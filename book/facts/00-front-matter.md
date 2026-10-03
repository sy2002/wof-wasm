# Fact sheet: the front matter and the appendices

Every claim the four pages will make that is a fact, one line each, with its source: the front page's preface and "How to read this book" (`book/docs/index.md`), the keys (`book/docs/keys.md`), the routine inventory (`book/docs/routines.md`) and the licence and the game data (`book/docs/licence.md`). The preface's reasoning, why the port and the book exist, is the project's voice and is not listed; what it states as fact is. A claim without a source goes to the list at the end and stays out of the pages. These pages define no term: a term they use links to its glossary entry in plain text, and none is set in bold (`book/BOOK.md` 4, point 3; `book/tools/links.py`, which reads the glossary's chapter lines from the chapters alone).

The sheet is brought to the draft: a claim the controller corrected or a claim kept off a page for its length is annotated in place; the controller approved the sheet with twelve notes, folded in where they touch a claim.

Counts are of the branch's base, `7b8216a`, read with Python's csv module from `re/functions.csv` and by counting the nav of `book/mkdocs.yml`. Nothing was run but CSV reads and, later, the book's build and its check: no test, no browser, no build of the page or the library.

Words used here as the pages use them. **The owner** is the project's owner, never named. **A session** is chapter 10's, one conversation with the AI coding assistant, Claude Code. **In flight** is the whole of a mission, the deck included, where `ingame_keys` reads the keys once a pass; **paused** is a mission paused. **The key layer** is `src/portkeys.c`'s rewriting of the port's command letters. **The shell's keys** are those `web/main.js` takes for itself. Keys are named by their position where layouts differ (`book/BOOK.md` 4, point 8).

The works outside the repository, each fetched once:

- The GNU Project's page of the licence, "The GNU General Public License v3.0", `https://www.gnu.org/licenses/gpl-3.0.html`: the licence's text of 29 June 2007, the same as `LICENSE`; its preamble: "if you distribute copies of such a program, whether gratis or for a fee, you must pass on to the recipients the same freedoms that you received", and `LICENSE`'s preamble goes on: they must "receive or can get the source code", and "you must show them these terms so they know their rights". **(reference)**
- Creative Commons' deed, "Attribution-ShareAlike 4.0 International", `https://creativecommons.org/licenses/by-sa/4.0/`, a summary of the licence that links its legal code: Share, "copy and redistribute the material in any medium or format for any purpose, even commercially"; Adapt, "remix, transform, and build upon the material for any purpose, even commercially"; Attribution, "You must give appropriate credit, provide a link to the license, and indicate if changes were made"; ShareAlike, "If you remix, transform, or build upon the material, you must distribute your contributions under the same license as the original". **(reference)**
- The W3C's Gamepad specification, `https://www.w3.org/TR/gamepad/`, section "Remapping", the standard gamepad: buttons 0 to 3 the right cluster, 6 and 7 the bottom left and right front buttons, 12 to 15 the left cluster's top, bottom, left and right, axes 0 and 1 the left stick. For the one sentence on a gamepad. **(reference)**

## A. The front page

### What stays

1. The title, the subtitle, the title-screen figure with its caption and the opening paragraph stay as they are. Source: the task; `book/docs/index.md` at the base.
2. The title is *Bringing Back Wings of Fury*, the subtitle *A 1990 Amiga game ported to the browser, and how we know it is faithful*. Source: `book/BOOK.md` 1.

### The preface

3. Wings of Fury is Broderbund's Amiga game of 1990, in which the player flies a Hellcat off a carrier against islands' targets, ships and enemy aircraft. Source: `SPEC.md` 1; `README.md`, Licence; chapters 14, 15 and 16, openings; the manual, page 11 (the Hellcat on the carrier).
3a. A remake is a new program written from watching the old one, and what it does is what its makers saw; an emulator imitates the old computer so that the old program runs unchanged, keeping the machine, the game coming with it. Source: chapter 1, "Three ways to keep a game".
4. The port is a faithful port: the game's own logic taken from the original executable's 68000 machine code, rewritten in C routine by routine, every picture, map, sound and table read from the original disk, and held to the original by comparison; not an emulator and not a remake. Source: chapter 1, "Three ways to keep a game"; `SPEC.md` 1.
5. The port keeps one game rather than the machine, and leaves the game readable: source, notes and proof. Source: chapter 1, "Three ways to keep a game"; `README.md`, "Amiga to Web".
5a. Every ported routine carries the address of its original in an `orig` comment. Source: `CLAUDE.md`, Rules; chapter 1, "Three ways to keep a game".
6. The port is one HTML file that runs from a double click and asks the network for nothing. Source: chapter 1, "One file in the browser"; `SPEC.md` 1.
7. The project is a retro preservation project and a case study in how one can be done today. Source: `README.md`, opening.
8. The owner directed the work; sessions of an AI coding assistant, Claude Code, did the rest. Source: chapter 10, "Who we were".
9. The instruments, not the readers of the listing, were arranged to decide. Source: chapter 10, opening.
10. The owner set the goal and made the decisions that shaped the port (the keys, the order of the milestones, what was dropped, whether to publish). Source: chapter 10, "Who we were".
11. The owner tested what no instrument could, the fades by eye and every sound by ear. Source: chapter 10, "Who we were" and "An honest account".
12. The owner's own Amiga, a PAL machine, confirmed which way the stick climbs, and a film of its screen measured how long a pass takes. Source: chapter 10, "Who we were"; chapter 7.
13. The owner plays the port, and findings from playing became tasks. Source: chapter 10, "Who we were".
14. The sessions read and rewrote every routine of the game's own that the scripts run, named the routines, and wrote the notes and the tests; the tools and the instruments are theirs too, "the rest" of the work. Source: chapter 10, "Who we were" ("The rest was done by sessions") and "An honest account".
15. This book is made the same way: a fact sheet, a draft from it, a fact-check by a reader that had no part in the draft, a readability read, the controller's read, the owner's read as the last gate. Source: chapter 10, "The same method for this book"; `book/BOOK.md` 6.
16. The sessions also got things wrong, in reading, in the instruments and in the tests; chapter 9 tells them and what caught each: an instrument, a reading of what the code really calls, or the owner's eyes, ears and keyboard. Source: chapter 10, "An honest account"; chapter 9, opening.
16a. A reading is a claim until the running original confirms it. Source: chapter 4, opening and "A reading is a claim".
17. The book tells how the game was ported and held faithful, what is inside it, and the code and the tools; it is told as an overview, not a diary. Source: `book/BOOK.md` 1 and its header; chapter 10, opening.
18. The game itself is the page after the front page, playable. Source: `book/mkdocs.yml`, nav; `book/docs/play.md`.
19. The source, the notes with what was observed and what was only read, the tests, the handbook and the history of every change are in the repository; anyone with the ROM, a Mac and the two browsers the tests drive can run the original beside the port. Source: chapter 10, "An honest account".
20. The Kickstart ROM is the one file the repository cannot give, not the project's to publish; the reader places their own copy. Source: chapter 21, opening; chapter 25, "The ROM"; `README.md`, "The Kickstart ROM".
21. The repository is `github.com/sy2002/wof-wasm`. Source: `README.md`, Build; chapter 1.

### How to read this book

22. Three readers: the retro enthusiast who has never read 68000 assembly; the developer who wants to do the same for another game; the future maintainer of the repository, human or AI, for whom the notes in `re/notes/` are the reference and the book only points to them. Source: `book/BOOK.md` 2.
23. Three parts: Part I, From the disk to a faithful game (chapters 1 to 10); Part II, The game inside (11 to 20); Part III, The code, the tools and the build (21 to 25); 25 chapters. Source: `book/BOOK.md` 3; `book/mkdocs.yml`, nav.
24. Chapter 2 is a short primer so that Part I can be read without Part II. Source: `book/BOOK.md` 3, opening.
25. The developer reads Part I and Part III for the method and the tools and follows the source links. Source: `book/BOOK.md` 2.
26. A chapter is meant for one sitting of about twenty minutes. Source: `book/BOOK.md` 2.
27. A chapter opens with what the reader will understand at its end and closes with what it hands to the next, then further reading. Source: `book/BOOK.md` 2 and 4, point 9.
28. Part II's chapters build on each other: chapter 14 opens from chapter 13, chapter 17 from 13 to 16. Source: chapters 14 and 17, openings.
29. A term is introduced once, in bold with a one-line definition, and the bold links its glossary entry; a term used before its chapter is linked in plain text with a short gloss. Source: `book/BOOK.md` 4, point 3.
30. A glossary entry gives the term, its definition in one line, where it is first met and where defined, the note that holds the detail and, where a good page exists, where to read more elsewhere. Source: `book/docs/glossary.md`, introduction; `book/BOOK.md` 5, "Writing a page".
31. The one sidebar, *For the developer*, carries the deeper detail with the link into the source; no chapter requires the source. Source: `book/BOOK.md` 2 and 4, point 6.
32. Listings are extracted from the real sources when the site is built, never retyped, at most about forty lines, each with a first line naming its source file and its lines or its address range. Source: `book/BOOK.md` 4, point 4, and 5, (a); `book/listings.toml`, header.
33. A ported routine is shown as the assembly from the listing beside its C. Source: `book/BOOK.md` 4, point 4.
34. Figures are rendered from the game's data by the port's own library and the project's tools and committed as images; diagrams are SVG, drawn for a black ground. Source: `book/BOOK.md` 4, point 5, and 5, (b) and "Writing a page".
35. Where figures cluster they go into a box titled "The figures". Source: `book/BOOK.md` 5, "Writing a page".
36. A file of the repository named on a page is a link to it on GitHub, which the build checks. Source: `book/BOOK.md` 4, point 2, and 5, "Writing a page".
37. The appendices: the glossary, the keys, the routine inventory, the licence and the game data. Source: `book/BOOK.md` 3, Appendices; `book/mkdocs.yml`, nav.
38. Two interactive pages, the shape browser and the map viewer, need the site served, by `mkdocs serve` or GitHub Pages, and say so when opened as files. Source: `book/BOOK.md` 5, "Interactive elements".
39. The headings of a page and its sections are set in the game's own font, made into a web font by the book's build from the game's data. Source: `book/BOOK.md` 5, (d); `book/docs/stylesheets/book.css`, comment and the `h1, h2` rule; chapter 21, "book/: this book".
40. The figure `font-specimen.png` shows the game's font, `newarmyfont`, every character it has, drawn by the port's `text_render` (`orig 0x015956`), each pixel two wide and four high. Source: `book/figures.toml`, entry font-specimen.
41. Hexadecimal is written in code font, `0x010228`, at the fixed load layout, so that an address in the book is the address in the listing. Source: `book/BOOK.md` 4, point 3; the glossary, Fixed load layout.
42. Keys are named by their position where layouts differ, because the owner's keyboard is German. Source: `book/BOOK.md` 4, point 8; `SPEC.md` 6.2, Input.
43. The manual is cited by page as `original/manual.txt` counts them: a line `PAGE N` begins page N; it is never quoted at length. Source: `book/BOOK.md` 4, point 7.
44. The machine is PAL. Source: `book/BOOK.md` 4, point 8.
45. The project's "we" for the work, "you" for the reader. Source: `book/BOOK.md` 4, point 1.
46. A count that grows with the suite is rounded in the prose and exact in the chapter's fact sheet under `book/facts/`, which names the commit it counted at; fixed counts are exact. Source: `book/BOOK.md` 4, point 2; the fact sheets' heads (e.g. `book/facts/19-front-end.md`, "Counts are of the branch's base, `63ed33b`").
47. Every claim carries how it was found. Source: `book/BOOK.md` 2.

### The ways through, the one table

48. Cover to cover, all 25 chapters; Part I alone, 1 to 10; Part I and Part III, 1 to 10 and 21 to 25; chapter 2 and Part II, 11 to 20; the notes for the maintainer. Source: claims 22 to 28.

## B. The keys

### (a) The stick and fire

49. The arrow keys or W, A, S and D are the stick: forward, back, left, right. Source: `web/input.js` lines 24 to 30 (`KEYS`); `SPEC.md` 6.2, Input; chapter 1, "The keys".
50. Space is the one fire key. Source: `web/input.js` line 29 and the comment at 20 to 23; `SPEC.md` 6.2, Input; chapter 23, "The keys".
51. Enter chooses in a menu, as fire does; the keypad's Enter too. Source: `web/input.js` line 67 (`Enter: 0x44`) and 79 (`NumpadEnter: 0x43`); `re/notes/keys.md`, "Rank selection" (`0x44`, `0x43` choose); chapter 19, "The readers and the commands".
52. The original's keys are the joystick, its button and Return. Source: chapter 1, "The keys". (The page names Return beside Enter; the joystick is chapter 1's.)
53. Fire ends the story scroller and skips the title pictures; it goes on from the briefing to the mission; it ends the high-score screen early. (The page keeps the first three, the high-score screen left off for the page's length.) Source: `re/notes/keys.md`, "Story scroller", "Publisher logo, title, credits", "Briefing" and "End of a mission, game over, high-score display".
54. In the rank selection the cursor keys up and down move the highlight, wrapping round. Source: `re/notes/keys.md`, "Rank selection"; chapter 19, "The readers and the commands". (Off the page, for its length.)
55. A gamepad works as the stick, in a fixed mapping: the left cluster or the left stick moves, the right cluster's four buttons and the two lower front buttons fire; the page names no button by its number (the controller's note 7). Source: `web/input.js` lines 39 to 41 and 156 to 183; `SPEC.md` 6.2, Input; chapter 23, "The keys"; the W3C Gamepad specification **(reference)**.
56. With the vertical flip on, forward and back swap; in the port the flip is a preference the browser remembers. Source: chapter 1, "The remembered flip"; the glossary, Vertical flip.
57. The keyboard assist makes one press one step in the weapon menu and lets a short tap reach the game exactly once; the page switches it on. Source: chapter 1, "The keyboard assist"; chapter 19, "The keyboard assist".

### (b) The game's commands, one row each

58. P or Escape: pause and continue, in flight. Original: Escape. Sources: `src/portkeys.c` lines 56 to 58 (P becomes Escape, any state outside the line editor); `re/notes/keys.md`, "In flight and paused" (`0x45` toggles `pause_flag`, read only by `ingame_keys`); `SPEC.md` 6.2, Input ("`KeyP` pauses and continues", "`Escape` is a second pause key"); chapter 1's table.
59. In the page's own fullscreen Escape leaves fullscreen and pauses, and never continues: the shell drops that Escape and one arriving within half a second after. (The page says "leaves fullscreen and pauses, never continues"; the half second is off the page, for its length.) Source: `web/main.js` lines 225 to 246 (`ESCAPE_AFTER_LEAVE_MS = 500`) and 401 to 417 (the leave rule); `SPEC.md` 6.2, Input; chapter 23, "Fullscreen and the hidden page".
60. V: the vertical flip, in flight or paused. Original: Control-F. Source: `src/portkeys.c` lines 59 to 61; `re/notes/keys.md`, "In flight and paused" (`0x23` with Control) and "The vertical flip, and how long it lasts" (written by `ingame_keys` alone); `SPEC.md` 6.2, Input; chapter 1's table.
61. G: save, on the carrier only, in flight or paused. Original: Control-G. Source: `src/portkeys.c` lines 62 to 64; `re/notes/keys.md`, "In flight and paused" (`0x24`, only while `player_on_deck` is 1); `SPEC.md` 6.2, Input; chapter 1's table; the manual, page 11.
62. L: load, in flight or paused, not while the demo plays; the rank selection's last item opens the load dialog too. Original: Control-L. Source: `src/portkeys.c` lines 65 to 67; `re/notes/keys.md`, "In flight and paused" (`0x28`, only while `demo_mode` is 0) and "Rank selection" (index 7, the load dialog); chapter 19, "The readers and the commands"; the manual, page 11.
63. M: music off and on, in flight or paused; the flag silences the sound effects too; the outer loop clears it before every rank selection. Original: Control-S. Source: `src/portkeys.c` lines 68 to 70; `re/notes/keys.md`, "In flight and paused" (`0x21`) and "The vertical flip, and how long it lasts" (the outer loop clears `opt_music_off`); `SPEC.md` 6.2, Input; chapter 18, the music's key.
64. R: restart, back to the rank selection, while paused or in the briefing; elsewhere R passes on as a plain letter, which does nothing. Original: Control-R. Source: `src/portkeys.c` lines 71 to 76; `re/notes/keys.md`, "Briefing" and "In flight and paused"; `SPEC.md` 6.2, Input; chapter 1's table.
65. C: clear the high scores, deleting the high-score file without a question, while paused. Original: Control-C. Source: `src/portkeys.c` lines 77 to 82; `re/notes/keys.md`, "In flight and paused" (`0x33`, `DeleteFile`, no further check); chapter 17, the high scores; `SPEC.md` 6.2, Input.
66. R and C act only while paused, R in the briefing too, because without Control a stray press could throw a campaign away; the original accepts both while paused, so this narrows it and adds nothing. Source: `SPEC.md` 6.2, Input; chapter 1, "The keys"; `src/portkeys.c`, header. (The page keeps the reason; the narrowing is chapter 1's.)
67. Inside the line editor no command applies and every key passes as it came. Source: `src/portkeys.c` line 54; `SPEC.md` 6.2, Input.
68. Each letter becomes the original's own Control code inside the core, so the original's readers see what they saw on the Amiga. Source: `src/portkeys.c`, header; chapter 1, "The keys".
69. The game reads these commands once a pass in a mission, before the pause test, so they work in flight and paused alike, and Escape can end the pause. Source: `re/notes/keys.md`, "In flight and paused" and "What the port has to keep"; chapter 19, "The readers and the commands".

### (c) The shell's own keys

70. H opens the help screen outside the line editor; while it is up any key closes it, and that key goes no further. Source: `web/main.js` lines 254 to 288 (`KeyH` at 276); `SPEC.md` 6.2, Input; chapter 23, "Over the picture".
71. The help screen is up when the page opens; the first key starts the sound and does nothing else; the screen goes when the sound runs. A click starts the sound too. (The click is off the page, for its length.) Source: `web/main.js` lines 172 to 181, 262 to 272 and 325 to 335; `SPEC.md` 6.2, Input and Audio; chapter 23, "Over the picture".
72. Over a running mission the help screen pauses it and continues it when it closes; a pause it did not ask for stays. Outside a mission the game runs on beneath it. (The page keeps the first clause.) Source: `web/main.js` lines 183 to 199; `SPEC.md` 6.2, Pause, "The help screen's pause"; chapter 23, "Over the picture".
73. F switches the page's own fullscreen on and off, outside the line editor; in it no mouse cursor shows. (The cursor is off the page, for its length.) Source: `web/main.js` lines 213 to 223 and 238 to 240, `KeyF` at 280; `SPEC.md` 6.2, Input; chapter 23, "Fullscreen and the hidden page".
74. Leaving fullscreen, by F, by Escape or by the browser, pauses a mission; P continues. Source: `web/main.js` lines 401 to 417; `SPEC.md` 6.2, Input; chapter 23, "Fullscreen and the hidden page".
75. A page hidden for a second or more brings a mission back paused, with its sign; P continues. Source: `web/main.js` lines 370 to 399 (`HIDDEN_PAUSE_MS = 1000`); `SPEC.md` 6.2, Pause; chapter 23, "Fullscreen and the hidden page".
76. While a mission is paused, whatever paused it, the shell shows `PAUSED` and, smaller, `Press P to continue`. Source: `SPEC.md` 6.2, Pause; chapter 23, "Over the picture". (Off the page, for its length; the page says "P continues".)
77. A key held with Control, Alt or Command goes to the browser, and the game never sees it. Source: `web/input.js` line 125; `web/main.js` line 263; `SPEC.md` 6.2, Input.
78. Inside the line editor H and F are letters. Source: `web/main.js` lines 276 and 280 (`core.lineEditorActive()`); `SPEC.md` 6.2, Input.

### (d) The line editor: the name entry and a file name

79. The line editor edits the name for the high scores, 16 characters at most, and a saved game's file name in the save dialog, 28. Source: `re/notes/keys.md`, "High-score name entry and the dialog's file names"; chapter 19, "The high scores and the name entry".
80. Return or Enter, or fire, accepts and leaves. Source: `re/notes/keys.md`, same section (`0x44`, `0x43`); chapter 19's table.
81. Cursor left and right move by a character; with either Shift to the line's start or end. Source: same.
82. Cursor up or down, or the stick forward or back, leave, to the slot above or below. Source: same.
83. Backspace deletes before the caret, Delete under it. Source: same; `web/input.js` lines 57 and 73.
84. Any other key is converted with its qualifier, Shift and Caps Lock giving capitals, and inserted if there is room; there is no filter. (The page keeps the capitals and the room; the missing filter is off the page, for its length.) Source: same; `web/input.js` lines 84 to 111 (the shell sends both Shifts and Caps Lock, never Control).
85. Right Amiga with X, the original's clear-line, has no key in the port: the shell sends no Amiga key and ignores a key held with Command. Source: `re/notes/keys.md`, same section (`0x32` with right Amiga); chapter 19, "The key layer" (the shell leaves out right Amiga); `web/input.js` lines 54 to 82 and 125.
86. The save dialog turns `:` and `/` into a space and puts `wof.` in front of the name. Source: `re/notes/keys.md`, same section; chapter 19, "The load and save dialog".
87. In the line editor P, V, G, L, M, R, C, H and F are letters. Source: claims 67 and 78.

### (e) The original's commands, from the manual

88. The manual's page 12 lists the original's keys: Escape to pause and continue; Control with R to restart and return to the rank selection, with D for the list of high scores, with C to clear that list after Control-D, with F to flip the vertical control; and, for the Amiga only, Control with G to save and with L to load. Source: `original/manual.txt`, page 12 (read, not quoted).
89. The manual's page 11 lets a game be saved whenever the Hellcat is on the carrier, and loaded from the rank selection or with Control-L in the game. Source: `original/manual.txt`, page 11.
90. Control with S switches the music and is not in the manual. Source: `re/notes/keys.md`, "In flight and paused" (M column empty); `SPEC.md` 6.2, Input; chapter 1, "The keys".
91. Control with D is not in this executable: no reader tests it, and a run with it ends as one without; the port leaves it out. Source: `re/notes/keys.md`, the paragraph after the in-flight table (`test_control_d_does_nothing_anywhere`); `SPEC.md` 6.2, Input; chapter 20, "What the manual promises".
92. Control with C deletes the high-score file at once, in flight or paused, where the manual puts it after Control-D. Source: `re/notes/keys.md`, same paragraph; chapter 17; chapter 20, "What the manual promises".
93. The executable has two more Control keys the manual leaves out, into the crash reporter and a version line, which the port never sends. Source: chapter 20, "What the manual promises"; `re/notes/keys.md`, "In flight and paused" (`0x35`, `0x34`) and "The plain letters the port takes for itself".
94. A cheat sequence hidden in the program, no part of the manual, cannot be typed in the port, because one of its letters is the load key. Source: `SPEC.md` 6.2, Input; chapter 1, "The keys"; chapter 19, "The key layer". (Off the page, for its length; chapter 1 tells it.)

### (f) For the developer

95. The diagnostics key is the key left of 1; it arrives as `Backquote`, or as `IntlBackslash` in Chrome and Safari on a Mac with an ISO keyboard, which report the key right of the left Shift as `Backquote`; both codes open the overlay in every browser, so the key right of the left Shift is a second diagnostics key; neither reaches the game. Source: `web/input.js` lines 32 to 37; `web/main.js` line 343; `SPEC.md` 6.2, Input; chapter 23, "The keys".
96. While the overlay is up: 1 sets the score to 5,000, enough to beat the tenth row, so that the name entry comes; 2 opens the save dialog at the next rank chosen; 3 the load dialog the same way; 4 switches `main`'s argument on and off, which records the following games as the demo `wofdemo`; 5 selects PAL; 6 NTSC; 7 steps the stereo width through the full width, 0.75, 0.5 and 0.25, and remembers it. Source: `web/main.js` lines 347 to 366; `web/audio.js` line 28; `SPEC.md` 6.2, Input (1 to 4) and 6.5 (7); `re/notes/porting-m3.md` (5 and 6); chapter 23, "The keys" and "What the shell stores".
97. The development keys work only behind the overlay, so that a digit typed into a name never goes to the shell, and none of them is the game's. (The page says they are behind the overlay and none is the game's.) Source: `web/main.js` lines 336 to 341; `SPEC.md` 6.2, Input; chapter 23, "The keys".
98. The function keys and Help are left unmapped, so that reload and the developer tools stay with the browser. Source: `web/input.js` lines 50 to 53; `SPEC.md` 6.2, Input.
99. No modifier key is ever mapped: with Control as fire and W as up, firing while climbing would be Control with W, which closes the tab and which a page cannot prevent. Source: `SPEC.md` 6.2, Input; `web/input.js` lines 20 to 23; chapter 1, "The keys".
100. The shell maps `KeyboardEvent.code`, a key's position, to the Amiga's raw key codes, also positional. Source: `web/input.js` lines 43 to 54; `SPEC.md` 6.2, Input; chapter 19.
101. The places: `src/portkeys.c` (the key layer), `web/input.js` (the map), `web/main.js` (the shell's keys), `re/notes/keys.md` (the original's commands state by state). Source: the files.

## C. The routine inventory

102. The routine inventory is `re/functions.csv`; chapter 4 defines it; the glossary has the entry. Source: chapter 4, "The inventory"; the glossary, Routine inventory.
103. The same run of `tools/disasm.py` that makes the listing makes the inventory, from the program and the hand-kept names; it is committed. Source: `tools/disasm.py`, docstring; chapter 4, "The inventory".
104. The status column is the one kept by hand; every regeneration carries it over and recomputes the rest; a routine new to the inventory starts as `todo`. Source: `SPEC.md` 7.4, last paragraph; `CLAUDE.md`, Rules; `tools/disasm.py` lines 542 to 564; chapter 4.
105. `tests/test_generated.py` holds the committed inventory to its regeneration, byte for byte. Source: `CLAUDE.md`, Rules; `tests/test_generated.py` lines 26 to 33; chapter 4, "Names".
106. Read it with a CSV reader: its strings column holds commas. Source: chapter 4, Further reading; chapter 25, "Reading a routine".
107. Its columns: `addr`, `name`, `kind`, `span`, `frame`, `a5_args`, `far_slot`, `callers`, `calls`, `os_calls`, `globals`, `strings`, `status`. Source: `re/functions.csv`, header.
108. The address is six hexadecimal digits at the fixed load layout; the table shows it as `0x` and six upper-case digits, as the book writes addresses. Source: `re/functions.csv`; `book/BOOK.md` 4, point 3.
109. A routine without a name is `sub_` and its address in six lower-case hexadecimal digits: 171 of them. Source: CSV read; chapter 4, "Names".
110. The kind is `C` for a routine whose first instruction is `link a5`, compiled by the C compiler, and `asm` for any other, written by hand: 223 and 393. Source: `tools/disasm.py` line 553 (`0x4E55`); CSV read; chapter 4, "Compiled C and assembly written by hand".
111. The span is the routine's size in bytes, from its entry point to the next routine's, so the spans tile the code: 616 spans adding up to 77,644 bytes, from `0x010000` to `0x022F4C`. Source: `tools/disasm.py` line 556 (`span=fend[fa] - fa`); CSV read; chapter 4, "The inventory" and its opening (77,644 bytes).
112. A routine that falls through into the next is cut in two: `ship_at_offset` has 4 bytes. Source: chapter 4, "The inventory".
113. `verified`: ported and held to the original by a test of its own, under the oracle for a pure routine, by other tests for the rest. Source: chapter 4's table; the glossary, Verified; `CLAUDE.md`, Rules; `SPEC.md` 7.4, step 4.
114. `ported`: ported and held by the comparisons of whole runs of the game. Source: chapter 4's table; chapter 25's table.
115. `partial`: ported as far as the scripts run it, the rest marked as stand-ins or, where the reading was sure, ported from it; chapter 25's corrected row, which the controller's note 4 makes the wording, chapter 10's one partial routine being of the second kind. Source: chapter 25's table; chapter 10, "What it took"; chapter 4's table; `SPEC.md` 7.4, step 5.
116. `replace`: the port does the job its own way (the memory, the copper lists, the calls into the floating point). Source: chapter 4's table; `SPEC.md` 6.6 and 7.4, step 5.
117. `drop`: not needed (the crack's screen, the debug reporters). Source: chapter 4's table; `SPEC.md` 6.6.
118. `todo`: no status set; most are the C library and the system's glue at the end of the code, or code with no caller, on which nothing had to be decided. Source: chapter 4's table and the paragraph after it; chapter 10, "What it took"; chapter 21, "re/: the reading". At `7b8216a`, by a CSV read: of the 210, 116 lie from `0x0215D8` on, 64 have no caller, 166 are one or both, so "most" holds (see "Found on the way").
119. The counts at `7b8216a`: `verified` 167, `ported` 155, `partial` 1, `replace` 47, `drop` 36, `todo` 210; 616 in all. Source: CSV read (`collections.Counter`); chapter 10's table; chapter 25's table.
120. The table on the page is made from the file every time the site is built, and the book's check holds the committed table to it. Source: the generator planned, section F.

## D. The licence and the game data

121. The code and the tools, `src/`, `web/`, `tools/`, `tests/` and the build, are free software under the GNU General Public License, version 3 or later, `LICENSE`. Source: `README.md`, Licence; `SPEC.md` 1 and 2.
122. The prose, `SPEC.md`, the notes in `re/notes/` and the book in `book/`, is under Creative Commons Attribution-ShareAlike 4.0 International, `LICENSE-CC-BY-SA-4.0`. Source: `README.md`, Licence; `SPEC.md` 2; `book/BOOK.md`, header.
123. `LICENSE` is the GNU General Public License, version 3, of 29 June 2007; `LICENSE-CC-BY-SA-4.0` is Attribution-ShareAlike 4.0 International. Source: the two files' first lines.
124. The game data is covered by neither: everything under `original/` (the disk image, the files extracted from it, the manual's text), the listings `re/Wings.lst` and `re/songplay.lst`, which reproduce the executable's code, the contact sheets in `ref/sheets/`, and the game data embedded in `dist/wof.html`. Source: `README.md`, Licence.
125. For the book: the figures rendered from the game's data and the listings taken from its executable are the game's, under the same reservation as `original/`; so is the game embedded in the site. Source: `book/BOOK.md`, header; `book/mkdocs.yml`, copyright; `book/docs/play.md`.
126. Wings of Fury is the work of its authors and publisher, Broderbund, 1990; it is kept for preservation, and no right to it is granted. Source: `README.md`, Licence.
127. The Kickstart ROM is not in the repository at all; it is the Amiga's system, from which the build takes the system font and the key conversion; the reader places their own copy. Source: `README.md`, "The Kickstart ROM" and Licence; chapter 25, "The ROM"; chapter 1, "One file in the browser"; the glossary, Kickstart.
128. What the GNU GPL asks of one who distributes copies: to pass on the same freedoms, to make sure the recipients receive or can get the source code, and to show them these terms. Source: `LICENSE`, preamble; the GNU Project's page **(reference)**.
129. What CC BY-SA 4.0 asks: appropriate credit, a link to the licence and an indication of changes; and contributions built on the material under the same licence. Source: Creative Commons' deed **(reference)**.
130. Elsewhere: `https://www.gnu.org/licenses/gpl-3.0.html` and `https://creativecommons.org/licenses/by-sa/4.0/`, each fetched once. Source: the fetches above.

## E. The specimen retired

131. `book/docs/specimen.md` is deleted and its nav entry, `Specimen: specimen.md`, removed from `book/mkdocs.yml`; nothing else of the nav changes. Source: the task; `book/BOOK.md` 5, "Writing a page" ("goes once the chapters show them all").
132. What only the specimen showed: the figures `title-credits.png` and `shapes-torpedo.png`, and `font-specimen.png`; the listings `c/wof_colour_lerp.c`, `asm/draw_world_record.lst` and `js/convert.js`. Every other figure and listing it showed is shown by a chapter (`mission-start` and `title-logo` by chapter 1, `mission-palettes` by chapter 2, `map-a` and `py/fields.py` by chapter 13, `asm/colour_lerp.lst` by chapter 4). Source: a search of the pages for each file name.
133. `font-specimen.png` stays, shown on the front page in "How to read this book" beside the sentence on the headings' font; the other two figures and the three listings go from `book/figures.toml` and `book/listings.toml` with their committed files. Source: the task (the choice is the writer's).
134. A committed file that no entry makes is reported as `stale` by `--check` (`book/tools/common.py`, `compare`) and removed by the generators' write (`replace_tree`), so an orphan fails the check. Source: `book/tools/common.py`.
134a. Six listings had entries but were shown by no page at all, the specimen included: `asm/rpck_unpack.lst`, `c/wof_rpck_unpack.c`, `c/wof_text_width.c`, `js/Core.vblank.js`, `py/Map.py`, `py/to_indexed.py`; each confirmed unused by `grep -rl "listings/<kind>/<name>" book/docs` and removed from `book/listings.toml` with its committed file (the controller's note 3). Source: the search; the controller's note 3.

## F. The generator planned

135. `book/tools/routines.py`, in the shape of `book/tools/suite.py` (as made: the kind as the CSV holds it, `C` or `asm`; the span right-aligned with a thousands comma; the file 32,174 bytes and 636 lines at `7b8216a`): reads `re/functions.csv` with the csv module and writes `docs/generated/tables/routines.md`, first a table of the six statuses with their counts and the total, then the inventory, one row a routine in the file's order, the address as `0x......` in a code span, the name in a code span, the kind, the span and the status, each table with a caption line; `--check` makes it into a temporary directory and compares; `--out DIR`; exit 0, 1 (a difference), 2 (a status outside the six, or the file missing). Source: the task; `book/tools/suite.py`.
136. Its step goes into `book/tools/build.py` after `suite`, in the build and in `--check`. Source: the task.
137. `book/tools/suite.py`'s `compare` and `replace_tree` work on the whole of `docs/generated/tables/`: a second generator's file there would be `stale` to it, and its write would delete that file. Both generators therefore compare and replace only their own files, through an argument the common module's two functions gain. Source: `book/tools/common.py`; `book/tools/suite.py`, `main`.
138. The page includes the generated file with one snippet line outside any fence, which `exclude_docs` keeps out of the site's pages. Source: `book/BOOK.md` 5, "Writing a page"; `book/mkdocs.yml`, `exclude_docs`.

## G. What the pages leave to the chapters

139. The definition of faithful in three parts, the instruments, the arrangement of the sessions and what it took: chapters 1, 5 to 9 and 10. The preface names them and links them.
140. How the key layer, the assist, the flip and the shell's keys work inside: chapters 1, 19 and 23. The keys page names a key and its condition and links them.
141. What each routine does: the notes and the chapters; the inventory names it and its status.
142. The ROM's identity and where to get it: chapter 25 and `README.md`; the licence page says in one sentence that the reader brings it.

## H. Where the sources disagree on the keys

Chapter 1's table ("The keys"), chapter 19's key layer table ("The key layer"), chapter 23's table of the shell's keys ("The keys"), `SPEC.md` 6.2 Input, `re/notes/porting-m3.md`, `src/portkeys.c` and `web/main.js`, compared row by row. For the controller; the chapters are not edited here.

1. **The development keys.** `web/main.js` has seven, 1 to 7. `SPEC.md` 6.2 Input lists 1 to 4 (5 and 6 nowhere in 6.2; 7 in 6.5). Chapter 19, "The key layer", names a score, either dialog and PAL or NTSC, that is 1, 2, 3, 5 and 6, leaving out 4 (the demo's recording) and 7 (the stereo width). Chapter 23's table has all seven. `re/notes/porting-m3.md` lists 1 to 3 and 5, 6.
2. **When the commands act.** Chapter 19's key layer table gives "always" for P, V, G, L and M, which is when the layer rewrites them; the commands themselves act only where `ingame_keys` reads them, in flight or paused (`re/notes/keys.md`). Chapter 1's table and `SPEC.md` give V and L no condition; the keys page gives "in flight or paused" for both.
3. **L and the demo.** Chapter 19's readers table says the load is not taken while a demo plays (`re/notes/keys.md`: only while `demo_mode` is 0); chapter 1's table and `SPEC.md` 6.2 say nothing of it.
4. **M while paused.** Chapter 1's table and the help screen say "in flight"; `SPEC.md` 6.2 says Control-S "is read only in flight, by `ingame_keys`". `ingame_keys` runs while paused too, so M acts while paused as well (`re/notes/keys.md`, "In flight and paused"). Not a contradiction if "in flight" covers a paused mission, as chapter 19's "In flight and paused" row suggests; the keys page says "in flight or paused".
5. **Escape continues.** Chapter 1's table gives "P, or Escape: pause and continue". In the page's own fullscreen Escape leaves it and pauses, and is dropped as a key, so it never continues there (`SPEC.md` 6.2 Input, `web/main.js` 225 to 246); the help screen's list says "Escape: pause" only. Chapter 1 is right outside the page's fullscreen.
6. **Escape's original key.** Chapter 1's table: Escape; chapter 19's key layer table: P becomes Escape "always", "Escape works too". The same; no disagreement.
7. Every other row agrees across the three: the stick, Space, Enter, G on the carrier, R paused or in the briefing, C paused, H, F, no modifier, the function keys and Help unmapped.

The controller's decision (note 5): the keys appendix is the player's authority and states the conditions as the code and `re/notes/keys.md` have them; `SPEC.md` 6.2 gains the development keys 5, 6 and 7 at the merge; chapter 19's sentence on the development keys is corrected in the whole-book pass; chapter 1's table stays.

## I. README's silences on the licences

`README.md`, Licence, names the code and the tools by their directories, the prose by its files and directories, and the game data by its places. It is silent on, and so are the pages:

1. `CLAUDE.md` and `CONTROLLER.md`, the handbook files, and `README.md` itself: prose, but not in its list.
2. The hand-kept files of `re/`: `re/names.txt`, `re/libbases.txt`, `re/songplay_names.txt`, `re/tables.toml`; and the generated `re/functions.csv`, which is neither listed as game data nor as code.
3. `tools/fd/`: the seven library lists copied from amitools, which its `ORIGIN.txt` says is under the GPL v2, inside `tools/`, which README puts under GPL-3.0-or-later.
4. `ref/title.png`, the title screen rendered by the port, beside the contact sheets README names.
5. The book's code, `book/tools/`, `book/hooks/` and `book/docs/javascripts/`, which README's "the book in `book/`" puts under the prose's licence.
6. The book's web font, `book/docs/fonts/wof-newarmy.woff`, and the interactive elements' data under `book/docs/generated/browser/` and `book/docs/generated/maps/`, all made from the game's data, which `book/BOOK.md`'s header ("the figures rendered from the game's data and the listings taken from its executable") does not name.
7. `requirements.txt` and `book/requirements.txt`; `tests/runs/` (chapter 21 says they stand under the code's licence, `README.md` only by `tests/`).

## Found on the way

1. Chapter 4, "The inventory", says of the `todo` routines that 117 lie at the end of the code and 67 have no caller; chapter 10, "What it took", says "most of the 215". At `7b8216a` there are 210 `todo` routines, 116 from `0x0215D8` on, 64 without a caller, 166 either (CSV read): chapter 10's fact sheet counted at a base with `drop` 31 and `todo` 215, and five routines have gone from `todo` to `drop` since; chapter 10's table and chapter 25's carry the new counts, the two sentences the old ones.

## Unsourced

The outline's claims that have no source, kept out of the pages or narrowed to what the sources say:

1. That Part II's chapters can be read "in any order after chapter 2": no source says so, and the chapters' openings build on the chapters before them (claim 28). The page says Part II reads best in order and that a subject's chapter can be read alone with the glossary for the terms it takes from earlier ones.
2. That the figures are rendered "by the port's library" alone: `book/BOOK.md` 5 (b) names the native library and the tools (`tools/ppkc.py`, `tools/map_decode.py`); the page says both.
