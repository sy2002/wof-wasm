"""The left-overs of SPEC.md section 10 that M5 answers, each by observation on its script.

    .venv/bin/python tools/m5_observe.py fall        how +0x12 moves +0x04, and the types
    .venv/bin/python tools/m5_observe.py pools       who writes Ricochet and Balloons
    .venv/bin/python tools/m5_observe.py flash       the sky's flash: who sets it, the rows
    .venv/bin/python tools/m5_observe.py couplings   the second coupling table of passes.md
    .venv/bin/python tools/m5_observe.py mapwrites   who writes the map's records in a mission

Each command runs the headless original over scripts of tools/m5_scripts.py with observers
or write hooks and prints what it saw; re/notes/porting-m5.md, "The left-overs of section
10", quotes the results.
"""
import argparse
import collections
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

from unicorn import UC_HOOK_MEM_WRITE                        # noqa: E402
from unicorn.m68k_const import UC_M68K_REG_PC                # noqa: E402

import headless                                              # noqa: E402
import m5_scripts                                            # noqa: E402

OBJECTS, EXTRA = 0x024CAE, 0x025594
PLAYER = 0x025078
FLASH_COUNT, FLASH_COLOUR = 0x025416, 0x025418


def machine_for(name, cls=headless.Headless, **options):
    m = cls(m5_scripts.script(name), **options)
    m5_scripts.install_pokes(m, m5_scripts.POKES.get(name))
    return m


def s16(v):
    return v - 0x10000 if v & 0x8000 else v


def s32(v):
    return v - (1 << 32) if v & 0x80000000 else v


def records(o):
    for i in range(16):
        yield i, (OBJECTS + 0x2A * i if i < 15 else EXTRA)


# ----------------------------------------------------------------------------------- fall

def fall(names=('bomb_a', 'high_a', 'rockets_a', 'torpedo_a', 'bomb_b')):
    """Every tick, every object record in flight (kind 0xFF) of a type other than 0: the rule
    `y' = high word of (+0x12' + (y << 16 | +0x06))` against the record's next height, where
    +0x12' is the vertical long after the tick subtracted g_025350 (object_step 0x010B76).
    Also which weapon type each record carries against weapon_type at the drop."""
    for name in names:
        m = machine_for(name)
        prev = {}
        held = broke = 0
        types = collections.Counter()
        frac = collections.Counter()
        limit = m5_scripts.script(name)['stop']['vblanks']
        while m.run(until='tick') == 'tick' and m.vblanks < limit:
            o = m.o
            now = {}
            for i, a in records(o):
                kind = o.read(a + 0x20, 1)[0]
                t = s16(o.r16(a + 0x22))
                now[i] = (kind, t, s16(o.r16(a + 4)), o.r16(a + 6), s32(o.r32(a + 0x12)),
                          o.read(a + 0x1E, 1)[0])
                if kind == 0xFF and prev.get(i, (0,))[0] != 0xFF:
                    types[(t, s16(o.r16(0x0253A4)))] += 1
            for i, (kind, t, y, w06, v, frame) in now.items():
                p = prev.get(i)
                if not p or p[0] != 0xFF or kind != 0xFF or t == 0 or (t == 2 and frame == 0x0A):
                    continue
                if y <= 0x1E:
                    continue                    # it came down this tick: the height is clamped
                want = s16(((v + ((p[2] << 16) | p[3])) >> 16) & 0xFFFF)
                frac[p[3]] += 1
                if want == y:
                    held += 1
                else:
                    broke += 1
            prev = now
        print('%-10s the rule held %d times, broke %d; fractions +0x06 seen %s; (type, weapon_type '
              'at the drop) %s' % (name, held, broke, dict(frac.most_common(4)), dict(types)))


# ---------------------------------------------------------------------------------- pools

class Writes(headless.Headless):
    """The original with a write hook on chosen ranges; per range the writers."""

    def __init__(self, run, ranges, **options):
        super().__init__(run, **options)
        self.watch = ranges
        self.writers = collections.defaultdict(collections.Counter)
        for label, (begin, length) in ranges.items():
            self.uc.hook_add(UC_HOOK_MEM_WRITE, self._write, begin=begin,
                             end=begin + length - 1, user_data=label)

    def _write(self, uc, access, address, size, value, label):
        pc = uc.reg_read(UC_M68K_REG_PC)
        self.writers[label][(self.names.routine(pc), self.phase())] += 1


def pools(names=None):
    """Who writes the Ricochet and the Balloons pools, over every M5 script: their
    allocations are found through their pointers after the start (0x026EA4, 0x026F66), and
    balloons_on (0x02535D), the Balloons' switch, is watched as well."""
    for name in names or m5_scripts.SCRIPTS:
        probe = machine_for(name)
        probe.run(until='inner')
        ric, bal = probe.o.r32(0x026EA4), probe.o.r32(0x026F66)
        m = machine_for(name, Writes, ranges={'Ricochet': (ric, 0x50), 'Balloons': (bal, 0x168),
                                             'balloons_on': (0x02535D, 1)})
        m.run()
        print('%-13s %s' % (name, {k: dict(v) for k, v in m.writers.items()} or 'no writes'))


# ---------------------------------------------------------------------------------- flash

def flash(names=('rockets_a', 'crash_a', 'hit_a', 'rockets_c', 'island_a')):
    """Every write of flash_count and flash_colour with its writer, and per pass while the
    flash runs the count before the pass, which decides the colour flip_buffers pokes."""
    for name in names:
        m = machine_for(name, Writes, ranges={'flash_count': (FLASH_COUNT, 2),
                                             'flash_colour': (FLASH_COLOUR, 2)})
        runs, count, before = [], 0, 0
        limit = m5_scripts.script(name)['stop']['vblanks']
        while True:
            r = m.run(until='pass')
            if r != 'pass' or m.vblanks >= limit:
                break
            now = m.o.r16(FLASH_COUNT)
            if before or now:
                runs.append((m.passes, before, now, hex(m.o.r16(FLASH_COLOUR))))
            before = now
        print('%-10s writers %s' % (name, {k: dict(v) for k, v in m.writers.items()}))
        print('           passes with a flash (pass, count before, after, colour): %s%s'
              % (runs[:12], ' ...' if len(runs) > 12 else ''))


# ------------------------------------------------------------------------------ couplings

def couplings(names=('island_a', 'guns_a', 'hit_a')):
    """The second coupling table of re/notes/passes.md: the score and island_score written in
    a pass (soldiers_draw), the player's oil (+0x12) written in a pass (target_fire), and the
    guard 0x024F24 of frame_update's own call of the restart."""
    for name in names:
        m = machine_for(name, Writes, ranges={'player_score': (0x02534C, 4),
                                             'island_score': (0x025450, 16),
                                             'player_oil': (PLAYER + 0x12, 2),
                                             'restart_guard': (0x024F24, 2)})
        m.run()
        print('%-9s %s' % (name, {k: dict(v) for k, v in m.writers.items()}))


# ------------------------------------------------------------------------------ the map

def mapwrites(names=('bomb_a', 'crash_a', 'rockets_c')):
    """Who writes the map's record list during a mission, and which records: re/notes/map.md
    said nothing writes them after the load; a hit on a barracks or a pillbox does."""
    for name in names:
        probe = machine_for(name)
        probe.run(until='inner')
        base = probe.o.r32(0x024628)
        length = probe.o.r16(0x0253C6)
        m = machine_for(name, Writes, ranges={'map': (base, length)})
        changed = {}
        m.run()
        for i in range(0, length, 2):
            before, after = probe.o.r16(base + i), m.o.r16(base + i)
            if before != after:
                changed[i * 4] = (hex(before), hex(after))
        print('%-10s writers %s' % (name, {k: dict(v) for k, v in m.writers.items()}))
        print('           records changed (world x: before, after): %s' % changed)


def main():
    parser = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    parser.add_argument('command', choices=['fall', 'pools', 'flash', 'couplings', 'mapwrites'])
    parser.add_argument('names', nargs='*')
    args = parser.parse_args()
    function = globals()[args.command]
    if args.names:
        function(args.names)
    else:
        function()
    return 0


if __name__ == '__main__':
    sys.exit(main())
