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

from picture import (assert_the_blocks_have_hard_edges,
                     assert_the_picture_lies_where_the_dom_says,
                     assert_the_screenshot_is_the_picture,
                     big_enough_blocks)
from conftest import (ROOT, assert_a_moment_hidden_changes_nothing,
                      assert_a_real_absence_comes_back_paused,
                      assert_an_enemy_aircraft_comes_up,
                      assert_fullscreen_keeps_the_page_going,
                      assert_the_mission_is_flown_from_the_keyboard,
                      assert_a_tap_as_soon_as_the_hold_appears_steps_once,
                      assert_the_weapon_menu_steps_once_per_tap,
                      assert_a_modifier_alone_starts_nothing,
                      assert_the_box_has_the_display_aspect,
                      assert_the_box_is_the_largest_that_fits,
                      assert_the_canvas_shows_the_picture,
                      assert_the_next_real_key_starts_the_sound,
                      assert_the_screenshot_shows_the_picture,
                      assert_the_stick_keys_give_the_bits_of_the_spec,
                      assert_web_audio_waits_for_a_gesture,
                      assert_the_title_is_heard, assert_keym_silences_the_effects, assert_the_mission_is_heard,
                      measured_box, overlay_audio, overlay_number,
                      window_could_not_enter_fullscreen)

# What the shell was showing when each measurement was taken.
STANDARD_OF = {'default': 'PAL', 'ntsc': 'NTSC', 'palAgain': 'PAL', 'wide': 'PAL',
               'tall': 'PAL', 'small': 'PAL', 'ranks': 'PAL'}

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


def test_the_up_key_is_the_stick_pushed_forward(loaded_firefox):
    assert_the_stick_keys_give_the_bits_of_the_spec(loaded_firefox)


def test_firefox_is_silenced_by_its_profile(loaded_firefox):
    """The page plays the game's sounds, and these runs happen on a machine somebody is working at.
    The profile the harness builds sets media.volume_scale, which turns Firefox's output down
    from outside the page so that the shipped configuration is still what the audio tests
    see.  What is read back here is the preference Firefox itself wrote out when it shut
    down; that it really is inaudible is the one part a person has to confirm."""
    assert loaded_firefox['volumeScale'] == 'user_pref("media.volume_scale", "0.0");', (
        'Firefox did not take the preference that silences it: %r'
        % loaded_firefox['volumeScale'])


def test_the_picture_is_the_core_geometry(loaded_firefox):
    picture = loaded_firefox['picture']
    assert (picture['width'], picture['height']) == (640, 214)
    assert picture['colours'] >= 8, 'the rank selection has almost no colours in it'


def test_the_front_end_runs_on_the_page(loaded_firefox):
    """The same walk as in Chrome: the story scroller, the publisher logo when fire ends it,
    the title, and the rank selection when a second fire skips the rest."""
    front = loaded_firefox['front']
    assert front['scroller']['colours'] >= 2, 'the story scroller drew nothing'
    for name in ('logo', 'title', 'ranks'):
        assert front[name]['colours'] >= 8, (name, front[name]['colours'])
    hashes = [front[name]['hash'] for name in ('scroller', 'logo', 'title', 'ranks')]
    assert len(set(hashes)) == 4, 'two of the four screens are the same picture'


def test_a_front_end_screen_leaves_the_rows_below_it_black(loaded_firefox):
    """One viewport of 200 lines at line 0; the fourteen below it go through the blank
    palette.  The play screen's three stacked viewports arrive with M4."""
    rows = loaded_firefox['picture']['rows']
    assert rows['playfield'] > 0, rows
    assert rows['blankAboveTicker'] == 0 and rows['ticker'] == 0, rows


def test_the_emulated_clock_is_steady(loaded_firefox):
    """PAL by default: 50 VBlanks, 50 passes and 12.5 ticks a second."""
    overlay = loaded_firefox['overlay']
    assert abs(overlay_number(overlay, 'vblanks/s') - 50) <= 2
    assert abs(overlay_number(overlay, 'passes/s') - 50) <= 2
    assert abs(overlay_number(overlay, 'ticks/s') - 12.5) <= 1
    assert 'exactly 4: yes' in overlay


def test_the_ntsc_standard_runs_the_clock_at_60(loaded_firefox):
    ntsc = loaded_firefox['box']['ntsc']['overlay']
    assert abs(overlay_number(ntsc, 'vblanks/s') - 60) <= 2
    assert abs(overlay_number(ntsc, 'passes/s') - 60) <= 2
    assert abs(overlay_number(ntsc, 'ticks/s') - 15) <= 1
    back = loaded_firefox['box']['palAgain']['overlay']
    assert abs(overlay_number(back, 'vblanks/s') - 50) <= 2
    assert abs(overlay_number(back, 'ticks/s') - 12.5) <= 1


# ------------------------------------------------------------------ the picture on the page

def test_the_picture_is_shown_in_the_display_aspect(loaded_firefox):
    for name, standard in STANDARD_OF.items():
        assert_the_box_has_the_display_aspect(loaded_firefox['box'][name]['geometry'],
                                              standard, name)


def test_the_picture_fills_the_window(loaded_firefox):
    for name, standard in STANDARD_OF.items():
        assert_the_box_is_the_largest_that_fits(loaded_firefox['box'][name]['geometry'],
                                                standard, name)


def test_the_picture_follows_a_resize(loaded_firefox):
    seen = {}
    for name in ('default', 'wide', 'tall', 'small'):
        geometry = loaded_firefox['box'][name]['geometry']
        seen[name] = (geometry['window']['width'], geometry['window']['height'])
    assert len(set(seen.values())) == len(seen), seen

    wide = measured_box(loaded_firefox['box']['wide']['geometry'])
    assert abs(wide['height'] - wide['available_height']) <= 1 and wide['width'] < wide['available_width']
    tall = measured_box(loaded_firefox['box']['tall']['geometry'])
    assert abs(tall['width'] - tall['available_width']) <= 1 and tall['height'] < tall['available_height']


def test_the_canvas_on_the_page_shows_the_picture(loaded_firefox):
    for name in STANDARD_OF:
        assert_the_canvas_shows_the_picture(loaded_firefox['box'][name]['display'], name)


def test_a_screenshot_shows_the_picture_in_the_box_and_black_around_it(loaded_firefox):
    for name in ('default', 'wide', 'ranks'):
        seen = loaded_firefox['box'][name]
        assert_the_screenshot_shows_the_picture(seen['screenshot'], seen['geometry'],
                                                seen['display'], name)


def measurable(report):
    """The looks whose screenshot can be judged pixel by pixel: a framebuffer pixel has to be
    shown as at least three device pixels in each direction.  A real devicePixelRatio of 2
    gives that at the size the window opens at; at 1 it takes a large viewport, which is why
    the harness makes one."""
    return [name for name, seen in report['box'].items()
            if seen.get('screenshot') and seen.get('sourcePng')
            and big_enough_blocks(seen['geometry'], seen['screenshot'])]


def check_the_picture(report, note):
    names = measurable(report)
    assert names, ('no screenshot in this run shows the framebuffer large enough to judge '
                   'it pixel by pixel: %s' % list(report['box']))
    for name in names:
        seen = report['box'][name]
        where = '%s %s' % (note, name)
        assert_the_screenshot_is_the_picture(seen['sourcePng'], seen['screenshot'],
                                             seen['geometry'], where)
        assert_the_picture_lies_where_the_dom_says(seen['sourcePng'], seen['screenshot'],
                                                   seen['geometry'], where)
        assert_the_blocks_have_hard_edges(seen['sourcePng'], seen['screenshot'],
                                          seen['geometry'], where)
    return names


def test_the_screenshot_is_the_picture_pixel_for_pixel(loaded_firefox):
    """Every framebuffer pixel against the screenshot, where it lies, and how hard its edges
    are - the three the display box measured off the DOM cannot answer."""
    check_the_picture(loaded_firefox, 'headless')


def test_the_hint_bar_shares_the_diagnostics_key(loaded_firefox):
    assert loaded_firefox['hintVisibleWithOverlay']
    for name in ('default', 'wide', 'ranks'):
        assert loaded_firefox['box'][name]['hintVisible'] is False, name


def test_audio_is_running_after_the_key_press(loaded_firefox):
    """The same worklet from a data: URL that Chrome takes.  Underruns are not asserted:
    Firefox under WebDriver has no real output device and starves the graph at start-up."""
    backend, state, rate = overlay_audio(loaded_firefox['overlay'])
    assert backend == 'worklet', 'Firefox fell back to %r' % backend
    assert state == 'running'
    assert rate >= 8000
    assert overlay_number(loaded_firefox['overlay'], 'buffer') > 0, 'no audio is queued'


def test_a_mission_is_flown_from_the_keyboard(loaded_firefox):
    """T7 in Firefox: the lift, the roll, the take-off and the climb, the pause, the flip,
    and the flip still on after the page is loaded again."""
    flight = loaded_firefox['flight']
    assert_the_mission_is_flown_from_the_keyboard(flight)
    after = flight['afterReload']
    assert after['stored'] == '1' and after['player']['flip'], after


def test_the_front_end_plays_its_music(loaded_firefox):
    """M8 in Firefox: the key that started the sound came in the story scroller, whose song
    plays from the sixth VBlank; the PCM the shell has taken since through the worklet is not
    silent."""
    assert_the_title_is_heard(loaded_firefox['overlay'], 'worklet')


def test_keym_in_flight_silences_the_effects(loaded_firefox):
    """M8 in Firefox: KeyM in flight, the game's Control-S, stops the effects and a second
    press brings them back."""
    assert_keym_silences_the_effects(loaded_firefox['flight']['mute'])


def test_the_mission_sounds_through_the_worklet(loaded_firefox):
    """M8 in Firefox: after the hold, the lift, the take-off, the guns and a weapon's burst,
    the PCM that went through the AudioWorklet is not silent."""
    assert_the_mission_is_heard(loaded_firefox['flight']['pcm'], 'worklet')


def test_the_mission_sounds_through_the_scheduled_buffers(loaded_firefox):
    """M8 in Firefox: the enemy flight runs with ?audio=buffers, and its sounds went through
    the fallback as PCM that is not silent."""
    assert_the_mission_is_heard(loaded_firefox['enemy']['overlay'], 'buffers')


def test_an_enemy_aircraft_comes_up_on_the_page(loaded_firefox, ported):
    """M6 in Firefox: the second rank's first mission, map d, flown from the hold to the
    airfield, whose fighter the framebuffer shows over the island."""
    assert_an_enemy_aircraft_comes_up(loaded_firefox['enemy'], ported)


def test_a_tap_as_soon_as_the_hold_appears_steps_once(loaded_firefox):
    """The keyboard assist keeps a press made in the weapon menu's first fifteen ticks."""
    assert_a_tap_as_soon_as_the_hold_appears_steps_once(loaded_firefox['flight']['early'])


def test_a_tap_as_soon_as_the_hold_appears_steps_once_in_a_visible_window(loaded_firefox_visible):
    assert_a_tap_as_soon_as_the_hold_appears_steps_once(loaded_firefox_visible['flight']['early'])


def test_the_weapon_menu_steps_once_per_tap(loaded_firefox):
    """The keyboard assist in Firefox, keys through the driver."""
    assert_the_weapon_menu_steps_once_per_tap(loaded_firefox['flight']['weapon'])


def test_the_weapon_menu_steps_once_per_tap_in_a_visible_window(loaded_firefox_visible):
    assert_the_weapon_menu_steps_once_per_tap(loaded_firefox_visible['flight']['weapon'])


def test_a_mission_is_flown_in_a_visible_window(loaded_firefox_visible):
    """The same in a real window, where the canvas is accelerated."""
    flight = loaded_firefox_visible['flight']
    assert_the_mission_is_flown_from_the_keyboard(flight)
    after = flight['afterReload']
    assert after['stored'] == '1' and after['player']['flip'], after


def test_the_mission_sounds_in_a_visible_window(loaded_firefox_visible):
    """M8 in a visible Firefox window: the worklet's PCM of the front end, whose music plays,
    and of the flight, and the scheduled buffers' of the enemy flight are not silent; KeyM in
    flight silences the effects."""
    assert_the_title_is_heard(loaded_firefox_visible['overlay'], 'worklet')
    assert_keym_silences_the_effects(loaded_firefox_visible['flight']['mute'])
    assert_the_mission_is_heard(loaded_firefox_visible['flight']['pcm'], 'worklet')
    assert_the_mission_is_heard(loaded_firefox_visible['enemy']['overlay'], 'buffers')


def test_an_enemy_aircraft_comes_up_in_a_visible_window(loaded_firefox_visible, ported):
    """The same in a visible Firefox window: map d's airfield's fighter over the island."""
    assert_an_enemy_aircraft_comes_up(loaded_firefox_visible['enemy'], ported)


def test_the_visible_canvas_shows_the_picture(loaded_firefox_visible):
    """The one check headless cannot make.  In GPU-composited Firefox an accelerated 2D
    canvas never shows what putImageData wrote and reads back as a single colour, which is
    the black screen a player would see; web/video.js asks for a software-backed canvas to
    avoid it.  This is the canvas putImageData writes to."""
    picture = loaded_firefox_visible['picture']
    assert picture['colours'] > 1, 'the shipped canvas reads back as one colour'
    assert picture['colours'] >= 8
    rows = loaded_firefox_visible['picture']['rows']
    assert rows['playfield'] > 0, rows


def test_the_visible_page_shows_the_picture_it_was_given(loaded_firefox_visible):
    """The canvas on the page, not the one putImageData writes to: it is drawn into and
    composited, which is the path the fault above lives on, and in a real window it is the
    accelerated one.  At the size the window opens at and after a resize."""
    for name in ('default', 'wide'):
        assert_the_canvas_shows_the_picture(loaded_firefox_visible['box'][name]['display'], name)


def test_the_visible_compositor_shows_the_picture(loaded_firefox_visible):
    """And what the compositor really puts on the screen, which no canvas read-back can
    answer for: inside the box the picture, outside it black."""
    for name in ('default', 'wide', 'ranks'):
        seen = loaded_firefox_visible['box'][name]
        assert_the_screenshot_shows_the_picture(seen['screenshot'], seen['geometry'],
                                                seen['display'], name)


def test_the_visible_screenshot_is_the_picture_pixel_for_pixel(loaded_firefox_visible):
    """The same three on a real window at this machine's real devicePixelRatio, which is the
    one place in the suite where the whole path - accelerated canvas, compositor, screen
    density - is the player's."""
    check_the_picture(loaded_firefox_visible, 'visible')


def test_the_visible_window_shows_it_in_the_display_aspect(loaded_firefox_visible):
    for name in ('default', 'wide'):
        assert_the_box_has_the_display_aspect(
            loaded_firefox_visible['box'][name]['geometry'], 'PAL', name)
        assert_the_box_is_the_largest_that_fits(
            loaded_firefox_visible['box'][name]['geometry'], 'PAL', name)


# ------------------------------------------------------ fullscreen and a page hidden for a moment
#
# The owner's finding of 2026-09-26 (tests/pagefullscreen.mjs, tests/conftest.py): Firefox put
# into fullscreen during a mission, the picture stood still and the sound was gone from then
# on.  Driven in a tab of its own from the hold, where the sea plays for ever.

def test_a_moment_hidden_leaves_the_mission_and_its_sound_going(loaded_firefox):
    assert_a_moment_hidden_changes_nothing(loaded_firefox['fullscreen'])


def test_a_real_absence_comes_back_paused(loaded_firefox):
    assert_a_real_absence_comes_back_paused(loaded_firefox['fullscreen'])


def test_fullscreen_keeps_the_clock_the_picture_and_the_sound(loaded_firefox):
    """The browser's own fullscreen, by the driver's window-state command; headless Firefox
    gives the window the size of its virtual screen."""
    report = loaded_firefox['fullscreen']
    assert_fullscreen_keeps_the_page_going(report, report['before']['size'])


def test_a_moment_hidden_leaves_the_mission_and_its_sound_going_in_a_visible_window(
        loaded_firefox_visible):
    assert_a_moment_hidden_changes_nothing(loaded_firefox_visible['fullscreen'])


def test_a_real_absence_comes_back_paused_in_a_visible_window(loaded_firefox_visible):
    assert_a_real_absence_comes_back_paused(loaded_firefox_visible['fullscreen'])


def test_fullscreen_keeps_the_clock_the_picture_and_the_sound_in_a_visible_window(
        loaded_firefox_visible):
    """The same in a real window, where fullscreen is macOS's own: the window moves into a
    space of its own at the screen's size and density."""
    report = loaded_firefox_visible['fullscreen']
    if window_could_not_enter_fullscreen(report):
        pytest.skip('the window did not enter fullscreen (the driver answered %r) and the page '
                    'was hidden throughout: on macOS a window cannot move into its fullscreen '
                    'space while the screen is locked' % report['enter'])
    assert_fullscreen_keeps_the_page_going(report, report['before']['size'])
