"""Hand-written cases. Expected values were checked against Node 24."""

from __future__ import annotations

import copy
import math
import pickle
from datetime import datetime, timedelta, timezone
from typing import Any

import pytest

import jsnum
from jsnum import UNDEFINED, json_stringify, number_to_string


def test_number_to_string_thresholds() -> None:
    assert number_to_string(1e21) == "1e+21"
    assert number_to_string(999999999999999900000.0) == "999999999999999900000"
    assert number_to_string(1e-6) == "0.000001"
    assert number_to_string(1e-7) == "1e-7"
    assert number_to_string(-0.0) == "0"
    assert number_to_string(1.0) == "1"
    assert number_to_string(0.1 + 0.2) == "0.30000000000000004"
    assert number_to_string(math.nan) == "NaN"
    assert number_to_string(-math.inf) == "-Infinity"
    assert number_to_string(5e-324) == "5e-324"


def test_number_to_string_radix() -> None:
    assert number_to_string(25, 2) == "11001"
    assert number_to_string(0.5, 2) == "0.1"
    assert number_to_string(-255.5, 16) == "-ff.8"
    assert number_to_string(1e21, 36) == "5v1j4f4ds7c000"
    assert number_to_string(0.1, 3) == "0.0022002200220022002200220022002201"
    with pytest.raises(ValueError):
        number_to_string(1, 1)
    with pytest.raises(ValueError):
        number_to_string(1, 37)


def test_number_to_string_rejects_non_numbers() -> None:
    with pytest.raises(TypeError):
        number_to_string("1")  # type: ignore[arg-type]
    with pytest.raises(TypeError):
        number_to_string(True)


def test_fixed_precision_exponential() -> None:
    assert jsnum.to_fixed(1.005, 2) == "1.00"
    assert jsnum.to_fixed(2.5) == "3"
    assert jsnum.to_fixed(-2.5) == "-3"
    assert jsnum.to_fixed(-1e-10, 2) == "-0.00"
    assert jsnum.to_fixed(1e21, 2) == "1e+21"
    assert jsnum.to_fixed(0, 2) == "0.00"
    assert jsnum.to_precision(123.456, 4) == "123.5"
    assert jsnum.to_precision(0.00001234, 2) == "0.000012"
    assert jsnum.to_precision(1e21, 3) == "1.00e+21"
    assert jsnum.to_precision(9.5, 1) == "1e+1"
    assert jsnum.to_exponential(255) == "2.55e+2"
    assert jsnum.to_exponential(0, 2) == "0.00e+0"
    assert jsnum.to_exponential(math.nan, 101) == "NaN"
    assert jsnum.to_precision(math.inf, 0) == "Infinity"
    with pytest.raises(ValueError):
        jsnum.to_fixed(math.nan, 101)
    with pytest.raises(ValueError):
        jsnum.to_precision(1, 0)


def test_parse_float_and_int() -> None:
    assert jsnum.parse_float("\ufeff\u2028 3.14abc") == 3.14
    assert jsnum.parse_float("\u0663") != jsnum.parse_float("\u0663")  # Arabic-Indic digit is not a digit
    assert jsnum.parse_float(".5e1x") == 5.0
    assert jsnum.parse_float("-Infinityx") == -math.inf
    assert math.copysign(1, jsnum.parse_float("-0")) == -1
    assert jsnum.parse_int("  0x1F") == 31
    assert jsnum.parse_int("0x1F", 10) == 0
    assert jsnum.parse_int("12px") == 12
    assert jsnum.parse_int("9007199254740993") == 9007199254740992.0
    assert jsnum.parse_int("z", 36) == 35
    assert jsnum.parse_int("11", 37) != jsnum.parse_int("11", 37)
    assert jsnum.parse_int("11", 4294967298) == 3  # radix 2 after ToInt32
    assert jsnum.parse_int("", 10) != jsnum.parse_int("", 10)


def test_to_number() -> None:
    assert jsnum.to_number("") == 0.0
    assert jsnum.to_number("  \n") == 0.0
    assert jsnum.to_number("0b101") == 5.0
    assert jsnum.to_number("0o17") == 15.0
    assert jsnum.to_number("0XfF") == 255.0
    assert math.isnan(jsnum.to_number("-0x10"))
    assert math.isnan(jsnum.to_number("1_000"))
    assert math.isnan(jsnum.to_number("12px"))
    assert jsnum.to_number("5.e3") == 5000.0
    assert jsnum.to_number("+Infinity") == math.inf
    assert math.isnan(jsnum.to_number("infinity"))
    assert jsnum.to_number("1e400") == math.inf


def test_math_round() -> None:
    assert jsnum.math_round(2.5) == 3.0
    assert jsnum.math_round(-2.5) == -2.0
    assert jsnum.math_round(0.49999999999999994) == 0.0
    assert math.copysign(1, jsnum.math_round(-0.4)) == -1
    assert math.copysign(1, jsnum.math_round(-0.5)) == -1
    assert jsnum.math_round(4503599627370497.0) == 4503599627370497.0


def test_json_basics() -> None:
    assert json_stringify({"b": 2, "10": 1, "a": 3, "2": 0}) == '{"2":0,"10":1,"b":2,"a":3}'
    assert json_stringify({"4294967295": 1, "4294967294": 2, "01": 3, "-1": 4}) == '{"4294967294":2,"4294967295":1,"01":3,"-1":4}'
    assert json_stringify([1.0, -0.0, math.nan, math.inf, 1e21, 1e-7]) == "[1,0,null,null,1e+21,1e-7]"
    assert json_stringify("\ud800\u2028\x7f\x1f/") == '"\\ud800\u2028\x7f\\u001f/"'
    assert json_stringify("\ud83d\ude00") == '"\U0001f600"'  # a surrogate pair held as two code points
    assert json_stringify([True, 1, None]) == "[true,1,null]"
    assert json_stringify((1, 2)) == "[1,2]"


def test_json_undefined() -> None:
    assert json_stringify({"a": UNDEFINED, "b": [UNDEFINED], "c": 1}) == '{"b":[null],"c":1}'
    assert json_stringify(UNDEFINED) is None
    assert not UNDEFINED
    assert copy.deepcopy(UNDEFINED) is UNDEFINED
    assert repr(UNDEFINED) == "UNDEFINED"


def test_json_indent() -> None:
    assert json_stringify({"a": [1, {}], "b": []}, 2) == '{\n  "a": [\n    1,\n    {}\n  ],\n  "b": []\n}'
    assert json_stringify([1], "--") == "[\n--1\n]"
    assert json_stringify([[1]], 20) == json_stringify([[1]], 10)
    assert json_stringify([1], "x" * 20) == "[\n" + "x" * 10 + "1\n]"
    assert json_stringify([1], 0) == "[1]"
    assert json_stringify([1], -3) == "[1]"
    assert json_stringify([1], "") == "[1]"


def test_json_int_handling() -> None:
    assert json_stringify(2**53) == "9007199254740992"
    with pytest.raises(TypeError, match="int_overflow"):
        json_stringify(2**53 + 1)
    assert json_stringify(2**53 + 1, int_overflow="float") == "9007199254740992"
    assert json_stringify(10**400, int_overflow="float") == "null"
    assert json_stringify(True) == "true"
    with pytest.raises(ValueError):
        json_stringify(1, int_overflow="nope")  # type: ignore[arg-type]


def test_json_keys_are_stringified_like_js() -> None:
    assert json_stringify({1: "a", 2.5: "b", None: "d", 1e21: "e"}) == '{"1":"a","2.5":"b","null":"d","1e+21":"e"}'
    assert json_stringify({True: "c"}) == '{"true":"c"}'
    assert json_stringify({1: "a", "1": "b"}) == '{"1":"b"}'
    with pytest.raises(TypeError):
        json_stringify({(1, 2): 1})


class _Custom:
    def toJSON(self, key: str) -> Any:
        return {"key": key, "n": 1}


def test_json_to_json_hook() -> None:
    assert json_stringify({"a": _Custom(), "b": [_Custom()]}) == '{"a":{"key":"a","n":1},"b":[{"key":"0","n":1}]}'
    assert json_stringify(_Custom()) == '{"key":"","n":1}'


def test_json_datetime() -> None:
    d = datetime(2024, 1, 2, 3, 4, 5, 678999, tzinfo=timezone.utc)
    assert json_stringify(d) == '"2024-01-02T03:04:05.678Z"'
    assert json_stringify(d.astimezone(timezone(timedelta(hours=5)))) == '"2024-01-02T03:04:05.678Z"'
    with pytest.raises(TypeError):
        json_stringify(datetime(2024, 1, 2))


def test_json_errors() -> None:
    with pytest.raises(TypeError, match="not JSON serializable"):
        json_stringify({1, 2})
    with pytest.raises(TypeError, match="not JSON serializable"):
        json_stringify(b"x")
    loop: list[Any] = []
    loop.append(loop)
    with pytest.raises(TypeError, match="circular"):
        json_stringify(loop)
    shared = [1]
    assert json_stringify([shared, shared]) == "[[1],[1]]"  # sharing is not a cycle
    with pytest.raises(TypeError):
        json_stringify(1, indent=True)


def test_pickle_undefined() -> None:
    assert pickle.loads(pickle.dumps(UNDEFINED)) is UNDEFINED
