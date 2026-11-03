"""Baseline migration correctness: every spec 08 table + C0 additions exist,
and the ORM metadata matches the live schema exactly (empty autogenerate diff).
"""
from __future__ import annotations

from alembic.autogenerate import compare_metadata
from alembic.runtime.migration import MigrationContext
from sqlalchemy import inspect
from sqlalchemy.engine import Engine

from vieneu_portal.db import Base

EXPECTED_TABLES = {
    "users",
    "voices",
    "tts_recordings",
    "podcasts",
    "podcast_turns",
    "story_projects",
    "story_characters",
    "story_segments",
    "pronunciation_rules",
    "developer_api_keys",
    "mcp_connected_clients",
    "vouchers",
    "user_sessions",
    "auth_throttle_events",
    "system_dictionaries",
    "system_pronunciation_rules",
    "admin_audit_log",
}


def test_all_spec_and_addition_tables_exist(_migrated_engine: Engine) -> None:
    inspector = inspect(_migrated_engine)
    assert EXPECTED_TABLES.issubset(set(inspector.get_table_names()))


def test_autogenerate_diff_against_models_is_empty(_migrated_engine: Engine) -> None:
    with _migrated_engine.connect() as connection:
        context = MigrationContext.configure(connection)
        diff = compare_metadata(context, Base.metadata)
    assert diff == [], f"migration drifted from the ORM models: {diff}"


def test_users_role_check_rejects_unknown_role(db_session) -> None:
    from sqlalchemy.exc import IntegrityError

    from vieneu_portal.db.models_users_and_sessions import User

    db_session.add(
        User(
            email="role-check@example.com",
            username="role-check",
            password_hash="x",
            role="NOT_A_ROLE",
        )
    )
    try:
        db_session.flush()
        assert False, "expected the role CHECK constraint to reject an invalid role"
    except IntegrityError:
        db_session.rollback()


def test_db_upgrade_backs_up_a_nonempty_database_first(_migrated_engine: Engine, tmp_path) -> None:
    import shutil

    from vieneu_portal.config import get_settings
    from vieneu_portal.db.database_backup_before_migrate import backup_before_upgrade

    if shutil.which("pg_dump") is None:
        import pytest as _pytest

        _pytest.skip("pg_dump not on PATH in this environment")

    settings = get_settings()
    dest = backup_before_upgrade(settings.DATABASE_URL, tmp_path)
    assert dest is not None
    assert dest.exists()
    assert dest.stat().st_size > 0


def test_email_unique_index_is_case_insensitive(db_session) -> None:
    from sqlalchemy.exc import IntegrityError

    from vieneu_portal.db.models_users_and_sessions import User

    db_session.add(User(email="Dup@Example.com", username="a", password_hash="x"))
    db_session.flush()
    db_session.add(User(email="dup@example.com", username="b", password_hash="x"))
    try:
        db_session.flush()
        assert False, "expected lower(email) unique index to reject a case-only duplicate"
    except IntegrityError:
        db_session.rollback()
