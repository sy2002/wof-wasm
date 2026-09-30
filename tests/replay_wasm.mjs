/* A stored replay of tests/replays/ on the WebAssembly core (SPEC 8, "Whole game, replays";
 * tests/test_replays.py).  Prints one JSON object: the state hash after every input sample
 * and at the end, as the native side computes them.
 *
 *     node tests/replay_wasm.mjs <core.wasm> <fs-blob> <replay.json> */
import { readFileSync } from 'node:fs';
import { createHash } from 'node:crypto';

const [wasmPath, blobPath, replayPath] = process.argv.slice(2);
const replay = JSON.parse(readFileSync(replayPath, 'utf8'));
const module = new WebAssembly.Module(readFileSync(wasmPath));
const blob = readFileSync(blobPath);
const x = new WebAssembly.Instance(module, {}).exports;

const ptr = x.wof_alloc(blob.length);
new Uint8Array(x.memory.buffer, ptr, blob.length).set(blob);
x.wof_set_fade_vblanks(replay.fades);
x.wof_init(replay.seed >>> 0, ptr, blob.length);

/* The files laid over the disk, through the shell's own entry (SPEC 6.2, Storage). */
const scratch = x.wof_alloc(1 << 14);
const namePtr = x.wof_alloc(64);
for (const [name, hex] of Object.entries(replay.files)) {
    const data = Buffer.from(hex, 'hex');
    const chars = new Uint8Array(x.memory.buffer, namePtr, 64);
    for (let i = 0; i < name.length; i++) {
        chars[i] = name.charCodeAt(i);
    }
    chars[name.length] = 0;
    new Uint8Array(x.memory.buffer, scratch, data.length).set(data);
    if (!x.wof_fs_put(namePtr, scratch, data.length)) {
        throw new Error('wof_fs_put refused ' + name);
    }
}

const size = x.wof_state_size();
const statePtr = x.wof_alloc(size);
const digest = () => {
    x.wof_state_save(statePtr);
    return createHash('sha256').update(new Uint8Array(x.memory.buffer, statePtr, size))
        .digest('hex').slice(0, 16);
};

const hashes = [];
let last = x.wof_tick_count();
for (const entry of replay.schedule) {
    const [n, raw] = entry;
    const keys = entry.length > 2 ? entry[2] : [];
    for (let i = 0; i < n; i++) {
        if (i === 0) {
            for (const [code, qualifier] of keys) {
                x.wof_key(code, qualifier);
            }
        }
        x.wof_vblank(raw);
        x.wof_pass();
        const now = x.wof_tick_count();
        if (now !== last) {
            hashes.push([now, digest()]);
            last = now;
        }
    }
}
process.stdout.write(JSON.stringify({ hashes, final: digest() }) + '\n');
