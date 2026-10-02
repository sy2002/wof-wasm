/* src/screen.c, lines 404-413 */
/* orig 0x01876E cop_set_split_line - the back list's split WAIT rewritten in place, at the
 * row the pass computed (clamped to 162 by the caller). */
void wof_cop_set_split_line(int16_t row)
{
    wof_vport_t *v = wof_back_vport();

    wof_trace_add("split_line", row, wof_f.back_view, 0, 0, 0, 0);
    if (v)
        v->split_line = (uint16_t)row;
}
