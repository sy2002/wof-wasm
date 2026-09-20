/* Opens dist/wof.html in headless Chrome, from a file:// URL, and reports what it finds.
 *
 * This is the part of the M0 acceptance criteria that needs a browser: the page has to run
 * from a double click, draw the test pattern, hold a steady emulated 60 Hz and ask the
 * network for nothing.  Everything is read back through the page's own diagnostics overlay
 * and through the canvas, so the instrument is the same one a person would use.
 *
 * Whether the tone is audible is the one thing left for a person.
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
import { DISPLAY, GEOMETRY, PICTURE, PRESENT_COST } from './pagemeasure.mjs';

const pagePath = resolve(process.argv[2]);
const chromePath = process.argv[3] || process.env.WOF_CHROME || DEFAULT_CHROME;

const report = { chrome: chromePath, page: pagePath, requests: [], console: [] };

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

    async function open(session, url, watches = []) {
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

    report.picture = await evaluate(PICTURE);

    /* The M1 viewer's pages, stepped with the right arrow the way a person steps them.
       Page 0 is the publisher logo, 1 the title, 2 the credits, 5 the play screen. */
    report.pages = [report.picture];
    for (let i = 0; i < 5; i++) {
        await press(sessionId, 'right');
        await sleep(300);
        report.pages.push(await evaluate(PICTURE));
    }
    report.playScreen = report.pages[5];

    /* Back to the first page, so that the rest of the run sees what it saw before. */
    await press(sessionId, 'right');
    await sleep(300);
    report.wrapped = await evaluate(PICTURE);

    report.overlay = await evaluate("document.getElementById('overlay').textContent");
    report.overlayVisible = await evaluate(
        "!document.getElementById('overlay').classList.contains('off')");
    report.gestureHidden = await evaluate(
        "document.getElementById('gesture').classList.contains('off')");
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

    /* The title picture, which has colours all over it, is what the picture on the page is
       compared against; the publisher logo the viewer starts on is almost entirely black and
       would let a canvas that drew nothing but black pass. */
    await press(sessionId, 'right');
    await sleep(400);

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

    /* The play screen as well as the title picture: three viewports of different depths,
       stacked, with two blank lines between them. */
    for (let i = 0; i < 4; i++) {
        await press(sessionId, 'right');
        await sleep(250);
    }
    report.box.playScreen = await look('play screen', true);

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

    const promptShown = async () => !(await evaluateIn(modifierSession,
        "document.getElementById('gesture').classList.contains('off')"));

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
} finally {
    await stopChrome(browser);
}

process.stdout.write(JSON.stringify(report, null, 1));
