'use strict';
// usage: node gen_parse.js <count> <seed>
// row: {s, pf: parseFloat, pi: parseInt(s), pr: [radix, parseInt(s, radix)], n: Number(s)}  (results as strings, "-0" kept)
const { makeRng } = require('./prng');
const count = Number(process.argv[2] || 15000);
const rng = makeRng(Number(process.argv[3] || 2));
const t = (v) => (Object.is(v, -0) ? '-0' : String(v));
const WS = [0x9, 0xa, 0xb, 0xc, 0xd, 0x20, 0x85, 0xa0, 0x180e, 0x1680, 0x2000, 0x2003, 0x200a, 0x200b, 0x2028, 0x2029, 0x202f,
  0x205f, 0x3000, 0xfeff, 0x0, 0x1c, 0x1f, 0x2060, 0xffef].map((c) => String.fromCharCode(c));
const toks = ['', ' ', '+', '-', '0', '00', '1', '12', '007', '0x', '0X1F', '0b1', '0B101', '0o7', '0O17', '1e3', '1E-2', '1e+', 'e', 'E', '.', '.5', '5.', '5.e3',
  '1_0', '٣', '１', 'Infinity', '-Infinity', '+Infinity', 'infinity', 'Inf', 'NaN', 'px', 'abc', '1.5.5', '﻿', '9007199254740993', '1e400', '-0', '+0',
  '0.0000001', '123456789012345678901234567890', '%', '0x1g', 'n', '1n', 'ff', 'FF', 'zz', 'Z', '-0x10', '+0x10', '0x-1', '.e1', '1e', '1e1.5', 'é', '\ud83d', 'e5',
  '4294967295', '4294967296', '2147483648', '1.7976931348623157e308', '1.7976931348623159e308', '5e-324', '2e-324', '3e-324', '0.5', '00.5', '0.', '0.0', '1e-7'];
const digits = '0123456789abcdefghijklmnopqrstuvwxyz';
function randDigits(radix, n) { let s = ''; for (let i = 0; i < n; i++) s += digits[rng.int(radix)]; return s; }
const radices = [undefined, 0, 2, 3, 7, 8, 10, 16, 32, 36, 1, 37, -1, 4294967312, 4294967298, 2.9, NaN, Infinity];
const seen = new Set();
const rows = [];
function add(s) {
  if (seen.has(s)) return;
  seen.add(s);
  const pr = [];
  for (let i = 0; i < 3; i++) {
    const r = rng.pick(radices);
    pr.push([r === undefined ? null : (typeof r === 'number' && !Number.isFinite(r) ? String(r) : r), t(parseInt(s, r))]);
  }
  const row = { s, pf: t(parseFloat(s)), pi: t(parseInt(s)), pr, n: t(Number(s)) };
  rows.push(row);
}
while (rows.length < count) {
  const k = rng.int(10);
  let s = '';
  if (k <= 3) { const n = 1 + rng.int(4); for (let j = 0; j < n; j++) s += rng.pick(toks); }
  else if (k === 4) { s = rng.pick(WS) + rng.pick(WS) + (rng.f() < 0.5 ? '' : rng.pick(['1', '-2', '0x1f', '3.5', 'Infinity'])) + rng.pick(WS); }
  else if (k === 5) { const r = 2 + rng.int(35); s = (rng.f() < .2 ? '-' : '') + (r === 16 && rng.f() < .5 ? '0x' : '') + randDigits(r, 1 + rng.int(rng.f() < .5 ? 12 : 90)) + (rng.f() < .3 ? rng.pick(['.', 'g', ' ', '_', 'z']) + randDigits(r, 3) : ''); }
  else if (k === 6) { s = (rng.f() < .5 ? '' : rng.pick(['+', '-'])) + randDigits(10, 1 + rng.int(40)) + (rng.f() < .5 ? '.' + randDigits(10, rng.int(25)) : '') + (rng.f() < .5 ? rng.pick(['e', 'E']) + rng.pick(['', '+', '-']) + randDigits(10, 1 + rng.int(4)) : ''); }
  else if (k === 7) { s = rng.pick(WS) + (rng.f() < .5 ? '0x' : '') + randDigits(16, 1 + rng.int(20)) + rng.pick(['', 'zz', ' 1']); }
  else if (k === 8) { s = '0b' + randDigits(2, rng.int(70)); if (rng.f() < .5) s = '0o' + randDigits(8, rng.int(30)); if (rng.f() < .3) s += rng.pick(['2', '9', '.', 'n']); }
  else { // near float boundaries
    const m = randDigits(10, 15 + rng.int(6)); s = m[0] + '.' + m.slice(1) + 'e' + (rng.int(700) - 350);
  }
  add(s);
}
process.stdout.write(JSON.stringify(rows));
