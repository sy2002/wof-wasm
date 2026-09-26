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
#define SHIP_JAPCARRIER 3

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

/* ------------------------------------------------------------------ the angles */

/* orig 0x015108 - the sine of an angle in 0x400 steps a turn, from the quarter wave of 0x101
 * words at 0x02496C (0 to 0x7FFF), mirrored and negated for the other quarters. */
int16_t wof_sine(int16_t angle)
{
    uint16_t d0 = (uint16_t)angle & 0x3FFu;

    if (d0 < 0x100)
        return (int16_t)wof_image16(0x02496Cu + 2u * d0);
    if (d0 < 0x200)
        return (int16_t)wof_image16(0x02496Cu + 2u * (uint32_t)(uint16_t)(0x200u - d0));
    d0 = (uint16_t)(d0 - 0x200u);
    if (d0 >= 0x100)
        d0 = (uint16_t)(0x200u - d0);
    return (int16_t)-(int16_t)wof_image16(0x02496Cu + 2u * d0);
}

/* orig 0x015104 - the cosine: the sine a quarter turn on. */
int16_t wof_cosine(int16_t angle)
{
    return wof_sine((int16_t)(angle + 0x100));
}

/* orig 0x01514C - the tangent of the low byte of an angle's size, from the 0x100 words at
 * 0x02476C, with the angle's sign. */
int16_t wof_tangent(int16_t angle)
{
    uint16_t d0 = (uint16_t)(angle < 0 ? -angle : angle) & 0xFFu;
    int16_t  v  = (int16_t)wof_image16(0x02476Cu + 2u * d0);

    return angle < 0 ? (int16_t)-v : v;
}

/* orig 0x015CA6 - the angle of the vector (x, y) in 0x400 steps a turn: the smaller of the
 * two sizes over the larger, as a 16-bit fraction by divu, rounded to 8 bits, looked up in
 * the arctangent bytes at 0x0257EE (0 to 0x80), and placed in its octant by the signs and
 * the exchange (the jump table at 0x0257CE: 0x015D12, 0x015D0C, 0x015D1E, 0x015D18,
 * 0x015D26, 0x015D2A, 0x015D38, 0x015D30).  The dividend's low word is the upper word D1
 * held beside y (`swap`), which the caller says: `high`. */
int16_t wof_bearing_of(int16_t x, int16_t y, uint16_t high)
{
    uint32_t d1 = ((uint32_t)high << 16) | (uint16_t)y;
    uint32_t d2 = (uint16_t)x;
    uint16_t d4 = 0;
    int16_t  d0 = 0;

    if ((int16_t)(uint16_t)d1 < 0) {
        d4 |= 0x10u;
        d1 = (d1 & 0xFFFF0000u) | (uint16_t)-(int16_t)(uint16_t)d1;
    }
    if ((int16_t)(uint16_t)d2 < 0) {
        d4 |= 0x08u;
        d2 = (uint16_t)-(int16_t)(uint16_t)d2;
    }
    if ((int16_t)(uint16_t)d1 == (int16_t)(uint16_t)d2) {
        if ((uint16_t)d1 == 0)
            return 0;
        d0 = 0x80;
    } else {
        uint32_t q;
        uint16_t w;

        if ((int16_t)(uint16_t)d1 > (int16_t)(uint16_t)d2) {
            uint32_t tmp = d1;                                     /* exg.l */

            d1 = d2;
            d2 = tmp;
            d4 |= 0x04u;
        }
        d1 = (d1 << 16) | (d1 >> 16);                             /* swap */
        if ((uint16_t)d2 == 0)
            return 0;                        /* y of -0x8000 over a zero x: a trap on a 68000 */
        q = d1 / (uint16_t)d2;
        w = q > 0xFFFFu ? (uint16_t)d1 : (uint16_t)q;             /* divu.w; V leaves D1 */
        w = (uint16_t)((w >> 8) + ((w >> 7) & 1u));               /* lsr.w #8, addx */
        d0 = (int16_t)wof_image8(0x0257EEu + w);
    }
    switch (d4) {
    case 0x00: return d0;
    case 0x04: return (int16_t)(0x100 - d0);
    case 0x08: return (int16_t)(0x200 - d0);
    case 0x0C: return (int16_t)(d0 + 0x100);
    case 0x10: return (int16_t)-d0;
    case 0x14: return (int16_t)(d0 - 0x100);
    case 0x18: return (int16_t)(d0 - 0x200);
    default:   return (int16_t)-(int16_t)(d0 + 0x100);
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

/* orig 0x011BFC - smoke from a damaged engine, every second tick in the air: always once the
 * oil is more than 0x13 below full, and below that by chance, a bit of the table at 0x0255CA
 * (by how much oil is gone) against a draw of rand_beam.  smoke_at_player's D2 comes with an
 * upper word of 0 (observed at every call). */
static void engine_smoke(void)
{
    uint16_t d0;

    if (!wof_g.g_027346 || P.on_deck == 6 || P.on_deck == 8)
        return;
    d0 = (uint16_t)(0x80 - P.oil);
    if (d0 == 0)
        return;
    if (d0 <= 0x13) {
        uint16_t d1;

        d0 = (uint16_t)((uint16_t)(d0 << 3) & 0xF0u);
        d0 = (uint16_t)(((uint16_t)wof_rand_beam(0x011BFC) & 0x0Fu) + d0);
        d1 = d0;
        d0 = (uint16_t)(d0 >> 3);
        if (!(wof_image8(0x0255CAu + d0) & (1u << (d1 & 7u))))       /* btst.l on memory: a byte */
            return;
    }
    wof_smoke_at_player(5, 0);
}

/* orig 0x0119BC - the guns' bullets: while they fire, the aircraft sinks (0x026E62 below 0)
 * below y 0xA0 and is not stalling, the first free record of the Splashes pool takes the
 * ground the bullets reach (0x011A46): the soldiers within 0x10 of it start dying and a
 * splash, or the dust on land, is made there. */
static void gun_splashes(void)
{
    if (!wof_g.g_02536a || wof_g.g_026e62 >= 0 || P.y >= 0xA0 || wof_g.landing_stall)
        return;
    for (int i = 0; i < 20; i++) {
        wof_splash_t *s = &wof_m.splash_records[i];
        int16_t       x;
        uint16_t      slot;

        if (s->count)
            continue;
        x = wof_guns_ground_x(wof_g.g_025404);
        wof_soldiers_hit(x, 0x10);
        s->x = x;
        wof_splash_spawn(x);
        s->kind = (uint8_t)wof_map_slot_at(x, &slot);
        return;
    }
}

/* orig 0x011A46 guns_ground_x - where a shot along a bearing below the level (D0 negative)
 * reaches the ground: the height (the long at 0x026E6E / 0x100) over the tangent of the
 * bearing (0x01514C), by divu, ahead of the drawing's x; 0 for a bearing of 0 or up.  On a
 * quotient above 0xFFFF divu leaves the dividend, whose low word is taken then. */
int16_t wof_guns_ground_x(int16_t d0)
{
    uint32_t d1;
    uint16_t t;
    int16_t  w;

    if (d0 >= 0)
        return 0;
    if ((uint16_t)d0 == 0xFF01u)
        d0++;
    d1 = (uint32_t)((int32_t)(((uint32_t)(uint16_t)wof_g.g_026e6e << 16) | (uint16_t)wof_g.g_026e70) >> 8);
    t = (uint16_t)wof_tangent((int16_t)-d0);
    if (t != 0 && d1 / t <= 0xFFFFu)
        d1 = ((d1 % t) << 16) | (d1 / t);
    w = (int16_t)(uint16_t)d1;
    if (P.facing >= 0)
        w = (int16_t)-w;
    return (int16_t)(wof_g.draw_player_x - w);
}

/* The arithmetic 0x0123AC (a soldier's scream, M8) does through 0x012306 and 0x0122F6 on
 * D0 and D1 and leaves in them: the loudness by the distance from the aircraft, halved, and
 * the height's distance from 0x14. */
static void scream_registers(uint16_t *d0, uint16_t *d1)
{
    uint16_t a = (uint16_t)(*d0 - (uint16_t)P.x);
    uint16_t b = (uint16_t)(0x14u - (uint16_t)P.y);

    if ((int16_t)a < 0)
        a = (uint16_t)-(int16_t)a;
    if ((int16_t)b < 0)
        b = (uint16_t)-(int16_t)b;
    a = (uint16_t)((uint16_t)(a + b) >> 5);
    a = a > 0x40 ? 0 : (uint16_t)(0x40u - a);
    *d0 = (uint16_t)(a >> 1);
    *d1 = b;
}

/* orig 0x011A8C soldiers_hit - the running soldiers from x - w to x + w start dying (state 2,
 * frame 5, timer 2) with a scream; then 0x011AE2 over the same span.  The scream's sound
 * code (0x0123AC) leaves its own values in D0 and D1 and the walk goes on with them, so after
 * the first soldier hit the span is the scream's (scream_registers). */
void wof_soldiers_hit(int16_t x, int16_t w)
{
    uint16_t d0 = (uint16_t)(x - w);
    uint16_t d1 = (uint16_t)(w + w);

    for (uint16_t n = 0; n < wof_g.soldier_count && n < 160; n++) {
        wof_soldier_t *s = &wof_m.soldier_records[n];

        if (s->state != 1)
            continue;
        if ((uint16_t)(s->x - d0) > d1)
            continue;
        s->state = 2;
        s->frame = 5;
        s->timer = 2;
        scream_registers(&d0, &d1);
    }
    wof_torpedoes_hit(d0, d1);
}

/* orig 0x011AE2 torpedoes_hit - a torpedo in the water (drawn, type 2) whose drawing x is
 * within D1 of D0 goes out (kind 8); the extra record whatever its type. */
void wof_torpedoes_hit(uint16_t d0, uint16_t d1)
{
    for (int i = 0; i < 16; i++) {
        wof_object_t *o = i < 15 ? &wof_m.object_records[i] : &wof_m.object_record_extra[0];
        uint16_t      d2;

        if (o->draw_kind == 0 || (i < 15 && o->type != 2))
            continue;
        d2 = (uint16_t)(o->draw_x - d0);
        if ((int16_t)d2 < 0)
            d2 = (uint16_t)-(int16_t)d2;
        if (d2 > d1)
            continue;
        o->kind = 8;
        o->b21 = 1;
    }
}

/* orig 0x011622 - the enemy's airfields (airfield_records, 0x0252FA: the span +0x00 to
 * +0x02, the most up +0x04, the aircraft parked +0x06, the one rolling at x +0x08 with its
 * speed +0x0C, the end it takes off from +0x0E, -1 the west).  The first airfield with an
 * aircraft rolling moves it by a pixel for every eight of its speed, which grows by one a
 * tick up to 0x38, and at the far end it takes off as a fighter at height 0; that is all
 * the tick does then.  Else, out of the cooldown (launch_cooldown), every airfield whose
 * span the player is within 0x1E0 of rolls its next aircraft out from its end, 0x40 apart
 * by the aircraft left, and starts the cooldown at 100; one with fighters_up at its most
 * or none parked ends the walk. */
static void airfields(void)
{
    for (int i = 0; i < 4; i++) {
        wof_airfield_t *a = &wof_m.airfield_records[i];
        int16_t         d0;

        if (a->w[4] == 0)
            continue;
        d0 = (int16_t)(a->w[6] + 1);
        if (d0 > 0x38)
            d0 = 0x38;
        a->w[6] = d0;
        d0 = (int16_t)((uint16_t)d0 >> 3);
        if (a->w[7] != -1) {
            a->w[4] = (int16_t)(a->w[4] + d0);
            if (a->w[4] <= a->w[1])
                return;
        } else {
            a->w[4] = (int16_t)(a->w[4] - d0);
            if (a->w[4] >= a->w[0])
                return;
        }
        wof_aircraft_launch(0, a->w[4], 0, a->w[7]);
        a->w[4] = 0;
        return;
    }
    if (wof_g.launch_cooldown)
        return;
    for (int i = 0; i < 4; i++) {
        wof_airfield_t *a = &wof_m.airfield_records[i];
        int16_t         d1, d0;

        if (wof_g.g_026e6a < (int16_t)(a->w[0] - 0x1E0))
            continue;
        if (wof_g.g_026e6a > (int16_t)(a->w[1] + 0x1E0))
            continue;
        if (wof_g.fighters_up >= a->w[2] || a->w[3] <= 0)
            return;                                              /* 0x0116BE, 0x0116CA */
        a->w[3]--;
        wof_g.launch_cooldown = 100;
        d1 = (int16_t)((uint16_t)a->w[3] << 6);
        d0 = (int16_t)((int16_t)(a->w[1] - 0x20) - d1);
        if (a->w[7] != -1)
            d0 = (int16_t)((int16_t)(a->w[0] + 0x20) + d1);
        a->w[4] = d0;
        a->w[6] = 0;
    }
}

/* orig 0x011510 - the Japanese carrier's aircraft and the ships' launches.  A ship block
 * (0x025096, 0x40 bytes a ship in the order of ship_order) holds its count, the most up, the
 * span of the player's x it launches in, and entries of eight bytes from +8: a flag, x and
 * height.  The Japanese carrier's last entry, once readied (its flag above 0), rolls west
 * at japcarrier_roll sixteenths of a pixel a tick, 8 more each tick less a sixteenth of
 * itself, and takes off as a fighter facing west past the ship's west end.  Out of the
 * cooldown, every ship afloat with a score (not the carrier), hits left, the player in its
 * span, fewer fighters up than its most and an aircraft left sends up its last entry facing
 * west and starts the cooldown; the Japanese carrier, last of the order, readies it on its
 * deck instead, 0x17C past its west end at height 0x21, and ends the walk. */
static void ship_launches(void)
{
    uint16_t count = wof_m.ship_blocks[0x80].v;

    if (count != 0) {
        uint32_t    last = 0x80u + 4u + 4u * (uint32_t)(uint16_t)(count - 1u);
        wof_word_t *e = &wof_m.ship_blocks[last < 157u ? last : 156u];

        if (last < 157u && (int16_t)e[0].v > 0) {
            uint16_t d1 = (uint16_t)wof_g.japcarrier_roll;
            int16_t  d7;

            d1 = (uint16_t)(d1 + 8u - (uint16_t)(d1 >> 4));
            wof_g.japcarrier_roll = (int16_t)d1;
            e[1].v = (uint16_t)((int16_t)e[1].v - (int16_t)(d1 >> 4));
            d7 = (int16_t)(wof_m.ship_records[SHIP_JAPCARRIER].span0 << 2);
            if (d7 > (int16_t)e[1].v) {
                wof_m.ship_blocks[0x80].v--;
                wof_aircraft_launch(0, (int16_t)e[1].v, (int16_t)e[2].v, -1);
            }
        }
    }
    if (wof_g.launch_cooldown)
        return;
    for (int i = 0; i < 5; i++) {
        const wof_ship_t *s = ship_in_order(i);
        wof_word_t       *blk = &wof_m.ship_blocks[0x20 * i];
        uint32_t          at;

        if (s->present == 0 || s->w12 == 0 || s->w0c <= 0)
            continue;
        if (wof_g.g_026e6a < (int16_t)blk[2].v || wof_g.g_026e6a > (int16_t)blk[3].v)
            continue;
        if (wof_g.fighters_up >= (int16_t)blk[1].v || blk[0].v == 0)
            continue;
        if (i == 4) {                                            /* 0x0115F4 */
            at = 4u + 4u * (uint32_t)(uint16_t)(blk[0].v - 1u);
            if (0x20u * (uint32_t)i + at + 2u < 160u) {
                blk[at].v = 1;
                blk[at + 1].v = (uint16_t)((int16_t)(s->span0 << 2) + 0x17C);
                blk[at + 2].v = 0x21;
            }
            wof_g.japcarrier_roll = 0;
            wof_g.launch_cooldown = 100;
            return;
        }
        blk[0].v--;
        at = 4u + 4u * (uint32_t)blk[0].v;
        if (0x20u * (uint32_t)i + at + 2u < 160u)
            wof_aircraft_launch(0, (int16_t)blk[at + 1].v, (int16_t)blk[at + 2].v, -1);
        wof_g.launch_cooldown = 100;
    }
}

/* orig 0x011CD8 ship_sinking - a ship afloat whose hits (+0x0C) are gone: every +0x16 ticks
 * a row deeper (+0x14), the interval +0x18 one shorter each time.  The carrier (no score,
 * +0x12) puts the player back on the lift while he is aboard (0x025394 1) at every row, and
 * at 0x21 rows with him on the deck he goes into the sea: no life left, the game-over count
 * at 100.  An enemy ship scores at ten rows, the ticker says so (0x015640), one ship fewer
 * is left, and with none and no island left the mission is won.  At 0x78 rows a ship's map
 * records are cleared: the carrier is gone (+0x04 0, 0x0255C1 set), an enemy ship's hits
 * become -1 and briefing_number_2 one less.  The first test after the row's step is of the
 * score: the move.w of +0x12 sets the flags the beq reads, not the cmpi before it. */
static void ship_sinking(wof_ship_t *s)
{
    if (--s->w16 > 0)
        return;
    s->w14++;
    s->w16 = s->w18;
    if (s->w18 != 0)
        s->w18--;
    if (s->w12 == 0) {
        if (ABOARD == 1) {
            P.on_deck = 0x0B;
            ABOARD = 2;
            wof_g.g_025364 = 0;
            wof_g.attitude_index = 0;
        }
    } else if (s->w14 == 10) {
        wof_g.player_score += (uint32_t)(int32_t)s->w12;
        wof_ship_sunk_message(s);
        /* subq.b #1 then bgt: the signed result before its byte wraps, so 0x80 is not > 0 */
        if ((int8_t)wof_g.ships_left-- > 1 || wof_g.islands_left != 0) {
            if (wof_g.ticker_message == 0)                    /* 0x01555A: ticker_text */
                wof_g.ticker_message = 0x02716Au;
            return;
        }
        wof_mission_won();
        return;
    }
    if (s->w12 != 0) {
        if (s->w14 < 0x78)
            return;
        wof_g.briefing_number_2--;
        s->w0c = -1;
    } else {
        if (s->w14 < 0x21)
            return;
        if (s->w14 == 0x21 && P.on_deck == 1) {
            P.on_deck = 6;
            P.y = 0;
            wof_g.lives = 0;
            wof_g.g_025364 = 0;
            wof_g.game_over_count = 100;
        }
        if (s->w14 < 0x78)
            return;
        s->present = 0;
        wof_g.g_0255c1 = 0xFF;
    }
    /* 0x011DC2: the words of its map records from +0x00 to +0x02, bytes of the list */
    {
        uint16_t n = (uint16_t)((uint16_t)(s->span1 - s->span0) >> 1);
        int32_t  w = (int32_t)(int16_t)s->span0 >> 1;

        for (int32_t k = 0; k <= (int32_t)n; k++)
            if (w + k >= 0 && w + k < 3576)
                wof_m.map_records[w + k].v = 0;
    }
}

/* orig 0x011CAE - every ship afloat whose hits have run out sinks a step. */
static void ships_sinking(void)
{
    for (int i = 0; i < 5; i++) {
        wof_ship_t *s = ship_in_order(i);

        if (s->present != 0 && s->w0c == 0)
            ship_sinking(s);
    }
}

/* orig 0x011DE4 target_timers - the slot-3 and slot-4 targets that let their soldiers out
 * (+0x0A of them, one each time the timer +0x0B runs out, through 0x011E82 in mode 2 for a
 * dug-out and 1 for a barracks): the timer starts again from bits 4 to 8 of vblank_total,
 * 3 in place of 0, until the count is spent. */
static void target_timers(void)
{
    for (int k = 0; k < 2; k++) {
        wof_gtarget_t *list  = k == 0 ? wof_m.target_records_3 : wof_m.target_records_4;
        uint8_t        count = k == 0 ? wof_g.target_count_3 : wof_g.target_count_4;

        for (uint16_t i = 0; i < count && i < 16; i++) {
            wof_gtarget_t *t = &list[i];
            uint8_t        timer = (uint8_t)t->w0a;                        /* +0x0B */
            uint16_t       d0;

            if (timer == 0)
                continue;
            t->w0a = (int16_t)(((uint16_t)t->w0a & 0xFF00u) | (uint8_t)--timer);
            if (timer != 0)
                continue;
            wof_soldier_out(t, (uint8_t)(k == 0 ? 2 : 1), 0);
            t->w0a = (int16_t)(uint16_t)((uint16_t)t->w0a - 0x100u);          /* +0x0A */
            if (((uint16_t)t->w0a >> 8) == 0)
                continue;
            d0 = (uint16_t)((uint16_t)((uint16_t)wof_g.vblank_total >> 4) & 0x1Fu);
            if (d0 == 0)
                d0 = 3;
            t->w0a = (int16_t)(((uint16_t)t->w0a & 0xFF00u) | (uint8_t)d0);
        }
    }
}

/* orig 0x011C5E balloons_step - while balloons_on is set, every balloon in use drifts by its
 * speeds and is free once its height reaches 0xAA. */
static void balloons(void)
{
    if (!wof_g.balloons_on)
        return;
    for (int i = 0; i < 20; i++) {
        wof_balloon_t *b = &wof_m.balloon_records[i];

        if (!b->in_use)
            continue;
        b->x = (int32_t)((uint32_t)b->x + (uint32_t)b->dx);
        b->y = (int32_t)((uint32_t)b->y + (uint32_t)b->dy);
        if ((int16_t)(uint16_t)((uint32_t)b->y >> 16) >= 0xAA)
            b->in_use = 0;
    }
}

#ifdef WOF_TRACE
/* The oracle tests' entry to the tick's own routines (tests/test_oracle_m5.py). */
int32_t wof_test_tick_part(uint32_t orig)
{
    switch (orig) {
    case 0x0119BC: gun_splashes();  return 0;
    case 0x011BFC: engine_smoke();  return 0;
    case 0x011DE4: target_timers(); return 0;
    case 0x011C5E: balloons();      return 0;
    case 0x011622: airfields();     return 0;
    case 0x011510: ship_launches(); return 0;
    case 0x011CAE: ships_sinking(); return 0;
    default:       return -1000;
    }
}
#endif

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
            if (P.oil != 0x80 && --wof_g.g_027350 <= 0) {         /* 0x0113A2: the oil leaks */
                wof_g.g_027350 = 0x50;
                P.oil--;
            }
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
        wof_enemy_aircraft_step();                             /* src/enemy.c */
        engine_sound();
        wof_guns();
        /* 0x012066: the sound engine's slots (M8) */
        shot_origin();
        engine_smoke();
        wof_objects_step(0);        /* D4's upper word is 0 there (observed at every tick) */
        gun_splashes();
        if (--wof_g.launch_cooldown < 0)
            wof_g.launch_cooldown = 0;
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
