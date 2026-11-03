"""The ASYNC recording queue: `SKIP LOCKED` claiming, the engine-busy
backoff that never consumes an attempt, `WORKER_MAX_ATTEMPTS` exhaustion,
and the abandoned-SYNC-row sweep.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from decimal import Decimal

from sqlalchemy import select

from tests.portal.engine_double_asgi_app import SERVICE_KEY, EngineDoubleState, run_engine_double_server
from tests.portal.in_memory_object_storage import InMemoryObjectStorage
from vieneu_portal.config import get_settings
from vieneu_portal.db.models_users_and_sessions import User
from vieneu_portal.db.models_voices_and_recordings import TTSRecording, Voice
from vieneu_portal.db.session_factory import get_sessionmaker
from vieneu_portal.engine.engine_http_client import EngineClient
from vieneu_portal.jobs.recording_render_queue import claim_next_recording, sweep_abandoned_sync_recordings
from vieneu_portal.jobs.recording_render_worker_loop import run_worker_loop
from vieneu_portal.tts.user_synthesis_lease import acquire_lease


def _make_user(db_session, email: str) -> User:
    user = User(
        email=email, username=email.split("@")[0], password_hash="scrypt$16384$8$1$x$y",
        token_balance=1000, token_quota_total=1000, daily_char_limit=1000, daily_char_remaining=1000,
        has_accepted_tts_terms=True, terms_version=get_settings().TERMS_VERSION,
    )
    db_session.add(user)
    db_session.flush()
    return user


def _make_voice(db_session, voice_id: str) -> Voice:
    voice = Voice(
        id=voice_id, name=voice_id, initials="XX", gender="NAM", region="MIEN_BAC",
        engine_voice_name="Hải Đăng", sample_audio_url=f"voices/samples/{voice_id}.mp3",
        sample_object_key=f"voices/samples/{voice_id}.mp3", sort_order=0,
    )
    db_session.add(voice)
    db_session.flush()
    return voice


def _make_async_recording(db_session, user, voice) -> TTSRecording:
    recording = TTSRecording(
        user_id=user.id, voice_id=voice.id, original_text="Xin chào.", processed_text="Xin chào.",
        char_count=9, tokens_consumed=0, status="PENDING", render_mode="ASYNC",
    )
    db_session.add(recording)
    db_session.flush()
    return recording


def test_claim_returns_none_when_queue_is_empty(db_session) -> None:
    assert claim_next_recording(db_session, lease_sec=60) is None


def test_claim_increments_attempts_and_sets_locked_until(db_session) -> None:
    user = _make_user(db_session, "claim1@example.com")
    voice = _make_voice(db_session, "claim-voice-1")
    recording = _make_async_recording(db_session, user, voice)
    db_session.commit()

    claimed = claim_next_recording(db_session, lease_sec=60)
    db_session.commit()
    assert claimed.id == recording.id and claimed.attempts == 1

    db_session.expire_all()
    row = db_session.get(TTSRecording, recording.id)
    assert row.locked_until is not None and row.locked_until > datetime.now(timezone.utc)


def test_claim_skips_a_row_locked_by_another_session(db_session, portal_database_url) -> None:
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

    from vieneu_portal.config import to_sqlalchemy_url

    user = _make_user(db_session, "claim2@example.com")
    voice = _make_voice(db_session, "claim-voice-2")
    _make_async_recording(db_session, user, voice)
    db_session.commit()

    engine = create_engine(to_sqlalchemy_url(portal_database_url))
    Session_ = sessionmaker(bind=engine)
    holder = Session_()
    try:
        held = claim_next_recording(holder, lease_sec=60)   # claims and holds the row lock, never commits
        assert held is not None

        other = Session_()
        try:
            assert claim_next_recording(other, lease_sec=60) is None   # the only row is locked elsewhere
            other.commit()
        finally:
            other.close()
    finally:
        holder.rollback()
        holder.close()
        engine.dispose()


def test_engine_busy_releases_claim_without_consuming_an_attempt(db_session, monkeypatch) -> None:
    user = _make_user(db_session, "claim3@example.com")
    acquire_lease(db_session, user.id, lease_sec=600)
    voice = _make_voice(db_session, "claim-voice-3")
    recording = _make_async_recording(db_session, user, voice)
    db_session.commit()

    state = EngineDoubleState(fail_with=429)
    with run_engine_double_server(state) as base_url:
        monkeypatch.setenv("VIENEU_PORTAL_ENGINE_URL", base_url)
        monkeypatch.setenv("VIENEU_PORTAL_ENGINE_SERVICE_KEY", SERVICE_KEY)
        get_settings.cache_clear()
        try:
            settings = get_settings()
            engine_client = EngineClient(settings)
            storage = InMemoryObjectStorage()
            calls = {"n": 0}
            run_worker_loop(lambda: (calls.__setitem__("n", calls["n"] + 1), calls["n"] > 1)[1],
                             engine_client=engine_client, storage=storage)
        finally:
            get_settings.cache_clear()

    db_session.expire_all()
    row = db_session.get(TTSRecording, recording.id)
    assert row.status == "PENDING"   # never marked FAILED for a busy engine
    assert row.attempts == 0         # the busy attempt was not consumed
    assert db_session.get(User, user.id).synthesis_lock_until is not None   # lease still held, job still "in progress"


def test_persistent_engine_failure_gives_up_after_max_attempts(db_session, monkeypatch) -> None:
    monkeypatch.setenv("VIENEU_PORTAL_WORKER_MAX_ATTEMPTS", "1")
    db = get_sessionmaker()()
    try:
        user = _make_user(db, "claim4@example.com")
        acquire_lease(db, user.id, lease_sec=600)
        voice = _make_voice(db, "claim-voice-4")
        recording = _make_async_recording(db, user, voice)
        db.commit()
    finally:
        db.close()

    state = EngineDoubleState(fail_with=503)
    with run_engine_double_server(state) as base_url:
        monkeypatch.setenv("VIENEU_PORTAL_ENGINE_URL", base_url)
        monkeypatch.setenv("VIENEU_PORTAL_ENGINE_SERVICE_KEY", SERVICE_KEY)
        get_settings.cache_clear()
        try:
            settings = get_settings()
            engine_client = EngineClient(settings)
            storage = InMemoryObjectStorage()
            calls = {"n": 0}
            run_worker_loop(lambda: (calls.__setitem__("n", calls["n"] + 1), calls["n"] > 1)[1],
                             engine_client=engine_client, storage=storage)
        finally:
            get_settings.cache_clear()

    db2 = get_sessionmaker()()
    try:
        row = db2.get(TTSRecording, recording.id)
        assert row.status == "FAILED" and row.error_code == "ENGINE_UNAVAILABLE"
        assert db2.get(User, user.id).synthesis_lock_until is None
    finally:
        db2.close()


def test_sweep_abandoned_sync_recordings_fails_and_releases_lease(db_session) -> None:
    user = _make_user(db_session, "sweep1@example.com")
    user.synthesis_lock_until = datetime.now(timezone.utc) + timedelta(hours=1)
    voice = _make_voice(db_session, "sweep-voice-1")
    recording = TTSRecording(
        user_id=user.id, voice_id=voice.id, original_text="x", processed_text="x", char_count=1,
        tokens_consumed=0, status="PENDING", render_mode="SYNC",
        locked_until=datetime.now(timezone.utc) - timedelta(seconds=1),
    )
    db_session.add(recording)
    db_session.commit()

    swept = sweep_abandoned_sync_recordings(db_session)
    assert swept == 1

    db_session.expire_all()
    row = db_session.get(TTSRecording, recording.id)
    assert row.status == "FAILED" and row.error_code == "ABANDONED"
    assert db_session.get(User, user.id).synthesis_lock_until is None
