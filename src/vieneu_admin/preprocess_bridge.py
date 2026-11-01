"""Calls into the story preprocessor through its frozen public signature.

Resolved through the module attribute at call time (``vieneu_preprocess.preprocess``)
so the admin app follows whatever implementation is installed, and tests can stub it.
"""
from __future__ import annotations

import logging
from typing import Mapping, Optional, Sequence

import vieneu_preprocess
from vieneu_preprocess.types import LexiconEntry, PreprocessResult

log = logging.getLogger("vieneu.admin")


class PreprocessFailed(RuntimeError):
    """The preprocessor raised; the message is safe to show in the UI."""


def run_preprocess(text: str, lexicon: Sequence[LexiconEntry],
                   voices: Optional[Mapping[str, str]] = None) -> PreprocessResult:
    try:
        return vieneu_preprocess.preprocess(text, lexicon, voices=voices or None)
    except NotImplementedError as e:
        raise PreprocessFailed("The story preprocessor is not available in this build.") from e
    except Exception as e:
        log.exception("story preprocessor failed")
        raise PreprocessFailed(f"Preprocessing failed: {type(e).__name__}: {e}"[:300]) from e
