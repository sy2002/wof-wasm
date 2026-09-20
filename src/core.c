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

    wof_entropy_seed(seed);
    wof_fs_open(fs, fs_len);
    wof_video_init();
    wof_audio_init();
    wof_input_init();
    wof_keys_init();
    wof_assets_init();
    wof_viewer_init();
    wof_viewer_pass();
}

void wof_set_video_hz(int hz)
{
    wof_s.video_hz = (uint16_t)(hz == 50 ? 50 : 60);
}

void wof_pass(void)
{
    wof_s.passes++;
    wof_viewer_pass();
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
    wof_s.view_dirty = 1;             /* the picture follows the state, not the other way */
    wof_viewer_pass();
}

/* The state travels as the struct's bytes, which is why it is copied with wof_mem_copy
 * rather than assigned: a struct assignment need not carry the padding between members,
 * and since the front end's globals moved into the struct (src/globals.def) it has some.
 * wof_init zeroes the whole struct, so the padding is deterministic and the round trip is
 * exact; tests/test_core_native.py holds it to that.  The registry's own claim, that the
 * globals struct is the sum of its members, is checked in tests/test_oracle_m3.py. */
