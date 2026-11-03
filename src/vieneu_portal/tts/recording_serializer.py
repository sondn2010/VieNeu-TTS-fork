"""Serializes a `tts_recordings` row for the API — reused by the admin
recordings browser (phases 13-14)."""
from __future__ import annotations

from ..config import Settings
from ..db.models_voices_and_recordings import TTSRecording
from ..storage.object_storage_interface import ObjectStorage
from ..text.character_count_and_token_estimate import count_chars


def serialize_recording(recording: TTSRecording, storage: ObjectStorage, settings: Settings) -> dict:
    key = recording.audio_object_key or recording.audio_url
    is_success = recording.status == "SUCCESS" and key
    audio_url = storage.presigned_get(key, settings.PRESIGN_TTL_SEC) if is_success else None
    download_url = (
        storage.presigned_get(key, settings.PRESIGN_TTL_SEC, download_name=f"{recording.id}.mp3")
        if is_success else None
    )
    body = {
        "id": str(recording.id), "voice_id": recording.voice_id, "model_version": recording.model_version,
        "original_text": recording.original_text, "speed": float(recording.speed),
        "char_count": recording.char_count, "tokens_consumed": recording.tokens_consumed,
        "duration_seconds": float(recording.duration_seconds), "status": recording.status,
        "source_module": recording.source_module, "created_at": recording.created_at,
        "audio_url": audio_url, "download_url": download_url,
    }
    if recording.status == "FAILED":
        body["error_code"] = recording.error_code
    if recording.status == "PENDING":
        # No dedicated speech-rate constant exists yet; `ENGINE_SEC_PER_CHAR`
        # (render time per char) is the closest available proxy for a
        # progress hint — this never feeds billing or the engine timeout.
        processed_len = count_chars(recording.processed_text or recording.original_text)
        body["estimated_seconds"] = round(processed_len * settings.ENGINE_SEC_PER_CHAR, 1)
    return body
