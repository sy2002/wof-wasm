"""The saved game's layout (M7): what save_game_write (0x015E8A) writes and save_game_read
(0x015E1A) reads, through the walker sub_015ec2 and its callbacks (re/notes/campaign.md).

The walker hands its callback (file, address, length, flag) for, in this order:

  raw      object_records (0x024CAE) up to target_records_4 (0x0254F8), 0x84A bytes of
           memory as they stand, flag 0: registered globals, the fixed tables, pointers;
  length   map_length (0x0253C6), 2 bytes, flag 0;
  map      map_records (0x024628), flag 1: the block the pointer names, map_length bytes;
  guns     for each of the five ship records (0x025460, 0x1E bytes each) whose words at +4
           and +0x12 are set, the gun list its +6 names, 14 x the word at +0x0A bytes;
  (sub_015d62, which is empty)
  f        target_records_f, 14 x target_count_f bytes, flag 1;
  soldiers soldier_records, 8 x soldier_count bytes, flag 1;
  3        target_records_3, 16 x target_count_3 bytes, flag 1;
  4        target_records_4, 16 x target_count_4 bytes, flag 1.

The counts are read from the raw part the file begins with, so a file describes its own
layout, which is how save_game_read finds it and how this module decodes it.

    .venv/bin/python tools/savegame.py FILE              the file's sections and what it holds
    .venv/bin/python tools/savegame.py FILE --fields     and every field of the raw part by name
    .venv/bin/python tools/savegame.py --disk            the disk's own `wof.mission 3`
"""
import argparse
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)

RAW_START, RAW_END = 0x024CAE, 0x0254F8          # object_records, target_records_4
RAW_LENGTH = RAW_END - RAW_START                 # 0x84A
SHIPS, SHIP_SIZE = 0x025460, 0x1E
SHIP_NAMES = ('destroyer', 'battleship', 'cruiseship', 'japcarrier', 'carrier')
GUN_SIZE = 14
MAP_LENGTH = 0x0253C6
TARGET_COUNT_F, TARGET_COUNT_3, TARGET_COUNT_4 = 0x025385, 0x025386, 0x025387
SOLDIER_COUNT = 0x0253C4
RANK_PLAYED, MISSION_NUMBER = 0x0253BE, 0x0253C0
PLAYER_SCORE, LIVES = 0x02534C, 0x02535C
MISSIONS_PER_RANK = (3, 3, 2, 2, 1, 1, 3)        # 0x025548, read from the executable below
DISK_FILE = os.path.join(ROOT, 'original', 'disk', 'Wings_of_Fury', 'wof.mission 3')
LETTERS = 'abcdefghijklmno'


def raw_word(raw, address):
    return int.from_bytes(raw[address - RAW_START:address - RAW_START + 2], 'big')


def raw_byte(raw, address):
    return raw[address - RAW_START]


def raw_long(raw, address):
    return int.from_bytes(raw[address - RAW_START:address - RAW_START + 4], 'big')


def layout(raw):
    """The file's sections as (name, size), from its raw part: the order of the walker."""
    out = [('raw', RAW_LENGTH), ('length', 2), ('map', raw_word(raw, MAP_LENGTH))]
    for i, name in enumerate(SHIP_NAMES):
        ship = SHIPS + SHIP_SIZE * i
        if raw_word(raw, ship + 4) and raw_word(raw, ship + 0x12):
            out.append(('guns ' + name, GUN_SIZE * raw_word(raw, ship + 0x0A)))
    # The counts are bytes the walker sign-extends (ext.w) before its unsigned multiply.
    signed = lambda b: b - 0x100 if b & 0x80 else b
    out.append(('f', (GUN_SIZE * signed(raw_byte(raw, TARGET_COUNT_F))) & 0xFFFF))
    out.append(('soldiers', (8 * raw_word(raw, SOLDIER_COUNT)) & 0xFFFF))
    out.append(('3', (16 * signed(raw_byte(raw, TARGET_COUNT_3))) & 0xFFFF))
    out.append(('4', (16 * signed(raw_byte(raw, TARGET_COUNT_4))) & 0xFFFF))
    return out


def sections(data):
    """{section: bytes} of a saved game, and whether the sizes account for the file."""
    raw = data[:RAW_LENGTH]
    out = {}
    at = 0
    for name, size in layout(raw):
        out[name] = data[at:at + size]
        at += size
    return out, at == len(data)


def map_letter(length):
    """The map whose file is `length` long (the fifteen are all of different lengths)."""
    for letter in LETTERS:
        path = os.path.join(ROOT, 'original', 'disk', 'Wings_of_Fury', 'maps', letter + '.map')
        with open(path, 'rb') as handle:
            if int.from_bytes(handle.read(4), 'big') == length:
                return letter
    return None


def summary(data):
    """What a saved game holds: the map, the rank, the mission, the score, the lives and the
    count of every table."""
    parts, exact = sections(data)
    raw = parts['raw']
    rank, mission = raw_word(raw, RANK_PLAYED), raw_word(raw, MISSION_NUMBER)
    index = sum(MISSIONS_PER_RANK[:min(rank, 7)]) + mission - 1
    return {
        'size': len(data), 'exact': exact,
        'sections': [(name, len(parts[name])) for name, _ in layout(raw)],
        'map': map_letter(raw_word(raw, MAP_LENGTH)),
        'map_by_rank': LETTERS[index] if 0 <= index < 15 else None,
        'rank': rank, 'mission': mission, 'score': raw_long(raw, PLAYER_SCORE),
        'lives': raw_byte(raw, LIVES),
        'target_count_f': raw_byte(raw, TARGET_COUNT_F),
        'target_count_3': raw_byte(raw, TARGET_COUNT_3),
        'target_count_4': raw_byte(raw, TARGET_COUNT_4),
        'soldier_count': raw_word(raw, SOLDIER_COUNT),
        'islands': raw_byte(raw, 0x025384), 'islands_left': raw_byte(raw, 0x025383),
        'player_on_deck': raw_word(raw, 0x025084),
        'ships': [name for name, _ in layout(raw) if name.startswith('guns ')],
    }


# ------------------------------------------------------------------ the fields by name

def registry():
    """[(first, last, name, kind)] of the registered globals and the fixed tables' fields
    that lie in the raw range, from src/globals.def, src/mission.def and src/records.def."""
    sizes = {'uint8_t': 1, 'int8_t': 1, 'uint16_t': 2, 'int16_t': 2, 'uint32_t': 4,
             'int32_t': 4}
    out = []
    with open(os.path.join(ROOT, 'src', 'globals.def')) as handle:
        text = handle.read()
    for name, ctype, address in re.findall(
            r'^WOF_GLOBAL\((\w+),\s*(\w+),\s*(0x[0-9A-Fa-f]+)\)', text, re.M):
        out.append((int(address, 16), int(address, 16) + sizes[ctype] - 1, name, 'plain'))
    for name, ctype, count, address in re.findall(
            r'^WOF_GLOBAL_ARRAY\((\w+),\s*(\w+),\s*(\d+),\s*(0x[0-9A-Fa-f]+)\)', text, re.M):
        for i in range(int(count)):
            a = int(address, 16) + i * sizes[ctype]
            out.append((a, a + sizes[ctype] - 1, '%s[%d]' % (name, i), 'plain'))
    with open(os.path.join(ROOT, 'src', 'records.def')) as handle:
        rtext = handle.read()
    records = {}
    for rec, size in re.findall(r'^WOF_RECORD\((\w+),\s*(0x[0-9A-Fa-f]+|\d+)\)', rtext, re.M):
        records[rec] = {'size': int(size, 0), 'fields': []}
    for rec, name, ctype, offset, kind in re.findall(
            r'^WOF_FIELD\((\w+),\s*(\w+),\s*(\w+),\s*(0x[0-9A-Fa-f]+),\s*WOF_K_(\w+)\)', rtext, re.M):
        width = 4 if kind != 'PLAIN' else sizes[ctype]
        records[rec]['fields'].append((int(offset, 16), width, name, kind.lower()))
    for rec, name, ctype, count, offset, kind in re.findall(
            r'^WOF_FIELD_ARRAY\((\w+),\s*(\w+),\s*(\w+),\s*(\d+),\s*(0x[0-9A-Fa-f]+),\s*WOF_K_(\w+)\)',
            rtext, re.M):
        for i in range(int(count)):
            records[rec]['fields'].append((int(offset, 16) + i * sizes[ctype], sizes[ctype],
                                           '%s[%d]' % (name, i), kind.lower()))
    with open(os.path.join(ROOT, 'src', 'mission.def')) as handle:
        mtext = handle.read()
    for name, rec, count, address in re.findall(
            r'^WOF_TABLE\((\w+),\s*(\w+),\s*(\d+),\s*(0x[0-9A-Fa-f]+)\)', mtext, re.M):
        base, size = int(address, 16), records[rec]['size']
        for i in range(int(count)):
            for offset, width, field, kind in records[rec]['fields']:
                a = base + i * size + offset
                out.append((a, a + width - 1, '%s[%d].%s' % (name, i, field), kind))
    return sorted(e for e in out if RAW_START <= e[0] < RAW_END)


def field_of(address, fields=None):
    """(name, kind) of the registered field that covers an address of the raw range, or
    None where nothing the port keeps covers it."""
    for first, last, name, kind in fields if fields is not None else registry():
        if first <= address <= last:
            return name, kind
    return None


def main():
    parser = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    parser.add_argument('file', nargs='?')
    parser.add_argument('--disk', action='store_true', help="the disk's wof.mission 3")
    parser.add_argument('--fields', action='store_true')
    args = parser.parse_args()
    path = DISK_FILE if args.disk or not args.file else args.file
    with open(path, 'rb') as handle:
        data = handle.read()
    info = summary(data)
    for key, value in info.items():
        print('%-16s %s' % (key, value))
    if args.fields:
        raw = data[:RAW_LENGTH]
        fields = registry()
        covered = set()
        for first, last, name, kind in fields:
            value = raw[first - RAW_START:last - RAW_START + 1]
            covered.update(range(first, last + 1))
            print('%06X  +%03X  %-40s %-6s %s' % (first, first - RAW_START, name, kind, value.hex()))
        gaps = sorted(set(range(RAW_START, RAW_END)) - covered)
        print('%d bytes of the raw part are no registered field' % len(gaps))
    return 0


if __name__ == '__main__':
    sys.exit(main())
