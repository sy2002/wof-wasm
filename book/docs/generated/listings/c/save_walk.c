/* src/dialog.c, lines 185-210 */
/* orig 0x015EC2 - the walker of the saved game, for the write and the read alike: the
 * memory from object_records up to target_records_4, map_length, the map's record list,
 * the gun list of every ship whose +4 and +0x12 are set, and the four tables of map_scan,
 * each as long as its count says.  After the map it sets map_extent and map_records_end
 * from map_length, the latter to the list's end where map_load leaves it a word before, so
 * a save changes the running game there. */
static void save_walk(void (*put)(uint32_t addr, uint32_t len, uint16_t flag))
{
    put(0x024CAEu, 0x0254F8u - 0x024CAEu, 0);
    put(0x0253C6u, 2u, 0);
    put(0x024628u, (uint32_t)(int32_t)(int16_t)wof_g.map_length, 1);      /* ext.l */
    wof_g.map_extent = (uint16_t)(wof_g.map_length << 2);                  /* asl.w #2 */
    wof_m.map_records_end[0].off = (uint32_t)(int32_t)(int16_t)wof_g.map_length;
    for (uint32_t i = 0; i < 5u; i++) {
        const wof_ship_t *ship = &wof_m.ship_records[i];

        if (ship->present != 0 && ship->w12 != 0)                         /* +4, +0x12 */
            put(0x025460u + 0x1Eu * i + 6u,
                (uint16_t)((uint32_t)(uint16_t)ship->gun_count * 14u), 1); /* mulu.w */
    }
    save_nothing();
    put(0x025504u, (uint16_t)((uint32_t)(uint16_t)(int16_t)(int8_t)wof_g.target_count_f * 14u), 1);
    put(0x025500u, (uint16_t)(wof_g.soldier_count << 3), 1);
    put(0x0254FCu, (uint16_t)((uint16_t)(int16_t)(int8_t)wof_g.target_count_3 << 4), 1);
    put(0x0254F8u, (uint16_t)((uint16_t)(int16_t)(int8_t)wof_g.target_count_4 << 4), 1);
}
