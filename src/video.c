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
    wof_f.vram_used = 0;
    for (uint32_t i = 0; i < WOF_VP_MAX; i++) {
        wof_f.vport[i].next    = WOF_VP_NONE;
        wof_f.vport[i].ring_at = WOF_VP_RING_NONE;
    }

    wof_mem_set(framebuffer, 0, sizeof framebuffer);
    wof_mem_set(palette_rows, 0, sizeof palette_rows);
    wof_mem_set(palettes, 0, sizeof palettes);
    for (uint32_t p = 0; p < WOF_PAL_COUNT; p++)
        for (uint32_t i = 0; i < WOF_PAL_COLOURS; i++)
            palettes[p * WOF_PAL_COLOURS + i] = WOF_RGBA(0, 0, 0);
    band_count = 0;
}

/* A viewport's surface.  The record names it by an offset, so that nothing in the core's
 * state is a host pointer and a loaded state brings the picture back with the logic. */
uint8_t *wof_vport_pixels(const wof_vport_t *v)
{
    return wof_f.vram + (v->plane < WOF_VRAM_BYTES ? v->plane : 0);
}

/* orig 0x0167F2 vport_init_bitmap - the geometry, the plane out of the view's running
 * memory pointer, and both colour tables cleared.  Plane size on the machine is displayed
 * bytes per row times height, with the width rounded up to 16 pixels
 * (re/notes/display.md), so the indexed surface is that wide too. */
void wof_vport_init_bitmap(wof_vport_t *v, uint32_t *mem, uint16_t width, uint16_t height,
                           uint8_t depth)
{
    v->out_y         = 0;
    v->width         = width;
    v->height        = height;
    v->split_on      = 0;
    v->disp_rows     = height;
    v->bytes_per_row = (uint16_t)(((width + 15) & 0xFFF0u) >> 3);
    v->rows          = height;
    v->depth         = depth;
    v->hires         = (uint8_t)(v->bytes_per_row > 0x3C);
    v->scroll        = 0;
    v->ring_at       = WOF_VP_RING_NONE;
    v->ramp          = 0;
    v->plane         = *mem;
    *mem += (uint32_t)v->bytes_per_row * 8u * height;

    /* graphics.InitRastPort, which vport_init_bitmap calls on the RastPort the viewport
     * carries: the foreground pen is 0xFF, the background 0 and the draw mode JAM2, and
     * draw_set_target then ANDs the pen with the depth mask.  The briefing draws its text
     * without ever setting a pen, so that is the pen its text comes out in. */
    v->apen = 0xFF;
    v->bpen = 0;
    v->drmd = WOF_JAM2;
    v->cp_x = 0;
    v->cp_y = 0;

    for (uint32_t i = 0; i < WOF_PAL_COLOURS; i++) {
        v->colours[i]  = 0;
        v->colours2[i] = 0;
    }
}

/* The M1 viewer's own viewports, which go with it.  They come out of the same display
 * memory, after the two views, so that nothing has to know about both. */
wof_vport_t *wof_vport_make(uint16_t width, uint16_t height, uint8_t depth, uint8_t hires)
{
    static uint8_t next = WOF_VP_FIXED;

    if (next >= WOF_VP_MAX)
        return 0;

    wof_vport_t *v = &wof_f.vport[next++];
    uint32_t     bpr = ((uint32_t)((width + 15) & 0xFFF0u)) >> 3;

    if ((uint32_t)bpr * 8u * height > WOF_VRAM_BYTES - wof_f.vram_used)
        return 0;
    wof_vport_init_bitmap(v, &wof_f.vram_used, width, height, depth);
    v->hires = hires;
    v->next  = WOF_VP_NONE;
    return v;
}

/* orig 0x01A74C - BltClear of every plane, which on indexed pixels is the whole surface. */
void wof_vport_clear_planes(wof_vport_t *v)
{
    if (v)
        wof_mem_set(wof_vport_pixels(v), 0, (uint32_t)v->bytes_per_row * 8u * v->rows);
}

void wof_screen_reset(void)
{
    band_count = 0;
}

/* One run of output rows that share a source row and a set of colours.  The colours travel
 * with the band rather than being taken from the viewport, because the mechanisms of
 * SPEC 6.4 that change colours part-way down a screen - the story scroller's two grey
 * ramps, the sky-to-ocean split, the ticker ramp - are exactly runs of rows of one viewport
 * with a colour table of their own.  `src_row` may lie past the viewport's bitmap: the
 * story scroller displays 230 rows from a plane pointer that has walked past a 200-row
 * bitmap, and what it reads there is the cleared rest of the view's memory. */
void wof_screen_band(const wof_vport_t *vp, uint16_t out_y, uint16_t rows, int32_t src_row,
                     const uint16_t *colours)
{
    if (band_count >= WOF_MAX_BANDS || !vp || !rows)
        return;

    wof_band_t *b = &bands[band_count++];

    b->out_y   = out_y;
    b->rows    = rows;
    b->src_row = src_row;
    b->stride  = (uint16_t)(vp->bytes_per_row * 8u);
    b->width   = vp->width;
    b->hires   = vp->hires;
    b->plane   = vp->plane;
    for (uint32_t i = 0; i < WOF_PAL_COLOURS; i++)
        b->colours[i] = colours ? colours[i] : vp->colours[i];
}

/* Two bands that want the same colours share a palette.  That is what keeps the number of
 * palettes down to what the screen really has: the story scroller's 33 bands carry 16
 * distinct tables, and a screen of one viewport carries one. */
static uint16_t palette_for(const uint16_t *colours, uint16_t *used)
{
    for (uint16_t p = 1; p < *used; p++) {
        uint32_t i = 0;
        while (i < WOF_PAL_COLOURS &&
               palettes[p * WOF_PAL_COLOURS + i] == wof_colour_rgba(colours[i]))
            i++;
        if (i == WOF_PAL_COLOURS)
            return p;
    }
    if (*used >= WOF_PAL_COUNT)
        return WOF_PAL_BLANK;               /* more colour tables than SPEC 6.4 budgets */

    uint16_t p = (*used)++;

    for (uint32_t i = 0; i < WOF_PAL_COLOURS; i++)
        palettes[p * WOF_PAL_COLOURS + i] = wof_colour_rgba(colours[i]);
    return p;
}

/* The bands become the framebuffer, the palette tables and the row-to-palette map the
 * shell reads.  Rows no band covers stay black through the blank palette at index 0, which
 * is what the copper's BPLCON0 = 0x0200 gives on the machine. */
void wof_screen_present(void)
{
    uint16_t used = 1;                      /* palette 0 is the blank one */

    wof_mem_set(framebuffer, 0, sizeof framebuffer);
    for (uint32_t y = 0; y < WOF_FB_H; y++)
        palette_rows[y] = WOF_PAL_BLANK;
    for (uint32_t p = 0; p < WOF_PAL_COUNT; p++)
        for (uint32_t i = 0; i < WOF_PAL_COLOURS; i++)
            palettes[p * WOF_PAL_COLOURS + i] = WOF_RGBA(0, 0, 0);

    for (uint8_t i = 0; i < band_count; i++) {
        const wof_band_t *b = &bands[i];
        uint16_t pal = palette_for(b->colours, &used);

        for (uint32_t r = 0; r < b->rows; r++) {
            uint32_t oy = (uint32_t)b->out_y + r;
            int32_t  sy = b->src_row + (int32_t)r;

            if (oy >= WOF_FB_H)
                break;
            palette_rows[oy] = pal;

            int32_t  offset = (int32_t)b->plane + sy * (int32_t)b->stride;
            uint8_t *out    = framebuffer + oy * WOF_FB_W;

            if (sy < 0 || offset < 0 ||
                (uint32_t)offset + b->width > WOF_VRAM_BYTES)
                continue;                   /* outside the display memory: black */

            const uint8_t *src = wof_f.vram + offset;

            if (b->hires) {
                uint32_t n = b->width < WOF_FB_W ? b->width : WOF_FB_W;
                wof_mem_copy(out, src, n);
            } else {
                uint32_t n = b->width * 2u < WOF_FB_W ? b->width : WOF_FB_W / 2u;
                for (uint32_t x = 0; x < n; x++) {
                    out[x * 2 + 0] = src[x];
                    out[x * 2 + 1] = src[x];
                }
            }
        }
    }
}
