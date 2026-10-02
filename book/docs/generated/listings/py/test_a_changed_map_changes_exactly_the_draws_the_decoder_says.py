# tests/test_map.py, lines 180-208
def test_a_changed_map_changes_exactly_the_draws_the_decoder_says(tmp_path):
    """The control: one record of the map is given another slot and another height, laid over
    the disk through the run description's `files`.  Everything the decoder predicts for the
    first passes changes with it, and nothing else in the state does."""
    chart = map_decode.load('a')
    index = next(i for i, word in enumerate(chart.words)
                 if word & 0x8000 and (word >> 2) & 0x1FF == 0x27)
    changed = list(chart.words)
    changed[index] = (changed[index] & ~0x7FC & ~0x3800) | (0x24 << 2) | (3 << 11)
    data = struct.pack('>LL', chart.length, chart.start) + struct.pack(
        '>%dH' % chart.on_disk, *changed[:chart.on_disk])
    plain = flight()
    laid = flight(files={'maps/a.map': data.hex()})
    other = map_decode.Map('a', data)

    tables, views = tables_of(laid), passes_of(laid)
    for view in views:
        assert observed(laid, view, tables) == predicted(other, view, tables), view['pass']

    # What differs between the two runs is the map itself and what the changed record feeds:
    # the copy in memory, and the ground height the tick takes from it.
    before, after = passes_of(plain), views
    assert [view['player_x'] for view in before] == [view['player_x'] for view in after]
    differing = [i for i, (a, b) in enumerate(zip(before, after))
                 if observed(plain, a, tables_of(plain)) != observed(laid, b, tables)]
    assert differing, 'the changed record never reached the screen'
    for i in differing:
        assert (predicted(chart, before[i], tables_of(plain))
                != predicted(other, after[i], tables)), i
