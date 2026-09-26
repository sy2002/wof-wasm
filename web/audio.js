/* Audio: take the core's PCM and play it (SPEC 6.2, 6.5).
 *
 * The core mixes Paula's four channels VBlank by VBlank as it emulates them, so the samples
 * are emulated time: every animation frame the shell takes what the VBlanks it has just run
 * produced and queues it behind what is playing.  The two clocks, the emulation's and the
 * audio hardware's, drift apart a little, so the queue is kept between two bounds: below
 * the lower one the shell adds silence, above the upper one it drops what the core gave.
 * Both are counted and shown on the diagnostics overlay.
 *
 * An AudioWorklet is the real path.  Its module cannot be a file next to the page, so it
 * is handed to the browser as a URL made on the spot: a Blob URL, or a data: URL where a
 * file:// page refuses Blob URLs.  Where neither is allowed, scheduled
 * AudioBufferSourceNodes carry the same samples, a block at a time.  Which one is live is
 * on the diagnostics overlay, because the difference is otherwise inaudible.
 *
 * Nothing starts before the first user gesture: browsers do not allow it.  What the core
 * mixed before then is dropped when the sound starts. */

/* tools/build.py replaces this literal with the text of web/worklet.js. */
const WORKLET_SOURCE = '@@WOF_WORKLET_SOURCE@@';

const TARGET_SECONDS = 0.10;   /* queued ahead of the hardware when the sound starts */
const LOW_SECONDS = 0.04;      /* below this much queued, silence tops it up to the target */
const HIGH_SECONDS = 0.30;     /* above this much queued, the core's PCM is dropped */

/* The stereo width: 1 is the Amiga's, channels 0 and 3 hard left and 1 and 2 hard right;
   lower values blend each side into the other, 0 is mono.  A shell setting (SPEC 6.5). */
export const STEREO_WIDTHS = [1, 0.75, 0.5, 0.25];

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

export function createAudio(core, width = 1) {
    let ctx = null;
    let gain = null;
    let node = null;
    let backend = 'off';
    let note = '';
    let sent = 0;
    let consumed = 0;
    let underruns = 0;
    let nextTime = 0;
    let fresh = true;          /* the next pump starts the queue: the core's backlog goes */
    const counts = { emulated: 0, audible: 0, padded: 0, dropped: 0, peak: 0 };

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

    /* int16 interleaved to two float channels, with the stereo width applied. */
    function split(pcm, frames) {
        const left = new Float32Array(frames);
        const right = new Float32Array(frames);
        const near = (1 + width) / 2 / 32768;
        const far = (1 - width) / 2 / 32768;
        for (let i = 0; i < frames; i++) {
            const l = pcm[i * 2];
            const r = pcm[i * 2 + 1];
            left[i] = l * near + r * far;
            right[i] = r * near + l * far;
        }
        return { left, right };
    }

    /* Everything the core has mixed since the last call, as blocks of float channels, with
       the counts the page tests read: frames of emulated time, and how many were not
       silent. */
    function takeEmulated(rate) {
        const blocks = [];
        for (;;) {
            const pcm = core.renderAudio(core.audioFrames, rate);
            const frames = pcm.length / 2;
            if (frames === 0) {
                break;
            }
            for (let i = 0; i < frames; i++) {
                const l = pcm[i * 2];
                const r = pcm[i * 2 + 1];
                if (l !== 0 || r !== 0) {
                    counts.audible++;
                    counts.peak = Math.max(counts.peak, Math.abs(l), Math.abs(r));
                }
            }
            counts.emulated += frames;
            blocks.push(split(pcm, frames));
            if (frames < core.audioFrames) {
                break;
            }
        }
        return blocks;
    }

    function silence(frames) {
        return { left: new Float32Array(frames), right: new Float32Array(frames) };
    }

    function post(block) {
        const frames = block.left.length;
        node.port.postMessage(block, [block.left.buffer, block.right.buffer]);
        sent += frames;
    }

    function pumpWorklet() {
        const rate = ctx.sampleRate;
        let queued = sent - consumed;
        for (const block of takeEmulated(rate)) {
            if (fresh) {
                continue;                        /* mixed before the sound started */
            }
            if (queued > HIGH_SECONDS * rate) {
                counts.dropped += block.left.length;
                continue;
            }
            post(block);
            queued += block.left.length;
        }
        if (fresh || queued < LOW_SECONDS * rate) {
            const pad = Math.ceil(TARGET_SECONDS * rate - queued);
            if (!fresh) {
                counts.padded += pad;
            }
            post(silence(pad));
        }
        fresh = false;
    }

    function schedule(block, rate) {
        const frames = block.left.length;
        const buffer = ctx.createBuffer(2, frames, rate);
        buffer.getChannelData(0).set(block.left);
        buffer.getChannelData(1).set(block.right);
        const source = ctx.createBufferSource();
        source.buffer = buffer;
        source.connect(gain);
        source.start(nextTime);
        nextTime += frames / rate;
        sent += frames;
    }

    function pumpBuffers() {
        const rate = ctx.sampleRate;
        const blocks = takeEmulated(rate);
        if (fresh || nextTime < ctx.currentTime + LOW_SECONDS) {
            if (!fresh && nextTime < ctx.currentTime) {
                underruns++;
            }
            if (!fresh) {
                counts.padded += Math.round(
                    (ctx.currentTime + TARGET_SECONDS - Math.max(nextTime, ctx.currentTime)) * rate);
            }
            nextTime = ctx.currentTime + TARGET_SECONDS;
        }
        for (const block of blocks) {
            if (fresh) {
                continue;
            }
            if (nextTime > ctx.currentTime + HIGH_SECONDS) {
                counts.dropped += block.left.length;
                continue;
            }
            schedule(block, rate);
        }
        fresh = false;
        consumed = sent - Math.round((nextTime - ctx.currentTime) * rate);
    }

    /* Called once per animation frame by the clock, after the VBlanks it ran. */
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
       an ordinary resume; the queue starts again, because its clock moved on. */
    function resumeFromHidden() {
        if (ctx && ctx.state === 'suspended') {
            nextTime = 0;
            fresh = true;
            resume();
        }
    }

    /* Whether a further gesture could still change anything.  True once the context is
       running, and also where there is no Web Audio at all, because then no gesture will
       ever produce sound and the page should stop waiting for one. */
    function ready() {
        return backend === 'none' || (!!ctx && ctx.state === 'running');
    }

    function setWidth(value) {
        width = Math.max(0, Math.min(1, value));
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
            width,
            emulated: counts.emulated,
            audible: counts.audible,
            peak: counts.peak,
            padded: counts.padded,
            dropped: counts.dropped,
        };
    }

    return { start, ready, pump, suspend, resume: resumeFromHidden, stats, setWidth };
}
