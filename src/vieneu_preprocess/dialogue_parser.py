"""Stage 2: discourse and dialogue parser (spec section 3, tier 2).

Splits sanitised paragraphs into narration, dialogue, shout and inner-voice
segments. Handles Vietnamese–French `"…" — Tên nói.` and English–American
`"…," tag. "…"` dialogue (the split-dialogue linker gives the second quote the
first quote's speaker), the embedded-quote guard, colon-introduced lines
(`Rồi chiếc nón hét vang:` followed by a quote-only paragraph) and telepathy.
"""
from __future__ import annotations

import re
from typing import Optional

from .inner_voice_detector import InnerVoiceTracker
from .rules import Rules
from .sanitizer import SCENE_BREAK
from .segment_types import Segment
from .speaker_attribution import detect_emotion, speaker_from_tag
from .text_utils import (
    bare_word, capitalize_first, is_all_caps_word, split_sentences, word_count,
)

_QUOTE_SPLIT_RE = re.compile(r'("[^"]*")')
_TAG_END_RE = re.compile(r"[.!?](?=\s|$)")
_ROLL_CALL_RE = re.compile(r"^([^,]+),\s*([^,]+?)([!?.]+)$")

Attribution = tuple[Optional[str], Optional[str]]  # (speaker, emotion)


def collect_known_names(text: str) -> set[str]:
    """Capitalised words seen mid-sentence (`nhà Malfoy`, `tháng Chín`) count as names."""
    names: set[str] = set()
    for line in text.split("\n"):
        for sentence in split_sentences(line):
            prev = ""
            for tok in sentence.split()[1:]:
                w = bare_word(tok)
                if w[:1].isupper() and not tok.startswith('"') and prev[-1:] not in ':—"':
                    names.add(w)
                prev = tok
    return names


def is_roll_call(content: str) -> bool:
    m = _ROLL_CALL_RE.match(content.strip())
    return bool(m) and all(p.strip()[:1].isupper() and word_count(p) <= 2 for p in m.groups()[:2])


def _is_embedded(before: str, quote: str, after: str, rules: Rules) -> bool:
    """Section 2 row 6: `câu nói "..." vẫn vương lại` stays narration."""
    b, q, a = before.rstrip(), quote.strip(), after.lstrip()
    if not b or b[-1] in '.!?:—,' or not a or q[-1:] in ".!?" or "—" in q:
        return False
    if not (a[0].islower() or a[0] in ",;"):
        return False
    tail = b.casefold()
    return any(re.search(rf"(?<!\w){re.escape(n.casefold())}$", tail) for n in rules.embedded_quote_nouns)


def _split_parts(line: str, rules: Rules) -> list[tuple[str, str]]:
    """[("text"|"quote", s)], with embedded quotes folded back into the text."""
    if line.count('"') % 2:
        line += '"'  # a quote left open runs to the end of the paragraph
    raw = _QUOTE_SPLIT_RE.split(line)
    items: list[tuple[str, str]] = []
    i = 0
    while i < len(raw):
        piece = raw[i]
        if i % 2 == 1 and items and items[-1][0] == "text" and i + 1 < len(raw) \
                and _is_embedded(items[-1][1], piece[1:-1], raw[i + 1], rules):
            items[-1] = ("text", items[-1][1] + piece + raw[i + 1])
            i += 2
            continue
        if i % 2 == 1:
            items.append(("quote", piece[1:-1]))
        elif items and items[-1][0] == "text":
            items[-1] = ("text", items[-1][1] + piece)
        else:
            items.append(("text", piece))
        i += 1
    return items


def _take_tag(after: str, content: str) -> Optional[tuple[str, str, bool]]:
    """Dialogue tag right after a quote: (tag, remainder, is_dash_form)."""
    a = after.lstrip()
    dash = a.startswith("—")
    if dash:
        a = a[1:].lstrip()
    elif not (content.rstrip().endswith(",") or a[:1].islower()):
        return None
    if not a:
        return None
    m = _TAG_END_RE.search(a)
    end = m.end() if m else len(a)
    return a[:end], a[end:], dash


class DialogueParser:
    def __init__(self, rules: Rules, text: str) -> None:
        self.rules = rules
        self.inner = InnerVoiceTracker(rules, collect_known_names(text))
        self.pending: Attribution = (None, None)  # from a paragraph ending `... hét vang:`

    def parse(self, text: str) -> list[Segment]:
        out: list[Segment] = []
        para = 0
        for line in text.split("\n"):
            line = line.strip()
            if not line:
                continue
            if line == SCENE_BREAK:
                self.inner.close()
                self.pending = (None, None)
                out.append(Segment("scene_break", "", 0))
                continue
            para += 1
            pending, self.pending = self.pending, (None, None)
            if '"' in line:
                self.inner.close()
                out.extend(self._quoted_paragraph(line, para, pending))
            else:
                segs = self.inner.process(line, para)
                out.extend(segs if segs is not None else [Segment("narration", line, para)])
            self._note_colon(line)
        self.inner.close()
        return out

    def _note_colon(self, line: str) -> None:
        last = (split_sentences(line) or [""])[-1]
        if not last.endswith(":") or '"' in last:
            return
        if self.inner.is_mind_cue_colon(last):
            if not self.inner.active:
                self.inner.open()
            return
        speaker, has_verb = speaker_from_tag(last, self.rules)
        if has_verb:
            self.pending = (self._resolve_pronoun(speaker), detect_emotion(last, self.rules))

    def _resolve_pronoun(self, speaker: Optional[str]) -> Optional[str]:
        """`Hắn` -> the latest named narration subject, when one is known."""
        if speaker and self.inner.last_subject and speaker.casefold() in {
                p.casefold() for p in self.rules.pronoun_subjects}:
            return self.inner.last_subject
        return speaker

    def _attribution_from_before(self, before: str) -> Attribution:
        b = before.rstrip()
        if not b.endswith((":", ",")):
            return None, None
        last = (split_sentences(b) or [""])[-1]
        speaker, has_verb = speaker_from_tag(last, self.rules)
        return (speaker, detect_emotion(last, self.rules)) if has_verb else (None, None)

    def _quoted_paragraph(self, line: str, para: int, pending: Attribution) -> list[Segment]:
        r = self.rules
        items = _split_parts(line, r)
        standalone = len(items) == 1 or all(k == "quote" or not s.strip(" .,") for k, s in items)
        out: list[Segment] = []
        prev: Attribution = (None, None)
        first_quote = True
        for idx, (kind, s) in enumerate(items):
            if kind == "text":
                if s.strip(" .,;—"):
                    out.append(Segment("narration", capitalize_first(s.strip(" ,;")), para))
                    for sentence in split_sentences(s.strip()):
                        self.inner.note_narration(sentence)
                continue
            content = s.strip()
            if not content:
                continue
            speaker, emotion = None, None
            tag_seg: Optional[Segment] = None
            nxt = items[idx + 1] if idx + 1 < len(items) else None
            if nxt is not None and nxt[0] == "text":
                taken = _take_tag(nxt[1], content)
                if taken is not None:
                    tag, rest, dash = taken
                    spk, has_verb = speaker_from_tag(tag, r, allow_bare_name=dash)
                    if spk is not None or has_verb:
                        speaker, emotion = spk, detect_emotion(tag, r)
                        items[idx + 1] = ("text", rest)
                        if has_verb:  # a bare `— Tên` attribution is not read aloud
                            tag_text = tag.strip(" ,—").rstrip(",")
                            tag_text = tag_text if tag_text[-1:] in ".!?" else tag_text + "."
                            tag_seg = Segment("narration", capitalize_first(tag_text), para)
            if speaker is None and idx > 0 and items[idx - 1][0] == "text":
                speaker, emotion = self._attribution_from_before(items[idx - 1][1])
            speaker = self._resolve_pronoun(speaker)
            if speaker is None and prev[0] is not None:
                speaker, emotion = prev  # split-dialogue linker
            if speaker is None and first_quote and pending[0] is not None:
                speaker, emotion = pending
            if speaker is None:
                speaker = (r.roll_call_speaker or r.unknown_label) if is_roll_call(content) else r.unknown_label
            if content.endswith(","):
                content = content[:-1].rstrip() + "."
            letters_caps = is_all_caps_word(content.replace(" ", ""), r.thresholds.caps_min_letters)
            short_shout = standalone and word_count(content) <= r.thresholds.shout_max_words \
                and (content.endswith("!") or letters_caps)
            seg_kind = "shout" if short_shout or letters_caps or emotion == "shout" else "dialogue"
            out.append(Segment(seg_kind, content, para, speaker, emotion))
            if tag_seg is not None:
                out.append(tag_seg)
            prev, first_quote = (speaker, emotion), False
        return out


def parse_segments(text: str, rules: Rules) -> list[Segment]:
    return DialogueParser(rules, text).parse(text)


__all__ = ["DialogueParser", "parse_segments", "collect_known_names", "is_roll_call"]
