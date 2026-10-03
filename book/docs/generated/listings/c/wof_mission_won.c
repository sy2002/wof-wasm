/* src/targets.c, lines 806-835 */
/* orig 0x015694 - the map's last island neutralised: the next mission, and after the rank's
 * last mission (missions_per_rank, 0x025548) the first of the next rank, at most rank 6,
 * with balloons_on set (the promotion's balloons over the carrier and a life more at the
 * next mission's start, 0x010154); its message is appended to ticker_text over the last
 * character before the NUL (`subq.w #2` behind the NUL), the ticker shows ticker_text at
 * once, and 0x0253BC says the mission is won: the next time the weapon menu is up, main
 * goes on to the next mission (0x010132, M7's). */
void wof_mission_won(void)
{
    uint16_t end = 0;
    uint32_t format;

    wof_g.mission_number++;
    if ((int16_t)word_at(0x025548u + 2u * (uint32_t)(uint16_t)wof_g.rank_played) >=
        (int16_t)wof_g.mission_number) {
        format = 0x02399Eu;
    } else {
        wof_g.mission_number = 1;
        wof_g.rank_played++;
        if ((int16_t)wof_g.rank_played > 6)
            wof_g.rank_played = 6;
        wof_g.balloons_on = 0xFF;
        format = 0x023A5Au;
    }
    while (end < sizeof wof_g.ticker_text && wof_g.ticker_text[end])
        end++;
    wof_ticker_format(format, 0, (uint16_t)(end - 1u));
    wof_g.ticker_message = 0x02716Au;
    wof_g.g_0253bc = -1;
}
