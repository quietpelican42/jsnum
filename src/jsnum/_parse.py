"""parseInt, parseFloat, Number(string) and Math.round."""

from __future__ import annotations

import math
import re
from fractions import Fraction

from ._ws import trim, trim_start

_FLOAT_PREFIX = re.compile(r"[+-]?(?:Infinity|(?:[0-9]+\.?[0-9]*|\.[0-9]+)(?:[eE][+-]?[0-9]+)?)")
_DECIMAL_FULL = re.compile(r"[+-]?(?:Infinity|(?:[0-9]+\.?[0-9]*|\.[0-9]+)(?:[eE][+-]?[0-9]+)?)")
_NONDECIMAL = re.compile(r"0(?:[xX][0-9a-fA-F]+|[oO][0-7]+|[bB][01]+)")
_NAN = math.nan


def _decimal_to_float(text: str) -> float:
    if text.endswith("Infinity"):
        return -math.inf if text[0] == "-" else math.inf
    return float(text)


def parse_float(s: str) -> float:
    """ECMAScript parseFloat: longest StrDecimalLiteral prefix after leading whitespace, else NaN."""
    m = _FLOAT_PREFIX.match(trim_start(s))
    if m is None:
        return _NAN
    return _decimal_to_float(m.group(0))


def _to_int32(radix: object) -> int:
    if radix is None:
        return 0
    if isinstance(radix, bool):
        return int(radix)
    if isinstance(radix, int):
        n = radix
    elif isinstance(radix, float):
        if radix != radix or math.isinf(radix):
            return 0
        n = int(radix)
    else:
        raise TypeError("radix must be an int, float or None")
    n &= 0xFFFFFFFF
    return n - 0x100000000 if n >= 0x80000000 else n


_DIGIT_VALUES = {c: i for i, c in enumerate("0123456789abcdefghijklmnopqrstuvwxyz")}
_DIGIT_VALUES.update({c.upper(): i for c, i in list(_DIGIT_VALUES.items()) if c.isalpha()})


def _digits_to_float(digits: str, radix: int) -> float:
    """Value of a non-empty digit string as V8 computes it for parseInt."""
    if radix == 10:
        return float(digits)  # correctly rounded, like V8's Strtod path
    if radix & (radix - 1) == 0:
        try:
            return float(int(digits, radix))  # correct rounding, like V8's power-of-two path
        except OverflowError:
            return math.inf
    # Other radixes: V8's HandleGenericCase, 32-bit chunks combined in double arithmetic.
    number = 0.0
    i, n = 0, len(digits)
    while i < n:
        part, multiplier = 0, 1
        while i < n:
            m = multiplier * radix
            if m > 0xFFFFFFFF // 36:
                break
            part = part * radix + _DIGIT_VALUES[digits[i]]
            multiplier = m
            i += 1
        number = _fma(number, float(multiplier), float(part))
    return number


def _fma(a: float, b: float, c: float) -> float:
    """a * b + c with a single rounding, as compiled on arm64 (clang fuses the multiply-add)."""
    try:
        return float(Fraction(a) * Fraction(b) + Fraction(c))
    except OverflowError:
        return math.inf


def parse_int(s: str, radix: int | float | None = None) -> float:
    """ECMAScript parseInt. Returns a float: NaN when there are no digits, -0.0 for '-0'."""
    text = trim_start(s)
    sign = 1
    if text[:1] in ("+", "-"):
        if text[0] == "-":
            sign = -1
        text = text[1:]
    r = _to_int32(radix)
    strip_prefix = True
    if r != 0:
        if r < 2 or r > 36:
            return _NAN
        if r != 16:
            strip_prefix = False
    else:
        r = 10
    if strip_prefix and text[:2] in ("0x", "0X"):
        text = text[2:]
        r = 16
    end = 0
    limit = len(text)
    while end < limit and _DIGIT_VALUES.get(text[end], 99) < r:
        end += 1
    if end == 0:
        return _NAN
    value = _digits_to_float(text[:end], r)
    return -value if sign < 0 else value


def to_number(s: str) -> float:
    """ECMAScript Number(string): StringToNumber."""
    text = trim(s)
    if text == "":
        return 0.0
    if _NONDECIMAL.fullmatch(text):
        return _digits_to_float(text[2:], {"x": 16, "o": 8, "b": 2}[text[1].lower()])
    if _DECIMAL_FULL.fullmatch(text):
        return _decimal_to_float(text)
    return _NAN


def math_round(x: int | float) -> float:
    """Math.round: half toward +Infinity, preserving -0 for inputs in [-0.5, 0)."""
    v = float(x)
    if v != v or math.isinf(v) or v == 0 or abs(v) >= 2.0**52:
        return v
    r = math.floor(v)
    out = float(r + 1) if v - r >= 0.5 else float(r)
    if out == 0 and v < 0:
        return -0.0
    return out
