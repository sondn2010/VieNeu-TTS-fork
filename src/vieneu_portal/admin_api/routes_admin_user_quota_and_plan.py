"""`/api/v1/admin/users/{id}/tokens` and `.../plan`."""
from __future__ import annotations

from datetime import datetime
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..admin_services.token_and_plan_adjustment_service import adjust_tokens, update_plan
from ..auth.session_dependencies import AuthContext, get_client_ip, require_admin, require_csrf
from ..config import get_settings
from ..db.models_voices_and_recordings import TTSRecording
from ..db.session_factory import get_db
from ..user.user_profile_serializer import quota_today
from .admin_shared_helpers import get_target_user_or_404, require_actor_can_manage_target
from .routes_admin_users import serialize_admin_user_row

router = APIRouter()


class AdjustTokensRequest(BaseModel):
    delta: int
    reason: str


@router.post("/admin/users/{user_id}/tokens")
def adjust_tokens_route(
    user_id: UUID, payload: AdjustTokensRequest, request: Request,
    db: Session = Depends(get_db), ctx: AuthContext = Depends(require_admin), _csrf: None = Depends(require_csrf),
) -> dict:
    target = get_target_user_or_404(db, user_id)
    require_actor_can_manage_target(ctx.user, target)
    new_balance = adjust_tokens(
        db, actor=ctx.user, target=target, delta=payload.delta, reason=payload.reason, ip=get_client_ip(request)
    )
    db.commit()
    return {"token_balance": new_balance}


class UpdatePlanRequest(BaseModel):
    plan_tier: Optional[str] = None
    token_quota_total: Optional[int] = None
    daily_char_limit: Optional[int] = None
    plan_expires_at: Optional[datetime] = None
    reset_daily_remaining: Optional[bool] = False


@router.patch("/admin/users/{user_id}/plan")
def update_plan_route(
    user_id: UUID, payload: UpdatePlanRequest, request: Request,
    db: Session = Depends(get_db), ctx: AuthContext = Depends(require_admin), _csrf: None = Depends(require_csrf),
) -> dict:
    target = get_target_user_or_404(db, user_id)
    require_actor_can_manage_target(ctx.user, target)
    settings = get_settings()
    update_plan(
        db, actor=ctx.user, target=target, plan_tier=payload.plan_tier,
        token_quota_total=payload.token_quota_total, daily_char_limit=payload.daily_char_limit,
        plan_expires_at=payload.plan_expires_at, reset_daily_remaining=bool(payload.reset_daily_remaining),
        daily_chars_reset_on_today=quota_today(settings) if payload.reset_daily_remaining else None,
        ip=get_client_ip(request),
    )
    db.commit()
    count = db.execute(select(func.count()).where(TTSRecording.user_id == target.id)).scalar_one()
    return {"user": serialize_admin_user_row(target, count)}
