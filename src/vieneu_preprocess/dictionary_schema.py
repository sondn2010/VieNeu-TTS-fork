"""Load, validate and dump pronunciation dictionary JSON (format vieneu-dictionary/1).

Terms are never compiled as raw regex: mapper stages must wrap them in re.escape()
so symbols such as `C++`, `C#` or `.NET` are safe.
"""
from __future__ import annotations

import json
import re
from typing import Iterable

from .types import Dictionary, LexiconEntry

FORMAT = "vieneu-dictionary/1"
KINDS = ("english", "term", "name")
MODES = ("phonetic", "en")
MAX_ENTRIES = 20_000
_KIND_RANK = {"name": 0, "term": 1, "english": 2}
_TAG_RE = re.compile(r"<[^<>]*>")


class DictionaryFormatError(ValueError):
    def __init__(self, message: str, *, line: int | None = None,
                 column: int | None = None, path: str = ""):
        super().__init__(message)
        self.line, self.column, self.path = line, column, path


def _err(msg: str, path: str) -> DictionaryFormatError:
    return DictionaryFormatError(f"{path}: {msg}" if path else msg, path=path)


def _join(path: str, key: str) -> str:
    return f"{path}.{key}" if path else key


def _str(obj: dict, key: str, path: str, *, default="", lo=0, hi=None) -> str:
    v = obj.get(key, default)
    if not isinstance(v, str):
        raise _err("must be a string", _join(path, key))
    if len(v) < lo or (hi is not None and len(v) > hi):
        raise _err(f"length must be {lo}-{hi if hi is not None else 'unbounded'}", _join(path, key))
    return v


def _bool(obj: dict, key: str, path: str, default: bool) -> bool:
    v = obj.get(key, default)
    if not isinstance(v, bool):
        raise _err("must be a boolean", _join(path, key))
    return v


def _check_replacement(rep: str, path: str) -> None:
    if "[" in rep or "]" in rep or "<|" in rep or "|>" in rep:
        raise _err("must not contain '[', ']', '<|' or '|>'", path)
    if _TAG_RE.search(rep):
        raise _err("must not contain tags", path)


def load_dictionary_json(data: str | bytes) -> Dictionary:
    try:
        obj = json.loads(data)
    except json.JSONDecodeError as e:
        raise DictionaryFormatError(
            f"Invalid JSON at line {e.lineno}, column {e.colno}: {e.msg}",
            line=e.lineno, column=e.colno) from e
    except UnicodeDecodeError as e:
        raise DictionaryFormatError(f"Invalid UTF-8: {e}") from e
    if not isinstance(obj, dict):
        raise _err("top level must be an object", "")
    if obj.get("format") != FORMAT:
        raise _err(f"must equal {FORMAT!r}", "format")
    name = _str(obj, "name", "", default=None, lo=1, hi=80)
    kind = obj.get("kind")
    if kind not in KINDS:
        raise _err(f"must be one of {KINDS}", "kind")
    enabled = _bool(obj, "enabled", "", True)
    description = _str(obj, "description", "")
    raw = obj.get("entries", [])
    if not isinstance(raw, list):
        raise _err("must be a list", "entries")
    if len(raw) > MAX_ENTRIES:
        raise _err(f"at most {MAX_ENTRIES} entries", "entries")
    entries: list[LexiconEntry] = []
    seen: set[str] = set()
    for i, e in enumerate(raw):
        p = f"entries[{i}]"
        if not isinstance(e, dict):
            raise _err("must be an object", p)
        term = _str(e, "term", p, default=None, lo=1, hi=80)
        mode = e.get("mode", "phonetic")
        if mode not in MODES:
            raise _err(f"must be one of {MODES}", f"{p}.mode")
        rep = _str(e, "replacement", p, hi=200)
        if mode == "phonetic" and not rep:
            raise _err("required for phonetic mode", f"{p}.replacement")
        _check_replacement(rep, f"{p}.replacement")
        cs = _bool(e, "case_sensitive", p, False)
        note = _str(e, "note", p)
        key = term if cs else term.casefold()
        if key in seen:
            raise _err(f"duplicate term {term!r}", f"{p}.term")
        seen.add(key)
        entries.append(LexiconEntry(term, rep, mode, cs, note))
    return Dictionary(name, kind, enabled, description, entries)


def dump_dictionary_json(d: Dictionary) -> str:
    out = {
        "format": FORMAT, "name": d.name, "kind": d.kind, "enabled": d.enabled,
        "description": d.description,
        "entries": [
            {"term": e.term, "replacement": e.replacement, "mode": e.mode,
             "case_sensitive": e.case_sensitive, "note": e.note}
            for e in sorted(d.entries, key=lambda e: e.term)
        ],
    }
    return json.dumps(out, ensure_ascii=False, indent=2)


def merge_lexicon(dicts: Iterable[Dictionary]) -> list[LexiconEntry]:
    """Flatten enabled dictionaries; duplicate terms resolve name > term > english, ties by name order."""
    active = sorted((d for d in dicts if d.enabled), key=lambda d: (_KIND_RANK[d.kind], d.name))
    merged: dict[tuple[str, bool], LexiconEntry] = {}
    for d in active:
        for e in d.entries:
            key = (e.term if e.case_sensitive else e.term.casefold(), e.case_sensitive)
            merged.setdefault(key, e)
    return list(merged.values())
