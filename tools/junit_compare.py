"""Compare the outcomes of pytest runs from their junit XML files.

    .venv/bin/python tools/junit_compare.py REFERENCE.xml RUN.xml [RUN-2.xml ...]

The first file is one outcome set; every file after it together form the other, which is how
the suite's two-phase run is held to a serial one (re/notes/testing.md): the emulator phase
and the page phase each write a file, and their union must be the serial run's outcome set.

A test is its junit id, `module::name[parameters]`; its outcome is passed, failed, error or
skipped, a skip with its reason.  pytest-xdist's `--dist loadgroup` appends `@<group>` to the
id of a test in a group (the suite groups the loop tests of one recorded script); that suffix
says where the test ran, not what it is, and is dropped.  Printed: the counts of both sides,
every test only one side has, every test whose outcome differs, and a test that appears
twice in one set.  The exit status is 0 when the two sets are identical and 1 otherwise.
"""
import argparse
import collections
import sys
import xml.etree.ElementTree as ET


def outcomes(paths):
    """{test id: outcome} over the files, and the ids seen more than once."""
    seen = {}
    twice = []
    for path in paths:
        for case in ET.parse(path).getroot().iter('testcase'):
            test = '%s::%s' % (case.get('classname'), case.get('name').split('@', 1)[0])
            outcome = 'passed'
            for child in case:
                if child.tag in ('failure', 'error'):
                    outcome = child.tag
                    break
                if child.tag == 'skipped':
                    outcome = 'skipped: %s' % (child.get('message') or '').strip()
            if test in seen:
                twice.append(test)
            seen[test] = outcome
    return seen, twice


def counts(result):
    return dict(collections.Counter(outcome.split(':')[0] for outcome in result.values()))


def main():
    parser = argparse.ArgumentParser(description=__doc__.split('\n\n')[0])
    parser.add_argument('reference')
    parser.add_argument('runs', nargs='+')
    args = parser.parse_args()

    ref, ref_twice = outcomes([args.reference])
    run, run_twice = outcomes(args.runs)
    print('reference %s: %d tests %s' % (args.reference, len(ref), counts(ref)))
    print('run %s: %d tests %s' % (' + '.join(args.runs), len(run), counts(run)))

    problems = 0
    for label, twice in (('reference', ref_twice), ('run', run_twice)):
        for test in twice:
            print('twice in the %s: %s' % (label, test))
            problems += 1
    for test in sorted(set(ref) - set(run)):
        print('only in the reference: %s (%s)' % (test, ref[test]))
        problems += 1
    for test in sorted(set(run) - set(ref)):
        print('only in the run: %s (%s)' % (test, run[test]))
        problems += 1
    for test in sorted(set(ref) & set(run)):
        if ref[test] != run[test]:
            print('differs: %s: reference %s, run %s' % (test, ref[test], run[test]))
            problems += 1

    print('identical' if problems == 0 else '%d difference(s)' % problems)
    return 0 if problems == 0 else 1


if __name__ == '__main__':
    sys.exit(main())
