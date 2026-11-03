"""`GET /api/v1/admin/audit-log` — read-only; no update/delete endpoint
exists for this table by design.
"""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..auth.session_dependencies import AuthContext, require_admin
from ..db.models_admin_audit_log import AdminAuditLog
from ..db.session_factory import get_db

router = APIRouter()


def serialize_audit_row(row: AdminAuditLog) -> dict:
    return {
        "id": row.id, "actor_user_id": str(row.actor_user_id) if row.actor_user_id else None,
        "actor_label": row.actor_label, "action": row.action, "target_type": row.target_type,
        "target_id": row.target_id, "target_label": row.target_label, "before": row.before, "after": row.after,
        "created_at": row.created_at,
    }


@router.get("/admin/audit-log")
def list_audit_log(
    actor: Optional[str] = None,
    action: Optional[str] = None,
    target_type: Optional[str] = None,
    target_id: Optional[str] = None,
    from_: Optional[datetime] = Query(default=None, alias="from"),
    to: Optional[datetime] = None,
    page: int = 1,
    limit: int = 50,
    db: Session = Depends(get_db),
    ctx: AuthContext = Depends(require_admin),
) -> dict:
    limit = min(max(limit, 1), 200)
    page = max(page, 1)
    query = select(AdminAuditLog)
    if actor:
        query = query.where(AdminAuditLog.actor_label.ilike(f"%{actor}%"))
    if action:
        query = query.where(AdminAuditLog.action == action)
    if target_type:
        query = query.where(AdminAuditLog.target_type == target_type)
    if target_id:
        query = query.where(AdminAuditLog.target_id == target_id)
    if from_:
        query = query.where(AdminAuditLog.created_at >= from_)
    if to:
        query = query.where(AdminAuditLog.created_at <= to)

    total = db.execute(select(func.count()).select_from(query.subquery())).scalar_one()
    rows = list(
        db.execute(query.order_by(AdminAuditLog.created_at.desc()).offset((page - 1) * limit).limit(limit)).scalars()
    )
    return {"items": [serialize_audit_row(r) for r in rows], "total_count": total, "page": page, "limit": limit}
