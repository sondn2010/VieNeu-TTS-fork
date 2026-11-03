"""Login/signup rate limiting backed by `auth_throttle_events`, so limits hold
across uvicorn workers and survive restarts (the old `LoginLimiter` in
`src/vieneu_admin/security.py` was in-process memory and is not moved).
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Optional

from sqlalchemy import delete, func, select, text
from sqlalchemy.orm import Session

from ..config import Settings
from ..db.models_auth_throttle_events import AuthThrottleEvent
from ..errors import PortalError

LOGIN_FAILURE = "LOGIN_FAILURE"
SIGNUP = "SIGNUP"

LOGIN_FAILURE_WINDOW_SEC = 15 * 60
SIGNUP_WINDOW_SEC = 60 * 60
PURGE_OLDER_THAN_SEC = 24 * 60 * 60


def acquire_lock(db: Session, key: str) -> None:
    """Serialize concurrent count-then-insert attempts sharing `key` within
    this transaction (released automatically on commit/rollback). Without
    this, N parallel requests can all pass the same lockout/cap check before
    any of their events commit, turning e.g. `LOGIN_MAX_FAILURES=5` into
    effectively `5 + N`.
    """
    db.execute(text("SELECT pg_advisory_xact_lock(hashtext(:key)::bigint)"), {"key": key})


def record_event(db: Session, *, kind: str, ip: str, email_key: Optional[str] = None) -> None:
    db.add(AuthThrottleEvent(kind=kind, ip=ip, email_key=email_key))
    db.flush()


def clear_events(db: Session, *, kind: str, ip: Optional[str] = None, email_key: Optional[str] = None) -> int:
    stmt = delete(AuthThrottleEvent).where(AuthThrottleEvent.kind == kind)
    if ip is not None:
        stmt = stmt.where(AuthThrottleEvent.ip == ip)
    if email_key is not None:
        stmt = stmt.where(AuthThrottleEvent.email_key == email_key)
    result = db.execute(stmt)
    return result.rowcount


def _filtered(stmt, *, kind: str, window_sec: int, ip: Optional[str], email_key: Optional[str]):
    cutoff = datetime.now(timezone.utc) - timedelta(seconds=window_sec)
    stmt = stmt.where(AuthThrottleEvent.kind == kind, AuthThrottleEvent.created_at >= cutoff)
    if ip is not None:
        stmt = stmt.where(AuthThrottleEvent.ip == ip)
    if email_key is not None:
        stmt = stmt.where(AuthThrottleEvent.email_key == email_key)
    return stmt


def count_events(
    db: Session, *, kind: str, window_sec: int, ip: Optional[str] = None, email_key: Optional[str] = None
) -> int:
    stmt = _filtered(
        select(func.count()).select_from(AuthThrottleEvent),
        kind=kind,
        window_sec=window_sec,
        ip=ip,
        email_key=email_key,
    )
    return db.execute(stmt).scalar_one()


def retry_after_seconds(
    db: Session,
    *,
    kind: str,
    window_sec: int,
    max_count: int = 1,
    ip: Optional[str] = None,
    email_key: Optional[str] = None,
) -> int:
    """Seconds until the count drops back under `max_count` (0 if it isn't
    currently at or over it). Anchored on the (count - max_count + 1)-th
    oldest event, not the single oldest — if the count is already above
    `max_count`, the oldest event leaving the window does not yet unlock it.
    """
    stmt = _filtered(
        select(AuthThrottleEvent.created_at), kind=kind, window_sec=window_sec, ip=ip, email_key=email_key
    )
    stmt = stmt.order_by(AuthThrottleEvent.created_at.asc()).offset(max(max_count - 1, 0)).limit(1)
    anchor = db.execute(stmt).scalar_one_or_none()
    if anchor is None:
        return 0
    if anchor.tzinfo is None:
        anchor = anchor.replace(tzinfo=timezone.utc)
    elapsed = (datetime.now(timezone.utc) - anchor).total_seconds()
    return max(0, int(window_sec - elapsed) + 1)


def purge_expired(db: Session, *, older_than_sec: int = PURGE_OLDER_THAN_SEC) -> int:
    """Reused by the worker loop (phase 10) and opportunistically on login."""
    cutoff = datetime.now(timezone.utc) - timedelta(seconds=older_than_sec)
    result = db.execute(delete(AuthThrottleEvent).where(AuthThrottleEvent.created_at < cutoff))
    return result.rowcount


def enforce_login_lockout(db: Session, settings: Settings, *, email_key: str, ip: str) -> None:
    """Shared by `/auth/login` and `/user/password` (a wrong current password
    there "counts as a login failure" per spec) — raises `429 LOGIN_LOCKED`
    when either the `(email, ip)` or the `ip`-wide failure count is at or
    over its limit.
    """
    acquire_lock(db, f"login:{ip}")

    locked_pair = (
        count_events(db, kind=LOGIN_FAILURE, window_sec=LOGIN_FAILURE_WINDOW_SEC, email_key=email_key, ip=ip)
        >= settings.LOGIN_MAX_FAILURES
    )
    locked_ip = (
        count_events(db, kind=LOGIN_FAILURE, window_sec=LOGIN_FAILURE_WINDOW_SEC, ip=ip)
        >= settings.LOGIN_MAX_FAILURES_PER_IP
    )
    if not (locked_pair or locked_ip):
        return

    retry_after = max(
        retry_after_seconds(
            db,
            kind=LOGIN_FAILURE,
            window_sec=LOGIN_FAILURE_WINDOW_SEC,
            max_count=settings.LOGIN_MAX_FAILURES,
            email_key=email_key,
            ip=ip,
        )
        if locked_pair
        else 0,
        retry_after_seconds(
            db,
            kind=LOGIN_FAILURE,
            window_sec=LOGIN_FAILURE_WINDOW_SEC,
            max_count=settings.LOGIN_MAX_FAILURES_PER_IP,
            ip=ip,
        )
        if locked_ip
        else 0,
    )
    raise PortalError(429, "LOGIN_LOCKED", "too many failed login attempts", retry_after=retry_after)
