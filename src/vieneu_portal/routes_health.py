from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session

from .db.session_factory import get_db
from .errors import PortalError

router = APIRouter()


@router.get("/health")
def health(db: Session = Depends(get_db)) -> dict:
    try:
        db.execute(text("SELECT 1"))
    except Exception as exc:
        raise PortalError(503, "SERVICE_UNAVAILABLE", "database unreachable") from exc
    return {"status": "ok", "db": "ok"}
