"""JSON.stringify."""

from __future__ import annotations

import math
import re
from datetime import datetime, timezone
from typing import Any, Literal

from ._number import number_to_string


class _Undefined:
    """Type of the UNDEFINED sentinel."""

    _instance: _Undefined | None = None

    def __new__(cls) -> _Undefined:
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __repr__(self) -> str:
        return "UNDEFINED"

    def __bool__(self) -> bool:
        return False

    def __copy__(self) -> _Undefined:
        return self

    def __deepcopy__(self, memo: object) -> _Undefined:
        return self

    def __reduce__(self) -> str:
        return "UNDEFINED"


UNDEFINED = _Undefined()

_ESCAPE_RE = re.compile('[\x00-\x1f"\\\\\ud800-\udfff]')
_PAIR_RE = re.compile("[\ud800-\udbff][\udc00-\udfff]")
_SIMPLE = {'"': '\\"', "\\": "\\\\", "\b": "\\b", "\f": "\\f", "\n": "\\n", "\r": "\\r", "\t": "\\t"}
_PRIMITIVES = (str, int, float, bool, type(None), dict, list, tuple)
_MAX_SAFE = 2**53
_MAX_INDEX = 2**32 - 2  # largest array index


def _escape_char(m: re.Match[str]) -> str:
    c = m.group(0)
    simple = _SIMPLE.get(c)
    return simple if simple is not None else "\\u%04x" % ord(c)


def _join_pair(m: re.Match[str]) -> str:
    s = m.group(0)
    return chr(0x10000 + ((ord(s[0]) - 0xD800) << 10) + (ord(s[1]) - 0xDC00))


def quote(s: str) -> str:
    """JSON quoting as done by JSON.stringify (well-formed: lone surrogates become \\udXXX)."""
    if _ESCAPE_RE.search(s) is None:
        return '"' + s + '"'
    s = _PAIR_RE.sub(_join_pair, s)
    return '"' + _ESCAPE_RE.sub(_escape_char, s) + '"'


def _is_index(k: str) -> bool:
    return k.isascii() and k.isdigit() and (k == "0" or k[0] != "0") and int(k) <= _MAX_INDEX


def _key_string(k: Any) -> str:
    if isinstance(k, str):
        return k
    if k is None:
        return "null"
    if isinstance(k, bool):
        return "true" if k else "false"
    if isinstance(k, (int, float)):
        return number_to_string(k)
    if k is UNDEFINED:
        return "undefined"
    raise TypeError(f"unsupported object key type: {type(k).__name__}")


def _iso(d: datetime) -> str:
    if d.tzinfo is None:
        raise TypeError("naive datetime cannot be serialized; attach a tzinfo")
    u = d.astimezone(timezone.utc)
    return "%04d-%02d-%02dT%02d:%02d:%02d.%03dZ" % (u.year, u.month, u.day, u.hour, u.minute, u.second, u.microsecond // 1000)


class _Writer:
    def __init__(self, gap: str, big_int: str) -> None:
        self.gap = gap
        self.big_int = big_int
        self.stack: list[int] = []

    def number(self, v: int | float) -> str:
        if isinstance(v, int):
            if -_MAX_SAFE <= v <= _MAX_SAFE:
                return str(v)
            if self.big_int != "float":
                raise TypeError(f"int {v} is outside the exactly representable range of a JS number (2**53); pass int_overflow='float' to round it")
            try:
                v = float(v)
            except OverflowError:
                return "null"
        if v != v or v in (math.inf, -math.inf):
            return "null"
        if v == 0:
            return "0"
        return number_to_string(v)

    def value(self, v: Any, key: str, indent: str) -> str | None:
        if not isinstance(v, _PRIMITIVES):
            to_json = getattr(v, "toJSON", None)
            if callable(to_json):
                v = to_json(key)
        return self.plain(v, indent)

    def plain(self, v: Any, indent: str) -> str | None:
        if v is None:
            return "null"
        if v is True:
            return "true"
        if v is False:
            return "false"
        if isinstance(v, str):
            return quote(v)
        if isinstance(v, (int, float)):
            return self.number(v)
        if v is UNDEFINED:
            return None
        if isinstance(v, dict):
            return self.obj(v, indent)
        if isinstance(v, (list, tuple)):
            return self.arr(v, indent)
        if isinstance(v, datetime):
            return quote(_iso(v))
        raise TypeError(f"Object of type {type(v).__name__} is not JSON serializable")

    def enter(self, v: Any) -> None:
        if id(v) in self.stack:
            raise TypeError("Converting circular structure to JSON")
        self.stack.append(id(v))

    def obj(self, d: dict[Any, Any], indent: str) -> str:
        self.enter(d)
        inner = indent + self.gap
        merged: dict[str, Any] = {}
        for k, val in d.items():
            merged[_key_string(k)] = val
        keys = list(merged)
        idx = [k for k in keys if _is_index(k)]
        if idx:
            idx.sort(key=int)
            keys = idx + [k for k in keys if not _is_index(k)]
        parts: list[str] = []
        colon = ": " if self.gap else ":"
        for k in keys:
            s = self.value(merged[k], k, inner)
            if s is not None:
                parts.append(quote(k) + colon + s)
        self.stack.pop()
        if not parts:
            return "{}"
        if not self.gap:
            return "{" + ",".join(parts) + "}"
        sep = ",\n" + inner
        return "{\n" + inner + sep.join(parts) + "\n" + indent + "}"

    def arr(self, a: list[Any] | tuple[Any, ...], indent: str) -> str:
        self.enter(a)
        inner = indent + self.gap
        parts = []
        for i, item in enumerate(a):
            s = self.value(item, str(i), inner)
            parts.append("null" if s is None else s)
        self.stack.pop()
        if not parts:
            return "[]"
        if not self.gap:
            return "[" + ",".join(parts) + "]"
        sep = ",\n" + inner
        return "[\n" + inner + sep.join(parts) + "\n" + indent + "]"


def _gap(indent: int | float | str | None) -> str:
    if indent is None:
        return ""
    if isinstance(indent, str):
        return indent[:10]
    if isinstance(indent, bool) or not isinstance(indent, (int, float)):
        raise TypeError("indent must be None, an int or a str")
    if indent != indent or indent < 1:
        return ""
    return " " * int(min(10, indent))


def json_stringify(
    value: Any,
    indent: int | float | str | None = None,
    *,
    int_overflow: Literal["error", "float"] = "error",
) -> str | None:
    """JSON.stringify(value, null, indent). Returns None when JS would return undefined."""
    if int_overflow not in ("error", "float"):
        raise ValueError("int_overflow must be 'error' or 'float'")
    return _Writer(_gap(indent), int_overflow).value(value, "", "")
