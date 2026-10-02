/* src/draw.c, lines 192-213, a part of shape_blit (lines 157-213) */
    uint8_t M     = target.mask;
    uint8_t clr   = (uint8_t)(s->clear & M);
    uint8_t st    = (uint8_t)(s->set & M);
    uint8_t un    = (uint8_t)(s->union_mask & M);
    uint8_t keep  = (uint8_t)~(clr | st | un);
    uint8_t force = (uint8_t)(st & ~un);

    /* A shape that stores no plane has no pixels at all (8thscale's `bchm` is the one on
     * the disk).  It still paints its clear and set bytes over its box, opaquely. */
    for (int32_t r = sy0; r < sy1; r++) {
        const uint8_t *src = s->pixels ? s->pixels + (uint32_t)r * w : 0;
        uint8_t       *dst = target.pixels + (int32_t)(y0 + r) * target.stride + x0;

        for (int32_t c = sx0; c < sx1; c++) {
            uint8_t p = src ? src[c] : 0;

            if (useMask && !p)
                continue;
            dst[c] = (uint8_t)((dst[c] & keep) | force | (p & un));
        }
    }
}
