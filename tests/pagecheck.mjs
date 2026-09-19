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
    '--autoplay-policy=no-user-gesture-required',
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
        await cdp.send('Page.navigate', { url }, session);
        await sleep(1500);
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

    /* The overlay is opened with the same keypress that is the gesture starting the audio. */
    const OPEN_OVERLAY = "window.dispatchEvent(new KeyboardEvent('keydown', { code: 'Backquote' }))";

    await open(sessionId, 'file://' + pagePath);

    await evaluate(OPEN_OVERLAY);
    await sleep(2000);

    /* Rows 30 and 50 of the first band are the tick bar and the VBlank bar of the test
       pattern; both have to be somewhere else a moment later, or nothing is running. */
    const STRIPS = `(() => {
        const canvas = document.getElementById('screen');
        const image = canvas.getContext('2d').getImageData(0, 0, canvas.width, canvas.height).data;
        const strip = (y) => {
            let sum = 0;
            for (let x = 0; x < canvas.width; x++) {
                sum = (sum * 31 + image[(y * canvas.width + x) * 4]) >>> 0;
            }
            return sum;
        };
        return { tickBar: strip(30), vblankBar: strip(50), passMarker: strip(98) };
    })()`;

    report.picture = await evaluate(`(() => {
        const canvas = document.getElementById('screen');
        const ctx = canvas.getContext('2d');
        const pixel = (x, y) => [...ctx.getImageData(x, y, 1, 1).data].slice(0, 3).join(',');
        const image = ctx.getImageData(0, 0, canvas.width, canvas.height).data;
        const colours = new Set();
        for (let i = 0; i < image.length; i += 4) {
            colours.add(image[i] << 16 | image[i + 1] << 8 | image[i + 2]);
        }
        return {
            width: canvas.width,
            height: canvas.height,
            cssWidth: canvas.style.width,
            colours: colours.size,
            topBandPixel: pixel(10, 10),
            bottomBandPixel: pixel(10, 10 + canvas.height / 2),
        };
    })()`);

    const before = await evaluate(STRIPS);
    await sleep(600);
    const after = await evaluate(STRIPS);
    report.moving = {
        tickBar: before.tickBar !== after.tickBar,
        vblankBar: before.vblankBar !== after.vblankBar,
        passMarker: before.passMarker !== after.passMarker,
    };

    report.overlay = await evaluate("document.getElementById('overlay').textContent");
    report.overlayVisible = await evaluate(
        "!document.getElementById('overlay').classList.contains('off')");
    report.gestureHidden = await evaluate(
        "document.getElementById('gesture').classList.contains('off')");
    report.hint = await evaluate("document.getElementById('hint').textContent");

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
    await evaluateIn(fallbackSession, OPEN_OVERLAY);
    await sleep(2000);
    report.fallback = {
        overlay: await evaluateIn(fallbackSession, "document.getElementById('overlay').textContent"),
        requests: channel(fallbackSession).requests,
        console: channel(fallbackSession).console,
    };
} finally {
    chrome.kill();
    await sleep(200);
    rmSync(profile, { recursive: true, force: true });
}

process.stdout.write(JSON.stringify(report, null, 1));
