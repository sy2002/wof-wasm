"""The headless original: the game's own 68000 code, from `main` on, under Unicorn.

The operating system (headless_os.py), the hardware and time are stubs; no game logic is
re-implemented.  The program runs until it waits, and only where it waits do VBlanks occur:

  * the two spins on vblank_flag (wait_vblank, wait_next_vblank): VBlanks until the flag is set
  * graphics.WaitTOF: one VBlank;  dos.Delay(n): n fiftieths of a second in VBlanks
  * frame_update's entry, the start of a pass: as many VBlanks as the schedule still owes,
    so that a pass begins every `vblanks_per_pass` VBlanks

A VBlank sets the controller registers from the script and then runs the VBlank servers the
game installed with AddIntServer, in priority order, as nested calls.  The input byte, the
tap and hold latches, the queue and the ticker are therefore the original's own work.
Nothing depends on instruction counts or on how fast the emulator is.

Reads of the beam position 0xDFF006 take the next value of the entropy stream, the same
generator the port has in src/rand.c.  The crack's text screen is skipped.  The music player
is not run; calls into it are recorded.

    .venv/bin/python tools/headless.py run RUN.json --out DUMP [--changes REPORT]
    .venv/bin/python tools/headless.py show DUMP [--step N]
    .venv/bin/python tools/headless.py diff DUMP_A DUMP_B [--step N]

The run description, the dump format and the change report are described in
re/notes/headless.md.
"""
import argparse
import collections
import functools
import json
import os
import struct
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)

from unicorn import UcError, UC_HOOK_CODE, UC_HOOK_MEM_READ, UC_HOOK_MEM_WRITE        # noqa: E402
from unicorn.m68k_const import (                                                       # noqa: E402
    UC_M68K_REG_A0, UC_M68K_REG_A7, UC_M68K_REG_D0, UC_M68K_REG_PC, UC_M68K_REG_SR)

from capstone import Cs, CS_ARCH_M68K, CS_MODE_M68K_000                                # noqa: E402

import disasm                                                                          # noqa: E402
import headless_dump as dump                                                           # noqa: E402
from headless_os import AmigaOS, HarnessError                                          # noqa: E402
from oracle import Oracle                                                              # noqa: E402

A4 = 0x02AFFE

# ---- memory map.  The oracle maps 0x000000-0x1FFFFF and loads the executable at 0x010000.
LIB_AREA   = 0x0C0000            # fake library bases, LIB_SPAN each: jump table below, data above
LIB_SPAN   = 0x2000
LIB_NAMES  = ['exec', 'dos', 'graphics', 'intuition', 'device']
# input.device and console.device share the one device base; no fd file names a device's
# functions, so the ones the game calls are named here.
DEVICE_FUNCTIONS = {48: 'RawKeyConvert'}
MATH_BASE  = 0x0CE000            # mathffp.library: its jump table leads into the Kickstart ROM
SEG_AREA   = 0x0D0000            # fake segments for LoadSeg, SEG_SPAN each
SEG_SPAN   = 0x100
SCRATCH    = 0x0D8000            # records the stubs hand out: a Task, an InputEvent
MAIN_STACK_TOP   = 0x0F0000      # the main program's stack
NESTED_STACK_TOP = 0x0FF000      # interrupt servers and callbacks, 0x2000 per nesting level
END_TRAP    = 0x0FFF00           # main returns here
NESTED_TRAP = 0x0FFF10           # nested calls return here
OBSERVE_TRAMPOLINE = 0x0FFE00    # `move.w sr,OBSERVE_CCR; jmp OBSERVE_TRAP`, for a return observer
OBSERVE_CCR   = 0x0FFE10
OBSERVE_TRAP  = 0x0FFE20
HEAP_BASE, HEAP_END   = 0x200000, 0xA00000      # AllocMem, except display memory
PLANE_BASE, PLANE_END = 0xA00000, 0xB00000      # what display_alloc_chip asks for: planes, copper lists
CIA_BASE, CIA_SIZE = 0xBFD000, 0x2000
CUSTOM   = 0xDFF000
VHPOSR   = 0xDFF006
JOY1DAT  = 0xDFF00C
CIAA_PRA = 0xBFE001

# ---- the original
MAIN               = 0x010006
TICK_RETURNS       = (0x0100F6, 0x0114F4, 0x01CE02)   # behind the three calls of logic_tick: main's own
                                                      # at a mission's start, run_queued_ticks, the key handler
MISSION_START      = 0x01010A    # once per mission, just before the inner loop
INNER_LOOP         = 0x01010E
PASS_END           = 0x010192    # frame_update, which falls into flip_buffers, has returned
FRAME_UPDATE       = 0x010228
LOGIC_TICK         = 0x011386
SERVER_AFTER_SAMPLE = 0x0117D8   # vblank_server, just after read_joystick filled input_byte
READ_JOY_BITS      = 0x01520E
DISPLAY_ALLOC_CHIP = 0x0165CC
SPINS              = (0x01AA36, 0x01AA44)        # tst.b vblank_flag in wait_next_vblank, wait_vblank
CRACK_SCREEN       = 0x01F41A
RAND_BEAM          = 0x0203BE
READ_VHPOSR        = 0x015D5A
DATA_START, DATA_END = 0x023000, 0x028004
PASS_COUNTER = 0x0253C8
OPT_INVERT_VERTICAL = 0x0254F6
VBLANK_FLAG  = 0x0255BE
VBLANK_COUNTER = 0x026C92
TICK_INPUT   = 0x026D42
DEMO_MODE    = 0x026D4C
DOSBASE_VAR  = 0x026F1E
SYSBASE_VAR  = 0x026F74
INPUT_BYTE   = 0x027366

# The bits wof_vblank takes: U is the stick pushed forward, which is up in the menus and climbs.
RAW_BITS = {'U': 1, 'D': 2, 'R': 4, 'L': 8, 'F': 16}

# The IEQUALIFIER bits a key of a raw segment may carry, by name.  The game reads one of them,
# IEQUALIFIER_CONTROL, and key_qualifier_mask filters on them (re/notes/keys.md).
QUALIFIERS = {'lshift': 0x0001, 'rshift': 0x0002, 'capslock': 0x0004, 'ctrl': 0x0008,
              'lalt': 0x0010, 'ralt': 0x0020, 'lamiga': 0x0040, 'ramiga': 0x0080,
              'numpad': 0x0100, 'repeat': 0x0200}

DEFAULT_RUN = {
    'format': 'wof-headless-run', 'version': 1,
    'entropy': {'seed': 1},
    'video_hz': 50,
    'vblanks_per_pass': 2,
    'raw': [],
    'stop': {'ticks': 100},
}




# ------------------------------------------------------------------ the Kickstart ROM
# Two parts of the owner's ROM run for real, and the build needs one of them as well: the
# key conversion table of SPEC 5 step 1 comes from the same RawKeyConvert with the same
# keymap that a run uses (tools/extract_tables.py, re/notes/keys.md).  The three lookups
# take the ROM image and its base so that both callers can use them.

def rom_resident(rom, base, name):
    """The offset of a resident module of the ROM, found by its name."""
    wanted = name.encode() + b'\0'
    for offset in range(0, len(rom) - 26, 2):
        if rom[offset:offset + 2] != b'\x4a\xfc' or struct.unpack_from('>L', rom, offset + 2)[0] != base + offset:
            continue
        at = struct.unpack_from('>L', rom, offset + 14)[0] - base
        if rom[at:at + len(wanted)] == wanted:
            return offset
    return None


def rom_vectors(rom, base, table):
    """A library or device function table of the ROM, as MakeLibrary reads it."""
    at, vectors = table - base, []
    if struct.unpack_from('>h', rom, at)[0] == -1:                # word offsets from the table
        at += 2
        while struct.unpack_from('>h', rom, at)[0] != -1:
            vectors.append(table + struct.unpack_from('>h', rom, at)[0])
            at += 2
    else:
        while struct.unpack_from('>l', rom, at)[0] != -1:
            vectors.append(struct.unpack_from('>L', rom, at)[0])
            at += 4
    return vectors


def find_rom_console(rom, base):
    """console.device's RawKeyConvert and the keymap it converts with, both found in the
    ROM by their contents, as re/notes/system-font.md finds topaz 8.

    The resident module is found by its name.  It is not RTF_AUTOINIT, so its init code
    builds the device itself; that code begins with a movem and three `lea d16(pc),Ax`,
    of which the first gives the function table.  RawKeyConvert is LVO -48, the eighth
    entry.  The keymap is the one the ROM's console.device uses when a caller passes
    none: its LoKeyMap is found by the QWERTY row and the KeyMap record by a pointer to
    it.  Returns (RawKeyConvert, KeyMap), either of them None when it is not found."""
    if rom is None:
        return None, None
    convert = keymap = None
    offset = rom_resident(rom, base, 'console.device')
    if offset is not None:
        init = struct.unpack_from('>L', rom, offset + 22)[0] - base
        for at in range(init, init + 16, 2):
            if rom[at:at + 2] == b'\x41\xfa':                     # lea d16(pc),a0
                vectors = rom_vectors(rom, base, base + at + 2 + struct.unpack_from('>h', rom, at + 2)[0])
                if len(vectors) == 8:
                    convert = vectors[7]
                break
    # The LoKeyMap holds four bytes per raw code: alt-shift, alt, shift, plain.  Key 0x10
    # is the first of the QWERTY row, 0x21 and 0x22 the next two of the home row.
    for at in range(0, len(rom) - 0x100, 2):                   # at is the LoKeyMap itself
        if (rom[at + 0x10 * 4 + 2:at + 0x10 * 4 + 4] != b'Qq' or
                rom[at + 0x11 * 4 + 2:at + 0x11 * 4 + 4] != b'Ww' or
                rom[at + 0x21 * 4 + 2:at + 0x21 * 4 + 4] != b'Ss'):
            continue
        found = rom.find(struct.pack('>L', base + at))            # km_LoKeyMap, the second long
        if found > 4:
            keymap = base + found - 4
        break
    return convert, keymap


class Stuck(HarnessError):
    pass


def entropy_values(seed):
    """The generator of src/rand.c: values shaped like VHPOSR."""
    state = seed & 0xFFFFFFFF
    while True:
        state = (state * 1664525 + 1013904223) & 0xFFFFFFFF
        yield (((state >> 24) & 0xFF) << 8) | (((state >> 8) & 0xFFFF) % 0xE4)


def raw_state(text):
    value = 0
    for letter in text.upper():
        if letter in RAW_BITS:
            value |= RAW_BITS[letter]
        elif letter not in '-. ':
            raise ValueError('controller state %r: use the letters U D L R F' % text)
    return value


def qualifier_word(given):
    """A key's qualifier word: a number, or names of IEQUALIFIER bits joined with +."""
    if not isinstance(given, str):
        return int(given)
    word = 0
    for name in given.split('+'):
        name = name.strip().lower()
        if name not in QUALIFIERS:
            raise ValueError('unknown key qualifier %r: use %s' % (name, ', '.join(sorted(QUALIFIERS))))
        word |= QUALIFIERS[name]
    return word


def key_events(given):
    """The keys of a raw segment: a raw code on its own, or [code, qualifier]."""
    events = []
    for item in given:
        if isinstance(item, (list, tuple)):
            code, qualifier = item
        else:
            code, qualifier = item, 0
        events.append((int(code), qualifier_word(qualifier)))
    return events


def load_run(source):
    """A run description from a file name or a dict, completed with the defaults."""
    given = source
    if not isinstance(source, dict):
        with open(source) as f:
            given = json.load(f)
    unknown = set(given) - set(DEFAULT_RUN) - {'bytes', 'files'}
    if unknown:
        raise ValueError('unknown keys in the run description: %s' % ', '.join(sorted(unknown)))
    run = dict(DEFAULT_RUN)
    run.update(given)
    return run


class Headless(AmigaOS):
    def __init__(self, run=None, track_writes=False, verbose=False, observe=(),
                 observe_returns=False, watch=None, watch_for=None):
        self.run_spec = run = load_run(run or {})
        self.verbose = verbose
        self.names = dump.Names(ROOT)
        self.fd = disasm.load_fd(os.path.join(HERE, 'fd'))

        self.o = Oracle(a4=A4)
        self.uc = uc = self.o.uc
        uc.mem_map(HEAP_BASE, PLANE_END - HEAP_BASE)
        uc.mem_map(CIA_BASE, CIA_SIZE)
        uc.mem_map(CUSTOM, 0x1000)

        # the operating system
        self.lib_base = {}
        for i, name in enumerate(LIB_NAMES):
            base = LIB_AREA + i * LIB_SPAN + LIB_SPAN // 2
            self.lib_base[name] = base
            for offset in range(6, LIB_SPAN // 2, 6):
                uc.mem_write(base - offset, b'\x4e\x75')
        self.scratch_task = SCRATCH
        self.scratch_event = SCRATCH + 0x200
        # The task's trap handler.  sub_0125c6 looks at its first long: the handler dos gives a
        # process begins with movem.l d0-d7/a0-a6,-(a7), and only then does the game put its
        # own crash reporter in and leave the key qualifier mask at 0.  With anything else
        # there, a debugger's handler for one, it accepts keys only together with left Alt.
        self.o.write(SCRATCH + 0x100, b'\x48\xe7\xff\xfe')
        self.o.w32(self.scratch_task + 0x32, SCRATCH + 0x100)      # tc_TrapCode
        self.o.w32(4, self.lib_base['exec'])
        self.o.w32(SYSBASE_VAR, self.lib_base['exec'])      # what the C startup leaves behind
        self.o.w32(DOSBASE_VAR, self.lib_base['dos'])
        self.os_init({name: bytes.fromhex(text) for name, text in run.get('files', {}).items()})
        self.math_base = MATH_BASE
        self.rom, self.rom_base = self._map_rom()
        self.math_vectors = self._map_rom_mathffp()
        self.rom_rawkeyconvert, self.rom_keymap = self._find_rom_console()
        self.os_calls = collections.Counter()

        # memory
        self.heap, self.plane_heap = HEAP_BASE, PLANE_BASE
        self.allocs = {}                  # address -> size, live allocations outside display memory
        self.display_allocs = {}          # address -> size, what display_alloc_chip asked for
        self.alloc_labels = {}
        self.alloc_refused = []
        self._display_alloc = False
        self.plane_reads = collections.Counter()      # (routine, block of display memory) -> count
        uc.hook_add(UC_HOOK_MEM_READ, self._plane_read, begin=PLANE_BASE, end=PLANE_END - 1)

        # time
        self.vblanks = self.passes = self.ticks = self.missions = 0
        self.vblanks_per_pass = int(run['vblanks_per_pass'])
        self.video_hz = int(run['video_hz'])
        self.since_pass = 0
        self.schedule = []                # the run as it happened: V raw, P, T byte, S
        self.key_log = []                 # (vblank, code, qualifier), for the port's replay
        self.in_tick = False
        self.tick_return = None
        self.inner_reached = False
        self.loop_heads = 0               # times the head of the inner loop, 0x01010E, was executed

        # entropy
        entropy = run['entropy']
        self.entropy = iter(entropy['values']) if 'values' in entropy else entropy_values(entropy['seed'])
        self.entropy_log = []             # (index, value, routine, vblank, pass, tick)
        uc.hook_add(UC_HOOK_MEM_READ, self._beam_read, begin=VHPOSR, end=VHPOSR + 1)

        # input
        self.raw_script = [(int(seg[0]), raw_state(seg[1]), key_events(seg[2]) if len(seg) > 2 else [])
                           for seg in run['raw']]
        self.raw_index, self.raw_left = 0, (self.raw_script[0][0] if self.raw_script else 0)
        self.raw_fresh = True
        self.byte_script = list(run.get('bytes', []))
        self.bytes_used = 0
        self.joy_words = None
        self.set_ciaa_pra(0xFF)

        # dumps and reports
        self.writer = None
        self.step_hashes = []             # (kind, tick, pass, hash)
        self.track_writes = track_writes
        self.writes = {}                  # address -> set of routine start addresses, this step
        self.change_report = []
        self.last_state = None
        if track_writes:
            uc.hook_add(UC_HOOK_MEM_WRITE, self._data_write, begin=DATA_START, end=DATA_END - 1)
            uc.hook_add(UC_HOOK_MEM_WRITE, self._data_write, begin=HEAP_BASE, end=HEAP_END - 1)

        # control
        self.stops = {}
        self._until = None
        self._deadline = time.time() + 600.0
        self._fault = None
        self._skip = None
        self._reason = None
        self._pause = None
        self.depth = 0
        self.finished = False
        self.progress = 0
        uc.hook_add(UC_HOOK_CODE, self._range_stop, begin=LIB_AREA, end=LIB_AREA + len(LIB_NAMES) * LIB_SPAN - 1)
        uc.hook_add(UC_HOOK_CODE, self._range_stop, begin=SEG_AREA, end=SEG_AREA + 0xFFF)
        for address in SPINS:
            uc.hook_add(UC_HOOK_CODE, self._spin, begin=address, end=address)
        uc.hook_add(UC_HOOK_CODE, self._probe_display_alloc, begin=DISPLAY_ALLOC_CHIP, end=DISPLAY_ALLOC_CHIP)
        uc.hook_add(UC_HOOK_CODE, self._probe_sample, begin=SERVER_AFTER_SAMPLE, end=SERVER_AFTER_SAMPLE)
        uc.hook_add(UC_HOOK_CODE, self._probe_loop_head, begin=INNER_LOOP, end=INNER_LOOP)
        # Observers: every entry of a named routine is recorded with its registers and the
        # longs above its return address, which are a C routine's arguments.  An observer only
        # reads, so a run with observers gives the same steps as one without.
        self.observed = []
        self.observing = {}
        self.watch = dict(watch or {})
        self.watch_for = set(watch_for) if watch_for else None
        self.observe_returns = observe_returns
        self._open = []
        for wanted in observe:
            address = wanted if isinstance(wanted, int) else next(
                (a for a, _, name in self.names.code if name == wanted), None)
            if address is None:
                raise HarnessError('no routine is named %r; observe takes a name or an address' % wanted)
            self.observing[address] = self.names.routine(address)
            uc.hook_add(UC_HOOK_CODE, self._observe, begin=address, end=address)
            for at in (self._returns_of(address) if observe_returns else ()):
                self.stop_at(at, functools.partial(self._observe_return, at))
        self.o.write(OBSERVE_TRAMPOLINE, struct.pack(
            '>HLHL', 0x40F9, OBSERVE_CCR, 0x4EF9, OBSERVE_TRAP))
        self.stop_at(CRACK_SCREEN, self._skip_crack_screen)
        self.stop_at(MISSION_START, self._mission_start)
        self.stop_at(FRAME_UPDATE, self._pass_begin)
        self.stop_at(PASS_END, self._pass_end)
        self.stop_at(LOGIC_TICK, self._tick_begin)
        for address in TICK_RETURNS:              # hooks must exist before the code is first run:
            self.stop_at(address, self._tick_end)     # Unicorn does not re-translate for a new hook

        # the main program: main(argc, argv) with a 16-bit argc of 1, as the C startup calls it
        sp = MAIN_STACK_TOP
        for size, value in ((4, 0), (2, 1), (4, END_TRAP)):
            sp -= size
            self.o.write(sp, value.to_bytes(size, 'big'))
        uc.reg_write(UC_M68K_REG_SR, 0x2000)
        uc.reg_write(UC_M68K_REG_A7, sp)
        self.setreg('a4', A4)
        self.pc = MAIN

    # ------------------------------------------------------------------ registers, memory

    def reg(self, name):
        bank = UC_M68K_REG_D0 if name[0] == 'd' else UC_M68K_REG_A0
        return self.uc.reg_read(bank + int(name[1]))

    def setreg(self, name, value):
        bank = UC_M68K_REG_D0 if name[0] == 'd' else UC_M68K_REG_A0
        self.uc.reg_write(bank + int(name[1]), value & 0xFFFFFFFF)

    def cstr(self, address, limit=256):
        return self.o.read(address, limit).split(b'\0')[0].decode('latin1')

    def context(self):
        return ([self.uc.reg_read(UC_M68K_REG_D0 + i) for i in range(8)] +
                [self.uc.reg_read(UC_M68K_REG_A0 + i) for i in range(8)],
                self.uc.reg_read(UC_M68K_REG_SR))

    def restore(self, context):
        regs, sr = context
        self.uc.reg_write(UC_M68K_REG_SR, sr)
        for i in range(8):
            self.uc.reg_write(UC_M68K_REG_D0 + i, regs[i])
            self.uc.reg_write(UC_M68K_REG_A0 + i, regs[8 + i])

    def callers(self, limit=6):
        """Return addresses on the stack, innermost first: every long that points behind a
        jsr or bsr in the executable.  A heuristic, used for labels only."""
        sp = self.uc.reg_read(UC_M68K_REG_A7)
        stack = self.o.read(sp, 0x180)
        found = []
        for offset in range(0, len(stack) - 3, 2):
            value = struct.unpack_from('>L', stack, offset)[0]
            if not 0x010000 <= value < 0x022F4C or value & 1:
                continue
            before = self.o.read(value - 6, 6)
            if (before[2:4] in (b'\x4e\xac', b'\x4e\xba', b'\x61\x00') or before[0:2] == b'\x4e\xb9' or
                    before[4] == 0x61 and before[5] != 0 or before[4] == 0x4E and before[5] & 0xF8 == 0x90):
                found.append(value)
                if len(found) == limit:
                    break
        return found

    def alloc(self, size, flags=0):
        if size > HEAP_END - HEAP_BASE:
            self.alloc_refused.append(size)       # free_mission_assets asks for 4 GB to flush memory
            return 0
        size = (size + 7) & ~7
        chain = [self.names.routine(a) for a in self.callers()]
        wrappers = ('mem_alloc', 'mem_alloc_chip', 'mem_alloc_asm', 'display_alloc_chip', 'sub_020874')
        owner = next((name for name in chain if name not in wrappers), '?')
        if self._display_alloc:
            self._display_alloc = False
            address, self.plane_heap = self.plane_heap, self.plane_heap + size
            if self.plane_heap > PLANE_END:
                raise HarnessError('display memory exhausted')
            self.alloc_labels[address] = 'display %d (%s)' % (len(self.alloc_labels), owner)
            self.display_allocs[address] = size
            return address
        address, self.heap = self.heap, self.heap + size
        if self.heap > HEAP_END:
            raise HarnessError('heap exhausted: %d bytes asked by %s' % (size, owner))
        self.allocs[address] = size
        label = 'alloc %d (%s' % (len(self.alloc_labels), owner)
        if owner.startswith('load_file') and self.files_log:
            label += ' ' + self.files_log[-1][1]
        self.alloc_labels[address] = label + ')'
        return address

    def free(self, address):
        self.allocs.pop(address, None)

    def _map_rom(self):
        """The owner's Kickstart ROM, mapped where it lives.  Two of its parts run for real:
        the mathffp routines game logic computes with, and console.device's RawKeyConvert,
        which turns raw key codes into characters for the game's text entry."""
        path = os.path.join(ROOT, 'original', 'kick.rom')
        if not os.path.isfile(path):
            return None, None
        with open(path, 'rb') as f:
            rom = f.read()
        base = 0x1000000 - len(rom)
        self.uc.mem_map(base, len(rom))
        self.uc.mem_write(base, rom)
        return rom, base

    def _rom_resident(self, name):
        return rom_resident(self.rom, self.rom_base, name)

    def _rom_vectors(self, table):
        return rom_vectors(self.rom, self.rom_base, table)

    def _map_rom_mathffp(self):
        """Game logic computes with mathffp.library.  Its routines are pure register arithmetic,
        so the real ones run, as 68000 code from the ROM, reached through a jump table of jmp
        instructions.  Without the ROM the library does not open and the run stops there."""
        if self.rom is None:
            return None
        offset = self._rom_resident('mathffp.library')
        if offset is None or not self.rom[offset + 10] & 0x80:        # RTF_AUTOINIT
            return None
        init = struct.unpack_from('>L', self.rom, offset + 22)[0] - self.rom_base
        vectors = self._rom_vectors(struct.unpack_from('>L', self.rom, init + 4)[0])
        for index, vector in enumerate(vectors):
            self.o.write(MATH_BASE - 6 * (index + 1), b'\x4e\xf9' + struct.pack('>L', vector))
        return vectors

    def _find_rom_console(self):
        return find_rom_console(self.rom, self.rom_base)

    def segment_block(self, index):
        return SEG_AREA + index * SEG_SPAN

    # ------------------------------------------------------------------ hooks
    # A hook can read the machine but a register written inside one is lost, so every hook
    # that has work to do parks the program and the driver does the work.

    def _range_stop(self, uc, address, size, user):
        self._reason = address
        uc.emu_stop()

    def _stop(self, uc, address, size, user):
        if self._skip == address:
            self._skip = None
            return
        self._reason = address
        uc.emu_stop()

    def _spin(self, uc, address, size, user):
        if self.o.read(VBLANK_FLAG, 1) == b'\0':
            self._reason = address
            uc.emu_stop()

    def stop_at(self, address, handler):
        if address not in self.stops:
            self.uc.hook_add(UC_HOOK_CODE, self._stop, begin=address, end=address)
        self.stops[address] = handler

    def _returns_of(self, address):
        """Every `rts` of a routine, so that an observer can also record what it leaves.
        The span comes from the inventory and the instructions from the disassembler, the
        same two sources the listing is built from."""
        span = next((s for a, s, _ in self.names.code if a == address), 0)
        if not span:
            raise HarnessError('%06x has no span in re/functions.csv; regenerate it' % address)
        md = Cs(CS_ARCH_M68K, CS_MODE_M68K_000)
        return [ins.address for ins in md.disasm(self.o.read(address, span), address)
                if ins.mnemonic == 'rts']

    def _watched(self):
        """The watched ranges as they stand.  A range is (address, length), or
        ('*', pointer, length) for one the program reaches through a pointer, which is how
        the object records are addressed."""
        out = {}
        for name, where in self.watch.items():
            if where[0] == '*':
                at, length = self.o.r32(where[1]), where[2]
            else:
                at, length = where
            out[name] = self.o.read(at, length).hex() if at else ''
        return out

    def _observe(self, uc, address, size, user):
        """An observer: record and let the program run on.  Nothing is written, so the run is
        the same one it would be without it."""
        stack = self.reg('a7')
        record = {
            'routine': self.observing[address], 'address': address,
            'vblank': self.vblanks, 'pass': self.passes, 'tick': self.ticks,
            'd': [self.reg('d%d' % i) for i in range(8)],
            'a': [self.reg('a%d' % i) for i in range(8)],
            'args': [self.o.r32(stack + 4 + 4 * i) for i in range(8)],
            'words': [self.o.r16(stack + 4 + 2 * i) for i in range(16)],
            'a7': stack, 'caller': self.o.r32(stack),
        }
        if self.watch and (self.watch_for is None or record['routine'] in self.watch_for):
            record['memory'] = self._watched()
        self.observed.append(record)
        if self.observe_returns:
            self._open.append(record)

    def _observe_return(self, address):
        """The other end of an observer: what the routine leaves behind at its `rts`.

        The condition codes cannot be read out of the emulator, which keeps them lazily, so
        they are read the way tools/oracle.py reads them - by running two instructions that
        touch nothing else.  The program is parked at the `rts`, which has not run yet; a
        move from SR and a jump cost no register and no flag, and the driver resumes at the
        `rts` afterwards."""
        stack = self.reg('a7')
        for index in range(len(self._open) - 1, -1, -1):
            if self._open[index]['a7'] == stack:
                record = self._open.pop(index)
                break
        else:
            return                                   # an rts of a routine nobody entered here
        self.o.w16(OBSERVE_CCR, 0)
        self.uc.emu_start(OBSERVE_TRAMPOLINE, OBSERVE_TRAP, count=8)
        record['return'] = {
            'address': address, 'ccr': self.o.r16(OBSERVE_CCR) & 0x1F,
            'd': [self.reg('d%d' % i) for i in range(8)],
            'a': [self.reg('a%d' % i) for i in range(8)],
            'vblank': self.vblanks, 'pass': self.passes, 'tick': self.ticks,
        }
        if 'memory' in record:
            record['return']['memory'] = self._watched()

    def _probe_loop_head(self, uc, address, size, user):
        self.loop_heads += 1

    def _probe_display_alloc(self, uc, address, size, user):
        self._display_alloc = True

    def _probe_sample(self, uc, address, size, user):
        """The second input mode: the byte the server has just sampled is replaced."""
        if self.byte_script and self.inner_reached and self.o.r16(DEMO_MODE) == 0:
            value = self.byte_script[self.bytes_used] if self.bytes_used < len(self.byte_script) else 0
            self.bytes_used += 1
            self.o.w16(INPUT_BYTE, value)

    def _beam_read(self, uc, access, address, size, value, user):
        try:
            value = next(self.entropy)
        except StopIteration:
            self._fault = 'the entropy list of the run description is used up'
            uc.emu_stop()
            return
        uc.mem_write(VHPOSR, struct.pack('>H', value))
        pc = uc.reg_read(UC_M68K_REG_PC)
        if self.names.routine_start(pc) in (RAND_BEAM, READ_VHPOSR):   # frameless: the caller is on top
            pc = self.o.r32(uc.reg_read(UC_M68K_REG_A7))
        self.entropy_log.append((len(self.entropy_log), value, self.names.routine(pc),
                                 self.vblanks, self.passes, self.ticks))

    def _plane_read(self, uc, access, address, size, value, user):
        """Display memory read by the CPU: which routine, and which of display_init's blocks."""
        block = max((a for a in self.display_allocs if a <= address), default=None)
        where = '%d bytes' % self.display_allocs[block] if block is not None else 'outside any block'
        self.plane_reads[(self.names.routine(uc.reg_read(UC_M68K_REG_PC)), where)] += 1

    def _data_write(self, uc, access, address, size, value, user):
        start = self.names.routine_start(uc.reg_read(UC_M68K_REG_PC))
        for a in range(address, address + size):
            self.writes.setdefault(a, set()).add(start)

    # ------------------------------------------------------------------ the driver

    def run(self, until=None, wall_limit=600.0):
        """Run the main program.  until: 'inner' (the inner loop is reached), 'pass', 'tick',
        'step', or None for the stop condition of the run description.  Returns why it stopped."""
        self._until = until
        self._deadline = time.time() + wall_limit
        return self._drive(END_TRAP)

    def _drive(self, end):
        idle = 0
        while True:
            self._reason = self._fault = None
            self.o.fault = None
            before = self.progress
            try:
                self.uc.emu_start(self.pc, end, timeout=2_000_000)
            except UcError as error:
                pc = self.uc.reg_read(UC_M68K_REG_PC)
                raise HarnessError('%s: %s at %06x in %s' % (error, self.o.fault, pc, self.names.routine(pc))) from None
            self.pc = self.uc.reg_read(UC_M68K_REG_PC)
            if self._fault:
                raise HarnessError(self._fault)
            address = self._reason
            if address is None:
                if self.pc == end:
                    if self.depth == 0:
                        self.finished = True
                    return 'end'
                idle = idle + 1 if self.progress == before else 0
                if idle >= 5 or time.time() > self._deadline:
                    raise Stuck('no wait point for %d s: %06x in %s, called from %s' % (
                        2 * idle, self.pc, self.names.routine(self.pc),
                        ' < '.join(self.names.routine(a) for a in self.callers())))
                continue
            self.progress += 1
            idle = 0
            self._pause = None
            if LIB_AREA <= address < SEG_AREA:
                self._os_call(address)
            elif SEG_AREA <= address < SEG_AREA + 0x1000:
                self._segment_call(address)
            elif address in SPINS:
                if self.depth:
                    raise HarnessError('an interrupt server waits for a VBlank')
                self.deliver_vblanks(1)
            else:
                self.stops[address]()
                if self.pc == address:
                    self._skip = address
            if self._pause and self.depth == 0:
                return self._pause
            if time.time() > self._deadline:
                raise Stuck('wall clock limit reached at %06x in %s' % (self.pc, self.names.routine(self.pc)))

    def leave(self, d0=None):
        """Return from the routine the program has just entered."""
        sp = self.uc.reg_read(UC_M68K_REG_A7)
        self.pc = self.o.r32(sp)
        self.uc.reg_write(UC_M68K_REG_A7, sp + 4)
        if d0 is not None:
            self.setreg('d0', d0)

    def nested(self, address, regs, args=b''):
        """Run a routine of the original to its rts while the program is parked: an interrupt
        server, a callback.  It has a stack of its own and may call the operating system.
        `args` are the bytes a C routine reads above its return address, right to left as
        the caller would have pushed them.  Returns the registers it left."""
        if self.depth >= 3:
            raise HarnessError('nested calls too deep')
        saved = self.context(), self.pc, self._reason, self._pause
        self.depth += 1
        sp = NESTED_STACK_TOP - 0x2000 * (self.depth - 1) - 4 - len(args)
        if args:
            self.o.write(sp + 4, args)
        self.o.w32(sp, NESTED_TRAP)
        self.uc.reg_write(UC_M68K_REG_A7, sp)
        for name, value in regs.items():
            self.setreg(name, value)
        self.pc = address
        self._drive(NESTED_TRAP)
        out = self.context()[0]
        self.depth -= 1
        context, self.pc, self._reason, self._pause = saved
        self.restore(context)
        return out

    def _os_call(self, address):
        library = LIB_NAMES[(address - LIB_AREA) // LIB_SPAN]
        offset = self.lib_base[library] - address
        name = self.fd.get(library, {}).get(offset)
        if name is None and library == 'device':
            name = DEVICE_FUNCTIONS.get(offset)
        if name is None:
            name = 'offset -%d' % offset
        handler = getattr(self, 'os_%s_%s' % (library, name), None)
        self.os_calls[library + '.' + name] += 1
        if handler is None:
            chain = ' < '.join('%s (%06x)' % (self.names.routine(a), a) for a in self.callers())
            raise HarnessError('%s.%s is not stubbed; called from %s' % (library, name, chain))
        result = handler()
        if self.verbose:
            print('  %s.%s -> %r' % (library, name, result))
        self.leave(result)

    def _segment_call(self, address):
        """A call into the music player or the song data (headless_os.os_dos_LoadSeg)."""
        name = self.segments[(address - SEG_AREA) // SEG_SPAN]
        self.player_calls.append((name, self.reg('d0') & 0xFFFF, self.reg('d1'), self.reg('d2'),
                                  self.vblanks, self.passes, self.ticks))
        if name.lower() == 'wofsongs':
            self.setreg('a0', address)            # "the song data"; only the player would read it
        self.leave(0)                             # the player's answer to every question: idle

    # ------------------------------------------------------------------ time and input

    def set_ciaa_pra(self, value):
        """CIA-A decodes A8 to A11 only, so PRA answers at every odd address from 0xBFE001 to
        0xBFE0FF.  read_fire_button reads port 1's button through 0xBFE0FF."""
        for address in range(CIAA_PRA, CIAA_PRA + 0x100, 2):
            self.o.write(address, bytes([value]))

    def _joy_words(self):
        """JOY1DAT for each stick position, found by asking the original's own decoder."""
        words = {}
        for index in range(16):
            word = (index >> 3 & 1) << 9 | (index >> 2 & 1) << 8 | (index >> 1 & 1) << 1 | index & 1
            self.o.w16(JOY1DAT, word)
            saved = self.o.read(OPT_INVERT_VERTICAL, 1)           # a byte; the next one is another flag
            self.o.write(OPT_INVERT_VERTICAL, b'\0')              # off for the probe
            bits = self.nested(READ_JOY_BITS, {'a4': A4})[0] & 0x0F
            self.o.write(OPT_INVERT_VERTICAL, saved)
            words.setdefault(bits, word)                          # b0 down, b1 up, b2 left, b3 right
        return words

    def _next_raw(self):
        while self.raw_index < len(self.raw_script) and self.raw_left == 0:
            self.raw_index += 1
            self.raw_fresh = True
            if self.raw_index < len(self.raw_script):
                self.raw_left = self.raw_script[self.raw_index][0]
        if self.raw_index >= len(self.raw_script):
            return 0, []
        _, state, keys = self.raw_script[self.raw_index]
        self.raw_left -= 1
        fresh, self.raw_fresh = self.raw_fresh, False
        return state, (keys if fresh else [])

    def deliver_vblanks(self, count):
        for _ in range(count):
            self._vblank()

    def _vblank(self):
        if self.joy_words is None:
            self.joy_words = self._joy_words()
        raw, keys = self._next_raw()
        down, up, right, left, fire = [(raw >> i) & 1 for i in range(5)]
        if down and up:
            down = up = 0
        if left and right:
            left = right = 0
        self.o.w16(JOY1DAT, self.joy_words[down | up << 1 | left << 2 | right << 3])
        self.set_ciaa_pra(0x7F if fire else 0xFF)                 # port 2's button, active low
        for code, qualifier in keys:
            self.key_event(code, qualifier)
            # The keys with the VBlank each one was delivered at, so that a port test can
            # replay them through wof_key in the same order (SPEC 8).
            self.key_log.append((self.vblanks + 1, code, qualifier))
        self.vblanks += 1
        self.since_pass += 1
        self.progress += 1
        self.schedule.append(('V', raw))
        for _, _, data, code in sorted(self.servers, key=lambda s: (-s[0], s[1])):
            self.nested(code, {'a0': CUSTOM, 'a1': data, 'a5': code, 'a6': self.lib_base['exec']})
        stop = self.run_spec['stop']
        if self._until is None and 'vblanks' in stop and self.vblanks >= stop['vblanks']:
            self._pause = 'vblanks'

    def key_event(self, code, qualifier=0):
        """One raw key through the handler the game put on input.device."""
        event = self.scratch_event
        self.o.write(event, bytes(22))
        self.o.write(event + 4, b'\x01')                          # ie_Class: IECLASS_RAWKEY
        self.o.w16(event + 6, code)
        self.o.w16(event + 8, qualifier)
        for data, handler in self.input_handlers:
            self.nested(handler, {'a0': event, 'a1': data})

    # ------------------------------------------------------------------ stops in the original

    def _skip_crack_screen(self):
        self.leave(1)                             # non-zero: carry on to the title sequence

    def _mission_start(self):
        self.missions += 1
        self.inner_reached = True
        self.schedule.append(('S', self.missions))
        self._step('S')
        if self._until == 'inner':
            self._pause = 'inner'

    def _pass_begin(self):
        """frame_update is entered: the VBlanks this pass is still owed happen now."""
        owed = max(self.vblanks_per_pass - self.since_pass, 0)
        if owed == 0 and self.o.read(VBLANK_FLAG, 1) == b'\0':
            owed = 1
        self.deliver_vblanks(owed)
        self.since_pass = 0
        self.passes += 1
        self.schedule.append(('P', self.passes))

    def _pass_end(self):
        self._step('P')
        stop = self.run_spec['stop']
        if self._until in ('pass', 'step') or self._until is None and self.passes >= stop.get('passes', 1 << 60):
            self._pause = 'pass'

    def _tick_begin(self):
        self.in_tick = True
        self.tick_return = self.o.r32(self.uc.reg_read(UC_M68K_REG_A7))
        if self.tick_return not in TICK_RETURNS:
            raise HarnessError('logic_tick called from %06x, a site the harness does not know' % self.tick_return)

    def _tick_end(self):
        if not self.in_tick or self.pc != self.tick_return:
            return                                # 0x0114F4 is also the head of the loop
        self.in_tick = False
        self.ticks += 1
        self.schedule.append(('T', self.o.r16(TICK_INPUT)))
        self._step('T')
        stop = self.run_spec['stop']
        if self._until in ('tick', 'step') or self._until is None and self.ticks >= stop.get('ticks', 1 << 60):
            self._pause = 'tick'

    # ------------------------------------------------------------------ dumps and reports

    def regions(self):
        state = {DATA_START: self.o.read(DATA_START, DATA_END - DATA_START)}
        for address, size in self.allocs.items():
            state[address] = self.o.read(address, size)
        return state

    def labels(self):
        labels = {DATA_START: 'data'}
        labels.update({a: self.alloc_labels[a] for a in self.allocs})
        return labels

    def open_dump(self, path):
        self.writer = dump.DumpWriter(path, self.run_spec)

    def _step(self, kind):
        info = {'kind': kind, 'mission': self.missions, 'tick': self.ticks, 'pass': self.passes,
                'vblank': self.vblanks, 'entropy': len(self.entropy_log), 'input': self.o.r16(TICK_INPUT)}
        state = self.regions()
        digest = self.writer.step(info, state, self.labels()) if self.writer else dump.state_hash(state)
        self.step_hashes.append((kind, self.ticks, self.passes, digest))
        if self.track_writes:
            self._report(info, state)
        self.last_state = state

    def _report(self, info, state):
        """What this step changed and who wrote it, resolved to names."""
        lines = []
        labels = self.labels()
        old = self.last_state or {}
        changed = []
        for address in sorted(state):
            before = old.get(address)
            if before is None or len(before) != len(state[address]):
                continue                          # a new allocation: its loader filled it
            changed += [(address + s, n) for s, n in dump.changed_ranges(before, state[address], gap=0)]
        for address, length in changed:
            writers = set()
            for a in range(address, address + length):
                writers |= self.writes.get(a, set())
            who = ', '.join(sorted(self.names.routine(w) for w in writers)) or 'a stub'
            base = max(a for a in state if a <= address)
            old_bytes = old[base][address - base:address - base + length]
            new_bytes = state[base][address - base:address - base + length]
            lines.append('  %06x %-34s %2d  %s -> %s   by %s' % (
                address, dump.describe(address, self.names, state, labels), length,
                old_bytes[:8].hex(), new_bytes[:8].hex(), who))
        touched = len(self.writes)
        self.writes = {}
        head = '%s  tick %d  pass %d  vblank %d  input %02x  entropy %d   (%d bytes written, %d ranges changed)' % (
            info['kind'], info['tick'], info['pass'], info['vblank'], info['input'] & 0xFF,
            info['entropy'], touched, len(changed))
        self.change_report.append(head)
        self.change_report += lines

    def close(self):
        if self.writer:
            self.writer.close()
            self.writer = None


# ------------------------------------------------------------------------------ command line

def command_run(args):
    machine = Headless(args.run, track_writes=bool(args.changes), verbose=args.verbose)
    if args.out:
        machine.open_dump(args.out)
    started = time.time()
    try:
        why = machine.run()
    finally:
        machine.close()
    seconds = time.time() - started
    print('stopped: %s after %d VBlanks, %d passes, %d ticks, %d missions, %d entropy reads, %.1f s' % (
        why, machine.vblanks, machine.passes, machine.ticks, machine.missions,
        len(machine.entropy_log), seconds))
    if machine.step_hashes:
        print('steps: %d, last hash %s' % (len(machine.step_hashes), machine.step_hashes[-1][3]))
    if args.changes:
        with open(args.changes, 'w') as f:
            f.write('\n'.join(machine.change_report) + '\n')
    if args.entropy_log:
        with open(args.entropy_log, 'w') as f:
            for index, value, routine, vblank, passes, ticks in machine.entropy_log:
                f.write('%6d  %04x  %-28s vblank %-7d pass %-6d tick %d\n' % (
                    index, value, routine, vblank, passes, ticks))
    if args.schedule:
        with open(args.schedule, 'w') as f:
            json.dump(machine.schedule, f, separators=(',', ':'))
    if machine.plane_reads:
        print('CPU reads of display memory, by routine:')
        for (routine, block), count in machine.plane_reads.most_common():
            print('  %-24s block of %-16s %d' % (routine, block, count))


def command_show(args):
    if args.step is None:
        for head in dump.steps(args.dump):
            print('%5d  %s  mission %d  tick %-5d pass %-5d vblank %-7d input %02x  entropy %-5d %s  %d ranges' % (
                head['step'], head['kind'], head['mission'], head['tick'], head['pass'], head['vblank'],
                head['input'] & 0xFF, head['entropy'], head['hash'][:16], len(head['delta'])))
        return
    names = dump.Names(ROOT)
    reader = dump.DumpReader(args.dump)
    for head in reader:
        if head['step'] == args.step:
            print('step %d: %s' % (args.step, json.dumps({k: v for k, v in head.items() if k not in ('delta', 'regions')})))
            print('reconstruction matches the hash:', reader.verify(head))
            for address, length in head['delta']:
                print('  %06x %-36s %d' % (address, dump.describe(address, names, reader.regions, reader.labels), length))
            return
    sys.exit('no step %d' % args.step)


def command_diff(args):
    names = dump.Names(ROOT)
    a, b = dump.steps(args.a), dump.steps(args.b)
    step = args.step
    if step is None:
        step = next((x['step'] for x, y in zip(a, b) if x['hash'] != y['hash']), None)
        if step is None:
            print('identical over %d steps' % min(len(a), len(b)) +
                  ('' if len(a) == len(b) else '; one dump is longer (%d and %d steps)' % (len(a), len(b))))
            return
    head_a, state_a, labels_a = dump.state_at(args.a, step)
    head_b, state_b, _ = dump.state_at(args.b, step)
    print('first difference at step %d: %s tick %d pass %d' % (step, head_a['kind'], head_a['tick'], head_a['pass']))
    ranges, only_a, only_b = dump.diff_states(state_a, state_b)
    for address, length in ranges:
        base = max(x for x in state_a if x <= address)
        print('  %06x %-36s %3d  %s | %s' % (
            address, dump.describe(address, names, state_a, labels_a), length,
            state_a[base][address - base:address - base + min(length, 8)].hex(),
            state_b[base][address - base:address - base + min(length, 8)].hex()))
    for address in only_a:
        print('  region %06x only in %s' % (address, args.a))
    for address in only_b:
        print('  region %06x only in %s' % (address, args.b))


def main():
    parser = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    commands = parser.add_subparsers(dest='command', required=True)
    run = commands.add_parser('run', help='run the original as a run description says')
    run.add_argument('run', help='JSON run description')
    run.add_argument('--out', help='write the state dump here')
    run.add_argument('--changes', help='write the change report here (slow: hooks every write)')
    run.add_argument('--entropy-log', help='write the log of beam position reads here')
    run.add_argument('--schedule', help='write the schedule as it happened here, as JSON')
    run.add_argument('-v', '--verbose', action='store_true')
    run.set_defaults(function=command_run)
    show = commands.add_parser('show', help='list the steps of a dump, or one step with names')
    show.add_argument('dump')
    show.add_argument('--step', type=int)
    show.set_defaults(function=command_show)
    diff = commands.add_parser('diff', help='the first step where two dumps differ, with names')
    diff.add_argument('a')
    diff.add_argument('b')
    diff.add_argument('--step', type=int)
    diff.set_defaults(function=command_diff)
    args = parser.parse_args()
    args.function(args)


if __name__ == '__main__':
    main()
