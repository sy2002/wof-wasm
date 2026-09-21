/* Text: the game's own font and the system font.
 *
 * newarmyfont is loaded from the disk and rendered by the CPU into a 1-bit template,
 * which the original then puts on screen with BltTemplate (re/notes/drawing.md).  The
 * template is plain memory, so text_render is a pure routine and the oracle compares it
 * byte for byte.
 *
 * topaz 8 is not on the game disk.  The load and save dialog, the name entry and the file
 * list draw with graphics.Text and never set a font, so the original shows the system
 * default; the port takes it from the owner's Kickstart ROM at build time
 * (re/notes/system-font.md) and it arrives here through src/gen/tables.h. */
#include "wof.h"
#include "gen/tables.h"

#define FONT_GLYPHS 96          /* orig: the offset table has 0x5F + 1 entries */

static uint8_t       *font_file;
static uint32_t       font_len;
static uint16_t       font_height;
static uint8_t        font_first, font_last;
static const uint8_t *font_widths;
static const uint8_t *font_glyphs;
static uint16_t       font_offsets[FONT_GLYPHS];

static uint16_t be16(const uint8_t *p)
{
    return (uint16_t)(((uint16_t)p[0] << 8) | p[1]);
}

/* orig 0x012794 - loads newarmyfont and builds the glyph offset table.  Header: u16
 * height, u8 first character, u8 last, then one width byte per character; the glyph data
 * starts at 4 plus the character count rounded up to even, which is +100 for this file.
 * Glyph i occupies height rows of ((width + 15) / 16) words, and a width of 0 means there
 * is no glyph at all. */
int wof_font_load(void)
{
    uint32_t mark = wof_arena_mark();
    uint8_t *file = wof_load_file(wof_tbl_font_file, &font_len);

    if (!file) {
        wof_arena_release(mark);
        font_file = 0;
        return 0;
    }

    /* The font stays for the whole run, so it is copied down out of the scratch end. */
    font_file = (uint8_t *)wof_alloc(font_len);
    if (!font_file) {
        wof_arena_release(mark);
        return 0;
    }
    wof_mem_copy(font_file, file, font_len);
    wof_arena_release(mark);

    font_height = be16(font_file);
    font_first  = font_file[2];
    font_last   = font_file[3];
    font_widths = font_file + 4;

    uint16_t chars = (uint16_t)((uint8_t)(1 + font_last - font_first) + 1);

    chars      &= (uint16_t)0xFFFE;
    font_glyphs = font_file + 4 + chars;

    uint16_t at = 0;

    for (uint16_t i = 0; i < FONT_GLYPHS; i++) {
        font_offsets[i] = at;
        at = (uint16_t)(at + (uint16_t)(((font_widths[i] + 15) >> 4) * 2) * font_height);
    }
    return 1;
}

uint16_t wof_font_height(void)
{
    return font_height;
}

/* orig 0x01591E - the sum over the characters in range of width + 1, where a width of 0
 * counts as 10; characters outside first to last are skipped entirely. */
uint16_t wof_text_width(const char *s, uint16_t len)
{
    uint16_t w = 0;

    if (!font_file || len == 0)
        return 0;
    for (uint16_t i = 0; i < len; i++) {
        uint8_t c = (uint8_t)s[i];

        if (c > font_last || c < font_first)
            continue;

        uint8_t gw = font_widths[c - font_first];

        w = (uint16_t)(w + (gw ? gw : 10) + 1);
    }
    return w;
}

/* orig 0x015956 - the string into a 1-bit template.
 *
 * The template is buffer_height rows of ((buf_w + 15) / 16) * 2 bytes, cleared first.
 * Each glyph is ORed in at the pen position by shifting its words down inside a long, so
 * the template is big-endian and the port writes it that way.  With `justify` above the
 * text width the surplus is spread over the gaps: the quotient to every gap and one more
 * pixel to the first `remainder` gaps.  The division by len - 1 has no guard in the
 * original, so a one-character string asked to be wider than itself traps there; here it
 * simply spreads nothing.  Returns the pixel width, or 0 when the text does not fit. */
uint16_t wof_text_render(const char *s, uint16_t len, uint8_t *buffer, int16_t x, int16_t row,
                         int16_t justify, int16_t buf_w, int16_t buf_h)
{
    if (!font_file || !buffer || len == 0)
        return 0;

    uint16_t gaps  = (uint16_t)(len - 1);      /* the original's d0 = length - 1 */
    uint16_t width = wof_text_width(s, len);

    if (width > (uint16_t)buf_w)
        return 0;
    if ((uint16_t)buf_h > font_height)
        return 0;

    uint16_t result  = width;
    uint16_t gap_q   = 0;
    int16_t  gap_r   = 0;
    int16_t  surplus = (int16_t)(justify - (int16_t)width);

    if (surplus > 0 && gaps != 0) {
        result = (uint16_t)(result + surplus);
        gap_q  = (uint16_t)((uint16_t)surplus / gaps);
        gap_r  = (int16_t)((uint16_t)surplus % gaps);
    } else if (surplus > 0) {
        result = (uint16_t)(result + surplus);
    }

    uint16_t bpr = (uint16_t)((((uint16_t)buf_w + 15) >> 4) * 2);
    int32_t  pen = (int32_t)row * bpr;          /* byte offset of the first row */
    uint16_t bit = (uint16_t)(x & 15);
    int32_t  off = (int32_t)((x >> 4) * 2) + pen;

    wof_mem_set(buffer, 0, (uint32_t)((uint16_t)buf_h * bpr));

    for (uint16_t i = 0; i < len; i++) {
        uint8_t c = (uint8_t)s[i];

        if (c > font_last || c < font_first)
            continue;                           /* not even an advance */

        uint8_t  ci  = (uint8_t)(c - font_first);
        uint16_t adv = 10;
        uint8_t  gw  = font_widths[ci];

        if (gw) {
            adv = gw;

            uint16_t words   = (uint16_t)((gw + 15) >> 4);
            const uint8_t *g = font_glyphs + font_offsets[ci];
            int32_t  at      = off;

            for (uint16_t r = 0; r < font_height; r++) {
                for (uint16_t w = 0; w < words; w++) {
                    uint32_t v = (uint32_t)be16(g) << 16;

                    g += 2;
                    v >>= bit;
                    /* or.l into the big-endian long at `at` */
                    for (int k = 0; k < 4; k++) {
                        int32_t p = at + k;
                        if (p >= 0 && p < (int32_t)((uint16_t)buf_h * bpr))
                            buffer[p] |= (uint8_t)(v >> (24 - 8 * k));
                    }
                    at += 2;
                }
                at += bpr - 2 * words;
            }
        }

        bit = (uint16_t)(bit + adv + 1 + gap_q);
        if (--gap_r >= 0)
            bit++;
        off += (int32_t)((bit >> 4) * 2);
        bit &= 15;
    }
    return result;
}

/* The template on the current draw target.  The original hands it to BltTemplate with the
 * RastPort's pens and draw mode; the front end sets those per screen, which is M3.  M1
 * draws it in JAM1: the set bits take the pen, the rest of the box is left alone. */
void wof_text_draw(const char *s, uint16_t len, int16_t x, int16_t y, uint8_t pen)
{
    static uint8_t template_[1040];     /* the original's MaskBuffer, 80 bytes x 13 rows */
    const wof_target_t *t = wof_draw_target();

    if (!t->pixels || !font_file || font_height == 0)
        return;

    uint16_t w = wof_text_render(s, len, template_, 0, 0, 0, 640, (int16_t)font_height);

    if (!w)
        return;

    for (uint16_t r = 0; r < font_height; r++) {
        int32_t dy = y + r;

        if (dy < 0 || dy >= t->height)
            continue;
        for (uint16_t c = 0; c < w; c++) {
            int32_t dx = x + c;

            if (dx < 0 || dx >= t->width)
                continue;
            if (template_[r * 80 + (c >> 3)] & (0x80u >> (c & 7)))
                t->pixels[dy * t->stride + dx] = pen;
        }
    }
}

/* ------------------------------------------------------------------- the system font */

int wof_sysfont_present(void)
{
    return wof_tbl_topaz8_present;
}

/* graphics.library puts the pen on the baseline, and InitRastPort takes the number from
 * the font it sets: text_input adds it to the row it was given (RastPort +0x3E). */
uint16_t wof_sysfont_baseline(void)
{
    return wof_tbl_topaz8_present ? wof_tbl_topaz8_baseline : 0;
}

uint16_t wof_sysfont_width(const char *s, uint16_t len)
{
    if (!wof_tbl_topaz8_present)
        return wof_text_width(s, len);      /* the fallback of re/notes/system-font.md */
    return (uint16_t)(len * wof_tbl_topaz8_xsize);
}

/* graphics.Text on a fixed-width font: one cell per character, the glyph bits taken from
 * the location table's bit offset and width.  A character outside the font's range shows
 * the one extra glyph the table carries for exactly that, as the machine does. */
void wof_sysfont_draw(const char *s, uint16_t len, int16_t x, int16_t y, uint8_t pen)
{
    const wof_target_t *t = wof_draw_target();

    /* Without original/kick.rom there is no topaz 8, and the dialogs fall back to the
     * game's own font (re/notes/system-font.md).  The build says so when it happens. */
    if (!wof_tbl_topaz8_present) {
        wof_text_draw(s, len, x, y, pen);
        return;
    }
    if (!t->pixels)
        return;

    uint16_t glyphs = (uint16_t)(wof_tbl_topaz8_hi - wof_tbl_topaz8_lo + 1);

    for (uint16_t i = 0; i < len; i++) {
        uint8_t  c  = (uint8_t)s[i];
        uint16_t gi = (c >= wof_tbl_topaz8_lo && c <= wof_tbl_topaz8_hi)
                    ? (uint16_t)(c - wof_tbl_topaz8_lo) : glyphs;
        uint16_t bit_off = wof_tbl_topaz8_loc[gi * 2 + 0];
        uint16_t gw      = wof_tbl_topaz8_loc[gi * 2 + 1];
        int32_t  cell    = x + (int32_t)i * wof_tbl_topaz8_xsize;

        for (uint16_t r = 0; r < wof_tbl_topaz8_ysize; r++) {
            int32_t dy = y + r;

            if (dy < 0 || dy >= t->height)
                continue;

            const uint8_t *row = wof_tbl_topaz8_data + (uint32_t)r * wof_tbl_topaz8_modulo;

            for (uint16_t b = 0; b < gw; b++) {
                uint32_t bo = bit_off + b;
                int32_t  dx = cell + b;

                if (dx < 0 || dx >= t->width)
                    continue;
                if (row[bo >> 3] & (0x80u >> (bo & 7)))
                    t->pixels[dy * t->stride + dx] = pen;
            }
        }
    }
}

/* What vblank_server's ticker (orig 0x0118F8) reads of the font: the first character, a
 * character's width byte (the byte at +4 of the file, indexed from the first character),
 * and the word of a glyph at a byte offset from font_glyphs plus font_glyph_offsets. */
uint8_t wof_font_first(void)
{
    return font_first;
}

uint8_t wof_font_width_byte(uint8_t index)
{
    return font_file && 4u + index < font_len ? font_file[4u + index] : 0;
}

uint16_t wof_font_glyph_word(uint8_t index, uint32_t byte_offset)
{
    uint32_t at = (uint32_t)(font_glyphs - font_file) +
                  (index < FONT_GLYPHS ? font_offsets[index] : 0u) + byte_offset;

    return font_file && at + 1 < font_len ? be16(font_file + at) : 0;
}
