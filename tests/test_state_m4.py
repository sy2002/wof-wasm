"""A save state in the middle of a mission (M4, V7).

The core is taken into its first mission by the fire button alone and saved some passes
into it; running on from the save, from the loaded save, and from the save loaded into a
fresh core with another seed must give the same state and the same picture, on the native
library and on the WebAssembly core - and the two targets must agree with each other.
"""
import ctypes
import hashlib
import json

from conftest import ROOT, WASM, run

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
    lib.wt_tick_waits_clear()
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
    tick stand-in's waits, the pokes, the trace - exist in the native test build only
    (WOF_TRACE); dist/core.wasm is built without them."""
    names = wasm_function_names(WASM)
    assert len(names) > 100, 'the release core has no name section to check'
    hooks = [n for n in names if n.startswith(('wof_test_', 'wof_trace'))]
    assert hooks == [], hooks
    lib = ported.lib
    for name in ('wof_test_set_tick_waits', 'wof_test_set_pass_hook', 'wof_trace_add'):
        assert hasattr(lib, name), 'the test build lacks %s' % name
