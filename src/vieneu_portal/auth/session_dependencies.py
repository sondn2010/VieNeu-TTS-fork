"""Session CRUD, CSRF verification and the `require_user`/`require_admin`/
`require_superadmin` FastAPI dependencies. Session lookup re-reads `role` and
`is_active` on every request (no caching), so a demotion or disable takes
effect on the very next request.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import Cookie, Depends, Header, Request, Response
from sqlalchemy import delete, select, update
from sqlalchemy.orm import Session

from ..config import Settings, get_settings
from ..db.models_users_and_sessions import User, UserSession
from ..db.session_factory import get_db
from ..errors import PortalError
from ..security.derived_secret_keys import derive_key
from ..security.session_tokens_and_csrf import CsrfSigner, new_session_token, sha256_hex

SESSION_COOKIE_NAME = "session"
ANON_CSRF_COOKIE_NAME = "anon_csrf_nonce"
ADMIN_ROLES = ("ADMIN", "SUPERADMIN")
_RENEW_THRESHOLD = timedelta(hours=1)


@dataclass
class AuthContext:
    user: User
    session: UserSession


def csrf_signer_for(settings: Settings) -> CsrfSigner:
    return CsrfSigner(derive_key(settings.SECRET_KEY, "csrf"))


def _idle_ttl_sec(role: str, settings: Settings) -> int:
    return settings.ADMIN_SESSION_IDLE_TTL_SEC if role in ADMIN_ROLES else settings.SESSION_TTL_SEC


def get_client_ip(request: Request) -> Optional[str]:
    return request.client.host if request.client else None


def purge_expired_sessions(db: Session) -> int:
    """`expires_at` is always clamped to `absolute_expires_at` (at creation and
    on every renewal — see `create_session`/`_compute_renewal`), so filtering
    on it alone (the indexed column) also catches absolute-expiry rows.
    """
    now = datetime.now(timezone.utc)
    result = db.execute(delete(UserSession).where(UserSession.expires_at <= now))
    return result.rowcount


def create_session(
    db: Session, user: User, *, ip: Optional[str], user_agent: Optional[str]
) -> tuple[str, str]:
    """Insert a session row; returns `(cookie_token, csrf_token)`."""
    settings = get_settings()
    token, token_hash = new_session_token()
    nonce = CsrfSigner.new_nonce()
    now = datetime.now(timezone.utc)
    idle_ttl = _idle_ttl_sec(user.role, settings)
    absolute_expires_at = now + timedelta(seconds=settings.SESSION_ABSOLUTE_TTL_SEC)
    session_row = UserSession(
        token_hash=token_hash,
        user_id=user.id,
        csrf_nonce=nonce,
        expires_at=min(now + timedelta(seconds=idle_ttl), absolute_expires_at),
        absolute_expires_at=absolute_expires_at,
        ip=ip,
        user_agent=user_agent,
    )
    db.add(session_row)
    db.flush()
    csrf_token = csrf_signer_for(settings).token(nonce)
    return token, csrf_token


def delete_session(db: Session, token_hash: str) -> None:
    db.execute(delete(UserSession).where(UserSession.token_hash == token_hash))


def delete_other_sessions_for_user(db: Session, user_id, keep_token_hash: str) -> int:
    result = db.execute(
        delete(UserSession).where(UserSession.user_id == user_id, UserSession.token_hash != keep_token_hash)
    )
    return result.rowcount


def delete_all_sessions_for_user(db: Session, user_id) -> int:
    result = db.execute(delete(UserSession).where(UserSession.user_id == user_id))
    return result.rowcount


def set_session_cookie(response: Response, token: str, settings: Settings) -> None:
    response.set_cookie(
        SESSION_COOKIE_NAME,
        token,
        httponly=True,
        samesite="lax",
        secure=settings.COOKIE_SECURE,
        max_age=settings.SESSION_ABSOLUTE_TTL_SEC,
        path="/",
    )


def clear_session_cookie(response: Response, settings: Settings) -> None:
    response.delete_cookie(
        SESSION_COOKIE_NAME, path="/", httponly=True, samesite="lax", secure=settings.COOKIE_SECURE
    )


def _compute_renewal(session_row: UserSession, user: User, settings: Settings) -> Optional[datetime]:
    """Returns a new `expires_at`, or `None` if the current value should stand.

    Slides forward at most once per hour, never past `absolute_expires_at`.
    Clamps downward immediately (no threshold) when the role's idle window
    just got shorter — e.g. a promotion to ADMIN/SUPERADMIN mid-session —
    so a shorter idle TTL takes effect on the very next request instead of
    only once the slide would have extended it anyway.
    """
    now = datetime.now(timezone.utc)
    idle_ttl = _idle_ttl_sec(user.role, settings)
    candidate = min(now + timedelta(seconds=idle_ttl), session_row.absolute_expires_at)
    if candidate < session_row.expires_at:
        return candidate
    if candidate - session_row.expires_at >= _RENEW_THRESHOLD:
        return candidate
    return None


def _resolve_session(db: Session, token: Optional[str]) -> Optional[AuthContext]:
    if not token:
        return None
    token_hash = sha256_hex(token)
    now = datetime.now(timezone.utc)
    row = db.execute(
        select(UserSession, User)
        .join(User, User.id == UserSession.user_id)
        .where(
            UserSession.token_hash == token_hash,
            UserSession.expires_at > now,
            UserSession.absolute_expires_at > now,
            User.is_active.is_(True),
        )
    ).first()
    if row is None:
        return None
    session_row, user = row

    new_expires_at = _compute_renewal(session_row, user, get_settings())
    if new_expires_at is not None:
        # Persisted directly (not just mutated on the ORM object): a plain
        # GET request never otherwise commits, so without this write the
        # slide is lost and the session idles out on schedule regardless of
        # activity.
        db.execute(
            update(UserSession).where(UserSession.token_hash == token_hash).values(expires_at=new_expires_at)
        )
        db.commit()
        session_row.expires_at = new_expires_at

    return AuthContext(user=user, session=session_row)


def resolve_session_dependency(
    db: Session = Depends(get_db),
    session_token: Optional[str] = Cookie(default=None, alias=SESSION_COOKIE_NAME),
) -> Optional[AuthContext]:
    """FastAPI dependency; cached per-request, so `require_user` and
    `require_csrf` on the same route resolve the session only once.
    """
    return _resolve_session(db, session_token)


def require_user(ctx: Optional[AuthContext] = Depends(resolve_session_dependency)) -> AuthContext:
    if ctx is None:
        raise PortalError(401, "UNAUTHORIZED", "sign in required")
    return ctx


def require_admin(ctx: AuthContext = Depends(require_user)) -> AuthContext:
    if ctx.user.role not in ADMIN_ROLES:
        raise PortalError(403, "FORBIDDEN_ROLE", "admin role required")
    return ctx


def require_superadmin(ctx: AuthContext = Depends(require_user)) -> AuthContext:
    if ctx.user.role != "SUPERADMIN":
        raise PortalError(403, "FORBIDDEN_ROLE", "superadmin role required")
    return ctx


def require_csrf(
    ctx: Optional[AuthContext] = Depends(resolve_session_dependency),
    x_csrf_token: Optional[str] = Header(default=None, alias="X-CSRF-Token"),
    anon_csrf_nonce: Optional[str] = Cookie(default=None, alias=ANON_CSRF_COOKIE_NAME),
) -> None:
    settings = get_settings()
    signer = csrf_signer_for(settings)
    expected_nonce = ctx.session.csrf_nonce if ctx is not None else anon_csrf_nonce
    if not signer.verify(x_csrf_token, expected_nonce):
        raise PortalError(403, "CSRF_FAILED", "missing or invalid CSRF token")
