"""The same C sources as a native library, reached through ctypes.

SPEC section 8 runs every later milestone's oracle tests this way, against the original
executable under Unicorn, so the path has to work from the first milestone on.
"""
import ctypes
import hashlib
import re

import pytest

from conftest import ROOT


def test_native_library_loads_and_reports_the_same_geometry(native_core_factory, wasm, blob):
    core = native_core_factory(1, blob)
    assert core.width == wasm['geometry']['width']
    assert core.height == wasm['geometry']['height']
    assert core.lib.wof_palette_count() == wasm['geometry']['paletteCount']
    assert core.lib.wof_state_size() == wasm['geometry']['stateSize']


def test_four_vblanks_make_one_tick(native_core_factory):
    core = native_core_factory(1)
    core.run(240)
    assert core.lib.wof_vblank_count() == 240
    assert core.lib.wof_tick_count() == 60
    assert core.lib.wof_pass_count() == 240


@pytest.mark.parametrize('rate,hz', [(44100, 50), (48000, 60)])
def test_the_pcm_follows_the_emulated_time(native_core_factory, blob, rate, hz):
    """The frames wof_audio_render returns are the VBlanks' at the rate asked for: 882 or 800
    a VBlank here, the story scroller's song in them from its first notes, nothing more once
    they are taken (M8)."""
    core = native_core_factory(1, blob)
    core.lib.wof_set_video_hz(hz)
    buffer = (ctypes.c_int16 * (65536 * 2))()
    assert core.lib.wof_audio_render(buffer, 65536, rate) == 0
    core.run(20)
    frames = core.lib.wof_audio_render(buffer, 65536, rate)
    assert frames == 20 * rate // hz
    assert any(buffer[:frames * 2])
    assert core.lib.wof_audio_render(buffer, 65536, rate) == 0


def test_state_round_trips(native_core_factory, blob):
    core = native_core_factory(7, blob)
    core.run(100)
    saved = core.save_state()
    picture = core.framebuffer()

    core.run(60)
    straight = core.save_state()
    assert straight != saved

    core.load_state(saved)
    assert core.framebuffer() == picture
    core.run(60)
    assert core.save_state() == straight


def test_the_packed_file_system_reaches_the_core(native_core_factory, blob, game_file_names):
    core = native_core_factory(1, blob)
    assert core.lib.wof_fs_count() == len(game_file_names)


def test_palette_rows_cover_the_whole_picture(native_core_factory, wasm, blob):
    """The picture is black until the front end has run: wof_init leaves the coroutine at
    the wait inside display_init, where no viewport is installed yet."""
    core = native_core_factory(1, blob)
    core.run(200)
    rows = core.palette_rows()
    assert len(rows) == core.height
    assert max(rows) < wasm['geometry']['paletteCount']
    assert len(set(rows)) >= 2


def test_native_and_wasm_draw_the_same_picture(native_core_factory, wasm, blob):
    """The same sources compile for both targets (SPEC 6.1); they must also behave the same,
    or the oracle tests would be proving something the browser does not run.  The picture is
    decoded from the packed disk now, so both sides need the same blob."""
    expected = wasm['crossTarget']
    core = native_core_factory(expected['seed'], blob)
    core.run(expected['vblanks'], expected['raw'])
    assert hashlib.sha256(core.framebuffer()).hexdigest() == expected['hash']


def test_the_shell_hands_back_every_file_the_core_can_write(native_core_factory):
    """web/core.js puts a stored file back into the core's file system at a page's start
    (fsPut) only up to its FILE_MAX, and its scratch buffer has that size.  The core has no
    export for its own limit, WOF_SAVE_MAX (src/wof.h), the largest saved game its tables
    allow: so the macro is evaluated here and the shell's number read from its line, and the
    core takes a file of that size and refuses one a byte longer.  With a smaller number in
    the shell, a saved game on a large map is stored at the end of a visit and not put back
    at the next (tests/test_page.py, the oversized saved game)."""
    header = (ROOT / 'src' / 'wof.h').read_text(encoding='utf-8')
    found = re.search(r'^#define WOF_SAVE_MAX \((.*)\)$', header, re.M)
    assert found, 'WOF_SAVE_MAX is not a single-line expression in src/wof.h'
    expression = re.sub(r'\b(0x[0-9A-Fa-f]+|\d+)u\b', r'\1', found.group(1))
    assert re.fullmatch(r'[0-9A-Fa-fx+* ()]+', expression), expression
    save_max = eval(expression)

    shell = re.findall(r'^const FILE_MAX = (\d+);$',
                       (ROOT / 'web' / 'core.js').read_text(encoding='utf-8'), re.M)
    assert shell == [str(save_max)], 'web/core.js FILE_MAX %s, WOF_SAVE_MAX %d' % (shell, save_max)

    core = native_core_factory(1)
    put = core.lib.wof_fs_put
    put.argtypes = [ctypes.c_char_p, ctypes.c_char_p, ctypes.c_uint32]
    put.restype = ctypes.c_int
    core.lib.wof_fs_writes_reset()
    try:
        assert put(b'wof.largest', bytes(save_max), save_max) == 1
        assert put(b'wof.over', bytes(save_max + 1), save_max + 1) == 0
        assert core.lib.wof_fs_written_count() == 1
    finally:
        core.lib.wof_fs_writes_reset()
