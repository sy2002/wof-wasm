# Fact sheet: chapter 21, A tour of the repository

Every claim the chapter makes, one line each, with its source, in the order of the chapter. A claim without a source goes to the list at the end and stays out of the draft. A general fact that the repository does not state is sourced in a reference work and marked **(reference)**; what the repository holds always comes from its own files, counted at the branch's base. No "How we know" box and no "What went wrong" box (`book/BOOK.md` 4, point 6); the one sidebar is *For the developer*.

Counts are of the branch's base, `eb4d3f4`, counted in the files named, with the command in the counts table at the end. No run of the port, no headless original, no test run (one `pytest --collect-only -q`), no browser, no rebuild.

Words used in the sheet as the chapter will use them, each in one sense. The **repository** is the project's files with their history, as a clone holds them; a file is *in the repository* when `git ls-files` lists it. A **note** is a file of `re/notes/`, never a remark. **The listing** is `re/Wings.lst`; the extracts this book shows are **the book's listings**, never "listings" alone. **The page** is `dist/wof.html`; a page of the book or of the manual is named so. A **run** is a run description of `tests/runs/` or what the headless original does with it; a run of the suite is "a run of the suite". A **contact sheet** is a picture of `ref/sheets/`; a **fact sheet** is a file of `book/facts/`; "sheet" alone is not used in the chapter. A **chain** is one of the chapter's four ways the parts hang together (the names, the tables, the comparison, the generated files); the word needs no entry. A **generated file** is the chapter's term (claim 98); a **porting note** too (claim 48). `README.md` is a file, glossed in a clause, not a term (the controller's note 2).

The reference works:

- Wikipedia, "README", `https://en.wikipedia.org/wiki/README`, fetched once: a README file holds descriptive information about the contents of the directory it lies in, typically at the top level of a project, the entry point for a reader. Source of the clause "by convention the file a reader of a repository opens first" (claim 4). **(reference)**
- Wikipedia, "GNU General Public License", `https://en.wikipedia.org/wiki/GNU%5FGeneral%5FPublic%5FLicense`, fetched once: a series of widely used free software licences; copyleft: whoever distributes a modified version must pass on the same terms; version 3 of 2007. **(reference)**
- Creative Commons, "Attribution-ShareAlike 4.0 International", `https://creativecommons.org/licenses/by-sa/4.0/`, fetched once: the two conditions, attribution (credit, a link to the licence, changes indicated) and share-alike (contributions under the same licence). **(reference)**
- Wikipedia, "Git", `https://en.wikipedia.org/wiki/Git`, fetched once: a distributed version control system; `git clone` duplicates a repository, and each copy holds the entire repository with its history. **(reference)**
- MkDocs, `https://www.mkdocs.org/`, fetched once: a static site generator geared towards project documentation; Material for MkDocs is its theme (`book/BOOK.md` 5). **(reference)**
- pytest, `https://docs.pytest.org/`, fetched once: a framework for writing tests in Python. **(reference)**
- Unicorn (the 68000 emulator), Capstone (the disassembly library) and zig (the WebAssembly compiler, as the `ziglang` package): named with their pinned versions in `SPEC.md` 2; chapters 4, 5 and 6 cite their sites. **(reference)**

## Opening

1. By the chapter's end the reader knows where each kind of thing lives (the rules, the ground truth, the reading, the core, the shell, the instruments, the tests, the page, the book), why it lives there, how four chains tie the parts together, where to start for what they want, and what the repository leaves out and why. Source: `book/BOOK.md` 3 (Part III, chapter 21); the controller's task.
2. Earlier chapters told the mechanisms; this one says where they live and links: chapter 3 the disk, the manifest, the 55 packed files; 4 the listing, the names, the inventory, the skeleton; 5 the oracle; 6 the headless original and the run description; 8 the reach map, the scripts, the loops; 10 the sessions, the handbooks, the rules. Source: the chapters under `book/docs/part-1/` at `eb4d3f4`.
3. The repository is at `github.com/sy2002/wof-wasm`, the link every chapter's further reading gives; the book links into it with its `repo:` scheme. Source: `book/docs/part-1/faithful.md` (line 28 and its further reading); `book/BOOK.md` 5, "Writing a page".

## 1. The top level

4. `README.md` is the door, written for a reader who has just cloned: what the port is, how to play, build and verify, the ROM, the book, where things are, the idea of a template, the licence. Source: `SPEC.md` 2 (`README.md  for a reader who has just cloned: play, build, verify, the ROM, where things are, the licence`); `README.md`'s headings: Play; Build and verify (Prerequisites, The Kickstart ROM, Build, Verify); The book; Where things are; Amiga to Web; Licence. "By convention the file a reader of a repository opens first": the reference above. Not a bold term (the controller's note 2).
5. Its picture is the title screen rendered by the port's native library in the PAL aspect, `ref/title.png`; the chapter links Native library (chapter 5). Source: `README.md` (`![](ref/title.png)`); commit `7a159ba`'s subject ("the title screen, rendered by the port's own library in the PAL aspect"): the port's only library is the native library (`SPEC.md` 5; the glossary's Native library). (B, C2)
6. `SPEC.md` is the source of truth for goals, architecture, porting rules and milestones, written for an engineer, human or AI agent, working in the repository with its tools. Source: `CLAUDE.md` ("Read `SPEC.md` first; it is the source of truth for goals, architecture, porting rules and milestones"); `SPEC.md`'s opening line ("Target reader: an engineer (human or AI agent) working in this repository with the tools it already contains").
7. Its ten sections, one line each, as the chapter's table gives them: 1 one HTML file, faithful defined, what is out of scope; 2 this layout, the pinned packages; 3 the disk, the executable, how it runs, the formats; 4 the tools, the listing's conventions, the naming; 5 from the manifest to the page; 6 core, shell, picture and sound, what is not ported; 7 arithmetic, data, determinism, working method; 8 each level of comparison and its method; 9 M0 to M10, deliverables and acceptance; 10 thirteen questions, each answered in a note. Source: `SPEC.md`'s headings (`grep -n "^#" SPEC.md`) and sections; section 10's table (13 rows).
8. Section 1 defines faithful in three parts: the same game state after every logic tick for the same seed and input bytes; the same indexed pixels and palette for the same state; the same sound sample started on the same channel at the same tick with the same period and volume, and the music on the original player's timing. Chapter 1 told it. Source: `SPEC.md` 1, "Definition of faithful"; `book/docs/part-1/faithful.md`.
9. Section 6.6 names what is not ported (the C runtime's start-up, the system's glue, the memory management, the copper's construction, the interrupt plumbing, Workbench, the debug and crash reporters, the protection check, the crack screen), marked `replace` or `drop` in the inventory. Source: `SPEC.md` 6.6.
10. `CLAUDE.md` is the working rules every session reads: the commands, the session protocol, the rules; it is short (926 words). Source: `CLAUDE.md`'s headings ("Commands", "Session protocol", "Rules"); `SPEC.md` 2 ("short working rules for agent sessions"); `wc -w CLAUDE.md`.
11. Its commands block, lines 10 to 24 of `CLAUDE.md`, fifteen commands, from the setup of a fresh clone to the visible Firefox run: the ROM check, the disassembler, the skeleton, the oracle's self-test, the headless original, the reach map, the Markdown check, the two builds, the suite serially and in its two phases, the comparison of two runs' outcomes. Source: `CLAUDE.md` lines 9 to 25 (`grep -n "" CLAUDE.md`). Listing 1.
12. The rule the repository rests on: the repository is the handover, and nothing may live only in a conversation; a session starts from `SPEC.md` and the notes and ends by writing back names, findings, statuses and corrections. Source: `CLAUDE.md`, "Session protocol" ("The repository is the handover: nothing may live only in a conversation"; "Start", "End"); `book/docs/part-1/making.md`, "Who we were".
13. `CONTROLLER.md` is the handbook of the session that leads, published as it was used; chapter 10 told the arrangement. Its sections: The arrangement; The user's conventions; Driving workers; What a task contains; Reviewing a report; Asking the user; Models and effort; The plan ahead; Open items; Pitfalls that cost time. Source: `grep -n "^#" CONTROLLER.md`; `book/docs/part-1/making.md` ("The sessions' handbook, `CONTROLLER.md`, is published as it was used"); `CLAUDE.md` ("The session that leads the project, the controller, also reads `CONTROLLER.md`; workers do not need it").
14. "Pitfalls that cost time" is a list of warnings, each a lesson that cost time once: 28 at the base. Source: `CONTROLLER.md` (`awk` count of its bullets, counts table). The chapter gives no count.
15. Two licences: `LICENSE` is the GNU General Public License, version 3 or later, for the code and the tools (`src/`, `web/`, `tools/`, `tests/`, the build); `LICENSE-CC-BY-SA-4.0` is Creative Commons Attribution-ShareAlike 4.0 International, for the prose (`SPEC.md`, the notes, the book). The seven library lists under `tools/fd/` come from amitools under its own licence, the GPL version 2, as `tools/fd/ORIGIN.txt` says; the chapter says "under its own licence, as their origin file says". Source: `README.md`, "Licence"; `SPEC.md` 1 and 2; `head -3 LICENSE`, `head -1 LICENSE-CC-BY-SA-4.0`; `tools/fd/ORIGIN.txt` ("Copied unmodified from amitools 0.8.1 ... licensed under the GPL v2"). (B14)
16. Both are copyleft: a changed version passes on under the same terms. Source: the references (GPL, CC BY-SA). **(reference)**
17. The game data is under neither: everything under `original/`, the two listings `re/Wings.lst` and `re/songplay.lst`, which reproduce the program's and the music player's code, the contact sheets of `ref/sheets/`, and the game data in `dist/wof.html`; it is the work of its authors and publisher, kept for preservation, and no right to it is granted. The book's figures rendered from the game's data and its listings taken from the executable stand under the same reservation. Source: `README.md`, "Licence"; `book/BOOK.md`'s opening paragraph ("the figures rendered from the game's data and the listings taken from its executable are the game's and stand under the same reservation as `original/`"); `SPEC.md` 2 (`re/songplay.lst  annotated disassembly of the music player`). (B14, C22)
18. The ROM image is in no file of the repository; the two small tables the build reads from it, topaz 8's glyphs and the key conversion, travel inside the page. Source: `README.md`, "Licence" ("The Kickstart ROM is not in the repository at all"); `.gitignore` (`original/kick.rom`); `SPEC.md` 5, step 1 (the topaz 8 glyphs and the key conversion read from `original/kick.rom` into the generated tables, which the core compiled into the page carries); chapter 3 (the manifest's 2 entries from the ROM). (B7)
19. `requirements.txt` pins the port's seven Python packages at exact versions: capstone 5.0.9, numpy 2.4.6, pillow 12.3.0, pytest 9.1.1, pytest-xdist 3.8.0, unicorn 2.1.4, ziglang 0.16.0; `tools/setup.sh` installs them into `.venv`. zig arrives as a Python package carrying the C compiler that makes the WebAssembly core, so that nothing else need be installed for the page; the native library is built with Apple clang (`SPEC.md` 5), so the chapter names only the WebAssembly core. Source: `requirements.txt`; `SPEC.md` 2 ("`ziglang` 0.16.0, which provides a C compiler and linker for WebAssembly"); `CLAUDE.md` ("`tools/build.py` compiles the core with `.venv/bin/python -m ziglang cc -target wasm32-freestanding`; nothing else needs to be installed"); `README.md`, "Prerequisites" ("no system compiler is needed for the page"). No reason for the exact pins beyond the README's is given (C16). (C4, C16)
20. `.gitignore` keeps out the ROM, everything the build writes under `dist/` but the page, the tables generated into `src/gen/`, the local environment `.venv/`, compiled files (`*.wasm`, `*.o`, `*.dylib`), the test runner's cache and the book's built site `book/site/`. Source: `.gitignore`.
21. The top level holds eight files: `.gitignore`, `CLAUDE.md`, `CONTROLLER.md`, `LICENSE`, `LICENSE-CC-BY-SA-4.0`, `README.md`, `requirements.txt`, `SPEC.md`. Source: `git ls-files` (counts table).

## 2. The directories at a glance

22. The repository holds 719 files at the base, in nine directories and the eight files of the top level. Source: `git ls-files | wc -l`; the table below.
23. The table (files exact, lines rounded as chapter 10 rounds them; a count of `book/` grows with every chapter and is rounded):

| Directory | Files | What it holds | Size |
|---|---|---|---|
| `original/` | 78 | the disk image, its 76 files extracted, the manual's text | the image 901,120 bytes |
| `re/` | 37 | the listing, the names, the inventory, the manifest, the player's listing and names, 29 notes | the listing 1,627,981 bytes, 32,434 lines; the notes 196,970 words |
| `ref/` | 8 | seven contact sheets and the title picture | |
| `src/` | 41 | the core: 35 C files, 3 headers, 3 registries | 19,436 lines |
| `web/` | 10 | the shell: 8 modules, the template, the stylesheet | 2,404 lines |
| `tools/` | 52 | 43 Python tools, the setup script, the libraries' lists (`fd/`, 8 files) | 12,402 lines of Python and shell |
| `tests/` | 101 | 49 Python files (34 test modules), 14 Node drivers, 2 C files, 36 JSON files | 22,951 lines of Python, JavaScript and C |
| `dist/` | 1 | the page | 1,158,496 bytes |
| `book/` | 383 | the handbook, the site, its generators, the fact sheets, the generated files | grows with each chapter |

Source: the counts table. In the chapter: files exact but `book/` ("about 380"); the size column with its unit in every cell and labelled by what it counts: the image "about 880 KB", the listing "about 1.6 MB" and the notes "about 197,000 words", "8 pictures", "about 19,400 lines of C", "about 2,400 lines of JavaScript, HTML and CSS" (2,193 + 50 + 161), "about 12,400 lines of Python and the setup script" (12,317 + 85; among them `tools/m6_runs.py`, 435 lines written by `tools/m6_emit.py`, and `tools/m7_runs.py`, 47 lines written by `tools/m7_autopilot.py --all`, so the chapter no longer says "written by hand"), "about 23,000 lines of Python, JavaScript and C", the page "about 1.2 MB" (chapters 1 and 10 round so). (B5, C24)

## 3. original/

24. `original/` is the ground truth and read-only: nothing in it is ever modified, moved or deleted. Source: `CLAUDE.md`, "Rules"; `SPEC.md` 2 ("the disk image (read-only ground truth)").
25. It holds the disk image `original/wof.adf`, 901,120 bytes (880 KB); the disk's files extracted verbatim with xdftool under `original/disk/`, 76 files, 65 of them in the game's directory `Wings_of_Fury`; and the manual as text, `original/manual.txt`, 13 pages. The chapter names the three and gives no count of the files, leaning on chapter 3 (C24). Source: `SPEC.md` 2; `wc -c`; `git ls-files original/disk | wc -l`; `git ls-files original/disk/Wings_of_Fury | wc -l`; `grep -c "^PAGE" original/manual.txt`; chapter 3 (65 files).
26. Why the files beside the image: the port and the tools read the extracted files; the image is read for the directory's order alone. Source: `book/docs/part-1/disk.md`, "An image of the floppy".
27. The build packs 55 of the files into the page and leaves out ten: the program `Wings`, whose tables are read from it at build time, and nine files not the game's, `UFXintro`, `wingt` and seven `.info` files (`SPEC.md` 5, step 2, adds every dotfile, none of which is in the game's directory). Source: `SPEC.md` 5, step 2; chapter 3 ("all but the program and those nine"; "Nine files are not the game's at all: `UFXintro`, `wingt` and seven `.info` files").
28. The manual is read for the intended behaviour and the key commands, cited by page, never pasted into sources, notes or documents. Source: `CLAUDE.md`, "Rules"; `SPEC.md` 2 ("never quoted at length").
29. The ROM image, `original/kick.rom`, is placed by whoever clones, beside the disk image, where the build and the tools look for it: Kickstart 1.3, revision 34.5, the A500 and A2000 image, 262,144 bytes; `tools/rom.py` checks it by its SHA-1; without it the build stops and the suite skips, each with a message saying where to get it. Source: `CLAUDE.md`, "Rules"; `README.md`, "The Kickstart ROM" ("It goes to `original/kick.rom`; the setup checks it") and "Build"; `tools/extract_tables.py` line 32 (`ROM = os.path.join(ROOT, 'original', 'kick.rom')`); `tools/rom.py`. (C5, C15)
30. What the ROM gives: the system font topaz 8, the key conversion with the default keymap, and mathffp, the reference of the game's floating point. Source: `SPEC.md` 2 (`original/kick.rom` line); `README.md`, "The Kickstart ROM".

## 4. re/

31. `re/` holds the reading of the program: what the project has learnt of it, as generated files and hand-kept files side by side. Source: `README.md`, "Where things are" ("the annotated disassembly ..., the names, the function inventory, and the notes on every subsystem"); `SPEC.md` 2.
32. The listing `re/Wings.lst`: the program as annotated assembly, generated by `tools/disasm.py`, about 1.6 MB, 32,434 lines; versioned and held to its regeneration by `tests/test_generated.py`; never edited by hand and never loaded whole by a session. Source: `SPEC.md` 2; `CLAUDE.md` ("Never edit `re/Wings.lst` by hand"; "Never load `re/Wings.lst` whole. It is about 1.6 MB"); `wc -c -l`; chapter 4.
33. The names live in `re/names.txt`, kept by hand, one line a name: a hexadecimal address, a name, and after a semicolon a comment; its first line says so and that `tools/disasm.py` reads it. Source: `re/names.txt` line 1; `SPEC.md` 2 ("hand-maintained names for code and data addresses"); chapter 4. Listing 2.
34. Why apart: the listing is made again whenever a name changes or the tool learns something, so a name typed into the listing would be lost at the next run. Source: `book/docs/part-1/reading.md`, "Names"; `SPEC.md` 4, "Naming workflow".
35. `re/names.txt` has 883 lines and 822 name lines, naming 798 addresses (chapter 4's count). Source: `wc -l`; chapter 4's sheet, claim 40 (`book/facts/04-reading.md`). The chapter gives no count but links chapter 4.
36. The inventory `re/functions.csv`: a row for each of the 616 routines and thirteen columns, `addr`, `name`, `kind`, `span`, `frame`, `a5_args`, `far_slot`, `callers`, `calls`, `os_calls`, `globals`, `strings`, `status`; generated with the listing. The chapter names them in a sentence: the address, the name and kind, the size, the frame, where the arguments lie above A5, the far-call slot, the count of the callers, the routines called, the system calls made, the count of the variables, the strings and the status. Source: `csv.DictReader` (counts table); chapter 4; the rows of listing 3 (`callers` 9 for `record_at`, `globals` 2; `a5_args` `8 10` for `flash_set`). (B16)
37. The status column is the one kept by hand, carried over at every regeneration; all other columns are recomputed. Source: `SPEC.md` 7.4 (closing paragraph); `CLAUDE.md`, "Rules".
38. The status counts at the base: verified 167, ported 155, partial 1, replace 47, drop 36, todo 210 (`collections.Counter` over the `status` column). The chapter names no count and says: a routine starts as `todo`; `replace` and `drop` record a decision about what the specification leaves out, such as the memory and the crack's screen; most of what still says `todo` is the C library, the system's glue or code nothing calls, which needed no decision; chapter 4 tells the meanings, chapter 10 counts them. Source: `book/docs/part-1/reading.md`, the status table (`replace`: "the memory, the copper lists, the calls into the floating point"; `drop`: "the crack's screen, the debug reporters") and "117 of them lie at the end of the code, in the C library and the code that talks to the operating system, and 67 have no caller"; `book/docs/part-1/making.md` ("A routine starts as `todo`, while `replace` and `drop` mark a decision; most of the 215 are the C library and the system's glue at the end of the code, or code with no caller in the listing, on which nothing had to be decided"); `SPEC.md` 6.6. (C6)
39. Listing 3 shows the column names and eight rows, `record_at` to `sub_01cb1c`: compiled and hand-written routines, statuses `verified`, `ported` and `todo`, a far-call slot, arguments at `8(a5)`. Source: `re/functions.csv` lines 1 and 338 to 345.
40. `re/libbases.txt`, kept by hand, names the five variables that hold a library's base (exec, intuition, graphics, dos, mathffp). Source: `re/libbases.txt` (5 entries); `SPEC.md` 2; chapter 4.
41. The **manifest** `re/tables.toml` (the term, defined here: the list of what the build reads out of the original's files), 122 entries, each with a name, a kind, where to read and how much: 113 from the program `Wings`, 7 from the music player `songplay`, 2 from the ROM. Source: `tomllib` (`len(t['table'])` = 122; 7 with `file = "songplay"`; 2, `topaz8` and `keymap`, without an address); chapter 3 (113, 7, 2); `re/tables.toml`'s header comment ("An entry is (name, kind, address, count)"); `tools/extract_tables.py` lines 30 to 32 (the three files). (B4, C31)
42. The music player has a listing of its own, `re/songplay.lst` (935 lines), generated by `tools/disasm_player.py` from `songplay`'s hunks, with its names in `re/songplay_names.txt` (54 names), at addresses of its own layout. Source: `SPEC.md` 2; `re/songplay_names.txt`'s opening comment; `wc -l`; the regex count (counts table); `tools/disasm_player.py` docstring.
43. After a change to `re/names.txt`, `re/libbases.txt` or `re/songplay_names.txt`, the two disassemblers are run and what they write is committed. Source: `CLAUDE.md`, "Rules".
44. `re/notes/` holds 29 notes, one Markdown file a subject, about 197,000 words in all (196,970; chapter 10's "about 196,000" was right at its base); the words stand once, in the directory table (C24); the later sessions start from them instead of deriving again. Source: `ls re/notes | wc -l`; `cat re/notes/*.md | wc -w`; `SPEC.md` 2 ("one Markdown note per understood subsystem"); `SPEC.md` 7.4, step 6; `CLAUDE.md` ("When a subsystem is understood, write it down in `re/notes/` so that later sessions do not re-derive it").
45. A subsystem note gives the purpose, the data structures with offsets, the routines and the open points. Source: `SPEC.md` 7.4, step 6.
46. The notes of the milestones mark every statement as observed or measured, with the tool or test that shows it, or as read from the listing alone. Source: `book/docs/part-1/making.md`, "Inside a milestone"; `book/docs/part-1/reading.md`, "A reading is a claim".
47. The notes table (claim 56 for the kinds; words by `wc -w` at the base; the chapter that tells each from the chapters' further reading, `grep` per chapter; the shell's and the tests' notes go to chapters 23 and 24, still to be written):

| Note | Subject (its title) | Words | Chapter |
|---|---|---|---|
| `campaign.md` | The campaign and the saved game | 3,651 | 17 |
| `demo.md` | The demo | 1,627 | 17 |
| `display.md` | Display geometry and colours | 3,497 | 11 |
| `drawing.md` | Drawing routines and read-back | 3,704 | 12 |
| `enemy.md` | The enemy aircraft, the ships and the carrier's defence | 4,478 | 16 |
| `ffp.md` | The game's floating point | 3,044 | 14 |
| `frontend.md` | The front end | 3,981 | 19 |
| `highscore.md` | The high-score file | 744 | 17 |
| `input.md` | Input | 1,050 | 7 |
| `keys.md` | The key commands | 3,218 | 19 |
| `map.md` | The maps and the world coordinate system | 2,355 | 13 |
| `music.md` | The music player and the songs | 2,723 | 18 |
| `objects.md` | The object system | 4,173 | 15 |
| `passes.md` | Per-tick and per-pass state | 2,492 | 7 |
| `random.md` | Randomness and video rate | 617 | 6, 7 |
| `shapes.md` | Shapes: containers, name resolution, record header | 2,889 | 12 |
| `sound.md` | The sound effects engine | 2,201 | 18 |
| `system-font.md` | System font | 442 | 19 |
| `porting-m1.md` | M1: the loaders, the pixels, the tests | 2,126 | 3, 12 |
| `porting-m3.md` | M3: the front end as coroutines | 3,491 | 19 |
| `porting-m4.md` | M4: the world, the player and the tick | 27,461 | 8 |
| `porting-m5.md` | M5: the weapons and the ground targets | 22,780 | 15 |
| `porting-m6.md` | M6: the enemy, the ships, the torpedo attack, the carrier's defence | 34,201 | 16 |
| `porting-m7.md` | M7: the campaign and the saved game | 33,514 | 17 |
| `porting-m8.md` | M8: the sound effects engine and the music | 10,930 | 18 |
| `page-video.md` | The page's picture on the GPU (M9) | 4,202 | 23 |
| `headless.md` | The headless original | 7,554 | 6 |
| `testing.md` | Running the test suite | 2,496 | 24 |
| `amiga-to-web.md` | Amiga to Web: the idea of a template | 1,329 | 10 |

Source: each note's first line (`head -1`) and `wc -w`; the chapters' further reading (`awk '/^## Further reading/' ... | grep -o "repo:re/notes/..."`): chapter 17 names campaign, demo, highscore, porting-m7; 11 display; 12 drawing, shapes, porting-m1; 16 enemy, porting-m6; 14 ffp; 19 frontend, keys, system-font, porting-m3; 7 input, passes, random; 13 map; 18 music, sound, porting-m8; 15 objects, porting-m5; 6 headless, random; 3 porting-m1; 8 porting-m4; 10 amiga-to-web. `page-video.md` is named by no chapter yet (M9's, the shell's picture: chapter 23 by `book/BOOK.md` 3); `testing.md` is named by chapters 6, 9 and 10, and the tests are chapter 24's. In the chapter the words are rounded to the hundred under the header "Words, about" (the notes are corrected at merges), and the subjects are short forms of the titles ("the campaign", "the display", "the enemy", "M4, the world and the player", "a template" and so on).
48. Eighteen notes are of a subsystem of the game; seven are **porting notes** (the term, defined here: a note written for a milestone, what was ported, how it is held, what stands in, each statement marked observed or read), those of M1 and M3 to M8; one, `page-video.md`, is M9's note of the shell's WebGL picture, which ports nothing from the original; one is of an instrument (`headless.md`, M2's note); one of the suite (`testing.md`); one of an idea (`amiga-to-web.md`): 18 + 7 + 1 + 1 + 1 + 1 = 29. Source: the table; `SPEC.md` 9 ("the headless original of M2 ... is in `re/notes/headless.md`"); `re/notes/page-video.md`'s title and summary (a WebGL renderer, the core's interface unchanged). (B1)
49. The porting notes are the long ones: those of M4 to M8 carry their completeness lists and, as appendices, their reach maps; those of M4 to M7 also an appendix of the regions no run executed after the reach map. Source: `grep -n "^## Appendix" re/notes/*.md` (porting-m4 to m7 "Appendix: the reach map" and "Appendix: the regions no run executed", porting-m7 also "part 2's reach map"; porting-m8 "the reach map of the engine" and "of the player"); `grep -n -i "^#.*completeness" re/notes/porting-m*.md` (porting-m4 "### The completeness list", m5, m6, m7 twice, m8); the table's words. (B9, C19)

## 5. ref/

50. `ref/sheets/` holds seven contact sheets of five containers (`8thscale`, `battleship`, `hellcat`, `japplane`, `world`), every shape with its name, made by `tools/ppkc.py --sheets`, versioned and held to their regeneration; two containers, `battleship` and `world`, are laid out twice, on a grid and packed densely, the tallest first. Source: `git ls-files ref`; `tools/ppkc.py` (`SHEETS`, the layouts `grid` and `packed`; `packed_sheet`'s docstring: "The same shapes packed densely: the tallest first, left to right in rows"); `SPEC.md` 2; `tests/test_generated.py`. (C7: the follow-up's "packed as the file holds them" is not what `packed` does)
51. Why they are kept: a reader can browse the artwork without running anything; the look of the front end's screens was checked partly against them by eye, since the headless original draws nothing. Source: `tests/test_generated.py` docstring ("so that a reader can browse the annotated disassembly and the artwork without running anything"); `SPEC.md` 8, row Front end ("The harness draws nothing, so what a screen looks like rests on these calls, on the contact sheets and on the owner's eyes"). (C8)
52. `ref/title.png` is the README's picture (claim 5).

## 6. src/

53. `src/` is the core, the ported game in C; chapter 22 tells its inside. Its 41 files: 35 C files, three headers (`wof.h` the core's interface and shared declarations, `coro.h` the coroutines, `ffp.h` the floating point), and three registries, `globals.def` (every global taken over from the original), `mission.def` (the original's tables of records) and `records.def` (the records' layouts, field by field). Source: `ls src`; each file's first comment line.
54. The files that port the game follow the stretches of related routines that the specification calls the original's modules, their routines in the original's address order, so that a reader can move between the listing and the source. Source: `SPEC.md` 6.1 ("Source files mirror the original's modules in address order so that a reader can move between listing and source"); `src/enemy.c`'s first comment ("the module of compiled C from 0x01D18C to 0x01E8A7 in the original's order"); the first comments of `src/sound.c`, `src/objects.c`, `src/pools.c`, `src/targets.c`, `src/tick.c`, `src/player.c`, `src/mission.c`. Chapter 4 does not use the word "module" (C9 asked for its citation); the chapter cites none. (C9)
55. Every ported routine carries an `orig 0x......` comment naming its address in the listing: the bridge between the two. Source: `CLAUDE.md`, "Rules"; `SPEC.md` 6.1 (the comment's form); `grep -rn "orig 0x01C982" src/` (`src/player.c` line 68, `src/wof.h` line 1098).
56. The C files in four groups, each file's purpose from its first comment line:
    - the core's own frame, which ports nothing: `core.c` (the entry points, the VBlank clock, a pass, the save states), `rand.c` (the entropy stream), `trace.c` (what the port did, recorded for the differential tests);
    - the machine and its system, stood in for: `mem.c` (the static arena replacing exec's `AllocMem`), `fs.c` (the virtual file system and the dos.library calls the loaders make), `gfx.c` (graphics.library on indexed pixels, as far as the front end uses it), `screen.c` (views and viewports), `video.c` (the per-row palettes and the output picture), `audio.c` (Paula's audio side and the mixer), `ffp.c` (Motorola's fast floating point in integer code);
    - the game's own code, ported: `load.c`, `assets.c`, `iff.c`, `shapes.c`, `draw.c` (the blitter library onto indexed pixels), `font.c`, `fade.c`, `front.c`, `dialog.c`, `hiscore.c`, `keys.c`, `input.c`, `mission.c`, `world.c`, `dash.c`, `tick.c`, `player.c`, `objects.c`, `pools.c`, `targets.c`, `enemy.c`, `sound.c`, `music.c`: 23 files;
    - the port's own layers, decided with the owner: `portkeys.c` (the port's keys in front of the key buffer) and `assist.c` (the keyboard assist), each "not a port of anything: it is policy".
    Source: each file's first comment (`head -3`); the grouping is the chapter's, from those comments; counts 3 + 7 + 23 + 2 = 35. `input.c` is in the ported group and named in the chapter as the sampling, a VBlank's raw controller state into a tick's input byte (its first comment: "Input sampling: the raw controller state of one VBlank becomes the input byte of one logic tick"), so that chapter 22's account of `wof_vblank` there does not surprise (the controller's note 8).
57. `src/gen/` holds the tables extracted at every build; it is ignored by version control, so no number of the game is in a committed source. Source: `SPEC.md` 5, step 1 ("`src/gen/` is ignored by version control"); `.gitignore`; chapter 3.
58. Hand-written sources hold code only; tables, texts and tuning values come from the executable at build time. Source: `CLAUDE.md`, "Rules"; `SPEC.md` 1; chapter 3.

## 7. web/

59. `web/` is the shell, plain JavaScript modules and no framework: the template `index.html`, the stylesheet `style.css`, and eight modules: `clock.js`, `core.js` (the WebAssembly core wrapped), `input.js`, `video.js`, `audio.js` and `worklet.js` (the audio, in two), `overlay.js` (the diagnostics overlay), `main.js` (the entry point that wires them). Chapter 23 tells it. Source: `git ls-files web`; each file's first comment; `SPEC.md` 6.2. (C13: the worklet is "the audio in two", no gloss)
60. The modules are real ES modules, which a page opened from a file cannot load as files, so the build joins them into the one page with the core and the game's files. Source: `SPEC.md` 5, step 4.

## 8. tools/

61. `tools/` holds 43 Python tools, the setup script `setup.sh` and the libraries' lists `fd/` (seven lists of library routines, copied unmodified from amitools, and a note of their origin); 52 files. Source: `git ls-files tools`; `tools/fd/ORIGIN.txt` (first lines).
62. The tools by group as the chapter's table gives them, with a few names each: the build (`build.py`, `extract_tables.py`); reading the program (`disasm.py`, `skel.py` and three more: `disasm_player.py`, `m68kdis.py`, `hunk.py`); the oracle (`oracle.py`, `m68k_fix.py`); the headless original (`headless.py` and four more: `headless_os.py`, `headless_dump.py`, `headless_writes.py`, `headless_paula.py`); observing and measuring (`reach_observe.py` and eight more: `pass_observe.py`, `object_observe.py`, `ffp_observe.py`, `ffp_soak.py`, `m5_observe.py`, `m6_observe.py`, `sound_observe.py`, `film_rate.py`); the missions' scripts (an autopilot and its scripts for each of M4 to M7, eight files such as `m4_autopilot.py`, and four more: `m6_runs.py`, `m6_emit.py`, `m7_runs.py`, `m7_controls.py`); the decoders (`ppkc.py`, `map_decode.py` and three more: `rpck.py`, `song_decode.py`, `savegame.py`); the checks (`rom.py`, `mdcheck.py`, `junit_compare.py`). 2 + 5 + 2 + 5 + 9 + 12 + 5 + 3 = 43. Source: each tool's docstring (`ast.get_docstring`); `SPEC.md` 4; `CLAUDE.md`, "Commands". (C30)
63. All run with the project's Python from the repository's root, never the system's. Source: `SPEC.md` 4 ("Run everything with `.venv/bin/python` from the repository root"); `CLAUDE.md`, "Commands".
64. Chapter 25 tells how to run them. Source: `book/BOOK.md` 3, chapter 25.

## 9. tests/

65. `tests/` holds the suite: about 930 tests (`pytest --collect-only -q`: "930 tests collected") in 34 test modules (the count stands in the table, not the prose: C24) with 15 helper modules, run by pytest, and fourteen scripts in Node, which runs JavaScript outside a browser: the drivers of the core and of the two browsers and their instruments; two C files, the run descriptions and a replay. Source: `git ls-files tests`; chapter 10 ("about 930 tests"); Node: the scripts' first comments (`wasm_harness.mjs`: "Runs the WebAssembly core headlessly in Node"). (B12, C13, C24)
66. The test modules by layer, regrouped from their docstrings: a routine under the oracle (`test_oracle_m1.py` and seven more: `_m3` to `_m8`, `_ffp`; 8); the headless original, its instruments and the notes' findings (`test_headless.py`, `test_frontend.py` and five more: `test_passes.py`, `test_objects.py`, `test_map.py`, `test_sound.py`, `test_music.py`; 7); the port against the original (`test_world.py`, `test_enemy.py` and six more: `test_front_port.py`, `test_mission.py`, `test_weapons.py`, `test_campaign.py`, `test_loader.py`, `test_demo.py`; 8); the core's two forms and the instrumentation (`test_core_native.py`, `test_state_m4.py` and three more: `test_core_wasm.py`, `test_replays.py`, `test_isolation.py`; 5); the page (`test_page.py`, `test_firefox.py`, `test_dist.py`; 3); the port's own layer (`test_assist.py`; 1); the repository (`test_generated.py`, `test_rom.py`; 2). 8 + 7 + 8 + 5 + 3 + 1 + 2 = 34. Source: the docstrings (`test_sound.py`: "The headless original's model of Paula ... is held to what it claims"; `test_music.py`: "the instrument is held to what it claims ... and the port's timer and read-back registers to the same definitions"; `test_state_m4.py`: "on the native library and on the WebAssembly core - and the two targets must agree"; `test_isolation.py`: "The test instrumentation's state does not outlive a test"; `test_frontend.py`: "Every finding of re/notes/keys.md, re/notes/frontend.md and re/notes/highscore.md that can be observed is observed here, under the headless original"). Chapter 24 tells the layers. (B3) Whole-book pass: the chapter's table now groups the modules as chapter 24 does, by `book/suite.toml`'s seven layers and their names: one routine (`test_oracle_m1.py` and seven more), the original observed (`test_headless.py`, `test_frontend.py` and five more), the front end (`test_front_port.py`), the missions (`test_world.py`, `test_enemy.py` and five more), the whole game replayed (`test_replays.py`), the core itself (`test_core_native.py`, `test_state_m4.py` and six more: `test_core_wasm.py`, `test_dist.py`, `test_isolation.py`, `test_assist.py`, `test_generated.py`, `test_rom.py`) and the page (`test_page.py`, `test_firefox.py`); Layer (of the suite) linked at the word's first use.
67. The fourteen Node scripts: the drivers of the core (`wasm_harness.mjs`, `replay_wasm.mjs`, `state_wasm.mjs`, `ffp_wasm.mjs`) and of the browsers (`pagecheck.mjs`, `pagecheck_firefox.mjs`, `pagescale.mjs`, `pageframes.mjs`, `pagefullscreen.mjs`, `pageload.mjs`, `chrome.mjs`), and their instruments (`audiowatch.mjs`, `corewatch.mjs`) and shared expressions (`pagemeasure.mjs`). Source: their first comments. (B12)
68. `tests/runs/` holds 34 run descriptions: small JSON files of the player's hands, VBlank by VBlank, with no game data in them, as no hand-written file of the repository has, so that they stand under the code's licence. Source: `git ls-files tests/runs | wc -l`; `tests/test_frontend.py` docstring ("The run descriptions live in tests/runs/ and hold no game data: they are the player's hands, VBlank by VBlank"); `CLAUDE.md`, "Rules" ("Hand-written sources contain code only"); `README.md`, "Licence" (`tests/` under the GPL). (C23)
69. `tests/replays/demo_a.json` is a demo the port recorded, replayed in both forms of the core, native and WebAssembly, by `tests/test_replays.py`. Source: `SPEC.md` 8, row "Whole game, replays"; `git ls-files tests/replays`. (B20)
70. `tests/libwofcore.dylib`, the native library, is built from the same C by `tools/build.py --native` with Apple clang, and is never committed; `tests/shim.c`, the tests' access to the core's internals, is compiled into it and into nothing else: the page never carries it. Source: `SPEC.md` 5 ("A second target builds the same C sources natively with Apple clang ... `tests/libwofcore.dylib`"; "`dist/core.wasm` and `tests/libwofcore.dylib` are not" versioned); `tests/shim.c`'s first comment ("Compiled into tests/libwofcore.dylib and into nothing else: dist/core.wasm never sees it"; "Nothing in src/ may call any of this"); `.gitignore` (`*.dylib`, `*.wasm`).
71. The suite runs serially, or in two phases, the emulator tests first and the page tests after, never beside them. Source: `CLAUDE.md`, "Commands"; `README.md`, "Verify"; `re/notes/testing.md`.

## 10. dist/

72. `dist/wof.html` is the one committed page, about 1.2 MB (1,158,496 bytes); everything else the build writes under `dist/` is ignored. Source: `wc -c dist/wof.html`; `SPEC.md` 5 ("1.16 MB"); `.gitignore` (`dist/*`, `!dist/wof.html`). (B20, C24)
73. A worker never commits it; the controller builds it again at every merge and commits it, so that the committed page is always made from the committed sources; built twice from the same sources it is the same byte for byte and names no directory of the machine that made it. Source: `CLAUDE.md`, "Rules"; `SPEC.md` 2 and 5 ("Two default builds are byte for byte the same"; `-ffile-prefix-map`). (B20)
74. Why it is committed: it is the repository's runnable game, so that a reader plays without building. Source: `.gitignore`'s comment ("the one page, which is the repository's runnable game"); `README.md`, "Play" ("Open `dist/wof.html` ... It runs from the file itself and loads nothing from anywhere").
75. The book's site embeds that same page, copied in at every build, never committed a second time. Source: `book/BOOK.md` 5 (f); `book/hooks/game.py` docstring.

## 11. book/

76. `book/` holds everything of the book and is the site's source, but for the page it embeds, which `book/hooks/game.py` copies in from `dist/wof.html`. The chapter names the handbook `book/BOOK.md`, `book/docs/` (the chapters, the glossary, the hand-drawn diagrams, the two interactive pages) and `book/facts/`, with the rest in one clause (the site's configuration, the generators with their manifests, the pins). Source: `book/BOOK.md` 5, "Everything under `book/`" and (f); `book/hooks/game.py` docstring; `git ls-files book | awk -F/ '{print $2}' | sort | uniq -c`. (B11, C30)
77. The site is Material for MkDocs; `mkdocs build` in `book/` needs only the book's packages, no ROM, no compiler and no browser, because what needs them is generated beforehand and committed. Source: `book/BOOK.md` 5, "Engine" and "Everything under `book/`"; `book/mkdocs.yml`'s opening comment.
78. The generators make the book's listings, figures and the interactive pages' data into `book/docs/generated/` (282 files), and the game's own font as the headings' web font into `book/docs/fonts/wof-newarmy.woff`, all committed. Source: `book/BOOK.md` 5, "The build" (a) to (d); `book/tools/build.py` docstring; `git ls-files book/docs/generated | wc -l`. (B6)
79. `book/tools/build.py --check` makes them all again in a temporary directory and holds the committed files to that regeneration byte for byte; it also compares every colour of the stylesheet and the diagrams with the game's palette entry its comment names, and checks every link into the repository and every glossary line. Source: `book/BOOK.md` 5; `book/tools/build.py` docstring (steps, exit statuses); `README.md`, "The book".
80. The book's packages are pinned whole, the ones they pull in as well, so that every clone and every automatic build installs the same set and the engine stays at MkDocs 1.6.1. Source: `README.md`, "The book" ("so that every clone builds the site with the same set and the engine stays at MkDocs 1.6.1"); `book/requirements.txt`'s comment ("so that a clone and a CI run install the same set"). (C16)
81. The two interactive pages: the shape browser (`book/docs/browser.md` with `book/docs/javascripts/browser.js`) and the map viewer (`book/docs/maps.md` with `book/docs/javascripts/maps.js`); their data is made by `book/tools/elements.py` from the disk's files into `book/docs/generated/browser/` and `book/docs/generated/maps/`; the scripts load nothing from elsewhere and need the site served. Source: `book/BOOK.md` 5, "Interactive elements, first edition" and step (c); `book/mkdocs.yml` (`extra_javascript`).
82. Hand-drawn diagrams are SVG under `book/docs/figures/`, their colours commented with their palette entries. Source: `book/BOOK.md` 5, "Writing a page".
83. `book/site/`, the built site, is never committed; `mkdocs gh-deploy` publishes it. Source: `book/BOOK.md` 5; `.gitignore`.
84. The book's prose is under CC BY-SA 4.0 like the repository's; the figures rendered from the game's data and the listings taken from its executable stand under the same reservation as `original/`. Source: `book/BOOK.md`'s opening paragraph; `README.md`, "Licence".
85. Each chapter written starts as a fact sheet in `book/facts/`, every claim with its source; chapters 22 to 25 are stubs without one. Source: `book/BOOK.md` 6, step 1; chapter 10, "The same method for this book"; `git ls-files book/facts` (01 to 21). (B13)
86. `book/` holds about 380 files at the base, 282 of them generated under `book/docs/generated/`. Source: `git ls-files book | wc -l` = 383; `git ls-files book/docs/generated | wc -l` = 282.

## 12. How the parts hang together

87. Four chains run through the repository, each from a file kept by hand to what is made from it and to what holds what is made; the tools follow each of them. Source: claims 88 to 101; the chapter's own frame (the task's outline).
88. The names chain: a name added to `re/names.txt` is taken by `tools/disasm.py` into the listing and the inventory in about two seconds, and from there into every skeleton `tools/skel.py` prints. Source: `SPEC.md` 4, "Naming workflow" ("The listing, the skeletons and the inventory pick the name up everywhere"); `SPEC.md` 4's table ("about 2 seconds"); chapter 4.
89. The headless original's reports read the names file and the inventory themselves, not the listing: `tools/headless_dump.py` reads `re/names.txt` for data and `re/functions.csv` for code. Source: `tools/headless_dump.py` line 169 ("Addresses to names: re/names.txt for data, re/functions.csv for code"). (B10)
90. The book's listings pick the name up at the next build: an `asm` entry names a routine by its name in the inventory, a `skel` entry runs `tools/skel.py` at build time, and a name that no longer exists fails the build. Source: `book/listings.toml`'s opening comment; `book/tools/listings.py` docstring ("A name that does not exist ... fails the run with the name").
91. The tables chain: an entry of the manifest becomes a table, written as C at every build: `tools/extract_tables.py` reads it from the bytes of the program, the music player or the ROM and turns the byte order around, so that no number of the game is typed again; an address outside the program stops the build. Source: `SPEC.md` 5, step 1; `tools/extract_tables.py` lines 30 to 32; chapter 3. (B4, C25)
92. The book reads the same bytes: `book/tools/elements.py` takes the name lists and the file names (and the mask buffer's size) from the executable through `re/tables.toml` and `tools/extract_tables.py`. The chapter says "its interactive pages take the name lists and file names through the same manifest", Name list linked. Source: `book/tools/elements.py` docstring; `book/BOOK.md` 5 (c). (B19)
93. The comparison chain: a note's claim names the test that shows it; the test names its run descriptions or its oracle cases; a run description replays with one command, `tools/headless.py run`; and a test's name is stable enough that a chapter cites it. Source: claims 94 to 97; `book/docs/part-1/making.md` ("Every statement in the milestones' porting notes says how it is known ... with the tool or the test that shows it"); `SPEC.md` 4 (`tools/headless.py run RUN.json --out A.dump`).
94. Example: `re/notes/keys.md`, under "In flight and paused", says the manual's Control-D is not in the code and names `test_control_d_does_nothing_anywhere`. Source: `re/notes/keys.md` lines 175 to 180, under the heading `### In flight and paused (ingame_keys 0x01CCF6)`.
95. That test, in `tests/test_frontend.py`, runs four pairs of run descriptions, a run with the key and one without, in flight, paused, at the rank selection and in the briefing, and demands the same final state, the same files log and the same schedule. Source: `tests/test_frontend.py` (the `parametrize` list: `flight-control-d`/`flight-no-key`, `paused-control-d`/`paused-no-key`, `rank-control-d`/`rank-no-key`, `briefing-control-d`/`briefing-no-key`; its docstring).
96. `tests/runs/rank-control-d.json`: two presses of fire, the key 34 with Control at the rank selection, the stop at VBlank 110; in listing 4 the key stands on line 11. The key 34 is D's raw code, `0x22`: `web/input.js` line 65 (`KeyD: 0x22`); in decimal because JSON has no hexadecimal (chapter 6). Source: the file (listing 4).
97. Chapter 20 cites the same finding. Source: `book/docs/part-2/quirks.md` line 123 (the manual's row: Control-D, "a test finds the final state, the files and the schedule as without it").
98. The generated-files chain: what a tool makes from other files is committed, so that a reader sees it without the tool, and held byte for byte to what the tool makes again, so that the reader need not trust it. A **generated file** is such a file (the term). Source: `tests/test_generated.py` docstring ("versioned, so that a reader can browse ... without running anything. A committed file that went stale would mislead that reader: each is made again here ... and compared byte for byte"); `CLAUDE.md`, "Rules" ("versioned and held to their regeneration byte for byte by `tests/test_generated.py`").
99. `tests/test_generated.py` holds the listing, the inventory, the player's listing and the contact sheets; none of them needs the ROM. Source: `tests/test_generated.py` (two tests: `test_the_listings_are_their_regeneration`, `test_the_contact_sheets_are_their_regeneration`; docstring "None of them needs the Kickstart ROM"). Listing 5: the first test, lines 26 to 32.
100. `book/tools/build.py --check` holds the book's: the book's listings, the figures, the interactive pages' data, the web font, and the colours. Source: claim 79.
101. No test holds the page byte for byte: building it needs the ROM and a compiler, which a test of the repository cannot assume (the suite skips without the ROM); its rebuilding at every merge holds it, the build being deterministic. Source: `CLAUDE.md`, "Rules" (the ROM; "the controller rebuilds it and commits it at every merge"; "the build is deterministic"); `SPEC.md` 5; `tests/test_generated.py` (`pytestmark = pytest.mark.without_rom`: what it holds needs no ROM). (C18)
102. Figure (a) draws the four chains as lanes, each step a file or a tool by its path; lane 2's input names the manifest and the three files it reads, `original/disk/Wings_of_Fury/Wings`, `original/disk/Wings_of_Fury/songplay` and `original/kick.rom`; the caption names the arrows (solid makes or feeds, dotted names, dashed holds) and says the comparison is a chain of references. Source: claims 88 to 101; `tools/extract_tables.py` lines 30 to 32. (B15, C26)

## 13. Where to start

103. To play: `dist/wof.html` in Chrome, Firefox or Safari, from the file; the keys on its help screen. Source: `README.md`, "Play".
104. To read the code: a file of `src/` with the listing beside it, the `orig` comments as the bridge; `tools/skel.py` for a routine's shape first. Source: claims 54, 55; `SPEC.md` 7.4, step 1.
105. To check a claim: the note, the test it names, the run the test replays. Source: claims 93 to 96.
106. To change something: chapter 25; the setup, the build and the suite in `README.md`. Source: `book/BOOK.md` 3, chapter 25; `README.md`, "Build and verify".
107. To read the history: every change is a commit, 355 at the base, each message opening with a line that says what changed, 183 of them going on with a body of more lines, and every one carrying a line naming the model of the session that made it; the chapter says "a few hundred" and quotes none. Source: `git log --oneline | wc -l` = 355; a count of each message's lines without the co-author line and blank lines (172 of one line, 183 with a body); `git log --format=%B | grep -c "Co-Authored-By"` = 355. (A1)

## 14. What the repository does not hold

108. The Kickstart ROM image: told in the top level and in `original/` (claims 18, 29); the closing section no longer repeats it. (C30)
109. The project's chronicle, its decisions, findings and mistakes dated and sourced, lives outside the repository beside the sessions' transcripts, in the owner's archive; it is this book's source for the order of events. Source: `CONTROLLER.md`, "The user's conventions" ("Times": "The chronicle of the project ... is not published: it lives outside the repository, in the owner's archive folder beside the sessions' transcripts"); `book/BOOK.md` 6 ("the writers' private source for the order of events") and 3 (the chronicle among Part I's freshest sources). (B8)
110. The built site, the native library, the WebAssembly core outside the page, and the generated tables: each is made from what is committed. Source: `.gitignore`; `SPEC.md` 5; `book/BOOK.md` 5.
111. The local environment `.venv/`, made by the setup from the pins. Source: `SPEC.md` 2; `.gitignore`.

## 15. The sidebar, the hand-off

112. *For the developer*: read `re/functions.csv` with a CSV reader, since its strings hold commas, and the listing by an address range or a search, never whole. Source: `book/docs/part-1/reading.md`'s sidebar; `CONTROLLER.md`'s pitfalls ("`cut` on `re/functions.csv` miscounts"); `CLAUDE.md`, "Session protocol". The `grep` line moved to "Where to start" (C28).
113. Chapter 22 opens `src/`: the porting rules, the registered state, the arena, the file system, the interface the shell sees. Source: `book/BOOK.md` 3, chapter 22.

## The figures

| # | File | Kind | What it shows |
|---|---|---|---|
| (a) | `docs/figures/repository-chains.svg` | hand-drawn, new | claim 102: the four chains as lanes, the files and tools by path, generation and holding; viewBox 1000 x 680; lane 2's input the manifest and the three files it reads, spelt out; the style block's header "The design's colours, each an entry of one of the game's palettes" (B15); the rightmost element at x 966, 34 units from the viewBox's right edge, the rule asking a sixth of the longest label (`tools/extract_tables.py`, `tests/test_generated.py`, about 166 units at 12 px: 28); the longest label in the rightmost column, `book/tools/listings.py` and `book/tools/elements.py`, ends at 936.5, 29.5 units inside its box, by Courier New Bold's advance of 0.6 em, which Menlo's 0.602 em matches within a unit; every text's extent measured by the Pillow renderer, none leaving its box |

Tables (b) and (c) are typed into the chapter, counted at the base (claims 23 and 47), not generated: see "Choices".

Existing figures not shown again: chapter 4's `listing-made.svg` (the names chain's first half drawn whole) and `code-map.png`; chapter 3's `disk-files.png`; chapter 10's `arrangement.svg`; the title screens.

## The listings

| # | Kind | Name | Source | Shown before? |
|---|---|---|---|---|
| 1 | text (new kind) | `claude-commands` | `CLAUDE.md`, from `sh tools/setup.sh` to `WOF_FIREFOX_VISIBLE=1` | no |
| 2 | text | `names-start` | `re/names.txt`, from its first line to `close_libraries` | no |
| 3 | text, `head` | `functions-rows` | `re/functions.csv`, its first line and the rows from the address `01c982,` (`record_at`) to `01cb1c,` (`sub_01cb1c`), bounded by addresses so that a name given later changes nothing | no |
| 4 | json | `rank-control-d` | `tests/runs/rank-control-d.json` | no (chapter 6 showed `flight-control-f`) |
| 5 | py | `test_the_listings_are_their_regeneration` | `tests/test_generated.py` | no |

The `text` kind is an extension of `book/tools/listings.py`: a line range of any text file of the repository, named by two texts `from` and `to` as a `py` part is, or the whole file, with `head = true` keeping the file's first line above the part; its first line names the file and the lines in `#` comments; fenced `bash` for the commands (pure shell) and `text` for the rest.

## The terms

| Term | Defined here | Elsewhere | The glossary's computed line |
|---|---|---|---|
| Porting note | claim 48: a note written for a milestone | none | "First met and defined in chapter 21." (chapter 10 says "porting notes" in plain text, unlinked) |
| Generated file | claim 98 | none | "First met and defined in chapter 21." (chapter 10's milestone table says "the generated files" in plain text) |
| Manifest | claim 41 | none | "First met and defined in chapter 21." (chapter 3 says "The manifest" in plain text, unlinked; its link is owed to chapter 3's refinement) |

`README.md` is not a term (the controller's note 2).

Linked, defined earlier: Listing, Routine inventory, Control-flow skeleton, Label (none needed), Disassembler, Oracle, Headless original, Run description, Dump, Observer, Harness, Reach map, Mission script, Autopilot, Stand-in, Verified, Core, Shell, WebAssembly, Native library, Fixture, ADF, Kickstart, Fixed load layout, Contact sheet, Session, Controller, Worker, Handover, Commit, Branch, Review, Milestone, Faithful port, Differential test, Open loop, Closed loop, Quirk. Not defined, glossed: repository (chapter 1 uses it unlinked; an entry would read "first met in chapter 21"), the manifest (chapter 3 explains it unbolded), clone.

## Left to later chapters

The inside of `src/` (chapter 22); the shell's modules at work (chapter 23); the suite's layers, the two phases, what one run of the suite proves (chapter 24); running the tools, the setup, fixing a bug (chapter 25).

## Counts, and where they were counted

| Count | Where, how |
|---|---|
| 719 files; per directory | `git ls-files \| wc -l`; `git ls-files \| awk -F/ '{print (NF>1?$1"/":$1)}' \| sort \| uniq -c` |
| lines per directory | `git ls-files -z DIR \| xargs -0 cat \| wc -l` by extension: src `.c` 17,234, `.h` 1,370, `.def` 832 (19,436); web `.js` 2,193, `.html` 50, `.css` 161 (2,404); tools `.py` 12,317, `setup.sh` 85 (12,402), `fd/` 810 not counted; tests `.py` 18,031, `.mjs` 3,579, `.c` 1,341 (22,951), `.json` 2,188 not counted |
| 901,120; 11,454; 13 pages | `wc -c original/wof.adf original/manual.txt`; `grep -c "^PAGE" original/manual.txt` |
| 76; 65 | `git ls-files original/disk \| wc -l`; `git ls-files original/disk/Wings_of_Fury \| wc -l` |
| 1,627,981 bytes, 32,434 lines | `wc -c -l re/Wings.lst` |
| 935 lines | `wc -l re/songplay.lst` |
| 616 rows, 13 columns; the statuses | `csv.DictReader(open('re/functions.csv'))`; `Counter(r['status'])`: todo 210, verified 167, ported 155, replace 47, drop 36, partial 1; kinds asm 393, C 223; names 445, `sub_` 171 |
| 883 lines, 822 names, 798 addresses | `wc -l re/names.txt`; lines matching `^[0-9a-fA-F]{6}\s`; chapter 4's sheet, claim 40 |
| 5 library bases | `re/libbases.txt`, lines matching `^[0-9a-fA-F]{6}\s` |
| 54 player's names | `re/songplay_names.txt`, lines matching `^[0-9a-fA-F]{4,6}\s` |
| 122 manifest entries | `tomllib.load(open('re/tables.toml','rb'))['table']` |
| 29 notes; 196,970 words; each note | `ls re/notes \| wc -l` (the 29 `.md`; `re/notes/.gitkeep` besides); `cat re/notes/*.md \| wc -w`; `wc -w` each |
| 7 contact sheets, `ref/title.png` | `git ls-files ref` |
| 35 C, 3 headers, 3 registries | `git ls-files src \| sed 's/.*\.//' \| sort \| uniq -c` |
| 8 modules, the template, the stylesheet | `git ls-files web` |
| 43 tools, `setup.sh`, 8 files in `fd/` | `git ls-files tools` |
| 34 test modules, 15 helpers, 14 drivers, 2 C, 36 JSON | `git ls-files tests` |
| 34 run descriptions | `git ls-files tests/runs \| wc -l` |
| 930 tests | `.venv/bin/python -m pytest tests/ --collect-only -q`, its last line "930 tests collected in 0.35s" |
| 1,158,496 bytes | `wc -c dist/wof.html` |
| 383 files of `book/`; 282 generated; 20 fact sheets | `git ls-files book \| wc -l`; `git ls-files book/docs/generated \| wc -l`; `git ls-files book/facts \| wc -l` |
| 355 commits; 355 with a co-author line | `git log --oneline \| wc -l`; `git log --format=%B \| grep -c "Co-Authored-By"` |
| 28 pitfalls | `awk '/^## Pitfalls that cost time/{p=1;next} p&&/^## /{p=0} p&&/^- /' CONTROLLER.md \| wc -l` |
| 926 words | `wc -w CLAUDE.md` |
| 42 of 43 tools with a docstring | `ast.get_docstring` over `git ls-files 'tools/*.py'`; `tools/rpck.py` has none |
| 4,194 words, the chapter after the follow-up (3,787 at the draft) | `wc -w book/docs/part-3/repository.md` |
| 172 one-line messages, 183 with a body | each message of `git log eb4d3f4` without its co-author line and blank lines, counted by lines |
| 290 name-and-address pairs in the notes | `grep -o` of a code span name followed by a code span address in parentheses over `re/notes/*.md`, `wc -l` |
| 7 of `songplay`, 2 of the ROM in the manifest | `tomllib`: entries with `file = "songplay"`; entries without `addr` or `addrs` (`topaz8`, `keymap`) |
| 13 points | `SPEC.md` 10, rows of its table |
| 7 pinned packages; 36 lines of the book's pins | `requirements.txt`; `wc -l book/requirements.txt` |

## Unsourced

- The owner's archive holding the sessions' scratchpads: the repository names the chronicle and the transcripts (`CONTROLLER.md`), not scratchpads. The chapter says "the chronicle and the sessions' transcripts".
- Why the listing and the contact sheets are published although they reproduce the game: the README says they are kept for preservation and covered by neither licence, not why they are versioned rather than generated by the reader; `tests/test_generated.py` gives the reader's browsing as the reason, which the chapter uses.

## Where a source was wrong or silent

- **Chapter 10's status table is stale.** It counts drop 31 and todo 215; since chapter 20's merge (`6f54821`, "five never-called routines drop in re/functions.csv") the inventory holds drop 36 and todo 210. The chapter gives no status count and points to chapter 4 for the meanings; chapter 10's table is for the controller.
- **The headers.** The task's outline says "the two headers"; `src/` has three, `wof.h`, `coro.h` and `ffp.h`. The chapter says three.
- **The port's pins are not whole.** The task asks why both requirements files are pinned whole; `requirements.txt` pins its seven packages but not what they pull in (pytest's `iniconfig`, `packaging`, `pluggy`, `pygments`: `pip show pytest`); only `book/requirements.txt` is pinned whole (`README.md`, "The book"). The chapter says the seven are pinned at exact versions and the book's whole.
- **The scratchpads.** See "Unsourced".
- **Owed by other chapters and files, for the controller** (the follow-up): chapter 10's plain "porting notes" and "the generated files" to become links to their entries at its refinement, which moves the two glossary lines; chapter 3's plain "The manifest" to link Manifest at its refinement, which moves that line; `README.md`'s "Licence" is silent on `CLAUDE.md`, `CONTROLLER.md` and the hand-kept files of `re/` (`re/names.txt`, `re/libbases.txt`, `re/songplay_names.txt`, `re/tables.toml`), so the chapter says what README says and no more; README's "Licence" does not name `tools/fd/`'s GPL v2 lists, which `tools/fd/ORIGIN.txt` does, and the chapter now says they come from amitools under its own licence.
- **The follow-up's C7** says the second layout of the contact sheets is "packed as the file holds them"; `tools/ppkc.py`'s `packed_sheet` packs the shapes densely, the tallest first. The chapter says so (claim 50).
- **The follow-up's C4** says zig's compiler makes "the WebAssembly core and the native library"; the native library is built with Apple clang (`SPEC.md` 5, `README.md`'s prerequisites). The chapter names the WebAssembly core only (claim 19).
- **The follow-up's C9** cites chapter 4 for "the original's modules"; chapter 4 does not use the word; `SPEC.md` 6.1 does, and the chapter says "the specification calls" (claim 54).
- **`page-video.md`** is linked by no chapter yet; its chapter by `book/BOOK.md` 3 is 23 (the shell's picture). **`testing.md`** is linked by chapters 6, 9 and 10, and the tests are chapter 24's. The table gives 23 and 24.
- **The chapter's length.** The task asks 2,800 to 3,800 words; `book/BOOK.md` 4, point 2, says 3,000 to 4,500. The draft keeps both: 3,000 to 3,800.

## The controller's notes on the sheet, folded in

1. Chapter 10's status table is stale (drop 31, todo 215); the controller corrects it at the merge. The chapter points to chapter 4 for the meanings and to chapter 10 for the counts, and gives none.
2. README is no bold term and no glossary entry: `README.md` is linked and glossed in one clause, "by convention the file a reader of a repository opens first", with no Elsewhere line. Two terms are defined, Porting note and Generated file; the check computed "First met and defined in chapter 21." for both.
3. The `text` kind is kept small: the whole file, or a part from the first line holding `from` to the first at or after it holding `to`; `head` for the file's first line above a part; a `#` line naming the file and the lines. Fenced `bash` for `CLAUDE.md`'s commands, `text` for the names and the inventory.
4. The directory table gives every cell of its size column a unit: the image 901,120 bytes; the listing 1,627,981 bytes and the notes about 197,000 words; 8 pictures; the lines rounded as chapter 10 rounds them; 1,158,496 bytes; "about 380" files for `book/`.
5. The notes' words: "about 197,000"; chapter 10's "about 196,000" stays, a count of its base.
6. The commit history is described, never quoted: "each message a line saying what changed and naming the session's model".
7. The files left out: "leaves out ten: the program ... and nine files that are not the game's", as chapter 3 counts them (claim 27).
8. `input.c` is named in the ported group as the sampling; `core.c`, `rand.c` and `trace.c` are the frame (claim 56).
9. The requirements: the port's seven pinned exactly, the book's whole (claims 19, 80).
10. The chronicle: "in the owner's archive beside the sessions' transcripts", no path (claim 109).
11. Figure (a): solid arrows for making, dotted for naming, dashed for holding; every path as the repository spells it; no count; the rightmost box ends at x 966 in a viewBox 1000 wide, the longest label (`tools/extract_tables.py`, `tests/test_generated.py`, about 166 units at 12 px) needing 28 of slack; the text extents measured by a renderer of Pillow, none leaving its box.
12. This section; the sheet brought to the draft below; the draft between 3,000 and 3,800 words.

## Draft

`book/docs/part-3/repository.md`, 3,787 words by `wc -w` at the draft, 4,194 after the follow-up. The order: the opening; the top level (`README.md`, `SPEC.md` with its ten sections as a table, `CLAUDE.md` with its commands as listing 1, `CONTROLLER.md`, the two licences, the pins and `.gitignore`); the directories as a table; `original/`; `re/` (the listing, the names as listing 2, the library bases, the inventory as listing 3, the manifest and the player's listing, the notes with their table); `ref/`; `src/` with its four groups as a table; `web/`; `tools/` with its eight groups as a table; `tests/` with its seven layers as a table; `dist/`; `book/`; the four chains, each under its own heading, figure (a), listing 4 in the comparison, listing 5 in the generated files; where to start; what the repository leaves out; the sidebar; what comes next; further reading.

Claims made while drafting that the sheet above did not hold, each with its source:

114. The specification is corrected wherever it turned out wrong, so that it says what is. Source: `CLAUDE.md`, "Session protocol" ("End: ... `SPEC.md` corrected wherever it stated something that turned out different").
115. `CLAUDE.md` is short because every session pays to read it. Source: `book/docs/part-1/making.md`, "Two models, one worker at a time" ("every agent pays again to read the rules and the notes"); claim 10 (926 words).
116. The commands block shows how many commands make something again or check it rather than build it: of the fifteen, nine (the ROM check, the disassembler making the listing again, the oracle's self-test, the Markdown check, the suite serially and in its two phases, the comparison of two runs, the visible Firefox run); three build (the setup, the two builds); three read or run the original (the skeleton, the headless original, the reach map). Source: listing 1 (`CLAUDE.md` lines 10 to 24).
117. The project's Python is always `.venv`'s, so that every machine uses the same pinned packages. Source: `CLAUDE.md`, "Commands" ("Always use the project environment, never the system Python"); `SPEC.md` 2.
118. The port's packages are pinned so that a later clone runs what the tests ran: the instruments rest on one version of the emulator, whose fault the project corrects for that version. Source: `book/docs/part-1/oracle.md` ("Unicorn is a package pinned at one version, so the correction lives not in a patched emulator but in the repository"); `SPEC.md` 2 and 8 ("Unicorn 2.1.4 executes a memory-form shift ...").
119. `CONTROLLER.md`'s last section is "Pitfalls that cost time"; chapter 10 told the arrangement, what a task contains and how a report is reviewed. Source: `grep -n "^#" CONTROLLER.md`; `book/docs/part-1/making.md`, "The rules, and what each answers" and "A task and a review".
120. The rules forbid changing `original/` so that every claim is checked against the same bytes. Source: `CLAUDE.md`, "Rules" ("`original/` is read-only ground truth"); `SPEC.md` 2 ("read-only ground truth"); the reason is the word "ground truth".
121. The ROM is the Amiga's own system, sold under licence. Source: `README.md`, "The Kickstart ROM" ("Cloanto's Amiga Forever sells this image"); `book/docs/glossary.md`, Kickstart ("The heart of AmigaOS, in the ROM").
122. Without the ROM the build stops and the suite skips, each saying where to get it. Source: `README.md`, "Build" ("Without the ROM it stops with a message that says what is needed and where to get it"); `CLAUDE.md`, "Rules" ("each with the same message").
123. The inventory's row: `a5_args` holds the offsets of the arguments above A5 (8 for `record_at`'s one argument; `8 10` for `flash_set`'s two); `callers` and `globals` hold counts; `calls` and `os_calls` the names. Source: listing 3; chapter 3 (the first argument at `8(a5)`).
124. The registries tie each variable, table and record to the original's addresses and offsets, by which the tests copy state between the original and the port and compare it. Source: `src/globals.def`'s first comment ("uses the original addresses to copy state between the oracle and the port"); `src/records.def`'s ("field by field, with the offset and the width the original uses"; "copy a record between the original's big-endian bytes and the port's struct"); `src/mission.def`'s; `SPEC.md` 8 ("every registered global and table").
125. All but one of the 43 tools open with a sentence saying what they are for; `tools/rpck.py` opens with its imports. Source: `ast.get_docstring` over `tools/*.py` (counts table: 42 with a docstring).
126. The decoders serve the tools, the tests and this book; the core uses the game's own loaders, ported. Source: `book/docs/part-1/disk.md`, "The little there was to decode" ("For the core the port wrote no decoders: it ported the original's loaders"; "Decoders in Python under `tools/` serve the tools, the tests and this book's figures").
127. The tests' modules by layer, as the table counts them: the oracle's eight as "`test_oracle_m1.py`, six more by milestone, one for the floating point"; the headless original's five; the eleven whole runs; the core's builds four; the page three; the assist one; the repository two. Source: claim 66. Whole-book pass: superseded by claim 66's note, the grouping of `book/suite.toml`.
128. A page opened from a file cannot load modules one by one, so the build joins them. Source: `SPEC.md` 5, step 4 (claim 60).
129. A test's name says what it holds, so that a chapter can cite it by name. Source: `tests/test_frontend.py` (`test_control_d_does_nothing_anywhere`); `book/listings.toml` (the book's `py` listings name tests by their names, and a name that no longer exists fails the build: claim 90).
130. `tools/headless.py run tests/runs/rank-control-d.json --out A.dump` runs the run under the headless original; the test compares the pair's final state, files log and schedule, not a dump: a dump records the steps of a mission, and the rank run stops at VBlank 110 before any. Source: `re/notes/headless.md`, "Using it" and "Dump"; `tools/headless_dump.py` docstring; `tests/test_frontend.py` (`test_control_d_does_nothing_anywhere`: `regions()`, `files_log`, `schedule`). (B2)
131. Figure (a)'s caption: the four chains, from what is kept by hand to what is made from it and what holds what is made; the comparison a chain of references instead; solid arrows make or feed, dotted arrows name, dashed arrows hold, byte for byte. The alternative text: four lanes, one chain each. Source: claims 88 to 102. (C14, C26)

Claims made in the follow-up that the sheet did not hold, each with its source:

132. The rule of the handover shapes the layout: the names in a file rather than a session's memory, the status column carried over by the tool, the notes where the next session starts, the generated files committed and checked, each so that nothing lives only in a conversation; the same rule lets the sessions' transcripts stay out, since what the next reader needs is in the repository. Source: `CLAUDE.md`, "Session protocol" ("The repository is the handover: nothing may live only in a conversation"; "End: names into `re/names.txt`, findings into `re/notes/`, `status` in `re/functions.csv`") and "Rules"; `SPEC.md` 7.4 (the status carried over); `tests/test_generated.py`; `CONTROLLER.md`, "The user's conventions" (the chronicle beside the transcripts, not published); `book/BOOK.md` 6. (C20)
133. The address keeps the hand-written places in step when a name changes: it never changes, the `orig` comment carries it, and the notes name a routine by its name and its address; only the generated places follow a rename by themselves. Source: `CLAUDE.md`, "Rules" (the `orig 0x......` comment; the fixed load layout); `SPEC.md` 4, "Naming workflow"; the notes' habit, `grep -o` of a name followed by its address in parentheses over `re/notes/*.md`: 290 such pairs (`map_load` (`0x012ADC`) in `re/notes/map.md`, for one). (C21)
134. `record_at` along the names chain: its line in `re/names.txt` (line 784, `01c982 record_at` and a comment); its row in the inventory (listing 3, its second line); its port in `src/player.c` (line 68, `/* orig 0x01C982 - the map record under a world x ...`); `test_the_map_helpers_match_the_original` in `tests/test_oracle_m4.py`, parametrized over maps a, c, h, m and o, holding `record_at` (`0x01C982`) at every world x a record starts at; chapter 3's listing pair of it (`book/docs/part-1/disk.md`, `asm/record_at` beside `c/wof_record_at`, "The oracle holds the two to each other on five maps"). (C29)
135. The tables are a build product, made again at every build and kept out so that the port's sources hold code only; the listing is the reading itself, committed so that a reader can browse it without the tools. Source: `SPEC.md` 5, step 1 ("`src/gen/` is ignored by version control"); `CLAUDE.md`, "Rules" ("Hand-written sources contain code only"); `tests/test_generated.py`'s docstring (the reader's browsing). (C17)
136. The eight top-level files are named in the paragraphs that follow the sentence "the files are the place to start": `README.md`, `SPEC.md`, `CLAUDE.md`, `CONTROLLER.md`, `LICENSE`, `LICENSE-CC-BY-SA-4.0`, `requirements.txt`, `.gitignore`. Source: claim 21. (C1)
137. The project's Python is that of `.venv`, the environment the setup makes from the pins. Source: `SPEC.md` 2 ("`.venv` is made by `tools/setup.sh` from `requirements.txt`"); `CLAUDE.md`, "Commands". (C3)
138. The colour check compares every colour of the site's stylesheet and of the hand-drawn diagrams, each commented with the palette entry of the game it was taken from, with that entry. Source: `book/tools/build.py`'s docstring ("colours  every colour of docs/stylesheets/book.css and of the diagrams docs/figures/*.svg against the palette entry its comment names"); `book/BOOK.md` 5 (e). (C12)
139. Node runs JavaScript outside a browser. Source: `README.md`, "Prerequisites" ("For the tests only: Node"); `tests/wasm_harness.mjs`'s first comment ("Runs the WebAssembly core headlessly in Node"); `https://nodejs.org/`, fetched once: "a free, open-source, cross-platform JavaScript runtime environment". **(reference)** (C13)
140. "Where to start" gives the `grep` for an `orig` address under "To read the code" and adds "To learn how a part of the game works": the notes' table's chapter column, then the note. Source: claims 47, 55. (C28)
141. The repository holds everything the port is made of but the one file the reader brings, the ROM image. Source: claims 18, 29. (B17)
142. Terms linked at their first use in the chapter: Native library (the title picture), Handover (`CLAUDE.md`'s rule), Kickstart (the licences), Disassembler and Manifest (`re/`), Milestone and Reach map (the notes), VBlank (`input.c`'s row), Oracle and Autopilot (the tools' table), Worker (`dist/`), Name list (the game's tables), Commit (the history). Source: `book/docs/glossary.md`. (B19)
143. "The code excerpts this book shows, its listings" stands once, in the names chain, and "the book's listings" after; the tables chain's heading is "The game's tables"; the C tables are "written as C at every build". Source: `book/BOOK.md` 5 (the listings extracted from the real sources). (C25)
144. `core.c`, `rand.c` and `trace.c` are "the port's own scaffolding, a port of nothing". Source: their first comments (claim 56). (C10)
145. The test of the generated files makes the files in a temporary directory, `tmp_path`, and compares their bytes with the committed ones. Source: listing 5 (`generate(tmp_path, ...)`, `read_bytes() == ... read_bytes()`). (C27)

## The follow-up, folded in

The fact-check, the readability read and the controller's read, in one message; done in one pass, the chapter at 4,194 words by `wc -w` (the cap 4,200). Each point and what was done:

- **A1** The history: "each opening with a line that says what changed, many going on to say how, and every one naming the model of the session that made it" (claim 107; 172 of one line, 183 with a body, counted again).
- **B1** Seven porting notes; `page-video.md` its own clause, "the shell's picture, M9's"; the entry's definition kept (claim 48).
- **B2** "runs it under the headless original; the test compares the pair's final state, files log and schedule"; no dump named (claim 130).
- **B3** The tests table regrouped from the docstrings: the headless original, its instruments and the notes' findings with `test_sound.py` and `test_music.py`; the core's two forms and the instrumentation with `test_state_m4.py` and `test_isolation.py` (claim 66).
- **B4** "out of the program, the music player and the ROM" in the manifest's sentence and the tables chain; the figure's lane 2 names the three files (claims 41, 91, 102).
- **B5** The size cells labelled by what they count; "written by hand" dropped (claim 23).
- **B6** The web font in `book/docs/fonts/`, beside the generated files (claim 78).
- **B7** "the ROM image is in no file of the repository; the two small tables the build reads from it, the font and the key conversion, travel inside the page (chapter 3)" (claim 18).
- **B8** "it is this book's source for the order of events", "only" gone (claim 109).
- **B9** "those of M4 to M8 carry their completeness lists and, as appendices, their reach maps" (claim 49).
- **B10** "the headless original's reports read the names file and the inventory themselves" (claim 89).
- **B11** "the site's source, but for the page it embeds" (claim 76).
- **B12** "fourteen scripts in Node ...: the drivers of the core and of the two browsers, and their instruments" (claims 65, 67).
- **B13** "a fact sheet for each chapter written" (claim 85).
- **B14** The amitools clause; "the program's and the music player's code"; README's silence on the handbooks and `re/`'s hand-kept files noted for the owner, the chapter saying no more than README (claims 15, 17; "Where a source was wrong or silent").
- **B15** The figure: `original/disk/Wings_of_Fury/` with `Wings` and `songplay` under it and `original/kick.rom`, spelt out; the style comment "The design's colours, each an entry of one of the game's palettes"; the slack stated (34 to the viewBox's edge) and the longest label re-measured inside its box (29.5 units, Courier New Bold's metrics; Menlo's within a unit) (claim 102, the figures table).
- **B16** The row's columns named with `os_calls` and the two counts (claim 36).
- **B17** "all but the one file the reader brings" (claim 141).
- **B18** The glossary lines left as the check computes them: "First met and defined in chapter 21." for Porting note, Generated file and Manifest (the terms table).
- **B19** Ten terms linked at their first use, and Native library and Reach map besides (claim 142).
- **B20** "The disassembler, started once"; "the same pass of the tool"; "carries it over every time"; "the one committed page"; "both forms of the core, native and WebAssembly"; "always made from the committed sources"; "Built twice from the same sources".
- **C1** "nine directories and eight files; the files are the place to start", the eight named in the paragraphs that follow (claim 136).
- **C2** "rendered by the port's native library (chapter 5)" (claim 5).
- **C3** "from the environment `.venv` that the setup makes from the pins" (claim 137).
- **C4** zig's half sentence, naming the WebAssembly core only: the native library is Apple clang's (claim 19; "Where a source was wrong or silent").
- **C5** "the ROM image" (claim 29).
- **C6** The statuses as the inventory holds them, in chapter 4's and chapter 10's words (claim 38).
- **C7** "two containers are laid out twice, on a grid and packed densely, the tallest first", as `tools/ppkc.py` packs them, not "as the file holds them" (claim 50).
- **C8** "the look of the front end's screens was checked partly against them by eye" (claim 51).
- **C9** "the stretches of related routines the specification calls the original's modules"; chapter 4 does not use the word (claim 54).
- **C10** "the port's own scaffolding, a port of nothing" (claim 144).
- **C11** "the music player's listing" in the generated files; the player's own listing named so in `re/`.
- **C12** The colour check said whose colours (claim 138).
- **C13** Node glossed; "scripts", not "drivers"; the worklet as "the audio in two" (claims 59, 139).
- **C14** "Four lanes, one chain each" (claim 131).
- **C15** "beside the disk image, where the build and the tools look for it" (claim 29).
- **C16** The book's pins with README's reason in the `book/` paragraph; nothing beyond README said of the port's (claims 19, 80).
- **C17** One sentence in the game's tables (claim 135).
- **C18** "No test holds the page byte for byte, since building it needs the ROM and a compiler, which a test of the repository cannot assume; its rebuilding at every merge holds it" (claim 101).
- **C19** "They are the long ones, since those of M4 to M8 carry their completeness lists and, as appendices, their reach maps (chapter 8)"; the controls are only `porting-m7.md`'s ("Part 2: the controls"), so not named (claim 49).
- **C20** Two sentences opening "What the repository leaves out" (claim 132).
- **C21** The address as the key (claim 133).
- **C22** "and so are this book's figures of the game and its excerpts of the game's code" (claim 17).
- **C23** "as no file written by hand has, so that they stand under the code's licence" (claim 68).
- **C24** The bytes rounded (about 880 KB, 1.6 MB, 1.2 MB); `original/`'s 76 and 65 left to chapter 3; the module count out of the tests' prose; "about 197,000" once, in the table (claims 23, 25, 44, 65).
- **C25** The excerpts named once; "written as C at every build"; the heading "The game's tables" (claim 143).
- **C26** The caption names the arrows and the comparison's references (claim 131).
- **C27** "look at where it makes the files, a temporary directory, and at the byte comparison with the committed ones" (claim 145).
- **C28** The `grep` line in "To read the code"; "To learn how a part of the game works" added; the sidebar keeps the CSV reader and the listing (claims 112, 140).
- **C29** The `record_at` walk, four clauses (claim 134).
- **C30** The tools' rows to a group and two or three names; the tests' rows to one or two and "N more"; the `book/` paragraph to the handbook, `docs/` and `facts/` with the rest in a clause; "All but one open with a sentence" out; `.gitignore` a clause; besides, the opening's last sentence, the ROM's repetition in the closing section, the GPL and CC links of the further reading (the licences are linked as files) and the sidebar's `git ls-files` and `skel.py` lines.
- **C31** Manifest defined in bold at `re/tables.toml`, with its entry; the check computed "First met and defined in chapter 21."; Fact sheet and Suite glossed.

