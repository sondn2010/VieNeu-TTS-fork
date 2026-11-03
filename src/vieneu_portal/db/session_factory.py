from __future__ import annotations

from functools import lru_cache
from typing import Iterator

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from ..config import get_settings


@lru_cache(maxsize=1)
def get_engine() -> Engine:
    settings = get_settings()
    # Session-level `SET ...` issued from a `connect` event lands inside the
    # connection's first implicit transaction and is reverted by the next
    # rollback (e.g. SQLAlchemy's reset-on-checkin) — Postgres GUC changes are
    # transactional even without SET LOCAL. Passing them as libpq startup
    # `options` applies them before any transaction opens, so they stick for
    # the connection's whole life.
    return create_engine(
        settings.sqlalchemy_database_url,
        pool_size=settings.DB_POOL_SIZE,
        max_overflow=settings.DB_MAX_OVERFLOW,
        pool_timeout=settings.DB_POOL_TIMEOUT_SEC,
        pool_pre_ping=True,
        connect_args={
            "connect_timeout": 5,
            "options": (
                f"-c statement_timeout={settings.DB_STATEMENT_TIMEOUT_MS} "
                f"-c idle_in_transaction_session_timeout={settings.DB_IDLE_IN_TX_TIMEOUT_MS}"
            ),
        },
    )


@lru_cache(maxsize=1)
def get_sessionmaker() -> sessionmaker:
    return sessionmaker(bind=get_engine(), autoflush=False, autocommit=False, expire_on_commit=False)


def reset_engine_cache() -> None:
    """Test-only: drop the cached engine/sessionmaker/settings so a new
    DATABASE_URL takes effect, disposing the old engine's pooled connections.
    """
    if get_engine.cache_info().currsize:
        get_engine().dispose()
    get_engine.cache_clear()
    get_sessionmaker.cache_clear()
    get_settings.cache_clear()


def get_db() -> Iterator[Session]:
    """FastAPI dependency. Never hold the yielded session across an engine/storage
    call in a route handler — commit first, then open a new short session.
    """
    session = get_sessionmaker()()
    try:
        yield session
    finally:
        session.close()
