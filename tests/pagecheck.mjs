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
 * Talks the DevTools protocol over the WebSocket that Node has built in; nothing is
 * installed for it.
 */
import { spawn } from 'node:child_process';
import { mkdtempSync, existsSync, readFileSync, rmSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join, resolve } from 'node:path';

import { AUDIO_WATCH } from './audiowatch.mjs';
import { DISPLAY, GEOMETRY, PICTURE, PRESENT_COST } from './pagemeasure.mjs';

const DEFAULT_CHROME = '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome';
const pagePath = resolve(process.argv[2]);
const chromePath = process.argv[3] || process.env.WOF_CHROME || DEFAULT_CHROME;

const sleep = (ms) => new Promise((done) => setTimeout(done, ms));

async function waitForPort(directory, deadlineMs) {
    const file = join(directory, 'DevToolsActivePort');
    const until = Date.now() + deadlineMs;
    while (Date.now() < until) {
        if (existsSync(file)) {
            const lines = readFileSync(file, 'utf8').split('\n');
            if (lines[0] && lines[1]) {
                return { port: Number(lines[0]), path: lines[1] };
            }
        }
        await sleep(50);
    }
    throw new Error('Chrome did not open a debugging port');
}

class Devtools {
    constructor(socket) {
        this.socket = socket;
        this.next = 1;
        this.pending = new Map();
        this.listeners = [];
        socket.addEventListener('message', (event) => {
            const message = JSON.parse(event.data);
            if (message.id && this.pending.has(message.id)) {
                const { resolve: ok, reject } = this.pending.get(message.id);
                this.pending.delete(message.id);
                message.error ? reject(new Error(JSON.stringify(message.error))) : ok(message.result);
            } else if (message.method) {
                for (const listener of this.listeners) {
                    listener(message);
                }
            }
        });
    }

    on(listener) {
        this.listeners.push(listener);
    }

    send(method, params = {}, sessionId) {
        const id = this.next++;
        const payload = { id, method, params };
        if (sessionId) {
            payload.sessionId = sessionId;
        }
        this.socket.send(JSON.stringify(payload));
        return new Promise((ok, reject) => this.pending.set(id, { resolve: ok, reject }));
    }
}

const profile = mkdtempSync(join(tmpdir(), 'wof-chrome-'));
const chrome = spawn(chromePath, [
    '--headless=new',
    '--disable-gpu',
    '--no-first-run',
    '--no-default-browser-check',
    '--disable-extensions',
    '--mute-audio',
    '--user-data-dir=' + profile,
    '--remote-debugging-port=0',
    '--window-size=1280,900',
    'about:blank',
], { stdio: ['ignore', 'ignore', 'ignore'] });

const report = { chrome: chromePath, page: pagePath, requests: [], console: [] };

try {
    const { port } = await waitForPort(profile, 15000);
    const version = await (await fetch('http://127.0.0.1:' + port + '/json/version')).json();
    report.browser = version.Browser;

    const socket = new WebSocket(version.webSocketDebuggerUrl);
    await new Promise((ok, fail) => {
        socket.addEventListener('open', ok, { once: true });
        socket.addEventListener('error', fail, { once: true });
    });
    const cdp = new Devtools(socket);

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

    async function open(session, url) {
        for (const domain of ['Page.enable', 'Runtime.enable', 'Log.enable', 'Network.enable']) {
            await cdp.send(domain, {}, session);
        }
        await cdp.send('Page.addScriptToEvaluateOnNewDocument',
                       { source: '(' + AUDIO_WATCH + ')();' }, session);
        await cdp.send('Page.bringToFront', {}, session);
        await cdp.send('Page.navigate', { url }, session);
        await sleep(1500);
    }

    /* Real key events through the DevTools protocol, not synthesised ones: only a real
       event activates the page, and activation is what the shell waits for before it
       touches Web Audio. */
    const KEYS = {
        backquote: { key: '`', code: 'Backquote', text: '`' },
        space: { key: ' ', code: 'Space', text: ' ' },
        right: { key: 'ArrowRight', code: 'ArrowRight' },
        five: { key: '5', code: 'Digit5', text: '5' },
        six: { key: '6', code: 'Digit6', text: '6' },
        meta: { key: 'Meta', code: 'MetaLeft' },
    };

    /* Deliberately no windowsVirtualKeyCode and no modifiers: given those, headless Chrome
       answers a single modifier press with a flood of phantom keydown repeats carrying a
       different key, which drowns the very measurement this pass is here to make. */
    async function press(session, name) {
        const k = KEYS[name];
        await cdp.send('Input.dispatchKeyEvent',
                       { type: k.text ? 'keyDown' : 'rawKeyDown', key: k.key, code: k.code, text: k.text },
                       session);
        await cdp.send('Input.dispatchKeyEvent', { type: 'keyUp', key: k.key, code: k.code }, session);
    }

    async function evaluateIn(session, expression) {
        const result = await cdp.send('Runtime.evaluate', {
            expression, returnByValue: true, awaitPromise: true,
        }, session);
        if (result.exceptionDetails) {
            throw new Error(result.exceptionDetails.exception?.description || 'evaluate failed');
        }
        return result.result.value;
    }

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
} finally {
    chrome.kill();
    /* Chrome writes its profile out while it is dying, and a directory that is not empty
       yet must not lose the whole report: the cleanup waits, retries and then gives up. */
    for (let attempt = 0; attempt < 10; attempt++) {
        await sleep(200);
        try {
            rmSync(profile, { recursive: true, force: true });
            break;
        } catch {
            /* still busy */
        }
    }
}

process.stdout.write(JSON.stringify(report, null, 1));
