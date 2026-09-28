"""wofsongs decoded: the songs, their tracks and patterns, the voices and the samples.

wofsongs is a hunk file (re/notes/music.md): a CODE hunk whose entry returns the address of
the DATA hunk in A0, and the DATA hunk, 39,020 bytes in chip memory with 349 relocations,
which holds everything the player reads.  Relocated at 0, every pointer in it is an offset
into the DATA hunk, which is how this tool and the port read it.

    .venv/bin/python tools/song_decode.py              the songs, the voices, the samples
    .venv/bin/python tools/song_decode.py --events 2   song 2's tracks event by event

The layout, as the player reads it (re/songplay.lst):

    songs     5 longs: song n
    song      4 longs: the sequences of tracks 0 to 3; at +0x10 the voice table, voice n at
              +0x10 + 4n, ended by a zero long; voice 0 is in every song the rest voice, a
              record without a sample, which a pattern selects with 0xDC 0
    sequence  entries of 6 bytes: a long, the pattern, and a word, the transpose
    pattern   events of 2 bytes: a note below 0xD9 (bit 7 ties it to the one before) with the
              index of its length in the player's durations; or a command:
              0xD9 next sequence entry, 0xDA end, 0xDB sequence again from its start,
              0xDC voice n, 0xDD timer A's latch high byte, 0xDE its low byte (the tempo),
              0xDF volume, 0xE0 hold; any other byte from 0xE1 on is skipped
    voice     0x2E bytes: +0 VHDR and +4 BODY of its sample (the player fills them in),
              +8 the notes per octave (0x53 / ctOctave, the player's), +0xA the 8SVX FORM,
              +0x12 and +0x14 the vibrato's upper and lower limit, +0x16 its step, +0x18 its
              interval, +0x1A the interval at a note's start, +0x1C the countdown,
              +0x1E vibrato on, +0x22 arpeggio on, +0x24 four arpeggio offsets, +0x2C the
              arpeggio's position
    sample    an IFF 8SVX FORM with VHDR (oneShotHiSamples, repeatHiSamples,
              samplesPerHiCycle, samplesPerSec, ctOctave, sCompression, volume) and BODY
"""
import argparse
import os
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)

import hunk                                                     # noqa: E402

SONGS = os.path.join(ROOT, 'original', 'disk', 'Wings_of_Fury', 'wofsongs')
PLAYER = os.path.join(ROOT, 'original', 'disk', 'Wings_of_Fury', 'songplay')
COMMANDS = {0xD9: 'next', 0xDA: 'end', 0xDB: 'repeat', 0xDC: 'voice', 0xDD: 'tempo_hi',
            0xDE: 'tempo_lo', 0xDF: 'volume', 0xE0: 'hold'}
NOTE_NAMES = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']
PAL_E_CLOCK, NTSC_E_CLOCK = 709379, 715909


class Songs:
    def __init__(self, path=SONGS):
        segs = hunk.load(path, bases=[0x100000, 0, 0x200000])
        self.data = bytes(segs[1]['data'])
        self.symbols = {name: off for name, off in segs[1].get('symbols', ())
                        if not name.startswith('__H')}
        player = hunk.load(PLAYER, bases=[0x0, 0x1000, 0x2000])
        pdata = bytes(player[1]['data'])
        self.note_clocks = struct.unpack('>132L', pdata[0x44:0x254])       # indexed by note - 0x1B + 60
        self.durations = [tuple(pdata[0x254 + 2 * i:0x256 + 2 * i]) for i in range(20)]

    def l(self, at):
        return struct.unpack_from('>L', self.data, at)[0]

    def w(self, at):
        return struct.unpack_from('>H', self.data, at)[0]

    def songs(self):
        return [self.l(4 * i) for i in range(5)]

    def tracks(self, song):
        return [self.l(song + 4 * t) for t in range(4)]

    def voices(self, song):
        """The song's voice table by number, voice 0 the rest voice included."""
        out, at = {}, song + 0x10
        n = 0
        while self.l(at):
            out[n] = self.l(at)
            at += 4
            n += 1
        return out

    def sequence(self, start, songs_end=None):
        """The entries of a sequence up to the pattern that ends the track or repeats it."""
        out, at = [], start
        while True:
            pattern, transpose = self.l(at), struct.unpack_from('>h', self.data, at + 4)[0]
            out.append((pattern, transpose))
            last = self.pattern(pattern)[-1][0]
            if last in ('end', 'repeat') or len(out) > 200:
                return out
            at += 6

    def pattern(self, start):
        out, at = [], start
        while True:
            event, arg = self.data[at], self.data[at + 1]
            if event < 0xD9:
                out.append(('note', event, arg))
            else:
                out.append((COMMANDS.get(event, 'skip'), arg))
            at += 2
            if event in (0xD9, 0xDA, 0xDB) or len(out) > 2000:
                return out

    def form(self, at):
        """(name, VHDR fields, BODY offset, BODY length) of an 8SVX FORM; for a voice without a
        sample, the rest voice, ('no sample', None, None)."""
        if at == 0:
            return 'no sample', None, None
        assert self.data[at:at + 4] == b'FORM' and self.data[at + 8:at + 12] == b'8SVX', hex(at)
        end = at + 8 + self.l(at + 4)
        p, vhdr, body, name = at + 12, None, None, None
        while p < end:
            cid, size = self.data[p:p + 4], self.l(p + 4)
            if cid == b'VHDR':
                vhdr = struct.unpack_from('>LLLHBBL', self.data, p + 8)
            elif cid == b'BODY':
                body = (p + 8, size)
            elif cid == b'NAME':
                name = self.data[p + 8:p + 8 + size].rstrip(b'\0').decode('latin1')
            p += 8 + size + (size & 1)
        sym = next((n for n, o in self.symbols.items() if o == at), None)
        return name or sym or '%05x' % at, vhdr, body

    def voice(self, at):
        v = self.data[at:at + 0x2E]
        fields = struct.unpack('>LLHL', v[:0x0E])
        return {'form': fields[3], 'vib_hi': self.w(at + 0x12), 'vib_lo': self.w(at + 0x14),
                'vib_step': struct.unpack_from('>h', self.data, at + 0x16)[0],
                'vib_every': self.w(at + 0x18), 'vib_first': self.w(at + 0x1A),
                'vibrato': self.w(at + 0x1E), 'arpeggio': self.w(at + 0x22),
                'arp': struct.unpack_from('>4h', self.data, at + 0x24)}

    def note_name(self, note):
        return '%s%d' % (NOTE_NAMES[note % 12], note // 12)


def describe(s, events_of=None):
    out = []
    sym = {o: n for n, o in s.symbols.items()}
    for n, song in enumerate(s.songs()):
        out.append('song %d at %05x (%s)' % (n, song, sym.get(song, '')))
        for t, seq in enumerate(s.tracks(song)):
            entries = s.sequence(seq)
            tempos = []
            for pattern, _ in entries:
                hi = lo = None
                for ev in s.pattern(pattern):
                    if ev[0] == 'tempo_hi':
                        hi = ev[1]
                    if ev[0] == 'tempo_lo':
                        lo = ev[1]
                if hi is not None or lo is not None:
                    tempos.append((hi, lo))
            ends = s.pattern(entries[-1][0])[-1][0]
            out.append('  track %d: sequence %05x, %d entries, %s%s' % (
                t, seq, len(entries), ends, (', tempo bytes %s' % tempos) if tempos else ''))
            if events_of == n:
                for pattern, transpose in entries:
                    evs = s.pattern(pattern)
                    out.append('    pattern %05x transpose %d: %s' % (pattern, transpose, ' '.join(
                        ('%s%s/%d' % ('~' if e[1] & 0x80 else '', s.note_name((e[1] & 0x7F) + transpose), e[2])
                         if e[0] == 'note' else '%s %d' % (e[0], e[1])) for e in evs)))
        for k, v in s.voices(song).items():
            name, vhdr, body = s.form(s.voice(v)['form'])
            out.append('  voice %d at %05x: %s%s' % (k, v, name, ', the rest' if vhdr is None else ''))
    out.append('')
    forms = sorted({s.voice(v)['form'] for song in s.songs() for v in s.voices(song).values()} - {0})
    for f in forms:
        name, vhdr, body = s.form(f)
        one, rep, cyc, rate, octaves, comp, vol = vhdr
        out.append('sample %-14s FORM %05x: one-shot %5d, repeat %5d, %2d samples a cycle, %5d Hz, '
                   '%d octaves, volume %d/65536, BODY %05x %d bytes' % (
                       name, f, one, rep, cyc, rate, octaves, vol, body[0], body[1]))
    out.append('')
    seen = set()
    for song in s.songs():
        for v in s.voices(song).values():
            if v in seen:
                continue
            seen.add(v)
            d = s.voice(v)
            out.append('voice %05x (%s): vibrato %s every %d (first %d), step %d between %d and %d; '
                       'arpeggio %s %s' % (v, sym.get(v, ''), 'on' if d['vibrato'] else 'off',
                                            d['vib_every'], d['vib_first'], d['vib_step'],
                                            d['vib_lo'], d['vib_hi'],
                                            'on' if d['arpeggio'] else 'off', d['arp']))
    out.append('')
    out.append('durations (length, release tick): %s' % s.durations)
    return '\n'.join(out)


def main():
    parser = argparse.ArgumentParser(description='wofsongs decoded')
    parser.add_argument('--events', type=int, default=None, help='one song\'s patterns event by event')
    args = parser.parse_args()
    print(describe(Songs(), args.events))


if __name__ == '__main__':
    main()
