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
import os
import sys
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
import pass_observe                # noqa: E402

SCRIPTS = ['deck', 'flight', 'climb', 'lost', 'gameover']
NIGHT = {0x025390: (2, 1)}         # night_flag, poked at 0x01009E

# What the tick main runs itself before step S writes of the registered state.  The tick is
# part 2's, so these are the only fields in which the port differs from the original at S.
# The list is the harness's own record of that tick's writes, mapped to the registries;
# test_the_setup_agrees_at_step_s derives it again and holds it to this.
SETUP_TICK_WRITES = [
    'airspeed', 'airspeed_step', 'frame_drawn', 'g_02536a', 'g_0253ac', 'g_0253ae', 'g_0253b0',
    'g_025410', 'g_02542c', 'g_026d3e', 'g_026e62', 'input_queue[0]', 'input_queue[1]',
    'input_queue[2]', 'input_queue[3]', 'input_queue[4]', 'input_queue_count',
    'player[0].enemy_countdown', 'tick_input',
]


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


def compare_passes(replay, chart):
    """Run a replay and compare every pass; returns (passes, findings)."""
    found = Findings()

    def on_pass(r, memory, head, k):
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
        om, pm = r.predicted_map_draws(memory, chart), r.port_map_draws()
        if om != pm:
            found.add('map', k, ('decoder', om[:3], 'port', pm[:3]))

    passes = replay.run(on_pass=on_pass)
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


def run_both_loops(ported, tmp_path, name, rate=2, pokes=None, more=None, loops=('open', 'closed')):
    dump_path = str(tmp_path / ('%s-%d.dump' % (name, rate)))
    machine = m4compare.record(name, dump_path, rate=rate, pokes=pokes, more=more)
    keep_writes(recording_key(name, rate, pokes, more), machine)
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
def test_every_pass_agrees_in_both_loops(ported, tmp_path, name):
    """V1 and V2 over the whole script."""
    machine, results = run_both_loops(ported, tmp_path, name)
    assert_clean(machine, results)


def test_the_night_mission_agrees_in_both_loops(ported, tmp_path):
    """The flight script as a night mission: nightdash.shp, the nightdash picture, night.p and
    nightocean.p, on both sides (re/notes/porting-m4.md, "Night")."""
    machine, results = run_both_loops(ported, tmp_path, 'flight', pokes=NIGHT)
    assert machine.o.r16(0x025390) == 1, 'the poke did not make the mission a night mission'
    opened = [name.lower() for _, call, name, found in machine.files_at if call == 'Open' and found]
    assert 'shapes/nightdash.shp' in opened and 'shapes/night.p' in opened, opened
    assert_clean(machine, results)


@pytest.mark.parametrize('rate', [1, 3])
def test_the_closed_loop_holds_at_other_pass_rates(ported, tmp_path, rate):
    """The positive control of V8: the tick's input does not depend on the pass rate
    (re/notes/passes.md, "The control"), so the closed loop must hold at one and three VBlanks
    per pass as it does at two, through the restart of the lost script."""
    machine, results = run_both_loops(ported, tmp_path, 'lost', rate=rate,
                                      more={'stop': {'ticks': 600}}, loops=('closed',))
    assert_clean(machine, results)


def test_the_setup_agrees_at_step_s(ported, tmp_path):
    """Everything the setup after the briefing writes, at step S: every registered global and
    table agrees except what main's own logic tick wrote, which is part 2's, and that list is
    the harness's record of the tick's writes."""
    dump_path = str(tmp_path / 'setup.dump')
    machine = m4compare.Recorder(pass_observe.script('deck'))
    machine.open_dump(dump_path)
    machine.run(until='inner')
    machine.close()
    replay = m4compare.Replay(ported, machine, dump_path, mode='plain')
    memory, _ = replay.s_states()[0]
    replay.build_index(memory)
    kinds = [e[0] for e in machine.schedule if e[0] != 'V']
    tick = max(i for i, k in enumerate(kinds) if k == 'T')
    by_port = {(w, o): n for n, w, o, _, _ in replay.layout.fields()}
    written = sorted({by_port[(w[0], w[1])] for a in machine.t_writes[tick]
                      for w in [replay.index.get(a)] if w})
    assert written == SETUP_TICK_WRITES, 'the setup tick now writes %s' % written

    replay.run()
    layout = replay.layout
    wg, wm, problems = layout.expected(memory)
    assert not problems, problems
    differences = layout.differences(layout.port_globals(at_s=True), layout.port_mission(at_s=True),
                                     wg, wm, skip=SETUP_TICK_WRITES)
    assert differences == [], differences[:10]


# The runs the completeness test covers: the five scripts, the night mission, and the two of
# re/notes/passes.md that fire the guns and bomb an island, which reach the ricochets, the
# soldiers and the targets' damage.
COVERAGE_RUNS = [(name, None) for name in SCRIPTS] + [('flight', NIGHT), ('guns', None),
                                                     ('bomb', None)]


def test_every_address_a_mission_writes_is_compared_or_excluded(ported):
    """V3: every address the original writes during a mission outside its tick - setup, pass,
    VBlank, main program - is a registered field, compared by another check, or on the
    exclusion list with its reason and milestone (tests/m4complete.py)."""
    coverage = m4complete.Coverage(m4state.Layout(ported))
    for name, pokes in COVERAGE_RUNS:
        machine = RECORDED.get(recording_key(name, 2, pokes))
        if machine is None:
            machine = m4compare.Recorder(pass_observe.script(name), observe=(), pokes=pokes)
            machine.run()
        coverage.add(machine)
    uncovered = coverage.ranges()
    assert not uncovered, 'written during a mission and neither compared nor excluded:\n' + \
        m4complete.describe(uncovered)
    assert coverage.unused_rows() == [], 'rows no run needs any more: %s' % coverage.unused_rows()
    assert coverage.pool_writes > 0
