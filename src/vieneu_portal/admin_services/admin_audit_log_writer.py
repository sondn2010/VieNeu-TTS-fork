"""Writes `admin_audit_log` rows. Every admin mutation (this CLI, phase 13's
API) and every admin listing of another user's recordings writes exactly one
row, in the same transaction as the mutation itself — call this before the
caller's own `db.commit()`, never after.
"""
from __future__ import annotations

from typing import Any, Optional
from uuid import UUID

from sqlalchemy.orm import Session

from ..db.models_admin_audit_log import AdminAuditLog


def write_admin_audit(
    db: Session,
    *,
    actor_user_id: Optional[UUID],
    actor_label: str,
    action: str,
    target_type: str,
    target_id: str,
    target_label: Optional[str] = None,
    before: Optional[dict] = None,
    after: Optional[dict] = None,
    ip: Optional[str] = None,
) -> AdminAuditLog:
    row = AdminAuditLog(
        actor_user_id=actor_user_id,
        actor_label=actor_label,
        action=action,
        target_type=target_type,
        target_id=target_id,
        target_label=target_label,
        before=before,
        after=after,
        ip=ip,
    )
    db.add(row)
    db.flush()
    return row


def cli_actor_label() -> str:
    import getpass

    try:
        return f"cli:{getpass.getuser()}"
    except Exception:   # noqa: BLE001 - getpass can fail in odd environments (no tty/passwd entry)
        return "cli:unknown"
