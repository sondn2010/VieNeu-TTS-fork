"""Finalizes one render attempt of a `tts_recordings` row — shared,
byte-for-byte, by the sync `POST /tts/generate` route and the async worker.

The recording row is both the queue item and the idempotency guard:
finalize locks it (`SELECT ... FOR UPDATE WHERE status = 'PENDING'`) right
before charging; if it is no longer `PENDING` (another attempt already won,
or it was deleted), this attempt stops without charging or touching
objects. No DB session is held across the engine or storage call (phase 1
discipline): fetch in a short session, call out, then open a new short
session to charge and finalize.

`ENGINE_BUSY`, `ENGINE_UNAVAILABLE` and `STORAGE_ERROR` are returned
*without* marking the row FAILED or releasing the lease — whether that is
worth retrying depends on the caller (the sync route never retries; the
worker retries up to `WORKER_MAX_ATTEMPTS`), so the caller decides and, if
it gives up, calls `mark_recording_failed_and_release_lease` itself.
`ENGINE_REJECTED` and `QUOTA_RACE` are never worth retrying either way, so
this module marks them FAILED itself.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..config import Settings
from ..db.models_voices_and_recordings import TTSRecording, Voice
from ..db.session_factory import get_sessionmaker
from ..engine.engine_http_client import EngineBusy, EngineClient, EngineRejected, EngineUnavailable
from ..storage.object_storage_interface import ObjectStorage
from ..text.character_count_and_token_estimate import estimate_tokens
from .quota_precheck_and_atomic_charge import charge_or_none
from .user_synthesis_lease import release_lease


@dataclass(frozen=True)
class FinalizeOutcome:
    kind: str   # 'SUCCESS' | 'ENGINE_BUSY' | 'ENGINE_UNAVAILABLE' | 'ENGINE_REJECTED' | 'STORAGE_ERROR' | 'QUOTA_RACE' | 'ALREADY_FINALIZED'
    recording_id: object = None
    quota: Optional[dict] = None


def _open_session() -> Session:
    return get_sessionmaker()()


def mark_recording_failed_and_release_lease(recording_id, error_code: str) -> None:
    """For the caller to call when it decides a transient outcome
    (`ENGINE_BUSY`/`ENGINE_UNAVAILABLE`/`STORAGE_ERROR`) is final after all —
    the sync route always calls this immediately; the worker only after
    exhausting `WORKER_MAX_ATTEMPTS`.
    """
    db = _open_session()
    try:
        recording = db.execute(
            select(TTSRecording).where(TTSRecording.id == recording_id, TTSRecording.status == "PENDING").with_for_update()
        ).scalar_one_or_none()
        if recording is None:
            db.rollback()
            return
        recording.status = "FAILED"
        recording.error_code = error_code
        release_lease(db, recording.user_id)
        db.commit()
    finally:
        db.close()


def finalize_recording(
    recording_id, *, engine_client: EngineClient, storage: ObjectStorage, settings: Settings, attempt: int,
) -> FinalizeOutcome:
    db = _open_session()
    try:
        recording = db.execute(select(TTSRecording).where(TTSRecording.id == recording_id)).scalar_one_or_none()
        if recording is None or recording.status != "PENDING":
            return FinalizeOutcome(kind="ALREADY_FINALIZED", recording_id=recording_id)
        voice = db.get(Voice, recording.voice_id)
        user_id = recording.user_id
        processed_text = recording.processed_text or recording.original_text
        speed = float(recording.speed)
        char_count = recording.char_count
        engine_voice_name = voice.engine_voice_name if voice is not None else None
    finally:
        db.close()

    try:
        rendered = engine_client.render(processed_text, engine_voice_name, speed=speed, fmt="mp3")
    except EngineBusy:
        return FinalizeOutcome(kind="ENGINE_BUSY", recording_id=recording_id)
    except EngineRejected:
        mark_recording_failed_and_release_lease(recording_id, "ENGINE_REJECTED")
        return FinalizeOutcome(kind="ENGINE_REJECTED", recording_id=recording_id)
    except EngineUnavailable:
        return FinalizeOutcome(kind="ENGINE_UNAVAILABLE", recording_id=recording_id)

    key = f"recordings/{user_id}/{recording_id}-{attempt}.mp3"
    try:
        storage.put_bytes(key, rendered.audio, "audio/mpeg")
    except Exception:   # noqa: BLE001 - any storage failure here is STORAGE_ERROR
        return FinalizeOutcome(kind="STORAGE_ERROR", recording_id=recording_id)

    db = _open_session()
    try:
        recording = db.execute(
            select(TTSRecording).where(TTSRecording.id == recording_id, TTSRecording.status == "PENDING").with_for_update()
        ).scalar_one_or_none()
        if recording is None:
            db.rollback()
            storage.delete(key)   # a losing attempt can only delete what it wrote
            return FinalizeOutcome(kind="ALREADY_FINALIZED", recording_id=recording_id)

        tokens = estimate_tokens(char_count, settings.TOKENS_PER_CHAR_MILLI)
        charge_row = charge_or_none(db, user_id, settings, chars=char_count, tokens=tokens)
        if charge_row is None:
            recording.status = "FAILED"
            recording.error_code = "QUOTA_RACE"
            release_lease(db, user_id)
            db.commit()
            storage.delete(key)
            return FinalizeOutcome(kind="QUOTA_RACE", recording_id=recording_id)

        recording.status = "SUCCESS"
        recording.tokens_consumed = tokens
        recording.duration_seconds = rendered.duration_seconds
        recording.audio_object_key = key
        recording.audio_url = key
        release_lease(db, user_id)
        db.commit()
        token_balance, token_quota_total, daily_char_remaining = charge_row
        return FinalizeOutcome(
            kind="SUCCESS", recording_id=recording_id,
            quota={
                "token_balance": token_balance, "token_quota_total": token_quota_total,
                "daily_char_remaining": daily_char_remaining,
            },
        )
    finally:
        db.close()
