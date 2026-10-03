/* src/tick.c, lines 353-375 */
/* orig 0x011A8C soldiers_hit - the running soldiers from x - w to x + w start dying (state 2,
 * frame 5, timer 2) with a scream; then 0x011AE2 over the same span.  The scream's sound
 * code (0x0123AC) leaves its own values in D0 and D1 and the walk goes on with them, so after
 * the first soldier hit the span is the scream's (src/sound.c). */
void wof_soldiers_hit(int16_t x, int16_t w)
{
    uint16_t d0 = (uint16_t)(x - w);
    uint16_t d1 = (uint16_t)(w + w);

    for (uint16_t n = 0; n < wof_g.soldier_count && n < 160; n++) {
        wof_soldier_t *s = &wof_m.soldier_records[n];

        if (s->state != 1)
            continue;
        if ((uint16_t)(s->x - d0) > d1)
            continue;
        s->state = 2;
        s->frame = 5;
        s->timer = 2;
        wof_sound_scream(&d0, &d1);                            /* 0x0123AC */
    }
    wof_torpedoes_hit(d0, d1);
}
