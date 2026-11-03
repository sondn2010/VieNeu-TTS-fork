"""`/api/v1/admin/users/{id}/api-keys*` and recordings (read-only + delete).
Listing another user's recordings writes one `user.recordings_view` audit
row per request (not per presigned URL).
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..admin_services.admin_audit_log_writer import write_admin_audit
from ..auth.session_dependencies import AuthContext, get_client_ip, require_admin, require_csrf
from ..config import get_settings
from ..db.models_developer_and_billing import DeveloperApiKey
from ..db.models_voices_and_recordings import TTSRecording
from ..db.session_factory import get_db
from ..errors import PortalError
from ..storage.object_storage_interface import ObjectStorage
from ..storage.s3_object_storage import get_object_storage
from ..tts.recording_serializer import serialize_recording
from ..tts.recordings_query import query_recordings_library
from .admin_shared_helpers import get_target_user_or_404, require_actor_can_manage_target

router = APIRouter()

RECORDING_STATUSES = ("SUCCESS", "PENDING", "FAILED")


def serialize_api_key(key: DeveloperApiKey) -> dict:
    return {
        "id": str(key.id), "name": key.name, "environment": key.environment, "key_prefix": key.key_prefix,
        "created_at": key.created_at, "last_used_at": key.last_used_at, "revoked_at": key.revoked_at,
    }


@router.get("/admin/users/{user_id}/api-keys")
def list_api_keys(
    user_id: UUID, db: Session = Depends(get_db), ctx: AuthContext = Depends(require_admin),
) -> dict:
    target = get_target_user_or_404(db, user_id)
    require_actor_can_manage_target(ctx.user, target)
    rows = list(
        db.execute(
            select(DeveloperApiKey).where(DeveloperApiKey.user_id == target.id).order_by(DeveloperApiKey.created_at.desc())
        ).scalars()
    )
    return {"items": [serialize_api_key(k) for k in rows]}


@router.post("/admin/users/{user_id}/api-keys/{key_id}/revoke")
def revoke_api_key(
    user_id: UUID, key_id: UUID, request: Request,
    db: Session = Depends(get_db), ctx: AuthContext = Depends(require_admin), _csrf: None = Depends(require_csrf),
) -> dict:
    target = get_target_user_or_404(db, user_id)
    require_actor_can_manage_target(ctx.user, target)
    key = db.execute(
        select(DeveloperApiKey).where(DeveloperApiKey.id == key_id, DeveloperApiKey.user_id == target.id)
    ).scalar_one_or_none()
    if key is None:
        raise PortalError(404, "NOT_FOUND", "api key not found")
    if key.revoked_at is None:
        key.revoked_at = datetime.now(timezone.utc)
    write_admin_audit(
        db, actor_user_id=ctx.user.id, actor_label=f"user:{ctx.user.email}", action="api_key.revoke",
        target_type="api_key", target_id=str(key.id), target_label=key.name, before=None, after=None,
        ip=get_client_ip(request),
    )
    db.commit()
    return {"status": "ok"}


@router.get("/admin/users/{user_id}/recordings")
def list_user_recordings(
    user_id: UUID,
    request: Request,
    search: Optional[str] = None,
    voice_id: Optional[str] = None,
    status: Optional[str] = None,
    page: int = 1,
    db: Session = Depends(get_db),
    ctx: AuthContext = Depends(require_admin),
    storage: ObjectStorage = Depends(get_object_storage),
) -> dict:
    target = get_target_user_or_404(db, user_id)
    require_actor_can_manage_target(ctx.user, target)
    if status is not None and status not in RECORDING_STATUSES:
        raise PortalError(422, "VALIDATION_ERROR", f"status must be one of {RECORDING_STATUSES}")
    statuses = (status,) if status else RECORDING_STATUSES

    settings = get_settings()
    result = query_recordings_library(
        db, target.id, search=search, voice_id=voice_id, page=max(page, 1), limit=20, statuses=statuses
    )
    write_admin_audit(
        db, actor_user_id=ctx.user.id, actor_label=f"user:{ctx.user.email}", action="user.recordings_view",
        target_type="user", target_id=str(target.id), target_label=target.email, before=None, after=None,
        ip=get_client_ip(request),
    )
    db.commit()
    return {
        "items": [serialize_recording(r, storage, settings) for r in result.items],
        "total_count": result.total_count, "page": page,
    }


@router.delete("/admin/recordings/{recording_id}", status_code=204)
def delete_recording_route(
    recording_id: UUID, request: Request,
    db: Session = Depends(get_db), ctx: AuthContext = Depends(require_admin), _csrf: None = Depends(require_csrf),
    storage: ObjectStorage = Depends(get_object_storage),
) -> None:
    recording = db.get(TTSRecording, recording_id)
    if recording is None:
        raise PortalError(404, "NOT_FOUND", "recording not found")
    target = get_target_user_or_404(db, recording.user_id)
    require_actor_can_manage_target(ctx.user, target)

    key = recording.audio_object_key or recording.audio_url
    write_admin_audit(
        db, actor_user_id=ctx.user.id, actor_label=f"user:{ctx.user.email}", action="recording.delete",
        target_type="recording", target_id=str(recording.id), target_label=target.email, before=None, after=None,
        ip=get_client_ip(request),
    )
    db.delete(recording)
    db.commit()
    if key:
        try:
            storage.delete(key)
        except Exception:   # noqa: BLE001 - best-effort; the row is already gone
            pass
    return None
