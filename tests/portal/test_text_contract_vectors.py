"""Drives the shared JSON vectors in `tests/fixtures/text_contract_vectors/`
against the Python text-contract modules. The same vectors drive the
TypeScript mirror (`portal-web/src/lib/text/text-contract-vectors.test.ts`) —
no DB needed.
"""
from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

import pytest

from vieneu_portal.text.character_count_and_token_estimate import count_chars, estimate_tokens
from vieneu_portal.text.dictionary_import_export_and_merge import (
    ImportedRule,
    merge_imported_rules,
    parse_dictionary_import,
)
from vieneu_portal.text.pronunciation_dictionary_single_pass_matcher import apply_pronunciation_rules
from vieneu_portal.text.pronunciation_rule_types import Rule, RuleLayer, compile_rules

VECTORS_DIR = Path(__file__).resolve().parents[2] / "tests" / "fixtures" / "text_contract_vectors"


def _load(name: str) -> dict[str, Any]:
    return json.loads((VECTORS_DIR / name).read_text(encoding="utf-8"))


TOKEN_VECTORS = _load("token_estimate_vectors.json")
MATCHER_VECTORS = _load("dictionary_matcher_vectors.json")["matcher_vectors"]
IMPORT_VECTORS = _load("dictionary_import_vectors.json")


# --- character count / token estimate ---------------------------------------


@pytest.mark.parametrize("vector", TOKEN_VECTORS["char_count_vectors"], ids=lambda v: v["description"])
def test_count_chars_vectors(vector: dict) -> None:
    assert count_chars(vector["text"]) == vector["expected_chars"]


@pytest.mark.parametrize(
    "vector",
    TOKEN_VECTORS["token_estimate_vectors"],
    ids=lambda v: f"chars={v['chars']},rate={v['rate_milli']}",
)
def test_estimate_tokens_vectors(vector: dict) -> None:
    assert estimate_tokens(vector["chars"], vector["rate_milli"]) == vector["expected_tokens"]


# --- pronunciation dictionary matcher -----------------------------------------


def _rule_from_vector(i: int, v: dict) -> Rule:
    return Rule(
        id=f"r{i}",
        source=v["source"],
        target=v["target"],
        whole_word=v["whole_word"],
        case_sensitive=v["case_sensitive"],
        enabled=v["enabled"],
        layer=RuleLayer[v["layer"]],
        list_order=v["list_order"],
    )


@pytest.mark.parametrize("vector", MATCHER_VECTORS, ids=lambda v: v["description"])
def test_matcher_vectors(vector: dict) -> None:
    rules = [_rule_from_vector(i, r) for i, r in enumerate(vector["rules"])]
    compiled = compile_rules(rules)
    assert apply_pronunciation_rules(vector["text"], compiled) == vector["expected"]


def test_matcher_performance_benchmark() -> None:
    """20 000-char text, 2 000 account + 848 seed + 10 000 synthetic system
    rules: compile < 500 ms, apply < 200 ms (generous bounds; the required
    first-code-point index is what keeps this from degrading to O(n * rules)).
    """
    rules: list[Rule] = []
    for i in range(2000):
        rules.append(
            Rule(id=f"a{i}", source=f"acct{i:04d}", target=f"T{i}", whole_word=True, case_sensitive=False,
                 enabled=True, layer=RuleLayer.ACCOUNT, list_order=i)
        )
    for i in range(848):
        rules.append(
            Rule(id=f"s{i}", source=f"seed{i:04d}", target=f"S{i}", whole_word=True, case_sensitive=False,
                 enabled=True, layer=RuleLayer.SYSTEM, list_order=i)
        )
    for i in range(10000):
        rules.append(
            Rule(id=f"y{i}", source=f"syn{i:05d}", target=f"Y{i}", whole_word=True, case_sensitive=False,
                 enabled=True, layer=RuleLayer.SYSTEM, list_order=1000 + i)
        )

    t0 = time.perf_counter()
    compiled = compile_rules(rules)
    compile_s = time.perf_counter() - t0
    assert compile_s < 0.5, f"compile_rules took {compile_s:.3f}s"

    text = " ".join(f"word{i}" for i in range(20000 // 5))[:20000]
    t0 = time.perf_counter()
    apply_pronunciation_rules(text, compiled)
    apply_s = time.perf_counter() - t0
    assert apply_s < 0.2, f"apply_pronunciation_rules took {apply_s:.3f}s"


# --- dictionary import / export / merge ---------------------------------------


def _imported_rule_from_vector(v: dict) -> ImportedRule:
    return ImportedRule(
        source=v["source"], target=v["target"], whole_word=v["whole_word"],
        case_sensitive=v["case_sensitive"], enabled=v["enabled"],
    )


@pytest.mark.parametrize("vector", IMPORT_VECTORS["parse_vectors"], ids=lambda v: v["description"])
def test_parse_dictionary_import_vectors(vector: dict) -> None:
    rules, errors = parse_dictionary_import(vector["input"])
    expected_rules = tuple(_imported_rule_from_vector(r) for r in vector["expected_rules"])
    assert rules == expected_rules
    assert [e.line for e in errors] == vector["expected_error_lines"]


@pytest.mark.parametrize("vector", IMPORT_VECTORS["merge_vectors"], ids=lambda v: v["description"])
def test_merge_imported_rules_vectors(vector: dict) -> None:
    existing = [_imported_rule_from_vector(r) for r in vector["existing"]]
    imported = [_imported_rule_from_vector(r) for r in vector["imported"]]
    result = merge_imported_rules(existing, imported)
    if "expected_error" in vector:
        assert result.error == vector["expected_error"]
        assert result.rules == ()
    else:
        assert result.error is None
        assert result.rules == tuple(_imported_rule_from_vector(r) for r in vector["expected_rules"])


# --- validate_rule / export (not vector-driven; no dedicated vector file) ----


def test_validate_rule_rejects_newline_tab_and_equals_in_source() -> None:
    from vieneu_portal.text.dictionary_import_export_and_merge import validate_rule

    assert validate_rule("a\nb", "ok") != []
    assert validate_rule("a\tb", "ok") != []
    assert validate_rule("a=b", "ok") != []
    assert validate_rule("", "ok") != []
    assert validate_rule("x" * 256, "ok") != []
    assert validate_rule("ok", "ok") == []


def test_export_dictionary_txt_round_trips() -> None:
    from vieneu_portal.text.dictionary_import_export_and_merge import export_dictionary_txt

    rules = [
        ImportedRule(source="VieNeu", target="Vi Nơi"),
        ImportedRule(source="GPU", target="Gờ Pê U = viết tắt"),  # target may contain '='
    ]
    text = export_dictionary_txt(rules)
    reimported, errors = parse_dictionary_import(text)
    assert errors == ()
    assert reimported == tuple(rules)


def test_import_too_large_is_rejected_not_truncated() -> None:
    from vieneu_portal.text.dictionary_import_export_and_merge import ImportTooLargeError

    with pytest.raises(ImportTooLargeError):
        parse_dictionary_import("x" * 1_000_001)
    with pytest.raises(ImportTooLargeError):
        parse_dictionary_import("\n" * 5001)
