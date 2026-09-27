"""A save state in the middle of a mission (M4, V7).

The core is taken into its first mission by the fire button alone and saved some passes
into it; running on from the save, from the loaded save, and from the save loaded into a
fresh core with another seed must give the same state and the same picture, on the native
library and on the WebAssembly core - and the two targets must agree with each other.
"""
import ctypes
import hashlib
import json
import os
import sys

import pytest

from conftest import ROOT, WASM, run

sys.path.insert(0, os.path.join(str(ROOT), 'tools'))
import headless                  # noqa: E402
import m4_scripts                # noqa: E402
import pass_observe              # noqa: E402

AFTER = 400                      # VBlanks run on from the save
INTO = 160                       # VBlanks into the mission when the state is saved


def raw(vblank):
    return 0x10 if vblank % 30 < 3 else 0


def digest(data):
    return hashlib.sha256(data).hexdigest()


def drive(ported, start, count):
    for v in range(start, start + count):
        ported.vblank(raw(v))
        ported.pass_()


def native_state(ported):
    lib = ported.lib
    size = lib.wof_state_size()
    buf = ctypes.create_string_buffer(size)
    lib.wof_state_save(buf)
    return buf.raw


def native_load(ported, data):
    ported.lib.wof_state_load(ctypes.create_string_buffer(data, len(data)))


def frame(ported):
    lib = ported.lib
    lib.wof_framebuffer.restype = ctypes.c_void_p
    size = lib.wof_framebuffer_width() * lib.wof_framebuffer_height()
    return digest(ctypes.string_at(lib.wof_framebuffer(), size))


def test_a_state_saved_in_a_mission_continues_identically(ported, blob_file):
    lib = ported.lib
    lib.wof_state_size.restype = ctypes.c_uint32
    lib.wof_state_save.argtypes = [ctypes.c_void_p]
    lib.wof_state_load.argtypes = [ctypes.c_void_p]

    # What earlier tests may have left in the library's statics, set back to the defaults
    # the WebAssembly core runs with: the fades, the pass rate, no tick waits, no pokes.
    lib.wof_set_fade_vblanks(2)
    lib.wt_set_vblanks_per_pass(2)
    lib.wt_pokes_clear()
    ported.reset_core(seed=1)
    vblank = 0
    while ported.mission_count() == 0 and vblank < 6000:
        drive(ported, vblank, 1)
        vblank += 1
    assert ported.mission_count() == 1, 'no mission after %d VBlanks' % vblank
    drive(ported, vblank, INTO)
    before = vblank + INTO

    saved = native_state(ported)
    saved_frame = frame(ported)
    drive(ported, before, AFTER)
    straight = (digest(native_state(ported)), frame(ported))
    assert ported.mission_count() == 1

    native_load(ported, saved)
    assert frame(ported) == saved_frame, 'the picture after a load is not the saved one'
    drive(ported, before, AFTER)
    assert (digest(native_state(ported)), frame(ported)) == straight, 'native: replay differs'

    ported.reset_core(seed=4711)
    drive(ported, 0, 50)
    native_load(ported, saved)
    assert frame(ported) == saved_frame
    drive(ported, before, AFTER)
    assert (digest(native_state(ported)), frame(ported)) == straight, 'native: foreign core differs'
    ported.reset_core()

    out = run(['node', str(ROOT / 'tests' / 'state_wasm.mjs'), str(WASM), str(blob_file),
               str(before), str(AFTER)])
    wasm = json.loads(out.stdout)
    assert wasm['loadedFrame'] == wasm['savedFrame'] == wasm['foreignFrame']
    assert wasm['straight'] == wasm['replayed'] == wasm['foreign'], wasm
    assert wasm['saved'] == digest(saved), 'the two targets saved different states'
    assert wasm['savedFrame'] == saved_frame
    assert (wasm['straight']['state'], wasm['straight']['frame']) == straight


# ------------------------------------------------------------------ T5: the cases of part 2

def expand(raw_entries):
    """A script's raw schedule as one controller byte per VBlank, and its keys as
    (vblank, code, qualifier), each delivered before its VBlank as the harness does."""
    raw, keys = [], []
    for entry in raw_entries:
        state = headless.raw_state(entry[1])
        if len(entry) > 2:
            keys += [(len(raw), code, qualifier) for code, qualifier in headless.key_events(entry[2])]
        raw += [state] * entry[0]
    return raw, keys


def drive_schedule(ported, raw, keys, start, count, fed=None):
    """The script's VBlanks `start` to `start + count`; `fed`, when given, takes every VBlank
    as it was given, (raw, keys), the fades' waits included."""
    by = {}
    for v, code, qualifier in keys:
        by.setdefault(v, []).append((code, qualifier))
    for v in range(start, start + count):
        while ported.music_spin():
            # The music waits for a fade and the script with it, the VBlanks carrying no
            # input, as in the headless original (re/notes/headless.md, "The fade's wait").
            ported.vblank(0)
            ported.pass_()
            if fed is not None:
                fed.append((0, []))
        for code, qualifier in by.get(v, ()):
            ported.key(code, qualifier)
        ported.vblank(raw[v] if v < len(raw) else 0)
        ported.pass_()
        if fed is not None:
            fed.append((raw[v] if v < len(raw) else 0, by.get(v, [])))


ESCAPE = 0x45


def case_schedule(name):
    """(raw, keys, a function that says whether a VBlank is the one to save at)."""
    if name == 'left':
        # Flying left after the first turn of the turns script: hellcat.shp's frames are
        # mirrored then, which is state the containers hold (SPEC 7.2).
        raw, keys = expand(m4_scripts.TURNS)
        at = m4_scripts.length(m4_scripts.PILOT) + 190 + 124 + 79 + 40
        return raw, keys, lambda ported, v: v == at
    if name == 'restart':
        # Inside the WaitTOF loop of the restart after the lost script's crash: the tick is
        # waiting, halfway through its twenty VBlanks.
        raw, keys = expand(pass_observe.script('lost')['raw'])
        return raw, keys, lambda ported, v: ported.g('g_027452') == 10
    if name == 'paused':
        # The flight script with Escape in the climb, saved while paused, and Escape again
        # 150 VBlanks after the save.
        raw, keys = expand(pass_observe.script('flight')['raw'])
        at = m4_scripts.length(pass_observe.FRONT) + 900
        keys = keys + [(at - 60, ESCAPE, 0), (at + 150, ESCAPE, 0)]
        return raw, keys, lambda ported, v: v == at
    raise KeyError(name)


@pytest.mark.parametrize('name', ['left', 'restart', 'paused'])
def test_a_state_saved_in_a_flight_continues_identically(ported, blob_file, tmp_path, name):
    """T5: a state saved flying left with the shapes mirrored, inside the restart's waits in a
    tick, and while paused; loaded into the same core and into a fresh core with another
    seed, the state, the picture and the next 400 VBlanks are the same, on the native
    library and on the WebAssembly core, and the two targets agree."""
    lib = ported.lib
    lib.wof_state_size.restype = ctypes.c_uint32
    lib.wt_set_vblanks_per_pass(2)
    lib.wt_pokes_clear()
    raw, keys, here = case_schedule(name)
    lib.wof_set_fade_vblanks(0)            # the schedules are the headless original's
    ported.reset_core(seed=1)
    before = None
    fed = []                               # every VBlank as given, for the WebAssembly core
    for v in range(len(raw)):
        drive_schedule(ported, raw, keys, v, 1, fed)
        if ported.mission_count() and here(ported, v + 1):
            before = v + 1
            break
    assert before, 'the save point of %s was never reached' % name
    if name == 'left':
        hell = (ctypes.c_uint8 * 128)()
        torp = (ctypes.c_uint8 * 128)()
        lib.wt_markers_get(hell, torp)
        assert 0 in bytes(hell), 'no hellcat.shp frame is mirrored at the save'
    if name == 'paused':
        assert ported.g('pause_flag'), 'the game is not paused at the save'

    saved = native_state(ported)
    saved_frame = frame(ported)
    fed_before = len(fed)
    drive_schedule(ported, raw, keys, before, AFTER, fed)
    straight = (digest(native_state(ported)), frame(ported))

    native_load(ported, saved)
    assert frame(ported) == saved_frame, 'the picture after a load is not the saved one'
    drive_schedule(ported, raw, keys, before, AFTER)
    assert (digest(native_state(ported)), frame(ported)) == straight, 'native: replay differs'

    ported.reset_core(seed=4711)
    drive_schedule(ported, raw, keys, 0, 50)
    native_load(ported, saved)
    assert frame(ported) == saved_frame
    drive_schedule(ported, raw, keys, before, AFTER)
    assert (digest(native_state(ported)), frame(ported)) == straight, 'native: foreign core differs'
    lib.wof_set_fade_vblanks(2)
    ported.reset_core()

    schedule = tmp_path / 'schedule.json'
    schedule.write_text(json.dumps({
        'raw': [r for r, _ in fed] + [0] * AFTER, 'fades': 0,
        'keys': [(v, code, qualifier) for v, (_, ks) in enumerate(fed) for code, qualifier in ks]}))
    assert len(fed) == fed_before + AFTER, 'a fade in the flight after the save'
    out = run(['node', str(ROOT / 'tests' / 'state_wasm.mjs'), str(WASM), str(blob_file),
               str(fed_before), str(AFTER), str(schedule)])
    wasm = json.loads(out.stdout)
    assert wasm['loadedFrame'] == wasm['savedFrame'] == wasm['foreignFrame']
    assert wasm['straight'] == wasm['replayed'] == wasm['foreign'], wasm
    assert wasm['saved'] == digest(saved), 'the two targets saved different states'
    assert (wasm['straight']['state'], wasm['straight']['frame']) == straight


def wasm_function_names(path):
    """The function names of a WebAssembly module's name section."""
    data = path.read_bytes()

    def leb(at):
        value = shift = 0
        while True:
            byte = data[at]
            at += 1
            value |= (byte & 0x7F) << shift
            shift += 7
            if not byte & 0x80:
                return value, at

    names, at = [], 8
    while at < len(data):
        section, at = data[at], at + 1
        size, at = leb(at)
        end = at + size
        if section == 0:
            length, p = leb(at)
            if data[p:p + length] == b'name':
                p += length
                while p < end:
                    sub, p = data[p], p + 1
                    sub_size, p = leb(p)
                    if sub == 1:
                        count, q = leb(p)
                        for _ in range(count):
                            _, q = leb(q)
                            n, q = leb(q)
                            names.append(data[q:q + n].decode())
                            q += n
                    p += sub_size
        at = end
    return names


def test_the_release_core_has_no_test_hooks(ported):
    """The hooks the comparison drives the port with - the pass, tick and step S hooks, the
    pokes, the trace - exist in the native test build only
    (WOF_TRACE); dist/core.wasm is built without them."""
    names = wasm_function_names(WASM)
    assert len(names) > 100, 'the release core has no name section to check'
    hooks = [n for n in names if n.startswith(('wof_test_', 'wof_trace'))]
    assert hooks == [], hooks
    lib = ported.lib
    for name in ('wof_test_set_tick_hook', 'wof_test_set_pass_hook', 'wof_trace_add'):
        assert hasattr(lib, name), 'the test build lacks %s' % name
