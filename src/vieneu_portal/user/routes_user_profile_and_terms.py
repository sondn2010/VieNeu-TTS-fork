from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, field_validator
from sqlalchemy.orm import Session

from ..auth.session_dependencies import AuthContext, get_client_ip, require_csrf, require_user
from ..config import get_settings
from ..db.session_factory import get_db
from ..errors import PortalError
from .user_profile_serializer import avatar_initials_from_username, sanitize_username, serialize_profile

router = APIRouter()

_UI_THEMES = ("dark", "light")
_UI_LANGUAGES = ("vi", "en")


class ProfilePatchRequest(BaseModel):
    username: Optional[str] = None
    ui_theme: Optional[str] = None
    ui_language: Optional[str] = None
    onboarding_hidden: Optional[bool] = None

    @field_validator("ui_theme")
    @classmethod
    def _validate_theme(cls, value: Optional[str]) -> Optional[str]:
        if value is not None and value not in _UI_THEMES:
            raise ValueError(f"ui_theme must be one of {_UI_THEMES}")
        return value

    @field_validator("ui_language")
    @classmethod
    def _validate_language(cls, value: Optional[str]) -> Optional[str]:
        if value is not None and value not in _UI_LANGUAGES:
            raise ValueError(f"ui_language must be one of {_UI_LANGUAGES}")
        return value


class TermsAcceptRequest(BaseModel):
    terms_version: str


@router.get("/user/profile")
def get_profile(ctx: AuthContext = Depends(require_user)) -> dict:
    return serialize_profile(ctx.user, get_settings())


@router.patch("/user/profile")
def patch_profile(
    payload: ProfilePatchRequest,
    db: Session = Depends(get_db),
    ctx: AuthContext = Depends(require_user),
    _csrf: None = Depends(require_csrf),
) -> dict:
    if payload.username is not None:
        ctx.user.username = sanitize_username(payload.username)
        ctx.user.avatar_initials = avatar_initials_from_username(ctx.user.username)
    if payload.ui_theme is not None:
        ctx.user.ui_theme = payload.ui_theme
    if payload.ui_language is not None:
        ctx.user.ui_language = payload.ui_language
    if payload.onboarding_hidden is not None:
        ctx.user.onboarding_hidden = payload.onboarding_hidden
    db.commit()
    return serialize_profile(ctx.user, get_settings())


@router.post("/user/terms/accept")
def accept_terms(
    payload: TermsAcceptRequest,
    request: Request,
    db: Session = Depends(get_db),
    ctx: AuthContext = Depends(require_user),
    _csrf: None = Depends(require_csrf),
) -> dict:
    settings = get_settings()
    if payload.terms_version != settings.TERMS_VERSION:
        raise PortalError(409, "TERMS_VERSION_MISMATCH", "terms_version does not match the current version")
    ctx.user.has_accepted_tts_terms = True
    ctx.user.terms_accepted_at = datetime.now(timezone.utc)
    ctx.user.terms_version = payload.terms_version
    ctx.user.terms_accepted_ip = get_client_ip(request)
    db.commit()
    return serialize_profile(ctx.user, settings)
