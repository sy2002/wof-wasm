"""The controls of M7: each changes the port in one place, builds that into a library
of its own, runs the test that must catch it and reports what the test saw
(re/notes/porting-m7.md, "The controls").

    .venv/bin/python tools/m7_controls.py                 every control, in processes of their own
    .venv/bin/python tools/m7_controls.py extra_life      one

A control's library is built from a copy of src/ in a directory of its own, with the build's
own flags (tools/build.py, CC_NATIVE), and the tests find it through WOF_CORE_LIBRARY
(tests/conftest.py); tests/libwofcore.dylib and src/ are never touched.  A control passes
when its test fails; the report is the test's first lines of findings.
"""
import argparse
import concurrent.futures
import os
import re
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)

import build                                                 # noqa: E402

# name: (file, the text changed, what it becomes, the test that must catch it, what it is);
# a change in two places gives a list of (text, what it becomes) and None.
CONTROLS = {
    'extra_life': (
        'src/front.c',
        '                wof_g.lives++;                                /* 0x01015C: addq.b */',
        '                ;',
        'tests/test_campaign.py::test_every_tick_and_pass_agrees_in_the_closed_loop[ships_j]',
        'the extra life of a promotion not given (main 0x01015C)'),
    'promotion_early': (
        'src/targets.c',
        '''    if ((int16_t)word_at(0x025548u + 2u * (uint32_t)(uint16_t)wof_g.rank_played) >=
        (int16_t)wof_g.mission_number) {''',
        '''    if ((int16_t)word_at(0x025548u + 2u * (uint32_t)(uint16_t)wof_g.rank_played) >
        (int16_t)wof_g.mission_number) {''',
        'tests/test_campaign.py::test_every_tick_and_pass_agrees_in_the_closed_loop[ships_j]',
        'the promotion one mission early: mission_won promotes when the rank\'s last mission '
        'is the next one (bgt for bge at 0x0156AE)'),
    'next_map': (
        'src/front.c',
        '''            wof_dashboard_invalidate();
            wof_map_load();''',
        '''            wof_dashboard_invalidate();
            wof_g.mission_number++, wof_map_load(), wof_g.mission_number--;''',
        'tests/test_campaign.py::test_every_tick_and_pass_agrees_in_the_closed_loop[ships_j]',
        'the next mission\'s map one further (main 0x010168)'),
    'raw_byte': (
        'src/dialog.c',
        '            b = memory_byte(addr + i);',
        '            b = (uint8_t)(memory_byte(addr + i) + (addr + i == 0x0253BFu));',
        'tests/test_campaign.py::test_the_saved_file_is_the_originals_but_for_its_pointers[save_a]',
        'a byte of the saved file\'s raw part one off: rank_played\'s low byte'),
    'block_short': (
        'src/dialog.c',
        '    put(0x025500u, (uint16_t)(wof_g.soldier_count << 3), 1);',
        '    put(0x025500u, (uint16_t)((wof_g.soldier_count - 1u) << 3), 1);',
        'tests/test_campaign.py::test_the_saved_file_is_the_originals_but_for_its_pointers[save_a]',
        'the soldiers\' block of the saved file a record short'),
    'night_by_day': (
        'src/mission.c',
        '    if ((int8_t)map > 6) {',
        '    if ((int8_t)map >= 0) {',
        'tests/test_campaign.py::test_every_tick_and_pass_agrees_in_the_closed_loop[chain_a]',
        'choose_night\'s night branch taken by day (the map number above 6, 0x011214)'),
    # M7 part 2: the loaded game and the demo.
    'derived_as_read': (
        'src/dialog.c',
        """        p->shape = wof_shape_handle(WOF_C_HELLCAT,
                                    wof_shape_find(&wof_assets.c[WOF_C_HELLCAT], p->frame_name));""",
        """        p->shape = (uint16_t)(wof_fs_find(name, 0)[0x3CE + 2] << 8 |
                              wof_fs_find(name, 0)[0x3CE + 3]);""",
        'tests/test_loader.py::test_the_derived_fields_are_what_the_originals_first_tick_makes_of_them[load_disk]',
        'a derived pointer field left as read from the file: the player\'s shape the low word '
        'of the file\'s long at +0x3CE'),
    'raw_short': (
        'src/dialog.c',
        '    uint32_t n = load_take(len);',
        '    uint32_t n = load_take(len - (addr == 0x024CAEu ? 2u : 0u));',
        'tests/test_loader.py::test_a_loaded_game_agrees_in_the_closed_loop[load_disk]',
        'the raw range read two bytes short'),
    'table_short': (
        'src/dialog.c',
        '    uint32_t n = load_take(len);',
        '    uint32_t n = load_take(len -= (addr == 0x025500u ? 8u : 0u));',
        'tests/test_loader.py::test_a_loaded_game_agrees_in_the_closed_loop[load_disk]',
        'a table read one record short: the soldiers'),
    'demo_byte_early': (
        'src/input.c',
        [('    uint16_t d0;                        /* what the original\'s D0 holds on the way */',
          '    uint16_t d0; static uint16_t stale_; stale_ = wof_g.input_byte;'),
         ('        demo_store(wof_g.demo_index, (uint8_t)wof_g.input_byte);',
          '        demo_store(wof_g.demo_index, (uint8_t)stale_);')],
        None,
        'tests/test_demo.py::test_a_demo_agrees_in_the_closed_loop[demo_record]',
        'the demo\'s byte stored before read_joystick\'s sample rather than after'),
    'spin_one': (
        'src/front.c',
        '    while (wof_g.demo_bytes_owed)                                    /* 0x0114E0 */',
        '    while (wof_g.demo_bytes_owed > 1)                                /* 0x0114E0 */',
        'tests/test_demo.py::test_a_demo_agrees_in_the_closed_loop[demo_play_ff]',
        'run_queued_ticks\' spin waiting for one byte rather than two'),
    # The end at the count cannot be the control: a playback takes its entries in pairs
    # from entry 1, so entry 0x1386 is the second of its pass and an end one entry later
    # sets quit_flag in the same pass with the same index (re/notes/demo.md).  The 0xFF end
    # is: the 0xFF played as a neutral byte and the end taken at the entry after it.
    'end_late': (
        'src/input.c',
        '        d0 = demo_byte(d1);',
        '        d0 = d1 && demo_byte((uint16_t)(d1 - 1u)) == 0xFFu ? 0xFFu'
        ' : demo_byte(d1) == 0xFFu ? 0u : demo_byte(d1);',
        'tests/test_demo.py::test_a_demo_agrees_in_the_closed_loop[demo_play_ff]',
        'the playback\'s end one entry late: the 0xFF taken as a neutral byte, the end at the '
        'entry after it'),
}


def library(name, where):
    """The port with the control's change, as a native library in `where`."""
    path, old, new, _, _ = CONTROLS[name]
    src = os.path.join(where, 'src')
    shutil.copytree(os.path.join(ROOT, 'src'), src)
    with open(os.path.join(src, os.path.relpath(path, 'src'))) as handle:
        text = handle.read()
    for was, becomes in (old if isinstance(old, list) else [(old, new)]):
        assert text.count(was) == 1, '%s: the text to change is not in %s once' % (name, path)
        text = text.replace(was, becomes)
    with open(os.path.join(src, os.path.relpath(path, 'src')), 'w') as handle:
        handle.write(text)
    sources = [os.path.join(src, f) for f in os.listdir(src) if f.endswith('.c')]
    sources += [os.path.join(src, 'gen', f) for f in os.listdir(os.path.join(src, 'gen'))
                if f.endswith('.c')]
    flags = [f if f != build.SRC else src for f in build.CC_NATIVE]
    out = os.path.join(where, 'libwofcore.dylib')
    subprocess.run(['clang'] + flags + ['-o', out] + sorted(sources) +
                   [os.path.join(ROOT, 'tests', 'shim.c')], check=True, cwd=ROOT)
    return out


def run(name):
    """(name, caught, the test's findings) for one control."""
    where = tempfile.mkdtemp(prefix='wof-control-%s-' % name)
    try:
        lib = library(name, where)
        test = CONTROLS[name][3]
        env = dict(os.environ, WOF_CORE_LIBRARY=lib)
        done = subprocess.run([sys.executable, '-m', 'pytest', test, '--slow', '-q', '-x',
                               '-p', 'no:cacheprovider'],
                              cwd=ROOT, env=env, capture_output=True, text=True)
        text = done.stdout + done.stderr
        found = [line.strip() for line in text.splitlines()
                 if re.match(r'\s*E\s', line)][:12]
        return name, done.returncode != 0, found
    finally:
        shutil.rmtree(where, ignore_errors=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    parser.add_argument('names', nargs='*', default=sorted(CONTROLS))
    parser.add_argument('--jobs', type=int, default=6)
    args = parser.parse_args()
    failed = 0
    with concurrent.futures.ProcessPoolExecutor(max_workers=args.jobs) as pool:
        for name, caught, found in pool.map(run, args.names):
            print('%-16s %s  (%s)' % (name, 'caught' if caught else 'NOT CAUGHT', CONTROLS[name][4]))
            for line in found:
                print('    ' + line[:300])
            failed += not caught
    return 1 if failed else 0


if __name__ == '__main__':
    sys.exit(main())
