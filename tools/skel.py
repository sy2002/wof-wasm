#!/usr/bin/env python3
"""Control-flow skeleton of one routine from re/Wings.lst.

    skel.py <hex addr or name> [--all]

Prints only labels, calls, branches, compares/tests and returns, which is usually enough to see
what a routine does before reading it in full. --all prints every line of the routine.
"""
import os
import re
import sys

LST = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 're', 'Wings.lst')
KEEP = re.compile(r'\s(jsr|jmp|bsr(\.[bw])?|bra(\.[bw])?|b[a-z]{2}\.[bw]|db[a-z]{1,2}|rts|rte|tst\.[bwl]|cmpi?\.[bwl]|cmpa\.[wl]|btst(\.[bl])?)\s')


def routine(key):
    lines = open(LST).read().split('\n')
    key = key.lower()
    start = None
    for i, l in enumerate(lines):
        if l.startswith('; ') and re.match(r'^; (\S+)   \[(C|asm)\]', l):
            name = l.split()[1]
            is_hex = re.fullmatch(r'[0-9a-f]+', key) is not None
            if name.lower() == key or (is_hex and name.lower() == 'sub_%06x' % int(key, 16)):
                start = i
                break
    if start is None and re.fullmatch(r'[0-9a-f]+', key):           # address inside a routine
        want = '%06x ' % int(key, 16)
        hit = next((i for i, l in enumerate(lines) if l.startswith(want)), None)
        if hit is not None:
            start = max(i for i in range(hit + 1) if lines[i].startswith('; ===')) + 1
    if start is None:
        sys.exit('not found: ' + key)
    body = []
    for l in lines[start:]:
        if l.startswith('; ===') and body:
            break
        body.append(l)
    return body


def main():
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    full = '--all' in sys.argv
    for l in routine(sys.argv[1]):
        if full or l.startswith(';') or re.match(r'^[A-Za-z_]\w*:', l):
            print(l)
        elif KEEP.search(l):
            print('  ' + l[:6] + '  ' + re.sub(r'\s+', ' ', l[28:]).strip()[:120])


if __name__ == '__main__':
    main()
