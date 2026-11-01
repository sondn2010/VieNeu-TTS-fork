"""Shared state handed to every admin route module."""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Optional

from .auth import AdminDeps
from .script_lab_state import ScriptLabState
from .security import LoginLimiter
from .store import AdminStore
from .web import AdminWeb

log = logging.getLogger("vieneu.admin")


@dataclass
class AdminApp:
    """Everything a route module needs, built once per router."""

    store: AdminStore
    deps: AdminDeps
    web: AdminWeb
    tts_provider: Optional[Any]
    limiter: LoginLimiter = field(default_factory=LoginLimiter)
    lab: ScriptLabState = field(default_factory=ScriptLabState)

    def engine_available(self) -> bool:
        if self.tts_provider is None:
            return False
        try:
            return bool(self.tts_provider.available())
        except Exception:  # a broken provider must not take the admin UI down
            log.exception("tts_provider.available() failed")
            return False

    def engine_voices(self) -> list[str]:
        if not self.engine_available():
            return []
        try:
            return [str(v) for v in self.tts_provider.voices()]  # type: ignore[union-attr]
        except Exception:
            log.exception("tts_provider.voices() failed")
            return []
