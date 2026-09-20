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
    """vblank_server counts a divider down from 4 and samples when it goes below 1.  The
    divider lies in the zero-filled part of DATA, so the very first VBlank samples and the
    next one is the fifth: N VBlanks give ceil(N / 4) samples, not floor."""
    for step in wasm['ticks']['steps']:
        assert step['ticks'] == -(-step['vblanks'] // 4), step
        assert step['passes'] == step['vblanks'], step
    after = wasm['ticks']['after600']
    assert (after['vblanks'], after['ticks'], after['passes']) == (600, 150, 600)


def test_palette_rows_select_more_than_one_palette(wasm):
    rows = wasm['paletteRows']
    assert rows['distinct'] >= 2, 'the test pattern must prove per-row palettes'
    assert rows['max'] < wasm['geometry']['paletteCount']
    assert rows['first'] != rows['last']


def test_palettes_are_opaque_and_distinct(wasm):
    """Palette 0 is the blank one every row no viewport covers goes through, which is what
    the copper's BPLCON0 = 0x0200 gives on the machine; the picture's own colours are in
    the palette its band names."""
    assert wasm['palettes']['opaque'], 'palette entries must carry alpha 0xFF'
    assert wasm['palettes']['differ'], 'the two palettes must not be the same table'
    assert wasm['palettes']['blankIsBlack'], wasm['palettes']['distinct']
    assert wasm['palettes']['richest'] >= 16, wasm['palettes']['distinct']


def test_framebuffer_holds_indices_inside_the_palette(wasm):
    framebuffer = wasm['framebuffer']
    assert framebuffer['size'] == wasm['geometry']['width'] * wasm['geometry']['height']
    assert framebuffer['max'] < wasm['geometry']['paletteColours']
    assert framebuffer['nonzero'] > framebuffer['size'] // 10, 'the test pattern is nearly empty'


def test_display_list_exists_and_a_shape_page_fills_it(wasm):
    """SPEC 6.4: every shape draw appends a record.  The first page draws a picture, not
    shapes, so the list starts empty and fills when the browser draws."""
    assert wasm['displayList']['pointer']
    assert wasm['displayList']['count'] == 0
    assert wasm['viewer']['shapePageDraws'] > 0, 'the shape page appended nothing'


def test_the_assets_all_loaded(wasm):
    """Every container, the font and the four palettes came off the packed disk."""
    assert wasm['assetsReady'] == 1


def test_every_viewer_page_draws_something_of_its_own(wasm):
    viewer = wasm['viewer']
    for index, page in enumerate(viewer['pages']):
        assert page['nonzero'] > 1000, 'page %d is nearly empty: %s' % (index, page)
    assert viewer['allDifferent'], [p['hash'][:8] for p in viewer['pages']]
    assert viewer['wrapsRound'], 'stepping through every page did not come back to the first'


def test_the_pictures_have_their_own_colours(wasm):
    """The three pictures of the M1 acceptance criterion, pages 0 to 2."""
    for index in (0, 1, 2):
        assert wasm['viewer']['pages'][index]['colours'] >= 8, wasm['viewer']['pages'][index]


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
