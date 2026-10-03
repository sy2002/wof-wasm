#!/usr/bin/env python3
"""The suite's test modules by layer, with their tests, for chapter 24.

    .venv/bin/python book/tools/suite.py            write book/docs/generated/tables/suite-layers.md
    .venv/bin/python book/tools/suite.py --check    make it into a temporary directory and compare
                                                    with the committed file
    .venv/bin/python book/tools/suite.py --out DIR  write it into DIR instead

The tests are counted by pytest's own collection of the repository's suite,
`pytest tests/ --collect-only -q`, which imports the modules and runs no test: one line a test,
`module::name[parameters]`.  The collection does not depend on the ROM, the native library or
the browsers, whose absence marks tests skipped and leaves them collected, so the count is the
suite's wherever it is made.  The layers and their modules are book/suite.toml's.

The file is a Markdown table, one row a layer, its modules linked into the repository with
their tests, a last row for the whole suite, and the manifest's title as its caption; the
chapter includes it with a snippet.  A test
module of tests/ in no layer or in two, a module of the manifest with no tests, or a collection
that fails stops the run.

Exit status: 0 done (or --check found the committed file equal), 1 --check found a
difference, 2 the suite could not be collected or the manifest does not cover it.
"""
import argparse
import collections
import os
import pathlib
import re
import subprocess
import sys
import tempfile

from common import GENERATED, ROOT, Failure, compare, manifest, rel, replace_tree

TABLES = GENERATED / 'tables'
FILE = 'suite-layers.md'
TOTAL = re.compile(r'^(\d+) tests? collected')


def collected():
    """{module file name: tests}, from pytest's collection of tests/."""
    environment = dict(os.environ, PYTHONDONTWRITEBYTECODE='1')
    finished = subprocess.run([sys.executable, '-m', 'pytest', 'tests/', '--collect-only', '-q',
                               '-p', 'no:cacheprovider'],
                              cwd=ROOT, env=environment, capture_output=True, text=True)
    lines = finished.stdout.splitlines()
    if finished.returncode:
        raise Failure('pytest could not collect the suite:\n%s'
                      % '\n'.join((lines + finished.stderr.splitlines())[-20:]))
    counts = collections.Counter(line.split('::', 1)[0].rsplit('/', 1)[-1]
                                 for line in lines if '::' in line)
    total = next((int(m.group(1)) for m in map(TOTAL.match, lines) if m), None)
    if total != sum(counts.values()):
        raise Failure('pytest reports %s tests, the lines give %d' % (total, sum(counts.values())))
    return counts


def layers(counts):
    """The manifest's layers as (name, [(module, tests)]), checked against the suite."""
    rows, seen = [], collections.Counter()
    for layer in manifest('suite.toml')['layer']:
        rows.append((layer['name'], [(module, counts.get(module, 0)) for module in layer['modules']]))
        seen.update(layer['modules'])
    modules = {p.name for p in (ROOT / 'tests').glob('test_*.py')}
    problems = ['%s is in no layer' % m for m in sorted(modules - set(seen))]
    problems += ['%s is in %d layers' % (m, n) for m, n in sorted(seen.items()) if n > 1]
    problems += ['%s has no tests' % m for m in sorted(seen) if not counts.get(m)]
    problems += ['%s has tests and is no file of tests/' % m for m in sorted(set(counts) - modules)]
    if problems:
        raise Failure('book/suite.toml does not cover the suite: %s' % '; '.join(problems))
    return rows


def table(rows, title):
    """The Markdown table, the module names as repo: links (an underscore written %5F), and
    the manifest's title as its caption."""
    def link(module):
        return '[`%s`](repo:tests/%s)' % (module, module.replace('_', '%5F'))
    out = ['| Layer | Modules, with their tests | Tests |', '|---|---|---|']
    for name, modules in rows:
        out.append('| %s | %s | %s |' % (name, ', '.join('%s %d' % (link(m), n) for m, n in modules),
                                         '{:,}'.format(sum(n for _, n in modules))))
    every = [n for _, modules in rows for _, n in modules]
    out.append('| the suite | %d modules | %s |' % (len(every), '{:,}'.format(sum(every))))
    out += ['', '/// caption', title, '///']
    return '\n'.join(out) + '\n'


def generate(folder):
    path = pathlib.Path(folder) / FILE
    path.parent.mkdir(parents=True, exist_ok=True)
    rows = layers(collected())
    path.write_text(table(rows, manifest('suite.toml')['title']), encoding='utf-8')
    return path, rows


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
                problems = compare(temp, TABLES)
            for line in problems:
                print(line)
            print('suite     %s' % ('%d differ' % len(problems) if problems
                                    else '%s equal to the committed file' % FILE))
            return 1 if problems else 0
        if args.out:
            path, rows = generate(args.out)
        else:
            with tempfile.TemporaryDirectory() as temp:
                _, rows = generate(temp)
                replace_tree(temp, TABLES)
            path = TABLES / FILE
        tests = sum(n for _, modules in rows for _, n in modules)
        print('suite     %s, %d layers, %d tests' % (rel(path) if not args.out else path,
                                                    len(rows), tests))
        return 0
    except Failure as failure:
        print('suite     FAILED: %s' % failure, file=sys.stderr)
        return 2


if __name__ == '__main__':
    sys.exit(main())
