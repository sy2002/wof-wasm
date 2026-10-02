Chapter 12
{ .chapter-kicker }

# Shapes

Chapter 2 showed one blit and chapter 3 the file a shape comes in; this chapter follows a shape from that file into chapter 11's surfaces. By its end you will know what a shape is to the game and what each field of its header is for; how the program's names become shapes, and when; what exactly the blit does, and how its clipping comes out exact to the pixel although the blitter works sixteen pixels at a time; how the game turns the player's aircraft round; and how to read the contact sheets. Each mechanism ends with what the port made of it and the instrument that holds it.

## What a shape is to the game

The game keeps a [shape container](../glossary.md#shape-container) as it came from the disk. It loads the file whole into [chip memory](../glossary.md#chip-memory), unpacks it if it is packed in chapter 3's [Rpck](../glossary.md#rpck) format, and from then on works on that image, converting and moving nothing. A shape, to the game, is a pointer to its [**shape record**](../glossary.md#shape-record): a header of 20 bytes, then the planes the shape stores, one after another. Every routine that draws reads the fields and planes where they lie, so a pointer is all it holds.

The twelve containers hold 1,049 shapes. Most store fewer [bitplanes](../glossary.md#bitplane) than the playfield's five: about a quarter store all five, and one stores none. Here is one record whole, `smk3` of `world.shp`, one of the smoke's shapes.

![A dump of the record: the header's nine fields with their bytes, names and values; three planes as rows of bytes beside their bits; the smoke in grey with one pixel framed.](../generated/figures/record-smk3.png)

/// caption
The record of `smk3`, 68 bytes: its header field by field, each stored plane a row to a line beside its bits, and its colours with the hotspot framed.
///

## The header, field by field

The first two words give the size: the width in bytes, eight pixels to a byte, and the height in rows; the smoke is 16 by 8 pixels.

The next two are the [**hotspot**](../glossary.md#hotspot): the point of the shape, counted from its top left corner, that lands on the position the shape is drawn at. Every routine that draws subtracts it from the position first, so a shape is placed by a point of its own, the smoke by its middle, (9, 4): the code that places it needs nothing of its size, and the frames of an animation, each only as large as it needs, stay where they belong.

The words at `+8` and `+10` are, to all appearances, the position the shape was cut from in the picture it was drawn in: their x values are multiples of 16, and the frames of one animation share one. Only the rank selection reads them: it draws its highlight with one of the eight records of `selectrank.shp` at the position its header gives, one row of the rank list each. In two containers the game overwrites the first word, as the section on the mirror tells.

The next two bytes are the [**clear and set bytes**](../glossary.md#clear-and-set-bytes): the screen's planes that the blit sets to 0 and those it sets to 1 wherever the shape's [mask](../glossary.md#mask) is set. A plane a shape does not store would otherwise keep the background's bits, and a pixel's colour would depend on what lay beneath. A four-plane shape with the clear byte `0x10` lands in colours 0 to 15 whatever the background's fifth plane held: on the playfield's five planes that keeps its colours, while on the [dashboard](../glossary.md#dashboard)'s four the blit drops the fifth plane from every byte, so there the same clear byte, which 207 of the dashboard's 223 shapes carry, does nothing.

/// figures
| The two bytes in the 1,049 shapes | Shapes |
|---|---|
| Clear byte 0 | 512 |
| Clear byte `0x10`, the fifth plane | 481 |
| Clear byte of another value | 56 |
| Set byte other than 0 | 7 |
///

In the figure, `tre1`, a palm at the [eighth scale](../glossary.md#eighth-scale-view), has four planes and the clear byte `0x10`: over colour 17, an island's ground, whose fifth plane is set, it keeps its greens and browns, and without the byte it would turn blue and grey. `jcrm`, one of the Japanese carrier's shapes, stores three planes, colours 1 to 5, and its set byte `0x18` puts the fourth and fifth planes under every pixel: on the screen it shows the carrier's greys, 25 to 29.

![A palm and a carrier's deck, each over blue and over sand, by the rule and without the two bytes.](../generated/figures/clearset.png)

/// caption
The clear and set bytes at work: `tre1` of `8thscale.shp` and `jcrm` of `japcarrier.shp` over the sky's colour 1 and colour 17, by the game's rule on the left, without the two bytes on the right.
///

The header's last six bytes are the [**plane masks**](../glossary.md#plane-mask), one for each stored plane and a zero after the last: each names the screen's planes that stored plane is written to. An ordinary five-plane shape has `01 02 04 08 10`. A mask of two bits writes a stored plane into two planes: the smoke's third, `18`, lands its third plane in planes 4 and 5, and its clear byte `0x04` clears plane 3, which it does not store, so three stored planes give the smoke its colours 25 to 27 over any background. A pixel's colour number is the OR of the masks of the stored planes whose bit it has set, and no shape on the disk has two masks that share a plane.

## From names to shapes

The program asks for a shape by a name of four characters, never by its place in a file. The names lie in nine [**name lists**](../glossary.md#name-list) in the program's data, each ended by a zero. When a container is loaded, `shapes_resolve` looks every name of its list up in it and writes the results into a [**pointer table**](../glossary.md#pointer-table), an array of record pointers in the list's order. The code then names a shape by its [**slot**](../glossary.md#slot), its fixed position in a table, and fetches it with one load. Resolving once also lets one list serve two containers, as chapter 3 said: the world's names serve both scales, the dashboard's both day and night.

| Name list | Names | Resolved in | Absent |
|---|---|---|---|
| `world_names` | 184 | `world.shp`; `8thscale.shp` | 55; 84 |
| `torpedo_names` | 138 | `Torpedo.shp` | 40 |
| `dash_names` | 117 | `dash.shp`; `nightdash.shp` | none |
| `hellcat_names` | 107 | `hellcat.shp` | 16 |
| `destroyer_names` | 27 | `destroyer.shp` | none |
| `battleship_names` | 25 | `battleship.shp` | none |
| `cruiseship_names` | 24 | `cruiseship.shp` | none |
| `japplane_names` | 22 | `japplane.shp` | none |
| `japcarrier_names` | 13 | `japcarrier.shp` | 3 |

A name absent from its container gives a null pointer, and that is the normal case, not an error: 84 of the 184 world names have no shape at the eighth scale, as chapter 11 told. The map's drawing skips a null slot, and a null record draws nothing anywhere. The world's list even holds eight names twice: the slots, not the files, are what the code relies on.

The lookup, `shape_find`, walks the container's names from the first, stops at the first name not less than the one it wants, and then tests whether it is the same. That early exit is right only over names in ascending order, and all twelve containers are so, strictly; the nine lists are not, and need not be. Look at the loop on the left, `cmp.l (a1)+,d0` and `dble`, which compares four letters as one long; the port on the right keeps the exit.

//// html | div.listing-pair

/// html | div
```wingslst
--8<-- "generated/listings/asm/shape_find.lst"
```
///

/// html | div
```c
--8<-- "generated/listings/c/wof_shape_find.c"
```
///

////

`selectrank.shp` has no list: the rank selection takes its eight records by number, through `shape_by_index`, whose range check the compiler left without effect. A few names are looked up only when needed, the player's frames and the enemy aircraft's, which chapters 14 and 16 tell.

Before every mission two tables are built from the others, `MasterList` and `AthList`, "Ath" for eighth, 273 slots each, which the map's records index: the world's 184 slots, then the four enemy ships' blocks, null where the mission has no such ship; `AthList` holds the same names resolved in `8thscale.shp`. Here is the routine that draws a map's shape. Its first lines turn the world's position into the screen's, chapter 13's subject, and drop a shape whose x lies outside −128 to 448; then `add.w d2,d2` twice makes the slot an offset, four bytes a pointer, `movea.l (a0,d2.w),a0` fetches the record from the table, and the two `sub.w` take the hotspot off.

```wingslst
--8<-- "generated/listings/asm/draw_world_shape.lst"
```

The port builds its tables from the lists in the program, not from the files, keeps the slots and the early exit, and holds both under the [oracle](../glossary.md#oracle) of chapter 5: every name of every list and every name a container carries, looked up in all twelve containers, 6,963 lookups, and every table entry for entry.

## What is loaded when

| When | What | Until |
|---|---|---|
| The program's start | `world.shp`, `hellcat.shp`, `Torpedo.shp`, `japplane.shp`, `8thscale.shp` | the program's end |
| The rank selection | `selectrank.shp` | the screen's end |
| Each mission | `dash.shp` by day, `nightdash.shp` by night | the mission's end |
| Each mission, after its map | the container of each enemy ship the map holds | the mission's end |

The five that stay hold what any mission may draw: the world at both scales, the player's aircraft and its weapons, the enemy aircraft. Only the dashboard has night shapes; the world changes by its palette alone. A name such as `Torpedo.shp` finds `torpedo.shp`, whatever the case, as chapter 3 told. A container that cannot be loaded ends the program, except `battleship.shp`, without which the game clears the battleship's flag and carries on. The port loads the same files at the same moments; with every file in the page, neither failure can happen.

## The blit, exactly

Chapter 2 told the blit's idea: a mask of where the shape has colour, and one run of the [blitter](../glossary.md#blitter) for each plane. `shape_draw` chooses the mask first. A shape whose plane, its width in bytes times its height, is larger than 1,040 bytes, the buffer the mask is built in, gets none. Otherwise a shape of two or more planes gets the OR of its planes, written into that buffer by the processor; a shape of one plane is its own mask; a shape of no plane gets none. Look at the plane's size, `mulu.w`, compared with `MaskBuffer_size`; then the planes counted in D1, `bhi.b` to the OR loops for two or more, `lea.l $14(a0),a1`, the stored plane itself, for one, and `suba.l a1,a1` for none.

```wingslst
--8<-- "generated/listings/asm/shape_draw_mask.lst"
```

Then come three phases, a run of the blitter for each plane: the clear planes, its source B held at 0; the set planes, B held at all ones; and each stored plane into the planes of its mask, B the plane. Each run combines the mask, source A, with B and the screen's plane, C, by the [**minterm**](../glossary.md#minterm) `0xCA`. A minterm is the number that chooses the blitter's logic function, one bit for each of the eight ways A, B and C can be set; `0xCA` gives B where A is set and C where it is not. For a pixel of colour number v under the mask the phases come to `v = (((v and not clear) or set) and not U) or p`, U being the planes of all the masks together and p the shape's pixel; on the dashboard every byte first loses its fifth plane. Planes named by none of them keep the background's bits.

A shape without a mask writes its whole box, colour 0 included: an [**opaque shape**](../glossary.md#opaque-shape). Eleven are too large for the buffer, as chapter 2 told, and ten of them are pieces of the carriers and the ships. None of the ten holds a pixel of colour 0: nine paint the sky's own colour 1 around the hull, and `mcar` fills its box. The artwork was made for this blit. The eleventh, `rank`, the briefing's badge, is two-thirds colour 0 and is drawn on an empty screen. One shape stores no plane at all, `bchm` of `8thscale.shp`, which would paint its two bytes, colour 17, over a box of 16 by 1; no name in the program asks for it. A null record draws nothing.

![Ten grey hulls and carrier pieces with their names, blue sky in the corners of nine of their boxes.](../generated/figures/opaque-hulls.png)

/// caption
The ten hull pieces too large for a mask, from `world.shp` and the four ship containers, in the day palette: no colour 0, and the sky's colour 1 around nine hulls.
///

## Clipping to the pixel

Every draw is limited to a [**clip rectangle**](../glossary.md#clip-rectangle), the part of the screen it may change: the playfield's 162 rows by 320 columns, the dashboard's 37 by 640, a window of the dashboard from rows 7 to 31 and columns 256 to 399, one ending at the water line, or the front end's whole screen. The routine that sets it, `clip_set`, rounds the left and right edges down to a multiple of 16, with `andi.w #$fff0`: the blitter writes a plane a word at a time, 16 pixels, and an edge on a word's boundary lets a blit skip whole words. Every edge the game asks for is on one already.

That raises a puzzle. A shape may lie at any x and the blitter writes whole words, yet nothing outside the shape's box changes and the clip cuts the box exactly at its edge. Four things give the answer, and the diagram follows one row. The blit's span starts at the word that holds the shape's left edge and, when x is not a multiple of 16, is one word wider than the shape, so it overhangs the box on both sides. The blitter's shifter moves the mask right by x's remainder, bringing in zeros. Its two [**word masks**](../glossary.md#word-masks), ANDed with the first and the last word of every row of the mask, blank the shape's columns left of the clip and the extra word on the right. And with the minterm `0xCA`, a 0 in the mask leaves the screen's bit as it was. So every pixel of the shape's box inside the clip is written, and no other. A shape without a mask has one of all ones, cut the same way.

![One row of 48 pixels in three words: the box from 37 to 68, the clip from 48, the mask set from 48 to 68 only, and the screen's row written there in gold.](../figures/clip-blit.svg)

/// caption
One row of a shape 32 pixels wide at x 37, the clip from pixel 48: the shift and the two word masks leave the mask set only on the box's pixels inside the clip.
///

So the port may clip pixel by pixel, with the rectangle rounded as the original rounds it.

## A highlight that removes itself

A second routine, `shape_draw_xor`, takes no mask and ignores the clear byte: inside the clipped box it inverts the planes of the set byte and combines each stored plane with the screen's by exclusive or. Drawing the same shape twice at the same place therefore leaves the screen as it was. So the rank selection moves its highlight: drawn again, it is gone, and the next is drawn. The player's muzzle flash and an enemy aircraft's are drawn the same way, and the port's routine does the same on pixels.

## The mirror

The player's aircraft turns round, and the game keeps each frame once. At load it writes 2 into the word at `+8` of every record of `hellcat.shp` and `Torpedo.shp`. From then on that word is the [**mirror marker**](../glossary.md#mirror-marker), which way the stored pixels face, 2 being the way the file holds them. The routine that chooses the aircraft's frame compares the marker with the facing it wants, and only when they differ does it write the new value and call `shape_mirror_x`, which turns the record round in place. A frame is mirrored once when the aircraft turns, not at every draw.

`shape_mirror_x` reverses every row of every stored plane, swapping bytes from both ends and reversing each byte's bits through a table, `bit_reverse_table`. The hotspot turns too, so that the same point of the aircraft lands on the drawing position, now counted from the other side: its x becomes 8 times the width, less 1, less the old x. On the left, look at that arithmetic, `lsl.w #$3`, `subq.w #$1` and `sub.w $4(a0)`, and at the inner loop's two `move.b` through the table; on the right the port works on pixels, where one reversal of each row is the whole mirror.

//// html | div.listing-pair

/// html | div
```wingslst
--8<-- "generated/listings/asm/shape_mirror_x.lst"
```
///

/// html | div
```c
--8<-- "generated/listings/c/wof_shape_mirror_x.c"
```
///

////

![The Hellcat as stored and mirrored, a gold frame around its hotspot in each.](../generated/figures/mirror-hc05.png)

/// caption
The Hellcat `hc05` as `hellcat.shp` stores it and mirrored, its hotspot framed in both.
///

The routine that chooses the frame does not test its lookup: for a frame name absent from a container it reads the marker through a null pointer, harmless on the Amiga; the port tests first, to the same visible result, nothing. Under the oracle its mirror is held to the original's on all 216 records of the two containers, each mirrored twice to come back as it was.

## What the port made of it

The port has no planes and no blitter. It converts every shape once, at load, to pixels of the kind chapter 11's [indexed framebuffer](../glossary.md#indexed-framebuffer) holds, a colour number a byte, and keeps the header's fields the blit still needs: the clear and set bytes, the planes of all the masks together, the number of stored planes, the size of a plane, the hotspot and the marker. Then it throws the file image away. A pointer table becomes an array of shape numbers, −1 standing for null. Under the oracle every one of the 1,049 conversions is held to the planes the original keeps.

The mask needs no storage: because no shape has two plane masks that share a plane, the OR of its stored planes is set exactly where the converted pixel is not 0, as the conversion checked for every shape. The blit is the one place where the port cannot follow the original instruction by instruction, since the original programmes a chip the port does not have. It applies the rule per pixel, with the same clipping and the same order of drawing. Here is its heart: the two bytes and the masks' planes folded into `keep` and `force`, a pixel of 0 skipped where the shape has a mask, and one line that writes the pixel.

```c
--8<-- "generated/listings/c/shape_blit_pixels.c"
```

## How the blit is held

Chapter 5 told how the blit is compared, through its [**register programme**](../glossary.md#register-programme): the blitter's [registers](../glossary.md#register) as they stand when a blit starts, its pointers, modulos, word masks, shifts, minterm and size. The original's `shape_draw` runs under the oracle with the custom chips' addresses as plain memory, every blit is captured at the register that starts it, and a model of the blitter, [`tests/blitter.py`](repo:tests/blitter.py), replays it on a copy of the planes for the comparison with the port's pixels. The model knows only the modes the game uses; any other stops the test.

/// figures
| The blit's comparison | |
|---|---|
| Shapes | all 1,049, each at six positions: on a word and shifted, inside and over every edge |
| Clip rectangles | the whole playfield and one inside it |
| Backgrounds | empty and noisy |
| Draws on the playfield's five planes | 25,176 |
| Again on the dashboard's four planes | four containers at three positions, 2,106 draws |
///

That proves the clipping arithmetic, the pointers, the modulos, the word masks and the order of the phases to be the original's own, so a mistake in the port's clipping shows at once. It does not prove the model: how the blitter combines and shifts is documented hardware behaviour that the project modelled, not derived, and a mistake in that reading would be shared by the model and the port; a run against an emulator exact to the cycle would close it. One test leaves the port out and holds the programme itself to the claim of the clipping section: every seventh shape of `world.shp`, at four positions against both clips, drawn over all zeros and all ones; `touched`, the pixels either draw changed, must lie within `box`.

```python
--8<-- "generated/listings/py/test_the_blit_writes_exactly_the_shape_box.py"
```

These tests and those of the earlier sections make `shape_find`, `shapes_resolve`, `shape_mirror_x`, `clip_set` and the blit's routines [verified](../glossary.md#verified). The work turned up two findings: the first picture of the title sequence is the crack's, as chapter 1 told; and `cruiseship.shp` and `japplane.shp` unpack to one byte more than they declare, which the original writes past the end of its buffer and the port leaves out; nothing reads it.

## The contact sheets

A [**contact sheet**](../glossary.md#contact-sheet) is a picture of every shape of a container with its name above it, as a photographer's contact sheet shows a whole film. [`tools/ppkc.py`](repo:tools/ppkc.py) makes it from the container's planes in the day [palette](../glossary.md#palette), colour 0 left as the dark ground, twice enlarged, in a grid or packed. Seven are kept in [`ref/sheets/`](repo:ref/sheets/): the eighth scale, the battleship twice, the Hellcat, the enemy aircraft and the world twice. A test holds each byte for byte to what the tool makes of the disk.

A sheet answers what a name shows, lays an animation's frames side by side, and with the eighth scale's sheet beside the world's sets a name's two scales next to each other. One caution: a sheet shows the colour numbers the planes store, not what the clear and set bytes make of them, so `jcrm`, red and blue on a sheet, is grey on the screen. The shape browser of this book shows every shape of every container.

/// dev
The routines: `shapes_resolve` `0x015C5C`, `shape_mirror_x` `0x015B58`, `aircraft_frame` `0x01ABDE`; the blitter library `0x0209BC` to `0x0215D8`. The notes and [`SPEC.md`](repo:SPEC.md#35-file-formats) count the planes from 0, so their "clear plane 4" is this chapter's fifth plane, `0x10`. A clip rectangle's bottom and right are exclusive. Where the game's state holds a pointer to a record, the port's holds a handle, the container's number and the shape's in one word, since a saved state of the core can hold no pointer. In the port: [`src/shapes.c`](repo:src/shapes.c), [`src/draw.c`](repo:src/draw.c); the tests in [`tests/test_oracle_m1.py`](repo:tests/test%5Foracle%5Fm1.py).
///

## What comes next

The chapter in one sentence: a shape is a record in a container the game keeps as it came from the disk, reached through tables its names were resolved into once, and drawn by one blit whose rule, clipping included, the port keeps pixel by pixel. Chapter 13 turns to the map, whose records name these shapes by slot.

## Further reading

- [`re/notes/shapes.md`](repo:re/notes/shapes.md), the whole note.
- [`re/notes/drawing.md`](repo:re/notes/drawing.md), ["Summary"](repo:re/notes/drawing.md#summary), ["The blitter library"](repo:re/notes/drawing.md#the-blitter-library), ["What `shape_draw` does, exactly"](repo:re/notes/drawing.md#what-shape%5Fdraw-does-exactly) and ["The scene routines"](repo:re/notes/drawing.md#the-scene-routines).
- [`re/notes/porting-m1.md`](repo:re/notes/porting-m1.md), ["The blit is per-pixel, and why"](repo:re/notes/porting-m1.md#the-blit-is-per-pixel-and-why) and ["How the tests establish it"](repo:re/notes/porting-m1.md#how-the-tests-establish-it).
- [`SPEC.md`](repo:SPEC.md), section 3.5, ["File formats"](repo:SPEC.md#35-file-formats); 6.4, ["Video model"](repo:SPEC.md#64-video-model).
- [`src/shapes.c`](repo:src/shapes.c) and [`src/draw.c`](repo:src/draw.c), their opening comments; [`tools/ppkc.py`](repo:tools/ppkc.py) and [`ref/sheets/`](repo:ref/sheets/).

Outside the repository: the [*Amiga Hardware Reference Manual*](https://archive.org/details/commodore-amiga-tech-ref-series-amiga-hardware-reference-manual-3rd-edition), its chapter "Blitter Hardware", for the minterms, the shifters and the word masks.
