/* Paula's audio side (SPEC 6.5, re/notes/sound.md): the four channels the effects engine
 * (src/sound.c) plays through, their interrupts, and the mixer that turns them into the
 * shell's PCM.
 *
 * The model is the one tools/headless_paula.py gives the headless original, so that the
 * sound event logs of the two can be held to each other (SPEC 8).  Time is counted in units
 * of 1 / (clock x hz) seconds: a VBlank is `clock` units and a byte of a sample at period P
 * lasts P x hz units, clock being the colour clock of the video standard (PAL 3,546,895 Hz at
 * 50 Hz, NTSC 3,579,545 Hz at 60 Hz).  Every register write the game makes after VBlank k -
 * in soundfx_vblank at that VBlank, in the pass and the tick after it - happens at the
 * instant T_k = k x clock.  A channel's own events happen at their exact instants; those in
 * [T_k, T_k+1) are delivered at VBlank k+1, before its servers, in time order and at equal
 * instants in channel order, and an event at exactly T_k sees every write made at T_k.
 *
 * A channel switched on in DMACON takes LC and LEN (0 is 65,536 words) and raises its
 * interrupt request at once (Paula's first data fetch); it plays 2 x LEN bytes, each for
 * the period AUDxPER holds when the byte begins; when the last byte has played it takes LC
 * and LEN again as they stand, raises the request again and plays on.  Cleared in DMACON it
 * stops.  A request reaches audio_irq when INTENA has the master bit and the channel's bit,
 * after every channel event of a boundary and after soundfx_vblank returns.
 *
 * CIA-A's timer A, which the music player takes (src/music.c), is part of the same time: it
 * counts at the E clock, one tick of 5 x hz units, and underflows N + 1 ticks after it was
 * loaded with N (0 counting as 1); an underflow is an event like a channel's, delivered at
 * its instant in the same walk, after the channels' events of the same instant, with the
 * player's SongInt as ciaa.resource's vector.  Writing CRA to start a running timer without
 * a forced load leaves it counting; stopping it keeps what is left in the counter.
 *
 * The mixer runs inside the same walk: the output frames of [T_k, T_k+1) are mixed at the
 * boundary of VBlank k+1, each frame from the byte every channel plays at its instant, so a
 * channel audio_irq stops at a cycle's end falls silent there and not a VBlank later.
 * Channels 0 and 3 go left, 1 and 2 right (the Amiga's layout); the shell narrows the
 * stereo if asked.  The frames wait in a queue outside the state until wof_audio_render
 * takes them, so the shell's calls never touch what the game computes.
 *
 * Integer only.  Nothing here reads the wall clock; the state that matters is wof_s.paula. */
#include "wof.h"
#include "gen/tables.h"

#define PAL_CLOCK   3546895u
#define NTSC_CLOCK  3579545u
#define AUDIO_BITS  0x0780u
#define LEVEL4_ON   0x4000u

#define P (wof_s.paula)
#define C (wof_s.cia)
#define E_CLOCK_CC 5u       /* colour clocks per E clock cycle */

static uint32_t clock_of(uint16_t hz)
{
    return hz == 50 ? PAL_CLOCK : NTSC_CLOCK;
}

/* ------------------------------------------------------------------ the samples */

/* The eight effects, where the file system blob holds them.  Not state: the blob is the same
 * from one wof_init to the next, and a handle names a file by its index in sound_files. */
static const uint8_t *sound_bytes[8];
static uint32_t       sound_size[8];

static uint32_t be32(const uint8_t *p)
{
    return (uint32_t)p[0] << 24 | (uint32_t)p[1] << 16 | (uint32_t)p[2] << 8 | p[3];
}

/* The song data: wofsongs's DATA hunk, the second of the file, found as LoadSeg finds it
 * (tools/hunk.py reads the same): the header with its hunk sizes, then each hunk with its
 * relocations, symbols and debug data, up to the overlay table, where LoadSeg stops.  The
 * hunk's pointers are relocated to the hunk itself, so read as they stand they are offsets
 * into it (re/notes/music.md). */
static const uint8_t *song_bytes;
static uint32_t       song_size;

const uint8_t *wof_song_data(uint32_t *size)
{
    const uint8_t *raw;
    uint32_t       len, at = 4, first, last, hunk = 0, n;

    *size = song_size;
    if (song_bytes)
        return song_bytes;
    raw = wof_fs_find(wof_tbl_songs_file, &len);
    if (!raw || len < 8 || be32(raw) != 0x3F3u)
        return 0;
    for (;;) {                                          /* resident library names */
        if (at + 4 > len)
            return 0;
        n = be32(raw + at);
        at += 4;
        if (!n)
            break;
        at += 4u * n;
    }
    if (at + 12 > len)
        return 0;
    first = be32(raw + at + 4);
    last  = be32(raw + at + 8);
    at += 12u + 4u * (last - first + 1u);
    while (at + 4 <= len) {
        uint32_t type = be32(raw + at) & 0x3FFFFFFFu;

        at += 4;
        switch (type) {
        case 0x3E9:                                     /* HUNK_CODE */
        case 0x3EA:                                     /* HUNK_DATA */
            n = at + 4 <= len ? 4u * be32(raw + at) : 0;
            at += 4;
            if (at + n > len)
                return 0;
            if (hunk++ == 1) {
                song_bytes = raw + at;
                song_size  = n;
                *size      = n;
                return song_bytes;
            }
            at += n;
            break;
        case 0x3EB:                                     /* HUNK_BSS */
            at += 4;
            hunk++;
            break;
        case 0x3EC:                                     /* HUNK_RELOC32 */
            while (at + 4 <= len && (n = be32(raw + at)) != 0)
                at += 8u + 4u * n;
            at += 4;
            break;
        case 0x3F0:                                     /* HUNK_SYMBOL */
            while (at + 4 <= len && (n = be32(raw + at) & 0xFFFFFFu) != 0)
                at += 8u + 4u * n;
            at += 4;
            break;
        case 0x3F1:                                     /* HUNK_DEBUG */
            at += 4u + (at + 4 <= len ? 4u * be32(raw + at) : 0);
            break;
        case 0x3F2:                                     /* HUNK_END */
            break;
        default:                                        /* the overlay table, or no hunk */
            return 0;
        }
    }
    return 0;
}

const int8_t *wof_sound_data(uint32_t handle, uint32_t *left)
{
    int      file = WOF_SOUND_FILE(handle);
    uint32_t off  = WOF_SOUND_OFFSET(handle);

    *left = 0;
    if (file == WOF_SONG_FILE) {
        uint32_t       n;
        const uint8_t *d = wof_song_data(&n);

        if (!d || off >= n)
            return 0;
        *left = n - off;
        return (const int8_t *)(d + off);
    }
    if (file < 0 || file >= 8)
        return 0;
    if (!sound_bytes[file])
        sound_bytes[file] = wof_fs_find(wof_tbl_sound_files[file], &sound_size[file]);
    if (!sound_bytes[file] || off >= sound_size[file])
        return 0;
    *left = sound_size[file] - off;
    return (const int8_t *)(sound_bytes[file] + off);
}

/* ------------------------------------------------------------------ the event log */

#ifdef WOF_TRACE
#define EVENT_MAX 8192
static wof_sound_event_t events[EVENT_MAX];
static uint32_t          event_count;

uint32_t wof_sound_event_count(void) { return event_count; }
const wof_sound_event_t *wof_sound_event_at(uint32_t i) { return i < event_count ? &events[i] : 0; }
void wof_sound_events_reset(void) { event_count = 0; }

static void log_event(uint16_t kind, int c, uint64_t t, uint32_t vblank)
{
    const wof_paula_channel_t *ch = &P.ch[c];
    wof_sound_event_t         *e;

    if (event_count >= EVENT_MAX)
        return;
    e = &events[event_count++];
    e->time    = t;
    e->vblank  = vblank;
    e->pass    = wof_f.passes_run;
    e->tick    = wof_f.ticks_run;
    e->kind    = kind;
    e->channel = (uint16_t)c;
    e->file    = (int16_t)WOF_SOUND_FILE(ch->lc);
    e->offset  = ch->lc ? WOF_SOUND_OFFSET(ch->lc) : 0;
    e->words   = ch->len;
    e->period  = ch->per;
    e->volume  = ch->vol;
}
#else
#define log_event(kind, c, t, vblank) ((void)0)
#endif

/* ------------------------------------------------------------------ the mixer's queue */

/* Output frames wait here between the boundary that mixed them and wof_audio_render.  At
 * most half a second; what the shell leaves longer is dropped from the front. */
#define QUEUE_FRAMES 32768u
static int16_t  queue[QUEUE_FRAMES * 2];
static uint32_t queue_head, queue_count;
static uint32_t out_rate = 48000;

static void queue_put(int16_t l, int16_t r)
{
    uint32_t at;

    if (queue_count == QUEUE_FRAMES) {
        queue_head = (queue_head + 1) % QUEUE_FRAMES;
        queue_count--;
    }
    at = (queue_head + queue_count) % QUEUE_FRAMES;
    queue[at * 2]     = l;
    queue[at * 2 + 1] = r;
    queue_count++;
}

/* ------------------------------------------------------------------ the channels */

static uint64_t unit(int c)
{
    uint16_t per = P.ch[c].per ? P.ch[c].per : 1;

    return (uint64_t)per * P.hz;
}

static uint32_t cycle_bytes(uint16_t len)
{
    return 2u * (len ? len : 0x10000u);
}

#define NEVER UINT64_MAX

/* The instant channel c's cycle ends, if that is before `end`; NEVER otherwise. */
static uint64_t cycle_end(int c, uint64_t end)
{
    const wof_paula_channel_t *ch = &P.ch[c];
    uint64_t t;

    if (!ch->on)
        return NEVER;
    t = ch->next + (uint64_t)ch->left * unit(c);
    return t < end ? t : NEVER;
}

/* Every byte of the cycle that begins before `until` begins; the cycle does not end here. */
static void advance(int c, uint64_t until)
{
    wof_paula_channel_t *ch = &P.ch[c];
    uint64_t u, n;

    if (!ch->on || ch->left == 0 || ch->next >= until)
        return;
    u = unit(c);
    n = (until - 1u - ch->next) / u + 1u;
    if (n > ch->left)
        n = ch->left;
    ch->left -= (uint32_t)n;
    ch->ptr  += (uint32_t)n;
    ch->next += n * u;
}

static void request(int c)
{
    P.intreq = (uint16_t)(P.intreq | (0x80u << c));
}

static int deliverable(void)
{
    return (P.intena & LEVEL4_ON) && (P.intena & P.intreq & AUDIO_BITS);
}

/* The byte channel c plays at instant t, times its volume: the last byte that began at or
 * before t.  A channel that has not begun a byte of its cycle yet plays nothing. */
static int32_t level(int c, uint64_t t)
{
    wof_paula_channel_t *ch = &P.ch[c];
    const int8_t        *data;
    uint32_t             left;
    uint16_t             vol;

    if (!ch->on)
        return 0;
    advance(c, t + 1u);
    if (ch->next <= t || WOF_SOUND_OFFSET(ch->ptr) == 0)
        return 0;                       /* nothing of this cycle has begun */
    data = wof_sound_data(ch->ptr - 1u, &left);
    if (!data)
        return 0;
    vol = ch->vol > 64 ? 64 : ch->vol;
    return (int32_t)data[0] * vol;
}

/* The output frames whose instants lie in [from, to): frame j lies at j x clock x hz / rate. */
static void mix(uint64_t from, uint64_t to)
{
    uint64_t per_second = (uint64_t)clock_of(P.hz) * P.hz;
    uint64_t j   = (from * out_rate + per_second - 1u) / per_second;
    uint64_t end = (to * out_rate + per_second - 1u) / per_second;

    for (; j < end; j++) {
        uint64_t t = j * per_second / out_rate;
        int32_t  l = level(0, t) + level(3, t);
        int32_t  r = level(1, t) + level(2, t);

        l *= 2;
        r *= 2;
        queue_put((int16_t)(l > 32767 ? 32767 : l < -32768 ? -32768 : l),
                  (int16_t)(r > 32767 ? 32767 : r < -32768 ? -32768 : r));
    }
}

static uint64_t now(void)
{
    return (uint64_t)P.vblanks * clock_of(P.hz);
}

/* The instant of the channel event being delivered, while one is; a write inside audio_irq
 * then happens there and not at the boundary.  `in_server` while a VBlank's servers run,
 * whose requests are delivered when they return (wof_vblank). */
static uint64_t event_at;
static int      in_event;
static int      in_server;

void wof_paula_server(int inside)
{
    in_server = inside;
}

static void start(int c)
{
    wof_paula_channel_t *ch = &P.ch[c];
    uint64_t t = in_event ? event_at : now();

    ch->on   = 1;
    ch->ptr  = ch->lc;
    ch->left = cycle_bytes(ch->len);
    ch->next = t;
    log_event('S', c, t, P.vblanks + (in_event ? 1u : 0u));
    request(c);
}

static void restart(int c, uint64_t t)
{
    wof_paula_channel_t *ch = &P.ch[c];

    ch->ptr  = ch->lc;
    ch->left = cycle_bytes(ch->len);
    ch->next = t;
    log_event('R', c, t, P.vblanks + 1u);
    request(c);
}

/* ------------------------------------------------------------------ the registers */

static uint16_t set_clear(uint16_t old, uint16_t value)
{
    return (uint16_t)(value & 0x8000u ? (old | (value & 0x7FFFu)) : (old & ~value & 0x7FFFu));
}

void wof_paula_write(uint16_t reg, uint16_t value)
{
    /* DMACONR, ADKCONR, INTENAR and INTREQR can only be read: a write to one does nothing,
     * and what it reads stays the model's (the player writes INTREQR, src/music.c). */
    if (reg == 0x002 || reg == 0x010 || reg == 0x01C || reg == 0x01E)
        return;
    if (reg == WOF_DMACON) {
        for (int c = 0; c < 4; c++) {
            if (!(value & (1u << c)))
                continue;
            if ((value & 0x8000u) && !P.ch[c].on)
                start(c);
            else if (!(value & 0x8000u) && P.ch[c].on)
                P.ch[c].on = 0;
        }
    } else if (reg == WOF_INTENA) {
        P.intena = set_clear(P.intena, value);
    } else if (reg == WOF_INTREQ) {
        P.intreq = set_clear(P.intreq, value);
    } else if (reg >= 0x0A0 && reg < 0x0E0) {
        wof_paula_channel_t *ch = &P.ch[(reg - 0x0A0) >> 4];

        switch (reg & 0x0F) {
        case 0x4: ch->len = value; break;
        case 0x6: ch->per = value; break;
        case 0x8: ch->vol = value; break;
        default:  break;
        }
    }
    if (!in_event && !in_server && deliverable())
        P.late += 1;          /* made deliverable by the main program: none is expected */
}

void wof_paula_lc(int channel, uint32_t sound)
{
    P.ch[channel & 3].lc = sound;
}

uint16_t wof_paula_intenar(void) { return (uint16_t)(P.intena & 0x7FFFu); }
uint16_t wof_paula_intreqr(void) { return (uint16_t)(P.intreq & 0x7FFFu); }

/* ------------------------------------------------------------------ the VBlank */

/* The level-4 handler while a request is deliverable, whichever is at the autovector:
 * audio_irq once sound_init has put it there, the player's SongIntHandler while the music
 * is loaded, the system's before either, which clears what it is given. */
void wof_paula_deliver(void)
{
    for (int rounds = 0; deliverable() && rounds < 8; rounds++) {
        P.irqs++;
        switch (C.level4) {
        case WOF_L4_AUDIO_IRQ: wof_audio_irq();         break;
        case WOF_L4_SONGINT:   wof_song_int_handler();  break;
        default: P.intreq = (uint16_t)(P.intreq & ~AUDIO_BITS); break;
        }
    }
}

/* ------------------------------------------------------------------ CIA-A's timer A */

static uint64_t e_tick(void)
{
    return (uint64_t)E_CLOCK_CC * P.hz;
}

/* From a load of `count` to the underflow: count + 1 ticks, a count of 0 as 1. */
static uint64_t timer_period(uint16_t count)
{
    return ((uint64_t)(count ? count : 1u) + 1u) * e_tick();
}

void wof_cia_write(uint32_t address, uint8_t value)
{
    uint64_t t = in_event ? event_at : now();

    if (address == WOF_CIAA_TALO) {
        C.latch = (uint16_t)((C.latch & 0xFF00u) | value);
    } else if (address == WOF_CIAA_TAHI) {
        C.latch = (uint16_t)((C.latch & 0x00FFu) | (uint16_t)value << 8);
        if (!C.running) {                   /* a stopped timer is loaded, a one-shot starts */
            C.counter = C.latch;
            if (C.oneshot) {
                C.running = 1;
                C.next    = t + timer_period(C.counter);
            }
        }
    } else if (address == WOF_CIAA_CRA) {
        if (C.running && (value & 0x01u) && !(value & 0x10u)) {
            C.oneshot = (value & 0x08u) != 0;           /* it counts on */
            return;
        }
        if (C.running) {                    /* what is left: ticks to the underflow, less one */
            uint64_t left = C.next > t ? C.next - t : 0;
            uint64_t n    = (left + e_tick() - 1u) / e_tick();

            C.counter = (uint16_t)(n > 1u ? n - 1u : 0u);
        }
        if (value & 0x10u)
            C.counter = C.latch;
        C.oneshot = (value & 0x08u) != 0;
        C.running = value & 0x01u;
        C.next    = C.running ? t + timer_period(C.counter) : 0;
    }
}

static uint64_t timer_due(uint64_t end)
{
    return C.running && C.next < end ? C.next : NEVER;
}

/* Timer A underflows at t: it reloads from the latch, a one-shot timer stops, and the
 * vector ciaa.resource keeps for it runs, its writes at the underflow's instant. */
static void timer_underflow(uint64_t t)
{
    C.counter = C.latch;
    if (C.oneshot) {
        C.running = 0;
        C.next    = 0;
    } else {
        C.next = t + timer_period(C.latch);
    }
    if (C.vector) {
        C.calls++;
        wof_song_int();
    }
}

/* VBlank k+1 is about to happen: the events of [T_k, T_k+1) in time order - the channels'
 * cycle ends and timer A's underflows - each delivered, and the output frames of the same
 * span mixed around them.  At an equal instant the channels come first, in channel order,
 * because their interrupt is level 4 and the timer's level 2. */
void wof_paula_boundary(void)
{
    uint64_t from = now();
    uint64_t end  = from + clock_of(P.hz);
    uint64_t mixed = from;

    for (;;) {
        uint64_t best = NEVER, tt = timer_due(end);
        int      which = -1;

        for (int c = 0; c < 4; c++) {
            uint64_t t = cycle_end(c, end);

            if (t < best) {             /* strictly: at equal instants the lower channel */
                best  = t;
                which = c;
            }
        }
        if (tt < best) {
            mix(mixed, tt);
            mixed    = tt;
            event_at = tt;
            in_event = 1;
            timer_underflow(tt);
            wof_paula_deliver();
            in_event = 0;
            continue;
        }
        if (which < 0)
            break;
        mix(mixed, best);
        mixed = best;
        advance(which, best);
        P.ch[which].left = 0;
        P.ch[which].next = best;
        event_at = best;
        in_event = 1;
        restart(which, best);
        wof_paula_deliver();
        in_event = 0;
    }
    mix(mixed, end);
    for (int c = 0; c < 4; c++)
        advance(c, end);
    P.vblanks++;
}

/* The video standard changed (the shell sets it once at start, and its diagnostics overlay
 * can switch it): the units change with it, so what is left of each running channel's
 * current byte is carried over into the new ones, and so is what is left of timer A's
 * count. */
void wof_paula_rate(uint16_t hz)
{
    uint64_t old_now = now(), old_scale = (uint64_t)clock_of(P.hz) * P.hz;
    uint64_t new_scale = (uint64_t)clock_of(hz) * hz;
    uint64_t old_tick = e_tick();

    if (P.hz == hz)
        return;
    P.hz = hz;
    for (int c = 0; c < 4; c++) {
        wof_paula_channel_t *ch = &P.ch[c];
        uint64_t left = ch->next > old_now ? ch->next - old_now : 0;

        if (ch->on)
            ch->next = now() + left * new_scale / old_scale;
    }
    /* A CIA counts E cycles, and the E clock is the colour clock over 5, which differs
     * between the standards (709,379 and 715,909 Hz): the timer's time left is carried over
     * as E cycles, not as seconds, the count unchanged and the underflow's instant
     * recomputed in the new units, e_tick() of them a cycle. */
    if (C.running) {
        uint64_t left = C.next > old_now ? C.next - old_now : 0;

        C.next = now() + left * e_tick() / old_tick;
    }
}

/* ------------------------------------------------------------------ the core's side */

void wof_audio_init(void)
{
    wof_mem_set(&P, 0, sizeof P);
    P.intena = LEVEL4_ON;               /* the system runs with the master bit on */
    P.hz     = wof_s.video_hz;
    wof_mem_set(&C, 0, sizeof C);
    C.latch   = 0xFFFF;                 /* the 8520's state at power-up */
    C.counter = 0xFFFF;
    C.level4  = WOF_L4_SYSTEM;
    queue_head = queue_count = 0;
    song_bytes = 0;                     /* the blob wof_init was given may be another */
    song_size  = 0;
    for (int f = 0; f < 8; f++)
        sound_bytes[f] = 0;
#ifdef WOF_TRACE
    event_count = 0;
#endif
}

/* The frames of emulated time the boundaries have mixed, oldest first, as many as the shell
 * asks for; the rest of its buffer is silence.  Returns how many were emulated time.  A new
 * rate drops what was mixed at the old one. */
uint32_t wof_audio_render(int16_t *stereo, uint32_t frames, uint32_t rate)
{
    uint32_t n;

    if (!stereo)
        return 0;
    if (rate && rate != out_rate) {
        out_rate   = rate;
        queue_head = queue_count = 0;
    }
    n = frames < queue_count ? frames : queue_count;
    for (uint32_t i = 0; i < n; i++) {
        uint32_t at = (queue_head + i) % QUEUE_FRAMES;

        stereo[i * 2]     = queue[at * 2];
        stereo[i * 2 + 1] = queue[at * 2 + 1];
    }
    queue_head   = (queue_head + n) % QUEUE_FRAMES;
    queue_count -= n;
    if (frames > n)
        wof_mem_set(stereo + n * 2, 0, (frames - n) * 2u * sizeof *stereo);
    return n;
}
