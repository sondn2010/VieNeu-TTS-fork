"""Password hashing, API-key and session-token generation, CSRF signing, login lockout.

Only hashes ever reach the database: scrypt for passwords, SHA-256 for API keys and
session tokens (both are 256-bit random values, so a fast hash is sufficient).
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import secrets
import threading
import time
from collections import deque
from typing import Optional

SCRYPT_N, SCRYPT_R, SCRYPT_P = 2 ** 14, 8, 1
_SCRYPT_MAXMEM = 64 * 1024 * 1024
_MAX_SCRYPT_N = 2 ** 20  # refuse absurd parameters from a tampered hash
API_KEY_PREFIX = "vn_"
KEY_DISPLAY_LEN = 8
SESSION_TTL_SEC = 12 * 3600
MAX_PASSWORD_LEN = 256


def _b64(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")


def _unb64(text: str) -> bytes:
    return base64.urlsafe_b64decode(text + "=" * (-len(text) % 4))


def _scrypt(password: str, salt: bytes, n: int, r: int, p: int) -> bytes:
    return hashlib.scrypt(password.encode("utf-8"), salt=salt, n=n, r=r, p=p,
                          maxmem=_SCRYPT_MAXMEM, dklen=32)


def hash_password(password: str) -> str:
    """Return `scrypt$n$r$p$salt$hash` (salt and hash urlsafe-base64, unpadded)."""
    salt = secrets.token_bytes(16)
    digest = _scrypt(password, salt, SCRYPT_N, SCRYPT_R, SCRYPT_P)
    return f"scrypt${SCRYPT_N}${SCRYPT_R}${SCRYPT_P}${_b64(salt)}${_b64(digest)}"


def verify_password(password: str, encoded: str) -> bool:
    try:
        algo, n_s, r_s, p_s, salt_s, hash_s = encoded.split("$")
        n, r, p = int(n_s), int(r_s), int(p_s)
        if algo != "scrypt" or not (2 <= n <= _MAX_SCRYPT_N) or not (1 <= r <= 32) or not (1 <= p <= 16):
            return False
        expected = _unb64(hash_s)
        actual = _scrypt(password, _unb64(salt_s), n, r, p)
    except (ValueError, TypeError):
        return False
    return hmac.compare_digest(actual, expected)


# Pre-computed so unknown usernames cost the same scrypt time as known ones.
_DUMMY_HASH = hash_password(secrets.token_urlsafe(16))


def burn_password_check(password: str) -> None:
    """Spend one scrypt verification to equalize timing for unknown usernames."""
    verify_password(password, _DUMMY_HASH)


def sha256_hex(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def new_api_key() -> tuple[str, str, str]:
    """Return (plaintext, display_prefix, sha256_hex). The plaintext is shown once."""
    plaintext = API_KEY_PREFIX + secrets.token_urlsafe(32)
    return plaintext, plaintext[:KEY_DISPLAY_LEN], sha256_hex(plaintext)


def new_session_token() -> tuple[str, str]:
    """Return (cookie_value, sha256_hex stored in the sessions table)."""
    token = secrets.token_urlsafe(32)
    return token, sha256_hex(token)


class CsrfSigner:
    """Signed double-submit CSRF tokens: `nonce.HMAC(secret, nonce)`.

    The nonce lives in a cookie (anonymous forms such as /login) or in the session
    row (authenticated forms). Verification needs no database write, so anonymous
    traffic cannot create rows.
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
        return (hmac.compare_digest(nonce.encode(), expected_nonce.encode())
                and hmac.compare_digest(sig.encode(), self._sig(nonce).encode()))


class LoginLimiter:
    """In-memory failure counter keyed by (username, client_ip).

    Keying on the pair means an attacker hammering `admin` from one address does not
    lock the real admin out from another, and a shared reverse-proxy address does not
    lock out every user at once.
    """

    def __init__(self, max_failures: int = 5, window_sec: float = 300.0, max_keys: int = 10_000):
        self.max_failures, self.window, self.max_keys = max_failures, window_sec, max_keys
        self._fails: dict[tuple[str, str], deque[float]] = {}
        self._lock = threading.Lock()

    @staticmethod
    def _key(username: str, ip: str) -> tuple[str, str]:
        return username.strip().casefold()[:64], ip or "?"

    def _prune(self, key: tuple[str, str], now: float) -> deque[float]:
        q = self._fails.get(key, deque())
        while q and now - q[0] >= self.window:
            q.popleft()
        if not q:
            self._fails.pop(key, None)
        return q

    def locked_for(self, username: str, ip: str) -> float:
        """Seconds until another attempt is allowed (0 when not locked)."""
        now = time.monotonic()
        with self._lock:
            q = self._prune(self._key(username, ip), now)
            if len(q) < self.max_failures:
                return 0.0
            return max(0.0, self.window - (now - q[0]))

    def record_failure(self, username: str, ip: str) -> None:
        now = time.monotonic()
        key = self._key(username, ip)
        with self._lock:
            if key not in self._fails and len(self._fails) >= self.max_keys:
                for k in list(self._fails):  # bound memory: drop expired, then oldest
                    self._prune(k, now)
                while len(self._fails) >= self.max_keys:
                    self._fails.pop(next(iter(self._fails)))
            q = self._fails.setdefault(key, deque())
            q.append(now)
            while len(q) > self.max_failures:
                q.popleft()

    def reset(self, username: str, ip: str) -> None:
        with self._lock:
            self._fails.pop(self._key(username, ip), None)
