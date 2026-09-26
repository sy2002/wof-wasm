/* The object records (M5): the weapons in flight and the explosions, as the pass draws them,
 * in the original's address order (re/notes/objects.md; re/notes/porting-m5.md, "The object
 * records").
 *
 * A record's +0x22 is its type, the weapon it is: 0 a rocket, 1 a bomb, 2 the torpedo, the
 * weapon_type (0x0253A4) at the drop; an explosion object_spawn's first entry makes is of
 * type 1.  Its +0x20 is its kind: 0xFF while it flies, 8 while it goes out, 0 when free.
 * The guns' rounds are no object at all (0x0119BC takes the ground they hit directly).
 *
 * The listing addresses a record's positions and speeds as 16.16 longs: x at +0x00 with its
 * fraction at +0x02, y at +0x04 (+0x06, never written), the horizontal speed at +0x0E, the
 * vertical at +0x12, a rocket's thrust at +0x16 and +0x1A; the helpers below join and split
 * the words the record keeps.
 */
#include "wof.h"
#include "gen/tables.h"

#define P       (wof_m.player[0])

enum { T_WORLD, T_EIGHTH, T_MASTER, T_ATH, T_TORPEDO };

/* orig 0x010702 - one object record's drawing, by its type: a bomb from torpedo_shapes by its
 * frame (0x40 on), the torpedo 0x88 or 0x89 by the side it faces (+0x1F) and nothing once it
 * runs in the water (frame 0x0A), a rocket 0x4C on or 0x74 on while it still falls (+0x24)
 * by its frame; in the eighth-scale view every one is entry 9 of eighth_shapes.  While its
 * drawing kind is 8 it is going out: eight frames from world_shapes counted in +0x21, the
 * explosion 0x5A on over land or a ship, the splash 0x66 on over the sea (+0x1F 0), and
 * after the eighth the pass frees the record by clearing its kind (re/notes/passes.md). */
static void object_draw(wof_object_t *o)
{
    int     table = T_TORPEDO;
    int16_t d2;

    if (o->type == 1) {
        d2 = 9;
        if (wof_g.view_step != 1)
            d2 = (int16_t)(uint8_t)(0x40 + o->frame);             /* add.b */
    } else if (o->type == 2) {
        if (o->frame == 0x0A)
            return;
        d2 = 9;
        if (wof_g.view_step != 1)
            d2 = o->b1f < 0 ? 0x89 : 0x88;
    } else {
        d2 = 9;
        if (wof_g.view_step != 1)
            d2 = (int16_t)(uint8_t)((o->w24 != 0 ? 0x74 : 0x4C) + o->frame);   /* add.b */
    }
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
    if (wof_g.view_step != 8)
        table = T_EIGHTH;
    wof_draw_world_shape(table, d2, o->draw_x, o->draw_y);
}

/* orig 0x0106BE - the object records whose drawing kind is set, the extra one last; a
 * weapon's launch (0x01107C) leaves 0x02536C set, which the pass clears. */
void wof_draw_objects(void)
{
    if (wof_g.g_02536c)
        wof_g.g_02536c = 0;
    for (int i = 0; i < 15; i++)
        if (wof_m.object_records[i].draw_kind)
            object_draw(&wof_m.object_records[i]);
    if (wof_m.object_record_extra[0].draw_kind)
        object_draw(&wof_m.object_record_extra[0]);
}

/* ------------------------------------------------------------ the longs of a record */

static uint32_t long_x(const wof_object_t *o)
{
    return ((uint32_t)(uint16_t)o->x << 16) | (uint16_t)o->w02;
}

static void set_long_x(wof_object_t *o, uint32_t v)
{
    o->x   = (int16_t)(uint16_t)(v >> 16);
    o->w02 = (int16_t)(uint16_t)v;
}

static uint32_t long_y(const wof_object_t *o)
{
    return ((uint32_t)(uint16_t)o->y << 16) | (uint16_t)o->w06;
}

static uint32_t long_0e(const wof_object_t *o)
{
    return ((uint32_t)(uint16_t)o->speed_x << 16) | (uint16_t)o->w10;
}

static void set_long_0e(wof_object_t *o, uint32_t v)
{
    o->speed_x = (int16_t)(uint16_t)(v >> 16);
    o->w10     = (int16_t)(uint16_t)v;
}

static uint32_t long_16(const wof_object_t *o)
{
    return ((uint32_t)(uint16_t)o->w16 << 16) | (uint16_t)o->w18;
}

static void set_long_16(wof_object_t *o, uint32_t v)
{
    o->w16 = (int16_t)(uint16_t)(v >> 16);
    o->w18 = (int16_t)(uint16_t)v;
}

static uint32_t long_1a(const wof_object_t *o)
{
    return ((uint32_t)(uint16_t)o->w1a << 16) | (uint16_t)o->w1c;
}

static void set_long_1a(wof_object_t *o, uint32_t v)
{
    o->w1a = (int16_t)(uint16_t)(v >> 16);
    o->w1c = (int16_t)(uint16_t)v;
}

/* The four longs shot_origin (0x011274) leaves from 0x026E62. */
static uint32_t shot_long(int16_t hi, int16_t lo)
{
    return ((uint32_t)(uint16_t)hi << 16) | (uint16_t)lo;
}

/* ---------------------------------------------------------- 0x0107F2 to 0x010999 */

static void launch(wof_object_t *o);

/* orig 0x0107F2 object_draw_first - the other weapon, if any is left: 0x026F8A 0x14 for the
 * debug view behind 0x02536D, then the first free object record (of the fifteen, not the
 * extra one) goes to the launch at 0x01088E; with none free nothing is dropped. */
static void object_draw_first(void)
{
    wof_g.g_026f8a = 0x14;
    if (wof_g.weapon_count == 0)
        return;
    for (int i = 0; i < 15; i++) {
        if (wof_m.object_records[i].kind == 0) {
            launch(&wof_m.object_records[i]);
            return;
        }
    }
}

/* orig 0x010820 object_spawn - a free object record (+0x20 zero) for something left at a
 * map record: at the record's world x (its byte offset times four, a word), 0x0C above `y`,
 * kind 8, type 1; `flag` 0 marks it (+0x1F 2) and makes the burst's sound (0x012324).  With
 * all fifteen in use nothing happens. */
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
    if (flag == 0) {
        o->b1f = 2;
        wof_sound_boom(o->x);                                     /* 0x010888: jmp 0x012324 */
    }
}

/* orig 0x01088E - object_spawn's second entry, the launch: one weapon less unless they are
 * unlimited (0xFF), the weapon type, the aircraft's speeds (the horizontal one turned with
 * its facing) and position from shot_origin's longs, y the drawing's plus 0x0B, and the frame
 * 3 or 9 by the speed's sign.  A bomb flies at once; the torpedo keeps the facing's low byte
 * in +0x1F; a rocket also takes half the bearing (+0x26), the airspeed (+0x28), a thrust of
 * the bearing's sine and cosine times two (+0x1A, +0x16, the cosine turned with the speed),
 * a fall of 4, 8 or 12 ticks before it fires (+0x24, from the last of four draws of
 * rand_beam, 0 counting as 8) and the frame from the bearing, 0 to 9, ten more flying left. */
static void launch(wof_object_t *o)
{
    int16_t d0;

    if (wof_g.weapon_count != 0xFF)
        wof_g.weapon_count--;
    o->type = wof_g.weapon_type;
    o->l12 = (int32_t)shot_long(wof_g.g_026e62, wof_g.g_026e64);
    set_long_0e(o, shot_long(wof_g.g_026e66, wof_g.g_026e68));
    if (P.facing < 0)
        set_long_0e(o, (uint32_t)-(int32_t)long_0e(o));
    o->y = (int16_t)(wof_g.draw_player_y + 0x0B);
    set_long_x(o, shot_long(wof_g.g_026e6a, wof_g.g_026e6c));
    o->frame = (int8_t)(uint8_t)(o->speed_x >> 8) < 0 ? 3 : 9;
    if (o->type == 1) {
        o->kind = 0xFF;
        return;
    }
    if (o->type == 2) {
        o->b1f = (int8_t)(uint8_t)P.facing;                      /* 0x02508D */
        o->kind = 0xFF;
        return;
    }
    {
        int16_t  d4 = (int16_t)(wof_g.g_025404 >> 1);
        int32_t  v;
        uint16_t r = 0;

        o->w26 = d4;
        o->w28 = wof_g.airspeed;
        v = (int32_t)wof_sine(d4) * 0x10;
        set_long_1a(o, (uint32_t)(v >> 3));
        v = ((int32_t)wof_cosine(d4) * 0x10) >> 3;
        if (o->speed_x < 0)
            v = -v;
        set_long_16(o, (uint32_t)v);
        for (int k = 0; k < 4; k++)
            r = (uint16_t)wof_rand_beam(0x01088E);
        r = (uint16_t)(((uint16_t)(r << 1) | (uint16_t)(r >> 15)) & 0x0Cu);   /* rol.w #1 */
        if (r == 0)
            r = 8;
        o->w24 = (int16_t)r;
        d0 = (int16_t)(4 - (int16_t)(wof_g.g_025404 >> 5));
        if (d0 < 0)
            d0 = 0;
        if (d0 > 9)
            d0 = 9;
        if ((int8_t)(uint8_t)(o->speed_x >> 8) < 0)
            d0 = (int16_t)(d0 + 0x0A);
        o->frame = (uint8_t)d0;
        o->kind = 0xFF;
    }
}

/* orig 0x01099A - a rocket's homing, when its fall ends and it fires: along its bearing
 * (half of it in +0x26, only while it points down) the guns' ground x at it and 0x14 either
 * side, none of them 0; then the first gun of an enemy ship (0x0111A6) between the middle
 * and either side, else the first standing pillbox (0x01115C) there by map offset; aimed at
 * what was found, the bearing is the angle of its distance and the rocket's height, turned
 * down, and the speeds are the airspeed / 100 along it (the horizontal one keeping its old
 * sign).  The rocket is in flight again (+0x20 0xFF) either way. */
static void homing(wof_object_t *o)
{
    int16_t  d4 = (int16_t)(o->w26 >> 1);
    int16_t  d7, d6, d5, d0;
    uint16_t high = 0;

    if (d4 < 0 &&
        (d7 = wof_guns_ground_x(d4)) != 0 &&
        (d6 = wof_guns_ground_x((int16_t)(d4 + 0x14))) != 0 &&
        (d5 = wof_guns_ground_x((int16_t)(d4 - 0x14))) != 0) {
        uint32_t found = wof_ship_gun_between(d7, d6);

        if ((uint16_t)found == 0)                                  /* tst.w d0 */
            found = wof_ship_gun_between(d7, d5);
        if ((uint16_t)found != 0) {
            d0 = (int16_t)(uint16_t)found;
            high = (uint16_t)(found >> 16);
        } else {
            d5 = (int16_t)(d5 >> 2);
            d6 = (int16_t)(d6 >> 2);
            d7 = (int16_t)(d7 >> 2);
            d0 = wof_pillbox_between(d7, d6);
            if (d0 == 0)
                d0 = wof_pillbox_between(d7, d5);
            d0 = (int16_t)(d0 * 4);
        }
        if (d0 != 0) {
            int32_t  v;
            uint16_t d5u;
            uint32_t old;

            d0 = (int16_t)(d0 - o->x);
            if (d0 < 0)
                d0 = (int16_t)-d0;
            d4 = wof_bearing_of(d0, o->y, high);
            if (d4 >= 0)
                d4 = (int16_t)-d4;
            d5u = (uint16_t)((uint16_t)o->w28 / 100u);             /* divu.w: the quotient word */
            v = (int32_t)wof_cosine(d4) * (int16_t)d5u;
            old = long_0e(o);
            set_long_0e(o, (uint32_t)v);
            if ((int32_t)old < 0)
                set_long_0e(o, (uint32_t)-v);
            v = (int32_t)wof_sine(d4) * (int16_t)d5u;
            o->l12 = v;
        }
    }
    o->kind = 0xFF;
}

/* ------------------------------------------------------- 0x010A72 to 0x010DA5, the flight */

/* orig 0x010AA6 object_step - one record in the tick.  Kind 8 lies where it was left.  A
 * rocket (type 0) falls its first ticks a pixel back and down (+0x24), is aimed as the fall
 * ends (0x01099A), and then flies on its thrust; it is freed once it is more than 0x500
 * pixels from the drawing's player (0x1680 in the eighth-scale view).  A bomb or a falling
 * torpedo loses a tenth of its horizontal speed and gravity's 0x6000 (0x025350) of its
 * vertical every tick.  Over an airfield (0x011126) a rocket goes out and anything else
 * bounces on its runway at height 0x1E; elsewhere it comes down at 0x0C above the sea, land
 * and targets, or at a ship's deck plus 0x0B: it hits (0x0146DC), goes out as kind 8 and
 * the soldiers within 0x10 start dying.  A torpedo that comes down gently into the sea runs
 * there instead (frame 0x0A, 0x45000 a tick for 200 ticks), with a splash every tick, and
 * hits the first thing that is not sea.  A bomb in flight steps its frame on every other pass
 * that drew it.
 *
 * `d4` is the caller's D4, which the listing leaves alone except where a running torpedo
 * keeps its position there: a torpedo whose time runs out splashes at the upper word D4
 * holds (0x010D9A). */
static void object_step(wof_object_t *o, uint32_t *d4)
{
    int16_t  d5, h;
    uint16_t d2 = 0, slot;

    if (o->kind == 8)
        return;
    if (o->type == 0) {
        uint32_t x, d1;
        uint16_t w;

        if (o->w24 != 0) {
            if (--o->w24 != 0) {
                o->x = (int16_t)(o->x - (P.facing < 0 ? -1 : 1));
                o->y = (int16_t)(o->y - 1);
                goto moved;
            }
            homing(o);
        }
        o->l12 = (int32_t)((uint32_t)o->l12 + long_1a(o));
        set_long_0e(o, long_0e(o) + long_16(o));
moved:
        x = long_0e(o) + long_x(o);
        set_long_x(o, x);
        d1 = (((uint32_t)(uint16_t)wof_g.draw_player_x << 16) | (uint16_t)wof_g.draw_player_x_frac) - x;
        if ((int32_t)d1 < 0)
            d1 = (uint32_t)-(int32_t)d1;
        w = (uint16_t)((d1 >> 16) - 0x280u);                      /* swap, sub.w */
        if (wof_g.view_shift)
            w = (uint16_t)(w - 0x1180u);
        if ((int16_t)w > 0x280) {
            o->kind = 0;
            return;
        }
        d5 = (int16_t)(uint16_t)(((uint32_t)o->l12 + long_1a(o) + long_y(o)) >> 16);
    } else {
        uint32_t d0, v;
        int16_t  q;

        if (o->type == 2 && o->frame == 0x0A)
            goto running;
        d0 = long_0e(o);
        q = (int16_t)((int16_t)(uint16_t)(d0 >> 16) / 10);       /* ext.l, divs.w #10 */
        d0 -= (uint32_t)(uint16_t)q << 16;
        set_long_0e(o, d0);
        set_long_x(o, long_x(o) + d0);
        v = (uint32_t)o->l12 - (uint32_t)wof_g.g_025350;
        o->l12 = (int32_t)v;
        d5 = (int16_t)(uint16_t)((v + long_y(o)) >> 16);
    }

    if (wof_airfield_at(o->x)) {                                  /* 0x010B88 */
        int16_t hw;

        if (d5 > 0x1E) {
            o->y = d5;
            goto flying;
        }
        if (o->type == 0) {
            o->kind = 0;
            goto flying;
        }
        o->y = 0x1E;
        o->l12 = (int32_t)-(uint32_t)o->l12;
        hw = (int16_t)((int16_t)(uint16_t)((uint32_t)o->l12 >> 16) >> 1);   /* asr.w $12(a2) */
        if (hw >= 9)
            hw = 9;
        o->l12 = (int32_t)(((uint32_t)(uint16_t)hw << 16) | ((uint32_t)o->l12 & 0xFFFFu));
        if (hw == 0) {
            o->kind = 0;
            goto flying;
        }
        o->speed_x = (int16_t)(o->speed_x >> 1);                  /* asr.w $e(a2) */
        if (o->speed_x == 0)
            o->kind = 0;
        goto flying;
    }

    o->y = d5;                                                    /* 0x010BF0 */
    d2 = wof_map_slot_at(o->x, &slot);
    if (d2 == 1)
        h = (int16_t)(wof_ground_height((uint32_t)(((uint16_t)o->x >> 2) & 0xFFFEu)) + 0x0B);
    else
        h = 0x0C;                         /* the sea, land and targets (low bits 2 test 3 and 4) */
    if (d5 > h)
        goto flying;
    o->y = h;
    o->b1f = (int8_t)(uint8_t)d2;
    if ((uint8_t)d2 == 0)                                         /* 0x010C7E: cmp.b #2, #0 */
        wof_sound_splash(o->x);                                   /* 0x01233E, in the sea */
    else
        wof_sound_boom(o->x);                                     /* 0x012324 */
    o->w1a = (int16_t)wof_g.pass_counter;
    if (o->type == 2)
        goto torpedo_down;
hit:
    wof_weapon_hit(o);                                            /* 0x010CAE */
    o->kind = 8;
    o->b21 = 1;
    wof_soldiers_hit(o->x, 0x10);
    return;

flying:                                                           /* 0x010CCA */
    if (o->type == 1 && wof_g.frame_drawn && (wof_g.pass_counter & 1u)) {
        o->frame++;
        if (o->frame > 0x0B)
            o->frame = 0;
    }
    return;

torpedo_down:                                                     /* 0x010D00 */
    if (d2 != 0)
        goto hit;
    if (o->frame != 0x0A) {
        uint32_t d0 = 0x45000u;

        if ((int16_t)(uint16_t)((uint32_t)o->l12 >> 16) < -5)
            goto hit;
        if (o->speed_x < 0)
            d0 = (uint32_t)-(int32_t)d0;
        set_long_0e(o, d0);
        o->frame = 0x0A;
        o->l12 = 0xC8;
        if (wof_g.pass_counter != (uint16_t)o->w1a) {
            o->w1a = (int16_t)wof_g.pass_counter;
            wof_splash_spawn((int16_t)(uint16_t)(d0 >> 16));        /* swap d0 */
        }
    }
running:                                                          /* 0x010D50 */
    o->l12 = (int32_t)((uint32_t)o->l12 - 1u);
    if (o->l12 > 0) {
        uint32_t x = long_0e(o) + long_x(o);

        set_long_x(o, x);
        *d4 = x;
        if ((uint8_t)wof_map_slot_at((int16_t)(uint16_t)(x >> 16), &slot) != 0) {
            wof_weapon_hit(o);
            o->kind = 8;
            o->b21 = 1;
            /* 0x010D8E: the burst, then the splash with what the burst left in D0 */
            wof_sound_splash((int16_t)wof_sound_boom(o->x));
            return;
        }
    } else {
        o->kind = 0;
        o->b21 = 0;
    }
    wof_splash_spawn((int16_t)(uint16_t)(*d4 >> 16));             /* 0x010D9A */
}

/* orig 0x010A72 objects_step - every object record in use through 0x010AA6, then the extra
 * one; frame_drawn is cleared between them.  `d4` is D4 as logic_tick leaves it. */
void wof_objects_step(uint32_t d4)
{
    for (int i = 0; i < 15; i++)
        if (wof_m.object_records[i].kind)
            object_step(&wof_m.object_records[i], &d4);
    wof_g.frame_drawn = 0;
    if (wof_m.object_record_extra[0].kind)
        object_step(&wof_m.object_record_extra[0], &d4);
}

/* orig 0x01107C - the other weapon dropped (the button's click, 0x01B5E2): 0x02536C set for
 * the pass, the launch, and 0x026E3D cleared. */
void wof_drop(void)
{
    wof_g.g_02536c = 0xFF;
    object_draw_first();
    wof_g.g_026e3d = 0;
}

/* orig 0x011126 - whether an airfield lies under world x: the first airfield record whose
 * span (+0x00 to +0x02) holds it; the walk ends at a record whose +0x00 is 0 or that begins
 * east of x. */
int wof_airfield_at(int16_t x)
{
    for (int i = 0; i < 4; i++) {
        const wof_airfield_t *a = &wof_m.airfield_records[i];

        if (a->w[0] == 0 || x < a->w[0])
            return 0;
        if (x <= a->w[1])
            return 1;
    }
    return 0;
}

/* orig 0x01115C - the first standing pillbox (slot 0x0F, +0x08 zero) whose map offset lies
 * from the smaller of two map offsets up to the larger, the larger excluded; its offset, or 0
 * when none.  The walk runs target_count_f records. */
int16_t wof_pillbox_between(int16_t a, int16_t b)
{
    int16_t lo = a, hi = b;

    if (hi < lo) {
        lo = b;
        hi = a;
    }
    for (uint16_t n = 0; n < wof_g.target_count_f && n < 32; n++) {
        const wof_gtarget_f_t *t = &wof_m.target_records_f[n];

        if (t->state != 0)
            continue;
        if (lo > t->map_offset)
            continue;
        if (hi > t->map_offset)
            return t->map_offset;
    }
    return 0;
}

/* A ship's gun list (+0x06): the list of its kind, or none (the carrier's is cleared). */
wof_gun_t *wof_ship_guns(const wof_ship_t *s)
{
    if (!s->guns)
        return 0;
    switch (s - wof_m.ship_records) {
    case 0:  return wof_m.guns_destroyer;
    case 1:  return wof_m.guns_battleship;
    case 2:  return wof_m.guns_cruiseship;
    case 3:  return wof_m.guns_japcarrier;
    default: return 0;
    }
}

/* orig 0x0111A6 - the first gun of a ship afloat whose world x (+0x04) lies between two x,
 * both included: the ships in ship_order (0x02555A, to its negative end) whose long at
 * +0x12 is not 0 and whose +0x04 has its high byte set, each gun of its list (+0x06, +0x0A
 * of them).  Returns D0 as the original leaves it: the ship record's address in the upper
 * word and the gun's x in the lower, or 0 when none. */
uint32_t wof_ship_gun_between(int16_t a, int16_t b)
{
    int16_t lo = a, hi = b;

    if (hi < lo) {
        lo = b;
        hi = a;
    }
    for (int i = 0; i < 6; i++) {
        uint32_t          addr = wof_tbl_ship_order[i];
        const wof_ship_t *s;
        const wof_gun_t  *list;

        if ((int32_t)addr < 0)
            break;
        s = &wof_m.ship_records[(addr - 0x025460u) / 0x1Eu];
        if (s->w12 == 0 && s->w14 == 0)
            continue;
        if (((uint16_t)s->present >> 8) == 0)
            continue;
        list = wof_ship_guns(s);
        for (int16_t n = 0; n < s->gun_count && list && n < 16; n++) {
            int16_t x = list[n].w[2];

            if (lo > x)
                continue;
            if (hi >= x)
                return (addr & 0xFFFF0000u) | (uint16_t)x;
        }
    }
    return 0;
}
