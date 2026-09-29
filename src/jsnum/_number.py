"""Number.prototype formatting: toString, toFixed, toPrecision, toExponential."""

from __future__ import annotations

import math
from fractions import Fraction

_DIGITS = "0123456789abcdefghijklmnopqrstuvwxyz"


def _check_number(x: int | float) -> float:
    if isinstance(x, bool) or not isinstance(x, (int, float)):
        raise TypeError(f"expected int or float, got {type(x).__name__}")
    try:
        return float(x)
    except OverflowError:
        return math.inf if x > 0 else -math.inf


def _shortest(x: float) -> tuple[str, int]:
    """Shortest round-trip digits of finite x > 0 as (digits, n) with value 0.digits * 10**n.

    n is the ECMA-262 `n` (decimal point position); digits has no trailing zeros.
    """
    r = repr(x)
    mant, _, exp = r.partition("e")
    ip, _, fp = mant.partition(".")
    digits = ip + fp
    n = len(ip) + (int(exp) if exp else 0)
    stripped = digits.lstrip("0")
    n -= len(digits) - len(stripped)
    digits = stripped.rstrip("0")
    return digits, n


def _decimal_string(x: float) -> str:
    """Number::toString(x) in radix 10 for finite x != 0 (sign included)."""
    sign = "-" if x < 0 else ""
    digits, n = _shortest(abs(x))
    k = len(digits)
    if k <= n <= 21:
        return sign + digits + "0" * (n - k)
    if 0 < n <= 21:
        return sign + digits[:n] + "." + digits[n:]
    if -6 < n <= 0:
        return sign + "0." + "0" * (-n) + digits
    e = n - 1
    es = ("+" if e >= 0 else "-") + str(abs(e))
    if k == 1:
        return sign + digits + "e" + es
    return sign + digits[0] + "." + digits[1:] + "e" + es


def _radix_string(value: float, radix: int) -> str:
    """V8's DoubleToRadixCString (src/numbers/conversions.cc) for finite non-zero value."""
    negative = value < 0
    if negative:
        value = -value
    integer = math.floor(value)
    fraction = value - integer
    delta = 0.5 * (math.nextafter(value, math.inf) - value)
    delta = max(math.nextafter(0.0, math.inf), delta)
    frac_digits: list[int] = []
    if fraction >= delta:
        while True:
            fraction *= radix
            delta *= radix
            digit = int(fraction)
            frac_digits.append(digit)
            fraction -= digit
            if fraction > 0.5 or (fraction == 0.5 and (digit & 1)):
                if fraction + delta > 1:
                    # Round up, propagating the carry through the digits already written.
                    while True:
                        if not frac_digits:
                            integer += 1
                            break
                        last = frac_digits.pop()
                        if last + 1 < radix:
                            frac_digits.append(last + 1)
                            break
                    break
            if not fraction >= delta:
                break
    int_digits: list[str] = []
    integer_f = float(integer)
    # Digits below the double's precision are written as zeros. Measured against Node 24: the
    # quotient must still have a binary exponent above 0 (>= 2**53) after the division.
    while integer_f / radix >= 2.0**53:
        integer_f /= radix
        int_digits.append("0")
    while True:
        remainder = math.fmod(integer_f, radix)
        int_digits.append(_DIGITS[int(remainder)])
        integer_f = (integer_f - remainder) / radix
        if not integer_f > 0:
            break
    out = "".join(reversed(int_digits))
    if frac_digits:
        out += "." + "".join(_DIGITS[d] for d in frac_digits)
    return ("-" if negative else "") + out


def number_to_string(x: int | float, radix: int = 10) -> str:
    """ECMAScript Number::toString(x) / Number.prototype.toString(radix)."""
    if isinstance(radix, bool) or not isinstance(radix, int) or not 2 <= radix <= 36:
        raise ValueError("radix must be an integer between 2 and 36")
    v = _check_number(x)
    if v != v:
        return "NaN"
    if v == 0:
        return "0"
    if v in (math.inf, -math.inf):
        return "Infinity" if v > 0 else "-Infinity"
    if radix == 10:
        return _decimal_string(v)
    return _radix_string(v, radix)


def _check_digits(d: int, lo: int, name: str) -> int:
    if isinstance(d, bool) or not isinstance(d, int) or not lo <= d <= 100:
        raise ValueError(f"{name} must be an integer between {lo} and 100")
    return d


def _round_half_up(q: Fraction) -> int:
    """Nearest integer to q >= 0, ties to the larger (the spec's 'pick the larger n')."""
    return math.floor(q + Fraction(1, 2))


def to_fixed(x: int | float, fraction_digits: int = 0) -> str:
    """Number.prototype.toFixed with exact decimal arithmetic."""
    f = _check_digits(fraction_digits, 0, "fraction_digits")
    v = _check_number(x)
    if v != v:
        return "NaN"
    if abs(v) >= 1e21:
        return number_to_string(v)
    sign = "-" if v < 0 else ""
    n = _round_half_up(abs(Fraction(v)) * 10**f)
    if n == 0:
        m = "0"
    else:
        m = str(n)
    if f:
        if len(m) <= f:
            m = "0" * (f + 1 - len(m)) + m
        m = m[:-f] + "." + m[-f:]
    return sign + m


def _digits_for(a: Fraction, p: int) -> tuple[int, int]:
    """For a > 0 return (e, n) with 10**(p-1) <= n < 10**p and n * 10**(e-p+1) closest to a (ties: larger n)."""
    e = len(str(a.numerator)) - len(str(a.denominator))  # within 1 of floor(log10(a))
    while Fraction(10) ** e > a:
        e -= 1
    while Fraction(10) ** (e + 1) <= a:
        e += 1
    n = _round_half_up(a * Fraction(10) ** (p - 1 - e))
    if n >= 10**p:  # rounded up to the next power of ten
        e += 1
        n //= 10
    return e, n


def to_exponential(x: int | float, fraction_digits: int | None = None) -> str:
    """Number.prototype.toExponential; None means as many digits as necessary."""
    v = _check_number(x)
    if v != v or v in (math.inf, -math.inf):
        return number_to_string(v)
    if fraction_digits is not None:
        f = _check_digits(fraction_digits, 0, "fraction_digits")
    sign = "-" if v < 0 else ""
    a = abs(v)
    if fraction_digits is None:
        if a == 0:
            return "0e+0"
        digits, n = _shortest(a)
        e = n - 1
    elif a == 0:
        digits, e = "0" * (f + 1), 0
    else:
        e, m = _digits_for(Fraction(a), f + 1)
        digits = str(m)
    out = digits[0] + ("." + digits[1:] if len(digits) > 1 else "")
    return sign + out + "e" + ("+" if e >= 0 else "-") + str(abs(e))


def to_precision(x: int | float, precision: int | None = None) -> str:
    """Number.prototype.toPrecision; None behaves like Number::toString."""
    v = _check_number(x)
    if precision is None:
        return number_to_string(v)
    if v != v or v in (math.inf, -math.inf):
        return number_to_string(v)
    p = _check_digits(precision, 1, "precision")
    sign = "-" if v < 0 else ""
    a = abs(v)
    if a == 0:
        m, e = "0" * p, 0
    else:
        e, n = _digits_for(Fraction(a), p)
        m = str(n)
    if e < -6 or e >= p:
        out = m[0] + ("." + m[1:] if p != 1 else "")
        return sign + out + "e" + ("+" if e >= 0 else "-") + str(abs(e))
    if e == p - 1:
        return sign + m
    if e >= 0:
        return sign + m[: e + 1] + "." + m[e + 1 :]
    return sign + "0." + "0" * (-(e + 1)) + m
