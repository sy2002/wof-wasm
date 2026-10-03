/* src/player.c, lines 467-485, a part of wof_guns (lines 452-493) */
if (a->relation != 3)
    continue;
dx = (int16_t)(P.x - a->x);
if (dx < 0)
    dx = (int16_t)-dx;
dy = (int16_t)(P.y - a->y);
if (dy < 0)
    dy = (int16_t)-dy;
if (dx >= 0xA0 || dy >= 0x14 || wof_g.pitch_target != 0)
    continue;
a->hit = 1;
a->burst--;
if (a->burst > 0)
    continue;
wof_burn_smoke(0, 6, (int16_t)(a->x - 0x10), (int16_t)(a->y + 0x0A));
a->health = (int16_t)(a->health - 8);
if (a->health < 0x60) {
    wof_g.player_score += 0x15E;
    a->state = 4;
