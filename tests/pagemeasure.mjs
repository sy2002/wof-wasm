/* The expressions both page harnesses evaluate inside the page, kept in one place so that
 * the Chrome run and the Firefox run measure the same things in the same way.
 *
 * Each one returns plain data.  Every judgement about that data is made on the pytest side
 * (tests/conftest.py), and the geometry is measured off the DOM - getBoundingClientRect, the
 * canvas backing store, innerWidth, devicePixelRatio - never taken from what the shell says
 * about itself.  The shell's own numbers travel as `shellSays` for a failure message only.
 */

/* The exact framebuffer pixels.  After scaling (SPEC 6.2) they exist nowhere on the page, so
   the shell hands them to these tests as a 640 x 214 canvas: the 2D path's source canvas,
   or on the WebGL path one it fills from the framebuffer and the palettes on demand.  The
   canvas on the page carries the same picture scaled, and is checked separately by DISPLAY.
   `path` says which of the two renderers drew the page. */
export const PICTURE = `(() => {
    const canvas = window.__wofVideo.picture();
    const ctx = canvas.getContext('2d');
    const image = ctx.getImageData(0, 0, canvas.width, canvas.height).data;
    const colours = new Set();
    let hash = 0;
    for (let i = 0; i < image.length; i += 4) {
        colours.add(image[i] << 16 | image[i + 1] << 8 | image[i + 2]);
        hash = (hash * 31 + image[i] + image[i + 1] * 3 + image[i + 2] * 7) >>> 0;
    }
    const lit = (y) => {
        let n = 0;
        for (let x = 0; x < canvas.width; x++) {
            const i = (y * canvas.width + x) * 4;
            if (image[i] || image[i + 1] || image[i + 2]) n++;
        }
        return n;
    };
    return {
        path: window.__wofVideo.path,
        width: canvas.width,
        height: canvas.height,
        colours: colours.size,
        hash,
        rows: {
            playfield: lit(80) + lit(120),
            blankAboveDash: lit(162),
            dashboard: lit(180),
            blankAboveTicker: lit(200),
            ticker: lit(205),
        },
    };
})()`;

/* Where the picture really is on the page and how large its backing store really is. */
export const GEOMETRY = `(() => {
    const canvas = document.getElementById('screen');
    const rect = canvas.getBoundingClientRect();
    return {
        dpr: window.devicePixelRatio,
        window: { width: window.innerWidth, height: window.innerHeight },
        rect: { left: rect.left, top: rect.top, width: rect.width, height: rect.height },
        backing: { width: canvas.width, height: canvas.height },
        path: window.__wofVideo.path,
        shellSays: window.__wofVideo.geometry(),
    };
})()`;

/* Sample points for "the canvas on the page really shows the picture".
 *
 * The final step is a smooth reduction, so a single pixel read at the centre of a framebuffer
 * pixel is a blend of its neighbours - and in a small window one device pixel covers more
 * than one framebuffer pixel.  The points are therefore taken where the framebuffer is flat
 * over a whole neighbourhood, which makes the comparison independent of the filter without
 * making it blind: what is compared is still the colour that belongs at that place.
 *
 * Two things decide the search.  The radius shrinks until the points carry several colours,
 * because the flat parts of a picture are mostly its background and a sample set of one
 * colour would pass against a canvas that had drawn nothing but black.  And no colour may
 * take more than a few points, spread apart, so that the background cannot crowd out the
 * picture. */
export const DISPLAY = `(() => {
    const video = window.__wofVideo;
    const source = video.picture();
    const src = source.getContext('2d').getImageData(0, 0, source.width, source.height).data;
    /* What the displayed canvas holds, read back by the shell: a WebGL canvas keeps no
       drawing buffer once composited, so it is drawn again and read in the same task. */
    const shown = video.readDisplay();
    const display = { width: shown.width, height: shown.height };
    const dst = shown.data;

    const at = (data, width, x, y) => {
        const i = (y * width + x) * 4;
        return [data[i], data[i + 1], data[i + 2]];
    };
    const flat = (x, y, r) => {
        const c = at(src, source.width, x, y);
        for (let dy = -r; dy <= r; dy++) {
            for (let dx = -r; dx <= r; dx++) {
                const q = at(src, source.width, x + dx, y + dy);
                if (q[0] !== c[0] || q[1] !== c[1] || q[2] !== c[2]) return null;
            }
        }
        return c;
    };

    const PER_COLOUR = 5;
    const APART = 48;

    const collect = (r) => {
        const found = [];
        const seen = new Map();
        for (let y = r; y < source.height - r; y += 2) {
            for (let x = r; x < source.width - r; x += 3) {
                const colour = flat(x, y, r);
                if (!colour) continue;
                const key = colour.join(',');
                const kept = seen.get(key) || [];
                if (kept.length >= PER_COLOUR) continue;
                if (kept.some((p) => Math.abs(p.x - x) < APART && Math.abs(p.y - y) < APART)) continue;
                /* The centre of that framebuffer pixel, in the display's device pixels. */
                const dx = Math.min(display.width - 1,
                                    Math.floor((x + 0.5) * display.width / source.width));
                const dy = Math.min(display.height - 1,
                                    Math.floor((y + 0.5) * display.height / source.height));
                const point = { x, y, dx, dy, radius: r, source: colour,
                                display: at(dst, display.width, dx, dy) };
                kept.push(point);
                seen.set(key, kept);
                found.push(point);
            }
        }
        return found;
    };

    let points = [];
    for (const r of [6, 4, 3, 2]) {
        points = collect(r);
        const colours = new Set(points.map((p) => p.source.join(',')));
        if (points.length >= 12 && colours.size >= 4) break;
    }

    const colours = new Set();
    for (let i = 0; i < dst.length; i += 4) {
        colours.add(dst[i] << 16 | dst[i + 1] << 8 | dst[i + 2]);
    }
    return { points, displayColours: colours.size, path: video.path };
})()`;

/* One present() at the size the page currently has, timed in the page.  The first calls warm
   the canvases up; what is reported is the median of the rest, because a single slow frame
   says nothing and an average hides one. */
export const PRESENT_COST = `(() => {
    const times = [];
    for (let i = 0; i < 24; i++) {
        const start = performance.now();
        window.__wofVideo.present();
        times.push(performance.now() - start);
    }
    const kept = times.slice(4).sort((a, b) => a - b);
    return {
        median: kept[Math.floor(kept.length / 2)],
        worst: kept[kept.length - 1],
        best: kept[0],
    };
})()`;

/* The exact picture itself, as a PNG, so that the pytest side can compare every one of the
   136,960 framebuffer pixels with a screenshot instead of a few sample points.  A data URL
   rather than the pixels: the same bytes, a fiftieth of the JSON. */
export const SOURCE_PNG = "window.__wofVideo.picture().toDataURL('image/png')";

/* Which renderer draws the page and what it costs (web/video.js): the path, the reason for
   a fallback, and the frame and present() times the diagnostics overlay shows. */
export const VIDEO = 'window.__wofVideo.stats()';

/* The frame-time measurement of M9 (re/notes/page-video.md): every animation frame's time
   over ms, from a loop of this expression's own, so that it measures any page, the shell's
   earlier ones included; and the time present() took over the same span, from the shell's
   own count where it keeps one.  Where it keeps none, present() is timed by calling it,
   which a page of any age offers the tests. */
export const frameTimes = (ms) => `new Promise((done) => {
    const video = window.__wofVideo;
    const before = video.stats ? video.stats() : null;
    const frames = [];
    const step = (t) => {
        frames.push(t);
        if (frames.length < 2 || t - frames[0] < ${ms}) {
            requestAnimationFrame(step);
            return;
        }
        const after = before ? video.stats() : null;
        const out = {
            frames,
            path: video.path || 'none',
            note: after ? after.note : '',
            dpr: devicePixelRatio,
            window: { width: innerWidth, height: innerHeight },
            backing: { width: video.display.width, height: video.display.height },
            hidden: document.hidden,
        };
        if (after) {
            out.presents = after.presents - before.presents;
            out.presentMs = (after.presentMs - before.presentMs) / Math.max(1, out.presents);
            out.presentBy = 'the shell';
        } else {
            const times = [];
            for (let i = 0; i < 24; i++) {
                const start = performance.now();
                video.present();
                times.push(performance.now() - start);
            }
            out.presents = 20;
            out.presentMs = times.slice(4).reduce((a, b) => a + b, 0) / 20;
            out.presentBy = 'calls';
        }
        done(out);
    };
    requestAnimationFrame(step);
})`;

/* What the shell has put into browser storage: the game's own written files, under the
   wof: prefix (SPEC 6.2, Storage).  Read as the page left it, not as the core holds it. */
export const STORED_FILES = `(() => {
    try {
        const raw = window.localStorage.getItem('wof:files');
        const files = raw ? JSON.parse(raw) : [];
        return files.map((file) => ({ name: file.name, bytes: atob(file.data).length,
                                      text: atob(file.data) }));
    } catch (err) {
        return { error: String(err) };
    }
})()`;

/* The player's aircraft and the pause and flip, as the diagnostics overlay shows them
 * (M4): read off the overlay, the place a person would read them, so the overlay has to
 * be up. */
export const PLAYER = `(() => {
    const text = document.getElementById('overlay').textContent;
    const m = text.match(/player\\s+x (-?\\d+)\\s+y (-?\\d+)\\s+deck state (-?\\d+)\\s+weapon (-?\\d+)(, paused)?(, flip on)?/);
    const c = text.match(/counters\\s+(\\d+) vbl\\s+(\\d+) tick\\s+(\\d+) pass/);
    return m ? { x: +m[1], y: +m[2], deck: +m[3], weapon: +m[4], paused: !!m[5], flip: !!m[6],
                 vblanks: c ? +c[1] : null, ticks: c ? +c[2] : null } : null;
})()`;

/* The weapons as the framebuffer shows them (M5): a hash of the dashboard's weapon counter
   (the two drums at x 32 to 79, rows 180 to 192 of the source canvas) and the number of
   pure white pixels in the rows just above the sea (140 to 159), where nothing is white but
   a burst in the water, the splash of a weapon (the native pictures of a drop show none
   there in any other pass). */
export const WEAPON_VIEW = `(() => {
    const ctx = window.__wofVideo.picture().getContext('2d');
    const counter = ctx.getImageData(32, 180, 48, 13).data;
    let hash = 0;
    for (let i = 0; i < counter.length; i++) {
        hash = (Math.imul(hash, 31) + counter[i]) >>> 0;
    }
    const band = ctx.getImageData(0, 140, 640, 20).data;
    let white = 0;
    for (let i = 0; i < band.length; i += 4) {
        if (band[i] === 255 && band[i + 1] === 255 && band[i + 2] === 255) {
            white++;
        }
    }
    return { counter: hash, white };
})()`;

/* M5 on the page: a click of the button in the climb drops the weapon chosen in the hold,
   and holding it fires the guns.  Read off the framebuffer (WEAPON_VIEW): the counter
   steady before the click, turned after it, and a burst drawn in the water; the guns, which
   the weapon counter does not count, leave it alone.  `view` reads the framebuffer, `player`
   the overlay. */
/* KeyM in flight, the game's Control-S (opt_music_off, re/notes/keys.md): the effects stop
   within a tick and stay silent, and a second press brings them back.  The overlay's pcm line
   is read after the first press, a while later, and after the second. */
export async function muteRun(pressM, overlay, sleep) {
    const out = {};
    await pressM();
    await sleep(800);
    out.muted1 = await overlay();
    await sleep(1500);
    out.muted2 = await overlay();
    await pressM();
    await sleep(1500);
    out.unmuted = await overlay();
    return out;
}

export async function weaponRun(view, player, click, hold, sleep) {
    const before = [];
    for (let i = 0; i < 15; i++) {
        before.push(await view());
        await sleep(50);
    }
    await click();
    const after = [];
    const until = Date.now() + 4000;
    while (Date.now() < until) {
        after.push(await view());
        await sleep(30);
    }
    const settled = await view();
    const air = await player();
    await hold();
    const guns = await view();
    return {
        counterBefore: [...new Set(before.map((v) => v.counter))],
        whiteBefore: Math.max(...before.map((v) => v.white)),
        counterAfter: settled.counter,
        whiteAfter: Math.max(...after.map((v) => v.white)),
        samples: after.length,
        player: air,
        counterGuns: guns.counter,
        playerGuns: await player(),
    };
}

/* M6 on the page: the sky as the framebuffer shows it, the top 150 rows of the source canvas
   as a PNG.  The pytest side looks in it for an enemy aircraft: every opaque pixel of one of
   the 56 frames an enemy aircraft flies with (japplane.shp by the names enemy_frames takes,
   0x025F58), each doubled across the low-resolution playfield, in the colours of map d's
   sky, at one place (tests/conftest.py).  Colour alone does not tell it: the targets'
   bursts round the aircraft and the ships' and the carrier's paint share the fighter's. */
export const SKY_ROWS = 150;
export const SKY_PNG = `(() => {
    const source = window.__wofVideo.picture();
    const canvas = document.createElement('canvas');
    canvas.width = 640;
    canvas.height = ${SKY_ROWS};
    canvas.getContext('2d').drawImage(source, 0, 0, 640, ${SKY_ROWS}, 0, 0, 640, ${SKY_ROWS});
    return canvas.toDataURL('image/png');
})()`;

/* M6 on the page: map d, the first mission of the second rank, whose airfield (world x 3200
   to 3544) sends a fighter up when the aircraft comes within 0x1E0 of it (0x011622,
   re/notes/enemy.md).  From the hold: the lift, the roll east along the deck for 115 ticks
   as tools/m5_autopilot.py rolls, the stick forward, the take-off and the climb to 120,
   since a turn dives, then the turn and on
   west to the island,
   and there back and forth over the airfield for half a minute, the height kept between 70
   and 170 with short taps.  The sky is taken five times on the way, out of the airfield's
   reach (the control: no enemy aircraft can be there yet), and every 400 ms over the
   island.  `keys` holds, lets go and taps the keys by name; `player` reads the overlay and
   `sky` SKY_PNG. */
export async function enemyFlight(keys, player, sky, sleep) {
    const until = async (test, limitMs, stepMs = 100) => {
        for (let waited = 0; waited < limitMs; waited += stepMs) {
            const now = await player();
            if (now && test(now)) {
                return now;
            }
            await sleep(stepMs);
        }
        return player();
    };
    const out = { trail: [], before: [], over: [] };
    out.hold = await player();
    await keys.tap('space', 250);                                 /* the lift goes up */
    out.deck = await until((p) => p.deck === 1 && p.y > 30, 6000);
    await keys.down('right');
    const rollFrom = (await player()).ticks;              /* 115 ticks, as the scripts roll */
    out.rolling = await until((p) => p.ticks >= rollFrom + 115 || p.deck !== 1, 20000, 40);
    await keys.down('up');
    out.air = await until((p) => p.deck === 0, 10000);
    out.climbed = await until((p) => p.y >= 120 || p.deck !== 0, 15000);   /* a turn dives */
    await keys.up('up');
    await keys.up('right');
    let way = 'left';
    await keys.down(way);
    const started = Date.now();
    let zone = null;
    let lastShot = 0;
    while (Date.now() - started < 90000 && (zone === null || Date.now() - zone < 30000)) {
        const p = await player();
        if (!p) {
            await sleep(100);
            continue;
        }
        const now = Date.now();
        out.trail.push([now - started, p.x, p.y, p.deck]);
        if (p.deck !== 0) {
            break;                                               /* down: the run has failed */
        }
        if (p.x > 4700 && p.x < 7000 && out.before.length < 5 && now - lastShot > 1000) {
            out.before.push({ x: p.x, y: p.y, png: await sky() });
            lastShot = now;
        } else if (p.x <= 4600) {
            zone = zone === null ? now : zone;
            if (now - lastShot > 400) {
                out.over.push({ x: p.x, y: p.y, ms: now - zone, png: await sky() });
                lastShot = now;
            }
        }
        if (way === 'left' && p.x < 2900) {
            await keys.up(way);
            way = 'right';
            await keys.down(way);
        } else if (way === 'right' && p.x > 3900) {
            await keys.up(way);
            way = 'left';
            await keys.down(way);
        }
        if (p.y < 70) {
            await keys.tap('up', 120);
        } else if (p.y > 170) {
            await keys.tap('down', 120);
        }
        await sleep(100);
    }
    await keys.up(way);
    out.last = await player();
    return out;
}
