/* Shell entry point: decode the two payloads the build inlined, start the core, wire the
   clock, video, input, audio and the diagnostics overlay together. */

import { loadCore } from './core.js';
import { createVideo } from './video.js';
import { createInput } from './input.js';
import { createAudio } from './audio.js';
import { createClock } from './clock.js';
import { createOverlay } from './overlay.js';

/* A fixed seed, so that the same page always produces the same picture.  The original takes
   its seed from the beam position at start (re/notes/random.md); which seed the port uses
   is a front-end question and belongs to M3. */
const SEED = 0x57494e47;

function decodeBase64(text) {
    const binary = atob(text.replace(/\s+/g, ''));
    const out = new Uint8Array(binary.length);
    for (let i = 0; i < binary.length; i++) {
        out[i] = binary.charCodeAt(i);
    }
    return out;
}

function fail(message) {
    const hint = document.getElementById('hint');
    hint.textContent = message;
    hint.style.color = '#ff8080';
}

async function boot() {
    const wasm = decodeBase64(document.getElementById('wof-wasm').textContent);
    const blob = decodeBase64(document.getElementById('wof-fs').textContent);

    const core = await loadCore(wasm, blob, SEED);
    const video = createVideo(document.getElementById('screen'), core);
    const input = createInput(window);
    const audio = createAudio(core);
    const overlay = createOverlay(document.getElementById('overlay'), core, null, audio, input);
    const clock = createClock(core, input, video, audio, overlay.paint);

    /* The overlay needs the clock and the clock needs the overlay's paint function; the
       overlay is told about the clock once both exist. */
    overlay.attach(clock);

    const gesture = document.getElementById('gesture');
    async function firstGesture() {
        gesture.classList.add('off');
        await audio.start();
    }
    window.addEventListener('keydown', firstGesture, { once: true });
    window.addEventListener('pointerdown', firstGesture, { once: true });

    window.addEventListener('keydown', (event) => {
        if (event.code === 'Backquote') {
            overlay.toggle();
            event.preventDefault();
        } else if (event.code === 'Digit5') {
            clock.setHz(50);
        } else if (event.code === 'Digit6') {
            clock.setHz(60);
        }
    });

    document.addEventListener('visibilitychange', () => {
        if (document.hidden) {
            clock.stop();
            audio.suspend();
        } else {
            audio.resume();
            clock.start();
        }
    });

    clock.start();
}

boot().catch((err) => fail('start failed: ' + (err && err.message ? err.message : err)));
