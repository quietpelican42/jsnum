"""Measure incumbent Python libraries against Node on two corpora.

usage: python bench/incumbents.py <realistic.json> <edge_numbers.json> <edge_json.json> <edge_parse.json>

Corpora come from bench/gen_realistic.js and tests/gen/gen_{numbers,json,parse}.js.
Incumbents are installed separately (pip install -r bench/requirements.txt).
"""

from __future__ import annotations

import json
import math
import sys
from pathlib import Path
from typing import Any, Callable

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tests"))
from corpus import decode, double, has_undefined, natural  # noqa: E402

FLOATY = {"price", "price_x_qty", "price_tax", "price_sum", "ratio", "pct_1dp", "pct_4dp", "latlon", "latlon6", "duration_ms", "tiny_epsilon", "huge_wei"}


def pct(ok: int, n: int) -> str:
    return f"{ok}/{n} = {100 * ok / n:.1f}%"


def run(f: Callable[[Any], str], cases: list[tuple[Any, str]]) -> str:
    ok = 0
    for v, e in cases:
        try:
            ok += f(v) == e
        except Exception:
            pass
    return pct(ok, len(cases))


def number_impls() -> dict[str, Callable[[Any], str]]:
    impls: dict[str, Callable[[Any], str]] = {"str()": str, "str(float())": lambda v: str(float(v))}
    try:
        import rfc8785

        impls["rfc8785.dumps"] = lambda v: rfc8785.dumps(float(v)).decode()
    except ImportError:
        pass
    try:
        from domonic.javascript import Number

        impls["domonic Number.toString"] = lambda v: Number(v).toString()
    except ImportError:
        pass
    try:
        import orjson

        impls["orjson"] = lambda v: orjson.dumps(v).decode()
    except ImportError:
        pass
    try:
        import jsnum

        impls["jsnum.number_to_string"] = jsnum.number_to_string
    except ImportError:
        pass
    return impls


def json_impls(indent: int | None) -> dict[str, Callable[[Any], str]]:
    impls: dict[str, Callable[[Any], str]] = {}
    seps = (",", ":") if indent is None else None
    impls["json.dumps(ensure_ascii=False)"] = lambda v: json.dumps(v, ensure_ascii=False, separators=seps, indent=indent)
    impls["json.dumps (defaults)"] = lambda v: json.dumps(v, separators=seps, indent=indent)
    try:
        import orjson

        opt = orjson.OPT_INDENT_2 if indent else 0
        impls["orjson"] = lambda v: orjson.dumps(v, option=opt).decode()
    except ImportError:
        pass
    if indent is None:
        try:
            import ujson

            impls["ujson"] = lambda v: ujson.dumps(v, ensure_ascii=False, escape_forward_slashes=False)
        except ImportError:
            pass
        try:
            import msgspec

            impls["msgspec"] = lambda v: msgspec.json.encode(v).decode()
        except ImportError:
            pass
        try:
            import rapidjson

            impls["python-rapidjson"] = lambda v: rapidjson.dumps(v, ensure_ascii=False)
        except ImportError:
            pass
        try:
            import simplejson

            impls["simplejson"] = lambda v: simplejson.dumps(v, ensure_ascii=False, separators=(",", ":"))
        except ImportError:
            pass
        try:
            import rfc8785

            impls["rfc8785.dumps (sorts keys)"] = lambda v: rfc8785.dumps(v).decode()
        except ImportError:
            pass
    try:
        from domonic.javascript import JSON

        impls["domonic JSON.stringify"] = lambda v: JSON.stringify(v, None, indent) if indent else JSON.stringify(v)
    except ImportError:
        pass
    try:
        import jsnum

        impls["jsnum.json_stringify"] = lambda v: str(jsnum.json_stringify(v, indent=indent))
    except ImportError:
        pass
    return impls


def table(title: str, impls: dict[str, Callable[[Any], str]], cases: list[tuple[Any, str]]) -> None:
    print(f"\n{title} ({len(cases)} cases)")
    for name, f in impls.items():
        print(f"  {name:32s} {run(f, cases)}")


def same_number(v: Any, expected: str) -> bool:
    """Value equality including NaN and the sign of zero; `expected` is a JS String(number) or '-0'."""
    got, want = float(v), float(expected)
    if got != got or want != want:
        return got != got and want != want
    return got == want and math.copysign(1, got) == math.copysign(1, want)


def parse_impls() -> dict[str, dict[str, Callable[[str], Any]]]:
    out: dict[str, dict[str, Callable[[str], Any]]] = {
        "python float()/int()": {"pf": float, "pi": int, "n": float},
    }
    try:
        from domonic.javascript import Global

        out["domonic"] = {"pf": Global.parseFloat, "pi": Global.parseInt, "n": Global.parseFloat}
    except ImportError:
        pass
    try:
        import jsnum

        out["jsnum"] = {"pf": jsnum.parse_float, "pi": jsnum.parse_int, "n": jsnum.to_number}
    except ImportError:
        pass
    return out


def main() -> None:
    realistic = json.loads(Path(sys.argv[1]).read_text())
    edge_numbers = json.loads(Path(sys.argv[2]).read_text())
    edge_json = json.loads(Path(sys.argv[3]).read_text())

    for label, nums in (("realistic", realistic["numbers"]), ("edge", [r for r in edge_numbers if r["s"] not in ("NaN",)])):
        cases = [(natural(double(r["x"])), r["s"]) for r in nums]
        table(f"Number toString, {label}, natural types (int when integral)", number_impls(), cases)
        if label == "realistic":
            floaty = [(double(r["x"]) if r["c"] in FLOATY else natural(double(r["x"])), r["s"]) for r in nums]
            table("Number toString, realistic, price/ratio/coordinate fields held as float", number_impls(), floaty)
        cases = [(double(r["x"]), r["s"]) for r in nums]
        table(f"Number toString, {label}, all floats", number_impls(), cases)

    docs = realistic["docs"]
    table("JSON.stringify compact, realistic", json_impls(None), [(decode(d["v"], None), d["e"]) for d in docs])
    plain = [d for d in docs if d["p"]]
    table("JSON.stringify compact, realistic, plain subset (no int-like-key map, no value < 1e-6 or >= 1e16)", json_impls(None), [(decode(d["v"], None), d["e"]) for d in plain])
    table("JSON.stringify compact, realistic, price/ratio/coordinate fields held as float", json_impls(None), [(decode(d["v"], None, False, True), d["e"]) for d in docs])
    table("JSON.stringify compact, realistic plain subset, price/ratio/coordinate fields held as float", json_impls(None), [(decode(d["v"], None, False, True), d["e"]) for d in plain])
    table("JSON.stringify indent=2, realistic", json_impls(2), [(decode(d["v"], None), d["e2"]) for d in docs])
    ok = [d for d in edge_json if not has_undefined(d["v"]) and d["ec"] is not None]
    table("JSON.stringify compact, edge", json_impls(None), [(decode(d["v"], None), d["ec"]) for d in ok])

    fmt_incumbents(edge_numbers)
    if len(sys.argv) > 4:
        rows = json.loads(Path(sys.argv[4]).read_text())
        print(f"\nparseFloat / parseInt / Number(), edge ({len(rows)} strings)")
        for name, fs in parse_impls().items():
            print(f"  {name:32s} " + ", ".join(f"{k} {pct(sum(1 for r in rows if _safe(fs[k], r['s'], r[k])), len(rows))}" for k in ("pf", "pi", "n")))


def fmt_incumbents(rows: list[dict[str, Any]]) -> None:
    print(f"\ntoFixed / toPrecision / toExponential, edge ({len(rows)} rows, one random digit count each)")
    from domonic.javascript import Number as DNumber

    def naive(kind: str) -> Callable[[float, int], str]:
        return lambda x, d: f"{x:.{d}{kind}}"

    impls: dict[str, dict[str, Callable[[float, int], str]]] = {
        "python format()": {"fx": naive("f"), "pr": lambda x, p: f"{x:.{p}g}", "ex": naive("e")},
        "domonic": {"fx": lambda x, d: DNumber(x).toFixed(d), "pr": lambda x, p: DNumber(x).toPrecision(p), "ex": lambda x, d: DNumber(x).toExponential(d)},
    }
    try:
        import jsnum

        impls["jsnum"] = {"fx": jsnum.to_fixed, "pr": jsnum.to_precision, "ex": jsnum.to_exponential}
    except ImportError:
        pass
    for name, fs in impls.items():
        res = []
        for k in ("fx", "pr", "ex"):
            ok = n = 0
            for r in rows:
                arg, exp = r[k]
                if exp in ("RangeError",) or exp in ("NaN", "Infinity", "-Infinity"):
                    continue
                n += 1
                try:
                    ok += fs[k](double(r["x"]), arg) == exp
                except Exception:
                    pass
            res.append(f"{k} {pct(ok, n)}")
        print(f"  {name:32s} " + ", ".join(res))
    print("\nNumber.toString(radix), edge (2, 16, 36 and one random radix per row)")
    radix_impls: dict[str, Callable[[float, int], str]] = {"domonic": lambda x, r: str(DNumber(x).toString(r))}
    for name, f in radix_impls.items():
        ok = n = 0
        for row in rows:
            x = double(row["x"])
            if x != x or abs(x) == float("inf"):
                continue
            for radix, exp in row["r"]:
                n += 1
                try:
                    ok += f(x, radix) == exp
                except Exception:
                    pass
        print(f"  {name:32s} {pct(ok, n)}")
    try:
        import jsnum

        ok = n = 0
        for row in rows:
            x = double(row["x"])
            for radix, exp in row["r"]:
                n += 1
                ok += jsnum.number_to_string(x, radix) == exp
        print(f"  {'jsnum':32s} {pct(ok, n)}")
    except ImportError:
        pass


def _safe(f: Callable[[str], Any], s: str, expected: str) -> bool:
    try:
        return same_number(f(s), expected)
    except Exception:
        return False


if __name__ == "__main__":
    main()
