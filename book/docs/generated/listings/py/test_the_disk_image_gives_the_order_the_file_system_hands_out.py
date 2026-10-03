# tests/test_frontend.py, lines 143-153
def test_the_disk_image_gives_the_order_the_file_system_hands_out():
    """ExNext walks chain 0 upward, and inside a chain from its head.  The name hash decides the
    chain, which every entry of five directory blocks of original/wof.adf confirms."""
    order = headless_os.adf_order([])
    assert [name for _, name in order] == [
        'Wings', 'wingt', '.info', 'shapes', 'wofsongs', 'wings.info', 'maps', 'sounds',
        'UFXintro', 'highscore', 'songplay', 'newarmyfont', 'rank.iff.info', 'wof.mission 3']
    assert all(headless_os.name_hash(name) == chain for chain, name in order)
    assert all(headless_os.name_hash(name) == chain
               for chain, name in headless_os.adf_order(['shapes']))
    assert set(name for _, name in order) <= set(os.listdir(DISK)), 'the disk image names a file that is not there'
