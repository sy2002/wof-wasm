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

from unicorn import UC_HOOK_BLOCK, UC_HOOK_MEM_WRITE        # noqa: E402
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
        got = (ctypes.c_uint32 * 48)()
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


# ======================================================================== the music player
#
# M8 part 2 (re/notes/music.md): the player's routines against songplay's own code.  The
# oracle gets both files as LoadSeg lays them out - every hunk with its size and link in
# front, relocated - and the game's four pointers to them, so that tests/m4state.py finds
# the player's DATA hunk and the song data as it does in the headless original's runs.  A
# state is random but real: every track's sequence, pattern position and voice are the song
# data's own, the voices' samples those _ReadInstruments found, with random vibrato and
# arpeggio; the song data is otherwise as the file has it on both sides, because the port
# reads it from the file.

import hunk                                                 # noqa: E402
import song_decode                                          # noqa: E402

PLAYER_SEGLIST, PLAYER_ENTRY = 0x0255EA, 0x0255EE
SONGS_SEGLIST, SONG_DATA = 0x027428, 0x02742C
TRACK0, TRACK_SIZE, VOICES, VOICE_SIZE = 0x2AA, 0x4A, 0xCC, 0x2E


def signed16(v):
    return v & 0xFFFF


class MusicDifferential(SoundDifferential):
    """`songs`, when given, is a variant of wofsongs laid over the disk on both sides."""

    def __init__(self, ported, songs=None):
        super().__init__(ported)
        self.blob = ported.blob
        original = open(song_decode.SONGS, 'rb').read()
        if songs is not None:               # the variant in the file system blob's copy of it
            at = ported.blob.find(original)
            assert at > 0 and ported.blob.find(original, at + 1) < 0
            ported.blob = ported.blob[:at] + songs + ported.blob[at + len(songs):]
        ported.reset_core()                 # the port's song data taken afresh from its disk
        ported.lib.wof_set_video_hz(50)     # the oracle's model's rate: the timer counts in it
        self.songs_raw = songs if songs is not None else original
        o = self.o
        o.uc.mem_map(0xBFD000, 0x2000)
        o.uc.hook_add(UC_HOOK_MEM_WRITE,
                      lambda uc, access, address, size, value, user:
                      self.paula.timer.write(address, value & 0xFF),
                      begin=headless_paula.CIAA_TALO, end=headless_paula.CIAA_CRA)
        self.player = self.load_segment(open(song_decode.PLAYER, 'rb').read())
        self.songs = self.load_segment(self.songs_raw)
        o.w32(PLAYER_SEGLIST, (self.player[0][0] + 4) >> 2)
        o.w32(PLAYER_ENTRY, self.player[0][1])
        o.w32(SONGS_SEGLIST, (self.songs[0][0] + 4) >> 2)
        o.w32(SONG_DATA, self.songs[1][1])
        self.code, self.data, self.sdata = self.player[0][1], self.player[1][1], self.songs[1][1]
        self.ran = set()                    # the player's CODE offsets the original executed
        o.uc.hook_add(UC_HOOK_BLOCK,
                      lambda uc, address, size, user:
                      self.ran.update(range(address - self.code, address - self.code + size)),
                      begin=self.code, end=self.code + self.player[0][2] - 1)
        self.pristine = (o.read(self.data, self.player[1][2]), o.read(self.sdata, self.songs[1][2]))
        self.decoded = song_decode.Songs(self.songs_raw)
        m4state.SEEN_SONGS.clear()
        m4state.SEEN_SAMPLES.clear()
        lib = ported.lib
        lib.wof_test_songplay_call.argtypes = [ctypes.c_uint32] + [ctypes.c_int32] * 3 + [
            ctypes.POINTER(ctypes.c_int32)]
        lib.wof_test_songplay_call.restype = ctypes.c_int32
        lib.wt_timer_put.argtypes = [ctypes.c_void_p]

    def restore(self):
        super().restore()
        self.ported.blob = self.blob
        self.ported.reset_core()            # and the port's own song data again

    def load_segment(self, raw):
        """The hunks of a file as LoadSeg leaves them: (base, first byte, size) of each."""
        sizes = [len(h['data']) for h in hunk.load(raw)]
        bases = [self.o.alloc(size + 8) for size in sizes]
        hunks = hunk.load(raw, bases=[b + 8 for b in bases])
        for i, (base, h) in enumerate(zip(bases, hunks)):
            self.o.w32(base, len(h['data']) + 8)
            self.o.w32(base + 4, (bases[i + 1] + 4) >> 2 if i + 1 < len(bases) else 0)
            self.o.write(base + 8, bytes(h['data']))
        return [(b, b + 8, len(h['data'])) for b, h in zip(bases, hunks)]

    def memory(self):
        regions = {0x023000: bytes(self.o.read(0x023000, 0x028004 - 0x023000))}
        for base, first, size in self.player + self.songs:
            regions[base] = bytes(self.o.read(base, size + 8))
        return m4state.Memory(regions)

    # ------------------------------------------------------------------ both sides

    def timer_words(self):
        tm = self.paula.timer
        nxt = tm.next if tm.running and tm.next is not None else 0
        return [tm.latch, tm.counter, int(tm.running), int(tm.oneshot), nxt & 0xFFFFFFFF,
                nxt >> 32, int(tm.vector is not None), 0, 0]

    def load_port(self):
        super().load_port()
        self.ported.lib.wt_timer_put((ctypes.c_uint32 * 9)(*self.timer_words()))

    def differences(self):
        found = super().differences()
        got = self.ported.paula_state()[39:45]
        for name, a, b in zip(('latch', 'counter', 'running', 'one-shot', 'next', 'next_hi'),
                              got, self.timer_words()[:6]):
            if a != b:
                found.append(('timer ' + name, a, b))
        return found

    def songplay(self, offset, t=0, d1=0, d2=0):
        out = (ctypes.c_int32 * 1)()
        assert self.ported.lib.wof_test_songplay_call(offset, t, d1, d2, out) == 0, hex(offset)
        return out[0] & 0xFFFF

    def track(self, t):
        return self.data + TRACK0 + TRACK_SIZE * t

    def assert_ran(self, *regions):
        """Every region (first, last offset) the cases were to reach, reached by them: the
        regions no run of the game executes (tools/reach_observe.py --cold)."""
        missed = ['%04x-%04x' % (lo, hi) for lo, hi in regions if lo not in self.ran or hi not in self.ran]
        assert not missed, 'the cases never ran %s' % missed

    def with_sample(self, t):
        """Track t's VHDR as its voice has it: note_period is only ever reached with one."""
        tr = self.track(t)
        if not self.o.r32(tr + 0x14):
            self.o.w32(tr + 0x14, self.o.r32(self.o.r32(tr + 0x3C)))

    def voice(self, n):
        return self.sdata + VOICES + VOICE_SIZE * n

    # ------------------------------------------------------------------ a random state

    def randomise_music(self, rng, t=0):
        o, dec, sd = self.o, self.decoded, self.sdata
        o.write(self.data, self.pristine[0])
        o.write(self.sdata, self.pristine[1])
        song = rng.randrange(5)
        o.call(self.code, regs={'d0': 1, 'd1': song, 'd2': sd})            # _ReadInstruments
        sounding = [n for n in range(7) if o.r32(self.voice(n))]
        for n in range(7):
            v = self.voice(n)
            w(o, v + 0x12, rng.choice([rng.randrange(0x40), rng.randrange(0x10000)]))   # vib_hi
            w(o, v + 0x14, rng.choice([rng.randrange(0x40), rng.randrange(0x10000)]))   # vib_lo
            w(o, v + 0x16, rng.choice([rng.randrange(-8, 9), rng.randrange(0x10000)]))
            w(o, v + 0x18, rng.choice([1, 2, rng.randrange(8), rng.randrange(0x10000)]))
            w(o, v + 0x1A, rng.choice([1, 3, rng.randrange(8)]))
            w(o, v + 0x1C, rng.choice([0, 1, 2, rng.randrange(-2, 8), rng.randrange(0x10000)]))
            w(o, v + 0x1E, rng.choice([0, 0, 1]) if n in sounding else 0)          # vibrato
            w(o, v + 0x22, rng.choice([0, 0, 1]) if n in sounding else 0)          # arpeggio
            for k in range(4):
                w(o, v + 0x24 + 2 * k, rng.randrange(-12, 13))
            w(o, v + 0x2C, rng.randrange(0x10000))
        songs = dec.songs()
        at = self.data + 0x27C
        w(o, at + 0x00, rng.choice([0, 1, 2, 2, 3, 4, 4]))                       # PlayState
        o.w32(at + 0x02, rng.choice([0, 0x01000000 << rng.randrange(4), rng.randrange(1 << 32)]))
        w(o, at + 0x06, rng.choice([0, 0, 0, 0x100 << rng.randrange(4), rng.randrange(0x10000)]))
        w(o, at + 0x08, rng.randrange(0x10000))                                  # SfxMusicVol
        o.w32(at + 0x0A, sd + rng.choice(songs))                                  # SongAddr
        w(o, at + 0x0E, rng.choice([0xFFFF, 0, 1, 2, rng.randrange(0x10000)]))  # FadeCount
        w(o, at + 0x10, rng.choice([0, 1, 2, rng.randrange(0x10000)]))          # FadeSpeed
        w(o, at + 0x12, rng.choice([0, 0, 0, 0, 1]))                             # Paused
        o.w32(self.data + 0x3D2, sd + songs[song])
        o.w32(self.data + 0x3D6, sd + songs[song] + 0x10)
        w(o, self.data + 0x000, 0x8000 | 1 << t)
        w(o, self.data + 0x002, 1 << t)
        w(o, self.data + 0x004, 0x8000 | 0x80 << t)
        w(o, self.data + 0x006, t)
        for k in range(4):
            self.randomise_track(rng, k, sounding)
        p = self.paula
        p.m.vblanks = 0
        for ch in p.ch:
            ch.on = rng.random() < 0.5
            ch.lc = sd + 2 * rng.randrange(self.songs[1][2] // 2)
            ch.len, ch.per = rng.randrange(0x10000), rng.randrange(0x10000)
            ch.vol = rng.randrange(0x41)
            ch.ptr, ch.left, ch.next = ch.lc, headless_paula.cycle_bytes(ch.len), 0
        p.intena = 0x4000 | rng.randrange(0x10000) & 0x3FFF
        p.intreq = rng.randrange(0x4000)
        p._publish()
        tm = p.timer
        tm.latch = rng.choice([0xFFFF, 0x38FF, 0x3CFF, rng.randrange(0x10000)])
        tm.counter = rng.randrange(0x10000)
        tm.running, tm.oneshot = rng.random() < 0.7, rng.random() < 0.2
        tm.next = rng.randrange(1, 1 << 30) if tm.running else None
        tm.vector = None

    def randomise_track(self, rng, t, sounding):
        o, dec, sd = self.o, self.decoded, self.sdata
        tr = self.track(t)
        song = rng.choice(dec.songs())
        seq = rng.choice(dec.tracks(song))
        entries = dec.sequence(seq)
        k = rng.randrange(len(entries))
        pattern = entries[k][0]
        events = dec.pattern(pattern)
        voice = rng.choice(sounding)
        v = self.voice(voice)
        w(o, tr + 0x00, rng.choice([0, 0xFFFF, 0xFFFF, 1]))                     # active
        o.w32(tr + 0x02, sd + seq)
        o.w32(tr + 0x06, sd + pattern + 2 * rng.randrange(len(events)))
        o.w32(tr + 0x0A, 6 * k)
        dur = rng.choice([0, 0, 1, 2, rng.randrange(1, 97)])
        w(o, tr + 0x0E, dur)
        w(o, tr + 0x10, rng.choice([dur - 1, rng.randrange(97), 0]))            # release
        w(o, tr + 0x12, rng.choice([0xFFFF, 0, 1, 1, rng.randrange(0x10000)]))  # irq
        no_sample = not o.r16(v + 0x22) and rng.random() < 0.1
        o.w32(tr + 0x14, 0 if no_sample else o.r32(v))                         # vhdr
        o.w32(tr + 0x18, o.r32(v + 4))                                          # body
        w(o, tr + 0x1C, o.r16(v + 8))                                           # octave_div
        w(o, tr + 0x1E, rng.choice([0, 1, 0x20, rng.randrange(0x41), rng.randrange(0x10000)]))
        w(o, tr + 0x20, rng.choice([0x7C, rng.randrange(0x7C, 0x400), rng.randrange(0x10000)]))
        w(o, tr + 0x22, rng.choice([0, rng.randrange(0x10000)]))                # loop_words
        o.w32(tr + 0x24, sd + 2 * rng.randrange(self.songs[1][2] // 2))        # loop_start
        w(o, tr + 0x38, rng.choice([0, 0, 1, 2]))                               # hold
        w(o, tr + 0x3A, rng.choice([0, 0, 1, 2, 3]))                            # tie
        o.w32(tr + 0x3C, v)
        w(o, tr + 0x40, rng.randrange(12, 87))                                  # note
        w(o, tr + 0x42, rng.choice([0x7C, rng.randrange(0x7C, 0x400), rng.randrange(0x10000)]))
        w(o, tr + 0x44, rng.choice([rng.randrange(-8, 9), rng.randrange(0x10000)]))
        w(o, tr + 0x46, rng.choice([0, 0, 0, 0, 1]))                            # sfx
        w(o, tr + 0x48, rng.choice([0xFFFF, 0, 1, 3]))                          # sfx_count


@pytest.fixture
def music(ported):
    d = MusicDifferential(ported)
    yield d
    d.restore()


def music_case(d, rng, offset, n, regs=None, port=()):
    """One call on both sides from the same state: the original's routine at songplay +
    `offset`, the port's by the same offset; the state, Paula and the timer compared."""
    d.load_port()
    d.o.call(d.code + offset, regs=regs or {})
    d.songplay(offset, *port)
    check(d, 'case %d (+%04X, %r)' % (n, offset, regs))


@pytest.mark.parametrize('t', [0, 1, 2, 3])
def test_track_step_matches_the_original(music, t):
    """songplay+0x04F4 over random tracks: a note's time, its release (held, tied, an
    effect's channel), arpeggio and vibrato between their limits, and at a note's end the
    pattern's next events up to the next note, which starts."""
    d = music
    rng = random.Random(0x4F4 + t)
    for n in range(1500):
        d.randomise_music(rng, t)
        music_case(d, rng, 0x04F4, n, {'a3': d.track(t), 'd3': rng.randrange(1 << 32)}, (t,))
    d.assert_ran((0x050E, 0x051C), (0x0538, 0x0542), (0x054E, 0x0596))  # arpeggio, vibrato


def test_track_read_and_note_start_match_the_original(music):
    """songplay+0x05D2, the pattern's next events with D3 added to the note, and +0x0704, a
    note with each of the twenty lengths: tie, sample, period, AUDxLC and AUDxLEN, the loop
    part, the volume scaled while an effect plays, the track's bit of TrackState."""
    d = music
    rng = random.Random(0x5D2)
    for n in range(2000):
        t = rng.randrange(4)
        d.randomise_music(rng, t)
        if rng.random() < 0.5:
            d3 = rng.randrange(-12, 13) & 0xFFFF
            music_case(d, rng, 0x05D2, n, {'a3': d.track(t), 'd3': d3}, (t, d3))
        else:
            note, length = rng.randrange(12, 87), rng.randrange(20)
            music_case(d, rng, 0x0704, n, {'a3': d.track(t), 'd1': note, 'd2': length},
                       (t, note, length))
    d.assert_ran((0x066A, 0x067E), (0x07B0, 0x07BE))     # the sequence again; an effect's volume


def test_the_note_lookup_matches_the_original(music):
    """songplay+0x07EA, a note's octave and period, for every note the tables reach on every
    voice with a sample: the period into the channel and the track, D3 the octave."""
    d = music
    rng = random.Random(0x7EA)
    n = 0
    for note in range(0, 99):
        for repeat in range(8):
            t = rng.randrange(4)
            d.randomise_music(rng, t)
            d.with_sample(t)
            d.load_port()
            d.o.call(d.code + 0x07EA, regs={'a3': d.track(t), 'd1': note})
            want = d.o.reg('d3') & 0xFFFF
            got = d.songplay(0x07EA, t, note)
            assert got == want, 'note %d: octave port %d original %d' % (note, got, want)
            check(d, 'note %d case %d' % (note, n))
            n += 1
    d.assert_ran((0x0808, 0x0808))                       # a note above the sample's octaves


def test_the_instrument_lookup_matches_the_original(music):
    """Command 1, _ReadInstruments (songplay+0x0946), for each of the five songs from the
    voices as the file has them and from voices another song already read: the song, its
    voice table, every voice's VHDR, BODY and notes per octave."""
    d = music
    rng = random.Random(0x946)
    for n in range(100):
        d.randomise_music(rng)
        if rng.random() < 0.5:
            d.o.write(d.sdata, d.pristine[1])
        song = rng.randrange(5)
        d.load_port()
        d.o.call(d.code, regs={'d0': 1, 'd1': song, 'd2': d.sdata})
        d.songplay(0x0000, 0, song, 1)
        check(d, 'case %d, song %d' % (n, song))


def test_the_tick_and_the_fade_match_the_original(music):
    """SongInt (songplay+0x02A6) in every PlayState - a song begun, played, stopped, faded
    a step every FadeSpeed + 1 ticks and stopped with no volume left - paused and not; and
    the commands the game gives beside it: 2 PlaySong, 5 GetSongStat, 6 FadeSong."""
    d = music
    rng = random.Random(0x2A6)
    for n in range(3000):
        d.randomise_music(rng, rng.randrange(4))
        which = rng.choice(['tick', 'tick', 'tick', 2, 5, 6])
        if which == 'tick':
            music_case(d, rng, 0x02A6, n)
            continue
        speed = rng.choice([0, 1, 2, rng.randrange(0x10000)])
        if which == 6:
            w(d.o, d.data + 0x27C + 0x12, 0)     # Paused: only command 10 sets it, never given
        d.load_port()
        d.o.call(d.code, regs={'d0': which, 'd1': speed})
        want = d.o.reg('d0') & 0xFFFF
        got = d.songplay(0x0000, 0, speed, which)
        if which == 5:
            assert got == want, 'case %d: GetSongStat port %d original %d' % (n, got, want)
        check(d, 'case %d, command %d' % (n, which))
    d.assert_ran((0x04CC, 0x04D6))                       # a song no track started a note of


def test_the_players_level4_handler_matches_the_original(music):
    """SongIntHandler (songplay+0x0848) over random tracks and requests: at a note's first
    interrupt its loop part, or the channel marked to go off, or off; an effect's channel
    counting its repeats; every channel's request cleared."""
    d = music
    rng = random.Random(0x848)
    for n in range(3000):
        d.randomise_music(rng, rng.randrange(4))
        d.paula.intena |= 0x4000
        d.paula.intreq = rng.choice([0x80, 0x100, 0x200, 0x400, rng.randrange(0x800) & 0x780,
                                     rng.randrange(0x4000)])
        d.paula._publish()
        d.load_port()
        run_until(d.o, d.code + 0x0848, d.code + 0x08AC)
        d.songplay(0x0848)
        check(d, 'case %d' % n)
    d.assert_ran((0x0916, 0x0928))                       # an effect's channel


# A variant of wofsongs, of the file's length, with what no song of the disk has: in song 1's patterns a latch low
# byte (0xDE), a hold (0xE0), a command byte the player passes over (0xE5), a track's end
# (0xDA) and notes tied to the ones before; and BassDrum3 with three octaves, so that a note
# plays in a lower octave's part of the sample.  Only bytes that are no pointer change.

def variant_songs():
    raw = bytearray(open(song_decode.SONGS, 'rb').read())
    base = hunk.load(bytes(raw))[1]['file_off']
    dec = song_decode.Songs()
    tracks = dec.tracks(dec.songs()[1])
    first = [dec.sequence(seq)[0][0] for seq in tracks]
    commands = [(0xDE, 0x80), (0xE0, 1), (0xE5, 7), (0xE0, 0)]
    for k, (command, argument) in enumerate(commands):
        raw[base + first[0] + 2 + 4 * k:base + first[0] + 4 + 4 * k] = bytes([command, argument])
    raw[base + first[1] + 6:base + first[1] + 8] = bytes([0xDA, 0])
    events = dec.pattern(first[2])
    for i, event in enumerate(events):
        if event[0] == 'note' and i % 2:
            raw[base + first[2] + 2 * i] |= 0x80
    forms = {dec.form(dec.voice(v)['form'])[0]: dec.voice(v)['form']
             for song in dec.songs() for v in dec.voices(song).values()}
    at = forms['BassDrum3'] + 12
    while bytes(raw[base + at:base + at + 4]) != b'VHDR':
        at += 2
    raw[base + at + 8 + 0x0E] = 3                                          # ctOctave
    return bytes(raw)


@pytest.fixture
def variant(ported):
    d = MusicDifferential(ported, variant_songs())
    yield d
    d.restore()


def test_the_player_on_what_no_song_has_matches_the_original(variant):
    """The pattern commands no song of the disk gives, tied notes, and a sample of three
    octaves, through track_step, track_read, note_start and note_period over random states
    of a variant of the song data laid over the disk on both sides."""
    d = variant
    rng = random.Random(0x3F5)
    for n in range(2000):
        t = rng.randrange(4)
        d.randomise_music(rng, t)
        which = rng.choice([0x04F4, 0x05D2, 0x0704, 0x07EA])
        if which == 0x04F4:
            music_case(d, rng, which, n, {'a3': d.track(t)}, (t,))
        elif which == 0x05D2:
            music_case(d, rng, which, n, {'a3': d.track(t), 'd3': 0}, (t, 0))
        elif which == 0x0704:
            note, length = rng.randrange(12, 87), rng.randrange(20)
            music_case(d, rng, which, n, {'a3': d.track(t), 'd1': note, 'd2': length},
                       (t, note, length))
        else:
            note = rng.randrange(0, 99)
            d.with_sample(t)
            d.load_port()
            d.o.call(d.code + 0x07EA, regs={'a3': d.track(t), 'd1': note})
            want = d.o.reg('d3') & 0xFFFF
            assert d.songplay(0x07EA, t, note) == want, 'case %d' % n
            check(d, 'case %d' % n)
    d.assert_ran((0x0646, 0x064A), (0x0682, 0x0684), (0x06C2, 0x06D8), (0x06FC, 0x0700),
                 (0x0748, 0x0756))           # the commands no song gives, a lower octave
