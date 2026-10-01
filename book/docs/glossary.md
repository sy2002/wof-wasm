# The glossary

Every term the book introduces, in alphabetical order. An entry gives the term, its definition in one line, the chapter where you first meet it and the chapter that defines it, the note of the repository that holds the detail, and, where a good page exists, where to read more elsewhere.

### 68000

Motorola's processor, the chip in the Amiga that runs the program: sixteen registers of 32 bits, eight for data and eight for addresses, and instructions that work on bytes, words of 16 bits and longs of 32.

First met in [chapter 1](part-1/faithful.md), defined in [chapter 2](part-1/amiga.md). The detail: [`SPEC.md`](repo:SPEC.md), sections [3.2](repo:SPEC.md#32-executable) and [7.1](repo:SPEC.md#71-arithmetic).

Elsewhere: [Motorola 68000](https://en.wikipedia.org/wiki/Motorola%5F68000), Wikipedia; [*M68000 Family Programmer's Reference Manual*](https://archive.org/details/m68000familyprog0000unse), Internet Archive.

### A4

The 68000's address register 4, which the game's code keeps as its small-data base, `0x02AFFE` in the fixed load layout: see [Small-data base](#small-data-base).

First met and defined in [chapter 3](part-1/disk.md). The detail: [`SPEC.md`](repo:SPEC.md#32-executable), section 3.2.

### A5

The 68000's address register 5, which every compiled C routine of the game uses as the pointer to its stack frame: see [Stack frame](#stack-frame).

First met and defined in [chapter 3](part-1/disk.md). The detail: [`SPEC.md`](repo:SPEC.md#32-executable), section 3.2.

### ADF

An Amiga Disk File: a copy of an Amiga floppy, block by block, in one file, a double-density disk's 1,760 blocks of 512 bytes; the game's disk is [`original/wof.adf`](repo:original/wof.adf).

First met and defined in [chapter 3](part-1/disk.md). The detail: [`SPEC.md`](repo:SPEC.md), sections [2](repo:SPEC.md#2-repository) and [3.1](repo:SPEC.md#31-disk).

Elsewhere: [Amiga Disk File](https://en.wikipedia.org/wiki/Amiga%5FDisk%5FFile), Wikipedia; [Laurent Clévy's *ADF format FAQ*](https://web.archive.org/web/20241206200729/http://lclevy.free.fr/adflib/adf%5Finfo.html), the Wayback Machine's copy.

### Arithmetic shift

A shift of a number's bits that keeps its sign: shifted right, the sign bit is copied into the top, so that a negative number stays negative and is halved, rounded down; shifted left, it differs from a logical shift only in setting the overflow flag when the sign changes. The 68000's `asr` and `asl`.

First met and defined in [chapter 5](part-1/oracle.md). The detail: [`tools/m68k_fix.py`](repo:tools/m68k%5Ffix.py); [`SPEC.md`](repo:SPEC.md#71-arithmetic), section 7.1.

Elsewhere: [Arithmetic shift](https://en.wikipedia.org/wiki/Arithmetic%5Fshift), Wikipedia; [*M68000 Family Programmer's Reference Manual*](https://archive.org/details/m68000familyprog0000unse), Internet Archive.

### Assembly language

The written form of machine code, one instruction a line, a short name for the operation followed by its operands: the form in which the listing shows the whole program, and in which much of the game was written by hand.

First met in [chapter 1](part-1/faithful.md), defined in [chapter 2](part-1/amiga.md). The detail: [`SPEC.md`](repo:SPEC.md#32-executable), section 3.2.

Elsewhere: [Assembly language](https://en.wikipedia.org/wiki/Assembly%5Flanguage), Wikipedia.

### Attract demo

A recorded game that the program plays by itself when left alone at the rank selection, and which it can record from a game played; not a demoscene production.

First met and defined in [chapter 1](part-1/faithful.md). The detail: [`re/notes/demo.md`](repo:re/notes/demo.md).

Elsewhere: [Attract mode](https://en.wikipedia.org/wiki/Attract%5Fmode), Wikipedia.

### Autopilot

A program that flies the headless original by a policy, looking at the game's state every VBlank and choosing the stick and the button; its choices, compressed into runs of VBlanks, become a mission script, which the original then flies the same way without it.

First met and defined in [chapter 8](part-1/mission.md). The detail: [`tools/m4_autopilot.py`](repo:tools/m4%5Fautopilot.py); [`re/notes/porting-m4.md`](repo:re/notes/porting-m4.md#the-scripts-of-part-2), "The scripts of part 2".

### Beam

The point where the display is drawing the picture, sweeping each line from left to right and the lines from top to bottom; its position, which a register of the custom chips reports, is the game's only source of chance.

First met in [chapter 1](part-1/faithful.md), defined in [chapter 2](part-1/amiga.md). The detail: [`re/notes/random.md`](repo:re/notes/random.md).

Elsewhere: [Raster scan](https://en.wikipedia.org/wiki/Raster%5Fscan), Wikipedia.

### Big-endian

The byte order that stores the most significant byte of a number first: the 68000's, and that of every file the project reads; the opposite of little-endian.

First met and defined in [chapter 3](part-1/disk.md). The detail: [`SPEC.md`](repo:SPEC.md), sections [3.5](repo:SPEC.md#35-file-formats) and [5](repo:SPEC.md#5-build).

Elsewhere: [Endianness](https://en.wikipedia.org/wiki/Endianness), Wikipedia.

### Bitplane

One bit of every pixel's colour number, kept as a picture of its own; five bitplanes together give each pixel one of 32 colours.

First met and defined in [chapter 2](part-1/amiga.md). The detail: [`re/notes/display.md`](repo:re/notes/display.md).

Elsewhere: [Planar (computer graphics)](https://en.wikipedia.org/wiki/Planar%5F(computer%5Fgraphics)), Wikipedia; [*Amiga Hardware Reference Manual*](https://archive.org/details/commodore-amiga-tech-ref-series-amiga-hardware-reference-manual-3rd-edition), 3rd edition, Internet Archive.

### Blitter

The Amiga's unit, inside the custom chip Agnus, for copying and combining rectangles of memory one bitplane at a time; it draws the game's shapes into the bitplanes while the processor goes on with other work.

First met in [chapter 1](part-1/faithful.md), defined in [chapter 2](part-1/amiga.md). The detail: [`re/notes/drawing.md`](repo:re/notes/drawing.md).

Elsewhere: [Blitter](https://en.wikipedia.org/wiki/Blitter), Wikipedia; [*Amiga Hardware Reference Manual*](https://archive.org/details/commodore-amiga-tech-ref-series-amiga-hardware-reference-manual-3rd-edition), 3rd edition, Internet Archive.

### BSS

A hunk of memory that starts at zero and is given in the program's file by its size alone; the game's is 4 bytes at `0x028000`.

First met and defined in [chapter 3](part-1/disk.md). The detail: [`SPEC.md`](repo:SPEC.md#32-executable), section 3.2.

Elsewhere: [.bss](https://en.wikipedia.org/wiki/.bss), Wikipedia.

### Calling convention

The rules by which a caller hands a routine its arguments and gets the result back: in the game's compiled C the arguments go onto the stack, 2 bytes for an int and 4 for a long or a pointer, and the result comes back in D0.

First met and defined in [chapter 3](part-1/disk.md). The detail: [`SPEC.md`](repo:SPEC.md#32-executable), section 3.2.

Elsewhere: [Calling convention](https://en.wikipedia.org/wiki/Calling%5Fconvention), Wikipedia; [*M68000 Family Programmer's Reference Manual*](https://archive.org/details/m68000familyprog0000unse), Internet Archive.

### Change report

A list a run of the headless original can write: for every record of its dump, each range of memory that changed, with the old and the new bytes, a name and the routines that wrote it.

First met and defined in [chapter 6](part-1/headless.md). The detail: [`re/notes/headless.md`](repo:re/notes/headless.md#change-report-entropy-log-schedule), "Change report, entropy log, schedule".

### Chip memory

The memory the Amiga's custom chips can read and write by themselves, without the processor; the game keeps its screens, copper lists, shapes, sound effects and songs there.

First met and defined in [chapter 2](part-1/amiga.md). The detail: [`re/notes/display.md`](repo:re/notes/display.md#memory), "Memory".

Elsewhere: [Amiga Chip RAM](https://en.wikipedia.org/wiki/Amiga%5FChip%5FRAM), Wikipedia; [*Amiga Hardware Reference Manual*](https://archive.org/details/commodore-amiga-tech-ref-series-amiga-hardware-reference-manual-3rd-edition), 3rd edition, Internet Archive.

### CIA

One of the Amiga's two interface chips, which serve its ports and carry timers of their own; the game reads the fire button from one, and its music player takes one of their timers for its beat.

First met and defined in [chapter 2](part-1/amiga.md). The detail: [`re/notes/music.md`](repo:re/notes/music.md#the-timer), "The timer".

Elsewhere: [MOS Technology CIA](https://en.wikipedia.org/wiki/MOS%5FTechnology%5FCIA), Wikipedia.

### Closed loop

The comparison in which the port runs on its own from the program's start, handed nothing but the entropy seed and the address of the map's records, and is compared with the original after every pass and every tick, so that every error it carries over shows.

First met and defined in [chapter 8](part-1/mission.md). The detail: [`tests/m4compare.py`](repo:tests/m4compare.py); [`SPEC.md`](repo:SPEC.md#8-verification), section 8, "Mission, pass by pass".

### Cold region

A stretch of a ported routine's instructions that no run of the mission scripts executed; each must be covered by a stand-in's marker or by a note saying what it is.

First met and defined in [chapter 8](part-1/mission.md). The detail: [`tools/reach_observe.py`](repo:tools/reach%5Fobserve.py); [`re/notes/porting-m4.md`](repo:re/notes/porting-m4.md#appendix-the-regions-no-run-executed), "Appendix: the regions no run executed".

Elsewhere: [Code coverage](https://en.wikipedia.org/wiki/Code%5Fcoverage), Wikipedia.

### Colour clock

The clock the Amiga's custom chips run on, 3,546,895 cycles a second on a PAL machine: half the processor's clock, and the unit of Paula's period.

First met and defined in [chapter 2](part-1/amiga.md). The detail: [`re/notes/sound.md`](repo:re/notes/sound.md#the-slots-and-what-they-play), "The slots and what they play".

Elsewhere: [*Amiga Hardware Reference Manual*](https://archive.org/details/commodore-amiga-tech-ref-series-amiga-hardware-reference-manual-3rd-edition), 3rd edition, Internet Archive.

### Completeness list

The list that sorts every address the original writes during a mission into a registered field of the port, state compared in another form, or state the port does not keep, with its reason and the milestone that owes it; each row names the routines that write it.

First met and defined in [chapter 8](part-1/mission.md). The detail: [`tests/m4complete.py`](repo:tests/m4complete.py); [`re/notes/porting-m4.md`](repo:re/notes/porting-m4.md#the-completeness-list), "The completeness list".

### Condition codes

The five bits X, N, Z, V and C that the 68000 sets after most instructions, saying whether the result was negative, zero or too large for its width and whether a carry came out; a conditional branch reads them.

They sit in the low byte of the status register. The emulator the tests run on works them out only when an instruction needs them, so the oracle reads them through an instruction of the 68000's own ([`re/notes/headless.md`](repo:re/notes/headless.md#unicorn-as-it-behaves-here), "Unicorn, as it behaves here").

First met and defined in [chapter 5](part-1/oracle.md). The detail: [`tools/oracle.py`](repo:tools/oracle.py); [`re/notes/ffp.md`](repo:re/notes/ffp.md#how-the-game-reaches-it), "How the game reaches it".

Elsewhere: [Status register](https://en.wikipedia.org/wiki/Status%5Fregister), Wikipedia; [*M68000 Family Programmer's Reference Manual*](https://archive.org/details/m68000familyprog0000unse), Internet Archive.

### Control

A deliberate change of the port in one place, made to see that the test meant to catch it fails, and at which step; a positive control is a change that must leave the result as it is.

First met and defined in [chapter 8](part-1/mission.md). The detail: [`re/notes/porting-m4.md`](repo:re/notes/porting-m4.md#how-the-port-is-held-to-the-original), "How the port is held to the original"; [`tools/m7_controls.py`](repo:tools/m7%5Fcontrols.py).

Elsewhere: [Mutation testing](https://en.wikipedia.org/wiki/Mutation%5Ftesting), Wikipedia.

### Control flow

The order in which a program's instructions run, set by its branches, jumps, calls and returns; the disassembler follows it to tell the code from the data among it.

First met and defined in [chapter 4](part-1/reading.md). The detail: [`tools/disasm.py`](repo:tools/disasm.py).

Elsewhere: [Control flow](https://en.wikipedia.org/wiki/Control%5Fflow), Wikipedia.

### Control-flow skeleton

A routine shown with only its labels, calls, branches, comparisons and returns, as [`tools/skel.py`](repo:tools/skel.py) prints it from the listing: the first step of porting a routine, before it is read in full.

First met and defined in [chapter 4](part-1/reading.md). The detail: [`SPEC.md`](repo:SPEC.md#74-working-method), section 7.4.

### Copper

The Amiga's display coprocessor: it follows a list of waits and register writes in step with the beam, and so changes colours and screen modes part of the way down the picture.

First met in [chapter 1](part-1/faithful.md), defined in [chapter 2](part-1/amiga.md). The detail: [`re/notes/display.md`](repo:re/notes/display.md).

Elsewhere: [Original Chip Set](https://en.wikipedia.org/wiki/Original%5FChip%5FSet), Wikipedia; [*Amiga Hardware Reference Manual*](https://archive.org/details/commodore-amiga-tech-ref-series-amiga-hardware-reference-manual-3rd-edition), 3rd edition, Internet Archive.

### Core

The port's game: the ported logic, written in C and compiled to WebAssembly, which knows nothing of the browser around it.

First met and defined in [chapter 1](part-1/faithful.md). The detail: [`SPEC.md`](repo:SPEC.md#61-core), section 6.1.

### Coupling

A piece of state that a pass writes and a logic tick reads, such as the pass counter or the drawing copy in an object's record; through the couplings, the number of VBlanks a pass takes reaches the simulation.

First met and defined in [chapter 7](part-1/time.md). The detail: [`re/notes/passes.md`](repo:re/notes/passes.md#the-answer), "The answer".

### Crack

A change made to a program to remove its copy protection; the disk this port was made from carries one.

First met and defined in [chapter 1](part-1/faithful.md). The detail: [`SPEC.md`](repo:SPEC.md#31-disk), section 3.1.

Elsewhere: [Software cracking](https://en.wikipedia.org/wiki/Software%5Fcracking), Wikipedia.

### Custom chips

The Amiga's own chips beside the processor: Agnus with the copper and the blitter, Denise for the display, Paula for the sound. A program sets them to work through their registers, and they then work from chip memory by themselves.

First met and defined in [chapter 2](part-1/amiga.md). The detail: [`SPEC.md`](repo:SPEC.md#34-operating-system-and-hardware-use), section 3.4.

Elsewhere: [Original Chip Set](https://en.wikipedia.org/wiki/Original%5FChip%5FSet), Wikipedia; [*Amiga Hardware Reference Manual*](https://archive.org/details/commodore-amiga-tech-ref-series-amiga-hardware-reference-manual-3rd-edition), 3rd edition, Internet Archive.

### Differential test

A test that hands two implementations of the same thing the same input and demands the same output; the oracle's tests run the original's routine and its port so.

First met and defined in [chapter 5](part-1/oracle.md). The detail: [`SPEC.md`](repo:SPEC.md#74-working-method), section 7.4; [`tests/test_oracle_m1.py`](repo:tests/test%5Foracle%5Fm1.py).

Elsewhere: [Differential testing](https://en.wikipedia.org/wiki/Differential%5Ftesting), Wikipedia.

### Disassembler

A tool that turns machine code back into assembly language; the project's, [`tools/disasm.py`](repo:tools/disasm.py), follows the program's control flow and writes the listing and the routine inventory.

First met and defined in [chapter 4](part-1/reading.md). The detail: [`SPEC.md`](repo:SPEC.md#4-tools), section 4.

Elsewhere: [Disassembler](https://en.wikipedia.org/wiki/Disassembler), Wikipedia.

### Double buffering

Drawing into a hidden picture and showing it only when it is whole; the game keeps two screens, each with its own copper list, and swaps them with one register write.

First met and defined in [chapter 2](part-1/amiga.md). The detail: [`re/notes/display.md`](repo:re/notes/display.md#double-buffering-and-the-swap), "Double buffering and the swap".

Elsewhere: [Multiple buffering](https://en.wikipedia.org/wiki/Multiple%5Fbuffering), Wikipedia.

### Dump

The file a run of the headless original writes: the game's whole state when a mission is set up and after every logic tick and every pass, each record with a SHA-256 fingerprint of the state, for the comparisons with the port.

First met and defined in [chapter 6](part-1/headless.md). The detail: [`tools/headless_dump.py`](repo:tools/headless%5Fdump.py); [`re/notes/headless.md`](repo:re/notes/headless.md#dump), "Dump".

### Emulator

A program that imitates a computer's processor and chips closely enough that the computer's own programs run on it unchanged.

First met and defined in [chapter 1](part-1/faithful.md). The detail: [`README.md`](repo:README.md#amiga-to-web), "Amiga to Web".

Elsewhere: [Emulator](https://en.wikipedia.org/wiki/Emulator), Wikipedia.

### Entropy stream

The reproducible stream of values that stands in for the beam's position, one value for every read; the headless original and the port draw from the same one, so that both meet the same chance.

First met and defined in [chapter 6](part-1/headless.md). The detail: [`re/notes/random.md`](repo:re/notes/random.md#consequences), "Consequences"; [`re/notes/headless.md`](repo:re/notes/headless.md#entropy), "Entropy".

Elsewhere: [Linear congruential generator](https://en.wikipedia.org/wiki/Linear%5Fcongruential%5Fgenerator), Wikipedia.

### Faithful port

One game carried to another machine by rewriting its own logic, routine by routine, from its machine code, and held to the original by comparison.

First met and defined in [chapter 1](part-1/faithful.md). The detail: [`SPEC.md`](repo:SPEC.md#1-goal), section 1.

Elsewhere: [Porting](https://en.wikipedia.org/wiki/Porting), Wikipedia.

### Far-call table

185 jump instructions at the start of the game's data hunk, `0x023000` to `0x023456`, each holding the full address of a routine; a call such as `jsr -$7e1e(a4)` goes through one of them and needs no relocation of its own.

First met and defined in [chapter 3](part-1/disk.md). The detail: [`SPEC.md`](repo:SPEC.md#32-executable), section 3.2.

### Fast floating point

Motorola's floating-point format of 32 bits, whose routines live in the Amiga's ROM; the game's flight model computes in it, and the port reproduces it bit for bit in integer code.

A number in fast floating point fills one 32-bit register: a mantissa of 24 bits, a sign bit and an exponent of 7 bits, with no infinity and no NaN ([`re/notes/ffp.md`](repo:re/notes/ffp.md#the-format), "The format"). The game computes with it in two routines of its tick, the player's motion and an enemy aircraft's, which use six of the library's nine operations ([`SPEC.md`](repo:SPEC.md#34-operating-system-and-hardware-use), section 3.4). The port does the same arithmetic in integer code, instruction for instruction from the ROM's own routines, because a browser's floating point rounds differently and the game's state would drift ([`SPEC.md`](repo:SPEC.md#71-arithmetic), section 7.1); every operation is tested against the ROM under the oracle.

First met and defined in [chapter 1](part-1/faithful.md). The detail: [`re/notes/ffp.md`](repo:re/notes/ffp.md).

### Fixed load layout

The one set of addresses at which all the project's tools load the game's program: the code at `0x010000`, the data at `0x023000`, the BSS at `0x028000`, A4 holding `0x02AFFE`. Every address of the program in this book is one of it; the running port holds offsets instead.

First met and defined in [chapter 3](part-1/disk.md). The detail: [`SPEC.md`](repo:SPEC.md#32-executable), section 3.2; [`tools/hunk.py`](repo:tools/hunk.py).

### FPGA recreation

A computer rebuilt in programmable hardware, a chip whose circuits are configured to behave like the original machine's.

First met and defined in [chapter 1](part-1/faithful.md). The detail: [`README.md`](repo:README.md#amiga-to-web), "Amiga to Web".

Elsewhere: [Field-programmable gate array](https://en.wikipedia.org/wiki/Field-programmable%5Fgate%5Farray), Wikipedia.

### Front end

The game's screens before and between missions: the story, the title, the rank selection, the briefing, the high scores and the dialogs.

First met in [chapter 3](part-1/disk.md), defined in [chapter 19](part-2/front-end.md). The detail: [`re/notes/frontend.md`](repo:re/notes/frontend.md).

### Harness

The headless original's own code around the original program, written in Python: the stubs, the hooks, the script, the entropy stream and the dump.

First met and defined in [chapter 6](part-1/headless.md). The detail: [`tools/headless.py`](repo:tools/headless.py); [`re/notes/headless.md`](repo:re/notes/headless.md).

### Headless original

The original program run from its `main` routine on under emulation without a screen, the operating system's calls answered by stubs, the ROM's floating point, its key conversion and the game's music player run for real: the reference the port is compared with.

First met and defined in [chapter 1](part-1/faithful.md). The detail: [`re/notes/headless.md`](repo:re/notes/headless.md).

### Hexadecimal

Numbers in base 16, the digits 0 to 9 and A to F; this book marks them with `0x`, as in `0xDFF000`, and the listing with a `$`, as Motorola's assemblers do.

First met and defined in [chapter 2](part-1/amiga.md). The detail: [`book/BOOK.md`](repo:book/BOOK.md#4-the-style-guide), section 4, point 3.

Elsewhere: [Hexadecimal](https://en.wikipedia.org/wiki/Hexadecimal), Wikipedia.

### Hook

A routine of the instrument's own that the emulator calls whenever the program reaches a chosen instruction or touches chosen memory; the oracle corrects the emulator with hooks, and the headless original watches the game through them.

First met and defined in [chapter 5](part-1/oracle.md). The detail: [`tools/m68k_fix.py`](repo:tools/m68k%5Ffix.py); [`re/notes/headless.md`](repo:re/notes/headless.md#unicorn-as-it-behaves-here), "Unicorn, as it behaves here".

Elsewhere: [Hooking](https://en.wikipedia.org/wiki/Hooking), Wikipedia.

### Hunk

A part of an Amiga program that is loaded into memory as a whole: code, data with its starting values, or BSS.

First met and defined in [chapter 3](part-1/disk.md). The detail: [`SPEC.md`](repo:SPEC.md#32-executable), section 3.2.

Elsewhere: [Amiga Hunk](https://en.wikipedia.org/wiki/Amiga%5FHunk), Wikipedia; [*The AmigaDOS Manual*](https://archive.org/details/1991-baker-jesup-et-al-the-amigados-manual-3rd-ed), 3rd edition, Internet Archive.

### Hunk file

The AmigaDOS format for programs: a header giving the number of hunks and their sizes, then each hunk's contents, its relocations and an end mark; the game, its music player and its songs are hunk files.

First met and defined in [chapter 3](part-1/disk.md). The detail: [`tools/hunk.py`](repo:tools/hunk.py); [`SPEC.md`](repo:SPEC.md#32-executable), section 3.2.

Elsewhere: [Amiga Hunk](https://en.wikipedia.org/wiki/Amiga%5FHunk), Wikipedia; [*The AmigaDOS Manual*](https://archive.org/details/1991-baker-jesup-et-al-the-amigados-manual-3rd-ed), 3rd edition, Internet Archive.

### IFF ILBM

The Amiga's standard format for pictures: a file of chunks, each a name of four letters, its length and its contents, giving a picture's size, colours and bitplanes; the game's pictures and three of its palettes use it.

First met and defined in [chapter 3](part-1/disk.md). The detail: [`SPEC.md`](repo:SPEC.md#35-file-formats), section 3.5, "Pictures".

Elsewhere: [ILBM](https://en.wikipedia.org/wiki/ILBM), Wikipedia; [Interchange File Format](https://en.wikipedia.org/wiki/Interchange%5FFile%5FFormat), Wikipedia.

### Input byte

The byte that carries the stick's four directions and the button into one logic tick, the only way the stick and the button reach the game's logic; the key commands come in through the game's own key handler.

First met and defined in [chapter 1](part-1/faithful.md). The detail: [`re/notes/input.md`](repo:re/notes/input.md).

### Input queue

The list of up to six input bytes that the VBlank server fills every fourth VBlank and the logic ticks empty, one byte a tick; when it is full, the oldest byte is dropped.

First met and defined in [chapter 7](part-1/time.md). The detail: [`SPEC.md`](repo:SPEC.md#33-runtime-model), section 3.3; [`re/notes/input.md`](repo:re/notes/input.md#the-chain), "The chain".

Elsewhere: [FIFO (computing and electronics)](https://en.wikipedia.org/wiki/FIFO%5F(computing%5Fand%5Felectronics)), Wikipedia.

### Input sample

The taking of one input byte, which the game does every fourth VBlank, and the byte so taken; never a sound.

First met and defined in [chapter 1](part-1/faithful.md). The detail: [`re/notes/input.md`](repo:re/notes/input.md).

### int (the C type)

C's ordinary type for whole numbers: 16 bits wide in Manx Aztec C as the game was built, 32 in the compilers that build the port, which therefore names the width of every value of the game.

First met and defined in [chapter 3](part-1/disk.md). The detail: [`SPEC.md`](repo:SPEC.md#71-arithmetic), section 7.1.

Elsewhere: [C data types](https://en.wikipedia.org/wiki/C%5Fdata%5Ftypes), Wikipedia.

### Interrupt

A signal from the hardware that makes the processor put aside what it is doing, run a short routine and carry on where it was; the VBlank and Paula's channels raise them.

First met in [chapter 1](part-1/faithful.md), defined in [chapter 2](part-1/amiga.md). The detail: [`re/notes/headless.md`](repo:re/notes/headless.md#scheduling), "Scheduling".

Elsewhere: [Interrupt](https://en.wikipedia.org/wiki/Interrupt), Wikipedia.

### Keyboard assist

The port's switch that makes one key press one step in the weapon menu and lets a short tap reach the game exactly once everywhere else; off in every comparison with the original.

First met and defined in [chapter 1](part-1/faithful.md). The detail: [`re/notes/porting-m4.md`](repo:re/notes/porting-m4.md#the-keyboard-assist), "The keyboard assist".

### Kickstart

The heart of AmigaOS, in the ROM of the Amiga 500 and 2000 and loaded from a disk by the 1000; the port takes the font and the key table from Kickstart 1.3 when it is built and is held to its floating point, and the ROM is not part of the repository.

First met and defined in [chapter 2](part-1/amiga.md). The detail: [`re/notes/system-font.md`](repo:re/notes/system-font.md#the-rom), "The ROM".

Elsewhere: [Kickstart (Amiga)](https://en.wikipedia.org/wiki/Kickstart%5F(Amiga)), Wikipedia.

### Label

A name the listing gives an address that a branch or a call leads to, on a line of its own and ending in a colon: a routine's name, a name the project gave a place inside one, or `loc_` and the address.

First met and defined in [chapter 4](part-1/reading.md). The detail: [`re/Wings.lst`](repo:re/Wings.lst).

Elsewhere: [Label (computer science)](https://en.wikipedia.org/wiki/Label%5F(computer%5Fscience)), Wikipedia.

### Latch

A flag that keeps a brief event until it is read; the game latches a tap and a hold of the fire button between two input samples, so that a tap shorter than the interval between them still reaches the game.

First met and defined in [chapter 7](part-1/time.md). The detail: [`re/notes/input.md`](repo:re/notes/input.md#fire-button-and-the-taphold-discrimination), "Fire button and the tap/hold discrimination".

### Library

A collection of the operating system's routines that a program calls through a table of jumps at fixed offsets from the library's address; the game uses dos, exec, graphics and mathffp among others.

First met and defined in [chapter 2](part-1/amiga.md). The detail: [`SPEC.md`](repo:SPEC.md#34-operating-system-and-hardware-use), section 3.4.

Elsewhere: [Library (computing)](https://en.wikipedia.org/wiki/Library%5F(computing)), Wikipedia; [*Amiga ROM Kernel Reference Manual: Libraries*](https://archive.org/details/commodore-amiga-tech-ref-series-amiga-rom-kernel-reference-manual-libraries-3rd-edition), 3rd edition, Internet Archive.

### Library base

The address of a library in memory, which a program keeps in a variable and loads into A6 to call one of the library's routines at a fixed offset below it; [`re/libbases.txt`](repo:re/libbases.txt) names the game's five.

First met and defined in [chapter 4](part-1/reading.md). The detail: [`tools/disasm.py`](repo:tools/disasm.py); [`tools/fd/`](repo:tools/fd/).

Elsewhere: [*Amiga ROM Kernel Reference Manual: Libraries*](https://archive.org/details/commodore-amiga-tech-ref-series-amiga-rom-kernel-reference-manual-libraries-3rd-edition), 3rd edition, Internet Archive.

### Listing

The game's program written out as assembly language by the disassembler, each instruction with its address, its bytes and the names of what it touches: [`re/Wings.lst`](repo:re/Wings.lst).

First met in [chapter 1](part-1/faithful.md), defined in [chapter 4](part-1/reading.md). The detail: [`SPEC.md`](repo:SPEC.md), sections [2](repo:SPEC.md#2-repository) and [4](repo:SPEC.md#4-tools).

Elsewhere: [Disassembler](https://en.wikipedia.org/wiki/Disassembler), Wikipedia.

### Little-endian

The byte order that stores the least significant byte of a number first: that of the machines the port runs on, WebAssembly's among them; the opposite of big-endian.

First met and defined in [chapter 3](part-1/disk.md). The detail: [`tools/extract_tables.py`](repo:tools/extract%5Ftables.py).

Elsewhere: [Endianness](https://en.wikipedia.org/wiki/Endianness), Wikipedia.

### LoadSeg

The routine of AmigaDOS that loads a hunk file: it puts each hunk wherever it finds free memory of the kind asked for and corrects the relocations; the game loads its music with it.

First met and defined in [chapter 3](part-1/disk.md). The detail: [`re/notes/music.md`](repo:re/notes/music.md#the-two-files), "The two files".

Elsewhere: [*Amiga ROM Kernel Reference Manual: Libraries*](https://archive.org/details/commodore-amiga-tech-ref-series-amiga-rom-kernel-reference-manual-libraries-3rd-edition), 3rd edition, Internet Archive.

### Logic tick

One step of the game's simulation, one for every input byte, taken every fourth VBlank: 12.5 a second on a PAL Amiga, so that in a quiet scene two passes go to a tick.

First met and defined in [chapter 1](part-1/faithful.md). The detail: [`SPEC.md`](repo:SPEC.md#33-runtime-model), section 3.3.

### Logical shift

A shift of a number's bits that fills the vacated places with zeros, which halves a number without a sign as it shifts right but turns a negative one into a large positive one: the 68000's `lsr`.

First met and defined in [chapter 5](part-1/oracle.md). The detail: [`tools/m68k_fix.py`](repo:tools/m68k%5Ffix.py).

Elsewhere: [Logical shift](https://en.wikipedia.org/wiki/Logical%5Fshift), Wikipedia; [*M68000 Family Programmer's Reference Manual*](https://archive.org/details/m68000familyprog0000unse), Internet Archive.

### Machine code

A program as the processor reads it: its instructions as numbers in memory.

First met in [chapter 1](part-1/faithful.md), defined in [chapter 2](part-1/amiga.md). The detail: [`SPEC.md`](repo:SPEC.md#32-executable), section 3.2.

Elsewhere: [Machine code](https://en.wikipedia.org/wiki/Machine%5Fcode), Wikipedia.

### Manx Aztec C

The C compiler the game's C was built with: its int, as the game was built, is 16 bits, its code reaches the variables through A4, and each of its routines keeps a stack frame on A5.

First met and defined in [chapter 3](part-1/disk.md). The detail: [`SPEC.md`](repo:SPEC.md#32-executable), section 3.2.

Elsewhere: [Aztec C](https://en.wikipedia.org/wiki/Aztec%5FC), Wikipedia.

### Mask

A one-bit picture of where a shape has any colour at all: the OR of its planes, or, for a shape of one plane, that plane; the blitter draws the shape's bits where the mask is set and keeps the background elsewhere.

First met and defined in [chapter 2](part-1/amiga.md). The detail: [`re/notes/drawing.md`](repo:re/notes/drawing.md#what-shape%5Fdraw-does-exactly), "What `shape_draw` does, exactly".

Elsewhere: [Mask (computing)](https://en.wikipedia.org/wiki/Mask%5F(computing)), Wikipedia.

### Memory-form shift

A 68000 shift that works on a word in memory, by one bit, rather than on a register; the emulator the tests run on takes the game's five arithmetic ones for logical shifts, which gives three of them, the right shifts, a wrong word, and a hook corrects those three.

First met and defined in [chapter 5](part-1/oracle.md). The detail: [`re/notes/porting-m5.md`](repo:re/notes/porting-m5.md#the-emulators-memory-form-shift-observed), "The emulator's memory-form shift (observed)"; [`tools/m68k_fix.py`](repo:tools/m68k%5Ffix.py).

Elsewhere: [*M68000 Family Programmer's Reference Manual*](https://archive.org/details/m68000familyprog0000unse), Internet Archive.

### Mission script

A recorded sequence of stick and key inputs that flies a mission the same way every time, for the original and the port alike.

First met and defined in [chapter 1](part-1/faithful.md). The detail: [`re/notes/porting-m4.md`](repo:re/notes/porting-m4.md#how-the-port-is-held-to-the-original), "How the port is held to the original".

### Native library

The port's C compiled by the test machine's own compiler into a library that the tests load and call directly, beside the WebAssembly of the page, which is built from the same sources.

First met and defined in [chapter 5](part-1/oracle.md). The detail: [`SPEC.md`](repo:SPEC.md), sections [5](repo:SPEC.md#5-build) and [8](repo:SPEC.md#8-verification).

### Observer

A hook of the headless original on a routine's first instruction that records every entry with the registers and the arguments, and only reads, so that watching changes nothing.

First met and defined in [chapter 6](part-1/headless.md). The detail: [`re/notes/headless.md`](repo:re/notes/headless.md#observers), "Observers".

### Opcode

The first word of a 68000 instruction, which names the operation and how its operands are found, and so how many words the instruction has.

First met and defined in [chapter 4](part-1/reading.md). The detail: [`tools/disasm.py`](repo:tools/disasm.py).

Elsewhere: [Opcode](https://en.wikipedia.org/wiki/Opcode), Wikipedia; [*M68000 Family Programmer's Reference Manual*](https://archive.org/details/m68000familyprog0000unse), Internet Archive.

### Open loop

The comparison in which the port is set to the original's state after every pass and every tick, so that each step starts from the original's state and is compared alone, and a difference names its step.

First met and defined in [chapter 8](part-1/mission.md). The detail: [`tests/m4compare.py`](repo:tests/m4compare.py); [`SPEC.md`](repo:SPEC.md#8-verification), section 8, "Mission, pass by pass".

### Oracle

The instrument that runs one original routine on an emulated 68000 beside its port, on the same inputs, and compares the results.

The original runs under the emulator Unicorn with the program at the fixed load layout, called by the compiler's convention or with its registers set by hand; the port runs as the native library; the result, the memory each side touched and, where they matter, the condition codes are compared, on every input where the inputs are few and on random ones from a fixed seed where they are many.

First met and defined in [chapter 1](part-1/faithful.md). The detail: [`SPEC.md`](repo:SPEC.md), sections [7.4](repo:SPEC.md#74-working-method) and [8](repo:SPEC.md#8-verification); [`tools/oracle.py`](repo:tools/oracle.py); [chapter 5](part-1/oracle.md).

Elsewhere: [Test oracle](https://en.wikipedia.org/wiki/Test%5Foracle), Wikipedia.

### PAL

The European television standard, 50 pictures a second, which the Amiga's display follows in Europe; the port's default.

First met and defined in [chapter 1](part-1/faithful.md). The detail: [`SPEC.md`](repo:SPEC.md#62-shell), section 6.2, "Video".

Elsewhere: [PAL](https://en.wikipedia.org/wiki/PAL), Wikipedia.

### Palette

The table that turns a pixel's colour number into a colour: on the Amiga up to 32 entries of 4,096 possible colours, changed part of the way down the screen.

First met and defined in [chapter 1](part-1/faithful.md). The detail: [`re/notes/display.md`](repo:re/notes/display.md).

Elsewhere: [Palette (computing)](https://en.wikipedia.org/wiki/Palette%5F(computing)), Wikipedia.

### Pass

One round of the inner loop, the loop that plays a mission: it draws one picture and runs the part of the logic that goes by pictures. Two VBlanks long on a real PAL Amiga in a quiet scene, so two passes go to a tick.

First met and defined in [chapter 1](part-1/faithful.md). The detail: [`re/notes/passes.md`](repo:re/notes/passes.md).

### Paula

The Amiga's chip for sound, four channels that each play 8-bit sound samples at their own rate and volume; it also handles the interrupts, the disk and the serial port.

First met and defined in [chapter 2](part-1/amiga.md). The detail: [`re/notes/sound.md`](repo:re/notes/sound.md).

Elsewhere: [Original Chip Set](https://en.wikipedia.org/wiki/Original%5FChip%5FSet), Wikipedia; [*Amiga Hardware Reference Manual*](https://archive.org/details/commodore-amiga-tech-ref-series-amiga-hardware-reference-manual-3rd-edition), 3rd edition, Internet Archive.

### Period

Paula's measure of pitch: how many ticks of the colour clock, 3,546,895 a second on a PAL Amiga, each byte of a sound sample is held; a smaller period plays higher.

First met and defined in [chapter 2](part-1/amiga.md). The detail: [`re/notes/sound.md`](repo:re/notes/sound.md).

### Poke

A value written into one address of the game's state at a fixed point of a run, on both sides, the original and the port, so that a script reaches a state no flight of its length reaches.

First met and defined in [chapter 8](part-1/mission.md). The detail: [`tests/m4compare.py`](repo:tests/m4compare.py); [`re/notes/porting-m5.md`](repo:re/notes/porting-m5.md#the-scripts), "The scripts".

Elsewhere: [PEEK and POKE](https://en.wikipedia.org/wiki/PEEK%5Fand%5FPOKE), Wikipedia.

### Program counter

The 68000's register that holds the address of the instruction being executed; an address given relative to it names a distance from the instruction, not a place, so such a call needs no correcting wherever the program is loaded.

First met in [chapter 3](part-1/disk.md), defined in [chapter 4](part-1/reading.md). The detail: [`tools/disasm.py`](repo:tools/disasm.py).

Elsewhere: [Program counter](https://en.wikipedia.org/wiki/Program%5Fcounter), Wikipedia; [*M68000 Family Programmer's Reference Manual*](https://archive.org/details/m68000familyprog0000unse), Internet Archive.

### Pure routine

A routine that computes from its inputs alone, without touching anything else; every pure routine is held to the original under the oracle.

First met and defined in [chapter 1](part-1/faithful.md). The detail: [`SPEC.md`](repo:SPEC.md#74-working-method), section 7.4.

Elsewhere: [Pure function](https://en.wikipedia.org/wiki/Pure%5Ffunction), Wikipedia.

### Reach map

The record of which routines, and which of their instructions, the mission scripts execute in the headless original, counted by the window of the run and the phase; what it shows the game runs is what the port carries.

First met and defined in [chapter 8](part-1/mission.md). The detail: [`tools/reach_observe.py`](repo:tools/reach%5Fobserve.py); [`re/notes/porting-m4.md`](repo:re/notes/porting-m4.md#what-decides-what-is-ported-the-reach-map), "What decides what is ported: the reach map".

Elsewhere: [Code coverage](https://en.wikipedia.org/wiki/Code%5Fcoverage), Wikipedia.

### Register

A small named store inside a processor or a chip: the 68000's sixteen hold the values it computes with, and a custom chip's, at fixed addresses from `0xDFF000`, tell the chip what to do.

First met in [chapter 1](part-1/faithful.md), defined in [chapter 2](part-1/amiga.md). The detail: [`re/notes/drawing.md`](repo:re/notes/drawing.md#the-blitter-library), "The blitter library".

Elsewhere: [Processor register](https://en.wikipedia.org/wiki/Processor%5Fregister), Wikipedia; [*M68000 Family Programmer's Reference Manual*](https://archive.org/details/m68000familyprog0000unse), Internet Archive.

### Relocation

An entry in a hunk file that names a place in a hunk holding an address, which the loader corrects by where its target hunk landed.

First met and defined in [chapter 3](part-1/disk.md). The detail: [`tools/hunk.py`](repo:tools/hunk.py); [`SPEC.md`](repo:SPEC.md#32-executable), section 3.2.

Elsewhere: [Relocation (computing)](https://en.wikipedia.org/wiki/Relocation%5F(computing)), Wikipedia; [*The AmigaDOS Manual*](https://archive.org/details/1991-baker-jesup-et-al-the-amigados-manual-3rd-ed), 3rd edition, Internet Archive.

### Remake

A new program made to look and play like an old one, written from watching the old one.

First met and defined in [chapter 1](part-1/faithful.md). The detail: [`SPEC.md`](repo:SPEC.md#1-goal), section 1.

Elsewhere: [Video game remake](https://en.wikipedia.org/wiki/Video%5Fgame%5Fremake), Wikipedia.

### Routine

A piece of the program that is called, does one job and returns to its caller; the game's program has 616, 223 of them compiled from C, each a row of the routine inventory.

First met in [chapter 1](part-1/faithful.md), defined in [chapter 4](part-1/reading.md). The detail: [`re/functions.csv`](repo:re/functions.csv).

Elsewhere: [Function (computer programming)](https://en.wikipedia.org/wiki/Function%5F(computer%5Fprogramming)), Wikipedia.

### Routine inventory

[`re/functions.csv`](repo:re/functions.csv): a row for each of the program's 616 routines, with its address, name, kind, size, frame, callers, calls, library calls and its status in the port, made with the listing; the status is the one column kept by hand.

First met and defined in [chapter 4](part-1/reading.md). The detail: [`SPEC.md`](repo:SPEC.md#74-working-method), section 7.4; [the routine inventory](routines.md).

### Rpck

The game's own packed format, named after the four letters a packed file begins with: the unpacked size, then control bytes that copy bytes or repeat one; ten files of the disk use it.

First met and defined in [chapter 3](part-1/disk.md). The detail: [`SPEC.md`](repo:SPEC.md#35-file-formats), section 3.5; [`tools/rpck.py`](repo:tools/rpck.py).

### Run description

A small JSON file that says what one run of the headless original is: its script of the stick, the button and the keys by VBlank, its entropy stream, the VBlanks a pass and where it stops.

First met and defined in [chapter 6](part-1/headless.md). The detail: [`re/notes/headless.md`](repo:re/notes/headless.md#run-description), "Run description"; [`tests/runs/`](repo:tests/runs/).

### Schedule

The order of a run's VBlanks, passes and logic ticks as they happened; the VBlanks a pass takes are a setting of the run, so the schedule is an input of the simulation.

First met and defined in [chapter 6](part-1/headless.md). The detail: [`re/notes/passes.md`](repo:re/notes/passes.md#what-the-question-is), "What the question is"; [`re/notes/headless.md`](repo:re/notes/headless.md#scheduling), "Scheduling".

### Shape container

A file of many shapes, the format that begins with `PPkc`: the number of shapes, a name of four characters for each, where each shape's entry begins, and the entries, each a header and the planes; the disk has twelve.

First met in [chapter 2](part-1/amiga.md), defined in [chapter 3](part-1/disk.md). The detail: [`re/notes/shapes.md`](repo:re/notes/shapes.md).

### Shell

The thin layer of JavaScript around the core: the clock that paces it, the screen, a loudspeaker for the sound the core mixes, the keys, a place for saved games, and the help screen, the pause sign and fullscreen.

First met and defined in [chapter 1](part-1/faithful.md). The detail: [`SPEC.md`](repo:SPEC.md#62-shell), section 6.2.

### Sign extension

Widening a number to more bits by copying its sign bit into the new ones, so that it keeps its value: the 68000's `ext.l` widens a word to a long.

First met and defined in [chapter 3](part-1/disk.md). The detail: [`SPEC.md`](repo:SPEC.md#71-arithmetic), section 7.1.

Elsewhere: [Sign extension](https://en.wikipedia.org/wiki/Sign%5Fextension), Wikipedia; [*M68000 Family Programmer's Reference Manual*](https://archive.org/details/m68000familyprog0000unse), Internet Archive.

### Signed byte

A byte read as a number from −128 to 127 in two's complement, in which the top bit counts as −128: a byte above `0x7F` is itself less 256.

First met in [chapter 2](part-1/amiga.md), defined in [chapter 3](part-1/disk.md). The detail: [`SPEC.md`](repo:SPEC.md#35-file-formats), section 3.5.

Elsewhere: [Two's complement](https://en.wikipedia.org/wiki/Two%27s%5Fcomplement), Wikipedia.

### Slice

A stretch of emulation that ends after a fixed number of instructions, after which the headless original's harness looks at the wall clock and goes on; where it ends changes nothing in the run.

First met and defined in [chapter 6](part-1/headless.md). The detail: [`re/notes/headless.md`](repo:re/notes/headless.md#unicorn-as-it-behaves-here), "Unicorn, as it behaves here".

### Small-data base

The register A4 in the game's code, holding `0x02AFFE`, 32,766 bytes into the data, from which every variable is reached by an offset of 16 bits.

First met and defined in [chapter 3](part-1/disk.md). The detail: [`SPEC.md`](repo:SPEC.md#32-executable), section 3.2.

### Sound sample

A recorded waveform that Paula plays back on one of its four channels, at its own pitch and volume.

First met and defined in [chapter 1](part-1/faithful.md). The detail: [`re/notes/sound.md`](repo:re/notes/sound.md).

Elsewhere: [Pulse-code modulation](https://en.wikipedia.org/wiki/Pulse-code%5Fmodulation), Wikipedia.

### Split line

The line of the playfield where the sky's palette gives way to the sea's, computed again in every pass; the copper changes the colours there.

First met and defined in [chapter 2](part-1/amiga.md). The detail: [`re/notes/display.md`](repo:re/notes/display.md#the-split-line), "The split line".

### Stack frame

A routine's own stretch of the stack, from its arguments down to its own variables, which `link a5` builds at the start of each compiled C routine of the game; A5 points into it, the first argument at `8(a5)`.

First met and defined in [chapter 3](part-1/disk.md). The detail: [`SPEC.md`](repo:SPEC.md#32-executable), section 3.2.

Elsewhere: [Call stack](https://en.wikipedia.org/wiki/Call%5Fstack), Wikipedia.

### Stand-in

A marked place in the port's C where the original has code the port does not carry; reaching it counts in the game's state, fails every comparison in a test build, and in the release build skips what it stands for.

First met and defined in [chapter 8](part-1/mission.md). The detail: [`SPEC.md`](repo:SPEC.md#74-working-method), section 7.4; [`re/notes/porting-m4.md`](repo:re/notes/porting-m4.md#what-stands-in-and-where), "What stands in, and where".

### Stub

A stand-in that answers for something a routine calls but that is not under test, such as a call into the operating system.

First met and defined in [chapter 5](part-1/oracle.md). The detail: [`tests/original.py`](repo:tests/original.py); [`re/notes/headless.md`](repo:re/notes/headless.md#the-stubs), "The stubs".

Elsewhere: [Test stub](https://en.wikipedia.org/wiki/Test%5Fstub), Wikipedia.

### Symbol

A name a program file keeps for a routine or a variable, with its address; the game's program keeps none, its music player twenty.

First met and defined in [chapter 3](part-1/disk.md). The detail: [`tools/hunk.py`](repo:tools/hunk.py); [`re/notes/music.md`](repo:re/notes/music.md#the-two-files), "The two files".

Elsewhere: [Symbol table](https://en.wikipedia.org/wiki/Symbol%5Ftable), Wikipedia.

### Topaz 8

The Amiga's standard font, eight pixels high, in the Kickstart ROM; the game's dialogs for names and files show it, and the port reads it from the ROM when it is built.

First met and defined in [chapter 2](part-1/amiga.md). The detail: [`re/notes/system-font.md`](repo:re/notes/system-font.md).

### VBlank

The vertical blank, the moment the beam has finished a picture and returns to the top: 50 times a second on a PAL Amiga, and the clock the game counts its time in.

First met in [chapter 1](part-1/faithful.md), defined in [chapter 2](part-1/amiga.md). The detail: [`re/notes/passes.md`](repo:re/notes/passes.md).

Elsewhere: [Vertical blanking interval](https://en.wikipedia.org/wiki/Vertical%5Fblanking%5Finterval), Wikipedia; [*Amiga Hardware Reference Manual*](https://archive.org/details/commodore-amiga-tech-ref-series-amiga-hardware-reference-manual-3rd-edition), 3rd edition, Internet Archive.

### VBlank server

A routine the operating system calls at every VBlank; the game installs two, the sound effects engine's and its own, which counts the VBlanks, takes the input samples into the input queue and scrolls the ticker.

First met and defined in [chapter 7](part-1/time.md). The detail: [`SPEC.md`](repo:SPEC.md#33-runtime-model), section 3.3; [`re/notes/headless.md`](repo:re/notes/headless.md#scheduling), "Scheduling".

Elsewhere: [*Amiga ROM Kernel Reference Manual: Exec*](https://archive.org/details/amiga-rom-kernel-reference-manual-exec), Internet Archive.

### Verified

The status of a routine that is ported and held to the original by a test of its own: under the oracle for a pure routine, by other tests for the rest. A routine held only by the comparisons of whole runs of the game is ported.

First met in [chapter 1](part-1/faithful.md), defined in [chapter 4](part-1/reading.md). The detail: [`SPEC.md`](repo:SPEC.md#74-working-method), section 7.4; [chapter 5](part-1/oracle.md).

### Vertical flip

The game's command that swaps the stick's forward and back, for players who want a pilot's stick; in the port a remembered preference.

First met and defined in [chapter 1](part-1/faithful.md). The detail: [`re/notes/keys.md`](repo:re/notes/keys.md#the-vertical-flip-and-how-long-it-lasts), "The vertical flip, and how long it lasts".

### Wait point

A place where the program waits, for the next picture, for a time or for the music's fade to end; the headless original lets VBlanks happen there and nowhere else.

First met and defined in [chapter 6](part-1/headless.md). The detail: [`re/notes/headless.md`](repo:re/notes/headless.md#scheduling), "Scheduling".

Elsewhere: [Busy waiting](https://en.wikipedia.org/wiki/Busy%5Fwaiting), Wikipedia.

### WebAssembly

A compact binary form of program that every current browser runs: the form the port's core is compiled to.

WebAssembly is a compact binary form of program with an instruction set of its own, which every current browser runs at close to native speed inside a sandbox: the program gets one block of memory to itself and reaches nothing of the page but what the page hands it. The port's core is its C compiled to WebAssembly; the build carries the bytes inside the HTML file, and the page instantiates them when it loads, with the JavaScript shell around them ([`SPEC.md`](repo:SPEC.md), sections [1](repo:SPEC.md#1-goal), [5](repo:SPEC.md#5-build) and [6.1](repo:SPEC.md#61-core)). It is not JavaScript: the two run side by side, and the shell calls the functions the core exports. The reference is [the WebAssembly specification](https://webassembly.github.io/spec/core/).

First met and defined in [chapter 1](part-1/faithful.md). The detail: [`SPEC.md`](repo:SPEC.md#5-build), section 5.

Elsewhere: [WebAssembly](https://en.wikipedia.org/wiki/WebAssembly), Wikipedia; [webassembly.org](https://webassembly.org/).

### Workbench

The Amiga's desktop, which the game closes when it starts.

First met in [chapter 1](part-1/faithful.md), defined in [chapter 2](part-1/amiga.md). The detail: [`SPEC.md`](repo:SPEC.md#34-operating-system-and-hardware-use), section 3.4.

Elsewhere: [Workbench (AmigaOS)](https://en.wikipedia.org/wiki/Workbench%5F(AmigaOS)), Wikipedia.
