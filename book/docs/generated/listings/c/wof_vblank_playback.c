/* src/input.c, lines 311-333, a part of wof_vblank (lines 259-370) */
if (wof_g.demo_mode == 1) {
    /* 0x011790: a playback takes the byte from the demo, and only while step S has set
     * 0x026D54 and run_queued_ticks' count 0x026D44 still wants one: nothing is queued
     * otherwise.  A 0xFF byte ends the playback and is queued itself; so is the entry
     * that brings the index to 0x1386. */
    uint16_t d1;

    if (!wof_g.demo_step_s || !wof_g.demo_bytes_owed) {
        wof_vblank_ticker();
        return;
    }
    wof_g.demo_bytes_owed--;
    d1 = wof_g.demo_index;
    d0 = demo_byte(d1);
    if (d0 == 0xFFu) {
        wof_g.quit_flag = 0xFF;
    } else {
        d1++;
        wof_g.demo_index = d1;
        if (d1 >= WOF_DEMO_ENTRIES)
            wof_g.quit_flag = 0xFF;
    }
    wof_g.input_byte = d0;
