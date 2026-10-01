# The book about the port: its handbook

The reader model, the outline, the style guide, the site and the way of working for the book in this directory. **A draft of 2026-10-01**, written by the controller as a proposal: the owner's answers to the questions of section 7 settle it, and until then every point of it is a recommendation. Decided by the owner on 2026-10-01: the book covers the whole, what was done and how it was known to be right, and not the days, the hours or the quotes; the prose, this book included, is under CC BY-SA 4.0 (`../LICENSE-CC-BY-SA-4.0`).

## 1. What the book is

A didactic book about how a 1990 Amiga game was ported, routine by routine, to the browser, and how one knows the port is faithful; then what is inside the game and how it uses the Amiga; then the code, the tools and how to build. In the spirit of Fabien Sanglard's *Game Engine Black Book*: concrete, sourced, illustrated from the real data, readable by an enthusiast who has never seen the source. Published as an interactive static site from `book/` in this repository.

**Working title (recommendation):** *Bringing Back Wings of Fury*, subtitle *A 1990 Amiga game ported to the browser, and how we know it is faithful*. Alternatives: *Wings of Fury: The Port Book*; *The Wings of Fury Port*.

**Language (recommendation):** English, as the repository and the audience.

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
7. *Time.* VBlanks, passes and ticks; one input byte per four VBlanks; why the schedule is an input of the simulation; the film of the real Amiga at 240 frames a second: two VBlanks a pass.
8. *Porting a mission.* The reach map: what the scripts execute is ported, the rest is a marked stand-in that fails loudly. The open loop and the closed loop. The completeness list. The controls: breaking the port on purpose. The autopilots that find a landing or an attack.
9. *What went wrong, and what caught it.* The stick's bits, the shift, the timeout, the shared core, the register carried as a long, the last ticks nobody compared. Each with the instrument that caught it.
10. *How the port was made.* The way of working as a whole: one controller and workers in sessions, the rules, the reviews, the instruments, what it cost and what it took; the honest account of the AI collaboration, since that is the case study, told as an overview and not as a diary.

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

21. *A tour of the repository.* Where everything is, the notes, the specification, the listing, the chronicle.
22. *The core.* The porting rules (the 16-bit int, the registered state, blocking code as coroutines), the arena, the file system, the interface the shell sees.
23. *The shell.* The clock, the WebGL picture and the two-step scaling, the audio worklet, the keys, the storage, the help screen, the pause sign, fullscreen.
24. *The tests.* The layers, the two phases, the page tests under a true scale factor, the replays; what one run proves.
25. *Build it yourself.* The setup, the ROM, the build, running the headless original, reading a routine with the tools; how to fix a bug or extend the port.

**Appendices.** The glossary. The keys. The routine inventory. The licence and the game data.

**Recommendation on the writing order:** Part I first (the chronicle and the porting notes are the freshest sources), then Part II, then Part III; the preface last. About 25 chapters of 2,500 to 5,000 words, 60,000 to 90,000 words in all; the owner's read of each chapter is the final gate, which makes their reading time the pace.

## 4. The style guide

1. **Plain and concrete.** Short sentences, one idea per paragraph, no hype and no exclamation marks. The voice is the project's *we* for the work and *you* for the reader; the preface says who *we* were.
2. **Every number has its source**: a note's section, a listing address, a commit, a test, a film. The book's build extracts listings and renders figures from the real data, so that a stale claim fails the build rather than the reader.
3. **Terms** are introduced once, in bold with a one-line definition, and listed in the glossary. Hex is written as `0x010228` in code font; addresses always use the fixed load layout of the port.
4. **Listings** are extracted from the real sources by routine name at build time, never retyped, at most about forty lines each, with a sentence before each that says what to look at. A ported routine is shown as the assembly from the listing beside its C.
5. **Figures** are rendered by the port's own library at build time (a screen, a shape, a map, a palette) and committed as images, so that the site can be rebuilt without the ROM. Diagrams are SVG in the repository. Photographs only of what no library can render (the real machine).
6. **Sidebars** of three kinds: *How we know* (the instrument), *What went wrong* (a mistake and what caught it), *For the developer* (the deeper detail with the link into the source). No dates and no quotes in the body; the time of an event matters only where the order of events is the point.
7. **The game's texts and the manual** are never quoted at length; the game's art is shown as pictures rendered from the data.
8. **Keys** are named by their position where layouts differ; the machine is PAL.
9. **A chapter's shape:** what you will understand, the body, what went wrong (if anything did), what it hands to the next chapter, further reading (the note, the source).
10. **No narration of the writing.** The finished chapter reads as if it had always been right; the process is the subject of chapter 10, nowhere else.

## 5. The site

**Engine (recommendation):** Material for MkDocs, as the owner's AExp site, with a design of its own: a palette and fonts taken from the game (the game's own font as a web font made at build time for headings, the game's colours as accents), custom CSS, light and dark. It is Markdown-based, searchable, works on GitHub Pages, and the owner knows it. Alternatives: mdBook (Rust, simpler, fewer extensions) or a small generator of our own (full control, more work).

**The build** (`book/tools/`, Python from the project's `.venv`): a step before `mkdocs build` that (a) extracts the listings named by the chapters from `src/`, `web/`, `tools/` and `re/Wings.lst` into generated files, failing on a name that no longer exists; (b) renders the figures through the native library and the tools (`tools/ppkc.py`, `tools/map_decode.py`, the screens through the core) into committed images; (c) copies `dist/wof.html` into the site so that the embedded game is the repository's page. `mkdocs gh-deploy` publishes to a `gh-pages` branch; the site is built locally because the figures need the ROM's font, and the images are committed so that anyone can rebuild the site without it.

**Interactive elements, first edition (recommendation):** the playable game (an iframe of the page, with a note on the keys); the shape browser (every shape of every container as a gallery with its name, size, planes and the mirror, from images made at build time, no WebAssembly needed); the map viewer (each map's picture with the records overlaid and an inspector for a record's fields). Later, if wanted: a tick stepper that runs the core one tick at a time and shows the registered state.

## 6. The way of working

The controller is the editor: the outline, the style guide, the order, the reviews, and alone the owner's contact. This file holds the reader model, the outline, the style guide and the review below; the project's chronicle, kept outside the repository, is the writers' private source for the order of events.

**Per chapter, one Opus worker on a branch:**

1. **The fact sheet**: every claim the chapter will make with its source (a note's section, a listing address, a commit, a test), the figures to render, the listings to extract, the interactive element if any. The controller reads it against the notes and approves.
2. **The draft** from the fact sheet and the style guide, with the figures and the listings generated and the site's build green.
3. **The fact-check** by a second worker that had no part in the draft: every claim against the notes and the listing, in a report.
4. **The readability read** by a fresh session as the primary reader, given only the chapter and the glossary, reporting where it lost the thread.
5. **The controller's own read** and edit; then **the owner's read** as the final gate; then the merge, and the site rebuilt.

Workflows with several agents only for the fan-out steps, the fact-checks and the readability reads over a few chapters at once, tried once and costed; never for the prose.

## 7. The questions, each with its recommendation

1. **The title:** *Bringing Back Wings of Fury*, subtitle as above.
2. **The language:** English.
3. **The outline:** the 25 chapters and the appendices of section 3, written Part I, II, III.
4. **The voice and the AI:** the project's *we*, and the collaboration told in the open, in the preface and in chapter 10, because the case study is exactly that.
5. **The engine:** Material for MkDocs with a design of its own; a `gh-pages` branch deployed from a local build.
6. **The interactive elements of the first edition:** the playable game, the shape browser, the map viewer.
7. **The book's licence:** CC BY 4.0 for the text and the diagrams, with the note that the figures rendered from the game's data are the game's art and stand under the same reservation as `original/`.
8. **The pace:** one chapter at a time; the owner reads every chapter before it is merged.
