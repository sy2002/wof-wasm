/* The entropy stream of SPEC 7.3 and re/notes/random.md.
 *
 * The original's only random source, rand_beam (0x0203BE), exclusive-ors a constant with
 * the raster beam position, so all its variation comes from CPU timing.  A port cannot
 * reproduce that and does not need to: the core consumes one value per rand_beam call from
 * an explicit stream shaped like a real VHPOSR read, seeded by wof_init.  With the stream
 * fixed the port is deterministic, and the headless original of M2 is hooked to serve the
 * same values, which turns any divergence in call order into a visible state mismatch.
 *
 * rand_beam itself is not ported yet; this is only its input side. */
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
