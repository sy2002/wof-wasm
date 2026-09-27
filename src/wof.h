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

/* One palette per distinct set of colours that is on screen at once, plus the blank one at
 * index 0.  wof_palette_rows() says which applies to each output row.  The front end needs
 * the most of them: the story scroller changes COLOR01 on every row of two sixteen-row
 * ramps, which is seventeen (re/notes/display.md).  The sky-to-ocean split and the ticker's
 * ten-line ramp of the play screen fit in the same budget. */
#define WOF_PAL_COUNT   24
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
WOF_API(wof_set_keyboard_assist) void          wof_set_keyboard_assist(int on);   /* the port's own, src/assist.c */
WOF_API(wof_keyboard_assist)   int             wof_keyboard_assist(void);
WOF_API(wof_set_fade_vblanks)  void            wof_set_fade_vblanks(int n);
WOF_API(wof_fade_vblanks)      int             wof_fade_vblanks(void);
WOF_API(wof_set_vblanks_per_pass) void         wof_set_vblanks_per_pass(int n);
WOF_API(wof_vblanks_per_pass)  int             wof_vblanks_per_pass(void);

/* Development entries, for looking at what a mission would otherwise be needed to reach.
 * They are not part of the game and not part of the port's key layer: the shell offers them
 * only while the diagnostics overlay is up (SPEC 6.2, and M3's deliverable 7). */
WOF_API(wof_dev_set_score)     void            wof_dev_set_score(uint32_t score);
WOF_API(wof_dev_open_dialog)   void            wof_dev_open_dialog(int mode);
WOF_API(wof_dev_player)        const int16_t  *wof_dev_player(void);   /* x, y, player_on_deck, weapon_type; read-only */

/* The pause as a request (M4): the shell asks for it when the page is hidden, and the next
 * pass of a mission pauses the game as Escape does.  Outside a mission it is dropped. */
WOF_API(wof_request_pause)     void            wof_request_pause(void);
WOF_API(wof_paused)            int             wof_paused(void);
WOF_API(wof_pass)              void            wof_pass(void);
WOF_API(wof_framebuffer)       const uint8_t  *wof_framebuffer(void);
WOF_API(wof_palette_rows)      const uint16_t *wof_palette_rows(void);
WOF_API(wof_palettes)          const uint32_t *wof_palettes(void);
WOF_API(wof_display_list)      const void     *wof_display_list(uint32_t *count);
WOF_API(wof_audio_render)      uint32_t        wof_audio_render(int16_t *stereo, uint32_t frames, uint32_t rate);
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

/* --------------------------------------------------------------------- viewports 6.4 */

/* The port's stand-in for one of the original's ViewPort records (re/notes/display.md).
 * The planar BitMap becomes one indexed surface; `bytes_per_row` is kept because the
 * picture decoder writes rows back to back at the picture's stride, not the viewport's. */
typedef struct {
    uint16_t width;          /* displayed pixels        (vport +0xA8) */
    uint16_t height;         /* rows of the bitmap      (vport +0xAA, BitMap Rows) */
    uint16_t bytes_per_row;  /* BitMap BytesPerRow      (vport +4) */
    uint16_t rows;           /* BitMap Rows             (vport +6) */
    uint16_t disp_rows;      /* rows the copper shows   (vport +0xA2); 230 for the scroller */
    uint16_t out_y;          /* first display line      (vport +0xA6) */
    uint16_t scroll;         /* rows the plane pointer has advanced (story_screen) */
    uint16_t ring_at;        /* viewport row where the plane pointer is reloaded, else NONE */
    uint16_t ramp;           /* the story scroller's ramp count, 0 when there is none */
    uint16_t split_line;     /* vport +0x92 */
    uint16_t split_on;       /* vport +0x94 */
    uint32_t plane;          /* offset of the surface inside wof_f.vram */
    uint8_t  depth;          /* BitMap Depth            (vport +9) */
    uint8_t  hires;          /* 0 = low resolution, doubled on the 640-wide output */
    uint8_t  next;           /* index of the next viewport in the chain, or WOF_VP_NONE */
    uint8_t  has_colours2;   /* the viewport has a second colour table (vport +0x9C) */

    /* The RastPort the original embeds at vport +0x2C.  Only the five fields the front end
     * sets and reads are kept: the two pens, the draw mode and the pen position. */
    uint8_t  apen;           /* RastPort FgPen  (+0x19), SetAPen */
    uint8_t  bpen;           /* RastPort BgPen  (+0x1A), SetBPen */
    uint8_t  drmd;           /* RastPort DrawMode (+0x1C): JAM1 0, JAM2 1, COMPLEMENT 2 */
    int16_t  cp_x;           /* RastPort cp_x (+0x24), Move and Text */
    int16_t  cp_y;           /* RastPort cp_y (+0x26) */
    uint16_t colours[WOF_PAL_COLOURS];    /* colour table 1 (vport +0x98) */
    uint16_t colours2[WOF_PAL_COLOURS];   /* colour table 2 (vport +0x9C) */
} wof_vport_t;

/* The surface of a viewport, and the row its drawing starts at once the plane pointer has
 * advanced.  Both are computed rather than stored, so that no pointer lives in the state. */
uint8_t     *wof_vport_pixels(const wof_vport_t *v);
wof_vport_t *wof_vport_make(uint16_t width, uint16_t height, uint8_t depth, uint8_t hires);
void         wof_vport_clear_planes(wof_vport_t *v);     /* orig 0x01A74C */

/* --------------------------------------------------------------- the display memory */

/* The port's bitplanes.  The original keeps two views of 0xACD0 bytes each plus the
 * single-buffered ticker plane, all in chip memory (re/notes/display.md); the port keeps
 * one indexed byte per pixel instead, so the same picture needs eight times the bytes of
 * one plane and a fraction of the bytes of five.
 *
 * A view has to hold the tallest thing any screen asks of it.  That is the story scroller:
 * its bitmap is 640 x 200, but story_screen advances the plane by one row per step, 210
 * times, and the copper shows 230 rows from wherever the plane then starts, so the display
 * reads up to row 258 of the view's memory and the text is drawn down to row 209 of it.
 * Rows beyond the bitmap are the cleared rest of the view's block on the machine, and they
 * are black here for the same reason. */
#define WOF_VIEW_W       640
#define WOF_VIEW_ROWS    260
#define WOF_VIEW_BYTES   (WOF_VIEW_W * WOF_VIEW_ROWS)
#define WOF_TICKER_BYTES (84 * 8 * WOF_TICKER_H)     /* the bitmap is 84 bytes wide, 640 shown */
#define WOF_VRAM_BYTES   (2 * WOF_VIEW_BYTES + WOF_TICKER_BYTES)

/* The five viewport records the original keeps in BSS (re/notes/display.md), and room for
 * what the M1 viewer still makes for itself until the front end replaces it. */
#define WOF_VP_A1     0
#define WOF_VP_B1     1
#define WOF_VP_A2     2
#define WOF_VP_B2     3
#define WOF_VP_TICKER 4
#define WOF_VP_FIXED  5
#define WOF_VP_MAX    11
#define WOF_VP_NONE   0xFF

#define WOF_VIEW_A 0
#define WOF_VIEW_B 1

/* --------------------------------------------------------------- the front end (6.3) */

/* What the front end keeps between one wof_pass and the next: the resume points of the
 * coroutines, every local that lives across a wait (SPEC 6.3), the viewport records and the
 * display memory itself.  All of it is inside the core's state, so wof_state_save is a copy
 * and a loaded state brings the picture back with the logic.  Nothing here is a pointer:
 * a viewport names its surface by an offset into `vram` and its neighbour by an index. */
/* A coroutine's resume point.  One per routine that can wait; no routine of the front end
 * is ever inside itself, so a context per routine is enough and no stack is needed. */
typedef struct { uint16_t line; } wof_ctx_t;

typedef struct {
    uint16_t editing;    /* text_input has the line: every key passes as it came */
    uint16_t briefing;   /* mission_briefing is on screen: KeyR restarts from there too */

    uint8_t  front_view; /* which of the two views is installed (view_show) */
    uint8_t  back_view;
    uint8_t  view_first[2];   /* index of each view's first viewport, or WOF_VP_NONE */
    uint32_t view_base[2];    /* offset of each view's display memory inside vram */
    uint32_t ticker_base;
    uint32_t vram_used;       /* the bump pointer display_init leaves behind */

    /* The resume points, by the routine that owns each one. */
    wof_ctx_t co_main;        /* main's outer loop (orig 0x010066) */
    wof_ctx_t co_stage;       /* title_sequence, rank_select, mission_briefing, high scores */
    wof_ctx_t co_inner;       /* story_screen, load_save_dialog, high_score_entry */
    wof_ctx_t co_screen;      /* the five screen_ routines */
    wof_ctx_t co_show;        /* view_show_wait and cop_show_wait */
    wof_ctx_t co_vblank;      /* wait_vblank */
    wof_ctx_t co_fade;        /* the four fades */
    wof_ctx_t co_frames;      /* wait_frames_or_fire */
    wof_ctx_t co_menu;        /* menu_input */
    wof_ctx_t co_release;     /* wait_input_release */
    wof_ctx_t co_text;        /* text_input */
    wof_ctx_t co_setup;       /* mission_display_setup */
    wof_ctx_t co_mission;     /* the mission: main's setup after the briefing, the inner loop */
    wof_ctx_t co_pass;        /* frame_update */
    wof_ctx_t co_ticks;       /* run_queued_ticks */
    wof_ctx_t co_tick;        /* logic_tick (orig 0x011386) */
    wof_ctx_t co_player;      /* the player update (orig 0x01C660) */
    wof_ctx_t co_lost;        /* the wait after a crash (orig 0x01AF7C) */
    wof_ctx_t co_restart;     /* the next aircraft (orig 0x0135CE) */
    wof_ctx_t co_lost_restart; /* player_lost_restart (orig 0x0135D8) */
    wof_ctx_t co_keys;        /* ingame_keys (orig 0x01CCF6) */
    wof_ctx_t co_music;       /* music_start and music_stop: the wait for the fade */

    /* Locals that live across a wait.  The original keeps them on its stack; a stackless
     * coroutine cannot, so they carry the name they have in the routine that owns them. */
    uint16_t fade_step;       /* fade_to: 0..15 */
    uint16_t fade_count;      /* 1 << depth of the front view's first viewport */
    uint16_t fade_pair;       /* fade_to_pair rather than fade_to */
    uint16_t fade_start1[WOF_PAL_COLOURS];   /* the tables the fade starts from */
    uint16_t fade_start2[WOF_PAL_COLOURS];
    uint16_t fade_start3[WOF_PAL_COLOURS];
    uint16_t fade_target1[WOF_PAL_COLOURS];  /* and the ones it is going to */
    uint16_t fade_target2[WOF_PAL_COLOURS];

    uint16_t frames_i;        /* wait_frames_or_fire: the round it is on */
    uint16_t frames_n;        /* and how many it was asked for */
    uint16_t frames_fire;     /* what it returns */

    uint16_t fade_wait;       /* the VBlanks a fade step still owes */

    uint16_t menu_rounds;     /* menu_input */
    uint16_t menu_timeout;
    int16_t  menu_result;
    uint16_t release_i;       /* wait_input_release */

    uint8_t  show_view;       /* which view view_show_wait was given */

    /* title_sequence (orig 0x018022) and its three pictures */
    uint16_t title_pal[WOF_PAL_COLOURS];

    /* story_screen (orig 0x017E80).  d4, d5 and d6 of the original live here. */
    uint16_t story_step;      /* -8(a5): the step, which decides when a line is drawn */
    uint16_t story_at;        /* -4(a5): where the next line starts in the text block */
    uint16_t story_lines;     /* -6(a5): how many have been drawn */
    int16_t  story_wrap;      /* d5: rows left before the plane pointer restarts */
    int16_t  story_last;      /* d4: rounds left since the last line was drawn */
    uint16_t story_ramp;      /* -0x10(a5): the wind-down's ramp count */

    /* rank_select (orig 0x018262) */
    uint16_t rank_pal[WOF_PAL_COLOURS];
    uint16_t rank_prev;       /* -0x46(a5): the cursor the highlight is drawn at */
    int16_t  rank_shape;      /* -0x4c(a5): the highlight's shape, as an index */

    /* mission_briefing (orig 0x018590) */
    uint16_t briefing_pal[WOF_PAL_COLOURS];
    uint16_t briefing_i;      /* -0x80(a5): the round it is on, of 240 */
    uint16_t briefing_result; /* 1 when Control-R sent it back to the outer loop */

    /* load_save_dialog (orig 0x018B96) and high_score_screen (orig 0x019856) */
    uint16_t dialog_mode;     /* 0 load, 1 save */
    uint16_t dialog_result;   /* 0 when a game was loaded or saved */
    int16_t  dialog_cursor;   /* 0..5 the slots, 6 and 7 the two buttons */
    int16_t  dialog_prev;     /* where the highlight is drawn */
    int16_t  dialog_move;     /* what menu_input or the editor last returned */
    uint16_t dialog_i;
    uint16_t dialog_count;    /* how many names the list found */
    uint16_t dialog_pal[WOF_PAL_COLOURS];
    char     dialog_names[6][29];    /* orig 0x027C7E, the slot names */
    char     dialog_copy[6][29];     /* orig 0x027D2C, the copy it keeps beside them */
    char     dialog_path[40];        /* the name it opens, with `wof.` in front */

    /* text_input (orig 0x016086), the line editor of both */
    uint16_t text_max;        /* the longest line it will take */
    int16_t  text_x, text_y;
    int16_t  text_cursor;     /* -0x52(a5) */
    int16_t  text_prev;       /* -0x54(a5), the column the caret is drawn at */
    int16_t  text_result;     /* -0x64(a5): 0 accepted, -1 upward, 1 downward */
    uint16_t text_redraw;     /* -0x5a(a5) */
    uint16_t text_which;      /* which buffer the editor has: a slot, or the name entry */
    char     text_pad[0x51];  /* -0x50(a5), the spaces it blanks the rest of the line with */

    /* high_score_screen (orig 0x019856) and what it draws */
    uint8_t  hiscore[360];    /* the table, a local of high_score_screen (0x027DDA) */
    char     entry_name[18];  /* -0x51(a5) of high_score_entry, at most 16 characters */
    uint16_t hiscore_pal[WOF_PAL_COLOURS];
    uint16_t slab_pal[WOF_PAL_COLOURS];
    uint16_t hs_pass;
    uint16_t hs_row;

    uint8_t  keys_char;       /* ingame_keys: the character of the key it is on */
    uint8_t  pause_request;   /* wof_request_pause: the next ingame_keys pauses */
    uint16_t mission_count;   /* how often a mission has been reached (step S) */
    uint16_t mission_end;     /* how the inner loop was left: 1 quit_flag, 2 end_of_mission */
    uint32_t ticks_run;       /* logic ticks run, the stand-in's and main's own */
    uint32_t passes_run;      /* passes of the inner loop */
    uint8_t  draw_vport;      /* the viewport draw_set_target was last given, or WOF_VP_NONE */

    /* The mirror markers of hellcat.shp and Torpedo.shp (+8 of each record): game state,
     * because the game mirrors the pixel data in place when the facing changes
     * (re/notes/shapes.md, SPEC 7.2).  The containers' own copies follow these on a load. */
    uint8_t  marker_hellcat[128];
    uint8_t  marker_torpedo[128];

    /* What the original keeps as pointers that are not game data: which dashboard container
     * dash_shapes names (night_flag when load_dash_assets ran), which of the eight sounds are
     * loaded, and which ship containers are (by ship record index). */
    uint8_t  dash_night;
    uint8_t  dash_picture_night;  /* night + 1 of the picture load_dash_assets kept, or 0 */
    uint8_t  sound_loaded;
    uint8_t  ship_loaded;

    /* The play screen's copper lists, as far as anything can see them (re/notes/display.md):
     * whether a view's list carries the ticker ramp, and the COLOR01 flip_buffers poked into
     * it.  `blank` is the black list cop_show_wait installs between screens. */
    uint8_t  play_screen;
    uint8_t  blank;
    uint8_t  ticker_ramp[2];
    uint8_t  colour1_poked[2];
    uint16_t colour1[2];
    uint16_t dev_dialog;      /* a development request: 1 the load dialog, 2 the save one */

    /* music_start and music_stop (src/music.c): the VBlanks left of a round of their wait
     * for the fade, and the song music_start was asked for across it. */
    uint16_t music_spin;
    uint16_t music_song;

    wof_vport_t vport[WOF_VP_MAX];
    uint8_t     vram[WOF_VRAM_BYTES];
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

/* ------------------------------------------------------------- the original's records */

/* The record layouts of src/records.def become C structs with the original's field order;
 * the offsets and widths travel beside them for the tests (SPEC 7.2).  The kinds say how a
 * field travels between the original's bytes and the port's struct. */
#define WOF_K_PLAIN 0
#define WOF_K_SHAPE 1
#define WOF_K_MAP   2
#define WOF_K_POOL  3
#define WOF_K_SOUND 4
#define WOF_K_SONG  5
#define WOF_K_VECTOR 6

#define WOF_RECORD(r, size)                   typedef struct {
#define WOF_FIELD(r, n, t, off, k)            t n;
#define WOF_FIELD_ARRAY(r, n, t, c, off, k)   t n[c];
#define WOF_RECORD_END(r)                     } wof_##r##_t;
#include "records.def"
#undef WOF_RECORD
#undef WOF_FIELD
#undef WOF_FIELD_ARRAY
#undef WOF_RECORD_END

/* The tables of src/mission.def: those at a fixed address in DATA and those the original
 * allocates, both kept at a fixed place in the core's state (re/notes/porting-m4.md, "Where
 * mission memory lives").  Nothing here is a pointer. */
typedef struct {
#define WOF_TABLE(n, r, c, a)  wof_##r##_t n[c];
#define WOF_POOL(n, r, c, p)   wof_##r##_t n[c];
#include "mission.def"
#undef WOF_TABLE
#undef WOF_POOL
} wof_mission_t;

/* ------------------------------------------------------------- Paula's audio side (M8) */

/* A sample pointer as the port keeps it (records.def, WOF_K_SOUND): the sound file's index
 * in sound_files plus one in the top byte, the offset into the file below it; 0 for none.
 * The samples are the files as the disk has them, signed 8-bit PCM, read from the file
 * system blob where they lie. */
#define WOF_SOUND(file, offset) ((((uint32_t)(file) + 1u) << 24) | ((uint32_t)(offset) & 0xFFFFFFu))
#define WOF_SOUND_FILE(h)       ((int)((h) >> 24) - 1)
#define WOF_SOUND_OFFSET(h)     ((h) & 0xFFFFFFu)

/* One audio channel of the model (SPEC 6.5, re/notes/sound.md): the registers as the game
 * wrote them and where the channel is in its cycle.  Time is counted in units of
 * 1 / (clock x hz) seconds, so that a VBlank is `clock` units and a sample at period P is
 * P x hz units, both whole numbers; tools/headless_paula.py keeps the same. */
typedef struct {
    uint64_t next;       /* the instant the next byte of the cycle begins */
    uint32_t lc;         /* AUDxLC, a sound handle */
    uint32_t ptr;        /* the next byte of the cycle to begin, a sound handle */
    uint32_t left;       /* bytes of the cycle not begun yet */
    uint16_t len;        /* AUDxLEN in words, 0 for 65,536 */
    uint16_t per;        /* AUDxPER */
    uint16_t vol;        /* AUDxVOL */
    uint16_t on;         /* the channel's bit in DMACON */
} wof_paula_channel_t;

typedef struct {
    wof_paula_channel_t ch[4];
    uint32_t vblanks;    /* VBlanks the model has seen: the instant T_k is vblanks x clock */
    uint32_t irqs;       /* calls of the level-4 handler */
    uint32_t late;       /* requests the main program made deliverable (none is expected) */
    uint16_t intena;     /* INTENA as INTENAR reads it */
    uint16_t intreq;     /* INTREQ as INTREQR reads it */
    uint16_t hz;         /* the video rate the units were taken at */
    uint16_t pad;
} wof_paula_t;

/* The rest of the hardware the music player takes (M8 part 2, re/notes/music.md): CIA-A's
 * timer A, whose underflow ciaa.resource hands to the vector AddICRVector installed, and
 * the level-4 autovector at 0x70, which the player takes over while it is loaded.  Timer A
 * counts at the E clock, a tick of 5 x hz units of the Paula model; tools/headless_paula.py
 * keeps the same (re/notes/headless.md, "The music's timer"). */
#define WOF_L4_SYSTEM    0   /* the operating system's: it clears what it is given */
#define WOF_L4_AUDIO_IRQ 1   /* audio_irq, 0x01EBAA, which sound_init puts there */
#define WOF_L4_SONGINT   2   /* the player's SongIntHandler, songplay+0x0848 */

typedef struct {
    uint64_t next;       /* the instant of the next underflow while the timer runs */
    uint32_t calls;      /* calls of the ICR vector */
    uint16_t latch;      /* timer A's latch, TALO and TAHI */
    uint16_t counter;    /* its counter as last loaded */
    uint16_t running;    /* CRA bit 0 */
    uint16_t oneshot;    /* CRA bit 3 */
    uint16_t vector;     /* the ICR vector of timer A: 1 the player's SongInt, 0 none */
    uint16_t level4;     /* the handler at 0x70, WOF_L4_* */
} wof_cia_t;

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
    uint16_t video_hz;      /* 60 or 50 */
    uint16_t raw;           /* the most recent VBlank's controller state, opposing
                             * directions cancelled: the port's JOY1DAT and CIA-A PRA */
    uint16_t invert_pref;   /* the shell's remembered vertical flip, 0 or 1 */
    uint16_t invert_given;  /* whether the shell ever handed one over (SPEC 6.1) */
    uint32_t standin_hits;  /* marked stand-ins reached, wof_standin_hits (M4) */
    uint32_t since_pass;    /* VBlanks since the previous pass began, wof_vblanks_per_pass */
    uint16_t assist;        /* the keyboard assist is on (src/assist.c), 0 or 1 */
    uint16_t assist_prev;   /* the directions of the previous VBlank, for the edges */
    uint16_t assist_armed;  /* directions pressed since the previous sample, not yet sampled */
    uint16_t assist_push;   /* the direction of the weapon menu's running push, 0 for none */
    uint16_t assist_left;   /* the VBlanks that push still covers */
    uint16_t assist_queued; /* presses remembered while it runs, at most two */
    uint16_t assist_queue[2];
    wof_paula_t   paula;    /* Paula's audio side, src/audio.c (M8) */
    wof_cia_t     cia;      /* timer A and the level-4 vector, src/audio.c (M8 part 2) */
    wof_globals_t g;        /* the original's own globals, src/globals.def */
    wof_mission_t m;        /* the original's tables, src/mission.def */
    wof_front_t   f;        /* the front end: coroutines, screens, dialogs (SPEC 6.3) */
} wof_state_t;

#define WOF_STATE_MAGIC   0x574F4653u  /* 'WOFS' */
#define WOF_STATE_VERSION 11u

extern wof_state_t wof_s;

/* The ported globals read as themselves: wof_g.key_count is the original's key_count. */
#define wof_g (wof_s.g)
#define wof_f (wof_s.f)
#define wof_m (wof_s.m)

/* The registered globals start as the original's DATA hunk starts them: the initialised
 * part of the hunk comes out of the executable at build time (re/tables.toml, data_image)
 * and every entry of src/globals.def and src/mission.def that has an address inside it is
 * loaded from there, with the byte order converted.  wof_init calls it after zeroing. */
void wof_globals_from_image(void);
int  wof_global_byte(uint32_t orig_address, uint8_t *out);   /* a registered global's byte */
int  wof_original_store8(uint32_t orig_address, uint8_t value);     /* a byte to a registered
                                                                       global or fixed table */
void wof_original_store16(uint32_t orig_address, uint16_t value);   /* a word, big-endian */

/* ------------------------------------------------------------- the marked stand-ins (M4)
 *
 * Code the five mission scripts never executed is not ported yet; each such region is one
 * stand-in with a marker naming the milestone that owes it.  Reaching one counts in the
 * state (wof_standin_hits, which the diagnostics overlay shows), and in test builds it is
 * also logged by name, so that every differential test can assert that none was reached.
 * In the release build a stand-in skips and does nothing else. */
void wof_standin(const char *marker);
#define WOF_STANDIN(marker) wof_standin(marker)
WOF_API(wof_standin_hits)      uint32_t        wof_standin_hits(void);

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
uint32_t wof_rand_beam(uint32_t caller);    /* orig 0x0203BE; caller: the original routine */
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

/* The write side (SPEC 6.2, Storage): an overlay in front of the read-only disk, which the
 * shell copies into localStorage under the wof: prefix.  It is not part of the core's
 * state: a save state is a snapshot of the running game and must not un-write a file. */
void        wof_fs_writes_reset(void);
int         wof_fs_write(const char *name, const uint8_t *data, uint32_t len);
int         wof_fs_delete(const char *name);          /* orig dos.DeleteFile */
const uint8_t *wof_fs_written_data(uint32_t index, uint32_t *len);
const char *wof_fs_dir_entry(uint32_t index);         /* the `wof.` files in ExNext order */

/* What the shell stores and hands back (SPEC 6.2, Storage).  It watches wof_fs_changes and
 * writes the files out when it moves; at start it puts back what it stored, in the order it
 * stored them, because that order is what the dialog's list is made of. */
WOF_API(wof_fs_changes)        uint32_t wof_fs_changes(void);
WOF_API(wof_fs_written_count)  uint32_t wof_fs_written_count(void);
WOF_API(wof_fs_written_name)   const char *wof_fs_written_name(uint32_t index);
WOF_API(wof_fs_written_size)   uint32_t wof_fs_written_size(uint32_t index);
WOF_API(wof_fs_written_bytes)  const uint8_t *wof_fs_written_bytes(uint32_t index);
WOF_API(wof_fs_put)            int wof_fs_put(const char *name, const uint8_t *data, uint32_t len);

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

/* A shape as game state names it: the container's slot and the shape's index in it, so
 * that a pointer the original keeps in a record or a table survives a save state
 * (SPEC 7.2).  0 is the original's null pointer. */
#define WOF_SHAPE_NONE ((uint16_t)0)
uint16_t           wof_shape_handle(int slot, int16_t index);
const wof_shape_t *wof_shape_of(uint16_t handle);
uint16_t           wof_shape_handle_of(const wof_shape_t *s);  /* by where it lies, 0 if none */
uint16_t           wof_table_handle(int slot, uint16_t entry);  /* entry of a resolved table */

int16_t  wof_shape_find(const wof_container_t *c, uint32_t name);   /* orig 0x020560 */
int16_t  wof_shape_by_index(const wof_container_t *c, uint16_t i);  /* orig 0x02050E */
int16_t *wof_shapes_resolve(const wof_container_t *c, const uint32_t *list, uint16_t count);
int      wof_shapes_load(wof_container_t *c, const char *file, const uint32_t *list);
void     wof_shape_mirror_x(wof_shape_t *s);                        /* orig 0x015B58 */
void     wof_shape_set_facing(wof_shape_t *s, int16_t facing);      /* the +8 marker rule */
uint16_t wof_namelist_count(const uint32_t *list);

/* A screen is the stack of viewports that is on the output at one moment.  Every band
 * names its source viewport, where it starts on the output and which palette its rows go
 * through, which is how SPEC 6.4's per-row palette interface is fed. */
/* One band per run of output rows that share a palette and a source row.  The story
 * scroller is the worst case: two sixteen-row ramps, the run between them, the run below
 * them, and the ring's reload splits one of those in two. */
#define WOF_MAX_BANDS 48

typedef struct {
    uint16_t out_y;
    uint16_t rows;
    int32_t  src_row;        /* may lie past the bitmap: the scroller's ring does */
    uint32_t plane;          /* the source viewport's surface, as an offset into vram */
    uint16_t stride;
    uint16_t width;
    uint8_t  hires;
    uint16_t colours[WOF_PAL_COLOURS];
} wof_band_t;

void wof_screen_reset(void);
void wof_screen_band(const wof_vport_t *vp, uint16_t out_y, uint16_t rows, int32_t src_row,
                     const uint16_t *colours);   /* 0: the viewport's own colour table 1 */
void wof_screen_present(void);           /* bands and colour tables -> framebuffer, palettes */

/* The row where a viewport's plane pointer is not reloaded at all (story_copper_build). */
#define WOF_VP_RING_NONE 0xFFFFu

void wof_vport_init_bitmap(wof_vport_t *v, uint32_t *mem, uint16_t width, uint16_t height,
                           uint8_t depth);   /* orig 0x0167F2 */

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
void wof_rect_fill(int16_t x0, int16_t y0, int16_t x1, int16_t y1, uint8_t colour); /* orig 0x021010 */
void wof_line_draw(int16_t x0, int16_t y0, int16_t x1, int16_t y1, uint8_t colour); /* orig 0x021318 */
void wof_draw_restore(void);                             /* the target again after a state load */
void wof_draw_context(uint16_t layer, uint16_t owner);   /* what the display list records */
const wof_target_t *wof_draw_target(void);
wof_vport_t        *wof_draw_target_vport(void);

/* ----------------------------------------------------------------------------- fonts */

/* The game's own font, newarmyfont (orig 0x012794, 0x01591E, 0x015956). */
int      wof_font_load(void);
uint16_t wof_font_height(void);
uint16_t wof_text_width(const char *s, uint16_t len);
uint8_t  wof_font_first(void);
uint8_t  wof_font_width_byte(uint8_t index);
uint16_t wof_font_glyph_word(uint8_t index, uint32_t byte_offset);
uint8_t  wof_ticker_char(uint32_t orig_address);     /* a byte of a ticker message */
void     wof_vblank_ticker(void);                    /* orig 0x011842, vblank_server's mission half */
uint16_t wof_text_render(const char *s, uint16_t len, uint8_t *buffer, int16_t x, int16_t row,
                         int16_t justify, int16_t buf_w, int16_t buf_h);
void     wof_text_draw(const char *s, uint16_t len, int16_t x, int16_t y, uint8_t pen);

/* topaz 8, taken from the owner's Kickstart ROM at build time (re/notes/system-font.md).
 * The dialogs of M3 draw with graphics.Text on this font because the game never sets one. */
void     wof_sysfont_draw(const char *s, uint16_t len, int16_t x, int16_t y, uint8_t pen);
uint16_t wof_sysfont_width(const char *s, uint16_t len);
int      wof_sysfont_present(void);
uint16_t wof_sysfont_baseline(void);

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
void wof_assets_follow_state(void);  /* mirror what the state's markers say is mirrored */

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

/* The keyboard assist, the port's own policy in front of the sample (src/assist.c).  While
 * the sample is taken the raw word may carry WOF_RAW_UNFLIPPED, which the shell can never
 * send (wof_vblank keeps five bits): its vertical bits are a push of the weapon menu, which
 * read_joy_bits does not flip. */
#define WOF_RAW_UNFLIPPED 0x20u
void     wof_assist_vblank(void);                   /* every VBlank that is not paused */
uint16_t wof_assist_sample(uint16_t physical);      /* what the sample sees */
int      wof_assist_swallows(uint8_t code);         /* a cursor key the weapon menu must not see */

/* ------------------------------ the arithmetic game logic computes with (7.1, point 13) */

#include "ffp.h"

/* ------------------------------------------- views, screens and the picture (6.4, 6.3) */

#include "coro.h"

void         wof_display_init(void);                  /* orig 0x016670, as far as M3 needs */
wof_vport_t *wof_front_vport(void);
wof_vport_t *wof_back_vport(void);
void         wof_view_layout(uint8_t view);           /* orig 0x01692C */
void         wof_view_copy(uint8_t from, uint8_t to); /* orig 0x01A9CA */
void         wof_view_show(uint8_t view);             /* orig 0x016F20 */
wof_co_t     wof_wait_vblank(void);                   /* orig 0x01AA3E */
wof_co_t     wof_wait_next_vblank(void);              /* orig 0x01AA32 */
wof_co_t     wof_view_show_wait(uint8_t view);        /* orig 0x016FC4 */
wof_co_t     wof_cop_show_blank(void);                /* orig 0x01A9FC with cop_blank */
wof_co_t     wof_screen_picture(void);                /* orig 0x016AD8 */
wof_co_t     wof_screen_story(void);                  /* orig 0x016A60 */
wof_co_t     wof_screen_hires3(void);                 /* orig 0x016B04 */
wof_co_t     wof_screen_dialog(void);                 /* orig 0x0169A4 */
wof_co_t     wof_screen_hiscore(void);                /* orig 0x016D7A */
void         wof_screen_from_front_view(void);
void         wof_screen_game(void);                   /* orig 0x016CC6 */
void         wof_screen_game_restore(void);           /* orig 0x016D32 */
void         wof_cop_set_split_line(int16_t row);     /* orig 0x01876E */
void         wof_cop_add_ticker_ramp(uint8_t view);   /* orig 0x0187BA */
void         wof_cop_poke_colour1(uint8_t view, uint16_t colour);
uint16_t     wof_ticker_ramp(uint16_t row);           /* ticker_ramp[row], from the executable */

/* --------------------------------------------- graphics.library on indexed pixels 6.4 */

/* The dialogs, the name entry, the high-score list and the story scroller draw with
 * graphics.library on the viewport's own RastPort and never open a font, so the text is
 * topaz 8 from the ROM (re/notes/system-font.md).  These are the seven calls they make
 * (re/notes/drawing.md); everything else goes through the blitter library of M1.
 *
 * None of them clips.  There is no Layer on these RastPorts, so on the machine a Move to a
 * negative row and a RectFill from it write before the plane, and the story scroller relies
 * on exactly that: its plane pointer has walked up the view's memory and the text is drawn
 * fourteen rows before it (re/notes/frontend.md).  The port bounds a write by the view's
 * memory block, which is where the original's own arithmetic keeps it. */
#define WOF_JAM1       0
#define WOF_JAM2       1
#define WOF_COMPLEMENT 2

void wof_gfx_set_apen(wof_vport_t *v, uint8_t pen);
void wof_gfx_set_bpen(wof_vport_t *v, uint8_t pen);
void wof_gfx_set_drmd(wof_vport_t *v, uint8_t mode);
void wof_gfx_move(wof_vport_t *v, int16_t x, int16_t y);
void wof_gfx_draw(wof_vport_t *v, int16_t x, int16_t y);
void wof_gfx_rect_fill(wof_vport_t *v, int16_t x0, int16_t y0, int16_t x1, int16_t y1);
void wof_gfx_text(wof_vport_t *v, const char *s, uint16_t len);

/* orig 0x015910 text_draw and 0x015A8C text_draw_justified: the game font through
 * MaskBuffer and BltTemplate, at the RastPort's pen position and in its pens and mode. */
void wof_text_draw_line(wof_vport_t *v, const char *s, uint16_t len);
void wof_text_draw_justified(wof_vport_t *v, const char *s, uint16_t len, int16_t width);

/* orig 0x020E24 shape_draw_xor - the exclusive-or blit the rank selection highlights with. */
void wof_shape_draw_xor(const wof_shape_t *s, int16_t x, int16_t y);

/* ----------------------------------------------- the waits and the fades (6.3, fade.c) */

wof_co_t wof_wait_frames_or_fire(uint16_t n);         /* orig 0x016EEE */
int      wof_frames_fire(void);                       /* what it returned */
wof_co_t wof_menu_input(uint16_t timeout);            /* orig 0x018194 */
int      wof_menu_result(void);
wof_co_t wof_wait_input_release(void);                /* orig 0x018228 */
wof_co_t wof_fade(const uint16_t *target1, const uint16_t *target2, int pair);
wof_co_t wof_fade_to(const uint16_t *target);         /* orig 0x017084 */
wof_co_t wof_fade_out(void);                          /* orig 0x0173B0 */
wof_co_t wof_fade_to_pair(const uint16_t *a, const uint16_t *b);  /* orig 0x0171F2 */
wof_co_t wof_fade_out_pair(void);                     /* orig 0x0173E6 */

/* ------------------------------------------------------ what the port did (SPEC 8) */

/* One recorded call: which routine, four numbers whose meaning the routine gives, and a
 * string - the text that was drawn, the file that was opened, the shape's four-character
 * name.  Compiled into the native test library only (src/trace.c). */
#define WOF_TRACE_MAX  4096
#define WOF_TRACE_TEXT 64   /* the story scroller's lines are 48 characters */

typedef struct {
    uint32_t vblank;
    int32_t  a, b, c, d;
    char     what[16];
    char     text[WOF_TRACE_TEXT];
} wof_trace_t;

#ifdef WOF_TRACE
void               wof_trace_add(const char *what, int32_t a, int32_t b, int32_t c,
                                 int32_t d, const char *text, uint16_t len);
void               wof_trace_reset(void);
uint32_t           wof_trace_count(void);
uint32_t           wof_trace_dropped(void);
const wof_trace_t *wof_trace_at(uint32_t i);

/* The ported globals as they stood at one moment.  The front end takes one where it ends,
 * which is the moment the harness's dump calls step S, because the outer loop runs on into
 * the next rank selection in the same pass while the M3 mission is a stand-in. */
void                   wof_trace_globals(void);
const wof_globals_t   *wof_trace_globals_at(void);

/* The stand-ins reached, by marker, for the tests to assert on (src/trace.c). */
void                   wof_trace_standin(const char *marker);
uint32_t               wof_trace_standins(void);
const char            *wof_trace_standin_at(uint32_t i, uint32_t *count);
void                   wof_trace_standins_reset(void);
#else
#define wof_trace_add(what, a, b, c, d, text, len) ((void)0)
#define wof_trace_globals() ((void)0)
#define wof_trace_standin(marker) ((void)(marker))
#endif

/* ------------------------------------------------------------------- the front end */

wof_co_t wof_front(void);                 /* orig 0x010006 main, the outer loop at 0x010066 */
void     wof_front_init(void);
uint16_t wof_number(char *dst, int32_t value);               /* the sprintf("%d") in use */
void     wof_view_set_picture(uint8_t view);                 /* orig 0x016A98 */
wof_co_t wof_load_save_dialog(uint16_t mode);                /* orig 0x018B96 */
wof_co_t wof_high_score_screen(void);                        /* orig 0x019856 */
void     wof_load_picture_black(const char *name, uint16_t *palette_out);  /* orig 0x017422 */
void     wof_load_picture_black_into(uint8_t vport, const char *name, uint16_t *palette_out);
uint16_t wof_format(char *dst, const char *format, int32_t number, const char *text);
uint16_t wof_raw_do_fmt(char *dst, const char *format, const uint16_t *data);   /* exec RawDoFmt */

/* The line editor of the name entry and the file names (orig 0x016086, re/notes/keys.md).
 * `buffer` is the line it edits; it returns 0 when the line was accepted, -1 when the
 * player left it upward and 1 downward. */
wof_co_t wof_text_input(char *buffer, uint16_t max, int16_t x, int16_t y);
int      wof_text_result(void);
void     wof_path_sanitise(char *name);                      /* orig 0x016592 */

/* The high-score file (re/notes/highscore.md).  The table is 360 bytes, ten entries of a
 * u32 score, a u16 rank and a 30-byte NUL-padded name, best first, all big-endian. */
#define WOF_HS_ENTRIES 10
#define WOF_HS_STRIDE  36
void     wof_high_score_load(void);                          /* orig 0x0193CC */
void     wof_high_score_sort(void);                          /* orig 0x019320 */
void     wof_high_score_save(void);                          /* orig 0x019288 */
uint32_t wof_high_score_of(uint16_t i);
wof_co_t wof_high_score_entry(void);                         /* orig 0x019472 */
void     wof_high_score_draw(void);                          /* orig 0x01967E */

void wof_audio_init(void);

/* Paula (src/audio.c).  The engine writes the registers through these, as the original
 * writes 0xDFF096 and on; wof_paula_boundary runs at every VBlank before the servers and
 * delivers the channel events of the VBlank that has passed, wof_paula_deliver calls the
 * level-4 handler while a request is deliverable. */
#define WOF_DMACON 0x096
#define WOF_INTENA 0x09A
#define WOF_INTREQ 0x09C
void     wof_paula_write(uint16_t reg, uint16_t value);        /* a custom register, 0x096 on */
void     wof_paula_lc(int channel, uint32_t sound);            /* AUDxLC as a long */
uint16_t wof_paula_intenar(void);
uint16_t wof_paula_intreqr(void);
void     wof_paula_boundary(void);
void     wof_paula_deliver(void);
void     wof_paula_server(int inside);                           /* a VBlank server runs */
void     wof_paula_rate(uint16_t hz);                            /* the video standard changed */
const int8_t *wof_sound_data(uint32_t handle, uint32_t *left);  /* the bytes from a handle on */
#define WOF_CIAA_TALO 0xBFE401u
#define WOF_CIAA_TAHI 0xBFE501u
#define WOF_CIAA_CRA  0xBFEE01u
void     wof_cia_write(uint32_t address, uint8_t value);         /* CIA-A: TALO, TAHI, CRA */

/* The music (src/music.c, re/notes/music.md): the game's two calls, as coroutines because
 * both wait for a fade to end, and the player they drive.  The song data is file
 * WOF_SONG_FILE of the sound handles: its samples play from wofsongs's DATA hunk. */
#define WOF_SONG_FILE 8

/* Where the parts of src/mission.def lie in songplay's DATA hunk (0x1000 below
 * re/songplay.lst's addresses) and the voices in wofsongs's. */
#define WOF_PLAYER_HEAD   0x000u
#define WOF_PLAYER_VARS   0x27Cu
#define WOF_PLAYER_TRACKS 0x2AAu
#define WOF_PLAYER_SONG   0x3D2u
#define WOF_VOICES_AT     0x0CCu
#define WOF_VOICES        7u
void     wof_music_memory_load(const uint8_t *player, const uint8_t *songs);   /* src/core.c */
void     wof_music_memory_free(void);
wof_co_t wof_music_start(uint16_t song);   /* orig 0x0123DC music_start("wofsongs", song) */
wof_co_t wof_music_stop(void);             /* orig 0x012470 */
uint16_t wof_player_call(uint16_t command, uint32_t d1, uint32_t d2);  /* orig songplay+0x0000 */
void     wof_song_int(void);               /* orig songplay+0x02A6 SongInt, timer A's tick */
void     wof_song_int_handler(void);       /* orig songplay+0x0848, the player's level-4 handler */
const uint8_t *wof_song_data(uint32_t *size);   /* wofsongs's DATA hunk, as the file holds it */

/* The effects engine (src/sound.c, re/notes/sound.md), in the original's address order. */
void     wof_sound_slots_clear(void);       /* orig 0x011F4E */
void     wof_sound_slots_init(void);        /* orig 0x011F76 */
void     wof_sound_channels(void);          /* orig 0x012066 */
void     wof_engine_sound(void);            /* orig 0x012132 */
uint16_t wof_sound_boom(int16_t x);         /* orig 0x012324, D0 as it leaves it */
void     wof_sound_splash(int16_t x);       /* orig 0x01233E */
void     wof_sound_clang(void);             /* orig 0x012354 */
void     wof_sound_screech(void);           /* orig 0x012380 */
void     wof_sound_scream(uint16_t *d0, uint16_t *d1);   /* orig 0x0123AC, D0 and D1 in and out */
void     wof_sound_init(void);              /* orig 0x01E8B8 */
void     wof_audio_irq(void);               /* orig 0x01EBAA */
void     wof_soundfx_vblank(void);          /* orig 0x01EC64 */

#ifdef WOF_TRACE
/* The sound event log of SPEC 8 (src/audio.c): one entry per sample start and restart. */
typedef struct {
    uint64_t time;
    uint32_t vblank, pass, tick;
    uint32_t offset;
    uint16_t kind;       /* 'S' or 'R' */
    uint16_t channel;
    int16_t  file;       /* index in sound_files, -1 for none */
    uint16_t words, period, volume;
} wof_sound_event_t;
uint32_t                 wof_sound_event_count(void);
const wof_sound_event_t *wof_sound_event_at(uint32_t i);
void                     wof_sound_events_reset(void);
#endif

/* ------------------------------------------------------ the mission (M4, src/mission.c) */

void     wof_mission_init(void);            /* the dashboard picture's buffer, at start-up */
void     wof_free_mission_assets(void);     /* orig 0x011234 */
void     wof_free_dash_shapes(void);        /* orig 0x0134AE */
void     wof_free_sounds(void);             /* orig 0x01346C */
void     wof_free_for_load(void);           /* orig 0x011256 */
void     wof_campaign_reset(void);          /* orig 0x013562 */
void     wof_mission_reset_tables(void);    /* orig 0x0135A8 */
wof_co_t wof_player_lost_restart(void);     /* orig 0x0135D8: it waits in a tick */
void     wof_player_lost_restart_now(void); /* the same, where 0x027452 is 0 and it cannot */
wof_co_t wof_next_aircraft(void);           /* orig 0x0135CE */
void     wof_player_restart_state(void);    /* orig 0x013684 */
void     wof_objects_clear(void);           /* orig 0x013756 */
void     wof_mark_facing(int slot, uint16_t handle, uint16_t want);   /* a +8 marker, mirrored */
uint16_t wof_rand_mod(uint16_t n);          /* orig 0x01CAC8 */
void     wof_choose_night(void);            /* orig 0x0111FC */
void     wof_load_dash_assets(void);        /* orig 0x01653C */
int      wof_dash_slot(void);               /* the container dash_shapes names */
void     wof_map_load(void);                /* orig 0x012ADC, with map_scan 0x012D5A */
void     wof_dashboard_invalidate(void);    /* orig 0x01EDAA */
void     wof_load_ship_shapes(void);        /* orig 0x013252 */
void     wof_build_master_lists(void);      /* orig 0x01535A */
void     wof_sounds_load(void);             /* orig 0x013368 */
void     wof_sound_engine_load(void);       /* orig 0x01344E */
void     wof_sound_engine_free(void);       /* orig 0x0134A4 */
void     wof_ticker_clear(void);            /* orig 0x016BBC */
void     wof_demo_end(void);                /* orig 0x01852A */
wof_co_t wof_mission_display_setup(void);   /* orig 0x018806 */

/* ------------------------------------------- the tick (M4 part 2, src/tick.c, src/player.c) */

wof_co_t wof_logic_tick(void);              /* orig 0x011386 */
wof_co_t wof_player_update(void);           /* orig 0x01C660 */
void     wof_player_motion(void);           /* orig 0x01BDFA */
void     wof_guns(void);                    /* orig 0x01B682 */
void     wof_engine_idle(void);             /* orig 0x01B9CC */
void     wof_crash(void);                   /* orig 0x01AFBA */
uint32_t wof_aircraft_frame(int16_t state, int16_t facing, int16_t frame);  /* orig 0x01ABDE */
int16_t  wof_wheel_height(void);            /* orig 0x01AAEA */
uint32_t wof_record_at(int16_t x);          /* orig 0x01C982 */
int      wof_on_water(uint32_t at);         /* orig 0x01CB74 */
int      wof_record_on_ship(uint32_t at);   /* orig 0x01CB34 */
int      wof_record_is_land(uint32_t at);   /* orig 0x01CBB2 */
void     wof_burn_smoke(int16_t unused, int16_t kind, int16_t x, int16_t y);   /* orig 0x01CAE0 */
void     wof_aircraft_frame_index(wof_aircraft_t *a);   /* orig 0x01D35A */
void     wof_aircraft_launch(int16_t kind, int16_t x, int16_t height, int16_t facing);   /* orig 0x01E4D0 */
void     wof_enemy_aircraft_step(void);    /* orig 0x01E7D6 */
uint16_t wof_crand(void);                   /* orig 0x021E24, the C library's rand() */
void     wof_flash_set(int16_t count, int16_t colour);   /* orig 0x01CAB4 */
uint16_t wof_map_slot_at(int16_t x, uint16_t *slot);     /* orig 0x0150C8 */
int16_t  wof_ground_height(uint32_t at);    /* orig 0x015714 */
void     wof_object_spawn(uint32_t at, int16_t y, int16_t flag);   /* orig 0x010820 */
void     wof_splash_spawn(int16_t x);       /* orig 0x0152B0 */
uint32_t wof_smoke_claim(int32_t x, int32_t y, int16_t kind);      /* orig 0x015460: D0 at its end */
uint16_t wof_image16(uint32_t addr);        /* a constant word of the DATA hunk, by address */
uint8_t  wof_image8(uint32_t addr);         /* a byte of the same */
uint32_t wof_image32(uint32_t addr);

/* ------------------------------------------- the pass (M4, src/world.c and src/dash.c) */

wof_co_t wof_frame_update(void);            /* orig 0x010228 */
void     wof_draw_player(void);             /* orig 0x0103A6 */
void     wof_draw_enemy_aircraft(void);     /* orig 0x010DA6 */
void     wof_map_window(void);              /* orig 0x01417E */
void     wof_draw_dashboard(void);          /* orig 0x01EE16 */
void     wof_draw_game_over(void);          /* orig 0x0110C2 */
void     wof_flip_buffers(void);            /* orig 0x01030C */
void     wof_window_height(void);           /* orig 0x0141B4 */
void     wof_clip_to_waterline(void);       /* orig 0x01526E */
int      wof_ship_at_offset(int16_t x);     /* orig 0x014A4E: the ship's index, or -1 */
int      wof_ship_at_span(int16_t offset);  /* orig 0x014A52, from a map offset */
void     wof_deck_span(void);               /* orig 0x01B7BC */
void     wof_weapon_gauge_reset(void);      /* orig 0x01EDBC */
void     wof_lives_gauge_reset(void);       /* orig 0x01EDEA */
void     wof_dash_digit(int16_t x, int16_t y, uint16_t d); /* orig 0x01F2B0 */
void     wof_clip_playfield(void);          /* orig 0x01524A */
void     wof_draw_at(uint16_t handle, int16_t x, int16_t y);
void     wof_draw_world_shape(int table, int16_t slot, int16_t x, int16_t y);  /* orig 0x015174 */
uint16_t wof_table_entry(int table, int16_t index);

/* ---------------------------- the targets, the soldiers, the pools (M5, src/targets.c, pools.c) */

void     wof_soldier_out(const wof_gtarget_t *t, uint8_t d0, int16_t d1);   /* orig 0x011E82 */
void     wof_island_flag(int table, int16_t d4);            /* orig 0x013B52 */
void     wof_targets_3_draw(int table);                    /* orig 0x013D78 */
void     wof_targets_f_draw(int table);                    /* orig 0x013DE8 */
void     wof_soldiers_draw(void);                          /* orig 0x013EEE */
int      wof_target_records(int16_t x, uint16_t out[4]);   /* orig 0x014AE4 */
void    *wof_target_of(int16_t x);                         /* orig 0x014B54 */
int16_t  wof_target_frame(int16_t x);                      /* orig 0x014D50 */
int16_t  wof_target_range_frame(int16_t d0, int16_t d1, int16_t d2);   /* orig 0x014DB8 */
void     wof_burnt_barracks(int16_t d4);                   /* orig 0x014E18 */
void     wof_target_fire(int16_t x, uint16_t d1_high, uint16_t d2_high);                       /* orig 0x014F5C */
void     wof_target_refill(wof_gtarget_t *a0);             /* orig 0x014FEE */
void     wof_ticker_format(uint32_t format, uint32_t value, uint16_t at);   /* orig 0x015078 */
void     wof_ticker_say(uint32_t format, uint32_t value);  /* orig 0x015624 */
void     wof_ship_sunk_message(const wof_ship_t *s);       /* orig 0x015640 */
void     wof_mission_won(void);                            /* orig 0x015694 */
uint16_t wof_island_bonus(uint8_t island);                 /* orig 0x015AE8 */
void     wof_smoke_draw(void);                             /* orig 0x010EE0 */
void     wof_splashes_draw(void);                          /* orig 0x0152F8 */
void     wof_smoke_at_player(int16_t kind, uint16_t d2_high);   /* orig 0x0154E0 */
void     wof_balloons_draw(void);                          /* orig 0x01557C */
void     wof_draw_objects(void);                           /* orig 0x0106BE */
uint32_t wof_rand_upper(void);                             /* rand_beam's constant upper word */

/* The weapons in the tick (M5 part 2). */
int16_t  wof_sine(int16_t angle);                /* orig 0x015108 */
int16_t  wof_cosine(int16_t angle);              /* orig 0x015104 */
int16_t  wof_tangent(int16_t angle);             /* orig 0x01514C */
int16_t  wof_bearing_of(int16_t x, int16_t y, uint16_t high);   /* orig 0x015CA6 */
int16_t  wof_guns_ground_x(int16_t bearing);     /* orig 0x011A46 */
void     wof_soldiers_hit(int16_t x, int16_t w); /* orig 0x011A8C */
void     wof_torpedoes_hit(uint16_t d0, uint16_t d1);   /* orig 0x011AE2 */
void     wof_objects_step(uint32_t d4);          /* orig 0x010A72 */
void     wof_drop(void);                         /* orig 0x01107C */
int      wof_airfield_at(int16_t x);             /* orig 0x011126 */
int16_t  wof_pillbox_between(int16_t a, int16_t b);        /* orig 0x01115C */
uint32_t wof_ship_gun_between(int16_t a, int16_t b);       /* orig 0x0111A6 */
wof_gun_t *wof_ship_guns(const wof_ship_t *s);
void     wof_weapon_hit(const wof_object_t *o);  /* orig 0x0146DC */
void     wof_crash_hit(uint32_t at);             /* orig 0x0146C6 */

/* The map list's address where the machine's allocator gives none (the release build): the
 * headless original's for the first mission of a game. */
#define WOF_MAP_LIST_ADDRESS 0x0024F404u

/* Test-build hooks of the M4 comparisons (tests/shim.c); in the release build they are
 * constants, so dist/core.wasm has neither the table nor the pokes. */
#ifdef WOF_TRACE
void     wof_test_poke(uint32_t offset, uint32_t size, uint32_t value);
void     wof_test_pokes_clear(void);
void     wof_test_poke_address(uint32_t addr, uint32_t size, uint32_t value, uint32_t reset);
const wof_state_t *wof_trace_mission_state(void);
void     wof_test_poke_after_rank(void);          /* a run's pokes at the rank selection's end */
void     wof_test_poke_reset(uint32_t offset, uint32_t size, uint32_t value);
void     wof_test_poke_after_reset(void);         /* and after the mission's reset (0x0100D6) */
void     wof_test_map_addresses(const uint32_t *list, uint32_t n);   /* the machine's, per map load */
uint32_t wof_env_map_address(void);
int32_t  wof_test_player_call(uint32_t orig, int32_t a);   /* src/player.c, the oracle tests */
int32_t  wof_test_m5_call(uint32_t orig, int32_t a, int32_t b, int32_t c, int32_t *out);   /* src/targets.c */
int32_t  wof_test_m6_call(uint32_t orig, int32_t a, int32_t b, int32_t c, int32_t *out);   /* src/world.c */
int32_t  wof_test_tick_part(uint32_t orig);     /* src/tick.c */
int32_t  wof_test_enemy_call(uint32_t orig, int32_t a, int32_t b, int32_t c, int32_t *out);   /* src/enemy.c */
void     wof_trace_mission(void);                 /* the whole state at step S */
void     wof_trace_pass_end(void);                /* the whole state after a pass */
const wof_state_t *wof_trace_pass_state(void);
void     wof_test_set_tick_hook(void (*hook)(uint32_t tick));
void     wof_test_tick_end(uint32_t tick);        /* calls the test's hook, if any */
void     wof_test_set_step_s_hook(void (*hook)(uint32_t mission));
void     wof_test_set_pass_hook(void (*hook)(uint32_t pass, uint32_t end));
void     wof_test_pass_start(uint32_t pass);
void     wof_test_step_s(uint32_t mission);
#else
#define wof_test_step_s(mission) ((void)0)
#define wof_test_pass_start(pass) ((void)0)
#define wof_trace_pass_end() ((void)0)
#define wof_test_tick_end(tick) ((void)0)
#define wof_test_poke_after_rank() ((void)0)
#define wof_test_poke_after_reset() ((void)0)
#define wof_env_map_address() WOF_MAP_LIST_ADDRESS
#define wof_trace_mission() ((void)0)
#endif

#endif /* WOF_H */
