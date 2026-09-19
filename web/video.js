/* Video: indexed pixels from the core through the per-row palettes to RGBA (SPEC 6.4), and
 * the two-step scaling that puts them on the page in the machine's proportions (SPEC 6.2).
 *
 * The palette is applied here, at presentation, and it is looked up per row, because the
 * original changes colours part-way down the screen and cycles them.  Nothing about the
 * picture is cached between frames for that reason: both the palettes and the row table
 * may have changed since the last pass.
 *
 * A framebuffer pixel is not square on either machine, so no single whole-number factor can
 * fill the window.  Three canvases carry the picture to the page:
 *
 *   source   640 x 214, one RGBA pixel per framebuffer pixel.  putImageData writes here and
 *            nothing else does; software-backed, see below.  It is never on the page.
 *   scaled   the source enlarged by the whole numbers kx and ky with nearest neighbour, so
 *            that every framebuffer pixel is still a block of exactly equal size.
 *   display  the canvas the page shows, exactly the size of the box in device pixels.  The
 *            enlargement is reduced onto it smoothly, which is the one step that may fall
 *            between pixels, and it falls between blocks that are already large.
 */

/* The display box for one 640 x 214 framebuffer, and the VBlank rate, per video standard
 * (SPEC 6.2).  The two belong together: a machine has one of them, not either.
 *
 * On PAL a low-resolution pixel is 16/15 as wide as it is tall, so a framebuffer pixel,
 * which is a high-resolution one, is 8/15 and 640 x 214 is shown as 1024 : 642.  On NTSC,
 * where 320 x 200 fills a 4:3 screen, a low-resolution pixel is 5/6 and the box is 800 : 642.
 * PAL is the default: this disk comes from a PAL region and the machine the port is compared
 * against is a PAL machine. */
export const STANDARDS = {
    pal: { name: 'PAL', hz: 50, boxWidth: 1024, boxHeight: 642 },
    ntsc: { name: 'NTSC', hz: 60, boxWidth: 800, boxHeight: 642 },
};

export function createVideo(canvas, core) {
    const w = core.width;
    const h = core.height;

    const source = document.createElement('canvas');
    source.width = w;
    source.height = h;

    /* willReadFrequently is not the hint it looks like here: it picks a software-backed 2D
       canvas, and in GPU-composited Firefox the accelerated one never shows what
       putImageData wrote - the canvas reads back as a single colour and the player sees a
       black picture.  Headless Firefox composites in software and cannot reproduce it, so
       only the visible check in tests/test_firefox.py catches a regression here.  In Chrome
       the flag is harmless.  Do not remove it as a no-op. */
    const sctx = source.getContext('2d', { alpha: false, willReadFrequently: true });
    const image = sctx.createImageData(w, h);
    const out = new Uint32Array(image.data.buffer);

    /* The other two are only ever drawn into, never read back by the shell, and drawImage is
       not the call the Firefox fault is about; they are left accelerated, because the
       reduction at a Retina fullscreen size is the one piece of per-frame work in the shell
       that is worth a GPU.  The visible Firefox run is what decides this, not the flag. */
    const scaled = document.createElement('canvas');
    const mctx = scaled.getContext('2d', { alpha: false });
    const dctx = canvas.getContext('2d', { alpha: false });

    let standard = STANDARDS.pal;
    let box = { deviceWidth: 0, deviceHeight: 0, left: 0, top: 0 };
    let dpr = 0;
    let kx = 1;
    let ky = 1;

    /* The box is laid out in whole device pixels and only then converted back to CSS pixels,
       so that the browser has nothing left to resample: the backing store is exactly the CSS
       size times devicePixelRatio, and the picture lands on the physical pixel grid. */
    function fit() {
        const ratio = window.devicePixelRatio || 1;
        const availableWidth = Math.max(1, Math.floor(window.innerWidth * ratio));
        const availableHeight = Math.max(1, Math.floor(window.innerHeight * ratio));
        const aspect = standard.boxWidth / standard.boxHeight;

        let deviceWidth = availableWidth;
        let deviceHeight = Math.round(availableWidth / aspect);
        if (deviceHeight > availableHeight) {
            deviceHeight = availableHeight;
            deviceWidth = Math.round(availableHeight * aspect);
        }
        deviceWidth = Math.max(1, Math.min(deviceWidth, availableWidth));
        deviceHeight = Math.max(1, Math.min(deviceHeight, availableHeight));

        const left = Math.round((availableWidth - deviceWidth) / 2);
        const top = Math.round((availableHeight - deviceHeight) / 2);

        if (ratio === dpr && deviceWidth === box.deviceWidth && deviceHeight === box.deviceHeight
            && left === box.left && top === box.top) {
            return;
        }
        dpr = ratio;
        box = { deviceWidth, deviceHeight, left, top };

        canvas.width = deviceWidth;
        canvas.height = deviceHeight;
        canvas.style.width = (deviceWidth / dpr) + 'px';
        canvas.style.height = (deviceHeight / dpr) + 'px';
        canvas.style.left = (left / dpr) + 'px';
        canvas.style.top = (top / dpr) + 'px';
        /* Resizing a canvas resets its context, so the smoothing settings are made again. */
        dctx.imageSmoothingEnabled = true;

        /* The smallest whole numbers whose enlargement is at least as large as the box. */
        kx = Math.max(1, Math.ceil(deviceWidth / w));
        ky = Math.max(1, Math.ceil(deviceHeight / h));
        if (kx > 1 || ky > 1) {
            scaled.width = w * kx;
            scaled.height = h * ky;
            mctx.imageSmoothingEnabled = false;
        }

        draw();
    }

    function draw() {
        if (kx === 1 && ky === 1) {
            /* The enlargement is the identity at this size: the source is the enlargement. */
            dctx.drawImage(source, 0, 0, box.deviceWidth, box.deviceHeight);
            return;
        }
        mctx.drawImage(source, 0, 0, scaled.width, scaled.height);
        dctx.drawImage(scaled, 0, 0, box.deviceWidth, box.deviceHeight);
    }

    function present() {
        const fb = core.framebuffer();
        const rows = core.paletteRows();
        const pal = core.palettes();
        const colours = core.paletteColours;

        for (let y = 0, i = 0; y < h; y++) {
            const base = rows[y] * colours;
            for (let x = 0; x < w; x++, i++) {
                out[i] = pal[base + fb[i]];
            }
        }
        sctx.putImageData(image, 0, 0);
        draw();
    }

    function setStandard(name) {
        standard = STANDARDS[name] || STANDARDS.pal;
        box = { deviceWidth: 0, deviceHeight: 0, left: 0, top: 0 };
        fit();
        return standard;
    }

    function geometry() {
        return {
            standard: standard.name,
            hz: standard.hz,
            ratio: standard.boxWidth + ':' + standard.boxHeight,
            dpr,
            kx,
            ky,
            deviceWidth: box.deviceWidth,
            deviceHeight: box.deviceHeight,
            cssWidth: box.deviceWidth / dpr,
            cssHeight: box.deviceHeight / dpr,
        };
    }

    /* devicePixelRatio changes without a resize event when the window moves to a screen of
       another density or the page is zoomed.  A media query on the ratio the page currently
       has is the only notice a page gets, and it has to be made again for the new one. */
    let density = null;
    function onDensityChange() {
        fit();
        watchDensity();
    }
    function watchDensity() {
        if (density) {
            density.removeEventListener('change', onDensityChange);
        }
        density = window.matchMedia('(resolution: ' + (window.devicePixelRatio || 1) + 'dppx)');
        density.addEventListener('change', onDensityChange);
    }

    window.addEventListener('resize', fit);
    document.addEventListener('fullscreenchange', fit);
    watchDensity();
    fit();

    /* The framebuffer's exact pixels live on the source canvas from here on, and the page
       tests of SPEC section 8 need both them and the canvas the browser really shows. */
    window.__wofVideo = { source, scaled, display: canvas, geometry, present };

    return { present, fit, setStandard, geometry, standard: () => standard };
}
