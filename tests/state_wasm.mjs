/* A save state in the middle of a mission, on the WebAssembly core (M4, V7).  Prints one
 * JSON object of digests; tests/test_state_m4.py compares them with each other and with the
 * native core's.
 *
 *     node tests/state_wasm.mjs <core.wasm> <fs-blob> <vblanks before the save> <vblanks after>
 *
 * The input is the one the Python side uses: the fire button for three VBlanks in every
 * thirty, which takes the front end into the first mission and goes on inside it. */
import { readFileSync } from 'node:fs';
import { createHash } from 'node:crypto';

const [wasmPath, blobPath, beforeArg, afterArg] = process.argv.slice(2);
const before = Number(beforeArg);
const after = Number(afterArg);
const module = new WebAssembly.Module(readFileSync(wasmPath));
const blob = readFileSync(blobPath);

function boot(seed) {
    const x = new WebAssembly.Instance(module, {}).exports;
    const ptr = x.wof_alloc(blob.length);
    new Uint8Array(x.memory.buffer, ptr, blob.length).set(blob);
    x.wof_init(seed >>> 0, ptr, blob.length);
    return x;
}

const raw = (v) => (v % 30 < 3 ? 0x10 : 0);
function run(x, from, count) {
    for (let v = from; v < from + count; v++) {
        x.wof_vblank(raw(v));
        x.wof_pass();
    }
}

const digest = (bytes) => createHash('sha256').update(bytes).digest('hex');
const frame = (x) => digest(new Uint8Array(x.memory.buffer, x.wof_framebuffer(),
                                           x.wof_framebuffer_width() * x.wof_framebuffer_height()));
function save(x) {
    const size = x.wof_state_size();
    const ptr = x.wof_alloc(size);
    x.wof_state_save(ptr);
    return new Uint8Array(x.memory.buffer, ptr, size).slice();
}
function load(x, bytes) {
    const ptr = x.wof_alloc(bytes.length);
    new Uint8Array(x.memory.buffer, ptr, bytes.length).set(bytes);
    x.wof_state_load(ptr);
}

const a = boot(1);
run(a, 0, before);
const saved = save(a);
const savedFrame = frame(a);
run(a, before, after);
const straight = { state: digest(save(a)), frame: frame(a) };

load(a, saved);
const loadedFrame = frame(a);
run(a, before, after);
const replayed = { state: digest(save(a)), frame: frame(a) };

const b = boot(4711);
run(b, 0, 50);
load(b, saved);
const foreignFrame = frame(b);
run(b, before, after);
const foreign = { state: digest(save(b)), frame: frame(b) };

console.log(JSON.stringify({ saved: digest(saved), savedFrame, loadedFrame, foreignFrame,
                             straight, replayed, foreign, passes: a.wof_pass_count() }));
