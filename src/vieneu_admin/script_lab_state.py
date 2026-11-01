"""Bounded in-memory Script Lab state per session: last analysis, last render, render guard.

Kept in process memory on purpose: it is a convenience cache for downloads, never a
source of truth, and the admin app assumes a single API instance.
"""
from __future__ import annotations

import threading
from collections import OrderedDict
from dataclasses import dataclass
from typing import Optional

MAX_SESSIONS_WITH_JSON = 64
MAX_SESSIONS_WITH_AUDIO = 8  # rendered audio is large; keep only the most recent few


@dataclass(frozen=True)
class RenderedAudio:
    data: bytes
    fmt: str  # "wav" or "flac"
    stamp: str  # cache-busting token used in the <audio> URL


class ScriptLabState:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._json: OrderedDict[str, str] = OrderedDict()
        self._audio: OrderedDict[str, RenderedAudio] = OrderedDict()
        self._rendering: set[str] = set()

    @staticmethod
    def _put(store: OrderedDict, key: str, value, limit: int) -> None:
        store[key] = value
        store.move_to_end(key)
        while len(store) > limit:
            store.popitem(last=False)

    def save_json(self, session_key: str, payload: str) -> None:
        with self._lock:
            self._put(self._json, session_key, payload, MAX_SESSIONS_WITH_JSON)

    def get_json(self, session_key: str) -> Optional[str]:
        with self._lock:
            return self._json.get(session_key)

    def save_audio(self, session_key: str, audio: RenderedAudio) -> None:
        with self._lock:
            self._put(self._audio, session_key, audio, MAX_SESSIONS_WITH_AUDIO)

    def get_audio(self, session_key: str) -> Optional[RenderedAudio]:
        with self._lock:
            return self._audio.get(session_key)

    def begin_render(self, session_key: str) -> bool:
        """Claim the session's single render slot; False when one is already running."""
        with self._lock:
            if session_key in self._rendering:
                return False
            self._rendering.add(session_key)
            return True

    def end_render(self, session_key: str) -> None:
        with self._lock:
            self._rendering.discard(session_key)
