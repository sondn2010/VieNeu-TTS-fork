"""Request bodies and field validation shared by `POST /tts/generate` and
`POST /tts/stream`."""
from __future__ import annotations

from typing import Optional

from pydantic import BaseModel
from sqlalchemy.orm import Session

from ..config import Settings
from ..db.models_voices_and_recordings import Voice
from ..errors import PortalError
from ..text.character_count_and_token_estimate import count_chars

SPEED_CHOICES = (0.5, 0.75, 1.0, 1.25, 1.5, 2.0)


class GenerateRequest(BaseModel):
    voice_id: str
    text: str
    speed: float = 1.0
    bg_music_id: Optional[str] = None


class StreamRequest(BaseModel):
    voice_id: str
    text: str


def validate_speed(speed: float) -> None:
    if speed not in SPEED_CHOICES:
        raise PortalError(422, "VALIDATION_ERROR", f"speed must be one of {SPEED_CHOICES}")


def validate_bg_music(bg_music_id: Optional[str]) -> None:
    if bg_music_id is not None:
        raise PortalError(422, "BG_MUSIC_UNAVAILABLE", "background music is not available yet")


def get_active_voice_or_422(db: Session, voice_id: str) -> Voice:
    voice = db.get(Voice, voice_id)
    if voice is None or not voice.is_active:
        raise PortalError(422, "UNKNOWN_VOICE", f"unknown voice {voice_id!r}")
    return voice


def validate_text_length(text: str, settings: Settings) -> int:
    chars = count_chars(text)
    if not (1 <= chars <= settings.TTS_MAX_CHARS):
        raise PortalError(422, "TEXT_TOO_LONG", f"text must be 1-{settings.TTS_MAX_CHARS} characters")
    return chars
