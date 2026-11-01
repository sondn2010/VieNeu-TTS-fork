"""Assemble the admin APIRouter from its feature modules."""
from __future__ import annotations

from typing import Any, Optional

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

from . import (routes_account, routes_dictionaries, routes_dictionary_entries, routes_dictionary_transfer,
               routes_help, routes_keys, routes_script_lab, routes_users)
from .admin_app import AdminApp
from .auth import build_dependencies
from .security import CsrfSigner
from .store import AdminStore
from .web import AdminWeb, apply_security_headers
from .web_paths import STATIC_DIR

# Whitelisted static assets: name -> media type. Nothing else under static/ is served.
_STATIC_FILES = {
    "htmx.min.js": "text/javascript",
    "app.js": "text/javascript",
    "app.css": "text/css",
}

# Order matters where paths overlap: fixed paths (/dictionaries/import) before /{id}.
_MODULES = (routes_account, routes_keys, routes_users, routes_dictionary_transfer,
            routes_dictionaries, routes_dictionary_entries, routes_script_lab, routes_help)


def build_admin_router(store: AdminStore, *, tts_provider: Optional[Any] = None) -> APIRouter:
    signer = CsrfSigner(store.csrf_secret())
    app = AdminApp(store, build_dependencies(store, signer), AdminWeb(signer), tts_provider)
    router = APIRouter()

    @router.get("/static/{name}", name="admin_static", include_in_schema=False)
    def static_file(name: str) -> FileResponse:
        media = _STATIC_FILES.get(name)
        if media is None:
            raise HTTPException(404)
        resp = FileResponse(STATIC_DIR / name, media_type=media)
        resp.headers["Cache-Control"] = "public, max-age=3600"
        return apply_security_headers(resp)  # type: ignore[return-value]

    for module in _MODULES:
        module.register(router, app)
    return router
