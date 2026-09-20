"""The port's front end against the headless original, VBlank by VBlank (SPEC 8, M3).

The headless original runs the real thing: its own code from `main` on, with the operating
system and time replaced (re/notes/headless.md).  A run records the schedule it produced -
one entry per VBlank, with the controller state of that VBlank - together with the keys it
delivered, the files it opened, the music it asked for and, with observers on, every
drawing call it made.

This file replays that schedule through the port: `wof_key` for the keys of a VBlank,
`wof_vblank` with the same raw state, then `wof_pass`.  One CO_WAIT of the port is one
VBlank, and the harness delivers a VBlank exactly where the program waits, so the two run
to the same clock and the comparison is call for call at the same VBlank number.

The fades are set to 0 VBlanks a step on both sides: the harness's fades take no time
because they contain no wait, and the port's provisional two VBlanks a step are a setting,
not a fact about the original (SPEC 10, point 6).
"""
import json
import os
import random
import sys

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
RUNS = os.path.join(HERE, 'runs')
sys.path.insert(0, os.path.join(ROOT, 'tools'))
sys.path.insert(0, HERE)

import headless                    # noqa: E402
from conftest import WOF_TRACE_TEXT  # noqa: E402

# The drawing routines the harness can watch by name, and what the port calls them.  The
# original's C routines are observed with their stack arguments; the port records the same
# numbers in the same order (src/trace.c).
OBSERVE = ['os_gfx_move', 'os_gfx_set_apen', 'os_gfx_rect_fill', 'text_draw',
           'text_draw_justified', 'shape_draw_c', 'shape_draw_xor_c', 'os_gfx_text']

# The executable's own two hunks.  A string that lies in them is the same at the end of the
# run as it was when it was drawn; a string on the stack - what sprintf("%d") leaves behind
# in the briefing and in the high-score list - is not, because the harness's memory is read
# when the run is over.  Where it is not, only the length is compared.
EXECUTABLE = range(0x010000, 0x028004)


def headless_run(name, until=None, **options):
    with open(os.path.join(RUNS, name + '.json')) as f:
        description = json.load(f)
    description.update(options.pop('description', {}))
    machine = headless.Headless(description, **options)
    machine.run(until=until)
    return machine


def replay(ported, machine, fade_vblanks=0, stop_at_mission=False, stop_at=None):
    """The harness's schedule through the port: its keys, its raw state, one pass each.

    With stop_at_mission the replay ends where the port's front end does, which is where
    the original reaches mission_display_setup.  That is the moment the two are compared
    at: everything after it is the mission, which M4 ports and which the port here stands
    in for with an immediate end."""
    keys = {}
    for vblank, code, qualifier in machine.key_log:
        keys.setdefault(vblank, []).append((code, qualifier))

    ported.reset_core(fade_vblanks=fade_vblanks)
    vblank = 0
    for event in machine.schedule:
        if event[0] != 'V':
            continue
        vblank += 1
        for code, qualifier in keys.get(vblank, ()):
            ported.key(code, qualifier)
        ported.vblank(event[1])
        ported.pass_()
        if stop_at_mission and ported.mission_count():
            break
        if stop_at is not None and vblank >= stop_at:
            break
    return vblank


def port_music(ported):
    return [(ported.music_vblank(i), ported.music_song(i))
            for i in range(ported.music_count())]


def original_music(machine):
    """music_start calls the player twice: ReadInstruments, then PlaySong with the number.
    Command 2 is the one that names the song (re/notes/frontend.md)."""
    return [(call[4], call[2]) for call in machine.player_calls
            if call[0] == 'songplay' and call[1] == 2]


@pytest.fixture(scope='module')
def idle():
    return headless_run('front-end-idle')


@pytest.fixture(scope='module')
def fire():
    return headless_run('front-end-fire')


# ------------------------------------------------------------------ the timetable

@pytest.mark.parametrize('run_name', ['front-end-idle', 'front-end-fire'])
def test_the_music_calls_fall_on_the_same_vblanks(ported, run_name):
    """Which song, at which VBlank.  The player is M8; the port records the call and plays
    nothing, which is what the harness does with it too."""
    machine = headless_run(run_name)
    replay(ported, machine)
    want = original_music(machine)
    got = port_music(ported)
    assert got[:len(want)] == want, 'port %s, original %s' % (got[:6], want[:6])


@pytest.mark.parametrize('run_name', ['front-end-idle', 'front-end-fire'])
def test_the_front_end_opens_the_same_files_at_the_same_vblanks(ported, run_name):
    """Every file the port's front end opens, the original opened at the same VBlank, and
    the four pictures of re/notes/frontend.md are among them.

    Two things are left out and both are M1's doing, not M3's.  The permanent shape
    containers, the game font and the four palettes are loaded once by wof_init, where the
    original loads them from init_assets and per screen (re/notes/porting-m1.md); they show
    in the port's log at VBlank 0 and are excluded by name.  Everything the original opens
    for the mission itself - the map, the dashboard picture, the sounds - belongs to M4,
    where the mission is a stand-in here, so the port opening fewer files than the original
    is expected and only the other direction is a failure."""
    machine = headless_run(run_name)
    replay(ported, machine, stop_at_mission=True)

    startup = {name for vblank, name, found in ported.file_log() if vblank == 0}
    want = [(v, name) for v, call, name, found in machine.files_at
            if call == 'Open' and found and v > 0 and name not in startup]
    got = [(v, name) for v, name, found in ported.file_log()
           if found and v > 0 and name not in startup]

    assert got, 'the port opened nothing at all'
    rest = list(want)
    for item in got:
        assert item in rest, 'the port opened %r; the original did not, or not then' % (item,)
        rest = rest[rest.index(item) + 1:]          # in order, and each one only once

    pictures = [name for _, name in got]
    for name in ('shapes/broderbund', 'shapes/selectrank'):
        assert name in pictures, '%s was never loaded: %s' % (name, pictures)


@pytest.mark.parametrize('run_name, mission_at', [
    ('front-end-idle', 6923),       # left alone, the front end takes this long
    ('front-end-fire', 130),        # with the five taps of fire the tests use
])
def test_the_mission_begins_at_the_same_vblank(ported, run_name, mission_at):
    """Where the original reaches mission_display_setup, the port reaches the mission
    stand-in.  The harness's own observer says where that is; the numbers in the parameters
    are only there so that a change shows up as a change."""
    machine = headless_run(run_name, observe=['mission_display_setup'])
    replay(ported, machine)

    want = [o['vblank'] for o in machine.observed if o['routine'] == 'mission_display_setup']
    got = [r['vblank'] for r in ported.traces('mission')]
    assert want, 'the run never reached a mission'
    assert want[0] == mission_at, 'the original now reaches the mission at %d' % want[0]
    assert got and got[0] == want[0], 'port %s, original %s' % (got[:3], want[:3])


def test_the_rank_the_briefing_was_reached_with_is_the_same(ported):
    """Return on the second entry of the rank selection: the cursor, the rank the run is
    played at and the rank the high-score entry would be written with."""
    machine = headless_run('rank-return', until='inner')
    replay(ported, machine, stop_at_mission=True)
    for name, address in (('rank_cursor', 0x026C64), ('rank_played', 0x0253BE),
                          ('rank_chosen', 0x025558)):
        assert ported.g_at_mission(name) == machine.o.r16(address), name


@pytest.mark.parametrize('run_name', ['rank-cursor-down', 'rank-cursor-up', 'rank-no-key'])
def test_the_rank_cursor_ends_where_the_original_leaves_it(ported, run_name):
    """These three runs stop inside the rank selection and never reach a mission, so both
    sides are read where they stand at the end of the run."""
    machine = headless_run(run_name)
    replay(ported, machine)
    assert ported.mission_count() == 0, 'the run was meant to stop in the rank selection'
    assert ported.g('rank_cursor') == machine.o.r16(0x026C64)


def test_control_r_in_the_briefing_sends_both_back_to_the_rank_selection(ported):
    """The key run and its negative control: with the key the rank selection is set up a
    second time, without it once (re/notes/keys.md)."""
    def selectrank_loads(machine, port):
        replay(port, machine)
        return len([1 for _, name, found in port.file_log()
                    if name == 'shapes/selectrank' and found])

    pressed = selectrank_loads(headless_run('briefing-control-r'), ported)
    quiet = selectrank_loads(headless_run('briefing-no-key'), ported)
    assert pressed == 2, 'Control-R did not send the port back to the rank selection'
    assert quiet == 1


def test_the_key_buffer_and_the_latches_end_where_the_original_leaves_them(ported):
    """SPEC 8: the state the front end hands on.  The press that ends the briefing is
    sampled after the queue is cleared, so the first tick of a mission can carry the tap
    bit (re/notes/input.md); these are the words that carry it."""
    machine = headless_run('front-end-fire', until='inner')
    replay(ported, machine, stop_at_mission=True)
    for name, address, width in (('key_count', 0x026CB6, 2), ('demo_mode', 0x026D4C, 2),
                                 ('fire_prev_state', 0x026C8C, 2),
                                 ('fire_tap_latch', 0x027DFC, 2),
                                 ('fire_hold_latch', 0x027DFA, 2),
                                 ('opt_invert_vertical', 0x0254F6, 1),
                                 ('opt_music_off', 0x0254F7, 1)):
        want = machine.o.r16(address) if width == 2 else machine.o.read(address, 1)[0]
        got = ported.g_at_mission(name)
        assert got == want, '%s: port %d, original %d' % (name, got, want)


# ------------------------------------------------------------------ the drawing calls

def cstring(machine, address, limit=64):
    """A NUL-terminated string out of the emulated memory, wherever it lies."""
    out = bytearray()
    while len(out) < limit:
        byte = machine.o.read(address + len(out), 1)[0]
        if byte == 0:
            break
        out.append(byte)
    return out.decode('latin1')


def signed(value):
    """A long as the original's C code reads it: the harness records the register."""
    return value - 0x100000000 if value >= 0x80000000 else value


def text_at(machine, address):
    """The string, where it is one that outlives the run; None where it was on the stack.
    Cut to what the port's own record keeps of it (src/wof.h, WOF_TRACE_TEXT)."""
    if address not in EXECUTABLE:
        return None
    return cstring(machine, address)[:WOF_TRACE_TEXT - 1]


def original_draws(machine):
    """What the harness's observers recorded, in the port's own shape.  A C routine's
    arguments are the longs and words above the return address (re/notes/headless.md); which
    of the two a routine takes follows from how its caller pushes them."""
    out = []
    for o in machine.observed:
        routine, args, words = o['routine'], o['args'], o['words']
        if routine == 'os_gfx_move':
            out.append((o['vblank'], 'os_gfx_move', signed(args[1]), signed(args[2]), 0, 0, ''))
        elif routine == 'os_gfx_set_apen':
            out.append((o['vblank'], 'os_gfx_set_apen', signed(args[1]), 0, 0, 0, ''))
        elif routine == 'os_gfx_rect_fill':
            out.append((o['vblank'], 'os_gfx_rectfill', signed(args[1]), signed(args[2]),
                        signed(args[3]), signed(args[4]), ''))
        elif routine == 'text_draw':
            out.append((o['vblank'], 'text_draw_c', signed(args[1]), 0, 0, 0,
                        text_at(machine, args[0])))
        elif routine == 'text_draw_justified':
            out.append((o['vblank'], 'text_draw_just', signed(args[1]), signed(args[2]), 0, 0,
                        text_at(machine, args[0])))
        elif routine == 'shape_draw_c':
            out.append((o['vblank'], 'shape_draw_c', words[4], words[5], 0, 0, ''))
        elif routine == 'shape_draw_xor_c':
            out.append((o['vblank'], 'shape_xor_c', words[2], words[3], 0, 0, ''))
    return out


def port_draws(ported, keep):
    out = []
    for r in ported.traces():
        if r['what'] not in keep:
            continue
        if r['what'] in ('shape_draw_c', 'shape_xor_c'):
            out.append((r['vblank'], r['what'], r['a'], r['b'], 0, 0, ''))
        elif r['what'] == 'text_draw_c':
            out.append((r['vblank'], r['what'], r['a'], 0, 0, 0, r['text']))
        elif r['what'] == 'text_draw_just':
            out.append((r['vblank'], r['what'], r['a'], r['b'], 0, 0, r['text']))
        elif r['what'] == 'os_gfx_set_apen':
            out.append((r['vblank'], r['what'], r['a'], 0, 0, 0, ''))
        elif r['what'] == 'os_gfx_move':
            out.append((r['vblank'], r['what'], r['a'], r['b'], 0, 0, ''))
        else:
            out.append((r['vblank'], r['what'], r['a'], r['b'], r['c'], r['d'], ''))
    return out


@pytest.mark.parametrize('run_name', ['front-end-idle', 'front-end-fire'])
def test_the_front_end_draws_the_same_calls_at_the_same_vblanks(ported, run_name):
    """Every drawing call the front end makes, with its position, its text and the VBlank it
    was made at, against the same run of the original with observers on the same routines.

    This is what "layout" rests on, together with the owner's eyes: the harness draws
    nothing at all, so what a screen *looks* like is not observable there.  What is
    observable is which routine was called, where the pen was and what string went through
    it, and that is what this compares.  The pens and the draw mode are not in the
    comparison because the harness's RastPort is the port's own stand-in for one; they are
    checked against the original's own initialisation in
    test_the_briefing_draws_its_text_in_the_pen_initrastport_left."""
    machine = headless_run(run_name, observe=OBSERVE)
    replay(ported, machine, stop_at_mission=True)

    want = original_draws(machine)
    got = port_draws(ported, {'os_gfx_move', 'os_gfx_set_apen', 'os_gfx_rectfill',
                              'text_draw_c', 'text_draw_just', 'shape_draw_c',
                              'shape_xor_c'})
    end = max(r['vblank'] for r in ported.traces('mission'))
    want = [row for row in want if row[0] <= end]

    assert got, 'the port drew nothing'
    assert len(got) == len(want), (
        'port made %d drawing calls, the original %d\nfirst port %s\nfirst orig %s'
        % (len(got), len(want), got[:4], want[:4]))
    for a, b in zip(got, want):
        if b[6] is None:                    # a string that was on the stack: length only
            assert a[:6] == b[:6], 'port %s\noriginal %s' % (a, b)
        else:
            assert a == b, 'port %s\noriginal %s' % (a, b)


def briefing_vblank(machine):
    marks = [o['vblank'] for o in machine.observed if o['routine'] == 'mission_briefing']
    assert marks, 'the run never reached the briefing'
    return marks[0]


def test_the_briefing_draws_its_text_in_the_pen_initrastport_left(ported):
    """The open point M1 left (re/notes/porting-m1.md): what BltTemplate and graphics.Text
    do with a template depends on the RastPort the front end set up, and the briefing sets
    no pen at all.  InitRastPort leaves the foreground pen at 0xFF and the draw mode at
    JAM2, and draw_set_target ANDs the pen with the depth mask, so on three planes the
    briefing's text is colour 7 on a background of colour 0.

    The screen is looked at while the briefing is still up: the outer loop runs on into the
    next rank selection in the same pass the mission stand-in ends in."""
    machine = headless_run('front-end-fire', observe=['mission_briefing'])
    replay(ported, machine, stop_at=briefing_vblank(machine) + 10)

    assert ported.vport('depth') == 3, 'the briefing screen is 640 x 147 with three planes'
    assert ported.vport('width') == 640 and ported.vport('height') == 147
    assert ported.vport('apen', back=True) == 0xFF, 'a pen was set the original does not set'
    assert ported.vport('bpen', back=True) == 0
    assert ported.vport('drmd', back=True) == 1, 'InitRastPort leaves JAM2'


# ----------------------------------------------- the high-score file (re/notes/highscore.md)

HIGH_SCORE_LOAD, HIGH_SCORE_SORT, HIGH_SCORE_SAVE = 0x0193CC, 0x019320, 0x019288
HIGH_SCORE_TABLE = 0x027DDA
SCRATCH = 0x0D9000                 # free memory in the harness's record area
TEXT_INPUT = 0x016086
DRAW_RASTPORT = 0x026F1A
PATH_SANITISE = 0x016592
DISK = os.path.join(ROOT, 'original', 'disk', 'Wings_of_Fury')


@pytest.fixture(scope='module')
def machine():
    """One headless machine with the game initialised, for the routines that need the
    operating system: the high-score file goes through dos, and the line editor converts
    keys with the ROM's own RawKeyConvert."""
    run = headless_run('front-end-fire', until='inner')
    run.o.w32(HIGH_SCORE_TABLE, SCRATCH)
    return run


def original_table(m):
    return m.o.read(SCRATCH, 360)


def put_original_table(m, data):
    m.o.write(SCRATCH, data)


def random_table(rng):
    """Ten entries of a u32 score, a u16 rank and a 30-byte NUL-padded name."""
    out = bytearray()
    for _ in range(10):
        name = bytes(rng.choice(b'abcdefgh ') for _ in range(rng.randrange(0, 17)))
        out += rng.randrange(0, 40000).to_bytes(4, 'big')
        out += rng.randrange(0, 7).to_bytes(2, 'big')
        out += name.ljust(30, b'\x00')
    return bytes(out)


def test_the_port_reads_the_disks_high_score_file_byte_for_byte(ported, machine):
    """The original's own reader on the disk's own file, and the port's beside it."""
    ported.reset_core()
    ported.hs_load()
    machine.nested(HIGH_SCORE_LOAD, {'a4': headless.A4})
    with open(os.path.join(DISK, 'highscore'), 'rb') as f:
        disk = f.read()
    assert original_table(machine) == disk
    assert ported.hs_table() == disk


@pytest.mark.parametrize('seed', range(6))
def test_the_sort_agrees_with_the_original_on_random_tables(ported, machine, seed):
    """Randomised inputs, results and touched memory compared (SPEC 7.4).  The whole
    36-byte entry travels with its score, which is what puts a name beside it."""
    rng = random.Random(seed)
    table = random_table(rng)

    put_original_table(machine, table)
    machine.nested(HIGH_SCORE_SORT, {'a4': headless.A4})
    ported.set_hs_table(table)
    ported.hs_sort()
    assert ported.hs_table() == original_table(machine)


def test_what_the_port_writes_is_what_the_original_writes(ported, machine):
    """The same table, the same 360 bytes on the way out."""
    rng = random.Random(99)
    table = random_table(rng)

    put_original_table(machine, table)
    machine.nested(HIGH_SCORE_SAVE, {'a4': headless.A4})
    ported.fs_reset()
    ported.set_hs_table(table)
    ported.hs_save()

    written = dict(ported.fs_written())
    assert list(written) == ['highscore']
    assert written['highscore'] == machine.overlay['highscore'] == table


def test_without_the_file_the_table_is_ten_empty_entries(ported, machine):
    """What the clear command leaves behind: score 0, rank 0, a name of twelve spaces."""
    ported.reset_core()
    assert ported.fs_delete('highscore'), 'the disk has no high-score file to delete'
    ported.hs_load()

    saved = machine.overlay.pop('highscore', None)
    machine.deleted.add('highscore')
    try:
        machine.nested(HIGH_SCORE_LOAD, {'a4': headless.A4})
        assert ported.hs_table() == original_table(machine)
        assert ported.hs_table() == (bytes(6) + b' ' * 12 + bytes(18)) * 10
    finally:
        machine.deleted.discard('highscore')
        if saved is not None:
            machine.overlay['highscore'] = saved
    ported.reset_core()


def test_a_score_equal_to_the_tenth_does_not_get_in(ported):
    """The comparison is `>` against entry 9 (re/notes/highscore.md), so a tie is out."""
    ported.reset_core()
    ported.hs_load()
    tenth = int.from_bytes(ported.hs_table()[9 * 36:9 * 36 + 4], 'big')

    ported.dev_set_score(tenth)
    before = ported.hs_table()
    ported.fs_reset()
    ported.hs_entry_run()
    assert ported.fs_written() == [], 'an equal score was written into the table'
    assert ported.hs_table() == before

    ported.dev_set_score(tenth + 1)
    ported.fs_reset()
    ported.hs_entry_run()
    assert [name for name, _ in ported.fs_written()] == ['highscore']


def test_a_name_of_sixteen_characters_reaches_the_file(ported):
    """text_input is called with a maximum of 16, and the entry is copied with strncpy over
    17 bytes into a 30-byte field (re/notes/frontend.md, re/notes/highscore.md)."""
    ported.reset_core()
    ported.hs_load()
    ported.dev_set_score(1000000)
    ported.fs_reset()

    letters = 'abcdefghijklmnopqrst'                 # twenty: four more than fit
    keys = [(0x20 + i % 9, 0) for i in range(len(letters))] + [(0x44, 0)]
    ported.hs_entry_run(keys)

    written = dict(ported.fs_written())
    assert list(written) == ['highscore']
    name = written['highscore'][6:36].split(b'\x00')[0]
    assert len(name) == 16, 'the entry took %d characters' % len(name)
    assert written['highscore'][6 + 16:36] == bytes(14), 'the rest of the field is not NUL'
    assert int.from_bytes(written['highscore'][:4], 'big') == 1000000
    assert int.from_bytes(written['highscore'][4:6], 'big') == ported.g('rank_played')


# ------------------------------------------------ the line editor (re/notes/keys.md)

def original_text_input(machine, text, keys, max_length=16):
    """The original's own text_input, on a RastPort of the harness's.  It converts its keys
    with the ROM's RawKeyConvert, so this is the whole reader, not a model of it.  The key
    buffer is ten deep, so a case here uses at most ten keys including the one that ends
    it."""
    buffer, rastport = SCRATCH + 0x400, SCRATCH + 0x500

    machine.o.write(rastport, bytes(100))
    machine.o.w32(DRAW_RASTPORT, rastport)
    machine.o.write(buffer, text.encode('latin1').ljust(max_length + 8, b'\x00'))
    machine.o.w16(0x026CB6, 0)                       # key_count: an empty buffer
    for code, qualifier in keys:
        machine.key_event(code, qualifier)

    args = (headless.struct.pack('>I', buffer) + headless.struct.pack('>h', max_length)
            + headless.struct.pack('>hhh', 0, 0, 10000))
    out = machine.nested(TEXT_INPUT, {'a4': headless.A4}, args=args)
    result = out[0] & 0xFFFF
    if result >= 0x8000:
        result -= 0x10000
    return result, machine.o.read(buffer, max_length + 8).split(b'\x00')[0].decode('latin1')


# Raw codes by position: the letters of the home row, and the editing keys of the note.
KEY_A, KEY_S, KEY_D, KEY_F = 0x20, 0x21, 0x22, 0x23
RETURN, KEYPAD_ENTER, BACKSPACE, DELETE = 0x44, 0x43, 0x41, 0x46
LEFT, RIGHT, UP, DOWN = 0x4F, 0x4E, 0x4C, 0x4D
KEY_X = 0x32
LSHIFT, RAMIGA = 0x0001, 0x0080


@pytest.mark.parametrize('start, keys', [
    ('', [(KEY_A, 0), (KEY_S, 0), (KEY_D, 0), (RETURN, 0)]),
    ('', [(KEY_A, LSHIFT), (KEY_S, 0), (RETURN, 0)]),
    ('abc', [(BACKSPACE, 0), (RETURN, 0)]),
    ('abc', [(RIGHT, 0), (RIGHT, 0), (BACKSPACE, 0), (RETURN, 0)]),
    ('abc', [(DELETE, 0), (RETURN, 0)]),
    ('abc', [(RIGHT, 0), (DELETE, 0), (RETURN, 0)]),
    ('abc', [(RIGHT, 0), (RIGHT, 0), (KEY_F, 0), (RETURN, 0)]),
    ('abc', [(RIGHT, LSHIFT), (KEY_F, 0), (RETURN, 0)]),
    ('abc', [(RIGHT, 0), (RIGHT, 0), (LEFT, LSHIFT), (KEY_F, 0), (RETURN, 0)]),
    ('abc', [(KEY_X, RAMIGA), (KEY_D, 0), (RETURN, 0)]),
    ('abc', [(UP, 0)]),
    ('abc', [(DOWN, 0)]),
    ('abc', [(KEYPAD_ENTER, 0)]),
    ('abcdefgh', [(DELETE, 0), (DELETE, 0), (KEY_A, 0), (RETURN, 0)]),
    ('', [(LEFT, 0), (LEFT, 0), (KEY_A, 0), (RETURN, 0)]),
    ('', [(BACKSPACE, 0), (DELETE, 0), (KEY_S, 0), (RETURN, 0)]),
])
def test_the_line_editor_agrees_with_the_original(ported, machine, start, keys):
    """Every editing operation of re/notes/keys.md, and the two that are in the code and in
    no note: a cursor key with Shift jumps to the start or the end of the line, and right
    Amiga with X clears it."""
    want = original_text_input(machine, start, keys)
    got = ported.text_input(start, keys)
    assert got == want, 'port %r, original %r' % (got, want)


@pytest.mark.parametrize('seed', range(8))
def test_random_key_sequences_edit_the_same_line(ported, machine, seed):
    """Randomised inputs, results and the line compared (SPEC 7.4)."""
    rng = random.Random(seed)
    pool = [KEY_A, KEY_S, KEY_D, KEY_F, BACKSPACE, DELETE, LEFT, RIGHT, KEY_X]
    quals = [0, 0, 0, LSHIFT, RAMIGA]

    for _ in range(6):
        start = ''.join(rng.choice('asdf') for _ in range(rng.randrange(0, 6)))
        keys = [(rng.choice(pool), rng.choice(quals)) for _ in range(rng.randrange(1, 9))]
        keys.append((RETURN, 0))
        want = original_text_input(machine, start, keys)
        got = ported.text_input(start, keys)
        assert got == want, 'start %r keys %s: port %r, original %r' % (start, keys, got, want)


def test_a_line_is_never_longer_than_the_maximum(ported, machine):
    keys = [(KEY_A, 0)] * 9 + [(RETURN, 0)]
    for maximum in (4, 8):
        want = original_text_input(machine, '', keys, max_length=maximum)
        got = ported.text_input('', keys, max_length=maximum)
        assert got == want and len(got[1]) == maximum, (maximum, got, want)


# ------------------------------------------------------------- path_sanitise (0x016592)

@pytest.mark.parametrize('name', ['plain', 'df0:name', 'a/b/c', ':/:/', '', 'x:y/z ', 'wof.a'])
def test_path_sanitise_agrees_with_the_original(ported, machine, name):
    """A ':' or a '/' becomes a space, so that a typed name cannot name a device."""
    at = SCRATCH + 0x600

    machine.o.write(at, name.encode('latin1') + b'\x00')
    machine.nested(PATH_SANITISE, {'a4': headless.A4},
                   args=headless.struct.pack('>I', at))
    want = machine.o.read(at, len(name) + 1).split(b'\x00')[0].decode('latin1')
    assert ported.path_sanitise(name) == want


# ---------------------------------------------- the load and save dialog (frontend.md)

import headless_os                                                   # noqa: E402


def test_the_directory_comes_out_in_the_file_systems_own_order(ported):
    """ExNext walks chain 0 upward and inside a chain from its head, and the order follows
    from the names alone (re/notes/frontend.md, "The order of the file list").  The port's
    own hash has to put the same names in the same chains as the harness's, which reads the
    disk image."""
    ported.reset_core()
    ported.fs_reset()
    assert ported.dir_entries() == ['wof.mission 3'], 'the disk brings exactly one saved game'

    names = ['wof.amission 3', 'wof.zz', 'wof.a', 'wof.b']
    for name in names:
        assert ported.fs_write(name, b'x' * 16)

    got = ported.dir_entries()
    assert sorted(got) == sorted(names + ['wof.mission 3'])
    chains = [headless_os.name_hash(name) for name in got]
    assert chains == sorted(chains), 'the list is not in chain order: %s' % list(zip(got, chains))

    ported.reset_core()
    ported.fs_reset()


def test_two_names_in_one_chain_come_newest_first(ported):
    """Which only matters when two saved games share a chain, and the harness puts a new
    entry at the head of its own chain, where a real file system puts it."""
    ported.reset_core()
    ported.fs_reset()

    same = [name for name in ('wof.a', 'wof.b', 'wof.c', 'wof.d', 'wof.e', 'wof.f', 'wof.g',
                              'wof.h', 'wof.i', 'wof.j')
            if headless_os.name_hash(name) == headless_os.name_hash('wof.a')]
    assert len(same) >= 1
    ported.fs_write('wof.a', b'x' * 16)
    ported.fs_write('wof.aa', b'x' * 16)
    order = [name for name in ported.dir_entries() if name in ('wof.a', 'wof.aa')]
    if headless_os.name_hash('wof.a') == headless_os.name_hash('wof.aa'):
        assert order == ['wof.aa', 'wof.a'], 'the newer file is not at the head of its chain'
    ported.reset_core()
    ported.fs_reset()


def test_a_save_through_the_dialog_renames_the_file_it_was_edited_from(ported):
    """Observed under the harness (re/notes/frontend.md): saving over a slot that already
    held a name writes the new file and deletes the old one, so editing a name renames the
    save.  The slot the disk's own `wof.mission 3` fills is edited to `amission 3`, which
    is the same edit the harness's dialog-save run makes."""
    ported.reset_core()
    ported.fs_reset()

    result, rounds = ported.dialog_run(1, [(KEY_A, 0), (RETURN, 0)])
    assert result == 0, 'the dialog did not save'
    assert ported.dialog_names()[0] == 'amission 3'

    written = [name for name, _ in ported.fs_written()]
    assert written == ['wof.amission 3'], written
    assert ported.dir_entries() == ['wof.amission 3'], (
        'the file the name was edited from is still in the directory')
    ported.reset_core()
    ported.fs_reset()


def test_the_load_dialog_lists_the_saved_games_and_comes_back_when_cancelled(ported):
    """In load mode the cursor skips the empty slots, so two moves from the one filled slot
    reach Cancel.  A cancel is -1, which is what sends the rank selection back to its menu."""
    ported.reset_core()
    ported.fs_reset()

    result, rounds = ported.dialog_run(0, [(DOWN, 0), (DOWN, 0), (RETURN, 0)])
    assert ported.dialog_names()[0] == 'mission 3'
    assert ported.dialog_names()[1:] == [''] * 5
    assert result == -1, 'a cancel must not read as a loaded game'
    assert ported.fs_written() == [], 'the load dialog wrote something'
    ported.reset_core()
    ported.fs_reset()


def test_the_dialog_with_nothing_to_load_starts_on_cancel(ported):
    """With no saved game at all the cursor cannot sit on a slot, so the dialog opens on
    the Cancel button (load_save_dialog 0x018DF0)."""
    ported.reset_core()
    ported.fs_reset()
    assert ported.fs_delete('wof.mission 3')

    result, rounds = ported.dialog_run(0, [(RETURN, 0)])
    assert result == -1
    assert ported.dialog_names() == [''] * 6
    ported.reset_core()
    ported.fs_reset()


# ------------------------------------------ what the front end draws with graphics.Draw

def test_every_draw_the_front_end_makes_is_parallel_to_an_axis(ported):
    """SPEC 10, point 7 leaves the pixel pattern of the blitter's line mode open, and
    graphics.Draw would need it for a sloped line.  It is not needed: every Draw the front
    end makes is a side of one of the load and save dialog's eight boxes or of the name
    entry's frame, and each of those is parallel to an axis.  This watches the original
    make them, in both modes of the dialog and in the name entry, rather than reading the
    tables and trusting them."""
    seen = 0
    for run_name in ('dialog-load', 'dialog-save'):
        machine = headless_run(run_name, observe=['os_gfx_move', 'os_gfx_draw'])
        pen = None
        for o in machine.observed:
            if o['routine'] == 'os_gfx_move':
                pen = (signed(o['args'][1]), signed(o['args'][2]))
                continue
            to = (signed(o['args'][1]), signed(o['args'][2]))
            assert pen is not None, 'a Draw with no Move before it'
            assert pen[0] == to[0] or pen[1] == to[1], (
                '%s: a sloped Draw from %s to %s' % (run_name, pen, to))
            pen = to
            seen += 1
    assert seen >= 8 * 4, 'only %d Draw calls were seen; the dialog alone makes 32' % seen


def test_the_port_draws_the_same_boxes_as_the_original(ported):
    """The eight boxes of the dialog, as the original's own table gives them, against the
    port's.  The dialog is driven on both sides, so this is the whole routine and not the
    table alone."""
    machine = headless_run('dialog-load', observe=['os_gfx_move', 'os_gfx_draw'])
    want = []
    pen = None
    for o in machine.observed:
        if o['routine'] == 'os_gfx_move':
            pen = (signed(o['args'][1]), signed(o['args'][2]))
        else:
            to = (signed(o['args'][1]), signed(o['args'][2]))
            want.append((pen, to))
            pen = to

    ported.reset_core()
    ported.fs_reset()
    ported.dialog_run(0, [(DOWN, 0), (DOWN, 0), (RETURN, 0)])

    got = []
    pen = None
    for r in ported.traces():
        if r['what'] == 'os_gfx_move':
            pen = (r['a'], r['b'])
        elif r['what'] == 'os_gfx_draw':
            got.append(((r['a'], r['b']), (r['c'], r['d'])))
            pen = (r['c'], r['d'])

    assert got[:len(want)] == want, 'port %s\noriginal %s' % (got[:4], want[:4])
    ported.reset_core()
    ported.fs_reset()
