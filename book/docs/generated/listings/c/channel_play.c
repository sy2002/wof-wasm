/* src/sound.c, lines 367-400 */
/* orig 0x01EA28 - a sample for channel c (D1), to start at the VBlank after next: with no
 * sample nothing; a busy channel stopped first (0x01EB2E); its request cleared and its
 * interrupt on; the record takes the sample, the length in words, the period, the volume
 * and the repeat count, and waits.  A request for channel 6 would hand channel 2 over to
 * the music first (0x01E9F4); no caller makes one. */
static void channel_play(uint32_t sample, uint32_t length, uint16_t c, uint16_t period,
                         uint16_t volume, uint16_t repeat)
{
    uint16_t bit;

    if (sample == 0)
        return;
    if (c == 6) {
        /* Dead (read): the one caller the game reaches, sound_channels, asks for its pair
         * index, 0 to 3 (0x0120F8, D6), and the other, sound_play_rate (0x01E992), has no
         * caller.  0x01E9F4 would hand channel 2 over from the music, with a Delay of ten
         * VBlanks; channel2_from_music (0x01EA18) would give it back and has no caller. */
        WOF_STANDIN("M8 STAND-IN: 0x01EA3A, a sample asked for on channel 6, which no caller does");
        c = 2;
    }
    c &= 3;
    if (CHAN(c).sample != 0)                                      /* 0x01EB2E */
        channel_stop(c);
    bit = (uint16_t)(1u << (c + 7));
    wof_paula_write(WOF_INTREQ, bit);
    wof_paula_write(WOF_INTENA, (uint16_t)(bit | 0x8000u));
    CHAN(c).words   = (uint16_t)(length >> 1);
    CHAN(c).period  = period;
    CHAN(c).volume  = (uint32_t)volume << 16;
    CHAN(c).repeat  = (int16_t)repeat;
    CHAN(c).sample  = sample;
    CHAN(c).target  = -1;
    CHAN(c).pending = 1;
}
