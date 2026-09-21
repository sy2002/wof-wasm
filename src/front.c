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

/* orig 0x0123DC music_start.  The player is a second executable the original loads with
 * LoadSeg; porting it is M8.  Until then a call is recorded with the VBlank it happened
 * at, which is what re/notes/frontend.md's timetable is made of, and nothing plays. */
void wof_music_start(const char *file, uint16_t song)
{
    (void)file;
    wof_trace_add("music_start", song, 0, 0, 0, file, 32);
    if (wof_f.music_count < WOF_MUSIC_LOG) {
        wof_f.music_song[wof_f.music_count]   = song;
        wof_f.music_vblank[wof_f.music_count] = wof_s.vblanks;
        wof_f.music_count++;
    }
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
    wof_music_start("wofsongs", 2);
    CO_CALL(c, &wof_f.co_inner, story_screen());
    wof_music_start("wofsongs", 1);
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
    wof_music_start("wofsongs", 4);
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
        wof_text_draw_line(v, number, wof_number(number, wof_g.briefing_number_1));
        wof_gfx_move(v, 0x154, 0x83);
        wof_text_draw_line(v, number, wof_number(number, wof_g.briefing_number_2));
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
    wof_f.music_count    = 0;
    wof_f.mission_count  = 0;
    wof_display_init();
}

/* ----------------------------------------------------------------- the mission (M4) */

/* orig 0x01CCF6 ingame_keys - M4 PART 2 STAND-IN: ingame_keys.  The original's command keys
 * are part 2's.  What is kept is what its path without a command does to the key buffer:
 * every waiting key is taken out, and the last one is remembered in last_key.  While the
 * tick is a stand-in nobody can fly, so the mission needs an end of its own: raw 0x12, the
 * E key by position, ends it the way the original's Control-R does not and quit_flag does,
 * so that the high scores and the rank selection stay reachable.  No script of the
 * headless original presses a key during a mission, and every other key is a stand-in hit. */
static void ingame_keys(void)
{
    wof_g.last_key = 0;
    while (wof_key_available()) {
        uint32_t key = wof_key_get() & 0x7FFFFFFFu;

        wof_g.last_key = key;
        if ((key & 0xFFu) == 0x12u && !((key >> 16) & 0x0008u)) {
            /* M4 PART 2 STAND-IN: the mission's end, on KeyE, while the tick is a stand-in. */
            wof_g.quit_flag = 0xFF;
            continue;
        }
        WOF_STANDIN("M4 PART 2 STAND-IN: ingame_keys, a key during a mission");
    }
}

/* M4 PART 2 STAND-IN: the tick.  logic_tick (orig 0x011386) is part 2's; this pops the
 * tick's input byte, so that the queue's arithmetic stays the original's, and does nothing
 * else.  In test builds a comparison can tell it how many VBlanks the original's tick
 * waited (the restart spins on WaitTOF inside the tick), and it then waits as many, so that
 * a replayed schedule delivers them at the same point; the release build never waits. */
static wof_co_t tick_standin(void)
{
    wof_ctx_t *c = &wof_f.co_tick;

    CO_BEGIN(c);
    if (!wof_g.pause_flag)
        wof_input_queue_pop();
    wof_f.tick_waits = wof_test_tick_waits(wof_f.ticks_run);
    wof_f.ticks_run++;
    while (wof_f.tick_waits) {
        wof_f.tick_waits--;
        CO_WAIT(c);
    }
    wof_trace_add("tick", (int32_t)wof_f.ticks_run, 0, 0, 0, 0, 0);
    wof_test_tick_end(wof_f.ticks_run - 1u);
    CO_END(c);
}

/* orig 0x0114D8 run_queued_ticks - one tick per queued byte.  In demo playback and
 * recording it first spins until the server has taken two bytes (M7). */
static wof_co_t run_queued_ticks(void)
{
    wof_ctx_t *c = &wof_f.co_ticks;

    CO_BEGIN(c);
    if (wof_g.g_026d44)
        WOF_STANDIN("M7 STAND-IN: run_queued_ticks, demo playback and recording");
    if ((int8_t)wof_g.pause_flag < 0)
        CO_RETURN(c);
    while ((int16_t)wof_g.input_queue_count > 0)
        CO_CALL(c, &wof_f.co_tick, tick_standin());
    wof_g.g_026d44 = (int16_t)(wof_g.demo_mode != 0 ? 2 : 0);
    CO_END(c);
}

/* The setup after the briefing and the inner loop, main from 0x0100B6 to 0x0101C2.  It
 * returns with wof_f.mission_end saying how the loop was left: 1 for quit_flag, which goes
 * on to the high scores, 2 for end_of_mission, which goes straight back to the outer loop. */
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
        wof_mission_reset_tables();                           /* orig 0x0135A8 */
        wof_player_restart_state();                           /* orig 0x013684 */
        wof_g.loaded_game = 0;
        wof_g.pause_flag = 0;
        wof_g.g_026d3c = 0;
        wof_g.tick_input = 0;
    }
    wof_g.outside_mission = 0;
    wof_g.loaded_game = 0;
    CO_CALL(c, &wof_f.co_tick, tick_standin());               /* main's own logic_tick */
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
        ingame_keys();
        if (wof_g.quit_flag)
            break;
        if (wof_g.pause_flag) {
            CO_CALL(c, &wof_f.co_vblank, wof_wait_vblank());  /* wait_next_vblank */
            continue;
        }
        if (wof_g.g_025364 && wof_g.g_0253bc) {
            /* 0x010132: the mission is won and the next one follows. */
            WOF_STANDIN("M4 PART 2 STAND-IN: the next mission of a campaign");
            wof_g.quit_flag = 0xFF;
            break;
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
        CO_CALL(c, &wof_f.co_stage, mission_briefing());
        if (wof_f.briefing_result)
            continue;

        CO_CALL(c, &wof_f.co_mission, mission());
        if (wof_f.mission_end == 2)
            continue;

        /* 0x0101C6: the mission is over. */
        wof_ticker_clear();                                   /* sub_011f4e is M8's */
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
