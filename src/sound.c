/* The sound effects engine (M8, re/notes/sound.md), in the original's address order: the
 * slots the tick fills (0x011F4E to 0x0123DA) and the channel layer under them with its
 * interrupt handler and its VBlank server (0x01E8B8 to 0x01ED78).
 *
 * Eight slots of 0x18 bytes at 0x027368, two per audio channel, name what should be
 * playing: the tick switches a slot on and off and moves its volume and period, and
 * sound_channels gives each channel the first of its two slots that is on.  A channel's
 * record of 0x1E bytes at 0x027E6E holds what it was asked to play; soundfx_vblank starts
 * it at the next VBlank but one after the channel last stopped, and audio_irq counts its
 * cycles down and stops it (src/audio.c raises the interrupts).
 *
 * The custom registers the original writes go to the Paula model (wof_paula_write); a
 * sample pointer is a sound handle (WOF_SOUND).  The periods, volumes, lengths and repeat
 * counts the engine hands its slots are the immediates of its instructions, read out of the
 * executable at build time (re/tables.toml). */
#include "wof.h"
#include "gen/tables.h"

#define SLOT(i)    (wof_m.sound_slots[i])
#define CHAN(c)    (wof_m.sound_channels[c])
#define AUD(c, r)  ((uint16_t)(0x0A0u + ((unsigned)(c) << 4) + (r)))
#define AUDLEN 0x4
#define AUDPER 0x6
#define AUDVOL 0x8

/* st.b on the first byte of a slot's word: the high byte set, the low one kept. */
static void slot_on(int i)
{
    SLOT(i).active = (uint16_t)(SLOT(i).active | 0xFF00u);
}

static void channel_stop(int c);
static void channel_adjust(int c, uint16_t period, uint16_t volume);
static void channel_play(uint32_t sample, uint32_t length, uint16_t c, uint16_t period,
                         uint16_t volume, uint16_t repeat);

/* ------------------------------------------------------------ the slots, 0x011F4E on */

/* orig 0x011F4E sound_slots_clear - every slot off, then the channels follow. */
void wof_sound_slots_clear(void)
{
    for (int i = 0; i < 8; i++)
        SLOT(i).active = 0;
    wof_sound_channels();
}

/* orig 0x011F76 - slots 0 to 6 as sounds_load leaves them: the player's guns and engine
 * (channel 0), an enemy's guns and engine (1), a bomb's burst and a splash (2), the guns of
 * the ground (3), each with its sample, length, period, volume and repeat count, all off.
 * Slot 7 is filled where it is switched on. */
void wof_sound_slots_init(void)
{
    static const uint8_t length_of[7] = { 0, 2, 0, 2, 1, 3, 0 };   /* sound_length's index */
    const uint32_t sample[7] = {
        wof_m.sound_machinegun[0].p, wof_m.sound_engine[0].p, wof_m.sound_machinegun[0].p,
        wof_m.sound_engine[0].p, wof_m.sound_boom[0].p, wof_m.sound_splash[0].p,
        wof_m.sound_machinegun[0].p,
    };

    for (int i = 0; i < 7; i++) {
        SLOT(i).sample = sample[i];
        SLOT(i).length = wof_g.sound_length[length_of[i]];
        SLOT(i).period = wof_tbl_slot_periods[i];
        SLOT(i).volume = wof_tbl_slot_volumes[i];
        SLOT(i).repeat = (int16_t)wof_tbl_slot_repeats[i];
        SLOT(i).active = 0;
    }
}

/* orig 0x012066 sound_channels - for each channel the first of its two slots that is on and
 * has a sample: the same sample as it plays is only adjusted when the period or the volume
 * moved, another one is started, three times over; with neither, or paused, or with the
 * music off, a playing channel is stopped, three times over. */
void wof_sound_channels(void)
{
    for (int c = 0; c < 4; c++) {
        wof_sound_slot_t *a2 = &SLOT(2 * c);
        wof_sound_slot_t *a3 = 0;

        if (!wof_g.pause_flag && !wof_g.opt_music_off) {
            if (a2->sample != 0 && a2->active != 0)
                a3 = a2;
            else if (SLOT(2 * c + 1).sample != 0 && SLOT(2 * c + 1).active != 0)
                a3 = &SLOT(2 * c + 1);
        }
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
    }
}

/* 0x0122CE: the loudness of an enemy aircraft at a distance, 0 beyond 0x2CF. */
static uint16_t distance_volume(uint16_t d0)
{
    d0 = (uint16_t)(d0 >> 4);
    if (d0 > 0x2C)
        return 0;
    d0 = d0 > 5 ? (uint16_t)(d0 + 0x14) : (uint16_t)(d0 << 2);
    return (uint16_t)(0x40u - d0);
}

/* 0x0122F6: the loudness of something at a distance from the aircraft, 0 beyond 0x81F. */
static uint16_t near_volume(uint16_t d0)
{
    d0 = (uint16_t)(d0 >> 5);
    if (d0 > 0x40)
        return 0;
    return (uint16_t)(0x40u - d0);
}

/* 0x012306: the loudness of something at world x and height 0x14, by its distance from the
 * aircraft; D1 is left holding the height's part of the distance. */
static uint16_t heard_at(uint16_t d0, uint16_t *d1)
{
    uint16_t a = (uint16_t)(d0 - (uint16_t)wof_m.player[0].x);
    uint16_t b = (uint16_t)(0x14u - (uint16_t)wof_m.player[0].y);

    if ((int16_t)a < 0)
        a = (uint16_t)-(int16_t)a;
    if ((int16_t)b < 0)
        b = (uint16_t)-(int16_t)b;
    *d1 = b;
    return near_volume((uint16_t)(a + b));
}

/* orig 0x012132 engine_sound - nothing while paused or with the music off.  The engine
 * (slot 1): the volume 0x02542C eases towards 0x025428 by one up and two down, and while it
 * is not zero the slot is on and the period 0x02542E eases towards what pitch_target,
 * 0x02542A and the height ask for, by twenty up and ten down; the comparisons are unsigned.
 * The guns (slot 0) sound while they fire.  The nearest enemy aircraft that flies (state 1
 * or 2) gives slot 3 its loudness by its distance, and any enemy that fires switches slot 2
 * on.  The lift moving (0x025394 2 or 3) grinds in slot 7 and silences slot 6; aboard the
 * carrier (1) the sea sounds in slot 5, and otherwise slot 5 is a splash again.  The guns of
 * the ground (0x027164) sound in slot 6 at the loudness draw_world found and silence slot 7. */
void wof_engine_sound(void)
{
    uint16_t d0, d1, nearest;
    int16_t  fired;

    if (wof_g.pause_flag || wof_g.opt_music_off)
        return;
    SLOT(1).active = 0;
    d0 = (uint16_t)wof_g.engine_volume;
    d1 = (uint16_t)wof_g.engine_volume_target;
    if (d1 != d0) {
        if (d1 > d0) {
            d0++;
        } else {
            d0 = (uint16_t)(d0 - 2);
            if (!(d1 <= d0))
                d0 = d1;
        }
    }
    wof_g.engine_volume = (int16_t)d0;
    SLOT(1).volume = d0;
    if (d0 != 0) {
        slot_on(1);
        d0 = (uint16_t)wof_g.engine_period;
        d1 = (uint16_t)((int16_t)(wof_g.pitch_target >> 7) + wof_g.engine_period_base +
                        (int16_t)(wof_m.player[0].y >> 4));
        if (d1 != d0) {
            if (d1 > d0) {
                d0 = (uint16_t)(d0 + 0x14);
                if (!(d1 > d0))
                    d0 = d1;
            } else {
                d0 = (uint16_t)(d0 - 0x0A);
                if (!(d1 <= d0))
                    d0 = d1;
            }
        }
        wof_g.engine_period = (int16_t)d0;
        SLOT(1).period = d0;
    }

    SLOT(0).active = (uint16_t)wof_g.g_02536a;          /* guns_firing */                 /* 0x0121C0 */
    nearest = 0xFFFF;
    fired   = 0;
    for (int i = 0; i < 4; i++) {
        const wof_aircraft_t *a = &wof_m.aircraft_records[i];
        uint16_t dx, dy;

        if (a->state == 0 || a->state > 2)                        /* subq.w #2; bgt */
            continue;
        dx = (uint16_t)(a->x - wof_m.player[0].x);
        if ((int16_t)dx < 0)
            dx = (uint16_t)-(int16_t)dx;
        dy = (uint16_t)(a->y - wof_m.player[0].y);
        if ((int16_t)dy < 0)
            dy = (uint16_t)-(int16_t)dy;
        dx = (uint16_t)(dx + dy);
        if (!(nearest <= dx))
            nearest = dx;
        fired = (int16_t)(fired | a->firing);
    }
    SLOT(3).active = 0;
    d0 = distance_volume(nearest);
    if (d0 != 0) {
        SLOT(3).volume = d0;
        slot_on(3);
    }
    SLOT(2).active = (uint16_t)fired;

    if (wof_g.g_025394 == 2 || wof_g.g_025394 == 3) {             /* 0x01223E */
        SLOT(7).sample = wof_m.sound_grind[0].p;
        SLOT(7).length = wof_g.sound_length[7];
        SLOT(7).period = wof_tbl_slot_lift[0];
        SLOT(7).volume = wof_tbl_slot_lift[1];
        SLOT(7).repeat = (int16_t)wof_tbl_slot_lift[2];
        SLOT(6).active = 0;
        slot_on(7);
        SLOT(5).active = 0;
    } else if (wof_g.g_025394 == 1) {                             /* 0x012276 */
        SLOT(5).sample = wof_m.sound_splash[0].p;
        SLOT(5).length = wof_g.sound_length[3];
        SLOT(5).period = wof_tbl_slot_aboard[0];
        SLOT(5).volume = wof_tbl_slot_aboard[1];
        SLOT(5).repeat = (int16_t)wof_tbl_slot_aboard[2];
        slot_on(5);
        goto ground_guns;
    }
    SLOT(5).sample = wof_m.sound_splash[0].p;                     /* 0x01229C */
    SLOT(5).length = wof_g.sound_length[3];
    SLOT(5).period = wof_tbl_slot_splash[0];
    SLOT(5).repeat = (int16_t)wof_tbl_slot_splash[1];
ground_guns:                                                      /* 0x0122B4 */
    SLOT(6).active = wof_g.g_027164;
    if (wof_g.g_027164 != 0)
        SLOT(7).active = 0;
    SLOT(6).volume = (uint16_t)wof_g.g_027166;
}

/* orig 0x012324 - a burst at world x (slot 4, channel 2), started again even where one
 * plays, at the loudness of its distance; nothing before the sound is loaded.  Returns D0 as
 * it leaves it, the loudness or else x, which 0x010D8E hands on to 0x01233E. */
uint16_t wof_sound_boom(int16_t x)
{
    uint16_t d1;

    if (wof_m.sound_boom[0].p == 0)
        return (uint16_t)x;
    slot_on(4);
    SLOT(4).playing = 0;
    SLOT(4).volume  = heard_at((uint16_t)x, &d1);
    return SLOT(4).volume;
}

/* orig 0x01233E - a splash at world x (slot 5, channel 2), the burst's slot off. */
void wof_sound_splash(int16_t x)
{
    uint16_t d1;

    SLOT(4).active = 0;
    slot_on(5);
    SLOT(4).playing = 0;
    SLOT(5).volume  = heard_at((uint16_t)x, &d1);
}

/* orig 0x012354 - the lift's clang (slot 7, channel 3), once.  The length is written as a
 * word into the low half of the slot's long. */
void wof_sound_clang(void)
{
    SLOT(7).sample = wof_m.sound_clang[0].p;
    SLOT(7).length = (SLOT(7).length & 0xFFFF0000u) | wof_tbl_slot_clang[0];
    SLOT(7).period = wof_tbl_slot_clang[1];
    SLOT(7).volume = wof_tbl_slot_clang[2];
    SLOT(7).repeat = (int16_t)wof_tbl_slot_clang[3];
    SLOT(6).active = 0;
    slot_on(7);
    SLOT(6).playing = 0;
}

/* orig 0x012380 - the wheels' screech on the deck (slot 7), once. */
void wof_sound_screech(void)
{
    SLOT(7).sample = wof_m.sound_screech[0].p;
    SLOT(7).length = (SLOT(7).length & 0xFFFF0000u) | wof_tbl_slot_screech[0];
    SLOT(7).period = wof_tbl_slot_screech[1];
    SLOT(7).volume = wof_tbl_slot_screech[2];
    SLOT(7).repeat = (int16_t)wof_tbl_slot_screech[3];
    SLOT(6).active = 0;
    slot_on(7);
    SLOT(6).playing = 0;
}

/* orig 0x0123AC - a soldier's scream (slot 7), once, at half the loudness of the soldier's
 * distance, D0 his x.  D0 and D1 come back as the arithmetic leaves them, which
 * soldiers_hit goes on with (src/tick.c). */
void wof_sound_scream(uint16_t *d0, uint16_t *d1)
{
    SLOT(7).sample = wof_m.sound_scream[0].p;
    SLOT(7).length = (SLOT(7).length & 0xFFFF0000u) | wof_tbl_slot_scream[0];
    SLOT(7).period = wof_tbl_slot_scream[1];
    *d0 = (uint16_t)(heard_at(*d0, d1) >> 1);
    SLOT(7).volume = *d0;
    SLOT(7).repeat = (int16_t)wof_tbl_slot_scream_repeat[0];
    SLOT(6).active = 0;
    slot_on(7);
    SLOT(6).playing = 0;
}

/* --------------------------------------------------- the channels, 0x01E8B8 on */

/* orig 0x01E8B8 sound_init - once: the four channel records free, every audio interrupt off
 * and every request cleared, the channels' DMA off, ADKCON's modulation bits clear, audio_irq
 * at the level-4 autovector, the four interrupts on, and soundfx_vblank added as a VBlank
 * server at priority 30. */
void wof_sound_init(void)
{
    if (wof_g.sound_installed)
        return;
    wof_g.sound_vblanks = 0;
    for (int c = 0; c < 4; c++) {
        CHAN(c).sample  = 0;
        CHAN(c).pending = 0;
        CHAN(c).target  = -1;
        CHAN(c).stamp   = 0;
    }
    wof_paula_write(WOF_INTENA, 0x0780);
    wof_paula_write(WOF_DMACON, 0x000F);
    /* 0x01E8F6: ADKCON 0x00FF, no modulation; the model has none.  0x01E8FC: the vector at
     * 0x70 kept in 0x027EE6 and audio_irq put there: the port calls it (src/audio.c). */
    wof_s.cia.level4 = WOF_L4_AUDIO_IRQ;
    wof_paula_write(WOF_INTREQ, 0x0780);
    wof_paula_write(WOF_INTENA, 0x8780);
    wof_g.sound_installed = 1;                  /* and AddIntServer: src/input.c calls it */
}

/* orig 0x01EAC0 - channel c stopped: its interrupt off, its DMA off, the record free with no
 * count and no easing, the volume 0, the VBlank it stopped at, and the period left at 0x7C;
 * for channel 2 the flag 0x027F16 cleared. */
static void channel_stop(int c)
{
    wof_paula_write(WOF_INTENA, (uint16_t)(0x80u << c));
    CHAN(c).pending = 0;
    wof_paula_write(WOF_DMACON, (uint16_t)(1u << c));
    CHAN(c).sample = 0;
    CHAN(c).count  = -1;
    CHAN(c).target = -1;
    wof_paula_write(AUD(c, AUDVOL), 0);
    CHAN(c).stamp = wof_g.sound_vblanks;
    wof_paula_write(AUD(c, AUDPER), wof_tbl_channel_stop_period[0]);
    if (c == 2)
        wof_g.sound_flags[2] = 0;
}

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

/* orig 0x01EB4C - the period of a playing channel, and its volume with any easing given up;
 * a negative value leaves its register alone. */
static void channel_adjust(int c, uint16_t period, uint16_t volume)
{
    if ((int16_t)period >= 0)
        wof_paula_write(AUD(c, AUDPER), period);
    if ((int16_t)volume >= 0) {
        CHAN(c).target = -1;
        CHAN(c).volume = (uint32_t)volume << 16;
        wof_paula_write(AUD(c, AUDVOL), volume);
    }
}

/* orig 0x01EBAA audio_irq - the level-4 handler: the CPU's interrupt off for its length; the
 * long at 0x027F1A stored into the table 0x026218 at the index 0x027F18 (nothing writes
 * either, so it stores 0 at 0x026218); then every channel whose request is on and enabled:
 * a free record, or a count that runs out, stops it (interrupt off - of this channel and of
 * every one handled before it in this call - DMA off, volume 0, no easing, the VBlank it
 * stopped at, the record free); a count below zero plays on for ever.  The requests it saw
 * are cleared. */
void wof_audio_irq(void)
{
    uint16_t d0, d4 = 0;
    uint32_t at = 0x026218u + (uint32_t)(int32_t)(int16_t)(uint16_t)(wof_g.g_027f18 * 4u);

    wof_paula_write(WOF_INTENA, 0x4000);
    wof_original_store16(at, (uint16_t)(wof_g.g_027f1a >> 16));
    wof_original_store16(at + 2u, (uint16_t)wof_g.g_027f1a);
    d0 = (uint16_t)(wof_paula_intreqr() & wof_paula_intenar() & 0x0780u);
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
    wof_paula_write(WOF_INTENA, 0xC000);
}

/* orig 0x01EC64 soundfx_vblank ("SoundFX_IntHandler") - the engine's VBlank: its count, the
 * audio interrupts off while it works; every channel whose record waits and stopped at least
 * two VBlanks ago gets its registers and its repeat count and is switched on together with
 * the others at the end; a volume being eased moves a step towards its target and stops
 * there.  The interrupts that were on come back on, and then all four. */
void wof_soundfx_vblank(void)
{
    wof_g.sound_vblanks++;
    wof_g.sound_intena = (uint16_t)(wof_paula_intenar() & 0x0780u);
    wof_paula_write(WOF_INTENA, 0x0780);
    wof_g.sound_dmacon = 0x8000;
    for (int c = 0; c < 4; c++) {
        wof_sound_channel_t *r = &CHAN(c);

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
        }
        if ((int16_t)((uint32_t)r->target >> 16) >= 0) {           /* 0x01ECF0 */
            int32_t v = (int32_t)r->volume;

            if (v == r->target) {
                v = r->target;
                r->target = -1;
            } else if (v < r->target) {
                v = (int32_t)((uint32_t)v + (uint32_t)r->step);
                if (v >= r->target) {
                    v = r->target;
                    r->target = -1;
                }
            } else {
                v = (int32_t)((uint32_t)v - (uint32_t)r->step);
                if (v <= r->target) {
                    v = r->target;
                    r->target = -1;
                }
            }
            r->volume = (uint32_t)v;
            wof_paula_write(AUD(c, AUDVOL), (uint16_t)((uint32_t)v >> 16));
        }
    }
    if (wof_g.sound_intena != 0)
        wof_paula_write(WOF_INTENA, (uint16_t)(wof_g.sound_intena | 0x8000u));
    if ((wof_g.sound_dmacon & 0xFFu) != 0)
        wof_paula_write(WOF_DMACON, wof_g.sound_dmacon);
    wof_paula_write(WOF_INTENA, 0x8780);
}

#ifdef WOF_TRACE
/* The oracle tests' entry (tests/test_oracle_m8.py): one routine of the engine by its
 * original address, on the port's state as the test left it.  Register arguments come in
 * a to f as the original takes them in D0, D1, D2, D3, D4 and A0; `out` takes D0 and D1 as
 * a routine leaves them where the caller goes on with them. */
int32_t wof_test_m8_call(uint32_t orig, int32_t a, int32_t b, int32_t c, int32_t d,
                         int32_t e, int32_t f, int32_t *out)
{
    uint16_t d0 = (uint16_t)a, d1 = (uint16_t)b;

    switch (orig) {
    case 0x011F4E: wof_sound_slots_clear(); return 0;
    case 0x011F76: wof_sound_slots_init(); return 0;
    case 0x012066: wof_sound_channels(); return 0;
    case 0x012132: wof_engine_sound(); return 0;
    case 0x0122CE: out[0] = distance_volume(d0); return 0;
    case 0x0122F6: out[0] = near_volume(d0); return 0;
    case 0x012306: out[0] = heard_at(d0, &d1); out[1] = d1; return 0;
    case 0x012324: out[0] = wof_sound_boom((int16_t)d0); return 0;
    case 0x01233E: wof_sound_splash((int16_t)d0); return 0;
    case 0x012354: wof_sound_clang(); return 0;
    case 0x012380: wof_sound_screech(); return 0;
    case 0x0123AC: wof_sound_scream(&d0, &d1); out[0] = d0; out[1] = d1; return 0;
    case 0x01E8B8: wof_sound_init(); return 0;
    case 0x01EA28:
        channel_play((uint32_t)f, (uint32_t)a, (uint16_t)b, (uint16_t)c, (uint16_t)d,
                     (uint16_t)e);
        return 0;
    case 0x01EAC0: channel_stop(a & 3); return 0;
    case 0x01EB4C: channel_adjust(a & 3, (uint16_t)b, (uint16_t)c); return 0;
    case 0x01EBAA: wof_audio_irq(); return 0;
    case 0x01EC64: wof_soundfx_vblank(); return 0;
    default:       return -1;
    }
}
#endif
