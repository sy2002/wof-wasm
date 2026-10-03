# tests/test_frontend.py, lines 248-255
def test_control_f_flips_the_vertical_control(flight):
    """The command the owner needs.  Control and the F key toggle the byte read_joy_bits reads;
    the same key without Control does nothing."""
    flipped, plain, twice = run('flight-control-f'), run('flight-plain-f'), run('flight-control-f-twice')
    assert byte(flight, OPT_INVERT_VERTICAL) == 0
    assert byte(flipped, OPT_INVERT_VERTICAL) == 0xFF
    assert byte(plain, OPT_INVERT_VERTICAL) == 0, 'the F key alone flipped the control'
    assert byte(twice, OPT_INVERT_VERTICAL) == 0, 'the flip did not toggle back'
