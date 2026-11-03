"""Builds a throwaway legacy admin SQLite database (the exact `SCHEMA_V1`
shape from `src/vieneu_admin/db.py`) with edge-case rows for the migrator's
tests: a disabled user, a revoked key, `en` entries with and without a
replacement, a case-sensitive duplicate term, unicode, and a pack whose name
survives import unedited.
"""
from __future__ import annotations

import hashlib
import sqlite3
import time
from pathlib import Path

_SCHEMA = (
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
    """CREATE TABLE sessions (
        token_hash TEXT PRIMARY KEY,
        user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
        csrf TEXT NOT NULL,
        expires_at INTEGER NOT NULL)""",
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
    "CREATE TABLE meta (key TEXT PRIMARY KEY, value TEXT NOT NULL)",
)

SCRYPT_PASSWORD_HASH_FOR = "correct-horse-battery-staple"


def fake_scrypt_hash(password: str) -> str:
    """A real `scrypt$...` hash so the migrated row logs in for real over
    HTTP: same format `security.hash_password` produces, salt fixed so the
    fixture is deterministic across test runs.
    """
    import base64

    salt = b"0123456789abcdef"
    digest = hashlib.scrypt(password.encode("utf-8"), salt=salt, n=2**14, r=8, p=1, maxmem=64 * 1024 * 1024, dklen=32)

    def b64(raw: bytes) -> str:
        return base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")

    return f"scrypt$16384$8$1${b64(salt)}${b64(digest)}"


def build_legacy_admin_sqlite(path: Path) -> dict:
    """Writes the fixture database and returns the raw row data used to
    build it, so a test can assert against exactly what it expects without
    re-deriving it.
    """
    conn = sqlite3.connect(path)
    try:
        for stmt in _SCHEMA:
            conn.execute(stmt)
        now = int(time.time())

        conn.execute(
            "INSERT INTO users (id, username, password_hash, role, active, created_at) VALUES (?, ?, ?, ?, ?, ?)",
            (1, "root", fake_scrypt_hash(SCRYPT_PASSWORD_HASH_FOR), "admin", 1, now - 1000),
        )
        conn.execute(
            "INSERT INTO users (id, username, password_hash, role, active, created_at) VALUES (?, ?, ?, ?, ?, ?)",
            (2, "disabled_user", fake_scrypt_hash("whatever-password"), "user", 0, now - 500),
        )

        conn.execute(
            "INSERT INTO api_keys (id, user_id, name, prefix, key_hash, created_at, last_used_at, revoked_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (1, 1, "ci", "vn_abcd1234", "a" * 64, now - 900, now - 100, None),
        )
        conn.execute(
            "INSERT INTO api_keys (id, user_id, name, prefix, key_hash, created_at, last_used_at, revoked_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (2, 2, "revoked-key", "vn_efgh5678", "b" * 64, now - 800, None, now - 50),
        )

        conn.execute(
            "INSERT INTO dictionaries (id, name, kind, enabled, description, updated_at) VALUES (?, ?, ?, ?, ?, ?)",
            (1, "Edge Cases", "term", 1, "unicode, en modes, case-sensitive duplicates", now),
        )
        entries = [
            # (id, term, term_key, replacement, mode, case_sensitive, note)
            (1, "KPI", "KPI", "kây-pi-ai", "phonetic", 1, ""),
            (2, "kpi", "kpi", "kây-pi-ai thường", "phonetic", 1, "case-sensitive duplicate of KPI"),
            (3, "API", "api", "ây-pi-ai", "en", "", "en with a replacement -> REPLACE"),
            (4, "Résumé", "résumé", "", "en", 0, "unicode, en with no replacement -> ENGLISH_FALLBACK"),
        ]
        for eid, term, term_key, replacement, mode, case_sensitive, note in entries:
            conn.execute(
                "INSERT INTO dictionary_entries (id, dictionary_id, term, term_key, replacement, mode, "
                "case_sensitive, note) VALUES (?, 1, ?, ?, ?, ?, ?, ?)",
                (eid, term, term_key, replacement, mode, int(bool(case_sensitive)), note),
            )
        conn.commit()
    finally:
        conn.close()

    return {
        "users": [
            {"id": 1, "username": "root", "role": "admin", "active": True},
            {"id": 2, "username": "disabled_user", "role": "user", "active": False},
        ],
        "api_keys": [{"id": 1, "user_id": 1}, {"id": 2, "user_id": 2, "revoked": True}],
        "dictionary_name": "Edge Cases",
        "entry_count": 4,
    }
