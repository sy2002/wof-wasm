# The glossary

Every term the book introduces, in alphabetical order. An entry gives the term, its definition in one line, the chapter where it first appears, and the note of the repository that holds the detail.

### Bitplane

One bit of every pixel's colour number, kept as a picture of its own; five bitplanes together give each pixel one of 32 colours.

First in [chapter 2](part-1/amiga.md). The detail: `re/notes/display.md`.

### Blitter

The Amiga's chip for copying and combining rectangles of memory, which draws the game's shapes into the bitplanes while the processor goes on with other work.

First in [chapter 2](part-1/amiga.md). The detail: `re/notes/drawing.md`.

### Copper

The Amiga's display coprocessor: it follows a list of waits and register writes in step with the beam, and so changes colours and screen modes part of the way down the picture.

First in [chapter 2](part-1/amiga.md). The detail: `re/notes/display.md`.

### Core

The port's game: the ported logic, written in C and compiled to WebAssembly, which knows nothing of the browser around it.

First in [chapter 1](part-1/faithful.md). The detail: `SPEC.md`, section 6.1.

### Crack

A change made to a program to remove its copy protection; the disk this port was made from carries one.

First in [chapter 1](part-1/faithful.md). The detail: `SPEC.md`, section 3.1.

### Emulator

A program that imitates a computer's processor and chips closely enough that the computer's own programs run on it unchanged.

First in [chapter 1](part-1/faithful.md). The detail: `README.md`, "Amiga to Web".

### Faithful port

One game carried to another machine by rewriting its own logic, routine by routine, from its machine code, and held to the original by comparison.

First in [chapter 1](part-1/faithful.md). The detail: `SPEC.md`, section 1.

### FPGA recreation

A computer rebuilt in programmable hardware, a chip whose circuits are configured to behave like the original machine's.

First in [chapter 1](part-1/faithful.md). The detail: `README.md`, "Amiga to Web".

### Headless original

The original program run whole under emulation without a screen, its operating system replaced by stand-ins: the reference the port is compared with.

First in [chapter 1](part-1/faithful.md). The detail: `re/notes/headless.md`.

### Input byte

The byte that carries the stick's four directions and the button into one logic tick, the only way the controls reach the game's logic.

First in [chapter 1](part-1/faithful.md). The detail: `re/notes/input.md`.

### Input sample

The taking of one input byte, which the game does every fourth VBlank, and the byte so taken; never a sound.

First in [chapter 1](part-1/faithful.md). The detail: `re/notes/input.md`.

### Keyboard assist

The port's switch that lets a tapped key do what a held joystick does, in the weapon menu and in flight; off in every comparison with the original.

First in [chapter 1](part-1/faithful.md). The detail: `re/notes/porting-m4.md`, "The keyboard assist".

### Logic tick

One step of the game's simulation, one for every input byte: 12.5 a second on a PAL Amiga.

First in [chapter 1](part-1/faithful.md). The detail: `SPEC.md`, section 3.3.

### Oracle

The instrument that runs one original routine on an emulated 68000 beside its port, on the same inputs, and compares the results.

First in [chapter 1](part-1/faithful.md). The detail: `SPEC.md`, sections 7.4 and 8.

### PAL

The European television standard, 50 pictures a second, which the Amiga's display follows in Europe; the port's default.

First in [chapter 1](part-1/faithful.md). The detail: `SPEC.md`, section 6.2, "Video".

### Palette

The table that turns a pixel's colour number into a colour: on the Amiga up to 32 entries of 4,096 possible colours, changed part of the way down the screen.

First in [chapter 1](part-1/faithful.md). The detail: `re/notes/display.md`.

### Pass

One round of the game's main loop, which draws one picture and runs part of the game's logic; two VBlanks long on a real PAL Amiga in a quiet scene.

First in [chapter 1](part-1/faithful.md). The detail: `re/notes/passes.md`.

### Paula

The Amiga's chip for sound, four channels that each play 8-bit sound samples at their own rate and volume; it also handles the interrupts, the disk and the serial port.

First in [chapter 2](part-1/amiga.md). The detail: `re/notes/sound.md`.

### Remake

A new program made to look and play like an old one, written from watching the old one.

First in [chapter 1](part-1/faithful.md). The detail: `SPEC.md`, section 1.

### Shell

The thin layer of JavaScript around the core that gives it a screen, sound, the keys and a place to keep saved games.

First in [chapter 1](part-1/faithful.md). The detail: `SPEC.md`, section 6.2.

### Sound sample

A recorded waveform that Paula plays back on one of its four channels, at its own pitch and volume.

First in [chapter 1](part-1/faithful.md). The detail: `re/notes/sound.md`.

### VBlank

The vertical blank, the moment the beam has finished a picture and returns to the top: 50 times a second on a PAL Amiga, and the clock the game counts its time in.

First in [chapter 2](part-1/amiga.md). The detail: `re/notes/passes.md`.

### Vertical flip

The game's command that swaps the stick's forward and back, for players who want a pilot's stick; in the port a remembered preference.

First in [chapter 1](part-1/faithful.md). The detail: `re/notes/keys.md`, "The vertical flip, and how long it lasts".

### WebAssembly

A compact binary form of program that every current browser runs: the form the port's core is compiled to.

First in [chapter 1](part-1/faithful.md). The detail: `SPEC.md`, section 5.
