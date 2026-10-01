# Wings of Fury

A faithful port of the Amiga game Wings of Fury, the 1990 Amiga version, to a single HTML file that runs in a browser, with a C core compiled to WebAssembly. The game's logic is ported routine by routine from the original executable, and a headless copy of that executable running under emulation holds the port to the original, pass by pass. It is a retro preservation project.

## Play

Open `dist/wof.html` in Chrome, Firefox or Safari. It runs from the file itself and loads nothing from anywhere. The keys are on its help screen, which is up at the start and comes back with H; any key starts the sound and the game. Safari keeps the keyboard in its address bar for a page opened from a file, so there click into the page once first.

## Build and verify

The project is developed on macOS: the native library the tests load is built with `clang` as a `.dylib`. It needs `python3` (3.11), Node, and for the page tests Google Chrome and Firefox.

1. Place the Kickstart ROM at `original/kick.rom`. It is not part of this repository. The image the project uses is Kickstart 1.3, revision 34.5, the A500 and A2000 image (exec 34.2 of 28 October 1987), 262,144 bytes, MD5 `82a21c1890cae844b3df741f2762d48d`, SHA-1 `891e9a547772fe0c6c19b610baf8bc4ea7fcb785`. Cloanto's Amiga Forever sells this image, and a real Amiga 500 with Kickstart 1.3 gives it too. `.venv/bin/python tools/rom.py` checks the file once the environment exists.
2. Run `sh tools/setup.sh`. It makes `.venv` from `requirements.txt`, says what is missing, checks the ROM and builds `dist/wof.html`. Without the ROM the build stops with a message that says what is needed and where to get it.
3. Run the tests in two phases, the second after the first and never beside it:

```
.venv/bin/python -m pytest tests/ --slow -m "not page" -n 8 --dist loadgroup
.venv/bin/python -m pytest tests/ --slow -m page
```

The first phase, the emulator tests over eight cores, takes about an hour, and the second, the page tests in the two browsers, about twenty minutes. Without the ROM every test but a handful skips, with the same message as its reason. `re/notes/testing.md` has the details.

## Where things are

- `SPEC.md`: the specification, the porting rules and the milestones.
- `src/`: the C core. `web/`: the shell in JavaScript. `tools/`: the build, the disassembler, the headless original and the 68000 oracle. `tests/`: the suite.
- `re/`: the annotated disassembly (`re/Wings.lst`, `re/songplay.lst`), the names, the function inventory, and the notes on every subsystem (`re/notes/`).
- `ref/sheets/`: contact sheets of the game's artwork.
- `original/`: the disk image, the files extracted from it and the manual's text, plus the ROM you place.
- `dist/wof.html`: the built game.

## Licence

The code and the tools of this repository (`src/`, `web/`, `tools/`, `tests/`, the build) are free software under the GNU General Public License, version 3 or later (`LICENSE`). The prose, that is `SPEC.md`, the notes in `re/notes/` and the book in `book/`, is under Creative Commons Attribution-ShareAlike 4.0 International (`LICENSE-CC-BY-SA-4.0`).

The game data is covered by neither: everything under `original/` (the disk image, the files extracted from it, the manual's text), the disassembly listings `re/Wings.lst` and `re/songplay.lst`, which reproduce the executable's code, the contact sheets in `ref/sheets/`, and the game data embedded in `dist/wof.html`. Wings of Fury is the work of its authors and publisher (Broderbund, 1990); it is kept here for preservation, and no right to it is granted. The Kickstart ROM is not in the repository at all (above).
