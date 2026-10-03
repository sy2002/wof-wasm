#!/usr/bin/env python3
"""The routine inventory as the appendix shows it: the routines by status, then every routine.

    .venv/bin/python book/tools/routines.py            write book/docs/generated/tables/routines.md
    .venv/bin/python book/tools/routines.py --check    make it into a temporary directory and
                                                       compare with the committed file
    .venv/bin/python book/tools/routines.py --out DIR  write it into DIR instead

The inventory is re/functions.csv, which tools/disasm.py writes with the listing and whose
status column is kept by hand (SPEC.md 7.4).  It is read with the csv module, since its strings
column holds commas, and nothing else is read: no ROM, no native library, no build.

The file is two Markdown tables, each with a caption under it: the statuses in the order of
SPEC.md 7.4 and chapter 4's table, each with its routines, and the whole; then one row a routine
in the file's order, which is the order of the address, with its address at the fixed load
layout, its name, its kind (C or asm), its span in bytes and its status.  The appendix includes
it with a snippet.  A status outside the six, or a row without an address, stops the run, so
that the page never counts what its prose does not explain.

Exit status: 0 done (or --check found the committed file equal), 1 --check found a
difference, 2 the inventory could not be read or holds what the page does not explain.
"""
import argparse
import collections
import csv
import pathlib
import re
import sys
import tempfile

from common import GENERATED, ROOT, Failure, compare, rel, replace_tree

TABLES = GENERATED / 'tables'
FILE = 'routines.md'                    # the directory is shared with suite.py: each holds its own file
INVENTORY = ROOT / 're' / 'functions.csv'
STATUSES = ('verified', 'ported', 'partial', 'replace', 'drop', 'todo')
ADDRESS = re.compile(r'^[0-9a-f]{6}$')


def routines():
    """The inventory's rows as (address, name, kind, span, status), in the file's order."""
    if not INVENTORY.exists():
        raise Failure('%s is missing' % rel(INVENTORY))
    with open(INVENTORY, newline='', encoding='utf-8') as handle:
        rows = [(r['addr'], r['name'], r['kind'], r['span'], r['status'])
                for r in csv.DictReader(handle)]
    problems = ['%s: no address of six hexadecimal digits' % (address or '(empty)')
                for address, _, _, _, _ in rows if not ADDRESS.match(address)]
    problems += ['%s %s: status %r is none of %s' % (address, name, status, ', '.join(STATUSES))
                 for address, name, _, _, status in rows if status not in STATUSES]
    if problems or not rows:
        raise Failure('%s: %s' % (rel(INVENTORY), '; '.join(problems) or 'no rows'))
    return rows


def table(rows):
    """The two tables with their captions, the numbers with a thousands comma as suite.py's."""
    counts = collections.Counter(status for _, _, _, _, status in rows)
    out = ['| Status | Routines |', '|---|---|']
    out += ['| `%s` | %s |' % (status, '{:,}'.format(counts[status])) for status in STATUSES]
    out.append('| all | %s |' % '{:,}'.format(len(rows)))
    out += ['', '/// caption',
            "The routines by status, counted from the inventory at the book's build.", '///', '']
    out += ['| Address | Name | Kind | Span | Status |', '|---|---|---|---:|---|']
    out += ['| `0x%s` | `%s` | %s | %s | %s |' % (address.upper(), name, kind,
                                                  '{:,}'.format(int(span)), status)
            for address, name, kind, span, status in rows]
    out += ['', '/// caption',
            "Every routine of the program in the order of its address, its span in bytes, "
            "from the inventory at the book's build.", '///']
    return '\n'.join(out) + '\n', counts


def generate(folder):
    path = pathlib.Path(folder) / FILE
    path.parent.mkdir(parents=True, exist_ok=True)
    rows = routines()
    text, counts = table(rows)
    path.write_text(text, encoding='utf-8')
    return path, rows, counts


def main():
    parser = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    parser.add_argument('--check', action='store_true',
                        help='compare a fresh table with the committed file, write nothing')
    parser.add_argument('--out', help='write into this directory instead')
    args = parser.parse_args()
    try:
        if args.check:
            with tempfile.TemporaryDirectory() as temp:
                generate(temp)
                problems = compare(temp, TABLES, only={FILE})
            for line in problems:
                print(line)
            print('routines  %s' % ('%d differ' % len(problems) if problems
                                    else '%s equal to the committed file' % FILE))
            return 1 if problems else 0
        if args.out:
            path, rows, counts = generate(args.out)
        else:
            with tempfile.TemporaryDirectory() as temp:
                _, rows, counts = generate(temp)
                replace_tree(temp, TABLES, only={FILE})
            path = TABLES / FILE
        print('routines  %s, %d routines: %s' % (
            rel(path) if not args.out else path, len(rows),
            ', '.join('%s %d' % (status, counts[status]) for status in STATUSES)))
        return 0
    except Failure as failure:
        print('routines  FAILED: %s' % failure, file=sys.stderr)
        return 2


if __name__ == '__main__':
    sys.exit(main())
