# Fact sheet: chapter 1, What faithful means

Every claim the chapter makes, one line each, with its source, in the order of the chapter. A claim without a source goes to the list at the end and stays out of the draft. Counts that grow with the suite are exact here, with their commit, and rounded in the prose; fixed counts are exact in both.

## Opening

1. Wings of Fury is Broderbund's Amiga game of 1990. Source: `SPEC.md` 1, Goal.
2. Most of the instruments have a chapter of their own in Part I: the oracle (5), the headless original (6), the comparisons (7, 8); the sound log is chapter 18 and the tests chapter 24. Source: `book/BOOK.md` 3.

## Three ways to keep a game

3. Retro preservation has two established ways of keeping a machine's games playable: software emulators and FPGA recreations; the MEGA65 and the MiSTer have Amiga cores. Source: `README.md`, "Amiga to Web".
4. An emulator recreates the machine in a program, on which the original program runs unchanged. Source: `README.md`, "Amiga to Web"; the term's definition in the book's words.
5. An FPGA recreation rebuilds the machine itself in programmable hardware, on which the original program runs unchanged. Source: `README.md`, "Amiga to Web"; the term's definition in the book's words.
6. A remake is a new program made to look and play like the old one, from watching it. Source: the term's definition in the book's words, set against `SPEC.md` 1 ("not re-imagined from observation").
7. The port is a third way, tried for one game, as `README.md` says it "hints at a third breed": one game rather than the machine, its own logic carried into a form today's computers run natively and proved against the original. Source: `README.md`, "Amiga to Web".
8. The logic is ported from the original 68000 executable routine by routine, not re-imagined from observation; no Amiga emulator runs in the page. Source: `SPEC.md` 1, Goal; `README.md`, opening.
9. Every picture, map, sound and table is read from the original disk. Source: `SPEC.md` 1, Goal.
10. The faithful port keeps the work of art without the machine, and of the three ways it alone leaves the game readable, as source, notes and proof. Source: `README.md`, "Amiga to Web".
11. The repository is `github.com/sy2002/wof-wasm`, and the book lives in it under `book/`. Source: `README.md`, Build (the clone line) and "Where things are"; `SPEC.md` 2.
12. The executable is one file of 94,292 bytes; its code falls into 616 routines, 223 compiled from C, the rest assembly. Source: `SPEC.md` 3.1 and 3.2; checked with `stat` and with `re/functions.csv` read by `csv.DictReader` (616 rows: kind C 223, asm 393).
13. Every routine the game runs was read, named and rewritten in C, and every ported routine carries the address of its original; the rest, dead code and the Amiga's own machinery, was left. Source: `CLAUDE.md`, Rules (the `orig` comment); `SPEC.md` 6.6 and 7.4; `re/functions.csv`, status column at `fe4e557` (verified 166, ported 153, partial 1, replace 42, drop 31, todo 223).
14. How it was known which routines the game runs is chapter 8, the reach map. Source: `book/BOOK.md` 3, chapter 8; `SPEC.md` 7.4, step 5.

## The definition

15. Logic: fed the same seed and the same stream of input bytes, the port's game state matches the original's after every logic tick. Source: `SPEC.md` 1, "Definition of faithful", point 1.
16. The comparisons give both sides the same keys as well as the same input bytes. Source: `SPEC.md` 8, "Front end" (keys with their qualifiers replayed) and "Whole game, logic" (the scripted controller); `re/notes/headless.md`, "Input".
17. One logic tick per input byte, one input byte every fourth VBlank: 12.5 ticks a second on PAL, 15 on NTSC, the machine the game was designed for. Source: `SPEC.md` 3.3.
18. A PAL machine shows 50 pictures a second, an NTSC machine 60. Source: `SPEC.md` 6.2, Clock.
19. The program never checks the video rate; on PAL it runs at five sixths of the NTSC speed. Source: `SPEC.md` 3.3.
20. The input byte carries the stick's four directions and the button, held or tapped; taking it is the input sample. Source: `SPEC.md` 3.3, "The input byte"; `re/notes/input.md`.
21. The input byte is the only way the stick and the button reach the game's logic; the keyboard is a second, separate way in, through the game's own key handler, for the commands. Source: `SPEC.md` 3.3, "The input byte" ("The keyboard is a separate path").
22. The game's only random source reads the beam position at the moment of the call, so in the original all randomness is CPU timing; the port replaces it by a reproducible stream, and both sides are given the same stream when compared. Source: `SPEC.md` 3.3 and 7.3; `SPEC.md` 8, "Whole game, logic".
23. The simulation is a function of the initial state, the input bytes and the entropy stream, and the interleaving of VBlanks, passes and ticks is a further input. Source: `SPEC.md` 3.3.
24. The game's flight model computes in Motorola's fast floating point, a 32-bit format whose routines live in the ROM's mathffp.library. Source: `SPEC.md` 3.4, the mathffp row; `re/notes/ffp.md`, "The format".
25. The browser's float or double would round differently and the state would drift, so the port reproduces the nine operations bit for bit in integer code, tested against the ROM's routines. Source: `SPEC.md` 7.1, the floating-point point ("Never substitute float or double; rounding differs and the state would drift"); `tests/test_oracle_ffp.py`.
26. Picture: for the same state, the same indexed pixels and the same palette. Source: `SPEC.md` 1, point 2.
27. Colours are 12-bit words in tables of 32 entries, so 4,096 possible colours. Source: `re/notes/display.md`, Summary.
28. The sky above the split, the sea below it, the dashboard and the message line (the ticker, with a ramp of ten colours of its own) each go through their own colours, so the port keeps a palette per row. Source: `re/notes/display.md`, "The play screen line by line" and "How colours change" (ticker ramp); `SPEC.md` 6.6.
29. The picture's 640 by 214 pixels are shown in a box of 1024 : 642, scaled so that every pixel stays sharp and evenly sized, never with square pixels. Source: `SPEC.md` 6.2, Video, "Aspect" and "Size".
30. PAL is the default: the disk comes from a PAL region, its added artwork is 256 lines high, and the real Amiga the port is compared with is a PAL machine. Source: `SPEC.md` 6.2, Video, "Video standard".
31. Sound: the same sample starts on the same channel at the same tick with the same period and volume; the music follows the original player's timing. Source: `SPEC.md` 1, point 3.
32. Paula has four channels, each with its own period and volume. Source: `SPEC.md` 6.5.
33. The sound effects and the music are the game's own samples, played by its own sound engine and music player, ported. Source: `README.md`, the paragraph after the picture; `SPEC.md` 6.5.
34. A pass is one round of the inner loop, which draws one picture; passes run part of the logic, among it the soldiers, which move and die once a pass. Source: `SPEC.md` 3.3, "Runtime model", point 3, and "Passes are not pure rendering".
35. On a real PAL Amiga a pass takes two VBlanks in a quiet scene, measured by filming the machine at 240 frames a second; so two passes go to a tick. Source: `SPEC.md` 3.3, last paragraph; `re/notes/passes.md`, "What the film of the real machine shows"; the two passes to a tick follow from claims 17 and 35.
36. A busy scene, where the original may need three VBlanks a pass, was not filmed; the port keeps two. Source: `re/notes/passes.md`, "What the film of the real machine shows", "Not measured"; `SPEC.md` 3.3.

## One file in the browser

37. One self-contained HTML file that opens from `file://` with a double click and makes no network request. Source: `SPEC.md` 1, Goal.
38. The help screen is up when the page opens and goes with the first key or click. Source: `SPEC.md` 6.2, Video and Audio.
39. Nothing to install, no emulator, no disk to boot, no settings. Source: `README.md`, the paragraph after the picture.
40. All game content is taken from the original disk at build time and embedded: 55 files, in their original formats. Source: `SPEC.md` 1, Goal; `SPEC.md` 5, step 2; `tools/build.py`, "files 55 files".
41. The page is 1,158,496 bytes at `698d0f8`, "about 1.2 megabytes" in the prose (1.16 million bytes). Source: `tools/build.py --native`, its last line.
42. It runs in Chrome, Firefox and Safari; the page tests drive Chrome and Firefox. Source: `README.md`, Play; `SPEC.md` 8, "Page".
43. The game is playable on the site's page "Play the game", and the file is `dist/wof.html` in the repository. Source: `book/docs/play.md`; `README.md`, "Where things are".
44. The core is the ported logic in C, compiled to WebAssembly. Source: `SPEC.md` 1, Goal; `SPEC.md` 5, step 3.
45. The shell is the clock that paces the core, the screen, the sound the core mixes played out, the keys, the storage of saved games, and the help screen, the pause sign and fullscreen. Source: `SPEC.md` 6.2, Clock, Video, Audio, Input, Storage, Pause; `SPEC.md` 6.5 (the core mixes Paula's channels).
46. The sources hold code only; every table, name list and text comes from the executable at build time, and the system font and the key table from the ROM. Source: `SPEC.md` 1; `SPEC.md` 5, step 1; `CLAUDE.md`, Rules.

## What was left out

47. The executable carries a crack: the protection check disabled and a text screen added; the game logic is otherwise the retail code. Source: `SPEC.md` 3.1.
48. Out of scope: the crack intro, the crack's text screen and the manual-lookup copy protection. Source: `SPEC.md` 1, "Out of scope".
49. The copy protection was a manual lookup, described in the prose as asking for something only the manual could answer. Source: `SPEC.md` 1, "Out of scope" ("manual-lookup copy protection").
50. The crack's text screen is `crack_text_screen` at `0x01F41A`; the headless original leaves it at once, and the port does not port it. Source: `re/notes/headless.md`, "What runs and what does not"; `SPEC.md` 6.6.
51. The first picture of the title sequence on this disk is the crack group's own; the title is the game's art with the group's copyright line of 1992 along its bottom edge; the publisher's logo is not on the disk. Source: `re/notes/porting-m1.md`, "Findings"; `SPEC.md` 3.1; figure `title-logo`.
52. The port shows what the files hold. Source: `re/notes/porting-m1.md`, "Findings".
53. Not ported, a browser having no use for them: the C runtime's startup, the Workbench handling, the interrupt plumbing, the copper lists' construction (their effect kept through the palette rows), the debug reporter and the crash reporter. Source: `SPEC.md` 6.6.
54. The operating system's services the game needs are replaced by small equivalents: a file system over the disk's files, an arena allocator, the ROM's key table taken at build time. Source: `SPEC.md` 3.4, the dos, exec and console.device rows; `SPEC.md` 5, step 1.

## What went wrong

55. The file of the first picture is called `broderbund`, and the publisher's logo was expected in it; the picture decoder, compared with the original's own on every picture file of the disk, showed the crack's picture and the crack's copyright on the title. Source: `re/notes/porting-m1.md`, "Findings" and "How the tests establish it" (all twelve ILBM files, pixels and colour table); `SPEC.md` 3.1 lists the file as `shapes/broderbund`.

## What was changed on purpose

56. Everything else is the original, its defects included; the departures only the code shows are the fixed address under a wreck's explosion on land, "Exit Game" reloading the page, and the seed file written beside a recorded demo. Source: `SPEC.md` 7.3; `SPEC.md` 6.2, Storage.
57. Those are told in chapters 17 (the demo and its seed file), 20 (the wreck's explosion and the address it takes) and 23 (the storage and the reload). Source: `book/BOOK.md` 3, chapters 17, 20 and 23.
58. The original's commands: Escape pauses; Control with R, C, F, G and L restarts, clears the high scores, flips, saves and loads; Control-S switches the music and is not in the manual. Source: `SPEC.md` 6.2, Input; `re/notes/keys.md`, "The commands"; the manual's last page.
59. The manual's Control-D is not in this executable. Source: `SPEC.md` 6.2, Input; `re/notes/keys.md`.
60. A browser keeps Control with these letters for itself (reload, find, the address bar), and a page cannot prevent all of them. Source: `SPEC.md` 6.2, Input.
61. The port's keys, as the table gives them: arrows or W, A, S, D; Space; Enter beside fire (the original's menu takes Return and Enter); P and Escape; V; G on the carrier only; L; M in flight, silencing the effects too; R while paused or in the briefing; C while paused; H; F. Source: `SPEC.md` 6.2, Input; `re/notes/porting-m3.md`, "The port's own layer"; `re/notes/keys.md`, "Rank selection".
62. R and C act only while paused (R in the briefing too), because without Control a stray key would throw a campaign away; the original accepts both while paused, so this narrows it and adds nothing. Source: `SPEC.md` 6.2, Input.
63. No modifier key is mapped: firing while climbing would be Control-W, which closes the tab. Source: `SPEC.md` 6.2, Input.
64. Keys are taken by position (`KeyboardEvent.code`), as the Amiga's raw key codes are positional, and the book names a key by its place where layouts differ. Source: `SPEC.md` 6.2, Input; `book/BOOK.md` 4, point 8.
65. Each command letter becomes the original's own Control code inside the core. Source: `re/notes/porting-m3.md`, "The port's own layer".
66. Nothing the manual describes is affected; the cheat sequence, no part of the game the manual describes, cannot be typed, because one of its letters is the load command and two debug keys it unlocks are taken as well. Source: `SPEC.md` 6.2, Input; `re/notes/porting-m3.md`, "The port's own layer".
67. In the weapon menu a step costs three input samples: the menu steps on one and ignores the next two; on a keyboard a step takes two or three presses; with the flip on, up on the key moves the menu down. In flight a tap shorter than four VBlanks can fall between two samples and be lost. Source: `re/notes/porting-m4.md`, "The keyboard assist", "What the original does".
68. With the assist, one press is one step in the weapon menu, never flipped; everywhere else a tap shorter than a sample reaches the tick exactly once, never more than a push of that length gives; the flying stays the original's; the core starts with it off and the page switches it on. Source: `SPEC.md` 6.2, Input, "The keyboard assist"; `re/notes/porting-m4.md`, "The keyboard assist".
69. By default the stick pushed forward climbs, established from the hardware decode and stated in the manual's take-off instructions, page 5 (cited, not quoted); the flip exists for players who want a pilot's stick. Source: `SPEC.md` 3.3, "The input byte"; `re/notes/keys.md`, "The vertical flip, and how long it lasts"; `SPEC.md` 6.2, Input, "The vertical flip is a preference". The manual's pages are counted as `original/manual.txt` marks them, a "PAGE N" line beginning page N, as `re/notes/keys.md` cites them.
70. In the original the flip starts off at program start, a restart keeps it, a loaded game sets it to the saved value, and nothing remembers it past the program's end. Source: `re/notes/keys.md`, "The vertical flip, and how long it lasts"; test `test_a_restart_keeps_the_flip_and_a_loaded_game_undoes_it`.
71. The port keeps the flip as a preference that wins over a loaded game, because the owner flies with it on; a core never given the preference behaves as the original, and that is what the comparisons run. Source: `SPEC.md` 6.2, Input; `re/notes/porting-m3.md`, "The vertical flip".
72. The help screen on H lists the port's keys in the player's words; it is up at the start in place of a prompt for the sound, which a browser starts only on a gesture. Source: `SPEC.md` 6.2, Video, Input and Audio.
73. The pause sign shows while a mission is paused, whatever asked for it; the shell pauses when fullscreen is left and when the page comes back from an absence of a second or more. Source: `SPEC.md` 6.2, Pause and Input.
74. F is the page's fullscreen. Source: `SPEC.md` 6.2, Input.

## The sidebars of the keys

75. In a comparison the assist is off and the flip preference is never handed to the core. Source: `re/notes/porting-m4.md`, "The keyboard assist"; `re/notes/porting-m3.md`, "The vertical flip".
76. The game's own flip command is exercised in compared runs: `tests/runs/flight-control-f.json`, `flight-control-f-twice.json`, `paused-control-f.json`, `flight-flip-then-load.json`, `flight-flip-then-restart.json`, and the M5 script `bomb_flip`. Source: `ls tests/runs`; `tools/m5_scripts.py`, `SCRIPTS`.
77. `tests/test_assist.py` repeats the original's table of taps and steps with the assist off. Source: `re/notes/porting-m4.md`, "What the original does".
78. Every letter the port takes was checked against every reader of the keyboard; of H, F and V none is taken plainly outside the line editor, where they are letters, except F as a cheat key at `cheat_state` 5, behind the untypeable sequence. Source: `re/notes/keys.md`, "The five readers" and "The plain letters the port takes for itself".
79. The files: `src/portkeys.c` (the layer), `web/main.js` (the shell's keys), `src/assist.c` (the assist); the key left of 1 toggles the diagnostics overlay and never reaches the game. Source: `re/notes/porting-m3.md`, "The port's own layer"; `re/notes/keys.md`, "The plain letters the port takes for itself"; `SPEC.md` 6.2, Input.

## How we know, in brief

80. The original runs beside the port under emulation: the 68000 under Unicorn for the oracle and the headless original. Source: `SPEC.md` 8; `re/notes/headless.md`, opening.
81. The oracle compares an original routine with its port on the same, often random, inputs; the fade's colour arithmetic (`colour_lerp`, `0x016FF6`) on 20,000 random triples; a pure routine gets an oracle test before it counts as verified. Source: `SPEC.md` 7.4, step 4; `SPEC.md` 8, Routine; `re/notes/porting-m1.md`, "How the tests establish it"; `CLAUDE.md`, Rules.
82. 310 oracle tests in eight modules at `698d0f8`, "more than three hundred" in the prose. Source: `pytest tests/test_oracle_*.py --collect-only -q --slow`.
83. The headless original runs the original's code from `main` on: the C startup is not run, nor the crack's text screen; the operating system's calls are stubs; nothing is drawn; the beam position comes from the port's stream; the ROM's mathffp.library and console.device's key conversion and the music player run for real; no game logic is re-implemented. Source: `re/notes/headless.md`, "What runs and what does not", "Game logic uses floating point", "The keyboard needs the ROM too"; `SPEC.md` 8, "Whole game, logic".
84. Compared after every tick and pass: every registered global and table, the drawing calls with their arguments, the entropy reads with their callers, the palette of every output row; in the open loop the port is set to the original's state before each pass, in the closed loop it runs alone from the program's start; a completeness test covers every address the original writes during a mission. Source: `SPEC.md` 8, "Mission, pass by pass"; `tests/m4complete.py`.
85. Mission scripts are recorded schedules of stick, button and key inputs that fly a mission the same way every time. Source: `tools/m4_scripts.py`, docstring (a raw schedule of VBlanks and letters); `tools/m5_scripts.py`, docstring ("the original is deterministic for a given schedule, so the recorded schedule flies the same flight again").
86. Sixty mission scripts (11 of M4, 18 of M5, 25 of M6, 6 of M7) on all fifteen maps; eight runs of loaded games and demos; twenty-one key runs in flight and while paused, two of them without a key (`flight-no-key`, `paused-no-key`) as controls. Source: `tools/reach_observe.py` (`PART2_SCRIPTS`, `m5_scripts_list`, `m6_scripts_list`), `tools/m7_scripts.py` (`SCRIPTS`, `PART2`), `ls tests/runs`; the fifteen maps: `SPEC.md` 9, M6.
87. The attract demo: after 1,800 idle rounds the rank selection plays a recorded game, which a game started with an argument records. Source: `SPEC.md` 3.3, `demo_mode`; `re/notes/demo.md`.
88. The front end is compared VBlank by VBlank. Source: `SPEC.md` 8, "Front end".
89. The sound event log is compared after every pass and tick of every mission script, in both loops. Source: `SPEC.md` 8, "Sound".
90. A demo the port recorded is replayed in the native core and in WebAssembly against a hash of the saved state after every input sample; the native build is the C sources compiled with Apple clang as a library for the tests. Source: `SPEC.md` 8, "Whole game, replays"; `SPEC.md` 2 and 5 (`tests/libwofcore.dylib`).
91. The page tests open the built page in Chrome and Firefox through the browsers' own driver protocols (DevTools, WebDriver BiDi), press keys through the driver, and check requests, console, pixels, display box, clock and sound. Source: `SPEC.md` 8, "Page".
92. 930 tests at `698d0f8`, "about nine hundred" in the prose. Source: `pytest tests/ --collect-only -q --slow`.
93. No whole mission scene is compared pixel by pixel, because the headless original draws nothing; the drawing calls and the palette rows stand for it. Every shape is drawn by the original's `shape_draw` through a model of the blitter and compared pixel by pixel with the port's framebuffer; the model is documented hardware behaviour, not derived from the original. Source: `SPEC.md` 8, "Mission, pass by pass" and "Drawing".
94. Four things rest on documented behaviour or the owner's eye and ear: the busy scene's rhythm (claim 36; the owner found the port right as it is, `SPEC.md` 3.3); the fade step, CPU time the listing cannot give, two VBlanks in the port, kept without a film (`SPEC.md` 6.3; `CONTROLLER.md`, "Open items"); the music's tempo, resting on the timer latch's low byte at power-up, every song heard and found right (`SPEC.md` 6.5; `SPEC.md` 9, the M8 paragraph; `re/notes/music.md`; `CONTROLLER.md`, "Open items"); the directory order, documented behaviour neither a run nor the disk confirmed, which orders the saved games in the load dialog (`SPEC.md` 6.2, Storage; `re/notes/frontend.md`, "The order of the file list").
95. The listing is the original's instructions written out by the disassembler. Source: `SPEC.md` 2 (`re/Wings.lst`); `book/BOOK.md` 3, chapter 4.
96. The detail of these four is in chapters 7 (time: the passes, and the fades by the review's assignment), 18 (the tempo that rests on one assumption) and 20 (the directory order). Source: `book/BOOK.md` 3, chapters 7, 18 and 20.

## Handed to chapter 2

97. Chapter 2 introduces the 68000, chip memory, bitplanes, the copper, the blitter, Paula, the VBlank and the little of AmigaOS the game uses. Source: `book/BOOK.md` 3, chapter 2.

## The chapter references the prose makes, each checked against `book/BOOK.md` 3

| Reference | Where in the prose | The outline's chapter |
|---|---|---|
| Part I | the opening | chapters 1 to 10, the instruments among them (5 to 9) |
| chapter 8 | "Routine by routine" | 8, Porting a mission: the reach map |
| chapters 17, 20 and 23 | "What was changed on purpose" | 17, the demo and the attract mode; 20, the wreck's explosion and its address; 23, the storage |
| chapters 7, 18 and 20 | the end of "How we know, in brief" | 7, Time; 18, the tempo that rests on one assumption; 20, the directory order |
| Chapter 2 | "What comes next" | 2, The Amiga in twenty minutes |

## Counts and where they were counted

| Count | Value | Where, and the command |
|---|---|---|
| tests in the suite | 930 ("about nine hundred") | `.venv/bin/python -m pytest tests/ --collect-only -q --slow` at `698d0f8` |
| emulator tests, page tests | 807, 123 | the same with `-m "not page"` and `-m page` |
| oracle tests | 310, in 8 modules ("more than three hundred") | `.venv/bin/python -m pytest tests/test_oracle_*.py --collect-only -q --slow` |
| mission scripts | 11, 18, 25, 6: 60 | `tools/reach_observe.py` `PART2_SCRIPTS` without the `run:` entries, `m5_scripts_list()`, `m6_scripts_list()`, `tools/m7_scripts.py` `SCRIPTS` |
| loaded games and demos | 8 | `tools/m7_scripts.py` `PART2` |
| key runs | 21, two without a key | `ls tests/runs`, `flight-*.json` and `paused-*.json` |
| maps | 15 | `SPEC.md` 3.1, `maps/a.map` to `o.map`; `SPEC.md` 9, M6 |
| files in the page | 55 | `SPEC.md` 5, step 2; `tools/build.py` |
| page size | 1,158,496 bytes ("about 1.2 megabytes") | `tools/build.py --native` |
| the executable | 94,292 bytes | `stat -f %z original/disk/Wings_of_Fury/Wings` |
| routines | 616, 223 of them C | `re/functions.csv` with `csv.DictReader` |
| ticks a second | 12.5 PAL, 15 NTSC | `SPEC.md` 3.3 |
| the fade's arithmetic | 20,000 random triples | `re/notes/porting-m1.md` |

## Figures

- `three-ways.svg`, drawn by hand under `book/docs/figures/`, its colours from the palettes and checked against them by script.
- `mission-start` (generated): the port's picture of the first mission.
- `title-logo` (generated): the crack's first picture.

## Listings

None.

## Terms and glossary entries

Introduced in chapter 1: attract demo, core, crack, emulator, faithful port, fast floating point, FPGA recreation, headless original, input byte, input sample, keyboard assist, logic tick, mission script, oracle, PAL, palette, pass, pure routine, remake, shell, sound sample, vertical flip, WebAssembly. No bare "sample". Used before their chapter and linked: VBlank, copper, blitter (chapter 2). Defined in passing without an entry: the repository, the native build, the browsers' drivers, the line editor, the listing.

## Sidebars

- What went wrong: the publisher's logo expected from a file's name (claim 55).
- How we know: the changes stay out of what is compared (claims 75 to 78).
- For the developer: the files of the key layer, the shell's keys and the assist, and the sources of the rules (claim 79).

## Left to later chapters

How the executable is read (3, 4); the oracle (5); the headless original (6); time and the film (7); the reach map and the loops (8); the mistakes (9); the way of working and the AI collaboration (the preface, 10); the defects and departures (17, 20, 23); the keys in full (19).

## Unsourced

Kept out of the draft: that `UFXintro` is the crack intro; any date of the crack beyond the 1992 on its pictures; why the port was made from a cracked disk.
