"""What the game really hands its floating point (SPEC 10 point 13, deliverable 4).

Runs the headless original with observers on the three routines that compute with mathffp
and on all nine glue entries, and writes what it saw:

    .venv/bin/python tools/ffp_observe.py            every run, the default
    .venv/bin/python tools/ffp_observe.py --list     the run names

    tests/ffp_observed.json   the operands, so that the differential test uses the real ones
    re/notes/ffp.md           the call-site table this prints

An observer only reads, so a run with observers takes the same steps as one without
(tests/test_frontend.py::test_an_observer_does_not_change_a_run and its twin for the
return side).
"""
import argparse
import collections
import json
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)

import headless                                              # noqa: E402

OUT = os.path.join(ROOT, 'tests', 'ffp_observed.json')

GLUE = ['ffp_add', 'ffp_cmp', 'ffp_neg', 'ffp_tst', 'ffp_fix',
        'ffp_sub', 'ffp_div', 'ffp_flt', 'ffp_mul']
ROUTINES = ['sub_01bdfa', 'sub_01d796', 'sub_021a40']
# The whole formatter tree above 0x021A40: it is entered only for a conversion letter of
# 'e' or above (0x02187A, `sub.w #$65,d0`), so what reaches sprintf decides whether the
# game ever computes with floating point outside the two tick routines.
FORMATTERS = ['sprintf', 'sub_0216b2']
OPERATION = {'ffp_add': 'add', 'ffp_sub': 'sub', 'ffp_mul': 'mul', 'ffp_div': 'div',
             'ffp_cmp': 'cmp', 'ffp_tst': 'tst', 'ffp_neg': 'neg', 'ffp_fix': 'fix',
             'ffp_flt': 'flt'}

# The globals the two tick routines read and write, and the record they work on, which they
# reach through the pointer at 0x027DEC.  Addresses are the load layout of SPEC 3.2.
PLAYER_POINTER = 0x027DEC
AIRCRAFT = 0x02522A                  # four enemy-aircraft records of 0x34 bytes
WATCH = {
    'player':  ('*', PLAYER_POINTER, 0x30),
    'aircraft': (AIRCRAFT, 4 * 0x34),    # the record 0x01D796 is handed is one of these
    'g_025402': (0x025402, 0x18),        # 0x025402 .. 0x025419
    'g_025aa2': (0x025AA2, 0x0C),        # 0x025AA2 .. 0x025AAD
    'g_027dea': (0x027DEA, 0x06),
    'g_025f16': (0x025F16, 0x02),
    'g_026d43': (0x026D43, 0x01),
}

FRONT = [[30, ''], [3, 'F']] * 5
TAKE_OFF = [[40, ''], [3, 'F'], [60, ''], [460, 'R'], [400, 'RU']]

RUNS = {
    # The take-off and flight of re/notes/headless.md, level after the climb.
    'flight':   FRONT + TAKE_OFF + [[1200, 'R']],
    # Climbing, diving and turning: forward, back, and the other way round.
    'climb':    FRONT + TAKE_OFF + [[300, 'RU'], [300, 'RD'], [300, 'LD'], [300, 'LU']],
    # With the guns firing throughout.
    'guns':     FRONT + TAKE_OFF + [[600, 'RF'], [600, 'RUF']],
    # Rolling over the bow instead, which resets the player.
    'roll_off': FRONT + [[40, ''], [3, 'F'], [60, ''], [1500, 'R']],
    # The front end alone, and then a mission left alone on the deck.
    'deck':     FRONT + [[1500, '']],
    # Long enough, and with the guns silent, for an enemy aircraft to be launched: the
    # countdown at 0x025094 only runs down while the fire button is not held (0x01BC02),
    # and it stands at about 1350 ticks when a mission begins.  That is the only way into
    # the second routine, which the update of an enemy aircraft calls.
    'zeros':    FRONT + [[40, ''], [3, 'F'], [60, ''], [460, 'R'],
                         [3000, 'RU'], [3000, 'R'], [3000, 'RD'], [3000, 'R']],
}
STOP = {'flight': 2600, 'climb': 2400, 'guns': 2400, 'roll_off': 1700, 'deck': 1700,
        'zeros': 13000}


def observe(name, verbose=True):
    description = {'raw': RUNS[name] + [[1, '']], 'stop': {'vblanks': STOP[name]}}
    started = time.time()
    machine = headless.Headless(description, observe=GLUE + ROUTINES + FORMATTERS,
                                observe_returns=True, watch=WATCH, watch_for=ROUTINES)
    machine.run()
    if verbose:
        print('%-9s %5d VBlanks, %4d ticks, %5d observations  (%.1f s)'
              % (name, machine.vblanks, machine.ticks, len(machine.observed),
                 time.time() - started))
    return machine


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--list', action='store_true')
    parser.add_argument('--runs', nargs='*', default=sorted(RUNS))
    parser.add_argument('--out', default=OUT)
    parser.add_argument('--keep', type=int, default=300,
                        help='entries of each routine written out, spread over the runs')
    args = parser.parse_args()
    if args.list:
        for name in sorted(RUNS):
            print(name)
        return 0

    operands = collections.defaultdict(list)
    seen = collections.defaultdict(set)
    sites = collections.defaultdict(lambda: collections.Counter())
    ranges = collections.defaultdict(list)
    entries = collections.defaultdict(list)
    formats = collections.Counter()

    for name in args.runs:
        machine = observe(name)
        current = None
        for record in machine.observed:
            routine = record['routine']
            if routine in OPERATION:
                operation = OPERATION[routine]
                site = record['caller'] - 4          # every call site is `jsr d16(pc)`
                sites[operation][site] += 1
                pair = (record['d'][0], record['d'][1])
                ranges[(operation, site)].append(pair)
                if pair not in seen[operation]:
                    seen[operation].add(pair)
                    operands[operation].append(list(pair))
                if current is not None:
                    back = record.get('return', {})
                    current['calls'].append([site, operation, pair[0], pair[1],
                                             back.get('d', [None])[0],
                                             back.get('d', [None, None])[1],
                                             back.get('ccr')])
            elif routine in FORMATTERS:
                if routine == 'sprintf':
                    formats[machine.o.read(record['args'][1], 40).split(b'\0')[0]] += 1
                else:
                    formats[b'(the formatter itself)'] += 1
            else:
                current = {
                    'run': name, 'tick': record['tick'], 'pass': record['pass'],
                    'arg': record['args'][0], 'in': record.get('memory', {}),
                    'out': record.get('return', {}).get('memory', {}),
                    'calls': [],
                }
                entries[routine].append(current)

    print()
    print('%-4s %-8s %7s  %s' % ('op', 'site', 'calls', 'operands D0 / D1'))
    for operation in ('add', 'sub', 'mul', 'div', 'cmp', 'tst', 'neg', 'fix', 'flt'):
        for site in sorted(sites[operation]):
            pairs = ranges[(operation, site)]
            print('%-4s %06X   %7d  D0 %08X..%08X  D1 %08X..%08X  (%d distinct)'
                  % (operation, site, sites[operation][site],
                     min(p[0] for p in pairs), max(p[0] for p in pairs),
                     min(p[1] for p in pairs), max(p[1] for p in pairs),
                     len(set(pairs))))
        if not sites[operation]:
            print('%-4s %-8s %7d  not reached by any run' % (operation, '-', 0))
    print()
    for routine in ROUTINES:
        print('%s: %d entries' % (routine, len(entries[routine])))
    print()
    print('format strings that reached sprintf:')
    for text, count in sorted(formats.items()):
        print('  %-24r %d' % (text.decode('latin1'), count))

    # Every entry is compared; what goes into the file is an even spread of them, so that
    # the test carries several hundred without carrying megabytes.
    kept = {}
    for routine in ROUTINES:
        all_of_them = entries[routine]
        stride = max(1, len(all_of_them) // args.keep + 1)
        kept[routine] = all_of_them[::stride][:args.keep]

    with open(args.out, 'w', encoding='utf-8') as handle:
        json.dump({'runs': args.runs,
                   'operands': {op: values for op, values in operands.items()},
                   'sites': {op: {'%06X' % site: count for site, count in counter.items()}
                             for op, counter in sites.items()},
                   'entries': kept}, handle)
    print('\n%s: %d operand pairs, %d entries of the three routines (of %d seen)'
          % (os.path.relpath(args.out, ROOT),
             sum(len(v) for v in operands.values()),
             sum(len(kept[r]) for r in ROUTINES),
             sum(len(entries[r]) for r in ROUTINES)))
    return 0


if __name__ == '__main__':
    sys.exit(main())
