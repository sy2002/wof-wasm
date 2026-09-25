"""The mission scripts of M6, and a per-tick view of the enemy aircraft and the ships while
one runs.

Every script is a raw schedule for tools/headless.py, flown by a plan of
tools/m6_autopilot.py and kept in tools/m6_runs.py (written by tools/m6_emit.py): the
original is deterministic for a given schedule, so the recorded schedule flies the same
flight again.  The maps beyond the first rank are reached as the setups of
tests/test_mission.py reach them: the rank chosen with the stick in the rank selection and
the mission number poked at the selection's end (`POKES`), because a campaign's next
mission is M7's.  Two scripts poke a state instead: `night_d` the night flag, as M4's night
mission does, and `kills_a` the enemy plane counter above 99.

    .venv/bin/python tools/m6_scripts.py --list
    .venv/bin/python tools/m6_scripts.py trace oil_d               the enemies, tick by tick
    .venv/bin/python tools/m6_scripts.py trace fight_a --every 8 --from 1300

`script(name)` returns the run description of any script of M4, M5 or M6, and `SCRIPTS`
names M6's in the order the tests use; `SLOW` those that run only with --slow.  What each
one reaches is in re/notes/porting-m6.md, "The scripts".
"""
import argparse
import json
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import headless                                              # noqa: E402
import m5_scripts                                            # noqa: E402
import m6_autopilot                                          # noqa: E402
import m6_runs                                               # noqa: E402

MISSION_NUMBER = 0x0253C0
NIGHT_FLAG = 0x025390
KILLS = 0x02537F
RANK_END, MISSION_RESET = m5_scripts.RANK_END, m5_scripts.MISSION_RESET

# The scripts in the order the tests take them; the long ones (more than about 2,000 ticks)
# run only with --slow.
SCRIPTS = ['kills_a', 'wrecks_a', 'oil_d', 'night_d', 'airfield_e', 'cruise_f', 'torpedo_f', 'crash_f', 'crash_side_f',
           'rockets_f', 'cruise_g', 'destroyer_h', 'ships_i', 'battleship_j', 'battleship_k',
           'destroyer_l', 'japcarrier_m', 'destroyer_n', 'japcarrier_o', 'countdown_b',
           'countdown_c', 'enemy_a', 'fight_a', 'sunk_a']
SLOW = {'countdown_b', 'countdown_c', 'enemy_a', 'fight_a', 'sunk_a'}


def length(raw):
    return sum(entry[0] for entry in raw)


# Where a script stops when its schedule runs on past the mission: sunk_a's mission ends
# with the game over at VBlank 25,810, and its schedule holds the autopilot's wait in the
# front end after it.
STOP = {'sunk_a': 26400}

RUNS = {}
POKES = {}
for _name in SCRIPTS:
    _raw = getattr(m6_runs, _name.upper(), None)
    if _raw is None:
        continue
    RUNS[_name] = (_raw, STOP.get(_name, length(_raw) + 20))
    _plan = m6_autopilot.PLANS[_name]
    _pokes = {}
    if _plan.get('mission'):
        _pokes[MISSION_NUMBER] = (2, _plan['mission'])
    for _address, _entry in _plan.get('pokes', {}).items():
        _pokes[_address] = (_entry[0], _entry[1] & ((1 << (8 * _entry[0])) - 1)) + tuple(_entry[2:])
    if _pokes:
        POKES[_name] = _pokes
SCRIPTS = [n for n in SCRIPTS if n in RUNS]

install_pokes = m5_scripts.install_pokes
poke_points = m5_scripts.poke_points


def script(name, **more):
    """The run description of an M6 script, or of an M4 or M5 one."""
    if name in RUNS:
        raw, vblanks = RUNS[name]
        description = {'raw': raw + [[1, '']], 'stop': {'vblanks': vblanks}}
        description.update(more)
        return description
    return m5_scripts.script(name, **more)


def pokes(name):
    return POKES.get(name) or m5_scripts.POKES.get(name)


def s16(v):
    return v - 0x10000 if v & 0x8000 else v


def trace(name, every=1, start=0, out=sys.stdout):
    """Run a script and print after every tick the player, the enemy plane counter, the
    carrier's hits left, the enemy ships' hits left and every enemy aircraft in use (its
    index, state, mode, relation, x, height, attitude, facing, firing and health)."""
    machine = headless.Headless(script(name))
    install_pokes(machine, pokes(name))
    started = time.time()
    limit = script(name)['stop'].get('vblanks', 1 << 60)
    print('tick  in  deck     x     y  oil lives kills carrier  ships | aircraft', file=out)
    while True:
        reason = machine.run(until='tick')
        if reason != 'tick' or machine.vblanks >= limit:
            break
        t = machine.ticks
        if t < start or (t - start) % every:
            continue
        o = machine.o
        ships = m6_autopilot.ships(o)
        print('%4d  %02x  %4d %5d %5d %4d %5d %5d %7d  %s | %s' % (
            t, o.r16(headless.TICK_INPUT) & 0xFF, s16(o.r16(0x025084)), s16(o.r16(0x02507A)),
            s16(o.r16(0x025078)), s16(o.r16(0x02508A)), o.read(0x02535C, 1)[0],
            o.read(KILLS, 1)[0], s16(o.r16(0x0254E4)),
            ','.join('%s:%d' % (sh['ship'][:4], sh['hits']) for sh in ships
                     if sh['ship'] != 'carrier'),
            ' '.join('%d:%x/%x/%d x%d y%d a%d f%d %s h%x' % (
                e['i'], e['state'], e['mode'], e['rel'], e['x'], e['y'], e['att'], e['face'],
                'F' if e['fire'] else '-', e['health'] & 0xFFFF)
                for e in m6_autopilot.aircraft(o))), file=out)
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
            raw, vblanks = RUNS[name]
            print('%-14s %6d VBlanks%s  %s' % (name, vblanks, ' (slow)' if name in SLOW else '',
                                              json.dumps(POKES.get(name, {}))))
        return 0
    trace(args.name, every=args.every, start=args.start)
    return 0


if __name__ == '__main__':
    sys.exit(main())
