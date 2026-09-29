# jsnum

Exact ECMAScript number formatting, number parsing and `JSON.stringify` for Python, in pure Python with no dependencies.

```python
from jsnum import json_stringify, number_to_string, parse_int, to_fixed, UNDEFINED

number_to_string(1e-7)            # '1e-7'      (str(1e-7) is '1e-07')
number_to_string(100.0)           # '100'       (str(100.0) is '100.0')
to_fixed(1.005, 2)                # '1.00'
parse_int("  0x1F px")            # 31.0
json_stringify({"b": 1, "2": 2, "a": [1.0, float("nan"), UNDEFINED]})
# '{"2":2,"b":1,"a":[1,null,null]}'
```

## Why

Python code that has to reproduce bytes produced by JavaScript (request signatures, content hashes, cache keys) breaks on small differences in how the two languages print numbers and order object keys.

- `str(float)` and `json.dumps` print `1e-07`, `1e+16` and `100.0` where JavaScript prints `1e-7`, `10000000000000000` and `100`.
- `JSON.stringify` puts integer-like keys first in ascending order. Python dicts keep insertion order.
- `JSON.stringify` writes `-0` as `0`, `NaN` and `±Infinity` as `null`, and escapes lone surrogates as `\udXXX`.
- `float()` and `int()` are not `parseFloat`, `parseInt` or `Number()`.
- `toFixed`, `toPrecision` and `toExponential` round the exact decimal value of the double, with ties going up.

Hand-rolled copies of these helpers exist in yt-dlp (`js_number_to_string`, which leaves the radix-10 case as `# TODO: implement special cases`), cv-cat/KuaiShou-Spider (`utils/sign/jsval.py`, a port of `Number::toString` because `str(1.0)` and `json.dumps` break signatures) and cv-cat/DouYin_Spider (`_js_json`, "Match JSON.stringify" through `json.dumps`).

Measured: `python bench/incumbents.py realistic.json edge_numbers.json edge_json.json edge_parse.json` against output recorded from Node 24.20 (arm64). Corpora come from `bench/gen_realistic.js` and `tests/gen/gen_*.js`. Exact match with Node, per case:

| Task | Corpus | Incumbents | jsnum |
| --- | --- | --- | --- |
| Number to string | realistic, ints held as int (20,000) | `str` 98.8%, orjson 99.4%, rfc8785 100% | 100% |
| Number to string | realistic, price/ratio/coordinate fields held as float | `str` 98.1%, orjson 98.7%, rfc8785 100% | 100% |
| Number to string | realistic, every number held as float | `str` 65.3%, orjson 65.9%, rfc8785 100% | 100% |
| Number to string | edge (49,990) | `str` 91.2%, orjson 93.3%, rfc8785 100% | 100% |
| `JSON.stringify` compact | realistic documents (5,000) | `json.dumps(ensure_ascii=False)` 84.6%, orjson 89.8%, ujson 88.6%, msgspec 87.1%, rapidjson 84.6%, simplejson 84.6%, domonic 21.5%, rfc8785 0% | 100% |
| `JSON.stringify` compact | realistic, plain subset (3,854) | `json.dumps(ensure_ascii=False)`, orjson, ujson, msgspec, rapidjson, simplejson all 100%; domonic 25.6% | 100% |
| `JSON.stringify` compact | realistic, price/ratio/coordinate fields held as float | orjson 67.2%, `json.dumps(ensure_ascii=False)` 63.3% | 100% |
| `JSON.stringify` indent 2 | realistic documents | orjson 89.8%, `json.dumps(ensure_ascii=False)` 84.6% | 100% |
| `JSON.stringify` compact | edge documents (10,801) | orjson 87.5%, `json.dumps(ensure_ascii=False)` 84.8%, msgspec 82.3%, rfc8785 86.9%, domonic 73.2% | 100% |
| `toFixed` / `toPrecision` / `toExponential` | edge (about 50,000 each) | `format()` 79.4 / 60.1 / 60.6%, domonic 66.4 / 99.7 / 99.7% | 100% |
| `toString(radix)` | edge (about 200,000) | domonic 24.2% | 100% |
| `parseFloat` / `parseInt` / `Number()` | edge (15,000 strings) | `float()`/`int()` 28.9 / 6.2 / 28.8%, domonic 95.4 / 96.8 / 51.9% | 100% |

How to read the JSON rows:

- The realistic corpus is 5,000 order-like documents (ids, ISO timestamps, prices, ratios, coordinates, unicode names, nested items). About 23% of them also carry a tail that real payloads occasionally have: a map keyed by numeric ids (10%), a rate below 1e-6 (10%) or an amount of 1e16 or more (5%). Those percentages are the corpus author's choice. The failure rate of the incumbents scales with them.
- On the plain subset, which has none of those, `json.dumps(ensure_ascii=False, separators=(",", ":"))` is already exact as long as integral values are held as `int`. The gap is the tail, and integral values held as `float` (`20.0`), which break every incumbent.
- Incumbents were given the most favorable configuration (no ASCII escaping, no spaces, dict keys in insertion order). `json.dumps` with default arguments scores 21.6% on the realistic documents.
- domonic 1.8.5 is a DOM toolkit that includes `Number.toString`, `toFixed`, `JSON.stringify`, `parseInt` and `parseFloat` wrappers. Its `JSON.stringify` uses `json.dumps` with default ASCII escaping, and its `toString(radix)` drops the fractional part.

## Installation

```sh
pip install jsnum
```

Python 3.11 or newer. No runtime dependencies.

## Usage

### Numbers to strings

```python
from jsnum import number_to_string, to_exponential, to_fixed, to_precision

number_to_string(255.5, 16)    # 'ff.8'
number_to_string(0.1, 3)       # '0.0022002200220022002200220022002201'
to_fixed(2.5)                  # '3'   (Python round(2.5) is 2)
to_precision(123.456, 4)       # '123.5'
to_exponential(0.00015, 1)     # '1.5e-4'
```

### Parsing

```python
from jsnum import math_round, parse_float, parse_int, to_number

parse_float("﻿3.14abc")   # 3.14
parse_int("9007199254740993")  # 9007199254740992.0
to_number("")                  # 0.0
to_number("0b101")             # 5.0
math_round(-0.4)               # -0.0
```

### JSON

```python
from jsnum import json_stringify

json_stringify({"a": 1, "b": [1, 2]}, indent=2)
json_stringify(2**60, int_overflow="float")
```

Objects with a `toJSON(key)` method are serialized through it. A timezone-aware `datetime` becomes `Date.prototype.toJSON` output (`2024-01-02T03:04:05.678Z`, truncated to milliseconds).

## Reference

| Function | Returns | Description |
| --- | --- | --- |
| `number_to_string(x, radix=10)` | `str` | `Number::toString` and `Number.prototype.toString(radix)`. `radix` is 2 to 36, otherwise `ValueError`. |
| `to_fixed(x, fraction_digits=0)` | `str` | `toFixed`, 0 to 100 digits, exact decimal rounding, ties up. `ValueError` out of range (checked before NaN, as in JS). |
| `to_precision(x, precision=None)` | `str` | `toPrecision`, 1 to 100. `None` behaves like `number_to_string`. |
| `to_exponential(x, fraction_digits=None)` | `str` | `toExponential`, 0 to 100. `None` uses as many digits as needed. |
| `parse_float(s)` | `float` | `parseFloat`. NaN when there is no numeric prefix. |
| `parse_int(s, radix=None)` | `float` | `parseInt`. `radix` goes through `ToInt32`. NaN without digits, `-0.0` for `"-0"`. |
| `to_number(s)` | `float` | `Number(string)`: empty is 0, `0x`/`0o`/`0b`, `Infinity`, whole-string match. |
| `math_round(x)` | `float` | `Math.round`: half toward +Infinity, `-0.0` for inputs in [-0.5, 0). |
| `json_stringify(value, indent=None, *, int_overflow="error")` | `str` or `None` | `JSON.stringify(value, null, indent)`. `None` is returned where JS returns `undefined`. |
| `UNDEFINED` | sentinel | Omitted from objects, `null` in arrays, `None` result at top level. |

`json_stringify` options:

| Name | Type | Default | Description |
| --- | --- | --- | --- |
| `indent` | `int`, `float`, `str` or `None` | `None` | Number: spaces, clamped to 10, below 1 means compact. String: first 10 characters. |
| `int_overflow` | `"error"` or `"float"` | `"error"` | An `int` beyond +/-2**53 raises `TypeError`, or is converted with `float()` and printed as a JS number. |

Type mapping for `json_stringify`:

| Python | JSON |
| --- | --- |
| `None` | `null` |
| `bool` (checked before `int`) | `true` / `false` |
| `int` within +/-2**53 | integer digits |
| `float` | `Number::toString`; `nan`, `inf`, `-inf` become `null`; `-0.0` becomes `0` |
| `str` | quoted, lone surrogates as `\udXXX`, a surrogate pair held as two code points is joined |
| `list`, `tuple` | array |
| `dict` | object. Integer-like keys (canonical array indexes below 2**32-1) first in ascending order, then insertion order. |
| dict keys | `str` as is; `int` and `float` via `number_to_string`; `bool` as `true`/`false`; `None` as `null`. Keys that collide after conversion keep the first position and the last value. Other key types raise `TypeError`. |
| `UNDEFINED` | omitted, `null` in arrays |
| object with `toJSON` | result of `toJSON(key)` |
| aware `datetime` | ISO string in UTC with milliseconds; naive raises `TypeError` |
| anything else, circular references | `TypeError` |

All functions that return a JS number return `float`, so NaN, Infinity and `-0.0` are representable. Inputs to the formatting functions may be `int` or `float`.

## How it works

- Shortest round-trip digits come from `repr(float)`, which produces the digits the spec asks for. They are laid out with the `Number::toString` rules (thresholds 1e21 and 1e-6).
- `to_fixed`, `to_precision` and `to_exponential` use `fractions.Fraction` on the exact value of the double, so a tie is a real tie and `1.005` (stored as 1.00499999999999989...) gives `1.00`.
- `number_to_string` for a radix other than 10 is a port of V8's `DoubleToRadixCString` (the same algorithm yt-dlp mirrors). ECMA-262 leaves non-decimal output implementation-approximated, so any output is conformant. V8's is not exact: for `|x| < 2**53` the printed value converts back to the same double in 85.5% of 144,202 corpus cases (measured with `Fraction`), because the digit loop multiplies in floating point. jsnum matches V8 digit for digit (100% of about 200,000 radix cases), not the mathematically shortest string. Digits below double precision in large integers are zero-filled the way V8 does it.
- `parse_int` gets radix 10 through `float()` on the digit run and radixes 2, 4, 8, 16 and 32 through exact `int()`, both correctly rounded like V8. Other radixes reproduce V8's 32-bit chunk accumulation.
- `json_stringify` is a small recursive writer. Escaping uses one regular expression.

## Limitations

- `parse_int` with a radix other than 2, 4, 8, 10, 16, 32 and more than about 11 digits is an implementation-defined approximation in the spec. V8 accumulates 32-bit chunks in double arithmetic, compiled with fused multiply-add on arm64. jsnum reproduces that with a single-rounding multiply-add. On the 45,000 parse-radix checks in the differential, 139 (0.3%) differ from Node by a few ulps in that region. The test suite tolerates a relative difference of 1e-13 there and reports nothing else. Results on x86-64 Node were not measured.
- Not implemented: `JSON.parse`, `replacer` and `space` arguments beyond `indent`, `BigInt`, `Date` parsing, locale-aware formatting, `Number.prototype.toLocaleString`.
- `json_stringify` recurses, so nesting deeper than about 300 levels raises `RecursionError`.
- Only built-in `int`, `float`, `str`, `bool`, `None`, `list`, `tuple`, `dict` and aware `datetime` are known. `Decimal`, NumPy scalars, `set` and `bytes` raise `TypeError`; expose them through `toJSON`.
- `toJSON` is looked up on objects that are not built-in JSON types. A dict cannot carry one.
- Strings are Python `str`. JavaScript strings can hold arbitrary UTF-16; Python `str` with lone surrogates is supported, a surrogate pair split over two code points is joined.
- The differential covers the corpora generated by `tests/gen/*.js`. Behavior outside them (for example the full 32-bit range of `parseInt` radix values) follows the spec text.

## Compatibility

Run here: Python 3.14.7 on macOS arm64 against Node v24.20.0 (V8 as shipped in that release). Python 3.11, 3.12 and 3.13 are covered only by the CI matrix and were not run locally. The code uses no 3.12+ features. Node 22 or other V8 versions were not run.

## Development

```sh
python -m venv .venv && .venv/bin/pip install -e '.[dev]'
.venv/bin/python -m pytest -q
.venv/bin/python -m mypy --strict src tests bench
```

`tests/test_fixtures.py` replays compact recorded fixtures (`tests/fixtures/*.json.gz`, 2,500 doubles, 2,500 strings, 1,500 JSON documents from Node 24) and needs no Node. `tests/test_differential.py` regenerates the full corpora with Node (60,000 doubles, 15,000 strings, 12,000 JSON documents, seeded, deterministic) and compares every result; it is skipped with an explicit message when `node` is not on `PATH` (set `JSNUM_NODE` to override, `JSNUM_DIFF_SCALE` to scale). Regenerate the fixtures with `python tests/gen/make_fixtures.py`.

To reproduce the incumbent table, install the packages named in `bench/requirements.txt` in a separate environment and run `bench/incumbents.py` as shown above.

## License

MIT. See [LICENSE](LICENSE).
