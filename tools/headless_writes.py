"""What a headless run wrote and read, summarised over the whole run.

A change report of a few hundred ticks is tens of thousands of lines and one of a few
thousand ticks is tens of megabytes, so a finding about "which state a pass writes" cannot
come from reading it.  This module accumulates the same information as the run goes and
hands back one line per address range:

  * the **phase** every write was made in: `V` inside a VBlank server, `T` inside
    logic_tick's tree, `F` inside frame_update's tree, `M` in the main program outside both;
  * the **window** the change showed up in, which is the step kind the dump records: `T`,
    `P` or `S`;
  * the routines that wrote it and how often;
  * for a table, the regular stride its written offsets fall into.

`Summary.write` is fed from the write hook of tools/headless.py and `Summary.change` from
the change report's own comparison, so a range that was written with the value it already
had is visible as written without being changed.  Reads are collected the same way
(`Reads`), which answers whether anything in logic_tick's tree reads what a pass leaves.
"""
import collections

PHASES = ('V', 'T', 'F', 'M')
PHASE_MEANING = {'V': 'a VBlank server', 'T': "logic_tick's tree",
                 'F': "frame_update's tree", 'M': 'the main program'}


class Summary:
    """Writes per address, with the phase and the routine, and changes per step kind."""

    def __init__(self):
        self.writes = {}                 # address -> Counter of (phase, routine)
        self.changes = {}                # address -> Counter of step kind
        self.steps = collections.Counter()

    def write(self, address, size, phase, routine):
        for a in range(address, address + size):
            slot = self.writes.get(a)
            if slot is None:
                slot = self.writes[a] = collections.Counter()
            slot[(phase, routine)] += 1

    def change(self, address, length, kind):
        for a in range(address, address + length):
            slot = self.changes.get(a)
            if slot is None:
                slot = self.changes[a] = collections.Counter()
            slot[kind] += 1

    def step(self, kind):
        self.steps[kind] += 1

    def ranges(self):
        """Consecutive addresses that were written and changed in exactly the same way,
        as [(address, length, writes, changes)] with the two Counters of the range."""
        out = []
        addresses = sorted(set(self.writes) | set(self.changes))
        empty = collections.Counter()
        start = previous = None
        signature = None
        for address in addresses:
            here = (self.writes.get(address, empty), self.changes.get(address, empty))
            mark = (tuple(sorted(here[0].items())), tuple(sorted(here[1].items())))
            if start is not None and address == previous + 1 and mark == signature:
                previous = address
                continue
            if start is not None:
                out.append((start, previous - start + 1) + kept)
            start = previous = address
            signature, kept = mark, here
        if start is not None:
            out.append((start, previous - start + 1) + kept)
        return out

    def phases_of(self, writes):
        return ''.join(p for p in PHASES if any(key[0] == p for key in writes))


def strides(items, minimum=3, widest=0x400, coverage=0.75, density=0.5):
    """The record size a set of written ranges falls into, or None.

    A table of records shows up as the same few offsets inside a record, repeated at the
    record size, over a run of consecutive records.  A candidate stride is accepted when
    every range fits inside one record, when the records it covers are a nearly unbroken
    run, and when they are not filled so densely that the "record" is really a plain array.
    Of the accepted ones the smallest wins, because the record is the smallest repeating
    unit; a plain array of words is rejected by the density rule rather than reported as a
    table of two-byte records.  A few ranges that are longer than the record, or straddle two,
    are passed over as long as they are a fifth of the cluster at most.  items: [(start, length)].  Returns (base, stride, records, offsets)."""
    items = sorted(set(items))
    if len(items) < minimum:
        return None
    starts = [a for a, _ in items]
    base = starts[0]
    candidates = set()
    for i, a in enumerate(starts):
        for b in starts[i + 1:i + 6]:
            if 2 <= b - a <= widest:
                candidates.add(b - a)
    for stride in sorted(candidates):
        offsets = {}
        records = set()
        strays = 0
        for start, length in items:
            offset = (start - base) % stride
            if offset + length > stride:
                strays += 1                        # too long or straddling: not a field here
                continue
            offsets[offset] = max(offsets.get(offset, 0), length)
            records.add((start - base) // stride)
        if (records and strays <= max(1, len(items) // 5) and len(records) >= minimum
                and len(offsets) <= 8 and len(records) >= coverage * (max(records) + 1)
                and sum(offsets.values()) <= density * stride):
            return (base, stride, len(records), sorted(offsets))
    return None


class Reads:
    """Reads of watched memory: (phase, routine, label, offset, size) -> count."""

    def __init__(self):
        self.counts = collections.Counter()
        self.events = []                 # (step, phase, routine, label, offset, size), on request

    def read(self, phase, routine, label, offset, size):
        self.counts[(phase, routine, label, offset, size)] += 1

    def by_routine(self):
        """{(phase, routine, label): (reads, first offset, last offset)}."""
        out = {}
        for (phase, routine, label, offset, size), count in self.counts.items():
            key = (phase, routine, label)
            reads, low, high = out.get(key, (0, offset, offset + size))
            out[key] = (reads + count, min(low, offset), max(high, offset + size))
        return out

    def offsets(self, label=None, phase=None, routine=None):
        """Every offset read, as a sorted list, filtered by label, phase or routine."""
        found = set()
        for key in self.counts:
            if ((label is None or key[2] == label) and (phase is None or key[0] == phase)
                    and (routine is None or key[1] == routine)):
                found.update(range(key[3], key[3] + key[4]))
        return sorted(found)


def format_summary(summary, describe, only_phases=None, limit=None):
    """The report: one line per range, sorted by address."""
    lines = []
    for address, length, writes, changes in summary.ranges():
        phases = summary.phases_of(writes)
        if only_phases and not set(phases) & set(only_phases):
            continue
        who = ', '.join('%s %s x%d' % (phase, routine, count)
                        for (phase, routine), count in sorted(writes.items(), key=lambda kv: -kv[1]))
        windows = ' '.join('%s x%d' % (kind, count) for kind, count in sorted(changes.items()))
        lines.append('%06x %-34s %3d  [%s] %-18s  %s' % (
            address, describe(address), length, phases, windows or '(no change)', who))
        if limit and len(lines) >= limit:
            break
    return lines


def tables(summary, region_of, minimum=3, apart=0x200):
    """The tables a run walked: for every routine and region, the regular stride its written
    ranges fall into.  A routine often writes several tables and single variables in the same
    region, so its ranges are first cut into clusters wherever they lie more than `apart`
    bytes from the next, and each cluster is looked at on its own.
    [(phase, routine, region, (base, stride, records, offsets))]."""
    groups = collections.defaultdict(set)
    for address, length, written, _ in summary.ranges():
        for phase, routine in written:
            groups[(phase, routine, region_of(address))].add((address, length))
    found = []
    for (phase, routine, region), items in groups.items():
        cluster = []
        for start, length in sorted(items) + [(None, None)]:
            if start is not None and (not cluster or start - cluster[-1][0] <= apart):
                cluster.append((start, length))
                continue
            stride = strides(cluster, minimum=minimum)
            if stride:
                found.append((phase, routine, region, stride))
            cluster = [(start, length)] if start is not None else []
    return sorted(found, key=lambda item: (-item[3][2], item[3][0]))


def format_tables(rows, describe):
    lines = []
    for phase, routine, _, (base, stride, records, offsets) in rows:
        lines.append('%s %-26s %06x %-30s stride 0x%-4x %4d records  offsets %s' % (
            phase, routine, base, describe(base), stride, records,
            ' '.join('0x%x' % o for o in offsets)))
    return lines
