"""The test instrumentation's state does not outlive a test (re/notes/testing.md, "A fresh
core for every test").

A process holds one copy of the core, and the instrumentation tests/shim.c sets in
src/trace.c - the hooks, the pokes, the map list's addresses, the stand-ins reached, the trace
records - lives beside the core's state and survives wof_init.  tests/conftest.py's
fresh_core puts it back before every test that takes the core, and a replay clears what it
set when it ends (tests/m4compare.py).  Found on 2026-09-29: under pytest-xdist a worker ran
bomb_c's closed loop, whose replay poked mission_number 3 at the rank selection's end, and
then the front end, which met the poke there.
"""
import ctypes

import pytest

import conftest
import test_front_port
import test_weapons

MAP_LIST_ADDRESS = 0x0024F404            # WOF_MAP_LIST_ADDRESS, src/wof.h


def test_the_fresh_core_leaves_no_test_state_behind(ported):
    """Everything the instrumentation can hold, set, then the fixture's reset, then none of
    it left: a poke of a global and one by the original's address applied at both points
    change nothing, the map list's address is the default one, no stand-in is counted, the
    trace holds what wof_init records and no more, a tick's end calls no hook, and the
    snapshots of the front end's end, of step S and of a pass's end are gone: reading one
    fails instead of answering with the old one."""
    lib = ported.lib
    for name, argtypes, restype in (
            ('wt_poke', [ctypes.c_uint] * 3, None),
            ('wt_poke_reset', [ctypes.c_uint] * 3, None),
            ('wt_poke_address', [ctypes.c_uint] * 4, None),
            ('wt_map_addresses', [ctypes.c_void_p, ctypes.c_uint], None),
            ('wt_set_tick_hook', [ctypes.c_void_p], None),
            ('wof_standin', [ctypes.c_char_p], None),
            ('wt_standin_count', [], ctypes.c_int),
            ('wt_trace_count', [], ctypes.c_int),
            ('wof_test_poke_after_rank', [], None),
            ('wof_test_poke_after_reset', [], None),
            ('wof_test_tick_end', [ctypes.c_uint32], None),
            ('wof_env_map_address', [], ctypes.c_uint32),
            ('wof_trace_add', [ctypes.c_char_p] + [ctypes.c_int32] * 4 + [ctypes.c_char_p,
                                                                          ctypes.c_uint16], None),
            ('wof_trace_globals', [], None),
            ('wof_trace_mission', [], None),
            ('wof_trace_pass_end', [], None),
            ('wt_globals_get', [ctypes.c_int, ctypes.c_void_p, ctypes.c_int], ctypes.c_int),
            ('wt_pass_view', [ctypes.c_int], ctypes.c_int)):
        function = getattr(lib, name)
        function.argtypes = argtypes
        function.restype = restype
    fresh_trace = lib.wt_trace_count()                  # what wof_init itself records
    registry = ported.globals_registry()
    offset = registry['mission_number'][3]
    address = registry['rank_played'][2]

    lib.wt_poke(offset, 2, 3)
    lib.wt_poke_reset(offset, 2, 4)
    lib.wt_poke_address(address, 2, 5, 0)
    addresses = (ctypes.c_uint32 * 1)(0x00300000)
    lib.wt_map_addresses(addresses, 1)
    marker = ctypes.create_string_buffer(b'TEST STAND-IN: set by tests/test_isolation.py')
    lib.wof_standin(marker)
    ticks = []
    hook = ctypes.CFUNCTYPE(None, ctypes.c_uint32)(ticks.append)
    lib.wt_set_tick_hook(ctypes.cast(hook, ctypes.c_void_p))
    lib.wof_test_tick_end(7)
    lib.wof_trace_add(b'test', 1, 2, 3, 4, b'', 0)
    ported.set_g('mission_number', 9)
    lib.wof_trace_globals()                              # the front end's end
    lib.wof_trace_mission()                              # step S
    lib.wof_trace_pass_end()                             # a pass's end
    state = ctypes.create_string_buffer(ported.globals_bytes())
    assert ticks == [7] and lib.wt_standin_count() == 1 and lib.wt_trace_count() >= 1, (
        'the instrumentation took nothing')
    assert ported.g_at_mission('mission_number') == 9
    assert lib.wt_globals_get(1, state, len(state)) == len(state) and lib.wt_pass_view(1) >= 0

    conftest.fresh_settings()
    ported.reset_core()

    ported.set_g('mission_number', 1)
    ported.set_g('rank_played', 2)
    lib.wof_test_poke_after_rank()
    lib.wof_test_poke_after_reset()
    assert (ported.g('mission_number'), ported.g('rank_played')) == (1, 2), 'a poke outlived its test'
    assert lib.wof_env_map_address() == MAP_LIST_ADDRESS, 'a map address outlived its test'
    assert lib.wt_standin_count() == 0, 'a stand-in count outlived its test'
    assert lib.wt_trace_count() == fresh_trace, 'a trace record outlived its test'
    lib.wof_test_tick_end(8)
    assert ticks == [7], 'a hook outlived its test'
    assert lib.wt_globals_get(1, state, len(state)) == -1, 'the step-S snapshot outlived its test'
    assert lib.wt_pass_view(1) == -1, "a pass's snapshot outlived its test"
    with pytest.raises(AssertionError, match='step S not reached'):
        ported.g_at_mission('mission_number')


@pytest.mark.slow
def test_a_replays_pokes_do_not_reach_the_front_end_after_it(ported):
    """The finding's pair in one process, in the order that failed: bomb_c's closed loop,
    whose replay pokes mission_number 3 at the rank selection's end, then, after the reset
    fresh_core makes between two tests, the front end's hand-over, which compares
    mission_number with the original's 1."""
    test_weapons.test_every_tick_and_pass_agrees_in_the_closed_loop(ported, 'bomb_c')
    conftest.fresh_settings()
    ported.reset_core()
    test_front_port.test_the_key_buffer_and_the_latches_end_where_the_original_leaves_them(ported)
