"""Character count and token estimate — pinned by `tests/fixtures/text_contract_vectors/
token_estimate_vectors.json`, shared with the TypeScript mirror in `portal-web/`.

Both sides count code points of the NFC-normalized text, not UTF-16 units
(JS `.length`) or raw code points of a possibly-NFD string: NFD Vietnamese
(combining diacritics) would otherwise count more characters than its NFC
form of the same visible text, and an astral character (e.g. an emoji) is one
code point here, not the two UTF-16 surrogate halves `.length` would count.
"""
from __future__ import annotations

import unicodedata


def count_chars(text: str) -> int:
    return len(unicodedata.normalize("NFC", text))


def estimate_tokens(chars: int, rate_milli: int) -> int:
    """Integer-only on both sides: `ceil(chars * rate_milli / 1000)`."""
    return (chars * rate_milli + 999) // 1000
