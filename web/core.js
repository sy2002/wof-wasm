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

        /* Scratch for handing a stored file back to the core's file system: a name and the
           bytes.  One allocation, reused, because the arena is never freed. */
        this.filePtr = exports.wof_alloc(8192);
        this.namePtr = exports.wof_alloc(64);
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

    /* The keyboard assist, the port's own (src/assist.c): the weapon menu steps once per key
       press with up always up, and a tap in flight is never lost between two samples.  The
       core starts without it, as the original; the shell switches it on. */
    setKeyboardAssist(on) {
        this.x.wof_set_keyboard_assist(on ? 1 : 0);
    }

    keyboardAssist() {
        return this.x.wof_keyboard_assist() !== 0;
    }

    /* --------------------------------------------------- the file system's write side
       (SPEC 6.2, Storage).  Everything the game writes - the high-score file and the saved
       games - lives in an overlay in front of the read-only disk; the shell copies it into
       localStorage and puts it back at start, in the order it was written, because that
       order is what the load and save dialog's list is made of. */

    cstring(ptr) {
        const bytes = new Uint8Array(this.x.memory.buffer, ptr, 64);
        let n = 0;
        while (n < 64 && bytes[n]) {
            n++;
        }
        return String.fromCharCode.apply(null, bytes.subarray(0, n));
    }

    fsChanges() {
        return this.x.wof_fs_changes();
    }

    fsFiles() {
        const out = [];
        const count = this.x.wof_fs_written_count();
        for (let i = 0; i < count; i++) {
            const size = this.x.wof_fs_written_size(i);
            out.push({
                name: this.cstring(this.x.wof_fs_written_name(i)),
                data: this.bytes(this.x.wof_fs_written_bytes(i), size).slice(),
            });
        }
        return out;
    }

    fsPut(name, data) {
        if (data.length > 8192 || name.length > 62) {
            return false;
        }
        const chars = this.bytes(this.namePtr, 64);
        for (let i = 0; i < name.length; i++) {
            chars[i] = name.charCodeAt(i) & 0xff;
        }
        chars[name.length] = 0;
        this.bytes(this.filePtr, data.length).set(data);
        return this.x.wof_fs_put(this.namePtr, this.filePtr, data.length) !== 0;
    }

    /* Development entries (M3 deliverable 7): not part of the game, and offered by the
       shell only while the diagnostics overlay is up. */
    devSetScore(score) {
        this.x.wof_dev_set_score(score >>> 0);
    }

    devOpenDialog(mode) {
        this.x.wof_dev_open_dialog(mode ? 1 : 0);
    }

    /* The player's x, y and deck state and the weapon type, for the overlay and the page
       test (read-only). */
    devPlayer() {
        const p = new Int16Array(this.x.memory.buffer, this.x.wof_dev_player(), 4);
        return { x: p[0], y: p[1], deck: p[2], weapon: p[3] };
    }

    /* The pause as a request: the next pass of a mission pauses as Escape does. */
    requestPause() {
        this.x.wof_request_pause();
    }

    paused() {
        return this.x.wof_paused() !== 0;
    }

    /* The end of a pause the help screen asked for: a request not yet taken is withdrawn, a
       mission it paused continues at the next pass as P would continue it. */
    requestContinue() {
        this.x.wof_request_continue();
    }

    /* The line editor has the keys: every letter, H too, is the game's. */
    lineEditorActive() {
        return this.x.wof_line_editor_active() !== 0;
    }

    /* The PCM of emulated time the core has mixed and the shell has not taken yet, oldest
       first, at most `frames` of it: interleaved stereo int16 at the given sample rate, as
       a view into the core's memory that the next call overwrites. */
    renderAudio(frames, rate) {
        const n = this.x.wof_audio_render(this.audioPtr, Math.min(frames, this.audioFrames), rate);
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
            filesWritten: this.x.wof_fs_written_count(),
            standinHits: this.x.wof_standin_hits(),
        };
    }
}
