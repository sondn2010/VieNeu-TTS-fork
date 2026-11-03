"""The admin CLI (`python -m vieneu_portal <group> <command>`), driven via
`main(argv)` against the real Postgres test DB and (for the `voices` group)
the engine double server.
"""
from __future__ import annotations

import json

import pytest
from sqlalchemy import select

from tests.portal.engine_double_asgi_app import SERVICE_KEY, EngineDoubleState, run_engine_double_server
from tests.fixtures.legacy_admin_sqlite_builder import build_legacy_admin_sqlite
from vieneu_portal.__main__ import main
from vieneu_portal.config import get_settings
from vieneu_portal.db.models_dictionaries import SystemDictionary
from vieneu_portal.db.models_users_and_sessions import User


def _fixed_password(monkeypatch, password: str, module) -> None:
    monkeypatch.setattr(module.getpass, "getpass", lambda prompt="": password)


def test_admin_create_then_user_commands(db_session, monkeypatch) -> None:
    import vieneu_portal.admin_cli.commands_users_and_admins as mod

    _fixed_password(monkeypatch, "correct horse battery", mod)
    assert main(["admin", "create", "root@example.com", "--role", "superadmin"]) == 0
    # A second superadmin so demoting the first below does not hit the
    # last-active-superadmin guard (covered on its own in test_role_change_guards.py).
    assert main(["admin", "create", "root2@example.com", "--role", "superadmin"]) == 0

    user = db_session.execute(select(User).where(User.email == "root@example.com")).scalar_one()
    assert user.role == "SUPERADMIN"

    assert main(["user", "set-role", "root@example.com", "ADMIN"]) == 0
    db_session.expire_all()
    assert db_session.get(User, user.id).role == "ADMIN"

    assert main(["user", "set-active", "root@example.com", "--off"]) == 0
    db_session.expire_all()
    assert db_session.get(User, user.id).is_active is False

    assert main(["user", "reset-password", "root@example.com"]) == 0


def test_user_set_role_rejects_unknown_email(db_session, monkeypatch) -> None:
    with pytest.raises(SystemExit):
        main(["user", "set-role", "nobody@example.com", "ADMIN"])


def test_system_dict_seed_list_import_export_enable_disable(db_session, tmp_path, capsys) -> None:
    assert main(["system-dict", "seed"]) == 0
    assert len(list(db_session.execute(select(SystemDictionary)).scalars())) == 7

    capsys.readouterr()
    assert main(["system-dict", "list"]) == 0
    out = capsys.readouterr().out
    assert "Kinh doanh" in out or "term" in out

    pack_name = db_session.execute(select(SystemDictionary.name)).scalars().first()
    import_file = tmp_path / "extra.txt"
    import_file.write_text("Hà Nội = Ha Noi\n", encoding="utf-8")
    assert main(["system-dict", "import", str(import_file), "--pack", pack_name, "--mode", "merge"]) == 0

    export_dir = tmp_path / "export"
    assert main(["system-dict", "export", str(export_dir)]) == 0
    assert len(list(export_dir.glob("*.json"))) == 7

    assert main(["system-dict", "disable", pack_name]) == 0
    db_session.expire_all()
    pack = db_session.execute(select(SystemDictionary).where(SystemDictionary.name == pack_name)).scalar_one()
    assert pack.is_enabled is False

    assert main(["system-dict", "enable", pack_name]) == 0
    db_session.expire_all()
    assert db_session.get(SystemDictionary, pack.id).is_enabled is True


def test_text_preview_runs_the_pipeline_and_prints_output(db_session, capsys) -> None:
    assert main(["text", "preview", "x ∈ ℝ"]) == 0
    out = capsys.readouterr().out
    assert "thuộc tập số thực" in out


def test_voices_sync(db_session, monkeypatch) -> None:
    state = EngineDoubleState()
    with run_engine_double_server(state) as base_url:
        monkeypatch.setenv("VIENEU_PORTAL_ENGINE_URL", base_url)
        monkeypatch.setenv("VIENEU_PORTAL_ENGINE_SERVICE_KEY", SERVICE_KEY)
        get_settings.cache_clear()
        try:
            assert main(["voices", "sync"]) == 0
        finally:
            get_settings.cache_clear()


def test_voices_render_samples(db_session, monkeypatch) -> None:
    import os

    from vieneu_portal.voices.voice_catalog_from_engine import slug_id

    if not os.environ.get("VIENEU_PORTAL_S3_ENDPOINT"):
        pytest.skip("VIENEU_PORTAL_S3_ENDPOINT is not set; run via `make portal-test`")

    state = EngineDoubleState()
    with run_engine_double_server(state) as base_url:
        monkeypatch.setenv("VIENEU_PORTAL_ENGINE_URL", base_url)
        monkeypatch.setenv("VIENEU_PORTAL_ENGINE_SERVICE_KEY", SERVICE_KEY)
        get_settings.cache_clear()
        try:
            assert main(["voices", "sync"]) == 0
            voice_id = slug_id(state.voices[0]["id"])
            assert main(["voices", "render-samples", "--only", voice_id]) == 0
        finally:
            get_settings.cache_clear()


def test_migrate_sqlite_dry_run_cli(db_session, tmp_path, monkeypatch, capsys) -> None:
    sqlite_path = tmp_path / "admin.sqlite3"
    build_legacy_admin_sqlite(sqlite_path)
    report_path = tmp_path / "report.json"

    # Keep the pg_dump/SQLite-backup side effect out of the repo working
    # directory (the default BACKUP_DIR is a relative path).
    monkeypatch.setenv("VIENEU_PORTAL_BACKUP_DIR", str(tmp_path / "backups"))
    get_settings.cache_clear()
    try:
        exit_code = main(["migrate-sqlite", "--sqlite", str(sqlite_path), "--dry-run", "--report", str(report_path)])
    finally:
        get_settings.cache_clear()
    assert exit_code == 0

    report = json.loads(report_path.read_text(encoding="utf-8"))
    assert report["mode"] == "dry-run"
    assert report["lost_rows"] == 0 and report["conflicts"] == []
    assert db_session.execute(select(User)).first() is None
