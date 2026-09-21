"""The original's state and the port's, side by side (SPEC 7.2, M4).

The port keeps the original's globals in the registry of src/globals.def and its tables in
the registry of src/mission.def, with the record layouts of src/records.def.  This module
reads those registries through tests/shim.c and turns a state of the headless original -
the DATA hunk and every live allocation, as a run or a dump holds it - into the bytes of
the port's two structs, and compares the two field by field with names.

A pointer travels by the kind its field has: a shape pointer becomes a handle, a pointer
into the map a byte offset, a pointer to an allocation the port keeps at a fixed place a
flag (src/records.def).  The table of a pool is found through its pointer global.
"""
import bisect
import ctypes
import struct

DATA_START, DATA_END = 0x023000, 0x028004

K_PLAIN, K_SHAPE, K_MAP, K_POOL = 0, 1, 2, 3

# The shape containers the original keeps pointers to, by the address of the pointer, and
# the port's container slot (src/wof.h, WOF_C_*).  dash.shp and nightdash.shp share one
# pointer; which one it holds follows from night_flag when the dashboard was loaded.
SLOTS = {'WORLD': 0, 'HELLCAT': 1, 'TORPEDO': 2, 'JAPPLANE': 3, 'EIGHTH': 4, 'DASH': 5,
         'BATTLESHIP': 6, 'DESTROYER': 7, 'CRUISESHIP': 8, 'JAPCARRIER': 9, 'SELECTRANK': 10,
         'NIGHTDASH': 11}
CONTAINER_POINTERS = [
    (0x024632, 'WORLD'), (0x024636, 'EIGHTH'), (0x02463A, 'DASH'), (0x02463E, 'HELLCAT'),
    (0x024642, 'TORPEDO'), (0x02464A, 'JAPPLANE'), (0x026F34, 'BATTLESHIP'),
    (0x026F3C, 'JAPCARRIER'), (0x026F44, 'DESTROYER'), (0x026F4C, 'CRUISESHIP'),
]
NIGHT_FLAG = 0x025390


def handle(slot, index):
    return ((slot + 1) << 11) | index


class Memory:
    """A state of the original as {region base: bytes}: the DATA hunk and the allocations."""

    def __init__(self, regions, copy=True):
        self.regions = {a: bytes(b) for a, b in regions.items()} if copy else regions
        self.bases = sorted(self.regions)

    def region(self, address):
        i = bisect.bisect_right(self.bases, address) - 1
        if i < 0:
            return None
        base = self.bases[i]
        return base if address < base + len(self.regions[base]) else None

    def read(self, address, n):
        base = self.region(address)
        if base is None or address + n > base + len(self.regions[base]):
            return None
        return self.regions[base][address - base:address - base + n]

    def u(self, address, n):
        raw = self.read(address, n)
        return None if raw is None else int.from_bytes(bytes(raw), 'big')

    def size_of(self, base):
        return len(self.regions.get(base, b''))


class Shapes:
    """Every shape record the original's containers hold, by address, as a port handle."""

    def __init__(self, memory, dash_night=None):
        self.by_address = {}
        night = memory.u(NIGHT_FLAG, 2) if dash_night is None else dash_night
        for pointer, name in CONTAINER_POINTERS:
            base = memory.u(pointer, 4)
            if not base:
                continue
            if name == 'DASH' and night:
                name = 'NIGHTDASH'
            head = memory.read(base, 6)
            if head is None or head[:4] != b'PPkc':
                continue
            count = struct.unpack('>H', head[4:6])[0]
            table = memory.read(base + 6 + 4 * count, 4 * count)
            if table is None:
                continue
            first = base + 6 + 8 * count
            for i in range(count):
                offset = struct.unpack_from('>L', table, 4 * i)[0]
                self.by_address[first + offset] = handle(SLOTS[name], i)

    def handle_of(self, pointer):
        if pointer == 0:
            return 0
        return self.by_address.get(pointer)


class Layout:
    """The registries of the port, read through the shim."""

    def __init__(self, ported):
        lib = ported.lib
        self.lib = lib
        u = ctypes.c_uint
        for name, args, res in (
                ('wt_field_count', [], ctypes.c_int), ('wt_record_count', [], ctypes.c_int),
                ('wt_table_count', [], ctypes.c_int), ('wt_mission_bytes', [], ctypes.c_int),
                ('wt_field', [ctypes.c_int, ctypes.POINTER(ctypes.c_char_p), ctypes.POINTER(u)], ctypes.c_char_p),
                ('wt_record', [ctypes.c_int, ctypes.POINTER(u)], ctypes.c_char_p),
                ('wt_table', [ctypes.c_int, ctypes.POINTER(ctypes.c_char_p), ctypes.POINTER(u)], ctypes.c_char_p),
                ('wt_mission_get', [ctypes.c_int, ctypes.c_void_p, ctypes.c_int], ctypes.c_int),
                ('wt_mission_put', [ctypes.c_void_p], None),
                ('wt_globals_get', [ctypes.c_int, ctypes.c_void_p, ctypes.c_int], ctypes.c_int),
                ('wt_globals_put', [ctypes.c_void_p], None)):
            f = getattr(lib, name)
            f.argtypes = args
            f.restype = res

        self.records = {}
        numbers = (u * 8)()
        for i in range(lib.wt_record_count()):
            name = lib.wt_record(i, numbers).decode()
            self.records[name] = {'orig_size': numbers[0], 'port_size': numbers[1], 'fields': []}
        field = ctypes.c_char_p()
        for i in range(lib.wt_field_count()):
            record = lib.wt_field(i, ctypes.byref(field), numbers).decode()
            orig, elem, count, port, kind = numbers[0], numbers[1], numbers[2], numbers[3], numbers[4]
            orig_elem = 4 if kind in (K_SHAPE, K_MAP, K_POOL) else elem
            for k in range(count):
                name = field.value.decode() + ('[%d]' % k if count > 1 else '')
                self.records[record]['fields'].append(
                    (name, orig + k * orig_elem, orig_elem, port + k * elem, elem, kind))

        self.tables = []
        record = ctypes.c_char_p()
        for i in range(lib.wt_table_count()):
            name = lib.wt_table(i, ctypes.byref(record), numbers).decode()
            self.tables.append({'name': name, 'record': record.value.decode(), 'count': numbers[0],
                                'addr': numbers[1], 'pool': bool(numbers[2]),
                                'port_offset': numbers[3]})
        self.mission_bytes = lib.wt_mission_bytes()

        # The plain globals of src/globals.def: (name, address, element size, count, offset).
        self.globals = []
        for name, (elem, count, addr, offset) in ported.globals_registry().items():
            self.globals.append((name, addr, elem, count, offset))
        self.globals_bytes = ported.globals_bytes()

    # --------------------------------------------------------------- the port's bytes

    def port_mission(self, at_s=False):
        buf = ctypes.create_string_buffer(self.mission_bytes)
        n = self.lib.wt_mission_get(1 if at_s else 0, buf, self.mission_bytes)
        assert n == self.mission_bytes, 'no state to read (step S not reached?)'
        return bytearray(buf.raw)

    def port_globals(self, at_s=False):
        buf = ctypes.create_string_buffer(self.globals_bytes)
        n = self.lib.wt_globals_get(1 if at_s else 0, buf, self.globals_bytes)
        assert n == self.globals_bytes
        return bytearray(buf.raw)

    def put(self, globals_bytes, mission_bytes):
        if globals_bytes is not None:
            self.lib.wt_globals_put(ctypes.create_string_buffer(bytes(globals_bytes), len(globals_bytes)))
        if mission_bytes is not None:
            self.lib.wt_mission_put(ctypes.create_string_buffer(bytes(mission_bytes), len(mission_bytes)))

    # ---------------------------------------------------- the original as the port's bytes

    def table_base(self, table, memory):
        """Where the table's records start in the original, and how many there are."""
        rec = self.records[table['record']]
        if not table['pool']:
            return table['addr'], table['count']
        # The game's allocator puts a header of its own in front of what it hands out, so
        # the pointer lies inside the harness's allocation, not at its start.
        base = memory.u(table['addr'], 4) or 0
        region = memory.region(base) if base else None
        if region is None:
            return 0, 0
        end = region + memory.size_of(region)
        return base, min((end - base) // rec['orig_size'], table['count'])

    def expected(self, memory, shapes=None):
        """The original's state converted: (globals bytes, mission bytes, problems)."""
        shapes = shapes or Shapes(memory)
        problems = []
        g = bytearray(self.globals_bytes)
        data = memory.regions.get(DATA_START)
        for name, addr, elem, count, offset in self.globals:
            at = addr - DATA_START
            for k in range(count):
                raw = data[at + k * elem:at + (k + 1) * elem]
                if len(raw) != elem:
                    problems.append('%s: %06x is not in the state' % (name, addr))
                    continue
                g[offset + k * elem:offset + (k + 1) * elem] = bytes(raw)[::-1]
        m = bytearray(self.mission_bytes)
        map_base = memory.u(0x024628, 4) or 0
        for table in self.tables:
            rec = self.records[table['record']]
            base, count = self.table_base(table, memory)
            if not count:
                continue
            region = memory.region(base)
            blob = memory.regions[region]
            start = base - region
            size = rec['orig_size']
            for i in range(count):
                at = start + i * size
                port_at = table['port_offset'] + i * rec['port_size']
                for fname, orig, orig_elem, port, elem, kind in rec['fields']:
                    raw = bytes(blob[at + orig:at + orig + orig_elem])
                    if kind == K_PLAIN:
                        m[port_at + port:port_at + port + elem] = raw[::-1]
                        continue
                    v = int.from_bytes(raw, 'big')
                    if kind == K_SHAPE:
                        h = shapes.handle_of(v)
                        if h is None:
                            problems.append('%s[%d].%s: %08x is no shape record' % (table['name'], i, fname, v))
                            h = 0xFFFF
                        v = h
                    elif kind == K_MAP:
                        v = (v - map_base) & 0xFFFFFFFF if v else 0
                    else:
                        v = 1 if v else 0
                    m[port_at + port:port_at + port + elem] = v.to_bytes(elem, 'little')
        return g, m, problems

    # ------------------------------------------------------------------ comparison

    def fields(self):
        """Every field of both structs as (name, struct, offset, size, orig address or None)."""
        if getattr(self, '_fields', None) is not None:
            return self._fields
        out = []
        for name, addr, elem, count, offset in self.globals:
            for k in range(count):
                out.append(('%s%s' % (name, '[%d]' % k if count > 1 else ''), 'g',
                            offset + k * elem, elem, addr + k * elem))
        for table in self.tables:
            rec = self.records[table['record']]
            for i in range(table['count']):
                for fname, orig, orig_elem, port, elem, kind in rec['fields']:
                    out.append(('%s[%d].%s' % (table['name'], i, fname), 'm',
                                table['port_offset'] + i * rec['port_size'] + port, elem,
                                (table, i, orig, orig_elem)))
        self._fields = out
        return out

    def differences(self, port_g, port_m, want_g, want_m, skip=()):
        out = []
        if port_g == want_g and port_m == want_m:
            return out
        for name, which, offset, size, orig in self.fields():
            if any(name == s or name.startswith(s + '[') or name.startswith(s + '.') for s in skip):
                continue
            a = (port_g if which == 'g' else port_m)[offset:offset + size]
            b = (want_g if which == 'g' else want_m)[offset:offset + size]
            if a != b:
                out.append((name, int.from_bytes(a, 'little'), int.from_bytes(b, 'little')))
        return out
