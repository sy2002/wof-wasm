Chapter 13
{ .chapter-kicker }

# The world

Chapter 3 gave the map files a sentence; this chapter opens them. By its end you will know what a world is to the game, a strip of small records and nothing else; what each of a record's sixteen bits is for; how a position in the world becomes a position on the screen; why the world never scrolls but is painted anew in every pass; what the game's logic reads from the map; and what the loader builds from it for each mission. Each mechanism ends with what the port made of it and the instrument that holds it.

## A world in one file

Each mission's world is one file, `maps/a.map` to `maps/o.map`: two numbers of four bytes, then [**map records**](../glossary.md#map-record) to the end of the file. A map record is a word of two bytes that stands for eight pixels of the world, from west to east: whether a shape stands there, which, and what lies under it. The map is the strip of them, and nothing else is in the file: no list of targets or ships, no picture of an island; a ship too is a run of records. Whatever else a mission needs, the loader builds from the strip.

`map_load` picks the file by the rank and the mission number (which map a mission gets is chapter 17's matter) and reads the two numbers. The first is the file's own length in bytes, and the loader takes it as the length of the record list too. The second is a byte offset into the records that falls on the carrier's deck. Four times it is the world x of the record it names, since a record is two bytes and covers eight pixels, and the player's aircraft starts eight pixels west of that, one record's width.

The loader reads eight bytes more than the file holds, so the last four records of every map never come from it. They are zero, because the game's own code asks the system for cleared memory on every allocation, as chapter 4 told. Why the eight bytes are asked for is not known, and nothing depends on the answer; what the game does rely on is that the memory it is given starts at zero, and a zero record draws nothing and gives no ground. The port clears its record list, a fixed table of the [core](../glossary.md#core)'s state, before reading the file into it, and its arena hands out zeroed memory too, the rule chapter 22 states. One test parses every map of the disk and finds nothing left over; another finds the map the first mission loads in the [headless original](../glossary.md#headless-original) equal to the file, word for word.

The fifteen maps differ in length and in what they carry; a, b and c are the first rank's three missions. The records include the four zero ones, a map is eight pixels wide for each, and a record with the draw flag, the next section's, may draw a shape.

| Map | Records | Width, pixels | The player's start, world x | Records with the draw flag | Islands | Enemy ships | Airfields |
|---|---|---|---|---|---|---|---|
| a | 955 | 7,640 | 7,032 | 89 | 1 | none | none |
| b | 1,751 | 14,008 | 6,112 | 172 | 2 | none | none |
| c | 1,951 | 15,608 | 5,880 | 238 | 3 | none | none |
| d | 1,795 | 14,360 | 7,456 | 213 | 2 | none | 1 |
| e | 2,135 | 17,080 | 10,760 | 259 | 3 | none | 1 |
| f | 1,744 | 13,952 | 8,416 | 157 | 2 | cruise ship | none |
| g | 2,359 | 18,872 | 10,488 | 226 | 3 | cruise ship | none |
| h | 2,775 | 22,200 | 12,920 | 281 | 3 | destroyer | 1 |
| i | 2,869 | 22,952 | 10,176 | 263 | 3 | destroyer, cruise ship | 1 |
| j | 997 | 7,976 | 3,960 | 19 | 0 | destroyer, battleship | none |
| k | 2,650 | 21,200 | 14,408 | 215 | 3 | battleship | 1 |
| l | 2,523 | 20,184 | 10,184 | 222 | 3 | destroyer, battleship | 2 |
| m | 3,569 | 28,552 | 13,760 | 282 | 4 | battleship, Japanese carrier | 2 |
| n | 2,932 | 23,456 | 10,904 | 183 | 3 | destroyer, battleship | 1 |
| o | 3,468 | 27,744 | 9,696 | 251 | 3 | destroyer, battleship, Japanese carrier | 1 |

Every map carries the player's carrier; map a, the shortest, is about twenty-four screens wide.

## The record, bit by bit

The project's [**map decoder**](../glossary.md#map-decoder), [`tools/map_decode.py`](repo:tools/map%5Fdecode.py), a reader of the map files written apart from the port, takes a record apart with a mask and a shift for each of its four fields:

```python
--8<-- "generated/listings/py/fields.py"
```

Bit 15 is the [**draw flag**](../glossary.md#draw-flag): only a record that carries it puts its shape on the screen. Bit 14 is never set. Bits 13 to 11 are the record's height field, 0 to 7, which despite its name moves the shape down the screen from the horizon's row, four rows a step. Bits 10 to 2 are the [slot](../glossary.md#slot) of chapter 12, in `MasterList` at full scale or `AthList` at the eighth scale, the two tables that turn a slot into a shape. Bits 1 and 0 say what lies under the record: 2 land, 1 a ship's deck, 0 open sea, where nothing stands.

![A palm over its four columns, numbered 15 to 18, and the four records' bits, the third with bit 15 set.](../generated/figures/maprecord-palm.png)

/// caption
Records 15 to 18 of map a, the four columns of one palm: each carries the palm's slot and height field, and the third alone the draw flag.
///

A shape wider than eight pixels covers several records; all carry its slot and one carries the flag, most often the third, so the shape is drawn once, its [hotspot](../glossary.md#hotspot) on that record's x. The other columns are not wasted: the ground-height routine of a later section reads the slot and ignores the flag, so a palm four records wide stands in the way under all four.

/// figures
| Where the draw flag sits | Drawn records on land |
|---|---|
| The third column of its shape: two of its slot to the left | 1,756 |
| The fourth | 664 |
| The second | 110 |
| The first, or the only one | 317 |
| All | 2,847 |
///

Of the 34,473 records, 3,070 carry the flag: those on land, 215 on ships and 8 over open sea. Not every one has a shape to draw: 45 name a marker slot, and 413 a bump of land that has a shape only at the eighth scale.

Only the palms and that bump, slots 6 to 9, have a height field other than 0, so an island's palms stand on different rows. The waves and the island's ground, drawn after them over the rows from the horizon down, hide more of a lower palm's trunk, and the palms rise from the shore to different heights. At the eighth scale the field is unused and every record stands on row 151.

A null entry of chapter 12's tables draws nothing. The tables hold 278 entries and the game fills 273; the five past them, 273 to 277, stay null, and the maps use them as markers that draw nothing. A pair of `0x111` and `0x112` stands at the two ends of every ship, a pair of `0x114` and `0x115` marks an airfield for the loader, and `0x113` marks where an island's flag stands; the flag is drawn beside that record as one of its extras, the shapes a record adds beside its own.

The low bits let a ship sink row by row while the record list stays as it is; a ship's run of records never moves along the strip, it sinks in place. A drawn record whose low bits are 1 is lowered by the ship whose span of the record list holds it, by the rows the ship has sunk and the swell. Of all the records, 2,677 carry these low bits, all within ships' spans, most without the flag. The low bits also tell the tick what lies under an object when a weapon lands or the aircraft comes down: open sea, land or a deck (chapters 14 and 15).

![Map a in eight bands: palms, barracks and dug-outs on the left, then sea, the carrier from the seventh band into the eighth.](../generated/figures/map-a.png)

/// caption
Map a as the strip of its drawn records, in bands of 960 pixels, three screens' width, the last one shorter: the island on the left, the carrier on the right; the island's ground between its beaches is not a record.
///

The figure shows map a, the first mission's world, whose shapes all come from `world.shp`; the later maps' ships come from [shape containers](../glossary.md#shape-container) of their own. [The map viewer](../maps.md) of this book shows every map with its records drawn in place, and the decoder's reading of the fields is held by its prediction of every draw, told below.

## From the world to the screen

Positions in a mission are [**world coordinates**](../glossary.md#world-coordinates): x in pixels from the map's west end, eight to a record, and y in pixels upward from the [**water line**](../glossary.md#water-line), the sea's surface, where y is zero. The screen counts its rows downward, so a conversion stands between the two.

Once in every [pass](../glossary.md#pass), before anything is drawn, `frame_update` works out where the screen lies in the world, from a copy of the player's position taken for the drawing, so that the whole pass draws from one position. At full scale:

- the screen's left edge, `view_x`, lies 160 pixels west of the player, so the aircraft is always at screen x 160, the middle of the playfield's 320;
- a shape's screen x is its world x less `view_x`;
- its screen y is `view_y` plus 11, less its world y, so the water line lies 11 rows below `view_y`;
- `view_y` is the horizon's row: row 151 while the aircraft is no higher than 131, and one row further down for each pixel it climbs above that.

Chapter 11's [split line](../glossary.md#split-line) is this row clamped to 162, the playfield's last, so the three are one row until the aircraft climbs above 142. Above a height of 131 the horizon sinks as the aircraft climbs, so the aircraft keeps its row on the screen; lower, it rises and falls. At the [eighth scale](../glossary.md#eighth-scale-view) `view_y` is 1,208, both screen coordinates are divided by eight and `view_x` lies 1,280 pixels west, which puts the aircraft at 160 again; the horizon's row is then 151 at any height.

`draw_world_shape`, chapter 12's helper for every shape the objects draw, makes this conversion and draws a shape only while its screen x lies from −128 to 448: that is the routine's rule.

![The playfield over a strip of records, the aircraft at screen x 160, the window from −128 to 448 marked under the strip.](../figures/world-view.svg)

/// caption
Where the world meets the screen at full scale: the records a pass draws reach past both edges of the playfield, from the one 288 pixels west of the aircraft.
///

The map's own loop in `draw_world` does the same arithmetic in its own words. It starts with the record 288 pixels west of the aircraft, at screen x −128 or a few pixels further left, steps one record at a time, eight screen pixels apart (one at the eighth scale, from eight times as far west), and stops with the first record past screen x 448: nearly the helper's window.

Both loops of chapter 8 compare `view_x` and `view_y` after every pass, and the decoder, below, holds the draws they place; the helpers that find the record under a world x are held under the [oracle](../glossary.md#oracle) at every world x where a record starts, on five maps.

## A picture painted anew

The world appears to scroll as the aircraft flies, but nothing scrolls: no pass copies the last picture and shifts it, and the Amiga's hardware scrolling is not used either. Every pass paints the [playfield](../glossary.md#playfield) anew from the map: first the sky in colour 1, from the top down to the horizon's row, then the strip, record by record, then the layers.

On the left, the record is read and shifted right by two; its draw flag, now bit 13, is tested and cleared (`bclr.b #$d,d1`), and a record without it gets only its extras. Shifted back and masked (`and.w #$7fc,d1`), the record leaves the slot times four, a pointer's size: the offset of its entry in the table, with no multiplication; a null entry is passed by. The row is 151 at the eighth scale (`move.w #$97,d1`), else the horizon's row in D5 plus four rows a step of the height field. After the extras the loop steps on and ends with the first record past screen x 448 (`cmp.w #$1d0,d4`, the screen x plus eight against 464). On the right, the decoder's `draw_list` is the same loop in Python.

//// html | div.listing-pair

/// html | div
```wingslst
--8<-- "generated/listings/asm/draw_world_loop.lst"
```
///

/// html | div
```python
--8<-- "generated/listings/py/draw_list.py"
```
///

////

A record's extras belong to its place: a burnt barracks smokes for a while, at both scales; at full scale the carrier's flag flies beside its tower's record, its lift, which raises the aircraft from the hold (chapter 14), beside each of its two lift records, and an island's flag beside the record of slot `0x113`. Walking the places on the screen, the loop needs no search for them.

After the strip come `draw_world`'s layers, always in this order: the aircraft waiting on the carrier's deck, one for each life left but the one flying; the one on the lift; the player's; the enemy aircraft and their wrecks; the guns of the dug-outs, the pillboxes and the enemy ships; the aircraft parked on the airfields and on the ships' decks; the waves; and last the islands. Drawn last, the waves and the islands' ground cover whatever lies below the horizon's row, the palms' trunks among it. Then `frame_update` draws the rest over the world: the smoke, the soldiers, the splashes, the objects in flight, the weapon marker in the hold, the balloons and, when a game ends, its sign (chapters 15 and 16).

The sea at full scale is one frame of the wave animation, drawn five times, 96 pixels apart; the frame steps through twelve as the passes go by, and its place follows the player's x, so that the waves move with the world. At the eighth scale it is a band of colour 10. An island is its two beaches, slots 1 and 2, at the world x of its drawn beach records, with colour 17, the island's ground, filled between them from the horizon's row down. An airfield in use shows its parked aircraft and the one rolling to take off (chapter 16).

The picture below comes from the island run, made for this book: a take-off and a turn west, flown by the stick's letters as chapter 8's scripts are.

![The play screen: the aircraft in a blue sky, palms over the island's ground, the waves, the dashboard.](../generated/figures/world-island.png)

/// caption
The first mission at VBlank 3500 of the island run, about 57 seconds into the mission: the aircraft at world x 3,381 of map a, 109 pixels up, at full scale. Look at the palms rising from the shore to different heights, the island's ground and the waves.
///

Painting anew fits the game, though no note says why it was chosen: the horizon's row moves with the aircraft's height and the scale changes at a height, so a copied picture would have to be remade then anyway; and the playfield is [double-buffered](../glossary.md#double-buffering) (chapter 11), so the screen a pass draws into last showed the picture of two passes before, which painting from the map makes irrelevant. The port, with no [blitter](../glossary.md#blitter), paints the same way per pixel into its [indexed framebuffer](../glossary.md#indexed-framebuffer), routine by routine and in the same order.

The decoder holds no data of the game; it reads the map files when it runs. Over a flight of 684 passes in the headless original, from the deck to the eighth scale, it predicts every draw the original made from the map, slot and position, in order, pass for pass: over five thousand draws. A [control](../glossary.md#control) of chapter 8's kind changes the map instead of the port: a drawn record of the carrier in map a gets another of the carrier's slots and another height field, laid over the disk:

```python
--8<-- "generated/listings/py/test_a_changed_map_changes_exactly_the_draws_the_decoder_says.py"
```

The prediction holds for every pass; every pass whose draws differ is one it predicted, and the aircraft's x is the same pass for pass, since a carrier's slot takes its ground from the deck whatever its height field. In both loops of chapter 8 the port's map draws are compared after every pass of the [mission scripts](../glossary.md#mission-script) with the decoder's prediction from the records as the original then holds them.

## The ground under the aircraft

In a flight without weapons the tick reads the map for one thing, the [**ground height**](../glossary.md#ground-height): how high what stands at a record reaches, asked for under an object. A run of the headless original with a hook on every read of the map, over a take-off and 568 ticks of flight without a weapon fired, found inside the ticks only the ground-height routine, against more than a hundred thousand reads by the drawing. When a weapon lands, a splash is made or the aircraft comes down, the tick also reads a record's slot and low bits, and a hit rewrites records (chapters 14 and 15). One value more comes from the drawing of the world, a distance the ground guns' sound takes, one of chapter 7's [couplings](../glossary.md#coupling). The picture is never read, so the logic is the same whether anything is drawn or not, as chapter 2 told.

/// figures
| Who read the map in that run | Reads |
|---|---|
| The mission's setup, its walks | 2,865 |
| The tick: the ground height | 547 |
| The pass: the strip | 71,635 |
| The pass: the map in the [dashboard](../glossary.md#dashboard)'s 3-D window | 48,639 |
| The pass: two small routines | 76 |
///

`ground_height` answers in three ways. For six classes of slot, the class's height from a table of six words in the executable, less the height field: one pixel a step, while the picture moves four rows a step. For a ship's slot, the ship's deck height less how far it has sunk and less the swell, and over the carrier's whole deck less the lift's value as well (chapter 14), so a deck's ground follows its ship. For every other slot, zero: the beaches, an island's plain ground and the sea all lie at height zero, and the tick's ground is the height of what stands there.

| Class | Slots | Height |
|---|---|---|
| A palm | 6 | 36 |
| A palm | 7 | 35 |
| A palm, and one more shape of the islands | 8, `0x0B` | 35 |
| A dug-out | 3 | 9 |
| A barracks | 4 | 13 |
| A pillbox, in any state | `0x0F` to `0x1E` | 12 |

On the left, the three answers: zero (`moveq #$0,d0`); a ship's deck, its height at `0x0E` less how far it has sunk at `0x14` less the swell, the carrier also less the lift; a class's height, the class number doubled to index the table and the height field, bits 11 to 13, taken off. On the right, the port's switch does the same.

//// html | div.listing-pair

/// html | div
```wingslst
--8<-- "generated/listings/asm/ground_height_answers.lst"
```
///

/// html | div
```c
--8<-- "generated/listings/c/wof_ground_height_switch.c"
```
///

////

Under the oracle of chapter 5 the original's routine is held to that formula over 600 random records, with random ships and swell, and the port's to the original's for every record of five maps, the ships' decks at random heights.

## What the loader builds

`map_scan` walks the record list twice and turns its records into the game's objects: the targets, the soldiers, the islands and the ships; a scan of its own, run first, takes the airfields' markers. The first walk looks at the drawn records only. It counts the barracks, the dug-outs and the pillboxes, the islands by their east beaches, and what the briefing will name. It fills the five ship records, each from the first drawn record of a slot that marks that ship: the span of the record list the ship covers, and fixed values for the rest; for an enemy ship also the block of aircraft parked on its deck, from a table by map number.

The tables are then sized by those counts, the soldiers five to each barracks and dug-out, and the second walk fills them: each target's place in the record list and its island, and the dug-outs' and the barracks' world x; each island's two beach records, in two short lists from which the drawing places the beaches; each island's span of dug-outs, and its two counts, the soldiers alive and the pillboxes standing. What the targets and the soldiers do with them is chapter 15's; the airfields' fighters are chapter 16's.

A hit rewrites the record list, and nothing else does. A bombed barracks' four records turn from slot 4 into slot 5, the burnt barracks, and a pillbox's four records into another of its states, each keeping its draw flag and its low bits. So the map a mission ends with is not the file's, and the burnt barracks is drawn, and smokes, from the records themselves. Chapter 3 told that a saved game carries them.

The port keeps every one of these tables at a fixed place with a fixed capacity, cleared where the original asks for cleared memory, and a test holds the capacities against all fifteen maps. The setup is compared at step S, chapter 6's [dump](../glossary.md#dump) after the setup, on each map loaded as the mission it belongs to, not laid over another map's file: every registered value and table equal, `map_scan`'s among them.

## What the port made of it

The port keeps the records as the original's sixteen-bit words, read with the same shifts and masks. Where the original holds a pointer into the map, the port holds the byte offset, which a saved state can carry. Beside it stands the decoder, against which the original's draws and the port's are held alike.

/// dev
The routines: `map_load` `0x012ADC`, `map_scan` `0x012D5A`, the airfields' scan `0x012C84`, `draw_world` `0x013772`, the record's extras `0x013B1C`, `draw_world_shape` `0x015174`, `ground_height` `0x015714`, `ship_at_offset` `0x014A4E`, `islands_draw` `0x0140E8`, `airfields_draw` `0x013A18`; in the tick, `map_slot_at` `0x0150C8`, a record's slot and low bits under a world x, and `on_water` `0x01CB74`.

The second walk of `map_scan` reads one record past the end of the list: its counter starts at the list's length in bytes and loses one twice a record, the second time in `dbmi` at `0x0131BE`. The port's table, 3,576 words, is a few records longer than the longest map, m, with the record the second walk reads past the end among them. No map has more than four islands, and the drawing would read past the beaches' lists of four for a fifth.

A wreck's x taken from the address where the allocator put the record list, which the port carries as an input, is chapter 20's story. In the port: [`src/mission.c`](repo:src/mission.c), [`src/world.c`](repo:src/world.c), [`src/tick.c`](repo:src/tick.c), [`src/mission.def`](repo:src/mission.def).
///

## What comes next

The chapter in one sentence: a world is a strip of two-byte records, one for every eight pixels, which the game paints anew in every pass and from which the tick takes the height of the ground and what lies under an object. Chapter 14 turns to the player, who flies over this strip, takes off from the carrier and lands on it.

## Further reading

- [`re/notes/map.md`](repo:re/notes/map.md), the whole note.
- [`re/notes/drawing.md`](repo:re/notes/drawing.md), ["Other drawing"](repo:re/notes/drawing.md#other-drawing) and ["The scene routines"](repo:re/notes/drawing.md#the-scene-routines).
- [`re/notes/porting-m4.md`](repo:re/notes/porting-m4.md), ["The mission setup"](repo:re/notes/porting-m4.md#the-mission-setup), ["The map loader"](repo:re/notes/porting-m4.md#the-map-loader) and ["The pass"](repo:re/notes/porting-m4.md#the-pass).
- [`re/notes/enemy.md`](repo:re/notes/enemy.md#the-fifteen-maps), "The fifteen maps"; [`re/notes/objects.md`](repo:re/notes/objects.md#the-order-of-a-pass), "The order of a pass".
- [`SPEC.md`](repo:SPEC.md#35-file-formats), section 3.5, "File formats", its paragraph "Maps".
- [`tools/map_decode.py`](repo:tools/map%5Fdecode.py); [`src/world.c`](repo:src/world.c) and [`src/mission.c`](repo:src/mission.c), their comments on `draw_world`, `map_load` and `map_scan`; [`tests/test_map.py`](repo:tests/test%5Fmap.py) and [`tests/test_oracle_m4.py`](repo:tests/test%5Foracle%5Fm4.py).

Outside the repository: the [*Amiga Hardware Reference Manual*](https://archive.org/details/commodore-amiga-tech-ref-series-amiga-hardware-reference-manual-3rd-edition), its chapter "Playfield Hardware", for the hardware scrolling the game does not use.
