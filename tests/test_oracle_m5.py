"""M5 part 1 differential tests: the pure routines of the targets, the soldiers and the pools
against the original (SPEC 7.4, re/notes/porting-m5.md, "How the port is held").

Each routine runs twice on the same randomised state, once as the original's 68000 code
under the oracle and once as the port's C, and the results and every registered global and
table the two touched are compared, as tests/test_oracle_m4.py does it.  The state is a map
of the disk with the target tables built from its records, the soldier table and the pools
allocated in the emulated memory where the original's pointers name them.  rand_beam's
beam position is served on both sides from the port's entropy generator.
"""
import ctypes
import os
import random
import sys

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, 'tools'))
sys.path.insert(0, HERE)

from unicorn import UC_HOOK_MEM_READ                 # noqa: E402

import map_decode                                    # noqa: E402
import m4compare                                     # noqa: E402
from test_oracle_m4 import PlayerDifferential, w      # noqa: E402

TARGETS_4, TARGETS_3, SOLDIERS, TARGETS_F = 0x0254F8, 0x0254FC, 0x025500, 0x025504
COUNT_F, COUNT_3, COUNT_4, SOLDIER_COUNT = 0x025385, 0x025386, 0x025387, 0x0253C4
ISLAND_SPAN, ISLAND_SCORE = 0x025440, 0x025450
PLAYER = 0x025078
BEAM = 0xDFF006


def entropy_next(state):
    """src/rand.c's generator: (the new state, the VHPOSR-shaped value)."""
    state = (state * 1664525 + 1013904223) & 0xFFFFFFFF
    return state, ((state >> 24) & 0xFF) << 8 | ((state >> 8) & 0xFFFF) % 0xE4


class TargetsDifferential(PlayerDifferential):
    """The player's differential with the target tables, the soldiers and the pools of a map
    built in the emulated memory, and the beam position served from the port's stream."""

    def __init__(self, ported, name='c'):
        super().__init__(ported, name)
        o = self.o
        self.t4 = o.alloc(16 * 0x10)
        self.t3 = o.alloc(16 * 0x10)
        self.tf = o.alloc(32 * 0x0E)
        self.soldiers = o.alloc(160 * 8)
        self.splashes = o.alloc(0x50)
        o.w32(0x026F30, self.splashes)
        o.w32(TARGETS_4, self.t4)
        o.w32(TARGETS_3, self.t3)
        o.w32(TARGETS_F, self.tf)
        o.w32(SOLDIERS, self.soldiers)
        # The draw records of the three kinds, as map_scan's second walk finds them.
        self.kinds = {3: [], 4: [], 0xF: []}
        for i, word in enumerate(self.chart.words):
            f = map_decode.fields(word)
            if f['draw'] and f['slot'] in self.kinds:
                self.kinds[f['slot']].append(2 * i)
        o.uc.mem_map(0xDFF000, 0x1000)
        self.state = 1
        o.uc.hook_add(UC_HOOK_MEM_READ, self._beam, begin=BEAM, end=BEAM + 1)
        lib = ported.lib
        lib.wof_test_m5_call.argtypes = [ctypes.c_uint32, ctypes.c_int32, ctypes.c_int32,
                                         ctypes.c_int32, ctypes.POINTER(ctypes.c_int32)]
        lib.wof_test_m5_call.restype = ctypes.c_int32
        lib.wt_entropy_set.argtypes = [ctypes.c_uint]

    def _beam(self, uc, access, address, size, value, user):
        if address == BEAM:
            self.state, v = entropy_next(self.state)
            uc.mem_write(BEAM, v.to_bytes(2, 'big'))

    def memory(self):
        regions = dict(super().memory().regions)
        for base, size in ((self.t4, 16 * 0x10), (self.t3, 16 * 0x10), (self.tf, 32 * 0x0E),
                           (self.soldiers, 160 * 8), (self.splashes, 0x50)):
            regions[base] = bytes(self.o.read(base, size))
        return self.m4state.Memory(regions)

    def load_port(self):
        super().load_port()
        self.ported.lib.wt_entropy_set(self.state)

    def randomise(self, rng):
        """Tables as map_scan leaves them and as the play changes them: each target at its
        draw record, with random soldiers inside, counts and timers."""
        o = self.o
        islands = sorted(set(rng.randrange(4) for _ in range(2)))
        for table, kind, size in ((self.t3, 3, 0x10), (self.t4, 4, 0x10)):
            offsets = self.kinds[kind][:16]
            for i in range(16):
                at = table + size * i
                off = offsets[i] if i < len(offsets) else rng.randrange(0x2000)
                o.w32(at, off)
                x = off * 4
                o.w16(at + 4, (x - (44 if kind == 3 else rng.randrange(0, 40))) & 0xFFFF)
                o.w16(at + 6, (x + 16) & 0xFFFF)
                o.write(at + 8, bytes([rng.choice([0, 0, 1, 2, 5, 5, 6, 0xFF])]))
                o.write(at + 9, bytes([min(i // 3, 3) if rng.random() < 0.8 else rng.randrange(4)]))
                o.write(at + 0x0A, bytes([rng.randrange(0, 6)]))
                o.write(at + 0x0B, bytes([rng.choice([0, 0, 1, rng.randrange(256)])]))
                o.w16(at + 0x0C, rng.choice([0, 0, 1, 2, 0x168, rng.randrange(0x10000)]))
                o.w16(at + 0x0E, rng.choice([0, 1, 2, 0xC8, rng.randrange(0x10000)]))
            o.write(COUNT_3 if kind == 3 else COUNT_4,
                    bytes([min(len(offsets), rng.choice([len(offsets), rng.randrange(0, 15)]))]))
        offsets = self.kinds[0xF][:32]
        for i in range(32):
            at = self.tf + 0x0E * i
            o.w16(at, offsets[i] if i < len(offsets) else rng.randrange(0x2000))
            for k in range(2, 0x0E, 2):
                o.w16(at + k, rng.choice([0, 0, 1, 0x32, rng.randrange(0x10000)]))
            o.write(at + 8, bytes([rng.choice([0, 0, 0xFF])]))
        o.write(COUNT_F, bytes([len(offsets)]))
        count = rng.choice([0, 20, 70, 135, 160])
        w(o, SOLDIER_COUNT, count)
        for i in range(160):
            at = self.soldiers + 8 * i
            o.w16(at, rng.randrange(0, 0x4000))
            o.write(at + 2, bytes([rng.choice([1, 0xFF, 3, 0xFD])]))
            o.write(at + 3, bytes([rng.randrange(0, 9)]))
            o.write(at + 4, bytes([rng.randrange(256)]))
            o.write(at + 5, bytes([rng.randrange(4)]))
            o.w16(at + 6, rng.choice([0, 0, 1, 2, 3]))
        for i in range(8):
            w(o, ISLAND_SPAN + 2 * i, rng.choice(self.kinds[3] + self.kinds[4] + [0]))
            w(o, ISLAND_SCORE + 2 * i, rng.randrange(0, 4))
        o.w32(0x0253CA, rng.randrange(1 << 32))            # vblank_total
        w(o, 0x026912, rng.randrange(0x10000))              # rand_seed_const
        self.state = rng.randrange(1 << 32)
        del islands

    def port(self, orig, a=0, b=0, c=0):
        out = (ctypes.c_int32 * 4)()
        r = self.ported.lib.wof_test_m5_call(orig, a, b, c, out)
        return r, list(out)


@pytest.fixture
def targets(ported):
    d = TargetsDifferential(ported)
    yield d
    d.restore()


def check(d, what, want=None, got=None):
    found = d.differences()
    assert found == [] and want == got, '%s: original %r, port %r, %s' % (what, want, got, found[:6])


def s16(v):
    v &= 0xFFFF
    return v - 0x10000 if v & 0x8000 else v


def test_the_target_lookups_match_the_original(targets):
    """0x014AE4, the four records of a target at x, and 0x014B54, its table entry, at every
    world x of map c that a record starts at and five pixels into it, with the tables built
    from the map's own draw records.  Both are reached only for x on the map: a hit first
    asks map_slot_at (0x0146EC), which gives the sea left of the map and past its end, and a
    soldier runs on land; so x runs from 0 to the map's extent, where the original's reads
    stay inside the record list and its four zero records (re/notes/map.md)."""
    d = targets
    rng = random.Random(0x14AE)
    d.randomise(rng)
    d.load_port()
    xs = [8 * i + k for i in range(len(d.chart.words)) for k in (0, 5)]
    xs = [x for x in xs if x < d.chart.extent]
    tables = {d.t4: 0x400, d.t3: 0x300, d.tf: 0xF00}
    sizes = {d.t4: 0x10, d.t3: 0x10, d.tf: 0x0E}
    for x in xs:
        x16 = x & 0xFFFF
        d.o.call(0x014AE4, regs={'d0': x16})
        want = [d.o.reg(r) & 0xFFFF for r in ('a0', 'a1', 'a2', 'a3')]
        _, got = d.port(0x014AE4, s16(x16))
        assert want == [g & 0xFFFF for g in got], 'x %d: records %s, port %s' % (s16(x16), want, got)
        d0 = d.o.call(0x014B54, regs={'d0': x16})
        if d0 & 0x80:
            want = -1
        else:
            a0 = d.o.reg('a0')
            base = max(t for t in tables if t <= a0)
            want = tables[base] | ((a0 - base) // sizes[base])
        got, _ = d.port(0x014B54, s16(x16))
        assert want == got, 'x %d: target %x, port %x' % (s16(x16), want, got)
    check(d, 'lookups')


def test_the_range_frame_matches_the_original(targets):
    """0x014DB8: targets and aircraft anywhere, heights from the water to the ceiling, at
    both scales."""
    d = targets
    rng = random.Random(0x14DB)
    for n in range(3000):
        w(d.o, 0x024F36, rng.choice([8, 8, 1]))
        a, b = rng.randrange(0x10000), rng.randrange(0x10000)
        if n % 2:
            b = (a + rng.randrange(-0x220, 0x220)) & 0xFFFF
        c = rng.choice([rng.randrange(0, 200), rng.randrange(0, 0x460)])
        d.load_port()
        want = d.o.call(0x014DB8, regs={'d0': a, 'd1': b, 'd2': c})
        got, _ = d.port(0x014DB8, s16(a), s16(b), c)
        check(d, 'case %d' % n, s16(want & 0xFFFF), got)


def test_the_island_bonus_matches_the_original(targets):
    """0x015AE8 for every rank, mission and island."""
    d = targets
    for rank in range(7):
        for mission in range(0, 5):
            for island in range(4):
                w(d.o, 0x0253BE, rank)
                w(d.o, 0x0253C0, mission)
                d.load_port()
                want = d.o.call(0x015AE8, regs={'d0': island}) & 0xFFFF
                got, _ = d.port(0x015AE8, island)
                check(d, 'rank %d mission %d island %d' % (rank, mission, island), want, got & 0xFFFF)


def test_a_soldier_out_matches_the_original(targets):
    """0x011E82 in both modes from both target tables: the direction given, from
    vblank_total, from the island's span and turned round by rand_beam, into a table with
    free records or none."""
    d = targets
    rng = random.Random(0x11E8)
    for n in range(600):
        d.randomise(rng)
        if n % 5 == 0:
            # Every record but one in use: the walk takes the last.  With none free the
            # original's walk has no end and runs past the table, which the balance of
            # soldiers and records never lets happen (the port's stand-in).
            count = d.o.r16(SOLDIER_COUNT)
            for i in range(160):
                w(d.o, d.soldiers + 8 * i + 6, 0 if i == count - 1 else 1)
        table = rng.choice([3, 4])
        index = rng.randrange(0, 12)
        mode = rng.choice([1, 1, 2, 2, 0, 3])
        count = d.o.r16(SOLDIER_COUNT)
        if count and not any(d.o.r16(d.soldiers + 8 * i + 6) == 0 for i in range(count)):
            w(d.o, d.soldiers + 8 * (count - 1) + 6, 0)
        d1 = rng.choice([0, 1, 0xFFFF, rng.randrange(0x10000)])
        a0 = (d.t3 if table == 3 else d.t4) + 0x10 * index
        d.load_port()
        d.o.call(0x011E82, regs={'d0': mode, 'd1': d1, 'a0': a0})
        d.port(0x011E82, (table << 8) | index, mode, s16(d1))
        check(d, 'case %d' % n)


def test_a_dug_out_refilled_matches_the_original(targets):
    """0x014FEE with 0x015034: the nearest barracks of the island with two soldiers or
    more gives one up, which runs to the dug-out."""
    d = targets
    rng = random.Random(0x14FE)
    ran = 0
    for n in range(600):
        d.randomise(rng)
        count = d.o.read(COUNT_4, 1)[0]
        if count == 0:
            continue
        index = rng.randrange(0, 12)
        d.load_port()
        d.o.call(0x014FEE, regs={'a0': d.t3 + 0x10 * index})
        d.port(0x014FEE, index)
        check(d, 'case %d' % n)
        ran += 1
    assert ran > 300


def test_the_pools_claims_match_the_original(targets):
    """smoke_claim (0x015460) at every height around the ground's line into a pool with free
    records or none; splash_spawn (0x0152B0) over land and sea into a pool with free records
    or none; smoke_at_player
    (0x0154E0) in every attitude, both facings, with D2's upper word 0 or rand_beam's."""
    d = targets
    rng = random.Random(0x1546)
    o = d.o
    for n in range(900):
        d.randomise(rng)
        for i in range(40):
            w(o, d.smoke + 0x14 * i + 0x10, rng.choice([0, 1, 5] if n % 7 else [3]))
        for i in range(20):
            o.write(d.splashes + 4 * i + 2, bytes([rng.choice([0, 3] if n % 4 else [2])]))
        w(o, PLAYER + 0x14, rng.choice([1, -1]))
        w(o, 0x02540E, rng.choice([0, rng.randrange(0, 26)]))
        w(o, 0x026E5C, rng.randrange(0, 0x7FFF))
        w(o, 0x026E60, rng.randrange(0, 0x440))
        w(o, 0x026E62, rng.randrange(0x10000))
        kind = n % 3
        d.load_port()
        if kind == 0:
            x = rng.randrange(1 << 32)
            y = rng.choice([rng.randrange(0, 0x200000), 0x100000, 0xFFFFF, rng.randrange(1 << 32)])
            k = rng.randrange(1, 7)
            want = o.call(0x015460, regs={'d0': x, 'd1': y, 'd2': k})
            got, _ = d.port(0x015460, x - (1 << 32) if x & 0x80000000 else x,
                            y - (1 << 32) if y & 0x80000000 else y, k)
            check(d, 'smoke_claim %d' % n, want, got & 0xFFFFFFFF)
        elif kind == 1:
            x = rng.choice([rng.randrange(0, d.chart.extent), rng.randrange(0x10000)])
            o.call(0x0152B0, regs={'d0': x})
            d.port(0x0152B0, s16(x))
            check(d, 'splash_spawn %d' % n)
        else:
            upper = rng.choice([0, (0x1FCCD + s16(o.r16(0x026912)) * 0x1AFB) >> 16 & 0xFFFF])
            k = rng.randrange(1, 7)
            o.call(0x0154E0, regs={'d0': k, 'd2': (upper << 16) | rng.randrange(0x10000)})
            d.port(0x0154E0, k, upper)
            check(d, 'smoke_at_player %d' % n)


def test_a_targets_frame_and_fire_match_the_original(targets):
    """target_frame (0x014D50) and target_fire (0x014F5C) with the aircraft on the deck, in
    the eighth-scale view and at full scale near and far, low and high, with the cheat's
    0x026F72 and without; target_fire gets the registers targets_3_draw leaves: D2 with
    rand_beam's upper word, D1 with 0."""
    d = targets
    rng = random.Random(0x14F5)
    o = d.o
    for n in range(1200):
        d.randomise(rng)
        w(o, PLAYER + 0x0C, rng.choice([0, 0, 0, 1]))
        w(o, PLAYER + 0x00, rng.choice([rng.randrange(0, 200), rng.randrange(0, 1100)]))
        w(o, PLAYER + 0x10, rng.choice([1, 2, 6, 0]))
        w(o, 0x024F34, rng.choice([0, 0, 3]))
        w(o, 0x024F36, 1 if o.r16(0x024F34) else 8)
        px = rng.randrange(0, 0x4000)
        w(o, 0x026E5C, px)
        w(o, 0x026E60, rng.randrange(0, 200))
        w(o, 0x027456, rng.choice([0x2710, rng.randrange(0, 0x300)]))
        w(o, 0x026F72, rng.choice([0, 0, 1]))
        x = (px + rng.randrange(-0x240, 0x240)) & 0xFFFF
        d.load_port()
        if n % 2:
            want = o.call(0x014D50, regs={'d0': x})
            got, _ = d.port(0x014D50, s16(x))
            check(d, 'target_frame %d' % n, s16(want), got)
        else:
            upper = (0x1FCCD + s16(o.r16(0x026912)) * 0x1AFB) >> 16 & 0xFFFF
            o.call(0x014F5C, regs={'d0': x, 'd1': rng.randrange(0x10000),
                                   'd2': (upper << 16) | rng.randrange(0x10000)})
            d.port(0x014F5C, s16(x))
            check(d, 'target_fire %d' % n)
