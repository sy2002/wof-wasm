# tools/m6_autopilot.py, lines 282-294, a part of dogfight (lines 244-294)
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
