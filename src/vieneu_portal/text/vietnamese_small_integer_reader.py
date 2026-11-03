"""Vietnamese cardinal number reader for 0..999 999, used by the math/chem
span readers (digits inside a math/chem span are read as words; a digit
outside a span is left to the engine's own front-end, which already reads
plain numbers, dates and units).
"""
from __future__ import annotations

_UNITS = ["không", "một", "hai", "ba", "bốn", "năm", "sáu", "bảy", "tám", "chín"]


def _read_0_to_99(n: int, *, has_tens_word: bool) -> str:
    if n < 10:
        return _UNITS[n]
    tens, ones = divmod(n, 10)
    if tens == 1:
        word = "mười"
        if ones == 0:
            return word
        if ones == 5:
            return f"{word} lăm"
        return f"{word} {_UNITS[ones]}"
    word = f"{_UNITS[tens]} mươi"
    if ones == 0:
        return word
    if ones == 1:
        return f"{word} mốt"
    if ones == 5:
        return f"{word} lăm"
    return f"{word} {_UNITS[ones]}"


def _read_0_to_999(n: int, *, pad_hundreds: bool = False) -> str:
    if n < 100:
        if not pad_hundreds:
            return _read_0_to_99(n, has_tens_word=False)
        if n == 0:
            return "không trăm"
        if n < 10:
            return f"không trăm linh {_UNITS[n]}"
        return f"không trăm {_read_0_to_99(n, has_tens_word=True)}"
    hundreds, rest = divmod(n, 100)
    out = f"{_UNITS[hundreds]} trăm"
    if rest == 0:
        return out
    if rest < 10:
        return f"{out} linh {_UNITS[rest]}"
    return f"{out} {_read_0_to_99(rest, has_tens_word=True)}"


def read_vietnamese_integer(n: int) -> str:
    if not (0 <= n <= 999_999):
        raise ValueError(f"read_vietnamese_integer supports 0..999999, got {n}")
    if n == 0:
        return "không"
    thousands, rest = divmod(n, 1000)
    if thousands == 0:
        return _read_0_to_999(rest)
    out = f"{_read_0_to_999(thousands)} nghìn"
    if rest == 0:
        return out
    return f"{out} {_read_0_to_999(rest, pad_hundreds=True)}"
