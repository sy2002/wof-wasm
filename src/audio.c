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

static uint32_t clock_of(uint16_t hz)
{
    return hz == 50 ? PAL_CLOCK : NTSC_CLOCK;
}

/* ------------------------------------------------------------------ the samples */

/* The eight effects, where the file system blob holds them.  Not state: the blob is the same
 * for the whole session, and a handle names a file by its index in sound_files. */
static const uint8_t *sound_bytes[8];
static uint32_t       sound_size[8];

const int8_t *wof_sound_data(uint32_t handle, uint32_t *left)
{
    int      file = WOF_SOUND_FILE(handle);
    uint32_t off  = WOF_SOUND_OFFSET(handle);

    *left = 0;
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

/* The level-4 handler while a request is deliverable: audio_irq once sound_init has put it
 * at the autovector, the system's before that, which clears what it is given. */
void wof_paula_deliver(void)
{
    for (int rounds = 0; deliverable() && rounds < 8; rounds++) {
        P.irqs++;
        if (wof_g.sound_installed)
            wof_audio_irq();
        else
            P.intreq = (uint16_t)(P.intreq & ~AUDIO_BITS);
    }
}

/* VBlank k+1 is about to happen: the channel events of [T_k, T_k+1) in time order, each
 * delivered, and the output frames of the same span mixed around them. */
void wof_paula_boundary(void)
{
    uint64_t from = now();
    uint64_t end  = from + clock_of(P.hz);
    uint64_t mixed = from;

    for (;;) {
        uint64_t best = NEVER;
        int      which = -1;

        for (int c = 0; c < 4; c++) {
            uint64_t t = cycle_end(c, end);

            if (t < best) {             /* strictly: at equal instants the lower channel */
                best  = t;
                which = c;
            }
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
 * current byte is carried over into the new ones. */
void wof_paula_rate(uint16_t hz)
{
    uint64_t old_now = now(), old_scale = (uint64_t)clock_of(P.hz) * P.hz;
    uint64_t new_scale = (uint64_t)clock_of(hz) * hz;

    if (P.hz == hz)
        return;
    P.hz = hz;
    for (int c = 0; c < 4; c++) {
        wof_paula_channel_t *ch = &P.ch[c];
        uint64_t left = ch->next > old_now ? ch->next - old_now : 0;

        if (ch->on)
            ch->next = now() + left * new_scale / old_scale;
    }
}

/* ------------------------------------------------------------------ the core's side */

void wof_audio_init(void)
{
    wof_mem_set(&P, 0, sizeof P);
    P.intena = LEVEL4_ON;               /* the system runs with the master bit on */
    P.hz     = wof_s.video_hz;
    queue_head = queue_count = 0;
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
