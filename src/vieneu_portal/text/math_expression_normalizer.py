"""Deterministic rule-based math/chem span reader. The engine's own front-end
already reads plain numbers, dates and units, so this module only fires on a
*strong* marker — a Unicode math symbol, a superscript/`^k`, or an ASCII
operator (`+ - * / < > =`) adjacent to something that already looks mathy —
never on bare ASCII alone (`2020-2021`, `5 km/h`, `A/B` stay untouched; see
the "ambiguous ASCII" split below, straight from the brainstorm/plan notes).

Whitespace-tokenizes the (NFC, already control-token-stripped) text, leaving
`[...]`, `<en>...</en>` and `<|...|>` spans (and any `protected_terms`, the
compiled dictionary's enabled source terms — `B2B`, `F0`, ...) completely
untouched so the dictionary pass can still match them afterwards.
"""
from __future__ import annotations

import re
import unicodedata
from typing import Optional, Sequence

from .chemical_equation_normalizer import read_chemical_formula_token
from .pronunciation_dictionary_single_pass_matcher import find_protected_spans
from .vietnamese_small_integer_reader import read_vietnamese_integer

# Unicode symbols are strong markers on their own (never ambiguous in prose):
# always converted wherever they appear as their own token.
_STRONG_SYMBOL_READINGS = {
    "≥": "lớn hơn hoặc bằng", "≤": "nhỏ hơn hoặc bằng", "≠": "khác", "≈": "xấp xỉ",
    "∈": "thuộc", "∉": "không thuộc", "⊂": "là tập con của",
    "∞": "vô cực", "√": "căn bậc hai của", "±": "cộng trừ",
    "×": "nhân", "·": "nhân", "÷": "chia",
    "Δ": "đen ta", "π": "pi",
    "ℝ": "tập số thực", "ℕ": "tập số tự nhiên", "ℤ": "tập số nguyên", "ℚ": "tập số hữu tỉ",
    "→": "tạo thành", "⇌": "thuận nghịch",
}

# Plain ASCII operators double as ordinary punctuation in prose
# (`2020-2021`, `km/h`, `A/B testing`) — only convert these when flanked by a
# token that already looks like part of a math/chem expression. ASCII `*`
# and `/` have no defined reading at all (always left alone: `MP3`, `A/B`,
# `km/h`).
_AMBIGUOUS_SYMBOL_READINGS = {
    "+": "cộng", "-": "trừ", "−": "trừ", "<": "nhỏ hơn", ">": "lớn hơn", "=": "bằng",
}

_ALL_DIGITS_RE = re.compile(r"^[0-9]+$")
_VARIABLE_RUN_RE = re.compile(r"^(?P<letters>[a-z]+)(?P<exp>\^[0-9]+|ⁿ|[⁰¹²³⁴⁵⁶⁷⁸⁹]+)?$")
_SUPERSCRIPT_DIGITS = {"⁰": "0", "¹": "1", "²": "2", "³": "3", "⁴": "4",
                        "⁵": "5", "⁶": "6", "⁷": "7", "⁸": "8", "⁹": "9"}
_TRAILING_PUNCT = ",.;:!?)"


def _read_exponent(exp: str) -> str:
    if exp.startswith("^"):
        k = int(exp[1:])
    elif exp == "ⁿ":
        return "mũ n"
    else:
        k = int("".join(_SUPERSCRIPT_DIGITS[ch] for ch in exp))
    if k == 2:
        return "bình phương"
    if k == 3:
        return "lập phương"
    return f"mũ {read_vietnamese_integer(k)}"


def _read_variable_run(letters: str, exp: Optional[str]) -> str:
    words = list(letters)
    if exp:
        words.append(_read_exponent(exp))
    return " ".join(words)


def _looks_mathy_shape(core: Optional[str]) -> bool:
    """Shape-only check (no adjacency) used to decide whether a *neighboring*
    ambiguous-ASCII/digit/variable token sits inside a math/chem expression."""
    if not core:
        return False
    if core in _STRONG_SYMBOL_READINGS or core in _AMBIGUOUS_SYMBOL_READINGS:
        return True
    if _ALL_DIGITS_RE.fullmatch(core):
        return True
    if _VARIABLE_RUN_RE.fullmatch(core):
        return True
    if read_chemical_formula_token(core) is not None:
        return True
    return False


def _classify_and_read(core: str, prev_mathy: bool, next_mathy: bool, protected_set: frozenset) -> Optional[str]:
    if not core or core in protected_set:
        return None
    if core in _STRONG_SYMBOL_READINGS:
        return _STRONG_SYMBOL_READINGS[core]
    if core in _AMBIGUOUS_SYMBOL_READINGS:
        return _AMBIGUOUS_SYMBOL_READINGS[core] if (prev_mathy or next_mathy) else None
    if _ALL_DIGITS_RE.fullmatch(core):
        return read_vietnamese_integer(int(core)) if (prev_mathy or next_mathy) else None
    chem = read_chemical_formula_token(core)
    if chem is not None:
        if any(ch.isdigit() for ch in core) or prev_mathy or next_mathy:
            return chem
        return None
    m = _VARIABLE_RUN_RE.fullmatch(core)
    if m:
        letters, exp = m.group("letters"), m.group("exp")
        if len(letters) == 1 or exp or prev_mathy or next_mathy:
            return _read_variable_run(letters, exp)
    return None


def _split_trailing_punct(word: str) -> tuple:
    j = len(word)
    while j > 0 and word[j - 1] in _TRAILING_PUNCT:
        j -= 1
    return word[:j], word[j:]


def normalize_math_and_chemistry(text: str, protected_terms: Sequence[str] = ()) -> str:
    protected_set = frozenset(protected_terms)
    normalized = unicodedata.normalize("NFC", text)
    cps = list(normalized)
    n = len(cps)
    span_ends = find_protected_spans(cps)

    # Pass 1: segment into ("space" | "protected" | "word", text) parts,
    # preserving exact spacing; a protected span is consumed whole.
    parts: list = []
    i = 0
    while i < n:
        end = span_ends.get(i)
        if end is not None:
            parts.append(("protected", "".join(cps[i:end])))
            i = end
            continue
        if cps[i].isspace():
            j = i
            while j < n and cps[j].isspace() and span_ends.get(j) is None:
                j += 1
            parts.append(("space", "".join(cps[i:j])))
            i = j
            continue
        j = i
        while j < n and not cps[j].isspace() and span_ends.get(j) is None:
            j += 1
        parts.append(("word", "".join(cps[i:j])))
        i = j

    # Pass 2: classify each "word" part's core (trailing punctuation split
    # off and spliced back on afterwards) using its immediate word-neighbors.
    word_indices = [idx for idx, (kind, _) in enumerate(parts) if kind == "word"]
    cores: dict = {}
    trails: dict = {}
    for idx in word_indices:
        core, trail = _split_trailing_punct(parts[idx][1])
        cores[idx] = core
        trails[idx] = trail

    for pos, idx in enumerate(word_indices):
        core = cores[idx]
        if not core:
            continue
        prev_core = cores[word_indices[pos - 1]] if pos > 0 else None
        next_core = cores[word_indices[pos + 1]] if pos + 1 < len(word_indices) else None
        reading = _classify_and_read(
            core, _looks_mathy_shape(prev_core), _looks_mathy_shape(next_core), protected_set
        )
        if reading is not None:
            kind, _ = parts[idx]
            parts[idx] = (kind, reading + trails[idx])

    return "".join(p[1] for p in parts)
