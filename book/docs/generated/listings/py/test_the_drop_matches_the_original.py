# tests/test_oracle_m5.py, lines 707-727
def test_the_drop_matches_the_original(tick):
    """0x01107C with 0x0107F2 and the launch at 0x01088E: every weapon type, counts from none
    to unlimited, bearings up and down, both facings, with free records and none."""
    d = tick
    o = d.o
    rng = random.Random(0x1107)
    for n in range(1500):
        d.randomise_tick(rng)
        w(o, 0x0253A4, rng.choice([0, 1, 2]))                          # weapon_type
        o.write(0x02536D, bytes([rng.choice([0, 1, 5, 30, 0xFF])]))    # weapon_count
        w(o, 0x025404, rng.randrange(-0x400, 0x400))
        w(o, 0x025414, rng.randrange(0, 1600))                         # airspeed
        for k in (0x026E62, 0x026E66, 0x026E6A, 0x026E6E):
            o.w32(k, rng.randrange(1 << 32))
        if n % 5 == 0:
            for i in range(15):
                o.write(OBJECTS + 0x2A * i + 0x20, bytes([0xFF]))
        d.load_port()
        o.call(0x01107C)
        d.port(0x01107C)
        check(d, 'case %d' % n)
