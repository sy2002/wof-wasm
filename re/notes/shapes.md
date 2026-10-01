# Shapes: containers, name resolution, record header

Answers points 4 and 11 of `SPEC.md` section 10. Everything here is read from the disassembly; addresses use the standard load layout. Three readings were confirmed by running the original code in the oracle: `shape_find` against every name list and every container (6,744 lookups), `shape_mirror_x` on all 116 shapes of `hellcat.shp`, and the mask handling of `shape_draw` (see `re/notes/drawing.md`).

## Summary

A `PPkc` container is loaded whole into chip memory and stays there unchanged in layout: the game works on the file image. A **shape is a pointer to its record inside that image**. Names are resolved once, at load, into **pointer tables**: for each container there is a zero-terminated list of 4-character names in DATA, and `shapes_resolve` turns it into an array of record pointers in the same order. Game code then uses fixed numeric indices into these arrays. **A name that is not in the container gives a null pointer, and that is the normal case, not an error**: 84 of the 184 world names are absent from `8thscale.shp`. Null entries are skipped by the map drawing loop and draw nothing elsewhere. A missing *file* is fatal (with one exception, `battleship.shp`).

`MasterList` and `AthList` are not object pools. They are the two pointer tables that the map indexes: 273 slots each, the first at full scale, the second resolved in `8thscale.shp` ("Ath" reads as "eighth").

Of the three header words the specification left open: `+8` and `+10` are the position the shape was cut from in its source picture, used only by the rank selection screen as a draw position; for `hellcat.shp` and `Torpedo.shp` the game overwrites `+8` and uses it as a **mirror marker**. `+12` is not a word but **two bytes that the blitter routine reads on every draw**: the planes to clear and the planes to set under the shape's mask. Drawing in M1 needs them.

## Record header, complete

| Offset | Type | Meaning |
|---|---|---|
| `+0` | u16 | width in bytes |
| `+2` | u16 | height in rows |
| `+4` | s16 | hotspot x; callers subtract it from the draw position |
| `+6` | s16 | hotspot y |
| `+8` | u16 | x of the shape in its source picture. For records of `hellcat.shp` and `Torpedo.shp`: mirror marker, see below |
| `+10` | u16 | y of the shape in its source picture |
| `+12` | u8 | **clear planes**: destination planes set to 0 wherever the mask is set |
| `+13` | u8 | **set planes**: destination planes set to 1 wherever the mask is set |
| `+14` | u8 x 6 | destination plane masks of the stored planes, zero-terminated |
| `+20` | | plane data |

Evidence, reader by reader:

- `+12`, `+13`: `shape_blit` (`0x020B0C`) reads `0xC(a5)` at `0x020BA2` and `0xD(a5)` at `0x020BF0`, each as a byte, ANDs it with the depth mask of the target and runs one blit per plane with constant source data 0 or `0xFFFF`. `shape_draw_xor` (`0x020E24`) reads only `+13` (`0x020EA4`) and inverts those planes. Exact behaviour: `re/notes/drawing.md`.
- `+8`, `+10` as a position: the rank selection routine (`0x018262`) loads `selectrank.shp` raw, takes record number `rank` with `shape_by_index` and calls `shape_draw_xor_c(record, word at +8, word at +10)` at `0x0182C6`, `0x018362` and `0x01838E`. In that file the words are 64/91, 64/101, 64/111, 64/121 and so on, the rows of the rank list. Drawing the same record twice removes the highlight again.
- `+8` as a mirror marker: `load_permanent_shapes` stores 2 into `+8` of **every** record of `hellcat.shp` and `Torpedo.shp` (`0x012A1C`, `0x012A52`). The C routine at `0x01ABDE` (arguments: state, facing, frame) looks the frame's shape up by name in both containers, compares `+8` with `facing + 1`, and when they differ stores `facing + 1` and calls `shape_mirror_x` (`0x015B58`). The pixel data of the player's aircraft is therefore **mirrored in place, lazily, whenever the facing changes**, and `+8` records which way the stored pixels currently face (2 is the orientation in the file).
- No other reader exists. Checked: every routine that takes a record from a pointer table or from `shape_find` (the list is in `re/notes/drawing.md`); they read `+0`, `+2`, `+4`, `+6` and nothing else of the header.

Values in the files: `+12` is 0 or `0x10` in most shapes (clear plane 4, so a 4-plane shape lands in colours 0 to 15 regardless of the background); `dash.shp` has `0x10` in 207 of 223 shapes and `0x18`, `0x15`, `0x11`, `0x13` in the rest; `+13` is non-zero in a handful of shapes (`0x18`, `0x10`, `0x11`). When both are 0, planes that the shape does not store **keep the background's bits**, which is visible behaviour.

`shape_mirror_x`, confirmed in the oracle: every stored plane is mirrored row by row (byte order reversed, bits reversed through `bit_reverse_table` at `0x0256B6`), and hotspot x becomes `8 * width - 1 - hotspot x`. It swaps byte pairs from both ends, so the middle byte of an odd byte width would stay unreversed; all widths in the files are even. A null record returns at once.

## Container and lookup

The container in memory is the unpacked file (`SPEC.md` section 3.5). The record of entry `i` is at `container + 6 + 8n + offset[i]`.

`shape_find` (`0x020560`; A0 = container, D0 = name as a big-endian long; result in A0 and D0) walks the name table with `cmp.l (a1)+,d0` / `dble`: it stops at the first stored name that is **greater than or equal to** the wanted one, as signed longs, and then tests for equality. It is a linear search with early exit and **requires ascending names**. All twelve containers on the disk are strictly ascending without duplicates, so the result always equals an exact-match lookup; the oracle run confirms this for every name list entry against every container. A port may use any exact-match lookup. The count is the word at `+4`; a count of 0 or less returns 0.

`shape_by_index` (`0x02050E`; container, index) returns the record of entry `index`. Its range check is compiled without effect, so an index outside the container reads garbage.

`shapes_load` (`0x015BC6`; A0 = file name, A1 = name list) counts the names, loads the file with `load_file_chip` and falls into `shapes_resolve` (`0x015C5C`), which allocates `4 * count` bytes of public memory and fills it with `shape_find` results. It returns the container in A0 and the table in D0. If the file cannot be loaded it formats `--Problem reading file '%s', DOS error:%d--` for the debug output and returns 0 in both.

## Name lists and containers

The nine lists lie back to back at `0x023BC0`–`0x024628`, each ended by a zero long.

| List | Address | Names | Container, file name as the game spells it | Container variable | Table variable | Absent from the file |
|---|---|---|---|---|---|---|
| `battleship_names` | `0x023BC0` | 25 | `shapes/battleship.shp` | `0x026F34` | `0x026F38` | 0 |
| `japcarrier_names` | `0x023C28` | 13 | `shapes/japcarrier.shp` | `0x026F3C` | `0x026F40` | 3: `jrbf`, `jrbt`, `cmsk` |
| `destroyer_names` | `0x023C60` | 27 | `shapes/destroyer.shp` | `0x026F44` | `0x026F48` | 0 |
| `cruiseship_names` | `0x023CD0` | 24 | `shapes/cruiseship.shp` | `0x026F4C` | `0x026F50` | 0 |
| `hellcat_names` | `0x023D34` | 107 | `shapes/hellcat.shp` | `0x02463E` | `0x026E82` | 16: `hc0b`–`hc1a` |
| `world_names` | `0x023EE4` | 184 | `shapes/world.shp` | `0x024632` | `0x026E4A` | 55, among them all of `lpn0`–`lpnj` |
| the same list | | | `shapes/8thscale.shp` | `0x024636` | `0x026E76` | 84 |
| `dash_names` | `0x0241C8` | 117 | `shapes/dash.shp` or `shapes/nightdash.shp` | `0x02463A` | `0x026E52` | 0 in both |
| `torpedo_names` | `0x0243A0` | 138 | `shapes/Torpedo.shp` | `0x024642` | `0x026F10` | 40: part of `hc..`, all of `rk01`–`rk14` |
| `japplane_names` | `0x0245CC` | 22 | `shapes/japplane.shp` | `0x02464A` | `0x024646` | 0 |

`world_names` contains 8 duplicates and a few names that exist in no file (`barf`, `LIVE`, `fgyx`); the table simply has the same pointer twice, or null. The slot order is what game code relies on, so the port must build the tables from the lists in the executable (`re/tables.toml`), not from the files.

**File name case.** The game asks for `shapes/Torpedo.shp` and `shapes/rank.iff`; the disk has `torpedo.shp` and `Rank.iff`. AmigaDOS compares names without regard to case, so the port's file system must do the same.

`selectrank.shp` has no list. `0x018262` loads it with `load_file_chip`, addresses its 8 records by index and frees it when the screen ends.

## MasterList and AthList

Allocated once by `alloc_pools` (`0x01283E`), `0x458` bytes each (278 longs, 273 used), under the debug names `MasterList` (`0x026F54`) and `AthList` (`0x026F82`). Filled before every mission by `build_master_lists` (`0x01535A`):

| Slots | MasterList | AthList |
|---|---|---|
| 0–183 | copy of `world_shapes` | copy of `eighth_shapes` |
| 184–207 | `cruiseship_shapes`, or 24 nulls when not loaded | the 24 `cruiseship_names` looked up in `8thscale.shp` |
| 208–234 | `destroyer_shapes`, 27 | `destroyer_names` in `8thscale.shp` |
| 235–247 | `japcarrier_shapes`, 13 | `japcarrier_names` in `8thscale.shp` |
| 248–272 | `battleship_shapes`, 25 | `battleship_names` in `8thscale.shp` |

A map record selects a slot with bits 2 to 10 (`draw_world` at `0x013842`, the height routine at `0x015714`). `draw_world` takes `AthList` when `view_step` (`0x024F36`) is 1, the eighth-scale view, and `MasterList` otherwise, and **skips a record whose slot is null** (`0x01386E`). The ship blocks are present or null per mission: the test is the table pointer for cruise ship, destroyer and battleship, and the flag `0x025378` for the Japanese carrier.

## The slots of the islands and the weapons

What the pass draws for M5, by slot of `world_names` (`MasterList` at full scale, `AthList` in
the eighth-scale view; read from the drawing routines of re/notes/porting-m5.md, and observed
as the shapes of their draw calls in the M5 scripts' comparison):

| Slots | Names | What they are |
|---|---|---|
| 1, 2 | `bchl`, `bchr` | an island's west and east beach |
| 3 | `dugo` | a dug-out, a target with soldiers that fires |
| 4, 5 | `huta`, `hutb` | a barracks and the burnt barracks a hit leaves in the map |
| 6 to 9 | `tre1` to `tre3`, `bumb` | palms and a bump of land |
| `0x0C` to `0x0E` | `balb`, `balr`, `balw` | the balloons, by colour |
| `0x0F` to `0x1E` | `pila` to `pilp` | a pillbox, whole and in its states of damage |
| `0x4A` to `0x4C` | `rock`, `bomb`, `torp` | the weapon marker in the hold, by `weapon_type` |
| `0x5A` to `0x60` | `expl`, `exp0` to `exp5` | an explosion over land (an object going out); `0x5A` is also a target in the eighth-scale view |
| `0x61` to `0x66` | `smk0` to `smk5` | smoke, by its kind |
| `0x66` to `0x6C` | `smk5`, `spl0` to `spl5` | a splash in the sea (an object going out, and the Splashes pool) |
| `0x6E` | `ric0` | the dust of a bullet on land |
| `0x6F` to `0x80` | `guy0` to `gy11` | a soldier running, nine further on facing west, and dying |
| `0x81` to `0x8E` | `gun0` to `gun6`, `gnf0` to `gnf6` | a dug-out's or pillbox's gun by range and height, and firing |
| `0xB0` to `0xB3` | `flg0` to `flg2`, `POST` | an island's flag, and the bare post once the island is neutralised |

`torpedo_shapes` gives the bomb's frames (`0x40` on) and the rocket's (`0x4C` on, `0x74` on
while it falls) and the torpedo's (`0x88`, `0x89`); `hellcat_shapes` the guns' muzzle flash
(`0x43` on and `0x57` on by the aircraft's frame).

## Names looked up at run time

Several tables of names in DATA are not lists for `shapes_resolve`; code indexes them and calls `shape_find` through `shape_find_c` (`0x0204F4`, reached by the jump at `0x01CB30`).

| Address | Names | Container | Reader |
|---|---|---|---|
| `0x025CE0` | 8 | `hellcat.shp` and `Torpedo.shp` | `0x01ABDE`, states 1 and 11 |
| `0x025D10`, `0x025D78` | 26 each | the same | `0x01ABDE`, other states, by the sign of a velocity field |
| `0x025DE0` | 20 | the same | `0x01ABDE`, default; also the source of the mirror handling above |
| `0x025E52` | 40, `wh14` down to `wh01` | `hellcat.shp` | `0x01C436` |
| `0x025F58`, `0x025FC8` | 28 each | `japplane.shp` | `0x01D1EA`, into the 56 pointers at `0x026F8E` |
| `0x026038`, `0x0260A8` | 28 each | `8thscale.shp` | `0x01D1EA`, into `0x02706E` |
| `0x026118`, `0x026188` | 28 each | `dash.shp` | `0x01D1EA`, into `0x02745C`: three variants per name, the second character replaced by `1`, `2`, `3` |

Single names appear as immediates: `gmov` (`draw_game_over`, `0x0110DE`, in `world.shp`) and `rank` (`0x018598`, in `world.shp`, drawn centred on the briefing screen).

`0x01ABDE` does not test the lookup result. For a frame name that is absent from one of the two containers it reads `+8` through a null pointer and may store to address 8. On the Amiga that touches an exception vector nobody uses; the port needs a guard with the same visible result, which is none. `shape_mirror_x` itself ignores a null record.

## When containers are loaded and freed

| When | Routine | What |
|---|---|---|
| start-up, once | `init_assets` `0x0134BC`: `font_load`, `alloc_pools`, then `load_permanent_shapes` `0x0129DC` | `world.shp`, `hellcat.shp` (then the `+8` marker), `Torpedo.shp` (marker), `japplane.shp`, `8thscale.shp`, in this order. They stay loaded until exit |
| rank selection | `0x018262` | `selectrank.shp`, freed on leaving the screen |
| before each mission, from `main` at `0x01009E` and again at `0x010176` | `load_dash_assets` `0x01653C` | `dash.shp` or `nightdash.shp`, and the raw dashboard picture file `iff-dash` or `nightdash` into `dash_picture_file` (`0x027744`) |
| then, after the map is loaded | `load_ship_shapes` `0x013252` | `battleship.shp`, `destroyer.shp`, `cruiseship.shp`, `japcarrier.shp`, each only if its flag is set (`0x025377`, `0x02537A`, `0x02537B`, `0x025378`; set by the map loader `0x012D5A` when the map contains that ship) |
| then | `build_master_lists` `0x01535A`, and `0x01D1EA` from `mission_display_setup` | the combined tables and the enemy aircraft tables |
| loading a saved game during play | the key handler `0x01CCF6` | frees and repeats the per-mission steps |
| end of a mission, and on exit | `free_mission_assets` `0x011234` | dash container and table, sounds, map, ship containers and tables. The permanent containers are freed only by `0x012A92` on exit |

Day or night is the word `night_flag` (`0x025390`), chosen per mission by `choose_night` (`0x0111FC`). It indexes four tables of two file names each: `palette_files` (`0x0258F0`: `wingspalette`, `night.p`), `dash_picture_files` (`0x0258F8`: `iff-dash`, `nightdash`), `ocean_palette_files` (`0x025900`: `ocean.palette`, `nightocean.p`) and `dash_shape_files` (`0x025908`: `dash.shp`, `nightdash.shp`). Only the dashboard has night shapes; the world shapes change by palette alone.

**Failure handling.** A container file that cannot be loaded ends the program through `fatal_exit` (`0x01020E`). The exception is `battleship.shp`: `load_ship_shapes` clears the battleship flag, sets `0x0255BF` and carries on. A failed table allocation is not checked anywhere. In the port both are unreachable.

## What M1 did with this

All of the above is ported and compared with the original: `shape_find` and
`shapes_resolve` against every name of every list in every container, the conversion to
indexed pixels against the plane data of all 1,049 shapes, and `shape_mirror_x` against
all 216 records of `hellcat.shp` and `Torpedo.shp`. Details, and what the comparison of
the blit does and does not prove, are in `re/notes/porting-m1.md`. Two things the port
found: no container has overlapping plane masks, so the blit's mask is exactly "the
converted pixel is not 0" and needs no storage of its own; and the nine name lists are
not in ascending order, although the twelve containers are, which is all that
`shape_find`'s early exit needs.

## Consequences for the port

- Convert a shape to indexed pixels at load as `tools/ppkc.py` does, but keep **per shape**: width, height, hotspot, the two plane bytes `+12` and `+13`, the union of the stored plane masks, the number of stored planes, the byte size of one plane, and for `hellcat.shp` and `Torpedo.shp` the mirror marker. The blit needs all of them (`re/notes/drawing.md`).
- Pointer tables become arrays of shape indices with a null value. Slot numbers are the interface to game code.
- The in-place mirror changes pixel data and hotspot of a loaded shape and persists until the facing changes again. The port can mirror its converted pixels the same way, or draw mirrored and keep only the marker; the visible result is the same as long as the hotspot rule is kept.
- `re/tables.toml` needs the nine name lists and the run-time name tables above.

## Open

- What the header words `+8` and `+10` were for the tool that wrote the files is inferred from their values (multiples of 16 in x, many shapes of one animation sharing one position). The game's only use is the one described.
- The meaning of the slots the M4 and M5 scripts do not draw belongs to the subsystems that use them; the lists give the names, which are mnemonic.
- The 40 `wh..` names at `0x025E52` sit at a word-aligned, not long-aligned, address; the reader at `0x01C436` was not followed further.
- Whether any state ever draws the 11 frame names that are absent from `hellcat.shp` or `Torpedo.shp`. The headless original can log null results of `shape_find_c`.
