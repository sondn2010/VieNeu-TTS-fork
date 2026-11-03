"""`/api/v1/admin/voices*` — catalog edit, avatar/sample upload, sample
re-render. Uploads are size-capped here (before the full body is read) and
magic-byte sniffed by the service layer.
"""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, File, Request, UploadFile
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..admin_services.voice_catalog_admin_service import (
    MAX_AVATAR_BYTES,
    MAX_SAMPLE_BYTES,
    delete_avatar,
    get_voice_or_404,
    put_avatar,
    put_sample,
    render_sample,
    update_voice_fields,
)
from ..auth.session_dependencies import AuthContext, get_client_ip, require_admin, require_csrf
from ..config import get_settings
from ..db.models_voices_and_recordings import Voice
from ..db.session_factory import get_db
from ..storage.object_storage_interface import ObjectStorage
from ..storage.s3_object_storage import get_object_storage
from ..voices.voice_serializer import serialize_voice

router = APIRouter()


@router.get("/admin/voices")
def list_admin_voices(
    db: Session = Depends(get_db), ctx: AuthContext = Depends(require_admin),
    storage: ObjectStorage = Depends(get_object_storage),
) -> dict:
    settings = get_settings()
    rows = list(db.execute(select(Voice).order_by(Voice.sort_order, Voice.name)).scalars())
    return {"items": [serialize_voice(v, storage, settings) for v in rows]}


class UpdateVoiceRequest(BaseModel):
    name: Optional[str] = None
    gender: Optional[str] = None
    region: Optional[str] = None
    tags: Optional[list[str]] = None
    language_label: Optional[str] = None
    is_active: Optional[bool] = None
    sort_order: Optional[int] = None


@router.patch("/admin/voices/{voice_id}")
def update_voice(
    voice_id: str, payload: UpdateVoiceRequest, request: Request,
    db: Session = Depends(get_db), ctx: AuthContext = Depends(require_admin), _csrf: None = Depends(require_csrf),
    storage: ObjectStorage = Depends(get_object_storage),
) -> dict:
    voice = get_voice_or_404(db, voice_id)
    update_voice_fields(
        db, actor=ctx.user, voice=voice, name=payload.name, gender=payload.gender, region=payload.region,
        tags=payload.tags, language_label=payload.language_label, is_active=payload.is_active,
        sort_order=payload.sort_order, ip=get_client_ip(request),
    )
    db.commit()
    settings = get_settings()
    return {"voice": serialize_voice(voice, storage, settings)}


@router.put("/admin/voices/{voice_id}/avatar")
async def put_voice_avatar(
    voice_id: str, request: Request, file: UploadFile = File(...),
    db: Session = Depends(get_db), ctx: AuthContext = Depends(require_admin), _csrf: None = Depends(require_csrf),
    storage: ObjectStorage = Depends(get_object_storage),
) -> dict:
    voice = get_voice_or_404(db, voice_id)
    data = await file.read(MAX_AVATAR_BYTES + 1)
    put_avatar(db, actor=ctx.user, voice=voice, data=data, storage=storage, ip=get_client_ip(request))
    db.commit()
    settings = get_settings()
    return {"voice": serialize_voice(voice, storage, settings)}


@router.delete("/admin/voices/{voice_id}/avatar")
def delete_voice_avatar(
    voice_id: str, request: Request,
    db: Session = Depends(get_db), ctx: AuthContext = Depends(require_admin), _csrf: None = Depends(require_csrf),
    storage: ObjectStorage = Depends(get_object_storage),
) -> dict:
    voice = get_voice_or_404(db, voice_id)
    delete_avatar(db, actor=ctx.user, voice=voice, storage=storage, ip=get_client_ip(request))
    db.commit()
    settings = get_settings()
    return {"voice": serialize_voice(voice, storage, settings)}


@router.put("/admin/voices/{voice_id}/sample")
async def put_voice_sample(
    voice_id: str, request: Request, file: UploadFile = File(...),
    db: Session = Depends(get_db), ctx: AuthContext = Depends(require_admin), _csrf: None = Depends(require_csrf),
    storage: ObjectStorage = Depends(get_object_storage),
) -> dict:
    voice = get_voice_or_404(db, voice_id)
    data = await file.read(MAX_SAMPLE_BYTES + 1)
    put_sample(db, actor=ctx.user, voice=voice, data=data, storage=storage, ip=get_client_ip(request))
    db.commit()
    settings = get_settings()
    return {"voice": serialize_voice(voice, storage, settings)}


class RenderSampleRequest(BaseModel):
    text: Optional[str] = None


@router.post("/admin/voices/{voice_id}/sample/render")
def render_voice_sample(
    voice_id: str, payload: RenderSampleRequest, request: Request,
    db: Session = Depends(get_db), ctx: AuthContext = Depends(require_admin), _csrf: None = Depends(require_csrf),
    storage: ObjectStorage = Depends(get_object_storage),
) -> dict:
    voice = get_voice_or_404(db, voice_id)
    settings = get_settings()
    render_sample(
        db, settings, actor=ctx.user, voice=voice, storage=storage, text=payload.text, ip=get_client_ip(request)
    )
    db.commit()
    return {"voice": serialize_voice(voice, storage, settings)}
