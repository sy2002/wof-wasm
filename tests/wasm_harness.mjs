/* Runs the WebAssembly core headlessly in Node and prints one JSON object of measurements.
 * tests/test_core_wasm.py asserts on the fields; keeping the checks here and the assertions
 * there means one Node start-up for the whole suite.
 *
 *     node tests/wasm_harness.mjs <core.wasm> <fs-blob>
 */
import { readFileSync } from 'node:fs';
import { createHash } from 'node:crypto';

const [wasmPath, blobPath] = process.argv.slice(2);
const wasmBytes = readFileSync(wasmPath);
const blob = readFileSync(blobPath);
const module = new WebAssembly.Module(wasmBytes);

function boot(seed, withBlob = true) {
    const instance = new WebAssembly.Instance(module, {});
    const x = instance.exports;
    let ptr = 0;
    let length = 0;
    if (withBlob) {
        length = blob.length;
        ptr = x.wof_alloc(length);
        new Uint8Array(x.memory.buffer, ptr, length).set(blob);
    }
    x.wof_init(seed >>> 0, ptr, length);
    return x;
}

const u8 = (x, ptr, n) => new Uint8Array(x.memory.buffer, ptr, n);
const u16 = (x, ptr, n) => new Uint16Array(x.memory.buffer, ptr, n);
const u32 = (x, ptr, n) => new Uint32Array(x.memory.buffer, ptr, n);

function framebuffer(x) {
    return u8(x, x.wof_framebuffer(), x.wof_framebuffer_width() * x.wof_framebuffer_height());
}

function digest(bytes) {
    return createHash('sha256').update(bytes).digest('hex');
}

function run(x, vblanks, raw = 0) {
    for (let i = 0; i < vblanks; i++) {
        x.wof_vblank(raw);
        x.wof_pass();
    }
}

/* Zero crossings of a triangle wave give its frequency directly: two per cycle. */
function frequency(samples, channel, frames, rate) {
    let crossings = 0;
    for (let i = 1; i < frames; i++) {
        const a = samples[(i - 1) * 2 + channel];
        const b = samples[i * 2 + channel];
        if ((a < 0) !== (b < 0)) {
            crossings++;
        }
    }
    return crossings / 2 / (frames / rate);
}

function tone(x, rate, raw) {
    const frames = 16384;
    const ptr = x.wof_alloc(frames * 4);
    x.wof_vblank(raw);                       /* the raw state is what selects the octave */
    x.wof_audio_render(ptr, frames, rate);
    const samples = new Int16Array(x.memory.buffer, ptr, frames * 2);
    let peak = 0;
    for (let i = 0; i < frames * 2; i++) {
        peak = Math.max(peak, Math.abs(samples[i]));
    }
    return {
        rate,
        left: frequency(samples, 0, frames, rate),
        right: frequency(samples, 1, frames, rate),
        peak,
    };
}

const result = {};

result.exports = WebAssembly.Module.exports(module).map((e) => e.name).sort();
result.imports = WebAssembly.Module.imports(module).map((e) => e.module + '.' + e.name);

{
    const x = boot(1);
    result.geometry = {
        width: x.wof_framebuffer_width(),
        height: x.wof_framebuffer_height(),
        paletteCount: x.wof_palette_count(),
        paletteColours: x.wof_palette_colours(),
        stateSize: x.wof_state_size(),
        arenaSize: x.wof_arena_size(),
    };
    result.files = x.wof_fs_count();

    const rows = u16(x, x.wof_palette_rows(), x.wof_framebuffer_height());
    result.paletteRows = {
        min: Math.min(...rows),
        max: Math.max(...rows),
        distinct: [...new Set(rows)].length,
        first: rows[0],
        last: rows[rows.length - 1],
    };

    const pal = u32(x, x.wof_palettes(), x.wof_palette_count() * x.wof_palette_colours());
    result.palettes = {
        opaque: [...pal].every((c) => (c >>> 24) === 0xff),
        differ: [...pal.slice(0, 32)].some((c, i) => c !== pal[32 + i]),
        distinctInPalette0: new Set(pal.slice(0, 32)).size,
    };

    const countPtr = x.wof_alloc(4);
    const listPtr = x.wof_display_list(countPtr);
    result.displayList = { pointer: listPtr !== 0, count: u32(x, countPtr, 1)[0] };
}

/* N VBlanks give N / 4 ticks, and the boundary lands where vblank_server puts it. */
{
    const x = boot(1);
    const steps = [];
    for (const n of [1, 2, 3, 4, 5, 8, 240]) {
        const y = boot(1);
        run(y, n);
        steps.push({ vblanks: n, ticks: y.wof_tick_count(), passes: y.wof_pass_count() });
    }
    run(x, 600);
    result.ticks = {
        steps,
        after600: { vblanks: x.wof_vblank_count(), ticks: x.wof_tick_count(), passes: x.wof_pass_count() },
    };
}

/* The framebuffer holds indices, every one of them inside the palette. */
{
    const x = boot(1);
    run(x, 41, 0x1f);
    const fb = framebuffer(x);
    let max = 0;
    let nonzero = 0;
    for (const value of fb) {
        if (value > max) max = value;
        if (value) nonzero++;
    }
    result.framebuffer = { max, nonzero, size: fb.length, hash: digest(fb) };
}

result.tones = {
    idle44100: tone(boot(1), 44100, 0),
    idle48000: tone(boot(1), 48000, 0),
    fire48000: tone(boot(1), 48000, 0x10),
};

/* Save and load round-trip, and a replay from a loaded state matching one from the start. */
{
    const a = boot(7);
    run(a, 100);
    const size = a.wof_state_size();
    const ptr = a.wof_alloc(size);
    a.wof_state_save(ptr);
    const saved = u8(a, ptr, size).slice();
    const savedFrame = digest(framebuffer(a));

    run(a, 60);
    a.wof_state_save(ptr);
    const straight = { state: digest(u8(a, ptr, size)), frame: digest(framebuffer(a)) };

    u8(a, ptr, size).set(saved);
    a.wof_state_load(ptr);
    const restored = { state: digest(saved), frame: digest(framebuffer(a)) };
    run(a, 60);
    a.wof_state_save(ptr);
    const replayed = { state: digest(u8(a, ptr, size)), frame: digest(framebuffer(a)) };

    /* A fresh core loaded with the same state must continue identically. */
    const b = boot(999);
    const bptr = b.wof_alloc(size);
    u8(b, bptr, size).set(saved);
    b.wof_state_load(bptr);
    const bAfterLoad = digest(framebuffer(b));
    run(b, 60);
    b.wof_state_save(bptr);

    result.state = {
        size,
        savedFrame,
        straight,
        restored,
        replayed,
        matchesAfterReplay: straight.state === replayed.state && straight.frame === replayed.frame,
        foreignCoreMatches: digest(u8(b, bptr, size)) === straight.state,
        foreignFrameAfterLoad: bAfterLoad,
        rejectsGarbage: (() => {
            const c = boot(3);
            run(c, 20);
            const cptr = c.wof_alloc(size);
            c.wof_state_save(cptr);
            const before = digest(u8(c, cptr, size));
            u8(c, cptr, size).fill(0xab);
            c.wof_state_load(cptr);
            c.wof_state_save(cptr);
            return digest(u8(c, cptr, size)) === before;
        })(),
    };
}

/* Determinism (SPEC 7.3): the picture is a function of the seed and the input, nothing else. */
{
    const one = boot(42);
    const two = boot(42);
    const other = boot(43);
    run(one, 200, 0);
    run(two, 200, 0);
    run(other, 200, 0);
    result.determinism = {
        sameSeed: digest(framebuffer(one)) === digest(framebuffer(two)),
        differentSeed: digest(framebuffer(one)) !== digest(framebuffer(other)),
        hash: digest(framebuffer(one)),
    };
}

/* The blob has to arrive through wof_init; a core that got none reports no files. */
{
    const empty = boot(1, false);
    result.emptyFs = empty.wof_fs_count();
}

/* The cross-target check: the native build must produce the same picture from the same
 * input.  test_core_native.py compares its hash with this one. */
{
    const x = boot(0x57494e47);
    run(x, 123, 0x05);
    result.crossTarget = { seed: 0x57494e47, vblanks: 123, raw: 0x05, hash: digest(framebuffer(x)) };
}

process.stdout.write(JSON.stringify(result, null, 1));
