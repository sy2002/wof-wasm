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

/* Keys that produce no character and therefore no user activation. */
const INERT_KEYS = new Set([
    'Meta', 'Control', 'Alt', 'AltGraph', 'Shift', 'CapsLock', 'Dead',
    'NumLock', 'ScrollLock', 'Fn', 'FnLock', 'Hyper', 'Super', 'Symbol', 'SymbolLock',
]);

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
    const clock = createClock(core, input, video, audio, (now) => {
        overlay.paint(now);
        checkAudioStarted();
    });

    /* The overlay needs the clock and the clock needs the overlay's paint function; the
       overlay is told about the clock once both exist. */
    overlay.attach(clock);

    const gesture = document.getElementById('gesture');

    /* Audio may only be started from a gesture, and not every event is one.  A modifier on
       its own - the Command of a Cmd+Option+K that opens the console, or a bare Shift - is
       a keydown that activates nothing, and a context built there is born suspended and
       stays that way.  So the page keeps listening until sound is actually running, and
       does nothing at all on an event that does not activate it: constructing a context
       that cannot start is what makes a browser log the autoplay warning. */
    function activates(event) {
        if (navigator.userActivation) {
            return navigator.userActivation.isActive;
        }
        /* Without navigator.userActivation, judge the event: modifiers and dead keys never
           activate, and a key pressed with a modifier held is a browser shortcut. */
        if (event.type !== 'keydown') {
            return true;
        }
        return !INERT_KEYS.has(event.key)
            && !event.metaKey && !event.ctrlKey && !event.altKey;
    }

    function onGesture(event) {
        if (!activates(event)) {
            return;
        }
        /* In this task, so that the activation is still in hand: the context is built and
           resumed inside audio.start(). */
        audio.start().catch(() => undefined);
    }

    window.addEventListener('keydown', onGesture);
    window.addEventListener('pointerdown', onGesture);

    /* The prompt is a statement about the sound, so it goes when the sound is really there,
       not when some event has been seen.  The listeners go at the same moment. */
    let waitingForAudio = true;
    function checkAudioStarted() {
        if (!waitingForAudio || !audio.ready()) {
            return;
        }
        waitingForAudio = false;
        gesture.classList.add('off');
        window.removeEventListener('keydown', onGesture);
        window.removeEventListener('pointerdown', onGesture);
    }

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
