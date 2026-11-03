"""`/api/v1/admin/voices*`: catalog edits (incl. inactive voices), magic-byte
sniffed avatar/sample uploads, and sample re-render through the engine
double.
"""
from __future__ import annotations

from sqlalchemy import select, update

from vieneu_portal.config import get_settings
from vieneu_portal.db.models_admin_audit_log import AdminAuditLog
from vieneu_portal.db.models_users_and_sessions import User
from vieneu_portal.db.models_voices_and_recordings import Voice
from vieneu_portal.engine.engine_http_client import EngineClient
from vieneu_portal.storage.s3_object_storage import get_object_storage

from tests.portal.in_memory_object_storage import InMemoryObjectStorage

_PASSWORD = "correct horse battery"

# Minimal valid magic bytes for each sniffed type.
_PNG_BYTES = b"\x89PNG\r\n\x1a\n" + b"\x00" * 16
_WAV_HEADER = b"RIFF" + b"\x00\x00\x00\x00" + b"WAVE" + b"\x00" * 8


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


def _seed_voice(db_session, voice_id: str, *, is_active: bool = True) -> None:
    db_session.add(Voice(
        id=voice_id, name=voice_id, initials="VV", gender="NAM", region="MIEN_BAC",
        engine_voice_name=voice_id, sample_audio_url=f"voices/samples/{voice_id}.mp3", is_active=is_active,
    ))
    db_session.commit()


def test_list_includes_inactive_voices(client, db_session) -> None:
    fake_storage = InMemoryObjectStorage()
    client.app.dependency_overrides[get_object_storage] = lambda: fake_storage
    try:
        csrf = _signup_admin(client, db_session, "boss@example.com")
        _seed_voice(db_session, "active-v")
        _seed_voice(db_session, "inactive-v", is_active=False)

        resp = client.get("/api/v1/admin/voices")
        assert resp.status_code == 200
        ids = {v["id"] for v in resp.json()["items"]}
        assert ids == {"active-v", "inactive-v"}
    finally:
        client.app.dependency_overrides.pop(get_object_storage, None)


def test_update_voice_fields_writes_one_audit_row(client, db_session) -> None:
    fake_storage = InMemoryObjectStorage()
    client.app.dependency_overrides[get_object_storage] = lambda: fake_storage
    try:
        csrf = _signup_admin(client, db_session, "boss2@example.com")
        _seed_voice(db_session, "editable-v")

        resp = client.patch(
            "/api/v1/admin/voices/editable-v", json={"name": "New Name", "sort_order": 3, "is_active": False},
            headers={"X-CSRF-Token": csrf},
        )
        assert resp.status_code == 200
        body = resp.json()["voice"]
        assert body["name"] == "New Name"
        assert body["is_active"] is False

        rows = list(db_session.execute(select(AdminAuditLog).where(AdminAuditLog.action == "voice.update")).scalars())
        assert len(rows) == 1
        assert rows[0].before["name"] == "editable-v"
        assert rows[0].after["name"] == "New Name"
    finally:
        client.app.dependency_overrides.pop(get_object_storage, None)


def test_avatar_upload_sniffs_type_and_rejects_fake_image(client, db_session) -> None:
    fake_storage = InMemoryObjectStorage()
    client.app.dependency_overrides[get_object_storage] = lambda: fake_storage
    try:
        csrf = _signup_admin(client, db_session, "boss3@example.com")
        _seed_voice(db_session, "avatar-v")

        resp = client.put(
            "/api/v1/admin/voices/avatar-v/avatar", headers={"X-CSRF-Token": csrf},
            files={"file": ("fake.png", b"<html>not really a png</html>", "image/png")},
        )
        assert resp.status_code == 422
        assert resp.json()["error"]["code"] == "UNSUPPORTED_FILE_TYPE"

        resp = client.put(
            "/api/v1/admin/voices/avatar-v/avatar", headers={"X-CSRF-Token": csrf},
            files={"file": ("real.png", _PNG_BYTES, "image/png")},
        )
        assert resp.status_code == 200
        key = resp.json()["voice"]["avatar_url"]
        assert "voices/avatars/avatar-v.png" in key
        assert fake_storage.exists("voices/avatars/avatar-v.png")

        resp = client.delete("/api/v1/admin/voices/avatar-v/avatar", headers={"X-CSRF-Token": csrf})
        assert resp.status_code == 200
        assert resp.json()["voice"]["avatar_url"] is None
        assert not fake_storage.exists("voices/avatars/avatar-v.png")
    finally:
        client.app.dependency_overrides.pop(get_object_storage, None)


def test_sample_upload_sniffs_wav_and_rejects_oversize(client, db_session) -> None:
    fake_storage = InMemoryObjectStorage()
    client.app.dependency_overrides[get_object_storage] = lambda: fake_storage
    try:
        csrf = _signup_admin(client, db_session, "boss4@example.com")
        _seed_voice(db_session, "sample-v")

        resp = client.put(
            "/api/v1/admin/voices/sample-v/sample", headers={"X-CSRF-Token": csrf},
            files={"file": ("sample.wav", _WAV_HEADER, "audio/wav")},
        )
        assert resp.status_code == 200
        key = resp.json()["voice"]["sample_audio_url"]
        assert key is not None

        too_big = b"RIFF" + b"\x00\x00\x00\x00" + b"WAVE" + (b"\x00" * (5 * 1024 * 1024 + 10))
        resp = client.put(
            "/api/v1/admin/voices/sample-v/sample", headers={"X-CSRF-Token": csrf},
            files={"file": ("big.wav", too_big, "audio/wav")},
        )
        assert resp.status_code == 422
        assert resp.json()["error"]["code"] == "FILE_TOO_LARGE"
    finally:
        client.app.dependency_overrides.pop(get_object_storage, None)


def test_render_sample_uses_engine_double_and_writes_audit_row(client, db_session, monkeypatch) -> None:
    fake_storage = InMemoryObjectStorage()
    client.app.dependency_overrides[get_object_storage] = lambda: fake_storage

    class FakeRendered:
        audio = b"fake-mp3-bytes"
        duration_seconds = 1.23
        sample_rate = 24000

    def fake_render(self, text, engine_voice_name, speed=1.0, fmt="mp3", timeout=None):
        return FakeRendered()

    monkeypatch.setattr(EngineClient, "render", fake_render)
    monkeypatch.setenv("VIENEU_PORTAL_ENGINE_URL", "http://engine.invalid")
    monkeypatch.setenv("VIENEU_PORTAL_ENGINE_SERVICE_KEY", "test-key")
    get_settings.cache_clear()
    try:
        csrf = _signup_admin(client, db_session, "boss5@example.com")
        _seed_voice(db_session, "render-v")

        resp = client.post(
            "/api/v1/admin/voices/render-v/sample/render", json={"text": "xin chào"},
            headers={"X-CSRF-Token": csrf},
        )
        assert resp.status_code == 200
        key = resp.json()["voice"]["sample_audio_url"]
        assert key is not None

        rows = list(
            db_session.execute(select(AdminAuditLog).where(AdminAuditLog.action == "voice.sample_render")).scalars()
        )
        assert len(rows) == 1
        assert rows[0].after["duration_seconds"] == 1.23
    finally:
        client.app.dependency_overrides.pop(get_object_storage, None)
        get_settings.cache_clear()
