/* The port's floating point through a stand-alone WebAssembly build of src/ffp.c.
 *
 *     node tests/ffp_wasm.mjs <ffp.wasm> <cases.bin> <results.bin>
 *
 * Cases are little-endian u32 triples (operation, D0, D1), results quadruples
 * (D0, D1, condition codes, trap).  tests/test_oracle_ffp.py compares them with the ROM's.
 */
import { readFileSync, writeFileSync } from 'node:fs';

const [wasmPath, casesPath, outPath] = process.argv.slice(2);
const instance = new WebAssembly.Instance(new WebAssembly.Module(readFileSync(wasmPath)), {});
const x = instance.exports;

const cases = new Uint32Array(readFileSync(casesPath).buffer.slice(0));
const count = cases.length / 3;
const batch = x.ffp_batch();
const results = new Uint32Array(count * 4);

for (let at = 0; at < count; at += batch) {
    const n = Math.min(batch, count - at);
    new Uint32Array(x.memory.buffer, x.ffp_input(), n * 3).set(cases.subarray(at * 3, (at + n) * 3));
    x.ffp_run(n);
    results.set(new Uint32Array(x.memory.buffer, x.ffp_output(), n * 4), at * 4);
}

writeFileSync(outPath, Buffer.from(results.buffer));
