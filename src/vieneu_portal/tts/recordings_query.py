"""Filter, search and totals for the recordings library — reused by the
admin recordings browser (phases 13-14).
"""
from __future__ import annotations

import unicodedata
from dataclasses import dataclass
from typing import Optional

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from ..db.models_voices_and_recordings import TTSRecording, Voice

_ESCAPE_MAP = {"\\": "\\\\", "%": "\\%", "_": "\\_"}


def _escape_ilike(term: str) -> str:
    return "".join(_ESCAPE_MAP.get(ch, ch) for ch in term)


@dataclass(frozen=True)
class LibraryPage:
    items: list
    total_count: int
    overall_count: int
    total_duration_seconds: float
    voices_used: list


def query_recordings_library(
    db: Session, user_id, *, search: Optional[str] = None, voice_id: Optional[str] = None,
    page: int = 1, limit: int = 20, statuses: tuple = ("SUCCESS", "PENDING"),
) -> LibraryPage:
    """`statuses` defaults to what the user-facing library shows (never a
    bare `FAILED` row); the admin recordings browser (phase 13) passes
    `("SUCCESS", "PENDING", "FAILED")` or a single admin-chosen status.
    """
    base = select(TTSRecording).where(
        TTSRecording.user_id == user_id, TTSRecording.status.in_(statuses)
    )
    if voice_id:
        base = base.where(TTSRecording.voice_id == voice_id)
    if search:
        normalized = unicodedata.normalize("NFC", search)
        pattern = f"%{_escape_ilike(normalized)}%"
        base = base.join(Voice, Voice.id == TTSRecording.voice_id).where(
            or_(TTSRecording.original_text.ilike(pattern), Voice.name.ilike(pattern))
        )

    total_count = db.execute(select(func.count()).select_from(base.subquery())).scalar_one()

    overall_count = db.execute(
        select(func.count()).where(TTSRecording.user_id == user_id, TTSRecording.status == "SUCCESS")
    ).scalar_one()

    duration_subq = base.where(TTSRecording.status == "SUCCESS").subquery()
    total_duration_seconds = db.execute(
        select(func.coalesce(func.sum(duration_subq.c.duration_seconds), 0))
    ).scalar_one()

    voices_used_rows = db.execute(
        select(Voice.id, Voice.name)
        .join(TTSRecording, TTSRecording.voice_id == Voice.id)
        .where(TTSRecording.user_id == user_id, TTSRecording.status == "SUCCESS")
        .distinct()
        .order_by(Voice.name)
    ).all()

    items = list(
        db.execute(base.order_by(TTSRecording.created_at.desc()).offset((page - 1) * limit).limit(limit)).scalars()
    )

    return LibraryPage(
        items=items, total_count=total_count, overall_count=overall_count,
        total_duration_seconds=float(total_duration_seconds),
        voices_used=[{"id": v.id, "name": v.name} for v in voices_used_rows],
    )
