/* src/iff.c, lines 220-251 */
/* orig 0x016FF6 - one step of a 16-step fade.
 *
 * Step 15 returns the target.  Otherwise the whole start word is taken and the masked
 * quotient of each component's difference is added into it, blue first, then green, then
 * red.  A falling component adds its negative quotient as a masked two's complement value
 * and therefore carries into the next higher component: 0x005 towards 0 at step 8 gives
 * 0x013.  The hardware ignores bits 12 to 15.  The intermediate colours of every fade-out
 * depend on this, so the arithmetic is kept exactly, including the widths: blue and green
 * divide a 16-bit product with divs.w, red divides the full 32-bit product. */
uint16_t wof_colour_lerp(int16_t step, uint16_t from, uint16_t to)
{
    if (step == 15)
        return to;

    uint16_t r = from;
    int16_t  d;
    int32_t  q;

    d = (int16_t)((int16_t)(to & 0x000F) - (int16_t)(from & 0x000F));
    q = (int32_t)(int16_t)((uint16_t)((int32_t)d * step)) / 15;
    r = (uint16_t)(r + (((uint16_t)q) & 0x000F));

    d = (int16_t)((int16_t)(to & 0x00F0) - (int16_t)(from & 0x00F0));
    q = (int32_t)(int16_t)((uint16_t)((int32_t)d * step)) / 15;
    r = (uint16_t)(r + (((uint16_t)q) & 0x00F0));

    d = (int16_t)((int16_t)(to & 0x0F00) - (int16_t)(from & 0x0F00));
    q = ((int32_t)d * step) / 15;
    r = (uint16_t)(r + (uint16_t)(((uint32_t)q) & 0x0F00));

    return r;
}
