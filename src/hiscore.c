/* The high-score file, its screen and the name entry (re/notes/highscore.md).
 *
 * The 360-byte table is a local of high_score_screen on the machine, and high_score_table
 * (0x027DDA) points at it, so it exists only while that screen runs; here it is a member of
 * the front end's state for the same lifetime.  Its bytes are the file's bytes, big-endian
 * and untouched, because what the port writes has to equal what the original writes.
 *
 * The list is drawn in the **game** font: high_score_draw goes through text_draw_c, which
 * is text_draw, which is the template through BltTemplate.  Only the name entry uses
 * graphics.Text and therefore the system font (re/notes/drawing.md's four callers).
 */
#include "wof.h"
#include "gen/tables.h"

#define HS_SCORE 0
#define HS_RANK  4
#define HS_NAME  6

static uint8_t *entry_at(uint16_t i)
{
    return wof_f.hiscore + (uint32_t)i * WOF_HS_STRIDE;
}

static uint32_t be32_of(const uint8_t *p)
{
    return ((uint32_t)p[0] << 24) | ((uint32_t)p[1] << 16) | ((uint32_t)p[2] << 8) | p[3];
}

static void put_be32(uint8_t *p, uint32_t v)
{
    p[0] = (uint8_t)(v >> 24); p[1] = (uint8_t)(v >> 16);
    p[2] = (uint8_t)(v >> 8);  p[3] = (uint8_t)v;
}

static void put_be16(uint8_t *p, uint16_t v)
{
    p[0] = (uint8_t)(v >> 8); p[1] = (uint8_t)v;
}

uint32_t wof_high_score_of(uint16_t i)
{
    return i < WOF_HS_ENTRIES ? be32_of(entry_at(i) + HS_SCORE) : 0;
}

/* The C library's strncpy: the source up to its terminator, then NULs to `n`. */
static void str_ncpy(char *dst, const char *src, uint16_t n)
{
    uint16_t i = 0;

    while (i < n && src[i]) {
        dst[i] = src[i];
        i++;
    }
    while (i < n)
        dst[i++] = 0;
}

static uint16_t str_len(const char *s)
{
    uint16_t n = 0;

    while (s[n])
        n++;
    return n;
}

/* orig 0x0193CC high_score_load - the 360 bytes of the file, or ten entries of score 0,
 * rank 0 and a name of twelve spaces when there is no file.  Those ten are exactly what
 * entries 7 to 9 of the disk's own file hold. */
void wof_high_score_load(void)
{
    wof_file_t file;

    if (wof_dos_open(&file, wof_tbl_highscore_file)) {
        wof_dos_read(&file, wof_f.hiscore, (int32_t)sizeof wof_f.hiscore);
        wof_dos_close(&file);
        return;
    }
    for (uint16_t i = 0; i < WOF_HS_ENTRIES; i++) {
        uint8_t *e = entry_at(i);

        put_be32(e + HS_SCORE, 0);
        put_be16(e + HS_RANK, 0);
        str_ncpy((char *)e + HS_NAME, wof_tbl_hiscore_empty_name, 30);
    }
}

/* orig 0x019320 high_score_sort - a bubble sort by score, descending, swapping whole
 * 36-byte entries, repeated until a pass swaps nothing. */
void wof_high_score_sort(void)
{
    int swapped;

    do {
        swapped = 0;
        for (uint16_t i = 0; i < 9; i++) {
            uint8_t *a = entry_at(i), *b = entry_at((uint16_t)(i + 1));

            if ((int32_t)be32_of(a + HS_SCORE) < (int32_t)be32_of(b + HS_SCORE)) {
                uint8_t tmp[WOF_HS_STRIDE];

                wof_mem_copy(tmp, a, WOF_HS_STRIDE);
                wof_mem_copy(a, b, WOF_HS_STRIDE);
                wof_mem_copy(b, tmp, WOF_HS_STRIDE);
                swapped = 1;
            }
        }
    } while (swapped);
}

/* orig 0x019288 high_score_save - save_file("highscore", table, 360). */
void wof_high_score_save(void)
{
    wof_fs_write(wof_tbl_highscore_file, wof_f.hiscore, (uint32_t)sizeof wof_f.hiscore);
}

/* orig 0x01967E high_score_draw - the ten lines, three times over the same ten entries with
 * hiscore_offsets of -1, 1 and 0 and hiscore_pens of 0, 0 and 15, so that the text gets a
 * black outline one pixel up-left and one down-right before the white goes on top.  An
 * entry whose score is 0 is skipped. */
void wof_high_score_draw(void)
{
    wof_vport_t *v = &wof_f.vport[WOF_VP_A2];
    char         line[40];

    wof_draw_set_target(v);
    for (uint16_t p = 0; p < 3; p++) {
        int16_t offset = (int16_t)wof_tbl_hiscore_offsets[p];

        for (uint16_t i = 0; i < WOF_HS_ENTRIES; i++) {
            const uint8_t *e = entry_at(i);

            if (be32_of(e + HS_SCORE) == 0)
                continue;

            int16_t  x = (int16_t)(offset + 13);
            int16_t  y = (int16_t)(offset + 12 * i + 6);
            uint16_t rank = (uint16_t)((e[HS_RANK] << 8) | e[HS_RANK + 1]);

            wof_gfx_set_apen(v, (uint8_t)wof_tbl_hiscore_pens[p]);
            wof_gfx_set_drmd(v, WOF_JAM1);

            wof_gfx_move(v, x, y);
            wof_text_draw_line(v, line, wof_format(line, "%d", i + 1, 0));

            wof_gfx_move(v, (int16_t)(x + 0x28), y);
            wof_text_draw_line(v, line,
                               wof_format(line, "%-6ld", (int32_t)be32_of(e + HS_SCORE), 0));

            wof_gfx_move(v, (int16_t)(x + 0x96), y);
            wof_text_draw_line(v, line,
                               wof_format(line, "%-12s", 0,
                                          wof_tbl_rank_names[rank < 7 ? rank : 0]));

            wof_gfx_move(v, (int16_t)(x + 0x12C), y);
            wof_text_draw_line(v, (const char *)e + HS_NAME,
                               str_len((const char *)e + HS_NAME));
        }
    }
}

/* orig 0x019472 high_score_entry - the file, the sort, and a name only when the player's
 * score is **greater** than entry 9's, so a score equal to the tenth does not get in. */
wof_co_t wof_high_score_entry(void)
{
    wof_ctx_t   *c = &wof_f.co_inner;
    wof_vport_t *v;

    CO_BEGIN(c);
    for (uint16_t i = 0; i < sizeof wof_f.entry_name; i++)
        wof_f.entry_name[i] = 0;

    wof_high_score_load();
    wof_high_score_sort();
    if ((int32_t)wof_g.player_score <= (int32_t)wof_high_score_of(9))
        CO_RETURN(c);

    CO_CALL(c, &wof_f.co_screen, wof_screen_dialog());
    v = wof_back_vport();
    wof_draw_set_target(v);
    wof_clip_set_full();
    wof_gfx_set_apen(v, 8);
    wof_gfx_set_drmd(v, WOF_JAM1);
    wof_gfx_move(v, 52, 83);
    wof_gfx_text(v, wof_tbl_entry_line1, str_len(wof_tbl_entry_line1));
    wof_gfx_move(v, 91, 92);
    wof_gfx_text(v, wof_tbl_entry_line2, str_len(wof_tbl_entry_line2));

    wof_gfx_set_apen(v, 2);
    wof_gfx_move(v, 80, 100);
    wof_gfx_draw(v, 225, 100);
    wof_gfx_draw(v, 225, 113);
    wof_gfx_draw(v, 80, 113);
    wof_gfx_draw(v, 80, 100);

    for (uint32_t i = 0; i < WOF_PAL_COLOURS; i++)
        wof_f.hiscore_pal[i] = i < 16 ? wof_tbl_dialog_palette[i] : 0;

    CO_CALL(c, &wof_f.co_show, wof_view_show_wait(wof_f.back_view));
    CO_CALL(c, &wof_f.co_fade, wof_fade_to(wof_f.hiscore_pal));
    CO_CALL(c, &wof_f.co_text, wof_text_input(wof_f.entry_name, 16, 82, 102));

    {
        uint8_t *e = entry_at(9);

        put_be32(e + HS_SCORE, wof_g.player_score);
        str_ncpy((char *)e + HS_NAME, wof_f.entry_name, 17);
        put_be16(e + HS_RANK, wof_g.rank_played);
    }
    CO_CALL(c, &wof_f.co_fade, wof_fade_out());
    wof_high_score_sort();
    wof_high_score_save();
    CO_END(c);
}

/* orig 0x019856 high_score_screen - the name entry first, then the slab with the ten lines
 * on it and the picture above it, both faded up together. */
wof_co_t wof_high_score_screen(void)
{
    wof_ctx_t *c = &wof_f.co_stage;

    CO_BEGIN(c);
    wof_music_start("wofsongs", 0);
    CO_CALL(c, &wof_f.co_inner, wof_high_score_entry());
    CO_CALL(c, &wof_f.co_screen, wof_screen_hiscore());

    /* The screen is view A alone, and the slab is its **second** viewport. */
    wof_f.back_view = WOF_VIEW_A;
    wof_load_picture_black_into(WOF_VP_A2, wof_tbl_hiscoreslab_pic, wof_f.slab_pal);
    wof_clip_set_full();
    wof_high_score_draw();
    wof_load_picture_black_into(WOF_VP_A1, wof_tbl_hiscore_pic, wof_f.hiscore_pal);

    CO_CALL(c, &wof_f.co_show, wof_view_show_wait(WOF_VIEW_A));
    CO_CALL(c, &wof_f.co_fade, wof_fade_to_pair(wof_f.hiscore_pal, wof_f.slab_pal));
    CO_CALL(c, &wof_f.co_frames, wof_wait_frames_or_fire(0x708));
    CO_CALL(c, &wof_f.co_fade, wof_fade_out_pair());
    CO_END(c);
}
