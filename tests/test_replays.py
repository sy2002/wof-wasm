"""SPEC.md section 8, "Whole game, replays": a demo the port recorded, kept in tests/replays/
with the port's state hashes, replayed as a regression test in the native core and in
Node's WebAssembly (re/notes/demo.md).

A replay file holds the seed wof_init was given, the fade setting, the files laid over the
disk before the start (wofdemo and wofdemo.seed, as the port's demo_end wrote them), the
schedule of controller bytes and keys VBlank by VBlank, and after every input sample
(wof_tick_count) the first 16 hex digits of the SHA-256 of the saved state.  The schedule
leaves the rank selection alone until the attract mode plays the demo, so the stored hashes
are the playback's, which the seed file makes the recording's own draws.

    WOF_REPLAY_WRITE=1 .venv/bin/python -m pytest tests/test_replays.py   records the demo anew
"""
import hashlib
import json
import os
import subprocess
import sys

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, 'tools'))
sys.path.insert(0, HERE)

REPLAYS = os.path.join(HERE, 'replays')
NODE_SCRIPT = os.path.join(HERE, 'replay_wasm.mjs')
WASM = os.path.join(ROOT, 'dist', 'core.wasm')
SEED, FADES = 1, 2

# The recording: fire tapped three VBlanks in thirty until the mission (rank 0, its
# briefing), then a take-off and a flight east, then Control-R, after which demo_end writes
# wofdemo and wofdemo.seed.  The playback: the title left with two taps, then nothing.
UP, DOWN, RIGHT, LEFT, FIRE = 1, 2, 4, 8, 16
CONTROL_R = (0x13, 0x0008)
RECORD = ([[27, 0], [3, FIRE]] * 20 + [[3, FIRE], [460, RIGHT], [173, RIGHT | UP],
          [400, RIGHT], [4, RIGHT | FIRE], [300, RIGHT], [1, 0, [CONTROL_R]], [300, 0]])
PLAYBACK = [[27, 0], [3, FIRE], [27, 0], [3, FIRE], [9000, 0]]


def vblanks(schedule):
    for entry in schedule:
        n, raw = entry[0], entry[1]
        keys = entry[2] if len(entry) > 2 else []
        for i in range(n):
            yield raw, (keys if i == 0 else [])


def digest(state):
    return hashlib.sha256(state).hexdigest()[:16]


def saved_state(ported):
    """The core's save state (wof_state_save), the bytes the WebAssembly side hashes."""
    import ctypes
    lib = ported.lib
    lib.wof_state_size.restype = ctypes.c_uint32
    lib.wof_state_save.argtypes = [ctypes.c_void_p]
    buffer = ctypes.create_string_buffer(lib.wof_state_size())
    lib.wof_state_save(buffer)
    return buffer.raw


def run_native(ported, schedule, files=(), record=False):
    """Drive the native core VBlank by VBlank as the shell does; returns (hashes after every
    input sample, the final hash, the files it wrote)."""
    lib = ported.lib
    ported.reset_core(seed=SEED, fade_vblanks=FADES)
    ported.fs_reset()
    for name, data in dict(files).items():
        assert ported.fs_write(name, data), name
    if record:
        lib.wof_dev_demo_record(1)
    import ctypes
    lib.wof_dev_game.restype = ctypes.POINTER(ctypes.c_int32)
    hashes, last = [], lib.wof_tick_count()
    modes = set()
    for raw, keys in vblanks(schedule):
        for code, qualifier in keys:
            lib.wof_key(code, qualifier)
        lib.wof_vblank(raw)
        lib.wof_pass()
        modes.add(lib.wof_dev_game()[5])
        now = lib.wof_tick_count()
        if now != last:
            hashes.append([now, digest(saved_state(ported))])
            last = now
    final = digest(saved_state(ported))
    written = dict(ported.fs_written())
    ported.reset_core()
    ported.fs_reset()
    run_native.modes = modes
    return hashes, final, written


def make(ported):
    """Record the demo with the port and its playback's hashes: tests/replays/demo_a.json."""
    _, _, written = run_native(ported, RECORD, record=True)
    assert 2 in run_native.modes, 'the recording never ran'
    files = {n: written[n] for n in ('wofdemo', 'wofdemo.seed')}
    entries = files['wofdemo'].index(0xFF, 1)
    assert entries > 200, 'the demo holds %d entries' % entries
    hashes, final, _ = run_native(ported, PLAYBACK, files)
    assert 1 in run_native.modes, 'the attract mode played nothing'
    make.entries = entries
    replay = {'seed': SEED, 'fades': FADES,
              'files': {n: d.hex() for n, d in files.items()},
              'schedule': PLAYBACK, 'hashes': hashes, 'final': final}
    os.makedirs(REPLAYS, exist_ok=True)
    with open(os.path.join(REPLAYS, 'demo_a.json'), 'w') as handle:
        json.dump(replay, handle, separators=(',', ':'))
        handle.write('\n')
    return replay


def stored():
    if os.environ.get('WOF_REPLAY_WRITE') == '1' or not os.path.isdir(REPLAYS):
        return []
    return sorted(f for f in os.listdir(REPLAYS) if f.endswith('.json'))


def load(name):
    with open(os.path.join(REPLAYS, name)) as handle:
        return json.load(handle)


@pytest.mark.skipif(os.environ.get('WOF_REPLAY_WRITE') != '1', reason='WOF_REPLAY_WRITE=1 records')
def test_record_the_replays(ported):
    replay = make(ported)
    assert len(replay['hashes']) > 500
    print('demo entries', make.entries, 'samples hashed', len(replay['hashes']))


@pytest.mark.parametrize('name', stored())
def test_a_stored_replay_gives_its_hashes_in_the_native_core(ported, name):
    """The native core, from wof_init on with the replay's seed and files, gives the stored
    hash after every input sample and at the end."""
    replay = load(name)
    files = {n: bytes.fromhex(d) for n, d in replay['files'].items()}
    hashes, final, _ = run_native(ported, replay['schedule'], files)
    first = next((i for i, (a, b) in enumerate(zip(hashes, replay['hashes'])) if a != b), None)
    assert first is None and len(hashes) == len(replay['hashes']), (
        'first difference at %r of %d' % (first, len(replay['hashes'])))
    assert final == replay['final']


@pytest.mark.parametrize('name', stored())
def test_a_stored_replay_gives_its_hashes_in_webassembly(built, blob_file, name):
    """The release core.wasm in Node, driven the same way, gives the same hashes."""
    finished = subprocess.run(['node', NODE_SCRIPT, WASM, str(blob_file),
                               os.path.join(REPLAYS, name)],
                              capture_output=True, text=True, check=True, cwd=ROOT)
    got = json.loads(finished.stdout)
    replay = load(name)
    first = next((i for i, (a, b) in enumerate(zip(got['hashes'], replay['hashes'])) if a != b),
                 None)
    assert first is None and len(got['hashes']) == len(replay['hashes']), (
        'first difference at %r of %d' % (first, len(replay['hashes'])))
    assert got['final'] == replay['final']
