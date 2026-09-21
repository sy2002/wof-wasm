/* The entropy stream of SPEC 7.3 and re/notes/random.md.
 *
 * The original's only random source, rand_beam (0x0203BE), exclusive-ors a constant with
 * the raster beam position, so all its variation comes from CPU timing.  A port cannot
 * reproduce that and does not need to: the core consumes one value per rand_beam call from
 * an explicit stream shaped like a real VHPOSR read, seeded by wof_init.  With the stream
 * fixed the port is deterministic, and the headless original of M2 is hooked to serve the
 * same values, which turns any divergence in call order into a visible state mismatch.
 *
 * rand_beam itself is at the end of this file. */
#include "wof.h"

/* Numerical Recipes' LCG constants.  The generator only has to be cheap, reproducible and
 * free of short cycles in the bits that are used; it is not part of the original. */
#define ENTROPY_MUL 1664525u
#define ENTROPY_ADD 1013904223u

void wof_entropy_seed(uint32_t seed)
{
    wof_s.entropy = seed;
}

/* VHPOSR shape: high byte the low 8 bits of the vertical position, low byte the horizontal
 * position in units of two low-resolution pixels, 0 to 0xE3.  The modulo biases the low
 * byte by less than half a percent, which is far below the resolution of anything the game
 * does with the value. */
uint16_t wof_entropy_next(void)
{
    wof_s.entropy = wof_s.entropy * ENTROPY_MUL + ENTROPY_ADD;

    uint32_t v  = wof_s.entropy;
    uint32_t hi = (v >> 24) & 0xFFu;
    uint32_t lo = ((v >> 8) & 0xFFFFu) % 0xE4u;

    return (uint16_t)((hi << 8) | lo);
}

/* orig 0x0203BE rand_beam - the game's only random source (re/notes/random.md): a constant
 * derived from rand_seed_const, exclusive-ored in its low word with the beam position,
 * which the port takes from the entropy stream.  The result is the whole long in D0, whose
 * high word is the constant's; every caller the five mission scripts reach uses the low
 * word, and the callers that shift or rotate it say so where they do.  `caller` is the
 * original address of the routine that calls it, which the comparison with the harness's
 * entropy log needs (test builds record it). */
uint32_t wof_rand_beam(uint32_t caller)
{
    int32_t  v    = (int32_t)(int16_t)wof_g.rand_seed_const * 0x1AFB + 0x1FCCD;
    uint16_t beam = wof_entropy_next();

    v = (int32_t)(((uint32_t)v & 0xFFFF0000u) | (uint16_t)((uint16_t)v ^ beam));
    wof_g.rand_state = (uint16_t)v;
    wof_trace_add("rand_beam", beam, (uint16_t)v, (int32_t)caller, 0, 0, 0);
    (void)caller;
    return (uint32_t)v;
}
