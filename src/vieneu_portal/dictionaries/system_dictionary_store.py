"""Admin-managed "system" pronunciation dictionary packs (math/chem seed
rules, English fallback list, ...): pack CRUD, JSON import/export, `.txt/.csv`
import via the phase 7 parser, the bundled-seed loader, and the
`SYSTEM_RULES_MAX` cap. Every mutation moderates rule targets and bumps the
owning pack's `updated_at`, which keys phase 9's compiled system-layer cache.

Owns its own `vieneu-dictionary/1` JSON schema independently of
`vieneu_preprocess.dictionary_schema` — the portal never imports
`vieneu_preprocess` (phase 7's own matcher is independent for the same
reason), so seed files round-trip through the parser in this module instead.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, Sequence

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..config import Settings
from ..db.models_dictionaries import SystemDictionary, SystemPronunciationRule
from ..errors import PortalError
from ..moderation.moderation_provider_interface import ContentPolicyViolation, ModerationProvider
from ..text.dictionary_import_export_and_merge import ImportedRule, export_dictionary_txt, parse_dictionary_import
from ..text.engine_text_pipeline import check_moderation_or_raise

FORMAT = "vieneu-dictionary/1"
KINDS = ("english", "term", "name")
MODES = ("phonetic", "en")
SEED_DIR = Path(__file__).resolve().parent.parent / "seed" / "system_dictionaries"


class DictionaryFormatError(ValueError):
    """The JSON text does not match the `vieneu-dictionary/1` schema."""


@dataclass(frozen=True)
class ParsedEntry:
    term: str
    replacement: str
    mode: str
    case_sensitive: bool
    note: str


@dataclass(frozen=True)
class ParsedPack:
    name: str
    kind: str
    enabled: bool
    description: str
    entries: tuple


def parse_dictionary_pack_json(text: str) -> ParsedPack:
    try:
        obj = json.loads(text)
    except json.JSONDecodeError as exc:
        raise DictionaryFormatError(f"invalid JSON: {exc}") from exc
    if not isinstance(obj, dict):
        raise DictionaryFormatError("top level must be an object")
    if obj.get("format") != FORMAT:
        raise DictionaryFormatError(f"format must equal {FORMAT!r}")
    name = obj.get("name")
    if not isinstance(name, str) or not (1 <= len(name) <= 120):
        raise DictionaryFormatError("name must be a string of 1-120 characters")
    kind = obj.get("kind")
    if kind not in KINDS:
        raise DictionaryFormatError(f"kind must be one of {KINDS}")
    enabled = obj.get("enabled", True)
    if not isinstance(enabled, bool):
        raise DictionaryFormatError("enabled must be a boolean")
    description = obj.get("description") or ""
    if not isinstance(description, str):
        raise DictionaryFormatError("description must be a string")
    raw_entries = obj.get("entries", [])
    if not isinstance(raw_entries, list):
        raise DictionaryFormatError("entries must be a list")

    entries: list = []
    seen: dict = {}
    for i, raw in enumerate(raw_entries):
        path = f"entries[{i}]"
        if not isinstance(raw, dict):
            raise DictionaryFormatError(f"{path} must be an object")
        term = raw.get("term")
        if not isinstance(term, str) or not (1 <= len(term) <= 255):
            raise DictionaryFormatError(f"{path}.term must be a string of 1-255 characters")
        mode = raw.get("mode", "phonetic")
        if mode not in MODES:
            raise DictionaryFormatError(f"{path}.mode must be one of {MODES}")
        replacement = raw.get("replacement") or ""
        if not isinstance(replacement, str) or len(replacement) > 255:
            raise DictionaryFormatError(f"{path}.replacement must be a string of at most 255 characters")
        if mode == "phonetic" and not replacement:
            raise DictionaryFormatError(f"{path}.replacement is required for mode 'phonetic'")
        case_sensitive = bool(raw.get("case_sensitive", False))
        note = raw.get("note") or ""
        key = term if case_sensitive else term.lower()
        if key in seen:
            raise DictionaryFormatError(f"{path}.term: duplicate term {term!r}")
        seen[key] = True
        entries.append(ParsedEntry(term, replacement, mode, case_sensitive, str(note)))
    return ParsedPack(name=name, kind=kind, enabled=bool(enabled), description=description, entries=tuple(entries))


def _rule_kind_and_replacement(mode: str, replacement: str) -> tuple:
    if mode == "en" and not replacement:
        return "ENGLISH_FALLBACK", ""
    return "REPLACE", replacement


def _rule_from_entry(dictionary_id: int, entry: ParsedEntry, sort_order: int) -> SystemPronunciationRule:
    rule_kind, replacement = _rule_kind_and_replacement(entry.mode, entry.replacement)
    return SystemPronunciationRule(
        dictionary_id=dictionary_id, source_term=entry.term, phonetic_replacement=replacement,
        match_whole_word=True, case_sensitive=entry.case_sensitive, is_enabled=True,
        sort_order=sort_order, note=entry.note, rule_kind=rule_kind,
    )


def _touch_pack(pack: SystemDictionary) -> None:
    pack.updated_at = datetime.now(timezone.utc)


def _enabled_rule_count(db: Session, *, exclude_dictionary_id: Optional[int] = None) -> int:
    q = (
        select(func.count())
        .select_from(SystemPronunciationRule)
        .join(SystemDictionary, SystemDictionary.id == SystemPronunciationRule.dictionary_id)
        .where(SystemPronunciationRule.is_enabled.is_(True), SystemDictionary.is_enabled.is_(True))
    )
    if exclude_dictionary_id is not None:
        q = q.where(SystemPronunciationRule.dictionary_id != exclude_dictionary_id)
    return db.execute(q).scalar_one()


def _guard_system_rules_cap(
    db: Session, settings: Settings, *, incoming_enabled: int, dictionary_id: Optional[int]
) -> None:
    current = _enabled_rule_count(db, exclude_dictionary_id=dictionary_id)
    if current + incoming_enabled > settings.SYSTEM_RULES_MAX:
        raise PortalError(
            422, "SYSTEM_RULES_LIMIT_EXCEEDED",
            f"would exceed the system rule cap of {settings.SYSTEM_RULES_MAX}",
        )


def _partition_entries_by_moderation(
    entries: Sequence[ParsedEntry], moderation: ModerationProvider, settings: Settings
) -> tuple:
    """Rejects (skips, never aborts the whole import on) an entry whose target
    fails moderation; a provider *outage* (`ModerationUnavailable`) still
    aborts everything, since that is a systemic failure, not a content issue.
    """
    accepted: list = []
    rejected: list = []
    for i, entry in enumerate(entries):
        if entry.replacement:
            try:
                check_moderation_or_raise(moderation, entry.replacement, settings)
            except ContentPolicyViolation as exc:
                rejected.append({"index": i, "term": entry.term, "reason": exc.message})
                continue
        accepted.append(entry)
    return accepted, rejected


# -- pack CRUD ----------------------------------------------------------------

def list_packs(db: Session) -> list:
    return list(db.execute(select(SystemDictionary).order_by(SystemDictionary.sort_order, SystemDictionary.name)).scalars())


def get_pack(db: Session, pack_id: int) -> SystemDictionary:
    pack = db.get(SystemDictionary, pack_id)
    if pack is None:
        raise PortalError(404, "NOT_FOUND", f"system dictionary {pack_id} not found")
    return pack


def get_pack_by_name(db: Session, name: str) -> SystemDictionary:
    pack = db.execute(select(SystemDictionary).where(SystemDictionary.name == name)).scalar_one_or_none()
    if pack is None:
        raise PortalError(404, "NOT_FOUND", f"system dictionary {name!r} not found")
    return pack


def update_pack_metadata(
    db: Session, pack: SystemDictionary, *, name: Optional[str] = None, kind: Optional[str] = None,
    description: Optional[str] = None,
) -> SystemDictionary:
    if name is not None:
        pack.name = name
    if kind is not None:
        if kind not in KINDS:
            raise PortalError(422, "VALIDATION_ERROR", f"kind must be one of {KINDS}")
        pack.kind = kind
    if description is not None:
        pack.description = description
    _touch_pack(pack)
    db.flush()
    return pack


def set_pack_enabled(db: Session, settings: Settings, pack: SystemDictionary, enabled: bool) -> SystemDictionary:
    if enabled and not pack.is_enabled:
        enabled_rules = sum(1 for r in list_rules(db, pack.id) if r.is_enabled)
        _guard_system_rules_cap(db, settings, incoming_enabled=enabled_rules, dictionary_id=pack.id)
    pack.is_enabled = enabled
    _touch_pack(pack)
    db.flush()
    return pack


def delete_pack(db: Session, pack: SystemDictionary) -> None:
    db.delete(pack)
    db.flush()


# -- rules ----------------------------------------------------------------

def list_rules(db: Session, pack_id: int) -> list:
    return list(
        db.execute(
            select(SystemPronunciationRule)
            .where(SystemPronunciationRule.dictionary_id == pack_id)
            .order_by(SystemPronunciationRule.sort_order)
        ).scalars()
    )


def replace_all_rules(
    db: Session, settings: Settings, moderation: ModerationProvider, pack: SystemDictionary,
    entries: Sequence[ParsedEntry],
) -> list:
    accepted, rejected = _partition_entries_by_moderation(entries, moderation, settings)
    _guard_system_rules_cap(db, settings, incoming_enabled=len(accepted), dictionary_id=pack.id)
    for rule in list_rules(db, pack.id):
        db.delete(rule)
    db.flush()
    for i, entry in enumerate(accepted):
        db.add(_rule_from_entry(pack.id, entry, i))
    _touch_pack(pack)
    db.flush()
    return rejected


# -- JSON import/export ----------------------------------------------------------------

def create_pack_from_json(
    db: Session, settings: Settings, moderation: ModerationProvider, *, json_text: str,
) -> tuple:
    parsed = parse_dictionary_pack_json(json_text)
    accepted, rejected = _partition_entries_by_moderation(parsed.entries, moderation, settings)
    _guard_system_rules_cap(db, settings, incoming_enabled=len(accepted), dictionary_id=None)

    pack = SystemDictionary(name=parsed.name, kind=parsed.kind, is_enabled=parsed.enabled, description=parsed.description)
    db.add(pack)
    db.flush()
    for i, entry in enumerate(accepted):
        db.add(_rule_from_entry(pack.id, entry, i))
    db.flush()
    return pack, rejected


def _conflicts_with_accepted(source: str, case_sensitive: bool, accepted: Sequence[ParsedEntry]) -> bool:
    for entry in accepted:
        if not case_sensitive or not entry.case_sensitive:
            if source.lower() == entry.term.lower():
                return True
        elif source == entry.term:
            return True
    return False


def import_json_into_pack(
    db: Session, settings: Settings, moderation: ModerationProvider, *, pack: SystemDictionary,
    json_text: str, mode: str,
) -> list:
    """`mode="merge"`: accepted entries are upserted into `pack`, existing
    rules that do not conflict are kept. `mode="replace"`: `pack`'s metadata
    and every rule are replaced by the imported file.
    """
    if mode not in ("merge", "replace"):
        raise ValueError(f"mode must be 'merge' or 'replace', got {mode!r}")
    parsed = parse_dictionary_pack_json(json_text)
    accepted, rejected = _partition_entries_by_moderation(parsed.entries, moderation, settings)

    existing_rules = list_rules(db, pack.id)
    if mode == "replace":
        pack.name, pack.kind, pack.is_enabled, pack.description = (
            parsed.name, parsed.kind, parsed.enabled, parsed.description,
        )
        kept_rules: list = []
    else:
        kept_rules = [r for r in existing_rules if not _conflicts_with_accepted(r.source_term, r.case_sensitive, accepted)]

    for rule in existing_rules:
        if rule not in kept_rules:
            db.delete(rule)
    db.flush()

    kept_enabled = sum(1 for r in kept_rules if r.is_enabled)
    _guard_system_rules_cap(db, settings, incoming_enabled=kept_enabled + len(accepted), dictionary_id=pack.id)

    for i, entry in enumerate(accepted):
        db.add(_rule_from_entry(pack.id, entry, len(kept_rules) + i))
    _touch_pack(pack)
    db.flush()
    return rejected


def export_pack_json(db: Session, pack: SystemDictionary) -> str:
    rules = list_rules(db, pack.id)
    entries = []
    for r in sorted(rules, key=lambda r: r.source_term):
        mode = "en" if r.rule_kind == "ENGLISH_FALLBACK" else "phonetic"
        entries.append({
            "term": r.source_term, "replacement": r.phonetic_replacement, "mode": mode,
            "case_sensitive": r.case_sensitive, "note": r.note,
        })
    out = {
        "format": FORMAT, "name": pack.name, "kind": pack.kind, "enabled": pack.is_enabled,
        "description": pack.description or "", "entries": entries,
    }
    return json.dumps(out, ensure_ascii=False, indent=2)


def export_pack_txt(db: Session, pack: SystemDictionary) -> str:
    """`source = target` lines (phase 7's import format) for every `REPLACE`
    rule with a non-empty replacement; `ENGLISH_FALLBACK` rules have no
    target to export in this plain-text shape and are skipped — JSON export
    is the only round-trip-complete format for those.
    """
    rules = list_rules(db, pack.id)
    importable = [
        ImportedRule(source=r.source_term, target=r.phonetic_replacement, case_sensitive=r.case_sensitive)
        for r in sorted(rules, key=lambda r: r.source_term)
        if r.rule_kind == "REPLACE" and r.phonetic_replacement
    ]
    return export_dictionary_txt(importable)


# -- `.txt`/`.csv` import (phase 7 parser: `source = target` lines) ----------------

def import_text_rules_into_pack(
    db: Session, settings: Settings, moderation: ModerationProvider, *, pack: SystemDictionary,
    text: str, mode: str,
) -> tuple:
    """Returns `(rejected_by_moderation, line_errors)`. `line_errors` are
    unparseable lines (phase 7's `parse_dictionary_import`); `rejected` are
    parsed rules whose target failed moderation.
    """
    if mode not in ("merge", "replace"):
        raise ValueError(f"mode must be 'merge' or 'replace', got {mode!r}")
    imported, line_errors = parse_dictionary_import(text)

    accepted: list = []
    rejected: list = []
    for rule in imported:
        try:
            check_moderation_or_raise(moderation, rule.target, settings)
        except ContentPolicyViolation as exc:
            rejected.append({"source": rule.source, "reason": exc.message})
            continue
        accepted.append(rule)

    existing_rules = list_rules(db, pack.id)
    if mode == "replace":
        kept_rules: list = []
    else:
        as_entries = [ParsedEntry(term=r.source, replacement="", mode="phonetic", case_sensitive=r.case_sensitive, note="")
                      for r in accepted]
        kept_rules = [r for r in existing_rules if not _conflicts_with_accepted(r.source_term, r.case_sensitive, as_entries)]

    for rule in existing_rules:
        if rule not in kept_rules:
            db.delete(rule)
    db.flush()

    kept_enabled = sum(1 for r in kept_rules if r.is_enabled)
    _guard_system_rules_cap(db, settings, incoming_enabled=kept_enabled + len(accepted), dictionary_id=pack.id)

    for i, rule in enumerate(accepted):
        db.add(SystemPronunciationRule(
            dictionary_id=pack.id, source_term=rule.source, phonetic_replacement=rule.target,
            match_whole_word=rule.whole_word, case_sensitive=rule.case_sensitive, is_enabled=True,
            sort_order=len(kept_rules) + i, note="", rule_kind="REPLACE",
        ))
    _touch_pack(pack)
    db.flush()
    return rejected, tuple(line_errors)


# -- bundled seed ----------------------------------------------------------------

def seed_if_empty(db: Session, settings: Settings, moderation: ModerationProvider) -> list:
    """Loads every bundled pack under `SEED_DIR`. Refuses when any pack
    already exists (seeding after a SQLite migration would create
    name-duplicate packs with no provenance)."""
    if db.execute(select(SystemDictionary.id).limit(1)).first() is not None:
        raise PortalError(409, "SEED_ALREADY_APPLIED", "a system dictionary pack already exists")
    created = []
    for path in sorted(SEED_DIR.glob("*.json")):
        pack, rejected = create_pack_from_json(db, settings, moderation, json_text=path.read_text(encoding="utf-8"))
        if rejected:
            raise PortalError(500, "SEED_REJECTED", f"bundled seed {path.name} failed moderation: {rejected}")
        created.append(pack.name)
    return created
