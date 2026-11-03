"""UTF-8 TSV blocklist provider: `CATEGORY<TAB>term` per line, NFC + lowercase
whole-word literal match. Deliberately simple — a real moderation vendor
belongs behind the same `ModerationProvider` interface later.
"""
from __future__ import annotations

import logging
import re
import unicodedata
from pathlib import Path

from .moderation_provider_interface import CATEGORIES, ModerationVerdict

log = logging.getLogger("vieneu.portal.moderation")

_MESSAGE_VI = {
    "PROFANITY_SEVERE": "Nội dung chứa ngôn từ tục tĩu nghiêm trọng.",
    "SEXUAL_EXPLICIT": "Nội dung chứa yếu tố khiêu dâm.",
    "HATE_HARASSMENT": "Nội dung chứa thù ghét hoặc quấy rối.",
    "POLITICAL_SOVEREIGNTY": "Nội dung liên quan đến chủ quyền hoặc chính trị nhạy cảm.",
    "VIOLENCE_ILLEGAL": "Nội dung chứa bạo lực hoặc hoạt động phi pháp.",
}


class BlocklistModerationProvider:
    def __init__(self, path: str) -> None:
        self._terms: list = []   # [(category, NFC-lowercased term)]
        self._load(path)

    def _load(self, path: str) -> None:
        for lineno, raw_line in enumerate(Path(path).read_text(encoding="utf-8").splitlines(), start=1):
            line = raw_line.strip()
            if not line or line.startswith("#"):
                continue
            parts = line.split("\t")
            if len(parts) != 2:
                raise ValueError(f"{path}:{lineno}: expected 'CATEGORY<TAB>term', got {raw_line!r}")
            category, term = parts
            if category not in CATEGORIES:
                raise ValueError(f"{path}:{lineno}: unknown category {category!r}")
            normalized = unicodedata.normalize("NFC", term).strip().lower()
            if normalized:
                self._terms.append((category, normalized))

    def check(self, text: str) -> ModerationVerdict:
        normalized = unicodedata.normalize("NFC", text).lower()
        for category, term in self._terms:
            pattern = r"(?<!\w)" + re.escape(term) + r"(?!\w)"
            if re.search(pattern, normalized):
                if category == "POLITICAL_SOVEREIGNTY":
                    # Never the text itself — only enough to see volume/trend.
                    log.warning("moderation: POLITICAL_SOVEREIGNTY hit (text length=%d)", len(text))
                return ModerationVerdict(allowed=False, category=category, message_vi=_MESSAGE_VI[category])
        return ModerationVerdict(allowed=True)
