"""A fault of the emulator both instruments run on, and its correction.

Unicorn 2.1.4 (its QEMU m68k translator) decides whether a memory-form shift is arithmetic
or logical from bit 3 of the opcode, which in the memory form belongs to the effective
address's mode, instead of from the type field (bits 9 and 10).  So `asr.w d16(An)` runs as
a logical shift and `lsr.w (An)` as an arithmetic one; the register forms are right, and so
are the left shifts' results.  A 68000 shifts `asr.w $12(a2)` of 0xFFFD to 0xFFFE, Unicorn
to 0x7FFE.  tests/test_headless.py holds the fault and this correction.

The executable has four memory-form right shifts (re/Wings.lst): three `asr.w d16(An)`,
which Unicorn gets wrong, and one `lsr.w d16(A4)`, which it gets right by the same fault.
install() puts a code hook on each of the three that performs the shift as the 68000 does,
flags included, and steps over the instruction.
"""
from unicorn import UC_HOOK_CODE
from unicorn.m68k_const import UC_M68K_REG_A0, UC_M68K_REG_PC, UC_M68K_REG_SR

# (address, address register) of every `asr.w d16(An)` of the executable.
ARITHMETIC_SHIFTS = [
    (0x010BB8, 2),     # object_step: a bomb's vertical speed bouncing on a runway
    (0x010BE0, 2),     # object_step: its horizontal speed there
    (0x019D5E, 5),     # cop_vport_planes: a word argument of the C routine
]


def asr_word(value):
    """asr.w #1 on a memory word: the result and the condition codes X N Z V C."""
    carry = value & 1
    result = ((value >> 1) | (value & 0x8000)) & 0xFFFF
    ccr = (0x11 if carry else 0) | (0x08 if result & 0x8000 else 0) | (0x04 if result == 0 else 0)
    return result, ccr


def _shift(uc, address, size, register):
    base = uc.reg_read(UC_M68K_REG_A0 + register) & 0xFFFFFFFF
    offset = int.from_bytes(uc.mem_read(address + 2, 2), 'big', signed=True)
    ea = (base + offset) & 0xFFFFFFFF
    result, ccr = asr_word(int.from_bytes(uc.mem_read(ea, 2), 'big'))
    uc.mem_write(ea, result.to_bytes(2, 'big'))
    uc.reg_write(UC_M68K_REG_SR, (uc.reg_read(UC_M68K_REG_SR) & ~0x1F) | ccr)
    uc.reg_write(UC_M68K_REG_PC, address + 4)


def install(uc):
    for address, register in ARITHMETIC_SHIFTS:
        uc.hook_add(UC_HOOK_CODE, lambda uc, a, s, u, r=register: _shift(uc, a, s, r),
                    begin=address, end=address)
