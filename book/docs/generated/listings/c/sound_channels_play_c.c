/* src/sound.c, lines 86-108, a part of wof_sound_channels (lines 70-110) */
if (!a3) {                                                /* 0x0120A4 */
    if (a2->playing != 0) {
        channel_stop(c);
        channel_stop(c);
        channel_stop(c);
        a2->playing = 0;
    }
    continue;
}
if (a3->sample == a2->playing) {                          /* 0x0120C6 */
    uint32_t pv = ((uint32_t)a3->period << 16) | a3->volume;

    if (pv == a2->playing_pv)
        continue;
    a2->playing_pv = pv;
    channel_adjust(c, a3->period, a3->volume);
    continue;
}
a2->playing    = a3->sample;                              /* 0x0120F0 */
a2->playing_pv = ((uint32_t)a3->period << 16) | a3->volume;
for (int k = 0; k < 3; k++)
    channel_play(a3->sample, a3->length, (uint16_t)c, a3->period, a3->volume,
                 (uint16_t)a3->repeat);
