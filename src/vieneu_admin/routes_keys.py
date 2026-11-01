"""API keys: everyone manages their own keys; admins see and may revoke every key."""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import Response

from .admin_app import AdminApp
from .models import ForbiddenError, NotFoundError, Session, StoreError


def register(router: APIRouter, app: AdminApp) -> None:
    deps, web, store = app.deps, app.web, app.store

    def keys_page(request: Request, session: Session, *, status: int = 200,
                  new_key: Optional[str] = None, new_key_name: str = "", error: str = "") -> Response:
        user = session.user
        keys = store.list_keys(None if user.is_admin else user.id)
        return web.render(request, "keys.html", session, status=status, keys=keys,
                          show_owner=user.is_admin, new_key=new_key, new_key_name=new_key_name, error=error)

    @router.get("/keys", name="admin_keys")
    def list_keys(request: Request, session: Session = Depends(deps.current_session)) -> Response:
        return keys_page(request, session)

    @router.post("/keys", name="admin_keys_create", dependencies=[Depends(deps.csrf_protect)])
    def create_key(request: Request, session: Session = Depends(deps.current_session),
                   name: str = Form("")) -> Response:
        try:
            plaintext, key = store.create_key(session.user.id, name)
        except StoreError as e:
            return keys_page(request, session, status=400, error=str(e))
        # The plaintext appears in this one response only (Cache-Control: no-store).
        return keys_page(request, session, new_key=plaintext, new_key_name=key.name)

    @router.post("/keys/{key_id}/revoke", name="admin_keys_revoke", dependencies=[Depends(deps.csrf_protect)])
    def revoke_key(request: Request, key_id: int, session: Session = Depends(deps.current_session)) -> Response:
        try:
            store.revoke_key(key_id, session.user)  # owner check lives in the store
        except ForbiddenError as e:
            raise HTTPException(403, str(e)) from e
        except NotFoundError as e:
            raise HTTPException(404, str(e)) from e
        return web.redirect(request, "admin_keys")
