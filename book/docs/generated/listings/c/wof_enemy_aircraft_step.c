/* src/enemy.c, lines 640-679 */
/* orig 0x01E7D6 enemy_aircraft_step - every record in use: its relation and the order, then
 * by its state 1 nothing, 2 its flight (and +0x24 at least 0x21 unless a torpedo plane),
 * 4 its fall, 8 nothing, 0x10 its burning; then, whatever the state has become, its
 * speed, its motion unless burning, and its frame. */
void wof_enemy_aircraft_step(void)
{
    wof_g.g_027e66 = 0;
    for (int16_t i = 0; i < 4; i++) {
        aircraft_t *a = &wof_m.aircraft_records[i];

        if (a->state == 0)
            continue;
        aircraft_relation(a);
        aircraft_order();
        switch (a->state) {
        case 1:
            aircraft_idle(a);
            break;
        case 2:
            aircraft_fly(a);
            if (!(a->mode & 4) && a->want_y < 0x21)
                a->want_y = 0x21;
            break;
        case 4:
            aircraft_falling(a);
            break;
        case 8:
            break;
        case 0x10:
            aircraft_burning(a);
            break;
        default:
            break;
        }
        aircraft_speed(a);
        if (a->state != 0x10)
            aircraft_motion(a);
        wof_aircraft_frame_index(a);
    }
}
