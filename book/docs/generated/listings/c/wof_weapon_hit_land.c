/* src/targets.c, lines 386-404, a part of wof_weapon_hit (lines 325-456) */
slot &= 0x1FFFu;
if (o->type == 0) {
    wof_g.flash_count = 5;
    wof_g.flash_colour = 0x0FFF;
}
if (slot == 0x113)
    return;
if (slot == 3) {                                              /* 0x014726 */
    wof_gtarget_t *t = wof_target_of(x);

    if (!t)
        return;
    if (o->type == 0)
        wof_g.flash_colour = 0x0F00;
    if (t->state == 0)
        return;
    t->w0e = 0xC8;
    wof_g.player_score += 0xC8;
    target_release(t);
