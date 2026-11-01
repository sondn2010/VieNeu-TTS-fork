"""Fail-open wrapper around `preprocess` for the speech API path.

A preprocessing anomaly must never fail a TTS request: the caller gets a
fallback result whose tagged text is the raw input, plus the error for its
warning log. Invalid argument types are programming errors and still raise.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Mapping, Optional, Sequence

from .types import Chunk, LexiconEntry, PreprocessResult

logger = logging.getLogger(__name__)


@dataclass
class SafePreprocessOutcome:
    result: PreprocessResult
    ok: bool
    error: Optional[str] = None  # "ExceptionType: message" when the fallback was used


def raw_text_result(text: str) -> PreprocessResult:
    """One narration chunk carrying `text` unchanged; `to_tagged_text()` returns `text`."""
    if not text.strip():
        return PreprocessResult(chunks=[], script="")
    chunk = Chunk(chunk_id="ch01_p01_s01", speaker="Narrator", role_type="narration", text=text)
    return PreprocessResult(chunks=[chunk], script=f"Narrator: {text}\n")


def preprocess_safely(text: str, lexicon: Sequence[LexiconEntry] = (), *,
                      voices: Optional[Mapping[str, str]] = None,
                      rules_path: Optional[str] = None) -> SafePreprocessOutcome:
    """Run `preprocess`; on any processing error log a warning and fall back to the raw text."""
    if not isinstance(text, str):
        raise TypeError(f"text must be str, not {type(text).__name__}")
    from . import preprocess  # local import: the package module imports this one

    try:
        return SafePreprocessOutcome(preprocess(text, lexicon, voices=voices, rules_path=rules_path), True)
    except Exception as e:  # noqa: BLE001 - fail-open contract: any anomaly falls back
        error = f"{type(e).__name__}: {e}"
        logger.warning("story preprocessor failed (%s); using raw text (%d chars)", error, len(text))
        return SafePreprocessOutcome(raw_text_result(text), False, error)
