#!/usr/bin/env python3
"""The book's build, in order, in one command.

    .venv/bin/python book/tools/build.py               generate, then mkdocs build --strict into book/site/
    .venv/bin/python book/tools/build.py --no-figures  the same, keeping the committed figures
    .venv/bin/python book/tools/build.py --check       remake the generated files into a temporary
                                                       directory and compare them with the committed
                                                       ones; nothing is written
    .venv/bin/python book/tools/build.py --serve       generate, then mkdocs serve

The steps, one line each:

    listings  book/tools/listings.py: the listings of book/listings.toml from the real sources
    figures   book/tools/figures.py: the figures of book/figures.toml through the native library
    elements  book/tools/elements.py: the data of the shape browser and the map viewer from the
              game's files
    font      book/tools/webfont.py: the game's font as the web font of the headings
    suite     book/tools/suite.py: the suite's test modules by layer, from pytest's collection,
              the layers book/suite.toml's
    colours   every colour of docs/stylesheets/book.css and of the diagrams docs/figures/*.svg against
              the palette entry its comment names
    links     book/tools/links.py: every repo: link of the pages resolves, to a file or directory
    refs      and a heading by GitHub's anchor; no code span names a repository file unlinked;
    glossary  every glossary entry's chapter line is what the chapters say, every term in bold
    external  a link to its entry; every link out of the repository is https
    page      dist/wof.html, the repository's game, which hooks/game.py copies into the site
    site      mkdocs build --strict in book/, and the game in the site compared with dist/wof.html

The generators need the built repository (tools/build.py --native: dist/wof.html and
tests/libwofcore.dylib) and run on macOS, all but elements.py, which reads only the disk's
files, and suite.py, which needs only pytest's collection of tests/; what they make is committed, so that mkdocs alone needs only the packages of
book/requirements.txt.  book/site/ is never committed.

Exit status:
    0  done; with --check, every generated file and every colour equal to what its source makes
    1  a generated file or a colour differs from what its source makes
    2  a generator could not make what its manifest asks for, or the build lacks something
    3  mkdocs build --strict failed; its output is printed
    4  a page fails the book's checks of its links, references and glossary (links.py)
"""
import argparse
import hashlib
import os
import re
import subprocess
import sys

import links
from common import BOOK, DOCS, PAGE, ROOT, rel

TOOLS = BOOK / 'tools'
SITE = BOOK / 'site'
STYLESHEET = DOCS / 'stylesheets' / 'book.css'
COLOUR = re.compile(r'(#[0-9A-Fa-f]{6});\s*/\*\s*([\w.\-]+) (\d+)\s*\*/')


def tool(name, *args):
    """One generator in a process of its own (the native core keeps its state per process);
    its lines are printed, its exit status returned."""
    finished = subprocess.run([sys.executable, str(TOOLS / name), *args], cwd=ROOT,
                              capture_output=True, text=True)
    for line in (finished.stdout + finished.stderr).splitlines():
        print(line)
    return finished.returncode


def colours():
    """The design's colours, in the stylesheet and in the hand-drawn diagrams, against the
    game's palettes: 0 equal, 1 one differs."""
    from figures import palette
    files = [STYLESHEET] + sorted((DOCS / 'figures').glob('*.svg'))
    wrong, total = [], 0
    for path in files:
        found = COLOUR.findall(path.read_text(encoding='utf-8'))
        total += len(found)
        for value, name, index in found:
            entries = palette(name)
            actual = '#%02X%02X%02X' % entries[int(index)] if int(index) < len(entries) else None
            if actual != value.upper():
                wrong.append('differs  %s: %s is not %s entry %s (%s)' % (rel(path), value, name,
                                                                         index, actual))
    for line in wrong:
        print(line)
    print('colours   %d of %s checked against the palettes, %s'
          % (total, ', '.join(rel(p) for p in files), '%d differ' % len(wrong) if wrong else 'all equal'))
    return 1 if wrong else 0


def sha1(path):
    return hashlib.sha1(path.read_bytes()).hexdigest()


def page():
    """The game the site embeds: present, and whether it is the committed page."""
    if not PAGE.exists():
        print('page      FAILED: %s is missing (git checkout dist/wof.html)' % rel(PAGE))
        return 2
    committed = subprocess.run(['git', 'rev-parse', 'HEAD:dist/wof.html'], cwd=ROOT,
                               capture_output=True, text=True).stdout.strip()
    on_disk = subprocess.run(['git', 'hash-object', str(PAGE)], cwd=ROOT,
                             capture_output=True, text=True).stdout.strip()
    print('page      %s, %d bytes, SHA-1 %s, %s' % (
        rel(PAGE), PAGE.stat().st_size, sha1(PAGE),
        'the committed page' if committed == on_disk else 'NOT the committed page (a local build)'))
    return 0


def mkdocs(command):
    environment = dict(os.environ, NO_MKDOCS_2_WARNING='1')
    return [sys.executable, '-m', 'mkdocs', command], environment


def site():
    command, environment = mkdocs('build')
    finished = subprocess.run(command + ['--strict'], cwd=BOOK, env=environment,
                              capture_output=True, text=True)
    if finished.returncode:
        print(finished.stdout + finished.stderr)
        print('site      FAILED: mkdocs build --strict')
        return 3
    copied = SITE / 'play' / 'wof.html'
    if not copied.exists() or copied.read_bytes() != PAGE.read_bytes():
        print('site      FAILED: %s is not dist/wof.html' % rel(copied))
        return 3
    pages = sum(1 for _ in SITE.rglob('index.html'))
    print('site      %s/, %d pages, mkdocs build --strict without a warning; %s is dist/wof.html'
          % (rel(SITE), pages, rel(copied)))
    return 0


def main():
    parser = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    group = parser.add_mutually_exclusive_group()
    group.add_argument('--check', action='store_true',
                       help='compare the generated files with a fresh generation, write nothing')
    group.add_argument('--serve', action='store_true',
                       help='generate, then run mkdocs serve instead of mkdocs build')
    parser.add_argument('--no-figures', action='store_true',
                        help='keep the committed figures instead of rendering them again')
    args = parser.parse_args()

    if args.check:
        results = [tool('listings.py', '--check'), tool('figures.py', '--check'),
                   tool('elements.py', '--check'), tool('webfont.py', '--check'),
                   tool('suite.py', '--check'), colours(),
                   links.run()]
        return max(results)

    for step in (['listings.py'], None if args.no_figures else ['figures.py'], ['elements.py'],
                 ['webfont.py'], ['suite.py']):
        if step is None:
            print('figures   kept as committed (--no-figures)')
            continue
        status = tool(*step)
        if status:
            return status
    status = colours() or links.run() or page()
    if status:
        return status
    if args.serve:
        command, environment = mkdocs('serve')
        return subprocess.call(command, cwd=BOOK, env=environment)
    return site()


if __name__ == '__main__':
    sys.exit(main())
