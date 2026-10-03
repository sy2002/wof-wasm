# Fact sheet: chapter 21, A tour of the repository

Every claim the chapter makes, one line each, with its source, in the order of the chapter. A claim without a source goes to the list at the end and stays out of the draft. A general fact that the repository does not state is sourced in a reference work and marked **(reference)**; what the repository holds always comes from its own files, counted at the branch's base. No "How we know" box and no "What went wrong" box (`book/BOOK.md` 4, point 6); the one sidebar is *For the developer*.

Counts are of the branch's base, `eb4d3f4`, counted in the files named, with the command in the counts table at the end. No run of the port, no headless original, no test run (one `pytest --collect-only -q`), no browser, no rebuild.

Words used in the sheet as the chapter will use them, each in one sense. The **repository** is the project's files with their history, as a clone holds them; a file is *in the repository* when `git ls-files` lists it. A **note** is a file of `re/notes/`, never a remark. **The listing** is `re/Wings.lst`; the extracts this book shows are **the book's listings**, never "listings" alone. **The page** is `dist/wof.html`; a page of the book or of the manual is named so. A **run** is a run description of `tests/runs/` or what the headless original does with it; a run of the suite is "a run of the suite". A **contact sheet** is a picture of `ref/sheets/`; a **fact sheet** is a file of `book/facts/`; "sheet" alone is not used in the chapter. A **chain** is one of the chapter's four ways the parts hang together (the names, the tables, the comparison, the generated files); the word needs no entry. A **generated file** is the chapter's term (claim 98); a **porting note** too (claim 56); **README** (claim 4).

The reference works:

- Wikipedia, "README", `https://en.wikipedia.org/wiki/README`, fetched once: a README file holds descriptive information about the contents of the directory it lies in, typically at the top level of a project, the entry point for a reader. For the glossary entry's Elsewhere line. **(reference)**
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

4. `README.md` is the door, written for a reader who has just cloned: what the port is, how to play, build and verify, the ROM, the book, where things are, the idea of a template, the licence. Source: `SPEC.md` 2 (`README.md  for a reader who has just cloned: play, build, verify, the ROM, where things are, the licence`); `README.md`'s headings: Play; Build and verify (Prerequisites, The Kickstart ROM, Build, Verify); The book; Where things are; Amiga to Web; Licence. The term README (claim 4) with the reference above.
5. Its picture is the title screen rendered by the port's own library in the PAL aspect, `ref/title.png`. Source: `README.md` (`![](ref/title.png)`); commit `7a159ba`'s subject ("the title screen, rendered by the port's own library in the PAL aspect").
6. `SPEC.md` is the source of truth for goals, architecture, porting rules and milestones, written for an engineer, human or AI agent, working in the repository with its tools. Source: `CLAUDE.md` ("Read `SPEC.md` first; it is the source of truth for goals, architecture, porting rules and milestones"); `SPEC.md`'s opening line ("Target reader: an engineer (human or AI agent) working in this repository with the tools it already contains").
7. Its ten sections, one line each: 1 the goal, with the definition of faithful and what is out of scope; 2 the repository's layout and the pinned packages; 3 the original program (the disk, the executable, the runtime model, the system and hardware it uses, the file formats); 4 the tools, the listing's conventions, the naming workflow, the oracle's use; 5 the build; 6 the architecture (the core, the shell, the coroutines, the video and audio models, what is not ported); 7 the porting rules (arithmetic, data, determinism, the working method); 8 the verification, level by level; 9 the milestones, M0 to M10, each with its deliverable and acceptance; 10 the thirteen points to establish, each answered in a note. Source: `SPEC.md`'s headings (`grep -n "^#" SPEC.md`); section 10's table (13 rows).
8. Section 1 defines faithful in three parts: the same game state after every logic tick for the same seed and input bytes; the same indexed pixels and palette for the same state; the same sound sample started on the same channel at the same tick with the same period and volume, and the music on the original player's timing. Chapter 1 told it. Source: `SPEC.md` 1, "Definition of faithful"; `book/docs/part-1/faithful.md`.
9. Section 6.6 names what is not ported (the C runtime's start-up, the system's glue, the memory management, the copper's construction, the interrupt plumbing, Workbench, the debug and crash reporters, the protection check, the crack screen), marked `replace` or `drop` in the inventory. Source: `SPEC.md` 6.6.
10. `CLAUDE.md` is the working rules every session reads: the commands, the session protocol, the rules; it is short (926 words). Source: `CLAUDE.md`'s headings ("Commands", "Session protocol", "Rules"); `SPEC.md` 2 ("short working rules for agent sessions"); `wc -w CLAUDE.md`.
11. Its commands block, lines 10 to 24 of `CLAUDE.md`, fifteen commands, from the setup of a fresh clone to the visible Firefox run: the ROM check, the disassembler, the skeleton, the oracle's self-test, the headless original, the reach map, the Markdown check, the two builds, the suite serially and in its two phases, the comparison of two runs' outcomes. Source: `CLAUDE.md` lines 9 to 25 (`grep -n "" CLAUDE.md`). Listing 1.
12. The rule the repository rests on: the repository is the handover, and nothing may live only in a conversation; a session starts from `SPEC.md` and the notes and ends by writing back names, findings, statuses and corrections. Source: `CLAUDE.md`, "Session protocol" ("The repository is the handover: nothing may live only in a conversation"; "Start", "End"); `book/docs/part-1/making.md`, "Who we were".
13. `CONTROLLER.md` is the handbook of the session that leads, published as it was used; chapter 10 told the arrangement. Its sections: The arrangement; The user's conventions; Driving workers; What a task contains; Reviewing a report; Asking the user; Models and effort; The plan ahead; Open items; Pitfalls that cost time. Source: `grep -n "^#" CONTROLLER.md`; `book/docs/part-1/making.md` ("The sessions' handbook, `CONTROLLER.md`, is published as it was used"); `CLAUDE.md` ("The session that leads the project, the controller, also reads `CONTROLLER.md`; workers do not need it").
14. "Pitfalls that cost time" is a list of warnings, each a lesson that cost time once: 28 at the base. Source: `CONTROLLER.md` (`awk` count of its bullets, counts table). The chapter gives no count.
15. Two licences: `LICENSE` is the GNU General Public License, version 3 or later, for the code and the tools (`src/`, `web/`, `tools/`, `tests/`, the build); `LICENSE-CC-BY-SA-4.0` is Creative Commons Attribution-ShareAlike 4.0 International, for the prose (`SPEC.md`, the notes, the book). Source: `README.md`, "Licence"; `SPEC.md` 1 and 2; `head -3 LICENSE`, `head -1 LICENSE-CC-BY-SA-4.0`.
16. Both are copyleft: a changed version passes on under the same terms. Source: the references (GPL, CC BY-SA). **(reference)**
17. The game data is under neither: everything under `original/`, the listings `re/Wings.lst` and `re/songplay.lst`, which reproduce the executable's code, the contact sheets of `ref/sheets/`, and the game data in `dist/wof.html`; it is the work of its authors and publisher, kept for preservation, and no right to it is granted. Source: `README.md`, "Licence".
18. The ROM is in no file of the repository. Source: `README.md`, "Licence" ("The Kickstart ROM is not in the repository at all"); `.gitignore` (`original/kick.rom`).
19. `requirements.txt` pins the port's seven Python packages at exact versions: capstone 5.0.9, numpy 2.4.6, pillow 12.3.0, pytest 9.1.1, pytest-xdist 3.8.0, unicorn 2.1.4, ziglang 0.16.0; `tools/setup.sh` installs them into `.venv`. Source: `requirements.txt`; `SPEC.md` 2.
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

Source: the counts table. In the chapter: files exact but `book/` ("about 380"); lines "about 19,400", "about 2,400", "about 12,400", "about 23,000" (chapter 10's figures box rounds the same four the same way); the listing "1.6 MB" (chapter 10) and its 32,434 lines (chapter 4); the page "1.16 MB" (`SPEC.md` 5).

## 3. original/

24. `original/` is the ground truth and read-only: nothing in it is ever modified, moved or deleted. Source: `CLAUDE.md`, "Rules"; `SPEC.md` 2 ("the disk image (read-only ground truth)").
25. It holds the disk image `original/wof.adf`, 901,120 bytes (880 KB); the disk's files extracted verbatim with xdftool under `original/disk/`, 76 files, 65 of them in the game's directory `Wings_of_Fury`; and the manual as text, `original/manual.txt`, 13 pages. Source: `SPEC.md` 2; `wc -c`; `git ls-files original/disk | wc -l`; `git ls-files original/disk/Wings_of_Fury | wc -l`; `grep -c "^PAGE" original/manual.txt`; chapter 3 (65 files).
26. Why the files beside the image: the port and the tools read the extracted files; the image is read for the directory's order alone. Source: `book/docs/part-1/disk.md`, "An image of the floppy".
27. The build packs 55 of the files into the page; it leaves out the program `Wings`, `UFXintro`, `wingt`, every `.info` file and every dotfile; the program's tables are read from it at build time. Source: `SPEC.md` 5, step 2; chapter 3.
28. The manual is read for the intended behaviour and the key commands, cited by page, never pasted into sources, notes or documents. Source: `CLAUDE.md`, "Rules"; `SPEC.md` 2 ("never quoted at length").
29. The ROM, `original/kick.rom`, is placed by whoever clones: Kickstart 1.3, revision 34.5, the A500 and A2000 image, 262,144 bytes; `tools/rom.py` checks it by its SHA-1; without it the build stops and the suite skips, each with one message. Source: `CLAUDE.md`, "Rules"; `README.md`, "The Kickstart ROM".
30. What the ROM gives: the system font topaz 8, the key conversion with the default keymap, and mathffp, the reference of the game's floating point. Source: `SPEC.md` 2 (`original/kick.rom` line); `README.md`, "The Kickstart ROM".

## 4. re/

31. `re/` holds the reading of the program: what the project has learnt of it, as generated files and hand-kept files side by side. Source: `README.md`, "Where things are" ("the annotated disassembly ..., the names, the function inventory, and the notes on every subsystem"); `SPEC.md` 2.
32. The listing `re/Wings.lst`: the program as annotated assembly, generated by `tools/disasm.py`, about 1.6 MB, 32,434 lines; versioned and held to its regeneration by `tests/test_generated.py`; never edited by hand and never loaded whole by a session. Source: `SPEC.md` 2; `CLAUDE.md` ("Never edit `re/Wings.lst` by hand"; "Never load `re/Wings.lst` whole. It is about 1.6 MB"); `wc -c -l`; chapter 4.
33. The names live in `re/names.txt`, kept by hand, one line a name: a hexadecimal address, a name, and after a semicolon a comment; its first line says so and that `tools/disasm.py` reads it. Source: `re/names.txt` line 1; `SPEC.md` 2 ("hand-maintained names for code and data addresses"); chapter 4. Listing 2.
34. Why apart: the listing is made again whenever a name changes or the tool learns something, so a name typed into the listing would be lost at the next run. Source: `book/docs/part-1/reading.md`, "Names"; `SPEC.md` 4, "Naming workflow".
35. `re/names.txt` has 883 lines and 822 name lines, naming 798 addresses (chapter 4's count). Source: `wc -l`; chapter 4's sheet, claim 40 (`book/facts/04-reading.md`). The chapter gives no count but links chapter 4.
36. The inventory `re/functions.csv`: a row for each of the 616 routines and thirteen columns, `addr`, `name`, `kind`, `span`, `frame`, `a5_args`, `far_slot`, `callers`, `calls`, `os_calls`, `globals`, `strings`, `status`; generated with the listing; `callers` and `globals` hold counts. Source: `csv.DictReader` (counts table); chapter 4; the rows of listing 3 (`callers` 9 for `record_at`, `globals` 2).
37. The status column is the one kept by hand, carried over at every regeneration; all other columns are recomputed. Source: `SPEC.md` 7.4 (closing paragraph); `CLAUDE.md`, "Rules".
38. The status counts at the base: verified 167, ported 155, partial 1, replace 47, drop 36, todo 210. Source: `collections.Counter` over the `status` column (counts table). The chapter names no count: chapter 4 tells what each status means and chapter 10 counts them (see "Where a source was wrong or silent": chapter 10's table predates five routines moved from `todo` to `drop`).
39. Listing 3 shows the column names and eight rows, `record_at` to `sub_01cb1c`: compiled and hand-written routines, statuses `verified`, `ported` and `todo`, a far-call slot, arguments at `8(a5)`. Source: `re/functions.csv` lines 1 and 338 to 345.
40. `re/libbases.txt`, kept by hand, names the five variables that hold a library's base (exec, intuition, graphics, dos, mathffp). Source: `re/libbases.txt` (5 entries); `SPEC.md` 2; chapter 4.
41. The manifest `re/tables.toml`, 122 entries: what the build reads out of the program and the ROM (chapter 3). Source: `tomllib` (`len(t['table'])` = 122); chapter 3 (113 from `Wings`, 7 from the player, 2 from the ROM).
42. The music player has a listing of its own, `re/songplay.lst` (935 lines), generated by `tools/disasm_player.py` from `songplay`'s hunks, with its names in `re/songplay_names.txt` (54 names), at addresses of its own layout. Source: `SPEC.md` 2; `re/songplay_names.txt`'s opening comment; `wc -l`; the regex count (counts table); `tools/disasm_player.py` docstring.
43. After a change to `re/names.txt`, `re/libbases.txt` or `re/songplay_names.txt`, the two disassemblers are run and what they write is committed. Source: `CLAUDE.md`, "Rules".
44. `re/notes/` holds 29 notes, one Markdown file a subject, about 197,000 words in all (chapter 10: "29, about 196,000 words"); the later sessions start from them instead of deriving again. Source: `ls re/notes | wc -l`; `cat re/notes/*.md | wc -w` = 196,970; `SPEC.md` 2 ("one Markdown note per understood subsystem"); `SPEC.md` 7.4, step 6; `CLAUDE.md` ("When a subsystem is understood, write it down in `re/notes/` so that later sessions do not re-derive it").
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

Source: each note's first line (`head -1`) and `wc -w`; the chapters' further reading (`awk '/^## Further reading/' ... | grep -o "repo:re/notes/..."`): chapter 17 names campaign, demo, highscore, porting-m7; 11 display; 12 drawing, shapes, porting-m1; 16 enemy, porting-m6; 14 ffp; 19 frontend, keys, system-font, porting-m3; 7 input, passes, random; 13 map; 18 music, sound, porting-m8; 15 objects, porting-m5; 6 headless, random; 3 porting-m1; 8 porting-m4; 10 amiga-to-web. `page-video.md` is named by no chapter yet (M9's, the shell's picture: chapter 23 by `book/BOOK.md` 3); `testing.md` is named by chapters 6, 9 and 10, and the tests are chapter 24's. In the chapter the words are rounded to the hundred under the header "Words, about" (the notes are corrected at merges); the titles of the M1, M3 and M6 notes shortened as above.
48. Eighteen notes are of a subsystem of the game, eight of a milestone (M1, M3 to M8, and M9's `page-video.md`), one of an instrument (`headless.md`, which is M2's note), one of the suite (`testing.md`), one of an idea (`amiga-to-web.md`). Source: the table; `SPEC.md` 9 ("the headless original of M2, how to run it and what it does not cover, is in `re/notes/headless.md`"); `re/notes/page-video.md`'s title.
49. The porting notes of M4 to M8 each end with an appendix, the reach map, and those of M4 to M7 with the regions no run executed. Source: `grep -n "^## Appendix" re/notes/*.md` (porting-m4 to m7 "Appendix: the reach map"; porting-m8 "the reach map of the engine" and "of the player"; porting-m4 to m7 "Appendix: the regions no run executed").

## 5. ref/

50. `ref/sheets/` holds seven contact sheets, pictures of the shapes of five containers (`8thscale`, `battleship`, `hellcat`, `japplane`, `world`, two of them also packed), made by `tools/ppkc.py --sheets`, versioned and held to their regeneration. Source: `git ls-files ref`; `tools/ppkc.py` docstring; `SPEC.md` 2; `tests/test_generated.py`.
51. Why they are kept: a reader can browse the artwork without running anything; the front end's comparisons rest partly on them. Source: `tests/test_generated.py` docstring ("so that a reader can browse the annotated disassembly and the artwork without running anything"); `SPEC.md` 8, row Front end ("what a screen looks like rests on these calls, on the contact sheets and on the owner's eyes").
52. `ref/title.png` is the README's picture (claim 5).

## 6. src/

53. `src/` is the core, the ported game in C; chapter 22 tells its inside. Its 41 files: 35 C files, three headers (`wof.h` the core's interface and shared declarations, `coro.h` the coroutines, `ffp.h` the floating point), and three registries, `globals.def` (every global taken over from the original), `mission.def` (the original's tables of records) and `records.def` (the records' layouts, field by field). Source: `ls src`; each file's first comment line.
54. The files that port the game mirror the original's modules, and their routines stand in the original's address order, so that a reader can move between the listing and the source. Source: `SPEC.md` 6.1 ("Source files mirror the original's modules in address order so that a reader can move between listing and source"); the first comments of `src/enemy.c`, `src/sound.c`, `src/objects.c`, `src/pools.c`, `src/targets.c`, `src/tick.c`, `src/player.c`, `src/mission.c` ("in the original's order", "in the original's address order").
55. Every ported routine carries an `orig 0x......` comment naming its address in the listing: the bridge between the two. Source: `CLAUDE.md`, "Rules"; `SPEC.md` 6.1 (the comment's form); `grep -rn "orig 0x01C982" src/` (`src/player.c` line 68, `src/wof.h` line 1098).
56. The C files in four groups, each file's purpose from its first comment line:
    - the core's own frame, which ports nothing: `core.c` (the entry points, the VBlank clock, a pass, the save states), `rand.c` (the entropy stream), `trace.c` (what the port did, recorded for the differential tests);
    - the machine and its system, stood in for: `mem.c` (the static arena replacing exec's `AllocMem`), `fs.c` (the virtual file system and the dos.library calls the loaders make), `gfx.c` (graphics.library on indexed pixels, as far as the front end uses it), `screen.c` (views and viewports), `video.c` (the per-row palettes and the output picture), `audio.c` (Paula's audio side and the mixer), `ffp.c` (Motorola's fast floating point in integer code);
    - the game's own code, ported: `load.c`, `assets.c`, `iff.c`, `shapes.c`, `draw.c` (the blitter library onto indexed pixels), `font.c`, `fade.c`, `front.c`, `dialog.c`, `hiscore.c`, `keys.c`, `input.c`, `mission.c`, `world.c`, `dash.c`, `tick.c`, `player.c`, `objects.c`, `pools.c`, `targets.c`, `enemy.c`, `sound.c`, `music.c`: 23 files;
    - the port's own layers, decided with the owner: `portkeys.c` (the port's keys in front of the key buffer) and `assist.c` (the keyboard assist), each "not a port of anything: it is policy".
    Source: each file's first comment (`head -3`); the grouping is the chapter's, from those comments; counts 3 + 7 + 23 + 2 = 35.
57. `src/gen/` holds the tables extracted at every build; it is ignored by version control, so no number of the game is in a committed source. Source: `SPEC.md` 5, step 1 ("`src/gen/` is ignored by version control"); `.gitignore`; chapter 3.
58. Hand-written sources hold code only; tables, texts and tuning values come from the executable at build time. Source: `CLAUDE.md`, "Rules"; `SPEC.md` 1; chapter 3.

## 7. web/

59. `web/` is the shell, plain JavaScript modules and no framework: the template `index.html`, the stylesheet `style.css`, and eight modules: `clock.js` (a fixed-rate clock on the browser's animation frames), `core.js` (the WebAssembly core wrapped), `input.js` (the keyboard and a gamepad into the controller's state), `video.js` (indexed pixels through the per-row palettes, the scaling), `audio.js` and `worklet.js` (the core's sound into the browser's audio), `overlay.js` (the diagnostics overlay), `main.js` (the entry point that wires them). Chapter 23 tells it. Source: `git ls-files web`; each file's first comment; `SPEC.md` 6.2 ("Plain JavaScript modules, no framework, no bundler other than the build script").
60. The modules are real ES modules, which a page opened from a file cannot load as files, so the build joins them into the one page with the core and the game's files. Source: `SPEC.md` 5, step 4.

## 8. tools/

61. `tools/` holds 43 Python tools, the setup script `setup.sh` and the libraries' lists `fd/` (seven lists of library routines, copied unmodified from amitools, and a note of their origin); 52 files. Source: `git ls-files tools`; `tools/fd/ORIGIN.txt` (first lines).
62. The tools by group, each tool's purpose from its first docstring line:
    - the build: `build.py` (the page, `--native` the test library), `extract_tables.py` (the manifest's tables), and `setup.sh` (a clone set up; with `--book` the book too);
    - reading the program: `disasm.py` (the listing and the inventory), `disasm_player.py` (the player's listing), `skel.py` (a skeleton), `m68kdis.py` (an address range decoded straight through), `hunk.py` (the hunk loader at the fixed bases);
    - the oracle: `oracle.py` (routines of the original under Unicorn) and `m68k_fix.py` (the emulator's fault and its correction);
    - the headless original: `headless.py`, with `headless_os.py` (the operating system, one method a library call), `headless_dump.py` (the dumps), `headless_writes.py` (what a run wrote and read), `headless_paula.py` (Paula's audio side);
    - the observers and measurements: `pass_observe.py`, `object_observe.py`, `reach_observe.py`, `ffp_observe.py`, `ffp_soak.py`, `m5_observe.py`, `m6_observe.py`, `sound_observe.py`, `film_rate.py`;
    - the mission scripts and their autopilots, milestone by milestone: `m4_autopilot.py`, `m4_scripts.py`, `m5_autopilot.py`, `m5_scripts.py`, `m6_autopilot.py`, `m6_scripts.py`, `m6_runs.py`, `m6_emit.py`, `m7_autopilot.py`, `m7_scripts.py`, `m7_runs.py`, `m7_controls.py`; `m6_runs.py` and `m7_runs.py` hold the schedules the autopilots flew, written by `m6_emit.py` and `m7_autopilot.py --all`;
    - the decoders of the formats: `rpck.py`, `ppkc.py` (with the contact sheets), `map_decode.py`, `song_decode.py`, `savegame.py`;
    - the checks: `rom.py` (the ROM), `mdcheck.py` (the Markdown), `junit_compare.py` (two runs of the suite compared by their outcomes).
    Source: each tool's docstring (`ast.get_docstring`, first paragraph); `tools/rpck.py` has none and is "reference decoders" with `ppkc.py` in `SPEC.md` 4; the groups follow `SPEC.md` 4's table and `CLAUDE.md`'s commands; counts 2 + 5 + 2 + 5 + 9 + 12 + 5 + 3 = 43.
63. All run with the project's Python from the repository's root, never the system's. Source: `SPEC.md` 4 ("Run everything with `.venv/bin/python` from the repository root"); `CLAUDE.md`, "Commands".
64. Chapter 25 tells how to run them. Source: `book/BOOK.md` 3, chapter 25.

## 9. tests/

65. `tests/` holds the suite: 34 test modules and 15 helper modules in Python, 14 drivers in Node (`.mjs`), two C files, the run descriptions and a replay; `pytest --collect-only -q` collects 930 tests at the base. Source: `git ls-files tests`; `.venv/bin/python -m pytest tests/ --collect-only -q` ("930 tests collected"); chapter 10 ("about 930 tests").
66. The test modules by layer, each from its first docstring line:
    - the oracle's: `test_oracle_m1.py`, `_m3`, `_m4`, `_m5`, `_m6`, `_m7`, `_m8`, `test_oracle_ffp.py` (8);
    - the headless original and what it observes: `test_headless.py`, `test_passes.py`, `test_objects.py`, `test_map.py`, `test_frontend.py` (5);
    - the port against the headless original, whole runs: `test_front_port.py`, `test_world.py`, `test_mission.py`, `test_state_m4.py`, `test_weapons.py`, `test_enemy.py`, `test_campaign.py`, `test_loader.py`, `test_demo.py`, `test_sound.py`, `test_music.py` (11);
    - the core's two builds and the instrumentation: `test_core_native.py`, `test_core_wasm.py`, `test_replays.py`, `test_isolation.py` (4);
    - the page: `test_page.py` (Chrome), `test_firefox.py`, `test_dist.py` (one file, no network, under the size limit) (3);
    - the port's own layer: `test_assist.py` (1);
    - the repository itself: `test_generated.py` (the generated files) and `test_rom.py` (the ROM check) (2).
    Source: first docstring lines; the grouping is the chapter's; 8 + 5 + 11 + 4 + 3 + 1 + 2 = 34. Chapter 24 tells the layers.
67. The Node drivers run the core in Node's WebAssembly and the page in the browsers: `wasm_harness.mjs`, `replay_wasm.mjs`, `state_wasm.mjs`, `ffp_wasm.mjs`, `pagecheck.mjs` (Chrome), `pagecheck_firefox.mjs`, `pagescale.mjs`, `pageframes.mjs`, `pagefullscreen.mjs`, `pageload.mjs`, `pagemeasure.mjs`, `chrome.mjs`, `audiowatch.mjs`, `corewatch.mjs`. Source: their first comments.
68. `tests/runs/` holds 34 run descriptions: small JSON files of the player's hands, VBlank by VBlank, that hold no game data; most are the key runs of the front end and the flight (chapter 6). Source: `git ls-files tests/runs | wc -l`; `tests/test_frontend.py` docstring ("The run descriptions live in tests/runs/ and hold no game data: they are the player's hands, VBlank by VBlank"); chapter 6.
69. `tests/replays/demo_a.json` is a demo the port recorded, with the schedule of its playback and the state's hash after every input sample, replayed in the native core and in Node's WebAssembly by `tests/test_replays.py`. Source: `SPEC.md` 8, row "Whole game, replays"; `git ls-files tests/replays`.
70. `tests/libwofcore.dylib`, the native library, is built from the same C by `tools/build.py --native` with Apple clang, and is never committed; `tests/shim.c`, the tests' access to the core's internals, is compiled into it and into nothing else: the page never carries it. Source: `SPEC.md` 5 ("A second target builds the same C sources natively with Apple clang ... `tests/libwofcore.dylib`"; "`dist/core.wasm` and `tests/libwofcore.dylib` are not" versioned); `tests/shim.c`'s first comment ("Compiled into tests/libwofcore.dylib and into nothing else: dist/core.wasm never sees it"; "Nothing in src/ may call any of this"); `.gitignore` (`*.dylib`, `*.wasm`).
71. The suite runs serially, or in two phases, the emulator tests first and the page tests after, never beside them. Source: `CLAUDE.md`, "Commands"; `README.md`, "Verify"; `re/notes/testing.md`.

## 10. dist/

72. `dist/wof.html` is the one committed build: the page, 1,158,496 bytes, about 1.16 MB; everything else the build writes under `dist/` is ignored. Source: `wc -c dist/wof.html`; `SPEC.md` 5 ("1.16 MB"); `.gitignore` (`dist/*`, `!dist/wof.html`).
73. A worker never commits it; the controller rebuilds and commits it at every merge, so that the committed page is always the build of the committed sources; the build is deterministic and names no directory of the machine that built it. Source: `CLAUDE.md`, "Rules"; `SPEC.md` 2 and 5 ("Two default builds are byte for byte the same"; `-ffile-prefix-map`).
74. Why it is committed: it is the repository's runnable game, so that a reader plays without building. Source: `.gitignore`'s comment ("the one page, which is the repository's runnable game"); `README.md`, "Play" ("Open `dist/wof.html` ... It runs from the file itself and loads nothing from anywhere").
75. The book's site embeds that same page, copied in at every build, never committed a second time. Source: `book/BOOK.md` 5 (f); `book/hooks/game.py` docstring.

## 11. book/

76. `book/` holds everything of the book and nothing of it lives elsewhere: the handbook `book/BOOK.md`, the site's configuration `book/mkdocs.yml` and pages under `book/docs/`, the generators under `book/tools/`, the hooks under `book/hooks/`, the manifests `book/listings.toml` and `book/figures.toml`, the pinned packages `book/requirements.txt`, and the fact sheets under `book/facts/`. Source: `book/BOOK.md` 5, "Everything under `book/`"; `SPEC.md` 2; `git ls-files book | awk -F/ '{print $2}' | sort | uniq -c` (counts table).
77. The site is Material for MkDocs; `mkdocs build` in `book/` needs only the book's packages, no ROM, no compiler and no browser, because what needs them is generated beforehand and committed. Source: `book/BOOK.md` 5, "Engine" and "Everything under `book/`"; `book/mkdocs.yml`'s opening comment.
78. The generators make the book's listings from the real sources, the figures through the native library and the tools, the data of the two interactive pages from the disk's files, and the game's own font as the headings' web font, all into `book/docs/generated/` and `book/docs/fonts/`, committed. Source: `book/BOOK.md` 5, "The build" (a) to (d); `book/tools/build.py` docstring.
79. `book/tools/build.py --check` makes them all again in a temporary directory and holds the committed files to that regeneration byte for byte; it also compares every colour of the stylesheet and the diagrams with the game's palette entry its comment names, and checks every link into the repository and every glossary line. Source: `book/BOOK.md` 5; `book/tools/build.py` docstring (steps, exit statuses); `README.md`, "The book".
80. The book's packages are pinned whole, the ones they pull in as well, so that every clone builds the site with the same set and the engine stays at MkDocs 1.6.1. Source: `README.md`, "The book"; `book/requirements.txt` (its comments: "The packages these pull in, pinned too").
81. The two interactive pages: the shape browser (`book/docs/browser.md` with `book/docs/javascripts/browser.js`) and the map viewer (`book/docs/maps.md` with `book/docs/javascripts/maps.js`); their data is made by `book/tools/elements.py` from the disk's files into `book/docs/generated/browser/` and `book/docs/generated/maps/`; the scripts load nothing from elsewhere and need the site served. Source: `book/BOOK.md` 5, "Interactive elements, first edition" and step (c); `book/mkdocs.yml` (`extra_javascript`).
82. Hand-drawn diagrams are SVG under `book/docs/figures/`, their colours commented with their palette entries. Source: `book/BOOK.md` 5, "Writing a page".
83. `book/site/`, the built site, is never committed; `mkdocs gh-deploy` publishes it. Source: `book/BOOK.md` 5; `.gitignore`.
84. The book's prose is under CC BY-SA 4.0 like the repository's; the figures rendered from the game's data and the listings taken from its executable stand under the same reservation as `original/`. Source: `book/BOOK.md`'s opening paragraph; `README.md`, "Licence".
85. Each chapter starts as a fact sheet in `book/facts/`, every claim with its source; the fact sheets are committed with the chapters. Source: `book/BOOK.md` 6, step 1; chapter 10, "The same method for this book".
86. `book/` holds about 380 files at the base, 282 of them generated under `book/docs/generated/`. Source: `git ls-files book | wc -l` = 383; `git ls-files book/docs/generated | wc -l` = 282.

## 12. How the parts hang together

87. Four chains run through the repository, each from a file kept by hand to what is made from it and to what holds what is made; the tools follow each of them. Source: claims 88 to 101; the chapter's own frame (the task's outline).
88. The names chain: a name added to `re/names.txt` is taken by `tools/disasm.py` into the listing and the inventory in about two seconds, and from there into every skeleton `tools/skel.py` prints. Source: `SPEC.md` 4, "Naming workflow" ("The listing, the skeletons and the inventory pick the name up everywhere"); `SPEC.md` 4's table ("about 2 seconds"); chapter 4.
89. The headless original's reports read the same names. Source: `book/docs/part-1/reading.md`, "Names" ("the reports of the headless original read the same file"); `tools/headless_dump.py` docstring ("names for addresses").
90. The book's listings pick the name up at the next build: an `asm` entry names a routine by its name in the inventory, a `skel` entry runs `tools/skel.py` at build time, and a name that no longer exists fails the build. Source: `book/listings.toml`'s opening comment; `book/tools/listings.py` docstring ("A name that does not exist ... fails the run with the name").
91. The tables chain: an entry of the manifest `re/tables.toml` becomes a table in `src/gen/` at every build, read by `tools/extract_tables.py` from the program's bytes with the byte order converted, so that no number of the game is typed again; `src/gen/` is never committed. Source: `SPEC.md` 5, step 1; chapter 3.
92. The book reads the same bytes: `book/tools/elements.py` takes the name lists, the file names and the mask buffer's size from the executable through `re/tables.toml` and `tools/extract_tables.py`, and `book/tools/figures.py` reads a name list at the address the manifest gives. Source: `book/tools/elements.py` docstring; `book/tools/figures.py` (the function at line 406, "A name list of the executable, read from it at the address re/tables.toml gives"); `book/BOOK.md` 5 (c).
93. The comparison chain: a note's claim names the test that shows it; the test names its run descriptions or its oracle cases; a run description replays with one command, `tools/headless.py run`; and a test's name is stable enough that a chapter cites it. Source: claims 94 to 97; `book/docs/part-1/making.md` ("Every statement in the milestones' porting notes says how it is known ... with the tool or the test that shows it"); `SPEC.md` 4 (`tools/headless.py run RUN.json --out A.dump`).
94. Example: `re/notes/keys.md`, under "In flight and paused", says the manual's Control-D is not in the code and names `test_control_d_does_nothing_anywhere`. Source: `re/notes/keys.md` lines 175 to 180, under the heading `### In flight and paused (ingame_keys 0x01CCF6)`.
95. That test, in `tests/test_frontend.py`, runs four pairs of run descriptions, a run with the key and one without, in flight, paused, at the rank selection and in the briefing, and demands the same final state, the same files log and the same schedule. Source: `tests/test_frontend.py` (the `parametrize` list: `flight-control-d`/`flight-no-key`, `paused-control-d`/`paused-no-key`, `rank-control-d`/`rank-no-key`, `briefing-control-d`/`briefing-no-key`; its docstring).
96. `tests/runs/rank-control-d.json`: two presses of fire, the key 34 with Control at the rank selection, the stop at VBlank 110. Source: the file (listing 4, the `json` kind). The key 34 is D's raw code, `0x22`: `web/input.js` line 65 (`KeyD: 0x22`); in decimal because JSON has no hexadecimal (chapter 6).
97. Chapter 20 cites the same finding. Source: `book/docs/part-2/quirks.md` line 123 (the manual's row: Control-D, "a test finds the final state, the files and the schedule as without it").
98. The generated-files chain: what a tool makes from other files is committed, so that a reader sees it without the tool, and held byte for byte to what the tool makes again, so that the reader need not trust it. A **generated file** is such a file (the term). Source: `tests/test_generated.py` docstring ("versioned, so that a reader can browse ... without running anything. A committed file that went stale would mislead that reader: each is made again here ... and compared byte for byte"); `CLAUDE.md`, "Rules" ("versioned and held to their regeneration byte for byte by `tests/test_generated.py`").
99. `tests/test_generated.py` holds the listing, the inventory, the player's listing and the contact sheets; none of them needs the ROM. Source: `tests/test_generated.py` (two tests: `test_the_listings_are_their_regeneration`, `test_the_contact_sheets_are_their_regeneration`; docstring "None of them needs the Kickstart ROM"). Listing 5: the first test, lines 26 to 32.
100. `book/tools/build.py --check` holds the book's: the book's listings, the figures, the interactive pages' data, the web font, and the colours. Source: claim 79.
101. The page is held differently: it is rebuilt at every merge from the committed sources, and two builds are byte for byte the same. Source: claim 73.
102. Figure (a) draws the four chains as lanes, each step a file or a tool named by its path. Source: claims 88 to 101.

## 13. Where to start

103. To play: `dist/wof.html` in Chrome, Firefox or Safari, from the file; the keys on its help screen. Source: `README.md`, "Play".
104. To read the code: a file of `src/` with the listing beside it, the `orig` comments as the bridge; `tools/skel.py` for a routine's shape first. Source: claims 54, 55; `SPEC.md` 7.4, step 1.
105. To check a claim: the note, the test it names, the run the test replays. Source: claims 93 to 96.
106. To change something: chapter 25; the setup, the build and the suite in `README.md`. Source: `book/BOOK.md` 3, chapter 25; `README.md`, "Build and verify".
107. To read the history: every change is a commit, 355 at the base, each message a line saying what changed and naming the model of the session that made it. Source: `git log --oneline | wc -l` = 355; `git log --format=%B | grep -c "Co-Authored-By"` = 355 (counts table). The chapter says "a few hundred" and no quotation.

## 14. What the repository does not hold

108. The Kickstart ROM: licensed, placed by whoever clones (claim 29). Source: `README.md`, "The Kickstart ROM" and "Licence".
109. The project's chronicle, its decisions, findings and mistakes dated and sourced, lives outside the repository beside the sessions' transcripts, in the owner's archive. Source: `CONTROLLER.md`, "The user's conventions" ("Times": "The chronicle of the project ... is not published: it lives outside the repository, in the owner's archive folder beside the sessions' transcripts"); `book/BOOK.md` 6 ("the project's chronicle, kept outside the repository").
110. The built site, the native library, the WebAssembly core outside the page, and the generated tables: each is made from what is committed. Source: `.gitignore`; `SPEC.md` 5; `book/BOOK.md` 5.
111. The local environment `.venv/`, made by the setup from the pins. Source: `SPEC.md` 2; `.gitignore`.

## 15. The sidebar, the hand-off

112. *For the developer*: `git ls-files` lists what the repository holds; `grep -rn "orig 0x01C982" src/` finds the port of a routine by its address (`src/player.c`); `tools/skel.py record_at` prints its skeleton by name; `grep -n "^PAGE" original/manual.txt` finds the manual's pages; the listing is read by address range or search, never whole. Source: claim 55; `CLAUDE.md`, "Commands" and "Session protocol"; `book/BOOK.md` 4, point 7.
113. Chapter 22 opens `src/`: the porting rules, the registered state, the arena, the file system, the interface the shell sees. Source: `book/BOOK.md` 3, chapter 22.

## The figures

| # | File | Kind | What it shows |
|---|---|---|---|
| (a) | `docs/figures/repository-chains.svg` | hand-drawn, new | claim 102: the four chains as lanes, the files and tools by path, generation and holding |

Tables (b) and (c) are typed into the chapter, counted at the base (claims 23 and 47), not generated: see "Choices".

Existing figures not shown again: chapter 4's `listing-made.svg` (the names chain's first half drawn whole) and `code-map.png`; chapter 3's `disk-files.png`; chapter 10's `arrangement.svg`; the title screens.

## The listings

| # | Kind | Name | Source | Shown before? |
|---|---|---|---|---|
| 1 | text (new kind) | `claude-commands` | `CLAUDE.md`, from `sh tools/setup.sh` to `WOF_FIREFOX_VISIBLE=1` | no |
| 2 | text | `names-start` | `re/names.txt`, from its first line to `close_libraries` | no |
| 3 | text, `head` | `functions-rows` | `re/functions.csv`, its first line and the rows `record_at` to `sub_01cb1c` | no |
| 4 | json | `rank-control-d` | `tests/runs/rank-control-d.json` | no (chapter 6 showed `flight-control-f`) |
| 5 | py | `test_the_listings_are_their_regeneration` | `tests/test_generated.py` | no |

The `text` kind is an extension of `book/tools/listings.py`: a line range of any text file of the repository, named by two texts `from` and `to` as a `py` part is, or the whole file, with `head = true` keeping the file's first line above the part; its first line names the file and the lines in `#` comments; fenced `bash` for the commands (pure shell) and `text` for the rest.

## The terms

| Term | Defined here | Elsewhere |
|---|---|---|
| README | claim 4 | Wikipedia, "README" |
| Porting note | claim 47/48: a note written for a milestone | none |
| Generated file | claim 98 | none |

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
- **`page-video.md`** is linked by no chapter yet; its chapter by `book/BOOK.md` 3 is 23 (the shell's picture). **`testing.md`** is linked by chapters 6, 9 and 10, and the tests are chapter 24's. The table gives 23 and 24.
- **The chapter's length.** The task asks 2,800 to 3,800 words; `book/BOOK.md` 4, point 2, says 3,000 to 4,500. The draft keeps both: 3,000 to 3,800.
