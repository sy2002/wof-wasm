"""The autopilot of M6: the enemy aircraft, the ships and the carrier's defence, flown on the
headless original.

tools/m5_autopilot.py takes off with a weapon and flies legs with actions on them; this
module flies the same way on any of the fifteen maps and adds what M6 needs: the enemy's
countdown left to run out (the plan's `countdown`), the guns at an enemy aircraft (a
dogfight), the torpedo at a ship, a crash on a ship's deck, and waiting on the carrier's deck
while the enemy attacks it.  Its choices, compressed into [VBlanks, letters] runs, are the
script; the original flies the same flight again without the autopilot (tools/m6_scripts.py
keeps them).

    .venv/bin/python tools/m6_autopilot.py PLAN            fly a plan of PLANS, print the script
    .venv/bin/python tools/m6_autopilot.py PLAN --verbose  and the enemy aircraft tick by tick

A plan names its map by the rank chosen in the rank selection and the mission number poked
at the selection's end (0x01009E), as the setups of tests/test_mission.py reach every map;
the rest is a plan of tools/m5_autopilot.py.  What each plan reaches is in
re/notes/porting-m6.md, "The scripts".
"""
import argparse
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import headless                                              # noqa: E402
import m4_autopilot                                          # noqa: E402
import m5_autopilot                                          # noqa: E402
import pass_observe                                          # noqa: E402

s16 = m4_autopilot.s16
PLAYER = 0x025078
AIRCRAFT = 0x02522A
SHIPS = 0x025460
SHIP_NAMES = ('destroyer', 'battleship', 'cruiseship', 'japcarrier', 'carrier')
AIRFIELDS = 0x0252FA
MISSION_NUMBER = 0x0253C0
KILLS = 0x02537F
WRECKS = 0x0251D8
FIGHTERS = 0x0251D6


def rank_prefix(rank):
    """The front end with the rank selection's cursor moved `rank` places down, as
    tools/reach_observe.py's rank_script and the setups of tests/test_mission.py choose a
    rank, and 40 VBlanks into the hold."""
    return (pass_observe.FRONT[:4] + [[4, '']] + [[2, 'D'], [10, '']] * rank +
            [[3, 'F'], [30, ''], [3, 'F'], [40, '']])


def prefix_of(plan):
    """The raw prefix a plan starts from: M5's for the first rank, else the rank chosen."""
    rank = plan.get('rank', 0)
    return pass_observe.FRONT + [[40, '']] if rank == 0 else rank_prefix(rank)


def aircraft(o):
    """The enemy aircraft records in use, as dicts of their fields (re/notes/porting-m6.md)."""
    out = []
    for i in range(4):
        a = AIRCRAFT + 0x34 * i
        w = [s16(o.r16(a + 2 * k)) for k in range(26)]
        if w[0]:
            out.append({'i': i, 'state': w[0], 'mode': w[1], 'rel': w[2], 'order': w[3],
                        'health': w[4], 'burst': w[5], 'w0c': w[6], 'w0e': w[7],
                        'timer': w[8], 'fire': w[9], 'face': w[10], 'att': w[11],
                        'w18': w[12], 'w1a': w[13], 'speed': w[14], 'want_speed': w[15],
                        'x': w[16], 'w22': w[17], 'want_y': w[18], 'y': w[19],
                        'dx': w[20], 'w2a': w[21], 'flash': w[22], 'draw_x': w[23],
                        'frame': w[24], 'w32': w[25]})
    return out


def ships(o):
    out = []
    for i, name in enumerate(SHIP_NAMES):
        a = SHIPS + 0x1E * i
        if o.r16(a + 4):
            out.append({'ship': name, 'span': (s16(o.r16(a)), s16(o.r16(a + 2))),
                        'hits': s16(o.r16(a + 0x0C)), 'w12': s16(o.r16(a + 0x12)),
                        'w18': s16(o.r16(a + 0x18)), 'row': s16(o.r16(a + 0x1A))})
    return out


class Enemy(m5_autopilot.Attack):
    """The headless original flown by an M6 plan: any rank, any mission."""

    def __init__(self, plan, **options):
        self.base = plan
        self.sortie = 0
        plan = self.sortie_plan(0)
        self.plan = plan
        m4_autopilot.Pilot.__init__(self, prefix_of(plan), policy, **options)
        if plan.get('mission'):
            self.stop_at(0x01009E, lambda: self.o.write(MISSION_NUMBER,
                                                         bytes([0, plan['mission']])))
        for address, entry in plan.get('pokes', {}).items():
            size, value = entry[0], entry[1]
            at = entry[2] if len(entry) > 2 else 0x01009E
            self.stop_at(at, lambda a=address, n=size, v=value:
                         self.o.write(a, (v & ((1 << (8 * n)) - 1)).to_bytes(n, 'big')))
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

    def state(self):
        s = super().state()
        o = self.o
        s['enemies'] = aircraft(o)
        s['ships'] = ships(o)
        s['kills'] = o.read(KILLS, 1)[0]
        s['carrier'] = s16(o.r16(SHIPS + 4 * 0x1E + 0x0C))
        s['countdown'] = o.r16(PLAYER + 0x1C)
        s['pitch_target'] = s16(o.r16(0x025402))
        return s


def met(m, s, cond):
    """A plan's condition on the state, or a list of them of which any will do: ('carrier', n) the carrier has n hits left or fewer,
    ('kills', n) n enemy aircraft shot down, ('down',) the aircraft is coming down or lost
    (deck state 4, 6 or 8), ('ticks', n) the tick count, ('gone', ship) that enemy ship no
    longer afloat."""
    if isinstance(cond, list):
        return any(met(m, s, c) for c in cond)
    kind = cond[0]
    if kind == 'carrier':
        return s['carrier'] <= cond[1]
    if kind == 'kills':
        return s['kills'] >= cond[1]
    if kind == 'down':
        return s['deck'] in (4, 6, 8)
    if kind == 'ticks':
        return m.ticks >= cond[1]
    if kind == 'gone':
        return not any(sh['ship'] == cond[1] and sh['hits'] > 0 for sh in s['ships'])
    if kind == 'mode':
        return any(e['mode'] & cond[1] for e in s['enemies'])
    if kind == 'after':
        return m.ticks >= getattr(m, 'stage_tick', 0) + cond[1]
    raise ValueError(cond)


def policy(m, s):
    """M5's attack with M6's parts laid over it: the plan's `wait` keeps the aircraft in the
    hold until its condition holds, `until` ends the legs when its condition holds, an `end`
    of 'land' brings the aircraft back onto the carrier and into the hold, and a leg's
    `dogfight` takes the stick while an enemy aircraft is in the air near the aircraft."""
    plan = m.plan
    if plan.get('wait') and m.phase in (None, 'hold') and not getattr(m, 'waited', False):
        if not met(m, s, plan['wait']):
            m.phase = 'hold'
            m.open_tick = m.ticks
            return ''
        m.waited = True
    if plan.get('until') and m.phase in ('leg', 'turn', 'dogfight') and met(m, s, plan['until']):
        then = plan.get('then')
        if then == 'orbit':
            # Back over the place where it happened, and over it again: 700 pixels each way.
            x0, face = s['x'], s['face']
            back, ahead = ('L', 'R') if face > 0 else ('R', 'L')
            plan = m.plan = dict(plan, until=('after', plan.get('orbit', 900)), then=None,
                                 legs=[{'dir': back, 'y': 150, 'to': x0 - 700 * face},
                                       {'dir': ahead, 'y': 150, 'to': x0 + 700 * face}] * 3)
            m.leg = 0
            m.stage_tick = m.ticks
            m.phase = 'leg'
        elif then:
            plan = m.plan = dict(plan, **then)
            plan.setdefault('then', None)
            if 'then' not in then:
                plan['then'] = None
            m.leg = 0
            m.stage_tick = m.ticks
            m.phase = 'leg'
        else:
            m.go('end')
    if m.phase == 'end' and plan.get('end') == 'land' and s['deck'] == 0:
        m.go('land')
        m.land = 'out'
    if m.phase == 'land':
        if s['deck'] == 1 and s['y'] <= 0 and getattr(m, 'land', '') == 'button':
            m.go('end')
            m.landed = True
            return ''
        return m5_autopilot.land(m, s)
    if m.phase == 'end' and getattr(m, 'landed', False):
        return ''
    if m.phase == 'dogfight':
        letters = dogfight(m, s)
        if letters is not None:
            return letters
        m.phase = 'leg'                       # nothing left to fight: back to the legs
    letters = m5_autopilot.attack(m, s)
    if m.phase != 'leg' or m.leg >= len(plan['legs']) or s['deck'] != 0:
        return letters
    leg = plan['legs'][m.leg]
    for act in leg.get('do', ()):
        if act[0] == 'dogfight' and s['kills'] < act[3] and target(m, s, act) is not None:
            m.fight = act
            m.phase = 'dogfight'
            return dogfight(m, s) or letters
    return letters


def done(m, s):
    return m.phase == 'end' and m.since() >= m.plan.get('tail', 60)


def target(m, s, act):
    """The enemy aircraft to fight: flying (state 2), of the kind the action names (a mask
    of +0x02), within the stretch and 2,500 pixels of the aircraft, the nearest; once
    chosen it is kept while it flies."""
    lo, hi = sorted(act[1:3])
    mask = act[4] if len(act) > 4 else 0xFF
    if not lo <= s['x'] <= hi:
        return None
    live = [e for e in s['enemies'] if e['state'] == 2 and e['mode'] & mask and
            lo <= e['x'] <= hi and abs(e['x'] - s['x']) < 2500]
    kept = [e for e in live if e['i'] == getattr(m, 'chosen', None)]
    if kept:
        return kept[0]
    if not live:
        m.chosen = None
        return None
    e = min(live, key=lambda e: abs(e['x'] - s['x']))
    m.chosen = e['i']
    return e


def dogfight(m, s):
    """The guns at an enemy aircraft: they hit one that flies the same way ahead of the
    aircraft (+0x04 of 3) within 0xA0 pixels and 0x14 of height while the pitch target is 0
    (guns, 0x01B6E0), 19 bursts of hits for the first to bring it down from +0x08 0xF0 below
    0x60.  So: behind it and the same way, level with the stick left alone and the button
    held.  The airspeed is managed so that it is met at 10 pixels a tick about 100 pixels
    behind it (the direction held raises the airspeed by 8 a tick up to 1400, 14 pixels a
    tick; let go it falls by 4 to 1000, 10 pixels a tick, and the pitch target stays 0);
    its height is matched with short pushes of the stick once the chase is close.  Coming
    the other way it is let past and then followed with a turn, which is made above 120
    pixels because a turn dives.  None: nothing to fight."""
    act = m.fight
    e = target(m, s, act)
    if e is None or s['kills'] >= act[3] or s['deck'] != 0:
        return None
    face = s['face']
    gap = (e['x'] - s['x']) * face             # positive while it is ahead
    same = e['face'] == face
    way = 'R' if face > 0 else 'L'
    back = 'L' if face > 0 else 'R'
    low = act[5] if len(act) > 5 else 34
    safe = 130
    if s['att'] != 0:                          # inside a turn: keep turning, and up
        return m.turn_way + m5_autopilot.hold_height(s, safe + 20, gain=4.0, limit=2)
    # Behind us, or coming head on within 250 pixels: turn now, so that after the turn (about
    # 50 ticks) it is ahead the same way.
    behind = (gap < -30 and (not same or gap < -300)) or (not same and 0 <= gap < 250)
    if behind:
        if s['y'] < safe - 10:
            return way + 'U'                   # climb before the turn
        m.turn_way = back
        return back
    if not same:
        # Head on, or going away the other way: hold the course high until it has passed.
        return way + m5_autopilot.hold_height(s, safe + 20, gain=4.0, limit=3)
    dy = e['y'] - s['y']
    if gap > 800:
        return way + m5_autopilot.hold_height(s, max(e['y'], low, 60), gain=4.0, limit=3)
    # The chase.  A torpedo plane chased from behind (0x01DEB0) wants the player's airspeed
    # less the gap beyond 150 (+0x1E from +0x28), so it keeps about 150 pixels ahead by
    # itself, inside the guns' reach, and jinks to heights of 35 to 95; the chase holds full
    # speed and follows the height with short pushes, each with the direction, because
    # forward alone while flying left is the stall (0x025AAA).
    # The button is held through the whole close chase, corrections included: the guns need
    # it held for ten VBlanks before they fire (the hold latch), and a press let go sooner
    # would drop the other weapon (the tap latch).
    push = way if gap > 100 or s['air'] < 1000 else ''
    fire = 'F' if 0 < gap < 400 else ''
    if abs(dy) >= 14 or s['y'] < low:
        return way + m5_autopilot.hold_height(s, max(e['y'], low), gain=2.0, limit=3) + fire
    return push + fire


# ------------------------------------------------------------------------------ the plans

# The maps' enemy content, from `tools/m6_observe.py maps` (world x): map a's carrier at
# 6592-7360; map d's airfield at 3200-3544; map e's at 15664-16008; map f's cruise ship at
# 5296-5424 (the carrier at 7976-8744); map g's cruise ship at 18704-18832; map h's destroyer
# at 21520-22160; map i's destroyer at 6544-7184, cruise ship at 17520-17648 and airfield at
# 3120-3464; map j's destroyer at 8-648 and battleship at 7160-7928; map k's battleship at
# 6064-6832; map l's destroyer at 14352-14992 and battleship at 0-768; map m's battleship at
# 0-768 and Japanese carrier at 22000-22624; map n's destroyer at 2696-3336; map o's
# Japanese carrier at 8-632, battleship at 20600-21368, destroyer at 27064-27704 and
# airfield at 3672-4016.  A ship's aircraft go up while the player is within its block's
# range (the Japanese carrier's at 21750-22020 on map m and -242-28 on map o).
NIGHT_FLAG = 0x025390
EAST_A = [{'dir': 'R', 'y': 150, 'to': 10000}, {'dir': 'L', 'y': 150, 'to': 8200}]


def over(ship, pad=600, y=150, times=2, start='L'):
    """Legs back and forth over a stretch of world x, `times` times each way."""
    lo, hi = ship
    first, second = ({'dir': 'L', 'y': y, 'to': lo - pad}, {'dir': 'R', 'y': y, 'to': hi + pad})
    legs = [first, second] if start == 'L' else [second, first]
    return legs * times


PLANS = {
    # Map a, the countdown left to run: out east of the carrier and back and forth while the
    # torpedo plane comes and drops; once the carrier is hit, the landing on it.
    'enemy_a': {'countdown': True, 'legs': EAST_A * 20, 'until': ('carrier', 3),
                'end': 'land', 'tail': 40},
    # Map a: the countdown's torpedo planes fought with the guns until one is shot down;
    # then back over the place where it came down (its wreck on the water).
    'fight_a': {'countdown': True, 'legs': [
        {'dir': 'R', 'y': 150, 'to': 16000, 'do': [('dogfight', -8000, 30000, 1, 0x14)]},
        {'dir': 'L', 'y': 150, 'to': 12000, 'do': [('dogfight', -8000, 30000, 1, 0x14)]},
    ] * 20, 'until': ('kills', 1), 'then': 'orbit', 'orbit': 1100, 'end': 'level', 'tail': 20},
    # Map a: the same over the island (32 to 3944), so that the aircraft shot down comes down
    # on land, where it burns (state 0x10) and leaves its wreck (0x01E398); the countdown
    # runs out with the aircraft west of the deck, so the torpedo plane comes from the west.
    'fight_island_a': {'countdown': True, 'legs': [
        {'dir': 'L', 'y': 150, 'to': 900, 'do': [('dogfight', 400, 3700, 1, 0x14)]},
        {'dir': 'R', 'y': 150, 'to': 3400, 'do': [('dogfight', 400, 3700, 1, 0x14)]},
    ] * 30, 'until': ('kills', 1), 'then': 'orbit', 'orbit': 1100, 'end': 'level', 'tail': 20},
    # Map a: the carrier left to the torpedo planes from the hold until one hit is left, then
    # the aircraft up and out east until the carrier is sunk, and back to land on it.
    'sunk_a': {'countdown': True, 'wait': ('carrier', 1), 'legs': EAST_A * 20,
               'until': ('carrier', 0), 'end': 'land', 'tail': 200},
    # Map a with the kill counter poked above 99: the counter shows 99 and fourteen icons.
    'kills_a': {'pokes': {0x02537F: (1, 120)}, 'legs': [{'dir': 'R', 'y': 150, 'to': 9000}],
                'end': 'level', 'tail': 40},
    # Map a with three wrecks of enemy aircraft on the water, as an aircraft shot down over
    # land leaves them (0x01E476), poked into the list after the mission's reset of its
    # tables (0x0100D6, which clears the count at 0x0135C0): out east and back over them low,
    # then high in the eighth-scale view.
    'wrecks_a': {'pokes': {0x0251D8: (2, 3, 0x0100D6), 0x0251DA: (2, -6900, 0x0100D6),
                           0x0251DC: (2, 7400, 0x0100D6), 0x0251DE: (2, -8300, 0x0100D6)},
                 'legs': [{'dir': 'R', 'y': 150, 'to': 9000}, {'dir': 'L', 'y': 150, 'to': 6000},
                          {'dir': 'R', 'y': 420, 'to': 9000}, {'dir': 'L', 'y': 420, 'to': 6000}],
                 'end': 'level', 'tail': 20},
    # Maps b and c: the countdown's torpedo plane, until it has dropped its torpedo.
    'countdown_b': {'mission': 2, 'countdown': True,
                    'legs': [{'dir': 'R', 'y': 150, 'to': 9000},
                             {'dir': 'L', 'y': 150, 'to': 7200}] * 20,
                    'until': ('mode', 0x10), 'then': {'until': ('after', 150)}, 'tail': 10},
    'countdown_c': {'mission': 3, 'countdown': True,
                    'legs': [{'dir': 'R', 'y': 150, 'to': 8800},
                             {'dir': 'L', 'y': 150, 'to': 7000}] * 20,
                    'until': ('mode', 0x10), 'then': {'until': ('after', 150)}, 'tail': 10},
    # Map d: back and forth over the airfield; its fighters shoot until the engine seizes.
    'oil_d': {'rank': 1, 'mission': 1, 'legs': over((3200, 3544), times=6),
              'until': ('down',), 'tail': 200},
    # The same as a night mission (night_flag poked at the rank selection's end).
    'night_d': {'rank': 1, 'mission': 1, 'pokes': {NIGHT_FLAG: (2, 1)},
                'legs': over((3200, 3544), times=6), 'until': ('down',), 'tail': 200},
    # Map e: out east past the airfield and back over it.
    # Map e: out east past the airfield and back over it, then over it high in the
    # eighth-scale view with its fighter on the aircraft's tail.
    'airfield_e': {'rank': 1, 'mission': 2, 'legs': over((15664, 16008), times=2, start='R') +
                   over((15664, 16008), y=420, times=1, start='R'),
                   'until': [('after', 1500), ('down',)], 'end': 'level', 'tail': 10},
    # Map f: over the cruise ship, its guns firing; its aircraft go up.
    'cruise_f': {'rank': 1, 'mission': 3, 'legs': over((5296, 5424), times=3),
                 'until': ('after', 1000), 'end': 'level', 'tail': 10},
    # Map f: the torpedo (the menu one step down): west high over the carrier, down to 24
    # pixels past it, the torpedo dropped east of the cruise ship, which it runs into; then
    # up and away over the ship and back.
    'torpedo_f': {'rank': 1, 'mission': 3, 'menu': 'D', 'legs': [
        {'dir': 'L', 'y': 150, 'to': 7300},
        {'dir': 'L', 'y': 24, 'to': 5750, 'do': [('drop', 5880)]},
        {'dir': 'L', 'y': 150, 'to': 4600}, {'dir': 'R', 'y': 150, 'to': 6200},
        {'dir': 'L', 'y': 150, 'to': 4800}], 'until': ('down',), 'end': 'level', 'tail': 200},
    # Map f: straight down onto the cruise ship's deck.
    'crash_f': {'rank': 1, 'mission': 3, 'legs': [{'dir': 'L', 'y': 120, 'to': 5560}],
                'end': 'crash', 'tail': 400, 'once': True},
    # Map f: low into the cruise ship's side, below its deck: the wreck slides back along it
    # with the sky's flash (0x01B0E2, flash_set).
    'crash_side_f': {'rank': 1, 'mission': 3, 'legs': [
        {'dir': 'L', 'y': 150, 'to': 7300}, {'dir': 'L', 'y': 16, 'to': 4800}],
                     'until': ('down',), 'tail': 400},
    # Map f: rockets (the menu one step up) in a dive at the cruise ship's guns.
    'rockets_f': {'rank': 1, 'mission': 3, 'menu': 'U', 'legs': [
        {'dir': 'L', 'y': 150, 'to': 4900, 'do': [('rocket', 5360, 245, 115)]},
        {'dir': 'R', 'y': 150, 'to': 6000}], 'end': 'level', 'tail': 200, 'once': True},
    # The ships of maps g to o: out to the ship and back and forth over it, its guns firing
    # and its aircraft going up, until the aircraft is brought down or the legs are flown.
    'cruise_g': {'rank': 2, 'mission': 1, 'legs': over((18704, 18832), times=1, start='R') +
                 over((18704, 18832), y=420, times=1, start='R'),
                 'until': ('down',), 'end': 'level', 'tail': 200},
    'destroyer_h': {'rank': 2, 'mission': 2, 'legs': over((21520, 22160), times=2, start='R'),
                    'until': ('down',), 'end': 'level', 'tail': 200},
    'ships_i': {'rank': 3, 'mission': 1, 'legs': [
        {'dir': 'L', 'y': 150, 'to': 5900}, {'dir': 'R', 'y': 150, 'to': 7800},
        {'dir': 'L', 'y': 150, 'to': 2800}], 'until': ('down',), 'end': 'level', 'tail': 200},
    'battleship_j': {'rank': 3, 'mission': 2, 'legs': over((7160, 7928), times=2, start='R'),
                     'until': ('down',), 'end': 'level', 'tail': 200},
    'battleship_k': {'rank': 4, 'mission': 1, 'legs': over((6064, 6832), times=2),
                     'until': ('down',), 'end': 'level', 'tail': 200},
    'destroyer_l': {'rank': 5, 'mission': 1, 'legs': over((14352, 14992), times=2, start='R'),
                    'until': ('down',), 'end': 'level', 'tail': 200},
    'japcarrier_m': {'rank': 6, 'mission': 1, 'legs': [
        {'dir': 'R', 'y': 150, 'to': 22900}, {'dir': 'L', 'y': 150, 'to': 21700},
        {'dir': 'R', 'y': 150, 'to': 22900}, {'dir': 'L', 'y': 150, 'to': 21700}],
                     'until': ('down',), 'end': 'level', 'tail': 200},
    'destroyer_n': {'rank': 6, 'mission': 2, 'legs': over((2696, 3336), times=2),
                    'until': ('down',), 'end': 'level', 'tail': 200},
    # Map o: west high in the eighth-scale view over the airfield (3672-4016, its aircraft
    # rolling east to take off), then down to the Japanese carrier at the map's west end.
    'japcarrier_o': {'rank': 6, 'mission': 3, 'legs': [
        {'dir': 'L', 'y': 420, 'to': 3000},
        {'dir': 'L', 'y': 150, 'to': -150}, {'dir': 'R', 'y': 150, 'to': 1200},
        {'dir': 'L', 'y': 150, 'to': -150}, {'dir': 'R', 'y': 150, 'to': 1200}],
                     'until': ('down',), 'end': 'level', 'tail': 200},
    # Probes, not scripts.
    'probe_a': {'countdown': True, 'legs': [
        {'dir': 'R', 'y': 150, 'to': 9000}, {'dir': 'L', 'y': 150, 'to': 6000},
    ] * 6, 'end': 'level', 'tail': 100},
    'probe_d': {'rank': 1, 'mission': 1, 'legs': [
        {'dir': 'L', 'y': 150, 'to': 2600}, {'dir': 'R', 'y': 150, 'to': 4200},
    ] * 8, 'end': 'level', 'tail': 100},
}


def fly(plan, max_ticks=6000, verbose=False, every=16):
    m = Enemy(plan)
    m.every = every
    trail = []
    seen = {}
    while m.ticks < max_ticks:
        try:
            if m.run(until='tick', wall_limit=120.0) != 'tick':
                break
        except headless.Stuck:
            break                             # the game is over and waits in the front end
        if m.o.read(0x02464E, 1)[0]:
            break                             # outside_mission: the mission has ended
        s = m.state()
        trail.append((m.ticks, m.phase, m.leg, s))
        if verbose:
            for e in s['enemies']:
                key = (e['state'], e['mode'], e['rel'])
                if seen.get(e['i']) != key or m.ticks % m.every == 0:
                    print('%5d %-8s %-3s p x %5d y %4d sy %2d pt %5d air %4d deck %2d oil %3d lives %d kills %d carrier %d | '
                          '%d: state %x mode %x rel %d x %5d y %4d att %2d face %2d fire %d '
                          'health %x speed %d' % (
                              m.ticks, m.phase, m.log[-1] if m.log else '', s['x'], s['y'], s['sy'], s['pitch_target'], s['air'], s['deck'], s['oil'], s['lives'],
                              s['kills'], s['carrier'], e['i'], e['state'], e['mode'],
                              e['rel'], e['x'], e['y'], e['att'], e['face'], e['fire'],
                              e['health'], e['speed']))
                    seen[e['i']] = key
        if done(m, s):
            break
    return prefix_of(plan) + m4_autopilot.compress(m.log), m, trail


def summary(m, trail):
    last = trail[-1][3] if trail else {}
    return {'ticks': m.ticks, 'vblanks': m.vblanks, 'phase': m.phase,
            'kills': last.get('kills'), 'carrier': last.get('carrier'),
            'lives': last.get('lives'), 'score': last.get('score'), 'oil': last.get('oil'),
            'ships': [(sh['ship'], sh['hits']) for sh in last.get('ships', [])],
            'most_enemies': max((len(t[3]['enemies']) for t in trail), default=0),
            'modes': sorted({e['mode'] for t in trail for e in t[3]['enemies']}),
            'states': sorted({e['state'] for t in trail for e in t[3]['enemies']})}


def fly_one(job):
    name, ticks = job
    script, m, trail = fly(PLANS[name], max_ticks=ticks)
    return name, script, summary(m, trail)


def fly_all(names, ticks, jobs, out):
    import concurrent.futures
    results = {}
    if os.path.exists(out):
        with open(out) as handle:
            results = json.load(handle)
    with concurrent.futures.ProcessPoolExecutor(max_workers=jobs) as pool:
        for name, script, info in pool.map(fly_one, [(n, ticks) for n in names]):
            results[name] = {'script': script, 'summary': info}
            print(name, json.dumps(info), flush=True)
            with open(out, 'w') as handle:
                json.dump(results, handle)
    return results


def main():
    parser = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    parser.add_argument('plan', nargs='?', choices=sorted(PLANS))
    parser.add_argument('--all', nargs='*', help='fly these plans in processes of their own')
    parser.add_argument('--jobs', type=int, default=8)
    parser.add_argument('--out', default='m6_flown.json')
    parser.add_argument('--verbose', action='store_true')
    parser.add_argument('--ticks', type=int, default=6000)
    parser.add_argument('--every', type=int, default=16)
    args = parser.parse_args()
    if args.all is not None:
        fly_all(args.all or [n for n in PLANS if not n.startswith('probe')], args.ticks,
                args.jobs, args.out)
        return 0
    script, m, trail = fly(PLANS[args.plan], max_ticks=args.ticks, verbose=args.verbose,
                           every=args.every)
    last = None
    for tick, phase, leg, s in trail:
        if (phase, leg) != last:
            print('%5d %-6s leg %d deck %2d x %5d y %5d face %2d att %2d oil %3d lives %d '
                  'kills %d score %d' % (tick, phase, leg, s['deck'], s['x'], s['y'], s['face'],
                                         s['att'], s['oil'], s['lives'], s['kills'], s['score']))
            last = (phase, leg)
    print(json.dumps(script))
    print('ticks %d, vblanks %d' % (m.ticks, m.vblanks))
    return 0


if __name__ == '__main__':
    sys.exit(main())
