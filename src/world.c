/* One pass of the inner loop: frame_update (orig 0x010228) and its tree, the playfield half
 * (re/notes/drawing.md, "The scene routines"; re/notes/objects.md, "The order of a pass").
 * The dashboard half is src/dash.c.
 *
 * The routines are hand-written assembly in the original and pass values in registers from
 * one to the next; where a register crosses a call that way, the C passes it as an argument
 * and says which register it was.  The blitter library's shape_draw keeps d0 to d6, a0 to a3
 * and a5 (re/notes/porting-m4.md), which is what the callers rely on.
 *
 * What the five mission scripts of M4 never executed is not here: each such region of a
 * routine is one WOF_STANDIN with the milestone that owes it (re/notes/porting-m4.md,
 * "Stand-ins").  Reaching one skips it.
 */
#include "wof.h"
#include "coro.h"
#include "gen/tables.h"

#define carrier (wof_m.ship_records[4])

/* ------------------------------------------------------------------ pointer tables */

/* The pointer tables the scene routines index with move.l (a0,d2.w),a0: the resolved tables
 * of the containers, and MasterList and AthList.  A shape is a handle (src/shapes.c). */
enum { T_WORLD, T_EIGHTH, T_MASTER, T_ATH, T_TORPEDO, T_HELLCAT, T_JAPPLANE };

uint16_t wof_table_entry(int table, int16_t index)
{
    switch (table) {
    case T_WORLD:    return index >= 0 && index < 184 ? wof_table_handle(WOF_C_WORLD, (uint16_t)index) : 0;
    case T_EIGHTH:   return index >= 0 && index < 184 ? wof_table_handle(WOF_C_EIGHTH, (uint16_t)index) : 0;
    case T_MASTER:   return index >= 0 && index < 278 ? wof_m.master_list[index].s : 0;
    case T_ATH:      return index >= 0 && index < 278 ? wof_m.ath_list[index].s : 0;
    case T_TORPEDO:  return index >= 0 && index < 138 ? wof_table_handle(WOF_C_TORPEDO, (uint16_t)index) : 0;
    case T_HELLCAT:  return index >= 0 && index < 107 ? wof_table_handle(WOF_C_HELLCAT, (uint16_t)index) : 0;
    case T_JAPPLANE: return index >= 0 && index < 22 ? wof_table_handle(WOF_C_JAPPLANE, (uint16_t)index) : 0;
    default:         return 0;
    }
}

/* shape_draw with the caller's hotspot subtraction, as every scene routine does it:
 * sub.w 4(a0),d0; sub.w 6(a0),d1; suba.l a1,a1; jsr shape_draw.  A null record is drawn as
 * nothing; the original reads its "hotspot" from low memory and then blit_clip_setup
 * rejects it, so the call is recorded with no shape and no position. */
void wof_draw_at(uint16_t handle, int16_t x, int16_t y)
{
    const wof_shape_t *s = wof_shape_of(handle);

    if (!s) {
        wof_trace_add("shape_draw", 0, 0, 0, 1, 0, 0);
        return;
    }
    wof_shape_draw(s, (int16_t)(x - s->hot_x), (int16_t)(y - s->hot_y));
}

/* shape_draw at a position the caller has not taken the hotspot off: suba.l a1,a1; jsr
 * shape_draw straight after the position is computed.  A null record is drawn as nothing,
 * as in wof_draw_at. */
static void draw_raw(uint16_t handle, int16_t x, int16_t y)
{
    const wof_shape_t *s = wof_shape_of(handle);

    if (!s) {
        wof_trace_add("shape_draw", 0, 0, 0, 1, 0, 0);
        return;
    }
    wof_shape_draw(s, x, y);
}

/* The exclusive-or blit of a shape, recorded as the original's shape_draw_xor call. */
static void draw_xor(uint16_t handle, int16_t x, int16_t y)
{
    const wof_shape_t *s = wof_shape_of(handle);

    wof_trace_add("shape_draw_xor", s ? x : 0, s ? y : 0, handle, s ? 0 : 1, 0, 0);
    if (s)
        wof_shape_draw_xor(s, x, y);
}

/* orig 0x015174 draw_world_shape - A0 = table, D2 = slot, D0 = world x, D1 = world y: to
 * the screen with view_x, view_y and view_shift, dropped outside -128 to 448, then drawn
 * less its hotspot (re/notes/map.md). */
void wof_draw_world_shape(int table, int16_t slot, int16_t x, int16_t y)
{
    int16_t d1 = (int16_t)(-y + 0x0B + wof_g.view_y);
    int16_t d0 = (int16_t)(x - wof_g.view_x);

    if (wof_g.view_shift) {
        d0 = (int16_t)(d0 >> 3);
        d1 = (int16_t)(d1 >> 3);
    }
    if (d0 < -128 || d0 > 0x1C0)
        return;
    wof_draw_at(wof_table_entry(table, slot), d0, d1);
}

/* ------------------------------------------------------------------ clip helpers */

/* orig 0x01524A clip_playfield. */
void wof_clip_playfield(void)
{
    wof_clip_set(0, 0xA2, 0, 0x140);
}

/* orig 0x01526E - the playfield's clip with its bottom at the carrier's waterline, or 161
 * while 0x025394 is clear (re/notes/drawing.md). */
void wof_clip_to_waterline(void)
{
    int16_t d1 = (int16_t)(0xA2 - carrier.w0e + carrier.row + wof_g.g_026e56 + 3);

    if (wof_g.g_025394 == 0)
        d1 = 0xA1;
    wof_clip_set(wof_g.clip_top, d1, wof_g.clip_left, wof_g.clip_right);
}

/* ------------------------------------------------------------------ snapshot_for_draw */

/* orig 0x010F88 snapshot_for_draw - between Forbid and Permit, the logic's positions copied
 * into what the drawing reads (re/notes/objects.md), then two counters of the pass. */
static void snapshot_for_draw(void)
{
    const wof_player_t *p = &wof_m.player[0];

    wof_g.draw_player_x = p->x;
    wof_g.draw_player_y = p->y;
    wof_g.draw_facing   = p->facing;
    wof_g.draw_attitude = wof_g.attitude_index;
    wof_g.draw_g_026f7c = wof_g.g_026e62;
    wof_g.g_026e56      = wof_g.g_0253ae;
    wof_g.view_step     = wof_g.g_0253b0;
    for (int i = 0; i < 16; i++) {
        wof_object_t *o = i < 15 ? &wof_m.object_records[i] : &wof_m.object_record_extra[0];

        o->draw_x    = o->x;
        o->draw_y    = o->y;
        o->draw_kind = o->kind;
        o->draw_b0d  = o->b21;
    }
    for (int i = 0; i < 4; i++) {
        wof_aircraft_t *a = &wof_m.aircraft_records[i];

        a->draw_x = (int16_t)(uint16_t)((uint16_t)(int16_t)(a->x >> 3) * 2u);
    }
    for (int i = 0; i < 4; i++) {
        wof_m.airfield_records[i].w[8] = wof_m.airfield_records[i].w[3];
        wof_m.airfield_records[i].w[9] = wof_m.airfield_records[i].w[4];
    }
    for (int i = 0; i < 5; i++) {
        uint32_t at   = wof_tbl_ship_order[i];
        int      ship = (int)((at - 0x025460u) / 0x1Eu);

        if (ship >= 0 && ship < 5)
            wof_m.ship_records[ship].row = wof_m.ship_records[ship].w14;
    }
    for (int i = 0; i < 160; i++)
        wof_m.ship_blocks_draw[i].v = wof_m.ship_blocks[i].v;

    if ((int8_t)--wof_g.g_025368 < 0) {
        if ((int8_t)--wof_g.g_02538e < 0)
            wof_g.g_02538e = 0x0B;
        wof_g.g_025368 = 1;
    }
}

/* ------------------------------------------------------------ draw_world's sub-routines */

/* orig 0x014A4E ship_at_offset with 0x014A52 - the ship whose span of map offsets holds the
 * world x in D0, tested in the order destroyer, battleship, cruise ship, japanese carrier
 * and the player's carrier, each but the last only when the map carries it.  Returns the
 * ship's index, or -1 (the original's moveq #-1,d0). */
int wof_ship_at_offset(int16_t x)
{
    return wof_ship_at_span((int16_t)(uint16_t)(((uint16_t)x >> 3) * 2u));
}

/* orig 0x014A52 ship_at_span - the same, from a map offset. */
int wof_ship_at_span(int16_t d0)
{
    static const uint8_t order[4] = { 0, 1, 2, 3 };
    const uint8_t *flag[4] = { &wof_g.has_destroyer, &wof_g.has_battleship,
                               &wof_g.has_cruiseship, &wof_g.has_japcarrier };

    for (int i = 0; i < 4; i++) {
        const wof_ship_t *s = &wof_m.ship_records[order[i]];

        if (*flag[i] && d0 >= s->span0 && d0 <= s->span1)
            return order[i];
    }
    if (d0 >= carrier.span0 && d0 <= carrier.span1)
        return 4;
    return -1;
}

/* orig 0x014EAC ride_on_ship - a record of low bits 1 moved down with the ship it stands
 * on: D4 is the record's screen x, D1 its screen y; returns D1. */
static int16_t ride_on_ship(int16_t d4, int16_t d1)
{
    int16_t d0 = (int16_t)(d4 - 0xA0);
    int     ship;

    if (wof_g.view_shift)
        d0 = (int16_t)(uint16_t)((uint16_t)d0 << 3);
    d0 = (int16_t)(d0 + wof_g.draw_player_x);
    ship = wof_ship_at_offset(d0);
    if (ship < 0)
        return d1;
    {
        uint16_t add = (uint16_t)(wof_m.ship_records[ship].row + wof_g.g_026e56);

        if (wof_g.view_shift)
            add = (uint16_t)(add >> 3);
        return (int16_t)(d1 + (int16_t)add);
    }
}

/* orig 0x013B1C, the deck's lift (0x013BCE) - the two halves of the carrier's lift step
 * toward their targets from deck_lift_a and deck_lift_b, one row a pass, and are drawn at
 * the record's screen x.  D4 is that x, D5 split_row, D6 0x026E56, the table D7's. */
static void deck_lift(int table, int16_t d4, int16_t d6)
{
    if (!wof_g.g_027458) {
        uint8_t d0 = wof_g.g_02535f;
        int16_t d1;

        wof_g.g_027458 = 0xFF;
        if (d0 != wof_g.g_02568c) {
            wof_g.g_02568c = d0;
            wof_g.g_025654 = (int16_t)wof_tbl_deck_lift_a[(d0 * 2u + 1u) % 12u];
            wof_g.g_025658 = (int16_t)wof_tbl_deck_lift_b[(d0 * 2u + 1u) % 12u];
        }
        d1 = 1;
        if (wof_g.g_025656 != wof_g.g_025654) {
            if (!(wof_g.g_025656 < wof_g.g_025654))
                d1 = -1;
            wof_g.g_025656 = (int16_t)(wof_g.g_025656 + d1);
        } else if (wof_g.g_02568c != 2 || wof_g.g_025656 == wof_g.g_02565a) {
            uint16_t k  = (uint16_t)(wof_g.g_02568c * 2u);
            int16_t  v  = (int16_t)wof_tbl_deck_lift_a[k % 12u];

            if (v == wof_g.g_025656)
                v = (int16_t)wof_tbl_deck_lift_a[(k + 1u) % 12u];
            wof_g.g_025654 = v;
        }
        d1 = 1;
        if (wof_g.g_02565a != wof_g.g_025658) {
            if (!(wof_g.g_02565a < wof_g.g_025658))
                d1 = -1;
            wof_g.g_02565a = (int16_t)(wof_g.g_02565a + d1);
        } else {
            uint16_t k = (uint16_t)(wof_g.g_02568c * 2u);
            int16_t  v = (int16_t)wof_tbl_deck_lift_b[k % 12u];

            if (v == wof_g.g_02565a)
                v = (int16_t)wof_tbl_deck_lift_b[(k + 1u) % 12u];
            wof_g.g_025658 = v;
        }
    }
    {
        int16_t y = (int16_t)(wof_g.split_row + d6 + carrier.row);

        wof_draw_at(wof_table_entry(table, (int16_t)(wof_g.g_025656 + 0x8F)),
                    (int16_t)(d4 - 8), y);
        wof_draw_at(wof_table_entry(table, (int16_t)(wof_g.g_02565a + 8 + 0x8F)),
                    (int16_t)(d4 - 8), y);
    }
}

/* orig 0x013B1C, the deck's flag (0x013D10) - four frames from deck_flag_frames, one step
 * every second pass (on odd pass counts). */
static void deck_flag(int table, int16_t d4, int16_t d6)
{
    if (wof_g.pass_counter & 1u) {
        if ((int8_t)--wof_g.g_02538d < 0)
            wof_g.g_02538d = 3;
    }
    {
        uint8_t frame = wof_tbl_deck_flag_frames[wof_g.g_02538d & 3u];

        wof_draw_at(wof_table_entry(table, (int16_t)(frame + 0xB4)), (int16_t)(d4 - 8),
                    (int16_t)(wof_g.split_row + d6 + carrier.row));
    }
}

/* orig 0x013B1C - what one map record adds beside its own shape, by its slot word D3 (the
 * record shifted right by two, which keeps its height): a burnt barracks' smoke (a drawn
 * record of slot 5, at both scales), and at full scale the carrier's lift and flag and an
 * island's flag.  D4 is the record's screen x. */
static void record_extras(int table, uint16_t d3, int16_t d4, int16_t d6)
{
    if (d3 & 0x2000u) {
        d3 &= (uint16_t)~0x2000u;
        if (d3 == 5) {
            wof_burnt_barracks(d4);                              /* beq.w 0x014E18 */
            return;
        }
    }
    if (wof_g.view_step == 1)
        return;
    if (d3 == 0x22)
        deck_flag(table, d4, d6);
    else if (d3 == 0x9F)
        deck_lift(table, d4, d6);
    else if (d3 == 0x113)
        wof_island_flag(table, d4);
}

/* orig 0x013ABC - the lives waiting on the carrier's deck: one aircraft for every life but
 * the one flying, at most eight, thirty pixels apart from player_start_x - 200. */
static void deck_aircraft(void)
{
    uint8_t d3;
    int16_t d0, d1;
    int     table;

    if (carrier.present == 0)
        return;
    d3 = wof_g.lives;
    if (d3 > 9)                                                   /* cmp.b, bls: unsigned */
        d3 = 9;
    d3--;                                                         /* subq.b, ble: 1 or less */
    if (d3 == 0 || d3 == 0xFF)
        return;
    d0 = (int16_t)(wof_g.player_start_x - 0xC8);
    d1 = (int16_t)(0x0B - wof_g.g_026e56);
    table = wof_g.view_shift ? T_ATH : T_MASTER;
    d1 = (int16_t)(d1 - carrier.row);
    for (int16_t n = (int16_t)(int8_t)d3; n > 0; n--) {          /* dbra over the byte */
        wof_draw_world_shape(table, 0x26, d0, d1);
        d0 = (int16_t)(d0 - 0x1E);
    }
}

/* orig 0x01409C - the aircraft on the carrier's lift while the view is at full scale and
 * 0x025394 is clear, clipped at the waterline. */
static void lift_aircraft(void)
{
    if (wof_g.view_step != 8)
        return;
    if (wof_g.g_025394 != 1) {
        int16_t d1 = (int16_t)(carrier.w0e - carrier.row + 0x0B - wof_g.g_025396 - wof_g.g_026e56);

        wof_clip_to_waterline();
        wof_draw_world_shape(T_MASTER, 0x25, wof_g.player_start_x, d1);
    }
    wof_clip_playfield();
}

/* orig 0x013E6C - the ocean: at full scale five shapes of the wave animation from
 * world_shapes, 0x60 apart, from the player's x modulo 64; in the eighth-scale view a band
 * of colour 10 from row 151.  Returns D1, which 0x0140E8 takes as its own. */
static int16_t ocean(void)
{
    if (wof_g.view_step != 8) {
        wof_rect_fill(0, 0x97, 0x13F, 0xA2, 0x0A);
        return 0x97;
    }
    {
        int16_t  d0 = (int16_t)(0x3F - (wof_g.draw_player_x & 0x3F) + (int16_t)0xFFB0);
        int16_t  d1 = (int16_t)(wof_g.split_row + 0x0A);
        uint16_t h  = wof_table_entry(T_WORLD, (int16_t)(wof_g.g_02538e + 0x4E));
        const wof_shape_t *s = wof_shape_of(h);

        if (s) {
            d0 = (int16_t)(d0 - s->hot_x);
            d1 = (int16_t)(d1 - s->hot_y);
        }
        for (int i = 0; i < 5; i++) {
            if (s)
                wof_shape_draw(s, d0, d1);
            else
                wof_trace_add("shape_draw", 0, 0, 0, 1, 0, 0);
            d0 = (int16_t)(d0 + 0x60);
        }
        return d1;
    }
}

/* orig 0x0140E8 - the islands: for each, its two end shapes from MasterList (or AthList)
 * at the slot-1 and slot-2 records' world x, and a fill of colour 0x11 between them from
 * split_row down to the row the caller left in D1 (plus four at full scale). */
static void islands(int16_t d1_in)
{
    uint8_t n     = wof_g.island_count;
    int     table = wof_g.view_shift ? T_ATH : T_MASTER;
    int16_t d3    = d1_in;

    if (wof_g.view_step == 8)
        d3 = (int16_t)(d3 + 4);
    /* The two lists (0x025430, 0x025438) hold four words each and the walk takes as many as
     * island_count says, reading on into what follows them for a fifth: the words are read
     * by address.  No map carries more than four islands (re/notes/enemy.md, the maps). */
    for (uint16_t i = 0; (int16_t)(n - 1 - (int16_t)i) >= 0; i++) {
        int16_t x1 = (int16_t)(uint16_t)(wof_image16(0x025430u + 2u * i) << 2);
        int16_t x2 = (int16_t)(uint16_t)(wof_image16(0x025438u + 2u * i) << 2);
        int16_t d0, d2;

        wof_draw_world_shape(table, 1, x1, 0x0B);
        wof_draw_world_shape(table, 2, x2, 0x0B);
        d0 = (int16_t)(x1 - wof_g.view_x);
        d2 = (int16_t)(x2 - wof_g.view_x);
        if (wof_g.view_shift) {
            d0 = (int16_t)(d0 >> wof_g.view_shift);
            d2 = (int16_t)(d2 >> wof_g.view_shift);
        }
        wof_rect_fill(d0, wof_g.split_row, d2, d3, 0x11);
    }
}

/* The ship record at an address of ship_order (0x02555A). */
static wof_ship_t *ship_at(uint32_t addr)
{
    return &wof_m.ship_records[(addr - 0x025460u) / 0x1Eu];
}

/* A ship's gun list, the allocation behind its +0x06 (src/mission.def). */
static wof_gun_t *guns_of(const wof_ship_t *s)
{
    switch (s - wof_m.ship_records) {
    case 0:  return wof_m.guns_destroyer;
    case 1:  return wof_m.guns_battleship;
    case 2:  return wof_m.guns_cruiseship;
    case 3:  return wof_m.guns_japcarrier;
    default: return 0;
    }
}

/* orig 0x014EFC - a ship's gun at world x D0 shells the aircraft: when a draw of rand_beam
 * modulo 512 exceeds its distance from the player's live x (unsigned), it notes the shot
 * (0x026D4A, which nothing reads) and, with the aircraft no higher than 0xC8 and a second
 * draw's low nibble below 6, a third puts a splash in the water within 32 pixels of the
 * drawing's x (0x0152B0), where a torpedo of the player's within ten pixels goes out
 * (0x011AE2).  D0 to D2 are kept. */
static void ship_gun_shell(int16_t x)
{
    int16_t  d0 = (int16_t)(x - wof_m.player[0].x);
    uint16_t d2;

    if (d0 < 0)
        d0 = (int16_t)-d0;
    d2 = (uint16_t)d0;
    if (d2 >= (uint16_t)(wof_rand_beam(0x014EFC) & 0x1FFu))
        return;
    wof_g.ship_shell = (uint16_t)((wof_g.ship_shell & 0x00FFu) | 0xFF00u);   /* st.b */
    if (wof_m.player[0].y > 0xC8)
        return;
    if ((int16_t)((wof_rand_beam(0x014EFC) & 0x0Fu) - 6) >= 0)
        return;
    d2 = (uint16_t)((wof_rand_beam(0x014EFC) & 0x3Fu) - 0x20u + (uint16_t)wof_g.draw_player_x);
    wof_splash_spawn((int16_t)d2);
    wof_torpedoes_hit(d2, 0x0A);
}

/* orig 0x014C3E ship_guns_draw - the enemy ships' guns while the aircraft is off the deck:
 * every ship of ship_order to its negative end but the player's carrier, afloat (+0x04) and
 * not yet sunk (+0x0C above 0), every gun of its list.  A standing gun (+0x08 clear) shells
 * the aircraft (0x014EFC), and within reach shows the frame of target_range_frame for its
 * distance and the drawing's height, plus 0x81 and seven more on bit 15 of a draw of
 * rand_beam, at the ship's deck less its row and the swell plus the gun's own height and
 * 0x0D; in the eighth-scale view the frame 0x5A, drawn on a clear bit 15 of a further draw;
 * then it may hit the aircraft (0x014F5C).  A destroyed gun smokes while +0x0A runs, a puff
 * every 0x32 - +0x0A passes as +0x0A counts down, at its x and, as a 16.16 long, the ship's
 * deck less its row with D1's old upper word plus 0x0D as the fraction (the swap comes
 * before the add); smoke_claim raises a height below 16 to 16.  D1's upper word is 0 at
 * the entry (observed at every entry over the M6 scripts, re/notes/porting-m6.md) and is
 * what the smoke's long left it after one; target_fire takes it with D2's, which is 0. */
static void ship_guns_draw(int table)
{
    uint16_t d1_high = 0;

    if (wof_m.player[0].on_deck != 0)
        return;
    for (int i = 0;; i++) {
        uint32_t    at = wof_tbl_ship_order[i];
        wof_ship_t *s;
        wof_gun_t  *g;

        if ((int32_t)at < 0)
            break;
        if (at == 0x0254D8u)
            continue;
        s = ship_at(at);
        if (s->present == 0 || s->w0c <= 0)
            continue;
        g = guns_of(s);
        for (uint16_t n = 0; (int16_t)(s->gun_count - 1 - (int16_t)n) >= 0 && n < 16; n++, g++) {
            int16_t *w = g->w;                 /* +0x04 x, +0x06 height, +0x08 destroyed,
                                                * +0x0A puffs left, +0x0C passes to the next */
            int16_t  d1, d2;

            if (w[4] != 0) {
                int32_t y;

                if (w[5] == 0)
                    continue;
                if (--w[6] > 0)
                    continue;
                if (--w[5] == 0)
                    continue;
                w[6] = (int16_t)(0x32 - w[5]);
                y = (int32_t)(((uint32_t)(uint16_t)(s->w0e - s->row) << 16) |
                              (uint16_t)(d1_high + 0x0D));
                wof_smoke_claim((int32_t)((uint32_t)(uint16_t)w[2] << 16), y, 5);
                d1_high = y < 0x100000 ? 0x10 : (uint16_t)((uint32_t)y >> 16);
                continue;
            }
            ship_gun_shell(w[2]);
            d2 = wof_target_range_frame(w[2], wof_g.draw_player_x, wof_g.draw_player_y);
            if (d2 < 0)
                continue;
            d1 = (int16_t)(s->w0e - s->row - wof_g.g_026e56 + w[3] + 0x0D);
            d2 = (int16_t)(d2 + 0x81);
            if (wof_rand_beam(0x014C3E) & 0x8000u)
                d2 = (int16_t)(d2 + 7);
            if (wof_g.view_step == 1) {
                d2 = 0x5A;
                if (!(wof_rand_beam(0x014C3E) & 0x8000u))
                    wof_draw_world_shape(table, d2, w[2], d1);
            } else {
                wof_draw_world_shape(table, d2, w[2], d1);
            }
            wof_target_fire(w[2], d1_high, 0);
        }
    }
}

/* orig 0x013A18 airfields_draw - the aircraft parked on each airfield in use (+0x02 set):
 * japplane_shapes entry 20 facing west, from the east end +0x02 westward 0x40 apart, or
 * entry 21 facing east from the west end +0x00 eastward (+0x0E not -1), as many as the
 * drawing's count +0x10, on the sea's row view_y; and the one rolling to take off at its
 * drawing's x +0x12.  In the eighth-scale view entries 0xA0 and 0xA3 of eighth_shapes, all
 * of it shifted down by three and a row higher. */
static void airfields_draw(void)
{
    for (int i = 0; i < 4; i++) {
        const wof_airfield_t *a = &wof_m.airfield_records[i];
        uint16_t h = wof_table_entry(T_JAPPLANE, 20);
        const wof_shape_t *sh;
        int16_t  d0 = a->w[1], d1 = wof_g.view_y, d2 = 0x20;
        int16_t  n = a->w[8];

        if (d0 == 0)
            continue;
        if (a->w[7] != -1) {
            h = wof_table_entry(T_JAPPLANE, 21);
            d0 = a->w[0];
            d2 = -0x20;
        }
        d0 = (int16_t)(d0 - wof_g.view_x);
        if (wof_g.view_shift) {
            d0 = (int16_t)(d0 >> 3);
            d2 = (int16_t)(d2 >> 3);
            d1 = (int16_t)((d1 >> 3) - 1);
            h = wof_table_entry(T_EIGHTH, a->w[7] != -1 ? 0xA3 : 0xA0);
        }
        sh = wof_shape_of(h);
        d0 = (int16_t)(d0 - d2);
        d2 = (int16_t)(d2 + d2);
        d0 = (int16_t)(d0 - (sh ? sh->hot_x : 0));
        d1 = (int16_t)(d1 - (sh ? sh->hot_y : 0));
        for (int16_t k = n; (int16_t)(k - 1) != -1; k--) {       /* bra to dbra: n draws */
            draw_raw(h, d0, d1);
            d0 = (int16_t)(d0 - d2);
        }
        d0 = a->w[9];
        if (d0 == 0)
            continue;
        d0 = (int16_t)(d0 - wof_g.view_x);
        if (wof_g.view_shift)
            d0 = (int16_t)(d0 >> 3);
        draw_raw(h, (int16_t)(d0 - (sh ? sh->hot_x : 0)), d1);
    }
}

/* orig 0x01391E ship_planes - the aircraft parked on the ships' decks, from the drawing's
 * copy of the ship blocks (0x024F38, the block of the ship at the same place of ship_order
 * 0x40 bytes on): every entry whose +0x00 is set, japplane_shapes entry 0x14, or 0x15 when
 * its +0x06 is not negative, at its x and its height less the ship's row (and the swell at
 * full scale); in the eighth-scale view entries 0xA0 and 0xA3 of eighth_shapes under a clip
 * at row 0x96.  The last ship of the order, the Japanese carrier, clips its aircraft at its
 * waterline, 0x8E below its row.  After the walk, with that carrier's block holding
 * aircraft and at full scale, its crane, MasterList entry 0xF7, 0x199 east of its first
 * map offset and 0x15 above the row the walk left in D6 (the last ship afloat's, else the
 * swell draw_world handed on, d6_in), drawn without its hotspot under the caller's clip. */
static void ship_planes(int16_t d6_in)
{
    int16_t saved_bottom = wof_g.clip_bottom;
    int16_t d6 = d6_in;

    for (int k = 0; k < 5; k++) {
        const wof_ship_t *s = ship_at(wof_tbl_ship_order[k]);
        uint16_t count;

        if (s->present == 0)
            continue;
        d6 = s->row;
        if (wof_g.view_shift) {
            wof_g.clip_bottom = 0x96;
        } else {
            d6 = (int16_t)(d6 + wof_g.g_026e56);
            if (4 - k <= 0) {
                int16_t d1 = (int16_t)(0x8E + d6);

                if (d1 < wof_g.clip_bottom)
                    wof_g.clip_bottom = d1;
            }
        }
        count = wof_m.ship_blocks_draw[k * 0x20].v;
        for (uint16_t n = 0; (int16_t)(count - 1 - n) >= 0 && n < 7; n++) {
            const wof_word_t *e = &wof_m.ship_blocks_draw[k * 0x20 + 4 + 4 * n];
            int16_t d2;
            int     table = T_JAPPLANE;

            if (e[0].v == 0)
                continue;
            d2 = (int16_t)e[3].v < 0 ? 0x14 : 0x15;
            if (wof_g.view_shift) {
                table = T_EIGHTH;
                d2 = (int16_t)e[3].v < 0 ? 0xA0 : 0xA3;
            }
            wof_draw_world_shape(table, d2, (int16_t)e[1].v, (int16_t)((int16_t)e[2].v - d6));
        }
    }
    if ((int16_t)wof_m.ship_blocks_draw[4 * 0x20].v > 0 && !wof_g.view_shift) {
        const wof_ship_t *jc = ship_at(wof_tbl_ship_order[4]);
        int16_t d0 = (int16_t)((int16_t)(jc->span0 << 2) + 0x199 - wof_g.view_x);
        int16_t d1 = (int16_t)(-0x15 + d6 + wof_g.view_y);

        if (d0 >= -0x80 && d0 <= 0x1C0) {
            wof_g.clip_bottom = saved_bottom;
            draw_raw(wof_m.master_list[0xF7].s, d0, d1);
        }
    }
    wof_g.clip_bottom = saved_bottom;
}

/* orig 0x01CB34 - whether a map record rides on a ship: 1 for low bits 1, 0 for any other
 * record and for one outside the list (at or before its start, or at its last record). */
int wof_record_on_ship(uint32_t at)
{
    uint32_t end = wof_m.map_records_end[0].off;

    if (at == 0 || !(at < end - 2u))
        return 0;
    return ((at >> 1) < 3576u && (wof_m.map_records[at >> 1].v & 3u) == 1) ? 1 : 0;
}

/* orig 0x01CBF2 - the ship a record of low bits 1 belongs to, as its place in ship_order
 * (0x02555A).  Where the record is on no ship, or on none of the five, the original prints
 * a debugging line to its console (0x021DCE) and returns 1; the port returns 1. */
static int16_t ship_of_record(uint32_t at)
{
    int16_t off = (int16_t)(uint16_t)at;

    if (!wof_record_on_ship(at))
        return 1;
    for (int16_t i = 0; i < 5; i++) {
        int ship = (int)((wof_tbl_ship_order[i] - 0x025460u) / 0x1Eu);
        const wof_ship_t *sh = &wof_m.ship_records[ship];

        if (off >= sh->span0 && off <= sh->span1)
            return i;
    }
    return 1;
}

/* orig 0x0103A6 - the player's aircraft, at screen x 160 and at its height below view_y,
 * clipped at the carrier's waterline: its shape from the player's record at full scale, or
 * from eighth_shapes by facing and climb in the eighth-scale view; before it, at full
 * scale while it flies level or stands on the lift, the shape 0x02541A (moved a row a pass
 * toward 0x02540A).  Nothing is drawn while 0x025394 says the aircraft is aboard.  On the
 * way it overwrites the drawing's copy of the height with the player's own when the
 * aircraft is on the deck, in the eighth-scale view or left of the map, which is the
 * copy 0x026E60 that the tick reads (re/notes/passes.md). */
void wof_draw_player(void)
{
    const wof_player_t *p = &wof_m.player[0];
    int16_t  saved = wof_g.clip_bottom;
    uint16_t shape;
    int16_t  d6, d7;
    int      own_y = 0;

    if (p->on_deck == 1 || p->on_deck == 7 || p->on_deck == 0x0B || p->on_deck == 8) {
        own_y = 1;
    } else {
        if (wof_g.g_025394 == 1)
            goto done;
        if (wof_g.view_shift || wof_g.draw_player_x < 0) {
            own_y = 1;
        } else {
            uint32_t at = (uint32_t)(uint16_t)(((uint16_t)wof_g.draw_player_x >> 3) * 2u);

            if (at < wof_m.map_records_end[0].off &&
                ((at >> 1) < 3576u ? (wof_m.map_records[at >> 1].v & 3u) : 0u) == 1)
                (void)ship_of_record(at);           /* its height is computed and dropped */
        }
    }
    if (own_y)
        wof_g.draw_player_y = p->y;
    wof_g.clip_bottom = 0xA1;

    if (wof_g.view_step == 1) {
        int16_t d1 = wof_g.draw_facing, d2 = wof_g.draw_attitude;

        if (d2 != 0) {                                /* 0x01047E: in a turn */
            if ((uint16_t)d2 > 8 && (uint16_t)d2 < 0x12) {
                if ((uint16_t)d2 > 0x0D)
                    d1 = (int16_t)-d1;
                d2 = (int16_t)(d2 + 0x2F);
                if (d1 >= 0)
                    d2 = (int16_t)(d2 + 9);
            } else {
                if ((uint16_t)d2 >= 0x12)
                    d2 = (int16_t)(0x1A - d2);
                d2 = (int16_t)((int16_t)(d2 - 1) >> 2);
                d2 = (int16_t)(d2 + 0x34);
                if (d1 >= 0)
                    d2 = (int16_t)(d2 + 2);
            }
        } else {
            d2 = (int16_t)((int16_t)-wof_g.draw_g_026f7c >> 2);
            if (d2 < -2)
                d2 = -2;                              /* read: the five scripts never clamp */
            if (d1 >= 0)
                d2 = (int16_t)(d2 + 6);
            d2 = (int16_t)(d2 + 0x2A);
        }
        shape = wof_table_entry(T_EIGHTH, d2);
    } else {
        shape = p->shape;
    }
    d6 = 0xA0;
    d7 = (int16_t)((int16_t)(wof_g.view_y - wof_g.draw_player_y) >> wof_g.view_shift);
    wof_clip_to_waterline();
    if (wof_g.draw_attitude == 0 && wof_g.weapon_type == 2 && wof_g.weapon_count &&
        !wof_g.view_shift)
        wof_draw_at(wof_m.torpedo_shape[0].s, d6, d7);         /* 0x01052A: the torpedo under it */

    if (wof_g.draw_attitude == 0 && !wof_g.view_shift &&
        (p->on_deck == 0 || p->on_deck == 7 || wof_g.g_025a9c != 0)) {
        int16_t d1 = wof_g.g_02534a;

        if (d1 != wof_g.g_02540a) {
            if (d1 > wof_g.g_02540a)
                d1 = (int16_t)(d1 - 1);
            else
                d1 = (int16_t)(d1 + 1);           /* read: the five scripts only fell */
            wof_g.g_02534a = d1;
        }
        wof_draw_at(wof_m.g_02541a[0].s, d6, (int16_t)(d1 - 5 + d7));
    }
    wof_draw_at(shape, d6, d7);
    if (p->on_deck == 7) {
        /* 0x0105CA: the arresting cable, from where the hook caught it (0x026D3A) to the
         * hook, 16 pixels behind the aircraft and 5 below its reference point. */
        int16_t d5 = p->facing >= 0 ? 0x10 : -0x10;

        wof_line_draw((int16_t)(wof_g.g_026d3a - wof_g.draw_player_x + 0xA0), (int16_t)(d7 + 6),
                      (int16_t)(d6 - d5), (int16_t)(d7 + 5), 3);
    }
    if (wof_g.draw_attitude != 0 && wof_g.weapon_type == 2 && wof_g.weapon_count &&
        !wof_g.view_shift)
        wof_draw_at(wof_m.torpedo_shape[0].s, d6, d7);         /* 0x010610: banked */
    wof_clip_playfield();
    if (wof_g.g_02536a != 0 && wof_g.draw_attitude == 0 && wof_g.view_step != 1) {
        /* 0x010654: the guns' muzzle flash, a frame of muzzle_frames (0x024C08) by a count
         * of the passes the guns fire, none on its even steps: a hellcat_shapes entry by the
         * aircraft's frame (0x025592), 0x43 on or 0x57 on, ten further on facing left,
         * drawn with the exclusive-or blit at the aircraft's place. */
        uint8_t d0 = (uint8_t)((wof_g.muzzle_frame + 1u) & 3u);

        wof_g.muzzle_frame = d0;
        d0 = wof_image8(0x024C08u + d0);
        if (d0) {
            int16_t  d2 = (int16_t)(wof_g.g_025592 - 5 + (d0 == 1 ? 0x43 : 0x57));
            uint16_t h;
            const wof_shape_t *s;

            if (wof_g.draw_facing < 0)
                d2 = (int16_t)(d2 + 0x0A);
            h = wof_table_entry(T_HELLCAT, d2);
            s = wof_shape_of(h);
            wof_trace_add("shape_draw_xor", s ? (int16_t)(d6 - s->hot_x) : 0,
                          s ? (int16_t)(d7 - s->hot_y) : 0, h, s ? 0 : 1, 0, 0);
            if (s)
                wof_shape_draw_xor(s, (int16_t)(d6 - s->hot_x), (int16_t)(d7 - s->hot_y));
        }
    }
done:

    wof_g.clip_bottom = saved;
}

/* The k-th word of the wrecks' list (0x0251DA), read on past its forty words into the
 * aircraft records behind it as the original's (a5)+ would; nothing else lies closer. */
static int16_t wreck_word(uint16_t k)
{
    if (k < 40)
        return wof_g.wrecks[k];
    if (k < 40 + 4 * 26) {
        const uint8_t *b = (const uint8_t *)wof_m.aircraft_records + 2u * (k - 40u);
        int16_t        v;

        wof_mem_copy(&v, b, 2);
        return v;
    }
    return (int16_t)wof_image16(0x0251DAu + 2u * k);
}

/* An entry of the enemy aircraft's frame tables (0x026F8E at full scale, 0x02706E in the
 * eighth-scale view, 56 each: 28 facing west, then 28 facing east), read by address as the
 * original's (a0,d2.w) does: past the first table lies the second. */
static uint16_t enemy_frame(int eighth, int16_t index)
{
    int32_t i = (eighth ? 56 : 0) + index;

    if (i >= 0 && i < 56)
        return wof_m.japplane_frames[i].s;
    if (i >= 56 && i < 112)
        return wof_m.eighth_frames[i - 56].s;
    return WOF_SHAPE_NONE;
}

/* orig 0x010DA6 draw_enemy_aircraft - the wrecks of the enemy aircraft shot down, and the
 * four aircraft records.  A wreck is a word of 0x0251DA, as many as 0x0251D8 counts
 * (0x01E476 leaves one when a burning wreck on the water, state 0x10, has gone out): the
 * world x, negative for an aircraft that faced west, drawn with frame 27 or 55 of the frame
 * table four rows above view_y.  A record in use is drawn at its x (+0x20) and height
 * (+0x26) with the frame +0x30; one that fires (+0x12) at full scale counts +0x2C up in the
 * pass and on its odd counts puts its guns' flash over it, japplane_shapes entry 0x10 or
 * 0x11, two further on facing west, with the exclusive-or blit. */
void wof_draw_enemy_aircraft(void)
{
    int eighth = wof_g.view_shift != 0;

    for (int16_t n = wof_g.wreck_count; (int16_t)(n - 1) != -1; n--) {   /* bra to dbra */
        int16_t  d0 = wreck_word((uint16_t)(wof_g.wreck_count - n));
        int16_t  d2 = d0;
        int16_t  d1 = (int16_t)(-4 + wof_g.view_y);
        uint16_t h;
        const wof_shape_t *s;

        if (d0 < 0)
            d0 = (int16_t)-d0;
        d0 = (int16_t)(d0 - wof_g.view_x);
        if (eighth) {
            d0 = (int16_t)(d0 >> 3);
            d1 = (int16_t)(d1 >> 3);
        }
        if (d0 < -0x80 || d0 > 0x1C0)
            continue;
        h = enemy_frame(eighth, d2 < 0 ? 27 : 55);
        s = wof_shape_of(h);
        if (!s) {
            wof_trace_add("shape_draw", 0, 0, 0, 1, 0, 0);
            continue;
        }
        wof_shape_draw(s, (int16_t)(d0 - s->hot_x), (int16_t)(d1 - s->hot_y));
    }
    for (int i = 0; i < 4; i++) {
        wof_aircraft_t *a = &wof_m.aircraft_records[i];
        int16_t  d0, d1;
        uint16_t h;
        const wof_shape_t *s;

        if (a->state == 0)
            continue;
        d0 = (int16_t)(a->x - wof_g.view_x);
        d1 = (int16_t)(-a->y + wof_g.view_y - 7);
        if (eighth) {
            d0 = (int16_t)(d0 >> 3);
            d1 = (int16_t)(d1 >> 3);
        }
        if (d0 < -0x80 || d0 > 0x1C0)
            continue;
        h = enemy_frame(eighth, a->frame);
        s = wof_shape_of(h);
        if (!s) {
            wof_trace_add("shape_draw", 0, 0, 0, 1, 0, 0);
            continue;
        }
        wof_shape_draw(s, (int16_t)(d0 - s->hot_x), (int16_t)(d1 - s->hot_y));
        if (a->firing == 0 || eighth)
            continue;
        a->flash = (int16_t)(a->flash + 1);
        if (!(a->flash & 1))
            continue;
        {
            int16_t  d2 = (int16_t)(((uint16_t)a->flash & 3u) >> 1);
            uint16_t fh;
            const wof_shape_t *f;

            d2 = (int16_t)(d2 + 0x10);
            if (a->facing < 0)
                d2 = (int16_t)(d2 + 2);
            fh = wof_table_entry(T_JAPPLANE, d2);
            f = wof_shape_of(fh);
            draw_xor(fh, f ? (int16_t)(d0 - f->hot_x) : 0, f ? (int16_t)(d1 - f->hot_y) : 0);
        }
    }
}

/* ------------------------------------------------------------------ draw_world, 0x013772 */

/* orig 0x013772 draw_world - the sky, then the map strip from MasterList or AthList with
 * each record's extras, then the scene's layers in their fixed order (re/notes/map.md). */
static void draw_world(void)
{
    int      table;
    int16_t  d4, d6, d5, split;
    int32_t  at;
    uint32_t end = wof_m.map_records_end[0].off;

    wof_g.g_027458 = 0;
    wof_g.g_027454 = 0;
    wof_g.g_027456 = 0x2710;
    {
        uint16_t d3 = (uint16_t)(wof_g.view_y + 1);

        if (d3 > 0xA1)
            d3 = 0xA1;
        wof_rect_fill(0, 0, 0x13F, (int16_t)d3, 1);
    }
    wof_g.pass_counter = (uint16_t)(wof_g.pass_counter + 1u == 100u ? 0u : wof_g.pass_counter + 1u);

    d6 = wof_g.draw_player_x;
    if (wof_g.view_step == 1)
        d6 = (int16_t)(d6 & (int16_t)0xFFF8);
    {
        int16_t d1 = 0x120, d2;

        if (wof_g.view_step != 8)
            d1 = (int16_t)(uint16_t)((uint16_t)d1 << 3);
        d2 = (int16_t)((int16_t)(d6 - d1) >> 2);
        d2 = (int16_t)(d2 & ~1);
        at = d2;                                             /* adda.w: sign-extended */
    }
    d4 = (int16_t)(8 - (d6 & 7) + (int16_t)0xFF80);
    d6 = wof_g.g_026e56;
    d5 = (int16_t)((wof_g.draw_player_y >> 4) + 0x18);
    wof_g.g_0253e6 = d5;
    table = wof_g.view_step == 1 ? T_ATH : T_MASTER;

    /* Records before the map's start are stepped over without being read. */
    while (at < 0) {
        at += 2;
        d4 = (int16_t)(d4 + wof_g.view_step);
        if (d4 >= 0x1D0)
            goto layers;
    }
    split = wof_g.split_row;
    for (;;) {
        uint16_t rec = (uint32_t)at >> 1 < 3576u ? wof_m.map_records[(uint32_t)at >> 1].v : 0;
        uint16_t d3  = (uint16_t)(rec >> 2);

        at += 2;
        if ((uint32_t)at > end)
            break;
        if (d3 & 0x2000u) {
            uint16_t h = wof_table_entry(table, (int16_t)((rec >> 2) & 0x1FF));

            if (h != WOF_SHAPE_NONE) {
                int16_t y = wof_g.view_shift ? 0x97
                                             : (int16_t)(((d3 >> 7) & 0x1C) + split);

                if ((rec & 3u) == 1)
                    y = ride_on_ship(d4, y);
                wof_trace_add("map_draw", (int32_t)(at / 2 - 1), (int32_t)((rec >> 2) & 0x1FF),
                              (int16_t)(d4 - 8), y, 0, 0);
                wof_draw_at(h, (int16_t)(d4 - 8), y);
            }
        }
        record_extras(table, d3, d4, d6);
        d4 = (int16_t)(d4 + wof_g.view_step);
        if (d4 >= 0x1D0)
            break;
    }
layers:
    deck_aircraft();
    lift_aircraft();
    wof_draw_player();
    wof_draw_enemy_aircraft();
    wof_targets_3_draw(table);
    wof_targets_f_draw(table);
    ship_guns_draw(table);
    airfields_draw();
    ship_planes(wof_g.g_026e56);
    islands(ocean());

    if (wof_g.g_027454 != 0) {
        uint16_t d0 = (uint16_t)((uint16_t)wof_g.g_027456 >> 3);

        if (d0 > 0x40)
            d0 = 0x40;
        wof_g.g_027166 = (int16_t)(0x40 - d0);
        wof_g.g_027164 = (uint16_t)((wof_g.g_027164 & 0x00FFu) | 0xFF00u);
    } else {
        wof_g.g_027164 = 0;
    }
    wof_g.g_027458 = 0;
}

/* ---------------------------------------------------------- the pools and the objects */

/* orig 0x010344 - two shapes of world_shapes at a fixed place, unmasked, while 0x025364 is
 * set and 0x0253BC clear: entry 0x4D, and entry 0x4A plus the weapon type. */
static void weapon_marker(void)
{
    if (!wof_g.g_025364 || wof_g.g_0253bc)
        return;
    {
        const wof_shape_t *a = wof_shape_of(wof_table_entry(T_WORLD, 0x4D));
        const wof_shape_t *b = wof_shape_of(wof_table_entry(T_WORLD, (int16_t)(wof_g.weapon_type + 0x4A)));

        if (a)
            wof_shape_blit(a, 0, (int16_t)(0xFA - a->hot_x), (int16_t)(0x3C - a->hot_y));
        if (b)
            wof_shape_blit(b, 0, (int16_t)(0xFA - b->hot_x), (int16_t)(0x3C - b->hot_y));
    }
}

/* orig 0x0110C2 draw_game_over - `gmov` from world.shp, centred on the playfield, while the
 * game is over; then the countdown in game_over_count, which sets quit_flag when it runs
 * out: `subq.b #1` and `bgt`, so the flag is set when the count was 1 or below as a signed
 * byte before the step, 0x80 included.  In the five scripts the game ended with the count
 * at zero, so the countdown is held to the original under the oracle for every count
 * (tests/test_oracle_m4.py). */
void wof_draw_game_over(void)
{
    if (!wof_g.game_over)
        return;
    wof_clip_playfield();
    wof_draw_set_target(wof_back_vport());
    {
        int16_t index = wof_shape_find(&wof_assets.c[WOF_C_WORLD], 0x676D6F76u);   /* 'gmov' */

        if (index >= 0) {
            const wof_shape_t *s = &wof_assets.c[WOF_C_WORLD].shapes[index];

            wof_shape_draw(s, (int16_t)(0xA0 - s->hot_x), (int16_t)(0x51 - s->hot_y));
        }
    }
    if (wof_g.game_over_count) {
        int8_t before = (int8_t)wof_g.game_over_count;

        wof_g.game_over_count--;
        if (before <= 1)
            wof_g.quit_flag = 0xFF;
    }
}

/* orig 0x01030C flip_buffers - COLOR01 of the back list poked with the sky colour, or with
 * flash_colour on odd counts while flash_count runs, then the back view shown.  The flash
 * is set in the tick by a rocket's or a crash's hit on land (0x0146DC, rockets_a). */
void wof_flip_buffers(void)
{
    wof_vport_t *v  = wof_back_vport();
    uint16_t     d1 = v ? v->colours[1] : 0;
    uint16_t     d2 = wof_g.flash_count;

    if (d2 != 0) {
        wof_g.flash_count--;
        if (d2 & 1u)
            d1 = wof_g.flash_colour;
    }
    wof_cop_poke_colour1(wof_f.back_view, d1);
    wof_view_show(wof_f.back_view);                          /* flip_view 0x0150B0 */
}

/* ------------------------------------------------------------------ frame_update */

/* orig 0x010228 frame_update - one pass.  It begins with wait_vblank, and the pass as a
 * whole begins only when wof_vblanks_per_pass VBlanks have happened since the previous one
 * began and vblank_flag is set: that is the headless original's rule for when a pass may
 * start (re/notes/headless.md, "Scheduling"), and a pass that finds the flag clear owes
 * one more.  VBlanks inside a pass count toward the next one. */
wof_co_t wof_frame_update(void)
{
    wof_ctx_t *c = &wof_f.co_pass;

    CO_BEGIN(c);
    CO_WAIT_UNTIL(c, wof_s.since_pass >= (uint32_t)wof_vblanks_per_pass() && wof_g.vblank_flag);
    wof_s.since_pass = 0;
    wof_f.passes_run++;
    wof_test_pass_start(wof_f.passes_run);
    wof_trace_add("pass", (int32_t)wof_f.passes_run, 0, 0, 0, 0, 0);
    CO_CALL(c, &wof_f.co_vblank, wof_wait_vblank());

    wof_g.g_0253a6++;
    if (wof_g.g_0253a6 > 10)
        wof_g.g_0253a6 = 0;
    wof_clip_playfield();
    wof_draw_set_target(wof_back_vport());
    snapshot_for_draw();
    {
        int16_t d1 = wof_g.view_step == 1 ? 3 : 0;
        int16_t d0;

        wof_g.view_shift = d1;
        wof_g.view_x = (int16_t)((int16_t)(uint16_t)((uint16_t)0xFF60 << d1) + wof_g.draw_player_x);
        d0 = 0x97;
        if (wof_g.view_step == 1) {
            wof_g.view_y = 0x4B8;
        } else {
            int32_t d = (int32_t)wof_g.draw_player_y - 0x83;     /* sub.w, ble: exact */

            if (d > 0)
                d0 = (int16_t)(d0 + d);
            wof_g.view_y = d0;
        }
        wof_g.split_row = d0;
        if (d0 > 0xA2)
            d0 = 0xA2;
        wof_cop_set_split_line(d0);
    }
    if (wof_g.g_024f24) {
        /* No instruction of the executable sets 0x024F24; the call is kept as it is. */
        carrier.present = -1;
        CO_CALL(c, &wof_f.co_lost_restart, wof_player_lost_restart());
        wof_g.g_024f24 = 0;
    }
    draw_world();
    wof_smoke_draw();
    wof_soldiers_draw();
    wof_splashes_draw();
    wof_draw_objects();
    weapon_marker();
    wof_balloons_draw();
    wof_draw_game_over();
    wof_clip_set(0, 0x25, 0, 0x280);                         /* clip_dashboard 0x01F2DC */
    {
        wof_vport_t *play = wof_back_vport();

        wof_draw_set_target(play && play->next != WOF_VP_NONE ? &wof_f.vport[play->next] : 0);
    }
    wof_map_window();
    wof_draw_dashboard();
    wof_g.frame_drawn = 0xFF;
    wof_flip_buffers();
    wof_trace_pass_end();
    CO_END(c);
}

#ifdef WOF_TRACE
/* The oracle tests' entry into the pass routines of M6 part 1 (tests/test_oracle_m6.py). */
int32_t wof_test_m6_call(uint32_t orig, int32_t a, int32_t b, int32_t c, int32_t *out)
{
    (void)b; (void)c; (void)out;
    switch (orig) {
    case 0x014EFC: ship_gun_shell((int16_t)a); return 0;
    case 0x014C3E: ship_guns_draw(wof_g.view_step == 1 ? T_ATH : T_MASTER); return 0;
    default:       return -1000;
    }
}
#endif
