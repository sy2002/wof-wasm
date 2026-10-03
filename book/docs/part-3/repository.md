Chapter 21
{ .chapter-kicker }

# A tour of the repository

Everything the port is made of lies in one repository: the project's files with the whole history of their changes, which anyone can copy, or clone, with git. By the end of this chapter you will know where each kind of thing lives, from the rules and the original to the port, its instruments and this book, and why it lives there. You will know the four chains that tie the parts together, where to start for what you want, and what the repository leaves out on purpose. Earlier chapters told how each part works; this one says where it is.

## The top level

A clone opens on nine directories and eight files, which are read first.

[`README.md`](repo:README.md), by convention the file a reader of a repository opens first, is the door: what the port is, how to play it, how to build and verify it, where the book is, where things are, the idea of a template the method could become, and the licence. Its picture, [`ref/title.png`](repo:ref/title.png), is the title screen rendered by the port's own library.

[`SPEC.md`](repo:SPEC.md), the specification, is the source of truth for the goals, the architecture, the porting rules and the milestones. Written for an engineer, human or AI, it is corrected wherever it turned out wrong, so that it says what is, not what was planned. Its first section holds the three-part definition of faithful that chapter 1 told: the same game state after every tick, the same pixels and palette, the same sound samples started at the same moments.

| Section | What it holds |
|---|---|
| [1, Goal](repo:SPEC.md#1-goal) | the one HTML file, what faithful means, what is out of scope |
| [2, Repository](repo:SPEC.md#2-repository) | the layout this chapter walks, the pinned packages |
| [3, The original program](repo:SPEC.md#3-the-original-program) | the disk, the executable, how it runs, the formats |
| [4, Tools](repo:SPEC.md#4-tools) | the tools, the listing's conventions, how a name is added |
| [5, Build](repo:SPEC.md#5-build) | the steps from the manifest to the page |
| [6, Architecture](repo:SPEC.md#6-architecture) | the core, the shell, the models of picture and sound, what is not ported |
| [7, Porting rules](repo:SPEC.md#7-porting-rules) | the arithmetic, the data, determinism, the working method |
| [8, Verification](repo:SPEC.md#8-verification) | each level of comparison and its method |
| [9, Milestones](repo:SPEC.md#9-milestones) | M0 to M10, each deliverable and its acceptance |
| [10, Points to establish](repo:SPEC.md#10-points-to-establish) | thirteen questions, each answered in a note |

[`CLAUDE.md`](repo:CLAUDE.md) holds the working rules every [session](../glossary.md#session) reads when it starts: the commands, the session protocol and the rules. It is short, under a thousand words, because every session pays to read it. Its protocol rests on the rule the whole layout serves: the repository is the handover, and nothing may live only in a conversation (chapter 10). Here are the commands; look at how many of them make something again or check it, rather than build it:

```bash
--8<-- "generated/listings/text/claude-commands.txt"
```

The Python is always the project's own, so that every machine uses the same pinned packages.

[`CONTROLLER.md`](repo:CONTROLLER.md) is the handbook of the [controller](../glossary.md#controller), the session that leads, published as it was used; chapter 10 told the arrangement, [what a task contains](repo:CONTROLLER.md#what-a-task-contains) and how [a report is reviewed](repo:CONTROLLER.md#reviewing-a-report). Its last section, [the pitfalls that cost time](repo:CONTROLLER.md#pitfalls-that-cost-time), is a list of warnings, each a lesson paid for once.

Two licences divide the rest. [`LICENSE`](repo:LICENSE), the GNU General Public License, version 3 or later, covers the code and the tools; [`LICENSE-CC-BY-SA-4.0`](repo:LICENSE-CC-BY-SA-4.0), Creative Commons Attribution-ShareAlike 4.0, covers the prose: the specification, the notes and this book. Both let anyone use and change what they cover, as long as a changed version is passed on under the same terms. The game is under neither: the disk, its files, the manual's text, the two listings that reproduce the program's code, the contact sheets and the game inside the page are its authors' and publisher's, kept for preservation, no right granted. The Kickstart ROM is in no file at all.

[`requirements.txt`](repo:requirements.txt) pins the port's seven Python packages to exact versions, the emulator Unicorn, the disassembly library Capstone, pytest and the compiler zig among them, so that a later clone runs what the tests ran. [`.gitignore`](repo:.gitignore) names what never enters, from the ROM to the book's built site.

## The directories at a glance

| Directory | Files | What it holds | Size |
|---|---|---|---|
| [`original/`](repo:original/) | 78 | the disk image, its files, the manual | the image 901,120 bytes |
| [`re/`](repo:re/) | 37 | the listing, the names, the inventory, the manifest, the notes | the listing 1,627,981 bytes; the notes about 197,000 words |
| [`ref/`](repo:ref/) | 8 | contact sheets, the title picture | 8 pictures |
| [`src/`](repo:src/) | 41 | the core, in C | about 19,400 lines |
| [`web/`](repo:web/) | 10 | the shell, in JavaScript | about 2,400 lines |
| [`tools/`](repo:tools/) | 52 | the instruments, in Python | about 12,400 lines |
| [`tests/`](repo:tests/) | 101 | the suite | about 23,000 lines |
| [`dist/`](repo:dist/) | 1 | the page | 1,158,496 bytes |
| [`book/`](repo:book/) | about 380 | this book | grows with each chapter |

The files are what `git ls-files` lists; the lines are those of code written by hand.

## original/: the ground truth

[`original/`](repo:original/) holds what the port is held to, and the rules forbid modifying, moving or deleting anything in it, so that every claim is checked against the same bytes. It holds the disk image [`original/wof.adf`](repo:original/wof.adf), the disk's 76 files extracted byte for byte under [`original/disk/`](repo:original/disk/), 65 of them in the game's own directory, and the manual as text, [`original/manual.txt`](repo:original/manual.txt). The tools read the extracted files; the image is read only for the order in which the disk lists a directory (chapter 3). The build packs 55 of the files into the page and leaves out ten: the program, whose tables it reads instead, and nine files that are not the game's. The manual, which says what the game is meant to do, is cited by its page numbers and never copied.

One file belongs here and is not in the repository: the Kickstart 1.3 ROM, which whoever clones places as `kick.rom` in [`original/`](repo:original/). It is the Amiga's own system, sold under licence, and the project takes three things from it: the system font, the keyboard's conversion of a key into a character, and the floating point the flight model is held to. [`tools/rom.py`](repo:tools/rom.py) checks the image by its checksum; without it the build stops and the suite skips, each saying where to get it.

## re/: the reading

[`re/`](repo:re/) holds what the project learnt by reading the program: files a tool makes, beside the files kept by hand they are made from.

The [listing](../glossary.md#listing), [`re/Wings.lst`](repo:re/Wings.lst), the program as annotated assembly, has 32,434 lines (chapter 4). [`tools/disasm.py`](repo:tools/disasm.py) makes it, and nobody edits it: it is made again whenever a name changes, and a name typed into it would be gone at the next run. So the names live apart, in [`re/names.txt`](repo:re/names.txt), one a line: an address in hexadecimal, a name and, after a semicolon, a comment. Here are its first lines:

```text
--8<-- "generated/listings/text/names-start.txt"
```

[`re/libbases.txt`](repo:re/libbases.txt), also kept by hand, names the five variables that hold a library's address, by which the tool names the system's calls.

The same run writes the [routine inventory](../glossary.md#routine-inventory), [`re/functions.csv`](repo:re/functions.csv), a row for each of the program's 616 routines. Here are its column names and eight rows from `record_at` on:

```text
--8<-- "generated/listings/text/functions-rows.txt"
```

A row gives a routine's address, name and kind, its size, frame and arguments, its far-call slot, its callers, calls and variables, its strings and its status. The status is the one column kept by hand; the tool carries it over at every run and works out the rest again. Chapter 4 tells what each status means, chapter 10 counts them; what the specification leaves out on purpose, such as the system's glue and the crack's screen, is `replace` or `drop`.

Beside them lie the manifest [`re/tables.toml`](repo:re/tables.toml), the 122 entries the build reads out of the program and the ROM (chapter 3), and the music player's own listing, [`re/songplay.lst`](repo:re/songplay.lst), made by [`tools/disasm_player.py`](repo:tools/disasm%5Fplayer.py) with the names of [`re/songplay_names.txt`](repo:re/songplay%5Fnames.txt).

[`re/notes/`](repo:re/notes/) holds 29 notes, one Markdown file a subject, about 197,000 words in all. A later session starts from them instead of reading the listing again. Eighteen describe a part of the game: its purpose, its data with their offsets, its routines, what is still open. Eight are [**porting notes**](../glossary.md#porting-note), each written for a milestone: what was ported, how it is held to the original, what stands in, each statement marked as observed, with the test or tool that shows it, or as read from the listing alone. Those of M4 to M8 end with their [reach maps](../glossary.md#reach-map) (chapter 8). One note describes an instrument, one the suite, one an idea. The last column names the chapter that tells the subject:

| Note | Subject | Words, about | Chapter |
|---|---|---|---|
| [`campaign.md`](repo:re/notes/campaign.md) | the campaign, the saved game | 3,700 | 17 |
| [`demo.md`](repo:re/notes/demo.md) | the demo | 1,600 | 17 |
| [`display.md`](repo:re/notes/display.md) | the display | 3,500 | 11 |
| [`drawing.md`](repo:re/notes/drawing.md) | the drawing routines | 3,700 | 12 |
| [`enemy.md`](repo:re/notes/enemy.md) | the enemy | 4,500 | 16 |
| [`ffp.md`](repo:re/notes/ffp.md) | the floating point | 3,000 | 14 |
| [`frontend.md`](repo:re/notes/frontend.md) | the front end | 4,000 | 19 |
| [`highscore.md`](repo:re/notes/highscore.md) | the high-score file | 700 | 17 |
| [`input.md`](repo:re/notes/input.md) | input | 1,100 | 7 |
| [`keys.md`](repo:re/notes/keys.md) | the key commands | 3,200 | 19 |
| [`map.md`](repo:re/notes/map.md) | the maps | 2,400 | 13 |
| [`music.md`](repo:re/notes/music.md) | the music | 2,700 | 18 |
| [`objects.md`](repo:re/notes/objects.md) | the object system | 4,200 | 15 |
| [`passes.md`](repo:re/notes/passes.md) | passes and ticks | 2,500 | 7 |
| [`random.md`](repo:re/notes/random.md) | chance, the video rate | 600 | 6, 7 |
| [`shapes.md`](repo:re/notes/shapes.md) | shapes | 2,900 | 12 |
| [`sound.md`](repo:re/notes/sound.md) | the sound effects | 2,200 | 18 |
| [`system-font.md`](repo:re/notes/system-font.md) | the system font | 400 | 19 |
| [`porting-m1.md`](repo:re/notes/porting-m1.md) | M1, the loaders | 2,100 | 3, 12 |
| [`porting-m3.md`](repo:re/notes/porting-m3.md) | M3, the front end | 3,500 | 19 |
| [`porting-m4.md`](repo:re/notes/porting-m4.md) | M4, the world and the player | 27,500 | 8 |
| [`porting-m5.md`](repo:re/notes/porting-m5.md) | M5, the weapons | 22,800 | 15 |
| [`porting-m6.md`](repo:re/notes/porting-m6.md) | M6, the enemy | 34,200 | 16 |
| [`porting-m7.md`](repo:re/notes/porting-m7.md) | M7, the campaign | 33,500 | 17 |
| [`porting-m8.md`](repo:re/notes/porting-m8.md) | M8, the sound | 10,900 | 18 |
| [`page-video.md`](repo:re/notes/page-video.md) | M9, the picture on the GPU | 4,200 | 23 |
| [`headless.md`](repo:re/notes/headless.md) | the headless original | 7,600 | 6 |
| [`testing.md`](repo:re/notes/testing.md) | running the suite | 2,500 | 24 |
| [`amiga-to-web.md`](repo:re/notes/amiga-to-web.md) | a template | 1,300 | 10 |

## ref/: the artwork to look at

[`ref/sheets/`](repo:ref/sheets/) holds seven [contact sheets](../glossary.md#contact-sheet), every shape of five containers with its name, made by [`tools/ppkc.py`](repo:tools/ppkc.py). They are committed so that a reader can look at the artwork without running anything, and the screens of the front end were judged partly against them, since the headless original draws nothing.

## src/: the core

[`src/`](repo:src/) is the [core](../glossary.md#core), the game ported to C, compiled to [WebAssembly](../glossary.md#webassembly) for the page and to the [native library](../glossary.md#native-library) for the tests: 35 C files, three headers and three registries. The files that port the game follow the original's modules, their routines in the original's address order, so that a reader can move between the listing and the source; every ported routine carries a comment, `orig` and its address, the bridge between the two. The C files fall into four groups:

| Group | Files |
|---|---|
| the frame, a port of nothing | [`core.c`](repo:src/core.c) (the entry points, the saved states), [`rand.c`](repo:src/rand.c) (the stream of chance), [`trace.c`](repo:src/trace.c) (what the port did, for the tests) |
| the machine and its system, stood in for | [`mem.c`](repo:src/mem.c), [`fs.c`](repo:src/fs.c), [`gfx.c`](repo:src/gfx.c), [`screen.c`](repo:src/screen.c), [`video.c`](repo:src/video.c), [`audio.c`](repo:src/audio.c), [`ffp.c`](repo:src/ffp.c) |
| the game, ported | 23 files, from [`load.c`](repo:src/load.c) to [`music.c`](repo:src/music.c), among them [`input.c`](repo:src/input.c) (the sampling, a VBlank's controller state into a tick's input byte), [`front.c`](repo:src/front.c), [`world.c`](repo:src/world.c) (a pass), [`tick.c`](repo:src/tick.c) and [`player.c`](repo:src/player.c) |
| the port's own layers, decided with the owner | [`portkeys.c`](repo:src/portkeys.c) (the port's keys), [`assist.c`](repo:src/assist.c) (the keyboard assist) |

The registries, [`src/globals.def`](repo:src/globals.def), [`src/mission.def`](repo:src/mission.def) and [`src/records.def`](repo:src/records.def), list every variable, table and record layout the port took over, tied to the original's addresses and offsets, by which the tests copy state between the two games and compare it. [`src/wof.h`](repo:src/wof.h) is the core's interface. The game's numbers are not here: hand-written sources hold code only, and the manifest's tables are generated as C at every build into a directory that is never committed (chapter 3). Chapter 22 opens the core.

## web/: the shell

[`web/`](repo:web/) is the [shell](../glossary.md#shell), plain JavaScript with no framework: the page's template [`web/index.html`](repo:web/index.html), its stylesheet, and eight modules, the clock, the core's wrapper, the input, the video, the audio and its worklet, the diagnostics overlay and the entry point that joins them. A page opened from a file cannot load modules one by one, so the build joins them into the page with the core and the game's files. Chapter 23 tells the shell.

## tools/: the instruments

[`tools/`](repo:tools/) holds 43 Python tools, the setup script [`tools/setup.sh`](repo:tools/setup.sh), and in [`tools/fd/`](repo:tools/fd/) the system libraries' lists of routines by which the disassembler names the system's calls. All but one open with a sentence saying what they are for. By group:

| Group | Tools |
|---|---|
| the build | [`build.py`](repo:tools/build.py), [`extract_tables.py`](repo:tools/extract%5Ftables.py) |
| reading the program | [`disasm.py`](repo:tools/disasm.py), [`disasm_player.py`](repo:tools/disasm%5Fplayer.py), [`skel.py`](repo:tools/skel.py), [`m68kdis.py`](repo:tools/m68kdis.py), [`hunk.py`](repo:tools/hunk.py) |
| the oracle (chapter 5) | [`oracle.py`](repo:tools/oracle.py), and [`m68k_fix.py`](repo:tools/m68k%5Ffix.py) for the emulator's fault |
| the headless original (chapter 6) | [`headless.py`](repo:tools/headless.py), with the system, the dump, the writes and the sound chip in four more |
| observing and measuring | [`reach_observe.py`](repo:tools/reach%5Fobserve.py), the reach map, and eight more, the film of the real machine among them |
| the missions' scripts (chapter 8) | for each of M4 to M7 an autopilot and the scripts it flew; [`m7_controls.py`](repo:tools/m7%5Fcontrols.py) |
| the decoders | [`rpck.py`](repo:tools/rpck.py), [`ppkc.py`](repo:tools/ppkc.py), [`map_decode.py`](repo:tools/map%5Fdecode.py), [`song_decode.py`](repo:tools/song%5Fdecode.py), [`savegame.py`](repo:tools/savegame.py) |
| the checks | [`rom.py`](repo:tools/rom.py), [`mdcheck.py`](repo:tools/mdcheck.py) for the Markdown, [`junit_compare.py`](repo:tools/junit%5Fcompare.py) for two runs of the suite |

The decoders serve the tools, the tests and this book; the core uses the game's own loaders, ported (chapter 3). Chapter 25 tells how to run the tools.

## tests/: the suite

[`tests/`](repo:tests/) is the suite: about 930 tests in 34 modules, run by pytest, with the helpers they share and fourteen drivers in Node that run the WebAssembly core and drive the two browsers. The modules by layer:

| Layer | Modules |
|---|---|
| a routine under the oracle | [`test_oracle_m1.py`](repo:tests/test%5Foracle%5Fm1.py), six more by milestone, one for the floating point |
| the headless original | [`test_headless.py`](repo:tests/test%5Fheadless.py), [`test_frontend.py`](repo:tests/test%5Ffrontend.py) and three more |
| the port against the original | [`test_world.py`](repo:tests/test%5Fworld.py), [`test_enemy.py`](repo:tests/test%5Fenemy.py), [`test_campaign.py`](repo:tests/test%5Fcampaign.py) and eight more |
| the core's two builds | [`test_core_native.py`](repo:tests/test%5Fcore%5Fnative.py), [`test_core_wasm.py`](repo:tests/test%5Fcore%5Fwasm.py), [`test_replays.py`](repo:tests/test%5Freplays.py), [`test_isolation.py`](repo:tests/test%5Fisolation.py) |
| the page | [`test_page.py`](repo:tests/test%5Fpage.py), [`test_firefox.py`](repo:tests/test%5Ffirefox.py), [`test_dist.py`](repo:tests/test%5Fdist.py) |
| the port's own layer | [`test_assist.py`](repo:tests/test%5Fassist.py) |
| the repository | [`test_generated.py`](repo:tests/test%5Fgenerated.py), [`test_rom.py`](repo:tests/test%5From.py) |

[`tests/runs/`](repo:tests/runs/) holds 34 [run descriptions](../glossary.md#run-description), the player's hands VBlank by VBlank, with no game data in them; [`tests/replays/demo_a.json`](repo:tests/replays/demo%5Fa.json) is a demo the port recorded, replayed in both builds of the core. The native library is built from the same C and never committed, and [`tests/shim.c`](repo:tests/shim.c), the tests' way into the core's insides, is compiled into it and nothing else, so the page never carries it. Chapter 24 tells the layers and what one run of the suite proves.

## dist/: the page

[`dist/wof.html`](repo:dist/wof.html), the game, is the one committed build, so that a reader can play without building anything. A worker never commits it: the controller builds it again at every merge and commits that, so the committed page is always the build of the committed sources. Two builds of the same sources are the same byte for byte and name no directory of the machine that made them, so anyone can build it again and compare.

## book/: this book

[`book/`](repo:book/) holds everything of this book and is the site's whole source. [`book/BOOK.md`](repo:book/BOOK.md) is its handbook: the reader model, the outline, the style guide, the way of working. [`book/mkdocs.yml`](repo:book/mkdocs.yml) configures the site, made with MkDocs. [`book/docs/`](repo:book/docs/) holds the chapters, the glossary, the hand-drawn diagrams and two interactive pages, the [shape browser](../browser.md) and the [map viewer](../maps.md). [`book/tools/`](repo:book/tools/) holds the generators, steered by [`book/listings.toml`](repo:book/listings.toml) and [`book/figures.toml`](repo:book/figures.toml). [`book/facts/`](repo:book/facts/) holds a fact sheet for each chapter, every claim with its source. [`book/requirements.txt`](repo:book/requirements.txt) pins the book's packages whole, those they pull in as well, so that every clone builds the site with the same engine.

The book's listings, figures, interactive data and web font are generated from the real sources and committed, about 280 files under [`book/docs/generated/`](repo:book/docs/generated/), so that building the site needs only the book's packages: no ROM, no compiler, no browser. The site embeds the repository's page itself, copied in at every build.

## How the parts hang together

Four chains tie the parts together.

![Four lanes, one a chain: the names, the tables, the comparison and the generated files, each step a file or a tool by its path; solid arrows make or feed, dotted ones name, dashed ones hold.](../figures/repository-chains.svg)

/// caption
The four chains: what is kept by hand, what is made from it, and what holds what is made.
///

### The names

A name added to [`re/names.txt`](repo:re/names.txt) reaches every place the program is shown. A run of the disassembler, about two seconds, writes it into the listing and the inventory; from there it reaches every [control-flow skeleton](../glossary.md#control-flow-skeleton), the headless original's reports and, at the next build, the book's listings, which name a routine by its name in the inventory and fail on a name that no longer exists. So one word, chosen once, names a routine in the listing, the notes, the source, the tests and this book (chapter 4).

### The tables

An entry of the manifest becomes a table in C at every build: [`tools/extract_tables.py`](repo:tools/extract%5Ftables.py) reads it from the program's bytes and turns the byte order around, so that no number of the game is typed again, and an address outside the program stops the build (chapter 3). The book reads the same bytes: its interactive pages take the name lists and file names through the same manifest.

### The comparison

A claim in a note names the test that shows it; the test names the run descriptions it replays or the oracle's cases it runs; a run description replays with one command. Take the manual's Control-D, which chapter 20 told. [`re/notes/keys.md`](repo:re/notes/keys.md#in-flight-and-paused-ingame%5Fkeys-0x01ccf6) says it is not in the code and names `test_control_d_does_nothing_anywhere` in [`tests/test_frontend.py`](repo:tests/test%5Ffrontend.py). The test runs four pairs, in flight, paused, at the rank selection and in the briefing, each a run with the key and one without, and demands the same final state, files and schedule. Here is the run at the rank selection; look at the key on line 11, 34 with Control, D's code in decimal:

```json linenums="1"
--8<-- "generated/listings/json/rank-control-d.json"
```

`.venv/bin/python tools/headless.py run tests/runs/rank-control-d.json --out A.dump` runs it under the [headless original](../glossary.md#headless-original) and writes the [dump](../glossary.md#dump) of every step. A test's name says what it holds, so that a chapter can cite it by name, as this one does.

### The generated files

A [**generated file**](../glossary.md#generated-file) is one a tool makes from other files of the repository. The repository commits it, so that a reader sees it without running the tool, and holds it byte for byte to what the tool makes again, so that the reader need not trust it. [`tests/test_generated.py`](repo:tests/test%5Fgenerated.py) holds the listing, the inventory, the player's listing and the contact sheets, none of which needs the ROM. Here is its first test:

```python
--8<-- "generated/listings/py/test_the_listings_are_their_regeneration.py"
```

[`book/tools/build.py --check`](repo:book/tools/build.py) holds the book's generated files the same way, and checks every colour against the game's palette entry its comment names and every link into the repository. The page is held another way: it is built again at every merge, and the build always gives the same bytes.

## Where to start

- **To play**, open [`dist/wof.html`](repo:dist/wof.html) in Chrome, Firefox or Safari, straight from the file; the keys are on its help screen.
- **To read the code**, open a file of [`src/`](repo:src/) with the listing beside it, the `orig` comments as the bridge.
- **To check a claim**, go from the note to the test it names, and from the test to the run it replays.
- **To change something**, read chapter 25, and the README's [Build and verify](repo:README.md#build-and-verify).
- **To read the history**, read the commits, a few hundred, each message a line saying what changed and naming the session's model.

## What the repository leaves out

The ROM is licensed, so whoever clones brings their own. The project's chronicle, its decisions, findings and mistakes with their dates, lives in the owner's archive beside the sessions' transcripts: too detailed for a release, it gives this book only the order of events. What a build makes, the tables, the WebAssembly core outside the page, the native library, the book's built site, is made again from what is committed, and the local environment by the setup from the pins.

/// dev
`git ls-files src | wc -l` counts what the repository holds of a directory. `grep -rn "orig 0x01C982" src/` finds the port of the routine at that address, `record_at` in [`src/player.c`](repo:src/player.c); [`tools/skel.py record_at`](repo:tools/skel.py) prints its skeleton. Read [`re/functions.csv`](repo:re/functions.csv) with a CSV reader, since its strings hold commas, and the listing by an address range or a search, never whole.
///

## What comes next

The chapter in one sentence: the repository keeps the original, what was read from it, the port and its instruments side by side, and four chains hold them to each other. Chapter 22 opens [`src/`](repo:src/): the porting rules, the registered state, the arena, the file system and the interface the shell sees.

## Further reading

The files named here are in the repository, [`github.com/sy2002/wof-wasm`](repo:).

- [`README.md`](repo:README.md): ["Play"](repo:README.md#play), ["Build and verify"](repo:README.md#build-and-verify), ["Where things are"](repo:README.md#where-things-are) and ["Licence"](repo:README.md#licence).
- [`SPEC.md`](repo:SPEC.md), sections 2, ["Repository"](repo:SPEC.md#2-repository), and 4, ["Tools"](repo:SPEC.md#4-tools).
- [`CLAUDE.md`](repo:CLAUDE.md): ["Commands"](repo:CLAUDE.md#commands), ["Session protocol"](repo:CLAUDE.md#session-protocol) and ["Rules"](repo:CLAUDE.md#rules); [`CONTROLLER.md`](repo:CONTROLLER.md).
- [`book/BOOK.md`](repo:book/BOOK.md), sections 5, ["The site"](repo:book/BOOK.md#5-the-site), and 6, ["The way of working"](repo:book/BOOK.md#6-the-way-of-working).
- [`re/notes/`](repo:re/notes/), [`tests/runs/`](repo:tests/runs/) and [`tools/`](repo:tools/).

Outside the repository: Wikipedia's ["Git"](https://en.wikipedia.org/wiki/Git), for what a repository and a clone are; the [GNU General Public License](https://www.gnu.org/licenses/gpl-3.0.html) and [Creative Commons Attribution-ShareAlike 4.0](https://creativecommons.org/licenses/by-sa/4.0/); [MkDocs](https://www.mkdocs.org/), the site's engine.
