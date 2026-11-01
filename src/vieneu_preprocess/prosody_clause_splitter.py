"""Sentence-internal hard pauses for stage 3.

Turns one sentence into pieces `[(text, pause_after_or_None)]`; the last piece
always has `None` (its pause comes from the sentence-end rules). Covers P-08,
P-09, P-10, the embedded-quote wrap (section 2 row 6), the roll-call split
(section 2 row 4) and the inner-voice soft comma (section 4.3).
"""
from __future__ import annotations

import re
from typing import Optional

from .dialogue_parser import is_roll_call
from .rules import Rules
from .text_utils import soft_end, starts_with_phrase, word_count

Piece = tuple[str, Optional[float]]
_EMBEDDED_RE = re.compile(r'"[^"]+"')
_DASH_RE = re.compile(r"\s*—\s*")
_ROLL_CALL_PARTS_RE = re.compile(r"^([^,]+),\s*(.+)$")


def _split_embedded(text: str, rules: Rules) -> list[tuple[str, Optional[float], bool]]:
    """`câu nói "X" vẫn` -> `câu nói...` [0.2] `"X"` [0.25] `vẫn`; bool marks quote pieces."""
    p = rules.pauses
    out: list[tuple[str, Optional[float], bool]] = []
    pos = 0
    for m in _EMBEDDED_RE.finditer(text):
        before = text[pos:m.start()].strip()
        if not before:
            continue
        out.append((soft_end(before), p.embedded_quote_before, False))
        out.append((m.group(), p.embedded_quote_after, True))
        pos = m.end()
    rest = text[pos:].strip(" ,")
    if rest:
        out.append((rest, None, False))
    elif out:
        out[-1] = (out[-1][0], None, out[-1][2])
    return out or [(text, None, False)]


def split_dashes(text: str, rules: Rules) -> list[Piece]:
    """P-08 `A — B — C` -> A... [0.3] B... [0.35] C ; P-09 `A — B.` -> A... [0.4] B."""
    parts = [s for s in _DASH_RE.split(text)]
    if parts and not parts[0].strip():
        parts = parts[1:]
    if parts and not parts[-1].strip():
        parts = parts[:-1]
    if len(parts) < 2:
        return [(text.strip(), None)]
    p, d = rules.pauses, len(parts) - 1
    out: list[Piece] = []
    for j in range(d):
        if j % 2 == 1:
            pause = p.p08_dash_pair_close
        elif j + 1 < d:
            pause = p.p08_dash_pair_open
        else:
            pause = p.p09_dash_tail
        out.append((soft_end(parts[j].strip()), pause))
    out.append((parts[-1].strip(), None))
    return out


def split_long_clauses(text: str, rules: Rules) -> list[Piece]:
    """P-10: a clause of >= 18 words + `,` + connector becomes `,...` [0.3]."""
    t = rules.thresholds
    min_words = max(t.long_clause_words, t.soft_comma_max_words)
    out: list[Piece] = []
    start = 0
    for m in re.finditer(",", text):
        clause, rest = text[start:m.start()], text[m.end():]
        if word_count(clause) >= min_words and starts_with_phrase(rest, rules.long_clause_connectors):
            out.append((text[start:m.end()].strip() + "...", rules.pauses.p10_long_clause_breath))
            start = m.end()
    out.append((text[start:].strip(), None))
    return out


def split_roll_call(text: str, rules: Rules) -> list[Piece]:
    """`Potter, Harry!` -> `Potter...` [0.25] `Harry!`."""
    m = _ROLL_CALL_PARTS_RE.match(text.strip()) if is_roll_call(text) else None
    if m is None:
        return [(text, None)]
    return [(m.group(1).strip() + "...", rules.pauses.roll_call_comma), (m.group(2).strip(), None)]


def soften_inner_commas(text: str, rules: Rules) -> str:
    """Section 4.3: in inner voice, `,` after a short clause becomes `...` (`Chà, một` -> `Chà... một`)."""
    limit = rules.thresholds.inner_short_clause_words
    out, start = [], 0
    for m in re.finditer(r",", text):
        clause = re.split(r"[,.!?]", text[start:m.start()])[-1]
        out.append(text[start:m.start()])
        out.append("..." if 0 < word_count(clause) <= limit else ",")
        start = m.end()
    out.append(text[start:])
    return "".join(out)


def split_sentence(sentence: str, kind: str, rules: Rules, *, fast: bool = False) -> list[Piece]:
    """Pieces for one sentence of a segment of the given kind."""
    if kind == "shout":
        return split_roll_call(sentence, rules)
    if kind == "inner_voice":
        sentence = soften_inner_commas(sentence, rules)
    staged = _split_embedded(sentence, rules) if kind == "narration" else [(sentence, None, False)]
    out: list[Piece] = []
    for text, pause, is_quote in staged:
        if is_quote:
            out.append((text, pause))
            continue
        for d_text, d_pause in split_dashes(text, rules):
            sub = [(d_text, None)] if fast else split_long_clauses(d_text, rules)
            sub[-1] = (sub[-1][0], d_pause)
            out.extend(sub)
        out[-1] = (out[-1][0], pause)
    return [(t, p) for t, p in out if t] or [(sentence, None)]
