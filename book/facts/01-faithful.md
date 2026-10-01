# Fact sheet: chapter 1, What faithful means

Every claim the chapter makes, one line each, with its source. A claim without a source goes to the list at the end and stays out of the draft.

## The three ways and the port

1. The established ways of keeping a machine's games playable are software emulators and FPGA recreations of the machine; the MEGA65 and the MiSTer have Amiga cores. Source: `README.md`, "Amiga to Web", first paragraph.
2. An emulator recreates the machine in a program and runs the original program unchanged on it. Source: `README.md`, "Amiga to Web" ("recreate the machine in a program"); the book's definition of the term.
3. An FPGA recreation rebuilds the machine itself in programmable hardware. Source: `README.md`, "Amiga to Web" ("FPGA recreations of the machine itself"); the book's definition of the term.
4. A port of this kind preserves one game rather than the machine: its own logic carried into a form today's computers run natively, and proved against the original in a way one can read and repeat. Source: `README.md`, "Amiga to Web".
5. It keeps the work of art without the machine, and of the three ways it alone leaves the game readable, as source, notes and proof. Source: `README.md`, "Amiga to Web".
6. The game logic is ported from the original 68000 executable routine by routine, not re-imagined from observation. Source: `SPEC.md` 1, Goal.
7. The port is neither emulated nor remade; it runs no Amiga emulator. Source: `README.md`, opening paragraph and the paragraph after the picture.
8. A remake is a new program made to look and play like the old one, from observation of it. Source: the book's definition of the term, set against `SPEC.md` 1 ("not re-imagined from observation").
9. The logic runs in a WebAssembly core written in C; a thin JavaScript shell provides the screen, the sound, the input and the storage. Source: `SPEC.md` 1, Goal; `README.md`, opening.
10. Hand-written sources hold code only; every table, text and tuning value comes from the original executable at build time. Source: `SPEC.md` 1; `CLAUDE.md`, Rules; `SPEC.md` 5, step 1.

## The definition of faithful

11. Logic: fed the same seed and the same stream of input bytes, the port's game state matches the original's after every logic tick. Source: `SPEC.md` 1, "Definition of faithful", point 1.
12. Picture: for the same state, the same indexed pixels and the same palette. Source: `SPEC.md` 1, point 2.
13. Sound: the same sample starts on the same channel at the same tick with the same period and volume; the music follows the original player's timing. Source: `SPEC.md` 1, point 3.
14. The game advances in fixed steps, one logic tick per input byte, one input byte every fourth VBlank: 12.5 ticks a second on PAL, 15 on NTSC. Source: `SPEC.md` 3.3, Runtime model.
15. The input byte carries the stick's four directions and the button, held or tapped; it is the only channel by which the controls reach the game's logic. Source: `SPEC.md` 3.3, "The input byte".
16. The game's only random source reads the position of the screen's beam at the moment of the call; the port replaces it by a reproducible stream of values. Source: `SPEC.md` 3.3; `re/notes/random.md`.
17. A pass is one round of the game's main loop, which draws one picture and also runs some of the game's logic. Source: `SPEC.md` 3.3, "Passes are not pure rendering".
18. On a real PAL Amiga a pass takes two VBlanks in a quiet scene, measured by filming the machine at 240 frames a second; the port takes that number. Source: `SPEC.md` 3.3, last paragraph; `SPEC.md` 6.2, Clock; `re/notes/passes.md`.
19. The game's floating point is Motorola's fast floating point from the ROM's mathffp.library; the port reproduces its nine operations bit for bit in integer code, tested against the ROM's routines. Source: `SPEC.md` 3.4, the mathffp row; `re/notes/ffp.md`; `tests/test_oracle_ffp.py`.
20. The picture is shown in the PAL aspect: a framebuffer of 640 by 214 in a box of 1024 : 642, never with square pixels. Source: `SPEC.md` 6.2, Video, "Aspect".
21. PAL is the default because this disk comes from a PAL region, its added artwork is 256 lines high, and the real Amiga the port is compared with is a PAL machine. Source: `SPEC.md` 6.2, Video, "Video standard".
22. The program never checks the machine's video rate; on PAL it runs at five sixths of the NTSC speed. Source: `SPEC.md` 3.3.
23. The port's colours change per row of the picture, through a palette per row, as the original's copper lists change them. Source: `SPEC.md` 6.6; `re/notes/display.md`, Summary.

## Why the browser and one file

24. The result is one self-contained HTML file that opens from `file://` with a double click and makes no network request. Source: `SPEC.md` 1, Goal.
25. All game content (graphics, maps, sounds, music, fonts, tables, texts) is taken from the original disk image at build time and embedded in the file. Source: `SPEC.md` 1, Goal.
26. The page is 1,158,496 bytes. Source: `tools/build.py --native`, its last line, at `698d0f8`; `SPEC.md` 5 ("below 2 MB").
27. It runs in Chrome, Firefox and Safari, from the file itself. Source: `README.md`, Play.
28. Nothing to install, no emulator in between, no disk to boot, no settings to get right. Source: `README.md`, the paragraph after the picture.

## What was left out

29. Out of scope: the crack intro, the crack's text screen and the manual-lookup copy protection. Source: `SPEC.md` 1, "Out of scope".
30. The executable on this disk carries a crack: the protection check is disabled and a text screen was added; the game logic is otherwise the retail code. Source: `SPEC.md` 3.1.
31. The crack's text screen is `crack_text_screen` at `0x01F41A`; the headless original leaves it at once, and the port does not port it. Source: `re/notes/headless.md`, the stubs table; `SPEC.md` 6.6; `SPEC.md` 3.4, the graphics row.
32. The crack also replaced artwork: `shapes/broderbund` and `shapes/wingstitle` carry the crack group's own pictures, dated 1992, so the publisher's logo is not on this disk. Source: `SPEC.md` 3.1; `re/notes/porting-m1.md`, "Findings".
33. The port shows what the files hold: the first picture of the title sequence is the crack's. Source: `re/notes/porting-m1.md`, "Findings"; figure `title-logo`.
34. Files on the disk that are not part of the game (among them `UFXintro` and `wingt`) are left out of the page; 55 files go in. Source: `SPEC.md` 3.1 and 5, step 2.
35. Not ported, because a browser does not need them: the C runtime's startup, the operating system glue, memory management, the construction of the copper lists (their effect is reproduced through the palette rows), the interrupt plumbing, the Workbench handling, the debug and crash reporters. Source: `SPEC.md` 6.6.
36. Emulating the Amiga's hardware or AmigaOS in the shipped product is out of scope. Source: `SPEC.md` 1, "Out of scope".

## What was changed on purpose

37. The original's commands are Escape for the pause and Control with R, C, F, G and L for restart, clearing the high scores, the vertical flip, save and load; Control-S switches the music and is not in the manual. Source: `SPEC.md` 6.2, Input; `re/notes/keys.md`, "The commands"; the manual's last page.
38. The manual's Control-D, which would show the high scores, is not in this executable, and the port leaves it out. Source: `SPEC.md` 6.2, Input; `re/notes/keys.md`.
39. A browser keeps Control with those letters for itself (reload, find, the address bar), and a page cannot prevent all of them. Source: `SPEC.md` 6.2, Input.
40. The port's keys: P pauses and continues, Escape too; V flips the vertical control; G saves (on the carrier only, as in the original); L loads; M switches the music; R restarts and C clears the high scores, both only while paused (R in the briefing as well); Enter chooses in a menu beside fire; Space is the one fire key; the arrow keys or W, A, S and D move. Source: `SPEC.md` 6.2, Input; `re/notes/porting-m3.md`, "The port's own layer".
41. M acts only in flight, and silences the sound effects as well, as the original's Control-S does. Source: `SPEC.md` 6.2, Input.
42. R and C act only while paused because without Control a stray key would throw a campaign away; the original accepts both while paused, so this narrows the original and adds nothing. Source: `SPEC.md` 6.2, Input.
43. The port's layer rewrites each of its keys into the raw code and qualifier the original's own key readers expect. Source: `re/notes/porting-m3.md`, "The port's own layer".
44. No modifier key may be mapped: firing while climbing would be Control-W, which closes the tab. Source: `SPEC.md` 6.2, Input.
45. The keys are taken by their position (`KeyboardEvent.code`), and the book names a key by its position where layouts differ, such as the key left of 1. Source: `SPEC.md` 6.2, Input; `book/BOOK.md` 4, point 8.
46. Nothing the manual describes is affected; what is lost lies outside the manual: the cheat sequence cannot be typed, because one of its letters is the load command; it stays untypeable by the owner's decision. Source: `SPEC.md` 6.2, Input; `re/notes/porting-m3.md`, "The port's own layer".
47. The vertical flip: in the original it starts off, only the flip command changes it, a restart keeps it, a loaded game sets it to what the saved game holds, and nothing remembers it past the end of the program. Source: `re/notes/keys.md`, "The vertical flip, and how long it lasts"; test `test_a_restart_keeps_the_flip_and_a_loaded_game_undoes_it`.
48. Up on the stick climbs in the original, because the game is seen from the side; the flip swaps forward and back for players who want a pilot's stick. Source: `SPEC.md` 3.3, "The input byte".
49. The port keeps the flip as a preference in the browser's storage, and the remembered value wins over a loaded game; a deliberate divergence, because the project's owner flies with it on. Source: `SPEC.md` 6.2, Input; `re/notes/porting-m3.md`, "The vertical flip".
50. A core that was never given a preference behaves exactly as the original, and that is what the comparisons run. Source: `re/notes/porting-m3.md`, "The vertical flip".
51. The keyboard assist exists because a key is tapped where a joystick is held: the menus should feel as a player expects today while the flying stays the original's. Source: `SPEC.md` 6.2, Input, "The keyboard assist".
52. In the original's weapon menu in the hold a step costs three sampled inputs, so on a keyboard a step takes two or three presses, and with the flip on, up on the key goes down in the menu; in flight a tap shorter than four VBlanks can fall between two samples and be lost. Source: `re/notes/porting-m4.md`, "The keyboard assist", "What the original does".
53. With the assist, one press in the weapon menu is one step, never flipped, and elsewhere a tap shorter than a sample reaches the game exactly once, never more than the original gives a push of that length. Source: `SPEC.md` 6.2, Input; `re/notes/porting-m4.md`, "What the assist does".
54. The assist is off in the core and in every comparison with the original; the page switches it on. Source: `re/notes/porting-m4.md`, "The keyboard assist"; `tests/test_assist.py` repeats the original's table with it off.
55. The shell adds a help screen (H), which lists the port's keys and is up when the page opens, in place of a prompt for the sound. Source: `SPEC.md` 6.2, Video and Input.
56. A browser starts sound only on a gesture of the player's, so the first key or click starts the sound and closes the help screen. Source: `SPEC.md` 6.2, Audio.
57. The shell adds a pause sign over the picture while a mission is paused, and pauses a mission when the page is hidden or fullscreen is left. Source: `SPEC.md` 6.2, Pause and Input.
58. F asks for the page's own fullscreen and leaves it. Source: `SPEC.md` 6.2, Input.
59. No reader of the game takes a plain H, F or V outside the line editor, so the keys the shell takes cost the game nothing. Source: `re/notes/keys.md`, "The plain letters the port takes for itself".

## How we know, as an overview

60. The oracle: one original routine runs under an emulated 68000 and is compared with its port on the same, often random, inputs; required for every pure routine. Source: `SPEC.md` 7.4, step 4; `SPEC.md` 8, Routine.
61. The suite holds 310 oracle tests in eight modules. Counted: `pytest tests/test_oracle_*.py --collect-only -q --slow` at `698d0f8`.
62. The headless original: the original's own code runs from `main` on under emulation, with the operating system's calls stubbed, nothing drawn, the beam position served from the same stream the port uses; no game logic is re-implemented. Source: `SPEC.md` 8, "Whole game, logic"; `re/notes/headless.md`.
63. Mission by mission, the port is compared with the headless original after every tick and every pass, in an open loop (the port set to the original's state before each pass) and a closed loop (the port on its own from the program's start). Source: `SPEC.md` 8, "Mission, pass by pass".
64. Compared after every pass: every registered variable and table, the drawing calls with their arguments, the random reads with their callers, the palette of every row; a completeness test demands that every address the original writes during a mission is compared or listed with its reason. Source: `SPEC.md` 8, "Mission, pass by pass"; `tests/m4complete.py`.
65. The mission scripts: 11 of M4, 18 of M5, 25 of M6 and 6 of M7, 60 in all, on all fifteen maps; besides them 8 runs of loaded games and demos and 21 runs of the key commands during a mission. Counted from `tools/reach_observe.py` (`PART2_SCRIPTS`, `m5_scripts_list`, `m6_scripts_list`, `m7_scripts_list`) and `tools/m7_scripts.py` (`SCRIPTS`, `PART2`); the fifteen maps: `SPEC.md` 9, M6.
66. The front end is compared VBlank by VBlank: every file opened, every music call, every drawing call with its text and position. Source: `SPEC.md` 8, "Front end".
67. The sound event log, one entry per sample start, is compared after every pass and every tick of every mission script in both loops. Source: `SPEC.md` 8, "Sound".
68. A demo the port recorded is replayed in the native core and in WebAssembly against a hash of the state after every input sample. Source: `SPEC.md` 8, "Whole game, replays"; `tests/test_replays.py`.
69. The built page is opened in Chrome and Firefox, driven by key presses through the browser's driver, and checked for only local requests, a clean console, the exact pixels, the display box, the clock and the sound. Source: `SPEC.md` 8, "Page".
70. The suite has 930 tests: 807 emulator tests and 123 page tests, run in two phases. Counted: `pytest tests/ --collect-only -q --slow`, with `-m "not page"` and `-m page`, at `698d0f8`.
71. Not compared: no pixel of a mission scene is compared with the original, because the headless original draws nothing; the drawing calls, the palette rows and a model of the blitter stand for the picture. Source: `SPEC.md` 8, "Mission, pass by pass" and "Drawing".
72. Provisional: how many VBlanks a step of a fade takes on the machine is not established; the port takes two. Source: `re/notes/porting-m3.md`, "The fades, and the one provisional setting"; `re/notes/display.md`, Open.

## What went wrong

73. The specification first called the first picture the publisher's logo; the picture decoder of M1 showed the crack's picture, and the specification was corrected. Source: `re/notes/porting-m1.md`, "Findings"; `SPEC.md` 3.1 as it now reads.

## Handed to chapter 2

74. The terms chapter 2 introduces: the 68000, chip memory, bitplanes, the copper, the blitter, Paula, the VBlank, the little of AmigaOS the game uses. Source: `book/BOOK.md` 3, chapter 2.

## Counts and where they were counted

| Count | Value | Where, and the command |
|---|---|---|
| tests in the suite | 930 | `.venv/bin/python -m pytest tests/ --collect-only -q --slow` |
| emulator tests, page tests | 807, 123 | the same with `-m "not page"` and `-m page` |
| oracle tests | 310, in 8 modules | `.venv/bin/python -m pytest tests/test_oracle_*.py --collect-only -q --slow` |
| mission scripts | 11, 18, 25, 6: 60 | `tools/reach_observe.py` `PART2_SCRIPTS` without the `run:` entries, `m5_scripts_list()`, `m6_scripts_list()`, `tools/m7_scripts.py` `SCRIPTS` |
| loaded games and demos | 8 | `tools/m7_scripts.py` `PART2` |
| key runs during a mission | 21 | `PART2_SCRIPTS`, the `run:` entries (`tests/runs/flight-*.json`, `paused-*.json`) |
| maps | 15 | `SPEC.md` 3.1, `maps/a.map` to `o.map`; `SPEC.md` 9, M6 |
| replays | 1 demo | `ls tests/replays` |
| page size | 1,158,496 bytes | `tools/build.py --native`, last line |
| files in the page | 55 | `SPEC.md` 5, step 2; `tools/build.py`, "files 55 files" |
| ticks a second | 12.5 PAL, 15 NTSC | `SPEC.md` 3.3 |

## Figures

- `three-ways.svg`, new, drawn by hand under `book/docs/figures/`: the emulator, the FPGA recreation and the port side by side, what each keeps and what runs on what.
- `title-logo` (exists): the first picture of the title sequence, the crack's in place of the publisher's logo.
- `mission-start` (exists): the port's picture of the first mission, for the definition's picture part.

## Listings

None. The chapter makes "routine by routine" concrete in words and points to chapter 4 and chapter 5, where the reader has the terms to read a listing.

## Terms and glossary entries

New entries: crack, emulator, FPGA recreation, faithful port, input byte, keyboard assist, logic tick, palette, pass, PAL, remake, sample, shell, core, vertical flip, WebAssembly, the oracle, the headless original.

## Sidebars

- How we know: the changed keys and the assist do not touch what is compared: the assist and the remembered flip are off in every comparison, and the port's keys arrive as the original's own codes (claims 43, 50, 54, 59).
- What went wrong: the publisher's logo that was not there (claim 73).
- For the developer: the keys in the player's words, by position, beside the original's (claims 37, 38, 40, 41, 42), with the places in the source (`src/portkeys.c`, `web/main.js`, `src/assist.c`).

## Left to later chapters

- How the executable is read and named: chapters 3 and 4.
- The oracle in detail, verified, the emulator's own bug: chapter 5.
- The headless original, determinism, the wall clock: chapter 6.
- VBlanks, passes, ticks and the film of the real machine: chapter 7.
- The reach map, the loops, the completeness list, the autopilots: chapter 8.
- The mistakes and their instruments: chapter 9.
- The way of working and the AI collaboration: the preface and chapter 10.
- The keys and the assist in full: chapter 19.

## Unsourced

- None of the claims above. Left out of the draft for want of a source: that `UFXintro` is the crack intro (the specification names the crack intro and lists `UFXintro` as not part of the game, but never says the two are the same), and when exactly the crack was made beyond the date on its pictures.
