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
| the player | `player_record` `0x027DEC` points at `0x025078` | `0x30` | 1 | `0x013684` | `0x01C660` | `snapshot_for_draw`, `0x0103A6` |
| `object_records` | `0x024CAE`, in DATA | `0x2A` | 15 and one more at `0x025594` | `0x013756` clears them | `0x010A72`, `object_spawn` | `0x0106BE`, `0x010702`, `snapshot_for_draw` |
| `aircraft_records` | `0x02522A`, in DATA | `0x34` | 4 | `0x01E608`, `0x0135A8` | `0x01E7D6`, `0x01B682` (their guns), `0x012132` | `snapshot_for_draw`, `0x010DA6`, `0x014206` |
| `ship_records` | `0x025460`, in DATA | `0x1E` | 5 | `map_scan` | `ground_height`, `0x011510`, `0x011CAE`, `0x01B45A`, `0x01BC02` | `ride_on_ship`, `0x014206`, `0x01409C`, `0x01526E` |
| `airfield_records` | `0x0252FA`, in DATA | `0x14` | 4 | `0x012C84`, `0x013554` | `0x011622` | `snapshot_for_draw`, `0x013A18` |
| Ricochet | `ricochet_records` `0x026EA4` | 4 | 20 | `alloc_pools` | `0x011A14` (read only) | |
| Splashes | `splash_records` `0x026F30` | 4 | 20 | `alloc_pools` | `0x0119BC`, `0x0152B0` | `0x0152F8` |
| Smoke | `smoke_records` `0x026F58` | `0x14` | 40 | `alloc_pools` | `smoke_at_player` | `0x010EE0`, `smoke_claim`, `player_lost_restart` |
| Balloons | `balloon_records` `0x026F66` | `0x12` | 20 | `alloc_pools` | `0x011C5E` (read only) | `0x01557C` (read only) |
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
| `aircraft_records` | the state word at `+0x00` | `0x01E608` | `0x01E7D6` |

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

Splashes and Ricochet are four bytes: a word at `+0x00`, the in-use byte at `+0x02` and a
random byte at `+0x03` that their walkers take from `rand_beam`.

An `object_records` record keeps whole pixels instead (observed over one bomb of the bombing
run, from the tick it was dropped to the tick it went out):

| Offset | What the run shows |
|---|---|
| `+0x00` | word, world x; it moves by the word at `+0x0E` every tick |
| `+0x04` | word, world y; it falls faster and faster |
| `+0x08`, `+0x0A` | words, the position of the previous tick |
| `+0x0E` | word, the horizontal speed, `-9` for a bomb dropped while flying left at 10 |
| `+0x12` | long, `0xFFFFA000` at the drop and `0x6000` less every tick, which is three eighths of a pixel per tick in 16.16 |
| `+0x1E` | byte, the animation frame, counting 0 to 11 |
| `+0x20` | byte, the kind: `0xFF`, then 8, then 0 |
| `+0x22` | word, the type, 1 for a bomb |

How exactly `+0x12` moves `+0x04` is not established: the fall is not the plain sum of the
velocity, and the fraction is kept somewhere this reading did not find.

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
record is `0x30` bytes. Every field below is observed over the flights of
`tools/object_observe.py --player`, with the routine the write summary names as its writer.

| Offset | Name | Unit | What the run shows | Writer |
|---|---|---|---|---|
| `+0x00` | `player_y` | pixels above the water | moves by `+0x18` every tick, 516 of 568 ticks | `player_motion`, `0x01C5F4`, `0x01C660` |
| `+0x02` | `player_x` | world pixels | moves by `+0x16` times `+0x14`, 554 of 568 ticks | `player_motion`, `0x01BDBA`, `0x01B7EC` |
| `+0x04` … `+0x0B` | | | four words the drawing reads; they move while the aircraft turns | `0x01C378` |
| `+0x0C` | `player_on_deck` | | 1 on the carrier, 0 in the air, and 4, 6, 8 and 11 through the lift and the restart | `0x0112B0`, `0x01C5F4`, `0x01C660` |
| `+0x0E` | `player_fuel` | | `0xC0` at a reset, one less every 28 ticks in the air, never while the aircraft stands in the hold, and never upward | `logic_tick` |
| `+0x10` | | | `rand_beam` modulo 4 plus 6 at the reset, constant afterwards | `0x01B7EC` |
| `+0x12` | `player_oil` | | `0x80` at a reset and constant while nothing shoots; the smoke spawn and the dashboard read it, which is the oil pressure of the manual's page 8 | `0x01B7EC` |
| `+0x14` | `player_facing` | | `+1` or `-1`; the horizontal speed is multiplied by it | `player_lost_restart`, `0x01AB80`, `0x01C4E8` |
| `+0x16` | `player_speed_x` | pixels per tick | what `player_motion` computes from the airspeed and the attitude | `player_motion`, `0x01BDBA` |
| `+0x18` | `player_speed_y` | pixels per tick | the same for the climb | `player_motion` |
| `+0x1C` | `enemy_countdown` | ticks | `1349` at the start of a mission, one less on every tick whose input byte has **neither** fire bit, and never on a tick that has one: 249 moves and 319 stands in a 568-tick run with the guns firing, with no exception | `0x01BC02` |
| `+0x1E` … `+0x2E` | `player_trail` | | five words four apart that `snapshot_for_draw` reads in every pass; **no run saw anything write them**, so what fills them is open | — |

The globals around it, and the three names `re/notes/ffp.md` left open:

| Where | Name | What the runs show |
|---|---|---|
| `0x025414` | `airspeed` | it scales both speed components; it rises by `airspeed_step` to a ceiling of `1400` and falls to a floor of `1000`, and below `1000` the aircraft sinks. The game has no throttle control — the manual's controls are the stick and the button — and `object_spawn` copies it into a new object's `+0x28`, which is a shot taking the aircraft's speed with it. It is therefore the **airspeed**, not a throttle setting |
| `0x027DEA` | `airspeed_step` | how much the airspeed moves per tick: `0x01C0B2` takes one off it with a floor of 4, `0x01C132` and `0x01C534` add one with a ceiling of 8, and `player_motion` takes the climb out of it. Right after them the airspeed moves by exactly that much (observed over 171 of 190 changes in two flights; the rest are the take-off ramp and the two bounds) |
| `0x025F16` | `pitch_step` | how far `pitch_target` moves per tick. It stood at 600 through every flight, and the only writers are the cheat keys `i` and `k`, which add and subtract 50 (`re/notes/keys.md`). It is a tuning value, not state |
| `0x025AAA` | — | **open.** `0x01BFF4` sets it to 1 wherever it eases `pitch_target` to `+600`, and clears it in two other places; `player_motion` and the splash walker `0x0119BC` read it. No flight of the seven scripts ever saw it set, so what it means is not established and it is left unnamed |

## The other tables, as far as the runs show

Only what the seven scripts of `re/notes/passes.md` reached; the details of each kind belong
to the notes of M5 and M6.

- **`aircraft_records`** (`0x02522A`, four records of `0x34`): `0x01E608` clears them at the
  mission's start, `0x01E7D6` walks them every tick and calls `aircraft_motion` for every
  record whose state word is neither 0 nor `0x10` (`re/notes/ffp.md`), and
  `snapshot_for_draw` writes `+0x2E` of each. The state words `1`, `2`, `4`, `8` and `0x10`
  are still only read. No script brought an enemy aircraft up: the countdown at the player's
  `+0x1C` needs about 1,350 ticks without the button, which only `tools/ffp_observe.py`'s
  `zeros` script reaches.
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
  takes one off `island_score`. Observed in the bombing run: a bomb on a barracks at tick 850
  put six of the twenty into state 1 and the score rose by 200.
- **`target_records_4`** and **`target_records_3`** (`0x10` bytes each, one per map record of
  slot 4 and slot 3): `+0x00` the map offset as a long, `+0x04` and `+0x06` the world x, for
  slot 3 as a span from x − 44 to x + 16, `+0x08` a state byte that starts at 5 and `+0x09`
  the island number. The tick reads `+0x0A` and `+0x0B` in `0x011DE4` and the pass reads and
  writes `+0x08` and `+0x0C`.
- **Ricochet** (`0x011A14` in the tick) and **Balloons** (`0x01557C` in the pass, `0x011C5E`
  in the tick) were **never written by any of the seven scripts**; they are listed here as
  read, with the routines that would write them. Ricochet takes a `rand_beam` byte per
  record, which suggests bullets glancing off a ship, and no script ever shot at one.

## The controls

For every table a scripted input can reach, a pair of runs that differ in that one input,
compared over their whole state (`tools/object_observe.py --controls`, observed):

| The one input | What differs |
|---|---|
| a bomb dropped or not | `object_records` 566 bytes, the player's record 2, and 60 bytes elsewhere |
| the guns held or not | no table at all: 2 bytes of the player's record and 31 elsewhere |
| climbing or level | no table: 12 bytes of the player's record and 54 elsewhere |
| over the bow or lifting off | `object_records` 70 bytes, Splashes 22, the player's record 30, and 1,434 elsewhere |

The 60 bytes beside the object table in the first pair are, one by one: `weapon_count`
(`0x02536D`), which starts a mission at **30** and loses one for every bomb — the manual's
"thirty 100 lb. bombs" — the sound engine's slots, the ticker, the blitter's parameter block
and the clip rectangle. Nothing else differs.

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
- The state words of `aircraft_records` and everything about an enemy aircraft beyond
  `aircraft_motion`: no script of this note brought one up.
- Ricochet and Balloons, which no script filled.
- What `+0x04` to `+0x0B` of the player's record hold; `0x01C378` writes all four words and
  the drawing reads them.
- How `+0x12` of an object record moves `+0x04`, which the bomb's fall does not explain as a
  plain sum.
- Which kind each value of an object record's `+0x22` is: 0, 1 and 2 are tested, and a bomb
  carries 1.
