#!/usr/bin/env python3
"""The book's figures, rendered from the game's data by the port and the repository's tools.

    .venv/bin/python book/tools/figures.py              every figure into book/docs/generated/figures/
    .venv/bin/python book/tools/figures.py NAME ...     only these
    .venv/bin/python book/tools/figures.py --check      make every figure into a temporary directory
                                                        and compare with the committed files
    .venv/bin/python book/tools/figures.py --out DIR    write into DIR instead

Reads the manifest book/figures.toml, which names each figure with what it shows, how it is
made and the command that remakes it, and writes PNG files:

    screen     the port's picture at a VBlank of a run of the native core
               (tests/libwofcore.dylib through tests/conftest.py's Ported, on the files packed
               into dist/wof.html), through its per-row palettes with tests/m4_renders.py's
               picture(), scaled into the PAL box
    palettes   the per-row palettes of that picture, one labelled band per run of rows
    shapes     a contact sheet of a shape container with tools/ppkc.py
    map        a map's drawn records with tools/map_decode.py and the shapes of tools/ppkc.py
    font       a specimen of the game's font, drawn by the core's text_render
    planes     one shape of a container taken apart into its stored planes with tools/ppkc.py,
               and put together again as colour numbers and through a palette
    sample     a sound effect's file as a waveform, the whole and a stretch enlarged

It needs the built repository (tools/build.py --native: dist/wof.html and the native library)
and runs on macOS, as the tests do; never the ROM at the time the site is built, because the
images are committed.  The figures are deterministic: two runs write the same bytes (a PNG of
Pillow carries no time), which --check holds.

Exit status: 0 done (or --check found the committed files equal), 1 --check found a
difference, 2 a figure could not be made.
"""
import argparse
import ctypes
import os
import pathlib
import sys
import tempfile

from common import FIGURES, ROOT, Failure, compare, core, manifest, rel, replace_tree

DISK = ROOT / 'original' / 'disk' / 'Wings_of_Fury'
SHAPES = DISK / 'shapes'
FIRE = 16                       # the raw controller byte of fire (tests/runs/, title_shot)
LABEL = (200, 200, 200)         # the label colour and background of tools/ppkc.py's sheets
GROUND = (40, 40, 48)
PANEL = (16, 16, 20)            # the box of a shape or a waveform on that background
AXIS = (90, 90, 104)            # a zero line, a tick


def ppkc():
    import ppkc
    return ppkc


def palette(name):
    """A palette file's or picture's colours as (r, g, b), each 4-bit component widened as
    tools/ppkc.py's load_cmap widens it: as many as the CMAP chunk holds, at most 32, as
    iff_cmap_to_table takes them.  The bare palette files (wingspalette, night.p, ...) carry
    no valid length, and cmap_file_to_table takes 32 from them whatever it says
    (re/notes/display.md, "How colours change"); so does this."""
    import rpck
    raw, _ = rpck.load(str(SHAPES / name))
    at = raw.find(b'CMAP')
    if at < 0:
        raise Failure('%s has no CMAP chunk' % name)
    count = min(int.from_bytes(raw[at + 4:at + 8], 'big') // 3, 32)
    body = raw[at + 8:at + 8 + 3 * count]
    return [tuple((b >> 4) * 17 for b in body[i:i + 3]) for i in range(0, 3 * count, 3)]


def text(draw, at, words):
    draw.text(at, words, fill=LABEL, font=ppkc().FONT)


# ------------------------------------------------------------------ the runs of the core

def raw_input(spec, vblank, lib):
    """The raw controller byte of one VBlank of a run."""
    if 'fire_from' in spec:
        return FIRE if spec['fire_from'] <= vblank < spec['fire_from'] + spec['fire_held'] else 0
    if 'fire_every' in spec:
        if lib.wt_mission_count():
            return 0
        held = (vblank - 1) % spec['fire_every'] >= spec['fire_every'] - spec['fire_held']
        return FIRE if held else 0
    raise Failure('a run needs fire_from or fire_every: %s' % spec)


def capture(lib, width, height):
    """The core's present picture: the indexed framebuffer, each row's palette and the
    palettes, read the way tests/m4_renders.py's picture() reads them."""
    lib.wof_framebuffer.restype = ctypes.c_void_p
    lib.wof_palette_rows.restype = ctypes.c_void_p
    lib.wof_palettes.restype = ctypes.c_void_p
    fb = ctypes.string_at(lib.wof_framebuffer(), width * height)
    rows = ctypes.string_at(lib.wof_palette_rows(), height * 2)
    count = lib.wof_palette_colours()
    pal = ctypes.string_at(lib.wof_palettes(), lib.wof_palette_count() * count * 4)
    rows = [int.from_bytes(rows[2 * y:2 * y + 2], 'little') for y in range(height)]
    palettes = [[tuple(pal[(p * count + c) * 4:(p * count + c) * 4 + 3]) for c in range(count)]
                for p in range(lib.wof_palette_count())]
    return fb, rows, palettes


def run_core(name, spec, wanted):
    """One run of the core from its start; at each wanted VBlank the picture (an RGB image of
    640 x 214) and its raw parts.  Returns {vblank: (image, framebuffer, rows, palettes)}."""
    from m4_renders import picture
    ported = core()
    ported.reset_core()
    lib = ported.lib
    lib.wof_set_video_hz(50)
    out, last = {}, max(wanted)
    for vblank in range(1, last + 1):
        lib.wof_vblank(raw_input(spec, vblank, lib))
        lib.wof_pass()
        if 'mission_at' in spec and lib.wt_mission_count() and 'begun' not in out:
            out['begun'] = vblank
            if vblank != spec['mission_at']:
                raise Failure('run %s: the mission began at VBlank %d, the manifest says %d'
                              % (name, vblank, spec['mission_at']))
        if vblank in wanted:
            image = picture(ported)
            width, height = image.size
            out[vblank] = (image,) + capture(lib, width, height)
    if 'mission_at' in spec and 'begun' not in out:
        raise Failure('run %s: no mission began within %d VBlanks' % (name, last))
    return out


# ------------------------------------------------------------------ the makers

def make_screen(figure, shot, path):
    from PIL import Image
    image = shot[0].resize(tuple(figure['size']), Image.NEAREST)
    image.save(path)


def palette_file_of(colours, files):
    """The palette file whose colours the band's palette carries in its first entries."""
    for name in files:
        known = palette(name)
        if colours[:len(known)] == known:
            return '%s, %d colours' % (name, len(known))
    return ''


def make_palettes(figure, shot, path):
    from PIL import Image, ImageDraw
    _, fb, rows, palettes = shot
    width, height = len(fb) // len(rows), len(rows)
    bands = []
    for y, p in enumerate(rows):
        if bands and bands[-1][2] == p:
            bands[-1][1] = y
        else:
            bands.append([y, y, p])
    areas = figure['areas']
    swatch, gap, label_w, row_h, top = 9, 2, 300, 13, 16
    colours = max(len(p) for p in palettes)
    image = Image.new('RGB', (label_w + colours * (swatch + gap) + 6, top + row_h * len(bands) + 4),
                      GROUND)
    draw = ImageDraw.Draw(image)
    text(draw, (4, 2), 'rows     area        palette')
    for c in range(0, colours, 4):
        text(draw, (label_w + c * (swatch + gap), 2), str(c))
    for i, (first, last, p) in enumerate(bands):
        y0 = top + i * row_h
        area = next((a[2] for a in areas if a[0] <= first and last <= a[1]), '?')
        span = '%d' % first if first == last else '%d-%d' % (first, last)
        used = {fb[y * width + x] for y in range(first, last + 1) for x in range(width)}
        source = palette_file_of(palettes[p], figure['files'])
        text(draw, (4, y0), '%-8s %-11s %d %s' % (span, area, p, source))
        for c, rgb in enumerate(palettes[p]):
            x0 = label_w + c * (swatch + gap)
            if c in used:
                draw.rectangle((x0, y0, x0 + swatch - 1, y0 + swatch - 1), fill=rgb)
            else:
                draw.rectangle((x0 + 2, y0 + 2, x0 + swatch - 3, y0 + swatch - 3), fill=rgb)
    scale = figure.get('scale', 1)
    image.resize((image.width * scale, image.height * scale), Image.NEAREST).save(path)


def make_shapes(figure, path):
    tool = ppkc()
    shapes = tool.parse(str(SHAPES / figure['container']))
    flat = tool.load_cmap(str(SHAPES / figure['palette']))
    tool.sheet(shapes, flat, str(path))


def executable_names(table):
    """A name list of the executable, read from it at the address re/tables.toml gives."""
    import tomllib
    import extract_tables
    with open(ROOT / 're' / 'tables.toml', 'rb') as handle:
        entries = {t['name']: t for t in tomllib.load(handle)['table']}
    if table not in entries:
        raise Failure('re/tables.toml has no table %s' % table)
    entry = entries[table]
    image = extract_tables.Image(extract_tables.EXE)
    return [image.bytes(entry['addr'] + 4 * i, 4).decode('latin1') for i in range(entry['count'])]


def make_map(figure, path):
    from PIL import Image, ImageDraw
    import map_decode
    tool = ppkc()
    chart = map_decode.load(figure['map'])
    names = executable_names(figure['names'])
    shapes = {s['name']: s for s in tool.parse(str(SHAPES / figure['container']))}
    colours = palette(figure['palette'])
    split = figure['split_row']

    # Every draw of the whole map: draw_list for views a band of 256 pixels apart, each draw
    # put back into world x (the player stands at screen x 160), each record once.
    draws, view = {}, 0
    while view < chart.extent + 512:
        for index, slot, screen_x, screen_y, _ in map_decode.draw_list(chart, view,
                                                                       split_row=split):
            draws[index] = (slot, screen_x + view - 160, screen_y)
        view += 256
    sprites = []
    for index in sorted(draws):
        slot, x, y = draws[index]
        if slot >= len(names):
            continue            # past world_names: a ship's block or a null slot, none in map a
        shape = shapes.get(names[slot])
        if shape is None:
            continue            # a null slot, which draw_world skips
        sprites.append((x - shape['ox'], y - shape['oy'], shape))
    if not sprites:
        raise Failure('map %s: no record draws a shape' % figure['map'])
    top = min(y for _, y, _ in sprites) - 4
    bottom = max(y + s['h'] for _, y, s in sprites) + 2
    band = figure['band']
    count = (chart.extent + band - 1) // band
    strip_h, label_h = bottom - top, 12
    image = Image.new('RGB', (band, count * (strip_h + label_h)), GROUND)
    draw = ImageDraw.Draw(image)
    for b in range(count):
        y0 = b * (strip_h + label_h)
        text(draw, (2, y0), 'map %s, world x %d-%d' % (figure['map'], b * band,
                                                        min((b + 1) * band, chart.extent) - 1))
        draw.rectangle((0, y0 + label_h, min(band, chart.extent - b * band) - 1,
                        y0 + label_h + strip_h - 1), fill=colours[1])
    for x0, y0, shape in sprites:
        for dy, row in enumerate(tool.to_indexed(shape)):
            for dx, c in enumerate(row):
                x = x0 + dx
                if not c or not 0 <= x < chart.extent:
                    continue
                b = x // band
                image.putpixel((x - b * band, b * (strip_h + label_h) + label_h + y0 + dy - top),
                               colours[c])
    image.save(path)


def make_font(figure, path):
    from PIL import Image
    lib = core().lib
    core().reset_core()
    height = lib.wt_font_height()
    width = 640                                     # MaskBuffer's template, 640 x 12
    stride = width // 8
    ink, paper = palette(figure['ink'][0])[figure['ink'][1]], palette(figure['paper'][0])[figure['paper'][1]]
    lines = figure['lines']
    rendered = []
    for line in lines:
        data = line.encode('latin1')
        template = (ctypes.c_uint8 * (stride * height))()
        drawn = lib.wt_text_render(data, len(data), template, 0, 0, 0, width, height)
        if not drawn:
            raise Failure('font: "%s" does not fit the template' % line)
        rendered.append((drawn, bytes(template)))
    margin, gap = 6, 4
    image = Image.new('RGB', (max(d for d, _ in rendered) + 2 * margin,
                              len(lines) * (height + gap) - gap + 2 * margin), paper)
    for i, (drawn, template) in enumerate(rendered):
        for y in range(height):
            for x in range(drawn):
                if template[y * stride + x // 8] >> (7 - x % 8) & 1:
                    image.putpixel((margin + x, margin + i * (height + gap) + y), ink)
    sx, sy = figure['scale']
    image.resize((image.width * sx, image.height * sy), Image.NEAREST).save(path)


def make_planes(figure, path):
    """One shape's stored planes, each as its bits, then the colour numbers they make, as
    shades from black to white, then the same through a palette; one pixel marked in every
    row, its bit, its number and its colour written beside the row."""
    from PIL import Image, ImageDraw
    tool = ppkc()
    shapes = {s['name']: s for s in tool.parse(str(SHAPES / figure['container']))}
    if figure['shape'] not in shapes:
        raise Failure('%s has no shape %s' % (figure['container'], figure['shape']))
    shape = shapes[figure['shape']]
    masks = shape['masks']
    if masks != [1 << i for i in range(len(masks))]:
        raise Failure('%s: its planes land in %s, not in planes 1, 2, 4, ... in order'
                      % (figure['shape'], masks))
    wb, height = shape['wbytes'], shape['h']
    width = 8 * wb
    planes = []
    for i in range(len(masks)):
        data = shape['data'][i * wb * height:(i + 1) * wb * height]
        planes.append([[data[y * wb + (x >> 3)] >> (7 - (x & 7)) & 1 for x in range(width)]
                       for y in range(height)])
    numbers = [[sum(planes[i][y][x] << i for i in range(len(planes))) for x in range(width)]
               for y in range(height)]
    if numbers != tool.to_indexed(shape):
        raise Failure('%s: the planes do not make the pixels of tools/ppkc.py' % figure['shape'])
    colours = palette(figure['palette'])
    mark = palette(figure['mark'][0])[figure['mark'][1]]
    px, py = figure['pixel']
    value = numbers[py][px]
    top = (1 << len(planes)) - 1                     # the largest colour number, white

    def plane_ink(i):
        return lambda x, y: LABEL if planes[i][y][x] else None

    def shade(x, y):
        c = numbers[y][x]
        return (round(c * 255 / top),) * 3 if c else None

    def colour(x, y):
        return colours[numbers[y][x]] if numbers[y][x] else None

    rows = [('plane %d, worth %d' % (i + 1, 1 << i), plane_ink(i),
             'bit %d' % planes[i][py][px]) for i in range(len(planes))]
    rows.append(('colour number', shade,
                 '%d = %s' % (value, ' + '.join(str(1 << i) for i in range(len(planes))
                                                if planes[i][py][px]))))
    rows.append(('through %s' % figure['palette'], colour,
                 'colour %d, #%02X%02X%02X' % ((value,) + colours[value])))
    zoom = figure['zoom']
    label_w, gap, margin, head = 136, 7, 6, 18
    box_w, box_h = width * zoom, height * zoom
    image = Image.new('RGB', (margin + label_w + box_w + 10 + figure['note_width'],
                              head + len(rows) * (box_h + gap) - gap + 2 * margin), GROUND)
    draw = ImageDraw.Draw(image)
    text(draw, (margin, margin - 2), '%s, %s: %d x %d pixels, %d planes'
         % (figure['container'], figure['shape'], width, height, len(planes)))
    for r, (label, ink, note) in enumerate(rows):
        x0, y0 = margin + label_w, margin + head + r * (box_h + gap)
        text(draw, (margin, y0 + (box_h - 11) // 2), label)
        draw.rectangle((x0, y0, x0 + box_w - 1, y0 + box_h - 1), fill=PANEL)
        for y in range(height):
            for x in range(width):
                rgb = ink(x, y)
                if rgb:
                    draw.rectangle((x0 + x * zoom, y0 + y * zoom,
                                    x0 + (x + 1) * zoom - 1, y0 + (y + 1) * zoom - 1), fill=rgb)
        draw.rectangle((x0 + px * zoom - 1, y0 + py * zoom - 1,
                        x0 + (px + 1) * zoom, y0 + (py + 1) * zoom), outline=mark)
        text(draw, (x0 + box_w + 10, y0 + (box_h - 11) // 2), note)
    scale = figure.get('scale', 1)
    image.resize((image.width * scale, image.height * scale), Image.NEAREST).save(path)


def make_sample(figure, path):
    """A sound effect's file, signed 8-bit bytes, as a waveform: the whole of it, one column
    per few bytes from their smallest to their largest value, with a tick every 100 ms at the
    figure's period; then a stretch of it enlarged, each byte held as a step, as Paula holds
    it for one period."""
    from PIL import Image, ImageDraw
    import rpck
    name = 'sounds/%s' % figure['sound']
    raw, _ = rpck.load(str(DISK / name))
    values = [b - 256 if b > 127 else b for b in raw]
    count, period, clock = len(values), figure['period'], figure['clock']
    seconds = count * period / clock
    first, many = figure['zoom']
    if first + many > count:
        raise Failure('%s has %d bytes, the stretch %d + %d does not fit'
                      % (name, count, first, many))
    ink = palette(figure['ink'][0])[figure['ink'][1]]
    width, strip, margin, head, gap = figure['width'], figure['height'], 6, 14, 26
    image = Image.new('RGB', (width + 2 * margin, 2 * margin + 2 * (head + strip) + gap), GROUND)
    draw = ImageDraw.Draw(image)
    half = strip // 2 - 1

    def level(y0, v):
        return y0 + half - round(v * half / 128)

    def frame(y0, title):
        text(draw, (margin, y0 - head), title)
        draw.rectangle((margin, y0, margin + width - 1, y0 + strip - 1), fill=PANEL)
        draw.line((margin, y0 + half, margin + width - 1, y0 + half), fill=AXIS)

    y0 = margin + head
    frame(y0, '%s: %s bytes, %d ms at period %d on PAL'
          % (name, format(count, ','), round(seconds * 1000), period))
    for ms in range(0, int(seconds * 1000) + 1, 100):
        x = margin + round(ms / 1000 * clock / period * width / count)
        draw.line((x, y0 + strip, x, y0 + strip + 3), fill=AXIS)
        text(draw, (x + 2, y0 + strip + 1), '%d ms' % ms)
    for x in range(width):
        part = values[x * count // width:max(x * count // width + 1, (x + 1) * count // width)]
        draw.line((margin + x, level(y0, max(part)), margin + x, level(y0, min(part))), fill=ink)
    a = margin + first * width // count
    b = margin + (first + many) * width // count
    draw.rectangle((a - 1, y0, b, y0 + strip - 1), outline=LABEL)

    y1 = y0 + strip + gap + head
    frame(y1, 'bytes %d to %d, %.1f ms: each byte held for %d colour clocks'
          % (first, first + many - 1, many * period / clock * 1000, period))
    step = width / many
    last = None
    for i, v in enumerate(values[first:first + many]):
        xa, xb, y = margin + round(i * step), margin + round((i + 1) * step) - 1, level(y1, v)
        if last is not None:
            draw.line((xa, last, xa, y), fill=ink)
        draw.line((xa, y, xb, y), fill=ink)
        last = y
    scale = figure.get('scale', 1)
    image.resize((image.width * scale, image.height * scale), Image.NEAREST).save(path)


# ------------------------------------------------------------------ the manifest

def figures_of(names=None):
    data = manifest('figures.toml')
    figures, runs = data.get('figure', []), data.get('run', {})
    seen = set()
    for figure in figures:
        if figure['name'] in seen or figure['file'] in seen:
            raise Failure('%s is named twice in book/figures.toml' % figure['name'])
        seen.update((figure['name'], figure['file']))
        expected = '.venv/bin/python book/tools/figures.py %s' % figure['name']
        if figure.get('command') != expected:
            raise Failure('%s: its command must be "%s"' % (figure['name'], expected))
        if 'run' in figure and figure['run'] not in runs:
            raise Failure('%s: no run %s in book/figures.toml' % (figure['name'], figure['run']))
    if names:
        unknown = sorted(set(names) - {f['name'] for f in figures})
        if unknown:
            raise Failure('no figure named %s in book/figures.toml' % ', '.join(unknown))
        figures = [f for f in figures if f['name'] in names]
    return figures, runs


def generate(out, names=None, log=print):
    """The figures into `out`; returns how many."""
    figures, runs = figures_of(names)
    out = pathlib.Path(out)
    out.mkdir(parents=True, exist_ok=True)
    shots = {}
    for run in sorted({f['run'] for f in figures if 'run' in f}):
        wanted = {f['vblank'] for f in figures if f.get('run') == run}
        shots[run] = run_core(run, runs[run], wanted)
    for figure in figures:
        path = out / figure['file']
        maker = figure['maker']
        if maker == 'screen':
            make_screen(figure, shots[figure['run']][figure['vblank']], path)
        elif maker == 'palettes':
            make_palettes(figure, shots[figure['run']][figure['vblank']], path)
        elif maker == 'shapes':
            make_shapes(figure, path)
        elif maker == 'map':
            make_map(figure, path)
        elif maker == 'font':
            make_font(figure, path)
        elif maker == 'planes':
            make_planes(figure, path)
        elif maker == 'sample':
            make_sample(figure, path)
        else:
            raise Failure('%s: no maker %s' % (figure['name'], maker))
        if log:
            log('figure    %s' % figure['file'])
    return len(figures)


def main():
    parser = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    parser.add_argument('names', nargs='*', help='only these figures')
    parser.add_argument('--check', action='store_true',
                        help='compare a fresh rendering with the committed files, write nothing')
    parser.add_argument('--out', help='write into this directory instead')
    args = parser.parse_args()
    try:
        if args.check:
            with tempfile.TemporaryDirectory() as temp:
                count = generate(temp, log=None)
                problems = compare(temp, FIGURES)
            for line in problems:
                print(line)
            print('figures   %d checked, %s' % (count, '%d differ' % len(problems) if problems
                                                else 'all equal to the committed files'))
            return 1 if problems else 0
        if args.out:
            count = generate(args.out, args.names)
        elif args.names:
            count = generate(FIGURES, args.names)
        else:
            with tempfile.TemporaryDirectory() as temp:
                count = generate(temp, log=None)
                replace_tree(temp, FIGURES)
        print('figures   %d written to %s' % (count, args.out or rel(FIGURES)))
        return 0
    except Failure as failure:
        print('figures   FAILED: %s' % failure, file=sys.stderr)
        return 2


if __name__ == '__main__':
    os.chdir(ROOT)
    sys.exit(main())
