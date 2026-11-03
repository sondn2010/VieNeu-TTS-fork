"""Ported from `tests/test_admin_security.py` (hashing/CSRF/token cases only —
the in-memory `LoginLimiter` is replaced by `postgres_auth_throttle`, covered
in `test_auth_throttle_and_signup_switch.py`). No DB needed.
"""
from __future__ import annotations

import re

import pytest

from vieneu_portal.security.derived_secret_keys import derive_key
from vieneu_portal.security.password_hashing import burn_password_check, hash_password, verify_password
from vieneu_portal.security.session_tokens_and_csrf import CsrfSigner, new_session_token, sha256_hex


def test_password_hash_format_and_verify() -> None:
    h = hash_password("correct horse")
    algo, n, r, p, salt, digest = h.split("$")
    assert (algo, n, r, p) == ("scrypt", str(2**14), "8", "1")
    assert salt and digest and "correct" not in h
    assert verify_password("correct horse", h)
    assert not verify_password("wrong horse", h)
    assert hash_password("correct horse") != h  # random salt


@pytest.mark.parametrize(
    "bad",
    ["", "plain", "scrypt$1$8$1$aa$bb", "md5$16384$8$1$aa$bb", "scrypt$16384$8$1$!!$??", "scrypt$99999999$8$1$aa$bb"],
)
def test_verify_rejects_malformed_or_hostile_hashes(bad: str) -> None:
    assert verify_password("x", bad) is False


def test_burn_password_check_runs_without_raising() -> None:
    burn_password_check("whatever")


def test_session_token_is_stored_hashed() -> None:
    token, digest = new_session_token()
    assert digest == sha256_hex(token) and token not in digest


def test_csrf_signer_round_trip_and_rejections() -> None:
    signer = CsrfSigner(b"k" * 32)
    nonce = signer.new_nonce()
    tok = signer.token(nonce)
    assert signer.verify(tok, nonce)
    assert not signer.verify(tok, signer.new_nonce())  # bound to the expected nonce
    assert not signer.verify(nonce + ".deadbeef", nonce)  # forged signature
    assert not signer.verify(None, nonce) and not signer.verify(tok, None)
    assert not CsrfSigner(b"z" * 32).verify(tok, nonce)  # other secret
    with pytest.raises(ValueError):
        CsrfSigner(b"short")


def test_derive_key_is_deterministic_and_domain_separated() -> None:
    a = derive_key("x" * 32, "csrf")
    b = derive_key("x" * 32, "csrf")
    c = derive_key("x" * 32, "other-purpose")
    assert a == b  # same secret_key + label -> same derived key, every worker/restart
    assert a != c  # different label -> independent key
    assert len(a) == 32


def test_csrf_secret_derived_from_different_secret_keys_do_not_cross_verify() -> None:
    signer_a = CsrfSigner(derive_key("a" * 32, "csrf"))
    signer_b = CsrfSigner(derive_key("b" * 32, "csrf"))
    nonce = signer_a.new_nonce()
    token = signer_a.token(nonce)
    assert signer_a.verify(token, nonce)
    assert not signer_b.verify(token, nonce)
