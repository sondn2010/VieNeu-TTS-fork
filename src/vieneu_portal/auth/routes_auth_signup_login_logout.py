from __future__ import annotations

import re
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, Cookie, Depends, Request, Response
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ..config import get_settings
from ..db.models_users_and_sessions import User
from ..db.session_factory import get_db
from ..errors import PortalError
from ..security import postgres_auth_throttle as throttle
from ..security.password_hashing import MAX_PASSWORD_LEN, MIN_PASSWORD_LEN, burn_password_check, hash_password, verify_password
from ..security.session_tokens_and_csrf import CsrfSigner
from ..user.user_profile_serializer import avatar_initials_from_username, quota_today, sanitize_username
from .session_dependencies import (
    ANON_CSRF_COOKIE_NAME,
    AuthContext,
    clear_session_cookie,
    create_session,
    csrf_signer_for,
    delete_session,
    get_client_ip,
    purge_expired_sessions,
    require_csrf,
    resolve_session_dependency,
    set_session_cookie,
)

router = APIRouter()

_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+$")
_MAX_LOGIN_EMAIL_LEN = 320  # RFC 5321; a defensive bound, not a format check
_MAX_LOGIN_PASSWORD_LEN = 1024  # scrypt has no inherent cap; bound input size defensively


class SignupRequest(BaseModel):
    email: str
    password: str
    username: Optional[str] = None


class LoginRequest(BaseModel):
    email: str
    password: str


def _normalize_email(email: str) -> str:
    return email.strip().lower()


def _validate_password_length(password: str) -> None:
    if not (MIN_PASSWORD_LEN <= len(password) <= MAX_PASSWORD_LEN):
        raise PortalError(
            422, "VALIDATION_ERROR", f"password must be {MIN_PASSWORD_LEN}-{MAX_PASSWORD_LEN} characters"
        )


def _validate_signup_email(email: str) -> str:
    normalized = _normalize_email(email)
    if not normalized or len(normalized) > 255 or not _EMAIL_RE.match(normalized):
        raise PortalError(422, "VALIDATION_ERROR", "invalid email")
    settings = get_settings()
    domain = normalized.rsplit("@", 1)[-1]
    if domain == settings.MIGRATION_EMAIL_DOMAIN:
        raise PortalError(
            422, "EMAIL_DOMAIN_RESERVED", "this email domain is reserved for migrated accounts"
        )
    return normalized


def _validate_login_identifier(email: str, password: str) -> str:
    """Login accepts any syntax (migrated `@migrated.invalid` accounts reject
    strict validators) — only a defensive size bound, no format check.
    """
    normalized = _normalize_email(email)
    if not normalized or len(normalized) > _MAX_LOGIN_EMAIL_LEN or len(password) > _MAX_LOGIN_PASSWORD_LEN:
        raise PortalError(422, "VALIDATION_ERROR", "invalid email or password")
    return normalized


@router.get("/auth/csrf")
def get_csrf(
    response: Response,
    ctx: Optional[AuthContext] = Depends(resolve_session_dependency),
    anon_csrf_nonce: Optional[str] = Cookie(default=None, alias=ANON_CSRF_COOKIE_NAME),
) -> dict:
    settings = get_settings()
    signer = csrf_signer_for(settings)
    if ctx is not None:
        return {"csrf_token": signer.token(ctx.session.csrf_nonce)}

    # Reuse an existing valid anonymous nonce instead of always minting a new
    # one: two overlapping GETs (two tabs, a UI retry, React StrictMode) would
    # otherwise each overwrite the cookie, leaving the other's token pointing
    # at a nonce no longer in the cookie — an intermittent CSRF_FAILED.
    nonce = anon_csrf_nonce if CsrfSigner.looks_like_nonce(anon_csrf_nonce) else CsrfSigner.new_nonce()
    response.set_cookie(
        ANON_CSRF_COOKIE_NAME,
        nonce,
        httponly=True,
        samesite="lax",
        secure=settings.COOKIE_SECURE,
        max_age=3600,
        path="/",
    )
    return {"csrf_token": signer.token(nonce)}


@router.post("/auth/signup", status_code=201)
def signup(
    payload: SignupRequest,
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
    ctx: Optional[AuthContext] = Depends(resolve_session_dependency),
    _csrf: None = Depends(require_csrf),
) -> dict:
    settings = get_settings()
    if not settings.SIGNUP_ENABLED:
        raise PortalError(403, "SIGNUP_DISABLED", "signup is currently disabled")

    ip = get_client_ip(request) or "0.0.0.0"
    email = _validate_signup_email(payload.email)
    _validate_password_length(payload.password)

    # Lock in a fixed order (per-IP, then the constant global key) so
    # concurrent signups never deadlock against each other; held for the
    # whole transaction, closing the count-then-insert race on both caps.
    throttle.acquire_lock(db, f"signup:{ip}")
    throttle.acquire_lock(db, "signup:global")

    if throttle.count_events(
        db, kind=throttle.SIGNUP, window_sec=throttle.SIGNUP_WINDOW_SEC, ip=ip
    ) >= settings.SIGNUP_MAX_PER_IP_PER_HOUR:
        raise PortalError(429, "SIGNUP_RATE_LIMITED", "too many signups from this address")
    if throttle.count_events(
        db, kind=throttle.SIGNUP, window_sec=throttle.SIGNUP_WINDOW_SEC
    ) >= settings.SIGNUP_MAX_GLOBAL_PER_HOUR:
        raise PortalError(429, "SIGNUP_RATE_LIMITED", "signup is temporarily at capacity")

    existing = db.execute(select(User.id).where(func.lower(User.email) == email)).first()
    if existing is not None:
        raise PortalError(409, "EMAIL_TAKEN", "an account with this email already exists")

    username = sanitize_username(payload.username or email.split("@", 1)[0])
    now = datetime.now(timezone.utc)
    user = User(
        email=email,
        username=username,
        avatar_initials=avatar_initials_from_username(username),
        password_hash=hash_password(payload.password),
        token_balance=settings.TRIAL_TOKENS,
        token_quota_total=settings.TRIAL_TOKENS,
        daily_char_limit=settings.TRIAL_DAILY_CHARS,
        daily_char_remaining=settings.TRIAL_DAILY_CHARS,
        daily_chars_reset_on=quota_today(settings),
        plan_expires_at=now + timedelta(days=settings.TRIAL_DAYS),
    )
    db.add(user)
    try:
        db.flush()
    except IntegrityError:
        # A concurrent signup for the same email won the race between our
        # existence check and this insert; the advisory lock above only
        # covers the throttle counters, not the email uniqueness check.
        db.rollback()
        raise PortalError(409, "EMAIL_TAKEN", "an account with this email already exists")

    throttle.record_event(db, kind=throttle.SIGNUP, ip=ip)

    if ctx is not None:  # a stale pre-existing session cookie is never reused
        delete_session(db, ctx.session.token_hash)

    token, csrf_token = create_session(db, user, ip=ip, user_agent=request.headers.get("user-agent"))
    db.commit()

    set_session_cookie(response, token, settings)
    return {"csrf_token": csrf_token}


@router.post("/auth/login")
def login(
    payload: LoginRequest,
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
    ctx: Optional[AuthContext] = Depends(resolve_session_dependency),
    _csrf: None = Depends(require_csrf),
) -> dict:
    settings = get_settings()
    ip = get_client_ip(request) or "0.0.0.0"
    email = _validate_login_identifier(payload.email, payload.password)

    throttle.enforce_login_lockout(db, settings, email_key=email, ip=ip)

    user = db.execute(select(User).where(func.lower(User.email) == email)).scalar_one_or_none()
    if user is None or not user.is_active:
        burn_password_check(payload.password)
        throttle.record_event(db, kind=throttle.LOGIN_FAILURE, ip=ip, email_key=email)
        db.commit()
        raise PortalError(401, "INVALID_CREDENTIALS", "invalid email or password")

    if not verify_password(payload.password, user.password_hash):
        throttle.record_event(db, kind=throttle.LOGIN_FAILURE, ip=ip, email_key=email)
        db.commit()
        raise PortalError(401, "INVALID_CREDENTIALS", "invalid email or password")

    throttle.clear_events(db, kind=throttle.LOGIN_FAILURE, email_key=email, ip=ip)
    throttle.purge_expired(db)
    purge_expired_sessions(db)

    if ctx is not None:  # a stale pre-existing session cookie is never reused
        delete_session(db, ctx.session.token_hash)

    user.last_login_at = datetime.now(timezone.utc)
    token, csrf_token = create_session(db, user, ip=ip, user_agent=request.headers.get("user-agent"))
    db.commit()

    set_session_cookie(response, token, settings)
    return {"csrf_token": csrf_token}


@router.post("/auth/logout")
def logout(
    response: Response,
    db: Session = Depends(get_db),
    ctx: Optional[AuthContext] = Depends(resolve_session_dependency),
    _csrf: None = Depends(require_csrf),
) -> dict:
    settings = get_settings()
    if ctx is not None:
        delete_session(db, ctx.session.token_hash)
        db.commit()
    clear_session_cookie(response, settings)
    return {"status": "ok"}
