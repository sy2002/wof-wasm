/* src/keys.c, lines 64-75 */
/* The original's shift loop runs from index 0 up to and including the new key_count, so
 * with a full buffer its last round copies one entry past the end of each array.  On the
 * machine those two reads land on the next globals: key_buffer + 10 is the first byte of
 * key_qualifier_buffer, which big-endian is the high byte of its first word, and
 * key_qualifier_buffer + 20 is key_count itself.  The port keeps the values rather than the
 * adjacency, so that the quirk survives a struct whose order is its own. */
static uint8_t key_code_at(uint16_t i)
{
    if (i < 10)
        return wof_g.key_buffer[i];
    return (uint8_t)(wof_g.key_qualifier_buffer[0] >> 8);
}
