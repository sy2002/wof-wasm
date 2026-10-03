# Wings of Fury port — working rules

Faithful port of the Amiga game to a single HTML file with a C/WebAssembly core. **Read `SPEC.md` first**; it is the source of truth for goals, architecture, porting rules and milestones. Subsystem knowledge accumulates in `re/notes/`. The session that leads the project, the controller, also reads `CONTROLLER.md`; workers do not need it.

## Commands

Run from the repository root. Always use the project environment, never the system Python.

```bash
sh tools/setup.sh                        # a fresh clone: .venv from requirements.txt, Node and the browsers, the ROM check, the build
.venv/bin/python tools/rom.py            # is original/kick.rom the expected image
.venv/bin/python tools/disasm.py          # regenerate re/Wings.lst and re/functions.csv (about 2 s); commit what it writes
.venv/bin/python tools/skel.py 010228     # control-flow skeleton of one routine (address or name)
.venv/bin/python tools/oracle.py          # 68000 oracle self-test, must print PASSED
.venv/bin/python tools/headless.py run RUN.json --out A.dump   # the headless original; formats, show and diff in re/notes/headless.md
.venv/bin/python tools/reach_observe.py   # which routines and blocks the mission scripts execute in the original; --cold lists the stand-ins owed
.venv/bin/python tools/mdcheck.py SPEC.md # Markdown safety check, run on every .md that was edited
.venv/bin/python tools/build.py --native  # build dist/wof.html, dist/core.wasm and tests/libwofcore.dylib
.venv/bin/python tools/build.py --debug --native   # the same with the debug information kept in the core (the release page leaves it out)
.venv/bin/python -m pytest tests/         # full suite, serially; page tests use Chrome and Firefox and skip a missing browser
.venv/bin/python -m pytest tests/ --slow -m "not page" -n 8 --dist loadgroup   # phase 1: the emulator tests over the cores (about an hour)
.venv/bin/python -m pytest tests/ --slow -m page                               # phase 2, after it, never beside it: the page tests alone (about twenty minutes)
.venv/bin/python tools/junit_compare.py REF.xml PHASE1.xml PHASE2.xml          # the outcome sets of two runs from --junitxml files; re/notes/testing.md
WOF_FIREFOX_VISIBLE=1 .venv/bin/python -m pytest tests/test_firefox.py   # also opens a real Firefox window
```

`tools/build.py` compiles the core with `.venv/bin/python -m ziglang cc -target wasm32-freestanding`; nothing else needs to be installed.

## Session protocol

Work one milestone, or one clearly bounded part of one, per session. The repository is the handover: nothing may live only in a conversation.

- **Start:** read the `SPEC.md` sections for the milestone and every file in `re/notes/` that touches it.
- **Never load `re/Wings.lst` whole.** It is about 1.6 MB. Use `tools/skel.py`, `grep`, or an address range.
- **End:** names into `re/names.txt`, findings into `re/notes/`, `status` in `re/functions.csv`, tests green, and `SPEC.md` corrected wherever it stated something that turned out different.
- **Worker sessions do not ask the user for anything.** When a controller session assigned your task, everything goes to the controller: the report, questions, and any request that needs the user's eyes, ears or decision (a manual test, a listening check, a choice). Put such requests into your report for the controller to relay. The user watches the controller chat and will miss a request made anywhere else.
- **Stop and report instead of retrying** (to the controller if you have one, otherwise to the user) when: an oracle test still fails after two fix attempts; a routine in the hand-written assembly region (`0x010000`–`0x015D62`) is not understood after reading it in full; a change would alter a struct layout, the core interface or a porting rule.

## Rules

- `original/` is read-only ground truth. Never modify, move or delete anything in it.
- `original/` is versioned except `original/kick.rom`, the Kickstart ROM, which is never committed: whoever clones the repository places their own copy, and `tools/rom.py` checks it (Kickstart 1.3, revision 34.5, the A500 and A2000 image, 262,144 bytes, SHA-1 `891e9a547772fe0c6c19b610baf8bc4ea7fcb785`). Without it the build stops and the suite skips, each with the same message. The repository will be published by the owner's decision of 2026-09-30; nothing is pushed to any remote unless the owner asks.
- `dist/` is ignored except `dist/wof.html`, the repository's runnable page. A worker never commits `dist/wof.html` on a task branch; the controller rebuilds it and commits it at every merge, so that the committed page is always the build of the committed sources (the build is deterministic and names no directory of the machine that built it).
- `original/manual.txt` is the game's manual. Read it for intended behaviour and the key commands, and cite it by page; do not paste its text into sources, notes or documents.
- Hand-written sources contain code only. Tables, texts and tuning values come from the original executable at build time (`re/tables.toml`, see `SPEC.md` section 5).
- Port from the disassembly, not from assumptions. `int` in the original is 16 bits; follow `SPEC.md` section 7.1 exactly.
- Addresses always use the fixed load layout: CODE `0x010000`, DATA `0x023000`, A4 `0x02AFFE`.
- `re/Wings.lst`, `re/functions.csv`, `re/songplay.lst` and `ref/sheets/` are versioned and held to their regeneration byte for byte by `tests/test_generated.py`. After changing `re/names.txt`, `re/libbases.txt` or `re/songplay_names.txt`, run `tools/disasm.py` and `tools/disasm_player.py` and commit what they write; after changing the recipe in `tools/ppkc.py`, run `tools/ppkc.py --sheets` and commit the sheets.
- The book under `book/` shows listings, figures and tables made from `src/`, `web/`, `tools/`, `tests/` and `re/` and committed. After a change there run `.venv/bin/python book/tools/build.py --check`; if it differs, run `book/tools/build.py` and commit what it regenerates (`book/BOOK.md`, section 5).
- Never edit `re/Wings.lst` by hand. Put names in `re/names.txt`, library bases in `re/libbases.txt`, then regenerate. The `status` column of `re/functions.csv` is the only hand-edited generated column and survives regeneration.
- Every ported routine carries an `orig 0x......` comment. Pure routines get an oracle test before they count as `verified`.
- When a subsystem is understood, write it down in `re/notes/` so that later sessions do not re-derive it.
- The long printable text blocks in the executable are summarised in the listing on purpose. Read them from the binary by address when the port needs them; do not paste them into source files, notes or documents.
