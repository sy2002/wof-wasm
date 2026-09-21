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

An entry is the execution of a routine's first instruction.  A routine that branches back
to its own first instruction would count each round; the tool finds those statically and
names them.  A routine that another one falls into is entered by the fall, which is how
frame_update reaches flip_buffers.
"""
import argparse
import collections
import csv
import json
import os
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

    def _block(self, uc, address, size, user):
        self.blocks[(self.window, self.phase(), address, size)] += 1

    def _mark(self, uc, address, size, user):
        self.window = WINDOW_MARKS[address]

    def _entry(self, uc, address, size, user):
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


def observe(name, verbose=True, blocks=False, **more):
    started = time.time()
    machine = Reach(pass_observe.script(name, **more), blocks=blocks)
    machine.run()
    if verbose:
        print('%-9s %5d VBlanks, %5d passes, %4d ticks, %d missions, %d entropy reads  (%.0f s)'
              % (name, machine.vblanks, machine.passes, machine.ticks, machine.missions,
                 len(machine.entropy_log), time.time() - started))
    return machine


def collect(names, verbose=True, blocks=False):
    out = {}
    for name in names:
        m = observe(name, verbose=verbose, blocks=blocks)
        out[name] = {
            'entries': [[w, p, r, n] for (w, p, r), n in sorted(m.entries.items())],
            'draws': [[w, p, r, n] for (w, p, r), n in sorted(m.draws.items())],
            'line_calls': m.line_calls,
            'view_step_writes': m.view_step_writes,
            'night': m.night,
            'counters': {'vblanks': m.vblanks, 'passes': m.passes, 'ticks': m.ticks,
                         'missions': m.missions, 'entropy': len(m.entropy_log)},
            'self_looping': self_looping(m, m.table) if name == names[0] else None,
            'blocks': [[w, p, a, size, n] for (w, p, a, size), n in sorted(m.blocks.items())],
        }
    return out


# The lists the M4 task asks for, as (title, window, phase).
LISTS = [
    ('The head of the outer loop, before the rank selection', ('outer',), 'M'),
    ('After the rank selection, before the briefing', ('pre-briefing',), 'M'),
    ('Mission setup, main program: the briefing\'s end to step S', ('setup',), 'M'),
    ('Mission setup, the tick main runs itself (part 2)', ('setup',), 'T'),
    ('Mission setup, VBlank servers', ('setup',), 'V'),
    ('A pass during a mission: frame_update\'s tree (phase F)', ('mission',), 'F'),
    ('A VBlank during a mission (phase V)', ('mission',), 'V'),
    ('The inner loop beside frame_update during a mission (phase M)', ('mission',), 'M'),
    ('The tick during a mission (phase T, part 2)', ('mission',), 'T'),
]


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
        lines.append('### %s' % title)
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
    lines.append('### Entropy reads, by the routine that called rand_beam')
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
    parser.add_argument('--markdown')
    parser.add_argument('--json')
    parser.add_argument('--blocks', action='store_true',
                        help='also record every basic block executed, by window and phase (slow)')
    args = parser.parse_args()
    data = collect(args.runs, blocks=args.blocks)
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


if __name__ == '__main__':
    sys.exit(main())


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
