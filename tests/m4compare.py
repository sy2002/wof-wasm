"""The port against the headless original, pass by pass and tick by tick (M4).

A script of tools/m4_scripts.py runs once under the headless original with a dump of the
state after every step, observers on the drawing routines, and a record of which addresses
each tick wrote.  The port then replays the same schedule - the keys, the raw controller
state of every VBlank, one wof_pass after each - with the fades at 0.  After every pass its
state, its drawing calls, its entropy draws and its picture's palette rows are held against
the original's, and after every tick its state, the entropy the tick drew, the drawing calls
it made and the VBlanks it waited.

Two ways of running:

  open     at the end of every step the port's registered state is set to the original's
           state after that step, with the views, the entropy stream's position and the
           mirror markers, so that every pass and every tick starts from the original's
           state before it and is compared alone (T1).
  closed   the port runs on its own from the program's start, with nothing handed over
           (T2).

A tick that waits - a lost aircraft's restart spins on WaitTOF inside the tick - waits in the
port because the port's tick waits: the schedule's VBlanks fall where they fall.
"""
import collections
import ctypes
import os
import struct
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, 'tools'))
sys.path.insert(0, HERE)

from unicorn import UC_HOOK_CODE, UC_HOOK_MEM_WRITE   # noqa: E402
from unicorn.m68k_const import UC_M68K_REG_A7, UC_M68K_REG_PC   # noqa: E402

import headless                                       # noqa: E402
import headless_dump as dump                          # noqa: E402
import map_decode                                     # noqa: E402
import pass_observe                                   # noqa: E402
import m4_scripts                                     # noqa: E402
import m4state                                        # noqa: E402
import m5_scripts                                     # noqa: E402

DRAW_OBSERVERS = ['shape_draw', 'shape_blit', 'rect_fill', 'shape_draw_xor', 'clip_set',
                  'draw_set_target', 'line_draw']

# The far-call slots the scene routines reach the blitter library through: a return address
# behind `jsr d16(a4)` with one of these displacements is a direct call.  shape_draw enters
# shape_blit with a bra, which the observer on shape_blit also sees; this tells them apart.
DIRECT_CALLS = {'shape_blit': 0x4EAC8320, 'shape_draw': 0x4EAC832C, 'rect_fill': 0x4EAC8344,
                'shape_draw_xor': 0x4EAC8338, 'draw_set_target': 0x4EAC835C,
                'line_draw': 0x4EAC837A}

# The viewports' RastPorts in the original (vport + 0x2C) and the port's viewport indices.
RASTPORTS = {0x027748 + 0x2C: 0, 0x0277F4 + 0x2C: 1, 0x0278A0 + 0x2C: 2, 0x02794C + 0x2C: 3,
             0x027296 + 0x2C: 4}
VIEW_A, VIEW_B = 0x0279F8, 0x027A06
FRONT_VIEW = 0x026E30

def signed(v, bits=16):
    v &= (1 << bits) - 1
    return v - (1 << bits) if v >> (bits - 1) else v


def entropy_state(seed, n):
    """The port's generator state after n values (src/rand.c)."""
    state = seed & 0xFFFFFFFF
    for _ in range(n):
        state = (state * 1664525 + 1013904223) & 0xFFFFFFFF
    return state


# Where main is when a mission's setup begins (the briefing has returned, for the first
# mission of a campaign and for the next ones), where its inner loop begins (step S), and
# where a mission is over (tools/reach_observe.py, WINDOW_MARKS).
MAP_LIST_POINTER = 0x024628
MISSION_WINDOW = {0x0100B2: 'setup', 0x010170: 'setup', 0x01010A: 'mission',
                  0x010132: None, 0x0101C6: None}


class Recorder(headless.Headless):
    """The headless original with, per step, the addresses its tick wrote, and every write
    made during a mission outside the tick (the completeness check, V3)."""

    def __init__(self, run, observe=DRAW_OBSERVERS, pokes=None, **options):
        super().__init__(run, observe=observe, **options)
        self.t_writes = []                        # per step: the addresses written in phase T
        self.t_windows = []                       # per tick: 'setup' for main's own, else 'mission'
        self._t = set()
        self.entropy_phase = []                   # the phase of every entropy read
        self.pokes = pokes or {}
        self.window = None
        self.mission_writes = {}                  # address -> {(window, phase, routine start)}
        self.at_s = []                            # the DATA hunk at every step S
        self._starts = {}
        for begin, end in ((headless.DATA_START, headless.DATA_END),
                           (headless.HEAP_BASE, headless.HEAP_END),
                           (headless.PLANE_BASE, headless.PLANE_END)):
            self.uc.hook_add(UC_HOOK_MEM_WRITE, self._write_t, begin=begin, end=end - 1)
        for address in MISSION_WINDOW:
            self.uc.hook_add(UC_HOOK_CODE, self._window, begin=address, end=address)
        self.map_addresses = []                   # the map list's address at every map load
        self.uc.hook_add(UC_HOOK_MEM_WRITE, self._map_pointer, begin=MAP_LIST_POINTER,
                         end=MAP_LIST_POINTER + 3)
        m5_scripts.install_pokes(self, self.pokes)

    def _window(self, uc, address, size, user):
        # A mission won goes on to the campaign's next one at 0x010132, which is M7's (the
        # port's stand-in ends the campaign there); nothing after it is recorded as a mission.
        if address == 0x010132:
            if not getattr(self, 'won', False):
                self.next_mission_pass = self.passes      # the last pass of the won mission
            self.won = True
        self.window = None if getattr(self, 'won', False) else MISSION_WINDOW[address]
        if self.window == 'mission':
            self.at_s.append(bytes(self.o.read(headless.DATA_START,
                                               headless.DATA_END - headless.DATA_START)))

    def _map_pointer(self, uc, access, address, size, value, user):
        if address == MAP_LIST_POINTER and size == 4 and value:
            self.map_addresses.append(value)

    def _beam_read(self, uc, access, address, size, value, user):
        before = len(self.entropy_log)
        super()._beam_read(uc, access, address, size, value, user)
        if len(self.entropy_log) > before:
            self.entropy_phase.append(self.phase())

    def _write_t(self, uc, access, address, size, value, user):
        if self.in_tick and address < headless.PLANE_BASE:
            self._t.update(range(address, address + size))
        if self.window is None:
            return
        pc = uc.reg_read(UC_M68K_REG_PC)
        start = self._starts.get(pc)
        if start is None:
            start = self._starts[pc] = self.names.routine_start(pc)
        key = (self.window, self.phase(), start)
        for a in range(address, address + size):
            slot = self.mission_writes.get(a)
            if slot is None:
                self.mission_writes[a] = {key}
            else:
                slot.add(key)

    def _step(self, kind):
        super()._step(kind)
        self.t_writes.append(self._t)
        self._t = set()
        if kind == 'T':
            self.t_windows.append(self.window)


def record(name, dump_path, rate=2, pokes=None, more=None):
    """One script under the headless original, dumped to `dump_path`."""
    import m6_scripts
    description = m6_scripts.script(name, vblanks_per_pass=rate, **(more or {}))
    machine = Recorder(description, pokes=pokes)
    machine.open_dump(dump_path)
    try:
        machine.run()
    finally:
        machine.close()
    return machine


class Replay:
    """The port driven through a recorded run."""

    def __init__(self, ported, machine, dump_path, mode='open', rate=2, pokes=None):
        self.ported = ported
        self.lib = ported.lib
        self.machine = machine
        self.dump_path = dump_path
        self.mode = mode
        self.rate = rate
        self.layout = m4state.Layout(ported)
        self.pokes = pokes or {}
        self.names = dump.Names(ROOT)
        lib = self.lib
        for name, args, res in (
                ('wt_pass_mission_get', [ctypes.c_void_p, ctypes.c_int], ctypes.c_int),
                ('wt_pass_globals_get', [ctypes.c_void_p, ctypes.c_int], ctypes.c_int),
                ('wt_pass_view', [ctypes.c_int], ctypes.c_int),
                ('wt_views_set', [ctypes.c_int], None),
                ('wt_entropy_set', [ctypes.c_uint], None),
                ('wt_markers_put', [ctypes.c_void_p, ctypes.c_void_p], None),
                ('wt_markers_get', [ctypes.c_void_p, ctypes.c_void_p], None),
                ('wt_present', [], None),
                ('wof_palette_rows', [], ctypes.c_void_p),
                ('wof_palettes', [], ctypes.c_void_p),
                ('wof_palette_count', [], ctypes.c_uint32),
                ('wof_palette_colours', [], ctypes.c_uint32),
                ('wt_set_tick_hook', [ctypes.c_void_p], None),
                ('wt_set_step_s_hook', [ctypes.c_void_p], None),
                ('wt_set_pass_hook', [ctypes.c_void_p], None),
                ('wt_set_vblanks_per_pass', [ctypes.c_int], None),
                ('wof_vblank_count', [], ctypes.c_uint32),
                ('wt_pokes_clear', [], None),
                ('wt_poke', [ctypes.c_uint, ctypes.c_uint, ctypes.c_uint], None),
                ('wt_poke_reset', [ctypes.c_uint, ctypes.c_uint, ctypes.c_uint], None),
                ('wt_poke_address', [ctypes.c_uint, ctypes.c_uint, ctypes.c_uint, ctypes.c_uint],
                 None),
                ('wt_map_addresses', [ctypes.c_void_p, ctypes.c_uint], None),
                ('wt_standin_count', [], ctypes.c_int),
                ('wt_standin', [ctypes.c_int, ctypes.POINTER(ctypes.c_uint)], ctypes.c_char_p),
                ('wt_standins_reset', [], None),
                ('wt_ticks_run', [], ctypes.c_uint),
                ('wt_passes_run', [], ctypes.c_uint)):
            f = getattr(lib, name)
            f.argtypes = args
            f.restype = res
        self._hook = None

    def map_addresses(self):
        """The map list's address (the pointer at 0x024628) at every map load of the run."""
        return list(getattr(self.machine, 'map_addresses', []))

    # ------------------------------------------------------------------ the schedule

    def groups(self):
        """The schedule as (VBlank entries, the step entry that follows them)."""
        pending = []
        for entry in self.machine.schedule:
            if entry[0] == 'V':
                pending.append(entry)
            else:
                yield pending, entry
                pending = []

    def inside_tick_waits(self):
        """VBlanks inside each tick of the original, by tick number from 1: the V entries
        between the step before a T and the T.  A tick starts right after the pass or the
        tick before it, with nothing that could wait in between."""
        out = {}
        previous = None
        tick = 0
        for vs, step in self.groups():
            if step[0] == 'T':
                tick += 1
                out[tick] = len(vs) if previous in ('P', 'T', 'S') else 0
            previous = step[0]
        return out

    def build_index(self, memory):
        """address -> (struct, port offset of the field, field size, byte in the field, kind)
        for every plain field whose place in the original is fixed (globals and DATA
        tables) or known through its pool's pointer now."""
        index = {}
        for name, addr, elem, count, offset in self.layout.globals:
            for k in range(count):
                for b in range(elem):
                    index[addr + k * elem + b] = ('g', offset + k * elem, elem, b, m4state.K_PLAIN,
                                                  addr + k * elem)
        for table in self.layout.tables:
            rec = self.layout.records[table['record']]
            base, count = self.layout.table_base(table, memory)
            for i in range(count):
                for fname, orig, orig_elem, port, elem, kind in rec['fields']:
                    field_at = base + i * rec['orig_size'] + orig
                    for b in range(orig_elem):
                        index[field_at + b] = (
                            'm', table['port_offset'] + i * rec['port_size'] + port, elem, b, kind,
                            field_at)
        self.index = index
        return index

    # ---------------------------------------------------------------- the injection

    def inject(self, memory, head):
        """The port's registered state, views, entropy and markers set to a state of the
        original (the open loop)."""
        g, m, problems = self.layout.expected(memory, getattr(self, 'shapes', None))
        assert not problems, problems[:5]
        self.layout.put(g, m)
        front = memory.u(FRONT_VIEW, 4)
        self.lib.wt_views_set(1 if front == VIEW_B else 0)
        self.lib.wt_entropy_set(entropy_state(1, head['entropy']))
        hell = (ctypes.c_uint8 * 128)()
        torp = (ctypes.c_uint8 * 128)()
        for slot, arr, pointer in ((1, hell, 0x02463E), (2, torp, 0x024642)):
            base = memory.u(pointer, 4)
            count = memory.u(base + 4, 2)
            table = base + 6 + 4 * count
            first = base + 6 + 8 * count
            for i in range(min(count, 128)):
                off = memory.u(table + 4 * i, 4)
                arr[i] = memory.u(first + off + 8, 2) & 0xFF
        self.lib.wt_markers_put(hell, torp)

    # ------------------------------------------------------------------ the replay

    def run(self, on_pass=None, on_setup=None, files=None, on_tick=None, raw=None,
            on_reset=None):
        """Replay the schedule's VBlanks through the port.  Everything else happens in the
        port's own hooks, at the points where the original's steps end: step S, the end of
        a pass (where both loops compare) and the end of a tick.  The open loop sets the
        port to the original's state at the end of every step, so that every pass and every
        tick starts from the original's state before it, owed VBlanks included; the closed
        loop hands over nothing.  A pass may begin without a VBlank before it - after the
        restart's waits in the tick - so none of this can be tied to the VBlank entries."""
        ported = self.ported
        keys = collections.defaultdict(list)
        for vblank, code, qualifier in self.machine.key_log:
            keys[vblank].append((code, qualifier))

        ported.reset_core(fade_vblanks=0)
        if on_reset:
            on_reset(self)
        for fname, data in (files or {}).items():
            assert ported.fs_write(fname, data), fname      # laid over the disk, as the run's
        self.lib.wt_set_vblanks_per_pass(self.rate)
        self.lib.wt_standins_reset()
        self.lib.wt_pokes_clear()
        for at, items in m5_scripts.poke_points(self.pokes).items():
            poke = self.lib.wt_poke if at == m5_scripts.RANK_END else self.lib.wt_poke_reset
            assert at in (m5_scripts.RANK_END, m5_scripts.MISSION_RESET), hex(at)
            for address, size, value in items:
                # A global, or an element of a global array (the wrecks' words of
                # tools/m6_scripts.py's wrecks_a): the element's offset in the port's struct;
                # else a record of a table (burning_a's aircraft), by its address.
                entry = next((e for e in self.layout.globals
                              if e[1] <= address < e[1] + e[2] * e[3]), None)
                if entry is None:
                    self.lib.wt_poke_address(address, size, value,
                                             0 if at == m5_scripts.RANK_END else 1)
                    continue
                poke(entry[4] + (address - entry[1]), size, value)
        # The address the harness's allocator gave the map list at every map load, which the
        # port takes as it takes the entropy stream (re/notes/porting-m5.md, "The wreck").
        addresses = self.map_addresses()
        self._addresses = (ctypes.c_uint32 * max(len(addresses), 1))(*addresses)
        self.lib.wt_map_addresses(self._addresses, len(addresses))

        self.reader = dump.DumpReader(self.dump_path)
        self.current = None              # (memory, head) of the last step consumed
        self.upcoming = None             # the head read ahead, not yet applied
        self.passes = 0
        self.ticks = 0
        self.errors = []
        self.missions = 0
        self.waits = self.inside_tick_waits()
        self.vblank_mark = None
        self.stopped = None              # a reason a comparison gives for ending the replay

        one = ctypes.CFUNCTYPE(None, ctypes.c_uint32)
        two = ctypes.CFUNCTYPE(None, ctypes.c_uint32, ctypes.c_uint32)

        def guarded(function):
            def call(*args):
                try:
                    function(*args)
                except Exception as error:          # an exception must not cross into C
                    self.errors.append(error)
            return call

        def at_s(mission):
            memory, head = self.advance_to(lambda h: h['kind'] == 'S' and h['mission'] == mission)
            self.shapes = m4state.Shapes(memory)
            self.missions = mission
            self.flash_before = memory.u(0x025416, 2)
            if on_setup:
                on_setup(self, memory, head)
            if self.mode == 'open':
                self.inject(memory, head)
            self.vblank_mark = self.lib.wof_vblank_count()

        def at_pass(number, end):
            if not end:
                self.lib.wt_trace_reset()
                return
            memory, head = self.advance_to(lambda h: h['kind'] == 'P' and h['pass'] == number)
            self.passes = number
            if on_pass:
                on_pass(self, memory, head, number)
            self.flash_before = memory.u(0x025416, 2)
            if self.mode == 'open':
                self.inject(memory, head)
            self.lib.wt_trace_reset()
            self.vblank_mark = self.lib.wof_vblank_count()

        def at_tick(tick):
            memory, head = self.advance_to(lambda h: h['kind'] == 'T' and h['tick'] == tick + 1)
            self.ticks = tick + 1
            if tick < len(self.machine.t_windows) and self.machine.t_windows[tick] == 'setup':
                # main's own tick in a mission's setup: the shapes of the new mission's
                # containers, and the setup's drawing and entropy are the setup's, which step
                # S compares; this tick's own state is compared as any other's.
                self.shapes = m4state.Shapes(memory)
                self.setup_tick = True
            else:
                self.setup_tick = False
            if on_tick and self.missions:
                waited = self.lib.wof_vblank_count() - self.vblank_mark
                on_tick(self, memory, head, tick + 1, waited)
            self.flash_before = memory.u(0x025416, 2)
            if self.mode == 'open':
                self.inject(memory, head)
            if not self.setup_tick:
                self.lib.wt_trace_reset()         # the setup's own trace is read at step S
            self.vblank_mark = self.lib.wof_vblank_count()

        self._hooks = [one(guarded(at_s)), two(guarded(at_pass)), one(guarded(at_tick))]
        self.lib.wt_set_step_s_hook(ctypes.cast(self._hooks[0], ctypes.c_void_p))
        self.lib.wt_set_pass_hook(ctypes.cast(self._hooks[1], ctypes.c_void_p))
        self.lib.wt_set_tick_hook(ctypes.cast(self._hooks[2], ctypes.c_void_p))

        vblank = 0
        last_pass = max((h for h in self.machine.step_hashes if h[0] == 'P'),
                        key=lambda h: h[2], default=(None, 0, 0, None))[2]
        try:
            for entry in self.machine.schedule:
                if entry[0] != 'V':
                    continue
                vblank += 1
                for code, qualifier in keys.get(vblank, ()):
                    ported.key(code, qualifier)
                ported.vblank(raw(entry[1]) if raw else entry[1])
                ported.pass_()
                if self.errors:
                    raise self.errors[0]
                if self.passes >= last_pass and last_pass:
                    break
                if self.stopped:
                    break
        finally:
            self.lib.wt_set_tick_hook(None)
            self.lib.wt_set_step_s_hook(None)
            self.lib.wt_set_pass_hook(None)
        if self.errors:
            raise self.errors[0]
        return self.passes

    def _next_head(self):
        if self.upcoming is None:
            self.upcoming = next(self.reader, None)
        return self.upcoming

    def _consume(self):
        head = self._next_head()
        self.upcoming = None
        memory = m4state.Memory(self.reader.regions, copy=False)
        self.current = (memory, head)
        return self.current

    def advance_to(self, wanted):
        """Consume dump steps up to and including the first one `wanted` accepts."""
        while True:
            head = self._next_head()
            if head is None:
                raise AssertionError('the dump ran out before the port did')
            self._consume()
            if wanted(head):
                return self.current

    def advance_before(self, wanted):
        """Consume dump steps up to the one before the first one `wanted` accepts."""
        while True:
            head = self._next_head()
            if head is None or wanted(head):
                return self.current
            self._consume()

    def s_states(self):
        """The original's state at every step S of the run, with its step header."""
        out = []
        reader = dump.DumpReader(self.dump_path)
        for head in reader:
            if head['kind'] == 'S':
                out.append((m4state.Memory({a: bytes(b) for a, b in reader.regions.items()}), head))
        return out

    # ------------------------------------------------------------------ comparisons

    def port_pass_state(self):
        gb = ctypes.create_string_buffer(self.layout.globals_bytes)
        mb = ctypes.create_string_buffer(self.layout.mission_bytes)
        assert self.lib.wt_pass_globals_get(gb, self.layout.globals_bytes) > 0
        assert self.lib.wt_pass_mission_get(mb, self.layout.mission_bytes) > 0
        return bytearray(gb.raw), bytearray(mb.raw)

    def state_differences(self, memory, skip=(), live=False):
        if live:
            pg, pm = self.layout.port_globals(), self.layout.port_mission()
        else:
            pg, pm = self.port_pass_state()
        wg, wm, problems = self.layout.expected(memory, getattr(self, 'shapes', None))
        return problems + ['%s: port %x original %x' % d
                           for d in self.layout.differences(pg, pm, wg, wm, skip)]

    def standins(self):
        out = []
        count = ctypes.c_uint()
        for i in range(self.lib.wt_standin_count()):
            marker = self.lib.wt_standin(i, ctypes.byref(count)).decode()
            out.append((marker, count.value))
        return out

    # The drawing calls of one pass, as tuples both sides can give.
    def _by_pass(self):
        if getattr(self, '_observed_by_pass', None) is None:
            by = collections.defaultdict(list)
            for o in self.machine.observed:
                if o['phase'] == 'F':
                    by[o['pass']].append(o)
            self._observed_by_pass = by
            ent = collections.defaultdict(list)
            for (i, value, routine, v, p, t), phase in zip(self.machine.entropy_log,
                                                           self.machine.entropy_phase):
                if phase == 'F':
                    ent[p].append((value, routine))
            self._entropy_by_pass = ent
        return self._observed_by_pass

    def _by_tick(self):
        """The original's drawing calls and entropy reads inside each tick, by tick number
        from 1 (the harness counts a tick when it returns)."""
        if getattr(self, '_observed_by_tick', None) is None:
            by = collections.defaultdict(list)
            for o in self.machine.observed:
                if o['phase'] == 'T':
                    by[o['tick'] + 1].append(o)
            self._observed_by_tick = by
            ent = collections.defaultdict(list)
            for (i, value, routine, v, p, t), phase in zip(self.machine.entropy_log,
                                                           self.machine.entropy_phase):
                if phase == 'T':
                    ent[t + 1].append((value, routine))
            self._entropy_by_tick = ent
        return self._observed_by_tick

    def original_tick_calls(self, memory, tick):
        return self.original_calls(memory, None, self._by_tick().get(tick, ()))

    def original_tick_entropy(self, tick):
        self._by_tick()
        return self._entropy_by_tick.get(tick, [])

    def marker_differences(self, memory):
        """The mirror markers (+8) of hellcat.shp and Torpedo.shp, the port's against the
        original's: game state that lives in the containers (re/notes/shapes.md)."""
        hell = (ctypes.c_uint8 * 128)()
        torp = (ctypes.c_uint8 * 128)()
        self.lib.wt_markers_get(hell, torp)
        out = []
        for slot, arr, pointer in ((1, hell, 0x02463E), (2, torp, 0x024642)):
            base = memory.u(pointer, 4)
            count = memory.u(base + 4, 2)
            table = base + 6 + 4 * count
            first = base + 6 + 8 * count
            for i in range(min(count, 128)):
                want = memory.u(first + memory.u(table + 4 * i, 4) + 8, 2) & 0xFF
                if arr[i] != want:
                    out.append((slot, i, 'port', arr[i], 'original', want))
        return out

    def original_calls(self, memory, pass_number, observations=None):
        shapes = getattr(self, 'shapes', None) or m4state.Shapes(memory)
        out = []
        if observations is None:
            observations = self._by_pass().get(pass_number, ())
        for o in observations:
            r = o['routine']
            want = DIRECT_CALLS.get(r)
            if want is not None:
                before = self.machine.o.r32(o['caller'] - 4)
                if before != want:
                    continue
            d, a = o['d'], o['a']
            if r in ('shape_draw', 'shape_blit', 'shape_draw_xor'):
                h = shapes.handle_of(a[0])
                if a[0] == 0:
                    out.append((r, 0, None, None))
                else:
                    out.append((r, h, signed(d[0]), signed(d[1])))
            elif r == 'rect_fill':
                out.append((r, signed(d[0]), signed(d[1]), signed(d[2]), signed(d[3]), d[4] & 0xFF))
            elif r == 'clip_set':
                out.append((r, signed(d[0]), signed(d[1]), signed(d[2]), signed(d[3])))
            elif r == 'line_draw':
                out.append((r, signed(d[0]), signed(d[1]), signed(d[2]), signed(d[3]), d[4] & 0xFF))
            elif r == 'draw_set_target':
                out.append((r, RASTPORTS.get(a[0], -1)))
        return out

    def port_calls(self):
        out = []
        for t in self.ported.traces():
            w = t['what']
            if w == 'shape_draw':
                out.append(('shape_draw', 0, None, None) if t['d'] else
                           ('shape_draw', t['c'], t['a'], t['b']))
            elif w == 'shape_blit':
                out.append(('shape_blit', t['c'], t['a'], t['b']))
            elif w == 'shape_xor_c':
                pass
            elif w == 'shape_draw_xor':
                out.append(('shape_draw_xor', 0, None, None) if t['d'] else
                           ('shape_draw_xor', t['c'], t['a'], t['b']))
            elif w == 'rect_fill':
                out.append(('rect_fill', t['a'], t['b'], signed(t['c']), t['d'], (t['c'] >> 16) & 0xFF))
            elif w == 'clip_set':
                out.append(('clip_set', t['a'], t['b'], t['c'], t['d']))
            elif w == 'line_draw':
                out.append(('line_draw', t['a'], t['b'], signed(t['c']), t['d'], (t['c'] >> 16) & 0xFF))
            elif w == 'draw_set_target':
                out.append(('draw_set_target', t['a']))
        return out

    def original_entropy(self, pass_number):
        self._by_pass()
        return self._entropy_by_pass.get(pass_number, [])

    def port_entropy(self):
        return [(t['a'], self.names.routine(t['c'])) for t in self.ported.traces('rand_beam')]

    # --------------------------------------------------- V1 (d): the palette of every row

    COLTABS = {VIEW_A: (0x027A18, 0x027B58, 0x027A98), VIEW_B: (0x027A58, 0x027B98, 0x027AD8)}
    COLTAB_TICKER = 0x027B18
    TICKER_RAMP = 0x025994

    def expected_rows(self, memory):
        """What the original's copper shows on each of the 214 output rows after the pass:
        12-bit colours per row, or None for a blank row.  The front view's first viewport
        takes table 1 above the split line and table 2 below it where table 2 differs, with
        COLOR01 above it as flip_buffers poked it; the dashboard its own table; the ticker
        its COLOR01 ramp (re/notes/display.md).  Built from the original's colour tables and
        split_row alone, which is what makes it a separate voice."""
        front = memory.u(FRONT_VIEW, 4)
        t1a, t2a, dasha = self.COLTABS[front]
        t1 = [memory.u(t1a + 2 * i, 2) for i in range(32)]
        t2 = [memory.u(t2a + 2 * i, 2) for i in range(32)]
        dash = [memory.u(dasha + 2 * i, 2) for i in range(16)]
        ticker = [memory.u(self.COLTAB_TICKER + 2 * i, 2) for i in range(2)]
        ramp = [memory.u(self.TICKER_RAMP + 2 * i, 2) for i in range(10)]
        # The sky's flash: flip_buffers pokes COLOR01 of the list it shows with flash_colour
        # when the count it found was odd, and counts it down (re/notes/porting-m5.md, "The
        # sky's flash").  The count it found is the one the step before the pass left.
        colour1 = t1[1]
        before = getattr(self, 'flash_before', 0)
        if before and before & 1:
            colour1 = memory.u(0x025418, 2)
        split = min(signed(memory.u(0x0253A0, 2)), 162)
        rows = []
        for y in range(214):
            if y < 162:
                if y < split:
                    row = list(t1)
                else:
                    row = [b if b != a else a for a, b in zip(t1, t2)]
                if y < split or t2[1] == t1[1]:
                    row[1] = colour1
                rows.append(row)
            elif 163 <= y < 200:
                rows.append(dash)
            elif y >= 201:
                rows.append([ticker[0], ramp[min(y - 201, 9)]])
            else:
                rows.append(None)
        return rows

    def port_rows(self):
        """The port's picture after the pass, as 12-bit colours per row: the entries of each
        row's palette, as many as the model gives for that row."""
        self.lib.wt_present()
        rows = []
        pr = ctypes.string_at(self.lib.wof_palette_rows(), 214 * 2)
        count = self.lib.wof_palette_colours()
        pal = ctypes.string_at(self.lib.wof_palettes(), self.lib.wof_palette_count() * count * 4)
        for y in range(214):
            p = int.from_bytes(pr[2 * y:2 * y + 2], 'little')
            if p == 0:
                rows.append(None)
                continue
            row = []
            for i in range(count):
                rgba = int.from_bytes(pal[(p * count + i) * 4:(p * count + i) * 4 + 4], 'little')
                r, g, b = rgba & 0xFF, (rgba >> 8) & 0xFF, (rgba >> 16) & 0xFF
                row.append(((r // 17) << 8) | ((g // 17) << 4) | (b // 17))
            rows.append(row)
        return rows

    def view_difference(self, memory):
        """Which of the two views is in front: the original keeps the pointer front_view,
        the port the view's index.  None when they agree."""
        want = 1 if memory.u(FRONT_VIEW, 4) == VIEW_B else 0
        got = self.lib.wt_front_view()
        return None if got == want else ('port', got, 'original', want)

    def row_differences(self, memory):
        want = self.expected_rows(memory)
        got = self.port_rows()
        out = []
        for y, (a, b) in enumerate(zip(got, want)):
            if b is None or a is None:
                if (a is None) != (b is None):
                    out.append((y, a, b))
                continue
            if a[:len(b)] != b:
                out.append((y, a[:len(b)], b))
        return out

    # --------------------------------------------------- V1 (e): the map, a third voice

    SHIPS = [(0x02537A, 0x025460), (0x025377, 0x02547E), (0x02537B, 0x02549C),
             (0x025378, 0x0254BA), (None, 0x0254D8)]

    def predicted_map_draws(self, memory, chart):
        """The map draws of the pass as tools/map_decode.py predicts them from the map file
        and the original's view: record, slot and position before the hotspot."""
        px = memory.u(0x026E5C, 2)
        step = memory.u(0x024F36, 2)
        shift = memory.u(0x024F34, 2)
        split = memory.u(0x0253A0, 2)
        ybase = signed(memory.u(0x026E56, 2))
        table = memory.u(0x026F82 if step == 1 else 0x026F54, 4)

        def ride(world_x):
            offset = signed(((world_x >> 3) * 2) & 0xFFFF)
            for flag, base in self.SHIPS:
                if flag is not None and not memory.u(flag, 1):
                    continue
                if signed(memory.u(base, 2)) <= offset <= signed(memory.u(base + 2, 2)):
                    value = signed(memory.u(base + 0x1A, 2)) + ybase
                    return value >> 3 if shift else value
            return 0

        found = map_decode.draw_list(chart, px, step, shift, split,
                                     lambda slot: memory.u(table + 4 * slot, 4) != 0, ride)
        return [(index, slot, signed(x), signed(y)) for index, slot, x, y, _ in found]

    def live_chart(self, memory):
        """The map as the original holds it at this step, for tools/map_decode.py's draw list:
        the record list read from the original's allocation (the pointer at 0x024628) with
        the length of map_length (0x0253C6, in bytes), which the hits rewrite during a
        mission."""
        pointer = memory.u(MAP_LIST_POINTER, 4)
        length = memory.u(0x0253C6, 2)
        if getattr(self, '_chart_key', None) != (pointer, length):
            chart = object.__new__(map_decode.Map)
            chart.name = 'live'
            chart.length = length
            chart.on_disk = length // 2
            chart.padding = 0
            chart.extent = (length * 4) & 0xFFFF
            self._chart_key, self._chart = (pointer, length), chart
        chart = self._chart
        chart.words = list(struct.unpack('>%dH' % (length // 2), memory.read(pointer, length & ~1)))
        return chart

    def port_map_draws(self):
        return [(t['a'], t['b'], t['c'], t['d']) for t in self.ported.traces('map_draw')]
