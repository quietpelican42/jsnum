"""Decoding of the tagged corpora written by tests/gen/*.js into Python values."""

from __future__ import annotations

import struct
from typing import Any


def double(hex_bits: str) -> float:
    return float(struct.unpack(">d", bytes.fromhex(hex_bits))[0])


def natural(x: float) -> int | float:
    """The type a Python program would usually hold: int when integral and safe."""
    if x == x and abs(x) <= 2**53 and x == int(x) and str(x) != "-0.0":
        return int(x)
    return x


def decode(node: Any, undefined: Any, floats: bool = False, typed: bool = False) -> Any:
    """Tagged JSON -> Python. `floats` holds every integer as a float; `typed` holds {"i": n} as float."""
    if node is None or isinstance(node, (str, bool)):
        return node
    if isinstance(node, int):
        return float(node) if floats else node
    if isinstance(node, list):
        return [decode(n, undefined, floats, typed) for n in node]
    if "i" in node:
        return float(node["i"]) if typed or floats else int(node["i"])
    if "f" in node:
        return double(node["f"])
    if "u" in node:
        return undefined
    return {k: decode(v, undefined, floats, typed) for k, v in node["o"]}


def has_undefined(node: Any) -> bool:
    if isinstance(node, list):
        return any(has_undefined(n) for n in node)
    if isinstance(node, dict):
        if "u" in node:
            return True
        if "o" in node:
            return any(has_undefined(v) for _, v in node["o"])
    return False
