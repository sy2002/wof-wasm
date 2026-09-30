"""M7 part 2, the loaded game, against the headless original (re/notes/porting-m7.md,
re/notes/campaign.md).

The scripts of tools/m7_scripts.py that load a saved game - the disk's own file from the
rank selection, save_a's save in flight and from the rank selection after a round of the
outer loop - are recorded under the headless original and run through the port by
tests/m4compare.py in the closed loop (T2) from the program's start.
"""
import os
import sys

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, 'tools'))
sys.path.insert(0, HERE)

import m7_scripts                  # noqa: E402
import test_campaign               # noqa: E402

LOADS = ['load_disk', 'load_hold', 'load_menu']


def params(names):
    return [n if n not in m7_scripts.PART2_SLOW else pytest.param(n, marks=pytest.mark.slow)
            for n in names]


@pytest.mark.parametrize('name', params(LOADS))
def test_a_loaded_game_agrees_in_the_closed_loop(ported, name):
    """T2 over a load script: the dialog, the file read through the walker, the briefing,
    the mission's setup without its reset and the mission from the save, after every tick
    and every pass."""
    machine, replay, passes, found, standins, stopped = test_campaign.closed_loop(ported, name)
    test_campaign.assert_closed(machine, replay, passes, found, standins, stopped)
    assert machine.loads, 'the original loaded no game'
    DERIVED_SEEN[name] = dict(replay.derived_counts)


# The passes in which a derived field differed after a load, by script (m4compare, DERIVED).
DERIVED_SEEN = {}


# The four pointer fields of a saved game's raw part, which the port derives and the original
# keeps as the file brought them until its tick sets them (re/notes/campaign.md, "The
# loader"): the player's shape and the torpedo's, 0x02541A, and each ship's gun list.
DERIVED_FIELDS = ('player[0].shape', 'torpedo_shape[0].s', 'g_02541a[0].s')


def load_state(replay):
    """The port's registered state as its last load left it (tests/shim.c)."""
    import ctypes
    lib, layout = replay.lib, replay.layout
    for name in ('wt_load_globals_get', 'wt_load_mission_get'):
        getattr(lib, name).argtypes = [ctypes.c_void_p, ctypes.c_int]
        getattr(lib, name).restype = ctypes.c_int
    gb = ctypes.create_string_buffer(layout.globals_bytes)
    mb = ctypes.create_string_buffer(layout.mission_bytes)
    assert lib.wt_load_globals_get(gb, layout.globals_bytes) > 0, 'the port loaded no game'
    assert lib.wt_load_mission_get(mb, layout.mission_bytes) > 0
    return bytearray(gb.raw), bytearray(mb.raw)


@pytest.mark.parametrize('name', params(LOADS))
def test_the_state_a_load_leaves_is_the_originals(ported, name):
    """At the end of save_game_read, before any tick: every registered global and table of
    the port as the original's, but for the pointer fields the port derives, which the
    original's first tick sets (the closed loop holds them from there); the ships' gun
    lists as the flags of the blocks the original read."""
    import m4state
    machine, replay, passes, found, standins, stopped = test_campaign.closed_loop(ported, name)
    test_campaign.assert_closed(machine, replay, passes, found, standins, stopped)
    assert machine.load_states, 'the original loaded no game'
    memory = m4state.Memory(machine.load_states[-1])
    pg, pm = load_state(replay)
    wg, wm, problems = replay.layout.expected(memory, m4state.Shapes(memory))
    differing = ['%s: port %x original %x' % d
                 for d in replay.layout.differences(pg, pm, wg, wm)]
    # The tables of shape pointers into the dashboard's and the ships' containers, which
    # both paths have freed at this point and load again after it (0x0134AE, free_map and
    # load_dash_assets, load_ship_shapes in flight; free_mission_assets before the rank
    # selection): the original's pointers name memory no longer allocated, the port's
    # handles its containers; the closed loop holds them from the next tick on.
    def freed(problem):
        if 'is no shape record' not in problem:
            return False
        pointer = int(problem.split(': ')[1].split(' ')[0], 16)
        return load.region(pointer) is None
    load = memory
    gone = {p.split(':')[0] for p in problems if freed(p)}
    left = [p for p in problems + differing if p.split(':')[0] not in DERIVED_FIELDS
            and p.split(':')[0] not in gone]
    assert left == [], left[:8]


def shape_by_name(memory, container, name):
    """The port's handle of the shape `name` names in the original's container of that
    kind (tests/m4state.py, CONTAINER_POINTERS), or 0 where the name names none: the port's
    lookup gives no shape then (src/shapes.c)."""
    import struct
    import m4state
    pointer = next(p for p, n in m4state.CONTAINER_POINTERS if n == container)
    base = memory.u(pointer, 4)
    count = struct.unpack('>H', memory.read(base + 4, 2))[0]
    names = memory.read(base + 6, 4 * count)
    for i in range(count):
        if int.from_bytes(names[4 * i:4 * i + 4], 'big') == name:
            return m4state.handle(m4state.SLOTS[container], i)
    return 0


def shape_by_pointer(memory, pointer, player, frame):
    """The port's handle of the hellcat.shp shape a saved pointer names (0x02541A): the
    record it points to in the original's own memory; or, for a pointer of another
    machine, the record at its distance from the player's pointer, whose shape the frame
    name gives, in the container's layout; 0 where neither finds one."""
    import struct
    import m4state
    shapes = m4state.Shapes(memory)
    own = shapes.handle_of(pointer)
    if own is not None:
        return own
    base = memory.u(0x02463E, 4)
    count = struct.unpack('>H', memory.read(base + 4, 2))[0]
    names = memory.read(base + 6, 4 * count)
    offsets = [memory.u(base + 6 + 4 * count + 4 * i, 4) for i in range(count)]
    first = 6 + 8 * count
    mine = next((i for i in range(count)
                 if int.from_bytes(names[4 * i:4 * i + 4], 'big') == frame), None)
    if mine is None:
        return 0
    there = player - (first + offsets[mine])
    for i in range(count):
        if there + first + offsets[i] == pointer:
            return m4state.handle(m4state.SLOTS['HELLCAT'], i)
    return 0


@pytest.mark.parametrize('name', params(LOADS))
def test_the_derived_fields_are_what_the_originals_first_tick_makes_of_them(ported, name):
    """The four pointer fields the port derives at the load: the player's shape and the
    torpedo's are the shapes the loaded frame name names, which is what the original's
    first tick after the load sets whenever that tick leaves the frame name as it was; the
    shape at 0x02541A is the one the saved pointer names, in the original's own memory for
    its own file and, for the disk's file from another machine, at its distance from the
    player's saved pointer; a ship's gun list is set exactly where the original's load read
    a block for it."""
    import m4state
    machine, replay, passes, found, standins, stopped = test_campaign.closed_loop(ported, name)
    test_campaign.assert_closed(machine, replay, passes, found, standins, stopped)
    lib = replay.lib
    load = m4state.Memory(machine.load_states[-1])
    tick = m4state.Memory(machine.after_load_tick[-1])
    shapes = m4state.Shapes(tick)
    frame = load.u(0x025080, 4)
    assert lib.wt_load_derived(0) == shape_by_name(load, 'HELLCAT', frame)
    assert lib.wt_load_derived(1) == shape_by_name(load, 'TORPEDO', frame)
    assert lib.wt_load_derived(2) == shape_by_pointer(load, load.u(0x02541A, 4),
                                                      load.u(0x02507C, 4), frame)
    if tick.u(0x025080, 4) == frame:
        assert shapes.handle_of(tick.u(0x02507C, 4)) == lib.wt_load_derived(0)
        assert shapes.handle_of(tick.u(0x02541E, 4)) == lib.wt_load_derived(1)
    if tick.u(0x025422, 4):
        name = tick.u(0x025422, 4)
        assert shapes.handle_of(tick.u(0x02541A, 4)) == shape_by_name(tick, 'HELLCAT', name)
    for i in range(5):
        block = load.u(0x025460 + 0x1E * i + 6, 4)
        base = load.region(block) if block else None           # mem_alloc's header before it
        read = base in machine.load_allocs[-1]
        assert bool(lib.wt_load_derived(3 + i)) == read, (i, hex(block or 0), read)


@pytest.mark.slow
@pytest.mark.parametrize('rate', [1, 3])
def test_a_loaded_game_holds_at_other_pass_rates(ported, rate):
    """load_disk at one and three VBlanks per pass against the original run at the same
    rate: the dialog, the disk's file, the briefing and the mission from the file."""
    machine, replay, passes, found, standins, stopped = test_campaign.closed_loop(
        ported, 'load_disk', rate)
    test_campaign.assert_closed(machine, replay, passes, found, standins, stopped)
    assert machine.loads and machine.missions == replay.missions == 1


def open_loop(ported, name):
    """T1 over a part 2 script: every pass and every tick starts from the original's state
    before it; no step may differ and none may reach a stand-in but M8's, which the
    scripts do not reach either (re/notes/porting-m7.md, "Part 2: how it is held")."""
    import m4compare
    import test_weapons
    import test_world
    machine, dump_path = test_world.recorded(name, pokes=m7_scripts.pokes(name))
    replay = m4compare.Replay(ported, machine, dump_path, mode='open',
                              pokes=m7_scripts.pokes(name))
    old = test_weapons.later
    test_weapons.later = lambda marker: 'M8 STAND-IN' in marker
    try:
        steps, differing, bad, reached = test_weapons.attribute(replay)
    finally:
        test_weapons.later = old
    assert steps > 100, 'only %d steps compared' % steps
    assert bad == [] and differing == 0 and not reached, (differing, bad[:3], dict(reached))


@pytest.mark.parametrize('name', params(LOADS))
def test_every_step_agrees_in_the_open_loop(ported, name):
    open_loop(ported, name)


# ------------------------------------------------------- 0x02541A from the saved pointers

def hellcat_layout():
    """hellcat.shp as load_file leaves it in memory: its names and each record's place
    from the container's start (6 + 8 x count + the record's offset)."""
    import struct
    import rpck
    data, _ = rpck.load(os.path.join(ROOT, 'original', 'disk', 'Wings_of_Fury', 'shapes',
                                  'hellcat.shp'))
    count = struct.unpack('>H', data[4:6])[0]
    names = [struct.unpack('>L', data[6 + 4 * i:10 + 4 * i])[0] for i in range(count)]
    offsets = [struct.unpack('>L', data[6 + 4 * count + 4 * i:10 + 4 * count + 4 * i])[0]
               for i in range(count)]
    return names, [6 + 8 * count + o for o in offsets]


def test_the_shape_at_0x02541a_comes_from_where_its_pointer_lies(ported):
    """The loader's derivation of 0x02541A (src/dialog.c, saved_hellcat_shape) over the
    disk's own wof.mission 3 with that field and the player's pointer rewritten: the disk's
    pair of addresses names the record at their distance; a distance that falls inside a
    record or outside the container, and a pointer beside a player's that the frame name
    does not place, name no shape (handle 0: nothing is drawn there until frame_select's
    level path sets the field); in the port's own file a handle of hellcat.shp is taken,
    one of another container is not, and 0 stays 0."""
    import m4state
    lib = ported.lib
    names, places = hellcat_layout()
    with open(os.path.join(ROOT, 'original', 'disk', 'Wings_of_Fury', 'wof.mission 3'), 'rb') as f:
        disk = f.read()
    at_player, at_level, at_frame = 0x02507C - 0x024CAE, 0x02541A - 0x024CAE, 0x025080 - 0x024CAE
    player = int.from_bytes(disk[at_player:at_player + 4], 'big')
    frame = int.from_bytes(disk[at_frame:at_frame + 4], 'big')
    base = player - places[names.index(frame)]
    level = int.from_bytes(disk[at_level:at_level + 4], 'big')
    hellcat = lambda i: m4state.handle(m4state.SLOTS['HELLCAT'], i)
    world = m4state.handle(m4state.SLOTS['WORLD'], 5)
    own = hellcat(names.index(frame))
    cases = [
        ('the disk as it is', player, level, hellcat(places.index(level - base))),
        ('another record at its distance', player, base + places[7], hellcat(7)),
        ('inside a record', player, base + places[7] + 2, 0),
        ('before the container', player, base - 0x100, 0),
        ('0', player, 0, 0),
        ('a handle of hellcat.shp', own, hellcat(12), hellcat(12)),
        ('a handle of another container', own, world, 0),
        ('a handle past hellcat.shp', own, hellcat(len(names)), 0),
    ]
    for label, p, l, want in cases:
        data = bytearray(disk)
        data[at_player:at_player + 4] = p.to_bytes(4, 'big')
        data[at_level:at_level + 4] = l.to_bytes(4, 'big')
        ported.reset_core()
        ported.fs_reset()
        assert ported.fs_write('wof.case', bytes(data))
        assert lib.wof_save_game_read(b'wof.case') == 1
        assert lib.wt_load_derived(2) == want, (label, lib.wt_load_derived(2), want)
    ported.reset_core()
    ported.fs_reset()
