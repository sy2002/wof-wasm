/* src/screen.c, lines 449-486 */
/* The play screen's colours per row of one viewport (re/notes/display.md): the playfield
 * shows table 1 above its split line and, below it, table 2 wherever table 2 differs from
 * table 1 (the copper moves only those); COLOR01 above the split is what flip_buffers poked
 * into the list.  The ticker takes its ten-line ramp on COLOR01 when its view's list has
 * one.  Returns the number of rows from `row` on that share the colours it fills in. */
static uint16_t play_colours(const wof_vport_t *v, uint16_t row, uint16_t *colours)
{
    uint8_t  view  = wof_f.front_view;
    uint16_t rows  = v->disp_rows;
    uint16_t run   = (uint16_t)(rows - row);

    for (uint32_t i = 0; i < WOF_PAL_COLOURS; i++)
        colours[i] = v->colours[i];

    if (v == VP(WOF_VP_TICKER)) {
        if (wof_f.ticker_ramp[view]) {
            colours[1] = row < 10 ? wof_ticker_ramp(row) : wof_ticker_ramp(9);
            run = row < 9 ? 1 : (uint16_t)(rows - row);
        }
        return run;
    }
    if (v != VP(wof_f.view_first[view]))
        return run;                         /* the dashboard: its own table, no poke, no split */
    if (wof_f.colour1_poked[view])
        colours[1] = wof_f.colour1[view];
    if (v->has_colours2 && v->split_on) {
        uint16_t split = v->split_line;

        if (row >= split) {
            for (uint32_t i = 0; i < WOF_PAL_COLOURS; i++)
                if (v->colours2[i] != v->colours[i])
                    colours[i] = v->colours2[i];
        } else if (split < rows) {
            run = (uint16_t)(split - row);
        }
    }
    return run;
}
