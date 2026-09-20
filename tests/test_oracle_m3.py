"""M3 differential tests: the key path against the original (SPEC 7.4).

Every pure routine the front end is built on runs twice on the same randomised input, once
as 68000 code under the oracle and once as the C the port compiled, and the results and the
memory both of them touched are compared.  What the original needs in order to run without
an operating system is in tests/original.py, which names its stubs.
"""
import os
import random
import struct
import sys

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, 'tools'))
sys.path.insert(0, HERE)

import original                      # noqa: E402
import headless                      # noqa: E402

ROM = os.path.join(ROOT, 'original', 'kick.rom')

# The qualifier bits the generated table covers (tools/extract_tables.py): the two Shift
# keys, Caps Lock and the Control the port's own key layer puts in front of a command.
KEYMAP_CODES = 128
KEYMAP_QUALIFIERS = 16


@pytest.fixture(scope='module')
def keys():
    """One emulated machine with the key buffer set up as keyboard_open leaves it."""
    machine = original.Original()
    machine.keys_init()
    return machine


def port_key_state(ported):
    return ported.g_all('key_buffer'), ported.g_all('key_qualifier_buffer'), ported.g('key_count')


# ------------------------------------------------------------------ the registry, SPEC 7.2

def test_every_ported_global_is_in_the_registry_with_its_original_address(ported):
    registry = ported.globals_registry()
    assert len(registry) >= 20
    for name, (elem, count, addr, offset) in registry.items():
        assert elem in (1, 2, 4), (name, elem)
        assert count >= 1
        assert 0x023000 <= addr < 0x028004, '%s: 0x%06X is outside the DATA and BSS range' % (name, addr)
        assert offset + elem * count <= ported.globals_bytes()
    assert len(set(addr for _, _, addr, _ in registry.values())) == len(registry), \
        'two globals claim the same original address'


def test_the_globals_struct_is_the_sum_of_its_members(ported):
    """The state travels as the struct's bytes, so a hole in it would be uninitialised
    memory in a save state.  wof_init zeroes the whole struct, which makes a hole harmless,
    but a struct without one is the cheaper guarantee and this says whether there is one."""
    registry = ported.globals_registry()
    total = sum(elem * count for elem, count, _, _ in registry.values())
    assert total == ported.globals_bytes(), (
        'wof_globals_t is %d bytes for %d bytes of members: reorder src/globals.def by '
        'decreasing element size' % (ported.globals_bytes(), total))


# ------------------------------------------------------------------ the key buffer

def test_the_buffer_starts_as_keyboard_open_leaves_it(ported, keys):
    ported.keys_init()
    assert ported.g('key_buffer_max') == keys.o.r16(original.KEY_BUFFER_MAX) == 10
    assert ported.g('key_count') == keys.o.r16(original.KEY_COUNT) == 0
    assert ported.g('key_qualifier_mask') == keys.o.r16(original.KEY_QUAL_MASK) == 0


def test_a_key_up_event_is_ignored(ported, keys):
    """input_handler drops an event whose code has bit 7 set; that is the release."""
    keys.keys_init()
    ported.keys_init()
    for code in (0x93, 0xFF, 0x80):
        keys.key_event(code)
        ported.key(code)
    assert keys.key_state()[2] == 0
    assert ported.g('key_count') == 0


def test_the_buffer_is_ten_deep_and_drops_what_does_not_fit(ported, keys):
    keys.keys_init()
    ported.keys_init()
    for i in range(14):
        keys.key_event(0x10 + i, 0x0008 if i % 3 == 0 else 0)
        ported.key(0x10 + i, 0x0008 if i % 3 == 0 else 0)
    assert keys.key_state()[2] == 10
    assert port_key_state(ported) == keys.key_state()


def test_popping_a_full_buffer_reproduces_the_original_off_by_one(ported, keys):
    """The shift loop of key_get runs one entry too far.  With a full buffer that copies the
    high byte of the first qualifier word into the last code slot and key_count itself into
    the last qualifier slot.  Nothing reads those slots until the buffer fills again, but
    they are state, and the port has to leave the same values behind."""
    keys.keys_init()
    ported.keys_init()
    for i in range(10):
        keys.key_event(0x20 + i, 0x0100 * (i + 1))
        ported.key(0x20 + i, 0x0100 * (i + 1))
    assert keys.key_get() == ported.key_get()
    assert port_key_state(ported) == keys.key_state()
    # The shift runs upward, so by its last round the first qualifier word already holds
    # what the second one held: 0x0200, whose high byte is what lands in the last code slot.
    assert keys.key_state()[0][9] == 0x02, 'the quirk is not what this test thinks it is'
    assert keys.key_state()[1][9] == 9, 'the last qualifier slot is not the new key_count'


@pytest.mark.parametrize('seed', range(8))
def test_random_sequences_of_pushes_and_pops_agree(ported, seed):
    """Randomised inputs, results and touched memory compared (SPEC 7.4)."""
    machine = original.Original()
    machine.keys_init()
    ported.keys_init()
    rng = random.Random(seed)

    for _ in range(200):
        if rng.random() < 0.6:
            code = rng.randrange(0x00, 0x100)          # key-up codes included on purpose
            qualifier = rng.choice([0, 1, 2, 4, 8, 9, 0x8000, 0x4321])
            machine.key_event(code, qualifier)
            ported.key(code, qualifier)
        else:
            assert machine.key_available() == ported.key_available()
            if machine.key_available():
                assert machine.key_get() == ported.key_get()
        assert port_key_state(ported) == machine.key_state()


def test_the_qualifier_mask_filters_and_is_taken_out_of_what_key_get_returns(ported):
    """key_qualifier_mask is dead for a game started from the CLI, but it is the other path
    task_setup can take, so the port keeps it: a key that carries none of its bits is
    dropped, and its bits are removed from the qualifier key_get hands back."""
    machine = original.Original()
    machine.keys_init(mask=0x0010)                      # left Alt, what key_mask_default holds
    ported.keys_init()
    ported.set_g('key_qualifier_mask', 0x0010)

    for code, qualifier in ((0x13, 0x0000), (0x14, 0x0010), (0x15, 0x0018)):
        machine.key_event(code, qualifier)
        ported.key(code, qualifier)
    assert machine.key_state()[2] == 2, 'the unqualified key was not dropped'
    assert port_key_state(ported) == machine.key_state()
    assert machine.key_get() == ported.key_get() == 0x0014
    assert machine.key_get() == ported.key_get() == 0x00080015


# ------------------------------------------------------- the key conversion table, SPEC 5

@pytest.mark.skipif(not os.path.exists(ROM), reason='original/kick.rom is not here')
def test_the_generated_table_is_what_the_roms_own_routine_returns(ported):
    """Every raw code under every qualifier combination the table covers, against
    console.device's RawKeyConvert run from the ROM with the ROM's own default keymap - the
    same routine and the same keymap the headless original runs (re/notes/keys.md)."""
    from unicorn import Uc, UC_ARCH_M68K, UC_MODE_BIG_ENDIAN
    from unicorn.m68k_const import (UC_CPU_M68K_M68000, UC_M68K_REG_A0, UC_M68K_REG_A1,
                                    UC_M68K_REG_A2, UC_M68K_REG_A6, UC_M68K_REG_A7,
                                    UC_M68K_REG_D0, UC_M68K_REG_D1, UC_M68K_REG_PC,
                                    UC_M68K_REG_SR)
    with open(ROM, 'rb') as f:
        rom = f.read()
    base = 0x1000000 - len(rom)
    convert, keymap = headless.find_rom_console(rom, base)
    assert convert and keymap

    event, buffer, stack, trap = 0x010000, 0x010100, 0x0F0000, 0x0FFF00
    uc = Uc(UC_ARCH_M68K, UC_MODE_BIG_ENDIAN)
    uc.ctl_set_cpu_model(UC_CPU_M68K_M68000)
    uc.mem_map(0, 0x100000)
    uc.mem_map(base, len(rom))
    uc.mem_write(base, rom)

    characters = 0
    for code in range(KEYMAP_CODES):
        for qualifier in range(KEYMAP_QUALIFIERS):
            uc.mem_write(event, bytes(22))
            uc.mem_write(event + 4, b'\x01')
            uc.mem_write(event + 6, struct.pack('>HH', code, qualifier))
            uc.mem_write(buffer, bytes(8))
            uc.mem_write(stack, struct.pack('>L', trap))
            uc.reg_write(UC_M68K_REG_SR, 0x2000)
            uc.reg_write(UC_M68K_REG_A7, stack)
            uc.reg_write(UC_M68K_REG_A0, event)
            uc.reg_write(UC_M68K_REG_A1, buffer)
            uc.reg_write(UC_M68K_REG_A2, keymap)
            uc.reg_write(UC_M68K_REG_A6, 0)
            uc.reg_write(UC_M68K_REG_D1, 1)
            uc.emu_start(convert, trap, count=200000)
            assert uc.reg_read(UC_M68K_REG_PC) == trap
            want = 0
            if uc.reg_read(UC_M68K_REG_D0) & 0xFFFF == 1:
                want = uc.mem_read(buffer, 1)[0]
            characters += want != 0
            got = ported.key_to_char((qualifier << 16) | code)
            assert got == want, 'raw 0x%02X qualifier %d: port %r, ROM %r' % (
                code, qualifier, got, want)
    assert characters > 500, 'only %d entries carry a character' % characters


def test_key_to_char_answers_the_rows_of_the_note(ported):
    """The table of re/notes/keys.md, which was observed under the headless original."""
    assert ported.key_to_char(0x13) == ord('r')
    assert ported.key_to_char((0x0001 << 16) | 0x13) == ord('R')
    assert ported.key_to_char((0x0008 << 16) | 0x13) == 0x12
    assert ported.key_to_char(0x45) == 0x1B
    assert ported.key_to_char(0x44) == 0x0D
    assert ported.key_to_char(0x41) == 0x08
    assert ported.key_to_char(0x46) == 0x7F
    assert ported.key_to_char(0x40) == ord(' ')
    assert ported.key_to_char(0x4C) == 0, 'a cursor key gives more than one character'
    assert ported.key_to_char(0x50) == 0, 'a function key gives three'


def test_a_code_above_the_table_gives_no_character(ported):
    assert ported.key_to_char(0x80) == 0
    assert ported.key_to_char(0xFFFF) == 0


# --------------------------------------------------------- the port's key layer, SPEC 6.2

CONTROL = 0x0008
ESCAPE, RAW_R, RAW_S, RAW_F, RAW_G, RAW_L, RAW_C, RAW_M, RAW_P = (
    0x45, 0x13, 0x21, 0x23, 0x24, 0x28, 0x33, 0x37, 0x19)


def one_port_key(ported, code, qualifier=0, paused=False, briefing=False, editing=False):
    """What wof_port_key puts into the buffer for one key, in one of the four states."""
    ported.keys_init()
    ported.set_g('pause_flag', 0xFF if paused else 0)
    ported.lib.wt_front_set(1 if editing else 0, 1 if briefing else 0)
    ported.port_key(code, qualifier)
    if not ported.key_available():
        return None
    return ported.key_get()


@pytest.mark.parametrize('code, state, want', [
    # the port's key, the state it is pressed in, the (qualifier << 16) | code it becomes
    (RAW_P, {}, ESCAPE),                                   # pause, anywhere
    (RAW_F, {}, (CONTROL << 16) | RAW_F),                  # the vertical flip
    (RAW_G, {}, (CONTROL << 16) | RAW_G),                  # save
    (RAW_L, {}, (CONTROL << 16) | RAW_L),                  # load
    (RAW_M, {}, (CONTROL << 16) | RAW_S),                  # the music: KeyS is the stick
    (RAW_R, {}, RAW_R),                                    # restart: not while playing
    (RAW_R, {'paused': True}, (CONTROL << 16) | RAW_R),
    (RAW_R, {'briefing': True}, (CONTROL << 16) | RAW_R),
    (RAW_C, {}, RAW_C),                                    # clear: not while playing
    (RAW_C, {'paused': True}, (CONTROL << 16) | RAW_C),
    (ESCAPE, {}, ESCAPE),                                  # the second pause key passes
    (0x20, {}, 0x20),                                      # an ordinary letter passes
    # inside the line editor every key passes as it came, command or not
    (RAW_F, {'editing': True}, RAW_F),
    (RAW_P, {'editing': True}, RAW_P),
    (RAW_R, {'editing': True, 'paused': True}, RAW_R),
])
def test_the_port_key_layer_rewrites_exactly_the_keys_of_the_spec(ported, code, state, want):
    assert one_port_key(ported, code, **state) == want


def test_the_layer_keeps_the_shift_bits_it_was_given(ported):
    """The qualifier the shell sends survives the rewrite: the readers strip it before they
    convert and test only the Control bit, so a Shift held changes nothing but is not lost."""
    assert one_port_key(ported, RAW_F, 0x0001) == ((CONTROL | 0x0001) << 16) | RAW_F
    assert one_port_key(ported, 0x20, 0x0004) == (0x0004 << 16) | 0x20


def test_the_letters_the_layer_always_takes_are_exactly_four(ported):
    """What the keys decision costs, written down so that it is a decision and not a
    surprise.  F, G, L and M carry a command in every state outside the line editor, so a
    plain press of them never reaches a reader as a plain letter; R and C do reach one
    while the game is running.  The consequence is that the cheat sequence c o l i n
    (re/notes/keys.md) cannot be typed through the port's key layer, because its `l` is the
    load command.  Nothing the manual describes is affected: plain letters do nothing in the
    original either, outside the editor and outside the debug keys the cheat unlocks."""
    always = []
    for code in range(0x00, 0x70):
        ported.keys_init()
        ported.set_g('pause_flag', 0)
        ported.lib.wt_front_set(0, 0)
        ported.port_key(code, 0)
        if ported.key_available() and ported.key_get() != code:
            always.append(code)
    assert always == [RAW_P, RAW_F, RAW_G, RAW_L, RAW_M]

    ported.keys_init()
    ported.lib.wt_front_set(1, 0)                       # inside the line editor nothing is
    for code in always:                                 # a command, so all five pass as typed
        ported.port_key(code, 0)
    assert ported.g_all('key_buffer')[:5] == always


# ------------------------------------------------------------------- the vertical flip

def test_a_core_that_was_never_told_behaves_as_the_original(ported):
    """opt_invert_vertical lies in the initialised part of DATA and the executable has a 0
    there, so a fresh core flies arcade fashion, which is what the differential tests run."""
    ported.input_init()
    assert ported.g('opt_invert_vertical') == 0
    assert ported.invert_vertical() == 0


def test_the_remembered_flip_reaches_the_byte_the_joystick_decoder_reads(ported):
    ported.input_init()
    ported.set_invert_vertical(True)
    assert ported.g('opt_invert_vertical') == 0xFF
    assert ported.invert_vertical() == 1
    ported.set_invert_vertical(False)
    assert ported.g('opt_invert_vertical') == 0
    assert ported.invert_vertical() == 0


@pytest.mark.parametrize('raw, plain, flipped', [
    (0x01, 0x1, 0x2),            # the stick pushed forward becomes pulled back
    (0x02, 0x2, 0x1),
    (0x04, 0x8, 0x8),            # right is b3 of read_joy_bits and is not touched
    (0x08, 0x4, 0x4),
    (0x05, 0x9, 0xA),            # forward and right
    (0x00, 0x0, 0x0),            # a centred stick must not come out as up and down at once
])
def test_the_flip_swaps_the_two_vertical_bits_and_only_them(ported, raw, plain, flipped):
    ported.input_init()
    ported.vblank(raw)
    assert ported.read_joy_bits() == plain
    ported.set_invert_vertical(True)
    assert ported.read_joy_bits() == flipped
    ported.set_invert_vertical(False)


# --------------------------------------------------------------- the input sampling

def test_opposing_directions_cancel_before_anything_reads_the_stick(ported):
    """A real stick cannot report both ends of an axis, and the headless original's script is
    turned into hardware state the same way before it writes JOY1DAT."""
    ported.input_init()
    ported.vblank(0x03)
    assert ported.read_joy_bits() == 0 and ported.poll_joy_dir8() == 0
    ported.vblank(0x0C)
    assert ported.read_joy_bits() == 0 and ported.poll_joy_dir8() == 0
    ported.vblank(0x07)                                   # forward, back and right
    assert ported.poll_joy_dir8() == 3, 'the horizontal went with the vertical'


@pytest.mark.parametrize('raw, dir8', [
    (0x00, 0), (0x01, 1), (0x05, 2), (0x04, 3), (0x06, 4),
    (0x02, 5), (0x0A, 6), (0x08, 7), (0x09, 8),
])
def test_the_eight_directions_are_the_ones_the_table_gives(ported, raw, dir8):
    """joy_dir8_table: 0 centre, then clockwise from 1, which is the stick pushed forward."""
    ported.input_init()
    ported.vblank(raw)
    assert ported.poll_joy_dir8() == dir8


def test_a_tap_and_a_hold_are_told_apart_at_vblank_rate(ported):
    """The threshold is ten VBlanks, not ten ticks, and the latches live between samples, so
    a press that begins and ends between two samples is still delivered (re/notes/input.md)."""
    ported.input_init()
    ported.vblank(0x10)                    # pressed
    ported.vblank(0x10)
    ported.vblank(0x00)                    # released after three VBlanks: a tap
    bytes_seen = []
    for _ in range(8):
        ported.vblank(0x00)
        bytes_seen.append(ported.g('input_byte'))
    assert 0x20 in bytes_seen and 0x10 not in bytes_seen

    ported.input_init()
    for _ in range(24):
        ported.vblank(0x10)                # held
    assert ported.g('input_byte') == 0x10


def test_the_queue_holds_six_and_drops_the_oldest(ported):
    ported.input_init()
    for i in range(1, 9):
        for _ in range(4):
            ported.vblank(0x04 if i % 2 else 0x08)
    assert ported.g('input_queue_count') == 6
    ported.input_queue_clear()
    assert ported.g('input_queue_count') == 0


# ------------------------------------------------------------------- the fades, SPEC 6.3

def random_table(rng):
    return [rng.randrange(0x1000) for _ in range(32)]


def fade_case(ported, rng, depth, depth2, colours2, pair, to_black):
    """One fade, run by the original and by the port on the same starting tables."""
    machine = original.Original()
    machine.fade_setup(depth, depth2, colours2)

    start = {name: random_table(rng) for name in machine.tables}
    for name, table in start.items():
        machine.set_table(name, table)

    ported.set_fade_vblanks(0)
    ported.view_setup(depth, depth2, colours2)
    ported.set_colours(0, 0, start['a1'])
    if colours2:
        ported.set_colours(0, 1, start['a2'])
    if depth2:
        ported.set_colours(1, 0, start['b1'])

    target1 = random_table(rng)
    target2 = random_table(rng)

    if pair:
        if to_black:
            machine.fade_out_pair()
            ported.fade_run(pair=True)
        else:
            machine.fade_to_pair(target1, target2)
            ported.fade_run(target1, target2, pair=True)
    else:
        if to_black:
            machine.fade_out()
            ported.fade_run()
        else:
            machine.fade_to(target1)
            ported.fade_run(target1)

    n = 1 << depth
    for name, which, table in (('a1', 0, 0), ('a2', 0, 1), ('b1', 1, 0)):
        if name not in machine.tables:
            continue
        want, got = machine.get_table(name), ported.colours(which, table)
        assert want[:n] == got[:n], '%s: %s vs %s' % (name, want[:n], got[:n])
        assert got[n:] == start[name][n:], '%s: the fade touched a colour past 1 << depth' % name


@pytest.mark.parametrize('depth, depth2, colours2, pair, to_black', [
    (5, 0, False, False, False),      # the picture screens: one viewport, one table
    (5, 0, False, False, True),       # fade_out, whose carry is what the note warns about
    (4, 0, True,  False, False),      # a viewport with a second colour table
    (4, 0, True,  False, True),
    (3, 0, False, False, False),      # the briefing
    (5, 4, False, True,  False),      # the high-score screen: two viewports, two targets
    (5, 4, True,  True,  False),
    (5, 4, True,  True,  True),       # fade_out_pair, which ends the mission
])
def test_the_fades_agree_with_the_original(ported, depth, depth2, colours2, pair, to_black):
    rng = random.Random(0x1234 + depth * 16 + depth2 + pair * 4 + to_black * 2 + colours2)
    for _ in range(4):
        fade_case(ported, rng, depth, depth2, colours2, pair, to_black)


def test_the_number_of_colours_comes_from_the_first_viewports_depth(ported):
    """Both loops of fade_to_pair run 1 << depth of the **first** viewport, even over the
    second one, which here has four planes and therefore sixteen colours of its own.  All
    thirty-two entries of its table are written."""
    machine = original.Original()
    machine.fade_setup(5, 4, False)
    rng = random.Random(9)
    start = {name: random_table(rng) for name in machine.tables}
    for name, table in start.items():
        machine.set_table(name, table)
    machine.fade_to_pair([0] * 32, [0xFFF] * 32)
    assert machine.get_table('b1') == [0xFFF] * 32
    assert machine.get_table('a1') == [0] * 32

    ported.set_fade_vblanks(0)
    ported.view_setup(5, 4, False)
    ported.set_colours(0, 0, start['a1'])
    ported.set_colours(1, 0, start['b1'])
    ported.fade_run([0] * 32, [0xFFF] * 32, pair=True)
    assert ported.colours(1, 0) == [0xFFF] * 32
    assert ported.colours(0, 0) == [0] * 32


def test_a_fade_step_takes_the_provisional_number_of_vblanks(ported):
    """PROVISIONAL (SPEC 10, point 6).  The original's fade is CPU time and nothing in the
    executable says how much, so a step is given a fixed number of VBlanks; the differential
    tests set it to 0, where the harness's fades take no time either."""
    ported.view_setup(5, 0, False)
    for n in (0, 1, 2, 4):
        ported.set_fade_vblanks(n)
        assert ported.fade_vblanks() == n
        assert ported.fade_run([0] * 32) == 16 * n
    ported.set_fade_vblanks(0)


# ------------------------------------------------------ the waits as coroutines, SPEC 6.3

@pytest.mark.parametrize('n, vblanks', [(1, 1), (2, 2), (3, 3), (60, 60), (240, 240), (1800, 1800)])
def test_wait_frames_or_fire_costs_exactly_its_argument_in_vblanks(ported, n, vblanks):
    """One round is one WaitTOF, which is one VBlank, which is one pass.  That is what makes
    the port's front end run to the same timetable as the headless original's."""
    ported.input_init()
    assert ported.frames_run(n) == vblanks


def test_wait_frames_or_fire_ends_early_on_fire_and_says_so(ported):
    ported.input_init()
    assert ported.frames_run(600, raw=0, raw_after=0x10, switch_at=5) < 600
    assert ported.frames_run(600, raw=0x10) == 1, 'the first WaitTOF happens whatever else does'


def test_wait_input_release_waits_for_the_stick_and_the_button(ported):
    """It returns after one round when nothing is held, keeps going while something is, and
    gives up after nine; a key already waiting ends it at once."""
    ported.input_init()
    ported.keys_init()
    assert ported.release_run(raw=0) == 1
    assert ported.release_run(raw=0x10) == 9, 'a held button did not keep it waiting'
    assert ported.release_run(raw=0x04) == 9, 'a pushed stick did not keep it waiting'
    assert ported.release_run(raw=0x10, raw_after=0, switch_at=3) == 3, \
        'it went on waiting after the button came up'
    ported.key(0x13)
    assert ported.release_run(raw=0x10) == 1, 'a waiting key did not end it'
    ported.keys_init()


def test_menu_input_answers_the_keys_the_stick_and_the_button(ported):
    ported.input_init()
    for raw, want in ((0x00, None), (0x01, -1), (0x02, 1), (0x10, 0), (0x04, None)):
        ported.keys_init()
        result, rounds = ported.menu_run(timeout=0, raw=raw, limit=20)
        if want is None:
            assert rounds == 20, 'raw 0x%02X ended the menu' % raw
        else:
            assert result == want and rounds == 0, (raw, result, rounds)

    for code, want in ((0x4C, -1), (0x4D, 1), (0x44, 0), (0x43, 0)):
        ported.input_init()
        ported.keys_init()
        ported.key(code, 0x0008)                 # any qualifier: menu_input takes the code
        result, rounds = ported.menu_run(timeout=0, raw=0, limit=20)
        assert (result, rounds) == (want, 0), (code, result, rounds)

    ported.input_init()
    ported.keys_init()
    ported.key(0x20)                             # a key it does not know falls through
    result, rounds = ported.menu_run(timeout=0, raw=0, limit=20)
    assert rounds == 20 and ported.g('key_count') == 0, 'the key was not taken out of the buffer'


def test_menu_input_gives_up_after_1800_rounds_and_asks_for_a_demo(ported):
    """The timeout that sets demo_mode to 1 in the rank selection (re/notes/frontend.md)."""
    ported.input_init()
    ported.keys_init()
    result, rounds = ported.menu_run(timeout=1, raw=0, limit=4000)
    assert result == 1000
    assert rounds == 1801, 'menu_input gave up after %d rounds' % rounds

    ported.input_init()
    ported.keys_init()
    result, rounds = ported.menu_run(timeout=0, raw=0, limit=2500)
    assert rounds == 2500, 'without the flag it gave up anyway'


# --------------------------------------------------- the story scroller's ring and ramps

def test_the_scrollers_ramps_are_the_grey_ramp_of_the_copper_builder(ported):
    """story_copper_build puts i x 0x111 on COLOR01 at viewport row i and again at row
    196 - i, keeps the brightest value between them and black below (re/notes/display.md).
    The rows here are output rows: the viewport sits at display line 5."""
    def colour_at(row, ramp=16):
        _, rgba = ported.story_bands(0, 0xFFFF, ramp, 5 + row)
        return rgba

    def grey(value):
        component = ((value >> 8) & 0xF) * 17
        return 0xFF000000 | (component << 16) | (component << 8) | component

    for row in range(16):
        assert colour_at(row) == grey(row * 0x111), 'top ramp row %d' % row
    assert colour_at(100) == grey(0xFFF)
    for i in range(16):
        assert colour_at(196 - i) == grey(i * 0x111), 'bottom ramp row %d' % (196 - i)
    assert colour_at(197) == grey(0)
    assert colour_at(203) == grey(0), 'below the lower ramp COLOR01 stays black'

    used, _ = ported.story_bands(0, 0xFFFF, 16)
    assert used == 17, 'the scroller needs %d palettes, not 17' % used
    assert used <= 24

    for ramp in (1, 4, 8, 16):
        used, _ = ported.story_bands(0, 0xFFFF, ramp)
        assert used <= 24
    assert colour_at(100, ramp=1) == grey(0), 'the wind-down did not take the ramp out'


def test_the_scrollers_ring_sends_the_display_back_to_the_first_row(ported):
    """The plane pointer walks up the view's memory and the copper reloads it at the wrap
    row, which is what makes a 200-row bitmap a ring of 210."""
    used, _ = ported.story_bands(30, 180, 16)
    assert used <= 24
    used, _ = ported.story_bands(209, 1, 16)
    assert used <= 24


# ------------------------------------- the justified spacing of the story scroller (M3)

STORY_TEXT = 0x017494          # the block of lines, 2,152 bytes (re/notes/frontend.md)
STORY_WIDTH = 0x267            # what story_screen stretches a line to


def story_lines(machine, count):
    """The lines as the scroller walks them, read out of the executable and never written
    down (CLAUDE.md): a block of NUL-terminated strings."""
    block = machine.o.read(STORY_TEXT, 2152)
    out, at = [], 0
    while len(out) < count and at < len(block):
        end = block.index(b'\x00', at)
        out.append(block[at:end].decode('latin1'))
        at = end + 1
    return out


@pytest.mark.parametrize('justify', [0, STORY_WIDTH])
def test_the_justified_template_agrees_with_the_original(ported, justify):
    """The surplus over the text's own width is spread over the gaps: the quotient to every
    gap and one more pixel to the first remainder gaps (re/notes/drawing.md).  That is what
    makes the scroller's lines fill the screen, and it is compared here template for
    template on the lines it really draws."""
    machine = original.Original()
    machine.font_load()

    for line in story_lines(machine, 14):
        if not line:
            continue                       # an empty line ends a paragraph and is not drawn
        want = machine.text_render(line, 0, 0, justify, 640, 12)
        got = ported.text_render(line, 0, 0, justify, 640, 12)
        assert got == want, 'line %r at justify %d' % (line[:20], justify)


def test_a_wider_justify_than_the_text_spreads_and_a_narrower_one_does_not(ported):
    """Both sides of the branch, over strings of the port's own choosing."""
    machine = original.Original()
    machine.font_load()

    for text in ('a b c', 'one two three four', 'x y', 'hello world'):
        for justify in (0, 40, 100, 300, 615):
            want = machine.text_render(text, 0, 0, justify, 640, 12)
            got = ported.text_render(text, 0, 0, justify, 640, 12)
            assert got == want, (text, justify)
