#!/usr/bin/env python3
"""The book's checks of its own pages: the links into the repository, the references that
should be links, the glossary's chapter lines and the links out of the repository.

    .venv/bin/python book/tools/links.py                  every check, one line each
    .venv/bin/python book/tools/links.py --fix-glossary   write each glossary entry's chapter
                                                          line as the chapters give it, then check

The checks read the pages under book/docs/ (the generated files left out) and the repository
beside them, and nothing else: no network, no ROM, no native library.

    links     every repo: link resolves (an underscore written %5F, as tools/mdcheck.py needs):
              its file or directory exists in the repository; an
              anchor names a heading of a Markdown file by GitHub's slug rule; no anchor points
              into any other kind of file
    refs      no code span names a repository file (one beginning with src/, web/, tools/,
              tests/, re/, book/, original/, dist/ or ref/, or naming SPEC.md, README.md,
              CLAUDE.md, CONTROLLER.md or LICENSE) without being the text of a repo: link
    glossary  every entry's line, "First met in chapter N, defined in chapter M." or "First
              met and defined in chapter N.", is what the chapters say: the defining chapter is
              the one that sets the term in bold, the first-met chapter the lowest-numbered one
              that sets it in bold or links to its entry; a term in bold is a link to its entry;
              no term is set in bold without an entry, and none in two chapters
    external  every link out of the repository is https, and the links of a glossary entry's
              "Elsewhere:" line carry no code span

How a bold is read: its text matches an entry's heading without regard to case, with a
trailing s, es or (for a y) ies allowed, and with a parenthesis at the end of the heading
left out ("int (the C type)" is matched by "int"). A bold that opens a list item is a label:
with a leading "the", "a" or "an" and its closing punctuation taken off it may define a term,
and if it matches none it is a label and nothing more.  Headings and fenced blocks are not read.

Exit status: 0 every check holds; 4 a check fails, its problems listed one line each.
"""
import argparse
import re
import sys
from urllib.parse import unquote

from common import BOOK, DOCS, ROOT

REPO_PREFIXES = ('src/', 'web/', 'tools/', 'tests/', 're/', 'book/', 'original/', 'dist/', 'ref/')
REPO_DOCUMENTS = re.compile(r'(?<![\w.])(SPEC\.md|README\.md|CLAUDE\.md|CONTROLLER\.md|LICENSE)')
LINK = re.compile(r'\[((?:[^\[\]\n]|\[[^\[\]\n]*\])*)\]\(([^()\s]+)\)')
CODE = re.compile(r'`([^`\n]+)`')
BOLD = re.compile(r'\*\*([^*\n]+?)\*\*')
FENCE = re.compile(r'^\s*(```|~~~)')
HEADING = re.compile(r'^(#{1,6})\s+(.*?)\s*#*\s*$')
ITEM_START = re.compile(r'^\s*(?:[-*+]|\d+\.)\s+\[?$')
NAV = re.compile(r'^\s*- "(\d+)\. [^"]*": (part-\d/[\w-]+\.md)\s*$')
GLOSSARY_LINK = re.compile(r'glossary\.md#([\w-]+)')
LINE = re.compile(r'^(?:Introduced in \[chapter \d+\]\([^)]*\)\.'
                  r'|First met and defined in \[chapter \d+\]\([^)]*\)\.'
                  r'|First met in \[chapter \d+\]\([^)]*\), defined in \[chapter \d+\]\([^)]*\)\.)')
GLOSSARY = DOCS / 'glossary.md'


# ------------------------------------------------------------------ reading a page

def pages():
    """Every page of the book, as paths under docs/, the generated files left out."""
    return sorted(p for p in DOCS.rglob('*.md') if 'generated' not in p.relative_to(DOCS).parts)


def text_lines(path):
    """The lines of a page that are prose: front matter and fenced blocks left out, with
    their line numbers."""
    lines = path.read_text(encoding='utf-8').split('\n')
    out, fenced, start = [], False, 0
    if lines and lines[0].strip() == '---':
        start = next((i for i in range(1, len(lines)) if lines[i].strip() == '---'), 0) + 1
    for number, line in enumerate(lines[start:], start + 1):
        if FENCE.match(line):
            fenced = not fenced
            continue
        if not fenced:
            out.append((number, line))
    return out


def github_slug(text):
    """The anchor GitHub gives a heading: its inline markup rendered to text, lowercased,
    punctuation dropped but hyphens and underscores, every space a hyphen."""
    text = re.sub(r'`([^`]*)`', r'\1', text)
    text = re.sub(r'\[([^\]]*)\]\([^)]*\)', r'\1', text)
    text = re.sub(r'\*\*(.+?)\*\*', r'\1', text)
    text = re.sub(r'(?<![\w*])\*(\S(?:.*?\S)?)\*(?![\w*])', r'\1', text)
    text = re.sub(r'[^\w\- ]', '', text.strip().lower())
    return text.replace(' ', '-')


_anchors = {}


def markdown_anchors(path):
    """Every anchor GitHub makes for the headings of a Markdown file, a repeated heading
    suffixed -1, -2 and so on."""
    if path not in _anchors:
        seen, found = {}, set()
        fenced = False
        for line in path.read_text(encoding='utf-8').split('\n'):
            if FENCE.match(line):
                fenced = not fenced
                continue
            m = None if fenced else HEADING.match(line)
            if not m:
                continue
            slug = github_slug(m.group(2))
            if slug in seen:
                seen[slug] += 1
                found.add('%s-%d' % (slug, seen[slug]))
            else:
                seen[slug] = 0
                found.add(slug)
        _anchors[path] = found
    return _anchors[path]


def links_in(line):
    """The links of a line: (text, target, start, end)."""
    return [(m.group(1), m.group(2), m.start(), m.end()) for m in LINK.finditer(line)]


# ------------------------------------------------------------------ the checks

def check_links():
    """Every repo: link resolves."""
    problems, count, where = [], 0, set()
    for path in pages():
        for number, line in text_lines(path):
            for _, target, _, _ in links_in(line):
                if not target.startswith('repo:'):
                    continue
                count += 1
                where.add(path)
                at = '%s:%d' % (path.relative_to(BOOK.parent), number)
                file, _, anchor = unquote(target[5:]).partition('#')
                full = ROOT / file if file else ROOT
                if not full.exists():
                    problems.append('%s: %s does not exist in the repository' % (at, file))
                elif file.endswith('/') and not full.is_dir():
                    problems.append('%s: %s is not a directory' % (at, file))
                elif anchor and (full.is_dir() or full.suffix != '.md'):
                    problems.append('%s: %s has an anchor, #%s, but is not a Markdown file; '
                                    'link the file without one' % (at, file, anchor))
                elif anchor and anchor not in markdown_anchors(full):
                    problems.append('%s: %s has no heading whose anchor is #%s'
                                    % (at, file, anchor))
    line = 'links     %d repo: links in %d pages, %s' % (
        count, len(where), '%d do not resolve' % len(problems) if problems else 'every one resolves')
    return problems, line


def looks_like_repository(span):
    return span.startswith(REPO_PREFIXES) or bool(REPO_DOCUMENTS.search(span))


def check_references():
    """No code span names a repository file without being a repo: link's text."""
    problems, spans, scanned = [], 0, 0
    for path in pages():
        scanned += 1
        for number, line in text_lines(path):
            linked = [(start, end) for text, target, start, end in links_in(line)
                      if target.startswith('repo:')]
            for m in CODE.finditer(line):
                if not looks_like_repository(m.group(1)):
                    continue
                spans += 1
                if not any(start < m.start() < end for start, end in linked):
                    problems.append('%s:%d: `%s` names a repository file but is not a repo: link'
                                    % (path.relative_to(BOOK.parent), number, m.group(1)))
    line = 'refs      %d references to repository files in %d pages, %s' % (
        spans, scanned, '%d not linked' % len(problems) if problems else 'every one a repo: link')
    return problems, line


def chapters():
    """The chapters in the navigation: {number: page path relative to docs/}."""
    found = {}
    for line in (BOOK / 'mkdocs.yml').read_text(encoding='utf-8').split('\n'):
        m = NAV.match(line)
        if m:
            found[int(m.group(1))] = m.group(2)
    return found


def entries():
    """The glossary's entries, in order: [(heading, anchor, key, chapter line number or None,
    the anchor of the entry it points to with "see", or None)]."""
    from markdown.extensions.toc import slugify
    lines = GLOSSARY.read_text(encoding='utf-8').split('\n')
    found = []
    for i, line in enumerate(lines):
        if line.startswith('### '):
            heading = line[4:].strip()
            key = re.sub(r'\s*\([^)]*\)$', '', heading).lower()
            j = i + 1
            while j < len(lines) and not lines[j].startswith('### ') and not LINE.match(lines[j]):
                j += 1
            pointer = re.search(r'see \[[^\]]*\]\(#([\w-]+)\)', '\n'.join(lines[i + 1:j]))
            found.append((heading, slugify(heading, '-'), key,
                          j if j < len(lines) and LINE.match(lines[j]) else None,
                          pointer.group(1) if pointer else None))
    return found


STUB_WORDS = 500


def stubs():
    """The chapters not written yet: pages of fewer than STUB_WORDS words, where a chapter has
    3,000 or more (book/BOOK.md, section 4, point 2)."""
    return {number for number, page in chapters().items()
            if not (DOCS / page).exists()
            or len((DOCS / page).read_text(encoding='utf-8').split()) < STUB_WORDS}


def matches(text, key, label):
    text = text.strip().rstrip('.,:;').strip().lower()
    if label:
        text = re.sub(r'^(the|a|an)\s+', '', text)
    return (text in (key, key + 's', key + 'es')
            or (key.endswith('y') and text == key[:-1] + 'ies'))


def glossary_reading():
    """What the chapters say of every entry: {anchor: (defining chapters, first-met chapters)},
    with the problems of the bold terms found on the way."""
    table = entries()
    by_anchor = {anchor: (heading, key) for heading, anchor, key, _, _ in table}
    defined = {anchor: set() for anchor in by_anchor}
    met = {anchor: set() for anchor in by_anchor}
    problems, bolds = [], 0
    for number, page in sorted(chapters().items()):
        path = DOCS / page
        if not path.exists():
            continue
        for line_number, line in text_lines(path):
            at = '%s:%d' % (path.relative_to(BOOK.parent), line_number)
            if HEADING.match(line):
                continue
            links = links_in(line)
            for m in GLOSSARY_LINK.finditer(line):
                if m.group(1) in met:
                    met[m.group(1)].add(number)
                else:
                    problems.append('%s: a link to the glossary entry #%s, which does not exist'
                                    % (at, m.group(1)))
            for m in BOLD.finditer(line):
                text = m.group(1)
                label = bool(ITEM_START.match(line[:m.start()]))
                hits = [anchor for anchor, (_, key) in by_anchor.items() if matches(text, key, label)]
                if not hits:
                    if not label:
                        problems.append('%s: **%s** is set in bold but has no glossary entry'
                                        % (at, text))
                    continue
                bolds += 1
                anchor = hits[0]
                defined[anchor].add(number)
                met[anchor].add(number)
                inside = [target for _, target, start, end in links
                          if start <= m.start() and m.end() <= end]
                glossary_targets = [GLOSSARY_LINK.search(t) for t in inside]
                glossary_targets = [g.group(1) for g in glossary_targets if g]
                if not glossary_targets:
                    problems.append('%s: **%s** is a term in bold but not a link to its entry, '
                                    '../glossary.md#%s' % (at, text, anchor))
                elif glossary_targets[0] != anchor:
                    problems.append('%s: **%s** links to #%s, but its entry is #%s'
                                    % (at, text, glossary_targets[0], anchor))
    return table, defined, met, problems, bolds


def expected_line(first, defining, pages_by_number):
    if first == defining:
        return 'First met and defined in [chapter %d](%s).' % (first, pages_by_number[first])
    return 'First met in [chapter %d](%s), defined in [chapter %d](%s).' % (
        first, pages_by_number[first], defining, pages_by_number[defining])


def stated_chapter(line):
    """The defining chapter an entry's line names: the last chapter number in it."""
    numbers = re.findall(r'\[chapter (\d+)\]', line)
    return int(numbers[-1]) if numbers else None


def check_glossary(fix=False):
    """Every entry's chapter line against the chapters.  Two kinds of entry take their
    defining chapter from elsewhere: one that points to another entry with "see" takes that
    entry's, and one whose line names a chapter not written yet keeps that chapter, as long
    as no written chapter sets the term in bold."""
    table, defined, met, problems, bolds = glossary_reading()
    pages_by_number = chapters()
    not_written = stubs()
    lines = GLOSSARY.read_text(encoding='utf-8').split('\n')
    corrected = []
    for heading, anchor, key, line_index, pointer in table:
        if line_index is None:
            problems.append('glossary: %s has no chapter line' % heading)
            continue
        defining = set(defined[anchor])
        if not defining and pointer and defined.get(pointer):
            defining = set(defined[pointer])
        if not defining:
            stated = stated_chapter(lines[line_index])
            if stated in not_written:
                defining = {stated}
            else:
                problems.append('glossary: %s is set in bold in no chapter' % heading)
                continue
        if len(defining) > 1:
            problems.append('glossary: %s is set in bold in chapters %s; a term is defined once'
                            % (heading, ', '.join(map(str, sorted(defining)))))
        want = expected_line(min(met[anchor] | defining), min(defining), pages_by_number)
        have = LINE.match(lines[line_index]).group(0)
        if have != want:
            if fix:
                lines[line_index] = want + lines[line_index][len(have):]
                corrected.append('%s: %s' % (heading, want))
            else:
                problems.append('glossary: %s says "%s", the chapters say "%s"'
                                % (heading, have, want))
    if fix and corrected:
        GLOSSARY.write_text('\n'.join(lines), encoding='utf-8')
    line = 'glossary  %d entries against chapters %d to %d, %d terms in bold, %s' % (
        len(table), min(pages_by_number), max(pages_by_number), bolds,
        '%d problems' % len(problems) if problems else
        'every chapter line true and every bold term a link to its entry')
    return problems, line, corrected


def check_external():
    """Every link out of the repository is https; an Elsewhere line carries no code span."""
    problems, count = [], 0
    for path in pages():
        for number, line in text_lines(path):
            at = '%s:%d' % (path.relative_to(BOOK.parent), number)
            for text, target, _, _ in links_in(line):
                if re.match(r'^[a-z]+://', target) or target.startswith('www.'):
                    count += 1
                    if not target.startswith('https://'):
                        problems.append('%s: %s is not https' % (at, target))
                    if line.startswith('Elsewhere:') and '`' in text:
                        problems.append('%s: the Elsewhere link [%s] has a code span' % (at, text))
    line = 'external  %d links out of the repository, %s' % (
        count, '%d malformed' % len(problems) if problems else 'all https')
    return problems, line


def run(fix_glossary=False, log=print):
    """Every check; returns 0 or 4."""
    failed = False
    for check in (check_links, check_references,
                  lambda: check_glossary(fix_glossary)[:2], check_external):
        problems, line = check()
        for problem in problems:
            log('          ' + problem)
        log(line)
        failed = failed or bool(problems)
    return 4 if failed else 0


def main():
    parser = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    parser.add_argument('--fix-glossary', action='store_true',
                        help="write the glossary entries' chapter lines as the chapters give them")
    args = parser.parse_args()
    if args.fix_glossary:
        _, _, corrected = check_glossary(fix=True)
        for line in corrected:
            print('corrected ' + line)
    return run()


if __name__ == '__main__':
    sys.exit(main())
