/* src/shapes.c, lines 32-48 */
/* orig 0x020560 - A0 = container, D0 = the name as a big-endian long.  A linear scan that
 * stops at the first stored name greater than or equal to the wanted one, so it needs the
 * ascending order that all thirteen containers on the disk have.  The port keeps the early
 * exit: the result is the same as an exact-match lookup, and the oracle test compares it
 * against the original for every name of every list. */
int16_t wof_shape_find(const wof_container_t *c, uint32_t name)
{
    if (!c || (int16_t)c->count <= 0)
        return WOF_NO_SHAPE;

    for (uint16_t i = 0; i < c->count; i++) {
        if (c->names[i] >= name)
            return c->names[i] == name ? (int16_t)i : WOF_NO_SHAPE;
    }
    /* Ran past the end: the original then re-tests the last entry, which cannot match. */
    return WOF_NO_SHAPE;
}
