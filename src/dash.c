/* The dashboard of a pass: the 3-D view (orig 0x01417E) and the instruments of
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

/* --------------------------------------------------------------------- the 3-D view */

/* orig 0x014564 - the window's sky and, below the horizon row 0x0253E6, its sea. */
static void window_background(void)
{
    wof_vport_t *play = wof_back_vport();

    wof_draw_set_target(play && play->next != WOF_VP_NONE ? &wof_f.vport[play->next] : 0);
    wof_rect_fill(0x102, 7, 0x17C, 0x20, 2);
    wof_rect_fill(0x102, wof_g.g_0253e6, 0x17C, 0x20, 1);
}

/* orig 0x0141B4 - the 3-D view's cursor, the artificial horizon of the manual's page 8,
 * at x 0x13F: row 0x0D above
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

/* orig 0x0145A6 - the shape of a map record's class in the 3-D view, on window row `row`
 * (0 at the bottom): an entry of dash_shapes, or of MasterList for an enemy ship that has
 * its own (+0x1C), as the byte offset the caller indexes with; negative for none.  The rows
 * scale the shapes through two byte tables, 0x0246B8 for the ground and 0x0246C4 for the
 * ships.  `off` is the map offset the row's walk ended at, which is where the ship is
 * looked for. */
static int16_t window_shape(uint16_t cls, uint8_t low, int16_t row, int16_t off, int *master)
{
    int16_t d1;

    *master = 0;
    if ((int16_t)cls >= 6 && (int16_t)cls <= 8) {
        d1 = 0x0E;
    } else if (cls == 4 || cls == 5) {
        d1 = cls == 4 ? 0x1B : 0x22;
    } else if (cls == 3) {
        d1 = 0x14;
    } else if (low == 1) {                                    /* 0x014610: a ship */
        d1 = wof_m.player[0].facing < 0 ? 0x0A : 0;
        if (cls == 0x22 || cls == 0xF6) {
            d1 = (int16_t)(d1 + 0x4D);
        } else {
            int ship = wof_ship_at_span(off);

            if (ship < 0)
                return (int16_t)ship;
            if (wof_m.ship_records[ship].slot_base) {
                d1 = (int16_t)(d1 + wof_m.ship_records[ship].slot_base);
                wof_g.g_0276fc = 0xFF;
                *master = 1;
            } else {
                wof_g.g_0276fc = 0;
                d1 = (int16_t)(d1 + 0x3C);
            }
        }
        return (int16_t)((d1 + (int16_t)wof_tbl_data_image[0x0246C4u - 0x023000u + (uint16_t)row]) * 4);
    } else if ((int16_t)cls >= 0x0F && (int16_t)cls <= 0x1E) {
        d1 = cls == 0x0F ? 0x29 : 0x30;
    } else {
        return -1;
    }
    return (int16_t)((d1 + (int16_t)wof_tbl_data_image[0x0246B8u - 0x023000u + (uint16_t)row]) * 4);
}

/* 0x0143A6 and 0x0143DE: the record a row found, at the window's right edge on the row. */
static void window_record(int16_t cls, int16_t row, int16_t off)
{
    int     master;
    int16_t at;

    if (cls < 0)
        return;
    at = window_shape((uint16_t)(cls & 0x1FF), wof_g.g_02568d, row, off, &master);
    if (at < 0)
        return;
    wof_draw_at(master ? wof_m.master_list[(uint16_t)at >> 2].s : dash((uint16_t)(at >> 2)),
                0x13F, wof_g.g_0253e2);
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
            if (s->w12 == 0 || s->w12 == 0x1770)
                wof_g.g_02745a = 1;
        }
    }

    for (int16_t k = 11; k >= 1; k--) {
        int16_t land;
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
        /* 0x0142A0: an enemy aircraft whose drawing's map offset (+0x2E) lies in the row's
         * span is drawn on the row at x 0x13F, the window's middle, dash_frames by its frame
         * (+0x30) turned to the player's live facing (0x1C on facing east, round within
         * the 0x38 of one set), the row's set added as a byte (window_rows, 0x024692), and
         * a quarter of its height above the row. */
        for (int i = 0; i < 4; i++) {
            const wof_aircraft_t *a = &wof_m.aircraft_records[i];
            uint16_t d2;
            int16_t  d1;

            if (a->state == 0 || d3 > a->draw_x || d4 < a->draw_x)
                continue;
            d2 = (uint16_t)a->frame;
            if (wof_m.player[0].facing >= 0) {
                d2 = (uint16_t)(d2 + 0x1C);
                if (d2 >= 0x38)
                    d2 = (uint16_t)(d2 - 0x38);
            }
            d2 = (uint16_t)((d2 & 0xFF00u) | ((d2 + wof_tbl_window_rows[k - 1]) & 0xFFu));   /* add.b */
            d1 = (int16_t)(-(int16_t)((a->y >> 2) + 4) + wof_g.g_0253e2);
            wof_draw_at(d2 < 168 ? wof_m.dash_frames[d2].s : WOF_SHAPE_NONE, 0x13F, d1);
        }

        land = 0;
        for (int16_t n = d5; n >= 0; n--) {
            if (d6 >= 0 && (uint32_t)(uint16_t)d6 <= wof_m.map_records_end[0].off) {
                uint16_t rec = wof_m.map_records[(uint16_t)d6 >> 1].v;
                uint16_t low = (uint16_t)(rec & 3u);
                uint16_t slot = (uint16_t)(rec & 0x7FCu);

                wof_g.g_02568d = (uint8_t)low;
                if (low == (uint16_t)wof_g.g_02745a)
                    slot = 0;
                slot >>= 2;
                if (slot) {                                   /* 0x01434C */
                    if (slot >= 6 && slot <= 8)
                        wof_g.g_0253da = (int16_t)slot;
                    else if (wof_g.g_0253d8 != 0x22 && wof_g.g_0253d8 != 0xF6)
                        wof_g.g_0253d8 = (int16_t)slot;
                }
                if ((uint8_t)(low - 2) == 0)
                    land = -1;
            }
            d6 = (int16_t)(d6 + dir);
        }
        if (land)                                             /* 0x01438A: the shore */
            wof_rect_fill(0x102, wof_g.g_0253e2, 0x17C, wof_g.g_0253e2, 5);
        window_record(wof_g.g_0253da, (int16_t)(k - 1), d6);
        window_record(wof_g.g_0253d8, (int16_t)(k - 1), d6);
        wof_g.g_0253e2++;
    }
    if (!wof_g.g_0276fc) {
        window_ship();
        wof_g.g_0276fc = 0;
    }
}

/* orig 0x01417E - the 3-D view (the manual, page 8): its clip, its horizon row, the
 * background and, at full scale, the strip and the cursor. */
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
 * digit_rows (0x024BFC) gives the digit, a byte added to the row and sign-extended as the
 * original does.  The digit indexes the table as a signed word, so a character below '0'
 * reads the bytes in front of it (draw_score's '-', M7 part 2). */
void wof_dash_digit(int16_t x, int16_t y, uint16_t d)
{
    const wof_shape_t *s = wof_shape_of(dash(7));
    uint8_t            add = wof_image8(0x024BFCu + (uint32_t)(int32_t)(int16_t)d);
    int16_t            row = (int16_t)(int8_t)(uint8_t)((uint16_t)y + add);

    if (s)
        wof_shape_blit(s, 0, (int16_t)(x - s->hot_x), (int16_t)(row - s->hot_y));
}

/* orig 0x01F26A draw_score - the score through RawDoFmt's "%07ld" (0x0266C8) into
 * score_text, then a digit per character up to the NUL, clipped to rows 11 to 17.
 * RawDoFmt fills the whole converted field, its sign included, on the left, so a negative
 * score reads "000-123" and its '-' is drawn as the digit 0x2D - 0x30, which dash_digit
 * takes from the byte three before digit_rows.  A score of more than seven characters runs
 * on past score_text's eight bytes as the original's does.  Nothing the game does makes the
 * score negative; a loaded game can bring any score (M7 part 2, re/notes/campaign.md). */
static void score(void)
{
    int32_t  v = (int32_t)wof_g.player_score;
    uint32_t u = v < 0 ? 0u - (uint32_t)v : (uint32_t)v;
    char     field[12];
    char     text[16];
    uint16_t n = 0, len = 0;
    int16_t  x = 0x200;

    wof_g.clip_top = 0x0B;
    wof_g.clip_bottom = 0x12;
    do {
        field[n++] = (char)('0' + u % 10u);
        u /= 10u;
    } while (u);
    if (v < 0)
        field[n++] = '-';
    while (len + n < 7u)
        text[len++] = '0';
    while (n)
        text[len++] = field[--n];
    text[len] = 0;
    for (uint16_t i = 0; i <= len; i++)
        wof_original_store8(0x027F22u + i, (uint8_t)text[i]);
    for (uint16_t i = 0; text[i]; i++, x = (int16_t)(x + 0x0E))
        wof_dash_digit(x, 0x0B, (uint16_t)((uint16_t)(uint8_t)text[i] - 0x30u));
}

#ifdef WOF_TRACE
/* The oracle test's entry (tests/test_oracle_m7.py): draw_score alone. */
void wof_test_draw_score(void)
{
    if (!wof_shape_of(dash(7)))
        wof_load_dash_assets();             /* the dashboard's shapes, as a mission has them */
    score();
}
#endif

/* orig 0x01F21A enemy_arrows - the first enemy aircraft in use that is a torpedo plane
 * (+0x02 low three bits 4) gets the arrow of the 3-D view (the manual, page 11): dash
 * shape 8 when it is west of the player's live x or level with it, 9 when east, at the
 * window's top centre. */
static void enemy_arrows(void)
{
    for (int i = 0; i < 4; i++) {
        const wof_aircraft_t *a = &wof_m.aircraft_records[i];

        if (a->state == 0 || (a->mode & 7) != 4)
            continue;
        draw_hot((int16_t)(wof_m.player[0].x - a->x) >= 0 ? 8 : 9, 0x140, 0x0A);
        return;
    }
}

/* orig 0x01F200 kill_icons - a row of D2 kill icons (dash shape 116), 13 apart from D0,
 * at row D1, drawn without the hotspot taken off. */
static void kill_icons(int16_t count, int16_t x, int16_t y)
{
    for (; count > 0; count--, x = (int16_t)(x + 0x0D))
        draw_raw(116, x, y);
}

/* orig 0x01EE16 draw_dashboard.  Oil and fuel are needle gauges that move four steps a pass
 * toward their value; the weapon, the weapon counter's two drums, the lives drum, the score
 * and the enemy plane counter at 0x02537F are redrawn when this buffer's cache says they
 * changed (the manual, pages 8 and 9, names the instruments). */
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
    if (wof_g.gauge_flying != 0 && (uint16_t)p->oil < 0x74) {   /* 0x01EEB8: the warning blinks */
        d4 = 0x10;
        if (--wof_g.gauge_oil_blink <= 0) {
            d4 = 0x0C;
            if (wof_g.gauge_oil_blink != 0)
                wof_g.gauge_oil_blink = 0x0A;
        }
    }
    if (d4 != c->oil_warn || d5 != c->oil) {
        c->oil_warn = d4;
        c->oil = d5;
        draw_hot(0x73, 0xD0, 0x12);
        draw_raw((uint16_t)(d4 >> 2), 0xCA, 0x0A);
        draw_hot((uint16_t)((uint16_t)(d5 + 0x170) >> 2), 0xD0, 0x12);
    }

    /* The fuel gauge. */
    d5 = p->fuel;
    if (d5 < 0)
        d5 = 0;                                               /* 0x01EF32 */
    d5 = (int16_t)((uint16_t)d5 >> 1);
    if ((uint16_t)d5 > 0x58)
        d5 = 0x58;
    d5 = (int16_t)(d5 & (int16_t)0xFFFC);
    if (d5 == 0 && wof_g.gauge_flying) {
        /* 0x01EF48: the empty tank's needle trembles by chance, bit 15 of a draw */
        uint16_t r = (uint16_t)wof_rand_beam(0x01EE16);

        r = (uint16_t)((uint16_t)(r << 3) | (uint16_t)(r >> 13));
        d5 = (int16_t)(r & 4u);
    }
    if (d5 != wof_g.gauge_fuel) {
        if (d5 > wof_g.gauge_fuel)
            wof_g.gauge_fuel = (int16_t)(wof_g.gauge_fuel + 4);
        else
            wof_g.gauge_fuel = (int16_t)(wof_g.gauge_fuel - 4);
    }
    d5 = wof_g.gauge_fuel;
    d4 = 0x0C;
    if (wof_g.gauge_flying != 0 && p->fuel <= 0x40) {         /* 0x01EF8C: the warning blinks */
        d4 = 0x10;
        if (--wof_g.gauge_fuel_blink <= 0) {
            d4 = 0x0C;
            if (wof_g.gauge_fuel_blink != 0)
                wof_g.gauge_fuel_blink = 8;
        }
    }
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

            if (n == 0xFF)
                d2 = d3 = 0x64;                               /* 0x01F062: unlimited, the cheat's m */
            if (wof_g.gauge_weapons_tens == d3 && wof_g.gauge_weapons_ones == d2) {
                c->weapons = (int16_t)n;
            } else {
                /* 0x01F07A: the drums turn one row a pass toward the count, the ones drum
                 * always, round after 0x50 to 1 (unsigned); the tens drum only while the
                 * ones drum passes its rows 0 to 8, which is the moment a real counter's
                 * tens wheel moves on. */
                uint16_t d1 = (uint16_t)(wof_g.gauge_weapons_ones + 1);
                uint16_t d4 = (uint16_t)wof_g.gauge_weapons_tens;

                if (d1 > 0x50)
                    d1 = 1;
                wof_g.gauge_weapons_ones = (int16_t)d1;
                if ((int16_t)d4 != d3 && !((uint16_t)wof_g.gauge_weapons_ones > 8)) {
                    d4 = (uint16_t)(d4 + 1);
                    if (d4 > 0x50)
                        d4 = 1;
                    wof_g.gauge_weapons_tens = (int16_t)d4;
                }
            }
            wof_g.clip_top = 0x13;
            wof_g.clip_bottom = 0x1C;
            draw_hot(6, 0x2A, (int16_t)(0x1C + wof_g.gauge_weapons_tens));
            draw_hot(6, 0x42, (int16_t)(0x1C + wof_g.gauge_weapons_ones));
        }
    }

    /* The lives drum. */
    {
        uint8_t d3 = wof_g.lives;

        if ((int8_t)d3 < 0)
            d3 = 0;                                           /* 0x01F102 */
        if (d3 > 9)
            d3 = 9;                                           /* 0x01F10C */
        if ((int16_t)d3 != c->lives) {
            int16_t d0 = (int16_t)(0x59 - (int16_t)(d3 << 3));
            int16_t d2 = wof_g.gauge_lives;

            if (d0 == d2) {
                c->lives = d3;
            } else {
                if (d0 > d2)
                    d2 = (int16_t)(d2 + 1);
                else
                    d2 = (int16_t)(d2 - 1);                   /* 0x01F12E: a life more */
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

    /* The enemy plane counter of 0x02537F: two digits, at most 99, and its kill icons,
     * seven a row in two rows (the manual, page 9). */
    {
        uint16_t d3 = wof_g.g_02537f;

        if (d3 > 0x63)
            d3 = 0x63;                                        /* 0x01F186 */
        if ((int16_t)d3 != c->w0e) {
            int16_t n;

            c->w0e = (int16_t)d3;
            wof_g.clip_top = 0x14;
            wof_g.clip_bottom = 0x1C;
            wof_dash_digit(0x1FC, 0x15, (uint16_t)(d3 / 10u));
            wof_dash_digit(0x20A, 0x15, (uint16_t)(d3 % 10u));
            wof_g.clip_top = 0x13;
            wof_g.clip_bottom = 0x1F;
            n = c->w0e;
            kill_icons((int16_t)(n - 7) > 0 ? 7 : n, 0x216, 0x13);
            n = (int16_t)(n - 7);
            kill_icons((int16_t)(n - 7) > 0 ? 7 : n, 0x216, 0x19);
        }
    }
}
