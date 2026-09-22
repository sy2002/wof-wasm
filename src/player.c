/* The player's aircraft in the tick (M4 part 2): the C routines of the original from
 * 0x01AA6E to 0x01CB74, in address order.  logic_tick (src/tick.c) calls 0x01C660 once per
 * tick; everything here hangs off it.  The record is wof_m.player[0] (0x025078, the one
 * player_record always points at); g_027df4 always points at player_start_x, so what the
 * original reads at +2 of it is g_025394, the word behind (re/notes/porting-m4.md).
 *
 * The original is Aztec C with 16-bit int; every width change of the listing is kept.  The
 * map is addressed by byte offsets into wof_m.map_records as in src/world.c.  Regions no
 * script executes are marked stand-ins, as elsewhere. */
#include "wof.h"
#include "ffp.h"
#include "gen/tables.h"

#define P       (wof_m.player[0])
#define carrier (wof_m.ship_records[4])

/* The word behind player_start_x, read through g_027df4 + 2. */
#define ABOARD  (wof_g.g_025394)

/* A word or a long of the DATA hunk, by its original address: the tables of frames,
 * heights and offsets the player's code indexes (re/tables.toml, data_image).  An index the
 * original lets run past a table reads whatever lies behind it, which can be a global the
 * game changes (0x025E3E at attitude 9 is 0x025E50), so a byte a registered global covers is
 * read from the global and only the others from the executable's constant image. */
static uint8_t data_byte(uint32_t addr)
{
    uint8_t  b;
    uint32_t at = addr - 0x023000u;

    if (wof_global_byte(addr, &b))
        return b;
    return at < sizeof wof_tbl_data_image ? wof_tbl_data_image[at] : 0;
}

uint16_t wof_image16(uint32_t addr)
{
    return (uint16_t)((data_byte(addr) << 8) | data_byte(addr + 1u));
}

uint8_t wof_image8(uint32_t addr)
{
    return data_byte(addr);
}

uint32_t wof_image32(uint32_t addr)
{
    return ((uint32_t)wof_image16(addr) << 16) | wof_image16(addr + 2);
}

/* The tick's input byte, as the C code reads it: the low byte of tick_input (0x026D43). */
#define INPUT   ((uint8_t)wof_g.tick_input)

static uint16_t find_handle(int slot, uint32_t name)
{
    return wof_shape_handle(slot, wof_shape_find(&wof_assets.c[slot], name));
}

/* ------------------------------------------------------------------------------------ */

/* orig 0x021E24 - the C library's rand(): the seed at 0x026A16 times 0x41C64E6D plus
 * 0x3039, and bits 16 to 30 of the new seed. */
uint16_t wof_crand(void)
{
    wof_g.crand_seed = wof_g.crand_seed * 0x41C64E6Du + 0x3039u;
    return (uint16_t)((wof_g.crand_seed >> 16) & 0x7FFFu);
}

/* orig 0x01C982 - the map record under a world x: x / 8 words into the list, the last
 * record for anything at or beyond the end, record 0 for x below zero. */
uint32_t wof_record_at(int16_t x)
{
    uint32_t at;

    if (x < 0)
        x = 0;
    at = (uint32_t)(uint16_t)(int16_t)(((int32_t)x / 8) * 2);   /* asl.w, then ext.l */
    at = (uint32_t)(int32_t)(int16_t)(uint16_t)at;
    if (at >= wof_m.map_records_end[0].off)
        at = wof_m.map_records_end[0].off - 2u;
    return at;
}

/* orig 0x01AA6E - whether the aircraft may turn: always on the deck; in the air not while
 * an enemy aircraft of state 2, 1, 3 is at 13 of its +0x16 (M6).  The walk's record pointer
 * the original keeps at 0x027DF0 is set before every read, so the port walks by index. */
static int16_t turn_allowed(void)
{
    int16_t r = 1;

    if (P.on_deck == 0) {
        for (int16_t i = 0; i < 4; i++) {
            const wof_aircraft_t *a = &wof_m.aircraft_records[i];

            if (a->w[0] == 2 && a->w[1] == 1 && a->w[2] == 3 && a->w[11] > 12 && a->w[11] < 14)
                r = 0;
        }
    }
    return r;
}

/* orig 0x01AAEA - how far the aircraft's wheels are below its reference point: by the
 * attitude while it turns in the air, else by the frame's height (0x025AAC) and, while the
 * hook is out (g_02540a), the hook's (0x025AC2). */
int16_t wof_wheel_height(void)
{
    int16_t d = 0x0B;
    int16_t att = wof_g.attitude_index;

    if (att != 0 && P.on_deck != 1 && P.on_deck != 0x0B) {
        if (att < 6)
            d = (int16_t)wof_image16(0x025B00u + 2u * (uint32_t)(int32_t)att);
        else if (att > 0x13)
            d = (int16_t)wof_image16(0x025B00u + 2u * (uint32_t)(int32_t)(int16_t)(0x19 - att));
    } else {
        d = (int16_t)wof_image16(0x025AACu + 2u * (uint32_t)(uint16_t)wof_g.g_025592);
        if (wof_g.g_02540a)
            d = (int16_t)(d + (int16_t)wof_image16(0x025AC2u + 2u * (uint32_t)(uint16_t)wof_g.g_025592));
    }
    return d;
}

/* orig 0x01AB80 - one step of a turn, every second call: the attitude runs 0 to 25, the
 * facing changes at 14, and past 19 without `whole` it folds back towards 13. */
static void turn_step(int32_t whole)
{
    if (!turn_allowed())
        return;
    if (--wof_g.g_025aa0 != 0)
        return;
    wof_g.g_025aa0 = 2;
    wof_g.attitude_index++;
    if (wof_g.attitude_index > 0x19) {
        wof_g.attitude_index = 0;
        return;
    }
    if (wof_g.attitude_index > 0x13 && whole == 0)
        wof_g.attitude_index = (int16_t)(wof_g.attitude_index - (int16_t)((wof_g.attitude_index - 0x0D) << 1));
    if (wof_g.attitude_index == 0x0E)
        P.facing = (int16_t)-P.facing;
}

/* orig 0x01ABDE - the name of the aircraft's frame for a state, a facing and a frame
 * index, with the frame's records in hellcat.shp and Torpedo.shp mirrored to the facing on
 * the way (re/notes/shapes.md).  The tables are read at the original's addresses, so an
 * index past a table's end reads what follows it, as the original does. */
static void mark_both(uint32_t name, int16_t facing)
{
    uint16_t want = (uint16_t)(facing + 1);

    wof_mark_facing(WOF_C_HELLCAT, find_handle(WOF_C_HELLCAT, name), want);
    wof_mark_facing(WOF_C_TORPEDO, find_handle(WOF_C_TORPEDO, name), want);
}

uint32_t wof_aircraft_frame(int16_t state, int16_t facing, int16_t frame)
{
    uint32_t name;
    int32_t  f = frame;

    switch (state) {
    case 0:
    case 4:
        if (wof_g.attitude_index != 0) {                          /* 0x01ACAA */
            wof_g.g_025592 = 0;
            if (P.facing == -1)
                return wof_image32(0x025D10u + 4u * (uint32_t)f);
            return wof_image32(0x025D78u + 4u * (uint32_t)f);
        }
        name = wof_image32(0x025DE0u + 4u * (uint32_t)f);
        mark_both(name, facing);
        wof_g.g_025592 = (int16_t)wof_image16(0x025AD8u + 2u * (uint32_t)f);
        return name;
    case 1:
    case 11:
        if (wof_g.g_025a9c != 0) {                                /* 0x01ACEA */
            f = 9;
            name = wof_image32(0x025DE0u + 4u * (uint32_t)f);
        } else {
            name = wof_image32(0x025CE0u + 4u * (uint32_t)f);
        }
        mark_both(name, facing);
        wof_g.g_027de6 = (int16_t)wof_image16(0x025D00u + 2u * (uint32_t)f);
        wof_g.g_025592 = 4;
        return name;
    default:                                                      /* 0x01ADFE */
        name = wof_image32(0x025DE0u + 4u * (uint32_t)f);
        mark_both(name, facing);
        wof_g.g_025592 = (int16_t)wof_image16(0x025AD8u + 2u * (uint32_t)f);
        return name;
    }
}

/* orig 0x01AED8 - while the aircraft burns or sinks, a puff of smoke now and then: at
 * most 0x4B of them, each some random ticks after the last, at a random x beside it. */
static void wreck_smoke(void)
{
    uint32_t at = wof_record_at(P.x);
    int16_t  dy = (int16_t)(P.y - wof_wheel_height());
    int16_t  sinking = P.on_deck == 6 ? 1 : 0;

    if (sinking)
        dy = 0;
    wof_g.g_025428 = 0;
    if (wof_g.g_025aa6 >= 0x4B || wof_g.g_025aa6 < wof_g.g_025aa8)
        return;
    {
        int16_t r = (int16_t)(wof_crand() & 0x0C);
        int16_t x;

        wof_g.g_025aa8 = (int16_t)(wof_g.g_025aa6 + r);
        x = (int16_t)((int16_t)(wof_crand() & 0x0F) + P.x - 8);
        (void)at;
        wof_object_spawn(wof_record_at(x), dy, sinking);
    }
}

/* orig 0x01AF7C - the time after a crash: with the last life the game is over; after 150
 * ticks, or after 30 with the button, the next aircraft (0x0135CE). */
static wof_co_t lost_wait(void)
{
    wof_ctx_t *c = &wof_f.co_lost;

    CO_BEGIN(c);
    if (wof_g.lives == 1 || wof_g.lives == 0)
        wof_g.game_over = 1;
    wof_g.g_025aa6++;
    if (wof_g.g_025aa6 == 0x96 || (wof_g.g_025aa6 > 0x1E && (INPUT & 0x30u)))
        CO_CALL(c, &wof_f.co_restart, wof_next_aircraft());
    CO_END(c);
}

/* orig 0x01AFBA - the aircraft down.  Where it came down decides: the sea (0x01CB74 says a
 * record of low bits 0, or outside the list), a ship (record_on_ship), or land.  In the
 * sea it floats and sinks, on land or a deck it burns; the attitude levels out two steps a
 * tick and, once the aircraft rests, the record goes to state 6 (in the water) or 8
 * (burning).  What a wreck at rest on land or a deck does to the island's targets and the
 * object it leaves are M5's. */
void wof_crash(void)
{
    int16_t  where = 1;            /* -2(a5): 1 land, 2 the sea, 3 a ship */
    int16_t  fall = 0;             /* -8(a5) */
    int16_t  rest = 0;             /* -0x0A(a5) */
    int16_t  wheels = wof_wheel_height();                         /* -0x10(a5) */
    uint32_t at = wof_record_at(P.x);                              /* -6(a5) */

    if (wof_on_water(at))
        where = 2;
    else if (wof_record_on_ship(at))
        where = 3;

    switch (where) {
    case 2:                                                       /* 0x01B01A */
        if (P.y <= wof_wheel_height()) {
            wof_g.g_025592 = 0;
            wof_g.pitch_angle = 0;
            wof_g.pitch_target = 0;
            P.y = wof_wheel_height();
            rest = 1;
            wof_splash_spawn((int16_t)(P.x + (int16_t)(P.facing << 3)));
        }
        break;
    case 1:                                                       /* 0x01B070 */
        if ((int16_t)(P.y - wof_wheel_height()) > 0 || wof_g.attitude_index != 0) {
            fall = 1;
        } else {
            wof_g.g_025592 = 0;
            wof_g.pitch_angle = 0;
            wof_g.pitch_target = 0;
            P.y = wof_wheel_height();
            wof_aircraft_frame(P.on_deck, P.facing, 0);
            rest = 1;
            wof_object_spawn(at, (int16_t)(P.y - 1), 0);
        }
        break;
    case 3: {                                                     /* 0x01B0E2 */
        int16_t step = (int16_t)((int16_t)((int32_t)wof_g.airspeed / 100) * P.facing);

        wheels = (int16_t)(wheels + wof_ground_height(at));
        if (P.y <= wheels) {
            if (wof_on_water((uint32_t)(at - (uint32_t)(int32_t)(int16_t)(P.facing * 10)))) {
                P.x = (int16_t)(P.x - (int16_t)(step + 4));
                wof_g.airspeed = 0;
                wof_flash_set(7, 0x0F00);
                wheels = 2;
                wof_object_spawn(at, P.y, 0);
            } else {
                rest = 1;
                wof_g.g_025592 = 0;
                wof_g.pitch_angle = 0;
                wof_g.pitch_target = 0;
                P.y = (int16_t)(wof_wheel_height() + wof_ground_height(at));
            }
        }
        break;
    }
    }

    /* 0x01B1BC: the attitude levels out, two steps a tick */
    if (wof_g.attitude_index < 0x0E) {
        wof_g.attitude_index = (int16_t)(wof_g.attitude_index - 2);
        if (wof_g.attitude_index < 0)
            wof_g.attitude_index = 0;
    } else {
        if (wof_g.attitude_index == 0x0E)
            P.facing = (int16_t)-P.facing;
        wof_g.attitude_index = (int16_t)(wof_g.attitude_index + 2);
        if (wof_g.attitude_index > 0x19)
            wof_g.attitude_index = 0;
    }

    if (wof_g.attitude_index != 0 && P.y <= wheels) {             /* 0x01B1F8 */
        int16_t lift = 0x0B;

        if (wof_g.attitude_index < 6)
            lift = (int16_t)wof_image16(0x025B00u + 2u * (uint32_t)(int32_t)wof_g.attitude_index);
        else if (wof_g.attitude_index > 0x13)
            lift = (int16_t)wof_image16(0x025B00u + 2u * (uint32_t)(int32_t)(int16_t)(0x19 - wof_g.attitude_index));
        if (wof_record_on_ship(at) || wof_on_water(at))
            P.y = (int16_t)(wof_ground_height(at) + lift);
        P.x = (int16_t)(P.x + (int16_t)((int16_t)((int32_t)wof_g.airspeed / 100) * P.facing));
        wof_g.g_025410 = 0;
    } else if (rest) {                                            /* 0x01B2A2 */
        P.x = (int16_t)(P.x + (int16_t)((int16_t)((int32_t)wof_g.airspeed / 100) * P.facing));
        wof_g.airspeed = (int16_t)(wof_g.airspeed - 0x55);
        if (wof_g.airspeed < 0x64)
            wof_g.airspeed = 0;
        if (where == 2)
            wof_splash_spawn((int16_t)(P.x + (int16_t)(P.facing << 3)));
        else
            WOF_STANDIN("M5 PART 2 STAND-IN: 0x01B304, a wreck at rest on land or a deck");
    } else {                                                      /* 0x01B340 */
        wof_g.pitch_target = (int16_t)(wof_g.pitch_target - wof_g.pitch_step);
        if (wof_g.pitch_target < (int16_t)0xF3E4)
            wof_g.pitch_target = (int16_t)0xF3E4;
        fall = 1;
    }

    if (fall) {                                                   /* 0x01B35C */
        P.speed_y = (int16_t)(P.speed_y - 1);
        if (P.speed_y < -10)
            P.speed_y = -10;
        P.y = (int16_t)(P.y + P.speed_y);
        if ((int16_t)(P.y - wof_wheel_height()) <= 0) {
            P.y = wof_wheel_height();
            wof_object_spawn(at, (int16_t)(P.y - 1), 0);
        }
        P.x = (int16_t)(P.x + (int16_t)((int16_t)((int32_t)wof_g.airspeed / 100) * P.facing));
    }

    /* 0x01B3E6: at rest */
    if (wof_g.airspeed == 0 && wof_g.attitude_index == 0 && P.y <= wheels) {
        if (wof_on_water(at) || (wof_record_on_ship(at) && P.y < 0x14))
            P.on_deck = 6;
        else
            P.on_deck = 8;
        P.oil = 0;
        P.w1a = 0;
        wof_g.g_025aa8 = 0;
        wof_g.g_025aa6 = 0;
        wof_g.g_025aa4 = 0;
    }
}

/* orig 0x01B45A - whether the hook is out (0x02540A, the hook's extra height): on the deck,
 * in the lift, after the landing and in the burning state always; in the air only over the
 * carrier's lift, within 0x025F02 of it, while the carrier is afloat. */
static void hook_state(void)
{
    switch (P.on_deck) {
    case 0:
        if (P.x > (int16_t)(wof_g.player_start_x - (int16_t)wof_image16(0x025F02u)) &&
            P.x < (int16_t)(wof_g.player_start_x + (int16_t)wof_image16(0x025F02u)))
            wof_g.g_02540a = carrier.present ? 5 : 0;
        else
            wof_g.g_02540a = 0;
        break;
    case 1:
    case 7:
    case 11:
        wof_g.g_02540a = 5;
        wof_g.g_02534a = 5;
        break;
    default:
        wof_g.g_02540a = 0;
        break;
    }
}

/* orig 0x01B4DE - on the deck, whether the aircraft stands on the lift: its wheels, from
 * 0x025E30 and 0x025E3E by attitude and facing, inside player_start_x - 0x17 to + 0x21.
 * 0x02535F says why not: 1 short of it, 0 beyond it. */
static int16_t on_the_lift(void)
{
    int16_t r = 0, left, right;
    int32_t att = wof_g.attitude_index;

    if (P.on_deck != 1)
        return 0;
    if (P.facing < 0) {
        left  = (int16_t)(P.x - (int16_t)wof_image16(0x025E30u + 2u * (uint32_t)att));
        right = (int16_t)((int16_t)wof_image16(0x025E3Eu + 2u * (uint32_t)att) + P.x);
    } else {
        left  = (int16_t)(P.x - (int16_t)wof_image16(0x025E3Eu + 2u * (uint32_t)att));
        right = (int16_t)((int16_t)wof_image16(0x025E30u + 2u * (uint32_t)att) + P.x);
    }
    if (left < (int16_t)(wof_g.player_start_x - 0x17))
        wof_g.g_02535f = 1;
    else if (right > (int16_t)(wof_g.player_start_x + 0x21))
        wof_g.g_02535f = 0;
    else
        r = 1;
    return r;
}

/* orig 0x01B5B0 - the button: in the air a click drops the other weapon (M5) and holding it
 * fires the guns while the aircraft flies level and has rounds (0x025F14); on the deck, on
 * the lift, stopped and with the carrier afloat, it takes the aircraft down (state 11). */
static void button(void)
{
    if (!(wof_g.tick_input & 0x30u)) {
        wof_g.g_02536a = 0;
        return;
    }
    if (P.on_deck == 0) {
        if (INPUT & 0x20u) {
            if (wof_g.attitude_index < 6 || wof_g.attitude_index > 0x10)
                WOF_STANDIN("M5 PART 2 STAND-IN: 0x01B5E2, the other weapon dropped");
        } else if (wof_g.attitude_index == 0 && wof_g.g_025f14 > 0) {
            wof_g.g_02536a = 1;
        } else {
            wof_g.g_02536a = 0;
        }
        return;
    }
    if (P.on_deck == 1 && ABOARD == 0 && carrier.w0c != 0 && on_the_lift() && wof_g.airspeed == 0) {
        wof_g.g_02535f = 3;
        ABOARD = 3;
        P.on_deck = 11;
        wof_g.g_025428 = 0;
        P.y = (int16_t)(wof_wheel_height() + wof_ground_height(wof_record_at(P.x)));
    }
}

/* orig 0x01B682 - the guns against the enemy aircraft (M6): only while they fire, and only
 * a record in state 3 near the aircraft is hit. */
void wof_guns(void)
{
    if (!wof_g.g_02536a)
        return;
    for (int16_t i = 0; i < 4; i++)
        if (wof_m.aircraft_records[i].w[2] == 3)
            WOF_STANDIN("M6 STAND-IN: 0x01B6B0, the guns at an enemy aircraft");
}

/* orig 0x01B8C4 - whether the aircraft touches what is below it: its wheels at or below the
 * ground under the point it will be at, x plus its speed and 8 ahead. */
static int16_t touches(void)
{
    int16_t ahead = (int16_t)(P.x + (int16_t)((int16_t)(P.speed_x + 8) * P.facing));
    int16_t above = (int16_t)(P.y - wof_wheel_height());

    (void)ahead;
    if (above < wof_ground_height(wof_record_at(P.x)) || above <= 0)
        return 1;
    return 0;
}

/* orig 0x01B92E - the hook: at 600 or more of airspeed and with 0x025A9C clear, the hook
 * 0x18 behind the aircraft within 8 of one of the four cables, 0x38 apart from
 * player_start_x + 0x46, catches it: state 7. */
static void hook(void)
{
    int16_t hook_x;

    if (wof_g.airspeed < 0x258 || wof_g.g_025a9c != 0)
        return;
    hook_x = P.x;
    if (P.facing == -1)
        hook_x = (int16_t)(hook_x + 0x18);
    else
        hook_x = (int16_t)(hook_x - 0x18);
    wof_g.g_02540c = (int16_t)(wof_g.player_start_x + 0x46);
    for (int16_t i = 0; i < 4; i++) {
        if (hook_x >= (int16_t)(wof_g.g_02540c - 8) && hook_x <= (int16_t)(wof_g.g_02540c + 8)) {
            P.on_deck = 7;
            wof_g.g_025a9e = -1;
            wof_g.g_02535f = 4;
            wof_g.g_026d3a = wof_g.g_02540c;
            return;
        }
        wof_g.g_02540c = (int16_t)(wof_g.g_02540c + 0x38);
    }
}

/* orig 0x01B9CC - the engine's sound at rest (M8's parameters, kept as state). */
void wof_engine_idle(void)
{
    wof_g.g_02542c = 0x28;
    wof_g.g_025428 = 0x28;
    wof_g.g_02542e = 0x328;
    wof_g.g_02542a = 0x328;
    wof_g.g_027de8 = 0;
}

/* orig 0x01BA80 - the ground: once the aircraft's wheels come within 0x37 of the sea and it
 * touches, over the carrier's deck and level it lands if it flies left with the stick
 * forward alone (0x025AAA), else it bounces; anywhere else it crashes (state 4). */
static void ground(void)
{
    int16_t  x = P.x;
    uint32_t at = wof_record_at(P.x);
    int16_t  deck = 0;

    if (x >= wof_g.g_0253fc && x <= wof_g.g_0253fe && wof_g.attitude_index == 0 &&
        P.y >= (int16_t)(wof_ground_height(at) + wof_wheel_height() - 4) && carrier.present)
        deck = 1;
    if (wof_wheel_height() >= 0x37 || P.on_deck != 0 || !touches())
        return;
    if (deck) {
        if (P.facing == -1 && wof_g.landing_stall) {
            P.on_deck = 1;
            wof_g.g_025a9e = -1;
            /* 0x012380: the touch-down's sound (M8) */
            P.y = (int16_t)(wof_ground_height(at) + wof_wheel_height());
        } else {
            P.speed_y = (int16_t)-P.speed_y;
            wof_g.pitch_target = (int16_t)-wof_g.pitch_target;
            P.y = (int16_t)(P.y + 6);
            /* 0x012380: the touch-down's sound (M8) */
        }
        return;
    }
    P.on_deck = 4;
    wof_g.airspeed = (int16_t)(P.speed_x * 100);
    if (!wof_on_water(at) && !(wof_record_on_ship(at) && P.y < 0x14)) {    /* 0x01BBC4 */
        wof_object_spawn(wof_record_at((int16_t)((int16_t)(P.facing << 4) + P.x)), P.y, 0);
        WOF_STANDIN("M5 PART 2 STAND-IN: 0x01BBF4, what a crash on land does to the island's targets");
    }
    wof_crash();
}

/* orig 0x01BC02 - the enemy's countdown (0x02509A, M6 brings the aircraft): the button
 * holds it at 750 at most; without it, while the carrier is afloat, one less each tick. */
static void enemy_countdown(void)
{
    int16_t far = (int16_t)(0x7FFF - P.x);

    if (far < 0)
        far = (int16_t)-far;
    if (wof_g.tick_input & 0x30u) {
        if (P.enemy_countdown != 0 && P.enemy_countdown < 0x2EE)
            P.enemy_countdown = 0x2EE;
        return;
    }
    if (P.enemy_countdown == 0 || !carrier.present || carrier.w0c == 0)
        return;
    if (--P.enemy_countdown != 0 || far <= 0x1A00)
        return;
    WOF_STANDIN("M6 STAND-IN: 0x01BC66, the enemy aircraft come");
}

/* orig 0x01BCCE - on the deck, the carrier's state (0x02535F) and the touch-down: at the
 * lift nothing; else the deck's end ahead (0x01B4DE) or, rolling fast towards the wrong
 * end of the deck, the fall over it (4). */
static void deck_state(void)
{
    if (wof_g.g_025367) {
        if ((int16_t)(P.x - wof_g.g_0253fc) < 0x136 && wof_g.airspeed < 0x190)
            wof_g.g_02535f = 1;
        else
            wof_g.g_02535f = 0;
        return;
    }
    if (on_the_lift()) {
        wof_g.g_02535f = 5;
        return;
    }
    wof_g.g_025e4c = (int16_t)((int32_t)wof_g.airspeed / 4);
    wof_g.g_025e4e = (int16_t)(wof_g.g_025e4c * wof_g.g_025e4c);
    wof_g.g_025e4e = (int16_t)(wof_g.g_025e4e << 1);
    wof_g.g_025e4e = (int16_t)((int32_t)wof_g.g_025e4e / 100);
    wof_g.g_025e50 = (int16_t)(P.x - wof_g.player_start_x);
    if (wof_g.g_025e50 < 0)
        wof_g.g_025e50 = (int16_t)-wof_g.g_025e50;
    wof_g.g_025e50 = (int16_t)(wof_g.g_025e50 - 0x10);
    if (P.x < wof_g.player_start_x) {
        if (wof_g.g_025e4e > wof_g.g_025e50 && P.facing == 1 && wof_g.airspeed > 0)
            wof_g.g_02535f = 4;
    } else {
        if (wof_g.g_025e4e > wof_g.g_025e50 && P.facing == -1 && wof_g.airspeed > 0)
            wof_g.g_02535f = 4;
    }
}

/* orig 0x01BDBA - on the deck or the lift the airspeed moves the aircraft: speed x is
 * (airspeed + 50) / 100. */
static void deck_roll(void)
{
    if (P.on_deck == 0)
        return;
    P.speed_x = (int16_t)((int32_t)(int16_t)(wof_g.airspeed + 0x32) / 100);
    P.x = (int16_t)(P.x + (int16_t)(P.speed_x * P.facing));
}

/* orig 0x01BDFA player_motion - the pitch eases a quarter of the way to its target; the
 * sine and the cosine of the angle scale the airspeed into the two speed components, in
 * the game's floating point (re/notes/ffp.md, "player_motion"); below an airspeed of 1000
 * the aircraft sinks; the ceiling is 1100, where the climb reverses at half its speed. */
void wof_player_motion(void)
{
    int16_t  angle;
    uint32_t across, along, v;

    if (wof_g.landing_stall && wof_g.pitch_target == 0x258)
        wof_g.pitch_angle = (int16_t)(wof_g.pitch_angle +
                                      (int16_t)((int32_t)(int16_t)(0xFCE0 - (uint16_t)wof_g.pitch_angle) / 4));
    else
        wof_g.pitch_angle = (int16_t)(wof_g.pitch_angle +
                                      (int16_t)((int32_t)(int16_t)(wof_g.pitch_target - wof_g.pitch_angle) / 4));
    angle = (int16_t)(wof_g.pitch_angle + wof_g.pitch_delta);
    if (angle < 0)
        angle = (int16_t)-angle;
    across = wof_image32(0x025B74u + 4u * (uint32_t)(int32_t)(int16_t)((int32_t)angle / 100));
    along  = wof_image32(0x025B74u + 4u * (uint32_t)(int32_t)(int16_t)((int32_t)(int16_t)(0x2328 - angle) / 100));
    if (wof_g.pitch_angle < 0 || wof_g.pitch_delta < 0)
        across = wof_ffp_neg(across);

    wof_g.airspeed_step = (int16_t)(wof_g.airspeed_step - (int16_t)wof_ffp_fix(across));
    if (P.facing > 0 && wof_g.airspeed < 1000)
        wof_g.airspeed_step = (int16_t)(wof_g.airspeed_step - (int16_t)((int32_t)wof_g.airspeed_step / 10));

    v = wof_ffp_mul(wof_image32(0x025B0Cu + 4u * (uint32_t)(int32_t)wof_g.attitude_index),
                    wof_ffp_flt((uint32_t)(int32_t)wof_g.airspeed));
    v = wof_ffp_mul(v, along);
    v = wof_ffp_add(v, 0xC8000046u);                               /* + 50 */
    v = wof_ffp_div(v, 0xC8000047u);                               /* / 100 */
    P.speed_x = (int16_t)wof_ffp_fix(v);
    P.x = (int16_t)(P.x + (int16_t)(P.speed_x * P.facing));

    v = wof_ffp_mul(wof_ffp_flt((uint32_t)(int32_t)wof_g.airspeed), across);
    v = wof_ffp_div(v, 0xC8000047u);
    P.speed_y = (int16_t)wof_ffp_fix(v);
    if (wof_g.airspeed < 1000 && P.on_deck == 0) {
        if (!(INPUT & 0x01u)) {
            wof_g.pitch_target = (int16_t)(wof_g.pitch_target - (int16_t)((int32_t)wof_g.pitch_step / 2));
            if (wof_g.pitch_target < (int16_t)0xEE6C)
                wof_g.pitch_target = (int16_t)0xEE6C;
        }
        P.speed_y = (int16_t)(P.speed_y - (int16_t)((int32_t)(int16_t)(1000 - wof_g.airspeed) / 100));
    }
    P.y = (int16_t)(P.y + P.speed_y);
    if (P.y > 0x44C) {
        P.y = 0x44C;
        wof_g.pitch_target = (int16_t)-wof_g.pitch_target;
        P.speed_y = (int16_t)-(int16_t)((int32_t)P.speed_y / 2);
    } else if (P.y < -4) {
        P.y = -4;
    }
}

/* The pitch's small offset when the target stands between 0 and 500: its negative. */
static void pitch_nudge(void)
{
    if (wof_g.pitch_target > 0 && wof_g.pitch_target <= 0x1F4)
        wof_g.pitch_delta = (int16_t)-wof_g.pitch_target;
}

/* orig 0x01BFF4 - the stick in the air.  Left alone: a turn in progress finishes, the nose
 * comes down towards level, and the airspeed falls by its step, not below 1000.  Towards
 * the facing: full throttle, the airspeed rises by its step to 1400.  Against it: a turn.
 * Forward and back move the pitch target; the stick forward alone while flying left eases
 * it to 600 and sets 0x025AAA, the manual's stall. */
static void flight_controls(void)
{
    int16_t with = 0;
    int16_t dir = (INPUT & 0x08u) ? -1 : 1;

    wof_g.landing_stall = 0;
    (void)with;
    wof_g.pitch_delta = 0;
    if ((wof_g.tick_input & 0x0Fu) == 0) {
        if (wof_g.attitude_index != 0) {
            if (wof_g.attitude_index > 6)
                turn_step(0);
            else
                wof_g.attitude_index--;
            wof_g.g_025410 = 0;
            wof_g.pitch_target = (int16_t)(wof_g.pitch_target - (int16_t)((int32_t)wof_g.pitch_step / 4));
            if (wof_g.pitch_target < (int16_t)0xF736)
                wof_g.pitch_target = (int16_t)0xF736;
            pitch_nudge();
        } else if (wof_g.pitch_target > 0) {
            wof_g.pitch_target = (int16_t)(wof_g.pitch_target - wof_g.pitch_step);
            if (wof_g.pitch_target < 0)
                wof_g.pitch_target = 0;
            pitch_nudge();
        }
        wof_g.airspeed_step = (int16_t)(wof_g.airspeed_step - 1);
        if (wof_g.airspeed_step < 4)
            wof_g.airspeed_step = 4;
        if (wof_g.airspeed > 1000) {
            wof_g.airspeed = (int16_t)(wof_g.airspeed - wof_g.airspeed_step);
            if (wof_g.airspeed < 1000)
                wof_g.airspeed = 1000;
        }
        wof_g.g_025428 = 0x31;
        wof_g.g_02542a = 0x181;
        wof_g.g_027de8 = 0;
        return;
    }
    if (wof_g.tick_input & 0x0Cu) {                               /* 0x01C0F6 */
        if (P.facing == dir) {
            wof_g.g_027de8 = 1;
            if (wof_g.attitude_index != 0) {
                if (wof_g.attitude_index > 6)
                    turn_step(1);
                else
                    wof_g.attitude_index--;
            }
            wof_g.airspeed_step = (int16_t)(wof_g.airspeed_step + 1);
            if (wof_g.airspeed_step > 8)
                wof_g.airspeed_step = 8;
            wof_g.g_025428 = 0x40;
            wof_g.g_02542a = 0x14F;
            wof_g.g_027de8 = 1;
            wof_g.airspeed = (int16_t)(wof_g.airspeed + wof_g.airspeed_step);
            if (wof_g.airspeed > 0x578)
                wof_g.airspeed = 0x578;
        } else {
            turn_step(0);
        }
        if (wof_g.tick_input & 0x03u) {                           /* 0x01C176 */
            if (INPUT & 0x02u) {
                int16_t d = wof_g.attitude_index != 0 ? (int16_t)((int32_t)wof_g.pitch_step / 2)
                                                      : wof_g.pitch_step;

                wof_g.pitch_target = (int16_t)(wof_g.pitch_target - d);
                if (wof_g.pitch_target < (int16_t)0xEE6C)
                    wof_g.pitch_target = (int16_t)0xEE6C;
            } else if (wof_g.airspeed > 1000) {
                wof_g.pitch_target = (int16_t)(wof_g.pitch_target + wof_g.pitch_step);
                if (wof_g.pitch_target > 0xBB8)
                    wof_g.pitch_target = 0xBB8;
            } else {
                int16_t d = P.facing > 0 ? (int16_t)((int32_t)wof_g.pitch_step / 4)
                                         : (int16_t)((int32_t)wof_g.pitch_step / 8);

                wof_g.pitch_target = (int16_t)(wof_g.pitch_target + d);
                if (wof_g.pitch_target > 0xBB8)
                    wof_g.pitch_target = 0xBB8;
            }
        } else if (wof_g.attitude_index != 0) {                   /* 0x01C21E */
            wof_g.pitch_target = (int16_t)(wof_g.pitch_target - (int16_t)((int32_t)wof_g.pitch_step / 4));
            if (wof_g.pitch_target < (int16_t)0xF736)
                wof_g.pitch_target = (int16_t)0xF736;
            pitch_nudge();
        } else if (wof_g.pitch_target > 0) {
            wof_g.pitch_target = (int16_t)(wof_g.pitch_target - wof_g.pitch_step);
            if (wof_g.pitch_target < 0)
                wof_g.pitch_target = 0;
            pitch_nudge();
        }
        return;
    }
    /* 0x01C288: forward or back alone */
    wof_g.g_025428 = 0x31;
    wof_g.g_02542a = 0x181;
    wof_g.g_027de8 = 0;
    if (INPUT & 0x02u) {
        wof_g.g_025428 = 0x40;
        wof_g.g_02542a = 0x14F;
        wof_g.g_027de8 = 1;
        wof_g.pitch_target = (int16_t)(wof_g.pitch_target - (int16_t)(wof_g.pitch_step << 1));
        if (wof_g.pitch_target < (int16_t)0xEE6C)
            wof_g.pitch_target = (int16_t)0xEE6C;
    } else if (INPUT & 0x01u) {
        if (P.facing == -1) {
            if (wof_g.pitch_target == 0 || wof_g.pitch_target < 0x258) {
                wof_g.pitch_target = (int16_t)(wof_g.pitch_target + wof_g.pitch_step);
                if (wof_g.pitch_target > 0x258)
                    wof_g.pitch_target = 0x258;
            } else {
                wof_g.pitch_target = (int16_t)(wof_g.pitch_target - wof_g.pitch_step);
                if (wof_g.pitch_target < 0x258)
                    wof_g.pitch_target = 0x258;
            }
            wof_g.landing_stall = 1;
        } else {
            wof_g.pitch_target = (int16_t)(wof_g.pitch_target - wof_g.pitch_step);
            if (wof_g.pitch_target < (int16_t)0xFDA8)
                wof_g.pitch_target = (int16_t)(wof_g.pitch_target -
                                               (int16_t)((int32_t)(int16_t)(wof_g.pitch_target + 0x258) / 2));
            wof_g.pitch_delta = 0;
            wof_g.landing_stall = 0;
        }
    }
    if (wof_g.attitude_index != 0) {                              /* 0x01C350 */
        if (wof_g.attitude_index > 6)
            turn_step(0);
        else
            wof_g.attitude_index--;
        wof_g.g_025410 = 0;
    }
}

/* orig 0x01C378 - the frames of this tick: the player's (+8, its name, and +4, its record
 * in hellcat.shp), the torpedo's under it (0x02541E) and, flying level, the shape
 * 0x02541A the drawing puts in front (0x025E52 by pitch flying left, 0x025EA2 right). */
static void frame_select(void)
{
    int16_t up = 0;                /* -2(a5): the pitch as a frame step */
    int16_t which = 9;             /* -6(a5) */

    wof_g.g_025422 = 0;
    if (P.on_deck != 1 && P.on_deck != 0x0B && wof_g.attitude_index == 0) {
        up = (int16_t)((int32_t)(int16_t)(wof_g.pitch_target + 0x1388) / 0x1F4);
        which = up;
    }
    if (P.on_deck == 0 || P.on_deck == 7 || P.on_deck == 4 || wof_g.g_025a9c == 1) {
        if (wof_g.attitude_index != 0) {
            P.frame_name = wof_aircraft_frame(P.on_deck, P.facing, wof_g.attitude_index);
            wof_g.g_025a9e = -1;
        } else {
            if (P.facing == -1) {
                wof_g.g_025422 = wof_image32(0x025E52u + 4u * (uint32_t)(int32_t)which);
                wof_g.g_025426 = (int16_t)(up + 0x0A);
            } else {
                wof_g.g_025422 = wof_image32(0x025EA2u + 4u * (uint32_t)(int32_t)which);
                wof_g.g_025426 = up;
            }
            wof_m.g_02541a[0].s = find_handle(WOF_C_HELLCAT, wof_g.g_025422);
        }
    }
    if (P.on_deck != 8)
        P.frame_name = wof_aircraft_frame(P.on_deck, P.facing, (int16_t)(wof_g.attitude_index + up));
    P.shape = find_handle(WOF_C_HELLCAT, P.frame_name);
    wof_m.torpedo_shape[0].s = find_handle(WOF_C_TORPEDO, P.frame_name);
}

/* orig 0x01C4E8 - the stick on the deck: towards the facing the aircraft rolls faster,
 * against it, stopped, it turns round on the spot (the attitude up to 6, then the facing
 * flips); left alone it slows down.  0x025A9C: fast enough to lift off unless the stick is
 * held forward, which is what keeps the hook down. */
static void deck_controls(void)
{
    wof_g.g_02536a = 0;
    if (wof_g.tick_input & 0x0Cu) {
        int16_t dir = (INPUT & 0x08u) ? -1 : 1;

        if (P.facing == dir) {
            wof_g.g_027de8 = 1;
            if (wof_g.attitude_index == 0) {
                wof_g.g_025428 = 0x40;
                wof_g.g_02542a = 0x14F;
                wof_g.airspeed_step = (int16_t)(wof_g.airspeed_step + 1);
                if (wof_g.airspeed_step > 8)
                    wof_g.airspeed_step = 8;
            } else {
                wof_g.g_025428 = 0x28;
                wof_g.g_02542a = 0x328;
                wof_g.attitude_index--;
            }
            wof_g.airspeed = (int16_t)(wof_g.airspeed + wof_g.airspeed_step);
        } else {
            wof_g.g_027de8 = 0;
            wof_g.g_025428 = 0x28;
            wof_g.g_02542a = 0x328;
            wof_g.airspeed_step = 0;
            if (wof_g.airspeed == 0) {
                wof_g.attitude_index++;
                if (wof_g.attitude_index > 6) {
                    P.facing = (int16_t)-P.facing;
                    wof_g.attitude_index = 5;
                }
            }
            wof_g.airspeed = (int16_t)(wof_g.airspeed - 8);
        }
    } else {
        wof_g.g_025428 = 0x28;
        wof_g.g_02542a = 0x328;
        wof_g.g_027de8 = 0;
        wof_g.airspeed_step = 0;
        wof_g.airspeed = (int16_t)(wof_g.airspeed - 8);
    }
    wof_g.g_025a9c = 0;
    if (wof_g.airspeed > 0x258 && !(INPUT & 0x01u))
        wof_g.g_025a9c = 1;
    if (wof_g.airspeed < 0)
        wof_g.airspeed = 0;
    else if (wof_g.airspeed > 0x578)
        wof_g.airspeed = 0x578;
}

/* orig 0x01C5F4 - off either end of the deck the aircraft is in the air (state 0); on it,
 * its wheels stand on the deck. */
static void deck_edge(void)
{
    if (P.x < wof_g.g_0253fc || P.x > wof_g.g_0253fe) {
        wof_g.g_02535f = 2;
        wof_g.g_025367 = 0;
        P.on_deck = 0;
        wof_g.g_025410 = (int16_t)wof_image16(0x025F04u);
        return;
    }
    P.y = (int16_t)(wof_wheel_height() + wof_ground_height(wof_record_at(P.x)));
}

/* orig 0x01CAB4 flash_set - the sky's flash: flash_colour on every other of `count`
 * passes (flip_buffers). */
void wof_flash_set(int16_t count, int16_t colour)
{
    wof_g.flash_count = count;
    wof_g.flash_colour = colour;
}

/* orig 0x01CAE0 - a puff of smoke from the burning wreck, a random 0 to 7 to the right and
 * 6 up, through 0x0154CC into the Smoke pool. */
static void burn_smoke(int16_t unused, int16_t kind, int16_t x, int16_t y)
{
    (void)unused;
    x = (int16_t)(x + (int16_t)(wof_rand_beam(0x01CAE4) & 7));
    y = (int16_t)(y + 6);
    wof_smoke_claim((int32_t)((uint32_t)(int32_t)x << 16), (int32_t)((uint32_t)(int32_t)y << 16), kind);
}

/* orig 0x01CB74 - whether a map record is open sea: low bits 0, or outside the list. */
int wof_on_water(uint32_t at)
{
    if (at == 0 || !(at < wof_m.map_records_end[0].off - 2u))
        return 1;
    return ((at >> 1) < 3576u ? (wof_m.map_records[at >> 1].v & 3u) : 0u) == 0;
}

/* orig 0x01C660 - the player, once per tick: the button, the enemy's countdown, and by the
 * record's state (+0x0C) one of the cases below; then the hook and the frames, and whether
 * the next snapshot takes the eighth-scale view (above y 0xBA).  While the weapon menu is
 * up (0x025364) nothing moves.  The states: 0 in the air, 1 on the deck, 4 falling, 6 in
 * the water, 7 caught by a cable, 8 burning, 11 on the lift; 2, 3, 5, 9 and 10 are never
 * set.  It waits, because the next aircraft (0x0135CE) is reached from states 6 and 8. */
wof_co_t wof_player_update(void)
{
    wof_ctx_t *c = &wof_f.co_player;

    CO_BEGIN(c);
    wof_g.g_025410 = 0x64;
    button();
    enemy_countdown();
    if (wof_g.g_025364 || wof_g.g_025365) {                       /* tst.w of 0x025364 */
        wof_g.airspeed_step = 0;
        wof_g.airspeed = 0;
        goto view;
    }
    if (wof_g.airspeed == 0)
        wof_g.g_026c8a = 0;
    /* The original's switch on the state, as a chain: the waits of states 6 and 8 cannot sit
     * inside a switch of the coroutine's own (src/coro.h). */
    if (P.on_deck == 0) {                                         /* 0x01C6A0 */
        if (P.oil < 0x60 || P.fuel < 0) {
            wof_g.g_02535f = 3;
            P.on_deck = 4;
            wof_g.airspeed = (int16_t)(P.speed_x * 100);
            wof_crash();
        } else if (P.y <= -7) {
            P.on_deck = 6;
            wof_g.g_025aa8 = 0;
            wof_g.g_025aa6 = 0;
            wof_g.g_025aa4 = 0;
            wof_g.g_02535f = 3;
        } else {
            flight_controls();
            wof_player_motion();
            ground();
            wof_g.g_02535f = P.y > 0x50 ? 3 : 2;
            deck_state();
        }
    } else if (P.on_deck == 1) {                                  /* 0x01C736 */
        deck_controls();
        deck_roll();
        deck_edge();
        hook();
        deck_state();
    } else if (P.on_deck == 4) {                                  /* 0x01C74E */
        wof_g.g_025428 = 0x19;
        wof_g.g_02542a = 0x3C0;
        wof_g.g_027de8 = 0;
        wof_g.g_02536a = 0;
        wof_g.pitch_delta = 0;
        wof_g.g_02535f = 3;
        wof_g.g_025a9e = -1;
        wof_crash();
    } else if (P.on_deck == 6) {                                  /* 0x01C78C */
        wof_g.g_025428 = 0;
        if (++wof_g.g_025aa4 > 2) {
            wof_g.g_025aa4 = 0;
            P.y = (int16_t)(P.y - 1);
        }
        wof_g.pitch_target = (int16_t)(wof_g.pitch_target - 0xFA);
        if (wof_g.pitch_target < (int16_t)0xEE6C)
            wof_g.pitch_target = (int16_t)0xEE6C;
        wreck_smoke();
        CO_CALL(c, &wof_f.co_lost, lost_wait());
    } else if (P.on_deck == 7) {                                  /* 0x01C882 */
        wof_g.g_025428 = 0x28;
        wof_g.g_02542a = 0x328;
        P.y = (int16_t)(wof_wheel_height() + wof_ground_height(wof_record_at(P.x)));
        wof_g.pitch_target = 0;
        wof_g.pitch_delta = 0;
        wof_g.g_026c8a = 0;
        wof_g.airspeed = (int16_t)(wof_g.airspeed - 0x6E);
        if (wof_g.airspeed < 0) {
            wof_g.airspeed = 0;
            P.on_deck = 1;
            wof_g.g_025a9e = -1;
        }
        deck_roll();
    } else if (P.on_deck == 8) {                                  /* 0x01C7C6 */
        uint32_t at;

        P.frame_name = P.facing == -1 ? 0x68637266u : 0x68637235u;     /* hcrf, hcr5 */
        wof_g.g_025592 = 0;
        at = wof_record_at(P.x);
        if (wof_record_on_ship(at))
            P.y = (int16_t)(wof_wheel_height() + wof_ground_height(at));
        else
            P.y = wof_wheel_height();
        if ((++wof_g.g_026c84 & 3) == 0)
            burn_smoke(1, 6, (int16_t)(P.x + (int16_t)(P.facing << 3)), (int16_t)(P.y + 0x0B));
        wreck_smoke();
        CO_CALL(c, &wof_f.co_lost, lost_wait());
    } else if (P.on_deck != 9) {                                  /* 2, 3, 5, 10, 11 */
        P.y = (int16_t)(wof_wheel_height() + wof_ground_height(wof_record_at(P.x)));
        if (ABOARD == 0)
            P.on_deck = 1;
    }
    hook_state();
    frame_select();
view:
    wof_g.g_0253b0 = 8;
    if (P.y > 0xBA)
        wof_g.g_0253b0 = 1;
    CO_END(c);
}

#ifdef WOF_TRACE
/* The player's routines by their original address, for the oracle tests (T4,
 * tests/test_oracle_m4.py): the static ones have no other way in.  Test builds only. */
int32_t wof_test_player_call(uint32_t orig, int32_t a)
{
    uint16_t slot;

    switch (orig) {
    case 0x01AA6E: return turn_allowed();
    case 0x01AAEA: return wof_wheel_height();
    case 0x01AB80: turn_step(a); return 0;
    case 0x01AFBA: wof_crash(); return 0;
    case 0x01BA80: ground(); return 0;
    case 0x01B45A: hook_state(); return 0;
    case 0x01B4DE: return on_the_lift();
    case 0x01B5B0: button(); return 0;
    case 0x01B8C4: return touches();
    case 0x01B92E: hook(); return 0;
    case 0x01BC02: enemy_countdown(); return 0;
    case 0x01BCCE: deck_state(); return 0;
    case 0x01BDBA: deck_roll(); return 0;
    case 0x01BDFA: wof_player_motion(); return 0;
    case 0x01BFF4: flight_controls(); return 0;
    case 0x01C4E8: deck_controls(); return 0;
    case 0x01C5F4: deck_edge(); return 0;
    case 0x01C982: return (int32_t)wof_record_at((int16_t)a);
    case 0x01CB34: return wof_record_on_ship((uint32_t)a);
    case 0x01CB74: return wof_on_water((uint32_t)a);
    case 0x015714: return wof_ground_height((uint32_t)a);
    case 0x0150C8: {
        uint16_t low = wof_map_slot_at((int16_t)a, &slot);

        return (int32_t)(((uint32_t)slot << 16) | low);
    }
    default:       return -1;
    }
}
#endif
