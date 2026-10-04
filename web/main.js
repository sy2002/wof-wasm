/* Shell entry point: decode the two payloads the build inlined, start the core, wire the
   clock, video, input, audio and the diagnostics overlay together. */

import { loadCore } from './core.js';
import { createVideo } from './video.js';
import { createInput, DIAGNOSTIC_CODES } from './input.js';
import { createAudio, STEREO_WIDTHS } from './audio.js';
import { createClock } from './clock.js';
import { createOverlay } from './overlay.js';

/* The seed of the core's entropy stream, the beam positions the port's rand_beam takes where
   the original reads the raster beam (re/notes/random.md).  It is fixed, so every visit
   starts the same stream.  A recorded demo keeps the stream's state at its start in its
   seed file, wofdemo.seed, and its playback starts from that (re/notes/demo.md). */
const SEED = 0x57494e47;

/* Keys that are only ever held with another one: they are no key of their own, so they
   neither start the sound nor take the help screen away. */
const MODIFIER_KEYS = new Set([
    'Meta', 'Control', 'Alt', 'AltGraph', 'Shift', 'CapsLock',
    'NumLock', 'ScrollLock', 'Fn', 'FnLock', 'Hyper', 'Super', 'Symbol', 'SymbolLock',
]);

/* Keys that produce no character and therefore no user activation. */
const INERT_KEYS = new Set([...MODIFIER_KEYS, 'Dead']);

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
    document.getElementById('help').classList.add('off');   /* no key will start anything */
    const hint = document.getElementById('hint');
    hint.textContent = message;
    hint.style.color = '#ff8080';
    hint.classList.remove('off');
}

async function boot() {
    const wasm = decodeBase64(document.getElementById('wof-wasm').textContent);
    const blob = decodeBase64(document.getElementById('wof-fs').textContent);

    const core = await loadCore(wasm, blob, SEED);
    const video = createVideo(document.getElementById('screen'), core,
                              document.getElementById('paused'), document.getElementById('help'));
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
        video.noteFrame(now);                            /* the frame interval, for the overlay */
        video.showPaused(core.paused() && !helpShown);   /* the pause sign, after the VBlanks */
        overlay.paint(now);
        checkAudioStarted();
        rememberInvert();
        rememberFiles();
        checkExit();
    });

    /* The overlay needs the clock and the clock needs the overlay's paint function; the
       overlay is told about the clock, and about the page record, once both exist. */
    overlay.attach(clock, page);

    const help = document.getElementById('help');
    const hint = document.getElementById('hint');

    /* One setting, PAL or NTSC, picks the VBlank rate and the pixel aspect together, the way
       a machine has one or the other (SPEC 6.2).  PAL is what the page starts on. */
    function setStandard(name) {
        clock.setHz(video.setStandard(name).hz);
    }
    setStandard('pal');

    /* The hint bar lies over the bottom of the picture, which fills the window, so it is
       there only with the diagnostics overlay, whose key it names. */
    function showOrHideHint() {
        hint.classList.toggle('off', !overlay.visible());
    }

    /* The help screen (SPEC 6.2).  It is up when the page opens, in place of a prompt for
       sound, and goes by that prompt's rule: when the sound is really running.  The key that
       starts the sound is the shell's and does nothing else.  After that H brings it back,
       except in the line editor, where H is a letter; while it is up any key takes it away,
       and that key is the shell's too.  Over a running mission it asks for the pause and ends that pause when it
       goes; a pause it did not ask for - P, Escape, an absence, fullscreen left - stays, with
       its sign, when it goes.  Outside a mission the game runs on beneath it. */
    let waitingForAudio = true;
    let helpShown = true;
    let helpPaused = false;

    function openHelp() {
        helpShown = true;
        helpPaused = !core.paused();
        if (helpPaused) {
            core.requestPause();                 /* dropped outside a mission */
        }
        video.showHelp(true);
    }

    function closeHelp() {
        helpShown = false;
        video.showHelp(false);
        if (helpPaused) {
            helpPaused = false;
            core.requestContinue();              /* dropped outside a mission */
        }
    }

    /* The dialog's "Exit Game" ends the program on the machine; here it starts it again, as
       a reload of the page (SPEC 6.2): the game begins at the story scroller, and the saved
       games and the high scores stay, because they live in the browser's storage and were
       written there on the frame the game wrote them (rememberFiles, just before). */
    let exiting = false;
    function checkExit() {
        if (!exiting && core.exitRequested()) {
            exiting = true;
            window.location.reload();
        }
    }

    /* The page's own fullscreen, on the root element so that the picture and everything the
       shell lays over it stay in it.  F asks for it and F in it leaves it; the request is
       made in the keydown's own task, because a browser grants it only to a gesture.
       Leaving by either way asks for the pause (followFullscreen, below). */
    function toggleFullscreen() {
        if (document.fullscreenElement) {
            document.exitFullscreen().catch(() => undefined);
        } else if (document.documentElement.requestFullscreen) {
            document.documentElement.requestFullscreen().catch(() => undefined);
        }
    }

    /* Escape in the page's fullscreen leaves it, which a browser insists on, and the game is
       paused by the leave rule; the same key must not reach the game as its pause toggle,
       which would continue it again.  So an Escape pressed in the page's fullscreen is
       dropped, and so is one that arrives just after the page's fullscreen ended, for a
       browser that leaves first and hands the key over afterwards. */
    const ESCAPE_AFTER_LEAVE_MS = 500;
    let elementFullscreenLeftAt = -Infinity;
    let hadFullscreenElement = false;
    document.addEventListener('fullscreenchange', () => {
        if (hadFullscreenElement && !document.fullscreenElement) {
            elementFullscreenLeftAt = performance.now();
        }
        hadFullscreenElement = !!document.fullscreenElement;
        /* No mouse cursor in the page's own fullscreen: the page has nothing to click and
           every input is the keyboard (web/style.css).  The browser's fullscreen keeps it. */
        document.documentElement.classList.toggle('page-fullscreen', hadFullscreenElement);
    });
    function escapeLeavesFullscreen(event) {
        return event.code === 'Escape'
            && (!!document.fullscreenElement
                || performance.now() - elementFullscreenLeftAt < ESCAPE_AFTER_LEAVE_MS);
    }

    /* A pause the page asks for itself is the player's to end, even under the help screen. */
    function requestPauseFromPage() {
        helpPaused = false;
        core.requestPause();
    }

    /* Ahead of every other key listener of the page, in the capture phase: a key the shell
       takes here - the Escape that leaves fullscreen, every key while the help screen is up,
       H and F - goes no further, neither to the game nor to the shell's other keys.  A key
       held with Control, Alt or Command is the browser's, and a repeat is not a press.
       While the help screen is up at the start, the key starts the sound and does nothing
       else; the screen goes once the sound runs (checkAudioStarted), so a key that cannot
       start it, a dead key say, leaves the screen up for the next one.  While it is up after
       that, the key takes it away.  In the line editor H and F are letters. */
    window.addEventListener('keydown', (event) => {
        if (MODIFIER_KEYS.has(event.key) || event.ctrlKey || event.altKey || event.metaKey) {
            return;
        }
        if (escapeLeavesFullscreen(event)) {
            /* nothing: the browser leaves fullscreen and the leave rule pauses */
        } else if (waitingForAudio) {
            if (!event.repeat) {
                onGesture(event);                /* its listener below does not see this key */
            }
        } else if (helpShown) {
            if (!event.repeat) {
                closeHelp();
            }
        } else if (event.code === 'KeyH' && !core.lineEditorActive()) {
            if (!event.repeat) {
                openHelp();
            }
        } else if (event.code === 'KeyF' && !core.lineEditorActive()) {
            if (!event.repeat) {
                toggleFullscreen();
            }
        } else {
            return;
        }
        event.preventDefault();
        event.stopImmediatePropagation();
    }, true);

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

    /* The help screen's line about the sound is a statement about the sound, so the screen
       goes when the sound is really there, not when some event has been seen.  The
       listeners go at the same moment, and from then on the screen speaks of the game. */
    function checkAudioStarted() {
        if (!waitingForAudio || !audio.ready()) {
            return;
        }
        waitingForAudio = false;
        closeHelp();
        help.classList.remove('start');
        window.removeEventListener('keydown', onGesture);
        window.removeEventListener('pointerdown', onGesture);
    }

    /* The shell's own keys.  Only the diagnostics toggle is always live; everything else
       the shell reads for itself works while the overlay is up, so that a key the game
       wants - a digit typed into a name, say - never goes to the shell instead.  The
       toggle is named by its position, because the character on it differs by keyboard; it
       arrives with either of two codes (DIAGNOSTIC_CODES, web/input.js), and the game sees
       neither. */
    window.addEventListener('keydown', (event) => {
        if (DIAGNOSTIC_CODES.has(event.code)) {
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
        } else if (overlay.visible() && event.code === 'Digit4') {
            core.devDemoRecord(core.demoRecording() === 0);   /* main's argument, on or off */
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
                    requestPauseFromPage();  /* a mission comes back paused */
                }
            }
            hiddenSince = -1;
            audio.resume();
            video.restartFrames();                   /* the time away is no frame */
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
            requestPauseFromPage();
        }
        page.fullscreen = now;
    }
    fullscreenQuery.addEventListener('change', followFullscreen);
    document.addEventListener('fullscreenchange', followFullscreen);

    clock.start();
}

boot().catch((err) => fail('start failed: ' + (err && err.message ? err.message : err)));
