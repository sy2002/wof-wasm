# tools/m5_autopilot.py, lines 116-138
def fall(m, s):
    """Where a bomb dropped now comes down, as object_step moves a type-1 record (0x010B58):
    the horizontal speed loses a tenth of its whole part every tick, the vertical long loses
    g_025350, and the height is the whole part of the vertical long plus the height with its
    old fraction.  It explodes at height 0x0C over land or sea (0x010C04, 0x010C1A).  The
    fraction the record keeps from its last use is taken as 0 here; the plan's `lead`
    absorbs the rest."""
    g = s32(m.o.r32(GRAVITY))
    x = s['x'] << 16
    dx = s['sx'] << 16
    if s['face'] < 0:
        dx = -dx
    vy = s['sy'] << 16
    y = (s['y'] + 0x0B) << 16
    for _ in range(400):
        q = int((dx >> 16) / 10)
        dx -= q << 16
        x += dx
        vy -= g
        y = ((vy + y) >> 16) << 16
        if (y >> 16) <= 0x0C:
            break
    return x >> 16
