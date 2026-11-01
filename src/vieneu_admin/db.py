"""SQLite connection management, schema and numbered migrations for the admin app.

Threading: every thread gets its own connection (``threading.local``), so cursors are
never shared across FastAPI worker threads. WAL mode plus ``busy_timeout`` lets those
connections read concurrently while writers serialize through ``BEGIN IMMEDIATE``.

Before any migration runs on an existing database, the WAL is checkpointed and a
consistent copy is written with the SQLite online-backup API (never a raw file copy).
"""
from __future__ import annotations

import logging
import os
import sqlite3
import threading
import time
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Callable, Iterator, Optional, Sequence, Union

log = logging.getLogger("vieneu.admin.db")

DEFAULT_DB_PATH = os.path.join("vieneu_data", "admin.sqlite3")

Migration = Union[Sequence[str], Callable[[sqlite3.Connection], None]]

SCHEMA_V1: tuple[str, ...] = (
    """CREATE TABLE users (
        id INTEGER PRIMARY KEY,
        username TEXT NOT NULL UNIQUE COLLATE NOCASE,
        password_hash TEXT NOT NULL,
        role TEXT NOT NULL CHECK (role IN ('admin', 'user')),
        active INTEGER NOT NULL DEFAULT 1,
        created_at INTEGER NOT NULL)""",
    """CREATE TABLE api_keys (
        id INTEGER PRIMARY KEY,
        user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
        name TEXT NOT NULL,
        prefix TEXT NOT NULL,
        key_hash TEXT NOT NULL UNIQUE,
        created_at INTEGER NOT NULL,
        last_used_at INTEGER,
        revoked_at INTEGER)""",
    "CREATE INDEX idx_api_keys_user ON api_keys(user_id)",
    """CREATE TABLE sessions (
        token_hash TEXT PRIMARY KEY,
        user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
        csrf TEXT NOT NULL,
        expires_at INTEGER NOT NULL)""",
    "CREATE INDEX idx_sessions_user ON sessions(user_id)",
    """CREATE TABLE dictionaries (
        id INTEGER PRIMARY KEY,
        name TEXT NOT NULL UNIQUE COLLATE NOCASE,
        kind TEXT NOT NULL CHECK (kind IN ('english', 'term', 'name')),
        enabled INTEGER NOT NULL DEFAULT 1,
        description TEXT NOT NULL DEFAULT '',
        updated_at INTEGER NOT NULL)""",
    """CREATE TABLE dictionary_entries (
        id INTEGER PRIMARY KEY,
        dictionary_id INTEGER NOT NULL REFERENCES dictionaries(id) ON DELETE CASCADE,
        term TEXT NOT NULL,
        term_key TEXT NOT NULL,
        replacement TEXT NOT NULL DEFAULT '',
        mode TEXT NOT NULL CHECK (mode IN ('phonetic', 'en')),
        case_sensitive INTEGER NOT NULL DEFAULT 0,
        note TEXT NOT NULL DEFAULT '',
        UNIQUE (dictionary_id, term_key))""",
    # Small key/value table: CSRF signing secret and the dictionary version counter.
    "CREATE TABLE meta (key TEXT PRIMARY KEY, value TEXT NOT NULL)",
)

MIGRATIONS: list[tuple[int, Migration]] = [(1, SCHEMA_V1)]


def default_db_path() -> Path:
    return Path(os.environ.get("VIENEU_ADMIN_DB") or DEFAULT_DB_PATH)


class Database:
    def __init__(self, path: Union[str, os.PathLike, None] = None):
        self.path = Path(path) if path is not None else default_db_path()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._local = threading.local()
        self._all: list[sqlite3.Connection] = []
        self._all_lock = threading.Lock()
        self._closed = False

    # -- connections -------------------------------------------------------------
    def conn(self) -> sqlite3.Connection:
        c: Optional[sqlite3.Connection] = getattr(self._local, "conn", None)
        if c is not None:
            return c
        if self._closed:
            raise RuntimeError("database is closed")
        # check_same_thread=False only so close() can release every thread's handle at
        # shutdown; during normal operation each connection is used by its owner only.
        c = sqlite3.connect(self.path, timeout=10.0, isolation_level=None, check_same_thread=False)
        c.row_factory = sqlite3.Row
        c.execute("PRAGMA journal_mode = WAL")
        c.execute("PRAGMA busy_timeout = 10000")
        c.execute("PRAGMA foreign_keys = ON")
        c.execute("PRAGMA synchronous = NORMAL")
        self._local.conn = c
        with self._all_lock:
            self._all.append(c)
        return c

    def close(self) -> None:
        with self._all_lock:
            self._closed = True
            for c in self._all:
                try:
                    c.close()
                except sqlite3.Error:  # pragma: no cover - best effort at shutdown
                    log.warning("failed to close a SQLite connection", exc_info=True)
            self._all.clear()
        self._local = threading.local()

    @contextmanager
    def write(self) -> Iterator[sqlite3.Connection]:
        """One write transaction; takes the write lock up front to avoid upgrade deadlocks."""
        c = self.conn()
        c.execute("BEGIN IMMEDIATE")
        try:
            yield c
        except BaseException:
            c.execute("ROLLBACK")
            raise
        c.execute("COMMIT")

    def query(self, sql: str, params: Sequence[Any] = ()) -> list[sqlite3.Row]:
        return self.conn().execute(sql, params).fetchall()

    def query_one(self, sql: str, params: Sequence[Any] = ()) -> Optional[sqlite3.Row]:
        return self.conn().execute(sql, params).fetchone()

    # -- migrations --------------------------------------------------------------
    def schema_version(self) -> int:
        c = self.conn()
        c.execute("CREATE TABLE IF NOT EXISTS schema_version (version INTEGER NOT NULL)")
        row = c.execute("SELECT MAX(version) FROM schema_version").fetchone()
        return int(row[0] or 0)

    def backup(self, label: str) -> Path:
        """Checkpoint the WAL, then write a consistent copy next to the database file."""
        c = self.conn()
        c.execute("PRAGMA wal_checkpoint(TRUNCATE)")
        stamp = time.strftime("%Y%m%d-%H%M%S")
        dest = self.path.with_name(f"{self.path.name}.bak-{label}-{stamp}")
        n = 1
        while dest.exists():
            n += 1
            dest = self.path.with_name(f"{self.path.name}.bak-{label}-{stamp}-{n}")
        target = sqlite3.connect(dest)
        try:
            c.backup(target)
        finally:
            target.close()
        return dest

    def migrate(self, migrations: Optional[Sequence[tuple[int, Migration]]] = None) -> int:
        """Apply pending migrations in order; returns the resulting schema version."""
        steps = sorted(migrations if migrations is not None else MIGRATIONS, key=lambda m: m[0])
        current = self.schema_version()
        pending = [(v, m) for v, m in steps if v > current]
        if not pending:
            return current
        if current > 0:
            bak = self.backup(f"v{current}")
            log.info("admin DB backed up to %s before migrating v%d -> v%d", bak, current, pending[-1][0])
        for version, step in pending:
            with self.write() as c:
                # Re-check inside the write lock in case another process migrated meanwhile.
                done = c.execute("SELECT MAX(version) FROM schema_version").fetchone()[0] or 0
                if version <= done:
                    continue
                if callable(step):
                    step(c)
                else:
                    for stmt in step:
                        c.execute(stmt)
                c.execute("INSERT INTO schema_version (version) VALUES (?)", (version,))
            log.info("admin DB migrated to schema v%d", version)
        return self.schema_version()
