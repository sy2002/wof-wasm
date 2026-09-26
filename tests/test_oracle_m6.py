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


# ------------------------------------------------------------ part 2: the tick's routines

AIRCRAFT = 0x02522A
AIRFIELDS = 0x0252FA


class Reached:
    """The original's translation blocks executed while it is installed, as (start, end):
    a region of the listing counts as reached when a block covers its first address (a
    block may run on through a label that only a fall-through reaches)."""

    def __init__(self, o, lo=0x010000, hi=0x023000):
        from unicorn import UC_HOOK_BLOCK
        self.o = o
        self.blocks = set()
        self.hook = o.uc.hook_add(UC_HOOK_BLOCK, self._block, begin=lo, end=hi)

    def _block(self, uc, address, size, user):
        self.blocks.add((address, address + size))

    def close(self):
        self.o.uc.hook_del(self.hook)

    def missing(self, starts):
        return ['0x%06X' % a for a in starts
                if not any(lo <= a < hi for lo, hi in self.blocks)]


# The regions of the M6 routines that no script executes (re/notes/porting-m6.md, "Appendix:
# the regions no run executed"), by the routine whose test must reach them.
COLD = {
    0x01D562: [0x01D6BE, 0x01D6EE],                        # aircraft_turn: case 1, case 2
    0x01D9C6: [0x01DB86],                                  # fighter_cruise: a hit ahead
    0x01DEA4: [0x01DF8C],                                  # torpedo_plane: past the deck's west end
    0x01E244: [0x01E380, 0x01E3D2, 0x01CBC0, 0x01CBD4],    # at rest on land; a fighter; record_is_land
    0x01E3E8: [0x01E3E8],                                  # aircraft_burning
    0x01E4C8: [0x01E4C8],                                  # aircraft_idle
    0x01E4D0: [0x01E504],                                  # a torpedo plane already up
    # aircraft_speed's clamp at 900 (0x01E71A) is dead: slowing towards a want speed that is
    # at least 900 lands half the gap and 5 above it.
    0x01E728: [0x01E7BA, 0x01E7D0],                        # a mode none of the four
    0x01E7D6: [0x01E84E, 0x01E876],                        # states 1, 8, 0x10 and the rest
    0x011CAE: [0x011D28, 0x011D3A, 0x011D7E],              # won; the carrier's lift; the sea
    0x01B682: [0x01B6C8],                                  # an aircraft east of the player
}
SHIP_BLOCKS = 0x025096
CARRIER = 0x0254D8
MAP_RECORDS = 0x024628
TICK_INPUT = 0x026D42


class EnemyDifferential(ShipsDifferential):
    """The ships' differential with the four enemy aircraft records, the player around them,
    the airfields, the ship blocks and the carrier, as the play leaves them and beyond."""

    def randomise_enemy(self, rng):
        """The ships' state, and the enemy's: every record in any state and mode near the
        player or far from him, turning or level, hit or not, falling over the sea, on land
        or onto a ship; the player in the air, on the deck or down; the counters, the wrecks'
        list short and past its forty words; the airfields with an aircraft rolling or not;
        the ship blocks and the ships sinking, the carrier among them."""
        o = self.o
        self.randomise_ships(rng)
        px = o.r16(PLAYER + 2)
        py = o.r16(PLAYER)
        w(o, PLAYER + 0x0C, rng.choice([0, 0, 0, 0, 1, 4, 6, 8, 11]))
        w(o, PLAYER + 0x0E, rng.randrange(0, 0x800))                  # fuel
        w(o, PLAYER + 0x10, rng.choice([0, 1, 2, 6, 10]))
        w(o, PLAYER + 0x12, rng.randrange(0, 0x81))                   # oil
        w(o, PLAYER + 0x16, rng.choice([0, rng.randrange(0, 20), rng.randrange(-8, 20)]))
        w(o, PLAYER + 0x1C, rng.choice([0, 1, 1, 2, 500, 750, 1350, rng.randrange(0x800)]))
        w(o, 0x02540E, rng.choice([0, 0, 0, rng.randrange(0, 0x1A)]))   # attitude_index
        w(o, 0x025414, rng.choice([1000, 0x6A4, rng.randrange(0, 0x800)]))   # airspeed
        w(o, 0x027346, rng.randrange(2))
        lo = px + rng.choice([rng.randrange(-0x1000, 0x1000), rng.randrange(-0x200, 0x100)])
        w(o, 0x0253FC, lo)
        w(o, 0x0253FE, lo + 0x2F0)
        w(o, 0x027E66, rng.randrange(0, 4))
        w(o, 0x0251D6, rng.randrange(0, 5))                          # fighters_up
        w(o, 0x0251D8, rng.choice([0, 1, 3, 3, 39, 40, 45, 143, 150, 183, 190, 300]))
        for i in range(40):
            w(o, 0x0251DA + 2 * i, rng.randrange(0x10000))
        w(o, 0x026C96, rng.randrange(0, 3))                          # skid_count
        o.write(0x02537F, bytes([rng.randrange(0, 0x70)]))
        w(o, 0x025402, rng.choice([0, 0, 0, 1, 0xFFFF]))              # pitch_target
        w(o, 0x02536A, rng.choice([0, 1, 1]))                        # the guns fire
        w(o, 0x027348, rng.choice([0, 0, 1, 100]))                   # launch_cooldown
        w(o, 0x02734A, rng.choice([0, rng.randrange(0, 0x100)]))     # japcarrier_roll
        w(o, 0x026E6A, px)
        chart = len(self.chart.words) * 2
        for i in range(4):
            at = AIRCRAFT + 0x34 * i
            state = rng.choice([0, 0, 1, 2, 2, 2, 2, 4, 4, 4, 8, 0x10, 0x10, rng.randrange(0x20)])
            mode = rng.choice([0, 1, 1, 2, 2, 4, 4, 9, 0x0A, 0x0C, 0x10, 0x10, 0x18,
                               rng.randrange(0x20)])
            x = px + rng.choice([rng.randrange(-0x100, 0x100), rng.randrange(-0x800, 0x800),
                                 rng.randrange(-0x2000, 0x2000)])
            y = rng.choice([py + rng.randrange(-0x20, 0x20), rng.randrange(0, 0x100)])
            want_y = rng.choice([y, y, 0x14, 0x21, 0x3C, -3, rng.randrange(-4, 0x100)])
            fields = {
                0x00: state, 0x02: mode, 0x04: rng.randrange(0, 5), 0x06: rng.randrange(0, 2),
                0x08: rng.choice([0xF0, 0x68, 0x60, 0x58, rng.randrange(0x40, 0xF1)]),
                0x0A: rng.choice([1, 1, 2, rng.randrange(0, 10)]),
                0x0C: rng.randrange(0, 5), 0x0E: rng.randrange(0x10000),
                0x10: rng.choice([0, 0, 1, 2, 0x113, 0x226, rng.randrange(0, 0x300)]),
                0x12: rng.randrange(0, 2), 0x14: rng.choice([1, 0xFFFF]),
                0x16: rng.choice([0, 0, 0, 0x0D, 0x0E, 0x13, 0x14, 0x19, rng.randrange(0, 0x1A)]),
                0x18: rng.choice([0, 0, 1, 2, rng.randrange(0, 14)]),
                0x1A: rng.randrange(0, 4),
                0x1C: rng.choice([900, 0xA28, 0x1F4, 0x12C, 0x64, 0x63, 0x1E, 1,
                                  rng.randrange(0x64, 0xC00)]),
                0x1E: rng.choice([900, 0xA28, 6, 2, 1, rng.randrange(0, 0xC00)]),
                0x20: x, 0x22: rng.choice([0, rng.randrange(-0x400, 0x400)]),
                0x24: want_y, 0x26: y,
                0x28: rng.choice([0, 0x82, 0x96, 0xA0, rng.randrange(0, 0x100),
                                  rng.randrange(0, 0x1000)]),
                0x2A: rng.randrange(0x10000), 0x2C: rng.randrange(0, 8),
                0x2E: rng.randrange(0x10000), 0x30: rng.randrange(0, 0x38),
                0x32: rng.randrange(0, 3)}
            if state in (1, 2) or rng.random() < 0.8:
                fields[0x1C] = max(fields[0x1C], 0x64)     # a flight's divisions by its speed
            for off, v in fields.items():
                w(o, at + off, v)
        for i in range(4):                                            # the airfields
            at = AIRFIELDS + 0x14 * i
            lo = s16(o.r16(at))
            w(o, at + 0x04, rng.randrange(0, 4))
            w(o, at + 0x06, rng.randrange(0, 5))
            w(o, at + 0x08, rng.choice([0, 0, lo + rng.randrange(-0x40, 0x200)]))
            w(o, at + 0x0C, rng.choice([0, 7, 0x37, 0x38, rng.randrange(0, 0x40)]))
            w(o, at + 0x0E, rng.choice([1, 0xFFFF]))
        for k in range(5):                                            # the ship blocks
            at = SHIP_BLOCKS + 0x40 * k
            w(o, at, rng.choice([0, 0, 1, 2, 7, rng.randrange(0, 8)]))
            w(o, at + 2, rng.randrange(0, 4))
            lo = px + rng.randrange(-0x300, 0x100)
            w(o, at + 4, lo)
            w(o, at + 6, lo + rng.randrange(0, 0x400))
            for e in range(7):
                ent = at + 8 + 8 * e
                w(o, ent, rng.choice([0, 1, 0, rng.randrange(0x10000)]))
                w(o, ent + 2, px + rng.randrange(-0x400, 0x400))
                w(o, ent + 4, rng.randrange(0, 0x40))
                w(o, ent + 6, rng.choice([1, 0xFFFF]))
        for ship in SHIPS_ALL:                                        # afloat, sinking
            span = rng.randrange(0, chart - 0x100) & ~1
            w(o, ship + 0x00, span)
            w(o, ship + 0x02, span + rng.choice([0, 2, 0x20, 0xA0]))
            if ship == CARRIER:
                w(o, ship + 0x04, rng.choice([0, 0xFFFF, 0xFFFF]))
                w(o, ship + 0x0C, rng.choice([0, 0, 1, 4]))
                w(o, ship + 0x12, 0)
            else:
                w(o, ship + 0x12, rng.choice([0, 1000, 2500, 4500, 6000, 6000]))
                if rng.random() < 0.5:
                    w(o, ship + 0x0C, 0)
            w(o, ship + 0x14, rng.choice([0, 9, 10, 0x20, 0x21, 0x77, 0x78, rng.randrange(0x80)]))
            w(o, ship + 0x16, rng.choice([0, 1, 1, 2, 20]))
            w(o, ship + 0x18, rng.choice([0, 1, 20]))
        o.write(0x025371, bytes([rng.choice([1, 1, 2, 0x80, 0])]))    # ships_left
        o.write(0x025383, bytes([rng.choice([0, 0, 1])]))              # islands_left
        o.write(0x025370, bytes([rng.randrange(0, 4)]))                # briefing_number_2
        w(o, 0x025394, rng.choice([0, 1, 1, 2, 3]))                    # aboard
        o.write(0x025364, bytes([rng.choice([0, 0xFF])]))              # the weapon menu
        o.write(0x0255C2, bytes([rng.choice([0, 5])]))                 # game_over_count
        o.write(0x02716A, bytes(rng.randrange(0x20, 0x7F) for _ in range(40)) + b'\0')
        w(o, 0x0253C0, rng.randrange(1, 4))                            # mission_number
        w(o, 0x0253BE, rng.randrange(0, 7))                            # rank_played
        del chart

    def record_at(self, i):
        return AIRCRAFT + 0x34 * i


SHIPS_ALL = [0x025460, 0x02547E, 0x02549C, 0x0254BA, CARRIER]


def s16(v):
    v &= 0xFFFF
    return v - 0x10000 if v & 0x8000 else v


@pytest.fixture
def enemy(ported):
    d = EnemyDifferential(ported)
    yield d
    d.restore()


ENEMY_ROUTINES = [
    (0x01D18C, 'aircraft_gone_far', True),
    (0x01D35A, 'aircraft_frame_index', False),
    (0x01D3B4, 'aircraft_relation', False),
    (0x01D530, 'aircraft_turn_step', False),
    (0x01D562, 'aircraft_turn', False),
    (0x01D796, 'aircraft_motion', False),
    (0x01D9C6, 'fighter_cruise', False),
    (0x01DCCC, 'fighter_attack', False),
    (0x01DEA4, 'torpedo_plane', False),
    (0x01E17A, 'torpedo_plane_away', False),
    (0x01E244, 'aircraft_falling', False),
    (0x01E3E8, 'aircraft_burning', False),
    (0x01E4C8, 'aircraft_idle', False),
    (0x01E64E, 'aircraft_speed', False),
    (0x01E728, 'aircraft_fly', False),
]


@pytest.mark.parametrize('address,what,returns', ENEMY_ROUTINES,
                         ids=[r[1] for r in ENEMY_ROUTINES])
def test_each_enemy_aircraft_routine_matches_the_original(enemy, address, what, returns):
    """Every routine of the enemy module that takes a record, on one record of four over
    1,200 random states (every mode and relation, level and turning, hit and not, falling
    over the sea, on land, on a ship, burning, the wrecks' list short and long): what it
    writes anywhere, with rand_beam served on both sides from the port's stream, and its
    result where it has one."""
    d = enemy
    rng = random.Random(address)
    reached = Reached(d.o)
    for n in range(1200):
        d.randomise_enemy(rng)
        i = rng.randrange(4)
        if address not in (0x01E244, 0x01E3E8):  # a flight divides by its speed's hundreds
            at = d.record_at(i) + 0x1C
            w(d.o, at, max(s16(d.o.r16(at)), 0x64))
        d.load_port()
        want = d.o.call(address, d.o.L(d.record_at(i))) & 0xFFFF
        got = d.m6(address, i) & 0xFFFF
        check(d, '%s, case %d' % (what, n), want if returns else 0, got if returns else 0)
    reached.close()
    assert reached.missing(COLD.get(address, [])) == [], 'no case reached these regions'


def test_the_order_of_the_aircraft_matches_the_original(enemy):
    """aircraft_order (0x01D476) over 2,000 random tables: the places of the aircraft behind
    the player, one further for each nearer one before it in the table."""
    d = enemy
    rng = random.Random(0x1D476)
    for n in range(2000):
        d.randomise_enemy(rng)
        for i in range(4):
            if rng.random() < 0.6:
                w(d.o, AIRCRAFT + 0x34 * i + 4, 1)
        d.load_port()
        d.o.call(0x01D476)
        d.m6(0x01D476)
        check(d, 'case %d' % n)


def test_the_enemy_aircraft_step_matches_the_original(enemy):
    """enemy_aircraft_step (0x01E7D6), the four records in one tick, over 3,000 random states:
    relation, order, the flights of every mode, the fall and the burning, the speed, the
    motion with its mathffp and the frames."""
    d = enemy
    rng = random.Random(0x1E7D6)
    reached = Reached(d.o)
    for n in range(3000):
        d.randomise_enemy(rng)
        d.load_port()
        d.o.call(0x01E7D6)
        d.m6(0x01E7D6)
        check(d, 'case %d' % n)
    reached.close()
    assert reached.missing(COLD[0x01E7D6]) == [], 'no case reached these regions'


def test_an_aircraft_launch_matches_the_original(enemy):
    """aircraft_launch (0x01E4D0) of a fighter and of a torpedo plane into tables with none,
    some and every record free and with a torpedo plane up or not."""
    d = enemy
    rng = random.Random(0x1E4D0)
    reached = Reached(d.o)
    for n in range(2000):
        d.randomise_enemy(rng)
        for i in range(4):
            if rng.random() < 0.5:
                w(d.o, AIRCRAFT + 0x34 * i, 0)
        kind = rng.choice([0, 1, 1, rng.randrange(0x10000)])
        x = rng.randrange(0x10000)
        height = rng.randrange(0, 0x100)
        facing = rng.choice([1, 0xFFFF])
        d.load_port()
        d.o.call(0x01E4D0, d.o.W(kind), d.o.W(x), d.o.W(height), d.o.W(facing))
        d.m6(0x01E4D0, s16(kind), s16(x), (height << 16) | facing)
        check(d, 'case %d' % n)
    reached.close()
    assert reached.missing(COLD[0x01E4D0]) == [], 'no case reached these regions'


TICK_ROUTINES = [
    (0x01B682, 'the guns at an enemy aircraft'),
    (0x01BC02, "the enemy's countdown and its launch"),
    (0x011622, "the airfields' launches"),
    (0x011510, "the ships' launches and the Japanese carrier's roll"),
    (0x011CAE, 'the ships sinking'),
]


@pytest.mark.parametrize('address,what', TICK_ROUTINES, ids=['%06X' % r[0] for r in TICK_ROUTINES])
def test_the_tick_routines_of_the_enemy_match_the_original(enemy, address, what):
    """The tick's routines around the enemy aircraft over 2,000 random states each: the guns'
    hits, bursts and the shooting down; the countdown with the button and without it, and
    the torpedo plane it launches on either side of the deck; an airfield's rolling
    aircraft and its next one; the ships' launches, the Japanese carrier's aircraft readied
    and rolling; a ship's rows, its score and the ticker's message, the carrier's, the lift,
    the game's end, the records cleared and the mission won."""
    d = enemy
    rng = random.Random(address)
    reached = Reached(d.o)
    for n in range(2000):
        d.randomise_enemy(rng)
        if address == 0x01BC02:
            w(d.o, PLAYER + 0x1C, rng.choice([1, 1, 1, 2, 0, 700]))
            w(d.o, TICK_INPUT, rng.choice([0, 0, 0, 0x10, 0x20, 0x30, 0x0F]))
        d.load_port()
        d.o.call(address)
        d.m6(address)
        check(d, '%s, case %d' % (what, n))
    reached.close()
    assert reached.missing(COLD.get(address, [])) == [], 'no case reached these regions'
