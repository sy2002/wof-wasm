"""M8 part 1 differential tests: the sound effects engine against the original (SPEC 7.4,
re/notes/sound.md, re/notes/porting-m8.md).

Each routine runs twice on the same randomised state, once as the original's 68000 code
under the oracle and once as the port's C (src/sound.c), and every registered global and
table the two touched is compared - the eight slots, the four channel records, the sample
pointers, the engine's counters and flags - with Paula beside them: the custom chips'
audio registers are watched on the oracle's side by the model of the headless original
(tools/headless_paula.py) and compared with the port's model (src/audio.c) register by
register, with the channels' DMA, INTENA and INTREQ.  The sample pointers of the original
are eight made-up addresses, one per sound file, which the comparison turns into the port's
handles as it does in the mission runs (tests/m4state.py).
"""
import ctypes
import os
import random
import struct
import sys

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, 'tools'))
sys.path.insert(0, HERE)

from unicorn import UC_HOOK_MEM_WRITE                       # noqa: E402
from unicorn.m68k_const import UC_M68K_REG_A7, UC_M68K_REG_A4, UC_M68K_REG_SR   # noqa: E402

import headless_paula                                       # noqa: E402
import m4state                                              # noqa: E402
from test_oracle_m4 import Differential, w                  # noqa: E402

SLOTS, CHANNELS = 0x027368, 0x027E6E
PLAYER = 0x025078
AIRCRAFT = 0x02522A
SOUND_LENGTH = 0x025572
SYSBASE = 0x026F74
AUDIO_IRQ, AUDIO_IRQ_RTE = 0x01EBAA, 0x01EC62

# Where the made-up samples lie in the oracle's memory, by sound file (sound_files' order),
# and the pointer sounds_load keeps to each (tests/m4state.py, SOUND_POINTERS).
SAMPLE_BASE = 0x180000
POINTER_OF = {index: where for where, index in m4state.SOUND_POINTERS.items()}


class Machine:
    """What tools/headless_paula.py asks of the headless original, for a lone oracle."""

    def __init__(self, o):
        self.o = o
        self.vblanks = self.passes = self.ticks = self.in_vblank = self.depth = 0
        self.alloc_sizes, self.alloc_labels = {}, {}


class SoundDifferential(Differential):
    def __init__(self, ported):
        super().__init__(ported)
        o = self.o
        o.uc.mem_map(headless_paula.CUSTOM, 0x1000)
        self.paula = headless_paula.Paula(Machine(o), 50)
        o.uc.hook_add(UC_HOOK_MEM_WRITE,
                      lambda uc, access, address, size, value, user:
                      self.paula.write(address, size, value),
                      begin=headless_paula.CUSTOM + headless_paula.DMACON,
                      end=headless_paula.CUSTOM + 0x0DF)
        self.samples = [SAMPLE_BASE + 0x8000 * i for i in range(8)]
        for index, where in POINTER_OF.items():
            o.w32(where, self.samples[index])
        # exec's AddIntServer, for sound_init: an rts at its offset from a made-up SysBase
        base = o.alloc(0x200) + 0x100
        o.write(base - 0xA8, bytes.fromhex('4E75'))
        o.w32(SYSBASE, base)
        lib = ported.lib
        lib.wof_test_m8_call.argtypes = [ctypes.c_uint32] + [ctypes.c_int32] * 6 + [
            ctypes.POINTER(ctypes.c_int32)]
        lib.wof_test_m8_call.restype = ctypes.c_int32
        lib.wt_paula_put.argtypes = [ctypes.c_void_p]
        lib.wt_paula_state.argtypes = [ctypes.c_void_p]

    # ------------------------------------------------------------------ the two sides

    def m8(self, orig, d0=0, d1=0, d2=0, d3=0, d4=0, a0=0):
        out = (ctypes.c_int32 * 2)()
        assert self.ported.lib.wof_test_m8_call(orig, d0, d1, d2, d3, d4, a0, out) == 0, hex(orig)
        return out[0] & 0xFFFF, out[1] & 0xFFFF

    def handle(self, pointer):
        h = m4state.sound_handle(self.memory(), pointer)
        return 0xFFFFFFFF if h is None else h

    def paula_words(self):
        """The oracle side's model in the port's 39 words (tests/shim.c, wt_paula_put)."""
        out = []
        for ch in self.paula.ch:
            out += [self.handle(ch.lc), ch.len, ch.per, ch.vol, int(ch.on), self.handle(ch.ptr),
                    ch.left, ch.next & 0xFFFFFFFF, ch.next >> 32]
        return out + [self.paula.intena, self.paula.intreq, self.paula.m.vblanks]

    def load_port(self):
        super().load_port()
        self.ported.lib.wt_paula_put((ctypes.c_uint32 * 39)(*self.paula_words()))

    def differences(self):
        found = super().differences()
        got = (ctypes.c_uint32 * 39)()
        self.ported.lib.wt_paula_state(got)
        want = self.paula_words()
        names = ['lc', 'len', 'per', 'vol', 'on', 'ptr', 'left', 'next', 'next_hi']
        for i in range(36):
            if got[i] != want[i]:
                found.append(('paula channel %d %s' % (i // 9, names[i % 9]), got[i], want[i]))
        for i, name in ((36, 'intena'), (37, 'intreq')):
            if got[i] != want[i]:
                found.append(('paula ' + name, got[i], want[i]))
        return found

    # ------------------------------------------------------------------ random states

    def sample(self, rng):
        first = 1 if getattr(self, 'no_boom', False) else 0
        return self.samples[rng.randrange(first, 8)] + rng.choice([0, 0, 0, 2 * rng.randrange(0x100)])

    def randomise(self, rng):
        o = self.o
        for i in range(8):
            at = SLOTS + 0x18 * i
            w(o, at + 0x00, rng.choice([0, 0, 0xFF00, 0xFFFF, rng.randrange(0x10000)]))
            o.w32(at + 0x02, rng.choice([0, self.sample(rng), self.sample(rng)]))
            o.w32(at + 0x06, rng.choice([rng.randrange(0x4000), rng.randrange(1 << 32)]))
            w(o, at + 0x0A, rng.choice([0x7C, 0x17C, 0x328, rng.randrange(0x10000)]))
            w(o, at + 0x0C, rng.choice([0, 0x22, 0x40, rng.randrange(0x41), rng.randrange(0x10000)]))
            w(o, at + 0x0E, rng.choice([0xFFFF, 1, 0, 2, rng.randrange(0x10000)]))
            o.w32(at + 0x10, rng.choice([0, 0, self.sample(rng)]))
            o.w32(at + 0x14, rng.choice([0, rng.randrange(1 << 32)]))
        vblanks = rng.choice([rng.randrange(0x100), rng.randrange(1 << 32)])
        o.w32(0x027E6A, vblanks)
        for c in range(4):
            at = CHANNELS + 0x1E * c
            o.w32(at + 0x00, rng.choice([0, self.sample(rng)]))
            o.w32(at + 0x04, (vblanks - rng.choice([0, 1, 2, 3, rng.randrange(1 << 32)])) & 0xFFFFFFFF)
            w(o, at + 0x08, rng.choice([0, 0, 1, rng.randrange(0x10000)]))
            w(o, at + 0x0A, rng.randrange(0x10000))
            w(o, at + 0x0C, rng.randrange(0x10000))
            o.w32(at + 0x0E, rng.choice([0x400000, rng.randrange(0x410000), rng.randrange(1 << 32)]))
            w(o, at + 0x12, rng.choice([0xFFFF, 1, 0, rng.randrange(0x10000)]))
            w(o, at + 0x14, rng.choice([0xFFFF, 1, 0, rng.randrange(0x10000)]))
            o.w32(at + 0x16, rng.choice([0xFFFFFFFF, 0xFFFFFFFF, rng.randrange(0x410000),
                                         rng.randrange(1 << 32)]))
            o.w32(at + 0x1A, rng.choice([0x10000, rng.randrange(0x40000), rng.randrange(1 << 32)]))
        o.write(0x025556, bytes([rng.choice([0, 0, 0, 0xFF])]))       # pause_flag
        o.write(0x0254F7, bytes([rng.choice([0, 0, 0, 0xFF])]))       # opt_music_off
        o.write(0x027F14, bytes([rng.choice([0, 0xFF]), rng.choice([0, 0, 0xFF]),
                                 rng.choice([0, 0xFF]), 0]))
        w(o, 0x027F18, 0)                                            # nothing writes it
        o.w32(0x027F1A, rng.randrange(1 << 32))
        for i in range(8):
            o.w32(SOUND_LENGTH + 4 * i, rng.choice([rng.randrange(0x4000), rng.randrange(1 << 32)]))
        # Paula: which channels run, their registers, the interrupt bits
        p = self.paula
        p.m.vblanks = 0
        for ch in p.ch:
            ch.on = rng.random() < 0.5
            ch.lc = self.sample(rng)
            ch.len, ch.per = rng.randrange(0x10000), rng.randrange(0x10000)
            ch.vol = rng.randrange(0x41)
            ch.ptr, ch.left, ch.next = ch.lc, headless_paula.cycle_bytes(ch.len), 0
        p.intena = 0x4000 | rng.randrange(0x10000) & 0x3FFF
        p.intreq = rng.randrange(0x4000)
        p._publish()

    def randomise_engine(self, rng):
        """engine_sound's inputs beside the slots: the engine's eased values, the pitch and
        the height, the guns, the four enemy aircraft, the lift's state and the ground's
        guns."""
        o = self.o
        self.randomise(rng)
        for at in (0x02542C, 0x025428, 0x02542E, 0x02542A):
            w(o, at, rng.choice([0, 1, 2, 0x28, 0x328, rng.randrange(0x400), rng.randrange(0x10000)]))
        w(o, 0x025402, rng.randrange(0x10000))                        # pitch_target
        px = rng.randrange(0x10000)
        w(o, PLAYER + 0x02, px)
        w(o, PLAYER + 0x00, rng.choice([rng.randrange(0x100), rng.randrange(0x10000)]))
        w(o, 0x02536A, rng.choice([0, 0, 0xFFFF, rng.randrange(0x10000)]))   # guns_firing
        for i in range(4):
            at = AIRCRAFT + 0x34 * i
            w(o, at + 0x00, rng.choice([0, 1, 2, 2, 4, 0x10, rng.randrange(0x10000)]))
            w(o, at + 0x12, rng.choice([0, 0, 1, rng.randrange(0x10000)]))
            w(o, at + 0x20, (px + rng.choice([rng.randrange(-0x400, 0x400),
                                              rng.randrange(0x10000)])) & 0xFFFF)
            w(o, at + 0x26, rng.randrange(0x10000))
        w(o, 0x025394, rng.choice([0, 1, 2, 3, 4, rng.randrange(0x10000)]))
        w(o, 0x027164, rng.choice([0, 0, 0xFF00, rng.randrange(0x10000)]))
        w(o, 0x027166, rng.randrange(0x10000))


@pytest.fixture
def sound(ported):
    d = SoundDifferential(ported)
    yield d
    d.restore()


def check(d, what):
    found = d.differences()
    assert found == [], '%s: %s' % (what, found[:6])


def run_until(o, begin, until):
    """A handler that ends with rte, run from its first instruction up to its rte."""
    o.uc.reg_write(UC_M68K_REG_SR, 0x2000)
    o.uc.reg_write(UC_M68K_REG_A7, 0x0FE000)
    o.uc.reg_write(UC_M68K_REG_A4, 0x02AFFE)
    o.uc.emu_start(begin, until, count=100000)


# ------------------------------------------------------------------------ the loudness

def test_the_loudness_by_distance_matches_the_original(sound):
    """0x0122CE, an enemy aircraft's loudness, and 0x0122F6, the one of a burst, a splash or
    a scream, for every distance; 0x012306, the distance from the aircraft to world x at
    height 0x14 and its loudness, D0 and D1 as it leaves them, over random positions."""
    d = sound
    for d0 in range(0x10000):
        want = d.o.call(0x0122CE, regs={'d0': d0}) & 0xFFFF
        assert d.m8(0x0122CE, d0)[0] == want, 'd0 %04X' % d0
        want = d.o.call(0x0122F6, regs={'d0': d0}) & 0xFFFF
        assert d.m8(0x0122F6, d0)[0] == want, 'd0 %04X' % d0
    rng = random.Random(0x12306)
    for n in range(3000):
        w(d.o, PLAYER + 0x02, rng.randrange(0x10000))
        w(d.o, PLAYER + 0x00, rng.choice([rng.randrange(0x100), rng.randrange(0x10000)]))
        x = rng.randrange(0x10000)
        d.load_port()
        d.o.call(0x012306, regs={'d0': x, 'd1': rng.randrange(1 << 32)})
        want = (d.o.reg('d0') & 0xFFFF, d.o.reg('d1') & 0xFFFF)
        assert d.m8(0x012306, x) == want, 'case %d' % n


# ------------------------------------------------------------------------ the slots

def test_engine_sound_matches_the_original(sound):
    """0x012132 over random states: the volume and the period eased, the guns, the nearest
    enemy aircraft that flies and any that fires, the lift, the carrier, the ground's guns,
    paused and with the music off; every slot and both eased values compared."""
    d = sound
    rng = random.Random(0x12132)
    for n in range(3000):
        d.randomise_engine(rng)
        d.load_port()
        d.o.call(0x012132)
        d.m8(0x012132)
        check(d, 'case %d' % n)


@pytest.mark.parametrize('orig', [0x011F76, 0x012324, 0x01233E, 0x012354, 0x012380, 0x0123AC])
def test_the_slot_setters_match_the_original(sound, orig):
    """sub_011f76, which builds slots 0 to 6 from the pointers and the lengths, and the
    one-shots the tick and the pass start: a burst (none before its sound is loaded), a
    splash, the lift's clang, the touch-down's screech and a soldier's scream, with D0 and
    D1 as the burst and the scream leave them."""
    d = sound
    rng = random.Random(orig)
    for n in range(1000):
        d.no_boom = orig == 0x012324 and rng.random() < 0.3
        d.randomise_engine(rng)
        if d.no_boom:
            d.o.w32(0x026E3E, 0)                                     # no burst loaded
        x, d1 = rng.randrange(0x10000), rng.randrange(0x10000)
        d.load_port()
        d.o.call(orig, regs={'d0': x, 'd1': d1})
        want = (d.o.reg('d0') & 0xFFFF, d.o.reg('d1') & 0xFFFF)
        got = d.m8(orig, x, d1)
        if orig in (0x012324, 0x0123AC):
            assert got[0] == want[0], 'case %d: d0 port %04X original %04X' % (n, got[0], want[0])
        if orig == 0x0123AC:
            assert got[1] == want[1], 'case %d: d1 port %04X original %04X' % (n, got[1], want[1])
        check(d, 'case %d' % n)
        d.no_boom = False
        d.o.w32(0x026E3E, d.samples[0])                              # the pointer back


# ------------------------------------------------------------------------ the channels

def test_sound_channels_matches_the_original(sound):
    """0x012066 and 0x011F4E over random slot tables and channel records: the first slot of
    each pair that is on, the same sample adjusted or another started three times over, a
    channel with nothing to play stopped three times over, paused and with the music off;
    the slots, the records and Paula compared."""
    d = sound
    rng = random.Random(0x12066)
    for n in range(3000):
        d.randomise(rng)
        orig = rng.choice([0x012066, 0x012066, 0x011F4E])
        d.load_port()
        d.o.call(orig)
        d.m8(orig)
        check(d, 'case %d (%06X)' % (n, orig))


def test_the_channel_routines_match_the_original(sound):
    """0x01EA28, a sample for a channel with the busy one stopped first; 0x01EAC0, a channel
    stopped; 0x01EB4C, a channel's period and volume, either left alone when negative.  The
    channel number of 0x01EA28 is taken as the original takes it, its low two bits, except 6,
    which hands channel 2 to the music and is a stand-in in the port."""
    d = sound
    rng = random.Random(0x1EA28)
    for n in range(3000):
        d.randomise(rng)
        which = rng.choice([0x01EA28, 0x01EAC0, 0x01EB4C])
        regs = {'d0': rng.choice([rng.randrange(0x8000), rng.randrange(1 << 32)]),
                'd1': rng.choice([0, 1, 2, 3, 4, 5, 7, rng.randrange(0x10000)]),
                'd2': rng.randrange(1 << 32), 'd3': rng.randrange(1 << 32),
                'd4': rng.randrange(1 << 32),
                'a0': rng.choice([0, d.sample(rng), d.sample(rng)])}
        if which == 0x01EA28 and regs['d1'] & 0xFFFF == 6:
            regs['d1'] = 2
        if which != 0x01EA28:
            regs['d0'] = rng.choice([0, 1, 2, 3])
        d.load_port()
        d.o.call(which, regs=regs)
        if which == 0x01EA28:
            d.m8(which, regs['d0'], regs['d1'], regs['d2'], regs['d3'], regs['d4'],
                 d.handle(regs['a0']) if regs['a0'] else 0)
        elif which == 0x01EAC0:
            d.m8(which, regs['d0'])
        else:
            d.m8(which, regs['d0'], regs['d1'], regs['d2'])
        check(d, 'case %d (%06X, %r)' % (n, which, regs))


def test_audio_irq_matches_the_original(sound):
    """0x01EBAA, the level-4 handler, over random channel records and interrupt bits: a free
    record or a count that runs out stops its channel (and switches off the interrupts of
    every channel it handled before), a count below zero plays on, the requests it saw are
    cleared, and the long 0x027F1A goes to 0x026218."""
    d = sound
    rng = random.Random(0x1EBAA)
    for n in range(3000):
        d.randomise(rng)
        d.paula.intena |= 0x4000
        d.paula.intreq = rng.choice([0x80, 0x100, 0x200, 0x400, rng.randrange(0x800) & 0x780,
                                     rng.randrange(0x4000)])
        d.paula._publish()
        d.load_port()
        run_until(d.o, AUDIO_IRQ, AUDIO_IRQ_RTE)
        d.m8(AUDIO_IRQ)
        check(d, 'case %d' % n)


def test_soundfx_vblank_matches_the_original(sound):
    """0x01EC64, the engine's VBlank server, over random records: a channel waiting two
    VBlanks after it stopped, started with the others at the end; the music's flags for
    channel 2; and a volume eased up or down to its target, which only the uncalled 0x01EB94
    sets."""
    d = sound
    rng = random.Random(0x1EC64)
    for n in range(3000):
        d.randomise(rng)
        d.load_port()
        d.o.call(0x01EC64, regs={'a6': headless_paula.CUSTOM})
        d.m8(0x01EC64)
        check(d, 'case %d' % n)


def test_sound_init_matches_the_original(sound):
    """0x01E8B8, once and a second time, which does nothing: the records free, every audio
    interrupt and channel off, the requests cleared, the four interrupts on."""
    d = sound
    rng = random.Random(0x1E8B8)
    for n in range(200):
        d.randomise(rng)
        w(d.o, 0x027E68, rng.choice([0, 0, 1]))
        d.load_port()
        d.o.call(0x01E8B8)
        d.m8(0x01E8B8)
        check(d, 'case %d' % n)
