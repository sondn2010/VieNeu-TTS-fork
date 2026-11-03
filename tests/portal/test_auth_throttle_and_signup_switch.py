"""Postgres-backed rate limiting: `auth_throttle_events` counting/purge, the
signup on/off switch, per-IP/global signup caps, and login lockout.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from vieneu_portal.security import postgres_auth_throttle as throttle


@pytest.fixture()
def fresh_settings():
    from vieneu_portal.config import get_settings

    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


# --- throttle module, DB-level ---------------------------------------------


def test_count_events_scoped_by_ip_and_email_key(db_session) -> None:
    throttle.record_event(db_session, kind=throttle.LOGIN_FAILURE, ip="1.1.1.1", email_key="a@example.com")
    throttle.record_event(db_session, kind=throttle.LOGIN_FAILURE, ip="1.1.1.1", email_key="b@example.com")
    throttle.record_event(db_session, kind=throttle.LOGIN_FAILURE, ip="2.2.2.2", email_key="a@example.com")

    assert throttle.count_events(db_session, kind=throttle.LOGIN_FAILURE, window_sec=900, ip="1.1.1.1") == 2
    assert (
        throttle.count_events(
            db_session, kind=throttle.LOGIN_FAILURE, window_sec=900, ip="1.1.1.1", email_key="a@example.com"
        )
        == 1
    )
    assert throttle.count_events(db_session, kind=throttle.SIGNUP, window_sec=900, ip="1.1.1.1") == 0


def test_retry_after_seconds_is_positive_within_window_and_zero_when_none(db_session) -> None:
    assert throttle.retry_after_seconds(db_session, kind=throttle.LOGIN_FAILURE, window_sec=900, ip="9.9.9.9") == 0
    throttle.record_event(db_session, kind=throttle.LOGIN_FAILURE, ip="9.9.9.9", email_key="x@example.com")
    retry_after = throttle.retry_after_seconds(db_session, kind=throttle.LOGIN_FAILURE, window_sec=900, ip="9.9.9.9")
    assert 0 < retry_after <= 900


def test_acquire_lock_serializes_concurrent_holders(_migrated_engine) -> None:
    """A direct, deterministic check of the Postgres mechanism `signup`/
    `login` rely on to close the count-then-insert race (H3): a second
    session trying to acquire the same key must block until the first
    commits (releasing its `pg_advisory_xact_lock`), not just "usually work".
    """
    import threading
    import time

    from sqlalchemy.orm import Session as SASession

    key = "test-lock-key"
    held_for = 0.3

    def holder() -> None:
        session = SASession(bind=_migrated_engine)
        throttle.acquire_lock(session, key)
        time.sleep(held_for)
        session.commit()  # releases the advisory xact lock
        session.close()

    t = threading.Thread(target=holder)
    t.start()
    time.sleep(0.05)  # let the holder acquire first

    waiter_session = SASession(bind=_migrated_engine)
    start = time.monotonic()
    throttle.acquire_lock(waiter_session, key)
    waited = time.monotonic() - start
    waiter_session.commit()
    waiter_session.close()
    t.join()

    assert waited >= held_for - 0.1


def test_purge_expired_removes_only_old_rows(db_session) -> None:
    from vieneu_portal.db.models_auth_throttle_events import AuthThrottleEvent

    old = AuthThrottleEvent(
        kind=throttle.LOGIN_FAILURE, ip="3.3.3.3", created_at=datetime.now(timezone.utc) - timedelta(days=2)
    )
    db_session.add(old)
    throttle.record_event(db_session, kind=throttle.LOGIN_FAILURE, ip="3.3.3.3")
    db_session.flush()

    removed = throttle.purge_expired(db_session, older_than_sec=86400)
    assert removed == 1
    assert throttle.count_events(db_session, kind=throttle.LOGIN_FAILURE, window_sec=10**9, ip="3.3.3.3") == 1


# --- HTTP level --------------------------------------------------------------


def _signup_payload(email: str, password: str = "correct horse battery") -> dict:
    return {"email": email, "password": password}


def _csrf(client) -> str:
    resp = client.get("/api/v1/auth/csrf")
    assert resp.status_code == 200
    return resp.json()["csrf_token"]


def test_signup_disabled_returns_403(client, fresh_settings, monkeypatch) -> None:
    from vieneu_portal.config import get_settings

    monkeypatch.setenv("VIENEU_PORTAL_SIGNUP_ENABLED", "false")
    get_settings.cache_clear()

    resp = client.post(
        "/api/v1/auth/signup", json=_signup_payload("disabled@example.com"), headers={"X-CSRF-Token": _csrf(client)}
    )
    assert resp.status_code == 403
    assert resp.json()["error"]["code"] == "SIGNUP_DISABLED"


def test_signup_per_ip_cap_returns_429(client, fresh_settings, monkeypatch) -> None:
    from vieneu_portal.config import get_settings

    monkeypatch.setenv("VIENEU_PORTAL_SIGNUP_MAX_PER_IP_PER_HOUR", "1")
    get_settings.cache_clear()

    first = client.post(
        "/api/v1/auth/signup", json=_signup_payload("cap1@example.com"), headers={"X-CSRF-Token": _csrf(client)}
    )
    assert first.status_code == 201

    second = client.post(
        "/api/v1/auth/signup", json=_signup_payload("cap2@example.com"), headers={"X-CSRF-Token": _csrf(client)}
    )
    assert second.status_code == 429
    assert second.json()["error"]["code"] == "SIGNUP_RATE_LIMITED"


def test_signup_global_cap_returns_429(client, fresh_settings, monkeypatch) -> None:
    from vieneu_portal.config import get_settings

    monkeypatch.setenv("VIENEU_PORTAL_SIGNUP_MAX_GLOBAL_PER_HOUR", "1")
    monkeypatch.setenv("VIENEU_PORTAL_SIGNUP_MAX_PER_IP_PER_HOUR", "100")
    get_settings.cache_clear()

    first = client.post(
        "/api/v1/auth/signup", json=_signup_payload("global1@example.com"), headers={"X-CSRF-Token": _csrf(client)}
    )
    assert first.status_code == 201

    second = client.post(
        "/api/v1/auth/signup", json=_signup_payload("global2@example.com"), headers={"X-CSRF-Token": _csrf(client)}
    )
    assert second.status_code == 429
    assert second.json()["error"]["code"] == "SIGNUP_RATE_LIMITED"


def test_login_lockout_per_email_and_ip(client, fresh_settings, monkeypatch) -> None:
    from vieneu_portal.config import get_settings

    monkeypatch.setenv("VIENEU_PORTAL_LOGIN_MAX_FAILURES", "2")
    monkeypatch.setenv("VIENEU_PORTAL_LOGIN_MAX_FAILURES_PER_IP", "100")
    get_settings.cache_clear()

    signup = client.post(
        "/api/v1/auth/signup", json=_signup_payload("lockme@example.com"), headers={"X-CSRF-Token": _csrf(client)}
    )
    assert signup.status_code == 201

    for _ in range(2):
        resp = client.post(
            "/api/v1/auth/login",
            json={"email": "lockme@example.com", "password": "wrong password"},
            headers={"X-CSRF-Token": _csrf(client)},
        )
        assert resp.status_code == 401

    locked = client.post(
        "/api/v1/auth/login",
        json={"email": "lockme@example.com", "password": "correct horse battery"},
        headers={"X-CSRF-Token": _csrf(client)},
    )
    assert locked.status_code == 429
    body = locked.json()
    assert body["error"]["code"] == "LOGIN_LOCKED"
    assert body["error"]["retry_after"] > 0


def test_login_lockout_per_ip_across_emails(client, fresh_settings, monkeypatch) -> None:
    from vieneu_portal.config import get_settings

    monkeypatch.setenv("VIENEU_PORTAL_LOGIN_MAX_FAILURES", "100")
    monkeypatch.setenv("VIENEU_PORTAL_LOGIN_MAX_FAILURES_PER_IP", "2")
    get_settings.cache_clear()

    for i in range(2):
        resp = client.post(
            "/api/v1/auth/login",
            json={"email": f"nobody{i}@example.com", "password": "whatever"},
            headers={"X-CSRF-Token": _csrf(client)},
        )
        assert resp.status_code == 401

    locked = client.post(
        "/api/v1/auth/login",
        json={"email": "yet-another@example.com", "password": "whatever"},
        headers={"X-CSRF-Token": _csrf(client)},
    )
    assert locked.status_code == 429
    assert locked.json()["error"]["code"] == "LOGIN_LOCKED"
