Chapter 4
{ .chapter-kicker }

# Reading the executable

The code of the program on the disk is 77,644 bytes of [machine code](../glossary.md#machine-code) without a single name in it, and the port was written from it, routine by routine. By the end of this chapter you will know how those bytes were turned back into something people can read, and what that reading gives that the bytes do not. You will know how the routines got their names and why the names live in a file of their own, what the inventory of routines records, and what a control-flow skeleton is for. You will see compiled C and hand-written assembly side by side and learn why the port has to tell them apart. Last, you will see what could be recognised in the code and how, and why a reading counts only as a claim until the running original confirms it.

## The program as numbers

Chapter 3 left the program's code [hunk](../glossary.md#hunk) at `0x010000`: a row of bytes, and no [symbol](../glossary.md#symbol) to say where a routine begins or what a variable is for. A processor needs nothing more. A person does, and the port is written from the original's code, not from what the game seems to do ([`CLAUDE.md`](repo:CLAUDE.md#rules), "Rules"), so the first instrument of the project is a [**disassembler**](../glossary.md#disassembler): a tool that turns machine code back into [assembly language](../glossary.md#assembly-language), one instruction a line.

Decoding one instruction is mechanical. A [68000](../glossary.md#68000) instruction is one word of 16 bits or more, and the first word, the [**opcode**](../glossary.md#opcode), names the operation and how its operands are found, and so how many words follow. In this program every instruction is 2, 4, 6 or 8 bytes long. The project leaves this step to Capstone, a disassembly library.

The hard part is knowing where to start. The code hunk does not hold only code: the strings lie after the routines that use them, and tables sit between routines. Bytes decoded from the wrong place still give instructions, only nonsense ones, and ordinary text decodes as perfectly valid 68000 code. A disassembler that ran straight through the hunk would read every message as instructions.

So [`tools/disasm.py`](repo:tools/disasm.py) follows the program's [**control flow**](../glossary.md#control-flow): the order in which its instructions run, set by its branches, jumps, calls and returns. It starts where code certainly begins, at the program's first instruction, at every routine the [far-call table](../glossary.md#far-call-table) points to, and at every `link a5`, which opens each compiled routine (chapter 3). From each start it decodes on, follows a branch both ways and a call into the routine it calls, and ends a path at a return or an unconditional jump. A call such as `jsr -$7e1e(a4)` is followed through its slot of the far-call table; a `switch` of the compiled C through its table of offsets.

What no path reaches is a string where the code points to it, text where it is a run of at least twelve printable bytes that are mostly letters, and otherwise tried last, in a gap sweep: a gap counts as code only if it decodes cleanly up to a return or a jump and its first bytes are not nearly all printable. That last test is there because text decodes as code: without it, the inventory below would hold routines that do not exist. The sweep found 55 blocks of code that no path reaches, routines nothing calls or reaches only through an address computed at run time, and the listing marks each one. Of the hunk's 77,644 bytes, 73,792 are instructions, 3,725 strings and text and 88 the tables of four `switch` statements; 39 bytes stay unexplained.

## The listing

What the disassembler writes is the [**listing**](../glossary.md#listing), [`re/Wings.lst`](repo:re/Wings.lst): the whole program as assembly language, 32,434 lines, 21,332 of them instructions. It is what the port was read from. Each instruction stands at its address in the [fixed load layout](../glossary.md#fixed-load-layout), so that an address names the same place in the listing, the notes, the tests and the port's comments. Here is the start of the game's main routine, `main`, with the lines the listing puts above it:

```wingslst linenums="1"
--8<-- "generated/listings/asm/main_start.lst"
```

Line 1 is the book's, naming the range. Line 2 opens the routine: its name, its kind, here `[asm]` for written by hand, and its slot in the far-call table. Line 3 is the comment the project gave it, and line 4 lists the routines that call it; this one's caller has no name yet. Line 5 is a [**label**](../glossary.md#label): a name for an address that a branch or a call leads to, on a line of its own, so that the place a jump lands is plain to see; line 18 is one inside the routine, `loc_` and its address.

An instruction's line has four columns: the address, the instruction's bytes, the instruction, and after a semicolon what the tool knows of it. That last column is where the listing earns its keep:

- An operand relative to the [small-data base](../glossary.md#small-data-base), A4, gets the variable's name, `outside_mission` on line 11, or, for one nobody has named, `g_` and its address, as on line 13.
- A call through the far-call table gets an arrow and the routine its slot holds, line 7; without it, `-$7e1e(a4)` would say nothing about where the call goes.
- A call relative to the program counter gets its routine's name, `open_libraries` on line 8.
- A call into the operating system gets the [library](../glossary.md#library) and the routine, `intuition.CloseWorkBench` on line 10: the game closes the [Workbench](../glossary.md#workbench) as it starts.
- An address the loader corrects, a [relocation](../glossary.md#relocation), gets the name or the string it points to: on line 17, `main` stores the address of the demo file's name, `wofdemo`, in `demo_file_name` when the game was started with an argument (chapter 17).

The listing names only what the program reaches in those ways. The first instruction, line 6, sets a bit at `$bfe001.l`, a port of one of the [CIAs](../glossary.md#cia), and the tool leaves the address a number. That bit drives the power light and with it the Amiga's audio filter, which dulls the high notes; set, it switches both off. The first thing `main` does is let the game's sound through unfiltered.

The library calls are named in two steps. A program keeps a library's address, its [**library base**](../glossary.md#library-base), in a variable and loads it into the register A6 to call one of the library's routines at a fixed offset below it. [`re/libbases.txt`](repo:re/libbases.txt) says which five variables hold the bases of exec, intuition, graphics, dos and mathffp; the tool watches A6 being loaded from one, and looks the offset up in that library's list of routines under [`tools/fd/`](repo:tools/fd/), the first routine at 30 below the base, each further one six bytes on. Of the 137 calls into a library in the code, 130 are named so; seven keep only their offset, where A6 was loaded in a way the tool does not follow. These names matter beyond reading: every call into the system is a place where the port must stand in for the operating system, as chapter 2's table showed.

After the code, the listing shows the data hunk: the far-call table's 185 slots, each with its routine, then the variables by name with their starting values. The texts are summarised on purpose. A string the code points to appears in a comment, cut after 48 characters; each of the six long runs of text that nothing points to, 2,278 bytes in all, most of the story among them, is one line with its length. The listing is part of the repository that anyone can read, and it is not meant to be a second copy of the game's texts; the port reads them from the program when it is built, as chapter 3 told.

## Names

Every name in the listing was given by the project. They come from one hand-kept file, [`re/names.txt`](repo:re/names.txt): a line for each address, the address in hexadecimal, a name and, after a semicolon, a comment. It holds 798 names, 449 in the code and 349 for variables and tables in the data, and most carry a comment that says what the thing does or which note tells more. A routine without a name is `sub_` and its address, which still holds for 171 of them.

The names are kept apart from the listing for a reason. The listing is made by the tool and never edited by hand, so that it can be made again whenever the tool learns something or a name changes; a name typed into the listing would be gone at the next run. So a routine, once understood, gets its line in [`re/names.txt`](repo:re/names.txt), and a run of about two seconds puts the name into the listing and the inventory, and from there into every skeleton; the reports of the headless original read the same file. The test [`tests/test_generated.py`](repo:tests/test%5Fgenerated.py) makes the listing again from the committed names and compares it with the committed file byte for byte, so the listing a reader browses is always what the tool makes.

![Four boxes on the left, the program and three hand-kept files, feed tools/disasm.py, which writes the listing and the inventory; the status column runs back into the tool; a test below makes both again and compares them.](../figures/listing-made.svg)

/// caption
How the listing is made: the program and the hand-kept files go in, the listing and the inventory come out, and a test holds both to what the tool makes.
///

A name is a claim about what a thing is. The names are also the vocabulary the notes, the port's comments and the tests share: `record_at` is the same routine everywhere, and its port says `orig 0x01C982` beside its C.

## The inventory

A [**routine**](../glossary.md#routine) is a piece of the program that is called, does one job and returns to its caller. The same run of the disassembler writes the [**routine inventory**](../glossary.md#routine-inventory), [`re/functions.csv`](repo:re/functions.csv): a row for each of the 616 routines, with its address and name, whether it is C or assembly, its size in bytes, for C the size of its frame and where it reads its arguments, its far-call slot, how many routines call it and which routines it calls, which library routines it calls, how many variables it touches, the strings it uses, and its status in the port. It is the list the work was planned on, by kind and size, and the list by which the observation of the original hooks every routine.

The inventory counts as one routine everything from an entry point the disassembler found to the next one, so every byte of the code belongs to one routine. That is nearly always right. A routine that runs on into the next one's instructions is cut in two: `ship_at_offset` appears with 4 bytes, and the rest of it under the following address.

The status says where the port stands with each routine. It is the one column kept by hand; the tool carries it over at every run, and a routine new to the inventory starts as `todo`. A routine is [**verified**](../glossary.md#verified) when it is ported and held to the original under the [oracle](../glossary.md#oracle), which chapter 5 explains. The other values are `ported`; `partial`, ported as far as the recorded runs of the game reach it, the rest marked so that a run reaching it fails (chapter 8); `replace`, the port does the job its own way, as for the memory, the copper lists and the calls into the floating point; `drop`, not needed, as the crack's screen and the debug reporters; and `todo`, no status set. About a quarter of the routines are verified, a quarter ported, and a third have no status. Those are not all work left: 117 of them lie at the end of the code, in the C library and the system's glue, and 67 have no caller in the listing.

![Two panels of ten rows each, the code hunk from 0x010000 in rows of 8 KB. The kind panel is orange to 0x015D62, then mostly blue with orange islands, the blitter library and the end of the code orange; the status panel mixes the colours of verified and ported, with grey at the end.](../generated/figures/code-map.png)

/// caption
The code hunk along its addresses, from [`re/functions.csv`](repo:re/functions.csv): above by the kind of each routine, below by its status in the port.
///

## The skeleton of a routine

A long routine in the listing is a wall of moves and arithmetic, and what it does is easier to see in its shape: where it loops, where it branches away, what it calls, what it asks the system for. A [**control-flow skeleton**](../glossary.md#control-flow-skeleton) is that shape: the routine with only its labels, calls, branches, tests and returns. [`tools/skel.py`](repo:tools/skel.py) prints it from the listing, by name or address, and it is the first step of porting any routine, before it is read in full ([`SPEC.md`](repo:SPEC.md#74-working-method), section 7.4).

Here is the skeleton of `map_load`, a hand-written routine of 226 bytes: 22 lines of its 76.

```wingslst
--8<-- "generated/listings/skel/map_load.lst"
```

Read from the top, it clears the airfields and runs a short loop: the `dbra` counts a register down and branches back until it falls below zero, here adding up the missions of the ranks before the one played, to find the mission's map. It opens the map's file through dos, reads twice, the two numbers at the file's head that chapter 3 described, and asks for memory; if none is given, it branches away to the routine that ends the program. Then it reads the records, closes the file and hands the records to `map_scan`. The 54 lines the skeleton leaves out clear the mission's counts, find the file's name and work out the sizes, and they are read next, with the shape already known.

## Compiled C and assembly written by hand

The two kinds of code look different in the listing, and the port must know which is which. A compiled routine keeps to the compiler's [calling convention](../glossary.md#calling-convention): its arguments on the stack, its result in D0, its [int](../glossary.md#int-the-c-type) 16 bits wide, with the widths chapter 3 showed. A hand-written routine has a convention of its own, taken from its registers, and may leave a value in a register for the next one to read, which chapter 9 shows the port had to learn. So the oracle calls a compiled routine with arguments on the stack and a hand-written one with its registers set, and every hand-written routine is read in full and never guessed at.

Two routines show the difference: `colour_lerp`, compiled C, one step of a fade from one colour to another, and `text_width`, written by hand, the width of a text in the game's font.

//// html | div.listing-pair

/// html | div
```wingslst
--8<-- "generated/listings/asm/colour_lerp.lst"
```
///

/// html | div
```wingslst
--8<-- "generated/listings/asm/text_width.lst"
```
///

////

`colour_lerp` opens with `link.w a5, #$fffe`, a [stack frame](../glossary.md#stack-frame) with room for one variable at `-$2(a5)`, and reads its three arguments at `$8(a5)`, `$a(a5)` and `$c(a5)`. Its caller hands them over the compiler's way: it pushes three words with `move.w ..., -(a7)`, the last argument first, calls, then takes the six bytes off the stack again with `addq.w #$6, a7` and finds the result in D0. The first two colour components are computed with the 16-bit idioms, `muls.w`, `ext.l` and `divs.w`; the third's division goes through a helper near the end of the code, unnamed in the listing, that divides one 32-bit number by another: the compiler's own division of a long. The port keeps both widths. The routine ends with `unlk a5` and `rts`.

`text_width` has no frame. It saves fourteen registers, all but D0, with one `movem.l`, takes the text's address in A0 and its length less one in D0, and uses A5, the compiled code's frame pointer, for its own purpose: the address of the loaded font file. It loops with `dbra`, leaves the width in D0, restores the registers and returns. Its caller, `text_render`, also written by hand, takes one off the length itself before the call. That convention is written nowhere but in the routine and in the comment the project gave it.

The inventory tells the two kinds apart by one rule: a routine whose first instruction is `link a5` is C, any other is assembly. The rule holds because the compiler opens every function that way, and it counts 223 compiled routines and 393 hand-written ones, the 223 the specification names. The code map above shows where they lie. Every one of the 205 routines up to `0x015D62` is written by hand: the main loop, the drawing of the scene, the interrupt routines, the objects' movement. From there on the compiled routines stand among hand-written ones: 61 among the game's C, such as the sound effects engine, the dashboard and the keyboard's handler; the 25 of the blitter library; and 102 at the very end beside 36 compiled ones, the C library and the system's glue. In bytes, C has 42,436 and assembly 35,208.

## What could be recognised, and how

Four kinds of evidence recur behind the names and the notes.

- **A library call by its offset.** The tool names most of these by itself. Where it cannot, the same lists serve by hand: the game's nine routines of [fast floating point](../glossary.md#fast-floating-point) each push a number and jump to one dispatcher, and the number is the routine's offset in the mathffp library, −66 for an addition. Matched against the library's list, the numbers gave `ffp_add` and its eight neighbours.
- **A text by its use.** Where the code takes a string's address, the string names what holds it. The variable that `main` fills with `wofdemo` became `demo_file_name`; a routine that asks for four blocks of memory under the names `Ricochet`, `Splashes`, `Smoke` and `Balloons` named the pools of small objects it makes ([`re/notes/objects.md`](repo:re/notes/objects.md#the-inventory), "The inventory").
- **A table by its stride.** A routine that walks a table steps by the size of one record, so the step gives the record, and the table's size divided by it the count. The smoke's pool is `0x320` bytes and its walkers step `0x14`, so it holds 40 puffs of smoke; a run of the original wrote it with the same stride.
- **A routine by its callers and its data.** The header lists who calls a routine, and the comments which variables it touches and which library routines it uses. `text_width` is called by `text_render` alone and reads the font's first and last character. The only routine that writes the ricochet's pool has no caller in the listing, and the runs that watched the pools never saw that one filled.

## A reading is a claim

Everything above is reading, and a reading can be wrong. The notes therefore mark every statement as "read", from the listing alone, or "observed", with the run or the test that shows it. To observe, the project runs the original program whole: the [headless original](../glossary.md#headless-original) can watch any routine by name, every time it is entered with its registers and its arguments, and a test holds that watching changes nothing; chapter 6 tells how. That is how the notes know what each screen of the front end draws, and what the floating point is handed in the middle of a flight. A [pure routine](../glossary.md#pure-routine) is held to its port under the oracle, chapter 5.

A routine ported from reading alone is a claim too. The one that makes the play screen the one drawn again after a dialog was ported from reading and first run by a script that saves a game: 997 of that run's [passes](../glossary.md#pass) differed from the original's, in the rows below the [split line](../glossary.md#split-line) and in the ticker's, until it was fixed ([`re/notes/porting-m7.md`](repo:re/notes/porting-m7.md#the-port), "The port"). Chapter 9 tells of a reading of the stick's bits that the running original contradicted.

/// wrong
A note once said that the last four records of every map are left uninitialised on a real machine, because the map's loader asks for eight bytes more than the file holds; it rested on how the headless original's stand-in for the system's memory behaved. Reading the allocator the game itself calls showed `bset #$10,d0` at `0x020884`: bit 16 of the flags it hands the system is the one that asks for cleared memory, so the four records are zero on the machine as in the harness ([`re/notes/map.md`](repo:re/notes/map.md#the-file), "The file"). The port's memory hands out zeroed blocks since, and a test holds it. A claim about the original rests on the original's code, not on the instrument's stand-in for it.
///

/// dev
[`tools/disasm.py`](repo:tools/disasm.py) writes into [`re/`](repo:re/), or with `--out DIR` elsewhere, and always takes the status column from [`re/functions.csv`](repo:re/functions.csv); read that file with a CSV reader, because its strings column holds commas. [`tools/m68kdis.py`](repo:tools/m68kdis.py) `EXE START LEN` decodes an address range straight through, without the control flow; [`tools/skel.py`](repo:tools/skel.py) `ADDR --all` prints a whole routine. The music player has its own listing, [`re/songplay.lst`](repo:re/songplay.lst), made by [`tools/disasm_player.py`](repo:tools/disasm%5Fplayer.py).
///

## What comes next

Chapter 5 takes one routine out of the listing and runs it on an emulated 68000 beside its port, on thousands of inputs: the oracle, and what verified means.

## Further reading

The files named here are in the repository, [`github.com/sy2002/wof-wasm`](repo:).

- [`SPEC.md`](repo:SPEC.md), section 3.2, ["Executable"](repo:SPEC.md#32-executable); 4, ["Tools"](repo:SPEC.md#4-tools); 7.4, ["Working method"](repo:SPEC.md#74-working-method).
- [`tools/disasm.py`](repo:tools/disasm.py), [`tools/skel.py`](repo:tools/skel.py), [`re/names.txt`](repo:re/names.txt), [`re/libbases.txt`](repo:re/libbases.txt), [`re/functions.csv`](repo:re/functions.csv) and [`tests/test_generated.py`](repo:tests/test%5Fgenerated.py).
- [`re/notes/headless.md`](repo:re/notes/headless.md), ["Observers"](repo:re/notes/headless.md#observers) and ["Write summary, read hook"](repo:re/notes/headless.md#write-summary-read-hook); [`re/notes/objects.md`](repo:re/notes/objects.md#the-inventory), "The inventory".

Outside the repository: Motorola's [*M68000 Family Programmer's Reference Manual*](https://archive.org/details/m68000familyprog0000unse), for the instructions and their encoding; the [*Amiga Hardware Reference Manual*](https://archive.org/details/commodore-amiga-tech-ref-series-amiga-hardware-reference-manual-3rd-edition), for the CIAs.
