# tools/map_decode.py, lines 80-108
def draw_list(chart, player_x, view_step=8, view_shift=0, split_row=0, slot_used=None,
              ride=None):
    """The map draws of one pass, in the order `draw_world` makes them.

    player_x is the drawing's copy of the player's world x (`0x026E5C`).  slot_used(slot)
    says whether that slot of the pointer table holds a shape; a null slot is skipped.
    ride(world_x) gives the rows a record of `low` 1 is moved down by, which is the ship it
    stands on (`0x014EAC` through `0x014A4E`); without it such a record keeps its own row.
    Returns [(index, slot, screen_x, screen_y, record)], where screen_x and screen_y are
    what `draw_world` hands `shape_draw` before the shape's hotspot is taken off."""
    x = player_x & 0xFFF8 if view_step == 1 else player_x
    margin = MARGIN_FULL if view_step == 8 else MARGIN_EIGHTH
    offset = (((x - margin) & 0xFFFF) ^ 0x8000) - 0x8000        # a signed word
    offset = (offset >> 2) & ~1                                 # asr.w #2, then bclr #0
    index = offset // 2
    screen_x = (8 - (x & 7) - 128)
    out = []
    while screen_x < SCREEN_END:
        if 0 <= index < len(chart.words) - 1:        # the last record is read but never drawn
            record = chart.record(index)
            if record['draw'] and (slot_used is None or slot_used(record['slot'])):
                y = 0x97 if view_shift else split_row + HEIGHT_STEP * record['height']
                if record['low'] == 1 and ride is not None:
                    world_x = (screen_x - 0xA0) * (8 if view_shift else 1) + player_x
                    y += ride(world_x & 0xFFFF)
                out.append((index, record['slot'], screen_x - 8, y, record))
        index += 1
        screen_x += view_step
    return out
