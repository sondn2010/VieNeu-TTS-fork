"""Profile serialization and username/avatar helpers shared by the profile
route, signup, and later quota responses (phase 10 reuses the `client_config`
subset).
"""
from __future__ import annotations

import re
from datetime import date, datetime
from typing import Any
from zoneinfo import ZoneInfo

from ..config import Settings
from ..db.models_users_and_sessions import User
from ..errors import PortalError

_CONTROL_CHARS_RE = re.compile(r"[\x00-\x1f\x7f]")
MAX_USERNAME_LEN = 100
MAX_AVATAR_INITIALS_LEN = 4  # users.avatar_initials is VARCHAR(4)


def sanitize_username(raw: str) -> str:
    cleaned = _CONTROL_CHARS_RE.sub("", raw).strip()
    if not cleaned:
        raise PortalError(422, "VALIDATION_ERROR", "username must not be empty")
    return cleaned[:MAX_USERNAME_LEN]


def avatar_initials_from_username(username: str) -> str:
    parts = [p for p in username.split() if p]
    if not parts:
        initials = "US"
    elif len(parts) == 1:
        initials = (parts[0][:2] or "US").upper()
    else:
        initials = (parts[0][:1] + parts[1][:1]).upper()
    # .upper() can expand some characters (e.g. 'ﬃ'.upper() == 'FFI'), which
    # could otherwise overflow the VARCHAR(4) column and 500 the request.
    return initials[:MAX_AVATAR_INITIALS_LEN]


def quota_today(settings: Settings) -> date:
    """"Today" in `QUOTA_TIMEZONE` — the single source of truth for the daily
    reset date, shared with phase 10's metering so the two never disagree.
    """
    return datetime.now(ZoneInfo(settings.QUOTA_TIMEZONE)).date()


def _effective_daily_char_remaining(user: User, settings: Settings) -> int:
    """Lazy reset view: once "today" (in `QUOTA_TIMEZONE`) no longer matches
    the stored reset date, report a full daily allowance without writing it —
    the actual reset happens at the point of consumption (phase 10). `!=`
    (not `<`) matches phase 10's planned `IS DISTINCT FROM` reset condition,
    so a stored date that is somehow ahead of "today" doesn't disagree.
    """
    if user.daily_chars_reset_on != quota_today(settings):
        return user.daily_char_limit
    return user.daily_char_remaining


def serialize_profile(user: User, settings: Settings) -> dict[str, Any]:
    has_accepted = bool(user.has_accepted_tts_terms) and user.terms_version == settings.TERMS_VERSION
    return {
        "id": str(user.id),
        "email": user.email,
        "username": user.username,
        "avatar_initials": user.avatar_initials,
        "plan_tier": user.plan_tier,
        "token_balance": user.token_balance,
        "token_quota_total": user.token_quota_total,
        "daily_char_limit": user.daily_char_limit,
        "daily_char_remaining": _effective_daily_char_remaining(user, settings),
        "plan_expires_at": user.plan_expires_at,
        "has_accepted_tts_terms": has_accepted,
        "terms_version": user.terms_version,
        "onboarding_completed_steps": user.onboarding_completed_steps,
        "onboarding_hidden": user.onboarding_hidden,
        "ui_theme": user.ui_theme,
        "ui_language": user.ui_language,
        "role": user.role,
        "client_config": {
            "tokens_per_char_milli": settings.TOKENS_PER_CHAR_MILLI,
            "tts_max_chars": settings.TTS_MAX_CHARS,
            "tts_sync_char_cap": settings.TTS_SYNC_CHAR_CAP,
            "terms_version": settings.TERMS_VERSION,
        },
    }
