Chapter 2
{ .chapter-kicker }

# The Amiga in twenty minutes

Wings of Fury was written for one machine: its manual asks for an Amiga 500, 1000 or 2000 with at least 512 KB of memory and a joystick (page 2). This chapter is a short tour of that machine for a reader who has never programmed it. By its end you will know what the 68000 processor does and how its machine code looks on the page; what chip memory, bitplanes, the copper, the blitter and Paula are, and what this game does with each; why the VBlank is the beat the game counts in; and which few services of the operating system it asks for. Every topic goes only as far as the port needed it. The deep dives come in Part II.

## The machine in one picture

An Amiga is a processor surrounded by chips of its own. The processor is the **68000**: Motorola's processor, the chip that runs the program, one instruction after another. Around it sit the **custom chips**: the Amiga's own chips for the picture, the drawing and the sound, which do their work beside the processor and, once told what to do, without it. There are three. Agnus holds the copper and the blitter, Denise turns the picture's data into the signal for the screen, and Paula plays the sound and also serves the disk drive, the serial port and the **interrupts**: the signals with which the hardware makes the processor put aside what it is doing, run a short routine, and carry on where it was.

A program tells a custom chip what to do through its **registers**: small named stores inside a processor or a chip. A custom chip's registers sit at fixed addresses, from `0xDFF000` on, and a value written to one of them sets the chip to work. The game keeps the address `0xDFF000` in a variable of its own and writes the registers directly: those of the copper, the blitter, the sound and the interrupts. It reads few of them: the sound's interrupt bits, the blitter's busy flag while it waits for the blitter, and the two that matter, the joystick's directions and the position of the beam that draws the picture.

![The 68000 and the custom chips Agnus, Denise and Paula, all reaching chip memory, where the game keeps its screens, copper lists, shapes, sounds and songs; below, reached by the processor alone, the CIAs, the Kickstart ROM and any other memory.](../figures/amiga-chips.svg)

/// caption
The chips around chip memory, and what the game keeps where.
///

The **CIAs** are the Amiga's two interface chips, which serve its ports and carry timers of their own; the game reads the fire button from one of them, and its music player takes one of their timers. The core of the operating system, AmigaOS, lives in the machine's ROM, the memory that cannot be changed: **Kickstart**, the ROM and its contents. Among much else it holds the fast floating point of chapter 1, the table that turns keys into characters, and the system's font.

## The 68000

The 68000 runs at about seven million cycles a second on a PAL Amiga. It has sixteen registers of its own, each 32 bits wide: eight data registers, D0 to D7, for the values it computes with, and eight address registers, A0 to A7, which point into memory; A7 is the stack pointer, which marks the stack, where routines keep their arguments and return addresses. The program counter holds the address of the next instruction.

Memory is a long row of bytes, each with its address. An instruction moves a value between memory and a register, or computes with registers: it adds, multiplies, compares or jumps. It works on a byte of 8 bits, a word of 16 or a long of 32, and says which with a letter after its name: `.b`, `.w` or `.l`.

The instructions are themselves numbers in memory. That is **machine code**: the program as the processor reads it, bytes that encode one instruction after another. Written out for people, each instruction becomes a line of **assembly language**: a short name for the operation followed by its operands, such as `move.w` or `rts`.

The listing, the original's instructions written out by the disassembler (chapter 4 tells how it was made), shows the two side by side. Here is a whole routine of the game, `rand_beam`, the only source of chance chapter 1 told of:

```wingslst
--8<-- "generated/listings/asm/rand_beam.lst"
```

Each line gives the instruction's address, its bytes of machine code, the instruction in assembly language, and after a semicolon the name of a variable it touches. Numbers are hexadecimal, marked with a `$` as Motorola's assemblers mark them; this book writes them as `0x0203BE`. Read from the top, the routine loads the word `rand_seed_const` into D0; multiplies it by `0x1AFB`, which gives a 32-bit product; adds `0x1FCCD`; reads the word at address `0xDFF006` into D1; combines the two with an exclusive or; stores the result in `rand_state`; and returns. The result stays in D0, where the caller finds it; the game calls the routine from 43 places.

The fourth line is the one the port cares about. Address `0xDFF006` is not memory but a register of the custom chips, `VHPOSR`, which holds the position of the beam: the line it is drawing and its place on that line. So the number the routine returns is a constant combined with where the beam happens to be at that instant, and that is why chance in this game is a matter of timing. The port answers that one read from its reproducible stream.

The operand `-$46ec(a4)` is how the program finds a variable: at an offset from the address in A4. Chapter 3 explains that; the listing prints the variable's name beside it, so that nobody has to work the address out. `rand_beam` was written by hand in assembly language. The game's 223 routines written in C were translated by a compiler, and they look different in the listing, as chapter 4 shows.

## Chip memory

**Chip memory** is the memory the custom chips can reach: they read and write it by themselves, without the processor. Memory a machine has beyond it, if any, only the processor reaches. Whatever a custom chip has to see must therefore be in chip memory: the picture the display shows, the shapes the blitter copies, the sound samples Paula plays, the lists the copper follows.

A program asks the operating system for chip memory by a flag, as the game's `load_file_chip` at `0x01FECA` does. What the game keeps there: the bitplanes of its two play screens, 44,240 bytes each; three buffers of 1,000 bytes for copper lists; a scratch buffer of 1,040 bytes for the blitter's masks; every shape container, loaded whole; the eight sound effects; and the music's songs, voices and sound samples. What only the processor reads, such as the table that finds a shape by its name, goes into ordinary memory.

In the port all of it lives in one block of memory, an arena from which the core hands out what the original asked the operating system for. A browser has no chip memory and needs none: the port draws and mixes the sound in its own code.

## Bitplanes

The Amiga does not store a picture as one number per pixel. It stores it as **bitplanes**: one bit of every pixel's colour number, kept as a picture of its own. A picture of 32 colours has five planes. Plane 1 holds the lowest bit of every pixel's colour number, worth 1; plane 2 the next, worth 2; and so on to plane 5, worth 16. To show a pixel, the display takes its bit from each plane and puts the five together into a number from 0 to 31, and that number goes through the [palette](../glossary.md#palette), 32 colour registers each set to one of 4,096 colours.

One of the game's own shapes shows how it works. The Hellcat, the player's aircraft, in level flight is 48 by 13 pixels, stored in five planes. The marked pixel has its bit set in planes 1, 3 and 5, so its colour number is 1 + 4 + 16, which is 21, a mid blue in the palette of the day. Every pixel of the aircraft uses one of the colours 19 to 31, so plane 5 is set wherever the aircraft is.

![The Hellcat seven times, one under the other: its five planes as light bits, the colour numbers they make as greys, and its colours. A framed pixel on the fuselage has the bits 1, 0, 1, 0, 1 and the colour number 21.](../generated/figures/planes-hellcat.png)

/// caption
One shape of the game taken apart into its five bitplanes and put together again: each plane's bits, the colour numbers they make, and the colours.
///

The play screen stacks three areas. The playfield, where the game is played, has 162 lines in low resolution, 320 pixels wide, with five planes and 32 colours. The dashboard, 37 lines, is in high resolution, 640 pixels wide, a pixel there being half as wide, with four planes and 16 colours. The message ticker, 13 lines, has one plane. With a blank line between each, that makes 214 lines.

The port keeps no planes. Its picture holds one byte per pixel, the colour number itself, and the palette is applied only when the picture is shown. The shapes are turned from planes into such numbers once, when they are loaded, and the drawing works on the numbers. The picture holds the same numbers as the original's, which is the second part of chapter 1's definition.

## The beam and the copper

The picture on a screen of the time is drawn by a **beam**: the point where the display is drawing, which sweeps each line from left to right and the lines from top to bottom. A PAL frame has 313 lines. The game's picture begins at beam line 44, and on the play screen it ends at beam line 257; above and below it lie the border and the lines of the vertical blank.

The **copper** is a small processor inside Agnus that does nothing but follow the beam. It follows a list of simple instructions, of which the game uses two kinds: wait until the beam reaches a given position, and write a value into one of the chips' registers. With it a program can change a colour, or the whole screen mode, at a chosen line of every frame, without the 68000 doing anything.

![The play screen as the beam draws it, line by line, from the sky down to the ticker, and the beam's way back to the top; beside it the copper's list at the lines where it acts.](../figures/beam-copper.svg)

/// caption
The beam draws the picture line by line; the copper's list waits for chosen lines and changes the colours and the screen mode there.
///

The game writes its copper lists itself and points the copper at one by writing a single register, `COP1LC`. The list of the play screen follows the picture down. Before line 0 it sets the playfield's colours and planes. At the split line it sets the sea's colours where they differ from the sky's, fifteen of them by day. At lines 162 and 200 it switches the planes off for a blank line and then sets up the next area. On the ticker's first ten lines it sets the single colour anew on each: a ramp of greys from dim to bright and back, brightest on the middle line.

The split line is computed again in every pass and written into the list, so that it moves; to all appearances it follows the horizon. When the sky flashes, the game pokes one colour into the built list. A fade, in which a picture comes up from black, rebuilds the list sixteen times with colours ever closer to the picture's own; how long that takes is processor time, which chapter 7 takes up.

The game keeps two complete screens, each with its own planes and its own copper list. While one is shown, the next pass draws into the other; then one write to `COP1LC` hands the copper the new list, which it takes up at the next vertical blank. That is double buffering, and it is why the player never sees a half-drawn picture.

The port has no copper. It keeps what the copper achieves: a palette for every row of its picture. The split, the ramp, the flash and the fades become further palettes for further rows.

![The first mission's palettes, one band of colour swatches for each run of rows: the sky's, the sea's, black for the blank rows, the dashboard's, and the ticker's single grey rising and falling.](../generated/figures/mission-palettes.png)

/// caption
What the copper does on the play screen, as the port keeps it: the palette of every run of rows of the first mission's picture.
///

## The blitter

The **blitter** is the chip for copying and combining rectangles of memory, one bitplane at a time. It reads up to three sources, called A, B and C, combines them bit by bit with a logic function that the program chooses by a number, and writes the result to a destination, D. Once started it works by itself, and the processor is free meanwhile.

Every shape, rectangle and line of the game is drawn by one small library of hand-written assembly, at `0x0209BC` to `0x0215D8`, which programs the blitter. To draw a shape, the processor first combines the shape's planes into a mask, a one-bit picture of where the shape has any colour at all. Then the blitter runs once for each plane. With the mask as source A, the shape's plane as B and the screen's plane as C, its logic function writes the shape's bit wherever the mask is set and keeps the screen's bit everywhere else. That is how colour 0 in a shape becomes see-through: no plane has a bit there, so the mask is clear and the background stays.

There is a limit. The mask's buffer holds 1,040 bytes, and a shape whose plane is larger gets no mask and is drawn whole, its colour-0 pixels included. Eleven shapes are that large. Ten of them are the pieces of the carrier and the ships, and those contain no colour 0 at all: they carry the sky's colour around the hull, so the artwork was made for this behaviour.

Nothing in the game's logic ever reads back what was drawn: no pixel, no mask, no flag of the blitter. That fact makes the [headless original](../glossary.md#headless-original) possible, which runs without drawing anything.

/// know
The port draws each shape pixel by pixel on its picture of colour numbers, with the original's clipping and in its order. To compare, the original's own drawing routine runs under emulation; whenever it starts a blit, all the blitter's registers are captured, and a model of the blitter replays them. The result is compared pixel by pixel with the port's, for every shape of every container, at six positions, against two clipping rectangles and over two backgrounds. What this cannot check is the model itself, built from the chip's documentation; one test independent of it checks that a blit changes nothing outside the shape's box.
///

## Paula

**Paula** is the sound chip: four channels, and each is given the address of a sound sample in chip memory, its length, a volume from 0 to 64, and a **period**: the number of ticks of the machine's colour clock that each byte is held, so that a smaller period plays higher. The colour clock ticks 3,546,895 times a second on a PAL Amiga. Then the channel plays the bytes by itself. At their end it starts again from the address in its register, and each time it starts it raises an interrupt, so that a program can hand it the next sound or stop it. Channels 0 and 3 go to the left, 1 and 2 to the right.

A sound sample is nothing but a row of numbers. The game's eight sound effects are files of signed bytes, from −128 to 127, with no header. The burst of a bomb or a rocket, `sounds/boom`, is 5,466 bytes, played once at period 500: each byte is held for 500 ticks of the colour clock, about 0.14 milliseconds, and the whole burst lasts 0.77 seconds.

![The burst's sound sample in gold: a loud start that thins out over 0.77 seconds; below, a hundred of its bytes enlarged into a staircase of flat steps.](../generated/figures/sample-boom.png)

/// caption
The sound sample of a burst, `sounds/boom`, as Paula plays it: the whole, and a hundred bytes enlarged, each held for one period.
///

The game drives Paula with two engines. The sound effects engine has eight slots, two for each channel; the logic tick switches them on and off and moves their volume and period, and the first slot of a pair that is on gets the channel, so that the player's guns drown the engine's hum.

The music is a separate small program, `songplay`, with its songs in a file of their own, `wofsongs`; the game loads both from the disk when a song is to play. The music takes its beat from a timer of one of the CIAs, which counts 709,379 ticks a second on PAL. Four of the five songs set it so that the player's routine runs every 14,592 ticks: every 20.57 milliseconds, a little slower than the VBlanks. One byte of the timer is never written and is taken to keep the value it has when the machine is switched on; that is the one assumption the music's tempo rests on, which chapter 1 mentioned and chapter 18 explains.

The port's Paula is a model of the four channels, the same one the headless original runs: every sound sample started, with its channel, period and volume, is logged on both sides, and the logs must agree. The core mixes the channels into the sound your browser plays.

## The VBlank

After the last line of a frame the beam goes back to the top, and a new frame begins. That moment is the **VBlank**, the vertical blank: 50 times a second on a PAL Amiga, 60 on an NTSC one, and the beat the whole game counts in.

The VBlank reaches the program as an interrupt. The game asks the operating system to call two routines of its own at every VBlank. The first belongs to the sound effects engine and starts the sounds the tick has asked for. The second counts the VBlanks; on every fourth it takes an [input byte](../glossary.md#input-byte) from the stick into a queue of up to six, which is where the 12.5 logic ticks a second of chapter 1 come from; and it scrolls the ticker by one pixel.

The main program keeps the same beat. Each pass of the inner loop begins by waiting for a VBlank, draws its picture into the hidden screen and hands its copper list over, and the picture appears at the next VBlank. On a real PAL Amiga a pass takes two VBlanks in a quiet scene. The program never asks whether the machine gives 50 VBlanks a second or 60; on PAL everything simply runs slower.

In the port the VBlank comes from the shell's clock, which calls the core 50 or 60 times for every second of emulated time, each call followed by a pass.

## The little of AmigaOS the game uses

AmigaOS offers its services in **libraries**: collections of routines that a program opens by name and calls through a table of jumps at fixed offsets from the library's address. The game asks little of them. It closes the Workbench, the Amiga's desktop, when it starts, and builds its own display. This is what it does ask for, and what the port does instead:

| What | The original | The port |
|---|---|---|
| Files | dos.library | a file system over the disk's files; saved games in the browser's storage |
| Memory | exec.library, chip memory where a chip must see it | one arena |
| The VBlank | exec.library: two routines on the VBlank interrupt | the shell's clock |
| The system font | graphics.library: the dialogs never choose a font, so they get topaz 8 from the ROM | topaz 8, read from the ROM when the port is built |
| Keys to characters | console.device, with the system's keymap | a table made when the port is built, by the ROM's own routine |
| Floating point | mathffp.library in the ROM, nine operations | the same arithmetic in integer code, bit for bit |

The game's own font, in which the story and the briefing are told, comes from the disk; only the dialogs for names and files use the system's. A key reaches the game as a raw code that names the key's position, not its letter, and the keymap turns it into a character; chapter 19 has the detail.

Three of the rows lead into the ROM, Kickstart 1.3, 262,144 bytes. It is not in the repository: whoever builds the port places their own copy, which the build checks. The headless original runs the ROM's own floating point and key conversion; the port takes the font and the key table from it when it is built.

/// know
The headless original runs the game's own code with the custom chips taken out. Their addresses are plain memory: writes to the copper and the blitter land there and change nothing, and every wait for the blitter ends at once, because its busy bit reads as zero. A read of the beam's position takes the next value of the port's stream; the joystick and the fire button are set from the run's script; Paula and the CIA's timer are the port's model. Because no logic reads back the picture, nothing more is needed. Chapter 6 tells the rest.
///

/// dev
The registers: `VHPOSR`, the beam, `0xDFF006`; `JOY1DAT`, the stick in port 2, `0xDFF00C`; `BLTSIZE`, whose write starts a blit, `0xDFF058`; `COP1LC`, the copper's list, `0xDFF080`; the fire buttons, bits 6 and 7 of CIA-A's port at `0xBFE001`, read for port 1 at `0xBFE0FF`; the audio interrupt's vector, `0x70`. In the port: `src/draw.c`, `src/audio.c` (Paula), `src/sound.c` and `src/music.c` (the two engines), `src/ffp.c`, `src/rand.c` (the stream for the beam), `src/fs.c`.
///

## What comes next

This chapter has looked at the machine. Chapter 3 looks at what the game brought to it: the disk and its files; the executable and its hunks, the parts the operating system loads into memory; the compiler the game was built with, Manx Aztec C, whose integers are 16 bits wide; and the register A4, through which the program reaches its variables.

## Further reading

The files named here are in the repository, `github.com/sy2002/wof-wasm`.

- `SPEC.md`, section 3.4, "Operating system and hardware use"; 6.4, "Video model"; 6.5, "Audio model".
- `re/notes/display.md`, "Summary", "Memory", "The copper builder" and "Double buffering and the swap".
- `re/notes/drawing.md`, "Summary", "What `shape_draw` does, exactly" and "Read-back".
- `re/notes/shapes.md`, "Record header, complete"; `re/notes/random.md`, "The generator".
- `re/notes/sound.md`, "Two layers" and "The samples"; `re/notes/music.md`, "The timer".
- `re/notes/headless.md`, "What runs and what does not"; `re/notes/porting-m1.md`, "How the tests establish it".
- `re/notes/keys.md`, "Raw code to character: console.device"; `re/notes/system-font.md`.

Outside the repository: the *Amiga Hardware Reference Manual*, for the custom chips, and Motorola's *M68000 Family Programmer's Reference Manual*, for the processor.
