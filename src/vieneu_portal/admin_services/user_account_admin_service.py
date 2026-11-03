"""Admin user-management services shared by the admin CLI (phase 5) and the
phase 13 HTTP API: one implementation, one audit trail, one set of guards.
`actor=None` means the CLI invoked it directly — it counts as SUPERADMIN and
is audited as `cli:<os-user>`, since the CLI itself is already a privileged,
operator-only surface.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Optional

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ..auth.session_dependencies import delete_all_sessions_for_user
from ..config import Settings
from ..db.models_users_and_sessions import User
from ..errors import PortalError
from ..security.password_hashing import hash_password
from ..user.user_profile_serializer import avatar_initials_from_username, quota_today, sanitize_username
from .admin_audit_log_writer import cli_actor_label, write_admin_audit
from .role_change_guards import guard_not_last_active_superadmin, guard_not_self

ROLES = ("USER", "ADMIN", "SUPERADMIN")
_PRIVILEGED_ROLES = ("ADMIN", "SUPERADMIN")


def _actor_role(actor: Optional[User]) -> str:
    return "SUPERADMIN" if actor is None else actor.role


def _actor_label(actor: Optional[User]) -> str:
    return cli_actor_label() if actor is None else f"user:{actor.email}"


def _actor_id(actor: Optional[User]):
    return actor.id if actor is not None else None


def _require_role_assignable_by(actor: Optional[User], role: str) -> None:
    if role not in ROLES:
        raise PortalError(422, "VALIDATION_ERROR", f"role must be one of {ROLES}")
    if role in _PRIVILEGED_ROLES and _actor_role(actor) != "SUPERADMIN":
        raise PortalError(403, "FORBIDDEN_ROLE", "only a superadmin may create or change an admin or superadmin account")


def create_user_by_admin(
    db: Session, settings: Settings, *, actor: Optional[User], email: str, username: str,
    password: str, role: str = "USER", ip: Optional[str] = None,
) -> User:
    _require_role_assignable_by(actor, role)

    normalized_email = email.strip().lower()
    existing = db.execute(select(User.id).where(func.lower(User.email) == normalized_email)).first()
    if existing is not None:
        raise PortalError(409, "EMAIL_TAKEN", "an account with this email already exists")

    clean_username = sanitize_username(username)
    now = datetime.now(timezone.utc)
    user = User(
        email=normalized_email,
        username=clean_username,
        avatar_initials=avatar_initials_from_username(clean_username),
        password_hash=hash_password(password),
        role=role,
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
        db.rollback()
        raise PortalError(409, "EMAIL_TAKEN", "an account with this email already exists")

    write_admin_audit(
        db, actor_user_id=_actor_id(actor), actor_label=_actor_label(actor),
        action="user.create", target_type="user", target_id=str(user.id), target_label=user.email,
        before=None, after={"email": user.email, "role": user.role}, ip=ip,
    )
    return user


def reset_password(
    db: Session, *, actor: Optional[User], target: User, new_password: str, ip: Optional[str] = None,
) -> None:
    target.password_hash = hash_password(new_password)
    delete_all_sessions_for_user(db, target.id)
    write_admin_audit(
        db, actor_user_id=_actor_id(actor), actor_label=_actor_label(actor),
        action="user.reset_password", target_type="user", target_id=str(target.id),
        target_label=target.email, before=None, after=None, ip=ip,
    )


def set_user_active(
    db: Session, *, actor: Optional[User], target: User, active: bool, ip: Optional[str] = None,
) -> None:
    if not active:
        guard_not_self(actor, target, "disable")
        guard_not_last_active_superadmin(db, target)
    before = {"is_active": target.is_active}
    target.is_active = active
    if not active:
        delete_all_sessions_for_user(db, target.id)
    write_admin_audit(
        db, actor_user_id=_actor_id(actor), actor_label=_actor_label(actor),
        action="user.set_active", target_type="user", target_id=str(target.id), target_label=target.email,
        before=before, after={"is_active": active}, ip=ip,
    )


def set_user_role(
    db: Session, *, actor: Optional[User], target: User, role: str, ip: Optional[str] = None,
) -> None:
    _require_role_assignable_by(actor, role)
    if role != target.role:
        guard_not_self(actor, target, "change the role of")
        if target.role == "SUPERADMIN":
            guard_not_last_active_superadmin(db, target)
    before = {"role": target.role}
    target.role = role
    write_admin_audit(
        db, actor_user_id=_actor_id(actor), actor_label=_actor_label(actor),
        action="user.set_role", target_type="user", target_id=str(target.id), target_label=target.email,
        before=before, after={"role": role}, ip=ip,
    )
