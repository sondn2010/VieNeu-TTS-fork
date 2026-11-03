"""Chemical formula token reader. `read_chemical_formula_token` parses one
whitespace-delimited token as `[coefficient digits] (element symbol [subscript
digits])+`, case-sensitive (symbols are `Xx` form), consuming the token
exactly or not at all — any leftover character means it is not a formula.
`A4`/`MP3`/`COVID-19` all fail this (no element is `A`, `M`, `MP`, or `D`).
"""
from __future__ import annotations

from typing import Optional

from .chemical_element_symbols import ELEMENT_SYMBOLS
from .vietnamese_small_integer_reader import read_vietnamese_integer


def _read_leading_digits(token: str, i: int) -> tuple:
    j = i
    while j < len(token) and token[j].isdigit():
        j += 1
    if j == i:
        return None, i
    return int(token[i:j]), j


def read_chemical_formula_token(token: str) -> Optional[str]:
    if not token:
        return None
    n = len(token)
    words: list = []

    coeff, i = _read_leading_digits(token, 0)
    if coeff is not None:
        words.append(read_vietnamese_integer(coeff))
    if i >= n:
        return None   # digits only (or empty): not a formula, no element present

    groups = 0
    while i < n:
        if i + 2 <= n and token[i : i + 2] in ELEMENT_SYMBOLS:
            symbol = token[i : i + 2]
            i += 2
        elif token[i] in ELEMENT_SYMBOLS:
            symbol = token[i]
            i += 1
        else:
            return None   # a character that cannot start a valid element symbol
        words.append(symbol)
        groups += 1
        count, i = _read_leading_digits(token, i)
        if count is not None:
            words.append(read_vietnamese_integer(count))

    if groups == 0:
        return None
    return " ".join(words)
