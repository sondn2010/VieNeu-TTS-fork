"""SQLite -> Postgres migrator: dry-run leaves the DB untouched, apply is
idempotent, a migrated user logs in over HTTP with the old password at the
synthetic `@migrated.invalid` address, and natural-key conflicts abort and
name the conflict.
"""
from __future__ import annotations

from sqlalchemy import select

from tests.fixtures.legacy_admin_sqlite_builder import SCRYPT_PASSWORD_HASH_FOR, build_legacy_admin_sqlite
from vieneu_portal.config import get_settings
from vieneu_portal.db.models_developer_and_billing import DeveloperApiKey
from vieneu_portal.db.models_dictionaries import SystemDictionary, SystemPronunciationRule
from vieneu_portal.db.models_users_and_sessions import User
from vieneu_portal.sqlite_migration.run_sqlite_to_postgres_migration import run_migration


def test_dry_run_is_clean_and_leaves_the_db_untouched(db_session, tmp_path) -> None:
    sqlite_path = tmp_path / "admin.sqlite3"
    build_legacy_admin_sqlite(sqlite_path)
    settings = get_settings()

    report = run_migration(db_session, settings, sqlite_path=sqlite_path, apply=False)

    assert report.lost_rows == 0
    assert report.conflicts == []
    assert report.users_total == 2 and report.users_inserted == 2
    assert report.dictionaries_total == 1 and report.rules_total == 4
    assert db_session.execute(select(User)).first() is None   # nothing committed


def test_apply_then_apply_again_is_idempotent(db_session, tmp_path) -> None:
    sqlite_path = tmp_path / "admin.sqlite3"
    build_legacy_admin_sqlite(sqlite_path)
    settings = get_settings()

    first = run_migration(db_session, settings, sqlite_path=sqlite_path, apply=True)
    assert first.lost_rows == 0 and first.conflicts == []
    assert first.users_inserted == 2
    assert db_session.execute(select(User)).all() != []

    second = run_migration(db_session, settings, sqlite_path=sqlite_path, apply=True, allow_existing=True)
    assert second.lost_rows == 0 and second.conflicts == []
    assert second.users_inserted == 0 and second.users_skipped_existing == 2
    assert second.dictionaries_inserted == 0 and second.dictionaries_skipped_existing == 1


def test_migrated_user_logs_in_over_http_with_the_old_password(client, db_session, tmp_path) -> None:
    sqlite_path = tmp_path / "admin.sqlite3"
    build_legacy_admin_sqlite(sqlite_path)
    settings = get_settings()

    report = run_migration(db_session, settings, sqlite_path=sqlite_path, apply=True)
    assert report.conflicts == [] and report.lost_rows == 0
    db_session.commit()

    email = next(n["email"] for n in report.needs_email if n["username"] == "root")
    assert email.endswith(f"@{settings.MIGRATION_EMAIL_DOMAIN}")

    csrf = client.get("/api/v1/auth/csrf").json()["csrf_token"]
    resp = client.post(
        "/api/v1/auth/login", json={"email": email, "password": SCRYPT_PASSWORD_HASH_FOR},
        headers={"X-CSRF-Token": csrf},
    )
    assert resp.status_code == 200

    profile = client.get("/api/v1/user/profile")
    assert profile.status_code == 200 and profile.json()["role"] == "SUPERADMIN"


def test_apply_migrates_dictionary_rules_with_correct_rule_kind(db_session, tmp_path) -> None:
    sqlite_path = tmp_path / "admin.sqlite3"
    build_legacy_admin_sqlite(sqlite_path)
    settings = get_settings()

    report = run_migration(db_session, settings, sqlite_path=sqlite_path, apply=True)
    assert report.conflicts == [] and report.lost_rows == 0

    pack = db_session.execute(select(SystemDictionary).where(SystemDictionary.name == "Edge Cases")).scalar_one()
    rules = {r.source_term: r for r in db_session.execute(
        select(SystemPronunciationRule).where(SystemPronunciationRule.dictionary_id == pack.id)
    ).scalars()}

    assert rules["KPI"].rule_kind == "REPLACE" and rules["KPI"].case_sensitive is True
    assert rules["kpi"].rule_kind == "REPLACE" and rules["kpi"].phonetic_replacement == "kây-pi-ai thường"
    assert rules["API"].rule_kind == "REPLACE" and rules["API"].phonetic_replacement == "ây-pi-ai"
    assert rules["Résumé"].rule_kind == "ENGLISH_FALLBACK" and rules["Résumé"].phonetic_replacement == ""


def test_apply_migrates_api_keys_as_live_developer_keys(db_session, tmp_path) -> None:
    sqlite_path = tmp_path / "admin.sqlite3"
    build_legacy_admin_sqlite(sqlite_path)
    settings = get_settings()

    report = run_migration(db_session, settings, sqlite_path=sqlite_path, apply=True)
    assert report.api_keys_inserted == 2

    keys = list(db_session.execute(select(DeveloperApiKey)).scalars())
    assert {k.environment for k in keys} == {"LIVE"}
    assert {k.key_hash for k in keys} == {"a" * 64, "b" * 64}


def test_apply_aborts_with_named_conflict_on_a_squatting_signup(client, db_session, tmp_path) -> None:
    sqlite_path = tmp_path / "admin.sqlite3"
    build_legacy_admin_sqlite(sqlite_path)
    settings = get_settings()

    squatted_email = f"root@{settings.MIGRATION_EMAIL_DOMAIN}"
    db_session.add(User(
        email=squatted_email, username="squatter", password_hash="scrypt$16384$8$1$x$y",
        token_balance=0, token_quota_total=0, daily_char_limit=0, daily_char_remaining=0,
    ))
    db_session.commit()

    report = run_migration(db_session, settings, sqlite_path=sqlite_path, apply=True, allow_existing=True)

    assert len(report.conflicts) == 1
    assert report.conflicts[0].kind == "user_email"
    assert report.conflicts[0].natural_key == squatted_email
    # Nothing committed: the squatter is the only user row, unchanged.
    db_session.expire_all()
    users = list(db_session.execute(select(User)).scalars())
    assert len(users) == 1 and users[0].email == squatted_email


def test_apply_aborts_with_named_conflict_on_a_pre_seeded_pack(db_session, tmp_path) -> None:
    sqlite_path = tmp_path / "admin.sqlite3"
    build_legacy_admin_sqlite(sqlite_path)
    settings = get_settings()

    db_session.add(SystemDictionary(name="Edge Cases", kind="term", description=""))
    db_session.commit()

    report = run_migration(db_session, settings, sqlite_path=sqlite_path, apply=True, allow_existing=True)

    assert len(report.conflicts) == 1
    assert report.conflicts[0].kind == "dictionary_name"
    assert report.conflicts[0].natural_key == "Edge Cases"
