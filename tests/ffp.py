"""The original's floating point, run for real, as the reference for src/ffp.c.

Game logic computes with Motorola fast floating point (`re/notes/ffp.md`).  The game
reaches it through the C library's glue at 0x021C9C-0x021D2E, which pushes a library
offset and jumps to `ffp_dispatch` (0x021CF6); that opens `mathffp.library` on first use
into `MathBase` and then jumps into it with the operands still in D0 and D1.  The caller
branches on the condition codes the library's routine leaves, so the reference is the glue
entry itself, called with `MathBase` preset to a jump table that leads into the owner's
Kickstart ROM, exactly as the headless original arranges it (`re/notes/headless.md`).

    ref = Reference()                       # None when original/kick.rom is absent
    out = ref.call('mul', 0x80000041, 0x40000042)
    out.d0, out.d1, out.ccr, out.flags      # result, second operand, condition codes

Nothing here is copied into the repository: the ROM is read at test time.
"""
import os
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, 'tools'))

from unicorn import UC_HOOK_INTR             # noqa: E402
from unicorn.m68k_const import UC_M68K_REG_PC  # noqa: E402

import headless                              # noqa: E402
from oracle import Oracle, ccr_text          # noqa: E402

A4 = 0x02AFFE
MATH_BASE = 0x0CE000                  # where the jump table into the ROM goes
MATHBASE_VAR = 0x027FAE               # -0x3050(a4), what ffp_dispatch reads
EXEC_BASE = 0x0CC000                  # SPCmp and SPTst call exec.GetCC through SysBase
GETCC = -0x210                        # exec.GetCC, the only library call mathffp makes
ROM_PATH = os.path.join(ROOT, 'original', 'kick.rom')

# The nine glue entries, each with the mathffp function it reaches and its library offset.
GLUE = {
    'add': (0x021C9C, 'SPAdd', -66),
    'cmp': (0x021CA6, 'SPCmp', -42),
    'neg': (0x021CB0, 'SPNeg', -60),
    'tst': (0x021CBA, 'SPTst', -48),
    'fix': (0x021CC4, 'SPFix', -30),
    'sub': (0x021CCE, 'SPSub', -72),
    'div': (0x021CD8, 'SPDiv', -84),
    'flt': (0x021CE2, 'SPFlt', -36),
    'mul': (0x021CEC, 'SPMul', -78),
}
OPERATIONS = ('add', 'sub', 'mul', 'div', 'cmp', 'tst', 'neg', 'fix', 'flt')

# The ones that take a second operand in D1.  SPFix, SPFlt, SPNeg and SPTst take one.
BINARY = ('add', 'sub', 'mul', 'div', 'cmp')

X, N, Z, V, C = 0x10, 0x08, 0x04, 0x02, 0x01


class Trap(Exception):
    """The routine ran into a 68000 exception.  SPDiv reaches `divu.w #0,d0` when the
    divisor's exponent byte is zero, which is vector 5, the zero divide."""

    def __init__(self, vector, pc):
        super().__init__('68000 exception %d at %06X' % (vector, pc))
        self.vector, self.pc = vector, pc


class Result:
    """What a mathffp routine left behind: D0, D1 and the condition codes."""

    __slots__ = ('d0', 'd1', 'ccr')

    def __init__(self, d0, d1, ccr):
        self.d0, self.d1, self.ccr = d0, d1, ccr

    @property
    def flags(self):
        return ccr_text(self.ccr)

    def __eq__(self, other):
        return (self.d0, self.d1, self.ccr) == (other.d0, other.d1, other.ccr)

    def __repr__(self):
        return 'd0=%08X d1=%08X %s' % (self.d0, self.d1, self.flags)


def rom_available():
    return os.path.isfile(ROM_PATH)


def rom_getcc(rom, base):
    """exec.GetCC in the ROM, found by its contents.

    SPCmp and SPTst capture their comparison's condition codes with it, because `move sr`
    is privileged from the 68010 on; it is the one library call mathffp makes.  exec's
    function table is not a plain vector table in the image, so the routine is found the
    way the other ROM lookups here work, by what it is: the only `move.w sr,Dn` in the
    ROM, and it reads into D0 and returns."""
    found = []
    for at in range(0, len(rom) - 2, 2):
        if 0x40C0 <= struct.unpack_from('>H', rom, at)[0] <= 0x40C7:
            found.append(base + at)
    if len(found) != 1 or struct.unpack_from('>H', rom, found[0] - base)[0] != 0x40C0:
        return None
    tail = rom[found[0] - base + 2:found[0] - base + 10]
    return found[0] if b'\x4e\x75' in tail else None


class Reference:
    """One emulated machine with the ROM's mathffp reachable through the game's glue."""

    def __init__(self):
        self.o = Oracle(a4=A4)
        with open(ROM_PATH, 'rb') as f:
            rom = f.read()
        self.rom_base = 0x1000000 - len(rom)
        self.o.uc.mem_map(self.rom_base, len(rom))
        self.o.uc.mem_write(self.rom_base, rom)

        # mathffp is RTF_AUTOINIT: the long after its init pointer is the function table.
        offset = headless.rom_resident(rom, self.rom_base, 'mathffp.library')
        if offset is None or not rom[offset + 10] & 0x80:
            raise RuntimeError('no mathffp.library in %s' % ROM_PATH)
        self.version = rom[offset + 11]
        identifier = struct.unpack_from('>L', rom, offset + 18)[0] - self.rom_base
        self.id_string = rom[identifier:rom.index(b'\0', identifier)].decode('latin1')
        init = struct.unpack_from('>L', rom, offset + 22)[0] - self.rom_base
        self.vectors = headless.rom_vectors(rom, self.rom_base,
                                            struct.unpack_from('>L', rom, init + 4)[0])
        for index, vector in enumerate(self.vectors):
            self.o.write(MATH_BASE - 6 * (index + 1), b'\x4e\xf9' + struct.pack('>L', vector))
        self.o.w32(MATHBASE_VAR, MATH_BASE)

        self.getcc = rom_getcc(rom, self.rom_base)
        if self.getcc is None:
            raise RuntimeError('no exec.GetCC in %s' % ROM_PATH)
        self.o.write(EXEC_BASE + GETCC, b'\x4e\xf9' + struct.pack('>L', self.getcc))
        self.o.w32(4, EXEC_BASE)                       # SysBase, where the ROM's routines read it
        self.trap = None
        self.o.uc.hook_add(UC_HOOK_INTR, self._interrupt)

    def _interrupt(self, uc, number, user):
        # No vector table is set up: an exception is the answer, not something to service.
        self.trap = (number, uc.reg_read(UC_M68K_REG_PC))
        uc.emu_stop()

    def rom_entry(self, operation):
        """Where in the ROM the operation's routine begins."""
        return self.vectors[-GLUE[operation][2] // 6 - 1]

    def call(self, operation, d0, d1=0, scratch=0):
        """One operation through the game's glue entry, with D0 and D1 as the caller left
        them.  Returns the registers and the condition codes at the return to the caller.

        `scratch` is what D3, D4 and D5 hold at the call.  The routines that use them save
        and restore them, and the bits they leave uninitialised are meant never to reach a
        result; the port takes them as zero, so that is the default here, and a test runs
        the original with random values in them to show that it makes no difference."""
        entry = GLUE[operation][0]
        self.trap = None
        try:
            self.o.call(entry, regs={'d0': d0, 'd1': d1, 'd3': scratch,
                                     'd4': scratch, 'd5': scratch}, ccr=True)
        except RuntimeError:
            if self.trap is None:
                raise
        if self.trap is not None:
            raise Trap(*self.trap)
        return Result(self.o.reg('d0'), self.o.reg('d1'), self.o.ccr)
