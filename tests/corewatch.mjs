/* Instrumentation for the one page on which the page checks hold the stick keys.
 *
 * The shell hands the raw controller state of SPEC 6.1 to the core once per VBlank, and
 * nothing on the page says what it handed over: the overlay reads the input module, not the
 * call.  So the call itself is watched.  WebAssembly.instantiate is wrapped before any page
 * script runs, and the instance the shell gets back has its wof_vblank export replaced by a
 * function that notes the argument and passes it on unchanged.  The shell runs as it is;
 * every other export, the memory included, is the core's own.
 *
 *   window.__wofRaw = { last, seen, calls }
 *     last   the argument of the most recent wof_vblank
 *     seen   every bit handed over since the harness last set it to 0
 *     calls  how many VBlanks that was
 */
export const CORE_WATCH = `() => {
    window.__wofRaw = { last: 0, seen: 0, calls: 0 };
    const native = WebAssembly.instantiate;
    WebAssembly.instantiate = async function (...args) {
        const result = await native.apply(this, args);
        const real = result.instance && result.instance.exports;
        if (!real || typeof real.wof_vblank !== 'function') {
            return result;
        }
        const exports = {};
        for (const name of Object.keys(real)) {
            exports[name] = real[name];
        }
        exports.wof_vblank = (raw) => {
            window.__wofRaw.last = raw;
            window.__wofRaw.seen |= raw;
            window.__wofRaw.calls += 1;
            return real.wof_vblank(raw);
        };
        return { module: result.module, instance: { exports } };
    };
}`;

/* What the harness reads while a key is held: the overlay's input line and the watch. */
export const STICK_LOOK = `({
    input: (document.getElementById('overlay').textContent.match(/^input\\s+(.*)$/m) || [null, null])[1],
    raw: window.__wofRaw,
})`;
