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

from conftest import (assert_a_modifier_alone_starts_nothing,
                      assert_the_next_real_key_starts_the_sound,
                      assert_web_audio_waits_for_a_gesture,
                      overlay_audio, overlay_number)

CHROME = os.environ.get('WOF_CHROME', '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome')

pytestmark = pytest.mark.skipif(not os.path.exists(CHROME), reason='Google Chrome is not installed')


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
    """SPEC 6.4: 640 x 214, the play screen's three viewports stacked."""
    picture = loaded['picture']
    assert (picture['width'], picture['height']) == (640, 214)
    assert picture['colours'] >= 8, 'the publisher logo has almost no colours in it'


def test_the_canvas_is_scaled_by_a_whole_number(loaded):
    factor = int(loaded['picture']['cssWidth'].replace('px', '')) / loaded['picture']['width']
    assert factor == int(factor) and factor >= 1


def test_the_three_pictures_are_on_the_canvas(loaded):
    """The M1 acceptance criterion: the publisher logo, the title and the credit picture,
    each decoded by the ported ILBM reader with its own colours."""
    for index, what in ((0, 'publisher logo'), (1, 'title'), (2, 'credits')):
        page = loaded['pages'][index]
        assert page['colours'] >= 8, 'the %s has %d colours' % (what, page['colours'])
    hashes = [loaded['pages'][i]['hash'] for i in range(3)]
    assert len(set(hashes)) == 3, 'two of the three pictures are the same picture'


def test_every_viewer_page_draws_something(loaded):
    for index, page in enumerate(loaded['pages']):
        assert page['colours'] >= 2, 'page %d is one flat colour' % index
    assert len(set(page['hash'] for page in loaded['pages'])) == len(loaded['pages'])
    assert loaded['wrapped']['hash'] == loaded['pages'][0]['hash'], (
        'stepping past the last page did not come back to the first')


def test_the_play_screen_stacks_three_viewports(loaded):
    """The playfield, the dashboard at line 163 and the ticker at line 201, with lines 162
    and 200 blank - which is what the copper does above every lower viewport."""
    rows = loaded['playScreen']['rows']
    assert rows['playfield'] > 0, 'the playfield is empty'
    assert rows['dashboard'] > 0, 'the dashboard is empty'
    assert rows['ticker'] > 0, 'the ticker is empty'
    assert rows['blankAboveDash'] == 0, 'line 162 is not blank'
    assert rows['blankAboveTicker'] == 0, 'line 200 is not blank'


def test_the_emulated_clock_is_steady(loaded):
    assert abs(overlay_number(loaded['overlay'], 'vblanks/s') - 60) <= 2
    assert abs(overlay_number(loaded['overlay'], 'passes/s') - 60) <= 2
    assert abs(overlay_number(loaded['overlay'], 'ticks/s') - 15) <= 1
    assert 'exactly 4: yes' in loaded['overlay']
    assert overlay_number(loaded['overlay'], 'animation/s') > 30


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
