/* Test-only access to the core's internals.
 *
 * Compiled into tests/libwofcore.dylib and into nothing else: dist/core.wasm never sees
 * it.  The oracle tests of SPEC 7.4 need to reach the ported routines and the loaded
 * containers directly, and mirroring C structs in ctypes would tie the tests to a layout
 * that is free to change.  Every entry point here is a plain scalar interface instead.
 *
 * Nothing in src/ may call any of this. */
#include "wof.h"

enum {
    F_WBYTES, F_HEIGHT, F_HOT_X, F_HOT_Y, F_MARKER, F_SRC_Y, F_CLEAR, F_SET,
    F_PLANES, F_UNION, F_PLANE_BYTES, F_HAS_PIXELS,
};

static const wof_container_t *container(int slot)
{
    if (slot < 0 || slot >= WOF_C_COUNT)
        return 0;
    return &wof_assets.c[slot];
}

int wt_container_count(void)
{
    return WOF_C_COUNT;
}

int wt_container_shapes(int slot)
{
    const wof_container_t *c = container(slot);

    return c ? (int)c->count : -1;
}

const char *wt_container_file(int slot)
{
    const wof_container_t *c = container(slot);

    return c ? c->file : 0;
}

unsigned wt_container_name(int slot, int i)
{
    const wof_container_t *c = container(slot);

    if (!c || i < 0 || i >= (int)c->count)
        return 0;
    return c->names[i];
}

int wt_shape_field(int slot, int i, int field)
{
    const wof_container_t *c = container(slot);

    if (!c || i < 0 || i >= (int)c->count)
        return -1;

    const wof_shape_t *s = &c->shapes[i];

    switch (field) {
    case F_WBYTES:      return s->wbytes;
    case F_HEIGHT:      return s->height;
    case F_HOT_X:       return s->hot_x;
    case F_HOT_Y:       return s->hot_y;
    case F_MARKER:      return s->marker;
    case F_SRC_Y:       return s->src_y;
    case F_CLEAR:       return s->clear;
    case F_SET:         return s->set;
    case F_PLANES:      return s->planes;
    case F_UNION:       return s->union_mask;
    case F_PLANE_BYTES: return (int)s->plane_bytes;
    case F_HAS_PIXELS:  return s->pixels ? 1 : 0;
    default:            return -1;
    }
}

/* The converted pixels of one shape: 8 * wbytes columns by height rows. */
int wt_shape_pixels(int slot, int i, uint8_t *dst, int max)
{
    const wof_container_t *c = container(slot);

    if (!c || i < 0 || i >= (int)c->count)
        return -1;

    const wof_shape_t *s = &c->shapes[i];
    int n = (int)((uint32_t)s->wbytes * 8u * s->height);

    if (n > max)
        return -1;
    if (s->pixels)
        wof_mem_copy(dst, s->pixels, (uint32_t)n);
    else
        wof_mem_set(dst, 0, (uint32_t)n);
    return n;
}

int wt_shape_find(int slot, unsigned name)
{
    const wof_container_t *c = container(slot);

    return c ? wof_shape_find(c, name) : -2;
}

int wt_shape_by_index(int slot, int i)
{
    const wof_container_t *c = container(slot);

    return c ? wof_shape_by_index(c, (uint16_t)i) : -2;
}

/* The pointer table shapes_resolve built for this container, entry by entry. */
int wt_table_entry(int slot, int i)
{
    if (slot < 0 || slot >= WOF_C_COUNT || !wof_assets.table[slot])
        return -2;
    return wof_assets.table[slot][i];
}

void wt_shape_mirror(int slot, int i)
{
    const wof_container_t *c = container(slot);

    if (c && i >= 0 && i < (int)c->count)
        wof_shape_mirror_x(&c->shapes[i]);
}

void wt_shape_set_facing(int slot, int i, int facing)
{
    const wof_container_t *c = container(slot);

    if (c && i >= 0 && i < (int)c->count)
        wof_shape_set_facing(&c->shapes[i], (int16_t)facing);
}

/* One file through the ported loader, unpacked. */
int wt_load_file(const char *name, uint8_t *dst, int max)
{
    uint32_t mark = wof_arena_mark();
    uint32_t len  = 0;
    uint8_t *raw  = wof_load_file(name, &len);
    int      n    = -1;

    if (raw && (int)len <= max) {
        wof_mem_copy(dst, raw, len);
        n = (int)len;
    }
    wof_arena_release(mark);
    return n;
}

/* One picture through the ported ILBM reader, into a viewport of the given shape. */
int wt_iff_decode(const char *file, int width, int height, int depth,
                  uint8_t *pixels, uint16_t *colours)
{
    uint32_t mark = wof_arena_mark();
    uint32_t len  = 0;
    uint8_t *raw  = wof_load_file(file, &len);
    wof_vport_t *v = wof_vport_make((uint16_t)width, (uint16_t)height, (uint8_t)depth, 0);
    int ok = 0;

    if (raw && v) {
        ok = wof_iff_to_vport(raw, len, v);
        if (ok) {
            wof_mem_copy(pixels, v->pixels, (uint32_t)v->bytes_per_row * 8u * v->rows);
            wof_mem_copy(colours, v->colours, sizeof v->colours);
        }
    }
    wof_arena_release(mark);
    return ok;
}

int wt_cmap_file(const char *name, uint16_t *out)
{
    uint32_t mark = wof_arena_mark();
    uint32_t len  = 0;
    uint8_t *raw  = wof_load_file(name, &len);

    if (raw)
        wof_cmap_file_to_table(raw, len, out);
    wof_arena_release(mark);
    return raw ? 1 : 0;
}

int wt_text_width(const char *s, int len)
{
    return wof_text_width(s, (uint16_t)len);
}

int wt_text_render(const char *s, int len, uint8_t *buffer, int x, int row, int justify,
                   int buf_w, int buf_h)
{
    return wof_text_render(s, (uint16_t)len, buffer, (int16_t)x, (int16_t)row,
                           (int16_t)justify, (int16_t)buf_w, (int16_t)buf_h);
}

int wt_font_height(void)
{
    return wof_font_height();
}

/* One blit onto a target of the given shape, over the given background.  This is the
 * comparison the blitter model in tests/blitter.py is run against. */
int wt_blit(int slot, int i, int bytes_per_row, int rows, int depth,
            int top, int bottom, int left, int right, int x, int y,
            const uint8_t *background, uint8_t *out)
{
    const wof_container_t *c = container(slot);
    wof_vport_t v;
    uint32_t    n = (uint32_t)bytes_per_row * 8u * rows;

    if (!c || i < 0 || i >= (int)c->count)
        return -1;

    v.width         = (uint16_t)(bytes_per_row * 8);
    v.height        = (uint16_t)rows;
    v.bytes_per_row = (uint16_t)bytes_per_row;
    v.rows          = (uint16_t)rows;
    v.depth         = (uint8_t)depth;
    v.hires         = 1;
    v.pixels        = out;
    wof_mem_set(v.colours, 0, sizeof v.colours);

    wof_mem_copy(out, background, n);
    wof_draw_set_target(&v);
    wof_clip_set((int16_t)top, (int16_t)bottom, (int16_t)left, (int16_t)right);
    wof_shape_draw(&c->shapes[i], (int16_t)x, (int16_t)y);
    return (int)n;
}
