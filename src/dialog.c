/* The load and save dialog, the saved game and the line editor (re/notes/frontend.md,
 * re/notes/campaign.md, re/notes/keys.md).
 *
 * The dialog draws itself entirely with graphics.library in the system font on a 320 x 200
 * screen of four planes, and it is the only place in the front end that lists the game's
 * own directory.  ExNext hands the entries out in the file system's own order, not the
 * alphabet, and that order is behaviour: the port reproduces it from the names alone
 * (src/fs.c, re/notes/frontend.md, "The order of the file list").
 *
 * A save writes what the walker of the saved game (0x015EC2) hands its write callback, in
 * the original's layout (re/notes/campaign.md), and a load reads the same pieces back
 * through the same walker with the read callback; the four pointer fields of the raw part
 * are derived from the data beside them, never taken from the file.
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

/* ------------------------------------------------------------------ the saved game */

/* The file a save is assembled in: the callback's writes go here in the walker's order and
 * the whole goes into the file system at the end, which is Open(MODE_NEWFILE), the Writes
 * and Close as one (src/fs.c).  It is scratch memory at the arena's top only while the save
 * runs, so the arena does not grow. */
static uint8_t *save_data;
static uint32_t save_at;

/* The byte the original's memory holds at `addr`: a registered global's or a fixed table's
 * (src/core.c), and where the port keeps nothing, the executable's own image, which is what
 * the original holds where nothing writes. */
static uint8_t memory_byte(uint32_t addr)
{
    uint8_t  b;
    uint32_t at = addr - 0x023000u;

    if (wof_original_load8(addr, &b))
        return b;
    return at < sizeof wof_tbl_data_image ? wof_tbl_data_image[at] : 0;
}

/* orig 0x015D62 - called by the walker between the ships and the targets; it does nothing. */
static void save_nothing(void)
{
}

/* orig 0x015DDE - the walker's write callback (file, address, length, flag): flag 1 writes
 * the block the long at the address points to, anything else the memory at the address.
 * Write's result is not looked at. */
static void save_put(uint32_t addr, uint32_t len, uint16_t flag)
{
    for (uint32_t i = 0; i < len; i++) {
        uint8_t b = 0;

        if (flag == 1)
            wof_pool_load8(addr, i, &b);
        else
            b = memory_byte(addr + i);
        if (save_at < WOF_SAVE_MAX)
            save_data[save_at] = b;
        save_at++;
    }
}

/* orig 0x015EC2 - the walker of the saved game, for the write and the read alike: the
 * memory from object_records up to target_records_4, map_length, the map's record list,
 * the gun list of every ship whose +4 and +0x12 are set, and the four tables of map_scan,
 * each as long as its count says.  After the map it sets map_extent and map_records_end
 * from map_length, the latter to the list's end where map_load leaves it a word before, so
 * a save changes the running game there. */
static void save_walk(void (*put)(uint32_t addr, uint32_t len, uint16_t flag))
{
    put(0x024CAEu, 0x0254F8u - 0x024CAEu, 0);
    put(0x0253C6u, 2u, 0);
    put(0x024628u, (uint32_t)(int32_t)(int16_t)wof_g.map_length, 1);      /* ext.l */
    wof_g.map_extent = (uint16_t)(wof_g.map_length << 2);                  /* asl.w #2 */
    wof_m.map_records_end[0].off = (uint32_t)(int32_t)(int16_t)wof_g.map_length;
    for (uint32_t i = 0; i < 5u; i++) {
        const wof_ship_t *ship = &wof_m.ship_records[i];

        if (ship->present != 0 && ship->w12 != 0)                         /* +4, +0x12 */
            put(0x025460u + 0x1Eu * i + 6u,
                (uint16_t)((uint32_t)(uint16_t)ship->gun_count * 14u), 1); /* mulu.w */
    }
    save_nothing();
    put(0x025504u, (uint16_t)((uint32_t)(uint16_t)(int16_t)(int8_t)wof_g.target_count_f * 14u), 1);
    put(0x025500u, (uint16_t)(wof_g.soldier_count << 3), 1);
    put(0x0254FCu, (uint16_t)((uint16_t)(int16_t)(int8_t)wof_g.target_count_3 << 4), 1);
    put(0x0254F8u, (uint16_t)((uint16_t)(int16_t)(int8_t)wof_g.target_count_4 << 4), 1);
}

/* orig 0x015E8A save_game_write - the file opened new (0x3EE), the walker with the write
 * callback, the file closed; 1.  When the file cannot be opened the original returns 0
 * without walking (0x015EBE), and its caller ignores the result; the port's file system
 * refuses a file only when its overlay is full.  The file's handle, save_handle
 * (0x026C60), is the file system's own in the port. */
int16_t wof_save_game_write(const char *name)
{
    uint32_t mark = wof_arena_mark();

    if (!wof_fs_can_write(name))
        return 0;
    save_data = (uint8_t *)wof_scratch_alloc(WOF_SAVE_MAX);
    save_at   = 0;
    if (save_data) {
        save_walk(save_put);
        wof_fs_write(name, save_data, save_at <= WOF_SAVE_MAX ? save_at : WOF_SAVE_MAX);
    }
    wof_arena_release(mark);
    save_data = 0;
    return 1;
}

/* ------------------------------------------------------------ the saved game, read back */

/* The file a load reads: the file system's own bytes, taken piece by piece as dos.Read
 * hands them out, a short read at the end of the file. */
static const uint8_t *load_data;
static uint32_t       load_len, load_at;

static uint32_t load_take(uint32_t len)
{
    uint32_t left = load_at < load_len ? load_len - load_at : 0;

    return len < left ? len : left;
}

/* The ship whose gun-list pointer (+0x06) lies at `addr`, or -1. */
static int ship_of_gun_pointer(uint32_t addr)
{
    for (int i = 0; i < 5; i++)
        if (addr == 0x025460u + 0x1Eu * (uint32_t)i + 6u)
            return i;
    return -1;
}

/* orig 0x015D7C save_read_part - the walker's read callback (file, address, length, flag):
 * flag 0 reads the memory at the address where it lies; flag 1 allocates a new block of the
 * length (mem_alloc, cleared), reads into it and stores its address at the address the
 * walker gave, only when Read gave the whole length, so a short read leaves the pointer.
 * The blocks the running game held are not freed.  The port's block is the pool at a fixed
 * place behind that pointer (src/mission.def), zeroed as the allocation would be; what it
 * keeps for the pointer is the map's address as the environment gives it (SPEC 7.3) or a
 * ship's gun-list flag.  A byte of the raw part goes where a registered field holds it; the
 * pointer fields there are the saving machine's and are derived afterwards, never taken
 * (wof_save_game_read). */
static void save_get(uint32_t addr, uint32_t len, uint16_t flag)
{
    uint32_t n = load_take(len);

    if (flag == 1) {
        int ship = ship_of_gun_pointer(addr);

        load_at += n;
        if (n != len)
            return;                            /* 0x015DB8: the new block is lost, the pointer stays */
        wof_pool_zero(addr);
        for (uint32_t i = 0; i < n; i++)
            wof_pool_store8(addr, i, load_data[load_at - n + i]);
        if (addr == 0x024628u)
            wof_g.map_list_address = wof_env_map_address();
        else if (ship >= 0)
            wof_m.ship_records[ship].guns = 1;
        return;
    }
    for (uint32_t i = 0; i < n; i++)
        wof_original_store8(addr + i, load_data[load_at + i]);
    load_at += n;
}

/* The port's check before a load, which the original does not make: the file is there, and
 * it holds every piece its own counts ask for, each within what the port keeps behind the
 * piece's pointer (src/mission.def).  The walker's lengths are computed as it computes them,
 * from the file's raw part and its map_length (re/notes/campaign.md, "The layout").  A file
 * that fails would make the original exit (0x015E50, a file that cannot be opened) or read
 * into blocks it cannot have; the port leaves the dialog as a cancel instead. */
int wof_save_game_fits(const char *name)
{
    wof_file_t     f;
    const uint8_t *d;
    uint32_t       len = 0, at, need;
    uint32_t       raw = 0x0254F8u - 0x024CAEu;

    if (!wof_dos_open(&f, name))
        return 0;
    wof_dos_close(&f);
    d = wof_fs_find(name, &len);
    if (!d)
        return 0;
#define RAW8(a)  ((uint32_t)d[(a) - 0x024CAEu])
#define RAW16(a) ((RAW8(a) << 8) | RAW8((a) + 1u))
    if (len < raw + 2u)
        return 0;
    at = raw + 2u;
    need = (uint32_t)(int32_t)(int16_t)(uint16_t)((d[raw] << 8) | d[raw + 1u]);   /* ext.l */
    if (need > wof_pool_capacity(0x024628u) || len - at < need)
        return 0;
    at += need;
    for (uint32_t i = 0; i < 5u; i++) {
        uint32_t ship = 0x025460u + 0x1Eu * i;

        if (RAW16(ship + 4u) == 0 || RAW16(ship + 0x12u) == 0)
            continue;
        need = (uint16_t)(RAW16(ship + 0x0Au) * 14u);                     /* mulu.w */
        if (need > wof_pool_capacity(ship + 6u) || len - at < need)
            return 0;
        at += need;
    }
    {
        const uint32_t pointer[4] = { 0x025504u, 0x025500u, 0x0254FCu, 0x0254F8u };
        uint32_t       lengths[4];

        lengths[0] = (uint16_t)((uint32_t)(uint16_t)(int16_t)(int8_t)RAW8(0x025385u) * 14u);
        lengths[1] = (uint16_t)(RAW16(0x0253C4u) << 3);
        lengths[2] = (uint16_t)((uint16_t)(int16_t)(int8_t)RAW8(0x025386u) << 4);
        lengths[3] = (uint16_t)((uint16_t)(int16_t)(int8_t)RAW8(0x025387u) << 4);
        for (int i = 0; i < 4; i++) {
            if (lengths[i] > wof_pool_capacity(pointer[i]) || len - at < lengths[i])
                return 0;
            at += lengths[i];
        }
    }
#undef RAW8
#undef RAW16
    return 1;
}

static uint32_t file_long(const uint8_t *p)
{
    return (uint32_t)p[0] << 24 | (uint32_t)p[1] << 16 | (uint32_t)p[2] << 8 | p[3];
}

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

/* orig 0x015E1A save_game_read - the file opened old (0x3ED), the walker with the read
 * callback, the file closed; 1.  A file that cannot be opened makes the original print an
 * error and exit the game (0x015E50); the port's dialog asks wof_save_game_fits first and
 * never comes here with such a file.  After the walk the port derives the four pointer
 * fields of the raw part from the data beside them, as the tick's frame_select (0x01C378)
 * would set them (re/notes/campaign.md, "The loader"): the player's shape and the
 * torpedo's from the frame name at the player's +0x08, the shape at 0x02541A from where
 * its pointer lies beside the player's (saved_hellcat_shape), and a ship's gun list from
 * whether the walker read one.  The owner's remembered vertical flip then wins over the
 * file's (SPEC 6.1). */
int16_t wof_save_game_read(const char *name)
{
    wof_file_t f;

    if (!wof_dos_open(&f, name))
        return 0;
    wof_dos_close(&f);
    load_data = wof_fs_find(name, &load_len);
    load_at   = 0;
    if (!load_data)
        return 0;
    for (int i = 0; i < 5; i++)
        wof_m.ship_records[i].guns = 0;        /* the saving machine's pointers are not taken */
    save_walk(save_get);

    {
        wof_player_t *p = &wof_m.player[0];
        uint32_t      raw = 0x0254F8u - 0x024CAEu;
        uint32_t      player = 0, level = 0;

        if (load_len >= raw) {
            player = file_long(load_data + (0x02507Cu - 0x024CAEu));
            level  = file_long(load_data + (0x02541Au - 0x024CAEu));
        }
        p->shape = wof_shape_handle(WOF_C_HELLCAT,
                                    wof_shape_find(&wof_assets.c[WOF_C_HELLCAT], p->frame_name));
        wof_m.torpedo_shape[0].s = wof_shape_handle(
            WOF_C_TORPEDO, wof_shape_find(&wof_assets.c[WOF_C_TORPEDO], p->frame_name));
        wof_m.g_02541a[0].s = saved_hellcat_shape(level, player, p->frame_name);
    }
    load_data = 0;
    wof_invert_vertical_restore();
    wof_test_load_end();
    return 1;
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

/* The dialog's "Exit Game" was taken (SPEC 6.1).  Set once and never cleared: the shell
 * reloads the page on it.  Not game state, so neither a registered global nor part of the
 * save state. */
static int exit_requested;

int wof_exit_requested(void)
{
    return exit_requested;
}

/* orig 0x018B96 load_save_dialog(mode): 0 load, 1 save; 0 back when a game was loaded or
 * saved and -1 when the player left it.  A file the port cannot hold is refused before the
 * load begins and the dialog leaves as a cancel (wof_save_game_fits). */
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
        if (!mode && !wof_save_game_fits(wof_f.dialog_path))
            break;                          /* the port's refusal: as Cancel (below) */
        wof_gfx_move(v, 10, 10);
        if (!mode) {
            /* 0x019132: the text, the music stopped, the running game's map freed and the
             * file read; then straight to the end, with no fade: the caller fades. */
            wof_gfx_text(v, wof_tbl_dialog_loading, str_len(wof_tbl_dialog_loading));
            CO_CALL(c, &wof_f.co_music, wof_music_stop());   /* 0x019146 */
            wof_free_map();                                   /* 0x01914A */
            wof_save_game_read(wof_f.dialog_path);            /* 0x019152 */
            wof_f.dialog_result = 0;                          /* 0x019218 */
            wof_sound_engine_load();                          /* 0x019248 */
            CO_RETURN(c);
        }

        wof_gfx_text(v, wof_tbl_dialog_saving, str_len(wof_tbl_dialog_saving));
        wof_save_game_write(wof_f.dialog_path);                 /* 0x019174 */

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
    /* 0x019228: "Exit Game" calls exit_game and with it fatal_exit, which ends the program.
     * The port raises wof_exit_requested at that point and the shell reloads the page, which
     * is the program started again; until the reload lands the dialog leaves as a cancel. */
    if (wof_f.dialog_cursor == 6)
        exit_requested = 1;
    CO_CALL(c, &wof_f.co_show, wof_view_show_wait(wof_f.back_view));
    wof_f.dialog_result = 0xFFFF;
    wof_sound_engine_load();                /* 0x019248 */
    CO_END(c);
}
