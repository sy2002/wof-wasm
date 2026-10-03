# M6: the enemy aircraft, the ships, the torpedo attack and the carrier's defence

Milestone M6 of `SPEC.md` section 9, on all fifteen maps. It is done in two parts, cut by
phase as M4 and M5 were: part 1 is everything the M6 scripts execute in a pass
(`frame_update`'s tree, phase F) and in a VBlank (phase V); part 2 is what they execute in
the tick (phase T): the enemy aircraft's flight, their launches, the guns at them, the
ships' launches and sinking, the torpedo into a ship, the crash on a ship, and the closed
loop on all fifteen maps. This note covers both parts. What the enemy is and does,
observed, is `re/notes/enemy.md`. Addresses use the standard load layout.

Every statement is either **observed**, with the tool or test that shows it, or **read**,
which means it comes from the listing alone.

```text
src/world.c              the pass: draw_enemy_aircraft with the wrecks and the guns' flash,
                         ship_planes, airfields_draw, ship_guns_draw with the shells, the islands
src/dash.c               the 3-D view's enemy aircraft, the arrows, the kill counter and its icons
src/targets.c            target_fire with the upper words its callers hand it; the message of a
                         ship sunk (0x015640)
src/enemy.c              the tick: the enemy module 0x01D18C-0x01E8A7, the aircraft's flight,
                         attack, turns, fall and burning, and their launch
src/player.c             the guns at an enemy aircraft (0x01B682), the countdown's launch
                         (0x01BC02), record_is_land (0x01CBB2)
src/tick.c               the airfields' launches (0x011622), the ships' launches with the Japanese
                         carrier's roll (0x011510), the ships sinking (0x011CAE, 0x011CD8)
src/core.c               a word stored to its original address: a wreck's word past the list
src/dialog.c             %s in RawDoFmt, for the sunk ship's name
src/records.def          the enemy aircraft record's fields
src/globals.def          fighters_up, wreck_count, wrecks, ship_shell, skid_count,
                         launch_cooldown, japcarrier_roll
tools/m6_autopilot.py    the autopilot the scripts were flown with: any map, the dogfight
tools/m6_scripts.py      the M6 scripts, and the enemy tick by tick while one runs
tools/m6_runs.py         the flown schedules (tools/m6_emit.py writes it)
tools/m6_observe.py      the maps' enemy content, and the writes of the enemy's records
tools/reach_observe.py   the reach map, with --m6 and --m6-only
tests/test_enemy.py      every M6 script in the closed loop, at three pass rates for two, and
                         in the attributed open loop; the completeness list; the capacities
                         on all fifteen maps; the register at ship_guns_draw
tests/test_oracle_m6.py  the shells, the ships' guns, the exclusive-or blit of japplane.shp;
                         every routine of the tick over random states, and the regions no
                         script runs reached by the cases
tests/m6_renders.py      pictures of the new scenes, dist/m6-part1/ and dist/m6-part2/
```

## What decides what is ported: the reach map

The M6 scripts are the twenty-five of `tools/m6_scripts.py` ("The scripts" below). The
reach map runs them beside every run of M4 and M5 and joins the two for the cold regions
(observed):

```text
.venv/bin/python tools/reach_observe.py --m5 --blocks --setups --jobs 12 --json REACH45.json
.venv/bin/python tools/reach_observe.py --m6-only --blocks --jobs 12 --json REACH6.json
.venv/bin/python tools/reach_observe.py --m6-only --load REACH6.json --markdown TABLE.md
.venv/bin/python tools/reach_observe.py --cold REACH45.json REACH6.json
```

### The cut between the parts (observed)

What the M6 scripts executed that no script of M4 or M5 did, by phase, over the joined runs:

- **Phase F (part 1):** `draw_enemy_aircraft`'s aircraft, their guns' flash, the wrecks'
  words and both of its scales; `ship_planes`'s deck aircraft, the Japanese carrier's clip
  and its draw of `MasterList` slot `0xF7`, and the eighth-scale view; `airfields_draw` whole; `ship_guns_draw` whole, with
  a routine no earlier script entered, `ship_gun_shell` (`0x014EFC`), which calls M5's
  `splash_spawn` and `torpedoes_hit` in the pass; `target_range_frame`'s eighth-scale branch
  (`0x014DCA`), whose only other caller takes that view itself; `window_strip`'s enemy
  aircraft and blocks of `window_shape` M4 ported from reading (an enemy ship in the 3-D
  view); `enemy_arrows` and `kill_icons` whole; `draw_dashboard`'s counter above 99; blocks
  of `object_draw` and `draw_objects` (the enemy's torpedo in the extra object record),
  `record_extras`, `ship_at_span`, `smoke_claim` and `map_slot_at`.
- **Phase V:** nothing new.
- **Phase M:** nothing new.
- **Phase T (part 2):** the whole enemy module `0x01D18C` to `0x01E8A7` (`aircraft_launch`,
  `enemy_aircraft_step` with every mode's flight, `aircraft_motion`, the turns, the falling
  and burning), the countdown's launch (`0x01BC66`), the airfields' and the ships' launches
  (`0x011630`, `0x0116D2`, `0x01152A`, `0x0115C4`, `0x0115F4`), the ships sinking
  (`0x011CD8`), the guns at an enemy aircraft (`0x01B6B0`), `record_is_land`, the crash on a
  ship with `flash_set`, and routines of the sound engine (`0x01EA28` to `0x01EB4C`, M8's)
  that the tick calls.

One routine the task put in part 1 is part 2's by phase: `flash_set` (`0x01CAB4`) runs in
the tick, from `crash`; its pass side, `flip_buffers`'s flash, is M5's and held.

## The scripts

Each is a raw schedule for the headless original, flown by a plan of
`tools/m6_autopilot.py` and kept in `tools/m6_runs.py`; `tools/m6_scripts.py trace NAME`
prints the player, the enemy plane counter, the carrier's hits, the ships' hits and every
enemy aircraft tick by tick. A plan names its map by the rank chosen in the rank selection
and the mission number poked at its end (`0x01009E`), as `tests/test_mission.py`'s setups
reach every map, because a campaign's next mission is M7's. The autopilot is M5's with M6's
parts laid over it: a plan's `countdown` leaves the button alone in turns so that the
enemy's countdown runs out; `wait` keeps the aircraft in the hold; `until` ends the legs on
a condition (the carrier's hits, a kill, the aircraft down, a torpedo dropped, a tick
count); an `end` of `land` brings it down onto the carrier; a leg's `dogfight` takes the
stick while an enemy aircraft of a kind is near (below).

| Script | Map | What it flies | Ticks |
|---|---|---|---|
| `kills_a` | a | the enemy plane counter poked to 120: 99 on the counter and fourteen kill icons | 343 |
| `wrecks_a` | a | three wrecks' words poked after the mission's reset of its tables (`0x0100D6`): over them low and high | 1,130 |
| `burning_a` | a | an enemy fighter shot down high over the island, poked into the first aircraft record after the mission's reset of its tables: it falls, rests on land, burns and leaves its wreck's word while the aircraft flies over the island and back | 982 |
| `oil_d` | d | back and forth over the airfield; its fighter takes off, gets on the aircraft's tail and fires until the oil is gone and the engine seizes | 946 |
| `night_d` | d | the same as a night mission (`night_flag` poked at the rank selection's end) | 946 |
| `airfield_e` | e | east past the airfield and back, then over it high in the eighth-scale view with its fighter following | 1,412 |
| `cruise_f` | f | over the cruise ship three times each way: its guns fire and shell, its aircraft goes up | 1,010 |
| `torpedo_f` | f | the torpedo (the menu one step down), dropped at 24 pixels east of the cruise ship: it runs into it and the ship sinks (+1,000) | 1,094 |
| `crash_f` | f | straight down onto the cruise ship's deck: the wreck at rest there (the player's state 8), a gun destroyed (+200) | 899 |
| `crash_side_f` | f | low into the cruise ship's hull: `flash_set(7, 0xF00)`, a gun destroyed (+200), into the sea | 917 |
| `rockets_f` | f | rockets (the menu one step up) in a dive at the cruise ship: a gun destroyed (+200), its smoke | 899 |
| `cruise_g` | g | out east over the cruise ship, then over it high | 1,235 |
| `destroyer_h` | h | out east over the destroyer | 1,183 |
| `ships_i` | i | west over the destroyer and on over the airfield | 1,086 |
| `battleship_j` | j | east over the battleship | 816 |
| `battleship_k` | k | west over the battleship | 1,122 |
| `destroyer_l` | l | east over the destroyer | 902 |
| `japcarrier_m` | m | east to the Japanese carrier: its deck aircraft, its aircraft readied and launched | 983 |
| `destroyer_n` | n | west over the destroyer | 1,236 |
| `japcarrier_o` | o | west high over the airfield (its aircraft rolling east), then to the Japanese carrier at the map's west end | 1,386 |
| `countdown_b` | b | the countdown's torpedo plane until it has dropped its torpedo; the arrow | 2,181 |
| `countdown_c` | c | the same on map c | 2,063 |
| `enemy_a` | a | the countdown's torpedo plane hits the carrier (4 to 3); then the landing on it | 2,606 |
| `fight_a` | a | the guns at the countdown's torpedo planes until one is shot down (+350, the kill counter 1) | 8,996 |
| `sunk_a` | a | the aircraft waits in the hold while three torpedoes hit the carrier, flies, and the fourth sinks it; the landing on the sunken deck and the game's end | 6,420 |

The ship scripts end when the aircraft is brought down, which the fighters of a ship or an
airfield do within a pass or two over their ship. The last five run only with `--slow`
(`tools/m6_scripts.py`, `SLOW`); `sunk_a` stops at VBlank 26,400, 600 after its mission
ends, because its schedule holds the autopilot's wait in the front end after the game's end.
Every script replays as flown (observed: the open loop of `tests/test_enemy.py` records each
under the headless original, and the counters above are those of its trace).

### The dogfight

The guns bring an enemy aircraft down after nineteen bursts of hits, and every hit starts
its evasion, a turn 8 to 13 ticks later (`re/notes/enemy.md`, "Shot down"). The
autopilot's `dogfight` action: follow one aircraft of the kinds the action names; behind it
the same way, hold the button through the whole close chase (the guns fire only after ten
VBlanks held, and a shorter press would drop the other weapon), follow its height with
pushes of the stick that always carry the direction (forward alone while flying left is
the stall, `0x025AAA`), and leave the stick level otherwise, because the guns hit only
while the pitch target is 0; coming the other way, turn above 130 pixels (a turn dives)
when it is within 250 pixels head on or behind. A chased torpedo plane keeps about 150
pixels ahead by itself, inside the guns' reach; so `fight_a` fights the countdown's
torpedo planes east of map a's carrier and takes one down after some 3,000 ticks of passes.

What no script reaches by play after a bounded attempt: **an enemy aircraft shot down over
land**, its burning (state `0x10`) and the wreck it leaves. `fight_a`'s kill falls east of
map a's end, where the aircraft is freed at once. The plan `fight_island_a` flew the same
dogfight over map a's island (32 to 3944) for 9,000 ticks: the dug-outs' fire takes the oil
during the low chase, and every aircraft came down burning on land before a kill. Against
the airfields' fighters, seven plans flew the dogfight with the mask of a fighter's modes:
`fight_e`, `fight_e_low` and `fight_e_wide` for 9,000 ticks and `fight_e_70` and
`fight_e_wide70` for 15,000 over map e's land east of its airfield (16024 to 17040, no
target on it) and over the airfield's island, and `fight_d` and `fight_d_70` over map d's
airfield between its dug-out and its pillboxes. None brought a fighter down: a fighter hit
turns away 8 to 13 ticks later, it jinks down to 35 pixels over land, where a chase that
follows it flies into the ground, and on the aircraft's tail it takes the oil; a floor of
70 pixels under the chase kept the aircraft flying but out of the guns' reach of height.
The fall on land, the burning and the wreck's word are reached with the poke of
`burning_a`, as `wrecks_a` reached the wrecks' drawing and M5 the balloons.

## The pass: what part 1 ports

- **The enemy aircraft** (`draw_enemy_aircraft`, `0x010DA6`): first the wrecks, each word of
  `0x0251DA` up to `0x0251D8`'s count at its x (negated when it faced west) and `view_y`
  less 4, with frame 27 or 55 of the frame table (`0x026F8E`, or `0x02706E` in the
  eighth-scale view); the list is read by address, so a forty-first word would come from the
  aircraft records behind it. Then every aircraft in use at its x and height with its frame
  `+0x30`; one that fires counts `+0x2C` up in the pass and on its odd counts draws its
  guns' flash, `japplane_shapes` `0x10` or `0x11`, two further on facing west, with the
  exclusive-or blit. Everything is shifted down by three in the eighth-scale view, and
  dropped outside -128 to 448.
- **The aircraft on the ships' decks** (`ship_planes`, `0x01391E`): each ship afloat of
  `ship_order`, the drawing's copy of its block of deck aircraft (`0x024F38`, the ship at
  the same place 0x40 bytes on), an entry set drawn at its x and height less the ship's row
  and the swell, facing by its `+0x06`; the Japanese carrier, last of the order, clips its
  aircraft at its waterline, and after the walk, with aircraft on its block at full scale,
  `MasterList` slot `0xF7` is drawn `0x199` east of its first map offset and `0x15` above
  the row the walk left, without a hotspot, under the caller's clip. The slot is the
  Japanese carrier's thirteenth name, `cmsk`, which `japcarrier.shp` does not hold, so
  `shapes_resolve` leaves it 0 and the call draws nothing (observed: all 82 calls in
  `japcarrier_m` and all 480 in `japcarrier_o` hand `shape_draw` a null shape); the port
  makes the same call.
- **The airfields** (`airfields_draw`, `0x013A18`): the parked aircraft in a row from the
  end they take off from, `0x40` apart, on the sea's row, and the one rolling at its x.
- **The ships' guns** (`ship_guns_draw`, `0x014C3E`) as `re/notes/enemy.md` says: the
  shells (`ship_gun_shell`, `0x014EFC`), the frame, the fire, the smoke of a destroyed gun.
- **The 3-D view** (`window_strip`, `0x014206`): an aircraft whose drawing's map offset
  lies in a row's span is drawn on the row at x `0x13F`, the window's middle (the window spans
  columns 256 to 399; chapter 16 of the book found the earlier "right edge" wrong), `dash_frames` by its
  frame turned to the player's facing and the row's set added as a byte, a quarter of its
  height above the row.
- **The arrows** (`enemy_arrows`, `0x01F21A`) and **the enemy plane counter**: at most 99,
  its kill icons seven a row in two rows (`kill_icons`, `0x01F200`).
- **The islands** (`islands_draw`, `0x0140E8`): the two lists are read by address; no map
  has more than four islands.

## Registers that cross a call

- **D1's upper word in `ship_guns_draw`.** A destroyed gun's smoke is claimed with the y long
  `(deck - row) << 16 | (D1's upper word + 0x0D)`: the swap comes before the add, so the
  deck is the whole part and the old upper word the fraction; after the claim D1's upper word
  is the deck less the row, or `0x10` when `smoke_claim` raised a lower height. D1's upper
  word is 0 at every entry of the routine in the ship scripts (observed: 1,805 entries in
  `rockets_f`, and
  `tests/test_enemy.py::test_the_ship_guns_find_d1_and_d2_clear_at_their_entry` over four
  ship scripts), and D2's too; it is what the targets' walks before it left, which a
  dug-out refilled or a pillbox's smoke in the same pass changes (`re/notes/porting-m5.md`,
  "Registers that cross a call"), and the port takes it from `wof_targets_f_draw`.
- **`target_fire`'s exchange.** When the distance is no more than the height it exchanges
  the two longs, so the smoke at the engine takes the caller's D1 upper word as its x
  fraction instead of D2's. From the targets' draws that is D1's upper word as the walks
  before left it (0 but after a refill or a pillbox's smoke, M5) and `rand_beam`'s constant; from the ships' guns D1's upper word as above (observed: 18 of `rockets_f`'s entries
  from `ship_guns_draw` came with `0x1C`, after a destroyed gun's smoke) and 0. The port
  hands both upper words to `wof_target_fire`.
- **D7 into `ship_guns_draw`** is `draw_world`'s table, `MasterList` or `AthList`, which the
  routines between leave alone (read); the port passes it.
- **D6 into `ship_planes`** is `draw_world`'s swell (`0x026E56`) when no ship is afloat,
  and the draw of slot `0xF7` takes the row of the last ship afloat (read; the port passes
  it).

## The tick: what part 2 ports

- **The enemy aircraft** (`enemy_aircraft_step`, `0x01E7D6`, and the module of compiled C
  behind it, `src/enemy.c`): every record's relation and order, its flight by its mode (a
  fighter cruising or on the tail, a torpedo plane before and after its drop), the turns,
  the speed, the motion and the frame, the fall of one shot down and the burning of one at
  rest on land, as `re/notes/enemy.md` says. The compiler kept `int` 16 bits wide: where a
  `muls.w` product is sign-extended again with `ext.l` before a `divs.w` (the timing of a
  turn by the distance times 100), only its low word divides, and the port says so there.
  The height's steps are the words of `climb_steps` (`0x0261F8`) by the twentieths of the
  distance to the wanted height, the speeds' limits the DATA words `0x025F52` (900) and
  `0x025F54` (`0xA28`), which nothing writes and which are registered
  (`aircraft_speed_min`, `aircraft_speed_max`, with the unread word after them, which keeps
  the globals' struct free of padding beside `japcarrier_roll`), and x moves by mathffp
  (`aircraft_motion`, `re/notes/ffp.md`).
- **The guns at an enemy aircraft** (`0x01B682`): by the relation alone, whatever the
  state, as the original walks them.
- **The countdown's launch** (`0x01BC02`): the torpedo plane `0x1800` away on the side of
  the deck the player is on, a draw of `rand_beam` over the deck.
- **The airfields** (`0x011622`), **the ships' launches** with the Japanese carrier's
  aircraft readied and rolling (`0x011510`, `japcarrier_roll` registered), and **the
  sinking** (`0x011CAE`, `0x011CD8`) with the ticker's message of a ship sunk (`0x015640`,
  a `%s` and a `%ld`, which the port's RawDoFmt now takes).
- **A wreck's word** goes to `0x0251DA` plus twice the count whatever the count is. The
  port stores it by that address (`wof_original_store16`, `src/core.c`) into whichever
  registered global or table at a fixed address covers it, byte by byte and big-endian as
  the original's memory holds it, so a forty-first word lands in the aircraft records as
  the original's does (the oracle's cases have lists of 45, 150, 190 and 300 words).
- **The sounds** the tick starts from these routines are the sound engine's (`0x01EA28` to
  `0x01EB4C`, M8's). M6 leaves the calls out with a comment naming them, as M4 and M5
  do for the engine's slots; M8 ports the engine and calls them (`re/notes/porting-m8.md`).
  A stand-in marker there would be reached in almost every tick of every script, and a
  reached stand-in fails every differential test (`SPEC.md` section 7.4).

## Flags that decide in the tick

- **The carrier or an enemy ship.** In `ship_sinking` the `beq` after the row's step reads
  the flags of the `move.w` of the ship's score, which comes between it and the `cmpi.w #1`
  of the rows: a score of 0, the carrier's, takes the carrier's path at every row (read; the
  oracle's cases include both).
- **The last ship.** `subq.b #1` of `ships_left` and then `bgt` compare the true result, so
  from `0x80` the byte becomes `0x7F` with the overflow flag set and the branch is not
  taken: the mission is won although 127 ships are left. The port tests the byte before the
  decrement, as signed, against 1 (found by the oracle's case 508 of the sinking; no map has
  more than three enemy ships, map o).
- **A dead floor.** `aircraft_speed`'s floor at 900 when an aircraft slows (`0x01E71A`) is
  never reached: slowing towards a want speed of at least 900 lands half the gap and 5 above
  it (read).

## How the port is held to the original

| Check | Test | What it covers |
|---|---|---|
| T2 | `tests/test_enemy.py::test_every_tick_and_pass_agrees_in_the_closed_loop[...]` | every M6 script in the closed loop, from the program's start with nothing handed over but the entropy and the map list's address: after every tick and every pass the registered state, the drawing calls, the entropy with its callers, the view, the palette of every row, the markers and the map draws agree, and no stand-in is reached (the five long scripts with `--slow`) |
| T2 at 1 and 3 | `test_the_closed_loop_holds_at_other_pass_rates[1, 3][torpedo_f, enemy_a]` (slow) | the closed loop at one and three VBlanks per pass against the original run at the same rate |
| T1, attributed | `test_every_pass_agrees_and_every_other_difference_is_owed[...]` | the open loop over every M6 script: a step that differs must have reached a stand-in of M7 or M8 in that same step, and no step may reach another (none differs) |
| T3 | `test_every_address_the_m6_scripts_write_is_compared_or_excluded` | the completeness list over the M6 scripts, below |
| capacities | `test_the_tables_the_pass_walks_hold_every_map` | the islands' lists, the gun lists and the blocks of deck aircraft on all fifteen maps at step S |
| register | `test_the_ship_guns_find_d1_and_d2_clear_at_their_entry` | the upper words `ship_guns_draw` finds, over four ship scripts |
| V6 | `tests/test_oracle_m6.py` | `ship_gun_shell` over 2,000 states and `ship_guns_draw` over 1,500 (four ships afloat or sunk, sixteen guns each standing or smoking, torpedoes near, both views, the aircraft on the deck; the original's `shape_draw` returns at once and the drawing is the open loop's), touched memory compared |
| V5 | `tests/test_oracle_m6.py::test_the_exclusive_or_blit_of_the_enemy_guns_matches_the_blitter` | `shape_draw_xor` for every shape of `japplane.shp` on the playfield, against the blitter model |
| V6, part 2 | `tests/test_oracle_m6.py` | every routine of the enemy module that takes a record, over 1,200 states each (every state, mode and relation, level and turning, hit and not, falling over the sea, on land and on a ship, burning, the wrecks' list short and past forty words); `aircraft_order` over 2,000 tables; `enemy_aircraft_step` over 3,000; `aircraft_launch` over 2,000; the guns at an enemy aircraft, the countdown with its launch, the airfields, the ships' launches and the sinking with the ticker's message and the mission won, over 2,000 each; `rand_beam` served on both sides from the port's stream, touched memory compared, and every region no script runs executed by the cases (`COLD`) |
| T1, T2 | `tests/test_world.py`, `tests/test_weapons.py` | every M4 and M5 script in both loops, unchanged |
| T7 | `tests/test_page.py`, `tests/test_firefox.py`: `test_an_enemy_aircraft_comes_up_on_the_page`, `..._in_a_visible_window` | on the page, in Chrome, Firefox and a visible Firefox window: the second rank's first mission, map d, flown from the keyboard from the hold to the airfield; the fighter it sends up found in the framebuffer by its frame's pixels, and none in the sky taken on the way (below) |

The controls of the pass (part 1), each run by changing the port, rebuilding and running
the open loop of one script with its attribution, then reverting; every one leaves steps
that differ without a later stand-in reached:

| Control | Script | Steps not owed | The first |
|---|---|---|---|
| the enemy guns' flash one frame on (`0x11` for `0x10`, `src/world.c`) | `oil_d` | 43 | pass 1405: the flash's exclusive-or draw with another shape of `japplane_shapes`, a pixel higher |
| a destroyed gun's smoke fraction `+ 0x0C` for `+ 0x0D` | `rockets_f` | 39 | pass 1061: `smoke_records[9].y` `0x1DF0BC` for `0x1DF0BD` |
| an airfield's parked aircraft `0x20` apart for `0x40` | `oil_d` | 1,090 | pass 1: the second parked aircraft 32 pixels east |
| a deck aircraft facing east in the eighth-scale view with frame `0xA4` for `0xA3` | `cruise_g` | 114 | pass 1977: the other shape of `eighth_shapes`, a pixel higher |
| a shell's splash a pixel east (`- 0x1F` for `- 0x20`) | `cruise_f` | 301 | pass 971: the splash drawn at 117 for 116, and `splash_records[0].x` one more |
| the kill icons 12 apart for 13 (`src/dash.c`) | `kills_a` | 2 | pass 1: the second icon at 546 for 547 |
| an enemy aircraft in the 3-D view turned with `0x1B` for `0x1C` | `oil_d` | 162 | pass 1351: the aircraft's `dash_frames` entry one lower |

In `kills_a` the kill icons are drawn in the mission's first two passes only, as the
counter does not change after them; the other controls fail wherever their part is drawn.

The controls of the tick, each run by changing the port, rebuilding and running the closed
loop of one script, then reverting; the closed loop catches every one, and the first step
where it shows is the tick named:

| Control | Script | The first |
|---|---|---|
| the countdown after a torpedo plane's drop 501 for 500 (`src/enemy.c`) | `countdown_b` | tick 2021: `player[0].enemy_countdown` `0x1F5` for `0x1F4` |
| the health a burst of the guns takes 7 for 8 (`src/player.c`) | `fight_a` | tick 2143: `aircraft_records[3].health` `0xE9` for `0xE8` |
| a torpedo plane's evasion 9 to 14 ticks for 8 to 13 | `fight_a` | tick 2138: `aircraft_records[3].turn_in` 9 for 8 |
| the sinking's interval not shortened (`src/tick.c`) | `torpedo_f` | tick 620: `ship_records[2].w18` `0x14` for `0x13` |
| the countdown's launch `0x1801` away for `0x1800` | `countdown_b` | tick 1353: the torpedo plane's x `0x34A5` for `0x34A4` |
| an airfield's roll at most `0x37` for `0x38` | `oil_d` | tick 602: `airfield_records[0]` x and speed; the fighter then takes off later, the aircraft is not brought down, and the port runs on past the recording's end |
| the Japanese carrier's roll 9 more a tick for 8 | `japcarrier_m` | tick 731: `japcarrier_roll` 9 for 8 |

### The page

An enemy aircraft is within a minute of the page's keyboard flight: in the second rank's
first mission, map d, the airfield 3,500 pixels west of the carrier sends its fighter up
when the aircraft comes within `0x1E0` of it. `tests/pagemeasure.mjs` (`enemyFlight`)
flies there from the hold in a session of its own in Chrome and in a Firefox tab, the
visible window included: the lift, the roll for 115 ticks as the scripts roll, the climb to
120 before the turn (a turn dives), west to the island and back and forth over the airfield
for half a minute, the height kept between 70 and 170. The sky, the top 150 rows of the
framebuffer, is taken five times on the way out of the airfield's reach and every 400 ms
over the island. The pytest side (`tests/conftest.py`, `enemy_templates`) looks in each for
one of the 56 frames an enemy aircraft flies with: the shapes of `japplane.shp` by the
names `enemy_frames` reads (`0x025F58`), each pixel doubled across the low-resolution
playfield, in the colours of map d's sky as the port's own closed loop of `oil_d` shows
them, every opaque pixel at one place. Colour alone does not tell it: over 2,488 passes of
four scripts no colour of the sky appeared with an enemy in view and never without, because
the targets' bursts round the aircraft and the ships' and the carrier's paint share the
fighter's. The frames' pixels matched in none of the 1,945 passes of `oil_d`,
`airfield_e`, `cruise_f` and `torpedo_f` in which the port drew no enemy aircraft on the
screen, and in 154 of the 341 in which it drew one; in the others smoke, the guns' flash or
the picture's edge covers part of it (observed with the native library, the port's own
drawing calls taken for what is on the screen). The aircraft parked on an airfield or a
deck are other shapes, which the search leaves out. The
first run found the fighter in 13 of 48 looks over the island, climbing after its take-off,
and in none of the five on the way.

## The completeness list

`test_every_address_the_m6_scripts_write_is_compared_or_excluded` takes the rows of M4 and
M5 and adds these (`tests/m4complete.py`, `M6_EXCLUDED` and `M6_HEAP`), the mission setup
on the maps with ships; none is owed to M6:

| Address | Writers | What it is | How the port carries it | Owed to |
|---|---|---|---|---|
| `0x0256A2` | `shapes_load` | `shapes_load_name`, the file name for the loader's error text | every container is loaded at start-up (`src/assets.c`) | M1 |
| `0x026F34`-`0x026F53` | `load_ship_shapes` | the four ships' containers and their tables of record pointers | the containers are held from start-up and `ship_loaded` says which ships the mission loaded; the tables fill `MasterList` from slot `0xB8` on, which is registered and compared | M4 |
| heap, allocated by `shapes_resolve` | `shapes_resolve` | a ship's table of record pointers (24, 27, 13 or 25 of them) | the names are resolved into shape handles at start-up (`src/shapes.c`); `MasterList` as above | M4 |

What the tick writes is registered: `japcarrier_roll` (`0x02734A`) joins `launch_cooldown`
(`0x027348`) and the tables of the aircraft records, the airfields, the ship blocks and the
ships; the sound engine's slots and channels the tick's routines start are M4's rows owed to
M8, and `g_027df0`, the record pointer of the guns' walk, is M4's row too. Everything else
the twenty-five scripts write is a registered field or one of those rows (observed, the
test with `--slow`).

## What stands in, and where

No stand-in of M6 is left, of either part, and no value marker of M6 either (the cold list
below, observed). What the twenty-five scripts do not run of the ported routines is ported
from reading and named in the cold list with the oracle test whose cases reach it: the
rarer turns and hits of the enemy's flight, a torpedo plane already up at a launch, the
states 1 and 8 that nothing sets, a wreck facing east, the carrier sinking with the player
aboard or on its deck, and the mission won by the last enemy ship sunk; the oracle tests
assert that their cases execute every one of these regions of the original
(`tests/test_oracle_m6.py`, `COLD`). Two regions are data, the jump tables of two switches,
and one is dead, `aircraft_speed`'s floor at 900 (above, "Flags that decide in the tick").
The markers left in the sources are M7's (a campaign's next mission, which M7 part 1 ports,
and a loaded game, a demo, a negative score and a ticker message outside the registered
state, M7 part 2's) and M5's value marker for the soldiers' table. The sound engine's routines the tick calls (`0x01EA28` to `0x01EB4C`)
are M8's: left out with a comment and excluded in the completeness list, without a marker,
as M4 and M5 leave the engine's slots ("The tick: what part 2 ports"). M8 ports them and
the rows are gone (`re/notes/porting-m8.md`).

## Appendix: the reach map

Entries per routine and phase during an M6 script's mission, for the twenty-five scripts,
written from the run above (observed) with

```text
.venv/bin/python tools/reach_observe.py --m6-only --load REACH6.json --markdown TABLE.md
```

The windows before the mission are M4's, which the scripts of maps d to o reach through the
rank selection as the setups do (re/notes/porting-m4.md, "Appendix: the reach map").

### The head of the outer loop, before the rank selection

| Routine | Address | `kills_a` | `wrecks_a` | `burning_a` | `oil_d` | `night_d` | `airfield_e` | `cruise_f` | `torpedo_f` | `crash_f` | `crash_side_f` | `rockets_f` | `cruise_g` | `destroyer_h` | `ships_i` | `battleship_j` | `battleship_k` | `destroyer_l` | `japcarrier_m` | `destroyer_n` | `japcarrier_o` | `countdown_b` | `countdown_c` | `enemy_a` | `fight_a` | `sunk_a` |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| `free_mission_assets` | `011234` | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 |
| `mem_free_var` | `0124e0` | 16 | 16 | 16 | 16 | 16 | 16 | 16 | 16 | 16 | 16 | 16 | 16 | 16 | 16 | 16 | 16 | 16 | 16 | 16 | 16 | 16 | 16 | 16 | 16 | 16 |
| `shapes_free` | `012502` | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 |
| `free_map` | `012bbe` | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 |
| `sub_01346c` | `01346c` | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 |
| `sub_0134a4` | `0134a4` | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 |
| `sub_0134ae` | `0134ae` | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 |
| `campaign_reset` | `013562` | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 |
| `mission_reset_tables` | `0135a8` | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 |
| `player_lost_restart` | `0135d8` | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 |
| `player_restart_state` | `013684` | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 |
| `sub_013756` | `013756` | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 |
| `shape_mirror_x` | `015b58` | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 |
| `aircraft_frame` | `01abde` | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 |
| `deck_span` | `01b7bc` | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 |
| `player_reset` | `01b7ec` | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 |
| `sub_01b9bc` | `01b9bc` | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 |
| `rand_mod` | `01cac8` | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 |
| `sub_01cb30` | `01cb30` | 4 | 4 | 4 | 4 | 4 | 4 | 4 | 4 | 4 | 4 | 4 | 4 | 4 | 4 | 4 | 4 | 4 | 4 | 4 | 4 | 4 | 4 | 4 | 4 | 4 |
| `aircraft_clear` | `01e608` | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 |
| `weapon_gauge_reset` | `01edbc` | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 |
| `lives_gauge_reset` | `01edea` | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 |
| `rand_beam` | `0203be` | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 |
| `shape_find_c` | `0204f4` | 4 | 4 | 4 | 4 | 4 | 4 | 4 | 4 | 4 | 4 | 4 | 4 | 4 | 4 | 4 | 4 | 4 | 4 | 4 | 4 | 4 | 4 | 4 | 4 | 4 |
| `shape_find` | `020560` | 4 | 4 | 4 | 4 | 4 | 4 | 4 | 4 | 4 | 4 | 4 | 4 | 4 | 4 | 4 | 4 | 4 | 4 | 4 | 4 | 4 | 4 | 4 | 4 | 4 |

### After the rank selection, before the briefing

| Routine | Address | `kills_a` | `wrecks_a` | `burning_a` | `oil_d` | `night_d` | `airfield_e` | `cruise_f` | `torpedo_f` | `crash_f` | `crash_side_f` | `rockets_f` | `cruise_g` | `destroyer_h` | `ships_i` | `battleship_j` | `battleship_k` | `destroyer_l` | `japcarrier_m` | `destroyer_n` | `japcarrier_o` | `countdown_b` | `countdown_c` | `enemy_a` | `fight_a` | `sunk_a` |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| `ship_block` | `01252c` | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 2 | 2 | 1 | 2 | 2 | 2 | 3 | 0 | 0 | 0 | 0 | 0 |
| `sub_0129c8` | `0129c8` | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 |
| `map_load` | `012adc` | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 |
| `airfields_scan` | `012c84` | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 |
| `map_scan` | `012d5a` | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 |
| `sub_0131c8` | `0131c8` | 2 | 2 | 2 | 6 | 6 | 9 | 6 | 6 | 6 | 6 | 6 | 9 | 9 | 9 | 0 | 8 | 6 | 13 | 9 | 9 | 5 | 7 | 2 | 2 | 2 |
| `sub_013216` | `013216` | 2 | 2 | 2 | 6 | 6 | 9 | 6 | 6 | 6 | 6 | 6 | 8 | 9 | 9 | 0 | 10 | 7 | 14 | 11 | 11 | 5 | 7 | 2 | 2 | 2 |
| `sub_013236` | `013236` | 0 | 0 | 0 | 4 | 4 | 6 | 6 | 6 | 6 | 6 | 6 | 10 | 8 | 12 | 0 | 16 | 14 | 24 | 24 | 30 | 0 | 4 | 0 | 0 | 0 |
| `airfields_clear` | `013554` | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 |
| `mem_alloc_asm` | `0158ec` | 5 | 5 | 5 | 6 | 6 | 6 | 6 | 6 | 6 | 6 | 6 | 6 | 6 | 6 | 2 | 6 | 6 | 6 | 6 | 6 | 5 | 6 | 5 | 5 | 5 |
| `shapes_load` | `015bc6` | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 |
| `shapes_resolve` | `015c5c` | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 |
| `load_file_public_asm` | `015d3e` | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 |
| `load_file_chip_asm` | `015d50` | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 |
| `load_dash_assets` | `01653c` | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 |
| `sub_0165c4` | `0165c4` | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 |
| `load_file_public` | `01feb4` | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 |
| `load_file_chip` | `01feca` | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 |
| `load_file` | `01ff16` | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 |
| `shape_find` | `020560` | 117 | 117 | 117 | 117 | 117 | 117 | 117 | 117 | 117 | 117 | 117 | 117 | 117 | 117 | 117 | 117 | 117 | 117 | 117 | 117 | 117 | 117 | 117 | 117 | 117 |
| `mem_alloc` | `020848` | 7 | 7 | 7 | 8 | 8 | 8 | 8 | 8 | 8 | 8 | 8 | 8 | 8 | 8 | 4 | 8 | 8 | 8 | 8 | 8 | 7 | 8 | 7 | 7 | 7 |
| `sub_020874` | `020874` | 9 | 9 | 9 | 10 | 10 | 10 | 10 | 10 | 10 | 10 | 10 | 10 | 10 | 10 | 6 | 10 | 10 | 10 | 10 | 10 | 9 | 10 | 9 | 9 | 9 |
| `mem_free` | `02090a` | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 |
| `os_dos_close` | `022aae` | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 |
| `sub_022ab2` | `022ab2` | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 |
| `os_dos_examine` | `022ada` | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 |
| `os_dos_lock` | `022b1a` | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 |
| `os_dos_open` | `022b2c` | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 |
| `sub_022b30` | `022b30` | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 |
| `os_dos_read` | `022b3e` | 4 | 4 | 4 | 4 | 4 | 4 | 4 | 4 | 4 | 4 | 4 | 4 | 4 | 4 | 4 | 4 | 4 | 4 | 4 | 4 | 4 | 4 | 4 | 4 | 4 |
| `os_dos_unlock` | `022b50` | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 |
| `sub_022d36` | `022d36` | 9 | 9 | 9 | 10 | 10 | 10 | 10 | 10 | 10 | 10 | 10 | 10 | 10 | 10 | 6 | 10 | 10 | 10 | 10 | 10 | 9 | 10 | 9 | 9 | 9 |
| `sub_022d3a` | `022d3a` | 9 | 9 | 9 | 10 | 10 | 10 | 10 | 10 | 10 | 10 | 10 | 10 | 10 | 10 | 6 | 10 | 10 | 10 | 10 | 10 | 9 | 10 | 9 | 9 | 9 |
| `sub_022d86` | `022d86` | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 |
| `sub_022d8a` | `022d8a` | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 |

### Mission setup, main program: the briefing's end to step S

| Routine | Address | `kills_a` | `wrecks_a` | `burning_a` | `oil_d` | `night_d` | `airfield_e` | `cruise_f` | `torpedo_f` | `crash_f` | `crash_side_f` | `rockets_f` | `cruise_g` | `destroyer_h` | `ships_i` | `battleship_j` | `battleship_k` | `destroyer_l` | `japcarrier_m` | `destroyer_n` | `japcarrier_o` | `countdown_b` | `countdown_c` | `enemy_a` | `fight_a` | `sunk_a` |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| `input_queue_clear` | `01174a` | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 |
| `sub_011f76` | `011f76` | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 |
| `load_ship_shapes` | `013252` | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 |
| `sounds_load` | `013368` | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 |
| `ship_guns_setup` | `01350e` | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 2 | 2 | 1 | 2 | 2 | 2 | 3 | 0 | 0 | 0 | 0 | 0 |
| `mission_reset_tables` | `0135a8` | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 |
| `player_lost_restart` | `0135d8` | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 |
| `player_restart_state` | `013684` | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 |
| `sub_013756` | `013756` | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 |
| `build_master_lists` | `01535a` | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 |
| `mem_alloc_asm` | `0158ec` | 0 | 0 | 0 | 0 | 0 | 0 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 4 | 4 | 2 | 4 | 4 | 4 | 6 | 0 | 0 | 0 | 0 | 0 |
| `file_length` | `015b1a` | 8 | 8 | 8 | 8 | 8 | 8 | 8 | 8 | 8 | 8 | 8 | 8 | 8 | 8 | 8 | 8 | 8 | 8 | 8 | 8 | 8 | 8 | 8 | 8 | 8 |
| `shapes_load` | `015bc6` | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 2 | 2 | 1 | 2 | 2 | 2 | 3 | 0 | 0 | 0 | 0 | 0 |
| `shapes_resolve` | `015c5c` | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 2 | 2 | 1 | 2 | 2 | 2 | 3 | 0 | 0 | 0 | 0 | 0 |
| `load_file_public_asm` | `015d3e` | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 |
| `load_file_chip_asm` | `015d50` | 8 | 8 | 8 | 8 | 8 | 8 | 9 | 9 | 9 | 9 | 9 | 9 | 9 | 10 | 10 | 9 | 10 | 10 | 10 | 11 | 8 | 8 | 8 | 8 | 8 |
| `vport_init_bitmap` | `0167f2` | 4 | 4 | 4 | 4 | 4 | 4 | 4 | 4 | 4 | 4 | 4 | 4 | 4 | 4 | 4 | 4 | 4 | 4 | 4 | 4 | 4 | 4 | 4 | 4 | 4 |
| `view_layout` | `01692c` | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 |
| `ticker_vport_init` | `016bd8` | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 |
| `view_set_game` | `016c38` | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 |
| `screen_game` | `016cc6` | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 |
| `cmap_file_to_table` | `016dd6` | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 |
| `cop_add_ticker_ramp` | `0187ba` | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 |
| `mission_display_setup` | `018806` | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 |
| `cop_reset` | `019958` | 6 | 6 | 6 | 6 | 6 | 6 | 6 | 6 | 6 | 6 | 6 | 6 | 6 | 6 | 6 | 6 | 6 | 6 | 6 | 6 | 6 | 6 | 6 | 6 | 6 |
| `cop_move` | `0199bc` | 290 | 290 | 290 | 290 | 296 | 290 | 290 | 290 | 290 | 290 | 290 | 290 | 290 | 290 | 290 | 290 | 290 | 290 | 290 | 290 | 290 | 290 | 290 | 290 | 290 |
| `cop_move_ptr` | `019a08` | 96 | 96 | 96 | 96 | 96 | 96 | 96 | 96 | 96 | 96 | 96 | 96 | 96 | 96 | 96 | 96 | 96 | 96 | 96 | 96 | 96 | 96 | 96 | 96 | 96 |
| `cop_wait` | `019a9c` | 78 | 78 | 78 | 78 | 78 | 78 | 78 | 78 | 78 | 78 | 78 | 78 | 78 | 78 | 78 | 78 | 78 | 78 | 78 | 78 | 78 | 78 | 78 | 78 | 78 |
| `cop_colours` | `019b5a` | 14 | 14 | 14 | 14 | 14 | 14 | 14 | 14 | 14 | 14 | 14 | 14 | 14 | 14 | 14 | 14 | 14 | 14 | 14 | 14 | 14 | 14 | 14 | 14 | 14 |
| `cop_vport_colours` | `019c0a` | 14 | 14 | 14 | 14 | 14 | 14 | 14 | 14 | 14 | 14 | 14 | 14 | 14 | 14 | 14 | 14 | 14 | 14 | 14 | 14 | 14 | 14 | 14 | 14 | 14 |
| `cop_vport_split` | `019c80` | 4 | 4 | 4 | 4 | 4 | 4 | 4 | 4 | 4 | 4 | 4 | 4 | 4 | 4 | 4 | 4 | 4 | 4 | 4 | 4 | 4 | 4 | 4 | 4 | 4 |
| `cop_vport_planes` | `019d18` | 14 | 14 | 14 | 14 | 14 | 14 | 14 | 14 | 14 | 14 | 14 | 14 | 14 | 14 | 14 | 14 | 14 | 14 | 14 | 14 | 14 | 14 | 14 | 14 | 14 |
| `cop_sprites_off` | `01a06c` | 6 | 6 | 6 | 6 | 6 | 6 | 6 | 6 | 6 | 6 | 6 | 6 | 6 | 6 | 6 | 6 | 6 | 6 | 6 | 6 | 6 | 6 | 6 | 6 | 6 |
| `view_build_copper` | `01a0d4` | 6 | 6 | 6 | 6 | 6 | 6 | 6 | 6 | 6 | 6 | 6 | 6 | 6 | 6 | 6 | 6 | 6 | 6 | 6 | 6 | 6 | 6 | 6 | 6 | 6 |
| `iff_cmap_to_table` | `01a1f6` | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 |
| `iff_next_chunk` | `01a336` | 8 | 8 | 8 | 8 | 8 | 8 | 8 | 8 | 8 | 8 | 8 | 8 | 8 | 8 | 8 | 8 | 8 | 8 | 8 | 8 | 8 | 8 | 8 | 8 | 8 |
| `iff_body_to_vport` | `01a362` | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 |
| `iff_parse_ilbm` | `01a452` | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 |
| `iff_to_vport` | `01a548` | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 |
| `view_poke_colours1` | `01a60e` | 3 | 3 | 3 | 3 | 3 | 3 | 3 | 3 | 3 | 3 | 3 | 3 | 3 | 3 | 3 | 3 | 3 | 3 | 3 | 3 | 3 | 3 | 3 | 3 | 3 |
| `view_poke_colours2` | `01a6ac` | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 |
| `vport_clear_planes` | `01a74c` | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 |
| `view_copy_bitmaps` | `01a834` | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 |
| `view_copy_colours` | `01a8c4` | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 |
| `view_copy` | `01a9ca` | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 |
| `cop_show_wait` | `01a9fc` | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 |
| `cop_install` | `01aa0e` | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 |
| `wait_vblank` | `01aa3e` | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 |
| `aircraft_frame` | `01abde` | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 |
| `deck_span` | `01b7bc` | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 |
| `player_reset` | `01b7ec` | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 |
| `sub_01b9bc` | `01b9bc` | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 |
| `rand_mod` | `01cac8` | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 |
| `sub_01cb30` | `01cb30` | 288 | 288 | 288 | 288 | 288 | 288 | 288 | 288 | 288 | 288 | 288 | 288 | 288 | 288 | 288 | 288 | 288 | 288 | 288 | 288 | 288 | 288 | 288 | 288 | 288 |
| `enemy_frames` | `01d1ea` | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 |
| `dash_cache_invalidate` | `01ed7a` | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 |
| `dashboard_invalidate` | `01edaa` | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 |
| `weapon_gauge_reset` | `01edbc` | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 |
| `load_file_public` | `01feb4` | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 |
| `load_file_chip` | `01feca` | 8 | 8 | 8 | 8 | 8 | 8 | 9 | 9 | 9 | 9 | 9 | 9 | 9 | 10 | 10 | 9 | 10 | 10 | 10 | 11 | 8 | 8 | 8 | 8 | 8 |
| `rpck_unpack` | `01fee0` | 1 | 1 | 1 | 1 | 0 | 1 | 2 | 2 | 2 | 2 | 2 | 2 | 1 | 2 | 1 | 1 | 1 | 2 | 1 | 2 | 1 | 1 | 1 | 1 | 1 |
| `load_file` | `01ff16` | 10 | 10 | 10 | 10 | 10 | 10 | 11 | 11 | 11 | 11 | 11 | 11 | 11 | 12 | 12 | 11 | 12 | 12 | 12 | 13 | 10 | 10 | 10 | 10 | 10 |
| `rand_beam` | `0203be` | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 |
| `byterun1_row` | `0203e8` | 148 | 148 | 148 | 148 | 148 | 148 | 148 | 148 | 148 | 148 | 148 | 148 | 148 | 148 | 148 | 148 | 148 | 148 | 148 | 148 | 148 | 148 | 148 | 148 | 148 |
| `shape_find_c` | `0204f4` | 288 | 288 | 288 | 288 | 288 | 288 | 288 | 288 | 288 | 288 | 288 | 288 | 288 | 288 | 288 | 288 | 288 | 288 | 288 | 288 | 288 | 288 | 288 | 288 | 288 |
| `shape_find` | `020560` | 288 | 288 | 288 | 288 | 288 | 288 | 336 | 336 | 336 | 336 | 336 | 336 | 342 | 390 | 392 | 338 | 392 | 364 | 392 | 418 | 288 | 288 | 288 | 288 | 288 |
| `mem_alloc` | `020848` | 11 | 11 | 11 | 11 | 10 | 11 | 15 | 15 | 15 | 15 | 15 | 15 | 14 | 18 | 17 | 14 | 17 | 18 | 17 | 21 | 11 | 11 | 11 | 11 | 11 |
| `sub_020874` | `020874` | 21 | 21 | 21 | 21 | 20 | 21 | 26 | 26 | 26 | 26 | 26 | 26 | 25 | 30 | 29 | 25 | 29 | 30 | 29 | 34 | 21 | 21 | 21 | 21 | 21 |
| `mem_free` | `02090a` | 14 | 14 | 14 | 14 | 13 | 14 | 16 | 16 | 16 | 16 | 16 | 16 | 15 | 17 | 16 | 15 | 16 | 17 | 16 | 18 | 14 | 14 | 14 | 14 | 14 |
| `sub_0223cc` | `0223cc` | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 |
| `sub_022424` | `022424` | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 |
| `os_dos_close` | `022aae` | 10 | 10 | 10 | 10 | 10 | 10 | 11 | 11 | 11 | 11 | 11 | 11 | 11 | 12 | 12 | 11 | 12 | 12 | 12 | 13 | 10 | 10 | 10 | 10 | 10 |
| `sub_022ab2` | `022ab2` | 10 | 10 | 10 | 10 | 10 | 10 | 11 | 11 | 11 | 11 | 11 | 11 | 11 | 12 | 12 | 11 | 12 | 12 | 12 | 13 | 10 | 10 | 10 | 10 | 10 |
| `os_dos_examine` | `022ada` | 10 | 10 | 10 | 10 | 10 | 10 | 11 | 11 | 11 | 11 | 11 | 11 | 11 | 12 | 12 | 11 | 12 | 12 | 12 | 13 | 10 | 10 | 10 | 10 | 10 |
| `os_dos_lock` | `022b1a` | 10 | 10 | 10 | 10 | 10 | 10 | 11 | 11 | 11 | 11 | 11 | 11 | 11 | 12 | 12 | 11 | 12 | 12 | 12 | 13 | 10 | 10 | 10 | 10 | 10 |
| `os_dos_open` | `022b2c` | 10 | 10 | 10 | 10 | 10 | 10 | 11 | 11 | 11 | 11 | 11 | 11 | 11 | 12 | 12 | 11 | 12 | 12 | 12 | 13 | 10 | 10 | 10 | 10 | 10 |
| `sub_022b30` | `022b30` | 10 | 10 | 10 | 10 | 10 | 10 | 11 | 11 | 11 | 11 | 11 | 11 | 11 | 12 | 12 | 11 | 12 | 12 | 12 | 13 | 10 | 10 | 10 | 10 | 10 |
| `os_dos_read` | `022b3e` | 20 | 20 | 20 | 20 | 20 | 20 | 22 | 22 | 22 | 22 | 22 | 22 | 22 | 24 | 24 | 22 | 24 | 24 | 24 | 26 | 20 | 20 | 20 | 20 | 20 |
| `os_dos_unlock` | `022b50` | 10 | 10 | 10 | 10 | 10 | 10 | 11 | 11 | 11 | 11 | 11 | 11 | 11 | 12 | 12 | 11 | 12 | 12 | 12 | 13 | 10 | 10 | 10 | 10 | 10 |
| `sub_022d36` | `022d36` | 21 | 21 | 21 | 21 | 20 | 21 | 26 | 26 | 26 | 26 | 26 | 26 | 25 | 30 | 29 | 25 | 29 | 30 | 29 | 34 | 21 | 21 | 21 | 21 | 21 |
| `sub_022d3a` | `022d3a` | 21 | 21 | 21 | 21 | 20 | 21 | 26 | 26 | 26 | 26 | 26 | 26 | 25 | 30 | 29 | 25 | 29 | 30 | 29 | 34 | 21 | 21 | 21 | 21 | 21 |
| `sub_022d86` | `022d86` | 14 | 14 | 14 | 14 | 13 | 14 | 16 | 16 | 16 | 16 | 16 | 16 | 15 | 17 | 16 | 15 | 16 | 17 | 16 | 18 | 14 | 14 | 14 | 14 | 14 |
| `sub_022d8a` | `022d8a` | 14 | 14 | 14 | 14 | 13 | 14 | 16 | 16 | 16 | 16 | 16 | 16 | 15 | 17 | 16 | 15 | 16 | 17 | 16 | 18 | 14 | 14 | 14 | 14 | 14 |
| `gfx_BltBitMap` | `022e0c` | 3 | 3 | 3 | 3 | 3 | 3 | 3 | 3 | 3 | 3 | 3 | 3 | 3 | 3 | 3 | 3 | 3 | 3 | 3 | 3 | 3 | 3 | 3 | 3 | 3 |
| `gfx_BltClear` | `022e2e` | 7 | 7 | 7 | 7 | 7 | 7 | 7 | 7 | 7 | 7 | 7 | 7 | 7 | 7 | 7 | 7 | 7 | 7 | 7 | 7 | 7 | 7 | 7 | 7 | 7 |
| `gfx_InitBitMap` | `022e5a` | 5 | 5 | 5 | 5 | 5 | 5 | 5 | 5 | 5 | 5 | 5 | 5 | 5 | 5 | 5 | 5 | 5 | 5 | 5 | 5 | 5 | 5 | 5 | 5 | 5 |
| `gfx_InitRastPort` | `022e6c` | 5 | 5 | 5 | 5 | 5 | 5 | 5 | 5 | 5 | 5 | 5 | 5 | 5 | 5 | 5 | 5 | 5 | 5 | 5 | 5 | 5 | 5 | 5 | 5 | 5 |

### Mission setup, the tick main runs itself

| Routine | Address | `kills_a` | `wrecks_a` | `burning_a` | `oil_d` | `night_d` | `airfield_e` | `cruise_f` | `torpedo_f` | `crash_f` | `crash_side_f` | `rockets_f` | `cruise_g` | `destroyer_h` | `ships_i` | `battleship_j` | `battleship_k` | `destroyer_l` | `japcarrier_m` | `destroyer_n` | `japcarrier_o` | `countdown_b` | `countdown_c` | `enemy_a` | `fight_a` | `sunk_a` |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| `objects_step` | `010a72` | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 |
| `shot_origin` | `011274` | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 |
| `logic_tick` | `011386` | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 |
| `ship_launches` | `011510` | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 |
| `airfields_step` | `011622` | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 |
| `input_queue_pop` | `011714` | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 |
| `gun_splashes` | `0119bc` | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 |
| `engine_smoke` | `011bfc` | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 |
| `balloons_step` | `011c5e` | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 |
| `ships_sinking` | `011cae` | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 |
| `target_timers` | `011de4` | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 |
| `sound_channels` | `012066` | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 |
| `engine_sound` | `012132` | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 |
| `sub_0122ce` | `0122ce` | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 |
| `smoke_claim` | `015460` | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| `sub_0154cc` | `0154cc` | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| `button` | `01b5b0` | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 |
| `guns` | `01b682` | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 |
| `enemy_countdown_step` | `01bc02` | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 |
| `player_update` | `01c660` | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 |
| `rand_mod` | `01cac8` | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| `burn_smoke` | `01cae0` | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| `aircraft_frame_index` | `01d35a` | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| `aircraft_relation` | `01d3b4` | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| `aircraft_order` | `01d476` | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| `aircraft_motion` | `01d796` | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| `aircraft_falling` | `01e244` | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| `aircraft_speed` | `01e64e` | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| `enemy_aircraft_step` | `01e7d6` | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 |
| `sub_01ea28` | `01ea28` | 3 | 3 | 3 | 3 | 3 | 3 | 3 | 3 | 3 | 3 | 3 | 3 | 3 | 3 | 3 | 3 | 3 | 3 | 3 | 3 | 3 | 3 | 3 | 3 | 3 |
| `sub_01eac0` | `01eac0` | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 |
| `sub_01eb2e` | `01eb2e` | 3 | 3 | 3 | 3 | 3 | 3 | 3 | 3 | 3 | 3 | 3 | 3 | 3 | 3 | 3 | 3 | 3 | 3 | 3 | 3 | 3 | 3 | 3 | 3 | 3 |
| `rand_beam` | `0203be` | 0 | 0 | 5 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| `ffp_fix` | `021cc4` | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| `ffp_flt` | `021ce2` | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| `ffp_mul` | `021cec` | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| `sub_021d7c` | `021d7c` | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| `os_disable` | `022d48` | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 |
| `os_enable` | `022d66` | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 |

### Mission setup, VBlank servers

| Routine | Address | `kills_a` | `wrecks_a` | `burning_a` | `oil_d` | `night_d` | `airfield_e` | `cruise_f` | `torpedo_f` | `crash_f` | `crash_side_f` | `rockets_f` | `cruise_g` | `destroyer_h` | `ships_i` | `battleship_j` | `battleship_k` | `destroyer_l` | `japcarrier_m` | `destroyer_n` | `japcarrier_o` | `countdown_b` | `countdown_c` | `enemy_a` | `fight_a` | `sunk_a` |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| `input_queue_pop` | `011714` | 0 | 0 | 0 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 0 | 0 | 0 | 0 | 0 |
| `vblank_server` | `011754` | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 |
| `read_joy_bits` | `01520e` | 0 | 0 | 0 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 0 | 0 | 0 | 0 | 0 |
| `vblank_every_frame` | `01c9ca` | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 |
| `read_joystick` | `01ca32` | 0 | 0 | 0 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 0 | 0 | 0 | 0 | 0 |
| `read_joy_dispatch` | `01cb20` | 0 | 0 | 0 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 0 | 0 | 0 | 0 | 0 |
| `soundfx_vblank` | `01ec64` | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 |
| `poll_fire` | `02044c` | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 |
| `read_fire_button` | `02046a` | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 |
| `os_disable` | `022d48` | 0 | 0 | 0 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 0 | 0 | 0 | 0 | 0 |
| `os_enable` | `022d66` | 0 | 0 | 0 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 0 | 0 | 0 | 0 | 0 |

### A pass during a mission: `frame_update`'s tree (phase F)

| Routine | Address | `kills_a` | `wrecks_a` | `burning_a` | `oil_d` | `night_d` | `airfield_e` | `cruise_f` | `torpedo_f` | `crash_f` | `crash_side_f` | `rockets_f` | `cruise_g` | `destroyer_h` | `ships_i` | `battleship_j` | `battleship_k` | `destroyer_l` | `japcarrier_m` | `destroyer_n` | `japcarrier_o` | `countdown_b` | `countdown_c` | `enemy_a` | `fight_a` | `sunk_a` |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| `frame_update` | `010228` | 692 | 2266 | 1970 | 1890 | 1890 | 2831 | 2027 | 2186 | 1796 | 1832 | 1805 | 2468 | 2364 | 2170 | 1630 | 2242 | 1802 | 1964 | 2470 | 2770 | 4368 | 4123 | 5218 | 17989 | 12837 |
| `flip_buffers` | `01030c` | 692 | 2266 | 1970 | 1890 | 1890 | 2831 | 2027 | 2186 | 1796 | 1832 | 1805 | 2468 | 2364 | 2170 | 1630 | 2242 | 1802 | 1964 | 2470 | 2770 | 4368 | 4123 | 5218 | 17989 | 12837 |
| `weapon_marker` | `010344` | 692 | 2266 | 1970 | 1890 | 1890 | 2831 | 2027 | 2186 | 1796 | 1832 | 1805 | 2468 | 2364 | 2170 | 1630 | 2242 | 1802 | 1964 | 2470 | 2770 | 4368 | 4123 | 5218 | 17989 | 12837 |
| `draw_player` | `0103a6` | 692 | 2266 | 1970 | 1890 | 1890 | 2831 | 2027 | 2186 | 1796 | 1832 | 1805 | 2468 | 2364 | 2170 | 1630 | 2242 | 1802 | 1964 | 2470 | 2770 | 4368 | 4123 | 5218 | 17989 | 12837 |
| `draw_objects` | `0106be` | 692 | 2266 | 1970 | 1890 | 1890 | 2831 | 2027 | 2186 | 1796 | 1832 | 1805 | 2468 | 2364 | 2170 | 1630 | 2242 | 1802 | 1964 | 2470 | 2770 | 4368 | 4123 | 5218 | 17989 | 12837 |
| `object_draw` | `010702` | 0 | 0 | 0 | 322 | 322 | 0 | 0 | 1292 | 189 | 126 | 36 | 112 | 161 | 217 | 168 | 112 | 112 | 112 | 217 | 133 | 329 | 837 | 1102 | 1161 | 9131 |
| `draw_enemy_aircraft` | `010da6` | 692 | 2266 | 1970 | 1890 | 1890 | 2831 | 2027 | 2186 | 1796 | 1832 | 1805 | 2468 | 2364 | 2170 | 1630 | 2242 | 1802 | 1964 | 2470 | 2770 | 4368 | 4123 | 5218 | 17989 | 12837 |
| `smoke_draw` | `010ee0` | 692 | 2266 | 1970 | 1890 | 1890 | 2831 | 2027 | 2186 | 1796 | 1832 | 1805 | 2468 | 2364 | 2170 | 1630 | 2242 | 1802 | 1964 | 2470 | 2770 | 4368 | 4123 | 5218 | 17989 | 12837 |
| `snapshot_for_draw` | `010f88` | 692 | 2266 | 1970 | 1890 | 1890 | 2831 | 2027 | 2186 | 1796 | 1832 | 1805 | 2468 | 2364 | 2170 | 1630 | 2242 | 1802 | 1964 | 2470 | 2770 | 4368 | 4123 | 5218 | 17989 | 12837 |
| `draw_game_over` | `0110c2` | 692 | 2266 | 1970 | 1890 | 1890 | 2831 | 2027 | 2186 | 1796 | 1832 | 1805 | 2468 | 2364 | 2170 | 1630 | 2242 | 1802 | 1964 | 2470 | 2770 | 4368 | 4123 | 5218 | 17989 | 12837 |
| `torpedoes_hit` | `011ae2` | 0 | 0 | 0 | 0 | 0 | 0 | 449 | 104 | 58 | 40 | 191 | 221 | 329 | 466 | 606 | 358 | 429 | 300 | 274 | 640 | 0 | 0 | 0 | 0 | 0 |
| `draw_world` | `013772` | 692 | 2266 | 1970 | 1890 | 1890 | 2831 | 2027 | 2186 | 1796 | 1832 | 1805 | 2468 | 2364 | 2170 | 1630 | 2242 | 1802 | 1964 | 2470 | 2770 | 4368 | 4123 | 5218 | 17989 | 12837 |
| `ship_planes` | `01391e` | 692 | 2266 | 1970 | 1890 | 1890 | 2831 | 2027 | 2186 | 1796 | 1832 | 1805 | 2468 | 2364 | 2170 | 1630 | 2242 | 1802 | 1964 | 2470 | 2770 | 4368 | 4123 | 5218 | 17989 | 12837 |
| `airfields_draw` | `013a18` | 692 | 2266 | 1970 | 1890 | 1890 | 2831 | 2027 | 2186 | 1796 | 1832 | 1805 | 2468 | 2364 | 2170 | 1630 | 2242 | 1802 | 1964 | 2470 | 2770 | 4368 | 4123 | 5218 | 17989 | 12837 |
| `deck_aircraft` | `013abc` | 692 | 2266 | 1970 | 1890 | 1890 | 2831 | 2027 | 2186 | 1796 | 1832 | 1805 | 2468 | 2364 | 2170 | 1630 | 2242 | 1802 | 1964 | 2470 | 2770 | 4368 | 4123 | 5218 | 17989 | 12837 |
| `record_extras` | `013b1c` | 28431 | 361838 | 136141 | 139532 | 139532 | 427911 | 149550 | 161442 | 132180 | 134818 | 133290 | 171416 | 154558 | 160166 | 100240 | 165620 | 133050 | 144744 | 182448 | 919546 | 322605 | 304404 | 62732 | 242312 | 672677 |
| `targets_3_draw` | `013d78` | 692 | 2266 | 1970 | 1890 | 1890 | 2831 | 2027 | 2186 | 1796 | 1832 | 1805 | 2468 | 2364 | 2170 | 1630 | 2242 | 1802 | 1964 | 2470 | 2770 | 4368 | 4123 | 5218 | 17989 | 12837 |
| `targets_f_draw` | `013de8` | 692 | 2266 | 1970 | 1890 | 1890 | 2831 | 2027 | 2186 | 1796 | 1832 | 1805 | 2468 | 2364 | 2170 | 1630 | 2242 | 1802 | 1964 | 2470 | 2770 | 4368 | 4123 | 5218 | 17989 | 12837 |
| `ocean` | `013e6c` | 692 | 2266 | 1970 | 1890 | 1890 | 2831 | 2027 | 2186 | 1796 | 1832 | 1805 | 2468 | 2364 | 2170 | 1630 | 2242 | 1802 | 1964 | 2470 | 2770 | 4368 | 4123 | 5218 | 17989 | 12837 |
| `soldiers_draw` | `013eee` | 692 | 2266 | 1970 | 1890 | 1890 | 2831 | 2027 | 2186 | 1796 | 1832 | 1805 | 2468 | 2364 | 2170 | 1630 | 2242 | 1802 | 1964 | 2470 | 2770 | 4368 | 4123 | 5218 | 17989 | 12837 |
| `lift_aircraft` | `01409c` | 692 | 2266 | 1970 | 1890 | 1890 | 2831 | 2027 | 2186 | 1796 | 1832 | 1805 | 2468 | 2364 | 2170 | 1630 | 2242 | 1802 | 1964 | 2470 | 2770 | 4368 | 4123 | 5218 | 17989 | 12837 |
| `islands_draw` | `0140e8` | 692 | 2266 | 1970 | 1890 | 1890 | 2831 | 2027 | 2186 | 1796 | 1832 | 1805 | 2468 | 2364 | 2170 | 1630 | 2242 | 1802 | 1964 | 2470 | 2770 | 4368 | 4123 | 5218 | 17989 | 12837 |
| `map_window` | `01417e` | 692 | 2266 | 1970 | 1890 | 1890 | 2831 | 2027 | 2186 | 1796 | 1832 | 1805 | 2468 | 2364 | 2170 | 1630 | 2242 | 1802 | 1964 | 2470 | 2770 | 4368 | 4123 | 5218 | 17989 | 12837 |
| `window_height` | `0141b4` | 692 | 1225 | 1970 | 1890 | 1890 | 2220 | 2027 | 2186 | 1796 | 1832 | 1805 | 2354 | 2364 | 2170 | 1630 | 2242 | 1802 | 1964 | 2470 | 1346 | 4368 | 4123 | 5218 | 17989 | 12809 |
| `window_strip` | `014206` | 692 | 1225 | 1970 | 1890 | 1890 | 2220 | 2027 | 2186 | 1796 | 1832 | 1805 | 2354 | 2364 | 2170 | 1630 | 2242 | 1802 | 1964 | 2470 | 1346 | 4368 | 4123 | 5218 | 17989 | 12809 |
| `window_ship` | `014430` | 692 | 1225 | 1970 | 1890 | 1890 | 2220 | 810 | 834 | 798 | 814 | 1173 | 1274 | 1328 | 810 | 558 | 1464 | 696 | 1964 | 1464 | 1346 | 4368 | 4123 | 5218 | 17989 | 12809 |
| `window_background` | `014564` | 692 | 2266 | 1970 | 1890 | 1890 | 2831 | 2027 | 2186 | 1796 | 1832 | 1805 | 2468 | 2364 | 2170 | 1630 | 2242 | 1802 | 1964 | 2470 | 2770 | 4368 | 4123 | 5218 | 17989 | 12837 |
| `window_shape` | `0145a6` | 0 | 1046 | 8943 | 13496 | 13496 | 20890 | 2856 | 3732 | 1206 | 1548 | 2632 | 9920 | 11216 | 5724 | 2662 | 6714 | 4700 | 7128 | 7236 | 1350 | 3832 | 24513 | 3166 | 17928 | 2722 |
| `ship_at_offset` | `014a4e` | 2899 | 13967 | 3743 | 3986 | 3986 | 2854 | 4036 | 4436 | 8116 | 8468 | 4875 | 3296 | 4134 | 6092 | 4598 | 4408 | 3842 | 3500 | 5516 | 11216 | 2899 | 5690 | 6656 | 7372 | 79135 |
| `ship_at_span` | `014a52` | 3222 | 15190 | 4737 | 4968 | 4968 | 3172 | 5764 | 6034 | 10038 | 10418 | 7019 | 4072 | 6568 | 11592 | 7488 | 6708 | 6268 | 4512 | 9306 | 12676 | 5188 | 7428 | 9712 | 10754 | 89902 |
| `ship_guns_draw` | `014c3e` | 692 | 2266 | 1970 | 1890 | 1890 | 2831 | 2027 | 2186 | 1796 | 1832 | 1805 | 2468 | 2364 | 2170 | 1630 | 2242 | 1802 | 1964 | 2470 | 2770 | 4368 | 4123 | 5218 | 17989 | 12837 |
| `target_frame` | `014d50` | 1384 | 4532 | 3940 | 18900 | 18900 | 42465 | 24324 | 26232 | 21552 | 21984 | 21660 | 46892 | 40188 | 45570 | 0 | 53808 | 36040 | 72668 | 81510 | 108030 | 21840 | 45353 | 10436 | 35978 | 25674 |
| `target_range_frame` | `014db8` | 746 | 1812 | 3302 | 11760 | 11760 | 28590 | 27408 | 20888 | 11392 | 11488 | 22791 | 38594 | 41250 | 48048 | 20152 | 58064 | 45696 | 82500 | 96580 | 100720 | 20245 | 34441 | 8960 | 34050 | 7616 |
| `ride_on_ship` | `014eac` | 2899 | 13967 | 3743 | 3986 | 3986 | 2854 | 4036 | 4436 | 8116 | 8468 | 4875 | 3296 | 4134 | 6092 | 4598 | 4408 | 3842 | 3500 | 5516 | 11216 | 2899 | 5690 | 6656 | 7372 | 79135 |
| `ship_gun_shell` | `014efc` | 0 | 0 | 0 | 0 | 0 | 0 | 6852 | 3464 | 2848 | 2872 | 5139 | 7016 | 13200 | 17472 | 20152 | 21392 | 23936 | 36250 | 38632 | 76072 | 0 | 0 | 0 | 0 | 0 |
| `target_fire` | `014f5c` | 0 | 1031 | 534 | 742 | 742 | 6001 | 2336 | 586 | 296 | 256 | 976 | 3433 | 2518 | 2532 | 3254 | 3006 | 2206 | 3092 | 3108 | 83878 | 0 | 2633 | 0 | 644 | 31 |
| `format_to` | `015078` | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 4 | 4 | 4 | 4 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 4 | 2 |
| `format_putch` | `015090` | 16 | 16 | 16 | 16 | 16 | 16 | 16 | 32 | 32 | 32 | 32 | 16 | 16 | 16 | 16 | 16 | 16 | 16 | 16 | 16 | 16 | 16 | 16 | 32 | 16 |
| `flip_view` | `0150b0` | 692 | 2266 | 1970 | 1890 | 1890 | 2831 | 2027 | 2186 | 1796 | 1832 | 1805 | 2468 | 2364 | 2170 | 1630 | 2242 | 1802 | 1964 | 2470 | 2770 | 4368 | 4123 | 5218 | 17989 | 12837 |
| `map_slot_at` | `0150c8` | 0 | 0 | 0 | 0 | 0 | 0 | 449 | 104 | 58 | 40 | 191 | 221 | 329 | 466 | 603 | 356 | 429 | 275 | 274 | 570 | 0 | 0 | 0 | 0 | 0 |
| `draw_world_shape` | `015174` | 3411 | 11271 | 34943 | 20380 | 20380 | 48041 | 35673 | 26514 | 18118 | 16223 | 25467 | 52052 | 48551 | 50929 | 39513 | 50305 | 44662 | 62166 | 67351 | 140619 | 31241 | 65408 | 26930 | 118583 | 59563 |
| `sub_01520c` | `01520c` | 692 | 2266 | 1970 | 1890 | 1890 | 2831 | 2027 | 2186 | 1796 | 1832 | 1805 | 2468 | 2364 | 2170 | 1630 | 2242 | 1802 | 1964 | 2470 | 2770 | 4368 | 4123 | 5218 | 17989 | 12837 |
| `clip_playfield` | `01524a` | 2076 | 5757 | 5910 | 5670 | 5670 | 7882 | 6081 | 6558 | 5388 | 5496 | 5415 | 7290 | 7092 | 6510 | 4890 | 6726 | 5406 | 5892 | 7410 | 6886 | 13104 | 12369 | 15654 | 53967 | 38483 |
| `clip_dash_window` | `01525c` | 692 | 2266 | 1970 | 1890 | 1890 | 2831 | 2027 | 2186 | 1796 | 1832 | 1805 | 2468 | 2364 | 2170 | 1630 | 2242 | 1802 | 1964 | 2470 | 2770 | 4368 | 4123 | 5218 | 17989 | 12837 |
| `clip_to_waterline` | `01526e` | 1335 | 3442 | 3891 | 3704 | 3704 | 5007 | 4010 | 4274 | 3098 | 3128 | 3546 | 4766 | 4650 | 4260 | 3182 | 4408 | 3526 | 3850 | 4860 | 4040 | 8687 | 8160 | 10298 | 35892 | 17259 |
| `splash_spawn` | `0152b0` | 0 | 0 | 0 | 0 | 0 | 0 | 449 | 104 | 58 | 40 | 191 | 221 | 329 | 466 | 606 | 358 | 429 | 300 | 274 | 640 | 0 | 0 | 0 | 0 | 0 |
| `splashes_draw` | `0152f8` | 692 | 2266 | 1970 | 1890 | 1890 | 2831 | 2027 | 2186 | 1796 | 1832 | 1805 | 2468 | 2364 | 2170 | 1630 | 2242 | 1802 | 1964 | 2470 | 2770 | 4368 | 4123 | 5218 | 17989 | 12837 |
| `smoke_claim` | `015460` | 0 | 0 | 43 | 59 | 59 | 100 | 187 | 51 | 33 | 21 | 117 | 203 | 211 | 182 | 273 | 256 | 202 | 266 | 251 | 255 | 0 | 195 | 0 | 61 | 0 |
| `smoke_at_player` | `0154e0` | 0 | 0 | 43 | 59 | 59 | 100 | 187 | 51 | 33 | 21 | 78 | 203 | 211 | 182 | 273 | 256 | 202 | 266 | 251 | 255 | 0 | 195 | 0 | 61 | 0 |
| `balloons_draw` | `01557c` | 692 | 2266 | 1970 | 1890 | 1890 | 2831 | 2027 | 2186 | 1796 | 1832 | 1805 | 2468 | 2364 | 2170 | 1630 | 2242 | 1802 | 1964 | 2470 | 2770 | 4368 | 4123 | 5218 | 17989 | 12837 |
| `view_show` | `016f20` | 692 | 2266 | 1970 | 1890 | 1890 | 2831 | 2027 | 2186 | 1796 | 1832 | 1805 | 2468 | 2364 | 2170 | 1630 | 2242 | 1802 | 1964 | 2470 | 2770 | 4368 | 4123 | 5218 | 17989 | 12837 |
| `cop_set_split_line` | `01876e` | 692 | 2266 | 1970 | 1890 | 1890 | 2831 | 2027 | 2186 | 1796 | 1832 | 1805 | 2468 | 2364 | 2170 | 1630 | 2242 | 1802 | 1964 | 2470 | 2770 | 4368 | 4123 | 5218 | 17989 | 12837 |
| `cop_wait` | `019a9c` | 692 | 2266 | 1970 | 1890 | 1890 | 2831 | 2027 | 2186 | 1796 | 1832 | 1805 | 2468 | 2364 | 2170 | 1630 | 2242 | 1802 | 1964 | 2470 | 2770 | 4368 | 4123 | 5218 | 17989 | 12837 |
| `cop_install` | `01aa0e` | 692 | 2266 | 1970 | 1890 | 1890 | 2831 | 2027 | 2186 | 1796 | 1832 | 1805 | 2468 | 2364 | 2170 | 1630 | 2242 | 1802 | 1964 | 2470 | 2770 | 4368 | 4123 | 5218 | 17989 | 12837 |
| `wait_vblank` | `01aa3e` | 692 | 2266 | 1970 | 1890 | 1890 | 2831 | 2027 | 2186 | 1796 | 1832 | 1805 | 2468 | 2364 | 2170 | 1630 | 2242 | 1802 | 1964 | 2470 | 2770 | 4368 | 4123 | 5218 | 17989 | 12837 |
| `record_on_ship` | `01cb34` | 4 | 112 | 112 | 112 | 112 | 4 | 184 | 166 | 140 | 420 | 260 | 56 | 192 | 340 | 230 | 220 | 188 | 88 | 282 | 172 | 4 | 8 | 12 | 224 | 70 |
| `ship_of_record` | `01cbf2` | 4 | 112 | 112 | 112 | 112 | 4 | 184 | 166 | 140 | 420 | 260 | 56 | 192 | 340 | 230 | 220 | 188 | 88 | 282 | 172 | 4 | 8 | 12 | 224 | 70 |
| `draw_dashboard` | `01ee16` | 692 | 2266 | 1970 | 1890 | 1890 | 2831 | 2027 | 2186 | 1796 | 1832 | 1805 | 2468 | 2364 | 2170 | 1630 | 2242 | 1802 | 1964 | 2470 | 2770 | 4368 | 4123 | 5218 | 17989 | 12837 |
| `kill_icons` | `01f200` | 32 | 4 | 10 | 4 | 4 | 4 | 4 | 4 | 4 | 4 | 4 | 4 | 4 | 4 | 4 | 4 | 4 | 4 | 4 | 4 | 4 | 4 | 4 | 10 | 4 |
| `enemy_arrows` | `01f21a` | 692 | 2266 | 1970 | 1890 | 1890 | 2831 | 2027 | 2186 | 1796 | 1832 | 1805 | 2468 | 2364 | 2170 | 1630 | 2242 | 1802 | 1964 | 2470 | 2770 | 4368 | 4123 | 5218 | 17989 | 12837 |
| `draw_score` | `01f26a` | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 4 | 4 | 4 | 4 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 4 | 2 |
| `dash_digit` | `01f2b0` | 18 | 18 | 22 | 18 | 18 | 18 | 18 | 32 | 32 | 32 | 32 | 18 | 18 | 18 | 18 | 18 | 18 | 18 | 18 | 18 | 18 | 18 | 18 | 36 | 18 |
| `clip_dashboard` | `01f2dc` | 1384 | 4532 | 3940 | 3780 | 3780 | 5662 | 4054 | 4372 | 3592 | 3664 | 3610 | 4936 | 4728 | 4340 | 3260 | 4484 | 3604 | 3928 | 4940 | 5540 | 8736 | 8246 | 10436 | 35978 | 25674 |
| `rand_beam` | `0203be` | 0 | 2082 | 1342 | 1849 | 1849 | 12732 | 14218 | 5326 | 3824 | 3662 | 8362 | 16028 | 20712 | 25344 | 30460 | 30175 | 31087 | 44983 | 47306 | 248221 | 0 | 6298 | 0 | 1878 | 56 |
| `blit_clip_setup` | `0209bc` | 11320 | 36604 | 42213 | 61568 | 61568 | 140768 | 44186 | 38047 | 33681 | 32454 | 35535 | 63761 | 68455 | 57317 | 43701 | 60222 | 55185 | 64476 | 70834 | 116205 | 45056 | 113700 | 59274 | 243087 | 268750 |
| `shape_blit` | `020b0c` | 11320 | 36604 | 42213 | 61525 | 61525 | 140768 | 44186 | 37990 | 33681 | 32454 | 35535 | 63761 | 68443 | 57295 | 43701 | 60222 | 55170 | 64476 | 70834 | 116201 | 45056 | 113700 | 59274 | 241344 | 268750 |
| `shape_draw` | `020ce2` | 11202 | 36486 | 42091 | 61353 | 61353 | 140660 | 44078 | 37756 | 32659 | 31348 | 35371 | 63629 | 68267 | 57115 | 43525 | 60050 | 54994 | 64300 | 70654 | 116029 | 44938 | 113508 | 58978 | 241134 | 251956 |
| `shape_draw_xor` | `020e24` | 0 | 0 | 0 | 43 | 43 | 0 | 0 | 57 | 0 | 0 | 0 | 0 | 12 | 22 | 0 | 0 | 15 | 0 | 0 | 4 | 0 | 0 | 0 | 1743 | 0 |
| `rect_fill` | `021010` | 2768 | 10105 | 16112 | 18950 | 18950 | 34865 | 10705 | 12058 | 9074 | 9278 | 9275 | 21746 | 20648 | 13160 | 4890 | 17996 | 12242 | 18812 | 21028 | 18044 | 22540 | 42375 | 20872 | 87574 | 51376 |
| `draw_set_target` | `02124a` | 2076 | 6798 | 5910 | 5670 | 5670 | 8493 | 6081 | 6558 | 5388 | 5496 | 5415 | 7404 | 7092 | 6510 | 4890 | 6726 | 5406 | 5892 | 7410 | 8310 | 13104 | 12369 | 15654 | 53967 | 38511 |
| `clip_set` | `02129c` | 5487 | 15997 | 15711 | 15044 | 15044 | 21382 | 16172 | 17390 | 13874 | 14120 | 14376 | 19460 | 18834 | 17280 | 12962 | 17860 | 14338 | 15634 | 19680 | 19236 | 34895 | 32898 | 41606 | 143826 | 94253 |
| `blit_begin` | `0212ce` | 4893 | 15911 | 13839 | 13306 | 13306 | 19861 | 14233 | 15400 | 13066 | 13360 | 12699 | 17332 | 16626 | 15270 | 11488 | 15770 | 12692 | 13826 | 17370 | 19466 | 30625 | 28947 | 36664 | 126009 | 98246 |
| `blit_end` | `0212d4` | 4893 | 15911 | 13839 | 13306 | 13306 | 19861 | 14233 | 15400 | 13066 | 13360 | 12699 | 17332 | 16626 | 15270 | 11488 | 15770 | 12692 | 13826 | 17370 | 19466 | 30625 | 28947 | 36664 | 126009 | 98246 |
| `line_draw` | `021318` | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 26 | 0 | 0 |
| `sub_022e40` | `022e40` | 4893 | 15911 | 13839 | 13306 | 13306 | 19861 | 14233 | 15400 | 13066 | 13360 | 12699 | 17332 | 16626 | 15270 | 11488 | 15770 | 12692 | 13826 | 17370 | 19466 | 30625 | 28947 | 36664 | 126009 | 98246 |
| `sub_022e8a` | `022e8a` | 4893 | 15911 | 13839 | 13306 | 13306 | 19861 | 14233 | 15400 | 13066 | 13360 | 12699 | 17332 | 16626 | 15270 | 11488 | 15770 | 12692 | 13826 | 17370 | 19466 | 30625 | 28947 | 36664 | 126009 | 98246 |

### A VBlank during a mission (phase V)

| Routine | Address | `kills_a` | `wrecks_a` | `burning_a` | `oil_d` | `night_d` | `airfield_e` | `cruise_f` | `torpedo_f` | `crash_f` | `crash_side_f` | `rockets_f` | `cruise_g` | `destroyer_h` | `ships_i` | `battleship_j` | `battleship_k` | `destroyer_l` | `japcarrier_m` | `destroyer_n` | `japcarrier_o` | `countdown_b` | `countdown_c` | `enemy_a` | `fight_a` | `sunk_a` |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| `vblank_server` | `011754` | 1385 | 4533 | 3941 | 3779 | 3779 | 5663 | 4055 | 4371 | 3591 | 3663 | 3611 | 4935 | 4727 | 4339 | 3259 | 4483 | 3603 | 3927 | 4939 | 5539 | 8737 | 8245 | 10437 | 35977 | 25673 |
| `vblank_server:ticker_glyph` | `011754` | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 48 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| `vblank_server:ticker_message` | `011754` | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 49 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| `vblank_server:ticker_scroll` | `011754` | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1181 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| `read_joy_bits` | `01520e` | 347 | 1134 | 986 | 945 | 945 | 1416 | 1014 | 1093 | 898 | 916 | 903 | 1234 | 1182 | 1085 | 815 | 1121 | 901 | 982 | 1235 | 1385 | 2185 | 2062 | 2610 | 8995 | 6419 |
| `vblank_every_frame` | `01c9ca` | 1385 | 4533 | 3941 | 3779 | 3779 | 5663 | 4055 | 4371 | 3591 | 3663 | 3611 | 4935 | 4727 | 4339 | 3259 | 4483 | 3603 | 3927 | 4939 | 5539 | 8737 | 8245 | 10437 | 35977 | 25673 |
| `read_joystick` | `01ca32` | 347 | 1134 | 986 | 945 | 945 | 1416 | 1014 | 1093 | 898 | 916 | 903 | 1234 | 1182 | 1085 | 815 | 1121 | 901 | 982 | 1235 | 1385 | 2185 | 2062 | 2610 | 8995 | 6419 |
| `read_joy_dispatch` | `01cb20` | 347 | 1134 | 986 | 945 | 945 | 1416 | 1014 | 1093 | 898 | 916 | 903 | 1234 | 1182 | 1085 | 815 | 1121 | 901 | 982 | 1235 | 1385 | 2185 | 2062 | 2610 | 8995 | 6419 |
| `soundfx_vblank` | `01ec64` | 1385 | 4533 | 3941 | 3779 | 3779 | 5663 | 4055 | 4371 | 3591 | 3663 | 3611 | 4935 | 4727 | 4339 | 3259 | 4483 | 3603 | 3927 | 4939 | 5539 | 8737 | 8245 | 10437 | 35977 | 25673 |
| `poll_fire` | `02044c` | 1385 | 4533 | 3941 | 3779 | 3779 | 5663 | 4055 | 4371 | 3591 | 3663 | 3611 | 4935 | 4727 | 4339 | 3259 | 4483 | 3603 | 3927 | 4939 | 5539 | 8737 | 8245 | 10437 | 35977 | 25673 |
| `read_fire_button` | `02046a` | 1385 | 4533 | 3941 | 3779 | 3779 | 5663 | 4055 | 4371 | 3591 | 3663 | 3611 | 4935 | 4727 | 4339 | 3259 | 4483 | 3603 | 3927 | 4939 | 5539 | 8737 | 8245 | 10437 | 35977 | 25673 |

### The inner loop beside `frame_update` during a mission (phase M)

| Routine | Address | `kills_a` | `wrecks_a` | `burning_a` | `oil_d` | `night_d` | `airfield_e` | `cruise_f` | `torpedo_f` | `crash_f` | `crash_side_f` | `rockets_f` | `cruise_g` | `destroyer_h` | `ships_i` | `battleship_j` | `battleship_k` | `destroyer_l` | `japcarrier_m` | `destroyer_n` | `japcarrier_o` | `countdown_b` | `countdown_c` | `enemy_a` | `fight_a` | `sunk_a` |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| `run_queued_ticks` | `0114d8` | 692 | 2266 | 1970 | 1890 | 1890 | 2831 | 2027 | 2186 | 1796 | 1832 | 1805 | 2468 | 2364 | 2170 | 1630 | 2242 | 1802 | 1964 | 2470 | 2770 | 4368 | 4123 | 5218 | 17989 | 12837 |
| `ingame_keys` | `01ccf6` | 693 | 2267 | 1971 | 1891 | 1891 | 2832 | 2028 | 2187 | 1797 | 1833 | 1806 | 2469 | 2365 | 2171 | 1631 | 2243 | 1803 | 1965 | 2471 | 2771 | 4369 | 4124 | 5219 | 17990 | 12837 |
| `key_available` | `0207d8` | 693 | 2267 | 1971 | 1891 | 1891 | 2832 | 2028 | 2187 | 1797 | 1833 | 1806 | 2469 | 2365 | 2171 | 1631 | 2243 | 1803 | 1965 | 2471 | 2771 | 4369 | 4124 | 5219 | 17990 | 12837 |

### The tick during a mission (phase T)

| Routine | Address | `kills_a` | `wrecks_a` | `burning_a` | `oil_d` | `night_d` | `airfield_e` | `cruise_f` | `torpedo_f` | `crash_f` | `crash_side_f` | `rockets_f` | `cruise_g` | `destroyer_h` | `ships_i` | `battleship_j` | `battleship_k` | `destroyer_l` | `japcarrier_m` | `destroyer_n` | `japcarrier_o` | `countdown_b` | `countdown_c` | `enemy_a` | `fight_a` | `sunk_a` |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| `flip_buffers` | `01030c` | 0 | 0 | 0 | 1 | 1 | 0 | 0 | 1 | 1 | 1 | 0 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 0 | 1 | 0 | 1 | 0 |
| `object_draw_first` | `0107f2` | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 0 | 0 | 2 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| `object_spawn` | `010820` | 0 | 0 | 0 | 46 | 46 | 0 | 0 | 16 | 27 | 18 | 0 | 16 | 23 | 31 | 24 | 16 | 16 | 16 | 31 | 19 | 0 | 46 | 0 | 47 | 15 |
| `rocket_homing` | `01099a` | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| `objects_step` | `010a72` | 346 | 1133 | 985 | 949 | 949 | 1415 | 1013 | 1097 | 902 | 920 | 902 | 1238 | 1186 | 1089 | 819 | 1125 | 905 | 986 | 1239 | 1389 | 2184 | 2066 | 2609 | 8999 | 6419 |
| `object_step` | `010aa6` | 0 | 0 | 0 | 184 | 184 | 0 | 0 | 654 | 108 | 72 | 19 | 64 | 92 | 124 | 96 | 64 | 64 | 64 | 124 | 76 | 165 | 442 | 551 | 606 | 4574 |
| `weapon_drop` | `01107c` | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 0 | 0 | 2 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| `airfield_at` | `011126` | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 11 | 0 | 0 | 13 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 10 | 10 | 10 | 20 | 40 |
| `pillbox_between` | `01115c` | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 2 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| `ship_gun_between` | `0111a6` | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 2 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| `shot_origin` | `011274` | 346 | 1133 | 985 | 949 | 949 | 1415 | 1013 | 1097 | 902 | 920 | 902 | 1238 | 1186 | 1089 | 819 | 1125 | 905 | 986 | 1239 | 1389 | 2184 | 2066 | 2609 | 8999 | 6419 |
| `weapon_menu` | `0112b0` | 333 | 1120 | 972 | 922 | 922 | 1402 | 1000 | 1070 | 875 | 893 | 889 | 1215 | 1159 | 1062 | 792 | 1098 | 878 | 959 | 1212 | 1362 | 2171 | 2039 | 2582 | 8972 | 6406 |
| `logic_tick` | `011386` | 346 | 1133 | 985 | 949 | 949 | 1415 | 1013 | 1097 | 902 | 920 | 902 | 1238 | 1186 | 1089 | 819 | 1125 | 905 | 986 | 1239 | 1389 | 2184 | 2066 | 2609 | 8999 | 6419 |
| `lift_step` | `011460` | 333 | 1120 | 972 | 922 | 922 | 1402 | 1000 | 1070 | 875 | 893 | 889 | 1215 | 1159 | 1062 | 792 | 1098 | 878 | 959 | 1212 | 1362 | 2171 | 2039 | 2582 | 8972 | 6406 |
| `ship_launches` | `011510` | 346 | 1133 | 985 | 949 | 949 | 1415 | 1013 | 1097 | 902 | 920 | 902 | 1238 | 1186 | 1089 | 819 | 1125 | 905 | 986 | 1239 | 1389 | 2184 | 2066 | 2609 | 8999 | 6419 |
| `airfields_step` | `011622` | 346 | 1133 | 985 | 949 | 949 | 1415 | 1013 | 1097 | 902 | 920 | 902 | 1238 | 1186 | 1089 | 819 | 1125 | 905 | 986 | 1239 | 1389 | 2184 | 2066 | 2609 | 8999 | 6419 |
| `input_queue_pop` | `011714` | 346 | 1133 | 985 | 949 | 949 | 1415 | 1013 | 1097 | 902 | 920 | 902 | 1238 | 1186 | 1089 | 819 | 1125 | 905 | 986 | 1239 | 1389 | 2184 | 2066 | 2609 | 8999 | 6419 |
| `vblank_server` | `011754` | 0 | 0 | 0 | 21 | 21 | 0 | 0 | 21 | 21 | 21 | 0 | 21 | 21 | 21 | 21 | 21 | 21 | 21 | 21 | 21 | 0 | 21 | 0 | 21 | 0 |
| `gun_splashes` | `0119bc` | 346 | 1133 | 985 | 949 | 949 | 1415 | 1013 | 1097 | 902 | 920 | 902 | 1238 | 1186 | 1089 | 819 | 1125 | 905 | 986 | 1239 | 1389 | 2184 | 2066 | 2609 | 8999 | 6419 |
| `guns_ground_x` | `011a46` | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 3 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 366 | 0 |
| `soldiers_hit_c` | `011a84` | 0 | 0 | 23 | 15 | 15 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 15 | 0 | 62 | 0 |
| `soldiers_hit` | `011a8c` | 0 | 0 | 23 | 15 | 15 | 0 | 0 | 0 | 0 | 0 | 2 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 15 | 0 | 428 | 0 |
| `torpedoes_hit` | `011ae2` | 0 | 0 | 23 | 15 | 15 | 0 | 0 | 0 | 0 | 0 | 2 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 15 | 0 | 428 | 0 |
| `engine_smoke` | `011bfc` | 346 | 1133 | 985 | 949 | 949 | 1415 | 1013 | 1097 | 902 | 920 | 902 | 1238 | 1186 | 1089 | 819 | 1125 | 905 | 986 | 1239 | 1389 | 2184 | 2066 | 2609 | 8999 | 6419 |
| `balloons_step` | `011c5e` | 346 | 1133 | 985 | 949 | 949 | 1415 | 1013 | 1097 | 902 | 920 | 902 | 1238 | 1186 | 1089 | 819 | 1125 | 905 | 986 | 1239 | 1389 | 2184 | 2066 | 2609 | 8999 | 6419 |
| `ships_sinking` | `011cae` | 346 | 1133 | 985 | 949 | 949 | 1415 | 1013 | 1097 | 902 | 920 | 902 | 1238 | 1186 | 1089 | 819 | 1125 | 905 | 986 | 1239 | 1389 | 2184 | 2066 | 2609 | 8999 | 6419 |
| `ship_sinking` | `011cd8` | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 329 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 329 |
| `target_timers` | `011de4` | 346 | 1133 | 985 | 949 | 949 | 1415 | 1013 | 1097 | 902 | 920 | 902 | 1238 | 1186 | 1089 | 819 | 1125 | 905 | 986 | 1239 | 1389 | 2184 | 2066 | 2609 | 8999 | 6419 |
| `sound_slots_clear` | `011f4e` | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 2 | 2 | 2 | 1 |
| `sound_channels` | `012066` | 347 | 1134 | 986 | 950 | 950 | 1416 | 1014 | 1098 | 903 | 921 | 903 | 1239 | 1187 | 1090 | 820 | 1126 | 906 | 987 | 1240 | 1390 | 2185 | 2068 | 2611 | 9001 | 6420 |
| `engine_sound` | `012132` | 346 | 1133 | 985 | 949 | 949 | 1415 | 1013 | 1097 | 902 | 920 | 902 | 1238 | 1186 | 1089 | 819 | 1125 | 905 | 986 | 1239 | 1389 | 2184 | 2066 | 2609 | 8999 | 6419 |
| `sub_0122ce` | `0122ce` | 346 | 1133 | 985 | 949 | 949 | 1415 | 1013 | 1097 | 902 | 920 | 902 | 1238 | 1186 | 1089 | 819 | 1125 | 905 | 986 | 1239 | 1389 | 2184 | 2066 | 2609 | 8999 | 6419 |
| `sub_0122f6` | `0122f6` | 0 | 0 | 0 | 46 | 46 | 0 | 0 | 4 | 27 | 3 | 2 | 1 | 8 | 31 | 9 | 1 | 1 | 1 | 31 | 4 | 3 | 49 | 3 | 49 | 12 |
| `sub_012306` | `012306` | 0 | 0 | 0 | 46 | 46 | 0 | 0 | 4 | 27 | 3 | 2 | 1 | 8 | 31 | 9 | 1 | 1 | 1 | 31 | 4 | 3 | 49 | 3 | 49 | 12 |
| `sub_012324` | `012324` | 0 | 0 | 0 | 46 | 46 | 0 | 0 | 2 | 27 | 3 | 2 | 1 | 8 | 31 | 9 | 1 | 1 | 1 | 31 | 4 | 1 | 47 | 1 | 47 | 4 |
| `sub_01233e` | `01233e` | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 2 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 2 | 2 | 2 | 2 | 8 |
| `sub_012354` | `012354` | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 2 | 2 | 2 | 1 |
| `sub_012380` | `012380` | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 0 | 1 |
| `next_aircraft` | `0135ce` | 0 | 0 | 0 | 1 | 1 | 0 | 0 | 1 | 1 | 1 | 0 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 0 | 1 | 0 | 1 | 1 |
| `player_lost_restart` | `0135d8` | 0 | 0 | 0 | 1 | 1 | 0 | 0 | 1 | 1 | 1 | 0 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 0 | 1 | 0 | 1 | 1 |
| `player_restart_state` | `013684` | 0 | 0 | 0 | 1 | 1 | 0 | 0 | 1 | 1 | 1 | 0 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 0 | 1 | 1 | 1 | 0 |
| `sub_013756` | `013756` | 0 | 0 | 0 | 1 | 1 | 0 | 0 | 1 | 1 | 1 | 0 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 0 | 1 | 1 | 1 | 0 |
| `crash_hit` | `0146c6` | 0 | 0 | 11 | 15 | 15 | 0 | 0 | 0 | 1 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 15 | 0 | 39 | 0 |
| `weapon_hit` | `0146dc` | 0 | 0 | 11 | 15 | 15 | 0 | 0 | 1 | 1 | 1 | 2 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 16 | 1 | 39 | 4 |
| `ship_at_offset` | `014a4e` | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 1 | 1 | 2 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 1 | 1 | 23 | 4 |
| `ship_at_span` | `014a52` | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 1 | 1 | 2 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 1 | 1 | 23 | 4 |
| `format_to` | `015078` | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| `format_putch` | `015090` | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 49 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| `flip_view` | `0150b0` | 0 | 0 | 0 | 1 | 1 | 0 | 0 | 1 | 1 | 1 | 0 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 0 | 1 | 0 | 1 | 0 |
| `map_slot_at` | `0150c8` | 0 | 0 | 34 | 17 | 17 | 0 | 0 | 253 | 1 | 1 | 15 | 32 | 16 | 0 | 14 | 32 | 32 | 32 | 0 | 26 | 244 | 283 | 332 | 1636 | 1380 |
| `cosine` | `015104` | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 2 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| `sine` | `015108` | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 4 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| `tangent` | `01514c` | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 3 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 357 | 0 |
| `sub_01520c` | `01520c` | 0 | 0 | 0 | 1 | 1 | 0 | 0 | 1 | 1 | 1 | 0 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 0 | 1 | 0 | 1 | 0 |
| `read_joy_bits` | `01520e` | 0 | 0 | 0 | 5 | 5 | 0 | 0 | 5 | 5 | 5 | 0 | 5 | 5 | 5 | 5 | 5 | 5 | 5 | 5 | 5 | 0 | 5 | 0 | 5 | 0 |
| `clip_playfield` | `01524a` | 0 | 0 | 0 | 1 | 1 | 0 | 0 | 1 | 1 | 1 | 0 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 0 | 1 | 0 | 1 | 0 |
| `splash_spawn_c` | `0152ac` | 0 | 0 | 23 | 2 | 2 | 0 | 0 | 32 | 0 | 0 | 0 | 32 | 16 | 0 | 14 | 32 | 32 | 32 | 0 | 26 | 0 | 0 | 0 | 47 | 0 |
| `splash_spawn` | `0152b0` | 0 | 0 | 23 | 2 | 2 | 0 | 0 | 136 | 0 | 0 | 0 | 32 | 16 | 0 | 14 | 32 | 32 | 32 | 0 | 26 | 116 | 128 | 160 | 813 | 666 |
| `smoke_claim` | `015460` | 0 | 0 | 491 | 103 | 103 | 376 | 166 | 110 | 39 | 3 | 97 | 292 | 223 | 182 | 116 | 145 | 120 | 154 | 258 | 132 | 0 | 490 | 0 | 952 | 0 |
| `sub_0154cc` | `0154cc` | 0 | 0 | 420 | 37 | 37 | 0 | 0 | 0 | 37 | 0 | 0 | 0 | 0 | 37 | 0 | 0 | 0 | 0 | 37 | 0 | 0 | 37 | 0 | 331 | 0 |
| `smoke_at_player` | `0154e0` | 0 | 0 | 71 | 66 | 66 | 376 | 166 | 110 | 2 | 3 | 97 | 292 | 223 | 145 | 116 | 145 | 120 | 154 | 221 | 132 | 0 | 453 | 0 | 621 | 0 |
| `ticker_offer` | `01555a` | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| `ship_sunk_message` | `015640` | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| `sub_015710` | `015710` | 321 | 1267 | 1012 | 774 | 774 | 1393 | 1043 | 912 | 716 | 551 | 974 | 1020 | 992 | 1103 | 627 | 950 | 678 | 767 | 1263 | 1238 | 2159 | 1834 | 2545 | 8887 | 2107 |
| `ground_height` | `015714` | 321 | 1267 | 1012 | 774 | 774 | 1393 | 1043 | 912 | 716 | 551 | 984 | 1020 | 992 | 1103 | 627 | 950 | 678 | 767 | 1263 | 1238 | 2159 | 1834 | 2545 | 8887 | 2107 |
| `shape_mirror_x` | `015b58` | 24 | 32 | 30 | 34 | 34 | 40 | 38 | 46 | 40 | 38 | 48 | 32 | 38 | 42 | 38 | 38 | 38 | 28 | 34 | 44 | 46 | 74 | 58 | 360 | 66 |
| `view_show` | `016f20` | 0 | 0 | 0 | 1 | 1 | 0 | 0 | 1 | 1 | 1 | 0 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 0 | 1 | 0 | 1 | 0 |
| `cop_install` | `01aa0e` | 0 | 0 | 0 | 1 | 1 | 0 | 0 | 1 | 1 | 1 | 0 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 0 | 1 | 0 | 1 | 0 |
| `turn_allowed` | `01aa6e` | 0 | 156 | 104 | 104 | 104 | 260 | 208 | 156 | 52 | 52 | 104 | 104 | 52 | 156 | 52 | 52 | 52 | 0 | 104 | 104 | 520 | 360 | 572 | 1820 | 468 |
| `wheel_height` | `01aaea` | 507 | 2240 | 1837 | 1767 | 1767 | 2651 | 1899 | 1890 | 1222 | 1066 | 1709 | 2164 | 2010 | 2017 | 1275 | 1969 | 1474 | 1628 | 2307 | 2476 | 4183 | 3801 | 4785 | 17760 | 4174 |
| `turn_step` | `01ab80` | 0 | 156 | 104 | 104 | 104 | 260 | 208 | 156 | 52 | 52 | 104 | 104 | 52 | 156 | 52 | 52 | 52 | 0 | 104 | 104 | 520 | 360 | 572 | 1820 | 468 |
| `aircraft_frame` | `01abde` | 322 | 1259 | 1061 | 874 | 874 | 1644 | 1192 | 1196 | 553 | 700 | 971 | 1308 | 1195 | 1047 | 828 | 1135 | 914 | 945 | 1147 | 1449 | 2660 | 2233 | 3091 | 10569 | 2676 |
| `wreck_smoke` | `01aed8` | 0 | 0 | 0 | 150 | 150 | 0 | 0 | 150 | 150 | 150 | 0 | 150 | 150 | 150 | 150 | 150 | 150 | 150 | 150 | 150 | 0 | 150 | 0 | 150 | 150 |
| `lost_wait` | `01af7c` | 0 | 0 | 0 | 150 | 150 | 0 | 0 | 150 | 150 | 150 | 0 | 150 | 150 | 150 | 150 | 150 | 150 | 150 | 150 | 150 | 0 | 150 | 0 | 150 | 150 |
| `crash` | `01afba` | 0 | 0 | 0 | 35 | 35 | 0 | 0 | 34 | 11 | 5 | 0 | 45 | 34 | 33 | 34 | 35 | 34 | 34 | 33 | 35 | 0 | 34 | 0 | 20 | 0 |
| `hook_state` | `01b45a` | 322 | 1109 | 961 | 908 | 908 | 1394 | 992 | 1045 | 652 | 649 | 871 | 1207 | 1144 | 1046 | 777 | 1084 | 863 | 944 | 1196 | 1348 | 2160 | 2020 | 2540 | 8953 | 2226 |
| `on_the_lift` | `01b4de` | 187 | 974 | 826 | 588 | 588 | 1259 | 857 | 726 | 357 | 360 | 736 | 877 | 825 | 728 | 458 | 764 | 544 | 625 | 878 | 1028 | 2025 | 1566 | 2361 | 8514 | 1940 |
| `button` | `01b5b0` | 346 | 1133 | 985 | 949 | 949 | 1415 | 1013 | 1097 | 902 | 920 | 902 | 1238 | 1186 | 1089 | 819 | 1125 | 905 | 986 | 1239 | 1389 | 2184 | 2066 | 2609 | 8999 | 6419 |
| `guns` | `01b682` | 346 | 1133 | 985 | 949 | 949 | 1415 | 1013 | 1097 | 902 | 920 | 902 | 1238 | 1186 | 1089 | 819 | 1125 | 905 | 986 | 1239 | 1389 | 2184 | 2066 | 2609 | 8999 | 6419 |
| `deck_span` | `01b7bc` | 0 | 0 | 0 | 1 | 1 | 0 | 0 | 1 | 1 | 1 | 0 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 0 | 1 | 1 | 1 | 0 |
| `player_reset` | `01b7ec` | 0 | 0 | 0 | 1 | 1 | 0 | 0 | 1 | 1 | 1 | 0 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 0 | 1 | 1 | 1 | 0 |
| `touches_ground` | `01b8c4` | 186 | 973 | 825 | 587 | 587 | 1258 | 856 | 725 | 356 | 359 | 735 | 876 | 824 | 727 | 457 | 763 | 543 | 624 | 877 | 1027 | 2024 | 1564 | 2240 | 8512 | 1917 |
| `cable_hook` | `01b92e` | 104 | 104 | 104 | 104 | 104 | 104 | 104 | 104 | 104 | 104 | 104 | 104 | 104 | 104 | 104 | 104 | 104 | 104 | 104 | 104 | 104 | 208 | 223 | 208 | 126 |
| `sub_01b9bc` | `01b9bc` | 0 | 0 | 0 | 1 | 1 | 0 | 0 | 1 | 1 | 1 | 0 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 0 | 1 | 1 | 1 | 0 |
| `engine_idle` | `01b9cc` | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 2 | 1 | 2 | 1 |
| `sub_01b9f0` | `01b9f0` | 186 | 973 | 825 | 587 | 587 | 1258 | 856 | 725 | 356 | 359 | 735 | 876 | 824 | 727 | 457 | 763 | 543 | 624 | 877 | 1027 | 2024 | 1564 | 2240 | 8512 | 1917 |
| `ground_contact` | `01ba80` | 186 | 973 | 825 | 587 | 587 | 1258 | 856 | 725 | 356 | 359 | 735 | 876 | 824 | 727 | 457 | 763 | 543 | 624 | 877 | 1027 | 2024 | 1564 | 2240 | 8512 | 1917 |
| `enemy_countdown_step` | `01bc02` | 346 | 1133 | 985 | 949 | 949 | 1415 | 1013 | 1097 | 902 | 920 | 902 | 1238 | 1186 | 1089 | 819 | 1125 | 905 | 986 | 1239 | 1389 | 2184 | 2066 | 2609 | 8999 | 6419 |
| `deck_state` | `01bcce` | 290 | 1077 | 929 | 691 | 691 | 1362 | 960 | 829 | 460 | 463 | 839 | 980 | 928 | 831 | 561 | 867 | 647 | 728 | 981 | 1131 | 2128 | 1772 | 2463 | 8720 | 2043 |
| `deck_roll` | `01bdba` | 104 | 104 | 104 | 104 | 104 | 104 | 104 | 104 | 104 | 104 | 104 | 104 | 104 | 104 | 104 | 104 | 104 | 104 | 104 | 104 | 104 | 208 | 236 | 208 | 126 |
| `player_motion` | `01bdfa` | 186 | 973 | 825 | 587 | 587 | 1258 | 856 | 725 | 356 | 359 | 735 | 876 | 824 | 727 | 457 | 763 | 543 | 624 | 877 | 1027 | 2024 | 1564 | 2240 | 8512 | 1917 |
| `flight_controls` | `01bff4` | 186 | 973 | 825 | 587 | 587 | 1258 | 856 | 725 | 356 | 359 | 735 | 876 | 824 | 727 | 457 | 763 | 543 | 624 | 877 | 1027 | 2024 | 1564 | 2240 | 8512 | 1917 |
| `frame_select` | `01c378` | 322 | 1109 | 961 | 908 | 908 | 1394 | 992 | 1045 | 652 | 649 | 871 | 1207 | 1144 | 1046 | 777 | 1084 | 863 | 944 | 1196 | 1348 | 2160 | 2020 | 2540 | 8953 | 2226 |
| `deck_controls` | `01c4e8` | 104 | 104 | 104 | 104 | 104 | 104 | 104 | 104 | 104 | 104 | 104 | 104 | 104 | 104 | 104 | 104 | 104 | 104 | 104 | 104 | 104 | 208 | 223 | 208 | 126 |
| `deck_edge` | `01c5f4` | 104 | 104 | 104 | 104 | 104 | 104 | 104 | 104 | 104 | 104 | 104 | 104 | 104 | 104 | 104 | 104 | 104 | 104 | 104 | 104 | 104 | 208 | 223 | 208 | 126 |
| `player_update` | `01c660` | 346 | 1133 | 985 | 949 | 949 | 1415 | 1013 | 1097 | 902 | 920 | 902 | 1238 | 1186 | 1089 | 819 | 1125 | 905 | 986 | 1239 | 1389 | 2184 | 2066 | 2609 | 8999 | 6419 |
| `record_at` | `01c982` | 507 | 2081 | 1808 | 1693 | 1693 | 2651 | 1847 | 1817 | 1184 | 1028 | 1605 | 2141 | 2015 | 1969 | 1281 | 1895 | 1453 | 1615 | 2269 | 2423 | 4183 | 3780 | 4780 | 17696 | 4155 |
| `vblank_every_frame` | `01c9ca` | 0 | 0 | 0 | 21 | 21 | 0 | 0 | 21 | 21 | 21 | 0 | 21 | 21 | 21 | 21 | 21 | 21 | 21 | 21 | 21 | 0 | 21 | 0 | 21 | 0 |
| `read_joystick` | `01ca32` | 0 | 0 | 0 | 5 | 5 | 0 | 0 | 5 | 5 | 5 | 0 | 5 | 5 | 5 | 5 | 5 | 5 | 5 | 5 | 5 | 0 | 5 | 0 | 5 | 0 |
| `flash_set` | `01cab4` | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| `rand_mod` | `01cac8` | 0 | 0 | 486 | 278 | 278 | 427 | 391 | 417 | 201 | 192 | 180 | 286 | 301 | 402 | 682 | 280 | 551 | 25 | 524 | 392 | 66 | 50 | 44 | 719 | 181 |
| `burn_smoke` | `01cae0` | 0 | 0 | 420 | 37 | 37 | 0 | 0 | 0 | 37 | 0 | 0 | 0 | 0 | 37 | 0 | 0 | 0 | 0 | 37 | 0 | 0 | 37 | 0 | 331 | 0 |
| `read_joy_dispatch` | `01cb20` | 0 | 0 | 0 | 5 | 5 | 0 | 0 | 5 | 5 | 5 | 0 | 5 | 5 | 5 | 5 | 5 | 5 | 5 | 5 | 5 | 0 | 5 | 0 | 5 | 0 |
| `sub_01cb30` | `01cb30` | 1488 | 4973 | 4383 | 3851 | 3851 | 6098 | 4238 | 4656 | 2691 | 2976 | 3933 | 5616 | 5451 | 4361 | 3616 | 5151 | 4046 | 4601 | 5261 | 6321 | 9178 | 8548 | 10781 | 39004 | 9486 |
| `record_on_ship` | `01cb34` | 0 | 0 | 0 | 185 | 185 | 0 | 0 | 0 | 163 | 7 | 0 | 9 | 25 | 174 | 26 | 0 | 0 | 8 | 184 | 21 | 0 | 185 | 0 | 172 | 0 |
| `on_water` | `01cb74` | 0 | 0 | 23 | 36 | 36 | 0 | 0 | 35 | 24 | 8 | 0 | 46 | 43 | 50 | 44 | 36 | 35 | 35 | 50 | 39 | 0 | 35 | 0 | 69 | 0 |
| `record_is_land` | `01cbb2` | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 0 |
| `aircraft_gone_far` | `01d18c` | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 118 | 160 | 131 | 1925 | 924 |
| `aircraft_frame_index` | `01d35a` | 0 | 0 | 609 | 337 | 337 | 882 | 513 | 585 | 408 | 418 | 392 | 507 | 427 | 574 | 672 | 273 | 724 | 194 | 624 | 825 | 787 | 618 | 890 | 5819 | 3450 |
| `aircraft_relation` | `01d3b4` | 0 | 0 | 609 | 337 | 337 | 882 | 513 | 585 | 408 | 418 | 392 | 507 | 427 | 574 | 672 | 273 | 724 | 194 | 624 | 825 | 787 | 618 | 890 | 5818 | 3450 |
| `aircraft_order` | `01d476` | 0 | 0 | 609 | 337 | 337 | 882 | 513 | 585 | 408 | 418 | 392 | 507 | 427 | 574 | 672 | 273 | 724 | 194 | 624 | 825 | 787 | 618 | 890 | 5818 | 3450 |
| `aircraft_turn_step` | `01d530` | 0 | 0 | 0 | 52 | 52 | 463 | 312 | 221 | 73 | 73 | 145 | 171 | 106 | 129 | 334 | 21 | 106 | 0 | 125 | 275 | 0 | 0 | 0 | 1504 | 73 |
| `aircraft_turn` | `01d562` | 0 | 0 | 0 | 53 | 53 | 468 | 315 | 224 | 73 | 73 | 147 | 174 | 108 | 131 | 336 | 21 | 108 | 0 | 126 | 277 | 0 | 0 | 0 | 1504 | 73 |
| `aircraft_motion` | `01d796` | 0 | 0 | 509 | 337 | 337 | 882 | 513 | 585 | 408 | 418 | 392 | 507 | 427 | 574 | 672 | 273 | 724 | 194 | 624 | 825 | 787 | 618 | 890 | 5818 | 3450 |
| `fighter_cruise` | `01d9c6` | 0 | 0 | 0 | 206 | 206 | 871 | 513 | 480 | 408 | 418 | 392 | 489 | 295 | 464 | 659 | 273 | 554 | 194 | 581 | 737 | 0 | 0 | 0 | 0 | 0 |
| `fighter_attack` | `01dccc` | 0 | 0 | 0 | 131 | 131 | 11 | 0 | 105 | 0 | 0 | 0 | 18 | 132 | 110 | 13 | 0 | 170 | 0 | 43 | 88 | 0 | 0 | 0 | 0 | 0 |
| `torpedo_plane` | `01dea4` | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 669 | 458 | 759 | 3818 | 2526 |
| `torpedo_plane_away` | `01e17a` | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 118 | 160 | 131 | 1925 | 924 |
| `aircraft_falling` | `01e244` | 0 | 0 | 509 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 75 | 0 |
| `aircraft_burning` | `01e3e8` | 0 | 0 | 100 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| `aircraft_launch` | `01e4d0` | 0 | 0 | 0 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 2 | 1 | 2 | 1 | 2 | 2 | 1 | 1 | 2 | 3 | 4 |
| `aircraft_speed` | `01e64e` | 0 | 0 | 609 | 337 | 337 | 882 | 513 | 585 | 408 | 418 | 392 | 507 | 427 | 574 | 672 | 273 | 724 | 194 | 624 | 825 | 787 | 618 | 890 | 5818 | 3450 |
| `aircraft_fly` | `01e728` | 0 | 0 | 0 | 337 | 337 | 882 | 513 | 585 | 408 | 418 | 392 | 507 | 427 | 574 | 672 | 273 | 724 | 194 | 624 | 825 | 787 | 618 | 890 | 5743 | 3450 |
| `enemy_aircraft_step` | `01e7d6` | 346 | 1133 | 985 | 949 | 949 | 1415 | 1013 | 1097 | 902 | 920 | 902 | 1238 | 1186 | 1089 | 819 | 1125 | 905 | 986 | 1239 | 1389 | 2184 | 2066 | 2609 | 8999 | 6419 |
| `sub_01ea28` | `01ea28` | 9 | 9 | 18 | 117 | 117 | 135 | 24 | 33 | 93 | 21 | 24 | 33 | 54 | 120 | 45 | 24 | 27 | 21 | 114 | 255 | 18 | 159 | 33 | 234 | 45 |
| `sub_01eac0` | `01eac0` | 12 | 12 | 28 | 129 | 129 | 217 | 38 | 45 | 103 | 31 | 32 | 53 | 70 | 134 | 57 | 38 | 39 | 33 | 128 | 413 | 22 | 196 | 46 | 275 | 56 |
| `sub_01eb2e` | `01eb2e` | 9 | 9 | 18 | 117 | 117 | 135 | 24 | 33 | 93 | 21 | 24 | 33 | 54 | 120 | 45 | 24 | 27 | 21 | 114 | 255 | 18 | 159 | 33 | 234 | 45 |
| `sub_01eb4c` | `01eb4c` | 86 | 453 | 403 | 643 | 643 | 1320 | 600 | 727 | 240 | 235 | 499 | 1086 | 796 | 762 | 517 | 691 | 622 | 558 | 906 | 862 | 691 | 1378 | 919 | 3961 | 940 |
| `soundfx_vblank` | `01ec64` | 0 | 0 | 0 | 21 | 21 | 0 | 0 | 21 | 21 | 21 | 0 | 21 | 21 | 21 | 21 | 21 | 21 | 21 | 21 | 21 | 0 | 21 | 0 | 21 | 0 |
| `weapon_gauge_reset` | `01edbc` | 0 | 0 | 0 | 1 | 1 | 0 | 0 | 2 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 0 | 1 | 1 | 1 | 0 |
| `rand_beam` | `0203be` | 0 | 0 | 2599 | 970 | 970 | 2452 | 1436 | 1404 | 739 | 627 | 973 | 1605 | 1407 | 1497 | 1616 | 1027 | 1561 | 701 | 1872 | 1635 | 853 | 2066 | 935 | 9292 | 3634 |
| `poll_fire` | `02044c` | 0 | 0 | 0 | 21 | 21 | 0 | 0 | 21 | 21 | 21 | 0 | 21 | 21 | 21 | 21 | 21 | 21 | 21 | 21 | 21 | 0 | 21 | 0 | 21 | 0 |
| `read_fire_button` | `02046a` | 0 | 0 | 0 | 21 | 21 | 0 | 0 | 21 | 21 | 21 | 0 | 21 | 21 | 21 | 21 | 21 | 21 | 21 | 21 | 21 | 0 | 21 | 0 | 21 | 0 |
| `sub_0204e4` | `0204e4` | 322 | 1109 | 961 | 908 | 908 | 1394 | 992 | 1045 | 652 | 649 | 871 | 1207 | 1144 | 1046 | 777 | 1084 | 863 | 944 | 1196 | 1348 | 2160 | 2020 | 2540 | 8953 | 2226 |
| `sub_0204ec` | `0204ec` | 322 | 1109 | 961 | 908 | 908 | 1394 | 992 | 1045 | 652 | 649 | 871 | 1207 | 1144 | 1046 | 777 | 1084 | 863 | 944 | 1196 | 1348 | 2160 | 2020 | 2540 | 8953 | 2226 |
| `shape_find_c` | `0204f4` | 1488 | 4973 | 4383 | 3851 | 3851 | 6098 | 4238 | 4656 | 2691 | 2976 | 3933 | 5616 | 5451 | 4361 | 3616 | 5151 | 4046 | 4601 | 5261 | 6321 | 9178 | 8548 | 10781 | 39004 | 9486 |
| `shape_find` | `020560` | 1488 | 4973 | 4383 | 3851 | 3851 | 6098 | 4238 | 4656 | 2691 | 2976 | 3933 | 5616 | 5451 | 4361 | 3616 | 5151 | 4046 | 4601 | 5261 | 6321 | 9178 | 8548 | 10781 | 39004 | 9486 |
| `rect_fill` | `021010` | 0 | 0 | 0 | 1 | 1 | 0 | 0 | 1 | 1 | 1 | 0 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 0 | 1 | 0 | 1 | 0 |
| `draw_set_target` | `02124a` | 0 | 0 | 0 | 1 | 1 | 0 | 0 | 1 | 1 | 1 | 0 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 0 | 1 | 0 | 1 | 0 |
| `clip_set` | `02129c` | 0 | 0 | 0 | 1 | 1 | 0 | 0 | 1 | 1 | 1 | 0 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 0 | 1 | 0 | 1 | 0 |
| `blit_begin` | `0212ce` | 0 | 0 | 0 | 1 | 1 | 0 | 0 | 1 | 1 | 1 | 0 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 0 | 1 | 0 | 1 | 0 |
| `blit_end` | `0212d4` | 0 | 0 | 0 | 1 | 1 | 0 | 0 | 1 | 1 | 1 | 0 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 0 | 1 | 0 | 1 | 0 |
| `ffp_add` | `021c9c` | 186 | 973 | 825 | 587 | 587 | 1258 | 856 | 725 | 356 | 359 | 735 | 876 | 824 | 727 | 457 | 763 | 543 | 624 | 877 | 1027 | 2024 | 1564 | 2240 | 8512 | 1917 |
| `ffp_neg` | `021cb0` | 0 | 590 | 746 | 508 | 508 | 465 | 749 | 542 | 288 | 292 | 332 | 150 | 102 | 632 | 111 | 696 | 137 | 0 | 798 | 909 | 1667 | 1040 | 1833 | 4236 | 1416 |
| `ffp_fix` | `021cc4` | 558 | 2919 | 2984 | 2098 | 2098 | 4656 | 3081 | 2760 | 1476 | 1495 | 2597 | 3135 | 2899 | 2755 | 2043 | 2562 | 2353 | 2066 | 3255 | 3906 | 6859 | 5310 | 7610 | 31354 | 9201 |
| `ffp_div` | `021cd8` | 372 | 1946 | 1650 | 1174 | 1174 | 2516 | 1712 | 1450 | 712 | 718 | 1470 | 1752 | 1648 | 1454 | 914 | 1526 | 1086 | 1248 | 1754 | 2054 | 4048 | 3128 | 4480 | 17024 | 3834 |
| `ffp_flt` | `021ce2` | 372 | 1946 | 2159 | 1511 | 1511 | 3398 | 2225 | 2035 | 1120 | 1136 | 1862 | 2259 | 2075 | 2028 | 1586 | 1799 | 1810 | 1442 | 2378 | 2879 | 4835 | 3746 | 5370 | 22842 | 7284 |
| `ffp_mul` | `021cec` | 558 | 2919 | 2984 | 2098 | 2098 | 4656 | 3081 | 2760 | 1476 | 1495 | 2597 | 3135 | 2899 | 2755 | 2043 | 2562 | 2353 | 2066 | 3255 | 3906 | 6859 | 5310 | 7610 | 31354 | 9201 |
| `sub_021d7c` | `021d7c` | 1 | 1 | 0 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 |
| `sub_021e24` | `021e24` | 0 | 0 | 0 | 30 | 30 | 0 | 0 | 30 | 30 | 30 | 0 | 30 | 30 | 30 | 30 | 30 | 30 | 30 | 30 | 30 | 0 | 30 | 0 | 30 | 30 |
| `sub_0222f4` | `0222f4` | 0 | 0 | 0 | 30 | 30 | 0 | 0 | 30 | 30 | 30 | 0 | 30 | 30 | 30 | 30 | 30 | 30 | 30 | 30 | 30 | 0 | 30 | 0 | 30 | 30 |
| `os_disable` | `022d48` | 346 | 1133 | 985 | 949 | 949 | 1415 | 1013 | 1097 | 902 | 920 | 902 | 1238 | 1186 | 1089 | 819 | 1125 | 905 | 986 | 1239 | 1389 | 2184 | 2066 | 2609 | 8999 | 6419 |
| `os_enable` | `022d66` | 346 | 1133 | 985 | 949 | 949 | 1415 | 1013 | 1097 | 902 | 920 | 902 | 1238 | 1186 | 1089 | 819 | 1125 | 905 | 986 | 1239 | 1389 | 2184 | 2066 | 2609 | 8999 | 6419 |
| `sub_022e40` | `022e40` | 0 | 0 | 0 | 1 | 1 | 0 | 0 | 1 | 1 | 1 | 0 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 0 | 1 | 0 | 1 | 0 |
| `sub_022e8a` | `022e8a` | 0 | 0 | 0 | 1 | 1 | 0 | 0 | 1 | 1 | 1 | 0 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 0 | 1 | 0 | 1 | 0 |
| `gfx_WaitTOF` | `022eee` | 0 | 0 | 0 | 21 | 21 | 0 | 0 | 21 | 21 | 21 | 0 | 21 | 21 | 21 | 21 | 21 | 21 | 21 | 21 | 21 | 0 | 21 | 0 | 21 | 0 |

### Entropy reads, by the routine that called `rand_beam`

| Window | Phase | Caller | `kills_a` | `wrecks_a` | `burning_a` | `oil_d` | `night_d` | `airfield_e` | `cruise_f` | `torpedo_f` | `crash_f` | `crash_side_f` | `rockets_f` | `cruise_g` | `destroyer_h` | `ships_i` | `battleship_j` | `battleship_k` | `destroyer_l` | `japcarrier_m` | `destroyer_n` | `japcarrier_o` | `countdown_b` | `countdown_c` | `enemy_a` | `fight_a` | `sunk_a` |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| outer | M | `rand_mod` | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 |
| setup | M | `rand_mod` | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 |
| setup | T | `aircraft_falling` | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| setup | T | `burn_smoke` | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| setup | T | `rand_mod` | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| setup | T | `smoke_claim` | 0 | 0 | 2 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| mission | F | `draw_dashboard` | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 221 | 0 |
| mission | F | `ship_gun_shell` | 0 | 0 | 0 | 0 | 0 | 0 | 8492 | 3861 | 3065 | 3027 | 5827 | 7850 | 14466 | 19207 | 22461 | 22765 | 25560 | 37356 | 39685 | 78458 | 0 | 0 | 0 | 0 | 0 |
| mission | F | `ship_guns_draw` | 0 | 0 | 0 | 0 | 0 | 0 | 2336 | 586 | 296 | 256 | 976 | 1912 | 1786 | 2532 | 3254 | 1980 | 2206 | 1480 | 1502 | 108820 | 0 | 0 | 0 | 0 | 0 |
| mission | F | `smoke_claim` | 0 | 0 | 86 | 118 | 118 | 200 | 372 | 102 | 66 | 42 | 234 | 406 | 410 | 362 | 418 | 438 | 386 | 440 | 482 | 364 | 0 | 390 | 0 | 122 | 0 |
| mission | F | `target_fire` | 0 | 0 | 722 | 989 | 989 | 1989 | 3018 | 777 | 397 | 337 | 1325 | 3086 | 3318 | 3243 | 4327 | 3966 | 2935 | 4095 | 4031 | 5043 | 0 | 3275 | 0 | 891 | 0 |
| mission | F | `target_frame` | 0 | 2082 | 534 | 742 | 742 | 10543 | 0 | 0 | 0 | 0 | 0 | 2774 | 732 | 0 | 0 | 1026 | 0 | 1612 | 1606 | 55536 | 0 | 2633 | 0 | 644 | 56 |
| mission | T | `aircraft_falling` | 0 | 0 | 509 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 75 | 0 |
| mission | T | `aircraft_fly` | 0 | 0 | 0 | 337 | 337 | 882 | 513 | 585 | 408 | 418 | 392 | 507 | 427 | 574 | 672 | 273 | 724 | 194 | 624 | 825 | 787 | 618 | 890 | 5743 | 3450 |
| mission | T | `burn_smoke` | 0 | 0 | 420 | 37 | 37 | 0 | 0 | 0 | 37 | 0 | 0 | 0 | 0 | 37 | 0 | 0 | 0 | 0 | 37 | 0 | 0 | 37 | 0 | 331 | 0 |
| mission | T | `enemy_countdown_step` | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 0 | 3 |
| mission | T | `engine_smoke` | 0 | 0 | 202 | 112 | 112 | 391 | 200 | 182 | 15 | 11 | 199 | 228 | 233 | 120 | 40 | 192 | 46 | 186 | 171 | 160 | 0 | 381 | 0 | 520 | 0 |
| mission | T | `object_spawn` | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 8 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| mission | T | `rand_mod` | 0 | 0 | 486 | 278 | 278 | 427 | 391 | 417 | 201 | 192 | 180 | 286 | 301 | 402 | 682 | 280 | 551 | 25 | 524 | 392 | 66 | 50 | 44 | 719 | 181 |
| mission | T | `smoke_claim` | 0 | 0 | 982 | 206 | 206 | 752 | 332 | 220 | 78 | 6 | 194 | 584 | 446 | 364 | 222 | 282 | 240 | 296 | 516 | 258 | 0 | 980 | 0 | 1904 | 0 |

## Appendix: the regions no run executed

Every region of a ported routine that no run of M4, M5 or M6 executed - M4's scripts, the
night mission, the key runs, the fifteen setups, the eighteen M5 scripts and the twenty-five
of M6 - with the stand-in marker that covers it or what it is otherwise (M7 part 1's scripts
execute the rows of `main` at `0x01015C`, `choose_night`'s night branch and `mission_won`'s
promotion, `re/notes/porting-m7.md`); below them, the
markers whose region the original did run (M7's) and the markers that stand for
a value rather than a region. Written by

```text
.venv/bin/python tools/reach_observe.py --cold REACH45.json REACH6.json
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
| `object_draw_first` `0x0107F2` | `0x01081A`-`0x01081F` | ported from reading: no weapon left or every object record in use, nothing is dropped; tests/`test_oracle_m5.py`, the drop | |
| `object_spawn` `0x010820` | `0x010840`-`0x010841` | ported from reading: all fifteen object records in use, nothing is left | |
| `object_spawn` `0x010820` | `0x010970`-`0x010971` | ported from reading: a rocket's frame from the bearing, clamped at 0; tests/`test_oracle_m5.py`, the drop | |
| `rocket_homing` `0x01099A` | `0x010A16`-`0x010A67` | ported from reading: a rocket aimed at a pillbox or a ship's gun under its bearing, which no script's rocket found; tests/`test_oracle_m5.py`, the objects' step | |
| `object_step` `0x010AA6` | `0x010B1E`-`0x010B21` | ported from reading: a rocket's reach in the eighth-scale view; tests/`test_oracle_m5.py`, the objects' step | |
| `object_step` `0x010AA6` | `0x010B3C`-`0x010B43` | ported from reading: a rocket out of reach is freed; tests/`test_oracle_m5.py`, the objects' step | |
| `object_step` `0x010AA6` | `0x010B94`-`0x010BEF` | ported from reading: a weapon over an airfield, which no script's weapon came down on; tests/`test_oracle_m5.py`, the objects' step | |
| `object_step` `0x010AA6` | `0x010C1A`-`0x010C1F` | ported from reading: a weapon over a record of low bits 3; tests/`test_oracle_m5.py`, the objects' step | |
| `object_step` `0x010AA6` | `0x010C36`-`0x010C53` | ported from reading: a weapon over a ship's deck (low bits 1); `0x010C36` to `0x010C53`, the test of low bits 2 for 3 and 4, is unreachable; tests/`test_oracle_m5.py`, the objects' step | |
| `object_step` `0x010AA6` | `0x010D46`-`0x010D4F` | unreachable: +`0x1A` was set from `pass_counter` a few instructions before, so the splash at the start of a run is never made | |
| `draw_game_over` `0x0110C2` | `0x011118`-`0x011123` | ported from reading; tests/`test_oracle_m4.py`, every count | |
| `airfield_at` `0x011126` | `0x011138`-`0x011153` | ported from reading: an airfield record with a span, which maps a to c have none of; tests/`test_oracle_m5.py`, the objects' step | |
| `pillbox_between` `0x01115C` | `0x01119E`-`0x01119F` | ported from reading: a standing pillbox found under a rocket's bearing; tests/`test_oracle_m5.py`, the objects' step | |
| `choose_night` `0x0111FC` | `0x011218`-`0x01122D` | ported from reading; reached only between two missions, M7's next mission | |
| `weapon_menu` `0x0112B0` | `0x0112D4`-`0x0112D5` | ported from reading: the cursor keys and Return in the weapon menu | |
| `weapon_menu` `0x0112B0` | `0x0112DE`-`0x0112DF` | ported from reading: the cursor keys and Return in the weapon menu | |
| `weapon_menu` `0x0112B0` | `0x0112E8`-`0x0112E9` | ported from reading: the cursor keys and Return in the weapon menu | |
| `weapon_menu` `0x0112B0` | `0x0112F2`-`0x0112F5` | ported from reading: the cursor keys and Return in the weapon menu | |
| `run_queued_ticks` `0x0114D8` | `0x0114E0`-`0x0114E5` | `0x0114E0`, `run_queued_ticks`, demo playback and recording | M7 |
| `run_queued_ticks` `0x0114D8` | `0x0114EE`-`0x0114EF` | ported from reading: nothing runs while paused | |
| `run_queued_ticks` `0x0114D8` | `0x011508`-`0x01150D` | ported from reading: `demo_mode` sets `0x026D44` | |
| `vblank_server` `0x011754` | `0x011790`-`0x0117D3` | M3's input half: demo playback (M7) | |
| `vblank_server` `0x011754` | `0x01180A`-`0x011841` | M3's input half: demo recording (M7) | |
| `guns_ground_x` `0x011A46` | `0x011A58`-`0x011A59` | ported from reading: a bearing of `0xFF01`, taken as `0xFF02`; tests/`test_oracle_m5.py`, the guns' reach | |
| `torpedoes_hit` `0x011AE2` | `0x011B08`-`0x011B09` | ported from reading: a torpedo west of the span; tests/`test_oracle_m5.py`, the soldiers' and torpedoes' hits | |
| `torpedoes_hit` `0x011AE2` | `0x011B30`-`0x011B4B` | ported from reading: the extra object record hit; tests/`test_oracle_m5.py`, the soldiers' and torpedoes' hits | |
| `ship_sinking` `0x011CD8` | `0x011D28`-`0x011D2F` | ported from reading; tests/`test_oracle_m6.py`, the ships sinking: the last enemy ship sunk with no island left, the mission won | |
| `ship_sinking` `0x011CD8` | `0x011D3A`-`0x011D51` | ported from reading; tests/`test_oracle_m6.py`, the ships sinking: the carrier a row deeper with the player aboard, back on the lift | |
| `ship_sinking` `0x011CD8` | `0x011D7E`-`0x011D97` | ported from reading; tests/`test_oracle_m6.py`, the ships sinking: the carrier `0x21` rows down with the aircraft on its deck, into the sea | |
| `target_timers` `0x011DE4` | `0x011E6E`-`0x011E6F` | ported from reading: a barracks' next soldier's timer from `vblank_total`, 0 counting as 3; tests/`test_oracle_m5.py`, the tick's routines | |
| `soldier_out` `0x011E82` | `0x011EF2`-`0x011EF5` | ported from reading: every soldier record in use, nobody comes out | |
| `soldier_out` `0x011E82` | `0x011F42`-`0x011F47` | ported from reading: a dug-out's soldier turned round by `rand_beam` | |
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
| `deck_aircraft` `0x013ABC` | `0x013ADA`-`0x013ADB` | ported from reading: more than nine lives count as nine | |
| `soldiers_draw` `0x013EEE` | `0x013FA8`-`0x013FB5` | ported from reading: an island neutralised that is not the map's last | |
| `soldiers_draw` `0x013EEE` | `0x013FE8`-`0x013FED` | ported from reading: a soldier turning round at the water | |
| `window_shape` `0x0145A6` | `0x014694`-`0x0146AD` | ported from reading: the shape of a record in the 3-D view | |
| `weapon_hit` `0x0146DC` | `0x014722`-`0x014725` | ported from reading: a hit on slot `0x113`, which it leaves alone; tests/`test_oracle_m5.py`, the hits | |
| `weapon_hit` `0x0146DC` | `0x014788`-`0x01478F` | ported from reading: the draw bit on another of the barracks' records than the third (D1, which nothing reads); tests/`test_oracle_m5.py`, the hits | |
| `weapon_hit` `0x0146DC` | `0x0147A8`-`0x0147AF` | ported from reading: the draw bit on another of the barracks' records than the third (D1, which nothing reads); tests/`test_oracle_m5.py`, the hits | |
| `weapon_hit` `0x0146DC` | `0x0147E8`-`0x0147EF` | ported from reading: the draw bit on another of the barracks' records than the third (D1, which nothing reads); tests/`test_oracle_m5.py`, the hits | |
| `weapon_hit` `0x0146DC` | `0x01493A`-`0x014981` | ported from reading: an island's last pillbox destroyed with no soldier left; tests/`test_oracle_m5.py`, the hits | |
| `target_of` `0x014B54` | `0x014B88`-`0x014B97` | ported from reading: no draw record among the four, no target | |
| `target_of` `0x014B54` | `0x014BC6`-`0x014BCB` | ported from reading: a burnt barracks not in the table, no target | |
| `target_of` `0x014B54` | `0x014BF4`-`0x014BF9` | ported from reading: a dug-out not in the table, no target | |
| `target_of` `0x014B54` | `0x014C2C`-`0x014C31` | ported from reading: a pillbox not in the table, no target | |
| `target_of` `0x014B54` | `0x014C3A`-`0x014C3D` | ported from reading: another slot, no target | |
| `target_refill` `0x014FEE` | `0x01501E`-`0x01501F` | ported from reading: the barracks east of the dug-out, its soldier runs west | |
| `nearest_barracks` `0x015034` | `0x015060`-`0x015061` | ported from reading: the barracks west of the dug-out, the distance negated | |
| `sine` `0x015108` | `0x015122`-`0x015127` | ported from reading: an angle in the second quarter; tests/`test_oracle_m5.py`, the angles | |
| `tangent` `0x01514C` | `0x015156`-`0x015157` | ported from reading: a negative angle; tests/`test_oracle_m5.py`, the angles | |
| `tangent` `0x01514C` | `0x01516C`-`0x01516D` | ported from reading: a negative angle; tests/`test_oracle_m5.py`, the angles | |
| `ticker_say` `0x015624` | `0x015624`-`0x01563F` | ported from reading: an island neutralised that is not the map's last, its message (`0x015624`) | |
| `mission_won` `0x015694` | `0x0156B2`-`0x0156E7` | ported from reading: the rank's last mission won, the promotion (map c) | |
| `bearing_of` `0x015CA6` | `0x015CA6`-`0x015D0B` | ported from reading: the angle of a vector, which only an aimed rocket asks for; tests/`test_oracle_m5.py`, the angles | |
| `load_dash_assets` `0x01653C` | `0x016568`-`0x01656B` | dash.shp missing, fatal; the port loads every container at start-up | |
| `screen_game_restore` `0x016D32` | `0x016D32`-`0x016D79` | ported from reading: the play screen back after the save or the load dialog | |
| `demo_end` `0x01852A` | `0x018536`-`0x01855D` | `0x018536`, saving a recorded demo | M7 |
| `turn_allowed` `0x01AA6E` | `0x01AABE`-`0x01AACD` | ported from reading; tests/`test_oracle_m4.py`, an enemy aircraft that stops a turn | |
| `crash` `0x01AFBA` | `0x01B1A6`-`0x01B1A7` | ported from reading (M4): a wreck sliding along a ship; tests/`test_oracle_m4.py`, the crash and the ground | |
| `crash` `0x01AFBA` | `0x01B1BA`-`0x01B1BB` | ported from reading; tests/`test_oracle_m4.py`, the aircraft down on a ship | |
| `crash` `0x01AFBA` | `0x01B1DC`-`0x01B1E7` | ported from reading; tests/`test_oracle_m4.py`, the attitude levelling out | |
| `crash` `0x01AFBA` | `0x01B200`-`0x01B2A1` | ported from reading; tests/`test_oracle_m4.py`, a wreck sliding along a ship | |
| `hook_state` `0x01B45A` | `0x01B4A8`-`0x01B4AB` | ported from reading; tests/`test_oracle_m4.py`, the hook with the carrier sunk | |
| `on_the_lift` `0x01B4DE` | `0x01B538`-`0x01B56F` | ported from reading; tests/`test_oracle_m4.py`, on the lift facing right | |
| `button` `0x01B5B0` | `0x01B5DA`-`0x01B5E1` | ported from reading: the click inside a turn (attitude 6 to 16) drops nothing | |
| `guns` `0x01B682` | `0x01B6C8`-`0x01B6CB` | ported from reading; tests/`test_oracle_m6.py`, the guns at an enemy aircraft east of the player | |
| `ground_contact` `0x01BA80` | `0x01BB68`-`0x01BB81` | ported from reading; tests/`test_oracle_m4.py`, a bounce off the deck | |
| `deck_state` `0x01BCCE` | `0x01BCEA`-`0x01BCF9` | ported from reading; tests/`test_oracle_m4.py`, the deck state | |
| `deck_state` `0x01BCCE` | `0x01BD86`-`0x01BD91` | ported from reading; tests/`test_oracle_m4.py`, the deck state | |
| `player_motion` `0x01BDFA` | `0x01BF84`-`0x01BF89` | ported from reading; tests/`test_oracle_m4.py`, `player_motion` | |
| `player_motion` `0x01BDFA` | `0x01BFE8`-`0x01BFEF` | ported from reading; tests/`test_oracle_m4.py`, `player_motion` | |
| `flight_controls` `0x01BFF4` | `0x01C074`-`0x01C085` | ported from reading; tests/`test_oracle_m4.py`, the stick in the air | |
| `flight_controls` `0x01BFF4` | `0x01C09C`-`0x01C09F` | ported from reading; tests/`test_oracle_m4.py`, the stick in the air | |
| `flight_controls` `0x01BFF4` | `0x01C12E`-`0x01C131` | ported from reading; tests/`test_oracle_m4.py`, the stick in the air | |
| `flight_controls` `0x01BFF4` | `0x01C200`-`0x01C20D` | ported from reading; tests/`test_oracle_m4.py`, the stick in the air | |
| `flight_controls` `0x01BFF4` | `0x01C2A0`-`0x01C2CD` | ported from reading; tests/`test_oracle_m4.py`, the stick in the air | |
| `flight_controls` `0x01BFF4` | `0x01C326`-`0x01C34F` | ported from reading; tests/`test_oracle_m4.py`, the stick in the air | |
| `deck_controls` `0x01C4E8` | `0x01C5E6`-`0x01C5EB` | ported from reading; tests/`test_oracle_m4.py`, the stick on the deck | |
| `player_update` `0x01C660` | `0x01C8EE`-`0x01C8EF` | ported from reading: state 9 does nothing | |
| `player_update` `0x01C660` | `0x01C934`-`0x01C94B` | the player update's jump table: data | |
| `record_on_ship` `0x01CB34` | `0x01CB50`-`0x01CB51` | ported from reading: a record at the list's end is on no ship | |
| `record_is_land` `0x01CBB2` | `0x01CBEE`-`0x01CBEF` | ported from reading; tests/`test_oracle_m6.py`, an aircraft at rest on a record that is not land | |
| `ship_of_record` `0x01CBF2` | `0x01CC04`-`0x01CC0F` | ported from reading: a debugging line to the console, and 1 | |
| `ship_of_record` `0x01CBF2` | `0x01CC68`-`0x01CCB5` | ported from reading: a debugging line to the console, and 1 | |
| `ingame_keys` `0x01CCF6` | `0x01CD92`-`0x01CD9F` | ported from reading: the save dialog on the carrier | |
| `ingame_keys` `0x01CCF6` | `0x01CE0A`-`0x01CE1D` | ported from reading: the load dialog cancelled | |
| `ingame_keys` `0x01CCF6` | `0x01CE26`-`0x01CE27` | the crash reporter of Control-B, which the port does not have (re/notes/keys.md) | |
| `aircraft_turn` `0x01D562` | `0x01D6BE`-`0x01D6E5` | ported from reading; tests/`test_oracle_m6.py`, a fighter's turn reversed behind the player while he turns | |
| `aircraft_turn` `0x01D562` | `0x01D6EE`-`0x01D703` | ported from reading; tests/`test_oracle_m6.py`, a fighter's turn reversed east of the player while he turns | |
| `aircraft_turn` `0x01D562` | `0x01D742`-`0x01D74B` | the jump table of `aircraft_turn`'s switch: data, not code | |
| `fighter_cruise` `0x01D9C6` | `0x01DB86`-`0x01DBBD` | ported from reading; tests/`test_oracle_m6.py`, a fighter ahead of the player hit by the guns: its evasion | |
| `fighter_cruise` `0x01D9C6` | `0x01DCAC`-`0x01DCB5` | the jump table of `fighter_cruise`'s switch: data, not code | |
| `torpedo_plane` `0x01DEA4` | `0x01DF8C`-`0x01DF97` | ported from reading; tests/`test_oracle_m6.py`, a torpedo plane flying west turning 500 past the deck | |
| `aircraft_falling` `0x01E244` | `0x01E3D2`-`0x01E3D5` | ported from reading; tests/`test_oracle_m6.py`, a fighter shot down and freed off land: one fewer up | |
| `aircraft_burning` `0x01E3E8` | `0x01E404`-`0x01E40D` | ported from reading; tests/`test_oracle_m6.py`, a wreck burning facing east | |
| `aircraft_idle` `0x01E4C8` | `0x01E4C8`-`0x01E4CF` | ported from reading; tests/`test_oracle_m6.py`, state 1, which nothing sets | |
| `aircraft_launch` `0x01E4D0` | `0x01E504`-`0x01E515` | ported from reading; tests/`test_oracle_m6.py`, a torpedo plane already up when another is launched | |
| `aircraft_speed` `0x01E64E` | `0x01E71A`-`0x01E723` | unreachable: slowing towards a want speed of at least 900 lands half the gap and 5 above it | |
| `aircraft_fly` `0x01E728` | `0x01E7BA`-`0x01E7BB` | ported from reading; tests/`test_oracle_m6.py`, a mode that is none of the four | |
| `aircraft_fly` `0x01E728` | `0x01E7D0`-`0x01E7D1` | ported from reading; tests/`test_oracle_m6.py`, a mode that is none of the four | |
| `enemy_aircraft_step` `0x01E7D6` | `0x01E84E`-`0x01E859` | ported from reading; tests/`test_oracle_m6.py`, state 1, which nothing sets | |
| `enemy_aircraft_step` `0x01E7D6` | `0x01E866`-`0x01E869` | ported from reading; tests/`test_oracle_m6.py`, state 8, which nothing sets | |
| `enemy_aircraft_step` `0x01E7D6` | `0x01E87E`-`0x01E87F` | ported from reading; tests/`test_oracle_m6.py`, a state that is none of the five | |
| `lives_gauge_reset` `0x01EDEA` | `0x01EDF4`-`0x01EDF5` | ported from reading; tests/`test_oracle_m4.py`, the gauge resets | |
| `lives_gauge_reset` `0x01EDEA` | `0x01EDFE`-`0x01EDFF` | ported from reading; tests/`test_oracle_m4.py`, the gauge resets | |
| `draw_dashboard` `0x01EE16` | `0x01F102`-`0x01F103` | ported from reading: negative lives count as none | |
| `draw_dashboard` `0x01EE16` | `0x01F10C`-`0x01F10D` | ported from reading: more than nine lives count as nine | |
| `draw_dashboard` `0x01EE16` | `0x01F12E`-`0x01F133` | ported from reading: the lives drum turning down, a life more | |
| `line_draw` `0x021318` | `0x021342`-`0x021343` | ported from reading, PROVISIONAL: the clipping of `line_draw` | |
| `line_draw` `0x021318` | `0x021354`-`0x021357` | ported from reading, PROVISIONAL: the clipping of `line_draw` | |
| `line_draw` `0x021318` | `0x02136A`-`0x02136B` | ported from reading, PROVISIONAL: the clipping of `line_draw` | |
| `line_draw` `0x021318` | `0x02137C`-`0x02137F` | ported from reading, PROVISIONAL: the clipping of `line_draw` | |
| `line_draw` `0x021318` | `0x02138E`-`0x0214EB` | ported from reading, PROVISIONAL: the clipping of `line_draw` | |
| `line_draw` `0x021318` | `0x021556`-`0x021561` | the blitter's busy wait, which the port's line has none of | |
| `line_draw` `0x021318` | `0x0215D0`-`0x0215D7` | ported from reading, PROVISIONAL: a line wholly outside the clip | |
| | run by the original | `0x019152`, `save_game_read`: a saved game loaded | M7 |
| | run by the original | `0x01CDD4`, a loaded game: the briefing and the mission again | M7 |
| | no region: a value | a negative score, in `0x01F26A` | M7 |
| | no region: a value | every soldier record in use, `0x011E82` walks past the table | M5 |
| | no region: a value | a ticker message outside the registered state | M7 |
