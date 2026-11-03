"""`/api/v1/admin/users/{id}/api-keys*` and `/admin/users/{id}/recordings`,
`/admin/recordings/{id}`: never returns a key hash, lists `FAILED` rows too
(unlike the user-facing library), and listing another user's recordings
writes exactly one `user.recordings_view` row per request.
"""
from __future__ import annotations

from sqlalchemy import select, update

from vieneu_portal.db.models_admin_audit_log import AdminAuditLog
from vieneu_portal.db.models_developer_and_billing import DeveloperApiKey
from vieneu_portal.db.models_users_and_sessions import User
from vieneu_portal.db.models_voices_and_recordings import TTSRecording, Voice
from vieneu_portal.storage.s3_object_storage import get_object_storage

from tests.portal.in_memory_object_storage import InMemoryObjectStorage

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


def test_list_and_revoke_api_keys_never_leak_the_hash(client, db_session) -> None:
    _signup(client, "boss@example.com")
    _promote(db_session, "boss@example.com", "SUPERADMIN")
    csrf = _csrf(client)
    target_id = _create_target(client, csrf, "haskeys@example.com")

    key = DeveloperApiKey(
        user_id=target_id, name="ci key", environment="LIVE", key_prefix="vn_live_abcd",
        key_hash="x" * 64,
    )
    db_session.add(key)
    db_session.commit()

    resp = client.get(f"/api/v1/admin/users/{target_id}/api-keys")
    assert resp.status_code == 200
    items = resp.json()["items"]
    assert len(items) == 1
    assert items[0]["key_prefix"] == "vn_live_abcd"
    assert "key_hash" not in items[0]
    assert "x" * 64 not in str(items[0])

    resp = client.post(
        f"/api/v1/admin/users/{target_id}/api-keys/{items[0]['id']}/revoke", headers={"X-CSRF-Token": csrf}
    )
    assert resp.status_code == 200
    db_session.expire_all()
    assert db_session.get(DeveloperApiKey, key.id).revoked_at is not None
    rows = list(db_session.execute(select(AdminAuditLog).where(AdminAuditLog.action == "api_key.revoke")).scalars())
    assert len(rows) == 1


def _seed_voice(db_session, voice_id: str) -> None:
    db_session.add(Voice(
        id=voice_id, name=voice_id, initials="VV", gender="NAM", region="MIEN_BAC",
        engine_voice_name=voice_id, sample_audio_url=f"voices/samples/{voice_id}.mp3",
    ))
    db_session.commit()


def test_admin_recordings_view_includes_failed_rows_and_audits_once_per_list(client, db_session) -> None:
    client.app.dependency_overrides[get_object_storage] = lambda: InMemoryObjectStorage()
    try:
        _signup(client, "boss2@example.com")
        _promote(db_session, "boss2@example.com", "SUPERADMIN")
        csrf = _csrf(client)
        target_id = _create_target(client, csrf, "haverecordings@example.com")
        _seed_voice(db_session, "v1")

        db_session.add_all([
            TTSRecording(
                user_id=target_id, voice_id="v1", original_text="ok one", speed=1, char_count=6, tokens_consumed=1,
                status="SUCCESS", duration_seconds=1.0,
            ),
            TTSRecording(
                user_id=target_id, voice_id="v1", original_text="broke", speed=1, char_count=5, tokens_consumed=0,
                status="FAILED", error_code="ENGINE_UNAVAILABLE",
            ),
        ])
        db_session.commit()

        resp = client.get(f"/api/v1/admin/users/{target_id}/recordings")
        assert resp.status_code == 200
        body = resp.json()
        statuses = {item["status"] for item in body["items"]}
        assert statuses == {"SUCCESS", "FAILED"}
        failed = next(item for item in body["items"] if item["status"] == "FAILED")
        assert failed["error_code"] == "ENGINE_UNAVAILABLE"

        rows = list(
            db_session.execute(select(AdminAuditLog).where(AdminAuditLog.action == "user.recordings_view")).scalars()
        )
        assert len(rows) == 1

        # A second list call writes a second, independent row (one per request).
        client.get(f"/api/v1/admin/users/{target_id}/recordings")
        rows = list(
            db_session.execute(select(AdminAuditLog).where(AdminAuditLog.action == "user.recordings_view")).scalars()
        )
        assert len(rows) == 2
    finally:
        client.app.dependency_overrides.pop(get_object_storage, None)


def test_delete_recording_removes_object_and_audits(client, db_session) -> None:
    fake_storage = InMemoryObjectStorage()
    client.app.dependency_overrides[get_object_storage] = lambda: fake_storage
    try:
        _signup(client, "boss3@example.com")
        _promote(db_session, "boss3@example.com", "SUPERADMIN")
        csrf = _csrf(client)
        target_id = _create_target(client, csrf, "ownsrecording@example.com")
        _seed_voice(db_session, "v2")

        recording = TTSRecording(
            user_id=target_id, voice_id="v2", original_text="to delete", speed=1, char_count=9, tokens_consumed=1,
            status="SUCCESS", duration_seconds=2.0, audio_object_key="recordings/x/y.mp3",
        )
        db_session.add(recording)
        db_session.commit()
        recording_id = recording.id
        fake_storage.put_bytes("recordings/x/y.mp3", b"audio", "audio/mpeg")

        resp = client.delete(f"/api/v1/admin/recordings/{recording_id}", headers={"X-CSRF-Token": csrf})
        assert resp.status_code == 204
        assert not fake_storage.exists("recordings/x/y.mp3")
        db_session.expire_all()
        assert db_session.execute(select(TTSRecording).where(TTSRecording.id == recording_id)).first() is None
        rows = list(
            db_session.execute(select(AdminAuditLog).where(AdminAuditLog.action == "recording.delete")).scalars()
        )
        assert len(rows) == 1
    finally:
        client.app.dependency_overrides.pop(get_object_storage, None)
