/* src/load.c, lines 18-48 */
/* orig 0x01FEE0 - signed-byte RLE.  A control byte below 0 copies -c literals (0x80 means
 * 128), one of 0 or above repeats the next byte c + 1 times.  The original writes until
 * the source is exhausted and ignores the declared size, which is why two files on the
 * disk produce one byte more than declared; here the write stops at dstlen, because the
 * buffer is exactly that big and the declared size is what the callers go by. */
void wof_rpck_unpack(const uint8_t *src, uint32_t srclen, uint8_t *dst, uint32_t dstlen)
{
    uint32_t i = 0, o = 0;

    while (i < srclen) {
        int8_t c = (int8_t)src[i++];

        if (c < 0) {
            uint32_t n = (uint32_t)(-(int32_t)c);
            while (n-- && i < srclen) {
                if (o < dstlen)
                    dst[o] = src[i];
                o++;
                i++;
            }
        } else {
            uint32_t n = (uint32_t)c + 1;
            uint8_t  v = i < srclen ? src[i++] : 0;
            while (n--) {
                if (o < dstlen)
                    dst[o] = v;
                o++;
            }
        }
    }
}
