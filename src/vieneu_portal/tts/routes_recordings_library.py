"""`GET /tts/recordings`, `GET /tts/recordings/{id}` (polling),
`DELETE /tts/recordings/{id}`. Every query is scoped by the session's
`user_id` — there is no IDOR surface.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..auth.session_dependencies import AuthContext, require_csrf, require_user
from ..config import get_settings
from ..db.models_users_and_sessions import User
from ..db.models_voices_and_recordings import TTSRecording
from ..db.session_factory import get_db
from ..errors import PortalError
from ..storage.object_storage_interface import ObjectStorage
from ..storage.s3_object_storage import get_object_storage
from .recording_serializer import serialize_recording
from .recordings_query import query_recordings_library

router = APIRouter()


@router.get("/tts/recordings")
def list_recordings(
    search: Optional[str] = None,
    voice_id: Optional[str] = None,
    page: int = 1,
    limit: int = 20,
    db: Session = Depends(get_db),
    ctx: AuthContext = Depends(require_user),
    storage: ObjectStorage = Depends(get_object_storage),
) -> dict:
    settings = get_settings()
    limit = min(max(limit, 1), 100)
    page = max(page, 1)
    result = query_recordings_library(db, ctx.user.id, search=search, voice_id=voice_id, page=page, limit=limit)
    return {
        "items": [serialize_recording(r, storage, settings) for r in result.items],
        "total_count": result.total_count,
        "overall_count": result.overall_count,
        "total_duration_seconds": result.total_duration_seconds,
        "voices_used": result.voices_used,
        "page": page,
        "limit": limit,
    }


def _get_own_recording_or_404(db: Session, ctx: AuthContext, recording_id: UUID) -> TTSRecording:
    recording = db.get(TTSRecording, recording_id)
    if recording is None or recording.user_id != ctx.user.id:
        raise PortalError(404, "NOT_FOUND", "recording not found")
    return recording


@router.get("/tts/recordings/{recording_id}")
def get_recording(
    recording_id: UUID,
    db: Session = Depends(get_db),
    ctx: AuthContext = Depends(require_user),
    storage: ObjectStorage = Depends(get_object_storage),
) -> dict:
    recording = _get_own_recording_or_404(db, ctx, recording_id)
    return {"recording": serialize_recording(recording, storage, get_settings())}


@router.delete("/tts/recordings/{recording_id}", status_code=204)
def delete_recording(
    recording_id: UUID,
    db: Session = Depends(get_db),
    ctx: AuthContext = Depends(require_user),
    storage: ObjectStorage = Depends(get_object_storage),
    _csrf: None = Depends(require_csrf),
) -> None:
    recording = _get_own_recording_or_404(db, ctx, recording_id)
    if recording.status == "PENDING":
        user = db.get(User, ctx.user.id)
        has_live_lease = user.synthesis_lock_until is not None and user.synthesis_lock_until > datetime.now(timezone.utc)
        if has_live_lease:
            raise PortalError(409, "RECORDING_IN_PROGRESS", "this recording is still being rendered")
        # The lease already expired: this row was abandoned (the serving
        # process died mid-request); fail it so it can be deleted.
        recording.status = "FAILED"
        recording.error_code = "ABANDONED"

    key = recording.audio_object_key or recording.audio_url
    db.delete(recording)
    db.commit()
    if key:
        try:
            storage.delete(key)
        except Exception:   # noqa: BLE001 - best-effort; the row is already gone
            pass
    return None
