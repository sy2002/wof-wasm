/* Video: viewports, the per-row palette interface and the composition of the output
 * picture (SPEC 6.4, re/notes/display.md).
 *
 * The original display is planar and composed from several ViewPorts of its own making,
 * each with a 32-word colour table that a copper list turns into COLORxx moves.  The port
 * gives every viewport one indexed surface at its native width - 320 pixels in low
 * resolution, 640 in high - and applies the palette at presentation, one palette per
 * output row.  That is what makes the day and night palettes, the sky-to-ocean split part
 * way down the playfield, the ticker ramp and the 16-step fades expressible without the
 * renderer knowing about any of them.
 *
 * The output is 640 x 214 with low-resolution pixels doubled: the play screen's three
 * viewports stacked as the machine stacks them, and 200 lines for the front-end screens. */
#include "wof.h"

static uint8_t  framebuffer[WOF_FB_W * WOF_FB_H];
static uint16_t palette_rows[WOF_FB_H];
static uint32_t palettes[WOF_PAL_COUNT * WOF_PAL_COLOURS];

static wof_band_t bands[WOF_MAX_BANDS];
static uint8_t    band_count;

const uint8_t  *wof_framebuffer(void)       { return framebuffer; }
const uint16_t *wof_palette_rows(void)      { return palette_rows; }
const uint32_t *wof_palettes(void)          { return palettes; }
uint32_t        wof_framebuffer_width(void) { return WOF_FB_W; }
uint32_t        wof_framebuffer_height(void){ return WOF_FB_H; }
uint32_t        wof_palette_count(void)     { return WOF_PAL_COUNT; }
uint32_t        wof_palette_colours(void)   { return WOF_PAL_COLOURS; }

/* An Amiga colour is 4 bits per component.  Replicating the nibble into both halves of
 * the byte maps 0 to 0 and 15 to 255, which is what every Amiga screenshot does. */
uint32_t wof_colour_rgba(uint16_t rgb4)
{
    uint32_t r = (rgb4 >> 8) & 0xF;
    uint32_t g = (rgb4 >> 4) & 0xF;
    uint32_t b = rgb4 & 0xF;

    return WOF_RGBA(r * 17, g * 17, b * 17);
}

void wof_video_init(void)
{
    wof_mem_set(framebuffer, 0, sizeof framebuffer);
    wof_mem_set(palette_rows, 0, sizeof palette_rows);
    wof_mem_set(palettes, 0, sizeof palettes);
    for (uint32_t p = 0; p < WOF_PAL_COUNT; p++)
        for (uint32_t i = 0; i < WOF_PAL_COLOURS; i++)
            palettes[p * WOF_PAL_COLOURS + i] = WOF_RGBA(0, 0, 0);
    band_count = 0;
}

/* One viewport: an indexed surface plus the BitMap numbers the picture decoder needs.
 * Plane size on the machine is displayed bytes per row times height, with the width
 * rounded up to 16 pixels (re/notes/display.md), so the surface is that wide too. */
wof_vport_t *wof_vport_make(uint16_t width, uint16_t height, uint8_t depth, uint8_t hires)
{
    wof_vport_t *v = (wof_vport_t *)wof_alloc(sizeof(wof_vport_t));

    if (!v)
        return 0;
    v->width         = width;
    v->height        = height;
    v->bytes_per_row = (uint16_t)(((width + 15) / 16) * 2);
    v->rows          = height;
    v->depth         = depth;
    v->hires         = hires;
    v->pixels        = (uint8_t *)wof_alloc((uint32_t)v->bytes_per_row * 8u * height);
    if (!v->pixels)
        return 0;
    return v;
}

/* orig 0x01A74C - BltClear of every plane, which on indexed pixels is the whole surface. */
void wof_vport_clear_planes(wof_vport_t *v)
{
    if (v && v->pixels)
        wof_mem_set(v->pixels, 0, (uint32_t)v->bytes_per_row * 8u * v->rows);
}

void wof_screen_reset(void)
{
    band_count = 0;
}

void wof_screen_band(const wof_vport_t *vp, uint16_t out_y, uint16_t rows, uint16_t src_y,
                     uint16_t palette)
{
    if (band_count >= WOF_MAX_BANDS || !vp)
        return;

    wof_band_t *b = &bands[band_count++];

    b->vp      = vp;
    b->out_y   = out_y;
    b->rows    = rows;
    b->src_y   = src_y;
    b->palette = palette;
}

/* The bands and their colour tables become the framebuffer, the palette tables and the
 * row-to-palette map the shell reads.  Rows no band covers stay black through the blank
 * palette at index 0, which is what the copper's BPLCON0 = 0x0200 gives on the machine. */
void wof_screen_present(void)
{
    wof_mem_set(framebuffer, 0, sizeof framebuffer);
    for (uint32_t y = 0; y < WOF_FB_H; y++)
        palette_rows[y] = WOF_PAL_BLANK;
    for (uint32_t i = 0; i < WOF_PAL_COLOURS; i++)
        palettes[WOF_PAL_BLANK * WOF_PAL_COLOURS + i] = WOF_RGBA(0, 0, 0);

    for (uint8_t i = 0; i < band_count; i++) {
        const wof_band_t  *b = &bands[i];
        const wof_vport_t *v = b->vp;
        uint32_t pal = b->palette < WOF_PAL_COUNT ? b->palette : WOF_PAL_BLANK;

        for (uint32_t c = 0; c < WOF_PAL_COLOURS; c++)
            palettes[pal * WOF_PAL_COLOURS + c] = wof_colour_rgba(v->colours[c]);

        uint32_t src_stride = (uint32_t)v->bytes_per_row * 8u;

        for (uint32_t r = 0; r < b->rows; r++) {
            uint32_t oy = b->out_y + r;
            uint32_t sy = b->src_y + r;

            if (oy >= WOF_FB_H || sy >= v->rows)
                break;

            const uint8_t *src = v->pixels + sy * src_stride;
            uint8_t       *out = framebuffer + oy * WOF_FB_W;

            palette_rows[oy] = (uint16_t)pal;

            if (v->hires) {
                uint32_t n = v->width < WOF_FB_W ? v->width : WOF_FB_W;
                wof_mem_copy(out, src, n);
            } else {
                uint32_t n = v->width * 2u < WOF_FB_W ? v->width : WOF_FB_W / 2u;
                for (uint32_t x = 0; x < n; x++) {
                    out[x * 2 + 0] = src[x];
                    out[x * 2 + 1] = src[x];
                }
            }
        }
    }
}
