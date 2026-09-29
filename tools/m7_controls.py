"""The controls of M7 part 1: each changes the port in one place, builds that into a library
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

# name: (file, the text changed, what it becomes, the test that must catch it, what it is)
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
}


def library(name, where):
    """The port with the control's change, as a native library in `where`."""
    path, old, new, _, _ = CONTROLS[name]
    src = os.path.join(where, 'src')
    shutil.copytree(os.path.join(ROOT, 'src'), src)
    with open(os.path.join(src, os.path.relpath(path, 'src'))) as handle:
        text = handle.read()
    assert text.count(old) == 1, '%s: the text to change is not in %s once' % (name, path)
    with open(os.path.join(src, os.path.relpath(path, 'src')), 'w') as handle:
        handle.write(text.replace(old, new))
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
