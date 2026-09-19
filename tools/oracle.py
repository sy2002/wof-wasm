"""68k oracle: executes routines of the original `Wings` executable inside Unicorn.

The executable is loaded at the same fixed addresses that the disassembly listing
uses (see hunk.load), so every address in re/Wings.lst can be called directly.

    from oracle import Oracle
    o = Oracle()
    src = o.alloc_bytes(packed)             # copy data into emulated RAM
    dst = o.alloc(unpacked_size)
    o.call(0x01FEE0, o.L(src), o.L(len(packed)), o.L(dst), o.L(unpacked_size))
    result = o.read(dst, unpacked_size)

Calling convention of the game's C code (Manx Aztec C, 16-bit int):
  * arguments are pushed right to left; `int`/`short` occupy 2 bytes, `long` and
    pointers 4 bytes  -> build them with o.W(...) and o.L(...)
  * result in D0 (only the low word is meaningful for `int` functions)
  * D0-D3/A0-A3 are scratch (verify per function), A4 = small-data base, A5 = frame pointer
"""
import os
import struct

from unicorn import Uc, UcError, UC_ARCH_M68K, UC_MODE_BIG_ENDIAN, UC_HOOK_MEM_UNMAPPED, UC_HOOK_CODE
from unicorn.m68k_const import (
    UC_CPU_M68K_M68000,
    UC_M68K_REG_A0, UC_M68K_REG_A4, UC_M68K_REG_A7, UC_M68K_REG_D0, UC_M68K_REG_PC, UC_M68K_REG_SR,
)

import hunk

HERE = os.path.dirname(os.path.abspath(__file__))
EXE = os.path.join(HERE, '..', 'original', 'disk', 'Wings_of_Fury', 'Wings')

RAM_BASE, RAM_SIZE = 0x000000, 0x200000        # 2 MB flat RAM, image lives inside it
HEAP_BASE = 0x100000                           # bump allocator for test buffers
STACK_TOP = 0x0FF000
RETURN_TRAP = 0x0FFF00                         # calls return here; emulation stops


class Oracle:
    D = [UC_M68K_REG_D0 + i for i in range(8)]
    A = [UC_M68K_REG_A0 + i for i in range(8)]

    def __init__(self, exe=EXE, a4=None):
        self.segs = hunk.load(exe)
        self.uc = Uc(UC_ARCH_M68K, UC_MODE_BIG_ENDIAN)
        # Unicorn defaults to a ColdFire core, which lacks DBcc and other 68000 instructions.
        self.uc.ctl_set_cpu_model(UC_CPU_M68K_M68000)
        self.uc.mem_map(RAM_BASE, RAM_SIZE)
        for s in self.segs:
            self.uc.mem_write(s['base'], bytes(s['data']))
        self.heap = HEAP_BASE
        self.a4 = a4
        self.trace = None
        self.uc.hook_add(UC_HOOK_MEM_UNMAPPED, self._unmapped)

    # ---- memory helpers -------------------------------------------------
    def alloc(self, n, fill=0):
        addr = self.heap
        self.heap = (self.heap + n + 3) & ~3
        self.uc.mem_write(addr, bytes([fill]) * n)
        return addr

    def alloc_bytes(self, data):
        addr = self.alloc(len(data))
        self.uc.mem_write(addr, bytes(data))
        return addr

    def read(self, addr, n):
        return bytes(self.uc.mem_read(addr, n))

    def write(self, addr, data):
        self.uc.mem_write(addr, bytes(data))

    def r16(self, addr, signed=False):
        return struct.unpack('>h' if signed else '>H', self.read(addr, 2))[0]

    def r32(self, addr, signed=False):
        return struct.unpack('>l' if signed else '>L', self.read(addr, 4))[0]

    def w16(self, addr, v):
        self.write(addr, struct.pack('>H', v & 0xFFFF))

    def w32(self, addr, v):
        self.write(addr, struct.pack('>L', v & 0xFFFFFFFF))

    # ---- argument builders ---------------------------------------------
    @staticmethod
    def W(v):
        return struct.pack('>H', v & 0xFFFF)

    @staticmethod
    def L(v):
        return struct.pack('>L', v & 0xFFFFFFFF)

    # ---- execution -------------------------------------------------------
    def _unmapped(self, uc, access, address, size, value, user):
        # Exceptions raised inside a Unicorn hook are swallowed, so record and report from call().
        self.fault = 'unmapped access @%08x (size %d) from pc=%06x, a7=%08x' % (
            address, size, uc.reg_read(UC_M68K_REG_PC), uc.reg_read(UC_M68K_REG_A7))
        return False

    def call(self, addr, *args, regs=None, max_insns=50_000_000):
        """Call a routine with stack arguments (left-to-right as in the C prototype).
        `regs` optionally presets registers, e.g. {'d0': 1, 'a0': ptr} for asm routines.
        Returns D0."""
        sp = STACK_TOP
        blob = b''.join(args)
        sp -= len(blob)
        self.uc.mem_write(sp, blob)
        sp -= 4
        self.uc.mem_write(sp, struct.pack('>L', RETURN_TRAP))
        self.uc.reg_write(UC_M68K_REG_SR, 0x2000)      # before A7: changing the S bit swaps stack pointers
        self.uc.reg_write(UC_M68K_REG_A7, sp)
        if self.a4 is not None:
            self.uc.reg_write(UC_M68K_REG_A4, self.a4)
        for name, val in (regs or {}).items():
            bank = self.D if name[0] == 'd' else self.A
            self.uc.reg_write(bank[int(name[1])], val & 0xFFFFFFFF)
        self.fault = None
        try:
            self.uc.emu_start(addr, RETURN_TRAP, count=max_insns)
        except UcError as e:
            raise RuntimeError(self.fault or str(e)) from None
        pc = self.uc.reg_read(UC_M68K_REG_PC)
        if pc != RETURN_TRAP:
            raise RuntimeError('did not return (pc=%06x) - instruction budget exhausted?' % pc)
        return self.uc.reg_read(UC_M68K_REG_D0)

    def reg(self, name):
        bank = self.D if name[0] == 'd' else self.A
        return self.uc.reg_read(bank[int(name[1])])


if __name__ == '__main__':
    # Self-test: run the game's own Rpck unpacker on every packed file and compare
    # it with the Python implementation.
    import glob
    import rpck
    shapes = os.path.join(HERE, '..', 'original', 'disk', 'Wings_of_Fury', 'shapes', '*')
    ok = True
    for path in sorted(glob.glob(shapes)):
        raw = open(path, 'rb').read()
        if raw[:4] != b'Rpck':
            continue
        size = struct.unpack('>L', raw[4:8])[0]
        o = Oracle()
        src = o.alloc_bytes(raw[8:])
        dst = o.alloc(size + 16, fill=0xEE)
        o.call(0x01FEE0, o.L(src), o.L(len(raw) - 8), o.L(dst), o.L(size))
        got = o.read(dst, size)
        want = rpck.unrle(raw[8:])[:size]
        same = got == want
        ok &= same
        print('%-16s %6d bytes  68k-vs-python: %s' % (os.path.basename(path), size, 'identical' if same else 'DIFFERENT'))
    print('ORACLE SELF-TEST', 'PASSED' if ok else 'FAILED')
