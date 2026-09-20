/* Test-only access to the core's internals.
 *
 * Compiled into tests/libwofcore.dylib and into nothing else: dist/core.wasm never sees
 * it.  The oracle tests of SPEC 7.4 need to reach the ported routines and the loaded
 * containers directly, and mirroring C structs in ctypes would tie the tests to a layout
 * that is free to change.  Every entry point here is a plain scalar interface instead.
 *
 * Nothing in src/ may call any of this. */
#include "wof.h"

enum {
    F_WBYTES, F_HEIGHT, F_HOT_X, F_HOT_Y, F_MARKER, F_SRC_Y, F_CLEAR, F_SET,
    F_PLANES, F_UNION, F_PLANE_BYTES, F_HAS_PIXELS,
};

static const wof_container_t *container(int slot)
{
    if (slot < 0 || slot >= WOF_C_COUNT)
        return 0;
    return &wof_assets.c[slot];
}

int wt_container_count(void)
{
    return WOF_C_COUNT;
}

int wt_container_shapes(int slot)
{
    const wof_container_t *c = container(slot);

    return c ? (int)c->count : -1;
}

const char *wt_container_file(int slot)
{
    const wof_container_t *c = container(slot);

    return c ? c->file : 0;
}

unsigned wt_container_name(int slot, int i)
{
    const wof_container_t *c = container(slot);

    if (!c || i < 0 || i >= (int)c->count)
        return 0;
    return c->names[i];
}

int wt_shape_field(int slot, int i, int field)
{
    const wof_container_t *c = container(slot);

    if (!c || i < 0 || i >= (int)c->count)
        return -1;

    const wof_shape_t *s = &c->shapes[i];

    switch (field) {
    case F_WBYTES:      return s->wbytes;
    case F_HEIGHT:      return s->height;
    case F_HOT_X:       return s->hot_x;
    case F_HOT_Y:       return s->hot_y;
    case F_MARKER:      return s->marker;
    case F_SRC_Y:       return s->src_y;
    case F_CLEAR:       return s->clear;
    case F_SET:         return s->set;
    case F_PLANES:      return s->planes;
    case F_UNION:       return s->union_mask;
    case F_PLANE_BYTES: return (int)s->plane_bytes;
    case F_HAS_PIXELS:  return s->pixels ? 1 : 0;
    default:            return -1;
    }
}

/* The converted pixels of one shape: 8 * wbytes columns by height rows. */
int wt_shape_pixels(int slot, int i, uint8_t *dst, int max)
{
    const wof_container_t *c = container(slot);

    if (!c || i < 0 || i >= (int)c->count)
        return -1;

    const wof_shape_t *s = &c->shapes[i];
    int n = (int)((uint32_t)s->wbytes * 8u * s->height);

    if (n > max)
        return -1;
    if (s->pixels)
        wof_mem_copy(dst, s->pixels, (uint32_t)n);
    else
        wof_mem_set(dst, 0, (uint32_t)n);
    return n;
}

int wt_shape_find(int slot, unsigned name)
{
    const wof_container_t *c = container(slot);

    return c ? wof_shape_find(c, name) : -2;
}

int wt_shape_by_index(int slot, int i)
{
    const wof_container_t *c = container(slot);

    return c ? wof_shape_by_index(c, (uint16_t)i) : -2;
}

/* The pointer table shapes_resolve built for this container, entry by entry. */
int wt_table_entry(int slot, int i)
{
    if (slot < 0 || slot >= WOF_C_COUNT || !wof_assets.table[slot])
        return -2;
    return wof_assets.table[slot][i];
}

void wt_shape_mirror(int slot, int i)
{
    const wof_container_t *c = container(slot);

    if (c && i >= 0 && i < (int)c->count)
        wof_shape_mirror_x(&c->shapes[i]);
}

void wt_shape_set_facing(int slot, int i, int facing)
{
    const wof_container_t *c = container(slot);

    if (c && i >= 0 && i < (int)c->count)
        wof_shape_set_facing(&c->shapes[i], (int16_t)facing);
}

/* One file through the ported loader, unpacked. */
int wt_load_file(const char *name, uint8_t *dst, int max)
{
    uint32_t mark = wof_arena_mark();
    uint32_t len  = 0;
    uint8_t *raw  = wof_load_file(name, &len);
    int      n    = -1;

    if (raw && (int)len <= max) {
        wof_mem_copy(dst, raw, len);
        n = (int)len;
    }
    wof_arena_release(mark);
    return n;
}

/* A viewport of the given shape on the first view's display memory.  A test that uses one
 * is not looking at what is on screen, so the block can be borrowed. */
static int scratch_vport(wof_vport_t *v, int width, int height, int depth)
{
    uint32_t at = 0;

    wof_mem_set(v, 0, sizeof *v);
    wof_vport_init_bitmap(v, &at, (uint16_t)width, (uint16_t)height, (uint8_t)depth);
    v->next = WOF_VP_NONE;
    return at <= WOF_VRAM_BYTES;
}

/* One picture through the ported ILBM reader, into a viewport of the given shape. */
int wt_iff_decode(const char *file, int width, int height, int depth,
                  uint8_t *pixels, uint16_t *colours)
{
    uint32_t mark = wof_arena_mark();
    uint32_t len  = 0;
    uint8_t *raw  = wof_load_file(file, &len);
    wof_vport_t v;
    int ok = 0;

    if (raw && scratch_vport(&v, width, height, depth)) {
        ok = wof_iff_to_vport(raw, len, &v);
        if (ok) {
            wof_mem_copy(pixels, wof_vport_pixels(&v), (uint32_t)v.bytes_per_row * 8u * v.rows);
            wof_mem_copy(colours, v.colours, sizeof v.colours);
        }
    }
    wof_arena_release(mark);
    return ok;
}

int wt_cmap_file(const char *name, uint16_t *out)
{
    uint32_t mark = wof_arena_mark();
    uint32_t len  = 0;
    uint8_t *raw  = wof_load_file(name, &len);

    if (raw)
        wof_cmap_file_to_table(raw, len, out);
    wof_arena_release(mark);
    return raw ? 1 : 0;
}

int wt_text_width(const char *s, int len)
{
    return wof_text_width(s, (uint16_t)len);
}

int wt_text_render(const char *s, int len, uint8_t *buffer, int x, int row, int justify,
                   int buf_w, int buf_h)
{
    return wof_text_render(s, (uint16_t)len, buffer, (int16_t)x, (int16_t)row,
                           (int16_t)justify, (int16_t)buf_w, (int16_t)buf_h);
}

int wt_font_height(void)
{
    return wof_font_height();
}

/* One blit onto a target of the given shape, over the given background.  This is the
 * comparison the blitter model in tests/blitter.py is run against. */
int wt_blit(int slot, int i, int bytes_per_row, int rows, int depth,
            int top, int bottom, int left, int right, int x, int y,
            const uint8_t *background, uint8_t *out)
{
    const wof_container_t *c = container(slot);
    wof_vport_t v;
    uint32_t    n = (uint32_t)bytes_per_row * 8u * rows;

    if (!c || i < 0 || i >= (int)c->count)
        return -1;

    if (n > WOF_VRAM_BYTES || !scratch_vport(&v, bytes_per_row * 8, rows, depth))
        return -1;
    v.hires = 1;

    wof_mem_copy(wof_vport_pixels(&v), background, n);
    wof_draw_set_target(&v);
    wof_clip_set((int16_t)top, (int16_t)bottom, (int16_t)left, (int16_t)right);
    wof_shape_draw(&c->shapes[i], (int16_t)x, (int16_t)y);
    wof_mem_copy(out, wof_vport_pixels(&v), n);
    return (int)n;
}

/* ------------------------------------------------------ the registry of src/globals.def
 *
 * SPEC 7.2: every ported global gets an entry in a registry, and the test harness uses it
 * to copy state between the oracle and the port with byte-order conversion.  The entries
 * are read here rather than mirrored in Python, so that a global added to globals.def is
 * visible to the tests without a second edit.  An element is read and written as an
 * integer, which is what makes the byte order the host's problem and not the test's.
 */
typedef struct {
    const char *name;
    uint32_t    elem;       /* bytes per element */
    uint32_t    count;      /* elements */
    uint32_t    addr;       /* the original's address, SPEC 3.2 load layout */
    uint32_t    offset;     /* inside wof_globals_t */
} wt_global_t;

static const wt_global_t wt_globals[] = {
#define WOF_GLOBAL(n, t, a)          { #n, (uint32_t)sizeof(t), 1u, (uint32_t)(a), \
                                       (uint32_t)offsetof(wof_globals_t, n) },
#define WOF_GLOBAL_ARRAY(n, t, c, a) { #n, (uint32_t)sizeof(t), (uint32_t)(c), (uint32_t)(a), \
                                       (uint32_t)offsetof(wof_globals_t, n) },
#include "globals.def"
#undef WOF_GLOBAL
#undef WOF_GLOBAL_ARRAY
};

int wt_global_count(void)
{
    return (int)(sizeof wt_globals / sizeof wt_globals[0]);
}

int wt_globals_bytes(void)
{
    return (int)sizeof(wof_globals_t);
}

static const wt_global_t *entry_at(int i)
{
    return (i < 0 || i >= wt_global_count()) ? 0 : &wt_globals[i];
}

const char *wt_global_name(int i)
{
    const wt_global_t *e = entry_at(i);

    return e ? e->name : 0;
}

int wt_global_elem(int i)   { const wt_global_t *e = entry_at(i); return e ? (int)e->elem : -1; }
int wt_global_elems(int i)  { const wt_global_t *e = entry_at(i); return e ? (int)e->count : -1; }
unsigned wt_global_addr(int i)   { const wt_global_t *e = entry_at(i); return e ? e->addr : 0u; }
unsigned wt_global_offset(int i) { const wt_global_t *e = entry_at(i); return e ? e->offset : 0u; }

static uint8_t *element(int i, int index, uint32_t *size)
{
    const wt_global_t *e = entry_at(i);

    if (!e || index < 0 || (uint32_t)index >= e->count)
        return 0;
    *size = e->elem;
    return (uint8_t *)&wof_s.g + e->offset + (uint32_t)index * e->elem;
}

unsigned wt_global_get(int i, int index)
{
    uint32_t size = 0;
    const uint8_t *at = element(i, index, &size);
    uint32_t value = 0;

    if (!at)
        return 0u;
    for (uint32_t b = 0; b < size; b++)               /* host order, both targets little */
        value |= (uint32_t)at[b] << (8 * b);
    return value;
}

void wt_global_set(int i, int index, unsigned value)
{
    uint32_t size = 0;
    uint8_t *at = element(i, index, &size);

    if (!at)
        return;
    for (uint32_t b = 0; b < size; b++)
        at[b] = (uint8_t)(value >> (8 * b));
}

/* The two front-end flags the port's key layer asks about (SPEC 6.2).  A test sets them
 * directly so that the layer can be checked in all four of its states without first
 * driving the front end into each of them. */
void wt_front_set(int editing, int briefing)
{
    wof_f.editing  = (uint16_t)(editing ? 1 : 0);
    wof_f.briefing = (uint16_t)(briefing ? 1 : 0);
}

/* ------------------------------------------------------- the screens, waits and fades
 *
 * A coroutine is resumed once per pass, and a pass follows a VBlank, so a test drives one
 * by alternating wof_vblank with a resume and counting the rounds.  These helpers do that
 * for one routine at a time, which is what a differential test against the original needs:
 * the original's own routine runs under the oracle with the same starting tables.
 */

/* A view of one or two viewports on view A, made the front view, so that the fades have
 * something to fade.  Returns the number of viewports it laid out. */
int wt_view_setup(int depth, int depth2, int has_colours2)
{
    wof_display_init();
    wof_f.view_first[WOF_VIEW_A] = WOF_VP_A1;
    wof_f.vport[WOF_VP_A1].width  = 320;
    wof_f.vport[WOF_VP_A1].height = 8;
    wof_f.vport[WOF_VP_A1].depth  = (uint8_t)depth;
    wof_f.vport[WOF_VP_A1].next   = WOF_VP_NONE;
    if (depth2 > 0) {
        wof_f.vport[WOF_VP_A1].next   = WOF_VP_A2;
        wof_f.vport[WOF_VP_A2].width  = 640;
        wof_f.vport[WOF_VP_A2].height = 8;
        wof_f.vport[WOF_VP_A2].depth  = (uint8_t)depth2;
        wof_f.vport[WOF_VP_A2].next   = WOF_VP_NONE;
    }
    wof_view_layout(WOF_VIEW_A);
    wof_f.vport[WOF_VP_A1].has_colours2 = (uint8_t)(has_colours2 != 0);
    wof_view_show(WOF_VIEW_A);
    return depth2 > 0 ? 2 : 1;
}

static wof_vport_t *shim_vport(int which)
{
    return &wof_f.vport[which ? WOF_VP_A2 : WOF_VP_A1];
}

void wt_vport_colours_set(int which, int table, const uint16_t *src)
{
    wof_vport_t *v = shim_vport(which);

    for (uint32_t i = 0; i < WOF_PAL_COLOURS; i++)
        (table ? v->colours2 : v->colours)[i] = src[i];
}

void wt_vport_colours_get(int which, int table, uint16_t *dst)
{
    const wof_vport_t *v = shim_vport(which);

    for (uint32_t i = 0; i < WOF_PAL_COLOURS; i++)
        dst[i] = (table ? v->colours2 : v->colours)[i];
}

/* One whole fade, run to its end.  Returns the number of passes it took, so that the
 * provisional VBlanks-per-step setting can be checked as well as the arithmetic. */
int wt_fade_run(const uint16_t *target1, const uint16_t *target2, int pair)
{
    int passes = 0;

    wof_f.co_fade.line = 0;
    while (wof_fade(target1, target2, pair) == WOF_CO_WAIT && passes < 10000) {
        wof_vblank(0);
        passes++;
    }
    return passes;
}

/* wait_frames_or_fire, wait_input_release and menu_input, each driven the way the shell
 * drives the front end: one VBlank, one resume.  `raw` is the controller state of every
 * VBlank; `raw_after` takes over once `switch_at` VBlanks have gone by. */
typedef struct { uint8_t raw, raw_after; int switch_at; } wt_drive_t;

static void wt_vblank_at(const wt_drive_t *d, int n)
{
    wof_vblank(d->switch_at >= 0 && n >= d->switch_at ? d->raw_after : d->raw);
}

int wt_frames_run(int n, int raw, int raw_after, int switch_at)
{
    wt_drive_t d = { (uint8_t)raw, (uint8_t)raw_after, switch_at };
    int passes = 0;

    wt_vblank_at(&d, 0);                 /* the controller state the routine is entered with */
    wof_f.co_frames.line = 0;
    while (wof_wait_frames_or_fire((uint16_t)n) == WOF_CO_WAIT && passes < 10000) {
        passes++;
        wt_vblank_at(&d, passes);
    }
    return passes;
}

int wt_release_run(int raw, int raw_after, int switch_at)
{
    wt_drive_t d = { (uint8_t)raw, (uint8_t)raw_after, switch_at };
    int passes = 0;

    wt_vblank_at(&d, 0);
    wof_f.co_release.line = 0;
    while (wof_wait_input_release() == WOF_CO_WAIT && passes < 10000) {
        passes++;
        wt_vblank_at(&d, passes);
    }
    return passes;
}

int wt_menu_run(int timeout, int raw, int limit, int *rounds)
{
    int passes = 0;

    wof_vblank((uint8_t)raw);
    wof_f.co_menu.line = 0;
    while (wof_menu_input((uint16_t)timeout) == WOF_CO_WAIT && passes < limit) {
        passes++;
        wof_vblank((uint8_t)raw);
    }
    *rounds = passes;
    return wof_menu_result();
}

/* The story scroller's ring and its two grey ramps, as bands: how many output rows the
 * front view covers, how many palettes they need, and the colour a given row is drawn in. */
int wt_story_bands(int scroll, int ring_at, int ramp, int row, unsigned *colour)
{
    wof_vport_t *v = &wof_f.vport[WOF_VP_A1];

    wof_display_init();
    wof_f.view_first[WOF_VIEW_A] = WOF_VP_A1;
    v->width  = 640;
    v->height = 200;
    v->depth  = 1;
    v->next   = WOF_VP_NONE;
    wof_view_layout(WOF_VIEW_A);
    v->out_y     = 5;
    v->disp_rows = 230;
    v->scroll    = (uint16_t)scroll;
    v->ring_at   = (uint16_t)ring_at;
    v->ramp      = (uint16_t)ramp;
    wof_view_show(WOF_VIEW_A);
    wof_screen_from_front_view();

    const uint16_t *rows = wof_palette_rows();
    const uint32_t *pal  = wof_palettes();
    int used = 0;

    for (uint32_t y = 0; y < WOF_FB_H; y++)
        if (rows[y] + 1 > used)
            used = rows[y] + 1;
    if (colour)
        *colour = (row >= 0 && row < (int)WOF_FB_H)
                ? pal[rows[row] * WOF_PAL_COLOURS + 1] : 0;
    return used;
}

/* ---------------------------------------------------------- what the port did (SPEC 8) */

#ifdef WOF_TRACE
int wt_trace_count(void)   { return (int)wof_trace_count(); }
int wt_trace_dropped(void) { return (int)wof_trace_dropped(); }
void wt_trace_reset(void)  { wof_trace_reset(); }

/* One record, spelled out for ctypes: the routine, the VBlank, its four numbers and its
 * string.  `what` and `text` are copied into the caller's buffers. */
int wt_trace_get(int i, char *what, char *text, int *numbers)
{
    const wof_trace_t *r = wof_trace_at((uint32_t)i);

    if (!r)
        return 0;
    for (int n = 0; n < 16; n++)
        what[n] = r->what[n];
    for (int n = 0; n < WOF_TRACE_TEXT; n++)
        text[n] = r->text[n];
    numbers[0] = (int)r->vblank;
    numbers[1] = r->a;
    numbers[2] = r->b;
    numbers[3] = r->c;
    numbers[4] = r->d;
    return 1;
}
#endif

/* The music calls the front end made, with the VBlank each one happened at. */
int wt_music_count(void)        { return wof_f.music_count; }
int wt_music_song(int i)        { return i < wof_f.music_count ? wof_f.music_song[i] : -1; }
int wt_music_vblank(int i)      { return i < wof_f.music_count ? (int)wof_f.music_vblank[i] : -1; }

/* Where the front end stands: which screen, which viewports, what is on the output. */
int wt_front_line(void)         { return wof_f.co_main.line; }
int wt_front_vport_field(int which, int field)
{
    const wof_vport_t *v = which ? wof_back_vport() : wof_front_vport();

    if (!v)
        return -1;
    switch (field) {
    case 0:  return v->width;
    case 1:  return v->height;
    case 2:  return v->depth;
    case 3:  return v->out_y;
    case 4:  return v->disp_rows;
    case 5:  return v->scroll;
    case 6:  return v->ring_at;
    case 7:  return v->ramp;
    case 8:  return v->hires;
    case 9:  return v->next;
    default: return -1;
    }
}

/* How often the front end has reached the mission, which in M3 is a stand-in.  A test
 * replays a headless schedule up to that point and compares the state there with the
 * harness's dump at its step S. */
int wt_mission_count(void) { return wof_f.mission_count; }

#ifdef WOF_TRACE
/* One element of a global as it stood where the front end ended (src/trace.c). */
unsigned wt_global_get_at_mission(int i, int index)
{
    const wt_global_t   *e = entry_at(i);
    const wof_globals_t *g = wof_trace_globals_at();
    uint32_t value = 0;

    if (!e || !g || index < 0 || (uint32_t)index >= e->count)
        return 0u;

    const uint8_t *at = (const uint8_t *)g + e->offset + (uint32_t)index * e->elem;

    for (uint32_t b = 0; b < e->elem; b++)
        value |= (uint32_t)at[b] << (8 * b);
    return value;
}
#endif

/* The RastPort fields the front end sets, for the test that asks what pen the briefing's
 * text came out in (tests/test_front_port.py). */
int wt_front_vport_pen(int which, int field)
{
    const wof_vport_t *v = which ? wof_back_vport() : wof_front_vport();

    if (!v)
        return -1;
    switch (field) {
    case 0:  return v->apen;
    case 1:  return v->bpen;
    case 2:  return v->drmd;
    default: return -1;
    }
}

/* --------------------------------------------- the high-score file and the line editor */

/* The 360-byte table, as the tests hand it about.  It is the file's bytes, big-endian. */
void wt_hs_get(uint8_t *dst)  { wof_mem_copy(dst, wof_f.hiscore, sizeof wof_f.hiscore); }
void wt_hs_put(const uint8_t *src) { wof_mem_copy(wof_f.hiscore, src, sizeof wof_f.hiscore); }
void wt_hs_load(void)  { wof_high_score_load(); }
void wt_hs_sort(void)  { wof_high_score_sort(); }
void wt_hs_save(void)  { wof_high_score_save(); }

/* One whole run of the line editor: the keys go into the buffer first, so that the reader
 * never has to wait, and the coroutine is resumed until it is done.  A VBlank goes by
 * between resumes, the way the shell drives it. */
int wt_text_input_run(char *buffer, int max, int x, int y,
                      const uint8_t *codes, const uint16_t *quals, int n)
{
    wof_vport_t v;
    int rounds = 0;

    if (!scratch_vport(&v, 320, 200, 4))
        return -1000;
    wof_draw_set_target(&v);
    wof_clip_set_full();

    /* The buffer is ten deep, so the keys are fed one at a time as the editor takes them,
     * which is also how a player's hands deliver them. */
    int next = 0;

    wof_keys_init();
    if (next < n)
        wof_key(codes[next], quals[next]), next++;

    wof_f.co_text.line = 0;
    while (wof_text_input(buffer, (uint16_t)max, (int16_t)x, (int16_t)y) == WOF_CO_WAIT
           && rounds < 10000) {
        wof_vblank(0);
        rounds++;
        if (!wof_key_available() && next < n)
            wof_key(codes[next], quals[next]), next++;
    }
    return wof_text_result();
}

/* The game's own directory in ExNext order, which is what the dialog's list is made of. */
const char *wt_dir_entry(int index)
{
    return wof_fs_dir_entry((uint32_t)index);
}

int wt_fs_write(const char *name, const uint8_t *data, int len)
{
    return wof_fs_write(name, data, (uint32_t)len);
}

int wt_fs_delete(const char *name)
{
    return wof_fs_delete(name);
}

void wt_fs_writes_reset(void)
{
    wof_fs_writes_reset();
}

int wt_fs_written_count(void)            { return (int)wof_fs_written_count(); }
const char *wt_fs_written_name(int i)    { return wof_fs_written_name((uint32_t)i); }
int wt_fs_written_size(int i)            { return (int)wof_fs_written_size((uint32_t)i); }

int wt_fs_written_bytes(int i, uint8_t *dst, int max)
{
    uint32_t len = 0;
    const uint8_t *data = wof_fs_written_data((uint32_t)i, &len);

    if (!data || (int)len > max)
        return -1;
    wof_mem_copy(dst, data, len);
    return (int)len;
}

void wt_path_sanitise(char *name) { wof_path_sanitise(name); }

/* high_score_entry to its end, with the keys its name entry is to be given.  It needs a
 * screen, which screen_dialog builds; the coroutine is resumed until it is done. */
int wt_hs_entry_run(const uint8_t *codes, const uint16_t *quals, int n)
{
    int rounds = 0;
    int next = 0;

    wof_keys_init();
    wof_set_fade_vblanks(0);
    wof_f.co_inner.line = 0;
    while (wof_high_score_entry() == WOF_CO_WAIT && rounds < 20000) {
        wof_vblank(0);
        rounds++;
        /* One key at a time, as the editor takes them; once they run out, Return, so that
         * a test that supplies too few does not spin until the limit. */
        if (!wof_key_available() && wof_f.editing)
            next < n ? (wof_key(codes[next], quals[next]), next++) : (wof_key(0x44, 0), 0);
    }
    return rounds;
}

/* The whole load and save dialog, with its keys fed one at a time as it takes them. */
int wt_dialog_run(int mode, const uint8_t *codes, const uint16_t *quals, int n, int *rounds)
{
    int at = 0;

    *rounds = 0;
    wof_keys_init();
    wof_set_fade_vblanks(0);
    wof_display_init();
    wof_f.co_inner.line = 0;
    while (wof_load_save_dialog((uint16_t)mode) == WOF_CO_WAIT && *rounds < 20000) {
        wof_vblank(0);
        (*rounds)++;
        if (!wof_key_available() && at < n)
            wof_key(codes[at], quals[at]), at++;
    }
    return (int16_t)wof_f.dialog_result;
}

const char *wt_dialog_name(int slot)
{
    return slot >= 0 && slot < 6 ? wof_f.dialog_names[slot] : 0;
}

int wt_dialog_count(void) { return wof_f.dialog_count; }

/* ------------------------------------------------ SPEC 10 point 13: the floating point
 *
 * One entry for all nine operations of src/ffp.c, so that the differential test can loop
 * over them by name.  `out` takes D0, D1, the condition codes and the trap the original
 * would have taken; the return value says whether the operation exists. */
int wt_ffp(int op, uint32_t d0, uint32_t d1, uint32_t *out)
{
    wof_ffp_t r;

    switch (op) {
    case 0:  r = wof_ffp_add_cc(d0, d1); break;
    case 1:  r = wof_ffp_sub_cc(d0, d1); break;
    case 2:  r = wof_ffp_mul_cc(d0, d1); break;
    case 3:  r = wof_ffp_div_cc(d0, d1); break;
    case 4:  r = wof_ffp_cmp_cc(d0, d1); break;
    case 5:  r = wof_ffp_tst_cc(d0, d1); break;
    case 6:  r = wof_ffp_neg_cc(d0, d1); break;
    case 7:  r = wof_ffp_fix_cc(d0, d1); break;
    case 8:  r = wof_ffp_flt_cc(d0, d1); break;
    default: return 0;
    }
    out[0] = r.d0;
    out[1] = r.d1;
    out[2] = r.ccr;
    out[3] = r.trap;
    return 1;
}

uint32_t wt_ffp_traps(void)
{
    return wof_ffp_traps;
}

void wt_ffp_traps_reset(void)
{
    wof_ffp_traps = 0;
}
