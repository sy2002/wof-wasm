/* The core's entry points: initialisation, the VBlank clock, one pass of the main program,
 * and save states (SPEC 6.1).
 *
 * wof_vblank is the port of vblank_server (orig 0x011754) with vblank_every_frame (orig
 * 0x01C9CA) and lives in src/input.c, beside the rest of the sampling chain.  wof_pass
 * resumes the coroutine that the original's main loop becomes (SPEC 6.3); until the front
 * end takes it over it resumes the M1 viewer, which redraws when a key changed the page.
 */
#include "wof.h"

wof_state_t wof_s;

void wof_init(uint32_t seed, const uint8_t *fs, uint32_t fs_len)
{
    wof_mem_set(&wof_s, 0, sizeof wof_s);
    wof_s.magic    = WOF_STATE_MAGIC;
    wof_s.version  = WOF_STATE_VERSION;
    wof_s.seed     = seed;
    wof_s.video_hz = 60;

    wof_globals_from_image();
    wof_entropy_seed(seed);
    wof_fs_open(fs, fs_len);
    wof_fs_writes_reset();
    wof_video_init();
    wof_display_init();
    wof_audio_init();
    wof_input_init();
    wof_keys_init();
    wof_assets_init();
    wof_front_init();

    /* The original runs from its first instruction to its first wait before any VBlank
     * happens, so the port does too: wof_init leaves the coroutine parked at the wait
     * inside display_init, and pass N then runs what the original runs after VBlank N. */
    wof_front();
    wof_screen_from_front_view();
}

void wof_set_video_hz(int hz)
{
    wof_s.video_hz = (uint16_t)(hz == 50 ? 50 : 60);
    wof_paula_rate(wof_s.video_hz);
}

/* One resume of the coroutine the original's main program becomes (SPEC 6.3), and the
 * picture that follows from where it now stands. */
void wof_pass(void)
{
    wof_s.passes++;
    wof_front();
    wof_screen_from_front_view();
}

uint32_t wof_vblank_count(void) { return wof_s.vblanks; }
uint32_t wof_tick_count(void)   { return wof_s.ticks; }
uint32_t wof_pass_count(void)   { return wof_s.passes; }

/* Save states carry no host pointers (SPEC 7.2) because wof_s holds no pointers: the file
 * blob, the loaded assets and the framebuffer live outside it, and wof_pass rebuilds the
 * picture from it.  The assets are read-only after wof_init, so leaving them out of the
 * state is not a gap; the one thing that is written after load, the mirror marker of a
 * hellcat or Torpedo record, is in the state since M4 (marker_hellcat, marker_torpedo)
 * and follows a load. */
uint32_t wof_state_size(void)
{
    return (uint32_t)sizeof(wof_state_t);
}

void wof_state_save(uint8_t *dst)
{
    if (dst)
        wof_mem_copy(dst, &wof_s, sizeof wof_s);
}

void wof_state_load(const uint8_t *src)
{
    wof_state_t in;

    if (!src)
        return;
    wof_mem_copy(&in, src, sizeof in);
    if (in.magic != WOF_STATE_MAGIC || in.version != WOF_STATE_VERSION)
        return;                       /* not ours: leave the running state alone */
    wof_mem_copy(&wof_s, &in, sizeof wof_s);
    wof_assets_follow_state();        /* the mirrored shapes follow their markers */
    wof_draw_restore();
    wof_screen_from_front_view();     /* the picture follows the state, not the other way */
}

/* The state travels as the struct's bytes, which is why it is copied with wof_mem_copy
 * rather than assigned: a struct assignment need not carry the padding between members,
 * and since the front end's globals moved into the struct (src/globals.def) it has some.
 * wof_init zeroes the whole struct, so the padding is deterministic and the round trip is
 * exact; tests/test_core_native.py holds it to that.  The registry's own claim, that the
 * globals struct is the sum of its members, is checked in tests/test_oracle_m3.py. */

/* ------------------------------------------------------------- the registered globals */

/* Every entry of src/globals.def and src/mission.def whose address lies in the initialised
 * part of the DATA hunk starts with the original's value, converted from big-endian.  The
 * image is the executable's own, taken at build time (re/tables.toml, data_image).  A
 * table's shape pointers and pool pointers start as none, which is what the original's
 * zero longs there are. */
#include "gen/tables.h"

static uint32_t image_value(uint32_t addr, uint32_t size)
{
    uint32_t v = 0;

    for (uint32_t b = 0; b < size; b++) {
        uint32_t at = addr + b - 0x023000u;

        v = (v << 8) | (at < sizeof wof_tbl_data_image ? wof_tbl_data_image[at] : 0u);
    }
    return v;
}

static void store(void *dst, uint32_t size, uint32_t v)
{
    uint8_t *d = (uint8_t *)dst;

    for (uint32_t b = 0; b < size; b++)               /* host order, both targets little */
        d[b] = (uint8_t)(v >> (8 * b));
}

void wof_globals_from_image(void)
{
#define WOF_GLOBAL(n, t, a)                                                            \
    store(&wof_g.n, (uint32_t)sizeof(t), image_value((uint32_t)(a), (uint32_t)sizeof(t)));
#define WOF_GLOBAL_ARRAY(n, t, c, a)                                                   \
    for (uint32_t i = 0; i < (uint32_t)(c); i++)                                       \
        store(&wof_g.n[i], (uint32_t)sizeof(t),                                        \
              image_value((uint32_t)(a) + i * (uint32_t)sizeof(t), (uint32_t)sizeof(t)));
#include "globals.def"
#undef WOF_GLOBAL
#undef WOF_GLOBAL_ARRAY
}

/* The byte at an original address as the original's memory would hold it, big-endian,
 * when a registered global covers the address.  Returns 0 when none does. */
static int byte_of(const void *p, uint32_t size, uint32_t count, uint32_t base,
                   uint32_t addr, uint8_t *out)
{
    uint32_t at;

    if (addr < base || addr - base >= size * count)
        return 0;
    at = addr - base;
    *out = ((const uint8_t *)p)[(at / size) * size + (size - 1u - at % size)];
    return 1;
}

int wof_global_byte(uint32_t addr, uint8_t *out)
{
#define WOF_GLOBAL(n, t, a)                                                            \
    if (byte_of(&wof_g.n, (uint32_t)sizeof(t), 1u, (uint32_t)(a), addr, out))         \
        return 1;
#define WOF_GLOBAL_ARRAY(n, t, c, a)                                                   \
    if (byte_of(wof_g.n, (uint32_t)sizeof(t), (uint32_t)(c), (uint32_t)(a), addr, out)) \
        return 1;
#include "globals.def"
#undef WOF_GLOBAL
#undef WOF_GLOBAL_ARRAY
    return 0;
}

/* The records of src/records.def by number, with the original's size of each. */
enum {
#define WOF_RECORD(r, size)                 rec_##r,
#define WOF_FIELD(r, n, t, off, k)
#define WOF_FIELD_ARRAY(r, n, t, c, off, k)
#define WOF_RECORD_END(r)
#include "records.def"
    rec_count
};
static const uint32_t record_size[rec_count] = {
#undef WOF_RECORD
#define WOF_RECORD(r, size)                 (uint32_t)(size),
#include "records.def"
};
#undef WOF_RECORD
#undef WOF_FIELD
#undef WOF_FIELD_ARRAY
#undef WOF_RECORD_END

/* The byte of the port's struct that holds byte `off` of an original record: the plain
 * field that covers it, big-endian in the original.  -1 where none does (a gap, or a
 * pointer the port keeps as a handle). */
static int32_t record_byte(int rec, uint32_t off)
{
    switch (rec) {
#define WOF_RECORD(r, size)                 case rec_##r:
#define WOF_FIELD(r, n, t, o, k)                                                       \
        if ((k) == WOF_K_PLAIN && off - (uint32_t)(o) < (uint32_t)sizeof(t))           \
            return (int32_t)(offsetof(wof_##r##_t, n) + sizeof(t) - 1u - (off - (uint32_t)(o)));
#define WOF_FIELD_ARRAY(r, n, t, c, o, k)                                              \
        if ((k) == WOF_K_PLAIN && off - (uint32_t)(o) < (uint32_t)(sizeof(t) * (c)))   \
            return (int32_t)(offsetof(wof_##r##_t, n) +                                \
                             ((off - (uint32_t)(o)) / sizeof(t)) * sizeof(t) +         \
                             sizeof(t) - 1u - (off - (uint32_t)(o)) % sizeof(t));
#define WOF_RECORD_END(r)                   return -1;
#include "records.def"
#undef WOF_RECORD
#undef WOF_FIELD
#undef WOF_FIELD_ARRAY
#undef WOF_RECORD_END
    default:
        return -1;
    }
}

/* A byte stored at an original address, into the registered global or the table at a
 * fixed address that covers it, as the original's move to that address would.  Returns 0
 * where nothing the port keeps covers the address. */
int wof_original_store8(uint32_t addr, uint8_t value)
{
#define WOF_GLOBAL(n, t, a)                                                            \
    if (addr - (uint32_t)(a) < (uint32_t)sizeof(t)) {                                  \
        ((uint8_t *)&wof_g.n)[sizeof(t) - 1u - (addr - (uint32_t)(a))] = value;        \
        return 1;                                                                      \
    }
#define WOF_GLOBAL_ARRAY(n, t, c, a)                                                   \
    if (addr - (uint32_t)(a) < (uint32_t)(sizeof(t) * (c))) {                          \
        uint32_t at_ = addr - (uint32_t)(a);                                           \
        ((uint8_t *)wof_g.n)[(at_ / sizeof(t)) * sizeof(t) + sizeof(t) - 1u - at_ % sizeof(t)] = value; \
        return 1;                                                                      \
    }
#include "globals.def"
#undef WOF_GLOBAL
#undef WOF_GLOBAL_ARRAY
#define WOF_TABLE(n, r, c, a)                                                          \
    if (addr - (uint32_t)(a) < record_size[rec_##r] * (uint32_t)(c)) {                 \
        uint32_t at_ = addr - (uint32_t)(a);                                           \
        int32_t  b_  = record_byte(rec_##r, at_ % record_size[rec_##r]);               \
                                                                                       \
        if (b_ < 0)                                                                    \
            return 0;                                                                  \
        ((uint8_t *)&wof_m.n[at_ / record_size[rec_##r]])[b_] = value;                 \
        return 1;                                                                      \
    }
#define WOF_POOL(n, r, c, p)
#include "mission.def"
#undef WOF_TABLE
#undef WOF_POOL
    return 0;
}

void wof_original_store16(uint32_t addr, uint16_t value)
{
    wof_original_store8(addr, (uint8_t)(value >> 8));
    wof_original_store8(addr + 1u, (uint8_t)value);
}

/* Byte `off` of a record as the original's memory holds it: a plain field's, big-endian;
 * a pointer's as a long of what the port keeps in its place, the shape handle or the pool's
 * flag, because the original's address exists only in its own memory
 * (re/notes/campaign.md, "What the port writes in the raw part").  Returns 0 in a gap. */
static int record_read(int rec, const uint8_t *port, uint32_t off, uint8_t *out)
{
    switch (rec) {
#define WOF_RECORD(r, size)                 case rec_##r:
#define WOF_FIELD(r, n, t, o, k)                                                       \
        if ((k) == WOF_K_PLAIN && off - (uint32_t)(o) < (uint32_t)sizeof(t)) {         \
            *out = port[offsetof(wof_##r##_t, n) + sizeof(t) - 1u - (off - (uint32_t)(o))]; \
            return 1;                                                                  \
        }                                                                              \
        if ((k) != WOF_K_PLAIN && off - (uint32_t)(o) < 4u) {                          \
            t v_;                                                                      \
                                                                                       \
            wof_mem_copy(&v_, port + offsetof(wof_##r##_t, n), (uint32_t)sizeof v_);   \
            *out = (uint8_t)((uint32_t)v_ >> (8u * (3u - (off - (uint32_t)(o)))));     \
            return 1;                                                                  \
        }
#define WOF_FIELD_ARRAY(r, n, t, c, o, k)                                              \
        if ((k) == WOF_K_PLAIN && off - (uint32_t)(o) < (uint32_t)(sizeof(t) * (c))) { \
            *out = port[offsetof(wof_##r##_t, n) +                                     \
                        ((off - (uint32_t)(o)) / sizeof(t)) * sizeof(t) +              \
                        sizeof(t) - 1u - (off - (uint32_t)(o)) % sizeof(t)];           \
            return 1;                                                                  \
        }
#define WOF_RECORD_END(r)                   return 0;
#include "records.def"
#undef WOF_RECORD
#undef WOF_FIELD
#undef WOF_FIELD_ARRAY
#undef WOF_RECORD_END
    default:
        return 0;
    }
}

/* The byte at an original address as the original's memory would hold it, from the
 * registered global or the table at a fixed address that covers it (record_read).  Returns
 * 0 where nothing the port keeps covers the address. */
int wof_original_load8(uint32_t addr, uint8_t *out)
{
    if (wof_global_byte(addr, out))
        return 1;
#define WOF_TABLE(n, r, c, a)                                                          \
    if (addr - (uint32_t)(a) < record_size[rec_##r] * (uint32_t)(c)) {                 \
        uint32_t at_ = addr - (uint32_t)(a);                                           \
                                                                                       \
        return record_read(rec_##r, (const uint8_t *)&wof_m.n[at_ / record_size[rec_##r]], \
                           at_ % record_size[rec_##r], out);                           \
    }
#define WOF_POOL(n, r, c, p)
#include "mission.def"
#undef WOF_TABLE
#undef WOF_POOL
    return 0;
}

/* Byte `off` of the allocation whose pointer the original keeps at `pointer`, as the
 * original's memory holds it: big-endian by the pool's record layout.  Returns 0 past the
 * port's capacity and for a pointer the port keeps no pool behind. */
int wof_pool_load8(uint32_t pointer, uint32_t off, uint8_t *out)
{
#define WOF_TABLE(n, r, c, a)
#define WOF_POOL(n, r, c, p)                                                           \
    if (pointer == (uint32_t)(p) && off < record_size[rec_##r] * (uint32_t)(c))        \
        return record_read(rec_##r, (const uint8_t *)&wof_m.n[off / record_size[rec_##r]], \
                           off % record_size[rec_##r], out);
#include "mission.def"
#undef WOF_TABLE
#undef WOF_POOL
    return 0;
}

/* The capacity in bytes of the pool the port keeps behind the pointer at `pointer`, as the
 * original's layout counts it; 0 where it keeps none (M7 part 2: a saved game that asks for
 * more than the port holds is refused, re/notes/campaign.md). */
uint32_t wof_pool_capacity(uint32_t pointer)
{
#define WOF_TABLE(n, r, c, a)
#define WOF_POOL(n, r, c, p)                                                           \
    if (pointer == (uint32_t)(p))                                                      \
        return record_size[rec_##r] * (uint32_t)(c);
#include "mission.def"
#undef WOF_TABLE
#undef WOF_POOL
    return 0;
}

/* The pool behind the pointer at `pointer` zeroed, as the original's allocator hands a new
 * block out (MEMF_CLEAR, SPEC 7.2).  Returns 0 where the port keeps no pool there. */
int wof_pool_zero(uint32_t pointer)
{
#define WOF_TABLE(n, r, c, a)
#define WOF_POOL(n, r, c, p)                                                           \
    if (pointer == (uint32_t)(p)) {                                                    \
        wof_mem_set(wof_m.n, 0, sizeof wof_m.n);                                       \
        return 1;                                                                      \
    }
#include "mission.def"
#undef WOF_TABLE
#undef WOF_POOL
    return 0;
}

/* Byte `off` of the allocation whose pointer the original keeps at `pointer`, stored as the
 * original's move into that block would store it: into the plain field that covers it.
 * Returns 0 past the capacity, in a gap and on a pointer field, which the port derives
 * instead (M7 part 2, the loader). */
int wof_pool_store8(uint32_t pointer, uint32_t off, uint8_t value)
{
#define WOF_TABLE(n, r, c, a)
#define WOF_POOL(n, r, c, p)                                                           \
    if (pointer == (uint32_t)(p) && off < record_size[rec_##r] * (uint32_t)(c)) {      \
        int32_t b_ = record_byte(rec_##r, off % record_size[rec_##r]);                 \
                                                                                       \
        if (b_ < 0)                                                                    \
            return 0;                                                                  \
        ((uint8_t *)&wof_m.n[off / record_size[rec_##r]])[b_] = value;                 \
        return 1;                                                                      \
    }
#include "mission.def"
#undef WOF_TABLE
#undef WOF_POOL
    return 0;
}

/* ------------------------------------------------------- the music's memory (M8 part 2) */

static uint32_t image_long(const uint8_t *p)
{
    return (uint32_t)p[0] << 24 | (uint32_t)p[1] << 16 | (uint32_t)p[2] << 8 | p[3];
}

/* A record as LoadSeg leaves it in a hunk: a plain field takes the file's bytes; a pointer
 * into the song data its offset, which is the long as the file holds it, because the song
 * data's pointers are relocated to its own hunk (re/notes/music.md); a pointer the port
 * keeps as a flag whether it is set.  The player's DATA hunk holds no vector yet. */
static void record_load(int rec, uint8_t *dst, const uint8_t *src)
{
    for (uint32_t off = 0; off < record_size[rec]; off++) {
        int32_t b = record_byte(rec, off);

        if (b >= 0)
            dst[b] = src[off];
    }
    switch (rec) {
#define WOF_RECORD(r, size)                 case rec_##r:
#define WOF_FIELD(r, n, t, o, k)                                                       \
        if ((k) == WOF_K_SONG || (k) == WOF_K_POOL) {                                  \
            uint32_t v_ = image_long(src + (o));                                       \
            t        f_ = (t)((k) == WOF_K_POOL ? (v_ != 0u) : v_);                    \
            wof_mem_copy(dst + offsetof(wof_##r##_t, n), &f_, (uint32_t)sizeof f_);    \
        }
#define WOF_FIELD_ARRAY(r, n, t, c, o, k)                                              \
        if ((k) == WOF_K_POOL)                                                         \
            for (uint32_t i_ = 0; i_ < (uint32_t)(c); i_++) {                          \
                t f_ = (t)(image_long(src + (o) + 4u * i_) != 0u);                     \
                wof_mem_copy(dst + offsetof(wof_##r##_t, n) + i_ * sizeof(t), &f_,     \
                             (uint32_t)sizeof f_);                                     \
            }
#define WOF_RECORD_END(r)                   break;
#include "records.def"
#undef WOF_RECORD
#undef WOF_FIELD
#undef WOF_FIELD_ARRAY
#undef WOF_RECORD_END
    default:
        break;
    }
}

/* LoadSeg of songplay and wofsongs as far as the port keeps them: the parts of the player's
 * DATA hunk that change, from its image, and the seven voices of the song data, from the
 * file (src/mission.def). */
void wof_music_memory_load(const uint8_t *player, const uint8_t *songs)
{
    record_load(rec_plhead, (uint8_t *)&wof_m.player_head[0], player + WOF_PLAYER_HEAD);
    record_load(rec_plvars, (uint8_t *)&wof_m.player_vars[0], player + WOF_PLAYER_VARS);
    for (uint32_t t = 0; t < 4; t++)
        record_load(rec_track, (uint8_t *)&wof_m.player_tracks[t],
                    player + WOF_PLAYER_TRACKS + t * record_size[rec_track]);
    record_load(rec_plsong, (uint8_t *)&wof_m.player_song[0], player + WOF_PLAYER_SONG);
    for (uint32_t n = 0; n < WOF_VOICES; n++)
        record_load(rec_voice, (uint8_t *)&wof_m.song_voices[n],
                    songs + WOF_VOICES_AT + n * record_size[rec_voice]);
}

/* UnLoadSeg of both: nothing of either is left. */
void wof_music_memory_free(void)
{
    wof_mem_set(wof_m.player_head, 0, (uint32_t)sizeof wof_m.player_head);
    wof_mem_set(wof_m.player_vars, 0, (uint32_t)sizeof wof_m.player_vars);
    wof_mem_set(wof_m.player_tracks, 0, (uint32_t)sizeof wof_m.player_tracks);
    wof_mem_set(wof_m.player_song, 0, (uint32_t)sizeof wof_m.player_song);
    wof_mem_set(wof_m.song_voices, 0, (uint32_t)sizeof wof_m.song_voices);
}

/* ------------------------------------------------------------------ marked stand-ins */

uint32_t wof_standin_hits(void)
{
    return wof_s.standin_hits;
}

void wof_standin(const char *marker)
{
    wof_s.standin_hits++;
    wof_trace_standin(marker);
}

/* ------------------------------------------------------------- VBlanks per pass (6.2) */

/* How many VBlanks a pass takes (SPEC 10, point 2): 2, measured on the owner's PAL Amiga by
 * a film at 240 frames a second in a quiet scene (re/notes/passes.md), kept a setting like the
 * fade's so that the tests can run other rates.  A pass begins only when this many VBlanks
 * have happened since the previous one began and vblank_flag is set (re/notes/headless.md). */
static uint16_t vblanks_per_pass = 2;

void wof_set_vblanks_per_pass(int n)
{
    vblanks_per_pass = (uint16_t)(n < 1 ? 1 : n > 16 ? 16 : n);
}

int wof_vblanks_per_pass(void)
{
    return vblanks_per_pass;
}
