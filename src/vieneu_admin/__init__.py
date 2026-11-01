"""VieNeu admin web app: users, API keys, pronunciation dictionaries, Script Lab and Help.

Self-contained: imports neither ``apps.*`` nor the TTS engine. The speech API mounts
``create_admin_router(store, tts_provider=...)`` at ``/admin`` and checks Bearer keys
with ``verify_api_key``. FastAPI is imported lazily so the CLI works without it.
"""
from __future__ import annotations

from typing import TYPE_CHECKING, Any, Optional

from .api_key_verification import verify_api_key
from .models import KeyOwner
from .store import SEED_DIR, AdminStore
from .web_paths import STATIC_DIR

if TYPE_CHECKING:  # pragma: no cover
    from fastapi import APIRouter

__all__ = ["AdminStore", "KeyOwner", "SEED_DIR", "STATIC_DIR", "create_admin_router", "verify_api_key"]


def create_admin_router(store: AdminStore, *, tts_provider: Optional[Any] = None) -> "APIRouter":
    """Build the admin ``APIRouter`` (mount with ``prefix="/admin"``).

    ``tts_provider`` exposes ``available() -> bool``, ``voices() -> list[str]`` and
    ``render(result, voices, fmt) -> bytes`` (``fmt`` is ``"wav"`` or ``"flac"``).
    Pass None when no engine is loaded; Script Lab then shows "engine not loaded".
    """
    from .routes import build_admin_router

    return build_admin_router(store, tts_provider=tts_provider)
