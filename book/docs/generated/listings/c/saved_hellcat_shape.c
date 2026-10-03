/* src/dialog.c, lines 353-394 */
/* The shape of hellcat.shp that a pointer of the saving machine names (0x02541A): the
 * pointer is the long the file holds, `player` the player's shape pointer beside it, whose
 * shape the frame name gives.  In the port's own file both are shape handles, and the
 * handle is taken when it names a shape of hellcat.shp.  In a machine's file both are
 * addresses of that machine's memory: the player's pointer and its shape's place in the
 * container (6 + 8 x count + the record's offset, as load_file leaves a PPkc file) give the
 * container's address there, and the pointer's distance from it gives the record it names.
 * Anything else names no shape. */
static uint16_t saved_hellcat_shape(uint32_t pointer, uint32_t player, uint32_t frame)
{
    const wof_container_t *c = &wof_assets.c[WOF_C_HELLCAT];
    uint32_t               mark, len = 0, base, at;
    const uint8_t         *file;
    uint16_t               count, found = WOF_SHAPE_NONE;
    int16_t                own;

    if (pointer == 0)
        return WOF_SHAPE_NONE;
    if (pointer < 0x10000u || player < 0x10000u) {
        if (pointer >= 0x10000u || (pointer >> 11) != (uint32_t)WOF_C_HELLCAT + 1u ||
            (pointer & 0x7FFu) >= c->count)
            return WOF_SHAPE_NONE;
        return (uint16_t)pointer;
    }
    own = wof_shape_find(c, frame);
    if (own < 0)
        return WOF_SHAPE_NONE;
    mark = wof_arena_mark();
    file = wof_load_file(c->file, &len);
    if (file && len >= 6 && file_long(file) == 0x50506B63u) {            /* 'PPkc' */
        count = (uint16_t)(file[4] << 8 | file[5]);
        at    = 6u + 4u * count;                                         /* the offsets */
        if (len >= at + 4u * count && (uint16_t)own < count) {
            base = player - (6u + 8u * count + file_long(file + at + 4u * (uint32_t)own));
            for (uint16_t i = 0; i < count; i++)
                if (base + 6u + 8u * count + file_long(file + at + 4u * i) == pointer)
                    found = wof_shape_handle(WOF_C_HELLCAT, (int16_t)i);
        }
    }
    wof_arena_release(mark);
    return found;
}
