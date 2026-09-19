"""dist/wof.html in Firefox, from a file:// URL.

Firefox earns a run of its own: its canvas and its autoplay policy differ from Chrome's, and
the first version of the shell drew a black picture there while every Chrome test was green.

Headless by default.  The canvas fault that caused that black picture only happens on the
accelerated canvas, which headless Firefox does not use, so the check that would have caught
it needs a real window and is opt-in: WOF_FIREFOX_VISIBLE=1.

Skipped where Firefox is not installed; set WOF_FIREFOX to use another binary.
"""
import json
import os
import subprocess

import pytest

from conftest import (ROOT,
                      assert_a_modifier_alone_starts_nothing,
                      assert_the_next_real_key_starts_the_sound,
                      assert_web_audio_waits_for_a_gesture,
                      overlay_audio, overlay_number)

FIREFOX = os.environ.get('WOF_FIREFOX', '/Applications/Firefox.app/Contents/MacOS/firefox')
HARNESS = ROOT / 'tests' / 'pagecheck_firefox.mjs'

pytestmark = pytest.mark.skipif(not os.path.exists(FIREFOX), reason='Firefox is not installed')


def run_firefox(page, visible):
    command = ['node', str(HARNESS), str(page), FIREFOX] + (['--visible'] if visible else [])
    finished = subprocess.run(command, cwd=ROOT, capture_output=True, text=True)
    assert finished.returncode == 0, 'tests/pagecheck_firefox.mjs failed:\n%s\n%s' % (
        finished.stdout, finished.stderr)
    return json.loads(finished.stdout)


@pytest.fixture(scope='session')
def loaded_firefox(built):
    return run_firefox(built, visible=False)


@pytest.fixture(scope='session')
def loaded_firefox_visible(built):
    if os.environ.get('WOF_FIREFOX_VISIBLE') != '1':
        pytest.skip('opens a window; set WOF_FIREFOX_VISIBLE=1 to run it')
    return run_firefox(built, visible=True)


def test_page_makes_no_network_request(loaded_firefox):
    """Firefox reports the page's own data: URLs - the icon and the worklet module - as
    requests where Chrome does not.  Neither leaves the file."""
    outside = [url for url in loaded_firefox['requests']
               if not url.startswith(('file://', 'data:'))]
    assert not outside, 'the page asked for %s' % outside


def test_page_loads_without_errors(loaded_firefox):
    errors = [entry for entry in loaded_firefox['logs'] if entry['level'] == 'error']
    assert errors == []


def test_web_audio_waits_for_a_gesture(loaded_firefox):
    assert_web_audio_waits_for_a_gesture(loaded_firefox)
    autoplay = [entry for entry in loaded_firefox['logs'] if 'autoplay' in entry['text'].lower()]
    assert autoplay == [], autoplay


def test_a_modifier_alone_starts_nothing(loaded_firefox):
    assert_a_modifier_alone_starts_nothing(loaded_firefox)


def test_the_next_real_key_starts_the_sound(loaded_firefox):
    assert_the_next_real_key_starts_the_sound(loaded_firefox)


def test_the_picture_is_the_core_geometry(loaded_firefox):
    picture = loaded_firefox['picture']
    assert (picture['width'], picture['height']) == (640, 214)
    assert picture['colours'] >= 8, 'the publisher logo has almost no colours in it'


def test_the_three_pictures_are_on_the_canvas(loaded_firefox):
    for index in (0, 1, 2):
        assert loaded_firefox['pages'][index]['colours'] >= 8, loaded_firefox['pages'][index]
    hashes = [loaded_firefox['pages'][i]['hash'] for i in range(3)]
    assert len(set(hashes)) == 3, 'two of the three pictures are the same picture'


def test_the_play_screen_stacks_three_viewports(loaded_firefox):
    rows = loaded_firefox['playScreen']['rows']
    assert rows['playfield'] > 0 and rows['dashboard'] > 0 and rows['ticker'] > 0, rows
    assert rows['blankAboveDash'] == 0 and rows['blankAboveTicker'] == 0, rows


def test_the_emulated_clock_is_steady(loaded_firefox):
    overlay = loaded_firefox['overlay']
    assert abs(overlay_number(overlay, 'vblanks/s') - 60) <= 2
    assert abs(overlay_number(overlay, 'passes/s') - 60) <= 2
    assert abs(overlay_number(overlay, 'ticks/s') - 15) <= 1
    assert 'exactly 4: yes' in overlay


def test_audio_is_running_after_the_key_press(loaded_firefox):
    """The same worklet from a data: URL that Chrome takes.  Underruns are not asserted:
    Firefox under WebDriver has no real output device and starves the graph at start-up."""
    backend, state, rate = overlay_audio(loaded_firefox['overlay'])
    assert backend == 'worklet', 'Firefox fell back to %r' % backend
    assert state == 'running'
    assert rate >= 8000
    assert overlay_number(loaded_firefox['overlay'], 'buffer') > 0, 'no audio is queued'


def test_the_visible_canvas_shows_the_picture(loaded_firefox_visible):
    """The one check headless cannot make.  In GPU-composited Firefox an accelerated 2D
    canvas never shows what putImageData wrote and reads back as a single colour, which is
    the black screen a player would see; web/video.js asks for a software-backed canvas to
    avoid it."""
    picture = loaded_firefox_visible['picture']
    assert picture['colours'] > 1, 'the shipped canvas reads back as one colour'
    assert picture['colours'] >= 8
    rows = loaded_firefox_visible['playScreen']['rows']
    assert rows['playfield'] > 0 and rows['dashboard'] > 0 and rows['ticker'] > 0, rows
