"""`load_rules_for_synthesis`: the full compiled rule set phase 10's
generate/stream routes (and the phase 5 `text preview` CLI) hand to
`build_engine_text` — the account's own enabled rules (layer `ACCOUNT`,
table order) plus the cached, enabled system layer (layer `SYSTEM` or
`ENGLISH_FALLBACK`, pack then rule `sort_order`). The matcher's own
precedence (longest match, then `ACCOUNT` > `SYSTEM` > `ENGLISH_FALLBACK`)
does the rest.
"""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..db.models_dictionaries import PronunciationRule
from ..text.pronunciation_rule_types import CompiledRuleSet, Rule, RuleLayer, compile_rules
from .system_rule_layer_cache import get_cached_system_rules


def _account_rules(db: Session, user_id) -> list:
    rows = db.execute(
        select(PronunciationRule)
        .where(PronunciationRule.user_id == user_id, PronunciationRule.is_enabled.is_(True))
        .order_by(PronunciationRule.sort_order)
    ).scalars()
    rules = []
    for i, r in enumerate(rows):
        rules.append(Rule(
            id=str(r.id), source=r.source_term, target=r.phonetic_replacement, whole_word=r.match_whole_word,
            case_sensitive=r.case_sensitive, enabled=True, layer=RuleLayer.ACCOUNT, list_order=i,
        ))
    return rules


def load_rules_for_synthesis(db: Session, user_id) -> CompiledRuleSet:
    return compile_rules(_account_rules(db, user_id) + get_cached_system_rules(db))
