# Wings of Fury port — working rules

Faithful port of the Amiga game to a single HTML file with a C/WebAssembly core. **Read `SPEC.md` first**; it is the source of truth for goals, architecture, porting rules and milestones. Subsystem knowledge accumulates in `re/notes/`.

## Commands

Run from the repository root. Always use the project environment, never the system Python.

```bash
.venv/bin/python tools/disasm.py          # regenerate re/Wings.lst and re/functions.csv (about 2 s)
.venv/bin/python tools/skel.py 010228     # control-flow skeleton of one routine (address or name)
.venv/bin/python tools/oracle.py          # 68000 oracle self-test, must print PASSED
.venv/bin/python tools/mdcheck.py SPEC.md # Markdown safety check, run on every .md that was edited
.venv/bin/python tools/build.py --native  # build dist/wof.html, dist/core.wasm and tests/libwofcore.dylib
.venv/bin/python -m pytest tests/         # full suite; the page tests need Google Chrome
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
- `original/` and `dist/` contain the game data. Never publish them or push them to a public remote.
- Hand-written sources contain code only. Tables, texts and tuning values come from the original executable at build time (`re/tables.toml`, see `SPEC.md` section 5).
- Port from the disassembly, not from assumptions. `int` in the original is 16 bits; follow `SPEC.md` section 7.1 exactly.
- Addresses always use the fixed load layout: CODE `0x010000`, DATA `0x023000`, A4 `0x02AFFE`.
- `re/Wings.lst` and `ref/sheets/` are not versioned. After a fresh checkout, run `tools/disasm.py` once to create the listing.
- Never edit `re/Wings.lst` by hand. Put names in `re/names.txt`, library bases in `re/libbases.txt`, then regenerate. The `status` column of `re/functions.csv` is the only hand-edited generated column and survives regeneration.
- Every ported routine carries an `orig 0x......` comment. Pure routines get an oracle test before they count as `verified`.
- When a subsystem is understood, write it down in `re/notes/` so that later sessions do not re-derive it.
- The long printable text blocks in the executable are summarised in the listing on purpose. Read them from the binary by address when the port needs them; do not paste them into source files, notes or documents.
