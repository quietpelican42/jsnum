"""ECMAScript WhiteSpace and LineTerminator code points (not Python's str.isspace)."""

from __future__ import annotations

WS_CHARS = (
    "\t\n\v\f\r              "
    "    　﻿"
)


def trim_start(s: str) -> str:
    return s.lstrip(WS_CHARS)


def trim(s: str) -> str:
    return s.strip(WS_CHARS)
