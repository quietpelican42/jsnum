'use strict';
// Deterministic PRNG (mulberry32) so corpora are reproducible across Node versions.
function makeRng(seed) {
  let a = seed >>> 0;
  function u32() {
    a = (a + 0x6d2b79f5) >>> 0;
    let t = a;
    t = Math.imul(t ^ (t >>> 15), t | 1);
    t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
    return (t ^ (t >>> 14)) >>> 0;
  }
  const f = () => u32() / 4294967296;
  const int = (n) => Math.floor(f() * n);
  const pick = (arr) => arr[int(arr.length)];
  return { u32, f, int, pick };
}
const dv = new DataView(new ArrayBuffer(8));
function toHex(x) {
  dv.setFloat64(0, x);
  return dv.getBigUint64(0).toString(16).padStart(16, '0');
}
function fromHex(h) {
  dv.setBigUint64(0, BigInt('0x' + h));
  return dv.getFloat64(0);
}
function bitsDouble(rng) {
  dv.setUint32(0, rng.u32());
  dv.setUint32(4, rng.u32());
  return dv.getFloat64(0);
}
module.exports = { makeRng, toHex, fromHex, bitsDouble };
