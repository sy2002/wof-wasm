# tests/test_oracle_m3.py, lines 450-463
@pytest.mark.parametrize('depth, depth2, colours2, pair, to_black', [
    (5, 0, False, False, False),      # the picture screens: one viewport, one table
    (5, 0, False, False, True),       # fade_out, whose carry is what the note warns about
    (4, 0, True,  False, False),      # a viewport with a second colour table
    (4, 0, True,  False, True),
    (3, 0, False, False, False),      # the briefing
    (5, 4, False, True,  False),      # the high-score screen: two viewports, two targets
    (5, 4, True,  True,  False),
    (5, 4, True,  True,  True),       # fade_out_pair, which ends the mission
])
def test_the_fades_agree_with_the_original(ported, depth, depth2, colours2, pair, to_black):
    rng = random.Random(0x1234 + depth * 16 + depth2 + pair * 4 + to_black * 2 + colours2)
    for _ in range(4):
        fade_case(ported, rng, depth, depth2, colours2, pair, to_black)
