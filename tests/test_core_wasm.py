"""The core as it runs in the browser: dist/core.wasm, instantiated in Node.

The measurements come from tests/wasm_harness.mjs; this file is the judgement on them.
"""
import pytest

# The interface SPEC.md section 6.1 declares.  The names are normative.
SPEC_EXPORTS = [
    'wof_init', 'wof_set_video_hz', 'wof_vblank', 'wof_pass', 'wof_framebuffer',
    'wof_palette_rows', 'wof_palettes', 'wof_display_list', 'wof_audio_render',
    'wof_state_size', 'wof_state_save', 'wof_state_load',
]

TONE_TOLERANCE_HZ = 2.0


def test_exports_the_spec_interface(wasm):
    missing = [name for name in SPEC_EXPORTS if name not in wasm['exports']]
    assert not missing, 'missing from the core: %s' % missing
    assert 'memory' in wasm['exports'], 'the shell needs the linear memory'


def test_core_needs_nothing_from_the_host(wasm):
    """No imports at all: no clock, no allocator, no callback into JavaScript (SPEC 6.1)."""
    assert wasm['imports'] == []


def test_geometry_is_queryable_and_sane(wasm):
    geometry = wasm['geometry']
    assert geometry['width'] > 0 and geometry['height'] > 0
    assert geometry['width'] % 8 == 0
    assert geometry['paletteCount'] >= 2
    assert geometry['paletteColours'] >= 32
    assert geometry['stateSize'] > 0


def test_four_vblanks_make_one_tick(wasm):
    for step in wasm['ticks']['steps']:
        assert step['ticks'] == step['vblanks'] // 4, step
        assert step['passes'] == step['vblanks'], step
    after = wasm['ticks']['after600']
    assert (after['vblanks'], after['ticks'], after['passes']) == (600, 150, 600)


def test_palette_rows_select_more_than_one_palette(wasm):
    rows = wasm['paletteRows']
    assert rows['distinct'] >= 2, 'the test pattern must prove per-row palettes'
    assert rows['max'] < wasm['geometry']['paletteCount']
    assert rows['first'] != rows['last']


def test_palettes_are_opaque_and_distinct(wasm):
    assert wasm['palettes']['opaque'], 'palette entries must carry alpha 0xFF'
    assert wasm['palettes']['differ'], 'the two palettes must not be the same table'
    assert wasm['palettes']['distinctInPalette0'] >= 16


def test_framebuffer_holds_indices_inside_the_palette(wasm):
    framebuffer = wasm['framebuffer']
    assert framebuffer['size'] == wasm['geometry']['width'] * wasm['geometry']['height']
    assert framebuffer['max'] < wasm['geometry']['paletteColours']
    assert framebuffer['nonzero'] > framebuffer['size'] // 10, 'the test pattern is nearly empty'


def test_display_list_exists_and_is_empty(wasm):
    """SPEC 6.4 keeps the door open for an enhanced renderer; nothing fills it before M1."""
    assert wasm['displayList']['pointer']
    assert wasm['displayList']['count'] == 0


@pytest.mark.parametrize('case,left,right', [
    ('idle44100', 440, 660),
    ('idle48000', 440, 660),
    ('fire48000', 880, 1320),
])
def test_test_tone_has_the_right_pitch_at_the_requested_rate(wasm, case, left, right):
    tone = wasm['tones'][case]
    assert abs(tone['left'] - left) < TONE_TOLERANCE_HZ, tone
    assert abs(tone['right'] - right) < TONE_TOLERANCE_HZ, tone
    assert 0 < tone['peak'] <= 32767


def test_state_round_trips(wasm):
    state = wasm['state']
    assert state['restored']['frame'] == state['savedFrame'], 'loading did not restore the picture'
    assert state['matchesAfterReplay'], 'a replay from a loaded state diverged (SPEC 7.3)'


def test_state_moves_between_cores(wasm):
    """A save must not depend on anything host-side, or replays and tests cannot use it."""
    assert wasm['state']['foreignCoreMatches']
    assert wasm['state']['foreignFrameAfterLoad'] == wasm['state']['savedFrame']


def test_state_load_rejects_foreign_data(wasm):
    assert wasm['state']['rejectsGarbage'], 'wof_state_load accepted bytes it did not write'


def test_the_picture_is_a_function_of_the_seed(wasm):
    assert wasm['determinism']['sameSeed'], 'same seed and input gave different pictures'
    assert wasm['determinism']['differentSeed'], 'the seed does not reach the entropy stream'


def test_the_packed_file_system_reaches_the_core(wasm, game_file_names):
    assert wasm['files'] == len(game_file_names)
    assert wasm['emptyFs'] == 0, 'a core given no blob must report no files'
