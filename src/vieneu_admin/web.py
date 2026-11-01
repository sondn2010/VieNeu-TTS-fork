"""Template rendering, cookies and security headers shared by every admin route."""
from __future__ import annotations

import time
from typing import Any, Optional

from fastapi import Request
from fastapi.responses import HTMLResponse, RedirectResponse, Response
from fastapi.templating import Jinja2Templates

from .auth import CSRF_COOKIE, SESSION_COOKIE, cookie_secure, path_for
from .models import Session
from .security import SESSION_TTL_SEC, CsrfSigner
from .web_paths import TEMPLATES_DIR

# The UI loads only same-origin scripts/styles; htmx is configured without eval.
_CSP = ("default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; "
        "media-src 'self' blob:; connect-src 'self'; form-action 'self'; base-uri 'none'; "
        "frame-ancestors 'none'; object-src 'none'")


def format_ts(value: Optional[int]) -> str:
    if not value:
        return "never"
    return time.strftime("%Y-%m-%d %H:%M", time.localtime(int(value)))


def apply_security_headers(resp: Response) -> Response:
    resp.headers.setdefault("Cache-Control", "no-store")
    resp.headers.setdefault("X-Content-Type-Options", "nosniff")
    resp.headers.setdefault("X-Frame-Options", "DENY")
    resp.headers.setdefault("Referrer-Policy", "same-origin")
    resp.headers.setdefault("Content-Security-Policy", _CSP)
    return resp


class AdminWeb:
    def __init__(self, signer: CsrfSigner):
        self.signer = signer
        self.templates = Jinja2Templates(directory=str(TEMPLATES_DIR))  # autoescape on for .html
        self.templates.env.filters["ts"] = format_ts

    def render(self, request: Request, name: str, session: Optional[Session], *,
               status: int = 200, headers: Optional[dict[str, str]] = None, **context: Any) -> HTMLResponse:
        """Render a page or partial with user, CSRF token and a path helper in context."""
        new_cookie_nonce: Optional[str] = None
        if session is not None:
            nonce = session.csrf
        else:
            nonce = request.cookies.get(CSRF_COOKIE) or ""
            if not self.signer.looks_like_nonce(nonce):
                nonce = new_cookie_nonce = self.signer.new_nonce()
        ctx = {
            "user": session.user if session else None,
            "csrf_token": self.signer.token(nonce),
            "u": lambda route, /, **p: path_for(request, route, **p),
            **context,
        }
        resp = self.templates.TemplateResponse(request, name, ctx, status_code=status, headers=headers)
        if new_cookie_nonce:
            resp.set_cookie(CSRF_COOKIE, new_cookie_nonce, httponly=True, samesite="lax",
                            secure=cookie_secure(request), path="/")
        return apply_security_headers(resp)  # type: ignore[return-value]

    @staticmethod
    def redirect(request: Request, route: str, /, **params: Any) -> RedirectResponse:
        return apply_security_headers(  # type: ignore[return-value]
            RedirectResponse(path_for(request, route, **params), status_code=303))

    @staticmethod
    def set_session_cookie(resp: Response, request: Request, token: str) -> None:
        resp.set_cookie(SESSION_COOKIE, token, max_age=SESSION_TTL_SEC, httponly=True, samesite="lax",
                        secure=cookie_secure(request), path="/")

    @staticmethod
    def clear_session_cookie(resp: Response) -> None:
        resp.delete_cookie(SESSION_COOKIE, path="/")
