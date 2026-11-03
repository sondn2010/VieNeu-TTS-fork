"""Golden pairs for `normalize_math_and_chemistry`, including TC-04 verbatim
and its required negatives. No Postgres needed.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from vieneu_portal.text.math_expression_normalizer import normalize_math_and_chemistry

_GOLDEN_PATH = Path(__file__).parent.parent / "fixtures" / "normalization_golden" / "math_chem_vi.json"
_CASES = json.loads(_GOLDEN_PATH.read_text(encoding="utf-8"))


@pytest.mark.parametrize("case", _CASES, ids=[c["name"] for c in _CASES])
def test_golden_pair(case: dict) -> None:
    result = normalize_math_and_chemistry(case["input"], case.get("protected_terms", ()))
    assert result == case["output"]
