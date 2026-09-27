"""M8 part 2: the music player, its timer and its songs (re/notes/music.md,
re/notes/headless.md).

The headless original runs the real player: `songplay` and `wofsongs` loaded as LoadSeg
loads them, CIA-A's timer A in the model's time, the player's own level-4 handler.  Here the
instrument is held to what it claims - the player changes nothing of a mission, its songs
start where the game's calls put them, a register that can only be read keeps what the chip
holds - and the port's timer and read-back registers to the same definitions.  The port's
music is compared event by event in tests/test_front_port.py and in every loop of
tests/m4compare.py.
"""
import ctypes
import functools
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
import m6_scripts                  # noqa: E402
import music_steps                 # noqa: E402
import pass_observe                # noqa: E402
import test_front_port             # noqa: E402

@pytest.fixture(autouse=True)
def a_fresh_core_after(request):
    """The runs here leave the port in a mission, its shapes mirrored in place; the tests
    after them take the core as wof_init leaves it."""
    yield
    if 'ported' in request.fixturenames:
        request.getfixturevalue('ported').reset_core()


# The scripts whose missions are held to the player's absence: a kill of the enemy plane
# counter, the guns over map a's island, the take-off from the deck.
MISSIONS = ['kills_a', 'guns_a', 'deck']


# The state's VBlank counts, which count the fades' VBlanks too: vblank_total, vblank_counter,
# fire_press_frame (vblank_counter at a press), sound_vblanks and the VBlank each of the
# four channel records stopped at (re/notes/sound.md).
VBLANK_COUNTS = [0x0253CA, 0x026C92, 0x026C8E, 0x027E6A] + [0x027E72 + 0x1E * c for c in range(4)]


class Steps(headless.Headless):
    """The headless original with a hash of its state after every step, the VBlank counts
    taken less the fades' VBlanks, all of which come before the mission."""

    def __init__(self, run):
        super().__init__(run)
        self.hashes = []

    def _step(self, kind):
        super()._step(kind)
        state = self.regions()
        data = bytearray(state[headless.DATA_START])
        for address in VBLANK_COUNTS:
            at = address - headless.DATA_START
            value = int.from_bytes(data[at:at + 4], 'big')
            if value:
                data[at:at + 4] = ((value - self.spin_vblanks) & 0xFFFFFFFF).to_bytes(4, 'big')
        state[headless.DATA_START] = bytes(data)
        self.hashes.append((kind, self.ticks, self.passes, dump.state_hash(state)))


@functools.lru_cache(maxsize=None)
def mission_run(name, music):
    description = m6_scripts.script(name)
    description['music'] = music
    machine = Steps(description)
    m6_scripts.install_pokes(machine, m6_scripts.pokes(name))
    machine.run()
    return machine


def after_s(machine):
    return machine.schedule[machine.schedule.index(('S', 1)):]


@pytest.mark.parametrize('name', MISSIONS)
def test_the_music_changes_nothing_of_the_mission(name):
    """The run with the real player against the run with the player answered as idle (the
    Paula model on in both): from step S on the schedule, the ticks, the passes, the entropy
    and every step's state are the same, the state's VBlank counts taken less the fades'
    VBlanks.  Before S the fades' waits add those VBlanks, while which the script waits
    (re/notes/headless.md, "The fade's wait"); the player's own memory is gone by S, and its
    timer and vector are not in the state."""
    real, idle = mission_run(name, True), mission_run(name, False)
    assert real.missions == idle.missions == 1
    assert real.spin_vblanks > 0 and idle.spin_vblanks == 0
    assert after_s(real) == after_s(idle)
    assert (real.ticks, real.passes) == (idle.ticks, idle.passes)
    # (index, value, routine, pass, tick): the VBlank a value was drawn at moves by the fades
    assert [e[:3] + e[4:] for e in real.entropy_log] == [e[:3] + e[4:] for e in idle.entropy_log]
    assert len(real.hashes) > 100
    assert real.hashes == idle.hashes


@pytest.mark.parametrize('name', MISSIONS)
def test_the_mission_begins_with_audio_irq_and_the_timer_closed(name):
    """At step S the level-4 vector holds audio_irq again and the timer has no vector: the
    rank selection ended with music_stop, command 4 (re/notes/music.md, "The timer")."""
    machine = mission_run(name, True)
    s = [i for i, e in enumerate(machine.schedule) if e == ('S', 1)]
    assert s and machine.music_at_s is not None
    vector, installed = machine.music_at_s
    assert vector == headless_paula.AUDIO_IRQ and not installed
    assert [c[1] for c in machine.player_calls if c[0] == 'songplay'][-1] == 4


@pytest.fixture(scope='module')
def idle_front():
    return test_front_port.headless_run('front-end-idle')


def test_a_songs_first_notes_start_at_the_first_tick_after_its_call(idle_front):
    """Every song the front end starts (command 2, PlaySong) begins at the timer's next
    tick: its first sample starts fall on that tick's VBlank and instant, and no note of the
    song sounds before it."""
    machine = idle_front
    calls = [c[4] for c in machine.player_calls if c[0] == 'songplay' and c[1] == 2]
    ticks = machine.paula.timer.calls
    songs = [e for e in machine.paula.events if e[5] == 'wofsongs']
    assert len(calls) == 3
    for at in calls:
        vblank, instant, latch = next(t for t in ticks if t[1] >= at * headless_paula.PAL_CLOCK)
        first = [e for e in songs if e[10] >= at * headless_paula.PAL_CLOCK]
        assert first and first[0][10] == instant and first[0][1] == vblank, (at, first[:1], vblank)
        starts = [e for e in first if e[10] == instant]
        assert all(e[0] == 'S' for e in starts) and len(starts) >= 2


def test_the_timer_ticks_at_the_songs_tempo(idle_front):
    """The songs set only the latch's high byte, 56 here; the low byte keeps its power-up
    0xFF, so a tick comes every 0x38FF + 1 E cycles, 14,592 x 5 x 50 units on PAL; the
    first after the timer opens at the power-up latch, 65,536 cycles after it."""
    ticks = idle_front.paula.timer.calls
    tick = headless_paula.E_CLOCK_CC * 50
    assert ticks[0][2] == 0xFFFF and ticks[0][1] == headless_paula.PAL_CLOCK + 0x10000 * tick
    steady = [b[1] - a[1] for a, b in zip(ticks, ticks[1:]) if a[2] == b[2] == 0x38FF]
    assert len(steady) > 5000 and set(steady) == {0x3900 * tick}


def test_a_write_to_a_read_only_register_changes_nothing():
    """A request pending, the player's stray write of 0x0780 to INTREQR, and a read of
    INTREQR still gives the request; INTENAR likewise, and DMACONR keeps what it held."""
    machine = headless.Headless({'stop': {'vblanks': 1}})
    paula, o = machine.paula, machine.o
    paula.intreq, paula.intena = 0x0100, 0x4000 | 0x0780
    paula._publish()
    o.w16(headless_paula.CUSTOM + 0x002, 0x1234)
    code = 0x0D9000
    o.write(code, bytes.fromhex(
        '33FC078000DFF01E'      # move.w #$0780,$dff01e.l
        '33FC000000DFF01C'      # move.w #$0000,$dff01c.l
        '33FCFFFF00DFF002'      # move.w #$ffff,$dff002.l
        '303900DFF01E'          # move.w $dff01e.l,d0
        '323900DFF01C'          # move.w $dff01c.l,d1
        '343900DFF002'          # move.w $dff002.l,d2
        '4E71'))                # nop
    machine.uc.emu_start(code, code + 42)
    assert machine.reg('d0') & 0xFFFF == 0x0100
    assert machine.reg("d1") & 0xFFFF == 0x4780
    assert machine.reg('d2') & 0xFFFF == 0x1234


def test_the_ports_read_only_registers_ignore_a_write(ported):
    """The port's model the same way: wof_paula_write to INTREQR or INTENAR changes neither."""
    lib = ported.lib
    lib.wt_paula_put.argtypes = [ctypes.c_void_p]
    lib.wof_paula_write.argtypes = [ctypes.c_uint16, ctypes.c_uint16]
    lib.wof_paula_intreqr.restype = lib.wof_paula_intenar.restype = ctypes.c_uint16
    ported.reset_core()
    words = ported.paula_state()[:39]
    words[36], words[37] = 0x4000 | 0x0780, 0x0100
    lib.wt_paula_put((ctypes.c_uint32 * 39)(*words))
    lib.wof_paula_write(0x01E, 0x0780)
    lib.wof_paula_write(0x01C, 0x0000)
    assert lib.wof_paula_intreqr() == 0x0100
    assert lib.wof_paula_intenar() == 0x4780


def test_the_ports_timer_follows_the_definition(ported):
    """CIA-A timer A in the port: TAHI loads a stopped timer's counter; CRA 0x10 then 0x01,
    the songs' tempo command, starts it from the latch, an underflow every latch + 1 ticks;
    CRA 0x01 again while it runs leaves it counting; a stop keeps the ticks left less one."""
    lib = ported.lib
    lib.wof_cia_write.argtypes = [ctypes.c_uint32, ctypes.c_uint8]
    ported.reset_core()
    lib.wof_set_video_hz(50)
    tick = 5 * 50

    def timer():
        latch, counter, running, oneshot, lo, hi, vector, level4, calls = ported.paula_state()[39:48]
        return latch, counter, running, oneshot, lo | hi << 32

    assert timer() == (0xFFFF, 0xFFFF, 0, 0, 0)
    lib.wof_cia_write(0xBFE501, 0x38)
    assert timer() == (0x38FF, 0x38FF, 0, 0, 0)
    lib.wof_cia_write(0xBFEE01, 0x10)
    lib.wof_cia_write(0xBFEE01, 0x01)
    assert timer() == (0x38FF, 0x38FF, 1, 0, 0x3900 * tick)
    lib.wof_cia_write(0xBFEE01, 0x01)
    assert timer()[4] == 0x3900 * tick, 'a start of a running timer restarted it'
    lib.wof_cia_write(0xBFEE01, 0x00)
    assert timer() == (0x38FF, 0x38FF, 0, 0, 0)


# ------------------------------------------------------------------ the outer loop

# The front end with fire, five aircraft rolled over the bow, the game over and the high-score
# screen (song 0), the outer loop's rank selection (song 4, faded from song 0), its end with
# music_stop and the second mission; and the same with the music switched off (Control-S,
# raw key 0x21) as the first aircraft stands on the deck, which silences the effects and
# leaves the high-score screen's song unplayed.
OUTER_RAW = pass_observe.FRONT + pass_observe.ROLL_OFF * 5 + [[1500, ''], [4000, '']]
OUTER = {'raw': OUTER_RAW + [[1, '']], 'stop': {'vblanks': 12000}}
OUTER_OFF = {'raw': pass_observe.FRONT + [[40, ''], [1, '', [[0x21, 'ctrl']]]] + OUTER_RAW[10:] +
             [[1, '']], 'stop': {'vblanks': 12000}}
RUNS = {'front-end-idle': 'front-end-idle', 'front-end-fire': 'front-end-fire',
        'outer-loop': OUTER, 'outer-loop-music-off': OUTER_OFF}


@functools.lru_cache(maxsize=None)
def recorded(name):
    return test_front_port.headless_run(RUNS[name], machine_class=music_steps.Recorder)


@pytest.mark.parametrize('name', list(RUNS))
def test_the_music_is_the_originals_after_every_vblank(ported, name):
    """The front end without input and with fire, and the outer loop after a game over with
    the music on and switched off: after every VBlank's pass the port's music state - the
    game's pointers to the two segments, the song asked for, 0x027430, the player's DATA hunk
    and the voices - is the original's before the next VBlank (tests/music_steps.py); and the
    whole sound event log, the songs' and the effects', with timer A where the run ends."""
    machine = recorded(name)
    comparison = music_steps.Comparison(ported)
    found = []

    def each(vblank):
        if found:
            return
        state = machine.state_at(vblank)
        if state is not None:
            d = comparison.differences(state)
            if d:
                found.append((vblank, d))

    test_front_port.replay(ported, machine, each=each)
    assert not found, 'VBlank %d: %s' % found[0]
    loaded = [s for _, s in machine.music_states if s[0][0]]
    assert loaded, 'the music was never loaded'
    want, got = test_front_port.original_events(machine), test_front_port.port_events(ported)
    n = next((i for i, (a, b) in enumerate(zip(got, want)) if a != b), min(len(got), len(want)))
    assert got == want, 'event %d: port %s, original %s' % (n, got[n:n + 2], want[n:n + 2])
    timer = ported.paula_state()[39:48]
    latch, counter, running, oneshot, nxt, vector, level4, calls = machine.paula.snapshot()[4]
    assert timer == [latch, counter, running, oneshot, nxt & 0xFFFFFFFF, nxt >> 32, vector,
                     level4, calls]


def test_the_outer_loop_plays_the_high_scores_and_the_rank_selection_again():
    """After the game over the high-score screen loads the music again and plays song 0;
    the outer loop then goes on to the rank selection, song 4 faded in from song 0, and
    music_stop before the second mission.  The title sequence is not played again: main
    calls it once, before the outer loop."""
    machine = recorded('outer-loop')
    calls = [(c[1], c[2] & 0xFFFF) for c in machine.player_calls if c[0] == 'songplay' and c[1] != 5]
    assert [n for n, _ in machine.loaded_history] == ['wofsongs', 'songplay'] * 2
    second = calls[calls.index((4, 2)) + 1:]
    assert second[:6] == [(0, 22006), (1, 0), (2, 0), (6, 2), (1, 4), (2, 4)], second
    assert second[6:8] == [(6, 2), (4, 2)] and machine.missions == 2


def test_the_music_switched_off_silences_the_effects_and_the_high_scores():
    """Control-S in flight (opt_music_off): no effect is started from then on in that game,
    and the high-score screen's music_start reads the song's voices but starts no song and
    waits for no fade; the outer loop clears the flag before the rank selection, whose song
    plays again."""
    machine = recorded('outer-loop-music-off')
    key_at = next(v for v, code, q in machine.key_log if code == 0x21)
    over_at = next(c[4] for c in machine.player_calls if c[0] == 'songplay' and c[1] == 1
                   and c[2] & 0xFFFF == 0)
    effects = [e for e in machine.paula.events if e[5] != 'wofsongs' and e[0] == 'S']
    assert not [e for e in effects if key_at < e[1] < over_at], 'an effect after Control-S'
    calls = [(c[1], c[2] & 0xFFFF) for c in machine.player_calls if c[0] == 'songplay' and c[1] != 5]
    second = calls[calls.index((4, 2)) + 1:]
    assert second[:3] == [(0, 22006), (1, 0), (6, 2)], second
    assert (1, 4) in second and (2, 4) in second
