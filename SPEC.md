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
3. **Inner loop** (`0x01010E`): one pass per displayed frame. Each pass calls `frame_update` (`0x010228`), a fixed pipeline of about twenty subsystem routines, some assembly and some C, and then `run_queued_ticks` (`0x0114D8`).

**Timing is a fixed-step simulation driven by an input queue:**

- The VBlank interrupt server `vblank_server` (`0x011754`) counts VBlanks. On **every 4th VBlank** it obtains one *input byte* and appends it to a FIFO of at most 6 entries (`input_queue` at `0x027356`, count at `0x027354`). When the queue is full, the oldest entry is dropped.
- `run_queued_ticks` executes **one logic tick per queued input byte**.
- The logic rate is therefore the VBlank rate divided by 4: **15 Hz on NTSC** (the machine the game was designed for), 12.5 Hz on PAL.
- The input byte comes from `read_joystick` (`0x01CA32`) in normal play.
- `demo_mode` (`0x026D4C`): `0` is normal play; `1` is **demo playback**, where input bytes are read from a buffer (at most `0x1386` entries, a `0xFF` byte ends it); `2` is demo recording. The executable refers to a file `wofdemo`, which is not on this disk.

This design is what makes a verifiable port possible: the simulation is a function of initial state, the input byte stream, and one further input, the **entropy stream**. The game's only random source, `rand_beam` (`0x0203BE`, 43 call sites), returns a constant exclusive-ored with the raster beam position at the moment of the call, so in the original all randomness is CPU timing. The port replaces the beam position by an explicit, reproducible stream of values (`re/notes/random.md`). The program never checks the machine's video rate; at 50 Hz everything simply runs at five sixths of the speed.

**The input byte** is assembled by `read_joystick` (`0x01CA32`) and is the only channel by which controls reach game logic. Its low byte is: bit 0 stick forward, bit 1 stick back, bit 2 stick right, bit 3 stick left, bit 4 fire held for 10 or more VBlanks, bit 5 fire tapped and released inside 10 VBlanks. Bits 6 and 7 are unused. Forward is the stick pushed away from the player, which the hardware reports as bit 9 exclusive-or bit 8 of `JOY1DAT`; it moves the cursor up in the menus and **climbs** in flight, because the game is seen from the side and up on the stick is up on the screen; the manual's take-off instructions say the same and the owner's real Amiga confirms it. The reversed-vertical option, which the manual gives as Control-F, swaps the two bits for players who want a pilot's stick; the owner is one of them, so the port must offer it and remember it. Opposing directions cancel to centre. The latches are not cleared between the front end and a mission: the release of the press that ends the briefing is sampled after the queue is cleared, so the first tick of the mission can carry the tap bit. The tap and hold timing runs at VBlank rate, not tick rate, and latches between samples. The keyboard is a separate path: an input.device handler at priority 127 buffers raw Amiga key codes with their qualifier words, ten deep, and does not feed the tick. Five routines read the buffer: the menus, a release wait, the line editor of the name and file-name entry, the briefing and the in-flight commands. The game tests one qualifier bit, Control (`0x0008`), and turns a raw code into a character through console.device's `RawKeyConvert` with the system's default keymap, accepting a key only when exactly one character comes back. Details and consequences for the port: `re/notes/input.md` and `re/notes/keys.md`.

**Passes are not pure rendering.** `frame_update` begins with `wait_vblank` (`0x01AA3E`), so there is at most one pass per VBlank, counted from the previous buffer flip, and it contains game logic that runs once per pass, not per tick: soldiers move and die, score is added, ticker messages are queued, and the restart after a lost aircraft and the game-over countdown advance. Nine routines in its call tree call `rand_beam`. The tick in turn reads state the pass leaves behind (the flag at `0x026E3C`, a frame was drawn since the last tick, and the pass counter at `0x0253C8`). The interleaving of VBlanks, passes and ticks is therefore an input of the simulation, like the input bytes and the entropy stream. How many VBlanks a pass takes on a real A500 is not established; it sets the speed of everything that runs per pass (`re/notes/drawing.md`).

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
| mathffp: `SPFix`, `SPFlt`, `SPCmp`, `SPTst`, `SPNeg`, `SPAdd`, `SPSub`, `SPMul`, `SPDiv`, opened on first use by C-library glue at `0x021C9C`–`0x021D2E` | the game's logic computes with Motorola fast floating point in three routines, two of them in the call tree of the tick (`re/notes/headless.md`). The port reproduces the nine operations bit-exact in integer code, tested against the ROM's routines under the oracle (section 7.1) |
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

**Maps.** Two u32 values (the first equals the file length), then a sequence of u16 records. Low bits select a tile or object type, high bits are flags (`0x8000` occurs frequently). Record semantics are to be established from the map loader.

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
| `tools/rpck.py`, `tools/ppkc.py` | reference decoders; `ppkc.py SHP PALETTE OUT.png` renders a contact sheet |
| `tools/fd/` | AmigaOS library offset tables used to name OS calls |

**Listing conventions.** Routine headers give the kind (`C` or `asm`), the stack frame size, the far-call slot, and the callers. Operands that use A4 are followed by the absolute address or its name. Relocated longs are shown as names or as the string they point to. OS calls are named. Blocks marked *found by gap sweep* are code that nothing references by control flow (uncalled library routines or routines reached only through computed addresses).

**Naming workflow.** When a routine or global is understood, add it to `re/names.txt` and regenerate. The listing, the skeletons and the inventory pick the name up everywhere. Never edit `re/Wings.lst` by hand.

**The oracle.** `Oracle.call(addr, *args, regs=...)` executes an original routine on a real 68000 model with the executable mapped at the listing addresses. Build stack arguments with `Oracle.W()` for `int` and `Oracle.L()` for `long` and pointers. Pass `a4=0x02AFFE` when the routine touches globals. Its self-test runs `rpck_unpack` on all ten packed files and compares the output with `tools/rpck.py`.

## 5. Build

`tools/build.py` produces `dist/wof.html` in these steps (`--native` also builds the test library):

1. **Extract tables.** `tools/extract_tables.py` reads `re/tables.toml`, a manifest of (name, address, element type, count) entries, and writes `src/gen/tables.c` and `src/gen/tables.h` from the bytes of `original/disk/Wings_of_Fury/Wings`. Every constant table, name list, text and tuning array the port needs from the DATA or CODE hunk is obtained this way. Byte order is converted during extraction. The same step reads the topaz 8 glyphs, location table and metrics from `original/kick.rom`, locating the font by its contents so that other Kickstart versions work, and falls back to the game's own font, in the build with a message and in the core when it draws, when the ROM is absent. The key conversion comes from the ROM in the same step: the build runs console.device's `RawKeyConvert` with the ROM's default keymap, both located by their contents as the headless original locates them, for every raw code under the qualifier combinations the shell can send, and writes the single characters as a table; the game never asks for more than one character and never brings a keymap of its own (`re/notes/keys.md`). Without the ROM the build says so and the table holds only what the positions of the raw codes give: letters, digits and the space bar. `src/gen/` is ignored by version control.
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

A palette entry is RGBA in memory order, which canvas `ImageData` takes without conversion. `wof_init` does not reset the arena, because the shell allocates the file blob from it before calling `wof_init`. `wof_state_load` checks a magic and a version and leaves the running state untouched when they do not match. A save state is the bytes of the core's state struct, which holds no pointers and no padding; this is valid between little-endian hosts, which both targets are.

`wof_vblank` is the port of `vblank_server` together with `vblank_every_frame`. It takes the **raw controller state** of that VBlank, not a finished input byte: bit 0 stick forward (up), bit 1 stick back (down), bit 2 right, bit 3 left, bit 4 fire button currently down. The shell maps the up key and a gamepad pushed forward to bit 0. The core runs the fire-button press timer, cancels opposing directions, applies the reversed-vertical option, assembles the input byte, counts to 4 and queues it, including the 6-entry limit and demo playback and recording. Keeping the tap and hold discrimination inside the core is required for fidelity, because it is evaluated at 60 Hz while sampling happens at 15 Hz (`re/notes/input.md`).

`wof_key` is the port of `input_handler`: it appends a raw Amiga key code and its qualifier word to the ten-deep key buffer with the original's drop rule, and the ported readers take it from there unchanged. The differential tests replay the keys of a headless schedule through it. `wof_port_key` is what the shell calls, a thin layer of the port's own in front of `wof_key`: while the line editor is active it passes every key on as it came; otherwise it rewrites the port's command keys into the code and qualifier the original's readers expect and applies the port's restrictions (section 6.2). The state that decides this (line editor active, paused, briefing) lives in the core, which is why the layer does. The picture viewer's `wof_key_press` goes when M3 replaces the viewer.

`wof_set_invert_vertical` gives the core the owner's remembered preference for the vertical flip. A core that was never given one behaves as the original, which is what the differential tests run. Once given, the core keeps the preference outside the saved game, the flip command changes both, and when a loaded game has overwritten `opt_invert_vertical` (`0x0254F6`, which lies inside the range a saved game covers) the core restores it from the preference. The shell reads `wof_invert_vertical` to store the value.

### 6.2 Shell

Plain JavaScript modules, no framework, no bundler other than the build script (section 5, step 4).

- **Clock.** A fixed-rate accumulator driven by `requestAnimationFrame` issues `wof_vblank` calls at the VBlank rate of the video standard, 50 Hz of emulated time on PAL and 60 on NTSC, each followed by one `wof_pass`, independent of the monitor's refresh rate. The original allows at most one pass per VBlank and on real hardware a pass takes longer than that; since logic runs per pass (section 3.3), the number of VBlanks per pass is a core setting, provisionally 2, until point 2 of section 10 is measured. After a stall, at most 24 VBlanks are replayed, which matches the original's queue limit of 6 ticks.
- **Video.** Canvas 2D or WebGL. The indexed framebuffer is converted through the per-row palettes to RGBA. A 2D context must be requested with `willReadFrequently: true`, which selects a software-backed canvas: in GPU-composited Firefox the accelerated canvas can drop `putImageData` entirely, so that the canvas reads back as one colour and the player sees a black picture. Headless Firefox composites in software and does not show the fault. **Video standard:** one shell setting, PAL or NTSC, selects the VBlank rate (50 or 60 Hz) and the pixel aspect together, as the machine does. The executable is the same for both and never checks. **PAL is the default**: this disk comes from a PAL region, its added artwork is 256 lines high, and the owner's real Amiga, against which the port is compared, is a PAL machine. **Aspect:** on PAL a low-resolution pixel is 16/15 as wide as it is tall, so a framebuffer pixel, which is a high-resolution pixel, is 8/15 and the 640 x 214 framebuffer is shown in a box of 1024 : 642. On NTSC, where 320 x 200 fills a 4:3 screen, a low-resolution pixel is 5/6 as wide as tall and the box is 800 : 642. The picture is never shown with square framebuffer pixels, which gives a strip three times as wide as it is high. **Size:** the picture fills the largest box of that ratio that fits the browser window, centred on black, recomputed on every resize, in fullscreen and when `devicePixelRatio` changes. The box is laid out in whole device pixels and only then converted to CSS pixels, so the displayed canvas has a backing store of exactly its CSS size times `devicePixelRatio` and the browser resamples nothing a third time. Because the pixel aspect rules out whole-number factors in both directions, scaling is done in two steps so that pixels stay crisp and evenly sized: a whole-number nearest-neighbour enlargement to at least the box size in device pixels, then a smooth reduction to the exact size; where both factors are 1 the source is reduced directly. Three canvases carry this: the 640 x 214 source canvas that receives `putImageData`, which stays software-backed as described above and is never on the page, the enlargement, and the displayed canvas. The last two are accelerated; `drawImage` is not subject to the Firefox fault, which the visible Firefox run confirms. The shell names the three on `window.__wofVideo`, because after scaling the exact framebuffer pixels exist only on the source canvas and the page tests need them. Nothing covers the picture permanently: the key hint goes away with the sound prompt on the first activating key press and comes back with the diagnostics overlay. A square-pixel, whole-number mode can be an option in M9.
- **Input.** Keyboard and Gamepad API are merged into the raw state word passed to `wof_vblank`. A button that goes down and up again between two VBlanks is held sticky until the next `wof_vblank`, so short taps survive; the original samples a level, so this only compensates for the browser's coarser event timing. Menu and text-entry keys take the second path: the shell maps `KeyboardEvent.code`, which is positional, to raw Amiga key codes, which are also positional, and feeds the core's key buffer. The key map is configurable and stored locally. The original's key commands (manual, last page, and `re/notes/keys.md`: pause on Escape, and Control with R, C, F, G and L for restart, clearing the high scores, the vertical flip, save and load; Control-S switches the music and is not in the manual; the manual's Control-D, which would show the high scores, is not in this executable, and the port leaves it out) cannot be taken over as they are, because a browser keeps Control with those letters for itself (reload, find, address bar) and a page cannot prevent all of them. **The port's keys, decided with the owner**, by `KeyboardEvent.code`: `KeyP` pauses and continues, `KeyF` flips the vertical control, `KeyG` saves (on the carrier only, as in the original), `KeyL` loads, `KeyM` switches the music (`KeyS` is the stick pulled back), `KeyR` restarts and `KeyC` clears the high scores; `Enter` chooses in a menu beside fire, and the arrow keys move. `KeyR` and `KeyC` act only while the game is paused, `KeyR` in the briefing as well: without Control in front of them a stray key would throw a campaign away, and the original accepts both while paused, so this narrows the original and adds nothing to it. `Escape` is a second pause key, and the shell asks the core to pause, as a request and not a toggle, whenever fullscreen is left: a browser takes Escape to leave fullscreen and a page cannot prevent that, so with both rules Escape always pauses. Inside the line editor every key is a character or an editing key and no command applies. The shell sends the qualifier bits of Shift and Caps Lock, never Control, and ignores a key pressed together with Control, Alt or Command. **The vertical flip is a preference, not game state**: the owner flies with it on, so the shell stores it with its settings, hands it to the core at start, and the remembered value wins over a loaded game, which in the original overwrites it (`wof_set_invert_vertical`, section 6.1). This is a deliberate divergence from the original, confirmed by the owner. No modifier key may ever be mapped: with Control as fire and W as up, firing while climbing is Ctrl+W, which closes the tab and which a page cannot prevent.
- **Audio.** The shell pulls PCM from `wof_audio_render` in blocks that correspond to emulated time and plays them through an `AudioWorklet`, fed by `postMessage`. The worklet module is inlined and loaded from a `data:` URL on a `file://` page, where a Blob URL is refused as a cross-origin load, and from a Blob URL elsewhere. Scheduled `AudioBufferSourceNode` blocks are the fallback; the query `?audio=buffers` forces it so that the tests can exercise it. Audio starts on the first event that really activates the page, which is not the same as the first event: a modifier pressed on its own, such as the Command of a console or screenshot shortcut, is a `keydown` that activates nothing, and a context built there is born suspended and logs an autoplay warning. The shell asks `navigator.userActivation.isActive` where it exists and otherwise ignores modifier keys, dead keys and keys pressed with a modifier held. It builds and resumes the context in the same task as the event, keeps listening and retrying until the context state is running, and only then removes the prompt that asks for a key.
- **Storage.** `highscore` and saved games are written through the virtual file system to `localStorage`, base64-encoded, under a `wof:` prefix; the shell's own settings, the vertical flip among them, live under the same prefix. `highscore` is 360 bytes, ten entries of a u32 score, a u16 rank and a 30-byte NUL-padded name, best first; a missing file reads as ten empty entries, and clearing the high scores deletes the file (`re/notes/highscore.md`). The load and save dialog shows the first six entries of the game's directory whose names begin with `wof.`, in the order `ExNext` hands them out, which on the original's disk is the order of the directory's hash chains and not the alphabet. The virtual file system reproduces that order from the names alone: an entry's chain is the AmigaDOS name hash modulo 72, chains are walked upward, and inside a chain a newer file comes before an older one. A name keeps its case as typed. That Kickstart 1.3 walks the chains in this order and puts a new entry at the head of its chain is documented behaviour which neither a run nor the disk image has confirmed (`re/notes/frontend.md`).
- **Pause** when the page is hidden.

### 6.3 Blocking code becomes coroutines

The original's front end blocks: it waits for VBlanks, for `Delay`, for the fire button, for fades. A browser page cannot block, and from `file://` there is no `SharedArrayBuffer` to block in a worker. Therefore:

- The main program (`main` and everything that can wait) is ported as a **stackless coroutine** in the protothreads style: a `switch`-based resume point, with locals that live across a wait moved into a context struct. The original's linear control flow is kept; each original wait becomes `CO_WAIT_UNTIL(condition)` or `CO_YIELD()`.
- `wof_pass()` resumes the coroutine once. During play this is exactly one pass of the inner loop.
- Routines that never wait are ported as ordinary functions.

### 6.4 Video model

The original display is planar. The port uses **8-bit indexed framebuffers** and applies the palette at presentation, so that fades, the day and night palettes, colour cycling and any palette change part-way down the screen behave as in the original.

- Shapes are converted from plane data and plane masks to indexed pixels once, at load. `tools/ppkc.py` shows the pixel values but is not the reference for drawing: the port keeps per shape the clear and set bytes (+12, +13), the union of its plane masks, its plane count and plane size, and blits against the existing framebuffer value exactly as `shape_blit` (`0x020B0C`) does, including the opaque cases and the depth of the target (the dashboard has 4 planes).
- All drawing primitives of the original (shape blit with transparency, masked and clipped variants, scrolling, text, screen copies) are reimplemented on indexed pixels with identical clipping and identical draw order.
- The original builds no OS View. It keeps its own view and viewport records, builds copper lists and writes `COP1LC` itself (`re/notes/display.md`). The play screen is three stacked areas, 214 lines in all: the playfield, 320 x 162 low resolution with 5 planes, at line 0; the dashboard, 640 x 37 high resolution with 4 planes, at line 163; the message ticker, 640 x 13 high resolution with 1 plane, at line 201; lines 162 and 200 are blank. Playfield and dashboard are double-buffered and the swap is one `COP1LC` write; the ticker is single-buffered and scrolled inside `vblank_server`. Front-end screens use 200 lines in several formats, tabulated in the note. The shell output is 640 pixels wide with low-resolution pixels doubled.
- Colours are 32-word tables per viewport. The mechanisms to reproduce are: the day and night palette files, chosen once per mission; a sky-to-ocean palette split part-way down the playfield whose line moves every pass; a ten-line colour ramp on the ticker; a sky flash; ramps on the story scroller; and 16-step fades whose arithmetic carries between colour components and must be kept (`colour_lerp`, `0x016FF6`). There is no colour cycling. The per-row palette interface expresses all of these.
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
- Reproduce every width change the listing shows. `ext.l` is a sign extension of a 16-bit value. `muls.w` multiplies two 16-bit values into 32 bits; what happens next (`move.w` or `move.l`) decides whether the product is truncated. `divs.w` divides 32 by 16 bits, truncates toward zero and yields a 16-bit quotient; `swap` afterwards means the remainder is used.
- Signedness follows the branch: `blt`, `bge`, `bgt`, `ble` are signed; `bcs`, `bcc`, `bhi`, `bls` are unsigned.
- Wrap-around is behaviour. Do not widen a variable because it might overflow. Make the wrap explicit with a cast, because signed overflow is undefined in C.
- Shifts: `asr` is arithmetic; write it so that it is arithmetic on every compiler.
- A division by zero or a quotient overflow traps on a 68000. Assert in test builds.
- Floating point: where the listing calls the `ffp_` glue, the port calls its own integer implementation of that mathffp operation on the same 32-bit format (a 24-bit mantissa, a sign bit, a 7-bit excess-64 exponent). Never substitute `float` or `double`; rounding differs and the state would drift. Each operation gets an oracle test against the routine in `original/kick.rom`, over edge cases and random operands.

### 7.2 Data

- File data is big-endian. Read it with explicit byte accessors. Never cast file bytes to a struct.
- Game structures get C structs with the original field order and widths. Record the original offsets in a comment or a static assertion table, because the tests map fields by offset.
- Pointers inside game structures become either real pointers or indices. Decide per structure and note it in the subsystem note. Save states and test comparisons must not depend on host pointer values. Data that the game changes after loading belongs to the save state as well: the facing markers at +8 of the `hellcat.shp` and `Torpedo.shp` records and the pixel data mirrored in place with them.
- Every global that is ported gets an entry in a registry (`src/globals.def`, an X-macro: name, C type, original address). The test harness uses it to copy state between oracle and port with byte-order conversion.

### 7.3 Determinism

- All randomness goes through the port of `rand_beam`. Where the original reads the beam position register, the port takes the next value of the entropy stream: a small generator inside the core, seeded by `wof_init`, that produces values shaped like a real `VHPOSR` (high byte 0 to 255, low byte 0 to `0xE3`). One value is consumed per call, in the original call order. The test builds can replace the stream by an externally supplied one.
- No state outside the core influences logic. `wof_state_save` and `wof_state_load` must round-trip exactly; a replay from a loaded state must match a replay from the start.

### 7.4 Working method

For each routine, in an order that follows the milestones:

1. `tools/skel.py ADDR`, then read the routine in the listing.
2. Name it and the globals it touches in `re/names.txt`; regenerate.
3. Write the C, with the origin comment.
4. If it is pure (arithmetic, table lookups, decoders, collision tests, state machines over plain structures): add an oracle test that runs the original and the port on the same randomised inputs and compares results and touched memory. This is mandatory for pure routines.
5. Set `status` in `re/functions.csv` to `ported` or `verified`, and `replace` or `drop` where section 6.6 applies.
6. When a subsystem is understood, write `re/notes/NAME.md`: purpose, data structures with offsets, routine list, open points. Later sessions start from these notes instead of re-deriving them.

`re/functions.csv` is regenerated by the disassembler. Its `status` column is hand-edited and is carried over from the previous file on every regeneration; all other columns are recomputed.

## 8. Verification

| Level | Method |
|---|---|
| Routine | Oracle differential tests (section 7.4). Run with `.venv/bin/python -m pytest tests/` against the native library |
| Whole game, logic | **Headless original** (`tools/headless.py`, `re/notes/headless.md`). The original's own code runs from `main` on under the oracle: initialisation, the front end, mission setup, the inner loop, the VBlank servers and the key handler. No game logic is re-implemented. Stubbed are the OS calls of section 3.4 (files served from `original/disk`, memory from a bump allocator that never reuses an address, display records filled in and nothing drawn), the music player (its calls are recorded and answered as idle) and the crack's text screen (`0x01F41A`), which would draw entropy the port never draws. Custom-chip and CIA space is plain memory, except the beam position `0xDFF006`, served from the same entropy stream the port consumes and logged with its caller, and `JOY1DAT` and CIA-A PRA, which carry the scripted controller. `mathffp.library` is the real one, run from `original/kick.rom`, and so is console.device's `RawKeyConvert`, with the ROM's own default keymap. A directory is listed in the disk image's own order, read from `original/wof.adf`. Routines can be observed by name: every entry is recorded with its registers and stack arguments, and a test holds that observing changes no step. **Time:** the program runs until it waits, and VBlanks happen only where it waits (the spins on `vblank_flag`, `WaitTOF`, `Delay`, and the start of a pass, which is owed the configured number of VBlanks since the previous one); nothing depends on instruction counts. A VBlank sets the controller registers from the script, delivers scripted keys, each with its qualifier word, through the game's own input handler, and calls the servers the game installed, `soundfx_vblank` and `vblank_server`, so the input byte, the tap and hold latches and the queue are the original's own work; injecting input bytes behind `read_joystick` is a second mode. The audio interrupt is never raised. **Output:** a dump of the executable's DATA and BSS range and of every allocation outside display memory after every tick and every pass, each step with a hash; the schedule as it happened (VBlank with raw state, pass, tick with its byte), which a port test replays through `wof_vblank` and `wof_pass`; on request a report of which routine wrote which address in each step. The port runs the same input; the states must agree. A test fails if any routine other than the copper builder and `text_render` reads display memory, which closes the read-back question of section 6.4 by observation |
| Whole game, replays | The port records (seed, input bytes) in the original's demo format. Replays are regression tests: final state hash and per-tick hashes are stored in `tests/replays/` |
| Page | The built `dist/wof.html` is opened from a `file://` URL in headless Chrome (DevTools protocol) and headless Firefox (WebDriver BiDi), both driven through Node's built-in WebSocket with nothing installed; each module skips when its browser is missing. Keys are pressed through the driver, never dispatched from a script, because a scripted event activates nothing. Checked: only local requests, a clean console, the exact pixels on the source canvas, the display box measured off the DOM in both video standards and after resizes made through the driver, the displayed canvas and a driver screenshot sampled against the source canvas, a steady clock in both standards, Web Audio untouched before an activating key and running after it. Both browsers are silenced from outside the page, Chrome with `--mute-audio` and Firefox with the profile preference `media.volume_scale`, which leaves the audio graph running. `WOF_FIREFOX_VISIBLE=1` adds a run in a visible Firefox window, the only check that can see a GPU canvas fault. A `devicePixelRatio` emulated through the DevTools protocol places the canvas on whole CSS pixels, so a box edge on half a CSS pixel is shifted by a device pixel or resampled there; a scale factor given on Chrome's command line with `--force-device-scale-factor` behaves like a real display and shows the picture exact to the pixel. The picture itself is therefore judged under such a true scale factor in Chrome, at the screen's real ratio in the visible Firefox window and in a large headless Firefox viewport (`tests/picture.py`): every framebuffer pixel against the screenshot at the centre of the block it is shown as, the picture's position fitted from its own colour edges to a fraction of a device pixel and compared with the DOM's rectangle, and the hardness of the block edges. These checks apply where a framebuffer pixel is shown as at least three device pixels in each direction, and refuse below that instead of passing |
| Drawing | The original's drawing routines drive the hardware blitter, so their results cannot be read from memory. The original routine runs under the oracle with the custom-chip space mapped as memory; each write to `BLTSIZE` is captured with the registers as they stand, a small model of the blitter's area mode (`tests/blitter.py`) replays the programme on a copy of the bitplanes, and the result, converted to indexed pixels, is compared with the port's framebuffer. Done for `shape_draw` over every shape at clipped and unclipped positions, on empty and non-empty backgrounds, on 5-plane and 4-plane targets. The model is documented hardware behaviour, not derived from the original; a comparison with a cycle-exact emulator is due when `line_draw` is ported |
| Picture | Framebuffer hashes per pass for the stored replays, once the classic renderer is declared correct for a scene by visual comparison with the contact sheets and with the original running in an Amiga emulator |
| Sound | Log of (tick, channel, sample id, period, volume) events compared between port and headless original |

If the blitter turns out to be driven only from a few assembly routines, the headless harness can intercept those routines and perform the blits on the emulated bitplanes, which also yields reference frames. This is optional.

## 9. Milestones

Each milestone ends with a working `dist/wof.html` and green tests. **M0, M1 and M2 are complete.** What M1 ported, how it was verified and what it left for later is in `re/notes/porting-m1.md`; the headless original of M2, how to run it and what it does not cover, is in `re/notes/headless.md`. What M3 builds on, all of it observed under the headless original, is in `re/notes/keys.md`, `re/notes/frontend.md` and `re/notes/highscore.md`.

| # | Deliverable | Accepted when |
|---|---|---|
| M0 | Build pipeline, empty core, shell with canvas, clock, input and audio plumbing | `dist/wof.html` opens from `file://`, shows a test pattern from the core at a steady emulated 60 Hz, plays a test tone after a key press, makes no network request |
| M1 | Virtual file system, arena, `load_file` with `Rpck`, shape tables by name, ILBM reader, palettes, font and text drawing, table extraction | the page shows the first picture, the title and the credit picture with correct colours and draws text in the game font; decoders pass oracle tests |
| M2 | Headless original (section 8) reaching the first pass of the inner loop | per-tick state dumps are produced for a scripted input stream and a fixed entropy stream; two runs give identical dumps |
| M3 | Front end as coroutines: story scroller, title sequence, rank selection, mission briefing, high-score display and entry, load and save dialogs; the key path with the port's keys, the line editor and the key conversion table | screens match the original in layout, timing and transitions (`re/notes/frontend.md`); for the same recorded inputs and keys the port reaches the same choices as the headless original (cursor, rank, file names, the bytes of a written `highscore`); high scores persist across reloads |
| M4 | World and player: map loading and drawing, scrolling, carrier, take-off and landing, flight model, dashboard, day and night | a mission can be started, flown and ended by landing or crashing; logic matches the headless original for recorded inputs |
| M5 | Weapons and ground targets: guns, bombs, rockets, torpedoes, islands, bunkers, guns, soldiers, effects | as M4, on the first three maps |
| M6 | Enemy aircraft, ships, torpedo attack view, carrier defence | as M4, on all 15 maps |
| M7 | Missions, ranks, scoring, messages, save and load, demo record and playback, end sequence | a full campaign is playable; a recorded demo replays identically after a page reload |
| M8 | Sound effects engine and the music player | event logs match; music plays on the title and between missions as in the original |
| M9 | Shell polish: key configuration, gamepad, scaling options, the video standard as an option, pause, fullscreen | usable without reading documentation |

## 10. Points to establish

Each point is answerable from the listing. Record the answer in `re/notes/` and update this document where it states a fact. A point is due **before the milestone that consumes its answer starts**; the numbering is not an order.

| # | Point | Due before | Where to start, or status |
|---|---|---|---|
| 1 | Input byte and keyboard path | answered | `re/notes/input.md` and `re/notes/keys.md`. Left over: the alternative controller path behind `read_joy_dispatch` `0x01CB20` (due before M9) |
| 2 | Per-tick versus per-pass state changes | M4 | Established so far (`re/notes/drawing.md`): the per-pass logic list and the two variables through which passes and ticks couple. Open: how many VBlanks a pass takes on a real or cycle-exact emulated A500, to be measured; and the object-table fields written during a pass, which the memory-compare run of the headless original closes |
| 3 | The object system: the pools `Ricochet`, `Splashes`, `Smoke`, `Balloons`; record layout, handler dispatch, draw order | M4 | The headless original is the instrument: watch which memory a tick changes |
| 4 | Shape name resolution | answered | `re/notes/shapes.md`. `MasterList` and `AthList` are not object lists: they are the combined shape pointer tables that map records index, full size and eighth scale |
| 5 | Map record semantics and the world coordinate system | M4 | The map loader, found through the `maps/` filename table in DATA |
| 6 | Display geometry | answered | `re/notes/display.md` for the geometry, `re/notes/frontend.md` for what the front-end screens load, draw and wait for, observed VBlank by VBlank. Left over: the real duration of the fades, which are CPU-bound in the original, so M3 gives a fade step a fixed number of VBlanks as a provisional setting; and the sky flash, whose writers are named in `re/notes/frontend.md` but which no short mission script provoked (due before M5) |
| 7 | Drawing routines and read-back | answered | `re/notes/drawing.md`: no logic reads drawing results. Left over: the pixel pattern of the blitter's line mode, to be compared with an emulator when `line_draw` is ported |
| 8 | Randomness and seeding | answered | `re/notes/random.md` |
| 9 | 50 Hz versus 60 Hz | answered | `re/notes/random.md`: the program never checks |
| 10 | Sound-effect tables and the song format | M8 | `songplay` has symbols and is cheap to read at any time |
| 11 | The shape record header words at +8, +10, +12 | answered | `re/notes/shapes.md` and section 3.5 |
| 12 | High-score file layout, save-game layout | M7 for the save game | The high-score file is answered (`re/notes/highscore.md`, section 6.2). The save-game layout is open: `0x015EC2` holds the table of ranges a saved game covers, and `opt_invert_vertical` lies inside one of them |
| 13 | The game's floating point: what the three routines that use mathffp compute (`0x01BDFA`, `0x01D796`, `0x021A40`, 28 call sites, constants at `0x025B0C`), and a bit-exact integer implementation of the nine operations | M4 | `re/notes/headless.md`; the ROM's routines under the oracle are the reference |

Points 2, 3 and 5 are questions for the headless original, which turns them from reading into observing: its change report names, for every tick and every pass, the addresses written and the routines that wrote them, and `re/notes/headless.md` says how to ask each of the three. The glyphs for the dialogs that use the system default font come from the owner's Kickstart ROM (`re/notes/system-font.md`).
