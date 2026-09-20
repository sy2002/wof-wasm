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
            'wof_audio_render': ([ctypes.c_void_p, ctypes.c_uint32, ctypes.c_uint32], None),
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


class Ported:
    """The ported routines, reached through tests/shim.c on the native library.

    One process holds one copy of the core's statics, so this owns the library: nothing
    else may re-initialise it while a test is using one.
    """

    def __init__(self, blob):
        self.lib = ctypes.CDLL(str(DYLIB))
        p, i, u8p, u16p, c = (ctypes.c_void_p, ctypes.c_int,
                              ctypes.c_void_p, ctypes.c_void_p, ctypes.c_char_p)
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
        }
        for name, (argtypes, restype) in signatures.items():
            function = getattr(self.lib, name)
            function.argtypes = argtypes
            function.restype = restype

        self.lib.wof_arena_reset()
        pointer = self.lib.wof_alloc(len(blob))
        assert pointer, 'core arena too small for the blob'
        ctypes.memmove(pointer, blob, len(blob))
        self.lib.wof_init(1, pointer, len(blob))
        assert self.lib.wof_assets_ready() == 1, 'the core did not load every asset'
        self.scratch = (ctypes.c_uint8 * SCRATCH)()

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
