"""The sound of a few M4 to M6 scripts as the port mixes it, for listening to.

    .venv/bin/python tests/m8_renders.py                  writes dist/m8-sound/*.wav
    .venv/bin/python tests/m8_renders.py kills_a guns_a   only those

Each script runs through the port in the closed loop of tests/m4compare.py, from the
program's start, with nothing handed over but the entropy and the map list's address; after
every pass the PCM the port mixed for the VBlanks so far is taken at 48 kHz, as the page
takes it, and the whole flight is written as one stereo WAV: channels 0 and 3 left, 1 and 2
right, the Amiga's full width.  The same run compares the port with the headless original
pass by pass, so what is heard is the original's sound as the port reproduces it; the model
has no Amiga filter.  dist/ is not versioned, and neither are these.
"""
import ctypes
import os
import sys
import tempfile
import wave

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, 'tools'))
sys.path.insert(0, HERE)

import conftest                            # noqa: E402
import m4compare                           # noqa: E402
import m6_scripts                          # noqa: E402

OUT = os.path.join(ROOT, 'dist', 'm8-sound')
RATE = 48000

# The flights, and what each lets one hear.
SCRIPTS = {
    'flight': 'the sea in the hold, the lift grinding and its clang, the engine, the take-off',
    'landing': 'the landing and the wheels\' screech on the deck',
    'guns_a': 'the guns over the engine, the ground\'s guns',
    'bomb_b': 'bombs bursting on an island of map b, the soldiers\' screams',
    'oil_d': 'map d: bursts, an enemy fighter\'s engine and guns on the right, the ground\'s guns',
}


def render(ported, name):
    dump_path = os.path.join(tempfile.mkdtemp(prefix='wof-m8-'), name + '.dump')
    pokes = m6_scripts.pokes(name)
    machine = m4compare.record(name, dump_path, pokes=pokes)
    lib = ported.lib
    room = 65536
    buffer = (ctypes.c_int16 * (room * 2))()
    frames = []

    def on_pass(r, memory, head, k):
        while True:
            n = lib.wof_audio_render(buffer, room, RATE)
            frames.append(bytes(memoryview(buffer).cast('B')[:n * 4]))
            if n < room:
                break

    replay = m4compare.Replay(ported, machine, dump_path, mode='closed', pokes=pokes)
    lib.wof_audio_render(buffer, room, RATE)            # the rate, before the first VBlank
    replay.run(on_pass=on_pass)
    os.makedirs(OUT, exist_ok=True)
    path = os.path.join(OUT, name + '.wav')
    with wave.open(path, 'wb') as out:
        out.setnchannels(2)
        out.setsampwidth(2)
        out.setframerate(RATE)
        out.writeframes(b''.join(frames))
    return path, sum(len(f) for f in frames) // 4


def main(names):
    page = open(os.path.join(ROOT, 'dist', 'wof.html'), encoding='utf-8').read()
    ported = conftest.Ported(conftest.payload(page, 'wof-fs'))
    for name in names or list(SCRIPTS):
        path, count = render(ported, name)
        print('%-9s %6.1f s  %s  (%s)' % (name, count / RATE, os.path.relpath(path, ROOT),
                                         SCRIPTS.get(name, '')))


if __name__ == '__main__':
    main(sys.argv[1:])
