# tests/test_oracle_m1.py, lines 320-350
def test_colour_lerp_matches_over_its_range(ported):
    """The 16 steps against black and white in both directions, which is every fade the
    game runs, plus random triples.  The three components are independent apart from the
    carry between them, and the sweeps exercise that carry at every step.

    WOF_SLOW_ORACLE=1 runs the whole 16 x 4096 x 4096 cross product instead.
    """
    original = Original()

    def compare(step, source, target):
        want = original.colour_lerp(step, source, target)
        got = ported.colour_lerp(step, source, target)
        assert got == want, 'step %d, %03X -> %03X: %04X, want %04X' % (
            step, source, target, got, want)

    if SLOW:
        for step in range(16):
            for source in range(0x1000):
                for target in range(0x1000):
                    compare(step, source, target)
        return

    for step in range(16):
        for value in range(0x1000):
            compare(step, value, 0x000)
            compare(step, value, 0xFFF)
            compare(step, 0x000, value)

    rng = random.Random(11)
    for _ in range(20000):
        compare(rng.randrange(16), rng.randrange(0x1000), rng.randrange(0x1000))
