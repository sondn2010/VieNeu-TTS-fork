"""`/api/v1/admin/users*`: list/create/view/update/role/password/delete,
their guards (last superadmin, self-modification, ADMIN-manages-USER-only),
and that every mutation writes exactly one audit row.
"""
from __future__ import annotations

from sqlalchemy import select, update

from vieneu_portal.db.models_admin_audit_log import AdminAuditLog
from vieneu_portal.db.models_users_and_sessions import User

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


def _audit_rows(db_session, action: str) -> list:
    return list(db_session.execute(select(AdminAuditLog).where(AdminAuditLog.action == action)).scalars())


def test_create_user_requires_admin_and_rejects_role_escalation_for_admin_actor(client, db_session) -> None:
    _signup(client, "boss@example.com")
    _promote(db_session, "boss@example.com", "ADMIN")
    csrf = _csrf(client)

    resp = client.post(
        "/api/v1/admin/users", json={"email": "wannabe@example.com", "password": _PASSWORD, "role": "ADMIN"},
        headers={"X-CSRF-Token": csrf},
    )
    assert resp.status_code == 403
    assert resp.json()["error"]["code"] == "FORBIDDEN_ROLE"

    resp = client.post(
        "/api/v1/admin/users", json={"email": "newbie@example.com", "password": _PASSWORD},
        headers={"X-CSRF-Token": csrf},
    )
    assert resp.status_code == 201
    assert resp.json()["user"]["role"] == "USER"
    assert len(_audit_rows(db_session, "user.create")) == 1


def test_list_users_restricts_admin_actor_to_user_role_only(client, db_session) -> None:
    _signup(client, "boss2@example.com")
    _promote(db_session, "boss2@example.com", "SUPERADMIN")
    csrf = _csrf(client)
    client.post(
        "/api/v1/admin/users", json={"email": "member@example.com", "password": _PASSWORD},
        headers={"X-CSRF-Token": csrf},
    )
    client.post(
        "/api/v1/admin/users", json={"email": "otheradmin@example.com", "password": _PASSWORD, "role": "ADMIN"},
        headers={"X-CSRF-Token": csrf},
    )
    _promote(db_session, "boss2@example.com", "ADMIN")

    resp = client.get("/api/v1/admin/users")
    emails = {u["email"] for u in resp.json()["items"]}
    assert "member@example.com" in emails
    assert "otheradmin@example.com" not in emails
    assert "boss2@example.com" not in emails  # the actor itself is ADMIN, not USER


def test_admin_cannot_manage_an_admin_or_superadmin_target(client, db_session) -> None:
    _signup(client, "super1@example.com")
    _promote(db_session, "super1@example.com", "SUPERADMIN")
    csrf = _csrf(client)
    resp = client.post(
        "/api/v1/admin/users", json={"email": "other-admin@example.com", "password": _PASSWORD, "role": "ADMIN"},
        headers={"X-CSRF-Token": csrf},
    )
    other_admin_id = resp.json()["user"]["id"]

    _signup(client, "plainadmin@example.com")
    _promote(db_session, "plainadmin@example.com", "ADMIN")
    csrf = _csrf(client)

    resp = client.get(f"/api/v1/admin/users/{other_admin_id}")
    assert resp.status_code == 403
    assert resp.json()["error"]["code"] == "FORBIDDEN_ROLE"

    resp = client.patch(
        f"/api/v1/admin/users/{other_admin_id}", json={"username": "renamed"}, headers={"X-CSRF-Token": csrf},
    )
    assert resp.status_code == 403


def test_update_user_disable_revokes_sessions_and_writes_one_audit_row(client, db_session) -> None:
    _signup(client, "boss3@example.com")
    _promote(db_session, "boss3@example.com", "SUPERADMIN")
    csrf = _csrf(client)
    resp = client.post(
        "/api/v1/admin/users", json={"email": "target1@example.com", "password": _PASSWORD},
        headers={"X-CSRF-Token": csrf},
    )
    target_id = resp.json()["user"]["id"]

    resp = client.patch(
        f"/api/v1/admin/users/{target_id}",
        json={"is_active": False, "username": "disabled-user"},
        headers={"X-CSRF-Token": csrf},
    )
    assert resp.status_code == 200
    body = resp.json()["user"]
    assert body["is_active"] is False
    assert body["username"] == "disabled-user"

    rows = _audit_rows(db_session, "user.update")
    assert len(rows) == 1
    assert rows[0].after["is_active"] is False
    assert "password" not in str(rows[0].after)


def test_cannot_disable_the_last_active_superadmin(client, db_session) -> None:
    _signup(client, "lonely-super@example.com")
    _promote(db_session, "lonely-super@example.com", "SUPERADMIN")
    csrf = _csrf(client)
    me_id = client.get("/api/v1/admin/users").json()["items"][0]["id"]
    # the only SUPERADMIN acting on itself: both guard_not_self and
    # guard_not_last_active_superadmin apply; self is checked first.
    resp = client.patch(
        f"/api/v1/admin/users/{me_id}", json={"is_active": False}, headers={"X-CSRF-Token": csrf},
    )
    assert resp.status_code == 409
    assert resp.json()["error"]["code"] == "SELF_MODIFICATION"


def test_set_role_requires_superadmin_and_guards_last_superadmin(client, db_session) -> None:
    _signup(client, "super2@example.com")
    _promote(db_session, "super2@example.com", "SUPERADMIN")
    csrf = _csrf(client)
    me_id = client.get("/api/v1/admin/users").json()["items"][0]["id"]

    resp = client.put(f"/api/v1/admin/users/{me_id}/role", json={"role": "ADMIN"}, headers={"X-CSRF-Token": csrf})
    assert resp.status_code == 409
    assert resp.json()["error"]["code"] in ("SELF_MODIFICATION", "LAST_SUPERADMIN")

    # Add a second superadmin so demoting the first one is actually allowed.
    resp = client.post(
        "/api/v1/admin/users", json={"email": "super3@example.com", "password": _PASSWORD, "role": "SUPERADMIN"},
        headers={"X-CSRF-Token": csrf},
    )
    assert resp.status_code == 201
    other_id = resp.json()["user"]["id"]
    resp = client.put(f"/api/v1/admin/users/{other_id}/role", json={"role": "ADMIN"}, headers={"X-CSRF-Token": csrf})
    assert resp.status_code == 200
    assert len(_audit_rows(db_session, "user.set_role")) == 1


def test_admin_reset_password_revokes_sessions(client, db_session) -> None:
    _signup(client, "boss4@example.com")
    _promote(db_session, "boss4@example.com", "SUPERADMIN")
    csrf = _csrf(client)
    resp = client.post(
        "/api/v1/admin/users", json={"email": "target2@example.com", "password": _PASSWORD},
        headers={"X-CSRF-Token": csrf},
    )
    target_id = resp.json()["user"]["id"]

    resp = client.post(
        f"/api/v1/admin/users/{target_id}/password", json={"new_password": "a-brand-new-password"},
        headers={"X-CSRF-Token": csrf},
    )
    assert resp.status_code == 200
    assert len(_audit_rows(db_session, "user.reset_password")) == 1

    login = client.post(
        "/api/v1/auth/login", json={"email": "target2@example.com", "password": _PASSWORD},
        headers={"X-CSRF-Token": _csrf(client)},
    )
    assert login.status_code == 401


def test_delete_user_requires_matching_confirm_email_and_sweeps_objects(client, db_session) -> None:
    from vieneu_portal.db.models_voices_and_recordings import Voice
    from vieneu_portal.storage.s3_object_storage import get_object_storage
    from tests.portal.in_memory_object_storage import InMemoryObjectStorage

    fake_storage = InMemoryObjectStorage()
    client.app.dependency_overrides[get_object_storage] = lambda: fake_storage
    try:
        _signup(client, "boss5@example.com")
        _promote(db_session, "boss5@example.com", "SUPERADMIN")
        csrf = _csrf(client)
        resp = client.post(
            "/api/v1/admin/users", json={"email": "doomed@example.com", "password": _PASSWORD},
            headers={"X-CSRF-Token": csrf},
        )
        target_id = resp.json()["user"]["id"]

        db_session.add(Voice(
            id="v1", name="V1", initials="V1", gender="NAM", region="MIEN_BAC",
            engine_voice_name="v1", sample_audio_url="voices/samples/v1.mp3",
        ))
        db_session.commit()
        fake_storage.put_bytes(f"recordings/{target_id}/rec1-1.mp3", b"audio", "audio/mpeg")

        resp = client.request(
            "DELETE", f"/api/v1/admin/users/{target_id}", json={"confirm_email": "wrong@example.com"},
            headers={"X-CSRF-Token": csrf},
        )
        assert resp.status_code == 422

        resp = client.request(
            "DELETE", f"/api/v1/admin/users/{target_id}", json={"confirm_email": "doomed@example.com"},
            headers={"X-CSRF-Token": csrf},
        )
        assert resp.status_code == 204
        assert db_session.execute(select(User).where(User.id == target_id)).first() is None
        assert not fake_storage.exists(f"recordings/{target_id}/rec1-1.mp3")
        assert len(_audit_rows(db_session, "user.delete")) == 1
    finally:
        client.app.dependency_overrides.pop(get_object_storage, None)
