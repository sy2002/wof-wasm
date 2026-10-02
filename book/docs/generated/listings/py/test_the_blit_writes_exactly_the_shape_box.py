# tests/test_oracle_m1.py, lines 495-517
def test_the_blit_writes_exactly_the_shape_box(ported):
    """An independent statement about the register programme, not about the port: the
    blitter's first and last word masks leave the destination alone everywhere outside
    the shape's own box and outside the clip rectangle, however the blit is shifted.
    This is what lets the port clip per pixel."""
    reference = Reference('shapes/world.shp', 40, 162, 5)
    ones = bytes([31]) * (320 * 162)
    zeros = bytes(320 * 162)

    for index in range(0, reference.count, 7):
        width, height = reference.shape_size(index)
        for x, y in ((33, 20), (48, 20), (-5, -3), (310, 155)):
            for clip in (CLIP_FULL_5, CLIP_INNER_5):
                lit = reference.draw(index, x, y, clip, zeros)
                dark = reference.draw(index, x, y, clip, ones)
                touched = {i for i in range(len(ones)) if lit[i] or dark[i] != 31}
                box = {(y + r) * 320 + (x + c)
                       for r in range(height) for c in range(width)
                       if clip[0] <= y + r < clip[1] and clip[2] <= x + c < clip[3]
                       and 0 <= x + c < 320 and 0 <= y + r < 162}
                assert touched <= box, (
                    'a blit of %s at (%d,%d) touched %d pixels outside its box'
                    % (struct.pack('>I', reference.name(index)), x, y, len(touched - box)))
