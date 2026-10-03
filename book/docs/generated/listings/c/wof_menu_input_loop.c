/* src/fade.c, lines 70-92, a part of wof_menu_input (lines 58-93) */
for (;;) {
    if (wof_key_available()) {
        uint16_t key = (uint16_t)(wof_key_get() & 0xFFFFu);

        if (key == 0x4C) { wof_f.menu_result = -1; CO_RETURN(c); }
        if (key == 0x4D) { wof_f.menu_result =  1; CO_RETURN(c); }
        if (key == 0x44 || key == 0x43) { wof_f.menu_result = 0; CO_RETURN(c); }
    }
    {
        int dir = wof_poll_joy_dir8();

        if (dir == 1) { wof_f.menu_result = -1; CO_RETURN(c); }
        if (dir == 5) { wof_f.menu_result =  1; CO_RETURN(c); }
    }
    if (wof_poll_fire()) { wof_f.menu_result = 0; CO_RETURN(c); }
    CO_WAIT(c);
    wof_f.menu_rounds++;
    if (wof_f.menu_timeout && (int16_t)wof_f.menu_rounds > 0x708) {
        wof_f.menu_result = 1000;
        CO_RETURN(c);
    }
}
CO_END(c);
