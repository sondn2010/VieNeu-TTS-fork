"""Spec-based story preprocessor (docs/tts-specs/tts-specs-v1.md).

`preprocess` runs the five-stage pipeline; `render` turns its chunks into audio;
`preprocess_safely` is the fail-open wrapper for the speech API.
"""
from __future__ import annotations

from typing import Mapping, Optional, Sequence

from .types import Chunk, Dictionary, LexiconEntry, PreprocessResult

__all__ = ["Chunk", "Dictionary", "LexiconEntry", "PreprocessResult", "preprocess", "render",
           "preprocess_safely"]


def preprocess(text: str, lexicon: Sequence[LexiconEntry] = (), *,
               voices: Optional[Mapping[str, str]] = None,
               rules_path: Optional[str] = None) -> PreprocessResult:
    """Return chunks (spec 5.3) and the formatted script (spec 5.2) for a story text."""
    from .pipeline import run_pipeline
    from .rules import load_rules

    return run_pipeline(text, lexicon, voices=voices, rules=load_rules(rules_path))


def render(result: PreprocessResult, tts, *, default_voice: Optional[str] = None,
           apply_speed: bool = True):
    """Return a 48 kHz float32 numpy array."""
    from .runner import render_chunks

    return render_chunks(result.chunks, tts, default_voice=default_voice, apply_speed=apply_speed)


def preprocess_safely(text: str, lexicon: Sequence[LexiconEntry] = (), *,
                      voices: Optional[Mapping[str, str]] = None,
                      rules_path: Optional[str] = None):
    """Fail-open `preprocess`: returns `SafePreprocessOutcome(result, ok, error)`."""
    from .safe_execution import preprocess_safely as _safe

    return _safe(text, lexicon, voices=voices, rules_path=rules_path)
