/* src/player.c, lines 20-33 */
/* A word or a long of the DATA hunk, by its original address: the tables of frames,
 * heights and offsets the player's code indexes (re/tables.toml, data_image).  An index the
 * original lets run past a table reads whatever lies behind it, which can be a global the
 * game changes (0x025E3E at attitude 9 is 0x025E50), so a byte a registered global covers is
 * read from the global and only the others from the executable's constant image. */
static uint8_t data_byte(uint32_t addr)
{
    uint8_t  b;
    uint32_t at = addr - 0x023000u;

    if (wof_global_byte(addr, &b))
        return b;
    return at < sizeof wof_tbl_data_image ? wof_tbl_data_image[at] : 0;
}
