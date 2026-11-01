"""Stage 5: output formatters (spec section 5.2 script, 5.3 JSON, tagged text).

Between two chunks the effective pause is `max(prev.pause_after, next.pause_before)`,
so a boundary is never tagged twice.
"""
from __future__ import annotations

import json
from typing import Sequence

from .rules import Rules
from .segment_types import AnnotatedChunk
from .text_utils import format_pause
from .types import Chunk, PreprocessResult


def boundary_pauses(chunks: Sequence[Chunk]) -> tuple[float, list[float]]:
    """(leading pause, pause after each chunk) using the effective-pause rule."""
    if not chunks:
        return 0.0, []
    after = [max(c.pause_after_sec, chunks[i + 1].pause_before_sec) if i + 1 < len(chunks)
             else c.pause_after_sec for i, c in enumerate(chunks)]
    return chunks[0].pause_before_sec, after


def to_tagged_text(chunks: Sequence[Chunk]) -> str:
    """Single-voice text with `[x.xx]` tags; speaker labels dropped (streaming API path)."""
    lead, after = boundary_pauses(chunks)
    parts = [format_pause(lead)] if lead > 0 else []
    for c, pause in zip(chunks, after):
        parts.append(c.text)
        if pause > 0:
            parts.append(format_pause(pause))
    return " ".join(parts)


def speaker_label(chunk: Chunk, rules: Rules) -> str:
    return rules.narrator_label if chunk.speaker == rules.narrator else chunk.speaker


def to_script(annotated: Sequence[AnnotatedChunk], rules: Rules) -> str:
    """Mode 1: `// Phân cảnh N` comments and one `Speaker: text [x] ...` line per turn."""
    if not annotated:
        return ""
    chunks = [a.chunk for a in annotated]
    lead, after = boundary_pauses(chunks)
    lines: list[str] = []
    scene, turn_key, current = 0, None, []
    for i, (ac, pause) in enumerate(zip(annotated, after)):
        if ac.scene != scene:
            if current:
                lines.extend([" ".join(current), ""])
                current = []
            scene = ac.scene
            lines.append(f"// {rules.scene_label} {scene}")
            turn_key = None
        key = (ac.paragraph, ac.chunk.speaker)
        if key != turn_key:
            if current:
                lines.extend([" ".join(current), ""])
            current = [f"{speaker_label(ac.chunk, rules)}:"]
            turn_key = key
        if i == 0 and lead > 0:
            current.append(format_pause(lead))
        current.append(ac.chunk.text)
        if pause > 0:
            current.append(format_pause(pause))
    if current:
        lines.append(" ".join(current))
    return "\n".join(lines).rstrip() + "\n"


def to_json_text(result: PreprocessResult) -> str:
    """Mode 2: JSON chunks (section 5.3 keys), UTF-8 friendly."""
    return json.dumps(result.to_json(), ensure_ascii=False, indent=2)


class StoryPreprocessResult(PreprocessResult):
    """PreprocessResult whose tagged text uses the effective-pause rule (no double tags)."""

    def to_tagged_text(self) -> str:
        return to_tagged_text(self.chunks)
