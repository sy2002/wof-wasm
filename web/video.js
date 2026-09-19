/* Video: indexed pixels from the core through the per-row palettes to RGBA (SPEC 6.4).
 *
 * The palette is applied here, at presentation, and it is looked up per row, because the
 * original changes colours part-way down the screen and cycles them.  Nothing about the
 * picture is cached between frames for that reason: both the palettes and the row table
 * may have changed since the last pass. */

export function createVideo(canvas, core) {
    const w = core.width;
    const h = core.height;

    canvas.width = w;
    canvas.height = h;

    const ctx = canvas.getContext('2d', { alpha: false });
    const image = ctx.createImageData(w, h);
    const out = new Uint32Array(image.data.buffer);
    let scale = 1;

    /* Integer scaling only: a fractional factor would blur or unevenly duplicate the
       original's pixels.  The 4:3 pixel-aspect option belongs to the shell polish of M9. */
    function fit() {
        const k = Math.max(1, Math.floor(Math.min(window.innerWidth / w, window.innerHeight / h)));
        if (k === scale) {
            return;
        }
        scale = k;
        canvas.style.width = (w * k) + 'px';
        canvas.style.height = (h * k) + 'px';
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
        ctx.putImageData(image, 0, 0);
    }

    fit();
    window.addEventListener('resize', fit);

    return { present, fit, scale: () => scale };
}
