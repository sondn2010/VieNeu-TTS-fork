"""Per-user synthesis lease (`users.synthesis_lock_until`): with one request
in flight the read-only quota precheck is exact, so parallel streams or
queued jobs from the same user cannot overspend, and one account cannot
occupy every engine slot. A crash simply lets the lease expire — there is
no separate release-on-timeout job.
"""
from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.orm import Session

from ..errors import PortalError

_ACQUIRE = text(
    "UPDATE users SET synthesis_lock_until = now() + make_interval(secs => :lease) "
    "WHERE id = :uid AND (synthesis_lock_until IS NULL OR synthesis_lock_until < now()) "
    "RETURNING id"
)
_RENEW = text("UPDATE users SET synthesis_lock_until = now() + make_interval(secs => :lease) WHERE id = :uid")
_RELEASE = text("UPDATE users SET synthesis_lock_until = NULL WHERE id = :uid")


def acquire_lease(db: Session, user_id, lease_sec: int) -> None:
    row = db.execute(_ACQUIRE, {"uid": user_id, "lease": lease_sec}).first()
    if row is None:
        raise PortalError(409, "SYNTHESIS_IN_PROGRESS", "a synthesis is already in progress for this account")


def renew_lease(db: Session, user_id, lease_sec: int) -> None:
    db.execute(_RENEW, {"uid": user_id, "lease": lease_sec})


def release_lease(db: Session, user_id) -> None:
    db.execute(_RELEASE, {"uid": user_id})
