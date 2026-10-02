/* src/mission.c, lines 335-345, a part of wof_player_lost_restart (lines 310-350) */
if (wof_g.g_027452 != 0) {
    wof_clip_playfield();
    wof_draw_set_target(wof_back_vport());
    wof_rect_fill(0, 0, 0x13F, 0xA1, 0);
    wof_flip_buffers();
    do {
        CO_WAIT(c);                                   /* WaitTOF */
    } while (--wof_g.g_027452 != 0);
    do {
        CO_WAIT(c);                                   /* WaitTOF */
    } while (wof_g.g_027452 != 0);
