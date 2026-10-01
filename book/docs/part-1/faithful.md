Chapter 1
{ .chapter-kicker }

# What faithful means

This book is about a port of Wings of Fury, Broderbund's Amiga game of 1990, to the browser, and about the word that carries most of the weight in its description: faithful. By the end of this chapter you will know what a faithful port is and how it differs from an emulator, an FPGA recreation and a remake, what the word promises in three parts, and why the result is a single HTML file. You will also know what was left out of the game and what was changed on purpose, and, in outline, which instruments hold the port to the original; most of them have a chapter of their own in Part I.

## Three ways to keep a game

Retro preservation has two established ways of keeping an old computer's games playable.

The first is the [**emulator**](../glossary.md#emulator): a program that imitates the old computer, its processor and its chips, closely enough that the game's original program runs on it unchanged. You play the game as its authors shipped it, on a machine that exists only as software.

The second is the [**FPGA recreation**](../glossary.md#fpga-recreation): the old computer rebuilt in programmable hardware, a chip whose circuits can be configured to behave like the original machine's. The Amiga cores for the MEGA65 and the MiSTer are of this kind. Here too the game's original program runs unchanged, on a machine that is real again.

Both keep the machine, and the game comes with it; neither changes a byte of the game.

A [**remake**](../glossary.md#remake) goes the other way. It is a new program, made to look and play like the old one, written from watching the old one. However well it is made, its code is new, and what it does is what its makers saw the original do.

This book tells of a third way, tried here for one game, and it is not a remake. It is a [**faithful port**](../glossary.md#faithful-port): one game carried from its original machine to another by rewriting its own logic, routine by routine, from the original program's [machine code](../glossary.md#machine-code), and held to the original by comparison. It preserves one game rather than the machine. The game's logic was taken out of the original executable's [68000](../glossary.md#68000) machine code and rewritten in C, and every picture, map, sound and table is read from the original disk. What runs in your browser is not an imitation of an Amiga. It is the game, carried over into a form today's computers run natively.

![Three columns side by side. An emulator runs the original program, unchanged, on an Amiga recreated in a program on your computer, and keeps the machine. An FPGA recreation runs the original program, unchanged, on an Amiga recreated in programmable hardware, and keeps the machine. A faithful port runs the game's own logic, rewritten routine by routine with its data from the disk, in a small shell for screen, sound and keys, in your browser, and keeps the game.](../figures/three-ways.svg)

/// caption
Three ways to keep an Amiga game, and what each one keeps.
///

The faithful port keeps the work of art without keeping the machine. It is also the one way of the three that leaves the game readable: the port's source, the notes on how every part of the game works, and the proof that the port behaves as the original does are all in the repository, [`github.com/sy2002/wof-wasm`](repo:), where this book lives too.

"Routine by routine" is meant literally. The original program is one file of 94,292 bytes, and its machine code falls into 616 routines, 223 of them compiled from C and the rest written in [assembly language](../glossary.md#assembly-language). Every routine the game runs was read, named and rewritten in C, and carries the address of its original, so that the port's C and the original's assembly can be laid side by side. The rest, dead code and the Amiga's own machinery, was left, and chapter 8 tells how we knew which is which. The port is not a reconstruction of what the game seems to do; it is a translation of what its code does.

## The definition, in three parts

Faithful is a strong word, so we pin it down in three parts, each of which can be checked.

### Logic, tick for tick

The game does not move its world continuously. It moves it in steps, [**logic ticks**](../glossary.md#logic-tick): one step of the game's simulation, in which its aircraft, bombs and ships move on. On a European Amiga there are 12.5 of them a second, on the American machines the game was designed for, 15. The difference comes from the television standards. A [**PAL**](../glossary.md#pal) machine, the European kind, draws its picture 50 times a second, an NTSC machine 60 times, and the game takes one tick for every four of those pictures. The program never asks which kind of machine it runs on; on PAL everything simply runs at five sixths of the speed.

For every tick the game takes one [**input sample**](../glossary.md#input-sample): it reads the stick and the button into one [**input byte**](../glossary.md#input-byte), four bits for the stick's directions and two for the button, held or tapped. That byte is the only way the stick and the button reach the game's logic. The keyboard is a second way in, through the game's own key handler, for the commands.

The first part of the definition says: give the port and the original the same start, the same input bytes and the same keys, and after every logic tick the two hold the same game state. Not a similar state; the same values.

There is one more input, and it is easy to overlook: chance. The game's only source of random numbers reads where the [beam](../glossary.md#beam) that draws the picture on the screen happens to be at the moment of asking. On the real machine that depends on exactly how long the code took to get there. The port replaces the beam by a stream of values that can be reproduced, and whenever the port is compared with the original, both are given the same stream. With that, the game becomes, in a precise sense, a function: of its start, its inputs and its random stream, and of the rhythm of its ticks and pictures, which comes at the end of this section. That is what makes a faithful port checkable at all.

The arithmetic is held to the same standard. The game computes its flight model in [**fast floating point**](../glossary.md#fast-floating-point), Motorola's number format of 32 bits, whose routines live in the Amiga's ROM. A browser computes in another format, which rounds differently, and the game's state would drift away from the original's; so the port does the same arithmetic in integer code, bit for bit, and its nine operations are tested against the ROM's own routines.

### The same pixels and the same palette

The second part is about the picture. The Amiga does not store a colour for every pixel. It stores a number, and a [**palette**](../glossary.md#palette) turns each number into a colour: a table of up to 32 entries, each one of 4,096 possible colours.

The definition says: for the same game state, the port's picture holds the same number in every pixel and the same palette as the original's. The game changes the palette part of the way down the screen: the sky above the horizon is drawn through one palette, the sea below it through another, the dashboard at the bottom through a third, and the message line under the dashboard through a ramp of its own. So the port keeps a palette for every row of its picture.

![The first mission as the port draws it: the carrier's deck with its tower under a blue sky, the weapon menu at the top right, the sea, and the dashboard with its gauges at the bottom.](../generated/figures/mission-start.png)

/// caption
The first mission, as the port draws it from the game's data: every pixel a number, every row through its own palette, the whole shown in the shape a PAL display gives it.
///

The picture is shown as a PAL screen showed it. A pixel of a PAL Amiga is not square, and the port never pretends it is: the picture's 640 by 214 pixels are shown in the proportions a PAL screen gave them, 1024 to 642, scaled so that every pixel stays sharp and evenly sized. PAL is the port's default for three reasons: this disk comes from a PAL country, the extra pictures it carries are of PAL height, and the real Amiga the port was compared with is a PAL machine.

### The same sounds at the same moments

The third part is about sound. The Amiga plays its sounds as [**sound samples**](../glossary.md#sound-sample): recorded waveforms that its sound chip plays back on one of four channels, each at its own pitch and volume. The definition says: the port starts the same sound sample on the same channel in the same tick, at the same pitch and the same volume, as the original; and its music keeps the timing of the original's music player. The sound effects and the music are not new recordings. They are the game's own sound samples, played by the game's own sound engine and music player, ported with the rest.

### The rhythm of ticks and pictures

Each of the three parts compares the port with the original in the same situation. What they do not fix is the rhythm in which situations follow each other. The game draws its pictures in [**passes**](../glossary.md#pass): a pass is one round of the inner loop, the loop that plays a mission, which draws one picture and runs the part of the logic that goes by pictures; the soldiers on the islands, for one, move once a pass.

A tick comes every fourth [VBlank](../glossary.md#vblank), the moment the display has finished one of its 50 pictures a second. A pass takes as many VBlanks as the machine needs for its work, and on a real PAL Amiga that is two in a quiet scene, which we measured by filming the machine at 240 frames a second. So two passes go to a tick: the simulation moves per tick, while each pass draws and runs its own part. In a busy scene the original may need three VBlanks for a pass; that was not filmed, and the port keeps two.

## One file in the browser

The port is a single HTML file. You open it with a double click, and the game is there, behind its help screen until the first key. It needs no installation, no emulator, no disk to boot and no settings, and it asks the network for nothing. Every picture, map, sound, piece of music, table and text of the game, and the game's own font, comes from the original disk when the file is built and goes inside it: 55 of the disk's files, in their original formats, together with the port's code. The whole file is about 1.2 megabytes. It runs in Chrome, Firefox and Safari; the tests drive Chrome and Firefox. You can play it on this site's page [Play the game](../play.md); the file itself is [`dist/wof.html`](repo:dist/wof.html) in the repository.

Two layers make it up. The [**core**](../glossary.md#core) is the game: the ported logic, written in C and compiled to [**WebAssembly**](../glossary.md#webassembly), a compact binary form of program that every current browser runs. The [**shell**](../glossary.md#shell) is a thin layer of JavaScript around the core: the clock that paces it, a screen, a loudspeaker for the sound the core mixes, a keyboard, a place for saved games, and a few things around the game, listed below.

Code and content are kept strictly apart. The port's sources hold code only: every table, name list and text the game needs is read from the original executable when the file is built, and the system font and the key table from the Amiga's ROM. Nothing of the game was typed in again by hand.

## What was left out

The disk the port was made from is not quite the disk Broderbund sold. Its executable carries a [**crack**](../glossary.md#crack): a change made to a program to remove its copy protection. The game's logic is the retail code; the crack disabled the protection check, added a text screen of its own to the executable and overwrote two picture files. Two things are left out of the port, and one is missing from the disk.

- **The copy protection.** The original checked that its player owned the printed manual, by asking for something only the manual could answer. On this disk the crack had already disabled the check, and the port does not bring it back.
- **The crack's own additions.** The crack's intro and the text screen it put into the executable are dropped; the picture files it overwrote are shown as the disk holds them.
- **The publisher's logo**, which this disk does not carry. The first picture of the title sequence should be Broderbund's; the crack replaced it with a picture of its own, and put its copyright line of 1992 along the bottom edge of the game's title picture. So the port's title sequence opens with the crack's picture.

![The first picture of the title sequence on this disk: blue lettering on black over a grey bar, the crack group's picture in place of the publisher's logo.](../generated/figures/title-logo.png)

/// caption
The first picture of the title sequence, as this disk carries it: the crack's picture, where the publisher's logo once was.
///

/// wrong
The file of the first picture is called `broderbund`, and we expected the publisher's logo in it. The picture decoder, compared with the original's own decoder on every picture file of the disk, showed the crack's picture instead, and the crack's copyright on the title. The lesson stayed with us: the data decides, not the name.
///

A few things are left out for a plainer reason: a browser has no use for them. The original starts up its C runtime, closes the [Workbench](../glossary.md#workbench), plumbs its [interrupts](../glossary.md#interrupt), builds the lists for the [copper](../glossary.md#copper) that change the colours down the screen, and carries a debug reporter and a crash reporter. None of that is ported; the copper lists' effect is kept through the palette for every row. The operating system's services the game does need, the port replaces with small equivalents of its own: a file system over the disk's files, an allocator for its memory, and the ROM's key table, taken at build time.

## What was changed on purpose

Everything else is the original, its own defects included. What follows is every change a player can meet; the defects, and the few departures only the code shows, are told where they belong, in chapters 17, 20 and 23.

### The keys

The original takes its commands from the keyboard. Escape pauses, and the Control key with a letter restarts the game, clears the high scores, flips the vertical control, saves and loads; Control with S switches the music and is not in the manual. The manual for its part promises Control with D for the list of high scores, which this version of the program does not have. A browser keeps Control with R, F and L for itself (reload, find, the address bar), and a page cannot stop it from taking all of them. So the port gives each command a plain letter:

| Key | What it does | The original's key |
|---|---|---|
| the arrow keys, or W, A, S, D | the stick | the joystick |
| Space | fire | the joystick's button |
| Enter | chooses in a menu, as fire does | Return |
| P, or Escape | pause and continue | Escape |
| V | the vertical flip | Control-F |
| G | save, on the carrier only, as in the original | Control-G |
| L | load | Control-L |
| M | music off and on, in flight; silences the effects too | Control-S |
| R | restart, while paused or in the briefing | Control-R |
| C | clear the high scores, while paused | Control-C |
| H | the help screen | none |
| F | fullscreen | none |

R and C act only while the game is paused, R in the briefing as well, because without the Control key in front of them a stray press could throw a whole campaign away; the original accepts both while paused, so this narrows it and adds nothing. No key of the game is ever put on Control, Alt or Command: with Control as fire and W as up, firing while climbing would be Control with W, which closes the browser's tab. The port takes the keys by their position on the keyboard, as the Amiga did, so this book names a key by its place where keyboards differ, such as the key left of 1.

Inside the core, each command letter becomes the original's own Control code, so that the original's key handling sees what it saw on the Amiga. Nothing the manual describes is lost. One thing outside it is: a cheat sequence hidden in the program, no part of the game the manual describes, can no longer be typed, because letters it needs are commands now.

### The keyboard assist

The original was made for a joystick, which you hold, and a key is something you tap. In two places that matters. In the weapon menu in the carrier's hold, a step costs three input samples: the menu steps on one and ignores the next two. So on a keyboard one step takes two or three presses, and with the vertical flip on, up on the key moves the menu down. In flight, a tap shorter than four VBlanks can fall between two input samples and be lost.

The [**keyboard assist**](../glossary.md#keyboard-assist) smooths both. In the weapon menu one press is one step, the right way up whatever the flip says; everywhere else a short tap reaches the game exactly once, and never more often than a joystick held for that long would. The flying stays the original's. The assist is a switch in the core that the page turns on.

### The remembered flip

By default, pushing the stick forward makes the aircraft climb. That is how the game reads the joystick, and the manual's instructions for the take-off (page 5) say the same. For players who want a pilot's stick the game has a command: the [**vertical flip**](../glossary.md#vertical-flip), which swaps forward and back.

In the original the flip is part of the game's state. It starts off every time the program starts, a restart keeps it, and loading a saved game sets it to whatever the saved game held, so that a game saved without the flip switches it off under a player who flies with it. The project's owner is such a player, and so the port treats the flip as a preference: the browser remembers it, and the remembered value wins over a loaded game. A core that has not been given the preference behaves exactly as the original, and that is how every comparison runs.

### What the shell adds

Three things the original does not have at all come from the shell, around the game rather than in it.

- **The help screen**, on H, lists the port's keys in the player's words. It is up when the page opens, because a browser starts sound only after the player has pressed a key or clicked, and the first key or click starts the sound and takes the help screen away.
- **The pause sign**, shown over the picture while a mission is paused, whatever asked for the pause. The shell also pauses a mission when fullscreen is left, and when the page comes back from an absence of a second or more.
- **Fullscreen**, on F.

/// know
The changes stay out of what is compared. In a comparison the assist is off, and the flip preference is never handed to the core; the game's own flip command is exercised in several of the compared runs, as the original has it. With the assist off, [`tests/test_assist.py`](repo:tests/test%5Fassist.py) repeats the original's own table of taps and menu steps. And every letter the port takes was checked against every place the program reads the keyboard. The command letters are turned into the original's own Control codes. Of the three plain letters the shell and the port keep, H, F and V, none means anything to the game outside the line editor, where a name or a file name is typed and they are letters again, except F as a debug key behind the cheat sequence, which is lost anyway.
///

/// dev
The layer that turns the port's command letters into the original's codes is [`src/portkeys.c`](repo:src/portkeys.c). The shell's own keys are in [`web/main.js`](repo:web/main.js): H, F, and the key left of 1, which opens the shell's diagnostics overlay and never reaches the game. The assist is [`src/assist.c`](repo:src/assist.c). Every rule is in [`SPEC.md`](repo:SPEC.md#62-shell), section 6.2, "Input", and [`re/notes/keys.md`](repo:re/notes/keys.md), whose ["The five readers"](repo:re/notes/keys.md#the-five-readers) lists every place the program reads the keyboard.
///

## How we know, in brief

The emulator is not what you play, but it is how the port was measured: the original runs beside it under emulation. A definition is worth what checks it, and these are the instruments, in outline.

- [**The oracle.**](../glossary.md#oracle) An original routine runs on an emulated 68000 processor beside its port, on the same inputs, often thousands of random ones (the colour arithmetic of a fade, for one, on 20,000), and the results must be equal. Every [**pure routine**](../glossary.md#pure-routine), one that computes from its inputs alone, has to pass it before it counts as verified. The suite holds more than three hundred oracle tests.
- [**The headless original.**](../glossary.md#headless-original) The original program, from its `main` routine on, runs under emulation without a screen: the operating system's calls answered by stubs, nothing drawn, and the beam's position served from the same random stream the port uses. The ROM's own floating point and key conversion and the game's music player run for real. None of the game's logic is rewritten for it.
- **The comparisons.** The port and the headless original play the same mission from the same input bytes and the same keys, and are compared after every tick and every pass: every game variable and table the port keeps as the game's state, every drawing call with its arguments, every random number drawn and the routine that drew it, the palette of every row. One way of comparing sets the port to the original's state before each pass, so that a difference points at its pass; the other lets the port run alone from the program's start, as it runs in your browser. A completeness test demands that every place in memory the original writes during a mission is compared, or listed with the reason why not.
- **The missions** are flown by [**mission scripts**](../glossary.md#mission-script), recorded sequences of stick and key inputs that fly a mission the same way every time: sixty of them on all fifteen maps, eight more runs of loaded games and of the game's [**attract demo**](../glossary.md#attract-demo), a recorded game it plays by itself when left alone, and twenty-one runs of the keyboard commands in flight and while paused, two of them without a key as controls. The title sequence and the menus are compared VBlank by VBlank.
- **The sound event log.** Every sound sample started, by the port and by the original, with its channel, pitch and volume, compared after every tick and every pass of every mission script.
- **The replay.** A demo recorded by the port is played back in the native build, the port compiled for the test machine itself outside the browser, and in WebAssembly, against a fingerprint of the whole game state after every input sample.
- **The page.** The finished file is opened in Chrome and Firefox and played through the browsers' own drivers, the remote control a browser offers to tests, with real key presses, and checked for its pixels, its display, its timing and its sound.

Together they are about nine hundred tests.

What the instruments do not see belongs to the definition too. The headless original draws nothing, so no whole mission scene is compared pixel by pixel; the drawing calls and the palette of every row stand for it. What is compared pixel by pixel is every single shape. Each is drawn by the original's own routine through a model of the Amiga's [blitter](../glossary.md#blitter), the chip that does the drawing, and compared with the port's picture. That model is built from the chip's documentation, not derived from the original.

Four things rest on documented behaviour, or on the eye and ear of the project's owner, rather than on a comparison:

- The rhythm of a busy scene was not filmed. The port keeps two VBlanks a pass, and it plays right.
- How long a step of a fade between two pictures takes is processor time in the original, which the [listing](../glossary.md#listing), the original's instructions written out, cannot tell. The port sets it to two VBlanks, and the fades were found right by eye.
- The tempo of the music rests on the value one [register](../glossary.md#register) of the timer holds when the machine is switched on. Every song was heard and found right.
- The order in which a directory lists its files decides the order of the saved games in the load dialog. The Amiga's documentation describes it, and neither a run nor the disk has confirmed it.

Chapters 7, 18 and 20 give the detail.

## What comes next

This chapter has used a handful of Amiga words without explaining them: the VBlank, the copper, the blitter, the palette that changes down the screen. Chapter 2 takes twenty minutes to explain the machine the game was written for, the 68000 processor, chip memory, bitplanes, the copper, the blitter, Paula and the VBlank, and the little of AmigaOS the game uses: only what the port needed, so that the next chapters can be read without the deep dives that come later in the book.

## Further reading

The files named here are in the repository, [`github.com/sy2002/wof-wasm`](repo:).

- [`SPEC.md`](repo:SPEC.md), section 1: ["Goal"](repo:SPEC.md#1-goal), ["Definition of faithful"](repo:SPEC.md#definition-of-faithful) and ["Out of scope"](repo:SPEC.md#out-of-scope-for-this-specification).
- [`SPEC.md`](repo:SPEC.md), section 3.1, ["Disk"](repo:SPEC.md#31-disk), and 3.3, ["Runtime model"](repo:SPEC.md#33-runtime-model).
- [`SPEC.md`](repo:SPEC.md), section 6.2, ["Shell"](repo:SPEC.md#62-shell): "Video" and "Input"; 6.3, ["Blocking code becomes coroutines"](repo:SPEC.md#63-blocking-code-becomes-coroutines); 6.5, ["Audio model"](repo:SPEC.md#65-audio-model).
- [`SPEC.md`](repo:SPEC.md#8-verification), section 8, "Verification".
- [`README.md`](repo:README.md#amiga-to-web), "Amiga to Web".
- [`re/notes/keys.md`](repo:re/notes/keys.md), ["The commands"](repo:re/notes/keys.md#the-commands) and ["The vertical flip, and how long it lasts"](repo:re/notes/keys.md#the-vertical-flip-and-how-long-it-lasts).
- [`re/notes/porting-m4.md`](repo:re/notes/porting-m4.md#the-keyboard-assist), "The keyboard assist".
- [`re/notes/porting-m1.md`](repo:re/notes/porting-m1.md#findings), "Findings".
- [`re/notes/passes.md`](repo:re/notes/passes.md#what-the-film-of-the-real-machine-shows), "What the film of the real machine shows".
