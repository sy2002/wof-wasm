"""The mission scripts of M5, and a per-tick view of the weapons while one runs.

Every script is a raw schedule for tools/headless.py, a list of [VBlanks, letters] where the
letters are the stick and the button of that VBlank (U forward, D back, L, R, F;
re/notes/headless.md, "Input"), flown by tools/m5_autopilot.py's plans and kept here as the
autopilot printed them: the original is deterministic for a given schedule, so the recorded
schedule flies the same flight again.  Maps b and c are the second and third missions of the
first rank; they are reached as the M4 setups reach them, with mission_number poked at the
rank selection's end (`POKES`), because a campaign's next mission is M7's.

    .venv/bin/python tools/m5_scripts.py --list
    .venv/bin/python tools/m5_scripts.py trace bomb_a            the weapons, tick by tick
    .venv/bin/python tools/m5_scripts.py trace island_a --every 8 --from 600

`script(name)` returns the run description of any script of M4 or M5, and `SCRIPTS` names
M5's in the order the tests use.  What each one reaches is in re/notes/porting-m5.md, "The
scripts".
"""
import argparse
import json
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import headless                                              # noqa: E402
import m4_scripts                                            # noqa: E402
import pass_observe                                          # noqa: E402

# The front end and the first VBlanks in the hold, after which the autopilot takes over.
PLANE = pass_observe.FRONT + [[40, '']]

MISSION_NUMBER = 0x0253C0

# The guns held in three shallow dives over the sea east of the carrier, at 90 pixels and
# down to 30 (plan guns_sea): splashes in the water.
GUNS_SEA = PLANE + [
    [20, ''], [3, 'F'], [126, ''], [415, 'R'], [157, 'RU'], [39, 'RD'], [12, 'R'],
    [28, 'RU'], [12, 'R'], [12, 'RDF'], [56, 'RF'], [12, 'RUF'], [44, 'RF'], [16, 'RU'],
    [16, 'R'], [12, 'RU'], [12, 'R'], [12, 'RU'], [12, 'R'], [12, 'RU'], [20, 'R'],
    [8, 'RU'], [8, 'R'], [4, 'RU'], [4, 'R'], [4, 'RU'], [16, 'RDF'], [36, 'RF'],
    [4, 'RUF'], [4, 'RF'], [4, 'RUF'], [56, 'RF'], [20, 'RU'], [16, 'R'], [12, 'RU'],
    [12, 'R'], [12, 'RU'], [12, 'R'], [12, 'RU'], [12, 'R'], [12, 'RU'], [20, 'R'],
    [12, 'RDF'], [36, 'RF'], [12, 'RUF'], [12, 'RF'], [8, 'RDF'], [12, 'RF'], [4, 'RUF'],
    [20, 'RF'], [20, 'RU'], [16, 'R'], [12, 'RU'], [12, 'R'], [12, 'RU'], [12, 'R'],
    [4, 'RU'], [1, ''], [7, 'RU'], [12, 'R'], [12, 'RU'], [20, 'R'], [8, 'RU'], [8, 'R'],
    [4, 'RU'], [4, 'R'], [8, 'RU'], [8, 'R'], [8, 'RU'], [140, 'R'],
]

# The same over map a's island, flying left (plan guns_a): splashes on land; the targets'
# fire hits the aircraft.
GUNS_A = PLANE + [
    [20, ''], [3, 'F'], [126, ''], [415, 'R'], [157, 'RU'], [1, 'L'], [30, 'LD'],
    [24, 'LDF'], [36, 'LF'], [8, 'LUF'], [4, 'LF'], [8, 'LUF'], [20, 'LF'], [4, 'LUF'],
    [20, 'LF'], [4, 'LUF'], [8, 'LF'], [8, 'L'], [8, 'LU'], [1248, 'L'], [4, 'LDF'],
    [100, 'LF'], [4, 'LUF'], [4, 'LF'], [20, 'LU'], [16, 'L'], [8, 'LU'], [8, 'L'],
    [8, 'LU'], [24, 'LDF'], [8, 'LF'], [16, 'LUF'], [92, 'LF'], [16, 'LU'], [16, 'L'],
    [12, 'LU'], [12, 'L'], [12, 'LU'], [12, 'L'], [12, 'LU'], [20, 'L'], [4, 'LU'],
    [16, 'LDF'], [36, 'LF'], [12, 'LUF'], [24, 'LF'], [16, 'LU'], [16, 'L'], [12, 'LU'],
    [12, 'L'], [1, ''], [11, 'LU'], [12, 'L'], [12, 'LU'], [20, 'L'], [8, 'LU'], [8, 'L'],
    [4, 'LU'], [4, 'L'], [8, 'LU'], [152, 'L'],
]

# One bomb on each of map a's four targets from 150 pixels, flying left (plan bomb_a): the
# slot-3 targets at 3224 and 1736, the slot-4 targets at 2712 and 2392.
BOMB_A = PLANE + [
    [20, ''], [3, 'F'], [126, ''], [415, 'R'], [173, 'RU'], [1, 'L'], [22, 'LD'], [8, 'L'],
    [4, 'LDF'], [4, 'LF'], [4, 'LUF'], [48, 'LF'], [4, 'LUF'], [8, 'LF'], [4, 'LUF'],
    [20, 'LF'], [4, 'LUF'], [16, 'LF'], [4, 'LUF'], [8, 'LF'], [8, 'LUF'], [8, 'LU'],
    [8, 'L'], [12, 'LD'], [12, 'L'], [4, 'LD'], [36, 'L'], [4, 'LU'], [1160, 'L'],
    [4, 'LF'], [140, 'L'], [4, 'LF'], [88, 'L'], [4, 'LF'], [184, 'L'], [4, 'LF'],
    [168, 'L'], [1, ''], [799, 'L'],
]

# The same from 420 pixels, in the eighth-scale view (plan high_a).
HIGH_A = PLANE + [
    [20, ''], [3, 'F'], [126, ''], [415, 'R'], [369, 'RU'], [1, 'L'], [30, 'LD'],
    [12, 'LDF'], [24, 'LF'], [8, 'LUF'], [4, 'LF'], [4, 'LUF'], [28, 'LF'], [8, 'LUF'],
    [32, 'LF'], [4, 'LUF'], [8, 'LF'], [4, 'LUF'], [24, 'L'], [8, 'LU'], [1320, 'L'],
    [4, 'LF'], [140, 'L'], [4, 'LF'], [88, 'L'], [4, 'LF'], [184, 'L'], [4, 'LF'],
    [216, 'L'], [1, ''], [1199, 'L'],
]

# Rockets (the menu one step up), two in a dive at the slot-3 target at 3224 and two at the
# slot-4 target at 2712 (plan rockets_a); the sky's flash.
ROCKETS_A = PLANE + [
    [4, ''], [8, 'U'], [48, ''], [3, 'F'], [126, ''], [415, 'R'], [177, 'RU'], [1, 'L'],
    [30, 'LD'], [4, 'LDF'], [32, 'LF'], [8, 'LUF'], [24, 'LF'], [4, 'LUF'], [16, 'LF'],
    [4, 'LUF'], [12, 'LF'], [4, 'LUF'], [16, 'LF'], [4, 'LUF'], [8, 'LF'], [8, 'L'],
    [4, 'LU'], [16, 'L'], [4, 'LU'], [1220, 'L'], [32, 'LD'], [4, 'LDF'], [8, 'LD'],
    [1, 'LDF'], [3, 'LUF'], [45, 'LU'], [15, 'L'], [4, 'LU'], [4, 'L'], [8, 'LU'],
    [8, 'L'], [8, 'LU'], [4, 'L'], [4, 'R'], [4, 'RU'], [12, 'R'], [4, 'RU'], [8, 'R'],
    [8, 'RF'], [4, 'RUF'], [16, 'RF'], [4, 'RUF'], [16, 'RF'], [4, 'RUF'], [16, 'RF'],
    [4, 'RUF'], [16, 'RF'], [4, 'RUF'], [16, 'RF'], [4, 'RUF'], [16, 'RF'], [4, 'RUF'],
    [4, 'RF'], [12, 'R'], [4, 'RU'], [16, 'R'], [4, 'RU'], [4, 'R'], [8, 'RU'], [8, 'R'],
    [4, 'RU'], [4, 'R'], [8, 'RU'], [8, 'R'], [4, 'RU'], [4, 'R'], [8, 'RU'], [8, 'R'],
    [4, 'RU'], [4, 'R'], [8, 'RU'], [8, 'R'], [4, 'RU'], [4, 'R'], [8, 'RU'], [8, 'R'],
    [4, 'RU'], [4, 'R'], [4, 'RU'], [4, 'R'], [4, 'RU'], [4, 'R'], [4, 'RU'], [4, 'R'],
    [4, 'RU'], [4, 'R'], [4, 'RU'], [4, 'R'], [4, 'RU'], [4, 'R'], [4, 'RU'], [4, 'R'],
    [4, 'RU'], [176, 'R'], [28, 'L'], [4, 'LU'], [12, 'LF'], [20, 'LUF'], [36, 'LDF'],
    [28, 'LF'], [8, 'LUF'], [4, 'LF'], [8, 'LUF'], [20, 'LF'], [24, 'L'], [4, 'LU'],
    [12, 'L'], [4, 'LU'], [364, 'L'], [36, 'LD'], [4, 'LDF'], [8, 'LD'], [1, 'LDF'],
    [3, 'LUF'], [45, 'LU'], [15, 'L'], [4, 'LU'], [4, 'L'], [8, 'LU'], [8, 'L'], [8, 'LU'],
    [8, 'L'], [8, 'LU'], [8, 'L'], [8, 'LU'], [8, 'L'], [8, 'LU'], [8, 'L'], [8, 'LU'],
    [8, 'L'], [8, 'LU'], [8, 'L'], [8, 'LU'], [8, 'L'], [8, 'LU'], [8, 'L'], [8, 'LU'],
    [8, 'L'], [1, ''], [7, 'LU'], [8, 'L'], [8, 'LU'], [8, 'L'], [8, 'LU'], [8, 'L'],
    [8, 'LU'], [8, 'L'], [8, 'LU'], [8, 'L'], [8, 'LU'], [8, 'L'], [8, 'LU'], [8, 'L'],
    [8, 'LU'], [8, 'L'], [8, 'LU'], [8, 'L'], [8, 'LU'], [8, 'L'], [8, 'LU'], [8, 'L'],
    [4, 'LU'], [4, 'L'], [4, 'LU'], [4, 'L'], [4, 'LU'], [4, 'L'], [4, 'LU'], [4, 'L'],
    [4, 'LU'], [4, 'L'], [4, 'LU'], [580, 'L'],
]

# The torpedo (the menu one step down), dropped at 40 pixels into the sea east of the
# carrier (plan torpedo_a).
TORPEDO_A = PLANE + [
    [4, ''], [8, 'D'], [48, ''], [3, 'F'], [126, ''], [415, 'R'], [157, 'RU'], [39, 'RD'],
    [24, 'R'], [8, 'RU'], [32, 'R'], [16, 'RU'], [136, 'R'], [4, 'RF'], [440, 'R'],
    [1, ''], [799, 'R'],
]

# Low passes over map a's island at 45 pixels until the targets' fire has taken the oil
# below 0x60 and the engine seizes over the island (plan hit_a).
HIT_A = PLANE + [
    [20, ''], [3, 'F'], [126, ''], [415, 'R'], [157, 'RU'], [1, 'L'], [30, 'LD'],
    [24, 'LDF'], [80, 'LF'], [4, 'LUF'], [12, 'LF'], [16, 'LUF'], [40, 'L'], [12, 'LU'],
    [1729, 'L'], [15, 'LU'], [16, 'L'], [12, 'LU'], [12, 'L'], [12, 'LU'], [12, 'L'],
    [12, 'LU'], [12, 'L'], [12, 'LU'], [12, 'L'], [12, 'LU'], [24, 'R'], [4, 'RU'],
    [4, 'R'], [12, 'RF'], [4, 'RUF'], [16, 'RF'], [4, 'RUF'], [16, 'RF'], [4, 'RUF'],
    [16, 'RF'], [4, 'RUF'], [16, 'RF'], [4, 'RUF'], [16, 'RF'], [4, 'RUF'], [16, 'RF'],
    [4, 'RUF'], [16, 'R'], [4, 'RU'], [16, 'R'], [4, 'RU'], [4, 'R'], [4, 'RU'], [4, 'R'],
    [4, 'RU'], [4, 'R'], [4, 'RU'], [101, 'R'], [15, 'RD'], [20, 'R'], [4, 'RU'],
    [48, 'R'], [4, 'RU'], [8, 'R'], [4, 'RU'], [44, 'R'], [4, 'RU'], [453, 'R'],
    [15, 'RU'], [16, 'R'], [12, 'RU'], [12, 'R'], [12, 'RU'], [12, 'R'], [12, 'RU'],
    [12, 'R'], [12, 'RU'], [12, 'R'], [12, 'RU'], [4, 'R'], [8, 'L'], [4, 'LU'], [16, 'L'],
    [4, 'LU'], [16, 'LF'], [4, 'LUF'], [16, 'LF'], [4, 'LUF'], [16, 'LF'], [4, 'LUF'],
    [16, 'LF'], [4, 'LUF'], [16, 'LF'], [4, 'LUF'], [16, 'LF'], [4, 'LUF'], [16, 'LF'],
    [4, 'LU'], [16, 'L'], [4, 'LU'], [20, 'L'], [8, 'LU'], [117, 'L'], [15, 'LD'],
    [20, 'L'], [4, 'LU'], [48, 'L'], [4, 'LU'], [8, 'L'], [4, 'LU'], [8, 'L'], [4, 'LU'],
    [489, 'L'], [15, 'LU'], [16, 'L'], [12, 'LU'], [12, 'L'], [12, 'LU'], [12, 'L'],
    [12, 'LU'], [12, 'L'], [12, 'LU'], [12, 'L'], [12, 'LU'], [4, 'L'], [8, 'R'],
    [4, 'RU'], [16, 'R'], [4, 'RU'], [16, 'RF'], [4, 'RUF'], [16, 'RF'], [4, 'RUF'],
    [16, 'RF'], [4, 'RUF'], [16, 'RF'], [4, 'RUF'], [16, 'RF'], [4, 'RUF'], [16, 'RF'],
    [4, 'RUF'], [16, 'RF'], [4, 'RU'], [16, 'R'], [4, 'RU'], [145, 'R'], [15, 'RD'],
    [20, 'R'], [4, 'RU'], [52, 'R'], [4, 'RU'], [8, 'R'], [4, 'RU'], [8, 'R'], [4, 'RU'],
    [485, 'R'], [15, 'RU'], [16, 'R'], [12, 'RU'], [12, 'R'], [12, 'RU'], [12, 'R'],
    [12, 'RU'], [12, 'R'], [12, 'RU'], [12, 'R'], [12, 'RU'], [4, 'R'], [8, 'L'],
    [4, 'LU'], [16, 'L'], [4, 'LU'], [16, 'LF'], [4, 'LUF'], [16, 'LF'], [4, 'LUF'],
    [16, 'LF'], [4, 'LUF'], [16, 'LF'], [4, 'LUF'], [16, 'LF'], [4, 'LUF'], [16, 'LF'],
    [4, 'LUF'], [16, 'LF'], [4, 'LU'], [16, 'L'], [4, 'LU'], [141, 'L'], [15, 'LD'],
    [20, 'L'], [4, 'LU'], [52, 'L'], [4, 'LU'], [8, 'L'], [4, 'LU'], [8, 'L'], [4, 'LU'],
    [489, 'L'], [15, 'LU'], [16, 'L'], [12, 'LU'], [12, 'L'], [12, 'LU'], [12, 'L'],
    [12, 'LU'], [12, 'L'], [12, 'LU'], [12, 'L'], [12, 'LU'], [4, 'L'], [8, 'R'],
    [4, 'RU'], [16, 'R'], [4, 'RU'], [16, 'RF'], [4, 'RUF'], [16, 'RF'], [4, 'RUF'],
    [16, 'RF'], [4, 'RUF'], [16, 'RF'], [4, 'RUF'], [16, 'RF'], [4, 'RUF'], [16, 'RF'],
    [4, 'RUF'], [16, 'RF'], [4, 'RU'], [16, 'R'], [4, 'RU'], [145, 'R'], [15, 'RD'],
    [20, 'R'], [4, 'RU'], [52, 'R'], [4, 'RU'], [8, 'R'], [4, 'RU'], [8, 'R'], [4, 'RU'],
    [736, 'R'], [305, 'L'],
]

# Straight into the ground of map a's island by the eastern slot-4 target, the wreck at rest
# and the next aircraft (plan crash_a).
CRASH_A = PLANE + [
    [20, ''], [3, 'F'], [126, ''], [415, 'R'], [157, 'RU'], [1, 'L'], [30, 'LD'],
    [8, 'LDF'], [40, 'LF'], [16, 'LUF'], [4, 'LF'], [4, 'LUF'], [56, 'LF'], [4, 'LUF'],
    [4, 'LF'], [4, 'L'], [20, 'LU'], [4, 'L'], [24, 'LD'], [28, 'L'], [8, 'LU'],
    [1316, 'L'], [1, ''], [67, 'LD'], [1533, 'L'],
]

# Map a's four targets bombed, then pass after pass the guns at the soldiers that come out
# and a bomb on every target that still holds soldiers, until the island is neutralised;
# then into the ground, and the next aircraft in the hold (plan island_a).
ISLAND_A = PLANE + [
    [20, ''], [3, 'F'], [126, ''], [415, 'R'], [173, 'RU'], [1, 'L'], [22, 'LD'], [8, 'L'],
    [4, 'LDF'], [4, 'LF'], [4, 'LUF'], [48, 'LF'], [4, 'LUF'], [8, 'LF'], [4, 'LUF'],
    [20, 'LF'], [4, 'LUF'], [16, 'LF'], [4, 'LUF'], [8, 'LF'], [8, 'LUF'], [8, 'LU'],
    [8, 'L'], [12, 'LD'], [12, 'L'], [4, 'LD'], [36, 'L'], [4, 'LU'], [1160, 'L'],
    [4, 'LF'], [140, 'L'], [4, 'LF'], [88, 'L'], [4, 'LF'], [184, 'L'], [4, 'LF'],
    [196, 'L'], [1, 'R'], [11, 'RD'], [20, 'R'], [16, 'RUF'], [4, 'RF'], [4, 'RUF'],
    [52, 'RF'], [8, 'RUF'], [28, 'RF'], [8, 'RUF'], [16, 'RF'], [16, 'R'], [4, 'RU'],
    [8, 'R'], [4, 'RU'], [116, 'R'], [8, 'RDF'], [120, 'RF'], [4, 'RUF'], [12, 'RF'],
    [4, 'RUF'], [44, 'RF'], [16, 'RU'], [12, 'R'], [4, 'RU'], [4, 'R'], [4, 'RU'],
    [4, 'R'], [8, 'RU'], [8, 'R'], [4, 'RU'], [4, 'R'], [8, 'RU'], [8, 'R'], [4, 'RU'],
    [4, 'R'], [8, 'RU'], [8, 'R'], [4, 'RU'], [4, 'R'], [8, 'RU'], [8, 'R'], [4, 'RU'],
    [4, 'R'], [8, 'RU'], [24, 'RDF'], [24, 'RF'], [4, 'RUF'], [20, 'RF'], [4, 'RUF'],
    [4, 'RF'], [4, 'RU'], [4, 'RUF'], [16, 'RU'], [16, 'R'], [4, 'RU'], [4, 'R'],
    [4, 'RU'], [4, 'R'], [4, 'RU'], [4, 'R'], [8, 'RU'], [8, 'R'], [4, 'RU'], [4, 'R'],
    [8, 'RU'], [8, 'R'], [4, 'RU'], [4, 'R'], [8, 'RU'], [8, 'R'], [4, 'RU'], [4, 'R'],
    [8, 'RU'], [8, 'R'], [4, 'RU'], [4, 'R'], [8, 'RU'], [8, 'R'], [4, 'RU'], [4, 'R'],
    [8, 'RU'], [4, 'R'], [4, 'L'], [4, 'LU'], [16, 'L'], [4, 'LU'], [4, 'L'], [12, 'LF'],
    [4, 'LUF'], [16, 'LF'], [4, 'LUF'], [16, 'LF'], [4, 'LUF'], [16, 'LF'], [4, 'LUF'],
    [16, 'LF'], [4, 'LUF'], [40, 'LF'], [16, 'L'], [20, 'LU'], [12, 'L'], [4, 'LU'],
    [92, 'L'], [4, 'LF'], [424, 'L'], [4, 'LF'], [188, 'L'], [28, 'R'], [4, 'RU'],
    [12, 'RF'], [4, 'RUF'], [16, 'RF'], [20, 'RUF'], [36, 'RDF'], [28, 'RF'], [8, 'RUF'],
    [4, 'RF'], [8, 'RUF'], [56, 'R'], [4, 'RU'], [80, 'R'], [12, 'RDF'], [16, 'RF'],
    [32, 'RU'], [4, 'R'], [4, 'RD'], [2, 'RDF'], [2, 'RD'], [24, 'RDF'], [12, 'RF'],
    [8, 'RUF'], [16, 'RU'], [20, 'RDF'], [36, 'RF'], [4, 'RUF'], [4, 'RF'], [28, 'RU'],
    [24, 'R'], [12, 'RU'], [12, 'R'], [12, 'RU'], [12, 'R'], [12, 'RU'], [12, 'R'],
    [8, 'RU'], [12, 'R'], [8, 'RU'], [8, 'R'], [4, 'RU'], [4, 'R'], [8, 'RU'], [8, 'R'],
    [8, 'RU'], [240, 'R'], [28, 'L'], [4, 'LU'], [12, 'LF'], [20, 'LUF'], [36, 'LDF'],
    [28, 'LF'], [8, 'LUF'], [4, 'LF'], [8, 'LUF'], [20, 'LF'], [24, 'L'], [4, 'LU'],
    [12, 'L'], [4, 'LU'], [524, 'L'], [4, 'LF'], [192, 'L'], [28, 'R'], [4, 'RU'],
    [8, 'RF'], [4, 'RUF'], [24, 'RF'], [8, 'RUF'], [32, 'RF'], [20, 'RUF'], [4, 'RF'],
    [32, 'RDF'], [4, 'RF'], [24, 'R'], [16, 'RU'], [88, 'R'], [2, 'RDF'], [2, 'R'],
    [12, 'RDF'], [16, 'RF'], [16, 'RU'], [4, 'RF'], [8, 'RDF'], [112, 'RF'], [24, 'RU'],
    [16, 'R'], [12, 'RU'], [12, 'R'], [12, 'RU'], [12, 'R'], [12, 'RU'], [12, 'R'],
    [12, 'RU'], [12, 'R'], [12, 'RU'], [12, 'R'], [12, 'RU'], [12, 'R'], [4, 'RU'],
    [8, 'R'], [8, 'RU'], [8, 'R'], [4, 'RU'], [4, 'R'], [8, 'RU'], [8, 'R'], [8, 'RU'],
    [224, 'R'], [28, 'L'], [4, 'LU'], [16, 'LUF'], [4, 'LF'], [32, 'LDF'], [28, 'LF'],
    [16, 'LUF'], [40, 'LF'], [12, 'L'], [8, 'LU'], [128, 'L'], [4, 'LF'], [616, 'L'],
    [12, 'R'], [4, 'RU'], [16, 'R'], [4, 'RUF'], [16, 'RF'], [4, 'RUF'], [16, 'RF'],
    [20, 'RUF'], [36, 'RDF'], [28, 'RF'], [8, 'RUF'], [4, 'RF'], [8, 'RU'], [226, 'R'],
    [6, 'RDF'], [44, 'RF'], [28, 'RU'], [16, 'R'], [4, 'RU'], [4, 'R'], [8, 'RU'],
    [8, 'R'], [8, 'RU'], [8, 'R'], [8, 'RU'], [8, 'R'], [4, 'RU'], [4, 'R'], [4, 'RU'],
    [4, 'R'], [4, 'RU'], [4, 'R'], [4, 'RU'], [4, 'R'], [4, 'RU'], [4, 'R'], [4, 'RU'],
    [4, 'R'], [4, 'RU'], [332, 'R'], [28, 'L'], [4, 'LU'], [16, 'LUF'], [4, 'LF'],
    [32, 'LDF'], [28, 'LF'], [16, 'LUF'], [40, 'LF'], [12, 'L'], [8, 'LU'], [552, 'L'],
    [4, 'LF'], [192, 'L'], [12, 'R'], [4, 'RU'], [16, 'R'], [4, 'RUF'], [16, 'RF'],
    [4, 'RUF'], [16, 'RF'], [20, 'RUF'], [36, 'RDF'], [28, 'RF'], [8, 'RUF'], [4, 'RF'],
    [8, 'RU'], [84, 'R'], [728, 'L'], [85, ''], [3, 'F'], [130, ''], [415, 'R'],
    [173, 'RU'], [1, 'L'], [22, 'LD'], [4, 'L'], [4, 'LD'], [4, 'LDF'], [36, 'LF'],
    [8, 'LUF'], [24, 'LF'], [4, 'LUF'], [16, 'LF'], [4, 'LUF'], [12, 'LF'], [4, 'LUF'],
    [16, 'LF'], [8, 'LUF'], [12, 'LU'], [4, 'L'], [28, 'LD'], [56, 'L'], [4, 'LU'],
    [1768, 'L'], [1, 'R'], [11, 'RD'], [20, 'R'], [16, 'RUF'], [4, 'RF'], [4, 'RUF'],
    [52, 'RF'], [8, 'RUF'], [28, 'RF'], [8, 'RUF'], [16, 'RF'], [16, 'R'], [4, 'RU'],
    [8, 'R'], [4, 'RU'], [736, 'R'], [24, 'L'], [4, 'LU'], [4, 'L'], [4, 'LF'],
    [16, 'LUF'], [8, 'LF'], [24, 'LDF'], [32, 'LF'], [16, 'LUF'], [36, 'LF'], [16, 'L'],
    [8, 'LU'], [744, 'L'], [20, 'R'], [12, 'RU'], [8, 'RUF'], [4, 'RF'], [32, 'RDF'],
    [28, 'RF'], [16, 'RUF'], [48, 'RF'], [4, 'R'], [8, 'RU'], [28, 'R'], [4, 'RU'],
    [488, 'R'], [4, 'RF'], [232, 'R'], [24, 'L'], [4, 'LU'], [4, 'L'], [4, 'LF'],
    [16, 'LUF'], [8, 'LF'], [24, 'LDF'], [32, 'LF'], [16, 'LUF'], [36, 'LF'], [16, 'L'],
    [8, 'LU'], [288, 'L'], [8, 'LDF'], [24, 'LF'], [18, 'LU'], [66, 'LD'], [1771, 'L'],
]

# Map b: the western island's six targets bombed, then the guns at the soldiers (plan bomb_b).
BOMB_B = PLANE + [
    [20, ''], [3, 'F'], [126, ''], [415, 'R'], [173, 'RU'], [1, 'L'], [22, 'LD'], [8, 'L'],
    [4, 'LDF'], [4, 'LF'], [4, 'LUF'], [48, 'LF'], [4, 'LUF'], [8, 'LF'], [4, 'LUF'],
    [20, 'LF'], [4, 'LUF'], [16, 'LF'], [4, 'LUF'], [8, 'LF'], [8, 'LUF'], [8, 'LU'],
    [8, 'L'], [12, 'LD'], [12, 'L'], [4, 'LD'], [36, 'L'], [4, 'LU'], [1012, 'L'],
    [4, 'LF'], [144, 'L'], [4, 'LF'], [64, 'L'], [4, 'LF'], [52, 'L'], [4, 'LF'],
    [24, 'L'], [4, 'LF'], [164, 'L'], [4, 'LF'], [152, 'L'], [1, 'R'], [11, 'RD'],
    [20, 'R'], [16, 'RUF'], [4, 'RF'], [4, 'RUF'], [52, 'RF'], [8, 'RUF'], [28, 'RF'],
    [8, 'RUF'], [16, 'RF'], [16, 'R'], [4, 'RU'], [8, 'R'], [4, 'RU'], [60, 'R'],
    [8, 'RDF'], [120, 'RF'], [4, 'RUF'], [12, 'RF'], [4, 'RUF'], [40, 'RF'], [12, 'RU'],
    [12, 'RDF'], [20, 'RF'], [16, 'RU'], [12, 'R'], [4, 'RU'], [4, 'R'], [4, 'RU'],
    [4, 'R'], [8, 'RU'], [8, 'R'], [4, 'RU'], [4, 'R'], [8, 'RU'], [8, 'R'], [4, 'RU'],
    [4, 'R'], [8, 'RU'], [8, 'R'], [4, 'RU'], [4, 'R'], [8, 'RU'], [8, 'R'], [4, 'RU'],
    [4, 'R'], [8, 'RU'], [8, 'R'], [4, 'RU'], [4, 'R'], [8, 'RU'], [8, 'R'], [4, 'RU'],
    [4, 'R'], [8, 'RU'], [8, 'R'], [4, 'RU'], [4, 'R'], [8, 'RU'], [8, 'R'], [4, 'RU'],
    [4, 'R'], [8, 'RU'], [8, 'R'], [4, 'RU'], [4, 'R'], [8, 'RU'], [8, 'R'], [4, 'RU'],
    [4, 'R'], [4, 'RU'], [4, 'R'], [4, 'RU'], [4, 'R'], [4, 'RU'], [4, 'R'], [4, 'RU'],
    [4, 'R'], [4, 'RU'], [4, 'R'], [4, 'RU'], [4, 'R'], [4, 'RU'], [132, 'R'], [1, ''],
    [399, 'R'],
]

# Map c: the western island's six targets bombed, then the guns at the soldiers (plan bomb_c).
BOMB_C = PLANE + [
    [20, ''], [3, 'F'], [126, ''], [415, 'R'], [173, 'RU'], [1, 'L'], [22, 'LD'], [8, 'L'],
    [4, 'LDF'], [4, 'LF'], [4, 'LUF'], [48, 'LF'], [4, 'LUF'], [8, 'LF'], [4, 'LUF'],
    [20, 'LF'], [4, 'LUF'], [16, 'LF'], [4, 'LUF'], [8, 'LF'], [8, 'LUF'], [8, 'LU'],
    [8, 'L'], [12, 'LD'], [12, 'L'], [4, 'LD'], [36, 'L'], [4, 'LU'], [948, 'L'],
    [4, 'LF'], [96, 'L'], [4, 'LF'], [24, 'L'], [4, 'LF'], [32, 'L'], [4, 'LF'], [40, 'L'],
    [4, 'LF'], [120, 'L'], [4, 'LF'], [172, 'L'], [1, 'R'], [11, 'RD'], [20, 'R'],
    [16, 'RUF'], [4, 'RF'], [4, 'RUF'], [52, 'RF'], [8, 'RUF'], [28, 'RF'], [8, 'RUF'],
    [16, 'RF'], [16, 'R'], [4, 'RU'], [8, 'R'], [4, 'RU'], [68, 'R'], [8, 'RDF'],
    [116, 'RF'], [28, 'RU'], [16, 'R'], [4, 'RU'], [4, 'R'], [4, 'RU'], [4, 'R'],
    [4, 'RU'], [4, 'R'], [8, 'RU'], [8, 'R'], [4, 'RU'], [4, 'R'], [8, 'RU'], [8, 'R'],
    [4, 'RU'], [4, 'R'], [8, 'RU'], [8, 'R'], [4, 'RU'], [4, 'R'], [8, 'RU'], [8, 'R'],
    [4, 'RU'], [4, 'R'], [8, 'RU'], [8, 'R'], [4, 'RU'], [4, 'R'], [8, 'RU'], [8, 'R'],
    [4, 'RU'], [4, 'R'], [8, 'RU'], [8, 'R'], [4, 'RU'], [4, 'R'], [8, 'RU'], [8, 'R'],
    [4, 'RU'], [4, 'R'], [8, 'RU'], [8, 'R'], [4, 'RU'], [4, 'R'], [4, 'RU'], [4, 'R'],
    [4, 'RU'], [4, 'R'], [4, 'RU'], [96, 'R'], [1, ''], [399, 'R'],
]

# Map c: rockets in a dive at each of the western island's two pillboxes, slot 0x0F (plan
# rockets_c).
ROCKETS_C = PLANE + [
    [4, ''], [8, 'U'], [48, ''], [3, 'F'], [126, ''], [415, 'R'], [177, 'RU'], [1, 'L'],
    [30, 'LD'], [4, 'LDF'], [32, 'LF'], [8, 'LUF'], [24, 'LF'], [4, 'LUF'], [16, 'LF'],
    [4, 'LUF'], [12, 'LF'], [4, 'LUF'], [16, 'LF'], [4, 'LUF'], [8, 'LF'], [8, 'L'],
    [4, 'LU'], [16, 'L'], [4, 'LU'], [824, 'L'], [32, 'LD'], [4, 'LDF'], [8, 'LD'],
    [1, 'LDF'], [3, 'LUF'], [45, 'LU'], [15, 'L'], [4, 'LU'], [4, 'L'], [8, 'LU'],
    [8, 'L'], [8, 'LU'], [8, 'L'], [8, 'LU'], [8, 'L'], [8, 'LU'], [8, 'L'], [1, 'R'],
    [3, 'RU'], [12, 'R'], [4, 'RU'], [12, 'R'], [4, 'RF'], [4, 'RUF'], [16, 'RF'],
    [4, 'RUF'], [16, 'RF'], [4, 'RUF'], [16, 'RF'], [4, 'RUF'], [16, 'RF'], [4, 'RUF'],
    [16, 'RF'], [4, 'RUF'], [16, 'RF'], [4, 'RUF'], [8, 'RF'], [8, 'R'], [4, 'RU'],
    [16, 'R'], [4, 'RU'], [8, 'R'], [8, 'RU'], [8, 'R'], [8, 'RU'], [8, 'R'], [8, 'RU'],
    [8, 'R'], [8, 'RU'], [8, 'R'], [8, 'RU'], [8, 'R'], [8, 'RU'], [8, 'R'], [4, 'RU'],
    [4, 'R'], [4, 'RU'], [4, 'R'], [4, 'RU'], [4, 'R'], [4, 'RU'], [4, 'R'], [4, 'RU'],
    [4, 'R'], [4, 'RU'], [4, 'R'], [4, 'RU'], [4, 'R'], [4, 'RU'], [196, 'R'], [28, 'L'],
    [4, 'LU'], [16, 'LUF'], [4, 'LF'], [32, 'LDF'], [28, 'LF'], [16, 'LUF'], [40, 'LF'],
    [12, 'L'], [8, 'LU'], [208, 'L'], [32, 'LD'], [4, 'LDF'], [8, 'LD'], [1, 'LDF'],
    [3, 'LUF'], [45, 'LU'], [15, 'L'], [4, 'LU'], [4, 'L'], [8, 'LU'], [8, 'L'], [8, 'LU'],
    [8, 'L'], [8, 'LU'], [8, 'L'], [8, 'LU'], [1, ''], [7, 'L'], [8, 'LU'], [8, 'L'],
    [8, 'LU'], [8, 'L'], [8, 'LU'], [8, 'L'], [8, 'LU'], [8, 'L'], [8, 'LU'], [8, 'L'],
    [8, 'LU'], [8, 'L'], [8, 'LU'], [8, 'L'], [8, 'LU'], [8, 'L'], [8, 'LU'], [8, 'L'],
    [8, 'LU'], [8, 'L'], [8, 'LU'], [8, 'L'], [8, 'LU'], [8, 'L'], [8, 'LU'], [8, 'L'],
    [8, 'LU'], [8, 'L'], [8, 'LU'], [8, 'L'], [8, 'LU'], [8, 'L'], [8, 'LU'], [8, 'L'],
    [4, 'LU'], [4, 'L'], [4, 'LU'], [4, 'L'], [4, 'LU'], [4, 'L'], [4, 'LU'], [4, 'L'],
    [4, 'LU'], [4, 'L'], [4, 'LU'], [476, 'L'],
]

# Map c with balloons_on set after the mission's reset, as the promotion after a rank's last
# mission leaves it (0x0156CC) for the flight back to the carrier: out over the balloons,
# back and out again (the autopilot's plan balloons_c).
BALLOONS_C = PLANE + [
    [20, ''], [3, 'F'], [126, ''], [415, 'R'], [157, 'RU'], [23, 'RD'], [40, 'R'],
    [4, 'RU'], [4, 'R'], [28, 'L'], [4, 'LU'], [4, 'LUF'], [32, 'LF'], [4, 'LUF'],
    [8, 'LF'], [4, 'LUF'], [24, 'LF'], [20, 'LUF'], [4, 'LF'], [32, 'LDF'], [4, 'LF'],
    [24, 'L'], [16, 'LU'], [404, 'L'], [1, 'R'], [11, 'RD'], [20, 'R'], [20, 'RUF'],
    [56, 'RF'], [8, 'RUF'], [28, 'RF'], [8, 'RUF'], [16, 'RF'], [16, 'R'], [4, 'RU'],
    [8, 'R'], [16, 'RU'], [320, 'R'], [1, ''], [239, 'R'],
]

# The VBlank at which the key runs press their key: the first bomb of bomb_a is in the air.
BOMB_KEYS_AT = 2377


def length(raw):
    return sum(entry[0] for entry in raw)


def with_keys(raw, at, keys):
    """The schedule with raw key codes delivered at VBlank `at` (from 0): the segment that
    holds it is split and a one-VBlank segment carries the keys, with the same stick."""
    out, v = [], 0
    for entry in raw:
        n = entry[0]
        if v <= at < v + n:
            before, after = at - v, v + n - at - 1
            if before:
                out.append([before] + entry[1:])
            out.append([1, entry[1], keys])
            if after:
                out.append([after] + entry[1:])
        else:
            out.append(list(entry))
        v += n
    return out


# Escape (0x45), Control-F (0x23) and Control-R (0x13), as the key runs of tests/runs/ press
# them (re/notes/keys.md), during the first bombing run of map a: the pause and its end 40
# VBlanks later, the flip, and the restart, each while a bomb is in the air.
ESCAPE, CONTROL_F, CONTROL_R = 69, [35, 'ctrl'], [19, 'ctrl']

RUNS = {name: (raw, length(raw) + 20) for name, raw in [
    ('guns_sea', GUNS_SEA), ('guns_a', GUNS_A), ('bomb_a', BOMB_A), ('high_a', HIGH_A),
    ('rockets_a', ROCKETS_A), ('torpedo_a', TORPEDO_A), ('hit_a', HIT_A), ('crash_a', CRASH_A),
    ('island_a', ISLAND_A), ('bomb_b', BOMB_B), ('bomb_c', BOMB_C), ('rockets_c', ROCKETS_C),
    ('balloons_c', BALLOONS_C),
]}
RUNS['bomb_pause'] = (with_keys(with_keys(BOMB_A, BOMB_KEYS_AT, [ESCAPE]), BOMB_KEYS_AT + 40,
                                [ESCAPE]), length(BOMB_A) + 20)
RUNS['bomb_flip'] = (with_keys(BOMB_A, BOMB_KEYS_AT, [CONTROL_F]), length(BOMB_A) + 20)
RUNS['bomb_restart'] = (with_keys(BOMB_A, BOMB_KEYS_AT, [CONTROL_R]), BOMB_KEYS_AT + 400)
# The cheat sequence of tests/runs/flight-cheat.json in the climb, then its `m` (0x37), which
# makes the weapons unlimited (0x01D08A, weapon_count 0xFF: the counter's drums turn to 0x64,
# 0x01F062), and `m` again during the bombing run, which gives the weapon type's count back.
CHEAT = [0x33, 0x18, 0x28, 0x17, 0x36]
RUNS['bomb_cheat'] = (with_keys(with_keys(with_keys(BOMB_A, 800, CHEAT), 900, [0x37]),
                                BOMB_KEYS_AT + 200, [0x37]), length(BOMB_A) + 20)

# The mission number each script is flown on, poked at the rank selection's end (0x01009E)
# as {address: (size, value)} on both sides, as tests/test_mission.py's setups do; a third
# element names another point, here the one after the mission's reset of its tables
# (0x0100D6, main's jsr to player_restart_state), where balloons_on stays as poked.
RANK_END, MISSION_RESET = 0x01009E, 0x0100D6
BALLOONS_ON = 0x02535D
POKES = {'bomb_b': {MISSION_NUMBER: (2, 2)}, 'bomb_c': {MISSION_NUMBER: (2, 3)},
         'rockets_c': {MISSION_NUMBER: (2, 3)},
         'balloons_c': {MISSION_NUMBER: (2, 3), BALLOONS_ON: (1, 0xFF, MISSION_RESET)}}


def poke_points(pokes):
    """{point: [(address, size, value)]} of a script's pokes."""
    out = {}
    for address, entry in (pokes or {}).items():
        at = entry[2] if len(entry) > 2 else RANK_END
        out.setdefault(at, []).append((address, entry[0], entry[1]))
    return out


def install_pokes(machine, pokes):
    """Make a script's pokes in a headless original at their points."""
    for at, items in poke_points(pokes).items():
        machine.stop_at(at, lambda items=items: [machine.o.write(a, v.to_bytes(s, 'big'))
                                                 for a, s, v in items])

SCRIPTS = list(RUNS)

PLAYER = 0x025078
WATCH = [
    ('deck', PLAYER + 0x0C, 2), ('y', PLAYER + 0x00, 2), ('x', PLAYER + 0x02, 2),
    ('oil', PLAYER + 0x12, 2), ('wtype', 0x0253A4, 2), ('wcount', 0x02536D, 1),
    ('score', 0x02534E, 2), ('flash', 0x025416, 2), ('left', 0x025383, 1),
    ('soldiers', 0x025450, 2), ('pills', 0x025452, 2),
]


def script(name, **more):
    """The run description of an M5 script, or of an M4 one through tools/m4_scripts.py."""
    if name in RUNS:
        raw, vblanks = RUNS[name]
        description = {'raw': raw + [[1, '']], 'stop': {'vblanks': vblanks}}
        description.update(more)
        return description
    return m4_scripts.script(name, **more)


def signed(v, bits):
    return v - (1 << bits) if v >> (bits - 1) else v


def objects(o):
    """The object records in use: (record, kind, type, x, y)."""
    out = []
    for i in range(16):
        a = 0x024CAE + 0x2A * i if i < 15 else 0x025594
        kind = o.read(a + 0x20, 1)[0]
        if kind:
            out.append((i, kind, signed(o.r16(a + 0x22), 16), signed(o.r16(a), 16),
                        signed(o.r16(a + 4), 16)))
    return out


def trace(name, every=1, start=0, out=sys.stdout):
    """Run a script and print the player, the weapons and the targets after every tick."""
    machine = headless.Headless(script(name))
    install_pokes(machine, POKES.get(name))
    started = time.time()
    print('tick  in   ' + ' '.join('%6s' % w[0] for w in WATCH) + '  objects', file=out)
    limit = script(name)['stop'].get('vblanks', 1 << 60)
    while True:
        reason = machine.run(until='tick')
        if reason != 'tick' or machine.vblanks >= limit:
            break
        t = machine.ticks
        if t >= start and (t - start) % every == 0:
            values = [signed(machine.o.r16(a) if n == 2 else machine.o.read(a, 1)[0], 8 * n)
                      for _, a, n in WATCH]
            print('%4d  %02x  ' % (t, machine.o.r16(headless.TICK_INPUT) & 0xFF) +
                  ' '.join('%6d' % v for v in values) + '  ' + str(objects(machine.o)), file=out)
    print('%d ticks, %d passes, %d VBlanks, %.0f s, stopped: %s'
          % (machine.ticks, machine.passes, machine.vblanks, time.time() - started, reason),
          file=out)
    return machine


def main():
    parser = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    parser.add_argument('command', nargs='?', choices=['trace'])
    parser.add_argument('name', nargs='?')
    parser.add_argument('--list', action='store_true')
    parser.add_argument('--every', type=int, default=1)
    parser.add_argument('--from', dest='start', type=int, default=0)
    args = parser.parse_args()
    if args.list or not args.command:
        for name in SCRIPTS:
            raw, vblanks = RUNS[name]
            print('%-14s %6d VBlanks  %s' % (name, vblanks, json.dumps(POKES.get(name, {}))))
        return 0
    trace(args.name, every=args.every, start=args.start)
    return 0


if __name__ == '__main__':
    sys.exit(main())
