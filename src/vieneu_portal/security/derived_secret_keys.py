"""Domain-separated keys derived from the one `SECRET_KEY`, so each purpose
(CSRF today; others later) gets an independent secret without storing extra
keys or re-deriving a new one per process — the same `SECRET_KEY` on every
worker and after a restart yields the same derived key.
"""
from __future__ import annotations

import hashlib
import hmac


def derive_key(secret_key: str, label: str) -> bytes:
    return hmac.new(secret_key.encode("utf-8"), label.encode("utf-8"), hashlib.sha256).digest()
