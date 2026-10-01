# Fact sheet: chapter 2, The Amiga in twenty minutes

Every claim the chapter makes, one line each, with its source, in the order of the chapter. A claim without a source goes to the list at the end and stays out of the draft. A general fact about the Amiga or the 68000 that the repository's notes do not state is sourced in a reference work outside the repository, named with its chapter or section, and marked **(reference)**, so that the fact-check can weigh it; a fact the notes state about this game is always sourced in the notes. Two reference works are cited:

- *Amiga Hardware Reference Manual*, Commodore-Amiga, third edition (Addison-Wesley, 1991), cited as HRM with the chapter: 1 "Introduction" (the machine, its custom chips, the CIAs and the clocks), 2 "Coprocessor Hardware", 3 "Playfield Hardware", 5 "Audio Hardware", 6 "Blitter Hardware", 7 "System Control Hardware".
- *M68000 Family Programmer's Reference Manual*, Motorola (M68000PM/AD), cited as PRM with its section 1, "Introduction": the integer unit's programming model and its data formats.

## Opening

1. The game's Amiga version asks for an Amiga 500, 1000 or 2000 with at least 512 KB of memory and a joystick. Source: `original/manual.txt`, page 2 (cited, not quoted).
2. The chapter covers only what the port needed, each hardware topic tied to what this game does with it; the deep dives are Part II. Source: `book/BOOK.md` 3, chapter 2 and Part II.

## The machine around the game

3. The Amiga is a Motorola 68000 processor beside a set of the Amiga's own chips, the custom chips, which make the picture, draw and play sound, and which, once set to work, work without the processor. Source: HRM 1 **(reference)**; the game's use of them: `SPEC.md` 3.4, the two "custom chips" rows.
4. The custom chips are three: Agnus holds the copper and the blitter, Denise turns the picture's data into the signal for the screen, Paula plays the sound and also serves the disk drive, the serial port and the interrupts. Source: HRM 1 **(reference)**, the chips' descriptions; HRM 5 and 7 **(reference)** for Paula's audio and its interrupt registers; the name Paula for the sound side also in `SPEC.md` 6.5 and `re/notes/headless.md` ("Paula's audio side").
5. An interrupt is a signal from the hardware that makes the processor put aside what it is doing, run a short routine and carry on where it was. Source: the term's definition in the book's words; the game's use: `re/notes/headless.md`, "Scheduling" (the servers called as an interrupt calls them, on a stack of their own, the parked program's registers kept).
6. The custom chips are driven through their registers at fixed addresses from `0xDFF000`; the game keeps that base in `custom_base` (`0x026938`) and writes the registers directly: `COP1LC` with copper lists of its own, the blitter's registers from the blitter library, the audio registers, `INTENA`, `INTREQ`. Source: `re/notes/drawing.md`, "The blitter library"; `SPEC.md` 3.4, the custom-chip rows.
7. The game reads few custom-chip registers: the sound code reads the interrupt bits (`INTENAR`, `INTREQR`), the blitter's busy bit is read only to wait for it, and the two that matter are `JOY1DAT` (the stick) and `VHPOSR` (the beam's position). Source: `re/notes/drawing.md`, "Read-back", the table's first two rows.
8. The CIAs are the Amiga's two interface chips, which serve its ports and carry timers; they sit at `0xBFD000` to `0xBFEFFF`; the game reads the fire button from CIA-A (bits 6 and 7 of its port register), and the music player takes CIA-A's timer A. Source: HRM 1 **(reference)** for their role; `re/notes/headless.md`, "Memory map"; `re/notes/input.md`, "Fire button and the tap/hold discrimination"; `re/notes/music.md`, "The timer". The CIA is an 8520 (`re/notes/music.md`, "The timer": "the 8520's reset state").
9. The ROM and its contents are called Kickstart; it holds the core of the operating system, AmigaOS (the image carries exec), and among it the floating point (`mathffp.library`), the key conversion (`console.device`) with the default keymap, and the system font. Source: `re/notes/system-font.md`, "The ROM" (`exec 34.2`) and "Where the fonts are"; `re/notes/headless.md`, "Game logic uses floating point" and "The keyboard needs the ROM too".

## The 68000

10. The 68000 runs at about seven million cycles a second on a PAL Amiga (7,093,790; the E clock of claim 72, 709,379 a second, is a tenth of it, and the colour clock of claim 63, 3,546,895, a half). Source: HRM 1 **(reference)**; `re/notes/music.md`, "The timer" (the E clock).
11. The 68000 has eight data registers, D0 to D7, and eight address registers, A0 to A7, each of 32 bits; A7 is the stack pointer; a program counter holds the address of the next instruction. Source: PRM 1 **(reference)**; the listing shows `d1-d7/a0-a6` saved and `-(a7)` as the stack (`re/Wings.lst`, `text_width` `0x01591E`, the `book/docs/generated/listings/asm/text_width.lst` extract).
12. An instruction works on a byte (8 bits), a word (16) or a long (32), written `.b`, `.w`, `.l` after its name. Source: PRM 1 **(reference)**; `SPEC.md` 7.1 (`muls.w` multiplies two 16-bit values into 32 bits, `ext.l` widens a 16-bit value).
13. Machine code is the processor's instructions as numbers in memory; assembly language is their written form, one instruction a line. Source: the terms' definitions in the book's words.
14. The listing, `re/Wings.lst`, prints each instruction with its address, its bytes of machine code in hexadecimal, and the instruction in assembly language; hexadecimal numbers carry a `$` there, as Motorola's assemblers write them, where this book writes `0x`. Source: `re/Wings.lst` (any line, e.g. `0x0203BE`); `book/BOOK.md` 4, point 3 (the book's hex).
15. `rand_beam` (`0x0203BE` to `0x0203D8`, seven instructions, hand-written assembly) is the game's only random source in use, the one chapter 1 told of without naming it, called from 43 places. Source: `re/Wings.lst` at the range; `re/functions.csv` (kind `asm`); `SPEC.md` 3.3; `re/notes/random.md`, "The generator" (43 call sites; `rand_lcg_unused` beside it, which nothing calls); chapter 1's fact sheet, claim 22.
16. What it does, line by line: loads the word `rand_seed_const` (`0x026912`) into D0; multiplies it, signed, by `0x1AFB` (`muls.w`); adds `0x1FCCD` as a long; reads the word at `0xDFF006`, `VHPOSR`, into D1; exclusive-ors D1 into D0; stores the word into `rand_state` (`0x026910`); returns (`rts`), the result in D0. Source: `re/Wings.lst` `0x0203BE`-`0x0203D8`; `re/notes/random.md`, "The generator" (the same in C).
17. `-$46ec(a4)` is `rand_seed_const`: `0x02AFFE` less `0x46EC` is `0x026912`; the listing prints the variable's name beside the instruction; how A4 leads to the program's variables is chapter 3's. Source: `SPEC.md` 3.2 (A4 is `0x02AFFE`, the listing prints the name); computed; `book/BOOK.md` 3, chapter 3 ("the data reached through A4").
18. `VHPOSR` holds the low 8 bits of the beam's line in its high byte and its horizontal position in its low byte; so the result is a constant combined with where the beam happens to be. Source: `re/notes/random.md`, "The generator" and the paragraph after it.
19. A routine returns its result in D0: true of the C routines and of `rand_beam`. Source: `SPEC.md` 3.2 ("Result in D0"); `re/notes/random.md`.
20. The port answers that one read from its reproducible stream. Source: `SPEC.md` 7.3; `re/notes/random.md`, "Consequences".
21. The game's 223 routines written in C were translated by a compiler and look different in the listing; chapter 4 reads the listing. Source: `SPEC.md` 3.2 (616 routines, 223 of them C); `book/BOOK.md` 3, chapter 4.

## Chip memory

22. Chip memory is the part of the Amiga's memory that the custom chips can read and write by themselves, without the processor (direct memory access); memory added beyond it, where a machine has any, only the processor reaches. Source: HRM 1 **(reference)**; HRM 7, "DMA control" **(reference)**.
23. A program asks the operating system for chip memory by a flag, as the game's `load_file_chip` (`0x01FECA`) does: it passes `MEMF_CHIP`, `MEMF_PUBLIC` and `MEMF_CLEAR` (`0x10003`, the `pea` at `0x01FECE`) to `load_file`. Source: `re/names.txt`, the line of `01feca`; `re/Wings.lst` `0x01FECA`-`0x01FEDE`.
24. `display_init` (`0x016670`) allocates the display's memory from chip memory once: the bitplanes of both views, `0x159A0` bytes; three copper list buffers of 1,000 bytes each; the ticker's plane; the sprite pointers' zero block. Source: `re/notes/display.md`, "Memory".
25. One view's bitplanes are `0xACD0`, 44,240 bytes, exactly the play screen: 40 x 162 x 5 for the playfield plus 80 x 37 x 4 for the dashboard; both views together 88,480. Source: `re/notes/display.md`, "Memory"; computed.
26. `MaskBuffer`, the blit mask's scratch space, 1,040 bytes, is in chip memory. Source: `re/notes/drawing.md`, Summary.
27. A shape container is loaded whole into chip memory; the table of pointers that names the shapes goes into public memory, ordinary memory the processor alone reads. Source: `re/notes/shapes.md`, Summary and "Container and lookup" (`shapes_load` with `load_file_chip`, `shapes_resolve` with public memory).
28. The eight sound effects are loaded into chip memory. Source: `re/notes/sound.md`, "The samples".
29. The song data `wofsongs` is a hunk file whose DATA hunk of 39,020 bytes, the songs, the voices and the sound samples of the music, goes into chip memory. Source: `re/notes/music.md`, "The two files"; `SPEC.md` 3.1.
30. The port has one static arena for all of it, from which the core hands out what the original asked the operating system for; the browser has no chip memory, and the game's out-of-memory paths are unreachable. Source: `SPEC.md` 3.4, the `AllocMem` row; `SPEC.md` 6.1 ("one static arena replaces `AllocMem`").

## Bitplanes

31. A picture is kept as bitplanes: one plane holds one bit of every pixel's colour number; the display takes the bit of each plane for a pixel and puts them together into its colour number, plane 1's bit the lowest. Five planes give numbers 0 to 31, 32 colours. Source: HRM 3 **(reference)**; for the shapes, `tools/ppkc.py`, `to_indexed` (each stored plane ORs its mask into the pixel); `re/notes/display.md`, "Screens" (`BPLCON0` `0x5200` for 5 planes, 32 colours).
32. The colour number goes through the palette, 32 colour registers (`COLOR00` upward) of 12-bit words, 4,096 colours. Source: `re/notes/display.md`, Summary and "The copper builder", step 4; chapter 1 introduced the palette.
33. The play screen: the playfield, 320 x 162 pixels in low resolution with 5 planes (32 colours), at line 0; the dashboard, 640 x 37 in high resolution with 4 planes (16 colours), at line 163; the message ticker, 640 x 13 in high resolution with 1 plane, at line 201; lines 162 and 200 blank; 214 lines in all. Source: `re/notes/display.md`, Summary and "The play screen line by line"; `SPEC.md` 6.4.
34. A high-resolution pixel is half as wide as a low-resolution one; the port's output is 640 wide with the low-resolution pixels doubled. Source: `SPEC.md` 6.4 ("The shell output is 640 pixels wide with low-resolution pixels doubled").
35. A shape stores its own planes, each with the destination plane it lands in (the masks at `+14`). Source: `re/notes/shapes.md`, "Record header, complete".
36. `hellcat.shp` has 116 shapes, 90 of them with five planes landing in planes 1, 2, 4, 8 and 16 in that order. Source: `tools/ppkc.py` `parse()` over `original/disk/Wings_of_Fury/shapes/hellcat.shp` (the command in "Counts"); `re/notes/shapes.md` (116 shapes of `hellcat.shp`).
37. The shape `hc05`, the Hellcat in level flight, is 48 x 13 pixels with five planes; its pixels use colours 19 to 31 only, so its fifth plane, worth 16, is set wherever the aircraft is; the marked pixel (x 22, y 8) has colour 21: planes 1, 3 and 5 set, 1 + 4 + 16. Source: `tools/ppkc.py` `to_indexed()` of `hc05` (the command in "Counts"); figure `planes-hellcat`.
38. Colour 21 of `wingspalette` is `#4477AA`, a mid blue. Source: `book/tools/figures.py` `palette('wingspalette')`.
39. The port keeps 8-bit indexed framebuffers, one byte a pixel holding the colour number, and applies the palette at presentation; shapes are converted from planes to such pixels once, at load. The same numbers in every pixel are the second part of chapter 1's definition. Source: `SPEC.md` 6.4, first two paragraphs; `SPEC.md` 1, "Definition of faithful", point 2.

## The beam and the copper

40. The display draws the picture with a beam that sweeps each line from left to right and the lines from top to bottom; above and below the picture lie the border and the lines of the vertical blank. Source: HRM 2 and 3 **(reference)**; `re/notes/random.md` (`VHPOSR` holds the beam's line and position on the line).
41. A PAL frame is 313 lines of 227 colour clocks, 71,051 clocks. Source: `SPEC.md` 6.5 ("a real PAL frame is 313 lines of 227 colour clocks"); `re/notes/porting-m8.md`, "What the model leaves out".
42. The game's picture begins at beam line `0x2C` (44), its display line 0, and the play screen ends at beam line 257. Source: `re/notes/display.md`, "The play screen line by line" (display line 0 is beam line `0x2C`, the picture ends at beam line 257) and the viewport table (+0xA6).
43. The copper, a small processor inside Agnus, follows a list of simple instructions in step with the beam; the game uses two kinds: a wait for a beam position, and a move that writes a value into one of the chips' registers (the copper has a third, a skip, which the game does not use). Source: HRM 2 **(reference)**; `re/notes/display.md`, "The copper builder" (`WAIT (0, y − 1)`, moves to `COLORxx`, `BPLCON0`), `cop_wait` (`0x019A9C`).
44. The game builds no operating-system display: it writes its own copper lists with a small C library (`0x019958` to `0x01A1F4`) and points the hardware at a list by writing `COP1LC` (`0xDFF080`). The operating system's display routines are linked in and never called. Source: `re/notes/display.md`, Summary; `SPEC.md` 3.4, the graphics row of `InitVPort` and the others.
45. The play screen's list, per area: a wait for the line above the area, `BPLCON0` off (the blank line), the area's colours, its bitplane pointers and its window, then a wait for its first line and `BPLCON0` with its depth and resolution. Source: `re/notes/display.md`, "The copper builder", steps 2 to 5.
46. The playfield's list holds a second wait at the split line, followed by a move for each colour where the sea's palette differs from the sky's: by day colours 2 to 15 and 24, fifteen moves. At lines 162 and 200 the list switches the planes off for a blank line and then sets up the next area (claim 45). Source: `re/notes/display.md`, "The copper builder", step 6, and "Day and night".
47. The split line is computed every pass and rewritten in the back list (`cop_set_split_line` `0x01876E`); that it follows the horizon is inferred. On the carrier's deck it is 151 (`0x97`). Source: `re/notes/display.md`, "The split line"; the figure `mission-palettes` (rows 0 to 150 the sky's, 151 to 161 the sea's).
48. The ticker gets ten waits, one per line from 201, each with a new `COLOR01`: the greys 777, 999, BBB, DDD, FFF, DDD, BBB, 999, 777, 555, brightest on the fifth line, the middle of the ramp. Source: `re/notes/display.md`, "How colours change", the ticker ramp row.
49. The sky's flash is one value poked into the built list, `COLOR01` of the back list. Source: `re/notes/display.md`, "How colours change", the sky flash row.
50. Double buffering: two complete views, each with its bitplanes and its copper list; a pass draws into the back view and installs the back view's list, one write to `COP1LC`; the hardware takes the new list at the next vertical blank. Source: `re/notes/display.md`, Summary and "Double buffering and the swap".
51. A fade runs 16 steps, rebuilding and installing the list at each, with no wait inside its loop, so its length is processor time; chapter 7 tells how the port times it. Source: `re/notes/display.md`, "Fades"; `book/BOOK.md` 3, chapter 7 (the fade step).
52. The game uses no hardware sprites and no colour cycling. Source: `re/notes/display.md`, Summary and "Memory" (`null_sprite`, "The game uses no sprites").
53. The port has no copper: it keeps a palette for every row of its picture, and the copper's effects, the split, the ramp, the flash and the fades, become further palettes for further rows. Source: `SPEC.md` 6.4 ("The per-row palette interface expresses all of these") and 6.6; `re/notes/porting-m1.md`, "Decisions the port made" ("A screen is a stack of bands").
54. The figure `mission-palettes`: at VBlank 759 of the mission run, rows 0 to 150 through `wingspalette`, 151 to 161 through `ocean.palette`, 162 and 200 through the black palette 0, 163 to 199 through `iff-dash` (16 colours), 201 to 209 through five palettes rising and falling (one palette for each grey of the ramp), 210 to 213 through a sixth, the ramp's last grey. Source: `book/docs/generated/figures/mission-palettes.png`, looked at; `book/figures.toml`.

## The blitter

55. The blitter copies and combines rectangles of memory, one bitplane at a time: up to three sources, A, B and C, and a destination, D, combined bit by bit by a logic function chosen by a number, the minterm. Once started it works by itself, and the processor is free meanwhile. Source: HRM 6 **(reference)**; one plane at a time: `re/notes/drawing.md`, "The blitter library" (`rect_fill`, one blit per plane); `re/notes/drawing.md`, "What `shape_draw` does, exactly" (A the mask, B the plane, C the destination, minterm `0xCA`, D = A·B + ¬A·C).
56. All shape, rectangle and line drawing goes through one library of hand-written assembly at `0x0209BC` to `0x0215D8`, and every routine of it drives the blitter; the scene routines decide what to draw and call it. Source: `SPEC.md` 3.2; `re/notes/drawing.md`, Summary.
57. To draw a shape, the processor writes the OR of its planes into `MaskBuffer`, which is the mask; the blitter then runs once per plane and writes, where the mask is set, the shape's bit, and keeps the background's bit where it is not. Source: `re/notes/drawing.md`, "What `shape_draw` does, exactly", steps 1 and 2 and "In hardware terms".
58. So colour 0 is see-through only in a shape that gets a mask; a shape whose plane is larger than 1,040 bytes gets none and is drawn opaque; eleven shapes are; the ten ship and carrier pieces among them contain no colour 0 at all and carry the sky's colour 1 around the hull. Source: `re/notes/drawing.md`, "What `shape_draw` does, exactly", the paragraph after "In hardware terms".
59. No game logic reads back what was drawn: no pixel, no mask, no blitter flag, no collision register; that makes the headless original, which draws nothing, possible. Source: `re/notes/drawing.md`, Summary and "Read-back" ("A headless run of the original without a blitter model is therefore valid").
60. (How we know) The port draws each shape per pixel on its indexed framebuffer with the original's clipping and draw order; the original's own `shape_draw` is run under emulation, the blitter's registers captured at every write to `BLTSIZE` (`0xDFF058`), which starts a blit, replayed through a model of the blitter, and compared pixel by pixel with the port's picture for every shape of every container at six positions, two clip rectangles and two backgrounds. Source: `SPEC.md` 6.4; `re/notes/porting-m1.md`, "How the tests establish it".
61. (How we know) The model of the blitter's area mode is documented hardware behaviour, not derived from the original, so the comparison cannot catch a mistake in the model; one test, `test_the_blit_writes_exactly_the_shape_box`, is independent of it. Source: `re/notes/porting-m1.md`, "What that proves and what it does not".

## Paula

62. Paula has four channels; each has the address of a sound sample in chip memory, a length in words, a period and a volume from 0 to 64, and plays its bytes without the processor. Source: `SPEC.md` 6.5 (four channels, pointer, length, period, volume, DMA); `re/notes/sound.md`, the slot table (volume 0 to 64); HRM 5 **(reference)** for the playing by DMA.
63. The period is the number of colour clocks each byte is held; on PAL 3,546,895 colour clocks a second (NTSC 3,579,545); a smaller period is a higher pitch. Source: `re/notes/sound.md`, "The slots and what they play" and the engine paragraph; `SPEC.md` 6.5.
64. Channels 0 and 3 go to the left, 1 and 2 to the right. Source: `SPEC.md` 6.5.
65. A channel switched on takes its address and length from its registers and raises its interrupt request at once; at the end of its bytes it takes them again, as they then stand, raises the request again and plays on, until it is switched off; so a program can hand it the next sound or stop it. Source: `SPEC.md` 6.5; `re/notes/headless.md`, "The audio channels".
66. The eight sound effects are files of signed 8-bit values without a header. Source: `re/notes/sound.md`, "The samples".
67. `sounds/boom` is 5,466 bytes; slot 4, the burst of a bomb or a rocket, plays it once on channel 2 at period `0x1F4`, 500, which on PAL lasts 0.77 s. Source: `stat`; `re/notes/sound.md`, the slot table; computed 5,466 x 500 / 3,546,895 = 0.7705 s.
68. One byte at period 500 lasts about 0.14 ms (141 microseconds); 100 bytes about 14 ms. Source: computed from claim 63.
69. The effects engine has eight slots, two per channel; the tick switches them on and off and moves their volume and period; the first slot of a pair that is on gets the channel, so that the player's guns drown the engine (slot 0, `machinegun`, before slot 1, `Engine`, on channel 0). Source: `re/notes/sound.md`, "Two layers" and "The slots and what they play" ("the guns drown the engine").
70. A sound the tick asks for is started by the engine's VBlank server, `soundfx_vblank` (`0x01EC64`). Source: `re/notes/sound.md`, "The channel layer"; `SPEC.md` 3.4, last paragraph.
71. The music is a separate small program, `songplay` (5,148 bytes), with the song data `wofsongs` (41,328 bytes), both loaded from the disk with dos's `LoadSeg` when a song is to play and they are not loaded. Source: `re/notes/music.md`, "The two files" and "The game's calls"; `SPEC.md` 3.4, the `LoadSeg` row; `stat`.
72. The player's beat comes from CIA-A's timer A, which counts the E clock, 709,379 a second on PAL; four of the five songs, 1 to 4, set it so that a tick comes every 14,592 cycles, 20.57 ms, a little longer than a VBlank's 20 ms (1.0285 VBlanks); song 0's comes every 15,616. Source: `re/notes/music.md`, "The timer".
73. The timer's lower byte, which nothing writes, is taken to keep its power-up value; that is the one assumption the music's tempo rests on; chapter 1 mentioned it, chapter 18 tells it. Source: `re/notes/music.md`, "The timer"; `SPEC.md` 6.5; `book/BOOK.md` 3, chapter 18; chapter 1's fact sheet, claim 94.
74. The port's Paula is the model the headless original runs: four channels in a time of their own, the same restarts and interrupts; the core mixes the channels, and the two logs of sound sample starts are compared. Source: `SPEC.md` 6.5, second paragraph; `re/notes/headless.md`, "The audio channels".
75. The figure `sample-boom`: the whole of `sounds/boom`, and 100 of its bytes enlarged, each held as a step. Source: the figure's manifest entry.

## The VBlank

76. The VBlank is the moment the beam has finished the picture and goes back to the top: 50 a second on PAL, 60 on NTSC. Source: the glossary entry; `SPEC.md` 6.2, Clock.
77. The VBlank reaches the program as an interrupt (claim 5). Source: `SPEC.md` 3.4, the `AddIntServer` row (VBlank).
78. The game installs two VBlank servers with exec's `AddIntServer`: `soundfx_vblank` at priority 30 and `vblank_server` (`0x011754`) at priority −10. Source: `re/notes/headless.md`, "Scheduling"; `re/notes/sound.md`, "The channel layer"; `SPEC.md` 3.4.
79. `vblank_server` counts the VBlanks and on every fourth takes one input byte into a queue of at most six, and a logic tick runs for every queued byte, which gives chapter 1's 12.5 ticks a second; it also scrolls the ticker one pixel, the processor shifting the plane, not the blitter. Source: `SPEC.md` 3.3; `re/notes/display.md`, "The play screen line by line"; `re/notes/drawing.md`, "Other drawing".
80. A pass begins by waiting for a VBlank (`wait_vblank` `0x01AA3E`), the first after the previous pass installed its list; the picture a pass draws appears at the VBlank after the pass ends. Source: `re/notes/display.md`, "Double buffering and the swap".
81. On a real PAL Amiga a pass takes two VBlanks in a quiet scene. Source: `re/notes/passes.md`, "What the film of the real machine shows"; chapter 1.
82. The program never asks whether it runs at 50 or 60. Source: `re/notes/random.md`, "Video rate".
83. In the port, the shell's clock issues the VBlanks, 50 or 60 a second of emulated time, each followed by a pass. Source: `SPEC.md` 6.2, Clock; `SPEC.md` 3.4, the `AddIntServer` row.

## The little of AmigaOS the game uses

84. The operating system's routines come in libraries, which a program opens by name and calls through a table of jumps at negative offsets from the library's base. Source: `re/notes/ffp.md`, "How the game reaches it" (offsets −30 to −84); `re/notes/keys.md`, "Raw code to character" (LVO −48); `re/notes/headless.md`, "Memory map" (library bases and their jump tables).
85. The game builds its own display and otherwise does its own work; it closes the Workbench, the Amiga's desktop, at start. Source: `SPEC.md` 3.4, opening sentence and the intuition row; `SPEC.md` 3.3, step 1.
86. Files: dos's `Open`, `Read`, `Write`, `Seek`, `Close` and the directory calls; the load and save dialog walks the game's directory with `ExNext`. The port: a read-only file system built from the disk's files, writes going to the browser's storage. Source: `SPEC.md` 3.4, the first dos row.
87. Memory: exec's `AllocMem`. The port: one static arena. Source: `SPEC.md` 3.4.
88. The VBlank: exec's `AddIntServer`. The port: the shell's clock. Source: `SPEC.md` 3.4.
89. The font: the load and save dialog, the name entry and the file list draw with graphics.library's `Text` and never set a font, so they show the system font, topaz 8, from the ROM; the story scroller and the briefing use the game's own font from the disk, `newarmyfont` (`story_screen` through `text_draw_justified`, `mission_briefing` through `text_draw_c`). The port reads topaz 8 from the ROM when it is built. Source: `re/notes/system-font.md`, opening; `re/notes/drawing.md`, "Text"; `re/functions.csv`, the calls of `mission_briefing`; `SPEC.md` 3.1.
90. The keymap: a key arrives as a raw code, which names the key's position, not its letter; the game turns it into a character through console.device's `RawKeyConvert` with the system's default keymap (taking a key only when exactly one character comes back, which the chapter leaves to chapter 19). The port: a table made at build time by running the ROM's own `RawKeyConvert`. Source: `re/notes/keys.md`, "Raw code to character: console.device"; `re/notes/input.md`, "Keyboard and mouse"; `SPEC.md` 3.4, the device row.
91. The floating point: mathffp.library in the ROM, nine operations, of which the tick's two routines use six. The port: `src/ffp.c`, bit for bit in integer code. Source: `SPEC.md` 3.4, the mathffp row; `re/notes/ffp.md`.
92. The ROM is Kickstart 1.3, revision 34.5, 262,144 bytes; three rows of the table (the font, the keys, the floating point) lead into it; it is not in the repository: whoever builds the port places their own copy, which `tools/rom.py` checks. Source: `CLAUDE.md`, Rules; `re/notes/system-font.md`, "The ROM".
93. The headless original runs the ROM's own mathffp routines and `RawKeyConvert`, found in the ROM by their contents; the port takes the font and the key table from the ROM when it is built (claims 89, 90). Source: `re/notes/headless.md`, "Game logic uses floating point" and "The keyboard needs the ROM too".

## The sidebars

94. (How we know) The headless original maps the custom chips' addresses as plain memory: the game's writes to the copper's and the blitter's registers land there and change nothing, and every wait for the blitter falls through, because its busy bit reads as 0. Reads of `VHPOSR` take the next value of the entropy stream, the port's; `JOY1DAT` and CIA-A's port are set from the run's script; Paula's audio side and CIA-A's timer A are a model, the port's (claim 74). Source: `re/notes/headless.md`, "What runs and what does not", "Memory map", "Entropy", "Scheduling"; `re/notes/drawing.md`, "Consequences".
95. (How we know) That a run without a picture is valid rests on the read-back finding, claim 59. Source: `re/notes/drawing.md`, Summary.
96. (For the developer) The registers and addresses: `VHPOSR` `0xDFF006`; `JOY1DAT` `0xDFF00C`, the stick in port 2; `BLTSIZE` `0xDFF058`, whose write starts a blit; `COP1LC` `0xDFF080`; the fire buttons in bits 6 and 7 of CIA-A's port register at `0xBFE001`, which the game reads for port 1 at `0xBFE0FF`; the audio interrupt's vector at `0x70`. Source: `re/notes/random.md`; `re/notes/input.md`; `re/notes/porting-m1.md`; `re/notes/display.md`; `re/notes/headless.md`, "What runs and what does not".
97. (For the developer) The port's files: `src/draw.c` (the blit), `src/audio.c` (Paula), `src/sound.c` and `src/music.c` (the effects engine and the music player), `src/ffp.c` (the floating point), `src/rand.c` (the entropy stream, the beam's stand-in), `src/fs.c` (the file system). Source: `re/notes/porting-m1.md`; `SPEC.md` 6.5; `re/notes/porting-m8.md` (the file list); `re/notes/headless.md`, "Entropy"; `SPEC.md` 3.4.

## Handed to chapter 3

98. Chapter 3 takes the disk: the ADF and its files, the executable's hunks, Manx Aztec C with its 16-bit `int`, the data reached through A4, and why the tables and texts are extracted at build time. Source: `book/BOOK.md` 3, chapter 3.

## The chapter references the prose makes, each checked against `book/BOOK.md` 3

| Reference | Where in the prose | The outline's chapter |
|---|---|---|
| Part II | the opening | chapters 11 to 20, the game inside |
| chapter 1 | the machine (Kickstart's floating point), the 68000 (chance), bitplanes (the definition), Paula (the tempo), the VBlank (12.5 ticks) | 1, What faithful means |
| chapter 3 | the 68000 (A4), What comes next | 3, The disk: the hunks, Manx Aztec C, the data reached through A4 |
| chapter 4 | the 68000, twice (how the listing was made; C against assembly) | 4, Reading the executable: the disassembler and the listing |
| chapter 6 | the second How we know | 6, The headless original |
| chapter 7 | the copper (the fades) | 7, Time: the fade step |
| chapter 18 | Paula | 18, Sound and music: the tempo that rests on one assumption |
| chapter 19 | AmigaOS | 19, The front end and the keys: the keymap from the ROM |

## Counts and where they were counted

| Count | Value | Where, and the command |
|---|---|---|
| the chapter's words | 3,946 | `wc -w book/docs/part-1/amiga.md`, the whole file with alt texts, captions, sidebars and the further reading |
| the 68000's clock on PAL | 7,093,790 a second ("about seven million") | HRM 1 **(reference)**; ten times the E clock of `re/notes/music.md` |
| `rand_beam`'s call sites | 43 | `SPEC.md` 3.3; `re/notes/random.md` |
| routines written in C | 223 of 616 | `SPEC.md` 3.2; `re/functions.csv` with `csv.DictReader` (kind C) |
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
| songs | 5 (0 to 4), four of them at latch `0x38FF` | `re/notes/music.md`, "The timer" |
| the music's tick | 14,592 E cycles, 20.57 ms, 1.0285 VBlanks | `re/notes/music.md`; `python -c "print(0x38FF+1, 14592/709379)"` |
| VBlank servers | 2, priorities 30 and −10 | `re/notes/headless.md`, "Scheduling" |
| input queue | at most 6 | `SPEC.md` 3.3 |
| the ROM | 262,144 bytes | `CLAUDE.md`, Rules |
| mathffp operations | 9, six used by the tick | `SPEC.md` 3.4 |

## Figures

Five, in the order of the chapter: two diagrams drawn by hand, two figures of new makers of `book/tools/figures.py`, one existing figure.

- `amiga-chips.svg` (new, drawn by hand under `book/docs/figures/`): the 68000 (the processor, runs the game's code, writes the chips' registers); across the top Agnus with the copper and the blitter, Denise with the display, Paula with four channels of sound, the interrupts and the disk; two-way arrows from each to chip memory, which holds the bitplanes of the two screens (88,480 bytes), the copper lists, the shapes, the sound effects and the songs, and to which the processor reaches too; at the bottom, on the processor's line alone, the CIAs (the music's timer, the fire button), the Kickstart ROM (the operating system's core: the floating point, the keymap, the font) and other memory where a machine has any. Claims 3, 4, 8, 9, 22 to 29. Its eleven colours are entries of the palettes, checked by the build.
- `planes-hellcat.png` (new maker `planes`, 828 x 690): `hc05` of `hellcat.shp` in seven rows: planes 1 to 5 as light bits on a dark box, each labelled with its worth, then the colour numbers as greys from black (0) to white (31), then the colours of `wingspalette`; the pixel at x 22, y 8 framed in gold in every row; beside the rows "bit 1, bit 0, bit 1, bit 0, bit 1", "21 = 1 + 4 + 16" and "colour 21, #4477AA". The maker checks that the planes it reads make the pixels of `tools/ppkc.py`'s `to_indexed()`. Claims 35 to 38.
- `beam-copper.svg` (new, drawn by hand): on the left the play screen at 1.5 units a line (the sky's playfield to line 150, the sea's palette to 161, the dashboard 163 to 199, the ticker 201 to 213, the blank lines 162 and 200 left black), the beam's first four lines with their dashed returns, and its dashed way back to the top after the picture, labelled with the frame's 313 lines and the VBlank; on the right the copper's list as five entries beside the lines where they act (line 0, beam line 44; the split line, 151 here, with the sea's 15 colours; lines 162 and 163; lines 200 and 201 to 210; the VBlank, where the list starts again) and a note that each entry waits for a line and writes registers. Claims 40 to 51, 76. Its ten colours are entries of the palettes, checked by the build.
- `mission-palettes.png` (existing): the per-row palettes of the first mission's picture, the copper's effect as the port keeps it. Claim 54.
- `sample-boom.png` (new maker `sample`, 1024 x 492): above, the whole of `sounds/boom` in gold, one column per eleven or so bytes from smallest to largest value, with ticks every 100 ms to 700 at period 500 on PAL and a frame around bytes 400 to 499; below, those hundred bytes as a staircase of five-pixel steps, labelled "bytes 400 to 499, 14.1 ms: each byte held for 500 colour clocks". Claims 66 to 68.

## Listings

- `rand_beam` (`kind = "asm"`), `0x0203BE` to `0x0203D8`, seven instructions: the 68000's machine code as the listing shows it, a read of a custom chip's register among them.

## Terms and glossary entries

Introduced in chapter 2, in bold with an entry: 68000, assembly language, beam, bitplane, blitter, chip memory, CIA, copper, custom chips, interrupt, Kickstart, library, machine code, Paula, period, register, VBlank. Twelve entries are new (68000, Assembly language, Beam, Chip memory, CIA, Custom chips, Interrupt, Kickstart, Library, Machine code, Period, Register); the five that existed (Bitplane, Blitter, Copper, Paula, VBlank) stand as they were, their general facts sourced here: the blitter working while the processor goes on (claim 55), Paula serving the disk, the serial port and the interrupts (claim 4). The interrupt is introduced with Paula in the first section and used again for the VBlank; the copper, the blitter and the beam are named in the first section's overview and in the figure before their own sections define them. Used from chapter 1 without a new definition: palette, PAL, sound sample, input byte, input sample, pass, logic tick, headless original, fast floating point. Defined in passing without an entry: the listing (chapter 4's), double buffering, high and low resolution, the stack pointer, the program counter, direct memory access. No bare "sample".

## Sidebars

- How we know: what the headless original does with the custom chips, and why a run without a picture is valid (claims 94, 95).
- How we know: the blit compared through the original's register programme (claims 60, 61).
- For the developer: the registers and the port's files (claims 96, 97).
- What went wrong: none. The notes record no mistake of the work about this chapter's subjects; the emulator's memory-form shift is chapter 5's.

## Left to later chapters

The disk, the hunks, Manx Aztec C and A4 (3); reading the listing, compiled C against hand-written assembly (4); the oracle (5); the headless original in full (6); the fades' duration and the film (7); the display, the copper lists in full, day and night (11); shapes, mirrors and clipping (12); the flight model on the floating point (14); the effects engine and the music in full, the tempo (18); the keys and the keymap (19).

## Unsourced

Kept out of the draft: the size of chip memory in an Amiga 500; the manual's remark that some sound effects may be left out on machines with 512 KB (page 3), which no note confirms in the code; the copper's third kind of instruction is named only here (claim 43), not in the prose.
