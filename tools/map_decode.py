"""The world maps of the game: the file, the records, and what a pass draws of them.

Answers `SPEC.md` section 10 point 5.  The decoder holds no game data: it reads a map from
`original/disk/Wings_of_Fury/maps/` when it runs.

    .venv/bin/python tools/map_decode.py                 every map: records and their kinds
    .venv/bin/python tools/map_decode.py --map a --list  one map's records, one line each
    .venv/bin/python tools/map_decode.py --map a --draw 7032
                                         what a pass draws with the player at that world x

A map is a strip of columns, **one record of two bytes per eight pixels of world x**.  The
record's bits are in `FIELDS` below; `re/notes/map.md` says what each one means and how it
was observed.  `draw_list` is `draw_world`'s own loop (`0x013772`, from `0x0137BC` to
`0x0138B8`) written out: given the view it returns the map draws of one pass, in order.
"""
import argparse
import os
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
MAPS = os.path.join(ROOT, 'original', 'disk', 'Wings_of_Fury', 'maps')
NAMES = [chr(c) for c in range(ord('a'), ord('o') + 1)]

WORLD_PER_RECORD = 8            # a record covers eight pixels of world x
HEIGHT_STEP = 4                 # one height step is four screen rows
SCREEN_END = 0x1D0              # draw_world stops when the screen x reaches this
MARGIN_FULL, MARGIN_EIGHTH = 0x120, 0x900


def fields(word):
    """The fields of one map record."""
    return {
        'draw': bool(word & 0x8000),          # bit 15: this record draws its shape
        'slot': (word >> 2) & 0x1FF,          # bits 2-10: the slot in MasterList or AthList
        'height': (word >> 11) & 7,           # bits 11-13: height steps above the horizon
        'low': word & 3,                      # bits 0-1: 1 rides on a ship, 2 stands on the world
        'bit14': bool(word & 0x4000),
    }


class Map:
    """One map file: the two leading longs and the record list."""

    def __init__(self, name, data):
        self.name = name
        self.file_length = len(data)
        self.length, self.start = struct.unpack_from('>LL', data, 0)
        # The first long is the file's own length, and the loader reads that many bytes of
        # records after the eight-byte header: the last eight bytes of the list are never
        # read from the file and are whatever the allocation held.  Here they are zero,
        # which is what the harness's fresh memory gives them.
        self.on_disk = (len(data) - 8) // 2
        self.padding = self.length // 2 - self.on_disk
        self.words = list(struct.unpack_from('>%dH' % self.on_disk, data, 8)) + [0] * self.padding
        # What the loader 0x012ADC computes from the two longs.
        self.extent = (self.length * 4) & 0xFFFF          # world x past the last record
        self.player_x = (self.start * 4 - 8) & 0xFFFF     # where the player starts

    def __len__(self):
        return len(self.words)

    def record(self, index):
        found = fields(self.words[index])
        found['index'] = index
        found['x'] = index * WORLD_PER_RECORD
        found['word'] = self.words[index]
        return found

    def records(self):
        return [self.record(i) for i in range(len(self.words))]


def load(name):
    with open(os.path.join(MAPS, '%s.map' % name), 'rb') as f:
        return Map(name, f.read())


def draw_list(chart, player_x, view_step=8, view_shift=0, split_row=0, slot_used=None,
              ride=None):
    """The map draws of one pass, in the order `draw_world` makes them.

    player_x is the drawing's copy of the player's world x (`0x026E5C`).  slot_used(slot)
    says whether that slot of the pointer table holds a shape; a null slot is skipped.
    ride(world_x) gives the rows a record of `low` 1 is moved down by, which is the ship it
    stands on (`0x014EAC` through `0x014A4E`); without it such a record keeps its own row.
    Returns [(index, slot, screen_x, screen_y, record)], where screen_x and screen_y are
    what `draw_world` hands `shape_draw` before the shape's hotspot is taken off."""
    x = player_x & 0xFFF8 if view_step == 1 else player_x
    margin = MARGIN_FULL if view_step == 8 else MARGIN_EIGHTH
    offset = (((x - margin) & 0xFFFF) ^ 0x8000) - 0x8000        # a signed word
    offset = (offset >> 2) & ~1                                 # asr.w #2, then bclr #0
    index = offset // 2
    screen_x = (8 - (x & 7) - 128)
    out = []
    while screen_x < SCREEN_END:
        if 0 <= index < len(chart.words) - 1:        # the last record is read but never drawn
            record = chart.record(index)
            if record['draw'] and (slot_used is None or slot_used(record['slot'])):
                y = 0x97 if view_shift else split_row + HEIGHT_STEP * record['height']
                if record['low'] == 1 and ride is not None:
                    world_x = (screen_x - 0xA0) * (8 if view_shift else 1) + player_x
                    y += ride(world_x & 0xFFFF)
                out.append((index, record['slot'], screen_x - 8, y, record))
        index += 1
        screen_x += view_step
    return out


def summary(chart):
    """Per map: the record count, the kinds that occur and how often."""
    drawn, plain = {}, {}
    for record in chart.records():
        (drawn if record['draw'] else plain).setdefault(record['slot'], 0)
        target = drawn if record['draw'] else plain
        target[record['slot']] += 1
    return drawn, plain


def main():
    parser = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    parser.add_argument('--map', help='one map by its letter')
    parser.add_argument('--list', action='store_true', help='every record of that map')
    parser.add_argument('--draw', type=lambda v: int(v, 0), help='the draws of a pass at this world x')
    args = parser.parse_args()

    if args.map:
        chart = load(args.map)
        print('%s.map: %d bytes, length long %d, start long %d -> player x %d, extent %d, '
              '%d records, %d of them past the file'
              % (chart.name, chart.file_length, chart.length, chart.start, chart.player_x,
                 chart.extent, len(chart), chart.padding))
        if args.list:
            for record in chart.records():
                if record['word']:
                    print('  %4d x=%5d word %04x slot %03x height %d low %d%s'
                          % (record['index'], record['x'], record['word'], record['slot'],
                             record['height'], record['low'], '  draw' if record['draw'] else ''))
        if args.draw is not None:
            for index, slot, screen_x, screen_y, _ in draw_list(chart, args.draw):
                print('  record %4d slot %03x  screen x %4d y %3d' % (index, slot, screen_x, screen_y))
        return 0

    print('%-5s %7s %7s %5s %8s %8s %7s  %s' % ('map', 'bytes', 'records', 'past', 'player x',
                                                'extent', 'drawn', 'slots that draw'))
    for name in NAMES:
        chart = load(name)
        drawn, plain = summary(chart)
        print('%-5s %7d %7d %5d %8d %8d %7d  %s' % (
            name, chart.file_length, len(chart), chart.padding, chart.player_x, chart.extent,
            sum(drawn.values()), ' '.join('%03x' % slot for slot in sorted(drawn))))
    return 0


if __name__ == '__main__':
    sys.exit(main())
