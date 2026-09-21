# The maps and the world coordinate system

Answers point 5 of `SPEC.md` section 10. Addresses use the standard load layout.

Every finding is marked **observed**, with the run or test that shows it, or **read**, which
means it comes from the listing alone.

```text
tools/map_decode.py    the decoder: the file, the records, and the draws of a pass
tests/test_map.py      the tests, part of the suite
```

## The file

`maps/a.map` … `maps/o.map`, one per mission. `map_load` (`0x012ADC`) picks the file with the
rank and the mission number, reads two longs, allocates and reads the record list, and calls
`map_scan` (`0x012D5A`) (read, and observed for map `a`).

```text
+0  u32  the file's own length, which is also the length of the record list in bytes
+4  u32  the byte offset of the carrier's first record
+8  u16 records to the end of the file
```

- `map_length` (`0x0253C6`) takes the first long, `map_records` (`0x024628`) the allocation,
  `map_records_end` (`0x02462C`) its last record, and `map_extent` (`0x024630`) the first
  long times four, which is the world x past the last record.
- `player_start_x` (`0x025392`) is the second long times four less eight.
- **The loader reads eight bytes more than the file holds.** It allocates and asks for
  `length` bytes of records although only `length - 8` follow the header, so the last four
  records of every map never come from the file. **They are zero records everywhere**, not
  undefined memory: the game's own allocator `0x020874`, which every `mem_alloc` goes through,
  sets bit 16 of the flags it hands `AllocMem` (`bset #$10,d0` at `0x020884`), which is
  `MEMF_CLEAR`, and the two entries above it already push `0x10001` and `0x10003` (read). The
  harness's fresh memory reads the same way. A zero record draws nothing and gives ground
  height zero. The last record of the list is read by the draw loop but never drawn, because
  the loop tests the pointer after it has been advanced. Observed for all 15 maps
  (`test_every_map_of_the_disk_parses_without_a_byte_left_over`).

  For the port this is a rule, not a curiosity: **its arena has to hand out zeroed memory**,
  because every allocation the game makes asks for `MEMF_CLEAR` and the game relies on it
  here.

All 15 maps parse with nothing left over (observed):

| Map | Bytes | Records | Player x | Extent | Records that draw |
|---|---|---|---|---|---|
| a | 1,910 | 955 | 7,032 | 7,640 | 89 |
| b | 3,502 | 1,751 | 6,112 | 14,008 | 172 |
| c | 3,902 | 1,951 | 5,880 | 15,608 | 238 |
| d | 3,590 | 1,795 | 7,456 | 14,360 | 213 |
| e | 4,270 | 2,135 | 10,760 | 17,080 | 259 |
| f | 3,488 | 1,744 | 8,416 | 13,952 | 157 |
| g | 4,718 | 2,359 | 10,488 | 18,872 | 226 |
| h | 5,550 | 2,775 | 12,920 | 22,200 | 281 |
| i | 5,738 | 2,869 | 10,176 | 22,952 | 263 |
| j | 1,994 | 997 | 3,960 | 7,976 | 19 |
| k | 5,300 | 2,650 | 14,408 | 21,200 | 215 |
| l | 5,046 | 2,523 | 10,184 | 20,184 | 222 |
| m | 7,138 | 3,569 | 13,760 | 28,552 | 282 |
| n | 5,864 | 2,932 | 10,904 | 23,456 | 183 |
| o | 6,936 | 3,468 | 9,696 | 27,744 | 251 |

The kinds that occur per map are what `tools/map_decode.py` prints; every map has the carrier
(slots `0x1F` to `0x27`), the islands with their targets (slots 1 to 9, `0x0B`, `0x0F`) and
one slot `0x113`, and the later maps add enemy ships (`0xCC`, `0xE4`–`0xE7`, `0xF1`–`0xF6`,
`0x10C`–`0x110`) and the airfield markers `0x114` and `0x115`.

## The record

One record of two bytes per **eight pixels of world x**: record `i` covers world x `8i`. The
whole map is that strip; there is nothing else in the file.

| Bits | Meaning |
|---|---|
| 15 | **draw**: only such a record puts its shape on the screen |
| 14 | never set in any of the 34,473 records of the 15 maps (observed) |
| 13–11 | the height in steps of four screen rows above the horizon, 0 to 7 |
| 10–2 | the slot in `MasterList` or `AthList` (`re/notes/shapes.md`) |
| 1–0 | 0 nothing, 2 stands on the world, 1 rides on a ship |

The `draw` flag is the one `SPEC.md` section 3.5 called "`0x8000` occurs frequently": a shape
wider than eight pixels occupies several columns, and only its leftmost record carries the
flag. **The other columns still carry the slot**, and the ground height routine reads the slot
without looking at the flag, so a hut four records wide gives ground under all four while
drawing once (read, and confirmed by the ground heights the tick asks for over a flight).

Low bits 1 mean the record moves with the ship it stands on, which is how the carrier deck and
the enemy ships' decks are drawn: 2,677 records of the 15 maps carry it and every one of them
belongs to a ship (observed). `0x014EAC` looks the ship up with `ship_at_offset` (`0x014A4E`),
which turns the world x into a map offset and tests it against the span at `+0` and `+2` of
each of the five ship records, and adds the ship's own `+0x1A` to the row.

## World coordinates

- **World x is in pixels**, one record every eight of them. `map_extent` is the world x past
  the last record; a map is between 7,640 and 28,552 pixels wide.
- **World y is a height in pixels, measured upward**, zero at the water line.
- The player starts at `player_start_x`, which lies over the carrier; the carrier's records are
  the block of slots `0x1F` to `0x27` around it, and `map_scan` writes their span of map
  offsets into `carrier_record` (`0x0254D8`).

`frame_update` computes the view once per pass, out of the drawing's copy of the player's
position (read, observed in every pass of the flights):

```text
view_shift = 3 in the eighth-scale view, otherwise 0
view_x     = player_x - (160 << view_shift)
view_y     = 151 + max(player_y - 131, 0),  or 1208 in the eighth-scale view
split_row  = the same value, clamped to 162 for the copper split
```

`draw_world_shape` (`0x015174`) turns a world position into a screen position:

```text
screen_x = world_x - view_x
screen_y = view_y + 11 - world_y
if view_shift:  both are shifted right by three
drawn only while -128 <= screen_x <= 448
```

So at full scale one world pixel is one screen pixel and the player sits at screen x 160; in
the eighth-scale view eight world pixels are one screen pixel and `view_x` is `1280` behind the
player, which puts the player at screen x 160 again. `draw_world`'s own loop over the map
does the same arithmetic in its own words: it starts at the record `(player_x - 0x120) / 8`,
puts it at screen x `-120 - (player_x and 7)` and steps by `view_step`, which is 8 at full
scale and 1 in the eighth-scale view, until the screen x reaches 464.

## The ground height

`ground_height` (`0x015714`) takes A0 = a map record and returns the height of its ground in D0
(observed under the oracle over 600 random records,
`test_the_ground_height_of_a_record_is_its_class_height_less_its_own_height`):

- terrain slots fall into six classes — 6, 7, (8 and `0x0B`), 3, 4, and `0x0F` to `0x1E` — and
  the answer is `ground_class_heights[class]` (`0x0257C2`, six words in the executable) less
  the record's own height bits;
- a ship slot answers with that ship's record: `+0x0E` less `+0x14` less `0x0253AE`, and the
  player's carrier subtracts `0x025396` as well, so the deck height follows the ship as it
  moves;
- every other slot, among them slot 0 and the slots below `0x0F` that are not named above,
  answers zero.

The routine is the only reader of the map inside a tick (observed, below).

## What the loader builds per mission

`map_scan` (`0x012D5A`) walks the record list twice and is the only routine that turns map
records into game objects (read, and observed as the writer of every table below):

1. **First walk**, over the records with the draw flag only: it counts the targets by slot —
   slot 4 into `target_count_4` (`0x025387`), slot 3 into `target_count_3` (`0x025386`), slot
   `0x0F` into `target_count_f` (`0x025385`) — counts the islands (slot 2) and the briefing
   numbers, and fills the five `ship_records` (`0x025460`, `0x1E` bytes each: the destroyer,
   the battleship, the cruise ship, the Japanese carrier, and the player's carrier at
   `carrier_record`, in this order)
   from the slot that introduces each: their span of map offsets at `+0` and `+2` and a set of
   constants for the rest.
2. **The allocations**: `target_count_4` records of `0x10` bytes at `target_records_4`
   (`0x0254F8`), `target_count_3` of `0x10` at `target_records_3` (`0x0254FC`),
   `(count_4 + count_3) * 5` soldiers of 8 bytes at `soldier_records` (`0x025500`) with their
   number in `soldier_count` (`0x0253C4`), and `target_count_f` records of `0x0E` bytes at
   `target_records_f` (`0x025504`).
3. **Second walk**: every slot-4 record fills a `target_records_4` entry, every slot-3 record
   a `target_records_3` entry — both keep the map offset as a long at `+0`, the world x at
   `+4` and `+6` (the slot-3 entry as a span from x − 44 to x + 16), a state byte of 5 at
   `+8` and the island number at `+9` — and every slot-`0x0F` record a `target_records_f`
   entry. Slot 1 and slot 2 records append their map offsets to the lists at `0x025430` and
   `0x025438`, and each island gets the span of its targets in `island_span` (`0x025440`) and
   five points per target in `island_score` (`0x025450`).

**Nothing else is done to the record list**: the records themselves are never written after
the read, in any of the seven runs of `re/notes/passes.md` (observed). What is rebuilt per
mission is the tables above, plus `MasterList` and `AthList` (`re/notes/shapes.md`).

## Who reads the map, and when

The read hook over the map allocation, by phase, over a take-off and 568 ticks of flight
(observed, `tools/headless.py --reads map_load`):

| Phase | Routine | Reads |
|---|---|---|
| `M` | `map_scan`, `0x012C84` | 2,865: the two walks of the mission setup |
| `T` | `ground_height` | 547: **the only reader inside a tick** |
| `F` | `draw_world` | 71,635: the strip on the screen |
| `F` | `0x014206`, `0x014430` | 48,639: the map window of the dashboard |
| `F` | `0x0103A6`, `0x01CB34` | 76 |

So the tick takes exactly one thing from the map — the ground under an object — and everything
else the map feeds is drawing.

## The decoder and its controls

`tools/map_decode.py` reads a map from `original/` when it runs and holds no game data.
`draw_list` is `draw_world`'s loop written out. Two controls hold it to the original:

- **It predicts the map draws of every pass.** Over a flight of 684 passes that covers the
  deck, the take-off, level flight and the eighth-scale view, the decoder predicts the slot,
  the screen x and the screen y of every draw `draw_world` made from the map, in order, and
  the sequences are equal pass for pass — 1,000 draws and more
  (`test_the_decoder_predicts_every_map_draw_of_every_pass`).
- **A changed map changes exactly what the decoder says.** One record of map `a` is given
  another slot and another height and the file is laid over the disk through the run
  description's `files`. The decoder's prediction for the changed map holds for every pass of
  that run, the passes whose draws differ are the ones it says differ, and the player's own
  position is the same pass for pass
  (`test_a_changed_map_changes_exactly_the_draws_the_decoder_says`).

## Open

- What the individual terrain slots are — which shape a hut, a palm or a gun emplacement has —
  belongs to the shape tables (`re/notes/shapes.md`) and to M5.
- The lists at `0x025430` and `0x025438`, which take the map offsets of the slot-1 and slot-2
  records, are filled but no reader of them was looked for.
- `0x012C84` reads the map a second time for the airfield markers `0x114` and `0x115`, which
  only the later maps carry; the records it builds at `0x0252FA` were not followed further.
- Why the loader asks for eight bytes more than the file holds is not established; the
  records it gets are zero and harmless, so nothing depends on the answer.
