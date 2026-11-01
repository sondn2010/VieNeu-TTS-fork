"""Shared data contracts for the story preprocessor, dictionaries and admin app."""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Literal, Optional

Mode = Literal["phonetic", "en"]
Kind = Literal["english", "term", "name"]


@dataclass(frozen=True)
class LexiconEntry:
    term: str
    replacement: str = ""  # required when mode == "phonetic"; ignored for "en"
    mode: Mode = "phonetic"
    case_sensitive: bool = False
    note: str = ""


@dataclass
class Dictionary:
    name: str
    kind: Kind
    enabled: bool = True
    description: str = ""
    entries: list[LexiconEntry] = field(default_factory=list)


@dataclass
class Chunk:
    """One synthesis unit (tts-specs-v1 section 5.3 shape)."""

    chunk_id: str
    speaker: str  # "Narrator" or a character name
    role_type: str  # narration, narration_countdown, dialogue, dialogue_shout, inner_voice
    text: str  # no [x.xx] tags; emotion tags allowed
    speed: float = 1.0
    pause_before_sec: float = 0.0
    pause_after_sec: float = 0.0
    voice_preset: Optional[str] = None
    temperature: float = 0.8


@dataclass
class PreprocessResult:
    chunks: list[Chunk]
    script: str  # spec mode 1: "Speaker: text [0.35] ..." with "// scene" comments

    def to_json(self) -> list[dict]:
        return [asdict(c) for c in self.chunks]

    def to_tagged_text(self) -> str:
        """Single-voice text with [x.xx] pause tags, for the API path."""
        parts: list[str] = []
        for c in self.chunks:
            if c.pause_before_sec > 0:
                parts.append(f"[{c.pause_before_sec:.2f}]")
            parts.append(c.text)
            if c.pause_after_sec > 0:
                parts.append(f"[{c.pause_after_sec:.2f}]")
        return " ".join(parts)
