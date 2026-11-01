"""Small text helpers shared by the preprocessor stages."""
from __future__ import annotations

import re
from typing import Iterable, Optional

_VOWELS = ("aàáảãạăằắẳẵặâầấẩẫậeèéẻẽẹêềếểễệiìíỉĩịoòóỏõọôồốổỗộơờớởỡợ"
           "uùúủũụưừứửữựyỳýỷỹỵ")
_VI_SYLLABLE_RE = re.compile(
    rf"^(?:ngh|ng|gh|gi|kh|nh|ph|qu|th|tr|ch|[bcdđghklmnprstvx])?[{_VOWELS}]{{1,3}}"
    r"(?:ng|nh|ch|[cmnpt])?$")
_SENT_BOUNDARY_RE = re.compile(r'[.!?]+"?(\s+)')
_WORD_TOKEN_RE = re.compile(r"(?<!\S)(?=\S*[^\W_])\S+")
_EDGE_PUNCT ="\"'“”‘’()[]{}.,;:!?…—-"


def word_count(text: str) -> int:
    """Count whitespace-separated tokens that contain at least one letter or digit."""
    return len(_WORD_TOKEN_RE.findall(text))


def split_sentences(text: str) -> list[str]:
    """Split at `.`, `!`, `?` (or `...`) followed by whitespace and an upper-case start.

    `... con biết` (ellipsis + lower case) stays inside one sentence.
    """
    out: list[str] = []
    start = 0
    for m in _SENT_BOUNDARY_RE.finditer(text):
        nxt = text[m.end():m.end() + 2].lstrip('"')
        if nxt[:1] and (nxt[0].isupper() or nxt[0].isdigit()):
            piece = text[start:m.start(1)].strip()
            if piece:
                out.append(piece)
            start = m.end()
    tail = text[start:].strip()
    if tail:
        out.append(tail)
    return out


def bare_word(token: str) -> str:
    return token.strip(_EDGE_PUNCT)


def first_word(text: str) -> str:
    for tok in text.split():
        w = bare_word(tok)
        if w:
            return w
    return ""


def is_vietnamese_syllable(word: str) -> bool:
    return bool(_VI_SYLLABLE_RE.match(word.lower()))


def is_proper_name(word: str, known_names: Iterable[str] = ()) -> bool:
    """Capitalised word that is either a known name or not a Vietnamese syllable (Dracaena)."""
    if not word or not word[0].isupper():
        return False
    if word in known_names:
        return True
    parts = [p for p in re.split(r"[-']", word) if p]
    return any(not is_vietnamese_syllable(p) for p in parts)


def starts_with_phrase(text: str, phrases: Iterable[str]) -> Optional[str]:
    """Return the longest phrase that `text` starts with as whole words (case-insensitive)."""
    low = text.lstrip(_EDGE_PUNCT + " ").casefold()
    best = None
    for p in phrases:
        pl = p.casefold()
        if low.startswith(pl) and (len(low) == len(pl) or not low[len(pl)].isalnum()):
            if best is None or len(p) > len(best):
                best = p
    return best


def contains_phrase(text: str, phrase: str) -> bool:
    return re.search(rf"(?<!\w){re.escape(phrase.casefold())}(?!\w)", text.casefold()) is not None


def capitalize_first(text: str) -> str:
    for i, ch in enumerate(text):
        if ch.isalpha():
            return text[:i] + ch.upper() + text[i + 1:]
    return text


def is_all_caps_word(word: str, min_letters: int) -> bool:
    letters = [c for c in word if c.isalpha()]
    return len(letters) >= min_letters and all(c.isupper() for c in letters)


def soft_end(text: str) -> str:
    """Ensure a clause ends with the soft pause `...` (`A,` -> `A,...`, `A.` stays)."""
    t = text.rstrip()
    if t.endswith("...") or t[-1:] in ".!?":
        return t
    return t + "..."


def format_pause(sec: float) -> str:
    """`0.35` -> `[0.35]`, `0.6` -> `[0.6]`, `1.0` -> `[1.0]`."""
    s = f"{sec:.2f}"
    if s.endswith("0"):
        s = s[:-1]
    return f"[{s}]"
