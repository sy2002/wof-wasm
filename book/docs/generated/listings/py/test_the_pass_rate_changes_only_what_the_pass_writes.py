# tests/test_passes.py, lines 91-106
def test_the_pass_rate_changes_only_what_the_pass_writes():
    """The control of re/notes/passes.md, over a shorter script: the same run at one, two and
    three VBlanks per pass, over an entropy stream of one constant value so that all three see
    the same stream.  The three have to feed the tick the same input bytes, or the comparison
    says nothing; then every byte that differs at the same tick number must have been written
    by a pass, by a VBlank server, or inside a tick by a routine that reads a range a pass
    wrote, or lies below one.  Whatever is left over is a finding, and there is none."""
    result = pass_observe.control(name='guns', ticks=55, rates=(1, 2, 3), verbose=False)
    assert result['inputs_match'], 'the three rates fed the tick different input bytes'
    assert len({result['counters'][rate][0] for rate in result['counters']}) == 3, \
        'the pass rates did not differ'
    assert result['differing'], 'nothing differs at all, so the control shows nothing'
    assert len(result['differing']) < 200, 'far more state depends on the pass rate than the note says'
    assert not result['leftover'], result['leftover']
    verdicts = {verdict for verdict, _, _ in result['rows']}
    assert 'written by a pass' in verdicts, verdicts
