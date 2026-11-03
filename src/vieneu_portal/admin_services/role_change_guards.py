"""Guards shared by every service that can demote, disable or self-modify a
privileged account: never remove the last active superadmin, never let an
actor change their own role or disable their own account.
"""
from __future__ import annotations

from typing import Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..db.models_users_and_sessions import User
from ..errors import PortalError


def lock_active_superadmins(db: Session) -> list:
    """Row-locks (`FOR UPDATE`) every active SUPERADMIN for the rest of this
    transaction, so two concurrent demotions/disables that would each leave
    at least one other active superadmin cannot both commit and leave zero —
    the second call blocks here until the first transaction ends.
    """
    return list(
        db.execute(
            select(User).where(User.role == "SUPERADMIN", User.is_active.is_(True)).with_for_update()
        ).scalars()
    )


def guard_not_last_active_superadmin(db: Session, target: User) -> None:
    """Call before demoting `target` away from SUPERADMIN or deactivating it.
    Raises `409 LAST_SUPERADMIN` when `target` is the only active superadmin.
    """
    locked = lock_active_superadmins(db)
    if target.role == "SUPERADMIN" and target.is_active and len(locked) <= 1:
        raise PortalError(409, "LAST_SUPERADMIN", "cannot remove the last active superadmin")


def guard_not_self(actor: Optional[User], target: User, action: str) -> None:
    """`actor is None` means the CLI, which never targets itself by construction."""
    if actor is not None and actor.id == target.id:
        raise PortalError(409, "SELF_MODIFICATION", f"cannot {action} your own account")
