"""Five-stage story preprocessing pipeline (spec section 3)."""
from __future__ import annotations

from typing import Mapping, Optional, Sequence

from .dialogue_parser import parse_segments
from .exporters import StoryPreprocessResult, to_script
from .lexicon_mapper import map_lexicon
from .prosody_annotator import ProsodyAnnotator
from .rules import Rules, load_rules
from .sanitizer import sanitize
from .types import LexiconEntry


def _voice_for(speaker: str, voices: Mapping[str, str], rules: Rules) -> Optional[str]:
    """Look up by speaker, by the base name of `X (Nội tâm)`, and by the narrator label."""
    candidates = [speaker]
    if rules.self_suffix and speaker.endswith(rules.self_suffix):
        candidates.append(speaker[: -len(rules.self_suffix)])
    if speaker == rules.narrator:
        candidates.append(rules.narrator_label)
    return next((voices[c] for c in candidates if c in voices), None)


def run_pipeline(text: str, lexicon: Sequence[LexiconEntry] = (), *,
                 voices: Optional[Mapping[str, str]] = None,
                 rules: Optional[Rules] = None, chapter: int = 1) -> StoryPreprocessResult:
    if not isinstance(text, str):
        raise TypeError(f"text must be str, not {type(text).__name__}")
    rules = rules or load_rules()
    clean = sanitize(text, rules)                                          # stage 1
    segments = parse_segments(clean, rules)                                # stage 2
    annotated = ProsodyAnnotator(rules, chapter=chapter).annotate(segments)  # stage 3
    entries = tuple(lexicon)
    for ac in annotated:                                                   # stage 4
        ac.chunk.text = map_lexicon(ac.chunk.text, entries,
                                    caps_min_letters=rules.thresholds.caps_min_letters)
        if voices:
            ac.chunk.voice_preset = _voice_for(ac.chunk.speaker, voices, rules)
    return StoryPreprocessResult(chunks=[ac.chunk for ac in annotated],     # stage 5
                                 script=to_script(annotated, rules))
