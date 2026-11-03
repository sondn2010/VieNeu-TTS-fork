"""Route-enumeration guard: every registered `/api/v1/admin` route must
appear in `ADMIN_ROUTE_MIN_ROLE` with the exact method+path (so a new route
cannot ship without an explicit, tested role requirement), and calling each
one proves the gate actually fires: unauthenticated -> 401, as `USER` ->
403, and as `ADMIN` -> 403 for every `SUPERADMIN`-only entry.
"""
from __future__ import annotations

from uuid import uuid4

from sqlalchemy import update

from vieneu_portal.admin_api.admin_permission_matrix import ADMIN_ROUTE_MIN_ROLE, SUPERADMIN
from vieneu_portal.db.models_users_and_sessions import User

from tests.portal.admin_route_enumeration import enumerate_routes

_PASSWORD = "correct horse battery"
_MUTATING = ("POST", "PATCH", "PUT", "DELETE")

_PATH_PARAM_VALUES = {
    "user_id": str(uuid4()),
    "key_id": str(uuid4()),
    "recording_id": str(uuid4()),
    "dictionary_id": "1",
    "voice_id": "some-voice",
}


def _fill_path(path: str) -> str:
    for name, value in _PATH_PARAM_VALUES.items():
        path = path.replace("{" + name + "}", value)
    return path


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


def _call(client, method: str, path: str, *, csrf: str | None = None):
    headers = {"X-CSRF-Token": csrf} if csrf else {}
    body = {} if method in _MUTATING else None
    return client.request(method, _fill_path(path), headers=headers, json=body)


def test_every_registered_admin_route_is_in_the_matrix(client) -> None:
    registered = {(m, p) for m, p in enumerate_routes(client.app) if p.startswith("/api/v1/admin")}
    matrix = {(m, p) for m, p, _role in ADMIN_ROUTE_MIN_ROLE}
    assert registered == matrix


def test_unauthenticated_gets_401_on_every_admin_route(client) -> None:
    for method, path, _min_role in ADMIN_ROUTE_MIN_ROLE:
        resp = _call(client, method, path)
        assert resp.status_code == 401, f"{method} {path} -> {resp.status_code}: {resp.text}"


def test_plain_user_gets_403_on_every_admin_route(client, db_session) -> None:
    _signup(client, "plainuser@example.com")
    csrf = _csrf(client)
    for method, path, _min_role in ADMIN_ROUTE_MIN_ROLE:
        resp = _call(client, method, path, csrf=csrf)
        assert resp.status_code == 403, f"{method} {path} -> {resp.status_code}: {resp.text}"
        assert resp.json()["error"]["code"] == "FORBIDDEN_ROLE"


def test_admin_gets_403_on_every_superadmin_only_route(client, db_session) -> None:
    _signup(client, "adminuser@example.com")
    _promote(db_session, "adminuser@example.com", "ADMIN")
    csrf = _csrf(client)
    superadmin_only = [(m, p) for m, p, role in ADMIN_ROUTE_MIN_ROLE if role == SUPERADMIN]
    assert superadmin_only, "expected at least one SUPERADMIN-only route"
    for method, path in superadmin_only:
        resp = _call(client, method, path, csrf=csrf)
        assert resp.status_code == 403, f"{method} {path} -> {resp.status_code}: {resp.text}"
        assert resp.json()["error"]["code"] == "FORBIDDEN_ROLE"
