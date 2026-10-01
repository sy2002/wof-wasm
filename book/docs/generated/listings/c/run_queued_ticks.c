/* src/front.c, lines 735-751 */
/* orig 0x0114D8 run_queued_ticks - one tick per queued byte.  In a demo, played back or
 * recorded, it first waits VBlank by VBlank until vblank_server has taken the two bytes
 * 0x026D44 asks for, so a demo's pass has two ticks (re/notes/demo.md). */
static wof_co_t run_queued_ticks(void)
{
    wof_ctx_t *c = &wof_f.co_ticks;

    CO_BEGIN(c);
    while (wof_g.demo_bytes_owed)                                    /* 0x0114E0 */
        CO_CALL(c, &wof_f.co_vblank, wof_wait_next_vblank());
    if ((int8_t)wof_g.pause_flag < 0)
        CO_RETURN(c);
    while ((int16_t)wof_g.input_queue_count > 0)
        CO_CALL(c, &wof_f.co_tick, wof_logic_tick());
    wof_g.demo_bytes_owed = (int16_t)(wof_g.demo_mode != 0 ? 2 : 0);
    CO_END(c);
}
