/* The logic tick (M4 part 2): logic_tick (orig 0x011386) and the hand-written routines it
 * calls, in the original's order (re/notes/objects.md, "The order of a tick").  The player's
 * own code is src/player.c; the helpers the world shares with the pass are here too.
 *
 * The tick can wait.  A lost aircraft's restart (0x0135CE into player_lost_restart) clears
 * the playfield, flips the buffers and spins on WaitTOF from inside the player update, so
 * the path from run_queued_ticks down to that wait is a chain of coroutines: logic_tick,
 * wof_player_update, the wait after a crash (0x01AF7C) and the restart.  Each WaitTOF is one
 * CO_WAIT, one VBlank, and the VBlanks the tick waited count toward the next pass as the
 * original's do (src/world.c, frame_update).
 *
 * What the scripts of part 2 never executed is a marked stand-in naming the milestone that
 * owes it (re/notes/porting-m4.md, "Appendix: the regions no run executed").  The sound
 * engine's routines keep nothing the port keeps except the two values 0x012132 eases, which
 * the dashboard's neighbours read; their slots are M8's (tests/m4complete.py). */
#include "wof.h"
#include "gen/tables.h"

#define P       (wof_m.player[0])
#define ABOARD  (wof_g.g_025394)

/* The ship records in the order the walks take them (ship_order, 0x02555A). */
static wof_ship_t *ship_in_order(int i)
{
    return &wof_m.ship_records[(wof_tbl_ship_order[i] - 0x025460u) / 0x1Eu];
}

/* ------------------------------------------------------------------ the map's helpers */

/* orig 0x0150C8 map_slot_at - the map record under a world x: its low bits, and its slot
 * (bits 2 to 10) through *slot; 0 and 0 left of the map and from map_extent on. */
uint16_t wof_map_slot_at(int16_t x, uint16_t *slot)
{
    uint16_t rec;

    if (x < 0 || (uint16_t)x >= wof_g.map_extent) {
        *slot = 0;
        return 0;
    }
    rec = wof_m.map_records[(int16_t)(uint16_t)(((uint16_t)x >> 3) << 1) >> 1].v;
    *slot = (uint16_t)((rec >> 2) & 0x1FFu);
    return (uint16_t)(rec & 3u);
}

/* orig 0x015714 ground_height - the height of the ground a map record stands for.  Land,
 * a bunker or a gun has its class's height from ground_class_heights (0x0257C2) less the
 * record's height bits (11 to 13); a ship's deck is its record's +0x0E less +0x14 less the
 * sea's swell 0x0253AE, and the carrier's also less 0x025396, the lift; anything else is 0. */
int16_t wof_ground_height(uint32_t at)
{
    uint16_t rec = (at >> 1) < 3576u ? wof_m.map_records[at >> 1].v : 0;
    uint16_t cls = (uint16_t)((rec >> 2) & 0x1FFu);
    int16_t  row;
    const wof_ship_t *ship;

    switch (cls) {
    case 0x06:                                 row = 0; break;
    case 0x07:                                 row = 1; break;
    case 0x08: case 0x0B:                      row = 2; break;
    case 0x03:                                 row = 3; break;
    case 0x04:                                 row = 4; break;
    default:
        if (cls >= 0x0F && cls <= 0x1E) {
            row = 5;
            break;
        }
        if (cls < 0x0F)
            return 0;
        switch (cls) {
        case 0xCC:
            ship = &wof_m.ship_records[2];                       /* 0x02549C */
            break;
        case 0xF1: case 0xF3: case 0xF2: case 0xF6:
            ship = &wof_m.ship_records[3];                       /* 0x0254BA */
            break;
        case 0x10C: case 0x10E: case 0x10D: case 0x10F: case 0x110:
            ship = &wof_m.ship_records[1];                       /* 0x02547E */
            break;
        case 0xE5: case 0xE6: case 0xE4: case 0xE7:
            ship = &wof_m.ship_records[0];                       /* 0x025460 */
            break;
        case 0x20: case 0x1F: case 0x21: case 0x26: case 0x23:
        case 0x22: case 0x24: case 0x25: case 0x9F: case 0x27:
            ship = &wof_m.ship_records[4];                       /* carrier_record */
            return (int16_t)(ship->w0e - ship->w14 - wof_g.g_0253ae - wof_g.g_025396);
        default:
            return 0;
        }
        return (int16_t)(ship->w0e - ship->w14 - wof_g.g_0253ae);
    }
    return (int16_t)((int16_t)wof_image16(0x0257C2u + 2u * (uint32_t)row) - (int16_t)((rec >> 11) & 7u));
}

/* ------------------------------------------------------------------ the pools' claims */

/* orig 0x010820 object_spawn - a free object record (+0x20 zero) for something left at a
 * map record: at the record's world x, 0x0C above `y`, kind 8, type 1; `flag` 0 marks it
 * (+0x1F 2) and makes the sound engine's noise (0x012324, M8).  With all fifteen in use
 * nothing happens. */
void wof_object_spawn(uint32_t at, int16_t y, int16_t flag)
{
    wof_object_t *o = 0;

    for (int i = 0; i < 15; i++) {
        if (wof_m.object_records[i].kind == 0) {
            o = &wof_m.object_records[i];
            break;
        }
    }
    if (!o)
        return;
    o->l12     = 0;
    o->speed_x = 0;
    o->w10     = 0;
    o->x       = (int16_t)(uint16_t)(at << 2);
    o->y       = (int16_t)(0x0C + y);
    o->frame   = 0;
    o->b1f     = 0;
    o->kind    = 8;
    o->b21     = 1;
    o->type    = 1;
    o->b1f     = 0;
    if (flag == 0)
        o->b1f = 2;
}

/* orig 0x0152B0 - a splash at world x: the first free record of the Splashes pool, with the
 * low bits of the map record under it and six frames to run. */
void wof_splash_spawn(int16_t x)
{
    for (int i = 0; i < 20; i++) {
        wof_splash_t *s = &wof_m.splash_records[i];
        uint16_t      slot;

        if (s->count)
            continue;
        s->x = x;
        s->kind = (uint8_t)wof_map_slot_at(x, &slot);
        if (s->kind == 2) {
            WOF_STANDIN("M5 STAND-IN: 0x0152D8, a splash on a record of low bits 2");
            return;
        }
        s->count = 6;
        return;
    }
}

/* orig 0x015460 smoke_claim - a puff of smoke: the first free record of the Smoke pool at
 * (x, y) in 16.16, y at least 16, drifting by two draws of rand_beam; with all forty in
 * use nothing happens. */
void wof_smoke_claim(int32_t x, int32_t y, int16_t kind)
{
    for (int i = 0; i < 40; i++) {
        wof_smoke_t *s = &wof_m.smoke_records[i];

        if (s->kind)
            continue;
        s->x = x;
        if (y < 0x100000) {
            WOF_STANDIN("M5 STAND-IN: 0x01548A, smoke below the ground's line");
            return;
        }
        s->y = y;
        s->kind = kind;
        s->timer = 6;
        s->dx = (int32_t)((wof_rand_beam(0x015460) & 0xFFFFu) + 0x10000u);
        s->dy = (int32_t)((wof_rand_beam(0x015460) & 0xFFFFu) + 0x10000u);
        return;
    }
}

/* ----------------------------------------------------------------- logic_tick's calls */

/* orig 0x0112B0 - the weapon menu in the hold, while 0x025364 is up and the mission not
 * won: the stick forward and back, or the cursor keys, step the weapon type round (with a
 * pause of two ticks between steps), the button or Return closes the menu and sends the
 * lift up (state 11, 0x025394 2). */
static void weapon_menu(void)
{
    uint16_t d0;

    if (!wof_g.g_025364 || wof_g.g_0253bc)
        return;
    d0 = wof_g.tick_input;
    if (d0 == 0) {
        uint16_t key = (uint16_t)wof_g.last_key;              /* 0x026F5E, its low word */

        if (key == 0x4D) d0 = 2;
        if (key == 0x4C) d0 = 1;
        if (key == 0x44) d0 = 0x10;
        if (key == 0x43) d0 = 0x10;
    }
    if (d0 == 0)
        return;
    if (d0 & 0x30u) {
        wof_g.g_025364 = 0;
        P.on_deck = 0x0B;
        ABOARD = 2;
        return;
    }
    if ((int8_t)wof_g.g_02536e > 0) {
        wof_g.g_02536e--;
        return;
    }
    if (!(d0 & 3u))
        return;
    wof_g.g_02536e = 2;
    if (!(d0 & 1u)) {
        wof_g.weapon_type++;
        if (wof_g.weapon_type == 3)
            wof_g.weapon_type = 0;
    } else {
        wof_g.weapon_type--;
        if (wof_g.weapon_type == -1)
            wof_g.weapon_type = 2;
    }
    if (wof_g.weapon_count != 0xFF)
        wof_g.weapon_count = wof_tbl_weapons_per_type[(uint16_t)wof_g.weapon_type];
    wof_weapon_gauge_reset();
}

/* orig 0x011460 - the lift, once per pass: going up (0x025394 2) it rises a step a pass
 * until 0x025396 is 0 and the engine idles on the deck; going down (3) it sinks to 0x20 and
 * the aircraft is reset in the hold.  The two sounds on the way (0x011F4E, 0x012354) are
 * the sound engine's slots, M8's. */
static void lift(void)
{
    if (wof_g.pass_counter == (uint16_t)wof_g.g_027352)
        return;
    wof_g.g_027352 = (int16_t)wof_g.pass_counter;
    if (ABOARD == 0)
        return;
    if (ABOARD == 2) {
        if (--wof_g.g_025396 != 0)
            return;
        ABOARD = 0;
        wof_engine_idle();                                    /* 0x01B9CC */
        return;
    }
    if (ABOARD == 3) {
        if (++wof_g.g_025396 != 0x20)
            return;
        wof_player_restart_state();
    }
}

/* orig 0x01E7D6 - the enemy aircraft, every live record (M6). */
static void enemy_aircraft(void)
{
    wof_g.g_027e66 = 0;
    for (int i = 0; i < 4; i++)
        if (wof_m.aircraft_records[i].w[0] != 0)
            WOF_STANDIN("M6 STAND-IN: 0x01E7FC, an enemy aircraft");
}

/* orig 0x012132 - the engine's sound, as far as the port keeps it: the volume 0x02542C eases
 * towards 0x025428 by one up and two down, and while it is not zero the pitch 0x02542E
 * towards what pitch_target, 0x02542A and the height ask for, by twenty up and ten down.
 * The comparisons are unsigned, as the original's.  Everything else it writes is the sound
 * engine's slots (M8).  Nothing moves while paused or with the music off. */
static void engine_sound(void)
{
    uint16_t d0, d1;

    if (wof_g.pause_flag || wof_g.opt_music_off)
        return;
    d0 = (uint16_t)wof_g.g_02542c;
    d1 = (uint16_t)wof_g.g_025428;
    if (d1 != d0) {
        if (d1 > d0) {
            d0++;
        } else {
            d0 = (uint16_t)(d0 - 2);
            if (!(d1 <= d0))
                d0 = d1;
        }
    }
    wof_g.g_02542c = (int16_t)d0;
    if (d0 == 0)
        return;
    d0 = (uint16_t)wof_g.g_02542e;
    d1 = (uint16_t)((int16_t)(wof_g.pitch_target >> 7) + wof_g.g_02542a + (int16_t)(P.y >> 4));
    if (d1 != d0) {
        if (d1 > d0) {
            d0 = (uint16_t)(d0 + 0x14);
            if (!(d1 > d0))
                d0 = d1;
        } else {
            d0 = (uint16_t)(d0 - 0x0A);
            if (!(d1 <= d0))
                d0 = d1;
        }
    }
    wof_g.g_02542e = (int16_t)d0;
}

/* orig 0x011274 - the player's speeds and position as four 16.16 longs from 0x026E62, and
 * the pitch as a bearing (0x025404), for what the aircraft shoots or drops next. */
static void shot_origin(void)
{
    wof_g.g_026e62 = P.speed_y;
    wof_g.g_026e64 = 0;
    wof_g.g_026e66 = P.speed_x;
    wof_g.g_026e68 = 0;
    wof_g.g_026e6a = P.x;
    wof_g.g_026e6c = 0;
    wof_g.g_026e6e = P.y;
    wof_g.g_026e70 = 0;
    wof_g.g_025404 = (int16_t)(((int32_t)(int16_t)(wof_g.pitch_angle + wof_g.pitch_angle) * 0x200) / 0x4650);
}

/* orig 0x011BFC - smoke from a damaged engine, every second tick in the air: the oil below
 * 0x80 decides how often (M6 brings the damage). */
static void engine_smoke(void)
{
    if (!wof_g.g_027346 || P.on_deck == 6 || P.on_deck == 8)
        return;
    if ((uint16_t)(0x80 - P.oil) != 0)
        WOF_STANDIN("M6 STAND-IN: 0x011C24, smoke from a damaged engine");
}

/* orig 0x010AA6 - one object record: a record of kind 8 lies where it was left; the others
 * are weapons and shots in flight (M5). */
static void object_step(wof_object_t *o)
{
    if (o->kind == 8)
        return;
    WOF_STANDIN("M5 STAND-IN: 0x010AB6-0x010DA5, a weapon or a shot in flight");
}

/* orig 0x010A72 - the object records: 0x010AA6 for every one in use, then the extra one. */
static void objects(void)
{
    for (int i = 0; i < 15; i++)
        if (wof_m.object_records[i].kind)
            object_step(&wof_m.object_records[i]);
    wof_g.frame_drawn = 0;
    if (wof_m.object_record_extra[0].kind)
        object_step(&wof_m.object_record_extra[0]);
}

/* orig 0x0119BC - the guns' bullets in the water (M5). */
static void gun_splashes(void)
{
    if (wof_g.g_02536a)
        WOF_STANDIN("M5 STAND-IN: 0x0119C4, the guns' bullets in the water");
}

/* orig 0x011622 - the enemy's airfields: an aircraft taking off, and the player near one
 * sending the next up (M6). */
static void airfields(void)
{
    for (int i = 0; i < 4; i++) {
        if (wof_m.airfield_records[i].w[4] != 0) {
            WOF_STANDIN("M6 STAND-IN: 0x011630, an enemy aircraft taking off");
            return;
        }
    }
    if (wof_g.g_027348)
        return;
    for (int i = 0; i < 4; i++) {
        const wof_airfield_t *a = &wof_m.airfield_records[i];

        if (wof_g.g_026e6a < (int16_t)(a->w[0] - 0x1E0))
            continue;
        if (wof_g.g_026e6a > (int16_t)(a->w[1] + 0x1E0))
            continue;
        WOF_STANDIN("M6 STAND-IN: 0x0116BE, the player near an enemy airfield");
        return;
    }
}

/* orig 0x011510 - the Japanese carrier's aircraft and the ships' launches (M6).  The
 * carrier's block (0x025196) holds a count and entries of eight bytes; the last entry's
 * first word above 0 is an aircraft to launch. */
static void ship_launches(void)
{
    uint16_t count = wof_m.ship_blocks[0x80].v;

    if (count != 0) {
        uint32_t last = 0x80u + 4u * (uint32_t)count;     /* 8 bytes in, (count - 1) * 8 on */

        if (last < 160u && (int16_t)wof_m.ship_blocks[last].v > 0)
            WOF_STANDIN("M6 STAND-IN: 0x01152A, the Japanese carrier's aircraft");
    }
    if (wof_g.g_027348)
        return;
    /* 0x011574: each ship in ship_order beside the block of the same place from 0x025096:
     * a ship afloat that has aircraft (+0x12) and is not sunk (+0x0C), the player within its
     * block's span, 0x0251D6 below its limit and an aircraft left launches one. */
    for (int i = 0; i < 5; i++) {
        const wof_ship_t *s = ship_in_order(i);
        const wof_word_t *blk = &wof_m.ship_blocks[0x20 * i];

        if (s->present == 0 || s->w12 == 0 || s->w0c <= 0)
            continue;
        if (wof_g.g_026e6a < (int16_t)blk[2].v || wof_g.g_026e6a > (int16_t)blk[3].v)
            continue;
        if (wof_g.g_0251d6 >= (int16_t)blk[1].v || blk[0].v == 0)
            continue;
        if (i == 4)
            WOF_STANDIN("M6 STAND-IN: 0x0115F4-0x011621, the last ship's aircraft readied");
        else
            WOF_STANDIN("M6 STAND-IN: 0x0115C4-0x0115E9, a ship launching an aircraft");
        return;
    }
}

/* orig 0x011CAE - a ship afloat whose +0x0C has run out sinks (0x011CD8, M6). */
static void ships_sinking(void)
{
    for (int i = 0; i < 5; i++) {
        const wof_ship_t *s = ship_in_order(i);

        if (s->present != 0 && s->w0c == 0)
            WOF_STANDIN("M6 STAND-IN: 0x011CCA, a ship sinking (0x011CD8)");
    }
}

/* orig 0x011DE4 - the timers of the slot-3 and slot-4 targets (+0x0B), which fire (M5). */
static void target_timers(void)
{
    for (int i = 0; i < wof_g.target_count_3; i++)
        if (wof_m.target_records_3[i].w0a & 0xFF)
            WOF_STANDIN("M5 STAND-IN: 0x011DFE, a slot-3 target's timer");
    for (int i = 0; i < wof_g.target_count_4; i++)
        if (wof_m.target_records_4[i].w0a & 0xFF)
            WOF_STANDIN("M5 STAND-IN: 0x011E48, a slot-4 target's timer");
}

/* orig 0x011C5E - the balloons (M5). */
static void balloons(void)
{
    if (wof_g.g_02535d)
        WOF_STANDIN("M5 STAND-IN: 0x011C66, the balloons");
}

/* ------------------------------------------------------------------------ logic_tick */

/* orig 0x011386 logic_tick - one tick: nothing while paused; in the air the oil and the
 * fuel timers; the swell's cycle (0x0253AC, 0x0253AE); the input byte; the weapon menu and
 * the lift while 0x026D3E has run down; then the player, the enemy aircraft, the engine's
 * sound, the guns, the shot origin, the engine's smoke, the objects, the guns' splashes,
 * 0x027348, the airfields, the ships' launches, the ships sinking, the targets' timers and
 * the balloons.  The player update can wait (a lost aircraft's restart). */
wof_co_t wof_logic_tick(void)
{
    wof_ctx_t *c = &wof_f.co_tick;

    CO_BEGIN(c);
    wof_f.ticks_run++;
    if (!wof_g.pause_flag) {
        if (P.on_deck == 0) {
            if (P.oil != 0x80)
                WOF_STANDIN("M6 STAND-IN: 0x0113A2, the oil leaking from a damaged engine");
            if (--wof_g.g_02734e <= 0) {
                P.fuel--;
                wof_g.g_02734e = wof_g.g_027168;
            }
        }
        wof_g.g_027346 = (int16_t)((wof_g.g_027346 + 1) & 1);
        if (--wof_g.g_0253ac < 0) {
            uint16_t d0;

            wof_g.g_0253ac = wof_g.g_0253e8;
            d0 = (uint16_t)((wof_g.g_02476a + 1) & 7);
            wof_g.g_02476a = (int16_t)d0;
            wof_g.g_0253ae = (int16_t)(wof_tbl_data_image[0x024C44u - 0x023000u + d0] + 1);
        }
        wof_g.tick_input = wof_input_queue_pop();
        if (wof_g.g_026d3e == 0 || --wof_g.g_026d3e <= 0) {
            weapon_menu();
            lift();
        }
        CO_CALL(c, &wof_f.co_player, wof_player_update());
        enemy_aircraft();
        engine_sound();
        wof_guns();
        /* 0x012066: the sound engine's slots (M8) */
        shot_origin();
        engine_smoke();
        objects();
        gun_splashes();
        if (--wof_g.g_027348 < 0)
            wof_g.g_027348 = 0;
        airfields();
        ship_launches();
        ships_sinking();
        target_timers();
        balloons();
    }
    wof_trace_add("tick", (int32_t)wof_f.ticks_run, 0, 0, 0, 0, 0);
    wof_test_tick_end(wof_f.ticks_run - 1u);
    CO_END(c);
}
