"""Serializes a `Voice` row for the API: presigns `sample_audio_url` and
`avatar_url` (object keys) into short-lived URLs instead of ever returning a
stored URL directly.
"""
from __future__ import annotations

from ..config import Settings
from ..db.models_voices_and_recordings import Voice
from ..storage.object_storage_interface import ObjectStorage


def serialize_voice(voice: Voice, storage: ObjectStorage, settings: Settings) -> dict:
    sample_key = voice.sample_object_key or voice.sample_audio_url
    return {
        "id": voice.id,
        "name": voice.name,
        "initials": voice.initials,
        "avatar_url": storage.presigned_get(voice.avatar_url, settings.PRESIGN_TTL_SEC) if voice.avatar_url else None,
        "gender": voice.gender,
        "region": voice.region,
        "language_code": voice.language_code,
        "language_label": voice.language_label,
        "model_version": voice.model_version,
        "tags": list(voice.tags or []),
        "supported_styles": list(voice.supported_styles or []),
        "sample_audio_url": storage.presigned_get(sample_key, settings.PRESIGN_TTL_SEC),
        "is_active": voice.is_active,
        "sort_order": voice.sort_order,
    }
