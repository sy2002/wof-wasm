/* src/enemy.c, lines 558-568, a part of wof_aircraft_launch (lines 551-591) */
int16_t free = -1, torpedo = 0;
aircraft_t *a;

for (int16_t i = 0; i < 4; i++) {
    if (wof_m.aircraft_records[i].state == 0)
        free = i;
    if ((wof_m.aircraft_records[i].mode & 4) && wof_m.aircraft_records[i].state != 0)
        torpedo = 1;
}
if (free == -1 || (kind != 0 && torpedo))
    return;
