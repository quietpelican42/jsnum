'use strict';
// usage: node gen_json.js <count> <seed>
// row: {v: tagged value, i: indent (absent/number/string), e: JSON.stringify(v, null, i) or null (undefined), ec: compact JSON.stringify(v)}
// tagged: string -> string; int -> number; {"f": hex} -> other doubles (incl. -0, NaN, Infinity); {"u":1} -> undefined;
//         array -> array; {"o": [[key, tagged], ...]} -> object with that insertion order; true/false/null as themselves.
const { makeRng, toHex, fromHex, bitsDouble } = require('./prng');
const count = Number(process.argv[2] || 12000);
const rng = makeRng(Number(process.argv[3] || 3));

const strPool = ['', 'a', 'hello world', 'a"b', 'a\\b', '\n\t\r\b\f', '\u0000', '\u001f', '\u007f', '\u0080', 'é', '中文', '😀', '\ud83d', '\ude00', 'a\ud800b',
  '􏿿', '\udfff\ud800', '  ', '</script>', '<&>', '­', '﻿', '￾', '￿', '/', "'", 'ḱ', '😀\ud83d', 'x'.repeat(40), '\u0008\u000b'];
const keyPool = ['a', 'b', 'c', 'name', 'id', '0', '1', '2', '10', '9', '100', '01', '-1', '1.5', '4294967294', '4294967295', '4294967296', '9007199254740993',
  '', ' ', 'a b', 'é', '中', '😀', '\ud83d', 'a\ud800', '"', '\\', '\n', '__proto__', 'constructor', 'toString', '1e3', '00', '+1', 'Infinity', 'NaN', '99999999999', '3', '7', '42', 'z', 'Z', 'A'];
const nums = [0, -0, 1, -1, 1.5, -1.5, 1e21, 1e-7, 1e20, 123456789012345680000, 0.1, 1e-6, 5e-324, 1.7976931348623157e308, 2 ** 53, 2 ** 53 + 2, -(2 ** 53),
  100, 1e16, 3.14159, 12345.6789e10, NaN, Infinity, -Infinity, 0.30000000000000004, 255, 4294967296, -0.5];
const ints = () => rng.int(rng.pick([10, 1000, 1e6, 2 ** 31, 2 ** 53])) * (rng.f() < 0.2 ? -1 : 1);
function randStr() {
  const k = rng.int(4);
  if (k === 0) return rng.pick(strPool);
  if (k === 1) { let s = ''; const n = rng.int(12); for (let i = 0; i < n; i++) s += String.fromCharCode(rng.f() < .5 ? 32 + rng.int(95) : rng.int(0x10000)); return s; }
  if (k === 2) { let s = ''; const n = rng.int(10); for (let i = 0; i < n; i++) s += String.fromCodePoint(rng.pick([rng.int(0x80), rng.int(0x800), rng.int(0xd800), 0xe000 + rng.int(0x2000), 0x10000 + rng.int(0x100000)])); return s; }
  return rng.pick(strPool) + rng.pick(strPool);
}
function tagNum(x) {
  if (Number.isInteger(x) && Math.abs(x) <= 2 ** 53 && !Object.is(x, -0)) return x;
  return { f: toHex(x) };
}
function gen(d) {
  const t = rng.int(d > 3 ? 6 : 9);
  switch (t) {
    case 0: return randStr();
    case 1: return tagNum(rng.pick(nums));
    case 2: return rng.f() < .5;
    case 3: return null;
    case 4: return tagNum(ints());
    case 5: { const x = rng.f() < .5 ? bitsDouble(rng) : (rng.f() - .5) * Math.pow(10, rng.int(40) - 20); return tagNum(x); }
    case 6: return rng.f() < 0.1 ? { u: 1 } : Array.from({ length: rng.int(5) }, () => (rng.f() < 0.08 ? { u: 1 } : gen(d + 1)));
    default: {
      const n = rng.int(rng.f() < .1 ? 12 : 5); const used = new Set(); const pairs = [];
      for (let i = 0; i < n; i++) {
        const k = rng.f() < .85 ? rng.pick(keyPool) : randStr();
        if (used.has(k)) continue; used.add(k);
        pairs.push([k, rng.f() < 0.06 ? { u: 1 } : gen(d + 1)]);
      }
      return { o: pairs };
    }
  }
}
function build(a) {
  if (a === null || typeof a === 'boolean' || typeof a === 'string' || typeof a === 'number') return a;
  if (Array.isArray(a)) return a.map(build);
  if ('f' in a) return fromHex(a.f);
  if ('u' in a) return undefined;
  const o = {};
  for (const [k, v] of a.o) Object.defineProperty(o, k, { value: build(v), enumerable: true, writable: true, configurable: true });
  return o;
}
const indents = [undefined, undefined, undefined, 0, 1, 2, 3, 4, 8, 10, 11, 100, -1, '\t', '  ', '--', '', ' ', 'abcdefghijklmnop', 'éé', '😀x'];
const rows = [];
for (let i = 0; i < count; i++) {
  const a = gen(0);
  const ind = rng.pick(indents);
  const e = JSON.stringify(build(a), null, ind);
  const ec = JSON.stringify(build(a));
  const row = { v: a, e: e === undefined ? null : e, ec: ec === undefined ? null : ec };
  if (ind !== undefined) row.i = ind;
  rows.push(row);
}
process.stdout.write(JSON.stringify(rows));
