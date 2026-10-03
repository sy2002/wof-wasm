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
    shapes     a contact sheet of a shape container with tools/ppkc.py, or of shapes picked
               from several, as a grid or packed
    map        a map's drawn records with tools/map_decode.py and the shapes of tools/ppkc.py
    maprecord  a run of a map's records, the columns of one shape: the shape over them, and
               each record's sixteen bits grouped by field and decoded by tools/map_decode.py
    font       a specimen of the game's font, drawn by the core's text_render
    planes     one shape of a container taken apart into its stored planes with tools/ppkc.py,
               and put together again as colour numbers and through a palette
    blit       the blitter's cookie cut of one plane of a shape over a plain background
    sample     a sound effect's file as a waveform, the whole and a stretch enlarged
    disk       the game's directory on the disk, its files in rows by kind, with their bytes,
               the formats their first bytes show and whether tools/build.py packs them
    packed     the first bytes of a packed file against the bytes they unpack to, with
               tools/rpck.py's unpacking, each control byte spelled out
    codemap    the executable's code along its addresses from re/functions.csv, once by the
               routines' kind and once by their status
    pairs      colour tables side by side, each read from its file by the port's own readers
               through the native library, the entries that differ from another table marked
    fade       the sixteen steps of fades through the port's colour_lerp, each step's colour
               and its twelve bits, framed where the carry between components shows
    record     one record of a shape container byte by byte: its header field by field, its
               stored planes beside their bits, its colours with the hotspot framed
    clearset   shapes drawn over plain grounds by the blit's rule and without their clear and
               set bytes, the rule checked against the port's blit through the native library
    mirror     one shape as stored and as shape_mirror_x leaves it, the hotspot framed in
               both, checked against the pixels reversed and against the port's mirror
    path       the player's flight over a stretch of a run, the height over the world x a
               dot a tick in the colour of the record's state, the deck, the lift's column
               and the four cables marked, and the moments the state changes numbered

A run of the core may poke the registered state at the rank selection's end, as the
comparisons reach the night mission (re/notes/porting-m4.md, "Night"), through the native
library's test hook; the pokes are cleared when the run ends.  After the mission begins a run
may move the stick by a schedule of letters, as the mission scripts are written, or replay from
the start a schedule the headless original recorded; it may name registered globals, and the
player's record's height, x, state and facing as record_y, record_x, record_state and
record_facing, with the values they must have at a VBlank, which the run checks.

It needs the built repository (tools/build.py --native: dist/wof.html and the native library)
and runs on macOS, as the tests do; never the ROM at the time the site is built, because the
images are committed.  The figures are deterministic: two runs write the same bytes (a PNG of
Pillow carries no time), which --check holds.

Exit status: 0 done (or --check found the committed files equal), 1 --check found a
difference, 2 a figure could not be made.
"""
import argparse
import collections
import ctypes
import fnmatch
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
MUTED = (130, 130, 150)         # a label of lesser weight, a header's bytes


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
    if 'schedule' in spec:
        return schedule_input(spec['schedule'], vblank)
    if 'fire_from' in spec:
        return FIRE if spec['fire_from'] <= vblank < spec['fire_from'] + spec['fire_held'] else 0
    if 'fire_every' in spec:
        if lib.wt_mission_count():
            return after_input(spec, vblank)
        held = (vblank - 1) % spec['fire_every'] >= spec['fire_every'] - spec['fire_held']
        return FIRE if held else 0
    raise Failure('a run needs fire_from or fire_every: %s' % spec)


def after_input(spec, vblank):
    """The raw byte of a VBlank after the mission began: nothing, or the run's `after` schedule,
    runs of [VBlanks, letters] counted from the VBlank after mission_at, each letter a bit as
    tools/headless.py's RAW_BITS gives it to wof_vblank, as the mission scripts are written."""
    from headless import RAW_BITS
    k = vblank - spec['mission_at'] - 1
    for count, letters in spec.get('after', []):
        if k < count:
            return sum(RAW_BITS[letter] for letter in letters)
        k -= count
    return 0


def schedule_input(schedule, vblank):
    """The raw byte of a VBlank of a recorded schedule: runs of [VBlanks, raw byte] from the
    program's start, as the headless original recorded the VBlanks of a script, which the
    port replays one wof_vblank and one wof_pass each, as the loops of tests/m4compare.py do;
    nothing after the schedule's end."""
    k = vblank - 1
    for count, raw in schedule:
        if k < count:
            return raw
        k -= count
    return 0


def player_reader(ported):
    """A function that reads the player's record (src/records.def, the original's offsets)
    from the port's mission state: its height, x, state and facing, through tests/m4state.py's
    layout of the registered tables."""
    import struct
    import m4state
    layout = m4state.Layout(ported)
    table = next(t for t in layout.tables if t['name'] == 'player')
    fields = {f[0]: f[3] for f in layout.records['player']['fields']}
    base = table['port_offset']

    def read():
        state = layout.port_mission()
        return {name: struct.unpack_from('<h', state, base + fields[field])[0]
                for name, field in (('y', 'y'), ('x', 'x'), ('state', 'on_deck'),
                                    ('facing', 'facing'))}
    return read


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


PAGE_FADE = None                # the core's VBlanks a fade step as the page has them (src/fade.c)


def run_core(name, spec, wanted, until=0, ticks=False):
    """One run of the core from its start; at each wanted VBlank the picture (an RGB image of
    640 x 214) and its raw parts, and with `ticks` the player's record after every tick of the
    mission through the core's tick hook, up to VBlank `until` at least.  Returns
    {vblank: (image, framebuffer, rows, palettes)}, with 'ticks' a list of
    {tick, vblank, y, x, state, facing, airspeed}, the deck's globals and how far the
    wheels lie below the aircraft's reference point (wheel_height, 0x01AAEA)."""
    from m4_renders import picture
    global PAGE_FADE
    ported = core()
    lib = ported.lib
    if PAGE_FADE is None:
        PAGE_FADE = lib.wof_fade_vblanks()      # the page's step, before any run changes it
    ported.reset_core(fade_vblanks=spec.get('fade_vblanks', PAGE_FADE))
    lib.wof_set_video_hz(50)
    lib.wt_poke_address.argtypes = [ctypes.c_uint] * 4
    lib.wt_pokes_clear()
    for address, size, value in spec.get('pokes', []):
        lib.wt_poke_address(address, size, value, 0)    # point 0: the rank selection's end
    out, last = {}, max(set(wanted) | {until})
    vblank, samples, failed = 0, [], []
    hook = None
    if ticks:
        read = player_reader(ported)
        lib.wof_test_player_call.argtypes = [ctypes.c_uint32, ctypes.c_int32]
        lib.wof_test_player_call.restype = ctypes.c_int32

        def tick_end(tick):
            try:
                if lib.wt_mission_count():
                    samples.append(dict(read(), tick=tick, vblank=vblank,
                                        airspeed=ported.g('airspeed'),
                                        deck_west=ported.g('g_0253fc'),
                                        deck_east=ported.g('g_0253fe'),
                                        start=ported.g('player_start_x'),
                                        cable=ported.g('g_026d3a'),
                                        wheels=lib.wof_test_player_call(0x01AAEA, 0)))
            except Exception as error:          # an exception must not cross into C
                failed.append(error)
        hook = ctypes.CFUNCTYPE(None, ctypes.c_uint32)(tick_end)
        lib.wt_set_tick_hook(ctypes.cast(hook, ctypes.c_void_p))
    try:
        for vblank in range(1, last + 1):
            lib.wof_vblank(raw_input(spec, vblank, lib))
            lib.wof_pass()
            if 'mission_at' in spec and lib.wt_mission_count() and 'begun' not in out:
                out['begun'] = vblank
                if vblank != spec['mission_at']:
                    raise Failure('run %s: the mission began at VBlank %d, the manifest says %d'
                                  % (name, vblank, spec['mission_at']))
            for expect in spec.get('expect', []):
                if expect['vblank'] == vblank:
                    record = player_reader(ported)() if any(
                        f.startswith('record_') for f in expect) else {}
                    for field, value in expect.items():
                        if field == 'vblank':
                            continue
                        found = (record[field[len('record_'):]] if field.startswith('record_')
                                 else ported.g(field))
                        if found != value:
                            raise Failure('run %s: %s is %d at VBlank %d, the manifest says %d'
                                          % (name, field, found, vblank, value))
            if vblank in wanted:
                image = picture(ported)
                width, height = image.size
                out[vblank] = (image,) + capture(lib, width, height)
            if failed:
                raise failed[0]
    finally:
        lib.wt_pokes_clear()
        if hook is not None:
            lib.wt_set_tick_hook(None)
    if ticks:
        out['ticks'] = samples
    if 'dash_night' in spec and lib.wt_dash_night() != spec['dash_night']:
        raise Failure('run %s: the dashboard of the %s was loaded, the manifest says the %s'
                      % (name, *(('night', 'day')[1 - v] for v in (lib.wt_dash_night(),
                                                                    spec['dash_night']))))
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
    """A contact sheet of tools/ppkc.py: every shape of `container`, or the shapes `pick`
    names as [container, name] pairs from several containers, in their order; laid out as a
    grid by sheet(), `columns` to a row when given, or with `layout = "packed"` by
    packed_sheet()."""
    tool = ppkc()
    if 'pick' in figure:
        shapes = []
        for container, name in figure['pick']:
            found = [s for s in tool.parse(str(SHAPES / container)) if s['name'].strip() == name]
            if not found:
                raise Failure('%s has no shape %s' % (container, name))
            shapes.append(found[0])
    else:
        shapes = tool.parse(str(SHAPES / figure['container']))
    flat = tool.load_cmap(str(SHAPES / figure['palette']))
    if figure.get('layout') == 'packed':
        tool.packed_sheet(shapes, flat, str(path))
    else:
        tool.sheet(shapes, flat, str(path), cols=figure.get('columns'))


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


def make_maprecord(figure, path):
    """A run of consecutive records of one map, the columns of one shape: on the left the
    shape of the run's drawn record from its container, over its columns at eight pixels a
    record, its hotspot framed on the drawn record's world x; on the right each record's
    index, world x and word, its sixteen bits in boxes grouped by field and named
    (re/notes/map.md, "The record"), and its fields decoded by tools/map_decode.py's fields(),
    the slot named by the name list read from the executable.  Checked: one record of the run
    draws, all carry its slot and its height field, the shape's columns lie within the run, and
    draw_list() draws that record at that world x on the row of its height."""
    from PIL import Image, ImageDraw
    import map_decode
    tool = ppkc()
    chart = map_decode.load(figure['map'])
    first, last = figure['first'], figure['last']
    words = chart.words[first:last + 1]
    fields = [map_decode.fields(w) for w in words]
    drawn = [first + i for i, f in enumerate(fields) if f['draw']]
    if len(drawn) != 1 or len({(f['slot'], f['height']) for f in fields}) != 1:
        raise Failure('map %s, records %d to %d: not one shape with one drawn record, one slot '
                      'and one height field' % (figure['map'], first, last))
    drawn = drawn[0]
    slot = fields[0]['slot']
    names = executable_names(figure['names'])
    name = names[slot]
    shapes = {s['name'].strip(): s for s in tool.parse(str(SHAPES / figure['container']))}
    if name not in shapes:
        raise Failure('%s has no shape %s for slot %d' % (figure['container'], name, slot))
    shape = shapes[name]
    width, height, hx, hy = 8 * shape['wbytes'], shape['h'], shape['ox'], shape['oy']
    left = map_decode.WORLD_PER_RECORD * drawn - hx
    if left < 8 * first or left + width > 8 * (last + 1):
        raise Failure('%s at record %d reaches past records %d to %d' % (name, drawn, first, last))
    split = figure['split_row']
    view = map_decode.WORLD_PER_RECORD * drawn
    found = [d for d in map_decode.draw_list(chart, view, split_row=split) if d[0] == drawn]
    height_bits = fields[drawn - first]['height']
    if not found or found[0][2] + view - 160 != 8 * drawn \
            or found[0][3] != split + map_decode.HEIGHT_STEP * height_bits:
        raise Failure('draw_list does not draw record %d at world x %d' % (drawn, 8 * drawn))
    colours = palette(figure['palette'])
    mark = palette(figure['mark'][0])[figure['mark'][1]]
    font = tool.FONT

    margin, line, zoom = 6, 13, figure['zoom']
    count = last - first + 1
    panel_x, panel_y = margin, margin + 2 * line
    panel_w, panel_h = 8 * count * zoom, (height + 2) * zoom
    ruler_y = panel_y + panel_h + 4
    cell, gap = 15, 12
    groups = [('draw', [15]), ('14', [14]), ('height', [13, 12, 11]),
              ('slot', list(range(10, 1, -1))), ('low', [1, 0])]
    rows_x = panel_x + panel_w + 24
    bits_x = rows_x + 3 * 54
    positions, x = {}, bits_x
    for _, bits in groups:
        for b in bits:
            positions[b] = x
            x += cell
        x += gap
    decoded_x = x + 4
    row_h, rows_y = line + 6, panel_y + 2 * line + 4
    lows = {0: 'nothing', 1: 'rides on a ship', 2: 'stands on the world', 3: '3'}
    decoded = ['draw %d, height %d, slot %d %s, low %d: %s'
               % (f['draw'], f['height'], f['slot'], names[f['slot']], f['low'], lows[f['low']])
               for f in fields]
    image_w = decoded_x + 6 * max(len(d) for d in decoded) + margin
    image_h = max(ruler_y + 3 * line, rows_y + count * row_h + 2 * line) + margin
    image = Image.new('RGB', (image_w, image_h), GROUND)
    draw = ImageDraw.Draw(image)
    text(draw, (margin, margin - 2), 'map %s, records %d to %d: the %d columns of one %s, %s of %s'
         % (figure['map'], first, last, count, figure['what'], name, figure['container']))

    # The shape over its columns, its hotspot framed on the drawn record's x.
    draw.rectangle((panel_x, panel_y, panel_x + panel_w - 1, panel_y + panel_h - 1), fill=colours[1])
    sx = left - 8 * first
    for dy, row in enumerate(tool.to_indexed(shape)):
        for dx, c in enumerate(row):
            if c:
                px, py = panel_x + (sx + dx) * zoom, panel_y + (1 + dy) * zoom
                draw.rectangle((px, py, px + zoom - 1, py + zoom - 1), fill=colours[c])
    fx, fy = panel_x + (sx + hx) * zoom, panel_y + (1 + hy) * zoom
    draw.rectangle((fx - 1, fy - 1, fx + zoom, fy + zoom), outline=mark)
    for k in range(count):
        x0 = panel_x + 8 * k * zoom
        ink = mark if first + k == drawn else LABEL
        draw.rectangle((x0, ruler_y, x0 + 8 * zoom - 2, ruler_y + line), outline=ink)
        label = str(first + k)
        draw.text((x0 + (8 * zoom - 6 * len(label)) // 2, ruler_y + 1), label, fill=ink, font=font)
    text(draw, (panel_x, ruler_y + line + 4), 'records, 8 pixels each; the hotspot (%d, %d) framed'
         % (hx, hy))

    # The records, a row each.
    head_y = panel_y
    for title, x0 in (('record', rows_x), ('world x', rows_x + 54), ('word', rows_x + 108)):
        draw.text((x0, head_y + line), title, fill=MUTED, font=font)
    for title, bits in groups:
        x0, x1 = positions[bits[0]], positions[bits[-1]] + cell - 1
        draw.text(((x0 + x1 - 6 * len(title)) // 2, head_y), title, fill=LABEL, font=font)
        for b in bits:
            label = str(b)
            draw.text((positions[b] + (cell - 6 * len(label)) // 2, head_y + line), label,
                      fill=MUTED, font=font)
    for i, (w, f) in enumerate(zip(words, fields)):
        y0 = rows_y + i * row_h
        ink = mark if first + i == drawn else LABEL
        draw.text((rows_x, y0 + 2), str(first + i), fill=ink, font=font)
        draw.text((rows_x + 54, y0 + 2), str(8 * (first + i)), fill=ink, font=font)
        draw.text((rows_x + 108, y0 + 2), '0x%04X' % w, fill=ink, font=font)
        for b, x0 in positions.items():
            bit = w >> b & 1
            fill = (mark if b == 15 else LABEL) if bit else PANEL
            draw.rectangle((x0, y0, x0 + cell - 2, y0 + line + 2), fill=fill)
            draw.text((x0 + (cell - 7) // 2, y0 + 2), str(bit), fill=GROUND if bit else MUTED,
                      font=font)
        draw.text((decoded_x, y0 + 2), decoded[i], fill=ink, font=font)
    y0 = rows_y + (drawn - first) * row_h
    draw.rectangle((rows_x - 4, y0 - 3, image_w - margin + 2, y0 + line + 5), outline=mark)
    scale = figure.get('scale', 1)
    image.resize((image.width * scale, image.height * scale), Image.NEAREST).save(path)


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


def shape_planes(figure):
    """The record of figure['shape'] in figure['container'] and its stored planes as rows of
    bits, the planes landing in planes 1, 2, 4, ... in order, checked against the pixels of
    tools/ppkc.py's to_indexed()."""
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
    return shape, planes, numbers


def make_planes(figure, path):
    """One shape's stored planes, each as its bits, then the colour numbers they make, as
    shades from black to white, then the same through a palette; one pixel marked in every
    row, its bit, its number and its colour written beside the row."""
    from PIL import Image, ImageDraw
    shape, planes, numbers = shape_planes(figure)
    width, height = len(numbers[0]), len(numbers)
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


def make_blit(figure, path):
    """The blitter's cookie cut for one plane, as shape_draw programmes it for a shape of two
    or more stored planes (re/notes/drawing.md, minterm 0xCA): A the mask, the OR of the
    shape's planes; B the shape's plane; C the screen's plane under the shape's box, here of a
    plain background of one colour; D = A and B, or not A and C.  The result is checked
    against the shape's pixels laid over the background, plane by plane."""
    from PIL import Image, ImageDraw
    shape, planes, numbers = shape_planes(figure)
    width, height = len(numbers[0]), len(numbers)
    plane, ground = figure['plane'], figure['ground']
    if not 1 <= plane <= len(planes):
        raise Failure('%s has no plane %d' % (figure['shape'], plane))
    a = [[1 if numbers[y][x] else 0 for x in range(width)] for y in range(height)]
    b = planes[plane - 1]
    c = [[ground >> (plane - 1) & 1] * width for _ in range(height)]
    d = [[a[y][x] & b[y][x] | (1 - a[y][x]) & c[y][x] for x in range(width)]
         for y in range(height)]
    over = [[numbers[y][x] if numbers[y][x] else ground for x in range(width)]
            for y in range(height)]
    if d != [[over[y][x] >> (plane - 1) & 1 for x in range(width)] for y in range(height)]:
        raise Failure('%s: the cookie cut does not give the shape over the ground' % figure['shape'])
    rows = [('A, the mask', a, 'the OR of all %d planes' % len(planes)),
            ('B, the shape\'s plane %d' % plane, b, 'as %s stores it' % figure['container']),
            ('C, the screen\'s plane %d' % plane, c, 'colour %d everywhere' % ground),
            ('D, the result', d, '(A and B) or (not A and C)')]
    zoom = figure['zoom']
    label_w, gap, margin, head = 160, 7, 6, 18
    box_w, box_h = width * zoom, height * zoom
    image = Image.new('RGB', (margin + label_w + box_w + 10 + figure['note_width'],
                              head + len(rows) * (box_h + gap) - gap + 2 * margin), GROUND)
    draw = ImageDraw.Draw(image)
    text(draw, (margin, margin - 2), '%s over colour %d, plane %d of %d, one blitter run'
         % (figure['shape'], ground, plane, len(planes)))
    for r, (label, bits, note) in enumerate(rows):
        x0, y0 = margin + label_w, margin + head + r * (box_h + gap)
        text(draw, (margin, y0 + (box_h - 11) // 2), label)
        draw.rectangle((x0, y0, x0 + box_w - 1, y0 + box_h - 1), fill=PANEL)
        for y in range(height):
            for x in range(width):
                if bits[y][x]:
                    draw.rectangle((x0 + x * zoom, y0 + y * zoom,
                                    x0 + (x + 1) * zoom - 1, y0 + (y + 1) * zoom - 1), fill=LABEL)
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


def file_format(raw):
    """What a file's first bytes say it is: a hunk file (0x3F3), the game's packed format
    around what it unpacks to, a shape container, an IFF form with its type, or a bare IFF
    colour chunk (SPEC.md 3.5); None for none of them."""
    import rpck
    if raw[:4] == b'\x00\x00\x03\xf3':
        return 'hunk file'
    if raw[:4] == b'Rpck':
        inner = file_format(rpck.unrle(raw[8:]))
        return 'Rpck around %s' % inner if inner else 'Rpck'
    if raw[:4] == b'PPkc':
        return 'PPkc'
    if raw[:4] == b'FORM':
        return 'IFF %s' % raw[8:12].decode('latin1')
    if raw[:4] == b'CMAP':
        return 'IFF CMAP'
    return None


def make_disk(figure, path):
    """The game's directory on the disk, one row for each kind of file the manifest names:
    the files' count and bytes, a bar of the bytes to scale with a segment for each file, in
    one colour where tools/build.py packs the file into the page and in another where it is
    left out, and under it the formats the files' first bytes show.  Every file of the
    directory must belong to exactly one row."""
    from PIL import Image, ImageDraw
    from common import port_build
    port_build()
    import build
    packed = set(build.game_files())
    files = sorted(p.relative_to(DISK).as_posix() for p in DISK.rglob('*')
                   if p.is_file() and p.name != '.DS_Store')
    groups = figure['groups']
    members = {i: [] for i in range(len(groups))}
    for name in files:
        owners = [i for i, g in enumerate(groups) if any(fnmatch.fnmatch(name, pattern)
                                                         for pattern in g['files'])]
        if len(owners) != 1:
            raise Failure('%s belongs to %d rows of the figure, not to one' % (name, len(owners)))
        members[owners[0]].append(name)
    size = {name: (DISK / name).stat().st_size for name in files}
    inside = palette(figure['packed_ink'][0])[figure['packed_ink'][1]]
    outside = palette(figure['left_ink'][0])[figure['left_ink'][1]]

    margin, pitch, bar_h, bar_w = 6, 30, 9, figure['bar_width']
    label_w = max(len(g['label']) for g in groups) * 6 + 12
    count_x, bytes_x = margin + label_w, margin + label_w + 4 * 6
    bar_x = bytes_x + 9 * 6 + 12
    head, legend = 22, 44
    image = Image.new('RGB', (bar_x + bar_w + margin, head + pitch * len(groups) + legend + 16),
                      GROUND)
    draw = ImageDraw.Draw(image)
    text(draw, (margin, margin - 2), '%s on the disk: %d files, %s bytes'
         % (DISK.name, len(files), format(sum(size.values()), ',')))
    largest = max(sum(size[n] for n in members[i]) for i in members)
    for i, group in enumerate(groups):
        names = members[i]
        if not names:
            raise Failure('no file of the directory falls in the row "%s"' % group['label'])
        total = sum(size[n] for n in names)
        y = head + i * pitch
        text(draw, (margin, y), group['label'])
        count = str(len(names))
        text(draw, (count_x + 3 * 6 - 6 * len(count), y), count)
        amount = format(total, ',')
        text(draw, (bytes_x + 8 * 6 - 6 * len(amount), y), amount)
        x = bar_x
        for n in names:
            w = max(2, round(size[n] * bar_w / largest))
            draw.rectangle((x, y + 1, x + w - 2, y + bar_h), fill=inside if n in packed else outside)
            x += w
        kinds = collections.Counter(file_format((DISK / n).read_bytes()) or group['rest']
                                    for n in names)
        shown = [k if len(kinds) == 1 and (len(names) == 1 or k == group['rest'])
                 else '%d x %s' % (c, k) for k, c in sorted(kinds.items(), key=lambda kc: -kc[1])]
        draw.text((margin + 12, y + 12), '%s: %s' % (group['where'], ', '.join(shown)),
                  fill=MUTED, font=ppkc().FONT)
    y = head + len(groups) * pitch + 4
    for row, (ink, words, names) in enumerate((
            (inside, 'packed into the page', [n for n in files if n in packed]),
            (outside, 'left out', [n for n in files if n not in packed]))):
        draw.rectangle((margin, y + row * 16 + 2, margin + 15, y + row * 16 + 9), fill=ink)
        text(draw, (margin + 22, y + row * 16), '%s: %d files, %s bytes'
             % (words, len(names), format(sum(size[n] for n in names), ',')))
    text(draw, (margin, y + 32), 'the bars to scale, a segment for each file')
    scale = figure.get('scale', 1)
    image.resize((image.width * scale, image.height * scale), Image.NEAREST).save(path)


def make_packed(figure, path):
    """The first bytes of a file in the game's packed format, Rpck, against the bytes they
    unpack to: the header, then as many control bytes as the manifest asks for, each with
    the bytes it copies or the byte it repeats; the bytes made are checked against
    tools/rpck.py's unpacking of the whole file.  Where the file unpacks to a shape
    container, the container's fields are named beside their rows."""
    from PIL import Image, ImageDraw
    import rpck
    name = figure['source']
    raw = (DISK / name).read_bytes()
    if raw[:4] != b'Rpck':
        raise Failure('%s is not packed' % name)
    declared = int.from_bytes(raw[4:8], 'big')
    roles, made, out = ['head'] * 8, [], bytearray()
    notes_in = {0: 'Rpck, size %s' % format(declared, ',')}
    at = 8
    for _ in range(figure['controls']):
        control = raw[at]
        roles.append('control')
        if control >= 0x80:
            count = 256 - control
            notes_in[at] = '%02X: copy %d' % (control, count)
            roles += ['copy'] * count
            out += raw[at + 1:at + 1 + count]
            made += ['copy'] * count
            at += 1 + count
        else:
            notes_in[at] = '%02X: %d x %02X' % (control, control + 1, raw[at + 1])
            roles.append('value')
            out += bytes([raw[at + 1]]) * (control + 1)
            made += ['repeat'] * (control + 1)
            at += 2
    whole, _ = rpck.load(str(DISK / name))
    if bytes(out) != whole[:len(out)]:
        raise Failure('%s: the bytes shown do not unpack as tools/rpck.py unpacks them' % name)
    notes_out = {}
    if out[:4] == b'PPkc':
        count = int.from_bytes(out[4:6], 'big')
        first = out[6:10].decode('latin1')
        fields = {0: 'PPkc', 4: '%d shapes' % count, 6: 'their names', 6 + 4 * count: 'their offsets',
                  6 + 8 * count: '%s: its header' % first, 6 + 8 * count + 20: 'its planes'}
        notes_out = {k: v for k, v in fields.items() if k < len(out)}
    control_ink = palette(figure['control_ink'][0])[figure['control_ink'][1]]
    repeat_ink = palette(figure['repeat_ink'][0])[figure['repeat_ink'][1]]
    ink = {'head': MUTED, 'control': control_ink, 'copy': LABEL, 'value': repeat_ink,
           'repeat': repeat_ink}

    def row_notes(notes, row):
        return '; '.join(v for k, v in sorted(notes.items()) if row * 16 <= k < row * 16 + 16)

    margin, line, cell = 6, 13, 18
    dump_x = margin + 30
    note_x = dump_x + 16 * cell + 6
    rows_in, rows_out = (at + 15) // 16, (len(out) + 15) // 16
    notes_w = max(len(row_notes(n, r)) for n, rows in ((notes_in, rows_in), (notes_out, rows_out))
                  for r in range(rows)) * 6
    head = 16
    height = margin + 2 * (head + 4) + (rows_in + rows_out) * line + 12 + 2 * 16
    image = Image.new('RGB', (note_x + notes_w + margin, height), GROUND)
    draw = ImageDraw.Draw(image)

    def dump(y, title, data, kinds, notes, rows):
        text(draw, (margin, y), title)
        y += head + 4
        for r in range(rows):
            draw.text((margin, y + r * line), '+%02X' % (16 * r), fill=MUTED, font=ppkc().FONT)
            for c, b in enumerate(data[16 * r:16 * r + 16]):
                draw.text((dump_x + c * cell, y + r * line), '%02X' % b,
                          fill=ink[kinds[16 * r + c]], font=ppkc().FONT)
            text(draw, (note_x, y + r * line), row_notes(notes, r))
        return y + rows * line

    y = dump(margin, '%s on the disk, %s bytes: the first %d' % (name, format(len(raw), ','), at),
             raw[:at], roles, notes_in, rows_in)
    y = dump(y + 8, 'unpacked, %s bytes: the first %d' % (format(len(whole), ','), len(out)),
             out, made, notes_out, rows_out) + 8
    for i, (colour, words) in enumerate(((control_ink, 'a control byte'),
                                         (repeat_ink, 'a byte a repeat writes'),
                                         (LABEL, 'a byte copied as it is'),
                                         (MUTED, 'the header'))):
        x = margin + (i % 2) * 190
        yy = y + (i // 2) * 16
        draw.rectangle((x, yy + 2, x + 15, yy + 9), fill=colour)
        text(draw, (x + 22, yy), words)
    scale = figure.get('scale', 1)
    image.resize((image.width * scale, image.height * scale), Image.NEAREST).save(path)


def make_codemap(figure, path):
    """The code hunk along its addresses, once for each column of re/functions.csv the manifest
    names (the kind, the status): rows of `row_bytes` at `pixel_bytes` a pixel, each pixel in
    the colour of the value that holds most of its bytes, ticks above the rows at the marked
    addresses, and under each panel its values with their routines and bytes.  The routines'
    spans must tile the code hunk exactly, and every value must be one the manifest names."""
    import csv
    import hunk
    from PIL import Image, ImageDraw
    with open(ROOT / 're' / 'functions.csv', newline='') as handle:
        rows = list(csv.DictReader(handle))
    code = hunk.load(str(DISK / 'Wings'))[0]
    lo, size = code['base'], len(code['data'])
    at = lo
    for row in rows:
        if int(row['addr'], 16) != at:
            raise Failure('re/functions.csv: %s begins at 0x%s, the previous routine ends at '
                          '0x%06X' % (row['name'], row['addr'].upper(), at))
        at += int(row['span'])
    if at != lo + size:
        raise Failure('re/functions.csv: the spans end at 0x%06X, the code hunk at 0x%06X'
                      % (at, lo + size))

    row_bytes, pixel_bytes = figure['row_bytes'], figure['pixel_bytes']
    width, lines = row_bytes // pixel_bytes, (size + row_bytes - 1) // row_bytes
    margin, label_w, row_h, gap, head, legend_h = 6, 48, 9, 5, 16, 13
    panels = figure['panels']
    panel_h = [head + lines * (row_h + gap) + 4 + legend_h * (len(p['values']) + ('note' in p))
               + 10 for p in panels]
    image = Image.new('RGB', (2 * margin + label_w + width, margin + sum(panel_h)), GROUND)
    draw = ImageDraw.Draw(image)
    y0 = margin
    for panel, height in zip(panels, panel_h):
        column, values = panel['column'], panel['values']
        order = [v[0] for v in values]
        colour = {v[0]: palette(v[2][0])[v[2][1]] for v in values}
        owner = bytearray(size)                          # the value of every byte, by its index
        for row in rows:
            if row[column] not in order:
                raise Failure('%s: %s has %s %r, which the manifest does not name'
                              % (figure['name'], row['name'], column, row[column]))
            a = int(row['addr'], 16) - lo
            owner[a:a + int(row['span'])] = bytes([order.index(row[column])]) * int(row['span'])
        text(draw, (margin, y0), panel['title'])
        top = y0 + head
        for line in range(lines):
            y = top + line * (row_h + gap) + gap
            text(draw, (margin, y - 2), '%06X' % (lo + line * row_bytes))
            x0 = margin + label_w
            first = line * row_bytes
            span = min(row_bytes, size - first)
            draw.rectangle((x0, y, x0 + width - 1, y + row_h - 1), fill=PANEL)
            for px in range((span + pixel_bytes - 1) // pixel_bytes):
                part = owner[first + px * pixel_bytes:min(first + (px + 1) * pixel_bytes, size)]
                counts = collections.Counter(part)
                best = max(counts, key=lambda v: (counts[v], -v))
                draw.line((x0 + px, y, x0 + px, y + row_h - 1), fill=colour[order[best]])
            for mark in figure['marks']:
                offset = mark - lo - first
                if 0 <= offset < row_bytes:
                    x = x0 + offset // pixel_bytes
                    draw.line((x, y - 4, x, y - 1), fill=LABEL)
        y = top + lines * (row_h + gap) + 4
        words_w = max(len(v[1]) for v in values)
        for i, (value, words, _) in enumerate(values):
            members = [r for r in rows if r[column] == value]
            yy = y + i * legend_h
            draw.rectangle((margin, yy + 2, margin + 15, yy + 9), fill=colour[value])
            text(draw, (margin + 22, yy), '%-*s %4d %-8s %7s bytes' % (
                words_w, words, len(members), 'routine' if len(members) == 1 else 'routines',
                format(sum(int(r['span']) for r in members), ',')))
        if 'note' in panel:
            draw.text((margin, y + len(values) * legend_h), panel['note'], fill=MUTED,
                      font=ppkc().FONT)
        y0 += height
    scale = figure.get('scale', 1)
    image.resize((image.width * scale, image.height * scale), Image.NEAREST).save(path)


def rgb4(word):
    """A colour word as the hardware shows it: bits 12 to 15 ignored, each 4-bit component
    widened as src/video.c's wof_colour_rgba widens it."""
    return tuple(((word >> shift) & 0xF) * 17 for shift in (8, 4, 0))


def colour_table(entry):
    """One colour table read from its file under shapes/ as the game reads it, by the port's
    own readers through the native library: a picture (`picture`: the viewport's width, rows
    and depth) through iff_to_vport, which takes its CMAP, as many colours as the depth gives;
    a bare palette file through cmap_file_to_table, 32 colours."""
    ported = core()
    path = 'shapes/%s' % entry['file']
    if 'picture' in entry:
        width, rows, depth = entry['picture']
        _, colours = ported.iff_decode(path, width, rows, depth)
        return colours[:1 << depth]
    return ported.cmap_file_to_table(path)


def make_pairs(figure, path):
    """Colour tables in rows, grouped by a time of day, each row its area, its file and its
    colours; a row with `against` marks every entry that differs from that area's table of
    the same group, and counts them."""
    from PIL import Image, ImageDraw
    core().reset_core()
    mark = palette(figure['mark'][0])[figure['mark'][1]]
    swatch, gap, label_w, row_h, top, group_gap, margin = 9, 2, 250, 16, 18, 8, 6
    tables = figure['tables']
    groups = []
    for entry in tables:
        if not groups or groups[-1][0] != entry['time']:
            groups.append((entry['time'], []))
        groups[-1][1].append(entry)
    width = margin + label_w + 32 * (swatch + gap) + figure['note_width']
    height = top + sum(len(g[1]) * row_h for g in groups) + (len(groups) - 1) * group_gap + margin
    image = Image.new('RGB', (width, height), GROUND)
    draw = ImageDraw.Draw(image)
    text(draw, (margin, 2), 'time      area       file')
    for c in range(0, 32, 4):
        text(draw, (margin + label_w + c * (swatch + gap), 2), str(c))
    y0 = top
    for time, entries in groups:
        read = {entry['area']: colour_table(entry) for entry in entries}
        for i, entry in enumerate(entries):
            colours = read[entry['area']]
            text(draw, (margin, y0), '%-9s %-10s %s' % (time if i == 0 else '', entry['area'],
                                                          entry['file']))
            differ = set()
            if 'against' in entry:
                other = read[entry['against']]
                differ = {c for c in range(len(colours)) if colours[c] != other[c]}
            for c, word in enumerate(colours):
                x = margin + label_w + c * (swatch + gap)
                draw.rectangle((x, y0, x + swatch - 1, y0 + swatch - 1), fill=rgb4(word))
                if c in differ:
                    draw.rectangle((x, y0 + swatch + 2, x + swatch - 1, y0 + swatch + 3), fill=mark)
            note = '%d colours' % len(colours)
            if 'against' in entry:
                note = '%d differ from the %s\'s' % (len(differ), entry['against'])
            text(draw, (margin + label_w + 32 * (swatch + gap) + 4, y0), note)
            y0 += row_h
        y0 += group_gap
    scale = figure.get('scale', 1)
    image.resize((image.width * scale, image.height * scale), Image.NEAREST).save(path)


def table_colour(value):
    """A colour of the fade figure's manifest: a word, or [file, entry] of a bare palette."""
    if isinstance(value, int):
        return value
    return core().cmap_file_to_table('shapes/%s' % value[0])[value[1]]


def make_fade(figure, path):
    """The sixteen steps of fades through the port's colour_lerp (orig 0x016FF6), one row
    each: every step's colour as the hardware shows it and its twelve bits in hexadecimal;
    framed where the step differs from the colour each component would give computed alone,
    the start plus the truncated share of its own difference, which is where the carry from
    a falling component into the next shows (re/notes/display.md, "Fades")."""
    from PIL import Image, ImageDraw
    ported = core()
    ported.reset_core()
    frame = palette(figure['frame'][0])[figure['frame'][1]]

    def alone(step, start, end):
        if step == 15:
            return end
        out = 0
        for shift in (0, 4, 8):
            a, b = start >> shift & 0xF, end >> shift & 0xF
            out |= a + int((b - a) * step / 15) << shift
        return out

    swatch_w, swatch_h, gap, label_w, row_h, top, margin = 22, 14, 3, 230, 30, 16, 6
    rows = figure['rows']
    image = Image.new('RGB', (margin + label_w + 16 * (swatch_w + gap) + margin,
                              top + len(rows) * row_h + margin), GROUND)
    draw = ImageDraw.Draw(image)
    text(draw, (margin, 2), 'from   to     step')
    for step in range(16):
        text(draw, (margin + label_w + step * (swatch_w + gap) + 4, 2), str(step))
    framed = 0
    for r, row in enumerate(rows):
        start, end = table_colour(row['from']), table_colour(row['to'])
        y0 = top + r * row_h
        text(draw, (margin, y0), '%03X -> %03X' % (start, end))
        text(draw, (margin, y0 + 12), row['note'])
        for step in range(16):
            word = ported.colour_lerp(step, start, end) & 0xFFF
            x = margin + label_w + step * (swatch_w + gap)
            draw.rectangle((x, y0, x + swatch_w - 1, y0 + swatch_h - 1), fill=rgb4(word))
            if word != alone(step, start, end):
                draw.rectangle((x - 1, y0 - 1, x + swatch_w, y0 + swatch_h), outline=frame)
                framed += 1
            draw.text((x + 2, y0 + swatch_h + 1), '%03X' % word, fill=LABEL, font=ppkc().FONT)
    if not framed:
        raise Failure('%s: no step shows the carry' % figure['name'])
    scale = figure.get('scale', 1)
    image.resize((image.width * scale, image.height * scale), Image.NEAREST).save(path)


# ------------------------------------------------------------------ one record, its rule, its mirror

def planes_named(byte):
    """The screen's planes a byte of a record names, counted from 1 as chapter 2 counts them."""
    named = [str(i + 1) for i in range(8) if byte >> i & 1]
    if not named:
        return 'none'
    if len(named) == 1:
        return 'plane %s' % named[0]
    return 'planes %s and %s' % (', '.join(named[:-1]), named[-1])


def record_of(container, name):
    """The record of shape `name` as the unpacked container holds it: its offset in the
    unpacked file and its bytes, from its entry's offset to the next entry's, checked against
    tools/ppkc.py's parse() of the same container."""
    import rpck
    image, _ = rpck.load(str(SHAPES / container))
    count = int.from_bytes(image[4:6], 'big')
    names = [image[6 + 4 * i:10 + 4 * i].decode('latin1').strip() for i in range(count)]
    if name not in names:
        raise Failure('%s has no shape %s' % (container, name))
    index = names.index(name)
    table = 6 + 4 * count
    offsets = [int.from_bytes(image[table + 4 * i:table + 4 * i + 4], 'big') for i in range(count)]
    base = 6 + 8 * count
    start = base + offsets[index]
    end = base + offsets[index + 1] if index + 1 < count else len(image)
    record = image[start:end]
    shape = ppkc().parse(str(SHAPES / container))[index]
    if record[20:] != shape['data'] or len(record) != 20 + shape['wbytes'] * shape['h'] * len(shape['masks']):
        raise Failure('%s %s: the record is not what tools/ppkc.py parses' % (container, name))
    return index, start, record, shape


def make_record(figure, path):
    """One record of a shape container, byte by byte: its header field by field with each
    field's name and value (re/notes/shapes.md, "Record header, complete"), then each stored
    plane, a row of the shape to a line, its bytes beside its bits, with the planes its mask
    names; last the shape's colours through a palette, the hotspot framed.  The planes put
    together through their masks are checked against tools/ppkc.py's to_indexed()."""
    from PIL import Image, ImageDraw
    index, start, record, shape = record_of(figure['container'], figure['shape'])
    wb, height = shape['wbytes'], shape['h']
    width = 8 * wb
    word = lambda at: int.from_bytes(record[at:at + 2], 'big')
    signed = lambda at: word(at) - 0x10000 if word(at) & 0x8000 else word(at)
    masks = shape['masks']
    clear, setb = record[12], record[13]
    fields = [(0, 2, 'width in bytes', '%d: %d pixels' % (wb, width)),
              (2, 2, 'height', '%d rows' % height),
              (4, 2, 'hotspot x', '%d' % signed(4)),
              (6, 2, 'hotspot y', '%d' % signed(6)),
              (8, 2, 'cut position x', '%d' % word(8)),
              (10, 2, 'cut position y', '%d' % word(10)),
              (12, 1, 'clear byte', planes_named(clear)),
              (13, 1, 'set byte', planes_named(setb)),
              (14, 6, 'plane masks', '; '.join(planes_named(m) for m in masks) + ', then 0')]
    planes = []
    for i, mask in enumerate(masks):
        data = record[20 + i * wb * height:20 + (i + 1) * wb * height]
        planes.append((mask, data, [[data[y * wb + (x >> 3)] >> (7 - (x & 7)) & 1
                                      for x in range(width)] for y in range(height)]))
    numbers = [[0] * width for _ in range(height)]
    for mask, _, bits in planes:
        for y in range(height):
            for x in range(width):
                if bits[y][x]:
                    numbers[y][x] |= mask
    if numbers != ppkc().to_indexed(shape):
        raise Failure('%s: the planes do not make the pixels of tools/ppkc.py' % figure['shape'])
    colours = palette(figure['palette'])
    mark = palette(figure['mark'][0])[figure['mark'][1]]
    hx, hy = signed(4), signed(6)

    margin, line, cell, zoom = 6, 13, 18, figure['zoom']
    off_x, bytes_x, name_x, value_x = margin, margin + 34, margin + 34 + 6 * cell + 4, 0
    value_x = name_x + 96
    hex_w = wb * cell
    block_w = hex_w + 6 + width * zoom
    block_h = line + height * zoom
    gap = 18
    top = margin + line + 4
    header_h = len(fields) * line
    blocks_y = top + header_h + 10
    columns = figure.get('columns', 2)
    blocks = [('+%d, stored plane %d, plane mask 0x%02X: %s' % (20 + i * wb * height, i + 1, mask,
                                                       planes_named(mask)), data, bits)
              for i, (mask, data, bits) in enumerate(planes)]
    blocks.append(('its colours through %s' % figure['palette'], None, None))
    rows = (len(blocks) + columns - 1) // columns
    widest = max(len(b[0]) for b in blocks) * 6
    column_w = max(block_w, widest) + gap
    image = Image.new('RGB', (max(margin + columns * column_w, value_x + 200),
                              blocks_y + rows * (block_h + gap) + margin), GROUND)
    draw = ImageDraw.Draw(image)
    text(draw, (margin, margin - 2), '%s, %s: its record, %d bytes at 0x%04X of the unpacked file'
         % (figure['container'], figure['shape'], len(record), start))
    for r, (at, size, name, value) in enumerate(fields):
        y = top + r * line
        draw.text((off_x, y), '+%d' % at, fill=MUTED, font=ppkc().FONT)
        for k in range(size):
            draw.text((bytes_x + k * cell, y), '%02X' % record[at + k], fill=LABEL, font=ppkc().FONT)
        text(draw, (name_x, y), name)
        text(draw, (value_x, y), value)
    for b, (title, data, bits) in enumerate(blocks):
        x0 = margin + (b % columns) * column_w
        y0 = blocks_y + (b // columns) * (block_h + gap)
        text(draw, (x0, y0), title)
        px0, py0 = x0 + hex_w + 6, y0 + line
        draw.rectangle((px0, py0, px0 + width * zoom - 1, py0 + height * zoom - 1), fill=PANEL)
        for y in range(height):
            if data is not None:
                for k in range(wb):
                    draw.text((x0 + k * cell, py0 + y * zoom + (zoom - 11) // 2),
                              '%02X' % data[y * wb + k], fill=LABEL, font=ppkc().FONT)
            for x in range(width):
                if bits is not None:
                    ink = LABEL if bits[y][x] else None
                else:
                    ink = colours[numbers[y][x]] if numbers[y][x] else None
                if ink:
                    draw.rectangle((px0 + x * zoom, py0 + y * zoom, px0 + (x + 1) * zoom - 1,
                                    py0 + (y + 1) * zoom - 1), fill=ink)
        if data is None:
            draw.rectangle((px0 + hx * zoom - 1, py0 + hy * zoom - 1, px0 + (hx + 1) * zoom,
                            py0 + (hy + 1) * zoom), outline=mark)
            text(draw, (x0, py0 + height * zoom + 2), 'the hotspot (%d, %d) framed' % (hx, hy))
    scale = figure.get('scale', 1)
    image.resize((image.width * scale, image.height * scale), Image.NEAREST).save(path)


def blit_rule(v, p, clear, setb, union, masked, depth=5):
    """One pixel as shape_blit leaves it (re/notes/porting-m1.md, "The blit is per-pixel, and
    why"): unchanged where a masked shape's pixel is 0, else the clear planes, the set planes
    and the stored planes in that order."""
    m = (1 << depth) - 1
    if masked and not p:
        return v
    return (((v & ~(clear & m)) | (setb & m)) & ~(union & m) | (p & m)) & 0xFF


def make_clearset(figure, path):
    """Shapes drawn over grounds of one colour each, twice: by the blit's rule with the
    record's clear and set bytes, and with the two bytes taken as 0.  The rule's result is
    checked against the port's own blit through the native library (tests/shim.c, wt_blit)
    on a five-plane target."""
    from PIL import Image, ImageDraw
    ported = core()
    ported.reset_core()
    colours = palette(figure['palette'])
    margin, line, pad, gap, label_w = 6, 13, 2, 10, 128
    sections = []
    for entry in figure['shapes']:
        shape = [s for s in ppkc().parse(str(SHAPES / entry['container']))
                 if s['name'].strip() == entry['shape']]
        if not shape:
            raise Failure('%s has no shape %s' % (entry['container'], entry['shape']))
        shape = shape[0]
        pixels = ppkc().to_indexed(shape)
        wb, height, masks = shape['wbytes'], shape['h'], shape['masks']
        width = 8 * wb
        clear, setb = shape['u'][2] >> 8, shape['u'][2] & 0xFF
        union = 0
        for mask in masks:
            union |= mask
        masked = wb * height <= 1040 and len(masks) > 0
        slot = entry['slot']
        names = [ported.container_name(slot, i) for i in range(ported.container_shapes(slot))]
        index = names.index(int.from_bytes(shape['name'].encode('latin1'), 'big'))
        rows = []
        for ground in figure['grounds']:
            game = [[blit_rule(ground, pixels[y][x], clear, setb, union, masked)
                     for x in range(width)] for y in range(height)]
            bare = [[blit_rule(ground, pixels[y][x], 0, 0, union, masked)
                     for x in range(width)] for y in range(height)]
            at_x, at_y = 16, 8
            out = ported.blit(slot, index, 40, 162, 5, (0, 162, 0, 320), at_x, at_y,
                              bytes([ground]) * (320 * 162))
            drawn = [[out[(at_y + y) * 320 + at_x + x] for x in range(width)] for y in range(height)]
            if drawn != game:
                raise Failure('%s: the rule is not what the port\'s blit draws over colour %d'
                              % (entry['shape'], ground))
            written = [[bool(pixels[y][x]) or not masked for x in range(width)]
                       for y in range(height)]
            rows.append((ground, game, bare, written))
        sections.append((entry, shape, width, height, clear, setb, rows))
    panel_w = max((s[2] + 2 * pad) * s[0]['zoom'] for s in sections)
    image_w = margin + label_w + 2 * (panel_w + gap) + margin
    image_h = margin + line + sum(line + 2 + len(s[6]) * ((s[3] + 2 * pad) * s[0]['zoom'] + line + gap)
                                  for s in sections) + margin
    image = Image.new('RGB', (image_w, image_h), GROUND)
    draw = ImageDraw.Draw(image)
    x_game, x_bare = margin + label_w, margin + label_w + panel_w + gap
    text(draw, (x_game, margin), 'by the game\'s rule')
    text(draw, (x_bare, margin), 'without the clear and set bytes')
    y = margin + line + 4
    for entry, shape, width, height, clear, setb, rows in sections:
        zoom = entry['zoom']
        text(draw, (margin, y), '%s of %s: clear byte 0x%02X, set byte 0x%02X, %s'
             % (entry['shape'], entry['container'], clear, setb,
                '%d times enlarged' % zoom if zoom > 1 else 'at its own size'))
        y += line + 2
        for ground, game, bare, written in rows:
            text(draw, (margin, y + 2), 'over colour %d' % ground)
            for x0, picture in ((x_game, game), (x_bare, bare)):
                box_w, box_h = (width + 2 * pad) * zoom, (height + 2 * pad) * zoom
                draw.rectangle((x0, y, x0 + box_w - 1, y + box_h - 1), fill=colours[ground])
                for py in range(height):
                    for px in range(width):
                        c = picture[py][px]
                        if written[py][px]:
                            draw.rectangle((x0 + (px + pad) * zoom, y + (py + pad) * zoom,
                                            x0 + (px + pad + 1) * zoom - 1,
                                            y + (py + pad + 1) * zoom - 1), fill=colours[c])
                used = sorted({picture[py][px] for py in range(height) for px in range(width)
                               if written[py][px]})
                text(draw, (x0, y + box_h + 1), 'colours ' + ' '.join(str(c) for c in used))
            y += (height + 2 * pad) * zoom + line + gap
    scale = figure.get('scale', 1)
    image.resize((image.width * scale, image.height * scale), Image.NEAREST).save(path)


def mirrored_planes(shape):
    """shape_mirror_x's rule (orig 0x015B58) on the stored planes: in every row of every
    plane the bytes swapped from both ends, each byte's bits reversed; the hotspot's x
    becomes 8 times the width less 1 less the old x."""
    wb, height = shape['wbytes'], shape['h']
    reverse = [int('{:08b}'.format(b)[::-1], 2) for b in range(256)]
    data = bytearray(shape['data'])
    for p in range(len(shape['masks'])):
        for y in range(height):
            at = p * wb * height + y * wb
            data[at:at + wb] = bytes(reverse[b] for b in reversed(data[at:at + wb]))
    turned = dict(shape, data=bytes(data), ox=8 * wb - 1 - shape['ox'])
    return turned


def make_mirror(figure, path):
    """One shape as its container stores it and as shape_mirror_x leaves it, the hotspot
    framed in both.  The mirror is computed on the stored planes by the original's rule and
    checked against tools/ppkc.py's pixels with each row reversed, and against the port's own
    mirror through the native library, which is mirrored back after."""
    from PIL import Image, ImageDraw
    tool = ppkc()
    shape = [s for s in tool.parse(str(SHAPES / figure['container']))
             if s['name'].strip() == figure['shape']]
    if not shape:
        raise Failure('%s has no shape %s' % (figure['container'], figure['shape']))
    shape = shape[0]
    turned = mirrored_planes(shape)
    before, after = tool.to_indexed(shape), tool.to_indexed(turned)
    if after != [row[::-1] for row in before]:
        raise Failure('%s: the mirrored planes are not the pixels reversed' % figure['shape'])
    ported = core()
    ported.reset_core()
    slot = figure['slot']
    names = [ported.container_name(slot, i) for i in range(ported.container_shapes(slot))]
    index = names.index(int.from_bytes(shape['name'].encode('latin1'), 'big'))
    width, height = 8 * shape['wbytes'], shape['h']
    stored = ported.shape_pixels(slot, index)
    ported.shape_mirror(slot, index)
    port = ported.shape_pixels(slot, index), ported.shape_field(slot, index, 'hot_x')
    ported.shape_mirror(slot, index)
    if ported.shape_pixels(slot, index) != stored:
        raise Failure('%s: the port\'s mirror is not its own inverse' % figure['shape'])
    if port != (bytes(c for row in after for c in row), turned['ox']):
        raise Failure('%s: the port\'s mirror differs from the rule' % figure['shape'])
    colours = palette(figure['palette'])
    mark = palette(figure['mark'][0])[figure['mark'][1]]
    zoom, margin, line, gap = figure['zoom'], 6, 13, 24
    box_w, box_h = width * zoom, height * zoom
    image = Image.new('RGB', (2 * margin + 2 * box_w + gap, 2 * margin + 2 * line + box_h + 4),
                      GROUND)
    draw = ImageDraw.Draw(image)
    for k, (title, pixels, s) in enumerate((('as %s stores it' % figure['container'], before, shape),
                                            ('mirrored', after, turned))):
        x0, y0 = margin + k * (box_w + gap), margin + line
        text(draw, (x0, margin - 2), title)
        draw.rectangle((x0, y0, x0 + box_w - 1, y0 + box_h - 1), fill=PANEL)
        for y in range(height):
            for x in range(width):
                if pixels[y][x]:
                    draw.rectangle((x0 + x * zoom, y0 + y * zoom, x0 + (x + 1) * zoom - 1,
                                    y0 + (y + 1) * zoom - 1), fill=colours[pixels[y][x]])
        hx, hy = s['ox'], s['oy']
        draw.rectangle((x0 + hx * zoom - 1, y0 + hy * zoom - 1, x0 + (hx + 1) * zoom,
                        y0 + (hy + 1) * zoom), outline=mark)
        text(draw, (x0, y0 + box_h + 3), 'the hotspot (%d, %d)' % (hx, hy))
    scale = figure.get('scale', 1)
    image.resize((image.width * scale, image.height * scale), Image.NEAREST).save(path)


def make_path(figure, spec, ticks, path):
    """The player's flight over a stretch of a run, tick by tick: the height over the world x,
    a dot a tick in the colour of the record's state, with the carrier's deck from its two ends
    (deck_west and deck_east, 0x0253FC and 0x0253FE) up to its surface where the aircraft stood
    on it, the aircraft's height less its wheels, the lift's column at player_start_x, the four
    cables at player_start_x + 0x46 and 0x38 apart (cable_hook's rule, 0x01B92E), the one the
    hook caught (0x026D3A) marked, and the moments the state changes numbered.  Checked: every tick of the stretch inside the
    figure's box, every state named in the manifest, the cable caught one of the four."""
    from PIL import Image, ImageDraw
    first, last = figure['vblanks']
    run = [t for t in ticks if first <= t['vblank'] <= last]
    if not run:
        raise Failure('%s: no tick between VBlanks %d and %d' % (figure['name'], first, last))
    (x0, x1), (y0, y1) = figure['x'], figure['y']
    xs, ys = figure['x_scale'], figure['y_scale']
    states = {state: (words, palette(ink[0])[ink[1]]) for state, words, ink in figure['states']}
    for t in run:
        if not (x0 <= t['x'] <= x1 and y0 <= t['y'] <= y1):
            raise Failure('%s: tick %d at (%d, %d) lies outside the figure'
                          % (figure['name'], t['tick'], t['x'], t['y']))
        if t['state'] not in states:
            raise Failure('%s: tick %d is in state %d, which the manifest does not name'
                          % (figure['name'], t['tick'], t['state']))
    end = run[-1]
    cables = [end['start'] + 0x46 + 0x38 * k for k in range(4)]
    caught = end['cable']
    if caught and caught not in cables:
        raise Failure('%s: the cable caught, %d, is none of %s' % (figure['name'], caught, cables))
    # The deck's surface where the aircraft stood on it: its height less its wheels.
    standing = sorted(t['y'] - t['wheels'] for t in run
                      if t['state'] == 1 and end['deck_west'] <= t['x'] <= end['deck_east'])
    if not standing:
        raise Failure('%s: the aircraft never stands on the deck' % figure['name'])
    deck_y = standing[len(standing) // 2]
    left, top, bottom = 34, 40, 22
    width, height = round((x1 - x0) * xs), round((y1 - y0) * ys)
    image = Image.new('RGB', (left + width + 8, top + height + bottom), GROUND)
    draw = ImageDraw.Draw(image)

    def px(x):
        return left + round((x - x0) * xs)

    def py(y):
        return top + round((y1 - y) * ys)

    draw.rectangle((left, top, left + width, top + height), fill=PANEL)
    sea = palette(figure['sea'][0])[figure['sea'][1]]
    draw.rectangle((left, py(0), left + width, top + height), fill=sea)
    hull = palette(figure['deck'][0])[figure['deck'][1]]
    draw.rectangle((px(end['deck_west']), py(deck_y), px(end['deck_east']), py(0)), fill=hull)
    draw.rectangle((px(end['start']) - 3, py(deck_y), px(end['start']) + 3, py(0)), fill=PANEL)
    mark = palette(figure['mark'][0])[figure['mark'][1]]
    wire = palette(figure['cable'][0])[figure['cable'][1]]
    for x in cables:
        draw.line((px(x), py(deck_y) - (6 if x == caught else 3), px(x), py(deck_y)),
                  fill=mark if x == caught else wire)
    for x in range(x0 - x0 % 200 + 200, x1 + 1, 200):
        draw.line((px(x), top + height, px(x), top + height + 3), fill=AXIS)
        text(draw, (px(x) - 12, top + height + 5), str(x))
    for y in range(0, y1 + 1, 50):
        draw.line((left - 3, py(y), left, py(y)), fill=AXIS)
        text(draw, (left - 6 - 6 * len(str(y)), py(y) - 6), str(y))
    previous = None
    for t in run:
        colour = states[t['state']][1]
        at = (px(t['x']), py(t['y']))
        if previous is not None:
            draw.line(previous + at, fill=colour)
        draw.rectangle((at[0] - 1, at[1] - 1, at[0] + 1, at[1] + 1), fill=colour)
        previous = at
    # The moments the state changes, numbered over their tick, alternately higher where two
    # lie close.
    moments, last_x, lift = [], None, 0
    for before, t in zip(run, run[1:]):
        if t['state'] != before['state']:
            moments.append(t)
    for n, t in enumerate(moments, 1):
        x, y = px(t['x']), py(t['y'])
        lift = 12 if last_x is not None and abs(x - last_x) < 24 and lift == 0 else 0
        draw.line((x, y - 3, x, y - 8 - lift), fill=MUTED)
        text(draw, (x - 2, y - 20 - lift), str(n))
        last_x = x
    x = left
    for state, (words, colour) in sorted(states.items()):
        draw.rectangle((x, 6, x + 7, 13), fill=colour)
        text(draw, (x + 11, 4), words)
        x += 11 + 6 * len(words) + 14
    text(draw, (left, 20), '  '.join('%d %s' % (n, figure['moments'][n - 1])
                                     for n in range(1, len(moments) + 1)))
    if len(moments) != len(figure['moments']):
        raise Failure('%s: the state changes %d times, the manifest names %d moments'
                      % (figure['name'], len(moments), len(figure['moments'])))
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
        wanted = {f['vblank'] for f in figures if f.get('run') == run and 'vblank' in f}
        paths = [f for f in figures if f.get('run') == run and f['maker'] == 'path']
        until = max([f['vblanks'][1] for f in paths], default=0)
        shots[run] = run_core(run, runs[run], wanted, until=until, ticks=bool(paths))
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
        elif maker == 'maprecord':
            make_maprecord(figure, path)
        elif maker == 'font':
            make_font(figure, path)
        elif maker == 'planes':
            make_planes(figure, path)
        elif maker == 'blit':
            make_blit(figure, path)
        elif maker == 'sample':
            make_sample(figure, path)
        elif maker == 'disk':
            make_disk(figure, path)
        elif maker == 'packed':
            make_packed(figure, path)
        elif maker == 'codemap':
            make_codemap(figure, path)
        elif maker == 'pairs':
            make_pairs(figure, path)
        elif maker == 'fade':
            make_fade(figure, path)
        elif maker == 'record':
            make_record(figure, path)
        elif maker == 'clearset':
            make_clearset(figure, path)
        elif maker == 'mirror':
            make_mirror(figure, path)
        elif maker == 'path':
            make_path(figure, runs[figure['run']], shots[figure['run']]['ticks'], path)
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
