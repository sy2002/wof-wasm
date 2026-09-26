"""Paula's audio side for the headless original (M8): the instrument behind the sound event log.

The headless original keeps the custom chips as plain memory, which is enough for everything
but sound: the effects engine (sound_init 0x01E8B8, audio_irq 0x01EBAA, soundfx_vblank
0x01EC64) starts a sample by writing a channel's registers and switching its DMA on, and
learns that a sample has played through the level-4 interrupt, which plain memory never
raises.  This model watches the writes the game makes to

    DMACON  0xDFF096   the four audio DMA bits, set and cleared
    INTENA  0xDFF09A   read back through INTENAR 0xDFF01C
    INTREQ  0xDFF09C   read back through INTREQR 0xDFF01E
    AUDx    0xDFF0A0 + 0x10 x   LC (a long, or two words), LEN, PER, VOL

and raises the audio interrupts the way Paula does, calling the handler the game put at the
level-4 autovector, 0x70, as the CPU would.  DMACONR is left alone: the blitter's busy bit is
read there, and a model of the audio bits would change nothing the game reads.

Time.  The harness has no clock between wait points (re/notes/headless.md, "Scheduling"), so
the model defines one.  A VBlank is `clock` units and a sample at period P is `P * hz` units,
where hz is the run's video rate and clock the colour clock of that standard (3,546,895 Hz
at 50 Hz, 3,579,545 Hz at 60 Hz); in seconds that is 1/hz for a VBlank and P/clock for a
sample, so all of it is integer.  Every write the program makes after VBlank k, in the
servers of VBlank k and in the main program up to the next VBlank, happens at the instant
T_k = k * clock.  A channel's own events, a sample's start and a cycle's end, happen at
their exact times; those in [T_k, T_k+1) are delivered at VBlank k+1, before its servers,
in time order and at equal times in channel order.  An event at exactly T_k sees every
write made at T_k.

A channel.  Switched on by DMACON, it takes LC and LEN (0 means 65,536 words) at once, raises
its interrupt request (the start interrupt, Paula's first data fetch) and plays 2 x LEN bytes,
each for the period its register holds when that byte begins.  When the last byte has been
played the cycle ends: the channel takes LC and LEN again, as they stand then, raises the
request again and plays on (the restart from the repeat pointer).  Cleared in DMACON it stops.
Paula raises the wrap request a word before the cycle's last word is played, when that word
is fetched; the model raises it when the word has played, a difference of four samples.

The interrupt.  A request in INTREQ reaches the CPU when INTENA has the master bit (14) and
the channel's bit.  Deliverable requests are delivered after every channel event at a VBlank
boundary and after every VBlank server returns, by calling the autovector's handler with an
exception frame, again while one stays deliverable.  A request the main program makes
deliverable would wait for the next such point; `late` counts those, and no run has had one.

The event log, one entry per sample start and per restart:
    (kind, vblank, pass, tick, channel, file, offset, words, period, volume, time)
kind 'S' for DMA switched on and 'R' for the restart at a cycle's end; `vblank` the VBlank the
event belongs to (a start inside VBlank k's servers is k, a channel event in [T_k, T_k+1) is
k+1); `file` the sound file the sample pointer lies in, `offset` the pointer's distance from
the file's start; `time` the event's instant in units.  tests/m4compare.py holds the port's
log (src/audio.c) to this one.
"""
import bisect
import struct

PAL_CLOCK = 3546895
NTSC_CLOCK = 3579545

CUSTOM = 0xDFF000
INTENAR, INTREQR = CUSTOM + 0x01C, CUSTOM + 0x01E
DMACON, INTENA, INTREQ = 0x096, 0x09A, 0x09C
AUD0 = 0x0A0
AUDIO_BITS = 0x0780
LEVEL4_VECTOR = 0x70

# The game's pointers to its eight sound files, which sounds_load (0x013368) fills.
SOUND_POINTERS = (0x026E3E, 0x026E42, 0x026E58, 0x026E7A, 0x026E96, 0x026EA8, 0x026EAC,
                  0x026EB4)


class Channel:
    __slots__ = ('on', 'lc', 'len', 'per', 'vol', 'ptr', 'left', 'next')

    def __init__(self):
        self.on = False
        self.lc = self.len = self.per = self.vol = 0
        self.ptr = 0            # the byte the cycle is at (not needed for timing; for the renderer)
        self.left = 0           # bytes of the cycle not yet begun
        self.next = 0           # the instant the next byte begins, or the cycle ends when left is 0


def cycle_bytes(length):
    return 2 * (length or 0x10000)


class Paula:
    def __init__(self, machine, hz):
        self.m = machine
        self.hz = hz
        self.clock = PAL_CLOCK if hz == 50 else NTSC_CLOCK
        self.ch = [Channel() for _ in range(4)]
        self.intena = 0x4000            # the operating system runs with the master bit on
        self.intreq = 0
        self.events = []
        self.irqs = 0                   # handler calls
        self.late = 0                   # requests made deliverable outside a delivery point
        self.at = None                  # the instant of the channel event being delivered
        self._publish()

    # ------------------------------------------------------------------ time

    def now(self):
        return self.m.vblanks * self.clock if self.at is None else self.at

    def unit(self, c):
        return max(self.ch[c].per, 1) * self.hz

    def _next_event(self, c, end):
        """The instant channel c's cycle ends if that is before `end`, else None."""
        ch = self.ch[c]
        if not ch.on:
            return None
        t = ch.next + ch.left * self.unit(c)
        return t if t < end else None

    def _advance(self, c, until):
        """Begin every byte of the cycle that begins before `until`; the cycle does not end."""
        ch = self.ch[c]
        if not ch.on or ch.left == 0 or ch.next >= until:
            return
        u = self.unit(c)
        n = min(ch.left, (until - 1 - ch.next) // u + 1)
        ch.left -= n
        ch.ptr += n
        ch.next += n * u

    # ------------------------------------------------------------------ the VBlank

    def boundary(self):
        """VBlank k+1 is about to happen: the channel events of [T_k, T_k+1), each delivered."""
        start = self.m.vblanks * self.clock
        end = start + self.clock
        while True:
            due = [(t, c) for c in range(4) for t in [self._next_event(c, end)] if t is not None]
            if not due:
                break
            t, c = min(due)
            self._advance(c, t)
            ch = self.ch[c]
            ch.next = t
            ch.left = 0
            self.at = t
            try:
                self._restart(c, t)
                self.deliver()
            finally:
                self.at = None
        for c in range(4):
            self._advance(c, end)

    def _restart(self, c, t):
        ch = self.ch[c]
        ch.ptr = ch.lc
        ch.left = cycle_bytes(ch.len)
        ch.next = t
        self._log('R', c, t, self.m.vblanks + 1)
        self._request(c)

    def _start(self, c):
        ch = self.ch[c]
        t = self.now()
        ch.on = True
        ch.ptr = ch.lc
        ch.left = cycle_bytes(ch.len)
        ch.next = t
        self._log('S', c, t, self.m.vblanks + (1 if self.at is not None else 0))
        self._request(c)

    def _request(self, c):
        self.intreq |= 0x80 << c
        self._publish()

    def deliverable(self):
        return bool(self.intena & 0x4000) and bool(self.intena & self.intreq & AUDIO_BITS)

    def deliver(self):
        """Call the level-4 handler while an audio request is deliverable."""
        rounds = 0
        while self.deliverable():
            rounds += 1
            if rounds > 8:
                raise RuntimeError('the audio interrupt does not clear its request')
            self.irqs += 1
            self.m.nested_interrupt(self.m.o.r32(LEVEL4_VECTOR))

    # ------------------------------------------------------------------ the registers

    def _publish(self):
        self.m.o.w16(INTENAR, self.intena & 0x7FFF)
        self.m.o.w16(INTREQR, self.intreq & 0x7FFF)

    @staticmethod
    def _setclr(old, value):
        return old | (value & 0x7FFF) if value & 0x8000 else old & ~value & 0x7FFF

    def write(self, address, size, value):
        """A write of the program to the custom chips, as the memory hook sees it."""
        reg = address - CUSTOM
        for i in range(0, size, 2):
            self._word(reg + i, (value >> (8 * (size - 2 - i))) & 0xFFFF)
        if (self.m.in_vblank == 0 and self.at is None and self.m.depth == 0
                and self.deliverable()):
            self.late += 1

    def _word(self, reg, word):
        if reg == DMACON:
            for c in range(4):
                bit = 1 << c
                if not word & bit:
                    continue
                if word & 0x8000 and not self.ch[c].on:
                    self._start(c)
                elif not word & 0x8000 and self.ch[c].on:
                    self.ch[c].on = False
        elif reg == INTENA:
            self.intena = self._setclr(self.intena, word)
            self._publish()
        elif reg == INTREQ:
            self.intreq = self._setclr(self.intreq, word)
            self._publish()
        elif AUD0 <= reg < AUD0 + 0x40:
            ch = self.ch[(reg - AUD0) >> 4]
            field = reg & 0x0F
            if field == 0x0:
                ch.lc = (ch.lc & 0xFFFF) | word << 16
            elif field == 0x2:
                ch.lc = (ch.lc & 0xFFFF0000) | (word & 0xFFFE)
            elif field == 0x4:
                ch.len = word
            elif field == 0x6:
                ch.per = word
            elif field == 0x8:
                ch.vol = word

    def snapshot(self):
        """The model's state: per channel (on, LC, LEN, PER, VOL, the next byte, the bytes
        left, the instant the next one begins), then INTENA, INTREQ and the VBlank count."""
        return (tuple((int(ch.on), ch.lc, ch.len, ch.per, ch.vol, ch.ptr, ch.left, ch.next)
                      for ch in self.ch), self.intena, self.intreq, self.m.vblanks)

    # ------------------------------------------------------------------ the log

    def sample(self, pointer):
        """(file, offset) of a sample pointer: the sound file whose allocation holds it, and
        the distance from the file's first byte, which is where the game's own pointer to
        it points (sounds_load keeps one per file, SOUND_POINTERS); the allocator's header
        lies in front of it."""
        bases = sorted(self.m.alloc_sizes)
        i = bisect.bisect_right(bases, pointer) - 1
        if i >= 0 and pointer < bases[i] + self.m.alloc_sizes[bases[i]]:
            base, end = bases[i], bases[i] + self.m.alloc_sizes[bases[i]]
            label = self.m.alloc_labels.get(base, '')
            name = label[label.rfind(' ') + 1:].rstrip(')') if 'sounds/' in label else label
            starts = [p for p in (self.m.o.r32(g) for g in SOUND_POINTERS)
                      if base <= p <= pointer < end]
            return name, pointer - (max(starts) if starts else base)
        return '%06x' % pointer, 0

    def _log(self, kind, c, t, vblank):
        ch = self.ch[c]
        name, offset = self.sample(ch.lc)
        self.events.append((kind, vblank, self.m.passes, self.m.ticks, c, name.lower(), offset,
                            ch.len, ch.per, ch.vol, t))


def install(machine, hz):
    """The model and its write hook, for a Headless machine before its first instruction."""
    from unicorn import UC_HOOK_MEM_WRITE
    paula = Paula(machine, hz)

    def hook(uc, access, address, size, value, user):
        paula.write(address, size, value)
    machine.uc.hook_add(UC_HOOK_MEM_WRITE, hook, begin=CUSTOM + DMACON, end=CUSTOM + 0x0DF)
    return paula


def frame(sr, pc):
    """The 68000's exception frame for an interrupt: the status register, then the return."""
    return struct.pack('>HL', sr & 0xFFFF, pc)
