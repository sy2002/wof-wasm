"""M2: the headless original (SPEC section 8, re/notes/headless.md).

The original's own main program runs under tools/headless.py from its first instruction,
through the title sequence and the rank selection into a mission, with a scripted
controller.  The tests hold the harness to what the milestone asks: the inner loop is
reached, the same run gives the same dumps, and a different run gives different ones.

The scripts below are the player's hands, VBlank by VBlank; they hold no game data.
"""
import ctypes
import json
import os
import subprocess
import sys

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, 'tools'))

import headless                    # noqa: E402
import headless_dump               # noqa: E402
import headless_writes             # noqa: E402

SLOW = pytest.mark.skipif(not os.environ.get('WOF_SLOW_HEADLESS'),
                          reason='set WOF_SLOW_HEADLESS=1 for the long headless runs')

# Fire taps carry the title sequence, the rank selection and the briefing along.
FRONT = [[30, ''], [3, 'F']] * 5
# On the deck: fire brings the aircraft up on the lift, stick right rolls it along the deck,
# stick right and forward lifts it off before the deck ends.
TAKE_OFF = [[40, ''], [3, 'F'], [60, ''], [460, 'R'], [3000, 'RU']]
# The same without pushing forward: the aircraft rolls over the bow.
ROLL_OFF = [[40, ''], [3, 'F'], [60, ''], [3460, 'R']]
FLIGHT_TICKS = 260

# What the instrument tests below watch, from re/names.txt.
VIEW_X            = 0x024F30
PASS_COUNTER      = 0x0253C8
INPUT_QUEUE_COUNT = 0x027354


def run(description, dump_path=None, **options):
    machine = headless.Headless(description, **options)
    if dump_path:
        machine.open_dump(str(dump_path))
    try:
        machine.why = machine.run()
    finally:
        machine.close()
    return machine


def flight(seed=1, tail=TAKE_OFF, ticks=FLIGHT_TICKS, **more):
    description = {'entropy': {'seed': seed}, 'raw': FRONT + tail, 'stop': {'ticks': ticks}}
    description.update(more)
    return description


@pytest.fixture(scope='module')
def dumps(tmp_path_factory):
    return tmp_path_factory.mktemp('headless')


@pytest.fixture(scope='module')
def first(dumps):
    return run(flight(), dumps / 'first.dump')


@pytest.fixture(scope='module')
def second(dumps):
    return run(flight(), dumps / 'second.dump')


@pytest.fixture(scope='module')
def other_entropy(dumps):
    return run(flight(seed=2), dumps / 'entropy.dump')


@pytest.fixture(scope='module')
def other_input(dumps):
    return run(flight(tail=ROLL_OFF), dumps / 'input.dump')


def word(state, address):
    data = state[headless.DATA_START]
    offset = address - headless.DATA_START
    return int.from_bytes(data[offset:offset + 2], 'big')


# ------------------------------------------------------------------ the milestone's criterion

def test_the_original_reaches_the_first_pass_of_the_inner_loop(first):
    assert first.why == 'tick'
    assert first.missions == 1
    assert first.loop_heads > 0, 'the head of the inner loop at 0x01010E was never executed'
    kinds = [event[0] for event in first.schedule]
    start = kinds.index('S')
    assert 'P' not in kinds[:start], 'a pass ran before the mission began'
    assert 'P' in kinds[start:]
    assert first.passes > 400 and first.ticks == FLIGHT_TICKS


def test_the_run_is_a_real_game(first):
    """The aircraft has left the deck, and the world has started to draw random numbers."""
    x, y = first.o.r16(0x026E5C, True), first.o.r16(0x026E60, True)
    assert y > 200, 'the aircraft is at height %d' % y
    assert x > 7600, 'the aircraft is at x %d' % x
    assert len(first.entropy_log) > 100


def test_two_runs_give_identical_dumps(first, second, dumps):
    assert len(first.step_hashes) == len(second.step_hashes) > 700
    assert first.step_hashes == second.step_hashes
    assert (dumps / 'first.dump').read_bytes() == (dumps / 'second.dump').read_bytes()
    assert first.schedule == second.schedule
    assert first.entropy_log == second.entropy_log


def test_another_entropy_stream_gives_other_dumps(first, other_entropy):
    assert first.schedule == other_entropy.schedule, 'the entropy changed the schedule'
    pairs = list(zip(first.step_hashes, other_entropy.step_hashes))
    assert all(a[3] != b[3] for a, b in pairs), 'some step has the same state under another entropy stream'


def test_another_input_gives_other_dumps(first, other_input, dumps):
    """Until the scripts part ways the dumps agree hash for hash; after that they never do."""
    same = [a == b for a, b in zip(first.step_hashes, other_input.step_hashes)]
    parted = same.index(False)
    assert parted > 100
    assert not any(same[parted:])
    vblank_of_parting = sum(segment[0] for segment in FRONT + TAKE_OFF[:4])
    heads = headless_dump.steps(str(dumps / 'first.dump'))
    assert heads[parted]['vblank'] >= vblank_of_parting, 'the dumps part before the scripts do'
    assert heads[parted]['vblank'] <= vblank_of_parting + 8, 'the dumps part long after the scripts do'


def test_a_dump_rebuilds_every_step_it_holds(first, dumps):
    reader = headless_dump.DumpReader(str(dumps / 'first.dump'))
    assert reader.run['entropy'] == {'seed': 1}
    count = 0
    for head in reader:
        assert reader.verify(head), 'step %d does not rebuild to its hash' % head['step']
        assert (head['kind'], head['tick'], head['pass'], head['hash']) == first.step_hashes[count]
        count += 1
    assert count == len(first.step_hashes)
    regions = reader.regions
    assert headless.DATA_START in regions
    assert not any(headless.PLANE_BASE <= a < headless.PLANE_END for a in regions), 'display memory is in the dump'


# ------------------------------------------------------------------ time, as the notes have it

def test_every_pass_of_a_mission_begins_two_vblanks_after_the_last(first):
    events = first.schedule[first.schedule.index(('S', 1)):]
    gaps, since = [], 0
    for event in events:
        if event[0] == 'V':
            since += 1
        elif event[0] == 'P':
            gaps.append(since)
            since = 0
    assert set(gaps[1:]) == {2}, 'VBlanks between passes: %s' % sorted(set(gaps[1:]))


def test_the_pass_period_is_a_setting():
    machine = run({'raw': FRONT, 'vblanks_per_pass': 3, 'stop': {'ticks': 12}})
    events = machine.schedule[machine.schedule.index(('S', 1)):]
    gaps, since = [], 0
    for event in events:
        if event[0] == 'V':
            since += 1
        elif event[0] == 'P':
            gaps.append(since)
            since = 0
    assert set(gaps[1:]) == {3}


def test_one_tick_for_every_four_vblanks(first):
    events = first.schedule[first.schedule.index(('S', 1)):]
    vblanks = sum(1 for e in events if e[0] == 'V')
    ticks = sum(1 for e in events if e[0] == 'T')
    assert abs(ticks - vblanks / 4) <= 1, '%d ticks in %d VBlanks' % (ticks, vblanks)


def test_the_originals_counters_count_what_the_harness_delivers(first):
    assert first.o.r32(headless.VBLANK_COUNTER) == first.vblanks      # vblank_every_frame
    assert first.o.r32(0x0253CA) == first.vblanks                     # the server's own count, its is_Data


def test_the_pass_counter_runs_from_0_to_99(first, dumps):
    reader = headless_dump.DumpReader(str(dumps / 'first.dump'))
    values = [word(reader.regions, headless.PASS_COUNTER) for head in reader if head['kind'] == 'P']
    assert set(values) == set(range(100))
    assert all((b - a) % 100 == 1 for a, b in zip(values, values[1:])), 'the pass counter skipped'


def test_the_tick_input_is_the_originals_own_input_byte(first):
    """Stick right is bit 2, stick forward bit 0, and a short press of fire is bit 5 for exactly one
    tick.  Three presses fall into the mission: the one that ended the briefing, whose release
    the server samples after the mission has begun, the last of FRONT, and the one of TAKE_OFF."""
    inputs = [event[1] for event in first.schedule[first.schedule.index(('S', 1)):] if event[0] == 'T']
    squeezed = [b for i, b in enumerate(inputs) if i == 0 or inputs[i - 1] != b]
    assert squeezed == [0x20, 0x00, 0x20, 0x00, 0x20, 0x00, 0x04, 0x05], ['%02x' % b for b in squeezed]
    assert inputs.count(0x20) == 3
    assert first.o.r16(headless.TICK_INPUT) == 0x05


def test_bit_0_of_the_input_byte_is_the_forward_switch():
    """The hardware gives the forward switch as bit 9 xor bit 8 of JOY1DAT, the back switch as
    bit 1 xor bit 0.  The original's decoder turns forward into bit 0, and its menu decoder turns
    forward into code 1, which menu_input answers like the cursor-up key."""
    machine = run({'raw': [], 'stop': {'vblanks': 3}})
    answers = {}
    for name, word in (('forward', 0x0100), ('back', 0x0001), ('right', 0x0003), ('left', 0x0300)):
        machine.o.w16(headless.JOY1DAT, word)
        answers[name] = (machine.nested(headless.READ_JOY_BITS, {})[0] & 0x0F,
                         machine.nested(0x020488, {})[0] & 0xFFFF)
    assert answers == {'forward': (1, 1), 'back': (2, 5), 'right': (8, 3), 'left': (4, 7)}


def test_pushing_forward_climbs_and_pulling_back_does_not(first):
    other = run(flight(tail=TAKE_OFF[:4] + [[3000, 'RD']]))
    assert first.o.r16(0x026E60, True) > 200
    assert other.o.r16(0x026E60, True) < 40, 'pulled back, the aircraft is at height %d' % other.o.r16(0x026E60, True)


def test_the_run_stops_where_the_description_says():
    machine = run({'raw': FRONT, 'stop': {'passes': 7}})
    assert (machine.why, machine.passes) == ('pass', 7)
    machine = run({'raw': [], 'stop': {'vblanks': 50}})
    assert machine.why == 'vblanks' and 50 <= machine.vblanks <= 60
    assert machine.o.r32(headless.VBLANK_COUNTER) == machine.vblanks


def test_holding_fire_becomes_the_hold_bit_after_ten_vblanks():
    machine = run({'raw': FRONT + [[40, ''], [40, 'F']], 'stop': {'ticks': 24}})
    inputs = [event[1] for event in machine.schedule[machine.schedule.index(('S', 1)):] if event[0] == 'T']
    held = inputs.index(0x10)
    assert inputs[held - 1] == 0x00 and set(inputs[held:]) == {0x10}, ['%02x' % b for b in inputs]


def test_input_bytes_can_be_given_directly():
    """The second input mode: the byte the server sampled is replaced, the queue stays its own."""
    given = [0x04, 0x04, 0x08, 0x01, 0x02, 0x10, 0x20, 0x00, 0x05]
    machine = run({'raw': FRONT, 'bytes': given, 'stop': {'ticks': 12}})
    inputs = [event[1] for event in machine.schedule[machine.schedule.index(('S', 1)):] if event[0] == 'T']
    assert inputs[:len(given)] == given, ['%02x' % b for b in inputs]
    assert set(inputs[len(given):]) <= {0}


# ------------------------------------------------------------------ entropy

def test_the_entropy_generator_is_the_ports(built):
    library = ctypes.CDLL(os.path.join(HERE, 'libwofcore.dylib'))
    library.wof_entropy_next.restype = ctypes.c_uint16
    library.wof_entropy_seed.argtypes = [ctypes.c_uint32]
    saved = ctypes.create_string_buffer(library.wof_state_size())
    library.wof_state_save(saved)
    try:
        for seed in (0, 1, 2, 0xDEADBEEF, 0xFFFFFFFF):
            library.wof_entropy_seed(seed)
            mine = headless.entropy_values(seed)
            for _ in range(2000):
                assert library.wof_entropy_next() == next(mine)
    finally:
        library.wof_state_load(saved)


def test_the_log_of_beam_reads_names_the_callers_in_order(first):
    values = headless.entropy_values(1)
    for index, (number, value, routine, vblank, passes, ticks) in enumerate(first.entropy_log):
        assert number == index and value == next(values)
        assert routine not in ('rand_beam', 'read_vhposr'), 'the log names the reader, not its caller'
    callers = {entry[2] for entry in first.entropy_log}
    known = {row[2] for row in first.names.code}
    assert callers <= known, callers - known
    assert [e[5] for e in first.entropy_log] == sorted(e[5] for e in first.entropy_log)


def test_an_entropy_list_is_served_value_for_value():
    values = [0x1234, 0x5678, 0x9ABC, 0x0011]
    machine = run({'raw': FRONT, 'entropy': {'values': values + [0] * 50}, 'stop': {'ticks': 4}})
    assert len(machine.entropy_log) >= 3
    assert [entry[1] for entry in machine.entropy_log] == (values + [0] * 50)[:len(machine.entropy_log)]
    assert machine.o.r16(0x026910) == (machine.o.r16(0x026912, True) * 0x1AFB + 0x1FCCD) & 0xFFFF ^ machine.entropy_log[-1][1]


def test_a_used_up_entropy_list_stops_the_run():
    with pytest.raises(headless.HarnessError, match='used up'):
        run({'raw': FRONT, 'entropy': {'values': [1, 2]}, 'stop': {'ticks': 4}})


# ------------------------------------------------------------------ the instrument

def test_the_change_report_names_who_wrote_what(dumps):
    machine = run({'raw': FRONT, 'stop': {'ticks': 6}}, track_writes=True)
    report = '\n'.join(machine.change_report)
    assert 'input_queue_count' in report and 'by input_queue_pop' in report
    assert 'by logic_tick' in report
    heads = [line for line in machine.change_report if not line.startswith(' ')]
    assert len(heads) == len(machine.step_hashes)
    assert heads[0].startswith('T ') and any(line.startswith('P ') for line in heads)


@pytest.fixture(scope='module')
def instrumented():
    """One short flight with every instrument switched on: the phase-aware write summary,
    the read hook over the pools and over one named global, and the detail log."""
    return run(flight(ticks=40), summary=True, keep_report=False, read_detail=True,
               read_owners=['alloc_pools'], read_ranges=[(PASS_COUNTER, 2), (VIEW_X, 2)])


def test_the_summary_says_in_which_phase_a_range_was_written(instrumented):
    """The phases: V inside a VBlank server, T inside logic_tick's tree, F inside
    frame_update's tree, M in the main program.  Four ranges whose writer is known from
    re/notes/drawing.md and re/notes/input.md are checked against it."""
    summary = instrumented.summary
    written = {address: (summary.phases_of(writes), {routine for _, routine in writes})
               for address, length, writes, _ in summary.ranges()}
    assert written[VIEW_X] == ('F', {'frame_update'})
    assert written[PASS_COUNTER] == ('F', {'draw_world'})
    assert 'V' in written[INPUT_QUEUE_COUNT][0]
    assert any(phases == 'T' for phases, _ in written.values())
    assert summary.steps['T'] == 40 and summary.steps['P'] == instrumented.passes


def test_the_summary_counts_the_windows_a_range_changed_in(instrumented):
    """A range is written in a phase and changes in a window: the pass counter is written by
    draw_world inside a pass and therefore changes in P windows only.  It counts to 99, so
    only its low byte ever changes, which is what the two byte counters below show."""
    changes = instrumented.summary.changes
    assert PASS_COUNTER not in changes
    assert set(changes[PASS_COUNTER + 1]) == {'P'}
    assert changes[PASS_COUNTER + 1]['P'] >= instrumented.passes - 2


def test_the_stride_detection_finds_a_table_of_records():
    """Two fields of a 0x34-byte record, over ten records, are a table; a plain array of
    words is not, and a gap of one record is still one."""
    items = [(0x100 + 0x34 * i + offset, 2) for i in range(10) for offset in (0, 0x16)]
    assert headless_writes.strides(items) == (0x100, 0x34, 10, [0, 0x16])
    assert headless_writes.strides([(0x100 + 2 * i, 2) for i in range(10)]) is None
    assert headless_writes.strides([(a, 2) for a, _ in items if a < 0x100 + 0x34 * 3
                                    or a >= 0x100 + 0x34 * 4])[1] == 0x34


def test_the_stride_detection_finds_a_real_pool(instrumented):
    """The pool of 0x14-byte records that player_lost_restart clears at the mission's start."""
    rows = headless_writes.tables(instrumented.summary, instrumented.region_of())
    place = instrumented.places()
    found = [(place(base), stride, records)
             for phase, routine, _, (base, stride, records, offsets) in rows
             if routine == 'player_lost_restart']
    assert found and found[0][1] == 0x14 and found[0][2] >= 8
    assert 'alloc_pools' in found[0][0]


def test_the_read_hook_says_who_read_a_watched_range(instrumented):
    """The read hook of a chosen allocation, the way _plane_read covers display memory: the
    routine, the phase and the offset of every read."""
    by_routine = instrumented.reads.by_routine()
    pools = {(phase, routine) for (phase, routine, label) in by_routine if 'alloc_pools' in label}
    assert ('F', 'draw_world') in pools, sorted(pools)
    counter = {(key[0], key[1]) for key in by_routine if key[2] == 'pass_counter'}
    assert ('F', 'draw_world') in counter and any(phase == 'T' for phase, _ in counter), counter
    assert instrumented.reads.offsets(label='view_x') == [0, 1]
    steps = {step for step, _, _, label, _, _ in instrumented.reads.events if label == 'pass_counter'}
    assert len(steps) > 4, 'the detail log holds no step of its own'


def test_an_instrument_does_not_change_a_run(instrumented):
    """The twin of test_an_observer_does_not_change_a_run for the write summary and the read
    hook: both only read, so the steps and the schedule are the ones of a plain run."""
    plain = run(flight(ticks=40))
    assert plain.step_hashes == instrumented.step_hashes
    assert plain.schedule == instrumented.schedule
    assert instrumented.summary.ranges() and not plain.summary


def test_no_logic_reads_what_was_drawn(first, other_input):
    """Closes the gap re/notes/drawing.md left open: the CPU reads display memory only to build
    copper lists and the text template, and never reads a bitplane."""
    display = {'cop_move', 'cop_move_ptr', 'cop_wait', 'cop_install', 'cop_colours', 'cop_set_split_line',
               'view_build_copper', 'view_poke_colours1', 'view_poke_colours2', 'text_render',
               'cop_vport_split', 'cop_vport_colours', 'cop_vport_planes', 'cop_sprites_off'}
    for machine in (first, other_input):
        planes = max(machine.display_allocs.values())
        assert planes == 0x159A0 + 12 + 4, 'display_init asked for %d bytes of planes' % planes
        for (routine, block), count in machine.plane_reads.items():
            assert routine in display, '%s reads display memory (%s)' % (routine, block)
            assert block != '%d bytes' % planes, '%s reads a bitplane' % routine


def test_the_music_player_is_recorded_not_run(first):
    names = {call[0] for call in first.player_calls}
    assert names == {'wofsongs', 'songplay'}
    assert [call[1] for call in first.player_calls if call[0] == 'songplay'][:3] == [0, 1, 2]


def test_a_key_goes_through_the_originals_input_handler():
    """Cursor down and return choose the second rank; the keys reach key_buffer through the
    handler the game itself put on input.device."""
    script = [[30, ''], [3, 'F'], [30, ''], [3, 'F'], [25, ''], [1, '', [0x4D]], [10, ''], [1, '', [0x44]]]
    machine = run({'raw': script + FRONT, 'stop': {'ticks': 2}})
    assert machine.missions == 1
    assert machine.o.r16(0x026C64) == 1, 'the rank chosen is %d' % machine.o.r16(0x026C64)


def test_the_command_line_runs_shows_and_compares(dumps):
    description = dumps / 'short.json'
    description.write_text(json.dumps({'raw': FRONT, 'stop': {'ticks': 5}}))
    tool = [sys.executable, os.path.join(ROOT, 'tools', 'headless.py')]
    for name in ('a', 'b'):
        out = subprocess.run(tool + ['run', str(description), '--out', str(dumps / name)],
                             capture_output=True, text=True, check=True).stdout
        assert 'stopped: tick' in out and '5 ticks' in out
    assert 'identical over' in subprocess.run(tool + ['diff', str(dumps / 'a'), str(dumps / 'b')],
                                              capture_output=True, text=True, check=True).stdout
    listing = subprocess.run(tool + ['show', str(dumps / 'a')], capture_output=True, text=True, check=True).stdout
    assert len(listing.splitlines()) > 10
    step = subprocess.run(tool + ['show', str(dumps / 'a'), '--step', '4'],
                          capture_output=True, text=True, check=True).stdout
    assert 'reconstruction matches the hash: True' in step


# ------------------------------------------------------------------ long runs, on request

@SLOW
def test_left_alone_the_program_starts_a_mission_by_itself(dumps):
    """No input at all: the title runs out, the rank selection gives up after 1800 VBlanks and
    asks for demo playback, the demo file is not on the disk, and a mission begins."""
    runs = [run({'raw': [], 'stop': {'ticks': 100}}) for _ in range(2)]
    assert runs[0].step_hashes == runs[1].step_hashes
    assert runs[0].missions == 1 and runs[0].vblanks > 6900
    assert ('Lock', 'wofdemo', False) in runs[0].files_log
    assert runs[0].o.r16(headless.DEMO_MODE) == 0


@SLOW
def test_a_long_flight_twice(dumps):
    runs = [run(flight(ticks=1500)) for _ in range(2)]
    assert runs[0].step_hashes == runs[1].step_hashes
    assert len(runs[0].entropy_log) > 1000
