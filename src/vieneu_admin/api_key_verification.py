"""Bearer API-key verification for the speech API (no web framework dependency)."""
from __future__ import annotations

from typing import TYPE_CHECKING, Optional

from .models import KeyOwner

if TYPE_CHECKING:  # pragma: no cover
    from .store import AdminStore


def verify_api_key(store: "AdminStore", header: Optional[str]) -> Optional[KeyOwner]:
    """Return the key owner for an ``Authorization`` header value, else None.

    Accepts ``Bearer vn_...`` (scheme case-insensitive). Revoked keys and keys of
    disabled users are rejected. ``last_used_at`` is refreshed at most once a minute.
    """
    if not header or not isinstance(header, str):
        return None
    scheme, _, token = header.strip().partition(" ")
    if scheme.lower() != "bearer":
        return None
    return store.lookup(token.strip())
