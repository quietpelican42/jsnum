'use strict';
// usage: node gen_realistic.js <numbers> <docs> <seed>  ->  {numbers: [...], docs: [...]}
// Numbers and JSON documents typical of API payloads: prices, IDs, timestamps, ratios, coordinates.
const { makeRng, toHex } = require('../tests/gen/prng');
const nNum = Number(process.argv[2] || 20000), nDoc = Number(process.argv[3] || 5000);
const rng = makeRng(Number(process.argv[4] || 7));

const gens = {
  price: () => rng.int(2000000) / 100,
  price_x_qty: () => (rng.int(200000) / 100) * (1 + rng.int(12)),
  price_tax: () => (rng.int(200000) / 100) * 1.0825,
  price_sum: () => rng.int(50000) / 100 + rng.int(50000) / 100 + rng.int(50000) / 100,
  int_small: () => rng.int(100000),
  id_int: () => rng.int(2 ** 31),
  id_snowflake: () => Math.floor(rng.f() * 9007199254740991),
  ts_ms: () => 1.6e12 + rng.int(2e11),
  ts_s_frac: () => (1.6e12 + rng.int(2e11)) / 1000,
  ts_s: () => 1.6e9 + rng.int(2e8),
  duration_ms: () => rng.f() * 5000,
  ratio: () => (1 + rng.int(999)) / (1 + rng.int(1000)),
  pct_1dp: () => rng.int(1001) / 10,
  pct_4dp: () => rng.int(1000001) / 10000,
  latlon: () => (rng.f() - 0.5) * 360,
  latlon6: () => Math.round((rng.f() - 0.5) * 360 * 1e6) / 1e6,
  neg_delta: () => -rng.int(100000) / 100,
  tiny_epsilon: () => Math.pow(10, -(5 + rng.int(6))) * (1 + rng.int(9)),
  huge_wei: () => (1 + rng.int(999)) * Math.pow(10, 15 + rng.int(9)),
  zero: () => 0,
};
const weights = { price: 14, price_x_qty: 8, price_tax: 6, price_sum: 6, int_small: 10, id_int: 6, id_snowflake: 3, ts_ms: 8, ts_s_frac: 4, ts_s: 4,
  duration_ms: 5, ratio: 7, pct_1dp: 3, pct_4dp: 3, latlon: 3, latlon6: 3, neg_delta: 3, tiny_epsilon: 1, huge_wei: 1, zero: 1 };
const bag = []; for (const [k, w] of Object.entries(weights)) for (let i = 0; i < w; i++) bag.push(k);

const numbers = [];
for (let i = 0; i < nNum; i++) { const cat = rng.pick(bag); const x = gens[cat](); numbers.push({ x: toHex(x), s: String(x), c: cat }); }

const names = ['Alice', 'Bob', 'Zoë', 'Renée', 'Łukasz', '李雷', 'O\'Brien', 'Anne-Marie', 'Nguyen', 'Müller', 'Søren', 'Ana María', '田中', 'D"Arcy'];
const words = ['alpha', 'beta', 'order', 'invoice', 'refund', 'pending', 'shipped', 'unit test', 'promo/2026', 'café ☕', 'ok 👍', 'line1\nline2', 'tab\there', 'a\\b', '<b>bold</b>', 'x&y'];
const tagNum = (x) => (Number.isInteger(x) && Math.abs(x) <= 2 ** 53 && !Object.is(x, -0) ? x : { f: toHex(x) });
// Integral values of fractional-type fields (prices, ratios, coordinates) are tagged {i: n}: a Python program
// computing them would hold a float (20.0), one that read them from JSON would hold an int (20).
const FLOATY = new Set(['price', 'price_x_qty', 'price_tax', 'price_sum', 'ratio', 'pct_1dp', 'pct_4dp', 'latlon', 'latlon6', 'duration_ms', 'tiny_epsilon', 'huge_wei']);
const N = (cat) => { const x = gens[cat](); return FLOATY.has(cat) && Number.isInteger(x) && Math.abs(x) <= 2 ** 53 ? { i: x } : tagNum(x); };
const iso = () => new Date(1.6e12 + rng.int(2e11)).toISOString();
function item() {
  return { o: [['sku', 'SKU-' + rng.int(99999)], ['name', rng.pick(words)], ['qty', 1 + rng.int(9)], ['unit_price', N('price')], ['total', N('price_x_qty')], ['discount', N('pct_1dp')], ['tags', Array.from({ length: rng.int(3) }, () => rng.pick(words))]] };
}
function doc() {
  const pairs = [['id', N('id_int')], ['uuid', [rng.u32(), rng.u32(), rng.u32(), rng.u32()].map((v) => v.toString(16).padStart(8, '0')).join('')],
    ['name', rng.pick(names)], ['active', rng.f() < 0.8], ['created_at', iso()], ['updated_ms', N('ts_ms')], ['balance', N('price')],
    ['score', N('ratio')], ['loc', { o: [['lat', N('latlon6')], ['lon', N('latlon6')]] }], ['note', rng.f() < 0.3 ? null : rng.pick(words)],
    ['items', Array.from({ length: rng.int(5) }, item)]];
  let plain = true;
  if (rng.f() < 0.1) { plain = false; pairs.push(['metrics', { o: [['p50', N('duration_ms')], ['p99', N('duration_ms')], ['err_rate', N('pct_4dp')], ['eps', N('tiny_epsilon')]] }]); }
  if (rng.f() < 0.1) { plain = false; pairs.push(['by_id', { o: Array.from({ length: 1 + rng.int(4) }, () => [String(1 + rng.int(99999)), N('price')]).filter((p, i, a) => a.findIndex((q) => q[0] === p[0]) === i) }]); }
  if (rng.f() < 0.05) { plain = false; pairs.push(['wei', N('huge_wei')]); }
  return { doc: { o: pairs }, plain };
}
function build(a) {
  if (a === null || typeof a !== 'object') return a;
  if (Array.isArray(a)) return a.map(build);
  if ('i' in a) return a.i;
  if ('f' in a) { const b = new DataView(new ArrayBuffer(8)); b.setBigUint64(0, BigInt('0x' + a.f)); return b.getFloat64(0); }
  const o = {}; for (const [k, v] of a.o) Object.defineProperty(o, k, { value: build(v), enumerable: true, writable: true, configurable: true }); return o;
}
const docs = [];
for (let i = 0; i < nDoc; i++) { const { doc: a, plain } = doc(); const v = build(a); docs.push({ v: a, p: plain, e: JSON.stringify(v), e2: JSON.stringify(v, null, 2) }); }
process.stdout.write(JSON.stringify({ numbers, docs }));
