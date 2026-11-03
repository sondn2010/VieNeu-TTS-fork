"""Caches the compiled system-dictionary layer (~850+ rules) across
requests, keyed by a cheap version signature over `system_dictionaries`
(`count(*), max(updated_at)`). Every admin mutation bumps the edited pack's
`updated_at` (phase 5's `_touch_pack`), so the signature changes and the
cache reloads on the very next request — admin edits take effect without
ever reloading the whole layer per request.
"""
from __future__ import annotations

import threading

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..db.models_dictionaries import SystemDictionary, SystemPronunciationRule
from ..text.pronunciation_rule_types import Rule, RuleLayer

_lock = threading.Lock()
_cache: dict = {"version": None, "rules": None}


def _version_signature(db: Session):
    return db.execute(select(func.count(SystemDictionary.id), func.max(SystemDictionary.updated_at))).one()


def _load_system_rules(db: Session) -> list:
    rows = db.execute(
        select(SystemPronunciationRule)
        .join(SystemDictionary, SystemDictionary.id == SystemPronunciationRule.dictionary_id)
        .where(SystemPronunciationRule.is_enabled.is_(True), SystemDictionary.is_enabled.is_(True))
        .order_by(SystemDictionary.sort_order, SystemPronunciationRule.sort_order)
    ).scalars()
    rules = []
    for i, r in enumerate(rows):
        layer = RuleLayer.ENGLISH_FALLBACK if r.rule_kind == "ENGLISH_FALLBACK" else RuleLayer.SYSTEM
        rules.append(Rule(
            id=str(r.id), source=r.source_term, target=r.phonetic_replacement, whole_word=r.match_whole_word,
            case_sensitive=r.case_sensitive, enabled=True, layer=layer, list_order=i,
        ))
    return rules


def get_cached_system_rules(db: Session) -> list:
    version = _version_signature(db)
    with _lock:
        if _cache["version"] == version and _cache["rules"] is not None:
            return _cache["rules"]
    rules = _load_system_rules(db)
    with _lock:
        _cache["version"] = version
        _cache["rules"] = rules
    return rules


def reset_system_rule_layer_cache() -> None:
    """Test-only: forces the next call to reload from the DB."""
    with _lock:
        _cache["version"] = None
        _cache["rules"] = None
