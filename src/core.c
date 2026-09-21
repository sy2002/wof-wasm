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
 * hellcat or Torpedo record, arrives with the flight model in M4 and has to join the
 * state then. */
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

/* PROVISIONAL (SPEC 10, point 2): how many VBlanks a pass takes.  The owner measures it on
 * the machine; until then it is a setting, like the fade's.  A pass begins only when this
 * many VBlanks have happened since the previous one began and vblank_flag is set, which is
 * the headless original's scheduling rule (re/notes/headless.md). */
static uint16_t vblanks_per_pass = 2;

void wof_set_vblanks_per_pass(int n)
{
    vblanks_per_pass = (uint16_t)(n < 1 ? 1 : n > 16 ? 16 : n);
}

int wof_vblanks_per_pass(void)
{
    return vblanks_per_pass;
}
