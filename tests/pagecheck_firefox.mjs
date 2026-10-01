/* Opens dist/wof.html in Firefox, from a file:// URL, and reports what it finds.
 *
 * The companion to tests/pagecheck.mjs, which does the same in Chrome.  Firefox is worth its
 * own run because its canvas and its autoplay policy differ from Chrome's in ways that have
 * already cost this project a black screen.
 *
 * Headless by default.  With --visible it opens a real window, which is the only way to see
 * the accelerated canvas path: headless Firefox composites in software and therefore cannot
 * reproduce what a person sees.
 *
 *     node tests/pagecheck_firefox.mjs <page.html> [firefox-binary] [--visible]
 *
 * Talks WebDriver BiDi over the WebSocket that Node has built in; nothing is installed for
 * it.  The key press goes through input.performActions rather than a synthesised event, so
 * that it counts as a user gesture and the autoplay policy sees what a person's key press
 * would produce.
 */
import { spawn } from 'node:child_process';
import { existsSync, mkdtempSync, readFileSync, rmSync, writeFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join, resolve } from 'node:path';

import { AUDIO_WATCH } from './audiowatch.mjs';
import { CORE_WATCH, STICK_LOOK } from './corewatch.mjs';
import { FULLSCREEN_LOOK, VISIBILITY_WATCH, fullscreenRun, walkToTheHold } from './pagefullscreen.mjs';
import { DISPLAY, GEOMETRY, PICTURE, PLAYER, PRESENT_COST, SKY_PNG, SOURCE_PNG, VIDEO,
         WEAPON_VIEW, enemyFlight, muteRun, startTheSound, weaponRun } from './pagemeasure.mjs';
import { STATE_WATCH, demoRun, flightLoadRun, saveLoadRun } from './pageload.mjs';

const DEFAULT_FIREFOX = '/Applications/Firefox.app/Contents/MacOS/firefox';
const args = process.argv.slice(2);
const visible = args.includes('--visible');
const positional = args.filter((a) => !a.startsWith('--'));
const pagePath = resolve(positional[0]);
const firefoxPath = positional[1] || process.env.WOF_FIREFOX || DEFAULT_FIREFOX;
const port = 9500 + Math.floor(Math.random() * 400);

const sleep = (ms) => new Promise((done) => setTimeout(done, ms));

const profile = mkdtempSync(join(tmpdir(), 'wof-firefox-'));

/* The page plays the game's sounds, and these runs happen on a machine somebody is working at.
   media.volume_scale turns Firefox's own output down to nothing without touching the page,
   so what is tested is still the shipped configuration: the context runs, the worklet
   backend is the one from the data: URL, and audio is queued.  Chrome is silenced the same
   way from the outside, with --mute-audio. */
writeFileSync(join(profile, 'user.js'), 'user_pref("media.volume_scale", "0.0");\n');

const firefox = spawn(firefoxPath, [
    ...(visible ? [] : ['--headless']),
    '--no-remote',
    '--profile', profile,
    '--remote-debugging-port', String(port),
    '--width', '1400', '--height', '800',
], { stdio: 'ignore' });

let nextId = 0;
const pending = new Map();
const logs = [];
const requests = [];

/* A BiDi command that is never answered would otherwise hang the whole run with nothing to
   say about which one it was, and a visible window does not accept everything a headless one
   does.  Every command is traced and given a deadline; the trace goes to stderr, which is
   what the pytest side prints when the run fails. */
const CALL_TIMEOUT_MS = 30000;
const started = Date.now();

function trace(text) {
    process.stderr.write('[' + ((Date.now() - started) / 1000).toFixed(1) + 's] ' + text + '\n');
}

function send(socket, method, params) {
    const id = ++nextId;
    trace(method);
    socket.send(JSON.stringify({ id, method, params }));
    return new Promise((ok, fail) => {
        const deadline = setTimeout(() => {
            pending.delete(id);
            fail(new Error(method + ' was not answered within ' + CALL_TIMEOUT_MS + ' ms'));
        }, CALL_TIMEOUT_MS);
        pending.set(id, {
            ok: (value) => { clearTimeout(deadline); ok(value); },
            fail: (error) => { clearTimeout(deadline); fail(error); },
        });
    });
}

async function connect() {
    for (let attempt = 0; attempt < 80; attempt++) {
        try {
            const socket = new WebSocket('ws://127.0.0.1:' + port + '/session');
            await new Promise((ok, fail) => {
                socket.addEventListener('open', ok, { once: true });
                socket.addEventListener('error', fail, { once: true });
            });
            return socket;
        } catch {
            await sleep(250);
        }
    }
    throw new Error('Firefox did not open a WebDriver BiDi port');
}

const report = { firefox: firefoxPath, page: pagePath, visible };

try {
    const socket = await connect();
    socket.addEventListener('message', (event) => {
        const message = JSON.parse(event.data);
        if (message.id && pending.has(message.id)) {
            const { ok, fail } = pending.get(message.id);
            pending.delete(message.id);
            message.type === 'error' ? fail(new Error(message.message)) : ok(message.result);
        } else if (message.method === 'log.entryAdded') {
            logs.push({ level: message.params.level, text: message.params.text });
        } else if (message.method === 'network.beforeRequestSent') {
            requests.push(message.params.request.url);
        }
    });

    const session = await send(socket, 'session.new', { capabilities: {} });
    report.browser = (session.capabilities.browserName || 'firefox') + '/' + session.capabilities.browserVersion;
    await send(socket, 'session.subscribe', { events: ['log.entryAdded', 'network.beforeRequestSent'] });

    /* Web Audio must not be touched before the first user gesture.  Firefox's own autoplay
       warning is a browser message that WebDriver does not deliver, so the invariant behind
       it is watched directly instead: the AudioContext constructor and resume are wrapped
       before any page script runs, and each call records whether the page had been
       activated by then. */
    await send(socket, 'script.addPreloadScript', { functionDeclaration: AUDIO_WATCH });

    const tree = await send(socket, 'browsingContext.getTree', {});
    const context = tree.contexts[0].context;

    await send(socket, 'browsingContext.navigate', { context, url: 'file://' + pagePath, wait: 'complete' });
    await sleep(2000);

    /* BiDi serialises objects as remote-value trees, so the page hands back JSON text and
       this side parses it.  The caller writes an ordinary expression. */
    async function evaluateIn(where, expression) {
        const result = await send(socket, 'script.evaluate', {
            expression: 'JSON.stringify(' + expression + ')', target: { context: where }, awaitPromise: true,
        });
        if (result.type === 'exception') {
            throw new Error(result.exceptionDetails.text);
        }
        return JSON.parse(result.result.value);
    }

    const evaluate = (expression) => evaluateIn(context, expression);

    /* WebDriver key codes.  A press through input.performActions is a real event and
       activates the page, where a synthesised KeyboardEvent would not. */
    const KEY_META = '\uE03D';
    const KEY_SPACE = ' ';
    const KEY_BACKQUOTE = '`';
    const KEY_RIGHT = '\uE014';
    const KEY_UP = '\uE013';
    const KEY_DOWN = '\uE015';
    const KEY_FIVE = '5';
    const KEY_SIX = '6';

    function press(where, value) {
        return send(socket, 'input.performActions', {
            context: where,
            actions: [{
                type: 'key',
                id: 'keyboard',
                actions: [{ type: 'keyDown', value }, { type: 'keyUp', value }],
            }],
        });
    }

    /* The two halves of a press, for a key that has to stay down while something is read.
       The key stays down between calls because both name the same input source. */
    function keyAction(where, type, value) {
        return send(socket, 'input.performActions', {
            context: where,
            actions: [{ type: 'key', id: 'keyboard', actions: [{ type, value }] }],
        });
    }

    /* What the console holds before anything has been pressed: an autoplay warning here
       would mean the shell touched Web Audio on its own. */
    report.logsBeforeKey = logs.slice();
    report.audioBeforeKey = await evaluate('window.__wofAudio');

    /* A fresh page's first key starts the sound and does nothing else: the help screen takes
       it (pagemeasure.mjs, startTheSound).  The diagnostics key, which the game never sees,
       is that key here; pressed again, it opens the overlay. */
    const soundOn = (tab) => startTheSound(() => press(tab, KEY_BACKQUOTE),
                                           (expression) => evaluateIn(tab, expression), sleep);

    await soundOn(context);
    await press(context, KEY_BACKQUOTE);            /* the overlay */
    await sleep(2500);

    report.audioAfterKey = await evaluate('window.__wofAudio');
    /* The front end runs in real time here, so the page is walked the way a player walks
       it (re/notes/frontend.md): the story scroller is up when the page opens, fire ends it,
       the publisher logo comes up, the title follows, and a second fire skips the rest of
       the sequence to the rank selection. */

    /* The front end moves on its own: a fade changes the picture between one read and the
       next, and a measurement that spans one would be of no picture at all.  This waits
       until two reads running give the same picture, which is what a screen that is up and
       waiting looks like. */
    async function settle(limitMs = 8000) {
        let last = null;
        for (let waited = 0; waited < limitMs; waited += 300) {
            await sleep(300);
            const now = await evaluate(PICTURE);
            if (last && now.hash === last.hash) {
                return now;
            }
            last = now;
        }
        return last;
    }


    /* One VBlank of fire can fall between two of the front end's polls; a player holds a
       key for a tenth of a second, and so does this. */
    async function fire() {
        await keyAction(context, 'keyDown', KEY_SPACE);
        await sleep(250);
        await keyAction(context, 'keyUp', KEY_SPACE);
    }

    report.front = { scroller: await evaluate(PICTURE) };

    await fire();
    /* The logo comes up in a palette of its own and only then fades to the picture's own
       colours, so it is looked at once it has (re/notes/frontend.md's timetable); before it
       the scroller's song fades out, which the game waits for, about two seconds. */
    await sleep(5500);
    report.front.logo = await settle();
    await sleep(3200);
    report.front.title = await settle();

    await fire();
    await sleep(3600);                              /* the title's song fades out first */
    report.front.ranks = await settle();
    report.picture = report.front.ranks;

    /* The rank selection gives up after 1800 rounds, which is 36 seconds on PAL.  A cursor
       move and a move back leave the picture as it was and start the count again. */
    async function keepRanks() {
        await press(context, KEY_DOWN);
        await sleep(400);
        await press(context, KEY_UP);
        await sleep(400);
    }

    report.overlay = await evaluate("document.getElementById('overlay').textContent");
    report.overlayVisible = await evaluate(
        "!document.getElementById('overlay').classList.contains('off')");
    report.gestureHidden = await evaluate(
        "document.getElementById('help').classList.contains('off')");

    /* ----------------------------------------------------------------- the display box
     *
     * SPEC 6.2: the picture is shown in the machine's proportions, as large as the window
     * allows, centred, on whole device pixels.  Measured off the DOM and judged in
     * tests/conftest.py, the same way as in Chrome (tests/pagemeasure.mjs).
     *
     * In the visible run this is the check that a canvas read-back cannot make on its own:
     * the screenshot comes from the compositor, which is where Firefox's accelerated canvas
     * once showed a black picture that every headless test called green.
     */
    async function viewport(width, height) {
        await send(socket, 'browsingContext.setViewport', {
            context, viewport: { width, height },
        });
        await sleep(500);
    }

    async function look(label, withScreenshot) {
        await settle();
        const seen = { label, geometry: await evaluate(GEOMETRY), display: await evaluate(DISPLAY) };
        if (withScreenshot) {
            /* Nothing may lie over the picture: the overlay and the hint bar go away on the
               key that brought them, and come back afterwards. */
            await press(context, KEY_BACKQUOTE);
            await sleep(400);
            seen.hintVisible = await evaluate(
                "!document.getElementById('hint').classList.contains('off')");
            seen.sourcePng = await evaluate(SOURCE_PNG);
            seen.screenshot = (await send(socket, 'browsingContext.captureScreenshot',
                                          { context })).data;
            await press(context, KEY_BACKQUOTE);
            await sleep(400);
        }
        return seen;
    }

    const overlayText = () => evaluate("document.getElementById('overlay').textContent");

    report.hintVisibleWithOverlay = await evaluate(
        "!document.getElementById('hint').classList.contains('off')");

    /* The rank selection rather than the story scroller the page opens on, which is nearly
       all black and would let a canvas that drew nothing but black pass. */
    report.box = { default: await look('default', true) };
    report.box.default.present = await evaluate(PRESENT_COST);
    const windowSize = report.box.default.geometry.window;

    await press(context, KEY_SIX);
    await sleep(1800);
    report.box.ntsc = { label: 'ntsc', geometry: await evaluate(GEOMETRY) };
    report.box.ntsc.overlay = await overlayText();
    report.box.ntsc.display = await evaluate(DISPLAY);

    await press(context, KEY_FIVE);
    await sleep(1800);
    report.box.palAgain = { label: 'pal again', geometry: await evaluate(GEOMETRY) };
    report.box.palAgain.overlay = await overlayText();
    report.box.palAgain.display = await evaluate(DISPLAY);

    /* One resize with a screenshot, which is what the visible run is here for, and two more
       shapes of window to show that the box follows any of them. */
    await viewport(1100, 500);
    report.box.wide = await look('wide', true);
    report.box.wide.present = await evaluate(PRESENT_COST);
    await viewport(600, 860);
    report.box.tall = await look('tall', false);
    await viewport(420, 320);
    report.box.small = await look('small', false);

    /* Large enough that one framebuffer pixel is shown as at least three device pixels in
       each direction, which is what a comparison pixel for pixel needs.  At a real
       devicePixelRatio of 1 that takes a viewport larger than most screens, which a headless
       window can have and a visible one cannot; the tests use whichever look is large
       enough rather than assuming this one is. */
    await viewport(1960, 1250);
    report.box.large = await look('large', true);

    /* Back to the size the window opened at, by asking for it: a null viewport, which is the
       documented way to give the window its own size back, is never answered in a visible
       window and hangs the run. */
    await viewport(windowSize.width, windowSize.height);

    /* The same picture at the window's own size, after everything the run has done to the
       viewport: the box has to come back to where it started. */
    await keepRanks();
    report.box.ranks = await look('ranks', true);

    /* The same pictures on the Canvas 2D path, asked for by ?video=2d (web/video.js): the
       fallback where WebGL is refused or lost, and in a visible window the path the
       putImageData fault lives on.  In a tab of its own, walked to the rank selection, at
       the window's size and at the large viewport. */
    const flatTab = (await send(socket, 'browsingContext.create', { type: 'tab' })).context;
    await send(socket, 'browsingContext.activate', { context: flatTab });
    await send(socket, 'browsingContext.navigate', {
        context: flatTab, url: 'file://' + pagePath + '?video=2d', wait: 'complete',
    });
    await sleep(1500);
    const flatFire = async () => {
        await keyAction(flatTab, 'keyDown', KEY_SPACE);
        await sleep(250);
        await keyAction(flatTab, 'keyUp', KEY_SPACE);
    };
    const flatSettle = async () => {
        let last = null;
        for (let waited = 0; waited < 8000; waited += 300) {
            await sleep(300);
            const now = await evaluateIn(flatTab, PICTURE);
            if (last && now.hash === last.hash) {
                return now;
            }
            last = now;
        }
        return last;
    };
    const flatLook = async (label) => {
        await flatSettle();
        const seen = { label, geometry: await evaluateIn(flatTab, GEOMETRY),
                       display: await evaluateIn(flatTab, DISPLAY),
                       sourcePng: await evaluateIn(flatTab, SOURCE_PNG) };
        seen.screenshot = (await send(socket, 'browsingContext.captureScreenshot',
                                      { context: flatTab })).data;
        return seen;
    };
    await soundOn(flatTab);                         /* the sound; nothing over the picture */
    await sleep(300);
    await flatFire();                               /* the scroller */
    await sleep(8700);                              /* the logo, then the title */
    await flatFire();
    await sleep(3600);
    report.flat = { picture: await flatSettle(), box: {} };
    report.flat.box.default = await flatLook('2d default');
    await send(socket, 'browsingContext.setViewport', {
        context: flatTab, viewport: { width: 1960, height: 1250 } });
    await sleep(500);
    report.flat.box.large = await flatLook('2d large');
    await send(socket, 'browsingContext.setViewport', {
        context: flatTab, viewport: { width: windowSize.width, height: windowSize.height } });
    report.flat.video = await evaluateIn(flatTab, VIDEO);

    /* A modifier on its own is the case that cost a session of silence: Command, pressed to
       open the console, is a keydown that activates nothing.  The page must build no
       AudioContext there and must go on saying that sound is off; the next real key must
       then start it. */
    const modifierTab = (await send(socket, 'browsingContext.create', { type: 'tab' })).context;
    await send(socket, 'browsingContext.activate', { context: modifierTab });
    await send(socket, 'browsingContext.navigate', {
        context: modifierTab, url: 'file://' + pagePath, wait: 'complete',
    });
    await sleep(1500);

    const promptShown = async () => !(await evaluateIn(modifierTab,
        "document.getElementById('help').classList.contains('off')"));

    await press(modifierTab, KEY_META);
    await sleep(800);
    const afterModifier = {
        promptShown: await promptShown(),
        audio: await evaluateIn(modifierTab, 'window.__wofAudio'),
        states: await evaluateIn(modifierTab, 'window.__wofContexts.map((c) => c.state)'),
        events: await evaluateIn(modifierTab, 'window.__wofEvents'),
    };

    await press(modifierTab, KEY_SPACE);
    await sleep(2000);
    const afterSpace = {
        promptShown: await promptShown(),
        audio: await evaluateIn(modifierTab, 'window.__wofAudio'),
        states: await evaluateIn(modifierTab, 'window.__wofContexts.map((c) => c.state)'),
        events: await evaluateIn(modifierTab, 'window.__wofEvents'),
    };

    await press(modifierTab, KEY_BACKQUOTE);
    await sleep(600);
    afterSpace.overlay = await evaluateIn(modifierTab, "document.getElementById('overlay').textContent");

    report.modifierFirst = { afterModifier, afterSpace };

    /* The stick keys, in a tab of their own whose wof_vblank is watched (tests/corewatch.mjs).
       SPEC 6.1: the up key is the stick pushed forward, bit 0 of the raw state; the down key
       is the stick pulled back, bit 1.  The watch is installed for this tab alone. */
    const stickTab = (await send(socket, 'browsingContext.create', { type: 'tab' })).context;
    await send(socket, 'script.addPreloadScript', { functionDeclaration: CORE_WATCH, contexts: [stickTab] });
    await send(socket, 'browsingContext.activate', { context: stickTab });
    await send(socket, 'browsingContext.navigate', {
        context: stickTab, url: 'file://' + pagePath, wait: 'complete',
    });
    await sleep(1500);
    await soundOn(stickTab);
    await press(stickTab, KEY_BACKQUOTE);
    await sleep(800);

    report.stick = {};
    for (const [name, value] of [['up', KEY_UP], ['down', KEY_DOWN]]) {
        await keyAction(stickTab, 'keyDown', value);
        await sleep(300);
        await evaluateIn(stickTab, '(window.__wofRaw.seen = 0, window.__wofRaw.calls = 0)');
        await sleep(500);
        report.stick[name] = await evaluateIn(stickTab, STICK_LOOK);
        await keyAction(stickTab, 'keyUp', value);
        await sleep(400);
    }
    await evaluateIn(stickTab, '(window.__wofRaw.seen = 0, window.__wofRaw.calls = 0)');
    await sleep(500);
    report.stick.released = await evaluateIn(stickTab, STICK_LOOK);

    /* A mission flown from the keyboard with the keys held in real time (M4), in a tab of
       its own: the front end walked to the first rank and through the briefing, then the
       lift, the roll, the take-off and the climb; the pause and its end; the flip, and the
       flip still on after the page is loaded again.  Read off the overlay. */
    const flightTab = (await send(socket, 'browsingContext.create', { type: 'tab' })).context;
    await send(socket, 'browsingContext.activate', { context: flightTab });
    await send(socket, 'browsingContext.navigate', {
        context: flightTab, url: 'file://' + pagePath, wait: 'complete',
    });
    await sleep(1500);
    await evaluateIn(flightTab, "(window.localStorage.removeItem('wof:invertVertical'), 0)");
    const KEY_ENTER = '\uE007';
    const holdIn = (value, ms) => keyAction(flightTab, 'keyDown', value)
        .then(() => sleep(ms)).then(() => keyAction(flightTab, 'keyUp', value));
    const player = () => evaluateIn(flightTab, PLAYER);
    const until = async (test, limitMs, stepMs = 250) => {
        for (let waited = 0; waited < limitMs; waited += stepMs) {
            const now = await player();
            if (now && test(now)) {
                return now;
            }
            await sleep(stepMs);
        }
        return player();
    };
    await soundOn(flightTab);
    await press(flightTab, KEY_BACKQUOTE);          /* the overlay */
    await sleep(800);
    await holdIn(KEY_SPACE, 250);                   /* the scroller */
    await sleep(6600);
    await holdIn(KEY_SPACE, 250);                   /* the title sequence */
    await sleep(4600);                              /* and the fade of its song */
    await press(flightTab, KEY_ENTER);              /* the first rank */
    await sleep(5100);                              /* the music's fade, then the briefing */
    await holdIn(KEY_SPACE, 250);                   /* the briefing */
    /* The first press in the hold comes as soon as the mission scene is there, which is when
       the player's x leaves 0 (step S): the tick does not run the weapon menu for its first
       fifteen ticks, and the keyboard assist keeps the press until it does (src/assist.c). */
    const early = { appeared: await until((p) => p.x !== 0, 15000, 40) };
    const seenAt = Date.now();
    await holdIn(KEY_UP, 100);
    early.tapAfterMs = Date.now() - seenAt - 100;
    await sleep(2500);
    early.after = (await player()).weapon;
    const flight = { hold: await player(), early };
    await sleep(1500);
    /* The weapon menu with the keyboard assist (src/assist.c): three quick taps of the up
       key, a tenth of a second each and a tenth apart, are three steps, which bring the
       weapon type round to where it started, with a step seen on the way; with the flip on,
       up still steps up, which is the weapon type going down.  The flip goes off again, so
       the flip further on starts from the stored value as before. */
    flight.weapon = { before: (await player()).weapon, seen: [] };
    {
        const until = Date.now() + 2000;
        const watching = (async () => {
            while (Date.now() < until) {
                const now = await player();
                if (now) {
                    flight.weapon.seen.push(now.weapon);
                }
                await sleep(30);
            }
        })();
        for (let i = 0; i < 3; i++) {
            await holdIn(KEY_UP, 100);
            await sleep(100);
        }
        await watching;
    }
    flight.weapon.after = (await player()).weapon;
    await press(flightTab, 'v');                    /* the flip; F is fullscreen */
    await sleep(600);
    flight.weapon.flipOn = (await player()).flip;
    await holdIn(KEY_UP, 100);
    await sleep(800);
    flight.weapon.flipped = (await player()).weapon;
    await press(flightTab, 'v');                    /* the flip; F is fullscreen */
    await sleep(600);
    flight.weapon.flipOff = !(await player()).flip;
    await holdIn(KEY_SPACE, 250);                   /* the lift goes up */
    flight.deck = await until((p) => p.deck === 1 && p.y > 30, 6000);
    await keyAction(flightTab, 'keyDown', KEY_RIGHT);
    flight.rolling = await until((p) => p.deck === 1 && p.x >= 7295, 20000, 60);
    await keyAction(flightTab, 'keyDown', KEY_UP);
    flight.air = await until((p) => p.deck === 0, 10000);
    await sleep(200);                               /* low, so that the burst is in view */
    flight.drop = await weaponRun(() => evaluateIn(flightTab, WEAPON_VIEW), player,
                                  () => holdIn(KEY_SPACE, 80), () => holdIn(KEY_SPACE, 1500),
                                  sleep);
    flight.climb1 = await player();
    await sleep(1500);
    flight.climb2 = await player();
    /* M8: the engine, the guns and the burst have played by now (the overlay's pcm line). */
    flight.pcm = await evaluateIn(flightTab, "document.getElementById('overlay').textContent");
    await keyAction(flightTab, 'keyUp', KEY_UP);
    await keyAction(flightTab, 'keyUp', KEY_RIGHT);
    flight.mute = await muteRun(() => press(flightTab, 'm'),
                                () => evaluateIn(flightTab, "document.getElementById('overlay').textContent"),
                                sleep);
    await press(flightTab, 'p');
    await sleep(600);
    flight.paused1 = await player();
    await sleep(1500);
    flight.paused2 = await player();
    await press(flightTab, 'p');
    await sleep(600);
    flight.running1 = await player();
    await sleep(1500);
    flight.running2 = await player();
    await press(flightTab, 'v');                    /* the flip; F is fullscreen */
    await sleep(800);
    flight.flipped = await player();
    await send(socket, 'browsingContext.reload', { context: flightTab, wait: 'complete' });
    await sleep(1500);
    await soundOn(flightTab);
    await press(flightTab, KEY_BACKQUOTE);
    await sleep(800);
    flight.afterReload = {
        stored: await evaluateIn(flightTab, "window.localStorage.getItem('wof:invertVertical')"),
        player: await player(),
    };
    report.flight = flight;

    /* M6: an enemy aircraft on the page, in a tab of its own: the front end walked to the
       rank selection, the cursor one rank down and Enter, the briefing, and then map d's
       airfield flown to from the hold (pagemeasure.mjs, enemyFlight). */
    const enemyTab = (await send(socket, 'browsingContext.create', { type: 'tab' })).context;
    await send(socket, 'browsingContext.activate', { context: enemyTab });
    /* M8: this flight plays its sounds through the fallback, the scheduled buffers. */
    await send(socket, 'browsingContext.navigate', {
        context: enemyTab, url: 'file://' + pagePath + '?audio=buffers', wait: 'complete',
    });
    await sleep(1500);
    /* The flight above left the flip stored, and the shell takes it when the page loads. */
    await evaluateIn(enemyTab, "(window.localStorage.removeItem('wof:invertVertical'), 0)");
    await send(socket, 'browsingContext.reload', { context: enemyTab, wait: 'complete' });
    await sleep(1500);
    const KEY_LEFT = '\uE012';
    const byName = { space: KEY_SPACE, left: KEY_LEFT, right: KEY_RIGHT, up: KEY_UP,
                     down: KEY_DOWN };
    const enemyKeys = {
        down: (name) => keyAction(enemyTab, 'keyDown', byName[name]),
        up: (name) => keyAction(enemyTab, 'keyUp', byName[name]),
        tap: async (name, ms) => {
            await keyAction(enemyTab, 'keyDown', byName[name]);
            await sleep(ms);
            await keyAction(enemyTab, 'keyUp', byName[name]);
        },
    };
    await soundOn(enemyTab);
    await press(enemyTab, KEY_BACKQUOTE);            /* the overlay */
    await sleep(800);
    await enemyKeys.tap('space', 250);               /* the scroller */
    await sleep(6600);
    await enemyKeys.tap('space', 250);               /* the title sequence */
    await sleep(4600);                               /* and the fade of its song */
    await press(enemyTab, KEY_DOWN);                 /* the second rank */
    await sleep(400);
    await press(enemyTab, KEY_ENTER);
    await sleep(5100);                               /* the music's fade, then the briefing */
    await enemyKeys.tap('space', 250);               /* the briefing */
    const enemyPlayer = () => evaluateIn(enemyTab, PLAYER);
    for (let waited = 0; waited < 20000; waited += 100) {
        const p = await enemyPlayer();
        if (p && p.x !== 0) {
            break;
        }
        await sleep(100);
    }
    await sleep(1500);
    report.enemy = await enemyFlight(enemyKeys, enemyPlayer,
                                     () => evaluateIn(enemyTab, SKY_PNG), sleep);
    report.enemy.overlay = await evaluateIn(enemyTab,
        "document.getElementById('overlay').textContent");

    /* Fullscreen, and a page hidden for a moment (pagefullscreen.mjs), in a tab of its own
       whose VBlanks are counted (tests/corewatch.mjs).  It comes last: in a visible window
       whose screen is locked, macOS cannot bring the window into its fullscreen space, and
       Firefox then reports the page hidden until the window is closed. */
    const fullTab = (await send(socket, 'browsingContext.create', { type: 'tab' })).context;
    for (const watch of [CORE_WATCH, VISIBILITY_WATCH]) {
        await send(socket, 'script.addPreloadScript', { functionDeclaration: watch, contexts: [fullTab] });
    }
    await send(socket, 'browsingContext.activate', { context: fullTab });
    await send(socket, 'browsingContext.navigate', {
        context: fullTab, url: 'file://' + pagePath, wait: 'complete',
    });
    await sleep(1500);
    await evaluateIn(fullTab, "(window.localStorage.removeItem('wof:invertVertical'), 0)");
    await send(socket, 'browsingContext.reload', { context: fullTab, wait: 'complete' });
    await sleep(1500);
    const fullKeys = { backquote: KEY_BACKQUOTE, space: KEY_SPACE, enter: KEY_ENTER, p: 'p',
                       escape: '\uE00C' };
    const fullTap = async (name, ms = 80) => {
        await keyAction(fullTab, 'keyDown', fullKeys[name]);
        await sleep(ms);
        await keyAction(fullTab, 'keyUp', fullKeys[name]);
    };
    const fullEvaluate = (expression) => evaluateIn(fullTab, expression);
    const walked = await walkToTheHold({ tap: fullTap, evaluate: fullEvaluate },
                                       () => fullEvaluate(PLAYER), sleep,
                                       () => fullEvaluate(FULLSCREEN_LOOK));
    /* The tab put in front for a while is a blank one; the page's own tab comes back. */
    const blankTab = (await send(socket, 'browsingContext.create', { type: 'tab', background: true })).context;
    let fullViewport = null;                        /* the tab's own size, before a small one */
    const clientWindow = async () => (await send(socket, 'browser.getClientWindows', {})).clientWindows[0];
    const windowState = async (state) => {
        const answer = await send(socket, 'browser.setClientWindowState', {
            clientWindow: (await clientWindow()).clientWindow, state,
        });
        return { state: answer.state, width: answer.width, height: answer.height };
    };
    report.fullscreen = await fullscreenRun({
        look: () => evaluateIn(fullTab, FULLSCREEN_LOOK),
        tap: fullTap,
        sleep,
        flip: async (ms) => {
            await send(socket, 'browsingContext.activate', { context: blankTab });
            if (ms) {
                await sleep(ms);
            }
            await send(socket, 'browsingContext.activate', { context: fullTab });
        },
        /* The browser's own fullscreen, the kind the owner used, by the driver's
           window-state command: a page cannot ask for it, and Firefox refuses an element's
           fullscreen to a window it drives, which never holds the focus. */
        enter: () => windowState('fullscreen'),
        leave: () => windowState('normal'),
        geometry: () => evaluateIn(fullTab, GEOMETRY),
        viewport: async (width, height) => {
            if (width !== null && !fullViewport) {
                fullViewport = await evaluateIn(fullTab, '[innerWidth, innerHeight]');
            }
            const [w, h] = width === null ? fullViewport : [width, height];
            await send(socket, 'browsingContext.setViewport', {
                context: fullTab, viewport: { width: w, height: h },
            });
        },
    });
    report.fullscreen.hold = walked.hold;
    report.fullscreen.outside = walked.outside;

    /* M7 part 2 (tests/pageload.mjs), in a tab of its own: a game saved on the carrier and
       loaded after a reload from the rank selection, the same save loaded with L in flight,
       and a demo recorded with the overlay's key 4, played after a reload and again. */
    const loadTab = (await send(socket, 'browsingContext.create', { type: 'tab' })).context;
    await send(socket, 'script.addPreloadScript', { functionDeclaration: STATE_WATCH, contexts: [loadTab] });
    await send(socket, 'browsingContext.activate', { context: loadTab });
    await send(socket, 'browsingContext.navigate', {
        context: loadTab, url: 'file://' + pagePath, wait: 'complete',
    });
    await sleep(1500);
    const loadKeys = { backquote: KEY_BACKQUOTE, space: KEY_SPACE, enter: KEY_ENTER, up: KEY_UP,
                       down: KEY_DOWN, right: KEY_RIGHT, keyG: 'g', keyL: 'l', keyP: 'p',
                       keyR: 'r', keyA: 'a', keyB: 'b', keyC: 'c', four: '4', p: 'p' };
    report.loadLogsBefore = logs.length;
    const loadDriver = {
        tap: async (name, ms = 80) => {
            await keyAction(loadTab, 'keyDown', loadKeys[name]);
            await sleep(ms);
            await keyAction(loadTab, 'keyUp', loadKeys[name]);
        },
        hold: (name) => keyAction(loadTab, 'keyDown', loadKeys[name]),
        release: (name) => keyAction(loadTab, 'keyUp', loadKeys[name]),
        sleep,
        evaluate: (expression) => evaluateIn(loadTab, expression),
        reload: async () => {
            await send(socket, 'browsingContext.reload', { context: loadTab, wait: 'complete' });
            await sleep(1500);
        },
    };
    report.saveLoad = await saveLoadRun(loadDriver);
    report.flightLoad = await flightLoadRun(loadDriver);
    report.demo = await demoRun(loadDriver);

    /* Which renderer drew each page of the run (web/video.js), with its reason for a
       fallback: every one but the 2D tab's is meant to be WebGL.  The blank tab has none. */
    report.video = [];
    for (const tab of (await send(socket, 'browsingContext.getTree', {})).contexts) {
        try {
            report.video.push({ url: tab.url.replace(/^.*\//, ''),
                                ...(await evaluateIn(tab.context, VIDEO)) });
        } catch {
            report.video.push({ url: tab.url, path: null });
        }
    }
} catch (err) {
    report.error = err && err.message ? err.message : String(err);
} finally {
    report.logs = logs.slice();
    report.requests = requests.slice();
    firefox.kill();
    await sleep(300);
    /* Firefox writes the preferences it is holding when it shuts down, so this says whether
       the profile really took the one that silences it. */
    const prefs = join(profile, 'prefs.js');
    report.volumeScale = existsSync(prefs)
        ? (readFileSync(prefs, 'utf8').match(/^user_pref\("media\.volume_scale".*$/m) || [null])[0]
        : null;
    rmSync(profile, { recursive: true, force: true });
}

process.stdout.write(JSON.stringify(report, null, 1));
if (report.error) {
    process.exitCode = 1;
}
