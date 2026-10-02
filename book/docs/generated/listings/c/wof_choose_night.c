/* src/mission.c, lines 405-424 */
/* orig 0x0111FC choose_night - the map number of the next mission, mission_map_table
 * (0x02345F) by rank_played x 4 + mission_number, read by address as the original indexes
 * it (a word index, signed); above 6 four draws of rand_beam, of which the last one's top
 * bit decides.  main calls it only between two missions of a campaign, after mission_won
 * has counted on, so the first mission is day whatever the map (re/notes/campaign.md). */
void wof_choose_night(void)
{
    uint16_t index = (uint16_t)((uint16_t)(wof_g.rank_played << 2) + wof_g.mission_number);
    uint8_t  map   = wof_image8(0x02345Fu + (uint32_t)(int32_t)(int16_t)index);
    uint16_t d0    = 0;

    if ((int8_t)map > 6) {
        wof_rand_beam(0x0111FC);
        wof_rand_beam(0x0111FC);
        wof_rand_beam(0x0111FC);
        d0 = (uint16_t)wof_rand_beam(0x0111FC);
        d0 = (uint16_t)(((d0 << 1) | (d0 >> 15)) & 1u);
    }
    wof_g.night_flag = d0;
}
