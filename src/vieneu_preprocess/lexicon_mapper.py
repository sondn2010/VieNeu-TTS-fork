"""Stage 4: lexicon and phonetic mapper (spec section 4.4).

Terms are always compiled through `re.escape()` (symbols such as `C++`, `C#`,
`.NET` are literal, never regex syntax). One alternation, longest term first,
so the longest term wins at each position. Word boundaries are applied only on
the sides of a term that end in a word character. Text inside `<en>…</en>`,
`[…]` and `<|…|>` is never touched.

Order matters: lexicon replacement runs first so case-sensitive acronyms match
their original casing; only the remaining unmapped ALL-CAPS words of
`caps_min_letters`+ letters are converted to Title Case afterwards.
"""
from __future__ import annotations

import re
from functools import lru_cache
from typing import Optional, Sequence

from .types import LexiconEntry

_PROTECTED_RE = re.compile(r"(<en>.*?</en>|\[[^\]]*\]|<\|.*?\|>)", re.S)
_CAPS_WORD_RE = re.compile(r"(?<!\w)[^\W\d_]+(?!\w)")


class LexiconMatcher:
    def __init__(self, entries: Sequence[LexiconEntry]) -> None:
        self._exact: dict[str, LexiconEntry] = {}
        self._folded: dict[str, LexiconEntry] = {}
        for e in entries:
            if not e.term:
                continue
            if e.case_sensitive:
                self._exact.setdefault(e.term, e)
            else:
                self._folded.setdefault(e.term.casefold(), e)
        alts = []
        for e in sorted(list(self._exact.values()) + list(self._folded.values()),
                        key=lambda e: len(e.term), reverse=True):
            body = re.escape(e.term)
            if not e.case_sensitive:
                body = f"(?i:{body})"
            left = r"(?<!\w)" if e.term[0].isalnum() or e.term[0] == "_" else ""
            right = r"(?!\w)" if e.term[-1].isalnum() or e.term[-1] == "_" else ""
            alts.append(f"{left}{body}{right}")
        self.pattern: Optional[re.Pattern] = re.compile("|".join(alts)) if alts else None

    def lookup(self, matched: str) -> Optional[LexiconEntry]:
        return self._exact.get(matched) or self._folded.get(matched.casefold())


@lru_cache(maxsize=32)
def _matcher(entries: tuple[LexiconEntry, ...]) -> LexiconMatcher:
    return LexiconMatcher(entries)


def _replacement(entry: LexiconEntry, matched: str) -> str:
    if entry.mode == "en":
        return f"<en>{matched}</en>"
    rep = entry.replacement
    # Case rule: a lower-case term matched with a capital (sentence start) keeps the capital.
    if matched[:1].isupper() and entry.term[:1].islower() and rep[:1].islower():
        rep = rep[0].upper() + rep[1:]
    return rep


def _caps_to_title(text: str, min_letters: int) -> str:
    def fix(m: re.Match) -> str:
        w = m.group()
        return w[0] + w[1:].lower() if len(w) >= min_letters and w.isupper() else w
    return _CAPS_WORD_RE.sub(fix, text)


def _map_plain(text: str, matcher: LexiconMatcher, min_letters: int) -> str:
    if matcher.pattern is None:
        return _caps_to_title(text, min_letters)
    out, pos = [], 0
    for m in matcher.pattern.finditer(text):
        entry = matcher.lookup(m.group())
        if entry is None:  # defensive: alternation and lookup tables are built from the same entries
            continue
        out.append(_caps_to_title(text[pos:m.start()], min_letters))
        out.append(_replacement(entry, m.group()))
        pos = m.end()
    out.append(_caps_to_title(text[pos:], min_letters))
    return "".join(out)


def map_lexicon(text: str, entries: Sequence[LexiconEntry], *, caps_min_letters: int = 4) -> str:
    """Apply lexicon entries, then Title-case leftover ALL-CAPS words, outside protected regions."""
    matcher = _matcher(tuple(entries))
    parts = _PROTECTED_RE.split(text)
    return "".join(part if i % 2 else _map_plain(part, matcher, caps_min_letters)
                   for i, part in enumerate(parts))
