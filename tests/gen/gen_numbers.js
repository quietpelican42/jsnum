'use strict';
// usage: node gen_numbers.js <count> <seed>  ->  JSON array of rows on stdout
// row: {x: hex bits, s: String(x), r: [radix, s], fx: [d, s|"RangeError"], pr: [p, ...],
//       ex: [e, ...], ex0: toExponential(), rd: Math.round as string}
const { makeRng, toHex, fromHex, bitsDouble } = require('./prng');
const count = Number(process.argv[2] || 60000);
const rng = makeRng(Number(process.argv[3] || 1));
const str = (v) => (Object.is(v, -0) ? '-0' : String(v));
const attempt = (f) => { try { return f(); } catch (e) { return e.name; } };

const edges = [
  0, -0, 1, -1, 0.5, -0.5, 1.5, 2.5, -1.5, -2.5, 0.49999999999999994, 4503599627370495.5,
  4503599627370497, 9007199254740991, 9007199254740992, 9007199254740993, -9007199254740992,
  1e21, 1e20, 9.999999999999999e20, 999999999999999900000, 1e-6, 1e-7, 9.9e-7, 1.5e-7, 123456789e-15,
  5e-324, 1e-323, 2.2250738585072014e-308, 2.225073858507201e-308, 1.7976931348623157e308,
  1.7976931348623155e308, NaN, Infinity, -Infinity, 0.1, 0.2, 0.30000000000000004, 1.005, 1.255,
  8.345, 10.235, 1.45, 2.675, 0.000001, 0.0000001, 1e100, 1e-100, 255, 4294967295, 4294967296,
  123.456, 0.000123, 100, 1000000, 12345678901234567890, 1.25, 0.125, 0.375, 3.5, 99.995, 0.045,
  5e-7, 0.0000005, 1e23, 1e22, 2 ** 64, 2 ** 70, 2 ** -30, 2 ** -1074, 0.1 + 0.7, 1 / 3, 2 / 3, Math.PI, Math.E,
];
const rows = [];
function add(x) {
  const row = { x: toHex(x), s: String(x) };
  row.r = [];
  for (const radix of [2, 16, 36, 3 + rng.int(33)]) row.r.push([radix, attempt(() => x.toString(radix))]);
  const d = rng.f() < 0.9 ? rng.int(21) : rng.int(103);
  row.fx = [d, attempt(() => x.toFixed(d))];
  const p = rng.f() < 0.9 ? 1 + rng.int(21) : rng.int(103);
  row.pr = [p, attempt(() => x.toPrecision(p))];
  const e = rng.f() < 0.9 ? rng.int(21) : rng.int(103);
  row.ex = [e, attempt(() => x.toExponential(e))];
  row.ex0 = x.toExponential();
  row.rd = str(Math.round(x));
  rows.push(row);
}
edges.forEach(add);
for (const x of edges) if (Number.isFinite(x)) { add(-x); add(x * 10); add(x / 10); }
let i = 0;
while (rows.length < count) {
  const k = i++ % 10;
  let x;
  if (k <= 3) x = bitsDouble(rng);
  else if (k === 4) x = (rng.f() - 0.5) * Math.pow(10, rng.int(44) - 22);
  else if (k === 5) x = Math.round(rng.f() * 1e7) / Math.pow(10, rng.int(9));
  else if (k === 6) x = rng.int(2000) / 8 + (rng.int(3) - 1) * 0.5; // ties in binary
  else if (k === 7) x = Math.floor(rng.f() * 2 ** 53) * Math.pow(2, rng.int(40) - 20);
  else if (k === 8) x = fromHex(toHex(Math.pow(10, rng.int(60) - 30)).slice(0, 15) + rng.int(16).toString(16)); // near powers of 10
  else x = rng.int(200000) / 100 * (rng.f() < 0.1 ? -1 : 1); // prices
  add(x);
}
process.stdout.write(JSON.stringify(rows));
