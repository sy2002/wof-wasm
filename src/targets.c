/* The ground targets and the soldiers (M5): what the pass draws of them and does with them,
 * in the original's address order (re/notes/porting-m5.md, "The targets and the soldiers").
 *
 * The islands carry three kinds of target in the map's records: slot 3, a dug-out that holds
 * soldiers and fires at the aircraft (target_records_3); slot 4, a barracks that holds
 * soldiers and burns once bombed, when its records become slot 5 (target_records_4); and
 * slots 0x0F to 0x1E, a pillbox that fires and that only a rocket destroys
 * (target_records_f).  island_score keeps per island the soldiers still alive and the
 * pillboxes still standing; when both are 0 the island is neutralised, and the last island
 * of the map ends the mission (0x015694, whose sequel is M7's).  The pass moves the soldiers,
 * kills them with their score, draws the targets with their fire and the islands' flags.
 *
 * The routines are hand-written assembly and pass values in registers; where a register
 * crosses a call, the C passes it as an argument and says which register it was.
 */
#include "wof.h"

enum { T_WORLD, T_EIGHTH, T_MASTER, T_ATH };

/* A word of the original's memory at a fixed address: a registered global where one covers
 * it, the executable's DATA image elsewhere (the constant tables). */
static int16_t word_at(uint32_t addr)
{
    return (int16_t)wof_image16(addr);
}

/* island_score as the original addresses it, a word at a byte offset (0x025450). */
static uint16_t *island_word(uint16_t byte_offset)
{
    return &wof_g.island_score[(byte_offset >> 1) & 7u];
}

/* ------------------------------------------------------------ 0x011E82, a soldier out */

/* orig 0x011E82 - a soldier comes out of target A0.  D0 1: into the first free record of the
 * soldier table, running in direction D1, or by the low byte of vblank_total when D1 is 0,
 * from the target's east end when that byte is positive and its west end otherwise, one to
 * seven pixels on by the byte's low bits.  D0 2: the direction from the island's span, east
 * from its first target, west from its last, none from any other, turned round when the
 * top bits of the fourth of four draws of rand_beam are all clear (a dug-out's soldier). */
void wof_soldier_out(const wof_gtarget_t *t, uint8_t d0, int16_t d1_in)
{
    int16_t d3 = d1_in;

    if (d0 == 2) {
        uint16_t i = (uint16_t)(t->island * 4u);
        uint16_t d1 = (uint16_t)t->map_offset;
        uint16_t r = 0;

        if (d1 == wof_g.island_span[(i >> 1) & 7u])
            d3 = 1;
        else if (d1 == wof_g.island_span[((i >> 1) + 1u) & 7u])
            d3 = -1;
        else
            d3 = 0;
        for (int k = 0; k < 4; k++)
            r = (uint16_t)wof_rand_beam(0x011E82);
        r = (uint16_t)((uint16_t)(r << 1) | (uint16_t)(r >> 15));        /* rol.w #1 */
        if ((r & 0x1Fu) == 0)
            d3 = (int16_t)-d3;
    } else if (d0 != 1) {
        return;
    }
    if (wof_g.soldier_count == 0)
        return;                                      /* the one dbra runs out at once */
    for (uint16_t n = 0;; n++) {
        wof_soldier_t *s = &wof_m.soldier_records[n];
        uint8_t        dir;
        int16_t        x;
        uint8_t        d2;

        /* The walk passes a record in use with `addq.l #8,a1; bra`, not through the dbra,
         * so it has no end: it stops at the first free record, past the table if none is
         * free there.  That never happens, because the soldiers inside the targets and the
         * records in use always add up to the table's size, five per target
         * (re/notes/porting-m5.md). */
        if (n >= wof_g.soldier_count || n >= 160) {
            WOF_STANDIN("M5 STAND-IN: every soldier record in use, 0x011E82 walks past the table");
            return;
        }
        if (s->state != 0)
            continue;
        s->state = 1;
        x = t->x0;
        s->island = t->island;
        dir = (uint8_t)d3;
        if (dir == 0)
            dir = (uint8_t)wof_g.vblank_total;
        s->dir = (int8_t)dir;
        if (!(dir & 0x80u))
            x = t->x1;
        d2 = (uint8_t)(dir & 7u);
        s->frame = (uint8_t)(d2 & 3u);
        s->x = (int16_t)(x + (int16_t)(d2 * 4u));
        return;
    }
}

/* -------------------------------------------------------- 0x013B52, an island's flag */

/* orig 0x013B52 - the flag of an island (a record of slot 0x113) at full scale: the island
 * is the first whose slot-2 record lies east of the drawing's player (island_slot2 walked
 * by the unsigned word compare, with no bound); while it has soldiers alive or pillboxes
 * standing the flag waves, a frame of 0xB0 to 0xB2 stepped down on every draw, else the
 * bare post 0xB3.  D4 is the record's screen x, the table D7's. */
void wof_island_flag(int table, int16_t d4)
{
    uint16_t d1 = (uint16_t)((uint16_t)wof_g.draw_player_x >> 2);
    uint16_t d0 = 0;
    int16_t  d2 = 0xB3;

    while (!(d1 < (uint16_t)word_at(0x025438u + 2u * d0)))
        d0++;
    d0 = (uint16_t)(d0 * 4u);
    if (word_at(0x025450u + d0) != 0 || word_at(0x025452u + d0) != 0) {
        if ((int8_t)--wof_g.flag_frame < 0)
            wof_g.flag_frame = 2;
        d2 = (int16_t)(0xB0 + wof_g.flag_frame);
    }
    wof_draw_at(wof_table_entry(table, d2), (int16_t)(d4 - 8), wof_g.split_row);
}

/* ------------------------------------------------------------ 0x013D78, the dug-outs */

/* orig 0x013D78 - the slot-3 targets: one that holds no soldier (+8 clear) counts +0x0E
 * down and at its end, 200 passes on, takes one from the nearest barracks (0x014FEE); one
 * whose +0x0C runs counts it down and shows nothing meanwhile; the others show the frame
 * 0x014D50 gives them at their world x and height 0x14, and may hit the aircraft. */
void wof_targets_3_draw(int table)
{
    for (uint16_t i = 0; i < wof_g.target_count_3 && i < 16; i++) {
        wof_gtarget_t *t = &wof_m.target_records_3[i];
        int16_t        x, frame;

        if (t->state == 0) {
            if (--t->w0e > 0)
                continue;
            t->w0e = 0xC8;
            wof_target_refill(t);
            continue;
        }
        if (t->w0c != 0) {
            if (--t->w0c != 0)
                continue;
        }
        x = (int16_t)(uint16_t)((uint16_t)t->map_offset << 2);
        frame = wof_target_frame(x);
        if (frame < 0)
            continue;
        wof_draw_world_shape(table, frame, x, 0x14);
        wof_target_fire(x);
    }
}

/* orig 0x013DE8 - the pillboxes: a destroyed one (+8 set) whose +0x0A has not run out
 * smokes, a puff every 0x32 - +0x0A passes as +0x0A counts down, at its x + 8 and y 0x11 in
 * 16.16 (the moveq #$32 before it leaves D0's upper word 0, so the fraction is 0); a
 * standing one shows its frame at height 0x16 and may hit the aircraft. */
void wof_targets_f_draw(int table)
{
    for (uint16_t i = 0; i < wof_g.target_count_f && i < 32; i++) {
        wof_gtarget_f_t *t = &wof_m.target_records_f[i];
        int16_t          x, frame;

        x = (int16_t)(uint16_t)((uint16_t)t->map_offset << 2);
        if (t->state != 0) {
            if (t->w0a == 0)
                continue;
            if (--t->w0c > 0)
                continue;
            if (--t->w0a == 0)
                continue;
            t->w0c = (int16_t)(0x32 - t->w0a);
            wof_smoke_claim((int32_t)((uint32_t)(uint16_t)(x + 8) << 16), 0x110000, 5);
            continue;
        }
        frame = wof_target_frame(x);
        if (frame < 0)
            continue;
        wof_draw_world_shape(table, frame, x, 0x16);
        wof_target_fire(x);
    }
}

/* ------------------------------------------------------------ 0x013EEE, the soldiers */

/* orig 0x013EEE soldiers_draw - every soldier record in use, in the pass: a running one (1)
 * steps its frame 0 to 4 and runs three pixels a pass, turning round at the water; a dying
 * one (2) steps its frame every third pass and after frame 7 is dead (3), which scores 25
 * and takes one off its island's soldiers, and the last of the island's soldiers, with no
 * pillbox left, neutralises it: the bonus of 0x015AE8, one island fewer, and the ticker's
 * message; the map's last island ends the mission (0x015694) and ends this walk.  Each is
 * drawn from MasterList at full scale (frames 0x6F on, nine more running west) or AthList,
 * and a running one that reaches a dug-out goes in. */
void wof_soldiers_draw(void)
{
    for (uint16_t n = 0; n < wof_g.soldier_count && n < 160; n++) {
        wof_soldier_t *s = &wof_m.soldier_records[n];
        int16_t        d2;
        int            table;

        if (s->state == 0)
            continue;
        if (s->state == 3) {
            /* dead: drawn */
        } else if (s->state == 2) {
            if (--s->timer < 0) {
                s->timer = 2;
                s->frame++;
                if (s->frame > 7) {
                    uint16_t d0 = (uint16_t)(s->island * 4u);
                    uint16_t *alive = island_word(d0);

                    s->state = 3;
                    wof_g.player_score += 0x19;
                    wof_g.soldiers_killed++;
                    if (--*alive == 0 && *island_word((uint16_t)(d0 + 2u)) == 0) {
                        uint32_t bonus = (uint16_t)wof_island_bonus(s->island);

                        wof_g.player_score += bonus;
                        if ((int8_t)--wof_g.islands_left > 0 || wof_g.ships_left != 0) {
                            wof_ticker_say(0x0239FAu, bonus);
                        } else {
                            wof_ticker_format(0x0239FAu, bonus, 0);
                            wof_mission_won();
                            return;
                        }
                    }
                }
            }
        } else {
            int16_t  d0;
            uint16_t slot;

            if (++s->frame > 4)
                s->frame = 0;
            d0 = s->dir < 0 ? -3 : 3;
            if (wof_map_slot_at((int16_t)(s->x + d0), &slot) == 0) {
                d0 = (int16_t)-d0;
                s->dir = (int8_t)-s->dir;
            }
            s->x = (int16_t)(s->x + d0);
        }

        d2 = s->frame;
        if (wof_g.view_step != 8) {
            if (s->state == 3)
                continue;
            d2 = (int16_t)((d2 & 1) + 1);
        }
        d2 = (int16_t)(d2 + 0x6F);
        if (s->dir < 0 && wof_g.view_step != 1)
            d2 = (int16_t)(d2 + 9);
        table = T_MASTER;
        if (wof_g.view_step != 8) {
            table = T_ATH;
            d2--;
        }
        wof_draw_world_shape(table, d2, s->x, 0x0C);
        if (s->state == 1) {
            uint16_t slot;
            wof_gtarget_t *t;

            wof_map_slot_at(s->x, &slot);
            if (slot != 3 || s->x < 0)
                continue;
            t = (wof_gtarget_t *)wof_target_of(s->x);
            if (!t)
                continue;
            if (t->w0c == 0 && t->state == 0)
                t->w0c = 0x168;
            t->state++;
            s->state = 0;
        }
    }
}

/* ------------------------------------------------ 0x014AE4 to 0x014B54, a target found */

/* orig 0x014AE4 - the four map records of the target at world x D0: the first of the
 * records at x - 8, x, x + 8 and x + 16 that carries the draw bit is the target's third, and
 * A0 to A3 are its four records as byte offsets into the map, all 0 when none does. */
int wof_target_records(int16_t x, uint16_t out[4])
{
    int16_t d3 = (int16_t)((((uint16_t)x >> 2) & 0xFFFEu) - 2u);

    for (int k = 0; k < 4; k++) {
        uint16_t rec = (uint32_t)(uint16_t)d3 >> 1 < 3576u ?
                       wof_m.map_records[(uint16_t)d3 >> 1].v : 0;

        if (rec & 0x8000u) {
            out[0] = (uint16_t)(d3 - 4);
            out[1] = (uint16_t)(d3 - 2);
            out[2] = (uint16_t)d3;
            out[3] = (uint16_t)(d3 + 2);
            return 1;
        }
        d3 = (int16_t)(d3 + 2);
    }
    out[0] = out[1] = out[2] = out[3] = 0;
    return 0;
}

/* orig 0x014B54 - the target record at world x D0: its draw record found by 0x014AE4 (none
 * is -1), then by the slot under x the table searched for that record's offset, count + 1
 * entries as the dbra runs: slot 5, a burnt barracks, in target_records_4; slot 3 in
 * target_records_3; slots 0x0F to 0x1E in target_records_f.  Returns the record or 0. */
void *wof_target_of(int16_t x)
{
    uint16_t r[4], slot, d2;

    wof_target_records(x, r);
    {
        int found = -1;

        for (int k = 0; k < 4; k++) {
            uint16_t off = r[k];
            uint16_t rec = (off >> 1) < 3576u ? wof_m.map_records[off >> 1].v : 0;

            if (rec & 0x8000u) {
                found = k;
                break;
            }
        }
        if (found < 0)
            return 0;
        d2 = r[found];
    }
    wof_map_slot_at(x, &slot);
    slot &= 0x1FFFu;
    if (slot == 5) {
        for (uint16_t i = 0; i <= wof_g.target_count_4 && i < 16; i++)
            if (wof_m.target_records_4[i].map_offset == d2)
                return &wof_m.target_records_4[i];
        return 0;
    }
    if (slot == 3) {
        for (uint16_t i = 0; i <= wof_g.target_count_3 && i < 16; i++)
            if (wof_m.target_records_3[i].map_offset == d2)
                return &wof_m.target_records_3[i];
        return 0;
    }
    if ((int16_t)slot >= 0x0F && (int8_t)slot <= 0x1E) {
        for (uint16_t i = 0; i <= wof_g.target_count_f && i < 32; i++)
            if ((uint16_t)wof_m.target_records_f[i].map_offset == d2)
                return &wof_m.target_records_f[i];
        return 0;
    }
    return 0;
}

/* --------------------------------------------- 0x014D50 to 0x014F5C, a target's fire */

/* orig 0x014D50 - the frame a target shows this pass: none while the aircraft is on the
 * deck; in the eighth-scale view 0x5A on a coin of rand_beam's top bit; at full scale the
 * frame 0x014DB8 gives for its distance and the drawing's height, plus 0x81, and seven more
 * (the firing frame) when the top nibble of a draw of rand_beam is 5 or less.  D0 is the
 * target's world x.  Returns the frame, or -1. */
int16_t wof_target_frame(int16_t x)
{
    int16_t d2;

    if (wof_m.player[0].on_deck != 0)
        return -1;
    if (wof_g.view_shift) {
        uint16_t r = (uint16_t)wof_rand_beam(0x014D50);

        return (r & 0x8000u) ? 0x5A : -1;
    }
    d2 = wof_target_range_frame(x, wof_g.draw_player_x, wof_g.draw_player_y);
    if (d2 < 0)
        return d2;
    d2 = (int16_t)(d2 + 0x81);
    {
        uint16_t r = (uint16_t)wof_rand_beam(0x014D50);

        r = (uint16_t)((uint16_t)(r << 4) | (uint16_t)(r >> 12));        /* rol.w #4 */
        if ((int16_t)(r & 0x0Fu) <= 5)
            d2 = (int16_t)(d2 + 7);
    }
    return d2;
}

/* orig 0x014DB8 - the frame by distance and height, D0 the target's x, D1 the aircraft's,
 * D2 its height: in the eighth-scale view 0; at full scale none for a target more than
 * 0x200 pixels away (`sub.w d0,d1` and `bgt` decide on the exact difference, the compares
 * with 0x200 on the 16-bit one), else an entry of range_frames (0x024C1C) by height in
 * steps of 32 and distance in steps of 40, read by address: the index can fall outside the
 * 48 bytes, into the constants around them. */
int16_t wof_target_range_frame(int16_t d0, int16_t d1, int16_t d2)
{
    int32_t diff = (int32_t)d1 - d0;
    int16_t w = (int16_t)diff;

    if (wof_g.view_step == 1)
        return 0;
    if (diff > 0 ? w > 0x200 : w < -0x200)
        return -1;
    if (wof_g.view_step == 1)
        return 0;
    {
        int16_t row = (int16_t)((int16_t)((d2 >> 5) - 1) << 3);
        int16_t col = (int16_t)((int32_t)w / 0x28 + 3);                /* divs.w: toward zero */

        return (int16_t)wof_image8(0x024C1Cu + (uint32_t)(int32_t)(int16_t)(row + col));
    }
}

/* orig 0x014E18 - a burnt barracks in view (a drawn record of slot 5): its target record,
 * found by its map offset with no bound, smokes while +0x0C runs, a puff every
 * 0x32 - +0x0C passes at its x + 0x10 and y 0x11.  D4 is the record's screen x. */
void wof_burnt_barracks(int16_t d4)
{
    uint16_t d0;
    wof_gtarget_t *t = 0;

    if (wof_g.view_step == 1)
        d0 = (uint16_t)((((uint16_t)wof_g.draw_player_x & 0xFFF8u) - 0x500u) +
                        (uint16_t)(d4 << 3) - 0x38u);
    else
        d0 = (uint16_t)((uint16_t)wof_g.draw_player_x - 0xA0u + (uint16_t)d4);
    d0 = (uint16_t)(((d0 >> 2) & 0xFFFEu) - 2u);
    for (uint16_t i = 0; i < 16; i++)
        if (wof_m.target_records_4[i].map_offset == d0) {
            t = &wof_m.target_records_4[i];
            break;
        }
    if (!t)
        return;
    if (t->w0c == 0)
        return;
    if (--t->w0e > 0)
        return;
    if (--t->w0c == 0)
        return;
    t->w0e = (int16_t)(0x32 - t->w0c);
    {
        uint32_t x = (uint32_t)(uint16_t)((uint16_t)t->map_offset << 2) + 0x10u;

        wof_smoke_claim((int32_t)((x << 16) | (x >> 16)), 0x110000, 5);
    }
}

/* orig 0x014F5C - a target within 0x1C0 pixels of the drawing's player may hit the
 * aircraft: it records the nearest distance for the sound (0x027456, 0x027454), and unless
 * the cheat's 0x026F72 is set, a draw of rand_beam modulo 512 at least the distance-and-
 * height d2 and a second modulo 2048 at most 0x199 hit: smoke from the engine (6), and at
 * the end of the hit count 0x025088 the oil falls by one, the fuel by a draw modulo 4, and
 * the count starts again at 6 plus a draw modulo 8. */
void wof_target_fire(int16_t x)
{
    int16_t  d0 = (int16_t)(x - wof_g.draw_player_x);
    int16_t  d1, d2;
    uint16_t d2_high;

    if (d0 < 0)
        d0 = (int16_t)-d0;
    if (d0 > 0x1C0)
        return;
    if (d0 <= wof_g.g_027456)
        wof_g.g_027456 = d0;
    /* D2 comes from the caller with rand_beam's upper word (targets_3_draw's exg); D1's
     * upper word is 0 there (observed at every entry, re/notes/porting-m5.md).  The exg
     * of the two longs takes the upper words along. */
    d2 = d0;
    d2_high = (uint16_t)(wof_rand_upper() >> 16);
    d1 = wof_m.player[0].y;
    if (!(d2 > d1)) {
        int16_t tmp = d1;

        d1 = d2;
        d2 = tmp;
        d2_high = 0;
    }
    d2 = (int16_t)(d2 + (int16_t)((uint16_t)d1 >> 2));
    wof_g.g_027454 = (uint16_t)((wof_g.g_027454 & 0x00FFu) | 0xFF00u);
    if (wof_g.g_026f72 != 0)
        return;
    if ((int16_t)(wof_rand_beam(0x014F5C) & 0x1FFu) < d2)
        return;
    if ((int16_t)(wof_rand_beam(0x014F5C) & 0x7FFu) > 0x199)
        return;
    wof_smoke_at_player(6, d2_high);
    if (--wof_m.player[0].w10 > 0)
        return;
    wof_m.player[0].oil--;
    wof_m.player[0].fuel = (int16_t)(wof_m.player[0].fuel - (int16_t)(wof_rand_beam(0x014F5C) & 3u));
    wof_m.player[0].w10 = (int16_t)((wof_rand_beam(0x014F5C) & 7u) + 6);
}

/* orig 0x014FEE - an empty dug-out A0 takes a soldier: the barracks of the same island that
 * holds two or more and lies nearest (0x015034) loses one, which runs from it towards the
 * dug-out (0x011E82 with D0 1); with none, nothing. */
void wof_target_refill(wof_gtarget_t *a0)
{
    wof_gtarget_t *a2 = 0;
    uint32_t       d2 = 0x2710;
    uint16_t       d7 = wof_g.target_count_4;

    /* orig 0x015034 - the walk: subq.w #1,d7 then dbra, so count entries, the dug-out's island
     * at +9 against each barracks' (blt ends the walk: the tables are in map order), one of
     * the same island with +8 at least 2 at a distance other than 0 and not beyond d2 is
     * the new nearest. */
    for (uint16_t i = 0; (int16_t)(d7 - 1 - i) >= 0 && i < 16; i++) {
        wof_gtarget_t *a1 = &wof_m.target_records_4[i];
        int16_t        d;

        if ((int8_t)a0->island < (int8_t)a1->island)
            break;
        if (a0->island != a1->island)
            continue;
        if ((int8_t)a1->state < 2)
            continue;
        d = (int16_t)(a0->x0 - a1->x0);
        if (d == 0)
            continue;
        if (d < 0)
            d = (int16_t)-d;
        if ((int32_t)(int16_t)d2 < d)
            continue;
        d2 = (uint32_t)(uint16_t)d;
        a2 = a1;
    }
    if (d2 == 0x2710 || !a2)
        return;
    {
        int16_t d1 = (int16_t)(a2->x0 - a0->x0) < 0 ? 1 : -1;

        a2->state--;
        wof_soldier_out(a2, 1, d1);
    }
}

/* ------------------------------------------- 0x015078 to 0x015AE8, the ticker's messages */

/* A NUL-ended string of the executable's DATA hunk (the ticker's formats), at most n - 1
 * bytes: the port reads them from the image by address and keeps none in its sources. */
static void image_string(uint32_t addr, char *out, uint16_t n)
{
    uint16_t i = 0;

    while (i + 1u < n) {
        char c = (char)wof_image8(addr + i);

        if (!c)
            break;
        out[i++] = c;
    }
    out[i] = 0;
}

/* orig 0x015078 - RawDoFmt of the format at A0 with the data stream at A1 into the buffer at
 * A2, through a PutChProc that stores each character and the NUL (0x015090): here into
 * ticker_text from byte `at` on, with one long of data, the bonus of the island messages.
 * A format without a conversion reads no data. */
void wof_ticker_format(uint32_t format, uint32_t value, uint16_t at)
{
    char     fmt[160];
    char     out[200];
    uint16_t data[2];
    uint16_t n;

    image_string(format, fmt, sizeof fmt);
    data[0] = (uint16_t)(value >> 16);
    data[1] = (uint16_t)value;
    n = wof_raw_do_fmt(out, fmt, data);
    for (uint16_t i = 0; i <= n && (uint32_t)at + i < sizeof wof_g.ticker_text; i++)
        wof_g.ticker_text[at + i] = (uint8_t)out[i];
}

/* orig 0x015624 - a message into ticker_text from its start, whether or not one is running
 * there, then 0x01555A: the ticker takes it only when it has no message. */
void wof_ticker_say(uint32_t format, uint32_t value)
{
    wof_ticker_format(format, value, 0);
    if (wof_g.ticker_message == 0)
        wof_g.ticker_message = 0x02716Au;                 /* 0x01555A: ticker_text */
}

/* orig 0x015694 - the map's last island neutralised: the next mission, and after the rank's
 * last mission (missions_per_rank, 0x025548) the first of the next rank, at most rank 6,
 * with balloons_on set (the promotion's balloons over the carrier and a life more at the
 * next mission's start, 0x010154); its message is appended to ticker_text over the last
 * character before the NUL (`subq.w #2` behind the NUL), the ticker shows ticker_text at
 * once, and 0x0253BC says the mission is won: the next time the weapon menu is up, main
 * goes on to the next mission (0x010132, M7's). */
void wof_mission_won(void)
{
    uint16_t end = 0;
    uint32_t format;

    wof_g.mission_number++;
    if ((int16_t)word_at(0x025548u + 2u * (uint32_t)(uint16_t)wof_g.rank_played) >=
        (int16_t)wof_g.mission_number) {
        format = 0x02399Eu;
    } else {
        wof_g.mission_number = 1;
        wof_g.rank_played++;
        if ((int16_t)wof_g.rank_played > 6)
            wof_g.rank_played = 6;
        wof_g.balloons_on = 0xFF;
        format = 0x023A5Au;
    }
    while (end < sizeof wof_g.ticker_text && wof_g.ticker_text[end])
        end++;
    wof_ticker_format(format, 0, (uint16_t)(end - 1u));
    wof_g.ticker_message = 0x02716Au;
    wof_g.g_0253bc = -1;
}

/* orig 0x015AE8 - the bonus for island D0 of the mission being flown: a word of
 * island_bonus (0x02347C) by the map's number in mission_map_table (0x02345F, by rank and
 * mission) and the island. */
uint16_t wof_island_bonus(uint8_t island)
{
    uint16_t d1 = (uint16_t)((uint16_t)(wof_g.rank_played * 4u) + wof_g.mission_number);
    uint16_t d2 = (uint16_t)((uint16_t)wof_image8(0x02345Fu + d1) << 3);

    d2 = (uint16_t)(d2 + (uint16_t)(island * 2u));
    return (uint16_t)word_at(0x02347Cu + d2);
}

#ifdef WOF_TRACE
/* The oracle tests' entry (tests/test_oracle_m5.py): one routine of the targets and the
 * pools by its original address, on the port's state as the test left it.  `out` takes
 * what a routine hands back beside D0. */
int32_t wof_test_m5_call(uint32_t orig, int32_t a, int32_t b, int32_t c, int32_t *out)
{
    switch (orig) {
    case 0x014AE4: {
        uint16_t r[4];

        wof_target_records((int16_t)a, r);
        for (int k = 0; k < 4; k++)
            out[k] = r[k];
        return 0;
    }
    case 0x014B54: {
        void *t = wof_target_of((int16_t)a);

        if (!t)
            return -1;
        for (int i = 0; i < 16; i++) {
            if (t == &wof_m.target_records_4[i]) return 0x400 | i;
            if (t == &wof_m.target_records_3[i]) return 0x300 | i;
        }
        for (int i = 0; i < 32; i++)
            if (t == &wof_m.target_records_f[i]) return 0xF00 | i;
        return -2;
    }
    case 0x014DB8: return wof_target_range_frame((int16_t)a, (int16_t)b, (int16_t)c);
    case 0x014D50: return wof_target_frame((int16_t)a);
    case 0x014F5C: wof_target_fire((int16_t)a); return 0;
    case 0x015AE8: return wof_island_bonus((uint8_t)a);
    case 0x011E82: {
        const wof_gtarget_t *t = (a >> 8) == 3 ? &wof_m.target_records_3[a & 0xFF]
                                               : &wof_m.target_records_4[a & 0xFF];

        wof_soldier_out(t, (uint8_t)b, (int16_t)c);
        return 0;
    }
    case 0x014FEE: wof_target_refill(&wof_m.target_records_3[a & 0xFF]); return 0;
    case 0x015460: return (int32_t)wof_smoke_claim(a, b, (int16_t)c);
    case 0x0152B0: wof_splash_spawn((int16_t)a); return 0;
    case 0x0154E0: wof_smoke_at_player((int16_t)a, (uint16_t)b); return 0;
    default:       return -1000;
    }
}
#endif
