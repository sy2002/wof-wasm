# tests/test_isolation.py, lines 86-103, a part of test_the_fresh_core_leaves_no_test_state_behind (lines 23-103)
conftest.fresh_settings()
ported.reset_core()

ported.set_g('mission_number', 1)
ported.set_g('rank_played', 2)
lib.wof_test_poke_after_rank()
lib.wof_test_poke_after_reset()
lib.wof_test_poke_after_map()
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
