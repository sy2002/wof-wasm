"""The keyboard assist (src/assist.c, re/notes/porting-m4.md, "The keyboard assist").

The port's own policy, decided with the owner: in the weapon menu in the hold a press of
forward or back is one step, up is up whatever the flip says, and a press made while a step
runs is remembered; everywhere else a tap shorter than four VBlanks reaches the tick exactly
once.  Everything here runs natively on the port alone, from the program's start with the
fades at 0, the way the closed loop does; the assist-off halves are the original's own counts,
which the headless original gave for the same taps (the note's table).
"""
import ctypes
import os
import sys

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), 'tools'))
sys.path.insert(0, HERE)

import headless                    # noqa: E402
import m4_scripts                  # noqa: E402
import m4state                     # noqa: E402
import pass_observe                # noqa: E402

# In the hold with the weapon menu up and live: 0x026D3E has run down by then.
HOLD = pass_observe.FRONT + [[40, '']]
# On the deck, the menu closed by the button and the lift up.
DECK = HOLD + [[3, 'F'], [240, '']]
# In the air, climbing to the right after the take-off.
FLIGHT = pass_observe.FRONT + pass_observe.TAKE_OFF + [[60, 'R']]

CURSOR_UP = 0x4C
CURSOR_DOWN = 0x4D


class Core:
    """The native core driven VBlank by VBlank, with the weapon type watched after every
    pass and the tick's input byte recorded at the end of every tick."""

    def __init__(self, ported, assist=None, invert=None):
        self.p = ported
        lib = self.lib = ported.lib
        for name, args, res in (
                ('wof_set_keyboard_assist', [ctypes.c_int], None),
                ('wof_keyboard_assist', [], ctypes.c_int),
                ('wof_dev_player', [], ctypes.c_void_p),
                ('wt_set_tick_hook', [ctypes.c_void_p], None),
                ('wt_set_vblanks_per_pass', [ctypes.c_int], None)):
            f = getattr(lib, name)
            f.argtypes = args
            f.restype = res
        ported.reset_core(fade_vblanks=0)
        lib.wt_set_vblanks_per_pass(2)
        if assist is not None:
            lib.wof_set_keyboard_assist(1 if assist else 0)
        if invert is not None:
            ported.set_invert_vertical(invert)
        self.index = {name: ported._global_index(name)
                      for name in ('weapon_type', 'tick_input', 'g_025364', 'vblank_divider',
                                   'g_026d3e', 'g_02536e')}
        self.vblank = 0
        self.steps = []                    # (VBlank, -1 or +1) for every step of the menu
        self.ticks = []                    # (VBlank, tick_input, menu flag after the tick)
        self.on_tick = None
        self._hook = ctypes.CFUNCTYPE(None, ctypes.c_uint32)(self._tick)
        lib.wt_set_tick_hook(ctypes.cast(self._hook, ctypes.c_void_p))

    def close(self):
        self.lib.wt_set_tick_hook(None)

    def g(self, name):
        value = self.lib.wt_global_get(self.index[name], 0)
        return value - 0x10000 if name == 'weapon_type' and value >= 0x8000 else value

    def _tick(self, tick):
        # Inside the pass that follows the VBlank being run, which is not counted yet.
        self.ticks.append((self.vblank + 1, self.g('tick_input'), self.g('g_025364')))
        if self.on_tick:
            self.on_tick(tick)

    def run(self, count, letters='', keys=()):
        raw = headless.raw_state(letters)
        for i in range(count):
            if i == 0:
                for code in keys:
                    self.p.port_key(code, 0)
            before = self.g('weapon_type')
            self.lib.wof_vblank(raw)
            self.lib.wof_pass()
            self.vblank += 1
            after = self.g('weapon_type')
            if after != before:
                self.steps.append((self.vblank, -1 if after == (before - 1) % 3 else 1))

    def script(self, segments):
        for segment in segments:
            self.run(segment[0], segment[1])

    def to_phase(self, phase):
        """Run idle until the next VBlank would be `phase` VBlanks after a sample."""
        while (4 - self.g('vblank_divider')) % 4 != phase:
            self.run(1)

    def player(self):
        return list((ctypes.c_int16 * 4).from_address(self.lib.wof_dev_player()))

    def ticks_since(self, vblank):
        return [t for t in self.ticks if t[0] > vblank]


@pytest.fixture
def core(ported):
    made = []

    def make(**options):
        made.append(Core(ported, **options))
        return made[-1]
    yield make
    for c in made:
        c.close()


def in_the_hold(core, **options):
    c = core(**options)
    c.script(HOLD)
    assert c.g('g_025364') and c.g('g_026d3e') == 0, 'the weapon menu is not up and live'
    c.steps = []
    return c


def taps(c, letters, length, count=12, gap=20, keys=()):
    for _ in range(count):
        c.run(length, letters, keys)
        c.run(gap)


# --------------------------------------------------------------------- the weapon menu

def test_the_core_starts_with_the_assist_off(core):
    c = core()
    assert c.lib.wof_keyboard_assist() == 0
    c.lib.wof_set_keyboard_assist(1)
    assert c.lib.wof_keyboard_assist() == 1


@pytest.mark.parametrize('length', [1, 2, 3, 5])
@pytest.mark.parametrize('letters,step', [('U', -1), ('D', 1)], ids=['forward', 'back'])
def test_every_tap_is_one_step_of_the_weapon_menu(core, length, letters, step):
    """Twelve taps 20 VBlanks apart give twelve steps, forward decreasing the weapon type."""
    c = in_the_hold(core, assist=True)
    taps(c, letters, length)
    assert [s for _, s in c.steps] == [step] * 12, c.steps


@pytest.mark.parametrize('length,steps', [(1, 1), (2, 2), (4, 4), (8, 8), (12, 12)])
def test_without_the_assist_the_taps_give_the_originals_counts(core, length, steps):
    """The headless original's counts for the same taps (re/notes/porting-m4.md): one step
    costs three samples.  The core is never told about the assist, so this is its default."""
    c = in_the_hold(core)
    taps(c, 'U', length)
    assert [s for _, s in c.steps] == [-1] * steps, c.steps


@pytest.mark.parametrize('assist', [True, False], ids=['assist', 'original'])
def test_held_forward_steps_twenty_times_in_240_vblanks(core, assist):
    c = in_the_hold(core, assist=assist)
    c.run(240, 'U')
    c.run(40)
    assert [s for _, s in c.steps] == [-1] * 20, c.steps


def test_the_flip_does_not_turn_the_push_round(core):
    c = in_the_hold(core, assist=True, invert=1)
    taps(c, 'U', 3, count=4)
    taps(c, 'D', 3, count=2)
    assert [s for _, s in c.steps] == [-1] * 4 + [1] * 2, c.steps


def test_without_the_assist_the_flip_turns_the_stick_round(core):
    """The control for the test above: the original's flip is on in these cores."""
    c = in_the_hold(core, invert=1)
    taps(c, 'U', 12, count=2)
    assert [s for _, s in c.steps] == [1] * 2, c.steps


def test_the_cursor_code_that_comes_with_a_tap_gives_no_second_step(core):
    """The page delivers ArrowUp twice: as the stick bit and as the cursor code 0x4C, which
    the weapon menu reads through last_key on a tick without stick.  A tap at every phase of
    the divider, with the code at its first VBlank and the keyboard's repeats of it after
    that, is one step each."""
    c = in_the_hold(core, assist=True)
    for phase in range(4):
        for length in (1, 3, 6, 30):
            c.to_phase(phase)
            before = len(c.steps)
            for i in range(length):
                c.run(1, 'U', keys=(CURSOR_UP,) if i % 3 == 0 else ())
            c.run(40)
            assert [s for _, s in c.steps[before:]] == [-1] * ((length + 11) // 12), \
                (phase, length, c.steps[before:])


def test_a_key_held_when_the_menu_opens_steps_nothing_until_pressed_again(core):
    """The key's own repeats of the cursor code included, which the original's menu would
    step on through last_key."""
    c = core(assist=True)
    c.script(pass_observe.FRONT[:7])           # the fourth press of the button ends the briefing
    assert c.p.mission_count() == 0
    opened = None
    for i in range(3 + 160):
        c.run(1, 'FU' if i < 3 else 'U', keys=(CURSOR_UP,) if i % 3 == 0 else ())
        if opened is None and c.p.mission_count():
            opened, c.steps = c.vblank, []
    assert opened and c.g('g_025364') and c.g('g_026d3e') == 0, opened
    assert c.steps == [], c.steps
    c.run(10)
    c.run(1, 'U', keys=(CURSOR_UP,))
    c.run(30)
    assert [s for _, s in c.steps] == [-1], c.steps


@pytest.mark.parametrize('length', [2, 5])
@pytest.mark.parametrize('period', [10, 12], ids=['200ms-pal', '200ms-ntsc'])
def test_three_quick_taps_are_three_steps(core, period, length):
    """A press made while a step runs is remembered and starts the next push when the
    current one ends.  A press still down when the push ends would start the next one
    anyway; a short one is gone by then and needs the memory."""
    c = in_the_hold(core, assist=True)
    for _ in range(3):
        c.run(length, 'U')
        c.run(period - length)
    c.run(60)
    assert [s for _, s in c.steps] == [-1] * 3, c.steps


def test_at_most_two_presses_are_remembered(core):
    c = in_the_hold(core, assist=True)
    for letters in ('U', 'D', 'U', 'U', 'D'):
        c.run(1, letters)
        c.run(1)
    c.run(60)
    assert [s for _, s in c.steps] == [-1, 1, -1], c.steps


def test_the_pollers_see_the_controller_as_it_is(core):
    c = in_the_hold(core, assist=True)
    c.run(1, 'U')
    seen = []
    for _ in range(11):
        c.run(1)
        seen.append(c.p.poll_joy_dir8())
    assert seen == [0] * 11, seen
    assert sum(1 for t in c.ticks_since(c.vblank - 12) if t[1] & 1) == 3
    c.run(1, 'D')
    assert c.p.poll_joy_dir8() == 5


def test_the_push_ends_with_the_menu(core):
    """A push started one VBlank before the button: the tick that closes the menu and every
    tick after it carries only what the controller carries."""
    for phase in range(4):
        c = in_the_hold(core, assist=True)
        c.to_phase(phase)
        start = c.vblank
        c.run(1, 'U')
        c.run(3, 'F')
        c.run(60)
        closed = [t for t in c.ticks_since(start) if not t[2]]
        assert closed and closed[0][1] & 0x30, (phase, c.ticks_since(start))
        assert all(t[1] & 0x0F == 0 for t in closed), (phase, closed)
        assert c.player()[2] == 11 or c.player()[2] == 1, c.player()


# -------------------------------------------------------------------- the never-lost tap

@pytest.mark.parametrize('where', ['deck', 'flight'])
@pytest.mark.parametrize('letters,bit', [('U', 0x01), ('D', 0x02), ('L', 0x08)])
def test_a_one_vblank_tap_reaches_the_tick_once_at_every_phase(core, where, letters, bit):
    c = core(assist=True)
    c.script(DECK if where == 'deck' else FLIGHT)
    assert c.player()[2] == (1 if where == 'deck' else 0), c.player()
    for phase in range(4):
        c.to_phase(phase)
        start = c.vblank
        c.run(1, letters)
        c.run(24)
        got = [t[1] for t in c.ticks_since(start) if t[0] <= start + 25]
        assert sum(1 for b in got if b & bit) == 1, (phase, got)


@pytest.mark.parametrize('length', [2, 3])
def test_a_short_tap_across_a_sample_is_one_tick_not_two(core, length):
    c = core(assist=True)
    c.script(DECK)
    for phase in range(4):
        c.to_phase(phase)
        start = c.vblank
        c.run(length, 'U')
        c.run(24)
        got = [t[1] for t in c.ticks_since(start) if t[0] <= start + 24 + length]
        assert sum(1 for b in got if b & 1) == 1, (phase, got)


def test_without_the_assist_a_one_vblank_tap_is_seen_at_one_phase_in_four(core):
    c = core()
    c.script(DECK)
    seen = []
    for phase in range(4):
        c.to_phase(phase)
        start = c.vblank
        c.run(1, 'U')
        c.run(24)
        seen.append(sum(1 for t in c.ticks_since(start) if t[1] & 1))
    assert sorted(seen) == [0, 0, 0, 1], seen


def test_a_press_is_the_samples_it_covers(core):
    """Longer than a sample apart, the assist adds nothing: ten VBlanks are two or three
    ticks, as in the original."""
    for assist in (False, True):
        counts = []
        c = core(assist=assist)
        c.script(DECK)
        for phase in range(4):
            c.to_phase(phase)
            start = c.vblank
            c.run(10, 'U')
            c.run(24)
            counts.append(sum(1 for t in c.ticks_since(start) if t[1] & 1))
        assert sorted(counts) == [2, 2, 3, 3], (assist, counts)


# ------------------------------------------------------------------------ what it reaches

# What the weapon menu writes (0x0112B0 and the gauge reset it calls) and what the dashboard
# keeps of it: its caches of the weapon and the count, and the clip rectangle its drums are
# drawn with, which a redraw of the gauge leaves behind.
WEAPON_FIELDS = ('weapon_type', 'weapon_count', 'g_02536e', 'gauge_weapons_tens',
                 'gauge_weapons_ones', 'view_caches[0].weapon', 'view_caches[1].weapon',
                 'view_caches[0].weapons', 'view_caches[1].weapons', 'clip_top', 'clip_bottom')
# The sample itself, which is what the assist changes.
SAMPLE_FIELDS = ('input_byte', 'tick_input') + tuple('input_queue[%d]' % i for i in range(6))


def tick_states(core, layout, name, assist):
    c = core(assist=assist)
    out = []
    c.on_tick = lambda tick: out.append((c.vblank + 1, c.g('g_025364'),
                                         layout.port_globals(), layout.port_mission()))
    c.script([segment[:2] for segment in m4_scripts.script(name)['raw']])
    c.close()
    return out


@pytest.mark.parametrize('name', ['deck', 'select'])
def test_the_assist_reaches_nothing_but_the_weapon_menu(core, ported, name):
    """The same raw schedule with the assist off and on, the whole registered state after
    every tick: on the deck script nothing differs; on the select script the sample differs
    while the menu is up, and otherwise only the weapon and what the dashboard keeps of it.
    The lift, the roll and the climb that follow are the same to the byte."""
    layout = m4state.Layout(ported)
    off = tick_states(core, layout, name, False)
    on = tick_states(core, layout, name, True)
    assert len(off) == len(on) > 300
    differing = set()
    for (v0, menu0, g0, m0), (v1, menu1, g1, m1) in zip(off, on):
        assert v0 == v1
        for field, _, _ in layout.differences(g1, m1, g0, m0):
            differing.add(field)
            if field in SAMPLE_FIELDS:
                assert menu0 and menu1, (v0, field)
            else:
                assert field in WEAPON_FIELDS, (v0, field)
    if name == 'deck':
        assert differing == set()
    else:
        assert {'weapon_type', 'tick_input'} <= differing, differing
