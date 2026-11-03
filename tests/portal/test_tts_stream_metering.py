"""`POST /tts/stream`: charges exactly once, after the last chunk; a
truncated engine body mid-stream charges nothing; the lease is always
released afterward.
"""
from __future__ import annotations

from sqlalchemy import select

from tests.portal.engine_double_asgi_app import SERVICE_KEY, EngineDoubleState, run_engine_double_server
from vieneu_portal.config import get_settings
from vieneu_portal.db.models_users_and_sessions import User
from vieneu_portal.db.models_voices_and_recordings import TTSRecording, Voice

_PASSWORD = "correct horse battery"


def _csrf(client) -> str:
    return client.get("/api/v1/auth/csrf").json()["csrf_token"]


def _signup_and_accept_terms(client, email: str) -> None:
    resp = client.post("/api/v1/auth/signup", json={"email": email, "password": _PASSWORD}, headers={"X-CSRF-Token": _csrf(client)})
    assert resp.status_code == 201
    settings = get_settings()
    resp2 = client.post(
        "/api/v1/user/terms/accept", json={"terms_version": settings.TERMS_VERSION}, headers={"X-CSRF-Token": _csrf(client)}
    )
    assert resp2.status_code == 200


def _seed_voice(db_session, voice_id: str = "stream-voice") -> Voice:
    voice = Voice(
        id=voice_id, name="Stream Voice", initials="SV", gender="NAM", region="MIEN_BAC",
        engine_voice_name="Hải Đăng", sample_audio_url=f"voices/samples/{voice_id}.mp3",
        sample_object_key=f"voices/samples/{voice_id}.mp3", sort_order=0,
    )
    db_session.add(voice)
    db_session.commit()
    return voice


def _point_engine_at(monkeypatch, base_url: str) -> None:
    monkeypatch.setenv("VIENEU_PORTAL_ENGINE_URL", base_url)
    monkeypatch.setenv("VIENEU_PORTAL_ENGINE_SERVICE_KEY", SERVICE_KEY)
    get_settings.cache_clear()


def test_stream_success_charges_once(client, db_session, monkeypatch) -> None:
    _signup_and_accept_terms(client, "stream-ok@example.com")
    voice = _seed_voice(db_session)
    user = db_session.execute(select(User).where(User.email == "stream-ok@example.com")).scalar_one()
    balance_before = user.token_balance

    state = EngineDoubleState()
    try:
        with run_engine_double_server(state) as base_url:
            _point_engine_at(monkeypatch, base_url)
            with client.stream(
                "POST", "/api/v1/tts/stream", json={"voice_id": voice.id, "text": "Xin chào."},
                headers={"X-CSRF-Token": _csrf(client)},
            ) as resp:
                assert resp.status_code == 200
                body = b"".join(resp.iter_bytes())
        assert len(body) > 0
    finally:
        get_settings.cache_clear()

    db_session.expire_all()
    user_after = db_session.get(User, user.id)
    assert user_after.token_balance < balance_before
    assert user_after.synthesis_lock_until is None
    assert db_session.execute(select(TTSRecording)).first() is None   # streams never create a recording row


def test_stream_truncated_body_charges_nothing(client, db_session, monkeypatch) -> None:
    _signup_and_accept_terms(client, "stream-truncated@example.com")
    voice = _seed_voice(db_session)
    user = db_session.execute(select(User).where(User.email == "stream-truncated@example.com")).scalar_one()
    balance_before = user.token_balance

    state = EngineDoubleState(truncate_stream=True)
    try:
        with run_engine_double_server(state) as base_url:
            _point_engine_at(monkeypatch, base_url)
            with client.stream(
                "POST", "/api/v1/tts/stream", json={"voice_id": voice.id, "text": "Xin chào."},
                headers={"X-CSRF-Token": _csrf(client)},
            ) as resp:
                try:
                    for _ in resp.iter_bytes():
                        pass
                except Exception:   # noqa: BLE001 - the truncation itself may surface as a read error
                    pass
    finally:
        get_settings.cache_clear()

    db_session.expire_all()
    user_after = db_session.get(User, user.id)
    assert user_after.token_balance == balance_before   # nothing charged
    assert user_after.synthesis_lock_until is None   # lease still released


def test_stream_requires_terms_accepted(client, db_session, monkeypatch) -> None:
    resp = client.post("/api/v1/auth/signup", json={"email": "stream-no-terms@example.com", "password": _PASSWORD}, headers={"X-CSRF-Token": _csrf(client)})
    assert resp.status_code == 201
    voice = _seed_voice(db_session)
    resp2 = client.post(
        "/api/v1/tts/stream", json={"voice_id": voice.id, "text": "x"}, headers={"X-CSRF-Token": _csrf(client)}
    )
    assert resp2.status_code == 403 and resp2.json()["error"]["code"] == "TERMS_NOT_ACCEPTED"
