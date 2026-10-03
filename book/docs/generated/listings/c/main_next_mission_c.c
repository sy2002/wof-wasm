/* src/front.c, lines 804-832, a part of mission (lines 753-847) */
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
