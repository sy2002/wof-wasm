/* PPkc shape containers: parsing, conversion to indexed pixels, name resolution and the
 * in-place mirror.  Everything here follows re/notes/shapes.md.
 *
 * The original keeps the unpacked file in chip memory and works on it: a shape is a
 * pointer into that image.  The port converts each record once, at load, into indexed
 * pixels plus the header fields the blit still needs (SPEC 6.4), and then throws the file
 * image away.  A pointer table becomes an array of shape indices with WOF_NO_SHAPE where
 * the original stores a null pointer, which is the normal case: 84 of the 184 world names
 * are absent from 8thscale.shp. */
#include "wof.h"

static uint16_t be16(const uint8_t *p)
{
    return (uint16_t)(((uint16_t)p[0] << 8) | p[1]);
}

static uint32_t be32(const uint8_t *p)
{
    return ((uint32_t)p[0] << 24) | ((uint32_t)p[1] << 16) | ((uint32_t)p[2] << 8) | p[3];
}

uint16_t wof_namelist_count(const uint32_t *list)
{
    uint16_t n = 0;

    if (list)
        while (list[n])
            n++;
    return n;
}

/* orig 0x020560 - A0 = container, D0 = the name as a big-endian long.  A linear scan that
 * stops at the first stored name greater than or equal to the wanted one, so it needs the
 * ascending order that all thirteen containers on the disk have.  The port keeps the early
 * exit: the result is the same as an exact-match lookup, and the oracle test compares it
 * against the original for every name of every list. */
int16_t wof_shape_find(const wof_container_t *c, uint32_t name)
{
    if (!c || (int16_t)c->count <= 0)
        return WOF_NO_SHAPE;

    for (uint16_t i = 0; i < c->count; i++) {
        if (c->names[i] >= name)
            return c->names[i] == name ? (int16_t)i : WOF_NO_SHAPE;
    }
    /* Ran past the end: the original then re-tests the last entry, which cannot match. */
    return WOF_NO_SHAPE;
}

/* orig 0x02050E - (container, index).  Its range check is compiled without effect on the
 * machine, so an index outside the container reads garbage there; here it is refused. */
int16_t wof_shape_by_index(const wof_container_t *c, uint16_t i)
{
    if (!c || i >= c->count)
        return WOF_NO_SHAPE;
    return (int16_t)i;
}

/* orig 0x015C5C - the zero-terminated name list becomes an array of shape indices in the
 * same order.  Game code then uses fixed numeric slots into that array. */
int16_t *wof_shapes_resolve(const wof_container_t *c, const uint32_t *list, uint16_t count)
{
    int16_t *table = (int16_t *)wof_alloc((uint32_t)count * sizeof(int16_t));

    if (!table)
        return 0;
    for (uint16_t i = 0; i < count; i++)
        table[i] = wof_shape_find(c, list[i]);
    return table;
}

/* One record of the file image into a wof_shape_t plus its indexed pixels.
 *
 * The pixel value is what the blit's plane loop leaves behind: for each stored plane in
 * order, the destination bits named by that plane's mask become the plane's bit.  No
 * container on the disk has overlapping masks, so this equals the OR that tools/ppkc.py
 * draws, but the loop is what shape_blit does and is what the port follows.
 *
 * The blit's transparency mask is the OR of the raw plane bits, which with disjoint masks
 * is exactly "the pixel is not 0"; the mask therefore needs no storage of its own. */
static int convert_record(wof_shape_t *s, const uint8_t *rec, uint32_t avail)
{
    if (avail < 20)
        return 0;

    s->wbytes = be16(rec + 0);
    s->height = be16(rec + 2);
    s->hot_x  = (int16_t)be16(rec + 4);
    s->hot_y  = (int16_t)be16(rec + 6);
    s->marker = be16(rec + 8);
    s->src_y  = be16(rec + 10);
    s->clear  = rec[12];
    s->set    = rec[13];

    uint8_t masks[6];
    uint8_t n = 0;

    while (n < 6 && rec[14 + n]) {
        masks[n] = rec[14 + n];
        n++;
    }
    s->planes     = n;
    s->union_mask = 0;
    for (uint8_t i = 0; i < n; i++)
        s->union_mask = (uint8_t)(s->union_mask | masks[i]);

    s->plane_bytes = (uint32_t)s->wbytes * s->height;
    s->pixels      = 0;

    if (n == 0 || s->plane_bytes == 0)
        return 1;
    if (avail < 20u + (uint32_t)n * s->plane_bytes)
        return 0;

    uint32_t w = (uint32_t)s->wbytes * 8u;
    uint8_t *px = (uint8_t *)wof_alloc(w * s->height);

    if (!px)
        return 0;
    s->pixels = px;

    for (uint8_t p = 0; p < n; p++) {
        const uint8_t *plane = rec + 20 + (uint32_t)p * s->plane_bytes;
        uint8_t        m     = masks[p];

        for (uint32_t y = 0; y < s->height; y++) {
            const uint8_t *row = plane + y * s->wbytes;
            uint8_t       *out = px + y * w;

            for (uint32_t x = 0; x < w; x++) {
                uint8_t bit = (uint8_t)((row[x >> 3] >> (7 - (x & 7))) & 1);
                out[x] = (uint8_t)((out[x] & ~m) | (bit ? m : 0));
            }
        }
    }
    return 1;
}

static int parse_container(wof_container_t *c, const uint8_t *img, uint32_t len)
{
    if (len < 6 || be32(img) != 0x50506B63uL)   /* 'PPkc' */
        return 0;

    uint16_t n = be16(img + 4);

    if (len < 6u + 8u * (uint32_t)n)
        return 0;

    uint32_t *names  = (uint32_t *)wof_alloc((uint32_t)n * sizeof(uint32_t));
    wof_shape_t *sh  = (wof_shape_t *)wof_alloc((uint32_t)n * sizeof(wof_shape_t));

    if (!names || !sh)
        return 0;

    const uint8_t *offsets = img + 6 + 4u * n;
    const uint8_t *base    = img + 6 + 8u * n;   /* the offsets are relative to here */

    for (uint16_t i = 0; i < n; i++) {
        names[i] = be32(img + 6 + 4u * i);

        uint32_t off = be32(offsets + 4u * i);
        if ((uint32_t)(base - img) + off > len)
            return 0;
        if (!convert_record(&sh[i], base + off, len - (uint32_t)(base - img) - off))
            return 0;
    }

    c->count  = n;
    c->names  = names;
    c->shapes = sh;
    return 1;
}

/* orig 0x015BC6 - A0 = file name, A1 = name list.  Counts the names, loads the file and
 * falls into shapes_resolve.  A missing file is fatal in the original (through fatal_exit,
 * except for battleship.shp); here it returns 0 and wof_assets_init reports it. */
int wof_shapes_load(wof_container_t *c, const char *file, const uint32_t *list)
{
    uint32_t mark = wof_arena_mark();
    uint32_t len  = 0;
    uint8_t *img;
    int      ok;

    c->file   = file;
    c->count  = 0;
    c->names  = 0;
    c->shapes = 0;
    (void)list;                     /* resolved by the caller, as shapes_resolve is */

    img = wof_load_file(file, &len);
    if (!img) {
        wof_arena_release(mark);
        return 0;
    }
    ok = parse_container(c, img, len);
    wof_arena_release(mark);        /* the file image goes; the conversion stays */
    if (!ok)
        c->count = 0;
    return ok;
}

/* orig 0x015B58 - mirrors a shape in place and turns its hotspot round.
 *
 * The original reverses the bytes of every stored plane row and the bits inside each byte
 * through bit_reverse_table; on indexed pixels that is one row reversal, because a pixel
 * carries the bits of all planes at once.  It swaps byte pairs from both ends, so the
 * middle byte of an odd byte width would stay unreversed - every width in the files is
 * even, which the oracle test relies on as much as the original does.  A null record
 * returns at once. */
void wof_shape_mirror_x(wof_shape_t *s)
{
    if (!s)
        return;

    s->hot_x = (int16_t)(s->wbytes * 8 - 1 - s->hot_x);

    if (!s->pixels)
        return;

    uint32_t w = (uint32_t)s->wbytes * 8u;

    for (uint32_t y = 0; y < s->height; y++) {
        uint8_t *row = s->pixels + y * w;
        for (uint32_t i = 0, j = w - 1; i < j; i++, j--) {
            uint8_t t = row[i];
            row[i] = row[j];
            row[j] = t;
        }
    }
}

/* The +8 marker rule of re/notes/shapes.md, as the caller at 0x01ABDE applies it: the
 * pixels of a hellcat or Torpedo record face the way the marker says, and a change of
 * facing mirrors them in place.  2 is the orientation stored in the file, which
 * load_permanent_shapes writes into every record of those two containers. */
void wof_shape_set_facing(wof_shape_t *s, int16_t facing)
{
    uint16_t want = (uint16_t)(facing + 1);

    if (!s || s->marker == want)
        return;
    s->marker = want;
    wof_shape_mirror_x(s);
}
