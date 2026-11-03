"""Deletes a user account in two transactions (red-team 2026-11-02: racing
an in-flight finalize). First, deactivate and revoke sessions — this makes
`charge_or_none`'s `WHERE is_active` clause fail any finalize attempt still
in flight for this user, so it can never charge after this point. Only then
delete the row (FK cascades recordings/rules/keys/sessions) and, after that
transaction commits, best-effort sweep its objects by prefix (not a key
snapshot, so a late-arriving upload from the dying finalize is caught too).
"""
from __future__ import annotations

from typing import Optional

from sqlalchemy.orm import Session

from ..auth.session_dependencies import delete_all_sessions_for_user
from ..db.models_users_and_sessions import User
from ..errors import PortalError
from ..storage.object_storage_interface import ObjectStorage
from .admin_audit_log_writer import write_admin_audit
from .role_change_guards import guard_not_last_active_superadmin, guard_not_self


def delete_user(
    db: Session, *, actor: User, target: User, confirm_email: str, storage: ObjectStorage,
    ip: Optional[str] = None,
) -> None:
    guard_not_self(actor, target, "delete")
    guard_not_last_active_superadmin(db, target)
    if confirm_email.strip().lower() != target.email.lower():
        raise PortalError(422, "VALIDATION_ERROR", "confirm_email does not match this account's email")

    target.is_active = False
    delete_all_sessions_for_user(db, target.id)
    db.commit()

    target_id = target.id
    target_email = target.email
    db.delete(target)
    write_admin_audit(
        db, actor_user_id=actor.id, actor_label=f"user:{actor.email}", action="user.delete",
        target_type="user", target_id=str(target_id), target_label=target_email,
        before=None, after=None, ip=ip,
    )
    db.commit()

    try:
        storage.delete_prefix(f"recordings/{target_id}/")
    except Exception:   # noqa: BLE001 - best-effort cleanup after the row is already gone
        pass
