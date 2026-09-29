/* The frame-time measurement of M9 (re/notes/page-video.md): how often the picture reaches
 * the screen during a mission at a screen-sized window, and what present() costs there.
 *
 *     node tests/pageframes.mjs <page.html> chrome|firefox [--visible] [--size=WxH]
 *                               [--seconds=N] [--query=video=2d] [binary]
 *
 * One driver for both browsers, and one that asks nothing of the page but what every build
 * of the shell has offered - the overlay's player line, window.__wofVideo.display and
 * present() - so that it measures the shell's earlier pages too, which is what makes a
 * negative control possible: the same run on an older build must fail where this one passes.
 *
 * The display's refresh is measured first, on the blank page the browser opens with, because
 * a page that misses every other frame has a median interval of two refreshes and would
 * judge itself by that.  Then the front end is walked to the first mission, the lift goes up
 * and the aircraft rolls along the deck with the picture scrolling, the window is made the
 * size of the screen, and every animation frame is timed over the span (FRAME_TIMES in
 * tests/pagemeasure.mjs).  The judgement is made on the pytest side.
 *
 * The screen's size: Chrome runs headless under a true scale factor of 2 at the owner's
 * screen, 1792 x 1120 CSS pixels unless --size says otherwise; a visible Firefox takes its
 * screen's own size from the page.  A visible window cannot be made as tall as the screen
 * (the menu bar and its own toolbar take some of it, and a locked screen refuses the
 * fullscreen space), so Firefox is given that size as its viewport.
 */
import { spawn } from 'node:child_process';
import { mkdtempSync, rmSync, writeFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join, resolve } from 'node:path';

import { DEFAULT_CHROME, sleep, startChrome, stopChrome } from './chrome.mjs';
import { PLAYER, VIDEO, frameTimes } from './pagemeasure.mjs';

const DEFAULT_FIREFOX = '/Applications/Firefox.app/Contents/MacOS/firefox';
const OWNER_SCREEN = [1792, 1120];

const args = process.argv.slice(2);
const option = (name, fallback) => {
    const found = args.find((a) => a.startsWith('--' + name + '='));
    return found ? found.slice(name.length + 3) : fallback;
};
const positional = args.filter((a) => !a.startsWith('--'));
const pagePath = resolve(positional[0]);
const which = positional[1];
const binary = positional[2];
const visible = args.includes('--visible');
const seconds = Number(option('seconds', '5'));
const query = option('query', '');
const asked = option('size', '');
const url = 'file://' + pagePath + (query ? '?' + query : '');

/* The display's refresh as requestAnimationFrame delivers it, on a page that does nothing. */
const REFRESH = `new Promise((done) => {
    const times = [];
    const step = (t) => {
        times.push(t);
        if (times.length < 91) {
            requestAnimationFrame(step);
        } else {
            done(times);
        }
    };
    requestAnimationFrame(step);
})`;

/* The browser as three operations and a key: evaluate, press, resize. */
async function openChrome() {
    const [width, height] = asked ? asked.split('x').map(Number) : OWNER_SCREEN;
    const browser = await startChrome(binary || process.env.WOF_CHROME || DEFAULT_CHROME, [
        '--force-device-scale-factor=2', '--window-size=' + width + ',' + height,
    ]);
    const cdp = browser.cdp;
    const { targetId } = await cdp.send('Target.createTarget', { url: 'about:blank' });
    const { sessionId } = await cdp.send('Target.attachToTarget', { targetId, flatten: true });
    for (const domain of ['Page.enable', 'Runtime.enable']) {
        await cdp.send(domain, {}, sessionId);
    }
    await cdp.send('Page.bringToFront', {}, sessionId);
    const { windowId } = await cdp.send('Browser.getWindowForTarget', { targetId });
    const names = { backquote: 'backquote', space: 'space', enter: 'enter', right: 'right' };
    return {
        name: browser.browser,
        evaluate: (expression) => cdp.evaluate(sessionId, expression),
        navigate: async (to) => { await cdp.send('Page.navigate', { url: to }, sessionId); },
        down: (key) => cdp.hold(sessionId, names[key]),
        up: (key) => cdp.release(sessionId, names[key]),
        screen: async () => [width, height],
        /* Headless Chrome's window is its viewport, less a little it keeps for itself: the
           window is grown by what is missing, once. */
        resize: async (w, h) => {
            const inner = await cdp.evaluate(sessionId, '[innerWidth, innerHeight]');
            if (inner[0] !== w || inner[1] !== h) {
                const { bounds } = await cdp.send('Browser.getWindowBounds', { windowId });
                await cdp.send('Browser.setWindowBounds', { windowId, bounds: {
                    width: bounds.width + w - inner[0], height: bounds.height + h - inner[1] } });
            }
        },
        close: () => stopChrome(browser),
    };
}

async function openFirefox() {
    const port = 9500 + Math.floor(Math.random() * 400);
    const profile = mkdtempSync(join(tmpdir(), 'wof-frames-'));
    /* Silent from outside the page, as in tests/pagecheck_firefox.mjs. */
    writeFileSync(join(profile, 'user.js'), 'user_pref("media.volume_scale", "0.0");\n');
    const firefox = spawn(binary || process.env.WOF_FIREFOX || DEFAULT_FIREFOX, [
        ...(visible ? [] : ['--headless']), '--no-remote', '--profile', profile,
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
    socket.addEventListener('message', (event) => {
        const message = JSON.parse(event.data);
        if (message.id && pending.has(message.id)) {
            const { ok, fail } = pending.get(message.id);
            pending.delete(message.id);
            message.type === 'error' ? fail(new Error(message.message)) : ok(message.result);
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
    /* A tab of its own: the one Firefox opens with may be a privileged page, in which the
       driver may not run a script. */
    const context = (await send('browsingContext.create', { type: 'tab' })).context;
    await send('browsingContext.activate', { context });
    const evaluate = async (expression) => {
        const result = await send('script.evaluate', {
            expression: 'Promise.resolve(' + expression + ').then(JSON.stringify)',
            target: { context }, awaitPromise: true,
        });
        if (result.type === 'exception') {
            throw new Error(result.exceptionDetails.text);
        }
        return JSON.parse(result.result.value);
    };
    const codes = { backquote: '`', space: ' ', enter: '', right: '' };
    const key = (type, name) => send('input.performActions', {
        context, actions: [{ type: 'key', id: 'keyboard', actions: [{ type, value: codes[name] }] }],
    });
    return {
        name: 'firefox/' + session.capabilities.browserVersion,
        evaluate,
        navigate: async (to) => { await send('browsingContext.navigate', { context, url: to, wait: 'complete' }); },
        down: (name) => key('keyDown', name),
        up: (name) => key('keyUp', name),
        screen: async () => (asked ? asked.split('x').map(Number)
                                   : await evaluate('[screen.width, screen.height]')),
        resize: async (w, h) => {
            await send('browsingContext.setViewport', { context, viewport: { width: w, height: h } });
        },
        close: async () => {
            firefox.kill();
            await sleep(400);
            rmSync(profile, { recursive: true, force: true });
        },
    };
}

const browser = which === 'firefox' ? await openFirefox() : await openChrome();
const report = { browser: browser.name, page: pagePath, query, visible: which === 'firefox' ? visible : false };
const tap = async (name, ms) => {
    await browser.down(name);
    await sleep(ms);
    await browser.up(name);
};

try {
    await sleep(500);
    report.refreshFrames = await browser.evaluate(REFRESH);
    const [width, height] = await browser.screen();
    report.screen = { width, height };

    await browser.navigate(url);
    await sleep(2500);
    /* The front end walked as a player walks it, as tests/pagefullscreen.mjs does. */
    await tap('backquote', 50);                     /* the sound, and the overlay */
    await sleep(800);
    await tap('space', 250);                        /* the scroller */
    await sleep(6600);
    await tap('space', 250);                        /* the title sequence */
    await sleep(4600);
    await tap('enter', 80);                         /* the first rank */
    await sleep(5100);
    await tap('space', 250);                        /* the briefing */
    for (let waited = 0; waited < 20000; waited += 100) {
        const p = await browser.evaluate(PLAYER);
        if (p && p.x !== 0) {
            break;
        }
        await sleep(100);
    }
    await sleep(1500);
    report.hold = await browser.evaluate(PLAYER);
    await tap('backquote', 50);                     /* nothing over the picture */
    await tap('space', 250);                        /* the lift */
    await sleep(3000);
    await browser.down('right');                    /* along the deck, the picture scrolling */
    await browser.resize(width, height);
    await sleep(1000);
    report.measured = await browser.evaluate(frameTimes(seconds * 1000));
    await browser.up('right');
    /* The overlay, which the player is read off, paints only while it is up. */
    await tap('backquote', 50);
    await sleep(500);
    report.rolled = await browser.evaluate(PLAYER);
    try {
        report.video = await browser.evaluate(VIDEO);
    } catch {
        report.video = null;                        /* a shell before M9 keeps no count */
    }
} catch (err) {
    report.error = err && err.stack ? err.stack : String(err);
} finally {
    await browser.close();
}

process.stdout.write(JSON.stringify(report, null, 1));
if (report.error) {
    process.exitCode = 1;
}
