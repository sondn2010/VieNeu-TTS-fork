"""Portal test harness: creates a throwaway database per session (never the
database named in `VIENEU_PORTAL_TEST_DATABASE_URL` itself — that URL's
database name is only a naming template), migrates it with Alembic, truncates
between tests, and drops it at session end. The suite errors (not skips) when
the connection is set but unreachable; it skips cleanly when unset, so the
main engine test suite never depends on Postgres.
"""
from __future__ import annotations

import os
import uuid
from typing import Iterator
from urllib.parse import urlsplit, urlunsplit

import pytest
from sqlalchemy import text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

os.environ.setdefault("VIENEU_PORTAL_SECRET_KEY", "x" * 32)

_BASE_TEST_DATABASE_URL = os.environ.get("VIENEU_PORTAL_TEST_DATABASE_URL")


def _split_maintenance_url_and_dbname(libpq_url: str) -> tuple[str, str]:
    parts = urlsplit(libpq_url)
    dbname = parts.path.lstrip("/")
    maintenance = urlunsplit((parts.scheme, parts.netloc, "/postgres", parts.query, parts.fragment))
    return maintenance, dbname


def _with_dbname(libpq_url: str, dbname: str) -> str:
    parts = urlsplit(libpq_url)
    return urlunsplit((parts.scheme, parts.netloc, f"/{dbname}", parts.query, parts.fragment))


@pytest.fixture(scope="session")
def portal_database_url() -> Iterator[str]:
    if not _BASE_TEST_DATABASE_URL:
        pytest.skip(
            "VIENEU_PORTAL_TEST_DATABASE_URL is not set; run `make portal-test` "
            "or export it to a disposable Postgres connection"
        )

    from vieneu_portal.config import to_libpq_url

    base_url = to_libpq_url(_BASE_TEST_DATABASE_URL)
    maintenance_url, base_dbname = _split_maintenance_url_and_dbname(base_url)
    if "test" not in base_dbname.lower():
        pytest.fail(
            f"VIENEU_PORTAL_TEST_DATABASE_URL's database name ({base_dbname!r}) must "
            "contain 'test' — this fixture creates and DROPS a database per session"
        )

    import psycopg

    test_dbname = f"{base_dbname}_{uuid.uuid4().hex[:8]}"
    test_url = _with_dbname(base_url, test_dbname)

    with psycopg.connect(maintenance_url, autocommit=True) as conn:
        conn.execute(f'CREATE DATABASE "{test_dbname}"')
    with psycopg.connect(test_url, autocommit=True) as conn:
        conn.execute("CREATE EXTENSION IF NOT EXISTS pgcrypto")
        conn.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")

    os.environ["VIENEU_PORTAL_DATABASE_URL"] = test_url
    try:
        yield test_url
    finally:
        with psycopg.connect(maintenance_url, autocommit=True) as conn:
            conn.execute(
                "SELECT pg_terminate_backend(pid) FROM pg_stat_activity "
                "WHERE datname = %s AND pid <> pg_backend_pid()",
                (test_dbname,),
            )
            conn.execute(f'DROP DATABASE IF EXISTS "{test_dbname}"')


@pytest.fixture(scope="session")
def _migrated_engine(portal_database_url: str) -> Iterator[Engine]:
    from alembic import command
    from alembic.config import Config

    from vieneu_portal.__main__ import PACKAGE_DIR
    from vieneu_portal.config import to_sqlalchemy_url
    from vieneu_portal.db.session_factory import get_engine, reset_engine_cache

    sqlalchemy_url = to_sqlalchemy_url(portal_database_url)
    cfg = Config(str(PACKAGE_DIR / "alembic.ini"))
    cfg.set_main_option("script_location", str(PACKAGE_DIR / "migrations"))
    cfg.set_main_option("sqlalchemy.url", sqlalchemy_url)
    command.upgrade(cfg, "head")

    reset_engine_cache()  # also clears the settings cache, so get_engine() rebinds to this DB
    engine = get_engine()
    yield engine

    command.downgrade(cfg, "base")
    reset_engine_cache()


@pytest.fixture()
def db_session(_migrated_engine: Engine) -> Iterator[Session]:
    Session_ = sessionmaker(bind=_migrated_engine, expire_on_commit=False)
    session = Session_()
    try:
        yield session
    finally:
        session.rollback()
        session.close()
        with _migrated_engine.begin() as conn:
            tables = conn.execute(
                text(
                    "SELECT tablename FROM pg_tables WHERE schemaname = 'public' "
                    "AND tablename NOT IN ('alembic_version')"
                )
            ).scalars().all()
            if tables:
                names = ", ".join(f'"{t}"' for t in tables)
                conn.execute(text(f"TRUNCATE TABLE {names} RESTART IDENTITY CASCADE"))


@pytest.fixture()
def client(db_session: Session):
    """A TestClient wrapping the real app, bound to the same migrated,
    per-test-truncated database as `db_session` (requested here only for its
    cleanup — the app uses its own session internally via `get_db()`).
    """
    from fastapi.testclient import TestClient

    from vieneu_portal.app import create_app

    app = create_app()
    # Starlette's TestClient defaults request.client.host to the literal
    # string "testclient", which is not a valid `INET` value for the
    # `ip`/`email_key` throttle columns; use a real-looking loopback address.
    # Also use an https:// base_url: COOKIE_SECURE defaults to True, so our
    # cookies carry `Secure`, and httpx's cookiejar (correctly) never resends
    # a Secure cookie over the default plain-http://testserver base_url.
    with TestClient(app, base_url="https://testserver", client=("127.0.0.1", 12345)) as c:
        yield c
