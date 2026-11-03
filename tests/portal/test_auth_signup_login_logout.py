"""Signup, login, logout, CSRF, session fixation/expiry, role dependencies,
password change, and the "no plaintext in the DB" contract.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient as _TestClient
from sqlalchemy import select

from vieneu_portal.app import create_app
from vieneu_portal.auth.session_dependencies import require_admin
from vieneu_portal.db.models_users_and_sessions import User, UserSession
from vieneu_portal.errors import install_error_handlers
from vieneu_portal.security.password_hashing import hash_password

_PASSWORD = "correct horse battery"
# COOKIE_SECURE defaults to True, so cookies carry `Secure`; httpx only
# resends those over https://.
_HTTPS_BASE_URL = "https://testserver"


def _csrf(client) -> str:
    """`client`'s cookiejar persists the anon-CSRF cookie this sets, so later
    requests on the same `client` carry it automatically.
    """
    resp = client.get("/api/v1/auth/csrf")
    assert resp.status_code == 200
    return resp.json()["csrf_token"]


# --- signup ------------------------------------------------------------------


def test_signup_happy_path_sets_session_cookie_and_csrf(client) -> None:
    resp = client.post(
        "/api/v1/auth/signup",
        json={"email": "happy@example.com", "password": _PASSWORD},
        headers={"X-CSRF-Token": _csrf(client)},
    )
    assert resp.status_code == 201
    assert "csrf_token" in resp.json()
    assert client.cookies.get("session")

    profile = client.get("/api/v1/user/profile")
    assert profile.status_code == 200
    body = profile.json()
    assert body["email"] == "happy@example.com"
    assert body["username"] == "happy"  # default from the email local part


def test_signup_duplicate_email_case_insensitive_returns_409(client) -> None:
    first = client.post(
        "/api/v1/auth/signup",
        json={"email": "Dup@Example.com", "password": _PASSWORD},
        headers={"X-CSRF-Token": _csrf(client)},
    )
    assert first.status_code == 201

    second = client.post(
        "/api/v1/auth/signup",
        json={"email": "dup@example.com", "password": "another horse battery"},
        headers={"X-CSRF-Token": _csrf(client)},
    )
    assert second.status_code == 409
    assert second.json()["error"]["code"] == "EMAIL_TAKEN"


def test_signup_weak_password_returns_422(client) -> None:
    resp = client.post(
        "/api/v1/auth/signup",
        json={"email": "weak@example.com", "password": "short"},
        headers={"X-CSRF-Token": _csrf(client)},
    )
    assert resp.status_code == 422
    assert resp.json()["error"]["code"] == "VALIDATION_ERROR"


def test_signup_reserved_migration_domain_returns_422(client) -> None:
    resp = client.post(
        "/api/v1/auth/signup",
        json={"email": "x@migrated.invalid", "password": _PASSWORD},
        headers={"X-CSRF-Token": _csrf(client)},
    )
    assert resp.status_code == 422
    assert resp.json()["error"]["code"] == "EMAIL_DOMAIN_RESERVED"


def test_mutating_request_without_csrf_header_returns_403(client) -> None:
    resp = client.post("/api/v1/auth/signup", json={"email": "nocsrf@example.com", "password": _PASSWORD})
    assert resp.status_code == 403
    assert resp.json()["error"]["code"] == "CSRF_FAILED"


def test_csrf_repeated_get_reuses_the_same_anonymous_nonce(client) -> None:
    """Two overlapping `GET /auth/csrf` calls (two tabs, a UI retry, React
    StrictMode double effects) must not invalidate each other's token.
    """
    first_token = _csrf(client)
    first_nonce_cookie = client.cookies.get("anon_csrf_nonce")

    second_token = _csrf(client)
    assert client.cookies.get("anon_csrf_nonce") == first_nonce_cookie

    resp = client.post(
        "/api/v1/auth/signup",
        json={"email": "reuse-nonce@example.com", "password": _PASSWORD},
        headers={"X-CSRF-Token": first_token},
    )
    assert resp.status_code == 201
    assert second_token == first_token  # same nonce -> same signed token


def test_csrf_token_from_one_app_instance_is_accepted_by_another(db_session) -> None:
    """CSRF verification is stateless (HMAC over a derived `SECRET_KEY`), so a
    token minted by one worker process must validate on any other with the
    same `SECRET_KEY` — no shared in-memory state required.
    """
    app_a, app_b = create_app(), create_app()
    with _TestClient(app_a, base_url=_HTTPS_BASE_URL, client=("127.0.0.1", 1)) as client_a, _TestClient(
        app_b, base_url=_HTTPS_BASE_URL, client=("127.0.0.1", 2)
    ) as client_b:
        token = _csrf(client_a)
        client_b.cookies.set("anon_csrf_nonce", client_a.cookies.get("anon_csrf_nonce"))
        resp = client_b.post(
            "/api/v1/auth/signup",
            json={"email": "cross-instance@example.com", "password": _PASSWORD},
            headers={"X-CSRF-Token": token},
        )
    assert resp.status_code == 201


# --- login / logout -----------------------------------------------------------


def test_logout_invalidates_cookie(client) -> None:
    signup = client.post(
        "/api/v1/auth/signup",
        json={"email": "logout@example.com", "password": _PASSWORD},
        headers={"X-CSRF-Token": _csrf(client)},
    )
    assert signup.status_code == 201
    assert client.get("/api/v1/user/profile").status_code == 200

    logout = client.post("/api/v1/auth/logout", headers={"X-CSRF-Token": _csrf(client)})
    assert logout.status_code == 200
    assert client.get("/api/v1/user/profile").status_code == 401


def test_migrated_style_account_can_login(client, db_session) -> None:
    db_session.add(
        User(
            email="123@migrated.invalid",
            username="migrated-user",
            password_hash=hash_password(_PASSWORD),
            legacy_source_id="sqlite:users:123",
        )
    )
    db_session.commit()

    resp = client.post(
        "/api/v1/auth/login",
        json={"email": "123@migrated.invalid", "password": _PASSWORD},
        headers={"X-CSRF-Token": _csrf(client)},
    )
    assert resp.status_code == 200
    assert "csrf_token" in resp.json()


def test_absolute_expiry_ends_a_renewed_session(client, db_session) -> None:
    signup = client.post(
        "/api/v1/auth/signup",
        json={"email": "expire@example.com", "password": _PASSWORD},
        headers={"X-CSRF-Token": _csrf(client)},
    )
    assert signup.status_code == 201

    db_session.execute(
        UserSession.__table__.update().values(absolute_expires_at=datetime.now(timezone.utc) - timedelta(seconds=1))
    )
    db_session.commit()

    assert client.get("/api/v1/user/profile").status_code == 401


def test_sliding_renewal_is_persisted_on_a_read_only_request(client, db_session) -> None:
    """A GET request never otherwise commits (`get_db()` only closes); the
    renewal must be written directly inside session resolution itself, or a
    user who only reads gets logged out on schedule regardless of activity.
    """
    from vieneu_portal.config import get_settings

    signup = client.post(
        "/api/v1/auth/signup",
        json={"email": "renew@example.com", "password": _PASSWORD},
        headers={"X-CSRF-Token": _csrf(client)},
    )
    assert signup.status_code == 201

    near_expiry = datetime.now(timezone.utc) + timedelta(minutes=1)
    db_session.execute(UserSession.__table__.update().values(expires_at=near_expiry))
    db_session.commit()

    assert client.get("/api/v1/user/profile").status_code == 200

    settings = get_settings()
    row = db_session.execute(select(UserSession)).scalar_one()
    assert row.expires_at > near_expiry + timedelta(seconds=settings.SESSION_TTL_SEC - 120)


def test_admin_promotion_shortens_idle_window_on_next_request(client, db_session) -> None:
    """A session created as USER has a 14-day idle window; once promoted to
    ADMIN, the shorter admin idle window must apply on the very next request,
    not only once the slide would have extended it anyway.
    """
    from vieneu_portal.config import get_settings

    signup = client.post(
        "/api/v1/auth/signup",
        json={"email": "promote-shrink@example.com", "password": _PASSWORD},
        headers={"X-CSRF-Token": _csrf(client)},
    )
    assert signup.status_code == 201

    user = db_session.execute(select(User).where(User.email == "promote-shrink@example.com")).scalar_one()
    user.role = "ADMIN"
    db_session.commit()

    assert client.get("/api/v1/user/profile").status_code == 200

    settings = get_settings()
    row = db_session.execute(select(UserSession)).scalar_one()
    assert row.expires_at <= datetime.now(timezone.utc) + timedelta(seconds=settings.ADMIN_SESSION_IDLE_TTL_SEC + 5)


def test_signup_response_cookie_attributes(client) -> None:
    resp = client.post(
        "/api/v1/auth/signup",
        json={"email": "cookieattrs@example.com", "password": _PASSWORD},
        headers={"X-CSRF-Token": _csrf(client)},
    )
    assert resp.status_code == 201
    set_cookie = resp.headers.get("set-cookie", "")
    assert "session=" in set_cookie
    assert "httponly" in set_cookie.lower()
    assert "samesite=lax" in set_cookie.lower()
    assert "secure" in set_cookie.lower()
    assert "path=/" in set_cookie.lower()


def test_db_never_stores_plaintext_password_or_session_token(client, db_session) -> None:
    resp = client.post(
        "/api/v1/auth/signup",
        json={"email": "plaincheck@example.com", "password": _PASSWORD},
        headers={"X-CSRF-Token": _csrf(client)},
    )
    assert resp.status_code == 201
    raw_cookie = client.cookies.get("session")

    user = db_session.execute(select(User).where(User.email == "plaincheck@example.com")).scalar_one()
    assert _PASSWORD not in user.password_hash

    sessions = db_session.execute(select(UserSession)).scalars().all()
    assert sessions
    for session_row in sessions:
        assert raw_cookie not in session_row.token_hash


# --- password change -----------------------------------------------------------


def test_password_change_revokes_other_sessions(client) -> None:
    """Two independent "browsers" (separate cookie jars, so logging in on one
    never touches the other's session — login only deletes a stale session
    presented via its *own* incoming cookie, per `test_logout_invalidates...`-
    adjacent fixation handling) log in as the same user; changing the
    password from one must revoke the other but keep itself.
    """
    signup = client.post(
        "/api/v1/auth/signup",
        json={"email": "pwchange@example.com", "password": _PASSWORD},
        headers={"X-CSRF-Token": _csrf(client)},
    )
    assert signup.status_code == 201
    session_a = client.cookies.get("session")

    app_b = create_app()
    with _TestClient(app_b, base_url=_HTTPS_BASE_URL, client=("127.0.0.1", 6)) as client_b:
        login = client_b.post(
            "/api/v1/auth/login",
            json={"email": "pwchange@example.com", "password": _PASSWORD},
            headers={"X-CSRF-Token": _csrf(client_b)},
        )
        assert login.status_code == 200
        session_b = client_b.cookies.get("session")
        assert session_a != session_b  # new token every login (session fixation)

        assert client.get("/api/v1/user/profile").status_code == 200  # session A still valid

        change = client_b.post(
            "/api/v1/user/password",
            json={"current_password": _PASSWORD, "new_password": "another correct horse battery"},
            headers={"X-CSRF-Token": _csrf(client_b)},
        )
        assert change.status_code == 200

        assert client.get("/api/v1/user/profile").status_code == 401  # session A: revoked
        assert client_b.get("/api/v1/user/profile").status_code == 200  # session B: kept (did the change)


def test_password_change_wrong_current_password_returns_401(client) -> None:
    signup = client.post(
        "/api/v1/auth/signup",
        json={"email": "wrongcurrent@example.com", "password": _PASSWORD},
        headers={"X-CSRF-Token": _csrf(client)},
    )
    assert signup.status_code == 201

    resp = client.post(
        "/api/v1/user/password",
        json={"current_password": "not the password", "new_password": "another correct horse battery"},
        headers={"X-CSRF-Token": _csrf(client)},
    )
    assert resp.status_code == 401
    assert resp.json()["error"]["code"] == "INVALID_CREDENTIALS"


# --- role dependencies (2b) ----------------------------------------------------


def _mount_admin_probe() -> FastAPI:
    probe_app = FastAPI()
    install_error_handlers(probe_app)

    @probe_app.get("/probe")
    def _probe(ctx=Depends(require_admin)) -> dict:
        return {"ok": True}

    return probe_app


def test_require_admin_rejects_plain_user_role(client) -> None:
    signup = client.post(
        "/api/v1/auth/signup",
        json={"email": "plainuser@example.com", "password": _PASSWORD},
        headers={"X-CSRF-Token": _csrf(client)},
    )
    assert signup.status_code == 201

    with _TestClient(_mount_admin_probe(), base_url=_HTTPS_BASE_URL, client=("127.0.0.1", 4)) as probe_client:
        probe_client.cookies.set("session", client.cookies.get("session"))
        resp = probe_client.get("/probe")

    assert resp.status_code == 403
    assert resp.json()["error"]["code"] == "FORBIDDEN_ROLE"


def test_demoted_admin_loses_access_on_next_request(client, db_session) -> None:
    signup = client.post(
        "/api/v1/auth/signup",
        json={"email": "soon-admin@example.com", "password": _PASSWORD},
        headers={"X-CSRF-Token": _csrf(client)},
    )
    assert signup.status_code == 201

    user = db_session.execute(select(User).where(User.email == "soon-admin@example.com")).scalar_one()
    user.role = "ADMIN"
    db_session.commit()

    with _TestClient(_mount_admin_probe(), base_url=_HTTPS_BASE_URL, client=("127.0.0.1", 5)) as probe_client:
        probe_client.cookies.set("session", client.cookies.get("session"))
        assert probe_client.get("/probe").status_code == 200

        demoted = db_session.execute(select(User).where(User.email == "soon-admin@example.com")).scalar_one()
        demoted.role = "USER"
        db_session.commit()

        assert probe_client.get("/probe").status_code == 403
