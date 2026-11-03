"""Single-pass, longest-match pronunciation dictionary matcher. Pinned by
`tests/fixtures/text_contract_vectors/dictionary_matcher_vectors.json`,
mirrored in TypeScript at `portal-web/src/lib/text/pronunciation-dictionary-single-pass-matcher.ts`.

Operates on code points (`list(text)`), not UTF-16 units — the TS mirror
uses `Array.from(text)` for the same reason. Comparisons use `.lower()`
(not `.casefold()`): `.casefold()` would map "ß" to "ss" and no longer match
JS's `.toLowerCase()`, which leaves "ß" alone. Using plain lower-casing on
both sides keeps the two implementations byte-for-byte identical, even
though a fold can change length (e.g. "İ".lower() == "i̇", two code points) —
match correctness here never depends on comparing lengths after folding,
only on direct string equality of the folded forms.
"""
from __future__ import annotations

import unicodedata
from typing import Optional

from .pronunciation_rule_types import CompiledRuleSet, Rule, RuleLayer


def _is_word_char(ch: str) -> bool:
    if ch == "_":
        return True
    return unicodedata.category(ch)[0] in ("L", "N")


def _find_literal(cps: list[str], start: int, literal: str) -> Optional[int]:
    """Index of `literal`'s first code point at or after `start`, or None."""
    lit = list(literal)
    n, m = len(cps), len(lit)
    for i in range(start, n - m + 1):
        if cps[i : i + m] == lit:
            return i
    return None


def _starts_with(cps: list[str], i: int, literal: str) -> bool:
    lit = list(literal)
    return cps[i : i + len(lit)] == lit


def find_protected_spans(cps: list[str]) -> dict[int, int]:
    """Maps a protected span's start index to its (exclusive) end index.
    `[...]`, `<en>...</en>` and `<|...|>` are never rewritten — an emotion
    tag like `[cười]` must survive a rule matching the bare word `cười`, and
    a target already wrapped in `<en>...</en>` is never rescanned. An
    unterminated opener (no closing delimiter anywhere in the rest of the
    text) is not protected — it is ordinary text.
    """
    spans: dict[int, int] = {}
    n = len(cps)
    i = 0
    while i < n:
        if cps[i] == "[":
            j = i + 1
            while j < n and cps[j] != "]":
                j += 1
            if j < n:
                spans[i] = j + 1
                i = j + 1
                continue
        elif _starts_with(cps, i, "<en>"):
            end = _find_literal(cps, i + 4, "</en>")
            if end is not None:
                spans[i] = end + 5
                i = end + 5
                continue
        elif _starts_with(cps, i, "<|"):
            end = _find_literal(cps, i + 2, "|>")
            if end is not None:
                spans[i] = end + 2
                i = end + 2
                continue
        i += 1
    return spans


def _match_at(cps: list[str], i: int, n: int, compiled: CompiledRuleSet) -> Optional[tuple[Rule, str]]:
    candidates = compiled.index.get(cps[i].lower(), ())
    for r in candidates:
        length = len(r.source)
        if i + length > n:
            continue
        candidate = "".join(cps[i : i + length])
        if r.case_sensitive:
            if candidate != r.source:
                continue
        elif candidate.lower() != r.source.lower():
            continue
        if r.whole_word:
            left_ok = i == 0 or not _is_word_char(cps[i - 1])
            right_ok = i + length >= n or not _is_word_char(cps[i + length])
            if not (left_ok and right_ok):
                continue
        return r, candidate
    return None


def _render(rule: Rule, matched_text: str) -> str:
    if rule.layer == RuleLayer.ENGLISH_FALLBACK:
        return f"<en>{matched_text}</en>"
    return rule.target


def apply_pronunciation_rules(text: str, compiled: CompiledRuleSet) -> str:
    cps = list(unicodedata.normalize("NFC", text))
    n = len(cps)
    spans = find_protected_spans(cps)

    out: list[str] = []
    i = 0
    while i < n:
        span_end = spans.get(i)
        if span_end is not None:
            out.append("".join(cps[i:span_end]))
            i = span_end
            continue
        matched = _match_at(cps, i, n, compiled)
        if matched is not None:
            rule, matched_text = matched
            out.append(_render(rule, matched_text))
            i += len(matched_text)
            continue
        out.append(cps[i])
        i += 1
    return "".join(out)
