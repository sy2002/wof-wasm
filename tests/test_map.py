"""M4's groundwork: the map records and the world coordinate system (SPEC 10 point 5).

The decoder of tools/map_decode.py is held to the original in three ways: it parses every map
of the disk without a byte left over; it predicts, for every pass of a flight, exactly the map
draws the original made, with the slot and the position of each; and a map with one record
changed changes exactly the draws and the ground height it says it does and nothing else.

The findings themselves are in re/notes/map.md.
"""
import os
import random
import struct
import sys

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, 'tools'))

import headless                    # noqa: E402
import map_decode                  # noqa: E402
from oracle import Oracle          # noqa: E402

A4 = 0x02AFFE
GROUND_HEIGHT = 0x015714           # A0 = a map record, D0 = the height of its ground
CLASS_HEIGHTS = 0x0257C2           # six words, the ground height of each terrain class
MAP_BASE, MAP_END = 0x024628, 0x02462C
MAP_LENGTH, MAP_EXTENT, PLAYER_START = 0x0253C6, 0x024630, 0x025392
MASTER_LIST, ATH_LIST = 0x026F54, 0x026F82
VIEW_X, SPLIT_ROW, Y_BASE, PLAYER_DRAW_X = 0x024F30, 0x0253A0, 0x026E56, 0x026E5C
MAP_DRAW_RETURN = 0x0138AC         # the return address of draw_world's own shape_draw call
SHIPS = [(0x02537A, 0x025460), (0x025377, 0x02547E), (0x02537B, 0x02549C),
         (0x025378, 0x0254BA), (None, 0x0254D8)]
SHIP_BLOCK = (0x025440, 0x100)
GROUND_OFF, GROUND_SUB = 0x0253AE, 0x025396

FRONT = [[30, ''], [3, 'F']] * 5
TAKE_OFF = [[40, ''], [3, 'F'], [60, ''], [460, 'R'], [400, 'RU']]
WATCH = {'view': (VIEW_X, 8), 'player_x': (PLAYER_DRAW_X, 2), 'split_row': (SPLIT_ROW, 2),
         'y_base': (Y_BASE, 2), 'ships': SHIP_BLOCK}


def signed(value, bits=16):
    return (value ^ (1 << (bits - 1))) - (1 << (bits - 1))


def flight(**more):
    description = {'raw': FRONT + TAKE_OFF + [[700, 'R']], 'stop': {'vblanks': 1500}}
    description.update(more)
    machine = headless.Headless(description, observe=['draw_world', 'shape_draw'],
                                watch=WATCH, watch_for=['draw_world'])
    machine.run()
    return machine


def passes_of(machine):
    """Every pass of a run: the view as draw_world found it, and the map draws it made."""
    found = []
    for record in machine.observed:
        if record['routine'] == 'draw_world':
            view = bytes.fromhex(record['memory']['view'])
            found.append({
                'pass': record['pass'],
                'view_shift': int.from_bytes(view[4:6], 'big'),
                'view_step': int.from_bytes(view[6:8], 'big'),
                'player_x': int(record['memory']['player_x'], 16),
                'y_base': signed(int(record['memory']['y_base'], 16)),
                'split_row': int(record['memory']['split_row'], 16),
                'ships': bytes.fromhex(record['memory']['ships']),
                'draws': []})
        elif record['routine'] == 'shape_draw' and record['caller'] == MAP_DRAW_RETURN and found:
            found[-1]['draws'].append((record['a'][0], record['d'][0] & 0xFFFF,
                                       record['d'][1] & 0xFFFF))
    return found


def tables_of(machine):
    """slot -> pointer, for the full-scale and the eighth-scale table."""
    out = {}
    for step, at in ((8, MASTER_LIST), (1, ATH_LIST)):
        table = machine.o.r32(at)
        out[step] = [machine.o.r32(table + 4 * i) for i in range(273)]
    return out


def rider(view):
    """0x014EAC: a record of `low` 1 stands on a ship and moves with it.  The ship is the one
    whose span of map offsets holds the record (0x014A4E)."""
    block = view['ships']

    def word(at):
        return signed(int.from_bytes(block[at - SHIP_BLOCK[0]:at - SHIP_BLOCK[0] + 2], 'big'))

    def ride(world_x):
        offset = signed(((world_x >> 3) * 2) & 0xFFFF)
        for flag, base in SHIPS:
            if flag is not None and not block[flag - SHIP_BLOCK[0]]:
                continue
            if word(base) <= offset <= word(base + 2):
                value = word(base + 0x1A) + view['y_base']
                return value >> 3 if view['view_shift'] else value
        return 0
    return ride


def predicted(chart, view, tables):
    table = tables[1 if view['view_step'] == 1 else 8]
    found = map_decode.draw_list(chart, view['player_x'], view['view_step'], view['view_shift'],
                                 view['split_row'], lambda slot: table[slot] != 0, rider(view))
    return [(slot, x, y) for _, slot, x, y, _ in found]


def observed(machine, view, tables):
    """The map draws the original made, back in the decoder's terms: the slot of the shape and
    the position before the shape's hotspot was taken off."""
    table = tables[1 if view['view_step'] == 1 else 8]
    slot_of = {}
    for slot, pointer in enumerate(table):
        if pointer:
            slot_of.setdefault(pointer, slot)
    out = []
    for pointer, d0, d1 in view['draws']:
        out.append((slot_of.get(pointer),
                    signed(d0) + machine.o.r16(pointer + 4, signed=True),
                    signed(d1) + machine.o.r16(pointer + 6, signed=True)))
    return out


@pytest.fixture(scope='module')
def flown():
    machine = flight()
    return machine, passes_of(machine), tables_of(machine)


# ------------------------------------------------------------------ the file

def test_every_map_of_the_disk_parses_without_a_byte_left_over():
    """The first long is the file's own length, the second gives the player's start.  The
    record list runs to the end of the file, and the loader reads eight bytes more than the
    file holds, so the last four records of every map never come from it; they are zero,
    because every allocation the game makes asks AllocMem for MEMF_CLEAR (re/notes/map.md)."""
    for name in map_decode.NAMES:
        chart = map_decode.load(name)
        assert chart.length == chart.file_length, name
        assert chart.padding == 4, name
        assert len(chart) == chart.length // 2
        assert chart.extent == len(chart) * map_decode.WORLD_PER_RECORD
        assert chart.player_x == chart.start * 4 - 8
        assert 0 < chart.player_x < chart.extent


def test_the_map_the_first_mission_loads_is_the_one_the_loader_put_in_memory(flown):
    machine = flown[0]
    chart = map_decode.load('a')
    assert [name for _, name, _ in machine.files_log if name.startswith('maps/')] == ['maps/a.map']
    base = machine.o.r32(MAP_BASE)
    assert machine.o.r16(MAP_LENGTH) == chart.length
    assert machine.o.r32(MAP_END) == base + chart.length - 2
    assert machine.o.r16(MAP_EXTENT) == chart.extent
    assert machine.o.r16(PLAYER_START) == chart.player_x
    assert [machine.o.r16(base + 2 * i) for i in range(len(chart))] == chart.words


# ------------------------------------------------------------------ the draws of a pass

def test_the_decoder_predicts_every_map_draw_of_every_pass(flown):
    """The acceptance of the record semantics: slot, screen x and screen y of every draw the
    original made from the map, in order, for every pass of a flight that covers the deck, the
    take-off, level flight and the eighth-scale view."""
    machine, views, tables = flown
    assert len(views) >= 100, 'the flight is too short to say much'
    assert sum(1 for view in views if view['view_step'] == 1) > 10, 'no eighth-scale pass'
    chart = map_decode.load('a')
    for view in views:
        assert observed(machine, view, tables) == predicted(chart, view, tables), view['pass']
    assert sum(len(view['draws']) for view in views) > 1000


def test_a_changed_map_changes_exactly_the_draws_the_decoder_says(tmp_path):
    """The control: one record of the map is given another slot and another height, laid over
    the disk through the run description's `files`.  Everything the decoder predicts for the
    first passes changes with it, and nothing else in the state does."""
    chart = map_decode.load('a')
    index = next(i for i, word in enumerate(chart.words)
                 if word & 0x8000 and (word >> 2) & 0x1FF == 0x27)
    changed = list(chart.words)
    changed[index] = (changed[index] & ~0x7FC & ~0x3800) | (0x24 << 2) | (3 << 11)
    data = struct.pack('>LL', chart.length, chart.start) + struct.pack(
        '>%dH' % chart.on_disk, *changed[:chart.on_disk])
    plain = flight()
    laid = flight(files={'maps/a.map': data.hex()})
    other = map_decode.Map('a', data)

    tables, views = tables_of(laid), passes_of(laid)
    for view in views:
        assert observed(laid, view, tables) == predicted(other, view, tables), view['pass']

    # What differs between the two runs is the map itself and what the changed record feeds:
    # the copy in memory, and the ground height the tick takes from it.
    before, after = passes_of(plain), views
    assert [view['player_x'] for view in before] == [view['player_x'] for view in after]
    differing = [i for i, (a, b) in enumerate(zip(before, after))
                 if observed(plain, a, tables_of(plain)) != observed(laid, b, tables)]
    assert differing, 'the changed record never reached the screen'
    for i in differing:
        assert (predicted(chart, before[i], tables_of(plain))
                != predicted(other, after[i], tables)), i


def test_the_ground_height_of_a_record_is_its_class_height_less_its_own_height(flown):
    """0x015714 under the oracle over random records: a terrain record gives the height of its
    class less its own height steps, a ship record gives the ship's own deck, and anything
    else gives zero."""
    o = Oracle(a4=A4)
    scratch = 0x001F0000
    heights = [o.r16(CLASS_HEIGHTS + 2 * i, signed=True) for i in range(6)]
    random.seed(4)
    seen = set()
    for _ in range(600):
        word = random.getrandbits(16)
        for flag, base in SHIPS:
            if flag is not None:
                o.write(flag, bytes([random.getrandbits(1)]))
            o.w16(base + 0x0E, random.getrandbits(16))
            o.w16(base + 0x14, random.getrandbits(16))
        o.w16(GROUND_OFF, random.getrandbits(16))
        o.w16(GROUND_SUB, random.getrandbits(16))
        o.w16(scratch, word)
        got = o.call(GROUND_HEIGHT, regs={'a0': scratch, 'a4': A4})
        slot = (word >> 2) & 0x1FF
        seen.add(slot if slot < 0x30 else 'high')
        want = ground_height_model(o, word, heights)
        assert got == want, '%04x: got %x want %x' % (word, got, want)
    assert len(seen) > 20


def ground_height_model(o, word, heights):
    """What 0x015714 computes, as the listing has it."""
    slot = (word >> 2) & 0x1FF
    classes = [(6,), (7,), (8, 0xB), (3,), (4,), tuple(range(0xF, 0x1F))]
    for index, members in enumerate(classes):
        if slot in members:
            return (heights[index] - ((word >> 11) & 7)) & 0xFFFF
    ships = [(0x02549C, (0xCC,)), (0x0254BA, (0xF1, 0xF3, 0xF2, 0xF6)),
             (0x02547E, (0x10C, 0x10E, 0x10D, 0x10F, 0x110)), (0x025460, (0xE5, 0xE6, 0xE4, 0xE7))]
    for base, members in ships:
        if slot in members:
            return (o.r16(base + 0x0E) - o.r16(base + 0x14) - o.r16(GROUND_OFF)) & 0xFFFF
    if slot in (0x20, 0x1F, 0x21, 0x26, 0x23, 0x22, 0x24, 0x25, 0x9F, 0x27):
        return (o.r16(0x0254D8 + 0x0E) - o.r16(0x0254D8 + 0x14)
                - o.r16(GROUND_OFF) - o.r16(GROUND_SUB)) & 0xFFFF
    return 0
