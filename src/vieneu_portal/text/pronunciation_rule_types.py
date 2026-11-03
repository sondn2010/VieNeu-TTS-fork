"""Rule and compiled-rule-set types for the pronunciation dictionary matcher
(`pronunciation_dictionary_single_pass_matcher.py`). Pinned by
`tests/fixtures/text_contract_vectors/dictionary_matcher_vectors.json`.
"""
from __future__ import annotations

import unicodedata
from dataclasses import dataclass
from enum import IntEnum
from typing import Mapping, Sequence


class RuleLayer(IntEnum):
    """Precedence rank at equal match length: account beats system beats the
    English fallback list.
    """

    ACCOUNT = 0
    SYSTEM = 1
    ENGLISH_FALLBACK = 2


@dataclass(frozen=True)
class Rule:
    id: str
    source: str
    target: str
    whole_word: bool
    case_sensitive: bool
    enabled: bool
    layer: RuleLayer
    # Stable tiebreak at equal length and layer: the account table's row
    # order, or (system pack order, then entry order within the pack).
    list_order: int


@dataclass(frozen=True)
class CompiledRuleSet:
    """Immutable and cacheable: callers (phase 9's dictionary API, phase 8's
    pipeline) compile once per account/version and reuse the result.
    """

    rules: tuple[Rule, ...]  # sorted: source length (code points) desc, layer asc, list_order asc
    # Indexed by `rule.source[0].lower()` (not casefold — see the matcher
    # module for why), each bucket keeping the same overall order as `rules`.
    index: Mapping[str, tuple[Rule, ...]]
    source_terms: frozenset[str]  # enabled rules' source terms, for phase 8's normalizer


def compile_rules(rules: Sequence[Rule]) -> CompiledRuleSet:
    normalized: list[Rule] = []
    for r in rules:
        if not r.enabled:
            continue
        source = unicodedata.normalize("NFC", r.source).strip()
        if not source:
            continue
        normalized.append(r if source == r.source else _with_source(r, source))

    ordered = tuple(sorted(normalized, key=lambda r: (-len(r.source), int(r.layer), r.list_order)))

    index: dict[str, list[Rule]] = {}
    for r in ordered:
        key = r.source[0].lower()
        index.setdefault(key, []).append(r)

    return CompiledRuleSet(
        rules=ordered,
        index={k: tuple(v) for k, v in index.items()},
        source_terms=frozenset(r.source for r in normalized),
    )


def _with_source(r: Rule, source: str) -> Rule:
    return Rule(
        id=r.id,
        source=source,
        target=r.target,
        whole_word=r.whole_word,
        case_sensitive=r.case_sensitive,
        enabled=r.enabled,
        layer=r.layer,
        list_order=r.list_order,
    )
