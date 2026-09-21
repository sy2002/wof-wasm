"""An autopilot on the headless original, which is how the flying scripts of M4 were found.

A script is a fixed raw schedule (tools/m4_scripts.py). Some are hard to write blind: a
landing needs the aircraft low over the bow at the right moment. This module flies the
headless original with a policy that looks at the player's state every VBlank and chooses
the stick and the button, and records what it chose; the record, compressed into
[VBlanks, letters] runs, is the script. The original is deterministic for a given schedule,
so the recorded script flies the same flight again without the autopilot.

    .venv/bin/python tools/m4_autopilot.py landing          fly it and print the script
    .venv/bin/python tools/m4_autopilot.py turns

What each policy does and why is in re/notes/porting-m4.md, "The scripts of part 2".
"""
import argparse
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import headless                                              # noqa: E402
import pass_observe                                          # noqa: E402

PLAYER = 0x025078
PREFIX = pass_observe.FRONT + [[40, ''], [3, 'F'], [60, ''], [460, 'R']]


def s16(v):
    return v - 0x10000 if v & 0x8000 else v


class Pilot(headless.Headless):
    """The headless original with its raw input chosen by a policy after the prefix."""

    def __init__(self, prefix, policy, **options):
        super().__init__({'raw': prefix + [[1, '']], 'stop': {'vblanks': 1 << 30}}, **options)
        self.prefix_len = sum(entry[0] for entry in prefix)
        self.policy = policy
        self.log = []
        self.phase = None
        self.mark = 0

    def state(self):
        o = self.o
        return {'deck': s16(o.r16(PLAYER + 0x0C)), 'y': s16(o.r16(PLAYER)),
                'x': s16(o.r16(PLAYER + 0x02)), 'face': s16(o.r16(PLAYER + 0x14)),
                'sx': s16(o.r16(PLAYER + 0x16)), 'sy': s16(o.r16(PLAYER + 0x18)),
                'air': s16(o.r16(0x025414)), 'att': s16(o.r16(0x02540E)),
                'step': s16(o.r16(0x024F36)), 'lives': o.read(0x02535C, 1)[0]}

    def go(self, phase):
        self.phase = phase
        self.mark = self.ticks

    def since(self):
        return self.ticks - self.mark

    def _next_raw(self):
        if self.vblanks < self.prefix_len:
            return super()._next_raw()
        letters = self.policy(self, self.state())
        self.log.append(letters)
        return headless.raw_state(letters), []


def compress(log):
    out = []
    for letters in log:
        if out and out[-1][1] == letters:
            out[-1][0] += 1
        else:
            out.append([1, letters])
    return out


# ------------------------------------------------------------------------------ landing

BOW = 7344                     # the carrier's deck ends at x 6608 and 7344 (0x0253FC, FE)
LIFT = 7032                    # player_start_x, where the lift is


def landing(m, s):
    """Take off to the right, fly out, turn and come back from the right low over the bow
    (the manual, page 6), put the aircraft on the deck and hold the stick forward, which
    keeps 0x025A9C clear so that the hook can catch a cable (0x01C5B8, 0x01B93E); then taxi
    to the lift, go down, take the next weapon, come up and take off again."""
    ph = m.phase or 'climb'
    m.phase = ph
    if ph == 'climb':
        if s['y'] > 120:
            m.go('out')
        return 'RU'
    if ph == 'out':
        if s['x'] > 8200:
            m.go('turn')
        return 'R'
    if ph == 'turn':
        if s['face'] == -1:
            m.go('approach')
        return 'L'
    if ph == 'approach':
        dist = s['x'] - BOW
        target = 36 + max(dist, 0) * 0.08                      # a glide path to the bow
        if dist < 20:
            m.go('stall')
        want = max(min((target - s['y']) / 4.0, 3), -4)
        if s['sy'] < want - 1:
            return 'LU'
        if s['sy'] > want + 1:
            return 'LD'
        return 'L'
    if ph in ('stall', 'down'):
        if s['deck'] == 7:
            m.go('caught')
        elif s['deck'] != 0:
            m.phase = 'down'
        return 'U'
    if ph == 'caught':
        if m.since() > 40:
            m.go('taxi')
        return ''
    if ph == 'taxi':
        dist = s['x'] - LIFT
        if abs(dist) <= 2 and s['air'] == 0:
            m.go('lift')
            return ''
        if abs(dist) <= s['air'] * s['air'] / 1600.0 + 2:       # coast to a stop there
            return ''
        return 'L' if dist > 0 else 'R'
    if ph == 'lift':
        if m.since() < 1:
            return 'F'
        if s['deck'] == 1 and s['y'] <= 0:
            m.go('hold')
        return ''
    if ph == 'hold':
        t = m.since()
        if t < 20 or 22 <= t < 40:
            return ''
        if t < 22:
            return 'D'                                         # the next weapon
        m.go('chosen')
        return 'F'
    if ph == 'chosen':
        if m.since() < 1:
            return 'F'
        if s['deck'] == 1 and s['y'] > 30:
            m.go('roll')
        return ''
    if ph == 'roll':
        if s['deck'] == 0:
            m.go('away')
        return 'R' if s['deck'] == 1 and (s['face'] == -1 or s['x'] < 7300) else 'RU'
    if ph == 'away':
        return 'RU' if m.since() < 40 else 'R'
    return ''


def landing_done(m, s):
    return m.phase == 'away' and m.since() >= 60


# -------------------------------------------------------------------------------- turns

def turns(m, s):
    """Turns both ways low and high, level, climbing and diving, one in the eighth-scale
    view and one at the ceiling; a glide with the stick left alone, in which the airspeed
    falls to its floor of 1000 (0x01C0C4) and the aircraft sinks; the stick forward alone
    while flying left, the manual's stall, which sets 0x025AAA (0x01C31E). The view changes
    to the eighth scale at about y 190, so the low turns stay below 170."""
    ph = m.phase or 'climb'
    m.phase = ph
    if ph == 'climb':                                          # off the deck and up
        if s['y'] > 110:
            m.go('level')
        return 'RU'
    if ph == 'level':
        if m.since() > 30:
            m.go('turn-left')
        return 'R' if s['y'] > 100 else 'RU'
    if ph == 'turn-left':                                      # a level turn, low
        if s['face'] == -1 and m.since() > 20:
            m.go('climb-left')
        return 'LU' if s['y'] < 100 else 'L'
    if ph == 'climb-left':
        if s['y'] > 160:
            m.go('turn-right-climbing')
        return 'LU'
    if ph == 'turn-right-climbing':
        if s['face'] == 1 and m.since() > 10:
            m.go('dive-right')
        return 'RU' if s['y'] < 170 else 'R'
    if ph == 'dive-right':
        if s['y'] < 110:
            m.go('turn-left-diving')
        return 'RD'
    if ph == 'turn-left-diving':
        if s['face'] == -1 or s['y'] < 70:
            m.go('up-high')
        return 'LD' if s['y'] > 90 else 'L'
    if ph == 'up-high':                                        # into the eighth-scale view
        if s['step'] == 1 and s['y'] > 700:
            m.go('turn-right-high')
        return 'LU'
    if ph == 'turn-right-high':
        if s['face'] == 1 and m.since() > 10:
            m.go('glide')
        return 'R'
    if ph == 'glide':                                          # the stick left alone
        if s['air'] <= 1000 and m.since() > 40:
            m.go('turn-left-high')
        return ''
    if ph == 'turn-left-high':
        if s['face'] == -1 and m.since() > 10:
            m.go('stall')
        return 'L'
    if ph == 'stall':                                          # forward alone, flying left
        if m.since() > 60:
            m.go('ceiling')
        return 'U'
    if ph == 'ceiling':
        if s['y'] >= 1100 and m.since() > 20:
            m.go('turn-right-ceiling')
        if m.since() > 400:
            m.go('turn-right-ceiling')
        return 'LU'
    if ph == 'turn-right-ceiling':
        if s['face'] == 1 and m.since() > 10:
            m.go('home')
        return 'R'
    if ph == 'home':
        return 'RD' if s['y'] > 400 else 'R'
    return ''


def turns_done(m, s):
    return m.phase == 'home' and m.since() >= 40


# --------------------------------------------------------------------------------- fuel

FUEL_Y = 400                   # the height the fuel flight holds
FUEL_LEGS = (7600, 11000)      # it turns at these x: over the sea, clear of the island


def fuel(m, s):
    """Back and forth over the sea east of the carrier, at a steady height, until the fuel
    runs out and the aircraft falls into the sea; then the next aircraft, left alone in the
    hold.  Left alone for 1,349 ticks the enemy's countdown brings the enemy aircraft
    (0x01BC02, M6); only the button raises it again, to 750.  Held in level flight the
    button fires the guns (M5) and tapped it drops a weapon (M5), so it is held only inside
    a turn, from attitude 4 to 20, where it does neither (0x01B5B0).  The legs take about
    250 ticks, well inside the 750."""
    ph = m.phase or 'climb'
    m.phase = ph
    vertical = ''
    if s['deck'] == 0:
        want = max(min((FUEL_Y - s['y']) / 8.0, 3), -3)
        if s['sy'] < want - 1:
            vertical = 'U'
        elif s['sy'] > want + 1:
            vertical = 'D'
    ahead = 'R' if s['face'] == 1 else 'L'
    back = 'L' if s['face'] == 1 else 'R'
    if ph == 'climb':
        if s['y'] > FUEL_Y - 40:
            m.go('cruise')
        return 'RU'
    if ph == 'cruise':
        if s['deck'] != 0:
            m.go('down')
            return ''
        if (s['face'] == 1 and s['x'] > FUEL_LEGS[1]) or (s['face'] == -1 and s['x'] < FUEL_LEGS[0]):
            m.go('turn')
            m.turn_from = s['face']
            m.button = False
            return back + vertical
        return ahead + vertical
    if ph == 'turn':
        if s['deck'] != 0:
            m.go('down')
            return ''
        if s['face'] != m.turn_from and s['att'] == 0:
            m.go('cruise')
            return ahead + vertical
        stick = 'L' if m.turn_from == 1 else 'R'
        if 4 <= s['att'] <= 20:
            m.button = True
        elif s['att'] > 20 or s['att'] == 0:
            m.button = False
        return stick + vertical + ('F' if m.button else '')
    return ''                                                  # down: the next aircraft waits


def fuel_done(m, s):
    return m.phase == 'down' and s['deck'] == 1 and s['y'] <= 0 and m.since() > 200


POLICIES = {'landing': (landing, landing_done), 'turns': (turns, turns_done),
            'fuel': (fuel, fuel_done)}


def fly(name, max_ticks=8000, verbose=False):
    """Fly a policy; returns (script, machine, trail of (tick, phase, state))."""
    policy, done = POLICIES[name]
    m = Pilot(PREFIX, policy)
    trail = []
    while m.ticks < max_ticks:
        if m.run(until='tick') != 'tick':
            break
        s = m.state()
        trail.append((m.ticks, m.phase, s))
        if verbose:
            print(m.ticks, m.phase, s)
        if done(m, s):
            break
    return PREFIX + compress(m.log), m, trail


def main():
    parser = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    parser.add_argument('name', choices=sorted(POLICIES))
    parser.add_argument('--verbose', action='store_true')
    args = parser.parse_args()
    script, m, trail = fly(args.name, verbose=args.verbose)
    last = None
    for tick, phase, s in trail:
        if phase != last:
            print('%5d %-22s deck %2d x %5d y %5d face %2d air %4d step %d lives %d'
                  % (tick, phase, s['deck'], s['x'], s['y'], s['face'], s['air'], s['step'],
                     s['lives']))
            last = phase
    print(json.dumps(script))
    return 0


if __name__ == '__main__':
    sys.exit(main())
