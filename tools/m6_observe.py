"""The enemy aircraft, the ships and the carrier's defence, answered by observation on the
headless original (re/notes/enemy.md).

    .venv/bin/python tools/m6_observe.py maps            the fifteen maps' enemy content at step S
    .venv/bin/python tools/m6_observe.py fields NAME...  every write of aircraft_records by field,
                                                         with its writers, phases and values
    .venv/bin/python tools/m6_observe.py records NAME... the same for the ship, airfield and gun
                                                         records and the wrecks' words
    .venv/bin/python tools/m6_observe.py states NAME...  every change of an aircraft's state and
                                                         mode words, with the tick and the writer
    .venv/bin/python tools/m6_observe.py events NAME...  the kill counter, the score, the carrier's
                                                         hits, the flash and a ship's sinking, with
                                                         their writers

NAME is a script of tools/m6_scripts.py.  Each command prints what it saw; the note quotes
the results.
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
import map_decode                                            # noqa: E402
import reach_observe                                         # noqa: E402

AIRCRAFT, AIRCRAFT_SIZE = 0x02522A, 0x34
SHIPS, SHIP_SIZE = 0x025460, 0x1E
SHIP_NAMES = ('destroyer', 'battleship', 'cruiseship', 'japcarrier', 'carrier')
AIRFIELDS, AIRFIELD_SIZE = 0x0252FA, 0x14
BLOCKS = 0x025096                    # the five ships' blocks of deck planes, 0x40 bytes each
BLOCK_OF = {'destroyer': 0, 'carrier': 1, 'battleship': 2, 'cruiseship': 3, 'japcarrier': 4}
WRECKS = 0x0251D8                    # a count and forty words
KILLS = 0x02537F
FIGHTERS = 0x0251D6
ISLAND_COUNT = 0x025384


def s16(v):
    return v - 0x10000 if v & 0x8000 else v


# ------------------------------------------------------------------------------- maps

def setup(letter):
    """The headless original at step S of a map loaded under its own number."""
    rank, mission = reach_observe.setup_runs()[letter]
    m = headless.Headless({'raw': reach_observe.rank_script(rank), 'stop': {'vblanks': 2000}})
    m.stop_at(0x01009E, lambda: m.o.write(reach_observe.MISSION_NUMBER, bytes([0, mission])))
    m.run(until='inner')
    return m, rank, mission


def map_content(letter):
    """What a map carries, read from the original's state at step S."""
    m, rank, mission = setup(letter)
    o = m.o
    out = {'map': letter, 'rank': rank, 'mission': mission,
           'player_x': s16(o.r16(0x025392)), 'islands': o.read(ISLAND_COUNT, 1)[0],
           'ships': [], 'airfields': []}
    for i, name in enumerate(SHIP_NAMES):
        a = SHIPS + SHIP_SIZE * i
        if not o.r16(a + 4):
            continue
        block = BLOCKS + 0x40 * BLOCK_OF[name]
        planes = s16(o.r16(block))
        out['ships'].append({
            'ship': name, 'x': (s16(o.r16(a)) * 4, s16(o.r16(a + 2)) * 4),
            'guns': s16(o.r16(a + 0x0A)), 'hits': s16(o.r16(a + 0x0C)),
            'deck': s16(o.r16(a + 0x0E)), 'w12': s16(o.r16(a + 0x12)),
            'w16': s16(o.r16(a + 0x16)),
            'planes': planes, 'most_up': s16(o.r16(block + 2)),
            'range': (s16(o.r16(block + 4)), s16(o.r16(block + 6))),
            'gun_x': [s16(o.r16(o.r32(a + 6) + 0x0E * k + 4))
                      for k in range(s16(o.r16(a + 0x0A)))] if o.r32(a + 6) else []})
    for i in range(4):
        a = AIRFIELDS + AIRFIELD_SIZE * i
        if not o.r16(a + 2):
            continue
        out['airfields'].append({'x': (s16(o.r16(a)), s16(o.r16(a + 2))),
                                 'most_up': s16(o.r16(a + 4)), 'parked': s16(o.r16(a + 6)),
                                 'way': s16(o.r16(a + 0x0E))})
    return out


def maps(letters=None):
    rows = []
    for letter in letters or reach_observe.LETTERS:
        rows.append(map_content(letter))
    for r in rows:
        ships = '; '.join('%s x %d-%d, %d guns, %d hits, %d planes (up to %d in the air when '
                          'the player is within x %d-%d)' % (
                              sh['ship'], sh['x'][0], sh['x'][1], sh['guns'], sh['hits'],
                              sh['planes'], sh['most_up'], sh['range'][0], sh['range'][1])
                          for sh in r['ships'] if sh['ship'] != 'carrier')
        fields = '; '.join('x %d-%d, %d parked, up to %d in the air, taking off %s' % (
            f['x'][0], f['x'][1], f['parked'], f['most_up'],
            'west' if f['way'] < 0 else 'east') for f in r['airfields'])
        carrier = [sh for sh in r['ships'] if sh['ship'] == 'carrier'][0]
        print('%s  rank %d mission %d  player x %d  islands %d  carrier x %d-%d, %d hits | '
              'ships: %s | airfields: %s' % (
                  r['map'], r['rank'], r['mission'], r['player_x'], r['islands'],
                  carrier['x'][0], carrier['x'][1], carrier['hits'], ships or 'none',
                  fields or 'none'))
    return rows


# ------------------------------------------------------------------------ write hooks

class Writes(headless.Headless):
    """The original with a write hook over chosen ranges: per address and value the writing
    routine, the phase and the step."""

    def __init__(self, run, ranges, **options):
        super().__init__(run, **options)
        self.log = []                  # (address, size, value, routine, phase, tick, pass)
        for begin, length in ranges:
            self.uc.hook_add(UC_HOOK_MEM_WRITE, self._write, begin=begin, end=begin + length - 1)

    def _write(self, uc, access, address, size, value, user):
        pc = uc.reg_read(UC_M68K_REG_PC)
        self.log.append((address, size, value & ((1 << (8 * size)) - 1),
                         self.names.routine(pc), self.phase(), self.ticks, self.passes))


def machine_for(name, cls=headless.Headless, **options):
    import m6_scripts
    m = cls(m6_scripts.script(name), **options)
    m6_scripts.install_pokes(m, m6_scripts.POKES.get(name))
    return m


def run_logged(name, ranges):
    import m6_scripts
    m = machine_for(name, Writes, ranges=ranges)
    limit = m6_scripts.script(name)['stop']['vblanks']
    while m.run(until='tick') == 'tick' and m.vblanks < limit:
        pass
    return m


FIELD_NAMES = {
    0x00: 'state', 0x02: 'mode', 0x04: 'relation', 0x06: 'hit', 0x08: 'health',
    0x0A: 'burst', 0x0C: 'order', 0x0E: 'w0e', 0x10: 'timer', 0x12: 'firing', 0x14: 'facing',
    0x16: 'attitude', 0x18: 'turn_in', 0x1A: 'turns', 0x1C: 'speed', 0x1E: 'want_speed',
    0x20: 'x', 0x22: 'climb', 0x24: 'want_y', 0x26: 'y', 0x28: 'distance', 0x2A: 'w2a',
    0x2C: 'flash', 0x2E: 'draw_x', 0x30: 'frame', 0x32: 'step_count'}


def fields(names):
    """Every write of aircraft_records, by field: the writers with their phases and counts,
    and the values written (the most frequent)."""
    writers = collections.defaultdict(collections.Counter)
    values = collections.defaultdict(collections.Counter)
    for name in names:
        m = run_logged(name, [(AIRCRAFT, 4 * AIRCRAFT_SIZE)])
        for address, size, value, routine, phase, tick, npass in m.log:
            offset = (address - AIRCRAFT) % AIRCRAFT_SIZE
            if size == 1:
                offset &= ~1
                value <<= 8 * (1 - (address & 1))
            writers[offset][(routine, phase)] += 1
            values[offset][s16(value) if size <= 2 else value] += 1
        print('%s: %d ticks, %d writes' % (name, m.ticks, len(m.log)))
    for offset in sorted(writers):
        print('+0x%02X %-12s writers %s' % (offset, FIELD_NAMES.get(offset, ''),
                                          ', '.join('%s (%s) %d' % (r, p, n) for (r, p), n in
                                                    writers[offset].most_common())))
        print('       values %s' % dict(values[offset].most_common(12)))


def records(names):
    """The same for the ship records, the airfield records, the gun lists, the ship blocks
    and the wrecks' words."""
    for name in names:
        probe = machine_for(name)
        probe.run(until='inner')
        ranges = [(SHIPS, 5 * SHIP_SIZE), (AIRFIELDS, 4 * AIRFIELD_SIZE), (BLOCKS, 0x140),
                  (WRECKS, 0x52)]
        guns = {}
        for i, sname in enumerate(SHIP_NAMES[:4]):
            a = SHIPS + SHIP_SIZE * i
            if probe.o.r16(a + 4) and probe.o.r32(a + 6):
                guns[sname] = (probe.o.r32(a + 6), 0x0E * probe.o.r16(a + 0x0A))
                ranges.append(guns[sname])
        m = run_logged(name, ranges)
        table = collections.defaultdict(collections.Counter)
        for address, size, value, routine, phase, tick, npass in m.log:
            if SHIPS <= address < SHIPS + 5 * SHIP_SIZE:
                where = '%s +0x%02X' % (SHIP_NAMES[(address - SHIPS) // SHIP_SIZE],
                                        (address - SHIPS) % SHIP_SIZE)
            elif AIRFIELDS <= address < AIRFIELDS + 4 * AIRFIELD_SIZE:
                where = 'airfield %d +0x%02X' % ((address - AIRFIELDS) // AIRFIELD_SIZE,
                                                 (address - AIRFIELDS) % AIRFIELD_SIZE)
            elif BLOCKS <= address < BLOCKS + 0x140:
                where = 'block %d +0x%02X' % ((address - BLOCKS) // 0x40, (address - BLOCKS) % 0x40)
            elif WRECKS <= address < WRECKS + 0x52:
                where = 'wrecks +0x%02X' % (address - WRECKS)
            else:
                sname = [k for k, (b, n) in guns.items() if b <= address < b + n][0]
                b = guns[sname][0]
                where = '%s gun %d +0x%02X' % (sname, (address - b) // 0x0E, (address - b) % 0x0E)
            table[where][(routine, phase)] += 1
        print('%s: %d ticks' % (name, m.ticks))
        for where in sorted(table):
            print('   %-22s %s' % (where, ', '.join('%s (%s) %d' % (r, p, n)
                                                    for (r, p), n in table[where].most_common())))


def states(names):
    """Every change of an aircraft's state word (+0x00) and mode word (+0x02), with the tick,
    the writer and the old and new values."""
    for name in names:
        m = run_logged(name, [(AIRCRAFT + AIRCRAFT_SIZE * i, 4) for i in range(4)])
        last = {}
        print('%s: %d ticks' % (name, m.ticks))
        for address, size, value, routine, phase, tick, npass in m.log:
            i, offset = (address - AIRCRAFT) // AIRCRAFT_SIZE, (address - AIRCRAFT) % AIRCRAFT_SIZE
            key = (i, offset)
            if size == 1:
                continue
            if last.get(key) != value:
                print('   tick %5d  aircraft %d %-5s %4x -> %4x  %s (%s)' % (
                    tick, i, 'state' if offset == 0 else 'mode', last.get(key, 0), value,
                    routine, phase))
                last[key] = value


def events(names):
    """The kill counter, the score, the carrier's hits, the sky's flash, the fighters in the
    air, the wrecks' count, and every ship's hits and sinking count, with their writers."""
    watched = {KILLS: 'kills', 0x02534C: 'score', 0x025416: 'flash_count',
               0x025418: 'flash_colour', FIGHTERS: 'fighters', WRECKS: 'wrecks',
               0x025094: 'countdown'}
    for i, sname in enumerate(SHIP_NAMES):
        watched[SHIPS + SHIP_SIZE * i + 0x04] = sname + ' afloat'
        watched[SHIPS + SHIP_SIZE * i + 0x0C] = sname + ' hits'
        watched[SHIPS + SHIP_SIZE * i + 0x18] = sname + ' sinking'
    for name in names:
        m = run_logged(name, [(a, 4 if n == 'score' else 2) for a, n in watched.items()])
        seen = collections.defaultdict(collections.Counter)
        firsts = {}
        for address, size, value, routine, phase, tick, npass in m.log:
            base = max(a for a in watched if a <= address)
            label = watched[base]
            seen[label][(routine, phase)] += 1
            if label != 'countdown':
                firsts.setdefault(label, []).append((tick, value))
        print('%s: %d ticks' % (name, m.ticks))
        for label in sorted(seen):
            steps = firsts.get(label, [])
            print('   %-18s %s   first %s' % (label, ', '.join('%s (%s) %d' % (r, p, n) for (r, p), n
                                                            in seen[label].most_common()),
                                           steps[:6]))


def main():
    parser = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    parser.add_argument('command', choices=['maps', 'fields', 'records', 'states', 'events'])
    parser.add_argument('names', nargs='*')
    args = parser.parse_args()
    globals()[args.command](args.names or None)
    return 0


if __name__ == '__main__':
    sys.exit(main())
