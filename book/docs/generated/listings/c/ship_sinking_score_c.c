/* src/tick.c, lines 543-552, a part of ship_sinking (lines 519-584) */
} else if (s->w14 == 10) {
    wof_g.player_score += (uint32_t)(int32_t)s->w12;
    wof_ship_sunk_message(s);
    /* subq.b #1 then bgt: the signed result before its byte wraps, so 0x80 is not > 0 */
    if ((int8_t)wof_g.ships_left-- > 1 || wof_g.islands_left != 0) {
        if (wof_g.ticker_message == 0)                    /* 0x01555A: ticker_text */
            wof_g.ticker_message = 0x02716Au;
        return;
    }
    wof_mission_won();
