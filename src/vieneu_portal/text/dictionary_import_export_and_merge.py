"""Dictionary file import, export and merge — pinned by
`tests/fixtures/text_contract_vectors/dictionary_import_vectors.json`,
mirrored in TypeScript at `portal-web/src/lib/text/dictionary-import-export-and-merge.ts`.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Optional, Sequence

MAX_SOURCE_OR_TARGET_LEN = 255
MAX_RULES = 2000
MAX_IMPORT_BYTES = 1_000_000
MAX_IMPORT_LINES = 5_000

# Priority order, not first-occurring-character order: if '=' appears
# anywhere in the line, split there even if ',' appears earlier —
# "Hà Nội, Việt Nam = Ha Noi" splits at '=', not the comma.
_SEPARATORS = ("=", "→", "\t", ",")
_LINE_SPLIT_RE = re.compile(r"\r?\n")


class ImportTooLargeError(ValueError):
    """The import text exceeds the DoS-prevention size/line caps."""


@dataclass(frozen=True)
class ImportedRule:
    source: str
    target: str
    whole_word: bool = True
    case_sensitive: bool = False
    enabled: bool = True


@dataclass(frozen=True)
class ImportLineError:
    line: int
    message: str


@dataclass(frozen=True)
class MergeResult:
    rules: tuple[ImportedRule, ...]
    error: Optional[str] = None


def validate_rule(source: str, target: str) -> list[str]:
    errors = []
    for label, value in (("source", source), ("target", target)):
        if "\n" in value or "\r" in value or "\t" in value:
            errors.append(f"{label} must not contain a newline or tab")
        if not (1 <= len(value) <= MAX_SOURCE_OR_TARGET_LEN):
            errors.append(f"{label} must be 1-{MAX_SOURCE_OR_TARGET_LEN} characters")
    if "=" in source:
        errors.append("source must not contain '=' (breaks the export round-trip)")
    return errors


def _split_on_separator(line: str) -> Optional[tuple[str, str]]:
    for sep in _SEPARATORS:
        idx = line.find(sep)
        if idx != -1:
            return line[:idx].strip(), line[idx + len(sep) :].strip()
    return None


def parse_dictionary_import(text: str) -> tuple[tuple[ImportedRule, ...], tuple[ImportLineError, ...]]:
    if len(text.encode("utf-8")) > MAX_IMPORT_BYTES:
        raise ImportTooLargeError(f"import text exceeds {MAX_IMPORT_BYTES} bytes")
    if text.startswith("﻿"):
        text = text[1:]
    lines = _LINE_SPLIT_RE.split(text)
    if len(lines) > MAX_IMPORT_LINES:
        raise ImportTooLargeError(f"import text exceeds {MAX_IMPORT_LINES} lines")

    # Duplicate sources within the file: the last line wins, including its
    # position — `order` is rebuilt to put the winning occurrence last.
    order: list[str] = []
    by_key: dict[str, ImportedRule] = {}
    errors: list[ImportLineError] = []

    for line_no, raw_line in enumerate(lines, start=1):
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        split = _split_on_separator(line)
        if split is None:
            errors.append(ImportLineError(line_no, "no separator ('=', '→', tab or ',') found"))
            continue
        source, target = split
        rule_errors = validate_rule(source, target)
        if rule_errors:
            errors.append(ImportLineError(line_no, "; ".join(rule_errors)))
            continue
        key = source.lower()  # imported rules default to case_sensitive=False
        if key in by_key:
            order.remove(key)
        order.append(key)
        by_key[key] = ImportedRule(source=source, target=target)

    return tuple(by_key[k] for k in order), tuple(errors)


def _conflicts(existing: ImportedRule, imported: ImportedRule) -> bool:
    """Equal ignoring case when either rule is case-insensitive, else exact equal."""
    if not existing.case_sensitive or not imported.case_sensitive:
        return existing.source.lower() == imported.source.lower()
    return existing.source == imported.source


def merge_imported_rules(existing: Sequence[ImportedRule], imported: Sequence[ImportedRule]) -> MergeResult:
    """Imported rules first (file order), then existing rules minus any that
    conflict with an imported one. Over `MAX_RULES` after merging is a hard
    error — never silently truncated.
    """
    kept_existing = [e for e in existing if not any(_conflicts(e, i) for i in imported)]
    merged = tuple(imported) + tuple(kept_existing)
    if len(merged) > MAX_RULES:
        return MergeResult(rules=(), error="DICTIONARY_LIMIT_EXCEEDED")
    return MergeResult(rules=merged, error=None)


def export_dictionary_txt(rules: Sequence[ImportedRule]) -> str:
    """`source = target` per line; re-importing this text round-trips
    exactly, since `validate_rule` already forbids '=' in `source`.
    """
    lines = ["# exported"] + [f"{r.source} = {r.target}" for r in rules]
    return "\n".join(lines) + "\n"
