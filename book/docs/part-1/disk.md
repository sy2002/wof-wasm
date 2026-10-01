Chapter 3
{ .chapter-kicker }

# The disk

Wings of Fury came on one floppy disk, from which an Amiga 500 or 2000 starts the game (the manual, page 2), and everything the port knows about the game comes from it. By the end of this chapter you will know what is on the disk and how little of it the port had to decode; how the program is built from parts called hunks, and why the port loads them at fixed addresses, so that every address in this book names one place; how the compiler reaches the variables through the register A4, which explains the operand `-$46ec(a4)` of chapter 2; what its 16-bit integers demand of the port; and why every table and text the port needs is read out of the program, never typed in again.

## An image of the floppy

The repository keeps the disk as an **ADF**, an Amiga Disk File: a copy of an Amiga floppy, block by block, in one file. A double-density floppy has 80 cylinders of two tracks, each track 11 blocks of 512 bytes: 1,760 blocks, 901,120 bytes, the 880 KB an Amiga owner knows. The image, `original/wof.adf`, is exactly that size. Beside it lie the disk's files, extracted byte for byte, under `original/disk/`. Nothing in the project ever writes to either.

The disk uses AmigaDOS's original file system, which keeps the top directory in block 880, the middle of the disk, and spreads a directory's entries over 72 chains by a hash of their names. The port and its tools read the extracted files; the image itself is read for one thing only, the order in which a directory lists its entries, which the [headless original](../glossary.md#headless-original) hands the game as the machine would; chapter 20 tells why it matters.

At start-up the disk's script, `s/startup-sequence`, runs two small commands from the disk's top level, `led` and `cd`, the second to enter the directory `Wings_of_Fury`, and then the program `Wings`. Beside them lies a second copy of the program, `Wings2`, byte for byte the same.

## What is on the disk

The game's directory, `Wings_of_Fury`, holds 65 files, 664,981 bytes in all.

![Eleven rows, one for each kind of file, each with its count, its bytes, a bar to scale and the formats its files' first bytes show; the shape containers' bar is the longest, the program's and the files not the game's are grey.](../generated/figures/disk-files.png)

/// caption
The game's directory on the disk: each kind of file with its count and bytes, each file a segment of its row's bar, gold where it goes into the port's page.
///

- **The program**, `Wings`, 94,292 bytes, the subject of the rest of this chapter.
- **The music**: `songplay`, 5,148 bytes, the music player, a small program of its own; and `wofsongs`, 41,328 bytes, the songs, the voices and their [sound samples](../glossary.md#sound-sample) (chapter 18).
- **Twelve shape containers**, the files ending in `.shp`, with 1,049 shapes, from 8 in `selectrank.shp` to 223 in each of the dashboard's two (chapter 12).
- **Nine pictures**: the title sequence's three, the rank selection's, the high-score screen's two, the dashboard's by day and by night, and `Rank.iff`, which the game never opens.
- **Six palettes**: three bare tables of 32 colours and three pictures kept for their colours, two of which the game never opens. The sky's palette, the sea's, the dashboard's picture and its shapes each come in a day and a night version (chapter 11).
- **Fifteen maps**, `maps/a.map` to `maps/o.map`, one for each mission, 1,910 to 7,138 bytes: after two numbers of four bytes, a row of records of two bytes, one for every eight pixels of the world from left to right, each saying what stands there and how high (chapter 13).
- **Eight sound effects** in `sounds/`: signed bytes with no header, which Paula plays as they are; `sounds/boom` is chapter 2's burst.
- **The game's font**, `newarmyfont`, 2,476 bytes: its height, 12, its first and last character, a width for each character, then the glyphs. The dialogs' font, [topaz 8](../glossary.md#topaz-8), comes from the ROM.
- **The high scores**, `highscore`, 360 bytes: ten entries of 36 bytes, each a score, the rank reached and a name.
- **A saved game**, `wof.mission 3`, 6,866 bytes, saved on a real Amiga in the first rank's third mission, with 14,225 points.

A saved game is the game's memory as it stood, with nothing between the pieces: 2,122 bytes of its variables, then the map's records and the tables of the targets. So its size follows from the map alone, from 4,258 bytes on map a to 11,516 on map m. Four of its fields are addresses in the memory of the machine that saved it, such as `0x0005FB4A` for the player's shape in this one, which mean nothing on another machine; the port works them out from the data beside them. Chapter 17 takes the saved game apart.

One file the game asks for is missing: `wofdemo`, the [attract demo](../glossary.md#attract-demo). Left alone at the rank selection, the game tries to load it and, without it, starts a mission. Nine files are not the game's at all: `UFXintro`, `wingt` and seven `.info` files.

The port packs 55 of the files into its page, all but the program and those nine: 540,960 bytes, each file in its original format. The program stays out because the port is its rewrite: its code became the [core](../glossary.md#core), and its data reaches the core as the last section tells. A file keeps its name relative to the game's directory, so that the ported loaders ask for the original's own names, found whatever their case, as AmigaDOS finds them: the game asks for `shapes/Torpedo.shp`, and the disk has `torpedo.shp`.

/// wrong
The port's file system first held files of at most 8,192 bytes, a limit sized from a saved game of 4,258 bytes on map a. When the saved game was ported, its size was measured on all fifteen maps (`re/notes/campaign.md`, "The sizes"): it reaches 11,516 bytes on map m, and a save on seven of the later maps would not have been kept (`re/notes/porting-m7.md`). The limit is now the largest save the port's tables allow, 12,412 bytes. A size is measured over every case before it is trusted.
///

## The little there was to decode

Three of the disk's formats are worth a closer look.

The game has a packed format of its own, **Rpck**, named after the four letters a packed file begins with. Then come the unpacked size, in four bytes, and a stream of control bytes. A control byte read as a negative number, −n, says: copy the next n bytes. Any other, n, says: repeat the next byte n + 1 times. Ten files are packed, eight shape containers and two palettes, and the game's loader unpacks any file that begins with those letters.

The figure shows the rank selection's shapes, 1,656 bytes on the disk and 5,630 unpacked. The first control byte, `0xDA`, is −38: the 38 bytes after it are copied, the start of a shape container. Then `0x05` writes a zero six times, `0xD2` copies 46 bytes, and `0x17` writes `0xFF` 24 times, the top row of the first shape, 192 pixels set.

![Two hexadecimal dumps: above, the first 98 bytes of the packed file, four control bytes in gold and explained beside their rows; below, the first 114 bytes they unpack to, a shape container's fields named beside them.](../generated/figures/packed-selectrank.png)

/// caption
The game's packed format at work: the first bytes of a packed file, and the shape container they unpack to.
///

Two files unpack to one byte more than they declare. The original writes that byte past the end of its buffer; the port stops at the declared size, and nothing reads it.

A **shape container** is a file of many shapes, the format that begins with `PPkc`: the number of shapes, a name of four characters for each, where each record begins, then the records. A record is a header of 20 bytes, with the shape's width and height, its hotspot (the point that lands on the position the shape is drawn at) and the [bitplanes](../glossary.md#bitplane) its stored planes go into, followed by the planes. The game asks for its shapes by name, through lists of names in its data, and looks them up once, when it loads a container.

The pictures are **IFF ILBM**, the Amiga's standard format for pictures: a file of chunks, each a name of four letters, its length and its contents, which give a picture's size, its colours (`CMAP`) and its bitplanes, each row packed (`BODY`). Three palette files are a bare `CMAP` chunk. The game reads its pictures with a reader of its own, which also knows a private chunk, `CMP2`, and the port carries that reader over rather than replacing it.

The sound effects and the maps need nothing decoded, and the font has a small header of its own. For the core the port wrote no decoders: it ported the original's loaders, routine by routine. The decoders in Python, `tools/rpck.py`, `tools/ppkc.py` and `tools/map_decode.py`, serve the tools, the tests and this book's figures.

/// know
Every loader and decoder ran twice on the same input, as the original's 68000 code under the [oracle](../glossary.md#oracle) and as the port's C, and the results had to be equal byte for byte: all ten packed files and 40 random streams for the unpacker, all 55 files through the loader, all 1,049 shapes into pixels, all twelve IFF picture files and all six palette files. The oracle's own self-test unpacks the ten packed files with the original's routine and compares them with `tools/rpck.py`. Chapter 5 tells how the oracle works.
///

## The executable, a hunk file

An Amiga program is a **hunk file**, the format of AmigaDOS for programs: a row of blocks, each opening with a number of four bytes that says what it is. A header names the hunks and their sizes; then come, hunk by hunk, its contents, its relocations and an end mark. A **hunk** is a part of a program that is loaded into memory as a whole: a code hunk holds instructions, a data hunk variables with their starting values, and a **BSS** hunk is memory that starts at zero, given in the file by its size alone.

`Wings` has one of each. Its code hunk is 77,644 bytes: the instructions, and the texts, each after the routine that uses it. Its data hunk takes 20,464 bytes in memory, of which the file stores the first 15,456; the rest starts at zero. Its BSS hunk is 4 bytes.

The file does not say where its hunks go. Where the program holds an address, the file holds an offset from the start of a hunk and lists the place in a **relocation**: an entry naming a place in a hunk that holds an address, which the loader corrects by where the hunk landed. The code hunk has 22 relocations, the data hunk 247, 185 of them in a table of jumps that comes up below.

AmigaDOS loads a program with **LoadSeg**, the routine of its [library](../glossary.md#library) that reads a hunk file, puts each hunk wherever it finds free memory of the kind the file asks for, and applies the relocations. `wofsongs` asks for [chip memory](../glossary.md#chip-memory), where Paula can reach its sound samples. The game loads its music with LoadSeg, and the system loaded `Wings` the same way.

`Wings` carries no symbols: no name of a routine or variable survives in it, and every name in this book's listings was given by the project, as chapter 4 tells. The music player kept its symbols, twenty names in its code.

![On the left the file's blocks: a header, the code with 22 relocations, the data with 247, the BSS. On the right memory to scale: the code from 0x010000, the data from 0x023000, the BSS at 0x028000, A4 at 0x02AFFE in gold and the span it reaches.](../figures/hunks.svg)

/// caption
The program on the disk, hunk by hunk, and where the project's tools load each hunk, with A4 and the span its offsets reach.
///

## One layout for every address

On a real Amiga, LoadSeg chooses the addresses, and they differ from one machine, and one start, to the next, so that an address written into a note would mean nothing the next day. So the project uses one **fixed load layout**: the one set of addresses at which all its tools load the program, the code at `0x010000`, the data at `0x023000` and the BSS at `0x028000`. It is the layout of `tools/hunk.py`: the first hunk at `0x010000`, each next one at the next 4 KB boundary.

Every tool loads the program through `tools/hunk.py`: the disassembler that writes the listing, the oracle, the headless original and the build's extractor of tables. Every ported routine names its original's address in a comment. So an address names one place everywhere: `0x01C982` is the routine `record_at` in the listing, in the notes, under the oracle, in its port's comment, and below.

## Manx Aztec C

The game's C was compiled with **Manx Aztec C**, a C compiler for the Amiga of its day. The code up to `0x015D62` is almost all [assembly language](../glossary.md#assembly-language) written by hand: the main loop, the drawing, the interrupt routines, the objects' movement. Then come the routines compiled from C, the C library's among them, with the blitter's routines, written by hand, in their midst. Of 616 routines, 223 are C. How the two kinds are told apart is chapter 4's subject; here they matter for what they share.

### A4

The compiler reaches the program's variables through one [register](../glossary.md#register), the **small-data base** A4: the register holding an address inside the data, from which every variable is reached by an offset of 16 bits. The program's first instruction jumps to the C library's start-up code, which first calls a routine of two instructions that loads A4. The file holds the number `0x7FFE` there, with a relocation into the data hunk, so A4 ends up 32,766 bytes into the data wherever the data was put: in the fixed layout, `0x02AFFE`.

An offset of 16 bits reaches from 32,768 bytes below the register to 32,767 above it. From `0x02AFFE` that is `0x022FFE` to `0x032FFD`: the whole data hunk from its first byte, and the BSS. An instruction names a variable in two bytes, where a full address takes four, and needs no relocation: when the data moves, A4 moves with it.

Now chapter 2's operand reads plainly. `-$46ec(a4)` is the variable `0x46EC` bytes below A4: `0x02AFFE` less `0x46EC` is `0x026912`, `rand_seed_const`. That chapter's `rand_beam` was written by hand, yet reaches its variables the same way: the hand-written assembly and the compiled C share one set of variables through A4. In the listing, 4,198 instructions have an operand relative to A4.

Of those, 659 are calls. A call written `jsr -$7e1e(a4)`, as in the game's main routine, jumps into the **far-call table**: 185 jump instructions at the start of the data hunk, each holding the full address of a routine. The listing names the routine behind each slot.

### The frame on A5

The compiler also fixes the **calling convention**: the rules by which a caller hands a routine its arguments and gets the result back. The caller pushes the arguments onto the stack, the last first, 2 bytes for an int and 4 for a long or a pointer, and calls; the result comes back in the register D0. Each of the 223 C routines begins with `link a5`, which builds its **stack frame**: the routine's own stretch of the stack, from its arguments down to its own variables, with A5 pointing into its middle. The call has pushed the return address; `link` pushes the caller's A5, points A5 at the stack, and moves the stack down to make room for the routine's variables. So the first argument is always at `8(a5)`.

![On the left the stack: the argument at 8(a5), the return address at 4(a5), the caller's A5 at 0(a5) where A5 points, the local at -4(a5) where A7 points. On the right A4 at 0x02AFFE and, 0x69D6 bytes below it, two variables of the map.](../figures/frame.svg)

/// caption
What `record_at` reaches while it runs: its frame on the stack through A5, and two variables through A4.
///

`record_at` shows both registers at work. Given a position in the world, its x, it returns the map record under it. In the listing, look at `$8(a5)`, the argument, read as a word because an int is 16 bits; at `ext.l` and `divs.w #$8`, x divided by 8; at `asl.w` and `ext.l`, which double the result as a 16-bit number and only then widen it to 32 bits; at `-$69d6(a4)`, the variable `map_records`, the address of the map's first record; at the routine's own variable at `-$4(a5)`; and at D0, which carries the result back.

//// html | div.listing-pair

/// html | div
```wingslst
--8<-- "generated/listings/asm/record_at.lst"
```
///

/// html | div
```c
--8<-- "generated/listings/c/wof_record_at.c"
```
///

////

The port names the original's address in its first comment and keeps each width the listing shows, with casts. It returns an offset into the map's records where the original returns an address: in the port a pointer into the game's data becomes an offset or an index, so that nothing in its state depends on where the browser put it. The oracle holds the two to each other on five maps, at every x where a record begins, near both ends and at 500 random places.

An operation on a floating-point number becomes a call of the C library, which passes it on to the ROM's [fast floating point](../glossary.md#fast-floating-point) (chapter 14).

## The 16-bit int

In Manx Aztec C, as the game was built, an **int**, C's ordinary type for whole numbers, is 16 bits wide, and a long and a pointer 32; the compilers that build the port make an int 32 bits. An int holds the numbers from −32,768 to 32,767, and one past the largest is the smallest.

The game's arithmetic lives in that width. An enemy fighter times a turn by its distance from the player, times 100, divided by its speed. The 68000's `muls.w` multiplies two 16-bit numbers into 32 bits; the compiled code then keeps only the low 16 bits of the product, as an int, before `divs.w` divides it. At a distance of 300 that changes nothing: 30,000 fits. From 328 on the product would not fit, 32,800 would become −32,736, and a port that kept all 32 bits would time the turn differently. The port does what the original does, bit for bit.

The specification turns this into rules for every routine (`SPEC.md`, section 7.1):

- No value of the game is a plain C int in the port; every width is named: `int16_t`, `uint16_t`, `int32_t` and their kin.
- Every change of width the listing shows happens in the port too: a sign extension, a product cut to 16 bits or kept at 32, a division that rounds toward zero and keeps a 16-bit quotient.
- Whether a comparison is signed follows the branch instruction that reads it.
- Wrap-around is behaviour. A value that runs past its largest number wraps in the original, and the port wraps it too, with an explicit cast, because in today's C a signed overflow is undefined, and a compiler may assume it never happens.
- Floating point never goes through C's `float` or `double`, which round differently.

One more rule concerns the upper half of a register a routine leaves holding 32 bits; the port once took it to be zero, and chapter 9 tells what caught that. Chapter 22 returns to the rules as a whole.

## Read from the executable, never retyped

The port needs the game's numbers and words: the names of its shapes and files, its palettes, the story's text, the periods of its sounds. The project's rule is that hand-written sources hold code only: every table, text and tuning value comes out of the program when the port is built.

The manifest `re/tables.toml` lists them, each entry with a name, a kind (a list of shape names, a string, a run of numbers, a block of bytes), an address in the fixed layout and a count. At every build, `tools/extract_tables.py` reads the bytes at those addresses and writes them out as C, which is never committed. On the way it converts the byte order: the 68000 is **big-endian**, storing the most significant byte of a number first, as every file the project reads does, and the tables come out as ordinary C.

The manifest has 122 entries: 113 from `Wings`, 7 from the music player and 2 from the ROM, the system font and the key table. They hold the lists of shape names, the file names, the front end's palettes, the rank names, the story, the dialogs' words, the mission's tables from the maps of each rank to the ships' guns, the sound effects' periods and volumes, and the music player's notes. One entry, `data_image`, is the stored part of the data hunk whole, 15,456 bytes, so that every variable the port keeps there starts with the original's own value. The texts come from the code hunk; the story runs from `0x017494` to `0x017CFB`.

Some values are in no table at all. Chapter 2's burst plays at period 500, the operand of an instruction in the routine that sets up the sound effects' slots, here slot 4:

```wingslst
--8<-- "generated/listings/asm/sound_slots_init_boom.lst"
```

The first two lines hand the slot the burst's sound sample and its length. The third writes `$1f4`, which is 500, as its period; the next two a volume of 64 (`$40`) and a count of one: the burst plays once. The manifest's entry `slot_periods` reads that word at `0x01200C`, and the same word in each of the seven slots' setups, `0x22` bytes apart.

The rule buys a port that cannot drift from the data. A number typed in again could be typed wrong, and nothing would say so; a number read from the program is the original's by construction, and an address outside the program stops the build. It also keeps the game out of the port's sources: the code is free software, the game's data is not, and the tables made from it are never committed.

/// dev
The fixed layout: code `0x010000` to `0x022F4C`; data `0x023000` to `0x027FF0`, its stored part to `0x026C60`, the far-call table `0x023000` to `0x023456`; BSS `0x028000`; A4 `0x02AFFE`. `tools/hunk.py FILE` prints a hunk file's hunks with their relocations and symbols, `tools/rpck.py FILE` a file's packed and unpacked sizes. The 55 files go into the page as one block (`tools/build.py`, `pack_fs()`): `WOFS`, a version, the count and the directory's offset, then 40 bytes for each file, its name in 32, its offset and its length, big-endian.
///

## What comes next

Chapter 4 opens the listing: how a disassembler turned the program's machine code back into this chapter's assembly language, how the routines got their names, how a skeleton of a routine's branches makes a long one readable, and how compiled C looks beside assembly written by hand.

## Further reading

The files named here are in the repository, `github.com/sy2002/wof-wasm`.

- `SPEC.md`, section 3.1, "Disk"; 3.2, "Executable"; 3.5, "File formats"; 5, "Build"; 7.1, "Arithmetic".
- `re/notes/porting-m1.md`, "The routines" and "How the tests establish it".
- `re/notes/shapes.md`, "Container and lookup"; `re/notes/map.md`, "The file" and "The record".
- `re/notes/music.md`, "The two files"; `re/notes/campaign.md`, "The saved game".
- `tools/hunk.py`, `tools/extract_tables.py` and `re/tables.toml`.

Outside the repository: *The AmigaDOS Manual*, for the hunk format; Laurent Clévy's *ADF format FAQ*, for the disk; Motorola's *M68000 Family Programmer's Reference Manual*, for `link` and the offsets from A4.
