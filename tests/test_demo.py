"""M7 part 2, the demo, against the headless original (re/notes/demo.md).

The demo scripts of tools/m7_scripts.py - a recording made with main's argument, and the
attract mode's playback of it after 1800 idle rounds of the rank selection, ended by fire,
by a 0xFF poked in early and by the count of 0x1386 entries - are recorded under the
headless original and run through the port by tests/m4compare.py in the closed loop (T2)
from the program's start: the demo buffer is a registered pool, so every byte recorded or
played is compared after every tick and every pass.
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
import test_campaign               # noqa: E402
import test_world                  # noqa: E402

DEMOS = ['demo_record', 'demo_record_long', 'demo_play', 'demo_play_ff', 'demo_play_long']


def params(names):
    return [n if n not in m7_scripts.PART2_SLOW else pytest.param(n, marks=pytest.mark.slow)
            for n in names]


@pytest.mark.parametrize('name', params(DEMOS))
def test_a_demo_agrees_in_the_closed_loop(ported, name):
    """T2 over a demo script: the recording's buffer and its file, or the attract mode's
    request, the file read, the seed from the beam, two ticks a pass, the end, and the
    high scores skipped after a playback."""
    machine, replay, passes, found, standins, stopped = test_campaign.closed_loop(ported, name)
    test_campaign.assert_closed(machine, replay, passes, found, standins, stopped)


def ports_files(ported, replay):
    """The files the port has written after the rest of the schedule: the replay ends with
    the original's last step, the mission's last pass, and the script's Control-R and
    demo_end come after it (m4compare.Replay.run_tail)."""
    replay.run_tail()
    return dict(ported.fs_written())


def test_the_ports_recording_is_the_originals_file(ported):
    """demo_record in the closed loop: the wofdemo the port's demo_end writes is the one the
    headless original wrote in the same run, all 5,000 bytes (the rank, the input bytes,
    the 0xFF, the zeros); beside it the port's wofdemo.seed, 12 bytes: the entropy stream's
    state where the recording began, the demo's hash, the swell's phase and night_flag."""
    machine, replay, passes, found, standins, stopped = test_campaign.closed_loop(
        ported, 'demo_record')
    test_campaign.assert_closed(machine, replay, passes, found, standins, stopped)
    written = ports_files(ported, replay)
    original = bytes(machine.overlay['wofdemo'])
    assert len(original) == 0x1388 and written['wofdemo'] == original
    seed = written['wofdemo.seed']
    assert len(seed) == 12
    h = 0x811C9DC5
    for b in original:
        h = ((h ^ b) * 0x01000193) & 0xFFFFFFFF
    assert int.from_bytes(seed[4:8], 'big') == h


def test_the_original_plays_the_ports_recording_as_the_port_does(ported):
    """The port's own recording (demo_record's closed loop) played back by the attract mode
    of the headless original and of the port, both from the program's start with the same
    entropy and without the seed file, as on another machine: the closed loop holds the
    two playbacks after every tick and every pass."""
    machine, replay, passes, found, standins, stopped = test_campaign.closed_loop(
        ported, 'demo_record')
    test_campaign.assert_closed(machine, replay, passes, found, standins, stopped)
    demo = ports_files(ported, replay)['wofdemo']
    more = {'files': {'wofdemo': demo.hex()}}
    machine, dump_path = test_world.recorded('demo_play', 2, pokes={}, more=more)
    replay = m4compare.Replay(ported, machine, dump_path, mode='closed', rate=2, pokes={})
    passes, found = test_world.compare_passes(replay, replay.live_chart)
    test_campaign.assert_closed(machine, replay, passes, found, replay.standins(), replay.stopped)
    assert machine.o.read(0x026F8C, 1)[0] == 0xFF, 'the original played no demo'


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


@pytest.mark.parametrize('name', params(DEMOS))
def test_every_step_agrees_in_the_open_loop(ported, name):
    open_loop(ported, name)
