"""Password hashing, token generation, CSRF signing and login lockout."""
import re

import pytest

from vieneu_admin import security
from vieneu_admin.security import (CsrfSigner, LoginLimiter, hash_password, new_api_key, new_session_token,
                                   sha256_hex, verify_password)


def test_password_hash_format_and_verify():
    h = hash_password("correct horse")
    algo, n, r, p, salt, digest = h.split("$")
    assert (algo, n, r, p) == ("scrypt", str(2 ** 14), "8", "1")
    assert salt and digest and "correct" not in h
    assert verify_password("correct horse", h)
    assert not verify_password("wrong horse", h)
    assert hash_password("correct horse") != h  # random salt


@pytest.mark.parametrize("bad", ["", "plain", "scrypt$1$8$1$aa$bb", "md5$16384$8$1$aa$bb",
                                 "scrypt$16384$8$1$!!$??", "scrypt$99999999$8$1$aa$bb"])
def test_verify_rejects_malformed_or_hostile_hashes(bad):
    assert verify_password("x", bad) is False


def test_api_key_shape_and_hash():
    plain, prefix, digest = new_api_key()
    assert plain.startswith("vn_") and len(plain) > 40
    assert prefix == plain[:8]
    assert digest == sha256_hex(plain) and re.fullmatch(r"[0-9a-f]{64}", digest)
    assert new_api_key()[0] != plain


def test_session_token_is_stored_hashed():
    token, digest = new_session_token()
    assert digest == sha256_hex(token) and token not in digest


def test_csrf_signer_round_trip_and_rejections():
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


def test_limiter_locks_pair_only(monkeypatch):
    clock = [1000.0]
    monkeypatch.setattr(security.time, "monotonic", lambda: clock[0])
    lim = LoginLimiter(max_failures=5, window_sec=300)
    for _ in range(4):
        lim.record_failure("Admin", "1.1.1.1")
    assert lim.locked_for("admin", "1.1.1.1") == 0
    lim.record_failure("admin", "1.1.1.1")
    assert lim.locked_for("ADMIN", "1.1.1.1") > 0
    # The same username from another address and another user from the same address stay open.
    assert lim.locked_for("admin", "2.2.2.2") == 0
    assert lim.locked_for("alice", "1.1.1.1") == 0
    clock[0] += 301
    assert lim.locked_for("admin", "1.1.1.1") == 0


def test_limiter_reset_and_memory_bound():
    lim = LoginLimiter(max_failures=2, window_sec=300, max_keys=3)
    lim.record_failure("a", "ip")
    lim.record_failure("a", "ip")
    assert lim.locked_for("a", "ip") > 0
    lim.reset("a", "ip")
    assert lim.locked_for("a", "ip") == 0
    for i in range(10):
        lim.record_failure(f"user{i}", "ip")
    assert len(lim._fails) <= 3
