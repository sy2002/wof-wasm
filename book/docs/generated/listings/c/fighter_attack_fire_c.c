/* src/enemy.c, lines 362-374, a part of fighter_attack (lines 334-376) */
if (on && a->order == 1 && dy < 8 && a->attitude == 0 && a->distance < 0xA0 && same &&
    (int16_t)(dx ^ P.facing) < 0) {
    a->firing = 1;
    if (!wof_g.g_026f72 && a->y == P.y && wof_g.g_027346) {
        P.w10--;
        if (P.w10 <= 0) {
            P.oil = (int16_t)(P.oil - 8);
            P.fuel = (int16_t)(P.fuel - (int16_t)wof_rand_mod(0x20));
            P.w10 = (int16_t)(wof_rand_mod(5) + 6);
        }
    }
} else {
    a->firing = 0;
