"""Session tokens and CSRF signing, ported from `src/vieneu_admin/security.py`."""
from __future__ import annotations

import hashlib
import hmac
import secrets
from typing import Optional


def sha256_hex(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def new_session_token() -> tuple[str, str]:
    """Return (cookie_value, sha256_hex stored in `user_sessions.token_hash`)."""
    token = secrets.token_urlsafe(32)
    return token, sha256_hex(token)


class CsrfSigner:
    """Signed double-submit CSRF tokens: `nonce.HMAC(secret, nonce)`.

    The nonce lives in a cookie (anonymous forms such as signup/login) or in
    the session row (authenticated forms). Verification needs no database
    write, so anonymous traffic cannot create rows.
    """

    def __init__(self, secret: bytes):
        if len(secret) < 32:
            raise ValueError("CSRF secret must be at least 32 bytes")
        self._secret = secret

    @staticmethod
    def new_nonce() -> str:
        return secrets.token_urlsafe(24)

    @staticmethod
    def looks_like_nonce(value: Optional[str]) -> bool:
        return bool(value) and 16 <= len(value) <= 64 and value.replace("-", "").replace("_", "").isalnum()

    def _sig(self, nonce: str) -> str:
        return hmac.new(self._secret, b"csrf|" + nonce.encode("utf-8"), hashlib.sha256).hexdigest()

    def token(self, nonce: str) -> str:
        return f"{nonce}.{self._sig(nonce)}"

    def verify(self, token: Optional[str], expected_nonce: Optional[str]) -> bool:
        if not token or not expected_nonce or token.count(".") != 1:
            return False
        nonce, sig = token.split(".")
        return hmac.compare_digest(nonce.encode(), expected_nonce.encode()) and hmac.compare_digest(
            sig.encode(), self._sig(nonce).encode()
        )
