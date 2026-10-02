Chapter 11
{ .chapter-kicker }

# The display

Chapter 2 gave the display's parts a paragraph each. This chapter, the first of Part II, opens the game's own display system. By its end you will know what the game keeps about a screen and why it builds its display itself; how it writes the copper's list and changes one instruction of it in every pass; where the colours come from, by day and by night; how the view zooms out when the aircraft climbs; why a fade to black passes through colours the picture never had; and how a picture, the dashboard and the ticker reach the screen. Each mechanism ends with what the port made of it and the instrument that holds it.

## A display of its own

An Amiga program normally asks the operating system for its display: it describes the screen in the system's records, a View for the whole and a ViewPort for each area, and the system's routines make the copper's list from them. Wings of Fury does not. Those routines are linked into the program, and nothing calls them. The game keeps records of its own, writes the copper's lists with a small library of its own, and hands the copper a list by writing the register `COP1LC` itself.

Chapter 2 said what it wants of the display: three areas in different modes and more colours than one palette holds. Writing the lists itself gives it one thing more: it knows where every instruction lies. The wait for the split line sits at an entry whose index the game keeps, the sky's colour at entry 35, so a pass can change the picture's colours by rewriting one instruction instead of building the list again.

The price is bookkeeping of its own. Each area's record still carries a BitMap and a RastPort, the operating system's descriptions of a picture's planes and of a pen, through which the dialogs write their text with the system's calls. And `display_init`, run once, takes every buffer from [chip memory](../glossary.md#chip-memory) and never resizes it: each screen's planes are exactly what the play screen needs, and the high-score display, the one larger screen, runs over into the other screen's half, which it does not use.

## What the game keeps about a screen

A [**view**](../glossary.md#view) is the game's record of one whole screen: 14 bytes that name its copper list, its bitplanes, the first of its areas and its entry in a cache the dashboard keeps. There are two, A and B, the two screens of the [double buffering](../glossary.md#double-buffering). A [**viewport**](../glossary.md#viewport) is one area of a view, a band of the screen with its own size, number of [bitplanes](../glossary.md#bitplane) and mode; each names the next one down, so that a view's viewports form a chain. Each holds a [**colour table**](../glossary.md#colour-table): 32 colours of 12 bits, which the copper writes into the colour registers above the viewport's first line. The playfield's viewport has a second table, the sea's. A [**copper list**](../glossary.md#copper-list) is the list of waits and register writes the [copper](../glossary.md#copper) follows through a frame; the game keeps one for each view and a third, spare.

/// figures
| What the game keeps | Size |
|---|---|
| A view | 14 bytes; two of them |
| A viewport | 172 bytes; five: two playfields, two dashboards, the ticker |
| A colour table | 32 colours of 12 bits |
| A copper list's buffer | 1,000 bytes; three: view A's, view B's, the spare |
| One view's bitplanes | 44,240 bytes |
| The ticker's bitplane | 84 x 13 bytes, shared by both views |
///

![Views A and B, each pointing to its copper list, its bitplanes and its chain of viewports, playfield, dashboard and the one ticker; the spare list between the lists; COP1LC pointing at list A.](../figures/display-records.svg)

/// caption
What the game keeps about the play screen: two views, each a chain of viewports with their colour tables, two copper lists and a spare, and one ticker shared by both.
///

## Eight screens

Every screen the game shows is one of eight layouts, each set up by a routine that fills in the viewports' sizes and depths. None uses HAM, interlace or another special mode. [**Low resolution**](../glossary.md#low-resolution) puts 320 pixels across a line, [**high resolution**](../glossary.md#high-resolution) 640 in the same time of the [beam](../glossary.md#beam).

| Screen | Viewports: size, bitplanes, first line | Shown for |
|---|---|---|
| Play | 320 x 162, 5, at 0; 640 x 37, 4, at 163; 640 x 13, 1, at 201 | a mission |
| Picture | 320 x 200, 5 | the title sequence, the rank selection |
| Story | 640 x 200, 1, at 5, with 230 rows shown | the story scroller |
| Briefing | 640 x 147, 3 | the briefing |
| Text | 640 x 200, 2 | the crack's text screen, not ported |
| Dialog | 320 x 200, 4, the hidden view only | loading and saving, a name for the high scores |
| High scores | 320 x 75, 5, at 0; 640 x 145, 4, at 76; view A only | the high-score display |
| Play, restored | as the play screen, the hidden view | the return from a dialog in a mission |

The play screen's lines are [**display lines**](../glossary.md#display-line), counted from the picture's top, where line 0 is beam line 44. The [**playfield**](../glossary.md#playfield), where the game is played, takes lines 0 to 161, the dashboard 163 to 199, the ticker 201 to 213. Lines 162 and 200 are blank, and the copper builder makes them so: above every viewport but the first it waits for the line and switches the planes off. On that line, with nothing on view, the copper writes the next area's colours, window, plane addresses and mode, dozens of register writes.

## The copper builder

`view_build_copper` makes a view's list again from its chain of viewports, step by step:

1. The planes off, and the eight sprite pointers parked on an empty sprite, since the game uses no sprites: 32 moves.
2. For each viewport below the first, a wait for the line above it and the planes off: the blank line.
3. For each viewport, a wait for the line above it and a move for each colour its depth gives, from table 1.
4. Its planes: the display window, the data fetch, the modulos, the plane addresses, then a wait for its first line and the mode with its depth.
5. Where the split is enabled and a second table exists: a wait for the split line and a move for each colour whose second value differs from its first.

A list for the play screen therefore begins with the planes off, the sprites' moves, the wait above the playfield, `COLOR00`, and at entry 35 `COLOR01`, the sky's colour. After building both lists, `mission_display_setup` appends the ticker's ramp to each: ten pairs of a wait and a `COLOR01`.

Here is the last step, `cop_vport_split`, compiled C as the listing shows it. Look first at the call of `cop_wait`, which writes the wait for the split line; then at the loop: `cmp.w` compares an entry of table 2, whose address the viewport holds at `$9c`, with the same entry of table 1, at `$98`; `beq.b` skips the move when they are equal; and the move's register is `$180` plus twice the index, the colour register of that entry.

```wingslst
--8<-- "generated/listings/asm/cop_vport_split.lst"
```

A move that wrote a colour already there would change nothing, so the sea costs only the moves of its own colours: fifteen by day.

## Two views and the swap

Chapter 2 told [double buffering](../glossary.md#double-buffering) as a concept and chapter 7 its timing. `view_show` installs a view's list: it writes an end marker behind the list's last entry, points `COP1LC` at it and sets the game's pointers to the front and the back view, without waiting. A [pass](../glossary.md#pass) of play waits for the [VBlank](../glossary.md#vblank), draws the playfield and the dashboard into the back view, rewrites the back list's split line, pokes the sky's colour into it and shows the back view; the copper takes the new list up at the next VBlank.

## How the colours change

Colours change in two ways: a table is changed and the list built again, or a built list is poked in place. Nothing cycles colours.

A picture brings its own colours: its `CMAP` chunk goes into table 1, each component's byte masked to its upper four bits, the Amiga's. The mission's palettes come from four files read by another routine, which converts a colour as `(r << 4) | g | (b >> 4)` without masking: a bit in the lower half of a byte would spill into the next component, but none of the four files has one. That routine searches for the letters `CMAP`, so it reads the sea's by day, `ocean.palette`, a whole picture with chunks that name colours to cycle, as readily as the three bare lists.

The horizon's [split line](../glossary.md#split-line) moves. Every pass computes it from the aircraft's height: 151 while the aircraft flies below 131 pixels, lower by as much as it climbs above, the row where the sky's fill ends. `cop_set_split_line` then rewrites the one wait in the back list, with a trick: it sets the list's count of entries back to the split's index, lets `cop_wait`, which appends a wait, write it there, and puts the count back. The port keeps the line in the viewport's record.

//// html | div.listing-pair

/// html | div
```wingslst
--8<-- "generated/listings/asm/cop_set_split_line.lst"
```
///

/// html | div
```c
--8<-- "generated/listings/c/wof_cop_set_split_line.c"
```
///

////

The copper gets the line clamped at 162. There it falls on the blank line, the sky's fill reaches past the playfield's last line, and the sea's palette is not seen at all.

The sky flash takes the other way. Every pass, `flip_buffers` pokes the sky's colour into entry 35 of the back list. When a rocket hits land or the aircraft crashes there, the tick sets a count of 5 and a colour, white, or red when the hit was a target; a hit on a ship flashes too, a bomb or a torpedo never. The pass counts down and on odd counts pokes the flash's colour instead: the colour, the sky, the colour, the sky, the colour. Colour 1 is the same in the sky's table and the sea's, so the flash reaches the rows above the split and below it alike.

A [**fade**](../glossary.md#fade), sixteen steps that carry a colour table to another, changes the table at every step, swaps the list on view for the spare buffer and builds the list again there, so that the copper never reads a list being written.

The port is held to all of this through the rows' colours: in both loops of chapter 8, after every pass, each row's colours are compared with a model made from the original's tables and split line alone.

## Day and night

Night is chosen between two missions: `choose_night` runs only on the way from one mission of a campaign to the next, and looks up the next mission's map. For the maps a to g it is day. For h to o it draws the beam four times and takes the top bit of the last draw: an even chance, from chapter 2's only source of chance. The flag starts at zero in the program's data, nothing else writes it and nothing clears it: so the first campaign after the program starts begins by day, and a campaign begun after a game lost at night begins at night. The original's four calls of `rand_beam` beside the port's:

//// html | div.listing-pair

/// html | div
```wingslst
--8<-- "generated/listings/asm/choose_night.lst"
```
///

/// html | div
```c
--8<-- "generated/listings/c/wof_choose_night.c"
```
///

////

The flag picks one file of each of four pairs: the sky's palette, `wingspalette` or `night.p`; the sea's, `ocean.palette` or `nightocean.p`; the dashboard's picture, `iff-dash` or `nightdash`, with 16 colours of its own; and the dashboard's shapes, `dash.shp` or `nightdash.shp`. By day the sea changes fifteen of the sky's colours, by night eighteen. Colour 1, the sky's own, is a light blue by day and black by night.

![Six rows of colour swatches, by day and by night: the sky's 32 colours, the sea's 32 with bars under the 15 or 18 that differ from the sky's, and the dashboard's 16.](../generated/figures/day-night-palettes.png)

/// caption
A mission's colour tables by day and by night, each read from its file as the game reads it; a bar marks a sea's colour that differs from the sky's, one the copper sets at the split line.
///

No script reaches the night by playing, since a campaign's first mission is day. The two loops of chapter 8 reach it by a [poke](../glossary.md#poke), the flag set on both sides at the end of the rank selection, and the whole flight agrees; the figure below is the port's first mission made night the same way. `choose_night` itself is held under the [oracle](../glossary.md#oracle) of chapter 5, over 2,000 states.

![The carrier's deck and tower under a black sky, the weapon menu at the top right, a dark sea, and the dashboard in its night colours.](../generated/figures/night-start.png)

/// caption
The first mission as a night mission, at the moment of chapter 1's day picture: the night's palettes, picture and shapes, in the 1024 by 642 box of a PAL display.
///

## Two scales

When the aircraft climbs above 186 pixels, the game zooms out. A flag the player's update sets selects the [**eighth-scale view**](../glossary.md#eighth-scale-view), in which eight pixels of the world make one of the screen: the drawing shifts every position on the screen right by three bits. The view is placed so that the aircraft stays at screen x 160, as at full scale, and the screen spans eight times as much of the world. The shapes come from a second table of pointers, resolved by name in a [shape container](../glossary.md#shape-container) of their own, `8thscale.shp`; of the world's 184 names, 84 have no shape there, and those things are not drawn. The split line stays at 151.

The picture holds two resolutions as well: a pixel of the playfield is as wide as two of the dashboard's. The port's picture is 640 pixels wide, and every low-resolution pixel is written twice; how a PAL pixel, 16/15 as wide as tall, is shown on a modern screen is chapter 23's.

## The fade's arithmetic

`colour_lerp`, whose listing chapter 4 read, does not interpolate a colour the way one might write it. It takes the start colour whole, and for blue, green and red in turn adds into the whole word the component's share of the difference: the difference times the step, divided by 15, masked to the component's four bits. When a component falls, its share is negative, and the mask turns it into a large positive number that carries into the next component up.

Take a dark blue, `0x005`, fading to black, at step 8. Blue's difference is −5, and −5 times 8, divided by 15, is −2. Masked to four bits, −2 is 14. Added to the word, 5 and 14 make 19, which is `0x013`: blue 3, and a 1 carried into green. Blue computed on its own would give `0x003`; the carry adds a green the colour never had, through most of the fade. The sky's blue gains a trace of red from its first step down, and a fade up from black, where every component rises, shows nothing of the kind.

![Five rows of sixteen swatches with their hexadecimal values: three colours rising from black, unframed; the day's sky and the dark blue 0x005 falling to black, their middle steps framed in gold.](../generated/figures/fade-steps.png)

/// caption
The sixteen steps of five fades through the port's `colour_lerp`, framed where a step differs from each component computed on its own.
///

Every fade-out's colours depend on this arithmetic, so the port keeps it exactly, and the oracle holds it on every fade the game runs. The game's four fade routines are one routine in two shapes, one viewport and one target or two of each; with two, both loops run as many colours as the first viewport's depth gives. The test that holds the port's one routine to the original's four over random tables names each case by where the game uses it:

```python
--8<-- "generated/listings/py/test_the_fades_agree_with_the_original.py"
```

A picture comes up from black: the game decodes it into the hidden view, keeps its colours, blacks the table, shows the view and fades to the kept colours. How long a step lasts is chapter 7's question.

## How a picture reaches a viewport

The pictures are [IFF ILBM](../glossary.md#iff-ilbm) files, chapter 3's format of chunks. The game's reader knows four chunks, `BMHD`, `CMAP`, `CMP2` and `BODY`, and ignores the rest. It clears the viewport's planes and decodes as many rows as both the picture and the viewport have, of as many planes as both have, each row unpacked from [**ByteRun1**](../glossary.md#byterun1), the ILBM format's packing, in which a control byte says either copy the next bytes or repeat the next one. It assumes that packing without looking; every picture on the disk uses it.

A picture taller than its viewport is cut off at the bottom: `broderbund`, `wingstitle` and `selectrank` are 256 rows high and show their first 200, and the high-score slab, 200 high, shows 145. The port carries the reader over, because its crop is what the screen shows. `Rank.iff` is on the disk and its name in the program's data, but nothing points at the name and no run opens the file. Under the oracle the port's reader is held to the original's on every picture and palette file.

## The dashboard

The [**dashboard**](../glossary.md#dashboard) is the play screen's middle area: 640 by 37 in high resolution, four planes, 16 colours, with its own picture by day and by night and its own shapes. The manual describes its instruments on its pages 8 and 9: counters of the weapon and of the Hellcats left, the oil pressure and fuel gauges with their warning lights, the score, the enemy aircraft shot down, and in the middle the 3-D view, which chapter 16 tells. The dashboard is double-buffered like the playfield, so every pass draws into the back view's dashboard only what has changed there, from one cache of every instrument for each view: each buffer must be brought up to date on its own. The digits are slices of one shape, copied without a mask.

## The ticker

The [**ticker**](../glossary.md#ticker) is the message line at the bottom of the play screen. Its one plane is 84 bytes a row, of which 80 are shown: 640 of 672 pixels. The [VBlank server](../glossary.md#vblank-server) draws each new character into the hidden 32 pixels at the right, and on every VBlank while a message runs it shifts the whole plane left by one pixel, with the processor, inside the interrupt. In the head of the loop, A0 takes the plane's address from the ticker's viewport and moves to its end, `$444` bytes on, and D0 counts the rows. Each row begins with `lsl.b` of a zero, which clears the extend flag, the 68000's carry for such chains; then each `roxl.w -(a0)` shifts one word left, taking in the bit the word to its right gave up, for all 42 words of the row, before `dbra` starts the next of the 13.

```wingslst
--8<-- "generated/listings/asm/vblank_server_ticker.lst"
```

Because the shift runs in the interrupt, the text moves one pixel every VBlank, whatever a pass costs. The messages are made at run time: the tick formats each one with the C library's `sprintf`, and the ticker takes a message only while none runs. Under the oracle the port's ticker is held to the original's VBlank by VBlank.

## What the port made of it

The port has no planes, no copper and no list. It keeps the two views and their chains, but every viewport is an [**indexed framebuffer**](../glossary.md#indexed-framebuffer), one byte per pixel holding its colour number, at the viewport's own width, 320 pixels or 640. Every drawing works there in the area's own pixels and the game's own coordinates, as on the machine, and installing a list means no more than saying which view the picture is made from.

What the copper builder does that can be seen comes out of [**bands**](../glossary.md#band): runs of output rows that share a source row and a set of colours, which [`src/screen.c`](repo:src/screen.c) hands to [`src/video.c`](repo:src/video.c). A band carries its colours with it, because every mechanism that changes colours part of the way down the screen is a run of rows of one viewport with a table of its own; two bands with the same colours share a palette. Here is where the play screen's rows get their colours, the port's form of the split, the flash and the ramp:

```c
--8<-- "generated/listings/c/play_colours.c"
```

/// figures
| The port's display | |
|---|---|
| The picture | 640 x 214, a byte a pixel |
| Palettes | 24 of 32 colours; palette 0 black |
| Bands | 48 at most |
| The first mission's picture | 10 palettes in 15 bands |
| A view's display memory | 640 x 260 bytes |
///

Twenty-four palettes, because the story scroller needs seventeen: it changes one colour on every row of two ramps of sixteen rows. Palette 0 is black and reserved for the rows no viewport covers, the blank lines. A view's memory is taller than any screen because the scroller's plane walks down it.

A viewport names its surface by an offset into one block of display memory, not by an address, so the core's state holds no pointer, and a saved state of the core, loaded again, brings the picture back with the logic. The list buffers, the parked sprites, the window and fetch registers and the plane pointers mean nothing without a copper; the inventory of chapter 4 marks them `replace`. Of installing a list the port keeps the one thing a waiting routine can see: it clears the flag the VBlank sets, so that the next wait really waits.

The tests of the core hold that every row has a palette and that the [native library](../glossary.md#native-library) and the WebAssembly draw the same picture; chapter 24 tells how the page's picture is held to the core's, and chapter 23 how the [shell](../glossary.md#shell) shows it.

/// dev
The copper library is `0x019958` to `0x01A1F4`. `view_build_copper` (`0x01A0D4`) also skips a viewport less than two lines above the next. `cop_wait` (`0x019A9C`) adds 44 to a display line, clamps the result at `0x106` and, past beam line 255, first writes the wait for the end of line 255. `BPLCON0` is `0x5200` for the playfield, `0xC200` for the dashboard, `0x9200` for the ticker. In the port: the bands and palettes in [`src/video.c`](repo:src/video.c), the views and rows in [`src/screen.c`](repo:src/screen.c), the reader and `colour_lerp` in [`src/iff.c`](repo:src/iff.c), the fades in [`src/fade.c`](repo:src/fade.c), the instruments in [`src/dash.c`](repo:src/dash.c).
///

## What comes next

Chapter 12 turns to what the pixels of these surfaces are made from: the shapes, the containers that hold them, the blit that draws them through a mask, the mirrors and the clipping.

## Further reading

- [`re/notes/display.md`](repo:re/notes/display.md), the whole note.
- [`re/notes/porting-m3.md`](repo:re/notes/porting-m3.md), ["The fades, and the one provisional setting"](repo:re/notes/porting-m3.md#the-fades-and-the-one-provisional-setting), ["Views, viewports and what reaches the output"](repo:re/notes/porting-m3.md#views-viewports-and-what-reaches-the-output), ["The story scroller's ring and its ramps"](repo:re/notes/porting-m3.md#the-story-scrollers-ring-and-its-ramps).
- [`re/notes/porting-m5.md`](repo:re/notes/porting-m5.md#the-skys-flash-observed), "The sky's flash (observed)"; [`re/notes/campaign.md`](repo:re/notes/campaign.md#day-and-night), "Day and night".
- [`SPEC.md`](repo:SPEC.md#64-video-model), section 6.4, "Video model"; [`src/video.c`](repo:src/video.c) and [`src/screen.c`](repo:src/screen.c), their opening comments.

Outside the repository: the [*Amiga Hardware Reference Manual*](https://archive.org/details/commodore-amiga-tech-ref-series-amiga-hardware-reference-manual-3rd-edition), for the copper and the playfield, and the [*Amiga ROM Kernel Reference Manual: Libraries and Devices*](https://archive.org/details/amiga-rom-kernel-reference-manual-libraries-and-devices), whose first chapter tells the system's View and ViewPort.
