"""M4's groundwork: what a pass writes and what a tick reads of it (SPEC 10 point 2).

The findings are in re/notes/passes.md, made over seven scripts that together run 8,000 ticks
(tools/pass_observe.py, outside the suite).  What is held here is the part a short script
already shows: the phase every coupled range is written in, the routine that writes it, the
routine that reads it back, and the control that says state which is not coupled does not
depend on how many VBlanks a pass takes.
"""
import os
import sys

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, 'tools'))

import headless                    # noqa: E402
import pass_observe                # noqa: E402

OBJECT_RECORDS, OBJECT_STRIDE, OBJECT_COUNT = 0x024CAE, 0x2A, 15
PASS_COUNTER, FRAME_DRAWN = 0x0253C8, 0x026E3C
VIEW_X, SPLIT_ROW = 0x024F30, 0x0253A0
SOUND_DISTANCE = 0x027164

FRONT = [[30, ''], [3, 'F']] * 5
TAKE_OFF = [[40, ''], [3, 'F'], [60, ''], [460, 'R'], [400, 'RU']]
# The guns fire so that objects are spawned: without them no object record is touched.
SHORT = {'raw': FRONT + TAKE_OFF + [[500, 'RF']], 'stop': {'ticks': 110}}


@pytest.fixture(scope='module')
def summarised():
    """One short flight with the write summary, and a second that watches reads of exactly
    what the first saw a pass write."""
    first = headless.Headless(dict(SHORT), summary=True, keep_report=False)
    first.run()
    written = [(address, length, writes) for address, length, writes, _ in first.summary.ranges()
               if 'F' in first.summary.phases_of(writes)]
    second = headless.Headless(dict(SHORT), read_ranges=[(a, n) for a, n, _ in written])
    second.run()
    readers = {}
    for (phase, routine, label, offset, size) in second.reads.counts:
        readers.setdefault(label, set()).add((phase, routine))
    return first, written, readers


def writers_of(written, address, phase='F'):
    for start, length, writes in written:
        if start <= address < start + length:
            return {routine for (where, routine) in writes if where == phase}
    return set()


def readers_of(first, readers, address, phase='T'):
    label = first.names.datum(address) if address < headless.HEAP_BASE else '%06x' % address
    return {routine for (where, routine) in readers.get(label, ()) if where == phase}


def test_the_pass_writes_the_view_and_the_counters(summarised):
    """The four the drawing note already named, now with the phase they are written in."""
    first, written, _ = summarised
    assert writers_of(written, VIEW_X) == {'frame_update'}
    assert writers_of(written, SPLIT_ROW) == {'frame_update'}
    assert writers_of(written, PASS_COUNTER) == {'draw_world'}
    assert writers_of(written, FRAME_DRAWN) == {'frame_update'}


def test_the_tick_reads_the_pass_counter_and_the_sound_distance(summarised):
    """Two of the couplings of re/notes/passes.md, over a script short enough for the suite.
    The others need an object in the air or the restart and are shown by tools/pass_observe.py."""
    first, _, readers = summarised
    assert 'lift_step' in readers_of(first, readers, PASS_COUNTER)
    assert readers_of(first, readers, SOUND_DISTANCE) == {'engine_sound'}


def test_a_pass_writes_the_drawing_fields_of_every_object_record(summarised):
    """The part of point 2 that static reading could not enumerate: fields of the object
    table that a pass writes through pointers.  snapshot_for_draw copies six bytes into every
    one of the fifteen records, which the stride detection finds as a table on its own."""
    first, written, _ = summarised
    copies = [OBJECT_RECORDS + OBJECT_STRIDE * i + 0x08 for i in range(OBJECT_COUNT)]
    for address in copies:
        assert writers_of(written, address) == {'snapshot_for_draw'}, hex(address)
    rows = headless.trace.tables(first.summary, first.region_of())
    found = [stride for phase, routine, _, stride in rows
             if routine == 'snapshot_for_draw' and stride[0] == copies[0]]
    assert found and found[0][1] == OBJECT_STRIDE and found[0][2] >= OBJECT_COUNT, rows[:4]


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
