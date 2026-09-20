"""M4's groundwork: the object system (SPEC 10 point 3).

The inventory and the per-kind details are in re/notes/objects.md, made with
tools/object_observe.py over long scripts.  What is held here is what a short script shows:
the tables are where the note says, a record is claimed and freed through its kind byte, the
tick walks the tables in one order, and a run that fires differs from one that does not only
in the tables the note names.
"""
import os
import sys

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, 'tools'))

import headless                    # noqa: E402
import headless_dump as dump       # noqa: E402
import object_observe              # noqa: E402

FRONT = [[30, ''], [3, 'F']] * 5
TAKE_OFF = [[40, ''], [3, 'F'], [60, ''], [460, 'R'], [400, 'RU']]
OBJECT_RECORDS, OBJECT_STRIDE, OBJECT_COUNT, KIND = 0x024CAE, 0x2A, 15, 0x20


def run(tail, ticks, **options):
    machine = headless.Headless({'raw': FRONT + TAKE_OFF + tail, 'stop': {'ticks': ticks}},
                                **options)
    machine.run()
    return machine


# The other weapon is dropped with a short click of the button (the manual, page 7), and
# that is what fills the object table; the machine gun, which is the button held, does not.
TAPS = [[3, 'F'], [13, '']] * 20 + [[100, '']]


@pytest.fixture(scope='module')
def firing():
    """A take-off and then twenty bombs: object records are claimed and freed all the time."""
    return run(TAPS, 330, summary=True, keep_report=False,
               observe=['sub_010a72', 'sub_01e7d6', 'sub_0119bc', 'sub_011c5e',
                        'sub_011e82', 'sub_01c660', 'sub_01b682'])


def test_the_tables_are_where_the_note_says(firing):
    """Every table of the inventory: its base, its record size and how many records fit."""
    tables = {name: (base, size, count) for name, base, size, count in object_observe.resolve(firing)}
    assert tables['object_records'][:3] == (OBJECT_RECORDS, OBJECT_STRIDE, OBJECT_COUNT)
    assert tables['aircraft_records'] == (0x02522A, 0x34, 4)
    assert tables['ship_records'] == (0x025460, 0x1E, 5)
    assert tables['player_record'][0] == 0x025078
    for name, size, bytes_total in (('ricochet', 4, 0x50), ('splashes', 4, 0x50),
                                    ('smoke', 0x14, 0x320), ('balloons', 0x12, 0x168)):
        base, record, count = tables[name]
        assert base and record == size and record * count == bytes_total, name
    assert tables['soldier_records'][2] == firing.o.r16(0x0253C4)


def test_an_object_record_is_claimed_and_freed_through_its_kind_byte(firing):
    """object_spawn (0x010820) walks the table for the first record whose kind byte is zero
    and fills it; the byte stays non-zero while the object lives and is cleared when it is
    gone.  Every record of the table is claimed at least once over twenty bombs."""
    writers = {}
    for address, length, written, changed in firing.summary.ranges():
        for byte in range(address, address + length):
            writers.setdefault(byte, set()).update(written)
    for i in range(OBJECT_COUNT):
        kind = OBJECT_RECORDS + OBJECT_STRIDE * i + KIND
        assert ('T', 'object_spawn') in writers[kind], (i, writers[kind])
        assert ('M', 'sub_013756') in writers[kind], (i, writers[kind])
    freed = [i for i in range(OBJECT_COUNT)
             if ('F', 'sub_010702') in writers.get(OBJECT_RECORDS + OBJECT_STRIDE * i + KIND, ())]
    assert freed, 'no record was ever freed inside a pass'
    kinds = [firing.o.read(OBJECT_RECORDS + OBJECT_STRIDE * i + KIND, 1)[0]
             for i in range(OBJECT_COUNT)]
    assert not all(kinds), 'no object record was free at the end of the run'


def test_the_tick_walks_the_tables_in_one_order(firing):
    """logic_tick's own order over the tables, as the entries of their walkers show."""
    order, seen = [], set()
    for record in firing.observed:
        if record['phase'] != 'T' or record['tick'] != 200:
            continue
        if record['routine'] not in seen:
            seen.add(record['routine'])
            order.append(record['routine'])
    assert order.index('sub_01c660') < order.index('sub_010a72'), order
    assert 'sub_0119bc' in order and 'sub_011c5e' in order, order
    assert order.index('sub_010a72') < order.index('sub_0119bc'), order


def test_firing_differs_from_not_firing_only_in_the_tables_the_note_names():
    """The control of re/notes/objects.md for the object table: two runs one scripted input
    apart.  What their states differ in is the object records, the smoke the guns make and the
    player's own record, and nothing that belongs to another table."""
    label, left, right = object_observe.pair('a bomb dropped or not', TAPS,
                                             [[16, '']] * 20 + [[100, '']], 330)
    hit = object_observe.controls([(label, left, right)], verbose=False)[0][1]
    assert hit['object_records'] > 0, dict(hit)
    assert set(hit) <= {'object_records', 'object_extra', 'player_record', 'smoke',
                        'splashes', 'ricochet', 'aircraft_records', 'elsewhere'}, dict(hit)
