"""Small helpers shared by every `/api/v1/admin` router."""
from __future__ import annotations

from uuid import UUID

from sqlalchemy.orm import Session

from ..db.models_users_and_sessions import User
from ..errors import PortalError

_ILIKE_ESCAPE = {"\\": "\\\\", "%": "\\%", "_": "\\_"}


def get_target_user_or_404(db: Session, user_id: UUID) -> User:
    user = db.get(User, user_id)
    if user is None:
        raise PortalError(404, "NOT_FOUND", "user not found")
    return user


def require_actor_can_manage_target(actor: User, target: User) -> None:
    """ADMIN manages `USER` accounts only; SUPERADMIN manages everyone."""
    if actor.role == "ADMIN" and target.role != "USER":
        raise PortalError(403, "FORBIDDEN_ROLE", "an admin may only manage USER accounts")


def escape_ilike(term: str) -> str:
    return "".join(_ILIKE_ESCAPE.get(ch, ch) for ch in term)
