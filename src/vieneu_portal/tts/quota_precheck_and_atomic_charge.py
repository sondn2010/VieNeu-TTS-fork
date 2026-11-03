"""Quota precheck (read-only) and the single atomic charge statement. This
module — plus the audited admin token-adjustment module of phase 13 — is the
only code allowed to write `token_balance`/`daily_char_remaining`.
"""
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import text
from sqlalchemy.orm import Session

from ..config import Settings
from ..db.models_users_and_sessions import User
from ..errors import PortalError
from ..user.user_profile_serializer import quota_today

_CHARGE = text(
    "UPDATE users SET token_balance = token_balance - :t, "
    "daily_char_remaining = (CASE WHEN daily_chars_reset_on IS DISTINCT FROM :today THEN daily_char_limit "
    "ELSE daily_char_remaining END) - :c, "
    "daily_chars_reset_on = :today, updated_at = now() "
    "WHERE id = :uid AND is_active AND token_balance >= :t "
    "AND (CASE WHEN daily_chars_reset_on IS DISTINCT FROM :today THEN daily_char_limit ELSE daily_char_remaining END) >= :c "
    "AND (plan_expires_at IS NULL OR plan_expires_at > now()) "
    "RETURNING token_balance, token_quota_total, daily_char_remaining"
)


def precheck_quota(user: User, settings: Settings, *, chars: int, tokens: int) -> None:
    """Read-only precheck; the per-user synthesis lease (acquired right
    after this) makes it exact — no parallel request from the same user can
    outrun it. The real, authoritative gate is still `charge_or_none`'s
    conditional `UPDATE`.
    """
    if user.plan_expires_at is not None and user.plan_expires_at <= datetime.now(timezone.utc):
        raise PortalError(402, "PLAN_EXPIRED", "the account's plan has expired")
    if user.token_balance < tokens:
        raise PortalError(402, "INSUFFICIENT_TOKENS", "not enough tokens for this request")
    today = quota_today(settings)
    remaining = user.daily_char_limit if user.daily_chars_reset_on != today else user.daily_char_remaining
    if remaining < chars:
        raise PortalError(402, "DAILY_CHAR_LIMIT_REACHED", "daily character limit reached")


def charge_or_none(db: Session, user_id, settings: Settings, *, chars: int, tokens: int):
    """Charges exactly once if (and only if) the user is still active, has
    enough tokens/chars and an unexpired plan — all in the `WHERE` clause of
    one round trip, so a failure never partially applies. Returns the
    `(token_balance, token_quota_total, daily_char_remaining)` row, or
    `None` when the conditional `UPDATE` matched no row (the normal-but-rare
    edge case once the per-user lease makes the precheck exact: an admin
    adjustment or expiry landed between precheck and charge).
    """
    today = quota_today(settings)
    return db.execute(_CHARGE, {"t": tokens, "c": chars, "today": today, "uid": user_id}).first()
