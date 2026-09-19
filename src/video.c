/* Video: the indexed framebuffer, the palette tables and the per-row palette selection of
 * SPEC 6.4, plus the M0 test pattern.
 *
 * The original display is planar and composed from more than one ViewPort with different
 * palettes.  The port draws 8-bit indices and applies the palette at presentation, one
 * palette per output row, so that fades, day and night, colour cycling and a palette change
 * part-way down the screen all work the way they do on the machine.
 *
 * The drawing primitives of the original arrive with M1; wof_video_test_pattern is M0
 * scaffolding and goes away with them. */
#include "wof.h"

static uint8_t  framebuffer[WOF_FB_W * WOF_FB_H];
static uint16_t palette_rows[WOF_FB_H];
static uint32_t palettes[WOF_PAL_COUNT * WOF_PAL_COLOURS];

static const wof_draw_t display_list[1];   /* nothing appends to it before M1 */

const uint8_t  *wof_framebuffer(void)       { return framebuffer; }
const uint16_t *wof_palette_rows(void)      { return palette_rows; }
const uint32_t *wof_palettes(void)          { return palettes; }
uint32_t        wof_framebuffer_width(void) { return WOF_FB_W; }
uint32_t        wof_framebuffer_height(void){ return WOF_FB_H; }
uint32_t        wof_palette_count(void)     { return WOF_PAL_COUNT; }
uint32_t        wof_palette_colours(void)   { return WOF_PAL_COLOURS; }

const void *wof_display_list(uint32_t *count)
{
    if (count)
        *count = 0;
    return display_list;
}

/* The two M0 palettes are built, not taken from the disk: the game's own tables are M1.
 * They are deliberately far apart so that the split down the screen is unmistakable. */
void wof_video_init(void)
{
    for (uint32_t i = 0; i < WOF_PAL_COLOURS; i++) {
        palettes[i]                    = WOF_RGBA(i * 4, i * 6, 60 + i * 6);  /* steel blue */
        palettes[WOF_PAL_COLOURS + i]  = WOF_RGBA(60 + i * 6, i * 5, i * 2);  /* amber      */
    }

    /* Top half through palette 0, bottom half through palette 1.  Both halves of the test
     * pattern draw the same indices, so any difference on screen is the palette. */
    for (uint32_t y = 0; y < WOF_FB_H; y++)
        palette_rows[y] = (uint16_t)(y < WOF_FB_H / 2 ? 0 : 1);

    wof_mem_set(framebuffer, 0, sizeof framebuffer);
}

static void fill(int32_t x, int32_t y, int32_t w, int32_t h, uint8_t index)
{
    if (x < 0) { w += x; x = 0; }
    if (y < 0) { h += y; y = 0; }
    if (x + w > WOF_FB_W) w = WOF_FB_W - x;
    if (y + h > WOF_FB_H) h = WOF_FB_H - y;
    if (w <= 0 || h <= 0)
        return;

    for (int32_t r = 0; r < h; r++)
        wof_mem_set(&framebuffer[(y + r) * WOF_FB_W + x], index, (uint32_t)w);
}

#define BAND_H  (WOF_FB_H / 2)
#define MARGIN  20
#define BAR_W   (WOF_FB_W - 2 * MARGIN)

#define IDX_OFF     6
#define IDX_ON     31
#define IDX_FRAME   4

/* One band of the test pattern.  Both bands are identical, which is the point: they differ
 * on screen only because wof_palette_rows sends them through different palettes. */
static void draw_band(int32_t top)
{
    /* A 32-step ramp over the full width: the palette itself, left to right. */
    for (int32_t i = 0; i < WOF_PAL_COLOURS; i++)
        fill(i * (WOF_FB_W / WOF_PAL_COLOURS), top + 4,
             WOF_FB_W / WOF_PAL_COLOURS, 16, (uint8_t)i);

    /* Logic ticks: 15 cells, one lit.  At the original's 15 Hz this sweeps once a second,
     * so a wrong tick rate is visible without reading a number. */
    for (int32_t i = 0; i < 15; i++)
        fill(MARGIN + i * (BAR_W / 15), top + 24, BAR_W / 15 - 2, 16,
             (uint32_t)i == wof_s.ticks % 15 ? IDX_ON : IDX_OFF);

    /* VBlanks: 60 cells.  One sweep a second at 60 Hz, 1.2 seconds at 50 Hz. */
    for (int32_t i = 0; i < 60; i++)
        fill(MARGIN + i * (BAR_W / 60), top + 44, BAR_W / 60 - 2, 16,
             (uint32_t)i == wof_s.vblanks % 60 ? IDX_ON : IDX_OFF);

    /* The five raw controller bits of SPEC 6.1, in bit order: down, up, right, left, fire.
     * Box n carries n + 1 tally marks so that it can be identified without a caption. */
    for (int32_t b = 0; b < 5; b++) {
        int32_t x   = MARGIN + b * 125;
        int32_t lit = (wof_s.raw >> b) & 1;

        fill(x, top + 64, 100, 24, IDX_FRAME);
        fill(x + 2, top + 66, 96, 20, lit ? IDX_ON : IDX_OFF);
        for (int32_t m = 0; m <= b; m++)
            fill(x + 10 + m * 8, top + 70, 4, 12, lit ? IDX_FRAME : IDX_ON);
    }

    /* The entropy stream (SPEC 7.3): one value per logic tick, hashed across 64 cells.  It
     * is here so that the picture is a function of the seed and nothing else, which is what
     * the determinism test checks. */
    for (int32_t c = 0; c < 64; c++) {
        uint32_t h = (uint32_t)wof_s.noise ^ ((uint32_t)wof_s.noise >> 5) ^ (uint32_t)(c * 37);
        fill(c * 10, top + 90, 10, 6, (uint8_t)(h & (WOF_PAL_COLOURS - 1)));
    }

    /* Passes: a block that steps once per wof_pass call.  It moves four times as fast as
     * the tick bar when the clock is right. */
    fill((int32_t)(wof_s.passes % 80) * 8, top + 97, 8, 3, IDX_ON);
}

void wof_video_test_pattern(void)
{
    wof_mem_set(framebuffer, 0, sizeof framebuffer);
    draw_band(0);
    draw_band(BAND_H);
}
