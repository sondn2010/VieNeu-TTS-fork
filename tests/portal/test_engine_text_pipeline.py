"""`build_engine_text` composition: pipeline order, control-token stripping,
billing from the original text, dictionary-protected chem tokens, moderation
of a malicious dictionary target, and the processed-length cap. Pure and
DB-free — no Postgres needed.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from vieneu_portal.config import get_settings
from vieneu_portal.moderation.blocklist_moderation_provider import BlocklistModerationProvider
from vieneu_portal.moderation.moderation_provider_factory import OffModerationProvider
from vieneu_portal.moderation.moderation_provider_interface import ContentPolicyViolation
from vieneu_portal.text.engine_text_pipeline import TextTooLongAfterProcessing, build_engine_text
from vieneu_portal.text.pronunciation_rule_types import Rule, RuleLayer, compile_rules

_BLOCKLIST_PATH = str(Path(__file__).parent.parent / "fixtures" / "moderation_blocklist_sample.tsv")


@pytest.fixture
def settings(monkeypatch):
    monkeypatch.setenv("VIENEU_PORTAL_SECRET_KEY", "x" * 32)
    monkeypatch.setenv("VIENEU_PORTAL_DATABASE_URL", "postgresql://unused/unused")
    get_settings.cache_clear()
    yield get_settings()
    get_settings.cache_clear()


def _rule(source: str, target: str, *, layer=RuleLayer.ACCOUNT, list_order: int = 0) -> Rule:
    return Rule(id=source, source=source, target=target, whole_word=True, case_sensitive=False,
                enabled=True, layer=layer, list_order=list_order)


def test_rule_applies_to_a_word_produced_by_normalization(settings):
    # "x" alone stays "x" (a bare single letter is a no-op split); a rule
    # targeting "x" must still see and rewrite it after normalization runs.
    rules = compile_rules([_rule("x", "biến ích")])
    result = build_engine_text("x ∈ ℝ", rules, OffModerationProvider(), settings)
    assert result.processed_text == "biến ích thuộc tập số thực"


def test_control_tokens_are_stripped_before_the_dictionary_ever_sees_them(settings):
    # A rule whose source is the literal control-token text never fires on it,
    # because the token is gone before the dictionary pass ever runs.
    rules = compile_rules([_rule("secret", "lộ")])
    result = build_engine_text("<|secret|> xin chào", rules, OffModerationProvider(), settings)
    assert "<|" not in result.processed_text
    assert "secret" not in result.processed_text
    assert "lộ" not in result.processed_text


def test_counts_come_from_the_original_not_the_processed_text(settings):
    rules = compile_rules([_rule("x", "một biến số dài hơn nhiều")])
    result = build_engine_text("x", rules, OffModerationProvider(), settings)
    assert result.char_count == 1
    assert result.processed_char_count > result.char_count


def test_dictionary_protected_term_is_read_by_its_own_rule_not_the_chem_reader(settings):
    rules = compile_rules([_rule("B2B", "doanh nghiệp với doanh nghiệp")])
    result = build_engine_text("Mô hình B2B rất phổ biến.", rules, OffModerationProvider(), settings)
    assert "doanh nghiệp với doanh nghiệp" in result.processed_text
    assert "B hai B" not in result.processed_text   # the chem reading never fires


def test_benign_original_with_malicious_dictionary_target_is_blocked(settings):
    hit = "hướng dẫn chế tạo bom"
    rules = compile_rules([_rule("hoa", hit)])
    moderation = BlocklistModerationProvider(_BLOCKLIST_PATH)
    with pytest.raises(ContentPolicyViolation) as exc_info:
        build_engine_text("hoa đẹp quá", rules, moderation, settings)
    assert exc_info.value.category == "VIOLENCE_ILLEGAL"


def test_expansion_over_the_cap_raises_text_too_long(settings):
    original = "x"
    rules = compile_rules([_rule("x", "y" * 3000)])
    with pytest.raises(TextTooLongAfterProcessing):
        build_engine_text(original, rules, OffModerationProvider(), settings)
