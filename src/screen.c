/* Views, viewports and what reaches the output picture (re/notes/display.md, SPEC 6.4).
 *
 * The original keeps two complete views, each a chain of ViewPort records with its own
 * bitplanes and its own copper list, and swaps them by writing COP1LC.  The port keeps the
 * same two views and the same chain, but a viewport is one indexed surface and a 32-word
 * colour table, and "installing a copper list" is nothing more than saying which view the
 * picture is composed from.  Everything the copper builder does that is visible - the
 * blank line above a lower viewport, the colour tables, the story scroller's two grey
 * ramps and its plane-pointer reload - comes out of the bands this file hands to
 * src/video.c, one per run of output rows that share a source row and a set of colours.
 *
 * What is not ported, because it has no meaning without a copper: the list buffers, the
 * sprite parking, the data-fetch and window registers, the plane pointers, and
 * cop_rotate_unused.  SPEC 6.6 marks all of that `replace`.  What is kept of cop_install
 * is the one thing a waiting routine can see: it clears vblank_flag, so the next
 * wait_vblank really waits.
 */
#include "wof.h"
#include "coro.h"

#define VP(i) (&wof_f.vport[i])

/* ------------------------------------------------------------------ display memory */

/* orig 0x016670 display_init, as far as M3 needs it: the two view blocks and the ticker
 * plane, out of the one block the port has instead of chip memory.  The original also
 * allocates the blank copper list, the null sprite and three copper buffers; none of them
 * has a meaning here (SPEC 6.6). */
void wof_display_init(void)
{
    wof_f.vram_used      = 0;
    wof_f.view_base[0]   = 0;
    wof_f.view_base[1]   = WOF_VIEW_BYTES;
    wof_f.ticker_base    = 2u * WOF_VIEW_BYTES;
    wof_f.vram_used      = WOF_VRAM_BYTES;
    wof_f.view_first[0]  = WOF_VP_NONE;
    wof_f.view_first[1]  = WOF_VP_NONE;
    wof_f.front_view     = WOF_VIEW_A;
    wof_f.back_view      = WOF_VIEW_B;
    wof_mem_set(wof_f.vram, 0, WOF_VRAM_BYTES);

    /* Only the first viewport of each view has a second colour table: coltab_a1_split and
     * coltab_b1_split, the ocean palette below the horizon (re/notes/display.md). */
    for (uint8_t i = 0; i < WOF_VP_MAX; i++) {
        wof_f.vport[i].next         = WOF_VP_NONE;
        wof_f.vport[i].ring_at      = WOF_VP_RING_NONE;
        wof_f.vport[i].has_colours2 = (uint8_t)(i == WOF_VP_A1 || i == WOF_VP_B1);
    }
    VP(WOF_VP_A1)->plane = wof_f.view_base[WOF_VIEW_A];
    VP(WOF_VP_B1)->plane = wof_f.view_base[WOF_VIEW_B];
    VP(WOF_VP_TICKER)->plane = wof_f.ticker_base;
}

wof_vport_t *wof_front_vport(void)
{
    uint8_t i = wof_f.view_first[wof_f.front_view];

    return i == WOF_VP_NONE ? 0 : VP(i);
}

wof_vport_t *wof_back_vport(void)
{
    uint8_t i = wof_f.view_first[wof_f.back_view];

    return i == WOF_VP_NONE ? 0 : VP(i);
}

/* orig 0x01692C view_layout - the view's memory cleared, then every viewport of the chain
 * given its surface out of the running memory pointer.  The original clears a fixed
 * 0xACD0 bytes, which is its whole half of the plane block; the port clears its whole
 * view block, which is the same statement about the same memory. */
void wof_view_layout(uint8_t view)
{
    uint32_t at = wof_f.view_base[view];

    wof_mem_set(wof_f.vram + at, 0, WOF_VIEW_BYTES);
    for (uint8_t i = wof_f.view_first[view]; i != WOF_VP_NONE; i = VP(i)->next)
        wof_vport_init_bitmap(VP(i), &at, VP(i)->width, VP(i)->height, VP(i)->depth);
}

/* orig 0x01A9CA view_copy with 0x01A834 and 0x01A8C4 - both views brought level: the
 * bitmaps with BltBitMap, and the split fields and both colour tables, viewport by
 * viewport.  The chains are laid out alike, so walking them together is the same walk. */
void wof_view_copy(uint8_t from, uint8_t to)
{
    uint8_t a = wof_f.view_first[from];
    uint8_t b = wof_f.view_first[to];

    while (a != WOF_VP_NONE && b != WOF_VP_NONE) {
        wof_vport_t *s = VP(a), *d = VP(b);
        uint32_t     n = (uint32_t)s->bytes_per_row * 8u * s->rows;

        if (n > (uint32_t)d->bytes_per_row * 8u * d->rows)
            n = (uint32_t)d->bytes_per_row * 8u * d->rows;
        wof_mem_copy(wof_vport_pixels(d), wof_vport_pixels(s), n);
        for (uint32_t i = 0; i < WOF_PAL_COLOURS; i++) {
            d->colours[i]  = s->colours[i];
            d->colours2[i] = s->colours2[i];
        }
        d->has_colours2 = s->has_colours2;
        d->split_line   = s->split_line;
        d->split_on     = s->split_on;
        a = s->next;
        b = d->next;
    }
}

/* ------------------------------------------------------------------ showing a view */

/* orig 0x01AA0E cop_install, as far as anything can see it: the list becomes the current
 * one and vblank_flag is cleared, so the next wait really waits for the next VBlank. */
static void cop_install(void)
{
    wof_g.vblank_flag = 0;
}

/* orig 0x016F20 view_show - the view is installed and the other one becomes the back view.
 * front_rastport, front_bitmap and their back counterparts collapse into the viewport
 * itself here, because the port's viewport is its own BitMap and RastPort. */
void wof_view_show(uint8_t view)
{
    cop_install();
    wof_f.front_view = view;
    wof_f.back_view  = (uint8_t)(view == WOF_VIEW_A ? WOF_VIEW_B : WOF_VIEW_A);
}

/* orig 0x01AA3E wait_vblank - the flag vblank_server sets on every VBlank, consumed.  When
 * it is already set there is no wait at all, which is what makes a pass that took longer
 * than a frame carry straight on. */
wof_co_t wof_wait_vblank(void)
{
    wof_ctx_t *c = &wof_f.co_vblank;

    CO_BEGIN(c);
    CO_WAIT_UNTIL(c, wof_g.vblank_flag != 0);
    wof_g.vblank_flag = 0;
    CO_END(c);
}

/* orig 0x016FC4 view_show_wait. */
wof_co_t wof_view_show_wait(uint8_t view)
{
    wof_ctx_t *c = &wof_f.co_show;

    CO_BEGIN(c);
    wof_view_show(view);
    CO_CALL(c, &wof_f.co_vblank, wof_wait_vblank());
    CO_END(c);
}

/* orig 0x01A9FC cop_show_wait(cop_blank) - the black screen every screen_ routine puts up
 * before it lays its viewports out.  The port has no copper list to install, so what is
 * left is the picture going black for one VBlank. */
wof_co_t wof_cop_show_blank(void)
{
    wof_ctx_t *c = &wof_f.co_show;

    CO_BEGIN(c);
    wof_f.view_first[0] = WOF_VP_NONE;
    wof_f.view_first[1] = WOF_VP_NONE;
    cop_install();
    CO_CALL(c, &wof_f.co_vblank, wof_wait_vblank());
    CO_END(c);
}

/* ------------------------------------------------------------------ the screens */

static void chain(uint8_t view, uint8_t first, uint8_t second)
{
    wof_f.view_first[view] = first;
    VP(first)->next = second;
    if (second != WOF_VP_NONE)
        VP(second)->next = WOF_VP_NONE;
}

/* orig 0x016A98 view_set_picture on its own: the rank selection rebuilds the back view
 * with it when the load dialog is cancelled. */
void wof_view_set_picture(uint8_t view)
{
    uint8_t first = (uint8_t)(view == WOF_VIEW_A ? WOF_VP_A1 : WOF_VP_B1);

    chain(view, first, WOF_VP_NONE);
    VP(first)->width  = 320;
    VP(first)->height = 200;
    VP(first)->depth  = 5;
    wof_view_layout(view);
}

/* orig 0x016A98 view_set_picture and 0x016AD8 screen_picture - both views, 320 x 200 with
 * five planes, and view A shown. */
wof_co_t wof_screen_picture(void)
{
    wof_ctx_t *c = &wof_f.co_screen;

    CO_BEGIN(c);
    CO_CALL(c, &wof_f.co_show, wof_cop_show_blank());
    for (uint8_t view = 0; view < 2; view++) {
        uint8_t first = (uint8_t)(view == WOF_VIEW_A ? WOF_VP_A1 : WOF_VP_B1);

        chain(view, first, WOF_VP_NONE);
        VP(first)->width  = 320;
        VP(first)->height = 200;
        VP(first)->depth  = 5;
        wof_view_layout(view);
    }
    CO_CALL(c, &wof_f.co_show, wof_view_show_wait(WOF_VIEW_A));
    CO_END(c);
}

/* orig 0x016A16 view_set_story and 0x016A60 screen_story - both views, 640 x 200 with one
 * plane at display line 5, and 230 rows shown, which is what makes the bitmap a ring. */
wof_co_t wof_screen_story(void)
{
    wof_ctx_t *c = &wof_f.co_screen;

    CO_BEGIN(c);
    CO_CALL(c, &wof_f.co_show, wof_cop_show_blank());
    for (uint8_t view = 0; view < 2; view++) {
        uint8_t first = (uint8_t)(view == WOF_VIEW_A ? WOF_VP_A1 : WOF_VP_B1);

        chain(view, first, WOF_VP_NONE);
        VP(first)->width  = 640;
        VP(first)->height = 200;
        VP(first)->depth  = 1;
        wof_view_layout(view);
        VP(first)->out_y     = 5;
        VP(first)->disp_rows = 0xE6;          /* 230 */
    }
    CO_CALL(c, &wof_f.co_show, wof_view_show_wait(WOF_VIEW_A));
    CO_END(c);
}

/* orig 0x016B04 screen_hires3 - both views, 640 x 147 with three planes. */
wof_co_t wof_screen_hires3(void)
{
    wof_ctx_t *c = &wof_f.co_screen;

    CO_BEGIN(c);
    CO_CALL(c, &wof_f.co_show, wof_cop_show_blank());
    for (uint8_t view = 0; view < 2; view++) {
        uint8_t first = (uint8_t)(view == WOF_VIEW_A ? WOF_VP_A1 : WOF_VP_B1);

        chain(view, first, WOF_VP_NONE);
        VP(first)->width  = 640;
        VP(first)->height = 0x93;             /* 147 */
        VP(first)->depth  = 3;
        wof_view_layout(view);
    }
    CO_CALL(c, &wof_f.co_show, wof_view_show_wait(WOF_VIEW_A));
    CO_END(c);
}

/* orig 0x0169A4 screen_dialog - the back view only, 320 x 200 with four planes, and it is
 * not shown: the caller draws on it first and shows it afterwards. */
wof_co_t wof_screen_dialog(void)
{
    wof_ctx_t *c = &wof_f.co_screen;

    CO_BEGIN(c);
    CO_CALL(c, &wof_f.co_show, wof_cop_show_blank());
    {
        uint8_t view  = wof_f.back_view;
        uint8_t first = (uint8_t)(view == WOF_VIEW_A ? WOF_VP_A1 : WOF_VP_B1);

        chain(view, first, WOF_VP_NONE);
        VP(first)->width  = 320;
        VP(first)->height = 200;
        VP(first)->depth  = 4;
        wof_view_layout(view);
    }
    CO_END(c);
}

/* orig 0x016D7A screen_hiscore - view A alone, 320 x 75 with five planes at line 0 and
 * 640 x 145 with four at line 76.  It needs more memory than one view's half and runs over
 * into the other one on the machine; the port gives each view a block of its own, so the
 * two viewports simply fit. */
wof_co_t wof_screen_hiscore(void)
{
    wof_ctx_t *c = &wof_f.co_screen;

    CO_BEGIN(c);
    CO_CALL(c, &wof_f.co_show, wof_cop_show_blank());
    chain(WOF_VIEW_A, WOF_VP_A1, WOF_VP_A2);
    VP(WOF_VP_A1)->width  = 320;
    VP(WOF_VP_A1)->height = 0x4B;             /* 75 */
    VP(WOF_VP_A1)->depth  = 5;
    VP(WOF_VP_A2)->width  = 640;
    VP(WOF_VP_A2)->height = 0x91;             /* 145 */
    VP(WOF_VP_A2)->depth  = 4;
    wof_view_layout(WOF_VIEW_A);
    VP(WOF_VP_A2)->out_y = 0x4C;              /* 76 */
    CO_END(c);
}

/* ------------------------------------------------------------- what reaches the output */

/* The story scroller's two grey ramps (orig 0x017D4E story_copper_build): COLOR01 takes
 * i x 0x111 at viewport row i for i below the ramp count, and again at row 196 - i going
 * the other way, so the text fades in at the top and out at the bottom.  Between the two
 * it keeps the brightest value; below the lower one it keeps black, which is why the text
 * is visible between display lines 6 and 200 only (re/notes/display.md). */
static uint16_t story_colour1(const wof_vport_t *v, uint16_t row)
{
    uint16_t n = v->ramp;

    if (row < n)
        return (uint16_t)(row * 0x111u);
    if (row > 196u)
        return 0;
    if (row + n > 196u)
        return (uint16_t)((196u - row) * 0x111u);
    return (uint16_t)((n - 1u) * 0x111u);
}

/* One viewport of the front view onto the output.  A run of rows that share a source row
 * and a set of colours is one band.  Two things break a run: the plane-pointer reload of
 * the story scroller, which sends the source back to row 0, and its ramps, which change
 * COLOR01 on every row. */
static void band_vport(const wof_vport_t *v)
{
    uint16_t rows = v->disp_rows;
    uint16_t done = 0;

    while (done < rows) {
        uint16_t run = (uint16_t)(rows - done);
        int32_t  src;

        if (v->ring_at != WOF_VP_RING_NONE && done >= v->ring_at) {
            src = (int32_t)(done - v->ring_at);
        } else {
            src = (int32_t)v->scroll + done;
            if (v->ring_at != WOF_VP_RING_NONE && run > v->ring_at - done)
                run = (uint16_t)(v->ring_at - done);
        }

        if (v->ramp) {
            uint16_t colours[WOF_PAL_COLOURS];
            uint16_t c1 = story_colour1(v, done);
            uint16_t k  = 1;

            while (k < run && story_colour1(v, (uint16_t)(done + k)) == c1)
                k++;
            run = k;
            for (uint32_t i = 0; i < WOF_PAL_COLOURS; i++)
                colours[i] = v->colours[i];
            colours[1] = c1;
            wof_screen_band(v, (uint16_t)(v->out_y + done), run, src, colours);
        } else {
            wof_screen_band(v, (uint16_t)(v->out_y + done), run, src, 0);
        }
        done = (uint16_t)(done + run);
    }
}

/* The front view's chain onto the output.  Rows no viewport covers stay black, which is
 * what the copper's BPLCON0 = 0x0200 gives above each lower viewport on the machine. */
void wof_screen_from_front_view(void)
{
    wof_screen_reset();
    for (uint8_t i = wof_f.view_first[wof_f.front_view]; i != WOF_VP_NONE; i = VP(i)->next)
        band_vport(VP(i));
    wof_screen_present();
}
