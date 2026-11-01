"""Login, logout, own password change and the dashboard."""
from __future__ import annotations

import logging
import math

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import Response

from .admin_app import AdminApp
from .models import Session, StoreError

log = logging.getLogger("vieneu.admin")


def _client_ip(request: Request) -> str:
    # Behind a reverse proxy, run uvicorn with --proxy-headers/--forwarded-allow-ips so
    # request.client reflects the real client; lockout keys on (username, ip) either way.
    return request.client.host if request.client else "?"


def register(router: APIRouter, app: AdminApp) -> None:
    deps, web, store = app.deps, app.web, app.store

    @router.get("/login", name="admin_login")
    def login_page(request: Request, session=Depends(deps.optional_session)) -> Response:
        if session is not None:
            return web.redirect(request, "admin_dashboard")
        return web.render(request, "login.html", None)

    @router.post("/login", name="admin_login_post", dependencies=[Depends(deps.csrf_anonymous)])
    def login(request: Request, username: str = Form(""), password: str = Form("")) -> Response:
        ip = _client_ip(request)
        wait = app.limiter.locked_for(username, ip)
        if wait > 0:
            minutes = max(1, math.ceil(wait / 60))
            return web.render(request, "login.html", None, status=429, username=username,
                              error=f"Too many failed attempts. Try again in {minutes} minute(s).")
        user = store.authenticate(username, password)
        if user is None:
            app.limiter.record_failure(username, ip)
            log.warning("admin login failed for %r from %s", username[:64], ip)
            return web.render(request, "login.html", None, status=401, username=username,
                              error="Invalid username or password.")
        app.limiter.reset(username, ip)
        token, _ = store.create_session(user.id)
        resp = web.redirect(request, "admin_dashboard")
        web.set_session_cookie(resp, request, token)
        return resp

    @router.post("/logout", name="admin_logout", dependencies=[Depends(deps.csrf_protect)])
    def logout(request: Request, session: Session = Depends(deps.current_session)) -> Response:
        store.delete_session(session.token_hash)
        resp = web.redirect(request, "admin_login")
        web.clear_session_cookie(resp)
        return resp

    @router.get("/", name="admin_dashboard")
    def dashboard(request: Request, session: Session = Depends(deps.current_session)) -> Response:
        enabled = [d for d in store.list_dictionaries() if d.enabled]
        return web.render(request, "dashboard.html", session,
                          key_count=store.count_keys(session.user.id),
                          dictionaries=enabled, engine_available=app.engine_available())

    @router.get("/account/password", name="admin_account_password")
    def password_page(request: Request, session: Session = Depends(deps.current_session)) -> Response:
        return web.render(request, "account_password.html", session)

    @router.post("/account/password", name="admin_account_password_post",
                 dependencies=[Depends(deps.csrf_protect)])
    def change_password(request: Request, session: Session = Depends(deps.current_session),
                        current: str = Form(""), new: str = Form(""), confirm: str = Form("")) -> Response:
        def fail(msg: str) -> Response:
            return web.render(request, "account_password.html", session, status=400, error=msg)

        ip, name = _client_ip(request), session.user.username
        if app.limiter.locked_for(name, ip) > 0:
            return fail("Too many failed attempts. Try again later.")
        if store.authenticate(name, current) is None:
            app.limiter.record_failure(name, ip)
            return fail("Current password is incorrect.")
        if new != confirm:
            return fail("The new passwords do not match.")
        try:
            store.reset_password(session.user.id, new)  # also ends every session of this user
        except StoreError as e:
            return fail(str(e))
        token, fresh = store.create_session(session.user.id)
        resp = web.render(request, "account_password.html", fresh, message="Password changed. "
                          "Other sessions were signed out.")
        web.set_session_cookie(resp, request, token)
        return resp
