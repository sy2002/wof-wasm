# The glossary

Every term the book introduces, in alphabetical order. An entry gives the term, its definition in one line, the chapter where you first meet it and the chapter that defines it, the note of the repository that holds the detail, and, where a good page exists, where to read more elsewhere.

### 3-D view

The window in the middle of the dashboard that shows, as from the cockpit, the sky, the sea and the map ahead of the aircraft, with a cursor for the horizon and the enemy aircraft ahead drawn in it.

First met and defined in [chapter 16](part-2/enemy.md). The detail: [`re/notes/porting-m4.md`](repo:re/notes/porting-m4.md#the-pass), "The pass"; [`re/notes/porting-m6.md`](repo:re/notes/porting-m6.md#the-pass-what-part-1-ports), "The pass: what part 1 ports".

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

### Absence (of the page)

A stretch of a second or more in which the page is hidden, behind another tab or window, which brings a mission back paused; a page hidden for a few milliseconds is none.

First met and defined in [chapter 23](part-3/shell.md). The detail: [`SPEC.md`](repo:SPEC.md#62-shell), section 6.2, "Pause"; [`re/notes/porting-m8.md`](repo:re/notes/porting-m8.md#the-page-and-the-fullscreen-finding), "The page and the fullscreen finding".

Elsewhere: [Page Visibility API](https://developer.mozilla.org/en-US/docs/Web/API/Page%5FVisibility%5FAPI), MDN.

### Accumulator

The shell clock's store of real time not yet turned into VBlanks: every animation frame adds the time since the last, every VBlank issued takes its share off, and the rest waits for the next animation frame.

First met and defined in [chapter 23](part-3/shell.md). The detail: [`web/clock.js`](repo:web/clock.js); [`SPEC.md`](repo:SPEC.md#62-shell), section 6.2, "Clock".

Elsewhere: [Fix Your Timestep!](https://gafferongames.com/post/fix%5Fyour%5Ftimestep/), Glenn Fiedler.

### ADF

An Amiga Disk File: a copy of an Amiga floppy, block by block, in one file, a double-density disk's 1,760 blocks of 512 bytes; the game's disk is [`original/wof.adf`](repo:original/wof.adf).

First met and defined in [chapter 3](part-1/disk.md). The detail: [`SPEC.md`](repo:SPEC.md), sections [2](repo:SPEC.md#2-repository) and [3.1](repo:SPEC.md#31-disk).

Elsewhere: [Amiga Disk File](https://en.wikipedia.org/wiki/Amiga%5FDisk%5FFile), Wikipedia; [Laurent Clévy's *ADF format FAQ*](https://web.archive.org/web/20241206200729/http://lclevy.free.fr/adflib/adf%5Finfo.html), the Wayback Machine's copy.

### Airfield

A runway on an island, marked by two records of the map, from which enemy fighters take off one at a time while the player is near; the map's table gives each its parked aircraft and the most fighters it lets up.

First met and defined in [chapter 16](part-2/enemy.md). The detail: [`re/notes/enemy.md`](repo:re/notes/enemy.md#what-launches-one), "What launches one", and ["The fifteen maps"](repo:re/notes/enemy.md#the-fifteen-maps).

### Airspeed

The number, from 0 to 1,400, that scales the player's aircraft's two speeds, in level flight hundredths of a pixel a tick: there is no throttle lever, the stick pushed the way the aircraft faces raises it, left alone in the air it falls to 1,000, and below 1,000 the aircraft sinks.

First met and defined in [chapter 14](part-2/player.md). The detail: [`re/notes/objects.md`](repo:re/notes/objects.md#the-players-record), "The player's record".

Elsewhere: [Airspeed](https://en.wikipedia.org/wiki/Airspeed), Wikipedia, the real quantity.

### Animation frame

One call the browser makes of a page's drawing routine just before it repaints, at the display's refresh rate, and none while the page is hidden; the shell's clock runs in them.

First met and defined in [chapter 23](part-3/shell.md). The detail: [`web/clock.js`](repo:web/clock.js).

Elsewhere: [Window: requestAnimationFrame() method](https://developer.mozilla.org/en-US/docs/Web/API/Window/requestAnimationFrame), MDN.

### Arena

The one block of memory, 3 MB, that the core reserves once and hands out zeroed in place of the system's allocator while the game loads: what lasts from the bottom, a file's scratch from the top, given back as one piece; nothing below is ever freed. What the original allocates for a mission the core keeps in its state instead.

First met and defined in [chapter 22](part-3/core.md). The detail: [`src/mem.c`](repo:src/mem.c); [`re/notes/porting-m1.md`](repo:re/notes/porting-m1.md#decisions-the-port-made), "Decisions the port made".

Elsewhere: [Region-based memory management](https://en.wikipedia.org/wiki/Region-based%5Fmemory%5Fmanagement), Wikipedia.

### Arithmetic shift

A shift of a number's bits that keeps its sign: shifted right, the sign bit is copied into the top, so that a negative number stays negative and is halved, rounded down; shifted left, it differs from a logical shift only in setting the overflow flag when the sign changes. The 68000's `asr` and `asl`.

First met and defined in [chapter 5](part-1/oracle.md). The detail: [`tools/m68k_fix.py`](repo:tools/m68k%5Ffix.py); [`SPEC.md`](repo:SPEC.md#71-arithmetic), section 7.1.

Elsewhere: [Arithmetic shift](https://en.wikipedia.org/wiki/Arithmetic%5Fshift), Wikipedia; [*M68000 Family Programmer's Reference Manual*](https://archive.org/details/m68000familyprog0000unse), Internet Archive.

### Arresting cable

One of the four cables across the carrier's deck that stop the player's aircraft when its tailhook, 24 pixels behind it, passes within 8 pixels of one at an airspeed of 600 or more with the deck's flag clear, that is, with the stick held forward after the touch-down.

First met and defined in [chapter 14](part-2/player.md). The detail: [`re/notes/porting-m4.md`](repo:re/notes/porting-m4.md#landing-refuelling-rearming), "Landing, refuelling, rearming".

Elsewhere: [Arresting gear](https://en.wikipedia.org/wiki/Arresting%5Fgear), Wikipedia.

### Assembly language

The written form of machine code, one instruction a line, a short name for the operation followed by its operands: the form in which the listing shows the whole program, and in which much of the game was written by hand.

First met in [chapter 1](part-1/faithful.md), defined in [chapter 2](part-1/amiga.md). The detail: [`SPEC.md`](repo:SPEC.md#32-executable), section 3.2.

Elsewhere: [Assembly language](https://en.wikipedia.org/wiki/Assembly%5Flanguage), Wikipedia.

### Attitude

The stage of a turn of the player's aircraft, the notes' name for it, 0 in straight flight and 1 to 25 while it turns, one stage every second tick in a turn: it picks the turn's frame and a factor for the horizontal speed, and at 14 the aircraft's facing changes. An enemy aircraft's turn steps it every third tick (chapter 16).

First met and defined in [chapter 14](part-2/player.md). The detail: [`src/player.c`](repo:src/player.c), the routine at `0x01AB80`; [`re/notes/ffp.md`](repo:re/notes/ffp.md#the-two-tables-of-constants), "The two tables of constants".

### Attract demo

A recorded game that the program plays by itself when left alone at the rank selection, and which it can record from a game played; not a demoscene production.

First met and defined in [chapter 1](part-1/faithful.md). The detail: [`re/notes/demo.md`](repo:re/notes/demo.md).

Elsewhere: [Attract mode](https://en.wikipedia.org/wiki/Attract%5Fmode), Wikipedia.

### Audio frame

One instant of the mixed sound, a value for the left and one for the right; the core hands out as many as the emulated time lasts at the rate the shell asks for.

First met and defined in [chapter 23](part-3/shell.md). The detail: [`web/audio.js`](repo:web/audio.js); [`SPEC.md`](repo:SPEC.md#61-core), section 6.1.

### Audio worklet

A small program the browser runs on its audio thread, a second line of work beside the page's; the shell's plays the blocks of audio frames the page posts and reports how much it has played.

First met and defined in [chapter 23](part-3/shell.md). The detail: [`web/worklet.js`](repo:web/worklet.js); [`web/audio.js`](repo:web/audio.js).

Elsewhere: [AudioWorklet](https://developer.mozilla.org/en-US/docs/Web/API/AudioWorklet), MDN.

### Autopilot

A program that flies the headless original by a policy, looking at the game's state every VBlank and choosing the stick, the button and the keys; its choices, compressed into segments of VBlanks, become a mission script, which the original then flies the same way without it.

First met and defined in [chapter 8](part-1/mission.md). The detail: [`tools/m4_autopilot.py`](repo:tools/m4%5Fautopilot.py); [`re/notes/porting-m4.md`](repo:re/notes/porting-m4.md#the-scripts-of-part-2), "The scripts of part 2".

### Band

In the port, a run of consecutive output rows of one viewport that share a set of colours: what the copper builder does that can be seen, handed from the views to the picture, two bands with the same colours sharing a palette.

First met and defined in [chapter 11](part-2/display.md). The detail: [`src/video.c`](repo:src/video.c), [`src/screen.c`](repo:src/screen.c); [`re/notes/porting-m3.md`](repo:re/notes/porting-m3.md#views-viewports-and-what-reaches-the-output), "Views, viewports and what reaches the output".

### Barracks

A target of an island, slot 4, that holds soldiers, five at the start, and burns when a weapon hits it, its four map records turned into the burnt barracks.

First met and defined in [chapter 15](part-2/weapons.md). The detail: [`re/notes/porting-m5.md`](repo:re/notes/porting-m5.md#three-kinds-of-target), "Three kinds of target".

Elsewhere: [Barracks](https://en.wikipedia.org/wiki/Barracks), Wikipedia.

### Beam

The point where the display is drawing the picture, sweeping each line from left to right and the lines from top to bottom; its position, which a register of the custom chips reports, is the game's only source of chance.

First met in [chapter 1](part-1/faithful.md), defined in [chapter 2](part-1/amiga.md). The detail: [`re/notes/random.md`](repo:re/notes/random.md).

Elsewhere: [Raster scan](https://en.wikipedia.org/wiki/Raster%5Fscan), Wikipedia.

### Bearing

The aircraft's pitch converted each tick to an angle of `0x800` steps a turn, for whatever the aircraft shoots or drops next: a rocket's thrust and frame, and where the guns reach the ground.

First met and defined in [chapter 15](part-2/weapons.md). The detail: [`src/tick.c`](repo:src/tick.c), `shot_origin`; [`re/notes/porting-m5.md`](repo:re/notes/porting-m5.md#the-tick-the-drop), "The tick: the drop".

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

### Branch (version control)

A line of commits kept apart from the repository's main line, so that a worker's changes stay separate until the controller merges them, folding the branch's commits into the main line.

First met and defined in [chapter 10](part-1/making.md). The detail: [`CONTROLLER.md`](repo:CONTROLLER.md#driving-workers), "Driving workers"; [`CLAUDE.md`](repo:CLAUDE.md#rules), "Rules".

Elsewhere: [Branching (version control)](https://en.wikipedia.org/wiki/Branching%5F(version%5Fcontrol)), Wikipedia.

### Brief

The controller's short account to the owner: where things stand, in a few lines, then every open ask in full, each with its context and a recommendation.

First met and defined in [chapter 10](part-1/making.md). The detail: [`CONTROLLER.md`](repo:CONTROLLER.md#the-users-conventions), "The user's conventions".

### Briefing

The screen before every mission that shows the rank's name, the mission number and the mission's two counts, for 240 rounds or until fire; Control-R goes back to the rank selection.

First met and defined in [chapter 19](part-2/front-end.md). The detail: [`re/notes/frontend.md`](repo:re/notes/frontend.md#screen-by-screen), "Screen by screen"; [`src/front.c`](repo:src/front.c).

### BSS

A hunk of memory that starts at zero and is given in the program's file by its size alone; the game's is 4 bytes at `0x028000`.

First met and defined in [chapter 3](part-1/disk.md). The detail: [`SPEC.md`](repo:SPEC.md#32-executable), section 3.2.

Elsewhere: [.bss](https://en.wikipedia.org/wiki/.bss), Wikipedia.

### ByteRun1

The packing of a picture's rows in IFF ILBM: a control byte says either copy the next bytes as they are or repeat the next byte; the game's reader assumes it, and every picture the game shows uses it.

First met and defined in [chapter 11](part-2/display.md). The detail: [`src/iff.c`](repo:src/iff.c); [`re/notes/display.md`](repo:re/notes/display.md#how-pictures-reach-a-viewport), "How pictures reach a viewport".

Elsewhere: [PackBits](https://en.wikipedia.org/wiki/PackBits), Wikipedia; [ILBM](https://en.wikipedia.org/wiki/ILBM), Wikipedia.

### Callback

A routine handed to another routine, which calls it back; the saved game's walker calls the writer's or the reader's callback once for each piece of the file.

First met and defined in [chapter 17](part-2/campaign.md). The detail: [`re/notes/campaign.md`](repo:re/notes/campaign.md#the-layout), "The layout".

Elsewhere: [Callback (computer programming)](https://en.wikipedia.org/wiki/Callback%5F(computer%5Fprogramming)), Wikipedia.

### Calling convention

The rules by which a caller hands a routine its arguments and gets the result back: in the game's compiled C the arguments go onto the stack, 2 bytes for an int and 4 for a long or a pointer, and the result comes back in D0.

First met and defined in [chapter 3](part-1/disk.md). The detail: [`SPEC.md`](repo:SPEC.md#32-executable), section 3.2.

Elsewhere: [Calling convention](https://en.wikipedia.org/wiki/Calling%5Fconvention), Wikipedia; [*M68000 Family Programmer's Reference Manual*](https://archive.org/details/m68000familyprog0000unse), Internet Archive.

### Campaign

The run of missions from the rank chosen at the rank selection to the game's end, through the maps from that rank's first on, in a fixed order by rank and mission number; it has no last mission.

First met and defined in [chapter 17](part-2/campaign.md). The detail: [`re/notes/campaign.md`](repo:re/notes/campaign.md#the-order-of-the-maps), "The order of the maps", and ["The rank's cap, and no end"](repo:re/notes/campaign.md#the-ranks-cap-and-no-end).

### Change report

A list a run of the headless original can write: for every record of its dump, each range of memory that changed, with the old and the new bytes, a name and the routines that wrote it.

First met and defined in [chapter 6](part-1/headless.md). The detail: [`re/notes/headless.md`](repo:re/notes/headless.md#change-report-entropy-log-schedule), "Change report, entropy log, schedule".

### Channel record

One of the sound effects engine's four records of `0x1E` bytes, one for each of Paula's channels, holding what the channel was last asked to play, when it last stopped and the count of cycles the handler takes down.

First met and defined in [chapter 18](part-2/sound.md). The detail: [`re/notes/sound.md`](repo:re/notes/sound.md#the-channel-layer), "The channel layer".

### Chip memory

The memory the Amiga's custom chips can read and write by themselves, without the processor; the game keeps its screens, copper lists, shapes, sound effects and songs there.

First met and defined in [chapter 2](part-1/amiga.md). The detail: [`re/notes/display.md`](repo:re/notes/display.md#memory), "Memory".

Elsewhere: [Amiga Chip RAM](https://en.wikipedia.org/wiki/Amiga%5FChip%5FRAM), Wikipedia; [*Amiga Hardware Reference Manual*](https://archive.org/details/commodore-amiga-tech-ref-series-amiga-hardware-reference-manual-3rd-edition), 3rd edition, Internet Archive.

### CIA

One of the Amiga's two interface chips, which serve its ports and carry timers of their own; the game reads the fire button from one, and its music player takes one of their timers for its beat.

First met and defined in [chapter 2](part-1/amiga.md). The detail: [`re/notes/music.md`](repo:re/notes/music.md#the-timer), "The timer".

Elsewhere: [MOS Technology CIA](https://en.wikipedia.org/wiki/MOS%5FTechnology%5FCIA), Wikipedia.

### Clear and set bytes

Two bytes of a shape's header naming the screen's planes that every draw sets to 0 and to 1 under the shape's mask; with them a shape storing fewer planes than the screen has lands in colours that do not depend on what lies beneath, which holds for every shape on the disk.

First met and defined in [chapter 12](part-2/shapes.md). The detail: [`re/notes/shapes.md`](repo:re/notes/shapes.md#record-header-complete), "Record header, complete"; [`re/notes/drawing.md`](repo:re/notes/drawing.md#what-shape%5Fdraw-does-exactly), "What `shape_draw` does, exactly".

### Clip rectangle

The rectangle of the screen a draw may change, its left and right edges rounded down to multiples of 16; the blit writes the pixels of a shape's box that lie inside it, and no others.

First met and defined in [chapter 12](part-2/shapes.md). The detail: [`re/notes/drawing.md`](repo:re/notes/drawing.md#the-blitter-library), "The blitter library"; [`re/notes/porting-m1.md`](repo:re/notes/porting-m1.md#the-blit-is-per-pixel-and-why), "The blit is per-pixel, and why".

Elsewhere: [Clipping (computer graphics)](https://en.wikipedia.org/wiki/Clipping%5F(computer%5Fgraphics)), Wikipedia.

### Closed loop

The comparison in which the port runs on its own from the program's start, given nothing but the entropy seed and the map list's addresses, which the open loop gets too, and is compared with the original after every pass and every tick, so that every error it carries over shows.

First met and defined in [chapter 8](part-1/mission.md). The detail: [`tests/m4compare.py`](repo:tests/m4compare.py); [`SPEC.md`](repo:SPEC.md#8-verification), section 8, "Mission, pass by pass".

### Cold region

A stretch of a ported routine's instructions that no run of the mission scripts executed; each must be covered by a stand-in's marker or by a note saying what it is.

First met and defined in [chapter 8](part-1/mission.md). The detail: [`tools/reach_observe.py`](repo:tools/reach%5Fobserve.py); [`re/notes/porting-m4.md`](repo:re/notes/porting-m4.md#appendix-the-regions-no-run-executed), "Appendix: the regions no run executed".

Elsewhere: [Code coverage](https://en.wikipedia.org/wiki/Code%5Fcoverage), Wikipedia.

### Colour clock

The clock the Amiga's custom chips run on, 3,546,895 cycles a second on a PAL machine: half the processor's clock, and the unit of Paula's period.

First met and defined in [chapter 2](part-1/amiga.md). The detail: [`re/notes/sound.md`](repo:re/notes/sound.md#the-slots-and-what-they-play), "The slots and what they play".

Elsewhere: [*Amiga Hardware Reference Manual*](https://archive.org/details/commodore-amiga-tech-ref-series-amiga-hardware-reference-manual-3rd-edition), 3rd edition, Internet Archive.

### Colour table

A viewport's 32 colours, 12 bits each, which the copper builder turns into writes to the colour registers; the playfield has two, the sky's and the sea's.

First met and defined in [chapter 11](part-2/display.md). The detail: [`re/notes/display.md`](repo:re/notes/display.md#records), "Records".

### Commit (version control)

A set of changes recorded in the repository's history, with a message saying what they are; every commit of this project carries the owner as its author.

First met and defined in [chapter 10](part-1/making.md). The detail: [`CLAUDE.md`](repo:CLAUDE.md#session-protocol), "Session protocol".

Elsewhere: [Commit (version control)](https://en.wikipedia.org/wiki/Commit%5F(version%5Fcontrol)), Wikipedia.

### Completeness list

The list that sorts every address the original writes during a mission into a registered field of the port, state compared in another form, or state the port does not keep, with its reason and the milestone that owes it; each row names the routines that write it.

First met and defined in [chapter 8](part-1/mission.md). The detail: [`tests/m4complete.py`](repo:tests/m4complete.py); [`re/notes/porting-m4.md`](repo:re/notes/porting-m4.md#the-completeness-list), "The completeness list".

### Condition codes

The five bits X, N, Z, V and C that the 68000 sets after most instructions, saying whether the result was negative, zero or too large for its width and whether a carry came out; a conditional branch reads them.

They sit in the low byte of the status register. The emulator the tests run on works them out only when an instruction needs them, so the oracle reads them through an instruction of the 68000's own ([`re/notes/headless.md`](repo:re/notes/headless.md#unicorn-as-it-behaves-here), "Unicorn, as it behaves here").

First met and defined in [chapter 5](part-1/oracle.md). The detail: [`tools/oracle.py`](repo:tools/oracle.py); [`re/notes/ffp.md`](repo:re/notes/ffp.md#how-the-game-reaches-it), "How the game reaches it".

Elsewhere: [Status register](https://en.wikipedia.org/wiki/Status%5Fregister), Wikipedia; [*M68000 Family Programmer's Reference Manual*](https://archive.org/details/m68000familyprog0000unse), Internet Archive.

### Contact sheet

A picture of every shape of a container with its name above it, in the day palette, made by [`tools/ppkc.py`](repo:tools/ppkc.py); seven are the pictures of the containers kept in the repository.

First met and defined in [chapter 12](part-2/shapes.md). The detail: [`tools/ppkc.py`](repo:tools/ppkc.py); [`ref/sheets/`](repo:ref/sheets/).

Elsewhere: [Contact print](https://en.wikipedia.org/wiki/Contact%5Fprint), Wikipedia, the photographer's sheet the name comes from.

### Control

A deliberate change of the port in one place, made to see that the test meant to catch it fails, and where; or a change that must leave the comparison's result as it is, such as another number of VBlanks a pass.

First met and defined in [chapter 8](part-1/mission.md). The detail: [`re/notes/porting-m4.md`](repo:re/notes/porting-m4.md#how-the-port-is-held-to-the-original), "How the port is held to the original"; [`tools/m7_controls.py`](repo:tools/m7%5Fcontrols.py).

Elsewhere: [Mutation testing](https://en.wikipedia.org/wiki/Mutation%5Ftesting), Wikipedia.

### Control flow

The order in which a program's instructions run, set by its branches, jumps, calls and returns; the disassembler follows it to tell the code from the data among it.

First met and defined in [chapter 4](part-1/reading.md). The detail: [`tools/disasm.py`](repo:tools/disasm.py).

Elsewhere: [Control flow](https://en.wikipedia.org/wiki/Control%5Fflow), Wikipedia.

### Control-flow skeleton

A routine shown with only its labels, calls, branches, comparisons and returns, as [`tools/skel.py`](repo:tools/skel.py) prints it from the listing: the first step of porting a routine, before it is read in full.

First met and defined in [chapter 4](part-1/reading.md). The detail: [`SPEC.md`](repo:SPEC.md#74-working-method), section 7.4.

### Controller

The session that leads the work: the owner talks to it alone; it sends the workers their tasks, reviews and merges what they deliver, keeps the specification and the rules true, and is the only session that asks the owner for anything.

First met and defined in [chapter 10](part-1/making.md). The detail: [`CONTROLLER.md`](repo:CONTROLLER.md#the-arrangement), "The arrangement".

### Copper

The Amiga's display coprocessor: it follows a list of waits and register writes in step with the beam, and so changes colours and screen modes part of the way down the picture.

First met in [chapter 1](part-1/faithful.md), defined in [chapter 2](part-1/amiga.md). The detail: [`re/notes/display.md`](repo:re/notes/display.md).

Elsewhere: [Original Chip Set](https://en.wikipedia.org/wiki/Original%5FChip%5FSet), Wikipedia; [*Amiga Hardware Reference Manual*](https://archive.org/details/commodore-amiga-tech-ref-series-amiga-hardware-reference-manual-3rd-edition), 3rd edition, Internet Archive.

### Copper list

The list of waits and register writes the copper follows through a frame; the game builds one for each of its two views, and a spare, in buffers of its own.

First met and defined in [chapter 11](part-2/display.md). The detail: [`re/notes/display.md`](repo:re/notes/display.md#the-copper-builder), "The copper builder".

Elsewhere: [*Amiga Hardware Reference Manual*](https://archive.org/details/commodore-amiga-tech-ref-series-amiga-hardware-reference-manual-3rd-edition), 3rd edition, Internet Archive.

### Core

The port's game: the ported logic, written in C and compiled to WebAssembly, which knows nothing of the browser around it.

First met and defined in [chapter 1](part-1/faithful.md). The detail: [`SPEC.md`](repo:SPEC.md#61-core), section 6.1.

### Coroutine

A routine that can stop at a wait, give control back and go on from there at its next call: the port's form of every routine of the original that waits, since a page may not block.

The port's are stackless, in the style of protothreads: the routine's body sits inside a `switch` on its resume point, the locals it keeps across a wait live in the front end's part of the core's state, beside the routine's context, and one wait is one VBlank ([`SPEC.md`](repo:SPEC.md#63-blocking-code-becomes-coroutines), section 6.3).

First met and defined in [chapter 22](part-3/core.md). The detail: [`src/coro.h`](repo:src/coro.h); [`re/notes/porting-m3.md`](repo:re/notes/porting-m3.md#the-front-end-as-coroutines), "The front end as coroutines".

Elsewhere: [Coroutine](https://en.wikipedia.org/wiki/Coroutine), Wikipedia; [Protothread](https://en.wikipedia.org/wiki/Protothread), Wikipedia.

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

### Cycle

One play of a channel's sound sample by Paula, from its address to the end of its length, after which the channel raises its interrupt request, takes the address and the length again and plays on.

First met and defined in [chapter 18](part-2/sound.md). The detail: [`re/notes/headless.md`](repo:re/notes/headless.md#the-audio-channels), "The audio channels".

### Dashboard

The play screen's middle area, 640 by 37 in high resolution with four bitplanes: the instruments and the 3-D window, drawn by day and by night from pictures and shapes of their own.

First met and defined in [chapter 11](part-2/display.md). The detail: [`re/notes/porting-m4.md`](repo:re/notes/porting-m4.md#the-pass), "The pass"; [`src/dash.c`](repo:src/dash.c).

### Deliberate divergence

A change of the original's behaviour that the port makes on purpose, by a decision of the project's owner written in the specification, as against a quirk of the original, which the port keeps, and a mistake of the port, which is put right.

First met and defined in [chapter 20](part-2/quirks.md). The detail: [`SPEC.md`](repo:SPEC.md), sections [1, "Out of scope"](repo:SPEC.md#out-of-scope-for-this-specification) and [6.2](repo:SPEC.md#62-shell).

### Depth

The number of a picture's bitplanes, which gives it 2 to that number colours: five for the playfield's 32, four for the dashboard's 16, one for the ticker's two.

First met and defined in [chapter 11](part-2/display.md). The detail: [`re/notes/display.md`](repo:re/notes/display.md#screens), "Screens".

Elsewhere: [Color depth](https://en.wikipedia.org/wiki/Color%5Fdepth), Wikipedia.

### Device pixel

One of the screen's own pixels, as against a CSS pixel, the page's unit of layout, which a Retina screen draws two device pixels wide; the shell lays out the picture's box in whole device pixels.

First met and defined in [chapter 23](part-3/shell.md). The detail: [`web/video.js`](repo:web/video.js); [`re/notes/page-video.md`](repo:re/notes/page-video.md#the-machine-and-the-displays-refresh), "The machine and the display's refresh".

Elsewhere: [Window: devicePixelRatio property](https://developer.mozilla.org/en-US/docs/Web/API/Window/devicePixelRatio), MDN.

### Diagnostics overlay

The shell's panel of figures over the picture, opened by the key left of 1, which shows what the page is doing and offers the development keys; not the game's, and not the overlay of the file system.

First met and defined in [chapter 23](part-3/shell.md). The detail: [`web/overlay.js`](repo:web/overlay.js); [`web/main.js`](repo:web/main.js).

### Differential test

A test that hands two implementations of the same thing the same input and demands the same output; the oracle's tests run the original's routine and its port so.

First met and defined in [chapter 5](part-1/oracle.md). The detail: [`SPEC.md`](repo:SPEC.md#74-working-method), section 7.4; [`tests/test_oracle_m1.py`](repo:tests/test%5Foracle%5Fm1.py).

Elsewhere: [Differential testing](https://en.wikipedia.org/wiki/Differential%5Ftesting), Wikipedia.

### Disassembler

A tool that turns machine code back into assembly language; the project's, [`tools/disasm.py`](repo:tools/disasm.py), follows the program's control flow and writes the listing and the routine inventory.

First met and defined in [chapter 4](part-1/reading.md). The detail: [`SPEC.md`](repo:SPEC.md#4-tools), section 4.

Elsewhere: [Disassembler](https://en.wikipedia.org/wiki/Disassembler), Wikipedia.

### Display line

A line of the picture counted from its top, as the game's records count them; display line 0 is beam line 44.

First met and defined in [chapter 11](part-2/display.md). The detail: [`re/notes/display.md`](repo:re/notes/display.md#the-play-screen-line-by-line), "The play screen line by line".

### Double buffering

Drawing into a hidden picture and showing it only when it is whole; the game keeps two screens, each with its own copper list, and swaps them with one register write.

First met and defined in [chapter 2](part-1/amiga.md). The detail: [`re/notes/display.md`](repo:re/notes/display.md#double-buffering-and-the-swap), "Double buffering and the swap".

Elsewhere: [Multiple buffering](https://en.wikipedia.org/wiki/Multiple%5Fbuffering), Wikipedia.

### Draw flag

Bit 15 of a map record: only a record that carries it draws its shape, so that a shape wider than eight pixels, whose slot all its records carry, is drawn once.

First met and defined in [chapter 13](part-2/world.md). The detail: [`re/notes/map.md`](repo:re/notes/map.md#the-record), "The record".

### Dug-out

A target of an island, slot 3, that holds soldiers, five at the start, and fires at the aircraft while it holds any; a hit lets its soldiers out but does not destroy it.

First met and defined in [chapter 15](part-2/weapons.md). The detail: [`re/notes/porting-m5.md`](repo:re/notes/porting-m5.md#three-kinds-of-target), "Three kinds of target".

### Dump

The file a run of the headless original writes: the game's whole state when a mission is set up and after every logic tick and every pass, each record with a SHA-256 fingerprint of the state, for the comparisons with the port.

First met and defined in [chapter 6](part-1/headless.md). The detail: [`tools/headless_dump.py`](repo:tools/headless%5Fdump.py); [`re/notes/headless.md`](repo:re/notes/headless.md#dump), "Dump".

### E clock

The clock the Amiga's CIAs count at, the colour clock divided by five: 709,379 counts a second on a PAL machine; the music's timer counts down at it.

First met and defined in [chapter 18](part-2/sound.md). The detail: [`re/notes/music.md`](repo:re/notes/music.md#the-timer), "The timer".

Elsewhere: [*Amiga Hardware Reference Manual*](https://archive.org/details/commodore-amiga-tech-ref-series-amiga-hardware-reference-manual-3rd-edition), 3rd edition, Internet Archive.

### Eighth-scale view

The zoomed-out picture the game switches to while the aircraft is high, "view" in the everyday sense and not the record: eight pixels of the world to one of the screen, the shapes taken from a container of their own.

First met and defined in [chapter 11](part-2/display.md). The detail: [`re/notes/map.md`](repo:re/notes/map.md#world-coordinates), "World coordinates"; [`re/notes/shapes.md`](repo:re/notes/shapes.md#masterlist-and-athlist), "MasterList and AthList".

### Emulated time

The game's own time, counted in the VBlanks the shell issues, as against the display's time, which the animation frames keep.

First met and defined in [chapter 23](part-3/shell.md). The detail: [`web/clock.js`](repo:web/clock.js); [`SPEC.md`](repo:SPEC.md#62-shell), section 6.2, "Clock".

### Emulator

A program that imitates a computer's processor and chips closely enough that the computer's own programs run on it unchanged.

First met and defined in [chapter 1](part-1/faithful.md). The detail: [`README.md`](repo:README.md#amiga-to-web), "Amiga to Web".

Elsewhere: [Emulator](https://en.wikipedia.org/wiki/Emulator), Wikipedia.

### Enemy aircraft record

One of four records of 52 bytes in which an enemy fighter or torpedo plane flies: its state word says free, flying, shot down and falling, or burning on land, and its mode, relation and order what it does and where it is against the player.

First met and defined in [chapter 16](part-2/enemy.md). The detail: [`re/notes/enemy.md`](repo:re/notes/enemy.md#the-record), "The record".

### Enemy plane counter

The dashboard's count of the enemy aircraft shot down: two digits, at most 99, and a kill icon for each plane, seven to a row in two rows.

First met and defined in [chapter 16](part-2/enemy.md). The detail: [`re/notes/porting-m6.md`](repo:re/notes/porting-m6.md#the-pass-what-part-1-ports), "The pass: what part 1 ports".

### Enemy's countdown

The field of the player's record that counts the ticks to the next torpedo plane: 1,350 for each new aircraft, held back by the fire button, and 500 again after each torpedo dropped.

First met and defined in [chapter 16](part-2/enemy.md). The detail: [`re/notes/enemy.md`](repo:re/notes/enemy.md#what-launches-one), "What launches one".

### Entropy stream

The reproducible stream of values that stands in for the beam's position, one value for every read; the headless original and the port draw from the same one, so that both meet the same chance.

First met and defined in [chapter 6](part-1/headless.md). The detail: [`re/notes/random.md`](repo:re/notes/random.md#consequences), "Consequences"; [`re/notes/headless.md`](repo:re/notes/headless.md#entropy), "Entropy".

Elsewhere: [Linear congruential generator](https://en.wikipedia.org/wiki/Linear%5Fcongruential%5Fgenerator), Wikipedia.

### Event log

The log of every sound sample started and of every restart at a cycle's end, with its channel, period, volume and instant, which the headless original and the port keep alike and the tests compare; chapter 1 calls it the sound event log.

First met and defined in [chapter 18](part-2/sound.md). The detail: [`re/notes/headless.md`](repo:re/notes/headless.md#the-audio-channels), "The audio channels".

### Fade

Sixteen steps that carry a colour table to another, most often from black or to black, the copper list built again at each; the arithmetic of a step carries from one colour component into the next.

First met and defined in [chapter 11](part-2/display.md). The detail: [`re/notes/display.md`](repo:re/notes/display.md#fades), "Fades"; [`src/fade.c`](repo:src/fade.c).

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

### Fighter

An enemy aircraft that hunts the player's: sent up by an airfield or a ship, it closes from behind, gets on his tail and fires.

First met and defined in [chapter 16](part-2/enemy.md). The detail: [`re/notes/enemy.md`](repo:re/notes/enemy.md#what-each-state-and-mode-does-read-and-held-by-the-oracle-and-the-closed-loop), "What each state and mode does".

Elsewhere: [Fighter aircraft](https://en.wikipedia.org/wiki/Fighter%5Faircraft), Wikipedia, the real kind.

### Fixed load layout

The one set of addresses at which all the project's tools load the game's program: the code at `0x010000`, the data at `0x023000`, the BSS at `0x028000`, A4 holding `0x02AFFE`. Every address of the program in this book is one of it; the running port holds offsets instead.

First met and defined in [chapter 3](part-1/disk.md). The detail: [`SPEC.md`](repo:SPEC.md#32-executable), section 3.2; [`tools/hunk.py`](repo:tools/hunk.py).

### Fixture

A function the test framework runs before a test, to set up what the test needs; the port's suite has one that resets the shared core before every test that uses it and puts back the settings a test with a core of its own needs.

First met and defined in [chapter 9](part-1/wrong.md). The detail: [`tests/conftest.py`](repo:tests/conftest.py); [`re/notes/testing.md`](repo:re/notes/testing.md#a-fresh-core-for-every-test), "A fresh core for every test".

Elsewhere: [Test fixture](https://en.wikipedia.org/wiki/Test%5Ffixture), Wikipedia.

### FPGA recreation

A computer rebuilt in programmable hardware, a chip whose circuits are configured to behave like the original machine's.

First met and defined in [chapter 1](part-1/faithful.md). The detail: [`README.md`](repo:README.md#amiga-to-web), "Amiga to Web".

Elsewhere: [Field-programmable gate array](https://en.wikipedia.org/wiki/Field-programmable%5Fgate%5Farray), Wikipedia.

### Fragment shader

The small program the graphics processor runs once for every pixel it draws, to give it its colour; the shell's works out both steps of its two-step scaling at once.

First met and defined in [chapter 23](part-3/shell.md). The detail: [`web/video.js`](repo:web/video.js); [`re/notes/page-video.md`](repo:re/notes/page-video.md#the-webgl-path), "The WebGL path".

Elsewhere: [Shader](https://en.wikipedia.org/wiki/Shader), Wikipedia.

### Freestanding

C with no operating system beneath it and only the part of the standard library that needs none: no allocator, no files, no clock. The core is written so, for the page and for the native library alike.

First met and defined in [chapter 22](part-3/core.md). The detail: [`SPEC.md`](repo:SPEC.md#61-core), section 6.1; [`src/wof.h`](repo:src/wof.h).

Elsewhere: [Conformance](https://en.cppreference.com/w/c/language/conformance), cppreference, on hosted and freestanding implementations.

### Front end

The game's screens before and between missions, from the story scroller and the title sequence to the rank selection, the briefing, the dialogs and the high-score screen, and the outer loop that joins them.

First met in [chapter 3](part-1/disk.md), defined in [chapter 19](part-2/front-end.md). The detail: [`re/notes/frontend.md`](repo:re/notes/frontend.md#the-timetable-left-alone), "The timetable, left alone"; [`re/notes/porting-m3.md`](repo:re/notes/porting-m3.md#the-front-end-as-coroutines), "The front end as coroutines".

### Game over

The end of a game, when the last Hellcat is lost or the carrier has sunk; the high scores follow, unless a demo was played, and then the rank selection.

First met and defined in [chapter 17](part-2/campaign.md). The detail: [`re/notes/porting-m4.md`](repo:re/notes/porting-m4.md#what-ends-a-mission), "What ends a mission"; [`re/notes/frontend.md`](repo:re/notes/frontend.md#the-outer-loop-as-a-state-diagram), "The outer loop, as a state diagram".

Elsewhere: [Game over](https://en.wikipedia.org/wiki/Game%5Fover), Wikipedia.

### Generated file

A file of the repository that a tool makes from others, committed so that a reader sees it without running the tool, and held byte for byte to what the tool makes again: the listing, the routine inventory, the contact sheets and this book's listings and figures among them.

First met and defined in [chapter 21](part-3/repository.md). The detail: [`tests/test_generated.py`](repo:tests/test%5Fgenerated.py); [`book/tools/build.py`](repo:book/tools/build.py); [`CLAUDE.md`](repo:CLAUDE.md#rules), "Rules".

### Ground height

How high what stands at a map record reaches, which a tick asks for under an object: a class's height less the record's height field, a ship's deck from the ship's record, or zero; in flight without weapons, the one thing the tick reads from the map.

First met and defined in [chapter 13](part-2/world.md). The detail: [`re/notes/map.md`](repo:re/notes/map.md#the-ground-height), "The ground height".

### Handover

The lead passed from a controller whose context is filling to a fresh session, at a quiet point, through the repository and a message saying where things stand.

First met and defined in [chapter 10](part-1/making.md). The detail: [`CONTROLLER.md`](repo:CONTROLLER.md#the-arrangement), "The arrangement"; [`CLAUDE.md`](repo:CLAUDE.md#session-protocol), "Session protocol".

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

### High resolution

The Amiga's mode of 640 pixels across a line, each half as wide as a low-resolution pixel; the dashboard and the ticker use it.

First met and defined in [chapter 11](part-2/display.md). The detail: [`re/notes/display.md`](repo:re/notes/display.md#screens), "Screens".

Elsewhere: [*Amiga Hardware Reference Manual*](https://archive.org/details/commodore-amiga-tech-ref-series-amiga-hardware-reference-manual-3rd-edition), 3rd edition, Internet Archive.

### High-score file

The file `highscore`, 360 bytes: ten rows of 36, each a score, the rank reached and a name, best first, read and written by the high-score screen at a game's end.

First met and defined in [chapter 17](part-2/campaign.md). The detail: [`re/notes/highscore.md`](repo:re/notes/highscore.md).

Elsewhere: [Score (video games)](https://en.wikipedia.org/wiki/Score%5F(video%5Fgames)), Wikipedia.

### High-score screen

The screen at a game's end that shows the ten rows of the high-score file in the game's font, outlined in black, behind the music's song 0.

First met and defined in [chapter 19](part-2/front-end.md). The detail: [`re/notes/frontend.md`](repo:re/notes/frontend.md#screen-by-screen), "Screen by screen"; [`src/hiscore.c`](repo:src/hiscore.c).

### Hit count

The word of the player's record that the targets' fire and the enemy fighters count down: when it runs out, the oil falls and the fuel with it, and a new count is drawn.

First met and defined in [chapter 16](part-2/enemy.md). The detail: [`re/notes/porting-m5.md`](repo:re/notes/porting-m5.md#the-targets-fire), "The targets' fire"; [`re/notes/enemy.md`](repo:re/notes/enemy.md#what-each-state-and-mode-does-read-and-held-by-the-oracle-and-the-closed-loop), "What each state and mode does".

### Hold

The carrier's hold, below its deck, where the lift takes the player's aircraft to be refuelled, repaired and rearmed, and where the weapon menu is shown.

First met and defined in [chapter 14](part-2/player.md). The detail: [`re/notes/porting-m4.md`](repo:re/notes/porting-m4.md#landing-refuelling-rearming), "Landing, refuelling, rearming".

### Hook

A routine of the instrument's own that the emulator calls whenever the program reaches a chosen instruction or touches chosen memory; the oracle corrects the emulator with hooks, and the headless original watches the game through them.

First met and defined in [chapter 5](part-1/oracle.md). The detail: [`tools/m68k_fix.py`](repo:tools/m68k%5Ffix.py); [`re/notes/headless.md`](repo:re/notes/headless.md#unicorn-as-it-behaves-here), "Unicorn, as it behaves here".

Elsewhere: [Hooking](https://en.wikipedia.org/wiki/Hooking), Wikipedia.

### Hotspot

The point of a shape, counted from its top left corner, that lands on the position the shape is drawn at; the routines that draw a shape from a table or a lookup subtract it from the position first.

First met and defined in [chapter 12](part-2/shapes.md). The detail: [`re/notes/shapes.md`](repo:re/notes/shapes.md#record-header-complete), "Record header, complete".

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

### Indexed framebuffer

A picture that holds one colour number per pixel, a byte, the palette applied only when it is shown: the port's form of every viewport and of its picture of 640 by 214.

First met and defined in [chapter 11](part-2/display.md). The detail: [`SPEC.md`](repo:SPEC.md#64-video-model), section 6.4; [`src/video.c`](repo:src/video.c).

Elsewhere: [Indexed color](https://en.wikipedia.org/wiki/Indexed%5Fcolor), Wikipedia.

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

### Interrupt request

The bit by which a chip asks the processor for an interrupt; Paula raises one for a channel when it is switched on and again at the end of every cycle, and it reaches the processor only while it is enabled.

First met and defined in [chapter 18](part-2/sound.md). The detail: [`re/notes/headless.md`](repo:re/notes/headless.md#the-audio-channels), "The audio channels".

Elsewhere: [Interrupt request](https://en.wikipedia.org/wiki/Interrupt%5Frequest), Wikipedia; [*Amiga Hardware Reference Manual*](https://archive.org/details/commodore-amiga-tech-ref-series-amiga-hardware-reference-manual-3rd-edition), 3rd edition, Internet Archive.

### Key buffer

The game's ten raw key codes and ten qualifier words with a count, filled by its handler on input.device and emptied by four of its five readers.

First met and defined in [chapter 19](part-2/front-end.md). The detail: [`re/notes/keys.md`](repo:re/notes/keys.md#the-chain-from-a-key-press-to-an-effect), "The chain from a key press to an effect"; [`src/keys.c`](repo:src/keys.c).
Elsewhere: [Keyboard buffer](https://en.wikipedia.org/wiki/Keyboard%5Fbuffer), Wikipedia.

### Key layer

The port's own routine in front of the key buffer that rewrites its seven command keys into the codes and the Control bit the original's readers expect; policy, not a port.

First met and defined in [chapter 19](part-2/front-end.md). The detail: [`re/notes/porting-m3.md`](repo:re/notes/porting-m3.md#the-ports-own-layer), "The port's own layer"; [`src/portkeys.c`](repo:src/portkeys.c).

### Keyboard assist

The port's switch that makes one key press one step in the weapon menu and lets a short tap reach the game exactly once everywhere else; off in every comparison with the original.

First met and defined in [chapter 1](part-1/faithful.md). The detail: [`re/notes/porting-m4.md`](repo:re/notes/porting-m4.md#the-keyboard-assist), "The keyboard assist".

### Keymap

The system's table that turns a raw key code and its qualifier into characters; the default one lies in the Kickstart ROM, and the port's build runs the ROM's own routine over it once.

First met and defined in [chapter 19](part-2/front-end.md). The detail: [`re/notes/keys.md`](repo:re/notes/keys.md#raw-code-to-character-consoledevice), "Raw code to character: console.device"; [`re/notes/porting-m3.md`](repo:re/notes/porting-m3.md#the-key-conversion-table), "The key conversion table".
Elsewhere: [Keyboard layout](https://en.wikipedia.org/wiki/Keyboard%5Flayout), Wikipedia.

### Kickstart

The heart of AmigaOS, in the ROM of the Amiga 500 and 2000 and loaded from a disk by the 1000; the port takes the font and the key table from Kickstart 1.3 when it is built and is held to its floating point, and the ROM is not part of the repository.

First met and defined in [chapter 2](part-1/amiga.md). The detail: [`re/notes/system-font.md`](repo:re/notes/system-font.md#the-rom), "The ROM".

Elsewhere: [Kickstart (Amiga)](https://en.wikipedia.org/wiki/Kickstart%5F(Amiga)), Wikipedia.

### Kind (of a field)

How a field of a registered record travels between the original's big-endian bytes and the port's structure: as the same integer, or as a pointer turned into a shape handle, a sound handle, an offset, a flag or the handler a vector names; seven in all.

Not the same as an object record's kind byte (chapter 15), a manifest entry's kind (chapter 3) or a routine's kind in the routine inventory (chapter 4).

First met and defined in [chapter 22](part-3/core.md). The detail: [`src/records.def`](repo:src/records.def), its opening comment; [`tests/m4state.py`](repo:tests/m4state.py).

### Label

A name the listing gives an address that a branch or a call leads to, on a line of its own and ending in a colon: a routine's name, a name the project gave a place inside one, or `loc_` and the address.

First met and defined in [chapter 4](part-1/reading.md). The detail: [`re/Wings.lst`](repo:re/Wings.lst).

Elsewhere: [Label (computer science)](https://en.wikipedia.org/wiki/Label%5F(computer%5Fscience)), Wikipedia.

### Landing stall

The flag the stick forward alone sets while the player's aircraft flies west, and every other input clears: the aircraft is drawn with its nose up while its pitch is eased downwards, and only with the flag set does it land on the carrier's deck.

First met and defined in [chapter 14](part-2/player.md). The detail: [`re/notes/objects.md`](repo:re/notes/objects.md#the-players-record), "The player's record", the globals; [`re/notes/porting-m4.md`](repo:re/notes/porting-m4.md#landing-refuelling-rearming), "Landing, refuelling, rearming".

### Latch

A flag that keeps a brief event until it is read; the game latches a tap and a hold of the fire button between two input samples, so that a tap shorter than the interval between them still reaches the game.

First met and defined in [chapter 7](part-1/time.md). The detail: [`re/notes/input.md`](repo:re/notes/input.md#fire-button-and-the-taphold-discrimination), "Fire button and the tap/hold discrimination".

### Leave rule

The shell's rule that leaving fullscreen asks the core for the pause, a request and not a toggle, so that Escape, which a browser takes for leaving fullscreen, always pauses.

First met and defined in [chapter 23](part-3/shell.md). The detail: [`SPEC.md`](repo:SPEC.md#62-shell), section 6.2, "Input"; [`web/main.js`](repo:web/main.js).

Elsewhere: [Fullscreen API](https://developer.mozilla.org/en-US/docs/Web/API/Fullscreen%5FAPI), MDN.

### Level-4 vector

The long at `0x70` holding the address of the routine the 68000 runs for an interrupt of level 4, the level of Paula's four channels among the processor's seven; the sound effects engine puts its handler there, and the music player its own while it is loaded.

First met and defined in [chapter 18](part-2/sound.md). The detail: [`re/notes/music.md`](repo:re/notes/music.md#the-timer), "The timer".

Elsewhere: [Interrupt vector table](https://en.wikipedia.org/wiki/Interrupt%5Fvector%5Ftable), Wikipedia; [*M68000 Family Programmer's Reference Manual*](https://archive.org/details/m68000familyprog0000unse), Internet Archive.

### Library

A collection of the operating system's routines that a program calls through a table of jumps at fixed offsets from the library's address; the game uses dos, exec, graphics and mathffp among others.

First met and defined in [chapter 2](part-1/amiga.md). The detail: [`SPEC.md`](repo:SPEC.md#34-operating-system-and-hardware-use), section 3.4.

Elsewhere: [Library (computing)](https://en.wikipedia.org/wiki/Library%5F(computing)), Wikipedia; [*Amiga ROM Kernel Reference Manual: Libraries*](https://archive.org/details/commodore-amiga-tech-ref-series-amiga-rom-kernel-reference-manual-libraries-3rd-edition), 3rd edition, Internet Archive.

### Library base

The address of a library in memory, which a program keeps in a variable and loads into A6 to call one of the library's routines at a fixed offset below it; [`re/libbases.txt`](repo:re/libbases.txt) names the game's five.

First met and defined in [chapter 4](part-1/reading.md). The detail: [`tools/disasm.py`](repo:tools/disasm.py); [`tools/fd/`](repo:tools/fd/).

Elsewhere: [*Amiga ROM Kernel Reference Manual: Libraries*](https://archive.org/details/commodore-amiga-tech-ref-series-amiga-rom-kernel-reference-manual-libraries-3rd-edition), 3rd edition, Internet Archive.

### Lift

The carrier's lift, which carries the player's aircraft between the deck and the hold below it.

First met and defined in [chapter 14](part-2/player.md). The detail: [`re/notes/porting-m4.md`](repo:re/notes/porting-m4.md#landing-refuelling-rearming), "Landing, refuelling, rearming".

### Line editor

The routine that edits a line of text for the name entry and the dialog's file names, with a caret, the cursor keys and the deletes, and no filter on what goes in.

First met and defined in [chapter 19](part-2/front-end.md). The detail: [`re/notes/keys.md`](repo:re/notes/keys.md#the-commands), "The commands"; [`src/dialog.c`](repo:src/dialog.c).

### Listing

The game's program written out as assembly language by the disassembler, each instruction with its address, its bytes and the names of what it touches: [`re/Wings.lst`](repo:re/Wings.lst).

First met in [chapter 1](part-1/faithful.md), defined in [chapter 4](part-1/reading.md). The detail: [`SPEC.md`](repo:SPEC.md), sections [2](repo:SPEC.md#2-repository) and [4](repo:SPEC.md#4-tools).

Elsewhere: [Disassembler](https://en.wikipedia.org/wiki/Disassembler), Wikipedia.

### Little-endian

The byte order that stores the least significant byte of a number first: that of the machines the port runs on, WebAssembly's among them; the opposite of big-endian.

First met and defined in [chapter 3](part-1/disk.md). The detail: [`tools/extract_tables.py`](repo:tools/extract%5Ftables.py).

Elsewhere: [Endianness](https://en.wikipedia.org/wiki/Endianness), Wikipedia.

### Load and save dialog

The screen that lists the saved games of the game's directory in the file system's own order and loads one, or saves the game under a typed name, drawn with graphics.library in topaz 8.

First met and defined in [chapter 19](part-2/front-end.md). The detail: [`re/notes/frontend.md`](repo:re/notes/frontend.md#screen-by-screen), "Screen by screen"; [`src/dialog.c`](repo:src/dialog.c).
Elsewhere: [Saved game](https://en.wikipedia.org/wiki/Saved%5Fgame), Wikipedia.

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

### Low resolution

The Amiga's mode of 320 pixels across a line, each twice as wide as a high-resolution pixel; the playfield and the front end's pictures use it.

First met and defined in [chapter 11](part-2/display.md). The detail: [`re/notes/display.md`](repo:re/notes/display.md#screens), "Screens".

Elsewhere: [*Amiga Hardware Reference Manual*](https://archive.org/details/commodore-amiga-tech-ref-series-amiga-hardware-reference-manual-3rd-edition), 3rd edition, Internet Archive.

### Machine code

A program as the processor reads it: its instructions as numbers in memory.

First met in [chapter 1](part-1/faithful.md), defined in [chapter 2](part-1/amiga.md). The detail: [`SPEC.md`](repo:SPEC.md#32-executable), section 3.2.

Elsewhere: [Machine code](https://en.wikipedia.org/wiki/Machine%5Fcode), Wikipedia.

### Manifest

The list of what the build reads out of the original's files, [`re/tables.toml`](repo:re/tables.toml): 122 entries, each with a name, a kind and where to read it, from the program, the music player and the ROM; the build writes them as C tables, so that no number of the game is typed again.

First met and defined in [chapter 21](part-3/repository.md). The detail: [`re/tables.toml`](repo:re/tables.toml); [`tools/extract_tables.py`](repo:tools/extract%5Ftables.py); [`SPEC.md`](repo:SPEC.md#5-build), section 5.

### Manx Aztec C

The C compiler the game's C was built with: its int, as the game was built, is 16 bits, its code reaches the variables through A4, and each of its routines keeps a stack frame on A5.

First met and defined in [chapter 3](part-1/disk.md). The detail: [`SPEC.md`](repo:SPEC.md#32-executable), section 3.2.

Elsewhere: [Aztec C](https://en.wikipedia.org/wiki/Aztec%5FC), Wikipedia.

### Map decoder

The project's reader of the map files, [`tools/map_decode.py`](repo:tools/map%5Fdecode.py), written apart from the port: it takes a record apart and predicts the map's draws of a pass, and is held to the original's draws.

First met and defined in [chapter 13](part-2/world.md). The detail: [`re/notes/map.md`](repo:re/notes/map.md#the-decoder-and-its-controls), "The decoder and its controls".

### Map record

One word of a map file, two bytes for eight pixels of the world from west to east: the draw flag, the height field, the slot of its shape and what lies under it, land, a ship's deck or open sea.

First met and defined in [chapter 13](part-2/world.md). The detail: [`re/notes/map.md`](repo:re/notes/map.md#the-record), "The record"; [`SPEC.md`](repo:SPEC.md#35-file-formats), section 3.5.

### Mask

A one-bit picture of where a shape has any colour at all: the OR of its planes, or, for a shape of one plane, that plane; the blitter draws the shape's bits where the mask is set and keeps the background elsewhere.

Not the same as a [plane mask](#plane-mask), a byte of a shape's header naming the screen's planes a stored plane is written to, nor the blitter's [word masks](#word-masks), which blank the edges of a row.

First met and defined in [chapter 2](part-1/amiga.md). The detail: [`re/notes/drawing.md`](repo:re/notes/drawing.md#what-shape%5Fdraw-does-exactly), "What `shape_draw` does, exactly".

Elsewhere: [Mask (computing)](https://en.wikipedia.org/wiki/Mask%5F(computing)), Wikipedia.

### Memory-form shift

A 68000 shift that works on a word in memory, by one bit, rather than on a register; the emulator the tests run on takes the game's five arithmetic ones for logical shifts, which gives three of them, the right shifts, a wrong word, and a hook corrects those three.

First met and defined in [chapter 5](part-1/oracle.md). The detail: [`re/notes/porting-m5.md`](repo:re/notes/porting-m5.md#the-emulators-memory-form-shift-observed), "The emulator's memory-form shift (observed)"; [`tools/m68k_fix.py`](repo:tools/m68k%5Ffix.py).

Elsewhere: [*M68000 Family Programmer's Reference Manual*](https://archive.org/details/m68000familyprog0000unse), Internet Archive.

### Milestone

One of the numbered stages the port was built in, M0 to M9, each ending with a working page and green tests and accepted on a deliverable of the specification: M4 to M7 the missions, M8 the sound, M9 the page's drawing.

First met and defined in [chapter 8](part-1/mission.md). The detail: [`SPEC.md`](repo:SPEC.md#9-milestones), section 9.

### Minterm

One of the eight ways the blitter's three sources, A, B and C, can be set at a pixel; the blitter's logic function is a byte with a bit for each minterm, saying whether the result is 1 there, and the game's blit uses `0xCA`, B where A is set and C where it is not.

First met and defined in [chapter 12](part-2/shapes.md). The detail: [`re/notes/drawing.md`](repo:re/notes/drawing.md#what-shape%5Fdraw-does-exactly), "What `shape_draw` does, exactly"; [`tests/blitter.py`](repo:tests/blitter.py).

Elsewhere: [Bit blit](https://en.wikipedia.org/wiki/Bit%5Fblit), Wikipedia; [*Amiga Hardware Reference Manual*](https://archive.org/details/commodore-amiga-tech-ref-series-amiga-hardware-reference-manual-3rd-edition), 3rd edition, Internet Archive.

### Mirror marker

The word at `+8` of each shape record of the player's aircraft and its weapons, set at load, that records which way the stored pixels face; when it differs from the facing wanted, the game mirrors the shape in place.

First met and defined in [chapter 12](part-2/shapes.md). The detail: [`re/notes/shapes.md`](repo:re/notes/shapes.md#record-header-complete), "Record header, complete".

### Mission number

The mission within the current rank, counted from 1, which a won mission counts on and a promotion sets back to 1; with the rank it picks the map.

First met and defined in [chapter 17](part-2/campaign.md). The detail: [`re/notes/campaign.md`](repo:re/notes/campaign.md#a-mission-won), "A mission won".

### Mission script

A recorded sequence of stick and key inputs that flies a mission the same way every time, for the original and the port alike.

First met and defined in [chapter 1](part-1/faithful.md). The detail: [`re/notes/porting-m4.md`](repo:re/notes/porting-m4.md#how-the-port-is-held-to-the-original), "How the port is held to the original".

### Mode (of an enemy aircraft)

The word of an enemy aircraft record that says what it does while it flies: 1 a fighter cruising, 2 a fighter on the player's tail, 4 a torpedo plane, `0x10` a torpedo plane after its drop, with 8 added while it turns.

First met and defined in [chapter 16](part-2/enemy.md). The detail: [`re/notes/enemy.md`](repo:re/notes/enemy.md#the-record), "The record", and ["What each state and mode does"](repo:re/notes/enemy.md#what-each-state-and-mode-does-read-and-held-by-the-oracle-and-the-closed-loop).

### Music player

The game's second sound engine, `songplay`, a small program of its own that the game loads beside its songs and calls with a command number, and that plays the songs on a timer of a CIA.

First met and defined in [chapter 18](part-2/sound.md). The detail: [`re/notes/music.md`](repo:re/notes/music.md#the-games-calls), "The game's calls".

### Name entry

The dialog before the high-score screen that asks for the player's name with the line editor, only when the score beats the tenth row's.

First met and defined in [chapter 19](part-2/front-end.md). The detail: [`re/notes/frontend.md`](repo:re/notes/frontend.md#screen-by-screen), "Screen by screen"; [`src/hiscore.c`](repo:src/hiscore.c).

### Name list

A list of four-character shape names in the program's data, ended by a zero, which the game resolves in its container at load into a pointer table.

First met and defined in [chapter 12](part-2/shapes.md). The detail: [`re/notes/shapes.md`](repo:re/notes/shapes.md#name-lists-and-containers), "Name lists and containers".

### Native library

The port's C compiled by the test machine's own compiler into a library that the tests load and call directly, beside the WebAssembly of the page, which is built from the same sources.

First met and defined in [chapter 5](part-1/oracle.md). The detail: [`SPEC.md`](repo:SPEC.md), sections [5](repo:SPEC.md#5-build) and [8](repo:SPEC.md#8-verification).

### Neutralised island

An island whose two counts, its soldiers alive and its pillboxes standing, have both fallen to zero; it pays its bonus, and the map's last, with no enemy ship left, ends the mission.

First met and defined in [chapter 15](part-2/weapons.md). The detail: [`re/notes/porting-m5.md`](repo:re/notes/porting-m5.md#three-kinds-of-target), "Three kinds of target".

### Object record

One of the fifteen records of 42 bytes in which a bomb, a rocket or the torpedo flies, or the explosion of a crash goes out, with a sixteenth for the enemy's torpedo: its kind byte says whether it flies, goes out or is free, its type which weapon it is.

First met and defined in [chapter 15](part-2/weapons.md). The detail: [`re/notes/objects.md`](repo:re/notes/objects.md#claiming-and-freeing-a-record), "Claiming and freeing a record" and ["Record layout, the fields that all of them share"](repo:re/notes/objects.md#record-layout-the-fields-that-all-of-them-share).

### Observer

A hook of the headless original on a routine's first instruction that records every entry with the registers and the arguments, and only reads, so that watching changes nothing.

First met and defined in [chapter 6](part-1/headless.md). The detail: [`re/notes/headless.md`](repo:re/notes/headless.md#observers), "Observers".

### Opaque shape

A shape drawn without a mask, its whole box written, colour 0 included: one whose plane is larger than the 1,040 bytes of the mask's buffer, or one that stores no plane.

First met and defined in [chapter 12](part-2/shapes.md). The detail: [`re/notes/drawing.md`](repo:re/notes/drawing.md#what-shape%5Fdraw-does-exactly), "What `shape_draw` does, exactly".

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

### Outer loop

The loop of the game's `main` that runs the rank selection, the briefing, a mission and the high-score screen again and again, after the title sequence has run once.

First met and defined in [chapter 19](part-2/front-end.md). The detail: [`re/notes/frontend.md`](repo:re/notes/frontend.md#the-outer-loop-as-a-state-diagram), "The outer loop, as a state diagram".

### Overlay (of the file system)

The files the game writes, the high scores and the saved games, kept by the core in front of the read-only disk: a written file shadows the disk's of the same name and a deleted one hides it. It lies outside the core's state, so that loading a save state does not un-write a file; not the shell's diagnostics overlay.

First met and defined in [chapter 22](part-3/core.md). The detail: [`src/fs.c`](repo:src/fs.c); [`re/notes/porting-m3.md`](repo:re/notes/porting-m3.md#the-file-systems-write-side), "The file system's write side".

Elsewhere: [Union mount](https://en.wikipedia.org/wiki/Union%5Fmount), Wikipedia, the same idea for directories.

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

### Pattern

A run of a track's events, notes and commands of two bytes each, which the track's sequence plays in turn.

First met and defined in [chapter 18](part-2/sound.md). The detail: [`re/notes/music.md`](repo:re/notes/music.md#the-song-format-wofsongss-data-hunk), "The song format".

### Paula

The Amiga's chip for sound, four channels that each play 8-bit sound samples at their own rate and volume; it also handles the interrupts, the disk and the serial port.

First met and defined in [chapter 2](part-1/amiga.md). The detail: [`re/notes/sound.md`](repo:re/notes/sound.md).

Elsewhere: [Original Chip Set](https://en.wikipedia.org/wiki/Original%5FChip%5FSet), Wikipedia; [*Amiga Hardware Reference Manual*](https://archive.org/details/commodore-amiga-tech-ref-series-amiga-hardware-reference-manual-3rd-edition), 3rd edition, Internet Archive.

### Period

Paula's measure of pitch: how many ticks of the colour clock, 3,546,895 a second on a PAL Amiga, each byte of a sound sample is held; a smaller period plays higher.

First met and defined in [chapter 2](part-1/amiga.md). The detail: [`re/notes/sound.md`](repo:re/notes/sound.md).

### Pillbox

The notes' name for an island's large gun, slots `0x0F` to `0x1E`, which fires at the aircraft and which only a rocket destroys; its slot shows which of its four map records a rocket has hit.

First met and defined in [chapter 15](part-2/weapons.md). The detail: [`re/notes/porting-m5.md`](repo:re/notes/porting-m5.md#three-kinds-of-target), "Three kinds of target".

Elsewhere: [Pillbox (military)](https://en.wikipedia.org/wiki/Pillbox%5F(military)), Wikipedia, the bunker the notes' name comes from, where the manual's target is a large anti-aircraft gun.

### Pitch (of the aircraft)

The angle of the player's aircraft, not a sound's pitch, in hundredths of a degree, positive with the nose up, which moves each tick a quarter of the way towards a target the stick sets.

First met and defined in [chapter 14](part-2/player.md). The detail: [`re/notes/ffp.md`](repo:re/notes/ffp.md#player%5Fmotion-0x01bdfa-once-per-tick-from-0x01c70e), "`player_motion` `0x01BDFA`, once per tick from `0x01C70E`".

Elsewhere: [Aircraft principal axes](https://en.wikipedia.org/wiki/Aircraft%5Fprincipal%5Faxes), Wikipedia.

### Pixel aspect

How wide a pixel is shown against its height: on PAL a low-resolution pixel is 16/15 as wide as tall and a framebuffer pixel half that, so the picture of 640 by 214 is shown in a box of 1024 : 642.

First met and defined in [chapter 23](part-3/shell.md). The detail: [`SPEC.md`](repo:SPEC.md#62-shell), section 6.2, "Video"; [`web/video.js`](repo:web/video.js).

Elsewhere: [Pixel aspect ratio](https://en.wikipedia.org/wiki/Pixel%5Faspect%5Fratio), Wikipedia.

### Plane mask

A byte of a shape's header naming the screen's planes that one stored plane is written to; a mask of two bits writes one stored plane into two planes.

First met and defined in [chapter 12](part-2/shapes.md). The detail: [`SPEC.md`](repo:SPEC.md#35-file-formats), section 3.5; [`re/notes/shapes.md`](repo:re/notes/shapes.md#record-header-complete), "Record header, complete".

### Player's record

The thirty bytes the game keeps of the player's aircraft: its height and its x, its frame, the state word that selects what the tick does with it, its fuel and oil, its facing, its two speeds and the enemy's countdown.

First met and defined in [chapter 14](part-2/player.md). The detail: [`re/notes/objects.md`](repo:re/notes/objects.md#the-players-record), "The player's record".

### Playfield

The play screen's upper area, where the game is played: 320 by 162 in low resolution with five bitplanes, under the sky's palette above the split line and the sea's below.

First met and defined in [chapter 11](part-2/display.md). The detail: [`re/notes/display.md`](repo:re/notes/display.md#the-play-screen-line-by-line), "The play screen line by line".

### Pointer field

One of the four kinds of field in a saved game's raw part that hold an address of the saving machine's memory: the player's shape, a shape the tick keeps for level flight, the torpedo's shape and a ship's gun list; the port derives them when it loads a game.

First met and defined in [chapter 17](part-2/campaign.md). The detail: [`re/notes/campaign.md`](repo:re/notes/campaign.md#what-the-port-writes-in-the-raw-part), "What the port writes in the raw part", and ["The loader"](repo:re/notes/campaign.md#the-loader).

### Pointer table

The array of shape-record pointers a name list becomes when its container is loaded, in the list's order, null where a name is absent; the port keeps an array of shape numbers instead.

First met and defined in [chapter 12](part-2/shapes.md). The detail: [`re/notes/shapes.md`](repo:re/notes/shapes.md#container-and-lookup), "Container and lookup".

### Poke

A value written into one address of the game's state at a fixed point of a run, on both sides, the original and the port, so that a script reaches a state no flight of its length reaches.

First met and defined in [chapter 8](part-1/mission.md). The detail: [`tests/m4compare.py`](repo:tests/m4compare.py); [`re/notes/porting-m5.md`](repo:re/notes/porting-m5.md#the-scripts), "The scripts".

Elsewhere: [PEEK and POKE](https://en.wikipedia.org/wiki/PEEK%5Fand%5FPOKE), Wikipedia.

### Pool

One of four tables of small records the game allocates once at its start, Smoke, Splashes, Balloons and Ricochet, each record with a byte or word that says it is in use, claimed by a walk for the first free one.

First met and defined in [chapter 15](part-2/weapons.md). The detail: [`re/notes/objects.md`](repo:re/notes/objects.md#the-inventory), "The inventory"; [`re/notes/porting-m5.md`](repo:re/notes/porting-m5.md#the-pools), "The pools".

Elsewhere: [Object pool pattern](https://en.wikipedia.org/wiki/Object%5Fpool%5Fpattern), Wikipedia.

### Porting note

A note of [`re/notes/`](repo:re/notes/) written for a milestone: what was ported, how it is held to the original and what stands in, each statement marked as observed, with the test or tool that shows it, or as read from the listing alone.

First met and defined in [chapter 21](part-3/repository.md). The detail: [`re/notes/porting-m4.md`](repo:re/notes/porting-m4.md#how-the-port-is-held-to-the-original), "How the port is held to the original", and the other milestones' notes in [`re/notes/`](repo:re/notes/).

### Program counter

The 68000's register that holds the address of the instruction being executed; an address given relative to it names a distance from the instruction, not a place, so such a call needs no correcting wherever the program is loaded.

First met in [chapter 3](part-1/disk.md), defined in [chapter 4](part-1/reading.md). The detail: [`tools/disasm.py`](repo:tools/disasm.py).

Elsewhere: [Program counter](https://en.wikipedia.org/wiki/Program%5Fcounter), Wikipedia; [*M68000 Family Programmer's Reference Manual*](https://archive.org/details/m68000familyprog0000unse), Internet Archive.

### Promotion

The step from a rank's last mission to the next rank's first: the rank one up, at most to 6, the balloons over the carrier and a Hellcat more at the next mission.

First met and defined in [chapter 17](part-2/campaign.md). The detail: [`re/notes/campaign.md`](repo:re/notes/campaign.md#the-promotion-the-extra-hellcat-and-the-balloons), "The promotion, the extra Hellcat and the balloons".

### Pure routine

A routine that computes from its inputs alone, without touching anything else; every pure routine is held to the original under the oracle.

First met and defined in [chapter 1](part-1/faithful.md). The detail: [`SPEC.md`](repo:SPEC.md#74-working-method), section 7.4.

Elsewhere: [Pure function](https://en.wikipedia.org/wiki/Pure%5Ffunction), Wikipedia.

### Push (of the keyboard assist)

The keyboard assist's stick, forward or back, held for exactly twelve VBlanks in the weapon menu in place of a key's press: three input samples, one step.

First met and defined in [chapter 19](part-2/front-end.md). The detail: [`re/notes/porting-m4.md`](repo:re/notes/porting-m4.md#what-the-assist-does), "What the assist does"; [`src/assist.c`](repo:src/assist.c).

### Qualifier

The word of bits that comes with a raw key code and says which of Shift, Caps Lock, Control, Alt and the Amiga keys were held; the game's command readers test only Control's, and its line editor also the two Shifts' and right Amiga's.

First met and defined in [chapter 19](part-2/front-end.md). The detail: [`re/notes/keys.md`](repo:re/notes/keys.md#control-and-the-two-masks), "Control, and the two masks".
Elsewhere: [Modifier key](https://en.wikipedia.org/wiki/Modifier%5Fkey), Wikipedia.

### Quirk

A place where the original's code does something odd, reading past a table, handing a routine the wrong thing, keeping code nothing runs or disagreeing with the game's manual, which the port keeps because the original does it.

First met and defined in [chapter 20](part-2/quirks.md). The detail: [`re/notes/porting-m5.md`](repo:re/notes/porting-m5.md#the-wrecks-explosion-and-the-map-lists-address-observed), "The wreck's explosion and the map list's address"; [`re/notes/porting-m6.md`](repo:re/notes/porting-m6.md#flags-that-decide-in-the-tick), "Flags that decide in the tick".

### Rank

One of the campaign's seven stages, 0 to 6, each a fixed run of maps; the player chooses the first at the rank selection, a promotion moves it on, and a high-score row records the rank reached.

First met and defined in [chapter 17](part-2/campaign.md). The detail: [`re/notes/campaign.md`](repo:re/notes/campaign.md#the-order-of-the-maps), "The order of the maps".

### Rank selection

The menu of the seven ranks and the load item below them, between the title sequence and the briefing, its highlight a shape drawn in exclusive-or.

First met and defined in [chapter 19](part-2/front-end.md). The detail: [`re/notes/frontend.md`](repo:re/notes/frontend.md#screen-by-screen), "Screen by screen"; [`src/front.c`](repo:src/front.c).

### Raw key code

The number from 0 to 127 that the Amiga's keyboard sends for a key's place, not for what is printed on it, with bit 7 set when the key goes up.

First met and defined in [chapter 19](part-2/front-end.md). The detail: [`re/notes/keys.md`](repo:re/notes/keys.md#the-chain-from-a-key-press-to-an-effect), "The chain from a key press to an effect".
Elsewhere: [Scancode](https://en.wikipedia.org/wiki/Scancode), Wikipedia.

### Raw part

The first piece of a saved game: 2,122 bytes of the game's memory from the object records on, as they stand, which hold the counts the later pieces need.

First met and defined in [chapter 17](part-2/campaign.md). The detail: [`re/notes/campaign.md`](repo:re/notes/campaign.md#the-raw-part), "The raw part"; [`tools/savegame.py`](repo:tools/savegame.py).

### Reach map

The record of which routines, and which of their instructions, the mission scripts execute in the headless original, counted by the window of the run and the phase; what it shows the game runs is what the port carries.

First met and defined in [chapter 8](part-1/mission.md). The detail: [`tools/reach_observe.py`](repo:tools/reach%5Fobserve.py); [`re/notes/porting-m4.md`](repo:re/notes/porting-m4.md#what-decides-what-is-ported-the-reach-map), "What decides what is ported: the reach map".

Elsewhere: [Code coverage](https://en.wikipedia.org/wiki/Code%5Fcoverage), Wikipedia.

### Reader (of the key buffer)

One of the five routines that look at the key buffer: the menus' reader, the line editor, the briefing and the commands in flight take keys from it, and the wait for a release only asks whether one waits.

First met and defined in [chapter 19](part-2/front-end.md). The detail: [`re/notes/keys.md`](repo:re/notes/keys.md#the-five-readers), "The five readers".

### Register

A small named store inside a processor or a chip: the 68000's sixteen hold the values it computes with, and a custom chip's, at fixed addresses from `0xDFF000`, tell the chip what to do.

First met in [chapter 1](part-1/faithful.md), defined in [chapter 2](part-1/amiga.md). The detail: [`re/notes/drawing.md`](repo:re/notes/drawing.md#the-blitter-library), "The blitter library".

Elsewhere: [Processor register](https://en.wikipedia.org/wiki/Processor%5Fregister), Wikipedia; [*M68000 Family Programmer's Reference Manual*](https://archive.org/details/m68000familyprog0000unse), Internet Archive.

### Register programme

The blitter's registers as they stand when a blit starts, its pointers, modulos, word masks, shifts, logic function and size; the blit tests capture it from the original and replay it on a model of the blitter.

First met and defined in [chapter 12](part-2/shapes.md). The detail: [`tests/blitter.py`](repo:tests/blitter.py); [`re/notes/porting-m1.md`](repo:re/notes/porting-m1.md#how-the-tests-establish-it), "How the tests establish it".

### Registered state

The variables, tables and records the registries list, kept as members of the core's state, each tied to its address in the original, so that the tests copy and compare it field by field and a save state cannot leave any of it out.

First met and defined in [chapter 22](part-3/core.md). The detail: [`src/globals.def`](repo:src/globals.def), [`src/mission.def`](repo:src/mission.def), [`src/records.def`](repo:src/records.def); [`re/notes/porting-m4.md`](repo:re/notes/porting-m4.md#where-mission-memory-lives), "Where mission memory lives".

### Registry

One of the port's three lists, [`src/globals.def`](repo:src/globals.def), [`src/mission.def`](repo:src/mission.def) and [`src/records.def`](repo:src/records.def), in which every variable, table and record layout taken over from the original is an entry, a macro call with its original address or offset; the files that include a list expand it into structures and code.

First met and defined in [chapter 22](part-3/core.md). The detail: the three files' opening comments; [`src/core.c`](repo:src/core.c).

Elsewhere: [X macro](https://en.wikipedia.org/wiki/X%5Fmacro), Wikipedia.

### Relation (to the player)

The word of an enemy aircraft record, worked out every tick, that says where it is against the player: 1 behind him the same way, 3 ahead of him the same way, 2 flying the other way east of him, 4 flying the other way west of him.

First met and defined in [chapter 16](part-2/enemy.md). The detail: [`re/notes/enemy.md`](repo:re/notes/enemy.md#the-record), "The record".

### Relocation

An entry in a hunk file that names a place in a hunk holding an address, which the loader corrects by where its target hunk landed.

First met and defined in [chapter 3](part-1/disk.md). The detail: [`tools/hunk.py`](repo:tools/hunk.py); [`SPEC.md`](repo:SPEC.md#32-executable), section 3.2.

Elsewhere: [Relocation (computing)](https://en.wikipedia.org/wiki/Relocation%5F(computing)), Wikipedia; [*The AmigaDOS Manual*](https://archive.org/details/1991-baker-jesup-et-al-the-amigados-manual-3rd-ed), 3rd edition, Internet Archive.

### Remake

A new program made to look and play like an old one, written from watching the old one.

First met and defined in [chapter 1](part-1/faithful.md). The detail: [`SPEC.md`](repo:SPEC.md#1-goal), section 1.

Elsewhere: [Video game remake](https://en.wikipedia.org/wiki/Video%5Fgame%5Fremake), Wikipedia.

### Renderer

The shell's code that puts the picture on the canvas: the WebGL renderer, the main one, or the 2D renderer, its fallback; the page and the notes call the one in use the path.

First met and defined in [chapter 23](part-3/shell.md). The detail: [`web/video.js`](repo:web/video.js); [`re/notes/page-video.md`](repo:re/notes/page-video.md).

Elsewhere: [WebGL: 2D and 3D graphics for the web](https://developer.mozilla.org/en-US/docs/Web/API/WebGL%5FAPI), MDN.

### Resume point

The number a coroutine keeps of where it waits: the line number of the wait in its source file, 0 for not started; the next call jumps back to it through a `switch`.

First met and defined in [chapter 22](part-3/core.md). The detail: [`src/coro.h`](repo:src/coro.h); [`src/wof.h`](repo:src/wof.h), `wof_ctx_t`.

Elsewhere: [Coroutines in C](https://www.chiark.greenend.org.uk/~sgtatham/coroutines.html), Simon Tatham.

### Review

The controller's check of a worker's report before a merge, in seven steps, among them a clean rebuild, the full suite and one check of the reviewer's own that the worker's tests could not make.

First met and defined in [chapter 10](part-1/making.md). The detail: [`CONTROLLER.md`](repo:CONTROLLER.md#reviewing-a-report), "Reviewing a report".

Elsewhere: [Code review](https://en.wikipedia.org/wiki/Code%5Freview), Wikipedia.

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

### Save state

The core's whole state as bytes, copied out and loaded back so that the game goes on exactly where it was: the core's counterpart of an emulator's save state, not the game's own saved game, which is a file the game writes (chapter 17) and the overlay keeps.

First met and defined in [chapter 22](part-3/core.md). The detail: [`SPEC.md`](repo:SPEC.md#61-core), section 6.1; [`src/core.c`](repo:src/core.c); [`re/notes/porting-m4.md`](repo:re/notes/porting-m4.md#save-states-and-the-mirror-markers), "Save states and the mirror markers".

Elsewhere: [Saved game](https://en.wikipedia.org/wiki/Saved%5Fgame), Wikipedia, whose save states are an emulator's.

### Saved game's walker

The routine `save_walk`, which goes through a saved game's pieces in a fixed order and hands each, as a file, an address, a length and a kind, to the writer's or the reader's callback, so that writing and reading take the same path; not the walks of the pools.

First met and defined in [chapter 17](part-2/campaign.md). The detail: [`re/notes/campaign.md`](repo:re/notes/campaign.md#the-layout), "The layout"; [`tools/savegame.py`](repo:tools/savegame.py).

### Schedule

The order of a run's VBlanks, passes and logic ticks as they happened; the VBlanks a pass takes are a setting of the run, so the schedule is an input of the simulation.

First met and defined in [chapter 6](part-1/headless.md). The detail: [`re/notes/passes.md`](repo:re/notes/passes.md#what-the-question-is), "What the question is"; [`re/notes/headless.md`](repo:re/notes/headless.md#scheduling), "Scheduling".

### Seed file

The port's file `wofdemo.seed`, 12 bytes written beside a recorded demo: the entropy stream's state, a hash of the demo, the swell's phase and the night flag, from which a playback of that demo starts.

First met and defined in [chapter 17](part-2/campaign.md). The detail: [`re/notes/demo.md`](repo:re/notes/demo.md#the-port), "The port"; [`re/notes/random.md`](repo:re/notes/random.md#the-seed), "The seed".

Elsewhere: [Random seed](https://en.wikipedia.org/wiki/Random%5Fseed), Wikipedia.

### Sequence

A track's list of patterns, each with a transpose, which the track plays in turn and may start again from its first.

First met and defined in [chapter 18](part-2/sound.md). The detail: [`re/notes/music.md`](repo:re/notes/music.md#the-song-format-wofsongss-data-hunk), "The song format".

### Session

One conversation with an AI coding assistant in a terminal opened in the repository, which only the owner can open: it reads files, runs commands and commits; what it has read and written, its context, has a limit, and a session whose context fills makes way for a fresh one.

First met and defined in [chapter 10](part-1/making.md). The detail: [`CLAUDE.md`](repo:CLAUDE.md#session-protocol), "Session protocol"; [`CONTROLLER.md`](repo:CONTROLLER.md#the-arrangement), "The arrangement".

### Shape container

A file of many shapes, the format that begins with `PPkc`: the number of shapes, a name of four characters for each, where each shape's entry begins, and the entries, each a header and the planes; the disk has twelve.

First met in [chapter 2](part-1/amiga.md), defined in [chapter 3](part-1/disk.md). The detail: [`re/notes/shapes.md`](repo:re/notes/shapes.md).

### Shape handle

The port's number for a shape, at most `0xFFFF`: its container and its place there, kept where the original keeps the address of the shape's record.

First met and defined in [chapter 17](part-2/campaign.md). The detail: [`re/notes/campaign.md`](repo:re/notes/campaign.md#what-the-port-writes-in-the-raw-part), "What the port writes in the raw part"; [`src/dialog.c`](repo:src/dialog.c), `saved_hellcat_shape`.

Elsewhere: [Handle (computing)](https://en.wikipedia.org/wiki/Handle%5F(computing)), Wikipedia.

### Shape record

One shape inside a container: a header of 20 bytes, then the planes it stores; to the game, a shape is a pointer to its record.

First met and defined in [chapter 12](part-2/shapes.md). The detail: [`re/notes/shapes.md`](repo:re/notes/shapes.md#record-header-complete), "Record header, complete"; [`SPEC.md`](repo:SPEC.md#35-file-formats), section 3.5.

### Shell

The thin layer of JavaScript around the core: the clock that paces it, the screen, a loudspeaker for the sound the core mixes, the keys, a place for saved games, and the help screen, the pause sign and fullscreen.

First met and defined in [chapter 1](part-1/faithful.md). The detail: [`SPEC.md`](repo:SPEC.md#62-shell), section 6.2.

### Ship record

One of five records of 30 bytes, the destroyer's, the battleship's, the cruise ship's, the Japanese carrier's and the carrier's: its span on the map, a pointer to its list of guns, 14 bytes an entry, and their count, its hits left, its deck's height, its score and its sinking.

First met and defined in [chapter 16](part-2/enemy.md). The detail: [`re/notes/enemy.md`](repo:re/notes/enemy.md#the-ships), "The ships" and ["Its guns"](repo:re/notes/enemy.md#its-guns).

### Sign extension

Widening a number to more bits by copying its sign bit into the new ones, so that it keeps its value: the 68000's `ext.l` widens a word to a long.

First met and defined in [chapter 3](part-1/disk.md). The detail: [`SPEC.md`](repo:SPEC.md#71-arithmetic), section 7.1.

Elsewhere: [Sign extension](https://en.wikipedia.org/wiki/Sign%5Fextension), Wikipedia; [*M68000 Family Programmer's Reference Manual*](https://archive.org/details/m68000familyprog0000unse), Internet Archive.

### Signed byte

A byte read as a number from −128 to 127 in two's complement, in which the top bit counts as −128: a byte above `0x7F` is itself less 256.

First met in [chapter 2](part-1/amiga.md), defined in [chapter 3](part-1/disk.md). The detail: [`SPEC.md`](repo:SPEC.md#35-file-formats), section 3.5.

Elsewhere: [Two's complement](https://en.wikipedia.org/wiki/Two%27s%5Fcomplement), Wikipedia.

### Sky flash

The sky's colour, colour 1, changed for a few passes to white, or to red for a target, when a rocket hits land, the aircraft crashes or a torpedo hits a ship, by a poke into the copper list.

First met and defined in [chapter 11](part-2/display.md). The detail: [`re/notes/porting-m5.md`](repo:re/notes/porting-m5.md#the-skys-flash-observed), "The sky's flash (observed)".

### Slice

A stretch of emulation that ends after a fixed number of instructions, after which the headless original's harness looks at the wall clock and goes on; where it ends changes nothing in the run. Slices once ended after a time, which made two runs of one script differ (chapter 9).

First met and defined in [chapter 6](part-1/headless.md). The detail: [`re/notes/headless.md`](repo:re/notes/headless.md#unicorn-as-it-behaves-here), "Unicorn, as it behaves here".

### Slot

A fixed position in a pointer table, by which the game's code and the map's records name a shape.

First met and defined in [chapter 12](part-2/shapes.md). The detail: [`re/notes/shapes.md`](repo:re/notes/shapes.md#masterlist-and-athlist), "MasterList and AthList".

### Small-data base

The register A4 in the game's code, holding `0x02AFFE`, 32,766 bytes into the data, from which every variable is reached by an offset of 16 bits.

First met and defined in [chapter 3](part-1/disk.md). The detail: [`SPEC.md`](repo:SPEC.md#32-executable), section 3.2.

### Soldier

One of the five men of a dug-out or a barracks, a record of eight bytes whose state says free, running, dying or dead; the soldiers alive are what an island counts.

First met and defined in [chapter 15](part-2/weapons.md). The detail: [`re/notes/porting-m5.md`](repo:re/notes/porting-m5.md#the-soldiers), "The soldiers".

### Song's fade

The music player's fade of a song: every track's volume one lower every few timer's ticks until none is left, which stops the song; not the display's [fade](#fade) of colours.

First met and defined in [chapter 18](part-2/sound.md). The detail: [`re/notes/music.md`](repo:re/notes/music.md#the-games-calls), "The game's calls".

Elsewhere: [Fade (audio engineering)](https://en.wikipedia.org/wiki/Fade%5F(audio%5Fengineering)), Wikipedia.

### Sound effects engine

The game's code that plays its eight sound effects: the sound slots the logic tick fills and, under them, the channel records, started by a VBlank server and stopped by the audio interrupt's handler.

First met and defined in [chapter 18](part-2/sound.md). The detail: [`re/notes/sound.md`](repo:re/notes/sound.md#two-layers), "Two layers".

### Sound handle

The port's number for a place in one of the sound files, kept where the original keeps a pointer into a sound sample: the file's index plus one in its top byte and the offset into the file below it, 0 for none.

First met and defined in [chapter 22](part-3/core.md). The detail: [`src/wof.h`](repo:src/wof.h), `WOF_SOUND`; [`re/notes/porting-m8.md`](repo:re/notes/porting-m8.md#the-port), "The port".

Elsewhere: [Handle (computing)](https://en.wikipedia.org/wiki/Handle%5F(computing)), Wikipedia.

### Sound sample

A recorded waveform that Paula plays back on one of its four channels, at its own pitch and volume.

First met and defined in [chapter 1](part-1/faithful.md). The detail: [`re/notes/sound.md`](repo:re/notes/sound.md).

Elsewhere: [Pulse-code modulation](https://en.wikipedia.org/wiki/Pulse-code%5Fmodulation), Wikipedia.

### Sound slot

One of eight records of `0x18` bytes, two for each of Paula's channels, in which the logic tick sets what should sound: a sound sample, its length, period, volume and repeat count; not a shape's [slot](#slot).

First met and defined in [chapter 18](part-2/sound.md). The detail: [`re/notes/sound.md`](repo:re/notes/sound.md#the-slots-and-what-they-play), "The slots and what they play".

### Split line

The line of the playfield where the sky's palette gives way to the sea's, computed again in every pass; the copper changes the colours there.

First met and defined in [chapter 2](part-1/amiga.md). The detail: [`re/notes/display.md`](repo:re/notes/display.md#the-split-line), "The split line".

### Sprite

One of the Amiga's eight small pictures that the hardware fetches through pointers of their own and draws over the bitplanes by itself; the game uses none and points all eight at zeros.

First met and defined in [chapter 11](part-2/display.md). The detail: [`re/notes/display.md`](repo:re/notes/display.md#memory), "Memory".

Elsewhere: [Sprite (computer graphics)](https://en.wikipedia.org/wiki/Sprite%5F(computer%5Fgraphics)), Wikipedia; [*Amiga Hardware Reference Manual*](https://archive.org/details/commodore-amiga-tech-ref-series-amiga-hardware-reference-manual-3rd-edition), 3rd edition, Internet Archive.

### Stack frame

A routine's own stretch of the stack, from its arguments down to its own variables, which `link a5` builds at the start of each compiled C routine of the game; A5 points into it, the first argument at `8(a5)`.

First met and defined in [chapter 3](part-1/disk.md). The detail: [`SPEC.md`](repo:SPEC.md#32-executable), section 3.2.

Elsewhere: [Call stack](https://en.wikipedia.org/wiki/Call%5Fstack), Wikipedia.

### Stand-in

A marked place in the port's C where the original has code the port does not carry; reaching it counts in the game's state, fails every comparison in a test build, and in the release build skips what it stands for.

First met and defined in [chapter 8](part-1/mission.md). The detail: [`SPEC.md`](repo:SPEC.md#74-working-method), section 7.4; [`re/notes/porting-m4.md`](repo:re/notes/porting-m4.md#what-stands-in-and-where), "What stands in, and where".

### Story scroller

The first screen of the front end: the game's story, drawn a line at a time in the game's font into a bitmap used as a ring, rising up the screen behind song 2.

First met and defined in [chapter 19](part-2/front-end.md). The detail: [`re/notes/frontend.md`](repo:re/notes/frontend.md#screen-by-screen), "Screen by screen"; [`re/notes/porting-m3.md`](repo:re/notes/porting-m3.md#the-story-scrollers-ring-and-its-ramps), "The story scroller's ring and its ramps".

### Stub

A substitute that answers for something a routine calls but that is not under test, such as a call into the operating system.

First met and defined in [chapter 5](part-1/oracle.md). The detail: [`tests/original.py`](repo:tests/original.py); [`re/notes/headless.md`](repo:re/notes/headless.md#the-stubs), "The stubs".

Elsewhere: [Test stub](https://en.wikipedia.org/wiki/Test%5Fstub), Wikipedia.

### Symbol

A name a program file keeps for a routine or a variable, with its address; the game's program keeps none, its music player twenty.

First met and defined in [chapter 3](part-1/disk.md). The detail: [`tools/hunk.py`](repo:tools/hunk.py); [`re/notes/music.md`](repo:re/notes/music.md#the-two-files), "The two files".

Elsewhere: [Symbol table](https://en.wikipedia.org/wiki/Symbol%5Ftable), Wikipedia.

### Ticker

The message line at the bottom of the play screen: one bitplane, 640 of its 672 pixels shown, scrolled a pixel every VBlank by the VBlank server while a message runs.

First met and defined in [chapter 11](part-2/display.md). The detail: [`re/notes/display.md`](repo:re/notes/display.md#the-play-screen-line-by-line), "The play screen line by line".

### Timer's latch

The 16-bit value a CIA's timer loads again each time it runs out, written a byte at a time; the songs write the music timer's high byte, and its low byte keeps its value from power-up; not the fire button's [latch](#latch).

First met and defined in [chapter 18](part-2/sound.md). The detail: [`re/notes/music.md`](repo:re/notes/music.md#the-timer), "The timer".

Elsewhere: [*Amiga Hardware Reference Manual*](https://archive.org/details/commodore-amiga-tech-ref-series-amiga-hardware-reference-manual-3rd-edition), 3rd edition, Internet Archive.

### Timer's tick

One run-out of the CIA timer the music player takes, at which the player runs its song routine once, every 14,592 counts of the E clock for four of the five songs; not the [logic tick](#logic-tick).

First met and defined in [chapter 18](part-2/sound.md). The detail: [`re/notes/music.md`](repo:re/notes/music.md#the-tick-songint), "The tick: SongInt".

### Title sequence

The routine that runs the story scroller and then three pictures at the program's start, each decoded out of sight, faded in, waited on and faded out.

First met and defined in [chapter 19](part-2/front-end.md). The detail: [`re/notes/frontend.md`](repo:re/notes/frontend.md#screen-by-screen), "Screen by screen"; [`src/front.c`](repo:src/front.c).

### Topaz 8

The Amiga's standard font, eight pixels high, in the Kickstart ROM; the game's dialogs for names and files show it, and the port reads it from the ROM when it is built.

First met and defined in [chapter 2](part-1/amiga.md). The detail: [`re/notes/system-font.md`](repo:re/notes/system-font.md).

### Torpedo plane

An enemy aircraft that the enemy's countdown sends against the carrier: it comes down low before the carrier's deck and drops a torpedo, which runs on in the sea into the carrier.

First met and defined in [chapter 16](part-2/enemy.md). The detail: [`re/notes/enemy.md`](repo:re/notes/enemy.md#what-each-state-and-mode-does-read-and-held-by-the-oracle-and-the-closed-loop), "What each state and mode does".

Elsewhere: [Torpedo bomber](https://en.wikipedia.org/wiki/Torpedo%5Fbomber), Wikipedia, the real kind.

### Track

One of a song's four lines of music, each on its own channel of Paula: a sequence of patterns played one after another.

First met and defined in [chapter 18](part-2/sound.md). The detail: [`re/notes/music.md`](repo:re/notes/music.md#the-song-format-wofsongss-data-hunk), "The song format".

### Two-step scaling

The shell's scaling of the picture: an enlargement by whole numbers with nearest neighbour, which makes every framebuffer pixel a block of equal size, then a smooth reduction to the box, so that the pixels stay crisp and even in the machine's proportions.

First met and defined in [chapter 23](part-3/shell.md). The detail: [`SPEC.md`](repo:SPEC.md#62-shell), section 6.2, "Video"; [`re/notes/page-video.md`](repo:re/notes/page-video.md#the-webgl-path), "The WebGL path".

Elsewhere: [Image scaling](https://en.wikipedia.org/wiki/Image%5Fscaling), Wikipedia.

### Upper word

The upper 16 bits of a 32-bit value; in a data register an instruction on a word leaves them as they were, so a value one routine leaves there reaches the next.

In memory a long's upper word comes first, so a word instruction at a long's address works on the upper word; an address register takes a word sign-extended, all 32 bits.

First met and defined in [chapter 9](part-1/wrong.md). The detail: [`SPEC.md`](repo:SPEC.md#71-arithmetic), section 7.1; [`re/notes/porting-m5.md`](repo:re/notes/porting-m5.md#registers-that-cross-a-call), "Registers that cross a call".

Elsewhere: [*M68000 Family Programmer's Reference Manual*](https://archive.org/details/m68000familyprog0000unse), Internet Archive.

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

### View

The game's record of one whole screen, 14 bytes: its copper list, its first viewport, its bitplanes; the game keeps two and shows one while it draws into the other.

First met and defined in [chapter 11](part-2/display.md). The detail: [`re/notes/display.md`](repo:re/notes/display.md#records), "Records".

Elsewhere: [*Amiga ROM Kernel Reference Manual: Libraries and Devices*](https://archive.org/details/amiga-rom-kernel-reference-manual-libraries-and-devices), Internet Archive, for the operating system's own View, which the game does without.

### Viewport

One area of a view, a band of the screen with its own size, mode, bitplanes and colour tables; each names the next one down, and the play screen has three.

First met and defined in [chapter 11](part-2/display.md). The detail: [`re/notes/display.md`](repo:re/notes/display.md#records), "Records".

Elsewhere: [*Amiga ROM Kernel Reference Manual: Libraries and Devices*](https://archive.org/details/amiga-rom-kernel-reference-manual-libraries-and-devices), Internet Archive, for the operating system's own ViewPort.

### Voice

An instrument of the song data: an IFF 8SVX sample, its one-shot and repeat parts, with settings for vibrato and arpeggio that every voice of the game leaves off.

First met and defined in [chapter 18](part-2/sound.md). The detail: [`re/notes/music.md`](repo:re/notes/music.md#the-song-format-wofsongss-data-hunk), "The song format".

Elsewhere: [8SVX](https://en.wikipedia.org/wiki/8SVX), Wikipedia.

### Wait point

A place where the program waits, for the next picture, for a time or for the music's fade to end; the headless original lets VBlanks happen there and nowhere else.

First met and defined in [chapter 6](part-1/headless.md). The detail: [`re/notes/headless.md`](repo:re/notes/headless.md#scheduling), "Scheduling".

Elsewhere: [Busy waiting](https://en.wikipedia.org/wiki/Busy%5Fwaiting), Wikipedia.

### Water line

The sea's surface in a mission's world, where world y is zero; at full scale it lies 11 rows below the horizon's row.

First met and defined in [chapter 13](part-2/world.md). The detail: [`re/notes/map.md`](repo:re/notes/map.md#world-coordinates), "World coordinates".

### WebAssembly

A compact binary form of program that every current browser runs: the form the port's core is compiled to.

WebAssembly is a compact binary form of program with an instruction set of its own, which every current browser runs at close to native speed inside a sandbox: the program gets one block of memory to itself and reaches nothing of the page but what the page hands it. The port's core is its C compiled to WebAssembly; the build carries the bytes inside the HTML file, and the page instantiates them when it loads, with the JavaScript shell around them ([`SPEC.md`](repo:SPEC.md), sections [1](repo:SPEC.md#1-goal), [5](repo:SPEC.md#5-build) and [6.1](repo:SPEC.md#61-core)). It is not JavaScript: the two run side by side, and the shell calls the functions the core exports. The reference is [the WebAssembly specification](https://webassembly.github.io/spec/core/).

First met and defined in [chapter 1](part-1/faithful.md). The detail: [`SPEC.md`](repo:SPEC.md#5-build), section 5.

Elsewhere: [WebAssembly](https://en.wikipedia.org/wiki/WebAssembly), Wikipedia; [webassembly.org](https://webassembly.org/).

### Won flag

The word that only `mission_won` sets when a mission is won; once the next aircraft stands in the hold, the game goes on to the next mission.

First met and defined in [chapter 17](part-2/campaign.md). The detail: [`re/notes/campaign.md`](repo:re/notes/campaign.md#a-mission-won), "A mission won", and ["The next mission"](repo:re/notes/campaign.md#the-next-mission).

### Word masks

The blitter's two masks for the first and the last word of every row of its source A; with the shift they blank the columns outside a shape's box and outside the clip.

First met and defined in [chapter 12](part-2/shapes.md). The detail: [`re/notes/porting-m1.md`](repo:re/notes/porting-m1.md#the-blit-is-per-pixel-and-why), "The blit is per-pixel, and why".

Elsewhere: [*Amiga Hardware Reference Manual*](https://archive.org/details/commodore-amiga-tech-ref-series-amiga-hardware-reference-manual-3rd-edition), 3rd edition, Internet Archive.

### Workbench

The Amiga's desktop, which the game closes when it starts.

First met in [chapter 1](part-1/faithful.md), defined in [chapter 2](part-1/amiga.md). The detail: [`SPEC.md`](repo:SPEC.md#34-operating-system-and-hardware-use), section 3.4.

Elsewhere: [Workbench (AmigaOS)](https://en.wikipedia.org/wiki/Workbench%5F(AmigaOS)), Wikipedia.

### Worker

A session that does the tasks the controller sends it, one at a time, each a milestone or a bounded part of one, on a branch of its own, and reports to the controller alone.

First met and defined in [chapter 10](part-1/making.md). The detail: [`CLAUDE.md`](repo:CLAUDE.md#session-protocol), "Session protocol"; [`CONTROLLER.md`](repo:CONTROLLER.md#what-a-task-contains), "What a task contains".

### World coordinates

Positions in a mission's world: x in pixels from the map's west end, eight to a map record, and y in pixels upward from the [water line](#water-line).

First met and defined in [chapter 13](part-2/world.md). The detail: [`re/notes/map.md`](repo:re/notes/map.md#world-coordinates), "World coordinates".

### Wreck's word

The word an enemy aircraft burnt out on land leaves in a list of forty, its x, negative when it faced west, by which the pass draws its wreck; it is written by the list's count, whatever the count.

First met and defined in [chapter 16](part-2/enemy.md). The detail: [`re/notes/enemy.md`](repo:re/notes/enemy.md#shot-down-and-what-it-scores), "Shot down, and what it scores".
