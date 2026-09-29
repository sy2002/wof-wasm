"""M7 part 1, the campaign and the saved game, against the headless original
(re/notes/porting-m7.md, re/notes/campaign.md).

Every script of tools/m7_scripts.py is recorded under the headless original and run through
the port by tests/m4compare.py in the closed loop (T2): the port runs on its own from the
program's start with nothing handed over but the entropy and the map list's addresses, and
after every tick and every pass it agrees with the original and reaches no stand-in, through
the mission won, the fade, the next map, its briefing, its setup and its first ticks, the
promotions and the rank's cap, the next campaign after a game lost at night, and the save in
the hold.  The open loop (T1) holds every step alone, and the chain of ships_j and save_a's
save hold at one and three VBlanks per pass.  Beside them: the saved file of save_a against the original's
byte for byte but for its pointers, and every address the M7 scripts write accounted for
(tests/m4complete.py).
"""
import os
import sys

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, 'tools'))
sys.path.insert(0, HERE)

import m4compare                   # noqa: E402
import m7_scripts                  # noqa: E402
import savegame                    # noqa: E402
import test_weapons                # noqa: E402
import test_world                  # noqa: E402

SCRIPTS = list(m7_scripts.SCRIPTS)
SLOW = set(m7_scripts.SLOW)


def params(names):
    return [n if n not in SLOW else pytest.param(n, marks=pytest.mark.slow) for n in names]


def closed_loop(ported, name, rate=2):
    """The closed loop over an M7 script with the live map; returns (machine, replay,
    passes, findings, stand-ins, the reason it stopped early or None).  Any stand-in ends
    it."""
    machine, dump_path = test_world.recorded(name, rate, pokes=m7_scripts.pokes(name))
    replay = m4compare.Replay(ported, machine, dump_path, mode='closed', rate=rate,
                              pokes=m7_scripts.pokes(name))

    def stop(r):
        reached = dict(r.standins())
        if reached:
            return 'the port reached %s in tick %d' % (sorted(reached), r.ticks)
        return None

    passes, found = test_world.compare_passes(replay, replay.live_chart, stop=stop)
    SAVED[(name, rate)] = (
        {n: bytes(d) for n, d in machine.overlay.items() if n.startswith('wof.')},
        {n.lower(): bytes(d) for n, d in ported.fs_written()})
    return machine, replay, passes, found, replay.standins(), replay.stopped


# The files each closed loop left on both sides, (script, rate) -> (the original's, the
# port's), for the saved file's own test, which takes them from the loop's run when the
# loop ran in its process (the two are one xdist group) and runs the loop itself otherwise.
SAVED = {}


def assert_closed(machine, replay, passes, found, standins, stopped):
    want = max(h[2] for h in machine.step_hashes if h[0] == 'P')
    assert not found, 'closed loop:\n%s' % found
    assert stopped is None and standins == [], 'the closed loop reached %s' % standins
    assert passes >= want - 1, 'only %d of %d passes compared' % (passes, want)


@pytest.mark.parametrize('name', params(SCRIPTS))
def test_every_pass_agrees_and_every_other_difference_is_owed(ported, name):
    """T1 over an M7 script: every pass and every tick starts from the original's state
    before it; a step that differs must have reached a stand-in of M7 part 2 or of M8 in
    that same step, and no step may reach any other stand-in (none differs)."""
    machine, dump_path = test_world.recorded(name, pokes=m7_scripts.pokes(name))
    replay = m4compare.Replay(ported, machine, dump_path, mode='open',
                              pokes=m7_scripts.pokes(name))
    old = test_weapons.later
    test_weapons.later = lambda marker: 'M7 PART 2 STAND-IN' in marker or 'M8 STAND-IN' in marker
    try:
        steps, differing, bad, reached = test_weapons.attribute(replay)
    finally:
        test_weapons.later = old
    assert steps > (500 if name == 'ships_j' else 800), 'only %d steps compared' % steps
    assert bad == [], '%d of %d differing steps are not owed to a later stand-in: %s' % (
        len(bad), differing, bad[:3])
    assert differing == 0 and not reached, (differing, dict(reached))


@pytest.mark.parametrize('name', params(SCRIPTS))
def test_every_tick_and_pass_agrees_in_the_closed_loop(ported, name):
    """T2 over an M7 script: the mission won, the aircraft back in the hold, the fade, the
    extra Hellcat of a promotion, choose_night, the next map, its briefing, its setup and
    the next mission's flight; the save in the hold and the flight after it."""
    machine, replay, passes, found, standins, stopped = closed_loop(ported, name)
    assert_closed(machine, replay, passes, found, standins, stopped)
    want = {'save_a': 1, 'ships_j': 8}.get(name, 2)
    assert machine.missions == want and replay.missions == want, (machine.missions, replay.missions)


@pytest.mark.slow
@pytest.mark.parametrize('rate', [1, 3])
@pytest.mark.parametrize('name', ['ships_j', 'save_a'])
def test_the_closed_loop_holds_at_other_pass_rates(ported, name, rate):
    """The chain of ships_j at one and three VBlanks per pass against the original run at the
    same rate: every mission won in the hold and the next one set up, through four
    promotions and the rank's cap, whatever a pass's length; and save_a's bombs, landing and
    save, where at one VBlank a pass a dug-out's refill falls between two of the targets'
    fire and hands D1's upper word on to the smoke at the engine, and the channel playing
    the engine's sample the save dialog let go is attributed by this run's samples alone."""
    machine, replay, passes, found, standins, stopped = closed_loop(ported, name, rate)
    assert_closed(machine, replay, passes, found, standins, stopped)
    want = 7 if name == 'ships_j' else 1
    assert machine.missions >= want and replay.missions == machine.missions, (
        machine.missions, replay.missions)


# ------------------------------------------------------------------ the saved file

# What the port writes in the raw part where the original writes an address of its own
# memory (re/notes/campaign.md, "What the port writes in the raw part"), by the field's kind.
POINTER_REASONS = {
    'shape': 'a pointer to a shape record: the port writes its shape handle as a long',
    'pool': 'a pointer to an allocation: the port writes 1, the flag it keeps, as a long',
}


@pytest.mark.parametrize('name', ['save_a'])
def test_the_saved_file_is_the_originals_but_for_its_pointers(ported, name):
    """The file save_a's save in the hold writes (wof.save, map f) is the one the headless
    original wrote in the same run, byte for byte, except where the raw part holds a pointer
    to the original's own memory: the player's shape, the two shape pointers of the tick and
    the cruise ship's gun list.  Every differing byte is listed with its field and reason."""
    if (name, 2) not in SAVED:
        assert_closed(*closed_loop(ported, name))
    originals, ports = SAVED[(name, 2)]
    saved = [n for n in originals if n != 'wof.mission 3']
    assert saved == ['wof.save'], saved
    original, port = originals['wof.save'], ports.get('wof.save')
    assert port is not None and len(port) == len(original) == 6424, (len(original), port and len(port))
    fields = savegame.registry()
    differing = {}
    for i, (a, b) in enumerate(zip(original, port)):
        if a == b:
            continue
        field = savegame.field_of(savegame.RAW_START + i, fields) if i < savegame.RAW_LENGTH else None
        assert field is not None and field[1] in POINTER_REASONS, (
            'byte %d (0x%06X) differs, original %02x, port %02x, in %s' % (
                i, savegame.RAW_START + i, a, b, field))
        differing.setdefault(field, []).append(i)
    assert sorted(differing) == [('g_02541a[0].s', 'shape'), ('player[0].shape', 'shape'),
                                 ('ship_records[2].guns', 'pool'),
                                 ('torpedo_shape[0].s', 'shape')], sorted(differing)
    guns = savegame.SHIPS + 2 * savegame.SHIP_SIZE + 6 - savegame.RAW_START
    assert port[guns:guns + 4] == b'\0\0\0\1', port[guns:guns + 4]
    info = savegame.summary(port)
    assert info['exact'] and info['map'] == 'f' and info['ships'] == ['guns cruiseship'], info


# ------------------------------------------------------------------ completeness (T3)

def test_every_address_the_m7_scripts_write_is_compared_or_excluded(ported, request):
    """T3 over the M7 scripts: every address the original writes during their missions and
    between them - the fade, the next map, its briefing and setup, the save - is a
    registered field, compared by another check, or on an exclusion list with its reason and
    milestone.  The long scripts are taken with --slow."""
    import m4complete
    import m4state
    slow = request.config.getoption('--slow') or os.environ.get('WOF_SLOW') == '1'
    coverage = m4complete.Coverage(
        m4state.Layout(ported),
        excluded=(m4complete.EXCLUDED + m4complete.M5_EXCLUDED + m4complete.M6_EXCLUDED +
                  m4complete.M7_EXCLUDED),
        heap=m4complete.HEAP + m4complete.M5_HEAP + m4complete.M6_HEAP + m4complete.M7_HEAP)
    for name in SCRIPTS:
        if name in SLOW and not slow:
            continue
        key = test_world.recording_key(name, 2, m7_scripts.pokes(name))
        machine = test_world.RECORDED.get(key)
        if machine is None:
            machine = m4compare.Recorder(m7_scripts.script(name), observe=(),
                                         pokes=m7_scripts.pokes(name))
            machine.run()
        coverage.add(machine)
    uncovered = coverage.ranges()
    assert not uncovered, 'written during a mission and neither compared nor excluded:\n' + \
        m4complete.describe(uncovered)
