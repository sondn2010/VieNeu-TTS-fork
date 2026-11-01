"""Schema creation, numbered migrations and the pre-migration SQLite backup."""
import sqlite3

import pytest

from vieneu_admin import AdminStore
from vieneu_admin.db import MIGRATIONS


def _tables(path):
    con = sqlite3.connect(path)
    try:
        return {r[0] for r in con.execute("SELECT name FROM sqlite_master WHERE type = 'table'")}
    finally:
        con.close()


def test_fresh_db_gets_v1_without_backup(tmp_path):
    db = tmp_path / "admin.sqlite3"
    store = AdminStore(db)
    try:
        assert store.schema_version == 1
        assert {"users", "api_keys", "sessions", "dictionaries", "dictionary_entries",
                "schema_version"} <= _tables(db)
        assert store.db.query_one("PRAGMA journal_mode")[0] == "wal"
    finally:
        store.close()
    assert not list(tmp_path.glob("*.bak-*"))


def test_default_path_from_env(tmp_path, monkeypatch):
    target = tmp_path / "nested" / "x.sqlite3"
    monkeypatch.setenv("VIENEU_ADMIN_DB", str(target))
    store = AdminStore()
    try:
        assert store.path == target and target.exists()
    finally:
        store.close()


def test_existing_v1_is_backed_up_before_v2_runs(tmp_path):
    db = tmp_path / "admin.sqlite3"
    store = AdminStore(db)
    store.create_user("keeper", "password123", "admin")  # data that sits in the WAL
    store.close()

    seen = {}

    def v2(conn):
        baks = list(tmp_path.glob("admin.sqlite3.bak-v1-*"))
        seen["baks"] = baks
        conn.execute("ALTER TABLE users ADD COLUMN email TEXT")

    store = AdminStore(db, migrations=[*MIGRATIONS, (2, v2)])
    try:
        assert store.schema_version == 2
    finally:
        store.close()
    assert len(seen["baks"]) == 1
    bak = seen["baks"][0]
    con = sqlite3.connect(bak)
    try:  # the backup is a consistent, openable copy holding the pre-migration data
        assert con.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
        assert con.execute("SELECT username FROM users").fetchall() == [("keeper",)]
        cols = [r[1] for r in con.execute("PRAGMA table_info(users)")]
        assert "email" not in cols
    finally:
        con.close()


def test_failed_migration_rolls_back_and_keeps_version(tmp_path):
    db = tmp_path / "admin.sqlite3"
    AdminStore(db).close()

    def broken(conn):
        conn.execute("CREATE TABLE half_done (x INTEGER)")
        raise RuntimeError("boom")

    with pytest.raises(RuntimeError):
        AdminStore(db, migrations=[*MIGRATIONS, (2, broken)])
    store = AdminStore(db)
    try:
        assert store.schema_version == 1
        assert "half_done" not in _tables(db)
    finally:
        store.close()


def test_reopen_is_idempotent(tmp_path):
    db = tmp_path / "admin.sqlite3"
    AdminStore(db).close()
    store = AdminStore(db)
    try:
        assert store.schema_version == 1
    finally:
        store.close()
    assert not list(tmp_path.glob("*.bak-*"))
