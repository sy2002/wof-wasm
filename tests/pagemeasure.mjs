/* The expressions both page harnesses evaluate inside the page, kept in one place so that
 * the Chrome run and the Firefox run measure the same things in the same way.
 *
 * Each one returns plain data.  Every judgement about that data is made on the pytest side
 * (tests/conftest.py), and the geometry is measured off the DOM - getBoundingClientRect, the
 * canvas backing store, innerWidth, devicePixelRatio - never taken from what the shell says
 * about itself.  The shell's own numbers travel as `shellSays` for a failure message only.
 */

/* The exact framebuffer pixels.  Since the picture is scaled in two steps (SPEC 6.2) they
   exist only on the source canvas, which the shell names for these tests; the canvas on the
   page carries the same picture resampled, and is checked separately by DISPLAY. */
export const PICTURE = `(() => {
    const canvas = window.__wofVideo.source;
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
    const source = video.source;
    const display = video.display;
    const src = source.getContext('2d').getImageData(0, 0, source.width, source.height).data;
    const dst = display.getContext('2d').getImageData(0, 0, display.width, display.height).data;

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
    return { points, displayColours: colours.size };
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

/* The source canvas itself, as a PNG, so that the pytest side can compare every one of the
   136,960 framebuffer pixels with a screenshot instead of a few sample points.  A data URL
   rather than the pixels: the same bytes, a fiftieth of the JSON. */
export const SOURCE_PNG = "window.__wofVideo.source.toDataURL('image/png')";

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
    const m = text.match(/player\\s+x (-?\\d+)\\s+y (-?\\d+)\\s+deck state (-?\\d+)(, paused)?(, flip on)?/);
    const c = text.match(/counters\\s+(\\d+) vbl\\s+(\\d+) tick\\s+(\\d+) pass/);
    return m ? { x: +m[1], y: +m[2], deck: +m[3], paused: !!m[4], flip: !!m[5],
                 vblanks: c ? +c[1] : null, ticks: c ? +c[2] : null } : null;
})()`;
