/* Pictures and palettes: the ILBM reader the game actually uses, the bare-CMAP palette
 * files, and the fade arithmetic.
 *
 * The original has two IFF readers.  The one that reports errors under the name ReadIFF is
 * dead code; the live one is iff_to_vport (0x01A548), which knows BMHD, CMAP, a private
 * CMP2 and BODY, assumes ByteRun1 without looking, clears the target's planes and decodes
 * min(picture rows, viewport rows) rows of min(picture planes, viewport depth) planes.
 * That reader is ported, not replaced (SPEC 3.5), because its cropping is what puts the
 * first 200 rows of a 256-row picture on the screen and nothing else.
 *
 * Rows are decoded at the picture's own stride and written back to back into the target's
 * plane memory, so a picture whose width differs from the viewport's shears rather than
 * being clipped.  The port reproduces that by decoding into planes of the viewport's size
 * and composing to indexed pixels afterwards, which keeps the shear.
 *
 * No code in the game reads a CRNG chunk: there is no colour cycling (re/notes/display.md). */
#include "wof.h"

#define ID_FORM 0x464F524DuL
#define ID_ILBM 0x494C424DuL
#define ID_BMHD 0x424D4844uL
#define ID_BODY 0x424F4459uL
#define ID_CMAP 0x434D4150uL
#define ID_CMP2 0x434D5032uL

/* iff_parse_ilbm stops when the chunk walk passes this; the original's own guard. */
#define IFF_LIMIT 40000u

static uint16_t be16(const uint8_t *p)
{
    return (uint16_t)(((uint16_t)p[0] << 8) | p[1]);
}

static uint32_t be32(const uint8_t *p)
{
    return ((uint32_t)p[0] << 24) | ((uint32_t)p[1] << 16) | ((uint32_t)p[2] << 8) | p[3];
}

/* orig 0x0203E8 - one ByteRun1 row of n bytes.  A control byte of 0x80 is a no-op, one
 * above it repeats the next byte 257 - c times, one below copies c + 1 literals.  The
 * loop ends when n bytes have been produced, not when the run ends, exactly as the
 * original's `sub.w d1,d0 / subq #1,d0 / tst.w d0 / bgt` does. */
static void byterun1_row(const uint8_t *src, uint32_t src_len, uint32_t *src_pos,
                         uint8_t *dst, uint32_t dst_len, uint32_t *dst_pos, int32_t n)
{
    uint32_t s = *src_pos;
    uint32_t d = *dst_pos;

    while (n > 0 && s < src_len) {
        uint8_t c = src[s++];

        if (c < 0x80) {
            int32_t k = (int32_t)c + 1;
            n -= k;
            while (k--) {
                uint8_t v = s < src_len ? src[s++] : 0;
                if (d < dst_len)
                    dst[d] = v;
                d++;
            }
        } else if (c == 0x80) {
            continue;                        /* the original skips it and tests n again */
        } else {
            int32_t k = 257 - (int32_t)c;
            uint8_t v = s < src_len ? src[s++] : 0;
            n -= k;
            while (k--) {
                if (d < dst_len)
                    dst[d] = v;
                d++;
            }
        }
    }
    *src_pos = s;
    *dst_pos = d;
}

/* orig 0x01A1F6 - a CMAP chunk into colour table 1: at most 32 entries, each component
 * masked to its high nibble.  Entries the chunk does not reach keep what they had. */
static void cmap_to_table(const uint8_t *chunk, uint32_t avail, uint16_t *table)
{
    uint32_t n = be32(chunk + 4) / 3u;
    const uint8_t *p = chunk + 8;

    if (n > WOF_PAL_COLOURS)
        n = WOF_PAL_COLOURS;
    if (avail < 8 || n > (avail - 8) / 3u)
        n = avail < 8 ? 0 : (avail - 8) / 3u;
    for (uint32_t i = 0; i < n; i++) {
        uint16_t r = p[i * 3 + 0];
        uint16_t g = p[i * 3 + 1];
        uint16_t b = p[i * 3 + 2];

        table[i] = (uint16_t)((((r << 4) & 0x0F00) | (g & 0x00F0)) | ((b >> 4) & 0x000F));
    }
}

/* orig 0x01A362 - the BODY into the viewport's planes. */
static void body_to_vport(const uint8_t *bmhd, const uint8_t *body, const uint8_t *end,
                          wof_vport_t *v)
{
    int32_t  src_bpr  = ((int32_t)be16(bmhd) + 7) / 8;
    uint16_t pic_rows = be16(bmhd + 2);
    uint8_t  pic_deep = bmhd[8];

    uint16_t rows   = pic_rows < v->rows ? pic_rows : v->rows;
    uint8_t  planes = pic_deep < v->depth ? pic_deep : v->depth;

    uint32_t plane_bytes = (uint32_t)v->bytes_per_row * v->rows;
    uint32_t mark        = wof_arena_mark();
    uint8_t *store       = (uint8_t *)wof_scratch_alloc(plane_bytes * (planes ? planes : 1));
    uint32_t cursor[8]   = {0};
    uint32_t body_len    = (uint32_t)(end - body);
    uint32_t body_pos    = 0;

    if (!store)
        return;

    wof_vport_clear_planes(v);

    /* The destination positions advance by the picture's bytes per row, not the
     * viewport's; that is the original's "written back to back". */
    for (uint16_t y = 0; y < rows; y++)
        for (uint8_t p = 0; p < planes; p++)
            byterun1_row(body, body_len, &body_pos,
                         store + (uint32_t)p * plane_bytes, plane_bytes, &cursor[p],
                         src_bpr);

    for (uint16_t y = 0; y < v->rows; y++) {
        uint8_t *out = v->pixels + (uint32_t)y * v->bytes_per_row * 8u;

        for (uint8_t p = 0; p < planes; p++) {
            const uint8_t *row = store + (uint32_t)p * plane_bytes
                               + (uint32_t)y * v->bytes_per_row;
            uint8_t bit = (uint8_t)(1u << p);

            for (uint32_t b = 0; b < v->bytes_per_row; b++) {
                uint8_t byte = row[b];
                if (!byte)
                    continue;
                for (uint32_t k = 0; k < 8; k++)
                    if (byte & (0x80u >> k))
                        out[b * 8 + k] |= bit;
            }
        }
    }
    wof_arena_release(mark);
}

/* orig 0x01A452 - the chunk walk, and 0x01A548 - the FORM/ILBM test around it. */
int wof_iff_to_vport(const uint8_t *file, uint32_t len, wof_vport_t *v)
{
    if (!file || !v || len < 20)
        return 0;
    if (be32(file) != ID_FORM || be32(file + 8) != ID_ILBM)
        return 0;

    const uint8_t *bmhd = 0, *body = 0;
    uint32_t off = 12;
    uint32_t end = be32(file + 4) + 8;

    if (end > len)
        end = len;

    while (off + 8 <= end) {
        uint32_t id  = be32(file + off);
        uint32_t clen = be32(file + off + 4);

        if (id == ID_BMHD)
            bmhd = file + off + 8;
        else if (id == ID_BODY)
            body = file + off + 8;
        else if (id == ID_CMAP)
            cmap_to_table(file + off, len - off, v->colours);
        else if (id == ID_CMP2)
            ;   /* the private split-palette chunk; no file on the disk carries one */

        off = (off + clen + 9) & ~1u;
        if (off >= IFF_LIMIT)
            break;
    }

    if (!bmhd || !body)
        return 0;
    if ((uint32_t)(bmhd - file) + 9 > len)
        return 0;

    body_to_vport(bmhd, body, file + len, v);
    return 1;
}

/* orig 0x016DD6 - the bare-CMAP palette files.  It searches the first 4000 bytes in steps
 * of four for 'CMAP', skips the length and converts 32 triplets as (r << 4) | g | (b >> 4)
 * without masking.  All four files in use have zero low nibbles, so the result equals the
 * masked conversion; the port keeps the arithmetic anyway. */
void wof_cmap_file_to_table(const uint8_t *file, uint32_t len, uint16_t *table)
{
    uint32_t off = 0;

    if (!file || !table)
        return;
    while (off + 4 <= len && off < 4000u && be32(file + off) != ID_CMAP)
        off += 4;
    if (off + 4 > len || be32(file + off) != ID_CMAP)
        return;

    off += 8;                                   /* past 'CMAP' and its length */
    for (uint32_t i = 0; i < WOF_PAL_COLOURS; i++) {
        if (off + 3 > len)
            return;
        uint16_t r = file[off + 0];
        uint16_t g = file[off + 1];
        uint16_t b = file[off + 2];

        table[i] = (uint16_t)(((uint16_t)(r << 4)) | g | (uint16_t)(b >> 4));
        off += 3;
    }
}

/* orig 0x016FF6 - one step of a 16-step fade.
 *
 * Step 15 returns the target.  Otherwise the whole start word is taken and the masked
 * quotient of each component's difference is added into it, blue first, then green, then
 * red.  A falling component adds its negative quotient as a masked two's complement value
 * and therefore carries into the next higher component: 0x005 towards 0 at step 8 gives
 * 0x013.  The hardware ignores bits 12 to 15.  The intermediate colours of every fade-out
 * depend on this, so the arithmetic is kept exactly, including the widths: blue and green
 * divide a 16-bit product with divs.w, red divides the full 32-bit product. */
uint16_t wof_colour_lerp(int16_t step, uint16_t from, uint16_t to)
{
    if (step == 15)
        return to;

    uint16_t r = from;
    int16_t  d;
    int32_t  q;

    d = (int16_t)((int16_t)(to & 0x000F) - (int16_t)(from & 0x000F));
    q = (int32_t)(int16_t)((uint16_t)((int32_t)d * step)) / 15;
    r = (uint16_t)(r + (((uint16_t)q) & 0x000F));

    d = (int16_t)((int16_t)(to & 0x00F0) - (int16_t)(from & 0x00F0));
    q = (int32_t)(int16_t)((uint16_t)((int32_t)d * step)) / 15;
    r = (uint16_t)(r + (((uint16_t)q) & 0x00F0));

    d = (int16_t)((int16_t)(to & 0x0F00) - (int16_t)(from & 0x0F00));
    q = ((int32_t)d * step) / 15;
    r = (uint16_t)(r + (uint16_t)(((uint32_t)q) & 0x0F00));

    return r;
}
