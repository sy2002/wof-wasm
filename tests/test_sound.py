"""M8 part 1: the instrument and the sound it hears (re/notes/sound.md, re/notes/headless.md).

The headless original's model of Paula (tools/headless_paula.py) is held to what it claims:
it only observes where nothing sounds, a one-shot plays one cycle and is stopped by its
second interrupt, a looping sample restarts at the end of every cycle at the instant its
length and period give, and no request is ever made deliverable where the model would not
deliver it.  The port's event log and model are held to the original's in every closed and
open loop of tests/m4compare.py (tests/test_world.py, test_weapons.py, test_enemy.py); here
the port's PCM is looked at too: silent before a mission's first sound and not after it.
"""
import ctypes
import os
import sys

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, 'tools'))
sys.path.insert(0, HERE)

import headless                    # noqa: E402
import headless_dump as dump       # noqa: E402
import headless_paula              # noqa: E402
import m4compare                   # noqa: E402
import m5_scripts                  # noqa: E402
import m6_scripts                  # noqa: E402
import test_world                  # noqa: E402

OPT_MUSIC_OFF = 0x0254F7
SOUND_INTENA = 0x027F1E            # what soundfx_vblank reads of INTENAR


def recorded(name):
    return test_world.recorded(name, pokes=m6_scripts.pokes(name))


class Steps(headless.Headless):
    """The headless original with a hash of its state after every step, leaving out the one
    word the model changes by being there: soundfx_vblank's copy of INTENAR's audio bits,
    which plain memory reads as 0 and the model as the bits sound_init switched on."""

    def __init__(self, run):
        super().__init__(run)
        self.hashes = []

    def _step(self, kind):
        super()._step(kind)
        state = self.regions()
        data = bytearray(state[headless.DATA_START])
        at = SOUND_INTENA - headless.DATA_START
        data[at:at + 2] = b'\0\0'
        state[headless.DATA_START] = bytes(data)
        self.hashes.append((kind, self.ticks, self.passes, dump.state_hash(state)))


def test_the_model_changes_no_step_of_a_silent_run():
    """An observer-only property, as the other instruments have: the take-off and flight of
    tools/m4_scripts.py with the music switched off (Control-S, opt_music_off), in which the
    engine asks for no sample, gives the same steps, schedule and entropy with the model and
    without it, except soundfx_vblank's copy of INTENAR; and the model delivers nothing."""
    runs = {}
    for paula in (True, False):
        description = m6_scripts.script('flight')
        description['paula'] = paula
        description['music'] = False        # the player answered as idle: the model alone
        description['stop'] = {'ticks': 400}
        machine = Steps(description)
        m5_scripts.install_pokes(machine, {OPT_MUSIC_OFF: (1, 0xFF)})
        machine.run()
        runs[paula] = machine
    on, off = runs[True], runs[False]
    assert on.ticks == 400 and len(on.hashes) > 800
    assert on.hashes == off.hashes
    assert on.schedule == off.schedule
    assert on.entropy_log == off.entropy_log
    assert on.paula.events == [] and on.paula.irqs == 0 and on.paula.late == 0
    assert off.paula is None


def test_a_one_shot_is_stopped_by_its_second_interrupt():
    """The lift's clang is a one-shot, a repeat count of 1 (0x012354): Paula raises the
    channel's request when the channel starts, which audio_irq counts from 1 to 0, and again
    at the end of its one cycle, which counts it below zero and stops the channel.  So the
    clang's channel sees exactly two handler calls from its start, the first at the VBlank it
    starts in and the second at the one its cycle ends in, and its DMA is off after the
    second; no restart of it is heard after that."""
    machine, _ = recorded('kills_a')
    paula = machine.paula
    starts = [e for e in paula.events if e[0] == 'S' and e[5] == 'sounds/metal.clang.1']
    assert starts, 'the script never clangs'
    for start in starts:
        channel, vblank = start[4], start[1]
        calls = [h for h in paula.handled if h[0] >= vblank and channel in h[1]]
        restarts = [e for e in paula.events if e[0] == 'R' and e[4] == channel and e[1] >= vblank]
        assert calls[0][0] == vblank and calls[0][2][channel] == 1, calls[:2]
        assert calls[1][0] == restarts[0][1], (calls[:2], restarts[:1])
        assert calls[1][2][channel] == 0, 'the clang plays on after its cycle: %s' % (calls[:2],)
        nxt = next((e for e in paula.events if e[4] == channel and e[1] > restarts[0][1]), None)
        assert nxt is None or nxt[0] == 'S', nxt


def test_a_looping_sample_restarts_at_the_end_of_every_cycle():
    """The engine loops (a repeat count of -1): every cycle ends in a restart, never a stop,
    and while the period stays, a cycle lasts 2 x LEN bytes of PER colour clocks - in the
    model's units 2 x LEN x PER x hz, a VBlank being the clock's 3,546,895 units at 50 Hz."""
    machine, _ = recorded('kills_a')
    paula = machine.paula
    engine = [e for e in paula.events if e[5] == 'sounds/engine']
    assert engine[0][0] == 'S' and len(engine) > 10
    assert all(e[0] == 'R' for e in engine[1:])
    same = 0
    for a, b in zip(engine, engine[1:]):
        moved = [p for p in paula.periods if p[1] == a[4] and a[10] <= p[0] < b[10]]
        if not moved:
            assert b[10] - a[10] == 2 * a[7] * a[8] * 50, (a, b)
            same += 1
    assert same >= 5, 'too few cycles at one period to hold the arithmetic to'


def test_no_request_waits_for_a_delivery_point():
    """The model delivers requests at the VBlank boundary and after each server; one that
    the main program made deliverable would wait for the next VBlank.  None of the recorded
    scripts makes one."""
    for name in ('kills_a', 'flight'):
        machine, _ = recorded(name) if name == 'kills_a' else test_world.recorded(name)
        assert machine.paula.late == 0, name


def test_the_port_is_silent_before_the_first_sound_and_heard_after(ported):
    """The port's own PCM over kills_a in the closed loop: every frame mixed up to the VBlank
    in which the first sample starts is silence, frames after it are not, and the frames of a
    VBlank are 960 at 48 kHz and 50 Hz."""
    machine, dump_path = recorded('kills_a')
    first = min(e[1] for e in machine.paula.events if e[0] == 'S')
    lib = ported.lib
    buffer = (ctypes.c_int16 * (65536 * 2))()
    heard = []

    def on_pass(r, memory, head, k):
        vblanks = lib.wof_vblank_count()
        frames = lib.wof_audio_render(buffer, 65536, 48000)
        heard.append((vblanks, frames, any(buffer[:frames * 2])))

    replay = m4compare.Replay(ported, machine, dump_path, mode='closed',
                              pokes=m6_scripts.pokes('kills_a'))
    lib.wof_audio_render(buffer, 65536, 48000)
    replay.run(on_pass=on_pass)
    assert len(heard) > 600
    for (v0, _, _), (v1, frames, _) in zip(heard, heard[1:]):
        assert frames == (v1 - v0) * 960, (v0, v1, frames)
    assert not any(loud for vblanks, _, loud in heard if vblanks <= first)
    assert any(loud for vblanks, _, loud in heard if vblanks > first + 1)
