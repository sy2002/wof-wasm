/* Stored saved games back in the core after a reload (web/core.js, FILE_MAX), in Chrome or
 * Firefox, headless:
 *
 *     node tests/pagerestore.mjs <page.html> chrome|firefox <files.json> [binary]
 *
 * files.json is { counted: [{ name, data }], saved: { name, data } }, each file's bytes in
 * base64 as the shell stores them; tests/test_page.py and tests/test_firefox.py write it.
 * The run is restoreRun of tests/pageload.mjs, through a driver of the shape that
 * tests/pagecheck.mjs and tests/pagecheck_firefox.mjs hand it, in a browser of its own, so
 * that it does not wait for the whole of those runs.  It asks nothing of the page but what
 * every build of the shell has offered - the overlay's files and game lines and the shell's
 * storage key - so the same run on an earlier page is the negative control.
 */
import { spawn } from 'node:child_process';
import { mkdtempSync, readFileSync, rmSync, writeFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join, resolve } from 'node:path';

import { DEFAULT_CHROME, sleep, startChrome, stopChrome } from './chrome.mjs';
import { restoreRun } from './pageload.mjs';

const DEFAULT_FIREFOX = '/Applications/Firefox.app/Contents/MacOS/firefox';

const [pageArg, which, filesArg, binary] = process.argv.slice(2);
const pagePath = resolve(pageArg);
const url = 'file://' + pagePath;
const files = JSON.parse(readFileSync(filesArg, 'utf8'));

async function openChrome() {
    const browser = await startChrome(binary || process.env.WOF_CHROME || DEFAULT_CHROME);
    const cdp = browser.cdp;
    const { targetId } = await cdp.send('Target.createTarget', { url: 'about:blank' });
    const { sessionId } = await cdp.send('Target.attachToTarget', { targetId, flatten: true });
    const errors = [];
    cdp.on((message) => {
        if (message.sessionId !== sessionId) {
            return;
        }
        if (message.method === 'Runtime.exceptionThrown') {
            errors.push(message.params.exceptionDetails.exception?.description ||
                        message.params.exceptionDetails.text);
        } else if (message.method === 'Runtime.consoleAPICalled' && message.params.type === 'error') {
            errors.push(message.params.args.map((a) => a.value ?? a.description).join(' '));
        }
    });
    for (const domain of ['Page.enable', 'Runtime.enable']) {
        await cdp.send(domain, {}, sessionId);
    }
    await cdp.send('Page.bringToFront', {}, sessionId);
    await cdp.send('Page.navigate', { url }, sessionId);
    await sleep(1500);
    return {
        name: browser.browser,
        errors,
        driver: {
            tap: async (name, ms = 80) => {
                await cdp.hold(sessionId, name);
                await sleep(ms);
                await cdp.release(sessionId, name);
            },
            hold: (name) => cdp.hold(sessionId, name),
            release: (name) => cdp.release(sessionId, name),
            sleep,
            evaluate: (expression) => cdp.evaluate(sessionId, expression),
            reload: async () => {
                await cdp.send('Page.reload', {}, sessionId);
                await sleep(1500);
            },
        },
        close: () => stopChrome(browser),
    };
}

async function openFirefox() {
    const port = 9500 + Math.floor(Math.random() * 400);
    const profile = mkdtempSync(join(tmpdir(), 'wof-restore-'));
    /* Silent from outside the page, as in tests/pagecheck_firefox.mjs. */
    writeFileSync(join(profile, 'user.js'), 'user_pref("media.volume_scale", "0.0");\n');
    const firefox = spawn(binary || process.env.WOF_FIREFOX || DEFAULT_FIREFOX, [
        '--headless', '--no-remote', '--profile', profile,
        '--remote-debugging-port', String(port), '--width', '1400', '--height', '800',
    ], { stdio: 'ignore' });

    let socket = null;
    for (let attempt = 0; attempt < 80 && !socket; attempt++) {
        try {
            const trying = new WebSocket('ws://127.0.0.1:' + port + '/session');
            await new Promise((ok, fail) => {
                trying.addEventListener('open', ok, { once: true });
                trying.addEventListener('error', fail, { once: true });
            });
            socket = trying;
        } catch {
            await sleep(250);
        }
    }
    if (!socket) {
        throw new Error('Firefox did not open a WebDriver BiDi port');
    }
    let nextId = 0;
    const pending = new Map();
    const errors = [];
    socket.addEventListener('message', (event) => {
        const message = JSON.parse(event.data);
        if (message.id && pending.has(message.id)) {
            const { ok, fail } = pending.get(message.id);
            pending.delete(message.id);
            message.type === 'error' ? fail(new Error(message.message)) : ok(message.result);
        } else if (message.method === 'log.entryAdded' && message.params.level === 'error') {
            errors.push(message.params.text);
        }
    });
    const send = (method, params) => {
        const id = ++nextId;
        socket.send(JSON.stringify({ id, method, params }));
        return new Promise((ok, fail) => {
            const deadline = setTimeout(() => {
                pending.delete(id);
                fail(new Error(method + ' was not answered within 60 s'));
            }, 60000);
            pending.set(id, { ok: (v) => { clearTimeout(deadline); ok(v); },
                              fail: (e) => { clearTimeout(deadline); fail(e); } });
        });
    };
    const session = await send('session.new', { capabilities: {} });
    await send('session.subscribe', { events: ['log.entryAdded'] });
    /* A tab of its own: the one Firefox opens with may be a privileged page, in which the
       driver may not run a script. */
    const context = (await send('browsingContext.create', { type: 'tab' })).context;
    await send('browsingContext.activate', { context });
    await send('browsingContext.navigate', { context, url, wait: 'complete' });
    await sleep(1500);
    const keys = { backquote: '`', space: ' ', enter: '', up: '' };
    const key = (type, name) => send('input.performActions', {
        context, actions: [{ type: 'key', id: 'keyboard', actions: [{ type, value: keys[name] }] }],
    });
    return {
        name: 'firefox/' + session.capabilities.browserVersion,
        errors,
        driver: {
            tap: async (name, ms = 80) => {
                await key('keyDown', name);
                await sleep(ms);
                await key('keyUp', name);
            },
            hold: (name) => key('keyDown', name),
            release: (name) => key('keyUp', name),
            sleep,
            evaluate: async (expression) => {
                const result = await send('script.evaluate', {
                    expression: 'Promise.resolve(' + expression + ').then(JSON.stringify)',
                    target: { context }, awaitPromise: true,
                });
                if (result.type === 'exception') {
                    throw new Error(result.exceptionDetails.text);
                }
                return JSON.parse(result.result.value);
            },
            reload: async () => {
                await send('browsingContext.reload', { context, wait: 'complete' });
                await sleep(1500);
            },
        },
        close: async () => {
            firefox.kill();
            await sleep(400);
            rmSync(profile, { recursive: true, force: true });
        },
    };
}

const browser = which === 'firefox' ? await openFirefox() : await openChrome();
const report = { browser: browser.name, page: pagePath };
try {
    Object.assign(report, await restoreRun(browser.driver, files.counted, files.saved));
} catch (err) {
    report.error = err && err.stack ? err.stack : String(err);
} finally {
    report.errors = browser.errors;
    await browser.close();
}

process.stdout.write(JSON.stringify(report, null, 1));
if (report.error) {
    process.exitCode = 1;
}
