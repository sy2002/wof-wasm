"""The autopilot of M5: attacks on the islands, flown on the headless original.

tools/m4_autopilot.py flies the landing, the turns and the fuel flight.  This module adds a
policy that takes off with a chosen weapon, flies legs at a chosen height, and on each leg
drops the other weapon where a bomb or a rocket will come down on a target, holds the button
for the guns over a stretch of world x, or lets the aircraft come down where it should.  Its
choices, compressed into [VBlanks, letters] runs, are the script; the original flies the same
flight again without the autopilot (tools/m5_scripts.py keeps them).

    .venv/bin/python tools/m5_autopilot.py PLAN          fly a plan of PLANS and print the script
    .venv/bin/python tools/m5_autopilot.py PLAN --verbose

A plan is a map (by its mission number, poked at the rank selection's end as the M4 setups
do; `balloons` also sets balloons_on after the mission's reset), the weapon menu's steps,
and a list of legs.  What each plan reaches is in
re/notes/porting-m5.md, "The scripts".
"""
import argparse
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import headless                                              # noqa: E402
import m4_autopilot                                          # noqa: E402
import pass_observe                                          # noqa: E402

PLAYER = 0x025078
MISSION_NUMBER = 0x0253C0
BALLOONS_ON = 0x02535D
OBJECTS = 0x024CAE
GRAVITY = 0x025350
WEAPON_TYPE = 0x0253A4
WEAPON_COUNT = 0x02536D
SCORE = 0x02534C

s16 = m4_autopilot.s16


def s32(v):
    return v - (1 << 32) if v & 0x80000000 else v


class Attack(m4_autopilot.Pilot):
    """The headless original flown by a plan (below), after the front end."""

    def __init__(self, plan, **options):
        # A plan of several sorties flies one with each aircraft: when one is lost (or its
        # sortie ends in a crash), the next aircraft takes the next sortie's weapon and legs.
        self.base = plan
        self.sortie = 0
        plan = self.sortie_plan(0)
        self.plan = plan
        prefix = pass_observe.FRONT + [[40, '']]
        super().__init__(prefix, attack, **options)
        if plan.get('mission'):
            self.stop_at(0x01009E, lambda: self.o.write(MISSION_NUMBER,
                                                         bytes([0, plan['mission']])))
        if plan.get('balloons'):
            self.stop_at(0x0100D6, lambda: self.o.write(BALLOONS_ON, b'\xff'))
        self.leg = 0
        self.tap = 0                   # VBlanks of the button still to hold for a tap
        self.cool = 0                  # VBlanks before the next tap may start
        self.last_tick = -1
        self.drops = []                # (tick, x, predicted impact x)
        self.done_flag = False
        self.open_tick = 0             # the tick the weapon menu opened
        self.lost_at = None

    def sortie_plan(self, k):
        sorties = self.base.get('sorties')
        if not sorties:
            return self.base
        merged = dict(self.base)
        merged.update(sorties[min(k, len(sorties) - 1)])
        merged['more'] = k + 1 < len(sorties)
        return merged

    def state(self):
        s = super().state()
        o = self.o
        s['wcount'] = o.read(WEAPON_COUNT, 1)[0]
        s['wtype'] = s16(o.r16(WEAPON_TYPE))
        s['menu'] = o.read(0x025364, 1)[0]
        s['score'] = o.r32(SCORE)
        s['oil'] = s16(o.r16(PLAYER + 0x12))
        s['fuel'] = s16(o.r16(PLAYER + 0x0E))
        # The soldiers by state (re/notes/objects.md: 1 running, 2 dying, 3 dead) and the
        # first island's two counts (island_score 0x025450: soldiers, then pillboxes).
        base, count = o.r32(0x025500), o.r16(0x0253C4)
        states = [o.r16(base + 8 * i + 6) for i in range(count)] if base else []
        s['running'] = [s16(o.r16(base + 8 * i)) for i in range(len(states)) if states[i] == 1]
        s['dead'] = sum(1 for v in states if v == 3)
        s['island'] = [o.r16(0x025450 + 2 * i) for i in range(8)]
        s['left'] = o.read(0x025383, 1)[0]
        s['flash'] = o.r16(0x025416)
        # The targets that still hold soldiers: (world x of the draw record, soldiers inside)
        # for the slot-3 and the slot-4 tables (re/notes/map.md).
        full = []
        for pointer, counter in ((0x0254FC, 0x025386), (0x0254F8, 0x025387)):
            tb, n = o.r32(pointer), o.read(counter, 1)[0]
            for i in range(n if tb else 0):
                inside = o.read(tb + 16 * i + 8, 1)[0]
                if inside and inside < 0x80:
                    full.append((o.r32(tb + 16 * i) * 4, inside))
        s['full'] = full
        # The pillboxes still standing (target_records_f +8 clear), by world x.
        tb, n = o.r32(0x025504), o.read(0x025385, 1)[0]
        s['pills'] = [o.r16(tb + 0x0E * i) * 4 for i in range(n if tb else 0)
                      if o.read(tb + 0x0E * i + 8, 1)[0] == 0]
        return s


def fall(m, s):
    """Where a bomb dropped now comes down, as object_step moves a type-1 record (0x010B58):
    the horizontal speed loses a tenth of its whole part every tick, the vertical long loses
    g_025350, and the height is the whole part of the vertical long plus the height with its
    old fraction.  It explodes at height 0x0C over land or sea (0x010C04, 0x010C1A).  The
    fraction the record keeps from its last use is taken as 0 here; the plan's `lead`
    absorbs the rest."""
    g = s32(m.o.r32(GRAVITY))
    x = s['x'] << 16
    dx = s['sx'] << 16
    if s['face'] < 0:
        dx = -dx
    vy = s['sy'] << 16
    y = (s['y'] + 0x0B) << 16
    for _ in range(400):
        q = int((dx >> 16) / 10)
        dx -= q << 16
        x += dx
        vy -= g
        y = ((vy + y) >> 16) << 16
        if (y >> 16) <= 0x0C:
            break
    return x >> 16


# Where a bomb comes down against fall()'s prediction, measured over the drops of bomb_a: 14
# pixels further on, the tick or so between the tap and the spawn (0x01B5E2 runs in the tick
# after the one the tap's sample fed).
BIAS = 14


def hold_height(s, want, gain=8.0, limit=3):
    if s['deck'] != 0:
        return ''
    target = max(min((want - s['y']) / gain, limit), -limit)
    if s['sy'] < target - 1:
        return 'U'
    if s['sy'] > target + 1:
        return 'D'
    return ''


def attack(m, s):
    """Front end done: the hold (the weapon menu), the lift, the roll, the climb, then the
    plan's legs one after the other; each leg flies one way at its height until its end x,
    doing its actions on the way, and the turn to the next leg comes after it."""
    plan = m.plan
    new_tick = m.ticks != m.last_tick
    m.last_tick = m.ticks
    if m.phase is None:
        m.go('hold')
        m.open_tick = max(0, m.ticks - 17)    # the menu is live from here on
    ph = m.phase
    if (ph in ('leg', 'turn', 'land') or (ph == 'end' and plan.get('more'))) and \
            s['deck'] == 1 and s['y'] <= 0 and s['menu'] and not plan.get('once'):
        m.go('hold')                          # the next aircraft, in the hold
        m.open_tick = m.ticks
        m.lost = getattr(m, 'lost', 0) + 1
        if m.base.get('sorties'):
            m.sortie += 1
            m.plan = plan = m.sortie_plan(m.sortie)
            m.leg = 0
            m.fired = set()
            m.rockets = {}
        ph = 'hold'
    if ph in ('leg', 'turn') and plan.get('until_clear') and s['left'] == 0:
        m.go('end')                           # the map's last island is neutralised
        ph = 'end'
    if ph in ('leg', 'turn') and plan.get('land') and plan.get('more') and \
            s['deck'] == 0 and s['oil'] < plan.get('land_oil', 0):
        m.go('end')                           # the engine leaks: back to the carrier now
        ph = 'end'
    if ph in ('leg', 'turn') and plan.get('once') and s['deck'] != 0:
        m.go('end')                           # the aircraft is lost: the plan is over
        ph = 'end'
    m.phase = ph
    if m.cool:
        m.cool -= 1
    if ph == 'hold':
        t = m.since()
        steps = plan.get('menu', '')
        # The menu is live 15 ticks after it opens (0x026D3E); each step is a push of 8
        # VBlanks and a pause of 32, as tools/m4_scripts.py's SELECT does.
        k = (m.ticks - m.open_tick - 18) // 10 if m.ticks - m.open_tick >= 18 else -1
        if 0 <= k < len(steps):
            return steps[k] if (m.ticks - m.open_tick - 18) % 10 < 2 else ''
        if m.ticks - m.open_tick < 18 + 10 * len(steps) + 4:
            return ''
        m.go('lift')
        m.tap = 3
    if ph == 'lift' or m.phase == 'lift':
        if m.tap:
            m.tap -= 1
            return 'F'
        if s['deck'] == 1 and s['y'] > 30 and not s['menu']:
            m.go('roll')
        return ''
    if ph == 'roll':
        if s['deck'] == 0:
            m.go('climb')
            return 'RU'
        return 'R' if m.since() < 115 else 'RU'
    if ph == 'climb':
        legs = plan['legs']
        if s['y'] >= max(legs[0].get('y', 400) - 30, 100) or m.since() > 200:
            m.go('leg')
            m.leg = 0
        return 'RU'
    if ph == 'turn':
        leg = plan['legs'][m.leg]
        way = leg['dir']
        want_face = -1 if way == 'L' else 1
        if s['face'] == want_face and s['att'] == 0:
            m.go('leg')
            m.button = False
            return way + hold_height(s, leg.get('y', 400))
        # The button held inside the turn, from attitude 4 to 20, where it neither fires the
        # guns nor drops a weapon (0x01B5B0) but keeps the enemy's countdown from running out
        # (0x01BC02): left alone for 1,349 ticks it brings the enemy aircraft, which are
        # M6's.  Released before the turn ends, after more than ten VBlanks, it is no tap.
        # A plan with `countdown` leaves the button alone, so that the enemy aircraft come.
        if 4 <= s['att'] <= 20 and not plan.get('countdown'):
            m.button = True
        elif s['att'] > 20 or s['att'] == 0:
            m.button = False
        return way + hold_height(s, leg.get('y', 400), limit=2) + ('F' if getattr(m, 'button', False) else '')
    if ph == 'leg':
        if m.leg >= len(plan['legs']):
            m.go('end')
            return ''
        leg = plan['legs'][m.leg]
        way = leg['dir']
        want_face = -1 if way == 'L' else 1
        if s['face'] != want_face:
            m.go('turn')
            return way
        ahead = (s['x'] - leg['to']) * want_face >= 0
        if ahead and plan.get('climb_to_turn') and s['deck'] == 0 and \
                s['y'] < min(leg.get('y', 400), 150) - 30:
            # Too low to turn: a turn at this height dives into the ground; climb on first.
            return way + 'U' + ('F' if m.tap else '')
        if ahead or s['deck'] != 0:
            m.leg += 1
            if m.leg >= len(plan['legs']):
                m.go('end')
                return ''
            nxt = plan['legs'][m.leg]
            if nxt['dir'] != way:
                m.go('turn')
                return nxt['dir']
            return way
        vertical = hold_height(s, leg.get('y', 400))
        button = ''
        if m.tap:
            m.tap -= 1
            button = 'F'
        for act in leg.get('do', ()):
            kind = act[0]
            if kind == 'guns':
                lo, hi = sorted(act[1:3])
                if lo <= s['x'] <= hi and s['att'] == 0:
                    button = 'F'
                    vertical = act[3] if len(act) > 3 else vertical
            elif kind == 'strafe':
                # The guns' bullets reach the ground only while the aircraft sinks (the
                # player's vertical speed negative) below y 0xA0 (gun_splashes, 0x0119C4):
                # a gentle descent to `low` with the button held, then level.
                lo, hi = sorted(act[1:3])
                low = act[3] if len(act) > 3 else 40
                if lo <= s['x'] <= hi and s['att'] == 0:
                    button = 'F'
                    vertical = hold_height(s, low, gain=10.0, limit=2)
            elif kind == 'drop' and new_tick and not m.tap and not m.cool:
                target = act[1]
                lead = act[2] if len(act) > 2 else 0
                key = ('drop', m.leg, target)
                if key in m.__dict__.setdefault('fired', set()):
                    continue
                impact = fall(m, s) + (lead or BIAS) * (-1 if s['face'] < 0 else 1)
                passed = (impact - target) * want_face >= 0
                if passed and abs(impact - target) < 60 and s['att'] == 0:
                    m.fired.add(key)
                    m.drops.append((m.ticks, s['x'], impact, target))
                    m.tap = 3
                    m.cool = 12
                    button = 'F'
            elif kind == 'spray' and new_tick and not m.tap and not m.cool:
                lo, hi = sorted(act[1:3])
                every = act[3] if len(act) > 3 else 4
                if lo <= s['x'] <= hi and s['att'] == 0 and m.ticks % every == 0:
                    m.drops.append((m.ticks, s['x'], fall(m, s), None))
                    m.tap = 3
                    m.cool = 5
                    button = 'F'
            elif kind == 'hunt':
                # The guns at the running soldiers of the stretch: descend with the button
                # held while one is ahead within 250 pixels.
                lo, hi = sorted(act[1:3])
                low = act[3] if len(act) > 3 else 30
                near = [x for x in s['running'] if lo <= x <= hi and 0 <= (x - s['x']) * want_face <= 250]
                if near and s['att'] == 0:
                    button = 'F'
                    vertical = hold_height(s, low, gain=10.0, limit=2)
            elif kind == 'bombfull' and new_tick and not m.tap and not m.cool:
                # A bomb on every target of the stretch that still holds soldiers.
                lo, hi = sorted(act[1:3])
                impact = fall(m, s) + BIAS * (-1 if s['face'] < 0 else 1)
                for x, inside in s['full']:
                    key = ('full', m.leg, x)
                    if not lo <= x <= hi or key in m.__dict__.setdefault('fired', set()):
                        continue
                    if (impact - x) * want_face >= 0 and abs(impact - x) < 40 and s['att'] == 0:
                        m.fired.add(key)
                        m.drops.append((m.ticks, s['x'], impact, x))
                        m.tap = 3
                        m.cool = 12
                        button = 'F'
                        break
            elif kind == 'rocket':
                # A dive at a target for the rockets: from `start` pixels before it the stick
                # forward until the height is `at`, a rocket then and another three ticks
                # later, then the stick back until the aircraft climbs again.
                target, start, at = act[1], act[2], act[3]
                key = ('rocket', m.leg, target)
                done = m.__dict__.setdefault('rockets', {})
                stage = done.get(key, 'wait')
                gap = (s['x'] - target) * want_face          # negative while before it
                if stage == 'wait' and -start <= gap < 0:
                    stage = 'dive'
                if stage == 'dive':
                    vertical = 'D'
                    if s['y'] <= at and new_tick and not m.tap:
                        m.drops.append((m.ticks, s['x'], None, target))
                        m.tap = 3
                        m.cool = 8
                        button = 'F'
                        stage = 'fire'
                        m.fire_tick = m.ticks
                elif stage == 'fire':
                    vertical = 'D'
                    if new_tick and not m.tap and not m.cool and m.ticks >= m.fire_tick + 3:
                        m.drops.append((m.ticks, s['x'], None, target))
                        m.tap = 3
                        button = 'F'
                        stage = 'pull'
                elif stage == 'pull':
                    vertical = 'U'
                    if s['sy'] >= 1:
                        stage = 'done'
                done[key] = stage
            elif kind == 'rocketfull':
                # A rocket dive at every target of the stretch that still holds soldiers,
                # and at every pillbox still standing: as 'rocket', aimed at the next one.
                lo, hi = sorted(act[1:3])
                aims = sorted([x for x, _ in s['full'] if lo <= x <= hi] +
                              [x for x in s['pills'] if lo <= x <= hi],
                              key=lambda x: (x - s['x']) * want_face)
                aims = [x for x in aims if (x - s['x']) * want_face > 150]
                done = m.__dict__.setdefault('rockets', {})
                live = [k for k, v in done.items() if k[0] == 'rf' and v in ('dive', 'fire', 'pull')]
                if live:
                    target = live[0][2]
                elif aims and s['wcount'] > 0:
                    target = aims[0]
                else:
                    target = None
                if target is not None:
                    key = ('rf', m.leg, target)
                    stage = done.get(key, 'wait')
                    gap = (s['x'] - target) * want_face
                    if stage == 'wait' and -245 <= gap < 0:
                        stage = 'dive'
                    if stage == 'dive':
                        vertical = 'D'
                        if s['y'] <= 115 and new_tick and not m.tap:
                            m.tap = 3
                            m.cool = 8
                            button = 'F'
                            stage = 'fire'
                            m.fire_tick = m.ticks
                    elif stage == 'fire':
                        vertical = 'D'
                        if new_tick and not m.tap and not m.cool and m.ticks >= m.fire_tick + 3:
                            m.tap = 3
                            button = 'F'
                            stage = 'pull'
                    elif stage == 'pull':
                        vertical = 'U'
                        if s['sy'] >= 1:
                            stage = 'done'
                    done[key] = stage
            elif kind == 'dive':
                # A controlled descent towards `low` over the stretch.
                lo, hi = sorted(act[1:3])
                low = act[3] if len(act) > 3 else 40
                if lo <= s['x'] <= hi:
                    vertical = hold_height(s, low, gain=6.0, limit=4)
        return way + vertical + button
    if ph == 'end' and plan.get('more') and plan.get('land'):
        m.go('land')
        m.land = 'out'
        ph = 'land'
    if ph == 'land':
        return land(m, s)
    if ph == 'end':
        end = 'crash' if plan.get('more') else plan.get('end', 'level')
        if end == 'level':
            way = 'L' if s['face'] < 0 else 'R'
            return way + hold_height(s, plan['legs'][-1].get('y', 400))
        if end == 'idle':
            return ''
        if end == 'crash':
            # Straight down into the ground ahead.
            way = 'L' if s['face'] < 0 else 'R'
            return way + ('D' if s['deck'] == 0 else '')
        return ''
    return ''


def turn_button(m, s):
    """The button inside a turn, where it keeps the enemy's countdown up (0x01BC02), unless
    the plan wants the enemy aircraft to come (`countdown`)."""
    return 'F' if 4 <= s['att'] <= 20 and not m.plan.get('countdown') else ''


def land(m, s):
    """Back to the carrier and down into the hold for the next sortie, as tools/m4_autopilot.py's
    landing flies it: out past the bow to the east, back low from the east on a glide path to
    the bow, the stick forward alone over it and after the touch-down (the hook needs
    0x025A9C clear), then the taxi to the lift and the button.  The deck of any map lies
    where its carrier does: the lift at player_start_x, the bow 312 pixels east of it."""
    lift = s16(m.o.r16(0x025392))
    bow = lift + 312
    stage = m.land
    if stage == 'out':
        if s['face'] == 1 and s['x'] > bow + 1150:
            m.land = 'turn'
            return 'L'
        way = 'R' if s['face'] == 1 else 'L'
        if s['face'] == -1 and s['x'] < bow + 1150:
            way = 'R'
        return way + hold_height(s, 150, limit=2) + turn_button(m, s)
    if stage == 'turn':
        if s['face'] == -1 and s['att'] == 0:
            m.land = 'approach'
        return 'L' + hold_height(s, 150, limit=2) + turn_button(m, s)
    if stage == 'approach':
        dist = s['x'] - bow
        target = 36 + max(dist, 0) * 0.08
        if dist < 20:
            m.land = 'stall'
        want = max(min((target - s['y']) / 4.0, 3), -4)
        if s['sy'] < want - 1:
            return 'LU'
        if s['sy'] > want + 1:
            return 'LD'
        return 'L'
    if stage in ('stall', 'down'):
        if s['deck'] == 7:
            m.land = 'caught'
            m.mark = m.ticks
        elif s['deck'] != 0:
            m.land = 'down'
        return 'U'
    if stage == 'caught':
        if m.ticks - m.mark > 40:
            m.land = 'taxi'
        return ''
    if stage == 'taxi':
        dist = s['x'] - lift
        if abs(dist) <= 2 and s['air'] == 0:
            m.land = 'button'
            m.mark = m.ticks
            return ''
        if abs(dist) <= s['air'] * s['air'] / 1600.0 + 2:
            return ''
        return 'L' if dist > 0 else 'R'
    if stage == 'button':
        return 'F' if m.ticks - m.mark < 1 else ''
    return ''


def attack_done(m, s):
    if m.plan.get('more'):
        return False
    return m.phase == 'end' and m.since() >= m.plan.get('tail', 60)


# ------------------------------------------------------------------------------ the plans

# Map a: the island lies from x 32 to 3944; the slot-3 targets (dugo) at 1736 and 3224, the
# slot-4 targets (huta) at 2392 and 2712, the flag (slot 0x113) at 2408.  The carrier's lift
# is at 7032.  Map b (mission 2): islands 32-3944 and 10304-13936, the carrier at 6112.
# Map c (mission 3): islands 32-3496, 8152-11432 and 12000-15536, slot-0x0F targets at 3432,
# 3464, 8256 and 8288, the carrier at 5880.
# The soldier hunts over map c's three islands, a leg each way: the guns at the running
# soldiers, a bomb (or with rockets a dive) on every target that still holds soldiers.
ISLAND1 = [
    {'dir': 'R', 'y': 130, 'to': 3600, 'do': [('hunt', 1300, 3600, 25), ('bombfull', 1300, 3600)]},
    {'dir': 'L', 'y': 130, 'to': 1300, 'do': [('hunt', 1300, 3600, 25), ('bombfull', 1300, 3600)]},
]
ISLAND2 = [
    {'dir': 'R', 'y': 140, 'to': 11600, 'do': [('hunt', 8000, 11600, 25), ('bombfull', 8000, 11600),
                                                ('rocketfull', 8000, 11600)]},
    {'dir': 'L', 'y': 140, 'to': 8000, 'do': [('hunt', 8000, 11600, 25), ('bombfull', 8000, 11600),
                                               ('rocketfull', 8000, 11600)]},
]
ISLAND3 = [
    {'dir': 'L', 'y': 130, 'to': 11900, 'do': [('hunt', 11900, 15600, 25), ('bombfull', 11900, 15600)]},
    {'dir': 'R', 'y': 130, 'to': 15700, 'do': [('hunt', 11900, 15600, 25), ('bombfull', 11900, 15600)]},
]

PLANS = {
    # One bomb on each target of map a from 150 pixels, flying left.
    'bomb_a': {'legs': [
        {'dir': 'L', 'y': 150, 'to': 1400,
         'do': [('drop', 3224), ('drop', 2712), ('drop', 2392), ('drop', 1736)]},
    ], 'end': 'level', 'tail': 200},
    # Map a's four targets bombed, then the guns at the soldiers that come out, pass after
    # pass over the island until the last one is dead.
    'island_a': {'legs': [
        {'dir': 'L', 'y': 150, 'to': 1300,
         'do': [('drop', 3224), ('drop', 2712), ('drop', 2392), ('drop', 1736)]},
    ] + [
        {'dir': 'R', 'y': 130, 'to': 3800, 'do': [('hunt', 1300, 3800, 25),
                                                  ('bombfull', 1300, 3800)]},
        {'dir': 'L', 'y': 130, 'to': 1300, 'do': [('hunt', 1300, 3800, 25),
                                                  ('bombfull', 1300, 3800)]},
    ] * 8, 'end': 'crash', 'tail': 400, 'until_clear': True},
    # Rockets (the menu one step up) at map a's targets: a rocket falls for a few ticks,
    # then flies on along the aircraft's pitch, accelerating (object_step, 0x010AC0), so it
    # comes down within reach only from a dive; a salvo every three ticks over each target.
    'rockets_a': {'menu': 'U', 'legs': [
        {'dir': 'L', 'y': 150, 'to': 3000, 'do': [('rocket', 3224, 245, 115)]},
        {'dir': 'R', 'y': 150, 'to': 4200},
        {'dir': 'L', 'y': 150, 'to': 2000, 'do': [('rocket', 2712, 235, 115)]},
    ], 'end': 'level', 'tail': 200, 'once': True},
    # The torpedo (the menu one step down), dropped low into the sea east of the carrier.
    'torpedo_a': {'menu': 'D', 'legs': [
        {'dir': 'R', 'y': 40, 'to': 10000, 'do': [('drop', 8600)]},
    ], 'end': 'level', 'tail': 200},
    # The same at 24 pixels: the torpedo meets the sea slowly and runs in it.
    'torpedo_run': {'menu': 'D', 'legs': [
        {'dir': 'R', 'y': 24, 'to': 10000, 'do': [('drop', 8600)]},
    ], 'end': 'level', 'tail': 360},
    # Low passes over map a's island without firing until the targets' fire has taken the
    # oil below 0x60 and the engine seizes.
    'hit_a': {'legs': [
        {'dir': 'L', 'y': 45, 'to': 1600}, {'dir': 'L', 'y': 150, 'to': 1100},
        {'dir': 'R', 'y': 150, 'to': 1500}, {'dir': 'R', 'y': 45, 'to': 3600},
        {'dir': 'R', 'y': 150, 'to': 4100}, {'dir': 'L', 'y': 150, 'to': 3700},
    ] * 10, 'end': 'level', 'tail': 250, 'once': True},
    # Into the ground of map a's island, next to the eastern hut.
    'crash_a': {'legs': [
        {'dir': 'L', 'y': 120, 'to': 2900},
    ], 'end': 'crash', 'tail': 400, 'once': True},
    # Map b (mission 2): its western island's six targets bombed and the soldiers hunted.
    'bomb_b': {'mission': 2, 'legs': [
        {'dir': 'L', 'y': 150, 'to': 900,
         'do': [('drop', 2824), ('drop', 2304), ('drop', 2064), ('drop', 1872), ('drop', 1768),
                ('drop', 1176)]},
        {'dir': 'R', 'y': 130, 'to': 3500, 'do': [('hunt', 900, 3500, 25)]},
    ], 'end': 'level', 'tail': 100},
    # Map c (mission 3): the western island's six targets bombed, the soldiers hunted.
    'bomb_c': {'mission': 3, 'legs': [
        {'dir': 'L', 'y': 150, 'to': 1300,
         'do': [('drop', 2808), ('drop', 2456), ('drop', 2368), ('drop', 2232), ('drop', 2088),
                ('drop', 1656)]},
        {'dir': 'R', 'y': 130, 'to': 3300, 'do': [('hunt', 1300, 3300, 25)]},
    ], 'end': 'level', 'tail': 100},
    # Map c: rockets at the two pillboxes (slot 0x0F) of the western island, one dive each.
    'rockets_c': {'mission': 3, 'menu': 'U', 'legs': [
        {'dir': 'L', 'y': 150, 'to': 3100, 'do': [('rocket', 3464, 245, 115)]},
        {'dir': 'R', 'y': 150, 'to': 4300},
        {'dir': 'L', 'y': 150, 'to': 3100, 'do': [('rocket', 3432, 245, 115)]},
    ], 'end': 'level', 'tail': 200, 'once': True},
    # Bombs from high above map a's island, in the eighth-scale view (above y 190).
    'high_a': {'legs': [
        {'dir': 'L', 'y': 420, 'to': 1400,
         'do': [('drop', 3224), ('drop', 2712), ('drop', 2392), ('drop', 1736)]},
    ], 'end': 'level', 'tail': 300},
    # Map c with balloons_on set after the mission's reset (0x0100D6), as the promotion
    # leaves it for the flight back to the carrier: out over the balloons and back.
    'balloons_c': {'mission': 3, 'balloons': True, 'legs': [
        {'dir': 'R', 'y': 120, 'to': 6700}, {'dir': 'L', 'y': 120, 'to': 5300},
        {'dir': 'R', 'y': 100, 'to': 6400},
    ], 'end': 'level', 'tail': 60},
    # Map c neutralised to its last island, for the promotion itself (mission_won): the
    # rockets on the four pillboxes and on island 2's targets with the first aircraft, the
    # bombs on islands 3 and 1 with the second, and the soldiers hunted with the guns; a
    # sortie that loses oil lands on the carrier, and the next sortie takes off from it.
    'win_c': {'mission': 3, 'until_clear': True, 'land': True, 'climb_to_turn': True,
                   'land_oil': 110,
                   'end': 'level', 'tail': 900,
                   'sorties': [
        {'menu': 'U', 'legs': [
            {'dir': 'R', 'y': 160, 'to': 9000, 'do': [('rocket', 8256, 260, 140)]},
        ] + ISLAND2 * 2 + [
            {'dir': 'L', 'y': 160, 'to': 4300},
            {'dir': 'L', 'y': 150, 'to': 3100, 'do': [('rocket', 3464, 235, 125)]},
            {'dir': 'R', 'y': 150, 'to': 4300},
            {'dir': 'L', 'y': 150, 'to': 3100, 'do': [('rocket', 3432, 235, 125)]},
        ]},
        {'legs': [
            {'dir': 'R', 'y': 150, 'to': 15700,
             'do': [('drop', 13160), ('drop', 13448), ('drop', 13728), ('drop', 14240)]},
        ] + ISLAND3 * 3},
        {'legs': [
            {'dir': 'L', 'y': 150, 'to': 1400,
             'do': [('drop', 2808), ('drop', 2456), ('drop', 2368), ('drop', 2232),
                    ('drop', 2088), ('drop', 1656)]},
        ] + ISLAND1 * 3},
        {'legs': ISLAND2 * 3 + ISLAND3 * 2},
        {'legs': ISLAND1 * 3},
        {'legs': ISLAND2 * 2 + ISLAND3 * 2},
        {'legs': ISLAND1 * 2 + ISLAND2 * 2},
        {'legs': ISLAND3 * 3},
    ]},
    # The guns over the sea east of the carrier: three shallow dives with the button held.
    'guns_sea': {'legs': [
        {'dir': 'R', 'y': 90, 'to': 10400,
         'do': [('strafe', 7900, 8300, 30), ('strafe', 8800, 9200, 30), ('strafe', 9700, 10100, 30)]},
    ], 'end': 'level', 'tail': 60},
    # The guns over the island of map a, flying left: dives over each target.
    'guns_a': {'legs': [
        {'dir': 'L', 'y': 90, 'to': 1400,
         'do': [('strafe', 3400, 3000, 30), ('strafe', 2800, 2300, 30), ('strafe', 1900, 1600, 30)]},
    ], 'end': 'level', 'tail': 60},
}


def impacts(m, kinds):
    """Object records that went from flying (0xFF) to going out (8) since the last look:
    (record, type, x, y, the frame's low bits byte +0x1F)."""
    out = []
    for i in range(15):
        a = OBJECTS + 0x2A * i
        kind = m.o.read(a + 0x20, 1)[0]
        if kinds.get(i) == 0xFF and kind == 8:
            out.append((i, s16(m.o.r16(a + 0x22)), s16(m.o.r16(a)), s16(m.o.r16(a + 4)),
                        m.o.read(a + 0x1F, 1)[0]))
        kinds[i] = kind
    return out


def fly(plan, max_ticks=6000, verbose=False):
    m = Attack(plan)
    trail = []
    kinds = {}
    m.impacts = []
    while m.ticks < max_ticks:
        if m.run(until='tick') != 'tick':
            break
        for hit in impacts(m, kinds):
            m.impacts.append((m.ticks,) + hit)
        s = m.state()
        trail.append((m.ticks, m.phase, m.leg, s))
        if verbose:
            print(m.ticks, m.phase, m.leg, s)
        if attack_done(m, s):
            break
    return pass_observe.FRONT + [[40, '']] + m4_autopilot.compress(m.log), m, trail


def emit(name, script, width=92):
    """The script as a Python literal for tools/m5_scripts.py, the runs after the front end
    wrapped to the width of the file."""
    head = pass_observe.FRONT + [[40, '']]
    assert script[:len(head)] == head
    runs = script[len(head):]
    lines, line = [], '    '
    for run in runs:
        item = '[%d, %r], ' % (run[0], run[1])
        if len(line) + len(item) > width:
            lines.append(line.rstrip())
            line = '    '
        line += item
    lines.append(line.rstrip())
    return '%s = PLANE + [\n%s\n]\n' % (name.upper(), '\n'.join(lines))


def main():
    parser = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    parser.add_argument('plan', choices=sorted(PLANS))
    parser.add_argument('--emit', action='store_true', help='print the script as a literal')
    parser.add_argument('--verbose', action='store_true')
    parser.add_argument('--ticks', type=int, default=6000)
    args = parser.parse_args()
    script, m, trail = fly(PLANS[args.plan], max_ticks=args.ticks, verbose=args.verbose)
    last = None
    for tick, phase, leg, s in trail:
        if (phase, leg) != last:
            print('%5d %-6s leg %d deck %2d x %5d y %5d face %2d att %2d air %4d w %d/%d score %d'
                  % (tick, phase, leg, s['deck'], s['x'], s['y'], s['face'], s['att'], s['air'],
                     s['wtype'], s['wcount'], s['score']))
            last = (phase, leg)
    for d in m.drops:
        print('drop at tick %s x %s, predicted %s, target %s' % d)
    for h in m.impacts:
        print('impact at tick %d: record %d type %d x %d y %d low %d' % h)
    if args.emit:
        print(emit(args.plan, script))
    else:
        print(json.dumps(script))
    print('ticks %d, vblanks %d' % (m.ticks, m.vblanks))
    return 0


if __name__ == '__main__':
    sys.exit(main())
