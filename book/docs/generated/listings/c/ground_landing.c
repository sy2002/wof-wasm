/* src/player.c, lines 568-580, a part of ground (lines 554-589) */
if (deck) {
    if (P.facing == -1 && wof_g.landing_stall) {
        P.on_deck = 1;
        wof_g.g_025a9e = -1;
        wof_sound_screech();                                  /* 0x012380 */
        P.y = (int16_t)(wof_ground_height(at) + wof_wheel_height());
    } else {
        P.speed_y = (int16_t)-P.speed_y;
        wof_g.pitch_target = (int16_t)-wof_g.pitch_target;
        P.y = (int16_t)(P.y + 6);
        wof_sound_screech();                                  /* 0x012380 */
    }
    return;
