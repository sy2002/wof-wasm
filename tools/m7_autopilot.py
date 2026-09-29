"""The autopilot of M7: the campaign and the saved game, flown on the headless original.

tools/m6_autopilot.py flies one mission of any map.  M7 needs a mission that follows
another: a mission won goes on, in the hold, to the campaign's next one (main 0x010132 to
0x01018D), with the ticker's message, the fade, the next map, its briefing and its setup.
A plan here either starts from a script that already wins its mission, `after`, whose raw
schedule it replays up to the step S of the mission named by `switch` and 40 VBlanks into
its hold, and flies that mission with the plan of tools/m6_autopilot.py; or it flies a
mission of its own from the front end as an M6 plan does.  Beside the legs and the landing
of M6 a plan can save the game in the hold (`save`): Control-G, the dialog's cursor moved to
an empty slot, a name typed and Return, as the manual's page 11 has it; and poke at the point
where main has run map_load for a campaign's first mission (0x0100AE), which is how a map
is won as a rank's last mission (the promotion) and as the last rank's last one (the cap).

The choices after the switch, compressed into [VBlanks, letters, keys] runs, are the
script's tail; the script is the base's schedule cut at the switch with the tail behind it,
which the original flies again without the autopilot (tools/m7_scripts.py keeps them).

    .venv/bin/python tools/m7_autopilot.py PLAN            fly a plan of PLANS, print the tail
    .venv/bin/python tools/m7_autopilot.py --all           fly every plan, write tools/m7_runs.py

The script's VBlanks are the schedule's own: the VBlanks of the music's fades, in which the
harness holds the schedule (re/notes/headless.md, "The fade's wait"), are not the script's,
and the policy is not asked in them.  What each plan reaches is in re/notes/porting-m7.md,
"The scripts".
"""
import argparse
import json
import os
import pprint
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import headless                                              # noqa: E402
import m4_autopilot                                          # noqa: E402
import m5_autopilot                                          # noqa: E402
import m6_autopilot                                          # noqa: E402

s16 = m4_autopilot.s16
PLAYER = 0x025078
MISSION_NUMBER = 0x0253C0
RANK_PLAYED = 0x0253BE
RANK_END = 0x01009E              # rank_select has returned (tools/m5_scripts.py, RANK_END)
MAP_LOADED = 0x0100AE            # main has run map_load for a campaign's first mission
MISSION_RESET = 0x0100D6         # after mission_reset_tables, in every mission
OUTSIDE_MISSION = 0x02464E
HOLD = 40                        # VBlanks into the hold before the policy takes over

# Raw key codes (re/notes/keys.md): the letters by their place on the keyboard.
CONTROL_G = [0x24, 'ctrl']
CURSOR_DOWN = 0x4D
RETURN = 0x44
LETTER_KEYS = {'a': 0x20, 's': 0x21, 'd': 0x22, 'f': 0x23, 'g': 0x24, 'h': 0x25, 'j': 0x26,
               'k': 0x27, 'l': 0x28, 'q': 0x10, 'w': 0x11, 'e': 0x12, 'r': 0x13, 't': 0x14,
               'y': 0x15, 'u': 0x16, 'i': 0x17, 'o': 0x18, 'p': 0x19, 'z': 0x31, 'x': 0x32,
               'c': 0x33, 'v': 0x34, 'b': 0x35, 'n': 0x36, 'm': 0x37}


def cut(raw, n):
    """The first `n` VBlanks of a raw schedule, a run split where the cut falls in it."""
    out = []
    left = n
    for entry in raw:
        if left <= 0:
            break
        if entry[0] <= left:
            out.append(list(entry))
            left -= entry[0]
        else:
            out.append([left] + list(entry[1:]))
            left = 0
    return out


def compress(log):
    """[VBlanks, letters] runs, and [1, letters, keys] where keys went in."""
    out = []
    for letters, keys in log:
        if keys:
            out.append([1, letters, [list(k) if isinstance(k, (list, tuple)) else k
                                     for k in keys]])
        elif out and len(out[-1]) == 2 and out[-1][1] == letters:
            out[-1][0] += 1
        else:
            out.append([1, letters])
    return out


def base_script(name):
    """The raw schedule and the pokes of a script of M4 to M6 the plan starts from."""
    import m6_scripts
    return m6_scripts.script(name)['raw'], dict(m6_scripts.pokes(name) or {})


class Campaign(m6_autopilot.Enemy):
    """The headless original flown by an M7 plan."""

    def __init__(self, plan, **options):
        self.base = plan
        self.sortie = 0
        plan = self.sortie_plan(0)
        self.plan = plan
        pokes = {}
        if plan.get('after'):
            prefix, pokes = base_script(plan['after'])
        else:
            prefix = m6_autopilot.prefix_of(plan)
            if plan.get('mission'):
                pokes[MISSION_NUMBER] = (2, plan['mission'])
        for address, entry in plan.get('pokes', {}).items():
            pokes[address] = entry
        self.pokes = pokes
        m4_autopilot.Pilot.__init__(self, prefix, m6_autopilot.policy, **options)
        due = {}
        for address, entry in pokes.items():
            at = entry[2] if len(entry) > 2 else RANK_END
            due.setdefault(at, []).append((address, entry[0], entry[1]))
        for at, items in due.items():
            def poke(items=items):
                for a, n, v in items:
                    self.o.write(a, (v & ((1 << (8 * n)) - 1)).to_bytes(n, 'big'))
            self.stop_at(at, poke)
        self.leg = 0
        self.tap = 0
        self.cool = 0
        self.last_tick = -1
        self.drops = []
        self.done_flag = False
        self.open_tick = 0
        self.lost_at = None
        self.fight = None
        self.turn_way = ''
        self.switched = False
        self.consumed = 0                     # the base's VBlanks replayed
        self.cut_at = None
        self.s_at = {}                        # mission -> the script VBlank of its step S
        self.saving = None                    # the save's VBlank count while it runs
        self.saved_at = None                  # (tick, VBlank) of the save's Return

    def _mission_start(self):
        super()._mission_start()
        self.s_at[self.missions] = self.vblanks - self.spin_vblanks

    def _switch_now(self):
        plan = self.plan
        if plan.get('after'):
            s = self.s_at.get(plan.get('switch', 2))
            return s is not None and self.vblanks - self.spin_vblanks - s >= HOLD
        return self.consumed >= self.prefix_len

    def _next_raw(self):
        if self._frozen:
            return 0, []                      # the fade's wait: the script stands
        if not self.switched:
            if not self._switch_now():
                self.consumed += 1
                return headless.Headless._next_raw(self)
            self.switched = True
            self.cut_at = self.consumed
        chosen = campaign_policy(self, self.state())
        letters, keys = chosen if isinstance(chosen, tuple) else (chosen, ())
        self.log.append((letters, tuple(keys)))
        return headless.raw_state(letters), headless.key_events(list(keys))

    def state(self):
        s = super().state()
        o = self.o
        s['rank'] = o.r16(RANK_PLAYED)
        s['mission'] = o.r16(MISSION_NUMBER)
        s['missions'] = self.missions
        return s

    def script(self):
        """The base cut at the switch, then the tail the policy chose."""
        head = cut(self.run_spec['raw'], self.cut_at if self.cut_at is not None else self.consumed)
        return head, compress(self.log)


def save_keys(name):
    """The save in the hold, VBlank by VBlank from Control-G: the dialog opens on the first
    slot's line editor; the cursor down leaves it for the second slot, where the name is
    typed, and Return saves (re/notes/frontend.md, the load and save dialog)."""
    out = {0: [CONTROL_G], 60: [CURSOR_DOWN]}
    at = 80
    for ch in name:
        out[at] = [LETTER_KEYS[ch]]
        at += 10
    out[at + 10] = [RETURN]
    return out, at + 10


def campaign_policy(m, s):
    """M6's policy, and in the hold after a landing the plan's save, after which the next
    sortie of the plan flies (`then`)."""
    plan = m.plan
    if plan.get('save') and getattr(m, 'landed', False) and m.phase == 'end' and s['menu']:
        m.phase = 'save'
        m.saving = 0
        m.hold_tick = m.ticks                 # the weapon menu came up a tick before
    if m.phase == 'save':
        keys, last = save_keys(plan['save'])
        v = m.saving
        m.saving += 1
        if v == last:
            m.saved_at = (m.ticks, m.vblanks)
        if v in keys:
            return '', keys[v]
        if m.saved_at and m.ticks >= m.saved_at[0] + 2:
            # The dialog is closed and the inner loop runs again: the next sortie, from the
            # hold, whose menu is live 15 ticks after it came up (0x026D3E) whatever the
            # dialog took, because the dialog stops the ticks.
            m.plan = dict(plan['then'])
            m.landed = False
            m.go('hold')
            m.open_tick = m.hold_tick - 1
            m.leg = 0
            m.fired = set()
            m.rockets = {}
        return ''
    if plan.get('hold'):
        return ''                             # the aircraft stays in the hold
    if plan.get('policy') == 'm5':
        return m5_autopilot.attack(m, s)
    return m6_autopilot.policy(m, s)


# ------------------------------------------------------------------------------ the plans

# The carriers' lifts (player_start_x) of the maps the plans reach: b 6112, d 7456, f 8416,
# m 13760 (tools/m6_observe.py maps: the carrier's span; the lift 440 pixels from its west
# end).  East of each carrier is open sea for a few thousand pixels.
LIVES = 0x02535C

# Map b's islands (tools/m5_autopilot.py): the western one from 1132 to 2840 with the slot-3
# targets at 1132-1192, 2020-2080 and 2780-2840 and the slot-4 ones at 1768, 1872 and 2304;
# the eastern one from 11564 to 12672, slot-3 at 11564-11624 and 12612-12672, slot-4 at
# 11800 and 12144.  The carrier's lift at 6112.
WEST_B = [
    {'dir': 'R', 'y': 130, 'to': 3500, 'do': [('hunt', 900, 3500, 30), ('bombfull', 900, 3500)]},
    {'dir': 'L', 'y': 130, 'to': 900, 'do': [('hunt', 900, 3500, 30), ('bombfull', 900, 3500)]},
]
EAST_B = [
    {'dir': 'L', 'y': 130, 'to': 11200, 'do': [('hunt', 11200, 13100, 30), ('bombfull', 11200, 13100)]},
    {'dir': 'R', 'y': 130, 'to': 13100, 'do': [('hunt', 11200, 13100, 30), ('bombfull', 11200, 13100)]},
]

PLANS = {
    # island_a's win of map a (tools/m5_scripts.py), the next mission of the campaign (the
    # first rank's second, map b): out east over the sea and back.
    'chain_a': {'after': 'island_a', 'switch': 2, 'legs': [
        {'dir': 'R', 'y': 150, 'to': 9000}, {'dir': 'L', 'y': 150, 'to': 7000}],
                'end': 'level', 'tail': 60},
    # The same win with the mission number poked to 3 after map_load (0x0100AE), so that map
    # a is won as the first rank's last mission: the promotion, the balloons, a life more,
    # and the second rank's first mission, map d.
    'promote_a': {'after': 'island_a', 'switch': 2,
                  'pokes': {MISSION_NUMBER: (2, 3, MAP_LOADED)}, 'legs': [
        {'dir': 'R', 'y': 150, 'to': 10000}, {'dir': 'L', 'y': 150, 'to': 8200}],
                  'end': 'level', 'tail': 60},
    # The same win as the last rank's last mission (rank_played 6, mission 3 poked after
    # map_load): the promotion leaves the rank at 6, and the next mission is its first, map
    # m, which choose_night may make a night mission.
    'cap_a': {'after': 'island_a', 'switch': 2,
              'pokes': {MISSION_NUMBER: (2, 3, MAP_LOADED), RANK_PLAYED: (2, 6, MAP_LOADED)},
              'legs': [{'dir': 'R', 'y': 150, 'to': 16500}, {'dir': 'L', 'y': 150, 'to': 14600}],
              'end': 'level', 'tail': 60},
    # Map f (the second rank's third mission): out east to the island at 11536-12712, a bomb
    # on its first barracks and its first dug-out, back to the carrier and down into the
    # hold, the game saved there under the name "save" (Control-G), then up again and out
    # east.  The cruise ship's gun list, the pillboxes, the soldiers and both target tables
    # all go into the file.
    'save_a': {'rank': 1, 'mission': 3, 'legs': [
        {'dir': 'R', 'y': 150, 'to': 12400, 'do': [('drop', 11776), ('drop', 11858)]},
        {'dir': 'L', 'y': 150, 'to': 11000}, {'dir': 'R', 'y': 150, 'to': 11200}],
               'end': 'land', 'save': 'save', 'then': {
        'legs': [{'dir': 'R', 'y': 150, 'to': 10500}, {'dir': 'L', 'y': 150, 'to': 9200}],
        'end': 'level', 'tail': 40}},
    # The second mission of the fourth rank, map j, with every enemy ship's hits and the
    # islands left poked to 0 after each mission's reset of its tables (0x0100D6): the ships
    # sink at once and the last one at ten rows wins the mission (ship_sinking 0x011D28),
    # while the aircraft waits in the hold with the weapon menu up, so that main goes on to
    # the next mission at once, and so on: j and k and l won with a promotion each, m and
    # n with the next mission, o with the rank's cap back to m.  The flight ends 300 VBlanks
    # into the seventh mission.  Nothing here depends on a pass's work, so the chain is the
    # same at one, two and three VBlanks per pass.
    'ships_j': {'rank': 3, 'mission': 2, 'hold': True, 'until_mission': 7, 'until_vblanks': 300,
                'pokes': {0x02546C: (2, 0, MISSION_RESET), 0x02548A: (2, 0, MISSION_RESET),
                          0x0254A8: (2, 0, MISSION_RESET), 0x0254C6: (2, 0, MISSION_RESET),
                          0x025383: (1, 0, MISSION_RESET)}, 'legs': []},
    # island_a's win of map a, then map b won as well: both islands bombed and their soldiers
    # hunted, sortie after sortie with a landing in between, until the map's last island is
    # neutralised; the lives poked to 9 after map_load (0x0100AE), because island_a comes to
    # map b with one.  The flight ends 200 VBlanks into the third mission's hold.
    'win_b': {'after': 'island_a', 'switch': 2, 'policy': 'm5',
              'pokes': {LIVES: (1, 9, MAP_LOADED)}, 'until_clear': True, 'land': True,
              'land_oil': 110, 'climb_to_turn': True, 'until_mission': 3, 'sorties': [
        {'legs': [{'dir': 'L', 'y': 150, 'to': 900, 'do': [
            ('drop', 2824), ('drop', 2304), ('drop', 2064), ('drop', 1872), ('drop', 1768),
            ('drop', 1176)]}] + WEST_B * 5},
        {'legs': [{'dir': 'R', 'y': 150, 'to': 13100, 'do': [
            ('drop', 11594), ('drop', 11800), ('drop', 12144), ('drop', 12642)]}] + EAST_B * 5},
        {'legs': WEST_B * 4 + [{'dir': 'R', 'y': 150, 'to': 11200}] + EAST_B * 4},
        {'legs': WEST_B * 4 + [{'dir': 'R', 'y': 150, 'to': 11200}] + EAST_B * 4},
        {'legs': WEST_B * 4 + [{'dir': 'R', 'y': 150, 'to': 11200}] + EAST_B * 4},
        {'legs': WEST_B * 4 + [{'dir': 'R', 'y': 150, 'to': 11200}] + EAST_B * 4},
    ]},
}


def done(m, s):
    until = m.base.get('until_mission')
    if until:
        at = m.s_at.get(until)
        return at is not None and m.vblanks - m.spin_vblanks - at >= m.base.get('until_vblanks', 200)
    return m.phase == 'end' and not m.plan.get('save') and m.since() >= m.plan.get('tail', 60)


def fly(plan, max_ticks=40000, verbose=False):
    m = Campaign(plan)
    trail = []
    while m.ticks < max_ticks:
        # No tick for 4,000 VBlanks: the game is over and waits in the front end.
        m.run_spec['stop']['vblanks'] = m.vblanks - m.spin_vblanks + 4000
        try:
            if m.run(until='tick', wall_limit=1800.0) != 'tick':
                break
        except headless.Stuck:
            break
        if m.o.read(OUTSIDE_MISSION, 1)[0] and m.switched:
            break                             # the game is over
        s = m.state()
        if m.switched:
            trail.append((m.ticks, m.phase, m.leg, s))
            if verbose and m.ticks % 16 == 0:
                print(m.ticks, m.phase, m.leg, {k: s[k] for k in ('deck', 'x', 'y', 'lives',
                                                                    'rank', 'mission')})
        if m.switched and done(m, s):
            break
    return m, trail


def summary(m, trail):
    last = trail[-1][3] if trail else {}
    return {'ticks': m.ticks, 'vblanks': m.vblanks, 'phase': m.phase, 'cut': m.cut_at,
            'missions': m.missions, 'rank': last.get('rank'), 'mission': last.get('mission'),
            'lives': last.get('lives'), 'score': last.get('score'), 'saved': m.saved_at,
            'kills': last.get('kills'), 'islands_left': last.get('left')}


def fly_one(name):
    m, trail = fly(PLANS[name])
    head, tail = m.script()
    return name, m.cut_at, tail, summary(m, trail)


def write_runs(results, path):
    """tools/m7_runs.py: each plan's cut and tail, as the scripts are built from them."""
    lines = ['"""The flown tails of the M7 scripts, written by tools/m7_autopilot.py --all.',
             '',
             'Each entry is (the base script, the VBlanks of it replayed, the tail the autopilot',
             'chose after them); a plan of its own has no base and its cut is its front end.',
             '"""', '']
    for name in sorted(results):
        base, cut_at, tail = results[name]
        lines.append('%s = (%r, %d, %s)' % (name.upper(), base, cut_at,
                                            pprint.pformat(tail, width=92, compact=True)))
        lines.append('')
    with open(path, 'w') as handle:
        handle.write('\n'.join(lines))


def main():
    parser = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    parser.add_argument('plan', nargs='?', choices=sorted(PLANS))
    parser.add_argument('--all', nargs='*', help='fly these plans (every one without names)')
    parser.add_argument('--jobs', type=int, default=4)
    parser.add_argument('--verbose', action='store_true')
    args = parser.parse_args()
    if args.all is not None:
        import concurrent.futures
        names = args.all or sorted(PLANS)
        path = os.path.join(HERE, 'm7_runs.py')
        results = {}
        if os.path.exists(path):
            import importlib.util
            spec = importlib.util.spec_from_file_location('m7_runs', path)
            runs = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(runs)
            for name in PLANS:
                if hasattr(runs, name.upper()):
                    results[name] = getattr(runs, name.upper())
        with concurrent.futures.ProcessPoolExecutor(max_workers=args.jobs) as pool:
            for name, cut_at, tail, info in pool.map(fly_one, names):
                results[name] = (PLANS[name].get('after'), cut_at, tail)
                print(name, json.dumps(info), flush=True)
        write_runs(results, path)
        return 0
    m, trail = fly(PLANS[args.plan], verbose=args.verbose)
    last = None
    for tick, phase, leg, s in trail:
        if (phase, leg, s['missions']) != last:
            print('%5d %-6s leg %d mission %d (rank %d, %d) deck %2d x %5d y %5d lives %d score %d'
                  % (tick, phase, leg, s['missions'], s['rank'], s['mission'], s['deck'], s['x'],
                     s['y'], s['lives'], s['score']))
            last = (phase, leg, s['missions'])
    head, tail = m.script()
    print(json.dumps(tail))
    print(json.dumps(summary(m, trail)))
    return 0


if __name__ == '__main__':
    sys.exit(main())
