"""Full differential run against a live Node. Skips loudly when node is not installed.

Set JSNUM_NODE to a node binary, and JSNUM_DIFF_SCALE (default 1.0) to shrink or grow the corpora.
Full scale: 60,000 doubles (x ~8 formatting calls each), 15,000 strings (x 6 calls), 12,000 JSON documents.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
from pathlib import Path
from typing import Any

import pytest

from checks import check_json_row, check_number_row, check_parse_row

GEN = Path(__file__).parent / "gen"
NODE = os.environ.get("JSNUM_NODE") or shutil.which("node")
SCALE = float(os.environ.get("JSNUM_DIFF_SCALE", "1.0"))

pytestmark = pytest.mark.skipif(
    NODE is None,
    reason="SKIPPED: node not found on PATH (set JSNUM_NODE). The differential against real Node did NOT run; only the recorded fixtures were checked.",
)


def corpus(script: str, count: int, seed: int) -> list[dict[str, Any]]:
    assert NODE is not None
    out = subprocess.run([NODE, str(GEN / script), str(int(count * SCALE)), str(seed)], check=True, capture_output=True, timeout=600).stdout
    rows: list[dict[str, Any]] = json.loads(out)
    return rows


def test_numbers_vs_node() -> None:
    rows = corpus("gen_numbers.js", 60000, 1)
    bad = [b for r in rows for b in check_number_row(r)]
    assert len(rows) >= 60000 * SCALE
    assert not bad, f"{len(bad)} mismatches of {len(rows)} rows: {bad[:10]}"


def test_parse_vs_node() -> None:
    rows = corpus("gen_parse.js", 15000, 2)
    bad = [b for r in rows for b in check_parse_row(r)]
    assert len(rows) >= 15000 * SCALE
    assert not bad, f"{len(bad)} mismatches of {len(rows)} rows: {bad[:10]}"


def test_json_vs_node() -> None:
    rows = corpus("gen_json.js", 12000, 3)
    bad = [b for i, r in enumerate(rows) for b in check_json_row(i, r)]
    assert len(rows) >= 12000 * SCALE
    assert not bad, f"{len(bad)} mismatches of {len(rows)} rows: {bad[:10]}"
