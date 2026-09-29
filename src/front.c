/* The front end: the story scroller, the title sequence, the rank selection, the briefing
 * and the outer loop that joins them up (re/notes/frontend.md, SPEC 6.3).
 *
 * Everything here blocks in the original and is a coroutine here.  The rule that makes the
 * two agree is in src/coro.h: one CO_WAIT is one VBlank, because the headless original
 * delivers a VBlank exactly where the program waits and the shell issues one wof_pass per
 * VBlank.  wof_init runs the coroutine up to the first wait, which is the one inside
 * display_init, so the music call that follows it is logged at VBlank 1 as it is there.
 *
 * The routine order follows the original's addresses, so that a reader can move between
 * this file and re/Wings.lst.
 */
#include "wof.h"
#include "gen/tables.h"

/* ------------------------------------------------------------------ small helpers */

static uint16_t str_len(const char *s)
{
    uint16_t n = 0;

    while (s && s[n])
        n++;
    return n;
}

/* orig 0x017422 load_picture_black - the picture is decoded into the **back** view, its
 * colours are handed to the caller and the viewport's table is blacked, so that the caller
 * can show the view and fade up to the colours it was given.  That is what keeps a picture
 * from ever being seen while it is decoded. */
void wof_load_picture_black_into(uint8_t which, const char *name, uint16_t *palette_out)
{
    wof_vport_t *v = &wof_f.vport[which];
    uint32_t mark = wof_arena_mark();
    uint32_t len  = 0;
    uint8_t *raw;

    if (which >= WOF_VP_MAX)
        return;
    raw = wof_load_file(name, &len);
    if (raw)
        wof_iff_to_vport(raw, len, v);        /* orig 0x016EB2 view_load_picture */
    wof_arena_release(mark);

    for (uint32_t i = 0; i < WOF_PAL_COLOURS; i++) {
        if (palette_out)
            palette_out[i] = v->colours[i];
        v->colours[i] = 0;
    }
}

/* The usual call: into the back view's first viewport. */
void wof_load_picture_black(const char *name, uint16_t *palette_out)
{
    uint8_t which = wof_f.view_first[wof_f.back_view];

    if (which != WOF_VP_NONE)
        wof_load_picture_black_into(which, name, palette_out);
}

/* ------------------------------------------------------------------ the story scroller */

/* orig 0x017D4E story_copper_build, as the port expresses it: the ramp count and the row
 * where the plane pointer is reloaded.  The reload is emitted only for a wrap row of 196 or
 * less - the three places that can emit it cover 0 to 15, 16 to 180 and 181 to 196 between
 * them - and above that the wrap point is below the visible text anyway. */
static void story_copper_build(uint16_t ramp, int16_t wrap)
{
    wof_vport_t *v = wof_front_vport();

    if (!v)
        return;
    v->ramp    = ramp;
    v->ring_at = (wrap >= 0 && wrap <= 196) ? (uint16_t)wrap : WOF_VP_RING_NONE;
}

/* orig 0x017E80 story_screen.  Every 14th step, which is every 56 VBlanks, a 12-row band
 * is cleared and one line of the text block is drawn into it in the game font; the plane
 * pointer advances by a row per step, so the text walks up the screen.  The first line goes
 * at row 196 and every later one 14 rows **before** the current plane start, which is the
 * bottom of the window because of the ring. */
static wof_co_t story_screen(void)
{
    wof_ctx_t   *c = &wof_f.co_inner;
    wof_vport_t *v;
    int16_t      y;

    CO_BEGIN(c);
    CO_CALL(c, &wof_f.co_screen, wof_screen_story());

    wof_f.story_wrap   = 0xD2;
    wof_f.story_at     = 0;
    wof_f.story_lines  = 0;
    wof_f.story_step   = 0;
    wof_f.story_last   = 0;

    for (;;) {
        if (wof_f.story_step % 14u == 0) {
            v = wof_front_vport();
            y = (int16_t)(wof_f.story_step ? 0xC4 - 0xD2 : 0xC4);

            wof_gfx_set_apen(v, 0);
            wof_gfx_rect_fill(v, 0, y, 0x27F, (int16_t)(y + 0x0B));
            wof_gfx_set_apen(v, 1);

            if (wof_f.story_lines < 0x35) {
                const char *line = (const char *)wof_tbl_story_text + wof_f.story_at;
                uint16_t    len  = str_len(line);
                int16_t     wide = line[len + 1] ? 0x267 : 0;

                wof_gfx_move(v, 0, y);
                wof_text_draw_justified(v, line, len, wide);
                wof_f.story_at   = (uint16_t)(wof_f.story_at + len + 1);
                wof_f.story_last = 0xD2;
            }
            wof_f.story_lines++;
        }

        CO_CALL(c, &wof_f.co_frames, wof_wait_frames_or_fire(2));
        story_copper_build(0x10, wof_f.story_wrap);
        wof_view_show(WOF_VIEW_A);
        CO_CALL(c, &wof_f.co_frames, wof_wait_frames_or_fire(2));

        wof_f.story_last--;
        wof_f.story_step++;
        wof_front_vport()->scroll++;
        wof_f.story_wrap--;
        if (wof_f.story_wrap <= 0) {
            wof_f.story_wrap = 0xD2;
            wof_front_vport()->scroll = 0;
            wof_f.story_step = 0;
        }
        if (wof_f.story_last < 0 || wof_poll_fire())
            break;
    }

    /* The wind-down: sixteen rounds that take the two grey ramps out. */
    for (wof_f.story_ramp = 0x10; wof_f.story_ramp > 0; wof_f.story_ramp--) {
        story_copper_build(wof_f.story_ramp, wof_f.story_wrap);
        wof_view_show(WOF_VIEW_A);
        CO_CALL(c, &wof_f.co_frames, wof_wait_frames_or_fire(2));
    }
    CO_END(c);
}

/* ------------------------------------------------- the publisher logo, title and credits */

/* orig 0x018022 title_sequence.  Show, fade up, wait, fade out, show the next; the logo is
 * the exception, fading first to a palette of its own.  Fire at any of the waits skips the
 * rest of the sequence at once. */
static wof_co_t title_sequence(void)
{
    wof_ctx_t *c = &wof_f.co_stage;

    CO_BEGIN(c);
    CO_CALL(c, &wof_f.co_music, wof_music_start(2));
    CO_CALL(c, &wof_f.co_inner, story_screen());
    CO_CALL(c, &wof_f.co_music, wof_music_start(1));
    CO_CALL(c, &wof_f.co_screen, wof_screen_picture());

    wof_load_picture_black(wof_tbl_broderbund_pic, wof_f.title_pal);
    CO_CALL(c, &wof_f.co_show, wof_view_show_wait(wof_f.back_view));
    CO_CALL(c, &wof_f.co_fade, wof_fade_to(wof_tbl_logo_fade_palette));
    CO_CALL(c, &wof_f.co_frames, wof_wait_frames_or_fire(0x3C));
    if (wof_frames_fire())
        goto done;

    CO_CALL(c, &wof_f.co_fade, wof_fade_to(wof_f.title_pal));
    wof_load_picture_black(wof_tbl_wingstitle_pic, wof_f.title_pal);
    CO_CALL(c, &wof_f.co_frames, wof_wait_frames_or_fire(0x78));
    if (wof_frames_fire())
        goto done;

    CO_CALL(c, &wof_f.co_fade, wof_fade_out());
    CO_CALL(c, &wof_f.co_show, wof_view_show_wait(wof_f.back_view));
    CO_CALL(c, &wof_f.co_fade, wof_fade_to(wof_f.title_pal));
    wof_load_picture_black(wof_tbl_creditscreen_pic, wof_f.title_pal);
    CO_CALL(c, &wof_f.co_frames, wof_wait_frames_or_fire(0x12C));
    if (wof_frames_fire())
        goto done;

    CO_CALL(c, &wof_f.co_fade, wof_fade_out());
    CO_CALL(c, &wof_f.co_show, wof_view_show_wait(wof_f.back_view));
    CO_CALL(c, &wof_f.co_fade, wof_fade_to(wof_f.title_pal));
    CO_CALL(c, &wof_f.co_frames, wof_wait_frames_or_fire(0x258));

done:
    CO_CALL(c, &wof_f.co_fade, wof_fade_out());
    CO_END(c);
}

/* ------------------------------------------------------------------ the rank selection */

/* The highlight: the shape of the cursor's index, drawn in exclusive-or at its own stored
 * source position, so that drawing it again erases it. */
static void rank_highlight(void)
{
    const wof_container_t *container = &wof_assets.c[WOF_C_SELECTRANK];

    if (wof_f.rank_shape < 0 || wof_f.rank_shape >= (int16_t)container->count)
        return;

    const wof_shape_t *s = &container->shapes[wof_f.rank_shape];

    wof_shape_draw_xor(s, (int16_t)s->marker, (int16_t)s->src_y);
}

/* orig 0x018262 rank_select.  Eight entries: seven ranks and, at index 7, the load dialog.
 * menu_input moves the cursor and chooses; 1800 rounds without any input set demo_mode to
 * 1, which asks for a file this disk does not carry, so it falls back to 0. */
static wof_co_t rank_select(void)
{
    wof_ctx_t *c = &wof_f.co_stage;

    CO_BEGIN(c);
    wof_g.rank_cursor = 0;
    CO_CALL(c, &wof_f.co_music, wof_music_start(4));
    CO_CALL(c, &wof_f.co_screen, wof_screen_picture());
    wof_g.loaded_game = 0;
    wof_load_picture_black(wof_tbl_selectrank_pic, wof_f.rank_pal);

    wof_f.rank_prev  = wof_g.rank_cursor;
    wof_draw_set_target(wof_back_vport());
    wof_clip_set_full();
    wof_f.rank_shape = wof_shape_by_index(&wof_assets.c[WOF_C_SELECTRANK], wof_g.rank_cursor);
    rank_highlight();
    CO_CALL(c, &wof_f.co_show, wof_view_show_wait(wof_f.back_view));
    CO_CALL(c, &wof_f.co_fade, wof_fade_to(wof_f.rank_pal));
    wof_view_copy(wof_f.front_view, wof_f.back_view);

    for (;;) {
        CO_CALL(c, &wof_f.co_menu, wof_menu_input(1));
        if (wof_menu_result() == 0)
            break;
        if (wof_menu_result() == 1000) {
            wof_g.demo_mode = 1;
            break;
        }
        wof_g.rank_cursor = (uint16_t)(wof_g.rank_cursor + wof_menu_result());
        if ((int16_t)wof_g.rank_cursor < 0)
            wof_g.rank_cursor = 7;
        if ((int16_t)wof_g.rank_cursor > 7)
            wof_g.rank_cursor = 0;
        if (wof_g.rank_cursor == wof_f.rank_prev)
            continue;

        wof_draw_set_target(wof_back_vport());
        rank_highlight();
        wof_f.rank_shape = wof_shape_by_index(&wof_assets.c[WOF_C_SELECTRANK],
                                              wof_g.rank_cursor);
        rank_highlight();
        CO_CALL(c, &wof_f.co_show, wof_view_show_wait(wof_f.back_view));
        wof_view_copy(wof_f.front_view, wof_f.back_view);
        wof_f.rank_prev = wof_g.rank_cursor;
        CO_CALL(c, &wof_f.co_release, wof_wait_input_release());
    }

    /* DEVELOPMENT (M3 deliverable 7): the save dialog has no way in before M4 ports
     * ingame_keys, and the user has to be able to look at it.  The request is made from
     * outside the port's key layer and is answered here, where the load dialog is. */
    if (wof_f.dev_dialog) {
        /* The mode goes into the state, not onto the stack: CO_CALL gives the pass back,
         * and a local does not survive that (src/coro.h). */
        wof_f.dialog_mode = (uint16_t)(wof_f.dev_dialog - 1);
        wof_f.dev_dialog  = 0;
        CO_CALL(c, &wof_f.co_inner, wof_load_save_dialog(wof_f.dialog_mode));
        wof_view_set_picture(wof_f.back_view);
        wof_view_copy(wof_f.front_view, wof_f.back_view);
    }

    while (wof_g.rank_cursor == 7) {
        /* M3 deliverable 6 fills the dialog in; until then a cancel comes straight back. */
        CO_CALL(c, &wof_f.co_inner, wof_load_save_dialog(0));
        if (wof_f.dialog_result == 0) {
            wof_g.loaded_game = 1;
            CO_CALL(c, &wof_f.co_fade, wof_fade_out());
            CO_RETURN(c);
        }
        wof_view_set_picture(wof_f.back_view);
        wof_view_copy(wof_f.front_view, wof_f.back_view);
        CO_CALL(c, &wof_f.co_menu, wof_menu_input(1));
        if (wof_menu_result() != 0 && wof_menu_result() != 1000) {
            wof_g.rank_cursor = (uint16_t)(wof_g.rank_cursor + wof_menu_result());
            if ((int16_t)wof_g.rank_cursor < 0)
                wof_g.rank_cursor = 7;
            if ((int16_t)wof_g.rank_cursor > 7)
                wof_g.rank_cursor = 0;
        }
    }

    CO_CALL(c, &wof_f.co_fade, wof_fade_out());

    /* Demo recording (demo_mode 2) needs a file name on the command line, which the port
     * has no way of giving; demo playback asks for `wofdemo`, which is not on this disk, so
     * demo_mode falls straight back to 0.  Both belong to M7. */
    wof_g.demo_mode = 0;
    /* The chosen rank is stored twice: once as the rank the run is played at and once as
     * the rank a high-score entry is written with (re/notes/frontend.md). */
    wof_g.rank_chosen = wof_g.rank_cursor;
    wof_g.rank_played = wof_g.rank_cursor;
    wof_g.mission_number  = 1;
    CO_CALL(c, &wof_f.co_music, wof_music_stop());           /* 0x0184D6 */
    CO_END(c);
}

/* ------------------------------------------------------------------------ the briefing */

/* orig 0x018590 mission_briefing.  The background is the shape named `rank` out of
 * world.shp - shapes/Rank.iff is on the disk and nothing opens it - and four pieces of text
 * in the game font go on top.  Fire or 240 rounds go on to the mission; Control and the R
 * key fade out and send main back to the top of the outer loop. */
static wof_co_t mission_briefing(void)
{
    wof_ctx_t   *c = &wof_f.co_stage;
    wof_vport_t *v;
    char         number[8];

    CO_BEGIN(c);
    wof_f.briefing_result = 0;
    wof_f.briefing        = 1;
    CO_CALL(c, &wof_f.co_screen, wof_screen_hires3());

    {
        int16_t index = wof_shape_find(&wof_assets.c[WOF_C_WORLD], 0x72616E6Bu);  /* 'rank' */

        v = wof_back_vport();
        wof_draw_set_target(v);
        wof_clip_set_full();
        for (uint32_t i = 0; i < WOF_PAL_COLOURS; i++)
            wof_f.briefing_pal[i] = i < 16 ? wof_tbl_briefing_palette[i] : 0;

        if (index >= 0) {
            const wof_shape_t *s = &wof_assets.c[WOF_C_WORLD].shapes[index];

            wof_shape_draw(s, (int16_t)(0x140 - (s->wbytes << 2)),
                           (int16_t)(0x65 - (s->height >> 1)));
        }
        /* No pen is ever set here: the text comes out in what InitRastPort left behind,
         * which is pen 0xFF masked to the viewport's three planes, in JAM2. */
        wof_gfx_move(v, 0x128, 0x3D);
        {
            const char *name = wof_tbl_rank_names[wof_g.rank_played < 7 ? wof_g.rank_played : 0];

            wof_text_draw_line(v, name, str_len(name));
        }
        wof_gfx_move(v, 0x154, 0x49);
        wof_text_draw_line(v, number, wof_number(number, wof_g.mission_number));
        wof_gfx_move(v, 0x154, 0x77);
        wof_text_draw_line(v, number, wof_number(number, wof_g.briefing_islands));
        wof_gfx_move(v, 0x154, 0x83);
        wof_text_draw_line(v, number, wof_number(number, wof_g.briefing_ships));
    }

    CO_CALL(c, &wof_f.co_show, wof_view_show_wait(wof_f.back_view));
    CO_CALL(c, &wof_f.co_fade, wof_fade_to(wof_f.briefing_pal));

    CO_WAIT(c);
    wof_f.briefing_i = 1;
    while ((int16_t)wof_f.briefing_i < 0xF0 && !wof_poll_fire()) {
        CO_WAIT(c);
        if (wof_key_available()) {
            uint32_t key = wof_key_get() & 0x7FFFFFFFu;

            if ((key >> 16) & 0x0008u) {                   /* IEQUALIFIER_CONTROL */
                if ((uint8_t)wof_key_to_char(key & 0xFFFFu) == 'r') {
                    CO_CALL(c, &wof_f.co_fade, wof_fade_out());
                    wof_f.briefing_result = 1;
                    wof_f.briefing        = 0;
                    CO_RETURN(c);
                }
            }
        }
        wof_f.briefing_i++;
    }
    CO_CALL(c, &wof_f.co_fade, wof_fade_out());
    wof_f.briefing = 0;
    CO_END(c);
}

/* ------------------------------------------------------------------- the outer loop */

void wof_front_init(void)
{
    wof_f.co_main.line   = 0;
    wof_f.mission_count  = 0;
    wof_display_init();
}

/* ----------------------------------------------------------------- the mission (M4) */

/* A registered global's word by its original address, for the Help key's walk over the
 * island tables, which reads on past the one it starts in. */
static uint16_t global_word(uint32_t addr)
{
    uint8_t hi = 0, lo = 0;

    wof_global_byte(addr, &hi);
    wof_global_byte(addr + 1u, &lo);
    return (uint16_t)((hi << 8) | lo);
}

/* A text of the DATA hunk, by its original address. */
static const char *image_text(uint32_t addr)
{
    return (const char *)&wof_tbl_data_image[addr - 0x023000u];
}

/* orig 0x01555A - a ticker message, unless one is running: ticker_message names it by the
 * original's address of its text (src/input.c). */
static void ticker_message(uint32_t addr)
{
    if (wof_g.ticker_message == 0)
        wof_g.ticker_message = addr;
}

/* orig 0x01CCF6 ingame_keys - every waiting key, once per pass from the head of the inner
 * loop, in flight and paused alike (re/notes/keys.md, "In flight and paused").  The key is
 * converted without its qualifier; with Control: r restarts (the mission ends and the rank
 * selection comes), s the music, f the vertical flip, g the save dialog on the carrier, l the
 * load dialog, b the crash reporter, c deletes the high scores, v the version in the ticker.
 * Any other key, and a Control key that is none of those, goes on to Escape, the pause, and
 * the cheat sequence c o l i n with the debug keys it unlocks.  Switching the music off,
 * the save and load dialogs and the pause clear the sound slots (0x011F4E), which stops
 * every channel; what a saved game holds is M7's. */
static wof_co_t ingame_keys(void)
{
    wof_ctx_t *c = &wof_f.co_keys;

    CO_BEGIN(c);
    if (wof_f.pause_request) {
        /* The shell's request (wof_request_pause), taken where Escape would be. */
        wof_f.pause_request = 0;
        if (!wof_g.pause_flag) {
            wof_g.pause_flag = 0xFF;
            wof_sound_slots_clear();                          /* as Escape: 0x01CE8E */
        }
    }
    wof_g.last_key = 0;
    while (wof_key_available()) {
        wof_g.last_key = wof_key_get() & 0x7FFFFFFFu;
        wof_f.keys_char = (uint8_t)wof_key_to_char(wof_g.last_key & 0xFFFFu);
        if ((wof_g.last_key >> 16) & 0x0008u) {
            if (wof_f.keys_char == 'r') {
                wof_g.ticker_message = 0;
                wof_ticker_clear();
                CO_CALL(c, &wof_f.co_fade, wof_fade_out_pair());
                wof_g.end_of_mission = 0xFF;
                wof_g.quit_flag = 0xFF;
                continue;
            }
            if (wof_f.keys_char == 's') {
                wof_g.opt_music_off = (uint8_t)~wof_g.opt_music_off;
                if (wof_g.opt_music_off)
                    wof_sound_slots_clear();                  /* 0x01CD60 */
                continue;
            }
            if (wof_f.keys_char == 'f') {
                wof_g.opt_invert_vertical = (uint8_t)~wof_g.opt_invert_vertical;
                wof_invert_vertical_follow();
                continue;
            }
            if (wof_f.keys_char == 'g') {
                if (wof_m.player[0].on_deck != 1)
                    continue;
                wof_sound_slots_clear();                      /* 0x01CD86 */
                CO_CALL(c, &wof_f.co_inner, wof_load_save_dialog(1));
                wof_screen_game_restore();
                wof_input_queue_clear();
                continue;
            }
            if (wof_f.keys_char == 'l') {
                if (wof_g.demo_mode != 0)
                    continue;
                wof_sound_slots_clear();                      /* 0x01CDB0 */
                wof_free_dash_shapes();                       /* 0x0134AE */
                wof_free_sounds();                            /* 0x01346C */
                wof_free_for_load();                          /* 0x011256 */
                wof_g.loaded_game = 0;
                CO_CALL(c, &wof_f.co_inner, wof_load_save_dialog(0));
                if (wof_f.dialog_result == 0) {
                    WOF_STANDIN("M7 PART 2 STAND-IN: 0x01CDD4, a loaded game: the briefing and the mission again");
                    continue;
                }
                wof_load_dash_assets();
                wof_sounds_load();
                wof_screen_game_restore();
                wof_input_queue_clear();
                continue;
            }
            if (wof_f.keys_char == 'b') {
                /* An illegal instruction, the way into the game's own crash reporter, which
                 * returns to the loop; the port has no crash reporter. */
                continue;
            }
            if (wof_f.keys_char == 'c') {
                wof_fs_delete("highscore");
                continue;
            }
            if (wof_f.keys_char == 'v') {
                uint16_t args[2] = { (uint16_t)wof_g.g_027de2, (uint16_t)wof_g.g_027de4 };

                wof_raw_do_fmt((char *)wof_g.ticker_text_2, image_text(0x025F43u), args);
                ticker_message(0x027E00u);
                continue;
            }
        }
        {
            uint8_t  ch  = wof_f.keys_char;
            uint8_t  raw = (uint8_t)wof_g.last_key;          /* 0x026F5F */
            int16_t *cs  = &wof_g.cheat_state;

            if (ch == 0x1B) {
                wof_g.pause_flag = (uint8_t)~wof_g.pause_flag;
                if (wof_g.pause_flag)
                    wof_sound_slots_clear();                  /* 0x01CE8E */
                continue;
            }
            if (ch == 'o') {
                *cs = *cs == 1 ? 2 : 0;
                continue;
            }
            if (ch == 'l') {
                *cs = *cs == 2 ? 3 : 0;
                continue;
            }
            if (ch == 'n') {
                *cs = *cs == 4 ? 5 : 0;
                continue;
            }
            if (ch == 'i') {
                if (*cs == 0)
                    continue;
                if (*cs == 5) {
                    wof_g.pitch_step = (int16_t)(wof_g.pitch_step + 0x32);
                    continue;
                }
                if (*cs == 3) {
                    *cs = 4;
                    continue;
                }
                *cs = 0;
            }
            if (ch == 'k') {
                if (*cs == 5)
                    wof_g.pitch_step = (int16_t)(wof_g.pitch_step - 0x32);
                continue;
            }
            if (ch == 'f') {
                if (*cs == 5)
                    wof_m.player[0].fuel = 0x80;
                continue;
            }
            if (ch == 'p') {
                if (*cs == 5)
                    wof_g.lives++;
                continue;
            }
            if (raw == 0x59) {                                /* F10 */
                if (*cs == 5)
                    wof_g.ticker_message = 0;
                continue;
            }
            if (ch == ' ') {
                /* Four AvailMem figures: the port's arena has one kind of memory, so its free
                 * bytes stand for chip, largest and total, and fast memory is none. */
                uint32_t free_bytes = wof_arena_size() - wof_arena_used();
                uint16_t args[8] = {
                    (uint16_t)(free_bytes >> 16), (uint16_t)free_bytes, 0, 0,
                    (uint16_t)(free_bytes >> 16), (uint16_t)free_bytes,
                    (uint16_t)(free_bytes >> 16), (uint16_t)free_bytes,
                };

                if (*cs != 5)
                    continue;
                wof_raw_do_fmt((char *)wof_g.ticker_text, image_text(0x023B3Au), args);
                ticker_message(0x02716Au);
                continue;
            }
            if (raw == 0x5F) {                                /* Help */
                uint16_t d1 = (uint16_t)((uint16_t)wof_g.draw_player_x >> 2);
                uint16_t n = 0;
                uint16_t args[2];

                if (*cs != 5)
                    continue;
                while (n < 64 && !(d1 < global_word(0x025438u + 2u * n)))
                    n++;
                args[0] = global_word(0x025450u + 4u * n);
                args[1] = global_word(0x025452u + 4u * n);
                wof_raw_do_fmt((char *)wof_g.ticker_text_2, image_text(0x025F1Au), args);
                ticker_message(0x027E00u);
                continue;
            }
            if (ch == 'q') {
                if (*cs == 5) {
                    wof_g.g_026f80 = (uint16_t)((wof_g.g_026f80 & 0x00FFu) | 0xFF00u);   /* st.b */
                    wof_g.quit_flag = 0xFF;
                }
                continue;
            }
            if (ch == 'm') {
                if (*cs != 5)
                    continue;
                if (wof_g.weapon_count == 0xFF) {
                    wof_g.weapon_count = wof_tbl_weapons_per_type[(uint16_t)wof_g.weapon_type];
                    wof_weapon_gauge_reset();
                } else {
                    wof_g.weapon_count = 0xFF;
                }
                continue;
            }
            if (ch == 'r') {
                if (*cs == 5)
                    wof_objects_clear();
                continue;
            }
            if (ch == 'c') {
                if (*cs == 0)
                    *cs = 1;
                else if (*cs == 5 && ++wof_g.weapon_type == 3)
                    wof_g.weapon_type = 0;
                continue;
            }
            if (ch == '8' || ch == '2' || ch == '4' || ch == '6') {
                if (*cs != 5)
                    continue;
                wof_g.g_025350 += ch == '8' ? 0x1000 : ch == '2' ? -0x1000 : ch == '4' ? -0x100 : 0x100;
            }
            if (ch == 'd' && *cs == 5) {
                wof_m.player[0].oil = 0x80;
                wof_m.player[0].on_deck = 0;
                wof_g.g_026f72 = (int16_t)~wof_g.g_026f72;
            }
        }
    }
    CO_END(c);
}

/* orig 0x0114D8 run_queued_ticks - one tick per queued byte.  In demo playback and
 * recording it first spins until the server has taken two bytes (M7). */
static wof_co_t run_queued_ticks(void)
{
    wof_ctx_t *c = &wof_f.co_ticks;

    CO_BEGIN(c);
    if (wof_g.g_026d44)
        WOF_STANDIN("M7 PART 2 STAND-IN: 0x0114E0, run_queued_ticks, demo playback and recording");
    if ((int8_t)wof_g.pause_flag < 0)
        CO_RETURN(c);
    while ((int16_t)wof_g.input_queue_count > 0)
        CO_CALL(c, &wof_f.co_tick, wof_logic_tick());
    wof_g.g_026d44 = (int16_t)(wof_g.demo_mode != 0 ? 2 : 0);
    CO_END(c);
}

/* The setup after the briefing and the inner loop, main from 0x0100B6 to 0x0101C2, with a
 * campaign's next mission (0x010132 to 0x01018D), which goes back into the setup at its
 * reset (0x0100D2).  It returns with wof_f.mission_end saying how the loop was left: 1 for
 * quit_flag, which goes on to the high scores, 2 for end_of_mission or the next mission's
 * briefing left with Control-R, both of which go straight back to the outer loop. */
static wof_co_t mission(void)
{
    wof_ctx_t *c = &wof_f.co_mission;

    CO_BEGIN(c);
    /* The point the original reaches mission_display_setup at, as the harness's observer
     * sees it. */
    wof_trace_add("mission", wof_g.rank_played, wof_g.mission_number, 0, 0, 0, 0);
    wof_dashboard_invalidate();                               /* orig 0x01EDAA */
    CO_CALL(c, &wof_f.co_setup, wof_mission_display_setup());
    wof_load_ship_shapes();
    wof_build_master_lists();
    wof_sounds_load();
    if (!wof_g.loaded_game) {
next_mission:                                                 /* orig 0x0100D2 */
        wof_mission_reset_tables();                           /* orig 0x0135A8 */
        wof_test_poke_after_reset();
        wof_player_restart_state();                           /* orig 0x013684 */
        wof_g.loaded_game = 0;
        wof_g.pause_flag = 0;
        wof_g.soldiers_killed = 0;
        wof_g.tick_input = 0;
    }
    wof_g.outside_mission = 0;
    wof_g.loaded_game = 0;
    CO_CALL(c, &wof_f.co_tick, wof_logic_tick());             /* main's own logic_tick */
    wof_input_queue_clear();
    if (wof_g.demo_mode != 0)
        wof_g.g_026d44 = 2;

    /* Step S of the headless original: the mission's inner loop is reached. */
    wof_trace_add("step_s", wof_g.rank_played, wof_g.mission_number, 0, 0, 0, 0);
    wof_f.mission_count++;
    wof_trace_globals();
    wof_trace_mission();
    wof_test_step_s(wof_f.mission_count);
    wof_g.g_026d54 = (uint16_t)((wof_g.g_026d54 & 0x00FFu) | 0xFF00u);   /* st.b */

    for (;;) {                                                /* orig 0x01010E */
        CO_CALL(c, &wof_f.co_keys, ingame_keys());
        if (wof_g.quit_flag)
            break;
        if (wof_g.pause_flag) {
            CO_CALL(c, &wof_f.co_vblank, wof_wait_next_vblank());
            continue;
        }
        if (wof_g.g_025364 && wof_g.g_0253bc) {
            /* 0x010132: the mission is won (0x0253BC, set only by mission_won 0x015694) and
             * the aircraft is back in the hold with the weapon menu up: the campaign's next
             * mission.  mission_won has already counted the mission on, or the rank with the
             * promotion, whose balloons_on gives the extra Hellcat here (the manual, page 8). */
            wof_g.g_0253bc = 0;
            wof_g.g_025364 = 0;
            wof_sound_slots_clear();                          /* orig 0x011F4E */
            wof_g.ticker_message = 0;
            wof_ticker_clear();
            CO_CALL(c, &wof_f.co_fade, wof_fade_out_pair());
            wof_free_mission_assets();
            if (wof_g.balloons_on)
                wof_g.lives++;                                /* 0x01015C: addq.b */
            wof_choose_night();                               /* orig 0x0111FC */
            wof_dashboard_invalidate();
            wof_map_load();
            CO_CALL(c, &wof_f.co_stage, mission_briefing());
            if (wof_f.briefing_result) {                      /* 0x010172: tst.b d0 */
                wof_f.mission_end = 2;
                CO_RETURN(c);
            }
            wof_load_dash_assets();
            wof_trace_add("mission", wof_g.rank_played, wof_g.mission_number, 0, 0, 0, 0);
            CO_CALL(c, &wof_f.co_setup, wof_mission_display_setup());
            wof_load_ship_shapes();
            wof_build_master_lists();
            wof_sounds_load();
            goto next_mission;                                /* 0x01018A: bra 0x0100D2 */
        }
        CO_CALL(c, &wof_f.co_pass, wof_frame_update());
        CO_CALL(c, &wof_f.co_ticks, run_queued_ticks());
        if (wof_g.end_of_mission) {
            wof_f.mission_end = 2;
            CO_RETURN(c);
        }
        if (wof_g.demo_mode == 1 && wof_poll_fire())
            break;
        if (wof_g.quit_flag)
            break;
    }
    wof_f.mission_end = 1;
    CO_END(c);
}

/* orig 0x010006 main, with the outer loop at 0x010066 (re/notes/frontend.md's diagram).
 * The initialisation that comes before it is src/assets.c and wof_init; what is left of it
 * here is the wait inside display_init, which is why the music call of the title sequence
 * falls on VBlank 1 as it does in the original. */
wof_co_t wof_front(void)
{
    wof_ctx_t *c = &wof_f.co_main;

    CO_BEGIN(c);
    wof_g.g_027de2 = 1;                                       /* 0x01AA50 */
    wof_g.g_027de4 = 0;
    wof_sound_init();                                         /* 0x012598, in open_libraries */
    wof_g.outside_mission = 0xFF;
    wof_g.g_024cac = 0xFFFF;
    CO_CALL(c, &wof_f.co_show, wof_cop_show_blank());     /* the tail of display_init */
    CO_CALL(c, &wof_f.co_stage, title_sequence());

    for (;;) {
        wof_free_mission_assets();
        wof_g.opt_music_off = 0;
        wof_g.end_of_mission = 0;
        wof_g.demo_mode = 0;
        wof_g.g_026d44 = 0;
        wof_m.object_record_extra[0].draw_kind = 0;
        wof_m.object_record_extra[0].kind = 0;
        wof_campaign_reset();                                 /* orig 0x013562 */
        wof_g.game_over = 0;
        wof_g.quit_flag = 0;                                  /* clr.w */
        wof_g.g_0253c3 = 0;
        wof_g.g_0255c1 = 0;
        wof_g.g_02537f = 0;

        CO_CALL(c, &wof_f.co_stage, rank_select());
        wof_test_poke_after_rank();
        wof_load_dash_assets();
        if (!wof_g.loaded_game)
            wof_map_load();
        wof_test_poke_after_map();                            /* 0x0100AE */
        CO_CALL(c, &wof_f.co_stage, mission_briefing());
        if (wof_f.briefing_result)
            continue;

        CO_CALL(c, &wof_f.co_mission, mission());
        if (wof_f.mission_end == 2)
            continue;

        /* 0x0101C6: the mission is over. */
        wof_sound_slots_clear();
        wof_ticker_clear();
        CO_CALL(c, &wof_f.co_fade, wof_fade_out_pair());
        wof_g.g_026d54 = 0;
        wof_g.demo_was_played = (uint8_t)(wof_g.demo_mode == 1 ? 0xFF : 0);
        wof_demo_end();                                       /* orig 0x01852A */
        wof_g.outside_mission = 0xFF;
        wof_g.ticker_message = 0;
        if (!wof_g.demo_was_played) {
            wof_free_mission_assets();
            CO_CALL(c, &wof_f.co_stage, wof_high_score_screen());
        }
    }
    CO_END(c);
}

/* The sprintf("%d") the briefing and the high-score list use.  exec RawDoFmt with the few
 * formats the original really passes is all that is needed (SPEC 3.4); this is the %d of
 * it, which is the only one the briefing uses.  Returns the length. */
uint16_t wof_number(char *dst, int32_t value)
{
    char     tmp[12];
    uint16_t n = 0, out = 0;
    uint32_t v;

    if (value < 0) {
        dst[out++] = '-';
        v = (uint32_t)(-value);
    } else {
        v = (uint32_t)value;
    }
    do {
        tmp[n++] = (char)('0' + v % 10u);
        v /= 10u;
    } while (v);
    while (n)
        dst[out++] = tmp[--n];
    dst[out] = 0;
    return out;
}

/* ------------------------------------------------------------- the development entries */

/* Not part of the game.  The shell offers these only while the diagnostics overlay is up,
 * and they are outside the port's key layer on purpose: they exist so that the name entry
 * and both modes of the dialog can be looked at before M4 makes a mission reach them. */
void wof_dev_set_score(uint32_t score)
{
    wof_g.player_score = score;
}

void wof_dev_open_dialog(int mode)
{
    wof_f.dev_dialog = (uint16_t)(mode ? 2 : 1);
}

/* The player's x, y and player_on_deck, and the weapon type the menu in the hold steps, for
 * the overlay and the page test: a copy, outside the state, that nothing in the core reads. */
const int16_t *wof_dev_player(void)
{
    static int16_t out[4];

    out[0] = wof_m.player[0].x;
    out[1] = wof_m.player[0].y;
    out[2] = wof_m.player[0].on_deck;
    out[3] = wof_g.weapon_type;
    return out;
}

/* ------------------------------------------------------------------------- the pause */

void wof_request_pause(void)
{
    if (!wof_g.outside_mission)
        wof_f.pause_request = 1;
}

int wof_paused(void)
{
    return !wof_g.outside_mission && wof_g.pause_flag ? 1 : 0;
}
