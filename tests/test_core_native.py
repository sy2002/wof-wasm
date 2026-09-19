"""The same C sources as a native library, reached through ctypes.

SPEC section 8 runs every later milestone's oracle tests this way, against the original
executable under Unicorn, so the path has to work from the first milestone on.
"""
import hashlib

import pytest

TONE_TOLERANCE_HZ = 2.0


def frequency(samples, channel, frames, rate):
    """Zero crossings of the triangle wave: two per cycle."""
    crossings = 0
    for i in range(1, frames):
        if (samples[(i - 1) * 2 + channel] < 0) != (samples[i * 2 + channel] < 0):
            crossings += 1
    return crossings / 2 / (frames / rate)


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


@pytest.mark.parametrize('rate', [44100, 48000])
def test_test_tone_follows_the_requested_rate(native_core_factory, rate):
    core = native_core_factory(1)
    frames = 16384
    samples = core.render_audio(frames, rate)
    assert abs(frequency(samples, 0, frames, rate) - 440) < TONE_TOLERANCE_HZ
    assert abs(frequency(samples, 1, frames, rate) - 660) < TONE_TOLERANCE_HZ


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
    core = native_core_factory(1, blob)
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
