"""The object system: the tables the game logic keeps, and who walks them (SPEC 10 point 3).

For every table it resolves the base in a run, watches every read of it and every write with
the phase it was made in, and prints which routine touches which offsets inside a record, in
the tick, in the pass and in the mission setup.

    .venv/bin/python tools/object_observe.py                  every script, the inventory
    .venv/bin/python tools/object_observe.py --runs guns bomb
    .venv/bin/python tools/object_observe.py --controls       one input apart, per table

The scripts are the ones of tools/pass_observe.py (re/notes/passes.md); the findings are in
re/notes/objects.md.  Both commands take minutes and are not part of the suite.
"""
import argparse
import collections
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)

import headless                                              # noqa: E402
import headless_dump as dump                                 # noqa: E402
import pass_observe                                          # noqa: E402

# name, where the base is, record size, how many records.  A base of ('at', address) is a long
# in the DATA hunk that points at the table; ('is', address) is the table itself.  A count of
# ('byte', address) or ('word', address) is read from there when the mission has begun.
TABLES = [
    ('player_record',    ('at', 0x027DEC), 0x30, 1),
    ('object_records',   ('is', 0x024CAE), 0x2A, 15),
    ('object_extra',     ('is', 0x025594), 0x2A, 1),
    ('aircraft_records', ('is', 0x02522A), 0x34, 4),
    ('ship_records',     ('is', 0x025460), 0x1E, 5),
    ('airfield_records', ('is', 0x0252FA), 0x14, 4),
    ('ricochet',         ('at', 0x026EA4), 0x04, 20),
    ('splashes',         ('at', 0x026F30), 0x04, 20),
    ('smoke',            ('at', 0x026F58), 0x14, 40),
    ('balloons',         ('at', 0x026F66), 0x12, 20),
    ('soldier_records',  ('at', 0x025500), 0x08, ('word', 0x0253C4)),
    ('target_records_4', ('at', 0x0254F8), 0x10, ('byte', 0x025387)),
    ('target_records_3', ('at', 0x0254FC), 0x10, ('byte', 0x025386)),
    ('target_records_f', ('at', 0x025504), 0x0E, ('byte', 0x025385)),
]


def resolve(machine):
    """Every table with its base and length, as the mission left them."""
    out = []
    for name, where, size, count in TABLES:
        base = machine.o.r32(where[1]) if where[0] == 'at' else where[1]
        if isinstance(count, tuple):
            count = machine.o.r16(count[1]) if count[0] == 'word' else machine.o.read(count[1], 1)[0]
        out.append((name, base, size, count))
    return out


def observe(name, verbose=True):
    """One script: the tables it fills, every read of them and every write, by phase."""
    started = time.time()
    first = headless.Headless(pass_observe.script(name))
    first.run(until='inner')
    tables = resolve(first)
    ranges = [(base, size * count) for _, base, size, count in tables if base and count]
    machine = headless.Headless(pass_observe.script(name), summary=True, keep_report=False,
                                read_ranges=ranges)
    machine.run()
    if verbose:
        print('%-9s %5d VBlanks, %4d ticks  (%.0f s)'
              % (name, machine.vblanks, machine.ticks, time.time() - started))
    return machine, tables


def touches(machine, tables):
    """{table: {(phase, routine, 'read'|'write'): set of offsets inside a record}}."""
    found = collections.defaultdict(lambda: collections.defaultdict(set))
    by_base = {base: (name, size, count) for name, base, size, count in tables if base and count}
    starts = sorted(by_base)
    # The harness labels a watched range by its name in the DATA hunk and by its address in
    # the heap; the same rule maps the labels of the read log back to the tables.
    by_label = {}
    for base, entry in by_base.items():
        label = machine.names.datum(base) if base < headless.HEAP_BASE else '%06x' % base
        by_label[label] = (base, entry)
    for (phase, routine, label, offset, size), _ in machine.reads.counts.items():
        if label not in by_label:
            continue
        base, (name, record, count) = by_label[label]
        found[name][(phase, routine, 'read')].add(offset % record)
    for address, length, written, _ in machine.summary.ranges():
        for base in starts:
            name, record, count = by_base[base]
            if base <= address < base + record * count:
                for phase, routine in written:
                    for byte in range(address, min(address + length, base + record * count)):
                        found[name][(phase, routine, 'write')].add((byte - base) % record)
                break
    return found


def report(name, tables, found):
    print()
    print('== %s ==' % name)
    for table, base, size, count in tables:
        marks = found.get(table, {})
        if not base or not count:
            print('  %-18s not allocated in this run' % table)
            continue
        print('  %-18s %06x  %d records of 0x%x bytes%s'
              % (table, base, count, size, '' if marks else '   (nobody touched it)'))
        for (phase, routine, what), offsets in sorted(marks.items()):
            spread = ' '.join('%02x' % o for o in sorted(offsets)[:14])
            print('      %s %-5s %-22s %s%s' % (phase, what, routine, spread,
                                                ' ...' if len(offsets) > 14 else ''))


def controls(pairs, verbose=True):
    """Pairs of runs one scripted input apart: which tables their states differ in."""
    out = []
    for label, left, right in pairs:
        states = []
        for description in (left, right):
            machine = headless.Headless(description)
            machine.run()
            states.append((machine.regions(), resolve(machine)))
        ranges, only_a, only_b = dump.diff_states(states[0][0], states[1][0])
        hit = collections.Counter()
        for address, length in ranges:
            where = 'elsewhere'
            for table, base, size, count in states[0][1]:
                if base and count and base <= address < base + size * count:
                    where = table
                    break
            hit[where] += length
        out.append((label, hit))
        if verbose:
            print('%-28s %s' % (label, ', '.join('%s %d bytes' % item for item in hit.most_common())))
    return out


FRONT = [[30, ''], [3, 'F']] * 5
TAKE_OFF = [[40, ''], [3, 'F'], [60, ''], [460, 'R'], [400, 'RU']]


def pair(label, tail_a, tail_b, ticks):
    """Two runs of the same length that differ in one scripted input."""
    return (label,
            {'raw': FRONT + TAKE_OFF + tail_a, 'stop': {'ticks': ticks}},
            {'raw': FRONT + TAKE_OFF + tail_b, 'stop': {'ticks': ticks}})


PAIRS = [
    pair('guns held or not', [[600, 'RF']], [[600, 'R']], 380),
    pair('a bomb dropped or not', pass_observe.TURN_LEFT + [[1500, '']] + [[3, 'F'], [13, '']] * 80,
         pass_observe.TURN_LEFT + [[1500, '']] + [[16, '']] * 80, 900),
    pair('climbing or level', [[600, 'RU']], [[600, 'R']], 380),
]


# ------------------------------------------------------------------ the player's record

PLAYER_POINTER = 0x027DEC
PLAYER_SIZE = 0x30
PLAYER_GLOBALS = {
    'pitch_angle': 0x025AA2, 'pitch_target': 0x025402, 'pitch_delta': 0x025408,
    'attitude_index': 0x02540E, 'airspeed': 0x025414, 'g_025aaa': 0x025AAA,
    'g_025f16': 0x025F16, 'g_027dea': 0x027DEA, 'g_02508a': 0x02508A,
    'g_025094': 0x025094, 'g_025096': 0x025096, 'g_02535c': 0x02535C,
}


def player_trace(name, ticks=None):
    """The player's record and the globals around it, once per tick, with the input byte.

    Stepping by tick switches the run description's own stop off, so the VBlank limit of the
    script is checked here."""
    description = pass_observe.script(name)
    limit = description['stop'].get('vblanks', 1 << 60)
    machine = headless.Headless(description)
    rows = []
    while machine.vblanks < limit:
        why = machine.run(until='tick')
        base = machine.o.r32(PLAYER_POINTER)
        row = {'tick': machine.ticks, 'pass': machine.passes, 'vblank': machine.vblanks,
               'input': machine.o.r16(0x026D42) & 0xFF,
               'record': [machine.o.r16(base + 2 * i, signed=True) for i in range(PLAYER_SIZE // 2)]}
        row.update({key: machine.o.r16(at, signed=True) for key, at in PLAYER_GLOBALS.items()})
        rows.append(row)
        if why != 'tick' or (ticks and machine.ticks >= ticks):
            break
    return machine, rows


def player_report(name, rows):
    """Which word of the record moved when, and what the two speeds predict."""
    print()
    print('== %s: %d ticks ==' % (name, len(rows)))
    changed = collections.Counter()
    for before, after in zip(rows, rows[1:]):
        for i, (a, b) in enumerate(zip(before['record'], after['record'])):
            if a != b:
                changed[i * 2] += 1
    print('  offsets that ever change: %s' % ' '.join(
        '+0x%02x x%d' % (offset, count) for offset, count in sorted(changed.items())))
    ok = collections.Counter()
    for before, after in zip(rows, rows[1:]):
        want_x = before['record'][1] + before['record'][0x16 // 2] * before['record'][0x14 // 2]
        ok['x moves by the horizontal speed times the facing'] += (
            (want_x & 0xFFFF) == (after['record'][1] & 0xFFFF))
        ok['y moves by the vertical speed'] += (
            ((before['record'][0] + before['record'][0x18 // 2]) & 0xFFFF)
            == (after['record'][0] & 0xFFFF))
        ok['ticks compared'] += 1
    for what, count in sorted(ok.items()):
        print('  %-52s %d' % (what, count))
    for key in sorted(PLAYER_GLOBALS):
        values = [row[key] for row in rows]
        moves = sum(1 for a, b in zip(values, values[1:]) if a != b)
        print('  %-16s %6d .. %-6d  changes %d' % (key, min(values), max(values), moves))


# ------------------------------------------------------------------ the draw order

def draw_order(name, want=3):
    """The sequence of draws of one pass, by the routine that made each one.  The map draws
    and the object draws are told apart by their caller, which is what the scene list of
    re/notes/drawing.md names."""
    machine = headless.Headless(pass_observe.script(name),
                                observe=['draw_world_shape', 'shape_draw', 'shape_blit',
                                         'shape_draw_xor', 'rect_fill', 'line_draw'])
    machine.run()
    passes = collections.defaultdict(list)
    for record in machine.observed:
        passes[record['pass']].append((machine.names.routine(record['caller']), record['routine']))
    busiest = sorted(passes, key=lambda p: -len(passes[p]))[:want]
    for number in sorted(busiest):
        print('  pass %d: %d drawing calls' % (number, len(passes[number])))
        run = []
        for caller, routine in passes[number]:
            if run and run[-1][0] == caller and run[-1][1] == routine:
                run[-1][2] += 1
            else:
                run.append([caller, routine, 1])
        for caller, routine, count in run:
            print('      %-22s %-16s x%d' % (caller, routine, count))
    return machine


def main():
    parser = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    parser.add_argument('--runs', nargs='*', default=sorted(pass_observe.RUNS))
    parser.add_argument('--controls', action='store_true')
    parser.add_argument('--player', action='store_true')
    parser.add_argument('--draw-order', action='store_true')
    args = parser.parse_args()
    if args.controls:
        controls(PAIRS)
        return 0
    if args.draw_order:
        for name in args.runs:
            print('== %s ==' % name)
            draw_order(name)
        return 0
    if args.player:
        for name in args.runs:
            machine, rows = player_trace(name)
            player_report(name, rows)
        return 0
    for name in args.runs:
        machine, tables = observe(name)
        report(name, tables, touches(machine, tables))
    return 0


if __name__ == '__main__':
    sys.exit(main())
