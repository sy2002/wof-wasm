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
import { DISPLAY, GEOMETRY, PICTURE, PRESENT_COST, SOURCE_PNG } from './pagemeasure.mjs';

const DEFAULT_FIREFOX = '/Applications/Firefox.app/Contents/MacOS/firefox';
const args = process.argv.slice(2);
const visible = args.includes('--visible');
const positional = args.filter((a) => !a.startsWith('--'));
const pagePath = resolve(positional[0]);
const firefoxPath = positional[1] || process.env.WOF_FIREFOX || DEFAULT_FIREFOX;
const port = 9500 + Math.floor(Math.random() * 400);

const sleep = (ms) => new Promise((done) => setTimeout(done, ms));

const profile = mkdtempSync(join(tmpdir(), 'wof-firefox-'));

/* The page plays a test tone, and these runs happen on a machine somebody is working at.
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

    await press(context, KEY_BACKQUOTE);
    await sleep(2500);

    report.audioAfterKey = await evaluate('window.__wofAudio');
    report.picture = await evaluate(PICTURE);

    report.pages = [report.picture];
    for (let i = 0; i < 5; i++) {
        await press(context, KEY_RIGHT);
        await sleep(300);
        report.pages.push(await evaluate(PICTURE));
    }
    report.playScreen = report.pages[5];

    await press(context, KEY_RIGHT);
    await sleep(300);
    report.wrapped = await evaluate(PICTURE);

    report.overlay = await evaluate("document.getElementById('overlay').textContent");
    report.overlayVisible = await evaluate(
        "!document.getElementById('overlay').classList.contains('off')");
    report.gestureHidden = await evaluate(
        "document.getElementById('gesture').classList.contains('off')");

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

    /* The title picture rather than the publisher logo the viewer starts on, which is almost
       entirely black and would let a canvas that drew nothing but black pass. */
    await press(context, KEY_RIGHT);
    await sleep(400);

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

    /* The play screen as well as the title picture: three viewports of different depths,
       stacked, with two blank lines between them. */
    for (let i = 0; i < 4; i++) {
        await press(context, KEY_RIGHT);
        await sleep(250);
    }
    report.box.playScreen = await look('play screen', true);

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
        "document.getElementById('gesture').classList.contains('off')"));

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
