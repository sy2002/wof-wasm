/* The music (M8 part 2, re/notes/music.md): the game's two calls and the player they drive.
 *
 * music_start (orig 0x0123DC) and music_stop (orig 0x012470) load the song data wofsongs and
 * the player songplay with LoadSeg, give the player its commands and, when a song fades,
 * wait for the fade to end.  The player is a small executable of its own (re/songplay.lst,
 * whose CODE offsets the `orig songplay+0x....` comments give): a command entry, a tick
 * SongInt that CIA-A's timer A runs through ciaa.resource (src/audio.c), and a level-4
 * handler SongIntHandler that takes audio_irq's place while it is loaded.
 *
 * What LoadSeg puts in memory the port keeps in its state (src/mission.def): the parts of
 * the player's DATA hunk that change, loaded from the hunk's image (re/tables.toml,
 * player_data) at every load and gone at every unload, and the seven voices of the song
 * data, the only part of it the player writes, loaded from the file.  The rest of the song
 * data is read where the file system blob holds it (wof_song_data): its pointers are
 * relocated to its own DATA hunk, so that read as they stand they are offsets into it, and
 * an offset is what the port keeps wherever the original keeps a pointer into the song
 * data.  A sample the player plays is the sound handle WOF_SOUND(WOF_SONG_FILE, offset).
 *
 * The player writes the channel's registers through addresses its track records hold
 * (+0x28 to +0x34); so does the port, through the same registered fields.
 */
#include "wof.h"
#include "gen/tables.h"

#define HEAD     (wof_m.player_head[0])
#define VARS     (wof_m.player_vars[0])
#define SONG     (wof_m.player_song[0])
#define TRACK(t) (wof_m.player_tracks[t])

#define CUSTOM       0xDFF000u
#define AUD0LC       0x0A0u
#define ADKCON       0x09Eu
#define INTREQR      0x01Eu
#define NT_INTERRUPT 2u

/* ------------------------------------------------------------------ the song data */

static uint8_t sd8(uint32_t off)
{
    uint32_t       n;
    const uint8_t *d = wof_song_data(&n);

    if (off - WOF_VOICES_AT < WOF_VOICES * 0x2Eu)
        WOF_STANDIN("M8 STAND-IN: songplay, a voice of wofsongs read as bytes");
    return d && off < n ? d[off] : 0;
}

static uint16_t sd16(uint32_t off)
{
    return (uint16_t)(sd8(off) << 8 | sd8(off + 1u));
}

static uint32_t sd32(uint32_t off)
{
    return (uint32_t)sd16(off) << 16 | sd16(off + 2u);
}

/* A word index as the 68000 adds it to an address, d16(An,Dn.w). */
static uint32_t index_w(uint32_t d)
{
    return (uint32_t)(int32_t)(int16_t)(uint16_t)d;
}

/* The voice record a pointer into the song data names. */
static wof_voice_t *voice_at(uint32_t off)
{
    static wof_voice_t none;
    uint32_t n = (off - WOF_VOICES_AT) / 0x2Eu;

    if (off < WOF_VOICES_AT || n >= WOF_VOICES || off != WOF_VOICES_AT + n * 0x2Eu) {
        WOF_STANDIN("M8 STAND-IN: songplay, a voice pointer that names no voice of wofsongs");
        wof_mem_set(&none, 0, sizeof none);
        return &none;
    }
    return &wof_m.song_voices[n];
}

/* ------------------------------------------------------------------ the 68000's arithmetic */

/* divu.w: the quotient in the low word, the remainder in the high one; a quotient that
 * does not fit leaves the dividend as it was.  A divisor of 0 traps, which no song does. */
static uint32_t divu(uint32_t dividend, uint16_t divisor)
{
    uint32_t q;

    if (!divisor) {
        WOF_STANDIN("M8 STAND-IN: songplay, a division by zero, which traps");
        return dividend;
    }
    q = dividend / divisor;
    if (q > 0xFFFFu)
        return dividend;
    return (dividend % divisor) << 16 | q;
}

/* lsl.l Dn: the count modulo 64, 32 and more shift everything out. */
static uint32_t lsl32(uint32_t v, uint16_t count)
{
    count &= 63u;
    return count >= 32u ? 0u : v << count;
}

/* ------------------------------------------------------------------ the channel's registers */

static void reg16(uint32_t address, uint16_t value)
{
    wof_paula_write((uint16_t)(address - CUSTOM), value);
}

static void reg_lc(uint32_t address, uint32_t song_offset)
{
    wof_paula_lc((int)((address - CUSTOM - AUD0LC) >> 4),
                 WOF_SOUND(WOF_SONG_FILE, song_offset));
}

/* orig songplay+0x04DA audio_off - the audio interrupts off, then the four channels.  Its
 * write of 0x0780 to INTREQR (0xDFF01E), which can only be read, does nothing. */
static void audio_off(void)
{
    wof_paula_write(WOF_INTENA, 0x0780);
    wof_paula_write(INTREQR, 0x0780);
    wof_paula_write(WOF_DMACON, 0x000F);
}

/* ------------------------------------------------------------------ a note */

/* orig songplay+0x07EA note_period - D1 note: the octave of the voice's sample it plays in
 * (D3), from the notes per octave and the sample's ctOctave, and the period, from the note's
 * colour clocks per cycle and the sample's samplesPerHiCycle shifted by the octave; the
 * period into the channel, unless an effect has it, and as the track's base and current
 * period; the voice's vibrato starts over. */
static uint16_t note_period(wof_track_t *tr, uint16_t d1)
{
    uint32_t     a2 = tr->vhdr;
    uint32_t     q  = divu((uint32_t)d1, tr->octave_div);
    int16_t      d3 = (int16_t)(uint16_t)(sd8(a2 + 0x0Eu) - (uint16_t)q - 1u);
    int32_t      at = (int16_t)(uint16_t)((uint16_t)(d1 - wof_tbl_note_base[0]) << 2);
    uint32_t     clocks = 0;
    uint16_t     period;
    wof_voice_t *v;

    if (d3 < 0)
        d3 = 0;
    /* lea note_clocks+0xF0 (0x1134): entry 60 is the note note_base */
    at = 60 + at / 4;
    if (at >= 0 && at < (int32_t)(sizeof wof_tbl_note_clocks / sizeof wof_tbl_note_clocks[0]))
        clocks = wof_tbl_note_clocks[at];
    else
        WOF_STANDIN("M8 STAND-IN: songplay, a note outside note_clocks (+0x0816)");
    period = (uint16_t)divu(clocks, (uint16_t)lsl32(sd32(a2 + 8u), (uint16_t)d3));
    if (!tr->sfx)
        reg16(tr->reg_per, period);
    tr->base_period = period;
    tr->cur_period  = period;
    v = voice_at(tr->voice);
    v->vib_count = (int16_t)v->vib_first;
    tr->vib_step = v->vib_step;
    return (uint16_t)d3;
}

/* A byte of the durations: a note's length and the tick of its release, in pairs. */
static uint8_t duration(uint16_t at)
{
    if (at < WOF_TBL_DURATIONS_COUNT)
        return wof_tbl_durations[at];
    WOF_STANDIN("M8 STAND-IN: songplay, a length past the durations (+0x0712)");
    return 0;
}

/* orig songplay+0x0704 note_start - D1 the note, D2 its length's index: the pattern moves
 * on; the length and the release tick from the durations; with a sample, and unless the
 * note is the tied continuation of the one before, the period, the octave's part of the
 * sample into AUDxLC and AUDxLEN over its one-shot and repeat parts, the repeat part kept
 * for the channel's first interrupt, the volume (scaled while an effect plays), and DMA
 * and the channel's interrupt on.  The track counts as started either way. */
static void note_start(wof_track_t *tr, uint16_t d1, uint16_t d2)
{
    uint16_t d3, oct;
    uint32_t a0, a2, d;

    tr->pos += 2u;
    d2 = (uint16_t)(d2 << 1);
    d3 = (uint16_t)(duration(d2) - 1u);
    tr->dur = d3;
    d3 = (uint16_t)((d3 & 0xFF00u) | (uint8_t)((uint8_t)d3 - duration((uint16_t)(d2 + 1u))));
    tr->release = d3;
    if (tr->vhdr == 0)
        goto done;
    if (tr->tie) {
        if (tr->tie == 1)
            goto done;
        tr->tie--;
    }
    oct = note_period(tr, d1);
    a0  = tr->body;
    a2  = tr->vhdr;
    if (oct) {                                    /* past the lower octaves' parts */
        uint16_t d4 = oct;

        d = sd32(a2) + sd32(a2 + 4u);
        do {
            a0 += d;
            d <<= 1;
        } while (--d4);
    }
    if (!tr->sfx)
        reg_lc(tr->reg_lc, a0);
    tr->loop_start = a0 + lsl32(sd32(a2), oct);
    tr->irq = 1;
    d = lsl32(sd32(a2) + sd32(a2 + 4u), oct) >> 1;
    if (!tr->sfx)
        reg16(tr->reg_len, (uint16_t)d);
    tr->loop_words = (uint16_t)(lsl32(sd32(a2 + 4u), oct) >> 1);
    if (!tr->sfx) {
        uint32_t d0 = tr->volume;

        if (VARS.sfx_state == 0) {
            reg16(tr->reg_vol, (uint16_t)d0);
        } else {
            d0 = (uint16_t)(d0 << 8);
            d0 = d0 * VARS.sfx_music_vol;                 /* mulu.w */
            reg16(tr->reg_vol, (uint16_t)(d0 >> 16));
        }
    }
    wof_paula_write(ADKCON, 0x00FF);                      /* no modulation; the model has none */
    wof_paula_write(WOF_DMACON, HEAD.dma_on);
    wof_paula_write(WOF_INTENA, HEAD.int_on);
done:
    VARS.track_state |= 1u << (24u + (HEAD.track_number & 7u));   /* bset.b on its top byte */
}

/* orig songplay+0x0598 note_release - unless the note is held or tied: its channel off,
 * the volume 0, the period left at release_period; the channel is done with. */
static void note_release(wof_track_t *tr)
{
    if (tr->hold == 1)
        return;
    if (tr->tie)
        return;
    if (!tr->sfx) {
        wof_paula_write(WOF_DMACON, HEAD.dma_off);
        reg16(tr->reg_vol, 0);
        reg16(tr->reg_per, wof_tbl_release_period[0]);
    }
    tr->irq = -1;
}

/* ------------------------------------------------------------------ a track's step */

/* orig songplay+0x05D2 track_read - the pattern's next events up to its next note, which
 * note_start plays, D3 added to it: 0xD9 the next entry of the sequence, 0xDB the sequence
 * from its start, 0xDA the track ends, 0xDC a voice, 0xDD and 0xDE timer A's latch, loaded
 * and started, 0xDF the volume (not while the song fades), 0xE0 the hold; any other command
 * byte is passed over. */
static void track_read(wof_track_t *tr, uint16_t d3)
{
    uint32_t a0 = tr->seq, a1 = tr->pos, d0 = tr->seq_index;

    for (;;) {
        uint16_t d1 = sd8(a1), d2 = sd8(a1 + 1u);

        if (d1 < 0xD9u) {
            if (d1 & 0x80u) {                       /* tied to the note before */
                if (tr->tie == 0)
                    tr->tie = 2;
            } else {
                tr->tie = 0;
            }
            d1 = (uint16_t)((d1 & 0x7Fu) + sd16(a0 + index_w(d0) + 4u));   /* the transpose */
            tr->note = d1;
            note_start(tr, (uint16_t)(d1 + d3), d2);
            return;
        }
        if (d1 == 0xD9u) {                          /* orig songplay+0x0656 event_next */
            tr->seq_index += 6u;
            d0 += 6u;
            tr->pos = sd32(a0 + index_w(d0));
            a1 = tr->pos;
            continue;
        }
        if (d1 == 0xDBu) {                          /* orig songplay+0x066A event_repeat */
            tr->seq_index = 0;
            a0 = tr->seq;
            tr->pos = sd32(a0);
            a1 = tr->pos;
            d0 = tr->seq_index;
            continue;
        }
        if (d1 == 0xDAu) {                          /* orig songplay+0x0682 event_end */
            tr->active = 0;
            return;
        }
        if (d1 == 0xDCu) {                          /* orig songplay+0x0688 event_voice */
            uint32_t     a2 = sd32(SONG.voice_table + index_w((uint32_t)d2 << 2));
            wof_voice_t *v  = voice_at(a2);

            tr->voice      = a2;
            tr->vhdr       = v->vhdr;
            tr->body       = v->body;
            tr->octave_div = v->octave_div;
        } else if (d1 == 0xDDu) {                   /* orig songplay+0x06AA event_tempo_hi */
            wof_cia_write(WOF_CIAA_TAHI, (uint8_t)d2);
            wof_cia_write(WOF_CIAA_CRA, 0x10);
            wof_cia_write(WOF_CIAA_CRA, 0x01);
        } else if (d1 == 0xDEu) {                   /* orig songplay+0x06C2 event_tempo_lo */
            wof_cia_write(WOF_CIAA_TALO, (uint8_t)d2);
            wof_cia_write(WOF_CIAA_CRA, 0x10);
            wof_cia_write(WOF_CIAA_CRA, 0x01);
        } else if (d1 == 0xDFu) {                   /* orig songplay+0x06DC event_volume */
            if (VARS.play_state != 4) {
                if (!tr->sfx)
                    reg16(tr->reg_vol, d2);
                tr->volume = d2;
            }
        } else if (d1 == 0xE0u) {                   /* orig songplay+0x06FC event_hold */
            tr->hold = d2;
        }
        tr->pos += 2u;                              /* orig songplay+0x064E */
        a1 += 2u;
    }
}

/* orig songplay+0x04F4 track_step - one track, one tick: with a note sounding, the
 * arpeggio's next offset, the note's time one less, and at its release tick the release;
 * otherwise the arpeggio's note, or the vibrato's next step between its limits; with the
 * note's time run out, the pattern's next events. */
static void track_step(wof_track_t *tr)
{
    wof_voice_t *v;
    uint16_t     d3 = 0;

    if (tr->active == 0)
        return;
    if (tr->dur == 0) {
        track_read(tr, d3);
        return;
    }
    v = voice_at(tr->voice);
    if (v->arpeggio) {
        uint16_t d0 = v->arp_index;

        v->arp_index++;
        d3 = (uint16_t)v->arp[d0 & 3u];
    }
    tr->dur--;
    if (tr->dur == tr->release) {
        note_release(tr);
        return;
    }
    v = voice_at(tr->voice);
    if (v->arpeggio) {
        note_period(tr, (uint16_t)(tr->note + d3));
        return;
    }
    if (!v->vibrato)
        return;
    if ((int32_t)v->vib_count - 1 > 0) {           /* subq.w; bgt */
        v->vib_count--;
        return;
    }
    v->vib_count = (int16_t)v->vib_every;
    {
        uint16_t d0 = (uint16_t)(tr->cur_period - tr->base_period);
        uint16_t d2 = tr->cur_period;

        if (tr->vib_step < 0 ? !(d0 > v->vib_lo) : d0 > v->vib_hi)
            tr->vib_step = (int16_t)(uint16_t)(0u - (uint16_t)tr->vib_step);
        d2 = (uint16_t)(d2 + (uint16_t)tr->vib_step);
        if (!tr->sfx)
            reg16(tr->reg_per, d2);
        tr->cur_period = d2;
    }
}

/* ------------------------------------------------------------------ the tick */

/* orig songplay+0x035A song_begin - each track from its sequence's first entry, at the
 * starting volume; PlayState 2 and the channels off; then as PlayState 2. */
static void song_begin(void)
{
    for (int t = 0; t < 4; t++) {
        wof_track_t *tr = &TRACK(t);

        tr->active    = 0xFFFF;
        tr->seq       = sd32(VARS.song_addr + 4u * (uint32_t)t);
        tr->pos       = sd32(tr->seq);
        tr->seq_index = 0;
        tr->dur       = 0;
        tr->volume    = wof_tbl_track_volume[t];
    }
    VARS.play_state = 2;
    wof_paula_write(WOF_DMACON, 0x000F);
}

/* orig songplay+0x041E song_step - the four tracks' steps, each with its channel's bits;
 * when no track has started a note since the timer was opened, the song is over. */
static void song_step(void)
{
    for (uint16_t t = 0; t < 4; t++) {
        HEAD.dma_on       = (uint16_t)(0x8000u | 1u << t);
        HEAD.dma_off      = (uint16_t)(1u << t);
        HEAD.int_on       = (uint16_t)(0x8000u | 0x80u << t);
        HEAD.track_number = t;
        track_step(&TRACK(t));
    }
    if (VARS.track_state == 0) {
        VARS.play_state = 0;
        audio_off();
    }
}

/* orig songplay+0x02FE song_stop */
static void song_stop(void)
{
    VARS.play_state = 0;
    audio_off();
}

/* orig songplay+0x0348 track_fade - the track's volume one lower; whether it had any. */
static int track_fade(wof_track_t *tr)
{
    if (tr->volume == 0)
        return 0;
    tr->volume--;
    return 1;
}

/* orig songplay+0x030A song_fade - every FadeSpeed + 1 ticks every track's volume one
 * lower, the tracks playing on meanwhile; with no volume left the song stops.  A note that
 * sounds keeps the volume it started with: only the next note takes the lower one. */
static void song_fade(void)
{
    int32_t count = (int32_t)VARS.fade_count - 1;
    int     any   = 0;

    VARS.fade_count = (int16_t)count;
    if (count >= 0) {                                  /* subq.w; bge */
        song_step();
        return;
    }
    VARS.fade_count = VARS.fade_speed;
    for (int t = 0; t < 4; t++)
        any |= track_fade(&TRACK(t));
    if (any)
        song_step();
    else
        song_stop();
}

/* orig songplay+0x02A6 SongInt - timer A's tick: a sound effect _PlaySfx left waiting is
 * started; unless the music is paused, the song's state machine (re/notes/music.md). */
void wof_song_int(void)
{
    if (VARS.sound_ptr)
        WOF_STANDIN("M8 STAND-IN: songplay+0x02B8, sfx_start (+0x0104), an effect of command 7");
    if (VARS.paused)
        return;
    switch (VARS.play_state) {
    case 1: song_begin(); song_step(); break;
    case 2: song_step(); break;
    case 3: song_stop(); break;
    case 4: song_fade(); break;
    default: break;
    }
}

/* ------------------------------------------------------------------ the channels' interrupts */

/* orig songplay+0x08AE CheckChannelInt - D1 the request's bit in INTREQR (D0), D2 the
 * channel's DMA bit, D3 its interrupt bit.  At a note's first interrupt the channel is
 * given its sample's repeat part to loop, or, with none, is marked to go off at the next;
 * then off: volume 0, the period at release_period, DMA off.  A channel an effect has
 * counts the effect's repeats down instead.  The request is cleared whether it was set or
 * not. */
static void check_channel_int(wof_track_t *tr, uint16_t d0, uint16_t d1, uint16_t d2, uint16_t d3)
{
    int off = 0;

    if (d0 & (1u << (d1 & 31u))) {
        if (tr->sfx) {
            if (tr->sfx_count == 0)
                off = 1;
            else if (tr->sfx_count != -1)
                tr->sfx_count--;
        } else if (tr->irq == 0) {
            off = 1;
        } else if (tr->irq > 0) {
            if (tr->loop_words) {
                reg16(tr->reg_len, tr->loop_words);
                reg_lc(tr->reg_lc, tr->loop_start);
                tr->irq = -1;
            } else {
                tr->irq = 0;
            }
        }
        if (off) {                                     /* orig songplay+0x08CC */
            VARS.sfx_state = (uint16_t)(VARS.sfx_state & ~(1u << (8u + ((d1 - 7u) & 7u))));
            reg16(tr->reg_vol, 0);
            reg16(tr->reg_per, wof_tbl_release_period[1]);
            wof_paula_write(WOF_DMACON, d2);
            tr->irq       = -1;
            tr->sfx_count = 0;
            tr->sfx       = 0;
        }
    }
    wof_paula_write(WOF_INTREQ, d3);
}

/* orig songplay+0x0848 SongIntHandler - the player's level-4 handler: each channel's
 * request as INTREQR shows it. */
void wof_song_int_handler(void)
{
    uint16_t d0 = wof_paula_intreqr();

    for (uint16_t t = 0; t < 4; t++)
        check_channel_int(&TRACK(t), d0, (uint16_t)(7u + t), (uint16_t)(1u << t),
                          (uint16_t)(0x80u << t));
}

/* ------------------------------------------------------------------ the commands */

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

/* orig songplay+0x0A50 _CloseTimerInt - command 4: the timer's vector removed (the timer
 * itself runs on), the audio interrupts and the channels off, 0x70 given back. */
static void close_timer_int(void)
{
    wof_s.cia.vector = 0;                              /* RemICRVector(0, timer_node) */
    wof_paula_write(WOF_INTENA, 0x0780);
    wof_paula_write(INTREQR, 0x0780);
    wof_paula_write(WOF_DMACON, 0x000F);
    wof_s.cia.level4 = (uint16_t)HEAD.saved_level4_vector;
}

/* orig songplay+0x099C find_vhdr and orig songplay+0x09AC find_body - the word-aligned
 * chunk id, and the address past its header. */
static uint32_t find_chunk(uint32_t a2, uint32_t id)
{
    uint32_t n;

    wof_song_data(&n);
    while (sd32(a2) != id) {
        a2 += 2u;
        if (a2 >= n) {
            WOF_STANDIN("M8 STAND-IN: songplay, a sample without its chunk (+0x099C)");
            return 0;
        }
    }
    return a2 + 8u;
}

/* orig songplay+0x0946 _ReadInstruments - command 1, D1 the song, D2 the song data: the
 * song and its voice table; for every voice from 1 on up to the zero long that has a sample,
 * its VHDR, its notes per octave (octave_notes / ctOctave) and its BODY. */
static void read_instruments(uint32_t d1, uint32_t d2)
{
    uint32_t a0 = sd32(d2 + index_w(d1 << 2));

    SONG.song_ptr    = a0;
    a0 += 0x10u;
    SONG.voice_table = a0;
    for (;;) {
        uint32_t     a1, a2;
        wof_voice_t *v;

        a0 += 4u;
        a1 = sd32(a0);
        if (a1 == 0)
            break;
        v = voice_at(a1);
        if (v->form == 0)
            continue;
        a2 = find_chunk(v->form, 0x56484452u);              /* "VHDR" */
        v->vhdr = a2;
        v->octave_div = (uint16_t)divu(wof_tbl_octave_notes[0], sd8(a2 + 0x0Eu));
        v->body = find_chunk(a2, 0x424F4459u);              /* "BODY" */
    }
}

/* orig songplay+0x0000 segentry - the command in D0.  The game reads D0 back only after
 * command 5; the others give 0 here.  Commands 3 and 7 to 12 are never given. */
uint16_t wof_player_call(uint16_t command, uint32_t d1, uint32_t d2)
{
    switch (command) {
    case 0:
        open_timer_int();
        break;
    case 1:
        read_instruments(d1, d2);
        break;
    case 2:              /* orig songplay+0x092A _PlaySong, orig songplay+0x027C PlaySong */
        if (VARS.play_state == 0 && (int32_t)SONG.song_ptr > 0) {
            VARS.song_addr  = SONG.song_ptr;
            VARS.play_state = 1;
        }
        break;
    case 4:
        close_timer_int();
        break;
    case 5:                                    /* orig songplay+0x029E _GetSongStat */
        return VARS.play_state;
    case 6:                                    /* orig songplay+0x0084 _FadeSong */
        if (VARS.paused) {
            WOF_STANDIN("M8 STAND-IN: songplay+0x0064 _StopSong, a fade while paused");
            break;
        }
        if (VARS.play_state == 0)
            break;
        VARS.fade_count = (int16_t)d1;
        VARS.fade_speed = (int16_t)d1;
        VARS.play_state = 4;
        break;
    case 3:
        WOF_STANDIN("M8 STAND-IN: songplay+0x0064 _StopSong, command 3");
        break;
    case 7:
        WOF_STANDIN("M8 STAND-IN: songplay+0x0034, command 7, _PlaySfx (+0x00AA)");
        break;
    case 8:
        WOF_STANDIN("M8 STAND-IN: songplay+0x003A, command 8, _StopSfx (+0x01A8)");
        break;
    case 9:
        WOF_STANDIN("M8 STAND-IN: songplay+0x0042, command 9, _SfxStat (+0x01EA)");
        break;
    case 10:
        WOF_STANDIN("M8 STAND-IN: songplay+0x004A, command 10, _PauseMusic (+0x01FA)");
        break;
    case 11:
        WOF_STANDIN("M8 STAND-IN: songplay+0x0052, command 11, _RestartMusic (+0x0240)");
        break;
    case 12:
        WOF_STANDIN("M8 STAND-IN: songplay+0x005A, command 12, _AdjustSfx (+0x0252)");
        break;
    default:
        break;
    }
    return 0;
}

/* ------------------------------------------------------------------ the game's calls */

/* The wait of music_start (0x012402) and music_stop (0x01248E) for a fade to end: command 5
 * again and again until it answers 0, with nothing else in the loop.  On the machine the
 * timer's ticks end the fade while the loop spins; the port gives each round the four
 * VBlanks the headless original gives it (re/notes/headless.md, "The fade's wait"), so that
 * the input sample's phase is where it was. */
#define SPIN_VBLANKS 4u

/* orig 0x0123DC music_start("wofsongs", song) - the song number kept; with the music loaded
 * the playing song faded out and, unless opt_music_off is set, its end waited for; without
 * it the song data and the player loaded, the song data's entry called for its address, and
 * the player's timer opened.  Then the song's voices read and, unless opt_music_off is set,
 * the song started and 0x027430's first byte set. */
wof_co_t wof_music_start(uint16_t song)
{
    wof_ctx_t *c = &wof_f.co_music;
    uint32_t   n;

    CO_BEGIN(c);
    wof_g.song_number = song;
    if (wof_m.songs_seglist[0].set) {
        wof_player_call(6, wof_tbl_music_fade_speed[0], 0);
        if (!wof_g.opt_music_off) {
            while (wof_player_call(5, 0, 0) != 0) {
                for (wof_f.music_spin = SPIN_VBLANKS; wof_f.music_spin; wof_f.music_spin--)
                    CO_WAIT(c);
            }
        }
    } else {
        /* 0x01240E: LoadSeg of the song data; none, and the call does nothing */
        if (!wof_song_data(&n))
            CO_RETURN(c);
        wof_m.songs_seglist[0].set = 1;
        wof_m.song_data[0].set     = 1;                     /* its entry: lea DATA,a0 */
        /* 0x01242C: LoadSeg("songplay"), its entry, command 0 */
        wof_m.player_seglist[0].set = 1;
        wof_m.player_entry[0].set   = 1;
        wof_music_memory_load(wof_tbl_player_data, wof_song_data(&n));
        wof_player_call(0, 0, 0);
    }
    wof_player_call(1, wof_g.song_number, 0);               /* the song data is offset 0 */
    if (!wof_g.opt_music_off) {
        wof_player_call(2, wof_g.song_number, 0);
        wof_g.music_playing[0] = (uint16_t)(wof_g.music_playing[0] | 0xFF00u);   /* st.b */
    }
    CO_END(c);
}

/* orig 0x012470 music_stop - with the music loaded: the song faded out, 0x027430 cleared,
 * unless opt_music_off is set the fade's end waited for, the timer closed, and both files
 * unloaded (0x01249E) with the four pointers cleared. */
wof_co_t wof_music_stop(void)
{
    wof_ctx_t *c = &wof_f.co_music;

    CO_BEGIN(c);
    if (!wof_m.songs_seglist[0].set)
        CO_RETURN(c);
    wof_player_call(6, wof_tbl_music_fade_speed[1], 0);
    wof_g.music_playing[0] = 0;
    if (!wof_g.opt_music_off) {
        while (wof_player_call(5, 0, 0) != 0) {
            for (wof_f.music_spin = SPIN_VBLANKS; wof_f.music_spin; wof_f.music_spin--)
                CO_WAIT(c);
        }
    }
    wof_player_call(4, 0, 0);
    wof_music_memory_free();
    wof_m.songs_seglist[0].set  = 0;
    wof_m.song_data[0].set      = 0;
    wof_m.player_seglist[0].set = 0;
    wof_m.player_entry[0].set   = 0;
    CO_END(c);
}

#ifdef WOF_TRACE
/* The oracle tests' entry (tests/test_oracle_m8.py): one routine of the player by its
 * offset in songplay's CODE hunk, on the port's state as the test left it.  `t` is the
 * track A3 names, `d1` and `d2` come as the original takes them in D1 and D2 (D3 for
 * track_read), the song data given as offset 0; `out` takes D0, and D3 of note_period, D7 of
 * track_fade. */
int32_t wof_test_songplay_call(uint32_t offset, int32_t t, int32_t d1, int32_t d2, int32_t *out)
{
    wof_track_t *tr = &TRACK(t & 3);

    switch (offset) {
    case 0x0000: out[0] = wof_player_call((uint16_t)d2, (uint32_t)d1, 0); return 0;
    case 0x02A6: wof_song_int(); return 0;
    case 0x0348: out[0] = track_fade(tr) ? 0xFFFF : 0; return 0;
    case 0x04F4: track_step(tr); return 0;
    case 0x0598: note_release(tr); return 0;
    case 0x05D2: track_read(tr, (uint16_t)d1); return 0;
    case 0x0704: note_start(tr, (uint16_t)d1, (uint16_t)d2); return 0;
    case 0x07EA: out[0] = note_period(tr, (uint16_t)d1); return 0;
    case 0x0848: wof_song_int_handler(); return 0;
    case 0x0946: read_instruments((uint32_t)d1, 0); return 0;
    default:     return -1;
    }
}
#endif
