// web/video.js, lines 115-128
/* The framebuffer through the palette of each row, as RGBA words in the byte order of an
   ImageData, which is the order the core keeps its palette words in. */
function convert(core, out) {
    const fb = core.framebuffer();
    const rows = core.paletteRows();
    const pal = core.palettes();
    const colours = core.paletteColours;
    for (let y = 0, i = 0; y < core.height; y++) {
        const base = rows[y] * colours;
        for (let x = 0; x < core.width; x++, i++) {
            out[i] = pal[base + fb[i]];
        }
    }
}
