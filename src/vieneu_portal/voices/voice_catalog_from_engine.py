"""Derives `voices` table rows from the engine's `/v1/voices` list, and syncs
them: insert new engine voices, deactivate rows whose engine voice
disappeared, never touch any other field of an existing row — the row is
admin-owned after its first insert (phases 13-14 edit everything else).
"""
from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field
from typing import Optional, Sequence

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..db.models_voices_and_recordings import Voice
from ..engine.engine_http_client import EngineClient, EngineVoice

_GENDER_FIELD_MAP = {"male": "NAM", "female": "NU"}
_DESC_GENDER_MAP = {"Nam": "NAM", "Nữ": "NU"}
_DESC_REGION_MAP = {"Bắc": "MIEN_BAC", "Trung": "MIEN_TRUNG", "Nam": "MIEN_NAM"}
_SLUG_NON_ALNUM_RE = re.compile(r"[^a-z0-9]+")


class VoiceSyncError(RuntimeError):
    """A voice's gender/region could not be determined, or two engine voices
    slug to the same id — sync aborts without touching any row.
    """


def slug_id(engine_voice_id: str) -> str:
    """`"Hải Đăng"` -> `"hai-dang"`: strip diacritics, `đ`/`Đ` -> `d`/`D`,
    runs of non-alphanumerics -> a single `-`.
    """
    s = engine_voice_id.replace("Đ", "D").replace("đ", "d")
    s = unicodedata.normalize("NFKD", s)
    s = "".join(ch for ch in s if not unicodedata.combining(ch))
    s = _SLUG_NON_ALNUM_RE.sub("-", s.lower()).strip("-")
    return s


def initials_from_name(name: str) -> str:
    words = name.split()
    if not words:
        return ""
    if len(words) == 1:
        return words[0][0].upper()
    return (words[0][0] + words[-1][0]).upper()


def _parse_description(description: Optional[str]) -> tuple[Optional[str], Optional[str]]:
    """`"<Nam|Nữ> · <Bắc|Trung|Nam>"` -> `(gender fallback, region)`, either
    side `None` when that segment does not match.
    """
    parts = [p.strip() for p in (description or "").split("·")]
    desc_gender = _DESC_GENDER_MAP.get(parts[0]) if parts and parts[0] else None
    region = _DESC_REGION_MAP.get(parts[1]) if len(parts) > 1 else None
    return desc_gender, region


def _resolve_gender(ev: EngineVoice) -> str:
    gender = _GENDER_FIELD_MAP.get((ev.gender or "").strip().lower())
    if gender is not None:
        return gender
    desc_gender, _ = _parse_description(ev.description)
    if desc_gender is not None:
        return desc_gender
    raise VoiceSyncError(
        f"cannot determine gender for engine voice {ev.id!r} (gender={ev.gender!r}, "
        f"description={ev.description!r})"
    )


def _resolve_region(ev: EngineVoice) -> str:
    _, region = _parse_description(ev.description)
    if region is not None:
        return region
    raise VoiceSyncError(f"cannot determine region for engine voice {ev.id!r} (description={ev.description!r})")


@dataclass(frozen=True)
class VoiceRow:
    id: str
    name: str
    initials: str
    gender: str
    region: str
    engine_voice_name: str
    sample_object_key: str
    sort_order: int
    model_version: str
    tags: list = field(default_factory=list)
    avatar_url: Optional[str] = None
    supported_styles: list = field(default_factory=lambda: ["Tự nhiên"])


def derive_voice_rows(engine_voices: Sequence[EngineVoice], model_version_label: str) -> list:
    """Pure function: engine voice list -> candidate rows, ordered `featured`
    first then name (that order becomes the stored `sort_order` rank).
    """
    ordered = sorted(engine_voices, key=lambda v: (not bool(v.featured), v.name))
    rows: list[VoiceRow] = []
    seen: dict[str, str] = {}
    for sort_order, ev in enumerate(ordered):
        voice_id = slug_id(ev.id)
        if voice_id in seen:
            raise VoiceSyncError(
                f"slug collision: engine voices {seen[voice_id]!r} and {ev.id!r} both slug to {voice_id!r}"
            )
        seen[voice_id] = ev.id
        rows.append(VoiceRow(
            id=voice_id,
            name=ev.name,
            initials=initials_from_name(ev.name),
            gender=_resolve_gender(ev),
            region=_resolve_region(ev),
            engine_voice_name=ev.id,
            sample_object_key=f"voices/samples/{voice_id}.mp3",
            sort_order=sort_order,
            model_version=model_version_label,
        ))
    return rows


@dataclass(frozen=True)
class SyncResult:
    inserted: list
    deactivated: list


def sync_voice_catalog(db: Session, engine_client: EngineClient, model_version_label: str) -> SyncResult:
    """Fully resolves the engine's voice list and derives rows before any
    write, so an engine failure or a derivation error (`EngineError`,
    `VoiceSyncError`) leaves every existing row untouched.
    """
    engine_voices = engine_client.list_voices()
    rows = derive_voice_rows(engine_voices, model_version_label)

    existing = {v.id: v for v in db.execute(select(Voice)).scalars()}
    live_ids = {row.id for row in rows}

    inserted: list[str] = []
    for row in rows:
        if row.id in existing:
            continue
        db.add(Voice(
            id=row.id, name=row.name, initials=row.initials, gender=row.gender, region=row.region,
            engine_voice_name=row.engine_voice_name, sample_audio_url=row.sample_object_key,
            sample_object_key=row.sample_object_key, sort_order=row.sort_order,
            model_version=row.model_version, tags=row.tags, avatar_url=row.avatar_url,
            supported_styles=row.supported_styles,
        ))
        inserted.append(row.id)

    deactivated: list[str] = []
    for voice_id, voice in existing.items():
        if voice_id not in live_ids and voice.is_active:
            voice.is_active = False
            deactivated.append(voice_id)

    db.commit()
    return SyncResult(inserted=inserted, deactivated=deactivated)
