"""What a pass writes and what a tick reads of it (SPEC 10 point 2, deliverable 2).

`frame_update` is not a renderer: it runs game logic once per pass.  This tool runs the
headless original over scripts that cover the deck, the take-off, level flight, climbing and
diving, the guns, a bomb on an island, the loss of the aircraft with its restart and the game
over countdown, and prints one line per range that a pass wrote, with the routine that wrote
it and with whoever reads it inside logic_tick's tree.

    .venv/bin/python tools/pass_observe.py                 every script, the table
    .venv/bin/python tools/pass_observe.py --list
    .venv/bin/python tools/pass_observe.py --runs guns --out table.txt
    .venv/bin/python tools/pass_observe.py --control --runs lost --ticks 600

The control runs a script at one, two and three VBlanks per pass over an entropy stream of one
constant value, so that the runs see the same stream although a pass consumes entropy, checks
that they fed the tick the same input bytes, and compares their state at equal tick numbers:
every byte that differs must have been written by a pass, by a VBlank server, or inside a tick
by a routine that reads a range a pass wrote or that such a reader calls.  Whatever is left
over is printed as a finding.

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

import csv                                                    # noqa: E402

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


def called_from(names):
    """Every routine the given ones reach, through the `calls` column of re/functions.csv.

    A tick routine that writes a byte need not be the one that read the coupled range: the
    reader calls it.  The closure makes that check mechanical instead of a story."""
    calls = {}
    with open(os.path.join(ROOT, 're', 'functions.csv'), newline='') as handle:
        for row in csv.DictReader(handle):
            calls[row['name']] = row['calls'].split()
    seen, todo = set(names), list(names)
    while todo:
        for callee in calls.get(todo.pop(), ()):
            if callee not in seen:
                seen.add(callee)
                todo.append(callee)
    return seen


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
    """The same script at several VBlanks per pass, over an entropy stream of one constant
    value so that the runs see the same stream although a pass consumes entropy.

    The comparison is only worth something when the three runs feed the tick the same input
    bytes, so that is checked and returned.  The writer of every byte comes from the compared
    runs themselves, and who reads a pass-written range inside a tick comes from one more run
    of the same script with a read hook over exactly those ranges.  Every byte that differs at
    the same tick number is then put in one of four classes, and whatever falls in the last
    one is a finding."""
    runs = {}
    for rate in rates:
        run = headless.Headless(script(name, vblanks_per_pass=rate, entropy={'constant': constant},
                                       stop={'ticks': ticks}), summary=True, keep_report=False)
        run.run()
        runs[rate] = run
        if verbose:
            print('  %d VBlanks per pass: %d passes, %d VBlanks at tick %d'
                  % (rate, run.passes, run.vblanks, run.ticks))

    # The tick's own input, as the schedule recorded it: equal, or the comparison means nothing.
    inputs = {rate: [entry[1] for entry in runs[rate].schedule if entry[0] == 'T'] for rate in rates}
    same_inputs = all(inputs[rate] == inputs[rates[0]] for rate in rates)

    # Who wrote which byte, from the compared runs and from nothing else.
    phases = {}
    for rate in rates:
        for address, length, written, _ in runs[rate].summary.ranges():
            for byte in range(address, address + length):
                phases.setdefault(byte, set()).update(written)

    # Who reads, inside a tick, what a pass wrote: one more run of the same script.
    pass_written = sorted(byte for byte, marks in phases.items() if any(p == 'F' for p, _ in marks))
    ranges, start = [], None
    for byte in pass_written:
        if start is None:
            start = previous = byte
        elif byte != previous + 1:
            ranges.append((start, previous - start + 1))
            start = byte
        previous = byte
    if start is not None:
        ranges.append((start, previous - start + 1))
    middle = rates[len(rates) // 2]
    reader = headless.Headless(script(name, vblanks_per_pass=middle, entropy={'constant': constant},
                                      stop={'ticks': ticks}), read_ranges=ranges or [DATA])
    reader.run()
    coupled_readers = {routine for (phase, routine, _, _, _) in reader.reads.counts if phase == 'T'}
    below_readers = called_from(coupled_readers)
    # A VBlank can happen inside a tick -- the restart spins on WaitTOF there -- so what a
    # server writes is recognised by the routine, not by the phase it was tagged with.
    servers = {reader.names.routine(code) for _, _, _, code in reader.servers}
    server_routines = called_from(servers)

    # Every byte that really differs at the same tick number.
    base = runs[rates[0]].regions()
    candidates = set()
    for rate in rates[1:]:
        spans, only_a, only_b = dump.diff_states(base, runs[rate].regions())
        assert not only_a and not only_b, 'the runs hold different allocations'
        for address, length in spans:
            candidates.update(range(address, address + length))
    real = set()
    for byte in sorted(candidates):
        values = set()
        for rate in rates:
            regions = runs[rate].regions()
            region = max(a for a in regions if a <= byte)
            values.add(regions[region][byte - region])
        if len(values) > 1:
            real.add(byte)

    place = runs[rates[0]].places()
    rows, leftover = collections.Counter(), []
    for byte in sorted(real):
        marks = phases.get(byte, set())
        kinds = {p for p, _ in marks}
        writers = ', '.join(sorted('%s %s' % (p, r) for p, r in marks)) or 'nobody in these runs'
        outside_setup = {r for p, r in marks if p != 'M'}
        if 'F' in kinds:
            verdict = 'written by a pass'
        elif outside_setup and outside_setup <= server_routines:
            verdict = 'written only by a VBlank server'
        elif 'T' in kinds and {r for p, r in marks if p == 'T'} & coupled_readers:
            verdict = 'written in a tick by a reader of a coupled range'
        elif 'T' in kinds and {r for p, r in marks if p == 'T'} & below_readers:
            verdict = 'written in a tick below a reader of a coupled range'
        else:
            verdict = 'NOT EXPLAINED'
            leftover.append((byte, place(byte), writers))
        rows[(verdict, place_name(place(byte)), writers)] += 1
    return {'runs': runs, 'rows': rows, 'differing': real, 'place': place, 'phases': phases,
            'inputs_match': same_inputs, 'leftover': leftover, 'reader': reader,
            'coupled_readers': coupled_readers, 'below_readers': below_readers,
            'counters': {rate: (runs[rate].passes, runs[rate].vblanks) for rate in rates}}


def report_control(name, ticks, result):
    print('\ntick input bytes identical across the rates:', result['inputs_match'])
    print('bytes that differ between the pass rates at tick %d of %s, by who wrote them:'
          % (ticks, name))
    for (verdict, where, writers), count in sorted(result['rows'].items()):
        print('  %-44s %-38s %2d bytes  by %s' % (verdict, where, count, writers))
    totals = collections.Counter()
    for (verdict, _, _), count in result['rows'].items():
        totals[verdict] += count
    print('%d bytes differ: %s' % (len(result['differing']),
                                   ', '.join('%s %d' % (v, n) for v, n in sorted(totals.items()))))
    if result['leftover']:
        print('LEFT OVER, not explained by the table:')
        for byte, where, writers in result['leftover']:
            print('  %06x %-40s by %s' % (byte, where, writers))
    else:
        print('nothing is left over: every differing byte is explained.')


def main():
    parser = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    parser.add_argument('--list', action='store_true')
    parser.add_argument('--runs', nargs='*', default=sorted(RUNS))
    parser.add_argument('--control', action='store_true')
    parser.add_argument('--ticks', type=int, help='how far the control runs; a default per script')
    parser.add_argument('--constant', type=lambda v: int(v, 0), default=0x2A40,
                        help='the one entropy value the control runs on')
    parser.add_argument('--out')
    args = parser.parse_args()
    if args.list:
        for name in sorted(RUNS):
            print(name)
        return 0

    if args.control:
        for name in args.runs:
            ticks = args.ticks or {'flight': 220}.get(name, 400)
            print('== %s, %d ticks ==' % (name, ticks))
            report_control(name, ticks, control(name, ticks=ticks, constant=args.constant))
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
