"""Replays committed fixtures (recorded from Node) without needing Node."""

from __future__ import annotations

import gzip
import json
from pathlib import Path
from typing import Any

import pytest

from checks import check_json_row, check_number_row, check_parse_row

FIXTURES = Path(__file__).parent / "fixtures"


def load(name: str) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = json.loads(gzip.decompress((FIXTURES / f"{name}.json.gz").read_bytes()))
    return rows


def test_numbers_fixture() -> None:
    rows = load("numbers")
    bad = [b for r in rows for b in check_number_row(r)]
    assert len(rows) >= 2500
    assert not bad, bad[:10]


def test_parse_fixture() -> None:
    rows = load("parse")
    bad = [b for r in rows for b in check_parse_row(r)]
    assert len(rows) >= 2500
    assert not bad, bad[:10]


def test_json_fixture() -> None:
    rows = load("json")
    bad = [b for i, r in enumerate(rows) for b in check_json_row(i, r)]
    assert len(rows) >= 1500
    assert not bad, bad[:10]


@pytest.mark.parametrize("name", ["numbers", "parse", "json"])
def test_fixture_files_exist(name: str) -> None:
    assert (FIXTURES / f"{name}.json.gz").stat().st_size > 1000
