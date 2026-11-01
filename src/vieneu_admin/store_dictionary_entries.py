"""Dictionary entry persistence (mixed into AdminStore) and shared entry helpers.

Validation reuses the phase-1 JSON schema (``vieneu_preprocess.dictionary_schema``) so web
forms, imports and seeds accept exactly the same entries. Every write calls
``touch_dictionaries`` to bump the ``dict_version`` counter that invalidates the lexicon cache.
"""
from __future__ import annotations

import json
import sqlite3
import time
from typing import Iterable, Optional

from vieneu_preprocess.dictionary_schema import FORMAT, DictionaryFormatError, load_dictionary_json
from vieneu_preprocess.types import LexiconEntry

from .db import Database
from .models import EntryRow, NotFoundError, StoreError

PAGE_SIZE = 50


def term_key(term: str, case_sensitive: bool) -> str:
    return term if case_sensitive else term.casefold()


def validate_entry(term: str, replacement: str = "", mode: str = "phonetic",
                   case_sensitive: bool = False, note: str = "") -> LexiconEntry:
    """Validate one entry with the dictionary schema; raise StoreError with a readable message."""
    doc = {"format": FORMAT, "name": "entry", "kind": "term",
           "entries": [{"term": (term or "").strip(), "replacement": (replacement or "").strip(),
                        "mode": mode, "case_sensitive": bool(case_sensitive), "note": note or ""}]}
    try:
        return load_dictionary_json(json.dumps(doc)).entries[0]
    except DictionaryFormatError as e:
        raise StoreError(str(e).replace("entries[0].", "")) from e


def touch_dictionaries(c: sqlite3.Connection, dictionary_id: Optional[int] = None) -> None:
    """Bump the global dictionary version (and the dictionary's updated_at)."""
    c.execute("INSERT INTO meta (key, value) VALUES ('dict_version', '1') ON CONFLICT(key) "
              "DO UPDATE SET value = CAST(CAST(value AS INTEGER) + 1 AS TEXT)")
    if dictionary_id is not None:
        c.execute("UPDATE dictionaries SET updated_at = ? WHERE id = ?", (int(time.time()), dictionary_id))


def require_dictionary(c: sqlite3.Connection, dictionary_id: int) -> None:
    if c.execute("SELECT 1 FROM dictionaries WHERE id = ?", (dictionary_id,)).fetchone() is None:
        raise NotFoundError("Dictionary not found.")


def insert_entries(c: sqlite3.Connection, dictionary_id: int, entries: Iterable[LexiconEntry],
                   *, upsert: bool) -> int:
    """Bulk insert; with ``upsert`` an existing term key is overwritten instead of failing."""
    sql = ("INSERT INTO dictionary_entries (dictionary_id, term, term_key, replacement, mode, "
           "case_sensitive, note) VALUES (?, ?, ?, ?, ?, ?, ?)")
    if upsert:
        sql += (" ON CONFLICT(dictionary_id, term_key) DO UPDATE SET term = excluded.term, "
                "replacement = excluded.replacement, mode = excluded.mode, "
                "case_sensitive = excluded.case_sensitive, note = excluded.note")
    n = 0
    for e in entries:
        c.execute(sql, (dictionary_id, e.term, term_key(e.term, e.case_sensitive), e.replacement,
                        e.mode, 1 if e.case_sensitive else 0, e.note))
        n += 1
    return n


def _entry(row: sqlite3.Row) -> EntryRow:
    return EntryRow(row["id"], row["dictionary_id"], row["term"], row["replacement"], row["mode"],
                    bool(row["case_sensitive"]), row["note"])


class EntryStoreMixin:
    db: Database

    def get_entry(self, dictionary_id: int, entry_id: int) -> Optional[EntryRow]:
        row = self.db.query_one("SELECT * FROM dictionary_entries WHERE id = ? AND dictionary_id = ?",
                                (entry_id, dictionary_id))
        return _entry(row) if row else None

    def upsert_entry(self, dictionary_id: int, entry: LexiconEntry, entry_id: Optional[int] = None) -> EntryRow:
        """Add an entry (``entry_id`` None) or edit one in place."""
        values = (entry.term, term_key(entry.term, entry.case_sensitive), entry.replacement, entry.mode,
                  1 if entry.case_sensitive else 0, entry.note)
        try:
            with self.db.write() as c:
                require_dictionary(c, dictionary_id)
                if entry_id is None:
                    cur = c.execute("INSERT INTO dictionary_entries (term, term_key, replacement, mode, "
                                    "case_sensitive, note, dictionary_id) VALUES (?, ?, ?, ?, ?, ?, ?)",
                                    (*values, dictionary_id))
                    entry_id = int(cur.lastrowid)
                elif c.execute("UPDATE dictionary_entries SET term = ?, term_key = ?, replacement = ?, mode = ?, "
                               "case_sensitive = ?, note = ? WHERE id = ? AND dictionary_id = ?",
                               (*values, entry_id, dictionary_id)).rowcount == 0:
                    raise NotFoundError("Entry not found.")
                touch_dictionaries(c, dictionary_id)
        except sqlite3.IntegrityError as e:
            raise StoreError(f"Term {entry.term!r} already exists in this dictionary.") from e
        return self.get_entry(dictionary_id, entry_id)  # type: ignore[return-value]

    def delete_entry(self, dictionary_id: int, entry_id: int) -> None:
        with self.db.write() as c:
            if c.execute("DELETE FROM dictionary_entries WHERE id = ? AND dictionary_id = ?",
                         (entry_id, dictionary_id)).rowcount == 0:
                raise NotFoundError("Entry not found.")
            touch_dictionaries(c, dictionary_id)

    def search_entries(self, dictionary_id: int, q: str = "", page: int = 1,
                       per_page: int = PAGE_SIZE) -> tuple[list[EntryRow], int]:
        """Return (entries on this page, total matches); matches term, replacement or note."""
        q = (q or "").strip()[:80]
        where, params = "dictionary_id = ?", [dictionary_id]
        if q:
            like = "%" + q.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_") + "%"
            where += (" AND (term LIKE ? ESCAPE '\\' OR replacement LIKE ? ESCAPE '\\' "
                      "OR note LIKE ? ESCAPE '\\')")
            params += [like, like, like]
        total = int(self.db.query_one(f"SELECT COUNT(*) FROM dictionary_entries WHERE {where}", params)[0])
        offset = (max(1, page) - 1) * per_page
        rows = self.db.query(f"SELECT * FROM dictionary_entries WHERE {where} "
                             "ORDER BY term COLLATE NOCASE, id LIMIT ? OFFSET ?", [*params, per_page, offset])
        return [_entry(r) for r in rows], total
