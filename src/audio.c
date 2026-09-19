/* Audio.  SPEC 6.5 puts a four-channel Paula model here, fed by the ported sound-effect
 * engine and the songplay player; that is milestone M8.
 *
 * M0 renders a test tone instead, so that the whole path - core to shell to AudioWorklet to
 * speakers - is proven before anything depends on it.  Two triangle waves, a fifth apart,
 * one per output channel, so a silent or mis-wired channel is audible as such.  Holding
 * fire raises both by an octave, which proves the input path reaches the core as well.
 *
 * Integer only, and a function of the core's own state: the same state renders the same
 * samples at the same rate, whatever the shell's buffering does. */
#include "wof.h"

#define TONE_LEFT_HZ   440u
#define TONE_RIGHT_HZ  660u
#define TONE_SHIFT     3        /* amplitude 1/8 of full scale */

/* Phase turns once per cycle over the full 32-bit range, so the step is exact enough at
 * every sample rate: 440 Hz at 48 kHz is off by less than a millihertz. */
static uint32_t phase_step(uint32_t hz, uint32_t rate)
{
    if (rate == 0)
        return 0;
    return (uint32_t)(((uint64_t)hz << 32) / rate);
}

/* Triangle from the top 16 bits of the phase: -32768 at the start of the cycle, +32767 in
 * the middle, back down.  No table and no floating point. */
static int32_t triangle(uint32_t phase)
{
    int32_t q = (int32_t)(phase >> 16);

    return q < 32768 ? q * 2 - 32768 : 98303 - q * 2;
}

void wof_audio_init(void)
{
    wof_s.tone_phase_l = 0;
    wof_s.tone_phase_r = 0;
}

void wof_audio_render(int16_t *stereo, uint32_t frames, uint32_t rate)
{
    if (!stereo)
        return;
    if (rate == 0) {
        wof_mem_set(stereo, 0, frames * 2u * sizeof *stereo);
        return;
    }

    uint32_t octave = (wof_s.raw >> 4) & 1;                 /* fire held: one octave up */
    uint32_t step_l = phase_step(TONE_LEFT_HZ  << octave, rate);
    uint32_t step_r = phase_step(TONE_RIGHT_HZ << octave, rate);

    for (uint32_t i = 0; i < frames; i++) {
        stereo[i * 2 + 0] = (int16_t)(triangle(wof_s.tone_phase_l) >> TONE_SHIFT);
        stereo[i * 2 + 1] = (int16_t)(triangle(wof_s.tone_phase_r) >> TONE_SHIFT);
        wof_s.tone_phase_l += step_l;
        wof_s.tone_phase_r += step_r;
    }
}
