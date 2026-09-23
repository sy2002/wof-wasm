/* The four pools of alloc_pools (M5): Smoke, Splashes and Balloons as the pass draws and
 * moves them, and the claims both trees share, in the original's address order
 * (re/notes/objects.md, "The inventory"; re/notes/porting-m5.md, "The pools").
 *
 * Ricochet is not here: its only writer, 0x011A14, has no caller in the executable, so the
 * pool keeps what alloc_pools gave it (re/notes/porting-m5.md, "The left-overs").
 */
#include "wof.h"

enum { T_WORLD, T_EIGHTH, T_MASTER, T_ATH };

#define carrier (wof_m.ship_records[4])

/* orig 0x010EE0 - the Smoke pool: every record in use drawn from MasterList at its
 * whole-pixel position with frame 0x60 + its kind (in the eighth-scale view from AthList,
 * 0x61 for a kind of 3 or less, else 0x62), then moved by its velocity; every seventh pass
 * its kind counts down, and at 0 the record is free.  Clipped at the carrier's waterline
 * while 0x025394 is set. */
void wof_smoke_draw(void)
{
    int16_t saved = wof_g.clip_bottom;
    int     table = wof_g.view_step == 8 ? T_MASTER : T_ATH;

    if (wof_g.g_025394 != 0)
        wof_g.clip_bottom = (int16_t)(0x84 + wof_g.g_026e56 + carrier.row);
    for (int i = 0; i < 40; i++) {
        wof_smoke_t *s = &wof_m.smoke_records[i];
        int16_t      d2 = s->kind;

        if (d2 == 0)
            continue;
        if (wof_g.view_step == 1)
            d2 = d2 <= 3 ? 1 : 2;
        d2 = (int16_t)(d2 + 0x60);
        wof_draw_world_shape(table, d2, (int16_t)((uint32_t)s->x >> 16),
                             (int16_t)((uint32_t)s->y >> 16));
        s->x = (int32_t)((uint32_t)s->x + (uint32_t)s->dx);
        s->y = (int32_t)((uint32_t)s->y + (uint32_t)s->dy);
        if (--s->timer >= 0)
            continue;
        s->timer = 6;
        s->kind--;
    }
    wof_g.clip_bottom = saved;
}

/* orig 0x0152B0 splash_spawn - a splash at world x D0: the first record of the Splashes pool
 * whose count is 0, with the low bits of the map record under it, and six passes to run, or
 * four on land (low bits 2), which draws the dust of a bullet.  With all twenty in use
 * nothing happens. */
void wof_splash_spawn(int16_t x)
{
    for (int i = 0; i < 20; i++) {
        wof_splash_t *s = &wof_m.splash_records[i];
        uint16_t      slot;

        if (s->count)
            continue;
        s->x = x;
        s->kind = (uint8_t)wof_map_slot_at(x, &slot);
        s->count = s->kind == 2 ? 4 : 6;                 /* 0x0152D8: the dust on land */
        return;
    }
}

/* orig 0x0152F8 splashes_draw - the Splashes pool: each record whose count runs is drawn from world_shapes (eighth_shapes in the eighth-scale view) at
 * its x, frame 0x67 plus the count at height 0x0D in the water, or 0x6E, the dust, at
 * height 9 on land; then its count falls by one. */
void wof_splashes_draw(void)
{
    int table = wof_g.view_step == 8 ? T_WORLD : T_EIGHTH;

    for (int i = 0; i < 20; i++) {
        wof_splash_t *s = &wof_m.splash_records[i];
        int16_t       d1 = 0x0D, d2;

        if (s->count == 0)
            continue;
        if (s->kind == 2) {
            d2 = 0x6E;
            d1 = (int16_t)(d1 - 4);
        } else {
            d2 = (int16_t)(uint8_t)(0x67 + s->count);             /* add.b */
        }
        wof_draw_world_shape(table, d2, s->x, d1);
        s->count--;
    }
}

/* orig 0x015460 smoke_claim - a puff of smoke: the first free record of the Smoke pool at
 * (x, y) in 16.16, y raised to 16 when below, of the kind in D2, drifting by two draws of rand_beam;
 * with all forty in use nothing happens.  Returns what D0 holds at the end: the second
 * drift, whose upper word is 1, or x when nothing was claimed (0x013DE8 carries it). */
uint32_t wof_smoke_claim(int32_t x, int32_t y, int16_t kind)
{
    for (int i = 0; i < 40; i++) {
        wof_smoke_t *s = &wof_m.smoke_records[i];
        uint32_t     d0;

        if (s->kind)
            continue;
        s->x = x;
        if (y < 0x100000)
            y = 0x100000;                                /* 0x01548A: at least the ground's line */
        s->y = y;
        s->kind = kind;
        s->timer = 6;
        d0 = (wof_rand_beam(0x015460) & 0xFFFFu) + 0x10000u;
        s->dx = (int32_t)d0;
        d0 = (wof_rand_beam(0x015460) & 0xFFFFu) + 0x10000u;
        s->dy = (int32_t)d0;
        return d0;
    }
    return (uint32_t)x;
}

/* orig 0x0154E0 smoke_at_player - a puff of the kind in D0 at the drawing's player: x the
 * long at draw_player_x ten pixels ahead (the word behind draw_player_x, its fraction, is
 * never written and stays 0), y the long at draw_player_y plus 13; while the aircraft
 * turns (attitude 9 to 17) x moves by a byte of smoke_turn (0x024BF0) in D2's low word,
 * backwards on one side of the turn, and the upper word D2 came with, negated with it,
 * becomes the move's fraction (`neg.l`, `swap`).  The caller says what that upper word
 * is: target_fire leaves rand_beam's constant upper word there when the target is farther
 * than the aircraft is high, else 0. */
void wof_smoke_at_player(int16_t kind, uint16_t d2_high)
{
    uint32_t d0 = ((uint32_t)(uint16_t)wof_g.draw_player_x << 16) |
                  (uint16_t)wof_g.draw_player_x_frac;
    uint32_t d1 = 0xA0000u;
    int16_t  a = wof_g.attitude_index;

    if (wof_m.player[0].facing < 0)
        d1 = (uint32_t)-(int32_t)d1;
    d0 += d1;
    d1 = (((uint32_t)(uint16_t)wof_g.draw_player_y << 16) | (uint16_t)wof_g.g_026e62) + 0xD0000u;
    if (a != 0 && a > 8 && a < 0x12) {
        uint32_t d2 = ((uint32_t)d2_high << 16) |
                      (uint16_t)(wof_image8(0x024BF0u + (uint32_t)(uint16_t)(a - 8)) & 0x0Fu);
        int16_t  w = (int16_t)(uint16_t)d2;
        int      negate;

        if (wof_m.player[0].facing < 0)
            negate = !(w > 0x0B);
        else
            negate = w < 0x0B;
        if (negate)
            d2 = (uint32_t)-(int32_t)d2;
        d2 = (d2 << 16) | (d2 >> 16);                                 /* swap */
        d0 += d2;
    }
    wof_smoke_claim((int32_t)d0, (int32_t)d1, kind);
}

/* orig 0x01557C balloons_draw - the balloons, while balloons_on (0x02535D) is set at full
 * scale: every record not yet in use is released over the carrier at player_start_x - 0x74
 * and height 0x38 (the whole words; the fractions stay), with a colour of rand_beam's bits
 * 12 and 13 less one (0 counting as 2) and a drift of twice a draw of rand_beam plus one in
 * 16.16 both ways; each is drawn from MasterList, frame 0x0C plus its colour. */
void wof_balloons_draw(void)
{
    if (!wof_g.balloons_on || wof_g.view_step != 8)
        return;
    for (int i = 0; i < 20; i++) {
        wof_balloon_t *b = &wof_m.balloon_records[i];

        if (!b->in_use) {
            uint16_t d0;

            b->x = (int32_t)(((uint32_t)(uint16_t)(wof_g.player_start_x - 0x74) << 16) |
                             ((uint32_t)b->x & 0xFFFFu));
            b->y = (int32_t)((0x38u << 16) | ((uint32_t)b->y & 0xFFFFu));
            d0 = (uint16_t)wof_rand_beam(0x01557C);
            d0 = (uint16_t)((uint16_t)(d0 << 4) | (uint16_t)(d0 >> 12));   /* rol.w #4 */
            d0 &= 3u;
            if (d0 == 0)
                d0 = 2;
            b->frame = (int8_t)(d0 - 1);
            b->dx = (int32_t)(((wof_rand_beam(0x01557C) & 0xFFFFu) << 1) + 0x10000u);
            b->dy = (int32_t)(((wof_rand_beam(0x01557C) & 0xFFFFu) << 1) + 0x10000u);
            b->in_use = 0xFF;
        }
        wof_draw_world_shape(T_MASTER, (int16_t)(uint8_t)(0x0C + (uint8_t)b->frame),
                             (int16_t)((uint32_t)b->x >> 16), (int16_t)((uint32_t)b->y >> 16));
    }
}
