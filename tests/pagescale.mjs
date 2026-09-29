/* Opens dist/wof.html in headless Chrome under a true scale factor, and reports the picture.
 *
 * This is the companion to tests/pagecheck.mjs and exists because of what that one cannot
 * see.  A devicePixelRatio emulated through the DevTools protocol places the canvas on whole
 * CSS pixels: where a box edge falls on half a CSS pixel the picture is shifted by a device
 * pixel, or resampled a third time.  A scale factor given on Chrome's own command line
 * behaves like a real display, which is what a person has, so that is what the picture is
 * judged on (SPEC.md section 8, row Page).
 *
 *     node tests/pagescale.mjs <page.html> [chrome-binary] [query]
 *
 * The query, video=2d, runs the same photographs on the shell's Canvas 2D path, which is
 * otherwise drawn only where WebGL is refused (web/video.js).
 *
 * The window size is chosen so that the box does land on half a CSS pixel, because that is
 * the case worth measuring; the test asserts that it still does rather than trusting it.
 * Headless Chrome keeps some of --window-size for itself, so the viewport is measured, not
 * assumed.
 */
import { resolve } from 'node:path';

import { DEFAULT_CHROME, sleep, startChrome, stopChrome } from './chrome.mjs';
import { DISPLAY, GEOMETRY, PICTURE, SOURCE_PNG, VIDEO } from './pagemeasure.mjs';

const pagePath = resolve(process.argv[2]);
const chromePath = process.argv[3] || process.env.WOF_CHROME || DEFAULT_CHROME;
const query = process.argv[4] || '';

const report = { chrome: chromePath, page: pagePath, query, console: [] };

const browser = await startChrome(chromePath, [
    '--force-device-scale-factor=2',
    '--window-size=1512,860',
]);
const cdp = browser.cdp;
report.browser = browser.browser;

try {
    const { targetId } = await cdp.send('Target.createTarget', { url: 'about:blank' });
    const { sessionId } = await cdp.send('Target.attachToTarget', { targetId, flatten: true });

    cdp.on((message) => {
        if (message.method === 'Runtime.exceptionThrown') {
            const detail = message.params.exceptionDetails;
            report.console.push('exception: ' + (detail.exception?.description || detail.text));
        } else if (message.method === 'Log.entryAdded' && message.params.entry.level === 'error') {
            report.console.push('log: ' + message.params.entry.text);
        }
    });

    for (const domain of ['Page.enable', 'Runtime.enable', 'Log.enable']) {
        await cdp.send(domain, {}, sessionId);
    }
    await cdp.send('Page.bringToFront', {}, sessionId);
    await cdp.send('Page.navigate', { url: 'file://' + pagePath + (query ? '?' + query : '') },
                   sessionId);
    await sleep(2000);

    /* The backquote is the gesture that starts the sound, and the prompt that lies over the
       whole page only goes when the sound is really running; it also opens the diagnostics
       overlay, which is pressed away again before anything is photographed. */
    await cdp.press(sessionId, 'backquote');
    await sleep(2500);
    await cdp.press(sessionId, 'backquote');
    await sleep(500);

    /* The front end moves on its own, and a measurement that spanned a fade would be of no
       picture at all: this waits until two reads running give the same picture. */
    async function settle(limitMs = 8000) {
        let last = null;
        for (let waited = 0; waited < limitMs; waited += 300) {
            await sleep(300);
            const now = await cdp.evaluate(sessionId, PICTURE);
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
        await cdp.hold(sessionId, 'space');
        await sleep(250);
        await cdp.release(sessionId, 'space');
    }

    async function look(label) {
        await settle();
        const seen = {
            label,
            geometry: await cdp.evaluate(sessionId, GEOMETRY),
            picture: await cdp.evaluate(sessionId, PICTURE),
            sourcePng: await cdp.evaluate(sessionId, SOURCE_PNG),
            display: await cdp.evaluate(sessionId, DISPLAY),
        };
        seen.screenshot = (await cdp.send('Page.captureScreenshot',
                                          { format: 'png' }, sessionId)).data;
        seen.hintVisible = await cdp.evaluate(sessionId,
            "!document.getElementById('hint').classList.contains('off')");
        return seen;
    }

    /* The front end walked the way a player walks it (re/notes/frontend.md): fire ends the
       story scroller, the publisher logo and then the title come up, and a second fire
       skips the rest of the sequence to the rank selection.  Both pictures have colours
       all over them, which is what this run photographs. */
    await fire();
    await sleep(5500);                    /* the scroller's song fades out first */
    await settle();                       /* the logo, in the picture's own colours */
    await sleep(3200);
    report.title = await look('title');

    await fire();
    await sleep(3600);                    /* the title's song fades out first */
    report.ranks = await look('ranks');
    report.video = await cdp.evaluate(sessionId, VIDEO);

    /* A lost WebGL context (web/video.js): given back, the page draws with WebGL again;
       not given back within two seconds, it draws with Canvas 2D on a new canvas.  The
       browser's own extension loses and restores it, which is what a GPU reset does. */
    if (report.video.path === 'webgl') {
        const lose = "(window.__wofLose = window.__wofVideo.display.getContext('webgl')"
            + ".getExtension('WEBGL_lose_context'), window.__wofLose.loseContext(), 0)";
        await cdp.evaluate(sessionId, lose);
        await sleep(300);
        report.lost = { video: await cdp.evaluate(sessionId, VIDEO) };
        await cdp.evaluate(sessionId, '(window.__wofLose.restoreContext(), 0)');
        await sleep(800);
        report.restored = { video: await cdp.evaluate(sessionId, VIDEO),
                            display: await cdp.evaluate(sessionId, DISPLAY) };
        await cdp.evaluate(sessionId, lose);
        await sleep(2800);
        report.fellBack = await look('fell back');
        report.fellBack.video = await cdp.evaluate(sessionId, VIDEO);
    }
} finally {
    await stopChrome(browser);
}

process.stdout.write(JSON.stringify(report, null, 1));
