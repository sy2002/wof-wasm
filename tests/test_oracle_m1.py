"""Differential tests for the routines M1 ports (SPEC 7.4 step 4, section 8).

Every pure routine runs twice on the same input - once as the original 68000 code under
the oracle, once as the C the port compiled - and the results are compared.  What the
original's routines need in order to run headlessly, and the three stubs that stand in
for things that are not under test, are in tests/original.py.

The shape blit cannot be compared that way, because the original drives the hardware
blitter.  It is compared through its register programme instead: the original's
shape_draw runs with the custom-chip space mapped as memory, every write to BLTSIZE is
captured with the registers as they stood, and tests/blitter.py replays the programme on
a copy of the bitplanes.  The clipping arithmetic, the pointers, the modulos, the sizes
and the word masks in that comparison are the original's; only the blitter's own area
mode is modelled.

    .venv/bin/python -m pytest tests/test_oracle_m1.py
    WOF_SLOW_ORACLE=1 .venv/bin/python -m pytest tests/test_oracle_m1.py   (the full range)
"""
import os
import random
import struct
import sys

import pytest

from conftest import ROOT

sys.path.insert(0, str(ROOT / 'tools'))

import rpck                                     # noqa: E402
from blitcheck import Reference                 # noqa: E402
from extract_tables import Image                # noqa: E402
from original import Original                   # noqa: E402

SLOW = os.environ.get('WOF_SLOW_ORACLE') == '1'

GAME = ROOT / 'original' / 'disk' / 'Wings_of_Fury'

# The containers in the order src/wof.h gives them, with the file the port loads and the
# name list it resolves against (re/notes/shapes.md).  The disk spells two of them
# differently from the game, which is why the port's file system ignores case.
CONTAINERS = [
    (0,  'shapes/world.shp',      'world_names'),
    (1,  'shapes/hellcat.shp',    'hellcat_names'),
    (2,  'shapes/torpedo.shp',    'torpedo_names'),
    (3,  'shapes/japplane.shp',   'japplane_names'),
    (4,  'shapes/8thscale.shp',   'world_names'),
    (5,  'shapes/dash.shp',       'dash_names'),
    (6,  'shapes/battleship.shp', 'battleship_names'),
    (7,  'shapes/destroyer.shp',  'destroyer_names'),
    (8,  'shapes/cruiseship.shp', 'cruiseship_names'),
    (9,  'shapes/japcarrier.shp', 'japcarrier_names'),
    (10, 'shapes/selectrank.shp', None),
    (11, 'shapes/nightdash.shp',  'dash_names'),
]

# The nine lists in DATA, at the addresses re/tables.toml names.
NAME_LISTS = {
    'battleship_names': (0x023BC0, 25),
    'japcarrier_names': (0x023C28, 13),
    'destroyer_names':  (0x023C60, 27),
    'cruiseship_names': (0x023CD0, 24),
    'hellcat_names':    (0x023D34, 107),
    'world_names':      (0x023EE4, 184),
    'dash_names':       (0x0241C8, 117),
    'torpedo_names':    (0x0243A0, 138),
    'japplane_names':   (0x0245CC, 22),
}

PICTURES = [
    ('shapes/broderbund',   40, 200, 5),
    ('shapes/wingstitle',   40, 200, 5),
    ('shapes/creditscreen', 40, 200, 5),
    ('shapes/selectrank',   40, 200, 5),
    ('shapes/Rank.iff',     80, 147, 3),
    ('shapes/hiscoreslab',  80, 145, 4),
    ('shapes/hiscore.iff',  40,  75, 5),
    ('shapes/iff-dash',     80,  37, 4),
    ('shapes/nightdash',    80,  37, 4),
    ('shapes/ocean.p',      40, 200, 5),
    ('shapes/ocean.palette', 40, 200, 5),
    ('shapes/palette',      40, 200, 5),
]

PALETTE_FILES = ['shapes/wingspalette', 'shapes/night.p', 'shapes/nightocean.p',
                 'shapes/ocean.palette', 'shapes/palette', 'shapes/ocean.p']


@pytest.fixture(scope='session')
def exe():
    return Image(str(GAME / 'Wings'))


@pytest.fixture(scope='session')
def name_lists(exe):
    """The nine lists straight out of the executable, not out of src/gen."""
    out = {}
    for name, (addr, count) in NAME_LISTS.items():
        out[name] = [exe.u32(addr + 4 * i) for i in range(count)]
        assert exe.u32(addr + 4 * count) == 0, name
    return out


@pytest.fixture(scope='session')
def packed_files():
    out = []
    for folder, _, names in os.walk(GAME):
        for name in sorted(names):
            path = os.path.join(folder, name)
            with open(path, 'rb') as handle:
                head = handle.read(8)
            if head[:4] == b'Rpck':
                out.append((os.path.relpath(path, GAME), path,
                            struct.unpack('>I', head[4:8])[0]))
    return sorted(out)


# ------------------------------------------------------------------ the unpacker

def test_rpck_unpack_matches_on_every_packed_file(ported, packed_files):
    assert len(packed_files) == 10, [name for name, _, _ in packed_files]
    for name, path, size in packed_files:
        with open(path, 'rb') as handle:
            raw = handle.read()
        want = Original().rpck_unpack(raw[8:], size)
        got = ported.rpck_unpack(raw[8:], size)
        assert got == want, name


def test_rpck_unpack_matches_on_random_streams(ported):
    """Runs the original's own loop over streams the disk does not contain, including the
    0x80 control byte, which means 128 literals and not a no-op."""
    rng = random.Random(0x57494E47)
    original = Original()

    for case in range(40):
        stream = bytearray()
        produced = 0
        while produced < 600:
            control = rng.randrange(256)
            stream.append(control)
            if control < 0x80:
                stream.append(rng.randrange(256))
                produced += control + 1
            else:
                n = 256 - control
                stream += bytes(rng.randrange(256) for _ in range(n))
                produced += n
        want = original.rpck_unpack(bytes(stream), produced)
        got = ported.rpck_unpack(bytes(stream), produced)
        assert got == want, 'case %d' % case


def test_load_file_returns_the_files_of_the_disk(ported):
    """The whole loader, over the packed file system, against the reference decoder."""
    for folder, _, names in os.walk(GAME):
        for name in sorted(names):
            if name.startswith('.') or name.endswith('.info'):
                continue
            path = os.path.join(folder, name)
            relative = os.path.relpath(path, GAME)
            if relative in ('Wings', 'UFXintro', 'wingt'):
                continue
            want = rpck.load(path)[0]
            declared = rpck.load(path)[1]
            got = ported.load_file(relative)
            assert got is not None, relative
            assert got == want[:declared], relative


def test_load_file_ignores_the_case_of_a_name(ported):
    """The game asks for shapes/Torpedo.shp and shapes/rank.iff; the disk has neither."""
    for asked, on_disk in (('shapes/Torpedo.shp', 'shapes/torpedo.shp'),
                           ('shapes/rank.iff', 'shapes/Rank.iff'),
                           ('SHAPES/WORLD.SHP', 'shapes/world.shp')):
        assert ported.load_file(asked) == ported.load_file(on_disk), asked


# ---------------------------------------------------------------- name resolution

@pytest.mark.parametrize('slot,path,list_name', CONTAINERS)
def test_shape_find_matches_on_every_name(ported, name_lists, slot, path, list_name):
    """Every name of every list, and every name the container itself carries, looked up
    in this container by the original and by the port."""
    original = Original()
    container = original.container(path)
    wanted = sorted({name for names in name_lists.values() for name in names}
                    | set(container['names']))

    for name in wanted:
        want = original.shape_find(container, name)
        got = ported.shape_find(slot, name)
        assert got == want, '%s: %s gave %d, want %d' % (
            path, struct.pack('>I', name), got, want)


def test_shape_find_refuses_a_name_that_is_in_no_container(ported):
    for text in (b'!!!!', b'~~~~', b'    '):
        name = struct.unpack('>I', text)[0]
        original = Original()
        container = original.container('shapes/world.shp')
        assert original.shape_find(container, name) == -1
        assert ported.shape_find(0, name) == -1


@pytest.mark.parametrize('slot,path,list_name', [c for c in CONTAINERS if c[2]])
def test_shapes_resolve_matches(ported, name_lists, slot, path, list_name):
    """The pointer table the original builds and the index table the port builds have to
    agree entry for entry, null for null."""
    original = Original()
    container = original.container(path)
    names = name_lists[list_name]

    want = original.shapes_resolve(container, names)
    got = [ported.table_entry(slot, i) for i in range(len(names))]
    assert got == want, path


def test_shape_by_index_matches(ported):
    original = Original()
    container = original.container('shapes/world.shp')
    for i in range(container['count']):
        assert original.shape_by_index(container, i) == container['records'][i]
        assert ported.shape_by_index(0, i) == i


# ------------------------------------------------------------------- the mirror

@pytest.mark.parametrize('slot,path', [(1, 'shapes/hellcat.shp'), (2, 'shapes/torpedo.shp')])
def test_shape_mirror_x_matches_on_every_shape(ported, slot, path):
    """The original mirrors plane data and bit-reverses each byte; the port reverses the
    converted pixel row.  Both have to leave the same picture and the same hotspot."""
    original = Original()
    container = original.container(path)

    for index in range(container['count']):
        before = ported.shape_pixels(slot, index)
        ported.shape_mirror(slot, index)
        after = ported.shape_pixels(slot, index)

        original.shape_mirror_x(container, index)
        record = original.record(container, index)
        want = record_to_indexed(record)

        name = struct.pack('>I', container['names'][index])
        width = ported.shape_field(slot, index, 'wbytes') * 8

        assert after == want, '%s %s: pixels differ' % (path, name)
        assert ported.shape_field(slot, index, 'hot_x') == struct.unpack('>h', record[4:6])[0]
        if any(before) and not is_symmetric(before, width):
            assert after != before, '%s %s: the mirror changed nothing' % (path, name)

        ported.shape_mirror(slot, index)          # back, for the tests that follow
        original.shape_mirror_x(container, index)
        assert ported.shape_pixels(slot, index) == before, '%s %s: not an involution' % (
            path, name)


def test_the_mirror_marker_rule(ported):
    """load_permanent_shapes writes 2 into +8 of every hellcat and Torpedo record, and
    0x01ABDE mirrors only when the facing it wants differs from what is stored."""
    for slot in (1, 2):
        assert ported.shape_field(slot, 0, 'marker') == 2

    before = ported.shape_pixels(1, 0)
    ported.shape_set_facing(1, 0, 1)              # facing + 1 == 2: nothing happens
    assert ported.shape_pixels(1, 0) == before
    assert ported.shape_field(1, 0, 'marker') == 2

    ported.shape_set_facing(1, 0, 0)              # facing + 1 == 1: mirror
    assert ported.shape_field(1, 0, 'marker') == 1
    mirrored = ported.shape_pixels(1, 0)

    ported.shape_set_facing(1, 0, 1)              # and back
    assert ported.shape_field(1, 0, 'marker') == 2
    assert ported.shape_pixels(1, 0) == before
    assert mirrored != before or is_symmetric(before, ported.shape_field(1, 0, 'wbytes') * 8)


def is_symmetric(pixels, width):
    rows = len(pixels) // width if width else 0
    for y in range(rows):
        row = pixels[y * width:(y + 1) * width]
        if row != row[::-1]:
            return False
    return True


def record_to_indexed(record):
    """One container record's plane data as the port's converted pixels."""
    wbytes, height = struct.unpack('>HH', record[0:4])
    masks = [b for b in record[14:20] if b]
    width = wbytes * 8
    out = bytearray(width * height)

    for index, mask in enumerate(masks):
        plane = record[20 + index * wbytes * height:20 + (index + 1) * wbytes * height]
        for y in range(height):
            row = plane[y * wbytes:(y + 1) * wbytes]
            for x in range(width):
                bit = (row[x >> 3] >> (7 - (x & 7))) & 1
                at = y * width + x
                out[at] = (out[at] & ~mask) | (mask if bit else 0)
    return bytes(out)


def test_every_shape_converts_to_the_same_pixels(ported):
    """The conversion at load, against the plane data the original keeps."""
    for slot, path, _ in CONTAINERS:
        original = Original()
        container = original.container(path)
        assert ported.container_shapes(slot) == container['count'], path
        for index in range(container['count']):
            want = record_to_indexed(original.record(container, index))
            assert ported.shape_pixels(slot, index) == want, '%s %d' % (path, index)


# ------------------------------------------------------------------- colour_lerp

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


# -------------------------------------------------------------------------- text

TEXT_CASES = [
    ('HELLO', 0, 0, 0),
    ('Wings of Fury', 3, 0, 0),
    ('A TIME OF FURY', 0, 0, 400),
    ('x', 5, 0, 0),
    ('  spaced  text  ', 1, 0, 500),
    ('AV.,;:!?', 15, 0, 0),
    ('0123456789', 7, 0, 320),
    (''.join(chr(c) for c in range(0x20, 0x50)), 0, 0, 0),
    (''.join(chr(c) for c in range(0x50, 0x7F)), 0, 0, 0),
    ('\x01\x1f\x7f\x80\xff ok', 0, 0, 0),
]


def test_text_width_matches(ported):
    original = Original()
    original.font_load()
    for text, _, _, _ in TEXT_CASES:
        assert ported.text_width(text) == original.text_width(text), repr(text)


def test_text_render_matches(ported):
    """text_render builds a 1-bit template in plain memory, so the comparison is the
    bytes themselves - the whole template, not only the glyphs."""
    original = Original()
    original.font_load()

    for text, x, row, justify in TEXT_CASES:
        want_width, want = original.text_render(text, x, row, justify, 640, 12)
        got_width, got = ported.text_render(text, x, row, justify, 640, 12)
        assert got_width == want_width, repr(text)
        assert got == want, '%r: template differs in %d bytes' % (
            text, sum(1 for a, b in zip(got, want) if a != b))


def test_text_render_refuses_what_does_not_fit(ported):
    """Text wider than the buffer, and a buffer taller than the font, both give 0."""
    original = Original()
    original.font_load()
    long_text = 'M' * 80

    for buf_w, buf_h in ((320, 12), (640, 13), (64, 12)):
        want_width, want = original.text_render(long_text, 0, 0, 0, buf_w, buf_h)
        got_width, got = ported.text_render(long_text, 0, 0, 0, buf_w, buf_h)
        assert (got_width, got) == (want_width, want), (buf_w, buf_h)


# ---------------------------------------------------------------------- pictures

@pytest.mark.parametrize('path,bytes_per_row,rows,depth', PICTURES)
def test_iff_to_vport_matches_on_every_picture(ported, path, bytes_per_row, rows, depth):
    """ByteRun1 and the whole reader: the planes the original decodes, converted to
    indexed pixels, against the indexed pixels the port produces, and the colour table
    with them."""
    original = Original()
    vport = original.viewport(bytes_per_row, rows, depth)
    original.iff_to_vport(path, vport)
    want = original.vport_indexed(vport)
    want_colours = original.vport_colours(vport)

    got, got_colours = ported.iff_decode(path, bytes_per_row * 8, rows, depth)
    assert got == want, '%s: %d pixels differ' % (
        path, sum(1 for a, b in zip(got, want) if a != b))
    assert got_colours == want_colours, path


def test_a_picture_taller_than_its_viewport_is_cut_off(ported):
    """broderbund, wingstitle and selectrank are 256 rows and show their first 200."""
    for path in ('shapes/broderbund', 'shapes/wingstitle', 'shapes/selectrank'):
        tall, _ = ported.iff_decode(path, 320, 256, 5)
        short, _ = ported.iff_decode(path, 320, 200, 5)
        assert short == tall[:320 * 200], path


def test_cmap_file_to_table_matches(ported):
    """The bare-CMAP palette files, through the reader the game uses for them."""
    original = Original()
    for path in PALETTE_FILES:
        want = original.cmap_file_to_table(path)
        got = ported.cmap_file_to_table(path)
        assert got == want, path


# ------------------------------------------------------------------------ the blit

POSITIONS_5 = [(0, 0), (37, 40), (16, 8), (-9, -5), (300, 150), (-40, 60)]
POSITIONS_4 = [(21, 3), (-7, -2), (600, 20)]

CLIP_FULL_5 = (0, 162, 0, 320)
CLIP_INNER_5 = (10, 120, 32, 288)
CLIP_FULL_4 = (0, 37, 0, 640)


def background(width, rows, seed, depth=5):
    """A background the target can really hold: on a 4-plane bitmap there is no bit 4,
    so a pixel value above 15 could not have got there in the first place."""
    if seed is None:
        return bytes(width * rows)
    rng = random.Random(seed)
    return bytes(rng.randrange(1 << depth) for _ in range(width * rows))


@pytest.mark.parametrize('slot,path,list_name', CONTAINERS)
def test_shape_blit_matches_the_blitter(ported, slot, path, list_name):
    """Every shape of this container, at six positions - word-aligned and shifted, inside
    the target and hanging off each edge - over an empty and a non-empty background, on
    the 5-plane playfield.  The original's blits are captured at BLTSIZE and replayed by
    the model in tests/blitter.py."""
    reference = Reference(path, 40, 162, 5)
    empty = background(320, 162, None)
    noisy = background(320, 162, 4711)

    for index in range(reference.count):
        for x, y in POSITIONS_5:
            for clip in (CLIP_FULL_5, CLIP_INNER_5):
                for bg in (empty, noisy):
                    want = reference.draw(index, x, y, clip, bg)
                    got = ported.blit(slot, index, 40, 162, 5, clip, x, y, bg)
                    assert got == want, '%s %s at (%d,%d) clip %s: %d pixels differ' % (
                        path, struct.pack('>I', reference.name(index)), x, y, clip,
                        sum(1 for a, b in zip(got, want) if a != b))


@pytest.mark.parametrize('slot,path', [(5, 'shapes/dash.shp'), (11, 'shapes/nightdash.shp'),
                                       (0, 'shapes/world.shp'), (1, 'shapes/hellcat.shp')])
def test_shape_blit_matches_on_a_four_plane_target(ported, slot, path):
    """The dashboard has four planes, so bit 4 of every plane mask and of the clear and
    set bytes is dropped.  Five-plane shapes are drawn there too, to prove it."""
    reference = Reference(path, 80, 37, 4)
    noisy = background(640, 37, 99, depth=4)

    for index in range(reference.count):
        for x, y in POSITIONS_4:
            want = reference.draw(index, x, y, CLIP_FULL_4, noisy)
            got = ported.blit(slot, index, 80, 37, 4, CLIP_FULL_4, x, y, noisy)
            assert got == want, '%s %s at (%d,%d): %d pixels differ' % (
                path, struct.pack('>I', reference.name(index)), x, y,
                sum(1 for a, b in zip(got, want) if a != b))


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


# ------------------------------------------------------------------- the system font

def test_the_system_font_came_out_of_the_rom():
    """topaz 8 is not on the game disk; the build takes it from the owner's Kickstart
    ROM by looking for its contents, so that another Kickstart version works too
    (re/notes/system-font.md)."""
    import extract_tables

    with open(ROOT / 'original' / 'kick.rom', 'rb') as handle:
        rom = handle.read()
    font = extract_tables.find_topaz8(rom)

    assert font is not None, 'no topaz 8 found in original/kick.rom'
    assert (font['ysize'], font['xsize'], font['baseline']) == (8, 8, 6)
    assert (font['lo'], font['hi']) == (0x20, 0xFF)
    assert font['modulo'] == 192

    glyphs = font['hi'] - font['lo'] + 2
    bitmap = rom[font['data']:font['data'] + font['modulo'] * font['ysize']]
    assert len(bitmap) == font['modulo'] * font['ysize']
    assert any(bitmap), 'the glyph bitmap is empty'

    # The location table is bit offset and bit width per glyph, and topaz is fixed width.
    locations = struct.unpack('>%dH' % (2 * glyphs),
                              rom[font['loc']:font['loc'] + 4 * glyphs])
    widths = set(locations[1::2])
    assert widths == {font['xsize']}, widths
    assert locations[0] == 0
    assert max(locations[0::2]) + font['xsize'] <= font['modulo'] * 8


def test_the_build_falls_back_when_the_rom_is_absent(tmp_path, capsys):
    """SPEC 5 step 1: no ROM means the game's own font and a message, not a failed build."""
    import extract_tables

    header, source, messages = [], [], []
    saved = extract_tables.ROM
    try:
        extract_tables.ROM = str(tmp_path / 'not-a-rom')
        extract_tables.emit_sysfont({'name': 'topaz8'}, header, source, messages.append)
    finally:
        extract_tables.ROM = saved

    assert any('kick.rom is absent' in message for message in messages), messages
    assert any('fall back to the game' in message for message in messages), messages
    assert 'const int      wof_tbl_topaz8_present  = 0;' in source
