"""Telepathy / inner-voice detector (spec section 2 row 2).

An inner-voice passage opens after a narration colon carrying a mind cue
(`... vang lên trong tâm trí cô:`) or inside a paragraph with an interjected tag
(`Rất thông minh, chiếc nón thì thầm.`). Inside it, each sentence is classified:
narration when it starts with a proper name or a narration subject, the
listener's own thought when it starts with a first-person opener (`Tôi`), and
otherwise the telepathic voice. The voice's name is taken from the first
interjected tag and back-filled onto earlier unresolved sentences.
"""
from __future__ import annotations

import re
from typing import Optional

from .rules import Rules
from .segment_types import Segment
from .speaker_attribution import canonical_speaker
from .text_utils import (
    bare_word, capitalize_first, contains_phrase, is_proper_name, split_sentences,
    starts_with_phrase, word_count,
)


class InnerVoiceTracker:
    def __init__(self, rules: Rules, known_names: set[str]) -> None:
        self.rules = rules
        self.known_names = known_names
        self.active = False
        self.other: Optional[str] = None
        self.pending: list[Segment] = []
        self.last_subject: Optional[str] = None
        verbs = "|".join(re.escape(v) for v in sorted(rules.inner_tag_verbs, key=len, reverse=True))
        self._interjection_re = re.compile(
            rf"^(?P<a>.*?\S),\s+(?P<subj>[^,.!?:\"]{{1,60}}?)\s+(?P<verb>{verbs})"
            rf"(?P<end>[.,!?])\s*(?P<b>.*)$", re.I | re.S)

    # -- state -------------------------------------------------------------
    def open(self) -> None:
        self.close()
        self.active = True

    def close(self) -> None:
        for seg in self.pending:
            seg.speaker = self.rules.unknown_inner_label
        self.pending, self.active, self.other = [], False, None

    def _set_other(self, speaker: str) -> None:
        self.other = speaker
        for seg in self.pending:
            seg.speaker = speaker
        self.pending = []

    def is_mind_cue_colon(self, sentence: str) -> bool:
        return sentence.rstrip().endswith(":") and any(
            contains_phrase(sentence, cue) for cue in self.rules.mind_cues)

    def note_narration(self, sentence: str) -> None:
        """Remember the latest named narration subject (the owner of a later `Tôi` thought)."""
        names = []
        for tok in sentence.split():
            w = bare_word(tok)
            if not is_proper_name(w, self.known_names):
                break
            names.append(w)
        if names:
            self.last_subject = " ".join(names)

    # -- classification ----------------------------------------------------
    def _interjection(self, sentence: str) -> Optional[re.Match]:
        m = self._interjection_re.match(sentence)
        if m and word_count(m["subj"]) <= self.rules.max_subject_words:
            return m
        return None

    def _is_narration(self, sentence: str) -> bool:
        first = bare_word(sentence.split()[0]) if sentence.split() else ""
        return (is_proper_name(first, self.known_names)
                or starts_with_phrase(sentence, self.rules.narration_subjects) is not None)

    def _inner(self, text: str, para: int, *, own_thought: bool) -> Segment:
        if own_thought:
            owner = self.last_subject or self.rules.unknown_label
            return Segment("inner_voice", text, para, owner + self.rules.self_suffix, "inner")
        seg = Segment("inner_voice", text, para, self.other, "inner")
        if self.other is None:
            self.pending.append(seg)
        return seg

    def _classify(self, sentence: str, para: int) -> Segment:
        r = self.rules
        if starts_with_phrase(sentence, r.self_openers):
            return self._inner(sentence, para, own_thought=True)
        if starts_with_phrase(sentence, r.other_openers):
            return self._inner(sentence, para, own_thought=False)
        if self._is_narration(sentence):
            self.note_narration(sentence)
            return Segment("narration", sentence, para)
        return self._inner(sentence, para, own_thought=False)

    def process(self, line: str, para: int) -> Optional[list[Segment]]:
        """Segments for an unquoted paragraph, or None when it is plain narration."""
        sentences = split_sentences(line)
        has_tag = any(self._interjection(s) for s in sentences)
        if not self.active and not has_tag:
            for s in sentences:
                self.note_narration(s)
            return None
        opened_by_tag = not self.active
        self.active = True
        out: list[Segment] = []
        for s in sentences:
            m = self._interjection(s)
            if m is None:
                out.append(self._classify(s, para))
                continue
            speaker = canonical_speaker(m["subj"], self.rules)
            out.append(self._inner(m["a"].rstrip(" ,") + ".", para, own_thought=False))
            self._set_other(speaker)
            out.append(Segment("narration", capitalize_first(f"{m['subj']} {m['verb']}."), para))
            if m["b"].strip():
                out.append(self._inner(capitalize_first(m["b"].strip()), para, own_thought=False))
        has_inner = any(seg.kind == "inner_voice" for seg in out)
        ends_with_cue = bool(sentences) and self.is_mind_cue_colon(sentences[-1])
        if (not has_inner or opened_by_tag) and not ends_with_cue:
            self.close()
        return merge_adjacent(out)


def merge_adjacent(segments: list[Segment]) -> list[Segment]:
    """Join consecutive segments that share kind, speaker, emotion and paragraph.

    Unresolved inner-voice segments (speaker None) still merge: the tracker keeps
    the survivor in its pending list, so back-filling the speaker reaches it.
    """
    out: list[Segment] = []
    for seg in segments:
        prev = out[-1] if out else None
        if (prev is not None and prev.kind == seg.kind and prev.speaker == seg.speaker
                and prev.emotion == seg.emotion and prev.paragraph == seg.paragraph):
            prev.text = f"{prev.text} {seg.text}"
        else:
            out.append(seg)
    return out
