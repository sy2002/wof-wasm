# Fact sheet: chapter 22, The core

Every claim the chapter makes, one line each, with its source, in the order of the chapter. A claim without a source goes to the list at the end and stays out of the draft. A general fact that the repository does not state is sourced in a reference work and marked **(reference)**; what the port does always comes from its sources, the specification, the notes and the tests. No "How we know" box and no "What went wrong" box (`book/BOOK.md` 4, point 6); the one sidebar is *For the developer*.

Counts are of the branch's base, `6bbf5fe`, counted in the files named, with the command in the counts table at the end. Runs for a fact: one short run of the native library as it stands (`tests/libwofcore.dylib`, not rebuilt), which loads the blob out of `dist/wof.html`, initialises the core and reads the state's size, the arena's use and the geometry (a scratch script, under a second). No test run, no browser, no rebuild.

Words used in the sheet as the chapter will use them, each in one sense. **The state** is always the core's state, `wof_s`, the struct `wof_state_t`; a record's state word is "the state word". **A handle** is the port's number for a shape or a sound sample; a file's handle under the dos glue is "a file handle", said once. **A pass** is one `wof_pass`. **A register** is the 68000's or a chip's; "registry" and "registered" are only the port's lists and what they list. **A table** is named with its noun: a registered table (of `src/mission.def`) or a lookup table of the original. **A wait** is a coroutine's; the music's fade wait is "the wait for the song's fade". **A line** in the coroutines' sense is "a line number"; a display line keeps its two words. **The overlay** is the overlay of written files; the shell's panel is always "the diagnostics overlay". **The registries** are the three files `src/globals.def`, `src/mission.def` and `src/records.def`.

The reference works:

- Wikipedia, "C11 (C standard revision)", `https://en.wikipedia.org/wiki/C11_(C_standard_revision)`, fetched once: C11, formally ISO/IEC 9899:2011, a standard of the C language. **(reference)**
- cppreference, "Conformance" (hosted and freestanding implementations), `https://en.cppreference.com/w/c/language/conformance`, fetched once: "A hosted environment has an operating system; a freestanding environment does not"; a freestanding implementation provides only a small subset of the library, among its headers `<stdint.h>` and `<stddef.h>`. Source of the definition of Freestanding and its Elsewhere line. **(reference)**
- cppreference, "Arithmetic operators", `https://en.cppreference.com/w/c/language/operator_arithmetic`, fetched once: a signed overflow is undefined behaviour ("it may wrap around ..., it may trap ..., or may be completely optimized out by the compiler"); for a negative left operand the value of `>>` is implementation-defined, most implementations shifting arithmetically. **(reference)**
- Wikipedia, "X macro", `https://en.wikipedia.org/wiki/X_macro`, fetched once: a list of invocations of a worker macro, expanded several times with the worker redefined, so that one list makes declarations, constants and code that cannot fall out of step. Elsewhere line of Registry. **(reference)**
- Wikipedia, "Region-based memory management", `https://en.wikipedia.org/wiki/Region-based_memory_management`, fetched once: a region, also called an arena, "a collection of allocated objects that can be efficiently reallocated or deallocated all at once". Elsewhere line of Arena. **(reference)**
- Wikipedia, "Saved game", `https://en.wikipedia.org/wiki/Saved_game`, fetched once (chapter 19's sheet fetched it for the Load and save dialog): "A save state is a form of a saved game in emulators", made when the emulator stores the emulated program's memory. Elsewhere line of Save state. **(reference)**
- Wikipedia, "Coroutine", `https://en.wikipedia.org/wiki/Coroutine`, fetched once: "computer program components that can be suspended and resumed". Elsewhere line of Coroutine. **(reference)**
- Wikipedia, "Protothread", `https://en.wikipedia.org/wiki/Protothread`, fetched once: protothreads, by Adam Dunkels and Oliver Schmidt after Simon Tatham and Tom Duff, are stackless coroutines in C built on a `switch` (Duff's device); a local variable does not keep its value across a yield. Elsewhere line of Coroutine. **(reference)**
- Simon Tatham, "Coroutines in C", `https://www.chiark.greenend.org.uk/~sgtatham/coroutines.html`, fetched once: the `switch` does the jump into the middle of the routine; `__LINE__` makes the case labels, so never two returns on one line; locals go into a context structure; never a return inside an explicit `switch` of the routine. Elsewhere line of Resume point. **(reference)**
- MDN, "SharedArrayBuffer", `https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Global_Objects/SharedArrayBuffer`, fetched once: shared memory between the main thread and workers, with `Atomics.wait()` to block a worker; usable only in a secure context that is cross-origin isolated by two HTTP headers, which a page opened from a file is not served with. **(reference)**
- Wikipedia, "Union mount", `https://en.wikipedia.org/wiki/Union_mount`, fetched once: directories combined so that they appear as one; the writable top layer shadows the lower, a deletion is a "whiteout" that keeps the lower file from reappearing. Elsewhere line of Overlay. **(reference)**
- Wikipedia, "Handle (computing)", `https://en.wikipedia.org/wiki/Handle_(computing)`: already the Elsewhere line of Shape handle; used for Sound handle. **(reference)**
- *Amiga ROM Kernel Reference Manual: Exec*: `MEMF_CLEAR` asks `AllocMem` for memory cleared to zeros; chapter 13's sheet (claim 11) sources it, chapter 13 tells it. **(reference)**

## Opening

1. By the chapter's end the reader knows what the core is and the rules it is written by, with the reason for each and the instrument that holds it: the arithmetic and the data, the registered state, save states, coroutines, the arena, the file system, the core's inputs, and the interface the shell sees. Source: `book/BOOK.md` 3, chapter 22; the controller's task.
2. Chapter 1 defined the core and the shell; chapter 21 placed `src/`. The chapter links both and defines them again nowhere. Source: `book/docs/part-1/faithful.md`, "One file in the browser"; `book/docs/part-3/repository.md`, "src/: the core"; the glossary's Core, Shell, WebAssembly.

## 1. One C program

3. The core is C11 and freestanding: no libc, no allocation after initialisation, one static arena replacing `AllocMem`, no host floating point in the game's logic, no dependence on wall-clock time, no undefined behaviour relied upon; the same sources compile for `wasm32-freestanding` and natively. Source: `SPEC.md` 6.1, first paragraph; `src/wof.h` lines 1-5.
4. C11 is the 2011 standard of C, ISO/IEC 9899:2011. Source: the reference. **(reference)**
5. **Freestanding** (the term, defined here): C without an operating system beneath it and with only the small part of the standard library that needs none, the fixed-width integers among it; no memory to ask for, no files, no clock. Source: the cppreference reference; `SPEC.md` 6.1. **(reference)**
6. The page's core is compiled with `-target wasm32-freestanding -std=c11 -O2 -nostdlib`; the native library with clang, `-std=c11 -O2 -dynamiclib -DWOF_TRACE=1`, plus `tests/shim.c`. Source: `tools/build.py` lines 52 to 57 and `compile_native`; `SPEC.md` 5 (Apple clang). The chapter names no flag but `WOF_TRACE`, in the sidebar.
7. With no C library the core has its own three byte routines, `wof_mem_set`, `wof_mem_copy` and `wof_mem_equal`, prefixed so that the native build does not collide with the system's library. Source: `src/mem.c`, opening comment and code.
8. Why freestanding: the WebAssembly the page runs gets one block of memory to itself and reaches nothing of the page but what the page hands it; the same C runs as the native library beside the original in the tests (chapter 5). Source: the glossary's WebAssembly (second paragraph); `src/wof.h` lines 3-5; chapter 5.
9. Why no allocation after initialisation: everything the core may change while running is in one struct, so that saving it is a copy and adding state cannot silently break the round trip. Source: `src/wof.h`, the comment above `wof_state_t`; `SPEC.md` 7.2, last bullet but one ("The arena is used only while assets load, so it does not grow from mission to mission").
10. Why no host floating point: a browser's rounds differently and the game's state would drift; chapters 5 and 14 told it. Source: `SPEC.md` 7.1, the floating-point bullet; `src/ffp.h` opening comment.
11. Why no clock: the game's time is the VBlanks the shell hands in, and nothing the program sees depends on a clock (chapters 6 and 7). Source: `SPEC.md` 6.1, 6.2 ("Clock"), 7.3.
12. Why no undefined behaviour: a compiler may assume it never happens (chapter 3, for the overflow), and the tests run the native build while the page runs the WebAssembly, so a difference between the two would mean the tests prove something the browser does not run. Source: `tests/test_core_native.py`, `test_native_and_wasm_draw_the_same_picture`'s docstring ("they must also behave the same, or the oracle tests would be proving something the browser does not run"); chapter 3.
13. Instruments: the native and the WebAssembly core draw the same picture (the test above); a state saved in a flight is the same bytes on both (`tests/test_state_m4.py`, "the two targets saved different states"); the demo the port recorded replays in both (chapter 1, `tests/test_replays.py`); the floating point also runs under clang's undefined-behaviour sanitizer, which stops at the first finding (`tests/test_oracle_ffp.py`, `test_the_same_code_under_the_undefined_behaviour_sanitizer`).
14. The core imports nothing: no clock, no allocator, no callback into JavaScript; a test holds the WebAssembly's import list empty. Source: `tests/test_core_wasm.py`, `test_core_needs_nothing_from_the_host` ("No imports at all: no clock, no allocator, no callback into JavaScript"); `web/core.js` opening comment.
15. The files that port the game follow the original's modules in address order, so that a reader moves between the listing and the source; every ported routine carries `orig 0x......`. Source: `SPEC.md` 6.1; `CLAUDE.md`, "Rules"; chapter 21 (claim 54 of its sheet).
16. The module table, each range as the file's opening comment or a note names it:
    - `src/player.c`: the player's C routines `0x01AA6E` to `0x01CBB2`, in their order (its opening; chapter 14).
    - `src/enemy.c`: the module of compiled C `0x01D18C` to `0x01E8A7` (its opening; chapter 16).
    - `src/sound.c`: the slots `0x011F4E` to `0x0123DA` and the channel layer `0x01E8B8` to `0x01ED78` (its opening; chapter 18).
    - `src/draw.c`: the blitter library, `0x0209BC` to `0x0215D8` (`re/notes/drawing.md`, line 14; chapter 2's sidebar; the file's opening names `blit_clip_setup` `0x0209BC`).
    - `src/ffp.c`: mathffp's own code in the ROM, reached through the glue at `0x021C9C` to `0x021D2E`, each line with its ROM address (its opening; chapter 14).
    - `src/music.c`: the music player, by the player's own offsets, `orig songplay+0x....` (its opening; 33 such comments; chapter 18).
    The chapter adds that the rest follow their routines in the original's order (claim 15).
17. What is not ported, marked `replace` or `drop` in the inventory: the C runtime's start-up, the system's glue, the memory management, the construction of views and copper lists (whose visible effect, the colour tables, the split, the pokes and ramps, comes back through the palette of every row), the interrupt plumbing, Workbench, the debug and crash reporters, the protection check and the crack's screen. Source: `SPEC.md` 6.6; chapter 1 told it in outline, chapter 4 the statuses.
18. The machine table, condensed from `SPEC.md` 3.4 (chapter 2's table gives the overview; this one names the calls):
    - dos `Open`, `Read`, `Lock`, `Examine`, `ExNext`, `Write`, `DeleteFile` and the rest: the file system over the packed files, writes into the overlay;
    - dos `LoadSeg`, `UnLoadSeg`: the music player ported into the core, the song data read where the file lies;
    - dos `Delay`, graphics `WaitTOF`: a coroutine's wait;
    - exec `AllocMem`, `AvailMem`: the arena;
    - exec `AddIntServer`, `RemIntServer`: the shell's clock and `wof_vblank`;
    - exec `RawDoFmt`: a small formatter for the formats the game uses;
    - mathffp: the nine operations in integer code;
    - graphics drawing calls: the same on indexed pixels;
    - the custom chips, `JOY1DAT`, `VHPOSR`, the audio registers, the vector at `0x70`: the raw controller state, the entropy stream, the Paula model;
    - `COP1LC` and the copper lists: the palette of every row;
    - exec `FindTask`, `SetTaskPri`, `Forbid`, `Permit`, `Supervisor`, `Alert`, `Debug`, intuition `CloseWorkBench`, `OpenWorkBench`: dropped.
    Source: `SPEC.md` 3.4, the table's rows.

## 2. The arithmetic

19. Every value of the game has a named width, `int16_t`, `uint16_t`, `int32_t` and their kin, never a plain `int`: Manx Aztec C's int is 16 bits as the game was built, today's compilers' 32. Source: `SPEC.md` 7.1, bullet 1; chapter 3 ("The 16-bit int"). Chapter 3 told it; this chapter puts it in the table.
20. Every width change of the listing is kept: `ext.l` a sign extension, `muls.w` two words into a long whose next `move` decides whether it is cut, `divs.w` a long by a word into a word quotient rounded toward zero, `swap` after it the remainder used. Source: `SPEC.md` 7.1, bullet 3; chapter 3.
21. Signedness follows the branch: `blt`, `bge`, `bgt`, `ble` signed; `bcs`, `bcc`, `bhi`, `bls` unsigned. Source: `SPEC.md` 7.1, bullet 4; chapter 3 told the rule.
22. A branch reads the flags of the last instruction that set them, which need not be the compare: `ship_sinking`'s `beq` at `0x011D00` reads a `move.w`; a `bgt` after `subq.b` judges the result with its overflow. Source: `SPEC.md` 7.1, bullet 5; chapters 16 and 20 told both.
23. A register's upper word a routine leaves is handed on as a value between the ported routines: `target_refill` (`0x014FEE`) to `target_fire`; never assumed 0 because the scripts found it so; the oracle tests draw it at random. Source: `SPEC.md` 7.1, bullet 6; chapter 9.
24. A constant table the original indexes past its end is read by its original address, from the registered variable where one covers the byte and from the executable's image elsewhere: the wheel table `0x025E3E` at attitude 9 reads `0x025E50`, which the same routine writes; an oracle test over random states found the case. Source: `SPEC.md` 7.1, bullet 2; chapters 14 and 20 (chapter 20 showed `data_byte`).
25. Wrap-around is behaviour: no variable is widened because it might overflow, and the wrap is written with a cast, because a signed overflow is undefined in C. Source: `SPEC.md` 7.1, bullet 7; the cppreference reference; chapter 3.
26. An arithmetic shift, `asr`, is written so that it is arithmetic on every compiler, because C leaves the right shift of a negative number to the compiler. Source: `SPEC.md` 7.1, bullet 8; the cppreference reference (implementation-defined). The bounce's `asr.w` is chapter 5's. **(reference)** for the C half.
27. A division by zero or a quotient too large traps on a 68000: the specification asks for an assertion in the test builds; the port's division of the enemy's routines leaves the dividend's low word and records the trap in the test build (`divs_w`, `src/enemy.c` lines 20 to 35), and the floating point counts its traps in `wof_ffp_traps`, which a test holds to the number the original took. Source: `SPEC.md` 7.1, bullet 9; `src/enemy.c`; `src/ffp.h` (`wof_ffp_traps`); `tests/test_oracle_ffp.py` (`ffp_traps`). (C: "asserted" is the specification's word; the code records and counts.)
28. Floating point never goes through C's `float` or `double`: where the listing calls the `ffp_` glue the port calls its own integer version of the operation on the same 32-bit format, the plain form where only the value is wanted and a `_cc` form where the original branches on the flags it returns. Source: `SPEC.md` 7.1, last bullet; `src/ffp.h` ("The interface M4 uses at the call sites"); chapters 5 and 14.
29. The instruments that hold the arithmetic: the oracle over random inputs (chapter 5), whose cases draw the upper words at random since chapter 9's finding, and the closed loop, in which any slip carries on and shows (chapter 8). Source: `SPEC.md` 7.1 and 7.4; chapters 5, 8, 9.

## 3. The data

30. File data is big-endian and is read with explicit byte accessors, never by casting file bytes to a struct: the file system's `be32` builds a long from four bytes. Source: `SPEC.md` 7.2, bullet 1; `src/fs.c` (`be32`). Why: the hosts are little-endian (chapter 3).
31. Game structures get C structs with the original field order and widths, the offsets recorded, because the tests map fields by offset. Source: `SPEC.md` 7.2, bullet 2.
32. A pointer inside the game's state becomes a handle, an offset, an index or a flag, so that a save state and a comparison depend on no host pointer value: a shape pointer a **shape handle** (chapter 17's entry), `((slot + 1) << 11) | index`, 0 for none; a pointer into the map a byte offset; a pointer to an allocation the port keeps at a fixed place a flag. Source: `SPEC.md` 7.2, bullet 3 and the bullet on tables; `re/notes/porting-m4.md`, "Where mission memory lives". The chapter does not give the handle's formula; the kinds table names the forms.
33. A **sound handle** (the term, defined here): the port's number for a place in one of the sound files, the file's index plus one in its top byte and the offset into the file below it, 0 for none; the samples are played where the files lie in the blob. Source: `src/wof.h` (`WOF_SOUND`, its comment); `src/records.def` (`WOF_K_SOUND`); `re/notes/porting-m8.md`, "The port". Chapter 18 called it so in plain words.
34. Every allocation the game's own code makes goes through `0x020874`, which sets `MEMF_CLEAR`, and the game relies on it: the map loader leaves the last four records of every map to the allocator. The port's arena hands out zeroed memory, also after `wof_arena_reset` or `wof_arena_release`, and a test holds it; a control removed the clearing and `wof_alloc` after a reset handed out old bytes. Source: `SPEC.md` 7.2, bullet 4; `re/notes/porting-m4.md`, "Where mission memory lives" and the controls in "How the port is held to the original"; chapter 13 told the records.
35. `MEMF_CLEAR`: the flag that asks `AllocMem` for memory cleared to zeros. **(reference)** RKM Exec; chapter 13's sheet.
36. Every table a mission allocates has a fixed place and a fixed capacity in the core's state; a test holds the capacities against all fifteen maps: the record list 3,576 words (map m needs 3,570 with the one read past the end), the slot-4 and slot-3 targets 16 each (14 and 13 on map m), the slot-`0x0F` targets 32 (30 on map o), the soldiers 160, the four gun lists 16 each, `MasterList` and `AthList` 278. Source: `SPEC.md` 7.2, bullet 5; `re/notes/porting-m4.md`, "Where mission memory lives"; `src/mission.def`; `tests/test_mission.py`, `test_the_pools_hold_every_map`. In the chapter: "all fifteen maps", the record list as the example.

## 4. The registered state

37. A **registry** (the term, defined here): one of the port's three lists of what it took over from the original, each entry a line of macro calls tied to the original's address or offset; `src/globals.def` for the plain variables, `src/mission.def` for the tables, `src/records.def` for the records' layouts. Source: the three files' opening comments; `SPEC.md` 7.2, last bullet.
38. `src/globals.def`'s form: `WOF_GLOBAL(name, type, orig_address)` and `WOF_GLOBAL_ARRAY(name, type, count, orig_address)`; the name is the one `re/names.txt` gives the address. Source: `src/globals.def` lines 9 to 12.
39. The technique is the X-macro: the same list is included several times, its macros defined anew each time, so that one list makes the struct's members, the code that starts them from the executable's data and the code that reads and writes them by address. Source: `src/wof.h` (`wof_globals_t`: `#define WOF_GLOBAL(name, type, addr) type name;` then `#include "globals.def"`); `src/core.c` (`wof_globals_from_image`, `wof_global_byte`, `wof_original_store8`); the X macro reference. **(reference)** for the name.
40. The entries become the members of `wof_globals_t`, which lives inside the core's state, so a global is saved and loaded with the state "and can never be forgotten there"; the test harness reads the same list through `tests/shim.c` and uses the original addresses to copy state between the original and the port. Source: `src/globals.def`, opening comment.
41. The entries are grouped by width, longs first, so that the struct has no padding and is exactly the sum of its members; `test_the_globals_struct_is_the_sum_of_its_members` holds it. Source: `src/globals.def`, opening comment; `tests/test_oracle_m3.py` line 57.
42. The struct's order is not the original's memory order; the address ties the two together. Where the original's adjacency is itself behaviour (`key_get` reads one entry past the key buffer) the routine spells the neighbour out. Source: `src/globals.def`, opening comment.
43. `src/globals.def` holds 252 entries: 238 variables and 14 arrays. Source: counts table; chapter 8's box gives 252 variables registered.
44. `src/mission.def` lists the tables: 30 at fixed addresses in the data (`WOF_TABLE(name, rec, count, addr)`) and 21 allocations (`WOF_POOL(name, rec, capacity, pointer)`), found in the original through the pointer it keeps and held by the port at a fixed place, zeroed when the original allocates. Source: `src/mission.def`, opening comment; counts table; chapter 8's box (30 tables, 21 blocks).
45. `src/records.def` describes every record once, field by field, with the original's offset and width; `src/wof.h` makes each a C struct in the original order, and `tests/shim.c` makes the same description the table by which the harness copies a record between the original's big-endian bytes and the port's struct; the fields tile each record exactly, which `tests/test_mission.py` holds. 26 records, 221 fields. A field is named by its role, or by its offset where its role is not known yet (`w1c`, the word at `+0x1C`). Source: `src/records.def`, opening comment; counts table.
46. A **kind** (the term, defined here: Kind (of a field)): how a field travels between the original's bytes and the port's struct. Seven: `WOF_K_PLAIN` an integer of the same width on both sides; `WOF_K_SHAPE` a shape pointer of 4 bytes in the original, a shape handle of 2 in the port; `WOF_K_MAP` a pointer into the map's records, a byte offset; `WOF_K_POOL` a pointer to an allocation, a flag saying whether there is one; `WOF_K_SOUND` a pointer into a sound effect, a sound handle; `WOF_K_SONG` a pointer into the song data, its offset in the data; `WOF_K_VECTOR` a level-4 vector, the handler it names. Fields by kind: 194, 2, 1, 7, 4, 12, 1. Source: `src/records.def`, opening comment; `src/wof.h` lines 402 to 408; counts table. (The task's outline names five; the file has seven.)
47. Listing 3, the player's record: 30 bytes (`0x1E`) at `0x025078`, its fields in the original's order with their offsets; the shape at `+0x04` is a 4-byte pointer in the original and a 16-bit handle in the port, kind `WOF_K_SHAPE`, the next field at `+0x08`. Source: `src/records.def`, the record `player`; chapter 14 (the player's record).
48. Why the registered state: the harness copies the original's state into the port and compares the two field by field after every pass and tick (chapter 8, the open and the closed loop); and nothing can be forgotten in a save state. Source: `src/globals.def`, `src/mission.def`, `src/records.def` openings; `SPEC.md` 8; `re/notes/porting-m4.md`, "How the port is held to the original".
49. The **registered state** (the term, defined here): the variables, tables and records the registries list, kept inside the core's state, each tied to its original address. Source: claims 37 to 45. Chapter 5 met it in plain words, chapters 17 and 18 linked its section.
50. The registered variables start as the original's data hunk starts them: every entry whose address lies in the stored part of the data is loaded from the executable's image (`data_image`, chapter 3), turned to the host's byte order, when `wof_init` runs. Source: `src/wof.h` (comment above `wof_globals_from_image`); `src/core.c` lines 100 to 138; `SPEC.md` 5, step 1.
51. The registries also let the port read and write by original address: `wof_original_store8` writes a byte into whichever registered variable or fixed table covers the address, as the original's move to that address would, and reports 0 where nothing the port keeps covers it; `wof_original_load8` reads one. The wreck's forty-first word reaches the aircraft records so (chapter 16); the saved game's writer takes its bytes so and the loader puts them back so, which leaves the pointer fields alone (chapter 17). Source: `src/core.c` lines 213 to 312; `re/notes/porting-m7.md`, "The port" and "Part 2: the port"; chapter 16's sidebar (`wof_original_store16`). Listing 4.

## 5. What the state holds, and what lies outside it

52. `wof_state_t` holds everything the core may change while running, in one struct; the comment: "so that `wof_state_save` is a copy and adding state cannot silently break the round trip". Source: `src/wof.h`, the comment above the struct.
53. Its 25 members: the magic and the version, the seed, the entropy stream's state, the counts of VBlanks, ticks and passes, the video rate, the raw controller state of the last VBlank, the flip's preference and whether one was given, the count of stand-ins reached, the VBlanks since the last pass began, seven members of the keyboard assist, Paula's state, the timer's and the level-4 vector's, the registered variables `g`, the registered tables `m` and the front end `f`. Source: `src/wof.h` lines 494 to 521 (listing 2); counts table.
54. The front end's part holds the resume points of 22 coroutines, every local that lives across a wait, the viewport records and the display memory itself, the mirror markers of `hellcat.shp` and `Torpedo.shp`, and what the original keeps as pointers that are not game data; nothing in it is a pointer: a viewport names its surface by an offset into the display memory and its neighbour by an index. Source: `src/wof.h`, `wof_front_t` and its comments; counts table (22 `wof_ctx_t` members).
55. The display memory is in the state, so a loaded state brings the picture back with the logic; it is most of the state's size: 341,536 of 368,080 bytes. Source: `re/notes/porting-m3.md`, "Views, viewports and what reaches the output"; `src/wof.h` (`WOF_VRAM_BYTES`: 2 x 640 x 260 + 84 x 8 x 13); the run for a fact (`wof_state_size`). In the chapter: "about 360 KB, most of it the display memory", in a figures box.
56. Paula's state joined the state with the sound engine and the timer's and the level-4 vector's with the music player (the versions 10 and 11). Source: `re/notes/porting-m8.md`, "The port" ("Paula's state ... is part of the save state. The state version is 10") and "Part 2: the music player", "The port" ("The state version is 11"). The chapter names no version but the current one.
57. The keyboard assist's state is part of the state, and none of it is a registered variable. Source: `SPEC.md` 6.1 ("Its state is part of the save state and none of it is a registered global"); `src/wof.h` (`assist`, `assist_prev`, ...).
58. The flip's preference and whether it was given are in the state; a core never given one behaves as the original (chapter 1). Source: `src/wof.h` (`invert_pref`, `invert_given`); `SPEC.md` 6.1.
59. Outside the state: the arena's contents, the blob of files and the assets loaded from it, read-only after `wof_init` (`src/core.c` lines 59 to 64; `SPEC.md` 6.1, "Loaded assets live in the arena, outside the state"); the framebuffer with its palette rows and palettes, which `wof_pass` and a load make again from the state (`src/wof.h`, the comment above `wof_state_t`; `src/video.c` lines 16 to 18; `src/core.c`, `wof_state_load`); the queue of mixed audio frames, so that a replay renders the same sound however the shell asks (`SPEC.md` 6.5; `re/notes/porting-m8.md`, "The port", "The mixer"); the overlay of written files (claim 92); the settings `wof_init` leaves alone, the fade step, the VBlanks a pass and the audio output rate (`re/notes/testing.md`, "A fresh core for every test"; `src/fade.c` line 20, `src/core.c` line 473, `src/audio.c` line 211); the exit request, "neither a registered global nor part of the save state" (`SPEC.md` 6.1); the native library's recording and test entries (claims 113, 114).
60. `wof_init` zeroes the whole state, sets the magic, the version, the seed and the video rate to 60, starts the registered variables from the executable's data, seeds the entropy stream, opens the file system, empties the overlay, sets up the picture, the display, the sound, the input and the keys, loads the assets, and runs the main program to its first wait; it does not reset the arena, because the shell has put the blob there before calling it. Source: `src/core.c` lines 13 to 38; `SPEC.md` 6.1; `src/mem.c`, the comment above `wof_alloc`.

## 6. Save states

61. A **save state** (the term, defined here): the bytes of the core's state, copied whole; loaded into a core of the same build, the game goes on as if nothing had happened. Source: `SPEC.md` 6.1 ("A save state is the bytes of the core's state struct, which holds no pointers"); the reference (an emulator's save state is the emulated program's memory stored). **(reference)** for the emulator's sense.
62. It is copied whole, padding included, and `wof_init` zeroes the struct, so the round trip is exact; it is valid between little-endian hosts, which both targets are. Source: `SPEC.md` 6.1; `src/wof.h` comment ("Both targets are little-endian ... if a big-endian target ever appears this needs accessors").
63. The struct is copied byte for byte rather than assigned, because an assignment need not carry the padding between members, and the state has some. Source: `src/core.c` lines 91 to 96.
64. Loading checks the magic, `0x574F4653`, the letters `WOFS`, and the version, 12, and leaves the running state untouched when either differs; a test hands it bytes it did not write. Source: `src/core.c`, `wof_state_load`; `src/wof.h` (`WOF_STATE_MAGIC`, `WOF_STATE_VERSION 12u`); `tests/test_core_wasm.py`, `test_state_load_rejects_foreign_data`.
65. The version is counted up whenever the state's layout changes, from 1 at the core's first commit to 12, so that a state from another layout is refused rather than read into the wrong members. Source: `git log -L` of the `WOF_STATE_VERSION` line (counts table: eleven changes); the reason is the check's (claim 64) and the comment's ("adding state cannot silently break the round trip"). The chapter gives no history.
66. On a load the mirrored shapes follow their markers, which the state holds (chapter 12), the drawing target is set again from the state, and the picture is made from the state: "the picture follows the state, not the other way". Source: `src/core.c` lines 85 to 88; `re/notes/porting-m4.md`, "Save states and the mirror markers" (116 records of `hellcat.shp`, 100 of `Torpedo.shp`); the control that left the markers out of a loaded state gave another picture and state 400 VBlanks on (`re/notes/porting-m4.md`, the controls).
67. A state saved inside a wait resumes there, because the resume points and the locals kept across a wait are part of it. The tests save a state flying left with the shapes mirrored, inside the restart's waits in a tick, and paused, load it into the same core and into a fresh one with another seed, and find the state, the picture and the next 400 VBlanks the same, on the native library and on the WebAssembly core, the two agreeing. Source: `SPEC.md` 6.1; `tests/test_state_m4.py`, `test_a_state_saved_in_a_flight_continues_identically` and its docstring.
68. A state carried across a reload of the page is not supported: the loaded assets live in the arena, outside it; within a session a state stays valid, since the arena never reuses memory. Source: `SPEC.md` 6.1.
69. The shell wraps the two entries but nothing in it calls them: the player saves the game's own way (chapter 17); save states serve the replays and the tests. Source: `web/core.js` (`saveState`, `loadState`, lines 220 to 228); `grep -rn "saveState\|loadState" web/` (only the definitions); `SPEC.md` 6.1 (`wof_state_size` "save states, replays, tests").
70. Listing 5, `test_state_round_trips` of `tests/test_core_native.py`: a core on seed 7 runs 100 VBlanks and is saved with its picture; 60 more give a state that differs; loaded, it shows the saved picture, and the same 60 VBlanks give the same bytes. Source: the test, lines 44 to 57.

## 7. Coroutines

71. The original blocks: it waits for VBlanks, for `Delay`, for the fire button, for fades and for the song's fade; a page cannot block, since it must hand control back to the browser between frames or nothing is drawn and no key arrives (chapter 19); and from a page opened from a file there is no `SharedArrayBuffer` in which a worker could block. Source: `SPEC.md` 6.3; `src/coro.h` opening comment; chapter 19 ("The waits, the drawing and the files").
72. `SharedArrayBuffer` gives the main thread and workers shared memory, in which a worker can block with `Atomics.wait()`; a browser offers it only to a secure, cross-origin-isolated page, set up by two HTTP headers, which a file opened from the disk does not come with. Source: the MDN reference. **(reference)**
73. A **coroutine** (the term, defined here): a routine that can stop at a wait, give control back, and go on from there at the next call. The port's are stackless, in the protothreads style: a `switch` on a stored resume point, and every local that lives across a wait moved into a context struct, while the original's control flow is kept line for line. Source: `SPEC.md` 6.3, first bullet; `src/coro.h` opening comment; the Coroutine and Protothread references. **(reference)** for the general sense and for protothreads.
74. Protothreads are by Adam Dunkels and Oliver Schmidt, after Simon Tatham and Tom Duff; a `switch` jumps back into the middle of the routine, and locals do not keep their values across a yield. Source: the Protothread and Tatham references. **(reference)**
75. The macros (listing 1): `CO_BEGIN` opens the `switch` on the context's resume point with `case 0`; `CO_WAIT` stores the line number, returns `WOF_CO_WAIT` and places a `case` label with that number; `CO_WAIT_UNTIL` does the same and tests its condition at once, so that a child coroutine runs its first stretch in the pass its parent reached it in; `CO_CALL` resets a child's context and waits until it returns `WOF_CO_DONE`; `CO_RETURN` leaves early; `CO_END` closes the `switch`, sets the point back to 0 and returns done. Source: `src/coro.h` lines 24 to 46.
76. A **resume point** (the term, defined here): the number a coroutine's context keeps of where it waits, the line number of the wait in its source file, 0 for not started, which a zeroed context gives. Source: `src/coro.h` ("A resume point. 0 is "not started", which is what a zeroed context gives"; `__LINE__`); `src/wof.h` (`wof_ctx_t`, `uint16_t line`).
77. The three rules the macros cannot check: no `CO_` macro inside a `switch` of the routine's own; a local that must survive a wait belongs in the context struct, since the resume jumps past its initialisation (a local read after a `CO_CALL` is read uninitialised); every coroutine returns `wof_co_t` and nothing else. Source: `src/coro.h` opening comment; `re/notes/porting-m3.md`, "The rule that makes the two agree". Chapter 19's sidebar named the first two.
78. One context a routine is enough, and no stack is needed, because no routine of the front end is ever inside itself; the state holds 22. Source: `src/wof.h`, the comment on `wof_ctx_t`; counts table.
79. The unit of time: one `CO_WAIT` is one VBlank, because the shell calls `wof_pass` once after every `wof_vblank` and the headless original delivers a VBlank exactly where the program waits; `wof_init` runs the coroutine to its first wait, inside `display_init`, so pass N runs what the original runs after VBlank N, and the music's first call falls on VBlank 1 on both sides. Source: `src/coro.h` opening comment; `re/notes/porting-m3.md`, "The rule that makes the two agree"; `src/core.c` lines 33 to 36; chapter 6 (the wait points).
80. During play a pass is one round of the inner loop; the logic tick belongs to the coroutine because the restart after a lost aircraft waits inside it (chapter 14), and the next mission is the mission coroutine's continuation (chapter 17); the front end's waits are chapter 19's, the song's fade chapter 18's. Source: `SPEC.md` 6.3, bullets 2 and 5; chapters 14, 17, 18, 19.
81. What it costs a reader: the resume point is a line number, so a change that adds or removes a line in a file with coroutines, a comment included, changes the core's bytes and the page's. Source: `CONTROLLER.md`, "Pitfalls that cost time" (the `__LINE__` pitfall); `src/coro.h` (`CO_WAIT` stores `__LINE__`). Told as a fact, without its history.

## 8. The arena

82. The **arena** (the term, defined here): one block of memory reserved once, from which the core hands out what the original would have asked the system for. 3 MB of BSS, which costs nothing in `dist/core.wasm`, only in the page's memory. Source: `src/mem.c`, `WOF_ARENA_SIZE` and its comment ("This is BSS: it costs nothing in dist/core.wasm, only in the page's linear memory"); the region reference. Chapter 2 met it in plain words.
83. It has two ends: what outlives a load grows up from the bottom; the buffer a file is read and unpacked into is scratch and grows down from the top, so that giving it back is one assignment however much was taken below it meanwhile; that is what the original's `Free` of a just-loaded file amounts to. Source: `src/mem.c`, the comment above `arena`; `re/notes/porting-m1.md`, "Decisions the port made"; `src/wof.h` (`wof_arena_mark`, `wof_arena_release`, `wof_scratch_alloc`).
84. Every hand-out is zeroed, from either end, and nothing is ever freed; out of memory returns 0 and the caller checks. Source: `src/mem.c` (`wof_alloc`, `wof_scratch_alloc`; the comment above `wof_alloc`).
85. The shell takes the blob's place in the arena before `wof_init`, and its own buffers for the sound and for a state. Source: `web/core.js` lines 22 to 38; `src/mem.c`.
86. Nothing is taken from the arena once the assets are loaded: thirty-one mission setups in a row leave `wof_arena_used` where the first left it. Source: `re/notes/porting-m4.md`, "Where mission memory lives"; `tests/test_mission.py`, `test_thirty_mission_setups_do_not_grow_the_arena` (it counts to 31 missions).
87. `wof_arena_reset` empties it for the tests, before a fresh core; a scratch buffer is given back with `wof_arena_release`. Source: `src/wof.h` ("host only, before a fresh core"); `tests/conftest.py`, `NativeCore` ("a new NativeCore resets the arena and re-initialises").
88. Figures box: the arena 3 MB (3,145,728 bytes); the blob about 530 KB (543,240 bytes); in use after `wof_init`, the blob included, about 1.1 MB (1,128,368 bytes). Source: the run for a fact; `src/mem.c`. (`src/mem.c`'s comment says the blob is "about 530 KB"; measured 543,240 bytes, which rounds to 530 KB at 1,024 bytes a KB.)

## 9. The file system

89. The build packs 55 files into one blob; the core reads it as it is: `WOFS`, a version, the count and the directory's offset, then a 40-byte entry for each file, a 32-byte name, an offset and a length, all big-endian. Chapter 3's sidebar told the layout; the chapter links it. Source: `SPEC.md` 5, step 2; `src/fs.c` opening comment; the run for a fact (55 files, version 1).
90. The names are paths relative to the disk's `Wings_of_Fury` directory, the original's current directory, so the ported loaders pass the original's own names; the lookup ignores case, as AmigaDOS does (chapter 3). Source: `SPEC.md` 5, step 2; `src/fs.c`.
91. A lock and a file handle are both an index into the directory, with a read position, so neither allocates nor can fail for want of memory. Source: `src/fs.c` opening comment; `src/wof.h` (`wof_file_t`).
92. The **overlay** (the term, defined here: Overlay (of the file system)): the files the game writes, the high scores and the saved games, kept in front of the read-only disk: a written file shadows the disk's file of the same name and a deleted one hides it, which is what AmigaDOS does to the game. It is not part of the core's state: a save state is a snapshot of the running game, and loading one must not un-write a file. Source: `src/fs.c`, "the write side"; `re/notes/porting-m3.md`, "The file system's write side"; the Union mount reference for the general idea. **(reference)** for the general idea.
93. It has 12 slots, the dialog's six, the high scores and room, each holding up to 12,412 bytes, the largest saved game the port's tables allow. Source: `src/fs.c` (`FS_WRITE_MAX`, `FS_FILE_MAX`); `src/wof.h` (`WOF_SAVE_MAX`); chapters 9 and 17.
94. The shell watches `wof_fs_changes` and, when it moves, stores the written files through their count, names, sizes and bytes; at the start it hands them back with `wof_fs_put` in the order it stored them, because that order is part of what the dialog lists. Source: `src/wof.h`, the comment above `wof_fs_changes`; `src/fs.c` (`wof_fs_put`); `SPEC.md` 6.2, "Storage".
95. The directory's order follows from the names alone (chapters 19 and 20). Source: `src/fs.c`, "the game's own directory, in order"; chapters 19, 20.
96. A loader is the original's own routine, ported, over this glue: `load_file` keeps its shape over the dos calls of `src/fs.c`, because the sizes and a one-byte overrun are behaviour (chapter 3). Source: `src/load.c` opening comment; chapter 3, "The little there was to decode".

## 10. The two inputs besides the hands, and the standard

97. The entropy stream is a small generator inside the core, a multiply and an add on 32 bits, seeded by `wof_init`, whose values are shaped like the beam register, the high byte 0 to 255 and the low byte 0 to `0xE3`; one value is taken for each call of `rand_beam`, in the original's order; the test builds can hand in a stream of their own. Chapter 6 told it. Source: `SPEC.md` 7.3, bullet 1; `src/rand.c`; chapter 6.
98. No state outside the core influences the logic, but two named inputs: the entropy stream and the map list's address, which a defect of the original makes part of a wreck's arithmetic (chapter 20); the tests fill it with the headless original's at every map load, the page with `0x24F404`. Source: `SPEC.md` 7.3, bullet 2; chapter 20.
99. The video standard is a setting, `wof_set_video_hz`, 50 or 60, which the shell sets at the start: it sets the VBlank rate the shell's clock keeps and the clocks of the sound model (Paula's colour clock, the timer's count carried over); nothing in the logic reads it, since the program never asks (chapter 7). Source: `src/core.c` (`wof_set_video_hz`: `wof_paula_rate`); `SPEC.md` 6.1, 6.2 ("Video standard"), 6.5; `re/notes/random.md`, "Video rate"; chapter 7.

## 11. The interface the shell sees

100. `src/wof.h` exports 53 entries; the specification's names are normative, and its signatures may grow; what the header adds are queries the shell needs in order to hard-code nothing, and the arena. Source: `grep -c "^WOF_API(" src/wof.h`; `SPEC.md` 6.1 ("names are normative, signatures may grow"); `src/wof.h`, the comment "Additions to SPEC 6.1".
101. The interface table, grouped by purpose (claim 100's 53 entries):
    - the start and the clock, 4: `wof_init`, `wof_set_video_hz`, `wof_vblank`, `wof_pass` (chapters 7, 23);
    - the keys, 3: `wof_key`, `wof_port_key`, `wof_line_editor_active` (chapter 19);
    - the settings, 8: the flip's preference, the keyboard assist, the fade step and the VBlanks a pass, each set and read (chapters 1, 7, 19);
    - the picture, 8: `wof_framebuffer`, its width and height, `wof_palette_rows`, `wof_palettes`, their count and their colours, `wof_display_list` (chapters 11, 23);
    - the sound, 1: `wof_audio_render` (chapters 18, 23);
    - the state, 3: `wof_state_size`, `wof_state_save`, `wof_state_load` (here);
    - the arena, 4: `wof_alloc`, `wof_arena_reset`, `wof_arena_size`, `wof_arena_used` (here);
    - the files, 7: `wof_fs_count`, `wof_fs_changes`, the written files' count, name, size and bytes, `wof_fs_put` (chapters 19, 23);
    - the requests, 4: `wof_request_pause`, `wof_paused`, `wof_request_continue`, `wof_exit_requested` (chapters 1, 23);
    - the counters, 5: `wof_vblank_count`, `wof_tick_count`, `wof_pass_count`, `wof_standin_hits`, `wof_assets_ready` (chapters 8, 23);
    - development, 6: `wof_dev_player`, `wof_dev_game`, `wof_dev_demo_record`, `wof_demo_recording`, `wof_dev_set_score`, `wof_dev_open_dialog` (chapters 17, 19, 23).
    4 + 3 + 8 + 8 + 1 + 3 + 4 + 7 + 4 + 5 + 6 = 53. Source: `src/wof.h`, the `WOF_API` lines and their comments.
102. `wof_vblank` takes the raw controller state of one VBlank, five bits, not a finished input byte, and runs the original's tap and hold timing and the queue inside the core (chapter 7). Source: `SPEC.md` 6.1, the paragraph on `wof_vblank`; chapter 7.
103. Its order of work: opposing directions cancelled; Paula's events of the VBlank that has passed; the sound engine's VBlank server with the interrupts it makes deliverable; the controller state kept and the VBlank counted; the flag the waits spin on; the pause's gate; the fire button's timing; the assist's watch; the divider; on every fourth VBlank the sample, from a played demo or from the controller as the assist hands it; the queue of six; a recorded demo's byte; the ticker. Source: `src/input.c`, `wof_vblank` (lines 269 to 367). The chapter gives it in one sentence.
104. `wof_key` is the port of the original's key handler; `wof_port_key`, the shell's entry, is the port's key layer in front of it (chapter 19). Source: `SPEC.md` 6.1; chapter 19.
105. `wof_audio_render` hands out the frames the VBlanks mixed, as many as the emulated time lasts at the rate asked for, and returns their number; the rest of the shell's buffer is silence: 960 frames a VBlank at 48,000 a second on PAL, 735 at 44,100 on NTSC. Source: `SPEC.md` 6.1 (the comment) and 6.5; `tests/test_core_wasm.py`, `test_the_pcm_is_emulated_time`.
106. The pause is a request, not a toggle: the next `ingame_keys` of a mission takes it as Escape; outside a mission it is dropped. `wof_exit_requested` is raised where the machine would end the program and never cleared. Source: `SPEC.md` 6.1; `src/wof.h` comments.
107. The development entries are offered by the shell only while the diagnostics overlay is up; they are not the game. Source: `SPEC.md` 6.1; `src/wof.h` comment.
108. The shell asks the core for the picture's geometry and never hard-codes it. Source: `SPEC.md` 6.1 (`wof_framebuffer_width`, "the shell queries geometry, never hard-codes it"); `web/core.js` lines 16 to 19.
109. The video model as the interface: an indexed framebuffer of 640 by 214, a byte a pixel; a palette for every row; 24 palettes of 32 colours, palette 0 black for the rows no viewport covers; the low-resolution areas doubled; a palette entry RGBA in memory order, which a canvas takes without conversion; the display list, a record for every shape drawn in a pass (its name, place, layer, flags and owner), for a renderer that could draw the game anew, which the classic renderer ignores; nothing in the logic reads a pixel back. Chapter 11 told the mechanism. Source: `SPEC.md` 6.4; `src/wof.h` (geometry, `WOF_PAL_COUNT`, `WOF_RGBA`, `wof_draw_t`, `WOF_DRAW_MAX` 1024); the run for a fact (640, 214, 24, 32); `tests/test_core_wasm.py`, `test_display_list_exists_and_the_briefing_fills_it`.
110. The audio model: chapter 18's Paula model, mixed VBlank by VBlank into a queue outside the state. Source: `SPEC.md` 6.5; chapter 18.

## 12. For the developer

111. The native library is the same sources compiled by clang with `WOF_TRACE` switched on, plus `tests/shim.c`; the page's core is built without either. Source: `tools/build.py` (`CC_NATIVE`, `compile_native`); `SPEC.md` 5.
112. `src/trace.c` records what the port did, the files opened, the songs asked for, every drawing call, for the comparisons with the headless original's observers; its calls are macros that disappear in the page's build. Source: `src/trace.c` opening comment; `src/wof.h` (`#else` branch of `WOF_TRACE`).
113. `tests/shim.c` gives the tests access to the core's internals through plain scalar entries, about 130 (129 functions named `wt_`), so that no test mirrors a C struct's layout; nothing in `src/` may call it. Source: `tests/shim.c` opening comment; counts table.
114. The recording lies beside the core's state, not in it, and survives `wof_init`, so the tests put it back before every test (chapter 9). Source: `re/notes/testing.md`, "A fresh core for every test"; `tests/test_isolation.py`.
115. A test holds that the page's core has none of it: no function of the WebAssembly's name section begins with `wof_test_` or `wof_trace`. Source: `tests/test_state_m4.py`, `test_the_release_core_has_no_test_hooks`.
116. The tests bind the core through ctypes with explicit argument and result types, 22 entries in `tests/conftest.py`'s `NativeCore`; chapter 24 tells the suite. Source: `tests/conftest.py` lines 186 to 228; counts table.
117. The harness converts the original's state field by field by the kinds, `tests/m4state.py`; chapter 24. Source: `re/notes/porting-m4.md`, "Where mission memory lives"; `re/notes/porting-m8.md`, "The port".

## 13. The hand-off

118. The chapter in one sentence: the core is one C program that keeps everything that changes in one struct tied to the original's addresses, waits by returning, and asks the page for nothing. Source: claims 3 to 110.
119. Chapter 23 tells the shell, which drives this interface at the VBlank rate and puts the picture and the sound on the page. Source: `book/BOOK.md` 3, chapter 23; the stub's subtitle.

## The figures

| # | File | Kind | What it shows |
|---|---|---|---|
| (a) | `docs/figures/core-state.svg` | hand-drawn, new | claims 53 to 59: on the left the core's state as one block of boxes, top to bottom the magic and version, the stream and the counters, the controller and the preferences, the stand-ins and the pass, the assist, Paula, the timer and the vector, the registered variables, the registered tables, the front end; on the right what lies outside, the arena with the files and the assets, the framebuffer and palettes, the queue of audio frames, the overlay of written files, the settings `wof_init` leaves alone, the native library's recording and entries; saved in gold, not saved in grey; no count; viewBox and slack measured at the draft |

Figure (b), the arena's two ends, is a figures box instead (claim 88), with a sentence for the two ends; figure (c), the coroutine's resume, is left out: listing 1 and the paragraph carry it.

## The figures boxes planned

| Box | Rows |
|---|---|
| The arena | its size, the blob, in use after `wof_init` (claim 88) |
| The registries | 252 variables, 30 tables, 21 allocations, 26 record layouts, the state's size about 360 KB with the display memory about 330 KB (claims 43 to 45, 55) |

## The listings

| # | Kind | Name | Source | Shown before? |
|---|---|---|---|---|
| 1 | text | `coro-macros` | `src/coro.h`, from `typedef enum` to `#define CO_RETURN` | no |
| 2 | text | `state-struct` | `src/wof.h`, from the comment above `wof_state_t` to `WOF_STATE_VERSION` | no |
| 3 | text | `player-record` | `src/records.def`, the player's record | no |
| 4 | c | `wof_original_store8` | `src/core.c` | no (chapter 20 showed `data_byte`, the reading side in `src/player.c`) |
| 5 | text | `arena-ends` | `src/mem.c`, from the comment above `wof_alloc` to `wof_arena_used` | no |
| 6 | py | `test_state_round_trips` | `tests/test_core_native.py` | no |

The `text` kind serves a range of a `.h` or `.def` file; its first line, a comment naming the file and the lines, is written in C's comment syntax for a `.c`, `.h` or `.def` file and in `#` for any other, a change of `book/tools/listings.py` that leaves the existing `text` listings as they are. Fenced `c`. `wof_original_store8` is shown in place of `wof_original_load8`: it shows the registry's variables expanded inline, where the load leaves them to `wof_global_byte`.

## The terms

| Term | Defined here | Elsewhere | The glossary's computed line |
|---|---|---|---|
| Freestanding | claim 5 | cppreference, Conformance | First met and defined in chapter 22. |
| Arena | claim 82 | Wikipedia, Region-based memory management | First met and defined in chapter 22 (chapter 2 says "one arena" in plain words) |
| Registry | claim 37 | Wikipedia, X macro | First met and defined in chapter 22. |
| Registered state | claim 49 | none | First met and defined in chapter 22 (chapter 5 says it in plain words; chapters 17 and 18 link chapter 5's section) |
| Kind (of a field) | claim 46 | none | First met and defined in chapter 22. |
| Sound handle | claim 33 | Wikipedia, Handle (computing) | First met and defined in chapter 22 (chapter 18 says it in plain words) |
| Save state | claim 61 | Wikipedia, Saved game | First met and defined in chapter 22. |
| Coroutine | claim 73 | Wikipedia, Coroutine; Wikipedia, Protothread | First met and defined in chapter 22 (chapters 14, 17, 19 say it and link the chapter's page) |
| Resume point | claim 76 | Simon Tatham, Coroutines in C | First met and defined in chapter 22. |
| Overlay (of the file system) | claim 92 | Wikipedia, Union mount | First met and defined in chapter 22 (chapter 19 says "the file system's overlay" in plain words) |

Linked, defined earlier: Core, Shell, WebAssembly, Native library, Faithful port, Listing, Routine, Routine inventory, Fixed load layout, int (the C type), Sign extension, Upper word, Condition codes, Arithmetic shift, Fast floating point, Big-endian, Little-endian, Shape handle, Pointer field, Mirror marker, Manifest, Oracle, Headless original, Harness, Open loop, Closed loop, Completeness list, Stand-in, Entropy stream, Wait point, VBlank, Pass, Logic tick, Schedule, Indexed framebuffer, Band, Palette, Paula, Level-4 vector, Keyboard assist, Vertical flip, Key layer, Fixture, Stub. The overlay is not the diagnostics overlay, said in a clause. Not defined, glossed: context struct (the struct that holds a coroutine's resume point and kept locals), display list (a sentence), X-macro (inside Registry's definition).

## Left to later chapters

The shell's clock, picture, sound, keys and storage at work (chapter 23); the suite's layers, the harness's conversion `tests/m4state.py`, the replays (chapter 24); the build, the working method of `SPEC.md` 7.4 and how to extend the port (chapter 25).

## Counts, and where they were counted

| Count | Where, how |
|---|---|
| 252 registered variables: 238 and 14 arrays | `grep -c "^WOF_GLOBAL(" src/globals.def`; `grep -c "^WOF_GLOBAL_ARRAY(" src/globals.def` |
| 30 tables, 21 allocations | `grep -c "^WOF_TABLE(" src/mission.def`; `grep -c "^WOF_POOL(" src/mission.def` |
| 26 records, 221 fields (215 and 6 arrays) | `grep -c "^WOF_RECORD(" src/records.def`; `grep -c "^WOF_FIELD(" src/records.def`; `grep -c "^WOF_FIELD_ARRAY(" src/records.def` |
| 7 kinds; fields by kind 194, 2, 1, 7, 4, 12, 1 | `src/wof.h` lines 402-408; `grep -oh "WOF_K_[A-Z]*)" src/records.def \| sort \| uniq -c` |
| 25 members of `wof_state_t` | `sed -n 494,521p src/wof.h \| grep -cE "^\s+(uint\|wof_)[a-z_0-9]+\s+[a-z_]+(\[[0-9]+\])?;"` |
| 22 resume points | `grep -c "wof_ctx_t co_" src/wof.h` |
| version 12, magic `0x574F4653` | `src/wof.h` lines 523-524 |
| eleven changes of the version, 1 to 12 | `git log -L '/define WOF_STATE_VERSION/,+1:src/wof.h'` |
| 6 macros | `src/coro.h`, `#define CO_` |
| 53 exported entries | `grep -c "^WOF_API(" src/wof.h` |
| 3 MB = 3,145,728 bytes | `src/mem.c` (`WOF_ARENA_SIZE`); `wof_arena_size()` in the run for a fact |
| blob 543,240 bytes, 55 files, version 1; arena in use after `wof_init` 1,128,368 bytes; state 368,080 bytes; 640, 214, 24, 32 | the run for a fact: `tests/conftest.py`'s `payload(page, 'wof-fs')` out of `dist/wof.html`, `wof_alloc`, `wof_init(1, ...)`, `wof_arena_used`, `wof_state_size`, `wof_fs_count`, the geometry queries |
| display memory 341,536 bytes | `src/wof.h`, `WOF_VRAM_BYTES` = 2 x 640 x 260 + 84 x 8 x 13 |
| 40-byte entries, 32-byte names | `src/fs.c` (`FS_ENTRY`, `FS_NAME_MAX`); `SPEC.md` 5, step 2 |
| 12 overlay slots; 12,412 bytes | `src/fs.c` (`FS_WRITE_MAX`); `src/wof.h` (`WOF_SAVE_MAX`: `0x84A` + 2 + 3,576 x 2 + 4 x 16 x 14 + 32 x 14 + 160 x 8 + 2 x 16 x 16 = 12,412) |
| 31 setups | `tests/test_mission.py`, `test_thirty_mission_setups_do_not_grow_the_arena` (`while missions < 31`); `re/notes/porting-m4.md` |
| 960 and 735 frames a VBlank | `tests/test_core_wasm.py`, `test_the_pcm_is_emulated_time` (`pal48000` 960, `ntsc44100` 735) |
| 129 `wt_` entries | `grep -E "^[a-zA-Z_][a-zA-Z_0-9 \*]*\bwt_[a-z_0-9]+\(" tests/shim.c \| wc -l` |
| 22 bound entries | `tests/conftest.py`, the `signatures` of `NativeCore` |
| 33 `orig songplay` comments | `grep -c "orig songplay" src/music.c` |
| 1,024 display list entries a pass | `src/wof.h`, `WOF_DRAW_MAX` |

## Unsourced

- None of the outline's points is without a source. Left out as unsourced: why a struct is never cast from file bytes beyond the byte order (the specification gives no other reason; the chapter gives the byte order alone).

## Where a source was wrong or silent

- **The glossary.** The task says Core, Shell, WebAssembly, Faithful port, Stand-in and Entropy stream are not entries yet; all six are, defined in chapters 1, 6 and 8. The chapter links them. Registered state, Save state and Coroutine are not, and the chapter defines them.
- **The kinds.** The task's outline names five kinds; `src/records.def` has seven, with `WOF_K_MAP` and `WOF_K_POOL`. The chapter gives seven.
- **The assist's setting.** The outline counts the assist among the settings `wof_init` leaves alone; the assist's switch is inside the state (`wof_s.assist`), which `wof_init` zeroes, and the page switches it on after `wof_init`. The settings left alone are the fade step, the VBlanks a pass and the audio output rate (`re/notes/testing.md`). The chapter says so.
- **`CO_YIELD`.** `SPEC.md` 6.3 says a wait becomes `CO_WAIT_UNTIL(condition)` or `CO_YIELD()`; `src/coro.h` has no `CO_YIELD`: `CO_WAIT` is the yield, and `CO_CALL` the wait for a child. The chapter follows `src/coro.h`. For the controller: `SPEC.md` 6.3's macro name.
- **Traps "asserted".** `SPEC.md` 7.1 asks for an assertion in test builds; the core has no assertion: `divs_w` of `src/enemy.c` records the trap in the trace and returns the dividend's low word, and `src/ffp.c` counts its traps. The chapter says "records" and "counts".
- **Stale comments in `src/`, for the controller.** `src/mem.c`'s opening comment lists "the viewport surfaces" among what grows from the arena's bottom and calls the blob "about 530 KB"; since M3 the display memory is in the state (`src/wof.h`, `wof_front_t.vram`), and the blob is 543,240 bytes. `src/core.c` lines 59 to 64 say the mirror marker "arrives with the flight model in M4 and has to join the state then"; it has joined (`marker_hellcat`, `marker_torpedo`). The chapter follows the code.
- **T7.** The task places T5 and T7 in `tests/test_state_m4.py`; `re/notes/porting-m4.md`'s table labels T7 the page tests (`tests/test_page.py`, `tests/test_firefox.py`). `tests/test_state_m4.py` holds T5 and the test that the page's core has no test entries. The chapter names tests by their names.
- **The arena test's name.** `test_thirty_mission_setups_do_not_grow_the_arena` counts to 31 missions; the note says thirty-one. The chapter says thirty-one.
- **The module ranges.** The task asks for a table of the modules with their address ranges from the files' openings; three openings name a range (`src/player.c`, `src/enemy.c`, `src/sound.c`), `src/ffp.c` names the glue's, and the blitter library's range is in `re/notes/drawing.md`. The table gives those six, the music player by its offsets, and says the rest follow their routines in order.
- **Links to re-point, for the controller.** Chapters 17 and 18 link "registered state" to chapter 5's section `calling-a-routine-without-its-program`; chapters 14, 17 and 19 say "coroutine" and link `../part-3/core.md`. With the entries added, those links could go to `../glossary.md#registered-state` and `../glossary.md#coroutine`, which would move both entries' "First met" lines to the lowest chapter linking them.
