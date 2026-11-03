"""Builds the configured `ModerationProvider` from `Settings.MODERATION_PROVIDER`."""
from __future__ import annotations

import logging

from ..config import ConfigError, Settings
from .blocklist_moderation_provider import BlocklistModerationProvider
from .moderation_provider_interface import ModerationProvider, ModerationVerdict

log = logging.getLogger("vieneu.portal.moderation")


class OffModerationProvider:
    """Stubbed-off default: allows everything, debug-logs the length only."""

    def check(self, text: str) -> ModerationVerdict:
        log.debug("moderation provider is 'off': allowing %d chars unchecked", len(text))
        return ModerationVerdict(allowed=True)


def build_moderation_provider(settings: Settings) -> ModerationProvider:
    if settings.MODERATION_PROVIDER == "off":
        return OffModerationProvider()
    if settings.MODERATION_PROVIDER == "blocklist":
        if not settings.MODERATION_BLOCKLIST_PATH:
            raise ConfigError(
                "VIENEU_PORTAL_MODERATION_BLOCKLIST_PATH is required when MODERATION_PROVIDER=blocklist"
            )
        return BlocklistModerationProvider(settings.MODERATION_BLOCKLIST_PATH)
    raise ConfigError(f"unknown MODERATION_PROVIDER {settings.MODERATION_PROVIDER!r}")
