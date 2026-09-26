# Wings of Fury — faithful WebAssembly port

Implementation specification. Target reader: an engineer (human or AI agent) working in this repository with the tools it already contains.

## 1. Goal

Port the Amiga game *Wings of Fury* (Broderbund, 1990) to the browser as **one self-contained HTML file** that behaves like the original, tick for tick.

- The game logic is **ported from the original 68000 executable**, routine by routine. It is not re-imagined from observation.
- The logic runs in a **WebAssembly core written in C**. A thin JavaScript shell provides canvas, audio, input and storage.
- All game content (graphics, maps, sounds, music, fonts, tables, texts) is taken from the original disk image **at build time** and embedded in the output file. Hand-written source files contain code only, never game content.
- The output `dist/wof.html` opens from `file://` with a double click. It makes no network requests.

The output file contains the game data and is for the disk owner's personal use. `original/` and `dist/` must never be published or pushed to a public remote.

### Definition of faithful

1. **Logic:** fed the same seed and the same stream of input bytes, the port's game state matches the original's after every logic tick.
2. **Picture:** the classic renderer produces the same indexed pixels and the same palette as the original for the same state.
3. **Sound:** the same sample starts on the same channel at the same tick with the same period and volume; music follows the original player's timing.

### Out of scope for this specification

- Enhanced graphics. The core exposes a display list (section 6.4) so an enhanced renderer can be added later without touching game logic. Nothing else is done for it now.
- Emulating Amiga hardware or AmigaOS in the shipped product.
- The crack intro, the crack text screen, and the manual-lookup copy protection. The port goes from the publisher logo straight to the title sequence.

## 2. Repository

```text
SPEC.md                 this document
CLAUDE.md               short working rules for agent sessions
original/wof.adf        the disk image (read-only ground truth)
original/disk/          its files, extracted verbatim with xdftool
original/manual.txt     the game's manual as text: intended behaviour and the key commands (read-only, never quoted at length)
original/kick.rom       the owner's Kickstart 1.3 ROM image: source of the system font, of the default keymap
                        with console.device's key conversion, and of mathffp.library as the reference
                        for the game's floating point (read-only)
re/Wings.lst            annotated disassembly of the main executable (generated)
re/functions.csv        routine inventory with a status column (generated, status is preserved by hand)
re/names.txt            hand-maintained names for code and data addresses
re/libbases.txt         hand-maintained map of library base variables
re/notes/               one Markdown note per understood subsystem
ref/sheets/             contact sheets of decoded shapes (visual reference)
tools/                  Python tooling (section 4)
src/                    C core
web/                    shell: page template, JavaScript modules, CSS
tests/                  pytest suite: core in Node and natively, the page in Chrome and Firefox
dist/wof.html           build output
.venv/                  project-local Python environment
```

`.venv` contains everything the project needs: `capstone` (disassembler), `unicorn` (68000 emulation), `pillow`, `numpy`, and `ziglang`, which provides a C compiler and linker for WebAssembly:

```bash
.venv/bin/python -m ziglang cc -target wasm32-freestanding -O2 -nostdlib -Wl,--no-entry -o core.wasm src/*.c
```

Node 26 is available for running the core headlessly. Apple clang is available for native test builds of the same C sources. Nothing else needs to be installed.

## 3. The original program

Everything in this section is established from the disk image and can be re-checked with the tools in section 4.

### 3.1 Disk

A standard AmigaDOS (OFS) disk. `s/startup-sequence` changes into `Wings_of_Fury` and runs `Wings`.

| Path under `original/disk/Wings_of_Fury/` | Content |
|---|---|
| `Wings` | main executable, 94,292 bytes, not packed |
| `songplay` | music and sound-effect player, a separate small executable that still contains its symbol table |
| `wofsongs` | song data, stored as a hunk file with one chip-memory hunk |
| `maps/a.map` … `maps/o.map` | 15 world maps |
| `shapes/*.shp` | shape (sprite) containers |
| `shapes/wingspalette`, `night.p`, `nightocean.p`, `ocean.palette`, `palette`, `ocean.p` | palettes |
| `shapes/broderbund`, `wingstitle`, `creditscreen`, `selectrank`, `hiscoreslab`, `hiscore.iff`, `Rank.iff`, `iff-dash`, `nightdash` | IFF ILBM pictures |
| `sounds/*` | 8 sound effects |
| `newarmyfont` | the game font |
| `highscore` | high-score table, 360 bytes |
| `wof.mission 3` | a saved game, 6,866 bytes |
| `UFXintro`, `wingt`, `*.info`, `.fastdir` | not part of the game |

The executable on this disk carries a crack: the protection check is disabled and an extra text screen was added. Game logic is otherwise the retail code. The crack also replaced artwork: `shapes/broderbund` and `shapes/wingstitle` carry the crack group's own pictures, dated 1992, so the publisher's logo is not on this disk.

### 3.2 Executable

Three hunks. `tools/hunk.py` loads them at fixed addresses, and **every address in this document, in the listing and in the oracle uses this layout**:

| Hunk | Range | Notes |
|---|---|---|
| CODE | `0x010000`–`0x022F4C` | 77,644 bytes |
| DATA | `0x023000`–`0x027FF0` | first `0x3C60` bytes initialised, the rest zero-filled |
| BSS | `0x028000`–`0x028004` | |

The program was built with **Manx Aztec C** plus hand-written assembly.

- **`int` is 16 bits.** Pointers and `long` are 32 bits. This governs all game arithmetic (section 7.1).
- **A4 is the small-data base, constant `0x02AFFE`.** Globals are addressed as `d16(a4)`. The listing prints the absolute address next to each such operand.
- **Far calls** go through a table of 185 `JMP abs.l` slots at `0x023000`–`0x023456`. `jsr d16(a4)` into that table is resolved to its real target in the listing.
- **C routines** start with `LINK A5`. Arguments are pushed right to left: 2 bytes for `int`, 4 bytes for `long` and pointers. First argument at `8(a5)`. Result in D0.
- **`switch`** compiles to a bounds check, a table of 16-bit offsets, and `jmp base(pc,d0.w)`. The listing resolves the tables and labels each case.
- **String literals live in the CODE hunk**, after the routine that uses them. Pointers from DATA into CODE are therefore often string pointers, not code pointers.
- Layout: `0x010000`–`0x015D62` is almost entirely hand-written assembly (main loop, drawing, interrupt servers, object movement). From `0x015D62` on: 223 C routines, then the C runtime and OS glue at the end. A second block of hand-written assembly, the blitter library that does all shape, rectangle and line drawing, sits at `0x0209BC`–`0x0215D8`.

Inventory: 616 routines, of which 223 are C. The listing classifies all but 39 bytes of the CODE hunk.

### 3.3 Runtime model

`main` (`0x010006`, assembly):

1. Initialise: open libraries, close Workbench, load assets, build the display, install interrupt servers.
2. **Outer loop** (`0x010066`): title sequence, rank selection, mission setup, high scores, load and save.
3. **Inner loop** (`0x01010E`): one pass per displayed frame. The head of the loop calls `ingame_keys` (`0x01CCF6`), which drains the key buffer, and tests the quit and the pause flag; each pass then calls `frame_update` (`0x010228`), a fixed pipeline of about twenty subsystem routines, some assembly and some C, and then `run_queued_ticks` (`0x0114D8`).

**Timing is a fixed-step simulation driven by an input queue:**

- The VBlank interrupt server `vblank_server` (`0x011754`) counts VBlanks. On **every 4th VBlank** it obtains one *input byte* and appends it to a FIFO of at most 6 entries (`input_queue` at `0x027356`, count at `0x027354`). When the queue is full, the oldest entry is dropped.
- `run_queued_ticks` executes **one logic tick per queued input byte**.
- The logic rate is therefore the VBlank rate divided by 4: **15 Hz on NTSC** (the machine the game was designed for), 12.5 Hz on PAL.
- The input byte comes from `read_joystick` (`0x01CA32`) in normal play.
- `demo_mode` (`0x026D4C`): `0` is normal play; `1` is **demo playback**, where input bytes are read from a buffer (at most `0x1386` entries, a `0xFF` byte ends it); `2` is demo recording. The executable refers to a file `wofdemo`, which is not on this disk.

This design is what makes a verifiable port possible: the simulation is a function of initial state, the input byte stream, and one further input, the **entropy stream**. The game's only random source, `rand_beam` (`0x0203BE`, 43 call sites), returns a constant exclusive-ored with the raster beam position at the moment of the call, so in the original all randomness is CPU timing. The port replaces the beam position by an explicit, reproducible stream of values (`re/notes/random.md`). The program never checks the machine's video rate; at 50 Hz everything simply runs at five sixths of the speed.

**The input byte** is assembled by `read_joystick` (`0x01CA32`) and is the only channel by which controls reach game logic. Its low byte is: bit 0 stick forward, bit 1 stick back, bit 2 stick right, bit 3 stick left, bit 4 fire held for 10 or more VBlanks, bit 5 fire tapped and released inside 10 VBlanks. Bits 6 and 7 are unused. Forward is the stick pushed away from the player, which the hardware reports as bit 9 exclusive-or bit 8 of `JOY1DAT`; it moves the cursor up in the menus and **climbs** in flight, because the game is seen from the side and up on the stick is up on the screen; the manual's take-off instructions say the same and the owner's real Amiga confirms it. The reversed-vertical option, which the manual gives as Control-F, swaps the two bits for players who want a pilot's stick; the owner is one of them, so the port must offer it and remember it. Opposing directions cancel to centre. The latches are not cleared between the front end and a mission: the release of the press that ends the briefing is sampled after the queue is cleared, so the first tick of the mission can carry the tap bit. The tap and hold timing runs at VBlank rate, not tick rate, and latches between samples. The keyboard is a separate path: an input.device handler at priority 127 buffers raw Amiga key codes with their qualifier words, ten deep, and does not feed the tick. Five routines read the buffer: the menus, a release wait, the line editor of the name and file-name entry, the briefing and the in-flight commands. The game tests one qualifier bit, Control (`0x0008`), and turns a raw code into a character through console.device's `RawKeyConvert` with the system's default keymap, accepting a key only when exactly one character comes back. Details and consequences for the port: `re/notes/input.md` and `re/notes/keys.md`.

**Passes are not pure rendering.** `frame_update` begins with `wait_vblank` (`0x01AA3E`), so there is at most one pass per VBlank, counted from the previous buffer flip, and it contains game logic that runs once per pass, not per tick: soldiers move and die, score is added, ticker messages are queued, and the restart after a lost aircraft and the game-over countdown advance. Nine routines in its call tree call `rand_beam`. The tick in turn reads state the pass leaves behind: the flag at `0x026E3C`, a frame was drawn since the last tick; the pass counter at `0x0253C8`; the drawing copies `snapshot_for_draw` writes into every object record; the kind byte a pass clears there, which frees the record; the four object pools a pass spawns into; the soldier table; the score and an island's count of soldiers, which `soldiers_draw` changes when a soldier dies; the oil and the fuel, which a target's fire (`0x014F5C`) takes from the player's record; and the blitter library's clip rectangle and draw target, which the tick needs because **the tick draws too**: the restart after a lost aircraft, `player_lost_restart` (`0x0135D8`), with its clearing of the playfield and its `WaitTOF` loops, runs inside `logic_tick`'s tree, reached from the player update while the aircraft is in the water, and in every observed run that was the only path it took. What crosses in each direction, observed and merely read, is in `re/notes/passes.md`; at equal tick numbers and equal input bytes, runs at one, two and three VBlanks per pass differ only in what that note lists. The interleaving of VBlanks, passes and ticks is therefore an input of the simulation, like the input bytes and the entropy stream. On the owner's PAL Amiga a pass takes 2 VBlanks in a quiet scene, measured by 240 fps film with the story scroller as the calibration (`re/notes/passes.md`, "What the film of the real machine shows"); a busy scene has not been filmed yet, and there the original may need 3.

### 3.4 Operating system and hardware use

The game builds its own display with graphics.library and otherwise does its own work.

| Used by the original | Port equivalent |
|---|---|
| dos: `Open`, `Read`, `Write`, `Seek`, `Close`, `Lock`, `Examine`, `ExNext`, `UnLock`, `IoErr`, `DeleteFile` | read-only virtual file system built from the disk files; writes go to browser storage. The load and save dialog walks the game's directory with `ExNext` and neither sorts nor filters beyond the prefix `wof.`, so the order of the entries is behaviour (section 6.2, Storage) |
| dos: `LoadSeg`, `UnLoadSeg` (twice: the `songplay` player, and `wofsongs`) | the player is ported into the core; song data is read from the embedded file |
| dos: `Delay` | coroutine yield for the given time (section 6.3) |
| exec: `AllocMem`, `AvailMem` | static arena allocator; out-of-memory paths are unreachable |
| exec: `AddIntServer`, `RemIntServer` (VBlank) | the shell's clock: 4 VBlanks make one tick |
| exec: `FindTask`, `SetTaskPri`, `Forbid`, `Permit`, `Supervisor`, `Alert`, `Debug` | dropped |
| exec: `RawDoFmt` | small `sprintf` subset written to match the format strings actually used |
| exec: `OpenDevice`, `DoIO`, `AddPort`, `RemPort`, `AllocSignal`, `FreeSignal` | input.device, to add and remove the key handler; console.device is opened for `RawKeyConvert`, which every command key and every typed character goes through, so the port needs the system keymap as well as the system font (`re/notes/keys.md`, `re/notes/system-font.md`). The rest is replaced by the shell's key path (section 6.2) |
| mathffp: `SPFix`, `SPFlt`, `SPCmp`, `SPTst`, `SPNeg`, `SPAdd`, `SPSub`, `SPMul`, `SPDiv`, opened on first use by C-library glue at `0x021C9C`–`0x021D2E` | the game's logic computes with Motorola fast floating point in two routines of the tick, the player's motion `0x01BDFA` and an enemy aircraft's `0x01D796`, which use six of the nine operations. The third user is the C library's `%e`, `%f` and `%g` conversion `0x021A40`, which the game never reaches: no format string it gives `sprintf` carries such a conversion. The port reproduces all nine operations bit-exact in integer code, `src/ffp.c`, tested against the ROM's routines under the oracle (section 7.1, `re/notes/ffp.md`) |
| graphics: `InitBitMap`, `InitRastPort`, `OwnBlitter`, `DisownBlitter`, `WaitTOF`, `BltClear` (4 sites), `RectFill`, `Move`, `Draw`, `SetAPen`, `SetBPen`, `SetDrMd` | the port's framebuffers and drawing primitives |
| graphics: `InitVPort`, `MakeVPort`, `MrgCop`, `GetColorMap`, `FreeColorMap`, `FreeVPortCopLists` | occur only in dead code and in the crack's text screen (`0x01F41A`), neither of which is ported. The game proper builds no OS View |
| graphics: `BltBitMap` (1 live site, a view copy at `0x01A89E`), `BltTemplate` (1), `Text` (4 callers) | software equivalents on the indexed framebuffer |
| intuition: `CloseWorkBench`, `OpenWorkBench` | dropped |
| custom chips: `JOY1DAT`, `VHPOSR`, `INTENA`, `INTREQ`, audio registers; level-4 autovector at `0x70` | input layer, entropy stream, Paula model (section 6.5) |
| custom chips: `COP1LC` written directly with copper lists the game builds itself; the blitter registers driven directly by the blitter library | palette tables per output row and software drawing primitives (section 6.4) |

Sound effects: `sound_init` (`0x01E8B8`) installs its own level-4 (audio) interrupt handler `audio_irq` (`0x01EBAA`) and a VBlank server named `SoundFX_IntHandler` (`0x01EC64`).

### 3.5 File formats

All multi-byte values are big-endian.

**`Rpck` compression wrapper.** Used by most `.shp` files and two palettes. Reference implementation: `tools/rpck.py`; original routine: `rpck_unpack` at `0x01FEE0`.

```text
+0  'Rpck'
+4  u32   unpacked size
+8  RLE stream to end of file. Read signed control byte c:
      c <  0 : copy -c literal bytes        (0x80 means 128)
      c >= 0 : read one byte, write it c+1 times
```

The loader `load_file` (`0x01FF16`) handles the wrapper transparently, so any file may or may not be wrapped. It also knows a second magic, `Pckd`, which it rejects; no file on the disk uses it. Two files decode to one byte more than the declared size; the declared size wins. The original's unpacker ignores the destination length and writes that byte past its buffer; the port stops at the declared size.

**`PPkc` shape container.** Reference implementation: `tools/ppkc.py`.

```text
+0            'PPkc'
+4            u16   n = number of shapes
+6            n x 4 bytes: shape names (4 ASCII characters, not terminated)
+6+4n         n x u32: offset of each record, relative to the end of this table
+6+8n         records

record:
+0   u16   width in bytes (pixel width = 8 x this)
+2   u16   height in rows
+4   s16   hotspot x
+6   s16   hotspot y
+8   u16   x of the shape in its source picture (overwritten at load for two files, see below)
+10  u16   y of the shape in its source picture
+12  u8    planes cleared under the mask on every draw
+13  u8    planes set under the mask on every draw
+14  u8 x 6    destination plane masks, zero-terminated list
+20  plane data: for each mask in the list, height x width bytes, plane after plane
```

A mask is the set of destination bitplanes that one stored plane is written to. `01 02 04 08 10` is an ordinary 5-plane shape. `01 02 04 18` stores 4 planes and writes the last one to planes 3 and 4. The pixel value is the OR of the masks of all stored planes whose bit is set. Colour 0 is transparent for shapes that are drawn through a mask, which is decided per shape at draw time: a shape whose plane is larger than 1,040 bytes (11 shapes, the carrier and ship hull pieces and `rank`) or that stores no planes is drawn opaque. Names inside a container are strictly ascending, which the game's lookup `shape_find` (`0x020560`) relies on. For `hellcat.shp` and `Torpedo.shp` the game overwrites +8 with a facing marker at load and mirrors shape data in place when the facing changes (`shape_mirror_x`, `0x015B58`). Name resolution, the pointer tables and the load order are in `re/notes/shapes.md`; the exact blit rule is in `re/notes/drawing.md`. The game refers to shapes **by their 4-character names**; name lists are in the executable's DATA hunk.

**Palettes.** `wingspalette`, `night.p`, `nightocean.p`: a bare IFF `CMAP` chunk: 4 bytes `CMAP`, 4 bytes to ignore, then 32 RGB triplets. Only the high nibble of each component is significant. `palette` and `ocean.palette` are `Rpck`-wrapped ILBM files used for their `CMAP`; `ocean.p` is an unwrapped one and also carries `CRNG` colour-cycling chunks. The game never opens `palette` or `ocean.p` and no code reads `CRNG`: there is no colour cycling.

**Pictures.** Standard IFF ILBM with ByteRun1 compression. The live reader is `iff_to_vport` (`0x01A548`), which handles `BMHD`, `CMAP`, a private `CMP2` chunk and `BODY`, crops to the viewport and assumes ByteRun1; it is to be ported rather than replaced. A second reader that reports errors under the name `ReadIFF` is dead code.

**Maps.** Two u32 values, the file's own length, which is also the length the loader gives the record list, and the offset of the carrier's first record, whose four times less eight is the world x at which the player starts; then one u16 record per eight pixels of world x. Bit 15 draws the record's shape, bits 13 to 11 give its height in steps of four screen rows, bits 10 to 2 the slot in `MasterList` or `AthList`, and bits 1 and 0 say whether the record stands on the world (2) or rides on a ship (1); bit 14 is never set in any of the fifteen maps. A shape wider than eight pixels occupies several records, of which one carries bit 15, most often the third, while the others still give the ground under it its height. The list is rewritten during a mission: a bombed barracks' four records become slot 5, and a hit on a pillbox gives its record another of the slots `0x0F` to `0x1E` (`re/notes/porting-m5.md`). The loader asks for `length` bytes of records although the file holds `length - 8`; the four records that never come from the file are zero, because the game's allocator sets `MEMF_CLEAR` on every request. Reference decoder: `tools/map_decode.py`; record semantics, the ground height and the world coordinate system: `re/notes/map.md`.

**Sounds.** Headerless signed 8-bit PCM. Playback periods are in the executable.

**Font.** `newarmyfont` starts with a u16 height (12), first and last character codes (`0x20`, `0x7E`), then a table of per-character widths, then glyph data. The header and glyph layout are in `re/notes/drawing.md`: glyph data starts at +100, and a width of 0 means no glyph and an advance of 11. The load and save dialogs, name entry and file list draw with the system default font instead, topaz 8, which is not on the game disk. The port takes it from `original/kick.rom` at build time (`re/notes/system-font.md`).

**`songplay` and `wofsongs`.** `songplay` exports, by symbol: `_PlaySong`, `_StopSong`, `_FadeSong`, `_PauseMusic`, `_RestartMusic`, `_GetSongStat`, `_PlaySfx`, `_StopSfx`, `_SfxStat`, `_AdjustSfx`, `_ReadInstruments`, `_OpenTimerInt`, `SongIntHandler`, `CheckChannelInt`. The song format is to be established from this player; it is 2.7 KB of code with names, which makes it the easiest part of the project to read.

## 4. Tools

Run everything with `.venv/bin/python` from the repository root.

| Tool | Purpose |
|---|---|
| `tools/disasm.py` | regenerates `re/Wings.lst` and `re/functions.csv` from the executable, `re/names.txt` and `re/libbases.txt` (about 2 seconds) |
| `tools/skel.py ADDR` | control-flow skeleton of one routine: labels, calls, branches, tests. Add `--all` for the full text |
| `tools/oracle.py` | runs original routines in a 68000 emulator; running it directly executes its self-test |
| `tools/headless.py` | the headless original (section 8): `run RUN.json --out A.dump` with `--changes`, `--entropy-log` and `--schedule`; `show A.dump`; `diff A.dump B.dump`. Formats and use in `re/notes/headless.md` |
| `tools/hunk.py` | hunk loader used by all of the above |
| `tools/m68kdis.py EXE START LEN` | raw linear disassembly of an address range |
| `tools/ffp_observe.py`, `tools/ffp_soak.py` | the floating point: the first records under the headless original every operand the game hands mathffp and every entry of the two routines that use it, over its own scripts and five M6 scripts (`tests/ffp_observed.json`); the second runs the port against the ROM over a million random operands per operation (`re/notes/ffp.md`) |
| `tools/pass_observe.py`, `tools/object_observe.py`, `tools/headless_writes.py` | observation of the headless original over a set of mission scripts (deck, flight, climb, guns, bomb, lost, game over): what a pass writes and what a tick reads of it, with the pass-rate control; the object tables, the draw order, the player's record and their controls; and the write summary and read collector behind both (`re/notes/passes.md`, `re/notes/objects.md`) |
| `tools/reach_observe.py` | which routines, and with `--blocks` which basic blocks, a set of mission scripts executes under the headless original, by window of `main` (setup, mission and so on) and by phase, with the entropy reads per caller; `--cold` lists the regions of the ported routines that no script executed, each with its stand-in marker, and fails on one without (section 7.4, `re/notes/porting-m4.md`) |
| `tools/m4_autopilot.py`, `tools/m5_autopilot.py`, `tools/m6_autopilot.py`, with `tools/m4_scripts.py`, `m5_scripts.py`, `m6_scripts.py` | the mission scripts of M4 to M6: a policy flies the headless original VBlank by VBlank and its choices, compressed into runs, are the script, which replays without it (`re/notes/porting-m4.md`, "The scripts of part 2") |
| `tools/m5_observe.py`, `tools/m6_observe.py` | observation over the M5 and M6 scripts: the pools, the sky flash, the couplings and an object's fall; the fifteen maps' enemy content and the enemy records' writers by phase (`re/notes/porting-m5.md`, `re/notes/enemy.md`) |
| `tools/map_decode.py` | the map files: records, world coordinates, and the map draws of a pass at a given view position (`re/notes/map.md`) |
| `tools/rpck.py`, `tools/ppkc.py` | reference decoders; `ppkc.py SHP PALETTE OUT.png` renders a contact sheet |
| `tools/fd/` | AmigaOS library offset tables used to name OS calls |

**Listing conventions.** Routine headers give the kind (`C` or `asm`), the stack frame size, the far-call slot, and the callers. Operands that use A4 are followed by the absolute address or its name. Relocated longs are shown as names or as the string they point to. OS calls are named. Blocks marked *found by gap sweep* are code that nothing references by control flow (uncalled library routines or routines reached only through computed addresses).

**Naming workflow.** When a routine or global is understood, add it to `re/names.txt` and regenerate. The listing, the skeletons and the inventory pick the name up everywhere. Never edit `re/Wings.lst` by hand.

**The oracle.** `Oracle.call(addr, *args, regs=...)` executes an original routine on a real 68000 model with the executable mapped at the listing addresses. Build stack arguments with `Oracle.W()` for `int` and `Oracle.L()` for `long` and pointers. Pass `a4=0x02AFFE` when the routine touches globals. The condition codes a routine leaves cannot be read out of the emulator, which keeps them lazily and reports stale ones; `call(..., ccr=True)` returns through a move from SR inside the emulation and leaves them in `Oracle.ccr`, and the headless original's return observers do the same. Its self-test runs `rpck_unpack` on all ten packed files and compares the output with `tools/rpck.py`.

## 5. Build

`tools/build.py` produces `dist/wof.html` in these steps (`--native` also builds the test library):

1. **Extract tables.** `tools/extract_tables.py` reads `re/tables.toml`, a manifest of (name, address, element type, count) entries, and writes `src/gen/tables.c` and `src/gen/tables.h` from the bytes of `original/disk/Wings_of_Fury/Wings`. Every constant table, name list, text and tuning array the port needs from the DATA or CODE hunk is obtained this way. Byte order is converted during extraction. One entry, `data_image`, is the initialised part of the DATA hunk as a whole: every registered global whose address lies in it starts with the original's value, and the ticker reads a constant message from it. The same step reads the topaz 8 glyphs, location table and metrics from `original/kick.rom`, locating the font by its contents so that other Kickstart versions work, and falls back to the game's own font, in the build with a message and in the core when it draws, when the ROM is absent. The key conversion comes from the ROM in the same step: the build runs console.device's `RawKeyConvert` with the ROM's default keymap, both located by their contents as the headless original locates them, for every raw code under the qualifier combinations the shell can send, and writes the single characters as a table; the game never asks for more than one character and never brings a keymap of its own (`re/notes/keys.md`). Without the ROM the build says so and the table holds only what the positions of the raw codes give: letters, digits and the space bar. `src/gen/` is ignored by version control.
2. **Pack the file system.** All game files from section 3.1 except the executable and the non-game files are concatenated into one blob. Left out are `Wings`, `UFXintro`, `wingt`, every `.info` file and every dotfile, which leaves 55 files. Files stay in their original formats; the core contains the ported loaders. The container is big-endian like everything else the project reads: the magic `WOFS`, a u32 version, a u32 file count, a u32 directory offset, then 40-byte directory entries of a 32-byte NUL-padded name, a u32 offset and a u32 length. Names are paths relative to the disk's `Wings_of_Fury` directory, which is the original's current directory, so the ported loaders use the original's own file names. File-name lookup ignores case: the game asks for `shapes/Torpedo.shp`, the disk has `torpedo.shp`. The executable also holds the name `shapes/rank.iff`, which nothing refers to: `Rank.iff` is never opened, and the briefing draws the shape `rank` from `world.shp` instead.
3. **Compile the core** to `core.wasm` with the command in section 2, plus `-Wl,--export-dynamic` or explicit export attributes.
4. **Assemble the page.** `web/index.html` is the template. The build inlines the CSS, the JavaScript, the base64 of `core.wasm` and the base64 of the file-system blob. The files in `web/` are real ES modules, which a `file://` page cannot load from files; the build concatenates them in dependency order into one scope, strips whole-line imports and leading `export` keywords, and then fails if any module syntax is left or an imported name is not defined. The page instantiates the module with `WebAssembly.instantiate(bytes, imports)`; streaming instantiation is not available from `file://`.

Expected output size is below 2 MB.

A second target builds the same C sources natively with Apple clang as a shared library for the tests (`tests/libwofcore.dylib`).

## 6. Architecture

### 6.1 Core

C11, freestanding: no libc, no allocation after initialisation (one static arena replaces `AllocMem`), no host floating point in game logic (the original's own floating point, mathffp, is reproduced in integer code, section 7.1), no dependence on wall-clock time, no undefined behaviour relied upon. The same sources must compile for `wasm32-freestanding` and natively.

Source files mirror the original's modules in address order so that a reader can move between listing and source. Every ported routine carries its origin:

```c
/* orig 0x01C660 - per-tick state machine of <whatever it turns out to be> */
```

Exported interface (names are normative, signatures may grow):

```c
void            wof_init(uint32_t seed, const uint8_t *fs, uint32_t fs_len);
void            wof_set_video_hz(int hz);          /* 60 or 50; the core starts at 60, the shell sets the standard at start, see 6.2 */
void            wof_vblank(uint8_t raw);           /* call once per emulated VBlank, see 6.2 */
void            wof_key(uint8_t code, uint16_t qualifier);       /* a raw key event as the original's handler receives it */
void            wof_port_key(uint8_t code, uint16_t qualifier);  /* the shell's entry: the port's command keys, see 6.2 */
void            wof_set_invert_vertical(int on);   /* the owner's remembered vertical flip, see 6.2 */
int             wof_invert_vertical(void);
void            wof_set_keyboard_assist(int on);   /* the port's keyboard assist, off in the core, see 6.2 */
int             wof_keyboard_assist(void);
void            wof_set_fade_vblanks(int n);       /* VBlanks per fade step, provisionally 2, see 6.3 */
int             wof_fade_vblanks(void);
void            wof_set_vblanks_per_pass(int n);   /* VBlanks a pass is owed, provisionally 2, see 6.2 */
int             wof_vblanks_per_pass(void);
uint32_t        wof_standin_hits(void);            /* how often a marked stand-in was reached, see 7.4 */
void            wof_request_pause(void);           /* the pause as a request, not a toggle, see 6.2 */
int             wof_paused(void);
const int16_t  *wof_dev_player(void);              /* x, y, deck state and weapon type of the player, read-only, for the overlay */
uint32_t        wof_fs_changes(void);              /* the shell stores the written files when this moves, see 6.2 */
uint32_t        wof_fs_written_count(void);
const char     *wof_fs_written_name(uint32_t i);
uint32_t        wof_fs_written_size(uint32_t i);
const uint8_t  *wof_fs_written_bytes(uint32_t i);
int             wof_fs_put(const char *name, const uint8_t *data, uint32_t len);   /* the shell hands stored files back at start */
void            wof_pass(void);                    /* one pass of the main program, see 6.3 */
const uint8_t  *wof_framebuffer(void);             /* indexed pixels, see 6.4 */
uint32_t        wof_framebuffer_width(void);       /* the shell queries geometry, never hard-codes it */
uint32_t        wof_framebuffer_height(void);
const uint16_t *wof_palette_rows(void);            /* palette index per output row, see 6.4 */
const uint32_t *wof_palettes(void);                /* wof_palette_count() tables of wof_palette_colours() entries */
uint32_t        wof_palette_count(void);
uint32_t        wof_palette_colours(void);
const void     *wof_display_list(uint32_t *count);
void            wof_audio_render(int16_t *stereo, uint32_t frames, uint32_t rate);
uint32_t        wof_state_size(void);              /* save states, replays, tests */
void            wof_state_save(uint8_t *dst);
void            wof_state_load(const uint8_t *src);
uint8_t        *wof_alloc(uint32_t bytes);         /* static arena; how the shell hands the file blob to the core */
void            wof_arena_reset(void);
uint32_t        wof_arena_size(void);
uint32_t        wof_arena_used(void);
uint32_t        wof_vblank_count(void);            /* counters for the diagnostics overlay and the tests */
uint32_t        wof_tick_count(void);
uint32_t        wof_pass_count(void);
```

A palette entry is RGBA in memory order, which canvas `ImageData` takes without conversion. `wof_init` does not reset the arena, because the shell allocates the file blob from it before calling `wof_init`. `wof_state_load` checks a magic and a version and leaves the running state untouched when they do not match. A save state is the bytes of the core's state struct, which holds no pointers. It is copied whole, padding included, and `wof_init` zeroes it, so the round trip is exact; this is valid between little-endian hosts, which both targets are. The coroutines' resume points and the locals they keep across a wait are part of it, so a state saved in the middle of a screen resumes there. Loaded assets live in the arena, outside the state; the arena never reuses memory, so a state stays valid within a session, and a state carried across a page reload is not supported. Two further entries, `wof_dev_set_score` and `wof_dev_open_dialog`, are not part of the game: the shell offers them only while the diagnostics overlay is up, so that a screen which a mission would be needed to reach can be looked at. `wof_dev_player` is read-only and feeds the overlay's player line (position, deck state, weapon type) and the page tests. `wof_set_keyboard_assist` switches the port's keyboard assist (section 6.2): a core that was never told runs without it, as the original, and every differential test runs that way; the shell switches it on at start. Its state is part of the save state and none of it is a registered global. With the assist on, `wof_vblank` hands the sample what the assist makes of the controller; the front end's pollers and the button's latches still see the controller as it is. `wof_request_pause` asks for the pause from outside: the next `ingame_keys` of a mission sets `pause_flag` as Escape does, and outside a mission the request is dropped; `wof_paused` says whether a mission is paused.

`wof_vblank` is the port of `vblank_server` together with `vblank_every_frame`. It takes the **raw controller state** of that VBlank, not a finished input byte: bit 0 stick forward (up), bit 1 stick back (down), bit 2 right, bit 3 left, bit 4 fire button currently down. The shell maps the up key and a gamepad pushed forward to bit 0. The core runs the fire-button press timer, cancels opposing directions, applies the reversed-vertical option, assembles the input byte, counts to 4 and queues it, including the 6-entry limit and demo playback and recording. Keeping the tap and hold discrimination inside the core is required for fidelity, because it is evaluated at 60 Hz while sampling happens at 15 Hz (`re/notes/input.md`).

`wof_key` is the port of `input_handler`: it appends a raw Amiga key code and its qualifier word to the ten-deep key buffer with the original's drop rule, and the ported readers take it from there unchanged. The differential tests replay the keys of a headless schedule through it. `wof_port_key` is what the shell calls, a thin layer of the port's own in front of `wof_key`: while the line editor is active it passes every key on as it came; otherwise it rewrites the port's command keys into the code and qualifier the original's readers expect and applies the port's restrictions (section 6.2). The state that decides this (line editor active, paused, briefing) lives in the core, which is why the layer does. The picture viewer's `wof_key_press` goes when M3 replaces the viewer.

`wof_set_invert_vertical` gives the core the owner's remembered preference for the vertical flip. A core that was never given one behaves as the original, which is what the differential tests run. Once given, the core keeps the preference outside the saved game, the flip command changes both, and when a loaded game has overwritten `opt_invert_vertical` (`0x0254F6`, which lies inside the range a saved game covers) the core restores it from the preference. The shell reads `wof_invert_vertical` to store the value.

### 6.2 Shell

Plain JavaScript modules, no framework, no bundler other than the build script (section 5, step 4).

- **Clock.** A fixed-rate accumulator driven by `requestAnimationFrame` issues `wof_vblank` calls at the VBlank rate of the video standard, 50 Hz of emulated time on PAL and 60 on NTSC, each followed by one `wof_pass`, independent of the monitor's refresh rate. The original allows at most one pass per VBlank and on real hardware a pass takes longer than that; since logic runs per pass (section 3.3), the number of VBlanks per pass is a core setting, 2, measured on the owner's PAL Amiga in a quiet scene (section 10, point 2). After a stall, at most 24 VBlanks are replayed, which matches the original's queue limit of 6 ticks. The first VBlank after a start samples an input byte, because `vblank_server`'s divider begins at 0: N VBlanks give N / 4 samples rounded up.
- **Video.** Canvas 2D or WebGL. The indexed framebuffer is converted through the per-row palettes to RGBA. A 2D context must be requested with `willReadFrequently: true`, which selects a software-backed canvas: in GPU-composited Firefox the accelerated canvas can drop `putImageData` entirely, so that the canvas reads back as one colour and the player sees a black picture. Headless Firefox composites in software and does not show the fault. **Video standard:** one shell setting, PAL or NTSC, selects the VBlank rate (50 or 60 Hz) and the pixel aspect together, as the machine does. The executable is the same for both and never checks. **PAL is the default**: this disk comes from a PAL region, its added artwork is 256 lines high, and the owner's real Amiga, against which the port is compared, is a PAL machine. **Aspect:** on PAL a low-resolution pixel is 16/15 as wide as it is tall, so a framebuffer pixel, which is a high-resolution pixel, is 8/15 and the 640 x 214 framebuffer is shown in a box of 1024 : 642. On NTSC, where 320 x 200 fills a 4:3 screen, a low-resolution pixel is 5/6 as wide as tall and the box is 800 : 642. The picture is never shown with square framebuffer pixels, which gives a strip three times as wide as it is high. **Size:** the picture fills the largest box of that ratio that fits the browser window, centred on black, recomputed on every resize, in fullscreen and when `devicePixelRatio` changes. The box is laid out in whole device pixels and only then converted to CSS pixels, so the displayed canvas has a backing store of exactly its CSS size times `devicePixelRatio` and the browser resamples nothing a third time. Because the pixel aspect rules out whole-number factors in both directions, scaling is done in two steps so that pixels stay crisp and evenly sized: a whole-number nearest-neighbour enlargement to at least the box size in device pixels, then a smooth reduction to the exact size; where both factors are 1 the source is reduced directly. Three canvases carry this: the 640 x 214 source canvas that receives `putImageData`, which stays software-backed as described above and is never on the page, the enlargement, and the displayed canvas. The last two are accelerated; `drawImage` is not subject to the Firefox fault, which the visible Firefox run confirms. The shell names the three on `window.__wofVideo`, because after scaling the exact framebuffer pixels exist only on the source canvas and the page tests need them. Nothing covers the picture permanently: the key hint goes away with the sound prompt on the first activating key press and comes back with the diagnostics overlay. A square-pixel, whole-number mode can be an option in M9.
- **Input.** Keyboard and Gamepad API are merged into the raw state word passed to `wof_vblank`. A button that goes down and up again between two VBlanks is held sticky until the next `wof_vblank`, so short taps survive; the original samples a level, so this only compensates for the browser's coarser event timing. Menu and text-entry keys take the second path: the shell maps `KeyboardEvent.code`, which is positional, to raw Amiga key codes, which are also positional, and feeds the core's key buffer. The key map is configurable and stored locally. The original's key commands (manual, last page, and `re/notes/keys.md`: pause on Escape, and Control with R, C, F, G and L for restart, clearing the high scores, the vertical flip, save and load; Control-S switches the music and is not in the manual; the manual's Control-D, which would show the high scores, is not in this executable, and the port leaves it out) cannot be taken over as they are, because a browser keeps Control with those letters for itself (reload, find, address bar) and a page cannot prevent all of them. **The port's keys, decided with the owner**, by `KeyboardEvent.code`: `KeyP` pauses and continues, `KeyF` flips the vertical control, `KeyG` saves (on the carrier only, as in the original), `KeyL` loads, `KeyM` switches the music (`KeyS` is the stick pulled back), `KeyR` restarts and `KeyC` clears the high scores; `Enter` chooses in a menu beside fire, and the arrow keys move. `KeyR` and `KeyC` act only while the game is paused, `KeyR` in the briefing as well: without Control in front of them a stray key would throw a campaign away, and the original accepts both while paused, so this narrows the original and adds nothing to it. `Escape` is a second pause key, and the shell asks the core to pause, as a request and not a toggle, whenever fullscreen is left: a browser takes Escape to leave fullscreen and a page cannot prevent that, so with both rules Escape always pauses. Inside the line editor every key is a character or an editing key and no command applies. Five of the keys, P, F, G, L and M, carry a command in every state outside the line editor, so a plain press of them never reaches a reader as a plain letter. Nothing the manual describes is affected; what is lost is outside the manual: the cheat sequence of `ingame_keys` cannot be typed, because one of its letters is the load command, and two of the debug keys it unlocks are taken as well (`re/notes/keys.md`). The owner decided on 2026-09-21 that the port does not need the cheat sequence: `ingame_keys` is ported as it is, the sequence stays untypeable, and no development key is built in its place. The shell leaves the function keys and Help unmapped, so that reload and the developer tools stay with the browser, and the key left of 1 toggles the diagnostics overlay and never reaches the game. The shell sends the qualifier bits of Shift and Caps Lock, never Control, and ignores a key pressed together with Control, Alt or Command. **The vertical flip is a preference, not game state**: the owner flies with it on, so the shell stores it with its settings, hands it to the core at start, and the remembered value wins over a loaded game, which in the original overwrites it (`wof_set_invert_vertical`, section 6.1). This is a deliberate divergence from the original, confirmed by the owner. No modifier key may ever be mapped: with Control as fire and W as up, firing while climbing is Ctrl+W, which closes the tab and which a page cannot prevent. **The keyboard assist, decided with the owner on 2026-09-22**, is a deliberate divergence, because a key is tapped where a joystick is held, and the owner wants the menus to feel as a player expects today while the flying stays the original's. In the weapon menu in the hold (`0x0112B0`, which steps on the sampled byte and swallows the two samples after a step) a press of forward or back is one step: a synthetic push of exactly twelve VBlanks, three samples at any phase, never flipped, so up on the key is up in the menu whatever the vertical flip says. Up to two presses made while a push runs are remembered, a key held when a push ends repeats as the original does, a press in the menu is never lost (in the fifteen ticks after each opening in which the original's tick does not yet run the menu, `0x026D3E`, a press is remembered the same way and its push starts on the VBlank the menu becomes live), the push ends with the menu and on a sample that carries the button to a live menu, and the cursor keys are swallowed there because they would reach the menu a second time through `last_key`. Everywhere else a tap shorter than a sample reaches the tick exactly once: a direction that goes down arms itself and the next sample carries it, so a press gives one tick for every sample it covers and one where it covers none, never more than the original gives a push of that length. The button's latches, the front end's pollers and the rank menu, which polls every VBlank and waits for the release, are untouched. The assist is off in the core and in every comparison with the original; `src/assist.c` and `re/notes/porting-m4.md`, "The keyboard assist".
- **Audio.** The shell pulls PCM from `wof_audio_render` in blocks that correspond to emulated time and plays them through an `AudioWorklet`, fed by `postMessage`. The worklet module is inlined and loaded from a `data:` URL on a `file://` page, where a Blob URL is refused as a cross-origin load, and from a Blob URL elsewhere. Scheduled `AudioBufferSourceNode` blocks are the fallback; the query `?audio=buffers` forces it so that the tests can exercise it. Audio starts on the first event that really activates the page, which is not the same as the first event: a modifier pressed on its own, such as the Command of a console or screenshot shortcut, is a `keydown` that activates nothing, and a context built there is born suspended and logs an autoplay warning. The shell asks `navigator.userActivation.isActive` where it exists and otherwise ignores modifier keys, dead keys and keys pressed with a modifier held. It builds and resumes the context in the same task as the event, keeps listening and retrying until the context state is running, and only then removes the prompt that asks for a key.
- **Storage.** `highscore` and saved games are written through the virtual file system to `localStorage`, base64-encoded, under a `wof:` prefix, as one list under `wof:files` and not a key per file, because the order in which files were written is part of the order in which the load and save dialog lists them; the shell's own settings, the vertical flip among them, live under the same prefix. `highscore` is 360 bytes, ten entries of a u32 score, a u16 rank and a 30-byte NUL-padded name, best first; a missing file reads as ten empty entries, and clearing the high scores deletes the file (`re/notes/highscore.md`). The load and save dialog shows the first six entries of the game's directory whose names begin with `wof.`, in the order `ExNext` hands them out, which on the original's disk is the order of the directory's hash chains and not the alphabet. The virtual file system reproduces that order from the names alone: an entry's chain is the AmigaDOS name hash modulo 72, chains are walked upward, and inside a chain a newer file comes before an older one. A name keeps its case as typed. That Kickstart 1.3 walks the chains in this order and puts a new entry at the head of its chain is documented behaviour which neither a run nor the disk image has confirmed (`re/notes/frontend.md`).
- **Pause** when the page is hidden, through `wof_request_pause`, so that a mission comes back paused.

### 6.3 Blocking code becomes coroutines

The original's front end blocks: it waits for VBlanks, for `Delay`, for the fire button, for fades. A browser page cannot block, and from `file://` there is no `SharedArrayBuffer` to block in a worker. Therefore:

- The main program (`main` and everything that can wait) is ported as a **stackless coroutine** in the protothreads style: a `switch`-based resume point, with locals that live across a wait moved into a context struct. The original's linear control flow is kept; each original wait becomes `CO_WAIT_UNTIL(condition)` or `CO_YIELD()`.
- `wof_pass()` resumes the coroutine once. During play this is exactly one pass of the inner loop. In the front end one wait is one VBlank: the shell calls `wof_pass` after every `wof_vblank`, the headless original delivers a VBlank exactly where the program waits, and so the two agree VBlank for VBlank. `wof_init` runs the coroutine up to its first wait.
- The original's fades contain no wait, so their duration is CPU time that the listing cannot give (section 10, point 6). The port gives a fade step a fixed number of VBlanks, a core setting, provisionally 2, which makes a whole fade 32 VBlanks; the differential tests set it to 0, as the harness's fades take no time either.
- Routines that never wait are ported as ordinary functions. The logic tick is not one of them: `player_lost_restart` loops on `WaitTOF` and is reached from inside `logic_tick`'s tree (section 3.3), so the path from `run_queued_ticks` through the player update down to the restart belongs to the coroutine, and the VBlanks it waits for are not owed again at the next pass, as in the headless original.

### 6.4 Video model

The original display is planar. The port uses **8-bit indexed framebuffers** and applies the palette at presentation, so that fades, the day and night palettes, colour cycling and any palette change part-way down the screen behave as in the original.

- Shapes are converted from plane data and plane masks to indexed pixels once, at load. `tools/ppkc.py` shows the pixel values but is not the reference for drawing: the port keeps per shape the clear and set bytes (+12, +13), the union of its plane masks, its plane count and plane size, and blits against the existing framebuffer value exactly as `shape_blit` (`0x020B0C`) does, including the opaque cases and the depth of the target (the dashboard has 4 planes).
- All drawing primitives of the original (shape blit with transparency, masked and clipped variants, scrolling, text, screen copies) are reimplemented on indexed pixels with identical clipping and identical draw order.
- The original builds no OS View. It keeps its own view and viewport records, builds copper lists and writes `COP1LC` itself (`re/notes/display.md`). The play screen is three stacked areas, 214 lines in all: the playfield, 320 x 162 low resolution with 5 planes, at line 0; the dashboard, 640 x 37 high resolution with 4 planes, at line 163; the message ticker, 640 x 13 high resolution with 1 plane, at line 201; lines 162 and 200 are blank. Playfield and dashboard are double-buffered and the swap is one `COP1LC` write; the ticker is single-buffered and scrolled inside `vblank_server`. Front-end screens use 200 lines in several formats, tabulated in the note. The story scroller's viewport is taller than the framebuffer, 230 rows from display line 5, but its lower grey ramp ends `COLOR01` at black on display line 201, so the rows beyond 214 hold nothing that can be seen. The shell output is 640 pixels wide with low-resolution pixels doubled.
- Colours are 32-word tables per viewport. The mechanisms to reproduce are: the day and night palette files, chosen once per mission by `choose_night` (`0x0111FC`), which `main` calls only between two missions of a campaign, so a campaign's first mission is always by day; a sky-to-ocean palette split part-way down the playfield whose line moves every pass; a ten-line colour ramp on the ticker; a sky flash; ramps on the story scroller; and 16-step fades whose arithmetic carries between colour components and must be kept (`colour_lerp`, `0x016FF6`). There is no colour cycling. The per-row palette interface expresses all of these.
- `wof_palette_rows` tells the shell which palette applies to each output row. Palette 0 is reserved and all black: it applies to rows that no viewport covers, such as lines 162 and 200 of the play screen, where the original's copper list switches the bitplanes off.
- **Display list.** Every shape draw also appends a `wof_draw_t` record (4-character shape name, x, y, layer, flags, owner object id) to a per-pass list. The classic renderer ignores it. It exists so that an enhanced renderer can be added later.

No game logic depends on a drawing result: nothing reads pixels, masks, the blitter's zero flag or the collision register (`re/notes/drawing.md`). `MaskBuffer` is scratch space for the blit mask and the text template and is never read back. Ground height comes from map record types, not from pixels.

### 6.5 Audio model

A minimal Paula: four channels, each with sample pointer, length, period, volume, repeat pointer and length, and the DMA-style restart behaviour. The output rate conversion uses the NTSC clock constant 3,579,545 Hz divided by the period (3,546,895 Hz when running at 50 Hz). Left and right follow the Amiga channel layout (0 and 3 left, 1 and 2 right) with an optional stereo-width reduction in the shell.

The sound-effect engine (`sound_init`, `audio_irq`, `soundfx_vblank`) and the `songplay` player are ported against this model. Their interrupt entry points become functions called by the core's own timing: per VBlank, per channel-end event, per player timer tick.

### 6.6 What is not ported

The C runtime startup, OS glue stubs, memory management, view and copper construction (its semantics, the colour tables, the split line, the colour pokes and ramps, are reproduced through the palette rows), interrupt plumbing, Workbench handling, the debug and crash reporters, the protection check and the crack screen. Mark these `replace` or `drop` in `re/functions.csv`. Everything else is `port`.

## 7. Porting rules

### 7.1 Arithmetic

Port from the **disassembly**, not from a guess at the C source.

- Use `int16_t`, `uint16_t`, `int32_t`, `uint32_t`, `int8_t`, `uint8_t` explicitly. Never plain `int` for game values.
- A constant table the original indexes past its end reads the memory behind it, which can be a registered global: the wheel table `0x025E3E` at attitude 9 is `0x025E50`, which the same routine writes. The port reads such a table by its original address, from the registered global where one covers the byte and from the executable's image elsewhere (`wof_image16`); an oracle test over random states found the case.
- Reproduce every width change the listing shows. `ext.l` is a sign extension of a 16-bit value. `muls.w` multiplies two 16-bit values into 32 bits; what happens next (`move.w` or `move.l`) decides whether the product is truncated. `divs.w` divides 32 by 16 bits, truncates toward zero and yields a 16-bit quotient; `swap` afterwards means the remainder is used.
- Signedness follows the branch: `blt`, `bge`, `bgt`, `ble` are signed; `bcs`, `bcc`, `bhi`, `bls` are unsigned.
- A branch reads the flags of the last instruction that set them, which need not be the compare before it: `ship_sinking`'s `beq` at `0x011D00` reads a `move.w`, and a `bgt` after `subq.b` compares the byte result with its overflow, so `0x80` less one is not above zero. Port the flags of the instruction the branch reads.
- Wrap-around is behaviour. Do not widen a variable because it might overflow. Make the wrap explicit with a cast, because signed overflow is undefined in C.
- Shifts: `asr` is arithmetic; write it so that it is arithmetic on every compiler.
- A division by zero or a quotient overflow traps on a 68000. Assert in test builds. mathffp's own `SPDiv` reaches such a trap for a divisor whose exponent byte is zero and for one whose mantissa is below `0x100`; `src/ffp.c` counts both in `wof_ffp_traps` and reports them in the result's `trap` field, and a test holds the count to the number the original took.
- Floating point: where the listing calls the `ffp_` glue, the port calls its own integer implementation of that mathffp operation on the same 32-bit format (a 24-bit mantissa, a sign bit, a 7-bit excess-64 exponent): `wof_ffp_mul(a, b)` and its siblings of `src/ffp.h` where only the value is wanted, which is every call site the game reaches, and the `_cc` forms where the original branches on the returned condition codes. Never substitute `float` or `double`; rounding differs and the state would drift. Each operation has an oracle test against the routine in `original/kick.rom`, reached through the game's own glue, over edge cases, random operands and every operand the game was observed to produce, in result, registers and condition codes, natively and in WebAssembly.

### 7.2 Data

- File data is big-endian. Read it with explicit byte accessors. Never cast file bytes to a struct.
- Game structures get C structs with the original field order and widths. Record the original offsets in a comment or a static assertion table, because the tests map fields by offset.
- Pointers inside game structures become either real pointers or indices. Decide per structure and note it in the subsystem note. Save states and test comparisons must not depend on host pointer values. Data that the game changes after loading belongs to the save state as well: the facing markers at +8 of the `hellcat.shp` and `Torpedo.shp` records and the pixel data mirrored in place with them.
- Every allocation the game makes goes through `0x020874`, which sets `MEMF_CLEAR`, and the game relies on it: the map loader leaves the last four records of every map to the allocator. The port's arena hands out zeroed memory, also when an address is handed out again after `wof_arena_reset` or `wof_arena_release`, and a test holds it.
- Every table a mission allocates has a fixed place and a fixed capacity in the core's state (`src/mission.def`, record layouts in `src/records.def`): the map's record list, the target tables, the soldiers, the gun lists, the four pools, `MasterList` and `AthList`. A test holds the capacities against all fifteen maps. There are no pointers in them: a shape pointer is a handle, a pointer into the map a byte offset, a pointer to an allocation a flag. The arena is used only while assets load, so it does not grow from mission to mission.
- Every global that is ported gets an entry in a registry (`src/globals.def`, an X-macro: name, C type, original address). The test harness uses it to copy state between oracle and port with byte-order conversion.

### 7.3 Determinism

- All randomness goes through the port of `rand_beam`. Where the original reads the beam position register, the port takes the next value of the entropy stream: a small generator inside the core, seeded by `wof_init`, that produces values shaped like a real `VHPOSR` (high byte 0 to 255, low byte 0 to `0xE3`). One value is consumed per call, in the original call order. The test builds can replace the stream by an externally supplied one.
- No state outside the core influences logic, with two inputs named: the entropy stream, and the address the original's allocator gave the map's record list, `map_list_address` (`0x024628`), from which the explosion of a wreck at rest on land takes its world x, because the crash's call hands `object_spawn` the aircraft's position where it expects the map pointer, an original defect (`re/notes/porting-m5.md`). The tests fill it with the headless original's address at every map load; the release build uses the value of a first mission there, `0x24F404`, so a crash on land explodes where the harness's original explodes. `wof_state_save` and `wof_state_load` must round-trip exactly; a replay from a loaded state must match a replay from the start.

### 7.4 Working method

For each routine, in an order that follows the milestones:

1. `tools/skel.py ADDR`, then read the routine in the listing.
2. Name it and the globals it touches in `re/names.txt`; regenerate.
3. Write the C, with the origin comment.
4. If it is pure (arithmetic, table lookups, decoders, collision tests, state machines over plain structures): add an oracle test that runs the original and the port on the same randomised inputs and compares results and touched memory. This is mandatory for pure routines.
5. Set `status` in `re/functions.csv` to `ported` or `verified`, and `replace` or `drop` where section 6.6 applies. A routine that is ported only as far as the observed scripts execute it is `partial`: `tools/reach_observe.py` records under the headless original which routines and which basic blocks a set of scripts executes, every region they never execute becomes one marked stand-in in the C (`M5 STAND-IN: ...`, with the address it stands for), and `tools/reach_observe.py --cold` lists those regions and fails on one without a marker. Reaching a stand-in skips what it stands for, counts in `wof_standin_hits`, which the diagnostics overlay shows, and is logged in test builds, where every differential test demands an empty log; so a script that leaves the ported ground fails loudly instead of diverging quietly. Calls into the sound engine, M8's, are left out with a comment naming the routine rather than a marker, because one would be reached in almost every tick; what the engine writes is excluded in `tests/m4complete.py` as M8's until M8 ports it.
6. When a subsystem is understood, write `re/notes/NAME.md`: purpose, data structures with offsets, routine list, open points. Later sessions start from these notes instead of re-deriving them.

`re/functions.csv` is regenerated by the disassembler. Its `status` column is hand-edited and is carried over from the previous file on every regeneration; all other columns are recomputed.

## 8. Verification

| Level | Method |
|---|---|
| Routine | Oracle differential tests (section 7.4). Run with `.venv/bin/python -m pytest tests/` against the native library |
| Whole game, logic | **Headless original** (`tools/headless.py`, `re/notes/headless.md`). The original's own code runs from `main` on under the oracle: initialisation, the front end, mission setup, the inner loop, the VBlank servers and the key handler. No game logic is re-implemented. Stubbed are the OS calls of section 3.4 (files served from `original/disk`, memory from a bump allocator that never reuses an address, display records filled in and nothing drawn), the music player (its calls are recorded and answered as idle) and the crack's text screen (`0x01F41A`), which would draw entropy the port never draws. Custom-chip and CIA space is plain memory, except the beam position `0xDFF006`, served from the same entropy stream the port consumes and logged with its caller, and `JOY1DAT` and CIA-A PRA, which carry the scripted controller. `mathffp.library` is the real one, run from `original/kick.rom`, and so is console.device's `RawKeyConvert`, with the ROM's own default keymap. Unicorn 2.1.4 executes a memory-form shift as logical or arithmetic by bit 3 of the opcode, which there belongs to the address mode, instead of by the instruction; the three `asr.w d16(An)` of the executable are executed by a hook of `tools/m68k_fix.py` as a 68000 does, flags included, in the oracle and in the headless original, and a test holds the list against the listing (`re/notes/porting-m5.md`). A directory is listed in the disk image's own order, read from `original/wof.adf`. Routines can be observed by name: every entry is recorded with its registers and stack arguments, on request also the return with its condition codes and chosen memory ranges at both ends, and a test holds that observing changes no step. Writes and reads can be summarised instead of listed: every write is tagged with the phase it was made in (a VBlank server, `logic_tick`'s tree, `frame_update`'s tree, the main program) and joined into ranges, the record size of a table is read off the strides, and a read hook over chosen allocations says which routine read which offsets in which phase. **Time:** the program runs until it waits, and VBlanks happen only where it waits (the spins on `vblank_flag`, `WaitTOF`, `Delay`, and the start of a pass, which is owed the configured number of VBlanks since the previous one); nothing depends on instruction counts. A VBlank sets the controller registers from the script, delivers scripted keys, each with its qualifier word, through the game's own input handler, and calls the servers the game installed, `soundfx_vblank` and `vblank_server`, so the input byte, the tap and hold latches and the queue are the original's own work; injecting input bytes behind `read_joystick` is a second mode. The audio interrupt is never raised. **Output:** a dump of the executable's DATA and BSS range and of every allocation outside display memory after every tick and every pass, each step with a hash; the schedule as it happened (VBlank with raw state, pass, tick with its byte), which a port test replays through `wof_vblank` and `wof_pass`; on request a report of which routine wrote which address in each step. The port runs the same input; the states must agree. A test fails if any routine other than the copper builder and `text_render` reads display memory, which closes the read-back question of section 6.4 by observation |
| Front end | The schedule of a headless run, its VBlanks with their raw state and its keys with their qualifiers, is replayed through `wof_vblank`, `wof_key` and `wof_pass` with the fade setting at 0 and compared with the original VBlank by VBlank: every file opened, every music call, every drawing call with its position and text (the harness's observers on the drawing routines against the port's own trace in test builds), the VBlank at which the mission begins, and the ported globals of `src/globals.def` at the step where the front end ends. The line editor, the high-score routines and `path_sanitise` run against the original's own under the harness. The harness draws nothing, so what a screen looks like rests on these calls, on the contact sheets and on the owner's eyes (`re/notes/porting-m3.md`) |
| Mission, pass by pass | `tests/m4compare.py` records a mission script under the headless original, with the dump, observers on the blitter library's entries, the entropy log and the addresses each tick wrote, and replays its schedule through the port. In the **open loop** the port's registered state, its views, its entropy position and the mirror markers are set to the original's before every pass, so each pass is compared alone and a difference names its pass. In the **closed loop** the port runs on its own from the program's start and nothing is handed over but the entropy seed and the map list's address (section 7.3): the same comparisons run after every tick and after every pass, and the VBlanks a tick waited inside the restart are compared too. After every pass: every registered global and table, the drawing calls with their arguments, the entropy reads with their callers, the view in front, the palette of every output row, and the map draws against `tools/map_decode.py`; no stand-in may have been reached. A completeness test takes every address the original writes during a mission and demands that it is a registered field, compared in another form, or on a list with its writers, the reason and the milestone that owes it (`tests/m4complete.py`). The harness runs no blits, so no pixel of a mission scene is compared with the original; the drawing calls, the palette rows and the blitter model of the row Drawing stand for the picture (`re/notes/porting-m4.md`) |
| Whole game, replays | The port records (seed, input bytes) in the original's demo format. Replays are regression tests: final state hash and per-tick hashes are stored in `tests/replays/` |
| Page | The built `dist/wof.html` is opened from a `file://` URL in headless Chrome (DevTools protocol) and headless Firefox (WebDriver BiDi), both driven through Node's built-in WebSocket with nothing installed; each module skips when its browser is missing. Keys are pressed through the driver, never dispatched from a script, because a scripted event activates nothing. Checked: only local requests, a clean console, the exact pixels on the source canvas, the display box measured off the DOM in both video standards and after resizes made through the driver, the displayed canvas and a driver screenshot sampled against the source canvas, a steady clock in both standards, Web Audio untouched before an activating key and running after it. Both browsers are silenced from outside the page, Chrome with `--mute-audio` and Firefox with the profile preference `media.volume_scale`, which leaves the audio graph running. `WOF_FIREFOX_VISIBLE=1` adds a run in a visible Firefox window, the only check that can see a GPU canvas fault; the window must stay in front and uncovered while it runs, because a covered or background window stops the page's clock and the tests then fail as if the page stood still. A `devicePixelRatio` emulated through the DevTools protocol places the canvas on whole CSS pixels, so a box edge on half a CSS pixel is shifted by a device pixel or resampled there; a scale factor given on Chrome's command line with `--force-device-scale-factor` behaves like a real display and shows the picture exact to the pixel. The picture itself is therefore judged under such a true scale factor in Chrome, at the screen's real ratio in the visible Firefox window and in a large headless Firefox viewport (`tests/picture.py`): every framebuffer pixel against the screenshot at the centre of the block it is shown as, the picture's position fitted from its own colour edges to a fraction of a device pixel and compared with the DOM's rectangle, and the hardness of the block edges. These checks apply where a framebuffer pixel is shown as at least three device pixels in each direction, and refuse below that instead of passing |
| Drawing | The original's drawing routines drive the hardware blitter, so their results cannot be read from memory. The original routine runs under the oracle with the custom-chip space mapped as memory; each write to `BLTSIZE` is captured with the registers as they stand, a small model of the blitter's area mode (`tests/blitter.py`) replays the programme on a copy of the bitplanes, and the result, converted to indexed pixels, is compared with the port's framebuffer. Done for `shape_draw` over every shape at clipped and unclipped positions, on empty and non-empty backgrounds, on 5-plane and 4-plane targets. The model is documented hardware behaviour, not derived from the original; a comparison with a cycle-exact emulator is due when `line_draw` is ported |
| Picture | Framebuffer hashes per pass for the stored replays, once the classic renderer is declared correct for a scene by visual comparison with the contact sheets and with the original running in an Amiga emulator |
| Sound | Log of (tick, channel, sample id, period, volume) events compared between port and headless original |

If the blitter turns out to be driven only from a few assembly routines, the headless harness can intercept those routines and perform the blits on the emulated bitplanes, which also yields reference frames. This is optional.

## 9. Milestones

Each milestone ends with a working `dist/wof.html` and green tests. **M0, M1, M2, M3, M4, M5 and M6 are complete.** M4 was done in two parts: the world as a pass (the mission setup after the briefing, `frame_update`'s tree with the map, the scrolling at both scales, the dashboard, day and night and the mission half of `vblank_server`), then the player and the tick (`logic_tick`'s tree with the flight model on the ported floating point, the deck with the weapon menu and the lift, take-off, landing on a cable, refuelling and rearming in the hold, the crash with its restart inside the tick, the game over, `ingame_keys` with the pause and the commands, the mirror markers in the save state). It is compared with the headless original tick by tick and pass by pass in the open and the closed loop of section 8, over scripts that fly, turn, land, run out of fuel and lose every aircraft, a night mission, and the key runs of `tests/runs/`; a mission is flown on the page in Chrome and Firefox by the tests (`re/notes/porting-m4.md`). What M4 leaves marked for later, from `tools/reach_observe.py --cold`: the weapons, the targets and the soldiers for M5, the enemy aircraft and ships for M6, a campaign's next mission, the demo and the loaded game for M7, and the sound engine's slots for M8. M5 is done in two parts as M4 was: part 1, the pass (the targets, their fire, the soldiers, the flags, the pools, the objects drawn, the muzzle flash, the weapon counter, the sky flash, the balloons), is held to the headless original in the open loop over seventeen scripts with every differing step owed to a part-2 or later stand-in (`re/notes/porting-m5.md`); part 2, the tick (the drop, the weapons in flight and their hits, the guns' bullets, the targets' timers, the balloons, the crash on land), holds in the closed loop over eighteen scripts on maps a, b and c, and the open loop is owed only to M6 and M7. What M5 leaves marked: the enemy aircraft, the ships and an enemy airfield's launch for M6, a campaign's next mission and the promotion after a rank's last mission for M7. M6 is done in two parts as M5 was: part 1, the pass (the enemy aircraft with their wrecks and their guns' flash, the ships' guns and their shells, the aircraft on the ships' decks, the airfields, the 3-D view's enemy aircraft, the arrows, the kill counter), is held to the headless original in the open loop over twenty-four scripts on all fifteen maps with every differing step owed to a part-2 or later stand-in (`re/notes/porting-m6.md`); what the enemy does, the aircraft record field by field, the launches, the ships, the torpedo run and the carrier's defence, is in `re/notes/enemy.md`. Part 2, the tick (the launches by the countdown, the airfields and the ships, the enemy aircraft's flight and attack, the guns at them, the ships sinking, the carrier's hits and its sinking), holds in the closed loop over twenty-five scripts on all fifteen maps, and the open loop is owed only to M7 and M8. **The order of execution after M6, decided by the owner on 2026-09-26: M8 before M7**, so that the sound is in the page for the owner's test flights sooner; the numbering stays and M9 comes last. M3's front end runs with one further marked stand-in, the content and loading of a saved game (M7); what it ported and how it was compared is in `re/notes/porting-m3.md`. What M1 ported, how it was verified and what it left for later is in `re/notes/porting-m1.md`; the headless original of M2, how to run it and what it does not cover, is in `re/notes/headless.md`. What M3 builds on, all of it observed under the headless original, is in `re/notes/keys.md`, `re/notes/frontend.md` and `re/notes/highscore.md`.

| # | Deliverable | Accepted when |
|---|---|---|
| M0 | Build pipeline, empty core, shell with canvas, clock, input and audio plumbing | `dist/wof.html` opens from `file://`, shows a test pattern from the core at a steady emulated 60 Hz, plays a test tone after a key press, makes no network request |
| M1 | Virtual file system, arena, `load_file` with `Rpck`, shape tables by name, ILBM reader, palettes, font and text drawing, table extraction | the page shows the first picture, the title and the credit picture with correct colours and draws text in the game font; decoders pass oracle tests |
| M2 | Headless original (section 8) reaching the first pass of the inner loop | per-tick state dumps are produced for a scripted input stream and a fixed entropy stream; two runs give identical dumps |
| M3 | Front end as coroutines: story scroller, title sequence, rank selection, mission briefing, high-score display and entry, load and save dialogs; the key path with the port's keys, the line editor and the key conversion table | screens match the original in layout, timing and transitions (`re/notes/frontend.md`); for the same recorded inputs and keys the port reaches the same choices as the headless original (cursor, rank, file names, the bytes of a written `highscore`); high scores persist across reloads |
| M4 | World and player: map loading and drawing, scrolling, carrier, take-off and landing, flight model, dashboard, day and night | a mission can be started, flown and ended by landing or crashing; logic matches the headless original for recorded inputs. **Done** |
| M5 | Weapons and ground targets: guns, bombs, rockets, torpedoes, islands, bunkers, guns, soldiers, effects | as M4, on the first three maps. **Done** |
| M6 | Enemy aircraft, ships, torpedo attack view, carrier defence | as M4, on all 15 maps. **Done** |
| M7 | Missions, ranks, scoring, messages, save and load, demo record and playback, end sequence | a full campaign is playable; a recorded demo replays identically after a page reload |
| M8 | Sound effects engine and the music player | event logs match; music plays on the title and between missions as in the original |
| M9 | Shell polish: key configuration, gamepad, scaling options, the video standard as an option, pause, fullscreen | usable without reading documentation |

## 10. Points to establish

Each point is answerable from the listing. Record the answer in `re/notes/` and update this document where it states a fact. A point is due **before the milestone that consumes its answer starts**; the numbering is not an order.

| # | Point | Due before | Where to start, or status |
|---|---|---|---|
| 1 | Input byte and keyboard path | answered | `re/notes/input.md` and `re/notes/keys.md`. Left over: the alternative controller path behind `read_joy_dispatch` `0x01CB20` (due before M9) |
| 2 | Per-tick versus per-pass state changes | answered | `re/notes/passes.md`: what a pass writes and a tick reads, observed over seven mission scripts, with the couplings the seven scripts did not reach listed beside them, which the M5 scripts then reached (a soldier's death scores in a pass, a target's fire lowers the oil and the fuel in a pass), and the control at one, two and three VBlanks per pass. Measured on the owner's PAL Amiga on 2026-09-22 by 240 fps film: 2 VBlanks per pass in a quiet scene (the hold, the lift, the deck), with the story scroller's 2 VBlanks per change as the calibration of the capture chain; `tools/film_rate.py`. Left over: a busy scene, where the original may take 3 |
| 3 | The object system: the pools `Ricochet`, `Splashes`, `Smoke`, `Balloons`; record layout, handler dispatch, draw order | answered | `re/notes/objects.md`: fourteen tables with record sizes, builders and walkers per phase; no allocator but an in-use field and a scan for the first free record; behaviour by a chain of tests on the kind byte and the type word, not a jump table; the order of a tick and of a pass; the player's record at `0x025078` field by field (`0x1E` bytes; the words behind it are the ships' deck blocks); a width table for M5 and M6. `0x025AAA` is `landing_stall`, the stick forward alone while flying left, which the touch-down on the deck needs. The pools are answered in `re/notes/porting-m5.md`: `Ricochet` is dead, its only writer has no caller; `Balloons` fly after the promotion at a rank's last mission. An object's y moves by the whole part of its velocity long, whose fraction never carries, and `+0x22` is the weapon type, 0 a rocket, 1 a bomb, 2 the torpedo. The state words of the enemy aircraft are answered in `re/notes/enemy.md`: 0 free, 2 flying, 4 shot down and falling, `0x10` burning on land; 1 and 8 are cases nothing sets |
| 4 | Shape name resolution | answered | `re/notes/shapes.md`. `MasterList` and `AthList` are not object lists: they are the combined shape pointer tables that map records index, full size and eighth scale |
| 5 | Map record semantics and the world coordinate system | answered | `re/notes/map.md` and section 3.5. `tools/map_decode.py` predicts slot and screen position of every map draw of 684 passes of a flight, in both views, and the effect of one changed record; `ground_height` `0x015714` is tested under the oracle |
| 6 | Display geometry | answered | `re/notes/display.md` for the geometry, `re/notes/frontend.md` for what the front-end screens load, draw and wait for, observed VBlank by VBlank. Left over: the real duration of the fades, which are CPU-bound in the original, so M3 gives a fade step a fixed number of VBlanks as a provisional setting. The sky flash is answered (`re/notes/porting-m5.md`): a rocket's hit on land or a crash on land sets a count of 5 in the tick, white, or red on a target, and `flip_buffers` pokes COLOR01 on the odd counts |
| 7 | Drawing routines and read-back | answered, the line mode provisionally | `re/notes/drawing.md`: no logic reads drawing results. `line_draw` `0x021318` is ported from the documented line mode (`src/draw.c`): the clipping is the original's own arithmetic and the walk is the Bresenham of `dmax + 1` pixels from the first end; its only live caller is `draw_player` `0x0103A6` drawing the cable of a landed aircraft, deck state 7, which the landing script reaches, and `tests/blitter.py` holds the port's clipping, octant, accumulator, start and length to the original's register programme over 400 random lines. Left over: the pixel pattern of the line mode itself, to be compared with a cycle-exact emulator. The front end does not need it: every `Draw` it makes is a side of a box and parallel to an axis, which a test observes, and the port's `Draw` refuses a sloped line |
| 8 | Randomness and seeding | answered | `re/notes/random.md` |
| 9 | 50 Hz versus 60 Hz | answered | `re/notes/random.md`: the program never checks |
| 10 | Sound-effect tables and the song format | M8 | `songplay` has symbols and is cheap to read at any time |
| 11 | The shape record header words at +8, +10, +12 | answered | `re/notes/shapes.md` and section 3.5 |
| 12 | High-score file layout, save-game layout | M7 for the save game | The high-score file is answered (`re/notes/highscore.md`, section 6.2). The save-game layout is open: `0x015EC2` holds the table of ranges a saved game covers, and `opt_invert_vertical` lies inside one of them |
| 13 | The game's floating point | answered | `re/notes/ffp.md`. The nine operations are ported bit-exact and tested against `mathffp 34.1` in `original/kick.rom` on both targets. `player_motion` `0x01BDFA` and `aircraft_motion` `0x01D796` are described, and a model of each reproduces every observed entry of the original; their constants are the tables `attitude_factor` `0x025B0C` and `sine_degrees` `0x025B74`. `format_float` `0x021A40` is dead, so the game proper uses six of the nine operations |

Points 2, 3 and 5 were answered by observing the headless original rather than by reading alone: its change report and write summary name, for every tick and every pass, the addresses written and the routines that wrote them, and the notes mark every finding as observed, with the run that shows it, or as read. The glyphs for the dialogs that use the system default font come from the owner's Kickstart ROM (`re/notes/system-font.md`).
