# tests/test_music.py, lines 141-149
def test_the_timer_ticks_at_the_songs_tempo(idle_front):
    """The songs set only the latch's high byte, 56 here; the low byte keeps its power-up
    0xFF, so a tick comes every 0x38FF + 1 E cycles, 14,592 x 5 x 50 units on PAL; the
    first after the timer opens at the power-up latch, 65,536 cycles after it."""
    ticks = idle_front.paula.timer.calls
    tick = headless_paula.E_CLOCK_CC * 50
    assert ticks[0][2] == 0xFFFF and ticks[0][1] == headless_paula.PAL_CLOCK + 0x10000 * tick
    steady = [b[1] - a[1] for a, b in zip(ticks, ticks[1:]) if a[2] == b[2] == 0x38FF]
    assert len(steady) > 5000 and set(steady) == {0x3900 * tick}
