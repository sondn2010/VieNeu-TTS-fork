"""FastAPI app factory. Shared file: later phases append their own
`app.include_router(...)` call in the marked block, in dependency order
(2, 3, 9, 10, 13), and never touch anything else here.
"""
from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse

from . import routes_health
from .admin_api import (
    routes_admin_audit_log,
    routes_admin_system_dictionaries,
    routes_admin_user_keys_and_recordings,
    routes_admin_user_quota_and_plan,
    routes_admin_users,
    routes_admin_voices,
)
from .auth import routes_auth_signup_login_logout
from .config import get_settings
from .dictionaries import routes_account_dictionary
from .errors import install_error_handlers
from .tts import routes_recordings_library, routes_tts_generate, routes_tts_stream
from .user import routes_user_password_change, routes_user_profile_and_terms
from .voices import routes_voices


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title="VieNeu Portal", version="0.1.0")
    install_error_handlers(app)

    app.include_router(routes_health.router, prefix="/api/v1")
    # --- routers: append below in dependency order, never reorder existing lines ---
    app.include_router(routes_auth_signup_login_logout.router, prefix="/api/v1")
    app.include_router(routes_user_password_change.router, prefix="/api/v1")
    app.include_router(routes_user_profile_and_terms.router, prefix="/api/v1")
    app.include_router(routes_voices.router, prefix="/api/v1")
    app.include_router(routes_account_dictionary.router, prefix="/api/v1")
    app.include_router(routes_tts_generate.router, prefix="/api/v1")
    app.include_router(routes_tts_stream.router, prefix="/api/v1")
    app.include_router(routes_recordings_library.router, prefix="/api/v1")
    app.include_router(routes_admin_users.router, prefix="/api/v1")
    app.include_router(routes_admin_user_quota_and_plan.router, prefix="/api/v1")
    app.include_router(routes_admin_user_keys_and_recordings.router, prefix="/api/v1")
    app.include_router(routes_admin_system_dictionaries.router, prefix="/api/v1")
    app.include_router(routes_admin_voices.router, prefix="/api/v1")
    app.include_router(routes_admin_audit_log.router, prefix="/api/v1")

    if settings.WEB_DIST_DIR:
        dist_dir = Path(settings.WEB_DIST_DIR)
        if dist_dir.is_dir():
            _mount_spa(app, dist_dir)

    return app


def _mount_spa(app: FastAPI, dist_dir: Path) -> None:
    """Serve the Next.js static export at `/`: exact file, then `<path>/index.html`,
    then `404.html`. `/api/*` always 404s as JSON instead of falling through here.
    """
    root = dist_dir.resolve()

    @app.get("/{full_path:path}", include_in_schema=False)
    async def spa_fallback(full_path: str) -> FileResponse:
        if full_path == "api" or full_path.startswith("api/"):
            raise HTTPException(status_code=404)
        try:
            candidate = (root / full_path).resolve()
        except (ValueError, OSError):
            raise HTTPException(status_code=404)
        if candidate != root and root not in candidate.parents:
            raise HTTPException(status_code=404)
        if candidate.is_file():
            return FileResponse(candidate)
        index_candidate = candidate / "index.html"
        if index_candidate.is_file():
            return FileResponse(index_candidate)
        not_found = root / "404.html"
        if not_found.is_file():
            return FileResponse(not_found, status_code=404)
        raise HTTPException(status_code=404)
