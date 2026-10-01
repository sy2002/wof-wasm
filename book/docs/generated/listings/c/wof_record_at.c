/* src/player.c, lines 68-81 */
/* orig 0x01C982 - the map record under a world x: x / 8 words into the list, the last
 * record for anything at or beyond the end, record 0 for x below zero. */
uint32_t wof_record_at(int16_t x)
{
    uint32_t at;

    if (x < 0)
        x = 0;
    at = (uint32_t)(uint16_t)(int16_t)(((int32_t)x / 8) * 2);   /* asl.w, then ext.l */
    at = (uint32_t)(int32_t)(int16_t)(uint16_t)at;
    if (at >= wof_m.map_records_end[0].off)
        at = wof_m.map_records_end[0].off - 2u;
    return at;
}
