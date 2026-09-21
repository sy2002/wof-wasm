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

        a->w[0x17] = (int16_t)(uint16_t)((uint16_t)(int16_t)(a->w[0x10] >> 3) * 2u);
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
 * record shifted right by two, which keeps its height): the carrier's lift and flag at full
 * scale.  D4 is the record's screen x. */
static void record_extras(int table, uint16_t d3, int16_t d4, int16_t d6)
{
    if (d3 & 0x2000u) {
        d3 &= (uint16_t)~0x2000u;
        if (d3 == 5) {
            WOF_STANDIN("M5 STAND-IN: 0x014E18, a slot-5 target in view");
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
        WOF_STANDIN("M5 STAND-IN: 0x013B52, an island's flag");
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
    for (uint16_t i = 0; (int16_t)(n - 1 - (int16_t)i) >= 0 && i < 4; i++) {
        int16_t x1 = (int16_t)(uint16_t)(wof_g.island_slot1[i] << 2);
        int16_t x2 = (int16_t)(uint16_t)(wof_g.island_slot2[i] << 2);
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
    if (n > 4)
        WOF_STANDIN("M6 STAND-IN: more than four islands, in 0x0140E8");
}

/* orig 0x014D50 - whether a target of the map shows its firing frame this pass: never while
 * the aircraft is on the deck; in the eighth-scale view on a coin of rand_beam's top bit;
 * at full scale by 0x014DB8's range test, which gives none for a target more than 0x200
 * pixels behind or ahead of the aircraft.  The five scripts met only such targets; one in
 * range goes on to a frame by height and distance (M5).  D0 is the target's world x.
 * Returns the frame, or -1.  `sub.w d0,d1` and `bgt` decide on the exact difference, the
 * two compares with 0x200 on the 16-bit one. */
static int16_t target_frame(int16_t x)
{
    if (wof_m.player[0].on_deck != 0)
        return -1;
    if (wof_g.view_shift) {
        uint16_t r = (uint16_t)wof_rand_beam(0x014D50);

        return (r & 0x8000u) ? 0x5A : -1;
    }
    if (wof_g.view_step == 1) {                                   /* orig 0x014DB8 */
        WOF_STANDIN("M5 STAND-IN: 0x014DCA, the range test in the eighth-scale view");
        return -1;
    }
    {
        int32_t r  = (int32_t)wof_g.draw_player_x - x;
        int16_t d1 = (int16_t)r;

        if (r > 0 ? d1 > 0x200 : d1 < -0x200)
            return -1;
    }
    WOF_STANDIN("M5 STAND-IN: 0x014DE8, a target within range at full scale");
    return -1;
}

/* orig 0x014F5C - a target near the aircraft may hit it: the five scripts only met targets
 * more than 448 pixels away, where it returns at once. */
static void target_fire(int16_t x)
{
    int16_t d0 = (int16_t)(x - wof_g.draw_player_x);

    if (d0 < 0)
        d0 = (int16_t)-d0;
    if (d0 > 0x1C0)
        return;
    WOF_STANDIN("M5 STAND-IN: 0x014F72, a target near the aircraft");
}

/* orig 0x013D78 - the slot-3 targets of the map: while one stands (+8 set) and its count at
 * +0x0C is clear, its frame from 0x014D50 at its world x, then 0x014F5C. */
static void targets_3(int table)
{
    for (uint16_t i = 0; i < wof_g.target_count_3 && i < 16; i++) {
        wof_gtarget_t *t = &wof_m.target_records_3[i];
        int16_t        x, frame;

        if (t->state == 0) {
            WOF_STANDIN("M5 STAND-IN: 0x013D92, a destroyed slot-3 target");
            continue;
        }
        if (t->w0c != 0) {
            WOF_STANDIN("M5 STAND-IN: 0x013DB2, a slot-3 target's count");
            continue;
        }
        x = (int16_t)(uint16_t)((uint16_t)t->map_offset << 2);
        frame = target_frame(x);
        if (frame < 0)
            continue;
        wof_draw_world_shape(table, frame, x, 0x14);
        target_fire(x);
    }
}

/* orig 0x013DE8 - the slot-0x0F targets.  Map a has none, so the five scripts never ran
 * the loop's body. */
static void targets_f(int table)
{
    (void)table;
    if (wof_g.target_count_f)
        WOF_STANDIN("M5 STAND-IN: 0x013DFA, the slot-0x0F targets");
}

/* orig 0x014C3E - the enemy ships' guns, while the aircraft is off the deck: the ship list
 * walked, the player's carrier skipped; the five scripts met no enemy ship (M6). */
static void ship_guns(void)
{
    if (wof_m.player[0].on_deck != 0)
        return;
    for (int i = 0; i < 6; i++) {
        uint32_t at   = wof_tbl_ship_order[i];
        int      ship = (int)((at - 0x025460u) / 0x1Eu);

        if ((int32_t)at < 0)
            break;
        if (at == 0x0254D8u || ship < 0 || ship > 4)
            continue;
        if (wof_m.ship_records[ship].present != 0)
            WOF_STANDIN("M6 STAND-IN: 0x014C66, an enemy ship's guns");
    }
}

/* orig 0x013A18 - the airfields' aircraft rows (M6); a record whose +2 is clear is empty. */
static void airfields(void)
{
    for (int i = 0; i < 4; i++)
        if (wof_m.airfield_records[i].w[1] != 0)
            WOF_STANDIN("M6 STAND-IN: 0x013A36, an airfield in view");
}

/* orig 0x01391E - the aircraft parked on the ships (the ship blocks' drawing copy), each
 * ship's block at 0x40 bytes, and the japanese carrier's deck crane (M6). */
static void ship_planes(void)
{
    int16_t saved_bottom = wof_g.clip_bottom;

    for (int k = 0; k < 5; k++) {
        uint32_t at   = wof_tbl_ship_order[k];
        int      ship = (int)((at - 0x025460u) / 0x1Eu);
        const wof_ship_t *s = (ship >= 0 && ship < 5) ? &wof_m.ship_records[ship] : 0;
        uint16_t count;

        if (!s || s->present == 0)
            continue;
        if (wof_g.view_shift) {
            wof_g.clip_bottom = 0x96;
        } else if (4 - k <= 0) {
            WOF_STANDIN("M6 STAND-IN: 0x01395A, the last ship's clip at full scale");
        }
        count = wof_m.ship_blocks_draw[k * 0x20].v;
        if (count)
            WOF_STANDIN("M6 STAND-IN: 0x013976, aircraft on a ship's deck");
    }
    if ((int16_t)wof_m.ship_blocks_draw[4 * 0x20].v > 0 && !wof_g.view_shift)
        WOF_STANDIN("M6 STAND-IN: 0x0139D6, the japanese carrier's crane");
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
    if (wof_g.g_02536a != 0 && wof_g.draw_attitude == 0 && wof_g.view_step != 1)
        WOF_STANDIN("M5 STAND-IN: 0x010642, the guns' muzzle flash");
done:

    wof_g.clip_bottom = saved;
}

/* orig 0x010DA6 - the enemy aircraft: the words counted in 0x0251D8 and the four aircraft
 * records.  The five scripts brought none up (re/notes/objects.md), so only the walk is
 * here (M6). */
void wof_draw_enemy_aircraft(void)
{
    if (wof_g.g_0251d8 != 0)
        WOF_STANDIN("M6 STAND-IN: 0x010DBA, the formation words of 0x0251D8");
    for (int i = 0; i < 4; i++)
        if (wof_m.aircraft_records[i].w[0] != 0)
            WOF_STANDIN("M6 STAND-IN: 0x010E26, an enemy aircraft");
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
    targets_3(table);
    targets_f(table);
    ship_guns();
    airfields();
    ship_planes();
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

/* orig 0x010EE0 - the Smoke pool: every record in use drawn from MasterList (or AthList) at
 * its whole-pixel position, moved by its velocity, its timer counted and its kind counted
 * down (re/notes/objects.md).  Clipped at the carrier's waterline while 0x025394 is set. */
static void smoke(void)
{
    int16_t saved = wof_g.clip_bottom;

    if (wof_g.g_025394 != 0)
        wof_g.clip_bottom = (int16_t)(0x84 + wof_g.g_026e56 + carrier.row);
    for (int i = 0; i < 40; i++) {
        if (wof_m.smoke_records[i].kind != 0)
            WOF_STANDIN("M5 STAND-IN: 0x010F2A, a smoke record");
    }
    wof_g.clip_bottom = saved;
}

/* orig 0x013EEE - the soldiers (M5): the walk over soldier_count records, of which the
 * five scripts only ever met free ones. */
static void soldiers(void)
{
    for (uint16_t i = 0; i < wof_g.soldier_count && i < 160; i++)
        if (wof_m.soldier_records[i].state != 0)
            WOF_STANDIN("M5 STAND-IN: 0x013F0A, a soldier");
}

/* orig 0x0152F8 - the Splashes pool: twenty records of four bytes, each in use while its
 * count is non-zero, drawn from world_shapes (or eighth_shapes) and counted down. */
static void splashes(void)
{
    int table = wof_g.view_step == 8 ? T_WORLD : T_EIGHTH;

    for (int i = 0; i < 20; i++) {
        wof_splash_t *s = &wof_m.splash_records[i];
        int16_t       d2;

        if (s->count == 0)
            continue;
        if (s->kind == 2) {
            WOF_STANDIN("M5 STAND-IN: 0x015334, a splash of kind 2");
            continue;
        }
        d2 = (int16_t)(uint8_t)(0x67 + s->count);                 /* add.b */
        wof_draw_world_shape(table, d2, s->x, 0x0D);
        s->count--;
    }
}

/* orig 0x010702 - one object record's drawing: type 1 (a bomb) from torpedo_shapes by its
 * frame.  While its drawing kind is 8 it is going out: eight frames of the explosion from
 * world_shapes, counted in +0x21, and after the eighth the pass frees the record by
 * clearing its kind (re/notes/passes.md).  The five scripts drew objects only at full
 * scale and only of type 1. */
static void object_draw(wof_object_t *o)
{
    int     table = T_TORPEDO;
    int16_t d2;

    if (o->type != 1) {
        WOF_STANDIN("M5 STAND-IN: 0x010726, an object of another type");
        return;
    }
    d2 = 9;
    if (wof_g.view_step != 1)
        d2 = (int16_t)(uint8_t)(0x40 + o->frame);                 /* add.b */
    if (o->draw_kind == 8) {
        uint16_t d3 = (uint16_t)(o->b21 + 1u);

        table = T_WORLD;
        if (d3 == 8) {
            o->kind = 0;
            o->b21  = 0;
            return;
        }
        o->b21 = (uint8_t)d3;
        d2 = (int16_t)((o->b1f == 0 ? 0x65 : 0x59) + d3);
    }
    if (wof_g.view_step != 8) {
        WOF_STANDIN("M5 STAND-IN: 0x0107C2, an object in the eighth-scale view");
        return;
    }
    wof_draw_world_shape(table, d2, o->draw_x, o->draw_y);
}

/* orig 0x0106BE - the object records whose drawing kind is set, the extra one last. */
static void objects(void)
{
    if (wof_g.g_02536c)
        wof_g.g_02536c = 0;
    for (int i = 0; i < 15; i++)
        if (wof_m.object_records[i].draw_kind)
            object_draw(&wof_m.object_records[i]);
    if (wof_m.object_record_extra[0].draw_kind)
        object_draw(&wof_m.object_record_extra[0]);
}

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

/* orig 0x01557C - the Balloons pool, while 0x02535D is set at full scale (M5). */
static void balloons(void)
{
    if (wof_g.g_02535d && wof_g.view_step == 8)
        WOF_STANDIN("M5 STAND-IN: 0x015584, the balloons");
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
 * flash_colour on odd counts while flash_count runs, then the back view shown.  No script
 * provokes the flash; its branch is ported from reading. */
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
    smoke();
    soldiers();
    splashes();
    objects();
    weapon_marker();
    balloons();
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
