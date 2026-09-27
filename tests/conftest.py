"""Shared fixtures: build the port once, then hand the tests the artefacts.

    .venv/bin/python -m pytest tests/

The suite exercises the same C sources through both targets they have to compile for: the
WebAssembly core in Node (tests/wasm_harness.mjs) and the native shared library through
ctypes, which is the path every later milestone's oracle tests will use.
"""
import base64
import ctypes
import io
import json
import math
import pathlib
import re
import subprocess
import sys

import pytest

ROOT = pathlib.Path(__file__).resolve().parent.parent
PAGE = ROOT / 'dist' / 'wof.html'
WASM = ROOT / 'dist' / 'core.wasm'
DYLIB = ROOT / 'tests' / 'libwofcore.dylib'
HARNESS = ROOT / 'tests' / 'wasm_harness.mjs'

sys.path.insert(0, str(ROOT / 'tools'))
import build as buildtool  # noqa: E402


# The slowest differential tests - a script of many thousand VBlanks in both loops - carry
# the marker `slow` and run only when asked for, with --slow or WOF_SLOW=1:
#
#     .venv/bin/python -m pytest tests/                 the fast suite
#     .venv/bin/python -m pytest tests/ --slow          everything
def pytest_addoption(parser):
    parser.addoption('--slow', action='store_true', help='also run the tests marked slow')


def pytest_configure(config):
    config.addinivalue_line('markers', 'slow: a long differential run, only with --slow')


def pytest_collection_modifyitems(config, items):
    import os
    if config.getoption('--slow') or os.environ.get('WOF_SLOW') == '1':
        return
    skip = pytest.mark.skip(reason='slow; run with --slow or WOF_SLOW=1')
    for item in items:
        if 'slow' in item.keywords:
            item.add_marker(skip)


def run(command, **kwargs):
    return subprocess.run(command, cwd=ROOT, check=True, capture_output=True, text=True, **kwargs)


@pytest.fixture(scope='session')
def built():
    """dist/wof.html, dist/core.wasm and tests/libwofcore.dylib, from the real build."""
    run([sys.executable, 'tools/build.py', '--native', '--quiet'])
    assert PAGE.exists() and WASM.exists() and DYLIB.exists()
    return PAGE


@pytest.fixture(scope='session')
def page(built):
    return PAGE.read_text(encoding='utf-8')


def payload(page_text, element_id):
    found = re.search(r'<script id="%s" type="text/wof-base64">(.*?)</script>' % element_id,
                      page_text, re.S)
    assert found, 'payload %s missing from the page' % element_id
    return base64.b64decode(re.sub(r'\s+', '', found.group(1)))


@pytest.fixture(scope='session')
def blob(page):
    """The packed file system, taken out of the built page rather than rebuilt, so the tests
    see exactly the bytes the browser would."""
    return payload(page, 'wof-fs')


@pytest.fixture(scope='session')
def blob_file(blob, tmp_path_factory):
    path = tmp_path_factory.mktemp('wof') / 'fs.blob'
    path.write_bytes(blob)
    return path


@pytest.fixture(scope='session')
def wasm(built, blob_file):
    """Everything tests/wasm_harness.mjs measured, in one dict."""
    finished = run(['node', str(HARNESS), str(WASM), str(blob_file)])
    return json.loads(finished.stdout)


@pytest.fixture(scope='session')
def game_file_names():
    return buildtool.game_files()


class NativeCore:
    """The same core as a native library.  One process holds one copy of its statics, so a
    new NativeCore resets the arena and re-initialises; the previous one stops being valid."""

    def __init__(self, seed, blob=b''):
        self.lib = ctypes.CDLL(str(DYLIB))
        signatures = {
            'wof_init': ([ctypes.c_uint32, ctypes.c_void_p, ctypes.c_uint32], None),
            'wof_set_video_hz': ([ctypes.c_int], None),
            'wof_vblank': ([ctypes.c_uint8], None),
            'wof_pass': ([], None),
            'wof_framebuffer': ([], ctypes.c_void_p),
            'wof_palette_rows': ([], ctypes.c_void_p),
            'wof_palettes': ([], ctypes.c_void_p),
            'wof_display_list': ([ctypes.c_void_p], ctypes.c_void_p),
            'wof_audio_render': ([ctypes.c_void_p, ctypes.c_uint32, ctypes.c_uint32], ctypes.c_uint32),
            'wof_state_size': ([], ctypes.c_uint32),
            'wof_state_save': ([ctypes.c_void_p], None),
            'wof_state_load': ([ctypes.c_void_p], None),
            'wof_alloc': ([ctypes.c_uint32], ctypes.c_void_p),
            'wof_arena_reset': ([], None),
            'wof_framebuffer_width': ([], ctypes.c_uint32),
            'wof_framebuffer_height': ([], ctypes.c_uint32),
            'wof_palette_count': ([], ctypes.c_uint32),
            'wof_palette_colours': ([], ctypes.c_uint32),
            'wof_fs_count': ([], ctypes.c_uint32),
            'wof_vblank_count': ([], ctypes.c_uint32),
            'wof_tick_count': ([], ctypes.c_uint32),
            'wof_pass_count': ([], ctypes.c_uint32),
        }
        for name, (argtypes, restype) in signatures.items():
            function = getattr(self.lib, name)
            function.argtypes = argtypes
            function.restype = restype

        self.lib.wof_arena_reset()
        pointer, length = None, 0
        if blob:
            length = len(blob)
            pointer = self.lib.wof_alloc(length)
            assert pointer, 'core arena too small for the blob'
            ctypes.memmove(pointer, blob, length)
        self.lib.wof_init(seed, pointer, length)

        self.width = self.lib.wof_framebuffer_width()
        self.height = self.lib.wof_framebuffer_height()

    def run(self, vblanks, raw=0):
        for _ in range(vblanks):
            self.lib.wof_vblank(raw)
            self.lib.wof_pass()

    def framebuffer(self):
        return ctypes.string_at(self.lib.wof_framebuffer(), self.width * self.height)

    def palette_rows(self):
        raw = ctypes.string_at(self.lib.wof_palette_rows(), self.height * 2)
        return [int.from_bytes(raw[i:i + 2], sys.byteorder) for i in range(0, len(raw), 2)]

    def palettes(self):
        count = self.lib.wof_palette_count() * self.lib.wof_palette_colours()
        raw = ctypes.string_at(self.lib.wof_palettes(), count * 4)
        return [int.from_bytes(raw[i:i + 4], sys.byteorder) for i in range(0, len(raw), 4)]

    def render_audio(self, frames, rate):
        buffer = (ctypes.c_int16 * (frames * 2))()
        self.lib.wof_audio_render(buffer, frames, rate)
        return buffer

    def save_state(self):
        size = self.lib.wof_state_size()
        buffer = ctypes.create_string_buffer(size)
        self.lib.wof_state_save(buffer)
        return buffer.raw

    def load_state(self, state):
        buffer = ctypes.create_string_buffer(state, len(state))
        self.lib.wof_state_load(buffer)


def overlay_number(overlay, label):
    """One measurement off the diagnostics overlay, which is what a person reads too."""
    found = re.search(r'^%s\s+([\d.]+)' % re.escape(label), overlay, re.M)
    assert found, 'the overlay has no %r line:\n%s' % (label, overlay)
    return float(found.group(1))


def overlay_audio(overlay):
    """The overlay's audio line as (backend, context state, sample rate)."""
    found = re.search(r'^audio\s+(\w+), (\w+), (\d+) Hz', overlay, re.M)
    assert found, overlay
    return found.group(1), found.group(2), int(found.group(3))


def assert_web_audio_waits_for_a_gesture(report):
    """Nothing may build an AudioContext before the page has been activated: one built
    without activation is born suspended and never plays, whatever is pressed afterwards.
    That is what a browser's autoplay warning is about, and browsers do not hand that
    warning to WebDriver, so the invariant is watched directly (tests/audiowatch.mjs)."""
    assert report['audioBeforeKey'] == [], (
        'the shell touched Web Audio before any gesture: %s' % report['audioBeforeKey'])
    after = report['audioAfterKey']
    assert [call['call'] for call in after] == ['construct', 'resume'], after
    assert all(call['activated'] for call in after), after


def assert_a_modifier_alone_starts_nothing(report):
    """The case that cost a session of silence: Command pressed to open the console is a
    keydown that activates nothing.  The page must build no context there, and must go on
    saying that the sound is off."""
    after = report['modifierFirst']['afterModifier']
    assert after['events'] == ['keydown:Meta'], (
        'the page saw %d events for one key press' % len(after['events']))
    assert after['audio'] == [], 'a modifier alone built an AudioContext: %s' % after['audio']
    assert after['states'] == []
    assert after['promptShown'], 'the page stopped asking for a key although no sound started'


def assert_the_stick_keys_give_the_bits_of_the_spec(report):
    """SPEC 6.1: the up key is the stick pushed forward, bit 0 of the raw controller state, and
    the down key is the stick pulled back, bit 1.  Read twice while each key is held down
    through the driver: off the overlay's input line, which is what a person sees, and off
    the argument of wof_vblank itself, which is what the core gets (tests/corewatch.mjs)."""
    stick = report['stick']
    for key, bit, line in (('up', 0x01, '00001  UP down right left fire'),
                           ('down', 0x02, '00010  up DOWN right left fire'),
                           ('released', 0x00, '00000  up down right left fire')):
        seen = stick[key]
        assert seen['input'] == line, 'with %s the overlay says %r' % (key, seen['input'])
        raw = seen['raw']
        assert raw['calls'] > 5, 'only %d VBlanks went by while %s was read' % (raw['calls'], key)
        assert raw['last'] == bit and raw['seen'] == bit, (
            'with %s the core was handed %s' % (key, raw))


def assert_the_mission_is_flown_from_the_keyboard(flight):
    """M4 on the page, with the keys held in real time and the state read off the overlay:
    the lift brings the aircraft up to the deck, the roll takes it off the deck and the stick
    forward makes it climb; the pause stops the ticks and a second press lets them run on;
    the flip shows on the overlay."""
    assert flight['deck']['deck'] == 1 and flight['deck']['y'] > 30, flight['deck']
    assert flight['air']['deck'] == 0, 'the aircraft never left the deck: %s' % flight['air']
    one, two = flight['climb1'], flight['climb2']
    assert one['deck'] == 0 and two['y'] > one['y'] > 40, 'no climb: %s %s' % (one, two)
    first, second = flight['paused1'], flight['paused2']
    assert first['paused'] and second['paused'], (first, second)
    assert first['ticks'] == second['ticks'], 'ticks went on while paused: %s %s' % (first, second)
    assert second['vblanks'] > first['vblanks'], 'the clock stopped too: %s %s' % (first, second)
    first, second = flight['running1'], flight['running2']
    assert not first['paused'] and second['ticks'] > first['ticks'], (first, second)
    assert flight['flipped']['flip'], flight['flipped']
    assert_a_weapon_is_dropped_and_the_guns_fire(flight['drop'])


# M8 on the page: the sound, read off the overlay's pcm line (web/audio.js), which counts the
# frames of emulated time the shell took from the core, how many of them were not silent,
# the loudest sample, and what the drift guard padded and dropped.
def overlay_pcm(text):
    found = re.search(r'pcm\s+(\d+) frames, (\d+) audible, peak (\d+), padded (\d+), '
                      r'dropped (\d+)', text)
    assert found, 'no pcm line on the overlay:\n%s' % text
    return dict(zip(('frames', 'audible', 'peak', 'padded', 'dropped'),
                    (int(v) for v in found.groups())))


def assert_the_front_end_is_silent(overlay):
    """The front end plays no effect (its music is M8's part 2): the shell has taken PCM from
    the core since the key started the sound, and every frame of it is silence."""
    pcm = overlay_pcm(overlay)
    assert pcm['frames'] > 0, 'the shell took no PCM from the core: %s' % pcm
    assert pcm['audible'] == 0 and pcm['peak'] == 0, 'the front end made a sound: %s' % pcm


def assert_the_mission_is_heard(overlay, backend):
    """A mission's effects - the sea in the hold, the lift, the engine, the guns - came
    through the shell's audio path, `backend`, as PCM that is not silent."""
    backend_found, state, _ = overlay_audio(overlay)
    assert backend_found == backend and state == 'running', (backend_found, state)
    pcm = overlay_pcm(overlay)
    assert pcm['audible'] > 0 and pcm['peak'] > 0, 'the mission was silent: %s' % pcm
    assert pcm['frames'] > pcm['audible'], pcm


# Fullscreen and a page hidden for a moment (tests/pagefullscreen.mjs).  The owner's finding
# of 2026-09-26: Firefox put into fullscreen during a mission, the picture stood still and the
# sound was gone from then on.  A page hidden and shown again within a few milliseconds did
# both: the pause the shell asked for on the way out stopped the mission, and the audio
# context, whose suspend landed after the page was back, stayed suspended for good.

def assert_the_page_goes_on(seen, where, hz=50):
    """A span in which the mission runs: the clock at the standard's rate, the picture
    changing, the game not paused, and the sound flowing - PCM taken from the core, most of
    it audible (the sea aboard plays for ever), little of it silence the shell had to add."""
    assert not seen['pausedSeen'], '%s: the mission was paused: %s' % (where, seen)
    assert abs(seen['vblankRate'] - hz) <= 2.5, (
        '%s: %.1f VBlanks a second, want %d: %s' % (where, seen['vblankRate'], hz, seen))
    assert seen['pictures'] >= 3, '%s: the picture stood still: %s' % (where, seen)
    assert seen['audioAtEnd'] == 'running', (
        '%s: the audio context is %r: %s' % (where, seen['audioAtEnd'], seen))
    assert seen['emulated'] > 0 and seen['audible'] > seen['emulated'] / 2, (
        '%s: the sound did not flow: %s' % (where, seen))
    assert seen['padded'] <= seen['emulated'] / 4, (
        '%s: the shell had to fill the queue with silence: %s' % (where, seen))


def assert_a_moment_hidden_changes_nothing(report):
    """Hidden and shown again at once, as a window's change of state can make a page: the
    mission is not paused, and its sound comes back with the page."""
    moment = report['moment']
    assert moment['hides'] >= 1 and moment['lastHiddenMs'] is not None, (
        'the tab put in front did not hide the page: %s' % moment)
    assert moment['lastHiddenMs'] < 1000, moment
    assert_the_page_goes_on(moment, 'a moment hidden (%.0f ms)' % moment['lastHiddenMs'])


def assert_a_real_absence_comes_back_paused(report):
    """SPEC 6.2: a mission comes back from a hidden page paused, and P brings back the game
    and its sound."""
    absence = report['absence']
    assert absence['lastHiddenMs'] is not None and absence['lastHiddenMs'] >= 1000, absence
    assert absence['pausedAtEnd'], (
        'a mission hidden for %.0f ms came back running: %s' % (absence['lastHiddenMs'], absence))
    assert_the_page_goes_on(report['afterAbsence'], 'P after the absence')


def window_could_not_enter_fullscreen(report):
    """The window-state command answered that the window stayed as it was, and the page was
    hidden all through the span: on macOS a window cannot move into its fullscreen space
    while the screen is locked, and Firefox then reports the page hidden.  Nothing about the
    page can be measured then."""
    seen = report['fullscreen']
    return (report['enter'].get('state') != 'fullscreen' and seen['hiddenSeen']
            and seen['vblankRate'] == 0)


def assert_fullscreen_keeps_the_page_going(report, windowed_size, standard='PAL'):
    """Into fullscreen: five seconds with the clock, the picture and the sound going, and
    the box the largest that fits the new size.  Out of it: the mission paused, which the
    shell asks for whenever fullscreen is left (SPEC 6.2), and P brings everything back."""
    assert report['enter']['state'] == 'fullscreen', 'no fullscreen: %s' % report['enter']
    seen = report['fullscreen']
    assert seen['fullscreenSeen'], 'the page never saw itself in fullscreen: %s' % seen
    assert seen['size'] != list(windowed_size), (
        'the window kept its size %s in fullscreen' % windowed_size)
    assert_the_page_goes_on(seen, 'in fullscreen')
    assert_the_box_is_the_largest_that_fits(report['fullscreenGeometry'], standard, 'fullscreen')

    assert report['leave']['state'] == 'normal', report['leave']
    left = report['left']
    assert left['pausedAtEnd'], 'leaving fullscreen did not pause the mission: %s' % left
    assert_the_page_goes_on(report['continued'], 'P after leaving fullscreen')


# M6 on the page: what an enemy aircraft looks like in the framebuffer (tests/pagemeasure.mjs,
# SKY_PNG and enemyFlight).  Its 56 flying frames, the shapes of japplane.shp by the names
# enemy_frames reads (0x025F58), each pixel doubled across the low-resolution playfield, in
# the colours of map d's sky: row 40's palette at the first pass of oil_d's mission in the
# closed loop, the port's own.  Built once.
_ENEMY_TEMPLATES = []


def enemy_templates(ported):
    if _ENEMY_TEMPLATES:
        return _ENEMY_TEMPLATES
    import tempfile
    import hunk
    import m4compare
    import m6_scripts
    for part in hunk.load(str(ROOT / 'original' / 'disk' / 'Wings_of_Fury' / 'Wings')):
        if part['base'] <= 0x025F58 < part['base'] + len(part['data']):
            names = bytes(part['data'][0x025F58 - part['base']:0x025F58 - part['base'] + 56 * 4])
    japplane = 3                                                  # WOF_C_JAPPLANE
    frames = sorted({ported.shape_find(japplane, int.from_bytes(names[i:i + 4], 'big'))
                     for i in range(0, 56 * 4, 4)} - {-1})
    dump = str(pathlib.Path(tempfile.mkdtemp()) / 'oil_d.dump')
    machine = m4compare.record('oil_d', dump, pokes=m6_scripts.pokes('oil_d'))
    replay = m4compare.Replay(ported, machine, dump, mode='closed', pokes=m6_scripts.pokes('oil_d'))
    palette = []

    class Enough(Exception):
        pass

    def on_pass(r, memory, head, k):
        if memory.u(0x02507A, 2) == 0:                            # before step S
            return
        lib = ported.lib
        lib.wt_present()
        lib.wof_palette_rows.restype = ctypes.c_void_p
        lib.wof_palettes.restype = ctypes.c_void_p
        rows = ctypes.string_at(lib.wof_palette_rows(), lib.wof_framebuffer_height() * 2)
        count = lib.wof_palette_colours()
        pal = ctypes.string_at(lib.wof_palettes(), lib.wof_palette_count() * count * 4)
        row = int.from_bytes(rows[80:82], 'little')
        palette.extend(tuple(pal[(row * count + i) * 4:(row * count + i) * 4 + 3])
                       for i in range(count))
        raise Enough()
    try:
        replay.run(on_pass=on_pass)
    except Enough:
        pass
    for i in frames:
        w = ported.shape_field(japplane, i, 'wbytes') * 8
        h = ported.shape_field(japplane, i, 'height')
        px = ported.shape_pixels(japplane, i)
        pts = [(y, 2 * x + d, palette[px[y * w + x]]) for y in range(h) for x in range(w)
               for d in (0, 1) if px[y * w + x]]
        if len(pts) >= 12:
            _ENEMY_TEMPLATES.append((i, pts))
    return _ENEMY_TEMPLATES


def enemy_in(png_url, templates):
    """(shape, x, y) of an enemy aircraft's frame whose every opaque pixel the picture holds
    at one place, or None."""
    import numpy as np
    from PIL import Image
    image = np.array(Image.open(io.BytesIO(base64.b64decode(png_url.split(',', 1)[1])))
                     .convert('RGB'))
    for shape, pts in templates:
        y0, x0, c0 = pts[0]
        ys, xs = np.nonzero(np.all(image == np.array(c0, np.uint8), axis=2))
        for top, left in zip(ys - y0, xs - x0):
            if all(0 <= top + y < image.shape[0] and 0 <= left + x < image.shape[1] and
                   tuple(int(v) for v in image[top + y, left + x]) == c for y, x, c in pts[1:]):
                return (shape, int(left), int(top))
    return None


def assert_an_enemy_aircraft_comes_up(enemy, ported):
    """M6 on the page: in the second rank's first mission, map d (its hold at x 7456), the
    aircraft takes off and flies to the airfield; the sky taken on the way, out of the
    airfield's reach, shows no enemy aircraft, and the sky over the island shows the fighter
    the airfield sends up, found by its frame's pixels (enemy_templates)."""
    assert enemy['hold'] and enemy['hold']['x'] == 7456, 'not map d: %s' % enemy['hold']
    assert not enemy['hold']['flip'], 'the flip is on: %s' % enemy['hold']
    assert enemy['air']['deck'] == 0, 'the aircraft never left the deck: %s' % enemy['air']
    assert len(enemy['before']) >= 3, 'the sky was taken %d times on the way' % len(enemy['before'])
    assert len(enemy['over']) >= 10, 'only %d looks over the island: %s' % (
        len(enemy['over']), enemy['trail'][-3:])
    templates = enemy_templates(ported)
    assert len(templates) >= 20, 'only %d frames to look for' % len(templates)
    early = [(shot['x'], enemy_in(shot['png'], templates)) for shot in enemy['before']]
    assert all(found is None for _, found in early), 'an enemy aircraft before the airfield: %s' % early
    seen = [(shot['x'], shot['ms'], found) for shot in enemy['over']
            for found in [enemy_in(shot['png'], templates)] if found]
    assert seen, 'no enemy aircraft in %d looks over the island; last %s' % (
        len(enemy['over']), enemy['last'])


def assert_a_weapon_is_dropped_and_the_guns_fire(drop):
    """M5 on the page, read off the framebuffer: before the click the weapon counter is
    steady and nothing is white just above the sea; after it the counter has turned and a
    burst was drawn in the water (pure white in the rows just above the sea); the guns held
    for a second and a half leave the counter alone, and the aircraft flies on."""
    assert len(drop['counterBefore']) == 1, 'the counter moved before the click: %s' % drop
    assert drop['whiteBefore'] == 0, 'white above the sea before the click: %s' % drop
    assert drop['counterAfter'] != drop['counterBefore'][0], 'the counter did not turn: %s' % drop
    assert drop['whiteAfter'] >= 8, 'no burst drawn in the water: %s' % drop
    assert drop['samples'] >= 40, drop
    assert drop['counterGuns'] == drop['counterAfter'], 'the guns turned the counter: %s' % drop
    assert drop['player']['deck'] == 0 and drop['playerGuns']['deck'] == 0, drop


def assert_a_tap_as_soon_as_the_hold_appears_steps_once(early):
    """The first press in the hold, made at once when the mission scene is there, falls into
    the fifteen ticks in which the tick does not run the weapon menu yet; the keyboard assist
    keeps it, and it is one step up, the weapon type going down by one.  The press has to
    start well inside that window, which is about a second at PAL."""
    appeared = early['appeared']
    assert appeared and appeared['x'] != 0, 'the mission scene never appeared: %s' % early
    assert early['tapAfterMs'] < 400, 'the tap came too late to test the window: %s' % early
    assert early['after'] == (appeared['weapon'] - 1) % 3, 'the early tap was lost: %s' % early


def assert_the_weapon_menu_steps_once_per_tap(weapon):
    """The keyboard assist on the page (src/assist.c): three quick taps of the up key are
    three steps of the weapon type, which has three values, so they come round to where they
    started with a step seen on the way; with the flip on, up still steps up, the weapon type
    going down by one."""
    before = weapon['before']
    assert before in (0, 1, 2), weapon
    assert any(value != before for value in weapon['seen']), 'no step was seen: %s' % weapon
    assert weapon['after'] == before, 'three taps did not make three steps: %s' % weapon
    assert weapon['flipOn'], 'the flip did not come on: %s' % weapon
    assert weapon['flipped'] == (before - 1) % 3, 'with the flip on, up went down: %s' % weapon
    assert weapon['flipOff'], 'the flip did not go off again: %s' % weapon


def assert_the_next_real_key_starts_the_sound(report):
    after = report['modifierFirst']['afterSpace']
    assert [call['call'] for call in after['audio']] == ['construct', 'resume'], after['audio']
    assert all(call['activated'] for call in after['audio']), after['audio']
    assert after['states'] == ['running'], 'the context is %s' % after['states']
    assert not after['promptShown'], 'the prompt is still up although the sound is running'


@pytest.fixture(scope='session')
def native_core_factory(built):
    def make(seed, blob=b''):
        return NativeCore(seed, blob)
    return make


# --------------------------------------------------------- the port, for the oracle tests

SHAPE_FIELDS = ['wbytes', 'height', 'hot_x', 'hot_y', 'marker', 'src_y', 'clear', 'set',
                'planes', 'union', 'plane_bytes', 'has_pixels']

# Big enough for the largest file on the disk (world.shp unpacks to 67,264 bytes) and for
# the largest shape's pixels (rank, 3,040 bytes a plane, is 24,320 indexed pixels).
SCRATCH = 128 * 1024

# src/wof.h WOF_TRACE_TEXT: how much of a recorded string the trace keeps.
WOF_TRACE_TEXT = 64


class Ported:
    """The ported routines, reached through tests/shim.c on the native library.

    One process holds one copy of the core's statics, so this owns the library: nothing
    else may re-initialise it while a test is using one.
    """

    def __init__(self, blob):
        self.lib = ctypes.CDLL(str(DYLIB))
        p, i, u8p, u16p, c = (ctypes.c_void_p, ctypes.c_int,
                              ctypes.c_void_p, ctypes.c_void_p, ctypes.c_char_p)
        u32p = ctypes.c_void_p
        signatures = {
            'wof_init': ([ctypes.c_uint32, p, ctypes.c_uint32], None),
            'wof_alloc': ([ctypes.c_uint32], p),
            'wof_arena_reset': ([], None),
            'wof_assets_ready': ([], ctypes.c_uint32),
            'wof_rpck_unpack': ([p, ctypes.c_uint32, p, ctypes.c_uint32], None),
            'wof_colour_lerp': ([ctypes.c_int16, ctypes.c_uint16, ctypes.c_uint16],
                                ctypes.c_uint16),
            'wt_container_count': ([], i),
            'wt_container_shapes': ([i], i),
            'wt_container_name': ([i, i], ctypes.c_uint32),
            'wt_shape_field': ([i, i, i], i),
            'wt_shape_pixels': ([i, i, u8p, i], i),
            'wt_shape_find': ([i, ctypes.c_uint32], i),
            'wt_shape_by_index': ([i, i], i),
            'wt_table_entry': ([i, i], i),
            'wt_shape_mirror': ([i, i], None),
            'wt_shape_set_facing': ([i, i, i], None),
            'wt_load_file': ([c, u8p, i], i),
            'wt_iff_decode': ([c, i, i, i, u8p, u16p], i),
            'wt_cmap_file': ([c, u16p], i),
            'wt_text_width': ([c, i], i),
            'wt_text_render': ([c, i, u8p, i, i, i, i, i], i),
            'wt_font_height': ([], i),
            'wt_blit': ([i] * 11 + [u8p, u8p], i),
            # M3: the key path, the input sampling and the registry of src/globals.def
            'wof_keys_init': ([], None),
            'wof_key': ([ctypes.c_uint8, ctypes.c_uint16], None),
            'wof_port_key': ([ctypes.c_uint8, ctypes.c_uint16], None),
            'wof_key_available': ([], i),
            'wof_key_get': ([], ctypes.c_uint32),
            'wof_key_to_char': ([ctypes.c_uint32], ctypes.c_uint16),
            'wof_set_invert_vertical': ([i], None),
            'wof_invert_vertical': ([], i),
            'wof_input_init': ([], None),
            'wof_vblank': ([ctypes.c_uint8], None),
            'wof_poll_fire': ([], i),
            'wof_poll_joy_dir8': ([], i),
            'wof_read_joy_bits': ([], ctypes.c_uint16),
            'wof_input_queue_clear': ([], None),
            'wt_global_count': ([], i),
            'wt_globals_bytes': ([], i),
            'wt_global_name': ([i], ctypes.c_char_p),
            'wt_global_elem': ([i], i),
            'wt_global_elems': ([i], i),
            'wt_global_addr': ([i], ctypes.c_uint32),
            'wt_global_offset': ([i], ctypes.c_uint32),
            'wt_global_get': ([i, i], ctypes.c_uint32),
            'wt_global_set': ([i, i, ctypes.c_uint32], None),
            'wt_front_set': ([i, i], None),
            'wt_trace_count': ([], i),
            'wt_trace_dropped': ([], i),
            'wt_trace_reset': ([], None),
            'wt_trace_get': ([i, ctypes.c_char_p, ctypes.c_char_p,
                              ctypes.POINTER(ctypes.c_int)], i),
            'wt_music_count': ([], i),
            'wt_music_song': ([i], i),
            'wt_music_vblank': ([i], i),
            'wt_front_line': ([], i),
            'wt_mission_count': ([], i),
            'wt_global_get_at_mission': ([i, i], ctypes.c_uint32),
            'wt_front_vport_field': ([i, i], i),
            'wt_front_vport_pen': ([i, i], i),
            # M3 deliverables 5 and 6: the high-score file, the editor and the dialog
            'wt_hs_get': ([u8p], None),
            'wt_hs_put': ([u8p], None),
            'wt_hs_load': ([], None),
            'wt_hs_sort': ([], None),
            'wt_hs_save': ([], None),
            'wt_text_input_run': ([c, i, i, i, u8p, u16p, i], i),
            'wt_dir_entry': ([i], ctypes.c_char_p),
            'wt_fs_write': ([c, u8p, i], i),
            'wt_fs_delete': ([c], i),
            'wt_fs_writes_reset': ([], None),
            'wt_fs_written_count': ([], i),
            'wt_fs_written_name': ([i], ctypes.c_char_p),
            'wt_fs_written_size': ([i], i),
            'wt_fs_written_bytes': ([i, u8p, i], i),
            'wt_path_sanitise': ([c], None),
            'wt_hs_entry_run': ([u8p, u16p, i], i),
            'wt_dialog_run': ([i, u8p, u16p, i, ctypes.POINTER(ctypes.c_int)], i),
            'wt_dialog_name': ([i], ctypes.c_char_p),
            'wt_dialog_count': ([], i),
            # SPEC 10 point 13: the nine mathffp operations of src/ffp.c
            'wt_ffp': ([i, ctypes.c_uint32, ctypes.c_uint32, u32p], i),
            'wt_ffp_traps': ([], ctypes.c_uint32),
            'wt_ffp_traps_reset': ([], None),
            'wt_ffp_table': ([i, i], ctypes.c_uint32),
            'wof_dev_set_score': ([ctypes.c_uint32], None),
            'wof_dev_open_dialog': ([i], None),
            'wof_pass': ([], None),
            # M3 deliverable 2: the screens, the waits and the fades
            'wof_set_fade_vblanks': ([i], None),
            'wof_fade_vblanks': ([], i),
            'wt_view_setup': ([i, i, i], i),
            'wt_vport_colours_set': ([i, i, u16p], None),
            'wt_vport_colours_get': ([i, i, u16p], None),
            'wt_fade_run': ([u16p, u16p, i], i),
            'wt_frames_run': ([i, i, i, i], i),
            'wt_release_run': ([i, i, i], i),
            'wt_menu_run': ([i, i, i, ctypes.POINTER(ctypes.c_int)], i),
            'wt_story_bands': ([i, i, i, i, ctypes.POINTER(ctypes.c_uint32)], i),
        }
        for name, (argtypes, restype) in signatures.items():
            function = getattr(self.lib, name)
            function.argtypes = argtypes
            function.restype = restype

        self.blob = blob
        self.reset_core()
        self.scratch = (ctypes.c_uint8 * SCRATCH)()

    def reset_core(self, seed=1, fade_vblanks=None):
        """A fresh core on the same blob: the arena back to empty and wof_init again.  The
        front end then stands where it stands after the original's own initialisation, at
        the wait inside display_init."""
        self.lib.wof_arena_reset()
        pointer = self.lib.wof_alloc(len(self.blob))
        assert pointer, 'core arena too small for the blob'
        ctypes.memmove(pointer, self.blob, len(self.blob))
        if fade_vblanks is not None:
            self.lib.wof_set_fade_vblanks(fade_vblanks)
        self.lib.wt_trace_reset()
        self.lib.wof_init(seed, pointer, len(self.blob))
        assert self.lib.wof_assets_ready() == 1, 'the core did not load every asset'

    # --------------------------------------------------- driving the front end, M3

    def pass_(self):
        self.lib.wof_pass()

    def music_count(self):
        return self.lib.wt_music_count()

    def music_song(self, i):
        return self.lib.wt_music_song(i)

    def music_vblank(self, i):
        return self.lib.wt_music_vblank(i)

    def front_line(self):
        return self.lib.wt_front_line()

    def mission_count(self):
        return self.lib.wt_mission_count()

    def vport(self, field, back=False):
        names = ['width', 'height', 'depth', 'out_y', 'disp_rows', 'scroll', 'ring_at',
                 'ramp', 'hires', 'next']
        pens = ['apen', 'bpen', 'drmd']
        if field in pens:
            return self.lib.wt_front_vport_pen(1 if back else 0, pens.index(field))
        return self.lib.wt_front_vport_field(1 if back else 0, names.index(field))

    def traces(self, what=None):
        """What the port recorded (src/trace.c): the routine, the VBlank, four numbers and
        a string.  `what` filters by routine name."""
        assert self.lib.wt_trace_dropped() == 0, 'the trace ring overflowed'
        name = ctypes.create_string_buffer(16)
        text = ctypes.create_string_buffer(WOF_TRACE_TEXT)
        numbers = (ctypes.c_int * 5)()
        out = []
        for index in range(self.lib.wt_trace_count()):
            assert self.lib.wt_trace_get(index, name, text, numbers)
            routine = name.value.decode('latin1')
            if what is not None and routine != what:
                continue
            out.append({'what': routine, 'vblank': numbers[0], 'text': text.value.decode('latin1'),
                        'a': numbers[1], 'b': numbers[2], 'c': numbers[3], 'd': numbers[4]})
        return out

    def file_log(self):
        return [(r['vblank'], r['text'], bool(r['a'])) for r in self.traces('load_file')]

    # ------------------------------------------------------- the floating point, point 13

    FFP_OPERATIONS = ('add', 'sub', 'mul', 'div', 'cmp', 'tst', 'neg', 'fix', 'flt')

    def ffp(self, operation, d0, d1=0):
        """One mathffp operation through src/ffp.c: (D0, D1, condition codes, trap)."""
        out = (ctypes.c_uint32 * 4)()
        assert self.lib.wt_ffp(self.FFP_OPERATIONS.index(operation), d0, d1, out), operation
        return out[0], out[1], out[2], out[3]

    def ffp_traps(self):
        return self.lib.wt_ffp_traps()

    def ffp_traps_reset(self):
        self.lib.wt_ffp_traps_reset()

    def ffp_table(self, which):
        count = self.lib.wt_ffp_table(which, -1)
        return [self.lib.wt_ffp_table(which, i) for i in range(count)]

    # ------------------------------------------------------------------ loaders

    def rpck_unpack(self, packed, out_len):
        src = (ctypes.c_uint8 * len(packed)).from_buffer_copy(packed)
        dst = (ctypes.c_uint8 * out_len)()
        self.lib.wof_rpck_unpack(src, len(packed), dst, out_len)
        return bytes(dst)

    def load_file(self, name):
        n = self.lib.wt_load_file(name.encode('latin1'), self.scratch, SCRATCH)
        return None if n < 0 else bytes(self.scratch[:n])

    # ------------------------------------------------------------------- shapes

    def container_shapes(self, slot):
        return self.lib.wt_container_shapes(slot)

    def container_name(self, slot, index):
        return self.lib.wt_container_name(slot, index)

    def shape_field(self, slot, index, field):
        return self.lib.wt_shape_field(slot, index, SHAPE_FIELDS.index(field))

    def shape_pixels(self, slot, index):
        n = self.lib.wt_shape_pixels(slot, index, self.scratch, SCRATCH)
        assert n >= 0, (slot, index)
        return bytes(self.scratch[:n])

    def shape_find(self, slot, name):
        return self.lib.wt_shape_find(slot, name)

    def shape_by_index(self, slot, index):
        return self.lib.wt_shape_by_index(slot, index)

    def table_entry(self, slot, index):
        return self.lib.wt_table_entry(slot, index)

    def shape_mirror(self, slot, index):
        self.lib.wt_shape_mirror(slot, index)

    def shape_set_facing(self, slot, index, facing):
        self.lib.wt_shape_set_facing(slot, index, facing)

    # ----------------------------------------------------------------- pictures

    def iff_decode(self, path, width, rows, depth):
        pixels = (ctypes.c_uint8 * (width * rows))()
        colours = (ctypes.c_uint16 * 32)()
        ok = self.lib.wt_iff_decode(path.encode('latin1'), width, rows, depth,
                                    pixels, colours)
        assert ok, path
        return bytes(pixels), list(colours)

    def cmap_file_to_table(self, path):
        colours = (ctypes.c_uint16 * 32)()
        assert self.lib.wt_cmap_file(path.encode('latin1'), colours), path
        return list(colours)

    # --------------------------------------------------------------------- text

    def text_width(self, text):
        raw = text.encode('latin1')
        return self.lib.wt_text_width(raw, len(raw))

    def text_render(self, text, x, row, justify, buf_w, buf_h):
        raw = text.encode('latin1')
        bpr = ((buf_w + 15) // 16) * 2
        buffer = (ctypes.c_uint8 * (bpr * buf_h + 64))()
        width = self.lib.wt_text_render(raw, len(raw), buffer, x, row, justify,
                                        buf_w, buf_h)
        return width, bytes(buffer[:bpr * buf_h])

    # ------------------------------------------------------------------- colour

    def colour_lerp(self, step, source, target):
        return self.lib.wof_colour_lerp(step, source, target)

    # ------------------------------------------------------------ the key path, M3

    def keys_init(self):
        self.lib.wof_keys_init()

    def key(self, code, qualifier=0):
        self.lib.wof_key(code, qualifier)

    def port_key(self, code, qualifier=0):
        self.lib.wof_port_key(code, qualifier)

    def key_available(self):
        return self.lib.wof_key_available()

    def key_get(self):
        return self.lib.wof_key_get()

    def key_to_char(self, key):
        return self.lib.wof_key_to_char(key)

    def set_invert_vertical(self, on):
        self.lib.wof_set_invert_vertical(1 if on else 0)

    def invert_vertical(self):
        return self.lib.wof_invert_vertical()

    def input_init(self):
        self.lib.wof_input_init()

    def vblank(self, raw):
        self.lib.wof_vblank(raw)

    def poll_fire(self):
        return self.lib.wof_poll_fire()

    def poll_joy_dir8(self):
        return self.lib.wof_poll_joy_dir8()

    def read_joy_bits(self):
        return self.lib.wof_read_joy_bits()

    def input_queue_clear(self):
        self.lib.wof_input_queue_clear()

    # ------------------------------------------------ the screens, waits and fades, M3

    def set_fade_vblanks(self, n):
        self.lib.wof_set_fade_vblanks(n)

    def fade_vblanks(self):
        return self.lib.wof_fade_vblanks()

    def view_setup(self, depth, depth2=0, colours2=False):
        return self.lib.wt_view_setup(depth, depth2, 1 if colours2 else 0)

    def set_colours(self, which, table, values):
        buffer = (ctypes.c_uint16 * 32)(*values)
        self.lib.wt_vport_colours_set(which, table, buffer)

    def colours(self, which, table):
        buffer = (ctypes.c_uint16 * 32)()
        self.lib.wt_vport_colours_get(which, table, buffer)
        return list(buffer)

    def fade_run(self, target1=None, target2=None, pair=False):
        a = (ctypes.c_uint16 * 32)(*target1) if target1 else None
        b = (ctypes.c_uint16 * 32)(*target2) if target2 else None
        return self.lib.wt_fade_run(a, b, 1 if pair else 0)

    def frames_run(self, n, raw=0, raw_after=0, switch_at=-1):
        return self.lib.wt_frames_run(n, raw, raw_after, switch_at)

    def release_run(self, raw=0, raw_after=0, switch_at=-1):
        return self.lib.wt_release_run(raw, raw_after, switch_at)

    def menu_run(self, timeout=0, raw=0, limit=4000):
        rounds = ctypes.c_int(0)
        result = self.lib.wt_menu_run(timeout, raw, limit, ctypes.byref(rounds))
        return result, rounds.value

    def story_bands(self, scroll, ring_at, ramp, row=-1):
        colour = ctypes.c_uint32(0)
        used = self.lib.wt_story_bands(scroll, ring_at, ramp, row, ctypes.byref(colour))
        return used, colour.value

    # ------------------------------------------- the registry of src/globals.def, SPEC 7.2

    def globals_registry(self):
        """name -> (element size, element count, the original's address, struct offset)."""
        out = {}
        for index in range(self.lib.wt_global_count()):
            out[self.lib.wt_global_name(index).decode()] = (
                self.lib.wt_global_elem(index), self.lib.wt_global_elems(index),
                self.lib.wt_global_addr(index), self.lib.wt_global_offset(index))
        return out

    def globals_bytes(self):
        return self.lib.wt_globals_bytes()

    def _global_index(self, name):
        for index in range(self.lib.wt_global_count()):
            if self.lib.wt_global_name(index).decode() == name:
                return index
        raise KeyError('%s is not in src/globals.def' % name)

    def g(self, name, index=0):
        return self.lib.wt_global_get(self._global_index(name), index)

    def g_all(self, name):
        which = self._global_index(name)
        return [self.lib.wt_global_get(which, i)
                for i in range(self.lib.wt_global_elems(which))]

    def set_g(self, name, value, index=0):
        self.lib.wt_global_set(self._global_index(name), index, value)

    # -------------------------------------- the high scores, the editor and the dialog

    def hs_table(self):
        buffer = (ctypes.c_uint8 * 360)()
        self.lib.wt_hs_get(buffer)
        return bytes(buffer)

    def set_hs_table(self, data):
        assert len(data) == 360
        self.lib.wt_hs_put((ctypes.c_uint8 * 360).from_buffer_copy(data))

    def hs_load(self):
        self.lib.wt_hs_load()

    def hs_sort(self):
        self.lib.wt_hs_sort()

    def hs_save(self):
        self.lib.wt_hs_save()

    def text_input(self, text, keys, max_length=16, x=0, y=0):
        """One run of the line editor: the buffer it starts with, the keys, what it left."""
        buffer = ctypes.create_string_buffer(text.encode('latin1'), max_length + 8)
        codes = (ctypes.c_uint8 * max(len(keys), 1))(*[k[0] for k in keys])
        quals = (ctypes.c_uint16 * max(len(keys), 1))(*[k[1] for k in keys])
        result = self.lib.wt_text_input_run(buffer, max_length, x, y, codes, quals, len(keys))
        return result, buffer.value.decode('latin1')

    def hs_entry_run(self, keys=((0x44, 0),)):
        """high_score_entry to its end, with the keys the name entry is given."""
        codes = (ctypes.c_uint8 * max(len(keys), 1))(*[k[0] for k in keys])
        quals = (ctypes.c_uint16 * max(len(keys), 1))(*[k[1] for k in keys])
        return self.lib.wt_hs_entry_run(codes, quals, len(keys))

    def dialog_run(self, mode, keys):
        """The whole load and save dialog, with its keys fed as it takes them."""
        codes = (ctypes.c_uint8 * max(len(keys), 1))(*[k[0] for k in keys])
        quals = (ctypes.c_uint16 * max(len(keys), 1))(*[k[1] for k in keys])
        rounds = ctypes.c_int(0)
        result = self.lib.wt_dialog_run(mode, codes, quals, len(keys), ctypes.byref(rounds))
        return result, rounds.value

    def dialog_names(self):
        return [self.lib.wt_dialog_name(i).decode('latin1') for i in range(6)]

    def path_sanitise(self, name):
        buffer = ctypes.create_string_buffer(name.encode('latin1'), len(name) + 8)
        self.lib.wt_path_sanitise(buffer)
        return buffer.value.decode('latin1')

    def dir_entries(self):
        out = []
        while True:
            name = self.lib.wt_dir_entry(len(out))
            if not name:
                return out
            out.append(name.decode('latin1'))

    def fs_write(self, name, data):
        return self.lib.wt_fs_write(name.encode('latin1'),
                                    (ctypes.c_uint8 * len(data)).from_buffer_copy(data),
                                    len(data))

    def fs_delete(self, name):
        return self.lib.wt_fs_delete(name.encode('latin1'))

    def fs_reset(self):
        self.lib.wt_fs_writes_reset()

    def fs_written(self):
        out = []
        buffer = (ctypes.c_uint8 * 8192)()
        for i in range(self.lib.wt_fs_written_count()):
            n = self.lib.wt_fs_written_bytes(i, buffer, 8192)
            out.append((self.lib.wt_fs_written_name(i).decode('latin1'), bytes(buffer[:n])))
        return out

    def dev_set_score(self, score):
        self.lib.wof_dev_set_score(score)

    def dev_open_dialog(self, mode):
        self.lib.wof_dev_open_dialog(1 if mode else 0)

    def g_at_mission(self, name, index=0):
        """A global as it stood where the front end ended, which is the moment the harness
        calls step S.  The outer loop runs on into the next rank selection in the same pass
        while the mission is a stand-in, so the value has to be taken there."""
        return self.lib.wt_global_get_at_mission(self._global_index(name), index)

    # --------------------------------------------------------------------- blit

    def blit(self, slot, index, bytes_per_row, rows, depth, clip, x, y, background):
        out = (ctypes.c_uint8 * len(background))()
        source = (ctypes.c_uint8 * len(background)).from_buffer_copy(background)
        n = self.lib.wt_blit(slot, index, bytes_per_row, rows, depth,
                             clip[0], clip[1], clip[2], clip[3], x, y, source, out)
        assert n == len(background), (slot, index)
        return bytes(out)


@pytest.fixture(scope='session')
def ported(built, blob):
    return Ported(blob)


# ------------------------------------------------- the display box, SPEC 6.2 bullet Video

# The box one 640 x 214 framebuffer is shown in, per video standard.  Both are the machine's,
# not a preference: a low-resolution pixel is 16/15 as wide as tall on PAL and 5/6 on NTSC.
BOXES = {'PAL': (1024, 642), 'NTSC': (800, 642)}

# Everything about the box is judged in device pixels and to within one of them, because that
# is the unit the shell rounds to and the smallest difference anybody could see.
DEVICE_PIXEL = 1.0

# How far a colour read back off the page may be from the framebuffer pixel it belongs to.
# The sample points sit in flat neighbourhoods (tests/pagemeasure.mjs), so the smooth
# reduction has nothing to blend there and the difference should be nothing at all; this
# leaves room for a rounding step, not for a wrong picture.
CANVAS_TOLERANCE = 8

# A screenshot is what the compositor shows, and it may carry a colour transform the canvas
# read-back does not.  The tolerance is therefore wider - but still far from black.
SCREENSHOT_TOLERANCE = 32
BLACK = 12


def measured_box(geometry):
    """The DOM's own numbers, converted to device pixels: what the page really shows."""
    dpr = geometry['dpr']
    rect = geometry['rect']
    return {
        'left': rect['left'] * dpr,
        'top': rect['top'] * dpr,
        'width': rect['width'] * dpr,
        'height': rect['height'] * dpr,
        'available_width': math.floor(geometry['window']['width'] * dpr),
        'available_height': math.floor(geometry['window']['height'] * dpr),
        'dpr': dpr,
    }


def _where(geometry, note):
    return '%s: window %s at dpr %s, canvas %s, backing %s, the shell says %s' % (
        note, geometry['window'], geometry['dpr'], geometry['rect'], geometry['backing'],
        geometry['shellSays'])


def assert_the_box_has_the_display_aspect(geometry, standard, note=''):
    """SPEC 6.2: 1024 : 642 on PAL, 800 : 642 on NTSC - never square framebuffer pixels,
    which would give a strip three times as wide as it is high."""
    box = measured_box(geometry)
    wide, high = BOXES[standard]
    wanted = box['height'] * wide / high
    assert abs(box['width'] - wanted) <= DEVICE_PIXEL, (
        'the box is %.2f x %.2f device pixels, which is %.4f : 1, not %d : %d (%.2f x %.2f) - %s'
        % (box['width'], box['height'], box['width'] / box['height'], wide, high,
           wanted, box['height'], _where(geometry, note)))


def assert_the_box_is_the_largest_that_fits(geometry, standard, note=''):
    """The largest box of that ratio the window holds, centred, on whole device pixels, with
    the backing store in device pixels so that nothing is resampled a third time."""
    box = measured_box(geometry)
    wide, high = BOXES[standard]
    available_width = box['available_width']
    available_height = box['available_height']

    if available_width * high >= available_height * wide:
        assert abs(box['height'] - available_height) <= DEVICE_PIXEL, (
            'the window is wider than the box, so the box must be as high as the window - %s'
            % _where(geometry, note))
    else:
        assert abs(box['width'] - available_width) <= DEVICE_PIXEL, (
            'the window is taller than the box, so the box must be as wide as the window - %s'
            % _where(geometry, note))
    assert box['width'] <= available_width + DEVICE_PIXEL, _where(geometry, note)
    assert box['height'] <= available_height + DEVICE_PIXEL, _where(geometry, note)

    assert abs(box['left'] - (available_width - box['width']) / 2) <= DEVICE_PIXEL, (
        'the box is not centred sideways - %s' % _where(geometry, note))
    assert abs(box['top'] - (available_height - box['height']) / 2) <= DEVICE_PIXEL, (
        'the box is not centred up and down - %s' % _where(geometry, note))

    assert abs(geometry['backing']['width'] - box['width']) <= DEVICE_PIXEL, (
        'the backing store is not the CSS width in device pixels - %s' % _where(geometry, note))
    assert abs(geometry['backing']['height'] - box['height']) <= DEVICE_PIXEL, (
        'the backing store is not the CSS height in device pixels - %s' % _where(geometry, note))

    for name in ('left', 'top', 'width', 'height'):
        assert abs(box[name] - round(box[name])) <= 0.25, (
            'the box does not land on whole device pixels (%s is %.3f) - %s'
            % (name, box[name], _where(geometry, note)))


def assert_the_samples_are_a_real_picture(display, note=''):
    """A sample set of one colour would pass against a canvas that drew nothing."""
    points = display['points']
    assert len(points) >= 12, '%s: only %d sample points' % (note, len(points))
    colours = {tuple(point['source']) for point in points}
    lit = [colour for colour in colours if max(colour) > BLACK]
    assert len(colours) >= 3 and len(lit) >= 2, (
        '%s: the sample points carry %s, which is too little of a picture to prove anything'
        % (note, sorted(colours)))


def assert_the_canvas_shows_the_picture(display, note=''):
    """The canvas the browser composites carries the framebuffer, read back pixel by pixel at
    the centres of framebuffer pixels that sit in a flat neighbourhood."""
    assert_the_samples_are_a_real_picture(display, note)
    worst = None
    for point in display['points']:
        delta = max(abs(a - b) for a, b in zip(point['source'], point['display']))
        if worst is None or delta > worst[0]:
            worst = (delta, point)
    assert worst[0] <= CANVAS_TOLERANCE, (
        '%s: at framebuffer pixel (%d, %d) the page shows %s where the framebuffer has %s'
        % (note, worst[1]['x'], worst[1]['y'], worst[1]['display'], worst[1]['source']))
    assert display['displayColours'] >= 8, (
        '%s: the canvas on the page has %d colours' % (note, display['displayColours']))


def screenshot_image(encoded):
    from PIL import Image
    return Image.open(io.BytesIO(base64.b64decode(encoded))).convert('RGB')


def assert_the_screenshot_shows_the_picture(encoded, geometry, display, note=''):
    """What the compositor puts on the screen, which a canvas read-back is not: inside the box
    the screenshot carries the picture, outside it there is black and nothing else."""
    assert_the_samples_are_a_real_picture(display, note)
    image = screenshot_image(encoded)
    dpr = geometry['dpr']
    rect = geometry['rect']
    # The screenshot need not be in device pixels; what it is in is decided by comparing it
    # with the viewport it shows.
    scale = image.width / geometry['window']['width']

    def shot_pixel(css_x, css_y):
        x = min(image.width - 1, max(0, int(css_x * scale)))
        y = min(image.height - 1, max(0, int(css_y * scale)))
        return image.getpixel((x, y))

    worst = None
    for point in display['points']:
        got = shot_pixel(rect['left'] + point['dx'] / dpr, rect['top'] + point['dy'] / dpr)
        delta = max(abs(a - b) for a, b in zip(point['source'], got))
        if worst is None or delta > worst[0]:
            worst = (delta, point, got)
    assert worst[0] <= SCREENSHOT_TOLERANCE, (
        '%s: the screenshot shows %s at framebuffer pixel (%d, %d), where the framebuffer has '
        '%s' % (note, list(worst[2]), worst[1]['x'], worst[1]['y'], worst[1]['source']))

    outside = []
    margin_left = rect['left']
    margin_top = rect['top']
    if margin_left >= 4:
        outside.append((margin_left / 2, rect['top'] + rect['height'] / 2))
        outside.append((rect['left'] + rect['width'] + margin_left / 2,
                        rect['top'] + rect['height'] / 2))
    if margin_top >= 4:
        outside.append((rect['left'] + rect['width'] / 2, margin_top / 2))
        outside.append((rect['left'] + rect['width'] / 2,
                        rect['top'] + rect['height'] + margin_top / 2))
    assert outside, '%s: the box fills the window, so there is nothing outside it' % note
    for css_x, css_y in outside:
        got = shot_pixel(css_x, css_y)
        assert max(got) <= BLACK, (
            '%s: outside the box, at (%.0f, %.0f) css, the screenshot is %s, not black'
            % (note, css_x, css_y, list(got)))
