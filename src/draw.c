/* Shape drawing: the port of the original's blitter library onto indexed pixels.
 *
 * On the machine every draw is a blitter programme (re/notes/drawing.md).  The port has to
 * produce the same pixels, not the same register writes, so what matters is the effective
 * rule, which the tests establish by running the original under the oracle, capturing the
 * blits at BLTSIZE and replaying them through a model of the blitter's area mode.
 *
 * The rule, read off blit_clip_setup (0x0209BC), shape_blit (0x020B0C) and shape_draw
 * (0x020CE2):
 *
 *   The destination span of a blit is word-aligned and up to one word wider than the
 *   shape, but the first and last word masks - left_mask_table[(clip_left - x) & 15] and
 *   0xFFFF << (x & 15) - blank the A channel exactly outside the shape's own box and
 *   outside the clip rectangle, and with minterm 0xCA a zero in A leaves the destination
 *   alone.  The visible effect is therefore per-pixel: every pixel of the shape's box that
 *   lies inside [clip_left, clip_right) x [clip_top, clip_bottom) is written, and nothing
 *   else is, whether the blit is shifted or not.  That is what this file does.
 *
 *   Per written pixel, with M the target's depth mask, `clear` and `set` the bytes at +12
 *   and +13 of the record, U the union of the stored planes' destination masks and p the
 *   shape's converted pixel:
 *
 *       v = (((v & ~(clear & M)) | (set & M)) & ~(U & M)) | (p & M)
 *
 *   which is the three blitter phases in order: clear planes, set planes, then one blit
 *   per stored plane.  Planes named by none of clear, set and U keep the background's bits.
 *
 *   Whether a pixel is written at all is the mask: a shape gets one when its plane is at
 *   most MaskBuffer_size (1040) bytes and it stores at least one plane, and then the mask
 *   is the OR of its stored planes, which on converted pixels is p != 0.  Without a mask
 *   the whole box is written and the shape is opaque - eleven shapes on the disk are.
 *
 * The rectangle fill is M4's; the line mode is not ported, because none of the five mission
 * scripts of M4 draws a line (re/notes/porting-m4.md).
 *
 * The clip rectangle is the original's own six words (clip_top .. clip_right_incl) and
 * lives in the registered globals, because the tick reads and writes it as well as the pass
 * (re/notes/passes.md).  The draw target is kept as the index of its viewport in the state,
 * and the pointers below are derived from it. */
#include "wof.h"

#define MASKBUFFER_SIZE 1040u    /* orig: alloc_pools stores 0x410 in MaskBuffer_size */

#define clip_top    (wof_g.clip_top)
#define clip_bottom (wof_g.clip_bottom)
#define clip_left   (wof_g.clip_left)
#define clip_right  (wof_g.clip_right)

static wof_target_t target;
static uint16_t draw_layer, draw_owner;

static wof_draw_t draw_list[WOF_DRAW_MAX];
static uint32_t   draw_count;

const wof_target_t *wof_draw_target(void)
{
    return &target;
}

void wof_draw_context(uint16_t layer, uint16_t owner)
{
    draw_layer = layer;
    draw_owner = owner;
}

void wof_draw_list_reset(void)
{
    draw_count = 0;
}

void wof_draw_list_add(uint32_t name, int16_t x, int16_t y, uint16_t layer,
                       uint16_t flags, uint16_t owner)
{
    if (draw_count >= WOF_DRAW_MAX)
        return;

    wof_draw_t *d = &draw_list[draw_count++];

    d->name[0] = (char)(name >> 24);
    d->name[1] = (char)(name >> 16);
    d->name[2] = (char)(name >> 8);
    d->name[3] = (char)name;
    d->x       = x;
    d->y       = y;
    d->layer   = layer;
    d->flags   = flags;
    d->owner   = owner;
}

const void *wof_display_list(uint32_t *count)
{
    if (count)
        *count = draw_count;
    return draw_list;
}

/* orig 0x02124A - remembers the RastPort and its BitMap and sets the RastPort's Mask byte
 * to the depth mask, which is what every draw ANDs its plane bytes with. */
static wof_vport_t *target_vport;

/* The viewport draw_set_target was last given, which is what the original calls
 * draw_rastport: the line editor draws on it without being told which it is. */
wof_vport_t *wof_draw_target_vport(void)
{
    return target_vport;
}

void wof_draw_set_target(wof_vport_t *v)
{
    target_vport = v;
    wof_f.draw_vport = (uint8_t)(v && v >= wof_f.vport && v < wof_f.vport + WOF_VP_MAX
                                 ? v - wof_f.vport : WOF_VP_NONE);
    wof_trace_add("draw_set_target", wof_f.draw_vport, 0, 0, 0, 0, 0);
    if (!v) {
        target.pixels = 0;
        target.stride = target.width = target.height = 0;
        target.mask   = 0;
        return;
    }
    target.pixels = wof_vport_pixels(v);
    target.width  = (int32_t)v->bytes_per_row * 8;
    target.stride = target.width;
    target.height = v->rows;
    target.mask   = (uint8_t)(0xFFu >> (8 - v->depth));
}

/* The target after a state was loaded: the viewport's index is state, the pointers are
 * not (SPEC 7.2). */
void wof_draw_restore(void)
{
    uint8_t i = wof_f.draw_vport;

    wof_draw_set_target(i < WOF_VP_MAX ? &wof_f.vport[i] : 0);
}

/* orig 0x02129C - bottom and right are exclusive, and left and right are rounded down to
 * a multiple of 16 because the blitter works in words.  The rounding is behaviour: a clip
 * asked for at column 100 really clips at 96.  The two inclusive words beside them are the
 * original's too; rect_fill and line_draw read those. */
void wof_clip_set(int16_t top, int16_t bottom, int16_t left, int16_t right)
{
    clip_top    = top;
    clip_bottom = bottom;
    clip_left   = (int16_t)(left & (int16_t)0xFFF0);
    clip_right  = (int16_t)(right & (int16_t)0xFFF0);
    wof_g.clip_right_incl  = (int16_t)(clip_right - 1);
    wof_g.clip_bottom_incl = (int16_t)(clip_bottom - 1);
    wof_trace_add("clip_set", top, bottom, left, right, 0, 0);
}

/* orig 0x021280 - the whole current BitMap. */
void wof_clip_set_full(void)
{
    wof_clip_set(0, (int16_t)target.height, 0, (int16_t)target.width);
}

/* orig 0x020B0C together with 0x0209BC.  `useMask` is the original's A1: non-zero means
 * the cookie-cut mask that shape_draw chose, zero means an opaque blit. */
static void shape_blit(const wof_shape_t *s, int useMask, int16_t x, int16_t y)
{
    if (!s || !target.pixels)
        return;

    int32_t w = (int32_t)s->wbytes * 8;
    int32_t h = (int32_t)s->height;
    int32_t x0 = x, y0 = y;

    /* Clip the box, exactly as the three-sided arithmetic of blit_clip_setup does. */
    int32_t sx0 = 0, sy0 = 0, sx1 = w, sy1 = h;

    if (x0 + sx0 < clip_left)   sx0 = clip_left - x0;
    if (x0 + sx1 > clip_right)  sx1 = clip_right - x0;
    if (y0 + sy0 < clip_top)    sy0 = clip_top - y0;
    if (y0 + sy1 > clip_bottom) sy1 = clip_bottom - y0;
    if (sx0 < 0) sx0 = 0;
    if (sy0 < 0) sy0 = 0;
    if (sx1 > w) sx1 = w;
    if (sy1 > h) sy1 = h;
    if (sx0 >= sx1 || sy0 >= sy1)
        return;

    /* The target's own edges.  On the machine a blit outside the BitMap would write into
     * whatever follows it; the clip rectangle is always inside, so this only guards the
     * port against a caller that sets a wider one. */
    if (x0 + sx1 > target.width)  sx1 = target.width - x0;
    if (y0 + sy1 > target.height) sy1 = target.height - y0;
    if (x0 + sx0 < 0) sx0 = -x0;
    if (y0 + sy0 < 0) sy0 = -y0;
    if (sx0 >= sx1 || sy0 >= sy1)
        return;

    uint8_t M     = target.mask;
    uint8_t clr   = (uint8_t)(s->clear & M);
    uint8_t st    = (uint8_t)(s->set & M);
    uint8_t un    = (uint8_t)(s->union_mask & M);
    uint8_t keep  = (uint8_t)~(clr | st | un);
    uint8_t force = (uint8_t)(st & ~un);

    /* A shape that stores no plane has no pixels at all (8thscale's `bchm` is the one on
     * the disk).  It still paints its clear and set bytes over its box, opaquely. */
    for (int32_t r = sy0; r < sy1; r++) {
        const uint8_t *src = s->pixels ? s->pixels + (uint32_t)r * w : 0;
        uint8_t       *dst = target.pixels + (int32_t)(y0 + r) * target.stride + x0;

        for (int32_t c = sx0; c < sx1; c++) {
            uint8_t p = src ? src[c] : 0;

            if (useMask && !p)
                continue;
            dst[c] = (uint8_t)((dst[c] & keep) | force | (p & un));
        }
    }
}

/* orig 0x020B0C called directly, which the dashboard's digits and 0x010344 do: no mask,
 * the whole box is written. */
void wof_shape_blit(const wof_shape_t *s, int useMask, int16_t x, int16_t y)
{
    if (!s)
        return;
    wof_trace_add("shape_blit", x, y, wof_shape_handle_of(s), useMask, 0, 0);
    shape_blit(s, useMask, x, y);
    wof_draw_list_add(s->name, x, y, draw_layer, 1, draw_owner);
}

/* orig 0x021010 rect_fill, with rect_fill_aligned (0x02113E) that it jumps into when both
 * edges fall on a word.  The corners are inclusive and are clamped to the clip rectangle
 * first; what is left is filled with the colour in every plane of the target's mask, exact
 * to the pixel on all four sides, because the first and last word masks of the blit are
 * left_mask_table[x0 & 15] and right_mask_table[(x1 & 15) + 1] (re/notes/drawing.md).  A
 * rectangle that is empty after the clamp draws nothing. */
void wof_rect_fill(int16_t x0, int16_t y0, int16_t x1, int16_t y1, uint8_t colour)
{
    wof_trace_add("rect_fill", x0, y0, (int32_t)(((uint32_t)colour << 16) | (uint16_t)x1), y1, 0, 0);
    if (x0 < clip_left)
        x0 = clip_left;
    if (x1 >= clip_right)
        x1 = (int16_t)(clip_right - 1);
    if (y0 < clip_top)
        y0 = clip_top;
    if (y1 >= clip_bottom)
        y1 = (int16_t)(clip_bottom - 1);
    if (!target.pixels || y1 < y0 || x1 < x0)
        return;
    if (x0 < 0 || y0 < 0 || x1 >= target.width || y1 >= target.height)
        return;                             /* the clip rectangle is always inside the target */

    uint8_t M = target.mask;
    uint8_t c = (uint8_t)(colour & M);

    for (int32_t r = y0; r <= y1; r++) {
        uint8_t *row = target.pixels + r * target.stride;

        for (int32_t x = x0; x <= x1; x++)
            row[x] = (uint8_t)((row[x] & ~M) | c);
    }
}

/* orig 0x020CE2 - chooses the mask, then blits.  A plane larger than MaskBuffer_size does
 * not get one, whatever it stores; neither does a shape that stores no plane at all.  With
 * one stored plane the plane itself is the mask, with two or more the CPU ORs them into
 * MaskBuffer first; on converted pixels both are "the pixel is not 0". */
void wof_shape_draw(const wof_shape_t *s, int16_t x, int16_t y)
{
    int useMask;

    if (!s)
        return;                           /* blit_clip_setup rejects a null record */

    useMask = s->plane_bytes <= MASKBUFFER_SIZE && s->planes > 0;
    {
        char name[5];                     /* the 4-character name, in the order it is read */

        name[0] = (char)(s->name >> 24); name[1] = (char)(s->name >> 16);
        name[2] = (char)(s->name >> 8);  name[3] = (char)s->name; name[4] = 0;
        wof_trace_add("shape_draw_c", x, y, s->wbytes, s->height, name, 4);
        wof_trace_add("shape_draw", x, y, wof_shape_handle_of(s), 0, name, 4);
    }
    shape_blit(s, useMask, x, y);

    /* SPEC 6.4: every shape draw also appends a display-list record.  The classic
     * renderer ignores it; it is here so that an enhanced one can be added later. */
    wof_draw_list_add(s->name, x, y, draw_layer, (uint16_t)(useMask ? 0 : 1), draw_owner);
}

/* orig 0x020E24 shape_draw_xor - the exclusive-or blit.  It uses no mask, so the whole
 * clipped box is written, and it ignores the clear byte at +12: inside the box it inverts
 * the planes of `set & M` and exclusive-ors each stored plane into the planes of its own
 * destination mask (minterm 0x6A, re/notes/drawing.md).  Because no container on the disk
 * has overlapping plane masks, the exclusive-or of the stored planes is the converted
 * pixel, so one exclusive-or of `(set ^ p) & M` is the whole operation.  Drawing twice
 * restores the background, which is what the rank selection's highlight relies on. */
void wof_shape_draw_xor(const wof_shape_t *s, int16_t x, int16_t y)
{
    if (!s || !target.pixels)
        return;

    int32_t w = (int32_t)s->wbytes * 8;
    int32_t h = (int32_t)s->height;
    int32_t x0 = x, y0 = y;
    int32_t sx0 = 0, sy0 = 0, sx1 = w, sy1 = h;

    if (x0 + sx0 < clip_left)   sx0 = clip_left - x0;
    if (x0 + sx1 > clip_right)  sx1 = clip_right - x0;
    if (y0 + sy0 < clip_top)    sy0 = clip_top - y0;
    if (y0 + sy1 > clip_bottom) sy1 = clip_bottom - y0;
    if (sx0 < 0) sx0 = 0;
    if (sy0 < 0) sy0 = 0;
    if (sx1 > w) sx1 = w;
    if (sy1 > h) sy1 = h;
    if (x0 + sx1 > target.width)  sx1 = target.width - x0;
    if (y0 + sy1 > target.height) sy1 = target.height - y0;
    if (x0 + sx0 < 0) sx0 = -x0;
    if (y0 + sy0 < 0) sy0 = -y0;
    if (sx0 >= sx1 || sy0 >= sy1)
        return;

    uint8_t M  = target.mask;
    uint8_t st = (uint8_t)(s->set & M);

    {
        char name[5];

        name[0] = (char)(s->name >> 24); name[1] = (char)(s->name >> 16);
        name[2] = (char)(s->name >> 8);  name[3] = (char)s->name; name[4] = 0;
        wof_trace_add("shape_xor_c", x, y, s->wbytes, s->height, name, 4);
    }

    for (int32_t r = sy0; r < sy1; r++) {
        const uint8_t *src = s->pixels ? s->pixels + (uint32_t)r * w : 0;
        uint8_t       *dst = target.pixels + (int32_t)(y0 + r) * target.stride + x0;

        for (int32_t c = sx0; c < sx1; c++) {
            uint8_t p = src ? src[c] : 0;

            dst[c] ^= (uint8_t)((st ^ p) & M);
        }
    }
    wof_draw_list_add(s->name, x, y, draw_layer, 2, draw_owner);
}
