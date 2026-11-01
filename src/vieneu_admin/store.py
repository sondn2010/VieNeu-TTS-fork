"""AdminStore: the single persistence facade used by the admin web app and the speech API."""
from __future__ import annotations

import logging
import os
import secrets
import threading
from pathlib import Path
from typing import Optional, Sequence, Union

from vieneu_preprocess.dictionary_schema import DictionaryFormatError, load_dictionary_json
from vieneu_preprocess.types import LexiconEntry

from .db import Database, Migration
from .models import StoreError
from .store_accounts import AccountStoreMixin
from .store_dictionaries import DictionaryStoreMixin
from .store_dictionary_entries import EntryStoreMixin
from .store_keys import KeyStoreMixin

log = logging.getLogger("vieneu.admin")

SEED_DIR = Path(__file__).resolve().parent / "seed"


class AdminStore(AccountStoreMixin, KeyStoreMixin, DictionaryStoreMixin, EntryStoreMixin):
    """Users, API keys, sessions and dictionaries in one SQLite file.

    Opening the store applies pending migrations (backing up an existing file first).
    Safe to share across threads: each thread uses its own SQLite connection.
    """

    def __init__(self, path: Union[str, os.PathLike, None] = None, *,
                 migrations: Optional[Sequence[tuple[int, Migration]]] = None):
        self.db = Database(path)
        self._lexicon_lock = threading.Lock()
        self._lexicon_cache: Optional[tuple[str, list[LexiconEntry]]] = None
        try:
            self.schema_version = self.db.migrate(migrations)
        except BaseException:
            self.db.close()  # do not leak handles (Windows keeps the file locked)
            raise

    @property
    def path(self) -> Path:
        return self.db.path

    def close(self) -> None:
        self.db.close()

    # -- meta -------------------------------------------------------------------
    def csrf_secret(self) -> bytes:
        """Random CSRF signing secret, created once and persisted so restarts keep forms valid."""
        with self.db.write() as c:
            c.execute("INSERT OR IGNORE INTO meta (key, value) VALUES ('csrf_secret', ?)",
                      (secrets.token_hex(32),))
            value = c.execute("SELECT value FROM meta WHERE key = 'csrf_secret'").fetchone()[0]
        return bytes.fromhex(value)

    # -- bootstrap --------------------------------------------------------------
    def bootstrap_admin(self, username: str, password: str) -> bool:
        """Ensure an active admin exists. Returns True when an account was created or promoted.

        A no-op when any active admin already exists, so env credentials never
        overwrite a password changed later in the web app.
        """
        if self.has_active_admin():
            return False
        existing = self.get_user_by_name(username)
        if existing is None:
            self.create_user(username, password, "admin")
        else:
            self.reset_password(existing.id, password)
            self.set_active(existing.id, True)
            self.set_role(existing.id, "admin")
        log.info("admin account %r is ready", username)
        return True

    def seed_if_empty(self, seed_dir: Union[str, os.PathLike, None] = None) -> int:
        """Load every ``*.json`` seed dictionary when the DB has no dictionaries yet.

        Returns the number of dictionaries imported. A broken seed file is logged and
        skipped so one bad file cannot block startup.
        """
        if self.list_dictionaries():
            return 0
        folder = Path(seed_dir) if seed_dir is not None else SEED_DIR
        if not folder.is_dir():
            log.warning("seed directory %s not found; no dictionaries seeded", folder)
            return 0
        count = 0
        for file in sorted(folder.glob("*.json")):
            try:
                self.import_dictionary(load_dictionary_json(file.read_bytes()))
                count += 1
            except (OSError, DictionaryFormatError, StoreError) as e:
                log.error("skipping seed dictionary %s: %s", file.name, e)
        if count:
            log.info("seeded %d dictionaries from %s", count, folder)
        return count
