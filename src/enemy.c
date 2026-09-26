/* The enemy aircraft (M6 part 2): the module of compiled C from 0x01D18C to 0x01E8A7 in the
 * original's order, but for the two routines the mission's setup runs, enemy_frames
 * (0x01D1EA) and aircraft_clear (0x01E608), which are src/mission.c's.  What each routine
 * does, and the record's fields, are re/notes/enemy.md; the fields are named in
 * src/records.def.  Every routine takes the record's address in the original; here it
 * takes the record.  The player's record is player_record's (0x027DEC), always
 * player_y (0x025078).
 *
 * The compiler's C keeps int 16 bits wide: a product of muls.w that is sign-extended again
 * with ext.l before a divs.w keeps only its low word, and the port says so where it
 * happens.  The two speed limits 0x025F52 (900) and 0x025F54 (0xA28) are registered
 * globals of the DATA hunk that nothing writes. */
#include "wof.h"

#define P          (wof_m.player[0])
#define SPEED_MIN  (wof_g.aircraft_speed_min)
#define SPEED_MAX  (wof_g.aircraft_speed_max)

typedef wof_aircraft_t aircraft_t;

/* divs.w: a long divided by a word, the quotient's word.  The divisors here are the
 * speeds, which the scripts never bring to 0; a 68000 would trap, and the port leaves the
 * dividend's low word and records the trap for the tests. */
static int16_t divs_w(int32_t dividend, int16_t divisor)
{
    int32_t q;

    if (divisor == 0) {
        wof_trace_add("divs_zero", dividend, 0, 0, 0, 0, 0);
        return (int16_t)dividend;
    }
    q = dividend / divisor;
    if (q < -32768 || q > 32767)
        return (int16_t)dividend;
    return (int16_t)q;
}

static int16_t abs16(int16_t v)
{
    return v < 0 ? (int16_t)-v : v;
}

/* orig 0x01D18C aircraft_gone_far - a torpedo plane that has dropped (mode bit 4) and is
 * more than 0xA28 from the player is freed (state and mode 0); 1 when it was. */
static int16_t aircraft_gone_far(aircraft_t *a)
{
    if (a->mode & 0x10) {
        int16_t d = abs16((int16_t)(P.x - a->x));

        if (d > 0xA28) {
            a->state = 0;
            a->mode = 0;
            return 1;
        }
    }
    return 0;
}

/* orig 0x01D35A aircraft_frame_index - +0x30 from the attitude: a torpedo plane level
 * (mode bit 2, attitude 0) takes 0x1A; facing east the frame is 0x1C further. */
void wof_aircraft_frame_index(aircraft_t *a)
{
    int16_t f = a->attitude;

    if ((a->mode & 4) && a->attitude == 0)
        f = 0x1A;
    a->frame = a->facing == -1 ? f : (int16_t)(f + 0x1C);
}

/* orig 0x01D3B4 aircraft_relation - +0x04 where the aircraft is against the player: facing
 * the same way, 1 behind him and 3 ahead of him (which starts +0x10 at 0x226 when it is 0);
 * facing the other way, 2 east of him and 4 west.  +0x28 the distance. */
static void aircraft_relation(aircraft_t *a)
{
    int16_t dx = (int16_t)(a->x - P.x);

    if (P.facing == a->facing) {
        a->relation = 1;
        if ((int16_t)(dx ^ P.facing) >= 0) {
            a->relation = 3;
            if (a->timer == 0)
                a->timer = 0x226;
        }
    } else {
        a->relation = 2;
        if (dx < 0)
            a->relation = 4;
    }
    a->distance = (int16_t)(a->x - P.x);
    if (a->distance < 0)
        a->distance = (int16_t)-a->distance;
}

/* orig 0x01D476 aircraft_order - +0x0C, the place of each aircraft with a mode that tails
 * the player (relation 1) among those before it in the table that do: one further for
 * each nearer one, and each farther one moved one further. */
static void aircraft_order(void)
{
    aircraft_t *r = wof_m.aircraft_records;

    for (int16_t i = 0; i < 4; i++) {
        int16_t order = 1;

        if (r[i].mode == 0 || r[i].relation != 1)
            continue;
        for (int16_t j = 0; j < i; j++) {
            if (r[j].relation != 1)
                continue;
            if (r[j].distance < r[i].distance)
                order++;
            else
                r[j].order++;
        }
        r[i].order = order;
    }
}

/* orig 0x01D530 aircraft_turn_step - +0x10 cleared; the attitude one on every third call
 * (+0x32 counts 2, 1, 0). */
static void aircraft_turn_step(aircraft_t *a)
{
    int16_t old = a->step_count;

    a->timer = 0;
    a->step_count = (int16_t)(old - 1);
    if (old > 0)
        return;
    a->step_count = 2;
    a->attitude++;
}

/* orig 0x01D562 aircraft_turn - a turn (mode bit 3), from aircraft_motion.  A fighter
 * (mode 1 or 2) takes the player's height while he flies.  A fighter behind him or ahead
 * the same way at attitude 0x13 or more ends its turn at once when he flies level.  Else
 * the attitude steps on: past 0x19 the turn ends, at 0x0E the facing turns, and at 0x14 a
 * fighter may reverse it (the attitude mirrored about 0x0D, one more in +0x1A), by its
 * relation and the player's attitude; the third reversal ends that and sets +0x10. */
static void aircraft_turn(aircraft_t *a)
{
    int16_t on_deck1 = P.on_deck == 1;
    int16_t reverse = 0;

    if (P.on_deck == 0 && (a->mode & 3))
        a->want_y = P.y;
    if (wof_g.attitude_index == 0 && !on_deck1 && P.on_deck == 0 && a->attitude >= 0x13 &&
        (a->relation == 1 || a->relation == 3) && (a->mode & 3)) {
        a->attitude = 0;
        a->mode = (int16_t)(a->mode & ~8);
        return;
    }
    aircraft_turn_step(a);
    if (a->attitude > 0x19) {
        a->attitude = 0;
        a->mode = (int16_t)(a->mode & ~8);
        return;
    }
    if (a->attitude == 0x0E) {
        a->facing = (int16_t)-a->facing;
        a->attitude++;
        return;
    }
    if (a->attitude != 0x14 || !(a->mode & 3) || P.on_deck != 0)
        return;
    if (a->turns >= 3) {
        a->turns = 0;
        a->timer = 0x226;
        return;
    }
    switch (a->relation) {                   /* ext.l, cmp.l #5, bcc: 0 to 4 only */
    case 1:
        if (wof_g.attitude_index > 0 && wof_g.attitude_index < 6 && a->timer == 0)
            a->turn_in = divs_w((int16_t)(a->distance * 100), a->speed);   /* muls, ext.l */
        reverse = 1;
        break;
    case 2:
        if (wof_g.attitude_index > 0 && wof_g.attitude_index < 6)
            reverse = 1;
        break;
    case 3:
        reverse = 1;
        break;
    case 4:
        if (a->timer == 0)
            a->turn_in = divs_w((int16_t)(a->distance * 100),
                                (int16_t)(a->speed + wof_g.airspeed));
        reverse = 1;
        break;
    default:
        break;
    }
    if (reverse && !on_deck1 && a->timer == 0) {
        a->attitude = (int16_t)(a->attitude - (int16_t)((a->attitude - 0x0D) << 1));
        a->turns++;
    }
}

/* orig 0x01D796 aircraft_motion - per tick, every record not burning: +0x1E 0x6A4 while
 * the player is down (states 4, 6, 8); x by the attitude factor times the speed's hundreds
 * turned with the facing, in mathffp (re/notes/ffp.md); +0x24 at least 0x21 (0x46 while
 * he is on the deck) unless shot down or a torpedo plane; the height towards +0x24 by the
 * table 0x0261F8 of its distance's twentieths and a draw of two, a falling aircraft first
 * by its climb; +0x18 counted down into a turn; and the turn itself while flying. */
static void aircraft_motion(aircraft_t *a)
{
    int16_t  d4;
    uint32_t v;

    if (!(a->state & 0x14) && (P.on_deck == 4 || P.on_deck == 8 || P.on_deck == 6))
        a->want_speed = 0x6A4;
    v = wof_ffp_flt((uint32_t)(int32_t)(int16_t)(divs_w(a->speed, 100) * a->facing));
    v = wof_ffp_mul(wof_image32(0x025B0Cu + 4u * (uint32_t)(int32_t)a->attitude), v);
    a->x = (int16_t)(a->x + (int16_t)wof_ffp_fix(v));
    if (!(a->state & 0x14) && !(a->mode & 4)) {
        if (P.on_deck == 1)
            a->want_y = 0x46;
        if (a->want_y < 0x21)
            a->want_y = 0x21;
    }
    d4 = abs16((int16_t)(a->want_y - a->y));
    if (d4 > 100)
        d4 = 100;
    d4 = (int16_t)(d4 / 20);
    if (a->state & 4) {
        if (a->y > a->want_y) {
            a->y = (int16_t)(a->y + divs_w(a->climb, 100));
            a->climb = (int16_t)(a->climb - 10);
        } else if (a->y < a->want_y) {
            a->y = a->want_y;
        }
    }
    if (a->y > a->want_y) {
        int16_t step = (int16_t)wof_image16(0x0261F8u + 2u * (uint32_t)(int32_t)d4);

        a->y = (int16_t)(a->y - (int16_t)(step + (int16_t)wof_rand_mod(2)));
    } else if (a->y < a->want_y) {
        int16_t step = (int16_t)wof_image16(0x0261F8u + 2u * (uint32_t)(int32_t)d4);

        a->y = (int16_t)(a->y + (int16_t)(step + (int16_t)wof_rand_mod(2)));
    }
    if (!(a->state & 0x14) && a->turn_in != 0) {
        a->turn_in--;
        if (a->turn_in <= 0) {
            a->mode = (int16_t)(a->mode | 8);
            a->turn_in = 0;
        }
    }
    if ((a->mode & 8) && a->state == 2)
        aircraft_turn(a);
}

/* orig 0x01D9C6 fighter_cruise - a fighter (mode 1) by its relation.  Behind the player:
 * near and in his turn it times a turn; near, first in the order and free it goes onto his
 * tail (mode 2); near otherwise it takes his height and his airspeed less 0x46 a place;
 * far, and level, it closes at his airspeed plus the distance, 0x50 a place more for the
 * first and less for the others.  East of him the other way it slows, or turns; ahead the
 * same way it slows by a quarter of the distance, 0x46 more for every fighter ahead
 * before it this tick (0x027E66), jinks between heights 0x23 and 0x5F, and turns after
 * +0x10, on his turn, far ahead, or 8 to 13 ticks after a hit; west of him the other way
 * it takes a height 0x20 above or below his, times a turn, and turns. */
static void fighter_cruise(aircraft_t *a)
{
    switch (a->relation) {
    case 1:
        if (a->distance < 0xA0) {
            if (wof_g.attitude_index > 0 && wof_g.attitude_index < 6 && P.on_deck != 1 &&
                a->turn_in == 0) {
                a->turn_in = (int16_t)(divs_w((int16_t)(a->distance * 100), a->speed) +
                                       (int16_t)(a->order << 1));
                return;
            }
            if (a->distance < 0xA0 && a->turn_in == 0 && a->order == 1) {
                a->mode = (int16_t)((a->mode & 8) | 2);
                return;
            }
            a->firing = 0;
            a->want_y = P.y;
            a->want_speed = (int16_t)(wof_g.airspeed - (int16_t)(a->order * 0x46));
            return;
        }
        if (a->attitude == 0) {
            a->want_speed = (int16_t)(a->distance + wof_g.airspeed);
            if (a->order == 1)
                a->want_speed = (int16_t)(a->want_speed + (int16_t)(a->order * 0x50));
            else
                a->want_speed = (int16_t)(a->want_speed - (int16_t)(a->order * 0x50));
        }
        return;
    case 2:
        if (P.on_deck == 0 && wof_g.attitude_index > 0 && wof_g.attitude_index < 0x0B)
            a->want_speed = SPEED_MIN;
        else
            a->mode = (int16_t)(a->mode | 8);
        return;
    case 3:
        if (a->distance >= 0x600) {
            a->mode = (int16_t)(a->mode | 8);
            return;
        }
        a->timer--;
        if (a->timer <= 0 ||
            (wof_g.attitude_index > 0 && wof_g.attitude_index < 6) || P.on_deck == 1) {
            a->mode = (int16_t)(a->mode | 8);
            a->timer = 0;
            return;
        }
        if (a->hit == 1) {
            a->hit = 0;
            if (a->turn_in == 0)
                a->turn_in = (int16_t)(wof_rand_mod(6) + 8);
            a->timer = 0x226;
            return;
        }
        a->want_speed = (int16_t)(wof_g.airspeed - divs_w(a->distance, 4));
        a->want_speed = (int16_t)(a->want_speed + (int16_t)((int16_t)wof_g.g_027e66++ * 0x46));
        if (a->y == a->want_y)
            a->want_y = (int16_t)((int16_t)(wof_rand_mod(7) * 10) + 0x23);
        return;
    case 4:
        if (P.on_deck != 0)
            return;
        a->want_speed = SPEED_MIN;
        if (a->y >= P.y)
            a->want_y = (int16_t)(P.y + 0x20);
        else
            a->want_y = (int16_t)(P.y - 0x20);
        a->turn_in = divs_w((int16_t)(a->distance * 100), (int16_t)(a->speed + P.speed_x));
        a->mode = (int16_t)(a->mode | 8);
        return;
    default:
        return;
    }
}

/* orig 0x01DCCC fighter_attack - a fighter on the player's tail (mode 2).  Not behind him:
 * back to mode 1.  In his turn, or with him on the deck, it turns (mode 9) and times the
 * turn; else it keeps 0x82 behind at his airspeed and 0x32 more or less.  It takes his
 * height, and fires (+0x12) while first in the order, level, within 0xA0 and 8 of height,
 * behind him the same way; at his very height, every other tick (0x027346), unless 0x026F72
 * is set, it counts his +0x10 down, and at the end his oil falls by 8 and his fuel by a
 * draw below 32, and +0x10 starts again at 6 to 10. */
static void fighter_attack(aircraft_t *a)
{
    int16_t dy, dx, on, same;

    if (a->relation != 1) {
        a->mode = 1;
        return;
    }
    if (wof_g.attitude_index != 0 || P.on_deck == 1) {
        a->mode = 9;
        a->turn_in = divs_w(a->distance, divs_w(a->speed, 100));
    } else if (a->distance > 0x82) {
        a->want_speed = (int16_t)(wof_g.airspeed + 0x32);
    } else if (a->distance < 0x82) {
        a->want_speed = (int16_t)(wof_g.airspeed - 0x32);
    }
    a->want_y = P.y;
    dy = abs16((int16_t)(P.y - a->y));
    on = P.on_deck == 0 && a->mode == 2;
    same = P.facing == a->facing;
    dx = (int16_t)(a->x - P.x);
    if (on && a->order == 1 && dy < 8 && a->attitude == 0 && a->distance < 0xA0 && same &&
        (int16_t)(dx ^ P.facing) < 0) {
        a->firing = 1;
        if (!wof_g.g_026f72 && a->y == P.y && wof_g.g_027346) {
            P.w10--;
            if (P.w10 <= 0) {
                P.oil = (int16_t)(P.oil - 8);
                P.fuel = (int16_t)(P.fuel - (int16_t)wof_rand_mod(0x20));
                P.w10 = (int16_t)(wof_rand_mod(5) + 6);
            }
        }
    } else {
        a->firing = 0;
    }
}

/* orig 0x01DEA4 torpedo_plane - a torpedo plane (mode 4).  Chased from behind (relation 3)
 * a hit starts its evasion and +0x10 at 0x113; it keeps about 0x96 ahead (+0x28 then 0xF0
 * farther, and less 0x96 nearer, where it jinks), wanting the player's airspeed less that.
 * Otherwise it turns once 500 past either end of the carrier's deck (0x0253FC, 0x0253FE).
 * Over the last 0x3E8 before the deck it goes down to 0x14; over the deck, level at 0x14,
 * it drops its torpedo into object_record_extra and flies on (mode 0x10) with the enemy's
 * countdown at 500; elsewhere it turns when +0x10 runs out. */
static void torpedo_plane(aircraft_t *a)
{
    int16_t drop = 0;

    if (a->relation == 3) {
        if (a->hit == 1) {
            a->hit = 0;
            if (a->turn_in == 0)
                a->turn_in = (int16_t)(wof_rand_mod(6) + 8);
            a->timer = 0x113;
        }
        if (a->distance > 0x96)
            a->distance = 0xF0;
        if (a->distance < 0x96) {
            a->distance = (int16_t)(a->distance - 0x96);
            if (a->y == a->want_y)
                a->want_y = (int16_t)((int16_t)(wof_rand_mod(7) * 10) + 0x23);
        }
        a->want_speed = (int16_t)(wof_g.airspeed - a->distance);
    } else if (a->facing == -1 && a->x < (int16_t)(wof_g.g_0253fc - 0x1F4)) {
        a->mode = (int16_t)(a->mode | 8);
    } else if (a->facing == 1 && a->x > (int16_t)(wof_g.g_0253fe + 0x1F4)) {
        a->mode = (int16_t)(a->mode | 8);
    }
    if (a->facing == -1 && a->x > wof_g.g_0253fe &&
        (int16_t)(a->x - wof_g.g_0253fe) < 0x3E8)
        a->want_y = 0x14;
    else if (a->facing == 1 && a->x < wof_g.g_0253fc &&
             (int16_t)(wof_g.g_0253fc - a->x) < 0x3E8)
        a->want_y = 0x14;
    if ((a->facing == -1 && a->x > wof_g.g_0253fe) || (a->facing == 1 && a->x < wof_g.g_0253fc))
        drop = 1;
    if (drop) {
        if (a->y == 0x14 && a->attitude == 0) {
            wof_object_t *e = &wof_m.object_record_extra[0];
            int32_t       sx = (int32_t)a->speed * 0x28F;              /* muls.w */

            e->type = 2;
            e->l12 = 0;
            e->y = (int16_t)(a->y + 0x0F);                            /* (y + 0x0F) << 16 */
            e->w06 = 0;
            e->x = a->x;                                              /* x << 16 */
            e->w02 = 0;
            e->b1f = (int8_t)(uint8_t)a->facing;
            if ((uint8_t)e->b1f == 0xFF)
                sx = -sx;
            e->speed_x = (int16_t)(uint16_t)((uint32_t)sx >> 16);
            e->w10 = (int16_t)(uint16_t)(uint32_t)sx;
            e->kind = 0xFF;
            e->frame = 0;
            a->state = 2;
            a->want_speed = (int16_t)(SPEED_MAX / 2);
            a->want_y = 0x3C;
            a->mode = 0x10;
            P.enemy_countdown = 500;
        }
    } else {
        a->timer--;
        if (a->timer <= 0) {
            a->mode = (int16_t)(a->mode | 8);
            a->timer = 0;
        }
    }
}

/* orig 0x01E17A torpedo_plane_away - a torpedo plane that has dropped (mode 0x10): freed far
 * away (0x01D18C); else, level, chased from behind a hit starts its evasion and +0x10 at
 * 0x226, or near it jinks between 0x19 and 0x53; behind the player it turns. */
static void torpedo_plane_away(aircraft_t *a)
{
    if (aircraft_gone_far(a))
        return;
    if (a->attitude != 0)
        return;
    if (a->relation == 3) {
        if (a->hit == 1) {
            a->hit = 0;
            if (a->turn_in == 0)
                a->turn_in = (int16_t)(wof_rand_mod(6) + 8);
            a->timer = 0x226;
        } else if (a->y == a->want_y && a->distance < 0xA0) {
            a->want_y = (int16_t)((int16_t)(wof_rand_mod(7) * 10) + 0x19);
        }
    } else if (a->relation == 1) {
        a->mode = (int16_t)(a->mode | 8);
    }
}

/* orig 0x01E244 aircraft_falling - shot down (state 4): smoke by its damage; on the ground
 * (at +0x24) it slides: over the sea and slower than 0x12C it skids (+0x24 one lower every
 * second tick, 0x18 of speed back), 0x23 slower each tick, soldiers within 0x14 die, faster
 * than 500 it hits the record under it, and it splashes; below 100 of speed the enemy
 * plane counter counts it, and on land it burns (state 0x10, +0x1E 6, +0x1C 0x1E),
 * elsewhere it is freed (one fighter fewer up unless a torpedo plane). */
static void aircraft_falling(aircraft_t *a)
{
    int16_t  damage = (int16_t)(0x80 - a->health);
    uint32_t at;

    if (damage > (int16_t)(wof_rand_beam(0x01E256) & 0x3F))
        wof_burn_smoke(1, (int16_t)((int16_t)(damage >> 3) + 1), (int16_t)(a->x - 0x10),
                       (int16_t)(a->y + 0x0A));
    if (a->y != a->want_y)
        return;
    at = wof_record_at(a->x);
    if (wof_on_water(at) && a->speed < 0x12C) {
        wof_g.skid_count++;
        if (wof_g.skid_count >= 2) {
            wof_g.skid_count = 0;
            a->want_y--;
        }
        a->speed = (int16_t)(a->speed + 0x18);
    }
    a->speed = (int16_t)(a->speed - 0x23);
    wof_soldiers_hit(a->x, 0x14);                                   /* 0x011A84 */
    if (a->speed > 0x1F4)
        wof_crash_hit(at);
    wof_splash_spawn((int16_t)((int16_t)(a->facing << 2) + a->x));   /* 0x0152AC */
    if (a->speed >= 0x64)
        return;
    wof_g.g_02537f++;
    if (wof_record_is_land(at) && at < wof_m.map_records_end[0].off) {
        a->state = 0x10;
        a->want_speed = 6;
        a->speed = 0x1E;
        a->mode = 0;
        return;
    }
    if (a->mode != 4 && a->mode != 0x10)
        wof_g.fighters_up--;
    a->state = 0;
    a->mode = 0;
}

/* orig 0x01E3E8 aircraft_burning - a wreck burning on land (state 0x10): the wreck's frame
 * (0x1B facing west, 0x37 east); +0x1E counts down, +0x1C five times it between steps,
 * smoke every fourth tick while +0x1E is above 1; then its word into the wrecks' list
 * (0x0251DA, its x negated facing west, written by address past the forty words as the
 * original's is) and the record freed, one fighter fewer up. */
static void aircraft_burning(aircraft_t *a)
{
    a->frame = a->facing == -1 ? 0x1B : 0x37;
    a->speed--;
    if (a->speed == 0) {
        a->want_speed--;
        a->speed = (int16_t)(a->want_speed * 5);
    }
    if (a->want_speed > 1) {
        if (!(a->speed & 3))
            wof_burn_smoke(1, a->want_speed, (int16_t)(a->x - 4), 6);
        return;
    }
    wof_original_store16(0x0251DAu + 2u * (uint32_t)(int32_t)wof_g.wreck_count++,
                         (uint16_t)(int16_t)(a->facing * a->x));
    if (a->mode != 4 && a->mode != 0x10)
        wof_g.fighters_up--;
    a->state = 0;
    a->mode = 0;
}

/* orig 0x01E4C8 aircraft_idle - state 1: nothing. */
static void aircraft_idle(aircraft_t *a)
{
    (void)a;
}

/* orig 0x01E4D0 aircraft_launch - an aircraft of `kind` (1 a torpedo plane, 0 a fighter)
 * into the last free record, a torpedo plane only while none is in the air: state 2, the
 * facing and x given, +0x24 0x32, both speeds 900, health 0xF0, a burst of 5 to 7, the rest
 * cleared; a torpedo plane mode 4 at height 0x32, a fighter mode 1 at the height given and
 * one more up. */
void wof_aircraft_launch(int16_t kind, int16_t x, int16_t height, int16_t facing)
{
    int16_t free = -1, torpedo = 0;
    aircraft_t *a;

    for (int16_t i = 0; i < 4; i++) {
        if (wof_m.aircraft_records[i].state == 0)
            free = i;
        if ((wof_m.aircraft_records[i].mode & 4) && wof_m.aircraft_records[i].state != 0)
            torpedo = 1;
    }
    if (free == -1 || (kind != 0 && torpedo))
        return;
    a = &wof_m.aircraft_records[free];
    a->state = 2;
    a->facing = facing;
    a->x = x;
    a->want_y = 0x32;
    a->want_speed = SPEED_MIN;
    a->speed = SPEED_MIN;
    a->health = 0xF0;
    a->burst = (int16_t)(wof_rand_mod(3) + 5);
    a->hit = 0;
    a->relation = 0;
    a->turn_in = 0;
    a->attitude = 0;
    a->order = 0;
    if (kind != 0) {
        a->mode = 4;
        a->y = 0x32;
    } else {
        wof_g.fighters_up++;
        a->mode = 1;
        a->y = height;
    }
}

/* orig 0x01E64E aircraft_speed - while flying, +0x1E within 900 and 0xA28, and +0x1C half the
 * way to it and 5 more, within the same limits. */
static void aircraft_speed(aircraft_t *a)
{
    if (a->state != 2)
        return;
    if (a->want_speed < SPEED_MIN)
        a->want_speed = SPEED_MIN;
    if (a->want_speed > SPEED_MAX)
        a->want_speed = SPEED_MAX;
    if (a->speed < a->want_speed) {
        a->speed = (int16_t)(a->speed + (int16_t)(divs_w((int16_t)(a->want_speed - a->speed), 2) + 5));
        if (a->speed > SPEED_MAX)
            a->speed = SPEED_MAX;
    } else if (a->speed > a->want_speed) {
        a->speed = (int16_t)(a->speed - (int16_t)(divs_w((int16_t)(a->speed - a->want_speed), 2) - 5));
        if (a->speed < SPEED_MIN)
            a->speed = SPEED_MIN;
    }
}

/* orig 0x01E728 aircraft_fly - state 2: smoke by its damage, then the flight of its mode,
 * bit 3 (the turn) aside. */
static void aircraft_fly(aircraft_t *a)
{
    int16_t damage = (int16_t)(0x80 - a->health);

    if (damage > (int16_t)(wof_rand_beam(0x01E73A) & 0x3F))
        wof_burn_smoke(1, (int16_t)((int16_t)(damage >> 3) + 1), a->x, (int16_t)(a->y + 0x0B));
    switch (a->mode & ~8) {
    case 1:
        fighter_cruise(a);
        break;
    case 2:
        fighter_attack(a);
        break;
    case 4:
        torpedo_plane(a);
        break;
    case 0x10:
        torpedo_plane_away(a);
        break;
    default:
        break;
    }
}

/* orig 0x01E7D6 enemy_aircraft_step - every record in use: its relation and the order, then
 * by its state 1 nothing, 2 its flight (and +0x24 at least 0x21 unless a torpedo plane),
 * 4 its fall, 8 nothing, 0x10 its burning; then, whatever the state has become, its
 * speed, its motion unless burning, and its frame. */
void wof_enemy_aircraft_step(void)
{
    wof_g.g_027e66 = 0;
    for (int16_t i = 0; i < 4; i++) {
        aircraft_t *a = &wof_m.aircraft_records[i];

        if (a->state == 0)
            continue;
        aircraft_relation(a);
        aircraft_order();
        switch (a->state) {
        case 1:
            aircraft_idle(a);
            break;
        case 2:
            aircraft_fly(a);
            if (!(a->mode & 4) && a->want_y < 0x21)
                a->want_y = 0x21;
            break;
        case 4:
            aircraft_falling(a);
            break;
        case 8:
            break;
        case 0x10:
            aircraft_burning(a);
            break;
        default:
            break;
        }
        aircraft_speed(a);
        if (a->state != 0x10)
            aircraft_motion(a);
        wof_aircraft_frame_index(a);
    }
}

#ifdef WOF_TRACE
/* The oracle tests' entry (tests/test_oracle_m6.py): a routine of the module by its
 * original address, on the port's state as the test left it; `a` names the record by its
 * place in aircraft_records, and aircraft_launch takes its four words from a, b and c
 * (height in c's upper word, facing in its lower). */
int32_t wof_test_enemy_call(uint32_t orig, int32_t a, int32_t b, int32_t c, int32_t *out)
{
    aircraft_t *r = &wof_m.aircraft_records[a & 3];

    (void)out;
    switch (orig) {
    case 0x01D18C: return aircraft_gone_far(r);
    case 0x01D35A: wof_aircraft_frame_index(r); return 0;
    case 0x01D3B4: aircraft_relation(r); return 0;
    case 0x01D476: aircraft_order(); return 0;
    case 0x01D530: aircraft_turn_step(r); return 0;
    case 0x01D562: aircraft_turn(r); return 0;
    case 0x01D796: aircraft_motion(r); return 0;
    case 0x01D9C6: fighter_cruise(r); return 0;
    case 0x01DCCC: fighter_attack(r); return 0;
    case 0x01DEA4: torpedo_plane(r); return 0;
    case 0x01E17A: torpedo_plane_away(r); return 0;
    case 0x01E244: aircraft_falling(r); return 0;
    case 0x01E3E8: aircraft_burning(r); return 0;
    case 0x01E4C8: aircraft_idle(r); return 0;
    case 0x01E4D0: wof_aircraft_launch((int16_t)a, (int16_t)b, (int16_t)(c >> 16), (int16_t)c);
                   return 0;
    case 0x01E64E: aircraft_speed(r); return 0;
    case 0x01E728: aircraft_fly(r); return 0;
    case 0x01E7D6: wof_enemy_aircraft_step(); return 0;
    default:       return -1000;
    }
}
#endif
