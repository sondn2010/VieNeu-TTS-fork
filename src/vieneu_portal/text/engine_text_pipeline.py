"""Composes the whole text path: NFC -> strip `<|...|>` control tokens ->
moderate the cleaned original -> normalize math/chem (dictionary sources
protected) -> apply the pronunciation dictionary -> moderate the processed
text -> cap the processed length. Pure and DB-free; no routes — phase 10
calls this directly from the generate/stream request handlers.
"""
from __future__ import annotations

import logging
import re
import unicodedata
from dataclasses import dataclass

from ..config import Settings
from ..moderation.moderation_provider_interface import (
    ContentPolicyViolation,
    ModerationProvider,
    ModerationUnavailable,
)
from .character_count_and_token_estimate import count_chars, estimate_tokens
from .math_expression_normalizer import normalize_math_and_chemistry
from .pronunciation_dictionary_single_pass_matcher import apply_pronunciation_rules
from .pronunciation_rule_types import CompiledRuleSet

log = logging.getLogger("vieneu.portal.text_pipeline")

_CONTROL_TOKEN_RE = re.compile(r"<\|.*?\|>")


class TextTooLongAfterProcessing(Exception):
    """Processed text grew past the engine's input limit or the expansion
    cap. Route layer maps this to `422 TEXT_TOO_LONG_AFTER_PROCESSING`."""


@dataclass(frozen=True)
class EngineText:
    processed_text: str
    char_count: int
    processed_char_count: int
    estimated_tokens: int


def check_moderation_or_raise(provider: ModerationProvider, text: str, settings: Settings) -> None:
    """Shared by this pipeline and dictionary rule save/import (phases 5, 9):
    same provider, same fail mode, `ContentPolicyViolation`/`ModerationUnavailable`
    on the same terms everywhere text reaches a user.
    """
    try:
        verdict = provider.check(text)
    except Exception as exc:   # noqa: BLE001 - any provider failure is "unavailable"
        if settings.MODERATION_FAIL_MODE == "closed":
            raise ModerationUnavailable(f"moderation provider failed: {exc}") from exc
        log.warning("moderation provider failed, failing OPEN (allowing): %s", exc)
        return
    if not verdict.allowed:
        raise ContentPolicyViolation(verdict.category or "UNKNOWN", verdict.message_vi or "blocked")


def build_engine_text(
    original: str, compiled_rules: CompiledRuleSet, moderation: ModerationProvider, settings: Settings,
) -> EngineText:
    cleaned = _CONTROL_TOKEN_RE.sub("", unicodedata.normalize("NFC", original))
    char_count = count_chars(cleaned)

    # Moderating only the original would let a dictionary rule's *target*
    # smuggle blocked text in (e.g. an account rule `hoa -> <blocked>`), so
    # the processed text is moderated again below.
    check_moderation_or_raise(moderation, cleaned, settings)

    normalized = normalize_math_and_chemistry(cleaned, compiled_rules.source_terms)
    processed = apply_pronunciation_rules(normalized, compiled_rules)

    check_moderation_or_raise(moderation, processed, settings)

    processed_char_count = count_chars(processed)
    cap = min(settings.ENGINE_MAX_INPUT_CHARS, max(2 * char_count, char_count + 2000))
    if processed_char_count > cap:
        raise TextTooLongAfterProcessing(
            f"processed text is {processed_char_count} chars, over the cap of {cap}"
        )

    return EngineText(
        processed_text=processed,
        char_count=char_count,
        processed_char_count=processed_char_count,
        # Billing counts come from the original (cleaned) text, never the
        # processed one.
        estimated_tokens=estimate_tokens(char_count, settings.TOKENS_PER_CHAR_MILLI),
    )
