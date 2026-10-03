# The book about the port: its handbook

The reader model, the outline, the style guide, the site and the way of working for the book in this directory, settled with the owner on 2026-10-01. Three conditions of the owner's hold over everything below: the book covers the whole, what was done and how it was known to be right, and not the days, the hours or the quotes; everything of the book lives under `book/`, the interactive elements included, so that the directory is self-contained and is the base of the GitHub Pages site; and the book's prose is under CC BY-SA 4.0 (`../LICENSE-CC-BY-SA-4.0`), as the repository's prose is, while the figures rendered from the game's data and the listings taken from its executable are the game's and stand under the same reservation as `original/` (`../README.md`, Licence).

## 1. What the book is

A didactic book about how a 1990 Amiga game was ported, routine by routine, to the browser, and how one knows the port is faithful; then what is inside the game and how it uses the Amiga; then the code, the tools and how to build. In the spirit of Fabien Sanglard's *Game Engine Black Book*: concrete, sourced, illustrated from the real data, readable by an enthusiast who has never seen the source. Published as an interactive static site from `book/` in this repository.

**Title:** *Bringing Back Wings of Fury*, subtitle *A 1990 Amiga game ported to the browser, and how we know it is faithful*.

**Language:** English, as the repository and the audience.

## 2. The reader model

**The primary reader** is a retro enthusiast: has played Amiga games, may own an Amiga or a MEGA65, has programmed something (BASIC, Python, a little C), has never read 68000 assembly and has not opened this repository. They read for pleasure and understanding, one chapter at a sitting of about twenty minutes. At the end they can explain to a friend what a faithful port is, how it differs from an emulator and a remake, how the port was held to the original, and how the game does three or four of its tricks.

**The second reader** is a developer who wants to do the same for another game. They read Part I and Part III for the method and the tools and follow the source links.

**The third reader** is the future maintainer of this repository, human or AI. For them the notes in `re/notes/` are the reference; the book only points to them.

What follows from the model:

- No chapter requires the source. The source is linked at the exact place for the curious, and a sidebar *For the developer* carries the deeper detail.
- Every term is introduced at its first use with a one-line definition and appears in the glossary. Amiga terms are kept (copper, blitter, Paula, bitplane, VBlank), because the reader wants to learn them.
- Every claim carries how it was found. The instrument is the didactic point of a preservation case study: the oracle, the headless original, the film of the real machine, a test that failed.
- A chapter opens with what the reader will understand at its end and closes with what it hands to the next.

## 3. The outline

Three parts, in the owner's arc: the story and the method first, then the game inside, then the code and the toolchain. Chapter 2 is a short primer so that Part I can be read without Part II; the deep dives come in Part II.

**Front matter.** The preface (why: preservation, a case study, who did what: the owner and the AI sessions, in the open). How to read this book. The game itself, playable in the page.

**Part I: From the disk to a faithful game.**

1. *What faithful means.* Port, emulator, remake. The three-part definition: logic tick for tick, the same pixels and palette, the same sample starts. Why the browser and one HTML file. What was left out (the crack intro, the copy protection) and what was changed on purpose (the keys, the assist, the remembered flip).
2. *The Amiga in twenty minutes.* The 68000, chip memory, bitplanes, the copper, the blitter, Paula, the VBlank, and the little of AmigaOS the game uses. Only what the port needed.
3. *The disk.* The ADF and its files, the executable's hunks, Manx Aztec C with 16-bit ints, the data reached through A4. Why the tables and texts are extracted at build time and never retyped.
4. *Reading the executable.* The disassembler and the listing, names, the control-flow skeleton, what compiled C looks like against hand-written assembly, what could be recognised and how.
5. *The oracle.* One original routine run under emulation and compared with its port on thousands of inputs. What "verified" means. The emulator's own bug (the memory-form shift) as the first lesson: the instrument is checked too.
6. *The headless original.* The whole game run without a screen, the operating system stubbed, the beam position as the only source of chance, VBlanks only where the program waits, a dump after every tick. Determinism, and the wall-clock lesson.
7. *Time.* VBlanks, passes and ticks; one input byte per four VBlanks; why the schedule is an input of the simulation; the film of the real Amiga at 240 frames a second: two VBlanks a pass. The fade step, processor time in the original that the listing cannot give, set by eye in the port.
8. *Porting a mission.* The reach map: what the scripts execute is ported, the rest is a marked stand-in that fails loudly. The open loop and the closed loop. The completeness list. The controls: breaking the port on purpose. The autopilots that find a landing or an attack.
9. *What went wrong, and what caught it.* The stick's bits, the shift, the timeout, the shared core, the register carried as a long, the last ticks nobody compared. Each with the instrument that caught it.
10. *How the port was made.* The way of working as a whole: one controller and workers in sessions, the rules, the reviews, the instruments, what it took; the honest account of the AI collaboration, since that is the case study, told as an overview and not as a diary.

**Part II: The game inside.**

11. *The display.* 320 x 214 in three areas, five bitplanes, the copper lists the game builds itself, the per-row palettes, day and night, the two scales.
12. *Shapes.* The containers, the packer, the blit through the blitter, mirrors, clipping; the contact sheets. Interactive: the shape browser.
13. *The world.* The map file and its records, world coordinates, the scrolling, islands and airfields. Interactive: the map viewer.
14. *The player.* The flight model on the ROM's floating point, the stick, take-off, the cable, the deck and the hold, fuel, the crash and the restart.
15. *Weapons, targets and soldiers.* Bombs, rockets, torpedoes, guns; dug-outs, pillboxes, the soldiers' timers, the pools, the balloons.
16. *The enemy.* The aircraft's states, launches, ships and their guns, the torpedo run, the carrier's defence, the 3-D view.
17. *The campaign.* Ranks, missions, promotion, the night, the saved game's bytes, the demo and the attract mode, the high scores; the game that never ends.
18. *Sound and music.* Paula, the effects engine's slots, the music player and its timer, the tempo that rests on one assumption.
19. *The front end and the keys.* The scroller, the title, the menus, the line editor, the keymap from the ROM; the port's keys and the assist.
20. *The original's quirks.* The wreck's explosion and the address it takes for an x, the directory order, what a real Amiga does differently and what the port keeps on purpose.

**Part III: The code, the tools and the build.**

21. *A tour of the repository.* Where everything is, the notes, the specification, the listing, the handbook.
22. *The core.* The porting rules (the 16-bit int, the registered state, blocking code as coroutines), the arena, the file system, the interface the shell sees.
23. *The shell.* The clock, the WebGL picture and the two-step scaling, the audio worklet, the keys, the storage, the help screen, the pause sign, fullscreen.
24. *The tests.* The layers, the two phases, the page tests under a true scale factor, the replays; what one run proves.
25. *Build it yourself.* The setup, the ROM, the build, running the headless original, reading a routine with the tools; how to fix a bug or extend the port.

**Appendices.** The glossary. The keys. The routine inventory. The licence and the game data.

**The writing order:** Part I first (the chronicle and the porting notes are the freshest sources), then Part II, then Part III; the preface last. About 25 chapters of 2,500 to 5,000 words, 60,000 to 90,000 words in all; the owner's read of each chapter is the final gate, which makes their reading time the pace.

## 4. The style guide

1. **Plain and concrete.** Short sentences, one idea per paragraph, no hype and no exclamation marks. The voice is the project's *we* for the work and *you* for the reader; the preface says who *we* were. **The why with the how:** every mechanism, number, tool and decision a chapter introduces carries its reason, what it is for, what problem it solves or what would go wrong without it, before or beside the how, in the chapter's own voice and without a formula: no ritual "why" opening, no "in this section we will". The reader reads cover to cover without the background; a section that tells what the copper does must first say what the game wants from it.
2. **Every number has its source**: a note's section, a listing address, a commit, a test, a film. Where a page names a file of the repository, the name is a link to it in the book's `repo:` scheme, which the build checks, so that a renamed file or a renamed heading fails the build rather than the reader. The book's build extracts listings and renders figures from the real data, so that a stale claim fails the build rather than the reader. Counts that grow with the suite are rounded in the prose and exact in the fact sheet with their commit; fixed counts (the maps, the files, the scripts of the finished port) are exact. **Numbers in prose:** sentences and paragraphs dense with numbers make a reader dizzy, so about three numbers a sentence at most; a cluster of related figures goes to a short table or a figures box; a derived number, a conversion of another, stays out of the prose; a number that is not the point is rounded; the fact sheet keeps every figure exact. A chapter's length is `wc -w` of its page file, markup, captions and sidebars included, between 3,000 and 4,500 words. A general fact about the machine that the notes do not state is sourced in the fact sheet in a named reference work with its chapter and marked "(reference)", so that the fact-check weighs it; what the game does with the machine always comes from the notes.
3. **Terms** are introduced once, in bold with a one-line definition, and the bold is a link to the term's glossary entry. Hex is written as `0x010228` in code font; addresses always use the fixed load layout of the port. A term used before the chapter that defines it is linked to its glossary entry with a short gloss and not set in bold. The glossary says of each term where the reader first meets it and where it is defined, "First met in chapter N, defined in chapter M." or "First met and defined in chapter N.", and the build holds that line against the chapters. A bold that opens a list item is a label, not a term. "Sample" never stands alone: a sound sample is what Paula plays, an input sample the input byte taken every fourth VBlank.
4. **Listings** are extracted from the real sources by routine name at build time, never retyped, at most about forty lines each, with a sentence before each that says what to look at. A ported routine is shown as the assembly from the listing beside its C.
5. **Figures** are rendered by the port's own library at build time (a screen, a shape, a map, a palette) and committed as images, so that the site can be rebuilt without the ROM. Diagrams are SVG in the repository. Photographs only of what no library can render (the real machine).
6. **Sidebars** of one kind: *For the developer* (the deeper detail with the link into the source). No *How we know* box: the mechanics of an instrument belong to its chapter, 5 to 9, and a chapter that needs to say that something was checked does it in one plain sentence naming that chapter. No *What went wrong* box: the mistakes and what caught them are chapter 9's, and a mistake that is a section's own point is told in the body in a sentence or two; the fact sheets keep such claims marked for chapter 9. No dates and no quotes in the body; the time of an event matters only where the order of events is the point.
7. **The game's texts and the manual** are never quoted at length; the game's art is shown as pictures rendered from the data. The manual is cited by page as `original/manual.txt` counts them: a line `PAGE N` begins page N.
8. **Keys** are named by their position where layouts differ; the machine is PAL.
9. **A chapter's shape:** what you will understand, the body, what it hands to the next chapter, further reading (the note, the source).
10. **No narration of the writing.** The finished chapter reads as if it had always been right; the process is the subject of chapter 10, nowhere else.

## 5. The site

**Engine:** Material for MkDocs, as the owner's AExp site, with a design of its own: a palette and fonts taken from the game (the game's own font as a web font made by the book's build from the data and committed, for the headings; the game's colours as accents), custom CSS, light and dark. It is Markdown-based, searchable, works on GitHub Pages, and the owner knows it.

**Everything under `book/`:** the site's configuration and pages, its own pinned Python requirements (installed into the project's `.venv` beside the port's, so that a clone that only wants the game installs none of them), its tools, the generated listings, the rendered figures, the web font and the interactive elements. Nothing of the book lives elsewhere in the repository, and `mkdocs build` in `book/` needs only those packages: no ROM, no compiler and no browser, because everything that needs them is generated beforehand and committed.

**The build** (`book/tools/`, Python from the project's `.venv`, with the book's packages installed into it by `.venv/bin/python -m pip install -r book/requirements.txt`, or by `sh tools/setup.sh --book`, which installs them and builds the site before the ROM check, so that a clone without the ROM gets the book too; the setup without the flag installs none of them; the packages are pinned whole, the ones they pull in as well, and when mkdocs or mkdocs-material is raised the rest are refreshed from a fresh `.venv`'s `pip freeze`): `.venv/bin/python book/tools/build.py` does it all in order, one line per step. (a) `listings.py` extracts the listings named in `book/listings.toml` from `src/`, `web/`, `tools/` and `re/Wings.lst` into `docs/generated/listings/`, each with its source and its line or address range in its first line and at most forty lines unless its entry asks for more, and fails on a name that no longer exists (an `asm` entry with `head = true` keeps the routine's header lines; a `skel` entry is `tools/skel.py`'s output for the routine, made at build time; a `py` entry may name a file under `tests/` through `file`, a module-level variable by its name, a function nested in a function as `outer.inner`, or a part of a function by two texts, `from` and `to`, the first lines holding them; a `c` entry may name a file-scope variable, which is extracted with the comment above it, or a part of a function by two texts, `from` and `to`, as a `py` entry may; a `json` entry lays out the JSON file `file` names, one top-level entry a line, after a comment line naming the source); (b) `figures.py` renders the figures named in `book/figures.toml` through the native library and the tools (`tools/ppkc.py`, `tools/map_decode.py`, the screens through the core) into `docs/generated/figures/`, with a maker for each kind of figure (a screen, whole or a box of it, its palettes, a shape sheet, a map, the font, a shape's planes, one blit, a sound sample, the disk's directory, a packed file against its bytes, the code map, the day and night palette pairs, a fade's steps, one record's bytes, a shape's clear and set bytes at work, a shape and its mirror, a sheet of shapes picked from several containers, in a chosen number of columns, with empty cells where a row ends early, or of one container packed, a run of a map's records with their bits, the path of a flight from a run's trace with its moments marked, a saved game's pieces to scale with the raw part's regions and its pointer fields, a demo file's bytes as a dump; a screen's run may carry pokes made at the rank selection's end through the test hooks, and the stick's letters after the mission begins, or replay from the start a schedule the headless original recorded with the fade step the recording had, with registered values, the player's record's height, x, state and facing, and a field of a registered table's record by its index, it checks at a VBlank), added to as the chapters need; (c) `webfont.py` makes the game's own font into `docs/fonts/wof-newarmy.woff` through the port's decoding; (d) every colour of the stylesheet is compared with the palette entry its comment names; (e) `mkdocs build --strict` writes `book/site/`, and `hooks/game.py` adds `dist/wof.html` to the site, so that the embedded game is the repository's page and is never committed a second time. The generators need the built repository (`tools/build.py --native`, which needs the ROM) and macOS, as the tests do; what they make is deterministic and committed, so that `mkdocs build` in `book/` needs only the book's packages, and `build.py --check` makes it all again into a temporary directory and compares it with the committed files byte for byte. `build.py --serve` generates and then runs `mkdocs serve`. `book/site/` is never committed; `mkdocs gh-deploy` publishes it to a `gh-pages` branch.

**Writing a page:** no raw HTML, because `tools/mdcheck.py` flags every tag and every page must pass it. The chapter's kicker and a subtitle are paragraphs with a class from `attr_list` (`{ .chapter-kicker }`, `{ .subtitle }`). A figure is an image line followed by a `/// caption` block. A listing is a fence tagged `wingslst`, `c`, `js`, `python` or `json` whose one line is a snippet include, `--8<-- "generated/listings/<kind>/<name>.<ext>"`, so that a missing file fails the build; `linenums="1"` on the fence asks for line numbers. The assembly beside its C is a `//// html | div.listing-pair` block holding two `/// html | div` blocks, one fence each. The one sidebar is `/// dev`, closed with `///`. Where figures cluster, they go into a figures box, `/// figures` closed with `///`, holding a short table of label and value under a header row, with the title "The figures"; the prose keeps the number that carries its point, a count that grows with the suite is rounded in the box as in the prose, and a sentence with two numbers stays as it is. A term links to the glossary as `glossary.md#term`. The page `specimen.md` shows every element on real generated content and goes once the chapters show them all. A hand-drawn diagram is an SVG under `docs/figures/`, its colours in a style block, each commented with its palette entry as `book.css`'s are; `build.py --check` holds them as it holds the stylesheet's. Figures are shown on black, so a diagram is drawn for a black ground. A hand-drawn diagram repeats no count the build cannot hold, or names each in the fact sheet for the fact-check; without a browser an SVG is looked at through a renderer at hand, which may draw no stroked path, so the wires are checked in the source. A reference to a file of the repository is a link whose text is the path in a code span and whose target is `repo:` followed by the path and, for a Markdown file, the heading's anchor; `repo:` alone is the repository, a path ending in a slash a directory. `hooks/links.py` rewrites it to GitHub, blob for a file and tree for a directory, on the branch `extra.repo_branch` names; an anchor is the heading's slug as GitHub makes it, into Markdown files only, never a line. Where a reference names several sections, the file's span links the file and each section's name links its heading. An underscore in any link's target is written `%5F`, which `tools/mdcheck.py` needs; the site carries it plain. A glossary entry is its heading, its one-line definition, at most a short second paragraph where the term carries weight before a chapter of its own, the line of chapters with "The detail:" in `repo:` links, and, where a good page exists, a last line "Elsewhere:" with one or two https links, the English Wikipedia article or an online copy of an Amiga reference work (the Internet Archive holds them), each fetched once before it is committed. `build.py` checks it all at every build and with `--check`: every `repo:` link resolves, no code span names a repository file unlinked, every glossary line agrees with the chapters, every term in bold links its entry, and every link out of the repository is https; a failure exits with 4.

**Interactive elements, first edition:** the playable game (an iframe of the page, with a note on the keys); the shape browser (every shape of every container as a gallery with its name, size, planes and the mirror, from images made at build time, no WebAssembly needed); the map viewer (each map's picture with the records overlaid and an inspector for a record's fields). Later, if wanted: a tick stepper that runs the core one tick at a time and shows the registered state.

## 6. The way of working

The controller is the editor: the outline, the style guide, the order, the reviews, and alone the owner's contact. This file holds the reader model, the outline, the style guide and the review below; the project's chronicle, kept outside the repository, is the writers' private source for the order of events.

**Per chapter, one Opus worker on a branch:**

1. **The fact sheet**: every claim the chapter will make with its source (a note's section, a listing address, a commit, a test), the figures to render, the listings to extract, the interactive element if any. The controller reads it against the notes and approves. It is `book/facts/NN-name.md`, committed on the chapter's branch and brought to the draft whenever the draft changes.
2. **The draft** from the fact sheet and the style guide, with the figures and the listings generated and the site's build green.
3. **The fact-check** by a second worker that had no part in the draft: every claim against the notes and the listing, in a report.
4. **The readability read** by a fresh session as the primary reader, given only the chapter and the glossary, reporting where it lost the thread.
5. **The controller's own read** and edit; then **the owner's read** as the final gate; then the merge, and the site rebuilt. When the owner cannot read in time, the chapter is merged after the controller's read and listed in section 7 as awaiting the owner's read, whose findings become a follow-up on a new branch (the owner's decision of 2026-10-01, to use the time while they are busy).

The fact-check and the readability read are fresh Opus agents the controller spawns; they read the branch's files, run nothing heavier than a collection of the tests, and edit nothing. Workflows with several agents only for the fan-out steps, the fact-checks and the readability reads over a few chapters at once, tried once and costed; never for the prose.

## 7. Where the chapters stand

| Chapter | State |
|---|---|
| 1. What faithful means | final |
| 2. The Amiga in twenty minutes | final |
| 3. The disk | final |
| 4. Reading the executable | merged, awaiting the owner's read |
| 5. The oracle | merged, awaiting the owner's read |
| 6. The headless original | merged, awaiting the owner's read |
| 7. Time | merged, awaiting the owner's read |
| 8. Porting a mission | merged, awaiting the owner's read |
| 9. What went wrong, and what caught it | merged, awaiting the owner's read |
| 10. How the port was made | merged, awaiting the owner's read |
| 11. The display | merged, awaiting the owner's read |
| 12. Shapes | merged, awaiting the owner's read |
| 13. The world | merged, awaiting the owner's read |
| 14. The player | merged, awaiting the owner's read |
| 15. Weapons, targets and soldiers | merged, awaiting the owner's read |
| 16. The enemy | merged, awaiting the owner's read |
| 17. The campaign | merged, awaiting the owner's read |

A chapter not listed is a stub. The states, in order: drafted (on its branch); reviewed (the fact-check, the readability read and the controller's read done and folded in); merged, awaiting the owner's read; final (the owner's read done and folded in).
