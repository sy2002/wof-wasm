Chapter 1
{ .chapter-kicker }

# What faithful means

This book is about a port of Wings of Fury, Broderbund's Amiga game of 1990, to the browser, and about the one word that carries most of the weight in its description: faithful. By the end of this chapter you will know what a faithful port is and how it differs from an emulator, an FPGA recreation and a remake; the three things the word promises, and how each of them can be checked; why the result is a single HTML file; what was left out of the game and what was changed on purpose, each with its reason; and, in outline, the instruments that hold the port to the original, each of which has a chapter of its own later in Part I.

## Three ways to keep a game

Retro preservation has two established ways of keeping an old computer's games playable once the machines wear out.

The first is the **emulator**: a program that imitates the old computer, its processor and its chips, closely enough that the game's original program runs on it unchanged. You take an image of the game's disk, start the emulator, and play the game as its authors shipped it, on a machine that exists only as software.

The second is the **FPGA recreation**: the old computer rebuilt in programmable hardware, a chip whose circuits can be configured to behave like the original machine's. The Amiga cores for the MEGA65 and the MiSTer are of this kind. Here too the game's original program runs unchanged, on a machine that is real again.

Both keep the machine, and the game comes with it. Neither changes a byte of the game.

A **remake** goes the other way. It is a new program, made to look and play like the old one, written from watching the old one. However well it is made, its code is new, and what it does is what its makers saw the original do.

This project is a third breed beside the emulator and the FPGA recreation, and it is not a remake. It is a **faithful port**: one game carried from its original machine to another by rewriting its own logic, routine by routine, from the original program's machine code, and held to the original by comparison. It preserves one game rather than the machine. The game's logic was taken out of the original executable's 68000 machine code and rewritten in C, and every picture, map, sound and table is read from the original disk. What runs in your browser is not an imitation of an Amiga. It is the game, carried over into a form today's computers run natively.

![Three columns side by side. An emulator runs the original program, unchanged, on an Amiga recreated in a program on your computer, and keeps the machine. An FPGA recreation runs the original program, unchanged, on an Amiga recreated in programmable hardware, and keeps the machine. A faithful port runs the game's own logic, rewritten routine by routine with its data from the disk, in a small shell for screen, sound and keys, in your browser, and keeps the game.](../figures/three-ways.svg)

/// caption
Three ways to keep an Amiga game, and what each one keeps.
///

The difference shows in what each way keeps. The emulator and the FPGA recreation keep the machine, and the game along with it. The faithful port keeps the work of art without keeping the machine. It is also the one way of the three that leaves the game readable: the port's source, the notes on how every part of the game works, and the proof that the port behaves as the original does are all in the repository, for whoever comes after.

"Routine by routine" is meant literally. The original program is one file of 94,292 bytes, and its machine code falls into 616 routines: 223 of them compiled from C, the rest written in assembly language. One routine at a time, that code was read, given names and rewritten in C, and every routine the port carries names the address of its original, so that the port's C and the original's assembly can be laid side by side. The port is not a reconstruction of what the game seems to do; it is a translation of what its code does. Chapter 4 shows how the executable was read, and chapter 5 how a single routine is compared with its port.

## The definition, in three parts

Faithful is a strong word, so the project pins it down in three parts, each of which can be checked.

### Logic, tick for tick

The game does not move its world continuously. It moves it in steps, **logic ticks**: one step of the game's simulation, in which its aircraft, bombs and ships move on. On a European Amiga there are 12.5 of them a second, on the American machines the game was designed for, 15. The difference comes from the television standards. A **PAL** machine, the European kind, draws its picture 50 times a second, an NTSC machine 60 times, and the game takes one tick for every four of those pictures. The program never asks which kind of machine it runs on; on PAL everything simply runs at five sixths of the speed.

For every tick the game takes one **input sample**: it reads the player's controls into one **input byte**, four bits for the stick's directions and two for the button, held or tapped. That byte is the only way the controls reach the game's logic.

The first part of the definition says: give the port and the original the same start and the same stream of input bytes, and after every logic tick the two hold the same game state. Not a similar state; the same values.

There is one more input, and it is easy to overlook: chance. The game's only source of random numbers reads where the beam that draws the picture on the screen happens to be at the moment of asking. On the real machine that depends on exactly how long the code took to get there. The port replaces the beam by a stream of values that can be reproduced, and whenever the port is compared with the original, both are given the same stream. With that, the game becomes, in a precise sense, a function: of its start, its input bytes and its random stream, and of one more thing, the timing between its steps and its drawing, which chapter 7 takes apart. That is what makes a faithful port checkable at all.

Even the arithmetic is held to it. The game computes its flight model in Motorola's fast floating point, a number format whose routines live in the Amiga's ROM. The port does the same arithmetic in integer code, bit for bit, and its nine operations are tested against the ROM's own routines.

### The same pixels and the same palette

The second part is about the picture. The Amiga does not store a colour for every pixel. It stores a number, and a **palette** turns each number into a colour: a table of up to 32 entries, each one of 4,096 possible colours. The game changes palettes part of the way down the screen: the sky above the horizon is drawn through one palette, the sea below it through another, the dashboard at the bottom through a third. So the port keeps a palette for every row of its picture.

The definition says: for the same game state, the port's picture holds the same number in every pixel, and the same palette for every row, as the original's.

![The first mission as the port draws it: the carrier's deck with its tower under a blue sky, the weapon menu at the top right, the sea, and the dashboard with its gauges at the bottom.](../generated/figures/mission-start.png)

/// caption
The first mission, as the port draws it from the game's data: every pixel a number, every row through its own palette, the whole shown in the shape a PAL display gives it.
///

The picture is shown as a PAL screen showed it. A pixel of a PAL Amiga is not square, and the port never pretends it is: the picture is shown in a box of 1024 to 642, and scaled so that every pixel stays sharp and evenly sized. PAL, not NTSC, is the port's default, for three reasons: this disk comes from a PAL country, the pictures added to it are 256 lines high, which is a PAL height, and the real Amiga the port was compared with is a PAL machine.

### The same sounds at the same moments

The third part is about sound. The Amiga plays its sounds as **sound samples**: recorded waveforms that its sound chip plays back on one of four channels, each at its own pitch and volume. The definition says: the port starts the same sound sample on the same channel in the same tick, at the same pitch and the same volume, as the original; and its music keeps the timing of the original's music player. The sound effects and the music are not new recordings. They are the game's own sound samples, played by the game's own sound engine and music player, ported with the rest.

### What the three parts leave open

Each of the three parts compares the port with the original in the same situation. What they do not say by themselves is how quickly the situations follow each other. The game draws its pictures in **passes**: a pass is one round of the game's main loop, which draws one picture and, as it turns out, runs part of the game's logic as well. How many of the display's 50 pictures a second, its [VBlanks](../glossary.md#vblank), a pass takes on a real Amiga decides how the game feels, and it is not written in the program: on a real machine a pass simply takes longer than one VBlank. We measured it by filming a real PAL Amiga at 240 frames a second: two VBlanks a pass, in a quiet scene. The port takes that number. Chapter 7 tells how.

## One file in the browser

The port is a single HTML file. You open it with a double click and the game starts. It needs no installation, no emulator, no disk to boot and no settings, and it asks the network for nothing. Every picture, map, sound, piece of music, table and text of the game, and the game's own font, comes from the original disk when the file is built, and goes inside it: 55 of the disk's files, in their original formats, together with the port's code. The whole file is about 1.1 megabytes, and it runs in Chrome, Firefox and Safari from the file itself.

Two layers make it up. The **core** is the game: the ported logic, written in C and compiled to **WebAssembly**, a compact binary form of program that every current browser runs. The **shell** is a thin layer of JavaScript around the core that gives it a screen, a sound chip, a keyboard and a place to keep saved games, and nothing else.

Code and content are kept strictly apart. The port's sources hold code only; every table, name list and text the game needs is read from the original executable when the file is built. Nothing of the game was typed in again by hand.

## What was left out

The disk the port was made from is not quite the disk Broderbund sold. Its executable carries a **crack**: a change made to a program to remove its copy protection. The game's logic is the retail code; the crack disabled the protection check and added a text screen of its own to the executable. Three things of that kind are left out of the port.

- **The copy protection.** The original checked that its player owned the printed manual, by asking for something only the manual could answer. On this disk the crack had already disabled the check, and the port does not bring it back.
- **The crack's own additions:** its intro and the text screen it put into the executable. The port begins with the game.
- **The publisher's logo.** The first picture of the title sequence should be Broderbund's. On this disk it is not, because the crack replaced the artwork: the file for the first picture and the file for the title both carry the crack group's own pictures, dated 1992. The port shows what the files on the disk hold, so its title sequence opens with the crack's picture.

![The first picture of the title sequence on this disk: blue lettering on black over a grey bar, the crack group's picture in place of the publisher's logo.](../generated/figures/title-logo.png)

/// caption
The first picture of the title sequence, as this disk carries it: the crack's picture, where the publisher's logo once was.
///

/// wrong
The specification first called the first picture of the title sequence the publisher's logo; its file is called `broderbund`. The picture decoder, ported in the first milestone and compared with the original's own decoder on every picture file of the disk, showed something else: the crack's picture, and the crack's copyright on the title as well. The port shows what the file holds, and the specification now says what the disk carries.
///

A few things are left out for a plainer reason: a browser has no use for them. The original starts up its C runtime, talks to the operating system, manages its memory, closes the Workbench, builds the lists for the [copper](../glossary.md#copper) that change the colours down the screen, plumbs its interrupts, and carries a debug and a crash reporter. None of that is ported. The effect of the copper lists is kept, through the palette for every row; the rest is the machinery the Amiga needed and a page does not.

## What was changed on purpose

Everything else is the original. A short list of things was changed on purpose, each for a reason, and each kept out of the way of the comparisons.

### The keys

The original takes its commands from the keyboard. Escape pauses, and the Control key with a letter restarts the game, clears the high scores, flips the vertical control, saves and loads; one more, Control with S, switches the music off and on, and is not in the manual. The manual for its part promises Control with D for the list of high scores, which this version of the program does not have. In a browser the Control commands cannot stay as they are: the browser keeps Control with R, F and L for itself (reload, find, the address bar), and a page cannot stop it from taking them.

So the port gives each command a plain letter. P pauses and continues, and Escape does too; V flips the vertical control; G saves, on the carrier only, as in the original; L loads; M switches the music, which in the original silences the sound effects as well. R restarts and C clears the high scores, and both act only while the game is paused, because without the Control key in front of them a stray press could throw a whole campaign away; the original accepts both while paused too, so this narrows what it allows and adds nothing. The stick is the arrow keys, or W, A, S and D, and the one fire key is Space. No key of the game is ever put on Control, Alt or Command: with Control as fire and W as up, firing while climbing would be Control with W, which closes the browser's tab.

The port takes the keys by where they are on the keyboard, not by the letter printed on them, as the Amiga did; so this book names a key by its place where keyboards differ, such as the key left of 1. Inside the core, each of the port's keys is turned back into the key code, Control included, that the original's own key handling expects, so that the original's code sees exactly what it would have seen on the Amiga. Nothing the manual describes is lost. What is lost lies outside it: a cheat sequence hidden in the program can no longer be typed, because one of its letters is now the load command, and the project decided to leave it so.

### The keyboard assist

The original was made for a joystick, which you hold, and a key is something you tap. In two places that matters. In the weapon menu in the carrier's hold, the original takes a step only after three input samples, so that on a keyboard one step takes two or three presses, and with the vertical flip on, up on the key moves the menu down. In flight, a tap shorter than four VBlanks can fall between two input samples and be lost.

The **keyboard assist** smooths both. In the weapon menu one press is one step, the right way up whatever the flip says; in flight a short tap reaches the game exactly once, and never more often than a joystick held for that long would. The flying itself stays the original's. The assist is a switch in the core that the page turns on; it is off in the core by default and in every comparison with the original.

### The remembered flip

By default, pushing the stick forward makes the aircraft climb. That is how the game reads the joystick, and the manual's instructions for the take-off (page 5) say the same. For players who want a pilot's stick the game has a command: the **vertical flip**, which swaps forward and back.

In the original the flip is part of the game's state. It starts off every time the program starts, a restart keeps it, and loading a saved game sets it to whatever the saved game held, so that a game saved without the flip switches it off under a player who flies with it. The project's owner is such a player, and so the port treats the flip as a preference: the browser remembers it, and the remembered value wins over a loaded game. A core that has not been given the preference behaves exactly as the original, and that is how every comparison runs.

### What the shell adds

Three things the original does not have at all come from the shell, around the game rather than in it.

- **The help screen**, on H, lists the port's keys in the player's words. It is up when the page opens, because a browser starts sound only after the player has pressed a key or clicked, and the first key or click starts the sound and takes the help screen away.
- **The pause sign**, shown over the picture while a mission is paused, whatever asked for the pause. The shell also pauses a mission when fullscreen is left, and when the page comes back from an absence of a second or more; a page hidden for a few milliseconds, which a window's change of state can cause, is not an absence.
- **Fullscreen**, on F.

/// know
Every change on this list is built so that the comparisons cannot see it. The port's keys reach the core as the original's own key codes, Control included, so the original's key handling runs unchanged on them. The assist is off and the flip is not set whenever the port is compared with the original, so those runs are the original game; with the assist off, `tests/test_assist.py` repeats the original's own table of taps and menu steps. And the three letters the shell and the port keep for themselves, H, F and V, were checked against every place in the program that reads the keyboard: none of them takes such a letter on its own outside the line editor where a name or a file name is typed, and there they are letters again.
///

/// dev
The keys, by position, beside the original's. The layer that turns them into the original's codes is `src/portkeys.c`, the shell's own keys are in `web/main.js`, and the assist is `src/assist.c`; every rule is in `SPEC.md`, section 6.2, "Input", and `re/notes/keys.md`.

| Key | What it does | The original's key |
|---|---|---|
| the arrow keys, or W, A, S, D | the stick | the joystick |
| Space | fire | the joystick's button |
| Enter | chooses in a menu, as fire does | Return |
| P, or Escape | pause and continue | Escape |
| V | the vertical flip | Control-F |
| G | save, on the carrier | Control-G |
| L | load | Control-L |
| M | music off and on, in flight; silences the effects too | Control-S |
| R | restart, while paused or in the briefing | Control-R |
| C | clear the high scores, while paused | Control-C |
| H | the help screen | none |
| F | fullscreen | none |

The key left of 1 opens the shell's diagnostics overlay and never reaches the game.
///

## How we know, in brief

A definition is worth what checks it. The rest of Part I is about the instruments that do; here they are in outline.

- **The oracle.** An original routine runs on an emulated 68000 processor beside its port, on the same inputs, often thousands of random ones (the colour arithmetic of a fade, for one, on 20,000), and the results must be equal. Every pure routine, one that computes from its inputs alone, has to pass it before it counts as verified. The suite holds more than three hundred oracle tests. Chapter 5 is about the oracle.
- **The headless original.** The whole original program, from its first instruction, runs under emulation without a screen: the operating system replaced by small stand-ins, nothing drawn, and the beam's position served from the same random stream the port uses. None of the game's logic is rewritten for it; it is the original's own code. Chapter 6 is about it.
- **The comparisons.** The port and the headless original play the same mission from the same inputs and are compared after every tick and every pass: every variable the port keeps, every drawing call with its arguments, every random number drawn and the routine that drew it, the palette of every row. One way of comparing sets the port to the original's state before each pass, so that a difference points at its pass; the other lets the port run alone from the program's start, as it runs in your browser. A completeness test demands that every place in memory the original writes during a mission is compared, or listed with the reason why not. Sixty mission scripts fly these comparisons on all fifteen maps, with eight more runs of loaded games and demos and twenty-one of the key commands, and the title sequence and the menus are compared VBlank by VBlank. Chapters 7 and 8 tell how.
- **The sound event log.** Every sound sample started, by the port and by the original, with its channel, pitch and volume, compared after every tick and every pass of every mission script.
- **The replay.** A demo recorded by the port is played back in the native build and in WebAssembly against a fingerprint of the whole game state after every input sample.
- **The page.** The finished file is opened in Chrome and Firefox and played through the browsers' own drivers with real key presses, and checked for its pixels, its display, its timing and its sound. Chapter 24 is about the tests.

Together they are about nine hundred tests.

What the instruments do not see belongs to the definition too. The headless original draws nothing, so no whole mission scene is ever compared pixel by pixel; the drawing calls, the palette of every row and the picture of every single shape stand for it. Every shape of the game is drawn by the original's own routine through a model of the Amiga's [blitter](../glossary.md#blitter), the chip that does the drawing, and compared pixel by pixel with the port's picture. Chapters 11 and 12 say what that proves and what it does not. And three things rest on documented behaviour or on the project owner's eye and ear rather than on a comparison: how long a step of a fade between two pictures takes, which in the original is processor time the listing cannot give and which the port sets to two VBlanks; the tempo of the music, which rests on the value one register of the timer holds when the machine is switched on; and the order in which a directory lists its files, which the Amiga's documentation describes and which neither a run nor the disk has confirmed. The fades and the music were found right by eye and by ear, every song heard; chapters 7, 18 and 19 give the detail.

## What comes next

This chapter has used a handful of Amiga words without explaining them: the VBlank, the copper, the blitter, the palette that changes down the screen. Chapter 2 takes twenty minutes to explain the machine the game was written for, the 68000 processor, chip memory, bitplanes, the copper, the blitter, Paula and the VBlank, and the little of AmigaOS the game uses: only what the port needed, so that the rest of Part I can be read without Part II.

## Further reading

- `SPEC.md`, section 1: "Goal", "Definition of faithful" and "Out of scope".
- `SPEC.md`, section 3.1, "Disk", and 3.3, "Runtime model".
- `SPEC.md`, section 6.2, "Shell": "Video" and "Input"; 6.3, "Blocking code becomes coroutines"; 6.5, "Audio model".
- `SPEC.md`, section 8, "Verification".
- `README.md`, "Amiga to Web".
- `re/notes/keys.md`, "The commands" and "The vertical flip, and how long it lasts".
- `re/notes/porting-m4.md`, "The keyboard assist".
- `re/notes/porting-m1.md`, "Findings".
