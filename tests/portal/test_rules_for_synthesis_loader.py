"""`load_rules_for_synthesis`: layer tagging, disabled pack/rule exclusion,
system-layer cache invalidation after a pack edit, and the end-to-end tie
(an account rule overrides a same-source system rule) through
`build_engine_text`.
"""
from __future__ import annotations

from vieneu_portal.config import get_settings
from vieneu_portal.db.models_dictionaries import PronunciationRule, SystemDictionary, SystemPronunciationRule
from vieneu_portal.db.models_users_and_sessions import User
from vieneu_portal.dictionaries.rules_for_synthesis_loader import load_rules_for_synthesis
from vieneu_portal.dictionaries.system_rule_layer_cache import get_cached_system_rules, reset_system_rule_layer_cache
from vieneu_portal.moderation.moderation_provider_factory import OffModerationProvider
from vieneu_portal.text.engine_text_pipeline import build_engine_text
from vieneu_portal.text.pronunciation_rule_types import RuleLayer


def _make_user(db_session, email: str) -> User:
    user = User(
        email=email, username=email.split("@")[0], password_hash="scrypt$16384$8$1$x$y",
        token_balance=0, token_quota_total=0, daily_char_limit=0, daily_char_remaining=0,
    )
    db_session.add(user)
    db_session.flush()
    return user


def _add_pack(db_session, name: str, *, enabled: bool = True) -> SystemDictionary:
    pack = SystemDictionary(name=name, kind="term", is_enabled=enabled, description="")
    db_session.add(pack)
    db_session.flush()
    return pack


def _add_system_rule(db_session, pack, source: str, replacement: str, *, enabled: bool = True, sort_order: int = 0) -> None:
    db_session.add(SystemPronunciationRule(
        dictionary_id=pack.id, source_term=source, phonetic_replacement=replacement, match_whole_word=True,
        case_sensitive=False, is_enabled=enabled, sort_order=sort_order, note="", rule_kind="REPLACE",
    ))
    db_session.flush()


def setup_function(_fn) -> None:
    reset_system_rule_layer_cache()


def test_account_and_system_rules_are_tagged_with_the_right_layer(db_session) -> None:
    user = _make_user(db_session, "loader1@example.com")
    pack = _add_pack(db_session, "Pack 1")
    _add_system_rule(db_session, pack, "GPU", "Gờ Pê U")
    db_session.add(PronunciationRule(user_id=user.id, source_term="VieNeu", phonetic_replacement="Vi Nơi", sort_order=0))
    db_session.commit()

    compiled = load_rules_for_synthesis(db_session, user.id)
    by_source = {r.source: r for r in compiled.rules}
    assert by_source["GPU"].layer == RuleLayer.SYSTEM
    assert by_source["VieNeu"].layer == RuleLayer.ACCOUNT


def test_disabled_pack_and_disabled_rule_are_excluded(db_session) -> None:
    user = _make_user(db_session, "loader2@example.com")
    enabled_pack = _add_pack(db_session, "Enabled Pack")
    _add_system_rule(db_session, enabled_pack, "Visible", "x")
    _add_system_rule(db_session, enabled_pack, "HiddenRule", "y", enabled=False)
    disabled_pack = _add_pack(db_session, "Disabled Pack", enabled=False)
    _add_system_rule(db_session, disabled_pack, "HiddenPack", "z")
    db_session.commit()

    compiled = load_rules_for_synthesis(db_session, user.id)
    sources = {r.source for r in compiled.rules}
    assert sources == {"Visible"}


def test_english_fallback_rule_kind_maps_to_english_fallback_layer(db_session) -> None:
    user = _make_user(db_session, "loader3@example.com")
    pack = _add_pack(db_session, "Fallback Pack")
    db_session.add(SystemPronunciationRule(
        dictionary_id=pack.id, source_term="Hello", phonetic_replacement="", match_whole_word=True,
        case_sensitive=False, is_enabled=True, sort_order=0, note="", rule_kind="ENGLISH_FALLBACK",
    ))
    db_session.commit()

    compiled = load_rules_for_synthesis(db_session, user.id)
    assert compiled.rules[0].layer == RuleLayer.ENGLISH_FALLBACK


def test_cache_invalidates_after_a_pack_edit(db_session) -> None:
    pack = _add_pack(db_session, "Cached Pack")
    _add_system_rule(db_session, pack, "First", "a")
    db_session.commit()

    first = {r.source for r in get_cached_system_rules(db_session)}
    assert first == {"First"}

    _add_system_rule(db_session, pack, "Second", "b")
    from datetime import datetime, timezone
    pack.updated_at = datetime.now(timezone.utc)
    db_session.commit()

    second = {r.source for r in get_cached_system_rules(db_session)}
    assert second == {"First", "Second"}


def test_account_rule_overrides_same_source_system_rule_end_to_end(db_session) -> None:
    user = _make_user(db_session, "loader4@example.com")
    pack = _add_pack(db_session, "Tie Pack")
    _add_system_rule(db_session, pack, "VieNeu", "system wins if alone")
    db_session.add(PronunciationRule(user_id=user.id, source_term="VieNeu", phonetic_replacement="account wins", sort_order=0))
    db_session.commit()

    compiled = load_rules_for_synthesis(db_session, user.id)
    result = build_engine_text("VieNeu", compiled, OffModerationProvider(), get_settings())
    assert result.processed_text == "account wins"
