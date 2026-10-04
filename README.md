# Wings of Fury

*Broderbund's 1990 Amiga classic, brought back as a single HTML file: not emulated, not remade, but ported routine by routine from the original 68000 executable, and held to the original tick for tick. [Click here to play.](https://sy2002.github.io/wof-wasm/play/wof.html)*

![](ref/title.png)

Open `dist/wof.html` (download it and double-click the `.html` file locally or [click here](https://sy2002.github.io/wof-wasm/play/wof.html)) and you are on the carrier's deck in 1944: the original's artwork, its sound effects and its music, in your browser, nothing to install. Under the hood there is no Amiga emulator. The game's own logic was taken out of the executable's machine code and rewritten in C, one routine at a time, and runs as WebAssembly; a small JavaScript shell gives it a screen, a sound chip and a keyboard.

What makes it faithful is the method, not just the care. The original executable itself ran headless under emulation beside the port, and the two were compared after every logic tick and every drawn frame, over more than sixty scripted missions on all fifteen maps, through whole campaigns, saved games and the demo: the same game state, byte for byte; the same drawing calls with the same palettes; the same sound sample started on the same channel at the same moment. The flight model runs on the Amiga's own floating-point arithmetic, bit for bit. The speed is the one measured on a real PAL Amiga. The enemy pilots, the ships' gunners, the soldiers running for the dug-outs do exactly what they did in 1990, down to a bug the game always had. What was changed on purpose fits in one short list: the keys a browser allows, menus that take a tap where the original wanted a held stick, and a remembered preference for the stick's sense.

The picture is as pixel-identical as a modern screen allows: the drawing routines are the original's, ported and held to a model of the Amiga's blitter, and what they draw is shown in the Amiga's own pixel aspect, every pixel crisp, at whatever size your window has. In a way it is better than the disk in an emulator: no emulator in between, no disk to boot, no settings to get right, just the game as it was, at the browser's full frame rate, with the sound and the music played by the original's own sound engine and music player, ported with the rest.

It is a retro preservation project, and a case study in how one can be done today: the tools, the notes, the disassembly and the tests that hold the port to the original are all in this repository, and the book about the way, *Bringing Back Wings of Fury*, is in `book/` (below).

## Play

Open [https://sy2002.github.io/wof-wasm/play/wof.html](https://sy2002.github.io/wof-wasm/play/wof.html) in Chrome, Firefox or Safari. It runs from the file itself and loads nothing from anywhere. You can also [download dist/wof.html](dist/wof.html) and run it locally by just double-clicking the `.html` file. The keys are on its help screen, which is up at the start and comes back with H; any key starts the sound and the game. Safari keeps the keyboard in its address bar for a page opened from a file, so there click into the page once first.

## Build and verify

### Prerequisites

- A POSIX shell with `git`: macOS, Linux, or Windows with WSL or Git Bash. The project was developed and is tested on macOS.
- Python 3.11 as `python3`. Everything else the build needs is pinned in `requirements.txt` and installed into `.venv` by the setup, the WebAssembly compiler (zig, as the `ziglang` package) among it; no system compiler is needed for the page.
- The Kickstart 1.3 ROM image, which you place yourself (next). It is not in the repository.
- For the tests only: Node, Google Chrome and Firefox, and macOS, because the native library the tests load is built with Apple clang as a `.dylib`. On another system the page builds and the suite does not.

### The Kickstart ROM

The image the project uses is Kickstart 1.3, revision 34.5, the A500 and A2000 image (exec 34.2 of 28 October 1987), 262,144 bytes, MD5 `82a21c1890cae844b3df741f2762d48d`, SHA-1 `891e9a547772fe0c6c19b610baf8bc4ea7fcb785`. Cloanto's Amiga Forever sells this image, a real Amiga 500 with Kickstart 1.3 gives it too, and a web search for the exact version named above finds further sources. It goes to `original/kick.rom`; the setup checks it, and so does `python tools/rom.py` at any later time. The build takes the system font topaz 8 and the keyboard's key conversion from it, and the test suite runs the original executable's own routines against it.

### Build

```
git clone https://github.com/sy2002/wof-wasm.git
cd wof-wasm
cp /path/to/your/kick.rom original/kick.rom
sh tools/setup.sh
source .venv/bin/activate
```

The setup makes `.venv` from `requirements.txt`, says what is missing, checks the ROM and builds `dist/wof.html`. Without the ROM it stops with a message that says what is needed and where to get it. That is the whole build. The last line activates the environment, which every command below assumes; later builds are then `python tools/build.py` (`--native` adds the test library, `--debug` keeps the core's debug information in the page).

### Verify

The tests run in two phases, the second after the first and never beside it:

```
python -m pytest tests/ --slow -m "not page" -n 8 --dist loadgroup
python -m pytest tests/ --slow -m page
```

The first phase, the emulator tests over the cores, takes about an hour, and the second, the page tests in the two browsers, about twenty minutes; `-n 8` is the number of physical cores, use your machine's (more workers than cores only slow it down). Without the ROM every test but a handful skips, with the same message as its reason. `re/notes/testing.md` has the details.

## The book

*Bringing Back Wings of Fury* is a book about this port: how a 1990 Amiga game was ported routine by routine and how one knows the port is faithful, then what is inside the game, then the code and the tools. It lives in `book/` as a MkDocs site, with a handbook of its own, `book/BOOK.md`. To read it on your machine:

```
sh tools/setup.sh --book
cd book && ../.venv/bin/mkdocs serve
```

and open `http://127.0.0.1:8000/wof-wasm/`. With `--book` the setup does everything it does for the game, installs the book's packages from `book/requirements.txt` into the same `.venv`, and builds the site once with `mkdocs build --strict`. It does that before it looks for the ROM, so a clone without the ROM still gets the book; without `--book` it installs none of the book's packages.

Reading and building the site need only Python and those packages, no ROM: the listings, the figures and the web font of the headings are generated beforehand from the real sources and committed. Regenerating them, `.venv/bin/python book/tools/build.py`, needs the ROM and the built repository (`python tools/build.py --native`, on macOS), as the tests do, and `book/tools/build.py --check` makes them all again in a temporary directory and holds the committed files to that regeneration, byte for byte. `book/site/` is the built site and is never committed.

The book's packages are pinned whole in `book/requirements.txt`, the ones they pull in as well, so that every clone builds the site with the same set and the engine stays at MkDocs 1.6.1: a future MkDocs 2.0 is never pulled in by accident.

The site is published at [https://sy2002.github.io/wof-wasm/](https://sy2002.github.io/wof-wasm/) by the workflow `.github/workflows/book.yml`. On every push to `main` it installs `book/requirements.txt`, runs `mkdocs build --strict` in `book/` and deploys `book/site/` with GitHub's Actions Pages flow, from the committed files alone, so it needs no ROM, no compiler and no browser; the port's build and tests stay out of CI, since both stop without the ROM. Its actions are pinned to full commit SHAs. For the workflow to deploy, Pages has to be enabled once in the repository's settings (Pages, Build and deployment) with "GitHub Actions" as the source.

## Where things are

- `SPEC.md`: the specification, the porting rules and the milestones.
- `src/`: the C core. `web/`: the shell in JavaScript. `tools/`: the build, the disassembler, the headless original and the 68000 oracle. `tests/`: the suite.
- `re/`: the annotated disassembly (`re/Wings.lst`, `re/songplay.lst`), the names, the function inventory, and the notes on every subsystem (`re/notes/`).
- `ref/sheets/`: contact sheets of the game's artwork.
- `original/`: the disk image, the files extracted from it and the manual's text, plus the ROM you place.
- `dist/wof.html`: the built game.
- `book/`: the book about the port, *Bringing Back Wings of Fury*, as a MkDocs site: its handbook, its pages, and the tools that extract its listings and render its figures from the real sources (`book/BOOK.md`).

## Amiga to Web

Retro preservation has two established ways of keeping a machine's games playable: software emulators, which recreate the machine in a program, and FPGA recreations of the machine itself, such as the Amiga cores for the MEGA65 and the MiSTer. This project hints at a third breed beside them: preserving one game rather than the machine, by carrying its own logic over into a form today's computers run natively, and proving the result against the original in a way one can read and repeat. It keeps the work of art without keeping the machine, and it is the one way of the three that leaves the game readable, as source, notes and proof, to whoever comes after.

It could also be done again. Take Wings of Fury out of this repository and most of it is still standing: the instruments that read an executable and run it headless with the operating system stubbed, the runtime that gives a program an Amiga without the Amiga, the shell that gives it a screen and a sound chip in a browser, the test harness, and the method, written down with every mistake that was made once and the instrument that caught it. Two fifths of this project built those, three fifths ported the game; for the next game of the same construction, the two fifths are already there.

Hence the idea, not started yet, of a template repository, "Amiga to Web": clone it, name it after the game, place the Kickstart ROM and the disk image, open the sessions the handbook names, say "start", and come back to the plan and the questions. Not a button, because a port like this one needs its owner for the decisions, the look and the listen, and a budget; but a way of doing again what was done here once, for the class of Amiga games built as this one is, proven the day a second game goes through it. What is reusable, what is each game's work, which games the method reaches and the shape such a template could take are in `re/notes/amiga-to-web.md`.

## Licence

The code and the tools of this repository (`src/`, `web/`, `tools/`, `tests/`, the build) are free software under the GNU General Public License, version 3 or later (`LICENSE`). The prose, that is `SPEC.md`, the notes in `re/notes/` and the book in `book/`, is under Creative Commons Attribution-ShareAlike 4.0 International (`LICENSE-CC-BY-SA-4.0`).

The game data is covered by neither: everything under `original/` (the disk image, the files extracted from it, the manual's text), the disassembly listings `re/Wings.lst` and `re/songplay.lst`, which reproduce the executable's code, the contact sheets in `ref/sheets/`, and the game data embedded in `dist/wof.html`. Wings of Fury is the work of its authors and publisher (Broderbund, 1990); it is kept here for preservation, and no right to it is granted. The Kickstart ROM is not in the repository at all (above).
