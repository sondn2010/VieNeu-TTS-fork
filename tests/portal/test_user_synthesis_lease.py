"""Per-user synthesis lease: one request in flight at a time, renewal
extends it, release clears it, and 10 parallel acquire attempts from the
same user leave exactly 1 holder.
"""
from __future__ import annotations

import threading
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import select

from vieneu_portal.db.models_users_and_sessions import User
from vieneu_portal.db.session_factory import get_sessionmaker
from vieneu_portal.errors import PortalError
from vieneu_portal.tts.user_synthesis_lease import acquire_lease, release_lease, renew_lease


def _make_user(db_session, email: str) -> User:
    user = User(
        email=email, username=email.split("@")[0], password_hash="scrypt$16384$8$1$x$y",
        token_balance=100, token_quota_total=100, daily_char_limit=100, daily_char_remaining=100,
    )
    db_session.add(user)
    db_session.commit()
    return user


def test_acquire_then_acquire_again_raises_409(db_session) -> None:
    user = _make_user(db_session, "lease1@example.com")
    acquire_lease(db_session, user.id, lease_sec=60)
    db_session.commit()
    with pytest.raises(PortalError) as exc_info:
        acquire_lease(db_session, user.id, lease_sec=60)
    assert exc_info.value.code == "SYNTHESIS_IN_PROGRESS"


def test_release_then_acquire_again_succeeds(db_session) -> None:
    user = _make_user(db_session, "lease2@example.com")
    acquire_lease(db_session, user.id, lease_sec=60)
    release_lease(db_session, user.id)
    db_session.commit()
    acquire_lease(db_session, user.id, lease_sec=60)   # does not raise
    db_session.commit()


def test_acquire_after_expiry_succeeds(db_session) -> None:
    user = _make_user(db_session, "lease3@example.com")
    db_session.execute(
        User.__table__.update().where(User.id == user.id).values(
            synthesis_lock_until=datetime.now(timezone.utc) - timedelta(seconds=1)
        )
    )
    db_session.commit()
    acquire_lease(db_session, user.id, lease_sec=60)   # does not raise
    db_session.commit()


def test_renew_extends_the_lease(db_session) -> None:
    user = _make_user(db_session, "lease4@example.com")
    acquire_lease(db_session, user.id, lease_sec=5)
    db_session.commit()
    db_session.expire_all()
    before = db_session.get(User, user.id).synthesis_lock_until

    renew_lease(db_session, user.id, lease_sec=600)
    db_session.commit()
    db_session.expire_all()
    after = db_session.get(User, user.id).synthesis_lock_until
    assert after > before


def test_ten_parallel_acquires_leave_exactly_one_holder(portal_database_url) -> None:
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

    from vieneu_portal.config import to_sqlalchemy_url

    engine = create_engine(to_sqlalchemy_url(portal_database_url))
    Session_ = sessionmaker(bind=engine)
    db = Session_()
    try:
        user = _make_user(db, "lease-concurrent@example.com")
        user_id = user.id
    finally:
        db.close()

    results = []
    lock = threading.Lock()

    def attempt():
        session = Session_()
        try:
            acquire_lease(session, user_id, lease_sec=60)
            session.commit()
            with lock:
                results.append("ok")
        except PortalError:
            session.rollback()
            with lock:
                results.append("busy")
        finally:
            session.close()

    threads = [threading.Thread(target=attempt) for _ in range(10)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert results.count("ok") == 1
    assert results.count("busy") == 9
    engine.dispose()
