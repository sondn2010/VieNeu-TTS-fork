"""Speaker and emotion attribution from dialogue tags (`chiếc nón thì thầm`, `— Gandalf nói`)."""
from __future__ import annotations

import re
from typing import Optional

from .rules import Rules
from .text_utils import capitalize_first, word_count

_TAG_STRIP = " \t,.;:!?—\""


def _find_phrase(text_cf: str, phrase: str) -> int:
    m = re.search(rf"(?<!\w){re.escape(phrase.casefold())}(?!\w)", text_cf)
    return m.start() if m else -1


def strip_lead_words(tag: str, rules: Rules) -> str:
    """Drop leading connectors (`Rồi chiếc nón` -> `chiếc nón`)."""
    changed = True
    while changed:
        changed = False
        for lead in sorted(rules.tag_lead_words, key=len, reverse=True):
            cf = tag.casefold()
            lc = lead.casefold()
            if cf.startswith(lc) and (len(cf) == len(lc) or not cf[len(lc)].isalnum()):
                tag = tag[len(lead):].lstrip(" ,")
                changed = True
                break
    return tag


def find_speech_verb(tag: str, rules: Rules) -> Optional[tuple[int, str]]:
    """Earliest speech verb in `tag` (longest wins at the same position)."""
    cf = tag.casefold()
    best: Optional[tuple[int, str]] = None
    for verb in rules.speech_verbs:
        pos = _find_phrase(cf, verb)
        if pos >= 0 and (best is None or pos < best[0] or (pos == best[0] and len(verb) > len(best[1]))):
            best = (pos, verb)
    return best


def canonical_speaker(subject: str, rules: Rules) -> str:
    subject = " ".join(subject.strip(_TAG_STRIP).split())
    return rules.alias_for(subject) or capitalize_first(subject)


def speaker_from_tag(tag: str, rules: Rules, *, allow_bare_name: bool = False) -> tuple[Optional[str], bool]:
    """Return `(speaker, has_speech_verb)` for a dialogue tag.

    The speaker is the name or title before the first speech verb. With
    `allow_bare_name` (Vietnamese–French `"…" — Tên`), a short capitalised tag
    without a verb is taken as the name itself.
    """
    body = strip_lead_words(tag.strip(_TAG_STRIP), rules)
    hit = find_speech_verb(body, rules)
    if hit is not None:
        subject = body[:hit[0]].strip(_TAG_STRIP)
        if subject and word_count(subject) <= rules.max_subject_words:
            return canonical_speaker(subject, rules), True
        return None, True
    if allow_bare_name and body[:1].isupper() and 0 < word_count(body) <= rules.max_subject_words:
        return canonical_speaker(body, rules), False
    return None, False


def detect_emotion(tag: str, rules: Rules) -> Optional[str]:
    """Section 4.3: the emotion group whose longest keyword appears in the tag."""
    cf = tag.casefold()
    best: Optional[tuple[int, str]] = None
    for rule in rules.emotions:
        for kw in rule.keywords:
            if _find_phrase(cf, kw) >= 0 and (best is None or len(kw) > best[0]):
                best = (len(kw), rule.name)
    return best[1] if best else None
