/* src/sound.c, lines 431-457, a part of wof_audio_irq (lines 415-459) */
    for (int c = 0; c < 4; c++) {
        uint16_t bit = (uint16_t)(1u << (c + 7));

        if (!(d0 & bit))
            continue;
        if (CHAN(c).sample != 0) {
            if (CHAN(c).count < 0)
                goto keep;
            CHAN(c).count--;
            if (CHAN(c).count >= 0)
                goto keep;
        }
        if (c == 2)                                               /* 0x01EC0C */
            wof_g.sound_flags[2] = 0;
        d4 = (uint16_t)(d4 | bit);
        wof_paula_write(WOF_INTENA, d4);
        wof_paula_write(WOF_DMACON, (uint16_t)(1u << c));
        CHAN(c).target = -1;
        wof_paula_write(AUD(c, AUDVOL), 0);
        CHAN(c).volume = 0;
        CHAN(c).stamp  = wof_g.sound_vblanks;
        CHAN(c).sample = 0;
keep:
        d4 = (uint16_t)(d4 | bit);
    }
    if (d4)
        wof_paula_write(WOF_INTREQ, d4);
