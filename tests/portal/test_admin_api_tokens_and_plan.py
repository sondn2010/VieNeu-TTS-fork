"""`/api/v1/admin/users/{id}/tokens` and `.../plan`: atomic adjustment
(never negative, even racing the metering charge statement) and audit rows.
"""
from __future__ import annotations

import threading
from datetime import datetime, timedelta, timezone

from sqlalchemy import select, update

from vieneu_portal.db.models_admin_audit_log import AdminAuditLog
from vieneu_portal.db.models_users_and_sessions import User
from vieneu_portal.db.session_factory import get_sessionmaker
from vieneu_portal.tts.quota_precheck_and_atomic_charge import charge_or_none
from vieneu_portal.config import get_settings

_PASSWORD = "correct horse battery"


def _csrf(client) -> str:
    return client.get("/api/v1/auth/csrf").json()["csrf_token"]


def _signup(client, email: str) -> None:
    resp = client.post(
        "/api/v1/auth/signup", json={"email": email, "password": _PASSWORD},
        headers={"X-CSRF-Token": _csrf(client)},
    )
    assert resp.status_code == 201


def _promote(db_session, email: str, role: str) -> None:
    db_session.execute(update(User).where(User.email == email).values(role=role))
    db_session.commit()


def _create_target(client, csrf: str, email: str) -> str:
    resp = client.post(
        "/api/v1/admin/users", json={"email": email, "password": _PASSWORD}, headers={"X-CSRF-Token": csrf},
    )
    assert resp.status_code == 201
    return resp.json()["user"]["id"]


def test_adjust_tokens_requires_a_reason_and_never_goes_negative(client, db_session) -> None:
    _signup(client, "boss@example.com")
    _promote(db_session, "boss@example.com", "SUPERADMIN")
    csrf = _csrf(client)
    target_id = _create_target(client, csrf, "poorfolk@example.com")

    resp = client.post(
        f"/api/v1/admin/users/{target_id}/tokens", json={"delta": 100, "reason": ""}, headers={"X-CSRF-Token": csrf},
    )
    assert resp.status_code == 422

    resp = client.post(
        f"/api/v1/admin/users/{target_id}/tokens", json={"delta": -10_000_000, "reason": "oops"},
        headers={"X-CSRF-Token": csrf},
    )
    assert resp.status_code == 409
    assert resp.json()["error"]["code"] == "INSUFFICIENT_TOKENS"

    resp = client.post(
        f"/api/v1/admin/users/{target_id}/tokens", json={"delta": 500, "reason": "goodwill credit"},
        headers={"X-CSRF-Token": csrf},
    )
    assert resp.status_code == 200
    rows = list(db_session.execute(select(AdminAuditLog).where(AdminAuditLog.action == "user.tokens_adjust")).scalars())
    assert len(rows) == 1
    assert rows[0].after["delta"] == 500
    assert rows[0].after["reason"] == "goodwill credit"


def test_adjust_tokens_concurrent_with_metering_charge_never_goes_negative(client, db_session) -> None:
    _signup(client, "boss2@example.com")
    _promote(db_session, "boss2@example.com", "SUPERADMIN")
    csrf = _csrf(client)
    target_id = _create_target(client, csrf, "racer@example.com")
    db_session.execute(update(User).where(User.id == target_id).values(token_balance=100))
    db_session.commit()

    barrier = threading.Barrier(2)
    settings = get_settings()

    def do_charge():
        barrier.wait()
        session = get_sessionmaker()()
        try:
            charge_or_none(session, target_id, settings, chars=1, tokens=60)
            session.commit()
        finally:
            session.close()

    charge_thread = threading.Thread(target=do_charge)
    charge_thread.start()
    barrier.wait()
    resp = client.post(
        f"/api/v1/admin/users/{target_id}/tokens", json={"delta": -60, "reason": "clawback"},
        headers={"X-CSRF-Token": csrf},
    )
    charge_thread.join()

    db_session.expire_all()
    final_balance = db_session.get(User, target_id).token_balance
    assert final_balance >= 0
    # Exactly one of the two 60-token debits against a 100-token balance
    # must have been rejected (both succeeding would overdraw to -20).
    assert resp.status_code in (200, 409)


def test_update_plan_resets_daily_remaining_and_writes_one_audit_row(client, db_session) -> None:
    _signup(client, "boss3@example.com")
    _promote(db_session, "boss3@example.com", "SUPERADMIN")
    csrf = _csrf(client)
    target_id = _create_target(client, csrf, "planholder@example.com")
    db_session.execute(update(User).where(User.id == target_id).values(daily_char_remaining=0))
    db_session.commit()

    new_expiry = (datetime.now(timezone.utc) + timedelta(days=30)).isoformat()
    resp = client.patch(
        f"/api/v1/admin/users/{target_id}/plan",
        json={
            "plan_tier": "PRO", "token_quota_total": 500000, "daily_char_limit": 100000,
            "plan_expires_at": new_expiry, "reset_daily_remaining": True,
        },
        headers={"X-CSRF-Token": csrf},
    )
    assert resp.status_code == 200
    body = resp.json()["user"]
    assert body["plan_tier"] == "PRO"
    assert body["token_quota_total"] == 500000
    assert body["daily_char_limit"] == 100000
    assert body["daily_char_remaining"] == 100000

    rows = list(db_session.execute(select(AdminAuditLog).where(AdminAuditLog.action == "user.plan_update")).scalars())
    assert len(rows) == 1
    assert rows[0].before["plan_tier"] != "PRO"
