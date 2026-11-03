"""Admin voice-catalog edits, avatar/sample uploads (magic-byte sniffed,
size-capped by the caller before the full body is read) and on-demand
sample re-render (the same `EngineClient.render` call the CLI's
`voices render-samples` command uses, so a row edited here still survives
a later `voices sync`).
"""
from __future__ import annotations

from typing import Optional, Sequence

from sqlalchemy.orm import Session

from ..config import Settings
from ..db.models_users_and_sessions import User
from ..db.models_voices_and_recordings import Voice
from ..engine.engine_http_client import EngineClient, EngineError
from ..errors import PortalError
from ..storage.object_storage_interface import ObjectStorage
from .admin_audit_log_writer import write_admin_audit
from .upload_type_sniffing import AUDIO_CONTENT_TYPES, IMAGE_CONTENT_TYPES, sniff_audio_type, sniff_image_type

MAX_AVATAR_BYTES = 1 * 1024 * 1024
MAX_SAMPLE_BYTES = 5 * 1024 * 1024
_SAMPLE_SENTENCE = "Xin chào, đây là giọng nói mẫu của VieNeu."

GENDERS = ("NAM", "NU")
REGIONS = ("MIEN_BAC", "MIEN_TRUNG", "MIEN_NAM")


def get_voice_or_404(db: Session, voice_id: str) -> Voice:
    voice = db.get(Voice, voice_id)
    if voice is None:
        raise PortalError(404, "NOT_FOUND", f"voice {voice_id!r} not found")
    return voice


def _actor_label(actor: User) -> str:
    return f"user:{actor.email}"


def update_voice_fields(
    db: Session, *, actor: User, voice: Voice, name: Optional[str] = None, gender: Optional[str] = None,
    region: Optional[str] = None, tags: Optional[Sequence[str]] = None, language_label: Optional[str] = None,
    is_active: Optional[bool] = None, sort_order: Optional[int] = None, ip: Optional[str] = None,
) -> Voice:
    if gender is not None and gender not in GENDERS:
        raise PortalError(422, "VALIDATION_ERROR", f"gender must be one of {GENDERS}")
    if region is not None and region not in REGIONS:
        raise PortalError(422, "VALIDATION_ERROR", f"region must be one of {REGIONS}")

    before = {
        "name": voice.name, "gender": voice.gender, "region": voice.region, "tags": list(voice.tags or []),
        "language_label": voice.language_label, "is_active": voice.is_active, "sort_order": voice.sort_order,
    }
    if name is not None:
        voice.name = name
    if gender is not None:
        voice.gender = gender
    if region is not None:
        voice.region = region
    if tags is not None:
        voice.tags = list(tags)
    if language_label is not None:
        voice.language_label = language_label
    if is_active is not None:
        voice.is_active = is_active
    if sort_order is not None:
        voice.sort_order = sort_order
    after = {
        "name": voice.name, "gender": voice.gender, "region": voice.region, "tags": list(voice.tags or []),
        "language_label": voice.language_label, "is_active": voice.is_active, "sort_order": voice.sort_order,
    }
    write_admin_audit(
        db, actor_user_id=actor.id, actor_label=_actor_label(actor), action="voice.update",
        target_type="voice", target_id=voice.id, target_label=voice.name, before=before, after=after, ip=ip,
    )
    db.flush()
    return voice


def put_avatar(
    db: Session, *, actor: User, voice: Voice, data: bytes, storage: ObjectStorage, ip: Optional[str] = None,
) -> Voice:
    if len(data) > MAX_AVATAR_BYTES:
        raise PortalError(422, "FILE_TOO_LARGE", "avatar must be at most 1 MB")
    try:
        ext = sniff_image_type(data)
    except ValueError as exc:
        raise PortalError(422, "UNSUPPORTED_FILE_TYPE", str(exc))
    key = f"voices/avatars/{voice.id}.{ext}"
    storage.put_bytes(key, data, IMAGE_CONTENT_TYPES[ext])
    voice.avatar_url = key
    write_admin_audit(
        db, actor_user_id=actor.id, actor_label=_actor_label(actor), action="voice.avatar_upload",
        target_type="voice", target_id=voice.id, target_label=voice.name, before=None, after={"key": key}, ip=ip,
    )
    db.flush()
    return voice


def delete_avatar(db: Session, *, actor: User, voice: Voice, storage: ObjectStorage, ip: Optional[str] = None) -> Voice:
    key = voice.avatar_url
    voice.avatar_url = None
    if key:
        storage.delete(key)
    write_admin_audit(
        db, actor_user_id=actor.id, actor_label=_actor_label(actor), action="voice.avatar_delete",
        target_type="voice", target_id=voice.id, target_label=voice.name, before={"key": key}, after=None, ip=ip,
    )
    db.flush()
    return voice


def put_sample(
    db: Session, *, actor: User, voice: Voice, data: bytes, storage: ObjectStorage, ip: Optional[str] = None,
) -> Voice:
    if len(data) > MAX_SAMPLE_BYTES:
        raise PortalError(422, "FILE_TOO_LARGE", "sample must be at most 5 MB")
    try:
        ext = sniff_audio_type(data)
    except ValueError as exc:
        raise PortalError(422, "UNSUPPORTED_FILE_TYPE", str(exc))
    key = f"voices/samples/{voice.id}.{ext}"
    storage.put_bytes(key, data, AUDIO_CONTENT_TYPES[ext])
    voice.sample_object_key = key
    voice.sample_audio_url = key
    write_admin_audit(
        db, actor_user_id=actor.id, actor_label=_actor_label(actor), action="voice.sample_upload",
        target_type="voice", target_id=voice.id, target_label=voice.name, before=None, after={"key": key}, ip=ip,
    )
    db.flush()
    return voice


def render_sample(
    db: Session, settings: Settings, *, actor: User, voice: Voice, storage: ObjectStorage,
    text: Optional[str] = None, ip: Optional[str] = None,
) -> Voice:
    engine_client = EngineClient(settings)
    try:
        rendered = engine_client.render(text or _SAMPLE_SENTENCE, voice.engine_voice_name, fmt="mp3")
    except EngineError as exc:
        raise PortalError(503, "ENGINE_UNAVAILABLE", f"sample render failed: {exc}")
    key = voice.sample_object_key or f"voices/samples/{voice.id}.mp3"
    storage.put_bytes(key, rendered.audio, "audio/mpeg")
    voice.sample_object_key = key
    voice.sample_audio_url = key
    write_admin_audit(
        db, actor_user_id=actor.id, actor_label=_actor_label(actor), action="voice.sample_render",
        target_type="voice", target_id=voice.id, target_label=voice.name, before=None,
        after={"key": key, "duration_seconds": rendered.duration_seconds}, ip=ip,
    )
    db.flush()
    return voice
