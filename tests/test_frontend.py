"""M3's groundwork: the key commands, the front-end screens, the high-score file, the dialog.

Every finding of re/notes/keys.md, re/notes/frontend.md and re/notes/highscore.md that can be
observed is observed here, under the headless original (re/notes/headless.md).  A key command is
checked twice: once with the key and once without it, so that the effect belongs to the key.

The run descriptions live in tests/runs/ and hold no game data: they are the player's hands,
VBlank by VBlank.
"""
import json
import os
import re
import struct
import subprocess
import sys

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
RUNS = os.path.join(HERE, 'runs')
sys.path.insert(0, os.path.join(ROOT, 'tools'))

import headless                    # noqa: E402
import headless_os                 # noqa: E402

DISK = os.path.join(ROOT, 'original', 'disk', 'Wings_of_Fury')

# The addresses the tests watch, from re/names.txt.
OPT_INVERT_VERTICAL = 0x0254F6
OPT_MUSIC_OFF       = 0x0254F7
PLAYER_ON_DECK      = 0x025084
PAUSE_FLAG          = 0x025556
QUIT_FLAG           = 0x0253C2
END_OF_MISSION      = 0x0255C0
CHEAT_STATE         = 0x025F18
RANK_CURSOR         = 0x026C64
KEY_COUNT           = 0x026CB6
HIGH_SCORE_TABLE    = 0x027DDA
DIALOG_NAMES        = 0x027C7E
NAME_STRIDE         = 29

HIGH_SCORE_LOAD, HIGH_SCORE_SORT, HIGH_SCORE_SAVE = 0x0193CC, 0x019320, 0x019288
SCRATCH = 0x0D9000                 # free memory in the harness's record area


def run(name, **options):
    with open(os.path.join(RUNS, name + '.json')) as f:
        description = json.load(f)
    description.update(options.pop('description', {}))
    machine = headless.Headless(description, **options)
    machine.run()
    return machine


def byte(machine, address):
    return machine.o.read(address, 1)[0]


def dialog_names(machine):
    return [machine.o.read(DIALOG_NAMES + NAME_STRIDE * i, NAME_STRIDE).split(b'\0')[0].decode('latin1')
            for i in range(6)]


@pytest.fixture(scope='module')
def flight():
    """A mission reached with five taps of fire, no key pressed: the negative control."""
    return run('flight-no-key')


@pytest.fixture(scope='module')
def listing():
    """re/Wings.lst is not versioned (CLAUDE.md), so a fresh checkout makes it here once
    rather than skipping the one test that reads it.  tools/disasm.py takes about two
    seconds and is what the repository's own instructions say to run."""
    path = os.path.join(ROOT, 're', 'Wings.lst')
    if not os.path.isfile(path):
        subprocess.run([sys.executable, os.path.join(ROOT, 'tools', 'disasm.py')],
                       cwd=ROOT, check=True, capture_output=True)
    with open(path) as f:
        return f.read()


@pytest.fixture(scope='module')
def idle():
    """The whole front end with no input at all, up to the first mission.  Two routines are
    watched so that the briefing's own timing can be read off the same run."""
    return run('front-end-idle', observe=['mission_briefing', 'mission_display_setup'])


# ------------------------------------------------------------------ the harness's new parts

def test_a_key_may_carry_a_qualifier():
    assert headless.key_events([68, [0x13, 'ctrl'], [0x13, 8], [0x13, 'ctrl+lshift']]) == [
        (68, 0), (0x13, 8), (0x13, 8), (0x13, 9)]
    with pytest.raises(ValueError, match='unknown key qualifier'):
        headless.key_events([[0x13, 'meta']])


def test_the_rom_converts_raw_codes_as_the_game_expects(flight):
    """key_to_char goes through console.device RawKeyConvert, which the harness runs from the
    owner's Kickstart ROM.  A key that gives more than one character gives the game none."""
    machine, event, buffer = flight, headless.SCRATCH + 0x400, headless.SCRATCH + 0x500
    assert machine.rom_rawkeyconvert and machine.rom_keymap

    def convert(code, qualifier=0, length=4):
        machine.o.write(event, bytes(22))
        machine.o.write(event + 4, b'\x01')
        machine.o.w16(event + 6, code)
        machine.o.w16(event + 8, qualifier)
        machine.o.write(buffer, bytes(8))
        count = machine.nested(machine.rom_rawkeyconvert,
                               {'a0': event, 'a1': buffer, 'd1': length, 'a2': machine.rom_keymap, 'a6': 0})[0]
        return machine.o.read(buffer, count) if count < 0x8000 else count

    assert convert(0x13) == b'r'
    assert convert(0x13, 0x0001) == b'R'
    assert convert(0x13, 0x0008) == b'\x12'
    assert convert(0x45) == b'\x1b' and convert(0x44) == b'\r'
    assert convert(0x41) == b'\x08' and convert(0x46) == b'\x7f' and convert(0x40) == b' '
    assert len(convert(0x4C)) == 2 and len(convert(0x50)) == 3
    assert convert(0x4C, length=1) == 0xFFFFFFFF            # -1: it does not fit


def test_an_observer_does_not_change_a_run():
    plain = run('front-end-fire')
    watched = run('front-end-fire', observe=['text_render', 'text_draw_justified', 'os_gfx_text'])
    assert plain.step_hashes == watched.step_hashes
    assert plain.schedule == watched.schedule
    assert len(watched.observed) > 3 and not plain.observed


def test_the_disk_image_gives_the_order_the_file_system_hands_out():
    """ExNext walks chain 0 upward, and inside a chain from its head.  The name hash decides the
    chain, which every entry of five directory blocks of original/wof.adf confirms."""
    order = headless_os.adf_order([])
    assert [name for _, name in order] == [
        'Wings', 'wingt', '.info', 'shapes', 'wofsongs', 'wings.info', 'maps', 'sounds',
        'UFXintro', 'highscore', 'songplay', 'newarmyfont', 'rank.iff.info', 'wof.mission 3']
    assert all(headless_os.name_hash(name) == chain for chain, name in order)
    assert all(headless_os.name_hash(name) == chain
               for chain, name in headless_os.adf_order(['shapes']))
    assert set(name for _, name in order) <= set(os.listdir(DISK)), 'the disk image names a file that is not there'


# ------------------------------------------------------------------ the front end, screen by screen

def test_the_front_end_runs_to_the_same_timetable_twice():
    """The run that touches every screen: scroller, three pictures, rank selection, briefing."""
    first, again = run('front-end-fire'), run('front-end-fire')
    assert first.step_hashes == again.step_hashes and first.schedule == again.schedule


def test_the_front_end_loads_its_screens_in_order(idle):
    loads = [name for call, name, found in idle.files_log if call == 'Open' and found]
    pictures = [name for name in loads if name.startswith('shapes/') and not name.endswith('.shp')]
    assert pictures[:4] == ['shapes/broderbund', 'shapes/wingstitle', 'shapes/creditscreen',
                            'shapes/selectrank']
    assert 'shapes/selectrank.shp' in loads


def test_the_music_starts_where_the_screens_change(idle):
    """music_start(file, song) calls the player: ReadInstruments then PlaySong with the number."""
    plays = [(call[4], call[2]) for call in idle.player_calls
             if call[0] == 'songplay' and call[1] == 2]          # command 2 is PlaySong
    assert plays[:3] == [(1, 2), (3791, 1), (4876, 4)]           # scroller, pictures, rank selection


def test_the_story_scroller_reads_no_key():
    """Nothing in the title sequence drains the key buffer: a key pressed there is still
    waiting when the rank selection starts."""
    machine = run('scroller-key')
    assert machine.o.r16(KEY_COUNT) == 1, 'the key buffer was drained during the scroller'


def test_fire_skips_the_front_end(idle):
    """Left alone the front end takes about 6900 VBlanks; five taps of fire reach a mission in 132."""
    with_fire = run('front-end-fire')
    assert with_fire.missions == 1
    start = [event for event in with_fire.schedule[:with_fire.schedule.index(('S', 1))] if event[0] == 'V']
    assert len(start) == 132
    late = [event for event in idle.schedule[:idle.schedule.index(('S', 1))] if event[0] == 'V']
    assert len(late) > 6900, 'left alone the front end took %d VBlanks' % len(late)


# ------------------------------------------------------------------ rank selection

def test_the_rank_menu_moves_with_the_cursor_keys():
    down, up, nothing = run('rank-cursor-down'), run('rank-cursor-up'), run('rank-no-key')
    assert nothing.o.r16(RANK_CURSOR) == 0
    assert down.o.r16(RANK_CURSOR) == 1
    assert up.o.r16(RANK_CURSOR) == 7, 'the cursor wraps from 0 to the load dialog'


def test_return_chooses_the_rank():
    machine = run('rank-return')
    assert machine.missions == 1
    assert machine.o.r16(0x0253BE) == 1, 'the rank the mission started with'


# ------------------------------------------------------------------ the briefing

def test_the_briefing_draws_the_rank_and_three_numbers():
    machine = run('front-end-fire', observe=['os_gfx_move', 'text_draw_c', 'shape_draw_c'])
    calls = [(o['routine'], o['args'][1], o['args'][2]) for o in machine.observed]
    moves = [(x, y) for name, x, y in calls if name == 'os_gfx_move']
    assert moves[-3:] == [(340, 73), (340, 119), (340, 131)]
    shapes = [o for o in machine.observed if o['routine'] == 'shape_draw_c']
    assert (shapes[-1]['words'][4], shapes[-1]['words'][5]) == (192, 54)


def test_the_briefing_waits_240_vblanks(idle):
    """Without input the briefing ends by itself: 240 rounds of WaitTOF, plus the three VBlanks
    the screen and the fades cost before main reaches mission_display_setup."""
    marks = {o['routine']: o['vblank'] for o in idle.observed}
    assert marks['mission_display_setup'] - marks['mission_briefing'] == 243


def test_control_r_in_the_briefing_restarts():
    """It returns 1, and main goes back to the top of the outer loop: the rank selection is set
    up again, which shows as selectrank being loaded a second time."""
    with_key, without = run('briefing-control-r'), run('briefing-no-key')
    def ranks(machine):
        return [name for call, name, _ in machine.files_log if name == 'shapes/selectrank' and call == 'Open']
    assert len(ranks(with_key)) == 2
    assert len(ranks(without)) == 1


# ------------------------------------------------------------------ in flight

def test_control_f_flips_the_vertical_control(flight):
    """The command the owner needs.  Control and the F key toggle the byte read_joy_bits reads;
    the same key without Control does nothing."""
    flipped, plain, twice = run('flight-control-f'), run('flight-plain-f'), run('flight-control-f-twice')
    assert byte(flight, OPT_INVERT_VERTICAL) == 0
    assert byte(flipped, OPT_INVERT_VERTICAL) == 0xFF
    assert byte(plain, OPT_INVERT_VERTICAL) == 0, 'the F key alone flipped the control'
    assert byte(twice, OPT_INVERT_VERTICAL) == 0, 'the flip did not toggle back'


def test_the_control_key_may_come_as_its_own_event_too():
    """On a real keyboard the Control key is buffered as raw code 0x63 before the command key.
    It converts to nothing, so it changes nothing."""
    assert byte(run('flight-control-key-first'), OPT_INVERT_VERTICAL) == 0xFF


def test_the_flip_is_read_by_the_joystick_decoder_and_by_nothing_else(listing):
    """Two halves, and neither is the whole answer.

    Read: the listing annotates two accesses to opt_invert_vertical by name, a tst.b in
    read_joy_bits and a not.b in ingame_keys.  That finds only the accesses the disassembler
    could resolve to the address; it cannot find one made through a pointer, and the save game
    makes exactly such an access, which is why a loaded game does change the flip
    (test_a_restart_keeps_the_flip_and_a_loaded_game_undoes_it).

    Observed: over a flight in which the flip is pressed, the change report names ingame_keys
    as the one routine that wrote the byte, and no other."""
    touching = [line for line in listing.splitlines()
                if '; opt_invert_vertical' in line and re.match(r'^[0-9a-f]{6} ', line)]
    assert len(touching) == 2, touching
    assert 'tst.b' in touching[0] and touching[0].startswith('015238')
    assert 'not.b' in touching[1] and touching[1].startswith('01cd6e')
    flipped = run('flight-control-f', track_writes=True)
    wrote = [line for line in flipped.change_report if ' opt_invert_vertical ' in line]
    assert len(wrote) == 1 and wrote[0].strip().startswith('0254f6'), flipped.change_report
    assert wrote[0].endswith('by ingame_keys'), wrote[0]


def test_a_restart_keeps_the_flip_and_a_loaded_game_undoes_it(saved):
    """What M3 has to know for the owner's sake: Control-R leaves opt_invert_vertical alone,
    but loading a game saved with the flip off turns the flip off, because the flip is inside
    the range the save covers."""
    restarted = run('flight-flip-then-restart')
    assert byte(restarted, OPT_INVERT_VERTICAL) == 0xFF
    assert byte(restarted, OPT_MUSIC_OFF) == 0, 'the outer loop clears the music flag'
    loaded = run('flight-flip-then-load',
                 description={'files': {'wof.amission 3': saved.overlay['wof.amission 3'].hex()}})
    assert ('Open', 'wof.amission 3', True) in loaded.files_log
    assert byte(loaded, OPT_INVERT_VERTICAL) == 0, 'the loaded game did not carry its own flip in'


def test_control_s_toggles_the_music_flag(flight):
    assert byte(flight, OPT_MUSIC_OFF) == 0
    assert byte(run('flight-control-s'), OPT_MUSIC_OFF) == 0xFF


def test_escape_pauses_and_unpauses(flight):
    once, twice = run('flight-escape'), run('flight-escape-twice')
    assert byte(flight, PAUSE_FLAG) == 0
    assert byte(once, PAUSE_FLAG) == 0xFF
    assert byte(twice, PAUSE_FLAG) == 0, 'Escape read while paused did not unpause'
    assert once.ticks < flight.ticks, 'the paused run ran as many ticks as the free one'


def test_control_r_in_flight_restarts(flight):
    restarted = run('flight-control-r')
    assert (byte(flight, QUIT_FLAG), byte(flight, END_OF_MISSION)) == (0, 0)
    assert (byte(restarted, QUIT_FLAG), byte(restarted, END_OF_MISSION)) == (0xFF, 0xFF)


def test_control_c_deletes_the_high_score_file(flight):
    deleted = run('flight-control-c')
    assert ('DeleteFile', 'highscore', True) in deleted.files_log
    assert not any(call == 'DeleteFile' for call, _, _ in flight.files_log)


def test_the_cheat_sequence_unlocks_the_debug_keys(flight):
    assert flight.o.r16(CHEAT_STATE) == 0
    assert run('flight-cheat').o.r16(CHEAT_STATE) == 5


# ------------------------------------------------------------------ the commands while paused

def test_the_commands_work_while_the_game_is_paused():
    """ingame_keys runs from the head of the inner loop, before the pause test, and the pause
    loop comes back to that head, so every command is live while paused."""
    still, cleared, flipped = run('paused-no-key'), run('paused-control-c'), run('paused-control-f')
    assert byte(still, PAUSE_FLAG) == 0xFF and still.ticks == cleared.ticks == flipped.ticks
    assert not any(call == 'DeleteFile' for call, _, _ in still.files_log)
    assert ('DeleteFile', 'highscore', True) in cleared.files_log
    assert byte(cleared, PAUSE_FLAG) == 0xFF, 'the clear command unpaused the game'
    assert byte(still, OPT_INVERT_VERTICAL) == 0 and byte(flipped, OPT_INVERT_VERTICAL) == 0xFF
    assert byte(flipped, PAUSE_FLAG) == 0xFF


def test_a_restart_from_the_pause_starts_the_next_mission_unpaused():
    machine = run('paused-restart')
    assert machine.missions == 2
    assert byte(machine, PAUSE_FLAG) == 0, 'the new mission began paused'
    started = machine.schedule.index(('S', 2))
    assert any(event[0] == 'T' for event in machine.schedule[started:]), 'no tick after the restart'


# ------------------------------------------------------------------ the command the manual has and the code has not

@pytest.mark.parametrize('with_key, without', [
    ('flight-control-d', 'flight-no-key'),
    ('paused-control-d', 'paused-no-key'),
    ('rank-control-d', 'rank-no-key'),
    ('briefing-control-d', 'briefing-no-key'),
])
def test_control_d_does_nothing_anywhere(with_key, without):
    """The manual's Control-D shows the high scores; no reader of this executable tests it.
    In each of the four states where a key is read, the run with the key ends in the same
    state, with the same files log and the same schedule as the run without it.  The step
    hashes in between differ, because the key sits in the buffer for a step, which is why
    the final state is what is compared."""
    pressed, quiet = run(with_key), run(without)
    assert pressed.regions() == quiet.regions()
    assert pressed.files_log == quiet.files_log
    assert pressed.schedule == quiet.schedule


# ------------------------------------------------------------------ the load and save dialog

@pytest.fixture(scope='module')
def saved():
    """Control-G on the deck, one letter typed into the first slot, then Return."""
    return run('dialog-save')


def test_the_dialog_lists_the_saved_games_of_the_disk():
    machine = run('flight-control-l')
    assert ('Lock dir', '', True) in machine.files_log
    assert machine.os_calls['dos.ExNext'] == 15, 'fourteen entries and the end of the list'
    assert dialog_names(machine) == ['mission 3', '', '', '', '', '']


def test_the_save_dialog_only_opens_on_the_carrier(flight):
    """player_on_deck is 1 on the deck and 0 in the air, and Control-G tests it."""
    assert flight.o.r16(PLAYER_ON_DECK) == 1
    assert any(call == 'Lock dir' for call, _, _ in run('flight-control-g').files_log)
    assert not any(call == 'Lock dir' for call, _, _ in flight.files_log)


def test_a_save_writes_a_wof_file_and_replaces_the_one_it_was_edited_from(saved):
    assert list(saved.overlay) == ['wof.amission 3']
    assert len(saved.overlay['wof.amission 3']) == 4258
    assert ('DeleteFile', 'wof.mission 3', True) in saved.files_log


def test_a_saved_game_can_be_loaded_again(saved):
    """The dialog lists the new file first, because the file system puts a new entry at the head
    of its chain, and opens it when Return picks it."""
    machine = run('dialog-load',
                  description={'files': {'wof.amission 3': saved.overlay['wof.amission 3'].hex()}})
    assert dialog_names(machine)[:2] == ['amission 3', 'mission 3']
    assert ('Open', 'wof.amission 3', True) in machine.files_log


def test_two_runs_of_the_dialog_give_identical_dumps(saved):
    again = run('dialog-save')
    assert saved.step_hashes == again.step_hashes
    assert saved.overlay == again.overlay


# ------------------------------------------------------------------ the high-score file

@pytest.fixture(scope='module')
def scores(flight):
    """The original's own reader on the disk's file, into a buffer of the harness's."""
    flight.o.w32(HIGH_SCORE_TABLE, SCRATCH)
    flight.nested(HIGH_SCORE_LOAD, {'a4': headless.A4})
    return flight


def entry(machine, index):
    record = machine.o.read(SCRATCH + 36 * index, 36)
    return (struct.unpack('>I', record[:4])[0], struct.unpack('>H', record[4:6])[0],
            record[6:].split(b'\0')[0].decode('latin1'))


def test_the_file_is_ten_entries_of_thirty_six_bytes(scores):
    """The disk's own file, decoded here from the layout alone, and the original's reader put
    beside it: they agree entry for entry.  Nothing of the file's contents is written down."""
    with open(os.path.join(DISK, 'highscore'), 'rb') as f:
        disk = f.read()
    assert len(disk) == 360 == 10 * 36
    assert scores.o.read(SCRATCH, 360) == disk
    ranked = []
    for index in range(10):
        record = disk[36 * index:36 * (index + 1)]
        score, rank = struct.unpack('>IH', record[:6])
        text, rest = record[6:].split(b'\0', 1)
        assert (score, rank, text.decode('latin1')) == entry(scores, index)
        assert rank < 7, 'the rank word indexes rank_names, which holds seven names'
        assert len(text) <= 16, 'text_input is called with a maximum of 16'
        assert all(32 <= letter < 127 for letter in text)
        assert rest == bytes(len(rest)), 'the name is padded with zeros to 30 bytes'
        ranked.append(score)
    assert ranked == sorted(ranked, reverse=True), 'the file is not in the order the sort leaves'
    assert ranked[0] > 0 and ranked[-1] == 0


def test_reading_the_file_and_writing_it_back_gives_the_same_bytes(scores):
    scores.nested(HIGH_SCORE_SAVE, {'a4': headless.A4})
    with open(os.path.join(DISK, 'highscore'), 'rb') as f:
        assert scores.overlay['highscore'] == f.read()


def test_an_inserted_score_lands_where_the_layout_says(scores):
    """high_score_entry overwrites entry 9 and sorts.  A score one above the disk's fourth is
    put fourth, and the entry that was there moves down: the whole 36 bytes travel together."""
    before = [entry(scores, i) for i in range(10)]
    mine = before[3][0] + 1
    scores.o.w32(SCRATCH + 9 * 36, mine)
    scores.o.w16(SCRATCH + 9 * 36 + 4, 3)
    scores.o.write(SCRATCH + 9 * 36 + 6, b'tester' + bytes(24))
    scores.nested(HIGH_SCORE_SORT, {'a4': headless.A4})
    after = [entry(scores, i) for i in range(10)]
    assert after[3] == (mine, 3, 'tester')
    assert after[:3] == before[:3] and after[4:] == before[3:9]
    assert [row[0] for row in after] == sorted(row[0] for row in after)[::-1]


def test_without_the_file_the_table_is_ten_empty_entries(scores):
    """What the clear command leaves behind: high_score_load fills in a score of 0 and a name of
    twelve spaces, which is what entries 7 to 9 of the disk's own file hold."""
    saved_copy = scores.overlay.pop('highscore', None)
    scores.deleted.add('highscore')
    try:
        scores.nested(HIGH_SCORE_LOAD, {'a4': headless.A4})
        assert [entry(scores, i) for i in range(10)] == [(0, 0, ' ' * 12)] * 10
    finally:
        scores.deleted.discard('highscore')
        if saved_copy is not None:
            scores.overlay['highscore'] = saved_copy
