/* src/music.c, lines 522-544 */
/* orig songplay+0x09BC _OpenTimerInt - command 0: the song idle and no track started;
 * ciaa.resource opened and its timer A vector given an Interrupt node with SongInt; timer A
 * started, counting on from whatever it holds; SongIntHandler at 0x70 in place of the
 * vector found there, which is kept; the audio interrupts on.  Its write to INTREQR does
 * nothing. */
static void open_timer_int(void)
{
    VARS.play_state  = 0;
    VARS.track_state = 0;
    HEAD.ciaa_base   = 1;                              /* OpenResource("ciaa.resource") */
    HEAD.node_type   = NT_INTERRUPT;
    HEAD.node_pri    = 0;
    HEAD.node_name   = 1;                              /* timer_name */
    HEAD.node_data   = 0;
    HEAD.node_code   = 1;                              /* SongInt */
    wof_s.cia.vector = 1;                              /* AddICRVector(0, timer_node) */
    wof_cia_write(WOF_CIAA_CRA, 0x01);
    wof_paula_write(WOF_INTENA, 0x0780);
    HEAD.saved_level4_vector = wof_s.cia.level4;
    wof_s.cia.level4 = WOF_L4_SONGINT;
    wof_paula_write(INTREQR, 0x0780);
    wof_paula_write(WOF_INTENA, 0x8780);
}
