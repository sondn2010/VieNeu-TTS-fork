"""Transactional SQLite -> Postgres migration runner. The caller is
responsible for the SQLite-side online backup (`sqlite_admin_reader` only
ever opens the source read-only) and for a pre-migration `pg_dump` of the
target (the CLI command does both before calling this). Everything here runs
inside one transaction: insert by provenance, verify, then commit on
`apply` or always roll back on `dry-run` — a verification failure rolls back
even in `apply` mode, exactly as a conflict does.
"""
from __future__ import annotations

from pathlib import Path
from typing import Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..config import Settings
from ..db.models_developer_and_billing import DeveloperApiKey
from ..db.models_dictionaries import SystemDictionary, SystemPronunciationRule
from ..db.models_users_and_sessions import User
from .legacy_rows_to_portal_rows import transform_api_key, transform_dictionary, transform_user
from .migration_verification_report import Conflict, MigrationReport
from .sqlite_admin_reader import LegacySnapshot, read_legacy_admin_database

_MAX_LEN = {
    "users.email": 255, "users.username": 100,
    "system_dictionaries.name": 120,
    "system_pronunciation_rules.source_term": 255, "system_pronunciation_rules.phonetic_replacement": 255,
    "developer_api_keys.name": 150, "developer_api_keys.key_prefix": 24,
}


class VarcharOverflowError(RuntimeError):
    pass


def _check_len(value: str, field: str, *, legacy_row_id) -> None:
    limit = _MAX_LEN[field]
    if value is not None and len(value) > limit:
        raise VarcharOverflowError(
            f"{field} overflow at legacy row id={legacy_row_id}: {len(value)} chars > {limit}"
        )


def _find_user_conflict(db: Session, email: str, legacy_source_id: str) -> Optional[User]:
    """A pre-existing row with this natural key (email) but a *different*
    provenance (or none at all) is a conflict; the same provenance means this
    row already IS the migrated copy (idempotent re-apply, not a conflict)."""
    existing = db.execute(select(User).where(User.email == email)).scalar_one_or_none()
    if existing is None or existing.legacy_source_id == legacy_source_id:
        return None
    return existing


def _find_dictionary_conflict(db: Session, name: str, legacy_source_id: str) -> Optional[SystemDictionary]:
    existing = db.execute(select(SystemDictionary).where(SystemDictionary.name == name)).scalar_one_or_none()
    if existing is None or existing.legacy_source_id == legacy_source_id:
        return None
    return existing


def run_migration(
    db: Session, settings: Settings, *, sqlite_path: Path, apply: bool, allow_existing: bool = False,
) -> MigrationReport:
    report = MigrationReport(sqlite_path=str(sqlite_path), mode="apply" if apply else "dry-run")
    snapshot = read_legacy_admin_database(sqlite_path)
    report.sessions_counted_not_migrated = snapshot.session_count

    if not allow_existing:
        has_unprovenanced_user = db.execute(select(User.id).where(User.legacy_source_id.is_(None)).limit(1)).first()
        has_unprovenanced_pack = db.execute(
            select(SystemDictionary.id).where(SystemDictionary.legacy_source_id.is_(None)).limit(1)
        ).first()
        if has_unprovenanced_user or has_unprovenanced_pack:
            raise RuntimeError(
                "the target already has users or system dictionaries without migration provenance; pass "
                "--allow-existing if this is expected (natural-key conflicts still abort the apply)"
            )

    user_id_by_legacy_username: dict = {}
    for legacy_user in snapshot.users:
        report.users_total += 1
        transformed = transform_user(legacy_user, migration_email_domain=settings.MIGRATION_EMAIL_DOMAIN)
        _check_len(transformed.email, "users.email", legacy_row_id=legacy_user.id)
        _check_len(transformed.username, "users.username", legacy_row_id=legacy_user.id)
        report.needs_email.append({"username": legacy_user.username, "email": transformed.email})

        conflict = _find_user_conflict(db, transformed.email, transformed.legacy_source_id)
        if conflict is not None:
            report.conflicts.append(Conflict(
                kind="user_email", natural_key=transformed.email, legacy_source_id=transformed.legacy_source_id,
                existing_row_description=f"user id={conflict.id} legacy_source_id={conflict.legacy_source_id!r}",
            ))
            continue

        existing = db.execute(select(User).where(User.legacy_source_id == transformed.legacy_source_id)).scalar_one_or_none()
        if existing is not None:
            report.users_skipped_existing += 1
            user_id_by_legacy_username[legacy_user.username] = existing.id
            continue

        row = User(
            email=transformed.email, username=transformed.username, password_hash=transformed.password_hash,
            role=transformed.role, is_active=transformed.is_active, created_at=transformed.created_at,
            legacy_source_id=transformed.legacy_source_id, has_accepted_tts_terms=False,
            token_balance=settings.TRIAL_TOKENS, token_quota_total=settings.TRIAL_TOKENS,
            daily_char_limit=settings.TRIAL_DAILY_CHARS, daily_char_remaining=settings.TRIAL_DAILY_CHARS,
        )
        db.add(row)
        db.flush()
        user_id_by_legacy_username[legacy_user.username] = row.id
        report.users_inserted += 1

    users_by_id = {u.id: u for u in snapshot.users}
    for legacy_key in snapshot.api_keys:
        report.api_keys_total += 1
        owner = users_by_id.get(legacy_key.user_id)
        user_id = user_id_by_legacy_username.get(owner.username) if owner is not None else None
        if user_id is None:
            continue   # the owning user conflicted (or the row is orphaned); its keys cannot migrate either

        existing_key = db.execute(
            select(DeveloperApiKey).where(DeveloperApiKey.key_hash == legacy_key.key_hash)
        ).scalar_one_or_none()
        if existing_key is not None:
            report.api_keys_skipped_existing += 1
            continue

        transformed_key = transform_api_key(legacy_key)
        _check_len(transformed_key.name, "developer_api_keys.name", legacy_row_id=legacy_key.id)
        _check_len(transformed_key.key_prefix, "developer_api_keys.key_prefix", legacy_row_id=legacy_key.id)
        db.add(DeveloperApiKey(
            user_id=user_id, name=transformed_key.name, environment="LIVE",
            key_prefix=transformed_key.key_prefix, key_hash=transformed_key.key_hash,
            last_used_at=transformed_key.last_used_at, revoked_at=transformed_key.revoked_at,
            created_at=transformed_key.created_at,
        ))
        report.api_keys_inserted += 1

    for legacy_dict in snapshot.dictionaries:
        report.dictionaries_total += 1
        transformed_dict = transform_dictionary(legacy_dict)
        _check_len(transformed_dict.name, "system_dictionaries.name", legacy_row_id=legacy_dict.id)

        conflict = _find_dictionary_conflict(db, transformed_dict.name, transformed_dict.legacy_source_id)
        if conflict is not None:
            report.conflicts.append(Conflict(
                kind="dictionary_name", natural_key=transformed_dict.name,
                legacy_source_id=transformed_dict.legacy_source_id,
                existing_row_description=f"pack id={conflict.id} legacy_source_id={conflict.legacy_source_id!r}",
            ))
            continue

        existing_pack = db.execute(
            select(SystemDictionary).where(SystemDictionary.legacy_source_id == transformed_dict.legacy_source_id)
        ).scalar_one_or_none()
        report.rules_total += len(transformed_dict.rules)
        if existing_pack is not None:
            report.dictionaries_skipped_existing += 1
            continue

        pack = SystemDictionary(
            name=transformed_dict.name, kind=transformed_dict.kind, is_enabled=transformed_dict.is_enabled,
            description=transformed_dict.description, legacy_source_id=transformed_dict.legacy_source_id,
        )
        db.add(pack)
        db.flush()
        for rule in transformed_dict.rules:
            _check_len(rule.source_term, "system_pronunciation_rules.source_term", legacy_row_id=legacy_dict.id)
            _check_len(rule.phonetic_replacement, "system_pronunciation_rules.phonetic_replacement", legacy_row_id=legacy_dict.id)
            db.add(SystemPronunciationRule(
                dictionary_id=pack.id, source_term=rule.source_term, phonetic_replacement=rule.phonetic_replacement,
                match_whole_word=True, case_sensitive=rule.case_sensitive, is_enabled=True,
                sort_order=rule.sort_order, note=rule.note, rule_kind=rule.rule_kind,
            ))
        report.rules_inserted += len(transformed_dict.rules)
        report.dictionaries_inserted += 1

    if report.conflicts:
        db.rollback()
        return report

    db.flush()
    report.lost_rows = _verify(db, snapshot)

    if report.lost_rows or not apply:
        db.rollback()
    else:
        db.commit()
    return report


def _verify(db: Session, snapshot: LegacySnapshot) -> int:
    """Set-equality checks, inside this still-open transaction: every source
    password hash and key hash must be present on the target; every
    dictionary's entries must round-trip to the same normalized (term,
    replacement, case_sensitive, note, is_fallback) tuple. `is_fallback`
    replaces the raw `mode` string on both sides: a `mode="en"` entry with a
    *non-empty* replacement is, by design (`legacy_rows_to_portal_rows`),
    indistinguishable after import from a `mode="phonetic"` entry — both
    become a `REPLACE` rule with the same replacement text, which is the
    only thing ever actually spoken, so the comparison does not reinstate a
    `mode` distinction the system no longer carries.
    """
    lost = 0

    source_hashes = {u.password_hash for u in snapshot.users}
    target_hashes = {row.password_hash for row in db.execute(select(User).where(User.legacy_source_id.isnot(None))).scalars()}
    lost += len(source_hashes - target_hashes)

    source_key_hashes = {k.key_hash for k in snapshot.api_keys}
    target_key_hashes = {row.key_hash for row in db.execute(select(DeveloperApiKey)).scalars()}
    lost += len(source_key_hashes - target_key_hashes)

    for legacy_dict in snapshot.dictionaries:
        from .legacy_rows_to_portal_rows import legacy_source_id_for_dictionary

        pack = db.execute(
            select(SystemDictionary).where(
                SystemDictionary.legacy_source_id == legacy_source_id_for_dictionary(legacy_dict.id)
            )
        ).scalar_one_or_none()
        if pack is None:
            lost += len(legacy_dict.entries)
            continue
        source_tuples = {
            (e.term, e.replacement, e.case_sensitive, e.note, e.mode == "en" and not e.replacement)
            for e in legacy_dict.entries
        }
        target_tuples = {
            (r.source_term, r.phonetic_replacement, r.case_sensitive, r.note, r.rule_kind == "ENGLISH_FALLBACK")
            for r in db.execute(select(SystemPronunciationRule).where(SystemPronunciationRule.dictionary_id == pack.id)).scalars()
        }
        lost += len(source_tuples - target_tuples)

    return lost
