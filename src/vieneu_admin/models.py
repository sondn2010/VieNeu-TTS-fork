"""Plain data records returned by AdminStore, plus the store's error types.

Timestamps are integer Unix epoch seconds (UTC); templates format them for display.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

ROLES = ("admin", "user")


class StoreError(ValueError):
    """A user-facing validation or business-rule failure (safe to show in the UI)."""


class NotFoundError(StoreError):
    """The referenced row does not exist."""


class ForbiddenError(StoreError):
    """The actor may not perform this operation on the referenced row."""


@dataclass(frozen=True)
class User:
    id: int
    username: str
    role: str
    active: bool
    created_at: int

    @property
    def is_admin(self) -> bool:
        return self.role == "admin"


@dataclass(frozen=True)
class ApiKey:
    id: int
    user_id: int
    username: str
    name: str
    prefix: str  # first 8 characters of the plaintext key, for display only
    created_at: int
    last_used_at: Optional[int]
    revoked_at: Optional[int]

    @property
    def active(self) -> bool:
        return self.revoked_at is None


@dataclass(frozen=True)
class KeyOwner:
    """Result of a successful API-key verification."""

    user_id: int
    username: str
    role: str
    key_id: int
    key_name: str


@dataclass(frozen=True)
class Session:
    token_hash: str
    user: User
    csrf: str  # per-session CSRF nonce, rotated on every login
    expires_at: int


@dataclass(frozen=True)
class DictionaryInfo:
    id: int
    name: str
    kind: str
    enabled: bool
    description: str
    updated_at: int
    entry_count: int


@dataclass(frozen=True)
class EntryRow:
    id: int
    dictionary_id: int
    term: str
    replacement: str
    mode: str
    case_sensitive: bool
    note: str
