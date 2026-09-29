"""The world as a pass, against the headless original (M4 part 1, re/notes/porting-m4.md).

Every pass of the five mission scripts of M4 is compared with the original's in both loops
of tests/m4compare.py: the open loop, which starts every pass from the original's state
before it (V1), and the closed loop, which runs the port on its own and hands it only what
each tick of the original wrote (V2).  After every pass: every registered global and table,
the drawing calls, the entropy draws, the palette of every output row, and the map draws
against tools/map_decode.py; and no marked stand-in may have been reached.

The night mission is the flight script with night_flag poked to 1 at the rank selection's
end on both sides, because the original chooses night only between two missions of a
campaign (re/notes/porting-m4.md, "Night").
"""
import collections
import glob
import os
import sys
import tempfile
import types

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, 'tools'))
sys.path.insert(0, HERE)

import map_decode                  # noqa: E402
import m4compare                   # noqa: E402
import m4complete                  # noqa: E402
import m4state                     # noqa: E402
import headless                    # noqa: E402
import m4_scripts                  # noqa: E402
import pass_observe                # noqa: E402

SCRIPTS = ['deck', 'flight', 'climb', 'lost', 'gameover', 'select', 'turns', 'landing']
SLOW_SCRIPTS = ['fuel']
NIGHT = {0x025390: (2, 1)}         # night_flag, poked at 0x01009E

# The key runs of M3 that start a mission and press a key in it (tests/runs/).  One is left
# out: in flight-flip-then-load the original loads a saved game, and the loader is M7's (the
# port's dialog comes back as a cancel and counts the stand-in).
KEY_RUNS = sorted(os.path.basename(f)[:-5] for f in
                  glob.glob(os.path.join(ROOT, 'tests', 'runs', 'flight-*.json')) +
                  glob.glob(os.path.join(ROOT, 'tests', 'runs', 'paused-*.json'))
                  if 'flip-then-load' not in f)



class Findings:
    """What went wrong in a run, by check, with the first few cases of each."""

    def __init__(self):
        self.count = collections.Counter()
        self.first = collections.defaultdict(list)

    def add(self, check, pass_number, detail):
        self.count[check] += 1
        if len(self.first[check]) < 3:
            self.first[check].append((pass_number, detail))

    def __bool__(self):
        return bool(self.count)

    def __str__(self):
        lines = []
        for check, n in sorted(self.count.items()):
            lines.append('%s: %d passes' % (check, n))
            for pass_number, detail in self.first[check]:
                lines.append('  pass %d: %s' % (pass_number, str(detail)[:600]))
        return '\n'.join(lines)


def compare_passes(replay, chart, stop=None):
    """Run a replay and compare every pass; returns (passes, findings).  `chart` is the map
    the draws are predicted from, or a function of the step's memory giving it; `stop(r)`,
    when given, may end the replay before a step with a reason (m4compare.Replay.stopped)."""
    found = Findings()

    def stopping(r):
        if stop and not r.stopped:
            r.stopped = stop(r)
        return r.stopped

    def on_pass(r, memory, head, k):
        if stopping(r):
            return
        d = r.state_differences(memory)
        if d:
            found.add('state', k, d[:8])
        oc, pc = r.original_calls(memory, k), r.port_calls()
        if oc != pc:
            n = next((i for i, (a, b) in enumerate(zip(oc, pc)) if a != b), min(len(oc), len(pc)))
            found.add('calls', k, ('original', oc[n:n + 3], 'port', pc[n:n + 3]))
        oe, pe = r.original_entropy(k), r.port_entropy()
        if oe != pe:
            found.add('entropy', k, ('original', oe[:4], 'port', pe[:4]))
        view = r.view_difference(memory)
        if view:
            found.add('view', k, view)
        rows = r.row_differences(memory)
        if rows:
            found.add('rows', k, rows[:2])
        om, pm = r.predicted_map_draws(memory, chart(memory) if callable(chart) else chart), \
            r.port_map_draws()
        if om != pm:
            found.add('map', k, ('decoder', om[:3], 'port', pm[:3]))
        sound = r.sound_differences(head)
        if sound:
            found.add('sound', k, sound)
        paula = r.paula_differences(memory)
        if paula:
            found.add('paula', k, paula[:4])

    def on_tick(r, memory, head, k, waited):
        if stopping(r):
            return
        d = r.state_differences(memory, live=True)
        if d:
            found.add('tick state', k, d[:8])
        if r.setup_tick:
            return
        oc, pc = r.original_tick_calls(memory, k), r.port_calls()
        if oc != pc:
            n = next((i for i, (a, b) in enumerate(zip(oc, pc)) if a != b), min(len(oc), len(pc)))
            found.add('tick calls', k, ('original', oc[n:n + 3], 'port', pc[n:n + 3]))
        oe, pe = r.original_tick_entropy(k), r.port_entropy()
        if oe != pe:
            found.add('tick entropy', k, ('original', oe[:4], 'port', pe[:4]))
        want = r.waits.get(k, 0)
        if waited != want:
            found.add('tick waits', k, ('port', waited, 'original', want))
        view = r.view_difference(memory)
        if view:
            found.add('tick view', k, view)
        markers = r.marker_differences(memory)
        if markers:
            found.add('tick markers', k, markers[:4])
        sound = r.sound_differences(head)
        if sound:
            found.add('tick sound', k, sound)
        paula = r.paula_differences(memory)
        if paula:
            found.add('tick paula', k, paula[:4])

    try:
        passes = replay.run(on_pass=on_pass, on_tick=on_tick)
    except AssertionError as error:
        # The port has run on where the original's run has no step (a control that loads
        # another map): what differed before it is the finding.
        raise AssertionError('%s\n%s' % (error, found)) from None
    return passes, found


# What the recordings of this module wrote during their missions, for the completeness test,
# so that it does not have to run the scripts again: (name, rate, pokes, more) -> writes.
RECORDED = {}


def recording_key(name, rate=2, pokes=None, more=None):
    return (name, rate, tuple(sorted((pokes or {}).items())), repr(more))


def keep_writes(key, machine):
    RECORDED[key] = types.SimpleNamespace(
        names=machine.names, alloc_labels=dict(machine.alloc_labels),
        alloc_sizes=dict(machine.alloc_sizes), display_allocs=dict(machine.display_allocs),
        at_s=list(machine.at_s), mission_writes=machine.mission_writes)


def compare_attributed(replay, chart):
    """The open loop with every difference attributed: a pass or a tick that differs from
    the original must have reached a marked stand-in in that same pass or tick.  Returns
    (steps compared, differing steps, the unattributed ones)."""
    counts = {'last': 0, 'steps': 0, 'differing': 0}
    unattributed = []

    def hits(r):
        return sum(count for _, count in r.standins())

    def judge(r, kind, k, found):
        now = hits(r)
        counts['steps'] += 1
        if found:
            counts['differing'] += 1
            if now == counts['last']:
                unattributed.append((kind, k, str(found)[:400]))
        counts['last'] = now

    inner = Findings()

    def on_pass(r, memory, head, k):
        found = Findings()
        d = r.state_differences(memory)
        if d:
            found.add('state', k, d[:6])
        if r.original_calls(memory, k) != r.port_calls():
            found.add('calls', k, '')
        if r.original_entropy(k) != r.port_entropy():
            found.add('entropy', k, '')
        if r.sound_differences(head):
            found.add('sound', k, '')
        if r.paula_differences(memory):
            found.add('paula', k, '')
        judge(r, 'pass', k, found)

    def on_tick(r, memory, head, k, waited):
        found = Findings()
        d = r.state_differences(memory, live=True)
        if d:
            found.add('tick state', k, d[:6])
        if r.original_tick_calls(memory, k) != r.port_calls():
            found.add('tick calls', k, '')
        if r.original_tick_entropy(k) != r.port_entropy():
            found.add('tick entropy', k, '')
        if waited != r.waits.get(k, 0):
            found.add('tick waits', k, (waited, r.waits.get(k, 0)))
        if r.sound_differences(head):
            found.add('tick sound', k, '')
        if r.paula_differences(memory):
            found.add('tick paula', k, '')
        judge(r, 'tick', k, found)

    replay.run(on_pass=on_pass, on_tick=on_tick)
    return counts['steps'], counts['differing'], unattributed


# Each script is recorded under the headless original once per session and shared by every
# test that replays it; the dumps live in a directory of their own for the session.
RECORDINGS = {}
RECORDING_DIR = tempfile.mkdtemp(prefix='wof-m4-')


def recorded(name, rate=2, pokes=None, more=None):
    key = recording_key(name, rate, pokes, more)
    if key not in RECORDINGS:
        dump_path = os.path.join(RECORDING_DIR, '%s-%d-%d.dump' % (
            name.replace(':', '_'), rate, len(RECORDINGS)))
        machine = m4compare.record(name, dump_path, rate=rate, pokes=pokes, more=more)
        keep_writes(key, machine)
        RECORDINGS[key] = (machine, dump_path)
    return RECORDINGS[key]


def run_both_loops(ported, tmp_path, name, rate=2, pokes=None, more=None, loops=('open', 'closed')):
    machine, dump_path = recorded(name, rate, pokes, more)
    chart = map_decode.load('a')
    results = {}
    for mode in loops:
        replay = m4compare.Replay(ported, machine, dump_path, mode=mode, rate=rate, pokes=pokes)
        passes, found = compare_passes(replay, chart)
        results[mode] = (passes, found, replay.standins())
    return machine, results


def assert_clean(machine, results):
    want = max(h[2] for h in machine.step_hashes if h[0] == 'P')
    for mode, (passes, found, standins) in results.items():
        assert passes >= want - 1 and passes > 100, '%s: only %d passes compared' % (mode, passes)
        assert not found, '%s loop:\n%s' % (mode, found)
        assert standins == [], '%s loop reached stand-ins: %s' % (mode, standins)


@pytest.mark.parametrize('name', SCRIPTS)
def test_every_pass_and_tick_agrees_in_both_loops(ported, tmp_path, name):
    """T1 and T2 over the whole script: the open loop, from the original's state before
    every pass and every tick, and the true closed loop from the program's start with
    nothing handed over."""
    machine, results = run_both_loops(ported, tmp_path, name)
    assert_clean(machine, results)


@pytest.mark.slow
@pytest.mark.parametrize('name', SLOW_SCRIPTS)
def test_the_long_scripts_agree_in_both_loops(ported, tmp_path, name):
    """T1 and T2 over the fuel script: 5,500 ticks of flight until the tank is empty."""
    machine, results = run_both_loops(ported, tmp_path, name)
    assert_clean(machine, results)


def test_the_island_flight_differs_only_where_a_stand_in_was_reached(ported, tmp_path):
    """The flight over the island of map a without the button (tools/m4_scripts.py, ISLAND)
    reaches M5's stand-ins - the soldiers, the targets' guns - so it is judged by attribution:
    in the open loop every pass and every tick that differs from the original reached a
    marked stand-in in that same pass or tick."""
    machine, dump_path = recorded('island')
    replay = m4compare.Replay(ported, machine, dump_path, mode='open')
    steps, differing, unattributed = compare_attributed(replay, map_decode.load('a'))
    assert steps > 1000, 'only %d steps compared' % steps
    assert unattributed == [], '%d of %d differing steps reached no stand-in: %s' % (
        len(unattributed), differing, unattributed[:3])


@pytest.mark.parametrize('name', KEY_RUNS)
def test_the_key_runs_agree_in_both_loops(ported, tmp_path, name):
    """T2 over M3's key runs in a mission: pause and continue, the restart, the flip, the
    save on the carrier and its refusal in the air, the load, the music, the high scores
    cleared while paused, the cheat sequence."""
    machine, results = run_both_loops(ported, tmp_path, 'run:' + name)
    want = max((h[2] for h in machine.step_hashes if h[0] == 'P'), default=0)
    for mode, (passes, found, standins) in results.items():
        assert passes >= want - 1, '%s: only %d passes compared' % (mode, passes)
        assert not found, '%s loop:\n%s' % (mode, found)
        assert standins == [], '%s loop reached stand-ins: %s' % (mode, standins)


def test_the_night_mission_agrees_in_both_loops(ported, tmp_path):
    """The flight script as a night mission: nightdash.shp, the nightdash picture, night.p and
    nightocean.p, on both sides (re/notes/porting-m4.md, "Night")."""
    machine, results = run_both_loops(ported, tmp_path, 'flight', pokes=NIGHT)
    assert machine.o.r16(0x025390) == 1, 'the poke did not make the mission a night mission'
    opened = [name.lower() for _, call, name, found in machine.files_at if call == 'Open' and found]
    assert 'shapes/nightdash.shp' in opened and 'shapes/night.p' in opened, opened
    assert_clean(machine, results)


def test_the_flip_with_the_stick_turned_round_flies_the_same_flight(ported, tmp_path):
    """The positive control: the port with the vertical flip on (wof_set_invert_vertical) and
    the turns script's forward and back exchanged flies the original's flight.  In the closed
    loop every pass and every tick agrees apart from the flip's own byte."""
    machine, dump_path = recorded('turns')
    replay = m4compare.Replay(ported, machine, dump_path, mode='closed')
    forward, back = headless.RAW_BITS['U'], headless.RAW_BITS['D']
    found = Findings()

    def swapped(raw):
        return (raw & ~(forward | back)) | (forward if raw & back else 0) | (back if raw & forward else 0)

    def on_pass(r, memory, head, k):
        d = r.state_differences(memory, skip=('opt_invert_vertical',))
        if d:
            found.add('state', k, d[:6])

    def on_tick(r, memory, head, k, waited):
        d = r.state_differences(memory, skip=('opt_invert_vertical',), live=True)
        if d:
            found.add('tick state', k, d[:6])

    try:
        passes = replay.run(on_pass=on_pass, on_tick=on_tick, raw=swapped,
                            on_reset=lambda r: r.lib.wof_set_invert_vertical(1))
    finally:
        ported.reset_core()
    assert passes > 1000 and not found, found
    assert machine.o.read(0x0254F6, 1) == b'\0'


@pytest.mark.slow
@pytest.mark.parametrize('name', ['lost', 'turns'])
@pytest.mark.parametrize('rate', [1, 3])
def test_the_closed_loop_holds_at_other_pass_rates(ported, tmp_path, name, rate):
    """The tick's input does not depend on the pass rate (re/notes/passes.md, "The
    control"), so the true closed loop must hold at one and three VBlanks per pass as it
    does at two against the original run at the same rate: through the restart of the lost
    script, and through every turn of the turns script."""
    machine, results = run_both_loops(ported, tmp_path, name, rate=rate, loops=('closed',))
    assert_clean(machine, results)


def test_the_setup_agrees_at_step_s(ported, tmp_path):
    """Everything the setup after the briefing writes, main's own logic tick included, at
    step S: every registered global and table agrees, with nothing left out."""
    dump_path = str(tmp_path / 'setup.dump')
    machine = m4compare.Recorder(pass_observe.script('deck'))
    machine.open_dump(dump_path)
    machine.run(until='inner')
    machine.close()
    replay = m4compare.Replay(ported, machine, dump_path, mode='plain')
    memory, _ = replay.s_states()[0]
    replay.run()
    layout = replay.layout
    wg, wm, problems = layout.expected(memory)
    assert not problems, problems
    differences = layout.differences(layout.port_globals(at_s=True), layout.port_mission(at_s=True),
                                     wg, wm)
    assert differences == [], differences[:10]


# The runs the completeness test covers: the five scripts, the night mission, and the two of
# re/notes/passes.md that fire the guns and bomb an island, which reach the ricochets, the
# soldiers and the targets' damage.
COVERAGE_RUNS = [(name, None) for name in SCRIPTS] + [('flight', NIGHT), ('guns', None),
                                                     ('bomb', None), ('island', None)]


def test_every_address_a_mission_writes_is_compared_or_excluded(ported):
    """T3: every address the original writes during a mission in any phase - setup, tick,
    pass, VBlank, main program - is a registered field, compared by another check, or on
    the exclusion list with its reason and milestone (tests/m4complete.py)."""
    coverage = m4complete.Coverage(m4state.Layout(ported))
    for name, pokes in COVERAGE_RUNS:
        machine = RECORDED.get(recording_key(name, 2, pokes))
        if machine is None:
            machine = m4compare.Recorder(m4_scripts.script(name), observe=(), pokes=pokes)
            machine.run()
        coverage.add(machine)
    uncovered = coverage.ranges()
    assert not uncovered, 'written during a mission and neither compared nor excluded:\n' + \
        m4complete.describe(uncovered)
    assert coverage.unused_rows() == [], 'rows no run needs any more: %s' % coverage.unused_rows()
    assert coverage.pool_writes > 0
