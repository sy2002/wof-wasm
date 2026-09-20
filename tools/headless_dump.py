"""State dumps of the headless original: the file format, a reader, and names for addresses.

A dump file is a sequence of records.  Each record is

    u32 length of the JSON part, u32 length of the payload, the JSON (UTF-8), the payload

all big-endian.  The first record is the header, every further record is one step.

    header  {"format": "wof-headless-dump", "version": 1, "run": <the run description>}
    step    {"step": n, "kind": "S" | "T" | "P", "mission": m, "tick": t, "pass": p,
             "vblank": v, "entropy": e, "input": byte of the tick, "hash": hex,
             "regions": [[address, size, label], ...]    only when the set has changed,
             "delta": [[address, length], ...]}
            payload: the bytes of the delta ranges, one after the other

Kinds: S is the state when a mission's inner loop is first reached, T the state after a
logic tick, P the state after a pass.  The counters are totals since the program start.

The state of a step is its regions with all deltas up to that step applied; a region that
appears starts as zeroes, which is what AllocMem hands out.  `hash` is the SHA-256 over
every region in address order, each as u32 address, u32 size and its bytes, so a reader can
check its own reconstruction.  Regions are the executable's DATA and BSS range and every
live allocation outside display memory.
"""
import bisect
import csv
import hashlib
import json
import os
import struct

import numpy

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)

FORMAT = 'wof-headless-dump'
VERSION = 1


def state_hash(regions):
    """regions: {address: bytes-like}."""
    digest = hashlib.sha256()
    for address in sorted(regions):
        data = regions[address]
        digest.update(struct.pack('>LL', address, len(data)))
        digest.update(data)
    return digest.hexdigest()


def changed_ranges(old, new, gap=8):
    """Byte ranges where two equally long buffers differ; ranges closer than `gap` are joined."""
    if old == new:
        return []
    a = numpy.frombuffer(old, dtype=numpy.uint8)
    b = numpy.frombuffer(new, dtype=numpy.uint8)
    where = numpy.nonzero(a != b)[0]
    if len(where) == 0:
        return []
    breaks = numpy.nonzero(numpy.diff(where) > gap)[0]
    starts = numpy.concatenate(([where[0]], where[breaks + 1]))
    ends = numpy.concatenate((where[breaks], [where[-1]]))
    return [(int(s), int(e - s + 1)) for s, e in zip(starts, ends)]


class DumpWriter:
    def __init__(self, path, run):
        self.file = open(path, 'wb')
        self.state = {}                       # address -> bytes of the previous step
        self.labels = {}
        self.steps = 0
        self._record({'format': FORMAT, 'version': VERSION, 'run': run}, b'')

    def _record(self, head, payload):
        text = json.dumps(head, separators=(',', ':')).encode()
        self.file.write(struct.pack('>LL', len(text), len(payload)))
        self.file.write(text)
        self.file.write(payload)

    def step(self, info, regions, labels):
        """info: the step's counters.  regions: {address: bytes}.  Returns the hash."""
        head = dict(info)
        head['step'] = self.steps
        head['hash'] = state_hash(regions)
        if set(regions) != set(self.state) or any(len(regions[a]) != len(self.state[a]) for a in regions):
            head['regions'] = [[a, len(regions[a]), labels.get(a, '')] for a in sorted(regions)]
        delta, payload = [], []
        for address in sorted(regions):
            new = regions[address]
            old = self.state.get(address)
            if old is None or len(old) != len(new):
                old = bytes(len(new))
            for start, length in changed_ranges(old, new):
                delta.append([address + start, length])
                payload.append(new[start:start + length])
        head['delta'] = delta
        self._record(head, b''.join(payload))
        self.state = dict(regions)
        self.steps += 1
        return head['hash']

    def close(self):
        self.file.close()


class DumpReader:
    """Iterates over the steps of a dump and keeps the reconstructed state of the current one."""

    def __init__(self, path):
        self.file = open(path, 'rb')
        head, _ = self._record()
        if head.get('format') != FORMAT or head.get('version') != VERSION:
            raise ValueError('%s is not a version %d headless dump' % (path, VERSION))
        self.run = head['run']
        self.regions = {}                     # address -> bytearray
        self.labels = {}

    def _record(self):
        lengths = self.file.read(8)
        if len(lengths) < 8:
            return None, None
        text_len, payload_len = struct.unpack('>LL', lengths)
        return json.loads(self.file.read(text_len)), self.file.read(payload_len)

    def __iter__(self):
        return self

    def __next__(self):
        head, payload = self._record()
        if head is None:
            self.file.close()
            raise StopIteration
        if 'regions' in head:
            fresh = {}
            for address, size, label in head['regions']:
                old = self.regions.get(address)
                fresh[address] = old if old is not None and len(old) == size else bytearray(size)
                self.labels[address] = label
            self.regions = fresh
        bases = sorted(self.regions)
        offset = 0
        for address, length in head['delta']:
            base = bases[bisect.bisect_right(bases, address) - 1]
            self.regions[base][address - base:address - base + length] = payload[offset:offset + length]
            offset += length
        return head

    def verify(self, head):
        return state_hash(self.regions) == head['hash']


def steps(path):
    """The step headers of a dump, without the states."""
    reader = DumpReader(path)
    return [head for head in reader]


def state_at(path, step):
    reader = DumpReader(path)
    for head in reader:
        if head['step'] == step:
            return head, {a: bytes(d) for a, d in reader.regions.items()}, dict(reader.labels)
    raise ValueError('%s has no step %d' % (path, step))


# ------------------------------------------------------------------------------ names

class Names:
    """Addresses to names: re/names.txt for data, re/functions.csv for code."""

    def __init__(self, root=ROOT):
        self.data = []
        path = os.path.join(root, 're', 'names.txt')
        for line in open(path):
            body = line.partition(';')[0].split()
            if len(body) >= 2 and not line.lstrip().startswith('#'):
                self.data.append((int(body[0], 16), body[1]))
        self.data.sort()
        self.data_keys = [a for a, _ in self.data]
        self.code = []
        with open(os.path.join(root, 're', 'functions.csv'), newline='') as f:
            for row in csv.DictReader(f):
                self.code.append((int(row['addr'], 16), int(row['span'] or 0), row['name']))
        self.code.sort()
        self.code_keys = [a for a, _, _ in self.code]

    def routine(self, pc):
        i = bisect.bisect_right(self.code_keys, pc) - 1
        if i < 0:
            return '%06x' % pc
        address, span, name = self.code[i]
        return name if pc < address + max(span, 1) else '%s+0x%x' % (name, pc - address)

    def routine_start(self, pc):
        i = bisect.bisect_right(self.code_keys, pc) - 1
        return self.code[i][0] if i >= 0 else pc

    def datum(self, address, limit=0x100):
        """A name for an address in the executable's data.  An address without a name of its
        own gets the listing's automatic name, and the nearest name below it for orientation;
        whether it belongs to that neighbour is not known here, because names carry no size."""
        i = bisect.bisect_right(self.data_keys, address) - 1
        if i >= 0 and self.data[i][0] == address:
            return self.data[i][1]
        auto = 'g_%06x' % address
        if i < 0 or address - self.data[i][0] > limit:
            return auto
        return '%s (%s+0x%x)' % (auto, self.data[i][1], address - self.data[i][0])


def describe(address, names, regions, labels):
    """A readable place for an address: a name, or an offset into a labelled allocation."""
    bases = sorted(regions)
    i = bisect.bisect_right(bases, address) - 1
    if i >= 0:
        base = bases[i]
        size = regions[base] if isinstance(regions[base], int) else len(regions[base])
        if base <= address < base + size and labels.get(base, '') not in ('', 'data'):
            return '%s+0x%x' % (labels[base], address - base)
    return names.datum(address)


def diff_states(a, b):
    """Differences between two states: [(address, length)] over regions both have, and the
    addresses of regions only one side has."""
    ranges = []
    for address in sorted(set(a) & set(b)):
        if len(a[address]) != len(b[address]):
            ranges.append((address, max(len(a[address]), len(b[address]))))
            continue
        ranges += [(address + s, n) for s, n in changed_ranges(a[address], b[address])]
    return ranges, sorted(set(a) - set(b)), sorted(set(b) - set(a))
