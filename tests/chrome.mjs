/* Driving Chrome over the DevTools protocol, for the harnesses that need it.
 *
 * Nothing is installed for this: Node has a WebSocket, Chrome opens a debugging port and
 * writes it into its profile directory.  Two harnesses share this - tests/pagecheck.mjs,
 * which runs the page, and tests/pagescale.mjs, which runs it again under a scale factor
 * given on the command line - so that there is one way of talking to Chrome, not two.
 */
import { spawn } from 'node:child_process';
import { mkdtempSync, existsSync, readFileSync, rmSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';

export const DEFAULT_CHROME = '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome';

export const sleep = (ms) => new Promise((done) => setTimeout(done, ms));

/* Real key events through the protocol, not synthesised ones: only a real event activates
   the page, and activation is what the shell waits for before it touches Web Audio.
   Deliberately no windowsVirtualKeyCode and no modifiers: given those, headless Chrome
   answers a single modifier press with a flood of phantom keydown repeats carrying a
   different key, which drowns the very measurements these harnesses make. */
export const KEYS = {
    backquote: { key: '`', code: 'Backquote', text: '`' },
    space: { key: ' ', code: 'Space', text: ' ' },
    right: { key: 'ArrowRight', code: 'ArrowRight' },
    left: { key: 'ArrowLeft', code: 'ArrowLeft' },
    up: { key: 'ArrowUp', code: 'ArrowUp' },
    down: { key: 'ArrowDown', code: 'ArrowDown' },
    five: { key: '5', code: 'Digit5', text: '5' },
    six: { key: '6', code: 'Digit6', text: '6' },
    meta: { key: 'Meta', code: 'MetaLeft' },
    enter: { key: 'Enter', code: 'Enter', text: '\r' },
    one: { key: '1', code: 'Digit1', text: '1' },
    two: { key: '2', code: 'Digit2', text: '2' },
    keyA: { key: 'a', code: 'KeyA', text: 'a' },
    keyB: { key: 'b', code: 'KeyB', text: 'b' },
    keyP: { key: 'p', code: 'KeyP', text: 'p' },
    keyF: { key: 'f', code: 'KeyF', text: 'f' },
    keyV: { key: 'v', code: 'KeyV', text: 'v' },
    escape: { key: 'Escape', code: 'Escape' },
    keyM: { key: 'm', code: 'KeyM', text: 'm' },
    keyH: { key: 'h', code: 'KeyH', text: 'h' },
    keyG: { key: 'g', code: 'KeyG', text: 'g' },
    keyL: { key: 'l', code: 'KeyL', text: 'l' },
    keyR: { key: 'r', code: 'KeyR', text: 'r' },
    keyC: { key: 'c', code: 'KeyC', text: 'c' },
    four: { key: '4', code: 'Digit4', text: '4' },
};

export class Devtools {
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

    async press(session, name) {
        await this.hold(session, name);
        await this.release(session, name);
    }

    /* The two halves of a press, for a key that has to stay down while something is read. */
    async hold(session, name) {
        const k = KEYS[name];
        await this.send('Input.dispatchKeyEvent',
                        { type: k.text ? 'keyDown' : 'rawKeyDown', key: k.key, code: k.code, text: k.text },
                        session);
    }

    async release(session, name) {
        const k = KEYS[name];
        await this.send('Input.dispatchKeyEvent', { type: 'keyUp', key: k.key, code: k.code }, session);
    }

    async evaluate(session, expression) {
        const result = await this.send('Runtime.evaluate', {
            expression, returnByValue: true, awaitPromise: true,
        }, session);
        if (result.exceptionDetails) {
            throw new Error(result.exceptionDetails.exception?.description || 'evaluate failed');
        }
        return result.result.value;
    }
}

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

/* Starts Chrome on a fresh profile and connects to it.  extraArgs is where a harness puts
   what makes it different, such as --window-size or --force-device-scale-factor.

   Headless, but on the GPU: the page draws with WebGL (web/video.js), which headless Chrome
   gives only with its GPU.  Without it (--disable-gpu) there is no WebGL at all, or with
   --enable-unsafe-swiftshader one in software that takes 68 ms a frame at the tests' Retina
   size, which the shell refuses (failIfMajorPerformanceCaveat) for its 2D path; the tests
   would then test the fallback under the main path's name (re/notes/page-video.md). */
export async function startChrome(chromePath, extraArgs = []) {
    const profile = mkdtempSync(join(tmpdir(), 'wof-chrome-'));
    const chrome = spawn(chromePath, [
        '--headless=new',
        '--no-first-run',
        '--no-default-browser-check',
        '--disable-extensions',
        '--mute-audio',
        '--user-data-dir=' + profile,
        '--remote-debugging-port=0',
        ...extraArgs,
        'about:blank',
    ], { stdio: ['ignore', 'ignore', 'ignore'] });

    const { port } = await waitForPort(profile, 15000);
    const version = await (await fetch('http://127.0.0.1:' + port + '/json/version')).json();
    const socket = new WebSocket(version.webSocketDebuggerUrl);
    await new Promise((ok, fail) => {
        socket.addEventListener('open', ok, { once: true });
        socket.addEventListener('error', fail, { once: true });
    });

    return { chrome, profile, browser: version.Browser, cdp: new Devtools(socket) };
}

export async function stopChrome({ chrome, profile }) {
    chrome.kill();
    /* Chrome writes its profile out while it is dying, and a directory that is not empty
       yet must not lose the whole report: the cleanup waits, retries and then gives up. */
    for (let attempt = 0; attempt < 10; attempt++) {
        await sleep(200);
        try {
            rmSync(profile, { recursive: true, force: true });
            return;
        } catch {
            /* still busy */
        }
    }
}
