/* Audio: pull PCM from the core and play it (SPEC 6.2).
 *
 * An AudioWorklet is the real path.  Its module cannot be a file next to the page, so it
 * is handed to the browser as a URL made on the spot: a Blob URL, or a data: URL where a
 * file:// page refuses Blob URLs.  Where neither is allowed, scheduled
 * AudioBufferSourceNodes carry the same samples, a block at a time.  Which one is live is
 * on the diagnostics overlay, because the difference is otherwise inaudible.
 *
 * Nothing starts before the first user gesture: browsers do not allow it, and the M0
 * acceptance criterion is exactly that - a test tone after a key press. */

/* tools/build.py replaces this literal with the text of web/worklet.js. */
const WORKLET_SOURCE = '@@WOF_WORKLET_SOURCE@@';

const TARGET_SECONDS = 0.12;   /* audio kept queued ahead of the hardware */
const MIN_RENDER = 256;        /* do not bother the core for less than this many frames */
const FALLBACK_BLOCK = 1024;

/* SPEC 6.2 asks for the worklet module as a Blob URL.  Chrome refuses to load one on a
   file:// page - the origin is opaque, and the fetch is treated as a cross-origin one - so
   a data: URL, which it does allow there, is tried next.  The scheduled buffers remain the
   fallback for anything that allows neither.  The source is ASCII, so btoa is safe. */
async function addWorkletModule(ctx) {
    const blobUrl = () => URL.createObjectURL(new Blob([WORKLET_SOURCE], { type: 'text/javascript' }));
    const dataUrl = () => 'data:text/javascript;base64,' + btoa(WORKLET_SOURCE);

    /* On a file:// page the blob: attempt is certain to fail and would log an error that
       looks like a fault, so the order is turned around there. */
    const candidates = location.protocol === 'file:' ? [dataUrl, blobUrl] : [blobUrl, dataUrl];
    let failure = null;

    for (const makeUrl of candidates) {
        const url = makeUrl();
        const kind = url.slice(0, 5) === 'blob:' ? 'blob:' : 'data:';
        try {
            await ctx.audioWorklet.addModule(url);
            return kind;
        } catch (err) {
            failure = err;
        } finally {
            if (kind === 'blob:') {
                URL.revokeObjectURL(url);
            }
        }
    }
    throw failure;
}

export function createAudio(core) {
    let ctx = null;
    let gain = null;
    let node = null;
    let backend = 'off';
    let note = '';
    let sent = 0;
    let consumed = 0;
    let underruns = 0;
    let nextTime = 0;

    /* Every browser's autoplay policy wants the context created and resumed while the page
       is activated, and Firefox counts that activation as transient.  Both calls therefore
       happen in the same task as the gesture that reached us, with no await in between, and
       nothing here is reached before that gesture: createAudio only builds closures, pump
       and resume return at once while there is no context, and start is called from the
       gesture handler alone. */
    function resume() {
        if (!ctx) {
            return;
        }
        /* A blocked resume stays pending in Firefox rather than rejecting, so it is never
           awaited: pump runs again on every animation frame and picks the audio up as soon
           as the context is running. */
        ctx.resume().catch(() => undefined);
    }

    async function start() {
        if (ctx) {
            resume();
            return backend;
        }

        const Ctor = window.AudioContext || window.webkitAudioContext;
        if (!Ctor) {
            backend = 'none';
            note = 'no Web Audio';
            return backend;
        }

        ctx = new Ctor();
        resume();
        gain = ctx.createGain();
        gain.gain.value = 1;
        gain.connect(ctx.destination);

        /* ?audio=buffers forces the fallback, so that the path that only some browsers take
           can be exercised deliberately instead of only when something else has failed. */
        const forced = new URLSearchParams(location.search).get('audio');

        if (ctx.audioWorklet && forced !== 'buffers') {
            try {
                note = 'worklet module from a ' + (await addWorkletModule(ctx)) + ' URL';
                node = new AudioWorkletNode(ctx, 'wof-core', {
                    numberOfInputs: 0,
                    numberOfOutputs: 1,
                    outputChannelCount: [2],
                });
                node.port.onmessage = (event) => {
                    consumed = event.data.consumed;
                    underruns = event.data.underruns;
                };
                node.connect(gain);
                backend = 'worklet';
            } catch (err) {
                node = null;
                note = 'worklet refused: ' + (err && err.message ? err.message : err);
            }
        } else {
            note = forced === 'buffers' ? 'scheduled buffers, asked for by ?audio=buffers'
                                        : 'no AudioWorklet';
        }

        if (!node) {
            backend = 'buffers';
            nextTime = 0;
        }

        pump();
        return backend;
    }

    function deinterleave(pcm, frames) {
        const left = new Float32Array(frames);
        const right = new Float32Array(frames);
        for (let i = 0; i < frames; i++) {
            left[i] = pcm[i * 2] / 32768;
            right[i] = pcm[i * 2 + 1] / 32768;
        }
        return { left, right };
    }

    function pumpWorklet() {
        const rate = ctx.sampleRate;
        const want = Math.ceil(TARGET_SECONDS * rate) - (sent - consumed);
        if (want < MIN_RENDER) {
            return;
        }
        const frames = Math.min(want, core.audioFrames);
        const block = deinterleave(core.renderAudio(frames, rate), frames);
        node.port.postMessage(block, [block.left.buffer, block.right.buffer]);
        sent += frames;
    }

    function pumpBuffers() {
        const rate = ctx.sampleRate;
        if (nextTime < ctx.currentTime) {
            if (nextTime !== 0) {
                underruns++;
            }
            nextTime = ctx.currentTime + 0.02;
        }
        while (nextTime < ctx.currentTime + TARGET_SECONDS) {
            const pcm = core.renderAudio(FALLBACK_BLOCK, rate);
            const buffer = ctx.createBuffer(2, FALLBACK_BLOCK, rate);
            const left = buffer.getChannelData(0);
            const right = buffer.getChannelData(1);
            for (let i = 0; i < FALLBACK_BLOCK; i++) {
                left[i] = pcm[i * 2] / 32768;
                right[i] = pcm[i * 2 + 1] / 32768;
            }
            const source = ctx.createBufferSource();
            source.buffer = buffer;
            source.connect(gain);
            source.start(nextTime);
            nextTime += FALLBACK_BLOCK / rate;
            sent += FALLBACK_BLOCK;
            consumed = sent - Math.round((nextTime - ctx.currentTime) * rate);
        }
    }

    /* Called once per animation frame by the clock; renders only what is missing. */
    function pump() {
        if (!ctx || ctx.state !== 'running') {
            return;
        }
        if (backend === 'worklet') {
            pumpWorklet();
        } else if (backend === 'buffers') {
            pumpBuffers();
        }
    }

    function suspend() {
        if (ctx && ctx.state === 'running') {
            ctx.suspend();
        }
    }

    /* Coming back from a hidden page.  The page has been activated long before, so this is
       an ordinary resume; the fallback's schedule is dropped because its clock moved on. */
    function resumeFromHidden() {
        if (ctx && ctx.state === 'suspended') {
            nextTime = 0;
            resume();
        }
    }

    /* Whether a further gesture could still change anything.  True once the context is
       running, and also where there is no Web Audio at all, because then no gesture will
       ever produce sound and the page should stop waiting for one. */
    function ready() {
        return backend === 'none' || (!!ctx && ctx.state === 'running');
    }

    function stats() {
        const rate = ctx ? ctx.sampleRate : 0;
        const queued = backend === 'buffers' && ctx
            ? Math.max(0, nextTime - ctx.currentTime) * 1000
            : (rate ? (sent - consumed) / rate * 1000 : 0);
        return {
            backend,
            note,
            state: ctx ? ctx.state : 'none',
            rate,
            queuedMs: queued,
            underruns,
        };
    }

    return { start, ready, pump, suspend, resume: resumeFromHidden, stats };
}
