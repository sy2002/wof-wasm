/* src/font.c, lines 79-98 */
/* orig 0x01591E - the sum over the characters in range of width + 1, where a width of 0
 * counts as 10; characters outside first to last are skipped entirely. */
uint16_t wof_text_width(const char *s, uint16_t len)
{
    uint16_t w = 0;

    if (!font_file || len == 0)
        return 0;
    for (uint16_t i = 0; i < len; i++) {
        uint8_t c = (uint8_t)s[i];

        if (c > font_last || c < font_first)
            continue;

        uint8_t gw = font_widths[c - font_first];

        w = (uint16_t)(w + (gw ? gw : 10) + 1);
    }
    return w;
}
