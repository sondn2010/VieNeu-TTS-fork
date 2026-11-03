"""Per-account pronunciation dictionary: CRUD-by-replacement (the whole table
is replaced in one transaction, matching the API's `PUT /dictionary`
semantics) plus the `etag` used for optimistic concurrency (`If-Match`).
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Sequence

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from ..db.models_dictionaries import PronunciationRule

MAX_RULES = 2000


@dataclass(frozen=True)
class RuleInput:
    source_term: str
    phonetic_replacement: str
    match_whole_word: bool = True
    case_sensitive: bool = False
    is_enabled: bool = True


def list_rules(db: Session, user_id) -> list:
    return list(
        db.execute(
            select(PronunciationRule).where(PronunciationRule.user_id == user_id).order_by(PronunciationRule.sort_order)
        ).scalars()
    )


def compute_etag(rules: Sequence[PronunciationRule]) -> str:
    tuples = [
        [r.source_term, r.phonetic_replacement, r.match_whole_word, r.case_sensitive, r.is_enabled]
        for r in rules
    ]
    payload = json.dumps(tuples, ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def replace_all_rules(db: Session, user_id, rules: Sequence[RuleInput]) -> list:
    """DELETE then bulk INSERT, in the caller's transaction; `sort_order` is
    the list index, so reordering is just resubmitting in the new order."""
    db.execute(delete(PronunciationRule).where(PronunciationRule.user_id == user_id))
    db.flush()
    rows = []
    for i, r in enumerate(rules):
        row = PronunciationRule(
            user_id=user_id, source_term=r.source_term, phonetic_replacement=r.phonetic_replacement,
            match_whole_word=r.match_whole_word, case_sensitive=r.case_sensitive, is_enabled=r.is_enabled,
            sort_order=i,
        )
        db.add(row)
        rows.append(row)
    db.flush()
    return rows
