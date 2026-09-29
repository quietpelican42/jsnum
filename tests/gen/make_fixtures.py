"""Regenerate the compact gzip fixtures in tests/fixtures using Node (deterministic seeds)."""

from __future__ import annotations

import gzip
import subprocess
from pathlib import Path

HERE = Path(__file__).resolve().parent
OUT = HERE.parent / "fixtures"

SPECS = [
    ("numbers", "gen_numbers.js", "2500", "101"),
    ("parse", "gen_parse.js", "2500", "102"),
    ("json", "gen_json.js", "1500", "103"),
]

if __name__ == "__main__":
    OUT.mkdir(exist_ok=True)
    for name, script, count, seed in SPECS:
        data = subprocess.run(["node", str(HERE / script), count, seed], check=True, capture_output=True, timeout=300).stdout
        (OUT / f"{name}.json.gz").write_bytes(gzip.compress(data, 9, mtime=0))
        print(name, len(data), "bytes")
