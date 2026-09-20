"""What a pass writes and what a tick reads of it (SPEC 10 point 2, deliverable 2).

`frame_update` is not a renderer: it runs game logic once per pass.  This tool runs the
headless original over scripts that cover the deck, the take-off, level flight, climbing and
diving, the guns, a bomb on an island, the loss of the aircraft with its restart and the game
over countdown, and prints one line per range that a pass wrote, with the routine that wrote
it and with whoever reads it inside logic_tick's tree.

    .venv/bin/python tools/pass_observe.py                 every script, the table
    .venv/bin/python tools/pass_observe.py --list
    .venv/bin/python tools/pass_observe.py --runs guns --out table.txt
    .venv/bin/python tools/pass_observe.py --control       the pass rate control below

The control runs one script at one, two and three VBlanks per pass over an entropy stream of
one constant value, so that the three runs see the same stream although a pass consumes
entropy, and compares their state at equal tick numbers: everything that differs must be a
range this table holds.

Every run here is minutes long, so this tool is not part of the suite; tests/test_passes.py
holds the same claims over a short script.
"""
import argparse
import collections
import os
import re
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)

import headless                                              # noqa: E402
import headless_dump as dump                                 # noqa: E402

DATA = (headless.DATA_START, headless.DATA_END - headless.DATA_START)

# The player's hands, VBlank by VBlank.  Fire taps carry the front end along; on the deck
# fire brings the aircraft up on the lift, stick right rolls it along the deck and a push
# forward lifts it off before the bow.
FRONT = [[30, ''], [3, 'F']] * 5
TAKE_OFF = [[40, ''], [3, 'F'], [60, ''], [460, 'R'], [400, 'RU']]

# Turning after the take-off dives the aircraft; a short push forward levels it out again,
# and it then flies at ten pixels a tick, which is how the island is reached.
TURN_LEFT = [[120, 'L'], [100, 'U']]
# A lift of the aircraft onto the deck, then rolling over the bow: one life each time.
ROLL_OFF = [[60, ''], [3, 'F'], [60, ''], [900, 'R']]

RUNS = {
    'deck':     (FRONT + [[2000, '']], 2000),
    'flight':   (FRONT + TAKE_OFF + [[1600, 'R']], 2400),
    'climb':    (FRONT + TAKE_OFF + [[500, 'RU'], [500, 'RD'], [500, 'LD'], [500, 'LU']], 2800),
    'guns':     (FRONT + TAKE_OFF + [[800, 'RF'], [800, 'RUF']], 2400),
    # The other weapon is dropped with a short click of the button (the manual, page 7), so
    # the bomb needs no key.  The island of map a lies about 3,000 pixels to the left of the
    # carrier; the aircraft turns after the take-off, flies there and drops a bomb every four
    # ticks.  One of them hits a barracks at tick 850 and its soldiers come out.
    'bomb':     (FRONT + TAKE_OFF + TURN_LEFT + [[1500, '']] +
                 [[3, 'F'], [13, '']] * 80 + [[600, '']], 4400),
    # Rolling over the bow instead of lifting off: the player is lost and restarted.
    'lost':     (FRONT + [[40, ''], [3, 'F'], [60, ''], [2400, 'R']], 2600),
    # The same four times over, which uses up every life and ends the mission.
    'gameover': (FRONT + ROLL_OFF * 5 + [[1500, '']], 7000),
}


def script(name, **more):
    raw, vblanks = RUNS[name]
    description = {'raw': raw + [[1, '']], 'stop': {'vblanks': vblanks}}
    description.update(more)
    return description


def place_name(text):
    """An allocation's place without its number, so that two runs can be compared."""
    return re.sub(r'^alloc \d+ ', '', text)


def observe(name, verbose=True, **more):
    """Two runs of one script: the first says which ranges a pass writes, the second watches
    reads of exactly those ranges.  Returns (machine of the second run, rows)."""
    started = time.time()
    first = headless.Headless(script(name, **more), summary=True, keep_report=False)
    first.run()
    place = first.places()
    written = [(address, length, writes) for address, length, writes, _ in first.summary.ranges()
               if 'F' in first.summary.phases_of(writes)]
    second = headless.Headless(script(name, **more),
                               read_ranges=[(a, n) for a, n, _ in written] or [DATA])
    second.run()
    readers = collections.defaultdict(set)
    for (phase, routine, label, offset, size) in second.reads.counts:
        readers[label].add((phase, routine))
    rows = {}
    for address, length, writes in written:
        label = first.names.datum(address) if address < headless.HEAP_BASE else '%06x' % address
        rows[place_name(place(address))] = {
            'address': address, 'length': length,
            'writers': {routine for (phase, routine) in writes if phase == 'F'},
            'other': {'%s %s' % (phase, routine) for (phase, routine) in writes if phase != 'F'},
            'readers': {routine for (phase, routine) in readers[label] if phase == 'T'},
            'pass_readers': {routine for (phase, routine) in readers[label] if phase == 'F'},
        }
    if verbose:
        print('%-9s %5d VBlanks, %5d passes, %4d ticks, %4d ranges written by a pass  (%.0f s)'
              % (name, second.vblanks, second.passes, second.ticks, len(rows), time.time() - started))
    return second, rows


def merge(all_rows):
    """One table over every script: a range keeps the union of its writers and readers."""
    table = {}
    for rows in all_rows:
        for place, row in rows.items():
            kept = table.setdefault(place, {'address': row['address'], 'length': row['length'],
                                            'writers': set(), 'readers': set(),
                                            'pass_readers': set(), 'other': set()})
            for key in ('writers', 'readers', 'pass_readers', 'other'):
                kept[key] |= row[key]
            kept['length'] = max(kept['length'], row['length'])
    return table


def format_table(table):
    lines = ['%-38s %-7s %4s  %-46s %s' % ('place', 'address', 'len', 'written in a pass by',
                                           'read in a tick by')]
    for place, row in sorted(table.items(), key=lambda kv: kv[1]['address']):
        lines.append('%-38s %06x  %4d  %-46s %s' % (
            place, row['address'], row['length'],
            ', '.join(sorted(row['writers']))[:46],
            ', '.join(sorted(row['readers'])) or '-'))
    return lines


def control(name='flight', ticks=220, constant=0x2A40, rates=(1, 2, 3), verbose=True):
    """The same script at one, two and three VBlanks per pass, over an entropy stream of one
    constant value, so that the three runs see the same stream although a pass consumes
    entropy.  Compares their state at the same tick number, byte by byte, and says for every
    byte that differs which phase wrote it.  Returns (rows, counts)."""
    first = headless.Headless(script(name, vblanks_per_pass=2), summary=True, keep_report=False)
    first.run()
    place, phases = first.places(), {}
    for address, length, written, _ in first.summary.ranges():
        for byte in range(address, address + length):
            phases[byte] = (first.summary.phases_of(written),
                            ', '.join(sorted({'%s %s' % (p, r) for p, r in written})))
    states = {}
    for rate in rates:
        run = headless.Headless(script(name, vblanks_per_pass=rate, entropy={'constant': constant},
                                       stop={'ticks': ticks}))
        run.run()
        states[rate] = (run.regions(), run.passes, run.vblanks)
        if verbose:
            print('  %d VBlanks per pass: %d passes, %d VBlanks at tick %d'
                  % (rate, run.passes, run.vblanks, run.ticks))
    base = states[rates[0]][0]
    differing = set()
    for rate in rates[1:]:
        ranges, only_a, only_b = dump.diff_states(base, states[rate][0])
        assert not only_a and not only_b, 'the runs hold different allocations'
        for address, length in ranges:
            differing.update(range(address, address + length))
    # A byte only counts as differing where the two states really differ; diff_states joins
    # ranges over gaps of up to eight equal bytes.
    real = set()
    for byte in sorted(differing):
        values = set()
        for rate in rates:
            regions = states[rate][0]
            region = max(a for a in regions if a <= byte)
            values.add(regions[region][byte - region])
        if len(values) > 1:
            real.add(byte)
    rows = collections.Counter()
    for byte in sorted(real):
        phase, writers = phases.get(byte, ('-', 'nobody in this run'))
        rows[(phase, place_name(place(byte)), writers)] += 1
    return rows, {rate: states[rate][1:] for rate in rates}, real, place, phases


def main():
    parser = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    parser.add_argument('--list', action='store_true')
    parser.add_argument('--runs', nargs='*', default=sorted(RUNS))
    parser.add_argument('--control', action='store_true')
    parser.add_argument('--out')
    args = parser.parse_args()
    if args.list:
        for name in sorted(RUNS):
            print(name)
        return 0

    if args.control:
        rows, counters, real, place, phases = control()
        print('\nbytes that differ between the three pass rates at the same tick, by the phase'
              '\nthey were written in (V a VBlank server, T a tick, F a pass, M the main program):')
        for (phase, where, writers), count in sorted(rows.items()):
            print('  [%-4s] %-40s %2d bytes  written by %s' % (phase, where, count, writers))
        print('%d bytes differ; %d of them were written by a pass, %d only by a VBlank server,'
              ' %d by neither'
              % (len(real),
                 sum(count for key, count in rows.items() if 'F' in key[0]),
                 sum(count for key, count in rows.items() if key[0] == 'V'),
                 sum(count for key, count in rows.items() if 'F' not in key[0] and key[0] != 'V')))
        return 0

    tables = []
    for name in args.runs:
        tables.append(observe(name)[1])
    table = merge(tables)
    lines = format_table(table)
    read = sum(1 for row in table.values() if row['readers'])
    print('\n%d ranges written by a pass, %d of them read inside a tick' % (len(table), read))
    if args.out:
        with open(args.out, 'w') as f:
            f.write('\n'.join(lines) + '\n')
        print('%s: %d lines' % (args.out, len(lines)))
    else:
        print('\n'.join(lines))
    return 0


if __name__ == '__main__':
    sys.exit(main())
