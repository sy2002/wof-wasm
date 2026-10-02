/* src/player.c, lines 508-533 */
/* orig 0x01B92E - the hook: at 600 or more of airspeed and with 0x025A9C clear, the hook
 * 0x18 behind the aircraft within 8 of one of the four cables, 0x38 apart from
 * player_start_x + 0x46, catches it: state 7. */
static void hook(void)
{
    int16_t hook_x;

    if (wof_g.airspeed < 0x258 || wof_g.g_025a9c != 0)
        return;
    hook_x = P.x;
    if (P.facing == -1)
        hook_x = (int16_t)(hook_x + 0x18);
    else
        hook_x = (int16_t)(hook_x - 0x18);
    wof_g.g_02540c = (int16_t)(wof_g.player_start_x + 0x46);
    for (int16_t i = 0; i < 4; i++) {
        if (hook_x >= (int16_t)(wof_g.g_02540c - 8) && hook_x <= (int16_t)(wof_g.g_02540c + 8)) {
            P.on_deck = 7;
            wof_g.g_025a9e = -1;
            wof_g.g_02535f = 4;
            wof_g.g_026d3a = wof_g.g_02540c;
            return;
        }
        wof_g.g_02540c = (int16_t)(wof_g.g_02540c + 0x38);
    }
}
