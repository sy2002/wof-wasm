# tests/test_campaign.py, lines 131-160
@pytest.mark.parametrize('name', ['save_a'])
def test_the_saved_file_is_the_originals_but_for_its_pointers(ported, name):
    """The file save_a's save in the hold writes (wof.save, map f) is the one the headless
    original wrote in the same run, byte for byte, except where the raw part holds a pointer
    to the original's own memory: the player's shape, the two shape pointers of the tick and
    the cruise ship's gun list.  Every differing byte is listed with its field and reason."""
    if (name, 2) not in SAVED:
        assert_closed(*closed_loop(ported, name))
    originals, ports = SAVED[(name, 2)]
    saved = [n for n in originals if n != 'wof.mission 3']
    assert saved == ['wof.save'], saved
    original, port = originals['wof.save'], ports.get('wof.save')
    assert port is not None and len(port) == len(original) == 6424, (len(original), port and len(port))
    fields = savegame.registry()
    differing = {}
    for i, (a, b) in enumerate(zip(original, port)):
        if a == b:
            continue
        field = savegame.field_of(savegame.RAW_START + i, fields) if i < savegame.RAW_LENGTH else None
        assert field is not None and field[1] in POINTER_REASONS, (
            'byte %d (0x%06X) differs, original %02x, port %02x, in %s' % (
                i, savegame.RAW_START + i, a, b, field))
        differing.setdefault(field, []).append(i)
    assert sorted(differing) == [('g_02541a[0].s', 'shape'), ('player[0].shape', 'shape'),
                                 ('ship_records[2].guns', 'pool'),
                                 ('torpedo_shape[0].s', 'shape')], sorted(differing)
    guns = savegame.SHIPS + 2 * savegame.SHIP_SIZE + 6 - savegame.RAW_START
    assert port[guns:guns + 4] == b'\0\0\0\1', port[guns:guns + 4]
    info = savegame.summary(port)
    assert info['exact'] and info['map'] == 'f' and info['ships'] == ['guns cruiseship'], info
