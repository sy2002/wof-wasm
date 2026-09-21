"""M4 differential tests: the drawing primitives of the pass and the pure routines of the
world, against the original (SPEC 7.4, re/notes/porting-m4.md).

The blits (V5) run as 68000 code under the oracle with the custom chips mapped as plain
memory; the blits they start are captured at BLTSIZE and replayed by the model in
tests/blitter.py over the same background the port draws on.  The pure routines (V6) run
twice on the same randomised input, once under the oracle and once as the port's C, and
their results, flags and the memory they write are compared.
"""
import os
import random
import sys

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, 'tools'))
sys.path.insert(0, HERE)

import ctypes                        # noqa: E402

from blitcheck import Reference      # noqa: E402

CUSTOM = 0xDFF000
RECT_FILL = 0x021010
SHAPE_BLIT = 0x020B0C
DIGIT = 0x01F2B0

WORLD, DASH, NIGHTDASH = 0, 5, 11


def background(width, rows, seed, depth):
    if seed is None:
        return bytes(width * rows)
    rng = random.Random(seed)
    return bytes(rng.randrange(1 << depth) for _ in range(width * rows))


def draw_op(ported, op, target, clip, background, slot=0, index=0, a=0, b=0, c=0, d=0, e=0):
    lib = ported.lib
    f = lib.wt_draw_op
    f.argtypes = [ctypes.c_int] * 15 + [ctypes.c_char_p, ctypes.c_char_p]
    f.restype = ctypes.c_int
    bytes_per_row, rows, depth = target
    out = ctypes.create_string_buffer(len(background))
    n = f(op, slot, index, bytes_per_row, rows, depth, clip[0], clip[1], clip[2], clip[3],
          a, b, c, d, e, background, out)
    assert n == len(background), (op, slot, index, n)
    return out.raw


def differ(got, want):
    return sum(1 for x, y in zip(got, want) if x != y)


# ------------------------------------------------------------------ V5: rect_fill

PLAYFIELD = (40, 162, 5)
DASHBOARD = (80, 37, 4)
CLIPS = {PLAYFIELD: [(0, 162, 0, 320), (10, 120, 32, 288), (0, 0x6C, 0, 320)],
         DASHBOARD: [(0, 37, 0, 640), (7, 0x20, 0x100, 0x190), (0x0B, 0x12, 0, 640)]}


@pytest.mark.parametrize('target', [PLAYFIELD, DASHBOARD], ids=['5-plane', '4-plane'])
def test_rect_fill_matches_the_blitter(ported, target):
    """Random rectangles - inside, across every edge, beyond the target, empty and one pixel
    wide - in every colour of the target, under the clips the pass uses (the playfield, the
    ocean band above the waterline, the dashboard, its map window and its score row)."""
    bytes_per_row, rows, depth = target
    width = bytes_per_row * 8
    reference = Reference('shapes/world.shp', bytes_per_row, rows, depth)
    o = reference.original.o
    rng = random.Random(0x4D34 + depth)
    noisy = background(width, rows, 7 + depth, depth)
    changed = 0
    for n in range(120):
        clip = rng.choice(CLIPS[target])
        x0 = rng.randrange(-40, width + 40)
        y0 = rng.randrange(-20, rows + 20)
        if n % 10 == 0:
            x1, y1 = x0, y0
        else:
            x1 = x0 + rng.randrange(-8, width // 2)
            y1 = y0 + rng.randrange(-4, rows)
        colour = rng.randrange(1 << depth)
        bg = noisy if n % 2 else bytes(width * rows)

        def call():
            o.call(RECT_FILL, regs={'d0': x0 & 0xFFFF, 'd1': y0 & 0xFFFF, 'd2': x1 & 0xFFFF,
                                    'd3': y1 & 0xFFFF, 'd4': colour, 'a6': CUSTOM})
        want = reference.replay(clip, bg, call)
        got = draw_op(ported, 2, target, clip, bg, a=x0, b=y0, c=x1, d=y1, e=colour)
        assert got == want, 'rect_fill (%d,%d)-(%d,%d) colour %d clip %s: %d pixels differ' % (
            x0, y0, x1, y1, colour, clip, differ(got, want))
        changed += want != bg
    assert changed >= 30, 'only %d of the fills drew anything' % changed


# ------------------------------------------------------- V5: shape_blit without a mask

POSITIONS_5 = [(0, 0), (0xFA - 8, 0x3C - 4), (37, 40), (-9, -5), (300, 150)]
POSITIONS_4 = [(0x10, 0x0B), (21, 3), (-7, -2), (600, 20)]


@pytest.mark.parametrize('slot,path,target,step', [
    (WORLD, 'shapes/world.shp', PLAYFIELD, 5),
    (DASH, 'shapes/dash.shp', DASHBOARD, 1),
    (NIGHTDASH, 'shapes/nightdash.shp', DASHBOARD, 1),
], ids=['world-5-plane', 'dash-4-plane', 'nightdash-4-plane'])
def test_shape_blit_without_a_mask_matches_the_blitter(ported, slot, path, target, step):
    """The weapon marker blits two world shapes and the dashboard its weapon icon and its
    digit drums with A1 = 0: the shape's whole box is written, no mask.  Every dashboard
    shape and every fifth world shape (among them 0x4A to 0x4D, the marker's) at aligned,
    shifted and hanging-off positions, under the full and a narrow clip."""
    bytes_per_row, rows, depth = target
    width = bytes_per_row * 8
    reference = Reference(path, bytes_per_row, rows, depth)
    o = reference.original.o
    noisy = background(width, rows, 99, depth)
    indices = sorted(set(range(0, reference.count, step)) |
                     ({0x4A, 0x4B, 0x4C, 0x4D} if slot == WORLD else set()))
    changed = cases = 0
    for index in indices:
        record = reference.container['records'][index]
        for x, y in (POSITIONS_5 if target == PLAYFIELD else POSITIONS_4):
            for clip in CLIPS[target][:2]:
                def call():
                    o.call(SHAPE_BLIT, regs={'a0': record, 'a1': 0, 'd0': x & 0xFFFF,
                                             'd1': y & 0xFFFF, 'a6': CUSTOM})
                want = reference.replay(clip, noisy, call)
                got = draw_op(ported, 1, target, clip, noisy, slot=slot, index=index, a=x, b=y)
                assert got == want, '%s %d at (%d,%d) clip %s: %d pixels differ' % (
                    path, index, x, y, clip, differ(got, want))
                changed += want != noisy
                cases += 1
    assert changed > cases // 3, 'only %d of %d blits drew anything' % (changed, cases)


# ------------------------------------------------------------ V5: the digit slices

# The digits of draw_dashboard: the score's seven and the counter's two, with the rows
# their callers clip to (src/dash.c).
DIGITS = [((0x0B, 0x12), [(0x200 + 14 * i, 0x0B) for i in range(7)]),
          ((0x14, 0x1C), [(0x1FC, 0x15), (0x20A, 0x15)])]


@pytest.mark.parametrize('slot,path', [(DASH, 'shapes/dash.shp'), (NIGHTDASH, 'shapes/nightdash.shp')],
                         ids=['day', 'night'])
def test_the_digit_slices_match_the_blitter(ported, slot, path):
    """0x01F2B0: a slice of dashboard frame 7 at the row digit_rows gives the digit, added
    to the low byte of y and sign-extended, blitted without a mask and cut by the drum's
    clip rows.  Every digit at every drum position of the dashboard."""
    lib = ported.lib
    lib.wt_dash_index.argtypes = [ctypes.c_int, ctypes.c_int]
    index = lib.wt_dash_index(7, 1 if slot == NIGHTDASH else 0)
    assert index >= 0
    reference = Reference(path, 80, 37, 4)
    o = reference.original.o
    table = o.alloc(4 * 8, fill=0)
    o.w32(table + 4 * 7, reference.container['records'][index])
    noisy = background(640, 37, 5, 4)
    changed = cases = 0
    for rows, places in DIGITS:
        clip = (rows[0], rows[1], 0, 0x280)
        for x, y in places:
            for digit in range(10):
                def call():
                    o.call(DIGIT, regs={'d0': x, 'd1': y, 'd2': digit, 'a3': table,
                                        'a6': CUSTOM})
                want = reference.replay(clip, noisy, call)
                got = draw_op(ported, 3, DASHBOARD, clip, noisy, slot=slot, a=x, b=y, e=digit)
                assert got == want, 'digit %d at (%d,%d) rows %s: %d pixels differ' % (
                    digit, x, y, rows, differ(got, want))
                changed += want != noisy
                cases += 1
    assert changed == cases, 'only %d of %d digits drew anything' % (changed, cases)


@pytest.mark.parametrize('slot,path', [(DASH, 'shapes/dash.shp'), (NIGHTDASH, 'shapes/nightdash.shp')],
                         ids=['day', 'night'])
def test_the_drum_slices_match_the_blitter(ported, slot, path):
    """The weapon counter's two drums and the lives drum: dashboard frame 6 drawn with its
    mask at every row the drums stand at (0x50 - 8n and 0x59 - 8n) and every row between,
    as they turn, cut by the drums' clip rows 0x13 to 0x1C."""
    lib = ported.lib
    lib.wt_dash_index.argtypes = [ctypes.c_int, ctypes.c_int]
    index = lib.wt_dash_index(6, 1 if slot == NIGHTDASH else 0)
    assert index >= 0
    reference = Reference(path, 80, 37, 4)
    record = reference.container['records'][index]
    hot_x = reference.original.o.r16(record + 4, signed=True)
    hot_y = reference.original.o.r16(record + 6, signed=True)
    noisy = background(640, 37, 6, 4)
    clip = (0x13, 0x1C, 0, 0x280)
    changed = cases = 0
    for x, base in ((0x2A, 0x1C), (0x42, 0x1C), (0x7D, 0x13)):
        for drum in range(0x08, 0x5A, 3):
            px, py = x - hot_x, base + drum - hot_y
            want = reference.draw(index, px, py, clip, noisy)
            got = ported.blit(slot, index, 80, 37, 4, clip, px, py, noisy)
            assert got == want, 'drum at (%d,%d): %d pixels differ' % (px, py, differ(got, want))
            changed += want != noisy
            cases += 1
    assert changed > cases // 2, 'only %d of %d drum slices drew anything' % (changed, cases)


# ------------------------------------------------------- V6: vblank_server's mission half

TICKER_HALF = 0x011842          # from the test of outside_mission to vblank_server's end
TICKER_TEXT = 0x02716A          # one of the tick's sprintf targets for a message
TICKER_BYTES = 84 * 13


def ticker_state(o):
    return {'outside_mission': o.read(0x02464E, 1)[0], 'g_025410': o.r16(0x025410),
            'g_0255c8': o.r16(0x0255C8), 'g_0255e0': o.r16(0x0255E0),
            'ticker_message': o.r32(0x0257B6)}


@pytest.mark.parametrize('message', [
    'MISSION ACCOMPLISHED  1250 POINTS',
    ''.join(chr(c) for c in range(0x20, 0x7F)),
], ids=['words', 'every-printable'])
def test_the_ticker_matches_the_original(ported, message):
    """0x011842 to 0x01195C under the oracle and the port's wof_vblank_ticker, VBlank by
    VBlank from a noisy plane until the message has scrolled out: the plane, the counter
    0x025410, the pixels left to scroll, the glyph width and the message pointer.  No
    script of M4 shows a message, so this is the only check of the glyph copy."""
    import numpy
    import original

    machine = original.Original()
    machine.font_load()
    o = machine.o
    plane = o.alloc(TICKER_BYTES + 0x100, fill=0)
    rng = random.Random(len(message))
    noise = bytes(rng.randrange(256) for _ in range(TICKER_BYTES))
    o.write(plane, noise)
    o.w32(0x0272A2, plane)
    text = message.encode('latin1') + b'\0'
    o.write(TICKER_TEXT, text)
    o.write(0x02464E, b'\0')
    o.w16(0x025410, 7)
    o.w16(0x0255C8, 0)
    o.w16(0x0255E0, 0)
    o.w32(0x0257B6, TICKER_TEXT)
    trampoline = o.alloc_bytes(bytes.fromhex('48E7FFFE4EF9') + TICKER_HALF.to_bytes(4, 'big'))

    for i, b in enumerate(text):
        ported.set_g('ticker_text', b, index=i)
    for name, value in ticker_state(o).items():
        ported.set_g(name, value)
    lib = ported.lib
    lib.wt_ticker_run.argtypes = [ctypes.c_char_p, ctypes.c_char_p]
    pixels = numpy.unpackbits(numpy.frombuffer(noise, dtype=numpy.uint8)).tobytes()
    out = ctypes.create_string_buffer(len(pixels))

    glyphs = 0
    for vblank in range(12 * len(message) + 0x2A0 + 40):
        o.call(trampoline)
        lib.wt_ticker_run(pixels, out)
        pixels = out.raw
        want = numpy.unpackbits(numpy.frombuffer(bytes(o.read(plane, TICKER_BYTES)),
                                                 dtype=numpy.uint8)).tobytes()
        assert pixels == want, 'VBlank %d: %d pixels of the ticker differ' % (
            vblank, sum(1 for a, b in zip(pixels, want) if a != b))
        state = ticker_state(o)
        got = {name: ported.g(name) for name in state}
        assert got == state, 'VBlank %d: %s' % (vblank, got)
        glyphs += state['g_0255c8'] == 0x2A0
    assert o.r32(0x0257B6) == 0 and glyphs >= len(message)
    assert o.read(plane + TICKER_BYTES, 0x100) == bytes(0x100), 'the glyph copy ran past the plane'


# ------------------------------------------------------------ V6: draw_game_over's count

A4 = 0x02AFFE
GAME_OVER, GAME_OVER_COUNT, QUIT_FLAG = 0x025362, 0x0255C2, 0x0253C2


def stub_slots(o, returns_zero=(), plain=()):
    """Far-call slots (jsr -d(a4)) turned into an immediate return, with D0 = 0 for those
    whose result the caller tests."""
    for displacement in plain:
        o.write(A4 - displacement, bytes.fromhex('4E75'))
    for displacement in returns_zero:
        o.write(A4 - displacement, bytes.fromhex('70004E75'))


def test_the_game_over_countdown_matches_the_original(ported):
    """0x0110C2 for every count and both states of the game: `subq.b #1` and `bgt` set
    quit_flag when the count was 1 or below as a signed byte, 0x80 included.  The drawing
    calls are stubbed on the original's side; shape_find returns none there, so shape_draw
    is not reached."""
    import original

    o = original.Original().o
    stub_slots(o, returns_zero=[0x7D28],                          # shape_find
               plain=[0x7C92, 0x7ED8, 0x7CA4, 0x7C8C])           # blit_begin, clip_playfield,
    lib = ported.lib                                             # draw_set_target, blit_end
    for over in (0, 1, 0xFF):
        for count in range(256):
            o.write(GAME_OVER, bytes([over]))
            o.write(GAME_OVER_COUNT, bytes([count]))
            o.write(QUIT_FLAG, b'\0')
            o.call(0x0110C2)
            want = (o.read(GAME_OVER_COUNT, 1)[0], o.read(QUIT_FLAG, 1)[0])
            ported.set_g('game_over', over)
            ported.set_g('game_over_count', count)
            ported.set_g('quit_flag', 0)
            lib.wof_draw_game_over()
            got = (ported.g('game_over_count'), ported.g('quit_flag') & 0xFF)
            assert got == want, 'game over %d, count %d: port %s, original %s' % (
                over, count, got, want)


# ------------------------------------------------------ V6: the pure routines, whole state

class Differential:
    """One emulated machine and the port.  Before each call the port's registered state -
    every global of src/globals.def and every fixed table of src/mission.def - is set from
    the machine's DATA hunk through tests/m4state.py; after it the two are compared field
    by field, so a routine that writes anything the other does not is caught by name."""

    def __init__(self, ported):
        import m4state
        import original
        self.m4state = m4state
        self.o = original.Original().o
        self.ported = ported
        self.layout = m4state.Layout(ported)
        self.saved = (self.layout.port_globals(), self.layout.port_mission())

    def memory(self):
        return self.m4state.Memory({0x023000: bytes(self.o.read(0x023000, 0x028004 - 0x023000))})

    def load_port(self):
        g, m, problems = self.layout.expected(self.memory())
        assert not problems, problems
        self.layout.put(g, m)

    def differences(self):
        g, m, problems = self.layout.expected(self.memory())
        assert not problems, problems
        return self.layout.differences(self.layout.port_globals(), self.layout.port_mission(), g, m)

    def restore(self):
        self.layout.put(*self.saved)


@pytest.fixture
def differential(ported):
    d = Differential(ported)
    yield d
    d.restore()


def run_both(d, original_call, port_call, what):
    d.load_port()
    original_call()
    port_call()
    found = d.differences()
    assert found == [], '%s: %s' % (what, found[:6])


CARRIER = 0x0254D8
SHIPS = [0x025460, 0x02547E, 0x02549C, 0x0254BA, CARRIER]
SHIP_FLAGS = [0x02537A, 0x025377, 0x02537B, 0x025378]      # destroyer, battleship, cruise, jap


def test_the_gauge_resets_match_the_original(differential):
    """0x01EDBC and 0x01EDEA for every weapon count and every number of lives, with the
    buffers' caches holding noise: the drums' target rows and the high byte st.b writes."""
    d, lib = differential, differential.ported.lib
    rng = random.Random(0x1EDB)
    for n in range(256):
        d.o.write(0x02536D, bytes([n]))
        d.o.write(0x02535C, bytes([n]))
        d.o.write(0x027F30, bytes(rng.randrange(256) for _ in range(0x28)))
        run_both(d, lambda: d.o.call(0x01EDBC), lib.wof_weapon_gauge_reset, 'weapons %d' % n)
        run_both(d, lambda: d.o.call(0x01EDEA), lib.wof_lives_gauge_reset, 'lives %d' % n)


def test_deck_span_matches_the_original(differential):
    d, lib = differential, differential.ported.lib
    rng = random.Random(0x1B7B)
    for n in range(300):
        d.o.w16(CARRIER, rng.randrange(0x10000))
        d.o.w16(CARRIER + 2, rng.randrange(0x10000))
        run_both(d, lambda: d.o.call(0x01B7BC), lib.wof_deck_span, 'case %d' % n)


def test_ship_at_offset_matches_the_original(differential):
    """0x014A4E: random spans and flags for the five ships, and world x values inside,
    at the edges of and between them, over the whole 16-bit range."""
    d, lib = differential, differential.ported.lib
    lib.wof_ship_at_offset.argtypes = [ctypes.c_int16]
    lib.wof_ship_at_offset.restype = ctypes.c_int
    rng = random.Random(0x14A4)
    for n in range(2000):
        spans = []
        for ship in SHIPS:
            a = rng.randrange(0x4000)
            b = a + rng.randrange(-8, 0x200)
            d.o.w16(ship, a & 0xFFFF)
            d.o.w16(ship + 2, b & 0xFFFF)
            spans.append((a, b))
        for flag in SHIP_FLAGS:
            d.o.write(flag, bytes([rng.choice([0, 0, 1, 0xFF])]))
        a, b = rng.choice(spans)
        x = rng.choice([a * 4, b * 4 + 7, a * 4 - 1, b * 4 + 8, rng.randrange(0x10000)]) & 0xFFFF
        d.load_port()
        d0 = d.o.call(0x014A4E, regs={'d0': x})
        want = -1 if d0 == 0xFFFFFFFF else SHIPS.index(d.o.reg('a0'))
        got = lib.wof_ship_at_offset(x - 0x10000 if x & 0x8000 else x)
        assert got == want, 'x %04X: port %d, original %d' % (x, got, want)


def test_clip_to_waterline_matches_the_original(differential):
    """0x01526E with random carrier heights and rows, view offsets and clip rectangles."""
    d, lib = differential, differential.ported.lib
    rng = random.Random(0x1526)
    for n in range(500):
        d.o.w16(CARRIER + 0x0E, rng.randrange(0x10000))
        d.o.w16(CARRIER + 0x1A, rng.randrange(-40, 200) & 0xFFFF)
        d.o.w16(0x026E56, rng.randrange(-200, 200) & 0xFFFF)
        d.o.w16(0x025394, rng.choice([0, 0, 1, 0x8000]))
        d.o.call(0x02129C, regs={'d0': rng.randrange(0, 60), 'd1': rng.randrange(60, 200),
                                 'd2': rng.randrange(0, 100), 'd3': rng.randrange(100, 400)})
        run_both(d, lambda: d.o.call(0x01526E), lib.wof_clip_to_waterline, 'case %d' % n)


def test_the_window_height_matches_the_original(differential):
    """0x0141B4 over the whole range of the drawing's height: the marker's row.  The draw
    at its end is stubbed on the original's side; its place is part of the pass's calls."""
    d, lib = differential, differential.ported.lib
    frames = d.o.alloc(4 * 8, fill=0)
    record = d.o.alloc(16, fill=0)
    d.o.w32(frames + 0x14, record)
    d.o.w32(0x026E52, frames)
    stub_slots(d.o, plain=[0x7CD4])                            # shape_draw
    for y in list(range(-300, 300)) + [0x7FFF, 0x8000, 0x8001, 0xFFFF]:
        d.o.w16(0x026E60, y & 0xFFFF)
        run_both(d, lambda: d.o.call(0x0141B4), lib.wof_window_height, 'height %d' % y)
