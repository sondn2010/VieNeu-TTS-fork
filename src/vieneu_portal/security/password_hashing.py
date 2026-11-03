"""Password hashing: scrypt, ported verbatim from `src/vieneu_admin/security.py`
so migrated SQLite password hashes (`scrypt$n$r$p$salt$hash`) stay verifiable
after the phase 5 migration.
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import secrets

SCRYPT_N, SCRYPT_R, SCRYPT_P = 2**14, 8, 1
_SCRYPT_MAXMEM = 64 * 1024 * 1024
_MAX_SCRYPT_N = 2**20  # refuse absurd parameters from a tampered hash
MIN_PASSWORD_LEN = 10
MAX_PASSWORD_LEN = 256


def _b64(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")


def _unb64(text: str) -> bytes:
    return base64.urlsafe_b64decode(text + "=" * (-len(text) % 4))


def _scrypt(password: str, salt: bytes, n: int, r: int, p: int) -> bytes:
    return hashlib.scrypt(password.encode("utf-8"), salt=salt, n=n, r=r, p=p, maxmem=_SCRYPT_MAXMEM, dklen=32)


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


# Pre-computed so an unknown email costs the same scrypt time as a known one.
_DUMMY_HASH = hash_password(secrets.token_urlsafe(16))


def burn_password_check(password: str) -> None:
    """Spend one scrypt verification to equalize timing for unknown emails."""
    verify_password(password, _DUMMY_HASH)
