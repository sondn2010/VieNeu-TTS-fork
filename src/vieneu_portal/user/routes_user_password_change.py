from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ..auth.session_dependencies import AuthContext, delete_other_sessions_for_user, get_client_ip, require_csrf, require_user
from ..config import get_settings
from ..db.session_factory import get_db
from ..errors import PortalError
from ..security import postgres_auth_throttle as throttle
from ..security.password_hashing import MAX_PASSWORD_LEN, MIN_PASSWORD_LEN, hash_password, verify_password

router = APIRouter()


class PasswordChangeRequest(BaseModel):
    current_password: str
    new_password: str


@router.post("/user/password")
def change_password(
    payload: PasswordChangeRequest,
    request: Request,
    db: Session = Depends(get_db),
    ctx: AuthContext = Depends(require_user),
    _csrf: None = Depends(require_csrf),
) -> dict:
    settings = get_settings()
    ip = get_client_ip(request) or "0.0.0.0"
    email_key = ctx.user.email.lower()

    # A stolen session cookie could otherwise brute-force the current
    # password at scrypt speed with no limit; apply the same lockout login
    # uses before verifying.
    throttle.enforce_login_lockout(db, settings, email_key=email_key, ip=ip)

    if not verify_password(payload.current_password, ctx.user.password_hash):
        throttle.record_event(db, kind=throttle.LOGIN_FAILURE, ip=ip, email_key=email_key)
        db.commit()
        raise PortalError(401, "INVALID_CREDENTIALS", "current password is incorrect")

    if not (MIN_PASSWORD_LEN <= len(payload.new_password) <= MAX_PASSWORD_LEN):
        raise PortalError(
            422, "VALIDATION_ERROR", f"new password must be {MIN_PASSWORD_LEN}-{MAX_PASSWORD_LEN} characters"
        )

    ctx.user.password_hash = hash_password(payload.new_password)
    delete_other_sessions_for_user(db, ctx.user.id, keep_token_hash=ctx.session.token_hash)
    db.commit()
    return {"status": "ok"}
