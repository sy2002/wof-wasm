"""A small model of the Amiga blitter's area mode, for checking the ported shape blit.

The original draws every shape by programming the blitter (re/notes/drawing.md), so the
port cannot be compared with it the way a pure routine can.  What this module makes
possible instead:

  1. run the original's `shape_draw` under the oracle with the custom-chip space mapped as
     plain memory, and hook the write to BLTSIZE (0xDFF058) that starts each blit;
  2. read the register programme out of that memory at exactly that moment;
  3. execute the programme here, on a copy of the emulated bitplanes;
  4. convert the planes to indexed pixels and compare with the port's framebuffer.

Everything in step 1 and 2 - the clipping arithmetic, the pointers, the modulos, the
sizes, the word masks, the order of the three phases - comes from the original's own code.
Step 3 is documented hardware behaviour rather than something this project re-derived:
the minterm (BLTCON0's low byte indexed by A, B, C), the barrel shifters (BLTCON0's high
nibble for A, BLTCON1's high nibble for B, carrying between words and across rows), and
the first and last word masks, which apply to the A channel whether A comes from memory
or from the constant BLTADAT.  That last point is what lets an unshifted opaque blit run
with USEA and USEC both off, which the original does, and it is what keeps a shifted one
from writing outside the shape's own box.

Only what the drawing of the game uses is modelled: the ascending area mode, and the line
mode for line_draw (execute_line).  Descending mode and the fill modes are asserted absent
rather than implemented; if a caller ever needs them, this stops.
"""
import struct

CUSTOM = 0xDFF000

BLTCON0 = 0x040
BLTCON1 = 0x042
BLTAFWM = 0x044
BLTALWM = 0x046
BLTCPT = 0x048
BLTBPT = 0x04C
BLTAPT = 0x050
BLTDPT = 0x054
BLTSIZE = 0x058
BLTCMOD = 0x060
BLTBMOD = 0x062
BLTAMOD = 0x064
BLTDMOD = 0x066
BLTCDAT = 0x070
BLTBDAT = 0x072
BLTADAT = 0x074

USEA, USEB, USEC, USED = 0x800, 0x400, 0x200, 0x100


def signed16(v):
    return v - 0x10000 if v & 0x8000 else v


class Blit:
    """One BLTSIZE write: the whole register programme as it stood at that moment."""

    def __init__(self, registers, size):
        r = registers
        self.con0 = r[BLTCON0]
        self.con1 = r[BLTCON1]
        self.afwm = r[BLTAFWM]
        self.alwm = r[BLTALWM]
        # Each pointer is a register pair: the high word at the named offset, the low
        # word two bytes on.  Only 21 bits reach the chip.
        self.apt = ((r[BLTAPT] << 16) | r[BLTAPT + 2]) & 0x1FFFFE
        self.aptl = r[BLTAPT + 2]                 # the line mode's accumulator, whole
        self.bpt = ((r[BLTBPT] << 16) | r[BLTBPT + 2]) & 0x1FFFFE
        self.cpt = ((r[BLTCPT] << 16) | r[BLTCPT + 2]) & 0x1FFFFE
        self.dpt = ((r[BLTDPT] << 16) | r[BLTDPT + 2]) & 0x1FFFFE
        self.amod = signed16(r[BLTAMOD])
        self.bmod = signed16(r[BLTBMOD])
        self.cmod = signed16(r[BLTCMOD])
        self.dmod = signed16(r[BLTDMOD])
        self.adat = r[BLTADAT]
        self.bdat = r[BLTBDAT]
        self.cdat = r[BLTCDAT]
        self.size = size
        self.rows = (size >> 6) & 0x3FF
        self.words = size & 0x3F
        if self.rows == 0:
            self.rows = 1024
        if self.words == 0:
            self.words = 64

    @property
    def minterm(self):
        return self.con0 & 0xFF

    @property
    def ash(self):
        return (self.con0 >> 12) & 0xF

    @property
    def bsh(self):
        return (self.con1 >> 12) & 0xF

    def __repr__(self):
        return ('Blit(con0=%04X con1=%04X fwm=%04X lwm=%04X %dx%d words '
                'a=%06X b=%06X c=%06X d=%06X mods=%d/%d/%d/%d)'
                % (self.con0, self.con1, self.afwm, self.alwm, self.rows, self.words,
                   self.apt, self.bpt, self.cpt, self.dpt,
                   self.amod, self.bmod, self.cmod, self.dmod))


class Window:
    """A window of emulated memory, addressed absolutely, 16-bit big-endian."""

    def __init__(self, base, data):
        self.base = base
        self.data = bytearray(data)

    def r16(self, addr):
        off = addr - self.base
        assert 0 <= off <= len(self.data) - 2, 'read outside the window at %06X' % addr
        return struct.unpack_from('>H', self.data, off)[0]

    def w16(self, addr, value):
        off = addr - self.base
        assert 0 <= off <= len(self.data) - 2, 'write outside the window at %06X' % addr
        struct.pack_into('>H', self.data, off, value & 0xFFFF)


def minterm_word(lf, a, b, c):
    """D = the sum of the minterms LF names, over A, B and C as 16-bit words."""
    d = 0
    for t in range(8):
        if not (lf >> t) & 1:
            continue
        av = a if t & 4 else ~a
        bv = b if t & 2 else ~b
        cv = c if t & 1 else ~c
        d |= av & bv & cv
    return d & 0xFFFF


def execute_line(mem, blit):
    """Run one line-mode blit: one pixel per row of BLTSIZE's height, from the word at
    BLTCPT (BLTDPT is the same) and the bit BLTCON0's shift names.  A is BLTADAT (a single
    bit) shifted to the pixel, B the texture BLTBDAT, C the word under it, D what the minterm
    makes of them.  After a pixel the octant bits of BLTCON1 step the position: SUD set
    means the major axis is x, SUL and AUL make the minor and the major step negative; the
    minor step comes only while the accumulator's sign is clear, and the accumulator
    (BLTAPTL) then adds BLTAMOD, else BLTBMOD.  ONEDOT is not modelled; the game never sets
    it.  This is the documented behaviour of the line mode, not something derived from the
    game."""
    assert blit.words == 2, 'a line blit is two words wide: %r' % blit
    assert not (blit.con1 & 0x02), 'ONEDOT is not modelled: con1=%04X' % blit.con1
    sud, sul, aul = blit.con1 & 0x10, blit.con1 & 0x08, blit.con1 & 0x04
    sign = bool(blit.con1 & 0x40)
    acc = signed16(blit.aptl)
    ptr = blit.cpt
    bit = blit.ash
    for _ in range(blit.rows):
        a = (blit.adat >> bit) & 0xFFFF
        c = mem.r16(ptr)
        mem.w16(ptr, minterm_word(blit.minterm, a, blit.bdat, c))

        def step_x(back):
            nonlocal ptr, bit
            if back:
                bit -= 1
                if bit < 0:
                    bit, ptr = 15, ptr - 2
            else:
                bit += 1
                if bit > 15:
                    bit, ptr = 0, ptr + 2

        def step_y(back):
            nonlocal ptr
            ptr += -blit.cmod if back else blit.cmod

        if not sign:
            (step_y if sud else step_x)(sul)
        (step_x if sud else step_y)(aul)
        acc = signed16((acc + (blit.amod if not sign else blit.bmod)) & 0xFFFF)
        sign = acc < 0


def execute(mem, blit):
    """Run one blit against `mem`: an ascending area-mode blit, or a line."""
    if blit.con1 & 0x01:
        execute_line(mem, blit)
        return
    assert not (blit.con1 & 0x02), 'descending mode is not modelled: con1=%04X' % blit.con1
    assert not (blit.con1 & 0x1A), 'fill mode is not modelled: con1=%04X' % blit.con1

    apt, bpt, cpt, dpt = blit.apt, blit.bpt, blit.cpt, blit.dpt
    a_hold = b_hold = 0

    for row in range(blit.rows):
        for word in range(blit.words):
            raw_a = mem.r16(apt) if blit.con0 & USEA else blit.adat
            if word == 0:
                raw_a &= blit.afwm
            if word == blit.words - 1:
                raw_a &= blit.alwm
            a = (((a_hold << 16) | raw_a) >> blit.ash) & 0xFFFF
            a_hold = raw_a

            raw_b = mem.r16(bpt) if blit.con0 & USEB else blit.bdat
            b = (((b_hold << 16) | raw_b) >> blit.bsh) & 0xFFFF
            b_hold = raw_b

            c = mem.r16(cpt) if blit.con0 & USEC else blit.cdat

            d = minterm_word(blit.minterm, a, b, c)
            if blit.con0 & USED:
                mem.w16(dpt, d)

            apt += 2
            bpt += 2
            cpt += 2
            dpt += 2

        apt += blit.amod
        bpt += blit.bmod
        cpt += blit.cmod
        dpt += blit.dmod


def capture(oracle):
    """Hook BLTSIZE so that every blit the emulated code starts is recorded.

    Returns the list the hook appends to.  The custom-chip space must be mapped as plain
    memory first (see map_custom), so that the register writes land somewhere readable and
    the busy-wait on DMACONR bit 14 falls straight through.
    """
    from unicorn import UC_HOOK_MEM_WRITE

    blits = []

    def on_write(uc, access, address, size, value, user):
        if address != CUSTOM + BLTSIZE:
            return
        registers = {}
        raw = bytes(uc.mem_read(CUSTOM + 0x040, 0x40))
        for offset in range(0x040, 0x080, 2):
            registers[offset] = struct.unpack_from('>H', raw, offset - 0x040)[0]
        blits.append(Blit(registers, value & 0xFFFF))

    oracle.uc.hook_add(UC_HOOK_MEM_WRITE, on_write,
                       begin=CUSTOM + BLTSIZE, end=CUSTOM + BLTSIZE + 1)
    return blits


def map_custom(oracle):
    """Map 0xDFF000 as plain memory, as SPEC section 8 says the headless original does."""
    oracle.uc.mem_map(0xDF0000, 0x10000)
    oracle.uc.mem_write(0xDF0000, bytes(0x10000))


def planes_to_indexed(mem, planes, bytes_per_row, rows):
    """The emulated bitplanes as indexed pixels, the way the port stores them."""
    import numpy

    width = bytes_per_row * 8
    out = numpy.zeros(width * rows, dtype=numpy.uint8)

    for index, base in enumerate(planes):
        off = base - mem.base
        raw = numpy.frombuffer(bytes(mem.data[off:off + bytes_per_row * rows]),
                               dtype=numpy.uint8)
        out |= numpy.unpackbits(raw) << index
    return out.tobytes()


def indexed_to_planes(pixels, bytes_per_row, rows, depth):
    """The inverse, for putting a background into the emulated bitplanes."""
    import numpy

    values = numpy.frombuffer(pixels, dtype=numpy.uint8)
    return [numpy.packbits((values >> p) & 1).tobytes() for p in range(depth)]
