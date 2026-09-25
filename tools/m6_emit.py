"""Writes the schedules the M6 autopilot flew into tools/m6_runs.py as Python literals.

    .venv/bin/python tools/m6_emit.py FLOWN.json [FLOWN2.json ...] [--only NAME ...]

tools/m6_autopilot.py --all saves each plan's schedule and a summary of what it reached in
a JSON file; this turns the schedules into the literals tools/m6_scripts.py imports, one
constant per script, the runs after the front end wrapped to the file's width.  A script
already in tools/m6_runs.py and not in the JSON files is kept as it is.
"""
import argparse
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import m6_autopilot                                          # noqa: E402

OUT = os.path.join(HERE, 'm6_runs.py')
HEAD = '''"""The schedules of the M6 scripts, as tools/m6_autopilot.py flew them (tools/m6_emit.py
writes this file; tools/m6_scripts.py says what each one is).  Each is the front end with the
rank chosen, then the runs of [VBlanks, letters] the autopilot chose."""
import m6_autopilot

'''


def literal(name, script, rank, width=92):
    head = m6_autopilot.prefix_of({'rank': rank})
    assert script[:len(head)] == head, name
    runs = script[len(head):]
    lines, line = [], '    '
    for run in runs:
        item = '[%d, %r], ' % (run[0], run[1])
        if len(line) + len(item) > width:
            lines.append(line.rstrip())
            line = '    '
        line += item
    lines.append(line.rstrip())
    return '%s = m6_autopilot.prefix_of({\'rank\': %d}) + [\n%s\n]\n' % (
        name.upper(), rank, '\n'.join(lines))


def existing():
    """{NAME: text} of the constants already in tools/m6_runs.py."""
    if not os.path.exists(OUT):
        return {}
    text = open(OUT).read()
    out = {}
    for match in re.finditer(r'^([A-Z0-9_]+) = m6_autopilot\.prefix_of.*?^\]\n', text,
                             re.M | re.S):
        out[match.group(1)] = match.group(0)
    return out


def main():
    parser = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    parser.add_argument('flown', nargs='+')
    parser.add_argument('--only', nargs='*')
    args = parser.parse_args()
    constants = existing()
    for path in args.flown:
        with open(path) as handle:
            flown = json.load(handle)
        for name, entry in flown.items():
            if args.only and name not in args.only:
                continue
            rank = m6_autopilot.PLANS[name].get('rank', 0)
            constants[name.upper()] = literal(name, entry['script'], rank)
            print('%-16s %6d ticks  %s' % (name, entry['summary']['ticks'],
                                          json.dumps(entry['summary'])[:150]))
    with open(OUT, 'w') as handle:
        handle.write(HEAD)
        for name in sorted(constants):
            handle.write('\n' + constants[name])
    return 0


if __name__ == '__main__':
    sys.exit(main())
