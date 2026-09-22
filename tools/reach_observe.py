"""The reach map of milestone M4: which routines the original enters, where, and how often.

M4 ports what the five mission scripts of tools/pass_observe.py reach and marks everything
else as a stand-in.  This tool runs each script under the headless original with a code
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

An entry is the execution of a routine's first instruction.  A routine that branches back
to its own first instruction would count each round; the tool finds those statically and
names them.  A routine that another one falls into is entered by the fall, which is how
frame_update reaches flip_buffers.
"""
import argparse
import bisect
import collections
import csv
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

    _last_entry = None

    def _block(self, uc, address, size, user):
        self.blocks[(self.window, self.phase(), address, size)] += 1

    def _mark(self, uc, address, size, user):
        self.window = WINDOW_MARKS[address]

    def _entry(self, uc, address, size, user):
        # A slice that ran out of time can stop between this hook and its instruction; the
        # next slice runs the hook again for the same entry (tools/headless.py, _observe).
        stack = uc.reg_read(UC_M68K_REG_A7)
        if self._refire == address and self._last_entry == (address, stack):
            self._refire = None
            return
        self._last_entry = (address, stack)
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


def description_of(name, **more):
    import m4_scripts
    import m5_scripts
    if name.startswith('run:'):
        with open(os.path.join(ROOT, 'tests', 'runs', name[4:] + '.json')) as handle:
            description = json.load(handle)
        description.update(more)
        return description
    if name in m5_scripts.RUNS:
        return m5_scripts.script(name, **more)
    return m4_scripts.script('flight' if name == 'night' else name, **more)


def pokes_of(name):
    """{address: (size, value)} poked at the rank selection's end for a script."""
    import m5_scripts
    if name == 'night':
        return {NIGHT_POKE[0]: (2, NIGHT_POKE[1])}
    return m5_scripts.POKES.get(name, {})


def observe(name, verbose=True, blocks=False, **more):
    started = time.time()
    machine = Reach(description_of(name, **more), blocks=blocks)
    pokes = pokes_of(name)
    if pokes:
        machine.stop_at(0x01009E, lambda: [machine.o.write(a, v.to_bytes(s, 'big'))
                                           for a, (s, v) in pokes.items()])
    machine.run()
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
        m = make()
        out[name] = {
            'entries': [[w, p, r, n] for (w, p, r), n in sorted(m.entries.items())],
            'draws': [[w, p, r, n] for (w, p, r), n in sorted(m.draws.items())],
            'line_calls': m.line_calls,
            'view_step_writes': m.view_step_writes,
            'night': m.night,
            'counters': {'vblanks': m.vblanks, 'passes': m.passes, 'ticks': m.ticks,
                         'missions': m.missions, 'entropy': len(m.entropy_log)},
            'self_looping': self_looping(m, m.table) if names and name == names[0] else None,
            'blocks': [[w, p, a, size, n] for (w, p, a, size), n in sorted(m.blocks.items())],
        }
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
]


CODE_WORD = re.compile(r"(?<![`\w])((?:[A-Za-z][\w.]*_[\w.]*[\w])|(?:0x[0-9A-Fa-f]+))(?![`\w])")


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
    parser.add_argument('--jobs', type=int, default=1,
                        help='run the scripts in this many processes')
    parser.add_argument('--markdown')
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
    data = collect(args.runs, blocks=args.blocks, setups=args.setups, jobs=args.jobs)
    report(data, args.runs)
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
PORT_FILES = ['src/mission.c', 'src/world.c', 'src/dash.c', 'src/tick.c', 'src/player.c']
M4_IN_OTHER_FILES = ['main', 'run_queued_ticks', 'ingame_keys', 'vblank_server', 'line_draw',
                     'wait_next_vblank', 'screen_game_restore']
MARKER_FILES = PORT_FILES + ['src/front.c', 'src/input.c', 'src/draw.c', 'src/dialog.c']
STANDIN = re.compile(r'WOF_STANDIN\("((M\d+(?: PART \d)?) STAND-IN: '
                     r'(?:(0x[0-9A-Fa-f]{6})(?:-(0x[0-9A-Fa-f]{6}))?, )?([^"]*))"\)')
ORIG = re.compile(r'orig (0x[0-9A-Fa-f]{6})')

# What a region no script ran and no marker stands for is, by its first address.  Every
# such region must be named here: the table marks any other one as unclassified, and
# --cold then fails.
REGION_NOTES = {
    0x010036: "M3's: the command line's demo file, which the port has no command line for",
    0x010104: 'ported from reading: demo_mode sets 0x026D44 before step S',
    0x010196: 'ported from reading: a paused mission waits for the next VBlank',
    0x0101B4: 'ported from reading: a demo ends on the fire button',
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
    0x011508: 'ported from reading: demo_mode sets 0x026D44',
    0x011790: "M3's input half: demo playback (M7)",
    0x01180A: "M3's input half: demo recording (M7)",
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
    parser.add_argument('--cold', required=True, help='a REACH.json written with --blocks')
    args = parser.parse_args(argv)
    with open(args.cold) as handle:
        data = json.load(handle)
    rows, unclassified = cold_table(data, sorted(data))
    print('\n'.join(rows))
    if unclassified:
        print('%d regions are unclassified: give each a marker or a REGION_NOTES entry'
              % unclassified, file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    if '--cold' in sys.argv:
        sys.exit(cold_main(sys.argv[1:]))
    sys.exit(main())
