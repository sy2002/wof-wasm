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
import { mkdtempSync, rmSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join, resolve } from 'node:path';

const DEFAULT_FIREFOX = '/Applications/Firefox.app/Contents/MacOS/firefox';
const args = process.argv.slice(2);
const visible = args.includes('--visible');
const positional = args.filter((a) => !a.startsWith('--'));
const pagePath = resolve(positional[0]);
const firefoxPath = positional[1] || process.env.WOF_FIREFOX || DEFAULT_FIREFOX;
const port = 9500 + Math.floor(Math.random() * 400);

const sleep = (ms) => new Promise((done) => setTimeout(done, ms));

const profile = mkdtempSync(join(tmpdir(), 'wof-firefox-'));
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

function send(socket, method, params) {
    const id = ++nextId;
    socket.send(JSON.stringify({ id, method, params }));
    return new Promise((ok, fail) => pending.set(id, { ok, fail }));
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
    await send(socket, 'script.addPreloadScript', {
        functionDeclaration: `() => {
            window.__wofAudio = [];
            const Native = window.AudioContext || window.webkitAudioContext;
            if (!Native) {
                return;
            }
            const activated = () => !!(navigator.userActivation && navigator.userActivation.hasBeenActive);
            class Watched extends Native {
                constructor(...args) {
                    super(...args);
                    window.__wofAudio.push({ call: 'construct', activated: activated() });
                }
                resume() {
                    window.__wofAudio.push({ call: 'resume', activated: activated() });
                    return super.resume();
                }
            }
            window.AudioContext = Watched;
            if (window.webkitAudioContext) {
                window.webkitAudioContext = Watched;
            }
        }`,
    });

    const tree = await send(socket, 'browsingContext.getTree', {});
    const context = tree.contexts[0].context;

    await send(socket, 'browsingContext.navigate', { context, url: 'file://' + pagePath, wait: 'complete' });
    await sleep(2000);

    /* BiDi serialises objects as remote-value trees, so the page hands back JSON text and
       this side parses it.  The caller writes an ordinary expression. */
    async function evaluate(expression) {
        const result = await send(socket, 'script.evaluate', {
            expression: 'JSON.stringify(' + expression + ')', target: { context }, awaitPromise: true,
        });
        if (result.type === 'exception') {
            throw new Error(result.exceptionDetails.text);
        }
        return JSON.parse(result.result.value);
    }

    /* What the console holds before anything has been pressed: an autoplay warning here
       would mean the shell touched Web Audio on its own. */
    report.logsBeforeKey = logs.slice();
    report.audioBeforeKey = await evaluate('window.__wofAudio');

    /* A real key press, so that the page sees a user gesture and not a synthetic event. */
    await send(socket, 'input.performActions', {
        context,
        actions: [{
            type: 'key',
            id: 'keyboard',
            actions: [{ type: 'keyDown', value: '`' }, { type: 'keyUp', value: '`' }],
        }],
    });
    await sleep(2500);

    const PICTURE = `(() => {
        const canvas = document.getElementById('screen');
        const ctx = canvas.getContext('2d');
        const image = ctx.getImageData(0, 0, canvas.width, canvas.height).data;
        const colours = new Set();
        for (let i = 0; i < image.length; i += 4) {
            colours.add(image[i] << 16 | image[i + 1] << 8 | image[i + 2]);
        }
        const pixel = (x, y) => {
            const i = (y * canvas.width + x) * 4;
            return image[i] + ',' + image[i + 1] + ',' + image[i + 2];
        };
        const strip = (y) => {
            let sum = 0;
            for (let x = 0; x < canvas.width; x++) {
                sum = (sum * 31 + image[(y * canvas.width + x) * 4]) >>> 0;
            }
            return sum;
        };
        return {
            width: canvas.width,
            height: canvas.height,
            cssWidth: canvas.style.width,
            colours: colours.size,
            topBandPixel: pixel(10, 10),
            bottomBandPixel: pixel(10, 10 + canvas.height / 2),
            strips: { tickBar: strip(30), vblankBar: strip(50), passMarker: strip(98) },
        };
    })()`;

    report.audioAfterKey = await evaluate('window.__wofAudio');
    report.picture = await evaluate(PICTURE);
    await sleep(600);
    const second = await evaluate(PICTURE);
    report.moving = {
        tickBar: report.picture.strips.tickBar !== second.strips.tickBar,
        vblankBar: report.picture.strips.vblankBar !== second.strips.vblankBar,
        passMarker: report.picture.strips.passMarker !== second.strips.passMarker,
    };

    report.overlay = await evaluate("document.getElementById('overlay').textContent");
    report.overlayVisible = await evaluate(
        "!document.getElementById('overlay').classList.contains('off')");
    report.gestureHidden = await evaluate(
        "document.getElementById('gesture').classList.contains('off')");

} catch (err) {
    report.error = err && err.message ? err.message : String(err);
} finally {
    report.logs = logs.slice();
    report.requests = requests.slice();
    firefox.kill();
    await sleep(300);
    rmSync(profile, { recursive: true, force: true });
}

process.stdout.write(JSON.stringify(report, null, 1));
if (report.error) {
    process.exitCode = 1;
}
