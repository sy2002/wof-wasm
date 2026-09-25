"""M6 part 1 differential tests: the routines of the pass that change state, against the
original (SPEC 7.4, re/notes/porting-m6.md, "How the port is held").

Each routine runs twice on the same randomised state, once as the original's 68000 code
under the oracle and once as the port's C, and every registered global and table the two
touched is compared, as tests/test_oracle_m5.py does it.  The state is map c with its
targets, the four enemy ships with a gun list each, the object records, the pools and the
player; rand_beam's beam position is served on both sides from the port's stream.  The
drawing the routines do is compared call by call in the open loop (tests/test_enemy.py);
here the original's shape_draw returns at once.  Beside them, the exclusive-or blit of the
enemy aircraft's guns' flash against the blitter model.
"""
import os
import random
import sys

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, 'tools'))
sys.path.insert(0, HERE)

import ctypes                                         # noqa: E402

from test_oracle_m4 import w                          # noqa: E402
from test_oracle_m5 import TickDifferential, check, OBJECTS, OBJECT_EXTRA   # noqa: E402

SHIPS = 0x025460
PLAYER = 0x025078
SHAPE_DRAW = 0x020CE2
SHIP_GUN_SHELL, SHIP_GUNS_DRAW = 0x014EFC, 0x014C3E


class ShipsDifferential(TickDifferential):
    """The tick's differential with all four enemy ships afloat or not, a gun list of sixteen
    each, and the original's shape_draw made to return at once."""

    def __init__(self, ported, name='c'):
        super().__init__(ported, name)
        o = self.o
        self.lists = [self.guns] + [o.alloc(16 * 0x0E) for _ in range(3)]
        o.write(SHAPE_DRAW, bytes.fromhex('4E75'))                    # rts
        lib = ported.lib
        lib.wof_test_m6_call.argtypes = [ctypes.c_uint32, ctypes.c_int32, ctypes.c_int32,
                                         ctypes.c_int32, ctypes.POINTER(ctypes.c_int32)]
        lib.wof_test_m6_call.restype = ctypes.c_int32

    def memory(self):
        m = super().memory()
        regions = dict(m.regions)
        for base in self.lists:
            regions[base] = bytes(self.o.read(base, 16 * 0x0E))
        return self.m4state.Memory(regions)

    def randomise_ships(self, rng):
        """The tick's state, the four enemy ships as map_scan leaves them and as the play
        changes them (afloat or sunk, their hits, deck and row), each gun at a world x near
        the player's, standing or destroyed with its smoke still to come, and the smoke pool
        partly in use."""
        o = self.o
        self.randomise_tick(rng)
        px = o.r16(PLAYER + 2)
        w(o, PLAYER + 0x0C, rng.choice([0, 0, 0, 0, 1]))
        w(o, PLAYER + 0x00, rng.choice([rng.randrange(0, 0xD0), rng.randrange(0, 0x400)]))
        w(o, 0x026E60, rng.randrange(0, 0x100))                     # draw_player_y
        w(o, 0x026E56, rng.randrange(0, 4))                         # the swell's snapshot
        step = rng.choice([8, 8, 1])
        w(o, 0x024F36, step)                                        # view_step
        w(o, 0x024F34, 3 if step == 1 else 0)                       # view_shift
        for k, base in enumerate(self.lists):
            ship = SHIPS + 0x1E * k
            w(o, ship + 0x04, rng.choice([0, 0xFFFF, 0xFFFF]))
            w(o, ship + 0x0A, rng.choice([rng.randrange(0, 17), 4, 8, 14, 15]))
            w(o, ship + 0x0C, rng.choice([0, 1, 2, 3, 0xFFFF]))
            w(o, ship + 0x0E, rng.choice([0x15, 0x1B, 0x1C, rng.randrange(0, 0x30)]))
            w(o, ship + 0x1A, rng.choice([0, 0, rng.randrange(0, 0x20)]))
            o.w32(ship + 0x06, base)
            for i in range(16):
                at = base + 0x0E * i
                w(o, at + 0, rng.randrange(0x10000))
                w(o, at + 2, rng.randrange(0x10000))
                w(o, at + 4, (px + rng.randrange(-0x300, 0x300)) & 0xFFFF)
                w(o, at + 6, rng.choice([0, 5, rng.randrange(0, 0x20)]))
                w(o, at + 8, rng.choice([0, 0, 0xFFFF]))
                w(o, at + 0x0A, rng.choice([0, 1, 2, 0x31, 0x32, rng.randrange(0, 0x40)]))
                w(o, at + 0x0C, rng.choice([0, 1, 2, rng.randrange(0, 0x40)]))
        for i in range(40):                                         # the smoke pool
            at = self.smoke + 0x14 * i
            w(o, at + 0x10, rng.choice([0, 0, 0, 1, 5]))
        w(o, 0x027456, rng.choice([0x2710, rng.randrange(0, 0x300)]))
        o.write(0x026F72, bytes([0, rng.choice([0, 0, 1])]))
        o.write(0x026D4A, bytes([rng.choice([0, 0xFF])]))

    def m6(self, orig, a=0, b=0, c=0):
        out = (ctypes.c_int32 * 4)()
        return self.ported.lib.wof_test_m6_call(orig, a, b, c, out)


@pytest.fixture
def ships(ported):
    d = ShipsDifferential(ported)
    yield d
    d.restore()


def test_a_ships_gun_shelling_matches_the_original(ships):
    """0x014EFC: a ship's gun shells the aircraft, near and far, low and high: the flag it
    leaves, the splash in the water beside the drawing's x and a torpedo of the player's
    it takes out, with three draws of rand_beam at most."""
    d = ships
    rng = random.Random(0x14EFC)
    for n in range(2000):
        d.randomise_ships(rng)
        px = d.o.r16(PLAYER + 2)
        x = (px + rng.choice([rng.randrange(-0x40, 0x40), rng.randrange(-0x400, 0x400)])) & 0xFFFF
        for i in range(16):                   # torpedoes near the splash, some drawn
            if rng.random() < 0.3:
                at = OBJECTS + 0x2A * i if i < 15 else OBJECT_EXTRA
                w(d.o, at + 0x08, d.o.r16(0x026E5C) + rng.randrange(-40, 40))
        d.load_port()
        d.o.call(SHIP_GUN_SHELL, regs={'d0': x, 'd1': rng.randrange(1 << 32),
                                       'd2': rng.randrange(1 << 32)})
        d.m6(SHIP_GUN_SHELL, x)
        check(d, 'case %d' % n)


def test_the_ships_guns_match_the_original(ships):
    """ship_guns_draw (0x014C3E) over random ships and guns: which ships it takes (afloat,
    not sunk, never the player's carrier), a standing gun's shells, frame and fire at the
    aircraft, a destroyed gun's smoke with its counters, D1's upper word carried from one
    gun's smoke into the next and into target_fire's exchange, in both views and with the
    aircraft on the deck."""
    d = ships
    rng = random.Random(0x14C3E)
    for n in range(1500):
        d.randomise_ships(rng)
        d.load_port()
        d.o.call(SHIP_GUNS_DRAW, regs={'d1': 0, 'd2': 0, 'd7': 0})
        d.m6(SHIP_GUNS_DRAW)
        check(d, 'case %d' % n)


# ------------------------------------------------ the exclusive-or blit, the guns' flash

def test_the_exclusive_or_blit_of_the_enemy_guns_matches_the_blitter(ported):
    """shape_draw_xor (0x020E24), which an enemy aircraft's guns' flash is drawn with on
    the 5-plane playfield (draw_enemy_aircraft, japplane_shapes 0x10 to 0x13): every shape
    of japplane.shp at aligned, shifted and hanging-off positions under two clips, over a
    noisy background, against the original's register programme replayed by
    tests/blitter.py.  M5's test holds the same blit for hellcat.shp."""
    from test_oracle_m4 import (PLAYFIELD, CLIPS, POSITIONS_5, CUSTOM, Reference, background,
                                draw_op, differ)
    from test_oracle_m5 import SHAPE_DRAW_XOR
    import m4state                                            # noqa: F401
    ported.reset_core()
    bytes_per_row, rows, depth = PLAYFIELD
    width = bytes_per_row * 8
    reference = Reference('shapes/japplane.shp', bytes_per_row, rows, depth)
    o = reference.original.o
    noisy = background(width, rows, 0x6A, depth)
    changed = cases = 0
    slot = JAPPLANE
    for index in range(reference.count):
        record = reference.container['records'][index]
        for x, y in POSITIONS_5:
            for clip in CLIPS[PLAYFIELD][:2]:
                def call():
                    o.call(SHAPE_DRAW_XOR, regs={'a0': record, 'd0': x & 0xFFFF,
                                                 'd1': y & 0xFFFF, 'a6': CUSTOM})
                want = reference.replay(clip, noisy, call)
                got = draw_op(ported, 5, PLAYFIELD, clip, noisy, slot=slot, index=index,
                              a=x, b=y)
                assert got == want, 'japplane.shp %d at (%d,%d) clip %s: %d pixels differ' % (
                    index, x, y, clip, differ(got, want))
                changed += want != noisy
                cases += 1
    assert changed > cases // 3, 'only %d of %d blits drew anything' % (changed, cases)


JAPPLANE = 3                                                  # WOF_C_JAPPLANE (src/wof.h)
