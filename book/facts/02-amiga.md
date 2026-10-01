# Fact sheet: chapter 2, The Amiga in twenty minutes

Every claim the chapter makes, one line each, with its source, in the order of the chapter. A claim without a source goes to the list at the end and stays out of the draft. A general fact about the Amiga or the 68000 that the repository's notes do not state is sourced in a reference work outside the repository, named with its chapter or section, and marked **(reference)**, so that the fact-check can weigh it; a fact the notes state about this game is always sourced in the notes. Two reference works are cited:

- *Amiga Hardware Reference Manual*, Commodore-Amiga, third edition (Addison-Wesley, 1991), cited as HRM with the chapter: 1 "Introduction", 2 "Coprocessor Hardware", 3 "Playfield Hardware", 5 "Audio Hardware", 6 "Blitter Hardware", 7 "System Control Hardware".
- *M68000 Family Programmer's Reference Manual*, Motorola (M68000PM/AD), cited as PRM with its section 1, "Introduction": the integer unit's programming model and its data formats.

## Opening

1. The game's Amiga version asks for an Amiga 500, 1000 or 2000 with at least 512 KB of memory and a joystick. Source: `original/manual.txt`, page 2 (cited, not quoted).
2. The chapter covers only what the port needed, each hardware topic tied to what this game does with it; the deep dives are Part II. Source: `book/BOOK.md` 3, chapter 2 and Part II.

## The machine around the game

3. The Amiga is a Motorola 68000 processor beside a set of the Amiga's own chips, the custom chips, which make the picture, draw and play sound, and which share one memory with the processor. Source: HRM 1 **(reference)**; the game's use of them: `SPEC.md` 3.4, the two "custom chips" rows.
4. The custom chips are driven through their registers at fixed addresses from `0xDFF000`; the game keeps that base in `custom_base` (`0x026938`) and writes the registers directly: `COP1LC` with copper lists of its own, the blitter's registers from the blitter library, the audio registers, `INTENA`, `INTREQ`. Source: `re/notes/drawing.md`, "The blitter library"; `SPEC.md` 3.4, the custom-chip rows.
5. The game reads only these custom-chip registers outright: `JOY1DAT` (the stick) and `VHPOSR` (the beam's position); the sound code reads `INTENAR` and `INTREQR`, and the blitter's busy bit is read only to wait for it. Source: `re/notes/drawing.md`, "Read-back", the table's first two rows.
6. Two further interface chips, the CIAs, sit at `0xBFD000` to `0xBFEFFF`; the game reads the fire button from CIA-A (bits 6 and 7 of its port register), and the music player takes CIA-A's timer A. Source: `re/notes/headless.md`, "Memory map"; `re/notes/input.md`, "Fire button and the tap/hold discrimination"; `re/notes/music.md`, "The timer". The CIA is an 8520 (`re/notes/music.md`, "The timer": "the 8520's reset state").
7. The ROM, Kickstart, holds the parts of the operating system the game reaches there: the floating point (`mathffp.library`), the key conversion (`console.device`) with the default keymap, and the system font. Source: `re/notes/headless.md`, "Game logic uses floating point" and "The keyboard needs the ROM too"; `re/notes/system-font.md`, "Where the fonts are".

## The 68000

8. The 68000 has eight data registers, D0 to D7, and eight address registers, A0 to A7, each of 32 bits; A7 is the stack pointer; a program counter holds the address of the next instruction. Source: PRM 1 **(reference)**; the listing shows `d1-d7/a0-a6` saved and `-(a7)` as the stack (`re/Wings.lst`, `text_width` `0x01591E`, the `book/docs/generated/listings/asm/text_width.lst` extract).
9. An instruction works on a byte (8 bits), a word (16) or a long (32), written `.b`, `.w`, `.l` after its name. Source: PRM 1 **(reference)**; `SPEC.md` 7.1 (`muls.w` multiplies two 16-bit values into 32 bits, `ext.l` widens a 16-bit value).
10. Machine code is the processor's instructions as numbers in memory; assembly language is their written form, one instruction a line. Source: the terms' definitions in the book's words.
11. The listing, `re/Wings.lst`, prints each instruction with its address, its bytes of machine code in hexadecimal, and the instruction in assembly language; hexadecimal numbers carry a `$` there, as Motorola's assemblers write them, where this book writes `0x`. Source: `re/Wings.lst` (any line, e.g. `0x0203BE`); `book/BOOK.md` 4, point 3 (the book's hex).
12. `rand_beam` (`0x0203BE` to `0x0203D8`, seven instructions, hand-written assembly) is the game's only random source in use, with 43 call sites. Source: `re/Wings.lst` at the range; `re/functions.csv` (kind `asm`); `SPEC.md` 3.3; `re/notes/random.md`, "The generator".
13. What it does, line by line: loads the word `rand_seed_const` (`0x026912`) into D0; multiplies it, signed, by `0x1AFB` (`muls.w`); adds `0x1FCCD` as a long; reads the word at `0xDFF006`, `VHPOSR`, into D1; exclusive-ors D1 into D0; stores the word into `rand_state` (`0x026910`); returns (`rts`), the result in D0. Source: `re/Wings.lst` `0x0203BE`-`0x0203D8`; `re/notes/random.md`, "The generator" (the same in C).
14. `-$46ec(a4)` is `rand_seed_const`: `0x02AFFE` less `0x46EC` is `0x026912`; the listing prints the variable's name beside the instruction; how A4 leads to the program's variables is chapter 3's. Source: `SPEC.md` 3.2 (A4 is `0x02AFFE`, the listing prints the name); computed; `book/BOOK.md` 3, chapter 3 ("the data reached through A4").
15. `VHPOSR` holds the low 8 bits of the beam's line in its high byte and its horizontal position in its low byte; so the result is a constant combined with where the beam happens to be. Source: `re/notes/random.md`, "The generator" and the paragraph after it.
16. A routine returns its result in D0: true of the C routines and of `rand_beam`. Source: `SPEC.md` 3.2 ("Result in D0"); `re/notes/random.md`.
17. Chapter 4 reads the listing; routines compiled from C and those written by hand look different there. Source: `book/BOOK.md` 3, chapter 4.

## Chip memory

18. Chip memory is the part of the Amiga's memory that the custom chips can read and write by themselves, without the processor (direct memory access); memory added beyond it, where a machine has any, only the processor reaches. Source: HRM 1 **(reference)**; HRM 7, "DMA control" **(reference)**.
19. The game asks the operating system for chip memory by a flag: `load_file_chip` (`0x01FECA`) passes `MEMF_CHIP`, `MEMF_PUBLIC` and `MEMF_CLEAR` (`0x10003`, the `pea` at `0x01FECE`) to `load_file`. Source: `re/names.txt`, the line of `01feca`; `re/Wings.lst` `0x01FECA`-`0x01FEDE`.
20. `display_init` (`0x016670`) allocates the display's memory from chip memory once: the bitplanes of both views, `0x159A0` bytes; three copper list buffers of 1,000 bytes each; the ticker's plane; the sprite pointers' zero block. Source: `re/notes/display.md`, "Memory".
21. One view's bitplanes are `0xACD0`, 44,240 bytes, exactly the play screen: 40 x 162 x 5 for the playfield plus 80 x 37 x 4 for the dashboard; both views together 88,480. Source: `re/notes/display.md`, "Memory"; computed.
22. `MaskBuffer`, the blit mask's scratch space, 1,040 bytes, is in chip memory. Source: `re/notes/drawing.md`, Summary.
23. A shape container is loaded whole into chip memory; the table of pointers that names the shapes goes into public memory, ordinary memory the processor alone reads. Source: `re/notes/shapes.md`, Summary and "Container and lookup" (`shapes_load` with `load_file_chip`, `shapes_resolve` with public memory).
24. The eight sound effects are loaded into chip memory. Source: `re/notes/sound.md`, "The samples".
25. The song data `wofsongs` is a hunk file whose DATA hunk of 39,020 bytes, the songs, the voices and the sound samples of the music, goes into chip memory. Source: `re/notes/music.md`, "The two files"; `SPEC.md` 3.1.
26. The port has one static arena for all of it; the browser has no chip memory, and the game's out-of-memory paths are unreachable. Source: `SPEC.md` 3.4, the `AllocMem` row; `SPEC.md` 6.1 ("one static arena replaces `AllocMem`").

## Bitplanes

27. A picture is kept as bitplanes: one plane holds one bit of every pixel's colour number; the display takes the bit of each plane for a pixel and puts them together into its colour number, plane 1's bit the lowest. Five planes give numbers 0 to 31, 32 colours. Source: HRM 3 **(reference)**; for the shapes, `tools/ppkc.py`, `to_indexed` (each stored plane ORs its mask into the pixel); `re/notes/display.md`, "Screens" (`BPLCON0` `0x5200` for 5 planes, 32 colours).
28. The colour number goes through the palette, 32 colour registers (`COLOR00` upward) of 12-bit words, 4,096 colours. Source: `re/notes/display.md`, Summary and "The copper builder", step 4; chapter 1 introduced the palette.
29. The play screen: the playfield, 320 x 162 pixels in low resolution with 5 planes (32 colours), at line 0; the dashboard, 640 x 37 in high resolution with 4 planes (16 colours), at line 163; the message ticker, 640 x 13 in high resolution with 1 plane, at line 201; lines 162 and 200 blank; 214 lines in all. Source: `re/notes/display.md`, Summary and "The play screen line by line"; `SPEC.md` 6.4.
30. A low-resolution pixel is twice as wide as a high-resolution one; the port's output is 640 wide with the low-resolution pixels doubled. Source: `SPEC.md` 6.4 ("The shell output is 640 pixels wide with low-resolution pixels doubled").
31. A shape stores its own planes, each with the destination plane it lands in (the masks at `+14`). Source: `re/notes/shapes.md`, "Record header, complete".
32. `hellcat.shp` has 116 shapes, 90 of them with five planes landing in planes 1, 2, 4, 8 and 16 in that order. Source: `tools/ppkc.py` `parse()` over `original/disk/Wings_of_Fury/shapes/hellcat.shp` (the command in "Counts"); `re/notes/shapes.md` (116 shapes of `hellcat.shp`).
33. The shape `hc05`, the Hellcat in level flight, is 48 x 13 pixels with five planes; its pixels use colours 19 to 31 only, so its fifth plane, worth 16, is set wherever the aircraft is; the marked pixel (x 22, y 8) has colour 21: planes 1, 3 and 5 set, 1 + 4 + 16. Source: `tools/ppkc.py` `to_indexed()` of `hc05` (the command in "Counts"); figure `planes-hellcat`.
34. Colour 21 of `wingspalette` is `#4477AA`, a mid blue. Source: `book/tools/figures.py` `palette('wingspalette')`.
35. The port keeps 8-bit indexed framebuffers, one byte a pixel holding the colour number, and applies the palette at presentation; shapes are converted from planes to such pixels once, at load. Source: `SPEC.md` 6.4, first two paragraphs.

## The beam and the copper

36. The display draws the picture with a beam that sweeps each line from left to right and the lines from top to bottom. Source: HRM 2 and 3 **(reference)**; `re/notes/random.md` (`VHPOSR` holds the beam's line and position on the line).
37. A PAL frame is 313 lines of 227 colour clocks, 71,051 clocks. Source: `SPEC.md` 6.5 ("a real PAL frame is 313 lines of 227 colour clocks"); `re/notes/porting-m8.md`, "What the model leaves out".
38. The game's picture begins at beam line `0x2C` (44), its display line 0, and the play screen ends at beam line 257. Source: `re/notes/display.md`, "The play screen line by line" (display line 0 is beam line `0x2C`, the picture ends at beam line 257) and the viewport table (+0xA6).
39. The copper follows a list of instructions in step with the beam: a wait for a beam position, and a move that writes a value into one of the chips' registers. Source: HRM 2 **(reference)**; `re/notes/display.md`, "The copper builder" (`WAIT (0, y − 1)`, moves to `COLORxx`, `BPLCON0`), `cop_wait` (`0x019A9C`).
40. The game builds no operating-system display: it writes its own copper lists with a small C library (`0x019958` to `0x01A1F4`) and points the hardware at a list by writing `COP1LC` (`0xDFF080`). The operating system's display routines are linked in and never called. Source: `re/notes/display.md`, Summary; `SPEC.md` 3.4, the graphics row of `InitVPort` and the others.
41. The play screen's list, per area: a wait for the line above the area, `BPLCON0` off (the blank line), the area's colours, its bitplane pointers and its window, then a wait for its first line and `BPLCON0` with its depth and resolution. Source: `re/notes/display.md`, "The copper builder", steps 2 to 5.
42. The playfield's list holds a second wait at the split line, followed by a move for each colour where the sea's palette differs from the sky's: by day colours 2 to 15 and 24, fifteen moves. Source: `re/notes/display.md`, "The copper builder", step 6, and "Day and night".
43. The split line is computed every pass and rewritten in the back list (`cop_set_split_line` `0x01876E`); that it follows the horizon is inferred. On the carrier's deck it is 151 (`0x97`). Source: `re/notes/display.md`, "The split line"; the figure `mission-palettes` (rows 0 to 150 the sky's, 151 to 161 the sea's).
44. The ticker gets ten waits, one per line from 201, each with a new `COLOR01`: the greys 777, 999, BBB, DDD, FFF, DDD, BBB, 999, 777, 555. Source: `re/notes/display.md`, "How colours change", the ticker ramp row.
45. The sky's flash is one value poked into the built list, `COLOR01` of the back list. Source: `re/notes/display.md`, "How colours change", the sky flash row.
46. Double buffering: two complete views, each with its bitplanes and its copper list; a pass draws into the back view and installs the back view's list, one write to `COP1LC`; the hardware takes the new list at the next vertical blank. Source: `re/notes/display.md`, Summary and "Double buffering and the swap".
47. A fade runs 16 steps, rebuilding and installing the list at each, with no wait inside its loop, so its length is processor time; chapter 7 tells how the port times it. Source: `re/notes/display.md`, "Fades"; `book/BOOK.md` 3, chapter 7 (the fade step).
48. The game uses no hardware sprites and no colour cycling. Source: `re/notes/display.md`, Summary and "Memory" (`null_sprite`, "The game uses no sprites").
49. The port has no copper: it keeps a palette for every row of its picture, and the copper's effects, the split, the ramp, the flash and the fades, become further palettes for further rows. Source: `SPEC.md` 6.4 ("The per-row palette interface expresses all of these") and 6.6; `re/notes/porting-m1.md`, "Decisions the port made" ("A screen is a stack of bands").
50. The figure `mission-palettes`: at VBlank 759 of the mission run, rows 0 to 150 through `wingspalette`, 151 to 161 through `ocean.palette`, 162 and 200 through the black palette 0, 163 to 199 through `iff-dash` (16 colours), 201 to 209 through five palettes rising and falling (one palette for each grey of the ramp), 210 to 213 through a sixth, the ramp's last grey. Source: `book/docs/generated/figures/mission-palettes.png`, looked at; `book/figures.toml`.

## The blitter

51. The blitter copies and combines rectangles of memory: up to three sources, A, B and C, and a destination, D, combined bit by bit by a logic function chosen by a number, the minterm. Source: HRM 6 **(reference)**; `re/notes/drawing.md`, "What `shape_draw` does, exactly" (A the mask, B the plane, C the destination, minterm `0xCA`, D = A·B + ¬A·C).
52. All shape, rectangle and line drawing goes through one library of hand-written assembly at `0x0209BC` to `0x0215D8`, and every routine of it drives the blitter; the scene routines decide what to draw and call it. Source: `SPEC.md` 3.2; `re/notes/drawing.md`, Summary.
53. To draw a shape, the processor writes the OR of its planes into `MaskBuffer`, which is the mask; the blitter then runs once per plane and writes, where the mask is set, the shape's bit, and keeps the background's bit where it is not. Source: `re/notes/drawing.md`, "What `shape_draw` does, exactly", steps 1 and 2 and "In hardware terms".
54. So colour 0 is see-through only in a shape that gets a mask; a shape whose plane is larger than 1,040 bytes gets none and is drawn opaque; eleven shapes are; the ten ship and carrier pieces among them contain no colour 0 at all and carry the sky's colour 1 around the hull. Source: `re/notes/drawing.md`, "What `shape_draw` does, exactly", the paragraph after "In hardware terms".
55. Text in the game's font is drawn by the processor into a one-bit template, which `graphics.library`'s `BltTemplate` puts on the screen. Source: `re/notes/drawing.md`, Summary and "Text".
56. The ticker is scrolled by the processor inside the VBlank interrupt, one pixel per VBlank, not by the blitter. Source: `re/notes/display.md`, "The play screen line by line"; `re/notes/drawing.md`, "Other drawing".
57. No game logic reads back what was drawn: no pixel, no mask, no blitter flag, no collision register. Source: `re/notes/drawing.md`, Summary and "Read-back".
58. The port draws each shape per pixel on its indexed framebuffer with the original's clipping and draw order; the original's own `shape_draw` is run, its blitter register writes captured at every write to `BLTSIZE` (`0xDFF058`), replayed through a model of the blitter, and compared pixel by pixel with the port's picture for every shape of every container at six positions, two clip rectangles and two backgrounds. Source: `SPEC.md` 6.4; `re/notes/porting-m1.md`, "How the tests establish it".
59. The model of the blitter's area mode is documented hardware behaviour, not derived from the original, so the comparison cannot catch a mistake in the model; one test, `test_the_blit_writes_exactly_the_shape_box`, is independent of it. Source: `re/notes/porting-m1.md`, "What that proves and what it does not".

## Paula

60. Paula has four channels; each has the address of a sound sample in chip memory, a length in words, a period and a volume from 0 to 64, and plays its bytes without the processor. Source: `SPEC.md` 6.5 (four channels, pointer, length, period, volume, DMA); `re/notes/sound.md`, the slot table (volume 0 to 64); HRM 5 **(reference)** for the playing by DMA.
61. The period is the number of colour clocks each byte is held; on PAL 3,546,895 colour clocks a second (NTSC 3,579,545); a smaller period is a higher pitch. Source: `re/notes/sound.md`, "The slots and what they play" and the engine paragraph; `SPEC.md` 6.5.
62. Channels 0 and 3 go to the left, 1 and 2 to the right. Source: `SPEC.md` 6.5.
63. A channel switched on takes its address and length and raises its interrupt request at once; at the end of its bytes it takes them again, raises the request again and plays on, until it is switched off. Source: `SPEC.md` 6.5; `re/notes/headless.md`, "The audio channels".
64. The eight sound effects are files of signed 8-bit values without a header. Source: `re/notes/sound.md`, "The samples".
65. `sounds/boom` is 5,466 bytes; slot 4, the burst of a bomb or a rocket, plays it once on channel 2 at period `0x1F4`, 500, which on PAL lasts 0.77 s. Source: `stat`; `re/notes/sound.md`, the slot table; computed 5,466 x 500 / 3,546,895 = 0.7705 s.
66. One byte at period 500 lasts about 0.14 ms (141 microseconds); 100 bytes about 14 ms. Source: computed from claim 61.
67. The effects engine has eight slots, two per channel; the tick switches them on and off and moves their volume and period; the first slot of a pair that is on gets the channel. Source: `re/notes/sound.md`, "Two layers" and "The slots and what they play".
68. A sound the tick asks for is started by the engine's VBlank server, `soundfx_vblank` (`0x01EC64`); the audio interrupt's handler `audio_irq` (`0x01EBAA`), at the level-4 vector `0x70`, counts a sound's repeats and stops it. Source: `re/notes/sound.md`, "The channel layer"; `SPEC.md` 3.4, last paragraph.
69. The music is a separate small program, `songplay` (5,148 bytes), with the song data `wofsongs` (41,328 bytes), both loaded with dos's `LoadSeg`. Source: `re/notes/music.md`, "The two files" and "The game's calls"; `SPEC.md` 3.4, the `LoadSeg` row; `stat`.
70. The player's beat comes from CIA-A's timer A, which counts the E clock, 709,379 a second on PAL; songs 1 to 4 set it so that a tick comes every 14,592 cycles, 20.57 ms, a little more than one VBlank (1.0285). Source: `re/notes/music.md`, "The timer".
71. The timer's lower byte, which nothing writes, is taken at its power-up value; that is the one assumption the music's tempo rests on; chapter 18 tells it. Source: `re/notes/music.md`, "The timer"; `SPEC.md` 6.5; `book/BOOK.md` 3, chapter 18.
72. The port's Paula is the model the headless original runs: four channels in a time of their own, the same restarts and interrupts; the core mixes the channels, and the two logs of sound sample starts are compared. Source: `SPEC.md` 6.5, second paragraph; `re/notes/headless.md`, "The audio channels".
73. The figure `sample-boom`: the whole of `sounds/boom`, and 100 of its bytes enlarged, each held as a step. Source: the figure's manifest entry.

## The VBlank

74. The VBlank is the moment the beam has finished the picture and goes back to the top: 50 a second on PAL, 60 on NTSC. Source: the glossary entry; `SPEC.md` 6.2, Clock.
75. An interrupt makes the processor leave what it is doing, run a short routine and go back. Source: the term's definition in the book's words; the game's use: `re/notes/headless.md`, "Scheduling" (the servers called as an interrupt calls them, the registers of the parked program).
76. The game installs two VBlank servers with exec's `AddIntServer`: `soundfx_vblank` at priority 30 and `vblank_server` (`0x011754`) at priority −10. Source: `re/notes/headless.md`, "Scheduling"; `re/notes/sound.md`, "The channel layer"; `SPEC.md` 3.4.
77. `vblank_server` counts the VBlanks and on every fourth takes one input byte into a queue of at most six; it also scrolls the ticker one pixel. Source: `SPEC.md` 3.3; `re/notes/display.md`, "The play screen line by line".
78. A pass begins by waiting for a VBlank (`wait_vblank` `0x01AA3E`), the first after the previous pass installed its list; the picture a pass draws appears at the VBlank after the pass ends. Source: `re/notes/display.md`, "Double buffering and the swap".
79. On a real PAL Amiga a pass takes two VBlanks in a quiet scene. Source: `re/notes/passes.md`, "What the film of the real machine shows"; chapter 1.
80. The program never asks whether it runs at 50 or 60. Source: `re/notes/random.md`, "Video rate".
81. In the port, the shell's clock issues the VBlanks, 50 or 60 a second of emulated time, each followed by a pass. Source: `SPEC.md` 6.2, Clock; `SPEC.md` 3.4, the `AddIntServer` row.

## The little of AmigaOS the game uses

82. The operating system's routines come in libraries, which a program opens by name and calls through a table of jumps at negative offsets from the library's base. Source: `re/notes/ffp.md`, "How the game reaches it" (offsets −30 to −84); `re/notes/keys.md`, "Raw code to character" (LVO −48); `re/notes/headless.md`, "Memory map" (library bases and their jump tables).
83. The game builds its own display with graphics.library and otherwise does its own work; it closes the Workbench at start. Source: `SPEC.md` 3.4, opening sentence and the intuition row; `SPEC.md` 3.3, step 1.
84. Files: dos's `Open`, `Read`, `Write`, `Seek`, `Close` and the directory calls; the load and save dialog walks the game's directory with `ExNext`. The port: a read-only file system built from the disk's files, writes going to the browser's storage. Source: `SPEC.md` 3.4, the first dos row.
85. Memory: exec's `AllocMem`. The port: one static arena. Source: `SPEC.md` 3.4.
86. The VBlank: exec's `AddIntServer`. The port: the shell's clock. Source: `SPEC.md` 3.4.
87. The font: the load and save dialog, the name entry and the file list draw with graphics.library's `Text` and never set a font, so they show the system font, topaz 8, from the ROM; the story scroller and the briefing use the game's own font from the disk, `newarmyfont` (`story_screen` through `text_draw_justified`, `mission_briefing` through `text_draw_c`). The port reads topaz 8 from the ROM when it is built. Source: `re/notes/system-font.md`, opening; `re/notes/drawing.md`, "Text"; `re/functions.csv`, the calls of `mission_briefing`; `SPEC.md` 3.1.
88. The keymap: a key arrives as a raw code, which names the key's position; the game turns it into a character through console.device's `RawKeyConvert` with the system's default keymap, taking a key only when exactly one character comes back. The port: a table made at build time by running the ROM's own `RawKeyConvert`. Source: `re/notes/keys.md`, "Raw code to character: console.device"; `re/notes/input.md`, "Keyboard and mouse"; `SPEC.md` 3.4, the device row.
89. The floating point: mathffp.library in the ROM, nine operations, of which the tick's two routines use six. The port: `src/ffp.c`, bit for bit in integer code. Source: `SPEC.md` 3.4, the mathffp row; `re/notes/ffp.md`.
90. The ROM is Kickstart 1.3, revision 34.5, 262,144 bytes; it is not in the repository: whoever builds the port places their own copy, which `tools/rom.py` checks. Source: `CLAUDE.md`, Rules; `re/notes/system-font.md`, "The ROM".
91. The headless original runs the ROM's own mathffp routines and `RawKeyConvert`, found in the ROM by their contents. Source: `re/notes/headless.md`, "Game logic uses floating point" and "The keyboard needs the ROM too".

## The sidebars

92. (How we know) The headless original maps the custom chips' addresses as plain memory: the game's writes to the copper's and the blitter's registers land there and change nothing, and every wait for the blitter falls through, because its busy bit reads as 0. Reads of `VHPOSR` take the next value of the entropy stream, and `JOY1DAT` and CIA-A's port are set from the run's script; Paula's audio side and CIA-A's timer A are a model. Source: `re/notes/headless.md`, "What runs and what does not", "Memory map", "Entropy", "Scheduling"; `re/notes/drawing.md`, "Consequences".
93. (How we know) That a run without a picture is valid rests on the read-back finding, claim 57. Source: `re/notes/drawing.md`, Summary.
94. (For the developer) The registers and addresses: the custom chips from `0xDFF000`; `VHPOSR` `0xDFF006`; `JOY1DAT` `0xDFF00C`, the stick in port 2; `BLTSIZE` `0xDFF058`, whose write starts a blit; `COP1LC` `0xDFF080`; the fire buttons in bits 6 and 7 of CIA-A's port register at `0xBFE001`, which the game reads for port 1 at `0xBFE0FF`; the audio interrupt's vector at `0x70`. Source: `re/notes/random.md`; `re/notes/input.md`; `re/notes/porting-m1.md`; `re/notes/display.md`; `re/notes/headless.md`, "What runs and what does not".
95. (For the developer) The port's files: `src/draw.c` (the blit), `src/audio.c` (Paula), `src/sound.c` (the effects engine), `src/music.c` (the player), `src/ffp.c` (the floating point), `src/rand.c` (the entropy stream), `src/fs.c` (the file system). Source: `re/notes/porting-m1.md`; `SPEC.md` 6.5; `re/notes/porting-m8.md` (the file list); `re/notes/headless.md`, "Entropy"; `SPEC.md` 3.4.

## Handed to chapter 3

96. Chapter 3 takes the disk: the ADF and its files, the executable's hunks, Manx Aztec C with its 16-bit `int`, the data reached through A4, and why the tables and texts are extracted at build time. Source: `book/BOOK.md` 3, chapter 3.
97. The disk carries 55 files the port takes. Source: chapter 1's fact sheet, claim 40 (`SPEC.md` 5, step 2).

## The chapter references the prose makes, each checked against `book/BOOK.md` 3

| Reference | Where in the prose | The outline's chapter |
|---|---|---|
| chapter 1 | the opening, the VBlank, the tempo | 1, What faithful means |
| chapter 3 | the 68000 (A4), the end | 3, The disk: the hunks, Manx Aztec C, the data reached through A4 |
| chapter 4 | the 68000 | 4, Reading the executable: the listing |
| chapter 6 | How we know | 6, The headless original |
| chapter 7 | the copper (the fades) | 7, Time: the fade step |
| chapter 11 | the copper | 11, The display: the copper lists, the per-row palettes |
| chapter 12 | the blitter | 12, Shapes: the blit through the blitter |
| chapter 18 | Paula | 18, Sound and music: the tempo that rests on one assumption |
| chapter 19 | AmigaOS | 19, The front end and the keys: the keymap from the ROM |

## Counts and where they were counted

| Count | Value | Where, and the command |
|---|---|---|
| `rand_beam`'s call sites | 43 | `SPEC.md` 3.3; `re/notes/random.md` |
| `rand_beam`'s instructions | 7 | `sed -n` over `re/Wings.lst` from the label `rand_beam:` to `0x0203D8` |
| one view's bitplanes | 44,240 bytes (`0xACD0`) | `re/notes/display.md`, "Memory"; `python -c "print(0xACD0, 40*162*5+80*37*4)"` |
| both views | 88,480 bytes (`0x159A0`) | the same; `python -c "print(0x159A0)"` |
| copper list buffers | 3 of 1,000 bytes | `re/notes/display.md`, "Memory" |
| `MaskBuffer` | 1,040 bytes | `re/notes/drawing.md` |
| opaque shapes | 11 | `re/notes/drawing.md`, "What `shape_draw` does, exactly" |
| shape containers on the disk | 12 | `ls original/disk/Wings_of_Fury/shapes/*.shp \| wc -l` |
| shapes | 1,049 | `re/notes/porting-m1.md`; `tools/ppkc.py` `parse()` over the twelve files |
| shapes of `hellcat.shp`, five-plane ones | 116, 90 | `parse()` of the file, masks `(1, 2, 4, 8, 16)` counted |
| `hc05` | 48 x 13, colours 19 to 31 | `to_indexed()` of `hc05` printed |
| sea colours that differ by day | 15 (2 to 15 and 24) | `re/notes/display.md`, "Day and night" |
| ticker ramp | 10 lines | `re/notes/display.md` |
| fade steps | 16 | `re/notes/display.md`, "Fades" |
| PAL frame | 313 lines x 227 = 71,051 colour clocks | `SPEC.md` 6.5; computed |
| first picture line | beam line 44 (`0x2C`); last 257 | `re/notes/display.md` |
| colour clocks a second | 3,546,895 PAL, 3,579,545 NTSC | `SPEC.md` 6.5 |
| sound effect files | 8 | `ls original/disk/Wings_of_Fury/sounds` |
| `sounds/boom` | 5,466 bytes, 0.77 s at period 500 | `stat -f %z`; `python -c "print(5466*500/3546895)"` |
| `songplay`, `wofsongs` | 5,148 and 41,328 bytes | `stat -f %z` |
| `wofsongs`'s DATA hunk | 39,020 bytes | `re/notes/music.md` |
| the music's tick | 14,592 E cycles, 20.57 ms, 1.0285 VBlanks | `re/notes/music.md`; `python -c "print(0x38FF+1, 14592/709379)"` |
| VBlank servers | 2, priorities 30 and −10 | `re/notes/headless.md`, "Scheduling" |
| input queue | at most 6 | `SPEC.md` 3.3 |
| the ROM | 262,144 bytes | `CLAUDE.md`, Rules |
| mathffp operations | 9, six used by the tick | `SPEC.md` 3.4 |

## Figures

At most five; three new, two of them made by new makers of `book/tools/figures.py`.

- `amiga-chips.svg` (new, drawn by hand under `book/docs/figures/`): the 68000 and the custom chips (the copper, the blitter, the display, Paula) around chip memory, with what the game keeps there; the ROM with the operating system's parts the game uses; other memory reached by the processor alone; the CIAs. Its colours from the palettes, checked by the build.
- `planes-hellcat.png` (new maker `planes`): the shape `hc05` of `hellcat.shp`, the Hellcat in level flight, taken apart into its five planes, each shown as bits, with the marked pixel's bit under each, then put together as colour numbers (shades from 0 to 31) and through `wingspalette`.
- `beam-copper.svg` (new, drawn by hand): the play screen as the beam draws it, line by line, with the copper's waits at the lines where the list changes something (the playfield, the split line, the blank line, the dashboard, the blank line, the ticker's ramp), and the vertical blank below the picture, where the beam returns to the top and the VBlank comes.
- `mission-palettes.png` (existing): the per-row palettes of the first mission's picture, the copper's effect as the port keeps it.
- `sample-boom.png` (new maker `sample`): `sounds/boom` as a waveform, the whole and 100 bytes enlarged with each byte held as a step, time in milliseconds at the burst's period 500 on PAL.

## Listings

- `rand_beam` (`kind = "asm"`), `0x0203BE` to `0x0203D8`, seven instructions: the 68000's machine code as the listing shows it, a read of a custom chip's register among them.

## Terms and glossary entries

Introduced in chapter 2, in bold with an entry: 68000, assembly language, beam, bitplane, blitter, chip memory, CIA, copper, custom chips, interrupt, Kickstart, library, machine code, Paula, period, register, VBlank. The entries Bitplane, Blitter, Copper, Paula and VBlank exist and are completed: Blitter loses "while the processor goes on with other work" and Paula "the disk and the serial port", neither of which the notes state. Used from chapter 1 without a new definition: palette, PAL, sound sample, input byte, input sample, pass, logic tick, headless original, fast floating point. Defined in passing without an entry: the listing (chapter 4's), double buffering, high and low resolution, the stack pointer, the program counter, direct memory access. No bare "sample".

## Sidebars

- How we know: what the headless original does with the custom chips, and why a run without a picture is valid (claims 92, 93).
- How we know: the blit compared through the original's register programme (claims 58, 59).
- For the developer: the registers and the port's files (claims 94, 95).
- What went wrong: none. The notes record no mistake of the work about this chapter's subjects; the emulator's memory-form shift is chapter 5's.

## Left to later chapters

The disk, the hunks, Manx Aztec C and A4 (3); reading the listing, compiled C against hand-written assembly (4); the oracle (5); the headless original in full (6); the fades' duration and the film (7); the display, the copper lists in full, day and night (11); shapes, mirrors and clipping (12); the flight model on the floating point (14); the effects engine and the music in full, the tempo (18); the keys and the keymap (19).

## Unsourced

Kept out of the draft: the processor's clock rate; the names of the chips that hold the copper, the blitter and the display (Agnus, Denise); the size of chip memory in an Amiga 500; that Paula also serves the disk and the serial port; that the blitter works while the processor goes on with other work, which the notes do not state for this game; the manual's remark that some sound effects may be left out on machines with 512 KB (page 3), which no note confirms in the code.
