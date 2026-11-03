"""`POST /tts/generate`: validates, moderates+normalizes the text, prechecks
quota, inserts a `PENDING` recording, then either renders it synchronously
(short text) or hands it to the worker (long text — `202` immediately).

A plain `def` route: FastAPI/Starlette already runs it in a worker thread,
so the blocking `build_engine_text` call and every DB round trip never
block the event loop — the same reasoning the stream route documents
explicitly because *it* has to be `async def`.
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, Response
from sqlalchemy.orm import Session

from ..auth.session_dependencies import AuthContext, require_csrf, require_user
from ..config import get_settings
from ..db.models_voices_and_recordings import TTSRecording
from ..db.session_factory import get_db
from ..dictionaries.rules_for_synthesis_loader import load_rules_for_synthesis
from ..engine.engine_http_client import EngineClient
from ..errors import PortalError
from ..moderation.moderation_provider_factory import build_moderation_provider
from ..moderation.moderation_provider_interface import ContentPolicyViolation, ModerationUnavailable
from ..storage.s3_object_storage import S3ObjectStorage
from ..text.engine_text_pipeline import TextTooLongAfterProcessing, build_engine_text
from .quota_precheck_and_atomic_charge import precheck_quota
from .recording_finalize_service import finalize_recording, mark_recording_failed_and_release_lease
from .recording_serializer import serialize_recording
from .request_models_and_validation import (
    GenerateRequest,
    get_active_voice_or_422,
    validate_bg_music,
    validate_speed,
    validate_text_length,
)
from .user_synthesis_lease import acquire_lease

log = logging.getLogger("vieneu.portal.tts")

router = APIRouter()


def _require_terms_accepted(ctx: AuthContext, settings) -> None:
    user = ctx.user
    if not (user.has_accepted_tts_terms and user.terms_version == settings.TERMS_VERSION):
        raise PortalError(403, "TERMS_NOT_ACCEPTED", "the current Terms must be accepted before generating audio")


@router.post("/tts/generate")
def generate(
    payload: GenerateRequest,
    response: Response,
    db: Session = Depends(get_db),
    ctx: AuthContext = Depends(require_user),
    _csrf: None = Depends(require_csrf),
) -> dict:
    settings = get_settings()
    user = ctx.user
    _require_terms_accepted(ctx, settings)

    voice = get_active_voice_or_422(db, payload.voice_id)
    validate_speed(payload.speed)
    validate_bg_music(payload.bg_music_id)
    validate_text_length(payload.text, settings)

    moderation = build_moderation_provider(settings)
    compiled = load_rules_for_synthesis(db, user.id)
    try:
        engine_text = build_engine_text(payload.text, compiled, moderation, settings)
    except ContentPolicyViolation as exc:
        raise PortalError(422, "CONTENT_POLICY_VIOLATION", exc.message, category=exc.category)
    except ModerationUnavailable as exc:
        raise PortalError(503, "MODERATION_UNAVAILABLE", str(exc))
    except TextTooLongAfterProcessing as exc:
        raise PortalError(422, "TEXT_TOO_LONG_AFTER_PROCESSING", str(exc))

    tokens = engine_text.estimated_tokens
    precheck_quota(user, settings, chars=engine_text.char_count, tokens=tokens)

    acquire_lease(db, user.id, settings.JOB_LEASE_SEC)

    render_mode = "ASYNC" if engine_text.processed_char_count > settings.TTS_SYNC_CHAR_CAP else "SYNC"
    now = datetime.now(timezone.utc)
    recording = TTSRecording(
        user_id=user.id, voice_id=voice.id, original_text=payload.text, processed_text=engine_text.processed_text,
        speed=payload.speed, char_count=engine_text.char_count, tokens_consumed=0, status="PENDING",
        source_module="STUDIO", render_mode=render_mode,
        locked_until=(now + timedelta(seconds=settings.JOB_LEASE_SEC)) if render_mode == "SYNC" else None,
    )
    db.add(recording)
    db.commit()

    if render_mode == "ASYNC":
        response.status_code = 202
        estimated_seconds = round(engine_text.processed_char_count * settings.ENGINE_SEC_PER_CHAR, 1)
        return {"recording": {"id": str(recording.id), "status": "PENDING", "estimated_seconds": estimated_seconds}}

    engine_client = EngineClient(settings)
    storage = S3ObjectStorage(settings)
    outcome = finalize_recording(recording.id, engine_client=engine_client, storage=storage, settings=settings, attempt=1)

    if outcome.kind == "SUCCESS":
        db.refresh(recording)
        return {"recording": serialize_recording(recording, storage, settings), "quota": outcome.quota}
    if outcome.kind == "ENGINE_BUSY":
        mark_recording_failed_and_release_lease(recording.id, "ENGINE_UNAVAILABLE")
        raise PortalError(503, "ENGINE_UNAVAILABLE", "the speech engine is busy; try again shortly", retry_after=2)
    if outcome.kind == "ENGINE_UNAVAILABLE":
        mark_recording_failed_and_release_lease(recording.id, "ENGINE_UNAVAILABLE")
        raise PortalError(503, "ENGINE_UNAVAILABLE", "the speech engine is unavailable", retry_after=5)
    if outcome.kind == "STORAGE_ERROR":
        mark_recording_failed_and_release_lease(recording.id, "STORAGE_ERROR")
        raise PortalError(502, "STORAGE_ERROR", "could not store the rendered audio")
    if outcome.kind == "ENGINE_REJECTED":
        raise PortalError(422, "ENGINE_REJECTED", "the engine rejected this request")
    if outcome.kind == "QUOTA_RACE":
        raise PortalError(402, "INSUFFICIENT_TOKENS", "quota changed before this request could be charged")
    raise PortalError(500, "INTERNAL_ERROR", f"unexpected finalize outcome: {outcome.kind}")   # pragma: no cover
