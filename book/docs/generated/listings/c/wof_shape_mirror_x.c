/* src/shapes.c, lines 202-230 */
/* orig 0x015B58 - mirrors a shape in place and turns its hotspot round.
 *
 * The original reverses the bytes of every stored plane row and the bits inside each byte
 * through bit_reverse_table; on indexed pixels that is one row reversal, because a pixel
 * carries the bits of all planes at once.  It swaps byte pairs from both ends, so the
 * middle byte of an odd byte width would stay unreversed - every width in the files is
 * even, which the oracle test relies on as much as the original does.  A null record
 * returns at once. */
void wof_shape_mirror_x(wof_shape_t *s)
{
    if (!s)
        return;

    s->hot_x = (int16_t)(s->wbytes * 8 - 1 - s->hot_x);

    if (!s->pixels)
        return;

    uint32_t w = (uint32_t)s->wbytes * 8u;

    for (uint32_t y = 0; y < s->height; y++) {
        uint8_t *row = s->pixels + y * w;
        for (uint32_t i = 0, j = w - 1; i < j; i++, j--) {
            uint8_t t = row[i];
            row[i] = row[j];
            row[j] = t;
        }
    }
}
