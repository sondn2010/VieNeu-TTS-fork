"""Read-only reader for the legacy admin SQLite database
(`src/vieneu_admin/db.py`'s `SCHEMA_V1`). Opens the file in SQLite's own
read-only URI mode — never writes, never imports `vieneu_admin` — so the
caller's online-backup copy is the only thing this ever touches, and the
portal migrator stays decoupled from whether `vieneu_admin` is still
installed.
"""
from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class LegacyUser:
    id: int
    username: str
    password_hash: str
    role: str   # 'admin' | 'user'
    active: bool
    created_at: int   # unix epoch seconds


@dataclass(frozen=True)
class LegacyApiKey:
    id: int
    user_id: int
    name: str
    prefix: str
    key_hash: str
    created_at: int
    last_used_at: "int | None"
    revoked_at: "int | None"


@dataclass(frozen=True)
class LegacyDictionaryEntry:
    id: int
    dictionary_id: int
    term: str
    replacement: str
    mode: str   # 'phonetic' | 'en'
    case_sensitive: bool
    note: str


@dataclass(frozen=True)
class LegacyDictionary:
    id: int
    name: str
    kind: str   # 'english' | 'term' | 'name'
    enabled: bool
    description: str
    entries: tuple


@dataclass(frozen=True)
class LegacySnapshot:
    users: tuple
    api_keys: tuple
    dictionaries: tuple
    session_count: int   # counted, never migrated (phase 2 owns session shape)


def _open_readonly(sqlite_path: Path) -> sqlite3.Connection:
    uri = f"file:{sqlite_path.as_posix()}?mode=ro"
    conn = sqlite3.connect(uri, uri=True)
    conn.row_factory = sqlite3.Row
    return conn


def read_legacy_admin_database(sqlite_path: Path) -> LegacySnapshot:
    conn = _open_readonly(sqlite_path)
    try:
        users = tuple(
            LegacyUser(r["id"], r["username"], r["password_hash"], r["role"], bool(r["active"]), r["created_at"])
            for r in conn.execute("SELECT * FROM users ORDER BY id")
        )
        api_keys = tuple(
            LegacyApiKey(r["id"], r["user_id"], r["name"], r["prefix"], r["key_hash"], r["created_at"],
                         r["last_used_at"], r["revoked_at"])
            for r in conn.execute("SELECT * FROM api_keys ORDER BY id")
        )
        dictionaries = []
        for d in conn.execute("SELECT * FROM dictionaries ORDER BY id"):
            entries = tuple(
                LegacyDictionaryEntry(e["id"], e["dictionary_id"], e["term"], e["replacement"], e["mode"],
                                       bool(e["case_sensitive"]), e["note"])
                for e in conn.execute(
                    "SELECT * FROM dictionary_entries WHERE dictionary_id = ? ORDER BY id", (d["id"],)
                )
            )
            dictionaries.append(
                LegacyDictionary(d["id"], d["name"], d["kind"], bool(d["enabled"]), d["description"], entries)
            )
        (session_count,) = conn.execute("SELECT COUNT(*) FROM sessions").fetchone()
        return LegacySnapshot(
            users=users, api_keys=api_keys, dictionaries=tuple(dictionaries), session_count=int(session_count)
        )
    finally:
        conn.close()
