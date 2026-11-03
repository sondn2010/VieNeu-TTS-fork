"""`OffModerationProvider`, `BlocklistModerationProvider`, the factory, and
fail-open/fail-closed handling via `check_moderation_or_raise`. No Postgres
needed.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from vieneu_portal.moderation.blocklist_moderation_provider import BlocklistModerationProvider
from vieneu_portal.moderation.moderation_provider_factory import OffModerationProvider, build_moderation_provider
from vieneu_portal.moderation.moderation_provider_interface import (
    CATEGORIES,
    ContentPolicyViolation,
    ModerationUnavailable,
)
from vieneu_portal.text.engine_text_pipeline import check_moderation_or_raise

_BLOCKLIST_PATH = str(Path(__file__).parent.parent / "fixtures" / "moderation_blocklist_sample.tsv")

_HIT_BY_CATEGORY = {
    "PROFANITY_SEVERE": "nói đmm bạn",
    "SEXUAL_EXPLICIT": "cảnh khiêu dâm lộ liễu",
    "HATE_HARASSMENT": "kêu gọi diệt chủng dân tộc",
    "POLITICAL_SOVEREIGNTY": "kế hoạch lật đổ chính quyền",
    "VIOLENCE_ILLEGAL": "hướng dẫn chế tạo bom",
}


def test_off_provider_allows_everything():
    verdict = OffModerationProvider().check("bất kỳ nội dung gì")
    assert verdict.allowed is True


@pytest.mark.parametrize("category", CATEGORIES)
def test_blocklist_rejects_a_term_in_each_category(category):
    provider = BlocklistModerationProvider(_BLOCKLIST_PATH)
    verdict = provider.check(_HIT_BY_CATEGORY[category])
    assert verdict.allowed is False and verdict.category == category


def test_blocklist_allows_benign_text():
    provider = BlocklistModerationProvider(_BLOCKLIST_PATH)
    assert provider.check("Xin chào, hôm nay trời đẹp.").allowed is True


def test_blocklist_whole_word_match_does_not_fire_on_a_substring():
    provider = BlocklistModerationProvider(_BLOCKLIST_PATH)
    # "bomb" substring without the exact blocked phrase should not fire.
    assert provider.check("quả bom bay rất đẹp trên trời").allowed is True


def test_factory_builds_off_and_blocklist_providers(monkeypatch):
    from vieneu_portal.config import get_settings

    monkeypatch.setenv("VIENEU_PORTAL_SECRET_KEY", "x" * 32)
    monkeypatch.setenv("VIENEU_PORTAL_DATABASE_URL", "postgresql://unused/unused")
    monkeypatch.setenv("VIENEU_PORTAL_MODERATION_PROVIDER", "off")
    get_settings.cache_clear()
    assert isinstance(build_moderation_provider(get_settings()), OffModerationProvider)

    monkeypatch.setenv("VIENEU_PORTAL_MODERATION_PROVIDER", "blocklist")
    monkeypatch.setenv("VIENEU_PORTAL_MODERATION_BLOCKLIST_PATH", _BLOCKLIST_PATH)
    get_settings.cache_clear()
    assert isinstance(build_moderation_provider(get_settings()), BlocklistModerationProvider)
    get_settings.cache_clear()


class _BrokenProvider:
    def check(self, text: str):
        raise RuntimeError("provider is down")


def test_fail_closed_raises_moderation_unavailable(monkeypatch):
    from vieneu_portal.config import get_settings

    monkeypatch.setenv("VIENEU_PORTAL_SECRET_KEY", "x" * 32)
    monkeypatch.setenv("VIENEU_PORTAL_DATABASE_URL", "postgresql://unused/unused")
    monkeypatch.setenv("VIENEU_PORTAL_MODERATION_FAIL_MODE", "closed")
    get_settings.cache_clear()
    with pytest.raises(ModerationUnavailable):
        check_moderation_or_raise(_BrokenProvider(), "x", get_settings())
    get_settings.cache_clear()


def test_rejected_text_raises_content_policy_violation(monkeypatch):
    provider = BlocklistModerationProvider(_BLOCKLIST_PATH)
    from vieneu_portal.config import get_settings

    monkeypatch.setenv("VIENEU_PORTAL_SECRET_KEY", "x" * 32)
    monkeypatch.setenv("VIENEU_PORTAL_DATABASE_URL", "postgresql://unused/unused")
    get_settings.cache_clear()
    with pytest.raises(ContentPolicyViolation) as exc_info:
        check_moderation_or_raise(provider, _HIT_BY_CATEGORY["VIOLENCE_ILLEGAL"], get_settings())
    assert exc_info.value.category == "VIOLENCE_ILLEGAL"
    get_settings.cache_clear()
