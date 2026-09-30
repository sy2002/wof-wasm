/* Opens dist/wof.html in headless Chrome, from a file:// URL, and reports what it finds.
 *
 * This is the part of the M0 acceptance criteria that needs a browser: the page has to run
 * from a double click, draw the test pattern, hold a steady emulated 60 Hz and ask the
 * network for nothing.  Everything is read back through the page's own diagnostics overlay
 * and through the canvas, so the instrument is the same one a person would use.
 *
 * Whether the sound is right to the ear is the one thing left for a person.
 *
 *     node tests/pagecheck.mjs <page.html> [chrome-binary]
 *
 * Talks the DevTools protocol through tests/chrome.mjs, over the WebSocket that Node has
 * built in; nothing is installed for it.
 */
import { resolve } from 'node:path';

import { AUDIO_WATCH } from './audiowatch.mjs';
import { DEFAULT_CHROME, sleep, startChrome, stopChrome } from './chrome.mjs';
import { CORE_WATCH, STICK_LOOK } from './corewatch.mjs';
import { FULLSCREEN_LOOK, VISIBILITY_WATCH, fullscreenRound, fullscreenRun,
         walkToTheHold } from './pagefullscreen.mjs';
import { DISPLAY, GEOMETRY, PICTURE, PLAYER, PRESENT_COST, SKY_PNG, STORED_FILES, VIDEO, WEAPON_VIEW,
         enemyFlight, muteRun, weaponRun } from './pagemeasure.mjs';
import { STATE_WATCH, demoRun, flightLoadRun, saveLoadRun } from './pageload.mjs';

const pagePath = resolve(process.argv[2]);

const HELP_SHOWN = "!document.getElementById('help').classList.contains('off')";
const SIGN_SHOWN = "!document.getElementById('paused').classList.contains('off')";
const chromePath = process.argv[3] || process.env.WOF_CHROME || DEFAULT_CHROME;

const report = { chrome: chromePath, page: pagePath, requests: [], console: [], help: {} };

const browser = await startChrome(chromePath, ['--window-size=1280,900']);
const cdp = browser.cdp;
report.browser = browser.browser;

try {
    const { targetId } = await cdp.send('Target.createTarget', { url: 'about:blank' });
    const { sessionId } = await cdp.send('Target.attachToTarget', { targetId, flatten: true });

    /* Requests and errors are kept per page, because a second page is opened further down
       and neither one's traffic may be read as the other's. */
    const channels = new Map();
    const channel = (id) => {
        if (!channels.has(id)) {
            channels.set(id, { requests: [], console: [] });
        }
        return channels.get(id);
    };

    cdp.on((message) => {
        const sink = channel(message.sessionId);
        if (message.method === 'Network.requestWillBeSent') {
            sink.requests.push(message.params.request.url);
        } else if (message.method === 'Runtime.exceptionThrown') {
            const detail = message.params.exceptionDetails;
            sink.console.push('exception: ' + (detail.exception?.description || detail.text));
        } else if (message.method === 'Runtime.consoleAPICalled' && message.params.type === 'error') {
            sink.console.push('console.error: ' + message.params.args.map((a) => a.value).join(' '));
        } else if (message.method === 'Log.entryAdded' && message.params.entry.level === 'error') {
            sink.console.push('log: ' + message.params.entry.text);
        }
    });

    /* Every page this run opens, so that each can say at the end which renderer drew it. */
    const opened = [];

    async function open(session, url, watches = []) {
        opened.push({ session, url });
        for (const domain of ['Page.enable', 'Runtime.enable', 'Log.enable', 'Network.enable']) {
            await cdp.send(domain, {}, session);
        }
        for (const watch of [AUDIO_WATCH, ...watches]) {
            await cdp.send('Page.addScriptToEvaluateOnNewDocument',
                           { source: '(' + watch + ')();' }, session);
        }
        await cdp.send('Page.bringToFront', {}, session);
        await cdp.send('Page.navigate', { url }, session);
        await sleep(1500);
    }

    const press = (session, name) => cdp.press(session, name);
    const evaluateIn = (session, expression) => cdp.evaluate(session, expression);
    const evaluate = (expression) => evaluateIn(sessionId, expression);

    await open(sessionId, 'file://' + pagePath);

    report.audioBeforeKey = await evaluate('window.__wofAudio');

    /* The same keypress opens the overlay and is the gesture that starts the audio. */
    await press(sessionId, 'backquote');
    await sleep(2000);
    report.audioAfterKey = await evaluate('window.__wofAudio');

    /* The front end runs in real time here, so the page is walked the way a player walks
       it (re/notes/frontend.md): the story scroller is up when the page opens, fire ends
       it, the publisher logo comes up and fades in, the title follows it, and a second
       fire skips the rest of the sequence to the rank selection.  The waits below are the
       note's timetable in seconds at 50 Hz, with room for the fades. */

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


    /* The front end polls the button once a pass, and a keyDown immediately followed by a
       keyUp is one VBlank wide: it can fall between two polls.  A player holds a key for a
       tenth of a second, so the fire presses here do too. */
    async function fire() {
        await cdp.hold(sessionId, 'space');
        await sleep(250);
        await cdp.release(sessionId, 'space');
    }

    report.front = { scroller: await evaluate(PICTURE) };

    await fire();                                    /* end the scroller */
    /* The logo comes up in a palette of its own and only then fades to the picture's own
       colours, so it is looked at once it has (re/notes/frontend.md's timetable); before it
       the scroller's song fades out, which the game waits for, about two seconds. */
    await sleep(5500);
    report.front.logo = await settle();
    await sleep(3200);
    report.front.title = await settle();

    await fire();                                    /* skip to the rank selection */
    await sleep(3600);                               /* the title's song fades out first */
    report.front.ranks = await settle();
    report.picture = report.front.ranks;

    /* The rank selection gives up after 1800 rounds, which is 36 seconds on PAL, and the
       measurements below take longer than that.  A cursor move and a move back leave the
       picture exactly as it was and start menu_input's count again. */
    async function keepRanks() {
        await press(sessionId, 'down');
        await sleep(400);
        await press(sessionId, 'up');
        await sleep(400);
    }

    report.overlay = await evaluate("document.getElementById('overlay').textContent");
    report.overlayVisible = await evaluate(
        "!document.getElementById('overlay').classList.contains('off')");
    report.gestureHidden = await evaluate(
        "document.getElementById('help').classList.contains('off')");
    report.hint = await evaluate("document.getElementById('hint').textContent");

    /* ----------------------------------------------------------------- the display box
     *
     * SPEC 6.2: the picture is shown in the machine's proportions, as large as the window
     * allows, centred, on whole device pixels.  Everything here is measured off the DOM -
     * getBoundingClientRect, the backing store, innerWidth, devicePixelRatio - and judged in
     * tests/conftest.py.  What the shell says about its own geometry travels along for a
     * failure message and is never what an assertion reads.
     */
    async function viewport(width, height, deviceScaleFactor) {
        await cdp.send('Emulation.setDeviceMetricsOverride',
                       { width, height, deviceScaleFactor, mobile: false }, sessionId);
        await sleep(400);
    }

    /* A canvas read back is not what the compositor puts on the screen; a screenshot is.
       Nothing may lie over the picture while the two are compared, and the diagnostics
       overlay and the hint bar go away on the same key that brought them. */
    async function look(label, withScreenshot) {
        await settle();
        const seen = { label, geometry: await evaluate(GEOMETRY), display: await evaluate(DISPLAY) };
        if (withScreenshot) {
            await press(sessionId, 'backquote');
            await sleep(300);
            seen.hintVisible = await evaluate(
                "!document.getElementById('hint').classList.contains('off')");
            seen.screenshot = (await cdp.send('Page.captureScreenshot',
                                              { format: 'png' }, sessionId)).data;
            await press(sessionId, 'backquote');
            await sleep(300);
        }
        return seen;
    }

    report.hintVisibleWithOverlay = await evaluate(
        "!document.getElementById('hint').classList.contains('off')");

    /* The rank selection, which has colours all over it, is what the picture on the page is
       compared against; the story scroller the page opens on is nearly all black and would
       let a canvas that drew nothing but black pass. */
    report.box = { default: await look('default', true) };

    /* Key 6 selects NTSC as a whole - the 800 : 642 box and 60 Hz - and key 5 PAL again.
       The overlay's rates are measured over a window of one second, so each standard gets
       longer than that; and the rates are read before the sampling below, which reads whole
       canvases back and blocks the page long enough to show up as a stall. */
    const overlayText = () => evaluate("document.getElementById('overlay').textContent");

    await press(sessionId, 'six');
    await sleep(1800);
    report.box.ntsc = { label: 'ntsc', geometry: await evaluate(GEOMETRY) };
    report.box.ntsc.overlay = await overlayText();
    report.box.ntsc.display = await evaluate(DISPLAY);

    await press(sessionId, 'five');
    await sleep(1800);
    report.box.palAgain = { label: 'pal again', geometry: await evaluate(GEOMETRY) };
    report.box.palAgain.overlay = await overlayText();
    report.box.palAgain.display = await evaluate(DISPLAY);

    /* A wide, a tall and a small viewport, each set through the driver. */
    await keepRanks();
    await viewport(1400, 600, 1);
    report.box.wide = await look('wide', true);
    await viewport(600, 900, 1);
    report.box.tall = await look('tall', true);
    await viewport(420, 320, 1);
    report.box.small = await look('small', false);

    /* A Retina screen: the backing store must be the CSS size times two. */
    await viewport(1280, 900, 2);
    report.box.retina = await look('retina', true);

    /* What the two scaling steps cost at a fullscreen Retina size.  This headless Chrome
       renders in software (--disable-gpu), so the number is an upper bound, not what a
       player's machine does; the clock's own rate at that size is the answer that counts. */
    await viewport(2560, 1440, 2);
    await sleep(2000);
    report.cost = {
        geometry: await evaluate(GEOMETRY),
        present: await evaluate(PRESENT_COST),
        overlay: await overlayText(),
    };

    await cdp.send('Emulation.clearDeviceMetricsOverride', {}, sessionId);
    await sleep(600);

    /* The same picture at the window's own size, after everything the run has done to the
       viewport: the box has to come back to where it started. */
    await keepRanks();
    report.box.ranks = await look('ranks', true);

    /* ------------------------------------ the dialog, the editor and browser storage
     *
     * M3's acceptance: the front end is walked to the save dialog and to the high-score
     * name entry, a name is typed into each, and what the game wrote is read back out of
     * localStorage and then out of a second visit to the page.  The save dialog and the
     * high score have no way in before M4 ports the in-flight commands, so the shell
     * offers one while the diagnostics overlay is up; everything after that is the game's
     * own: the dialog's list, the line editor, the 360 bytes of the high-score file.
     */
    const storage = {};

    /* This page has had other tabs in front of it, and a page that is not visible stops
       its clock (SPEC 6.2); nothing below would move if it stayed that way. */
    await cdp.send('Page.bringToFront', {}, sessionId);
    await sleep(600);

    /* Browser storage outlives a run, so the page is emptied of what an earlier one left:
       what is read back below is then this run's own doing and nothing else's. */
    await evaluate("(() => { try { window.localStorage.removeItem('wof:files'); } catch (e) {} })()");
    storage.before = await evaluate(STORED_FILES);

    /* look() leaves the overlay up, which is what the two development keys need. */
    await press(sessionId, 'one');                  /* a score that beats the tenth entry */
    await press(sessionId, 'two');                  /* the save dialog at the next rank */
    await sleep(300);
    await press(sessionId, 'backquote');            /* the overlay away again */
    await sleep(300);

    await press(sessionId, 'enter');                /* choose the rank under the cursor */
    await sleep(2000);
    storage.dialog = await settle();

    await press(sessionId, 'keyA');                 /* type into the slot's name */
    await sleep(500);
    storage.edited = await evaluate(PICTURE);
    await press(sessionId, 'keyH');                 /* a letter here, not the help */
    await sleep(300);
    storage.helpInEditor = await evaluate(HELP_SHOWN);
    await press(sessionId, 'enter');                /* accept: the saved game is written */
    await sleep(2000);
    storage.afterSave = await evaluate(STORED_FILES);

    /* On through the briefing, which is left to run out by itself, and into the mission,
       which is flown from the keyboard with the keys held in real time (M4): a weapon
       chosen in the hold, the lift up, the roll along the deck and the take-off; the pause
       and the flip; then three aircraft lost to the sea, the game over and the high-score
       entry, where the name goes in.  The player's state is read off the overlay. */
    await press(sessionId, 'backquote');            /* the overlay, for the readings */
    const until = async (test, limitMs, stepMs = 250) => {
        for (let waited = 0; waited < limitMs; waited += stepMs) {
            const now = await evaluate(PLAYER);
            if (now && test(now)) {
                return now;
            }
            await sleep(stepMs);
        }
        return evaluate(PLAYER);
    };
    const holdFor = async (name, ms) => {
        await cdp.hold(sessionId, name);
        await sleep(ms);
        await cdp.release(sessionId, name);
    };
    /* The first press in the hold comes as soon as the mission scene is there, which is when
       the player's x leaves 0 (step S): the tick does not run the weapon menu for its first
       fifteen ticks, and the keyboard assist keeps the press until it does (src/assist.c). */
    const early = { appeared: await until((p) => p.x !== 0, 20000, 40) };
    const seenAt = Date.now();
    await holdFor('up', 100);
    early.tapAfterMs = Date.now() - seenAt - 100;
    await sleep(2500);
    early.after = (await evaluate(PLAYER)).weapon;
    const flight = { hold: await evaluate(PLAYER), early };
    /* The weapon menu with the keyboard assist (src/assist.c): three quick taps of the up
       key, a tenth of a second each and a tenth apart, are three steps, which bring the
       weapon type round to where it started, with a step seen on the way; with the flip on,
       up still steps up, which is the weapon type going down.  The flip goes off again, so
       the flip further on starts from the stored value as before. */
    async function weaponTaps(read, tapUp, flip) {
        const weapon = { before: (await read()).weapon, seen: [] };
        const until = Date.now() + 2000;
        const watching = (async () => {
            while (Date.now() < until) {
                const now = await read();
                if (now) {
                    weapon.seen.push(now.weapon);
                }
                await sleep(30);
            }
        })();
        for (let i = 0; i < 3; i++) {
            await tapUp();
            await sleep(100);
        }
        await watching;
        weapon.after = (await read()).weapon;
        await flip();
        await sleep(600);
        weapon.flipOn = (await read()).flip;
        await tapUp();
        await sleep(800);
        weapon.flipped = (await read()).weapon;
        await flip();
        await sleep(600);
        weapon.flipOff = !(await read()).flip;
        return weapon;
    }
    await sleep(1500);                              /* the menu takes the stick after 15 ticks */
    flight.weapon = await weaponTaps(() => evaluate(PLAYER), () => holdFor('up', 100),
                                     () => press(sessionId, 'keyV'));
    await holdFor('down', 300);                     /* the next weapon, in the hold's menu */
    await sleep(600);
    await fire();                                   /* the lift goes up */
    flight.deck = await until((p) => p.deck === 1 && p.y > 30, 5000);
    /* The roll along the deck, and the stick forward late in it, as the scripts take off
       (tools/pass_observe.py, TAKE_OFF): forward early keeps the tail down (0x025A9C) and
       the aircraft leaves the bow too slow to climb. */
    await cdp.hold(sessionId, 'right');
    flight.rolling = await until((p) => p.deck === 1 && p.x >= 7295, 20000, 60);
    await cdp.hold(sessionId, 'up');
    flight.air = await until((p) => p.deck === 0, 10000);
    await sleep(200);                               /* low, so that the burst is in view */
    flight.drop = await weaponRun(() => evaluate(WEAPON_VIEW), () => evaluate(PLAYER),
                                  () => holdFor('space', 80), () => holdFor('space', 1500),
                                  sleep);
    flight.climb1 = await evaluate(PLAYER);
    await sleep(1500);
    flight.climb2 = await evaluate(PLAYER);
    /* M8: the engine, the guns and the burst have played by now; the overlay's pcm line
       counts the frames of emulated time the shell took and how many were not silent. */
    flight.pcm = await evaluate("document.getElementById('overlay').textContent");
    await cdp.release(sessionId, 'up');
    await cdp.release(sessionId, 'right');
    flight.mute = await muteRun(() => press(sessionId, 'keyM'),
                                () => evaluate("document.getElementById('overlay').textContent"),
                                sleep);

    /* The pause stops the ticks, and the second press lets them run on. */
    await press(sessionId, 'keyP');
    await sleep(600);
    flight.paused1 = await evaluate(PLAYER);
    await sleep(1500);
    flight.paused2 = await evaluate(PLAYER);
    await press(sessionId, 'keyP');
    await sleep(600);
    flight.running1 = await evaluate(PLAYER);
    await sleep(1500);
    flight.running2 = await evaluate(PLAYER);

    /* The help screen over the mission: H pauses a running one, and the key that closes the
       help lets it run on.  That key is P, which would pause again if it reached the game.
       Over a mission P has paused, the help leaves the pause as it was. */
    const helpStep = async (name) => {
        await press(sessionId, name);
        await sleep(600);
        return { help: await evaluate(HELP_SHOWN), sign: await evaluate(SIGN_SHOWN),
                 ...(await evaluate(PLAYER)) };
    };
    report.help.running = { open: await helpStep('keyH'), closed: await helpStep('keyP') };
    await sleep(600);
    report.help.running.later = await evaluate(PLAYER);
    await press(sessionId, 'keyP');
    await sleep(600);
    report.help.paused = { open: await helpStep('keyH'), closed: await helpStep('keyP') };
    await press(sessionId, 'keyP');
    await sleep(600);

    /* Into the sea: the stick back until the aircraft is in the water, then the button,
       which brings the next aircraft after thirty ticks rather than 150. */
    await cdp.hold(sessionId, 'down');
    flight.water1 = await until((p) => p.deck === 6, 15000);
    await cdp.release(sessionId, 'down');
    const nextAircraft = async () => {
        /* The button held until the next aircraft is there; held on, it would send the lift
           straight up, so it is let go and the lift sent up with a press of its own. */
        await cdp.hold(sessionId, 'space');
        const next = await until((p) => p.deck !== 6, 15000);
        await cdp.release(sessionId, 'space');
        await sleep(1500);
        return next;
    };
    flight.second = await nextAircraft();

    /* The flip, which the shell remembers; the next two aircraft are lost without the
       stick's forward and back, so it changes nothing there. */
    await press(sessionId, 'keyV');
    await sleep(600);
    flight.flipped = await evaluate(PLAYER);
    for (const life of ['third', 'end']) {
        if ((await evaluate(PLAYER)).y === 0) {
            await fire();                           /* the lift */
        }
        await until((p) => p.deck === 1 && p.y > 30, 5000);
        await cdp.hold(sessionId, 'right');         /* over the bow and into the sea */
        flight['water_' + life] = await until((p) => p.deck === 6, 40000);
        await cdp.release(sessionId, 'right');
        if (life !== 'end') {
            flight[life] = await nextAircraft();
        }
    }
    report.flight = flight;
    /* The last aircraft is left to go down without the button, which in the name entry
       would accept the line: 150 ticks, then the game is over. */
    await press(sessionId, 'backquote');            /* the overlay away for the entry */
    await sleep(18000);
    storage.entry = await settle();
    for (const key of ['keyA', 'keyB', 'keyA']) {
        await press(sessionId, key);
        await sleep(250);
    }
    await press(sessionId, 'enter');
    await sleep(2500);
    storage.afterEntry = await evaluate(STORED_FILES);
    storage.highScores = await settle();

    /* A second visit to the same page: what the game wrote is still there. */
    const again = (await cdp.send('Target.createTarget', { url: 'about:blank' })).targetId;
    const againSession = (await cdp.send('Target.attachToTarget',
                                         { targetId: again, flatten: true })).sessionId;
    await open(againSession, 'file://' + pagePath);
    await sleep(1500);
    storage.afterReload = await evaluateIn(againSession, STORED_FILES);
    await press(againSession, 'backquote');
    await sleep(800);
    report.flipAfterReload = {
        stored: await evaluateIn(againSession, "window.localStorage.getItem('wof:invertVertical')"),
        player: await evaluateIn(againSession, PLAYER),
    };
    storage.reloadConsole = channel(againSession).console;
    report.storage = storage;

    /* Back to the page this run is about, with its clock running and its overlay up: what
       follows reads the counters off it. */
    await cdp.send('Page.bringToFront', {}, sessionId);
    await sleep(600);
    await press(sessionId, 'backquote');
    await sleep(600);


    /* A stall must not be made up frame for frame: SPEC 6.2 replays at most 24 VBlanks,
       which is the original's queue of six ticks.  The counters come out of the overlay,
       the same place a person would read them. */
    const COUNTERS = `(() => {
        const text = document.getElementById('overlay').textContent;
        const counters = text.match(/counters\\s+(\\d+) vbl\\s+(\\d+) tick\\s+(\\d+) pass/);
        const stalls = text.match(/stalls (\\d+)/);
        return {
            vblanks: +counters[1], ticks: +counters[2], passes: +counters[3], stalls: +stalls[1],
        };
    })()`;

    const STALL_MS = 2500;
    const beforeStall = await evaluate(COUNTERS);
    await evaluate(`(() => { const end = Date.now() + ${STALL_MS}; while (Date.now() < end) {} })()`);
    await sleep(400);
    report.stall = {
        blockedMs: STALL_MS,
        settleMs: 400,
        before: beforeStall,
        after: await evaluate(COUNTERS),
    };

    report.requests = channel(sessionId).requests;
    report.console = channel(sessionId).console;

    /* The scheduled-buffer fallback is what a browser that refuses the worklet falls back
       on, so it is asked for deliberately and checked, rather than only ever being reached
       when something else has already gone wrong. */
    const fallbackTarget = await cdp.send('Target.createTarget', { url: 'about:blank' });
    const fallbackSession = (await cdp.send('Target.attachToTarget', {
        targetId: fallbackTarget.targetId, flatten: true,
    })).sessionId;

    await open(fallbackSession, 'file://' + pagePath + '?audio=buffers');
    await press(fallbackSession, 'backquote');
    await sleep(2000);
    report.fallback = {
        overlay: await evaluateIn(fallbackSession, "document.getElementById('overlay').textContent"),
        requests: channel(fallbackSession).requests,
        console: channel(fallbackSession).console,
    };

    /* A modifier on its own is the case that cost a session of silence: Command, pressed to
       open the console, is a keydown that activates nothing.  The page must build no
       AudioContext there and must go on saying that sound is off; the next real key must
       then start it. */
    const modifierTarget = await cdp.send('Target.createTarget', { url: 'about:blank' });
    const modifierSession = (await cdp.send('Target.attachToTarget', {
        targetId: modifierTarget.targetId, flatten: true,
    })).sessionId;
    await open(modifierSession, 'file://' + pagePath);

    /* The help screen stands in for the prompt for sound, under the same rule. */
    const promptShown = async () => !(await evaluateIn(modifierSession,
        "document.getElementById('help').classList.contains('off')"));
    report.help.atStart = await evaluateIn(modifierSession,
                                           "document.getElementById('help').innerText");

    await press(modifierSession, 'meta');
    await sleep(800);
    const afterModifier = {
        promptShown: await promptShown(),
        audio: await evaluateIn(modifierSession, 'window.__wofAudio'),
        states: await evaluateIn(modifierSession, 'window.__wofContexts.map((c) => c.state)'),
        events: await evaluateIn(modifierSession, 'window.__wofEvents'),
    };

    await press(modifierSession, 'space');
    await sleep(2000);
    const afterSpace = {
        promptShown: await promptShown(),
        audio: await evaluateIn(modifierSession, 'window.__wofAudio'),
        states: await evaluateIn(modifierSession, 'window.__wofContexts.map((c) => c.state)'),
        events: await evaluateIn(modifierSession, 'window.__wofEvents'),
    };

    /* H brings the help screen back and H takes it away; the story scroller reads no key. */
    await press(modifierSession, 'keyH');
    await sleep(300);
    report.help.reopened = await promptShown();
    await press(modifierSession, 'keyH');
    await sleep(300);
    report.help.closedAgain = await promptShown();

    await press(modifierSession, 'backquote');
    await sleep(600);
    afterSpace.overlay = await evaluateIn(modifierSession,
        "document.getElementById('overlay').textContent");

    report.modifierFirst = { afterModifier, afterSpace };

    /* The stick keys, on a page of their own whose wof_vblank is watched (tests/corewatch.mjs).
       SPEC 6.1: the up key is the stick pushed forward, bit 0 of the raw state; the down key
       is the stick pulled back, bit 1.  Each key is held while the overlay's input line and
       the value the clock hands to the core are read, then released. */
    const stickTarget = await cdp.send('Target.createTarget', { url: 'about:blank' });
    const stickSession = (await cdp.send('Target.attachToTarget', {
        targetId: stickTarget.targetId, flatten: true,
    })).sessionId;
    await open(stickSession, 'file://' + pagePath, [CORE_WATCH]);
    await press(stickSession, 'backquote');
    await sleep(600);

    report.stick = {};
    for (const name of ['up', 'down']) {
        await cdp.hold(stickSession, name);
        await sleep(300);
        await evaluateIn(stickSession, 'window.__wofRaw.seen = 0, window.__wofRaw.calls = 0');
        await sleep(500);
        report.stick[name] = await evaluateIn(stickSession, STICK_LOOK);
        await cdp.release(stickSession, name);
        await sleep(400);
    }
    await evaluateIn(stickSession, 'window.__wofRaw.seen = 0, window.__wofRaw.calls = 0');
    await sleep(500);
    report.stick.released = await evaluateIn(stickSession, STICK_LOOK);
    report.stick.console = channel(stickSession).console;

    /* M6: an enemy aircraft on the page, in a session of its own.  The front end walked to
       the rank selection, the cursor one rank down and fire, the briefing, and then map d's
       airfield flown to from the hold (pagemeasure.mjs, enemyFlight). */
    const enemyTarget = await cdp.send('Target.createTarget', { url: 'about:blank' });
    const enemySession = (await cdp.send('Target.attachToTarget', {
        targetId: enemyTarget.targetId, flatten: true,
    })).sessionId;
    /* M8: this flight plays its sounds through the fallback, the scheduled buffers. */
    await open(enemySession, 'file://' + pagePath + '?audio=buffers');
    /* The flight above left the flip stored, and the shell takes it when the page loads. */
    await evaluateIn(enemySession, "(window.localStorage.removeItem('wof:invertVertical'), 0)");
    await cdp.send('Page.reload', {}, enemySession);
    await sleep(1500);
    const enemyKeys = {
        down: (name) => cdp.hold(enemySession, name),
        up: (name) => cdp.release(enemySession, name),
        tap: async (name, ms) => {
            await cdp.hold(enemySession, name);
            await sleep(ms);
            await cdp.release(enemySession, name);
        },
    };
    await press(enemySession, 'backquote');          /* the overlay; also the gesture */
    await sleep(800);
    await enemyKeys.tap('space', 250);               /* the scroller */
    await sleep(6600);
    await enemyKeys.tap('space', 250);               /* the title sequence */
    await sleep(4600);                               /* and the fade of its song */
    await press(enemySession, 'down');               /* the second rank */
    await sleep(400);
    await press(enemySession, 'enter');
    await sleep(5100);                               /* the music's fade, then the briefing */
    await enemyKeys.tap('space', 250);               /* the briefing */
    const enemyPlayer = () => evaluateIn(enemySession, PLAYER);
    for (let waited = 0; waited < 20000; waited += 100) {
        const p = await enemyPlayer();
        if (p && p.x !== 0) {
            break;
        }
        await sleep(100);
    }
    await sleep(1500);
    report.enemy = await enemyFlight(enemyKeys, enemyPlayer,
                                     () => evaluateIn(enemySession, SKY_PNG), sleep);
    report.enemy.console = channel(enemySession).console;
    report.enemy.overlay = await evaluateIn(enemySession,
        "document.getElementById('overlay').textContent");

    /* Fullscreen, and a page hidden for a moment (pagefullscreen.mjs), in a session of its
       own whose VBlanks are counted (tests/corewatch.mjs): the browser's own fullscreen by
       the window-state command, the kind the owner used, and then an element's, which
       Chrome grants to a script run as a user gesture. */
    const fullTarget = await cdp.send('Target.createTarget', { url: 'about:blank' });
    const fullSession = (await cdp.send('Target.attachToTarget', {
        targetId: fullTarget.targetId, flatten: true,
    })).sessionId;
    await open(fullSession, 'file://' + pagePath, [CORE_WATCH, VISIBILITY_WATCH]);
    const fullNames = { backquote: 'backquote', space: 'space', enter: 'enter', p: 'keyP',
                        escape: 'escape' };
    const fullTap = async (name, ms = 80) => {
        await cdp.hold(fullSession, fullNames[name]);
        await sleep(ms);
        await cdp.release(fullSession, fullNames[name]);
    };
    const walked = await walkToTheHold({ tap: fullTap }, () => evaluateIn(fullSession, PLAYER),
                                       sleep, () => evaluateIn(fullSession, FULLSCREEN_LOOK));
    /* The tab put in front for a while is a blank one; the page's own comes back. */
    const blankTarget = await cdp.send('Target.createTarget', { url: 'about:blank', background: true });
    const { windowId } = await cdp.send('Browser.getWindowForTarget', { targetId: fullTarget.targetId });
    const windowState = async (state) => {
        await cdp.send('Browser.setWindowBounds', { windowId, bounds: { windowState: state } });
        const { bounds } = await cdp.send('Browser.getWindowBounds', { windowId });
        return { state: bounds.windowState, width: bounds.width, height: bounds.height };
    };
    const asGesture = async (expression) => (await cdp.send('Runtime.evaluate', {
        expression, awaitPromise: true, userGesture: true, returnByValue: true,
    }, fullSession)).result.value;
    const fullDriver = {
        look: () => evaluateIn(fullSession, FULLSCREEN_LOOK),
        tap: fullTap,
        sleep,
        geometry: () => evaluateIn(fullSession, GEOMETRY),
        flip: async (ms) => {
            await cdp.send('Target.activateTarget', { targetId: blankTarget.targetId });
            if (ms) {
                await sleep(ms);
            }
            await cdp.send('Target.activateTarget', { targetId: fullTarget.targetId });
        },
        enter: () => windowState('fullscreen'),
        leave: () => windowState('normal'),
        viewport: (width, height) => (width === null
            ? cdp.send('Emulation.clearDeviceMetricsOverride', {}, fullSession)
            : cdp.send('Emulation.setDeviceMetricsOverride',
                       { width, height, deviceScaleFactor: 0, mobile: false }, fullSession)),
    };
    report.fullscreen = await fullscreenRun(fullDriver);
    report.fullscreen.hold = walked.hold;
    report.fullscreen.outside = walked.outside;
    /* Escape through the protocol reaches the page as a key but leaves no fullscreen, so the
       element's fullscreen is left by exitFullscreen, which is what Escape does. */
    report.fullscreenElement = await fullscreenRound({
        ...fullDriver,
        enter: async () => ({ state: await asGesture(
            "document.documentElement.requestFullscreen().then(() => 'fullscreen', (e) => 'refused: ' + e.message)") }),
        leave: async () => ({ state: await evaluateIn(fullSession,
            "document.exitFullscreen().then(() => 'normal', (e) => 'refused: ' + e.message)") }),
    });
    report.fullscreen.console = channel(fullSession).console;

    /* M7 part 2 (tests/pageload.mjs), in a page of its own: a game saved on the carrier and
       loaded after a reload from the rank selection, the same save loaded with L in flight,
       and a demo recorded with the overlay's key 4, played after a reload and again. */
    const loadTarget = await cdp.send('Target.createTarget', { url: 'about:blank' });
    const loadSession = (await cdp.send('Target.attachToTarget', {
        targetId: loadTarget.targetId, flatten: true,
    })).sessionId;
    await open(loadSession, 'file://' + pagePath, [STATE_WATCH]);
    const loadNames = { backquote: 'backquote', space: 'space', enter: 'enter', up: 'up',
                        down: 'down', right: 'right', keyG: 'keyG', keyL: 'keyL', keyP: 'keyP',
                        keyR: 'keyR', keyA: 'keyA', keyB: 'keyB', keyC: 'keyC', four: 'four',
                        p: 'keyP' };
    const loadDriver = {
        tap: async (name, ms = 80) => {
            await cdp.hold(loadSession, loadNames[name]);
            await sleep(ms);
            await cdp.release(loadSession, loadNames[name]);
        },
        hold: (name) => cdp.hold(loadSession, loadNames[name]),
        release: (name) => cdp.release(loadSession, loadNames[name]),
        sleep,
        evaluate: (expression) => evaluateIn(loadSession, expression),
        reload: async () => {
            await cdp.send('Page.reload', {}, loadSession);
            await sleep(1500);
        },
    };
    report.saveLoad = await saveLoadRun(loadDriver);
    report.flightLoad = await flightLoadRun(loadDriver);
    report.demo = await demoRun(loadDriver);
    report.loadConsole = channel(loadSession).console;

    /* Which renderer drew each page of the run (web/video.js), with its reason for a
       fallback: every one of them is meant to be WebGL. */
    report.video = [];
    for (const { session, url } of opened) {
        report.video.push({ url: url.replace(/^.*\//, ''), ...(await evaluateIn(session, VIDEO)) });
    }
} finally {
    await stopChrome(browser);
}

process.stdout.write(JSON.stringify(report, null, 1));
