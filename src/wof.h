/* Wings of Fury - core interface and shared declarations (SPEC.md section 6.1).
 *
 * C11, freestanding: no libc, no allocation after initialisation, no floating point in
 * game logic, no dependence on wall-clock time.  The same sources compile for
 * wasm32-freestanding (dist/core.wasm) and natively (tests/libwofcore.dylib).
 */
#ifndef WOF_H
#define WOF_H

#include <stdint.h>
#include <stddef.h>

#if defined(__wasm__)
#define WOF_API(name) __attribute__((export_name(#name), used))
#else
#define WOF_API(name) __attribute__((visibility("default"), used))
#endif

/* ------------------------------------------------------------------ display geometry */

/* SPEC 6.4 and re/notes/display.md.  The original's play screen is three stacked
 * viewports, 214 display lines in all: the playfield (320 x 162 low resolution, 5 planes)
 * at line 0, the dashboard (640 x 37 high resolution, 4 planes) at line 163 and the
 * message ticker (640 x 13 high resolution, 1 plane) at line 201; lines 162 and 200 are
 * blank.  The output is 640 pixels wide with low-resolution pixels doubled, so the core's
 * picture is 640 x 214.  The front-end screens are 200 lines and leave the rest blank. */
#define WOF_FB_W        640
#define WOF_FB_H        214

#define WOF_PLAYFIELD_W 320
#define WOF_PLAYFIELD_H 162
#define WOF_DASH_W      640
#define WOF_DASH_H      37
#define WOF_DASH_Y      163
#define WOF_TICKER_W    640
#define WOF_TICKER_H    13
#define WOF_TICKER_Y    201
#define WOF_SCREEN_H    200          /* the front-end screens */

/* A viewport's colour table is 32 words on the machine whatever its depth is. */
#define WOF_PAL_COLOURS 32

/* One palette per viewport that can be on screen at once, plus the blank one at index 0.
 * wof_palette_rows() says which applies to each output row.  The mechanisms of SPEC 6.4
 * that need more of them - the sky/ocean split, the ticker ramp - arrive with M4. */
#define WOF_PAL_COUNT   5
#define WOF_PAL_BLANK   0

/* A palette entry is RGBA in memory order (0xAABBGGRR as a little-endian uint32), which is
 * what canvas ImageData expects, so the shell copies the table without converting it. */
#define WOF_RGBA(r, g, b) (0xFF000000u | ((uint32_t)(b) << 16) | ((uint32_t)(g) << 8) | (uint32_t)(r))

/* ------------------------------------------------------------------- display list 6.4 */

/* One entry per shape draw, for the enhanced renderer that SPEC 6.4 keeps the door open
 * for.  The classic renderer ignores it. */
typedef struct {
    char     name[4];   /* the shape's 4-character name, SPEC 3.5 */
    int16_t  x, y;
    uint16_t layer;
    uint16_t flags;
    uint16_t owner;     /* object id, 0 when the draw belongs to no object */
} wof_draw_t;

#define WOF_DRAW_MAX 1024

void wof_draw_list_reset(void);
void wof_draw_list_add(uint32_t name, int16_t x, int16_t y, uint16_t layer,
                       uint16_t flags, uint16_t owner);

/* --------------------------------------------------------------- exported interface */

WOF_API(wof_init)              void            wof_init(uint32_t seed, const uint8_t *fs, uint32_t fs_len);
WOF_API(wof_set_video_hz)      void            wof_set_video_hz(int hz);
WOF_API(wof_vblank)            void            wof_vblank(uint8_t raw);
WOF_API(wof_key)               void            wof_key(uint8_t code, uint16_t qualifier);
WOF_API(wof_port_key)          void            wof_port_key(uint8_t code, uint16_t qualifier);
WOF_API(wof_set_invert_vertical) void          wof_set_invert_vertical(int on);
WOF_API(wof_invert_vertical)   int             wof_invert_vertical(void);
WOF_API(wof_pass)              void            wof_pass(void);
WOF_API(wof_framebuffer)       const uint8_t  *wof_framebuffer(void);
WOF_API(wof_palette_rows)      const uint16_t *wof_palette_rows(void);
WOF_API(wof_palettes)          const uint32_t *wof_palettes(void);
WOF_API(wof_display_list)      const void     *wof_display_list(uint32_t *count);
WOF_API(wof_audio_render)      void            wof_audio_render(int16_t *stereo, uint32_t frames, uint32_t rate);
WOF_API(wof_state_size)        uint32_t        wof_state_size(void);
WOF_API(wof_state_save)        void            wof_state_save(uint8_t *dst);
WOF_API(wof_state_load)        void            wof_state_load(const uint8_t *src);

/* Additions to SPEC 6.1.  The signatures there "may grow"; these are the queries the shell
 * needs in order to hard-code nothing, plus the arena the shell hands the file blob in. */
WOF_API(wof_framebuffer_width)  uint32_t  wof_framebuffer_width(void);
WOF_API(wof_framebuffer_height) uint32_t  wof_framebuffer_height(void);
WOF_API(wof_palette_count)      uint32_t  wof_palette_count(void);   /* palettes in wof_palettes() */
WOF_API(wof_palette_colours)    uint32_t  wof_palette_colours(void); /* entries per palette */
WOF_API(wof_alloc)              void     *wof_alloc(uint32_t bytes); /* static arena, never freed */
WOF_API(wof_arena_reset)        void      wof_arena_reset(void);     /* host only, before a fresh core */
WOF_API(wof_arena_size)         uint32_t  wof_arena_size(void);
WOF_API(wof_arena_used)         uint32_t  wof_arena_used(void);
WOF_API(wof_fs_count)           uint32_t  wof_fs_count(void);        /* files in the blob wof_init got */
WOF_API(wof_vblank_count)       uint32_t  wof_vblank_count(void);
WOF_API(wof_tick_count)         uint32_t  wof_tick_count(void);
WOF_API(wof_pass_count)         uint32_t  wof_pass_count(void);
WOF_API(wof_assets_ready)       uint32_t  wof_assets_ready(void);    /* 0 while an asset is missing */

/* --------------------------------------------------------------- the front end (6.3) */

/* What the front end keeps between one wof_pass and the next: the resume points of the
 * coroutines and every local that lives across a wait (SPEC 6.3).  It grows screen by
 * screen; what is here is what the key layer of SPEC 6.2 asks the core about. */
typedef struct {
    uint16_t editing;    /* text_input has the line: every key passes as it came */
    uint16_t briefing;   /* mission_briefing is on screen: KeyR restarts from there too */
} wof_front_t;

/* ---------------------------------------------------------------- the ported globals */

/* The original addresses every global as d16(a4) from one small-data base.  src/globals.def
 * is the port's version of that page: one entry per ported global, with the original's name
 * and address (SPEC 7.2).  The struct lives inside the core's state, so a ported global is
 * part of a save state by construction and the tests can map it to its original address. */
typedef struct {
#define WOF_GLOBAL(name, type, addr)              type name;
#define WOF_GLOBAL_ARRAY(name, type, count, addr) type name[count];
#include "globals.def"
#undef WOF_GLOBAL
#undef WOF_GLOBAL_ARRAY
} wof_globals_t;

/* ------------------------------------------------------------------------ core state */

/* Everything the core may change while running, in one struct, so that wof_state_save is a
 * copy and adding state cannot silently break the round trip.  Neither the framebuffer nor
 * the loaded assets are in here: wof_pass redraws the one from this state and the other is
 * read-only after wof_init.  Both targets are little-endian, so the saved bytes are the
 * struct's bytes; if a big-endian target ever appears this needs accessors. */
typedef struct {
    uint32_t magic;
    uint32_t version;
    uint32_t seed;          /* as passed to wof_init */
    uint32_t entropy;       /* state of the entropy stream, SPEC 7.3 */
    uint32_t vblanks;       /* VBlanks since wof_init */
    uint32_t ticks;         /* logic ticks since wof_init, one per 4 VBlanks */
    uint32_t passes;        /* wof_pass calls since wof_init */
    uint32_t tone_phase_l;  /* test tone, 32-bit phase, one turn per cycle */
    uint32_t tone_phase_r;
    uint16_t video_hz;      /* 60 or 50 */
    uint16_t raw;           /* the most recent VBlank's controller state, opposing
                             * directions cancelled: the port's JOY1DAT and CIA-A PRA */
    uint16_t view_page;     /* M1 viewer: which page is on screen */
    uint16_t view_item;     /* M1 viewer: which container the browser shows */
    uint16_t view_sub;      /* M1 viewer: which page of that container */
    uint16_t view_dirty;    /* M1 viewer: the picture needs redrawing */
    uint16_t invert_pref;   /* the shell's remembered vertical flip, 0 or 1 */
    uint16_t invert_given;  /* whether the shell ever handed one over (SPEC 6.1) */
    wof_globals_t g;        /* the original's own globals, src/globals.def */
    wof_front_t   f;        /* the front end: coroutines, screens, dialogs (SPEC 6.3) */
} wof_state_t;

#define WOF_STATE_MAGIC   0x574F4653u  /* 'WOFS' */
#define WOF_STATE_VERSION 3u

extern wof_state_t wof_s;

/* The ported globals read as themselves: wof_g.key_count is the original's key_count. */
#define wof_g (wof_s.g)
#define wof_f (wof_s.f)

/* ------------------------------------------------------------------ memory and blocks */

void     wof_mem_set(void *dst, uint8_t value, uint32_t n);
void     wof_mem_copy(void *dst, const void *src, uint32_t n);
int      wof_mem_equal(const void *a, const void *b, uint32_t n);

/* The arena replaces exec AllocMem (SPEC 3.4).  wof_alloc grows from the bottom and is
 * never freed; the buffer load_file reads and unpacks a file into comes from the top with
 * wof_scratch_alloc and is given back with a mark, which is the only thing the original's
 * Free of a just-loaded file amounts to here. */
uint32_t wof_arena_mark(void);
void     wof_arena_release(uint32_t mark);
void    *wof_scratch_alloc(uint32_t bytes);

/* ------------------------------------------------------------------------ entropy 7.3 */

uint16_t wof_entropy_next(void);            /* one value per rand_beam call */
void     wof_entropy_seed(uint32_t seed);

/* ------------------------------------------------- the packed file system and dos glue */

int            wof_fs_open(const uint8_t *blob, uint32_t len);
const uint8_t *wof_fs_find(const char *name, uint32_t *len);
const char    *wof_fs_name(uint32_t index, uint32_t *len);

/* The dos.library calls of SPEC 3.4 that the ported loaders make.  A lock and a file
 * handle are both an index into the directory plus a read position, so neither allocates. */
typedef struct {
    int32_t  entry;     /* directory index, -1 when the handle is closed */
    uint32_t pos;       /* read position */
} wof_file_t;

int32_t  wof_dos_lock(const char *name);                       /* -1 when not found */
int32_t  wof_dos_examine_size(int32_t lock);                   /* fib_Size, -1 on error */
void     wof_dos_unlock(int32_t lock);
int      wof_dos_open(wof_file_t *f, const char *name);        /* 0 when not found */
int32_t  wof_dos_read(wof_file_t *f, uint8_t *dst, int32_t n); /* bytes read */
void     wof_dos_close(wof_file_t *f);
int32_t  wof_dos_ioerr(void);

/* ---------------------------------------------------------------------- file loading */

/* Port of load_file (orig 0x01FF16): the whole file, Rpck-unwrapped, in arena scratch.
 * The result is valid until the arena is released past it. */
uint8_t *wof_load_file(const char *name, uint32_t *len);
void     wof_rpck_unpack(const uint8_t *src, uint32_t srclen, uint8_t *dst, uint32_t dstlen);

/* --------------------------------------------------------------------------- shapes */

#define WOF_NO_SHAPE ((int16_t)-1)

/* One record of a PPkc container, converted to indexed pixels at load (SPEC 6.4).  The
 * header fields keep the original's names and meanings (re/notes/shapes.md); `pixels` is
 * what the plane data and the plane masks become, and `union_mask`, `planes`, `clear` and
 * `set` are what the blit still needs from the record. */
typedef struct {
    uint16_t wbytes;       /* +0   width in bytes; the pixel width is 8x this */
    uint16_t height;       /* +2 */
    int16_t  hot_x;        /* +4   subtracted from the draw position by the callers */
    int16_t  hot_y;        /* +6 */
    uint16_t marker;       /* +8   source x, or the mirror marker for hellcat and Torpedo */
    uint16_t src_y;        /* +10 */
    uint8_t  clear;        /* +12  planes cleared under the mask */
    uint8_t  set;          /* +13  planes set under the mask */
    uint8_t  planes;       /* number of stored planes */
    uint8_t  union_mask;   /* OR of the destination plane masks */
    uint32_t plane_bytes;  /* wbytes * height, the size the mask rule tests */
    uint32_t name;         /* the container's 4-character name, for the display list */
    uint8_t *pixels;       /* 8*wbytes x height indexed pixels, or 0 when nothing is stored */
} wof_shape_t;

typedef struct {
    uint16_t       count;
    wof_shape_t   *shapes;
    const uint32_t *names;   /* count 4-character names, big-endian longs, ascending */
    const char    *file;     /* the name the game asks for, for the viewer */
} wof_container_t;

int16_t  wof_shape_find(const wof_container_t *c, uint32_t name);   /* orig 0x020560 */
int16_t  wof_shape_by_index(const wof_container_t *c, uint16_t i);  /* orig 0x02050E */
int16_t *wof_shapes_resolve(const wof_container_t *c, const uint32_t *list, uint16_t count);
int      wof_shapes_load(wof_container_t *c, const char *file, const uint32_t *list);
void     wof_shape_mirror_x(wof_shape_t *s);                        /* orig 0x015B58 */
void     wof_shape_set_facing(wof_shape_t *s, int16_t facing);      /* the +8 marker rule */
uint16_t wof_namelist_count(const uint32_t *list);

/* --------------------------------------------------------------------- viewports 6.4 */

/* The port's stand-in for one of the original's ViewPort records (re/notes/display.md).
 * The planar BitMap becomes one indexed surface; `bytes_per_row` is kept because the
 * picture decoder writes rows back to back at the picture's stride, not the viewport's. */
typedef struct {
    uint16_t width;          /* displayed pixels        (vport +0xA8) */
    uint16_t height;         /* displayed rows          (vport +0xAA) */
    uint16_t bytes_per_row;  /* BitMap BytesPerRow      (vport +4) */
    uint16_t rows;           /* BitMap Rows             (vport +6) */
    uint8_t  depth;          /* BitMap Depth            (vport +9) */
    uint8_t  hires;          /* 0 = low resolution, doubled on the 640-wide output */
    uint8_t *pixels;         /* indexed, 8*bytes_per_row x rows */
    uint16_t colours[WOF_PAL_COLOURS];   /* colour table 1, 12-bit Amiga words (vport +0x98) */
} wof_vport_t;

wof_vport_t *wof_vport_make(uint16_t width, uint16_t height, uint8_t depth, uint8_t hires);
void         wof_vport_clear_planes(wof_vport_t *v);     /* orig 0x01A74C */

/* A screen is the stack of viewports that is on the output at one moment.  Every band
 * names its source viewport, where it starts on the output and which palette its rows go
 * through, which is how SPEC 6.4's per-row palette interface is fed. */
#define WOF_MAX_BANDS 6

typedef struct {
    const wof_vport_t *vp;
    uint16_t out_y;
    uint16_t rows;
    uint16_t src_y;
    uint16_t palette;
} wof_band_t;

void wof_screen_reset(void);
void wof_screen_band(const wof_vport_t *vp, uint16_t out_y, uint16_t rows, uint16_t src_y,
                     uint16_t palette);
void wof_screen_present(void);           /* bands and colour tables -> framebuffer, palettes */

void wof_video_init(void);

/* Amiga 12-bit colour word to the shell's RGBA, nibble replicated into both halves. */
uint32_t wof_colour_rgba(uint16_t rgb4);

/* orig 0x016FF6.  16-step fade arithmetic; the carry between components is behaviour. */
uint16_t wof_colour_lerp(int16_t step, uint16_t from, uint16_t to);

/* ---------------------------------------------------------------------- the ILBM path */

int  wof_iff_to_vport(const uint8_t *file, uint32_t len, wof_vport_t *v);  /* orig 0x01A548 */
void wof_cmap_file_to_table(const uint8_t *file, uint32_t len, uint16_t *table); /* 0x016DD6 */

/* ------------------------------------------------------------------------- drawing */

typedef struct {
    uint8_t *pixels;
    int32_t  stride;       /* pixels per row = 8 * bytes_per_row */
    int32_t  width;        /* 8 * bytes_per_row */
    int32_t  height;       /* BitMap Rows */
    uint8_t  mask;         /* depth mask, 5 planes give 0x1F  (RastPort Mask, +0x18) */
} wof_target_t;

void wof_draw_set_target(wof_vport_t *v);                              /* orig 0x02124A */
void wof_clip_set(int16_t top, int16_t bottom, int16_t left, int16_t right); /* orig 0x02129C */
void wof_clip_set_full(void);                                          /* orig 0x021280 */
void wof_shape_draw(const wof_shape_t *s, int16_t x, int16_t y);       /* orig 0x020CE2 */
void wof_shape_blit(const wof_shape_t *s, int useMask, int16_t x, int16_t y); /* orig 0x020B0C */
void wof_draw_context(uint16_t layer, uint16_t owner);   /* what the display list records */
const wof_target_t *wof_draw_target(void);

/* ----------------------------------------------------------------------------- fonts */

/* The game's own font, newarmyfont (orig 0x012794, 0x01591E, 0x015956). */
int      wof_font_load(void);
uint16_t wof_font_height(void);
uint16_t wof_text_width(const char *s, uint16_t len);
uint16_t wof_text_render(const char *s, uint16_t len, uint8_t *buffer, int16_t x, int16_t row,
                         int16_t justify, int16_t buf_w, int16_t buf_h);
void     wof_text_draw(const char *s, uint16_t len, int16_t x, int16_t y, uint8_t pen);

/* topaz 8, taken from the owner's Kickstart ROM at build time (re/notes/system-font.md).
 * The dialogs of M3 draw with graphics.Text on this font because the game never sets one. */
void     wof_sysfont_draw(const char *s, uint16_t len, int16_t x, int16_t y, uint8_t pen);
uint16_t wof_sysfont_width(const char *s, uint16_t len);
int      wof_sysfont_present(void);

/* ------------------------------------------------------------------------ the assets */

/* The containers of re/notes/shapes.md, in the original's load order. */
enum {
    WOF_C_WORLD, WOF_C_HELLCAT, WOF_C_TORPEDO, WOF_C_JAPPLANE, WOF_C_EIGHTH,
    WOF_C_DASH, WOF_C_BATTLESHIP, WOF_C_DESTROYER, WOF_C_CRUISESHIP, WOF_C_JAPCARRIER,
    WOF_C_SELECTRANK, WOF_C_NIGHTDASH, WOF_C_COUNT
};

typedef struct {
    wof_container_t c[WOF_C_COUNT];
    int16_t        *table[WOF_C_COUNT];   /* the resolved pointer tables, 0 where there is none */
    int             loaded[WOF_C_COUNT];
    uint16_t        day_palette[WOF_PAL_COLOURS];    /* shapes/wingspalette */
    uint16_t        night_palette[WOF_PAL_COLOURS];  /* shapes/night.p */
    uint16_t        ocean_palette[WOF_PAL_COLOURS];  /* shapes/ocean.palette */
    uint16_t        night_ocean_palette[WOF_PAL_COLOURS]; /* shapes/nightocean.p */
    int             ok;
} wof_assets_t;

extern wof_assets_t wof_assets;

void wof_assets_init(void);          /* orig 0x0134BC init_assets, as far as M1 goes */

/* ------------------------------------------------------- the key buffer (keys.md) */

/* The five readers take their keys from here, unchanged from the original.  wof_key is
 * the half of input_handler that the port keeps; the mouse half writes rmb_down, which
 * nothing in the executable reads, so it is dropped. */
void     wof_keys_init(void);                       /* orig 0x0205CC, as far as it is kept */
int      wof_key_available(void);                   /* orig 0x0207D8, 0xFF or 0 */
uint32_t wof_key_get(void);                         /* orig 0x0207E4, (qualifier << 16) | code */
uint16_t wof_key_to_char(uint32_t key);             /* orig 0x020700, through the ROM's keymap */

/* --------------------------------------------------------- input sampling (input.md) */

void     wof_input_init(void);
int      wof_poll_fire(void);                       /* orig 0x02044C */
int      wof_poll_joy_dir8(void);                   /* orig 0x020454, 0 centre, 1 up ... 8 up-left */
uint16_t wof_read_joy_bits(void);                   /* orig 0x01520E, b0 forward b1 back b2 left b3 right */
void     wof_input_queue_clear(void);               /* orig 0x01174A */
uint16_t wof_input_queue_pop(void);                 /* orig 0x011714 */

/* The port's key layer and the vertical flip as a preference (src/portkeys.c). */
void     wof_invert_vertical_follow(void);          /* the flip command changed the byte */
void     wof_invert_vertical_restore(void);         /* M7: after a loaded game */

/* ---------------------------------------------------------------------- the M1 viewer */

void wof_viewer_init(void);
void wof_viewer_pass(void);
WOF_API(wof_key_press) void wof_key_press(uint8_t code);   /* goes when M3 replaces the viewer */

void wof_audio_init(void);

#endif /* WOF_H */
