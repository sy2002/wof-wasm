# The object system

Answers point 3 of `SPEC.md` section 10. Addresses use the standard load layout.

Every finding is marked **observed**, with the run that shows it, or **read**, which means it
comes from the listing alone.

```text
tools/object_observe.py   the inventory, the draw order, the player's record, the controls
tests/test_objects.py     the claims of this note over short scripts, in the suite
```

## The inventory

Every table of records the game logic keeps. "Walked in" says which tree steps through the
whole table every tick or every pass.

| Table | Where | Record | Records | Built by | Walked in the tick | Walked in the pass |
|---|---|---|---|---|---|---|
| the player | `player_record` `0x027DEC` points at `0x025078` | `0x1E` | 1 | `0x013684` | `0x01C660` | `snapshot_for_draw`, `0x0103A6` |
| `object_records` | `0x024CAE`, in DATA | `0x2A` | 15 and one more at `0x025594` | `0x013756` clears them | `0x010A72`, `object_spawn` | `0x0106BE`, `0x010702`, `snapshot_for_draw` |
| `aircraft_records` | `0x02522A`, in DATA | `0x34` | 4 | `0x01E608`, `0x0135A8` | `0x01E7D6`, `0x01B682` (their guns), `0x012132` | `snapshot_for_draw`, `0x010DA6`, `0x014206` |
| `ship_records` | `0x025460`, in DATA | `0x1E` | 5 | `map_scan` | `ground_height`, `0x011510`, `0x011CAE`, `0x01B45A`, `0x01BC02` | `ride_on_ship`, `0x014206`, `0x01409C`, `0x01526E` |
| `airfield_records` | `0x0252FA`, in DATA | `0x14` | 4 | `0x012C84`, `0x013554` | `0x011622` | `snapshot_for_draw`, `0x013A18` |
| Ricochet | `ricochet_records` `0x026EA4` | 4 | 20 | `alloc_pools` | none: its writer `0x011A14` has no caller | |
| Splashes | `splash_records` `0x026F30` | 4 | 20 | `alloc_pools` | `0x0119BC`, `0x0152B0` | `0x0152F8` |
| Smoke | `smoke_records` `0x026F58` | `0x14` | 40 | `alloc_pools` | `smoke_at_player` | `0x010EE0`, `smoke_claim`, `player_lost_restart` |
| Balloons | `balloon_records` `0x026F66` | `0x12` | 20 | `alloc_pools` | `0x011C5E` | `0x01557C`, which fills them after a promotion |
| `soldier_records` | `0x025500` | 8 | five per target | `map_scan` | `0x011E82`, `0x011A8C` | `0x013EEE` |
| `target_records_4` | `0x0254F8` | `0x10` | one per slot-4 record | `map_scan` | `0x011DE4` | `draw_world`, `0x011E82`, `0x014FEE`, `0x015034` |
| `target_records_3` | `0x0254FC` | `0x10` | one per slot-3 record | `map_scan` | `0x011DE4`, `0x011E82`, `0x0146DC`, `0x014B40` | `draw_world`, `0x013D78`, `0x013EEE` |
| `target_records_f` | `0x025504` | `0x0E` | one per slot-`0x0F` record | `map_scan` | not allocated by map `a` | |

The four pools are the allocations `alloc_pools` (`0x01283E`) makes once at start-up under the
debug names `Ricochet`, `Splashes`, `Smoke` and `Balloons`; their sizes, `0x50`, `0x50`,
`0x320` and `0x168`, divided by the strides their walkers step with give the record counts
above (read, and confirmed by the stride the write summary finds in a run).

Every "walked in" entry is a routine the read hook saw touch that table in that phase over
the runs of `tools/object_observe.py`; a table the runs never reached is marked so.

## The architecture

### Claiming and freeing a record

There is no allocator. Every table carries a byte or word that says whether a record is in
use, and a spawn walks the table for the first one that is free (read):

| Table | The field | Claimed by | Freed by |
|---|---|---|---|
| `object_records` | `+0x20`, the kind byte | `object_spawn` `0x010820`, which walks the fifteen for the first zero and fills the record | `clr.b +0x20` in `0x010AA6` and in `0x010702`, inside a pass |
| Smoke | `+0x10`, the kind word | `smoke_claim` `0x015460`, which walks all forty | its own walkers, by clearing `+0x10` |
| Balloons | `+0x11` | `0x01557C` | `0x011C5E`, by clearing `+0x11` |
| Splashes, Ricochet | `+0x02` | `0x0152F8`, `0x011A14` | their walkers |
| `soldier_records` | `+0x06`, the state word | `0x011E82` | `0x013EEE`, by putting state 3 in |
| `aircraft_records` | the state word at `+0x00` | `aircraft_launch` `0x01E4D0`, which takes the last free record | `aircraft_falling`, `aircraft_burning`, `aircraft_gone_far` in `0x01E7D6`'s walk; `aircraft_clear` `0x01E608` at the mission's start (observed, `tools/m6_observe.py fields`, `re/notes/enemy.md`) |

`object_spawn` simply returns when all fifteen records are in use, so the game silently
drops a shot when its table is full. It has more than one entry: the one at `0x010820` leaves
kind 8, and two `st.b` sites inside it leave `0xFF`. `object_free_unused` (`0x0107D4`) is a
scan for a free record that nothing calls. The two spawn helpers the drawing and the tick
share, `smoke_claim` (`0x015460`) and `smoke_at_player` (`0x0154E0`), are the only ones
reached from both trees.

Over twenty bombs, every one of the fifteen records has its kind byte written by
`object_spawn` inside a tick and by `0x013756` at the mission's start, and the ones that went
out while the run lasted were freed by `0x010702` inside a pass (observed,
`tests/test_objects.py::test_an_object_record_is_claimed_and_freed_through_its_kind_byte`).

### What decides a record's behaviour

Not a table of routines and not a switch: **a chain of tests**. `0x010A72` walks the fifteen
object records and the sixteenth, skips a record whose kind byte is zero and hands the rest to
`0x010AA6`, which tests the kind byte against 8 and then the word at `+0x22` against 0, 1 and
2, and the frame byte at `+0x1E` against `0x0A`. So `+0x22` is the object's type and `+0x20`
its state: `0xFF` while it flies, 8 while it is going out, 0 when the record is free
(observed over the bombing run, where a fire tap puts `0xFF` into a free record, the record
becomes 8 about thirty ticks later and 0 a few ticks after that).

### Record layout, the fields that all of them share

`re/notes/drawing.md` named `+0x1A`, `+0x1E` and `+0x22` for the animation. The two larger
pools keep position and velocity as 32-bit fixed point with sixteen fractional bits (read from
`smoke_claim` and from the Balloons walker `0x011C5E`, which adds `+0x08` to `+0x00` and
`+0x0C` to `+0x04` as longs):

```text
Smoke, 0x14 bytes          Balloons, 0x12 bytes
+0x00 long  x, 16.16       +0x00 long  x, 16.16
+0x04 long  y, 16.16       +0x04 long  y, 16.16
+0x08 long  dx, 16.16      +0x08 long  dx, 16.16
+0x0c long  dy, 16.16      +0x0c long  dy, 16.16
+0x10 word  the kind       +0x11 byte  in use
+0x12 word  6 at the claim
```

Splashes and Ricochet are four bytes: a word at `+0x00`, the world x; the count of passes
still to run at `+0x02`, 0 when the record is free; and at `+0x03` the low bits of the map
record at that x, which `map_slot_at` gives the claim (read, `0x0152C8` and `0x011A28`; held
to the original over random states by `tests/test_oracle_m5.py`, `splash_spawn`).

An `object_records` record keeps its position as longs in 16.16 as well, whose whole words
are what the drawing copies (observed over one bomb of the bombing run, from the tick it was
dropped to the tick it went out, and read from `object_step`, `0x010AA6`):

| Offset | What the run shows |
|---|---|
| `+0x00` | long, world x in 16.16 (the whole word at `+0x00`); it moves by the long at `+0x0E` every tick |
| `+0x04` | long, world y in 16.16 (the whole word at `+0x04`, the fraction at `+0x06`); it falls faster and faster |
| `+0x08`, `+0x0A` | words, the drawing's copy of the position, which `snapshot_for_draw` takes |
| `+0x0E` | long, the horizontal speed in 16.16, `-9` for a bomb dropped while flying left at 10; it loses a tenth of its whole part every tick |
| `+0x12` | long, the vertical speed in 16.16: `0xFFFFA000` at the drop and `g_025350` (`0x6000`) less every tick, three eighths of a pixel per tick |
| `+0x16`, `+0x1A` | longs, a rocket's thrust, twice the cosine and the sine of its bearing, which it adds to its speeds every tick once it fires; `+0x1A` also takes the pass a weapon comes down in |
| `+0x1E` | byte, the animation frame, counting 0 to 11; `0x0A` for a torpedo running in the water, which is not drawn |
| `+0x1F` | byte, the torpedo's facing at the drop, and the low bits of the map record a weapon comes down on, which choose the explosion or the splash |
| `+0x20` | byte, the kind: `0xFF`, then 8, then 0 |
| `+0x21` | byte, the frames counted while it goes out |
| `+0x22` | word, the type: 0 a rocket, 1 a bomb, 2 the torpedo |
| `+0x24` | word, a rocket's fall in ticks before it fires, 4, 8 or 12 |
| `+0x26`, `+0x28` | words, a rocket's half bearing and the airspeed at the drop, which its aim uses |

The launch, the flight, the aim and the hits are in `re/notes/porting-m5.md`, "The tick".

**The fall.** Every tick the height becomes the high word of `+0x12 + (+0x04 << 16 | +0x06)`
and only the word at `+0x04` is written back; nothing ever writes `+0x06`, which stays 0. So
the height moves by the whole part of the vertical speed, rounded down, and the speed's
fraction never carries (read, `0x010B76` to `0x010B86`; observed by
`tools/m5_observe.py fall`, which checks that rule for every tick of every bomb and torpedo in flight of five
scripts and finds it held in every case, with `+0x06` always 0). **The type** is the
`weapon_type` (`0x0253A4`) at the drop: rockets, bombs, torpedo in the weapon menu's order,
0, 1, 2 (read, `0x01089C`; observed by the same command, every record carrying the weapon
type of its drop in the bomb, rocket and torpedo scripts of `tools/m5_scripts.py`). The
guns' rounds are no object record.

### The order of a tick

`logic_tick` (`0x011386`) pops one input byte and then calls a fixed list, in this order
(read; every entry that walks a table is named in the inventory above):

```text
input_queue_pop                  the tick's input byte
0x0112B0, 0x011460               only while 0x026D3E says so
0x01C660    the player           calls player_motion and, in the water, 0x01AF7C
0x01E7D6    the enemy aircraft   calls aircraft_motion for every live record
0x012132    the sound engine     takes the distance draw_world left at 0x027164
0x01B682    the ships            five records, their guns
0x012066, 0x011274
0x011BFC    the engine smoke     smoke_at_player, by chance
0x010A72    the object records   0x010AA6 for every record whose kind byte is set
0x0119BC    splashes and ricochets
0x011622, 0x011510, 0x011CAE, 0x011DE4
0x011C5E    the balloons
```

### The order of a pass

The drawing calls of one pass of the bombing run, by the routine that made each one, with the
table each routine was seen to read (observed, `tools/object_observe.py --draw-order`):

```text
draw_world                the sky, then the map strip, with 0x013B1C's extras between records
0x013ABC                  through draw_world_shape
0x0103A6                  the player's aircraft and the only lines
0x013D78                  the slot-3 targets of the map
0x013E6C
0x0140E8
0x010EE0                  the Smoke pool
0x013EEE                  the soldiers, which it also moves and kills
0x014564                  the map window of the dashboard
```

`snapshot_for_draw` (`0x010F88`) runs before all of them, between `Forbid` and `Permit`. It
writes six bytes at `+0x08` to `+0x0D` of every one of the sixteen object records and the word
at `+0x2E` of every aircraft record, and it reads the player's `+0x00`, `+0x02`, `+0x14` and
the five trail words `+0x1E`, `+0x22`, `+0x26`, `+0x2A` and `+0x2E`, and puts the player's
position into `0x026E5C` and `0x026E60`, which `draw_world` and `frame_update` build the view
from (observed: it writes exactly those bytes of every record in every pass, 657 times in a
330-tick run).

## The player's record

`player_record` (`0x027DEC`) always points at `0x025078`; `0x01B7EC` sets both at a reset. The
record is `0x1E` bytes. Every field below is observed over the flights of
`tools/object_observe.py --player`, with the routine the write summary names as its writer.

| Offset | Name | Unit | What the run shows | Writer |
|---|---|---|---|---|
| `+0x00` | `player_y` | pixels above the water | moves by `+0x18`: **every one of the 413 ticks in the air** of the flight, and 340 of the 344 of the climb, the other four being the ceiling below | `player_motion`, `0x01C5F4`, `0x01C660` |
| `+0x02` | `player_x` | world pixels | moves by `+0x16` times `+0x14`: **every tick in the air** of both flights | `player_motion`, `0x01BDBA`, `0x01B7EC` |
| `+0x04` … `+0x0B` | | | the frame: at `+0x04` the pointer to its shape record, at `+0x08` its name, which `aircraft_frame` (`0x01ABDE`) gives; they move while the aircraft turns | `0x01C378`, `0x01B7EC` |
| `+0x0C` | `player_on_deck` | | 1 on the carrier, 0 in the air, and 4, 6, 8 and 11 through the lift and the restart | `0x0112B0`, `0x01C5F4`, `0x01C660` |
| `+0x0E` | `player_fuel` | | `0xC0` at a reset, one less every 28 ticks in the air, never while the aircraft stands in the hold, and never upward | `logic_tick` |
| `+0x10` | | | `rand_beam` modulo 4 plus 6 at the reset, constant afterwards | `0x01B7EC` |
| `+0x12` | `player_oil` | | `0x80` at a reset and constant while nothing shoots; the smoke spawn and the dashboard read it, which is the oil pressure of the manual's page 8 | `0x01B7EC` |
| `+0x14` | `player_facing` | | `+1` or `-1`; the horizontal speed is multiplied by it | `player_lost_restart`, `0x01AB80`, `0x01C4E8` |
| `+0x16` | `player_speed_x` | pixels per tick | what `player_motion` computes from the airspeed and the attitude | `player_motion`, `0x01BDBA` |
| `+0x18` | `player_speed_y` | pixels per tick | the same for the climb | `player_motion` |
| `+0x1C` | `enemy_countdown` | ticks | `1350` at the reset (`0x546`, `player_reset`) and `1349` after the setup's own tick, one less on every tick whose input byte has **neither** fire bit, and never on a tick that has one: 249 moves and 319 stands in a 568-tick run with the guns firing, with no exception | `0x01BC02` |

The words directly behind the record, from `0x025096`, are not part of it: they are the
ships' blocks of deck planes, 160 words that `ship_block` (`0x01252C`) fills in the setup for
each enemy ship the map carries (the destroyer's at word 0, the battleship's at `0x40`, the
cruise ship's at `0x60`, the Japanese carrier's at `0x80`) and that `snapshot_for_draw`
copies to `0x024F38` in every pass (read, and compared on every map at step S and after
every pass of the five scripts, `re/notes/porting-m4.md`).

The two position rules hold with the speed the tick **ends** with, because `player_motion`
writes each speed and applies it in the same tick. They are stated for the ticks the aircraft
is in the air, and the exceptions outside that are all accounted for (observed over the
`flight` and `climb` runs, 1,236 ticks):

- **on the lift and on the deck** (`+0x0C` of 11 and 1) the aircraft is moved by the deck code
  and not by `player_motion`: in the flight that is 31 ticks of the lift raising it a pixel a
  tick with both speeds at zero, and 13 ticks of the roll, where x advances by one more than
  the speed. Those are every exception the flight has.
- **at the ceiling** `player_motion` clamps the height to 1100 instead of adding the speed
  (`re/notes/ffp.md`). In the climb that is exactly four ticks, 367 to 371, each with y already
  at 1100; they are the only in-air exceptions in either run.

The globals around it, and the three names `re/notes/ffp.md` left open:

| Where | Name | What the runs show |
|---|---|---|
| `0x025414` | `airspeed` | it scales both speed components; it rises by `airspeed_step` to a ceiling of `1400` and falls to a floor of `1000`, and below `1000` the aircraft sinks. No separate control sets it: the stick towards the facing raises it by `airspeed_step` to 1,400 (`0x01BFF4`), which the manual's page 5 calls full throttle, and `object_spawn` copies it into a new object's `+0x28`, which is a shot taking the aircraft's speed with it. It is therefore the **airspeed**, not a throttle setting |
| `0x027DEA` | `airspeed_step` | how much the airspeed moves per tick: `0x01C0B2` takes one off it with a floor of 4, `0x01C132` and `0x01C534` add one with a ceiling of 8, and `player_motion` subtracts `SPFix` of the across sine, which is 0 at every pitch the game reaches (the table's values are below 1 but at 90 degrees, and the targets are clamped to −4,500 and 3,000), so that line changes nothing. Right after them the airspeed moves by exactly that much (observed over 171 of 190 changes in two flights; the rest are the take-off ramp and the two bounds) |
| `0x025F16` | `pitch_step` | how far `pitch_target` moves per tick. It stood at 600 through every flight, and the only writers are the cheat keys `i` and `k`, which add and subtract 50 (`re/notes/keys.md`). It is a tuning value, not state |
| `0x025AAA` | `landing_stall` | 1 while the stick is forward alone and the aircraft flies left: `0x01BFF4` then eases `pitch_target` to `+600`, the manual's stall (page 6), and clears it on every other input; `player_motion` eases the pitch towards `0xFCE0` while it is set and the target stands at `+600`; `0x01BA80` lands the aircraft on the deck only with it set, and the guns' splashes (`0x0119BC`) are left out while it is. Observed set in the turns and landing scripts of `re/notes/porting-m4.md` |

## The other tables, as far as the runs show

Only what the seven scripts of `re/notes/passes.md` reached; the details of each kind belong
to the notes of M5 and M6.

- **`aircraft_records`** (`0x02522A`, four records of `0x34`): `0x01E608` clears them at the
  mission's start, `0x01E7D6` walks them every tick and calls `aircraft_motion` for every
  record whose state word is neither 0 nor `0x10` (`re/notes/ffp.md`), and
  `snapshot_for_draw` writes `+0x2E` of each. What the state words mean (2 flying, 4 shot
  down, `0x10` burning on land; 1 and 8 are set by nothing), every field with its writers,
  and what launches an aircraft are in `re/notes/enemy.md`, observed over the M6 scripts of
  `tools/m6_scripts.py`; the countdown at the player's `+0x1C` needs 1,350 ticks without the
  button.
- **`ship_records`** (`0x025460`, five records of `0x1E`): `map_scan` fills them from the map,
  `+0x00` and `+0x02` are the span of map offsets the ship covers, `+0x0E` and `+0x14` give
  its deck height to `ground_height`, and `+0x1A` is the row every map record of low bits 1
  is moved down by. In the tick `0x011510`, `0x011CAE`, `0x01B45A` and `0x01BC02` read
  `+0x04`, `+0x0C` and `+0x12` of them; `0x01B682`, which walks five records of its own, works
  on `aircraft_records`.
- **`soldier_records`** (five per target record of the map, eight bytes each): `+0x06` is the
  state, 0 free, 1 running, 2 dying, 3 dead; `+0x03` a frame; `+0x04` a frame timer; `+0x05`
  the island the soldier belongs to. `0x013EEE` runs them in the pass: it counts the timer
  down, advances the frame, and at frame 7 puts state 3 in, adds `0x19` to `player_score` and
  takes one off `island_score`. Observed in the bombing run: a bomb on a dug-out (slot 3) at
  tick 850 put six of the twenty into state 1 and the score rose by 200, what a hit on a
  dug-out with soldiers inside scores; a hit on a barracks (slot 4) scores 150
  (`tools/m5_scripts.py`'s `bomb_a`, re/notes/porting-m5.md).
- **`target_records_4`** and **`target_records_3`** (`0x10` bytes each, one per map record of
  slot 4, a barracks, and slot 3, a dug-out): `+0x00` the draw record's byte offset in the
  map as a long, `+0x04` and `+0x06` the world x of the ends soldiers come out at, for slot
  3 x − 44 and x + 16, `+0x08` the soldiers inside, 5 at the start, `+0x09` the island
  number, `+0x0A` the soldiers still to come out and `+0x0B` the timer that lets them out
  (`0x011DE4`), `+0x0C` and `+0x0E` two counts: for a dug-out the passes it hides after a
  soldier ran into it empty and the passes to its next soldier from a barracks, for a burnt
  barracks its puffs of smoke and the passes between them. What each kind does is in
  re/notes/porting-m5.md, "The targets and the soldiers".
- **Ricochet** has one writer, `0x011A14`, and nothing in the executable calls it: its
  far-call slot at `0x023054` is named by no instruction (read). None of the seventeen M5
  scripts writes the pool (observed, `tools/m5_observe.py pools`). It is dead.
- **Balloons** are released by `0x01557C` in the pass while `balloons_on` (`0x02535D`) is set,
  and moved by `0x011C5E` in the tick. Only the promotion at the end of a rank's last mission
  sets `balloons_on` (`0x0156CC`); of maps a to c only map c can give one, with all three of
  its islands neutralised. The next mission's `mission_reset_tables` clears it, so the
  balloons fly from the promotion until the aircraft is back on the deck (read). The M5
  script `balloons_c` pokes `balloons_on` on map c, and the pool is written by `0x01557C`
  and `0x011C5E` alone (observed, the same command; re/notes/porting-m5.md).

## The controls

For every table a scripted input can reach, a pair of runs that differ in that one input,
compared over their whole state (`tools/object_observe.py --controls`, observed):

| The one input | What differs |
|---|---|
| a bomb dropped or not | `object_records` 566 bytes, the player's record 2, and 60 bytes elsewhere |
| the guns held or not | no table at all: 2 bytes of the player's record and 31 elsewhere |
| climbing or level | no table: 12 bytes of the player's record and 54 elsewhere |
| over the bow or lifting off | `object_records` 70 bytes, Splashes 22, the player's record 30, and 1,434 elsewhere |
| a barracks hit or not | `object_records` 540 bytes, `soldier_records` 43, Smoke 40, `target_records_3` 8, `target_records_4` 1, the player's record 3, and 96 elsewhere |

The 60 bytes beside the object table in the first pair are, one by one: `weapon_count`
(`0x02536D`), which starts a mission at **30** and loses one for every bomb — the manual's
"thirty 100 lb. bombs" — the sound engine's slots, the ticker, the blitter's parameter block
and the clip rectangle. Nothing else differs.

The 96 beside the tables in the last pair are `player_score`, `weapon_count`, `rand_state`,
the ticker's message and the sound engine's slots, the dashboard's per-buffer cache and the
blitter's parameter block. That pair — the bombing run of `re/notes/passes.md` against the
same flight with the button never pressed — is the one that reaches the soldiers and the
targets, and it reaches no other table.

**The machine gun writes none of these tables.** Holding the button changes only the player's
own record and the sound; it is the other weapon, the short click, that fills
`object_records`. The crash over the bow is what fills Splashes. No pair of runs reached
Ricochet or Balloons.

## What the width of a port looks like

For planning M5 and M6: the routines of each kind, their sizes from `re/functions.csv`, and
whether a kind could be driven under the oracle with a record as its input.

| Kind | Routines | Bytes | C or asm | Shares | Testable in isolation |
|---|---|---|---|---|---|
| the player | `0x01C660` 802, `player_motion` 506, `0x01BFF4` 900, `0x01C378` 368, `0x01C4E8` 268, `0x01B7EC` 216, `0x01AF7C` 62 | 3,122 | C | `mathffp`, `rand_beam` | yes: the record and the globals are all in DATA, and `player_motion` already is |
| object records | `0x010AA6` 768, `object_spawn` 378, `0x01099A` 216, `0x010702` 210, `0x010EE0` 166, `0x0106BE` 68, `0x010A72` 52, `0x0107F2` 46 | 1,904 | asm | `draw_world_shape`, `ground_height`, `map_slot_at` | yes, with the map in memory |
| the map | `map_scan` 1,134, `draw_world` 428, `ground_height` 388, `map_load` 226, `ride_on_ship` 60, `map_slot_at` 58, `ship_at_offset` about 150 | 2,444 | asm | the shape tables | yes: `ground_height` and `map_slot_at` are pure given the globals |
| enemy aircraft | `aircraft_motion` 560, `0x01B682` 314, `0x01E7D6` 226, `0x01D35A` 90, `0x01E608` 70 | 1,260 | C | `mathffp`, `rand_beam` | yes, once a script brings one up |
| soldiers | `0x013EEE` 430, `0x011E82` 204, `0x011A8C` 78, `0x015AE8` 46 | 758 | asm | `draw_world_shape` | yes, after `map_scan` has built the table |
| the pools | `0x01557C` 168, `smoke_at_player` 122, `smoke_claim` 108, `0x0152F8` 98, `0x0119BC` 88, `0x011C5E` 80, `0x0152B0` 72 | 736 | asm | `rand_beam` | yes; they are small and take only their own records |
| ships and airfields | `0x012C84` 214, and the five records `map_scan` fills | 214 | asm | the map | yes |
| the restart | `player_lost_restart` 172 | 172 | asm | the blitter library, `WaitTOF` | no: it draws and waits |

`ship_at_offset` is one routine that the inventory cuts in two: `re/functions.csv` gives
`0x014A4E` a span of 4 because it falls through into `0x014A52`, and the two together are
about 150 bytes. Sizes of routines that only a kind's handler calls are counted once.

## Open

- `0x025AAA`, above.
- What `+0x04` to `+0x0B` of the player's record hold; `0x01C378` writes all four words and
  the drawing reads them.
- The promotion in a run: only map c with its three islands neutralised gives one on
  maps a to c, which no script reaches; its balloons are observed with `balloons_on` poked
  (re/notes/porting-m5.md, "The left-overs").
