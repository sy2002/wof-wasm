/* src/objects.c, lines 140-154 */
/* orig 0x0107F2 object_draw_first - the other weapon, if any is left: 0x026F8A 0x14 for the
 * debug view behind 0x02536D, then the first free object record (of the fifteen, not the
 * extra one) goes to the launch at 0x01088E; with none free nothing is dropped. */
static void object_draw_first(void)
{
    wof_g.g_026f8a = 0x14;
    if (wof_g.weapon_count == 0)
        return;
    for (int i = 0; i < 15; i++) {
        if (wof_m.object_records[i].kind == 0) {
            launch(&wof_m.object_records[i]);
            return;
        }
    }
}
