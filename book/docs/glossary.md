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

### Paula

The Amiga's chip for sound, four channels that each play 8-bit samples at their own rate and volume; it also handles the interrupts, the disk and the serial port.

First in [chapter 2](part-1/amiga.md). The detail: `re/notes/sound.md`.

### VBlank

The vertical blank, the moment the beam has finished a picture and returns to the top: 50 times a second on a PAL Amiga, and the clock the game counts its time in.

First in [chapter 2](part-1/amiga.md). The detail: `re/notes/passes.md`.
