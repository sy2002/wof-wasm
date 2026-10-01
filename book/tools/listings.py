#!/usr/bin/env python3
"""The book's listings, extracted from the real sources by name.

    .venv/bin/python book/tools/listings.py            write book/docs/generated/listings/
    .venv/bin/python book/tools/listings.py --check    make them into a temporary directory and
                                                       compare with the committed files
    .venv/bin/python book/tools/listings.py --out DIR  write them into DIR instead

Reads the manifest book/listings.toml and writes one plain-text file per entry,
book/docs/generated/listings/<kind>/<name>.<ext>, from:

    asm  re/Wings.lst, a routine by its name in re/functions.csv: its lines from its start
         address to its end (or a part of it between two addresses), with `head` also the
         header the listing gives it (its kind, frame, far-call slot, comment and callers)
    skel the control-flow skeleton of a routine of re/Wings.lst, by its name: what
         tools/skel.py prints for it, run at build time
    c    src/*.c, a C function, or a variable at file scope, by its name, with the comment
         directly above it
    js   web/*.js, a function or a method by its name, with the comment directly above it
    py   tools/*.py, or the file an entry's `file` names (tests/ too), a function or a class by
         its name (a method as Class.method, a function inside a function as outer.inner), or a
         variable at module level by its name, with the comments directly above it; or a part of
         a function, from the first of its lines that holds the text `from` to the first line
         at or after it that holds the text `to`, dedented
    json a JSON file the entry's `file` names (a run description of tests/runs/, say), the
         whole of it, laid out one key of the top-level object a line and one element of a
         top-level list a line, so that a script of many short lists reads as one line each

The first line of every file names the source and the line range (or the address range), in
the comment syntax of its language (`//` for JSON, which the highlighter's JSON lexer takes),
so that a chapter shows where the extract comes from.  A
name that does not exist, or exists more than once without a `file` to choose, fails the run
with the name; so does an extract longer than its limit (40 lines, or the entry's `lines`).

Exit status: 0 done (or --check found the committed files equal), 1 --check found a
difference, 2 the manifest asks for something the sources do not have.
"""
import argparse
import ast
import csv
import json
import pathlib
import re
import subprocess
import sys
import tempfile

from common import LISTINGS, ROOT, Failure, compare, manifest, rel, replace_tree

DEFAULT_LINES = 40
EXT = {'asm': 'lst', 'skel': 'lst', 'c': 'c', 'js': 'js', 'py': 'py', 'json': 'json'}
SKEL = ROOT / 'tools' / 'skel.py'
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


def c_variables(text, name):
    """Every definition of the C variable `name` at file scope in one file, as (first line,
    last line): a declaration that begins its line, with or without an initialiser, up to the
    semicolon that ends it, with the comment directly above it."""
    code = masked(text)
    lines = text.split('\n')
    found = []
    pattern = r'(?m)^(?!extern\b)[A-Za-z_][\w \t*]*?[ \t*]%s\s*(?:\[[^\]\n]*\]\s*)*(?==|;)'
    for m in re.finditer(pattern % re.escape(name), code):
        depth, k = 0, m.end()
        while k < len(code) and not (code[k] == ';' and depth == 0):
            depth += {'{': 1, '}': -1}.get(code[k], 0)
            k += 1
        if k == len(code):
            continue
        first = line_of(text, m.start())
        found.append((with_comment_above(lines, first), line_of(text, k)))
    return found


def c_definitions(text, name):
    """The C function `name` or the variable `name` at file scope."""
    return c_functions(text, name) + c_variables(text, name)


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
    """Every function or class `name` in one file, or a method `Class.method`, or a function
    defined inside a function, `outer.inner`, with its decorators and the comment lines
    directly above it; or a variable at module level, an assignment to `name`, with the
    comment lines directly above it."""
    tree = ast.parse(text)
    lines = text.split('\n')
    kinds = (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)
    parts = name.split('.')
    if len(parts) == 2:
        owners = [n for n in ast.walk(tree) if isinstance(n, kinds) and n.name == parts[0]]
        nodes = [c for o in owners for c in o.body if isinstance(c, kinds) and c.name == parts[1]]
    else:
        nodes = [n for n in ast.walk(tree) if isinstance(n, kinds) and n.name == name]
        nodes += [n for n in tree.body if isinstance(n, (ast.Assign, ast.AnnAssign)) and
                  any(isinstance(t, ast.Name) and t.id == name
                      for t in (n.targets if isinstance(n, ast.Assign) else [n.target]))]
    found = []
    for node in nodes:
        first = min([node.lineno] + [d.lineno for d in getattr(node, 'decorator_list', [])]) - 1
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
    if entry.get('head'):
        if lo != start:
            raise Failure('asm %s: a head belongs to the routine\'s start, not to a part from '
                          '0x%06X' % (name, lo))
        while begin > 0 and listing[begin - 1].startswith(';') \
                and not listing[begin - 1].startswith('; ===='):
            begin -= 1                                   # the header the listing gives it
        if not listing[begin].startswith('; %s   [' % name):
            raise Failure('asm %s: no header of that name above 0x%06X in re/Wings.lst'
                          % (name, lo))
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


def skel_extract(entry, table):
    """What tools/skel.py prints for a routine, with a first line that names the command, the
    routine's address range and how many of its lines in the listing the skeleton keeps."""
    name = entry['name']
    row = table.get(name)
    if row is None:
        raise Failure('skel %s: no routine of that name in re/functions.csv' % name)

    def skel(*options):
        done = subprocess.run([sys.executable, str(SKEL), name, *options], cwd=ROOT,
                              capture_output=True, text=True)
        if done.returncode:
            raise Failure('skel %s: tools/skel.py failed: %s'
                          % (name, (done.stderr or done.stdout).strip()))
        return [line.rstrip() for line in done.stdout.rstrip('\n').split('\n')]

    lines, whole = skel(), skel('--all')
    addresses = [int(m.group(1), 16) for m in map(ADDRESS.match, whole) if m]
    if not addresses or addresses[0] != int(row['addr'], 16):
        raise Failure('skel %s: tools/skel.py did not print the routine at 0x%s'
                      % (name, row['addr'].upper()))
    header = '; tools/skel.py %s: re/Wings.lst 0x%06X-0x%06X, %d of its %d lines' % (
        name, addresses[0], addresses[-1], len(lines), len(whole))
    return header, lines


def source_extract(entry):
    kind, name = entry['kind'], entry['name']
    folder, glob = SOURCES[kind]
    if 'file' in entry:
        paths = [ROOT / entry['file']]
        if not paths[0].exists():
            raise Failure('%s %s: no file %s' % (kind, name, entry['file']))
    else:
        paths = sorted((ROOT / folder).glob(glob))
    finder = {'c': c_definitions, 'js': js_functions, 'py': py_definitions}[kind]
    hits = []
    for path in paths:
        text = path.read_text(encoding='utf-8')
        for first, last in finder(text, name):
            hits.append((path, text, first, last))
    if not hits:
        raise Failure('%s %s: no such %s in %s' % (
            kind, name, {'c': 'function or variable', 'js': 'function or method',
                         'py': 'function or class'}[kind],
            entry.get('file', '%s/%s' % (folder, glob))))
    if len(hits) > 1:
        raise Failure('%s %s: defined %d times (%s); name the file' % (
            kind, name, len(hits), ', '.join('%s:%d' % (rel(p), f + 1) for p, _, f, _ in hits)))
    path, text, first, last = hits[0]
    lines = [line.rstrip() for line in text.split('\n')[first:last + 1]]
    where = '%s, lines %d-%d' % (rel(path), first + 1, last + 1)
    if 'from' in entry or 'to' in entry:
        lo, hi = py_part(entry, lines)
        where = '%s, lines %d-%d, a part of %s (lines %d-%d)' % (
            rel(path), first + lo + 1, first + hi + 1, name, first + 1, last + 1)
        lines = dedented(lines[lo:hi + 1])
    header = {'c': '/* %s */', 'js': '// %s', 'py': '# %s'}[kind] % where
    return header, lines


def py_part(entry, lines):
    """The part of a Python definition an entry names by two texts: from the first line that
    holds `from` to the first line at or after it that holds `to`, both inclusive, as indices
    into the definition's lines."""
    name, start, stop = entry['name'], entry.get('from'), entry.get('to')
    if not isinstance(start, str) or not isinstance(stop, str):
        raise Failure('py %s: a part takes from and to, both texts of its lines' % name)
    lo = next((i for i, line in enumerate(lines) if start in line), None)
    if lo is None:
        raise Failure('py %s: no line holds %r' % (name, start))
    hi = next((i for i in range(lo, len(lines)) if stop in lines[i]), None)
    if hi is None:
        raise Failure('py %s: no line at or after %r holds %r' % (name, start, stop))
    return lo, hi


def dedented(lines):
    """The lines with the indentation they all share taken off, blank lines aside."""
    indents = [len(line) - len(line.lstrip(' ')) for line in lines if line.strip()]
    cut = min(indents) if indents else 0
    return [line[cut:] if line.strip() else '' for line in lines]


# ------------------------------------------------------------------ JSON

def json_extract(entry):
    """A JSON file, the whole of it, laid out by the book rather than by its writer: one key
    of the top-level object a line, and a top-level list one element a line, each element
    written compactly.  The extract must read back as the same data."""
    name = entry['name']
    if 'file' not in entry:
        raise Failure('json %s: a json entry names its file' % name)
    path = ROOT / entry['file']
    if not path.exists():
        raise Failure('json %s: no file %s' % (name, entry['file']))
    data = json.loads(path.read_text(encoding='utf-8'))
    if not isinstance(data, dict):
        raise Failure('json %s: %s is not a JSON object' % (name, entry['file']))

    def compact(value):
        return json.dumps(value, ensure_ascii=False, separators=(', ', ': '))

    lines = ['{']
    items = list(data.items())
    for i, (key, value) in enumerate(items):
        comma = ',' if i < len(items) - 1 else ''
        if isinstance(value, list) and value:
            lines.append('  %s: [' % compact(key))
            for j, element in enumerate(value):
                lines.append('    %s%s' % (compact(element), ',' if j < len(value) - 1 else ''))
            lines.append('  ]%s' % comma)
        else:
            lines.append('  %s: %s%s' % (compact(key), compact(value), comma))
    lines.append('}')
    if json.loads('\n'.join(lines)) != data:
        raise Failure('json %s: the laid-out extract does not read back as %s'
                      % (name, entry['file']))
    header = '// %s, the whole file, one entry a line' % rel(path)
    return header, lines


def extract(entry, table, listing):
    if entry.get('kind') not in EXT:
        raise Failure('%s: the kind must be one of %s' % (entry, ', '.join(EXT)))
    if 'head' in entry and entry['kind'] != 'asm':
        raise Failure('%s %s: head is for asm only' % (entry['kind'], entry['name']))
    if ('from' in entry or 'to' in entry) and entry['kind'] not in ('asm', 'py'):
        raise Failure('%s %s: from and to are for asm and py only' % (entry['kind'], entry['name']))
    if entry['kind'] == 'asm':
        header, lines = asm_extract(entry, table, listing)
    elif entry['kind'] == 'json':
        header, lines = json_extract(entry)
    elif entry['kind'] == 'skel':
        header, lines = skel_extract(entry, table)
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
