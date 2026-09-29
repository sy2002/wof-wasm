"""M5, the weapons and the ground targets, against the headless original
(re/notes/porting-m5.md).

Every script of tools/m5_scripts.py is recorded under the headless original and replayed
through the port by tests/m4compare.py.  In the closed loop (T2) the port runs on its own
from the program's start and every tick and every pass must agree, with no stand-in
reached; island_a runs on through its win into the campaign's next mission (M7), and is
compared to its end.  In the open loop (T1) every step starts from the original's state
before it, and a step may differ only where it reached a stand-in of M6 or M7.  Both loops
also compare the map's draws with tools/map_decode.py's prediction from the original's
live record list, which the hits rewrite.  Beside them: the closed loop at one and three
VBlanks per pass, and every address the M5 scripts write accounted for
(tests/m4complete.py).
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
LATER = ('M6 STAND-IN', 'M7 STAND-IN', 'M7 PART 2 STAND-IN')


def later(marker):
    """A stand-in of M6 or M7: a difference there is owed, not a fault."""
    return any(tag in marker for tag in LATER)


def recorded(name):
    return test_world.recorded(name, pokes=m5_scripts.POKES.get(name))


def attribute(replay):
    """The open loop with every differing step judged: it must have reached a stand-in of
    M6 or M7 in that same step, and no step may reach another.  Returns (steps, differing,
    [unattributed], the stand-ins reached with their counts)."""
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
            bad.append((kind, k, new, 'a stand-in of M5 reached'))
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
        om, pm = r.predicted_map_draws(memory, r.live_chart(memory)), r.port_map_draws()
        if om != pm:
            found.add('map', k, ('decoder', om[:3], 'port', pm[:3]))
        sound = r.sound_differences(head)
        if sound:
            found.add('sound', k, sound)
        paula = r.paula_differences(memory)
        if paula:
            found.add('paula', k, paula[:4])
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
        sound = r.sound_differences(head)
        if sound:
            found.add('tick sound', k, sound)
        paula = r.paula_differences(memory)
        if paula:
            found.add('tick paula', k, paula[:4])
        judge(r, 'tick', k, found)

    replay.run(on_pass=on_pass, on_tick=on_tick)
    return counts['steps'], counts['differing'], bad, reached


def open_loop(ported, name):
    machine, dump_path = recorded(name)
    replay = m4compare.Replay(ported, machine, dump_path, mode='open',
                              pokes=m5_scripts.POKES.get(name))
    return attribute(replay)


def closed_loop(ported, name, rate=2):
    """The closed loop over a script with the live map; returns (machine, passes, findings,
    stand-ins, the reason it stopped early or None)."""
    machine, dump_path = test_world.recorded(name, rate, pokes=m5_scripts.POKES.get(name))
    replay = m4compare.Replay(ported, machine, dump_path, mode='closed', rate=rate,
                              pokes=m5_scripts.POKES.get(name))

    def stop(r):
        reached = dict(r.standins())
        if reached:
            return 'the port reached %s in tick %d' % (sorted(reached), r.ticks)
        return None

    passes, found = test_world.compare_passes(replay, replay.live_chart, stop=stop)
    return machine, passes, found, replay.standins(), replay.stopped


def assert_closed(machine, name, passes, found, standins, stopped):
    want = max(h[2] for h in machine.step_hashes if h[0] == 'P')
    assert not found, 'closed loop:\n%s' % found
    assert stopped is None and standins == [], 'the closed loop reached %s' % standins
    assert passes >= want - 1, 'only %d of %d passes compared' % (passes, want)
    if name == 'island_a':
        # The mission is won, the aircraft comes down, and back in the hold main goes on to
        # the campaign's next mission (0x010132, M7): map b's briefing, setup and hold.
        assert machine.missions == 2, machine.missions


@pytest.mark.parametrize('name', [n if n not in SLOW else
                                  pytest.param(n, marks=pytest.mark.slow) for n in SCRIPTS])
def test_every_tick_and_pass_agrees_in_the_closed_loop(ported, name):
    """T2 over an M5 script: the port runs on its own from the program's start - the front
    end, the setup, the flight, the drops, the hits, the guns, the soldiers, the crash - and
    after every tick and every pass its registered state, its drawing calls, its entropy,
    its view, its rows, its markers and its map draws are the original's."""
    machine, passes, found, standins, stopped = closed_loop(ported, name)
    assert_closed(machine, name, passes, found, standins, stopped)


@pytest.mark.slow
@pytest.mark.parametrize('name', ['bomb_a', 'hit_a'])
@pytest.mark.parametrize('rate', [1, 3])
def test_the_closed_loop_holds_at_other_pass_rates(ported, name, rate):
    """The closed loop at one and three VBlanks per pass against the original run at the
    same rate: bombs in flight between passes, and the targets' fire until the engine
    seizes."""
    machine, passes, found, standins, stopped = closed_loop(ported, name, rate)
    assert_closed(machine, name, passes, found, standins, stopped)


@pytest.mark.parametrize('name', [n if n not in SLOW else
                                  pytest.param(n, marks=pytest.mark.slow) for n in SCRIPTS])
def test_every_pass_agrees_and_every_other_difference_is_owed(ported, name):
    """The open loop over an M5 script: a pass or a tick that differs from the original must
    have reached a stand-in of M6 or M7 in that same step, and no step may reach any other
    stand-in."""
    steps, differing, bad, reached = open_loop(ported, name)
    assert steps > 800, 'only %d steps compared' % steps
    assert bad == [], '%d of %d differing steps are not owed to a later stand-in: %s' % (
        len(bad), differing, bad[:3])


# ------------------------------------------------------------------ completeness (T3)

def test_every_address_the_m5_scripts_write_is_compared_or_excluded(ported, request):
    """T3 over the M5 scripts: every address the original writes during their missions is a
    registered field, compared by another check, or on an exclusion list with its reason and
    milestone.  The two long scripts are taken with --slow; island_a goes on into the next
    mission of its campaign, whose rows are M7's."""
    slow = request.config.getoption('--slow') or os.environ.get('WOF_SLOW') == '1'
    coverage = m4complete.Coverage(m4state.Layout(ported),
                                   excluded=(m4complete.EXCLUDED + m4complete.M5_EXCLUDED +
                                             m4complete.M7_EXCLUDED),
                                   heap=m4complete.HEAP + m4complete.M5_HEAP + m4complete.M7_HEAP)
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


# ------------------------------------------- the value marker of soldier_out (0x011E82)

def test_a_soldier_always_finds_a_free_record():
    """soldier_out's walk (0x011E82) has no end: with every soldier record in use it would run
    past the table, which the port marks as a value stand-in.  It cannot happen: the soldiers
    inside the slot-3 and slot-4 targets (+0x08), those a hit let out that are still to come
    (+0x0A) and the records in use (running, dying or dead) always add up to soldier_count,
    so while a soldier is to come out a record is free.  Held in the original's state at
    every step of every M5 script but the two long ones."""
    import headless_dump as dump
    checked = 0
    for name in SCRIPTS:
        if name in SLOW:
            continue
        machine, dump_path = recorded(name)
        reader = dump.DumpReader(dump_path)
        for head in reader:
            memory = m4state.Memory(reader.regions, copy=False)
            count = memory.u(0x0253C4, 2)
            soldiers = memory.u(0x025500, 4)
            if not count or not soldiers:
                continue
            inside = 0
            for table, n in ((0x0254FC, memory.u(0x025386, 1)), (0x0254F8, memory.u(0x025387, 1))):
                block = memory.read(memory.u(table, 4), 0x10 * n)
                inside += sum(block[0x10 * i + 8] + block[0x10 * i + 0x0A] for i in range(n))
            block = memory.read(soldiers, 8 * count)
            used = sum(1 for i in range(count) if block[8 * i + 6] or block[8 * i + 7])
            assert inside + used == count, '%s step %s: %d inside, %d in use, %d records' % (
                name, head.get('pass') or head.get('tick'), inside, used, count)
            checked += 1
    assert checked > 20000
