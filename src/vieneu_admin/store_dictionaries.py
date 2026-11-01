"""Dictionary-level persistence and the cached enabled lexicon (mixed into AdminStore).

Every write bumps the ``dict_version`` counter in ``meta``, which invalidates the cached
lexicon, also across processes (e.g. a CLI import while the server runs).
"""
from __future__ import annotations

import re
import sqlite3
import threading
import time
import unicodedata
from typing import Iterable, Optional

from vieneu_preprocess.dictionary_schema import KINDS, merge_lexicon
from vieneu_preprocess.types import Dictionary, LexiconEntry

from .db import Database
from .models import DictionaryInfo, NotFoundError, StoreError
from .store_dictionary_entries import (PAGE_SIZE, insert_entries, require_dictionary, term_key,
                                       touch_dictionaries, validate_entry)

__all__ = ["DictionaryStoreMixin", "PAGE_SIZE", "slugify", "term_key", "validate_entry"]

MAX_DESCRIPTION_LEN = 500

_INFO_SELECT = ("SELECT d.*, (SELECT COUNT(*) FROM dictionary_entries e WHERE e.dictionary_id = d.id) "
                "AS entry_count FROM dictionaries d")


def slugify(name: str, fallback: str) -> str:
    """ASCII file-name slug for exports (Vietnamese diacritics stripped, đ -> d)."""
    text = unicodedata.normalize("NFKD", name.replace("đ", "d").replace("Đ", "D"))
    text = "".join(ch for ch in text if not unicodedata.combining(ch)).lower()
    slug = re.sub(r"[^a-z0-9]+", "-", text).strip("-")[:60]
    return slug or fallback


def _info(row: sqlite3.Row) -> DictionaryInfo:
    return DictionaryInfo(row["id"], row["name"], row["kind"], bool(row["enabled"]),
                          row["description"], row["updated_at"], row["entry_count"])


def _check_meta(name: str, kind: str, description: str) -> tuple[str, str]:
    name = (name or "").strip()
    if not (1 <= len(name) <= 80):
        raise StoreError("Dictionary name must be 1-80 characters.")
    if kind not in KINDS:
        raise StoreError(f"Kind must be one of {', '.join(KINDS)}.")
    if len(description or "") > MAX_DESCRIPTION_LEN:
        raise StoreError(f"Description must be at most {MAX_DESCRIPTION_LEN} characters.")
    return name, (description or "").strip()


class DictionaryStoreMixin:
    db: Database
    _lexicon_lock: threading.Lock
    _lexicon_cache: Optional[tuple[str, list[LexiconEntry]]]

    def list_dictionaries(self) -> list[DictionaryInfo]:
        return [_info(r) for r in self.db.query(_INFO_SELECT + " ORDER BY d.name COLLATE NOCASE")]

    def get_dictionary(self, dictionary_id: int) -> Optional[DictionaryInfo]:
        row = self.db.query_one(_INFO_SELECT + " WHERE d.id = ?", (dictionary_id,))
        return _info(row) if row else None

    def create_dictionary(self, name: str, kind: str, description: str = "", enabled: bool = True,
                          entries: Iterable[LexiconEntry] = ()) -> int:
        name, description = _check_meta(name, kind, description)
        try:
            with self.db.write() as c:
                cur = c.execute("INSERT INTO dictionaries (name, kind, enabled, description, updated_at) "
                                "VALUES (?, ?, ?, ?, ?)",
                                (name, kind, 1 if enabled else 0, description, int(time.time())))
                new_id = int(cur.lastrowid)
                insert_entries(c, new_id, entries, upsert=False)
                touch_dictionaries(c)
        except sqlite3.IntegrityError as e:
            raise StoreError(f"A dictionary named {name!r} already exists.") from e
        return new_id

    def import_dictionary(self, d: Dictionary) -> int:
        return self.create_dictionary(d.name, d.kind, d.description, d.enabled, d.entries)

    def update_dictionary(self, dictionary_id: int, *, name: Optional[str] = None,
                          description: Optional[str] = None) -> None:
        info = self.get_dictionary(dictionary_id)
        if info is None:
            raise NotFoundError("Dictionary not found.")
        new_name, new_desc = _check_meta(name if name is not None else info.name, info.kind,
                                         description if description is not None else info.description)
        try:
            with self.db.write() as c:
                c.execute("UPDATE dictionaries SET name = ?, description = ? WHERE id = ?",
                          (new_name, new_desc, dictionary_id))
                touch_dictionaries(c, dictionary_id)
        except sqlite3.IntegrityError as e:
            raise StoreError(f"A dictionary named {new_name!r} already exists.") from e

    def rename_dictionary(self, dictionary_id: int, name: str) -> None:
        self.update_dictionary(dictionary_id, name=name)

    def set_dictionary_enabled(self, dictionary_id: int, enabled: bool) -> None:
        with self.db.write() as c:
            require_dictionary(c, dictionary_id)
            c.execute("UPDATE dictionaries SET enabled = ? WHERE id = ?", (1 if enabled else 0, dictionary_id))
            touch_dictionaries(c, dictionary_id)

    def toggle_dictionary(self, dictionary_id: int) -> bool:
        with self.db.write() as c:
            require_dictionary(c, dictionary_id)
            c.execute("UPDATE dictionaries SET enabled = 1 - enabled WHERE id = ?", (dictionary_id,))
            touch_dictionaries(c, dictionary_id)
            return bool(c.execute("SELECT enabled FROM dictionaries WHERE id = ?", (dictionary_id,)).fetchone()[0])

    def delete_dictionary(self, dictionary_id: int) -> None:
        with self.db.write() as c:
            require_dictionary(c, dictionary_id)
            c.execute("DELETE FROM dictionaries WHERE id = ?", (dictionary_id,))
            touch_dictionaries(c)

    def replace_entries(self, dictionary_id: int, entries: Iterable[LexiconEntry]) -> int:
        with self.db.write() as c:
            require_dictionary(c, dictionary_id)
            c.execute("DELETE FROM dictionary_entries WHERE dictionary_id = ?", (dictionary_id,))
            n = insert_entries(c, dictionary_id, entries, upsert=False)
            touch_dictionaries(c, dictionary_id)
        return n

    def merge_entries(self, dictionary_id: int, entries: Iterable[LexiconEntry]) -> int:
        """Insert new terms and overwrite existing ones (matched by term key)."""
        with self.db.write() as c:
            require_dictionary(c, dictionary_id)
            n = insert_entries(c, dictionary_id, entries, upsert=True)
            touch_dictionaries(c, dictionary_id)
        return n

    def export_dictionary(self, dictionary_id: int) -> Dictionary:
        info = self.get_dictionary(dictionary_id)
        if info is None:
            raise NotFoundError("Dictionary not found.")
        rows = self.db.query("SELECT * FROM dictionary_entries WHERE dictionary_id = ?", (dictionary_id,))
        entries = [LexiconEntry(r["term"], r["replacement"], r["mode"], bool(r["case_sensitive"]), r["note"])
                   for r in rows]
        return Dictionary(info.name, info.kind, info.enabled, info.description, entries)  # type: ignore[arg-type]

    # -- lexicon ----------------------------------------------------------------
    def dict_version(self) -> str:
        row = self.db.query_one("SELECT value FROM meta WHERE key = 'dict_version'")
        return row[0] if row else "0"

    def enabled_lexicon(self) -> list[LexiconEntry]:
        """Merged entries of every enabled dictionary; cached until any dictionary write."""
        version = self.dict_version()
        with self._lexicon_lock:
            if self._lexicon_cache is not None and self._lexicon_cache[0] == version:
                return list(self._lexicon_cache[1])
        # A write racing this read only makes the cache look older than its data, so the
        # next call reloads; stale data is never cached under a newer version.
        lexicon = merge_lexicon([self.export_dictionary(d.id) for d in self.list_dictionaries() if d.enabled])
        with self._lexicon_lock:
            self._lexicon_cache = (version, lexicon)
        return list(lexicon)
