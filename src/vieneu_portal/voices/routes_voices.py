from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..auth.session_dependencies import AuthContext, require_user
from ..config import get_settings
from ..db.models_voices_and_recordings import Voice
from ..db.session_factory import get_db
from ..storage.object_storage_interface import ObjectStorage
from ..storage.s3_object_storage import get_object_storage
from .voice_serializer import serialize_voice

router = APIRouter()


@router.get("/voices")
def list_voices(
    _ctx: AuthContext = Depends(require_user),
    db: Session = Depends(get_db),
    storage: ObjectStorage = Depends(get_object_storage),
) -> dict:
    settings = get_settings()
    rows = db.execute(
        select(Voice).where(Voice.is_active.is_(True)).order_by(Voice.sort_order, Voice.name)
    ).scalars().all()
    return {"data": [serialize_voice(v, storage, settings) for v in rows]}
