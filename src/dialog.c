/* The load and save dialog and the line editor (re/notes/frontend.md, re/notes/keys.md).
 *
 * The dialog draws itself entirely with graphics.library in the system font on a 320 x 200
 * screen of four planes, and it is the only place in the front end that lists the game's
 * own directory.  ExNext hands the entries out in the file system's own order, not the
 * alphabet, and that order is behaviour: the port reproduces it from the names alone
 * (src/fs.c, re/notes/frontend.md, "The order of the file list").
 *
 * What a saved game contains is M7.  The routine that would write or read it is a marked
 * stand-in here; what it does instead is what the original does when the load fails, which
 * re/notes/frontend.md observed: the dialog comes back as a cancel and the rank selection
 * rebuilds its picture.
 */
#include "wof.h"
#include "gen/tables.h"

static uint16_t str_len(const char *s)
{
    uint16_t n = 0;

    while (s && s[n])
        n++;
    return n;
}

/* The `%d`, `%-6ld` and `%-12s` of the front end, which is all of RawDoFmt the original
 * really asks for (SPEC 3.4).  Returns the length. */
/* exec RawDoFmt as the debug keys call it: %d takes a word of the data stream and %ld a
 * long, both signed, and `data` is the stream as the stack holds it, word by word.  Returns
 * the length without the NUL it writes. */
uint16_t wof_raw_do_fmt(char *dst, const char *format, const uint16_t *data)
{
    uint16_t out = 0;

    for (const char *p = format; *p; p++) {
        int32_t v;
        char    digits[12];
        int     n = 0;

        if (*p != '%') {
            dst[out++] = *p;
            continue;
        }
        p++;
        if (*p == 's') {                        /* a long pointer to a text of the image */
            uint32_t addr = ((uint32_t)data[0] << 16) | data[1];

            data += 2;
            for (uint32_t i = 0; wof_image8(addr + i) != 0; i++)
                dst[out++] = (char)wof_image8(addr + i);
            continue;
        }
        if (*p == 'l') {
            p++;
            v = (int32_t)(((uint32_t)data[0] << 16) | data[1]);
            data += 2;
        } else {
            v = (int16_t)data[0];
            data += 1;
        }
        if (*p != 'd')
            break;
        if (v < 0) {
            dst[out++] = '-';
            v = -v;
        }
        do {
            digits[n++] = (char)('0' + (uint32_t)v % 10u);
            v = (int32_t)((uint32_t)v / 10u);
        } while (v);
        while (n)
            dst[out++] = digits[--n];
    }
    dst[out] = 0;
    return out;
}

uint16_t wof_format(char *dst, const char *format, int32_t number, const char *text)
{
    uint16_t out = 0;
    uint16_t width = 0;
    const char *p = format;

    while (*p) {
        if (*p != '%') {
            dst[out++] = *p++;
            continue;
        }
        p++;
        int left = 0;

        if (*p == '-') {
            left = 1;
            p++;
        }
        width = 0;
        while (*p >= '0' && *p <= '9')
            width = (uint16_t)(width * 10 + (uint16_t)(*p++ - '0'));
        while (*p == 'l')
            p++;

        char     body[40];
        uint16_t n = 0;

        if (*p == 's') {
            const char *s = text ? text : "";

            while (s[n] && n < sizeof body - 1) {
                body[n] = s[n];
                n++;
            }
        } else {
            n = wof_number(body, number);
        }
        p++;

        if (!left)
            for (uint16_t i = n; i < width; i++)
                dst[out++] = ' ';
        for (uint16_t i = 0; i < n; i++)
            dst[out++] = body[i];
        if (left)
            for (uint16_t i = n; i < width; i++)
                dst[out++] = ' ';
    }
    dst[out] = 0;
    return out;
}

/* orig 0x016592 path_sanitise - a ':' or a '/' in a name becomes a space, so that a typed
 * name cannot name a device or a directory. */
void wof_path_sanitise(char *name)
{
    for (; *name; name++)
        if (*name == ':' || *name == '/')
            *name = ' ';
}

/* ------------------------------------------------------------------ the line editor */

/* orig 0x016032 text_caret - one 8 x 8 cell inverted, which is how the caret appears and
 * disappears without anything being remembered about what was under it. */
static void text_caret(wof_vport_t *v, int16_t x, int16_t y)
{
    wof_gfx_set_drmd(v, WOF_COMPLEMENT);
    wof_gfx_rect_fill(v, x, y, (int16_t)(x + 7), (int16_t)(y + 7));
    wof_gfx_set_drmd(v, WOF_JAM2);
}

/* orig 0x016086 text_input.  The fifth argument, a round limit, is pushed by both callers
 * and read by nothing, like the second argument of fade_to.
 *
 * Two behaviours that are in the code and in no note: a cursor key with either Shift held
 * jumps to the start or the end of the line, and right Amiga with X clears it. */
wof_co_t wof_text_input(char *buffer, uint16_t max, int16_t x, int16_t y)
{
    wof_ctx_t   *c = &wof_f.co_text;
    wof_vport_t *v = wof_draw_target_vport();

    CO_BEGIN(c);
    wof_f.text_result = 0;
    wof_f.text_max    = max;
    wof_f.text_x      = x;
    wof_f.text_y      = y;
    wof_f.editing     = 1;

    wof_gfx_set_apen(v, 6);
    wof_gfx_set_bpen(v, 0);
    wof_gfx_set_drmd(v, WOF_JAM2);
    for (uint16_t i = 0; i < 0x50; i++)
        wof_f.text_pad[i] = ' ';
    wof_f.text_pad[0x50] = 0;
    wof_f.text_prev   = -1;
    wof_f.text_cursor = 0;
    wof_f.text_redraw = 0;

    for (;;) {
        v = wof_draw_target_vport();
        if (wof_f.text_cursor != wof_f.text_prev && !wof_f.text_redraw && wof_f.text_prev >= 0)
            text_caret(v, (int16_t)(wof_f.text_prev * 8 + wof_f.text_x), wof_f.text_y);

        if (wof_f.text_redraw) {
            uint16_t len = str_len(buffer);

            wof_gfx_move(v, wof_f.text_x, (int16_t)(wof_sysfont_baseline() + wof_f.text_y));
            wof_gfx_text(v, buffer, len);
            if ((int16_t)len <= (int16_t)wof_f.text_max) {
                uint16_t at = (uint16_t)(wof_f.text_max + 1 - len);

                wof_f.text_pad[at] = 0;
                wof_gfx_move(v, (int16_t)(len * 8 + wof_f.text_x),
                             (int16_t)(wof_sysfont_baseline() + wof_f.text_y));
                wof_gfx_text(v, wof_f.text_pad, str_len(wof_f.text_pad));
                wof_f.text_pad[at] = ' ';
            }
        }
        if (wof_f.text_redraw || wof_f.text_cursor != wof_f.text_prev)
            text_caret(v, (int16_t)(wof_f.text_cursor * 8 + wof_f.text_x), wof_f.text_y);
        wof_f.text_prev   = wof_f.text_cursor;
        wof_f.text_redraw = 0;

        while (!wof_key_available()) {
            CO_WAIT(c);
            if (wof_poll_fire())
                goto done;
            if (wof_poll_joy_dir8()) {
                if (wof_g.joy_dir8 == 1) {
                    CO_CALL(c, &wof_f.co_release, wof_wait_input_release());
                    wof_f.text_result = -1;
                    goto done;
                }
                if (wof_g.joy_dir8 == 5) {
                    CO_CALL(c, &wof_f.co_release, wof_wait_input_release());
                    wof_f.text_result = 1;
                    goto done;
                }
            }
        }
        {
            uint32_t key       = wof_key_get();
            uint16_t code      = (uint16_t)(key & 0xFFu);
            int16_t  qualifier = (int16_t)(key >> 16);
            uint16_t ch        = wof_key_to_char(key);
            uint16_t len       = str_len(buffer);

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
            if (code == 0x4D) { wof_f.text_result =  1; goto done; }
            if (code == 0x41) {                       /* backspace */
                if (!wof_f.text_cursor)
                    continue;
                wof_f.text_cursor--;
                code = 0x46;
            }
            if (code == 0x46) {                       /* delete under the cursor */
                uint16_t i = (uint16_t)wof_f.text_cursor;

                while (buffer[i]) {
                    buffer[i] = buffer[i + 1];
                    i++;
                    wof_f.text_redraw = 1;
                }
                continue;
            }
            if (wof_key_to_char(code) == 'x' && (qualifier & 0x0080)) {
                wof_f.text_cursor = 0;                /* right Amiga and X: clear the line */
                buffer[0] = 0;
                wof_f.text_redraw = 1;
                continue;
            }
            if (!ch || wof_f.text_cursor >= (int16_t)wof_f.text_max)
                continue;
            for (int16_t i = (int16_t)wof_f.text_max; i > wof_f.text_cursor; i--)
                buffer[i] = buffer[i - 1];
            buffer[wof_f.text_max] = 0;
            buffer[wof_f.text_cursor] = (char)ch;
            wof_f.text_cursor++;
            if (wof_f.text_cursor > (int16_t)wof_f.text_max)
                wof_f.text_cursor = (int16_t)wof_f.text_max;
            wof_f.text_redraw = 1;
        }
    }
done:
    text_caret(wof_draw_target_vport(),
               (int16_t)(wof_f.text_cursor * 8 + wof_f.text_x), wof_f.text_y);
    wof_f.editing = 0;
    CO_END(c);
}

int wof_text_result(void)
{
    return wof_f.text_result;
}

/* ------------------------------------------------------------------ the file list */

/* orig 0x018A06 dialog_file_list.  It locks the game's own directory with a NULL name,
 * walks it with ExNext and keeps at most six entries whose name begins with `wof.`, in the
 * order the file system hands them out.  fib_DirEntryType is not checked, so a directory
 * whose name began `wof.` would be listed; the port has no directories, so nothing does.
 * The part after `wof.` is copied into the slot and again into the copy beside it, which is
 * what a save over an edited name is compared against. */
static uint16_t dialog_file_list(void)
{
    uint16_t kept = 0;

    for (uint16_t i = 0; i < 6; i++)
        wof_f.dialog_names[i][0] = 0;

    for (uint32_t i = 0; kept < 6; i++) {
        const char *name = wof_fs_dir_entry(i);

        if (!name)
            break;

        uint16_t n = 0;

        while (n < 27 && name[4 + n]) {
            wof_f.dialog_names[kept][n] = name[4 + n];
            n++;
        }
        while (n < 28)
            wof_f.dialog_names[kept][n++] = 0;
        for (uint16_t k = 0; k < 29; k++)
            wof_f.dialog_copy[kept][k] = wof_f.dialog_names[kept][k];
        kept++;
    }
    return kept;
}

/* orig 0x018958 dialog_draw_names - the six slot names, each padded to 28 characters with
 * the spaces at 0x017CFC, so that a shorter name blanks what was there before. */
static void dialog_draw_names(void)
{
    wof_vport_t *v = wof_draw_target_vport();

    for (uint16_t i = 0; i < 6; i++) {
        uint16_t len = str_len(wof_f.dialog_names[i]);

        wof_gfx_set_drmd(v, WOF_JAM2);
        wof_gfx_move(v, 0x2D, (int16_t)((i << 4) + wof_sysfont_baseline() + 0x3D));
        wof_gfx_text(v, wof_f.dialog_names[i], len);
        if (len < 0x1C)
            wof_gfx_text(v, wof_tbl_spaces, (uint16_t)(0x1C - len));
    }
}

/* The highlight of one entry: a COMPLEMENT RectFill, which the next one undoes. */
static void dialog_highlight(int16_t which, uint16_t mode)
{
    wof_vport_t *v = wof_draw_target_vport();
    int16_t x = 0x2C, y;

    wof_gfx_set_drmd(v, WOF_COMPLEMENT);
    if (which < 6) {
        if (!mode) {                       /* in save mode the editor's caret marks the slot */
            y = (int16_t)((which << 4) + 0x3D);
            wof_gfx_rect_fill(v, x, (int16_t)(y - 1), (int16_t)(x + 0xED), (int16_t)(y + 7));
        }
    } else if (which == 6) {
        wof_gfx_rect_fill(v, 0x2D, 0xB9, 0x91, 0xC5);
    } else {
        wof_gfx_rect_fill(v, 0xCF, 0xB9, 0x11B, 0xC5);
    }
    wof_gfx_set_drmd(v, WOF_JAM2);
}

/* orig 0x018B96 load_save_dialog(mode): 0 load, 1 save; 0 back when a game was loaded or
 * saved and -1 when the player left it.  What a saved game holds is M7; the two routines
 * that would write and read it are stand-ins here. */
wof_co_t wof_load_save_dialog(uint16_t mode)
{
    wof_ctx_t   *c = &wof_f.co_inner;
    wof_vport_t *v;

    CO_BEGIN(c);
    wof_f.dialog_mode   = mode;
    wof_f.dialog_result = 0xFFFF;

    CO_CALL(c, &wof_f.co_screen, wof_screen_dialog());
    v = wof_back_vport();
    wof_draw_set_target(v);
    wof_clip_set_full();
    wof_gfx_set_apen(v, 0x8F);              /* SetAPen(0x28F): pen 15 on four planes */
    wof_gfx_set_drmd(v, WOF_JAM1);

    for (uint16_t i = 0; i < 3; i++) {
        const char *text = i == 0 ? wof_tbl_dialog_game
                         : i == 1 ? wof_tbl_dialog_exit : wof_tbl_dialog_cancel;

        wof_gfx_move(v, (int16_t)wof_tbl_dialog_labels[i * 4 + 2],
                     (int16_t)wof_tbl_dialog_labels[i * 4 + 3]);
        wof_gfx_text(v, text, str_len(text));
    }
    wof_gfx_move(v, 0x55, 0x13);
    {
        const char *text = mode ? wof_tbl_dialog_save : wof_tbl_dialog_load;

        wof_gfx_text(v, text, 4);
    }
    for (uint16_t i = 0; i < 8; i++) {
        int16_t x0 = (int16_t)wof_tbl_dialog_boxes[i * 4 + 0];
        int16_t y0 = (int16_t)wof_tbl_dialog_boxes[i * 4 + 1];
        int16_t x1 = (int16_t)wof_tbl_dialog_boxes[i * 4 + 2];
        int16_t y1 = (int16_t)wof_tbl_dialog_boxes[i * 4 + 3];

        wof_gfx_move(v, x0, y0);
        wof_gfx_draw(v, x1, y0);
        wof_gfx_draw(v, x1, y1);
        wof_gfx_draw(v, x0, y1);
        wof_gfx_draw(v, x0, y0);
    }

    for (uint32_t i = 0; i < WOF_PAL_COLOURS; i++)
        wof_f.dialog_pal[i] = i < 16 ? wof_tbl_dialog_box_palette[i] : 0;

    CO_CALL(c, &wof_f.co_show, wof_view_show_wait(wof_f.back_view));
    CO_CALL(c, &wof_f.co_fade, wof_fade_to(wof_f.dialog_pal));

    wof_f.dialog_cursor = 0;
    wof_f.dialog_prev   = 0;
    wof_draw_set_target(wof_front_vport());
    wof_clip_set_full();
    wof_sound_engine_free();                /* 0x018DE4: the engine's sound goes (0x0134A4) */
    wof_f.dialog_count = dialog_file_list();
    dialog_draw_names();
    if (wof_f.dialog_count == 0 && mode == 0)
        wof_f.dialog_cursor = 7;            /* nothing to load: start on Cancel */

    for (;;) {
        if (wof_f.dialog_cursor < 6 && mode) {
            wof_gfx_set_drmd(wof_front_vport(), WOF_JAM1);
            wof_gfx_set_apen(wof_front_vport(), 0x8F);
            CO_CALL(c, &wof_f.co_text,
                    wof_text_input(wof_f.dialog_names[wof_f.dialog_cursor], 0x1C, 0x2C,
                                   (int16_t)((wof_f.dialog_cursor << 4) + 0x3D)));
            wof_f.dialog_move = (int16_t)wof_text_result();
        } else {
            dialog_highlight(wof_f.dialog_cursor, mode);
            CO_CALL(c, &wof_f.co_menu, wof_menu_input(0));
            wof_f.dialog_move = (int16_t)wof_menu_result();
            CO_CALL(c, &wof_f.co_release, wof_wait_input_release());
        }

        wof_f.dialog_prev = wof_f.dialog_cursor;
        do {
            wof_f.dialog_cursor = (int16_t)(wof_f.dialog_cursor + wof_f.dialog_move);
            if (wof_f.dialog_cursor < 0)
                wof_f.dialog_cursor = 7;
            if (wof_f.dialog_cursor > 7)
                wof_f.dialog_cursor = 0;
        } while (!mode && wof_f.dialog_cursor < 6
                 && wof_f.dialog_names[wof_f.dialog_cursor][0] == 0);

        if (wof_f.dialog_cursor != wof_f.dialog_prev)
            dialog_highlight(wof_f.dialog_prev, mode);
        if (wof_f.dialog_move)
            continue;

        wof_path_sanitise(wof_f.dialog_names[wof_f.dialog_cursor]);
        if (wof_f.dialog_cursor >= 6 || wof_f.dialog_names[wof_f.dialog_cursor][0] == 0)
            break;                          /* a button, or an empty slot: nothing to do */

        v = wof_front_vport();
        wof_gfx_set_apen(v, 1);
        {
            uint16_t n = 0;

            for (const char *s = wof_tbl_wof_prefix; *s; s++)
                wof_f.dialog_path[n++] = *s;
            for (const char *s = wof_f.dialog_names[wof_f.dialog_cursor]; *s; s++)
                wof_f.dialog_path[n++] = *s;
            wof_f.dialog_path[n] = 0;
        }
        wof_gfx_move(v, 10, 10);
        if (!mode) {
            wof_gfx_text(v, wof_tbl_dialog_loading, str_len(wof_tbl_dialog_loading));
            CO_CALL(c, &wof_f.co_music, wof_music_stop());   /* 0x019146 */
            /* M7 STAND-IN: the loader.  What the original does when the load fails is what
             * re/notes/frontend.md observed, and what the port does until M7 ports it: the
             * dialog comes back as a cancel and the rank selection rebuilds its picture. */
            WOF_STANDIN("M7 STAND-IN: 0x019152, save_game_read: a saved game loaded");
            CO_CALL(c, &wof_f.co_fade, wof_fade_out());
            CO_CALL(c, &wof_f.co_show, wof_view_show_wait(wof_f.back_view));
            wof_f.dialog_result = 0xFFFF;
            wof_sound_engine_load();        /* 0x019248 */
            CO_RETURN(c);
        }

        wof_gfx_text(v, wof_tbl_dialog_saving, str_len(wof_tbl_dialog_saving));
        /* M7 STAND-IN: what a saved game holds.  The file is written so that the dialog,
         * the list and the rename below are the real thing; its contents are not. */
        wof_fs_write(wof_f.dialog_path, (const uint8_t *)wof_f.hiscore, 16);

        /* A save over a slot whose name was edited renames: the file the name came from is
         * deleted (re/notes/frontend.md). */
        for (wof_f.dialog_i = 0; wof_f.dialog_i < wof_f.dialog_count; wof_f.dialog_i++) {
            char *was = wof_f.dialog_copy[wof_f.dialog_i];
            char *now = wof_f.dialog_names[wof_f.dialog_i];
            uint16_t k = 0;

            if (!was[0])
                continue;
            while (was[k] == now[k] && was[k])
                k++;
            if (was[k] == now[k])
                continue;                   /* the name is the one it was */

            uint16_t n = 0;

            for (const char *s = wof_tbl_wof_prefix; *s; s++)
                wof_f.dialog_path[n++] = *s;
            for (const char *s = was; *s; s++)
                wof_f.dialog_path[n++] = *s;
            wof_f.dialog_path[n] = 0;
            wof_fs_delete(wof_f.dialog_path);
            break;
        }
        CO_CALL(c, &wof_f.co_fade, wof_fade_out());
        CO_CALL(c, &wof_f.co_show, wof_view_show_wait(wof_f.back_view));
        wof_f.dialog_result = 0;
        wof_sound_engine_load();            /* 0x019248: back, if it went */
        CO_RETURN(c);
    }

    CO_CALL(c, &wof_f.co_fade, wof_fade_out());
    /* "Exit Game" calls fatal_exit on the machine, which ends the program.  A page has
     * nothing to end into, so the port treats it as a cancel and says so here. */
    CO_CALL(c, &wof_f.co_show, wof_view_show_wait(wof_f.back_view));
    wof_f.dialog_result = 0xFFFF;
    wof_sound_engine_load();                /* 0x019248 */
    CO_END(c);
}
