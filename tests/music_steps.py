"""The music's state VBlank by VBlank, the headless original's against the port's (M8 part 2).

The mission scripts compare the player's memory at every pass and tick through the registry
(src/mission.def), but the music plays outside the missions: in the front end, on the
high-score screen and in the rank selection of the outer loop.  There the headless original
takes no steps, so this module takes one at every VBlank: before each VBlank it keeps what the
program's work since the previous one left - the game's pointers to the two segments, the song
it asked for, 0x027430, the player's DATA hunk and the song data's voices - and the port is
compared with it after the pass that follows the same VBlank, converted as tests/m4state.py
converts every table.  Only what changed from one VBlank to the next is kept.
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, 'tools'))
sys.path.insert(0, HERE)

import headless                    # noqa: E402
import m4state                     # noqa: E402

MUSIC_TABLES = ['songs_seglist', 'song_data', 'player_seglist', 'player_entry', 'player_head',
                'player_vars', 'player_tracks', 'player_song', 'song_voices']
# The game's own: the pointers, then song_number and 0x027430 with its neighbour.
POINTERS = (m4state.PLAYER_SEGLIST, m4state.PLAYER_ENTRY, 0x027428, m4state.SONG_DATA)
GLOBALS = ((0x0255F2, 4), (0x027430, 4))
VOICES_END = 0xCC + 7 * 0x2E


class Recorder(headless.Headless):
    """The headless original keeping the music's state before every VBlank."""

    def __init__(self, run, **options):
        super().__init__(run, **options)
        self.music_states = []            # (VBlanks before it, state) where it changed

    def _vblank(self):
        state = self.music_state()
        if not self.music_states or self.music_states[-1][1] != state:
            self.music_states.append((self.vblanks, state))
        super()._vblank()

    def music_state(self):
        o = self.o
        pointers = tuple(o.r32(a) for a in POINTERS)
        values = tuple(o.read(a, n) for a, n in GLOBALS)
        regions = ()
        seglist, _, _, songs = pointers
        if seglist:
            code = (seglist << 2) - 4
            link = o.r32(seglist << 2)
            data = (link << 2) - 4
            regions += ((code, o.read(code, 8)), (data, o.read(data, 8 + 0x3DC)))
        if songs:
            regions += ((songs - 8, o.read(songs - 8, 8 + VOICES_END)),)
        return pointers, values, regions

    def state_at(self, vblanks):
        """The music's state kept before the VBlank that followed `vblanks` VBlanks."""
        found = None
        for at, state in self.music_states:
            if at > vblanks:
                break
            found = state
        return found


def memory_of(state):
    """The state as the original's memory, for tests/m4state.py: the DATA hunk holds the
    pointers and the two globals, the rest is zero; the hunks are regions of their own."""
    pointers, values, regions = state
    data = bytearray(headless.DATA_END - headless.DATA_START)
    for address, value in zip(POINTERS, pointers):
        data[address - headless.DATA_START:address - headless.DATA_START + 4] = value.to_bytes(4, 'big')
    for (address, n), raw in zip(GLOBALS, values):
        data[address - headless.DATA_START:address - headless.DATA_START + n] = raw
    out = {headless.DATA_START: bytes(data)}
    out.update({base: bytes(raw) for base, raw in regions})
    return m4state.Memory(out, copy=False)


class Comparison:
    """The port's music state against a Recorder's, after every pass."""

    def __init__(self, ported):
        self.layout = m4state.Layout(ported)
        self.tables = [t for t in self.layout.tables if t['name'] in MUSIC_TABLES]
        assert len(self.tables) == len(MUSIC_TABLES)
        self.globals = [g for g in self.layout.globals if g[0] in ('song_number', 'music_playing')]
        self.cache = {}

    def ranges(self):
        for t in self.tables:
            size = self.layout.records[t['record']]['port_size'] * t['count']
            yield t['name'], t['port_offset'], size

    def expected(self, state):
        key = id(state)
        if key not in self.cache:
            g, m, problems = self.layout.expected(memory_of(state), tables=MUSIC_TABLES)
            assert not problems, problems
            self.cache = {key: (g, m)}
        return self.cache[key]

    def differences(self, state):
        want_g, want_m = self.expected(state)
        port_g, port_m = self.layout.port_globals(), self.layout.port_mission()
        out = []
        for name, offset, size in self.ranges():
            if port_m[offset:offset + size] != want_m[offset:offset + size]:
                out.append(name)
        for name, address, elem, count, offset in self.globals:
            if port_g[offset:offset + elem * count] != want_g[offset:offset + elem * count]:
                out.append(name)
        if out:
            fields = [f for f in self.layout.differences(port_g, port_m, want_g, want_m)
                      if f[0].split('[')[0] in out]
            return fields[:6] or out
        return []
