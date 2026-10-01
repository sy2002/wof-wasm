# tests/test_headless.py, lines 452-472
def test_where_a_slice_ends_changes_nothing():
    """The emulation runs in slices that Unicorn ends by counting instructions
    (tools/headless.py, _drive): before an instruction whose own hooks have not run yet, and
    nowhere that depends on the wall clock.  Three flights with every kind of hook in use - the
    harness's write hook, an observer on the blitter library's main entry, the beam's read
    hook, the stops - in slices of 97 instructions (an odd length, so that the ends fall
    everywhere, inside a block with a hooked instruction too), of the default length and of
    10**10 (one slice from each wait point to the next) give the same steps, the same entropy
    reads, the same schedule and the same observed calls.  A slice once ended by Unicorn's
    timeout instead, and with slices of 3 ms every recording of a mission script came out
    different (re/notes/headless.md, "Unicorn, as it behaves here")."""
    runs = [run(flight(), track_writes=True, observe=['shape_draw'], slice_insns=length)
            for length in (97, headless.SLICE_INSNS, 10 ** 10)]
    assert runs[0].slices_out > 10000, 'the short slices ended only %d times' % runs[0].slices_out
    assert runs[2].slices_out == 0
    assert len(runs[0].observed) > 1000 and len(runs[0].entropy_log) > 100
    for other in runs[1:]:
        assert other.step_hashes == runs[0].step_hashes
        assert other.entropy_log == runs[0].entropy_log
        assert other.schedule == runs[0].schedule
        assert other.observed == runs[0].observed
