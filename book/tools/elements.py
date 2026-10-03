#!/usr/bin/env python3
"""The data of the book's two interactive elements, made from the game's files.

    .venv/bin/python book/tools/elements.py            the data into book/docs/generated/browser/
                                                       and book/docs/generated/maps/
    .venv/bin/python book/tools/elements.py --check    make it into a temporary directory and
                                                       compare with the committed files
    .venv/bin/python book/tools/elements.py --out DIR  write into DIR instead

The shape browser (docs/browser.md, docs/javascripts/browser.js) reads browser/:

    index.json       the twelve containers in the order the game loads them, with their counts
    <name>.png       one container's sheet: every shape once at its own size, in rows, colour 0
                     transparent, the colours through the palette the game shows it in
    <name>.json      its shapes in the container's order, each with its header's fields, its
                     mask by shape_draw's rule and its place in the sheet

The map viewer (docs/maps.md, docs/javascripts/maps.js) reads maps/:

    index.json       the fifteen maps with their counts
    <map>-<n>.png    a map's picture in bands of BAND pixels of world x: the playfield's rows,
                     the sky's colour above the horizon's row and the sea's from it, and every
                     record with the draw flag drawn in place, the ships' records too
    <map>.json       the map's two longs and what the loader derives from them, its counts, its
                     ships, airfields and slots, and every record with its fields

Everything comes from the disk's files when this runs: the containers through tools/ppkc.py,
the maps through tools/map_decode.py, and from the executable through re/tables.toml and
tools/extract_tables.py the name lists, the containers' and the palettes' file names as the
game spells them, and the mask buffer's size.  It needs no ROM, no native library and no
browser.  What it makes is deterministic (a PNG of Pillow carries no time, the JSON is written
in a fixed order), and --check holds the committed files to it byte for byte.

Exit status: 0 done (or --check found the committed files equal), 1 --check found a
difference, 2 the data could not be made.
"""
import argparse
import json
import pathlib
import sys
import tempfile
import tomllib

from common import GENERATED, ROOT, Failure, compare, rel, replace_tree
from figures import SHAPES, executable_names, palette

import ppkc                     # tools/, on the path through common

PARTS = ('browser', 'maps')

# The twelve containers in the order the game loads them (re/notes/shapes.md, "When containers
# are loaded and freed"): the five that stay, the rank selection's, the dashboard's by day and
# by night, the four ships'.  Each is named by the entry of re/tables.toml that holds its file
# name as the game spells it, and comes with the palette the game shows it in, by the entry that
# names that file: the playfield's by day for the world, the aircraft, the weapons and the ships;
# the dashboard picture's own sixteen colours for the dashboard's shapes, by day and by night
# (re/notes/display.md, "Day and night"); the rank selection picture's for its shapes, which the
# game draws over that picture (re/notes/frontend.md).
CONTAINERS = [
    (('world_shp',), ('palette_files', 0), "the playfield's palette by day"),
    (('eighth_shp',), ('palette_files', 0), "the playfield's palette by day"),
    (('hellcat_shp',), ('palette_files', 0), "the playfield's palette by day"),
    (('torpedo_shp',), ('palette_files', 0), "the playfield's palette by day"),
    (('japplane_shp',), ('palette_files', 0), "the playfield's palette by day"),
    (('selectrank_shp',), ('selectrank_pic',), "the colours of the rank selection's picture"),
    (('dash_shape_files', 0), ('dash_picture_files', 0), "the dashboard picture's colours by day"),
    (('dash_shape_files', 1), ('dash_picture_files', 1), "the dashboard picture's colours by night"),
    (('battleship_shp',), ('palette_files', 0), "the playfield's palette by day"),
    (('destroyer_shp',), ('palette_files', 0), "the playfield's palette by day"),
    (('cruiseship_shp',), ('palette_files', 0), "the playfield's palette by day"),
    (('japcarrier_shp',), ('palette_files', 0), "the playfield's palette by day"),
]

# load_permanent_shapes writes the mirror marker into every record of these two (0x012A1C,
# 0x012A52; re/notes/shapes.md, "Record header, complete").
MIRRORED = {'hellcat_shp', 'torpedo_shp'}

# alloc_pools sizes the mask buffer with move.l #$410,d0 at 0x012892: the long of the
# instruction's immediate.  shape_draw gives no mask to a shape whose stored plane is larger.
MASK_BUFFER_SIZE = 0x012894

SHEET_WIDTH = 512               # a sheet is this wide; the widest shape is 256 pixels
GAP = 2                         # transparent pixels between two shapes of a sheet

# MasterList at full scale as build_master_lists (0x01535A) fills it before every mission: the
# world's list, then the four ships' lists in this order, each resolved in its own container
# (re/notes/shapes.md, "MasterList and AthList").  A ship's run of records is named by its list.
MASTER_LIST = [
    ('world_names', 'world_shp', "the player's carrier"),
    ('cruiseship_names', 'cruiseship_shp', 'cruise ship'),
    ('destroyer_names', 'destroyer_shp', 'destroyer'),
    ('japcarrier_names', 'japcarrier_shp', 'Japanese carrier'),
    ('battleship_names', 'battleship_shp', 'battleship'),
]
TABLE_ENTRIES = 278             # alloc_pools: 0x458 bytes each for MasterList and AthList

# The slots past the lists are null, and the maps use them as markers that draw nothing: a
# pair at the two ends of every ship, which nothing reads; one beside an island's flag, which
# draw_world's extras draw (0x013B46); the pairs of an airfield, which airfields_scan reads
# (0x012CDE, 0x012D18).  Chapter 13, "The record, bit by bit".
SHIP_WEST, SHIP_EAST = 0x111, 0x112
AIRFIELD = (0x114, 0x115)
MARKERS = {SHIP_WEST: "a ship's west end", SHIP_EAST: "a ship's east end",
           0x113: "an island's flag", 0x114: "an airfield's marker",
           0x115: "an airfield's marker"}
ISLAND_SLOT = 2                 # map_scan counts an island by a drawn record of slot 2 (0x012D5A)

# The picture of a map: the playfield's 162 rows (re/notes/display.md, "The play screen line by
# line"), the horizon's row at 151 as at the mission's start (re/notes/map.md, "World
# coordinates"), the sky's colour 1 of the playfield's palette above it and from it the sea's
# colour, colour 10 of the ocean's palette, with which the game fills the sea at the eighth
# scale (0x013E6C).  The records' shapes are drawn in the playfield's palette, as chapter 13's
# figure draws them, by the blit's rule (blitted below).
ROWS = 162
SPLIT_ROW = 151
SKY, SEA = 1, 10
BAND = 4096                     # a map's picture in bands this wide, so that no image is wider
                                # than the textures every phone's graphics draws


# ------------------------------------------------------------------ the executable

_image, _tables = None, None


def image():
    global _image
    if _image is None:
        import extract_tables
        _image = extract_tables.Image(extract_tables.EXE)
    return _image


def tables():
    global _tables
    if _tables is None:
        with open(ROOT / 're' / 'tables.toml', 'rb') as handle:
            _tables = {t['name']: t for t in tomllib.load(handle)['table']}
    return _tables


def file_name(entry):
    """A file name as the game spells it, without its directory: (name,) is a string of
    re/tables.toml, (name, i) the i-th of a table of pointers to strings."""
    if entry[0] not in tables():
        raise Failure('re/tables.toml has no table %s' % entry[0])
    address = tables()[entry[0]]['addr']
    if len(entry) == 2:
        address = image().u32(address + 4 * entry[1])
    return image().cstr(address).decode('latin1').split('/')[-1]


def on_disk(name):
    """The disk's file for a name the game asks for: AmigaDOS compares without regard to case."""
    found = [p for p in SHAPES.iterdir() if p.name.lower() == name.lower()]
    if len(found) != 1:
        raise Failure('the disk has no file %s in shapes/' % name)
    return found[0]


def stem(container):
    """The generated files' name for a container: its name in lower case, without .shp."""
    return container.lower().rsplit('.', 1)[0]


# ------------------------------------------------------------------ writing

def write_json(path, data, rows=(), compact=False):
    """A JSON file in a fixed order: one top-level key a line, and each element of the lists
    named in `rows` on a line of its own."""
    separators = (',', ':') if compact else (', ', ': ')
    lines, items = [], list(data.items())
    for i, (key, value) in enumerate(items):
        comma = ',' if i < len(items) - 1 else ''
        if key in rows:
            inner = ',\n'.join('  ' + json.dumps(row, separators=separators) for row in value)
            lines.append(' %s: [\n%s\n ]%s' % (json.dumps(key), inner, comma) if value
                         else ' %s: []%s' % (json.dumps(key), comma))
        else:
            lines.append(' %s: %s%s' % (json.dumps(key), json.dumps(value, separators=(', ', ': ')),
                                        comma))
    path.write_text('{\n' + '\n'.join(lines) + '\n}\n', encoding='utf-8')


def indexed_image(width, height, pixels):
    from PIL import Image
    return Image.frombytes('P', (width, height), bytes(pixels))


# ------------------------------------------------------------------ the shape browser

def sheet_places(shapes):
    """Every shape's place in its sheet, left to right in rows in the container's order."""
    places, x, y, row = [], GAP, GAP, 0
    for shape in shapes:
        w, h = 8 * shape['wbytes'], shape['h']
        if x > GAP and x + w + GAP > SHEET_WIDTH:
            x, y, row = GAP, y + row + GAP, 0
        places.append([x, y, w, h])
        x += w + GAP
        row = max(row, h)
    return places, y + row + GAP


def make_sheet(shapes, colours, places, height, path):
    """The sheet as an indexed PNG: entry 0 transparent, the ground; a colour number through
    the palette, which on the dashboard's four planes keeps the number's low four bits; a
    pixel that is not 0 but lands on the palette's entry 0 through the copy of that entry past
    the palette's end, so that it stays opaque."""
    from PIL import Image
    count = len(colours)
    if count not in (16, 32):
        raise Failure('a palette of %d colours' % count)
    sheet = Image.new('P', (SHEET_WIDTH, height), 0)
    sheet.putpalette([c for rgb in colours + [colours[0]] for c in rgb])
    for shape, (x, y, w, h) in zip(shapes, places):
        pixels = [(v & (count - 1)) or (count if v else 0)
                  for row in ppkc.to_indexed(shape) for v in row]
        sheet.paste(indexed_image(w, h, pixels), (x, y))
    sheet.save(path, transparency=0)


def shape_facts(number, shape, place, mask_buffer, mirrored):
    planes = len(shape['masks'])
    plane_bytes = shape['wbytes'] * shape['h']
    if plane_bytes > mask_buffer:
        opaque = 'size'
    elif planes == 0:
        opaque = 'no plane'
    else:
        opaque = None
    cut_x, cut_y, planes_word = shape['u']
    return {
        'number': number,
        'name': shape['name'],
        'width': 8 * shape['wbytes'],
        'height': shape['h'],
        'width_bytes': shape['wbytes'],
        'hotspot': [shape['ox'], shape['oy']],
        'cut': [cut_x, cut_y],
        'clear': planes_word >> 8,
        'set': planes_word & 0xFF,
        'planes': planes,
        'plane_masks': shape['masks'],
        'plane_bytes': plane_bytes,
        'record_bytes': 20 + planes * plane_bytes,
        'opaque': opaque,
        'mirrored': mirrored,
        'sheet': place,
    }


def make_browser(out):
    out.mkdir(parents=True, exist_ok=True)
    mask_buffer = image().u32(MASK_BUFFER_SIZE)
    summary, total, opaque = [], 0, {'size': 0, 'no plane': 0}
    for name_entry, palette_entry, palette_note in CONTAINERS:
        container = file_name(name_entry)
        colour_file = file_name(palette_entry)
        shapes = ppkc.parse(str(on_disk(container)))
        colours = palette(on_disk(colour_file).name)
        mirrored = name_entry[0] in MIRRORED
        places, height = sheet_places(shapes)
        base = stem(container)
        make_sheet(shapes, colours, places, height, out / ('%s.png' % base))
        facts = [shape_facts(i, s, p, mask_buffer, mirrored)
                 for i, (s, p) in enumerate(zip(shapes, places))]
        for f in facts:
            if f['opaque']:
                opaque[f['opaque']] += 1
        write_json(out / ('%s.json' % base), {
            'container': container,
            'disk': on_disk(container).name,
            'palette': colour_file,
            'palette_note': palette_note,
            'palette_colours': len(colours),
            'mirrored': mirrored,
            'sheet': '%s.png' % base,
            'sheet_size': [SHEET_WIDTH, height],
            'shapes': facts,
        }, rows=('shapes',))
        summary.append({'container': container, 'file': base, 'shapes': len(shapes),
                        'palette': colour_file, 'mirrored': mirrored,
                        'opaque': sum(1 for f in facts if f['opaque'])})
        total += len(shapes)
    write_json(out / 'index.json', {
        'containers': summary,
        'shapes': total,
        'opaque': opaque,
        'mask_buffer': mask_buffer,
    }, rows=('containers',))
    return len(summary), total


# ------------------------------------------------------------------ the map viewer

def master_list():
    """MasterList at full scale, slot by slot: the name, its list, and the shape when the
    table holds one (a name the container lacks leaves the slot null)."""
    slots = []
    for names, container_entry, ship in MASTER_LIST:
        container = file_name((container_entry,))
        shapes = {s['name']: s for s in ppkc.parse(str(on_disk(container)))}
        for name in executable_names(names):
            found = shapes.get(name)
            slots.append(dict(name=name, list=names, ship=ship,
                              container=container if found else None, shape=found))
    if len(slots) > TABLE_ENTRIES:
        raise Failure('MasterList would hold %d slots of %d' % (len(slots), TABLE_ENTRIES))
    return slots


def slot_facts(slot, slots):
    """A slot of MasterList: its name and list, the container of its shape or None where the
    table holds none, and what a marker stands for."""
    if slot < len(slots):
        s = slots[slot]
        return {'slot': slot, 'name': s['name'], 'list': s['list'], 'shape': s['container'],
                'marker': None}
    if slot < TABLE_ENTRIES:
        return {'slot': slot, 'name': None, 'list': None, 'shape': None,
                'marker': MARKERS.get(slot)}
    raise Failure('slot %d is past MasterList\'s %d entries' % (slot, TABLE_ENTRIES))


def ships_of(chart, fields, slots):
    """Every ship of a map, a run of records from its west marker to its east marker, named by
    the list of the slots between them."""
    ends = [(i, f['slot']) for i, f in enumerate(fields) if f['slot'] in (SHIP_WEST, SHIP_EAST)]
    if len(ends) % 2:
        raise Failure('map %s: a ship marker without its pair' % chart.name)
    ships = []
    for (west, a), (east, b) in zip(ends[0::2], ends[1::2]):
        if (a, b) != (SHIP_WEST, SHIP_EAST):
            raise Failure('map %s: the ship markers at %d and %d are not west and east'
                          % (chart.name, west, east))
        kinds = {slots[f['slot']]['ship'] for f in fields[west + 1:east]
                 if f['slot'] < len(slots) and chart.words[f['index']]}
        if len(kinds) != 1:
            raise Failure('map %s: records %d to %d hold %s' % (chart.name, west, east,
                                                                 sorted(kinds) or 'no ship'))
        ships.append({'ship': kinds.pop(), 'west': west, 'east': east})
    return ships


def airfields_of(fields):
    """The airfields as airfields_scan pairs their markers: every second ends one."""
    marks = [i for i, f in enumerate(fields) if f['slot'] in AIRFIELD]
    return [{'first': a, 'second': b} for a, b in zip(marks[0::2], marks[1::2])]


def blitted(shape, mask_buffer):
    """A shape's pixels as shape_draw leaves them on the playfield's five planes, and whether
    it is opaque, its whole box written, colour 0 too.  A pixel is the stored planes' colour
    number with the set byte's planes that no plane mask names; the clear byte takes nothing
    away that shows, and no plane of the background shows through, because in every shape the
    plane masks, the clear and the set byte together name all five planes (chapter 12)."""
    union = 0
    for m in shape['masks']:
        union |= m
    clear, sets = shape['u'][2] >> 8, shape['u'][2] & 0xFF
    if (union | clear | sets) & 0x1F != 0x1F:
        raise Failure('%s leaves planes of the background to show' % shape['name'])
    add = sets & ~union & 0x1F
    opaque = shape['wbytes'] * shape['h'] > mask_buffer or not shape['masks']
    pixels = [v | add if v or opaque else 0 for row in ppkc.to_indexed(shape) for v in row]
    return pixels, opaque


def make_map(chart, slots, colours, sea, mask_buffer, out):
    import map_decode
    from PIL import Image

    # Every draw of the whole map, as the figures' map maker finds them: draw_list for views a
    # band of 256 pixels apart, each draw put back into world x (the player stands at screen x
    # 160), each record once.  A ship's record rides its ship, which at the mission's start has
    # not sunk: it is drawn at its own row.
    draws, view = {}, 0
    while view < chart.extent + 512:
        for index, slot, screen_x, screen_y, _ in map_decode.draw_list(chart, view,
                                                                       split_row=SPLIT_ROW):
            draws[index] = (slot, screen_x + view - 160, screen_y)
        view += 256

    picture = Image.new('P', (chart.extent, ROWS), SKY)
    picture.putpalette([c for rgb in colours + [sea] for c in rgb])
    picture.paste(len(colours), (0, SPLIT_ROW, chart.extent, ROWS))
    shapes, boxes = {}, []
    for index in sorted(draws):
        slot, x, y = draws[index]
        shape = slots[slot]['shape'] if slot < len(slots) else None
        if shape is None:
            continue                    # a null slot, which draw_world skips
        w, h = 8 * shape['wbytes'], shape['h']
        left, top = x - shape['ox'], y - shape['oy']
        pixels, opaque = blitted(shape, mask_buffer)
        mask = Image.frombytes('L', (w, h), bytes(255 if v or opaque else 0 for v in pixels))
        picture.paste(indexed_image(w, h, pixels), (left, top), mask)
        shapes[index] = shape['name']
        boxes.append([index, left, top, w, h])

    bands = []
    for n, x0 in enumerate(range(0, chart.extent, BAND)):
        width = min(BAND, chart.extent - x0)
        name = '%s-%d.png' % (chart.name, n)
        picture.crop((x0, 0, x0 + width, ROWS)).save(out / name)
        bands.append({'file': name, 'x': x0, 'width': width})

    fields = []
    for i, word in enumerate(chart.words):
        f = map_decode.fields(word)
        f['index'] = i
        fields.append(f)
    rows = [[i, 8 * i, chart.words[i], int(f['draw']), int(f['bit14']), f['height'], f['slot'],
             f['low'], shapes.get(i)] for i, f in enumerate(fields)]
    used = sorted({f['slot'] for f in fields})
    ships = ships_of(chart, fields, slots)
    airfields = airfields_of(fields)
    counts = {
        'records': len(chart.words),
        'drawn': sum(1 for f in fields if f['draw']),
        'islands': sum(1 for f in fields if f['draw'] and f['slot'] == ISLAND_SLOT),
        'enemy_ships': [s['ship'] for s in ships if s['ship'] != MASTER_LIST[0][2]],
        'airfields': len(airfields),
    }
    write_json(out / ('%s.json' % chart.name), {
        'map': chart.name,
        'file': 'maps/%s.map' % chart.name,
        'file_bytes': chart.file_length,
        'longs': [chart.length, chart.start],
        'records_from_file': chart.on_disk,
        'extent': chart.extent,
        'player_x': chart.player_x,
        'rows': ROWS,
        'split_row': SPLIT_ROW,
        'bands': bands,
        'counts': counts,
        'ships': ships,
        'airfields': airfields,
        'slots': [slot_facts(s, slots) for s in used],
        'columns': ['index', 'x', 'word', 'draw', 'bit14', 'height', 'slot', 'low', 'shape'],
        'records': rows,
        'draws': boxes,
    }, rows=('bands', 'ships', 'airfields', 'slots', 'records', 'draws'), compact=True)
    return dict({'map': chart.name, 'extent': chart.extent, 'player_x': chart.player_x}, **counts)


def make_maps(out):
    import map_decode
    out.mkdir(parents=True, exist_ok=True)
    slots = master_list()
    colours = palette(on_disk(file_name(('palette_files', 0))).name)
    ocean = file_name(('ocean_palette_files', 0))
    sea = palette(on_disk(ocean).name)[SEA]
    mask_buffer = image().u32(MASK_BUFFER_SIZE)
    summary = [make_map(map_decode.load(name), slots, colours, sea, mask_buffer, out)
               for name in map_decode.NAMES]
    write_json(out / 'index.json', {
        'maps': summary,
        'palette': file_name(('palette_files', 0)),
        'sea': [ocean, SEA],
        'band': BAND,
    }, rows=('maps',))
    return len(summary), sum(m['records'] for m in summary)


# ------------------------------------------------------------------ the command

def generate(out):
    out = pathlib.Path(out)
    containers, shapes = make_browser(out / 'browser')
    maps, records = make_maps(out / 'maps')
    return containers, shapes, maps, records


def main():
    parser = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    parser.add_argument('--check', action='store_true',
                        help='compare a fresh generation with the committed files, write nothing')
    parser.add_argument('--out', help='write into this directory instead')
    args = parser.parse_args()
    try:
        if args.out:
            made = generate(args.out)
        else:
            with tempfile.TemporaryDirectory() as temp:
                made = generate(temp)
                if args.check:
                    problems = [p for part in PARTS
                                for p in compare(pathlib.Path(temp) / part, GENERATED / part)]
                    for line in problems:
                        print(line)
                    print('elements  %d containers, %d shapes, %d maps, %d records checked, %s'
                          % (made + ('%d differ' % len(problems) if problems
                                     else 'all equal to the committed files',)))
                    return 1 if problems else 0
                for part in PARTS:
                    replace_tree(pathlib.Path(temp) / part, GENERATED / part)
        print('elements  %d containers, %d shapes, %d maps, %d records written to %s'
              % (made + (args.out or ' and '.join(rel(GENERATED / p) for p in PARTS),)))
        return 0
    except Failure as failure:
        print('elements  FAILED: %s' % failure, file=sys.stderr)
        return 2


if __name__ == '__main__':
    sys.exit(main())
