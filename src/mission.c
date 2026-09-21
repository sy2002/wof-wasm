/* The mission's setup and its end: everything main runs around the inner loop
 * (re/notes/porting-m4.md, "What was ported").  The routines follow the original's
 * addresses; the order in which main calls them is in src/front.c.
 *
 * Tables the original allocates live at fixed places in wof_m (src/mission.def).  Where the
 * original allocates one with MEMF_CLEAR the port clears the fixed table instead, and where
 * it frees one the port clears it as well, so that "not allocated" and "all zero" are the
 * same thing on both sides.  Nothing here takes memory from the arena.
 */
#include "wof.h"
#include "coro.h"
#include "gen/tables.h"

#define SHIP_DESTROYER  0
#define SHIP_BATTLESHIP 1
#define SHIP_CRUISESHIP 2
#define SHIP_JAPCARRIER 3
#define SHIP_CARRIER    4

#define carrier (wof_m.ship_records[SHIP_CARRIER])

/* The byte the original writes with st.b or clr.b into the high half of a word. */
static uint16_t high_byte(uint16_t word, uint8_t value)
{
    return (uint16_t)(((uint16_t)value << 8) | (word & 0x00FFu));
}

/* ------------------------------------------------------------------ small helpers */

/* orig 0x01CAC8 - rand_beam's low word modulo n (divu.w: the remainder of a 32 by 16
 * division of the zero-extended word). */
uint16_t wof_rand_mod(uint16_t n)
{
    uint16_t r = (uint16_t)wof_rand_beam(0x01CAC8);

    return n ? (uint16_t)(r % n) : 0;
}

/* The shape the original's shape_find_c returns from a container, as a handle. */
static uint16_t find_handle(int slot, uint32_t name)
{
    return wof_shape_handle(slot, wof_shape_find(&wof_assets.c[slot], name));
}

/* The mirror marker of a hellcat.shp or Torpedo.shp record (+8), which the state keeps
 * (SPEC 7.2), set to `want` with the pixel data mirrored when it changes. */
static void mark_facing(int slot, uint16_t handle, uint16_t want)
{
    wof_shape_t *s = (wof_shape_t *)wof_shape_of(handle);
    uint8_t     *m;
    int16_t      index = (int16_t)(handle & 0x7FF);

    if (!s)
        return;                 /* the original reads and writes address 8; nothing visible */
    m = slot == WOF_C_HELLCAT ? wof_f.marker_hellcat : wof_f.marker_torpedo;
    if (s->marker == want)
        return;
    wof_shape_mirror_x(s);
    s->marker = want;
    if (index < 128)
        m[index] = (uint8_t)want;
}

/* ---------------------------------------------------------- the pools, cleared on use */

#define CLEAR(table) wof_mem_set(wof_m.table, 0, sizeof wof_m.table)

/* ------------------------------------------------------------------ 0x011234 and after */

/* orig 0x0134AE - the dash container and its table.  The port keeps both dashboards loaded
 * from start-up (M1); what the original frees is the pointer, which is not state here. */
static void free_dash_shapes(void)
{
}

/* orig 0x01346C - seven of the eight sounds; the first stays until 0x0134A4 frees it from
 * the load dialog.  The port keeps only whether each one is loaded (M8 plays them). */
static void free_sounds(void)
{
    wof_f.sound_loaded &= 0x01u;
}

/* orig 0x012BBE - the map, the target tables, and the gun list and container of every
 * enemy ship the previous map carried.  The ship's flag at +4 is cleared as a byte, which
 * leaves the low byte of the word set. */
static void free_map(void)
{
    static const uint8_t order[4] = { SHIP_DESTROYER, SHIP_BATTLESHIP, SHIP_CRUISESHIP,
                                      SHIP_JAPCARRIER };

    CLEAR(map_records);
    CLEAR(target_records_4);
    CLEAR(target_records_f);
    CLEAR(target_records_3);
    CLEAR(soldier_records);
    for (int i = 0; i < 4; i++) {
        wof_ship_t *s = &wof_m.ship_records[order[i]];

        if ((uint16_t)s->present >> 8) {
            s->present = (int16_t)high_byte((uint16_t)s->present, 0);
            s->guns = 0;
            switch (order[i]) {
            case SHIP_DESTROYER:  CLEAR(guns_destroyer);  break;
            case SHIP_BATTLESHIP: CLEAR(guns_battleship); break;
            case SHIP_CRUISESHIP: CLEAR(guns_cruiseship); break;
            default:              CLEAR(guns_japcarrier); break;
            }
            wof_f.ship_loaded &= (uint8_t)~(1u << order[i]);
        }
    }
    wof_g.has_carrier = 0;
}

/* orig 0x011234 free_mission_assets.  Its first call, AllocMem(-1), asks exec to flush
 * memory and means nothing here; the demo buffer it frees last belongs to M7. */
void wof_free_mission_assets(void)
{
    free_dash_shapes();
    free_sounds();
    free_map();
}

/* orig 0x016BBC ticker_clear - BltClear of the ticker plane. */
void wof_ticker_clear(void)
{
    wof_mem_set(wof_f.vram + wof_f.ticker_base, 0, WOF_TICKER_BYTES);
}

/* orig 0x01852A - the end of a demo recording, which M7 owns, then demo_mode cleared. */
void wof_demo_end(void)
{
    if (wof_g.demo_mode == 2)
        WOF_STANDIN("M7 STAND-IN: saving a recorded demo");
    wof_g.demo_mode = 0;
}

/* ------------------------------------------------------- the outer loop's reset, 0x013562 */

/* orig 0x01EDEA - the lives drum: its target row, and both buffers told to redraw it. */
static void lives_gauge_reset(void)
{
    uint8_t d0 = wof_g.lives;

    if ((int8_t)d0 < 0)
        d0 = 0;
    if (d0 > 9)
        d0 = 9;
    wof_g.gauge_lives = (int16_t)(0x59 - (int16_t)(d0 << 3));
    wof_m.view_caches[0].lives = (int16_t)high_byte((uint16_t)wof_m.view_caches[0].lives, 0xFF);
    wof_m.view_caches[1].lives = (int16_t)high_byte((uint16_t)wof_m.view_caches[1].lives, 0xFF);
}

/* orig 0x01EDBC - the two drums of the weapon counter, from weapon_count by divu #10. */
static void weapon_gauge_reset(void)
{
    uint16_t n = wof_g.weapon_count;
    uint16_t q = (uint16_t)(n / 10u), r = (uint16_t)(n % 10u);

    wof_g.gauge_weapons_lo = (int16_t)(0x50 - (int16_t)(uint16_t)(q << 3));
    wof_g.gauge_weapons_hi = (int16_t)(0x50 - (int16_t)(uint16_t)(r << 3));
    wof_m.view_caches[0].weapons = (int16_t)high_byte((uint16_t)wof_m.view_caches[0].weapons, 0xFF);
    wof_m.view_caches[1].weapons = (int16_t)high_byte((uint16_t)wof_m.view_caches[1].weapons, 0xFF);
}

/* orig 0x01E608 - every byte of the four aircraft records cleared. */
static void aircraft_clear(void)
{
    wof_mem_set(wof_m.aircraft_records, 0, sizeof wof_m.aircraft_records);
}

/* orig 0x013756 - the kind byte of every object record, the extra one included. */
void wof_objects_clear(void)
{
    for (int i = 0; i < 15; i++)
        wof_m.object_records[i].kind = 0;
    wof_m.object_record_extra[0].kind = 0;
}

/* orig 0x01B9BC. */
static void sub_01b9bc(void)
{
    wof_g.g_02542c = 0;
    wof_g.g_025428 = 0;
}

/* orig 0x01ABDE - the name of the aircraft's frame for a state, a facing and a frame index,
 * with the frame's records in hellcat.shp and Torpedo.shp mirrored to the facing on the way
 * (re/notes/shapes.md).  The five mission scripts reach it in the setup only with the state
 * the reset leaves, 1, and g_025a9c clear; the other states are the tick's, part 2. */
uint32_t wof_aircraft_frame(int16_t state, int16_t facing, int16_t frame)
{
    uint32_t name;
    uint16_t want = (uint16_t)(facing + 1);

    if (state == 1 || state == 11) {
        if (wof_g.g_025a9c != 0) {
            WOF_STANDIN("M4 PART 2 STAND-IN: 0x01ABDE, state 1 with 0x025A9C set");
            return 0;
        }
        name = wof_tbl_frames_deck[frame & 7];
        mark_facing(WOF_C_HELLCAT, find_handle(WOF_C_HELLCAT, name), want);
        mark_facing(WOF_C_TORPEDO, find_handle(WOF_C_TORPEDO, name), want);
        wof_g.g_027de6 = (int16_t)wof_tbl_frames_deck_attitude[frame & 7];
        wof_g.g_025592 = 4;
        return name;
    }
    WOF_STANDIN("M4 PART 2 STAND-IN: 0x01ABDE, a flying state");
    return 0;
}

/* orig 0x01B7BC - the carrier's deck as world x, sixteen pixels in from both ends. */
static void deck_span(void)
{
    wof_g.g_0253fc = (int16_t)((uint16_t)carrier.span0 << 2);
    wof_g.g_0253fe = (int16_t)((uint16_t)carrier.span1 << 2);
    wof_g.g_0253fc = (int16_t)(wof_g.g_0253fc + 0x10);
    wof_g.g_0253fe = (int16_t)(wof_g.g_0253fe - 0x10);
}

/* orig 0x01B7EC - the player's record at a reset (re/notes/objects.md). */
static void player_reset(void)
{
    wof_player_t *p = &wof_m.player[0];

    deck_span();
    p->y = 0;
    p->speed_x = 0;
    p->speed_y = 0;
    p->on_deck = 1;
    p->w10 = (int16_t)(wof_rand_mod(4) + 6);
    p->oil = 0x80;
    p->fuel = 0xC0;
    p->frame_name = wof_aircraft_frame(p->on_deck, p->facing, 0);
    p->shape = find_handle(WOF_C_HELLCAT, p->frame_name);
    wof_m.torpedo_shape[0].s = find_handle(WOF_C_TORPEDO, p->frame_name);
    wof_g.pitch_target = 0;
    p->enemy_countdown = 0x546;
    wof_g.airspeed = 0;
    wof_g.g_02540a = 5;
    wof_g.g_02534a = 5;
    wof_g.g_025a9c = 0;
    wof_g.g_027168 = 0x1C;
    wof_g.g_02734e = wof_g.g_027168;
}

/* orig 0x013684 - the aircraft back on the carrier's lift, with everything the pass and the
 * tick keep about a flight put back. */
void wof_player_restart_state(void)
{
    wof_g.g_026d3e = 0x0F;
    wof_objects_clear();
    wof_g.weapon_type = 1;
    wof_g.flash_count = 0;
    wof_g.airspeed = 0;
    wof_g.g_02535f = 3;
    wof_g.g_02568c = 0;
    sub_01b9bc();
    wof_g.g_025f14 = 0x600;
    wof_g.g_025394 = 1;
    wof_g.g_025396 = 0x20;
    wof_g.split_row = 0x97;
    wof_g.g_025364 = 0xFF;
    wof_g.g_025366 = 0x20;
    wof_g.g_025367 = 0xFF;
    wof_g.g_025368 = 1;
    wof_g.g_025369 = 5;
    wof_g.g_0253a2 = (int16_t)wof_g.pass_counter;
    wof_g.g_02536a = 0;
    wof_g.g_0253a6 = 0;
    wof_g.g_02536c = 0;
    if (wof_g.weapon_count != 0xFF)
        wof_g.weapon_count = wof_tbl_weapons_per_type[wof_g.weapon_type];
    weapon_gauge_reset();
    wof_g.g_0253a8 = 2;
    wof_g.g_0253ac = -1;
    wof_g.g_0253b0 = 8;
    wof_g.g_0253b2 = 1;
    wof_g.g_0253b4 = 3;
    wof_g.g_0253b6 = 3;
    wof_g.g_0253b8 = 1;
    wof_g.g_0253ba = 0x16;
    wof_g.g_02536e = 1;
    wof_g.g_02536f = 1;
    player_reset();
}

/* orig 0x0135D8 player_lost_restart, as far as the mission setup reaches it.  The branch
 * that clears the playfield, flips the buffers and waits is taken when 0x027452 is set,
 * which only the tick does (re/notes/passes.md): it is part 2's. */
void wof_player_lost_restart(void)
{
    wof_player_t *p = &wof_m.player[0];

    p->x = wof_g.player_start_x;
    wof_g.attitude_index = 0;
    p->facing = -1;
    for (int i = 0; i < 40; i++)
        wof_m.smoke_records[i].kind = 0;

    if ((int8_t)wof_g.lives <= 0 || carrier.w0c <= 0) {
        /* 0x013612: no life left, or the carrier sunk: the game is over. */
        wof_g.game_over = 0xFF;
        wof_g.quit_flag = 0xFF;
        wof_g.lives = 0;
    } else {
        wof_g.g_02535f = 3;
        wof_g.g_025360 = 0;
        wof_player_restart_state();
        if (wof_g.g_027452 != 0)
            WOF_STANDIN("M4 PART 2 STAND-IN: player_lost_restart, the clear, flip and wait");
    }
    wof_g.g_027452 = 0;
}

/* orig 0x0135A8. */
void wof_mission_reset_tables(void)
{
    wof_g.g_02535d = 0;
    for (int i = 0; i < 4; i++)
        wof_m.aircraft_records[i].w[0] = 0;
    wof_g.g_0251d6 = 0;
    wof_g.g_0251d8 = 0;
    wof_g.pause_flag = 0;
    wof_player_lost_restart();
}

/* orig 0x013562 - the campaign's start: score, lives and the counters of a run. */
void wof_campaign_reset(void)
{
    carrier.w0c = 4;
    wof_g.player_score = 0;
    wof_g.g_0253bc = 0;
    wof_g.quit_flag = 0;                      /* clr.w: the flag and the byte after it */
    wof_g.g_0253c3 = 0;
    wof_g.g_02535e = 0xFF;
    wof_g.lives = 3;
    wof_g.g_025350 = 0x6000;
    wof_g.g_025354 = 0x400;
    wof_g.g_025358 = 0x55;
    wof_g.g_02535a = 0xA0;
    lives_gauge_reset();
    aircraft_clear();
    wof_mission_reset_tables();
}

/* orig 0x0111FC choose_night - the map number of the next mission; above 6 four draws of
 * rand_beam, of which the last one's top bit decides.  main calls it only between two
 * missions of a campaign, so the first mission is day whatever the map. */
void wof_choose_night(void)
{
    uint8_t  map = wof_tbl_mission_map_table[(uint16_t)(wof_g.rank_played * 4u + wof_g.mission_number) % 29u];
    uint16_t d0  = 0;

    if ((int8_t)map > 6) {
        wof_rand_beam(0x0111FC);
        wof_rand_beam(0x0111FC);
        wof_rand_beam(0x0111FC);
        d0 = (uint16_t)wof_rand_beam(0x0111FC);
        d0 = (uint16_t)(((d0 << 1) | (d0 >> 15)) & 1u);
    }
    wof_g.night_flag = d0;
}

/* ------------------------------------------------------------- load_dash_assets, 0x01653C */

/* The larger of the two dashboard pictures, iff-dash and nightdash, in bytes.  The buffer is
 * taken from the arena at start-up, with the assets (src/assets.c); it is file data, not
 * state, and is only ever read by mission_display_setup of the same mission. */
static uint8_t *dash_picture;
static uint32_t dash_picture_len;
static uint32_t dash_picture_cap;

void wof_mission_init(void)
{
    uint32_t a = 0, b = 0;

    wof_fs_find(wof_tbl_dash_picture_files[0], &a);
    wof_fs_find(wof_tbl_dash_picture_files[1], &b);
    dash_picture_cap = (a > b ? a : b) + 64u;
    dash_picture     = (uint8_t *)wof_alloc(dash_picture_cap);
    dash_picture_len = 0;
}

/* orig 0x01653C - the dashboard's shapes and its picture, by night_flag.  The port keeps
 * both dash containers loaded from start-up (M1) and notes which one is current; the files
 * are still opened here, in the original's order, and the picture is kept for
 * mission_display_setup, which decodes it. */
void wof_load_dash_assets(void)
{
    uint16_t night = (uint16_t)(wof_g.night_flag != 0);
    uint32_t mark  = wof_arena_mark();
    uint32_t len   = 0;
    uint8_t *file;

    wof_f.dash_night = (uint8_t)night;
    wof_load_file(wof_tbl_dash_shape_files[night], &len);        /* shapes_load's own load */
    wof_arena_release(mark);

    file = wof_load_file(wof_tbl_dash_picture_files[night], &len);
    dash_picture_len = 0;
    if (file && dash_picture && len <= dash_picture_cap) {
        wof_mem_copy(dash_picture, file, len);
        dash_picture_len = len;
    }
    wof_f.dash_picture_night = (uint8_t)(night + 1);
    wof_arena_release(mark);
}

/* The dashboard's container as the original's dash_shapes names it. */
int wof_dash_slot(void)
{
    return wof_f.dash_night ? WOF_C_NIGHTDASH : WOF_C_DASH;
}

/* ------------------------------------------------------------------ map_load, 0x012ADC */

/* orig 0x013554 - the four airfield records cleared. */
static void airfields_clear(void)
{
    wof_mem_set(wof_m.airfield_records, 0, sizeof wof_m.airfield_records);
}

static uint16_t map_word(uint32_t byte_offset)
{
    uint32_t i = byte_offset >> 1;

    return i < sizeof wof_m.map_records / sizeof wof_m.map_records[0]
           ? wof_m.map_records[i].v : 0;
}

/* orig 0x012C84 - the airfields from the markers 0x114 and 0x115: every second marker ends
 * an airfield record, and two bytes per airfield come from a table by map number. */
static void airfields_scan(void)
{
    uint8_t  map  = wof_tbl_mission_map_table[(uint16_t)(wof_g.rank_played * 4u + wof_g.mission_number) % 29u];
    uint32_t tab  = (uint32_t)map << 2;
    uint16_t n    = (uint16_t)((uint16_t)(wof_m.map_records_end[0].off >> 1) - 1u);
    uint16_t d1   = 0, d2 = 0;
    int      rec  = 0;

    for (int i = 0; i < 4; i++) {
        wof_m.airfield_records[i].w[0] = 0;
        wof_m.airfield_records[i].w[1] = 0;
    }
    for (uint32_t at = 0; ; at += 2) {
        uint16_t slot = (uint16_t)((map_word(at) >> 2) & 0x1FF);

        if ((slot == 0x114 || slot == 0x115) && rec < 4) {
            wof_airfield_t *a = &wof_m.airfield_records[rec];

            d1++;
            if (d1 & 1u) {
                a->w[0] = (int16_t)d2;
            } else {
                a->w[1] = (int16_t)d2;
                a->w[7] = (int16_t)(slot == 0x114 ? -1 : 1);
                a->w[3] = (int16_t)(tab < 64 ? wof_tbl_airfield_table[tab] : 0);
                tab++;
                a->w[2] = (int16_t)(tab < 64 ? wof_tbl_airfield_table[tab] : 0);
                tab++;
                rec++;
            }
        }
        d2 = (uint16_t)(d2 + 8);
        if (n-- == 0)
            break;
    }
}

/* orig 0x01252C - a ship block: by map number, two bytes (how many planes stand on the
 * ship, and a second one), then from the ship's list two words and four words per plane,
 * the x words offset by the ship's world x. */
/* The two tables by the original's address: the counts at 0x023530 and the lists at
 * 0x0235A8 are each one block of the executable (re/tables.toml). */
#define COUNTS(addr) ((uint32_t)((addr) - 0x023530u))
#define LIST(addr)   ((uint32_t)(((addr) - 0x0235A8u) / 2u))

static void ship_block(uint16_t span0, uint32_t counts, uint32_t list, uint32_t block)
{
    uint8_t  map = wof_tbl_mission_map_table[(uint16_t)(wof_g.rank_played * 4u + wof_g.mission_number) % 29u];
    uint32_t c   = counts + (uint32_t)map * 2u;
    uint16_t d2  = c < sizeof wof_tbl_block_counts ? wof_tbl_block_counts[c] : 0;
    uint16_t d1  = c + 1 < sizeof wof_tbl_block_counts ? wof_tbl_block_counts[c + 1] : 0;
    uint16_t    d0  = (uint16_t)(span0 << 2);
    wof_word_t *out = wof_m.ship_blocks;
    uint32_t    at  = block;

#define PUT(val) do { if (at < 160) out[at].v = (uint16_t)(val); at++; } while (0)
#define NEXT()   (list < sizeof wof_tbl_block_lists / 2u ? wof_tbl_block_lists[list++] : (list++, (uint16_t)0))
    PUT(d2);
    PUT(d1);
    PUT(NEXT() + d0);
    PUT(NEXT() + d0);
    for (uint16_t i = (uint16_t)(d2 - 1u); i != 0xFFFFu; i--) {
        uint16_t a = NEXT(), b = NEXT(), c1 = NEXT(), c2 = NEXT();

        PUT(a);
        PUT(b + d0);
        PUT(c1);
        PUT(c2);
    }
#undef NEXT
#undef PUT
}

/* orig 0x012D5A map_scan - the map walked twice: the first walk counts the targets and the
 * islands and fills the ship records; the tables are allocated by those counts; the second
 * walk fills them (re/notes/map.md).  The second walk goes one record past the list, which
 * the pool's capacity and its zeroes cover. */
static void map_scan(void)
{
    for (int i = 0; i < 8; i++)
        wof_g.island_span[i] = 0;
    airfields_scan();

    wof_m.ship_records[SHIP_BATTLESHIP].present = 0;
    wof_m.ship_records[SHIP_BATTLESHIP].w14 = 0;
    wof_m.ship_records[SHIP_BATTLESHIP].row = 0;
    wof_g.has_battleship = 0;
    wof_g.g_0255bf = 0;
    wof_m.ship_records[SHIP_JAPCARRIER].present = 0;
    wof_g.has_japcarrier = 0;
    wof_m.ship_records[SHIP_JAPCARRIER].w14 = 0;
    wof_m.ship_records[SHIP_JAPCARRIER].row = 0;
    carrier.present = -1;
    carrier.w14 = 0;
    carrier.row = 0;
    wof_m.ship_records[SHIP_DESTROYER].present = 0;
    wof_g.has_destroyer = 0;
    wof_m.ship_records[SHIP_DESTROYER].w14 = 0;
    wof_m.ship_records[SHIP_DESTROYER].row = 0;
    wof_m.ship_records[SHIP_CRUISESHIP].present = 0;
    wof_g.has_cruiseship = 0;
    wof_m.ship_records[SHIP_CRUISESHIP].w14 = 0;
    wof_m.ship_records[SHIP_CRUISESHIP].row = 0;
    wof_g.target_count_4 = 0;
    wof_g.target_count_f = 0;
    wof_g.target_count_3 = 0;
    wof_g.g_025600 = 0;

    /* The first walk. */
    for (uint16_t d2 = 0; d2 < wof_g.map_length; d2 = (uint16_t)(d2 + 2)) {
        uint16_t rec = map_word(d2);
        uint16_t slot;

        if (!(rec & 0x8000u))
            continue;
        slot = (uint16_t)(((rec & 0x7FFFu) >> 2) & 0x1FF);
        switch (slot) {
        case 0x004: wof_g.g_025600 = 0xFF; wof_g.target_count_4++; break;
        case 0x003: wof_g.g_025600 = 0xFF; wof_g.target_count_3++; break;
        case 0x00F: wof_g.g_025600 = 0xFF; wof_g.target_count_f++; break;
        case 0x002:
            wof_g.island_count++;
            if (wof_g.g_025600) {
                wof_g.g_025600 = 0;
                wof_g.briefing_number_1++;
                wof_g.g_025383++;
            }
            break;
        case 0x10D:
            if (!wof_g.has_battleship) {
                wof_ship_t *s = &wof_m.ship_records[SHIP_BATTLESHIP];

                wof_g.has_battleship = 0xFF;
                wof_g.briefing_number_2++;
                wof_g.g_025371++;
                s->present = -1;
                s->gun_count = 0x0E;
                s->w0e = 0x1B;
                s->w12 = 0x1194;
                s->w0c = 2;
                s->span0 = (int16_t)(d2 - 0x20);
                s->span1 = (int16_t)(s->span0 + 0xC0);
                ship_block((uint16_t)s->span0, COUNTS(0x02354Eu), LIST(0x0235CCu), 0x40);
            }
            break;
        case 0x0F2:
            if (!wof_g.has_japcarrier) {
                wof_ship_t *s = &wof_m.ship_records[SHIP_JAPCARRIER];

                wof_g.has_japcarrier = 0xFF;
                wof_g.briefing_number_2++;
                wof_g.g_025371++;
                s->present = -1;
                s->gun_count = 0x0F;
                s->w0e = 0x15;
                s->w12 = 0x1770;
                s->w0c = 3;
                s->w16 = 0x14;
                s->span0 = (int16_t)(d2 - 0x20);
                s->span1 = (int16_t)(s->span0 + 0x9C);
                ship_block((uint16_t)s->span0, COUNTS(0x02358Au), LIST(0x023614u), 0x80);
            }
            break;
        case 0x0E4:
            if (!wof_g.has_destroyer) {
                wof_ship_t *s = &wof_m.ship_records[SHIP_DESTROYER];

                wof_g.has_destroyer = 0xFF;
                wof_g.briefing_number_2++;
                wof_g.g_025371++;
                s->present = -1;
                s->gun_count = 8;
                s->w0e = 0x1B;
                s->w12 = 0x9C4;
                s->w0c = 1;
                s->w16 = 0x14;
                s->span0 = (int16_t)(d2 - 0x20);
                s->span1 = (int16_t)(s->span0 + 0xA0);
                ship_block((uint16_t)s->span0, COUNTS(0x023530u), LIST(0x0235A8u), 0x00);
            }
            break;
        case 0x0CC:
            if (!wof_g.has_cruiseship) {
                wof_ship_t *s = &wof_m.ship_records[SHIP_CRUISESHIP];

                wof_g.has_cruiseship = 0xFF;
                wof_g.briefing_number_2++;
                wof_g.g_025371++;
                s->present = -1;
                s->w0e = 0x1C;
                s->gun_count = 4;
                s->w12 = 0x3E8;
                s->w0c = 1;
                s->w16 = 0x14;
                s->span0 = (int16_t)(d2 - 0x10);
                s->span1 = (int16_t)(s->span0 + 0x20);
                ship_block((uint16_t)s->span0, COUNTS(0x02356Cu), LIST(0x0235F8u), 0x60);
            }
            break;
        case 0x021:
            if (!wof_g.has_carrier) {
                wof_g.has_carrier = 0xFF;
                carrier.present = -1;
                wof_g.quit_flag = 0;          /* clr.w */
                wof_g.g_0253c3 = 0;
                carrier.w0e = 0x21;
                carrier.w0c = 4;
                carrier.w12 = 0;
                carrier.guns = 0;             /* clr.l +6 */
                carrier.gun_count = 0;        /* clr.w +0xA */
                carrier.w16 = 0x14;
                carrier.span0 = (int16_t)(d2 - 0xA0);
                carrier.span1 = (int16_t)(carrier.span0 + 0xC0);
            }
            break;
        default:
            break;
        }
    }

    /* The allocations, MEMF_CLEAR. */
    if (wof_g.target_count_4)
        CLEAR(target_records_4);
    if (wof_g.target_count_3)
        CLEAR(target_records_3);
    wof_g.soldier_count = (uint16_t)((uint8_t)(wof_g.target_count_4 + wof_g.target_count_3) * 5u);
    if (wof_g.soldier_count)
        CLEAR(soldier_records);
    if (wof_g.target_count_f)
        CLEAR(target_records_f);

    /* The second walk. */
    {
        uint16_t t3 = 0, t4 = 0, tf = 0, s1 = 0, s2 = 0, island = 0;
        int16_t  d3 = (int16_t)wof_g.map_length;

        for (int i = 0; i < 8; i++)
            wof_g.island_score[i] = 0;
        for (uint16_t d2 = 0; ; d2 = (uint16_t)(d2 + 2)) {
            uint16_t rec = map_word(d2);

            if (rec & 0x8000u) {
                uint16_t slot = (uint16_t)(((rec & 0x7FFFu) >> 2) & 0x1FF);

                if (slot == 4) {                                   /* orig 0x013216 */
                    if (t4 < 16) {
                        wof_gtarget_t *t = &wof_m.target_records_4[t4];

                        t->x0 = t->x1 = (int16_t)(uint16_t)(d2 << 2);
                        t->map_offset = d2;
                        t->island = (uint8_t)island;
                        t->state = 5;
                    }
                    if (island < 4)
                        wof_g.island_score[island * 2] = (uint16_t)(wof_g.island_score[island * 2] + 5);
                    t4++;
                } else if (slot == 3) {                            /* orig 0x0131C8 */
                    if (island < 4) {
                        if (wof_g.island_span[island * 2] == 0)
                            wof_g.island_span[island * 2] = d2;
                        wof_g.island_span[island * 2 + 1] = d2;
                    }
                    if (t3 < 16) {
                        wof_gtarget_t *t = &wof_m.target_records_3[t3];
                        uint16_t      x = (uint16_t)(d2 << 2);

                        t->x0 = (int16_t)(x - 0x2C);
                        t->x1 = (int16_t)(x + 0x10);
                        t->map_offset = d2;
                        t->island = (uint8_t)island;
                        t->state = 5;
                    }
                    if (island < 4)
                        wof_g.island_score[island * 2] = (uint16_t)(wof_g.island_score[island * 2] + 5);
                    t3++;
                } else if (slot == 0x0F) {                         /* orig 0x013236 */
                    if (tf < 32) {
                        wof_gtarget_f_t *t = &wof_m.target_records_f[tf];

                        t->map_offset = (int16_t)d2;
                        t->island = (int16_t)island;
                        t->w04 = 0;
                    }
                    if (island < 4)
                        wof_g.island_score[island * 2 + 1]++;
                    tf++;
                } else if (slot == 1) {
                    if (s1 < 4)
                        wof_g.island_slot1[s1] = d2;
                    s1++;
                } else if (slot == 2) {
                    if (s2 < 4)
                        wof_g.island_slot2[s2] = d2;
                    s2++;
                    island++;
                }
            }
            d3 = (int16_t)(d3 - 1);
            if (d3 < 0)
                break;
            d3 = (int16_t)(d3 - 1);
            if (d3 == -1)
                break;
        }
    }
}

/* orig 0x012ADC map_load - the file by rank and mission, its two longs, and the records.
 * The loader asks for `length` bytes of records although the file holds length - 8 after
 * its header: the last four records are zero because the allocation is (re/notes/map.md),
 * and the port's table is cleared before it is read into, which is the same statement. */
void wof_map_load(void)
{
    uint16_t   index = 0;
    uint32_t   length, start;
    uint8_t    head[8];
    wof_file_t f;
    int        found;

    airfields_clear();
    wof_g.quit_flag = 0;                      /* clr.w */
    wof_g.g_0253c3 = 0;
    wof_g.briefing_number_2 = 0;
    wof_g.g_025371 = 0;
    wof_g.island_count = 0;
    wof_g.briefing_number_1 = 0;
    wof_g.g_025383 = 0;

    for (uint16_t r = 0; r < wof_g.rank_played && r < 7; r++)
        index = (uint16_t)(index + wof_tbl_maps_per_rank[r]);
    index = (uint16_t)(index + wof_g.mission_number - 1u);
    wof_m.map_records_end[0].off = 0;

    if (index >= 15)
        return;
    found = wof_dos_open(&f, wof_tbl_map_file_ptrs[index]);
    wof_trace_add("map_load", found, index, 0, 0, wof_tbl_map_file_ptrs[index], 32);
    if (!found)
        return;                                   /* the original goes on with a null handle */
    wof_dos_read(&f, head, 4);
    wof_dos_read(&f, head + 4, 4);
    length = ((uint32_t)head[0] << 24) | ((uint32_t)head[1] << 16) | ((uint32_t)head[2] << 8) | head[3];
    start  = ((uint32_t)head[4] << 24) | ((uint32_t)head[5] << 16) | ((uint32_t)head[6] << 8) | head[7];
    wof_g.player_start_x = (int16_t)(uint16_t)(start * 4u - 8u);

    CLEAR(map_records);                           /* mem_alloc: MEMF_CLEAR */
    {
        uint32_t cap = (uint32_t)sizeof wof_m.map_records;
        uint32_t n   = length < cap ? length : cap;
        uint8_t  buf[2];

        for (uint32_t i = 0; i + 1 < n; i += 2) {
            if (wof_dos_read(&f, buf, 2) != 2)
                break;
            wof_m.map_records[i / 2].v = (uint16_t)((buf[0] << 8) | buf[1]);
        }
    }
    wof_dos_close(&f);

    wof_g.map_length = (uint16_t)length;
    wof_g.map_extent = (uint16_t)(length * 4u);
    wof_m.map_records_end[0].off = (uint32_t)(length - 2u);
    map_scan();
}

/* ------------------------------------------------------------- after the briefing */

/* orig 0x01ED7A for both entries of view_caches, 0x01EDAA - every instrument of both
 * buffers invalidated, and the oil and fuel gauges' target rows. */
void wof_dashboard_invalidate(void)
{
    for (int v = 0; v < 2; v++) {
        wof_cache_t *c = &wof_m.view_caches[v];

        c->oil_warn  = (int16_t)high_byte((uint16_t)c->oil_warn, 0xFF);
        c->oil       = (int16_t)high_byte((uint16_t)c->oil, 0xFF);
        c->fuel_warn = (int16_t)high_byte((uint16_t)c->fuel_warn, 0xFF);
        c->fuel      = (int16_t)high_byte((uint16_t)c->fuel, 0xFF);
        c->weapon    = (int16_t)high_byte((uint16_t)c->weapon, 0xFF);
        c->weapons   = (int16_t)high_byte((uint16_t)c->weapons, 0xFF);
        c->lives     = (int16_t)high_byte((uint16_t)c->lives, 0xFF);
        c->w0e       = (int16_t)high_byte((uint16_t)c->w0e, 0xFF);
        c->score     = (c->score & 0x00FFFFFFu) | 0xFF000000u;
        wof_g.gauge_oil  = 0x3C;
        wof_g.gauge_fuel = 0x54;
    }
}

/* orig 0x01D1EA - the enemy aircraft's frames: 28 names each way in japplane.shp and in
 * 8thscale.shp, and three variants of each in the dashboard's container, the second
 * character of the name replaced by 1, 2 and 3. */
static void enemy_frames(void)
{
    int dash = wof_dash_slot();

    for (int i = 0; i < 28; i++) {
        wof_m.japplane_frames[i].s      = find_handle(WOF_C_JAPPLANE, wof_tbl_japplane_frames_left[i]);
        wof_m.japplane_frames[i + 28].s = find_handle(WOF_C_JAPPLANE, wof_tbl_japplane_frames_right[i]);
        wof_m.eighth_frames[i].s        = find_handle(WOF_C_EIGHTH, wof_tbl_eighth_frames_left[i]);
        wof_m.eighth_frames[i + 28].s   = find_handle(WOF_C_EIGHTH, wof_tbl_eighth_frames_right[i]);
        for (int j = 0; j < 3; j++) {
            uint32_t variant = (uint32_t)(int32_t)(int16_t)(uint16_t)((j + 0x31) << 8);
            uint32_t left    = (wof_tbl_dash_frames_left[i] & 0xFFFF00FFu) + variant;
            uint32_t right   = (wof_tbl_dash_frames_right[i] & 0xFFFF00FFu) + variant;

            wof_m.dash_frames[j * 0x38 + i].s        = find_handle(dash, left);
            wof_m.dash_frames[j * 0x38 + i + 0x1C].s = find_handle(dash, right);
        }
    }
}

/* orig 0x01350E - a ship's gun list: gun_count entries of 0x0E bytes, each with the ship's
 * world x plus the table's word at +4.  Not for a loaded game. */
static void ship_guns(int ship, wof_gun_t *list, const uint16_t *table)
{
    wof_ship_t *s = &wof_m.ship_records[ship];
    uint16_t    d1 = (uint16_t)((uint16_t)s->span0 << 2);

    if (wof_g.loaded_game)
        return;
    wof_mem_set(list, 0, 16 * sizeof *list);
    s->guns = 1;
    for (uint16_t i = 0; i < (uint16_t)s->gun_count && i < 16; i++)
        list[i].w[2] = (int16_t)(uint16_t)(table[i] + d1);
}

/* orig 0x013252 load_ship_shapes - the containers of the ships the map carries.  The port
 * has every container loaded from start-up (M1), so what is left is the files opened in
 * the original's order, the slot bases and the gun lists. */
void wof_load_ship_shapes(void)
{
    uint32_t mark = wof_arena_mark();
    uint32_t len  = 0;

    carrier.slot_base = 0;
    if (wof_g.has_battleship) {
        wof_load_file(wof_tbl_battleship_shp, &len);
        wof_arena_release(mark);
        wof_m.ship_records[SHIP_BATTLESHIP].slot_base = 0xF8;
        wof_f.ship_loaded |= 1u << SHIP_BATTLESHIP;
        ship_guns(SHIP_BATTLESHIP, wof_m.guns_battleship, wof_tbl_guns_battleship);
    }
    if (wof_g.has_destroyer) {
        wof_load_file(wof_tbl_destroyer_shp, &len);
        wof_arena_release(mark);
        wof_m.ship_records[SHIP_DESTROYER].slot_base = 0xD0;
        wof_f.ship_loaded |= 1u << SHIP_DESTROYER;
        ship_guns(SHIP_DESTROYER, wof_m.guns_destroyer, wof_tbl_guns_destroyer);
    }
    if (wof_g.has_cruiseship) {
        wof_load_file(wof_tbl_cruiseship_shp, &len);
        wof_arena_release(mark);
        wof_m.ship_records[SHIP_CRUISESHIP].slot_base = 0xB8;
        wof_f.ship_loaded |= 1u << SHIP_CRUISESHIP;
        ship_guns(SHIP_CRUISESHIP, wof_m.guns_cruiseship, wof_tbl_guns_cruiseship);
        if (!wof_g.loaded_game) {
            wof_m.guns_cruiseship[1].w[3] = 5;
            wof_m.guns_cruiseship[2].w[3] = 5;
        }
    }
    if (wof_g.has_japcarrier) {
        wof_load_file(wof_tbl_japcarrier_shp, &len);
        wof_arena_release(mark);
        wof_m.ship_records[SHIP_JAPCARRIER].slot_base = 0;
        wof_f.ship_loaded |= 1u << SHIP_JAPCARRIER;
        ship_guns(SHIP_JAPCARRIER, wof_m.guns_japcarrier, wof_tbl_guns_japcarrier);
    }
}

/* orig 0x01535A build_master_lists - MasterList and AthList, the two tables the map's slots
 * index (re/notes/shapes.md): the world table and the eighth-scale one, then a block per
 * ship, from the ship's own table and by name in 8thscale.shp, or nulls. */
void wof_build_master_lists(void)
{
    uint16_t at = 0;
    struct { int slot; const uint32_t *names; uint16_t count; uint8_t ship; } blocks[4] = {
        { WOF_C_CRUISESHIP, wof_tbl_cruiseship_names, 24, SHIP_CRUISESHIP },
        { WOF_C_DESTROYER,  wof_tbl_destroyer_names,  27, SHIP_DESTROYER },
        { WOF_C_JAPCARRIER, wof_tbl_japcarrier_names, 13, SHIP_JAPCARRIER },
        { WOF_C_BATTLESHIP, wof_tbl_battleship_names, 25, SHIP_BATTLESHIP },
    };

    for (; at < 184; at++) {
        wof_m.master_list[at].s = wof_table_handle(WOF_C_WORLD, at);
        wof_m.ath_list[at].s    = wof_table_handle(WOF_C_EIGHTH, at);
    }
    for (int b = 0; b < 4; b++) {
        int present = blocks[b].ship == SHIP_JAPCARRIER
                      ? wof_g.has_japcarrier != 0
                      : (wof_f.ship_loaded >> blocks[b].ship) & 1u;

        for (uint16_t i = 0; i < blocks[b].count; i++, at++) {
            if (present) {
                wof_m.master_list[at].s = wof_table_handle(blocks[b].slot, i);
                wof_m.ath_list[at].s    = find_handle(WOF_C_EIGHTH, blocks[b].names[i]);
            } else {
                wof_m.master_list[at].s = WOF_SHAPE_NONE;
                wof_m.ath_list[at].s    = WOF_SHAPE_NONE;
            }
        }
    }
}

/* The sounds in the order sounds_load (0x013368) takes them: the index in sound_files and
 * the index of the length it stores in sound_length. */
static const uint8_t sound_order[8][2] = {
    { 7, 2 }, { 3, 3 }, { 1, 6 }, { 2, 4 }, { 5, 5 }, { 0, 1 }, { 6, 7 }, { 4, 0 },
};

/* orig 0x013368 sounds_load - each effect's length by file_length (0x015B1A), then the file,
 * each only if it is not loaded yet.  The engine that plays them is M8's: the slots
 * sub_011f76 builds from the pointers are not ported (M8 STAND-IN: the sound slots, which
 * stand on the exclusion list of the completeness test), but the files are opened and the
 * lengths kept, in the original's order. */
void wof_sounds_load(void)
{
    for (int k = 0; k < 8; k++) {
        const char *name = wof_tbl_sound_files[sound_order[k][0]];
        uint32_t    mark = wof_arena_mark();
        uint32_t    len  = 0;
        wof_file_t  f;

        if (wof_f.sound_loaded & (1u << k))
            continue;
        if (wof_dos_open(&f, name)) {                     /* file_length: Open, Seek, Close */
            int32_t size = wof_dos_examine_size(f.entry);

            wof_g.sound_length[sound_order[k][1]] = (uint32_t)(size < 0 ? 0 : size);
            wof_dos_close(&f);
        }
        wof_load_file(name, &len);
        wof_arena_release(mark);
        wof_f.sound_loaded |= (uint8_t)(1u << k);
    }
}

/* ---------------------------------------------------------- mission_display_setup, 0x018806 */

/* orig 0x018806 mission_display_setup - the play screen on both views, the dashboard picture
 * into the back view's dashboard with its colours into both views' tables, the day or night
 * palettes into the back view's playfield (sky as table 1, ocean as table 2), COLOR01 of
 * the ticker, then the back view copied to the front one and the ticker ramp on both lists;
 * last the enemy aircraft's frames (re/notes/display.md, "Day and night"). */
wof_co_t wof_mission_display_setup(void)
{
    wof_ctx_t *c = &wof_f.co_setup;

    CO_BEGIN(c);
    CO_CALL(c, &wof_f.co_show, wof_cop_show_blank());
    wof_screen_game();
    {
        wof_vport_t *play = wof_back_vport();
        wof_vport_t *dash = play && play->next != WOF_VP_NONE ? &wof_f.vport[play->next] : 0;
        uint16_t     night = (uint16_t)(wof_g.night_flag != 0);

        if (dash && dash_picture_len)
            wof_iff_to_vport(dash_picture, dash_picture_len, dash);
        dash_picture_len = 0;                                     /* mem_free */
        if (dash)
            for (uint32_t i = 0; i < WOF_PAL_COLOURS; i++) {
                wof_f.vport[WOF_VP_A2].colours[i] = dash->colours[i];
                wof_f.vport[WOF_VP_B2].colours[i] = dash->colours[i];
            }
        wof_g.ticker_message = 0;
        wof_g.g_0255c8 = 0;
        if (play) {
            uint32_t mark = wof_arena_mark();
            uint32_t len  = 0;
            uint8_t *file = wof_load_file(wof_tbl_palette_files[night], &len);

            if (file)
                wof_cmap_file_to_table(file, len, play->colours);
            wof_arena_release(mark);
            file = wof_load_file(wof_tbl_ocean_palette_files[night], &len);
            if (file)
                wof_cmap_file_to_table(file, len, play->colours2);
            wof_arena_release(mark);
        }
        wof_f.vport[WOF_VP_TICKER].colours[1] = 0x777;
    }
    CO_CALL(c, &wof_f.co_show, wof_cop_show_blank());
    wof_view_copy(wof_f.back_view, wof_f.front_view);
    wof_cop_add_ticker_ramp(wof_f.back_view);
    wof_cop_add_ticker_ramp(wof_f.front_view);
    enemy_frames();
    CO_END(c);
}
