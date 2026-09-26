"""The sound of the M4, M5 and M6 scripts under the headless original (M8, re/notes/sound.md).

Every script of tools/reach_observe.py's --m6 list runs with the model of Paula
(tools/headless_paula.py), and per script the tool gives: the sample starts and restarts of
the event log, by sound file and channel; the handler calls; the requests the main program
made deliverable (`late`, which the model's delivery rule wants at 0); and the event count
the closed loop of tests/m4compare.py holds the port to.

    .venv/bin/python tools/sound_observe.py --jobs 8 --markdown TABLE.md
    .venv/bin/python tools/sound_observe.py --runs kills_a deck
"""
import argparse
import collections
import concurrent.futures
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import headless                    # noqa: E402
import m5_scripts                  # noqa: E402
import reach_observe               # noqa: E402


def observe(name):
    """(name, record) of one script."""
    started = time.time()
    machine = headless.Headless(reach_observe.description_of(name))
    pokes = reach_observe.pokes_of(name)
    if pokes:
        m5_scripts.install_pokes(machine, pokes)
    machine.run(wall_limit=3600.0)
    paula = machine.paula
    by_file = collections.Counter((e[0], e[5].replace('sounds/', ''), e[4]) for e in paula.events)
    return name, {
        'vblanks': machine.vblanks, 'passes': machine.passes, 'ticks': machine.ticks,
        'starts': sum(1 for e in paula.events if e[0] == 'S'),
        'restarts': sum(1 for e in paula.events if e[0] == 'R'),
        'irqs': paula.irqs, 'late': paula.late,
        'player': sorted({c[1] for c in machine.player_calls if c[0].lower() == 'songplay'}),
        'together': sum(1 for h in paula.handled if len(h[1]) > 1),
        'by_file': sorted(by_file.items()),
        'seconds': time.time() - started,
    }


def scripts():
    return (reach_observe.PART2_SCRIPTS + reach_observe.m5_scripts_list() +
            reach_observe.m6_scripts_list())


def main():
    parser = argparse.ArgumentParser(description='the sound event logs of the mission scripts')
    parser.add_argument('--runs', nargs='*', default=None)
    parser.add_argument('--jobs', type=int, default=1)
    parser.add_argument('--markdown', default=None)
    args = parser.parse_args()
    names = args.runs or scripts()
    if args.jobs > 1:
        with concurrent.futures.ProcessPoolExecutor(max_workers=args.jobs) as pool:
            records = dict(pool.map(observe, names))
    else:
        records = dict(observe(name) for name in names)
    rows = ['| Script | VBlanks | Starts | Restarts | Handler calls | Late | Starts by sound and channel |',
            '|---|---|---|---|---|---|---|']
    for name in names:
        r = records[name]
        starts = ', '.join('%s %d:%d' % (f, c, n) for (k, f, c), n in r['by_file'] if k == 'S')
        rows.append('| `%s` | %d | %d | %d | %d | %d | %s |' % (
            name, r['vblanks'], r['starts'], r['restarts'], r['irqs'], r['late'], starts or 'none'))
    commands = sorted({c for n in names for c in records[n]['player']})
    rows.append('')
    rows.append('The commands the scripts give the music player: %s.  Handler calls that saw '
                'the requests of two channels or more: %d.' % (
                    commands, sum(records[n]['together'] for n in names)))
    rows.append('')
    total = [sum(records[n][k] for n in names) for k in ('starts', 'restarts', 'irqs', 'late')]
    rows.append('| all %d | | %d | %d | %d | %d | |' % tuple([len(names)] + total))
    text = '\n'.join(rows)
    print(text)
    if args.markdown:
        with open(args.markdown, 'w') as handle:
            handle.write(text + '\n')
    return 1 if total[3] else 0


if __name__ == '__main__':
    sys.exit(main())
