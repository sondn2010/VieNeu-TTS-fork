"""FastAPI dependencies: session authentication, admin role check and CSRF protection.

CSRF uses signed double-submit tokens (see ``security.CsrfSigner``):
- anonymous forms (``/login``): the nonce lives in the ``vieneu_csrf`` cookie;
- authenticated forms: the nonce is the session's ``csrf`` column, rotated on login.
Neither path writes to the database, so anonymous requests never create session rows.
"""
from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Callable, Optional

from fastapi import Depends, HTTPException, Request

from .models import Session
from .security import CsrfSigner
from .store import AdminStore

SESSION_COOKIE = "vieneu_session"
CSRF_COOKIE = "vieneu_csrf"
CSRF_FIELD = "csrf_token"
CSRF_HEADER = "X-CSRF-Token"
MAX_UPLOAD_BYTES = 5 * 1024 * 1024  # dictionary import file limit
MAX_BODY_BYTES = MAX_UPLOAD_BYTES + 256 * 1024  # upload plus multipart/form overhead


def cookie_secure(request: Request) -> bool:
    return os.environ.get("VIENEU_COOKIE_SECURE") == "1" or request.url.scheme == "https"


def path_for(request: Request, route: str, /, **params) -> str:
    """Path (not absolute URL) of a named route, so redirects survive proxies."""
    return request.url_for(route, **params).path


def is_htmx(request: Request) -> bool:
    return request.headers.get("HX-Request") == "true"


def _check_body_size(request: Request) -> None:
    """Reject oversized bodies before any form parsing spools them to disk."""
    try:
        length = int(request.headers.get("content-length") or 0)
    except ValueError:
        raise HTTPException(400, "Invalid Content-Length") from None
    if length > MAX_BODY_BYTES:
        raise HTTPException(413, "Request body too large")


async def submitted_csrf_token(request: Request) -> Optional[str]:
    _check_body_size(request)
    token = request.headers.get(CSRF_HEADER)
    if token:
        return token
    ctype = request.headers.get("content-type", "")
    if ctype.startswith(("application/x-www-form-urlencoded", "multipart/form-data")):
        value = (await request.form()).get(CSRF_FIELD)  # Starlette caches the parsed form
        return value if isinstance(value, str) else None
    return None


@dataclass(frozen=True)
class AdminDeps:
    optional_session: Callable[..., Optional[Session]]
    current_session: Callable[..., Session]
    require_admin: Callable[..., Session]
    csrf_protect: Callable[..., object]
    csrf_anonymous: Callable[..., object]


def build_dependencies(store: AdminStore, signer: CsrfSigner) -> AdminDeps:
    def optional_session(request: Request) -> Optional[Session]:
        return store.get_session(request.cookies.get(SESSION_COOKIE))

    def current_session(request: Request) -> Session:
        """Logged-in, active user's session; otherwise redirect to the login page."""
        session = optional_session(request)
        if session is not None:
            return session
        login = path_for(request, "admin_login")
        if is_htmx(request):
            raise HTTPException(401, "Login required", headers={"HX-Redirect": login})
        raise HTTPException(303, "Login required", headers={"Location": login})

    def require_admin(session: Session = Depends(current_session)) -> Session:
        if not session.user.is_admin:
            raise HTTPException(403, "Admin role required")
        return session

    async def csrf_protect(request: Request, session: Session = Depends(current_session)) -> None:
        if not signer.verify(await submitted_csrf_token(request), session.csrf):
            raise HTTPException(403, "CSRF token missing or invalid")

    async def csrf_anonymous(request: Request) -> None:
        if not signer.verify(await submitted_csrf_token(request), request.cookies.get(CSRF_COOKIE)):
            raise HTTPException(403, "CSRF token missing or invalid")

    return AdminDeps(optional_session, current_session, require_admin, csrf_protect, csrf_anonymous)
