"""M6, the enemy aircraft, the ships, the torpedo attack and the carrier's defence, against
the headless original (re/notes/porting-m6.md).

Every script of tools/m6_scripts.py is recorded under the headless original and run
through the port by tests/m4compare.py in the closed loop (T2): the port runs on its own
from the program's start with nothing handed over but the entropy and the map list's
address, and after every tick and every pass it must agree with the original and reach no
stand-in.  The open loop (T1) keeps every step starting from the original's state: a step
may differ only where it reached a stand-in of M7 or M8 in that same step.  Beside them:
every address the M6 scripts write accounted for (tests/m4complete.py), the tables'
capacities on all fifteen maps, and the register the ship guns hand on.
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
import m6_scripts                  # noqa: E402
import test_weapons                # noqa: E402
import test_world                  # noqa: E402

SCRIPTS = list(m6_scripts.SCRIPTS)
SLOW = set(m6_scripts.SLOW)
LATER = ('M7 STAND-IN', 'M7 PART 2 STAND-IN', 'M8 STAND-IN')


def later(marker):
    """A stand-in of M7 or M8: a difference there is owed, not a fault."""
    return any(tag in marker for tag in LATER)


def recorded(name):
    return test_world.recorded(name, pokes=m6_scripts.pokes(name))


def open_loop(ported, name):
    machine, dump_path = recorded(name)
    replay = m4compare.Replay(ported, machine, dump_path, mode='open',
                              pokes=m6_scripts.pokes(name))
    old = test_weapons.later
    test_weapons.later = later
    try:
        return test_weapons.attribute(replay)
    finally:
        test_weapons.later = old


def params(names):
    return [n if n not in SLOW else pytest.param(n, marks=pytest.mark.slow) for n in names]


def closed_loop(ported, name, rate=2):
    """The closed loop over an M6 script with the live map; returns (machine, passes,
    findings, stand-ins, the reason it stopped early or None).  Any stand-in ends it."""
    machine, dump_path = test_world.recorded(name, rate, pokes=m6_scripts.pokes(name))
    replay = m4compare.Replay(ported, machine, dump_path, mode='closed', rate=rate,
                              pokes=m6_scripts.pokes(name))

    def stop(r):
        reached = dict(r.standins())
        if reached:
            return 'the port reached %s in tick %d' % (sorted(reached), r.ticks)
        return None

    passes, found = test_world.compare_passes(replay, replay.live_chart, stop=stop)
    return machine, passes, found, replay.standins(), replay.stopped


def assert_closed(machine, passes, found, standins, stopped):
    want = max(h[2] for h in machine.step_hashes if h[0] == 'P')
    assert not found, 'closed loop:\n%s' % found
    assert stopped is None and standins == [], 'the closed loop reached %s' % standins
    assert passes >= want - 1, 'only %d of %d passes compared' % (passes, want)


@pytest.mark.parametrize('name', params(SCRIPTS))
def test_every_tick_and_pass_agrees_in_the_closed_loop(ported, name):
    """T2 over an M6 script: the port runs on its own from the program's start - the rank
    selection, the setup of the map, the flight, the enemy's launches from the countdown,
    the airfields and the ships, the enemy aircraft's flight, attack, turns, fall and
    burning, the guns at them, the ships' guns and their shells, a torpedo into a ship and
    into the carrier, the sinking, the crash on a ship, the landing on a sunken deck and
    the game's end - and after every tick and every pass its registered state, its drawing
    calls, its entropy with its callers, its view, its rows, its markers and its map draws
    are the original's, and it reaches no stand-in."""
    assert_closed(*closed_loop(ported, name))


@pytest.mark.slow
@pytest.mark.parametrize('name', ['torpedo_f', 'enemy_a'])
@pytest.mark.parametrize('rate', [1, 3])
def test_the_closed_loop_holds_at_other_pass_rates(ported, name, rate):
    """The closed loop at one and three VBlanks per pass against the original run at the same
    rate: the torpedo into the cruise ship and its sinking, and the countdown's torpedo plane
    into the carrier."""
    assert_closed(*closed_loop(ported, name, rate))


@pytest.mark.parametrize('name', params(SCRIPTS))
def test_every_pass_agrees_and_every_other_difference_is_owed(ported, name):
    """T1 over an M6 script: a pass or a tick that differs from the original must have reached
    a stand-in of M7 or M8 in that same step, and no step may reach any other stand-in."""
    steps, differing, bad, reached = open_loop(ported, name)
    assert steps > 800, 'only %d steps compared' % steps
    assert bad == [], '%d of %d differing steps are not owed to a later stand-in: %s' % (
        len(bad), differing, bad[:3])


# ------------------------------------------------------------------ completeness (T3)

def test_every_address_the_m6_scripts_write_is_compared_or_excluded(ported, request):
    """T3 over the M6 scripts: every address the original writes during their missions is a
    registered field, compared by another check, or on an exclusion list with its reason and
    milestone.  The long scripts are taken with --slow."""
    slow = request.config.getoption('--slow') or os.environ.get('WOF_SLOW') == '1'
    coverage = m4complete.Coverage(
        m4state.Layout(ported),
        excluded=m4complete.EXCLUDED + m4complete.M5_EXCLUDED + m4complete.M6_EXCLUDED,
        heap=m4complete.HEAP + m4complete.M5_HEAP + m4complete.M6_HEAP)
    for name in SCRIPTS:
        if name in SLOW and not slow:
            continue
        key = test_world.recording_key(name, 2, m6_scripts.pokes(name))
        machine = test_world.RECORDED.get(key)
        if machine is None:
            machine = m4compare.Recorder(m6_scripts.script(name), observe=(),
                                         pokes=m6_scripts.pokes(name))
            machine.run()
        coverage.add(machine)
    uncovered = coverage.ranges()
    assert not uncovered, 'written during a mission and neither compared nor excluded:\n' + \
        m4complete.describe(uncovered)


# --------------------------------------------------------------- capacities, all maps

@pytest.fixture(scope='module')
def maps():
    import m6_observe
    return {letter: m6_observe.map_content(letter) for letter in 'abcdefghijklmno'}


def test_the_tables_the_pass_walks_hold_every_map(maps):
    """The tables part 1 reads have fixed capacities in the port: the islands' two lists of
    four words (islands_draw reads as many as island_count and would read on past them), a
    ship's gun list of 16 (src/mission.def), and a ship's block of deck aircraft, seven
    entries of eight bytes behind its header of 0x40 bytes (ship_planes reads as many as its
    count).  Held at step S on all fifteen maps under their own numbers."""
    for letter, content in maps.items():
        assert content['islands'] <= 4, (letter, content['islands'])
        for ship in content['ships']:
            assert ship['guns'] <= 16, (letter, ship)
            assert ship['planes'] <= 7, (letter, ship)
    assert max(c['islands'] for c in maps.values()) == 4          # map m
    assert max(s['planes'] for c in maps.values() for s in c['ships']) == 7   # map o


# --------------------------------------------------------- a register across a call

def test_the_ship_guns_find_d1_and_d2_clear_at_their_entry():
    """ship_guns_draw (0x014C3E) hands D1's upper word on as the fraction of a destroyed
    gun's smoke and, through target_fire's exchange, of the engine's smoke; D2's with it.
    Both are 0 at every entry of the routine over the M6 scripts that fly over a ship, which
    is what the port takes (src/world.c)."""
    import headless
    entries = collections.Counter()
    for name in ('cruise_f', 'rockets_f', 'battleship_j', 'japcarrier_m'):
        m = headless.Headless(m6_scripts.script(name), observe=['ship_guns_draw'])
        m6_scripts.install_pokes(m, m6_scripts.pokes(name))
        m.run()
        for rec in m.observed:
            entries[(rec['d'][1] >> 16, rec['d'][2] >> 16)] += 1
    assert set(entries) == {(0, 0)}, entries
    assert sum(entries.values()) > 3000
