"""The same C sources as a native library, reached through ctypes.

SPEC section 8 runs every later milestone's oracle tests this way, against the original
executable under Unicorn, so the path has to work from the first milestone on.
"""
import ctypes
import hashlib

import pytest


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
    a VBlank here, silence in the front end, nothing more once they are taken (M8)."""
    core = native_core_factory(1, blob)
    core.lib.wof_set_video_hz(hz)
    buffer = (ctypes.c_int16 * (65536 * 2))()
    assert core.lib.wof_audio_render(buffer, 65536, rate) == 0
    core.run(20)
    frames = core.lib.wof_audio_render(buffer, 65536, rate)
    assert frames == 20 * rate // hz
    assert not any(buffer[:frames * 2])
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
