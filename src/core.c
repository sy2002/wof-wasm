/* The core's entry points: initialisation, the VBlank clock, one pass of the main program,
 * and save states (SPEC 6.1).
 *
 * M1 ports the loaders, the decoders and the blit, not the game loop.  What runs per pass
 * is therefore still not the original's inner loop:
 *
 *   wof_vblank  will become the port of vblank_server (orig 0x011754) together with
 *               vblank_every_frame (orig 0x01C9CA): the fire-button press timer, the
 *               cancelling of opposing directions, the reversed-vertical option, the input
 *               byte and the six-entry queue.  For now it does only the part that the
 *               shell's clock has to get right from the start, namely the count to four.
 *   wof_pass    will resume the coroutine that the original's main loop becomes (SPEC 6.3)
 *               in M3.  For now it resumes the M1 viewer, which redraws when a key has
 *               changed what is on screen.
 */
#include "wof.h"

wof_state_t wof_s;

/* Every 4th VBlank makes one logic tick: 15 Hz on a 60 Hz machine, 12.5 Hz on a 50 Hz one.
 * The program never asks which it is running on (re/notes/random.md). */
#define VBLANKS_PER_TICK 4u

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
    wof_assets_init();
    wof_viewer_init();
    wof_viewer_pass();
}

void wof_set_video_hz(int hz)
{
    wof_s.video_hz = (uint16_t)(hz == 50 ? 50 : 60);
}

/* raw: bit 0 forward (up), bit 1 back (down), bit 2 right, bit 3 left, bit 4 fire down. */
void wof_vblank(uint8_t raw)
{
    wof_s.raw = (uint16_t)(raw & 0x1Fu);
    wof_s.vblanks++;

    if (++wof_s.vblank_in_tick < VBLANKS_PER_TICK)
        return;

    wof_s.vblank_in_tick = 0;
    wof_s.ticks++;

    /* Placeholder for the logic tick.  One entropy value per tick keeps the picture a
     * function of the seed; the real consumers are the 43 rand_beam call sites. */
    wof_s.noise = wof_entropy_next();
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
    wof_s = in;
    wof_s.view_dirty = 1;             /* the picture follows the state, not the other way */
    wof_viewer_pass();
}

/* The save state is the struct's bytes, so the struct must not grow padding. */
_Static_assert(sizeof(wof_state_t) == 9 * 4 + 8 * 2,
               "wof_state_t has padding: wof_state_save would copy uninitialised bytes");
