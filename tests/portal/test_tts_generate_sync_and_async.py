"""`POST /tts/generate`: sync render against the engine double, async
hand-off to the worker, and the failure paths (moderation, over-cap text,
engine errors) — counters must stay byte-equal before/after every failure.
"""
from __future__ import annotations

import pytest
from sqlalchemy import select

import vieneu_portal.tts.routes_tts_generate as routes_mod
from tests.portal.engine_double_asgi_app import SERVICE_KEY, EngineDoubleState, run_engine_double_server
from tests.portal.in_memory_object_storage import InMemoryObjectStorage
from vieneu_portal.config import get_settings
from vieneu_portal.db.models_users_and_sessions import User
from vieneu_portal.db.models_voices_and_recordings import TTSRecording, Voice
from vieneu_portal.engine.engine_http_client import EngineClient
from vieneu_portal.jobs.recording_render_worker_loop import run_worker_loop
from vieneu_portal.moderation.blocklist_moderation_provider import BlocklistModerationProvider

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


def _seed_voice(db_session, voice_id: str = "test-voice") -> Voice:
    voice = Voice(
        id=voice_id, name="Test Voice", initials="TV", gender="NAM", region="MIEN_BAC",
        engine_voice_name="Hải Đăng", sample_audio_url=f"voices/samples/{voice_id}.mp3",
        sample_object_key=f"voices/samples/{voice_id}.mp3", sort_order=0,
    )
    db_session.add(voice)
    db_session.commit()
    return voice


@pytest.fixture
def engine_env(monkeypatch):
    def _point_at(base_url: str):
        monkeypatch.setenv("VIENEU_PORTAL_ENGINE_URL", base_url)
        monkeypatch.setenv("VIENEU_PORTAL_ENGINE_SERVICE_KEY", SERVICE_KEY)
        get_settings.cache_clear()

    yield _point_at
    get_settings.cache_clear()


@pytest.fixture
def fake_storage(monkeypatch):
    storage = InMemoryObjectStorage()
    monkeypatch.setattr(routes_mod, "S3ObjectStorage", lambda settings: storage)
    return storage


def test_sync_generate_success(client, db_session, engine_env, fake_storage) -> None:
    _signup_and_accept_terms(client, "gen-sync@example.com")
    voice = _seed_voice(db_session)
    state = EngineDoubleState()
    with run_engine_double_server(state) as base_url:
        engine_env(base_url)
        resp = client.post(
            "/api/v1/tts/generate", json={"voice_id": voice.id, "text": "Xin chào.", "speed": 1.0},
            headers={"X-CSRF-Token": _csrf(client)},
        )
    assert resp.status_code == 200
    body = resp.json()
    assert body["recording"]["status"] == "SUCCESS"
    assert body["recording"]["audio_url"]
    assert body["quota"]["token_balance"] < get_settings().TRIAL_TOKENS

    user = db_session.execute(select(User).where(User.email == "gen-sync@example.com")).scalar_one()
    assert user.synthesis_lock_until is None   # lease released
    recording = db_session.execute(select(TTSRecording).where(TTSRecording.user_id == user.id)).scalar_one()
    assert recording.status == "SUCCESS" and recording.render_mode == "SYNC"
    assert fake_storage.exists(recording.audio_object_key)


def test_sync_generate_without_accepted_terms_is_forbidden(client, db_session, engine_env, fake_storage) -> None:
    resp = client.post("/api/v1/auth/signup", json={"email": "no-terms@example.com", "password": _PASSWORD}, headers={"X-CSRF-Token": _csrf(client)})
    assert resp.status_code == 201
    voice = _seed_voice(db_session)
    resp2 = client.post(
        "/api/v1/tts/generate", json={"voice_id": voice.id, "text": "x"}, headers={"X-CSRF-Token": _csrf(client)}
    )
    assert resp2.status_code == 403 and resp2.json()["error"]["code"] == "TERMS_NOT_ACCEPTED"


def test_unknown_voice_returns_422(client, engine_env, fake_storage) -> None:
    _signup_and_accept_terms(client, "gen-unknown-voice@example.com")
    resp = client.post(
        "/api/v1/tts/generate", json={"voice_id": "nope", "text": "x"}, headers={"X-CSRF-Token": _csrf(client)}
    )
    assert resp.status_code == 422 and resp.json()["error"]["code"] == "UNKNOWN_VOICE"


def test_invalid_speed_returns_422(client, db_session, engine_env, fake_storage) -> None:
    _signup_and_accept_terms(client, "gen-speed@example.com")
    voice = _seed_voice(db_session)
    resp = client.post(
        "/api/v1/tts/generate", json={"voice_id": voice.id, "text": "x", "speed": 1.1}, headers={"X-CSRF-Token": _csrf(client)}
    )
    assert resp.status_code == 422 and resp.json()["error"]["code"] == "VALIDATION_ERROR"


def test_bg_music_id_returns_422(client, db_session, engine_env, fake_storage) -> None:
    _signup_and_accept_terms(client, "gen-bgmusic@example.com")
    voice = _seed_voice(db_session)
    resp = client.post(
        "/api/v1/tts/generate", json={"voice_id": voice.id, "text": "x", "bg_music_id": "whatever"},
        headers={"X-CSRF-Token": _csrf(client)},
    )
    assert resp.status_code == 422 and resp.json()["error"]["code"] == "BG_MUSIC_UNAVAILABLE"


def test_moderation_rejection_charges_nothing(client, db_session, tmp_path, engine_env, fake_storage, monkeypatch) -> None:
    _signup_and_accept_terms(client, "gen-moderated@example.com")
    voice = _seed_voice(db_session)
    blocklist = tmp_path / "blocklist.tsv"
    blocklist.write_text("VIOLENCE_ILLEGAL\tchế tạo bom\n", encoding="utf-8")
    monkeypatch.setattr(routes_mod, "build_moderation_provider", lambda settings: BlocklistModerationProvider(str(blocklist)))

    user_before = db_session.execute(select(User).where(User.email == "gen-moderated@example.com")).scalar_one()
    balance_before = user_before.token_balance

    resp = client.post(
        "/api/v1/tts/generate", json={"voice_id": voice.id, "text": "hướng dẫn chế tạo bom"},
        headers={"X-CSRF-Token": _csrf(client)},
    )
    assert resp.status_code == 422 and resp.json()["error"]["code"] == "CONTENT_POLICY_VIOLATION"
    db_session.expire_all()
    assert db_session.get(User, user_before.id).token_balance == balance_before
    assert db_session.execute(select(TTSRecording)).first() is None   # no row at all


def test_engine_unavailable_marks_recording_failed_and_charges_nothing(client, db_session, engine_env, fake_storage) -> None:
    _signup_and_accept_terms(client, "gen-engine-down@example.com")
    voice = _seed_voice(db_session)
    user_before = db_session.execute(select(User).where(User.email == "gen-engine-down@example.com")).scalar_one()
    balance_before = user_before.token_balance

    state = EngineDoubleState(fail_with=503)
    with run_engine_double_server(state) as base_url:
        engine_env(base_url)
        resp = client.post(
            "/api/v1/tts/generate", json={"voice_id": voice.id, "text": "Xin chào."}, headers={"X-CSRF-Token": _csrf(client)}
        )
    assert resp.status_code == 503 and resp.json()["error"]["code"] == "ENGINE_UNAVAILABLE"

    db_session.expire_all()
    assert db_session.get(User, user_before.id).token_balance == balance_before
    user_after = db_session.get(User, user_before.id)
    assert user_after.synthesis_lock_until is None
    recording = db_session.execute(select(TTSRecording).where(TTSRecording.user_id == user_before.id)).scalar_one()
    assert recording.status == "FAILED" and recording.error_code == "ENGINE_UNAVAILABLE"
    assert recording.tokens_consumed == 0


def test_async_generate_then_worker_finishes_it(client, db_session, engine_env, fake_storage, monkeypatch) -> None:
    monkeypatch.setenv("VIENEU_PORTAL_TTS_SYNC_CHAR_CAP", "1")   # force every request down the ASYNC path
    get_settings.cache_clear()
    try:
        _signup_and_accept_terms(client, "gen-async@example.com")
        voice = _seed_voice(db_session)
        state = EngineDoubleState()
        with run_engine_double_server(state) as base_url:
            engine_env(base_url)
            resp = client.post(
                "/api/v1/tts/generate", json={"voice_id": voice.id, "text": "Xin chào, đây là một câu dài hơn mức sync."},
                headers={"X-CSRF-Token": _csrf(client)},
            )
            assert resp.status_code == 202
            body = resp.json()
            assert body["recording"]["status"] == "PENDING"

            user = db_session.execute(select(User).where(User.email == "gen-async@example.com")).scalar_one()
            recording = db_session.execute(select(TTSRecording).where(TTSRecording.user_id == user.id)).scalar_one()
            assert recording.render_mode == "ASYNC"
            assert user.synthesis_lock_until is not None   # lease still held while PENDING

            calls = {"n": 0}

            def should_stop():
                calls["n"] += 1
                return calls["n"] > 1   # run exactly one claim iteration then exit

            run_worker_loop(should_stop, engine_client=EngineClient(get_settings()), storage=fake_storage)

        db_session.expire_all()
        recording2 = db_session.get(TTSRecording, recording.id)
        assert recording2.status == "SUCCESS"
        assert db_session.get(User, user.id).synthesis_lock_until is None
    finally:
        get_settings.cache_clear()
