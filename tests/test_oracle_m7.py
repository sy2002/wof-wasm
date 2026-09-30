"""M7 part 1 differential tests: the campaign's and the saved game's routines against the
original (SPEC 7.4, re/notes/porting-m7.md, "How the port is held").

Each routine runs twice on the same randomised state, once as the original's 68000 code
under the oracle and once as the port's C, and every registered global and table the two
touched is compared, as tests/test_oracle_m5.py and tests/test_oracle_m6.py do it:
mission_won over every rank and mission number with the rank's cap, choose_night with
rand_beam served on both sides from the port's stream, and the walker of the saved game
with its write callback, whose file is compared byte for byte with what the original hands
dos.Write.  The regions no script executes are reached by the cases, which each test
asserts.
"""
import os
import random
import sys

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, 'tools'))
sys.path.insert(0, HERE)

import ctypes                                         # noqa: E402

from unicorn import UC_HOOK_CODE                     # noqa: E402
from unicorn.m68k_const import UC_M68K_REG_D0        # noqa: E402

import savegame                                       # noqa: E402
from test_oracle_m4 import w                          # noqa: E402
from test_oracle_m5 import PLAYER, TickDifferential, check  # noqa: E402
from test_oracle_m6 import Reached, ShipsDifferential  # noqa: E402

MISSION_WON, CHOOSE_NIGHT = 0x015694, 0x0111FC
SAVE_WALK, SAVE_WRITE_PART, SAVE_GAME_WRITE = 0x015EC2, 0x015DDE, 0x015E8A
DOS_WRITE_SLOT = 0x0233FC                # the far-call slot of os_dos_write, -$7c02(a4)
DOS_OPEN_SLOT = 0x0233EA                 # and of os_dos_open, -$7c14(a4)
RANK_PLAYED, MISSION_NUMBER = 0x0253BE, 0x0253C0
TICKER_TEXT = 0x02716A
MAP_LENGTH, MAP_EXTENT, MAP_RECORDS_END = 0x0253C6, 0x024630, 0x02462C
SHIPS = 0x025460
COUNT_F, COUNT_3, COUNT_4, SOLDIER_COUNT = 0x025385, 0x025386, 0x025387, 0x0253C4

# The regions of the M7 routines that no script executes (re/notes/porting-m7.md, "Appendix:
# the regions no run executed"), by the routine whose test must reach them.
COLD = {
    MISSION_WON: [0x0156B2, 0x0156C6, 0x0156E8],           # the promotion, the cap, the next
    CHOOSE_NIGHT: [0x011218, 0x01122E],                    # the night draw, the day
    SAVE_GAME_WRITE: [0x015EBE],                           # the file that cannot be opened
}


def rank_and_mission(d, rng):
    """rank_played and mission_number as a campaign leaves them, and beyond: the ranks past
    the table read missions_per_rank by address on both sides."""
    o = d.o
    rank = rng.choice([0, 1, 2, 3, 4, 5, 6, 6, 6, rng.randrange(0, 7), 7, 8])
    missions = (3, 3, 2, 2, 1, 1, 3)[rank] if rank < 7 else 3
    mission = rng.choice([1, 1, missions, missions, missions + 1, rng.randrange(0, 5)])
    w(o, RANK_PLAYED, rank)
    w(o, MISSION_NUMBER, mission)
    return rank, mission


@pytest.fixture
def tick(ported):
    d = TickDifferential(ported)
    yield d
    d.restore()


def test_mission_won_matches_the_original(tick):
    """mission_won (0x015694) over 2,000 states: the next mission's number and its message,
    the promotion with balloons_on and its message, the rank's cap at 6 after the last
    rank's last mission, and the message appended to what ticker_text holds over its last
    character, as the scan to its NUL and the subq.w #2 place it.  The text before is at
    least a character and short enough that the longer message stays in ticker_text's 300
    bytes, as every caller leaves it (a message of its own comes first)."""
    d, lib = tick, tick.ported.lib
    rng = random.Random(0x015694)
    reached = Reached(d.o)
    seen = set()
    for n in range(2000):
        d.randomise_tick(rng)
        rank, mission = rank_and_mission(d, rng)
        text = bytes(rng.randrange(0x20, 0x7F) for _ in range(rng.randrange(1, 160)))
        d.o.write(TICKER_TEXT, text + b'\0' + bytes(rng.randrange(256) for _ in range(20)))
        d.o.write(0x02535D, bytes([rng.choice([0, 0, 0xFF])]))      # balloons_on
        w(d.o, 0x0253BC, rng.choice([0, 0xFFFF]))
        d.load_port()
        d.o.call(MISSION_WON)
        lib.wof_mission_won()
        check(d, 'mission_won, case %d (rank %d, mission %d)' % (n, rank, mission))
        seen.add((d.o.r16(RANK_PLAYED), d.o.r16(MISSION_NUMBER)))
    reached.close()
    assert reached.missing(COLD[MISSION_WON]) == [], 'no case reached these regions'
    assert (6, 1) in seen and (1, 1) in seen and (0, 2) in seen, sorted(seen)


def test_choose_night_matches_the_original(tick):
    """choose_night (0x0111FC) over 2,000 states: the map number of mission_map_table by
    rank_played x 4 + mission_number, day at 6 and below, and above it bit 15 of the fourth
    of four rand_beam draws, served on both sides from the port's stream; the index past
    the table's 29 bytes reads what follows it by address on both sides."""
    d, lib = tick, tick.ported.lib
    lib.wt_entropy_get.restype = ctypes.c_uint
    rng = random.Random(0x0111FC)
    reached = Reached(d.o)
    nights = 0
    for n in range(2000):
        d.randomise_tick(rng)
        rank_and_mission(d, rng)
        w(d.o, 0x025390, rng.choice([0, 1, rng.randrange(0x10000)]))   # night_flag before
        d.load_port()
        d.o.call(CHOOSE_NIGHT)
        lib.wof_choose_night()
        check(d, 'choose_night, case %d' % n)
        assert lib.wt_entropy_get() == d.state, 'case %d: the port drew another number of values' % n
        nights += d.o.r16(0x025390)
    reached.close()
    assert reached.missing(COLD[CHOOSE_NIGHT]) == [], 'no case reached these regions'
    assert 100 < nights < 1900, nights


# ------------------------------------------- D1's upper word through the targets' layers

@pytest.fixture
def layers(ported):
    d = ShipsDifferential(ported)
    yield d
    d.restore()


@pytest.mark.parametrize('address', [0x013D78, 0x013DE8], ids=['targets_3_draw', 'targets_f_draw'])
def test_the_targets_layers_hand_d1_on_as_the_original(layers, address):
    """targets_3_draw (0x013D78) and targets_f_draw (0x013DE8) over 1,500 states each, with
    dug-outs whose refill falls due and destroyed pillboxes whose smoke falls due: neither
    saves D1, so a refill leaves the direction's upper word there and a pillbox's smoke
    0x11, and target_fire's smoke at the engine takes it after the exchange.  Found in
    save_a at one VBlank a pass, where a refill before a dug-out's fire changed the smoke's
    x; the state and the upper word D1 leaves are compared."""
    d = layers
    rng = random.Random(address)
    refills = smokes = 0
    for n in range(1500):
        d.randomise_tick(rng)
        for i in range(16):                            # dug-outs empty, refills due
            at = d.t3 + 0x10 * i
            if rng.random() < 0.3:
                d.o.write(at + 8, b'\0')
                w(d.o, at + 0x0E, rng.choice([1, 1, 2]))
        for i in range(32):                            # pillboxes destroyed, smoke due
            at = d.tf + 0x0E * i
            if rng.random() < 0.3:
                d.o.write(at + 8, b'\xff')
                w(d.o, at + 0x0A, rng.choice([2, 5, 0x31]))
                w(d.o, at + 0x0C, rng.choice([1, 1, 3]))
        w(d.o, PLAYER + 0x0C, rng.choice([0, 0, 0, 1]))     # now and then on the deck
        if d.o.read(0x025387, 1)[0] == 0:
            # No barracks: nearest_barracks' dbra would walk 65,536 records, which no map
            # asks for (every map with dug-outs has barracks), as M5's test of the refill
            # leaves it out.
            d.o.write(0x025387, bytes([rng.randrange(1, 17)]))
        high = rng.choice([0, 0, 0xFFFF, 0x11, rng.randrange(0x10000)])
        d.load_port()
        d.o.call(address, regs={'d1': (high << 16) | rng.randrange(0x10000),
                                'd7': d.o.r32(0x026F54)})
        got, _ = d.port(address, 0, high)
        want = d.o.reg('d1') >> 16
        check(d, '%06X, case %d' % (address, n), want, got & 0xFFFF)
        refills += want != high and address == 0x013D78
        smokes += want == 0x11 and high != 0x11
    assert refills > 50 or smokes > 50, (refills, smokes)


# ------------------------------------------------------------------ the saved game's walker

class SaveDifferential(ShipsDifferential):
    """The ships' differential with dos.Write answered: the far-call slot of os_dos_write
    becomes `move.l 12(a7),d0; rts`, and a hook on it keeps what the walker's callback
    hands it, so that the original's saved game is the concatenation of its writes."""

    def __init__(self, ported, name='c'):
        super().__init__(ported, name)
        o = self.o
        o.write(DOS_WRITE_SLOT, bytes.fromhex('202F000C4E75'))
        self.written = bytearray()

        def write(uc, address, size, user):
            sp = o.reg('a7')
            buffer, length = o.r32(sp + 8), o.r32(sp + 12)
            self.written += o.read(buffer, length)
        o.uc.hook_add(UC_HOOK_CODE, write, begin=DOS_WRITE_SLOT, end=DOS_WRITE_SLOT)
        self.fields = savegame.registry()

    def randomise_save(self, rng):
        """The ships' state, the four target and soldier tables' counts up to the port's
        capacities, map_length up to the record list's, the ships afloat or not with and
        without a score and up to sixteen guns, and every plain registered byte of the raw
        part at random.  The bytes of the raw part no registered field covers stay the
        executable's, which is what nothing in the game writes (tests/m4complete.py holds
        that every address a mission writes is registered or listed)."""
        o = self.o
        self.randomise_ships(rng)
        for first, last, name, kind in self.fields:
            if kind == 'plain':
                o.write(first, bytes(rng.randrange(256) for _ in range(last - first + 1)))
        o.write(COUNT_F, bytes([rng.choice([0, 4, 30, 32, rng.randrange(0, 33)])]))
        o.write(COUNT_3, bytes([rng.choice([0, 7, 13, 16, rng.randrange(0, 17)])]))
        o.write(COUNT_4, bytes([rng.choice([0, 7, 14, 16, rng.randrange(0, 17)])]))
        w(o, SOLDIER_COUNT, rng.choice([0, 20, 70, 135, 160, rng.randrange(0, 161)]))
        w(o, MAP_LENGTH, rng.choice([self.chart.length, 1910, 7138, rng.randrange(0, 3577) * 2]))
        o.w32(0x025504, self.tf)
        o.w32(0x025500, self.soldiers)
        o.w32(0x0254FC, self.t3)
        o.w32(0x0254F8, self.t4)
        o.w32(0x024628, self.map_base)
        o.w32(MAP_RECORDS_END, self.map_base + rng.randrange(0, 3576 * 2))
        for i in range(5):
            ship = SHIPS + 0x1E * i
            w(o, ship + 0x04, rng.choice([0, 0xFFFF, 0x00FF, 0xFF00]))
            # the carrier's score is 0 on every map, so its missing gun list is never written
            w(o, ship + 0x12, rng.choice([0, 0, 1000, 2500, rng.randrange(0x10000)]) if i < 4 else 0)
            w(o, ship + 0x0A, rng.randrange(0, 17))
            o.w32(ship + 0x06, self.lists[i] if i < 4 else 0)
        # the player's shape and the two shape pointers of the tick, as the play leaves them
        o.w32(0x02507C, 0)
        o.w32(0x02541A, 0)
        o.w32(0x02541E, 0)

    def pointers(self):
        """{offset in the file: (field, the long the port writes there)} of the raw part's
        pointers: the shape handles are 0 here, the gun lists' flags whether one is set."""
        out = {}
        for first, last, name, kind in self.fields:
            if kind == 'plain':
                continue
            value = self.o.r32(first)
            port = (1 if value else 0) if kind == 'pool' else 0
            for k in range(4):
                out[first - savegame.RAW_START + k] = (name, (port >> (8 * (3 - k))) & 0xFF)
        return out


@pytest.fixture
def saving(ported):
    d = SaveDifferential(ported)
    yield d
    d.restore()
    ported.fs_reset()


def test_the_saved_games_walker_writes_what_the_original_writes(saving):
    """The walker (0x015EC2) with the write callback (0x015DDE) over 600 states: the file
    the port writes (wof_save_game_write) is the concatenation of what the original's
    callback hands dos.Write, byte for byte, but for the raw part's pointers, where the port
    writes the long it keeps in their place (the shape handle, the gun list's flag); and
    the walker's side effects on map_extent and map_records_end agree."""
    d, lib = saving, saving.ported.lib
    lib.wof_save_game_write.argtypes = [ctypes.c_char_p]
    lib.wof_save_game_write.restype = ctypes.c_int16
    rng = random.Random(0x015EC2)
    reached = Reached(d.o)
    sizes = set()
    for n in range(600):
        d.randomise_save(rng)
        d.load_port()
        d.ported.fs_reset()
        d.written = bytearray()
        d.o.call(SAVE_WALK, d.o.L(SAVE_WRITE_PART), d.o.L(0x1234))
        assert lib.wof_save_game_write(b'wof.oracle') == 1
        port = dict(d.ported.fs_written()).get('wof.oracle')
        want = bytearray(d.written)
        pointers = d.pointers()
        for at, (name, value) in pointers.items():
            want[at] = value
        assert port is not None and len(port) == len(want), (n, len(want), port and len(port))
        bad = [(i, want[i], port[i]) for i in range(len(want)) if want[i] != port[i]]
        assert bad == [], 'case %d: %s' % (n, bad[:6])
        check(d, 'the walker, case %d' % n)
        sizes.add(len(want))
    reached.close()
    assert reached.missing([0x015F5A, 0x015F86, 0x015D62]) == [], 'no case reached these regions'
    assert len(sizes) > 300, len(sizes)


def test_a_save_that_cannot_be_opened_writes_nothing(saving):
    """save_game_write (0x015E8A) when the file cannot be opened: the original's Open answers
    0 (its far-call slot made `moveq #0,d0; rts`), nothing is written and 0 comes back
    (0x015EBE); the port's file system refuses a file when its overlay is full, and the port
    writes nothing and answers 0 too.  The dialog ignores the answer on both sides."""
    d, lib = saving, saving.ported.lib
    lib.wof_save_game_write.argtypes = [ctypes.c_char_p]
    lib.wof_save_game_write.restype = ctypes.c_int16
    reached = Reached(d.o)
    d.o.write(DOS_OPEN_SLOT, bytes.fromhex('70004E754E71'))
    name = d.o.alloc_bytes(b'wof.oracle\0')
    d.written = bytearray()
    d.load_port()
    assert d.o.call(SAVE_GAME_WRITE, d.o.L(name)) & 0xFFFF == 0
    assert d.written == bytearray(), 'the original wrote without a file'
    d.ported.fs_reset()
    names = ['wof.full%d' % i for i in range(12)]
    for n in names:
        assert d.ported.fs_write(n, b'x')
    assert lib.wof_save_game_write(b'wof.oracle') == 0
    assert sorted(n for n, _ in d.ported.fs_written()) == sorted(names)
    check(d, 'a save that cannot be opened')
    reached.close()
    assert reached.missing(COLD[SAVE_GAME_WRITE]) == [], 'no case reached these regions'


def test_the_disks_saved_game_is_map_c_as_the_first_ranks_last_mission():
    """The disk's own `wof.mission 3`, a game saved on a real Amiga, decoded by the walker's
    layout (tools/savegame.py): its 6,866 bytes are exactly the raw part, map_length, map
    c's 3,902 bytes of records and the four tables of map c's counts, with no ship's gun
    list; rank 0, mission 3, 14,225 points, two Hellcats, two of three islands left."""
    with open(savegame.DISK_FILE, 'rb') as handle:
        data = handle.read()
    info = savegame.summary(data)
    assert info['exact'] and info['size'] == 6866, info
    assert info['map'] == info['map_by_rank'] == 'c', info
    assert (info['rank'], info['mission'], info['score'], info['lives']) == (0, 3, 14225, 2), info
    assert (info['target_count_f'], info['target_count_3'], info['target_count_4'],
            info['soldier_count']) == (4, 7, 7, 70), info
    assert (info['islands'], info['islands_left']) == (3, 2), info
    assert info['ships'] == [] and info['player_on_deck'] == 1, info
    assert info['sections'] == [('raw', 0x84A), ('length', 2), ('map', 3902), ('f', 56),
                                ('soldiers', 560), ('3', 112), ('4', 112)], info


# --------------------------------------------------------------- the saved game read back

SAVE_GAME_READ, SAVE_READ_PART = 0x015E1A, 0x015D7C
DOS_READ_SLOT = 0x0233F0                 # the far-call slot of os_dos_read, -$7c0e(a4)
DOS_CLOSE_SLOT = 0x0233C6                # os_dos_close, -$7c38(a4)
MEM_ALLOC_SLOT = 0x023306                # mem_alloc, -$7cf8(a4)
EXIT_GAME = 0x016E96
COLD[SAVE_GAME_READ] = [0x015E50, 0x015D98]   # the file not opened, a block not allocated
PRINTF_SLOT, IO_ERR_SLOT = 0x023384, 0x0233DE


class ReadDifferential(SaveDifferential):
    """The save differential with the file system and the allocator answered for a read:
    Open gives a handle, Read copies the next bytes of the file the test made, as many as
    are left and at most the length asked for, Close does nothing, and mem_alloc hands out
    fresh zeroed blocks from a bump allocator of the test's own."""

    def __init__(self, ported, name='c'):
        super().__init__(ported, name)
        o = self.o
        o.write(DOS_OPEN_SLOT, bytes.fromhex('4E754E714E71'))     # rts, D0 set by the hook
        self.open_answer = 1                                       # a handle, or 0: no file
        self.alloc_fails = False
        o.write(DOS_CLOSE_SLOT, bytes.fromhex('4E754E714E71'))    # rts
        o.write(DOS_READ_SLOT, bytes.fromhex('4E754E714E71'))     # rts, D0 set by the hook
        o.write(MEM_ALLOC_SLOT, bytes.fromhex('4E754E714E71'))
        self.file = b''
        self.at = 0
        self.blocks = []
        self.heap = o.alloc(0x40000)
        self.heap_at = self.heap

        def read(uc, address, size, user):
            sp = o.reg('a7')
            buffer, length = o.r32(sp + 8), o.r32(sp + 12)
            n = max(0, min(length, len(self.file) - self.at))
            o.write(buffer, self.file[self.at:self.at + n])
            self.at += n
            o.uc.reg_write(UC_M68K_REG_D0, n)

        def opened(uc, address, size, user):
            o.uc.reg_write(UC_M68K_REG_D0, self.open_answer)

        def alloc(uc, address, size, user):
            if self.alloc_fails:
                o.uc.reg_write(UC_M68K_REG_D0, 0)
                return
            length = o.r32(o.reg('a7') + 4)
            block = self.heap_at
            self.heap_at += (length + 15) & ~7
            o.write(block, bytes(length))
            self.blocks.append((block, length))
            o.uc.reg_write(UC_M68K_REG_D0, block)

        o.uc.hook_add(UC_HOOK_CODE, read, begin=DOS_READ_SLOT, end=DOS_READ_SLOT)
        o.uc.hook_add(UC_HOOK_CODE, alloc, begin=MEM_ALLOC_SLOT, end=MEM_ALLOC_SLOT)
        o.uc.hook_add(UC_HOOK_CODE, opened, begin=DOS_OPEN_SLOT, end=DOS_OPEN_SLOT)

    def memory(self):
        m = super().memory()
        regions = dict(m.regions)
        for block, length in self.blocks:
            regions[block] = bytes(self.o.read(block, max(length, 1)))
        return self.m4state.Memory(regions)


@pytest.fixture
def reading(ported):
    d = ReadDifferential(ported)
    yield d
    d.restore()
    ported.fs_reset()
    ported.lib.wt_map_addresses(None, 0)


def read_differences(d, skip):
    """The registered state's differences but for the fields in `skip`."""
    g, m, problems = d.layout.expected(d.memory())
    problems = [p for p in problems if p.split(':')[0] not in skip]
    found = d.layout.differences(d.layout.port_globals(), d.layout.port_mission(), g, m)
    return problems + ['%s: port %x original %x' % x for x in found if x[0] not in skip]


def test_save_game_read_reads_what_the_original_reads(reading):
    """save_game_read (0x015E1A) with the walker and the read callback (0x015D7C) over 600
    files the original's own walker wrote from random states, a third of them cut short at a
    random byte, each read over another random state, the running game: every registered
    global and table agrees afterwards, the blocks the original allocated anew compared as
    the port's pools, a piece read short leaving the pointer and the old block on both
    sides.  The four pointer fields are the port's to derive: the original keeps the file's
    values there, and a ship's gun list is compared as whether the original read a block for
    it (tests/test_loader.py holds the derived values to the original's first tick)."""
    import ctypes as c
    d, lib = reading, reading.ported.lib
    lib.wof_save_game_read.argtypes = [c.c_char_p]
    lib.wof_save_game_read.restype = c.c_int16
    lib.wt_map_addresses.argtypes = [c.c_void_p, c.c_uint]
    rng = random.Random(0x015E1A)
    reached = Reached(d.o)
    name = d.o.alloc_bytes(b'wof.oracle\0')
    shorts = whole = 0
    for n in range(600):
        d.randomise_save(rng)
        d.written = bytearray()
        d.o.call(SAVE_WALK, d.o.L(SAVE_WRITE_PART), d.o.L(0x1234))
        data = bytes(d.written)
        if rng.random() < 0.33:
            data = data[:rng.randrange(0, len(data))]
            shorts += 1
        else:
            whole += 1
        d.randomise_save(rng)                     # the running game the file is read over
        d.load_port()
        d.ported.fs_reset()
        assert d.ported.fs_write('wof.oracle', data)
        d.file, d.at, d.blocks, d.heap_at = data, 0, [], d.heap
        # The map's block is the first the read allocates, at the heap's start; the port
        # takes that address as it takes the harness's (SPEC 7.3).
        address = (c.c_uint32 * 1)(d.heap)
        lib.wt_map_addresses(address, 1)
        assert d.o.call(SAVE_GAME_READ, d.o.L(name)) & 0xFFFF == 1
        assert lib.wof_save_game_read(b'wof.oracle') == 1
        blocks = {b for b, _ in d.blocks}
        skip = {'player[0].shape', 'torpedo_shape[0].s', 'g_02541a[0].s'}
        port_guns = []
        for i in range(5):
            skip.add('ship_records[%d].guns' % i)
            read = d.o.r32(SHIPS + 0x1E * i + 6) in blocks
            port_guns.append((i, read, lib.wt_ship_guns(i)))
        found = read_differences(d, skip)
        assert found == [], 'case %d (%d bytes): %s' % (n, len(data), found[:6])
        bad = [(i, read, got) for i, read, got in port_guns if bool(got) != read]
        assert bad == [], 'case %d: a ship\'s gun list, (ship, read, port flag): %s' % (n, bad)
    reached.close()
    assert shorts > 100 and whole > 300, (shorts, whole)


def test_a_file_the_original_cannot_read_ends_the_game_and_the_port_refuses_it(reading):
    """The two ways out of save_game_read that end the program: a file Open cannot open
    (0x015E50: IoErr, the message, exit_game) and a block mem_alloc cannot give
    (0x015D98: exit_game), each run under the oracle to exit_game.  The port never reaches
    either: its dialog asks wof_save_game_fits first, which refuses a missing file and one
    whose counts exceed the pools the port keeps (src/mission.def), and leaves as a cancel."""
    import ctypes as c
    d, lib = reading, reading.ported.lib
    lib.wof_save_game_fits.argtypes = [c.c_char_p]
    lib.wof_save_game_fits.restype = c.c_int
    o = d.o
    exits = []

    def stop(uc, address, size, user):
        exits.append(o.r32(o.reg('a7')))                 # the return address: where from
        uc.emu_stop()
    o.uc.hook_add(UC_HOOK_CODE, stop, begin=EXIT_GAME, end=EXIT_GAME)
    o.write(PRINTF_SLOT, bytes.fromhex('4E754E714E71'))
    o.write(IO_ERR_SLOT, bytes.fromhex('203C000000CD4E75'))    # move.l #205,d0; rts
    reached = Reached(o)
    name = o.alloc_bytes(b'wof.oracle\0')

    d.open_answer = 0                                            # Open answers 0
    try:
        o.call(SAVE_GAME_READ, o.L(name))
    except RuntimeError:
        pass
    assert exits and exits[0] == 0x015E66, ['%06X' % e for e in exits]
    d.ported.fs_reset()
    assert lib.wof_save_game_fits(b'wof.oracle') == 0

    d.open_answer = 1
    rng = random.Random(0x015D98)
    d.randomise_save(rng)
    d.written = bytearray()
    o.call(SAVE_WALK, o.L(SAVE_WRITE_PART), o.L(0x1234))
    d.file, d.at = bytes(d.written), 0
    d.alloc_fails = True                                         # mem_alloc answers 0
    exits.clear()
    try:
        o.call(SAVE_GAME_READ, o.L(name))
    except RuntimeError:
        pass
    assert exits and exits[0] == 0x015D9E, ['%06X' % e for e in exits]
    reached.close()
    assert reached.missing(COLD[SAVE_GAME_READ]) == [], 'no case reached these regions'

    # The port's check: a file whose soldiers are more than its pool holds, and one shorter
    # than its own counts ask, are refused; the file as written is taken.
    raw = bytearray(d.file)
    d.ported.fs_reset()
    assert d.ported.fs_write('wof.oracle', bytes(raw))
    assert lib.wof_save_game_fits(b'wof.oracle') == 1
    at = 0x0253C4 - 0x024CAE                                    # soldier_count in the raw part
    raw[at:at + 2] = (161).to_bytes(2, 'big')
    assert d.ported.fs_write('wof.oracle', bytes(raw))
    assert lib.wof_save_game_fits(b'wof.oracle') == 0
    assert d.ported.fs_write('wof.oracle', bytes(d.file[:-1]))
    assert lib.wof_save_game_fits(b'wof.oracle') == 0


# ------------------------------------------------------------------ the score's digits

def rom_raw_do_fmt(rom, base):
    """exec.RawDoFmt in the ROM (LVO -522, the function table's entry 86): exec's function
    table is a table of word offsets MakeFunctions reads, found as the one whose entry 87
    (LVO -528) is GetCC, which tests/ffp.py finds by its contents.  Tried with the -1 that
    marks word offsets from the table and without it; None where neither is found."""
    import struct
    import ffp
    getcc = ffp.rom_getcc(rom, base)
    if getcc is None:
        return None
    found = []
    for at in range(0, len(rom) - 2 * 90, 2):
        for first in (at + 2, at):
            if first == at + 2 and struct.unpack_from('>h', rom, at)[0] != -1:
                continue
            table = base + at
            if table + struct.unpack_from('>h', rom, first + 2 * 87)[0] != getcc:
                continue
            entries = [table + struct.unpack_from('>h', rom, first + 2 * i)[0] for i in range(88)]
            if all(base <= e < base + len(rom) for e in entries):
                found.append(entries[86])
    return found[0] if len(set(found)) == 1 else None


DRAW_SCORE, DASH_DIGIT, DASH_DIGIT_ROW = 0x01F26A, 0x01F2B0, 0x01F2BE
SHAPE_BLIT_SLOT = 0x02AFFE - 0x7CE0      # shape_blit's far-call slot, -$7ce0(a4)
SCORE_TEXT, PLAYER_SCORE = 0x027F22, 0x02534C
GAME_SYSBASE = 0x02AFFE - 0x408A         # the game's SysBase, -$408a(a4)


def scores(rng):
    """Scores as play gives them and as a loaded game can bring them: small, seven digits
    and more, negative in every width, the extremes."""
    out = [0, 1, 9, 350, 14225, 9999999, 10000000, 0x7FFFFFFF, -1, -5, -123, -999999,
           -1000000, -9999999, -10000000, -0x80000000]
    for _ in range(600):
        width = rng.randrange(1, 11)
        value = rng.randrange(10 ** (width - 1), 10 ** width)
        out.append(min(value, 0x7FFFFFFF) * rng.choice([1, -1]))
    return out


@pytest.mark.skipif(not os.path.isfile(os.path.join(ROOT, 'original', 'kick.rom')),
                    reason='needs original/kick.rom for exec.RawDoFmt')
def test_draw_score_draws_what_the_original_draws(ported):
    """draw_score (0x01F26A) over 616 scores, negative ones and ones of eight and more
    characters among them, the original with exec's own RawDoFmt from the ROM: the text in
    score_text and, digit by digit, the position and the row dash_digit gives shape_blit
    (the row from digit_rows by a signed index, so a '-' reads the bytes in front of it);
    the port's blits are taken from its trace with its shape's hotspot added back.  The
    blits themselves are M4's, held by tests/blitter.py."""
    import struct
    import ffp
    from oracle import Oracle
    with open(ffp.ROM_PATH, 'rb') as handle:
        rom = handle.read()
    base = 0x1000000 - len(rom)
    raw_do_fmt = rom_raw_do_fmt(rom, base)
    assert raw_do_fmt is not None, 'exec.RawDoFmt not found in the ROM'
    o = Oracle(a4=0x02AFFE)
    o.uc.mem_map(base, len(rom))
    o.uc.mem_write(base, rom)
    o.write(ffp.EXEC_BASE - 522, b'\x4e\xf9' + struct.pack('>L', raw_do_fmt))
    o.w32(4, ffp.EXEC_BASE)
    o.w32(GAME_SYSBASE, ffp.EXEC_BASE)
    hot = (3, 5)
    record = o.alloc(0x20)
    o.write(record, struct.pack('>HHhh', 2, 8, *hot))
    table = o.alloc(4 * 16)
    o.w32(table + 4 * 7, record)
    o.write(SHAPE_BLIT_SLOT, bytes.fromhex('4E754E714E71'))
    rows = []

    def row(uc, address, size, user):
        from unicorn.m68k_const import UC_M68K_REG_D0, UC_M68K_REG_D1
        rows.append((uc.reg_read(UC_M68K_REG_D0) & 0xFFFF, uc.reg_read(UC_M68K_REG_D1) & 0xFFFF))
    o.uc.hook_add(UC_HOOK_CODE, row, begin=DASH_DIGIT_ROW, end=DASH_DIGIT_ROW)

    lib = ported.lib
    ported.reset_core()
    negative = 0
    for n, value in enumerate(scores(random.Random(0x01F26A))):
        word = value & 0xFFFFFFFF
        o.w32(PLAYER_SCORE, word)
        o.write(SCORE_TEXT, bytes(16))
        rows.clear()
        o.call(DRAW_SCORE, regs={'a3': table})
        want_text = o.read(SCORE_TEXT, 16).split(b'\0')[0]
        want = [(x, r) for x, r in rows]

        ported.set_g('player_score', word)
        for i in range(8):
            ported.set_g('score_text', 0, index=i)
        lib.wt_trace_reset()
        lib.wt_draw_score()
        got = []
        for t in ported.traces('shape_blit'):
            h = t['c']
            slot, index = (h >> 11) - 1, h & 0x7FF
            got.append(((t['a'] + lib.wt_shape_field(slot, index, 2)) & 0xFFFF,
                        (t['b'] + lib.wt_shape_field(slot, index, 3)) & 0xFFFF))
        text = bytes(ported.g('score_text', index=i) for i in range(8)).split(b'\0')[0]
        assert text == want_text[:8], 'case %d, %d: %r, port %r' % (n, value, want_text, text)
        assert got == want, 'case %d, %d (%r): %s, port %s' % (n, value, want_text, want, got)
        assert len(want) == len(want_text)
        negative += value < 0
    assert negative > 250
    ported.reset_core()
