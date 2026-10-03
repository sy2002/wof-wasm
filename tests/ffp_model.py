"""What the two tick routines compute, as a model (SPEC 10 point 13, deliverable 4).

`sub_01bdfa` (0x01BDFA) and `sub_01d796` (0x01D796) are the only routines of the game's
logic that use floating point and are in the call tree of the tick.  Each model here takes
the memory the headless original recorded at the routine's entry and produces both the
floating-point calls the routine should make, in order, and the memory it should leave.
tests/test_oracle_ffp.py compares both with what was observed, over every recorded entry.

The floating point comes in as a callable so that the same model can be driven by the ROM
through tests/ffp.py or by the port; the arithmetic around it is the original's own widths,
which are 16 bits for `int` (SPEC 7.1).
"""
import os
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, 'tools'))

import hunk                                                  # noqa: E402

EXE = os.path.join(ROOT, 'original', 'disk', 'Wings_of_Fury', 'Wings')

# The two tables of floating-point constants in the DATA hunk.  Their extent follows from
# the code that indexes them and from where the next one begins; re/notes/ffp.md.
TABLE_ATTITUDE = (0x025B0C, 26)      # indexed by an attitude word, 0 to 25
TABLE_SINE     = (0x025B74, 91)      # indexed by degrees, 0 to 90


def load_tables(exe=EXE):
    segments = hunk.load(exe)
    data = next(s for s in segments if s['base'] == 0x023000)['data']

    def read(base, count):
        at = base - 0x023000
        return [struct.unpack_from('>L', bytes(data), at + 4 * i)[0] for i in range(count)]

    return read(*TABLE_ATTITUDE), read(*TABLE_SINE)


ATTITUDE, SINE = load_tables()


# ------------------------------------------------------------- the original's arithmetic

def s16(v):
    v &= 0xFFFF
    return v - 0x10000 if v & 0x8000 else v


def s32(v):
    v &= 0xFFFFFFFF
    return v - (1 << 32) if v & 0x80000000 else v


def u16(v):
    return v & 0xFFFF


def divs_w(dividend, divisor):
    """divs.w: 32 by 16, truncated towards zero, a 16-bit quotient."""
    dividend, divisor = s32(dividend), s16(divisor)
    quotient = abs(dividend) // abs(divisor)
    if (dividend < 0) != (divisor < 0):
        quotient = -quotient
    return s16(quotient)


def muls_w(a, b):
    """muls.w: two 16-bit values into 32 bits."""
    return s16(a) * s16(b)


class Memory:
    """The watched ranges, addressed the way the listing addresses them."""

    def __init__(self, watched, ranges):
        self.blocks = {name: bytearray(bytes.fromhex(watched[name]))
                       for name in watched if name in ranges}
        self.ranges = ranges

    def w(self, name, offset):
        return struct.unpack_from('>H', self.blocks[name], offset)[0]

    def sw(self, name, offset):
        return struct.unpack_from('>h', self.blocks[name], offset)[0]

    def b(self, name, offset):
        return self.blocks[name][offset]


# The ranges tools/ffp_observe.py records, as (name, base).
RANGES = {'player': 0x000000, 'aircraft': 0x02522A, 'g_025402': 0x025402,
          'g_025aa2': 0x025AA2, 'g_027dea': 0x027DEA, 'g_025f16': 0x025F16,
          'g_026d43': 0x026D43}


class Calls:
    """The floating point, recorded as it is used."""

    def __init__(self, engine):
        self.engine = engine
        self.made = []

    def __call__(self, site, operation, d0, d1=0):
        d0, d1 = d0 & 0xFFFFFFFF, d1 & 0xFFFFFFFF
        out = self.engine(operation, d0, d1)
        self.made.append([site, operation, d0, d1, out])
        return out


# ------------------------------------------------------------------------- 0x01BDFA

def model_01bdfa(entry, engine):
    """orig 0x01BDFA, called once per tick from 0x01C70E.

    It moves the pitch (0x025AA2) a quarter of the way towards its target (0x025402), turns
    the sum of wind and the player's own drift into a pair of table entries, and from those
    and the airspeed (0x025414) computes the player aircraft's two speed components,
    +0x16 and +0x18, its position +0x00 and +0x02, and the airspeed's step at 0x027DEA.

    Returns the calls it makes and the values it leaves.
    """
    memory = Memory(entry['in'], RANGES)
    ffp = Calls(engine)

    g_025aaa = memory.sw('g_025aa2', 0x08)
    g_025402 = memory.sw('g_025402', 0x00)
    g_025aa2 = memory.sw('g_025aa2', 0x00)
    g_025408 = memory.sw('g_025402', 0x06)
    g_02540e = memory.sw('g_025402', 0x0C)
    g_025414 = memory.sw('g_025402', 0x12)
    g_027dea = memory.sw('g_027dea', 0x00)
    g_025f16 = memory.sw('g_025f16', 0x00)
    g_026d43 = memory.b('g_026d43', 0x00)
    player_0    = memory.sw('player', 0x00)
    player_2    = memory.sw('player', 0x02)
    player_c    = memory.sw('player', 0x0C)
    player_14   = memory.sw('player', 0x14)

    # 0x01BE02: the pitch creeps a quarter of the way towards its target, which is 0xFCE0
    # while 0x025AAA is set and 0x025402 stands at 0x258.
    if g_025aaa != 0 and g_025402 == 0x258:
        step = divs_w(s16(0xFCE0 - g_025aa2), 4)
    else:
        step = divs_w(s16(g_025402 - g_025aa2), 4)
    g_025aa2 = s16(g_025aa2 + step)

    # 0x01BE36: the magnitude of wind plus drift, in hundredths, indexes the sine table
    # twice - once directly and once as its complement to 0x2328, which is 90 x 100.
    angle = s16(g_025aa2 + g_025408)
    if angle < 0:
        angle = s16(-angle)
    across = SINE[divs_w(angle, 100)]                                   # -0x4(a5)
    along = SINE[divs_w(s16(0x2328 - angle), 100)]                      # -0x8(a5)

    # 0x01BE80: the across component takes the sign of the pitch and the tick's pitch offset.
    if g_025aa2 < 0 or g_025408 < 0:
        across = ffp(0x01BE90, 'neg', across)

    # 0x01BE98: the airspeed's step goes down by it, and by a further tenth while the aircraft is
    # airborne and the airspeed is below 0x3E8.
    g_027dea = s16(g_027dea - u16(ffp(0x01BE9C, 'fix', across)))
    if player_14 > 0 and g_025414 < 0x3E8:
        g_027dea = s16(g_027dea - divs_w(g_027dea, 10))

    # 0x01BEC4: horizontal speed = (attitude factor x airspeed x along + 50) / 100.
    speed = ffp(0x01BEE8, 'mul', ATTITUDE[g_02540e], ffp(0x01BEE0, 'flt', s32(g_025414)))
    speed = ffp(0x01BEF0, 'mul', speed, along)
    speed = ffp(0x01BEFA, 'add', speed, 0xC8000046)                     # 50.0
    speed = ffp(0x01BF04, 'div', speed, 0xC8000047)                     # 100.0
    player_16 = s16(ffp(0x01BF08, 'fix', speed))
    player_2 = s16(player_2 + muls_w(player_16, player_14))

    # 0x01BF2C: vertical speed = airspeed x across / 100, less a drop while slow.
    climb = ffp(0x01BF3A, 'mul', ffp(0x01BF32, 'flt', s32(g_025414)), across)
    climb = ffp(0x01BF44, 'div', climb, 0xC8000047)                     # 100.0
    player_18 = s16(ffp(0x01BF48, 'fix', climb))
    if g_025414 < 0x3E8 and player_c == 0:
        if not g_026d43 & 1:
            g_025402 = s16(g_025402 - divs_w(g_025f16, 2))
            if g_025402 < s16(0xEE6C):
                g_025402 = s16(0xEE6C)
        player_18 = s16(player_18 - divs_w(s16(0x3E8 - g_025414), 100))

    # 0x01BFA0: the height follows, bounded above at 0x44C, where the pitch target reverses and the
    # climb is halved and turned round, and below at -4.
    player_0 = s16(player_0 + player_18)
    if player_0 > 0x44C:
        player_0 = 0x44C
        g_025402 = s16(-g_025402)
        player_18 = s16(-divs_w(player_18, 2))
    elif player_0 < -4:
        player_0 = -4

    return ffp.made, {
        'g_025aa2': u16(g_025aa2), 'g_025402': u16(g_025402), 'g_027dea': u16(g_027dea),
        'player_0': u16(player_0), 'player_2': u16(player_2),
        'player_16': u16(player_16), 'player_18': u16(player_18),
    }


def observed_01bdfa(entry):
    """The same values as the run left them, for the comparison."""
    memory = Memory(entry['out'], RANGES)
    return {
        'g_025aa2': memory.w('g_025aa2', 0x00), 'g_025402': memory.w('g_025402', 0x00),
        'g_027dea': memory.w('g_027dea', 0x00),
        'player_0': memory.w('player', 0x00), 'player_2': memory.w('player', 0x02),
        'player_16': memory.w('player', 0x16), 'player_18': memory.w('player', 0x18),
    }


# ------------------------------------------------------------------------- 0x01D796

def aircraft_offset(entry):
    """Which of the four enemy-aircraft records this entry was handed."""
    return entry['arg'] - RANGES['aircraft']


def model_01d796(entry, engine):
    """orig 0x01D796, called from 0x01E898 for every enemy aircraft that is not in state
    0x10, once per tick per aircraft.

    The floating point in it is one line: the aircraft's height +0x20 moves by its attitude
    factor times its own speed-and-direction product.  Around that sit a target height
    +0x1E for three states of the player, and a floor under the target speed +0x24.
    """
    memory = Memory(entry['in'], RANGES)
    ffp = Calls(engine)
    at = aircraft_offset(entry)

    state = memory.w('aircraft', at + 0x00)
    r03 = memory.b('aircraft', at + 0x03)
    r14 = memory.sw('aircraft', at + 0x14)
    r16 = memory.sw('aircraft', at + 0x16)
    r1c = memory.sw('aircraft', at + 0x1C)
    r1e = memory.w('aircraft', at + 0x1E)
    r20 = memory.sw('aircraft', at + 0x20)
    r24 = memory.sw('aircraft', at + 0x24)
    player_c = memory.sw('player', 0x0C)

    # 0x01D796: while this aircraft is in neither of the two states of the mask 0x14 and
    # the player is in one of three states, the target height becomes 0x6A4.
    if not state & 0x14 and player_c in (4, 8, 6):
        r1e = 0x6A4

    # 0x01D7D6: height += attitude factor x (int)((direction / 100) x airspeed).
    step = s32(s16(muls_w(divs_w(r1c, 100), r14)))
    product = ffp(0x01D814, 'mul', ATTITUDE[r16], ffp(0x01D80C, 'flt', step))
    r20 = s16(r20 + u16(ffp(0x01D818, 'fix', product)))

    # 0x01D820: and the target speed gets a floor, 0x46 while the player is in state 1.
    if not state & 0x14 and not r03 & 0x04:
        if player_c == 1:
            r24 = 0x46
        if r24 < 0x21:
            r24 = 0x21

    # 0x01D96A: the countdown to a turn (+0x18) sets bit 3 of the mode at its end, and a
    # flying aircraft turning (0x01D562) takes the player's height into +0x24 while he
    # flies and it is a fighter (mode bit 0 or 1); nothing else in the turn writes the
    # three words compared here.
    mode = memory.w('aircraft', at + 0x02)
    r18 = memory.sw('aircraft', at + 0x18)
    if not state & 0x14 and r18 != 0:
        r18 -= 1
        if r18 <= 0:
            mode |= 8
    if mode & 8 and state == 2 and player_c == 0 and mode & 3:
        r24 = memory.sw('player', 0x00)

    return ffp.made, {'r1e': u16(r1e), 'r20': u16(r20), 'r24': u16(r24)}


def observed_01d796(entry):
    memory = Memory(entry['out'], RANGES)
    at = aircraft_offset(entry)
    return {'r1e': memory.w('aircraft', at + 0x1E),
            'r20': memory.w('aircraft', at + 0x20),
            'r24': memory.w('aircraft', at + 0x24)}


MODELS = {'player_motion': (model_01bdfa, observed_01bdfa),
          'aircraft_motion': (model_01d796, observed_01d796)}

# SPFix, SPFlt and SPNeg read D0 only, so what the caller happens to have left in D1 is not
# part of the call and is not compared.
BINARY = ('add', 'sub', 'mul', 'div', 'cmp')


def call_key(call):
    site, operation, d0, d1, result = call[0], call[1], call[2], call[3], call[4]
    return (site, operation, d0 & 0xFFFFFFFF,
            d1 & 0xFFFFFFFF if operation in BINARY else None,
            result & 0xFFFFFFFF if result is not None else None)
