"""dist/wof.html in a real browser, headless, from a file:// URL.

This is the M0 acceptance criterion of SPEC section 9 as far as it can be decided without a
person: the page opens from file://, draws the test pattern, holds a steady emulated 60 Hz
and makes no network request.  Whether the tone is audible is the one part left over.

Skipped where Google Chrome is not installed; set WOF_CHROME to use another binary.
"""
import json
import os
import re
import subprocess
import sys

import pytest

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


def overlay_number(loaded, label):
    found = re.search(r'^%s\s+([\d.]+)' % re.escape(label), loaded['overlay'], re.M)
    assert found, 'the overlay has no %r line:\n%s' % (label, loaded['overlay'])
    return float(found.group(1))


def test_page_makes_no_network_request(loaded):
    outside = [url for url in loaded['requests'] if not url.startswith('file://')]
    assert not outside, 'the page asked for %s' % outside
    assert loaded['requests'] == [loaded['requests'][0]], 'the page loaded more than itself'


def test_page_loads_without_errors(loaded):
    assert loaded['console'] == []


def test_the_test_pattern_is_on_the_canvas(loaded):
    picture = loaded['picture']
    assert (picture['width'], picture['height']) == (640, 200)
    assert picture['colours'] >= 32, 'the picture has almost no colours in it'


def test_the_canvas_is_scaled_by_a_whole_number(loaded):
    factor = int(loaded['picture']['cssWidth'].replace('px', '')) / loaded['picture']['width']
    assert factor == int(factor) and factor >= 1


def test_the_two_palettes_reach_the_screen(loaded):
    """Both halves draw the same indices; they differ on screen only through the row table."""
    assert loaded['picture']['topBandPixel'] != loaded['picture']['bottomBandPixel']


def test_the_picture_is_running(loaded):
    assert loaded['moving']['vblankBar'], 'nothing moved at VBlank rate'
    assert loaded['moving']['tickBar'], 'nothing moved at tick rate'
    assert loaded['moving']['passMarker'], 'no pass was drawn'


def test_the_emulated_clock_is_steady(loaded):
    assert abs(overlay_number(loaded, 'vblanks/s') - 60) <= 2
    assert abs(overlay_number(loaded, 'passes/s') - 60) <= 2
    assert abs(overlay_number(loaded, 'ticks/s') - 15) <= 1
    assert 'exactly 4: yes' in loaded['overlay']
    assert overlay_number(loaded, 'animation/s') > 30


def test_audio_is_running_after_the_key_press(loaded):
    line = re.search(r'^audio\s+(\w+), (\w+), (\d+) Hz', loaded['overlay'], re.M)
    assert line, loaded['overlay']
    backend, state, rate = line.group(1), line.group(2), int(line.group(3))
    assert backend in ('worklet', 'buffers'), backend
    assert state == 'running'
    assert rate >= 8000
    assert overlay_number(loaded, 'buffer') > 0, 'no audio is queued'
    assert 'underruns' in loaded['overlay']
    assert re.search(r'buffer\s+[\d.]+ ms queued, 0 underruns', loaded['overlay']), loaded['overlay']


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
