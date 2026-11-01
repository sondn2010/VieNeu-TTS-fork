"""Stage 1: text sanitizer (spec section 3, tier 1).

Produces one paragraph per line with unified punctuation, chapter metadata
removed, scene breaks normalised to `***` and lost drop-cap letters recovered.
"""
from __future__ import annotations

import re
import unicodedata

from .rules import Rules
from .text_utils import word_count

SCENE_BREAK = "***"
_FRONT_MATTER_RE = re.compile(r"\A---\n.*?\n---\n", re.S)
_HEADING_RE = re.compile(r"^#{1,6}\s+")
_QUOTE_MARK_RE = re.compile(r"^(?:>\s?)+")
_EMPHASIS_RE = re.compile(r"\*{1,3}|(?<!\w)_{1,2}|_{1,2}(?!\w)")
_TABLE_RULE_RE = re.compile(r"^\|?[\s:\-|]+\|?$")
_QUOTES = {"“": '"', "”": '"', "„": '"', "‟": '"', "″": '"', "＂": '"'}
_FIELD_SPLIT_RE = re.compile(r"[,;|\t]")


def unify_punctuation(line: str) -> str:
    """Quotes -> `"`, en dash / `--` -> `—`, `…` -> `...`, single spaces."""
    line = line.replace("…", "...")
    for src, dst in _QUOTES.items():
        line = line.replace(src, dst)
    line = re.sub(r"«\s*", '"', line)
    line = re.sub(r"\s*»", '"', line)
    line = line.replace("–", "—").replace("--", "—")
    line = re.sub(r"\s*—\s*", " — ", line).strip()
    if line.startswith("— "):
        line = "— " + line[2:].lstrip()
    return " ".join(line.split())


def _is_scene_marker(line: str, rules: Rules) -> bool:
    compact = line.replace("…", "...").strip()
    return compact in rules.scene_markers


def _is_metadata(line: str, rules: Rules, patterns: list[re.Pattern]) -> bool:
    if any(p.search(line) for p in patterns) or _TABLE_RULE_RE.match(line):
        return True
    fields = [f.strip() for f in _FIELD_SPLIT_RE.split(line)]
    if len(fields) < rules.csv_min_fields or line.rstrip()[-1:] in ".!?\"":
        return False
    return (all(word_count(f) <= rules.csv_max_field_words for f in fields)
            and any(re.fullmatch(r"\d[\d.:]*", f) for f in fields))


def recover_drop_cap(line: str, rules: Rules) -> str:
    """`ặt nước` -> `Mặt nước`, `hi ông` -> `Khi ông`; other lower-case starts are capitalised."""
    head, sep, rest = line.partition(" ")
    if not head or not head[0].isalpha() or head[0].isupper():
        return line
    core = head.rstrip(",.;:!?")
    tail = head[len(core):]
    for opener in rules.drop_cap_openers:
        if opener[1:].casefold() == core.casefold():
            return opener + tail + sep + rest
    return head[0].upper() + head[1:] + sep + rest


def sanitize(text: str, rules: Rules) -> str:
    """Return normalised text: one paragraph per line, scene breaks as `***`."""
    text = unicodedata.normalize("NFC", text.replace("\r\n", "\n").replace("\r", "\n"))
    text = _FRONT_MATTER_RE.sub("", text.lstrip("\ufeff"))
    patterns = [re.compile(p, re.I) for p in rules.metadata_patterns]
    out: list[str] = []
    needs_drop_cap = True  # first body paragraph of the chapter or after a heading
    raw_lines = text.split("\n")
    i = 0
    while i < len(raw_lines):
        line = _QUOTE_MARK_RE.sub("", raw_lines[i].strip()).strip()
        i += 1
        if not line:
            continue
        if _is_scene_marker(line, rules):
            if out and out[-1] != SCENE_BREAK:
                out.append(SCENE_BREAK)
            continue
        is_heading = bool(_HEADING_RE.match(line))
        line = _EMPHASIS_RE.sub("", _HEADING_RE.sub("", line)).strip()
        if not line or _is_metadata(line, rules, patterns):  # before dash rewriting (`| --- |`)
            continue
        line = unify_punctuation(line)
        # A drop-cap letter rendered on its own line: glue it to the next line's word.
        if len(line) == 1 and line.isalpha() and line.isupper():
            while i < len(raw_lines) and not raw_lines[i].strip():
                i += 1
            if i < len(raw_lines):
                nxt = _QUOTE_MARK_RE.sub("", raw_lines[i].strip()).strip()
                line = unify_punctuation(line + _EMPHASIS_RE.sub("", nxt))
                i += 1
        if is_heading:
            out.append(line)
            needs_drop_cap = True
            continue
        if needs_drop_cap:
            line = recover_drop_cap(line, rules)
            needs_drop_cap = False
        out.append(line)
    while out and out[0] == SCENE_BREAK:
        out.pop(0)
    return "\n".join(out)
