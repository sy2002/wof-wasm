"""SPEC 10 point 13: the port's floating point against the original's (SPEC 7.1, 7.4).

The reference is the game's own glue entry, called with `MathBase` preset to a jump table
into `mathffp.library` in the owner's Kickstart ROM (tests/ffp.py).  The port is
src/ffp.c, reached through tests/shim.c on the native library and through a WebAssembly
build the test makes itself.  Compared are the full 32-bit result, the second register and
the condition codes, because the game branches on the flags the routine leaves.

Without original/kick.rom everything that needs the reference skips; the control below
does not need it.
"""
import os
import random
import struct
import sys

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, 'tools'))
sys.path.insert(0, HERE)

import ffp                                                   # noqa: E402
from oracle import Oracle, RETURN_TRAP, ccr_text             # noqa: E402

needs_rom = pytest.mark.skipif(not ffp.rom_available(),
                               reason='original/kick.rom is absent')

X, N, Z, V, C = ffp.X, ffp.N, ffp.Z, ffp.V, ffp.C


# ------------------------------------------------- the instrument, before what it measures
# Unicorn keeps the condition codes lazily, so reg_read hands back whatever was last
# materialised: `addq.w #1` on 0x7FFF reports N without V, and `tst.w` on 0x00010000
# reports nothing at all.  Oracle.call(ccr=True) returns through `move.w sr,<ea>`, which
# runs inside the emulation and forces the computation.  These are hand-assembled
# sequences whose flags the 68000 user manual fixes, V and C-without-Z among them; if the
# instrument were still reading the lazy register, every one of them but the last would
# come out wrong.

CODE = 0x120000

CONTROL = [
    ('moveq #0,d0',                     [0x7000], 0, 0, Z),
    ('moveq #-1,d0',                    [0x70FF], 0, 0xFFFFFFFF, N),
    ('move.w #$7FFF,d0; addq.w #1,d0',  [0x303C, 0x7FFF, 0x5240], 0, 0x8000, N | V),
    ('move.b #$FF,d0; addi.b #2,d0',    [0x103C, 0x00FF, 0x0600, 0x0002], 0, 1, X | C),
    ('moveq #-1,d0; addq.l #1,d0',      [0x70FF, 0x5280], 0, 0, X | Z | C),
    ('move.w #$8000,d0; asl.w #1,d0',   [0x303C, 0x8000, 0xE340], 0, 0, X | Z | V | C),
    ('cmpi.w #1,d0 with d0 = 0',        [0x0C40, 0x0001], 0, 0, N | C),
    ('tst.w d0 with d0 = $00010000',    [0x4A40], 0x00010000, 0x00010000, Z),
    ('move.w #$8000,d0; subq.w #1,d0',  [0x303C, 0x8000, 0x5340], 0, 0x7FFF, V),
]


@pytest.mark.parametrize('name,words,d0_in,d0_out,ccr', CONTROL,
                         ids=[entry[0] for entry in CONTROL])
def test_the_oracle_reports_the_68000s_condition_codes(name, words, d0_in, d0_out, ccr):
    o = Oracle()
    o.write(CODE, b''.join(struct.pack('>H', w) for w in words) + b'\x4e\x75')
    o.call(CODE, regs={'d0': d0_in}, ccr=True)
    assert o.reg('d0') & 0xFFFFFFFF == d0_out, name
    assert o.ccr == ccr, '%s leaves %s, the oracle reports %s' % (
        name, ccr_text(ccr), ccr_text(o.ccr))


def test_a_call_without_the_flag_reports_no_condition_codes():
    """Everything that called the oracle before this milestone keeps its behaviour."""
    o = Oracle()
    o.write(CODE, struct.pack('>H', 0x7000) + b'\x4e\x75')
    o.call(CODE)
    assert o.ccr is None


# ------------------------------------------------------------------ the reference itself

@needs_rom
def test_the_reference_reaches_the_rom_through_the_games_glue():
    reference = ffp.Reference()
    assert reference.id_string.startswith('mathffp 34.1')
    assert reference.version == 34
    assert len(reference.vectors) == 16
    for operation in ffp.OPERATIONS:
        entry = reference.rom_entry(operation)
        assert reference.rom_base <= entry < 0x1000000, operation


@needs_rom
def test_the_reference_needs_no_hard_coded_rom_address():
    """Everything the harness reads out of the ROM is found by its contents, so another
    Kickstart image works: the library by its name, exec.GetCC by its instruction."""
    source = open(os.path.join(HERE, 'ffp.py'), encoding='utf-8').read()
    for literal in ('0xFE3ED4', '0xFC117C', '0xFE40E4'):
        assert literal not in source, 'a ROM address is hard-coded: %s' % literal
