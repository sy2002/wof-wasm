# tests/conftest.py, lines 1320-1356
def fresh_settings():
    """What lives beside the core's state and survives wof_init, put back to what the process
    held before any test ran (re/notes/testing.md, "A fresh core for every test"): the
    VBlanks of a fade step and of a pass, read off the core at the first call, and the test
    instrumentation tests/shim.c sets in src/trace.c - the three hooks, the pokes, the map
    list's addresses, the stand-ins reached, the trace records and the snapshots at step S
    and at a pass's end, which only this reset forgets, never one inside a test.  The audio
    output rate survives too and is left alone: every test that renders names its rate
    before the VBlanks it takes, and a new rate empties the queue."""
    lib = _SETTINGS.get('lib')
    if lib is None:
        lib = ctypes.CDLL(str(DYLIB))
        for name, argtypes, restype in (('wof_fade_vblanks', [], ctypes.c_int),
                                        ('wof_set_fade_vblanks', [ctypes.c_int], None),
                                        ('wof_vblanks_per_pass', [], ctypes.c_int),
                                        ('wt_set_vblanks_per_pass', [ctypes.c_int], None),
                                        ('wt_set_tick_hook', [ctypes.c_void_p], None),
                                        ('wt_set_step_s_hook', [ctypes.c_void_p], None),
                                        ('wt_set_pass_hook', [ctypes.c_void_p], None),
                                        ('wt_pokes_clear', [], None),
                                        ('wt_map_addresses', [ctypes.c_void_p, ctypes.c_uint], None),
                                        ('wt_standins_reset', [], None),
                                        ('wt_trace_reset', [], None),
                                        ('wt_snapshots_reset', [], None)):
            function = getattr(lib, name)
            function.argtypes = argtypes
            function.restype = restype
        _SETTINGS.update(lib=lib, fade=lib.wof_fade_vblanks(), per_pass=lib.wof_vblanks_per_pass())
    lib.wof_set_fade_vblanks(_SETTINGS['fade'])
    lib.wt_set_vblanks_per_pass(_SETTINGS['per_pass'])
    for hook in ('wt_set_tick_hook', 'wt_set_step_s_hook', 'wt_set_pass_hook'):
        getattr(lib, hook)(None)
    lib.wt_pokes_clear()
    lib.wt_map_addresses(None, 0)
    lib.wt_standins_reset()
    lib.wt_trace_reset()
    lib.wt_snapshots_reset()
