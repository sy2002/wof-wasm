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
re/Wings.lst            annotated disassembly of the main executable (generated)
re/functions.csv        routine inventory with a status column (generated, status is preserved by hand)
re/names.txt            hand-maintained names for code and data addresses
re/libbases.txt         hand-maintained map of library base variables
re/notes/               one Markdown note per understood subsystem
ref/sheets/             contact sheets of decoded shapes (visual reference)
tools/                  Python tooling (section 4)
src/                    C core                         (to be written)
web/                    shell template: HTML, JS, CSS  (to be written)
tests/                  oracle and replay tests        (to be written)
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

The executable on this disk carries a crack: the protection check is disabled and an extra text screen was added. Game logic is otherwise the retail code.

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
- Layout: `0x010000`–`0x015D62` is almost entirely hand-written assembly (main loop, drawing, interrupt servers, object movement). From `0x015D62` on: 223 C routines, then the C runtime and OS glue at the end.

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

This design is what makes a verifiable port possible: the whole simulation is a function of (initial state, seed, input byte stream).

**The input byte** is assembled by `read_joystick` (`0x01CA32`) and is the only channel by which controls reach game logic. Its low byte is: bit 0 stick down, bit 1 stick up, bit 2 stick right, bit 3 stick left, bit 4 fire held for 10 or more VBlanks, bit 5 fire tapped and released inside 10 VBlanks. Bits 6 and 7 are unused. Opposing directions cancel to centre. The tap and hold timing runs at VBlank rate, not tick rate, and latches between samples. The keyboard is a separate path: an input.device handler at priority 127 buffers raw Amiga key codes for the menus and does not feed the tick. Details and consequences for the port: `re/notes/input.md`.

Still to establish: which state changes happen per tick and which per pass; where randomness comes from (two reads of the beam position register `VHPOSR` exist and are candidates for seeding).

### 3.4 Operating system and hardware use

The game builds its own display with graphics.library and otherwise does its own work.

| Used by the original | Port equivalent |
|---|---|
| dos: `Open`, `Read`, `Seek`, `Close`, `Lock`, `Examine`, `UnLock`, `IoErr`, `DeleteFile` | read-only virtual file system built from the disk files; writes go to browser storage |
| dos: `LoadSeg`, `UnLoadSeg` (twice: the `songplay` player, and `wofsongs`) | the player is ported into the core; song data is read from the embedded file |
| dos: `Delay` | coroutine yield for the given time (section 6.3) |
| exec: `AllocMem`, `AvailMem` | static arena allocator; out-of-memory paths are unreachable |
| exec: `AddIntServer`, `RemIntServer` (VBlank) | the shell's clock: 4 VBlanks make one tick |
| exec: `FindTask`, `SetTaskPri`, `Forbid`, `Permit`, `Supervisor`, `Alert`, `Debug` | dropped |
| exec: `RawDoFmt` | small `sprintf` subset written to match the format strings actually used |
| exec: `DoIO` | to establish (input.device or console.device) |
| graphics: `InitBitMap`, `InitRastPort`, `InitVPort`, `MakeVPort`, `MrgCop`, `GetColorMap`, `FreeColorMap`, `FreeVPortCopLists` | replaced by the port's framebuffers and palette tables |
| graphics: `BltBitMap` (2 sites), `BltTemplate` (1), `Text` (1) | software equivalents on the indexed framebuffer |
| intuition: `CloseWorkBench`, `OpenWorkBench` | dropped |
| custom chips: `JOY1DAT`, `VHPOSR`, `COP1LC`, `INTENA`, `INTREQ`, audio registers; level-4 autovector at `0x70` | input layer, seed, palette tables, Paula model (section 6.5) |

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

The loader `load_file` (`0x01FF16`) handles the wrapper transparently, so any file may or may not be wrapped. It also knows a second magic, `Pckd`, which it rejects; no file on the disk uses it. Two files decode to one byte more than the declared size; the declared size wins.

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
+8   u16 x 3   purpose to establish
+14  u8 x 6    destination plane masks, zero-terminated list
+20  plane data: for each mask in the list, height x width bytes, plane after plane
```

A mask is the set of destination bitplanes that one stored plane is written to. `01 02 04 08 10` is an ordinary 5-plane shape. `01 02 04 18` stores 4 planes and writes the last one to planes 3 and 4. The pixel value is the OR of the masks of all stored planes whose bit is set. Colour 0 is transparent. The game refers to shapes **by their 4-character names**; name lists are in the executable's DATA hunk.

**Palettes.** `wingspalette`, `night.p`, `nightocean.p`: a bare IFF `CMAP` chunk: 4 bytes `CMAP`, 4 bytes to ignore, then 32 RGB triplets. Only the high nibble of each component is significant. `palette` and `ocean.palette` are `Rpck`-wrapped ILBM files used for their `CMAP`; `ocean.p` is an unwrapped one and also carries `CRNG` colour-cycling chunks.

**Pictures.** Standard IFF ILBM with ByteRun1 compression. The original has its own reader in C (it reports errors under the name `ReadIFF`), which is to be ported rather than replaced.

**Maps.** Two u32 values (the first equals the file length), then a sequence of u16 records. Low bits select a tile or object type, high bits are flags (`0x8000` occurs frequently). Record semantics are to be established from the map loader.

**Sounds.** Headerless signed 8-bit PCM. Playback periods are in the executable.

**Font.** `newarmyfont` starts with a u16 height (12), first and last character codes (`0x20`, `0x7E`), then a table of per-character widths, then glyph data. Details to establish from the text drawing routine.

**`songplay` and `wofsongs`.** `songplay` exports, by symbol: `_PlaySong`, `_StopSong`, `_FadeSong`, `_PauseMusic`, `_RestartMusic`, `_GetSongStat`, `_PlaySfx`, `_StopSfx`, `_SfxStat`, `_AdjustSfx`, `_ReadInstruments`, `_OpenTimerInt`, `SongIntHandler`, `CheckChannelInt`. The song format is to be established from this player; it is 2.7 KB of code with names, which makes it the easiest part of the project to read.

## 4. Tools

Run everything with `.venv/bin/python` from the repository root.

| Tool | Purpose |
|---|---|
| `tools/disasm.py` | regenerates `re/Wings.lst` and `re/functions.csv` from the executable, `re/names.txt` and `re/libbases.txt` (about 2 seconds) |
| `tools/skel.py ADDR` | control-flow skeleton of one routine: labels, calls, branches, tests. Add `--all` for the full text |
| `tools/oracle.py` | runs original routines in a 68000 emulator; running it directly executes its self-test |
| `tools/hunk.py` | hunk loader used by all of the above |
| `tools/m68kdis.py EXE START LEN` | raw linear disassembly of an address range |
| `tools/rpck.py`, `tools/ppkc.py` | reference decoders; `ppkc.py SHP PALETTE OUT.png` renders a contact sheet |
| `tools/fd/` | AmigaOS library offset tables used to name OS calls |

**Listing conventions.** Routine headers give the kind (`C` or `asm`), the stack frame size, the far-call slot, and the callers. Operands that use A4 are followed by the absolute address or its name. Relocated longs are shown as names or as the string they point to. OS calls are named. Blocks marked *found by gap sweep* are code that nothing references by control flow (uncalled library routines or routines reached only through computed addresses).

**Naming workflow.** When a routine or global is understood, add it to `re/names.txt` and regenerate. The listing, the skeletons and the inventory pick the name up everywhere. Never edit `re/Wings.lst` by hand.

**The oracle.** `Oracle.call(addr, *args, regs=...)` executes an original routine on a real 68000 model with the executable mapped at the listing addresses. Build stack arguments with `Oracle.W()` for `int` and `Oracle.L()` for `long` and pointers. Pass `a4=0x02AFFE` when the routine touches globals. Its self-test runs `rpck_unpack` on all ten packed files and compares the output with `tools/rpck.py`.

## 5. Build

`tools/build.py` (to be written) produces `dist/wof.html` in these steps:

1. **Extract tables.** `tools/extract_tables.py` reads `re/tables.toml`, a manifest of (name, address, element type, count) entries, and writes `src/gen/tables.c` and `src/gen/tables.h` from the bytes of `original/disk/Wings_of_Fury/Wings`. Every constant table, name list, text and tuning array the port needs from the DATA or CODE hunk is obtained this way. Byte order is converted during extraction. `src/gen/` is ignored by version control.
2. **Pack the file system.** All game files from section 3.1 except the executable and the non-game files are concatenated into one blob with a directory (name, offset, length). Files stay in their original formats; the core contains the ported loaders.
3. **Compile the core** to `core.wasm` with the command in section 2, plus `-Wl,--export-dynamic` or explicit export attributes.
4. **Assemble the page.** `web/index.html` is the template. The build inlines the CSS, the JavaScript, the base64 of `core.wasm` and the base64 of the file-system blob. The page instantiates the module with `WebAssembly.instantiate(bytes, imports)`; streaming instantiation is not available from `file://`.

Expected output size is below 2 MB.

A second target builds the same C sources natively with Apple clang as a shared library for the tests (`tests/libwofcore.dylib`).

## 6. Architecture

### 6.1 Core

C11, freestanding: no libc, no allocation after initialisation (one static arena replaces `AllocMem`), no floating point in game logic, no dependence on wall-clock time, no undefined behaviour relied upon. The same sources must compile for `wasm32-freestanding` and natively.

Source files mirror the original's modules in address order so that a reader can move between listing and source. Every ported routine carries its origin:

```c
/* orig 0x01C660 - per-tick state machine of <whatever it turns out to be> */
```

Exported interface (names are normative, signatures may grow):

```c
void            wof_init(uint32_t seed, const uint8_t *fs, uint32_t fs_len);
void            wof_set_video_hz(int hz);          /* 60 (default) or 50 */
void            wof_vblank(uint8_t raw);           /* call once per emulated VBlank, see 6.2 */
void            wof_pass(void);                    /* one pass of the main program, see 6.3 */
const uint8_t  *wof_framebuffer(void);             /* indexed pixels, see 6.4 */
const uint16_t *wof_palette_rows(void);            /* palette index per output row, see 6.4 */
const uint32_t *wof_palettes(void);
const void     *wof_display_list(uint32_t *count);
void            wof_audio_render(int16_t *stereo, uint32_t frames, uint32_t rate);
uint32_t        wof_state_size(void);              /* save states, replays, tests */
void            wof_state_save(uint8_t *dst);
void            wof_state_load(const uint8_t *src);
```

`wof_vblank` is the port of `vblank_server` together with `vblank_every_frame`. It takes the **raw controller state** of that VBlank, not a finished input byte: bit 0 down, bit 1 up, bit 2 right, bit 3 left, bit 4 fire button currently down. The core runs the fire-button press timer, cancels opposing directions, applies the reversed-vertical option, assembles the input byte, counts to 4 and queues it, including the 6-entry limit and demo playback and recording. Keeping the tap and hold discrimination inside the core is required for fidelity, because it is evaluated at 60 Hz while sampling happens at 15 Hz (`re/notes/input.md`).

### 6.2 Shell

Plain JavaScript modules, no framework, no bundler other than the build script.

- **Clock.** A fixed-rate accumulator driven by `requestAnimationFrame` issues `wof_vblank` calls at 60 Hz (or 50) of emulated time, then `wof_pass` calls. After a stall, at most 24 VBlanks are replayed, which matches the original's queue limit of 6 ticks.
- **Video.** Canvas 2D or WebGL. The indexed framebuffer is converted through the per-row palettes to RGBA. Integer scaling, optional 4:3 aspect correction for the 320 x 200 picture, fullscreen.
- **Input.** Keyboard and Gamepad API are merged into the raw state word passed to `wof_vblank`. A button that goes down and up again between two VBlanks is held sticky until the next `wof_vblank`, so short taps survive; the original samples a level, so this only compensates for the browser's coarser event timing. Menu and text-entry keys take the second path: the shell maps `KeyboardEvent.code`, which is positional, to raw Amiga key codes, which are also positional, and feeds the core's key buffer. The key map is configurable and stored locally.
- **Audio.** The shell pulls PCM from `wof_audio_render` in blocks that correspond to emulated time and plays them through an `AudioWorklet` loaded from a Blob URL, fed by `postMessage`. Scheduled `AudioBufferSourceNode` blocks are the fallback. Audio starts on the first user gesture.
- **Storage.** `highscore` and saved games are written through the virtual file system to `localStorage`, base64-encoded, under a `wof:` prefix.
- **Pause** when the page is hidden.

### 6.3 Blocking code becomes coroutines

The original's front end blocks: it waits for VBlanks, for `Delay`, for the fire button, for fades. A browser page cannot block, and from `file://` there is no `SharedArrayBuffer` to block in a worker. Therefore:

- The main program (`main` and everything that can wait) is ported as a **stackless coroutine** in the protothreads style: a `switch`-based resume point, with locals that live across a wait moved into a context struct. The original's linear control flow is kept; each original wait becomes `CO_WAIT_UNTIL(condition)` or `CO_YIELD()`.
- `wof_pass()` resumes the coroutine once. During play this is exactly one pass of the inner loop.
- Routines that never wait are ported as ordinary functions.

### 6.4 Video model

The original display is planar. The port uses **8-bit indexed framebuffers** and applies the palette at presentation, so that fades, the day and night palettes, colour cycling and any palette change part-way down the screen behave as in the original.

- Shapes are converted from plane data and plane masks to indexed pixels once, at load, exactly as in `tools/ppkc.py`.
- All drawing primitives of the original (shape blit with transparency, masked and clipped variants, scrolling, text, screen copies) are reimplemented on indexed pixels with identical clipping and identical draw order.
- The original composes its picture from more than one ViewPort: the 320-pixel low-resolution playfield with 32 colours, and a 640-pixel high-resolution dashboard with its own palette (`iff-dash`, `nightdash` are 640 x 37). The viewport constructor is the C routine around `0x01F7BE`; geometry and colour-table handling are to be established from its callers. The shell output is 640 pixels wide with playfield pixels doubled.
- `wof_palette_rows` tells the shell which palette applies to each output row.
- **Display list.** Every shape draw also appends (shape name, x, y, layer or order, flags, owner object id) to a per-pass list. The classic renderer ignores it. It exists so that an enhanced renderer can be added later.

If any game logic reads pixels or mask buffers back (the executable names a `MaskBuffer`), those buffers must be kept bit-exact and the logic must read them, not a substitute.

### 6.5 Audio model

A minimal Paula: four channels, each with sample pointer, length, period, volume, repeat pointer and length, and the DMA-style restart behaviour. The output rate conversion uses the NTSC clock constant 3,579,545 Hz divided by the period (3,546,895 Hz when running at 50 Hz). Left and right follow the Amiga channel layout (0 and 3 left, 1 and 2 right) with an optional stereo-width reduction in the shell.

The sound-effect engine (`sound_init`, `audio_irq`, `soundfx_vblank`) and the `songplay` player are ported against this model. Their interrupt entry points become functions called by the core's own timing: per VBlank, per channel-end event, per player timer tick.

### 6.6 What is not ported

The C runtime startup, OS glue stubs, memory management, View and copper construction, interrupt plumbing, Workbench handling, the debug and crash reporters, the protection check and the crack screen. Mark these `replace` or `drop` in `re/functions.csv`. Everything else is `port`.

## 7. Porting rules

### 7.1 Arithmetic

Port from the **disassembly**, not from a guess at the C source.

- Use `int16_t`, `uint16_t`, `int32_t`, `uint32_t`, `int8_t`, `uint8_t` explicitly. Never plain `int` for game values.
- Reproduce every width change the listing shows. `ext.l` is a sign extension of a 16-bit value. `muls.w` multiplies two 16-bit values into 32 bits; what happens next (`move.w` or `move.l`) decides whether the product is truncated. `divs.w` divides 32 by 16 bits, truncates toward zero and yields a 16-bit quotient; `swap` afterwards means the remainder is used.
- Signedness follows the branch: `blt`, `bge`, `bgt`, `ble` are signed; `bcs`, `bcc`, `bhi`, `bls` are unsigned.
- Wrap-around is behaviour. Do not widen a variable because it might overflow. Make the wrap explicit with a cast, because signed overflow is undefined in C.
- Shifts: `asr` is arithmetic; write it so that it is arithmetic on every compiler.
- A division by zero or a quotient overflow traps on a 68000. Assert in test builds.

### 7.2 Data

- File data is big-endian. Read it with explicit byte accessors. Never cast file bytes to a struct.
- Game structures get C structs with the original field order and widths. Record the original offsets in a comment or a static assertion table, because the tests map fields by offset.
- Pointers inside game structures become either real pointers or indices. Decide per structure and note it in the subsystem note. Save states and test comparisons must not depend on host pointer values.
- Every global that is ported gets an entry in a registry (`src/globals.def`, an X-macro: name, C type, original address). The test harness uses it to copy state between oracle and port with byte-order conversion.

### 7.3 Determinism

- All randomness goes through the ported generator. Its seed is an argument of `wof_init`. If the original seeds from hardware state, that value becomes the seed parameter.
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
| Whole game, logic | **Headless original.** A harness runs the original executable's initialisation and logic under the oracle with the OS calls of section 3.4 stubbed (files served from `original/disk`, memory from a bump allocator, display calls satisfied with dummy structures, custom-chip addresses mapped as plain memory). It then feeds input bytes straight into the input queue and calls the tick and pass routines, dumping the object tables after every tick. The port runs the same input stream; the dumps must be identical. Start with initialisation up to the first pass, then extend |
| Whole game, replays | The port records (seed, input bytes) in the original's demo format. Replays are regression tests: final state hash and per-tick hashes are stored in `tests/replays/` |
| Picture | Framebuffer hashes per pass for the stored replays, once the classic renderer is declared correct for a scene by visual comparison with the contact sheets and with the original running in an Amiga emulator |
| Sound | Log of (tick, channel, sample id, period, volume) events compared between port and headless original |

If the blitter turns out to be driven only from a few assembly routines, the headless harness can intercept those routines and perform the blits on the emulated bitplanes, which also yields reference frames. This is optional.

## 9. Milestones

Each milestone ends with a working `dist/wof.html` and green tests.

| # | Deliverable | Accepted when |
|---|---|---|
| M0 | Build pipeline, empty core, shell with canvas, clock, input and audio plumbing | `dist/wof.html` opens from `file://`, shows a test pattern from the core at a steady emulated 60 Hz, plays a test tone after a key press, makes no network request |
| M1 | Virtual file system, arena, `load_file` with `Rpck`, shape tables by name, ILBM reader, palettes, font and text drawing, table extraction | the page shows the publisher logo, title and credit pictures with correct colours and draws text in the game font; decoders pass oracle tests |
| M2 | Headless original (section 8) reaching the first pass of the inner loop | per-tick object dumps are produced for a scripted input stream |
| M3 | Front end as coroutines: title sequence, rank selection, high-score display and entry, load and save dialogs | screens match the original in layout, timing and transitions; high scores persist across reloads |
| M4 | World and player: map loading and drawing, scrolling, carrier, take-off and landing, flight model, dashboard, day and night | a mission can be started, flown and ended by landing or crashing; logic matches the headless original for recorded inputs |
| M5 | Weapons and ground targets: guns, bombs, rockets, torpedoes, islands, bunkers, guns, soldiers, effects | as M4, on the first three maps |
| M6 | Enemy aircraft, ships, torpedo attack view, carrier defence | as M4, on all 15 maps |
| M7 | Missions, ranks, scoring, messages, save and load, demo record and playback, end sequence | a full campaign is playable; a recorded demo replays identically after a page reload |
| M8 | Sound effects engine and the music player | event logs match; music plays on the title and between missions as in the original |
| M9 | Shell polish: key configuration, gamepad, scaling and aspect options, 50 Hz option, pause, fullscreen | usable without reading documentation |

## 10. Points to establish

Each of these is answerable from the listing. Record the answer in `re/notes/` and update this document where it states a fact.

1. **Answered, see `re/notes/input.md`.** What remains: which raw key codes the game tests and in which states (follow the key-buffer readers at `0x0207DA` upward), and what `read_joy_dispatch` `0x01CB20` reaches through `sub_021DCE` when `g_026EB0` is set.
2. Per-tick versus per-pass state changes. Start at `run_queued_ticks` `0x0114D8` and its tick routine `0x011386`, and at `frame_update` `0x010228`.
3. The object system: the executable names `MasterList` and `AthList`, and effect pools `Ricochet`, `Splashes`, `Smoke`, `Balloons`. Record layout, handler dispatch, draw order.
4. Shape name resolution: how the name lists in DATA become shape pointers, and which container each list belongs to.
5. Map record semantics and the world coordinate system.
6. Display geometry: viewport heights and positions, the dashboard, palette changes down the screen, colour cycling.
7. The drawing routines in the assembly region: which use the blitter, which the CPU, and whether any logic reads pixels or masks back.
8. Random number generation and seeding.
9. Whether the program distinguishes 50 Hz from 60 Hz machines anywhere.
10. Sound-effect tables (sample, period, volume, channel, priority) and the song format.
11. The remaining three words of the shape record header.
12. Save-game and high-score file layouts.
