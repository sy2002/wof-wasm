"""The reach map: which routines the original enters, where, and how often.

Each milestone from M4 to M7 ported what its mission scripts reach (the options below add
M5's, M6's and M7's to M4's five of tools/pass_observe.py) and marked everything else as a
stand-in.  This tool runs each script under the headless original with a code
hook on the first instruction of every routine of re/functions.csv and counts, per routine,
its entries by the part of the run it happened in and by the phase of the harness
(re/notes/headless.md, "Write summary, read hook"):

    window  where main is: `front` up to the outer loop, `outer` from its head to the rank
            selection, `rank` the rank selection, `pre-briefing` from its end to the briefing (load_dash_assets,
            map_load), `briefing`, `setup` from the briefing's end to step S, `mission` from
            step S to the mission's end, `between` from a mission's end to the next briefing,
            and `after` once the mission is over.
    phase   V inside a VBlank's handlers and servers, T inside logic_tick's tree, F inside
            frame_update's tree, M the main program outside all three.

Every read of the beam position is counted the same way under the routine that called
rand_beam or read_vhposr, and a few probes answer the questions of the M4 task by
observation: who calls line_draw and when, whether the ticker ever scrolls, what
choose_night decides, who writes view_step, and where ingame_keys is entered from.

    .venv/bin/python tools/reach_observe.py                     every script, the tables
    .venv/bin/python tools/reach_observe.py --runs deck flight
    .venv/bin/python tools/reach_observe.py --markdown TABLE.md  the tables for the note
    .venv/bin/python tools/reach_observe.py --json REACH.json    everything, for the tests
    .venv/bin/python tools/reach_observe.py --blocks --json REACH.json   with block coverage
    .venv/bin/python tools/reach_observe.py --blocks --setups --json REACH.json
                                            the same with the setups of all fifteen maps
    .venv/bin/python tools/reach_observe.py --cold REACH.json    the never-run regions of every
                                                                 ported routine, with markers
    .venv/bin/python tools/reach_observe.py --m5 --blocks --setups --jobs 12 --json REACH.json
                                            every script of M4 and M5 (M5's: tools/m5_scripts.py)
    .venv/bin/python tools/reach_observe.py --m5-only --load REACH.json --markdown TABLE.md
                                            M5's tables from a saved run
    .venv/bin/python tools/reach_observe.py --cold REACH4.json REACH5.json
                                            the cold regions over the union of the runs
    .venv/bin/python tools/reach_observe.py --m6 --blocks --setups --jobs 12 --json REACH.json
                                            every script of M4, M5 and M6 (tools/m6_scripts.py)
    .venv/bin/python tools/reach_observe.py --m6-only --load REACH.json --markdown TABLE.md
    .venv/bin/python tools/reach_observe.py --m7-only --blocks --jobs 4 --json REACH7.json
                                            M7's scripts (tools/m7_scripts.py); --m7 with all
                                            of M4 to M6 beside them

The music player (M8 part 2), a segment the game loads with LoadSeg, is watched the same way
from its load on: its routines by re/songplay_names.txt and the file's symbols, at the
offsets of re/songplay.lst, and with --blocks its basic blocks.

    .venv/bin/python tools/reach_observe.py --m6-only --load REACH.json --player-markdown TABLE.md
                                            the player's routines, entries by part of the run
    .venv/bin/python tools/reach_observe.py --cold REACH.json   also the never-run regions of
                                            every player routine src/music.c ports

An entry is the execution of a routine's first instruction.  A routine that branches back
to its own first instruction would count each round; the tool finds those statically and
names them.  A routine that another one falls into is entered by the fall, which is how
frame_update reaches flip_buffers.
"""
import argparse
import bisect
import collections
import csv
import functools
import glob
import json
import os
import re
import struct
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)

from unicorn import UC_HOOK_BLOCK, UC_HOOK_CODE, UC_HOOK_MEM_WRITE         # noqa: E402
from unicorn.m68k_const import UC_M68K_REG_A7, UC_M68K_REG_PC            # noqa: E402
from capstone import Cs, CS_ARCH_M68K, CS_MODE_M68K_000                   # noqa: E402

import headless                                                          # noqa: E402
import pass_observe                                                      # noqa: E402

# The five scripts M4 ports from; guns and bomb belong to M5.
M4_SCRIPTS = ['deck', 'flight', 'climb', 'lost', 'gameover']

# Where main is, by the instruction it has just reached (the listing of main, 0x010006).
WINDOW_MARKS = {
    0x010066: 'outer',          # the outer loop's head: free_mission_assets, sub_013562
    0x01009A: 'rank',           # the call of rank_select, the front end of M3
    0x01009E: 'pre-briefing',   # rank_select has returned: load_dash_assets, map_load
    0x0100AE: 'briefing',       # the call of mission_briefing
    0x0100B2: 'setup',          # the briefing has returned: the mission setup up to S
    0x01010A: 'mission',        # step S; from here the inner loop
    0x010132: 'between',        # a mission is over and the next one follows
    0x01016C: 'briefing',       # the next mission's briefing
    0x010170: 'setup',          # and its setup, which joins the first one's at 0x0100D2
    0x0101C6: 'after',          # the mission is over: fade, high scores, the outer loop
}

# Probes inside routines, counted like entries under a name of their own.
PROBES = {
    0x011856: 'vblank_server:ticker_scroll',    # a message is scrolling: the roxl chain runs
    0x0118DE: 'vblank_server:ticker_message',   # the message pointer is set
    0x0118F8: 'vblank_server:ticker_glyph',     # a new glyph goes into the hidden column
}

VIEW_STEP = 0x024F36
NIGHT_FLAG = 0x025390
LINE_DRAW = ('line_draw', 'line_draw_c')


def routines():
    """(address, span, name) of every routine of the inventory."""
    out = []
    with open(os.path.join(ROOT, 're', 'functions.csv'), newline='') as handle:
        for row in csv.DictReader(handle):
            out.append((int(row['addr'], 16), int(row['span'] or 0), row['name']))
    return out


def self_looping(machine, table):
    """Routines with a branch back to their own first instruction: their entry count also
    counts those rounds.  Found from the code, the way _returns_of finds an rts."""
    md = Cs(CS_ARCH_M68K, CS_MODE_M68K_000)
    found = []
    for address, span, name in table:
        if span <= 0 or not 0x010000 <= address < 0x022F4C:
            continue
        for ins in md.disasm(machine.o.read(address, span), address):
            if ins.mnemonic.startswith(('b', 'db', 'jmp')) and ins.mnemonic not in ('bset', 'bclr',
                                                                                  'bchg', 'btst'):
                target = ins.op_str.split(',')[-1].strip().lstrip('$')
                try:
                    if int(target, 16) == address:
                        found.append(name)
                        break
                except ValueError:
                    continue
    return found


class Reach(headless.Headless):
    """The headless original with a counter on every routine's first instruction."""

    def __init__(self, run, blocks=False, **options):
        super().__init__(run, **options)
        self.window = 'front'
        self.block_hooks = blocks
        self.player_entries = collections.Counter()   # (window, phase, routine) -> entries
        self.player_blocks = collections.Counter()    # (window, phase, offset, size) -> executions
        self.blocks = collections.Counter()       # (window, phase, block, size) -> executions
        self.entries = collections.Counter()      # (window, phase, routine) -> entries
        self.draws = collections.Counter()        # (window, phase, caller) -> entropy reads
        self.line_calls = []                      # (routine, caller, window, phase, pass, tick)
        self.view_step_writes = []                # (routine, value, window, phase, pass, tick)
        self.night = []                           # (mission, night_flag, map number) after choose_night
        self.table = routines()
        self.by_address = {address: name for address, _, name in self.table}
        uc = self.uc
        for address, _, name in self.table:
            uc.hook_add(UC_HOOK_CODE, self._entry, begin=address, end=address)
        for address in PROBES:
            uc.hook_add(UC_HOOK_CODE, self._probe, begin=address, end=address)
        for address in WINDOW_MARKS:
            uc.hook_add(UC_HOOK_CODE, self._mark, begin=address, end=address)
        uc.hook_add(UC_HOOK_MEM_WRITE, self._view_step_write, begin=VIEW_STEP, end=VIEW_STEP + 1)
        if blocks:
            uc.hook_add(UC_HOOK_BLOCK, self._block, begin=0x010000, end=0x022F4B)

    def segment_loaded(self, name):
        """The player's routines and, with --blocks, its blocks, from the load on; its CODE
        hunk is fresh memory, so hooks added now fire (re/notes/headless.md, Unicorn)."""
        super().segment_loaded(name)
        if name != 'songplay':
            return
        base, size, _ = self.loaded[name][0]
        for offset, routine in player_routines():
            self.uc.hook_add(UC_HOOK_CODE, functools.partial(self._player_entry, routine),
                             begin=base + offset, end=base + offset)
        if self.block_hooks:
            self.uc.hook_add(UC_HOOK_BLOCK, functools.partial(self._player_block, base),
                             begin=base, end=base + size - 1)

    def _player_entry(self, routine, uc, address, size, user):
        self.player_entries[(self.window, self.phase(), routine)] += 1

    def _player_block(self, base, uc, address, size, user):
        self.player_blocks[(self.window, self.phase(), address - base, size)] += 1

    def _block(self, uc, address, size, user):
        self.blocks[(self.window, self.phase(), address, size)] += 1

    def _mark(self, uc, address, size, user):
        self.window = WINDOW_MARKS[address]

    def _entry(self, uc, address, size, user):
        # Every entry fires this once: a slice never ends between a code hook and its
        # instruction (tools/headless.py, _drive).
        name = self.by_address[address]
        self.entries[(self.window, self.phase(), name)] += 1
        if name in LINE_DRAW:
            caller = self.o.r32(uc.reg_read(UC_M68K_REG_A7))
            self.line_calls.append((name, self.names.routine(caller), self.window, self.phase(),
                                    self.passes, self.ticks))

    def _probe(self, uc, address, size, user):
        self.entries[(self.window, self.phase(), PROBES[address])] += 1

    def _view_step_write(self, uc, access, address, size, value, user):
        routine = self.names.routine(uc.reg_read(UC_M68K_REG_PC))
        self.view_step_writes.append((routine, value & 0xFFFF, self.window, self.phase(),
                                      self.passes, self.ticks))

    def _beam_read(self, uc, access, address, size, value, user):
        before = len(self.entropy_log)
        super()._beam_read(uc, access, address, size, value, user)
        if len(self.entropy_log) > before:
            self.draws[(self.window, self.phase(), self.entropy_log[-1][2])] += 1

    def _mission_start(self):
        self.night.append((self.missions + 1, self.o.r16(NIGHT_FLAG), self.o.r16(0x0253C0),
                           self.o.r16(0x0253BE)))
        super()._mission_start()


# Part 2's scripts beside part 1's (tools/m4_scripts.py), the night mission, and the key
# runs M3 recorded for the mission (tests/runs/, named `run:` and the file's name).
PART2_SCRIPTS = (['deck', 'flight', 'climb', 'lost', 'gameover', 'night', 'select', 'turns',
                  'landing', 'island', 'fuel'] +
                 ['run:' + os.path.basename(f)[:-5] for f in sorted(
                     glob.glob(os.path.join(ROOT, 'tests', 'runs', 'flight-*.json')) +
                     glob.glob(os.path.join(ROOT, 'tests', 'runs', 'paused-*.json')))])
NIGHT_POKE = (0x025390, 1)                     # night_flag, at the rank selection's end


def m5_scripts_list():
    """M5's scripts (tools/m5_scripts.py): the weapons, the targets, the soldiers, maps b
    and c, and the key runs during a bombing run."""
    import m5_scripts
    return list(m5_scripts.SCRIPTS)


def m6_scripts_list():
    """M6's scripts (tools/m6_scripts.py): the enemy aircraft, the ships, the carrier's
    defence, on all fifteen maps."""
    import m6_scripts
    return list(m6_scripts.SCRIPTS)


def m7_scripts_list():
    """M7's scripts (tools/m7_scripts.py): the campaign's next mission, the promotion, the
    rank's cap and the saved game; part 2's loaded games and demos."""
    import m7_scripts
    return list(m7_scripts.SCRIPTS) + list(m7_scripts.PART2)


def description_of(name, **more):
    import m4_scripts
    import m5_scripts
    import m6_scripts
    import m7_scripts
    if name in m7_scripts.RUNS or name in m7_scripts.PART2:
        return m7_scripts.script(name, **more)
    if name in m6_scripts.RUNS:
        return m6_scripts.script(name, **more)
    if name.startswith('run:'):
        with open(os.path.join(ROOT, 'tests', 'runs', name[4:] + '.json')) as handle:
            description = json.load(handle)
        description.update(more)
        return description
    if name in m5_scripts.RUNS:
        return m5_scripts.script(name, **more)
    return m4_scripts.script('flight' if name == 'night' else name, **more)


def pokes_of(name):
    """{address: (size, value[, point])} poked for a script (tools/m5_scripts.py, POKES)."""
    import m5_scripts
    import m6_scripts
    import m7_scripts
    if name == 'night':
        return {NIGHT_POKE[0]: (2, NIGHT_POKE[1])}
    if name in m7_scripts.POKES or name in m7_scripts.PART2:
        return m7_scripts.pokes(name)
    return m6_scripts.POKES.get(name) or m5_scripts.POKES.get(name, {})


def observe(name, verbose=True, blocks=False, **more):
    started = time.time()
    machine = Reach(description_of(name, **more), blocks=blocks)
    pokes = pokes_of(name)
    if pokes:
        import m5_scripts
        m5_scripts.install_pokes(machine, pokes)
    machine.run(wall_limit=3600.0)           # the longest scripts with block hooks, on a busy machine
    if verbose:
        print('%-9s %5d VBlanks, %5d passes, %4d ticks, %d missions, %d entropy reads  (%.0f s)'
              % (name, machine.vblanks, machine.passes, machine.ticks, machine.missions,
                 len(machine.entropy_log), time.time() - started))
    return machine


# The setups of V4 (tests/test_mission.py): every map loaded under its own number, its rank
# chosen with the stick in the rank selection and the mission number poked at the selection's
# end, run to step S.  Their names are `setup-` and the map's letter.
LETTERS = 'abcdefghijklmno'
MISSION_NUMBER = 0x0253C0
MISSION_MAP_TABLE = 0x02345F


def setup_runs():
    """{letter: (rank, mission)}: the first place mission_map_table names each map."""
    import oracle as oracle_module
    table = oracle_module.Oracle().read(MISSION_MAP_TABLE, 29)
    out = {}
    for rank in range(7):
        for mission in range(1, 5):
            if rank * 4 + mission < 29 and table[rank * 4 + mission] < 15:
                out.setdefault(LETTERS[table[rank * 4 + mission]], (rank, mission))
    return out


def rank_script(rank):
    return (pass_observe.FRONT[:4] + [[4, '']] + [[2, 'D'], [10, '']] * rank +
            [[3, 'F'], [30, ''], [3, 'F'], [40, '']])


def observe_setup(letter, rank, mission, verbose=True, blocks=False):
    started = time.time()
    machine = Reach({'raw': rank_script(rank), 'stop': {'vblanks': 2000}}, blocks=blocks)
    machine.stop_at(0x01009E, lambda: machine.o.write(MISSION_NUMBER, bytes([0, mission])))
    machine.run(until='inner')
    if verbose:
        print('setup-%s   rank %d, mission %d, %d VBlanks  (%.0f s)'
              % (letter, rank, mission, machine.vblanks, time.time() - started))
    return machine


def _collect_one(job):
    """One script or setup in a process of its own (collect with jobs > 1)."""
    name, verbose, blocks, first = job
    if name.startswith('setup-'):
        letter = name[6:]
        m = observe_setup(letter, *setup_runs()[letter], verbose=verbose, blocks=blocks)
    else:
        m = observe(name, verbose=verbose, blocks=blocks)
    return name, record_of(m, first)


def record_of(m, first):
    return {
        'entries': [[w, p, r, n] for (w, p, r), n in sorted(m.entries.items())],
        'draws': [[w, p, r, n] for (w, p, r), n in sorted(m.draws.items())],
        'line_calls': m.line_calls,
        'view_step_writes': m.view_step_writes,
        'night': m.night,
        'counters': {'vblanks': m.vblanks, 'passes': m.passes, 'ticks': m.ticks,
                     'missions': m.missions, 'entropy': len(m.entropy_log)},
        'self_looping': self_looping(m, m.table) if first else None,
        'blocks': [[w, p, a, size, n] for (w, p, a, size), n in sorted(m.blocks.items())],
        'player_entries': [[w, p, r, n] for (w, p, r), n in sorted(m.player_entries.items())],
        'player_blocks': [[w, p, a, size, n]
                          for (w, p, a, size), n in sorted(m.player_blocks.items())],
    }


def collect(names, verbose=True, blocks=False, setups=False, jobs=1):
    out = {}
    if jobs > 1:
        import concurrent.futures
        todo = [(name, verbose, blocks, bool(names) and name == names[0]) for name in names]
        if setups:
            todo += [('setup-' + letter, verbose, blocks, False)
                     for letter in sorted(setup_runs())]
        with concurrent.futures.ProcessPoolExecutor(max_workers=jobs) as pool:
            for name, record in pool.map(_collect_one, todo):
                out[name] = record
        return out
    machines = [(name, lambda name=name: observe(name, verbose=verbose, blocks=blocks))
                for name in names]
    if setups:
        machines += [('setup-' + letter, lambda l=letter, rm=rm: observe_setup(l, *rm, verbose=verbose,
                                                                                blocks=blocks))
                     for letter, rm in sorted(setup_runs().items())]
    for name, make in machines:
        out[name] = record_of(make(), bool(names) and name == names[0])
    return out


# The lists the M4 task asks for, as (title, window, phase).
LISTS = [
    ('The head of the outer loop, before the rank selection', ('outer',), 'M'),
    ('After the rank selection, before the briefing', ('pre-briefing',), 'M'),
    ('Mission setup, main program: the briefing\'s end to step S', ('setup',), 'M'),
    ('Mission setup, the tick main runs itself', ('setup',), 'T'),
    ('Mission setup, VBlank servers', ('setup',), 'V'),
    ('A pass during a mission: frame_update\'s tree (phase F)', ('mission',), 'F'),
    ('A VBlank during a mission (phase V)', ('mission',), 'V'),
    ('The inner loop beside frame_update during a mission (phase M)', ('mission',), 'M'),
    ('The tick during a mission (phase T)', ('mission',), 'T'),
    ('Between two missions: the fade, the next map and its briefing\'s start, main program '
     '(phase M)', ('between',), 'M'),
]


CODE_WORD = re.compile(r"(?<![`\w])((?:_?[A-Za-z][\w.]*_[\w.]*[\w])|(?:_[A-Za-z]\w*)|(?:0x[0-9A-Fa-f]+))(?![`\w])")


def code_words(text):
    """Identifiers and addresses in backticks, so that Markdown does not read their
    underscores as emphasis."""
    return CODE_WORD.sub(r'`\1`', text)


def table_rows(data, names, windows, phase, key='entries'):
    """routine -> [count per script]."""
    rows = collections.defaultdict(lambda: [0] * len(names))
    for i, name in enumerate(names):
        for w, p, r, n in data[name][key]:
            if w in windows and p == phase:
                rows[r][i] += n
    return rows


def address_of(name, table):
    for address, _, n in table:
        if n == name:
            return '%06x' % address
    return ''


def markdown(data, names):
    table = routines()
    lines = []
    for title, windows, phase in LISTS:
        rows = table_rows(data, names, windows, phase)
        lines.append('### %s' % code_words(title))
        lines.append('')
        if not rows:
            lines.append('Nothing was entered.')
            lines.append('')
            continue
        lines.append('| Routine | Address | ' + ' | '.join('`%s`' % n for n in names) + ' |')
        lines.append('|---|---|' + '---|' * len(names))
        for routine in sorted(rows, key=lambda r: (address_of(r.split(':')[0], table), r)):
            lines.append('| `%s` | `%s` | %s |' % (
                routine, address_of(routine.split(':')[0], table),
                ' | '.join(str(v) for v in rows[routine])))
        lines.append('')
    lines.append('### Entropy reads, by the routine that called `rand_beam`')
    lines.append('')
    lines.append('| Window | Phase | Caller | ' + ' | '.join('`%s`' % n for n in names) + ' |')
    lines.append('|---|---|---|' + '---|' * len(names))
    rows = collections.defaultdict(lambda: [0] * len(names))
    for i, name in enumerate(names):
        for w, p, r, n in data[name]['draws']:
            rows[(w, p, r)][i] += n
    order = ['front', 'outer', 'rank', 'pre-briefing', 'briefing', 'setup', 'mission', 'between', 'after']
    for key in sorted(rows, key=lambda k: (order.index(k[0]), k[1], k[2])):
        lines.append('| %s | %s | `%s` | %s |' % (key[0], key[1], key[2],
                                                 ' | '.join(str(v) for v in rows[key])))
    lines.append('')
    return lines


# The sound effects engine (M8, re/notes/sound.md): its routines and those that call it.
SOUND_ROUTINES = {0x011F4E, 0x011F64, 0x011F76, 0x012066, 0x012132, 0x0122CE, 0x0122F6, 0x012306,
                  0x012324, 0x01233E, 0x012354, 0x012380, 0x0123AC, 0x013368, 0x01344E, 0x01346C,
                  0x0134A4, 0x01B9CC} | set(range(0x01E8B8, 0x01ED7A))


# ------------------------------------------------------------------ the music player

PLAYER_CODE_SIZE = 0x0A88


def player_routines():
    """(offset, name) of every routine of the player's CODE hunk: re/songplay_names.txt over
    the file's own symbols, at the offsets of re/songplay.lst."""
    import disasm_player
    import hunk
    segs = hunk.load(disasm_player.PLAYER, bases=disasm_player.BASES)
    names = disasm_player.names_of(segs, disasm_player.load_names())
    return sorted((a, n) for a, n in names.items() if a < PLAYER_CODE_SIZE)


def player_spans():
    """{offset: (span, name)} of the player's routines: each up to the next."""
    table = player_routines()
    ends = [a for a, _ in table[1:]] + [PLAYER_CODE_SIZE]
    return {a: (end - a, n) for (a, n), end in zip(table, ends)}


def player_markdown(data, names):
    """The reach map of the music player: per part of the run, the entries of each of its
    routines summed over the scripts, and the number of scripts that entered it."""
    names = [n for n in names if not n.startswith('setup-')]
    order = {n: a for a, n in player_routines()}
    windows = ['front', 'outer', 'rank', 'pre-briefing', 'briefing', 'setup', 'mission',
               'between', 'after']
    totals = collections.defaultdict(collections.Counter)
    runs = collections.Counter()
    for name in names:
        seen = set()
        for w, p, r, n in data[name].get('player_entries', ()):
            totals[r][w] += n
            seen.add(r)
        for r in seen:
            runs[r] += 1
    used = [w for w in windows if any(totals[r][w] for r in totals)]
    lines = ['| Routine | Offset | ' + ' | '.join('`%s`' % w for w in used) + ' | Runs |',
             '|---|---|' + '---|' * (len(used) + 1)]
    for routine in sorted(totals, key=lambda r: order.get(r, 1 << 20)):
        lines.append('| `%s` | `%04x` | %s | %d |' % (
            routine, order.get(routine, 0), ' | '.join(str(totals[routine][w]) for w in used),
            runs[routine]))
    never = [n for a, n in player_routines() if n not in totals]
    lines.append('')
    lines.append('Never entered: %s.' % ', '.join('`%s`' % n for n in never))
    return lines


# What a region of a player routine that no run executed is, by its first offset; each
# test named asserts that its cases executed the region.
PLAYER_REGION_NOTES = {
    0x04CC: 'ported from reading; tests/test_oracle_m8.py, the tick: a song no track has started '
            'a note of, which ends it',
    0x050E: 'ported from reading; tests/test_oracle_m8.py, track_step: the arpeggio\'s next '
            'offset, which no voice of wofsongs has on',
    0x0538: 'ported from reading; tests/test_oracle_m8.py, track_step: the arpeggio\'s note',
    0x054E: 'ported from reading; tests/test_oracle_m8.py, track_step: the vibrato between its '
            'limits, which no voice of wofsongs has on',
    0x0646: 'ported from reading; tests/test_oracle_m8.py, the variant song data: a hold and a '
            'command byte passed over, which no song gives',
    0x0682: 'ported from reading; tests/test_oracle_m8.py, the variant song data: a track\'s end',
    0x06C2: 'ported from reading; tests/test_oracle_m8.py, the variant song data: the latch\'s '
            'low byte',
    0x06FC: 'ported from reading; tests/test_oracle_m8.py, the variant song data: a hold',
    0x0748: 'ported from reading; tests/test_oracle_m8.py, the variant song data: a sample of '
            'three octaves, a note in a lower one\'s part',
    0x07B0: 'ported from reading; tests/test_oracle_m8.py, note_start: the volume scaled while an '
            'effect of command 7 plays',
    0x0808: 'ported from reading; tests/test_oracle_m8.py, the note lookup: a note above the '
            'sample\'s octaves',
    0x0916: 'ported from reading; tests/test_oracle_m8.py, the level-4 handler: a channel an '
            'effect of command 7 has',
}

PLAYER_ORIG = re.compile(r'orig songplay\+(0x[0-9A-Fa-f]{4})')
PLAYER_STANDIN = re.compile(r'WOF_STANDIN\("((M\d+) STAND-IN: songplay(?:\+(0x[0-9A-Fa-f]{4}))?[^"]*)"\)')


def player_cold_table(data, names):
    """(Markdown rows, unclassified count): every region of a player routine src/music.c
    ports that no run executed, with the stand-in marker at its offset or its note from
    PLAYER_REGION_NOTES; then the markers of routines src/music.c does not port, and those
    that name no region."""
    import disasm_player
    import hunk
    code = bytes(hunk.load(disasm_player.PLAYER, bases=disasm_player.BASES)[0]['data'])
    spans = player_spans()
    starts = sorted(spans)
    with open(os.path.join(ROOT, 'src', 'music.c')) as handle:
        text = handle.read()
    ported = set()
    for m in PLAYER_ORIG.finditer(text):
        offset = int(m.group(1), 16)
        i = bisect.bisect_right(starts, offset) - 1
        if i >= 0:
            ported.add(starts[i])
    markers = [(int(m.group(3), 16) if m.group(3) else None, m.group(1), m.group(2))
               for m in PLAYER_STANDIN.finditer(text)]
    seen = set()
    for name in names:
        for w, p, offset, size, n in data[name].get('player_blocks', ()):
            seen.update(range(offset, offset + size))
    md = Cs(CS_ARCH_M68K, CS_MODE_M68K_000)
    rows = ['| Routine | Region no run executed | Stand-in marker, or what it is | Owed to |',
            '|---|---|---|---|']
    used, unclassified = set(), 0
    for start in sorted(ported):
        span, name = spans[start]
        cold, first = [], None
        for ins in md.disasm(code[start:start + span], start):
            if ins.address in seen:
                if first is not None:
                    cold.append((first, ins.address))
                    first = None
            elif first is None:
                first = ins.address
        if first is not None:
            cold.append((first, start + span))
        for lo, hi in cold:
            inside = [mk for mk in markers if mk[0] is not None and lo <= mk[0] < hi]
            where, region = '`%s` `%04x`' % (name, start), '`%04x`-`%04x`' % (lo, hi - 1)
            if inside:
                for mk in inside:
                    used.add(mk)
                    rows.append('| %s | %s | %s | %s |' % (where, region,
                                                             code_words(mk[1].split(': ', 1)[1]), mk[2]))
            elif lo in PLAYER_REGION_NOTES:
                rows.append('| %s | %s | %s | |' % (where, region, code_words(PLAYER_REGION_NOTES[lo])))
            else:
                unclassified += 1
                rows.append('| %s | %s | **unclassified** | |' % (where, region))
    for mk in sorted((m for m in markers if m not in used), key=lambda m: (m[0] is None, m[0] or 0)):
        if mk[0] is None:
            where = 'no region: a value'
        elif bisect.bisect_right(starts, mk[0]) - 1 >= 0 and \
                starts[bisect.bisect_right(starts, mk[0]) - 1] not in ported:
            where = 'a routine not ported, never entered'
        else:
            where = 'run by the original'
        rows.append('| | %s | %s | %s |' % (where, code_words(mk[1].split(': ', 1)[1]), mk[2]))
    return rows, unclassified


def sound_markdown(data, names):
    """The reach map of the sound effects engine: per part of the run, every routine of the
    engine that was entered, with its entries summed over M4's, M5's and M6's scripts, and
    the number of scripts that entered it."""
    import m5_scripts
    import m6_scripts
    table = routines()
    names = [n for n in names if not n.startswith('setup-')]
    groups = [('M4', [n for n in names if n not in m5_scripts.SCRIPTS and n not in m6_scripts.SCRIPTS]),
              ('M5', [n for n in names if n in m5_scripts.SCRIPTS]),
              ('M6', [n for n in names if n in m6_scripts.SCRIPTS])]
    current = {address: name for address, _, name in table}

    def where(routine):
        """A routine's address by the name a saved run recorded it under, which may be the
        listing's automatic sub_ name of a routine named since."""
        name = routine.split(':')[0]
        found = address_of(name, table)
        if not found and name.startswith('sub_'):
            found = name[4:]
        return int(found or '0', 16)

    lines = []
    for title, windows, phase in LISTS:
        rows = table_rows(data, names, windows, phase)
        rows = {r: v for r, v in rows.items() if where(r) in SOUND_ROUTINES and any(v)}
        if not rows:
            continue
        lines.append('### %s' % code_words(title))
        lines.append('')
        lines.append('| Routine | Address | ' + ' | '.join('%s (%d)' % (g, len(m)) for g, m in groups)
                     + ' | Runs |')
        lines.append('|---|---|' + '---|' * (len(groups) + 1))
        for routine in sorted(rows, key=lambda r: (where(r), r)):
            values = dict(zip(names, rows[routine]))
            lines.append('| `%s` | `%06x` | %s | %d |' % (
                current.get(where(routine), routine), where(routine),
                ' | '.join(str(sum(values[n] for n in m)) for _, m in groups),
                sum(1 for n in names if values[n])))
        lines.append('')
    return lines


def report(data, names):
    for title, windows, phase in LISTS:
        rows = table_rows(data, names, windows, phase)
        print('\n== %s ==' % title)
        print('%-36s %-7s %s' % ('routine', 'address', '  '.join('%8s' % n for n in names)))
        table = routines()
        for routine in sorted(rows, key=lambda r: (address_of(r.split(':')[0], table), r)):
            print('%-36s %-7s %s' % (routine, address_of(routine.split(':')[0], table),
                                     '  '.join('%8d' % v for v in rows[routine])))
    print('\n== entropy reads by caller ==')
    for name in names:
        for w, p, r, n in data[name]['draws']:
            print('  %-9s %-12s %s %-28s %d' % (name, w, p, r, n))
    print('\n== line_draw ==')
    for name in names:
        calls = collections.Counter((c[0], c[1], c[2], c[3]) for c in data[name]['line_calls'])
        print('  %-9s %s' % (name, dict(calls) or 'never'))
    print('\n== writes of view_step ==')
    for name in names:
        writes = collections.Counter((c[0], c[1], c[2], c[3]) for c in data[name]['view_step_writes'])
        print('  %-9s %s' % (name, dict(writes)))
    print('\n== night_flag, mission_number, rank at step S ==')
    for name in names:
        print('  %-9s %s' % (name, data[name]['night']))
    first = data[names[0]].get('self_looping')
    if first:
        print('\nroutines that branch to their own first instruction:', ', '.join(first))


def main():
    parser = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    parser.add_argument('--runs', nargs='*', default=M4_SCRIPTS)
    parser.add_argument('--part2', action='store_true',
                        help="part 2's scripts, the night mission and the key runs")
    parser.add_argument('--m5', action='store_true',
                        help="M5's scripts (tools/m5_scripts.py) beside every script of M4")
    parser.add_argument('--m5-only', action='store_true', help="M5's scripts alone")
    parser.add_argument('--m6', action='store_true',
                        help="M6's scripts (tools/m6_scripts.py) beside every script of M4 and M5")
    parser.add_argument('--m6-only', action='store_true', help="M6's scripts alone")
    parser.add_argument('--m7', action='store_true',
                        help="M7's scripts (tools/m7_scripts.py) beside every script of M4 to M6")
    parser.add_argument('--m7-only', action='store_true', help="M7's scripts alone")
    parser.add_argument('--jobs', type=int, default=1,
                        help='run the scripts in this many processes')
    parser.add_argument('--load', nargs='+',
                        help='take the runs from REACH.json files instead of running them')
    parser.add_argument('--markdown')
    parser.add_argument('--sound-markdown', default=None,
                        help='the tables of the sound engine\'s routines (M8), summed by milestone')
    parser.add_argument('--player-markdown', default=None,
                        help='the table of the music player\'s routines (M8 part 2)')
    parser.add_argument('--json')
    parser.add_argument('--blocks', action='store_true',
                        help='also record every basic block executed, by window and phase (slow)')
    parser.add_argument('--setups', action='store_true',
                        help='also the setups of all fifteen maps under their own numbers, to S')
    args = parser.parse_args()
    if args.part2:
        args.runs = PART2_SCRIPTS
    if args.m5:
        args.runs = PART2_SCRIPTS + m5_scripts_list()
    if args.m5_only:
        args.runs = m5_scripts_list()
    if args.m6:
        args.runs = PART2_SCRIPTS + m5_scripts_list() + m6_scripts_list()
    if args.m6_only:
        args.runs = m6_scripts_list()
    if args.m7:
        args.runs = PART2_SCRIPTS + m5_scripts_list() + m6_scripts_list() + m7_scripts_list()
    if args.m7_only:
        args.runs = m7_scripts_list()
    if args.load:
        data = {}
        for path in args.load:
            with open(path) as handle:
                data.update(json.load(handle))
        wanted = args.runs if (args.m5 or args.m5_only or args.m6 or args.m6_only or
                               args.m7 or args.m7_only or args.part2) else list(data)
        data = {name: data[name] for name in wanted if name in data}
        args.runs = list(data)
    else:
        data = collect(args.runs, blocks=args.blocks, setups=args.setups, jobs=args.jobs)
    report(data, args.runs)
    if args.sound_markdown:
        with open(args.sound_markdown, 'w') as f:
            f.write('\n'.join(sound_markdown(data, args.runs)) + '\n')
        print('%s written' % args.sound_markdown)
    if args.player_markdown:
        with open(args.player_markdown, 'w') as f:
            f.write('\n'.join(player_markdown(data, args.runs)) + '\n')
        print('%s written' % args.player_markdown)
    if args.markdown:
        with open(args.markdown, 'w') as f:
            f.write('\n'.join(markdown(data, args.runs)) + '\n')
        print('%s written' % args.markdown)
    if args.json:
        with open(args.json, 'w') as f:
            json.dump(data, f, indent=0)
        print('%s written' % args.json)
    return 0



# ---------------------------------------------------------------- coverage inside routines

def instructions(machine_or_oracle, address, span):
    """The instructions of one routine: (address, size, text)."""
    md = Cs(CS_ARCH_M68K, CS_MODE_M68K_000)
    code = machine_or_oracle.read(address, span)
    return [(ins.address, ins.size, '%s %s' % (ins.mnemonic, ins.op_str))
            for ins in md.disasm(code, address)]


def executed(data, names, windows, phases):
    """Every instruction address a basic block of the given windows and phases covered."""
    seen = set()
    for name in names:
        for w, p, address, size, n in data[name].get('blocks', ()):
            if w in windows and p in phases:
                seen.update(range(address, address + size))
    return seen


def cold_ranges(oracle, data, names, routine, windows=('mission',), phases=('F',)):
    """(instructions executed, instructions in all, [(start, end) never executed])."""
    table = {n: (a, s) for a, s, n in routines()}
    address, span = table[routine]
    seen = executed(data, names, windows, phases)
    code = instructions(oracle, address, span)
    hot = [a for a, _, _ in code if a in seen]
    cold, start = [], None
    for a, size, _ in code:
        if a in seen:
            if start is not None:
                cold.append((start, a))
                start = None
        elif start is None:
            start = a
    if start is not None:
        cold.append((start, address + span))
    return len(hot), len(code), cold


# ------------------------------------------------ the cold regions of the ported routines

# M4's routines: every one a port file names with an `orig 0x......` comment, and of the
# files that hold M3's too, the routines M4 changed.
PORT_FILES = ['src/mission.c', 'src/world.c', 'src/dash.c', 'src/tick.c', 'src/player.c',
              'src/objects.c', 'src/targets.c', 'src/pools.c', 'src/enemy.c', 'src/sound.c']
M4_IN_OTHER_FILES = ['main', 'run_queued_ticks', 'ingame_keys', 'vblank_server', 'line_draw',
                     'wait_next_vblank', 'screen_game_restore',
                     # M7 part 1's saved game, beside M3's dialog in src/dialog.c
                     'save_game_write', 'save_walk', 'save_write_part', 'save_nothing',
                     # M7 part 2's loaded game and demo
                     'save_game_read', 'save_read_part', 'demo_end']
MARKER_FILES = PORT_FILES + ['src/front.c', 'src/input.c', 'src/draw.c', 'src/dialog.c']
STANDIN = re.compile(r'WOF_STANDIN\("((M\d+(?: PART \d)?) STAND-IN: '
                     r'(?:(0x[0-9A-Fa-f]{6})(?:-(0x[0-9A-Fa-f]{6}))?, )?([^"]*))"\)')
ORIG = re.compile(r'orig (0x[0-9A-Fa-f]{6})')

# What a region no script ran and no marker stands for is, by its first address.  Every
# such region must be named here: the table marks any other one as unclassified, and
# --cold then fails.
REGION_NOTES = {
    # M6 part 2: the tick's regions no script runs, each reached by the cases of an oracle test
    # (tests/test_oracle_m6.py asserts that its cases execute every one of them).
    0x011D28: 'ported from reading; tests/test_oracle_m6.py, the ships sinking: the last enemy '
              'ship sunk with no island left, the mission won',
    0x011D3A: 'ported from reading; tests/test_oracle_m6.py, the ships sinking: the carrier a row '
              'deeper with the player aboard, back on the lift',
    0x011D7E: 'ported from reading; tests/test_oracle_m6.py, the ships sinking: the carrier 0x21 '
              'rows down with the aircraft on its deck, into the sea',
    0x01B6C8: 'ported from reading; tests/test_oracle_m6.py, the guns at an enemy aircraft east '
              'of the player',
    0x01CBEE: 'ported from reading; tests/test_oracle_m6.py, an aircraft at rest on a record that '
              'is not land',
    0x01D6BE: 'ported from reading; tests/test_oracle_m6.py, a fighter\'s turn reversed behind '
              'the player while he turns',
    0x01D6EE: 'ported from reading; tests/test_oracle_m6.py, a fighter\'s turn reversed east of '
              'the player while he turns',
    0x01D742: 'the jump table of aircraft_turn\'s switch: data, not code',
    0x01DB86: 'ported from reading; tests/test_oracle_m6.py, a fighter ahead of the player hit '
              'by the guns: its evasion',
    0x01DCAC: 'the jump table of fighter_cruise\'s switch: data, not code',
    0x01DF8C: 'ported from reading; tests/test_oracle_m6.py, a torpedo plane flying west turning '
              '500 past the deck',
    0x01E3D2: 'ported from reading; tests/test_oracle_m6.py, a fighter shot down and freed off '
              'land: one fewer up',
    0x01E404: 'ported from reading; tests/test_oracle_m6.py, a wreck burning facing east',
    0x01E4C8: 'ported from reading; tests/test_oracle_m6.py, state 1, which nothing sets',
    0x01E504: 'ported from reading; tests/test_oracle_m6.py, a torpedo plane already up when '
              'another is launched',
    0x01E71A: 'unreachable: slowing towards a want speed of at least 900 lands half the gap and '
              '5 above it',
    0x01E7BA: 'ported from reading; tests/test_oracle_m6.py, a mode that is none of the four',
    0x01E7D0: 'ported from reading; tests/test_oracle_m6.py, a mode that is none of the four',
    0x01E84E: 'ported from reading; tests/test_oracle_m6.py, state 1, which nothing sets',
    0x01E866: 'ported from reading; tests/test_oracle_m6.py, state 8, which nothing sets',
    0x01E87E: 'ported from reading; tests/test_oracle_m6.py, a state that is none of the five',
    0x010196: 'ported from reading: a paused mission waits for the next VBlank',
    0x01020A: 'ported from reading: back to the outer loop after the high scores',
    0x010322: 'ported from reading: the flash of flip_buffers',
    0x01043E: 'unreachable: no branch leads there',
    0x0104D4: 'ported from reading: the climb clamped at -2 in the eighth-scale view',
    0x01058C: 'ported from reading',
    0x0106CC: 'ported from reading: 0x02536C cleared',
    0x0106F6: 'ported from reading: the extra object record drawn',
    0x011118: 'ported from reading; tests/test_oracle_m4.py, every count',
    0x0111FC: 'ported from reading; reached only between two missions, part 2',
    0x0114EE: 'ported from reading: nothing runs while paused',
    0x011856: 'ported from reading; tests/test_oracle_m4.py, the ticker',
    0x0118DE: 'ported from reading; tests/test_oracle_m4.py, the ticker',
    0x012B80: 'an allocation failed, fatal; the port\'s tables are fixed (src/mission.def)',
    0x012BF6: 'ported from reading: a ship released at the end of a mission',
    0x012C1A: 'ported from reading: a ship released at the end of a mission',
    0x012C3E: 'ported from reading: a ship released at the end of a mission',
    0x012C62: 'ported from reading: a ship released at the end of a mission',
    0x0130AE: 'an allocation failed, fatal; the port\'s tables are fixed (src/mission.def)',
    0x01327C: 'battleship.shp missing from the disk; the port loads every container at start-up',
    0x0132C4: 'destroyer.shp missing, fatal; the port loads every container at start-up',
    0x0132FE: 'cruiseship.shp missing, fatal; the port loads every container at start-up',
    0x013346: 'japcarrier.shp missing, fatal; the port loads every container at start-up',
    0x013516: 'ported from reading: nothing for a loaded game',
    0x01382E: 'ported from reading: records before the map\'s start stepped over',
    0x0138F2: 'ported from reading: the distance handed to the sound engine',
    0x013ADA: 'ported from reading: more than nine lives count as nine',
    0x014390: 'ported from reading: the shore line of the 3-D view',
    0x0143AE: 'ported from reading: a record of class 6 to 8 in the 3-D view',
    0x0143E6: 'ported from reading: a record in the 3-D view',
    0x014A5A: 'ported from reading; tests/test_oracle_m4.py, ship_at_offset',
    0x014A78: 'ported from reading; tests/test_oracle_m4.py, ship_at_offset',
    0x014A96: 'ported from reading; tests/test_oracle_m4.py, ship_at_offset',
    0x014AB4: 'ported from reading; tests/test_oracle_m4.py, ship_at_offset',
    0x014AE0: 'ported from reading; tests/test_oracle_m4.py, ship_at_offset',
    0x014D92: 'reached only when 0x014DB8 gives a frame, after its stand-ins (M5)',
    0x014DD6: 'ported from reading: no frame for a target far ahead',
    0x016568: 'dash.shp missing, fatal; the port loads every container at start-up',
    0x01CB50: 'ported from reading: a record at the list\'s end is on no ship',
    0x01CB70: 'ported from reading: a record of other low bits is on no ship',
    0x01EDF4: 'ported from reading; tests/test_oracle_m4.py, the gauge resets',
    0x01EDFE: 'ported from reading; tests/test_oracle_m4.py, the gauge resets',
    0x01EF68: 'ported from reading: the fuel needle moving down',
    0x01F1DA: 'ported from reading: the first row of bars clamped at seven',
    0x01F1EE: 'ported from reading: the second row of bars clamped at seven',
    # part 2: the tick, the player and what they reach
    0x0102BC: 'ported from reading: player_lost_restart from frame_update, when 0x024F24 is '
              'set, which no instruction of the executable does',
    0x0105F0: "ported from reading: the cable's end when the aircraft faces right",
    0x010840: 'ported from reading: all fifteen object records in use, nothing is left',
    0x01088E: "another entry, the weapon's launch from 0x01107C: M5's, behind the stand-in at "
              '0x01B5E2',
    0x010A9E: 'ported from reading: the extra object record walked as the others are',
    0x0112D4: 'ported from reading: the cursor keys and Return in the weapon menu',
    0x0112DE: 'ported from reading: the cursor keys and Return in the weapon menu',
    0x0112E8: 'ported from reading: the cursor keys and Return in the weapon menu',
    0x0112F2: 'ported from reading: the cursor keys and Return in the weapon menu',
    0x011572: 'ported from reading: nothing is launched while 0x027348 counts down',
    0x0121D8: "the sound slots (M8): an enemy aircraft's distance for its engine",
    0x01221E: "the sound slots (M8): an enemy aircraft's distance for its engine",
    0x01383A: "ported from reading: records before the map's start stepped over",
    0x013900: 'ported from reading: the distance handed to the sound engine',
    0x014244: 'ported from reading: the 3-D view over an enemy ship whose +0x12 is 6000',
    0x01435C: 'ported from reading: a record of class 6 to 8 in the 3-D view',
    0x014382: 'ported from reading: land in the 3-D view, which draws the shore line',
    0x0145EE: 'ported from reading: the shape of a record in the 3-D view',
    0x01460A: 'ported from reading: the shape of a record in the 3-D view',
    0x01461A: 'ported from reading: the shape of a ship in the 3-D view facing right',
    0x01464C: "ported from reading: an enemy ship's own shapes in the 3-D view",
    0x014662: "ported from reading: an enemy ship's own shapes in the 3-D view",
    0x01467E: 'ported from reading: the shape of a record in the 3-D view',
    0x01547A: 'ported from reading: all forty smoke records in use, nothing is left',
    0x015866: "ported from reading; tests/test_oracle_m4.py, every record of five maps",
    0x016D32: 'ported from reading: the play screen back after the save or the load dialog',
    0x01AA9A: 'ported from reading; tests/test_oracle_m4.py, an enemy aircraft that stops a turn',
    0x01AF16: "ported from reading: the burning wreck's smoke",
    0x01AFFC: 'ported from reading; tests/test_oracle_m4.py, the aircraft down on land or a ship',
    0x01B070: 'ported from reading; tests/test_oracle_m4.py, the aircraft down on land',
    0x01B1B4: 'ported from reading; tests/test_oracle_m4.py, the aircraft down on a ship',
    0x01B1D4: 'ported from reading; tests/test_oracle_m4.py, the attitude levelling out',
    0x01B200: 'ported from reading; tests/test_oracle_m4.py, a wreck sliding along a ship',
    0x01B40C: 'ported from reading; tests/test_oracle_m4.py, a wreck at rest on land or a ship',
    0x01B430: 'ported from reading; tests/test_oracle_m4.py, a wreck at rest on land or a ship',
    0x01B4A8: 'ported from reading; tests/test_oracle_m4.py, the hook with the carrier sunk',
    0x01B538: 'ported from reading; tests/test_oracle_m4.py, on the lift facing right',
    0x01B582: 'ported from reading; tests/test_oracle_m4.py, short of the lift',
    0x01B5EE: "ported from reading; tests/test_oracle_m4.py, the guns firing (their bullets "
              "are M5's, the stand-in at 0x0119C4)",
    0x01BB68: 'ported from reading; tests/test_oracle_m4.py, a bounce off the deck',
    0x01BC1A: "ported from reading; tests/test_oracle_m4.py, the enemy's countdown far east",
    0x01BCEA: 'ported from reading; tests/test_oracle_m4.py, the deck state',
    0x01BD7A: 'ported from reading; tests/test_oracle_m4.py, the deck state',
    0x01BF84: 'ported from reading; tests/test_oracle_m4.py, player_motion',
    0x01BFE8: 'ported from reading; tests/test_oracle_m4.py, player_motion',
    0x01C074: 'ported from reading; tests/test_oracle_m4.py, the stick in the air',
    0x01C09C: 'ported from reading; tests/test_oracle_m4.py, the stick in the air',
    0x01C12E: 'ported from reading; tests/test_oracle_m4.py, the stick in the air',
    0x01C200: 'ported from reading; tests/test_oracle_m4.py, the stick in the air',
    0x01C2A0: 'ported from reading; tests/test_oracle_m4.py, the stick in the air',
    0x01C326: 'ported from reading; tests/test_oracle_m4.py, the stick in the air',
    0x01C5E6: 'ported from reading; tests/test_oracle_m4.py, the stick on the deck',
    0x01C6E8: 'ported from reading: the aircraft below the sea without a crash',
    0x01C7C6: 'ported from reading: the burning wreck (state 8), which a crash on land leaves',
    0x01C8EE: 'ported from reading: state 9 does nothing',
    0x01C934: "the player update's jump table: data",
    0x01C98C: 'ported from reading; tests/test_oracle_m4.py, record_at left of the map',
    0x01CAB4: "ported from reading: the sky's flash, which a crash on a ship sets",
    0x01CAE0: 'ported from reading: smoke from the burning wreck',
    0x01CBAE: 'ported from reading; tests/test_oracle_m4.py, on_water',
    0x01CC04: 'ported from reading: a debugging line to the console, and 1',
    0x01CC68: 'ported from reading: a debugging line to the console, and 1',
    0x01CD92: 'ported from reading: the save dialog on the carrier',
    0x01CE0A: 'ported from reading: the load dialog cancelled',
    0x01CE26: "the crash reporter of Control-B, which the port does not have (re/notes/keys.md)",
    0x01EEB8: "ported from reading: the oil warning's blink",
    0x01F102: 'ported from reading: negative lives count as none',
    0x01F10C: 'ported from reading: more than nine lives count as nine',
    0x01F12E: 'ported from reading: the lives drum turning down, a life more',
    0x021342: 'ported from reading, PROVISIONAL: the clipping of line_draw',
    0x021354: 'ported from reading, PROVISIONAL: the clipping of line_draw',
    0x02136A: 'ported from reading, PROVISIONAL: the clipping of line_draw',
    0x02137C: 'ported from reading, PROVISIONAL: the clipping of line_draw',
    0x02138E: 'ported from reading, PROVISIONAL: the clipping of line_draw',
    0x021556: "the blitter's busy wait, which the port's line has none of",
    0x0215D0: 'ported from reading, PROVISIONAL: a line wholly outside the clip',
    # M5 part 1: the pass's regions of the targets, the soldiers and the pools that no script
    # of either milestone ran (re/notes/porting-m5.md, "Appendix: the regions no run executed")
    0x010752: 'ported from reading: the torpedo drawn facing the other way (+0x1F negative)',
    0x0118EC: "ported from reading; tests/test_oracle_m4.py, the ticker: a message's end",
    0x011EF2: 'ported from reading: every soldier record in use, nobody comes out',
    0x011F42: "ported from reading: a dug-out's soldier turned round by rand_beam",
    0x013B68: "ported from reading: an island's flag with the player past the island's end",
    0x013FA8: 'ported from reading: an island neutralised that is not the map\'s last',
    0x013FE8: 'ported from reading: a soldier turning round at the water',
    0x014694: 'ported from reading: the shape of a record in the 3-D view',
    0x014B88: 'ported from reading: no draw record among the four, no target',
    0x014BC6: 'ported from reading: a burnt barracks not in the table, no target',
    0x014BF4: 'ported from reading: a dug-out not in the table, no target',
    0x014C2C: 'ported from reading: a pillbox not in the table, no target',
    0x014C3A: 'ported from reading: another slot, no target',
    0x014DCA: 'unreachable from target_frame, which takes the eighth-scale view itself; '
              'ship_guns_draw (M6) is its other caller',
    0x01501E: 'ported from reading: the barracks east of the dug-out, its soldier runs west',
    0x015060: 'ported from reading: the barracks west of the dug-out, the distance negated',
    0x015624: "ported from reading: an island neutralised that is not the map's last, its "
              'message (0x015624)',
    0x01F0A4: "ported from reading: the weapon counter's tens drum round after 0x50",
    # M5 part 2: the tick's regions no script reaches, held by tests/test_oracle_m5.py
    0x01081A: 'ported from reading: no weapon left or every object record in use, nothing '
              'is dropped; tests/test_oracle_m5.py, the drop',
    0x010970: "ported from reading: a rocket's frame from the bearing, clamped at 0; "
              'tests/test_oracle_m5.py, the drop',
    0x010A16: 'ported from reading: a rocket aimed at a pillbox or a ship\'s gun under its '
              "bearing, which no script's rocket found; tests/test_oracle_m5.py, the objects' step",
    0x010B1E: "ported from reading: a rocket's reach in the eighth-scale view; "
              "tests/test_oracle_m5.py, the objects' step",
    0x010B3C: "ported from reading: a rocket out of reach is freed; tests/test_oracle_m5.py, "
              "the objects' step",
    0x010B94: "ported from reading: a weapon over an airfield, which no script's weapon came "
              "down on; tests/test_oracle_m5.py, the objects' step",
    0x010C12: 'ported from reading: a weapon over a record of low bits 3; '
              "tests/test_oracle_m5.py, the objects' step",
    0x010C36: "ported from reading: a weapon over a ship's deck (low bits 1); 0x010C36 to "
              '0x010C53, the test of low bits 2 for 3 and 4, is unreachable; '
              "tests/test_oracle_m5.py, the objects' step",
    0x010D26: 'ported from reading: a torpedo that meets the sea slowly flying left runs '
              "left; tests/test_oracle_m5.py, the objects' step",
    0x010D46: 'unreachable: +0x1A was set from pass_counter a few instructions before, so the '
              'splash at the start of a run is never made',
    0x010D7C: "ported from reading: a running torpedo meets land or a ship; "
              "tests/test_oracle_m5.py, the objects' step",
    0x011138: "ported from reading: an airfield record with a span, which maps a to c have none "
              "of; tests/test_oracle_m5.py, the objects' step",
    0x01119E: "ported from reading: a standing pillbox found under a rocket's bearing; "
              "tests/test_oracle_m5.py, the objects' step",
    0x0111C8: "ported from reading: a ship afloat with guns under a rocket's bearing (M6's "
              "ships); tests/test_oracle_m5.py, the objects' step",
    0x011A58: "ported from reading: a bearing of 0xFF01, taken as 0xFF02; "
              "tests/test_oracle_m5.py, the guns' reach",
    0x011A7C: "ported from reading: a level or upward bearing reaches no ground; "
              "tests/test_oracle_m5.py, the guns' reach",
    0x011B08: "ported from reading: a torpedo west of the span; tests/test_oracle_m5.py, the "
              "soldiers' and torpedoes' hits",
    0x011B30: "ported from reading: the extra object record hit; tests/test_oracle_m5.py, the "
              "soldiers' and torpedoes' hits",
    0x011E6E: "ported from reading: a barracks' next soldier's timer from vblank_total, 0 "
              "counting as 3; tests/test_oracle_m5.py, the tick's routines",
    0x014722: "ported from reading: a hit on slot 0x113, which it leaves alone; "
              'tests/test_oracle_m5.py, the hits',
    0x014788: "ported from reading: the draw bit on another of the barracks' records than the "
              'third (D1, which nothing reads); tests/test_oracle_m5.py, the hits',
    0x0147A8: "ported from reading: the draw bit on another of the barracks' records than the "
              'third (D1, which nothing reads); tests/test_oracle_m5.py, the hits',
    0x0147E8: "ported from reading: the draw bit on another of the barracks' records than the "
              'third (D1, which nothing reads); tests/test_oracle_m5.py, the hits',
    0x01493A: "ported from reading: an island's last pillbox destroyed with no soldier left; "
              'tests/test_oracle_m5.py, the hits',
    0x014992: "ported from reading: a weapon's hit on a ship (M6's ships); "
              'tests/test_oracle_m5.py, the hits',
    0x015122: 'ported from reading: an angle in the second quarter; tests/test_oracle_m5.py, '
              'the angles',
    0x015156: 'ported from reading: a negative angle; tests/test_oracle_m5.py, the angles',
    0x01516C: 'ported from reading: a negative angle; tests/test_oracle_m5.py, the angles',
    0x015CA6: 'ported from reading: the angle of a vector, which only an aimed rocket asks '
              'for; tests/test_oracle_m5.py, the angles',
    0x01B00A: 'ported from reading (M4): the crash on a ship; tests/test_oracle_m4.py, the '
              'crash and the ground',
    0x01B0E2: 'ported from reading (M4): a wreck sliding along a ship; tests/test_oracle_m4.py, '
              'the crash and the ground',
    0x01B41A: 'ported from reading (M4): a wreck at rest on a ship; tests/test_oracle_m4.py, '
              'the crash and the ground',
    0x01B5DA: 'ported from reading: the click inside a turn (attitude 6 to 16) drops nothing',
    0x01BBBA: 'ported from reading (M4): a crash on a deck; tests/test_oracle_m4.py, the crash '
              'and the ground',
    0x01C80C: 'ported from reading (M4): the burning wreck on a ship; tests/test_oracle_m4.py',
    # M6 part 1: sub-regions of code M4 and M5 ported from reading, which the M6 scripts
    # reached in part (the rest is held by the oracle tests named and by part 2's closed loop)
    0x010C1A: 'ported from reading: a weapon over a record of low bits 3; '
              "tests/test_oracle_m5.py, the objects' step",
    0x01AABE: 'ported from reading; tests/test_oracle_m4.py, an enemy aircraft that stops a turn',
    0x01B134: 'ported from reading (M4): a wreck sliding along a ship; tests/test_oracle_m4.py, '
              'the crash and the ground',
    0x01B1A6: 'ported from reading (M4): a wreck sliding along a ship; tests/test_oracle_m4.py, '
              'the crash and the ground',
    0x01B1BA: 'ported from reading; tests/test_oracle_m4.py, the aircraft down on a ship',
    0x01B1DC: 'ported from reading; tests/test_oracle_m4.py, the attitude levelling out',
    0x01BD86: 'ported from reading; tests/test_oracle_m4.py, the deck state',
    # M7 part 2: the loader's two ways out of the program, each reached by the oracle.
    0x015D98: 'ported from reading; tests/test_oracle_m7.py, a block mem_alloc cannot give: '
              'exit_game; the port\'s pools are fixed and wof_save_game_fits refuses a file '
              'whose counts exceed them before the load, which the dialog leaves as a cancel',
    0x015E50: 'ported from reading; tests/test_oracle_m7.py, a file Open cannot open: IoErr, '
              'the message and exit_game; wof_save_game_fits refuses a missing file before '
              'the load, which the dialog leaves as a cancel',
    # M7 part 1: the saved game's writer.
    0x015EBE: 'ported from reading; tests/test_oracle_m7.py, a save that cannot be opened: '
              'nothing is walked or written and 0 comes back, which the dialog ignores; the '
              'port\'s file system refuses a file only when its overlay is full',
    # M8 part 1: the effects engine's regions no script runs (tests/test_oracle_m8.py).
    0x01ECBE: 'ported from reading; tests/test_oracle_m8.py, soundfx_vblank: the music\'s flags '
              'for channel 2, which only the uncalled 0x01E9F4 sets',
    0x01ECF8: 'ported from reading; tests/test_oracle_m8.py, soundfx_vblank: a volume eased to '
              'its target, which only the uncalled 0x01EB94 starts',
}


def ported_and_markers():
    """(routine start addresses of M4's routines, [(first, last, marker, milestone)]).  A
    marker names the first address of what it stands for, or a range."""
    table = sorted(routines())
    starts = [a for a, _, _ in table]
    ported, markers = set(), []
    for path in MARKER_FILES:
        with open(os.path.join(ROOT, path)) as handle:
            text = handle.read()
        if path in PORT_FILES:
            for m in ORIG.finditer(text):
                i = bisect.bisect_right(starts, int(m.group(1), 16)) - 1
                if i >= 0 and int(m.group(1), 16) < table[i][0] + max(table[i][1], 2):
                    ported.add(table[i][0])
        for m in STANDIN.finditer(text):
            first = int(m.group(3), 16) if m.group(3) else None
            last = int(m.group(4), 16) if m.group(4) else first
            markers.append((first, last, m.group(1), m.group(2)))
    ported.update(a for a, _, n in table if n in M4_IN_OTHER_FILES)
    return ported, markers


def cold_table(data, names):
    """(Markdown rows, unclassified count): every region of an M4 routine that no run
    executed in any window or phase, with the stand-in marker whose address or range covers
    it, or its note from REGION_NOTES; then the markers whose region the original did run
    (the port stands in there although a script reached it in the original's tick, or on a
    value no script produced), and the markers that name no region."""
    import oracle as oracle_module
    o = oracle_module.Oracle()
    windows = {w for name in names for w, _, _, _, _ in data[name]['blocks']}
    phases = {p for name in names for _, p, _, _, _ in data[name]['blocks']}
    table = {a: (s, n) for a, s, n in routines()}
    ported, markers = ported_and_markers()
    rows = ['| Routine | Region no run executed | Stand-in marker, or what it is | Owed to |',
            '|---|---|---|---|']
    used, unclassified = set(), 0

    def text(marker):
        return marker.split(': ', 1)[1]

    for start in sorted(ported):
        span, name = table[start]
        if span <= 0:
            continue
        hot, total, cold = cold_ranges(o, data, names, name, windows, phases)
        for lo, hi in cold:
            inside = [mk for mk in markers if mk[0] is not None and
                      (lo <= mk[0] < hi or mk[0] <= lo <= mk[1])]
            where = '`%s` `0x%06X`' % (name, start)
            region = '`0x%06X`-`0x%06X`' % (lo, hi - 1)
            if inside:
                for mk in inside:
                    used.add(mk)
                    rows.append('| %s | %s | %s | %s |' % (where, region, code_words(text(mk[2])),
                                                             mk[3]))
            elif lo in REGION_NOTES:
                rows.append('| %s | %s | %s | |' % (where, region, code_words(REGION_NOTES[lo])))
            else:
                unclassified += 1
                rows.append('| %s | %s | **unclassified** | |' % (where, region))
    for mk in sorted((m for m in markers if m not in used), key=lambda m: (m[0] is None, m[0] or 0)):
        where = 'run by the original' if mk[0] is not None else 'no region: a value'
        rows.append('| | %s | %s | %s |' % (where, code_words(text(mk[2])), mk[3]))
    return rows, unclassified


def cold_main(argv):
    parser = argparse.ArgumentParser(description='the cold regions of the ported routines')
    parser.add_argument('--cold', required=True, nargs='+',
                        help='REACH.json files written with --blocks; their runs are joined, so '
                             'the cold list covers the union of M4\'s and M5\'s scripts')
    args = parser.parse_args(argv)
    data = {}
    for path in args.cold:
        with open(path) as handle:
            data.update(json.load(handle))
    rows, unclassified = cold_table(data, sorted(data))
    print('\n'.join(rows))
    if any(data[n].get('player_blocks') for n in data):
        rows, more = player_cold_table(data, sorted(data))
        print()
        print('The music player (src/music.c):')
        print()
        print('\n'.join(rows))
        unclassified += more
    if unclassified:
        print('%d regions are unclassified: give each a marker or a REGION_NOTES entry'
              % unclassified, file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    if '--cold' in sys.argv:
        sys.exit(cold_main(sys.argv[1:]))
    sys.exit(main())
