/* src/fs.c, lines 460-485 */
/* ------------------------------------------------- the game's own directory, in order
 *
 * ExNext walks a directory in the file system's own order: chain 0 upward, and inside a
 * chain from its head, where a real file system puts a new entry (re/notes/frontend.md).
 * The order follows from the names alone, so nothing has to be taken from the disk image:
 * an entry's chain is the AmigaDOS name hash modulo 72, and of two files in one chain the
 * newer comes first.  The dialog only ever shows names that begin with `wof.`, so that is
 * the whole list this has to get right.
 */
static uint16_t name_hash(const char *name)
{
    uint16_t hash = 0;

    while (name[hash])
        hash++;
    uint16_t h = hash;

    for (uint16_t i = 0; i < hash; i++) {
        uint8_t c = (uint8_t)name[i];

        if (c >= 'a' && c <= 'z')
            c = (uint8_t)(c - 32);
        h = (uint16_t)((h * 13u + c) & 0x7FFu);
    }
    return (uint16_t)(h % 72u);
}
