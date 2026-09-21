"""The mission setup and its memory (M4 part 1, re/notes/porting-m4.md).

The setup after the briefing is compared with the headless original's at step S on every
one of the fifteen maps, each laid over maps/a.map on both sides the way
tests/test_map.py lays a changed map over the disk, and for the first mission of every rank
of the rank selection, so that map_load's choice of file runs and is not only read.

Where mission memory lives: every table a mission allocates is at a fixed place in the core's
state at a fixed capacity (src/mission.def), and nothing is taken from the arena after the
assets are loaded.  The capacities are held against all fifteen maps, the arena against
thirty mission setups in a row, and the arena's own promise - zeroed memory, as MEMF_CLEAR
gives the original - against reuse of the same addresses.
"""
import ctypes
import os
import struct
import sys

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, 'tools'))
sys.path.insert(0, HERE)

import headless                    # noqa: E402
import map_decode                  # noqa: E402
import m4compare                   # noqa: E402
import m4state                     # noqa: E402
import pass_observe                # noqa: E402

MAPS = os.path.join(ROOT, 'original', 'disk', 'Wings_of_Fury', 'maps')
LETTERS = 'abcdefghijklmno'
RANK_MAPS = 'adgiklm'              # the first mission's map of each rank, mission_map_table


def rank_script(rank):
    """The front end's fire taps, with the stick pulled back `rank` times in the rank
    selection (menu_input answers the back switch with +1), then the briefing ended."""
    return (pass_observe.FRONT[:4] + [[4, '']] + [[2, 'D'], [10, '']] * rank +
            [[3, 'F'], [30, ''], [3, 'F'], [40, '']])


def setup_differences(ported, tmp_path, description, files=None, tag='run'):
    """One run to step S on both sides; returns (differences, the harness)."""
    dump_path = str(tmp_path / ('%s.dump' % tag))
    machine = m4compare.Recorder(description, observe=())
    machine.open_dump(dump_path)
    machine.run(until='inner')
    machine.close()
    assert machine.missions == 1, 'the run never reached a mission'
    replay = m4compare.Replay(ported, machine, dump_path, mode='plain')
    memory, _ = replay.s_states()[0]
    replay.build_index(memory)
    kinds = [e[0] for e in machine.schedule if e[0] != 'V']
    tick = max(i for i, k in enumerate(kinds) if k == 'T')
    by_port = {(w, o): n for n, w, o, _, _ in replay.layout.fields()}
    setup_tick = sorted({by_port[(w[0], w[1])] for a in machine.t_writes[tick]
                         for w in [replay.index.get(a)] if w})
    replay.run(files=files)
    layout = replay.layout
    wg, wm, problems = layout.expected(memory)
    assert not problems, problems[:5]
    diffs = layout.differences(layout.port_globals(at_s=True), layout.port_mission(at_s=True),
                               wg, wm, skip=setup_tick)
    assert replay.standins() == [], replay.standins()
    return diffs, machine


# ------------------------------------------------------------------- the record layouts

def test_every_record_layout_tiles_the_original_record(ported):
    """The fields of a record in src/records.def cover its original bytes exactly once."""
    layout = m4state.Layout(ported)
    for name, record in layout.records.items():
        covered = bytearray(record['orig_size'])
        for fname, orig, orig_elem, port, elem, kind in record['fields']:
            for b in range(orig, orig + orig_elem):
                assert b < record['orig_size'], '%s.%s runs past the record' % (name, fname)
                assert not covered[b], '%s.%s overlaps another field at +%#x' % (name, fname, b)
                covered[b] = 1
        assert all(covered), '%s leaves bytes uncovered' % name


def test_every_table_lies_where_the_original_keeps_it(ported):
    """A fixed table's address range lies in the DATA hunk, and no two overlap."""
    layout = m4state.Layout(ported)
    spans = []
    for table in layout.tables:
        if table['pool']:
            continue
        size = layout.records[table['record']]['orig_size'] * table['count']
        spans.append((table['addr'], table['addr'] + size, table['name']))
        assert 0x023000 <= table['addr'] and table['addr'] + size <= 0x028004, table['name']
    spans.sort()
    for (a0, a1, n0), (b0, b1, n1) in zip(spans, spans[1:]):
        assert a1 <= b0, '%s and %s overlap' % (n0, n1)


# --------------------------------------------------------------------- the capacities

def map_counts(letter):
    """What map_scan counts in a map's first walk, and the record list's length."""
    chart = map_decode.load(letter)
    counts = {'records': chart.length // 2 + 1, 't4': 0, 't3': 0, 'tf': 0, 'islands': 0,
              'slot1': 0}
    for w in chart.words:
        if not w & 0x8000:
            continue
        slot = (w >> 2) & 0x1FF
        key = {4: 't4', 3: 't3', 0x0F: 'tf', 2: 'islands', 1: 'slot1'}.get(slot)
        if key:
            counts[key] += 1
    return counts


def test_the_pools_hold_every_map(ported):
    """Every table a mission allocates fits its pool on all fifteen maps: the record list with
    the one record map_scan reads past it, the targets, the soldiers, the islands."""
    layout = m4state.Layout(ported)
    capacity = {t['name']: t['count'] for t in layout.tables}
    globals_ = {g[0]: g[3] for g in layout.globals}
    for letter in LETTERS:
        c = map_counts(letter)
        assert c['records'] <= capacity['map_records'], letter
        assert c['t4'] <= capacity['target_records_4'], letter
        assert c['t3'] <= capacity['target_records_3'], letter
        assert c['tf'] <= capacity['target_records_f'], letter
        assert (c['t4'] + c['t3']) * 5 <= capacity['soldier_records'], letter
        assert c['islands'] <= globals_['island_slot2'] and c['slot1'] <= globals_['island_slot1'], letter


# ------------------------------------------------------------ V4: every map, every rank

# The maps carrying the japanese carrier, m and o, cannot be laid over maps/a.map: the ship's
# block table (0x02358A) is indexed by the mission's map number, gives map 0 no planes, and
# sub_01252c's dbra on the count less one then runs 65,536 times and the original crashes.
# In the game those maps are only ever loaded as maps 12 and 14; the test below reaches all
# fifteen that way.
OVERLAID = [c for c in LETTERS if c not in 'mo']

# The rank and mission of each map number, from mission_map_table (0x02345F).
RANK_MISSION = {'a': (0, 1), 'b': (0, 2), 'c': (0, 3), 'd': (1, 1), 'e': (1, 2), 'f': (1, 3),
                'g': (2, 1), 'h': (2, 2), 'i': (3, 1), 'j': (3, 2), 'k': (4, 1), 'l': (5, 1),
                'm': (6, 1), 'n': (6, 2), 'o': (6, 3)}


@pytest.mark.parametrize('letter', OVERLAID)
def test_the_setup_agrees_on_every_map(ported, tmp_path, letter):
    """The map laid over maps/a.map on both sides; at step S every registered global and
    table agrees but what the setup's own tick wrote."""
    with open(os.path.join(MAPS, '%s.map' % letter), 'rb') as f:
        data = f.read()
    description = pass_observe.script('deck', files={'maps/a.map': data.hex()})
    diffs, machine = setup_differences(ported, tmp_path, description,
                                       files={'maps/a.map': data}, tag='map-' + letter)
    assert machine.o.r16(0x0253C6) == struct.unpack('>L', data[:4])[0] & 0xFFFF
    assert diffs == [], diffs[:10]


@pytest.mark.parametrize('letter', LETTERS)
def test_the_setup_agrees_on_every_map_under_its_own_number(ported, tmp_path, letter):
    """Each map loaded as the game loads it: its rank chosen with the cursor and the mission
    number poked to the one mission_map_table gives the map, on both sides, at the rank
    selection's end (0x01009E).  The poke is the instrument; the loader, the scanner and the
    ship tables then run as they do in a campaign."""
    rank, mission = RANK_MISSION[letter]
    pokes = {0x0253C0: (2, mission)}
    description = {'raw': rank_script(rank), 'stop': {'vblanks': 2000}}
    dump_path = str(tmp_path / ('number-%s.dump' % letter))
    machine = m4compare.Recorder(description, observe=(), pokes=pokes)
    machine.open_dump(dump_path)
    machine.run(until='inner')
    machine.close()
    opened = [name for _, call, name, found in machine.files_at if call == 'Open' and 'maps/' in name]
    assert opened == ['maps/%s.map' % letter], opened
    replay = m4compare.Replay(ported, machine, dump_path, mode='plain', pokes=pokes)
    memory, _ = replay.s_states()[0]
    replay.build_index(memory)
    kinds = [e[0] for e in machine.schedule if e[0] != 'V']
    tick = max(i for i, k in enumerate(kinds) if k == 'T')
    by_port = {(w, o): n for n, w, o, _, _ in replay.layout.fields()}
    setup_tick = sorted({by_port[(w[0], w[1])] for a in machine.t_writes[tick]
                         for w in [replay.index.get(a)] if w})
    replay.run()
    layout = replay.layout
    wg, wm, problems = layout.expected(memory)
    assert not problems, problems[:5]
    diffs = layout.differences(layout.port_globals(at_s=True), layout.port_mission(at_s=True),
                               wg, wm, skip=setup_tick)
    assert diffs == [], diffs[:10]
    assert replay.standins() == [], replay.standins()


@pytest.mark.parametrize('rank', range(7))
def test_the_first_mission_of_every_rank_agrees(ported, tmp_path, rank):
    """The rank selection's cursor moved `rank` places: the map the loader picks by rank and
    mission, and the setup at step S."""
    description = {'raw': rank_script(rank), 'stop': {'vblanks': 2000}}
    diffs, machine = setup_differences(ported, tmp_path, description, tag='rank-%d' % rank)
    opened = [name for _, call, name, found in machine.files_at if call == 'Open' and 'maps/' in name]
    assert opened == ['maps/%s.map' % RANK_MAPS[rank]], opened
    assert machine.o.r16(0x0253BE) == rank
    assert diffs == [], diffs[:10]
    port_opened = [r['text'] for r in ported.traces('map_load') if r['a']]
    assert port_opened == opened, port_opened


# ---------------------------------------------------------------- memory, SPEC 7.2

def arena(ported):
    lib = ported.lib
    for name, args, res in (('wof_arena_used', [], ctypes.c_uint32),
                            ('wof_arena_mark', [], ctypes.c_uint32),
                            ('wof_arena_release', [ctypes.c_uint32], None),
                            ('wof_scratch_alloc', [ctypes.c_uint32], ctypes.c_void_p),
                            ('wof_alloc', [ctypes.c_uint32], ctypes.c_void_p),
                            ('wof_arena_reset', [], None)):
        getattr(lib, name).argtypes = args
        getattr(lib, name).restype = res
    return lib


def test_the_arena_hands_out_zeroed_memory_also_when_the_address_was_used_before(ported):
    """SPEC 7.2: every allocation the game makes asks for MEMF_CLEAR and the game relies on it
    (the last four records of every map).  Memory from wof_alloc and from wof_scratch_alloc is
    zero also when the same address was handed out and written before: after
    wof_arena_reset for the one, after wof_arena_release for the other."""
    lib = arena(ported)
    try:
        lib.wof_arena_reset()
        first = lib.wof_alloc(4096)
        ctypes.memset(first, 0xA5, 4096)
        lib.wof_arena_reset()
        again = lib.wof_alloc(4096)
        assert again == first, 'the arena did not hand out the same address again'
        assert ctypes.string_at(again, 4096) == bytes(4096), 'wof_alloc after a reset is not zero'

        mark = lib.wof_arena_mark()
        scratch = lib.wof_scratch_alloc(4096)
        ctypes.memset(scratch, 0x5A, 4096)
        lib.wof_arena_release(mark)
        reused = lib.wof_scratch_alloc(4096)
        assert reused == scratch, 'the scratch end did not hand out the same address again'
        assert ctypes.string_at(reused, 4096) == bytes(4096), 'scratch after a release is not zero'
        lib.wof_arena_release(mark)
    finally:
        ported.reset_core()


def test_thirty_mission_setups_do_not_grow_the_arena(ported):
    """Nothing is taken from the arena after the assets are loaded: thirty missions in a row,
    each begun from the rank selection and ended with the stand-in's key, leave
    wof_arena_used where the first one found it."""
    lib = arena(ported)
    ported.reset_core(fade_vblanks=0)
    used = []
    vblank = 0
    missions = 0
    in_mission_since = None
    while missions < 31 and vblank < 60000:
        raw = 0x10 if vblank % 30 < 3 else 0
        ported.vblank(raw)
        ported.pass_()
        vblank += 1
        if ported.mission_count() > missions:
            missions = ported.mission_count()
            used.append(lib.wof_arena_used())
            in_mission_since = vblank
        if in_mission_since is not None and vblank - in_mission_since == 40:
            ported.key(0x13, 0x0008)                  # Control-R: the mission ends
            in_mission_since = None
    assert missions >= 31, 'only %d missions in %d VBlanks' % (missions, vblank)
    assert len(set(used)) == 1, 'the arena grew: %s' % used
    ported.reset_core()
