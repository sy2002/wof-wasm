/* graphics.library on indexed pixels, as far as the front end uses it (re/notes/drawing.md).
 *
 * The load and save dialog, the name entry, the high-score list and the story scroller draw
 * with Move, Text, RectFill, Draw, SetAPen, SetBPen and SetDrMd on the RastPort the
 * viewport carries, and with BltTemplate through text_draw and text_draw_justified.  They
 * never open a font, so Text draws topaz 8 out of the Kickstart ROM
 * (re/notes/system-font.md).
 *
 * Two things about this layer are not the blitter library's:
 *
 *   - It does not clip.  There is no Layer on these RastPorts, so on the machine a RectFill
 *     with a negative yMin writes before the plane.  The story scroller needs that: its
 *     plane pointer has walked up the view's memory and every line after the first is drawn
 *     fourteen rows before the current start (re/notes/frontend.md).  What bounds a write
 *     is the view's memory block, which is what bounds the original's too.
 *   - The draw mode decides what a set and a clear bit of a glyph or a template do: JAM1
 *     paints the foreground pen and leaves the rest alone, JAM2 paints the background pen
 *     as well, and COMPLEMENT inverts what is there.  RectFill is a solid rectangle in the
 *     foreground pen, and in COMPLEMENT it inverts, which is what draws the dialog's
 *     selection bar and the line editor's caret.
 */
#include "wof.h"
#include "gen/tables.h"

/* The bounds of the display-memory block a viewport's surface lies in: one of the two view
 * blocks or the ticker plane.  A write outside them is dropped, which is the port's answer
 * to a write that would leave the original's own allocation. */
static void block_of(const wof_vport_t *v, uint32_t *lo, uint32_t *hi)
{
    if (v->plane < WOF_VIEW_BYTES) {
        *lo = 0;
        *hi = WOF_VIEW_BYTES;
    } else if (v->plane < 2u * WOF_VIEW_BYTES) {
        *lo = WOF_VIEW_BYTES;
        *hi = 2u * WOF_VIEW_BYTES;
    } else {
        *lo = 2u * WOF_VIEW_BYTES;
        *hi = WOF_VRAM_BYTES;
    }
}

/* One row of the drawing surface, or 0 when it falls outside the block.  `scroll` is the
 * plane pointer the story scroller advances, so drawing follows the window down the ring. */
static uint8_t *row_of(const wof_vport_t *v, int32_t y, uint32_t *width)
{
    uint32_t lo, hi;
    int32_t  stride = (int32_t)v->bytes_per_row * 8;
    int32_t  at;

    block_of(v, &lo, &hi);
    at = (int32_t)v->plane + ((int32_t)v->scroll + y) * stride;
    if (at < (int32_t)lo || at + stride > (int32_t)hi)
        return 0;
    *width = (uint32_t)stride;
    return wof_f.vram + at;
}

static uint8_t depth_mask(const wof_vport_t *v)
{
    return (uint8_t)((1u << v->depth) - 1u);
}

void wof_gfx_set_apen(wof_vport_t *v, uint8_t pen)
{
    wof_trace_add("os_gfx_set_apen", pen, 0, 0, 0, 0, 0);
    if (v)
        v->apen = pen;
}

void wof_gfx_set_bpen(wof_vport_t *v, uint8_t pen)
{
    wof_trace_add("os_gfx_set_bpen", pen, 0, 0, 0, 0, 0);
    if (v)
        v->bpen = pen;
}

void wof_gfx_set_drmd(wof_vport_t *v, uint8_t mode)
{
    wof_trace_add("os_gfx_set_drmd", mode, 0, 0, 0, 0, 0);
    if (v)
        v->drmd = mode;
}

void wof_gfx_move(wof_vport_t *v, int16_t x, int16_t y)
{
    wof_trace_add("os_gfx_move", x, y, 0, 0, 0, 0);
    if (v) {
        v->cp_x = x;
        v->cp_y = y;
    }
}

/* One pixel in the RastPort's mode.  The depth mask is what keeps a pen of 15 on a
 * four-plane viewport from reaching a fifth plane that is not there. */
static void plot(uint8_t *row, uint32_t width, int32_t x, uint8_t pen, uint8_t mask,
                 uint8_t mode)
{
    if (x < 0 || (uint32_t)x >= width)
        return;
    if (mode == WOF_COMPLEMENT)
        row[x] ^= mask;
    else
        row[x] = (uint8_t)((row[x] & (uint8_t)~mask) | (pen & mask));
}

/* orig graphics.RectFill through the front end's callers: a solid rectangle in the
 * foreground pen, inclusive on all four sides. */
void wof_gfx_rect_fill(wof_vport_t *v, int16_t x0, int16_t y0, int16_t x1, int16_t y1)
{
    wof_trace_add("os_gfx_rectfill", x0, y0, x1, y1, 0, 0);
    if (!v)
        return;
    if (x1 < x0 || y1 < y0)
        return;

    uint8_t mask = depth_mask(v);

    for (int32_t y = y0; y <= y1; y++) {
        uint32_t width = 0;
        uint8_t *row = row_of(v, y, &width);

        if (!row)
            continue;
        for (int32_t x = x0; x <= x1; x++)
            plot(row, width, x, v->apen, mask, v->drmd);
    }
}

/* orig graphics.Draw.  Every Draw the front end makes is parallel to an axis - the four
 * sides of the dialog's boxes and of the name entry's frame - which
 * test_every_draw_the_front_end_makes_is_parallel_to_an_axis holds it to.  A sloped line
 * would need the blitter's line mode, whose pixel pattern is an open point of SPEC 10;
 * this refuses one rather than guessing at it. */
void wof_gfx_draw(wof_vport_t *v, int16_t x, int16_t y)
{
    wof_trace_add("os_gfx_draw", v ? v->cp_x : 0, v ? v->cp_y : 0, x, y, 0, 0);
    if (!v)
        return;

    int16_t x0 = v->cp_x, y0 = v->cp_y;
    uint8_t mask = depth_mask(v);

    v->cp_x = x;
    v->cp_y = y;

    if (x0 == x) {
        int16_t a = y0 < y ? y0 : y, b = y0 < y ? y : y0;

        for (int32_t row_y = a; row_y <= b; row_y++) {
            uint32_t width = 0;
            uint8_t *row = row_of(v, row_y, &width);

            if (row)
                plot(row, width, x, v->apen, mask, v->drmd);
        }
    } else if (y0 == y) {
        int16_t a = x0 < x ? x0 : x, b = x0 < x ? x : x0;
        uint32_t width = 0;
        uint8_t *row = row_of(v, y, &width);

        if (row)
            for (int32_t px = a; px <= b; px++)
                plot(row, width, px, v->apen, mask, v->drmd);
    }
    /* A sloped Draw is not reachable from the front end and is deliberately not drawn. */
}

/* One glyph row of the system font, most significant bit first, and what the draw mode
 * does with its set and clear bits. */
static void put_bits(wof_vport_t *v, int32_t x, int32_t y, uint32_t bits, uint16_t n,
                     const uint8_t *src, uint32_t src_bit)
{
    uint32_t width = 0;
    uint8_t *row = row_of(v, y, &width);
    uint8_t  mask = depth_mask(v);

    (void)bits;
    if (!row)
        return;
    for (uint16_t i = 0; i < n; i++) {
        uint32_t bit = src_bit + i;
        int      on  = (src[bit >> 3] >> (7 - (bit & 7))) & 1;

        if (on)
            plot(row, width, x + i, v->apen, mask, v->drmd);
        else if (v->drmd == WOF_JAM2)
            plot(row, width, x + i, v->bpen, mask, WOF_JAM1);
    }
}

/* orig graphics.Text on a fixed-width font: one cell per character at the pen position,
 * the glyph bits out of the location table, and the pen advanced by the cell width.  A
 * character outside the font's range shows the one extra glyph the table carries for it,
 * as the machine does. */
void wof_gfx_text(wof_vport_t *v, const char *s, uint16_t len)
{
    wof_trace_add("os_gfx_text", len, v ? v->cp_x : 0, v ? v->cp_y : 0, 0, s, len);
    if (!v || !s)
        return;

    if (!wof_tbl_topaz8_present) {
        /* re/notes/system-font.md: without the ROM the dialogs fall back to the game's own
         * font.  The pen still advances by 8 per character, which is what the harness sees
         * and what every position in re/notes/frontend.md was measured against. */
        for (uint16_t i = 0; i < len; i++)
            ;
        v->cp_x = (int16_t)(v->cp_x + len * 8);
        return;
    }

    uint16_t glyphs   = (uint16_t)(wof_tbl_topaz8_hi - wof_tbl_topaz8_lo + 1);
    uint16_t cell     = wof_tbl_topaz8_xsize;
    uint16_t height   = wof_tbl_topaz8_ysize;
    int16_t  baseline = (int16_t)wof_tbl_topaz8_baseline;

    for (uint16_t i = 0; i < len; i++) {
        uint8_t  c  = (uint8_t)s[i];
        uint16_t gi = (c >= wof_tbl_topaz8_lo && c <= wof_tbl_topaz8_hi)
                    ? (uint16_t)(c - wof_tbl_topaz8_lo) : glyphs;
        uint16_t bit_off = wof_tbl_topaz8_loc[gi * 2 + 0];
        uint16_t gw      = wof_tbl_topaz8_loc[gi * 2 + 1];
        int32_t  x       = v->cp_x + (int32_t)i * cell;

        for (uint16_t r = 0; r < height; r++) {
            const uint8_t *src = wof_tbl_topaz8_data + (uint32_t)r * wof_tbl_topaz8_modulo;

            /* The pen position is the baseline, as graphics.library defines it. */
            put_bits(v, x, v->cp_y - baseline + r, 0, gw, src, bit_off);
            if (v->drmd == WOF_JAM2 && gw < cell)
                for (uint16_t b = gw; b < cell; b++) {
                    uint32_t width = 0;
                    uint8_t *row = row_of(v, v->cp_y - baseline + r, &width);

                    if (row)
                        plot(row, width, x + b, v->bpen, depth_mask(v), WOF_JAM1);
                }
        }
    }
    v->cp_x = (int16_t)(v->cp_x + len * cell);
}

/* orig 0x015910 text_draw and 0x015A8C text_draw_justified.  The game's own font is
 * rendered by the CPU into a 1-bit template (text_render, verified in M1) and put on screen
 * with BltTemplate at the pen position, in the RastPort's pens and draw mode.  M1 could
 * only draw it in JAM1 with one pen; this is the rest of that routine. */
static void text_template(wof_vport_t *v, const char *s, uint16_t len, int16_t justify)
{
    static uint8_t template_[1040];        /* the original's MaskBuffer, 80 bytes x 13 rows */
    uint16_t height = wof_font_height();

    if (!v || !height)
        return;

    uint16_t w = wof_text_render(s, len, template_, 0, 0, justify, 640, (int16_t)height);

    if (!w)
        return;

    uint8_t mask = depth_mask(v);

    for (uint16_t r = 0; r < height; r++) {
        uint32_t width = 0;
        uint8_t *row = row_of(v, v->cp_y + r, &width);

        if (!row)
            continue;
        for (uint16_t c = 0; c < w; c++) {
            int32_t x  = v->cp_x + c;
            int     on = (template_[r * 80 + (c >> 3)] >> (7 - (c & 7))) & 1;

            if (on)
                plot(row, width, x, v->apen, mask, v->drmd);
            else if (v->drmd == WOF_JAM2)
                plot(row, width, x, v->bpen, mask, WOF_JAM1);
        }
    }
}

/* orig 0x015A8C text_draw_justified: the surplus over the text's own width is spread over
 * the gaps, which is what makes the story scroller's lines fill the screen. */
void wof_text_draw_justified(wof_vport_t *v, const char *s, uint16_t len, int16_t width)
{
    wof_trace_add("text_draw_just", len, width, v ? v->cp_x : 0, v ? v->cp_y : 0, s, len);
    text_template(v, s, len, width);
}

/* orig 0x015910 text_draw, and 0x018570 text_draw_c, which is it with strlen in front. */
void wof_text_draw_line(wof_vport_t *v, const char *s, uint16_t len)
{
    wof_trace_add("text_draw_c", len, 0, v ? v->cp_x : 0, v ? v->cp_y : 0, s, len);
    text_template(v, s, len, 0);
}
