/* Wings of Fury - core interface and shared declarations (SPEC.md section 6.1).
 *
 * C11, freestanding: no libc, no allocation after initialisation, no floating point in
 * game logic, no dependence on wall-clock time.  The same sources compile for
 * wasm32-freestanding (dist/core.wasm) and natively (tests/libwofcore.dylib).
 *
 * Milestone M0 contains no ported game logic.  Everything here is either the interface
 * the shell talks to or scaffolding that later milestones fill in.
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

/* Provisional.  The real geometry is open point 6 of SPEC section 10 (viewport sizes due
 * before M1): the original composes a 320 x 200 low-resolution playfield and a 640 x 37
 * high-resolution dashboard.  Until the viewport constructor at 0x01F7BE has been read,
 * the core reports the playfield alone, pixel-doubled to the 640-wide output of SPEC 6.4.
 * The shell asks for the size through wof_framebuffer_width/height and never assumes it,
 * so this changes without touching the shell. */
#define WOF_FB_W        640
#define WOF_FB_H        200

/* 32 colours is the low-resolution playfield's depth.  The dashboard has its own table;
 * the final number of palettes comes with the renderer (M1). */
#define WOF_PAL_COLOURS 32
#define WOF_PAL_COUNT   2

/* A palette entry is RGBA in memory order (0xAABBGGRR as a little-endian uint32), which is
 * what canvas ImageData expects, so the shell copies the table without converting it. */
#define WOF_RGBA(r, g, b) (0xFF000000u | ((uint32_t)(b) << 16) | ((uint32_t)(g) << 8) | (uint32_t)(r))

/* ------------------------------------------------------------------- display list 6.4 */

/* One entry per shape draw, for the enhanced renderer that SPEC 6.4 keeps the door open
 * for.  The classic renderer ignores it.  Nothing appends to it before M1. */
typedef struct {
    char     name[4];   /* the shape's 4-character name, SPEC 3.5 */
    int16_t  x, y;
    uint16_t layer;
    uint16_t flags;
    uint16_t owner;     /* object id, 0 when the draw belongs to no object */
} wof_draw_t;

/* --------------------------------------------------------------- exported interface */

WOF_API(wof_init)              void            wof_init(uint32_t seed, const uint8_t *fs, uint32_t fs_len);
WOF_API(wof_set_video_hz)      void            wof_set_video_hz(int hz);
WOF_API(wof_vblank)            void            wof_vblank(uint8_t raw);
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

/* ------------------------------------------------------------------------ core state */

/* Everything the core may change while running, in one struct, so that wof_state_save is a
 * copy and adding state cannot silently break the round trip.  The framebuffer is not in
 * here: wof_pass redraws it from this state.  Both targets are little-endian, so the saved
 * bytes are the struct's bytes; if a big-endian target ever appears this needs accessors. */
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
    uint16_t raw;           /* raw controller state of the most recent VBlank */
    uint16_t vblank_in_tick;/* 0..3, the count to 4 that vblank_server does */
    uint16_t noise;         /* newest entropy value, drawn by the test pattern */
} wof_state_t;

#define WOF_STATE_MAGIC   0x574F4653u  /* 'WOFS' */
#define WOF_STATE_VERSION 1u

extern wof_state_t wof_s;

/* ------------------------------------------------------------------ internal helpers */

void     wof_mem_set(void *dst, uint8_t value, uint32_t n);
void     wof_mem_copy(void *dst, const void *src, uint32_t n);
int      wof_mem_equal(const void *a, const void *b, uint32_t n);

uint16_t wof_entropy_next(void);            /* one value per rand_beam call, SPEC 7.3 */
void     wof_entropy_seed(uint32_t seed);

int      wof_fs_open(const uint8_t *blob, uint32_t len);
const uint8_t *wof_fs_find(const char *name, uint32_t *len);

void     wof_video_init(void);
void     wof_video_test_pattern(void);      /* M0 only, replaced by the renderer in M1 */

void     wof_audio_init(void);

#endif /* WOF_H */
