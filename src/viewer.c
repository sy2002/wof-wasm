/* TEMPORARY - the M1 viewer.  Replaced by the front end in M3; nothing else may depend
 * on it.
 *
 * M1 has no game loop: it has loaders, decoders, a blit and a picture.  This file is the
 * only place that puts them on screen, so that the milestone can be looked at.  It is
 * deliberately one file and deliberately not a port of anything: no title sequence, no
 * fades, no music.  Those are M3 and M8.
 *
 * Pages, stepped with the keys the shell sends to wof_key_press:
 *
 *   0  the publisher logo      shapes/broderbund   through the ported ILBM reader
 *   1  the title               shapes/wingstitle
 *   2  the credits             shapes/creditscreen
 *   3  the two fonts           newarmyfont and topaz 8
 *   4  the shape browser       every shape of every container, through the ported blit
 *   5  the play screen         the 214-line stack of SPEC 6.4, with three palettes
 */
#include "wof.h"
#include "gen/tables.h"

#define PAGE_LOGO    0
#define PAGE_TITLE   1
#define PAGE_CREDITS 2
#define PAGE_FONTS   3
#define PAGE_SHAPES  4
#define PAGE_PLAY    5
#define PAGE_COUNT   6

#define KEY_NEXT_PAGE 1
#define KEY_PREV_PAGE 2
#define KEY_NEXT_ITEM 3
#define KEY_PREV_ITEM 4

/* Palette slots.  0 is the blank one every uncovered row goes through. */
#define PAL_MAIN   1
#define PAL_DASH   2
#define PAL_TICKER 3

static wof_vport_t *vp_pic;      /* 320 x 200 x 5, low resolution: the pictures and shapes */
static wof_vport_t *vp_hi;       /* 640 x 200 x 4, high resolution: the fonts and the dash */
static wof_vport_t *vp_play;     /* 320 x 162 x 5: the playfield of the play screen */
static wof_vport_t *vp_dash;     /* 640 x  37 x 4: the dashboard, from iff-dash */
static wof_vport_t *vp_ticker;   /* 640 x  13 x 1: the message ticker */

static uint16_t dash_colours[WOF_PAL_COLOURS];
static uint16_t night_dash_colours[WOF_PAL_COLOURS];

/* show_shapes works the page count out from the layout; the keys wrap against it. */
static uint16_t shape_pages = 1;

/* ------------------------------------------------------------------ small helpers */

static uint16_t str_len(const char *s)
{
    uint16_t n = 0;

    while (s && s[n])
        n++;
    return n;
}

static uint16_t append(char *dst, uint16_t at, const char *s)
{
    while (s && *s)
        dst[at++] = *s++;
    return at;
}

static uint16_t append_num(char *dst, uint16_t at, uint32_t v)
{
    char tmp[10];
    uint16_t n = 0;

    do {
        tmp[n++] = (char)('0' + v % 10);
        v /= 10;
    } while (v);
    while (n)
        dst[at++] = tmp[--n];
    return at;
}

static uint16_t append_name(char *dst, uint16_t at, uint32_t name)
{
    for (int i = 3; i >= 0; i--) {
        char c = (char)((name >> (i * 8)) & 0xFF);
        dst[at++] = (c >= 0x20 && c < 0x7F) ? c : ' ';
    }
    return at;
}

/* The pen a caption is legible in, chosen from the viewport's own colours rather than
 * written down here: hand-written sources hold no tuning values. */
static uint8_t brightest_pen(const wof_vport_t *v)
{
    uint16_t top = (uint16_t)(1u << v->depth);
    uint8_t  best = 1;
    uint16_t score = 0;

    if (top > WOF_PAL_COLOURS)
        top = WOF_PAL_COLOURS;
    for (uint16_t i = 1; i < top; i++) {
        uint16_t c = v->colours[i];
        uint16_t s = (uint16_t)(((c >> 8) & 0xF) + ((c >> 4) & 0xF) + (c & 0xF));

        if (s > score) {
            score = s;
            best  = (uint8_t)i;
        }
    }
    return best;
}

/* Captions are trimmed to what the surface holds: text_render returns 0 for anything
 * wider than its buffer, so an over-long one would otherwise simply not appear. */
static void caption(wof_vport_t *v, const char *text, uint16_t len, int16_t y)
{
    while (len && wof_text_width(text, len) > v->width - 8)
        len--;
    wof_draw_set_target(v);
    wof_text_draw(text, len, 4, y, brightest_pen(v));
}

/* ----------------------------------------------------------------------- the pages */

static void show_picture(const char *file)
{
    uint32_t mark = wof_arena_mark();
    uint32_t len  = 0;
    uint8_t *raw  = wof_load_file(file, &len);

    wof_mem_set(vp_pic->colours, 0, sizeof vp_pic->colours);
    wof_vport_clear_planes(vp_pic);
    if (raw)
        wof_iff_to_vport(raw, len, vp_pic);
    wof_arena_release(mark);

    wof_screen_reset();
    wof_screen_band(vp_pic, 0, vp_pic->height, 0, PAL_MAIN);
}

/* Both fonts over the printable range, and the file names the executable carries, which
 * are the only strings in the port that are not made up on the spot. */
static void show_fonts(void)
{
    char line[96];
    uint16_t n;

    wof_mem_copy(vp_hi->colours, wof_assets.day_palette, sizeof vp_hi->colours);
    wof_vport_clear_planes(vp_hi);
    wof_draw_set_target(vp_hi);
    wof_clip_set_full();

    uint8_t pen = brightest_pen(vp_hi);
    int16_t y   = 8;

    n = (uint16_t)append(line, 0, "NEWARMYFONT   HEIGHT ");
    n = append_num(line, n, wof_font_height());
    wof_text_draw(line, n, 8, y, pen);
    y = (int16_t)(y + wof_font_height() + 6);

    for (uint8_t first = 0x20; first < 0x7F; first = (uint8_t)(first + 32)) {
        n = 0;
        for (uint8_t c = first; c < first + 32 && c < 0x7F; c++)
            line[n++] = (char)c;
        wof_text_draw(line, n, 8, y, pen);
        y = (int16_t)(y + wof_font_height() + 2);
    }

    y = (int16_t)(y + 10);
    n = (uint16_t)append(line, 0, wof_sysfont_present()
                         ? "TOPAZ 8 FROM THE KICKSTART ROM"
                         : "TOPAZ 8 IS NOT AVAILABLE: NO original/kick.rom");
    wof_text_draw(line, n, 8, y, pen);
    y = (int16_t)(y + wof_font_height() + 6);

    if (wof_sysfont_present()) {
        for (uint8_t first = 0x20; first < 0x7F; first = (uint8_t)(first + 32)) {
            n = 0;
            for (uint8_t c = first; c < first + 32 && c < 0x7F; c++)
                line[n++] = (char)c;
            wof_sysfont_draw(line, n, 8, y, pen);
            y = (int16_t)(y + 10);
        }
        y = (int16_t)(y + 8);
        wof_sysfont_draw(wof_tbl_highscore_file, str_len(wof_tbl_highscore_file), 8, y, pen);
        y = (int16_t)(y + 10);
        wof_sysfont_draw(wof_tbl_world_shp, str_len(wof_tbl_world_shp), 8, y, pen);
    }

    wof_screen_reset();
    wof_screen_band(vp_hi, 0, vp_hi->height, 0, PAL_MAIN);
}

/* Every shape of one container, laid out in a grid and drawn through the ported blit.
 * The dashboard containers go on a 4-plane high-resolution target with the dashboard's
 * own colours, which is where the game draws them and what their plane masks expect;
 * everything else goes on a 5-plane low-resolution one with the day palette. */
static void show_shapes(void)
{
    uint16_t slot = wof_s.view_item < WOF_C_COUNT ? wof_s.view_item : 0;
    int      dashy = (slot == WOF_C_DASH || slot == WOF_C_NIGHTDASH);
    wof_vport_t *v = dashy ? vp_hi : vp_pic;
    const wof_container_t *c = &wof_assets.c[slot];

    if (dashy)
        wof_mem_copy(v->colours, slot == WOF_C_DASH ? dash_colours : night_dash_colours,
                     sizeof v->colours);
    else
        wof_mem_copy(v->colours, wof_assets.day_palette, sizeof v->colours);

    wof_vport_clear_planes(v);
    wof_draw_set_target(v);
    wof_clip_set(0, (int16_t)v->height, 0, (int16_t)v->width);
    wof_draw_list_reset();
    wof_draw_context(slot, 0);

    int16_t top = (int16_t)(wof_font_height() * 2 + 6);
    int16_t x = 2, y = top, row_h = 0;
    uint16_t shown = 0;
    uint16_t page = wof_s.view_sub;

    /* Lay the shapes out left to right; whatever does not fit starts a new page. */
    uint16_t at = 0;

    for (uint16_t i = 0; i < c->count; i++) {
        const wof_shape_t *s = &c->shapes[i];
        int16_t w = (int16_t)(s->wbytes * 8 + 2);
        int16_t h = (int16_t)(s->height + 2);

        if (w > (int16_t)v->width)
            w = (int16_t)v->width;
        if (x + w > (int16_t)v->width) {
            x = 2;
            y = (int16_t)(y + row_h);
            row_h = 0;
        }
        if (y + h > (int16_t)v->height) {
            at++;                        /* this shape belongs to the next page */
            x = 2;
            y = top;
            row_h = 0;
        }
        if (at == page) {
            /* The hotspot is what the callers subtract, so the draw position is the
             * cell corner plus the hotspot: the shape then lands inside its cell. */
            wof_shape_draw(s, (int16_t)(x + s->hot_x), (int16_t)(y + s->hot_y));
            shown++;
        }
        if (h > row_h)
            row_h = h;
        x = (int16_t)(x + w);
    }
    shape_pages = (uint16_t)(at + 1);
    if (page >= shape_pages) {
        wof_s.view_sub = 0;
        wof_s.view_dirty = 1;
    }

    char line[96];
    uint16_t n;

    n = (uint16_t)append(line, 0, c->file ? c->file : "?");
    n = (uint16_t)append(line, n, " ");
    n = append_num(line, n, c->count);
    n = (uint16_t)append(line, n, " P");
    n = append_num(line, n, (uint32_t)page + 1);
    n = (uint16_t)append(line, n, "/");
    n = append_num(line, n, shape_pages);
    caption(v, line, n, 2);

    n = (uint16_t)append(line, 0, "DREW ");
    n = append_num(line, n, shown);
    n = (uint16_t)append(line, n, " LIST ");
    {
        uint32_t count = 0;
        wof_display_list(&count);
        n = append_num(line, n, count);
    }
    if (c->count) {
        n = (uint16_t)append(line, n, " ");
        n = append_name(line, n, c->names[0]);
        n = (uint16_t)append(line, n, "..");
        n = append_name(line, n, c->names[c->count - 1]);
    }
    caption(v, line, n, (int16_t)(wof_font_height() + 3));

    wof_screen_reset();
    wof_screen_band(v, 0, v->height, 0, PAL_MAIN);
}

/* The play screen of SPEC 6.4: three viewports, three palettes, 214 lines, with the
 * dashboard picture the game loads for it and a sample of world shapes on the playfield. */
static void show_play(void)
{
    wof_mem_copy(vp_play->colours, wof_assets.day_palette, sizeof vp_play->colours);
    wof_vport_clear_planes(vp_play);
    wof_draw_set_target(vp_play);

    /* The playfield's own clip rectangle, orig 0x01524A: rows 0 to 162, columns 0 to 320. */
    wof_clip_set(0, WOF_PLAYFIELD_H, 0, WOF_PLAYFIELD_W);
    wof_draw_list_reset();
    wof_draw_context(0, 0);

    const wof_container_t *c = &wof_assets.c[WOF_C_WORLD];
    int16_t x = 4, y = 20, row_h = 0;

    for (uint16_t i = 0; i < c->count; i++) {
        const wof_shape_t *s = &c->shapes[i];
        int16_t w = (int16_t)(s->wbytes * 8 + 2);
        int16_t h = (int16_t)(s->height + 2);

        if (s->height > 60 || s->wbytes > 12)
            continue;                       /* the big hull pieces would fill the page */
        if (x + w > WOF_PLAYFIELD_W) {
            x = 4;
            y = (int16_t)(y + row_h);
            row_h = 0;
        }
        if (y + h > WOF_PLAYFIELD_H)
            break;
        wof_shape_draw(s, (int16_t)(x + s->hot_x), (int16_t)(y + s->hot_y));
        if (h > row_h)
            row_h = h;
        x = (int16_t)(x + w);
    }
    caption(vp_play, "PLAYFIELD 320x162x5", 19, 2);

    wof_screen_reset();
    wof_screen_band(vp_play, 0, WOF_PLAYFIELD_H, 0, PAL_MAIN);
    wof_screen_band(vp_dash, WOF_DASH_Y, WOF_DASH_H, 0, PAL_DASH);
    wof_screen_band(vp_ticker, WOF_TICKER_Y, WOF_TICKER_H, 0, PAL_TICKER);
}

static void redraw(void)
{
    switch (wof_s.view_page) {
    case PAGE_LOGO:    show_picture(wof_tbl_broderbund_pic);   break;
    case PAGE_TITLE:   show_picture(wof_tbl_wingstitle_pic);   break;
    case PAGE_CREDITS: show_picture(wof_tbl_creditscreen_pic); break;
    case PAGE_FONTS:   show_fonts();                           break;
    case PAGE_SHAPES:  show_shapes();                          break;
    default:           show_play();                            break;
    }
    wof_screen_present();
}

/* --------------------------------------------------------------------------- set-up */

/* The dashboard, decoded into the viewport the game gives it, so that the play page shows
 * the real picture with its own sixteen colours and the shape browser has them too. */
static void load_dashboard(void)
{
    uint32_t mark = wof_arena_mark();
    uint32_t len  = 0;
    uint8_t *raw  = wof_load_file(wof_tbl_dash_picture_files[0], &len);

    if (raw)
        wof_iff_to_vport(raw, len, vp_dash);
    wof_arena_release(mark);
    wof_mem_copy(dash_colours, vp_dash->colours, sizeof dash_colours);

    /* The night dashboard for its colours, then the day one again, because that is the
     * picture the play page shows. */
    mark = wof_arena_mark();
    raw  = wof_load_file(wof_tbl_dash_picture_files[1], &len);
    if (raw)
        wof_iff_to_vport(raw, len, vp_dash);
    wof_arena_release(mark);
    wof_mem_copy(night_dash_colours, vp_dash->colours, sizeof night_dash_colours);

    mark = wof_arena_mark();
    raw  = wof_load_file(wof_tbl_dash_picture_files[0], &len);
    if (raw)
        wof_iff_to_vport(raw, len, vp_dash);
    wof_arena_release(mark);
}

static void fill_ticker(void)
{
    /* The ticker has one plane, so two colours; they come from the dashboard's table
     * rather than from a number written down here. */
    vp_ticker->colours[0] = dash_colours[0];
    vp_ticker->colours[1] = dash_colours[brightest_pen(vp_dash)];

    wof_vport_clear_planes(vp_ticker);
    wof_draw_set_target(vp_ticker);
    wof_clip_set(0, WOF_TICKER_H, 0, WOF_TICKER_W);
    wof_text_draw("TICKER 640x13x1", 15, 4, 0, 1);
}

void wof_viewer_init(void)
{
    vp_pic    = wof_vport_make(320, WOF_SCREEN_H, 5, 0);
    vp_hi     = wof_vport_make(640, WOF_SCREEN_H, 4, 1);
    vp_play   = wof_vport_make(WOF_PLAYFIELD_W, WOF_PLAYFIELD_H, 5, 0);
    vp_dash   = wof_vport_make(WOF_DASH_W, WOF_DASH_H, 4, 1);
    vp_ticker = wof_vport_make(WOF_TICKER_W, WOF_TICKER_H, 1, 1);

    if (!vp_pic || !vp_hi || !vp_play || !vp_dash || !vp_ticker)
        return;

    load_dashboard();
    fill_ticker();

    wof_s.view_page  = PAGE_LOGO;
    wof_s.view_item  = 0;
    wof_s.view_sub   = 0;
    wof_s.view_dirty = 1;
}

void wof_viewer_pass(void)
{
    if (!vp_pic || !wof_s.view_dirty)
        return;
    wof_s.view_dirty = 0;
    redraw();
}

/* The shell's keys.  A real key path - positional Amiga codes into the core's key buffer -
 * belongs to the front end of M3 (SPEC 6.2); this is four codes and a switch. */
void wof_key_press(uint8_t code)
{
    switch (code) {
    case KEY_NEXT_PAGE:
        wof_s.view_page = (uint16_t)((wof_s.view_page + 1) % PAGE_COUNT);
        wof_s.view_sub  = 0;
        break;
    case KEY_PREV_PAGE:
        wof_s.view_page = (uint16_t)((wof_s.view_page + PAGE_COUNT - 1) % PAGE_COUNT);
        wof_s.view_sub  = 0;
        break;
    case KEY_NEXT_ITEM:
        if (wof_s.view_page != PAGE_SHAPES)
            return;
        if (wof_s.view_sub + 1 < shape_pages) {
            wof_s.view_sub++;
        } else {
            wof_s.view_sub  = 0;
            wof_s.view_item = (uint16_t)((wof_s.view_item + 1) % WOF_C_COUNT);
        }
        break;
    case KEY_PREV_ITEM:
        if (wof_s.view_page != PAGE_SHAPES)
            return;
        if (wof_s.view_sub) {
            wof_s.view_sub--;
        } else {
            wof_s.view_item = (uint16_t)((wof_s.view_item + WOF_C_COUNT - 1) % WOF_C_COUNT);
            wof_s.view_sub  = 0;
        }
        break;
    default:
        return;
    }
    wof_s.view_dirty = 1;
}
