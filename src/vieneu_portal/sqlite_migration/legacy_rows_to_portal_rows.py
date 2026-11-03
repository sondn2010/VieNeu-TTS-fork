"""Pure transforms: legacy SQLite rows -> portal row shapes. No DB access —
`run_sqlite_to_postgres_migration.py` is the only caller that writes.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional

from .sqlite_admin_reader import LegacyApiKey, LegacyDictionary, LegacyUser

_ROLE_MAP = {"admin": "SUPERADMIN", "user": "USER"}


def legacy_source_id_for_user(legacy_id: int) -> str:
    return f"sqlite:users:{legacy_id}"


def legacy_source_id_for_dictionary(legacy_id: int) -> str:
    return f"sqlite:dictionaries:{legacy_id}"


def _epoch_to_datetime(seconds: int) -> datetime:
    return datetime.fromtimestamp(seconds, tz=timezone.utc)


@dataclass(frozen=True)
class TransformedUser:
    legacy_source_id: str
    email: str
    username: str
    password_hash: str
    role: str
    is_active: bool
    created_at: datetime


def transform_user(user: LegacyUser, *, migration_email_domain: str) -> TransformedUser:
    """SQLite users have no email: every migrated user gets
    `<username>@<migration_email_domain>` (the report lists these as
    `needs_email`; an admin fixes the real address later)."""
    return TransformedUser(
        legacy_source_id=legacy_source_id_for_user(user.id),
        email=f"{user.username}@{migration_email_domain}".lower(),
        username=user.username,
        password_hash=user.password_hash,
        role=_ROLE_MAP[user.role],
        is_active=user.active,
        created_at=_epoch_to_datetime(user.created_at),
    )


@dataclass(frozen=True)
class TransformedApiKey:
    name: str
    key_prefix: str
    key_hash: str
    created_at: datetime
    last_used_at: Optional[datetime]
    revoked_at: Optional[datetime]


def transform_api_key(key: LegacyApiKey) -> TransformedApiKey:
    return TransformedApiKey(
        name=key.name,
        key_prefix=key.prefix,
        key_hash=key.key_hash,
        created_at=_epoch_to_datetime(key.created_at),
        last_used_at=_epoch_to_datetime(key.last_used_at) if key.last_used_at else None,
        revoked_at=_epoch_to_datetime(key.revoked_at) if key.revoked_at else None,
    )


@dataclass(frozen=True)
class TransformedRule:
    source_term: str
    phonetic_replacement: str
    case_sensitive: bool
    rule_kind: str   # 'REPLACE' | 'ENGLISH_FALLBACK'
    note: str
    sort_order: int


@dataclass(frozen=True)
class TransformedDictionary:
    legacy_source_id: str
    name: str
    kind: str
    is_enabled: bool
    description: str
    rules: tuple


def _rule_kind_and_replacement(mode: str, replacement: str) -> tuple:
    """`mode="en"` with a non-empty replacement becomes an ordinary `REPLACE`
    rule (same as `mode="phonetic"`): once imported, both read exactly the
    same replacement text, so the original `mode` tag carries no further
    meaning. Only an empty-replacement `en` entry needs its own kind, since
    that is the only case the matcher treats differently (English-fallback
    wrap instead of a fixed replacement)."""
    if mode == "en" and not replacement:
        return "ENGLISH_FALLBACK", ""
    return "REPLACE", replacement


def transform_dictionary(dictionary: LegacyDictionary) -> TransformedDictionary:
    rules = []
    for i, entry in enumerate(dictionary.entries):
        rule_kind, replacement = _rule_kind_and_replacement(entry.mode, entry.replacement)
        rules.append(TransformedRule(
            source_term=entry.term, phonetic_replacement=replacement, case_sensitive=entry.case_sensitive,
            rule_kind=rule_kind, note=entry.note, sort_order=i,
        ))
    return TransformedDictionary(
        legacy_source_id=legacy_source_id_for_dictionary(dictionary.id), name=dictionary.name,
        kind=dictionary.kind, is_enabled=dictionary.enabled, description=dictionary.description,
        rules=tuple(rules),
    )
