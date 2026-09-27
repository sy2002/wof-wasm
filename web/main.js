/* Shell entry point: decode the two payloads the build inlined, start the core, wire the
   clock, video, input, audio and the diagnostics overlay together. */

import { loadCore } from './core.js';
import { createVideo } from './video.js';
import { createInput } from './input.js';
import { createAudio, STEREO_WIDTHS } from './audio.js';
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

/* The shell's own settings live beside the game's files, under the same wof: prefix
   (SPEC 6.2, Storage).  A browser that refuses storage must not stop the game. */
const SETTINGS_PREFIX = 'wof:';

function readSetting(name) {
    try {
        return window.localStorage.getItem(SETTINGS_PREFIX + name);
    } catch (err) {
        return null;
    }
}

function writeSetting(name, value) {
    try {
        window.localStorage.setItem(SETTINGS_PREFIX + name, value);
    } catch (err) {
        /* private mode, or storage turned off: the setting simply does not survive */
    }
}

/* The high-score file and the saved games, kept between visits (SPEC 6.2, Storage).  They
   live under one key so that the order they were written in survives with them: the load
   and save dialog lists them in the order the file system hands them out, and that order
   is made of the names and of which file is the newer (re/notes/frontend.md). */
const FILES_KEY = 'files';

function encodeBase64(bytes) {
    let binary = '';
    for (let i = 0; i < bytes.length; i++) {
        binary += String.fromCharCode(bytes[i]);
    }
    return btoa(binary);
}

function restoreFiles(core) {
    const stored = readSetting(FILES_KEY);
    if (!stored) {
        return;
    }
    try {
        for (const file of JSON.parse(stored)) {
            core.fsPut(file.name, decodeBase64(file.data));
        }
    } catch (err) {
        /* Something else wrote the key, or it was truncated: start with the disk alone. */
    }
}

function storeFiles(core) {
    const files = core.fsFiles().map((file) => (
        { name: file.name, data: encodeBase64(file.data) }));
    writeSetting(FILES_KEY, JSON.stringify(files));
}

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
    hint.classList.remove('off');
}

async function boot() {
    const wasm = decodeBase64(document.getElementById('wof-wasm').textContent);
    const blob = decodeBase64(document.getElementById('wof-fs').textContent);

    const core = await loadCore(wasm, blob, SEED);
    const video = createVideo(document.getElementById('screen'), core);
    const input = createInput(window, core);

    /* The vertical flip is the owner's, not the game's: hand the remembered value over
       before the first VBlank and write it back whenever the flip command changes it. */
    let invert = readSetting('invertVertical') === '1';
    core.setInvertVertical(invert);

    /* The keyboard assist is the port's own and always on here: the core starts as the
       original does, which is what every comparison with it runs. */
    core.setKeyboardAssist(true);

    /* What the game wrote last time, back before the first pass. */
    restoreFiles(core);
    let fsSeen = core.fsChanges();
    function rememberFiles() {
        if (core.fsChanges() !== fsSeen) {
            fsSeen = core.fsChanges();
            storeFiles(core);
        }
    }
    function rememberInvert() {
        if (core.invertVertical() !== invert) {
            invert = core.invertVertical();
            writeSetting('invertVertical', invert ? '1' : '0');
        }
    }
    /* The stereo width is the owner's too (SPEC 6.5): remembered, and 1 - the Amiga's hard
       left and right - until changed. */
    let width = Number(readSetting('stereoWidth'));
    if (!STEREO_WIDTHS.includes(width)) {
        width = STEREO_WIDTHS[0];
    }
    const audio = createAudio(core, width);
    /* What the page itself went through, for the diagnostics overlay: how often it was
       hidden, for how long the last time, and whether it is in fullscreen. */
    const page = { hides: 0, lastHiddenMs: 0, fullscreen: false };
    const overlay = createOverlay(document.getElementById('overlay'), core, null, audio, input,
                                  video);
    const clock = createClock(core, input, video, audio, (now) => {
        overlay.paint(now);
        checkAudioStarted();
        rememberInvert();
        rememberFiles();
    });

    /* The overlay needs the clock and the clock needs the overlay's paint function; the
       overlay is told about the clock, and about the page record, once both exist. */
    overlay.attach(clock, page);

    const gesture = document.getElementById('gesture');
    const hint = document.getElementById('hint');

    /* One setting, PAL or NTSC, picks the VBlank rate and the pixel aspect together, the way
       a machine has one or the other (SPEC 6.2).  PAL is what the page starts on. */
    function setStandard(name) {
        clock.setHz(video.setStandard(name).hz);
    }
    setStandard('pal');

    /* The hint bar lies over the bottom of the picture, which now fills the window, so it
       does not stay: it goes with the gesture prompt once the page has really been
       activated, and comes back with the diagnostics overlay. */
    let waitingForAudio = true;
    function showOrHideHint() {
        hint.classList.toggle('off', !(waitingForAudio || overlay.visible()));
    }

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
    function checkAudioStarted() {
        if (!waitingForAudio || !audio.ready()) {
            return;
        }
        waitingForAudio = false;
        gesture.classList.add('off');
        showOrHideHint();
        window.removeEventListener('keydown', onGesture);
        window.removeEventListener('pointerdown', onGesture);
    }

    /* The shell's own keys.  Only the diagnostics toggle is always live; everything else
       the shell reads for itself works while the overlay is up, so that a key the game
       wants - a digit typed into a name, say - never goes to the shell instead.  The
       toggle is named by its position, because the character on it differs by keyboard,
       and it is the one printable key the game cannot see. */
    window.addEventListener('keydown', (event) => {
        if (event.code === 'Backquote') {
            overlay.toggle();
            showOrHideHint();
            event.preventDefault();
        } else if (overlay.visible() && event.code === 'Digit5') {
            setStandard('pal');
        } else if (overlay.visible() && event.code === 'Digit6') {
            setStandard('ntsc');
        } else if (overlay.visible() && event.code === 'Digit7') {
            width = STEREO_WIDTHS[(STEREO_WIDTHS.indexOf(width) + 1) % STEREO_WIDTHS.length];
            audio.setWidth(width);
            writeSetting('stereoWidth', String(width));
        } else if (overlay.visible() && event.code === 'Digit1') {
            core.devSetScore(5000);          /* enough to beat the tenth entry */
            event.preventDefault();
        } else if (overlay.visible() && event.code === 'Digit2') {
            core.devOpenDialog(1);           /* the save dialog, at the next rank chosen */
            event.preventDefault();
        } else if (overlay.visible() && event.code === 'Digit3') {
            core.devOpenDialog(0);           /* the load dialog, the same way */
            event.preventDefault();
        }
    });

    /* A hidden page stops (SPEC 6.2, Pause): no animation frame reaches it, so the clock is
       stopped outright and the sound is held, and a mission comes back from a real absence
       paused.  A page can also be hidden for a few milliseconds only and shown again; a
       pause asked for on the way out then stopped the mission and its sound for an absence
       the player never made.  So the pause is asked for on the way back, and only after an
       absence of HIDDEN_PAUSE_MS or more.  No VBlank runs while the page is hidden, so the
       request reaches the same pass as one made on the way out. */
    const HIDDEN_PAUSE_MS = 1000;
    let hiddenSince = document.hidden ? performance.now() : -1;
    page.hides = document.hidden ? 1 : 0;

    document.addEventListener('visibilitychange', () => {
        if (document.hidden) {
            hiddenSince = performance.now();
            page.hides++;
            clock.stop();
            audio.suspend();
        } else {
            if (hiddenSince >= 0) {
                page.lastHiddenMs = performance.now() - hiddenSince;
                if (page.lastHiddenMs >= HIDDEN_PAUSE_MS) {
                    core.requestPause();     /* a mission comes back paused */
                }
            }
            hiddenSince = -1;
            audio.resume();
            clock.start();
        }
    });

    /* Leaving fullscreen asks for the pause (SPEC 6.2, Input): a browser takes Escape to
       leave the fullscreen of an element and a page cannot prevent it.  The browser's own
       fullscreen, the one its window control and menu give, sets no fullscreen element; it
       is followed through the display-mode media query, which Firefox and Chrome match
       there. */
    const fullscreenQuery = window.matchMedia('(display-mode: fullscreen)');
    const inFullscreen = () => fullscreenQuery.matches || !!document.fullscreenElement;
    page.fullscreen = inFullscreen();
    function followFullscreen() {
        const now = inFullscreen();
        if (page.fullscreen && !now) {
            core.requestPause();
        }
        page.fullscreen = now;
    }
    fullscreenQuery.addEventListener('change', followFullscreen);
    document.addEventListener('fullscreenchange', followFullscreen);

    clock.start();
}

boot().catch((err) => fail('start failed: ' + (err && err.message ? err.message : err)));
