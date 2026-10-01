# Fact sheet: chapter 3, The disk

Every claim the chapter makes, one line each, with its source, in the order of the chapter. A claim without a source goes to the list at the end and stays out of the draft. A general fact about the Amiga, its disk format, its program format or the 68000 that the repository does not state is sourced in a reference work outside the repository, named with its chapter or section, and marked **(reference)**, so that the fact-check can weigh it; a fact about this game is always sourced in the repository. These reference works are cited:

- *The .ADF (Amiga Disk File) format FAQ*, Laurent Clévy, version 1.11 (2005), cited as ADF FAQ with its sections "Amiga floppy disk geometry" and "The logical organisation of an Amiga volume" (the root block).
- *The AmigaDOS Manual*, Commodore-Amiga, third edition (Bantam, 1991), cited as ADM with its chapter "Amiga Binary File Structure" (the hunk format: the block types, the hunk header with its sizes and memory flags, the relocation blocks).
- *Amiga ROM Kernel Reference Manual: Includes and Autodocs*, Commodore-Amiga, third edition (Addison-Wesley, 1991), cited as RKM Autodocs with the entry `dos.library/LoadSeg`.
- *M68000 Family Programmer's Reference Manual*, Motorola (M68000PM/AD), cited as PRM with its sections 1 "Introduction" (data formats, big-endian memory), 2 "Addressing Capabilities" (address register indirect with displacement) and 4 "Integer Instructions" (`LINK`, `UNLK`, `JSR`).
- *EA IFF 85: Standard for Interchange Format Files*, Electronic Arts (1985), cited as IFF 85 with its section on chunks, together with Electronic Arts' *ILBM: IFF Interleaved Bitmap* (1986) for the meaning of `CMAP` and `BODY` and the row compression ByteRun1.
- For the width of `int` in the port's compilers: the WebAssembly tool conventions' *Basic C ABI* (`BasicCABI.md`, the data types), cited as wasm C ABI, and Apple's *64-Bit Transition Guide* (the LP64 data model) for the native build.

## Opening

1. The game came on one floppy disk, from which an Amiga 500 or 2000 starts it. Source: `original/manual.txt`, page 2 (cited, not quoted).
2. The chapter takes the disk and its files, the executable's hunks, Manx Aztec C with its 16-bit int, the data reached through A4, and why the tables and texts are extracted at build time; it hands the listing, the names, the skeleton and compiled C against hand-written assembly to chapter 4. Source: `book/BOOK.md` 3, chapters 3 and 4.

## The disk and its image

3. The repository keeps the disk as an image, `original/wof.adf`, read-only ground truth, and its files extracted verbatim with xdftool under `original/disk/`. Source: `SPEC.md` 2; `CLAUDE.md`, Rules (`original/` is read-only).
4. An ADF is a copy of an Amiga floppy block by block: a double-density disk has 80 cylinders of two tracks of 11 blocks of 512 bytes, 1,760 blocks, 901,120 bytes, 880 KB. Source: ADF FAQ, "Amiga floppy disk geometry" **(reference)**; `stat -f %z original/wof.adf` gives 901,120, and `python -c "print(80*2*11*512, 901120//512)"` gives 901120 1760.
5. The disk's file system is AmigaDOS's original one, OFS. Source: `SPEC.md` 3.1.
6. The root directory's block sits in the middle of a double-density disk, block 880, and a directory keeps its entries in 72 chains by a hash of the name. Source: `tools/headless_os.py` (`ROOT_BLOCK = 880`, "of a double-density disk"; `HASH_SIZE`, 72 chains); `re/notes/frontend.md`, "The order of the file list"; ADF FAQ, "The logical organisation of an Amiga volume" **(reference)**.
7. The port, the build and the tools read the extracted files; the image itself is read for one thing, the order in which a directory lists its entries, which the headless original takes from it; chapter 20 has the order. Source: `SPEC.md` 5, step 2 (the blob from the files of 3.1); `re/notes/frontend.md`, "The order of the file list" (nothing taken from `wof.adf` at build time; the harness serves the image's order); `re/notes/headless.md`, "Directories"; `book/BOOK.md` 3, chapter 20 ("the directory order").
8. At start-up the disk's script `s/startup-sequence` runs two small commands from the disk's top level, `led` and `cd`, the second to enter `Wings_of_Fury`, and then `Wings`; beside them lies a second copy of the program, `Wings2`, byte for byte `Wings`. Why the copy and the commands are there stays unsourced. Source: `SPEC.md` 3.1 (changes into `Wings_of_Fury` and runs `Wings`); the script itself, `original/disk/s/startup-sequence` (its three command lines, not quoted); `ls original/disk` (`cd` and `led` are hunk files, first bytes `000003f3`); `cmp original/disk/Wings2 original/disk/Wings_of_Fury/Wings` (equal).

## What is on the disk

9. The game's directory, `Wings_of_Fury`, holds 65 files, 664,981 bytes. Source: `find original/disk/Wings_of_Fury -type f ! -name .DS_Store` and `stat` (`.DS_Store` is the Finder's, git-ignored, not on the disk: `.gitignore`).
10. The figure `disk-files`. Source: the figure, described under "Figures".
11. `Wings`, the executable, 94,292 bytes, not packed. Source: `SPEC.md` 3.1; `stat`.
12. The music is two files of its own: `songplay`, 5,148 bytes, the music player, a small program; `wofsongs`, 41,328 bytes, the songs, the voices and their sound samples; chapter 18 has the music. Source: `SPEC.md` 3.1 and 3.5; `re/notes/music.md`, "The two files"; `stat`; `book/BOOK.md` 3, chapter 18.
13. Both are hunk files that the game loads with `LoadSeg` (the prose says so under the hunk file). Source: `re/notes/music.md`, "The two files" and "The game's calls"; `SPEC.md` 3.4, the `LoadSeg` row.
14. Twelve shape containers, `shapes/*.shp`, 240,092 bytes, hold 1,049 shapes, from 8 in `selectrank.shp` to 223 in `dash.shp` and in `nightdash.shp`; chapter 12 has the shapes. Source: `ls original/disk/Wings_of_Fury/shapes/*.shp | wc -l`; `stat`; `tools/ppkc.py` `parse()` per file; `re/notes/porting-m1.md`, Summary (1,049); `book/BOOK.md` 3, chapter 12.
15. Nine IFF ILBM pictures: the title sequence's three (`broderbund`, `wingstitle`, `creditscreen`), the rank selection's (`selectrank`), the high-score screens' two (`hiscoreslab`, `hiscore.iff`), the dashboard's by day and by night (`iff-dash`, `nightdash`), and `Rank.iff`, which the game never opens; 122,484 bytes. Source: `SPEC.md` 3.1 and 5, step 2 (`Rank.iff` is never opened, the briefing draws the shape `rank`); `re/notes/frontend.md`, "Screen by screen" (the loads of each screen); `re/notes/display.md`, "Day and night"; the first bytes of each file (`FORM`, then `ILBM`).
16. Six palette files, 1,428 bytes: three are a bare IFF colour chunk (`wingspalette`, `night.p`, `nightocean.p`), three whole IFF pictures used for their colours (`ocean.palette` and `palette` packed, `ocean.p` not); the game never opens `palette` or `ocean.p`, and nothing cycles colours. Source: `SPEC.md` 3.5, "Palettes"; the first bytes of each file (`CMAP`, `Rpck`, `FORM`).
17. Day and night choose between pairs of these files: `wingspalette` or `night.p`, `ocean.palette` or `nightocean.p`, `iff-dash` or `nightdash`, `dash.shp` or `nightdash.shp`; chapter 11. Source: `re/notes/display.md`, "Day and night"; `book/BOOK.md` 3, chapter 11.
18. Fifteen maps, `maps/a.map` to `maps/o.map`, one per mission, 1,910 to 7,138 bytes, 68,946 in all: two longs, then one record of two bytes for every eight pixels of the world from left to right; chapter 13 has the world. Source: `SPEC.md` 3.5, "Maps"; `re/notes/map.md`, "The file" (the table of sizes) and "The record"; `stat`; `book/BOOK.md` 3, chapter 13.
19. Eight sound effects under `sounds/`, signed 8-bit bytes without a header, 1,886 to 13,919 bytes, 51,832 in all; `sounds/boom` is chapter 2's burst. Source: `SPEC.md` 3.5, "Sounds"; `re/notes/sound.md`, "The samples"; `stat`; chapter 2's fact sheet, claim 87.
20. The game's own font, `newarmyfont`, 2,476 bytes: its height, 12, its first and last character, `0x20` and `0x7E`, a width for each character, the glyphs from byte 100; the dialogs' font, topaz 8, is not on the disk and comes from the ROM. Source: `SPEC.md` 3.5, "Font"; `re/notes/drawing.md`, the `font_load` row; `re/notes/system-font.md`, opening.
21. `highscore`, 360 bytes: ten entries of 36 bytes, best first, each a score, the rank the player reached and a name. Source: `re/notes/highscore.md`, "The file".
22. `wof.mission 3`, 6,866 bytes, is a game saved on a real Amiga in the first rank's third mission, with 14,225 points. Source: `SPEC.md` 3.1; `re/notes/campaign.md`, "The sizes".
23. A saved game is the game's memory as it stands, with nothing between the pieces: 2,122 bytes of its variables, then the map's records and the tables of the targets; so its size follows from the map alone, from 4,258 bytes on map a to 11,516 on map m; chapter 17 has the campaign. Source: `SPEC.md` 3.5, "Saved games"; `re/notes/campaign.md`, "The layout" and "The sizes" (observed at step S of all fifteen maps); `book/BOOK.md` 3, chapter 17 ("the saved game's bytes").
24. Four of its fields are addresses in the memory of the machine that saved it; the disk's file holds `0x0005FB4A` for the player's shape; the port derives all four from the data beside them. Source: `SPEC.md` 3.5, "Saved games"; `re/notes/campaign.md`, "The sizes" and "The loader".
25. Not on the disk: `wofdemo`, the attract demo's file; left alone at the rank selection, the game asks for it and, without it, starts a mission. Source: `SPEC.md` 3.3 (`wofdemo`, "which this disk does not carry"); `re/notes/demo.md`, "Playback and the attract mode", step 1 (observed on this disk); `book/BOOK.md` 3, chapter 17.
26. Not the game's: `UFXintro`, 27,208 bytes, `wingt`, 176 bytes, and seven `.info` files; nine files, 29,729 bytes. Source: `SPEC.md` 3.1 ("not part of the game"); `find` and `stat`.
27. The port packs 55 files into the page, everything in the game's directory but the executable, `UFXintro`, `wingt`, the `.info` files and the dotfiles: 540,960 bytes, each in its original format. Source: `SPEC.md` 5, step 2; `tools/build.py`, `game_files()` and `SKIP_NAMES`; the sizes summed over `game_files()` with `os.path.getsize`.
28. The names are paths relative to the game's directory, the original's current directory, so that the ported loaders ask for the original's own names; a name is found whatever its case, as AmigaDOS finds it: the game asks for `shapes/Torpedo.shp`, the disk has `torpedo.shp`. Source: `SPEC.md` 5, step 2; `re/notes/porting-m1.md`, "Decisions the port made".
29. The executable stays out: its code is what the port rewrote, and its data reaches the port as the tables of the last section. Source: `SPEC.md` 5, steps 1 and 2.
30. (What went wrong) The port's file system first kept a file of at most 8,192 bytes, sized from a saved game of 4,258 bytes on map a; when the saved game was worked out in full, its size measured on all fifteen maps ran to 11,516 bytes, and a save on maps h, i and k to o would not have been kept; the limit is now the largest save the port's tables allow, 12,412 bytes. Source: commit `448069f` (`src/fs.c`: `FS_FILE_MAX 8192u`, commented "a saved game is 4,258 bytes on this disk", becomes `WOF_SAVE_MAX`; `src/wof.h`, `WOF_SAVE_MAX`); `re/notes/porting-m7.md`, part 1 ("where it was 8,192 and a save on maps h, i and k to o would not have been kept"); `re/notes/campaign.md`, "The sizes" (h 8,906, i 9,206, k 8,852, l 8,402, m 11,516, n 9,752, o 11,118, the seven above 8,192). The sidebar ends with its lesson: a size is measured over every case before it is trusted (the controller's wording for this sidebar, after chapter 1's).

## The little there was to decode

31. The game's own packed format, `Rpck`: the four letters, the unpacked size as a long, then a stream in which a control byte read as signed says either "copy the next n bytes" (negative, n its magnitude, `0x80` meaning 128) or "repeat the next byte n + 1 times" (zero or positive). Source: `SPEC.md` 3.5, "`Rpck` compression wrapper"; `tools/rpck.py`, `unrle()`.
32. Ten files are packed: eight of the twelve shape containers and two palettes; the loader `load_file` unpacks any file that begins with `Rpck`, so any file may be packed or not. Source: `SPEC.md` 3.5; the first four bytes of every file of `shapes/` (ten `Rpck`); `SPEC.md` 4, "The oracle" ("all ten packed files").
33. The figure `packed-selectrank`: `shapes/selectrank.shp`, 1,656 bytes on the disk, 5,630 unpacked; `0xDA`, −38, copies 38 bytes, `PPkc`, the count 8 and the names `rnk0` to `rnk7`; `0x05` repeats a zero byte six times; `0xD2`, −46, copies 46 bytes; `0x17`, 23, repeats `0xFF` 24 times: the first row of the first shape's first plane, 192 pixels set. Source: the file's bytes (`xxd`); `tools/rpck.py`; `tools/ppkc.py` `parse()` (eight shapes of 192 x 9 pixels); the figure, described under "Figures".
34. Two files unpack to one byte more than they declare (`cruiseship.shp`, `japplane.shp`); the original writes that byte past its buffer, the port stops at the declared size, and nothing reads it. Source: `SPEC.md` 3.5; `re/notes/porting-m1.md`, "Findings".
35. A shape container, `PPkc`: the four letters, the number of shapes, a name of four characters for each, an offset for each, then the records; a record is a header of 20 bytes (the width in bytes, the height, the hotspot, the place in its source picture, the planes cleared and set under the shape, up to six plane masks) and the planes. Source: `SPEC.md` 3.5, "`PPkc` shape container"; `re/notes/shapes.md`, "Record header, complete".
36. The game asks for its shapes by name, through lists of names in the executable's data, resolved once, when a container is loaded. (That the lookup needs a container's names in ascending order, which they all are, is in the notes and not in the prose.) Source: `SPEC.md` 3.5; `re/notes/shapes.md`, Summary and "Container and lookup".
37. IFF is the Amiga's standard file format: a file of chunks, each a four-letter name, its length and its contents; an ILBM picture holds `BMHD` (its size), `CMAP` (its colours) and `BODY` (its bitplanes, each row packed with ByteRun1). Source: IFF 85, chunks, and ILBM **(reference)**; `SPEC.md` 3.5, "Pictures" and "Palettes" (`CMAP`, its length ignored, 32 triplets).
38. The game reads its pictures with its own reader, `iff_to_vport` (`0x01A548`), which handles `BMHD`, `CMAP`, a private chunk `CMP2` and `BODY`; the port ports it rather than replacing it. Source: `SPEC.md` 3.5, "Pictures".
39. The sound effects and the maps need nothing decoded beyond reading their bytes in order; the font has a small header of its own. Source: `SPEC.md` 3.5, "Maps", "Sounds" and "Font".
40. The core holds the original's own loaders and decoders, ported: the unpacker `rpck_unpack` (`0x01FEE0`), `load_file`, the shape loader and lookup, the picture reader, `font_load`; the Python decoders `tools/rpck.py`, `tools/ppkc.py` and `tools/map_decode.py` serve the tools, the tests and this book's figures. Source: `re/notes/porting-m1.md`, "The routines"; `SPEC.md` 4 ("reference decoders") and 5, step 2 ("the core contains the ported loaders").
41. (How we know) Each loader and decoder ran twice on the same input, as the original's 68000 code under the oracle and as the port's C, the results compared byte for byte: all ten packed files and 40 random streams for the unpacker, all 55 files through `load_file`, all 1,049 shapes into pixels, all twelve ILBM files, pixels and colours, for the picture reader, all six palette files; the oracle's own self-test unpacks the ten packed files with the original's routine and compares them with `tools/rpck.py`; chapter 5 has the oracle. Source: `re/notes/porting-m1.md`, "How the tests establish it"; `tests/test_oracle_m1.py`; `SPEC.md` 4, "The oracle"; `book/BOOK.md` 3, chapter 5.

## The executable, a hunk file

42. An Amiga program is a hunk file: a row of blocks, each opening with a 32-bit type: a header (`0x3F3`) with the number of hunks and the size of each; then for each hunk its contents (code `0x3E9`, data `0x3EA`, BSS `0x3EB`), its relocations (`0x3EC`) and an end mark (`0x3F2`). Source: `tools/hunk.py` (the codes it reads); ADM, "Amiga Binary File Structure" **(reference)**.
43. A hunk is a part of the program that the loader puts into memory whole: code is the instructions, data the variables with their starting values, BSS memory that starts at zero and is given in the file by its size alone. Source: ADM **(reference)**; `SPEC.md` 3.2 (the data hunk's initialised part and its zero-filled rest); `tools/hunk.py` (a BSS hunk is `bytearray(n)`).
44. `Wings`: a header of 32 bytes; the code hunk, 77,644 bytes, with 22 relocations; the data hunk, 20,464 bytes in memory, of which the file holds the first 15,456 and the rest starts at zero; the BSS hunk, 4 bytes. Source: `SPEC.md` 3.2 (`0x3C60` initialised); `.venv/bin/python tools/hunk.py original/disk/Wings_of_Fury/Wings` (lengths `0x12f4c`, `0x4ff0`, `0x4`; relocations 5 + 17 and 34 + 213); the blocks walked by a script (the data block stores `0x3C60` bytes; the file ends at 94,292).
45. The data hunk carries 247 relocations: 213 point into the code, among them the 185 slots of the far-call table, and 34 into the data. Source: `tools/hunk.py` output; `SPEC.md` 3.2 (185 slots).
46. A relocation names a place in a hunk that holds an address, written as an offset from the start of its target hunk; the loader adds where that hunk landed. Source: `tools/hunk.py` (`v + segs[target]['base']`); ADM **(reference)**.
47. AmigaDOS loads a program with `LoadSeg`, which reads the hunk file, puts each hunk wherever it finds free memory of the kind the header asks for, and applies the relocations; so on a real Amiga the program's addresses depend on the machine and the moment. Source: RKM Autodocs, `dos.library/LoadSeg` **(reference)**; ADM **(reference)**; `SPEC.md` 3.4 (the game's own two calls of `LoadSeg`); claim 24 (a saved game's addresses of its machine).
48. The header's size word of `wofsongs`'s data hunk asks for chip memory, so that `LoadSeg` puts the songs and their sound samples where Paula can reach them. Source: `SPEC.md` 3.1 ("one chip-memory hunk"); `re/notes/music.md`, "The two files"; the header read by a script (bit 30 set in the second size word); ADM, the memory flags **(reference)**.
49. `Wings` carries no symbols: no name of a routine or a variable survives in it, and every name in the listing was given by the project; `songplay` kept its symbols (twenty in its code), so its routines have their own names. Source: `tools/hunk.py` output (`syms= 0` for all three hunks of `Wings`; 20 for `songplay`'s code); `SPEC.md` 3.1 and 3.5 (`songplay`'s exported names); `SPEC.md` 2 and 4, "Naming workflow" (`re/names.txt`, hand-maintained); `book/BOOK.md` 3, chapter 4 (names).
50. The figure `hunks`. Source: the figure, described under "Figures".

## One layout for every address

51. The project loads the executable at fixed addresses: code `0x010000`–`0x022F4C`, data `0x023000`–`0x027FF0`, BSS `0x028000`–`0x028004`; every address in the specification, the listing and the oracle uses this layout. Source: `SPEC.md` 3.2; `CLAUDE.md`, Rules.
52. The layout is `tools/hunk.py`'s: the first hunk at `0x10000`, each next one at the next 4 KB boundary after the one before. Source: `tools/hunk.py`, the `bases` loop (`(a + len + 0xFFF) & ~0xFFF`).
53. The disassembler, the oracle, the headless original and the table extractor all load the executable through it; every ported routine's comment names its original's address in it (`orig 0x......`). Source: `SPEC.md` 4 (`tools/hunk.py`, "hunk loader used by all of the above"); `re/notes/headless.md`, "Memory map" (the executable at `0x010000`, `0x023000`, `0x028000`); `tools/extract_tables.py`, `Image`; `CLAUDE.md`, Rules.
54. So an address names one place everywhere: `0x01C982` is `record_at` in the listing, in the notes, under the oracle, in the port's comment and in this book. Source: `re/names.txt` (`01c982 record_at`); `src/player.c` (`orig 0x01C982`); `tests/test_oracle_m4.py` (`0x01C982`).

## Manx Aztec C

55. The program was built with Manx Aztec C, a C compiler for the Amiga, together with hand-written assembly. Source: `SPEC.md` 3.2.
56. `0x010000`–`0x015D62` is almost entirely hand-written assembly (the main loop, the drawing, the interrupt servers, the objects' movement); from `0x015D62` come 223 C routines, the C library's among them, then the system glue; the blitter's routines, `0x0209BC`–`0x0215D8`, are hand-written too; 616 routines in all. Source: `SPEC.md` 3.2; `re/functions.csv` with `csv.DictReader` (616 rows, C 223, asm 393); chapter 4 tells how they are told apart (`book/BOOK.md` 3, chapter 4).
57. A4 is the small-data base, the constant `0x02AFFE`; the variables are addressed as a 16-bit offset from A4, and the listing prints the absolute address or name beside each such operand. Source: `SPEC.md` 3.2; `tools/disasm.py` docstring ("A4 (small-data base) = 0x02AFFE").
58. The program's first instruction (`0x010000`) jumps to the C runtime's start, `c_startup` (`0x021F2E`), whose first instruction calls `geta4` (`0x021FA0`): `lea $2affe.l,a4`; the file holds `0x7FFE` there with a relocation into the data hunk, so A4 is the data hunk's address plus 32,766, wherever the hunk lands. Source: `re/Wings.lst`, `0x010000`, `0x021F2E` and `0x021FA0`; the bytes at that instruction in the file (`49f9 00007ffe`); `tools/hunk.py`, the code hunk's relocations into the data hunk (one at `0x021FA2`).
59. An offset of 16 bits reaches from 32,768 bytes below the register to 32,767 above it; from `0x02AFFE` that is `0x022FFE` to `0x032FFD`, which takes in the whole data hunk from its first byte, and the BSS. Source: PRM 2, address register indirect with displacement **(reference)**; computed (`python -c "print(hex(0x02AFFE-32768), hex(0x02AFFE+32767))"`). Further: An instruction names a variable in two bytes where a full address takes four, and needs no relocation: when the data moves, A4 moves with it; the code hunk carries 22 relocations, 17 of them into the data, against 4,198 operands relative to A4. Source: PRM 2, the displacement of 16 bits against an absolute long address **(reference)**; `tools/hunk.py` (the code hunk's relocations, 5 into the code and 17 into the data); claim 62.
60. `-$46ec(a4)` of chapter 2 is `0x02AFFE` − `0x46EC` = `0x026912`, `rand_seed_const`. Source: computed; chapter 2's fact sheet, claim 29.
61. The hand-written assembly reaches the variables through A4 in the same way (`rand_beam`, `text_width`), so the two kinds of code share one set of variables. Source: `re/Wings.lst`, `0x0203BE` and `0x01591E`.
62. 4,198 instructions of the listing have an operand relative to A4; 659 of them are calls through the far-call table. Source: `grep '^[0-9a-f]\{6\}  ' re/Wings.lst | grep -c '\$[0-9a-f]*(a4)'` gives 4,198; the same with `jsr` gives 659.
63. Calls into the far-call table, 185 slots of `JMP abs.l` at `0x023000`–`0x023456`, are written `jsr d16(a4)`; the listing names the real target, as at `main`'s `jsr -$7e1e(a4)` (`0x01000E`). Source: `SPEC.md` 3.2; `re/Wings.lst`, `0x01000E`.
64. The calling convention: the caller pushes the arguments right to left, 2 bytes for an `int`, 4 for a `long` or a pointer; a C routine starts with `link a5`; the first argument is at `8(a5)`; the result comes back in D0. Source: `SPEC.md` 3.2; `tools/oracle.py`, docstring.
65. All 223 C routines begin with `link a5`. Source: `SPEC.md` 3.2 ("C routines start with LINK A5"); `grep -c 'link.w     a5' re/Wings.lst` gives 223.
66. `jsr` pushes the return address; `link a5,#-n` pushes A5, sets A5 to the stack pointer and moves the stack pointer n bytes further down for the routine's own variables; `unlk a5` undoes it; so `0(a5)` holds the caller's A5, `4(a5)` the return address, `8(a5)` the first argument, and the routine's variables lie below A5. Source: PRM 4, `JSR`, `LINK`, `UNLK` **(reference)**; `SPEC.md` 3.2 (the first argument at `8(a5)`).
67. A stack frame is that area of the stack; A5 is its frame pointer. Source: the term's definition in the book's words, from claim 66.
68. The figure `frame`. Source: the figure, described under "Figures".
69. `record_at` (`0x01C982`–`0x01C9C8`), compiled C, 22 instructions: `link a5,#-4`; `tst.w 8(a5)`, the world x, an `int` of 2 bytes; a negative x becomes 0; `ext.l` and `divs.w #8`, x divided by 8; `asl.w #1` and `ext.l`, times two as a 16-bit value, then widened to a long; `add.l -$69d6(a4)`, `map_records` (`0x024628`), gives the record's address, kept in the local at `-4(a5)`; at or past `map_records_end` (`-$69d2(a4)`, `0x02462C`) it becomes the last record; the result in D0; `unlk`, `rts`. Source: `re/Wings.lst` `0x01C982`–`0x01C9C8`; `re/names.txt` (`record_at`, "the map record under a world x, clamped to the list"); computed (`0x02AFFE` − `0x69D6` = `0x024628`, − `0x69D2` = `0x02462C`).
70. Its port, `wof_record_at` in `src/player.c`, carries `orig 0x01C982`, takes x as an `int16_t`, keeps the widths of `asl.w` and `ext.l` in its casts, and returns a byte offset into the record list where the original returns an address, because a pointer into the game's data becomes an offset or an index in the port. Source: `src/player.c`, `wof_record_at`; `SPEC.md` 7.2 ("a pointer into the map a byte offset").
71. The oracle holds `record_at` and its port to each other on maps a, c, h, m and o, at every world x where a record starts, at 40 around each end and at 500 random ones. Source: `tests/test_oracle_m4.py`, `test_the_map_helpers_match_the_original`.
72. An operation on a floating-point number becomes a call of the C library's glue, which opens the ROM's `mathffp.library` on first use and passes the operation on; chapter 14 has the flight model that uses it. Source: `re/notes/ffp.md`, "How the game reaches it"; `SPEC.md` 3.4, the mathffp row; `book/BOOK.md` 3, chapter 14.

## The 16-bit int

73. In Manx Aztec C as the game was built, an `int` is 16 bits; a `long` and a pointer are 32. Source: `SPEC.md` 3.2; `tools/oracle.py`, docstring.
74. A 16-bit `int` holds −32,768 to 32,767; one past the largest is the smallest. Source: computed (two's complement, 2^15); PRM 1, the integer data formats **(reference)**.
75. The C compilers that build the port give `int` 32 bits: zig cc for the WebAssembly core, Apple clang for the native library of the tests. Source: wasm C ABI, data types **(reference)**; Apple's LP64 model for the native build **(reference)**; `SPEC.md` 2 (the two compilers) and 7.1 ("Never plain `int` for game values").
76. An enemy fighter times a turn by its distance times 100 divided by its speed; the compiled code multiplies with `muls.w`, which gives 32 bits, then `ext.l` keeps the low word as a signed value before `divs.w` divides it; from a distance of 328 on the product, 32,800 and up, no longer fits, and its low word is −32,736. Source: `re/notes/porting-m6.md`, "The tick: what part 2 ports" (the enemy aircraft); `src/enemy.c`, the header comment and `turn_in` (`muls, ext.l`); computed (`python -c "print(328*100-65536)"`).
77. The rules the 16-bit int imposes on the port: never a plain `int` for a game value, but `int16_t`, `uint16_t`, `int32_t` and their kin; every width change the listing shows is reproduced (`ext.l` a sign extension; `muls.w` 16 by 16 into 32 bits, the next `move.w` or `move.l` deciding whether it is cut; `divs.w` 32 by 16 bits, cut toward zero, a 16-bit quotient); the signedness follows the branch (`blt`, `bge` signed; `bcs`, `bhi` unsigned); wrap-around is behaviour, never widened away and written as an explicit cast, because a signed overflow is undefined in today's C; floating point never through `float` or `double`. Source: `SPEC.md` 7.1.
78. A register that a routine leaves as a long reaches the next routine's upper word, which the port once took to be zero; chapter 9 tells it. Source: `SPEC.md` 7.1 (the upper word); `book/BOOK.md` 3, chapter 9 ("the register carried as a long").
79. Chapter 22 returns to the porting rules. Source: `book/BOOK.md` 3, chapter 22 ("the porting rules (the 16-bit int ...)").

## Read from the executable, never retyped

80. The rule: hand-written sources contain code only; tables, texts and tuning values come from the original executable at build time. Source: `CLAUDE.md`, Rules; `SPEC.md` 5, step 1.
81. `tools/extract_tables.py` reads `re/tables.toml`, a manifest whose entries each give a name, a kind, an address in the fixed layout and a count, and writes `src/gen/tables.c` and `src/gen/tables.h` from the executable's bytes; `src/gen/` is not versioned and is made again by every build. Source: `SPEC.md` 5, step 1; `tools/extract_tables.py`, docstring; `re/tables.toml`, header.
82. The manifest has 122 entries: 113 read from `Wings`, 7 from `songplay`, 2 from the ROM (topaz 8 and the key table). Source: `re/tables.toml` read with `tomllib` (`file = "songplay"` on 7; `topaz8` and `keymap` without an address).
83. Its kinds: 36 runs of words, 34 strings, 19 blocks of bytes, 14 runs of longs, 9 shape name lists, 6 tables of string pointers, 2 blocks of strings, the font and the key table. Source: `re/tables.toml` read with `tomllib`, the kinds counted.
84. What they hold: the nine shape name lists; the file names; the front end's palettes, the rank names, the story's text and the dialogs' words; the mission's tables (the maps of each rank, the airfields, the ships' guns, the aircraft's frames, the dashboard's windows, a table of sines); the sound effects' periods and volumes; the music player's notes and durations. Source: `re/tables.toml`, its sections and names.
85. One entry, `data_image`, is the initialised part of the data hunk whole, 15,456 bytes, from which every variable the port keeps at an address inside it starts with the original's value. Source: `SPEC.md` 5, step 1; `re/tables.toml` (`data_image`, `0x023000`, 15456).
86. The texts are in the code hunk, after the routine that uses them; the story's text, `0x017494`–`0x017CFB`, is read from there. Source: `SPEC.md` 3.2 ("String literals live in the CODE hunk"); `re/tables.toml`, the comment of `story_text`.
87. Some values are operands of instructions: `sound_slots_init` (`0x011F76`) sets up the sound slots 0 to 6 in seven runs of `0x22` bytes; for slot 4, the burst, the listing's part `0x011FFE`–`0x01201C` hands the slot `sound_boom_ptr` and the burst's length (`0x025576`, which `sounds_load` fills with the length of `sounds/boom` at `0x013404`), then `move.w #$1f4,-$3c2c(a4)` at `0x01200A`, the period 500, chapter 2's, a volume of 64 (`$40`) and a count of 1, played once; the entry `slot_periods` reads the word at `0x011F84` and every `0x22` bytes after it, seven in all (200, 380, 160, 330, 500, 350, 320), slot 4's at `0x01200C`. Source: `re/tables.toml`, `slot_periods` and its comment; `re/Wings.lst` `0x011FFE`–`0x01201C` and `0x0133FC`–`0x01340C`; `re/names.txt` (`sound_slots_init`, `sound_boom_ptr`); `re/notes/sound.md`, the slot table (slot 4: `0x1F4`, repeat 1); `extract_tables.Image` read at the seven addresses; chapter 2's fact sheet, claim 87.
88. Big-endian is the byte order with the most significant byte first, the 68000's and that of every file the project reads; the extraction converts it. Source: `SPEC.md` 3.5 ("All multi-byte values are big-endian") and 5, step 1 ("Byte order is converted during extraction"); PRM 1 **(reference)**.
89. What the rule buys: a value typed again could be typed wrong and nothing would say so; a value read from the executable is the original's own, and an address outside the executable stops the build. Source: `CLAUDE.md`, Rules; `tools/extract_tables.py`, `Image.bytes` (`SystemExit`, "is outside the executable").
90. It also keeps the game out of the port's sources: the code is free software, the game's data stands under neither licence, and the generated tables are never committed. Source: `README.md`, Licence; `SPEC.md` 5, step 1 (`src/gen/` ignored by version control).
91. (For the developer) The file system packed into the page: the magic `WOFS`, a version, the file count, the directory's offset, then 40-byte entries of a 32-byte name, an offset and a length, big-endian. Source: `SPEC.md` 5, step 2; `tools/build.py`, `pack_fs()`.
92. (For the developer) The hunks: code `0x010000`–`0x022F4C`, data `0x023000`–`0x027FF0` with its stored part to `0x026C60`, the far-call table `0x023000`–`0x023456`, BSS `0x028000`, A4 `0x02AFFE`; `tools/hunk.py FILE` prints a hunk file's hunks with their relocations and symbols, `tools/rpck.py FILE` a file's packed and unpacked sizes. Source: `SPEC.md` 3.2 and 4; the tools' `__main__` blocks; computed (`0x023000` + `0x3C60` = `0x026C60`).

## What comes next

93. Chapter 4 takes the disassembler and the listing, the names, the control-flow skeleton, and compiled C against hand-written assembly. Source: `book/BOOK.md` 3, chapter 4.
94. The repository is `github.com/sy2002/wof-wasm`. Source: `README.md`, Build; `book/mkdocs.yml`, `repo_url`.

## The chapter references the prose makes, each checked against `book/BOOK.md` 3

| Reference | Where in the prose | The outline's chapter |
|---|---|---|
| chapter 2 | the opening (`-$46ec(a4)`), the sounds (`sounds/boom`), A4, the tables (the burst's period) | 2, The Amiga in twenty minutes |
| chapter 4 | the compiler (C against assembly), the names, What comes next | 4, Reading the executable: the listing, names, the skeleton, compiled C against hand-written assembly |
| chapter 5 | How we know (the decoders), the listing's test | 5, The oracle |
| chapter 9 | the 16-bit int (the upper word) | 9, What went wrong: the register carried as a long |
| chapter 11 | the palettes (day and night) | 11, The display: day and night |
| chapter 12 | the shape containers | 12, Shapes: the containers |
| chapter 13 | the maps | 13, The world: the map file and its records |
| chapter 14 | the floating point | 14, The player: the flight model on the ROM's floating point |
| chapter 17 | the saved game, the demo's file | 17, The campaign: the saved game's bytes, the demo |
| chapter 18 | the music's two files | 18, Sound and music: the music player |
| chapter 20 | the image (the directory order) | 20, The original's quirks: the directory order |
| chapter 22 | the 16-bit int (the rules) | 22, The core: the porting rules, the file system |

## Counts and where they were counted

| Count | Value | Where, and the command |
|---|---|---|
| the image | 901,120 bytes, 1,760 blocks of 512 | `stat -f %z original/wof.adf`; `python -c "print(901120//512)"` |
| the game's directory | 65 files, 664,981 bytes | `find original/disk/Wings_of_Fury -type f ! -name .DS_Store`, sizes by `os.path.getsize` |
| packed into the page | 55 files, 540,960 bytes | `tools/build.py` `game_files()`, sizes summed |
| left out | `Wings` 94,292 and nine files not the game's, 29,729 | `find` and `stat`; 540,960 + 94,292 + 29,729 = 664,981 |
| shape containers | 12, 240,092 bytes, 1,049 shapes (8 to 223) | `ls shapes/*.shp`; `tools/ppkc.py` `parse()` per file |
| pictures | 9 IFF ILBM, 122,484 bytes | `stat`; first bytes `FORM` and `ILBM` |
| palettes | 6, 1,428 bytes; 3 `CMAP`, 2 `Rpck`, 1 `FORM` | first bytes |
| maps | 15, 1,910 to 7,138 bytes, 68,946 in all | `stat`; `re/notes/map.md` |
| sound effects | 8, 1,886 to 13,919 bytes, 51,832 in all | `stat` |
| `songplay`, `wofsongs` | 5,148 and 41,328 bytes | `stat`; `re/notes/music.md` |
| `newarmyfont` | 2,476 bytes | `stat` |
| `highscore` | 360 bytes, 10 x 36 | `stat`; `re/notes/highscore.md` |
| `wof.mission 3` | 6,866 bytes | `stat`; `re/notes/campaign.md` |
| saved games by map | 4,258 (a) to 11,516 (m); seven above 8,192 | `re/notes/campaign.md`, "The sizes" |
| the largest save the port allows | 12,412 bytes | `src/wof.h`, `WOF_SAVE_MAX`: `python -c "print(0x84A+2+3576*2+4*16*14+32*14+160*8+2*16*16)"` |
| packed files | 10 | the first four bytes of every file |
| `selectrank.shp` | 1,656 packed, 5,630 unpacked, 8 shapes of 192 x 9 | `stat`; `tools/rpck.py`; `tools/ppkc.py` `parse()` |
| `Wings`'s hunks | code 77,644 (22 relocations), data 20,464 (15,456 stored, 247 relocations), BSS 4 | `tools/hunk.py`; the blocks walked by a script |
| far-call slots | 185 | `SPEC.md` 3.2 (`0x456` / 6 = 185) |
| A4's reach | `0x022FFE` to `0x032FFD` | computed |
| operands relative to A4 | 4,198, of which 659 far calls | `grep` on `re/Wings.lst` (claim 62) |
| C routines, routines | 223 of 616; 223 `link a5` | `re/functions.csv` with `csv.DictReader`; `grep -c 'link.w     a5' re/Wings.lst` |
| `record_at` | 22 instructions, `0x01C982`–`0x01C9C8` | `tools/skel.py 01c982 --all` |
| the code hunk's relocations | 22: 5 into the code, 17 into the data | `tools/hunk.py original/disk/Wings_of_Fury/Wings` |
| the chapter's words | 3,974 | `wc -w book/docs/part-1/disk.md`, the whole file with alt texts, captions, sidebars and the further reading |
| `songplay`'s symbols | 20 in its code hunk | `tools/hunk.py original/disk/Wings_of_Fury/songplay` |
| tables | 122 entries: 113 `Wings`, 7 `songplay`, 2 ROM | `re/tables.toml` with `tomllib` |
| `data_image` | 15,456 bytes | `re/tables.toml` |
| slot periods | 200, 380, 160, 330, 500, 350, 320 | `extract_tables.Image(EXE).bytes(0x011F84 + 0x22 * i, 2)` |
| the 16-bit product | 328 x 100 = 32,800, low word −32,736 | computed |

## Figures

Four, in the order of the chapter: two of new makers of `book/tools/figures.py`, two diagrams drawn by hand.

- `disk-files.png` (new maker `disk`): the game's directory as eleven rows, one for each kind of file in the order of the chapter (the program, the music, the shape containers, the pictures, the palettes, the maps, the sound effects, the font, the high scores, a saved game, the files not the game's): its files, their count and bytes, the formats their first bytes show (a hunk file, `Rpck`, `PPkc`, IFF ILBM, a bare `CMAP`) or the manifest's word for the rest, and a bar of the bytes to scale with every file a segment of it, gold where the files go into the page and grey where they are left out; the maker fails when a file of the directory belongs to no row or to two. Claims 9 to 27.
- `packed-selectrank.png` (new maker `packed`): the first 98 bytes of `shapes/selectrank.shp` on the disk, 16 to a row, the four control bytes in gold and the byte a repeat writes in blue, each control spelled out beside its row; under them the first 114 bytes they unpack to, the bytes a repeat made in blue, and the container's fields named beside their rows (`PPkc` and the count, the names, the offsets, the first record's header, its plane data). The maker checks the bytes it shows against `tools/rpck.py`. Claims 31 to 36.
- `hunks.svg` (new, drawn by hand under `book/docs/figures/`): on the left the file `Wings` as its blocks (the header, the code with its relocations, the data with its relocations, the BSS) with their sizes; on the right memory in the fixed layout, the code at `0x010000`, the data at `0x023000` with its initialised part and its zeros, the BSS at `0x028000`; arrows from each hunk to its place; A4 at `0x02AFFE` with the span its 16-bit offsets reach. Claims 42 to 59.
- `frame.svg` (new, drawn by hand): `record_at`'s view of memory: the stack with the caller's argument at `8(a5)`, the return address at `4(a5)`, the caller's A5 at `0(a5)` and the local at `-4(a5)`, A5 and A7 marked; beside it the data hunk with A4 and the two variables at `-$69d6(a4)` and `-$69d2(a4)`. Claims 64 to 69.

## Listings

- `record_at` (`kind = "asm"`) beside `wof_record_at` (`kind = "c"`): compiled C with its frame on A5, a 16-bit argument, two variables through A4, the widths the port keeps. Claims 69 and 70.
- `sound_slots_init`, the part `0x011FFE`–`0x01201C` (`kind = "asm"`, `as = "sound_slots_init_boom"`): slot 4 set up, the burst's sample and length, the period 500 as an instruction's operand, the volume and the count. Claim 87.

## Terms and glossary entries

Introduced in chapter 3, in bold with an entry: ADF, big-endian, BSS, calling convention, far-call table, fixed load layout, hunk, hunk file, IFF ILBM, int (the glossary's heading "int (the C type)", so that a reader finds it), LoadSeg, Manx Aztec C, relocation, Rpck, shape container, small-data base, stack frame. Used from chapters 1 and 2 and linked, not redefined: chip memory, register, 68000, assembly language, machine code, Paula, sound sample, palette, library, Kickstart, topaz 8, oracle, headless original, attract demo, fast floating point, bitplane, hexadecimal, core. Defined in passing without an entry: the listing (chapter 4's), a drawer, the hotspot, a plane mask, a chunk, the symbol table, sign extension, a frame pointer. No bare "sample".

## Sidebars

- What went wrong: the file system's limit of 8,192 bytes, sized from one saved game (claim 30).
- How we know: the loaders and decoders under the oracle (claim 41).
- For the developer: the file system's container, the hunks and the tools (claims 91, 92).

## Left to later chapters

The disassembler, the listing, the names, the skeleton and compiled C against hand-written assembly (4); the oracle (5); the upper word (9); day and night (11); the shapes, their mirrors and the blit (12); the maps' records and the world (13); the floating point in the flight model (14); the saved game's fields, the demo and the high scores (17); the music's files and the player (18); the directory order (20); the porting rules and the port's file system (22).

## Unsourced

Kept out of the draft: what `UFXintro` and `wingt` are; why the crack's disk carries a second copy of the executable and the two small commands at its top level; the volume's name; why Manx Aztec C places A4 32,766 bytes into the data (the chapter states the reach, which is computed, not the compiler's reason); why the game routes some calls through the far-call table and others not; whether an enemy fighter's distance ever passes 327 in play.
