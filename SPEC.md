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
original/kick.rom       the owner's Kickstart 1.3 ROM image, source of the system font (read-only)
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

**The input byte** is assembled by `read_joystick` (`0x01CA32`) and is the only channel by which controls reach game logic. Its low byte is: bit 0 stick down, bit 1 stick up, bit 2 stick right, bit 3 stick left, bit 4 fire held for 10 or more VBlanks, bit 5 fire tapped and released inside 10 VBlanks. Bits 6 and 7 are unused. Opposing directions cancel to centre. The tap and hold timing runs at VBlank rate, not tick rate, and latches between samples. The keyboard is a separate path: an input.device handler at priority 127 buffers raw Amiga key codes for the menus and does not feed the tick. Details and consequences for the port: `re/notes/input.md`.

**Passes are not pure rendering.** `frame_update` begins with `wait_vblank` (`0x01AA3E`), so there is at most one pass per VBlank, counted from the previous buffer flip, and it contains game logic that runs once per pass, not per tick: soldiers move and die, score is added, ticker messages are queued, and the restart after a lost aircraft and the game-over countdown advance. Nine routines in its call tree call `rand_beam`. The tick in turn reads state the pass leaves behind (the flag at `0x026E3C`, a frame was drawn since the last tick, and the pass counter at `0x0253C8`). The interleaving of VBlanks, passes and ticks is therefore an input of the simulation, like the input bytes and the entropy stream. How many VBlanks a pass takes on a real A500 is not established; it sets the speed of everything that runs per pass (`re/notes/drawing.md`).

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
| `tools/hunk.py` | hunk loader used by all of the above |
| `tools/m68kdis.py EXE START LEN` | raw linear disassembly of an address range |
| `tools/rpck.py`, `tools/ppkc.py` | reference decoders; `ppkc.py SHP PALETTE OUT.png` renders a contact sheet |
| `tools/fd/` | AmigaOS library offset tables used to name OS calls |

**Listing conventions.** Routine headers give the kind (`C` or `asm`), the stack frame size, the far-call slot, and the callers. Operands that use A4 are followed by the absolute address or its name. Relocated longs are shown as names or as the string they point to. OS calls are named. Blocks marked *found by gap sweep* are code that nothing references by control flow (uncalled library routines or routines reached only through computed addresses).

**Naming workflow.** When a routine or global is understood, add it to `re/names.txt` and regenerate. The listing, the skeletons and the inventory pick the name up everywhere. Never edit `re/Wings.lst` by hand.

**The oracle.** `Oracle.call(addr, *args, regs=...)` executes an original routine on a real 68000 model with the executable mapped at the listing addresses. Build stack arguments with `Oracle.W()` for `int` and `Oracle.L()` for `long` and pointers. Pass `a4=0x02AFFE` when the routine touches globals. Its self-test runs `rpck_unpack` on all ten packed files and compares the output with `tools/rpck.py`.

## 5. Build

`tools/build.py` produces `dist/wof.html` in these steps (`--native` also builds the test library):

1. **Extract tables.** `tools/extract_tables.py` reads `re/tables.toml`, a manifest of (name, address, element type, count) entries, and writes `src/gen/tables.c` and `src/gen/tables.h` from the bytes of `original/disk/Wings_of_Fury/Wings`. Every constant table, name list, text and tuning array the port needs from the DATA or CODE hunk is obtained this way. Byte order is converted during extraction. The same step reads the topaz 8 glyphs, location table and metrics from `original/kick.rom`, locating the font by its contents so that other Kickstart versions work, and falls back to the game's own font with a message when the ROM is absent. `src/gen/` is ignored by version control.
2. **Pack the file system.** All game files from section 3.1 except the executable and the non-game files are concatenated into one blob. Left out are `Wings`, `UFXintro`, `wingt`, every `.info` file and every dotfile, which leaves 55 files. Files stay in their original formats; the core contains the ported loaders. The container is big-endian like everything else the project reads: the magic `WOFS`, a u32 version, a u32 file count, a u32 directory offset, then 40-byte directory entries of a 32-byte NUL-padded name, a u32 offset and a u32 length. Names are paths relative to the disk's `Wings_of_Fury` directory, which is the original's current directory, so the ported loaders use the original's own file names. File-name lookup ignores case: the game asks for `shapes/Torpedo.shp` and `shapes/rank.iff`, the disk has `torpedo.shp` and `Rank.iff`.
3. **Compile the core** to `core.wasm` with the command in section 2, plus `-Wl,--export-dynamic` or explicit export attributes.
4. **Assemble the page.** `web/index.html` is the template. The build inlines the CSS, the JavaScript, the base64 of `core.wasm` and the base64 of the file-system blob. The files in `web/` are real ES modules, which a `file://` page cannot load from files; the build concatenates them in dependency order into one scope, strips whole-line imports and leading `export` keywords, and then fails if any module syntax is left or an imported name is not defined. The page instantiates the module with `WebAssembly.instantiate(bytes, imports)`; streaming instantiation is not available from `file://`.

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

`wof_vblank` is the port of `vblank_server` together with `vblank_every_frame`. It takes the **raw controller state** of that VBlank, not a finished input byte: bit 0 down, bit 1 up, bit 2 right, bit 3 left, bit 4 fire button currently down. The core runs the fire-button press timer, cancels opposing directions, applies the reversed-vertical option, assembles the input byte, counts to 4 and queues it, including the 6-entry limit and demo playback and recording. Keeping the tap and hold discrimination inside the core is required for fidelity, because it is evaluated at 60 Hz while sampling happens at 15 Hz (`re/notes/input.md`).

### 6.2 Shell

Plain JavaScript modules, no framework, no bundler other than the build script (section 5, step 4).

- **Clock.** A fixed-rate accumulator driven by `requestAnimationFrame` issues `wof_vblank` calls at 60 Hz (or 50) of emulated time, each followed by one `wof_pass`, independent of the monitor's refresh rate. The original allows at most one pass per VBlank and on real hardware a pass takes longer than that; since logic runs per pass (section 3.3), the number of VBlanks per pass is a core setting, provisionally 2, until point 2 of section 10 is measured. After a stall, at most 24 VBlanks are replayed, which matches the original's queue limit of 6 ticks.
- **Video.** Canvas 2D or WebGL. The indexed framebuffer is converted through the per-row palettes to RGBA. A 2D context must be requested with `willReadFrequently: true`, which selects a software-backed canvas: in GPU-composited Firefox the accelerated canvas can drop `putImageData` entirely, so that the canvas reads back as one colour and the player sees a black picture. Headless Firefox composites in software and does not show the fault. Integer scaling, optional 4:3 aspect correction for the 320 x 214 play picture, fullscreen.
- **Input.** Keyboard and Gamepad API are merged into the raw state word passed to `wof_vblank`. A button that goes down and up again between two VBlanks is held sticky until the next `wof_vblank`, so short taps survive; the original samples a level, so this only compensates for the browser's coarser event timing. Menu and text-entry keys take the second path: the shell maps `KeyboardEvent.code`, which is positional, to raw Amiga key codes, which are also positional, and feeds the core's key buffer. The key map is configurable and stored locally. No modifier key may ever be mapped: with Control as fire and W as up, firing while climbing is Ctrl+W, which closes the tab and which a page cannot prevent.
- **Audio.** The shell pulls PCM from `wof_audio_render` in blocks that correspond to emulated time and plays them through an `AudioWorklet`, fed by `postMessage`. The worklet module is inlined and loaded from a `data:` URL on a `file://` page, where a Blob URL is refused as a cross-origin load, and from a Blob URL elsewhere. Scheduled `AudioBufferSourceNode` blocks are the fallback; the query `?audio=buffers` forces it so that the tests can exercise it. Audio starts on the first event that really activates the page, which is not the same as the first event: a modifier pressed on its own, such as the Command of a console or screenshot shortcut, is a `keydown` that activates nothing, and a context built there is born suspended and logs an autoplay warning. The shell asks `navigator.userActivation.isActive` where it exists and otherwise ignores modifier keys, dead keys and keys pressed with a modifier held. It builds and resumes the context in the same task as the event, keeps listening and retrying until the context state is running, and only then removes the prompt that asks for a key.
- **Storage.** `highscore` and saved games are written through the virtual file system to `localStorage`, base64-encoded, under a `wof:` prefix.
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
- `wof_palette_rows` tells the shell which palette applies to each output row.
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

### 7.2 Data

- File data is big-endian. Read it with explicit byte accessors. Never cast file bytes to a struct.
- Game structures get C structs with the original field order and widths. Record the original offsets in a comment or a static assertion table, because the tests map fields by offset.
- Pointers inside game structures become either real pointers or indices. Decide per structure and note it in the subsystem note. Save states and test comparisons must not depend on host pointer values.
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
| Whole game, logic | **Headless original.** A harness runs the original executable's initialisation and logic under the oracle with the OS calls of section 3.4 stubbed (files served from `original/disk`, memory from a bump allocator, display calls satisfied with dummy structures, custom-chip addresses mapped as plain memory, except reads of the beam position register `0xDFF006`, which are hooked and served from the same entropy stream the port consumes). The blitter and `OwnBlitter`, `DisownBlitter`, `BltClear`, `BltBitMap`, `BltTemplate` and `WaitTOF` are no-ops, which is valid because no logic reads drawing results; `vblank_flag` (`0x0255BE`) is set before each pass because `wait_vblank` spins on it. The harness bypasses the crack's text screen (`0x01F41A`), which would otherwise draw entropy values the port never draws. It runs `frame_update` on every pass, never only the ticks, and the schedule of VBlanks, passes and ticks is part of the recorded input. It then feeds input bytes straight into the input queue and calls the tick and pass routines, dumping the object tables after every tick. The port runs the same input stream; the dumps must be identical. Start with initialisation up to the first pass, then extend |
| Whole game, replays | The port records (seed, input bytes) in the original's demo format. Replays are regression tests: final state hash and per-tick hashes are stored in `tests/replays/` |
| Page | The built `dist/wof.html` is opened from a `file://` URL in headless Chrome (DevTools protocol) and headless Firefox (WebDriver BiDi), both driven through Node's built-in WebSocket with nothing installed; each module skips when its browser is missing. Keys are pressed through the driver, never dispatched from a script, because a scripted event activates nothing. Checked: only local requests, a clean console, the picture on the canvas, a steady clock, Web Audio untouched before an activating key and running after it. `WOF_FIREFOX_VISIBLE=1` adds a run in a visible Firefox window, the only check that can see a GPU canvas fault |
| Picture | Framebuffer hashes per pass for the stored replays, once the classic renderer is declared correct for a scene by visual comparison with the contact sheets and with the original running in an Amiga emulator |
| Sound | Log of (tick, channel, sample id, period, volume) events compared between port and headless original |

If the blitter turns out to be driven only from a few assembly routines, the headless harness can intercept those routines and perform the blits on the emulated bitplanes, which also yields reference frames. This is optional.

## 9. Milestones

Each milestone ends with a working `dist/wof.html` and green tests. **M0 is complete**; the framebuffer it reports, 640 x 200, becomes 640 x 214 with M1 (section 6.4).

| # | Deliverable | Accepted when |
|---|---|---|
| M0 | Build pipeline, empty core, shell with canvas, clock, input and audio plumbing | `dist/wof.html` opens from `file://`, shows a test pattern from the core at a steady emulated 60 Hz, plays a test tone after a key press, makes no network request |
| M1 | Virtual file system, arena, `load_file` with `Rpck`, shape tables by name, ILBM reader, palettes, font and text drawing, table extraction | the page shows the publisher logo, title and credit pictures with correct colours and draws text in the game font; decoders pass oracle tests |
| M2 | Headless original (section 8) reaching the first pass of the inner loop | per-tick state dumps are produced for a scripted input stream and a fixed entropy stream; two runs give identical dumps |
| M3 | Front end as coroutines: title sequence, rank selection, high-score display and entry, load and save dialogs | screens match the original in layout, timing and transitions; high scores persist across reloads |
| M4 | World and player: map loading and drawing, scrolling, carrier, take-off and landing, flight model, dashboard, day and night | a mission can be started, flown and ended by landing or crashing; logic matches the headless original for recorded inputs |
| M5 | Weapons and ground targets: guns, bombs, rockets, torpedoes, islands, bunkers, guns, soldiers, effects | as M4, on the first three maps |
| M6 | Enemy aircraft, ships, torpedo attack view, carrier defence | as M4, on all 15 maps |
| M7 | Missions, ranks, scoring, messages, save and load, demo record and playback, end sequence | a full campaign is playable; a recorded demo replays identically after a page reload |
| M8 | Sound effects engine and the music player | event logs match; music plays on the title and between missions as in the original |
| M9 | Shell polish: key configuration, gamepad, scaling and aspect options, 50 Hz option, pause, fullscreen | usable without reading documentation |

## 10. Points to establish

Each point is answerable from the listing. Record the answer in `re/notes/` and update this document where it states a fact. A point is due **before the milestone that consumes its answer starts**; the numbering is not an order.

| # | Point | Due before | Where to start, or status |
|---|---|---|---|
| 1 | Input byte and keyboard path | answered | `re/notes/input.md`. Left over: the raw key codes the front end tests (due before M3, follow the key-buffer readers at `0x0207DA` upward) and the alternative controller path behind `read_joy_dispatch` `0x01CB20` (due before M9) |
| 2 | Per-tick versus per-pass state changes | M4 | Established so far (`re/notes/drawing.md`): the per-pass logic list and the two variables through which passes and ticks couple. Open: how many VBlanks a pass takes on a real or cycle-exact emulated A500, to be measured; and the object-table fields written during a pass, which the memory-compare run of the headless original closes |
| 3 | The object system: the pools `Ricochet`, `Splashes`, `Smoke`, `Balloons`; record layout, handler dispatch, draw order | M4 | The headless original is the instrument: watch which memory a tick changes |
| 4 | Shape name resolution | answered | `re/notes/shapes.md`. `MasterList` and `AthList` are not object lists: they are the combined shape pointer tables that map records index, full size and eighth scale |
| 5 | Map record semantics and the world coordinate system | M4 | The map loader, found through the `maps/` filename table in DATA |
| 6 | Display geometry | answered for the play screen | `re/notes/display.md`. Left over, due before M3: the front-end screens beyond their geometry, what triggers the sky flash, and the real duration of the fades, which are CPU-bound in the original |
| 7 | Drawing routines and read-back | answered | `re/notes/drawing.md`: no logic reads drawing results. Left over: the pixel pattern of the blitter's line mode, to be compared with an emulator when `line_draw` is ported |
| 8 | Randomness and seeding | answered | `re/notes/random.md` |
| 9 | 50 Hz versus 60 Hz | answered | `re/notes/random.md`: the program never checks |
| 10 | Sound-effect tables and the song format | M8 | `songplay` has symbols and is cheap to read at any time |
| 11 | The shape record header words at +8, +10, +12 | answered | `re/notes/shapes.md` and section 3.5 |
| 12 | High-score file layout, save-game layout | M3 and M7 | `0x019288`, `0x0193CC`, `0x018B96` |

Points 2, 3 and 5 are far easier once the headless original of M2 exists, because it turns them from reading into observing. The glyphs for the dialogs that use the system default font come from the owner's Kickstart ROM (`re/notes/system-font.md`).
