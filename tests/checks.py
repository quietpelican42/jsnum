"""Row checkers shared by the fixture test and the live differential test."""

from __future__ import annotations

import math
from typing import Any

import jsnum
from corpus import decode, double


def js_str(v: float) -> str:
    """String(v) but with '-0' for negative zero, the way the generators record it."""
    if v == 0 and math.copysign(1, v) < 0:
        return "-0"
    return jsnum.number_to_string(v)


def _expect(f: Any, exp: str) -> bool:
    if exp == "RangeError":
        try:
            f()
        except ValueError:
            return True
        return False
    return bool(f() == exp)


def check_number_row(r: dict[str, Any]) -> list[str]:
    x = double(r["x"])
    bad: list[str] = []
    if jsnum.number_to_string(x) != r["s"]:
        bad.append(f"toString {r['x']}")
    for radix, exp in r["r"]:
        if not _expect(lambda: jsnum.number_to_string(x, radix), exp):
            bad.append(f"toString({radix}) {r['x']}")
    for key, fn in (("fx", jsnum.to_fixed), ("pr", jsnum.to_precision), ("ex", jsnum.to_exponential)):
        arg, exp = r[key]
        if not _expect(lambda: fn(x, arg), exp):
            bad.append(f"{key}({arg}) {r['x']}")
    if jsnum.to_exponential(x) != r["ex0"]:
        bad.append(f"toExponential() {r['x']}")
    if js_str(jsnum.math_round(x)) != r["rd"]:
        bad.append(f"round {r['x']}")
    return bad


# The spec lets parseInt approximate the value for radixes other than 2, 4, 8, 10, 16, 32 (ECMA-262
# 19.2.5). V8 does, by accumulating 32-bit chunks in double arithmetic. jsnum reproduces that chunking
# but not every last bit; results that differ by a few ulps above 2**53 in those radixes are collected here.
APPROX: list[tuple[str, Any, str, str]] = []
_EXACT_RADIXES = {0, 2, 4, 8, 10, 16, 32}


def _is_v8_approximation(got: float, radix: Any, exp: str) -> bool:
    r = _radix(radix)
    if r is None or isinstance(r, float) and (r != r or math.isinf(r)):
        return False
    n = int(r) & 0xFFFFFFFF
    n = n - 0x100000000 if n >= 0x80000000 else n
    if n in _EXACT_RADIXES or not 2 <= n <= 36:
        return False
    want = float(exp)
    return abs(want) > 2.0**53 and abs(got - want) <= 1e-13 * abs(want)


def _radix(v: Any) -> int | float | None:
    if isinstance(v, str):
        return float(v)  # "NaN" / "Infinity"
    return v  # type: ignore[no-any-return]


def check_parse_row(r: dict[str, Any]) -> list[str]:
    s = r["s"]
    bad: list[str] = []
    if js_str(jsnum.parse_float(s)) != r["pf"]:
        bad.append(f"parseFloat {s!r}")
    if js_str(jsnum.parse_int(s)) != r["pi"]:
        bad.append(f"parseInt {s!r}")
    for radix, exp in r["pr"]:
        got = jsnum.parse_int(s, _radix(radix))
        if js_str(got) != exp:
            if _is_v8_approximation(got, radix, exp):
                APPROX.append((s, radix, exp, js_str(got)))
            else:
                bad.append(f"parseInt({s!r}, {radix!r})")
    if js_str(jsnum.to_number(s)) != r["n"]:
        bad.append(f"Number {s!r}")
    return bad


def check_json_row(index: int, r: dict[str, Any]) -> list[str]:
    value = decode(r["v"], jsnum.UNDEFINED, floats=index % 2 == 1)
    bad: list[str] = []
    got = jsnum.json_stringify(value, r.get("i"))
    if got != r["e"]:
        bad.append(f"json_stringify row {index} indent={r.get('i')!r}")
    if jsnum.json_stringify(value) != r["ec"]:
        bad.append(f"json_stringify compact row {index}")
    return bad
