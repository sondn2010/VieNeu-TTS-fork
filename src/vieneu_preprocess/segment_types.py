"""Internal structures passed between pipeline stages (not part of the public API)."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, Optional

from .types import Chunk

SegmentKind = Literal["narration", "dialogue", "shout", "inner_voice", "scene_break"]


@dataclass
class Segment:
    """Stage 2 output: a run of text with one voice role inside a paragraph."""

    kind: SegmentKind
    text: str
    paragraph: int  # 1-based content paragraph index (0 for scene breaks)
    speaker: Optional[str] = None  # None for narration (and unresolved inner voices)
    emotion: Optional[str] = None  # emotion rule name taken from the dialogue tag


@dataclass
class AnnotatedChunk:
    """Stage 3 output: a chunk plus the layout facts the exporters need."""

    chunk: Chunk
    paragraph: int
    scene: int
    pause_locked: bool = False  # P-07 shout pause_after is final; boundary rules may not raise it
