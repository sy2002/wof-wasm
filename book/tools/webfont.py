#!/usr/bin/env python3
"""The game's own font, newarmyfont, as the book's heading font.

    .venv/bin/python book/tools/webfont.py            write book/docs/fonts/wof-newarmy.woff
    .venv/bin/python book/tools/webfont.py --check    make it into a temporary directory and
                                                      compare with the committed file
    .venv/bin/python book/tools/webfont.py --out DIR  write it into DIR instead

The glyphs are read with the port's own decoding: original/disk/Wings_of_Fury/newarmyfont
as dist/wof.html packs it, loaded by the core's wof_font_load (orig 0x012794) and drawn one
character at a time by wof_text_render (orig 0x015956) through the native library, the way
tests/test_oracle_m1.py reaches them; the advance of each character is wof_text_width
(orig 0x01591E), its width plus one, and eleven for the space (re/notes/drawing.md, "Text").
The font is 12 rows high and has the characters 0x20 to 0x7E.

Each pixel of a glyph becomes a rectangle 60 units wide and 120 high, so that the letters keep
the shape they have on the screen they were drawn for: the game draws this font only on
high-resolution screens, whose pixels a PAL display shows 1.6 wide and 3 high, which is
rounded here to 1 : 2 so that the letters stand sharp at 24 and 48 CSS pixels.  The pixels of
a glyph are traced into the outline of their union, the outer contours clockwise and the
holes counter-clockwise, so that no seam shows between two neighbouring pixels at any size.
The baseline lies under the bottom row of the capitals, which the glyphs say is row 8.

Every run draws the font back with FreeType through Pillow at 24 pixels and compares each
glyph with the game's, pixel for pixel.  The file is deterministic: fixed names and
timestamps, and the same fontTools and zlib write the same bytes, which --check holds.

Exit status: 0 done (or --check found the committed file equal), 1 --check found a
difference, 2 the font could not be read or made.
"""
import argparse
import ctypes
import sys
import tempfile
from collections import Counter

from common import FONTS, Failure, compare, core, rel, replace_tree

FILE = 'wof-newarmy.woff'
FAMILY = 'WoF Newarmy'
PX_W, PX_H = 60, 120            # one font pixel in font units, 1 : 2 as a high-resolution pixel
ROWS = 12
TEMPLATE_W = 32                 # pixels: wider than the widest glyph (19)
# 2026-10-01 00:00:00 in the seconds since 1904 that the head table counts; a fixed value,
# so that two runs write the same bytes.
TIMESTAMP = 3873657600


class Glyph:
    def __init__(self, code, advance, rows):
        self.code, self.advance, self.rows = code, advance, rows      # rows: lists of 0 and 1

    def pixels(self):
        return [(x, r) for r, row in enumerate(self.rows) for x, bit in enumerate(row) if bit]


def game_font():
    """The font as the port decodes it: {character code: Glyph}, the advance in pixels."""
    lib = core().lib
    height = lib.wt_font_height()
    if height != ROWS:
        raise Failure('newarmyfont: the core reports a height of %d rows, not %d' % (height, ROWS))
    stride = (TEMPLATE_W + 15) // 16 * 2
    glyphs = {}
    for code in range(0x00, 0x100):
        char = bytes([code])
        advance = lib.wt_text_width(char, 1)
        if not advance:
            continue                                 # outside the font's first to last
        template = (ctypes.c_uint8 * (stride * ROWS))()
        width = lib.wt_text_render(char, 1, template, 0, 0, 0, TEMPLATE_W, ROWS)
        if width != advance:
            raise Failure('newarmyfont: character 0x%02X renders %d wide but advances %d'
                          % (code, width, advance))
        rows = [[(template[r * stride + x // 8] >> (7 - x % 8)) & 1 for x in range(TEMPLATE_W)]
                for r in range(ROWS)]
        glyphs[code] = Glyph(code, advance, rows)
    if sorted(glyphs) != list(range(0x20, 0x7F)):
        raise Failure('newarmyfont: expected the characters 0x20 to 0x7E, the core gives %s'
                      % ', '.join('0x%02X' % c for c in sorted(glyphs)))
    return glyphs


def baseline(glyphs):
    """The row under which the baseline lies: the bottom row most of the capitals end on."""
    bottoms = Counter(max(r for _, r in glyphs[c].pixels()) for c in range(ord('A'), ord('Z') + 1))
    return bottoms.most_common(1)[0][0]


def trace(pixels, base):
    """The outline of the union of the pixels, as closed contours of grid points (x, y), y up
    with 0 at the baseline: clockwise around the ink, counter-clockwise around a hole."""
    edges = set()
    for x, r in pixels:
        y = base - r                                  # the pixel spans y to y + 1
        square = [(x, y), (x, y + 1), (x + 1, y + 1), (x + 1, y)]
        for a, b in zip(square, square[1:] + square[:1]):
            if (b, a) in edges:
                edges.remove((b, a))                  # shared with a neighbour: inside
            else:
                edges.add((a, b))
    leaving = {}
    for a, b in edges:
        leaving.setdefault(a, []).append(b)
    contours = []
    while edges:
        start = min(edges)
        points, (a, b) = [start[0]], start
        while True:
            edges.remove((a, b))
            leaving[a].remove(b)
            if b == start[0]:
                break
            points.append(b)
            dx, dy = b[0] - a[0], b[1] - a[1]
            # Where two pixels touch only at a corner, turn right first, so that each keeps
            # a contour of its own instead of one that crosses itself.
            for tx, ty in ((dy, -dx), (dx, dy), (-dy, dx)):
                nxt = (b[0] + tx, b[1] + ty)
                if nxt in leaving.get(b, ()):
                    a, b = b, nxt
                    break
            else:
                raise Failure('tracing: an open contour at %s' % (b,))
        corners = []
        for i, p in enumerate(points):
            q, s = points[i - 1], points[(i + 1) % len(points)]
            if (p[0] - q[0]) * (s[1] - p[1]) != (p[1] - q[1]) * (s[0] - p[0]):
                corners.append(p)
        contours.append(corners)
    return contours


def build(glyphs, path):
    from fontTools.fontBuilder import FontBuilder
    from fontTools.pens.ttGlyphPen import TTGlyphPen

    base = baseline(glyphs)                    # rows 0 to base stand on the baseline
    ascent, descent = (base + 1) * PX_H, (ROWS - base - 1) * PX_H
    order = ['.notdef'] + ['space' if c == 0x20 else 'uni%04X' % c for c in sorted(glyphs)]
    cmap = {c: ('space' if c == 0x20 else 'uni%04X' % c) for c in sorted(glyphs)}
    outlines, metrics = {}, {}

    pen = TTGlyphPen(None)                     # .notdef: a frame the size of a capital
    for contour in ([(0, 0), (0, base + 1), (8, base + 1), (8, 0)],
                    [(1, 1), (7, 1), (7, base), (1, base)]):
        pen.moveTo((contour[0][0] * PX_W, contour[0][1] * PX_H))
        for x, y in contour[1:]:
            pen.lineTo((x * PX_W, y * PX_H))
        pen.closePath()
    outlines['.notdef'], metrics['.notdef'] = pen.glyph(), (9 * PX_W, 0)

    for code in sorted(glyphs):
        glyph, name = glyphs[code], cmap[code]
        pen = TTGlyphPen(None)
        for contour in trace(glyph.pixels(), base):
            pen.moveTo((contour[0][0] * PX_W, contour[0][1] * PX_H))
            for x, y in contour[1:]:
                pen.lineTo((x * PX_W, y * PX_H))
            pen.closePath()
        outlines[name] = pen.glyph()
        left = min((x for x, _ in glyph.pixels()), default=0)
        metrics[name] = (glyph.advance * PX_W, left * PX_W)

    x_height = (base + 1 - min(r for _, r in glyphs[ord('x')].pixels())) * PX_H
    builder = FontBuilder(unitsPerEm=ROWS * PX_H, isTTF=True)
    builder.updateHead(created=TIMESTAMP, modified=TIMESTAMP, fontRevision=1.0)
    builder.setupGlyphOrder(order)
    builder.setupCharacterMap(cmap)
    builder.setupGlyf(outlines)
    builder.setupHorizontalMetrics(metrics)
    builder.setupHorizontalHeader(ascent=ascent, descent=-descent, lineGap=0)
    builder.setupNameTable({
        'copyright': 'The glyphs are the font newarmyfont of Wings of Fury (Broderbund, 1990): '
                     'the game\'s data, kept for preservation, no right to it granted.',
        'familyName': FAMILY,
        'styleName': 'Regular',
        'uniqueFontIdentifier': '%s Regular 1.000' % FAMILY,
        'fullName': '%s Regular' % FAMILY,
        'version': 'Version 1.000',
        'psName': FAMILY.replace(' ', '') + '-Regular',
        'description': 'Made from the game\'s data by book/tools/webfont.py; one pixel is one '
                       'rectangle of 60 by 120 units.',
    })
    builder.setupOS2(sTypoAscender=ascent, sTypoDescender=-descent, sTypoLineGap=0,
                     usWinAscent=ascent, usWinDescent=descent, sxHeight=x_height,
                     sCapHeight=ascent, fsSelection=0x00C0, achVendID='NONE', fsType=0,
                     version=4)
    builder.setupPost(keepGlyphNames=False)
    builder.font.flavor = 'woff'
    builder.save(str(path))


def verify(path, glyphs):
    """The font drawn back at 24 CSS pixels, where one font pixel is one device pixel wide and
    two high, with FreeType through Pillow: every glyph must come out as exactly its pixels
    of the game's font, two rows per row, with no grey edge anywhere."""
    from PIL import Image, ImageDraw, ImageFont
    font = ImageFont.truetype(str(path), ROWS * 2)
    for code, glyph in sorted(glyphs.items()):
        image = Image.new('L', (TEMPLATE_W + 16, ROWS * 2 + 16), 0)
        ImageDraw.Draw(image).text((8, 8), chr(code), font=font, fill=255)
        seen = image.load()
        ink = {(x, y) for y in range(image.height) for x in range(image.width) if seen[x, y]}
        if any(seen[x, y] != 255 for x, y in ink):
            raise Failure('the web font draws a grey edge on character 0x%02X' % code)
        want = {(x, 2 * r + k) for x, r in glyph.pixels() for k in (0, 1)}
        if want and ink:
            dx = min(x for x, _ in ink) - min(x for x, _ in want)
            dy = min(y for _, y in ink) - min(y for _, y in want)
            want = {(x + dx, y + dy) for x, y in want}
        if want != ink:
            raise Failure('the web font draws character 0x%02X otherwise than the game' % code)


def generate(out):
    """The web font into `out`, drawn back and compared with the game's glyphs."""
    import pathlib
    out = pathlib.Path(out)
    out.mkdir(parents=True, exist_ok=True)
    glyphs = game_font()
    build(glyphs, out / FILE)
    verify(out / FILE, glyphs)
    return out / FILE


def main():
    parser = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    parser.add_argument('--check', action='store_true',
                        help='compare a fresh font with the committed file, write nothing')
    parser.add_argument('--out', help='write into this directory instead')
    args = parser.parse_args()
    try:
        if args.check:
            with tempfile.TemporaryDirectory() as temp:
                generate(temp)
                problems = compare(temp, FONTS)
            for line in problems:
                print(line)
            print('font      %s' % ('%d differ' % len(problems) if problems
                                    else '%s equal to the committed file' % FILE))
            return 1 if problems else 0
        if args.out:
            path = generate(args.out)
        else:
            with tempfile.TemporaryDirectory() as temp:
                generate(temp)
                replace_tree(temp, FONTS)
            path = FONTS / FILE
        print('font      %s, %d bytes' % (rel(path) if not args.out else path,
                                          path.stat().st_size))
        return 0
    except Failure as failure:
        print('font      FAILED: %s' % failure, file=sys.stderr)
        return 2


if __name__ == '__main__':
    sys.exit(main())
