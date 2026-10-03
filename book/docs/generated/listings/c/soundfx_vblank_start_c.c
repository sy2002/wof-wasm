/* src/sound.c, lines 475-486, a part of wof_soundfx_vblank (lines 461-516) */
if (r->pending != 0 && (int32_t)(wof_g.sound_vblanks - r->stamp) >= 2) {
    if (wof_g.sound_flags[1] != 0 && c == 2) {
        wof_g.sound_flags[0] = 0xFF;
        wof_g.sound_flags[2] = 0xFF;
    }
    wof_paula_lc(c, r->sample);
    wof_paula_write(AUD(c, AUDLEN), r->words);
    wof_paula_write(AUD(c, AUDPER), r->period);
    wof_paula_write(AUD(c, AUDVOL), (uint16_t)(r->volume >> 16));
    r->count = r->repeat;
    wof_g.sound_dmacon = (uint16_t)(wof_g.sound_dmacon | (1u << c));
    r->pending = 0;
