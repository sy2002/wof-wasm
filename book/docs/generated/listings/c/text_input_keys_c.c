/* src/dialog.c, lines 529-543, a part of wof_text_input (lines 453-584) */
if (code == 0x44 || code == 0x43)
    goto done;
if (code == 0x4F) {                       /* cursor left */
    wof_f.text_cursor--;
    if (wof_f.text_cursor < 0 || (qualifier & 3))
        wof_f.text_cursor = 0;
    continue;
}
if (code == 0x4E) {                       /* cursor right */
    wof_f.text_cursor++;
    if (wof_f.text_cursor > (int16_t)len || (qualifier & 3))
        wof_f.text_cursor = (int16_t)len;
    continue;
}
if (code == 0x4C) { wof_f.text_result = -1; goto done; }
