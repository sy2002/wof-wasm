"""M6, the enemy aircraft, the ships, the torpedo attack and the carrier's defence, against
the headless original (re/notes/porting-m6.md).

Part 1 ports the pass: what the M6 scripts execute in frame_update's tree and in the VBlank
server.  Every script of tools/m6_scripts.py is recorded under the headless original and
replayed through the port by tests/m4compare.py in the open loop (T1): every step starts
from the original's state before it, and a step may differ only where it reached a
stand-in of part 2 (the tick), M7 or M8 in that same step; no step may reach any other.
Beside it: every address the M6 scripts write accounted for (tests/m4complete.py), the
tables' capacities on all fifteen maps, and the register the ship guns hand on.
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
LATER = ('M6 PART 2 STAND-IN', 'M7 STAND-IN', 'M8 STAND-IN')


def later(marker):
    """A stand-in of M6's second part, M7 or M8: a difference there is owed, not a fault."""
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


@pytest.mark.parametrize('name', params(SCRIPTS))
def test_every_pass_agrees_and_every_other_difference_is_owed(ported, name):
    """T1 over an M6 script: a pass or a tick that differs from the original must have reached
    a stand-in of part 2, M7 or M8 in that same step, and no step may reach any other
    stand-in.  The passes carry the enemy aircraft, their wrecks and their guns' flash, the
    ships' guns and their shells, the aircraft on the ships' decks and the Japanese carrier's
    crane, the airfields, the arrows, the enemy plane counter and the 3-D view."""
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
