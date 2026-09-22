"""M5 part 1, the weapons and the ground targets as the pass draws them, against the headless
original (re/notes/porting-m5.md).

Every script of tools/m5_scripts.py is recorded under the headless original and replayed
through the port in the open loop of tests/m4compare.py: every pass and every tick starts
from the original's state before it.  The pass - the targets, their fire, the soldiers, the
flags, the pools, the objects, the muzzle flash, the weapon counter, the sky's flash - is
part 1's and must agree; the tick is part 2's, so a step may differ only where it reached a
stand-in of part 2 or of a later milestone in that same step.  Beside it: every address the
M5 scripts write accounted for (tests/m4complete.py), and the controls of the note, run by
changing the port and reverting it.
"""
import collections
import os
import sys

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, 'tools'))
sys.path.insert(0, HERE)

import m4compare                   # noqa: E402
import m4complete                  # noqa: E402
import m4state                     # noqa: E402
import m5_scripts                  # noqa: E402
import test_world                  # noqa: E402
from test_world import Findings    # noqa: E402

SCRIPTS = list(m5_scripts.SCRIPTS)
# The long ones run with --slow: the island cleared of its soldiers, and the low passes
# until the engine seizes.
SLOW = {'island_a', 'hit_a'}
LATER = (' PART 2 STAND-IN', 'M6 STAND-IN', 'M7 STAND-IN', 'M8 STAND-IN')


def later(marker):
    """A stand-in of part 2 or of a later milestone: a difference there is owed, not a fault."""
    return any(tag in marker for tag in LATER)


def recorded(name):
    return test_world.recorded(name, pokes=m5_scripts.POKES.get(name))


def attribute(replay):
    """The open loop with every differing step judged: it must have reached a stand-in of
    part 2 or later in that same step.  Returns (steps, differing, [unattributed], the
    stand-ins reached with their counts)."""
    state = {'hits': {}}
    counts = collections.Counter()
    bad = []
    reached = collections.Counter()

    def judge(r, kind, k, found):
        now = dict(r.standins())
        new = [m for m, c in now.items() if c != state['hits'].get(m, 0)]
        for m in new:
            reached[m] += 1
        counts['steps'] += 1
        if found:
            counts['differing'] += 1
            if not any(later(m) for m in new):
                bad.append((kind, k, new, str(found)[:500]))
        elif any(not later(m) for m in new):
            bad.append((kind, k, new, 'a part-1 stand-in reached'))
        state['hits'] = now

    def on_pass(r, memory, head, k):
        found = Findings()
        d = r.state_differences(memory)
        if d:
            found.add('state', k, d[:6])
        oc, pc = r.original_calls(memory, k), r.port_calls()
        if oc != pc:
            n = next((i for i, (a, b) in enumerate(zip(oc, pc)) if a != b), min(len(oc), len(pc)))
            found.add('calls', k, ('original', oc[n:n + 3], 'port', pc[n:n + 3]))
        if r.original_entropy(k) != r.port_entropy():
            found.add('entropy', k, (r.original_entropy(k)[:3], r.port_entropy()[:3]))
        view = r.view_difference(memory)
        if view:
            found.add('view', k, view)
        rows = r.row_differences(memory)
        if rows:
            found.add('rows', k, rows[:1])
        judge(r, 'pass', k, found)

    def on_tick(r, memory, head, k, waited):
        found = Findings()
        d = r.state_differences(memory, live=True)
        if d:
            found.add('tick state', k, d[:6])
        if not r.setup_tick:
            if r.original_tick_calls(memory, k) != r.port_calls():
                found.add('tick calls', k, '')
            if r.original_tick_entropy(k) != r.port_entropy():
                found.add('tick entropy', k, '')
        if waited != r.waits.get(k, 0):
            found.add('tick waits', k, (waited, r.waits.get(k, 0)))
        judge(r, 'tick', k, found)

    replay.run(on_pass=on_pass, on_tick=on_tick)
    return counts['steps'], counts['differing'], bad, reached


def open_loop(ported, name):
    machine, dump_path = recorded(name)
    replay = m4compare.Replay(ported, machine, dump_path, mode='open',
                              pokes=m5_scripts.POKES.get(name))
    return attribute(replay)


@pytest.mark.parametrize('name', [n if n not in SLOW else
                                  pytest.param(n, marks=pytest.mark.slow) for n in SCRIPTS])
def test_every_pass_agrees_and_every_other_difference_is_owed(ported, name):
    """The open loop over an M5 script: a pass or a tick that differs from the original must
    have reached a stand-in of part 2 or later in that same step, and no step may reach a
    stand-in of part 1."""
    steps, differing, bad, reached = open_loop(ported, name)
    assert steps > 800, 'only %d steps compared' % steps
    assert bad == [], '%d of %d differing steps are not owed to a later stand-in: %s' % (
        len(bad), differing, bad[:3])


# ------------------------------------------------------------------ completeness (T3)

# What the M5 scripts write that neither registry holds, beside tests/m4complete.py's rows:
# (first, last, writers, what it is, why the port does not keep it, milestone).
M5_EXCLUDED = [
    (0x027700, 0x027723, {'crash_hit'},
     'g_027700: the object record 0x0146C6 makes up for a crash on land (x at +0, type 0 at '
     '+0x22) and hands to 0x0146DC',
     'the crash on land is the tick\'s, behind the stand-in at 0x01BBF4', 'M5 part 2'),
]
# Display memory beside tests/m4complete.py's HEAP rows.
M5_HEAP = [
    ('ticker_vport_init', {'vblank_server'},
     'the ticker\'s plane, which vblank_server scrolls and fills with glyphs by CPU',
     'the port scrolls its own plane (wof_vblank_ticker); the message pointer and the '
     'counters are registered and compared after every step, and the plane is held to the '
     'original VBlank by VBlank under the oracle (test_the_ticker_matches_the_original)',
     'M4'),
]


def test_every_address_the_m5_scripts_write_is_compared_or_excluded(ported, request):
    """T3 over the M5 scripts: every address the original writes during their missions is a
    registered field, compared by another check, or on an exclusion list with its reason and
    milestone.  The two long scripts are taken with --slow."""
    slow = request.config.getoption('--slow') or os.environ.get('WOF_SLOW') == '1'
    coverage = m4complete.Coverage(m4state.Layout(ported),
                                   excluded=m4complete.EXCLUDED + M5_EXCLUDED,
                                   heap=m4complete.HEAP + M5_HEAP)
    for name in SCRIPTS:
        if name in SLOW and not slow:
            continue
        key = test_world.recording_key(name, 2, m5_scripts.POKES.get(name))
        machine = test_world.RECORDED.get(key)
        if machine is None:
            machine = m4compare.Recorder(m5_scripts.script(name), observe=(),
                                         pokes=m5_scripts.POKES.get(name))
            machine.run()
        coverage.add(machine)
    uncovered = coverage.ranges()
    assert not uncovered, 'written during a mission and neither compared nor excluded:\n' + \
        m4complete.describe(uncovered)
