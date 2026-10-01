# The glossary

Every term the book introduces, in alphabetical order. An entry gives the term, its definition in one line, the chapter that introduces it, and the note of the repository that holds the detail.

### 68000

Motorola's processor, the chip in the Amiga that runs the program: sixteen registers of 32 bits, eight for data and eight for addresses, and instructions that work on bytes, words of 16 bits and longs of 32.

Introduced in [chapter 2](part-1/amiga.md). The detail: `SPEC.md`, sections 3.2 and 7.1.

### A4

The 68000's address register 4, which the game's code keeps as its small-data base, `0x02AFFE` in the fixed load layout: see [Small-data base](#small-data-base).

Introduced in [chapter 3](part-1/disk.md). The detail: `SPEC.md`, section 3.2.

### A5

The 68000's address register 5, which every compiled C routine of the game uses as the pointer to its stack frame: see [Stack frame](#stack-frame).

Introduced in [chapter 3](part-1/disk.md). The detail: `SPEC.md`, section 3.2.

### ADF

An Amiga Disk File: a copy of an Amiga floppy, block by block, in one file, a double-density disk's 1,760 blocks of 512 bytes; the game's disk is `original/wof.adf`.

Introduced in [chapter 3](part-1/disk.md). The detail: `SPEC.md`, sections 2 and 3.1.

### Assembly language

The written form of machine code, one instruction a line, a short name for the operation followed by its operands: the form in which the listing shows the whole program, and in which much of the game was written by hand.

Introduced in [chapter 2](part-1/amiga.md). The detail: `SPEC.md`, section 3.2.

### Attract demo

A recorded game that the program plays by itself when left alone at the rank selection, and which it can record from a game played; not a demoscene production.

Introduced in [chapter 1](part-1/faithful.md). The detail: `re/notes/demo.md`.

### Beam

The point where the display is drawing the picture, sweeping each line from left to right and the lines from top to bottom; its position, which a register of the custom chips reports, is the game's only source of chance.

Introduced in [chapter 2](part-1/amiga.md). The detail: `re/notes/random.md`.

### Big-endian

The byte order that stores the most significant byte of a number first: the 68000's, and that of every file the project reads; the opposite of little-endian.

Introduced in [chapter 3](part-1/disk.md). The detail: `SPEC.md`, sections 3.5 and 5.

### Bitplane

One bit of every pixel's colour number, kept as a picture of its own; five bitplanes together give each pixel one of 32 colours.

Introduced in [chapter 2](part-1/amiga.md). The detail: `re/notes/display.md`.

### Blitter

The Amiga's unit, inside the custom chip Agnus, for copying and combining rectangles of memory one bitplane at a time; it draws the game's shapes into the bitplanes while the processor goes on with other work.

Introduced in [chapter 2](part-1/amiga.md). The detail: `re/notes/drawing.md`.

### BSS

A hunk of memory that starts at zero and is given in the program's file by its size alone; the game's is 4 bytes at `0x028000`.

Introduced in [chapter 3](part-1/disk.md). The detail: `SPEC.md`, section 3.2.

### Calling convention

The rules by which a caller hands a routine its arguments and gets the result back: in the game's compiled C the arguments go onto the stack, 2 bytes for an int and 4 for a long or a pointer, and the result comes back in D0.

Introduced in [chapter 3](part-1/disk.md). The detail: `SPEC.md`, section 3.2.

### Chip memory

The memory the Amiga's custom chips can read and write by themselves, without the processor; the game keeps its screens, copper lists, shapes, sound effects and songs there.

Introduced in [chapter 2](part-1/amiga.md). The detail: `re/notes/display.md`, "Memory".

### CIA

One of the Amiga's two interface chips, which serve its ports and carry timers of their own; the game reads the fire button from one, and its music player takes one of their timers for its beat.

Introduced in [chapter 2](part-1/amiga.md). The detail: `re/notes/music.md`, "The timer".

### Colour clock

The clock the Amiga's custom chips run on, 3,546,895 cycles a second on a PAL machine: half the processor's clock, and the unit of Paula's period.

Introduced in [chapter 2](part-1/amiga.md). The detail: `re/notes/sound.md`, "The slots and what they play".

### Copper

The Amiga's display coprocessor: it follows a list of waits and register writes in step with the beam, and so changes colours and screen modes part of the way down the picture.

Introduced in [chapter 2](part-1/amiga.md). The detail: `re/notes/display.md`.

### Core

The port's game: the ported logic, written in C and compiled to WebAssembly, which knows nothing of the browser around it.

Introduced in [chapter 1](part-1/faithful.md). The detail: `SPEC.md`, section 6.1.

### Crack

A change made to a program to remove its copy protection; the disk this port was made from carries one.

Introduced in [chapter 1](part-1/faithful.md). The detail: `SPEC.md`, section 3.1.

### Custom chips

The Amiga's own chips beside the processor: Agnus with the copper and the blitter, Denise for the display, Paula for the sound. A program sets them to work through their registers, and they then work from chip memory by themselves.

Introduced in [chapter 2](part-1/amiga.md). The detail: `SPEC.md`, section 3.4.

### Double buffering

Drawing into a hidden picture and showing it only when it is whole; the game keeps two screens, each with its own copper list, and swaps them with one register write.

Introduced in [chapter 2](part-1/amiga.md). The detail: `re/notes/display.md`, "Double buffering and the swap".

### Emulator

A program that imitates a computer's processor and chips closely enough that the computer's own programs run on it unchanged.

Introduced in [chapter 1](part-1/faithful.md). The detail: `README.md`, "Amiga to Web".

### Faithful port

One game carried to another machine by rewriting its own logic, routine by routine, from its machine code, and held to the original by comparison.

Introduced in [chapter 1](part-1/faithful.md). The detail: `SPEC.md`, section 1.

### Far-call table

185 jump instructions at the start of the game's data hunk, `0x023000` to `0x023456`, each holding the full address of a routine; a call such as `jsr -$7e1e(a4)` goes through one of them and needs no relocation of its own.

Introduced in [chapter 3](part-1/disk.md). The detail: `SPEC.md`, section 3.2.

### Fast floating point

Motorola's floating-point format of 32 bits, whose routines live in the Amiga's ROM; the game's flight model computes in it, and the port reproduces it bit for bit in integer code.

Introduced in [chapter 1](part-1/faithful.md). The detail: `re/notes/ffp.md`.

### Fixed load layout

The one set of addresses at which all the project's tools load the game's program: the code at `0x010000`, the data at `0x023000`, the BSS at `0x028000`, A4 holding `0x02AFFE`. Every address of the program in this book is one of it; the running port holds offsets instead.

Introduced in [chapter 3](part-1/disk.md). The detail: `SPEC.md`, section 3.2; `tools/hunk.py`.

### FPGA recreation

A computer rebuilt in programmable hardware, a chip whose circuits are configured to behave like the original machine's.

Introduced in [chapter 1](part-1/faithful.md). The detail: `README.md`, "Amiga to Web".

### Front end

The game's screens before and between missions: the story, the title, the rank selection, the briefing, the high scores and the dialogs.

Introduced in [chapter 19](part-2/front-end.md). The detail: `re/notes/frontend.md`.

### Headless original

The original program run from its `main` routine on under emulation without a screen, the operating system's calls answered by stubs, the ROM's floating point, its key conversion and the game's music player run for real: the reference the port is compared with.

Introduced in [chapter 1](part-1/faithful.md). The detail: `re/notes/headless.md`.

### Hexadecimal

Numbers in base 16, the digits 0 to 9 and A to F; this book marks them with `0x`, as in `0xDFF000`, and the listing with a `$`, as Motorola's assemblers do.

Introduced in [chapter 2](part-1/amiga.md). The detail: `book/BOOK.md`, section 4, point 3.

### Hunk

A part of an Amiga program that is loaded into memory as a whole: code, data with its starting values, or BSS.

Introduced in [chapter 3](part-1/disk.md). The detail: `SPEC.md`, section 3.2.

### Hunk file

The AmigaDOS format for programs: a header giving the number of hunks and their sizes, then each hunk's contents, its relocations and an end mark; the game, its music player and its songs are hunk files.

Introduced in [chapter 3](part-1/disk.md). The detail: `tools/hunk.py`; `SPEC.md`, section 3.2.

### IFF ILBM

The Amiga's standard format for pictures: a file of chunks, each a name of four letters, its length and its contents, giving a picture's size, colours and bitplanes; the game's pictures and three of its palettes use it.

Introduced in [chapter 3](part-1/disk.md). The detail: `SPEC.md`, section 3.5, "Pictures".

### Input byte

The byte that carries the stick's four directions and the button into one logic tick, the only way the stick and the button reach the game's logic; the key commands come in through the game's own key handler.

Introduced in [chapter 1](part-1/faithful.md). The detail: `re/notes/input.md`.

### Input sample

The taking of one input byte, which the game does every fourth VBlank, and the byte so taken; never a sound.

Introduced in [chapter 1](part-1/faithful.md). The detail: `re/notes/input.md`.

### int (the C type)

C's ordinary type for whole numbers: 16 bits wide in Manx Aztec C as the game was built, 32 in the compilers that build the port, which therefore names the width of every value of the game.

Introduced in [chapter 3](part-1/disk.md). The detail: `SPEC.md`, section 7.1.

### Interrupt

A signal from the hardware that makes the processor put aside what it is doing, run a short routine and carry on where it was; the VBlank and Paula's channels raise them.

Introduced in [chapter 2](part-1/amiga.md). The detail: `re/notes/headless.md`, "Scheduling".

### Keyboard assist

The port's switch that makes one key press one step in the weapon menu and lets a short tap reach the game exactly once everywhere else; off in every comparison with the original.

Introduced in [chapter 1](part-1/faithful.md). The detail: `re/notes/porting-m4.md`, "The keyboard assist".

### Kickstart

The heart of AmigaOS, in the ROM of the Amiga 500 and 2000 and loaded from a disk by the 1000; the port takes the font and the key table from Kickstart 1.3 when it is built and is held to its floating point, and the ROM is not part of the repository.

Introduced in [chapter 2](part-1/amiga.md). The detail: `re/notes/system-font.md`, "The ROM".

### Library

A collection of the operating system's routines that a program calls through a table of jumps at fixed offsets from the library's address; the game uses dos, exec, graphics and mathffp among others.

Introduced in [chapter 2](part-1/amiga.md). The detail: `SPEC.md`, section 3.4.

### Listing

The game's program written out as assembly language by the disassembler, each instruction with its address, its bytes and the names of what it touches: `re/Wings.lst`.

Introduced in [chapter 4](part-1/reading.md). The detail: `SPEC.md`, sections 2 and 4.

### Little-endian

The byte order that stores the least significant byte of a number first: that of the machines the port runs on, WebAssembly's among them; the opposite of big-endian.

Introduced in [chapter 3](part-1/disk.md). The detail: `tools/extract_tables.py`.

### LoadSeg

The routine of AmigaDOS that loads a hunk file: it puts each hunk wherever it finds free memory of the kind asked for and corrects the relocations; the game loads its music with it.

Introduced in [chapter 3](part-1/disk.md). The detail: `re/notes/music.md`, "The two files".

### Logic tick

One step of the game's simulation, one for every input byte, taken every fourth VBlank: 12.5 a second on a PAL Amiga, so that in a quiet scene two passes go to a tick.

Introduced in [chapter 1](part-1/faithful.md). The detail: `SPEC.md`, section 3.3.

### Machine code

A program as the processor reads it: its instructions as numbers in memory.

Introduced in [chapter 2](part-1/amiga.md). The detail: `SPEC.md`, section 3.2.

### Manx Aztec C

The C compiler the game's C was built with: its int, as the game was built, is 16 bits, its code reaches the variables through A4, and each of its routines keeps a stack frame on A5.

Introduced in [chapter 3](part-1/disk.md). The detail: `SPEC.md`, section 3.2.

### Mask

A one-bit picture of where a shape has any colour at all: the OR of its planes, or, for a shape of one plane, that plane; the blitter draws the shape's bits where the mask is set and keeps the background elsewhere.

Introduced in [chapter 2](part-1/amiga.md). The detail: `re/notes/drawing.md`, "What `shape_draw` does, exactly".

### Mission script

A recorded sequence of stick and key inputs that flies a mission the same way every time, for the original and the port alike.

Introduced in [chapter 1](part-1/faithful.md). The detail: `re/notes/porting-m4.md`, "How the port is held to the original".

### Oracle

The instrument that runs one original routine on an emulated 68000 beside its port, on the same inputs, and compares the results.

Introduced in [chapter 1](part-1/faithful.md). The detail: `SPEC.md`, sections 7.4 and 8.

### PAL

The European television standard, 50 pictures a second, which the Amiga's display follows in Europe; the port's default.

Introduced in [chapter 1](part-1/faithful.md). The detail: `SPEC.md`, section 6.2, "Video".

### Palette

The table that turns a pixel's colour number into a colour: on the Amiga up to 32 entries of 4,096 possible colours, changed part of the way down the screen.

Introduced in [chapter 1](part-1/faithful.md). The detail: `re/notes/display.md`.

### Pass

One round of the inner loop, the loop that plays a mission: it draws one picture and runs the part of the logic that goes by pictures. Two VBlanks long on a real PAL Amiga in a quiet scene, so two passes go to a tick.

Introduced in [chapter 1](part-1/faithful.md). The detail: `re/notes/passes.md`.

### Paula

The Amiga's chip for sound, four channels that each play 8-bit sound samples at their own rate and volume; it also handles the interrupts, the disk and the serial port.

Introduced in [chapter 2](part-1/amiga.md). The detail: `re/notes/sound.md`.

### Period

Paula's measure of pitch: how many ticks of the colour clock, 3,546,895 a second on a PAL Amiga, each byte of a sound sample is held; a smaller period plays higher.

Introduced in [chapter 2](part-1/amiga.md). The detail: `re/notes/sound.md`.

### Pure routine

A routine that computes from its inputs alone, without touching anything else; every pure routine is held to the original under the oracle.

Introduced in [chapter 1](part-1/faithful.md). The detail: `SPEC.md`, section 7.4.

### Register

A small named store inside a processor or a chip: the 68000's sixteen hold the values it computes with, and a custom chip's, at fixed addresses from `0xDFF000`, tell the chip what to do.

Introduced in [chapter 2](part-1/amiga.md). The detail: `re/notes/drawing.md`, "The blitter library".

### Relocation

An entry in a hunk file that names a place in a hunk holding an address, which the loader corrects by where its target hunk landed.

Introduced in [chapter 3](part-1/disk.md). The detail: `tools/hunk.py`; `SPEC.md`, section 3.2.

### Remake

A new program made to look and play like an old one, written from watching the old one.

Introduced in [chapter 1](part-1/faithful.md). The detail: `SPEC.md`, section 1.

### Rpck

The game's own packed format, named after the four letters a packed file begins with: the unpacked size, then control bytes that copy bytes or repeat one; ten files of the disk use it.

Introduced in [chapter 3](part-1/disk.md). The detail: `SPEC.md`, section 3.5; `tools/rpck.py`.

### Shape container

A file of many shapes, the format that begins with `PPkc`: the number of shapes, a name of four characters for each, where each shape's entry begins, and the entries, each a header and the planes; the disk has twelve.

Introduced in [chapter 3](part-1/disk.md). The detail: `re/notes/shapes.md`.

### Shell

The thin layer of JavaScript around the core: the clock that paces it, the screen, a loudspeaker for the sound the core mixes, the keys, a place for saved games, and the help screen, the pause sign and fullscreen.

Introduced in [chapter 1](part-1/faithful.md). The detail: `SPEC.md`, section 6.2.

### Sign extension

Widening a number to more bits by copying its sign bit into the new ones, so that it keeps its value: the 68000's `ext.l` widens a word to a long.

Introduced in [chapter 3](part-1/disk.md). The detail: `SPEC.md`, section 7.1.

### Signed byte

A byte read as a number from −128 to 127 in two's complement, in which the top bit counts as −128: a byte above `0x7F` is itself less 256.

Introduced in [chapter 3](part-1/disk.md). The detail: `SPEC.md`, section 3.5.

### Small-data base

The register A4 in the game's code, holding `0x02AFFE`, 32,766 bytes into the data, from which every variable is reached by an offset of 16 bits.

Introduced in [chapter 3](part-1/disk.md). The detail: `SPEC.md`, section 3.2.

### Sound sample

A recorded waveform that Paula plays back on one of its four channels, at its own pitch and volume.

Introduced in [chapter 1](part-1/faithful.md). The detail: `re/notes/sound.md`.

### Split line

The line of the playfield where the sky's palette gives way to the sea's, computed again in every pass; the copper changes the colours there.

Introduced in [chapter 2](part-1/amiga.md). The detail: `re/notes/display.md`, "The split line".

### Stack frame

A routine's own stretch of the stack, from its arguments down to its own variables, which `link a5` builds at the start of each compiled C routine of the game; A5 points into it, the first argument at `8(a5)`.

Introduced in [chapter 3](part-1/disk.md). The detail: `SPEC.md`, section 3.2.

### Symbol

A name a program file keeps for a routine or a variable, with its address; the game's program keeps none, its music player twenty.

Introduced in [chapter 3](part-1/disk.md). The detail: `tools/hunk.py`; `re/notes/music.md`, "The two files".

### Topaz 8

The Amiga's standard font, eight pixels high, in the Kickstart ROM; the game's dialogs for names and files show it, and the port reads it from the ROM when it is built.

Introduced in [chapter 2](part-1/amiga.md). The detail: `re/notes/system-font.md`.

### VBlank

The vertical blank, the moment the beam has finished a picture and returns to the top: 50 times a second on a PAL Amiga, and the clock the game counts its time in.

Introduced in [chapter 2](part-1/amiga.md). The detail: `re/notes/passes.md`.

### Vertical flip

The game's command that swaps the stick's forward and back, for players who want a pilot's stick; in the port a remembered preference.

Introduced in [chapter 1](part-1/faithful.md). The detail: `re/notes/keys.md`, "The vertical flip, and how long it lasts".

### WebAssembly

A compact binary form of program that every current browser runs: the form the port's core is compiled to.

Introduced in [chapter 1](part-1/faithful.md). The detail: `SPEC.md`, section 5.

### Workbench

The Amiga's desktop, which the game closes when it starts.

Introduced in [chapter 2](part-1/amiga.md). The detail: `SPEC.md`, section 3.4.
