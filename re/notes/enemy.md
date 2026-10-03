# The enemy aircraft, the ships and the carrier's defence

What the enemy does in a mission: the enemy aircraft (fighters and torpedo planes), what
launches them, how they fly, attack and are shot down; the enemy ships with their guns,
their aircraft and their sinking; what a torpedo plane does to the carrier and what the
carrier's defence is. Addresses use the standard load layout. This answers the left-over
of `SPEC.md` section 10, point 3 (the state words of the enemy aircraft) and deliverable 1
of M6; how the port takes it is in `re/notes/porting-m6.md`.

Every finding is marked **observed**, with the tool or script that shows it, or **read**,
which means it comes from the listing alone. The scripts are those of
`tools/m6_scripts.py` (`re/notes/porting-m6.md`, "The scripts").

```text
tools/m6_observe.py      maps: the fifteen maps' enemy content at step S; fields, records, states,
                         events: the writes of the aircraft, ship, airfield and gun records with
                         their writers, phases and values, over any script
tools/m6_scripts.py      the scripts, and `trace NAME`: the enemy aircraft and the ships tick by tick
tools/m6_autopilot.py    the plans the scripts were flown with, the dogfight among them
```

The manual describes the enemy on pages 1, 7 and 10 to 11: fighter planes (page 10, it is
not necessary to shoot them all down), torpedo planes that must be shot down or their
torpedoes destroyed to defend the carrier (page 11, with the arrow in the 3-D view), ships
that must be sunk (page 10), and the torpedo run at a ship once its guns are disabled
(page 7). The enemy plane counter tallies a kill icon per plane shot down (page 9).

## The fifteen maps

Read at step S of every map loaded under its own number, its rank chosen in the rank
selection and the mission number poked at its end (observed,
`tools/m6_observe.py maps`). World x is in pixels; a ship's x is the span of its map
records times four; "planes" is the count of its block of deck aircraft, "up to" the most
fighters in the air it lets go (`+0x02` of its block), "while" the player's x its block
names (`+0x04`, `+0x06`); an airfield's parked aircraft and most up come from the table at
`0x0234F4` by map number (`airfields_scan`, `0x012C84`).

| Map | Rank, mission | Islands | Carrier | Enemy ships | Airfields |
|---|---|---|---|---|---|
| a | 0, 1 | 1 | 6592-7360 | none | none |
| b | 0, 2 | 2 | 5672-6440 | none | none |
| c | 0, 3 | 3 | 5440-6208 | none | none |
| d | 1, 1 | 2 | 7016-7784 | none | 3200-3544: 2 parked, up to 1, taking off west |
| e | 1, 2 | 3 | 10320-11088 | none | 15664-16008: 3 parked, up to 1, west |
| f | 1, 3 | 2 | 7976-8744 | cruise ship 5296-5424: 4 guns, 1 hit, 2 planes, up to 1 while x 5096-5616 | none |
| g | 2, 1 | 3 | 10048-10816 | cruise ship 18704-18832: 4 guns, 1 hit, 3 planes, up to 1 while 18504-19024 | none |
| h | 2, 2 | 3 | 12480-13248 | destroyer 21520-22160: 8 guns, 1 hit, 3 planes, up to 1 while 21320-22140 | 6624-6968: 3 parked, up to 1, east |
| i | 3, 1 | 3 | 9736-10504 | destroyer 6544-7184: 8 guns, 1 hit, 4 planes, up to 1 while 6344-7164; cruise ship 17520-17648: 4 guns, 1 hit, 2 planes, up to 1 while 17320-17840 | 3120-3464: 2 parked, up to 1, west |
| j | 3, 2 | 0 | 3520-4288 | destroyer 8-648: 8 guns, 1 hit, 4 planes, up to 2 while -192-628; battleship 7160-7928: 14 guns, 2 hits, 6 planes, up to 2 while 6960-7780 | none |
| k | 4, 1 | 3 | 13968-14736 | battleship 6064-6832: 14 guns, 2 hits, 5 planes, up to 2 while 5864-6684 | 19752-20096: 3 parked, up to 1, west |
| l | 5, 1 | 3 | 9744-10512 | destroyer 14352-14992: 8 guns, 1 hit, 3 planes, up to 2 while 14152-14972; battleship 0-768: 14 guns, 2 hits, 4 planes, up to 2 while -200-620 | 5832-6176: 3 parked, up to 2, west; 19448-19792: 3 parked, up to 2, west |
| m | 6, 1 | 4 | 13320-14088 | battleship 0-768: 14 guns, 2 hits, 5 planes, up to 2 while -200-620; Japanese carrier 22000-22624: 15 guns, 3 hits, 6 planes, up to 3 while 21750-22020 | 3368-3712: 3 parked, up to 2, east; 5192-5536: 3 parked, up to 1, west |
| n | 6, 2 | 3 | 10464-11232 | destroyer 2696-3336: 8 guns, 1 hit, 4 planes, up to 2 while 2496-3316; battleship 0-768: 14 guns, 2 hits, 5 planes, up to 3 while -200-620 | 23000-23344: 4 parked, up to 1, west |
| o | 6, 3 | 3 | 9256-10024 | destroyer 27064-27704: 8 guns, 1 hit, 4 planes, up to 2 while 26864-27684; battleship 20600-21368: 14 guns, 2 hits, 5 planes, up to 2 while 20400-21220; Japanese carrier 8-632: 15 guns, 3 hits, 7 planes, up to 3 while -242-28 | 3672-4016: 4 parked, up to 2, east |

Every map, whatever else it carries, gets torpedo planes from the enemy's countdown (below).
No map has more than four islands: `island_count` (`0x025384`) is at most 4, on map m
(observed, the same command); `islands_draw` (`0x0140E8`) would read its two lists of four
words on past their end for a fifth.

## The enemy aircraft

### The record

`aircraft_records` (`0x02522A`), four records of `0x34` bytes. Every field with its writers
and the phase they write in, over `oil_d`, `cruise_f`, `torpedo_f`, `japcarrier_m`,
`enemy_a`, `battleship_j` and `fight_a` (observed, `tools/m6_observe.py fields`; the
meaning read from the writers named):

| Offset | Field | What it holds | Writers |
|---|---|---|---|
| `+0x00` | state | 0 free, 2 flying, 4 shot down and falling, `0x10` burning on land; 1 and 8 are cases of `enemy_aircraft_step` that nothing sets | `aircraft_launch` 2, `guns` 4, `aircraft_falling` 0x10 or 0, `aircraft_burning` and `aircraft_gone_far` 0, `aircraft_clear` and `mission_reset_tables` 0 (T and M) |
| `+0x02` | mode | 1 a fighter cruising, 2 a fighter on the player's tail, 4 a torpedo plane, `0x10` a torpedo plane that has dropped its torpedo; bit 3 set while it turns (9, `0x0A`, `0x0C`, `0x18`) | `aircraft_launch`, `fighter_cruise`, `fighter_attack`, `torpedo_plane`, `aircraft_motion` (bit 3), `aircraft_turn` (bit 3 cleared), `guns`, `aircraft_falling` (T) |
| `+0x04` | relation | where it is against the player: 1 the same way behind him, 3 the same way ahead of him, 2 the other way east of him, 4 the other way west of him | `aircraft_relation` (T), every tick |
| `+0x06` | hit | 1 when the guns hit it; its flight clears it and starts its evasion | `guns`, `torpedo_plane`, `torpedo_plane_away`, `fighter_cruise` (T) |
| `+0x08` | health | `0xF0` at the launch; the guns take 8 a burst; below `0x60` it is shot down | `aircraft_launch`, `guns` (T) |
| `+0x0A` | burst | the hits still to make a burst: 5 to 7 at the launch, 6 to 9 after each | `aircraft_launch`, `guns` (T) |
| `+0x0C` | order | the place among the aircraft that tail the player (1 the nearest) | `aircraft_order` (T) |
| `+0x0E`, `+0x2A` | | never written but by the clearing | `aircraft_clear` (M) |
| `+0x10` | timer | ticks to the next turn, `0x226` or `0x113` when set | `aircraft_relation`, `fighter_cruise`, `torpedo_plane`, `aircraft_turn` (T) |
| `+0x12` | firing | 1 while a fighter's guns fire at the player | `fighter_attack`, `fighter_cruise` (T) |
| `+0x14` | facing | 1 east, -1 west | `aircraft_launch`, `aircraft_turn` (T) |
| `+0x16` | attitude | the index into `attitude_factor` and the frame, 0 level; a turn runs it to `0x19`, the facing turning at `0x0E` | `aircraft_turn_step`, `aircraft_turn`, `guns` (T) |
| `+0x18` | turn in | ticks to a turn; a hit sets 8 to 13 | `aircraft_motion` (counts), `fighter_cruise`, `fighter_attack`, `torpedo_plane`, `aircraft_turn` (T) |
| `+0x1A` | turns | the turns reversed in their middle (`aircraft_turn`) | `aircraft_turn` (T) |
| `+0x1C` | speed | in hundredths of a pixel a tick, eased towards `+0x1E` | `aircraft_speed`, `aircraft_falling`, `aircraft_launch` (T) |
| `+0x1E` | want speed | set by the mode's flight from the player's airspeed and the distance | the flights of the modes, `aircraft_motion`, `aircraft_speed` (bounds) (T) |
| `+0x20` | x | world x | `aircraft_motion`, `aircraft_launch` (T) |
| `+0x22` | climb | a falling aircraft's climb (`aircraft_motion`) | `aircraft_motion` (T) |
| `+0x24` | want y | the height it flies towards | the flights of the modes, `aircraft_turn`, `aircraft_motion`, `enemy_aircraft_step`, `guns` (T) |
| `+0x26` | y | height above the water | `aircraft_motion`, `aircraft_launch` (T) |
| `+0x28` | distance | the distance to the player, or `0xF0` from a chased torpedo plane | `aircraft_relation`, `torpedo_plane` (T) |
| `+0x2C` | flash | counted up in the pass while it fires; the guns' flash on odd counts | `draw_enemy_aircraft` (F) |
| `+0x2E` | draw x | the drawing's copy of its map offset, `(x >> 3) * 2` | `snapshot_for_draw` (F) |
| `+0x30` | frame | the frame by attitude and facing, 28 a way, `0x1A` level for a torpedo plane | `aircraft_frame_index` (T) |
| `+0x32` | step count | counts the ticks of a turn's step | `aircraft_turn_step` (T) |

Only two fields are written in a pass: `+0x2C` by `draw_enemy_aircraft` and `+0x2E` by
`snapshot_for_draw` (observed, the same command). Everything else is the tick's.

### What each state and mode does (read, and held by the oracle and the closed loop)

`enemy_aircraft_step` (`0x01E7D6`) walks the four records every tick. For each one in use
it takes the relation (`aircraft_relation`, `0x01D3B4`) and the order of those that tail
the player (`aircraft_order`, `0x01D476`), then by the state: 2 flies by its mode
(`aircraft_fly`, `0x01E728`, which first trails smoke by its damage), 4 falls
(`aircraft_falling`, `0x01E244`), `0x10` burns (`aircraft_burning`, `0x01E3E8`); 1 and 8
do nothing. Then the speed is eased (`aircraft_speed`, `0x01E64E`), the aircraft moved by
`aircraft_motion` (`0x01D796`, `re/notes/ffp.md`) unless it burns, and its frame set
(`aircraft_frame_index`, `0x01D35A`). The modes' flights:

- **A fighter cruising** (mode 1, `fighter_cruise`, `0x01D9C6`) goes by its relation.
  Behind the player the same way: within `0xA0` pixels and first in the order it becomes
  mode 2; within `0xA0` otherwise it takes his height and his airspeed less `0x46` a place
  in the order; farther back it closes at his airspeed plus the distance, `0x50` a place
  more for the first and less for the others. The other way east of him it turns, or slows
  to `0x025F52` while he turns; west of him it slows, takes a height `0x20` above or below
  his and turns. Ahead of him the same way it wants his airspeed less a quarter of the
  distance (`0x46` more for each other fighter ahead), jinks between heights of `0x23` and
  `0x5F`, and turns after `0x226` ticks, more than `0x600` pixels ahead, when he turns, or
  8 to 13 ticks after the guns hit it.
- **A fighter on the player's tail** (mode 2, `fighter_attack`, `0x01DCCC`) keeps about
  `0x82` pixels behind at the player's airspeed plus or less `0x32`, flies at his height,
  and fires (`+0x12`) while it is first, level, within `0xA0` pixels and 8 of height; when
  its height equals his, every other tick counts his `+0x10` down, and at its end his oil
  falls by 8 and his fuel by a draw below 32. It turns when he does.
- **A torpedo plane** (mode 4, `torpedo_plane`, `0x01DEA4`) flies at the carrier at 9
  pixels a tick and a height of `0x32`; within `0x3E8` of the carrier's deck it goes down to
  `0x14`, and there, level, it drops its torpedo into `object_record_extra` (`0x025594`,
  type 2, the aircraft's speed times `0x28F` and its facing), becomes mode `0x10`, and sets
  the countdown to 500. Chased from behind it keeps about 150 pixels ahead of the player: it
  wants his airspeed less 240 while farther, and more than his by what the gap lacks of 150
  while nearer; it jinks between `0x23` and `0x5F`, and hit, it turns 8 to 13 ticks later.
  Past the carrier by `0x1F4` it turns back, and away from it it turns when its `+0x10` runs
  out.
- **A torpedo plane that has dropped** (mode `0x10`, `torpedo_plane_away`, `0x01E17A`)
  climbs to `0x3C` at half of `0x025F54` and flies on; behind the player the same way it
  turns, chased and hit it turns 8 to 13 ticks later, and more than `0xA28` from the player
  it is freed (`aircraft_gone_far`, `0x01D18C`).
- **A turn** (bit 3 of the mode, `aircraft_turn`, `0x01D562`, from `aircraft_motion`) runs
  the attitude up a step every third tick; at `0x0E` the facing turns, past `0x19` the turn
  ends. The horizontal speed follows `attitude_factor`, so an aircraft almost stands in
  the middle of its turn.

A fighter in the middle of its turn ahead of the player (state 2, mode 1, relation 3,
attitude 13) stops the player from turning (`turn_allowed`, `0x01AA6E`, read).

### What launches one

Everything goes through `aircraft_launch` (`0x01E4D0`) with a kind, an x, a height and a
facing: it takes the last free record, and for kind 1, a torpedo plane, only when no other
torpedo plane (`+0x03` bit 2) is in the air. Kind 1 gives mode 4 at height `0x32`; kind 0
gives a fighter, mode 1, at the given height, and one more in `fighters_up` (`0x0251D6`).
Every launch: state 2, health `0xF0`, speed and want speed `0x025F52` (900), burst 5 to 7
(read). Three sources:

- **The enemy's countdown**, the player's `+0x1C`: 1350 at the player's reset (`0x01B89A`),
  one less on every tick without a fire bit while the carrier is afloat with hits left; the
  button raises it to 750 when it is lower. At 0, with the player more than `0x1A00` from
  `0x7FFF`, a torpedo plane comes `0x1800` pixels away on the side of the carrier's deck the
  player is on, flying at him (a draw of `rand_beam` decides over the deck) (read; observed
  in `enemy_a` with `tools/m6_observe.py states`: the countdown runs out with the player
  east of the deck, and at tick 1352 the torpedo plane appears 6,144 pixels east of him
  flying west). After it drops its torpedo the countdown is 500 again, so the next one
  comes 500 ticks without the button after each drop (observed in `sunk_a` with
  `tools/m6_observe.py events`: the countdown written by `torpedo_plane` four times).
- **An airfield** (`airfields_step`, `0x011622`): with the player within `0x1E0` of its
  span, fewer fighters up than its most and an aircraft parked, one rolls from its end
  (`+0x08`), a pixel a tick faster every eight ticks up to 7, and at the far end takes off
  as a fighter at height 0; its roll starts a cooldown of 100 ticks (`launch_cooldown`,
  `0x027348`), as a ship's launch does, in which nothing else rolls or is sent up (read;
  observed in `oil_d`, `tools/m6_observe.py states`: `aircraft_launch` makes a fighter at
  tick 612 at x 3196, height 0, which goes onto the player's tail, mode 2, the tick after,
  and turns with him, modes 9 and `0x0A`).
- **A ship** (`ship_launches`, `0x011510`): a ship afloat, not sunk, with the player within
  its block's range and fewer fighters up than its most sends up the aircraft of its last
  block entry at its x and height. The Japanese carrier instead readies one at a time: the
  entry goes on its deck at `0x17C` past its first map offset and height `0x21`, rolls
  west faster and faster (`japcarrier_roll`, `0x02734A`, in sixteenths of a pixel: 8 more
  a tick less a sixteenth of itself, so towards 8 pixels a tick), and takes off at the
  ship's west end (read; observed in `japcarrier_m` and `japcarrier_o`).

### Shot down, and what it scores

The guns (`guns`, `0x01B682`) hit an aircraft that flies the same way ahead of the player
(relation 3) within `0xA0` pixels and `0x14` of height while his pitch target is 0 (level,
the stick left alone): each tick of hits counts `+0x0A` down, and at its end a burst takes
8 of the health, smoke comes off it and `+0x06` is set. The walk tests the relation only,
not the state, and a record that is freed keeps the relation it last had, so a free record
left at relation 3 near the player would be hit too (read; the port does the same, and the
oracle's cases include it). Below `0x60` it is shot down:
350 points, state 4, want y -3. So nineteen bursts, some 110 to 170 ticks of hits, bring
one down (read; observed in `fight_a`, `tools/m6_observe.py states` and `events`: the
torpedo plane launched at tick 5070 loses its health in bursts of 8 from `0xF0` to `0x58`,
`guns` puts state 4 in at tick 8021 and the score takes 350 there, and `aircraft_falling`
counts the kill and frees the record at tick 8096). Every hit starts the aircraft's
evasion, a turn 8 to 13 ticks later, which is why a kill takes many passes.

A falling aircraft (`aircraft_falling`) smokes and comes down; on the ground it slides,
kills soldiers within `0x14`, hits the record under it as a crash does while faster than
500, splashes, and under 100 of speed counts a kill on the enemy plane counter
(`0x02537F`). On land (a record of low bits 2, `record_is_land`, `0x01CBB2`) it burns
(state `0x10`, `aircraft_burning`) for about a hundred ticks and then leaves one of the
wrecks' words (`0x0251DA`, its x, negative facing west, counted in `0x0251D8`) and frees its
record; anywhere else it is freed at once (read; observed in `fight_a`: the kill came east
of map a's end and the record was freed without a wreck). The wreck's word goes to
`0x0251DA` plus twice the count whatever the count is, so a forty-first wreck would be
written into the aircraft records behind the list. `aircraft_burning` frees the record with
one fighter fewer up even for a torpedo plane: the fall cleared the mode when the burning
began. `draw_enemy_aircraft` draws the wrecks at `view_y` less 4, a height of 15 over the
sea.

The fall on land, observed in `burning_a` (`tools/m6_scripts.py trace burning_a`), where a
fighter shot down high over map a's island is poked into the first record after the
mission's reset of its tables, as the guns leave one (state 4, want y -3, one fighter up):
it falls west, comes to rest on the island at tick 500 at x 3239, slides to 3218, counts
the kill at tick 510 and burns (state `0x10`, `+0x1E` 6, `+0x1C` `0x1E`), and at tick 610
leaves the wreck's word -3218 with the count 1 and frees the record, `fighters_up` from 1
to 0.

## The ships

### The record

`ship_records` (`0x025460`), five of `0x1E` bytes: the destroyer, the battleship at
`0x02547E`, the cruise ship at `0x02549C`, the Japanese carrier at `0x0254BA`, the player's
carrier at `0x0254D8`; `ship_order` (`0x02555A`) walks them as destroyer, carrier,
battleship, cruise ship, Japanese carrier. `map_scan` fills them from the slot that
introduces each (`0xE4`, `0x10D`, `0xCC`, `0xF2`, `0x21`) (read, and observed as the only
writer at step S, `tools/m6_observe.py records`):

| Offset | What it holds | Destroyer | Battleship | Cruise ship | Japanese carrier | Carrier |
|---|---|---|---|---|---|---|
| `+0x00`, `+0x02` | the span of its map offsets | | | | | |
| `+0x04` | afloat | `0xFFFF` | `0xFFFF` | `0xFFFF` | `0xFFFF` | `0xFFFF` |
| `+0x06` | its gun list (`ship_guns_setup`) | | | | | |
| `+0x0A` | guns | 8 | 14 | 4 | 15 | |
| `+0x0C` | hits left | 1 | 2 | 1 | 3 | 4 |
| `+0x0E` | deck height | `0x1B` | `0x1B` | `0x1C` | `0x15` | `0x21` |
| `+0x12` | its score when sunk | 2500 | 4500 | 1000 | 6000 | 0 |
| `+0x14` | how far it has sunk | 0 | 0 | 0 | 0 | 0 |
| `+0x16`, `+0x18` | the sinking's ticks per row and their decrease | 20 | | 20 | 20 | |
| `+0x1A` | the rows its records ride down by: the drawing's copy of the sinking (`snapshot_for_draw`, F) | | | | | |
| `+0x1C` | its first slot in `MasterList` (`load_ship_shapes`) | `0xD0` | `0xF8` | `0xB8` | 0 | 0 |

### Its guns

A gun list entry is `0x0E` bytes: `+0x04` its world x (the ship's first map offset times four
plus the table's word), `+0x06` its height over the deck, `+0x08` destroyed, `+0x0A` the
puffs of smoke still to come, `+0x0C` the passes to the next (read, `ship_guns_setup` and
`ship_guns_draw`). In every pass with the player off the deck (`ship_guns_draw`,
`0x014C3E`) every gun of every enemy ship afloat and not sunk:

- **shells** the aircraft (`ship_gun_shell`, `0x014EFC`): when a draw of `rand_beam` modulo
  512 exceeds its distance from the player, and he is no higher than `0xC8`, six times in
  sixteen a splash goes into the water within 32 pixels of him, and a torpedo within ten
  pixels of it goes out, his or a torpedo plane's (`torpedoes_hit`) (read; observed in every
  ship script: 257,623 entries over the M6 scripts, `tools/reach_observe.py`);
- is drawn with its frame by distance and height, as a target's gun is (`target_range_frame`,
  `0x81` on, seven more when firing), and **fires** as a target does (`target_fire`,
  `0x014F5C`): smoke from the engine and in the end oil and fuel (observed: the oil falls in
  `cruise_f`, `destroyer_h` and the other ship scripts);
- destroyed, **smokes** for `0x32` puffs.

A rocket, a falling torpedo or a crash that comes down on a ship destroys its first standing
gun within 16 pixels of the hit: the flash white then red, 200 points (read, `weapon_hit`,
`0x0149DC`; observed in `rockets_f`, `crash_f` and `crash_side_f`, +200 each).

### The torpedo run and the sinking

A torpedo that meets the sea gently runs in it (`re/notes/porting-m5.md`) and hits the first
record that is not sea; on a ship a running torpedo flashes the sky red and takes one of the
ship's hits, and at 0 its sinking starts (`+0x18` 20) (read, `weapon_hit` `0x0149A6`;
observed in `torpedo_f`, `tools/m6_observe.py events`: dropped at 24 pixels east of map f's
cruise ship, it runs into it at tick 600, the sky flashes white and red, the ship's hits go
to 0 and its sinking starts at 20). The manual asks for the ship's guns to be disabled
first (page 7); the code does not: the hit counts whatever the guns do (read).

A ship whose hits are 0 sinks (`ships_sinking`, `0x011CAE`, `ship_sinking`, `0x011CD8`):
every `+0x16` ticks it goes a row deeper, the interval falling by one each time. Ten rows
down an enemy ship scores its `+0x12`, the ticker says so (`ship_sunk_message`,
`0x015640`: the format at `0x023AD8` with the ship's name, chosen by its score from the
four at `0x023BA8`, and the score), and one ship fewer is left; with no ship and no island
left the mission is won. What tells the carrier from an enemy ship is its score of 0: the
`beq` after the row's step reads the flags of the `move.w` of `+0x12` that comes between
it and the `cmpi.w #1` of the rows (read; the oracle's cases include both). At `0x78` rows it is gone and its map
records are cleared (read; observed in `torpedo_f`: 19 ticks later a row, then fewer; the
score +1000, the cruise ship's `+0x12`, at tick 763; its hits -1 and its records cleared at
tick 928).

## The carrier's defence

The player's carrier has four hits (`+0x0C` of `carrier_record`). A torpedo plane's
torpedo that runs into it takes one, as the player's do a ship's (observed,
`tools/m6_observe.py events`: in `enemy_a` the torpedo plane drops at tick 2014 and its
torpedo takes the carrier from 4 hits to 3 at tick 2183, flashing the sky white and red; in
`sunk_a` four torpedoes, at ticks 2084, 3127, 4172 and 5992). Sunk, it goes down as a ship
does; at every row while the player is aboard (in the hold, `0x025394` 1) he is put back
on the lift (deck state `0x0B`, `0x025394` 2, the weapon menu down, the attitude level),
`0x21` rows down with the aircraft on its deck he goes into the sea, his lives are taken and
the game-over count starts at 100, and the enemy's countdown stops (read; observed in
`sunk_a`: the sinking from tick
5992, the carrier gone at tick 6320, and the game's end at tick 6420 after the aircraft
came down on the sunken deck and into the sea). What defends the carrier is the
manual's (page 11): shoot the torpedo plane down before it drops, or destroy
its torpedo on the way - the guns' bullets, a bomb or a rocket within reach, or a ship's
shell, take out a torpedo in the water (`torpedoes_hit`, `0x011AE2`, which walks the extra
record whatever its type). An arrow in the 3-D view points to the first torpedo plane that
has not yet dropped (the mode's low three bits 4; none after the drop), west or east of the player (`enemy_arrows`, `0x01F21A`; observed in `enemy_a`,
`countdown_b` and `countdown_c`).

## The crash on a ship

A crash onto a ship's deck leaves the wreck at rest there, burning (the player's state 8,
observed in `crash_f`: the aircraft comes down on map f's cruise ship at x 5318 and rests
on its deck, bobbing with the swell). A crash into its hull below the deck slides the wreck back along
it with the sky's flash, `flash_set(7, 0xF00)` from `crash` (observed in `crash_side_f`:
the call at tick 516, then the aircraft in the sea).

## Open

- An enemy aircraft shot down over land by play: no flight reached it. Over map a's island
  the dug-outs' fire takes the oil during the chase; against the airfields' fighters of
  maps d and e, seven dogfight plans of up to 15,000 ticks (`re/notes/porting-m6.md`, "The
  scripts") brought none down, because a fighter jinks down to 35 pixels over land, where
  the chase flies into the ground, and a fighter on the aircraft's tail takes its oil. The
  fall, the burning and the wreck's word are held through the poke of `burning_a`.
- States 1 and 8 of the aircraft record: cases of `enemy_aircraft_step` that nothing sets.
- `aircraft_speed`'s floor at 900 when slowing (`0x01E71A`) is dead: slowing towards a
  want speed of at least 900 lands half the gap and 5 above it (read).
