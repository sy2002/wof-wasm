# M5: the weapons and the ground targets

Milestone M5 of `SPEC.md` section 9: the guns, the bombs, the rockets, the torpedo, the
islands with their targets and soldiers, and the effects, on the first three maps. Part 1,
this note's subject so far, is everything the M5 scripts execute in a pass
(`frame_update`'s tree, phase F) and in a VBlank (phase V). Part 2 is what they execute in
the tick (phase T): the weapons' launch and flight, their hits, the guns' bullets, the
targets' timers, the crash on land. Addresses use the standard load layout.

Every statement is either **observed**, with the tool or test that shows it, or **read**,
which means it comes from the listing alone.

```text
src/targets.c            the targets, the soldiers, their fire and the ticker's messages
src/pools.c              the Smoke, Splashes and Balloons pools and their claims
src/objects.c            the object records as the pass draws them
src/world.c              the pass: the island's flag and the burnt barracks wired in, the muzzle flash
src/dash.c               the weapon counter's drums
tools/m5_autopilot.py    the autopilot that flew the scripts: attacks by plan
tools/m5_scripts.py      the M5 scripts, and the weapons tick by tick while one runs
tools/m5_observe.py      the left-overs of SPEC 10 answered by observation
tools/reach_observe.py   the reach map, now with --m5, --m5-only, --load and a joined --cold
tests/test_weapons.py    the open loop over every M5 script, attributed; the completeness list
tests/test_oracle_m5.py  the pure routines of part 1 against the original
```

## What decides what is ported: the reach map

The M5 scripts are the sixteen of `tools/m5_scripts.py` ("The scripts" below). The reach
map runs them beside every run of M4 and joins the two for the cold regions (observed):

```text
.venv/bin/python tools/reach_observe.py --m5 --blocks --setups --jobs 12 --json REACH.json
.venv/bin/python tools/reach_observe.py --m5-only --load REACH.json --markdown TABLE.md
.venv/bin/python tools/reach_observe.py --cold REACH.json
```

`--m5` runs the M4 scripts, the night mission, the key runs and the fifteen setups, and
then the M5 scripts, each with the pokes it needs (the mission number for maps b and c);
`--jobs` runs them in processes of their own, and `--load` renders saved runs. `--cold`
takes several saved runs and joins them, so the cold regions are those that no script of
either milestone executed.

### The cut between the parts (observed)

What the M5 scripts executed that no M4 script did, by phase, over the joined runs:

- **Phase F (part 1):** `record_extras` (an island's flag, `0x013B52`, and a burnt
  barracks' smoke, `0x014E18`); `targets_3_draw` and `targets_f_draw`; `soldiers_draw`
  whole; `0x014AE4` and `0x014B54` (a target found); `target_frame`, `target_range_frame`
  and `target_fire`; `0x014FEE` with `0x015034` and `0x011E82` (a dug-out refilled from a
  barracks, which the pass does); `smoke_draw`, `splashes_draw` (the dust on land),
  `smoke_at_player`; the ticker's messages `0x015078`, `0x015624`, `0x015694` and
  `0x015AE8`; `0x010702` for every weapon type and in the eighth-scale view; the guns'
  muzzle flash in `draw_player`; the weapon counter's drums and the unlimited weapons in
  `draw_dashboard`; the flash of `flip_buffers`; blocks of `window_strip` and
  `window_shape` that M4 ported from reading.
- **Phase V (part 1):** only `vblank_server`'s ticker, which M4 ported from reading: the
  island's message scrolls in `island_a` (705 VBlanks of scrolling, 60 glyphs).
- **Phase T (part 2):** the drop at `0x01B5E2`, `object_spawn`'s second entry with
  `0x0107F2` and `0x01107C`, `object_step` with `0x01099A`, `0x011126`, `0x01115C` and
  `0x0111A6` (a rocket's homing), the hits `0x0146C6` and `0x0146DC` with `0x014B40`,
  `target_timers`, `0x011E82` from the tick, `gun_splashes` with `0x011A46`, `0x011A8C`
  and `0x011AE2`, `splash_spawn` on land, `smoke_claim` below the ground, the crash on
  land with the burning wreck, and three regions M4 marked M6 that the M5 scripts reach on
  map a and that are therefore M5's: the oil leak (`0x0113A2`) and the engine's smoke
  (`0x011C24`), which any hit of a target's gun starts, and the compare at `0x0116BE` to
  `0x0116C9`, which the empty airfield records of map a meet whenever the aircraft flies
  west of x 480.
- **Phase M:** `main`'s next mission (`0x010132` on, M7's), which `island_a` reaches, and
  blocks of the pause and the flip that the key runs reach in M4's ported code.

The enemy aircraft stay away: every script keeps the enemy's countdown (`0x01BC02`) from
running out by holding the button inside its turns, where the button neither fires nor
drops (observed: no aircraft record's state word is ever set, and the countdown's minimum
over the scripts is 393, `m5_observe`'s replay of every script).

## The scripts

Each is a raw schedule for the headless original, flown by a plan of
`tools/m5_autopilot.py` and kept in `tools/m5_scripts.py`; `trace NAME` prints the player,
the weapons, the score and the object records tick by tick. A plan names the weapon (the
menu one step up for the rockets, one down for the torpedo, as the manual's page 4 has it),
the legs (a direction, a height and where the leg ends) and on each leg the actions: a bomb
where `fall()` predicts it comes down on a target (the prediction is `object_step`'s own
arithmetic, 14 pixels short, measured over `bomb_a`'s drops), a rocket from a dive, the
guns in a shallow descent (the bullets reach the ground only while the aircraft sinks below
y `0xA0`, `0x0119C4`), the guns at the running soldiers, a bomb on every target that still
holds soldiers. Maps b and c are the second and third missions of the first rank and are
reached as the M4 setups reach them, with `mission_number` poked at the rank selection's
end (`POKES`), because winning the missions before is M7's.

| Script | What it flies | Ticks |
|---|---|---|
| `guns_sea` | three shallow dives with the guns over the sea east of the carrier | 470 |
| `guns_a` | the same over map a's island, flying left; the dug-outs' fire hits the aircraft | 766 |
| `bomb_a` | a bomb on each of map a's four targets from 150 pixels: the slot-3 targets at 3224 and 1736, the slot-4 targets at 2712 and 2392 (score 700) | 911 |
| `high_a` | the same from 420 pixels, in the eighth-scale view | 1,099 |
| `rockets_a` | the rockets, two in a dive at the dug-out at 3224 (hit) and two at the barracks at 2712; the sky's flash | 1,166 |
| `torpedo_a` | the torpedo, dropped at 40 pixels into the sea east of the carrier, where it runs | 590 |
| `hit_a` | low passes over map a's island until the targets' fire has taken the oil below `0x60`; the engine seizes and the aircraft comes down on the island | 2,184 |
| `crash_a` | straight down into the island next to the eastern barracks: the crash destroys it (score 150), the wreck burns at rest, the next aircraft | 998 |
| `island_a` | map a's four targets bombed, then pass after pass the guns at the soldiers that come out and a bomb on every target that still holds soldiers, until all twenty are dead: the island neutralised, its bonus and message, the mission won (`0x015694`); then into the ground, and in the hold the next mission begins (M7's) | 4,779 |
| `bomb_b` | map b: the western island's six targets bombed, the guns at the soldiers | 1,021 |
| `bomb_c` | map c: the same on its western island | 934 |
| `rockets_c` | map c: a rocket dive at each of the western island's two pillboxes (slot `0x0F`), both destroyed, their smoke | 1,003 |
| `bomb_pause` | `bomb_a` with Escape while the first bomb falls and again 40 VBlanks later | 902 |
| `bomb_flip` | `bomb_a` with Control-F while the first bomb falls | 911 |
| `bomb_restart` | `bomb_a` with Control-R while the first bomb falls, and the rank selection after it | 611 |
| `bomb_cheat` | `bomb_a` with the cheat sequence of `tests/runs/flight-cheat.json` in the climb, its `m` (unlimited weapons, the counter's drums turning to `0x64`) and `m` again during the run | 911 |

Every script replays as flown (observed, `m5_observe`'s replay and the verification runs
behind this table: score, weapons, lives, the flash, the oil and the islands left at the
end are those the autopilot saw).

One thing the scripts do not reach, after a real attempt, is in "The left-overs" below:
the Balloons pool, which only the last island of map c can fill.

## The left-overs of section 10 (point 3, point 6 and point 2)

### The Ricochet and Balloons pools (observed and read)

`tools/m5_observe.py pools` puts a write hook on both allocations and on `balloons_on`
(`0x02535D`) over every M5 script: **neither pool is written by anything in any script**,
and `balloons_on` only by `mission_reset_tables` (`0x0135A8`), which clears it.

- **Ricochet**'s only writer is `0x011A14`, which takes a world x in D0, finds the first
  record whose count is 0 and gives it the x, the low bits of the map record there and a
  count of 4. **Nothing calls it**: its far-call slot at `0x023054` (`jmp 0x011A14`,
  `-32682(a4)`) is named by no instruction of the executable, and no code refers to the
  routine otherwise (read, a search of the listing for the slot, the address and the
  displacement); the reach map never enters it (observed). The pool is dead: nothing fills
  it on any map, and it owes no milestone. The port keeps the allocation for the layout.
- **Balloons** are filled by `balloons_draw` (`0x01557C`) in the pass, while `balloons_on`
  is set and the view is at full scale: every record not in use is released over the
  carrier at `player_start_x - 0x74`, height `0x38`, with a colour and a drift from three
  draws of `rand_beam`; `balloons_step` (`0x011C5E`) moves them in the tick. **Only
  `0x0156CC` sets `balloons_on`**: in `0x015694`, the mission won, when the mission number
  passes `missions_per_rank` (`0x025548`: 3, 3, 2, 2, 1, 1, 3 by rank), which is the
  promotion after a rank's last mission. Of maps a to c only map c meets it, as the third
  mission of the first rank; there it needs all three islands neutralised: four pillboxes,
  which only a rocket destroys, and 70 soldiers, which a bomb or a rocket brings out of
  their dug-outs and barracks and the guns kill. (read, and the reach map: `0x0156B2` to
  `0x0156E7` is cold.) Maps b and a promote nobody: `island_a` wins map a and takes
  `0x0156E8`, the next mission's message.

### The sky's flash (observed)

`tools/m5_observe.py flash` watches `flash_count` (`0x025416`) and `flash_colour`
(`0x025418`) with their writers over `rockets_a`, `crash_a`, `hit_a`, `rockets_c` and
`island_a`:

- **What sets it on maps a to c** is `0x0146DC`, in the tick, for a hit of an object of
  type 0 that is not in the water: count 5 and colour `0xFFF`, and `0xF00` when the hit is a
  target (a dug-out with soldiers, a barracks, a pillbox). A rocket is type 0; so is the
  record `0x0146C6` makes up for a crash on land (`0x027700`, +`0x22` 0), which is why a
  crash on an island flashes too. The crash on a ship (`flash_set`, `0x01CAB4`) and a hit on
  a ship (`0x0149A6`, `0x0149DC`) are the others, M6's. A bomb or the torpedo never flashes.
- **What the rows show:** `flip_buffers` takes the count at the pass's end, counts it down,
  and on an odd count pokes COLOR01 of the list it shows with `flash_colour`. The tick sets
  5, so the passes show the colour, the sky, the colour, the sky, the colour: in
  `rockets_a` passes 1,178 to 1,182 (red, a hit on the dug-out) and 1,822 to 1,826 (white).
  The poke reaches the rows above the split line, and below it where the lower colour table
  gives COLOR01 no colour of its own. The comparison's model of the rows
  (`tests/m4compare.py`, `expected_rows`) now has the flash: it takes the count the step
  before the pass left.
- **The port's path**, ported from reading in M4, is compared on those scripts: every pass
  of them agrees in its rows (`tests/test_weapons.py`).

### The couplings of a pass (observed)

`tools/m5_observe.py couplings` hooks the writes of `player_score`, `island_score`, the
player's `+0x12` and `0x024F24` over `island_a`, `guns_a` and `hit_a`:

- **A soldier's death scores in the pass**: `soldiers_draw` writes `player_score` 21 times
  in `island_a` (twenty soldiers of 25 points and the island's bonus) and `island_score` 20
  times, all in phase F.
- **The player's `+0x12` (the oil) is written in a pass** by `target_fire`: 2 times in
  `guns_a`, 15 in `hit_a`, 11 in `island_a`. It is the fire of a dug-out or a pillbox
  hitting the aircraft: at the end of the hit count (`+0x10`) the oil falls by one.
- **`frame_update`'s own call of the restart stays unreachable**: nothing writes
  `0x024F24` in the three scripts, and no instruction of the executable writes it (read).

### How `+0x12` moves `+0x04`, and what `+0x22` is (observed and read)

- The height of an object in flight is the whole word at `+0x04`; the long at `+0x04` has
  its fraction at `+0x06`. Every tick `object_step` subtracts `g_025350` (`0x6000`) from the
  vertical long at `+0x12` and sets the height to the high word of `+0x12 + (+0x04 << 16 |
  +0x06)`, writing back only the word at `+0x04`. `+0x06` is never written, so it stays 0,
  and **the velocity's fraction never carries**: the height moves by the whole part of the
  velocity, rounded down, every tick (read, `0x010B76` to `0x010B86`).
  `tools/m5_observe.py fall` checks the rule for every tick of every bomb and torpedo in
  flight (a rocket's own flight is part 2's, and so is the torpedo's run in the water): it
  held in all 411 cases of `bomb_a`, `high_a`, `torpedo_a` and `bomb_b`, with `+0x06` always
  0 (observed).
- The horizontal long `+0x0E` loses a tenth of its whole part every tick, as the division
  truncates, so below ten pixels a tick it keeps its speed (read, `0x010B58`).
- `+0x22` is the weapon: **0 a rocket, 1 a bomb, 2 the torpedo**, the `weapon_type` of the
  drop (`0x01089C`); the menu's order is rockets, bombs, torpedo, and `weapon_marker` draws
  `rock`, `bomb`, `torp` for 0, 1, 2 (read). Observed: every record in flight carried the
  `weapon_type` at its drop, 1 in the bombing scripts, 0 in the rocket scripts, 2 in
  `torpedo_a`. `object_spawn`'s first entry, the explosion of a crash or a landing on the
  water, makes type 1 with the kind 8. **The guns' rounds are no object at all**:
  `gun_splashes` computes where the bullets reach the ground and splashes and kills there
  (read, `0x0119BC`).

## The targets and the soldiers

Read from the listing and held to the original in the scripts and under the oracle.

### Three kinds of target

| Slot | Shape | Table | What it does |
|---|---|---|---|
| 3 | `dugo`, a dug-out | `target_records_3`, `0x10` | holds soldiers (`+0x08`, 5 at the start), fires at the aircraft within `0x200` pixels (the frames `gun0` to `gnf6`), takes in the soldiers that run into it; empty, it takes one from a barracks every 200 passes |
| 4 | `huta`, a barracks | `target_records_4`, `0x10` | holds soldiers; a hit turns its four records into slot 5 (`hutb`, burnt) and lets its soldiers out; burnt, it smokes for `0x32` puffs |
| `0x0F` to `0x1E` | `pila` to `pilo`, a pillbox | `target_records_f`, `0x0E` | fires; only a rocket destroys it: its records take a slot that shows where it was hit, and it smokes |

A target's records are four: the one that carries the draw bit is the third, and
`0x014AE4` finds them from any x among them. `0x014B54` finds the table entry by the draw
record's byte offset, walking one entry past the table's count (a `dbra` without the
initial branch), which only matters when the record is missing.

**`island_score`** (`0x025450`) keeps two words per island: the soldiers still alive (five
per dug-out and barracks) and the pillboxes still standing. Barracks and dug-outs are not
counted as targets; an island is neutralised when both words are 0, which the last soldier's
death or the last pillbox's destruction finds. Then `0x015AE8` gives the island's bonus
(`island_bonus`, `0x02347C`, by the map and the island), `g_025383` counts the islands left,
and the ticker gets the island's message (`0x0239FA`, with the bonus); the map's last island
also ends the mission (`0x015694`), which appends the next mission's message, or after a
rank's last mission the promotion's, over the last character of the first.

### The soldiers

Five per dug-out and barracks, eight bytes each (`soldier_records`): the x, a direction
byte, a frame, a timer, the island, and the state: 0 free, 1 running, 2 dying, 3 dead.

- **Out**: `0x011E82` puts a soldier into the first free record at the target's east or
  west end by the sign of its direction, from the barracks' release timers in the tick
  (`target_timers`, part 2) and from `0x014FEE` in the pass. The walk over the records has no
  end (`addq.l #8,a1; bra` passes a record in use without counting): it would run past the
  table if every record were in use, which cannot happen, because the soldiers inside the
  targets and the records in use always add up to the table's size (read); the port marks
  that case as a stand-in.
- **Running** (`soldiers_draw`, in the pass): three pixels a pass, the frame 0 to 4, turning
  round at the water; a soldier that reaches a dug-out's records goes in.
- **Dying** (the guns, or any weapon's impact within 16 pixels, `0x011A8C` in the tick):
  the frame steps every third pass, and after frame 7 the soldier is dead, 25 points, one
  soldier fewer on the island. A dead soldier stays drawn at full scale.

### The targets' fire

`target_frame` gives a target's frame: none on the deck; in the eighth-scale view `0x5A` on
a coin of `rand_beam`; at full scale `range_frames` (`0x024C1C`) by the height in steps of
32 and the distance in steps of 40, plus `0x81`, and seven more, the firing frame, on a
draw of `rand_beam`. The table is read by address, and the index can leave its 48 bytes;
`target_range_frame`'s own branch for the eighth-scale view is unreachable from
`target_frame`, which takes that view first (read, and the reach map). `target_fire` then
records the nearest distance for the sound and, on two draws of `rand_beam` against the
distance and the height, hits the aircraft: smoke from the engine (`0x0154E0`) and at the end
of the hit count the oil and the fuel fall.

## Registers that cross a call

The pass's routines are hand-written and hand values on in registers. Two carry over into
what the state records:

- `smoke_at_player` (`0x0154E0`) in a turn adds a byte of `0x024BF0` to the smoke's x with
  `neg.l` and `swap` over the whole of D2, so the upper word D2 came with becomes the move's
  fraction. From `target_fire` that is `rand_beam`'s constant upper word when the target is
  farther than the aircraft is high, else 0 (the upper words of D0 and D1 at the targets'
  routines were 0 at every entry over `rockets_c` and `guns_a`, observed with observers on
  the entries). The port passes it as an argument.
- A pillbox's smoke (`0x013E24`) takes D0's upper word as the fraction of its x; the
  `moveq #$32` before it makes that 0.
- A burnt barracks in view (`0x014E18`) searches `target_records_4` for its record with a
  long compare and no bound; in the eighth-scale view D0's upper word comes from the record's
  draw before it. It was 0 at all 612 searches of `high_a`, which drew burnt barracks in the
  eighth-scale view, and every search found its record (observed, a stop at `0x014E58` and
  `0x014E68`); the port compares the offsets.

## The pools

- **Smoke** (`0x010EE0` in the pass): a record is drawn at its whole position with the
  frame `0x60` plus its kind, moved by its drift, and every seventh pass its kind counts
  down to free. `smoke_claim` (`0x015460`) claims one with two draws of `rand_beam` for its
  drift and raises a height below 16 to 16; it leaves the second drift in D0.
- **Splashes** (`0x0152F8`): the splash in the water, frame `0x67` plus its count at height
  `0x0D`, or the dust of a bullet on land, `0x6E` at height 9 for four passes. Both walks
  over the pool run twenty records (`moveq #$14` before a branch to the `dbra`).
- **Balloons** (`0x01557C`): ported from reading, see "The left-overs".

## The object records in the pass

`0x010702` draws a record by its type: a bomb from `torpedo_shapes` by its frame (`0x40`
on), the torpedo `0x88` or `0x89` by the side it faces and nothing while it runs in the
water (frame `0x0A`), a rocket `0x4C` on or `0x74` on while it still falls; in the
eighth-scale view every one is entry 9 of `eighth_shapes`. Going out (kind 8), eight frames
of the explosion (`0x5A` on) or of the splash (`0x66` on) and then the pass frees the record.
A torpedo that goes out while it runs in the water is never drawn, so its record is never
freed (read).

## The guns' muzzle flash and the weapon counter

- While the guns fire level at full scale, `draw_player` counts `0x025388` round 0 to 3 and
  draws the frame `muzzle_frames` (`0x024C08`: 0, 1, 0, 2) gives: nothing, or
  `hellcat_shapes` entry `0x43` or `0x57` on by the aircraft's frame, ten further on facing
  left, with the exclusive-or blit. Observed in `guns_sea`, `guns_a`, `bomb_b`, `bomb_c` and
  `island_a`; the comparison takes the port's exclusive-or draws as the original's
  `shape_draw_xor` calls.
- The weapon counter's drums turn a row a pass toward the count: the ones drum always, the
  tens drum only while the ones drum passes its rows 0 to 8; both wrap from `0x50` to 1.
  With unlimited weapons (the cheat's `m`, `weapon_count` `0xFF`) both go to `0x64`.

## How the port is held to the original

| Check | Test | What it covers |
|---|---|---|
| T1, attributed | `tests/test_weapons.py::test_every_pass_agrees_and_every_other_difference_is_owed[...]` | the open loop over every M5 script: every pass and every tick that differs from the original reached a stand-in of part 2 or later in that same step, and no step reached one of part 1 (`island_a` and `hit_a` with `--slow`) |
| T3 | `tests/test_weapons.py::test_every_address_the_m5_scripts_write_is_compared_or_excluded` | the completeness list over the M5 scripts, below |
| V6 | `tests/test_oracle_m5.py` | `0x014AE4` and `0x014B54` at every record of map c; `target_range_frame` at both scales; `0x015AE8` for every rank, mission and island; `0x011E82` in both modes; `0x014FEE` with `0x015034`; `smoke_claim`, `splash_spawn`, `smoke_at_player`; `target_frame` and `target_fire`, with `rand_beam` served on both sides from the port's stream |
| T1, T2 | `tests/test_world.py` | every M4 script in both loops, unchanged |

The closed loop over an M5 script is part 2's: it holds only once the tick drops and moves
the weapons.

## The completeness list

`tests/test_weapons.py` sorts every address the original writes during an M5 script's
mission with `tests/m4complete.py`'s lists and two rows of its own: the object record
`0x0146C6` makes up for a crash on land at `0x027700`, part 2's, and the ticker's plane,
which `vblank_server` scrolls by CPU and which the port scrolls in its own plane, held to
the original under the oracle by M4's `test_the_ticker_matches_the_original`. A mission won
goes on to the campaign's next mission at `0x010132`, M7's; the recorder of
`tests/m4compare.py` records nothing after it.

## What stands in, and where

- **Part 2's**, all in the tick, marked `M5 PART 2 STAND-IN` with the address: the drop
  (`0x01B5E2`), a weapon or a shot in flight (`0x010AB6` to `0x010DA5`), the guns' bullets
  (`0x0119C4`), the targets' timers (`0x011DFE`, `0x011E48`), the balloons' step
  (`0x011C66`), the crash on land (`0x01B304`, `0x01BBF4`); and the three regions M4 marked
  M6 that the M5 scripts reach (`0x0113A2`, `0x011C24`, `0x0116BE`).
- **M6's**: the enemy plane counter above 99 (`0x01F186`) and its kill icons (`0x01F206`),
  which only an enemy aircraft shot down raises (`0x01E36E` in `0x01E244`, read); M4 had
  marked them M5.
- **A value**: every soldier record in use when a soldier comes out (`0x011E82`), which the
  balance of soldiers and records rules out.

Part 1 ported two small regions of shared routines that only the tick reaches, because they
complete a routine the oracle tests take whole: the dust on land in `splash_spawn`
(`0x0152D8`) and the floor of 16 in `smoke_claim` (`0x01548A`).

## Appendix: the reach map

Entries per routine and phase during an M5 script's mission, for the sixteen scripts,
written from the joined run above (observed) with

```text
.venv/bin/python tools/reach_observe.py --m5-only --load REACH.json --markdown TABLE.md
```

The windows before the mission are M4's and unchanged (re/notes/porting-m4.md, "Appendix: the
reach map").

### A pass during a mission: `frame_update`'s tree (phase F)

| Routine | Address | `guns_sea` | `guns_a` | `bomb_a` | `high_a` | `rockets_a` | `torpedo_a` | `hit_a` | `crash_a` | `island_a` | `bomb_b` | `bomb_c` | `rockets_c` | `bomb_pause` | `bomb_flip` | `bomb_restart` | `bomb_cheat` |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| `frame_update` | `010228` | 936 | 1528 | 1818 | 2194 | 2328 | 1176 | 4355 | 1983 | 9532 | 2038 | 1864 | 2002 | 1800 | 1818 | 1216 | 1818 |
| `flip_buffers` | `01030c` | 936 | 1528 | 1818 | 2194 | 2328 | 1176 | 4355 | 1983 | 9532 | 2038 | 1864 | 2002 | 1800 | 1818 | 1216 | 1818 |
| `weapon_marker` | `010344` | 936 | 1528 | 1818 | 2194 | 2328 | 1176 | 4355 | 1983 | 9532 | 2038 | 1864 | 2002 | 1800 | 1818 | 1216 | 1818 |
| `draw_player` | `0103a6` | 936 | 1528 | 1818 | 2194 | 2328 | 1176 | 4355 | 1983 | 9532 | 2038 | 1864 | 2002 | 1800 | 1818 | 1216 | 1818 |
| `draw_objects` | `0106be` | 936 | 1528 | 1818 | 2194 | 2328 | 1176 | 4355 | 1983 | 9532 | 2038 | 1864 | 2002 | 1800 | 1818 | 1216 | 1818 |
| `object_draw` | `010702` | 0 | 0 | 236 | 388 | 96 | 33 | 336 | 280 | 1292 | 354 | 354 | 98 | 237 | 236 | 9 | 236 |
| `draw_enemy_aircraft` | `010da6` | 936 | 1528 | 1818 | 2194 | 2328 | 1176 | 4355 | 1983 | 9532 | 2038 | 1864 | 2002 | 1800 | 1818 | 1216 | 1818 |
| `smoke_draw` | `010ee0` | 936 | 1528 | 1818 | 2194 | 2328 | 1176 | 4355 | 1983 | 9532 | 2038 | 1864 | 2002 | 1800 | 1818 | 1216 | 1818 |
| `snapshot_for_draw` | `010f88` | 936 | 1528 | 1818 | 2194 | 2328 | 1176 | 4355 | 1983 | 9532 | 2038 | 1864 | 2002 | 1800 | 1818 | 1216 | 1818 |
| `draw_game_over` | `0110c2` | 936 | 1528 | 1818 | 2194 | 2328 | 1176 | 4355 | 1983 | 9532 | 2038 | 1864 | 2002 | 1800 | 1818 | 1216 | 1818 |
| `soldier_out` | `011e82` | 0 | 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 0 | 0 | 0 |
| `draw_world` | `013772` | 936 | 1528 | 1818 | 2194 | 2328 | 1176 | 4355 | 1983 | 9532 | 2038 | 1864 | 2002 | 1800 | 1818 | 1216 | 1818 |
| `ship_planes` | `01391e` | 936 | 1528 | 1818 | 2194 | 2328 | 1176 | 4355 | 1983 | 9532 | 2038 | 1864 | 2002 | 1800 | 1818 | 1216 | 1818 |
| `airfields_draw` | `013a18` | 936 | 1528 | 1818 | 2194 | 2328 | 1176 | 4355 | 1983 | 9532 | 2038 | 1864 | 2002 | 1800 | 1818 | 1216 | 1818 |
| `deck_aircraft` | `013abc` | 936 | 1528 | 1818 | 2194 | 2328 | 1176 | 4355 | 1983 | 9532 | 2038 | 1864 | 2002 | 1800 | 1818 | 1216 | 1818 |
| `record_extras` | `013b1c` | 28417 | 104465 | 109643 | 676783 | 153151 | 29891 | 312853 | 137769 | 685048 | 150549 | 137669 | 147515 | 109717 | 109643 | 80385 | 109643 |
| `targets_3_draw` | `013d78` | 936 | 1528 | 1818 | 2194 | 2328 | 1176 | 4355 | 1983 | 9532 | 2038 | 1864 | 2002 | 1800 | 1818 | 1216 | 1818 |
| `targets_f_draw` | `013de8` | 936 | 1528 | 1818 | 2194 | 2328 | 1176 | 4355 | 1983 | 9532 | 2038 | 1864 | 2002 | 1800 | 1818 | 1216 | 1818 |
| `ocean` | `013e6c` | 936 | 1528 | 1818 | 2194 | 2328 | 1176 | 4355 | 1983 | 9532 | 2038 | 1864 | 2002 | 1800 | 1818 | 1216 | 1818 |
| `soldiers_draw` | `013eee` | 936 | 1528 | 1818 | 2194 | 2328 | 1176 | 4355 | 1983 | 9532 | 2038 | 1864 | 2002 | 1800 | 1818 | 1216 | 1818 |
| `lift_aircraft` | `01409c` | 936 | 1528 | 1818 | 2194 | 2328 | 1176 | 4355 | 1983 | 9532 | 2038 | 1864 | 2002 | 1800 | 1818 | 1216 | 1818 |
| `islands_draw` | `0140e8` | 936 | 1528 | 1818 | 2194 | 2328 | 1176 | 4355 | 1983 | 9532 | 2038 | 1864 | 2002 | 1800 | 1818 | 1216 | 1818 |
| `map_window` | `01417e` | 936 | 1528 | 1818 | 2194 | 2328 | 1176 | 4355 | 1983 | 9532 | 2038 | 1864 | 2002 | 1800 | 1818 | 1216 | 1818 |
| `window_height` | `0141b4` | 936 | 1528 | 1818 | 433 | 2328 | 1176 | 4355 | 1983 | 9532 | 2038 | 1864 | 2002 | 1800 | 1818 | 1216 | 1818 |
| `window_strip` | `014206` | 936 | 1528 | 1818 | 433 | 2328 | 1176 | 4355 | 1983 | 9532 | 2038 | 1864 | 2002 | 1800 | 1818 | 1216 | 1818 |
| `window_ship` | `014430` | 936 | 1528 | 1818 | 433 | 2328 | 1176 | 4355 | 1983 | 9532 | 2038 | 1864 | 2002 | 1800 | 1818 | 1216 | 1818 |
| `window_background` | `014564` | 936 | 1528 | 1818 | 2194 | 2328 | 1176 | 4355 | 1983 | 9532 | 2038 | 1864 | 2002 | 1800 | 1818 | 1216 | 1818 |
| `window_shape` | `0145a6` | 0 | 8074 | 8348 | 0 | 12422 | 0 | 32436 | 6208 | 70192 | 13110 | 11287 | 12228 | 8352 | 8348 | 3144 | 8348 |
| `ship_at_offset` | `014a4e` | 2899 | 3747 | 3743 | 9735 | 3923 | 3079 | 5115 | 7725 | 11354 | 3743 | 3743 | 3923 | 3743 | 3743 | 4571 | 3743 |
| `ship_at_span` | `014a52` | 3222 | 4686 | 4698 | 10058 | 4894 | 3422 | 6204 | 9108 | 13694 | 4873 | 4892 | 5040 | 4698 | 4698 | 5618 | 4698 |
| `target_records` | `014ae4` | 0 | 0 | 13 | 16 | 6 | 0 | 0 | 5 | 16 | 25 | 25 | 0 | 3 | 13 | 0 | 13 |
| `target_of` | `014b54` | 0 | 0 | 13 | 16 | 6 | 0 | 0 | 5 | 16 | 25 | 25 | 0 | 3 | 13 | 0 | 13 |
| `ship_guns_draw` | `014c3e` | 936 | 1528 | 1818 | 2194 | 2328 | 1176 | 4355 | 1983 | 9532 | 2038 | 1864 | 2002 | 1800 | 1818 | 1216 | 1818 |
| `target_frame` | `014d50` | 1872 | 3056 | 2546 | 3003 | 3934 | 2352 | 8710 | 3966 | 7990 | 8174 | 18778 | 20544 | 2968 | 2546 | 2432 | 2546 |
| `target_range_frame` | `014db8` | 1234 | 2418 | 1908 | 228 | 3256 | 1674 | 7072 | 1796 | 5142 | 6579 | 15269 | 16815 | 2330 | 1908 | 1610 | 1908 |
| `ride_on_ship` | `014eac` | 2899 | 3747 | 3743 | 9735 | 3923 | 3079 | 5115 | 7725 | 11354 | 3743 | 3743 | 3923 | 3743 | 3743 | 4571 | 3743 |
| `target_fire` | `014f5c` | 0 | 294 | 182 | 1063 | 224 | 0 | 1598 | 150 | 1072 | 272 | 858 | 1072 | 239 | 182 | 49 | 182 |
| `target_refill` | `014fee` | 0 | 0 | 2 | 3 | 1 | 0 | 0 | 0 | 48 | 4 | 1 | 0 | 1 | 2 | 0 | 2 |
| `nearest_barracks` | `015034` | 0 | 0 | 2 | 3 | 1 | 0 | 0 | 0 | 48 | 4 | 1 | 0 | 1 | 2 | 0 | 2 |
| `format_to` | `015078` | 2 | 2 | 10 | 10 | 4 | 2 | 2 | 4 | 66 | 24 | 24 | 6 | 4 | 10 | 4 | 10 |
| `format_putch` | `015090` | 16 | 16 | 80 | 80 | 32 | 16 | 16 | 32 | 680 | 192 | 192 | 48 | 32 | 80 | 32 | 80 |
| `flip_view` | `0150b0` | 936 | 1528 | 1818 | 2194 | 2328 | 1176 | 4355 | 1983 | 9532 | 2038 | 1864 | 2002 | 1800 | 1818 | 1216 | 1818 |
| `map_slot_at` | `0150c8` | 0 | 0 | 12325 | 14508 | 5194 | 0 | 0 | 2247 | 19388 | 10169 | 7921 | 0 | 4975 | 12325 | 0 | 12325 |
| `draw_world_shape` | `015174` | 5063 | 9934 | 18779 | 19729 | 18819 | 5843 | 47446 | 13543 | 233105 | 28470 | 32373 | 29625 | 15024 | 18779 | 6026 | 18779 |
| `sub_01520c` | `01520c` | 936 | 1528 | 1818 | 2194 | 2328 | 1176 | 4355 | 1983 | 9532 | 2038 | 1864 | 2002 | 1800 | 1818 | 1216 | 1818 |
| `clip_playfield` | `01524a` | 2808 | 4584 | 5454 | 4821 | 6984 | 3528 | 13065 | 5949 | 28596 | 6114 | 5592 | 6006 | 5400 | 5454 | 3648 | 5454 |
| `clip_dash_window` | `01525c` | 936 | 1528 | 1818 | 2194 | 2328 | 1176 | 4355 | 1983 | 9532 | 2038 | 1864 | 2002 | 1800 | 1818 | 1216 | 1818 |
| `clip_to_waterline` | `01526e` | 1823 | 3007 | 3587 | 2578 | 4587 | 2283 | 8509 | 3475 | 18536 | 4027 | 3679 | 3935 | 3551 | 3587 | 2291 | 3587 |
| `splashes_draw` | `0152f8` | 936 | 1528 | 1818 | 2194 | 2328 | 1176 | 4355 | 1983 | 9532 | 2038 | 1864 | 2002 | 1800 | 1818 | 1216 | 1818 |
| `smoke_claim` | `015460` | 0 | 20 | 33 | 53 | 15 | 0 | 132 | 36 | 186 | 71 | 120 | 167 | 18 | 33 | 3 | 33 |
| `smoke_at_player` | `0154e0` | 0 | 20 | 19 | 3 | 15 | 0 | 132 | 11 | 88 | 26 | 75 | 92 | 18 | 19 | 3 | 19 |
| `balloons_draw` | `01557c` | 936 | 1528 | 1818 | 2194 | 2328 | 1176 | 4355 | 1983 | 9532 | 2038 | 1864 | 2002 | 1800 | 1818 | 1216 | 1818 |
| `mission_won` | `015694` | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| `island_bonus` | `015ae8` | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| `view_show` | `016f20` | 936 | 1528 | 1818 | 2194 | 2328 | 1176 | 4355 | 1983 | 9532 | 2038 | 1864 | 2002 | 1800 | 1818 | 1216 | 1818 |
| `cop_set_split_line` | `01876e` | 936 | 1528 | 1818 | 2194 | 2328 | 1176 | 4355 | 1983 | 9532 | 2038 | 1864 | 2002 | 1800 | 1818 | 1216 | 1818 |
| `cop_wait` | `019a9c` | 936 | 1528 | 1818 | 2194 | 2328 | 1176 | 4355 | 1983 | 9532 | 2038 | 1864 | 2002 | 1800 | 1818 | 1216 | 1818 |
| `cop_install` | `01aa0e` | 936 | 1528 | 1818 | 2194 | 2328 | 1176 | 4355 | 1983 | 9532 | 2038 | 1864 | 2002 | 1800 | 1818 | 1216 | 1818 |
| `wait_vblank` | `01aa3e` | 936 | 1528 | 1818 | 2194 | 2328 | 1176 | 4355 | 1983 | 9532 | 2038 | 1864 | 2002 | 1800 | 1818 | 1216 | 1818 |
| `record_on_ship` | `01cb34` | 4 | 112 | 112 | 4 | 112 | 4 | 114 | 112 | 224 | 112 | 112 | 112 | 112 | 112 | 112 | 112 |
| `ship_of_record` | `01cbf2` | 4 | 112 | 112 | 4 | 112 | 4 | 114 | 112 | 224 | 112 | 112 | 112 | 112 | 112 | 112 | 112 |
| `draw_dashboard` | `01ee16` | 936 | 1528 | 1818 | 2194 | 2328 | 1176 | 4355 | 1983 | 9532 | 2038 | 1864 | 2002 | 1800 | 1818 | 1216 | 1818 |
| `kill_icons` | `01f200` | 4 | 4 | 4 | 4 | 4 | 4 | 4 | 4 | 8 | 4 | 4 | 4 | 4 | 4 | 8 | 4 |
| `enemy_arrows` | `01f21a` | 936 | 1528 | 1818 | 2194 | 2328 | 1176 | 4355 | 1983 | 9532 | 2038 | 1864 | 2002 | 1800 | 1818 | 1216 | 1818 |
| `draw_score` | `01f26a` | 2 | 2 | 10 | 10 | 4 | 2 | 2 | 4 | 64 | 24 | 24 | 6 | 4 | 10 | 4 | 10 |
| `dash_digit` | `01f2b0` | 18 | 18 | 74 | 74 | 32 | 18 | 18 | 32 | 456 | 172 | 172 | 46 | 32 | 74 | 36 | 74 |
| `clip_dashboard` | `01f2dc` | 1872 | 3056 | 3636 | 4388 | 4656 | 2352 | 8710 | 3966 | 19064 | 4076 | 3728 | 4004 | 3600 | 3636 | 2432 | 3636 |
| `rand_beam` | `0203be` | 0 | 746 | 505 | 2353 | 558 | 0 | 4051 | 425 | 2879 | 792 | 2237 | 2865 | 590 | 505 | 108 | 505 |
| `blit_clip_setup` | `0209bc` | 13744 | 31955 | 36507 | 78796 | 48786 | 16088 | 116319 | 42036 | 273413 | 48424 | 47031 | 49911 | 36617 | 36507 | 22596 | 38149 |
| `shape_blit` | `020b0c` | 13660 | 31876 | 36507 | 78796 | 48786 | 16088 | 116319 | 42036 | 273270 | 48373 | 47002 | 49911 | 36617 | 36507 | 22596 | 38149 |
| `shape_draw` | `020ce2` | 13542 | 31758 | 36333 | 78622 | 48612 | 15928 | 115897 | 41020 | 271754 | 48101 | 46730 | 49723 | 36485 | 36333 | 22274 | 37975 |
| `shape_draw_xor` | `020e24` | 84 | 79 | 0 | 0 | 0 | 0 | 0 | 0 | 143 | 51 | 29 | 0 | 0 | 0 | 0 | 0 |
| `rect_fill` | `021010` | 3744 | 12363 | 13682 | 10537 | 19974 | 4704 | 49348 | 14618 | 110126 | 20966 | 19552 | 20576 | 13621 | 13682 | 6835 | 13682 |
| `draw_set_target` | `02124a` | 2808 | 4584 | 5454 | 6582 | 6984 | 3528 | 13065 | 5949 | 28596 | 6114 | 5592 | 6006 | 5400 | 5454 | 3648 | 5454 |
| `clip_set` | `02129c` | 7439 | 12175 | 14495 | 13981 | 18555 | 9339 | 34639 | 15373 | 75728 | 16255 | 14863 | 15947 | 14351 | 14495 | 9587 | 14495 |
| `blit_begin` | `0212ce` | 6601 | 10745 | 12775 | 15407 | 16365 | 8301 | 30686 | 14372 | 67252 | 14315 | 13097 | 14083 | 12649 | 12775 | 8653 | 12775 |
| `blit_end` | `0212d4` | 6601 | 10745 | 12775 | 15407 | 16365 | 8301 | 30686 | 14372 | 67252 | 14315 | 13097 | 14083 | 12649 | 12775 | 8653 | 12775 |
| `sub_022e40` | `022e40` | 6601 | 10745 | 12775 | 15407 | 16365 | 8301 | 30686 | 14372 | 67252 | 14315 | 13097 | 14083 | 12649 | 12775 | 8653 | 12775 |
| `sub_022e8a` | `022e8a` | 6601 | 10745 | 12775 | 15407 | 16365 | 8301 | 30686 | 14372 | 67252 | 14315 | 13097 | 14083 | 12649 | 12775 | 8653 | 12775 |

### A VBlank during a mission (phase V)

| Routine | Address | `guns_sea` | `guns_a` | `bomb_a` | `high_a` | `rockets_a` | `torpedo_a` | `hit_a` | `crash_a` | `island_a` | `bomb_b` | `bomb_c` | `rockets_c` | `bomb_pause` | `bomb_flip` | `bomb_restart` | `bomb_cheat` |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| `vblank_server` | `011754` | 1873 | 3057 | 3637 | 4389 | 4657 | 2353 | 8709 | 3965 | 19062 | 4077 | 3729 | 4005 | 3638 | 3637 | 2432 | 3637 |
| `vblank_server:ticker_glyph` | `011754` | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 60 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| `vblank_server:ticker_message` | `011754` | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 60 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| `vblank_server:ticker_scroll` | `011754` | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 705 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| `read_joy_bits` | `01520e` | 469 | 765 | 910 | 1098 | 1165 | 589 | 2178 | 992 | 4767 | 1020 | 933 | 1002 | 900 | 910 | 609 | 910 |
| `vblank_every_frame` | `01c9ca` | 1873 | 3057 | 3637 | 4389 | 4657 | 2353 | 8709 | 3965 | 19062 | 4077 | 3729 | 4005 | 3599 | 3637 | 2432 | 3637 |
| `read_joystick` | `01ca32` | 469 | 765 | 910 | 1098 | 1165 | 589 | 2178 | 992 | 4767 | 1020 | 933 | 1002 | 900 | 910 | 609 | 910 |
| `read_joy_dispatch` | `01cb20` | 469 | 765 | 910 | 1098 | 1165 | 589 | 2178 | 992 | 4767 | 1020 | 933 | 1002 | 900 | 910 | 609 | 910 |
| `soundfx_vblank` | `01ec64` | 1873 | 3057 | 3637 | 4389 | 4657 | 2353 | 8709 | 3965 | 19062 | 4077 | 3729 | 4005 | 3638 | 3637 | 2432 | 3637 |
| `poll_fire` | `02044c` | 1873 | 3057 | 3637 | 4389 | 4657 | 2353 | 8709 | 3965 | 19062 | 4077 | 3729 | 4005 | 3599 | 3637 | 2432 | 3637 |
| `read_fire_button` | `02046a` | 1873 | 3057 | 3637 | 4389 | 4657 | 2353 | 8709 | 3965 | 19062 | 4077 | 3729 | 4005 | 3599 | 3637 | 2432 | 3637 |
| `input_handler` | `02075a` | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 2 | 1 | 1 | 7 |

### The inner loop beside `frame_update` during a mission (phase M)

| Routine | Address | `guns_sea` | `guns_a` | `bomb_a` | `high_a` | `rockets_a` | `torpedo_a` | `hit_a` | `crash_a` | `island_a` | `bomb_b` | `bomb_c` | `rockets_c` | `bomb_pause` | `bomb_flip` | `bomb_restart` | `bomb_cheat` |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| `run_queued_ticks` | `0114d8` | 936 | 1528 | 1818 | 2194 | 2328 | 1176 | 4355 | 1983 | 9532 | 2038 | 1864 | 2002 | 1800 | 1818 | 1216 | 1818 |
| `sound_slots_clear` | `011f4e` | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 0 | 0 | 0 |
| `sound_channels` | `012066` | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 0 | 0 | 0 |
| `ticker_clear` | `016bbc` | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 0 |
| `view_show` | `016f20` | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 16 | 0 |
| `colour_lerp` | `016ff6` | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1536 | 0 |
| `fade_to_pair` | `0171f2` | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 0 |
| `fade_out_pair` | `0173e6` | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 0 |
| `cop_reset` | `019958` | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 16 | 0 |
| `cop_move` | `0199bc` | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 958 | 0 |
| `cop_move_ptr` | `019a08` | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 288 | 0 |
| `cop_wait` | `019a9c` | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 192 | 0 |
| `cop_colours` | `019b5a` | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 48 | 0 |
| `cop_vport_colours` | `019c0a` | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 48 | 0 |
| `cop_vport_split` | `019c80` | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 16 | 0 |
| `cop_vport_planes` | `019d18` | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 48 | 0 |
| `cop_sprites_off` | `01a06c` | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 16 | 0 |
| `view_build_copper` | `01a0d4` | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 16 | 0 |
| `cop_install` | `01aa0e` | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 16 | 0 |
| `wait_next_vblank` | `01aa32` | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 39 | 0 | 0 | 0 |
| `ingame_keys` | `01ccf6` | 937 | 1529 | 1819 | 2195 | 2329 | 1177 | 4356 | 1984 | 9534 | 2039 | 1865 | 2003 | 1840 | 1819 | 1218 | 1819 |
| `sub_01eac0` | `01eac0` | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 6 | 0 | 0 | 0 |
| `weapon_gauge_reset` | `01edbc` | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 |
| `key_to_char` | `020700` | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 2 | 1 | 1 | 7 |
| `key_available` | `0207d8` | 937 | 1529 | 1819 | 2195 | 2329 | 1177 | 4356 | 1984 | 9534 | 2039 | 1865 | 2003 | 1844 | 1821 | 1220 | 1833 |
| `key_get` | `0207e4` | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 2 | 1 | 1 | 7 |
| `sub_0223cc` | `0223cc` | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1440 | 0 |
| `sub_022424` | `022424` | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1440 | 0 |
| `os_disable` | `022d48` | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 2 | 1 | 1 | 7 |
| `os_enable` | `022d66` | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 2 | 1 | 1 | 7 |
| `gfx_BltClear` | `022e2e` | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 0 |
| `os_console_raw_key_convert` | `022f30` | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 2 | 1 | 1 | 7 |

### The tick during a mission (phase T)

| Routine | Address | `guns_sea` | `guns_a` | `bomb_a` | `high_a` | `rockets_a` | `torpedo_a` | `hit_a` | `crash_a` | `island_a` | `bomb_b` | `bomb_c` | `rockets_c` | `bomb_pause` | `bomb_flip` | `bomb_restart` | `bomb_cheat` |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| `flip_buffers` | `01030c` | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 1 | 2 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| `object_draw_first` | `0107f2` | 0 | 0 | 4 | 4 | 4 | 1 | 0 | 0 | 13 | 6 | 6 | 4 | 4 | 4 | 1 | 4 |
| `object_spawn` | `010820` | 0 | 0 | 0 | 0 | 0 | 0 | 48 | 40 | 83 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| `sub_01099a` | `01099a` | 0 | 0 | 0 | 0 | 4 | 0 | 0 | 0 | 0 | 0 | 0 | 2 | 0 | 0 | 0 | 0 |
| `objects_step` | `010a72` | 468 | 764 | 909 | 1097 | 1164 | 588 | 2182 | 996 | 4776 | 1019 | 932 | 1001 | 900 | 909 | 608 | 909 |
| `object_step` | `010aa6` | 0 | 0 | 120 | 196 | 50 | 17 | 192 | 160 | 694 | 180 | 180 | 51 | 120 | 120 | 5 | 120 |
| `sub_01107c` | `01107c` | 0 | 0 | 4 | 4 | 4 | 1 | 0 | 0 | 13 | 6 | 6 | 4 | 4 | 4 | 1 | 4 |
| `sub_011126` | `011126` | 0 | 0 | 108 | 184 | 38 | 14 | 0 | 0 | 323 | 162 | 162 | 39 | 108 | 108 | 5 | 108 |
| `sub_01115c` | `01115c` | 0 | 0 | 0 | 0 | 8 | 0 | 0 | 0 | 0 | 0 | 0 | 4 | 0 | 0 | 0 | 0 |
| `sub_0111a6` | `0111a6` | 0 | 0 | 0 | 0 | 8 | 0 | 0 | 0 | 0 | 0 | 0 | 4 | 0 | 0 | 0 | 0 |
| `shot_origin` | `011274` | 468 | 764 | 909 | 1097 | 1164 | 588 | 2182 | 996 | 4776 | 1019 | 932 | 1001 | 900 | 909 | 608 | 909 |
| `weapon_menu` | `0112b0` | 455 | 751 | 896 | 1084 | 1151 | 575 | 2155 | 969 | 4731 | 1006 | 919 | 988 | 887 | 896 | 582 | 896 |
| `logic_tick` | `011386` | 468 | 764 | 909 | 1097 | 1164 | 588 | 2182 | 996 | 4776 | 1019 | 932 | 1001 | 900 | 909 | 608 | 909 |
| `lift_step` | `011460` | 455 | 751 | 896 | 1084 | 1151 | 575 | 2155 | 969 | 4731 | 1006 | 919 | 988 | 887 | 896 | 582 | 896 |
| `ship_launches` | `011510` | 468 | 764 | 909 | 1097 | 1164 | 588 | 2182 | 996 | 4776 | 1019 | 932 | 1001 | 900 | 909 | 608 | 909 |
| `airfields_step` | `011622` | 468 | 764 | 909 | 1097 | 1164 | 588 | 2182 | 996 | 4776 | 1019 | 932 | 1001 | 900 | 909 | 608 | 909 |
| `input_queue_pop` | `011714` | 468 | 764 | 909 | 1097 | 1164 | 588 | 2182 | 996 | 4776 | 1019 | 932 | 1001 | 900 | 909 | 608 | 909 |
| `vblank_server` | `011754` | 0 | 0 | 0 | 0 | 0 | 0 | 21 | 21 | 42 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| `vblank_server:ticker_glyph` | `011754` | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| `vblank_server:ticker_message` | `011754` | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| `vblank_server:ticker_scroll` | `011754` | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 21 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| `gun_splashes` | `0119bc` | 468 | 764 | 909 | 1097 | 1164 | 588 | 2182 | 996 | 4776 | 1019 | 932 | 1001 | 900 | 909 | 608 | 909 |
| `guns_ground_x` | `011a46` | 72 | 49 | 0 | 0 | 12 | 0 | 0 | 0 | 125 | 36 | 29 | 6 | 0 | 0 | 0 | 0 |
| `sub_011a84` | `011a84` | 0 | 0 | 0 | 0 | 0 | 0 | 16 | 11 | 27 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| `soldiers_hit` | `011a8c` | 72 | 49 | 4 | 4 | 4 | 1 | 16 | 11 | 165 | 42 | 35 | 4 | 4 | 4 | 0 | 4 |
| `torpedoes_hit` | `011ae2` | 72 | 49 | 4 | 4 | 4 | 1 | 16 | 11 | 165 | 42 | 35 | 4 | 4 | 4 | 0 | 4 |
| `engine_smoke` | `011bfc` | 468 | 764 | 909 | 1097 | 1164 | 588 | 2182 | 996 | 4776 | 1019 | 932 | 1001 | 900 | 909 | 608 | 909 |
| `balloons_step` | `011c5e` | 468 | 764 | 909 | 1097 | 1164 | 588 | 2182 | 996 | 4776 | 1019 | 932 | 1001 | 900 | 909 | 608 | 909 |
| `ships_sinking` | `011cae` | 468 | 764 | 909 | 1097 | 1164 | 588 | 2182 | 996 | 4776 | 1019 | 932 | 1001 | 900 | 909 | 608 | 909 |
| `target_timers` | `011de4` | 468 | 764 | 909 | 1097 | 1164 | 588 | 2182 | 996 | 4776 | 1019 | 932 | 1001 | 900 | 909 | 608 | 909 |
| `soldier_out` | `011e82` | 0 | 0 | 20 | 20 | 5 | 0 | 0 | 5 | 36 | 30 | 30 | 0 | 5 | 20 | 0 | 20 |
| `sound_slots_clear` | `011f4e` | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 2 | 1 | 1 | 1 | 1 | 1 | 1 | 1 |
| `sound_channels` | `012066` | 469 | 765 | 910 | 1098 | 1165 | 589 | 2183 | 997 | 4778 | 1020 | 933 | 1002 | 901 | 910 | 609 | 910 |
| `engine_sound` | `012132` | 468 | 764 | 909 | 1097 | 1164 | 588 | 2182 | 996 | 4776 | 1019 | 932 | 1001 | 900 | 909 | 608 | 909 |
| `sub_0122ce` | `0122ce` | 468 | 764 | 909 | 1097 | 1164 | 588 | 2182 | 996 | 4776 | 1019 | 932 | 1001 | 900 | 909 | 608 | 909 |
| `sub_0122f6` | `0122f6` | 0 | 0 | 4 | 4 | 4 | 1 | 48 | 40 | 116 | 11 | 11 | 4 | 4 | 4 | 0 | 4 |
| `sub_012306` | `012306` | 0 | 0 | 4 | 4 | 4 | 1 | 48 | 40 | 116 | 11 | 11 | 4 | 4 | 4 | 0 | 4 |
| `sub_012324` | `012324` | 0 | 0 | 4 | 4 | 4 | 0 | 48 | 40 | 96 | 6 | 6 | 4 | 4 | 4 | 0 | 4 |
| `sub_01233e` | `01233e` | 0 | 0 | 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| `sub_012354` | `012354` | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 2 | 1 | 1 | 1 | 1 | 1 | 1 | 1 |
| `sub_0123ac` | `0123ac` | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 20 | 5 | 5 | 0 | 0 | 0 | 0 | 0 |
| `next_aircraft` | `0135ce` | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 1 | 2 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| `player_lost_restart` | `0135d8` | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 1 | 2 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| `player_restart_state` | `013684` | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 1 | 2 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| `sub_013756` | `013756` | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 1 | 2 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| `crash_hit` | `0146c6` | 0 | 0 | 0 | 0 | 0 | 0 | 16 | 12 | 28 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| `weapon_hit` | `0146dc` | 0 | 0 | 4 | 4 | 4 | 1 | 16 | 12 | 41 | 6 | 6 | 4 | 4 | 4 | 0 | 4 |
| `ship_at_offset` | `014a4e` | 0 | 0 | 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| `ship_at_span` | `014a52` | 0 | 0 | 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| `target_records` | `014ae4` | 0 | 0 | 6 | 6 | 2 | 0 | 0 | 2 | 16 | 9 | 9 | 8 | 1 | 6 | 0 | 6 |
| `target_release` | `014b40` | 0 | 0 | 4 | 4 | 1 | 0 | 0 | 1 | 10 | 6 | 6 | 0 | 1 | 4 | 0 | 4 |
| `target_of` | `014b54` | 0 | 0 | 4 | 4 | 2 | 0 | 0 | 1 | 14 | 6 | 6 | 4 | 1 | 4 | 0 | 4 |
| `flip_view` | `0150b0` | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 1 | 2 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| `map_slot_at` | `0150c8` | 144 | 98 | 116 | 192 | 44 | 15 | 16 | 13 | 628 | 246 | 232 | 47 | 113 | 116 | 5 | 116 |
| `sub_015104` | `015104` | 0 | 0 | 0 | 0 | 4 | 0 | 0 | 0 | 0 | 0 | 0 | 4 | 0 | 0 | 0 | 0 |
| `sub_015108` | `015108` | 0 | 0 | 0 | 0 | 8 | 0 | 0 | 0 | 0 | 0 | 0 | 8 | 0 | 0 | 0 | 0 |
| `sub_01514c` | `01514c` | 72 | 49 | 0 | 0 | 12 | 0 | 0 | 0 | 125 | 36 | 29 | 6 | 0 | 0 | 0 | 0 |
| `sub_01520c` | `01520c` | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 1 | 2 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| `read_joy_bits` | `01520e` | 0 | 0 | 0 | 0 | 0 | 0 | 5 | 5 | 10 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| `clip_playfield` | `01524a` | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 1 | 2 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| `splash_spawn` | `0152b0` | 72 | 49 | 0 | 0 | 0 | 0 | 0 | 0 | 125 | 36 | 29 | 0 | 0 | 0 | 0 | 0 |
| `smoke_claim` | `015460` | 0 | 31 | 56 | 0 | 106 | 0 | 527 | 45 | 1079 | 95 | 100 | 118 | 69 | 56 | 0 | 56 |
| `sub_0154cc` | `0154cc` | 0 | 0 | 0 | 0 | 0 | 0 | 37 | 37 | 75 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| `smoke_at_player` | `0154e0` | 0 | 31 | 56 | 0 | 106 | 0 | 490 | 8 | 1004 | 95 | 100 | 118 | 69 | 56 | 0 | 56 |
| `sub_015710` | `015710` | 443 | 792 | 936 | 1124 | 1182 | 553 | 1955 | 637 | 4263 | 1046 | 959 | 1019 | 927 | 936 | 589 | 936 |
| `ground_height` | `015714` | 443 | 792 | 936 | 1124 | 1182 | 553 | 1955 | 637 | 4263 | 1046 | 959 | 1019 | 927 | 936 | 589 | 936 |
| `shape_mirror_x` | `015b58` | 24 | 38 | 28 | 26 | 54 | 24 | 88 | 40 | 112 | 32 | 32 | 54 | 28 | 28 | 28 | 28 |
| `view_show` | `016f20` | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 1 | 2 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| `cop_install` | `01aa0e` | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 1 | 2 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| `turn_allowed` | `01aa6e` | 0 | 52 | 52 | 52 | 156 | 0 | 312 | 52 | 780 | 104 | 104 | 156 | 52 | 52 | 52 | 52 |
| `wheel_height` | `01aaea` | 751 | 1396 | 1685 | 2061 | 2176 | 971 | 4098 | 1427 | 8885 | 1905 | 1731 | 1850 | 1667 | 1685 | 991 | 1685 |
| `turn_step` | `01ab80` | 0 | 52 | 52 | 52 | 156 | 0 | 312 | 52 | 780 | 104 | 104 | 156 | 52 | 52 | 52 | 52 |
| `aircraft_frame` | `01abde` | 444 | 790 | 935 | 1123 | 1280 | 554 | 2245 | 659 | 4983 | 1095 | 1008 | 1117 | 926 | 935 | 588 | 935 |
| `wreck_smoke` | `01aed8` | 0 | 0 | 0 | 0 | 0 | 0 | 150 | 150 | 300 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| `lost_wait` | `01af7c` | 0 | 0 | 0 | 0 | 0 | 0 | 150 | 150 | 300 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| `crash` | `01afba` | 0 | 0 | 0 | 0 | 0 | 0 | 25 | 13 | 44 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| `hook_state` | `01b45a` | 444 | 740 | 885 | 1073 | 1130 | 554 | 2078 | 747 | 4504 | 995 | 908 | 967 | 876 | 885 | 538 | 885 |
| `on_the_lift` | `01b4de` | 309 | 605 | 750 | 938 | 995 | 419 | 1768 | 450 | 3891 | 860 | 773 | 832 | 741 | 750 | 403 | 750 |
| `button` | `01b5b0` | 468 | 764 | 909 | 1097 | 1164 | 588 | 2182 | 996 | 4776 | 1019 | 932 | 1001 | 900 | 909 | 608 | 909 |
| `guns` | `01b682` | 468 | 764 | 909 | 1097 | 1164 | 588 | 2182 | 996 | 4776 | 1019 | 932 | 1001 | 900 | 909 | 608 | 909 |
| `deck_span` | `01b7bc` | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 1 | 2 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| `player_reset` | `01b7ec` | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 1 | 2 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| `touches_ground` | `01b8c4` | 308 | 604 | 749 | 937 | 994 | 418 | 1767 | 449 | 3889 | 859 | 772 | 831 | 740 | 749 | 402 | 749 |
| `cable_hook` | `01b92e` | 104 | 104 | 104 | 104 | 104 | 104 | 104 | 104 | 208 | 104 | 104 | 104 | 104 | 104 | 104 | 104 |
| `sub_01b9bc` | `01b9bc` | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 1 | 2 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| `engine_idle` | `01b9cc` | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 2 | 1 | 1 | 1 | 1 | 1 | 1 | 1 |
| `sub_01b9f0` | `01b9f0` | 308 | 604 | 749 | 937 | 994 | 418 | 1767 | 449 | 3889 | 859 | 772 | 831 | 740 | 749 | 402 | 749 |
| `ground_contact` | `01ba80` | 308 | 604 | 749 | 937 | 994 | 418 | 1767 | 449 | 3889 | 859 | 772 | 831 | 740 | 749 | 402 | 749 |
| `enemy_countdown_step` | `01bc02` | 468 | 764 | 909 | 1097 | 1164 | 588 | 2182 | 996 | 4776 | 1019 | 932 | 1001 | 900 | 909 | 608 | 909 |
| `deck_state` | `01bcce` | 412 | 708 | 853 | 1041 | 1098 | 522 | 1871 | 553 | 4097 | 963 | 876 | 935 | 844 | 853 | 506 | 853 |
| `deck_roll` | `01bdba` | 104 | 104 | 104 | 104 | 104 | 104 | 104 | 104 | 208 | 104 | 104 | 104 | 104 | 104 | 104 | 104 |
| `player_motion` | `01bdfa` | 308 | 604 | 749 | 937 | 994 | 418 | 1767 | 449 | 3889 | 859 | 772 | 831 | 740 | 749 | 402 | 749 |
| `flight_controls` | `01bff4` | 308 | 604 | 749 | 937 | 994 | 418 | 1767 | 449 | 3889 | 859 | 772 | 831 | 740 | 749 | 402 | 749 |
| `frame_select` | `01c378` | 444 | 740 | 885 | 1073 | 1130 | 554 | 2078 | 747 | 4504 | 995 | 908 | 967 | 876 | 885 | 538 | 885 |
| `deck_controls` | `01c4e8` | 104 | 104 | 104 | 104 | 104 | 104 | 104 | 104 | 208 | 104 | 104 | 104 | 104 | 104 | 104 | 104 |
| `deck_edge` | `01c5f4` | 104 | 104 | 104 | 104 | 104 | 104 | 104 | 104 | 208 | 104 | 104 | 104 | 104 | 104 | 104 | 104 |
| `player_update` | `01c660` | 468 | 764 | 909 | 1097 | 1164 | 588 | 2182 | 996 | 4776 | 1019 | 932 | 1001 | 900 | 909 | 608 | 909 |
| `record_at` | `01c982` | 751 | 1343 | 1633 | 2009 | 2123 | 971 | 4033 | 1374 | 8762 | 1853 | 1679 | 1797 | 1615 | 1633 | 939 | 1633 |
| `vblank_every_frame` | `01c9ca` | 0 | 0 | 0 | 0 | 0 | 0 | 21 | 21 | 42 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| `read_joystick` | `01ca32` | 0 | 0 | 0 | 0 | 0 | 0 | 5 | 5 | 10 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| `rand_mod` | `01cac8` | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 1 | 2 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| `burn_smoke` | `01cae0` | 0 | 0 | 0 | 0 | 0 | 0 | 37 | 37 | 75 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| `read_joy_dispatch` | `01cb20` | 0 | 0 | 0 | 0 | 0 | 0 | 5 | 5 | 10 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| `sub_01cb30` | `01cb30` | 2098 | 3428 | 4153 | 5093 | 5078 | 2648 | 9103 | 3188 | 19486 | 4553 | 4118 | 4263 | 4108 | 4153 | 2418 | 4153 |
| `record_on_ship` | `01cb34` | 0 | 0 | 0 | 0 | 0 | 0 | 176 | 165 | 347 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| `on_water` | `01cb74` | 0 | 0 | 0 | 0 | 0 | 0 | 26 | 15 | 47 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| `enemy_aircraft_step` | `01e7d6` | 468 | 764 | 909 | 1097 | 1164 | 588 | 2182 | 996 | 4776 | 1019 | 932 | 1001 | 900 | 909 | 608 | 909 |
| `sub_01ea28` | `01ea28` | 27 | 33 | 27 | 87 | 21 | 12 | 138 | 96 | 366 | 63 | 60 | 27 | 33 | 27 | 12 | 27 |
| `sub_01eac0` | `01eac0` | 30 | 41 | 34 | 134 | 28 | 14 | 166 | 104 | 397 | 71 | 71 | 36 | 38 | 34 | 18 | 34 |
| `sub_01eb2e` | `01eb2e` | 27 | 33 | 27 | 87 | 21 | 12 | 138 | 96 | 366 | 63 | 60 | 27 | 33 | 27 | 12 | 27 |
| `sub_01eb4c` | `01eb4c` | 212 | 330 | 208 | 175 | 531 | 97 | 1493 | 238 | 1871 | 390 | 488 | 772 | 231 | 208 | 143 | 208 |
| `soundfx_vblank` | `01ec64` | 0 | 0 | 0 | 0 | 0 | 0 | 21 | 21 | 42 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| `weapon_gauge_reset` | `01edbc` | 0 | 0 | 0 | 0 | 1 | 1 | 1 | 1 | 2 | 0 | 0 | 1 | 0 | 0 | 0 | 0 |
| `rand_beam` | `0203be` | 0 | 161 | 324 | 40 | 540 | 0 | 1496 | 159 | 3395 | 495 | 496 | 516 | 323 | 324 | 0 | 324 |
| `poll_fire` | `02044c` | 0 | 0 | 0 | 0 | 0 | 0 | 21 | 21 | 42 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| `read_fire_button` | `02046a` | 0 | 0 | 0 | 0 | 0 | 0 | 21 | 21 | 42 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| `sub_0204e4` | `0204e4` | 444 | 740 | 885 | 1073 | 1130 | 554 | 2078 | 747 | 4504 | 995 | 908 | 967 | 876 | 885 | 538 | 885 |
| `sub_0204ec` | `0204ec` | 444 | 740 | 885 | 1073 | 1130 | 554 | 2078 | 747 | 4504 | 995 | 908 | 967 | 876 | 885 | 538 | 885 |
| `shape_find_c` | `0204f4` | 2098 | 3428 | 4153 | 5093 | 5078 | 2648 | 9103 | 3188 | 19486 | 4553 | 4118 | 4263 | 4108 | 4153 | 2418 | 4153 |
| `shape_find` | `020560` | 2098 | 3428 | 4153 | 5093 | 5078 | 2648 | 9103 | 3188 | 19486 | 4553 | 4118 | 4263 | 4108 | 4153 | 2418 | 4153 |
| `rect_fill` | `021010` | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 1 | 2 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| `draw_set_target` | `02124a` | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 1 | 2 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| `clip_set` | `02129c` | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 1 | 2 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| `blit_begin` | `0212ce` | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 1 | 2 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| `blit_end` | `0212d4` | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 1 | 2 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| `ffp_add` | `021c9c` | 308 | 604 | 749 | 937 | 994 | 418 | 1767 | 449 | 3889 | 859 | 772 | 831 | 740 | 749 | 402 | 749 |
| `ffp_neg` | `021cb0` | 107 | 430 | 682 | 833 | 575 | 372 | 1174 | 381 | 2975 | 587 | 525 | 427 | 673 | 682 | 335 | 682 |
| `ffp_fix` | `021cc4` | 924 | 1812 | 2247 | 2811 | 2982 | 1254 | 5301 | 1347 | 11667 | 2577 | 2316 | 2493 | 2220 | 2247 | 1206 | 2247 |
| `ffp_div` | `021cd8` | 616 | 1208 | 1498 | 1874 | 1988 | 836 | 3534 | 898 | 7778 | 1718 | 1544 | 1662 | 1480 | 1498 | 804 | 1498 |
| `ffp_flt` | `021ce2` | 616 | 1208 | 1498 | 1874 | 1988 | 836 | 3534 | 898 | 7778 | 1718 | 1544 | 1662 | 1480 | 1498 | 804 | 1498 |
| `ffp_mul` | `021cec` | 924 | 1812 | 2247 | 2811 | 2982 | 1254 | 5301 | 1347 | 11667 | 2577 | 2316 | 2493 | 2220 | 2247 | 1206 | 2247 |
| `sub_021d7c` | `021d7c` | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 |
| `sub_021e24` | `021e24` | 0 | 0 | 0 | 0 | 0 | 0 | 30 | 30 | 54 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| `sub_0222f4` | `0222f4` | 0 | 0 | 0 | 0 | 0 | 0 | 30 | 30 | 54 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| `os_disable` | `022d48` | 468 | 764 | 909 | 1097 | 1164 | 588 | 2182 | 996 | 4776 | 1019 | 932 | 1001 | 900 | 909 | 608 | 909 |
| `os_enable` | `022d66` | 468 | 764 | 909 | 1097 | 1164 | 588 | 2182 | 996 | 4776 | 1019 | 932 | 1001 | 900 | 909 | 608 | 909 |
| `sub_022e40` | `022e40` | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 1 | 2 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| `sub_022e8a` | `022e8a` | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 1 | 2 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| `gfx_WaitTOF` | `022eee` | 0 | 0 | 0 | 0 | 0 | 0 | 21 | 21 | 42 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |

### Entropy reads, by the routine that called `rand_beam`

| Window | Phase | Caller | `guns_sea` | `guns_a` | `bomb_a` | `high_a` | `rockets_a` | `torpedo_a` | `hit_a` | `crash_a` | `island_a` | `bomb_b` | `bomb_c` | `rockets_c` | `bomb_pause` | `bomb_flip` | `bomb_restart` | `bomb_cheat` |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| outer | M | `rand_mod` | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 2 | 1 |
| setup | M | `rand_mod` | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 4 | 2 | 2 | 2 | 2 | 2 | 4 | 2 |
| mission | F | `smoke_claim` | 0 | 40 | 66 | 106 | 30 | 0 | 264 | 72 | 372 | 142 | 240 | 334 | 36 | 66 | 6 | 66 |
| mission | F | `target_fire` | 0 | 412 | 257 | 110 | 304 | 0 | 2189 | 203 | 1435 | 378 | 1139 | 1459 | 315 | 257 | 53 | 257 |
| mission | F | `target_frame` | 0 | 294 | 182 | 2137 | 224 | 0 | 1598 | 150 | 1072 | 272 | 858 | 1072 | 239 | 182 | 49 | 182 |
| mission | T | `burn_smoke` | 0 | 0 | 0 | 0 | 0 | 0 | 37 | 37 | 75 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| mission | T | `engine_smoke` | 0 | 99 | 172 | 0 | 292 | 0 | 404 | 31 | 1056 | 245 | 236 | 264 | 165 | 172 | 0 | 172 |
| mission | T | `object_spawn` | 0 | 0 | 0 | 0 | 16 | 0 | 0 | 0 | 0 | 0 | 0 | 16 | 0 | 0 | 0 | 0 |
| mission | T | `rand_mod` | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 1 | 2 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| mission | T | `smoke_claim` | 0 | 62 | 112 | 0 | 212 | 0 | 1054 | 90 | 2158 | 190 | 200 | 236 | 138 | 112 | 0 | 112 |
| mission | T | `soldier_out` | 0 | 0 | 40 | 40 | 20 | 0 | 0 | 0 | 104 | 60 | 60 | 0 | 20 | 40 | 0 | 40 |

## Appendix: the regions no run executed

Every region of a ported routine that no run of either milestone executed - M4's scripts, the
night mission, the key runs, the fifteen setups and the sixteen M5 scripts - with the
stand-in marker that covers it or what it is otherwise; below them, the markers whose region
the original did run (all in the tick, part 2's, or M6's and M7's) and the markers that stand
for a value rather than a region. Written by

```text
.venv/bin/python tools/reach_observe.py --m5 --blocks --setups --jobs 12 --json REACH.json
.venv/bin/python tools/reach_observe.py --cold REACH.json
```

| Routine | Region no run executed | Stand-in marker, or what it is | Owed to |
|---|---|---|---|
| `main` `0x010006` | `0x010036`-`0x010041` | M3's: the command line's demo file, which the port has no command line for | |
| `main` `0x010006` | `0x010104`-`0x010109` | ported from reading: `demo_mode` sets `0x026D44` before step S | |
| `main` `0x010006` | `0x01015C`-`0x01015F` | `0x010132`-`0x01018D`, the next mission of a campaign | M7 |
| `main` `0x010006` | `0x0101B4`-`0x0101BD` | ported from reading: a demo ends on the fire button | |
| `frame_update` `0x010228` | `0x0102BC`-`0x0102CD` | ported from reading: `player_lost_restart` from `frame_update`, when `0x024F24` is set, which no instruction of the executable does | |
| `draw_player` `0x0103A6` | `0x01043E`-`0x01045B` | unreachable: no branch leads there | |
| `draw_player` `0x0103A6` | `0x0104D4`-`0x0104D5` | ported from reading: the climb clamped at -2 in the eighth-scale view | |
| `draw_player` `0x0103A6` | `0x0105F0`-`0x0105F1` | ported from reading: the cable's end when the aircraft faces right | |
| `draw_objects` `0x0106BE` | `0x0106F6`-`0x0106F9` | ported from reading: the extra object record drawn | |
| `object_draw` `0x010702` | `0x010752`-`0x010755` | ported from reading: the torpedo drawn facing the other way (+`0x1F` negative) | |
| `object_spawn` `0x010820` | `0x010840`-`0x010841` | ported from reading: all fifteen object records in use, nothing is left | |
| `object_spawn` `0x010820` | `0x010970`-`0x010971` | M5 part 2: a rocket's frame from the pitch, clamped at 0 (`object_spawn`'s second entry, behind the stand-in at `0x01B5E2`) | |
| `objects_step` `0x010A72` | `0x010A9E`-`0x010AA1` | ported from reading: the extra object record walked as the others are | |
| `object_step` `0x010AA6` | `0x010B1E`-`0x010B21` | `0x010AB6`-`0x010DA5`, a weapon or a shot in flight | M5 PART 2 |
| `object_step` `0x010AA6` | `0x010B3C`-`0x010B43` | `0x010AB6`-`0x010DA5`, a weapon or a shot in flight | M5 PART 2 |
| `object_step` `0x010AA6` | `0x010B94`-`0x010BEF` | `0x010AB6`-`0x010DA5`, a weapon or a shot in flight | M5 PART 2 |
| `object_step` `0x010AA6` | `0x010C12`-`0x010C1F` | `0x010AB6`-`0x010DA5`, a weapon or a shot in flight | M5 PART 2 |
| `object_step` `0x010AA6` | `0x010C36`-`0x010C6F` | `0x010AB6`-`0x010DA5`, a weapon or a shot in flight | M5 PART 2 |
| `object_step` `0x010AA6` | `0x010D18`-`0x010DA5` | `0x010AB6`-`0x010DA5`, a weapon or a shot in flight | M5 PART 2 |
| `draw_enemy_aircraft` `0x010DA6` | `0x010DBA`-`0x010E15` | `0x010DBA`, the formation words of `0x0251D8` | M6 |
| `draw_enemy_aircraft` `0x010DA6` | `0x010E26`-`0x010ED1` | `0x010E26`, an enemy aircraft | M6 |
| `draw_game_over` `0x0110C2` | `0x011118`-`0x011123` | ported from reading; tests/`test_oracle_m4.py`, every count | |
| `choose_night` `0x0111FC` | `0x011218`-`0x01122D` | ported from reading; reached only between two missions, M7's next mission | |
| `weapon_menu` `0x0112B0` | `0x0112D4`-`0x0112D5` | ported from reading: the cursor keys and Return in the weapon menu | |
| `weapon_menu` `0x0112B0` | `0x0112DE`-`0x0112DF` | ported from reading: the cursor keys and Return in the weapon menu | |
| `weapon_menu` `0x0112B0` | `0x0112E8`-`0x0112E9` | ported from reading: the cursor keys and Return in the weapon menu | |
| `weapon_menu` `0x0112B0` | `0x0112F2`-`0x0112F5` | ported from reading: the cursor keys and Return in the weapon menu | |
| `run_queued_ticks` `0x0114D8` | `0x0114E0`-`0x0114E5` | `0x0114E0`, `run_queued_ticks`, demo playback and recording | M7 |
| `run_queued_ticks` `0x0114D8` | `0x0114EE`-`0x0114EF` | ported from reading: nothing runs while paused | |
| `run_queued_ticks` `0x0114D8` | `0x011508`-`0x01150D` | ported from reading: `demo_mode` sets `0x026D44` | |
| `ship_launches` `0x011510` | `0x01152A`-`0x011569` | `0x01152A`, the Japanese carrier's aircraft | M6 |
| `ship_launches` `0x011510` | `0x011572`-`0x011573` | ported from reading: nothing is launched while `0x027348` counts down | |
| `ship_launches` `0x011510` | `0x0115AC`-`0x0115E9` | `0x0115C4`-`0x0115E9`, a ship launching an aircraft | M6 |
| `ship_launches` `0x011510` | `0x0115F4`-`0x011621` | `0x0115F4`-`0x011621`, the last ship's aircraft readied | M6 |
| `airfields_step` `0x011622` | `0x011630`-`0x011689` | `0x011630`, an enemy aircraft taking off | M6 |
| `airfields_step` `0x011622` | `0x0116CA`-`0x011709` | `0x0116BE`-`0x011709`, the player near an enemy airfield | M6 |
| `vblank_server` `0x011754` | `0x011790`-`0x0117D3` | M3's input half: demo playback (M7) | |
| `vblank_server` `0x011754` | `0x01180A`-`0x011841` | M3's input half: demo recording (M7) | |
| `vblank_server` `0x011754` | `0x0118EC`-`0x0118F7` | ported from reading; tests/`test_oracle_m4.py`, the ticker: a message's end | |
| `balloons_step` `0x011C5E` | `0x011C66`-`0x011CAB` | `0x011C66`, the balloons | M5 PART 2 |
| `ships_sinking` `0x011CAE` | `0x011CCA`-`0x011CCD` | `0x011CCA`, a ship sinking (`0x011CD8`) | M6 |
| `target_timers` `0x011DE4` | `0x011E6E`-`0x011E6F` | M5 part 2: the release timer from `vblank_total`, 0 counting as 3 | |
| `soldier_out` `0x011E82` | `0x011EF2`-`0x011EF5` | ported from reading: every soldier record in use, nobody comes out | |
| `soldier_out` `0x011E82` | `0x011F42`-`0x011F47` | ported from reading: a dug-out's soldier turned round by `rand_beam` | |
| `engine_sound` `0x012132` | `0x0121D8`-`0x012207` | the sound slots (M8): an enemy aircraft's distance for its engine | |
| `engine_sound` `0x012132` | `0x01221E`-`0x012225` | the sound slots (M8): an enemy aircraft's distance for its engine | |
| `map_load` `0x012ADC` | `0x012B80`-`0x012B83` | an allocation failed, fatal; the port's tables are fixed (src/mission.def) | |
| `free_map` `0x012BBE` | `0x012BF6`-`0x012C0D` | ported from reading: a ship released at the end of a mission | |
| `free_map` `0x012BBE` | `0x012C1A`-`0x012C31` | ported from reading: a ship released at the end of a mission | |
| `free_map` `0x012BBE` | `0x012C3E`-`0x012C55` | ported from reading: a ship released at the end of a mission | |
| `free_map` `0x012BBE` | `0x012C62`-`0x012C79` | ported from reading: a ship released at the end of a mission | |
| `map_scan` `0x012D5A` | `0x0130AE`-`0x0130B1` | an allocation failed, fatal; the port's tables are fixed (src/mission.def) | |
| `load_ship_shapes` `0x013252` | `0x01327C`-`0x013283` | battleship.shp missing from the disk; the port loads every container at start-up | |
| `load_ship_shapes` `0x013252` | `0x0132C4`-`0x0132C7` | destroyer.shp missing, fatal; the port loads every container at start-up | |
| `load_ship_shapes` `0x013252` | `0x0132FE`-`0x013301` | cruiseship.shp missing, fatal; the port loads every container at start-up | |
| `load_ship_shapes` `0x013252` | `0x013346`-`0x013349` | japcarrier.shp missing, fatal; the port loads every container at start-up | |
| `ship_guns_setup` `0x01350E` | `0x013516`-`0x013517` | ported from reading: nothing for a loaded game | |
| `draw_world` `0x013772` | `0x013900`-`0x013901` | ported from reading: the distance handed to the sound engine | |
| `ship_planes` `0x01391E` | `0x01395A`-`0x01396B` | `0x01395A`, the last ship's clip at full scale | M6 |
| `ship_planes` `0x01391E` | `0x013976`-`0x0139B7` | `0x013976`, aircraft on a ship's deck | M6 |
| `ship_planes` `0x01391E` | `0x0139CE`-`0x013A0D` | `0x0139D6`, the japanese carrier's crane | M6 |
| `airfields_draw` `0x013A18` | `0x013A36`-`0x013AB1` | `0x013A36`, an airfield in view | M6 |
| `deck_aircraft` `0x013ABC` | `0x013ADA`-`0x013ADB` | ported from reading: more than nine lives count as nine | |
| `record_extras` `0x013B1C` | `0x013B68`-`0x013B6B` | ported from reading: an island's flag with the player past the island's end | |
| `soldiers_draw` `0x013EEE` | `0x013FA8`-`0x013FB5` | ported from reading: an island neutralised that is not the map's last | |
| `soldiers_draw` `0x013EEE` | `0x013FE8`-`0x013FED` | ported from reading: a soldier turning round at the water | |
| `window_strip` `0x014206` | `0x014244`-`0x01424D` | ported from reading: the 3-D view over an enemy ship whose +`0x12` is 6000 | |
| `window_strip` `0x014206` | `0x0142AC`-`0x01430B` | `0x0142BC`, an enemy aircraft in the 3-D view | M6 |
| `window_shape` `0x0145A6` | `0x01464C`-`0x014655` | ported from reading: an enemy ship's own shapes in the 3-D view | |
| `window_shape` `0x0145A6` | `0x014662`-`0x014665` | ported from reading: an enemy ship's own shapes in the 3-D view | |
| `window_shape` `0x0145A6` | `0x014694`-`0x0146AD` | ported from reading: the shape of a record in the 3-D view | |
| `ship_at_span` `0x014A52` | `0x014A5A`-`0x014A6F` | ported from reading; tests/`test_oracle_m4.py`, `ship_at_offset` | |
| `ship_at_span` `0x014A52` | `0x014A78`-`0x014A8D` | ported from reading; tests/`test_oracle_m4.py`, `ship_at_offset` | |
| `ship_at_span` `0x014A52` | `0x014A96`-`0x014AAB` | ported from reading; tests/`test_oracle_m4.py`, `ship_at_offset` | |
| `ship_at_span` `0x014A52` | `0x014AB4`-`0x014AC9` | ported from reading; tests/`test_oracle_m4.py`, `ship_at_offset` | |
| `target_of` `0x014B54` | `0x014B88`-`0x014B97` | ported from reading: no draw record among the four, no target | |
| `target_of` `0x014B54` | `0x014BC6`-`0x014BCB` | ported from reading: a burnt barracks not in the table, no target | |
| `target_of` `0x014B54` | `0x014BF4`-`0x014BF9` | ported from reading: a dug-out not in the table, no target | |
| `target_of` `0x014B54` | `0x014C2C`-`0x014C31` | ported from reading: a pillbox not in the table, no target | |
| `target_of` `0x014B54` | `0x014C3A`-`0x014C3D` | ported from reading: another slot, no target | |
| `ship_guns_draw` `0x014C3E` | `0x014C66`-`0x014D49` | `0x014C66`, an enemy ship's guns | M6 |
| `target_range_frame` `0x014DB8` | `0x014DCA`-`0x014DCF` | unreachable from `target_frame`, which takes the eighth-scale view itself; `ship_guns_draw` (M6) is its other caller | |
| `target_refill` `0x014FEE` | `0x01501E`-`0x01501F` | ported from reading: the barracks east of the dug-out, its soldier runs west | |
| `nearest_barracks` `0x015034` | `0x015060`-`0x015061` | ported from reading: the barracks west of the dug-out, the distance negated | |
| `smoke_claim` `0x015460` | `0x01547A`-`0x01547D` | ported from reading: all forty smoke records in use, nothing is left | |
| `balloons_draw` `0x01557C` | `0x015584`-`0x015621` | ported from reading: the balloons, which only `mission_won`'s promotion releases: on maps a to c map c with its three islands neutralised (re/notes/porting-m5.md) | |
| `ticker_say` `0x015624` | `0x015624`-`0x01563F` | ported from reading: an island neutralised that is not the map's last, its message (`0x015624`) | |
| `mission_won` `0x015694` | `0x0156B2`-`0x0156E7` | ported from reading: the rank's last mission won, the promotion (map c) | |
| `ground_height` `0x015714` | `0x015866`-`0x015877` | ported from reading; tests/`test_oracle_m4.py`, every record of five maps | |
| `load_dash_assets` `0x01653C` | `0x016568`-`0x01656B` | dash.shp missing, fatal; the port loads every container at start-up | |
| `screen_game_restore` `0x016D32` | `0x016D32`-`0x016D79` | ported from reading: the play screen back after the save or the load dialog | |
| `demo_end` `0x01852A` | `0x018536`-`0x01855D` | `0x018536`, saving a recorded demo | M7 |
| `turn_allowed` `0x01AA6E` | `0x01AA9A`-`0x01AACD` | ported from reading; tests/`test_oracle_m4.py`, an enemy aircraft that stops a turn | |
| `crash` `0x01AFBA` | `0x01B00A`-`0x01B00F` | M5 part 2: ported from reading (M4), the crash on land or a ship | |
| `crash` `0x01AFBA` | `0x01B0E2`-`0x01B1A7` | M5 part 2: ported from reading (M4), a wreck sliding along a ship | |
| `crash` `0x01AFBA` | `0x01B1B4`-`0x01B1BB` | ported from reading; tests/`test_oracle_m4.py`, the aircraft down on a ship | |
| `crash` `0x01AFBA` | `0x01B1D4`-`0x01B1F7` | ported from reading; tests/`test_oracle_m4.py`, the attitude levelling out | |
| `crash` `0x01AFBA` | `0x01B200`-`0x01B2A1` | ported from reading; tests/`test_oracle_m4.py`, a wreck sliding along a ship | |
| `crash` `0x01AFBA` | `0x01B41A`-`0x01B423` | M5 part 2: ported from reading (M4), a wreck at rest on a ship | |
| `hook_state` `0x01B45A` | `0x01B4A8`-`0x01B4AB` | ported from reading; tests/`test_oracle_m4.py`, the hook with the carrier sunk | |
| `on_the_lift` `0x01B4DE` | `0x01B538`-`0x01B56F` | ported from reading; tests/`test_oracle_m4.py`, on the lift facing right | |
| `on_the_lift` `0x01B4DE` | `0x01B582`-`0x01B589` | ported from reading; tests/`test_oracle_m4.py`, short of the lift | |
| `button` `0x01B5B0` | `0x01B5DA`-`0x01B5E1` | M5 part 2: the other weapon not dropped inside a turn (attitude 6 to 16) | |
| `guns` `0x01B682` | `0x01B6B0`-`0x01B79D` | `0x01B6B0`, the guns at an enemy aircraft | M6 |
| `ground_contact` `0x01BA80` | `0x01BB68`-`0x01BB81` | ported from reading; tests/`test_oracle_m4.py`, a bounce off the deck | |
| `ground_contact` `0x01BA80` | `0x01BBBA`-`0x01BBC3` | M5 part 2: ported from reading (M4), a crash on a deck | |
| `enemy_countdown_step` `0x01BC02` | `0x01BC5E`-`0x01BCC9` | `0x01BC66`, the enemy aircraft come | M6 |
| `deck_state` `0x01BCCE` | `0x01BCEA`-`0x01BCF9` | ported from reading; tests/`test_oracle_m4.py`, the deck state | |
| `deck_state` `0x01BCCE` | `0x01BD7A`-`0x01BD91` | ported from reading; tests/`test_oracle_m4.py`, the deck state | |
| `player_motion` `0x01BDFA` | `0x01BF84`-`0x01BF89` | ported from reading; tests/`test_oracle_m4.py`, `player_motion` | |
| `player_motion` `0x01BDFA` | `0x01BFE8`-`0x01BFEF` | ported from reading; tests/`test_oracle_m4.py`, `player_motion` | |
| `flight_controls` `0x01BFF4` | `0x01C074`-`0x01C085` | ported from reading; tests/`test_oracle_m4.py`, the stick in the air | |
| `flight_controls` `0x01BFF4` | `0x01C09C`-`0x01C09F` | ported from reading; tests/`test_oracle_m4.py`, the stick in the air | |
| `flight_controls` `0x01BFF4` | `0x01C12E`-`0x01C131` | ported from reading; tests/`test_oracle_m4.py`, the stick in the air | |
| `flight_controls` `0x01BFF4` | `0x01C200`-`0x01C20D` | ported from reading; tests/`test_oracle_m4.py`, the stick in the air | |
| `flight_controls` `0x01BFF4` | `0x01C2A0`-`0x01C2CD` | ported from reading; tests/`test_oracle_m4.py`, the stick in the air | |
| `flight_controls` `0x01BFF4` | `0x01C326`-`0x01C34F` | ported from reading; tests/`test_oracle_m4.py`, the stick in the air | |
| `deck_controls` `0x01C4E8` | `0x01C5E6`-`0x01C5EB` | ported from reading; tests/`test_oracle_m4.py`, the stick on the deck | |
| `player_update` `0x01C660` | `0x01C6E8`-`0x01C705` | ported from reading: the aircraft below the sea without a crash | |
| `player_update` `0x01C660` | `0x01C80C`-`0x01C82F` | M5 part 2: ported from reading (M4), the burning wreck on a ship | |
| `player_update` `0x01C660` | `0x01C8EE`-`0x01C8EF` | ported from reading: state 9 does nothing | |
| `player_update` `0x01C660` | `0x01C934`-`0x01C94B` | the player update's jump table: data | |
| `flash_set` `0x01CAB4` | `0x01CAB4`-`0x01CAC7` | ported from reading: the sky's flash, which a crash on a ship sets | |
| `record_on_ship` `0x01CB34` | `0x01CB50`-`0x01CB51` | ported from reading: a record at the list's end is on no ship | |
| `ship_of_record` `0x01CBF2` | `0x01CC04`-`0x01CC0F` | ported from reading: a debugging line to the console, and 1 | |
| `ship_of_record` `0x01CBF2` | `0x01CC68`-`0x01CCB5` | ported from reading: a debugging line to the console, and 1 | |
| `ingame_keys` `0x01CCF6` | `0x01CD92`-`0x01CD9F` | ported from reading: the save dialog on the carrier | |
| `ingame_keys` `0x01CCF6` | `0x01CE0A`-`0x01CE1D` | ported from reading: the load dialog cancelled | |
| `ingame_keys` `0x01CCF6` | `0x01CE26`-`0x01CE27` | the crash reporter of Control-B, which the port does not have (re/notes/keys.md) | |
| `enemy_aircraft_step` `0x01E7D6` | `0x01E7FC`-`0x01E8A7` | `0x01E7FC`, an enemy aircraft | M6 |
| `lives_gauge_reset` `0x01EDEA` | `0x01EDF4`-`0x01EDF5` | ported from reading; tests/`test_oracle_m4.py`, the gauge resets | |
| `lives_gauge_reset` `0x01EDEA` | `0x01EDFE`-`0x01EDFF` | ported from reading; tests/`test_oracle_m4.py`, the gauge resets | |
| `draw_dashboard` `0x01EE16` | `0x01F102`-`0x01F103` | ported from reading: negative lives count as none | |
| `draw_dashboard` `0x01EE16` | `0x01F10C`-`0x01F10D` | ported from reading: more than nine lives count as nine | |
| `draw_dashboard` `0x01EE16` | `0x01F12E`-`0x01F133` | ported from reading: the lives drum turning down, a life more | |
| `draw_dashboard` `0x01EE16` | `0x01F186`-`0x01F187` | `0x01F186`, the enemy plane counter above 99, which only enemy aircraft shot down raise | M6 |
| `draw_dashboard` `0x01EE16` | `0x01F1DA`-`0x01F1DB` | ported from reading: the first row of bars clamped at seven | |
| `draw_dashboard` `0x01EE16` | `0x01F1EE`-`0x01F1EF` | ported from reading: the second row of bars clamped at seven | |
| `kill_icons` `0x01F200` | `0x01F206`-`0x01F217` | `0x01F206`, the enemy plane counter's kill icons, which only enemy aircraft shot down raise | M6 |
| `enemy_arrows` `0x01F21A` | `0x01F226`-`0x01F235` | `0x01F226`-`0x01F269`, an arrow to an enemy aircraft | M6 |
| `enemy_arrows` `0x01F21A` | `0x01F240`-`0x01F269` | `0x01F226`-`0x01F269`, an arrow to an enemy aircraft | M6 |
| `line_draw` `0x021318` | `0x021342`-`0x021343` | ported from reading, PROVISIONAL: the clipping of `line_draw` | |
| `line_draw` `0x021318` | `0x021354`-`0x021357` | ported from reading, PROVISIONAL: the clipping of `line_draw` | |
| `line_draw` `0x021318` | `0x02136A`-`0x02136B` | ported from reading, PROVISIONAL: the clipping of `line_draw` | |
| `line_draw` `0x021318` | `0x02137C`-`0x02137F` | ported from reading, PROVISIONAL: the clipping of `line_draw` | |
| `line_draw` `0x021318` | `0x02138E`-`0x0214EB` | ported from reading, PROVISIONAL: the clipping of `line_draw` | |
| `line_draw` `0x021318` | `0x021556`-`0x021561` | the blitter's busy wait, which the port's line has none of | |
| `line_draw` `0x021318` | `0x0215D0`-`0x0215D7` | ported from reading, PROVISIONAL: a line wholly outside the clip | |
| | run by the original | `0x0113A2`, the oil leaking from a damaged engine | M6 |
| | run by the original | `0x0119C4`, the guns' bullets in the water | M5 PART 2 |
| | run by the original | `0x011C24`, smoke from a damaged engine | M6 |
| | run by the original | `0x011DFE`, a slot-3 target's timer | M5 PART 2 |
| | run by the original | `0x011E48`, a slot-4 target's timer | M5 PART 2 |
| | run by the original | `0x019152`, `save_game_read`: a saved game loaded | M7 |
| | run by the original | `0x01B304`, a wreck at rest on land or a deck | M5 PART 2 |
| | run by the original | `0x01B5E2`, the other weapon dropped | M5 PART 2 |
| | run by the original | `0x01BBF4`, what a crash on land does to the island's targets | M5 PART 2 |
| | run by the original | `0x01CDD4`, a loaded game: the briefing and the mission again | M7 |
| | no region: a value | more than four islands, in `0x0140E8` | M6 |
| | no region: a value | a negative score, in `0x01F26A` | M7 |
| | no region: a value | every soldier record in use, `0x011E82` walks past the table | M5 |
| | no region: a value | a ticker message outside the registered state | M7 |
