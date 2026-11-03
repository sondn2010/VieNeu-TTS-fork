"""`POST /tts/stream`: proxies the engine's PCM16 stream (24 kHz) with no DB
session held while the engine renders; charges exactly once, after the last
chunk — a client disconnect, an engine error or a truncated engine body
mid-stream never charges. No recording row is created (streams never appear
in the library).

The route must be `async def` to proxy an async generator, so unlike the
other TTS routes (plain `def`, auto-threadpooled by Starlette) the blocking
setup here — DB reads, `build_engine_text`, the lease acquire — is pushed
onto a worker thread explicitly via `run_in_threadpool`, so it never blocks
the event loop while other streams are in flight.
"""
from __future__ import annotations

import logging

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from starlette.concurrency import run_in_threadpool

from ..auth.session_dependencies import AuthContext, require_csrf, require_user
from ..config import Settings, get_settings
from ..db.session_factory import get_db, get_sessionmaker
from ..dictionaries.rules_for_synthesis_loader import load_rules_for_synthesis
from ..engine.engine_http_client import EngineClient
from ..errors import PortalError
from ..moderation.moderation_provider_factory import build_moderation_provider
from ..moderation.moderation_provider_interface import ContentPolicyViolation, ModerationUnavailable
from ..text.engine_text_pipeline import EngineText, TextTooLongAfterProcessing, build_engine_text
from .quota_precheck_and_atomic_charge import charge_or_none, precheck_quota
from .request_models_and_validation import StreamRequest, get_active_voice_or_422, validate_text_length
from .user_synthesis_lease import acquire_lease, release_lease

log = logging.getLogger("vieneu.portal.tts")

router = APIRouter()

STREAM_SAMPLE_RATE = 24_000


def _prepare_stream(db: Session, ctx: AuthContext, payload: StreamRequest, settings: Settings):
    """Every blocking step, run via `run_in_threadpool` from the route
    below. Commits the lease acquisition before returning, same as the
    generate route."""
    user = ctx.user
    if not (user.has_accepted_tts_terms and user.terms_version == settings.TERMS_VERSION):
        raise PortalError(403, "TERMS_NOT_ACCEPTED", "the current Terms must be accepted before generating audio")

    voice = get_active_voice_or_422(db, payload.voice_id)
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
    db.commit()
    return voice.engine_voice_name, engine_text, tokens


def _finish_stream(user_id, settings: Settings, engine_text: EngineText, tokens: int, charged: bool) -> None:
    db = get_sessionmaker()()
    try:
        if charged:
            charge_or_none(db, user_id, settings, chars=engine_text.char_count, tokens=tokens)
        release_lease(db, user_id)
        db.commit()
    finally:
        db.close()


@router.post("/tts/stream")
async def stream(
    payload: StreamRequest,
    db: Session = Depends(get_db),
    ctx: AuthContext = Depends(require_user),
    _csrf: None = Depends(require_csrf),
) -> StreamingResponse:
    settings = get_settings()
    engine_voice_name, engine_text, tokens = await run_in_threadpool(_prepare_stream, db, ctx, payload, settings)
    user_id = ctx.user.id
    engine_client = EngineClient(settings)

    async def body():
        charged = False
        try:
            async for chunk in engine_client.open_stream(engine_text.processed_text, engine_voice_name, STREAM_SAMPLE_RATE):
                yield chunk
            charged = True
        finally:
            await run_in_threadpool(_finish_stream, user_id, settings, engine_text, tokens, charged)

    headers = {"X-Sample-Rate": str(STREAM_SAMPLE_RATE), "Cache-Control": "no-store"}
    return StreamingResponse(body(), media_type="audio/pcm", headers=headers)
