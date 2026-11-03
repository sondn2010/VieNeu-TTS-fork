"""Admin token-balance and plan adjustments: the only other writer of
`token_balance`/`daily_char_remaining` besides phase 10's metering charge
statement — both use the same atomic conditional-`UPDATE` style, so a
concurrent generate racing an admin adjustment can never leave a negative
balance (`test_admin_api_tokens_and_plan.py` proves this under concurrency).
"""
from __future__ import annotations

from datetime import date, datetime, timezone
from typing import Optional

from sqlalchemy import text
from sqlalchemy.orm import Session

from ..db.models_users_and_sessions import User
from ..errors import PortalError
from .admin_audit_log_writer import write_admin_audit

_ADJUST_TOKENS = text(
    "UPDATE users SET token_balance = token_balance + :delta, updated_at = now() "
    "WHERE id = :uid AND token_balance + :delta >= 0 "
    "RETURNING token_balance"
)


def adjust_tokens(
    db: Session, *, actor: User, target: User, delta: int, reason: str, ip: Optional[str] = None,
) -> int:
    if not reason.strip():
        raise PortalError(422, "VALIDATION_ERROR", "reason is required")
    row = db.execute(_ADJUST_TOKENS, {"delta": delta, "uid": target.id}).first()
    if row is None:
        raise PortalError(409, "INSUFFICIENT_TOKENS", "this adjustment would make the balance negative")
    new_balance = row[0]
    write_admin_audit(
        db, actor_user_id=actor.id, actor_label=f"user:{actor.email}", action="user.tokens_adjust",
        target_type="user", target_id=str(target.id), target_label=target.email,
        before=None, after={"delta": delta, "reason": reason, "resulting_balance": new_balance}, ip=ip,
    )
    return new_balance


def _isoformat_or_none(value: Optional[datetime]) -> Optional[str]:
    return value.isoformat() if value is not None else None


def update_plan(
    db: Session, *, actor: User, target: User, plan_tier: Optional[str] = None,
    token_quota_total: Optional[int] = None, daily_char_limit: Optional[int] = None,
    plan_expires_at: Optional[datetime] = None, reset_daily_remaining: bool = False,
    daily_chars_reset_on_today: Optional[date] = None, ip: Optional[str] = None,
) -> None:
    before = {
        "plan_tier": target.plan_tier, "token_quota_total": target.token_quota_total,
        "daily_char_limit": target.daily_char_limit, "plan_expires_at": _isoformat_or_none(target.plan_expires_at),
        "daily_char_remaining": target.daily_char_remaining,
    }
    if plan_tier is not None:
        target.plan_tier = plan_tier
    if token_quota_total is not None:
        target.token_quota_total = token_quota_total
    if daily_char_limit is not None:
        target.daily_char_limit = daily_char_limit
    if plan_expires_at is not None:
        target.plan_expires_at = plan_expires_at
    if reset_daily_remaining:
        # Admin-only reset path, explicitly allowed alongside the metering
        # charge statement (see the grep-guard test's allow-list) — never
        # touches `synthesis_lock_until`.
        target.daily_char_remaining = target.daily_char_limit
        if daily_chars_reset_on_today is not None:
            target.daily_chars_reset_on = daily_chars_reset_on_today
    target.updated_at = datetime.now(timezone.utc)
    after = {
        "plan_tier": target.plan_tier, "token_quota_total": target.token_quota_total,
        "daily_char_limit": target.daily_char_limit, "plan_expires_at": _isoformat_or_none(target.plan_expires_at),
        "daily_char_remaining": target.daily_char_remaining,
    }
    write_admin_audit(
        db, actor_user_id=actor.id, actor_label=f"user:{actor.email}", action="user.plan_update",
        target_type="user", target_id=str(target.id), target_label=target.email,
        before=before, after=after, ip=ip,
    )
