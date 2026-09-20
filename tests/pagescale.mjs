/* Opens dist/wof.html in headless Chrome under a true scale factor, and reports the picture.
 *
 * This is the companion to tests/pagecheck.mjs and exists because of what that one cannot
 * see.  A devicePixelRatio emulated through the DevTools protocol places the canvas on whole
 * CSS pixels: where a box edge falls on half a CSS pixel the picture is shifted by a device
 * pixel, or resampled a third time.  A scale factor given on Chrome's own command line
 * behaves like a real display, which is what a person has, so that is what the picture is
 * judged on (SPEC.md section 8, row Page).
 *
 *     node tests/pagescale.mjs <page.html> [chrome-binary]
 *
 * The window size is chosen so that the box does land on half a CSS pixel, because that is
 * the case worth measuring; the test asserts that it still does rather than trusting it.
 * Headless Chrome keeps some of --window-size for itself, so the viewport is measured, not
 * assumed.
 */
import { resolve } from 'node:path';

import { DEFAULT_CHROME, sleep, startChrome, stopChrome } from './chrome.mjs';
import { GEOMETRY, PICTURE, SOURCE_PNG } from './pagemeasure.mjs';

const pagePath = resolve(process.argv[2]);
const chromePath = process.argv[3] || process.env.WOF_CHROME || DEFAULT_CHROME;

const report = { chrome: chromePath, page: pagePath, console: [] };

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
    await cdp.send('Page.navigate', { url: 'file://' + pagePath }, sessionId);
    await sleep(2000);

    /* The backquote is the gesture that starts the sound, and the prompt that lies over the
       whole page only goes when the sound is really running; it also opens the diagnostics
       overlay, which is pressed away again before anything is photographed. */
    await cdp.press(sessionId, 'backquote');
    await sleep(2500);
    await cdp.press(sessionId, 'backquote');
    await sleep(500);

    async function look(label) {
        const seen = {
            label,
            geometry: await cdp.evaluate(sessionId, GEOMETRY),
            picture: await cdp.evaluate(sessionId, PICTURE),
            sourcePng: await cdp.evaluate(sessionId, SOURCE_PNG),
        };
        seen.screenshot = (await cdp.send('Page.captureScreenshot',
                                          { format: 'png' }, sessionId)).data;
        seen.hintVisible = await cdp.evaluate(sessionId,
            "!document.getElementById('hint').classList.contains('off')");
        return seen;
    }

    /* The title picture, which has colours all over it, and then the play screen, which has
       three viewports of different depths stacked with blank lines between them. */
    await cdp.press(sessionId, 'right');
    await sleep(500);
    report.title = await look('title');

    for (let i = 0; i < 4; i++) {
        await cdp.press(sessionId, 'right');
        await sleep(250);
    }
    report.playScreen = await look('play screen');
} finally {
    await stopChrome(browser);
}

process.stdout.write(JSON.stringify(report, null, 1));
