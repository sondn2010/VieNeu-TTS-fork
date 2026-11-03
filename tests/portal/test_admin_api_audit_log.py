"""`GET /api/v1/admin/audit-log`: read-only, filterable, and a true record
of mutations made through the admin API — no update/delete endpoint exists
for this table.
"""
from __future__ import annotations

from sqlalchemy import update

from vieneu_portal.db.models_users_and_sessions import User

_PASSWORD = "correct horse battery"


def _csrf(client) -> str:
    return client.get("/api/v1/auth/csrf").json()["csrf_token"]


def _signup_admin(client, db_session, email: str) -> str:
    resp = client.post(
        "/api/v1/auth/signup", json={"email": email, "password": _PASSWORD},
        headers={"X-CSRF-Token": _csrf(client)},
    )
    assert resp.status_code == 201
    db_session.execute(update(User).where(User.email == email).values(role="SUPERADMIN"))
    db_session.commit()
    return _csrf(client)


def test_audit_log_has_no_write_endpoints(client) -> None:
    from tests.portal.admin_route_enumeration import enumerate_routes

    audit_routes = [(m, p) for m, p in enumerate_routes(client.app) if p.startswith("/api/v1/admin/audit-log")]
    assert audit_routes == [("GET", "/api/v1/admin/audit-log")]


def test_audit_log_lists_and_filters_real_mutations(client, db_session) -> None:
    csrf = _signup_admin(client, db_session, "boss@example.com")
    resp = client.post(
        "/api/v1/admin/users", json={"email": "target@example.com", "password": _PASSWORD},
        headers={"X-CSRF-Token": csrf},
    )
    target_id = resp.json()["user"]["id"]
    client.post(
        f"/api/v1/admin/users/{target_id}/tokens", json={"delta": 10, "reason": "test credit"},
        headers={"X-CSRF-Token": csrf},
    )

    resp = client.get("/api/v1/admin/audit-log")
    assert resp.status_code == 200
    actions = {row["action"] for row in resp.json()["items"]}
    assert {"user.create", "user.tokens_adjust"}.issubset(actions)
    for row in resp.json()["items"]:
        assert "password" not in str(row).lower() or row["action"] != "user.create"

    resp = client.get("/api/v1/admin/audit-log?action=user.tokens_adjust")
    assert resp.status_code == 200
    items = resp.json()["items"]
    assert len(items) == 1
    assert items[0]["target_id"] == target_id
    assert items[0]["after"]["delta"] == 10

    resp = client.get(f"/api/v1/admin/audit-log?target_type=user&target_id={target_id}")
    assert resp.status_code == 200
    assert {row["action"] for row in resp.json()["items"]} == {"user.create", "user.tokens_adjust"}
