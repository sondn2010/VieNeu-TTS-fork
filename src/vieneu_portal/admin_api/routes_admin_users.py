"""`/api/v1/admin/users*` — list/create/view/update/role/password/delete.
Every mutation here writes exactly one `admin_audit_log` row in the same
transaction as the change itself.
"""
from __future__ import annotations

from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from ..admin_services.admin_audit_log_writer import write_admin_audit
from ..admin_services.role_change_guards import guard_not_last_active_superadmin, guard_not_self
from ..admin_services.user_account_admin_service import create_user_by_admin, reset_password, set_user_role
from ..admin_services.user_deletion_service import delete_user
from ..auth.session_dependencies import (
    AuthContext,
    delete_all_sessions_for_user,
    get_client_ip,
    require_admin,
    require_csrf,
    require_superadmin,
)
from ..config import get_settings
from ..db.models_users_and_sessions import User
from ..db.models_voices_and_recordings import TTSRecording
from ..db.session_factory import get_db
from ..errors import PortalError
from ..security.password_hashing import MAX_PASSWORD_LEN, MIN_PASSWORD_LEN
from ..storage.object_storage_interface import ObjectStorage
from ..storage.s3_object_storage import get_object_storage
from ..user.user_profile_serializer import sanitize_username
from .admin_shared_helpers import escape_ilike, get_target_user_or_404, require_actor_can_manage_target

router = APIRouter()

ROLES = ("USER", "ADMIN", "SUPERADMIN")


def _recording_count(db: Session, user_id) -> int:
    return db.execute(select(func.count()).where(TTSRecording.user_id == user_id)).scalar_one()


def serialize_admin_user_row(user: User, recording_count: int) -> dict:
    return {
        "id": str(user.id), "email": user.email, "username": user.username, "role": user.role,
        "is_active": user.is_active, "plan_tier": user.plan_tier, "token_balance": user.token_balance,
        "token_quota_total": user.token_quota_total, "daily_char_limit": user.daily_char_limit,
        "daily_char_remaining": user.daily_char_remaining, "plan_expires_at": user.plan_expires_at,
        "created_at": user.created_at, "last_login_at": user.last_login_at, "recording_count": recording_count,
    }


@router.get("/admin/users")
def list_users(
    search: Optional[str] = None, role: Optional[str] = None, status: Optional[str] = None,
    page: int = 1, limit: int = 20,
    db: Session = Depends(get_db), ctx: AuthContext = Depends(require_admin),
) -> dict:
    limit = min(max(limit, 1), 100)
    page = max(page, 1)
    query = select(User)
    if search:
        pattern = f"%{escape_ilike(search)}%"
        query = query.where(or_(User.email.ilike(pattern), User.username.ilike(pattern)))
    if role is not None:
        if role not in ROLES:
            raise PortalError(422, "VALIDATION_ERROR", f"role must be one of {ROLES}")
        query = query.where(User.role == role)
    if status is not None:
        if status not in ("active", "inactive"):
            raise PortalError(422, "VALIDATION_ERROR", "status must be 'active' or 'inactive'")
        query = query.where(User.is_active.is_(status == "active"))
    if ctx.user.role == "ADMIN":
        query = query.where(User.role == "USER")

    total = db.execute(select(func.count()).select_from(query.subquery())).scalar_one()
    rows = list(
        db.execute(query.order_by(User.created_at.desc()).offset((page - 1) * limit).limit(limit)).scalars()
    )
    counts: dict = {}
    if rows:
        counts = dict(
            db.execute(
                select(TTSRecording.user_id, func.count())
                .where(TTSRecording.user_id.in_([u.id for u in rows]))
                .group_by(TTSRecording.user_id)
            ).all()
        )
    return {
        "items": [serialize_admin_user_row(u, counts.get(u.id, 0)) for u in rows],
        "total_count": total, "page": page, "limit": limit,
    }


class CreateUserRequest(BaseModel):
    email: str
    username: Optional[str] = None
    password: str
    role: Optional[str] = "USER"


@router.post("/admin/users", status_code=201)
def create_user(
    payload: CreateUserRequest, request: Request,
    db: Session = Depends(get_db), ctx: AuthContext = Depends(require_admin), _csrf: None = Depends(require_csrf),
) -> dict:
    settings = get_settings()
    user = create_user_by_admin(
        db, settings, actor=ctx.user, email=payload.email,
        username=payload.username or payload.email.split("@", 1)[0], password=payload.password,
        role=payload.role or "USER", ip=get_client_ip(request),
    )
    db.commit()
    return {"user": serialize_admin_user_row(user, 0)}


@router.get("/admin/users/{user_id}")
def get_user(
    user_id: UUID, db: Session = Depends(get_db), ctx: AuthContext = Depends(require_admin),
) -> dict:
    target = get_target_user_or_404(db, user_id)
    require_actor_can_manage_target(ctx.user, target)
    return {"user": serialize_admin_user_row(target, _recording_count(db, target.id))}


class UpdateUserRequest(BaseModel):
    email: Optional[str] = None
    username: Optional[str] = None
    is_active: Optional[bool] = None


@router.patch("/admin/users/{user_id}")
def update_user(
    user_id: UUID, payload: UpdateUserRequest, request: Request,
    db: Session = Depends(get_db), ctx: AuthContext = Depends(require_admin), _csrf: None = Depends(require_csrf),
) -> dict:
    target = get_target_user_or_404(db, user_id)
    require_actor_can_manage_target(ctx.user, target)

    before = {"email": target.email, "username": target.username, "is_active": target.is_active}
    if payload.is_active is False:
        guard_not_self(ctx.user, target, "disable")
        guard_not_last_active_superadmin(db, target)
    if payload.email is not None:
        normalized = payload.email.strip().lower()
        existing = db.execute(
            select(User.id).where(func.lower(User.email) == normalized, User.id != target.id)
        ).first()
        if existing is not None:
            raise PortalError(409, "EMAIL_TAKEN", "an account with this email already exists")
        target.email = normalized
    if payload.username is not None:
        target.username = sanitize_username(payload.username)
    if payload.is_active is not None:
        target.is_active = payload.is_active
        if not payload.is_active:
            delete_all_sessions_for_user(db, target.id)
    after = {"email": target.email, "username": target.username, "is_active": target.is_active}

    write_admin_audit(
        db, actor_user_id=ctx.user.id, actor_label=f"user:{ctx.user.email}", action="user.update",
        target_type="user", target_id=str(target.id), target_label=target.email, before=before, after=after,
        ip=get_client_ip(request),
    )
    db.commit()
    return {"user": serialize_admin_user_row(target, _recording_count(db, target.id))}


class SetRoleRequest(BaseModel):
    role: str


@router.put("/admin/users/{user_id}/role")
def set_role(
    user_id: UUID, payload: SetRoleRequest, request: Request,
    db: Session = Depends(get_db), ctx: AuthContext = Depends(require_superadmin), _csrf: None = Depends(require_csrf),
) -> dict:
    target = get_target_user_or_404(db, user_id)
    set_user_role(db, actor=ctx.user, target=target, role=payload.role, ip=get_client_ip(request))
    db.commit()
    return {"user": serialize_admin_user_row(target, _recording_count(db, target.id))}


class ResetPasswordRequest(BaseModel):
    new_password: str


@router.post("/admin/users/{user_id}/password")
def admin_reset_password(
    user_id: UUID, payload: ResetPasswordRequest, request: Request,
    db: Session = Depends(get_db), ctx: AuthContext = Depends(require_admin), _csrf: None = Depends(require_csrf),
) -> dict:
    target = get_target_user_or_404(db, user_id)
    require_actor_can_manage_target(ctx.user, target)
    if not (MIN_PASSWORD_LEN <= len(payload.new_password) <= MAX_PASSWORD_LEN):
        raise PortalError(422, "VALIDATION_ERROR", f"password must be {MIN_PASSWORD_LEN}-{MAX_PASSWORD_LEN} characters")
    reset_password(db, actor=ctx.user, target=target, new_password=payload.new_password, ip=get_client_ip(request))
    db.commit()
    return {"status": "ok"}


class DeleteUserRequest(BaseModel):
    confirm_email: str


@router.delete("/admin/users/{user_id}", status_code=204)
def delete_user_route(
    user_id: UUID, payload: DeleteUserRequest, request: Request,
    db: Session = Depends(get_db), ctx: AuthContext = Depends(require_admin), _csrf: None = Depends(require_csrf),
    storage: ObjectStorage = Depends(get_object_storage),
) -> None:
    target = get_target_user_or_404(db, user_id)
    require_actor_can_manage_target(ctx.user, target)
    delete_user(
        db, actor=ctx.user, target=target, confirm_email=payload.confirm_email, storage=storage,
        ip=get_client_ip(request),
    )
    return None
