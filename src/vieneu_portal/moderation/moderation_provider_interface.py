"""Pluggable content moderation. The same `ModerationProvider.check()` gates
a TTS request's text (phase 10) and a dictionary rule's target on save/import
(phases 5, 9) — one provider, one fail mode, everywhere text reaches a user.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Protocol

CATEGORIES = (
    "PROFANITY_SEVERE",
    "SEXUAL_EXPLICIT",
    "HATE_HARASSMENT",
    "POLITICAL_SOVEREIGNTY",
    "VIOLENCE_ILLEGAL",
)


@dataclass(frozen=True)
class ModerationVerdict:
    allowed: bool
    category: Optional[str] = None
    message_vi: Optional[str] = None


class ContentPolicyViolation(Exception):
    """Raised when a provider rejects text. Route layer maps this to
    `422 CONTENT_POLICY_VIOLATION`."""

    def __init__(self, category: str, message: str) -> None:
        super().__init__(message)
        self.category = category
        self.message = message


class ModerationUnavailable(Exception):
    """The configured provider raised and `MODERATION_FAIL_MODE=closed`.
    Route layer maps this to `503 MODERATION_UNAVAILABLE`; never charges."""


class ModerationProvider(Protocol):
    def check(self, text: str) -> ModerationVerdict: ...
