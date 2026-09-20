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
import re
import struct
import subprocess
import sys

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, 'tools'))
sys.path.insert(0, HERE)

from unicorn import UC_HOOK_CODE                             # noqa: E402

import ffp                                                   # noqa: E402
from oracle import Oracle, ccr_text                          # noqa: E402


@pytest.fixture(scope='module')
def listing():
    """re/Wings.lst is not versioned (CLAUDE.md); a fresh checkout makes it here once."""
    path = os.path.join(ROOT, 're', 'Wings.lst')
    if not os.path.isfile(path):
        subprocess.run([sys.executable, os.path.join(ROOT, 'tools', 'disasm.py')],
                       cwd=ROOT, check=True, capture_output=True)
    with open(path, encoding='latin1') as handle:
        return handle.read()

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


@needs_rom
def test_nothing_the_original_returns_depends_on_the_scratch_registers():
    """SPAdd, SPSub, SPMul and SPDiv save D3 to D5 and leave parts of them uninitialised.
    The port starts them at zero, which is only allowed because no result and no flag ever
    depends on what was in them: here the original runs each case twice, once with zero
    and once with a random value in all three."""
    reference = ffp.Reference()
    rng = random.Random(11)
    for _ in range(1200):
        operation = rng.choice(ffp.OPERATIONS)
        pairs = [(normalised(rng), normalised(rng)),
                 (rng.getrandbits(32), rng.getrandbits(32))]
        for d0, d1 in pairs:
            garbage = rng.getrandbits(32)
            try:
                quiet = reference.call(operation, d0, d1, scratch=0)
                loud = reference.call(operation, d0, d1, scratch=garbage)
            except ffp.Trap:
                continue
            assert quiet == loud, '%s %08X %08X with D3-D5 = %08X' % (
                operation, d0, d1, garbage)


# --------------------------------------------------------------------------- the operands

def number(mantissa, sign, exponent):
    """One FFP value: a 24-bit mantissa, then the sign and the excess-64 exponent."""
    return ((mantissa & 0xFFFFFF) << 8) | ((sign & 1) << 7) | ((exponent + 64) & 0x7F)


def normalised(rng):
    """A number as the original's own code makes them: the top mantissa bit set and an
    exponent byte that is not the zero."""
    return (rng.randrange(1 << 23, 1 << 24) << 8) | rng.randrange(1, 256)


ONE      = number(0x800000, 0, 1)
MINUS_ONE = number(0x800000, 1, 1)
HALF     = number(0x800000, 0, 0)
BIGGEST  = number(0xFFFFFF, 0, 63)          # exponent byte 0x7F, the largest exponent
SMALLEST = number(0x800000, 0, -63)         # exponent byte 0x01, the smallest that is not zero
NEG_BIGGEST  = number(0xFFFFFF, 1, 63)
NEG_SMALLEST = number(0x800000, 1, -63)
SIGNED_ZERO  = number(0, 1, -64)            # 0x00000080: zero mantissa, sign bit set
EXPONENT_ZERO = 0x12345600                  # a mantissa with the zero exponent byte
UNNORMALISED  = number(0x000001, 0, 1)      # top mantissa bit clear

# Every edge SPEC 10 point 13 names, by name.  The reference and the port must agree on all
# of them; the ones whose answer is the behaviour of the format are pinned below as well.
EDGES = [
    ('zero',                              'add', 0, ONE),
    ('zero as the second operand',        'add', ONE, 0),
    ('zero',                              'sub', 0, ONE),
    ('zero',                              'mul', 0, ONE),
    ('zero as the dividend',              'div', 0, ONE),
    ('zero',                              'cmp', 0, 0),
    ('zero',                              'tst', 0, 0),
    ('zero',                              'neg', 0, 0),
    ('zero',                              'fix', 0, 0),
    ('zero',                              'flt', 0, 0),
    ('a zero mantissa with the sign set', 'add', SIGNED_ZERO, ONE),
    ('a zero mantissa with the sign set', 'sub', SIGNED_ZERO, ONE),
    ('a zero mantissa with the sign set', 'mul', SIGNED_ZERO, ONE),
    ('a zero mantissa with the sign set', 'div', ONE, SIGNED_ZERO),
    ('a zero mantissa with the sign set', 'cmp', SIGNED_ZERO, ONE),
    ('a zero mantissa with the sign set', 'tst', 0, SIGNED_ZERO),
    ('a zero mantissa with the sign set', 'neg', SIGNED_ZERO, 0),
    ('a zero mantissa with the sign set', 'fix', SIGNED_ZERO, 0),
    ('a mantissa with the zero exponent', 'add', EXPONENT_ZERO, ONE),
    ('a mantissa with the zero exponent', 'mul', EXPONENT_ZERO, ONE),
    ('a mantissa with the zero exponent', 'fix', EXPONENT_ZERO, 0),
    ('the largest exponent',              'add', BIGGEST, ONE),
    ('the largest exponent',              'mul', BIGGEST, ONE),
    ('the smallest exponent',             'add', SMALLEST, SMALLEST),
    ('the smallest exponent',             'mul', SMALLEST, ONE),
    ('overflow',                          'add', BIGGEST, BIGGEST),
    ('overflow',                          'sub', BIGGEST, NEG_BIGGEST),
    ('overflow',                          'mul', BIGGEST, BIGGEST),
    ('overflow',                          'div', BIGGEST, SMALLEST),
    ('overflow, negative',                'add', NEG_BIGGEST, NEG_BIGGEST),
    ('overflow, negative',                'mul', NEG_BIGGEST, BIGGEST),
    ('overflow',                          'fix', BIGGEST, 0),
    ('overflow, negative',                'fix', NEG_BIGGEST, 0),
    ('underflow',                         'mul', SMALLEST, SMALLEST),
    ('underflow',                         'div', SMALLEST, BIGGEST),
    ('underflow',                         'mul', NEG_SMALLEST, SMALLEST),
    ('equal magnitude, opposite sign',    'add', ONE, MINUS_ONE),
    ('equal magnitude, opposite sign',    'sub', ONE, ONE),
    ('equal magnitude, opposite sign',    'add', BIGGEST, NEG_BIGGEST),
    ('equal magnitude, opposite sign',    'cmp', ONE, MINUS_ONE),
    ('exponents 23 apart',                'add', number(0x800000, 0, 24), ONE),
    ('exponents 24 apart',                'add', number(0x800000, 0, 25), ONE),
    ('exponents 25 apart',                'add', number(0x800000, 0, 26), ONE),
    ('exponents 24 apart, opposite signs', 'add', number(0x800000, 0, 25), MINUS_ONE),
    ('exponents 24 apart, the other way', 'add', ONE, number(0x800000, 0, 25)),
    ('exponents 24 apart',                'sub', ONE, number(0x800000, 0, 25)),
    ('an unnormalised operand',           'add', UNNORMALISED, ONE),
    ('an unnormalised operand',           'sub', UNNORMALISED, ONE),
    ('an unnormalised operand',           'mul', UNNORMALISED, ONE),
    ('an unnormalised operand',           'cmp', UNNORMALISED, ONE),
    ('an unnormalised operand',           'fix', number(0x000001, 0, 40), 0),
    ('an unnormalised dividend',          'div', UNNORMALISED, ONE),
    ('division by zero',                  'div', ONE, 0),
    ('division by an unnormalised divisor', 'div', ONE, UNNORMALISED),
    ('SPFix between -1 and 1',            'fix', HALF, 0),
    ('SPFix between -1 and 1',            'fix', number(0x800000, 1, 0), 0),
    ('SPFix between -1 and 1',            'fix', number(0xFFFFFF, 0, 0), 0),
    ('SPFix of 2^31',                     'fix', number(0x800000, 0, 32), 0),
    ('SPFix of -2^31',                    'fix', number(0x800000, 1, 32), 0),
    ('SPFix of 2^31 - 128',               'fix', number(0xFFFFFF, 0, 31), 0),
    ('SPFix beyond 32 bits',              'fix', number(0x800000, 0, 33), 0),
    ('SPFix beyond 32 bits, negative',    'fix', number(0x800001, 1, 32), 0),
    ('SPFix of the smallest',             'fix', SMALLEST, 0),
    ('SPFlt of 0',                        'flt', 0, 0),
    ('SPFlt of 1',                        'flt', 1, 0),
    ('SPFlt of -1',                       'flt', 0xFFFFFFFF, 0),
    ('SPFlt of 0x7FFFFFFF',               'flt', 0x7FFFFFFF, 0),
    ('SPFlt of 0x80000000',               'flt', 0x80000000, 0),
    ('SPFlt of 24 bits',                  'flt', 0x00FFFFFF, 0),
    ('SPFlt of 25 bits',                  'flt', 0x01000001, 0),
    ('SPFlt of 25 bits, rounding up',     'flt', 0x01000003, 0),
    ('SPFlt of 32 bits, negative',        'flt', 0xFE000001, 0),
    ('SPFlt of 0xFFFFFF80',               'flt', 0xFFFFFF80, 0),
]

# What the ROM answers where the answer is the behaviour of the format rather than a number
# that follows from it.  These are observed (tests/ffp.py on original/kick.rom) and they are
# what re/notes/ffp.md states.
ROM_ANSWERS = [
    ('overflow is the largest magnitude with V',      'add', BIGGEST, BIGGEST,
     0xFFFFFF7F, V),
    ('overflow keeps the sign',                       'add', NEG_BIGGEST, NEG_BIGGEST,
     0xFFFFFFFF, X | N | V),
    ('SPMul overflows the same way',                  'mul', BIGGEST, BIGGEST,
     0xFFFFFF7F, V),
    ('underflow is a clean zero',                     'mul', SMALLEST, SMALLEST,
     0x00000000, X | Z),
    ('a quotient that underflows is zero',            'div', SMALLEST, BIGGEST,
     0x00000000, Z),
    ('equal magnitudes cancel to zero',               'add', ONE, MINUS_ONE,
     0x00000000, Z),
    ('an operand 24 exponents smaller is lost',       'add', number(0x800000, 0, 25), ONE,
     number(0x800000, 0, 25), 0),
    ('an operand 23 exponents smaller still counts',  'add', number(0x800000, 0, 24), ONE,
     0x80000158, 0),
    ('SPFix of 2^31 overflows to 0x7FFFFFFF',         'fix', number(0x800000, 0, 32), 0,
     0x7FFFFFFF, X | V | C),
    ('SPFix of -2^31 is exact',                       'fix', number(0x800000, 1, 32), 0,
     0x80000000, X | N),
    ('SPFix truncates towards zero',                  'fix', number(0xFFFFFF, 0, 0), 0,
     0x00000000, X | Z),
    ('SPFlt rounds to nearest, half away from zero',  'flt', 0x01000001, 0,
     0x80000159, 0),
    ('SPFlt of 0x7FFFFFFF rounds up to 2^31',         'flt', 0x7FFFFFFF, 0,
     0x80000060, 0),
    ('a zero exponent byte is zero whatever the mantissa', 'fix', EXPONENT_ZERO, 0,
     EXPONENT_ZERO, Z),
    ('negating a zero mantissa with the sign set gives the true zero', 'neg', SIGNED_ZERO, 0,
     0x00000000, Z),
]


@needs_rom
@pytest.mark.parametrize('name,operation,d0,d1,result,ccr', ROM_ANSWERS,
                         ids=['%s: %s' % (entry[1], entry[0]) for entry in ROM_ANSWERS])
def test_what_the_rom_answers_at_its_edges(name, operation, d0, d1, result, ccr):
    got = ffp.Reference().call(operation, d0, d1)
    assert (got.d0, got.ccr) == (result, ccr), '%s %s: %s' % (operation, name, got)


@needs_rom
def test_a_divisor_whose_exponent_byte_is_zero_traps():
    """SPDiv reaches `divu.w #0,d0` there, which is the 68000's zero divide.  A real
    machine would take exception vector 5; SPEC 7.1 has the port assert instead."""
    reference = ffp.Reference()
    with pytest.raises(ffp.Trap) as raised:
        reference.call('div', ONE, 0)
    assert raised.value.vector == 5


@needs_rom
def test_a_divisor_with_a_tiny_mantissa_traps_at_the_other_divide():
    """The second zero divide: after the swap SPDiv divides by the divisor's high word,
    which is zero when the mantissa is below 0x100.  Only an unnormalised operand gets
    there, and the port reports the same trap."""
    reference = ffp.Reference()
    with pytest.raises(ffp.Trap) as raised:
        reference.call('div', ONE, UNNORMALISED)
    assert raised.value.vector == 5


# ------------------------------------------------------------------------- the corpus
# One list of cases for all three ways the port is run: the native library, a stand-alone
# WebAssembly build and the same code under the undefined-behaviour sanitizer.  The
# random part is shaped so that the interesting cases are frequent - exponents close
# together, mantissas that differ in the last bits, the ends of the exponent range - and
# comes from a fixed seed, so a failure names an operand pair that can be looked at again.

RANDOM_PER_OPERATION = 2500
SEED = 0x1BDFA


def with_exponent(rng, mantissa, exponent_byte):
    return ((mantissa & 0xFFFFFF) << 8) | (exponent_byte & 0xFF)


def shaped(rng, shape, near=None):
    """One operand.  `near`, where it is given, is the operand this one should be close
    to, so that the exponent difference lands in the range where the arithmetic works."""
    if shape == 'raw':
        return rng.getrandbits(32)
    if shape == 'extreme':
        byte = rng.choice([0x01, 0x02, 0x03, 0x7D, 0x7E, 0x7F, 0x81, 0x82, 0xFD, 0xFE, 0xFF])
        return with_exponent(rng, rng.randrange(1 << 23, 1 << 24), byte)
    if shape == 'boundary':
        mantissa = rng.choice([0x800000, 0x800001, 0xFFFFFE, 0xFFFFFF,
                               0xFFFFFF - rng.randrange(4), 0x800000 + rng.randrange(4)])
        return with_exponent(rng, mantissa, rng.randrange(1, 256))
    if shape == 'close' and near is not None:
        sign = near & 0x80
        exponent = (near & 0x7F) + rng.randint(-26, 26)
        mantissa = ((near >> 8) ^ rng.getrandbits(rng.randrange(1, 9))) & 0xFFFFFF
        mantissa |= 1 << 23
        return with_exponent(rng, mantissa, sign | max(1, min(0x7F, exponent)))
    return normalised(rng)


SHAPES = ('norm', 'close', 'boundary', 'extreme', 'raw')

# SPFlt takes a plain 32-bit integer, so its corpus is integers of every width and both
# signs, plus the raw patterns.
def integer_of_every_width(rng):
    width = rng.randrange(1, 33)
    value = rng.getrandbits(width)
    return (-value if rng.getrandbits(1) else value) & 0xFFFFFFFF


def random_cases(rng, operation, count):
    out = []
    for i in range(count):
        shape = SHAPES[i % len(SHAPES)]
        if operation == 'flt':
            out.append((integer_of_every_width(rng), 0))
            continue
        d0 = shaped(rng, shape)
        if operation == 'div' and i % 7 == 6:
            # Both ways into the zero divide, often enough that all three targets meet them:
            # an exponent byte of zero, and a mantissa below 0x100, which leaves the high
            # word SPDiv divides by empty.
            divisor = (rng.randrange(0, 0x100) << 8) | rng.randrange(1, 256) \
                if rng.getrandbits(1) else (rng.randrange(1 << 23, 1 << 24) << 8)
            out.append((d0, divisor))
            continue
        if operation in ('fix', 'neg'):
            out.append((d0, 0))
        elif operation == 'tst':
            out.append((0, d0))
        else:
            out.append((d0, shaped(rng, shape, near=d0)))
    return out


OBSERVED = os.path.join(HERE, 'ffp_observed.json')


def observed_cases():
    """Every operand pair the headless original was seen to hand mathffp (deliverable 4 of
    SPEC 10 point 13; tools/ffp_observe.py writes the file)."""
    if not os.path.isfile(OBSERVED):
        return {}
    import json
    with open(OBSERVED, encoding='utf-8') as handle:
        return json.load(handle)['operands']


def build_corpus():
    """(operation index, D0, D1) for every case, in one list."""
    rng = random.Random(SEED)
    observed = observed_cases()
    cases = []
    for _, operation, d0, d1 in EDGES:
        cases.append((ffp.OPERATIONS.index(operation), d0, d1))
    for operation in ffp.OPERATIONS:
        index = ffp.OPERATIONS.index(operation)
        for d0, d1 in random_cases(rng, operation, RANDOM_PER_OPERATION):
            cases.append((index, d0, d1))
        for d0, d1 in observed.get(operation, []):
            cases.append((index, d0, d1))
    return cases


@pytest.fixture(scope='module')
def corpus():
    return build_corpus()


@pytest.fixture(scope='module')
def expected(corpus):
    """What the ROM answers for every case, through the game's glue.  A trap is kept as
    such: the original takes exception 5 and never returns a value."""
    if not ffp.rom_available():
        pytest.skip('original/kick.rom is absent')
    reference = ffp.Reference()
    out = []
    for index, d0, d1 in corpus:
        operation = ffp.OPERATIONS[index]
        try:
            got = reference.call(operation, d0, d1)
        except ffp.Trap as trap:
            out.append((None, None, None, trap.vector))
        else:
            out.append((got.d0, got.d1, got.ccr, 0))
    return out


def compare(corpus, expected, results, target):
    """One line per disagreement, the first few shown."""
    wrong = []
    for (index, d0, d1), want, got in zip(corpus, expected, results):
        operation = ffp.OPERATIONS[index]
        if want[3]:
            if got[3] != want[3]:
                wrong.append('%s %08X %08X: the original traps (%d), %s answers %s'
                             % (operation, d0, d1, want[3], target, got))
            continue
        if got[3] or (got[0], got[1], got[2]) != (want[0], want[1], want[2]):
            wrong.append('%s %08X %08X: rom d0=%08X d1=%08X %s, %s d0=%08X d1=%08X %s trap=%d'
                         % (operation, d0, d1, want[0], want[1], ccr_text(want[2]),
                            target, got[0], got[1], ccr_text(got[2]), got[3]))
    assert not wrong, '%d of %d cases differ on %s:\n%s' % (
        len(wrong), len(corpus), target, '\n'.join(wrong[:12]))


@needs_rom
def test_the_native_port_answers_what_the_rom_answers(ported, corpus, expected):
    ported.ffp_traps_reset()
    results = [ported.ffp(ffp.OPERATIONS[index], d0, d1) for index, d0, d1 in corpus]
    compare(corpus, expected, results, 'the native port')
    assert ported.ffp_traps() == sum(1 for want in expected if want[3]), \
        'the port counted a different number of zero divides than the original took'


# ------------------------------------------------- the other target, and the sanitizer
# SPEC 6.1: the same sources compile for wasm32-freestanding and natively, and the port
# relies on no undefined behaviour.  Both are claims about src/ffp.c specifically, so both
# are made here with src/ffp.c alone: one WebAssembly module built by this test and run in
# Node, and one native program built with -fsanitize=undefined.  Neither is part of
# dist/core.wasm; tests/ffp_export.c is the batch entry both of them use.

SRC = os.path.join(ROOT, 'src')
EXPORT = os.path.join(HERE, 'ffp_export.c')
WASM_RUNNER = os.path.join(HERE, 'ffp_wasm.mjs')
FFP_SOURCE = os.path.join(SRC, 'ffp.c')


def pack(corpus):
    return b''.join(struct.pack('<3I', index, d0, d1) for index, d0, d1 in corpus)


def unpack(raw, count):
    return [struct.unpack_from('<4I', raw, i * 16) for i in range(count)]


@needs_rom
def test_the_webassembly_build_answers_the_same(tmp_path, corpus, expected):
    module = tmp_path / 'ffp.wasm'
    built = subprocess.run(
        [sys.executable, '-m', 'ziglang', 'cc', '-target', 'wasm32-freestanding',
         '-std=c11', '-O2', '-Wall', '-Wextra', '-Werror', '-nostdlib', '-Wl,--no-entry',
         '-I', SRC, '-o', str(module), FFP_SOURCE, EXPORT],
        cwd=ROOT, capture_output=True, text=True)
    assert built.returncode == 0, built.stderr
    assert built.stderr == '', built.stderr

    cases, results = tmp_path / 'cases.bin', tmp_path / 'results.bin'
    cases.write_bytes(pack(corpus))
    run = subprocess.run(['node', WASM_RUNNER, str(module), str(cases), str(results)],
                         cwd=ROOT, capture_output=True, text=True)
    assert run.returncode == 0, run.stderr
    compare(corpus, expected, unpack(results.read_bytes(), len(corpus)), 'the wasm build')


@needs_rom
def test_the_same_code_under_the_undefined_behaviour_sanitizer(tmp_path, corpus, expected):
    """SPEC 6.1 forbids relying on undefined behaviour, and this code shifts, negates and
    overflows on purpose all over, so the claim is worth a machine's opinion.  The
    sanitizer stops on the first finding, so a clean run and matching answers together say
    that the whole corpus went through without one."""
    program = tmp_path / 'ffp_ubsan'
    built = subprocess.run(
        ['clang', '-std=c11', '-O1', '-g', '-Wall', '-Wextra', '-Werror',
         '-fsanitize=undefined', '-fno-sanitize-recover=all', '-I', SRC,
         '-o', str(program), FFP_SOURCE, EXPORT],
        cwd=ROOT, capture_output=True, text=True)
    assert built.returncode == 0, built.stderr

    cases, results = tmp_path / 'cases.bin', tmp_path / 'results.bin'
    cases.write_bytes(pack(corpus))
    run = subprocess.run([str(program), str(cases), str(results)],
                         cwd=ROOT, capture_output=True, text=True)
    assert run.returncode == 0, run.stdout + run.stderr
    assert 'runtime error' not in (run.stdout + run.stderr), run.stdout + run.stderr
    compare(corpus, expected, unpack(results.read_bytes(), len(corpus)), 'the sanitizer build')


# ------------------------------------------------ what the game computes, deliverable 4
# tools/ffp_observe.py ran the headless original with observers on the two routines of the
# tick that use floating point and on all nine glue entries, and wrote every floating-point
# call each entry made together with the memory at its entry and its return.  A model of the
# arithmetic (tests/ffp_model.py) has to produce both: the same calls, with the same
# operands at the same call sites and the same results, and the same memory afterwards.

import ffp_model                                            # noqa: E402


@pytest.fixture(scope='module')
def observations():
    if not os.path.isfile(OBSERVED):
        pytest.skip('tests/ffp_observed.json is absent; run tools/ffp_observe.py')
    import json
    with open(OBSERVED, encoding='utf-8') as handle:
        return json.load(handle)


def check_model(routine, entries, engine):
    model, observed = ffp_model.MODELS[routine]
    assert len(entries) >= 200, '%s was observed only %d times' % (routine, len(entries))
    wrong = []
    for entry in entries:
        calls, left = model(entry, engine)
        want = [ffp_model.call_key(call) for call in entry['calls']]
        got = [ffp_model.call_key(call) for call in calls]
        if got != want:
            wrong.append('%s run %s tick %d: the original called\n  %s\nthe model calls\n  %s'
                         % (routine, entry['run'], entry['tick'], want, got))
        elif left != observed(entry):
            wrong.append('%s run %s tick %d: the original left %s, the model leaves %s'
                         % (routine, entry['run'], entry['tick'], observed(entry), left))
    assert not wrong, '%d of %d entries differ:\n%s' % (
        len(wrong), len(entries), '\n'.join(wrong[:3]))


@needs_rom
@pytest.mark.parametrize('routine', sorted(ffp_model.MODELS))
def test_the_model_reproduces_what_the_original_computed(observations, routine):
    reference = ffp.Reference()
    check_model(routine, observations['entries'][routine],
                lambda operation, d0, d1: reference.call(operation, d0, d1).d0)


@pytest.mark.parametrize('routine', sorted(ffp_model.MODELS))
def test_the_model_gives_the_same_answers_on_the_ported_floating_point(ported, observations,
                                                                       routine):
    """The same model driven by src/ffp.c rather than by the ROM.  It needs no ROM, so this
    is also what says the port carries the game's own arithmetic on a machine without one."""
    check_model(routine, observations['entries'][routine],
                lambda operation, d0, d1: ported.ffp(operation, d0, d1)[0])


def test_every_operand_the_game_was_seen_to_produce_is_in_the_corpus(observations):
    """Deliverable 3c: the differential test runs on the real operands too, not only on
    made-up ones."""
    corpus = set((ffp.OPERATIONS[index], d0, d1) for index, d0, d1 in build_corpus())
    for operation, pairs in observations['operands'].items():
        for d0, d1 in pairs:
            assert (operation, d0, d1) in corpus, '%s %08X %08X was observed but is not tested' % (
                operation, d0, d1)


def test_the_tables_of_constants_are_normalised(observations):
    """Every entry of both tables has its top mantissa bit set, or is the zero, so nothing
    the game hands mathffp from them is unnormalised (re/notes/ffp.md)."""
    for table in (ffp_model.ATTITUDE, ffp_model.SINE):
        for value in table:
            assert value == 0 or (value >> 8) >= (1 << 23), '%08X is unnormalised' % value
    assert len(ffp_model.ATTITUDE) == 26 and len(ffp_model.SINE) == 91
    assert ffp_model.ATTITUDE[0] == 0x80000041 and ffp_model.ATTITUDE[14] == 0
    assert ffp_model.SINE[0] == 0 and ffp_model.SINE[90] == 0x80000041


def test_the_indices_the_game_uses_stay_inside_the_tables(observations):
    """The extent of the table at 0x025B0C is 26 entries because the sine table begins
    there; this is the observed half of that claim."""
    for routine, entries in observations['entries'].items():
        for entry in entries:
            for call in entry['calls']:
                if call[1] == 'mul' and call[0] in (0x01BEE8, 0x01D814):
                    assert call[2] in ffp_model.ATTITUDE, (
                        '%08X came out of the table at 0x025B0C but is not in it' % call[2])


# ------------------------------------------------- 0x021A40, the third routine, is dead
# It is the floating-point conversion of the C library's formatter, reached from 0x0218A4
# only for a conversion letter of 'e' or above (`sub.w #$65,d0` at 0x02187A).  No run
# entered it, and no format string the game hands its sprintf carries such a letter.

SPRINTF = 0x0215D8
FORMAT_CONVERSION = 0x021A40


@needs_rom
def test_the_formatter_is_entered_only_by_a_floating_point_conversion():
    """The control for the negative finding: the same observer that never fired in any run
    does fire as soon as sprintf is given a floating-point conversion.  Without it, 'the
    game never reaches 0x021A40' would be indistinguishable from 'the observer is broken'."""
    reference = ffp.Reference()
    machine = reference.o
    entered = []
    machine.uc.hook_add(UC_HOOK_CODE, lambda uc, address, size, user: entered.append(address),
                        begin=FORMAT_CONVERSION, end=FORMAT_CONVERSION)
    buffer = machine.alloc(256)

    def formatted(text, argument):
        entered.clear()
        machine.write(buffer, bytes(256))
        machine.call(SPRINTF, machine.L(buffer), machine.L(machine.alloc_bytes(text + b'\0')),
                     argument)
        return machine.read(buffer, 64).split(b'\0')[0].decode('latin1'), len(entered)

    assert formatted(b'%d', machine.W(1234)) == ('1234', 0)
    assert formatted(b'%f', machine.L(0xC8000047)) == ('100.000000', 1)
    assert formatted(b'%e', machine.L(0xC8000047)) == ('1.000000e+02', 1)
    assert formatted(b'[%8.3f]', machine.L(0xE10000C4)) == ('[ -14.062]', 1)


def test_the_game_hands_its_formatter_no_floating_point_conversion(listing):
    """The read half: the format string pushed in front of every call of sprintf, and of
    the one wrapper that takes its format as a parameter.  Four carry `%d`, one `%-6ld`,
    one `%-12s`, and the five of the crack's text screen carry no conversion at all; that
    screen is not ported (SPEC 8) and is not the game."""
    lines = listing.split('\n')

    def pushed_before(index):
        found = [re.search(r'; "(.*)"$', earlier) for earlier in lines[max(0, index - 8):index]]
        text = [match.group(1) for match in found if match]
        return text[-1] if text else None

    direct, wrapped = [], []
    for index, line in enumerate(lines):
        if line.rstrip().endswith('-> sprintf'):
            direct.append(pushed_before(index))
        elif line.rstrip().endswith('; sub_01f332'):
            wrapped.append(pushed_before(index))

    assert len(direct) == 7 and len(wrapped) == 5
    # Six of the seven push a literal; the seventh is inside sub_01f332, which passes on
    # the format its own five callers, all in the crack's text screen, hand it.
    literals = [text for text in direct if text is not None]
    assert len(literals) == 6 and direct.count(None) == 1
    assert literals.count('%d') == 4 and '%-6ld' in literals and '%-12s' in literals
    assert all(text is not None for text in wrapped)

    conversions = set(re.findall(r'%[-0-9.l]*([a-zA-Z])', ' '.join(literals + wrapped)))
    assert conversions == {'d', 's'}, 'a format string carries %s' % sorted(conversions)


def test_no_run_entered_the_formatter(observations):
    assert observations['entries']['sub_021a40'] == []
    assert observations['sites'].get('sub', {}) == {}
    assert observations['sites'].get('cmp', {}) == {}
    assert observations['sites'].get('tst', {}) == {}
