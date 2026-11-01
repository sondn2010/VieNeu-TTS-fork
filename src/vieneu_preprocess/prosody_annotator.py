"""Stage 3: prosody and pause engine (spec section 4).

Applies the P-01…P-14 matrix, the progressive countdown ladder, section 4.3
emotion tags and speeds, and P-07 shout pauses. Chunks are cut at hard pauses
only (section 4.1); soft pauses stay in the text as `...`.
"""
from __future__ import annotations

from itertools import groupby
from typing import Optional

from .prosody_clause_splitter import split_sentence
from .rules import EmotionRule, Rules
from .segment_types import AnnotatedChunk, Segment
from .text_utils import contains_phrase, split_sentences, word_count
from .types import Chunk

_ROLE_TYPES = {"narration": "narration", "dialogue": "dialogue",
               "shout": "dialogue_shout", "inner_voice": "inner_voice"}


def _ladder(values: tuple[float, ...], k: int) -> float:
    return values[min(k, len(values) - 1)]


def _countdown_positions(items: list[tuple[Segment, str, int]], rules: Rules) -> dict[int, int]:
    """Item index -> position in its countdown run (section 2 row 3 / P-05)."""
    cd = rules.countdown
    out: dict[int, int] = {}
    run: list[int] = []

    def flush() -> None:
        timed = all(any(contains_phrase(items[i][1], w) for w in cd.time_words) for i in run)
        if len(run) >= cd.min_run or (len(run) >= cd.time_run_min and timed):
            out.update({i: k for k, i in enumerate(run)})
        run.clear()

    for i, (seg, _, n) in enumerate(items):
        if seg.kind == "narration" and n <= cd.max_words:
            run.append(i)
        else:
            flush()
    flush()
    return out


def _sentence_end_pause(sentence: str, n: int, edge: bool, rules: Rules) -> float:
    p, t = rules.pauses, rules.thresholds
    s = sentence.rstrip().rstrip('"').rstrip()
    if s.endswith(":"):
        mind = any(contains_phrase(s, cue) for cue in rules.mind_cues)
        return p.p12_inner_voice if mind else p.p11_dialogue_narration
    if s.endswith(("?", "!")):
        return p.p06_question_exclaim
    if n <= t.emphatic_max_words and edge:
        return p.p04_emphatic_short
    if n <= t.p01_max_words:
        return p.p01_short_narration
    if n < t.p03_min_words:
        return p.p02_standard_narration
    return p.p03_long_narration


def _segment_speed(seg: Segment, emo: Optional[EmotionRule], rules: Rules) -> float:
    fixed = {"shout": "shout", "inner_voice": "inner"}.get(seg.kind)
    rule = rules.emotion(fixed) if fixed else emo
    return rule.speed if rule is not None and seg.kind != "narration" else 1.0


class ProsodyAnnotator:
    def __init__(self, rules: Rules, *, chapter: int = 1) -> None:
        self.rules, self.chapter = rules, chapter

    def _chunk_id(self, para: int, k: int) -> str:
        return f"{self.rules.chunk_prefix}{self.chapter:02d}_p{para:02d}_s{k:02d}"

    def annotate(self, segments: list[Segment]) -> list[AnnotatedChunk]:
        out: list[AnnotatedChunk] = []
        scene = 1
        for is_break, group in groupby(segments, key=lambda s: s.kind == "scene_break"):
            if is_break:
                if out:
                    last = out[-1].chunk
                    last.pause_after_sec = max(last.pause_after_sec, self.rules.pauses.p14_scene)
                scene += 1
                continue
            for _, para_segs in groupby(group, key=lambda s: s.paragraph):
                out.extend(self._paragraph(list(para_segs), scene))
        return out

    def _paragraph(self, segs: list[Segment], scene: int) -> list[AnnotatedChunk]:
        r, p = self.rules, self.rules.pauses
        items: list[tuple[Segment, str, int]] = []
        for seg in segs:
            sentences = [seg.text] if seg.kind == "shout" else split_sentences(seg.text)
            items.extend((seg, s, word_count(s)) for s in sentences)
        countdown = _countdown_positions(items, r)
        chunks: list[AnnotatedChunk] = []
        para = segs[0].paragraph
        for i, (seg, sentence, n) in enumerate(items):
            emo = r.emotion(seg.emotion) if seg.emotion else None
            seg_first = i == 0 or items[i - 1][0] is not seg
            seg_last = i == len(items) - 1 or items[i + 1][0] is not seg
            pieces = split_sentence(sentence, seg.kind, r, fast=emo is not None and emo.name == "fast")
            texts = [t for t, _ in pieces]
            k = countdown.get(i)
            if k is not None:
                end = _ladder(r.countdown.ladder, k)
                if texts[-1].endswith(".") and not texts[-1].endswith("..."):
                    texts[-1] = texts[-1][:-1] + r.countdown.soft_ending
            else:
                end = _sentence_end_pause(sentence, n, i in (0, len(items) - 1), r)
                if seg.kind == "dialogue" and emo is not None and emo.end_pause is not None:
                    end = emo.end_pause
            if seg.kind in ("dialogue", "shout") and emo is not None and emo.tag:
                if emo.position == "before" and seg_first:
                    texts[0] = f"{emo.tag} {texts[0]}"
                elif emo.position == "after" and seg_last:
                    texts[-1] = f"{texts[-1]} {emo.tag}"
            role = "narration_countdown" if k is not None else _ROLE_TYPES[seg.kind]
            speed = _ladder(r.countdown.speed_ladder, k) if k is not None else _segment_speed(seg, emo, r)
            speaker = seg.speaker or r.narrator
            for j, text in enumerate(texts):
                pause_after = pieces[j][1] if j < len(texts) - 1 else end
                chunk = Chunk(chunk_id=self._chunk_id(para, len(chunks) + 1), speaker=speaker,
                              role_type=role, text=text, speed=speed,
                              pause_after_sec=float(pause_after or 0.0), temperature=r.temperature)
                ac = AnnotatedChunk(chunk, para, scene)
                if seg.kind == "shout":
                    if seg_first and j == 0:
                        chunk.pause_before_sec = p.p07_shout_before
                    if seg_last and j == len(texts) - 1:
                        chunk.pause_after_sec, ac.pause_locked = p.p07_shout_after, True
                chunks.append(ac)
            if seg_last and i < len(items) - 1:
                self._raise_turn_boundary(chunks[-1], seg, items[i + 1][0])
        if chunks and not chunks[-1].pause_locked:
            last = chunks[-1].chunk
            last.pause_after_sec = max(last.pause_after_sec, p.p13_paragraph)
        return chunks

    def _raise_turn_boundary(self, ac: AnnotatedChunk, seg: Segment, nxt: Segment) -> None:
        """P-11 / P-12 at a speaker change inside a paragraph."""
        if ac.pause_locked or (seg.kind == nxt.kind and seg.speaker == nxt.speaker):
            return
        p = self.rules.pauses
        pause = p.p12_inner_voice if "inner_voice" in (seg.kind, nxt.kind) else p.p11_dialogue_narration
        ac.chunk.pause_after_sec = max(ac.chunk.pause_after_sec, pause)
