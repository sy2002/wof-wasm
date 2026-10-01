#!/usr/bin/env python3
"""The book's listings, extracted from the real sources by name.

    .venv/bin/python book/tools/listings.py            write book/docs/generated/listings/
    .venv/bin/python book/tools/listings.py --check    make them into a temporary directory and
                                                       compare with the committed files
    .venv/bin/python book/tools/listings.py --out DIR  write them into DIR instead

Reads the manifest book/listings.toml and writes one plain-text file per entry,
book/docs/generated/listings/<kind>/<name>.<ext>, from:

    asm  re/Wings.lst, a routine by its name in re/functions.csv: its lines from its start
         address to its end (or a part of it between two addresses)
    c    src/*.c, a C function by its name, with the comment directly above it
    js   web/*.js, a function or a method by its name, with the comment directly above it
    py   tools/*.py, a function or a class by its name, with the comments directly above it

The first line of every file names the source and the line range (or the address range), in
the comment syntax of its language, so that a chapter shows where the extract comes from.  A
name that does not exist, or exists more than once without a `file` to choose, fails the run
with the name; so does an extract longer than its limit (40 lines, or the entry's `lines`).

Exit status: 0 done (or --check found the committed files equal), 1 --check found a
difference, 2 the manifest asks for something the sources do not have.
"""
import argparse
import ast
import csv
import pathlib
import re
import sys
import tempfile

from common import LISTINGS, ROOT, Failure, compare, manifest, rel, replace_tree

DEFAULT_LINES = 40
EXT = {'asm': 'lst', 'c': 'c', 'js': 'js', 'py': 'py'}
SOURCES = {'c': ('src', '*.c'), 'js': ('web', '*.js'), 'py': ('tools', '*.py')}
LISTING = ROOT / 're' / 'Wings.lst'
FUNCTIONS = ROOT / 're' / 'functions.csv'


# ------------------------------------------------------------------ C and JavaScript

def masked(text, js=False):
    """The text with every comment, string, template and regular expression literal blanked
    to spaces, newlines kept, so that braces and parentheses can be counted in it."""
    out = list(text)
    n = len(text)
    i = 0
    stack = []                  # JS: the brace depth at which each open ${ returns to its template
    depth = 0
    last = ''                   # the last significant character of code

    def blank(a, b):
        for k in range(a, b):
            if out[k] != '\n':
                out[k] = ' '

    def template(i):
        """From inside a template literal to its end or to a ${; returns (position, opened)."""
        start = i
        while i < n:
            if text[i] == '\\':
                i += 2
                continue
            if text[i] == '`':
                blank(start, i)
                return i + 1, False
            if text.startswith('${', i):
                blank(start, i)
                return i + 2, True
            i += 1
        blank(start, n)
        return n, False

    while i < n:
        c = text[i]
        if text.startswith('//', i):
            end = text.find('\n', i)
            end = n if end < 0 else end
            blank(i, end)
            i = end
        elif text.startswith('/*', i):
            end = text.find('*/', i + 2)
            end = n if end < 0 else end + 2
            blank(i, end)
            i = end
        elif c in '"\'':
            k = i + 1
            while k < n and text[k] != c and text[k] != '\n':
                k += 2 if text[k] == '\\' else 1
            blank(i + 1, k)
            i = k + 1
            last = c
        elif js and c == '`':
            i, opened = template(i + 1)
            if opened:
                stack.append(depth)
                depth += 1
            last = '`'
        elif js and c == '/' and (last == '' or last in '(,=:[!&|?{};+-*%<>~^'):
            k = i + 1
            in_class = False
            while k < n and text[k] != '\n':
                if text[k] == '\\':
                    k += 2
                    continue
                if text[k] == '[':
                    in_class = True
                elif text[k] == ']':
                    in_class = False
                elif text[k] == '/' and not in_class:
                    break
                k += 1
            blank(i + 1, k)
            i = k + 1
            last = '/'
        else:
            if c == '{':
                depth += 1
            elif c == '}':
                depth -= 1
                if stack and stack[-1] == depth:
                    stack.pop()
                    i, opened = template(i + 1)
                    if opened:
                        stack.append(depth)
                        depth += 1
                    last = '`'
                    continue
            if not c.isspace():
                last = c
            i += 1
    return ''.join(out)


def closing(code, at, open_char, close_char):
    """The position just after the bracket that closes the one at `at`."""
    depth = 0
    for k in range(at, len(code)):
        if code[k] == open_char:
            depth += 1
        elif code[k] == close_char:
            depth -= 1
            if depth == 0:
                return k + 1
    return None


def skip_space(code, k):
    while k < len(code) and code[k].isspace():
        k += 1
    return k


def body_after(code, paren):
    """For a match ending at a parameter list's '(': the span of the body that follows it,
    or None when the parentheses are not followed by a body (a call, a prototype)."""
    end = closing(code, paren, '(', ')')
    if end is None:
        return None
    k = skip_space(code, end)
    if code.startswith('=>', k):
        k = skip_space(code, k + 2)
    if k < len(code) and code[k] == '{':
        stop = closing(code, k, '{', '}')
        return None if stop is None else (k, stop)
    return None


def line_of(text, pos):
    return text.count('\n', 0, pos)


def with_comment_above(lines, start):
    """The first line of the routine with the comment that ends directly above it."""
    above = start - 1
    if above >= 0 and lines[above].rstrip().endswith('*/'):
        k = above
        while k >= 0 and '/*' not in lines[k]:
            k -= 1
        if k >= 0 and lines[k].lstrip().startswith('/*'):
            return k
        return start
    k = start
    while k - 1 >= 0 and lines[k - 1].lstrip().startswith('//'):
        k -= 1
    return k


def c_functions(text, name):
    """Every definition of the C function `name` in one file, as (first line, last line)."""
    code = masked(text)
    lines = text.split('\n')
    found = []
    for m in re.finditer(r'(?m)^(?:[A-Za-z_][^\n;{}=()]*?\b)?%s\s*\(' % re.escape(name), code):
        span = body_after(code, m.end() - 1)
        if span is None:
            continue
        first = line_of(text, m.start())
        if re.match(r'%s\s*\(' % re.escape(name), lines[first]) and first > 0:
            first -= 1                        # the return type stands on the line above
        found.append((with_comment_above(lines, first), line_of(text, span[1] - 1)))
    return found


JS_PATTERNS = [
    r'\b(?:async\s+)?function\s*\*?\s*%s\s*\(',
    r'(?m)^[ \t]*(?:(?:static|async|get|set)\s+)*%s\s*\(',
    r'\b(?:const|let|var)\s+%s\s*=\s*(?:async\s*)?(?:function\b[^(]*)?\(',
]


def js_functions(text, name):
    """Every definition of the function or method `name` (or Class.method) in one file."""
    code = masked(text, js=True)
    lines = text.split('\n')
    lo, hi = 0, len(code)
    if '.' in name:
        owner, name = name.split('.', 1)
        m = re.search(r'\bclass\s+%s\b[^{]*' % re.escape(owner), code)
        if not m:
            return []
        lo = m.end()
        hi = closing(code, lo, '{', '}')
        if hi is None:
            return []
    found = set()
    for pattern in JS_PATTERNS:
        for m in re.finditer(pattern % re.escape(name), code[:hi]):
            if m.start() < lo:
                continue
            span = body_after(code, m.end() - 1)
            if span is None:
                continue
            first = line_of(text, m.start())
            found.add((with_comment_above(lines, first), line_of(text, span[1] - 1)))
    return sorted(found)


# ------------------------------------------------------------------ Python

def py_definitions(text, name):
    """Every function or class `name` (or Class.method) in one file, with its decorators and
    the comment lines directly above it."""
    tree = ast.parse(text)
    lines = text.split('\n')
    kinds = (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)
    parts = name.split('.')
    if len(parts) == 2:
        owners = [n for n in ast.walk(tree) if isinstance(n, ast.ClassDef) and n.name == parts[0]]
        nodes = [c for o in owners for c in o.body if isinstance(c, kinds) and c.name == parts[1]]
    else:
        nodes = [n for n in ast.walk(tree) if isinstance(n, kinds) and n.name == name]
    found = []
    for node in nodes:
        first = min([node.lineno] + [d.lineno for d in node.decorator_list]) - 1
        while first > 0 and lines[first - 1].lstrip().startswith('#'):
            first -= 1
        found.append((first, node.end_lineno - 1))
    return found


# ------------------------------------------------------------------ the listing

def routines():
    with open(FUNCTIONS, newline='') as handle:
        return {row['name']: row for row in csv.DictReader(handle)}


ADDRESS = re.compile(r'^([0-9a-f]{6})  ')
LABEL = re.compile(r'^[A-Za-z_]\w*:$')


def asm_extract(entry, table, listing):
    name = entry['name']
    row = table.get(name)
    if row is None:
        raise Failure('asm %s: no routine of that name in re/functions.csv' % name)
    start = int(row['addr'], 16)
    end = start + int(row['span'])                       # the first address after it
    lo, hi = entry.get('from', start), entry.get('to', end - 1)
    if not start <= lo <= hi < end:
        raise Failure('asm %s: from 0x%06X to 0x%06X lies outside the routine, 0x%06X-0x%06X'
                      % (name, lo, hi, start, end - 1))
    begin = next((i for i, line in enumerate(listing) if line.startswith('%06x  ' % lo)), None)
    if begin is None:
        raise Failure('asm %s: no instruction at 0x%06X in re/Wings.lst' % (name, lo))
    if 'to' in entry and not any(line.startswith('%06x  ' % hi)
                                 for line in listing[begin:begin + 4096]):
        raise Failure('asm %s: no instruction at 0x%06X in re/Wings.lst' % (name, hi))
    while begin > 0 and LABEL.match(listing[begin - 1]):
        begin -= 1                                       # the labels on the first instruction
    out, last = [], lo
    for line in listing[begin:]:
        m = ADDRESS.match(line)
        if m:
            address = int(m.group(1), 16)
            if address > hi:
                break
            last = address
        elif line.startswith('; ====') or not line.strip():
            break
        out.append(line.rstrip())
    while out and LABEL.match(out[-1]):
        out.pop()
    kind = '[%s]' % row['kind']
    part = '' if (lo, hi) == (start, end - 1) else ', a part of 0x%06X-0x%06X' % (start, end - 1)
    header = '; re/Wings.lst 0x%06X-0x%06X: %s %s%s' % (lo, last, name, kind, part)
    return header, out


def source_extract(entry):
    kind, name = entry['kind'], entry['name']
    folder, glob = SOURCES[kind]
    if 'file' in entry:
        paths = [ROOT / entry['file']]
        if not paths[0].exists():
            raise Failure('%s %s: no file %s' % (kind, name, entry['file']))
    else:
        paths = sorted((ROOT / folder).glob(glob))
    finder = {'c': c_functions, 'js': js_functions, 'py': py_definitions}[kind]
    hits = []
    for path in paths:
        text = path.read_text(encoding='utf-8')
        for first, last in finder(text, name):
            hits.append((path, text, first, last))
    if not hits:
        raise Failure('%s %s: no such %s in %s' % (
            kind, name, {'c': 'function', 'js': 'function or method',
                         'py': 'function or class'}[kind],
            entry.get('file', '%s/%s' % (folder, glob))))
    if len(hits) > 1:
        raise Failure('%s %s: defined %d times (%s); name the file' % (
            kind, name, len(hits), ', '.join('%s:%d' % (rel(p), f + 1) for p, _, f, _ in hits)))
    path, text, first, last = hits[0]
    lines = [line.rstrip() for line in text.split('\n')[first:last + 1]]
    where = '%s, lines %d-%d' % (rel(path), first + 1, last + 1)
    header = {'c': '/* %s */', 'js': '// %s', 'py': '# %s'}[kind] % where
    return header, lines


def extract(entry, table, listing):
    if entry.get('kind') not in EXT:
        raise Failure('%s: the kind must be one of %s' % (entry, ', '.join(EXT)))
    if ('from' in entry or 'to' in entry) and entry['kind'] != 'asm':
        raise Failure('%s %s: from and to are for asm only' % (entry['kind'], entry['name']))
    if entry['kind'] == 'asm':
        header, lines = asm_extract(entry, table, listing)
    else:
        header, lines = source_extract(entry)
    limit = entry.get('lines', DEFAULT_LINES)
    if len(lines) > limit:
        raise Failure('%s %s: %d lines, more than the %d allowed; ask for more with `lines` '
                      'in book/listings.toml, or show a part' % (entry['kind'], entry['name'],
                                                                len(lines), limit))
    return '\n'.join([header] + lines) + '\n'


def generate(out):
    """Every listing of the manifest into `out`; returns how many."""
    entries = manifest('listings.toml').get('listing', [])
    table = routines()
    listing = LISTING.read_text(encoding='utf-8').split('\n')
    seen = set()
    for entry in entries:
        target = '%s/%s.%s' % (entry['kind'], entry.get('as', entry['name']), EXT.get(entry['kind']))
        if target in seen:
            raise Failure('%s is named twice in book/listings.toml' % target)
        seen.add(target)
        text = extract(entry, table, listing)
        path = pathlib.Path(out) / target
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding='utf-8', newline='\n')
    return len(entries)


def main():
    parser = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    parser.add_argument('--check', action='store_true',
                        help='compare a fresh extraction with the committed files, write nothing')
    parser.add_argument('--out', help='write into this directory instead')
    args = parser.parse_args()
    try:
        if args.check:
            with tempfile.TemporaryDirectory() as temp:
                count = generate(temp)
                problems = compare(temp, LISTINGS)
            for line in problems:
                print(line)
            print('listings  %d checked, %s' % (count, '%d differ' % len(problems) if problems
                                                 else 'all equal to the committed files'))
            return 1 if problems else 0
        if args.out:
            count = generate(args.out)
        else:
            with tempfile.TemporaryDirectory() as temp:
                count = generate(temp)
                replace_tree(temp, LISTINGS)
        print('listings  %d written to %s' % (count, args.out or rel(LISTINGS)))
        return 0
    except Failure as failure:
        print('listings  FAILED: %s' % failure, file=sys.stderr)
        return 2


if __name__ == '__main__':
    sys.exit(main())
