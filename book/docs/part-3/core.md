Chapter 22
{ .chapter-kicker }

# The core

Chapter 21 placed the core in [`src/`](repo:src/); this chapter opens it. By its end you will know the rules its C is written by and the reason for each, how it keeps the original's arithmetic and data, and how every value it took over is tied to its address in the original. You will know how the game's state fits into one block that can be saved, how code that waited on an Amiga waits in a page, how the core keeps memory and files without an operating system, and what the shell can ask of it.

## One C program, and what it may not do

The [core](../glossary.md#core) is the game ported to C; the [shell](../glossary.md#shell) around it is the page's JavaScript (chapter 1). The core is C11, the C standard of 2011, and [**freestanding**](../glossary.md#freestanding): C with no operating system beneath it and only the part of the standard library that needs none, such as the integer types of fixed width, so it has nowhere to ask for memory, no files and no clock. The specification adds five bans, each with its reason:

- **No C library.** The page's [WebAssembly](../glossary.md#webassembly) has none and reaches nothing but what the page hands it; the core brings its own three routines to fill, copy and compare bytes.
- **No allocation once started.** Everything the core changes lives in one structure, so that saving it is a copy and nothing is left out; what it takes while loading comes from the arena below.
- **No host floating point in the game's logic.** A browser's rounds differently, and the flight would drift (chapters 5 and 14).
- **No clock.** The game's time is the VBlanks the shell hands in (chapters 6 and 7).
- **No undefined behaviour relied upon.** A compiler may assume it never happens, and the same sources build the page's WebAssembly and the [native library](../glossary.md#native-library) the tests run (chapter 5): if the two differed, the tests would prove something the browser does not run.

Tests hold the last ban: both forms of the core draw the same picture, save the same bytes and replay the same demo, and the floating point runs under a checker that stops at the first undefined operation too. Another holds that the WebAssembly imports nothing, no clock, no allocator, no call back into JavaScript: the page hands the core whatever it needs, through the interface at the end of this chapter.

## The modules, and what was left out

The files that port the game follow the original's modules, stretches of related routines, in address order, and every ported routine carries a comment, `orig` and its address, so that you can lay the [listing](../glossary.md#listing) beside the source. Where a file's opening or a note names its stretch:

| File | What of the original | Where |
|---|---|---|
| [`src/player.c`](repo:src/player.c) | the player's routines (chapter 14) | `0x01AA6E` to `0x01CBB2` |
| [`src/enemy.c`](repo:src/enemy.c) | the enemy aircraft's compiled C (chapter 16) | `0x01D18C` to `0x01E8A7` |
| [`src/sound.c`](repo:src/sound.c) | the sound slots, then the channels (chapter 18) | `0x011F4E` to `0x0123DA`; `0x01E8B8` to `0x01ED78` |
| [`src/draw.c`](repo:src/draw.c) | the blitter library (chapter 12) | `0x0209BC` to `0x0215D8` |
| [`src/ffp.c`](repo:src/ffp.c) | the ROM's floating point, reached through the game's glue | `0x021C9C` to `0x021D2E`; each line with its ROM address |
| [`src/music.c`](repo:src/music.c) | the music player (chapter 18) | by its own offsets, `songplay+0x....` |

The other files follow their routines the same way. What the original asks of the system, the core does itself; chapter 2 gave the overview, and these are the main calls:

| The original | The core |
|---|---|
| dos `Open`, `Read`, `Lock`, `ExNext`, `Write` and the rest | a file system over the packed files |
| dos `LoadSeg` | the music player ported into the core |
| dos `Delay`, graphics `WaitTOF` | a coroutine's wait |
| exec `AllocMem` | the arena |
| exec `AddIntServer` | the shell's clock |
| the copper's lists | a palette for every row |
| exec `Forbid`, `Alert`, intuition `CloseWorkBench` and the like | dropped |

What is left out is marked `replace` or `drop` in the [routine inventory](../glossary.md#routine-inventory): the C runtime's start-up, the system's glue, the interrupt plumbing, Workbench, the crash reporter, the protection check and the crack's screen (chapter 1).

## The arithmetic

The original's C has an [int](../glossary.md#int-the-c-type) of 16 bits, and much of the program is assembly written by hand; the port's compilers have an int of 32. The specification sets ten rules, each because a value would otherwise come out different; earlier chapters met them one at a time:

| Rule | Why | Told in |
|---|---|---|
| every value has a named width, `int16_t` and the like, never a plain `int` | the two ints differ | 3 |
| every change of width the listing shows is kept: the [sign extension](../glossary.md#sign-extension) `ext.l`, a product cut to a word, a quotient toward zero, `swap` for the remainder | the cut decides the value | 3 |
| a comparison is signed or unsigned as its branch is, `blt` or `bcs` | the 68000 has a branch of each kind | 3 |
| a branch reads the [condition codes](../glossary.md#condition-codes) of the instruction that set them last | that need not be the compare | 16, 20 |
| a value left in a register's [upper word](../glossary.md#upper-word) is handed to the next routine | the next one reads it | 9 |
| a table read past its end is read by the original address | the original finds whatever lies behind it | 14, 20 |
| wrap-around is written with a cast | a signed overflow is undefined in C | 3 |
| an [arithmetic shift](../glossary.md#arithmetic-shift) is written to stay arithmetic | C leaves a negative number's right shift to the compiler | 5 |
| a division that would trap is recorded in the test build, the floating point's traps counted | a 68000 stops there | 5 |
| [fast floating point](../glossary.md#fast-floating-point) never goes through `float` or `double` | the rounding differs | 5, 14 |

Two instruments hold them: the [oracle](../glossary.md#oracle), whose random inputs, upper words included, reach edges no recorded flight reaches, and the [closed loop](../glossary.md#closed-loop), in which a slip carries on until it shows (chapters 5 and 8).

## The data

The data has rules of its own, for the same reason:

- **Files are read a byte at a time.** Every file is [big-endian](../glossary.md#big-endian), the hosts [little-endian](../glossary.md#little-endian), so a number is built from its bytes, and file bytes are never laid over a C structure.
- **Structures keep the original's order.** Each record is a C structure with the original's fields, order and widths, its offsets written down, because the tests find a field by its offset.
- **No pointer survives.** Where the original keeps an address, the port keeps what means the same on every machine: a [shape handle](../glossary.md#shape-handle) for a shape, a byte offset into the map, a flag for a block kept at a fixed place, and for a sound sample a [**sound handle**](../glossary.md#sound-handle), the number of its file plus one in the top byte and the offset into the file below it. A host's address would differ between the page and the tests; a handle does not.
- **Every allocation is zeroed.** The game asks the system for cleared memory and relies on it: the last four records of every map come from no file (chapter 13). The port hands out its memory zeroed, which a test and a control hold.
- **Every table has a fixed place and size.** What the original allocates for a mission, the port keeps in its state at a size the largest map fits, and a test holds every size against all fifteen maps: the record list holds 3,576 words, where map m needs 3,570.

## The registered state

The comparisons of chapter 8 copy the original's state into the port and compare the two after every pass and tick, so the port must know where the original keeps each value. That is the core's central idea: a [**registry**](../glossary.md#registry), one of three lists in which every variable, table and record layout the port took over is a line, tied to its address or its offset in the original.

The lists are X-macros: each line calls a macro the list does not define, and every file that includes the list defines it to make what it needs, a structure's member or a line of code. [`src/globals.def`](repo:src/globals.def) holds the plain variables, each as `WOF_GLOBAL(name, type, address)` with the name the names file gives (chapter 4); [`src/mission.def`](repo:src/mission.def) the tables, those at fixed addresses and those the original allocates; [`src/records.def`](repo:src/records.def) the records' layouts. Here is the [player's record](../glossary.md#players-record) of chapter 14; look at the offsets in the fourth column, and at the shape at `+0x04`, a pointer of four bytes in the original and a handle of two in the port, so that the next field starts at `+0x08` on both sides:

```c
--8<-- "generated/listings/text/player-record.txt"
```

The last column is the field's [**kind**](../glossary.md#kind-of-a-field): how it travels between the original's bytes and the port's structure. There are seven, and most fields are plain:

| Kind | In the original | In the port |
|---|---|---|
| `WOF_K_PLAIN` | an integer, big-endian | the same integer |
| `WOF_K_SHAPE` | a pointer to a shape record | a shape handle |
| `WOF_K_MAP` | a pointer into the map's records | a byte offset |
| `WOF_K_POOL` | a pointer to an allocated block | a flag: is there one |
| `WOF_K_SOUND` | a pointer into a sound effect | a sound handle |
| `WOF_K_SONG` | a pointer into the song data | its offset in the data |
| `WOF_K_VECTOR` | the address at the level-4 vector | the handler it names |

The lines become the members of structures inside the core's state: the [**registered state**](../glossary.md#registered-state), the variables, tables and records the registries list, each tied to its original address. So the harness can copy the original's state into the port field by field, turning the byte order round and each pointer into its handle, and nothing a registry lists can be forgotten in a save state. The variables are grouped by width, so that their structure has no gaps and is exactly the sum of its members, which a test holds.

/// figures
| The registered state | |
|---|---|
| Variables | 252 |
| Tables at fixed addresses | 30 |
| Allocations kept at fixed places | 21 |
| Record layouts | 26 |
| The whole state | about 360 KB, of it the display memory about 330 KB |
///

The lists also let the port read and write by an address the original computes, in whichever registered variable or table covers it. That is how a wreck's forty-first word lands in the aircraft records (chapter 16), and how a saved game is written and read back (chapter 17). Look at the two `#include` lines, each list expanded into one test an entry of whether the address falls inside it:

```c
--8<-- "generated/listings/c/wof_original_store8.c"
```

## Inside the state, and outside it

Here is the end of the one structure that holds all the core changes; look at the registered variables, the registered tables and the front end, and at the magic and the version under it:

```c
--8<-- "generated/listings/text/state-struct.txt"
```

Beyond the game's own values the state holds the port's: the counters, the [entropy stream](../glossary.md#entropy-stream)'s place, the controller's last raw state, the [vertical flip](../glossary.md#vertical-flip)'s preference and whether the shell gave one, the [stand-ins](../glossary.md#stand-in) reached, the [keyboard assist](../glossary.md#keyboard-assist)'s presses, and the state of [Paula](../glossary.md#paula) and of the music's timer with its [level-4 vector](../glossary.md#level-4-vector) (chapter 18). The front end's part holds the coroutines' resume points and the locals they keep, the viewports, the display memory and the [mirror markers](../glossary.md#mirror-marker) (chapter 12); none of it is a pointer.

![Two columns: left, in gold, the members of the core's state, saved; right, in grey, what the core keeps outside it, not saved.](../figures/core-state.svg)

/// caption
The core's state, saved and loaded as one block, beside what the core keeps outside it.
///

What lies outside does so for a reason: the files and the assets never change once loaded; every pass makes the picture again from the state; the mixed sound waits outside so that a replay renders the same sound however the shell asks; and loading a state must not un-write a saved game. Three settings the tests set from outside survive a fresh start, the fade step, the VBlanks a pass and the sound's rate; the assist's switch is in the state and starts off.

## Save states

A [**save state**](../glossary.md#save-state) is the bytes of that structure, copied whole, the core's counterpart of an emulator's save state: loaded into a core of the same build, the game goes on as if nothing had happened. `wof_init` zeroes the structure, so even the gaps between members are zeros and the round trip is exact; the bytes hold between little-endian hosts, which both forms of the core are. A load checks the magic, `0x574F4653`, the letters `WOFS`, and the version, and leaves the running game alone if either differs. The version, 12 now, is counted up at every change of the layout, so that an older state is refused rather than read into the wrong members.

A load then turns the mirrored shapes to match the state's markers and makes the picture from the state. Because the resume points are part of the state, a state saved inside a wait resumes there: the tests save one in flight with the shapes mirrored, one inside the restart's waits in a tick and one paused, load each into the same core and into one started on another seed, and find the next 400 VBlanks the same on both forms of the core. Here is the plainest such test; look at the two comparisons at its end, the picture after the load and the bytes 60 VBlanks on:

```python
--8<-- "generated/listings/py/test_state_round_trips.py"
```

A state cannot cross a reload of the page, since the loaded assets are not in it. The page offers no save states, the player saving the game's own way (chapter 17); they serve the replays and the tests.

## Coroutines

The original blocks: it waits for the next picture, a time, the fire button or a fade, in loops that do nothing else. A page cannot, or nothing is drawn and no key arrives (chapter 19). A browser lets a worker block only on shared memory, a `SharedArrayBuffer`, which it grants to a page served with two security headers; a page opened from a file has none.

So every routine that can wait is a [**coroutine**](../glossary.md#coroutine): a routine that can stop at a wait, give control back, and go on from there at the next call. The port's follow protothreads, a technique for C by Adam Dunkels and Oliver Schmidt after Simon Tatham and Tom Duff: the routine's body sits inside a `switch`, a wait stores a number and returns, and the next call jumps through the `switch` straight back to it. The number is the routine's [**resume point**](../glossary.md#resume-point), the line number of the wait in its file, 0 for not started. The original's control flow stays as it was, line for line. Look at `CO_WAIT`, which stores `__LINE__`, returns, and leaves a `case` label with that number behind:

```c
--8<-- "generated/listings/text/coro-macros.txt"
```

`CO_CALL` runs one coroutine from inside another, starting it in the same call. Three rules hold that the macros cannot check: no wait inside a `switch` of the routine's own, whose labels would mix with the macros'; a local that must survive a wait lives in the routine's context struct beside its resume point, since the jump back skips the line that set it; and every coroutine returns the macros' type. One context a routine is enough, and no stack, because no routine of the front end is ever inside itself: the state holds 22 contexts.

The unit of time is the VBlank. The shell calls the core's pass once after every VBlank, and the [headless original](../glossary.md#headless-original) lets VBlanks happen only where the program waits (chapter 6), so one wait is one VBlank on both sides; `wof_init` runs the program to its first wait, so that pass N does what the original does after VBlank N. The tick belongs to the coroutine too, because the restart after a lost aircraft waits inside it (chapter 14); the next mission continues the mission's coroutine (chapter 17); the front end's waits are chapter 19's, the song's fade chapter 18's.

One cost is worth knowing before you edit the core: a resume point is a line number, so adding or removing a line in a file with coroutines, even a line of comment, changes the core's bytes and the page's.

## The arena

The core cannot ask a system for memory, so it hands out its own. The [**arena**](../glossary.md#arena) is one block reserved once, from which the core takes what the original asked the system for; a C array without starting values, it costs nothing in the WebAssembly file, only in the page's memory. It has two ends. What outlives a load, such as the converted shapes, grows up from the bottom; the buffer a file is read and unpacked into grows down from the top, so that giving it back is one assignment, however much was taken below it meanwhile, which is all the original's freeing of a just-loaded file amounts to here. Every piece is zeroed as it is handed out, and nothing is freed. Look at `wof_alloc` moving `arena_used` up, `wof_scratch_alloc` moving `arena_top` down, and the zeroing in both:

```c
--8<-- "generated/listings/text/arena-ends.txt"
```

The shell puts the file blob into the arena before it starts the core, which is why `wof_init` leaves the arena alone. Nothing is taken once the assets are loaded: thirty-one missions set up in a row leave its use where the first left it, so a long campaign cannot exhaust it. Only the tests empty it.

/// figures
| The arena | |
|---|---|
| Its size | 3 MB |
| The file blob | about 530 KB |
| In use once `wof_init` has run, the blob included | about 1.1 MB |
///

## The file system

The game opens its files by name through the system's dos library. The port answers its loaders' calls from one blob the build packs, the 55 files the page carries with a directory of their names, offsets and lengths (chapter 3's sidebar). The names are paths from the game's directory, so the loaders ask for the original's own names, found whatever their case, as AmigaDOS finds them. A loader is the original's routine, ported, so that a file's size and even a byte read past its end are what the original sees (chapter 3). A lock and a file handle are both an index into the directory, so neither needs memory nor can fail for want of it.

What the game writes, the high scores and the saved games, goes into the [**overlay**](../glossary.md#overlay-of-the-file-system): written files kept in front of the read-only disk, a written file shadowing the disk's of the same name and a deleted one hiding it, as AmigaDOS does to the game. It has twelve slots, each of up to 12,412 bytes, the largest saved game the port's tables allow (chapter 17). It lies outside the state, so that loading a state does not un-write a file. When a counter moves, the shell stores the written files in the browser, and at the next start hands them back in the order stored, on which the load dialog's list depends (chapters 19 and 20).

## Two inputs, and the video standard

Two inputs besides the player's hands reach the logic, and both are named. The entropy stream stands in for the beam (chapter 6): a small generator in the core, seeded by `wof_init`, its values shaped like the beam's register, one for each call of the game's random routine, in the original's order; a test build can hand in its own. The second is the address the machine's allocator gave the map's records, which a defect of the original turns into a wreck's position (chapter 20): the tests give the headless original's, the page a fixed one. The video standard is a setting the shell gives at the start: it sets the VBlank rate and the sound model's clocks, and nothing in the logic reads it (chapter 7).

## The interface the shell sees

The shell reaches the core through 53 exported functions, declared in [`src/wof.h`](repo:src/wof.h); among them are queries, such as the picture's size, so that the shell hard-codes nothing. By purpose:

| Purpose | Entries | Told in |
|---|---|---|
| the start and the clock | `wof_init`, `wof_set_video_hz`, `wof_vblank`, `wof_pass` | 7, 23 |
| the keys | `wof_key`, `wof_port_key`, `wof_line_editor_active` | 19 |
| the settings | the flip, the assist, the fade step, the VBlanks a pass, each set and read | 1, 7, 19 |
| the picture | `wof_framebuffer`, its size, `wof_palette_rows`, `wof_palettes` and their counts, `wof_display_list` | 11, 23 |
| the sound | `wof_audio_render` | 18, 23 |
| the state | `wof_state_size`, `wof_state_save`, `wof_state_load` | here |
| the arena | `wof_alloc`, `wof_arena_reset`, `wof_arena_size`, `wof_arena_used` | here |
| the files | the packed files' count, `wof_fs_changes`, the written files one by one, `wof_fs_put` | 19, 23 |
| the requests | `wof_request_pause`, `wof_paused`, `wof_request_continue`, `wof_exit_requested` | 1, 23 |
| the counters | VBlanks, ticks, passes, stand-ins reached, assets loaded | 8, 23 |
| development | the diagnostics overlay's lines, the demo's recording, a score, a dialog | 17, 19, 23 |

`wof_vblank` takes the controller's raw state, five bits, not a finished [input byte](../glossary.md#input-byte), and does a VBlank's work in the original's order: Paula's events, the sound's VBlank routine, the fire button's timing, the port's own watch for the assist and, every fourth VBlank, the input sample (chapter 7). The pause is a request, not a toggle, which a mission's next pass takes as Escape; the development entries the shell offers only while its diagnostics overlay is up.

The picture is an [indexed framebuffer](../glossary.md#indexed-framebuffer) of 640 by 214, a byte a pixel, with a palette for every row: 24 palettes of 32 colours, palette 0 black for the rows no viewport covers, in the byte order a canvas takes. Chapter 11 told how the [bands](../glossary.md#band) fill it; nothing in the logic reads a pixel back. Beside it the core lists every shape drawn in the pass, for a renderer that could one day draw the game anew; the page's ignores the list. The sound is chapter 18's Paula model: `wof_audio_render` hands out as many frames as the emulated time lasts at the rate asked for, 960 a VBlank at 48,000 a second on PAL, the rest of the shell's buffer silence.

/// dev
The native library carries two things the page never does. `WOF_TRACE` switches on [`src/trace.c`](repo:src/trace.c), which records what the port opened, played and drew, for the comparisons with the headless original's observers; in the page's build its calls are macros that vanish. [`tests/shim.c`](repo:tests/shim.c) adds about 130 entries through which the tests reach the core's insides with plain numbers, so that no test copies a C structure's layout. A test reads the names in the page's core and finds none of the test build's hooks among them. The recording lies beside the state and survives `wof_init`, so the suite puts it back before every test (chapter 9). The tests bind the core through ctypes, every function's types spelt out ([`tests/conftest.py`](repo:tests/conftest.py)), and convert the original's state by the kinds ([`tests/m4state.py`](repo:tests/m4state.py)); chapter 24 tells the suite.
///

## What comes next

The chapter in one sentence: the core is one C program that keeps everything it changes in one block tied to the original's addresses, waits by returning, and asks the page for nothing. Chapter 23 tells the other side of the interface: the shell, which calls the core at the VBlank rate, puts its picture on the screen, plays its sound and hands it the keys.

## Further reading

The files named here are in the repository, [`github.com/sy2002/wof-wasm`](repo:).

- [`SPEC.md`](repo:SPEC.md), sections [6.1, "Core"](repo:SPEC.md#61-core), [6.3, "Blocking code becomes coroutines"](repo:SPEC.md#63-blocking-code-becomes-coroutines), [6.4, "Video model"](repo:SPEC.md#64-video-model), [7.1, "Arithmetic"](repo:SPEC.md#71-arithmetic), [7.2, "Data"](repo:SPEC.md#72-data) and [7.3, "Determinism"](repo:SPEC.md#73-determinism).
- [`src/wof.h`](repo:src/wof.h), [`src/coro.h`](repo:src/coro.h), [`src/core.c`](repo:src/core.c), [`src/mem.c`](repo:src/mem.c) and [`src/fs.c`](repo:src/fs.c); the registries [`src/globals.def`](repo:src/globals.def), [`src/mission.def`](repo:src/mission.def) and [`src/records.def`](repo:src/records.def); [`tests/shim.c`](repo:tests/shim.c).
- [`re/notes/porting-m1.md`](repo:re/notes/porting-m1.md#decisions-the-port-made), "Decisions the port made"; [`re/notes/porting-m3.md`](repo:re/notes/porting-m3.md), ["The front end as coroutines"](repo:re/notes/porting-m3.md#the-front-end-as-coroutines) and ["The file system's write side"](repo:re/notes/porting-m3.md#the-file-systems-write-side); [`re/notes/porting-m4.md`](repo:re/notes/porting-m4.md), ["Where mission memory lives"](repo:re/notes/porting-m4.md#where-mission-memory-lives) and ["Save states and the mirror markers"](repo:re/notes/porting-m4.md#save-states-and-the-mirror-markers); [`re/notes/random.md`](repo:re/notes/random.md).

Outside the repository: Simon Tatham's ["Coroutines in C"](https://www.chiark.greenend.org.uk/~sgtatham/coroutines.html), the switch trick explained; Wikipedia's ["X macro"](https://en.wikipedia.org/wiki/X%5Fmacro), the technique of the registries.
