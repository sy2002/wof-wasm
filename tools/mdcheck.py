#!/usr/bin/env python3
"""Marked 2 / MathJax safety check for Markdown files: reports risky characters outside code.

    mdcheck.py FILE.md [...]

Flags, outside fenced blocks and inline code spans: bare $ (inline math), == (highlight),
< that could start an HTML tag, \\( \\[ (math delimiters), and * or _ that could open emphasis
inside a word or around numbers. Also flags language-tagged fences that contain apostrophes or
lines starting with #, which the syntax highlighter mangles.
"""
import re
import sys

LANG_OK = {'text', ''}


def check(path):
    problems = []
    in_fence, fence_lang, fence_start = False, '', 0
    for no, line in enumerate(open(path, encoding='utf-8'), 1):
        stripped = line.strip()
        m = re.match(r'^(```+|~~~+)\s*(\S*)', stripped)
        if m:
            if not in_fence:
                in_fence, fence_lang, fence_start = True, m.group(2).lower(), no
            else:
                in_fence = False
            continue
        if in_fence:
            if fence_lang not in LANG_OK:
                if "'" in line and fence_lang in ('bash', 'sh', 'shell', 'zsh'):
                    problems.append((no, 'apostrophe inside a %s fence (opened line %d)' % (fence_lang, fence_start)))
                if stripped.startswith('#') and fence_lang in ('bash', 'sh', 'shell', 'zsh', 'yaml') and not stripped.startswith('#!'):
                    pass                                  # genuine comments are fine
            continue
        prose = re.sub(r'`[^`]*`', '', line)
        for pat, what in ((r'(?<!\\)\$', 'bare $'), (r'(?<!\\)==', 'bare =='), (r'<(?=[A-Za-z/!])', 'bare <'),
                          (r'\\[(\[]', 'math delimiter'), (r'\w\*\w|\d \* \d', 'stray *'),
                          (r'(?<![\w`])_\w|\w_(?![\w`])|\w_\w', 'stray _')):
            if re.search(pat, prose):
                problems.append((no, '%s: %s' % (what, prose.strip()[:90])))
    if in_fence:
        problems.append((fence_start, 'unclosed fence'))
    return problems


if __name__ == '__main__':
    bad = 0
    for p in sys.argv[1:]:
        for no, msg in check(p):
            bad += 1
            print('%s:%d: %s' % (p, no, msg))
    print('%d problem(s)' % bad)
    sys.exit(1 if bad else 0)
