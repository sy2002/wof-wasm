/* The object records (M5): the weapons in flight and the explosions, as the pass draws them,
 * in the original's address order (re/notes/objects.md; re/notes/porting-m5.md, "The object
 * records").
 *
 * A record's +0x22 is its type, the weapon it is: 0 a rocket, 1 a bomb, 2 the torpedo, the
 * weapon_type (0x0253A4) at the drop; an explosion object_spawn's first entry makes is of
 * type 1.  Its +0x20 is its kind: 0xFF while it flies, 8 while it goes out, 0 when free.
 * The guns' rounds are no object at all (0x0119BC takes the ground they hit directly).
 */
#include "wof.h"

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
