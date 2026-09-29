/* Fullscreen and a page hidden for a moment, measured the same way in both page harnesses.
 *
 * The owner put Firefox into fullscreen during a mission, and the picture stood still and
 * the sound was gone from then on.  What a page goes through there is a change of the
 * window's size and, around the change, possibly a moment in which the browser reports it
 * hidden; the shell stops its clock and holds the sound while hidden, so both are driven
 * here: the page hidden and shown again at once, hidden for a real absence, and put into
 * fullscreen and out of it again.  After each, a span of a few seconds is measured:
 *
 *   the VBlanks the shell handed to the core (tests/corewatch.mjs counts them exactly) per
 *   second of the page's own clock; the overlay's audio counts, emulated, audible, padded
 *   and dropped; how many different pictures the source canvas showed; whether the game
 *   said it was paused; the context state; whether the page was hidden or in fullscreen.
 *
 * The judgement is made on the pytest side (tests/conftest.py).  The driver's part is given
 * as functions: look evaluates FULLSCREEN_LOOK, tap presses a key by name, flip(ms) puts
 * another tab in front for that long and brings the page back, enter and leave switch the
 * fullscreen and say what the browser answered.
 */

/* Installed before any page script runs: every change of the page's visibility, with the
   page's own time, so that a span can say the page really was hidden and for how long,
   whatever the shell makes of it. */
export const VISIBILITY_WATCH = `() => {
    window.__wofVisibility = [];
    document.addEventListener('visibilitychange', () => {
        window.__wofVisibility.push([performance.now(), document.visibilityState]);
    });
}`;

/* One sample.  The overlay must be up. */
export const FULLSCREEN_LOOK = `(() => {
    const o = document.getElementById('overlay').textContent;
    const pcm = o.match(/pcm\\s+(\\d+) frames, (\\d+) audible, peak (\\d+), padded (\\d+), dropped (\\d+)/);
    const player = (o.match(/^player\\s+(.*)$/m) || [null, ''])[1];
    const c = window.__wofVideo.picture();
    const d = c.getContext('2d').getImageData(0, 0, c.width, c.height).data;
    let hash = 0;
    for (let i = 0; i < d.length; i += 4) {
        hash = (hash * 31 + d[i] + d[i + 1] * 3 + d[i + 2] * 7) >>> 0;
    }
    return {
        t: performance.now(),
        vblanks: window.__wofRaw.calls,
        pcm: pcm ? { emulated: +pcm[1], audible: +pcm[2], padded: +pcm[4], dropped: +pcm[5] } : null,
        paused: /, paused/.test(player),
        audio: (o.match(/^audio\\s+\\w+, (\\w+)/m) || [null, null])[1],
        visibility: window.__wofVisibility.slice(),
        page: (o.match(/^page\\s+(.*)$/m) || [null, null])[1],
        hidden: document.hidden,
        fullscreen: matchMedia('(display-mode: fullscreen)').matches || !!document.fullscreenElement,
        width: innerWidth,
        height: innerHeight,
        hash,
        path: window.__wofVideo.path,
        sign: (() => {
            const sign = document.getElementById('paused');
            if (!sign || sign.classList.contains('off') || getComputedStyle(sign).display === 'none') {
                return null;
            }
            const rect = (e) => { const r = e.getBoundingClientRect();
                                  return { left: r.left, top: r.top, width: r.width, height: r.height }; };
            const title = sign.querySelector('.title');
            const more = sign.querySelector('.continue');
            return {
                title: title ? title.textContent : null, more: more ? more.textContent : null,
                titleSize: title ? parseFloat(getComputedStyle(title).fontSize) : 0,
                moreSize: more ? parseFloat(getComputedStyle(more).fontSize) : 0,
                rect: rect(sign), box: rect(document.getElementById('screen')),
            };
        })(),
    };
})()`;

/* Samples every stepMs for ms and sums them up. */
async function span(look, ms, sleep, stepMs = 250) {
    const samples = [await look()];
    const until = Date.now() + ms;
    while (Date.now() < until) {
        await sleep(stepMs);
        samples.push(await look());
    }
    const first = samples[0];
    const last = samples[samples.length - 1];
    const seconds = (last.t - first.t) / 1000;
    const delta = (name) => (first.pcm && last.pcm ? last.pcm[name] - first.pcm[name] : null);
    /* The page's hidden phases so far, from the watch: every hidden followed by a visible.
       The last one is the flip made just before the span. */
    const phases = [];
    const changes = last.visibility;
    for (let i = 0; i + 1 < changes.length; i++) {
        if (changes[i][1] === 'hidden' && changes[i + 1][1] === 'visible') {
            phases.push(changes[i + 1][0] - changes[i][0]);
        }
    }
    return {
        seconds,
        vblankRate: seconds > 0 ? (last.vblanks - first.vblanks) / seconds : 0,
        emulated: delta('emulated'),
        audible: delta('audible'),
        padded: delta('padded'),
        dropped: delta('dropped'),
        pictures: new Set(samples.map((s) => s.hash)).size,
        pausedSeen: samples.some((s) => s.paused),
        pausedAtEnd: last.paused,
        hiddenSeen: samples.some((s) => s.hidden),
        fullscreenSeen: samples.some((s) => s.fullscreen),
        audioAtEnd: last.audio,
        page: last.page,
        signSeen: samples.some((s) => s.sign),
        signAlways: samples.every((s) => s.sign),
        signLast: last.sign,
        hides: changes.filter((c) => c[1] === 'hidden').length,
        lastHiddenMs: phases.length ? phases[phases.length - 1] : null,
        size: [last.width, last.height],
        sizeAtStart: [first.width, first.height],
    };
}

/* From the hold of a mission with the sound running (the sea aboard plays for ever,
   re/notes/sound.md), and the overlay up. */
export async function fullscreenRun(d) {
    const out = {};
    out.before = await span(d.look, 2000, d.sleep);

    /* P pauses the mission: the pause sign comes up and the picture stands still; P again
       takes both away.  Escape, the game's other pause key, the same. */
    for (const key of ['p', 'escape']) {
        await d.tap(key);
        await d.sleep(600);
        out['paused_' + key] = await span(d.look, 1500, d.sleep);
        await d.tap(key);
        await d.sleep(600);
        out['resumed_' + key] = await span(d.look, 2000, d.sleep);
    }

    /* Hidden and shown again at once: the mission goes on, and so does its sound. */
    await d.flip(0);
    out.moment = await span(d.look, 3000, d.sleep);

    /* A real absence: the mission comes back paused (SPEC 6.2), and P brings the game and
       its sound back. */
    await d.flip(1500);
    await d.sleep(500);
    out.absence = await span(d.look, 1000, d.sleep);
    await d.tap('p');
    await d.sleep(500);
    out.afterAbsence = await span(d.look, 3000, d.sleep);

    Object.assign(out, await fullscreenRound(d));

    /* The sign in a small window: in the picture's middle still, its letters no smaller than
       their minimum.  Last, because Firefox keeps a viewport it was given through a later
       change of the window's state; d.viewport(null) gives the tab its size back. */
    await d.viewport(420, 320);
    await d.sleep(600);
    await d.tap('p');
    await d.sleep(600);
    out.pausedSmall = await span(d.look, 1000, d.sleep);
    await d.tap('p');
    await d.sleep(400);
    await d.viewport(null);
    await d.sleep(800);
    return out;
}

/* Into fullscreen, five seconds there, out of it again and on with P. */
export async function fullscreenRound(d) {
    const out = {};
    out.enter = await d.enter();
    await d.sleep(500);
    out.fullscreen = await span(d.look, 5000, d.sleep);
    out.fullscreenGeometry = d.geometry ? await d.geometry() : null;

    /* Paused in fullscreen: the sign at the fullscreen picture's size; P again goes on. */
    await d.tap('p');
    await d.sleep(600);
    out.pausedInFullscreen = await span(d.look, 1000, d.sleep);
    await d.tap('p');
    await d.sleep(600);

    /* Out of it again: the shell asks the core to pause (SPEC 6.2), and P continues. */
    out.leave = await d.leave();
    await d.sleep(800);
    out.left = await span(d.look, 1000, d.sleep);
    await d.tap('p');
    await d.sleep(500);
    out.continued = await span(d.look, 3000, d.sleep);
    return out;
}

/* The front end walked to the first rank's mission and into the hold, as the flight tabs
   do; keys.tap(name, ms) with the names backquote, space, enter and p.  The overlay comes up
   with the first key, which is also the page's gesture.  On the way the page is looked at
   (look evaluates FULLSCREEN_LOOK) at the title and in the rank menu, before and after a
   press of P, which the menu reads as Escape and lets fall through: outside a mission the
   game is never paused.  Returns the hold's player and those looks. */
export async function walkToTheHold(keys, player, sleep, look) {
    const outside = [];
    await keys.tap('backquote', 50);
    await sleep(800);
    await keys.tap('space', 250);                   /* the scroller */
    await sleep(6600);
    outside.push(['title', await look()]);
    await keys.tap('space', 250);                   /* the title sequence */
    await sleep(4600);                              /* and the fade of its song */
    outside.push(['ranks', await look()]);
    await keys.tap('p', 80);
    await sleep(600);
    outside.push(['ranks after P', await look()]);
    await keys.tap('enter', 80);                    /* the first rank */
    await sleep(5100);                              /* the music's fade, then the briefing */
    await keys.tap('space', 250);                   /* the briefing */
    for (let waited = 0; waited < 20000; waited += 100) {
        const p = await player();
        if (p && p.x !== 0) {
            break;
        }
        await sleep(100);
    }
    await sleep(1500);
    return { hold: await player(), outside };
}
