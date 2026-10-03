Chapter 19
{ .chapter-kicker }

# The front end and the keys

Before and between missions the game runs a few screens: a scrolling story, three pictures, a menu of ranks, a briefing, a dialog for saved games, the high scores. By the end of this chapter you will know what each screen draws, waits for and reads, VBlank by VBlank; how one loop joins them; how a key becomes a code in a buffer that five routines read and the ROM's own routine turns into a character; and what the port made of it, its own keys and the keyboard assist among it. The port and its instruments come at the end.

## A timetable of waits

The [**front end**](../glossary.md#front-end) is the game's screens before and between missions, and the loop that joins them. Each of its screens waits by calling graphics.library's `WaitTOF`, which returns at the next [VBlank](../glossary.md#vblank), so many times or until the button goes down; one call is a round of the wait, one VBlank. So, left alone, the program runs the same timetable every time, and the port is held to it VBlank by VBlank. This is a run of the [headless original](../glossary.md#headless-original) with no input, on PAL:

| VBlank | What happens |
|---|---|
| 1 | song 2; the story scroller |
| 3 to 2,915 | 53 lines of the story, one every 56 VBlanks |
| 3,791 | the scroller ends; song 2 fades |
| 3,895 | song 1; the first picture, 60 rounds in a palette of its own, 120 in its colours |
| 4,078 | the title, 300 rounds |
| 4,379 | the credits, 600 rounds |
| 4,980 | the rank selection; song 1 fades |
| 5,084 | song 4; the menu, at most 1,800 rounds |
| 6,888 | the menu gives up and asks for the demo; the music stops |
| 6,992 | the briefing, 240 rounds |
| 7,237 | the mission set up; its first tick, chapter 8's step S, comes next |

A change of song waits for the [song's fade](../glossary.md#songs-fade), 104 VBlanks in which the screen stands still (chapter 18). The display's [fades](../glossary.md#fade) hold no wait, so the headless original runs them in no time; the port gives a step two VBlanks, by the owner's eye, and the comparisons none ([chapter 7](../part-1/time.md#the-fade-step)). With the taps of fire the tests use, step S comes after 444 VBlanks, 312 of them the three songs' fades.

/// figures
| The timetable in seconds, derived | |
|---|---|
| A line of the story, 56 VBlanks | 1.1 s |
| The pictures' waits, 60, 120, 300, 600 rounds | 1.2, 2.4, 6, 12 s |
| The rank selection, 1,800 rounds; the briefing, 240 | 36 s; 4.8 s |
| A change of song, 104 VBlanks; a fade in the port, 32 | 2.1 s; 0.64 s |
| The front end left alone, 7,237 VBlanks; with fire, 444 | 145 s; 8.9 s |
///

## The story scroller

The [**story scroller**](../glossary.md#story-scroller) comes first, behind song 2; the [crack](../glossary.md#crack)'s text screen before it is left out (chapter 1). It is one [view](../glossary.md#view) of 640 by 200 with one [bitplane](../glossary.md#bitplane), and its window shows 230 rows, more than the bitmap has, because the bitmap is a ring. Each step, four VBlanks, moves the plane's start a row down, so the text rises with nothing copied; after 210 steps the start returns to the top, and the [copper list](../glossary.md#copper-list) reloads the plane's address where the bitmap runs out.

Every 56 VBlanks a band is cleared and a line drawn, from a block of strings in the executable, 2,152 bytes at `0x017494`. The processor draws the line in the game's own font into a one-bit template, a mask of where the ink goes, and graphics.library's `BltTemplate` stamps it in the current colour, justified to 615 pixels unless it ends a paragraph.

Where a line goes is the trick. The first is drawn at row 196, the window's bottom; every later one 14 rows before the plane's current start, which the ring makes the bottom again. So the drawing writes before the bitmap, into the rest of the view's memory, and graphics.library does not clip it there. That is why the port's graphics layer must not clip either, and why its view block is 640 by 260 bytes ([chapter 11](display.md#what-the-port-made-of-it)): the plane walks 210 rows down and the window shows 230 from there.

The text fades in at the bottom and out at the top, through a grey ramp of colour 1, `0x111` a row, over the window's top 16 rows and its bottom 16; the port gives each grey a palette. Fire ends the scroller, or 210 steps after its last line; it reads no key.

![The story scroller: a line dim at the top, a white justified paragraph, its short last line dim at the bottom.](../generated/figures/story-scroller.png)

/// caption
The story scroller at VBlank 780 of the front end left alone, both grey ramps carrying text; the paragraph's last line is not justified.
///

## The title sequence

The [**title sequence**](../glossary.md#title-sequence) runs the scroller and then three pictures behind song 1: chapter 1's picture of the crack, the title and the credits, on two views of 320 by 200 with five planes. Each picture is decoded into the view not on show, its colours set aside and the view's own black, while the previous one is still up; then the views swap and it fades in, so no picture is seen being decoded. Fire ends a wait and skips the rest of the sequence at once. The fades take a second argument that nothing reads.

## The rank selection

The [**rank selection**](../glossary.md#rank-selection) is the menu of chapter 17's seven [ranks](../glossary.md#rank) and the load item below them, behind song 4. Its highlight comes from a [shape container](../glossary.md#shape-container) of eight records, one an item, drawn by chapter 12's `shape_draw_xor`, which flips the screen's bits where the shape has them, so drawing it again takes it away. A move draws the old one away and the new one in, swaps the views and copies the shown one into the other, so that both agree.

![The rank selection: a heading, seven ranks and the load item, the second under a blue bar.](../generated/figures/rank-select.png)

/// caption
The rank selection after one pull of the stick: the highlight has moved to the second of the eight items.
///

Its reader, `menu_input`, takes the cursor keys and Return from the key buffer, then polls the stick and the button. Look at the count of rounds against `0x708`, 1,800, beyond which it returns 1000; in the port `CO_WAIT` stands for `WaitTOF`:

//// html | div.listing-pair

/// html | div
```wingslst
--8<-- "generated/listings/asm/menu_input_loop.lst"
```
///

/// html | div
```c
--8<-- "generated/listings/c/wof_menu_input_loop.c"
```
///

////

After a move it waits up to nine rounds for the stick and the button to rest. Left alone, the menu asks for chapter 17's [attract demo](../glossary.md#attract-demo), not on this disk, so a game starts at the rank under the cursor. The chosen rank is stored twice, as the rank played and the rank a high-score row will carry; the routine's return value is used by nothing.

## The briefing

The [**briefing**](../glossary.md#briefing) comes before every mission, on two views of 640 by 147 with three planes: the shape `rank` from `world.shp` as its background, the disk's `Rank.iff` never opened, and on it, in the game's font, the rank's name, the mission number and chapter 17's two counts. It sets no pen, graphics.library's colour number to draw with, so its text takes the one the system's initialisation leaves, `0xFF` cut to three planes: colour 7, a question the first milestone left open and a test now holds. After 240 rounds or on fire the mission begins; Control with R goes back to the rank selection.

## The load and save dialog

The [**load and save dialog**](../glossary.md#load-and-save-dialog) lists the saved games and loads one, or saves the game under a typed name. It takes the back view alone, 320 by 200 with four planes, and draws itself with graphics.library in the system font, [topaz 8](../glossary.md#topaz-8), since it never chooses one. Topaz 8 is in the [Kickstart](../glossary.md#kickstart) ROM, not on the disk, so the port reads it from the owner's ROM when it is built, found by its contents, because its header there is a placeholder the system fills at start-up. Six slots and two buttons come from a table, every line parallel to an axis; the selection is a rectangle filled in the complement mode, which inverts what is there, so filling it again undoes it.

![The dialog in load mode: six outlined slots, the first holding a saved game and highlighted, two buttons below.](../generated/figures/load-dialog.png)

/// caption
The dialog in load mode, with this disk's one saved game; every pixel is graphics.library's.
///

The list is the game's own directory as dos.library's `ExNext` hands out its entries. Look at the test of each name, `w`, `o`, `f` in either case, a full stop and one character more, and at the port's side, which computes the same list in the same order:

//// html | div.listing-pair

/// html | div
```wingslst
--8<-- "generated/listings/asm/dialog_file_list_prefix.lst"
```
///

/// html | div
```c
--8<-- "generated/listings/c/wof_fs_dir_entry.c"
```
///

////

There is no sorting: the list keeps the order of the directory's 72 hash chains (chapter 3), at most six, and a directory so named would be listed too. In save mode the cursor goes straight into the line editor on a slot's name, and saving over an edited name deletes the old file, so editing a name renames the save. A typed `:` or `/` becomes a space, so that a name cannot name a device or a directory, and `wof.` goes in front. After a load, chapter 17's setup of the loaded mission follows.

## The high scores and the name entry

The [**high-score screen**](../glossary.md#high-score-screen) ends a game, behind song 0, with chapter 17's [high-score file](../glossary.md#high-score-file) in a local of its routine and two [viewports](../glossary.md#viewport), a picture above a slab. The ten rows go on the slab in the game's font three times: a pixel up and left in pen 0, a pixel down and right in pen 0, then in place in pen 15, white outlined in black. Before it runs the [**name entry**](../glossary.md#name-entry), shown only when the score beats the tenth row's: the dialog's screen and the line editor, with room for 16 characters and a fifth argument nothing reads.

## The outer loop

The [**outer loop**](../glossary.md#outer-loop) is `main`'s loop that runs, after the title sequence, the rank selection, the briefing, a mission and the high-score screen, again and again. A mission is the inner loop, one [pass](../glossary.md#pass) a round, with chapter 17's briefings between missions inside it.

![The front end's screens as boxes joined by arrows, as the caption tells.](../figures/outer-loop.svg)

/// caption
The outer loop: the dialog belongs to the rank selection; the briefing's Control-R and a played demo go straight back to the loop's head.
///

## How a key reaches the game

The keyboard never reaches the logic through the [input byte](../glossary.md#input-byte). A key going down sends a [**raw key code**](../glossary.md#raw-key-code), a number from 0 to 127 that names the key's place, not its letter, with bit 7 set when it goes up; so a German keyboard gives the same codes as an American one. With it travels the [**qualifier**](../glossary.md#qualifier), a word of bits for the keys held: `0x0001` and `0x0002` the Shifts, `0x0004` Caps Lock, `0x0008` Control, `0x0010` left Alt, `0x0080` right Amiga.

The system's input.device passes every event down a chain of handlers by priority. The game's own sits at 127, the highest, so it sees each key first: it drops a key going up, appends the code and the qualifier to the [**key buffer**](../glossary.md#key-buffer), ten of each with a count, and clears the event's class, so that nothing after it sees the key.

![The key path on the Amiga and in the port, as the caption tells.](../figures/key-path.svg)

/// caption
From a key to a character: the buffer and its readers are the original's on both sides; the shell's map, the key layer and the table are the port's.
///

`key_get` takes the oldest key and shifts the rest down, with an off-by-one. Look at the loop's `ble`: it runs while the index is at most the new count, so with a full buffer its last round copies one entry from past the end of each array. Beside it, how the port reads that entry:

//// html | div.listing-pair

/// html | div
```wingslst
--8<-- "generated/listings/asm/key_get_shift.lst"
```
///

/// html | div
```c
--8<-- "generated/listings/c/key_code_at.c"
```
///

////

On the machine the byte past the ten codes is the high byte of a qualifier word, and the word past the ten qualifiers is the count. Nothing reads those slots before the buffer fills again, but they are state, compared with the original's after every step, so the port leaves the same values there; it keeps the values, not the neighbourhood, so its own structure may order its members freely.

Control is the one qualifier bit the game reads; the Control key's own code, `0x63`, matches no command. A mask that would make every key need left Alt is set only when the program finds a trap handler other than the one dos gives a process; started from the command line it is 0, dead in play.

To act on a letter, a reader calls `key_to_char`, which hands the key to console.device's `RawKeyConvert` with the system's default [**keymap**](../glossary.md#keymap), the table that turns a code and its qualifier into characters, and keeps the result only when exactly one character came back. So `0x13` gives r, R with Shift and `0x12` with Control, and a cursor key gives two characters, so none.

The keymap is the system's, in the ROM, and the headless original runs the ROM's own routine on it ([chapter 6](../part-1/headless.md#the-rom-run-for-real)). The port runs no 68000 code, so its build runs that routine once over every code under the sixteen combinations of the four bits the port can send, both Shifts, Caps Lock and Control: a table of 2,048 bytes, 1,050 of them characters. Writing the routine anew would mean its rules for every kind of key, for a game that never asks for more than one character; running it makes the ROM itself the reference. Without the ROM the build stops; the extraction tool run alone falls back to letters, digits and the space bar.

## The readers and the commands

Five [**readers**](../glossary.md#reader-of-the-key-buffer) take keys from the buffer: `menu_input` in the menus, `wait_input_release` between two moves, the line editor `text_input`, the briefing, and `ingame_keys`, once a pass in flight. The story, the pictures and the high scores read no key. `ingame_keys` runs before the inner loop's test of the pause and empties the buffer, so its commands work paused too, and Escape can end the pause. It and the briefing convert a key without its qualifier and test the Control bit apart:

| State | Keys |
|---|---|
| Rank selection | cursor up `0x4C` and down `0x4D` move the highlight, wrapping round; Return `0x44` or keypad Enter `0x43` chooses |
| Briefing | Control and R: back to the rank selection |
| In flight and paused | Escape `0x45`, the pause; with Control: R restart, S `0x21` the music (chapter 18), F `0x23` the [vertical flip](../glossary.md#vertical-flip), G `0x24` save on the carrier, L `0x28` load outside a demo, C `0x33` delete the high-score file |

Control with B leads into the game's own crash reporter, which the port lacks; five plain keys in a row unlock debug keys. The manual's Control-D for the high scores (page 12) is not in this executable, and Control-C, which the manual allows only after it, deletes the file at once. A restart keeps the flip and a loaded game sets it from the file, which is why the port keeps it as a preference (chapter 1). The right mouse button is noted in a byte nothing reads.

The [**line editor**](../glossary.md#line-editor), `text_input`, edits the name entry's name and the dialog's file names; its caret is a complement fill, drawn again to go. It tests keys by their raw code first:

| Key | What it does |
|---|---|
| Return or Enter, or fire | accept and leave |
| cursor left `0x4F`, right `0x4E` | a character; with either Shift, to the line's start or end |
| cursor up or down, or the stick | leave, to the slot above or below |
| Backspace `0x41`, Delete `0x46` | delete before, or under, the caret |
| right Amiga and X, `0x32` | clear the line |
| any other key | converted with its qualifier and inserted, if there is room |

There is no filter: any single byte the conversion gives goes in. Look at the Shift tested as the qualifier's two lowest bits:

//// html | div.listing-pair

/// html | div
```wingslst
--8<-- "generated/listings/asm/text_input_keys.lst"
```
///

/// html | div
```c
--8<-- "generated/listings/c/text_input_keys_c.c"
```
///

////

## What the port made of it

The key path is kept routine by routine, `key_to_char` over the table; dropped are the handler's mouse half, whose byte nothing reads, the chain of events, with no input.device to swallow one from, and `key_get`'s wait on an empty buffer, reached only from a routine with no caller. The dead mask stays: three lines, and a test runs its other path against the original.

### The key layer

In front of the buffer sits the port's [**key layer**](../glossary.md#key-layer), in a file of its own because it is policy decided with the owner, not a port. A browser keeps Control with R, F and L for itself, so each command gets a plain letter, rewritten into the code and the Control bit the readers expect:

| Key | Becomes | When | Why |
|---|---|---|---|
| P | Escape | always | |
| V | Control-F, the flip | always | F is fullscreen |
| G | Control-G, save | always | |
| L | Control-L, load | always | |
| M | Control-S, the music | always | S is the stick pulled back |
| R | Control-R, restart | paused, or in the briefing | a stray press would end a campaign |
| C | Control-C, clear the high scores | paused | the same |

Otherwise a key passes as it came, and inside the line editor every key does. Look at the editor's test around the switch:

```c
--8<-- "generated/listings/c/wof_port_key.c"
```

The cost: P, V, G, L and M never reach a reader as plain letters outside the editor, and the cheat's sequence cannot be typed, since its third key loads. Nothing in the manual is lost, for a plain letter does nothing in the original either. The shell ([chapter 23](../part-3/shell.md)) takes H and F for its help screen and fullscreen, and maps `KeyboardEvent.code`, a place too, to the raw code with the Shift and Caps Lock bits. It leaves out the function keys and Help, since swallowing F5 or F12 would take reload and the developer tools away; the key left of 1, its diagnostics key; and right Amiga, so the editor's clear has no key. Development keys behind its overlay set a score for the name entry, open the dialog and choose PAL or NTSC.

### The keyboard assist

Chapter 1 told what the [keyboard assist](../glossary.md#keyboard-assist) does; here is how. The weapon menu in the hold steps on the input byte and then waits for two more [input samples](../glossary.md#input-sample) that carry input, so a step costs three samples, twelve VBlanks, and for 15 ticks after it opens it is not run. A stick is held through that; a key is tapped. So the assist turns a press of forward or back in the menu into a [**push**](../glossary.md#push-of-the-keyboard-assist), the stick held for exactly twelve VBlanks: three samples at any phase, one step. Two presses made meanwhile are remembered; a press in the first 15 ticks waits for the VBlank the menu becomes live, predicted from its count less the bytes in the [input queue](../glossary.md#input-queue). The push is never flipped, and elsewhere a tap shorter than four VBlanks reaches exactly one tick. Twelve taps forward, 20 VBlanks apart:

| Each tap | Steps, the original | Steps, with the assist |
|---|---|---|
| 1 VBlank | 1 | 12 |
| 2 VBlanks | 2 | 12 |
| 3 or 5 VBlanks | | 12 |
| 4, 8 or 12 VBlanks | 4, 8 or 12 | |
| held for 240 VBlanks | 20 | 20 |

Only the sample sees the assist; the front end's polls, the button's [latches](../glossary.md#latch) and every compared value do not, and the rank menu, which polls every VBlank, is left alone. The core starts with the assist off, as every comparison runs; the page switches it on.

### The waits, the drawing and the files

The front end blocks, and a page cannot, so every routine that waits is a [coroutine](../part-3/core.md), code that stops at a wait and goes on there at the next call. One wait, `CO_WAIT`, is one VBlank, because the headless original delivers a VBlank where the program waits and the shell runs one pass a VBlank; and the port's start runs to its first wait, so the music's first call falls on VBlank 1 in both. A local that must outlive a wait lives in a structure, since the resume would skip its setting, and no wait sits inside a `switch` of the routine's own; chapter 22 tells the mechanism. The four waits:

| Wait | Rounds |
|---|---|
| `wait_frames_or_fire` | one, then up to n − 1 more; fire ends it |
| `menu_input` | one a round; after 1,800 it gives up |
| `wait_input_release` | up to nine; a waiting key ends it |
| `wait_vblank` | none when the VBlank has come already |

graphics.library becomes seven calls on [indexed](../glossary.md#indexed-framebuffer) pixels, `Move`, `Text`, `RectFill`, `Draw`, `SetAPen`, `SetBPen` and `SetDrMd`, without clipping, as on the machine. `Draw` refuses a sloped line, which would need the blitter's line mode, whose pixels the port has not established; the front end draws only the sides of boxes.

What the game writes goes into an overlay in front of the read-only disk. It is kept out of the core's state, so loading a state does not un-write a saved game, and its order comes from the names alone: the name's hash modulo 72 gives the chain, chains are walked upward, and in a chain the player's files come before the disk's, newest first. That a real Kickstart 1.3 walks the chains so, and puts a new entry at its chain's head, is documented behaviour nothing here confirmed. The dialog's button that ends the program reloads the page (chapter 23).

## How it is held

The keys are held under the headless original by the 34 [run descriptions](../glossary.md#run-description) of [`tests/runs/`](repo:tests/runs/): the front end left alone and with fire, and 32 runs pressing keys in every state that reads them. Each command runs with its key and without, so that the effect belongs to the key; here the flip, with Control and F, with F alone, twice, and with no key:

```python
--8<-- "generated/listings/py/test_control_f_flips_the_vertical_control.py"
```

The port replays both front-end runs from the program's start, given only their input, the fades at zero: the same files, the same notes, and every drawing call with its place and text at the same VBlank. The headless original draws nothing, so a screen's look rests on those calls and the owner's eyes; the [observers](../glossary.md#observer) that record them change no run. Under the [oracle](../glossary.md#oracle) run the off-by-one, the mask, the table against the ROM's routine over all 2,048 combinations, the justified template and the fades, and the line editor against the original's own. The page tests drive the keys in two browsers (chapter 24).

## What comes next

The chapter in one sentence: the front end is a timetable of waits counted in VBlanks, and a key is a raw code and a qualifier in a buffer of ten, read by five routines and made a character by the ROM's own routine, which the port ran once at its build. [Chapter 20](quirks.md) gathers the original's quirks, four met here: the directory order's unconfirmed half, the arguments nothing reads, the buffer's off-by-one, and the manual's Control-D.

## Further reading

- [`re/notes/frontend.md`](repo:re/notes/frontend.md): ["The timetable, left alone"](repo:re/notes/frontend.md#the-timetable-left-alone) and ["Screen by screen"](repo:re/notes/frontend.md#screen-by-screen).
- [`re/notes/keys.md`](repo:re/notes/keys.md): ["Raw code to character: console.device"](repo:re/notes/keys.md#raw-code-to-character-consoledevice), ["The five readers"](repo:re/notes/keys.md#the-five-readers) and ["The commands"](repo:re/notes/keys.md#the-commands).
- [`re/notes/porting-m3.md`](repo:re/notes/porting-m3.md): ["The key path"](repo:re/notes/porting-m3.md#the-key-path), ["The front end as coroutines"](repo:re/notes/porting-m3.md#the-front-end-as-coroutines) and ["The file system's write side"](repo:re/notes/porting-m3.md#the-file-systems-write-side); [`re/notes/porting-m4.md`](repo:re/notes/porting-m4.md): ["`ingame_keys` and the pause"](repo:re/notes/porting-m4.md#ingame%5Fkeys-and-the-pause) and ["The keyboard assist"](repo:re/notes/porting-m4.md#the-keyboard-assist).
- [`re/notes/system-font.md`](repo:re/notes/system-font.md); [`re/notes/drawing.md`](repo:re/notes/drawing.md#text), "Text".
- [`src/front.c`](repo:src/front.c), [`src/keys.c`](repo:src/keys.c), [`src/portkeys.c`](repo:src/portkeys.c), [`src/assist.c`](repo:src/assist.c), [`src/dialog.c`](repo:src/dialog.c); [`tests/test_frontend.py`](repo:tests/test%5Ffrontend.py), [`tests/test_front_port.py`](repo:tests/test%5Ffront%5Fport.py) and [`tests/test_oracle_m3.py`](repo:tests/test%5Foracle%5Fm3.py).
- [`original/manual.txt`](repo:original/manual.txt), the game's manual: pages 2 to 4, 11 and 12.
- Outside the repository: the [*Amiga ROM Kernel Reference Manual: Libraries and Devices*](https://archive.org/details/amiga-rom-kernel-reference-manual-libraries-and-devices), on input.device, console.device and graphics.library's text.
