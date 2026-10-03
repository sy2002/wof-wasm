# tests/test_generated.py, lines 26-32
def test_the_listings_are_their_regeneration(tmp_path):
    generate(tmp_path, 'tools/disasm.py', '--out')
    generate(tmp_path, 'tools/disasm_player.py', '--out')
    for name in ('Wings.lst', 'functions.csv', 'songplay.lst'):
        assert (tmp_path / name).read_bytes() == (ROOT / 're' / name).read_bytes(), (
            're/%s is not what tools/disasm.py and tools/disasm_player.py make: regenerate '
            'and commit it' % name)
