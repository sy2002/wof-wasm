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
    ocean band above the waterline, the dashboard, its 3-D view and its score row)."""
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


# ------------------------------------------------------------------ V5: line_draw

LINE_DRAW = 0x021318


def test_line_draw_matches_the_blitter(ported):
    """line_draw (0x021318), the landing's cable: random lines in every octant, short and
    long, inside, across every edge and wholly outside the clip, in every colour, over an
    empty and a noisy background, under the playfield's clips.  The original's clipping and
    register programme are its own; the pixels come from the line mode of tests/blitter.py,
    which is documented behaviour and PROVISIONAL with the port's line (SPEC 10, point 7)."""
    bytes_per_row, rows, depth = PLAYFIELD
    width = bytes_per_row * 8
    reference = Reference('shapes/world.shp', bytes_per_row, rows, depth)
    o = reference.original.o
    rng = random.Random(0x21318)
    noisy = background(width, rows, 11, depth)
    drawn = 0
    for n in range(400):
        clip = rng.choice(CLIPS[PLAYFIELD])
        x0, y0 = rng.randrange(-60, width + 60), rng.randrange(-40, rows + 40)
        if n % 3:
            x1, y1 = x0 + rng.randrange(-40, 41), y0 + rng.randrange(-40, 41)
        else:
            x1, y1 = rng.randrange(-60, width + 60), rng.randrange(-40, rows + 40)
        colour = rng.randrange(1 << depth)
        bg = noisy if n % 2 else bytes(width * rows)

        def call():
            o.call(LINE_DRAW, regs={'d0': x0 & 0xFFFF, 'd1': y0 & 0xFFFF, 'd2': x1 & 0xFFFF,
                                    'd3': y1 & 0xFFFF, 'd4': colour, 'a6': CUSTOM})
        want = reference.replay(clip, bg, call)
        got = draw_op(ported, 4, PLAYFIELD, clip, bg, a=x0, b=y0, c=x1, d=y1, e=colour)
        assert got == want, 'line (%d,%d)-(%d,%d) colour %d clip %s: %d pixels differ' % (
            x0, y0, x1, y1, colour, clip, differ(got, want))
        drawn += want != bg
    assert drawn > 150, 'only %d of the lines drew anything' % drawn


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


def test_the_3d_views_cursor_matches_the_original(differential):
    """0x0141B4 over the whole range of the drawing's height: the row of the 3-D view's
    cursor, the artificial horizon of the manual's page 8.  The draw
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


# ------------------------------------------------------ T4: the player's routines (part 2)
# The routines of the player update against the original, run on the same randomised state:
# the return value, and every registered global and table afterwards.  The original's
# floating point runs in the ROM's mathffp (tests/ffp.py): its library base is a table of
# entries that hand D0 and D1 to the ROM and put its D0 back.  A map is loaded as the
# original's loader leaves it (tools/map_decode.py), so that the routines that look at the
# ground have some.

import ffp                           # noqa: E402
import ffp_model                     # noqa: E402
import map_decode                    # noqa: E402
from unicorn import UC_HOOK_CODE     # noqa: E402
from unicorn.m68k_const import UC_M68K_REG_D0, UC_M68K_REG_D1   # noqa: E402

PLAYER = 0x025078
MATH_BASE_SLOT = 0x027FAE
FFP_LVO = {-0x1E: 'fix', -0x24: 'flt', -0x3C: 'neg', -0x42: 'add', -0x48: 'sub',
           -0x4E: 'mul', -0x54: 'div'}
needs_rom = pytest.mark.skipif(not ffp.rom_available(), reason='original/kick.rom is absent')


class PlayerDifferential(Differential):
    """The Differential with a map loaded and the pointers the player's code goes through."""

    def __init__(self, ported, name='a'):
        super().__init__(ported)
        chart = map_decode.load(name)
        self.chart = chart
        self.map_base = self.o.alloc(3576 * 2)
        self.o.write(self.map_base, b''.join(w.to_bytes(2, 'big') for w in chart.words))
        self.o.w32(0x024628, self.map_base)
        self.o.w32(0x02462C, self.map_base + chart.length - 2)
        self.o.w16(0x024630, chart.extent)
        self.o.w32(0x027DEC, PLAYER)                   # player_record
        self.o.w32(0x027DF4, 0x025392)                 # player_start_x's pointer
        self.splashes = self.o.alloc(20 * 4)           # the pools a crash leaves things in
        self.smoke = self.o.alloc(40 * 0x14)
        self.o.w32(0x026F30, self.splashes)
        self.o.w32(0x026F58, self.smoke)
        self.reference = ffp.Reference()
        # Records worth landing on: land (low bits 2), ships (1), and the sea around them.
        self.interesting = [i for i, word in enumerate(chart.words) if word & 3] or [0]
        base = self.o.alloc(0x100) + 0x80
        for lvo, operation in FFP_LVO.items():
            self.o.write(base + lvo, bytes.fromhex('4E714E75'))           # nop; rts

            def entry(uc, address, size, user, operation=operation):
                d0 = uc.reg_read(UC_M68K_REG_D0) & 0xFFFFFFFF
                d1 = uc.reg_read(UC_M68K_REG_D1) & 0xFFFFFFFF
                uc.reg_write(UC_M68K_REG_D0, self.reference.call(operation, d0, d1).d0)
            self.o.uc.hook_add(UC_HOOK_CODE, entry, begin=base + lvo, end=base + lvo)
        self.o.w32(MATH_BASE_SLOT, base)
        lib = ported.lib
        lib.wof_test_player_call.argtypes = [ctypes.c_uint32, ctypes.c_int32]
        lib.wof_test_player_call.restype = ctypes.c_int32

    def memory(self):
        return self.m4state.Memory({
            0x023000: bytes(self.o.read(0x023000, 0x028004 - 0x023000)),
            self.map_base: bytes(self.o.read(self.map_base, 3576 * 2)),
            self.splashes: bytes(self.o.read(self.splashes, 20 * 4)),
            self.smoke: bytes(self.o.read(self.smoke, 40 * 0x14))})

    def port(self, orig, a=0):
        return self.ported.lib.wof_test_player_call(orig, a)


@pytest.fixture
def player(ported):
    d = PlayerDifferential(ported)
    yield d
    d.restore()


def w(o, address, value):
    o.w16(address, value & 0xFFFF)


def random_flight(d, rng, deck=None):
    """A state the player update can be in: the record, the controls, the carrier."""
    o = d.o
    w(o, PLAYER + 0x00, rng.choice([rng.randrange(-8, 1120), rng.randrange(1090, 1110), 0, 37]))
    w(o, PLAYER + 0x02, rng.choice([rng.randrange(0, 0x7FFF), rng.randrange(6560, 7400),
                                    8 * rng.choice(d.interesting)]))
    w(o, PLAYER + 0x0C, deck if deck is not None else rng.choice([0, 0, 0, 1, 1, 4, 6, 7, 8, 11]))
    w(o, PLAYER + 0x0E, rng.choice([0xC0, rng.randrange(-4, 0xC0)]))
    w(o, PLAYER + 0x12, rng.choice([0x80, 0x80, rng.randrange(0x50, 0x80)]))
    w(o, PLAYER + 0x14, rng.choice([1, -1]))
    w(o, PLAYER + 0x16, rng.randrange(-20, 20))
    w(o, PLAYER + 0x18, rng.randrange(-12, 12))
    w(o, PLAYER + 0x1C, rng.choice([0, 1, 2, 0x2EE, rng.randrange(0, 0x546)]))
    w(o, 0x025AA2, rng.randrange(-6000, 6000))                 # pitch_angle
    w(o, 0x025402, rng.choice([0, 0x258, rng.randrange(-4800, 3100)]))   # pitch_target
    w(o, 0x025408, rng.choice([0, rng.randrange(-600, 600)]))  # pitch_delta
    w(o, 0x025AAA, rng.choice([0, 0, 1]))
    w(o, 0x02540E, rng.choice([0, 0, rng.randrange(0, 26)]))   # attitude_index
    w(o, 0x025414, rng.choice([0, 1000, 1400, 600, rng.randrange(-40, 1500)]))   # airspeed
    w(o, 0x027DEA, rng.choice([0, 4, 8, rng.randrange(-3, 12)]))   # airspeed_step
    w(o, 0x025F16, rng.choice([600, 600, 550, 650, rng.randrange(0, 1200)]))   # pitch_step
    w(o, 0x026D42, rng.randrange(0x40))                        # tick_input
    w(o, 0x025AA0, rng.choice([1, 2, rng.randrange(-1, 4)]))
    w(o, 0x025A9C, rng.choice([0, 0, 1]))
    w(o, 0x025392, rng.choice([7032, rng.randrange(6000, 8000)]))    # player_start_x
    w(o, 0x025394, rng.choice([0, 0, 1, 2, 3]))
    w(o, 0x0253FC, 6608)
    w(o, 0x0253FE, 7344)
    w(o, 0x0254D8 + 0x04, rng.choice([1, 1, 0]))               # carrier present
    w(o, 0x0254D8 + 0x0C, rng.choice([4, 4, 0, 1]))            # carrier w0c
    w(o, 0x0254D8 + 0x0E, rng.randrange(0, 0x40))
    w(o, 0x0254D8 + 0x14, rng.randrange(0, 0x10))
    w(o, 0x025592, rng.randrange(0, 12))
    w(o, 0x02540A, rng.choice([0, 5]))
    w(o, 0x025F14, rng.choice([0, 0x600]))
    o.write(0x025367, bytes([rng.choice([0, 0, 0xFF])]))
    for i in range(20):                                        # the Splashes pool
        o.write(d.splashes + 4 * i + 2, bytes([rng.choice([0, 0, 0, 3])]))
    for i in range(40):                                        # the Smoke pool
        w(o, d.smoke + 0x14 * i + 0x10, rng.choice([0, 0, 0, 5]))
    for i in range(15):                                        # the object records' kinds
        o.write(0x024CAE + 0x2A * i + 0x20, bytes([rng.choice([0, 0, 8])]))
    w(o, 0x026A16, rng.randrange(0x10000))                     # the C library's seed
    w(o, 0x026A18, rng.randrange(0x10000))
    w(o, 0x025AA6, rng.randrange(0, 0x100))
    w(o, 0x025AA8, rng.randrange(0, 0x100))
    for i in range(4):                                         # enemy aircraft, mostly none
        base = 0x02522A + 0x34 * i
        for k in (0, 2, 4, 0x16):
            w(o, base + k, rng.choice([0, 0, 0, 1, 2, 3, 13]))


def check(d, what, want, got):
    found = d.differences()
    assert found == [] and want == got, '%s: returned %r and %r, %s' % (what, want, got, found[:6])


@needs_rom
def test_player_motion_matches_the_original_and_the_model(player):
    """player_motion (0x01BDFA) over 3,000 random states: every attitude, both facings, the
    ceiling, the airspeed's floor and the bounds of airspeed_step; the whole registered state
    afterwards against the original, and its values against tests/ffp_model.py driven by
    the port's own floating point."""
    d = player
    rng = random.Random(0x1BDF)
    for n in range(3000):
        random_flight(d, rng, deck=rng.choice([0, 0, 0, 1]))
        entry = {'in': {
            'player': d.o.read(PLAYER, 0x1E).hex(), 'g_025402': d.o.read(0x025402, 0x14).hex(),
            'g_025aa2': d.o.read(0x025AA2, 0x0A).hex(), 'g_027dea': d.o.read(0x027DEA, 2).hex(),
            'g_025f16': d.o.read(0x025F16, 2).hex(), 'g_026d43': d.o.read(0x026D43, 1).hex()}}
        d.load_port()
        d.o.call(0x01BDFA)
        d.port(0x01BDFA)
        check(d, 'case %d' % n, 0, 0)
        _, left = ffp_model.model_01bdfa(entry, lambda op, a, b: d.ported.ffp(op, a, b)[0])
        after = {'g_025aa2': d.o.r16(0x025AA2), 'g_025402': d.o.r16(0x025402),
                 'g_027dea': d.o.r16(0x027DEA), 'player_0': d.o.r16(PLAYER),
                 'player_2': d.o.r16(PLAYER + 2), 'player_16': d.o.r16(PLAYER + 0x16),
                 'player_18': d.o.r16(PLAYER + 0x18)}
        assert left == after, 'case %d: the model leaves %s, the original %s' % (n, left, after)


# The routines that take no argument and whose whole effect is on the registered state,
# with the state each wants: in the air, on the deck, or any.
PLAYER_ROUTINES = [
    (0x01BFF4, 'the stick in the air', 0),
    (0x01C4E8, 'the stick on the deck', 1),
    (0x01AA6E, 'whether the aircraft may turn', None),
    (0x01AAEA, 'the wheels below the reference point', None),
    (0x01B45A, 'the hook', None),
    (0x01B4DE, 'on the lift', 1),
    (0x01B5B0, 'the button', None),
    (0x01B8C4, 'touching the ground', 0),
    (0x01B92E, 'the cables', 1),
    (0x01BC02, "the enemy's countdown", None),
    (0x01BCCE, 'the deck state', None),
    (0x01BDBA, 'the roll on the deck', None),
    (0x01C5F4, 'the ends of the deck', 1),
    (0x01AFBA, 'the aircraft down: in the sea, on land, on a ship', 4),
    (0x01BA80, 'the ground: a landing, a bounce, a crash', 0),
]


@needs_rom
@pytest.mark.parametrize('address,what,deck', PLAYER_ROUTINES,
                         ids=['%06X' % r[0] for r in PLAYER_ROUTINES])
def test_the_player_routines_match_the_original(player, address, what, deck):
    """Each of the player update's routines over 1,500 random states; flags are not part of
    their interface (they are C and return in D0 at most)."""
    d = player
    lib = d.ported.lib
    lib.wof_standin_hits.restype = ctypes.c_uint32
    rng = random.Random(address)
    compared = 0
    for n in range(1500):
        random_flight(d, rng, deck=deck)
        d.load_port()
        hits = lib.wof_standin_hits()
        try:
            want = d.o.call(address) & 0xFFFF
        except RuntimeError as error:
            # The enemy aircraft coming (0x01BC66) draw rand_beam, which reads the beam
            # counter this machine has no chips for; tests/test_oracle_m6.py serves the beam
            # and compares those cases.
            assert '00dff0' in str(error), error
            continue
        got = d.port(address) & 0xFFFF
        if lib.wof_standin_hits() != hits:
            continue                      # a later milestone's stand-in: the button's weapon
        returns = address in (0x01AA6E, 0x01AAEA, 0x01B4DE, 0x01B8C4)
        check(d, '%s, case %d' % (what, n), want if returns else 0, got if returns else 0)
        compared += 1
    assert compared > 1000, 'only %d cases compared' % compared


@needs_rom
def test_a_turn_step_matches_the_original(player):
    """0x01AB80 with and without its argument, through every attitude."""
    d = player
    rng = random.Random(0x1AB8)
    for n in range(1500):
        random_flight(d, rng)
        whole = rng.choice([0, 1])
        d.load_port()
        d.o.call(0x01AB80, d.o.L(whole))
        d.port(0x01AB80, whole)
        check(d, 'turn step %d' % n, 0, 0)


@pytest.mark.parametrize('name', ['a', 'c', 'h', 'm', 'o'])
def test_the_map_helpers_match_the_original(ported, name):
    """ground_height (0x015714) for every record of the map, with the ships' decks at random
    heights; map_slot_at (0x0150C8), record_at (0x01C982), on_water (0x01CB74) and
    record_on_ship (0x01CB34) at every world x a record starts at, around both ends and at
    random ones."""
    d = PlayerDifferential(ported, name)
    try:
        rng = random.Random(ord(name))
        for ship in (0x025460, 0x02547E, 0x02549C, 0x0254BA, 0x0254D8):
            w(d.o, ship + 0x0E, rng.randrange(0, 0x60))
            w(d.o, ship + 0x14, rng.randrange(0, 0x20))
        w(d.o, 0x0253AE, rng.randrange(0, 4))
        w(d.o, 0x025396, rng.randrange(0, 0x21))
        d.load_port()
        base = d.map_base
        for i in range(len(d.chart.words)):
            at = 2 * i
            want = d.o.call(0x015714, regs={'a0': base + at}) & 0xFFFF
            got = d.port(0x015714, at) & 0xFFFF
            assert want == got, 'map %s record %d: ground %d, port %d' % (name, i, want, got)
        xs = ([8 * i for i in range(len(d.chart.words))] + list(range(-20, 20)) +
              list(range(d.chart.extent - 20, d.chart.extent + 20)) +
              [rng.randrange(-0x8000, 0x8000) for _ in range(500)])
        for x in xs:
            x16 = x & 0xFFFF
            sx = x16 - 0x10000 if x16 & 0x8000 else x16
            d0 = d.o.call(0x0150C8, regs={'d0': x16})
            want = ((d.o.reg('d1') & 0xFFFF) << 16) | (d0 & 0xFFFF)
            got = d.port(0x0150C8, sx) & 0xFFFFFFFF
            assert want == got, 'map %s x %d: map_slot_at %08X, port %08X' % (name, sx, want, got)
            pointer = d.o.call(0x01C982, d.o.W(x16))
            at = d.port(0x01C982, sx)
            assert pointer - base == at, 'map %s x %d: record_at %d, port %d' % (
                name, sx, pointer - base, at)
            for call in (0x01CB74, 0x01CB34):
                want = d.o.call(call, d.o.L(pointer)) & 0xFFFF
                assert want == d.port(call, at) & 0xFFFF, 'map %s x %d: %06X' % (name, sx, call)
        assert d.differences() == []
    finally:
        d.restore()
