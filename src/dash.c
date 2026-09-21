/* The dashboard of a pass: the map window (orig 0x01417E) and the instruments of
 * draw_dashboard (orig 0x01EE16), drawn into the back view's dashboard viewport, which
 * frame_update has made the draw target (re/notes/drawing.md, "The scene routines").
 *
 * The dashboard is double-buffered like the playfield, so draw_dashboard keeps what each
 * buffer last showed in that buffer's entry of view_caches and redraws an instrument only
 * when its value differs.  The gauges move toward their targets by a fixed step per pass.
 * What each instrument is, in the manual's words, is in re/notes/porting-m4.md.
 *
 * Regions the five mission scripts never executed are marked stand-ins, as in src/world.c.
 */
#include "wof.h"
#include "gen/tables.h"

static uint16_t dash(uint16_t entry)
{
    return wof_table_handle(wof_dash_slot(), entry);
}

/* A draw with the caller's hotspot subtraction, and one without: draw_dashboard does both. */
static void draw_hot(uint16_t entry, int16_t x, int16_t y)
{
    wof_draw_at(dash(entry), x, y);
}

static void draw_raw(uint16_t entry, int16_t x, int16_t y)
{
    const wof_shape_t *s = wof_shape_of(dash(entry));

    if (s)
        wof_shape_draw(s, x, y);
    else
        wof_trace_add("shape_draw", 0, 0, 0, 1, 0, 0);
}

/* The byte the original writes with st.b into the high half of a word. */
static int16_t high_ff(int16_t word)
{
    return (int16_t)(uint16_t)(0xFF00u | ((uint16_t)word & 0xFFu));
}

/* ------------------------------------------------------------------ the map window */

/* orig 0x014564 - the window's sky and, below the horizon row 0x0253E6, its sea. */
static void window_background(void)
{
    wof_vport_t *play = wof_back_vport();

    wof_draw_set_target(play && play->next != WOF_VP_NONE ? &wof_f.vport[play->next] : 0);
    wof_rect_fill(0x102, 7, 0x17C, 0x20, 2);
    wof_rect_fill(0x102, wof_g.g_0253e6, 0x17C, 0x20, 1);
}

/* orig 0x0141B4 - the aircraft's height marker at the window's right edge: row 0x0D above
 * height 0x51, lower by a quarter of what the height falls short of it. */
void wof_window_height(void)
{
    wof_g.g_0253ba = 0x18;
    if (wof_g.draw_player_y >= 0x51)
        wof_g.g_0253ba = 0x0D;
    else
        wof_g.g_0253ba = (int16_t)(uint16_t)(((uint16_t)(0x51 - wof_g.draw_player_y) >> 2) + 0x0D);
    draw_hot(5, 0x13F, wof_g.g_0253ba);
}

/* orig 0x014430 - while the aircraft stands on a ship, the ship's own picture in the window:
 * the distance to the deck's end in the direction away from the facing, in records, picks a
 * row, a clip and a frame from three small tables. */
static void window_ship(void)
{
    int16_t  px = wof_g.draw_player_x;
    uint16_t at, d0, d1, d4, d5, d6;
    int16_t  step, d2 = 0;
    int16_t  facing = wof_m.player[0].facing;

    wof_g.g_0276fe = wof_g.clip_top;
    if (px < 0 || (uint16_t)px >= wof_g.map_extent)
        return;
    at = (uint16_t)(((uint16_t)px >> 3) * 2u);
    if ((wof_m.map_records[at >> 1].v & 3u) != 1)
        return;
    if (facing < 0) {
        wof_g.g_0253e4 = 0x49;
        step = 2;
    } else {
        wof_g.g_0253e4 = 0x41;
        step = -2;
    }
    for (;;) {
        int32_t  k   = ((int32_t)at + d2) >> 1;
        uint16_t rec = (k >= 0 && k < 3576) ? wof_m.map_records[k].v : 0;

        if (((rec >> 2) & 0x1FF) == 0)
            break;
        d2 = (int16_t)(d2 + step);
    }
    d2 = (int16_t)(d2 >> 1);
    if (d2 < 0)
        d2 = (int16_t)-d2;
    d0 = d2 < 102 ? wof_tbl_window_height_index[d2] : 0;
    d0 &= 0x0F;
    d1 = (uint16_t)wof_g.g_0253e6;
    d1 = (uint16_t)((d1 & 0xFF00u) | ((d1 + wof_tbl_window_row[d0]) & 0xFFu));   /* add.b */
    d1 = (uint16_t)(d1 + 7);
    d5 = d1;
    d6 = (uint16_t)(wof_tbl_window_clip[d0] + (uint16_t)wof_g.g_0253e6);
    wof_g.clip_top = (int16_t)d6;
    d4 = wof_tbl_window_frame[d0];
    draw_hot((uint16_t)(0x38 + d4), 0x13F, (int16_t)(d5 + 1));
    draw_hot((uint16_t)wof_g.g_0253e4, 0x13F, (int16_t)d5);
    wof_g.clip_top = wof_g.g_0276fe;
    draw_hot(facing >= 0 ? 0x51 : 0x59, 0x13F, (int16_t)d5);
}

/* orig 0x014206 - the strip of the map around the aircraft, eleven rows of the window from
 * the horizon down, each row the records at a spacing from window_steps.  The five scripts
 * saw it only over the carrier, whose records the strip leaves out (their low bits equal
 * 0x02745A), so the rows drew nothing; what the strip draws for any other record, and the
 * enemy aircraft it marks, are stand-ins. */
static void window_strip(void)
{
    int16_t px = wof_g.draw_player_x;

    wof_g.g_02745a = 4;
    if (px >= 0 && (uint16_t)px < wof_g.map_extent) {
        uint16_t at = (uint16_t)(((uint16_t)px >> 3) * 2u);

        if ((wof_m.map_records[at >> 1].v & 3u) == 1) {
            int16_t           off  = (int16_t)at;
            const wof_ship_t *s    = &wof_m.ship_records[4];
            int               ship = -1;
            static const uint8_t order[4] = { 0, 1, 2, 3 };
            const uint8_t *flag[4] = { &wof_g.has_destroyer, &wof_g.has_battleship,
                                       &wof_g.has_cruiseship, &wof_g.has_japcarrier };

            for (int i = 0; i < 4 && ship < 0; i++)                /* orig 0x014A52 */
                if (*flag[i] && off >= wof_m.ship_records[order[i]].span0 &&
                    off <= wof_m.ship_records[order[i]].span1)
                    ship = order[i];
            if (ship >= 0)
                s = &wof_m.ship_records[ship];
            if (s->w12 == 0)
                wof_g.g_02745a = 1;
            else
                WOF_STANDIN("M6 STAND-IN: 0x014244, the map window over an enemy ship");
        }
    }

    for (int16_t k = 11; k >= 1; k--) {
        int16_t d0 = (int16_t)wof_tbl_window_steps[k];
        int16_t d1 = (int16_t)wof_tbl_window_steps[k - 1];
        int16_t d5 = (int16_t)(d0 - d1);
        int16_t d6 = d0;
        int16_t dir = wof_m.player[0].facing;                   /* the live facing */
        int16_t d3, d4;

        wof_g.g_0253d8 = -1;
        wof_g.g_0253da = -1;
        if (dir < 0)
            d6 = (int16_t)-d6;
        dir = (int16_t)(dir + dir);
        d6 = (int16_t)(d6 + (int16_t)(wof_g.draw_player_x >> 3));
        d6 = (int16_t)(d6 + d6);

        d4 = d6;
        d3 = (int16_t)(d5 + d5);
        if (dir >= 0)
            d3 = (int16_t)-d3;
        d3 = (int16_t)(d3 + d4);
        if (d4 < d3) {
            int16_t t = d3;

            d3 = d4;
            d4 = t;
        }
        for (int i = 0; i < 4; i++) {
            const wof_aircraft_t *a = &wof_m.aircraft_records[i];

            if (a->w[0] != 0 && !(d3 > a->w[0x17]) && !(d4 < a->w[0x17]))
                WOF_STANDIN("M6 STAND-IN: 0x0142BC, an enemy aircraft in the map window");
        }

        for (int16_t n = d5; n >= 0; n--) {
            if (d6 >= 0 && (uint32_t)(uint16_t)d6 <= wof_m.map_records_end[0].off) {
                uint16_t rec = wof_m.map_records[(uint16_t)d6 >> 1].v;
                uint16_t low = (uint16_t)(rec & 3u);
                uint16_t slot = (uint16_t)(rec & 0x7FCu);

                wof_g.g_02568d = (uint8_t)low;
                if (low == (uint16_t)wof_g.g_02745a)
                    slot = 0;
                if (slot >> 2)
                    WOF_STANDIN("M4 PART 2 STAND-IN: 0x01434C, a map record in the map window");
                else if ((uint8_t)(low - 2) == 0)
                    WOF_STANDIN("M4 PART 2 STAND-IN: 0x014382, land in the map window");
            }
            d6 = (int16_t)(d6 + dir);
        }
        wof_g.g_0253e2++;
    }
    if (!wof_g.g_0276fc) {
        window_ship();
        wof_g.g_0276fc = 0;
    }
}

/* orig 0x01417E - the map window: its clip, its horizon row, the background and, at full
 * scale, the strip and the height marker. */
void wof_map_window(void)
{
    wof_clip_set(7, 0x20, 0x100, 0x190);                      /* clip_dash_window */
    wof_g.g_0253e2 = wof_g.g_0253e6;
    window_background();
    if (wof_g.view_step != 1) {
        window_strip();
        wof_window_height();
    }
}

/* ------------------------------------------------------------------ draw_dashboard */

/* orig 0x01F2B0 - one digit: a slice of dash shape 7, blitted without a mask at the row
 * digit_rows gives the digit, sign-extended from a byte as the original does. */
void wof_dash_digit(int16_t x, int16_t y, uint16_t d)
{
    const wof_shape_t *s = wof_shape_of(dash(7));
    int16_t            row = (int16_t)(int8_t)(uint8_t)((uint16_t)y + (d < 10 ? wof_tbl_digit_rows[d] : 0));

    if (s)
        wof_shape_blit(s, 0, (int16_t)(x - s->hot_x), (int16_t)(row - s->hot_y));
}

/* orig 0x01F26A - the score, sprintf("%07ld") into score_text and a digit per character,
 * clipped to rows 11 to 17. */
static void score(void)
{
    uint32_t v = wof_g.player_score;
    char     text[8];
    int16_t  x = 0x200;

    wof_g.clip_top = 0x0B;
    wof_g.clip_bottom = 0x12;
    for (int i = 6; i >= 0; i--) {
        text[i] = (char)('0' + (int32_t)v % 10);
        v = (uint32_t)((int32_t)v / 10);
    }
    text[7] = 0;
    if ((int32_t)wof_g.player_score < 0)
        WOF_STANDIN("M7 STAND-IN: 0x01F26A, a negative score");
    for (int i = 0; i < 8; i++)
        wof_g.score_text[i] = (uint8_t)text[i];
    for (int i = 0; text[i]; i++, x = (int16_t)(x + 0x0E))
        wof_dash_digit(x, 0x0B, (uint16_t)(text[i] - '0'));
}

/* orig 0x01F21A - the arrows that point to an enemy aircraft (M6). */
static void enemy_arrows(void)
{
    for (int i = 0; i < 4; i++)
        if (wof_m.aircraft_records[i].w[0] != 0)
            WOF_STANDIN("M6 STAND-IN: 0x01F226, an arrow to an enemy aircraft");
}

/* orig 0x01EE16 draw_dashboard.  Oil and fuel are needle gauges that move four steps a pass
 * toward their value; the weapon, the weapon counter's two drums, the lives drum, the score
 * and the two-digit counter at 0x02537F are redrawn when this buffer's cache says they
 * changed (the manual, page 8, names the instruments). */
void wof_draw_dashboard(void)
{
    wof_cache_t        *c = &wof_m.view_caches[wof_f.back_view & 1];
    const wof_player_t *p = &wof_m.player[0];
    int16_t             d4, d5;

    wof_clip_set(0, 0x25, 0, 0x280);                          /* clip_dashboard */
    wof_g.gauge_flying = (uint16_t)high_ff((int16_t)wof_g.gauge_flying);
    if (p->on_deck != 0 && p->on_deck != 1 && p->on_deck != 7)
        wof_g.gauge_flying = 0;
    enemy_arrows();

    /* The oil gauge. */
    d5 = (int16_t)(p->oil - 0x60);
    if ((int32_t)p->oil - 0x60 < 0)                               /* sub.w, bge: exact */
        d5 = 0;
    d5 = (int16_t)(d5 + d5);
    d5 = (int16_t)(d5 & (int16_t)0xFFFC);
    if (p->on_deck <= 1 && wof_g.g_027de8 != 0)
        d5 = (int16_t)(d5 + 0x18);
    if (d5 != wof_g.gauge_oil)
        wof_g.gauge_oil = (int16_t)(wof_g.gauge_oil + (d5 > wof_g.gauge_oil ? 4 : -4));
    d5 = wof_g.gauge_oil;
    d4 = 0x0C;
    if (wof_g.gauge_flying != 0 && (uint16_t)p->oil < 0x74)
        WOF_STANDIN("M4 PART 2 STAND-IN: 0x01EEB8, the oil warning");
    if (d4 != c->oil_warn || d5 != c->oil) {
        c->oil_warn = d4;
        c->oil = d5;
        draw_hot(0x73, 0xD0, 0x12);
        draw_raw((uint16_t)(d4 >> 2), 0xCA, 0x0A);
        draw_hot((uint16_t)((uint16_t)(d5 + 0x170) >> 2), 0xD0, 0x12);
    }

    /* The fuel gauge. */
    d5 = p->fuel;
    if (d5 < 0) {
        WOF_STANDIN("M4 PART 2 STAND-IN: 0x01EF32, fuel below zero");
        d5 = 0;
    }
    d5 = (int16_t)((uint16_t)d5 >> 1);
    if ((uint16_t)d5 > 0x58)
        d5 = 0x58;
    d5 = (int16_t)(d5 & (int16_t)0xFFFC);
    if (d5 == 0 && wof_g.gauge_flying)
        WOF_STANDIN("M4 PART 2 STAND-IN: 0x01EF48, the empty tank's needle");
    if (d5 != wof_g.gauge_fuel) {
        if (d5 > wof_g.gauge_fuel)
            wof_g.gauge_fuel = (int16_t)(wof_g.gauge_fuel + 4);
        else
            wof_g.gauge_fuel = (int16_t)(wof_g.gauge_fuel - 4);   /* read: the five only rose */
    }
    d5 = wof_g.gauge_fuel;
    d4 = 0x0C;
    if (wof_g.gauge_flying != 0 && p->fuel <= 0x40)
        WOF_STANDIN("M4 PART 2 STAND-IN: 0x01EF8C, the fuel warning");
    if (d4 != c->fuel_warn || d5 != c->fuel) {
        c->fuel_warn = d4;
        c->fuel = d5;
        draw_hot(0x73, 0x1AF, 0x12);
        draw_raw((uint16_t)(d4 >> 2), 0x1A8, 0x0A);
        draw_hot((uint16_t)((uint16_t)(d5 + 0x170) >> 2), 0x1AF, 0x12);
    }

    /* The weapon. */
    if (wof_g.weapon_type != c->weapon) {
        const wof_shape_t *s;

        c->weapon = wof_g.weapon_type;
        s = wof_shape_of(dash((uint16_t)wof_g.weapon_type));
        if (s)
            wof_shape_blit(s, 0, 0x10, 0x0B);
    }

    /* The weapon counter's two drums. */
    {
        uint16_t n = wof_g.weapon_count;

        if (n == 0xFF || n != (uint16_t)c->weapons) {
            int16_t d2 = (int16_t)(0x50 - (int16_t)((n % 10u) << 3));
            int16_t d3 = (int16_t)(0x50 - (int16_t)((n / 10u) << 3));

            if (n == 0xFF) {
                WOF_STANDIN("M5 STAND-IN: 0x01F062, unlimited weapons");
                d2 = d3 = 0x64;
            }
            if (wof_g.gauge_weapons_lo == d3 && wof_g.gauge_weapons_hi == d2)
                c->weapons = (int16_t)n;
            else
                WOF_STANDIN("M5 STAND-IN: 0x01F07A, the weapon counter's drums turning");
            wof_g.clip_top = 0x13;
            wof_g.clip_bottom = 0x1C;
            draw_hot(6, 0x2A, (int16_t)(0x1C + wof_g.gauge_weapons_lo));
            draw_hot(6, 0x42, (int16_t)(0x1C + wof_g.gauge_weapons_hi));
        }
    }

    /* The lives drum. */
    {
        uint8_t d3 = wof_g.lives;

        if ((int8_t)d3 < 0) {
            WOF_STANDIN("M4 PART 2 STAND-IN: 0x01F102, negative lives");
            d3 = 0;
        }
        if (d3 > 9) {
            WOF_STANDIN("M4 PART 2 STAND-IN: 0x01F10C, more than nine lives");
            d3 = 9;
        }
        if ((int16_t)d3 != c->lives) {
            int16_t d0 = (int16_t)(0x59 - (int16_t)(d3 << 3));
            int16_t d2 = wof_g.gauge_lives;

            if (d0 == d2) {
                c->lives = d3;
            } else {
                if (d0 > d2)
                    d2 = (int16_t)(d2 + 1);
                else
                    WOF_STANDIN("M4 PART 2 STAND-IN: 0x01F12E, the lives drum turning down");
                wof_g.gauge_lives = d2;
            }
            wof_g.clip_top = 0x13;
            wof_g.clip_bottom = 0x1C;
            draw_hot(6, 0x7D, (int16_t)(0x13 + d2));
        }
    }

    /* The score. */
    if (wof_g.player_score != c->score) {
        c->score = wof_g.player_score;
        score();
    }

    /* The two-digit counter of 0x02537F and its bars. */
    {
        uint16_t d3 = wof_g.g_02537f;

        if (d3 > 0x63) {
            WOF_STANDIN("M5 STAND-IN: 0x01F186, the counter above 99");
            d3 = 0x63;
        }
        if ((int16_t)d3 != c->w0e) {
            int16_t n1, n2;

            c->w0e = (int16_t)d3;
            wof_g.clip_top = 0x14;
            wof_g.clip_bottom = 0x1C;
            wof_dash_digit(0x1FC, 0x15, (uint16_t)(d3 / 10u));
            wof_dash_digit(0x20A, 0x15, (uint16_t)(d3 % 10u));
            wof_g.clip_top = 0x13;
            wof_g.clip_bottom = 0x1F;
            n1 = c->w0e;
            n2 = (int16_t)(n1 - 7);
            if (n2 > 0)
                n1 = 7;
            if (n1 > 0 || n2 > 0)
                WOF_STANDIN("M5 STAND-IN: 0x01F206, the counter's bars");
        }
    }
}
