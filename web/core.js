/* The WebAssembly core, wrapped so that the rest of the shell never touches raw exports.
 *
 * The page runs from file://, where streaming instantiation is not available, so the module
 * arrives as bytes and goes through WebAssembly.instantiate (SPEC 5 step 4).  The core has
 * no imports at all: it allocates nothing from the host, reads no clock and makes no call
 * back into JavaScript. */

export async function loadCore(wasmBytes, fsBytes, seed) {
    const { instance } = await WebAssembly.instantiate(wasmBytes, {});
    return new Core(instance.exports, fsBytes, seed);
}

class Core {
    constructor(exports, fsBytes, seed) {
        this.x = exports;
        this.width = exports.wof_framebuffer_width();
        this.height = exports.wof_framebuffer_height();
        this.paletteCount = exports.wof_palette_count();
        this.paletteColours = exports.wof_palette_colours();

        /* The file blob goes into the core's own arena, so the core owns every byte it
           reads and nothing depends on a JavaScript object staying alive. */
        this.fsPtr = exports.wof_alloc(fsBytes.length);
        if (!this.fsPtr) {
            throw new Error('core arena too small for the file blob: ' + fsBytes.length + ' bytes');
        }
        this.bytes(this.fsPtr, fsBytes.length).set(fsBytes);
        exports.wof_init(seed >>> 0, this.fsPtr, fsBytes.length);

        this.fbPtr = exports.wof_framebuffer();
        this.rowsPtr = exports.wof_palette_rows();
        this.palPtr = exports.wof_palettes();

        /* One scratch buffer for audio, big enough for the largest block the shell asks
           for; wof_audio_render writes interleaved stereo int16 into it. */
        this.audioFrames = 8192;
        this.audioPtr = exports.wof_alloc(this.audioFrames * 4);
        this.statePtr = exports.wof_alloc(exports.wof_state_size());
    }

    bytes(ptr, length) {
        return new Uint8Array(this.x.memory.buffer, ptr, length);
    }

    framebuffer() {
        return new Uint8Array(this.x.memory.buffer, this.fbPtr, this.width * this.height);
    }

    paletteRows() {
        return new Uint16Array(this.x.memory.buffer, this.rowsPtr, this.height);
    }

    palettes() {
        return new Uint32Array(this.x.memory.buffer, this.palPtr, this.paletteCount * this.paletteColours);
    }

    setVideoHz(hz) {
        this.x.wof_set_video_hz(hz);
    }

    vblank(raw) {
        this.x.wof_vblank(raw & 0x1f);
    }

    pass() {
        this.x.wof_pass();
    }

    /* TEMPORARY - the M1 viewer's four keys (src/viewer.c).  It goes when the front end
       takes the page over. */
    keyPress(code) {
        this.x.wof_key_press(code & 0xff);
    }

    /* The real key path (SPEC 6.2): a positional raw Amiga key code and the qualifier bits
       of Shift and Caps Lock, through the port's own layer in front of the key buffer. */
    portKey(code, qualifier) {
        this.x.wof_port_key(code & 0xff, qualifier & 0xffff);
    }

    /* The buffer itself, for a test that wants to bypass the port's layer. */
    key(code, qualifier) {
        this.x.wof_key(code & 0xff, qualifier & 0xffff);
    }

    /* The owner's remembered vertical flip.  It is a preference, not game state: the shell
       stores it and hands it over at start, and it wins over a loaded game (SPEC 6.1). */
    setInvertVertical(on) {
        this.x.wof_set_invert_vertical(on ? 1 : 0);
    }

    invertVertical() {
        return this.x.wof_invert_vertical() !== 0;
    }

    /* Interleaved stereo int16, as many frames as asked for, at the given sample rate. */
    renderAudio(frames, rate) {
        const n = Math.min(frames, this.audioFrames);
        this.x.wof_audio_render(this.audioPtr, n, rate);
        return new Int16Array(this.x.memory.buffer, this.audioPtr, n * 2);
    }

    saveState() {
        this.x.wof_state_save(this.statePtr);
        return this.bytes(this.statePtr, this.x.wof_state_size()).slice();
    }

    loadState(state) {
        this.bytes(this.statePtr, this.x.wof_state_size()).set(state);
        this.x.wof_state_load(this.statePtr);
    }

    counters() {
        return {
            vblanks: this.x.wof_vblank_count(),
            ticks: this.x.wof_tick_count(),
            passes: this.x.wof_pass_count(),
            files: this.x.wof_fs_count(),
            arenaUsed: this.x.wof_arena_used(),
            arenaSize: this.x.wof_arena_size(),
            assetsReady: this.x.wof_assets_ready(),
        };
    }
}
