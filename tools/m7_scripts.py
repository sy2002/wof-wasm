"""The mission scripts of M7, and a per-tick view of the campaign while one runs.

Every script is a raw schedule for tools/headless.py, flown by a plan of
tools/m7_autopilot.py and kept in tools/m7_runs.py as its base, the VBlanks of the base
replayed and the tail the autopilot chose after them: the base is a script of M4 to M6 that
already wins its mission (island_a), or, for a plan of its own, its front end.  The
original is deterministic for a given schedule, so the script flies the same flight again.
A script's pokes are its base's and its plan's: the promotion and the rank's cap are
reached by the mission number and the rank poked where main has run map_load for the
campaign's first mission (0x0100AE), on both sides, as balloons_c pokes balloons_on.

    .venv/bin/python tools/m7_scripts.py --list
    .venv/bin/python tools/m7_scripts.py trace chain_a              the campaign, tick by tick
    .venv/bin/python tools/m7_scripts.py trace promote_a --from 4300 --every 4

`script(name)` returns the run description of an M7 script, or of any script of M4 to M6,
and `SCRIPTS` names M7's in the order the tests use; `SLOW` those that run only with
--slow.  What each one reaches is in re/notes/porting-m7.md, "The scripts".
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
import m6_scripts                                            # noqa: E402
import m7_autopilot                                          # noqa: E402

MAP_LOADED = m7_autopilot.MAP_LOADED
RANK_END, MISSION_RESET = m5_scripts.RANK_END, m5_scripts.MISSION_RESET

# The scripts in the order the tests take them; those built on island_a's win of map a run
# some 4,500 ticks before the next mission and run only with --slow.
SCRIPTS = ['save_a', 'ships_j', 'night_again', 'chain_a', 'promote_a', 'cap_a']
SLOW = {'chain_a', 'promote_a', 'cap_a'}

try:
    import m7_runs
except ImportError:                  # before the autopilot has flown anything
    m7_runs = None


def length(raw):
    return sum(entry[0] for entry in raw)


def build(name):
    """(raw schedule, pokes) of an M7 script from its flown tail."""
    plan = m7_autopilot.PLANS[name]
    base, cut_at, tail = getattr(m7_runs, name.upper())
    if base:
        base_raw, pokes = m7_autopilot.base_script(base)
    else:
        base_raw, pokes = m6_autopilot.prefix_of(plan), {}
        if plan.get('mission'):
            pokes[m7_autopilot.MISSION_NUMBER] = (2, plan['mission'])
    pokes = dict(pokes)
    pokes.update(plan.get('pokes', {}))
    return m7_autopilot.cut(base_raw, cut_at) + [list(entry) for entry in tail], pokes


RUNS = {}
POKES = {}
for _name in SCRIPTS:
    if m7_runs is None or not hasattr(m7_runs, _name.upper()):
        continue
    _raw, _pokes = build(_name)
    RUNS[_name] = (_raw, length(_raw) + 20)
    POKES[_name] = _pokes
SCRIPTS = [n for n in SCRIPTS if n in RUNS]

install_pokes = m5_scripts.install_pokes
poke_points = m5_scripts.poke_points


# ------------------------------------------------------ part 2: the loaded game, the demo
#
# Written by hand as raw schedules, each from the program's start (re/notes/porting-m7.md,
# "Part 2: the scripts").  The keys go through the game's own input handler as a real
# keyboard's would: the cursor keys and Return in the menus, Control with L and R in flight.

UP, DOWN, RETURN = 0x4C, 0x4D, 0x44
CONTROL_L = [0x28, 'ctrl']
CONTROL_R = [0x13, 'ctrl']
TO_RANKS = [[30, ''], [3, 'F'], [30, ''], [3, 'F'], [400, '']]     # the rank selection is up
TO_MISSION = [[30, ''], [3, 'F']] * 5                             # rank 0 chosen, its briefing left
FROM_HOLD = [[3, 'F'], [126, ''], [415, 'R'], [173, 'RU'], [300, 'R']]   # the lift, the roll, off
LOAD_FIRST = [[1, '', [UP]], [60, ''], [1, '', [RETURN]], [200, ''], [1, '', [RETURN]]]
DEMO_FLIGHT = [[3, 'F'], [460, 'R'], [173, 'RU'], [200, 'R'], [4, 'RF'], [100, 'R'], [4, 'RF'],
               [200, 'RU'], [300, 'R'], [60, 'RD'], [200, 'R']]
DEMO_FF_AT = 100                     # demo_play_ff: the entry poked to 0xFF


def _save_a():
    return [list(e) for e in RUNS['save_a'][0]]


def _part2():
    runs = {
        # The disk's wof.mission 3 (map c, the first rank's third mission, saved on a real
        # Amiga) loaded from the rank selection's seventh entry, its briefing left with fire,
        # then the lift, the take-off and a flight east.
        'load_disk': (TO_RANKS + LOAD_FIRST + [[400, ''], [3, 'F'], [300, '']] + FROM_HOLD, {}),
        # save_a's flight with its save in the hold, then Control-L in flight: the dialog's
        # first entry is the save (the disk's file is the second), the briefing, which runs
        # out by itself, and the mission from the save again, from the hold up and away.
        'load_hold': (_save_a() + [[1, 'R', [CONTROL_L]], [120, ''], [1, '', [RETURN]],
                                   [700, '']] + FROM_HOLD, {}),
        # save_a's flight, then Control-R: 350 points beat the disk's tenth high score, so
        # the name entry comes (Return leaves the name empty), then the high scores (fire
        # leaves them), the outer loop round and the rank selection's seventh entry loading
        # the save.
        'load_menu': (_save_a() + [[1, 'R', [CONTROL_R]], [300, ''], [1, '', [RETURN]],
                                   [400, ''], [3, 'F'], [500, '']] +
                      LOAD_FIRST + [[700, '']] + FROM_HOLD, {}),
        # The game started with an argument (the harness's argc): the first rank chosen
        # records; a take-off, a flight east with two taps of fire, Control-R, and demo_end
        # writes wofdemo.
        'demo_record': (TO_MISSION + [[300, '']] + DEMO_FLIGHT + [[1, 'R', [CONTROL_R]],
                                                                  [300, '']], {}),
        # The same start, then nothing: the aircraft waits in the hold and the recording
        # ends at its count, 0x1386 entries (0x01183A), and demo_end writes it.
        'demo_record_long': (TO_MISSION + [[21000, '']], {}),
    }
    playback = [[30, ''], [3, 'F'], [30, ''], [3, 'F'], [2500, '']]
    runs['demo_play'] = (playback + [[1500, ''], [3, 'F'], [600, '']], {})
    runs['demo_play_ff'] = (playback + [[1500, '']], {})
    runs['demo_play_long'] = (playback + [[21000, '']], {})
    return runs


PART2 = ['load_disk', 'load_hold', 'load_menu', 'demo_record', 'demo_record_long', 'demo_play',
         'demo_play_ff', 'demo_play_long']
PART2_SLOW = {'load_hold', 'load_menu', 'demo_record_long', 'demo_play_long'}
_PART2 = None
_DEMO = None


def part2(name):
    global _PART2
    if _PART2 is None:
        _PART2 = _part2() if 'save_a' in RUNS else {}
    return _PART2[name]


def demo_file():
    """The wofdemo demo_record's run writes in the headless original, 0x1388 bytes."""
    global _DEMO
    if _DEMO is None:
        machine = headless.Headless(script('demo_record'))
        machine.run()
        _DEMO = bytes(machine.overlay['wofdemo'])
    return _DEMO


def demo_variant(name):
    """demo_play's file, and its two variants: a 0xFF poked in early, and every entry up to
    the buffer's end neutral, so that the playback ends at entry 0x1386."""
    data = bytearray(demo_file())
    if name == 'demo_play_ff':
        data[DEMO_FF_AT] = 0xFF
    elif name == 'demo_play_long':
        end = data.index(0xFF, 1)
        data[end:] = bytes(len(data) - end)
    return bytes(data)


def script(name, **more):
    """The run description of an M7 script, or of one of M4 to M6."""
    if name in PART2:
        raw, extra = part2(name)
        description = {'raw': [list(e) for e in raw] + [[1, '']],
                       'stop': {'vblanks': length(raw) + 20}}
        if name.startswith('demo_record'):
            description['argc'] = 2
        if name.startswith('demo_play'):
            description['files'] = {'wofdemo': demo_variant(name).hex()}
        description.update(extra)
        description.update(more)
        return description
    if name in RUNS:
        raw, vblanks = RUNS[name]
        description = {'raw': raw + [[1, '']], 'stop': {'vblanks': vblanks}}
        description.update(more)
        return description
    return m6_scripts.script(name, **more)


def pokes(name):
    if name in ('load_hold', 'load_menu'):
        return POKES['save_a']
    if name in PART2:
        return {}
    return POKES.get(name) if name in POKES else m6_scripts.pokes(name)


def s16(v):
    return v - 0x10000 if v & 0x8000 else v


def trace(name, every=1, start=0, out=sys.stdout):
    """Run a script and print after every tick the mission, the rank and the mission
    number, the player, the lives, the score, balloons_on, night_flag, the won flag
    (0x0253BC), the weapon menu and the balloon records in use."""
    machine = headless.Headless(script(name))
    install_pokes(machine, pokes(name))
    started = time.time()
    limit = script(name)['stop'].get('vblanks', 1 << 60)
    print('tick  in  S rank mis deck     x     y lives  score bal night won menu balloons',
          file=out)
    while True:
        reason = machine.run(until='tick')
        if reason != 'tick' or machine.vblanks - machine.spin_vblanks >= limit:
            break
        t = machine.ticks
        if t < start or (t - start) % every:
            continue
        o = machine.o
        pool = o.r32(0x026F66)
        up = sum(1 for i in range(20) if pool and o.read(pool + 0x12 * i + 0x11, 1)[0])
        print('%4d  %02x %2d %4d %3d %4d %5d %5d %5d %6d %3d %5d %3d %4d %8d' % (
            t, o.r16(headless.TICK_INPUT) & 0xFF, machine.missions, o.r16(0x0253BE),
            o.r16(0x0253C0), s16(o.r16(0x025084)), s16(o.r16(0x02507A)), s16(o.r16(0x025078)),
            o.read(0x02535C, 1)[0], o.r32(0x02534C), o.read(0x02535D, 1)[0], o.r16(0x025390),
            s16(o.r16(0x0253BC)), o.read(0x025364, 1)[0], up), file=out)
    print('%d ticks, %d passes, %d VBlanks, %d missions, %.0f s, stopped: %s'
          % (machine.ticks, machine.passes, machine.vblanks, machine.missions,
             time.time() - started, reason), file=out)
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
            print('%-10s %6d VBlanks%s  %s' % (name, vblanks, ' (slow)' if name in SLOW else '',
                                              json.dumps({hex(a): v for a, v in POKES[name].items()})))
        return 0
    trace(args.name, every=args.every, start=args.start)
    return 0


if __name__ == '__main__':
    sys.exit(main())
