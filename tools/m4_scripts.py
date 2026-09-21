"""The mission scripts of M4 part 2, and a per-tick view of the player while one runs.

The five scripts of part 1 live in tools/pass_observe.py (deck, flight, climb, lost,
gameover). Part 2 adds the ones below; each is a raw schedule for tools/headless.py, a list
of [VBlanks, letters] where the letters are the stick and the button of that VBlank (U
forward, D back, L, R, F; re/notes/headless.md, "Input").

    .venv/bin/python tools/m4_scripts.py --list
    .venv/bin/python tools/m4_scripts.py trace landing          the player, tick by tick
    .venv/bin/python tools/m4_scripts.py trace landing --every 4 --from 300

`script(name)` returns the run description of any of the scripts, part 1's included, and
`SCRIPTS` names all of them in the order the tests use.
"""
import argparse
import json
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import headless                                              # noqa: E402
import pass_observe                                          # noqa: E402

FRONT = pass_observe.FRONT
TAKE_OFF = pass_observe.TAKE_OFF

# The weapon menu on the deck: the stick moves the cursor, the button chooses (the manual,
# page 4, "Selecting weapons"), then the lift, the roll and the climb of TAKE_OFF.
SELECT = (FRONT + [[40, '']] +
          [[8, 'D'], [32, '']] * 3 + [[8, 'U'], [32, '']] * 4 + [[8, 'D'], [32, '']] +
          [[3, 'F'], [60, ''], [460, 'R'], [400, 'RU'], [300, 'R']])


def length(raw):
    return sum(entry[0] for entry in raw)


# The prefix the autopilot of tools/m4_autopilot.py starts from: the front end, bombs taken,
# the lift, the roll to the right.
PILOT = FRONT + [[40, ''], [3, 'F'], [60, ''], [460, 'R']]

# Flown by tools/m4_autopilot.py's policy `turns`: turns both ways low and high, level,
# climbing and diving, one in the eighth-scale view and one at the ceiling; a glide with the
# stick left alone down to the airspeed's floor; the stick forward alone while flying left.
TURNS = PILOT + [
    [190, 'RU'], [124, 'R'], [79, 'L'], [89, 'LU'], [7, 'RU'], [81, 'R'], [100, 'RD'],
    [7, 'LD'], [13, 'L'], [476, 'LU'], [112, 'R'], [396, ''], [112, 'L'], [244, 'U'],
    [628, 'LU'], [112, 'R'], [159, 'RD'],
]

# Flown by the policy `landing`: out to the right, back from the right low over the bow, the
# stick forward on the deck so that the hook catches the fourth cable (deck state 7), a taxi
# to the lift, down, the next weapon, up, and a second take-off.
LANDING = PILOT + [
    [198, 'RU'], [164, 'R'], [112, 'L'], [31, 'LU'], [56, 'L'], [4, 'LU'], [4, 'L'],
    [4, 'LU'], [4, 'L'], [4, 'LU'], [24, 'L'], [12, 'LD'], [12, 'L'], [12, 'LU'],
    [16, 'L'], [8, 'LD'], [20, 'L'], [8, 'LU'], [8, 'L'], [8, 'LD'], [16, 'L'], [8, 'LU'],
    [8, 'L'], [8, 'LD'], [20, 'L'], [8, 'LU'], [12, 'L'], [8, 'LD'], [20, 'L'], [1, 'LU'],
    [32, 'U'], [164, ''], [179, 'L'], [100, ''], [4, 'L'], [69, ''], [3, 'F'], [212, ''],
    [8, 'D'], [72, ''], [4, 'F'], [129, ''], [387, 'R'], [188, 'RU'], [80, 'R'],
]

# The flight to the island of map a and across it without the button (re/notes/passes.md's
# TURN_LEFT, then the stick left alone). Over land the aircraft reaches M5's stand-ins
# without any weapon, so this script is judged by attribution, not as a clean run.
ISLAND = FRONT + TAKE_OFF + pass_observe.TURN_LEFT + [[2600, '']]

# Flown by the policy `fuel`: back and forth over the sea east of the carrier at a steady
# height until the fuel runs out - 0xC0 units, one every 28 ticks in the air (logic_tick,
# 0x0113B4), about 5,400 ticks - then the fall into the sea and the next aircraft.  The button
# is held inside every turn, which keeps the enemy's countdown from running out (0x01BC02)
# without firing the guns or dropping a weapon (tools/m4_autopilot.py).
FUEL = PILOT + [
    [370, 'RU'], [19, 'RD'], [16, 'R'], [8, 'RU'], [8, 'R'], [4, 'RU'], [4, 'R'], [8, 'RU'],
    [744, 'R'], [28, 'L'], [4, 'LU'], [12, 'LF'], [20, 'LUF'], [36, 'LDF'], [28, 'LF'], [8,
    'LUF'], [4, 'LF'], [8, 'LUF'], [20, 'LF'], [24, 'L'], [4, 'LU'], [12, 'L'], [4, 'LU'], [976,
    'L'], [28, 'R'], [4, 'RU'], [8, 'RF'], [4, 'RUF'], [24, 'RF'], [8, 'RUF'], [32, 'RF'], [20,
    'RUF'], [4, 'RF'], [32, 'RDF'], [4, 'RF'], [24, 'R'], [16, 'RU'], [980, 'R'], [28, 'L'], [4,
    'LU'], [8, 'LF'], [4, 'LUF'], [24, 'LF'], [8, 'LUF'], [32, 'LF'], [4, 'LUF'], [8, 'LF'],
    [16, 'LUF'], [8, 'LF'], [24, 'LDF'], [32, 'L'], [16, 'LU'], [972, 'L'], [28, 'R'], [4,
    'RU'], [8, 'RF'], [4, 'RUF'], [24, 'RF'], [20, 'RUF'], [4, 'RF'], [32, 'RDF'], [28, 'RF'],
    [16, 'RUF'], [1020, 'R'], [12, 'L'], [4, 'LU'], [16, 'L'], [4, 'LUF'], [16, 'LF'], [4,
    'LUF'], [16, 'LF'], [4, 'LUF'], [16, 'LF'], [20, 'LUF'], [36, 'LDF'], [20, 'LF'], [8, 'L'],
    [8, 'LU'], [4, 'L'], [8, 'LU'], [992, 'L'], [28, 'R'], [4, 'RU'], [12, 'RF'], [4, 'RUF'],
    [16, 'RF'], [4, 'RUF'], [16, 'RF'], [4, 'RUF'], [16, 'RF'], [4, 'RUF'], [16, 'RF'], [4,
    'RUF'], [16, 'RF'], [20, 'RUF'], [4, 'RDF'], [32, 'RD'], [64, 'R'], [4, 'RU'], [920, 'R'],
    [28, 'L'], [4, 'LU'], [8, 'LF'], [4, 'LUF'], [24, 'LF'], [8, 'LUF'], [32, 'LF'], [4, 'LUF'],
    [8, 'LF'], [4, 'LUF'], [24, 'LF'], [20, 'LUF'], [4, 'L'], [32, 'LD'], [984, 'L'], [28, 'R'],
    [4, 'RU'], [8, 'RUF'], [4, 'RF'], [4, 'RUF'], [52, 'RF'], [8, 'RUF'], [28, 'RF'], [8,
    'RUF'], [24, 'RF'], [8, 'R'], [20, 'RU'], [4, 'R'], [20, 'RD'], [28, 'R'], [4, 'RU'], [940,
    'R'], [24, 'L'], [4, 'LU'], [4, 'L'], [4, 'LF'], [4, 'LUF'], [24, 'LF'], [8, 'LUF'], [32,
    'LF'], [4, 'LUF'], [8, 'LF'], [4, 'LUF'], [24, 'LF'], [20, 'LUF'], [4, 'LF'], [32, 'LD'],
    [56, 'L'], [4, 'LU'], [932, 'L'], [28, 'R'], [4, 'RU'], [8, 'RF'], [4, 'RUF'], [24, 'RF'],
    [8, 'RUF'], [32, 'RF'], [4, 'RUF'], [8, 'RF'], [4, 'RUF'], [24, 'RF'], [20, 'RUF'], [4,
    'R'], [32, 'RD'], [988, 'R'], [28, 'L'], [4, 'LU'], [8, 'LUF'], [4, 'LF'], [4, 'LUF'], [52,
    'LF'], [8, 'LUF'], [28, 'LF'], [8, 'LUF'], [24, 'LF'], [8, 'L'], [20, 'LU'], [4, 'L'], [20,
    'LD'], [28, 'L'], [4, 'LU'], [940, 'L'], [24, 'R'], [4, 'RU'], [4, 'R'], [4, 'RF'], [4,
    'RUF'], [24, 'RF'], [8, 'RUF'], [32, 'RF'], [4, 'RUF'], [8, 'RF'], [4, 'RUF'], [24, 'RF'],
    [20, 'RUF'], [4, 'RF'], [32, 'RD'], [56, 'R'], [4, 'RU'], [928, 'R'], [28, 'L'], [4, 'LU'],
    [8, 'LF'], [4, 'LUF'], [24, 'LF'], [8, 'LUF'], [32, 'LF'], [4, 'LUF'], [8, 'LF'], [4,
    'LUF'], [24, 'LF'], [20, 'LUF'], [4, 'L'], [32, 'LD'], [984, 'L'], [28, 'R'], [4, 'RU'], [8,
    'RUF'], [4, 'RF'], [4, 'RUF'], [52, 'RF'], [8, 'RUF'], [28, 'RF'], [8, 'RUF'], [24, 'RF'],
    [8, 'R'], [20, 'RU'], [4, 'R'], [20, 'RD'], [28, 'R'], [4, 'RU'], [940, 'R'], [24, 'L'], [4,
    'LU'], [4, 'L'], [4, 'LF'], [4, 'LUF'], [24, 'LF'], [8, 'LUF'], [32, 'LF'], [4, 'LUF'], [8,
    'LF'], [4, 'LUF'], [24, 'LF'], [20, 'LUF'], [4, 'LF'], [32, 'LD'], [56, 'L'], [4, 'LU'],
    [932, 'L'], [28, 'R'], [4, 'RU'], [8, 'RF'], [4, 'RUF'], [24, 'RF'], [8, 'RUF'], [32, 'RF'],
    [4, 'RUF'], [8, 'RF'], [4, 'RUF'], [24, 'RF'], [20, 'RUF'], [4, 'R'], [32, 'RD'], [988,
    'R'], [28, 'L'], [4, 'LU'], [8, 'LUF'], [4, 'LF'], [4, 'LUF'], [52, 'LF'], [8, 'LUF'], [28,
    'LF'], [8, 'LUF'], [24, 'LF'], [8, 'L'], [20, 'LU'], [4, 'L'], [20, 'LD'], [28, 'L'], [4,
    'LU'], [940, 'L'], [24, 'R'], [4, 'RU'], [4, 'R'], [4, 'RF'], [4, 'RUF'], [24, 'RF'], [8,
    'RUF'], [32, 'RF'], [4, 'RUF'], [8, 'RF'], [4, 'RUF'], [24, 'RF'], [20, 'RUF'], [4, 'RF'],
    [32, 'RD'], [28, 'R'], [857, ''],
]

RUNS = {
    'select': (SELECT, length(SELECT) + 20),
    'turns': (TURNS, length(TURNS) + 20),
    'landing': (LANDING, length(LANDING) + 20),
    'island': (ISLAND, length(ISLAND) + 20),
    'fuel': (FUEL, length(FUEL) + 20),
}

PART1 = ['deck', 'flight', 'climb', 'lost', 'gameover']
SCRIPTS = PART1 + list(RUNS)

PLAYER = 0x025078
WATCH = [
    ('deck', PLAYER + 0x0C, 2), ('y', PLAYER + 0x00, 2), ('x', PLAYER + 0x02, 2),
    ('face', PLAYER + 0x14, 2), ('sx', PLAYER + 0x16, 2), ('sy', PLAYER + 0x18, 2),
    ('fuel', PLAYER + 0x0E, 2), ('oil', PLAYER + 0x12, 2), ('air', 0x025414, 2),
    ('att', 0x02540E, 2), ('pitch', 0x025AA2, 2), ('step', 0x024F36, 2),
    ('lives', 0x02535C, 1), ('over', 0x025362, 1), ('wtype', 0x0253A4, 2),
    ('wcount', 0x02536D, 1), ('menu', 0x025364, 1),
]


def script(name, **more):
    """The run description of a part 1 or a part 2 script, or of a key run of tests/runs/
    named `run:` and the file's name."""
    if name.startswith('run:'):
        with open(os.path.join(os.path.dirname(HERE), 'tests', 'runs', name[4:] + '.json')) as f:
            description = json.load(f)
        description.update(more)
        return description
    if name in RUNS:
        raw, vblanks = RUNS[name]
        description = {'raw': raw + [[1, '']], 'stop': {'vblanks': vblanks}}
        description.update(more)
        return description
    return pass_observe.script(name, **more)


def signed(v, bits):
    return v - (1 << bits) if v >> (bits - 1) else v


def trace(name, every=1, start=0, raw=None, vblanks=None, out=sys.stdout):
    """Run a script and print the player's state after every tick."""
    description = script(name) if raw is None else {'raw': raw + [[1, '']],
                                                    'stop': {'vblanks': vblanks}}
    machine = headless.Headless(description)
    started = time.time()
    print('tick  in   ' + ' '.join('%6s' % w[0] for w in WATCH), file=out)
    limit = description['stop'].get('vblanks', 1 << 60)
    while True:
        reason = machine.run(until='tick')          # run(until=...) ignores the stop, so:
        if reason != 'tick' or machine.vblanks >= limit:
            break
        t = machine.ticks
        if t >= start and (t - start) % every == 0:
            values = [signed(machine.o.r16(a) if n == 2 else machine.o.read(a, 1)[0], 8 * n)
                      for _, a, n in WATCH]
            print('%4d  %02x  ' % (t, machine.o.r16(headless.TICK_INPUT) & 0xFF) +
                  ' '.join('%6d' % v for v in values), file=out)
    print('%d ticks, %d passes, %d VBlanks, %.0f s, stopped: %s'
          % (machine.ticks, machine.passes, machine.vblanks, time.time() - started, reason),
          file=out)
    return machine


def main():
    parser = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    parser.add_argument('command', nargs='?', choices=['trace'])
    parser.add_argument('name', nargs='?')
    parser.add_argument('--list', action='store_true')
    parser.add_argument('--every', type=int, default=1)
    parser.add_argument('--from', dest='start', type=int, default=0)
    args = parser.parse_args()
    if args.list or not args.command:
        for name in SCRIPTS:
            print(name)
        return 0
    trace(args.name, every=args.every, start=args.start)
    return 0


if __name__ == '__main__':
    sys.exit(main())
