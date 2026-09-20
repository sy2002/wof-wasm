"""dist/wof.html in a real browser, headless, from a file:// URL.

This is the M1 acceptance criterion of SPEC section 9 as far as it can be decided without a
person: the page opens from file://, shows the publisher logo, the title and the credit
picture with their own colours, browses the shapes, holds a steady emulated 60 Hz and makes
no network request.  Whether the tone is audible is the one part left over.

Skipped where Google Chrome is not installed; set WOF_CHROME to use another binary.
"""
import json
import os
import re
import subprocess
import sys

import pytest

from picture import (assert_the_blocks_have_hard_edges,
                     assert_the_picture_lies_where_the_dom_says,
                     assert_the_screenshot_is_the_picture)
from conftest import (assert_a_modifier_alone_starts_nothing,
                      assert_the_box_has_the_display_aspect,
                      assert_the_box_is_the_largest_that_fits,
                      assert_the_canvas_shows_the_picture,
                      assert_the_next_real_key_starts_the_sound,
                      assert_the_screenshot_shows_the_picture,
                      assert_the_stick_keys_give_the_bits_of_the_spec,
                      assert_web_audio_waits_for_a_gesture,
                      measured_box, overlay_audio, overlay_number)

# What the shell was showing when each measurement was taken.
STANDARD_OF = {'default': 'PAL', 'ntsc': 'NTSC', 'palAgain': 'PAL', 'wide': 'PAL',
               'tall': 'PAL', 'small': 'PAL', 'retina': 'PAL', 'ranks': 'PAL'}

CHROME = os.environ.get('WOF_CHROME', '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome')

pytestmark = pytest.mark.skipif(not os.path.exists(CHROME), reason='Google Chrome is not installed')


# The two pictures the scale-factor run photographs.
SCALED = ('title', 'ranks')


@pytest.fixture(scope='session')
def scaled(built):
    """The same page under a true scale factor of 2, which is what a Retina display gives.

    An emulated devicePixelRatio is not the same thing: Chrome then places the canvas on
    whole CSS pixels, so where a box edge falls on half a CSS pixel the picture is shifted by
    a device pixel or resampled a third time (SPEC 8, row Page).  That artefact would hide a
    real one, so the picture itself is judged here and not in the emulated run."""
    from conftest import ROOT
    finished = subprocess.run(
        ['node', str(ROOT / 'tests' / 'pagescale.mjs'), str(built), CHROME],
        cwd=ROOT, capture_output=True, text=True)
    assert finished.returncode == 0, 'tests/pagescale.mjs failed:\n%s' % finished.stderr
    return json.loads(finished.stdout)


@pytest.fixture(scope='session')
def loaded(built):
    from conftest import ROOT
    finished = subprocess.run(
        ['node', str(ROOT / 'tests' / 'pagecheck.mjs'), str(built), CHROME],
        cwd=ROOT, capture_output=True, text=True)
    assert finished.returncode == 0, 'tests/pagecheck.mjs failed:\n%s' % finished.stderr
    return json.loads(finished.stdout)


def test_page_makes_no_network_request(loaded):
    outside = [url for url in loaded['requests'] if not url.startswith('file://')]
    assert not outside, 'the page asked for %s' % outside
    assert loaded['requests'] == [loaded['requests'][0]], 'the page loaded more than itself'


def test_page_loads_without_errors(loaded):
    assert loaded['console'] == []


def test_the_picture_is_the_core_geometry(loaded):
    """SPEC 6.4: 640 x 214, which is the play screen's three viewports stacked.  The front
    end fills the first 200 of those lines and leaves the rest black."""
    picture = loaded['picture']
    assert (picture['width'], picture['height']) == (640, 214)
    assert picture['colours'] >= 8, 'the rank selection has almost no colours in it'


def test_the_front_end_runs_on_the_page(loaded):
    """M3's acceptance, walked the way a player walks it: the story scroller when the page
    opens, the publisher logo when fire ends it, the title after it, and the rank selection
    when a second fire skips the rest (re/notes/frontend.md).  Each of the three pictures is
    decoded by the ported ILBM reader and faded up to its own colours."""
    front = loaded['front']
    assert front['scroller']['colours'] >= 2, 'the story scroller drew nothing'
    for name in ('logo', 'title', 'ranks'):
        assert front[name]['colours'] >= 8, (
            'the %s has %d colours' % (name, front[name]['colours']))
    hashes = [front[name]['hash'] for name in ('scroller', 'logo', 'title', 'ranks')]
    assert len(set(hashes)) == 4, 'two of the four screens are the same picture'


def test_a_front_end_screen_leaves_the_rows_below_it_black(loaded):
    """A front-end screen is one viewport of 200 lines at line 0, so the fourteen lines
    below it go through the blank palette, which is what the copper's BPLCON0 = 0x0200 gives
    on the machine.  The play screen's three stacked viewports arrive with M4."""
    rows = loaded['picture']['rows']
    assert rows['playfield'] > 0, 'the picture is empty'
    assert rows['blankAboveTicker'] == 0, 'row 200 is below a 200-line screen'
    assert rows['ticker'] == 0, 'row 205 is below the front-end screen and must be black'


def test_the_emulated_clock_is_steady(loaded):
    """PAL is the default video standard, so the page runs at 50 VBlanks, 50 passes and
    12.5 ticks a second.  A counted rate of something that happens 12.5 times a second is a
    whole number either way; the cumulative ratio is the exact statement."""
    assert abs(overlay_number(loaded['overlay'], 'vblanks/s') - 50) <= 2
    assert abs(overlay_number(loaded['overlay'], 'passes/s') - 50) <= 2
    assert abs(overlay_number(loaded['overlay'], 'ticks/s') - 12.5) <= 1
    assert 'exactly 4: yes' in loaded['overlay']
    assert overlay_number(loaded['overlay'], 'animation/s') > 30


def test_the_ntsc_standard_runs_the_clock_at_60(loaded):
    """One setting: key 6 is the 800 : 642 box and 60 Hz together, key 5 is PAL again."""
    ntsc = loaded['box']['ntsc']['overlay']
    assert abs(overlay_number(ntsc, 'vblanks/s') - 60) <= 2
    assert abs(overlay_number(ntsc, 'passes/s') - 60) <= 2
    assert abs(overlay_number(ntsc, 'ticks/s') - 15) <= 1
    assert 'exactly 4: yes' in ntsc

    back = loaded['box']['palAgain']['overlay']
    assert abs(overlay_number(back, 'vblanks/s') - 50) <= 2
    assert abs(overlay_number(back, 'passes/s') - 50) <= 2
    assert abs(overlay_number(back, 'ticks/s') - 12.5) <= 1


# ------------------------------------------------------------------ the picture on the page

def test_the_picture_is_shown_in_the_display_aspect(loaded):
    """SPEC 6.2: 1024 : 642 on PAL and 800 : 642 on NTSC, measured off the DOM.  Square
    framebuffer pixels would give 640 : 214, a strip three times as wide as it is high."""
    for name, standard in STANDARD_OF.items():
        assert_the_box_has_the_display_aspect(loaded['box'][name]['geometry'], standard, name)


def test_the_picture_fills_the_window(loaded):
    """The largest box of that ratio that fits, centred, on whole device pixels."""
    for name, standard in STANDARD_OF.items():
        assert_the_box_is_the_largest_that_fits(loaded['box'][name]['geometry'], standard, name)


def test_the_picture_follows_a_resize(loaded):
    """A wide, a tall and a small viewport, each set through the driver: in the wide one the
    box is as high as the window, in the tall one as wide, which the assertions above decide
    for each.  What is left to prove here is that the viewport really did change and that the
    box is not simply the same rectangle every time."""
    seen = {}
    for name in ('default', 'wide', 'tall', 'small', 'retina'):
        geometry = loaded['box'][name]['geometry']
        seen[name] = (geometry['window']['width'], geometry['window']['height'],
                      geometry['dpr'], geometry['backing']['width'], geometry['backing']['height'])
    assert len(set(seen.values())) == len(seen), seen

    wide = measured_box(loaded['box']['wide']['geometry'])
    assert abs(wide['height'] - wide['available_height']) <= 1 and wide['width'] < wide['available_width']
    tall = measured_box(loaded['box']['tall']['geometry'])
    assert abs(tall['width'] - tall['available_width']) <= 1 and tall['height'] < tall['available_height']


def test_a_retina_backing_store_is_the_css_size_times_two(loaded):
    """devicePixelRatio 2, emulated through the DevTools protocol: the canvas has to carry
    twice as many pixels in each direction as its CSS size, or the picture is resampled by
    the browser on top of everything the shell did.

    The arithmetic is all this run can answer for.  An emulated ratio places the canvas on
    whole CSS pixels, so where a box edge falls on half a CSS pixel the picture itself is
    shifted by a device pixel or resampled again - a fault of the emulation, not of the
    shell (SPEC 8, row Page).  What the picture really looks like at that ratio is measured
    by the scale-factor tests above, which give Chrome the factor on its command line."""
    geometry = loaded['box']['retina']['geometry']
    assert geometry['dpr'] == 2, geometry
    assert geometry['backing']['width'] == round(geometry['rect']['width'] * 2), geometry
    assert geometry['backing']['height'] == round(geometry['rect']['height'] * 2), geometry


def test_the_canvas_on_the_page_shows_the_picture(loaded):
    """The exact pixels live on the source canvas now; what the page shows is the two-step
    scaling of them.  Sample points at the centres of framebuffer pixels, taken where the
    framebuffer is flat so that the smooth step has nothing to blend, must carry the colour
    that belongs there - on the title picture, on the play screen and at every size."""
    for name in STANDARD_OF:
        assert_the_canvas_shows_the_picture(loaded['box'][name]['display'], name)


def test_a_screenshot_shows_the_picture_in_the_box_and_black_around_it(loaded):
    """A screenshot is what the compositor puts on the screen, which a canvas read-back is
    not: it also proves that the canvas is where the measurements say it is."""
    shot = [name for name in STANDARD_OF if loaded['box'][name].get('screenshot')]
    assert sorted(shot) == ['default', 'ranks', 'retina', 'tall', 'wide'], shot
    for name in shot:
        seen = loaded['box'][name]
        assert_the_screenshot_shows_the_picture(seen['screenshot'], seen['geometry'],
                                                seen['display'], name)


# ------------------------------------------- the picture itself, under a true scale factor

def test_the_scale_factor_run_puts_a_box_edge_on_half_a_css_pixel(scaled):
    """The case that shows whether the picture is really laid out in device pixels, and the
    reason this second run exists.  If the window ever stopped producing such an edge the
    checks below would still pass while proving much less, so it is asserted, not assumed."""
    for name in SCALED:
        geometry = scaled[name]['geometry']
        assert geometry['dpr'] == 2, geometry
        rect = geometry['rect']
        halves = [side for side in ('left', 'top', 'width', 'height')
                  if abs(rect[side] % 1 - 0.5) < 0.01]
        assert halves, 'no edge of the box is on half a CSS pixel: %s' % rect


def test_the_scale_factor_run_is_the_same_page(scaled):
    """It is the shipped page, showing the framebuffer, with nothing lying over it: the
    gesture prompt is gone because a real key started the sound, and the hint bar with it."""
    assert scaled['console'] == [], scaled['console']
    for name in SCALED:
        picture = scaled[name]['picture']
        assert (picture['width'], picture['height']) == (640, 214), picture
        assert picture['colours'] >= 8, picture
        assert scaled[name]['hintVisible'] is False


def test_the_screenshot_is_the_picture_pixel_for_pixel(scaled):
    """Every one of the 136,960 framebuffer pixels, at the centre of the block it is shown
    as, against a screenshot of what the compositor put on the screen."""
    for name in SCALED:
        seen = scaled[name]
        assert_the_screenshot_is_the_picture(seen['sourcePng'], seen['screenshot'],
                                             seen['geometry'], name)


def test_the_picture_lies_where_the_dom_says(scaled):
    """Fitted from the picture's own colour edges, to a fraction of a device pixel: this is
    what catches a picture shifted or stretched by one, which a sample point in a flat area
    and a rectangle read off the DOM both agree to."""
    for name in SCALED:
        seen = scaled[name]
        assert_the_picture_lies_where_the_dom_says(seen['sourcePng'], seen['screenshot'],
                                                   seen['geometry'], name)


def test_the_blocks_have_hard_edges(scaled):
    """Two-step scaling, seen from the outside: between the centres of two neighbouring
    blocks of different colour there is almost nothing that is neither colour."""
    for name in SCALED:
        seen = scaled[name]
        assert_the_blocks_have_hard_edges(seen['sourcePng'], seen['screenshot'],
                                          seen['geometry'], name)


def test_the_hint_names_the_diagnostics_key_by_its_place(loaded):
    """The shell tests event.code Backquote, which is where the key is, not what is printed
    on it; that key is a caret on a German keyboard.  So the hint says where to press, and
    naming the character would send some players to a key they do not have there."""
    assert '`' not in loaded['hint'], loaded['hint']
    assert 'left of 1' in loaded['hint'], loaded['hint']


def test_the_hint_bar_shares_the_diagnostics_key(loaded):
    """It would lie over the ticker rows in every window wider than the box, so it goes with
    the gesture prompt and comes back only with the diagnostics overlay."""
    assert loaded['hintVisibleWithOverlay'], 'the hint bar is not shown with the overlay'
    for name in ('default', 'wide', 'tall', 'retina', 'ranks'):
        assert loaded['box'][name]['hintVisible'] is False, (
            'the hint bar is still up with the overlay closed (%s)' % name)


def test_audio_is_running_after_the_key_press(loaded):
    """The shipped configuration, not merely some backend: a file:// page loads the worklet
    module from a data: URL, and the fallback taking over silently would be a regression."""
    backend, state, rate = overlay_audio(loaded['overlay'])
    assert backend == 'worklet', 'the page fell back to %r' % backend
    assert 'worklet module from a data: URL' in loaded['overlay'], loaded['overlay']
    assert state == 'running'
    assert rate >= 8000
    assert overlay_number(loaded['overlay'], 'buffer') > 0, 'no audio is queued'
    assert re.search(r'buffer\s+[\d.]+ ms queued, 0 underruns', loaded['overlay']), loaded['overlay']


def test_the_scheduled_buffer_fallback_also_plays(loaded):
    """The path a browser that refuses the worklet lands on, asked for with ?audio=buffers."""
    fallback = loaded['fallback']
    backend, state, rate = overlay_audio(fallback['overlay'])
    assert backend == 'buffers', backend
    assert state == 'running'
    assert rate >= 8000
    assert re.search(r'buffer\s+[\d.]+ ms queued, 0 underruns', fallback['overlay']), fallback['overlay']
    assert fallback['console'] == []
    assert all(url.startswith('file://') for url in fallback['requests']), fallback['requests']


def test_web_audio_waits_for_a_gesture(loaded):
    assert_web_audio_waits_for_a_gesture(loaded)


def test_a_modifier_alone_starts_nothing(loaded):
    assert_a_modifier_alone_starts_nothing(loaded)


def test_the_next_real_key_starts_the_sound(loaded):
    assert_the_next_real_key_starts_the_sound(loaded)


def test_the_up_key_is_the_stick_pushed_forward(loaded):
    assert loaded['stick']['console'] == [], loaded['stick']['console']
    assert_the_stick_keys_give_the_bits_of_the_spec(loaded)


def test_the_gesture_prompt_goes_away(loaded):
    assert loaded['gestureHidden']
    assert loaded['overlayVisible'], 'the overlay did not open on its key'


def test_a_stall_is_not_made_up_frame_for_frame(loaded):
    """SPEC 6.2: after a stall at most 24 VBlanks are replayed, which is the original's own
    limit of six queued ticks seen from the outside."""
    stall = loaded['stall']
    blocked = stall['before']['vblanks']
    resumed = stall['after']['vblanks']
    real_time_would_give = (stall['blockedMs'] + stall['settleMs']) / 1000 * 60

    assert stall['after']['stalls'] > stall['before']['stalls'], 'the clock did not notice'
    assert resumed > blocked, 'the clock did not start again'
    assert resumed - blocked < real_time_would_give / 2, (
        'replayed %d VBlanks after a %d ms stall' % (resumed - blocked, stall['blockedMs']))


# ------------------------------------- the dialog, the line editor and browser storage

def test_the_save_dialog_and_the_line_editor_work_on_the_page(loaded):
    """M3's acceptance, walked on the real page: the save dialog comes up, a letter typed
    into a slot changes what is on screen, and accepting it writes a file whose name is the
    one that was typed - which is the rename re/notes/frontend.md observed, because the slot
    held the disk's own `wof.mission 3`."""
    storage = loaded['storage']
    assert storage['before'] == [], (
        'the page began with files an earlier run left: %s' % storage['before'])
    assert storage['dialog']['hash'] != storage['edited']['hash'], (
        'typing into the slot changed nothing on screen')

    saved = storage['afterSave']
    assert isinstance(saved, list), saved
    assert [file['name'] for file in saved] == ['wof.amission 3'], saved
    assert all(file['bytes'] > 0 for file in saved)


def test_a_high_score_typed_into_the_entry_reaches_the_file(loaded):
    """The name entry appears because the score beats the tenth, the name goes in through
    the line editor, and the 360 bytes of re/notes/highscore.md come out: a u32 score, a u16
    rank and a NUL-padded name, best first."""
    storage = loaded['storage']
    files = {file['name']: file for file in storage['afterEntry']}

    assert 'highscore' in files, storage['afterEntry']
    entry = files['highscore']
    assert entry['bytes'] == 360, 'the high-score file is ten entries of thirty-six bytes'

    best = entry['text'][:36]
    score = sum(ord(c) << (8 * (3 - i)) for i, c in enumerate(best[:4]))
    assert score == 5000, 'the development key sets 5000; the file holds %d' % score
    assert best[6:].split('\x00')[0] == 'aba', 'the name that was typed is %r' % best[6:12]


def test_what_the_game_wrote_is_still_there_on_the_next_visit(loaded):
    """SPEC 6.2, Storage, and M3's acceptance: high scores persist across reloads.  The
    second visit is a fresh page on the same file:// origin, and it reads the same files."""
    storage = loaded['storage']
    assert storage['reloadConsole'] == [], storage['reloadConsole']

    before = {file['name']: file['text'] for file in storage['afterEntry']}
    after = {file['name']: file['text'] for file in storage['afterReload']}
    assert after == before, 'the page came back with %s' % sorted(after)
    assert 'highscore' in after and len(after['highscore']) == 360


def test_the_high_score_screen_is_a_picture_and_a_slab(loaded):
    """Two viewports of different depths, 320 x 75 at line 0 and 640 x 145 at line 76, each
    faded up to its own colours (re/notes/display.md)."""
    assert loaded['storage']['highScores']['colours'] >= 16, loaded['storage']['highScores']
