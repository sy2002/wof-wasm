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
    more gives one up, which runs to the dug-out; D1, which it does not save, is left the
    direction as a long, or as it came when no barracks gave one, and its upper word goes
    on through the pass (M7's finding at one VBlank a pass)."""
    d = targets
    rng = random.Random(0x14FE)
    ran = 0
    for n in range(600):
        d.randomise(rng)
        count = d.o.read(COUNT_4, 1)[0]
        if count == 0:
            continue
        index = rng.randrange(0, 12)
        d1 = rng.randrange(1 << 32)
        d.load_port()
        d.o.call(0x014FEE, regs={'a0': d.t3 + 0x10 * index, 'd1': d1})
        got, _ = d.port(0x014FEE, index, d1 >> 16)
        check(d, 'case %d' % n, d.o.reg('d1') >> 16, got & 0xFFFF)
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
    rand_beam's upper word, D1 with 0 (another upper word, after a refill or a pillbox's
    smoke in the same pass, is tests/test_oracle_m7.py's)."""
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
            d.port(0x014F5C, s16(x), 0, upper)
            check(d, 'target_fire %d' % n)


# ------------------------------------------------ the exclusive-or blit, the muzzle flash

SHAPE_DRAW_XOR = 0x020E24
HELLCAT = 1


def test_the_exclusive_or_blit_matches_the_blitter(ported):
    """shape_draw_xor (0x020E24), which the guns' muzzle flash draws with on the 5-plane
    playfield: every shape of hellcat.shp, the flash's frames among them, at aligned,
    shifted and hanging-off positions under the full and a narrow clip, over a noisy
    background, against the original's register programme replayed by tests/blitter.py.
    The core is reset first, so that hellcat.shp faces as the file does."""
    from test_oracle_m4 import (PLAYFIELD, CLIPS, POSITIONS_5, CUSTOM, Reference, background,
                                draw_op, differ)
    ported.reset_core()
    bytes_per_row, rows, depth = PLAYFIELD
    width = bytes_per_row * 8
    reference = Reference('shapes/hellcat.shp', bytes_per_row, rows, depth)
    o = reference.original.o
    noisy = background(width, rows, 0x6A, depth)
    changed = cases = 0
    for index in range(reference.count):
        record = reference.container['records'][index]
        for x, y in POSITIONS_5:
            for clip in CLIPS[PLAYFIELD][:2]:
                def call():
                    o.call(SHAPE_DRAW_XOR, regs={'a0': record, 'd0': x & 0xFFFF, 'd1': y & 0xFFFF,
                                                 'a6': CUSTOM})
                want = reference.replay(clip, noisy, call)
                got = draw_op(ported, 5, PLAYFIELD, clip, noisy, slot=HELLCAT, index=index, a=x, b=y)
                assert got == want, 'hellcat.shp %d at (%d,%d) clip %s: %d pixels differ' % (
                    index, x, y, clip, differ(got, want))
                changed += want != noisy
                cases += 1
    assert changed > cases // 3, 'only %d of %d blits drew anything' % (changed, cases)


# ================================================================ part 2: the tick

from unicorn import UC_HOOK_CODE                     # noqa: E402

OBJECTS, OBJECT_EXTRA, CRASH_OBJECT = 0x024CAE, 0x025594, 0x027700
BALLOONS = 0x026F66
DESTROYER = 0x025460
SYSBASE = 0x026F74


def raw_do_fmt(o, fmt, data):
    """exec's RawDoFmt for the formats the ticker's messages use (as tools/headless_os.py
    models it): the characters with the terminating NUL."""
    text = o.read(fmt, 256).split(b'\0')[0]
    out = bytearray()
    i = 0
    while i < len(text):
        c = text[i]
        i += 1
        if c != 0x25:
            out.append(c)
            continue
        long = False
        width = 0
        while i < len(text) and 0x30 <= text[i] <= 0x39:
            width, i = width * 10 + text[i] - 0x30, i + 1
        if i < len(text) and text[i] == 0x6C:
            long, i = True, i + 1
        kind = chr(text[i])
        i += 1
        if kind == 's':                   # a long pointer to the text
            pointer = o.r32(data)
            data += 4
            field = o.read(pointer, 256).split(b'\0')[0] if pointer else b''
            out += b' ' * max(0, width - len(field)) + field
            continue
        if long:
            value = o.r32(data)
            data += 4
            value = value - (1 << 32) if value & 0x80000000 else value
        else:
            value = o.r16(data)
            data += 2
            value = value - 0x10000 if value & 0x8000 else value
        assert kind in 'du', kind
        field = str(value if kind == 'd' else value & (0xFFFFFFFF if long else 0xFFFF)).encode()
        out += b' ' * max(0, width - len(field)) + field
    return bytes(out) + b'\0'


class TickDifferential(TargetsDifferential):
    """The targets' differential with what the tick's weapons reach besides: the Balloons
    pool, a destroyer with a gun list for a rocket to aim at and hit, airfields, and exec's
    RawDoFmt for the ticker's message when an island is done."""

    def __init__(self, ported, name='c'):
        super().__init__(ported, name)
        o = self.o
        self.balloons = o.alloc(0x168)
        o.w32(BALLOONS, self.balloons)
        self.guns = o.alloc(16 * 0x0E)
        base = o.alloc(0x400) + 0x300
        o.write(base - 0x20A, bytes.fromhex('4E75'))                 # rts
        o.w32(SYSBASE, base)

        def fmt(uc, address, size, user):
            text = raw_do_fmt(o, o.reg('a0'), o.reg('a1'))
            a3 = o.reg('a3')
            o.write(a3, text)
        o.uc.hook_add(UC_HOOK_CODE, fmt, begin=base - 0x20A, end=base - 0x20A)
        lib = ported.lib
        lib.wt_map_addresses.argtypes = [ctypes.c_void_p, ctypes.c_uint]

    def memory(self):
        m = super().memory()
        regions = dict(m.regions)
        regions[self.balloons] = bytes(self.o.read(self.balloons, 0x168))
        regions[self.guns] = bytes(self.o.read(self.guns, 16 * 0x0E))
        return self.m4state.Memory(regions)

    def target_xs(self):
        return [4 * off for k in self.kinds.values() for off in k] or [0]

    def randomise_tick(self, rng):
        """The targets' state and around it the objects in flight and at rest, a destroyer
        with guns, the airfields, the aircraft, the view and the counters."""
        o = self.o
        self.randomise(rng)
        for i in range(32):                  # a pillbox's island is one map_scan can give
            w(o, self.tf + 0x0E * i + 6, rng.randrange(0, 4))
        xs = self.target_xs()
        px = rng.choice(xs) + rng.randrange(-0x200, 0x200)
        w(o, 0x026E5C, px)                                            # draw_player_x
        w(o, 0x026E60, rng.randrange(0, 0x100))                       # draw_player_y
        w(o, 0x024F34, rng.choice([0, 0, 0, 3]))                      # view_shift
        o.write(0x026E3C, bytes([rng.choice([0, 1, 0xFF])]))           # frame_drawn
        w(o, 0x0253C8, rng.randrange(0, 100))                         # pass_counter
        o.w32(0x025350, rng.choice([0x6000, 0x6000, rng.randrange(0x10000)]))
        w(o, PLAYER + 0x14, rng.choice([1, -1]))
        w(o, PLAYER + 0x00, rng.randrange(0, 0x100))
        w(o, PLAYER + 0x02, px)
        o.w32(0x026E6E, rng.choice([rng.randrange(0, 0x1000000), rng.randrange(1 << 32)]))
        for i in range(4):                                            # the airfields
            at = 0x0252FA + 0x14 * i
            lo = rng.choice([0, 0, rng.choice(xs) - rng.randrange(0, 0x100)])
            w(o, at, lo)
            w(o, at + 2, lo + rng.randrange(0, 0x200))
        # the destroyer: afloat, its span of map offsets, and a gun list of up to five guns
        o.write(0x02537A, bytes([rng.choice([0, 0xFF])]))              # has_destroyer
        w(o, DESTROYER + 0x04, rng.choice([0, 0x100, 0x1FF]))
        span = rng.randrange(0, len(self.chart.words) * 2)
        w(o, DESTROYER + 0x00, span)
        w(o, DESTROYER + 0x02, span + rng.randrange(0, 0x40))
        o.w32(DESTROYER + 0x06, rng.choice([self.guns, self.guns, 0]))
        w(o, DESTROYER + 0x0A, rng.randrange(0, 6))
        w(o, DESTROYER + 0x0C, rng.choice([0, 1, 2, 5]))
        o.w32(DESTROYER + 0x12, rng.choice([0, 1, rng.randrange(1 << 32)]))
        for i in range(16):
            at = self.guns + 0x0E * i
            for k in range(0, 0x0E, 2):
                w(o, at + k, rng.randrange(0x10000))
            w(o, at + 4, rng.choice(xs) + rng.randrange(-0x40, 0x40))
            w(o, at + 8, rng.choice([0, 0, 0xFFFF]))
        for i in range(16):
            at = OBJECTS + 0x2A * i if i < 15 else OBJECT_EXTRA
            self.random_object(rng, at, xs, px)
        for i in range(20):
            at = self.balloons + 0x12 * i
            o.w32(at, rng.randrange(1 << 32))
            o.w32(at + 4, rng.choice([rng.randrange(0x380000, 0xB00000), rng.randrange(1 << 32)]))
            o.w32(at + 8, rng.randrange(0x10000, 0x30000))
            o.w32(at + 0x0C, rng.randrange(0x10000, 0x30000))
            o.write(at + 0x10, bytes([rng.randrange(3), rng.choice([0, 0xFF])]))

    def random_object(self, rng, at, xs, px):
        o = self.o
        kind = rng.choice([0, 0xFF, 0xFF, 0xFF, 8])
        typ = rng.choice([0, 1, 2])
        x = rng.choice([rng.choice(xs) + rng.randrange(-24, 24), rng.randrange(0, 0x4000),
                        px + rng.randrange(-0x600, 0x600)])
        w(o, at + 0x00, x)
        w(o, at + 0x02, rng.randrange(0x10000))
        w(o, at + 0x04, rng.choice([rng.randrange(0, 0x30), rng.randrange(0, 0x100),
                                    rng.randrange(0x10000)]))
        w(o, at + 0x06, rng.choice([0, 0, rng.randrange(0x10000)]))
        w(o, at + 0x08, x + rng.randrange(-20, 20))                  # the drawing's x
        o.write(at + 0x0C, bytes([rng.choice([0, 8, 0xFF])]))          # the drawing's kind
        o.w32(at + 0x0E, rng.choice([rng.randrange(-0x80000, 0x80000) & 0xFFFFFFFF,
                                     0x45000, 0xFFFBB000, 0]))
        o.w32(at + 0x12, rng.choice([rng.randrange(-0x100000, 0x40000) & 0xFFFFFFFF,
                                     rng.randrange(0, 0x100), 1, 0]))
        o.w32(at + 0x16, rng.randrange(-0x20000, 0x20000) & 0xFFFFFFFF)
        o.w32(at + 0x1A, rng.randrange(-0x20000, 0x20000) & 0xFFFFFFFF)
        frame = rng.choice([rng.randrange(0, 0x0C), 0x0A, 0x0A if typ == 2 else 3])
        o.write(at + 0x1E, bytes([frame, rng.randrange(256), kind, rng.randrange(0, 8)]))
        w(o, at + 0x22, typ)
        w(o, at + 0x24, rng.choice([0, 0, 1, 2, rng.randrange(0, 13)]))
        w(o, at + 0x26, rng.choice([rng.randrange(-0x200, 0), rng.randrange(-0x400, 0x400)]))
        w(o, at + 0x28, rng.randrange(0, 1600))


@pytest.fixture
def tick(ported):
    d = TickDifferential(ported)
    yield d
    d.restore()


def test_the_angles_match_the_original(tick):
    """The sine (0x015108) and cosine (0x015104) of every angle of a turn and of words
    beyond, the tangent (0x01514C) of every byte with both signs, and the bearing
    (0x015CA6) of random vectors in every octant, on the axes, on the diagonals and at the
    word's ends, with the upper word of D1 that divu takes into the dividend."""
    d = tick
    o = d.o
    rng = random.Random(0x15CA)
    angles = list(range(0, 0x400)) + [rng.randrange(0x10000) for _ in range(200)] + [0x8000, 0x7FFF]
    for a in angles:
        for orig in (0x015108, 0x015104):
            want = s16(o.call(orig, regs={'d0': a}))
            got, _ = d.port(orig, s16(a))
            assert want == got, '%06x of %04x: %d, port %d' % (orig, a, want, got)
    for a in list(range(-0x100, 0x101)) + [0x7FFF, -0x8000]:
        want = s16(o.call(0x01514C, regs={'d0': a & 0xFFFF}))
        got, _ = d.port(0x01514C, a)
        assert want == got, 'tangent of %d: %d, port %d' % (a, want, got)
    cases = [(0, 0), (1, 0), (0, 1), (5, 5), (-5, 5), (5, -5), (-0x8000, 3), (3, -0x8000),
             (0x7FFF, 0x7FFF), (-0x7FFF, 0x7FFF)]
    cases += [(rng.randrange(-0x8000, 0x8000), rng.randrange(-0x8000, 0x8000)) for _ in range(3000)]
    cases += [(rng.randrange(-300, 300), rng.randrange(-300, 300)) for _ in range(3000)]
    for x, y in cases:
        high = rng.choice([0, 0, 2, rng.randrange(0x10000)])
        want = s16(o.call(0x015CA6, regs={'d0': (rng.randrange(0x10000) << 16) | (y & 0xFFFF),
                                           'd1': (high << 16) | (x & 0xFFFF)}))
        got, _ = d.port(0x015CA6, x, y, high)
        assert want == got, 'bearing of (%d, %d) over %04x: %d, port %d' % (x, y, high, want, got)


def test_the_guns_reach_matches_the_original(tick):
    """guns_ground_x (0x011A46): every bearing from level to straight down and some upward,
    at heights from the water to the ceiling and beyond (divu's overflow), both facings."""
    d = tick
    rng = random.Random(0x11A4)
    for n in range(4000):
        d.randomise_tick(rng)
        bearing = rng.choice([rng.randrange(-0x120, 0x10), 0xFF01 - 0x10000, -1, -0x100,
                              rng.randrange(-0x8000, 0x8000)])
        d.load_port()
        want = s16(d.o.call(0x011A46, regs={'d0': bearing & 0xFFFF}))
        got, _ = d.port(0x011A46, bearing)
        check(d, 'bearing %d' % bearing, want, got)


def test_the_soldiers_and_torpedoes_hit_match_the_original(tick):
    """soldiers_hit (0x011A8C) and torpedoes_hit (0x011AE2) at spans on and off running
    soldiers and drawn torpedoes: the scream's registers carried on to the next soldier."""
    d = tick
    rng = random.Random(0x11A8)
    for n in range(1500):
        d.randomise_tick(rng)
        count = d.o.r16(SOLDIER_COUNT)
        x = rng.choice([rng.randrange(0, 0x4000)] +
                       [d.o.r16(d.soldiers + 8 * i) for i in range(count)][:5] or [0])
        for i in range(min(count, 12)):
            if rng.random() < 0.4:
                w(d.o, d.soldiers + 8 * i, x + rng.randrange(-24, 24))
                w(d.o, d.soldiers + 8 * i + 6, 1)
        width = rng.choice([8, 0x10, rng.randrange(0, 0x40)])
        d.load_port()
        if n % 3:
            d.o.call(0x011A8C, regs={'d0': x & 0xFFFF, 'd1': width})
            d.port(0x011A8C, x, width)
        else:
            d.o.call(0x011AE2, regs={'d0': x & 0xFFFF, 'd1': width})
            d.port(0x011AE2, x, width)
        check(d, 'case %d' % n)


def test_the_tick_routines_match_the_original(tick):
    """gun_splashes (0x0119BC), engine_smoke (0x011BFC, D2's upper word 0 as logic_tick
    leaves it), target_timers (0x011DE4, with 0x011E82 from the tick) and balloons_step
    (0x011C5E) on random states."""
    d = tick
    o = d.o
    rng = random.Random(0x119B)
    for n in range(2400):
        d.randomise_tick(rng)
        orig = (0x0119BC, 0x011BFC, 0x011DE4, 0x011C5E)[n % 4]
        w(o, 0x02536A, rng.choice([0, 1, 1]))                          # the guns fire
        w(o, 0x026E62, rng.choice([-1, -3, 0, 2]))
        w(o, 0x025AAA, rng.choice([0, 0, 1]))
        w(o, 0x025404, rng.choice([rng.randrange(-0x100, 0), rng.randrange(-0x400, 0x400)]))
        w(o, PLAYER + 0x0C, rng.choice([0, 0, 0, 6, 8, 1]))
        w(o, PLAYER + 0x12, rng.choice([0x80, 0x7F, 0x70, 0x6D, 0x6C, rng.randrange(0, 0x81)]))
        w(o, 0x027346, rng.choice([0, 1]))
        w(o, 0x02540E, rng.choice([0, 0, rng.randrange(0, 26)]))
        o.write(0x02535D, bytes([rng.choice([0, 0xFF])]))              # balloons_on
        count = o.r16(SOLDIER_COUNT)
        for i in range(count):                                         # records to come out into
            if rng.random() < 0.3:
                w(o, d.soldiers + 8 * i + 6, 0)
        if orig == 0x0119BC and count:
            # running soldiers around the ground the bullets reach, the span's edges among them
            ground = o.call(0x011A46, regs={'d0': o.r16(0x025404)}) & 0xFFFF
            for i in rng.sample(range(count), min(count, 6)):
                w(o, d.soldiers + 8 * i, ground + rng.choice([-17, -16, -15, 15, 16, 17,
                                                              rng.randrange(-20, 21)]))
                w(o, d.soldiers + 8 * i + 6, 1)
        d.load_port()
        o.call(orig, regs={'d2': rng.randrange(0x10000)})
        d.port(orig)
        check(d, '%06x case %d' % (orig, n))


def test_the_objects_step_matches_the_original(tick):
    """objects_step (0x010A72) with 0x010AA6 over random records of every type and kind:
    rockets falling, aimed (0x01099A, at a pillbox of map c or a destroyer's gun) and in
    flight far and near, bombs and torpedoes falling onto land, targets, the sea, a ship and
    an airfield, torpedoes running out of time and into land; each hit (0x0146DC) with the
    map records it rewrites, the soldiers it kills, the flash, the score, an island done
    and the mission won with the ticker's message.  D4 comes in random."""
    d = tick
    rng = random.Random(0x10A7)
    for n in range(2500):
        d.randomise_tick(rng)
        d4 = rng.randrange(1 << 32)
        d.load_port()
        d.o.call(0x010A72, regs={'d4': d4})
        d.port(0x010A72, d4 - (1 << 32) if d4 & 0x80000000 else d4)
        check(d, 'case %d' % n)


def test_the_hits_match_the_original(tick):
    """weapon_hit (0x0146DC) by an object of every type at every record of map c that a
    target, the land, the sea or the destroyer occupies, and crash_hit (0x0146C6) at them."""
    d = tick
    o = d.o
    rng = random.Random(0x146D)
    xs = d.target_xs()
    for n in range(3000):
        d.randomise_tick(rng)
        index = rng.randrange(16)
        at = OBJECTS + 0x2A * index if index < 15 else OBJECT_EXTRA
        x = rng.choice([rng.choice(xs) + rng.randrange(-12, 12), rng.randrange(0, d.chart.extent)])
        w(o, at, x)
        d.load_port()
        if n % 4:
            o.call(0x0146DC, regs={'a0': at})
            d.port(0x0146DC, index)
        else:
            record = rng.randrange(0, len(d.chart.words)) * 2
            o.call(0x0146C6, o.L(d.map_base + record))
            d.port(0x0146C6, record)
        check(d, 'case %d' % n)


def test_the_drop_matches_the_original(tick):
    """0x01107C with 0x0107F2 and the launch at 0x01088E: every weapon type, counts from none
    to unlimited, bearings up and down, both facings, with free records and none."""
    d = tick
    o = d.o
    rng = random.Random(0x1107)
    for n in range(1500):
        d.randomise_tick(rng)
        w(o, 0x0253A4, rng.choice([0, 1, 2]))                          # weapon_type
        o.write(0x02536D, bytes([rng.choice([0, 1, 5, 30, 0xFF])]))    # weapon_count
        w(o, 0x025404, rng.randrange(-0x400, 0x400))
        w(o, 0x025414, rng.randrange(0, 1600))                         # airspeed
        for k in (0x026E62, 0x026E66, 0x026E6A, 0x026E6E):
            o.w32(k, rng.randrange(1 << 32))
        if n % 5 == 0:
            for i in range(15):
                o.write(OBJECTS + 0x2A * i + 0x20, bytes([0xFF]))
        d.load_port()
        o.call(0x01107C)
        d.port(0x01107C)
        check(d, 'case %d' % n)
