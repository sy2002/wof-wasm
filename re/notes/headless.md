# The headless original

The instrument of milestone M2 (`SPEC.md` section 8): the original executable's own 68000 code, from `main` on, running under Unicorn with the operating system, the hardware and time replaced by stubs. It produces state dumps after every logic tick and every pass, a log of every entropy read, and on request a report of who wrote which address. Addresses use the standard load layout.

```text
tools/headless.py        the machine, the schedule, the run description, the command line
tools/headless_os.py     the operating system: one Python method per library call
tools/headless_dump.py   the dump format, its reader, names for addresses, state comparison
tests/test_headless.py   the tests, part of the suite
```

## What runs and what does not

`main` (`0x010006`) is entered the way the C startup enters it: A4 set, `SysBase` and `DOSBase` filled in, a 16-bit `argc` of 1 and an `argv` on the stack. From there everything is the original's code: initialisation, the title sequence, the rank selection, the mission setup, the inner loop, the VBlank servers, the input handler. **No game logic is re-implemented.** The C startup itself (`0x021F2E`) is not run; with `argc` 1 the program never looks at `argv`.

Not run, and replaced by something that records or answers:

| What | Where | Replaced by |
|---|---|---|
| The operating system | library calls | `tools/headless_os.py`, table below |
| The crack's text screen | `crack_text_screen` `0x01F41A` | returns 1 at once. It draws entropy the port never draws |
| The music player and the song data | `music_start` `0x0123DC`, through `LoadSeg` | two fake segments; every call into them is recorded with its registers, VBlank, pass and tick, and answered with 0, which the game reads as "idle" |
| The blitter, the copper, Paula | custom-chip space | plain memory. Busy waits fall through, because bit 6 of `DMACONR` reads as 0 |
| The audio interrupt | level 4, vector at `0x70` | never raised. `sound_init` writes the vector into low memory, where nothing reads it |

The three habits of the game's code that the stubs have to know about:

- `free_mission_assets` (`0x011234`) begins with `AllocMem(0xFFFFFFFF, 0)`, the customary way to make exec flush its memory. The stub refuses any request larger than the heap and returns 0.
- `read_fire_button` (`0x02046A`) reads port 1's button at **`0xBFE0FF`**, not `0xBFE001`. CIA-A decodes only address lines A8 to A11 for the register number, so PRA answers at every odd address from `0xBFE001` to `0xBFE0FF`. The harness writes PRA to all of them. With plain memory there, the button reads as pressed for ever and the title sequence is skipped.
- `task_setup` (`0x0125C6`) looks at the first long of the task's trap handler (`tc_TrapCode`). If it is `0x48E7FFFE`, which is `movem.l d0-d7/a0-a6,-(a7)`, the game installs its own crash reporter `trap_handler` (`0x012640`). Otherwise it sets `key_mask_default` (`0x027162`) to `0x10`, and from then on `input_handler` accepts a key only together with left Alt; it also sets two words that nothing reads (`0x027450`, `0x026F60`). In Kickstart 1.3 the handler dos gives a process (`0xFF47EA`) begins with exactly that instruction and exec's default (`0xFC2FF0`) does not, so a game started from the CLI takes the first branch. The harness therefore hands `FindTask` a Task record whose trap handler begins with that long. The other branch looks like a provision for running under a debugger.

## Game logic uses floating point

**`logic_tick` computes with `mathffp.library`**, Motorola's fast floating point: 32 bits, a 24-bit mantissa, a sign bit and a 7-bit excess-64 exponent. The C library's glue at `0x021C9C`–`0x021D2E` opens the library on first use (`ffp_dispatch` `0x021CF6`, base in `MathBase` `0x027FAE`) and offers `ffp_add`, `ffp_cmp`, `ffp_neg`, `ffp_tst`, `ffp_fix`, `ffp_sub`, `ffp_div`, `ffp_flt`, `ffp_mul`. Three routines use it, at 28 call sites (12, 3 and 13), and the first two are in the call tree of `logic_tick`, through `0x01C660` and `0x01E7D6`:

| Routine | Called from | Uses |
|---|---|---|
| `0x01BDFA` | `0x01C70E` | add, neg, fix, div, flt, mul |
| `0x01D796` | `0x01E898`, in the call tree of `logic_tick` | fix, flt, mul, with constants from the table at `0x025B0C` |
| `0x021A40` | `0x0218A4` | all nine |

The harness does not model this arithmetic. The routines are pure register code, so the real ones run: `original/kick.rom` is mapped where it lives (`0xFC0000` for a 256 KB image), the resident `mathffp.library` is found by its name, its function table is read, and a jump table of `jmp` instructions at `0x0CE000` leads into the ROM. Without the ROM the library does not open and the run stops with a message. Kickstart 1.3 carries `mathffp 34.1`.

The port has these nine operations bit-exact, in integer code (`src/ffp.c`, `SPEC.md` section 7.1), tested against the ROM's routines under the oracle; what the three routines compute is in `re/notes/ffp.md`. The third, `format_float` `0x021A40`, is the C library's floating point conversion and is never entered. It is the only caller of `SPCmp` and `SPTst`, which in the ROM call `exec.GetCC`; the harness has no stub for that call on purpose, so a run that ever reached the formatter would stop with the library, the function and the call chain instead of going on unnoticed.

## The keyboard needs the ROM too

`key_to_char` (`0x020700`) turns a raw key code into a character with **console.device
`RawKeyConvert`** and the system's default keymap, which is not on the game disk. That routine is
pure — it reads the event, the keymap and nothing of the device — so the real one runs from the
ROM as well. Both it and the keymap are found in the ROM by their contents
(`headless._find_rom_console`): the resident module by its name, its function table through the
`lea d16(pc),a0` its init code begins with, `RawKeyConvert` as LVO −48, and the keymap by a
pointer to the `LoKeyMap`, which is recognised by the QWERTY row. In a 256 KB Kickstart 1.3 image
they sit at `0xFE6D18` and `0xFE7F8A`. Without the ROM a run stops at the first key the game
converts. `re/notes/keys.md` has the table and what it means for the port.

## Scheduling

The main program blocks and the VBlank interrupt is asynchronous; an emulator that delivered interrupts after some count of instructions would make every result depend on the emulator. The rule here is:

**The program runs until it waits. VBlanks happen only where it waits.**

| Wait point | VBlanks delivered |
|---|---|
| the spin in `wait_vblank` (`0x01AA44`) and in `wait_next_vblank` (`0x01AA36`), reached with `vblank_flag` clear | one, which sets the flag |
| `graphics.WaitTOF` | one |
| `dos.Delay(n)` | n x `video_hz` / 50 |
| entry of `frame_update` (`0x010228`), the start of a pass | as many as are still owed so that `vblanks_per_pass` lie between this pass's start and the previous one's; at least one if the flag is clear |

A VBlank is: set `JOY1DAT` and CIA-A PRA from the script, deliver the script's keys, then call every server the game installed with `AddIntServer(5, ...)`, highest priority first, as a nested call on a stack of its own with A1 = `is_Data`, A5 = `is_Code`, A0 = `0xDFF000`, A6 = `SysBase`. These are `soundfx_vblank` (`0x01EC64`, priority 30) and `vblank_server` (`0x011754`, priority −10). All other registers are the parked program's, as in a real interrupt. The servers may call the operating system (`input_queue_pop` uses `Disable` and `Enable`).

Consequences:

- Fades and other CPU-bound delays take no time. Their duration is not defined in the original either (`re/notes/display.md`).
- During play a pass is `V V P` with the provisional two VBlanks per pass, a tick follows every second pass, and the run records the schedule as it happened: `V raw`, `P n`, `T byte`, `S mission`. The port's tests can replay exactly that sequence through `wof_vblank` and `wof_pass`.
- Waits inside a pass count. `player_lost_restart` loops on `WaitTOF`; the VBlanks it uses are not owed again at the next pass.
- In demo playback and recording `run_queued_ticks` (`0x0114D8`) spins on `wait_next_vblank` until the server has taken two bytes, so there a pass has exactly two ticks whatever the setting.

### The front end runs for real

The title sequence, the rank selection and the briefing are not stubbed. They wait through `WaitTOF`, `wait_vblank` and `Delay`, poll the button and the key buffer, and the scripted controller carries them along. A run without any input also works: the title sequence runs out, `rank_select` (`0x018262`) gives up after 1800 VBlanks in `menu_input` (`0x018194`) and asks for demo playback, `wofdemo` is not on the disk, `demo_mode` falls back to 0 and a mission begins, after 6925 VBlanks. The load and save dialog runs too, with the directory `Lock` and `ExNext` below. What the whole front end does, screen by screen and VBlank by VBlank, is in `re/notes/frontend.md`.

## Input

**Raw mode** is the normal one. Per VBlank the script gives the five bits `wof_vblank` takes (forward, back, right, left, fire), written with the letters `U`, `D`, `R`, `L` and `F`: `U` is the stick pushed forward, bit 0, and `D` the stick pulled back, bit 1. The harness turns them into hardware state: `JOY1DAT` through a table it builds at start by calling the original's own decoder `read_joy_bits` (`0x01520E`) on all 16 combinations of bits 9, 8, 1 and 0, and bit 7 of CIA-A PRA, active low, for the button of port 2. Opposing directions cancel, as a real stick cannot produce them. The input byte, the tap and hold latches and the queue are then the work of `vblank_every_frame`, `read_joystick` and `vblank_server`.

**Bit 0 is the stick pushed forward.** The hardware reports the forward switch as bit 9 exclusive-or bit 8 of `JOY1DAT` and the back switch as bit 1 exclusive-or bit 0. With `JOY1DAT` = `0x0100`, forward alone, `read_joy_bits` returns 1, which is bit 0; with `0x0001`, back alone, it returns 2. The menus treat forward as up: for the forward switch `read_joy_dir8` (`0x020488`) returns 1, and `menu_input` answers 1 with −1, exactly as it answers the cursor-up key `0x4C`; the back switch gives 5 and +1, like cursor-down `0x4D`. In flight forward climbs: the take-off below needs it, and pulled back instead the aircraft goes over the bow. Pushing the stick away climbs, arcade fashion, and `opt_invert_vertical` turns that into pulling back. Two tests pin these facts.

**Keys** are raw Amiga key codes attached to a script segment. Each goes as an `IECLASS_RAWKEY` event through the handler the game put on input.device (`input_handler` `0x02075A`), before the servers of that VBlank. A key may carry a qualifier: an entry of the list is a bare code, which means qualifier 0, or `[code, qualifier]`, where the qualifier is a number or names of `IEQUALIFIER` bits joined with `+` (`headless.QUALIFIERS`). What the game does with each key is in `re/notes/keys.md`.

**Byte mode** replaces the byte the server has just sampled: a hook at `0x0117D8`, behind the call of `read_joystick`, overwrites `input_byte` (`0x027366`) with the next value of the list `bytes`, from the first sample after the first mission has begun, and only while `demo_mode` is 0. Queue, divider and drop rule stay the original's. After the list: 0.

What the tests establish about the byte: stick right is `0x04`, the forward switch `0x01`, a press of three VBlanks gives `0x20` in exactly one tick, a press held gives `0x10` from the first sample ten VBlanks after the press. **A press that ends the briefing reaches the mission**: its release is sampled after `input_queue_clear`, so the first tick of the mission can carry the tap bit. The port's front end has to hand its latches on in the same way.

## Entropy

Every read of `0xDFF006` takes the next value of the stream; the hook writes it into the register's memory before the read completes. The stream is the generator of `src/rand.c` (the test compares 2000 values for five seeds with the native library) or an explicit list, which ends the run when it is used up. The log names, for each read, the value, the **caller** of `rand_beam` or `read_vhposr`, and the VBlank, pass and tick.

Observed: `0x01CAC8`, reached from the player reset `0x013684`, reads once when the outer loop resets the game before the rank selection (`0x013562`) and twice in the mission setup. On the deck nothing reads. In the air `0x014D50`, in the call tree of `draw_world`, reads twice in every pass: 4191 reads in 1260 ticks. A different seed changes the state from the first dump on.

## Memory map

| Range | Use |
|---|---|
| `0x000000`–`0x1FFFFF` | RAM of `tools/oracle.py`; the executable at `0x010000`, `0x023000`, `0x028000`; address 4 holds `SysBase` |
| `0x0C0000`–`0x0C9FFF` | library bases, `0x2000` each, in this order: exec, dos, graphics, intuition, and one for both devices. Every jump-table slot is an `rts`; a code hook over the range parks the program |
| `0x0CE000` | `mathffp.library`: its slots jump into the ROM, outside the hooked range |
| `0x0D0000`–`0x0D0FFF` | fake segments for `LoadSeg`, `0x100` each |
| `0x0D8000` | records the stubs hand out: the Task, its trap handler's first long, an InputEvent |
| up to `0x0F0000` | the main program's stack |
| up to `0x0FF000` | stacks of nested calls, `0x2000` per level |
| `0x0FFF00`, `0x0FFF10` | where `main` and nested calls return to |
| `0x200000`–`0x9FFFFF` | `AllocMem`: a bump allocator, memory is never reused, so every address is reproducible and fresh memory is zero. `FreeMem` takes the block out of the dumps |
| `0xA00000`–`0xAFFFFF` | what `display_alloc_chip` (`0x0165CC`) asks for: planes, copper lists, `MaskBuffer`. Not dumped; CPU reads are logged |
| `0xBFD000`–`0xBFEFFF` | the CIAs, plain memory except PRA of CIA-A |
| `0xDFF000`–`0xDFFFFF` | custom chips, plain memory except `VHPOSR` and `JOY1DAT` |
| `0xFC0000`–`0xFFFFFF` | the Kickstart ROM, if present |

The whole run is in supervisor mode, so no instruction can trap for privilege.

## The stubs

A call for which `headless_os.py` has no method ends the run with the library, the function and the call chain. Arguments are in the registers the fd files name.

| Call | Does | Returns |
|---|---|---|
| `exec.OpenLibrary`, `OldOpenLibrary` | | the fake base; the ROM-backed base for `mathffp.library`; 0 for an unknown name |
| `exec.AllocMem` | bump allocation, from display memory if `display_alloc_chip` is the caller | the address; 0 for a request larger than the heap |
| `exec.FreeMem` | removes the block from the dumps | |
| `exec.AvailMem` | | `0x400000`, above the 400,000 bytes `0x01CCB6` compares it with |
| `exec.AddIntServer`, `RemIntServer` | keeps the server list; only interrupt 5 is accepted | |
| `exec.FindTask` | | the Task record described above |
| `exec.SetTaskPri`, `SetSignal` | | 0 |
| `exec.AllocSignal` | | 16, 17, ... |
| `exec.OpenDevice` | sets `io_Device` and clears `io_Error` | 0 |
| `exec.DoIO` | `IND_ADDHANDLER` and `IND_REMHANDLER` keep the handler list; any other command ends the run | 0 |
| `exec.RawDoFmt` | `%d %u %x %c %s` with `l`, width, `0`, `-` and `.limit`; 16-bit arguments without `l`; every character through the caller's `PutChProc` as 68000 code | |
| `exec.Forbid`, `Permit`, `Disable`, `Enable`, `CloseLibrary`, `CloseDevice`, `AddPort`, `RemPort`, `FreeSignal` | nothing | |
| `exec.Alert`, `Debug` | end the run: the program is in its crash reporter | |
| `intuition.CloseWorkBench`, `OpenWorkBench` | | 1 |
| `graphics.InitBitMap` | fills in BytesPerRow, Rows, Flags, Depth | |
| `graphics.InitRastPort` | clears the record; Mask, FgPen, AOlPen `0xFF`, JAM2, line pattern `0xFFFF` | |
| `graphics.Move`, `Draw` | set the pen position | |
| `graphics.SetAPen`, `SetBPen`, `SetDrMd` | set the field of the RastPort | |
| `graphics.Text` | advances the pen by 8 per character | |
| `graphics.WaitTOF` | one VBlank | |
| `graphics.OwnBlitter`, `DisownBlitter`, `BltClear`, `BltTemplate`, `RectFill` | nothing | |
| `graphics.BltBitMap` | nothing | 0 |
| `dos.Lock`, `Open` | files from `original/disk/Wings_of_Fury`, case ignored; `MODE_NEWFILE` creates a file in the overlay. `Lock` also takes a directory, and a name of 0 is the game's own directory, which is what the load and save dialog asks for | a handle, or 0 with `IoErr` 205 |
| `dos.Examine` | a FileInfoBlock with the type, the name and the size. `fib_FileName` is a plain string, which is what the dialog reads | −1 |
| `dos.ExNext` | the next entry of a directory lock, in the order the file system hands them out | −1, or 0 with `IoErr` 232 at the end |
| `dos.Read`, `Write`, `Seek`, `Close`, `UnLock`, `IoErr`, `DeleteFile` | as dos does; nothing is ever written to `original/`, and a deleted file is remembered so that it stays gone for the rest of the run | |
| `device.RawKeyConvert` | the ROM's own, see above | the number of characters |
| `dos.Delay` | VBlanks, see above | |
| `dos.LoadSeg`, `UnLoadSeg` | a fake segment, see above | a BPTR; −1 |

Stops inside the original, all of them observers except the first:

| Address | What happens there |
|---|---|
| `0x01F41A` | `crack_text_screen` is left at once with D0 = 1 |
| `0x01010A` | once per mission, just before the inner loop: step `S` |
| `0x010228` | a pass begins: the owed VBlanks, the pass count |
| `0x010192` | `frame_update` and `flip_buffers` have returned: step `P` |
| `0x011386`, and `0x0100F6`, `0x0114F4`, `0x01CE02` | `logic_tick` is entered, and has returned to one of its three callers: step `T` |
| `0x01AA36`, `0x01AA44` | the spins |
| `0x0117D8` | byte mode |
| `0x0165CC` | marks the next allocation as display memory |
| `0x01010E` | counts the executions of the inner loop's head |

## Formats

### Run description

JSON; every key is optional.

```text
{
  "entropy":          {"seed": 1}  or  {"values": [15381, 24129, ...]}  or  {"constant": 10304}
                      the generator of src/rand.c, an explicit list which ends the run when
                      it is used up, or one value for ever, which is what a comparison of two
                      runs that consume entropy at different rates needs
  "video_hz":         50           only Delay depends on it
  "vblanks_per_pass": 2
  "raw":              [[30, ""], [3, "F"], [460, "R"], [100, "RU"], [1, "", [68]]]
                      segments of [VBlanks, letters of U D L R F, optional raw key codes
                      delivered at the segment's first VBlank]; neutral after the last
  "bytes":            [4, 4, 5]    byte mode, see Input
  "files":            {"wofdemo": "<hex>"}   files laid over the disk
  "stop":             {"ticks": 100}  or  {"passes": n}  or  {"vblanks": n}
}
```

The counters of `stop` are totals since the program's start; `vblanks` is checked between wait points and may overshoot by the length of one wait.

### Dump

Described at the top of `tools/headless_dump.py`. A sequence of records, each a JSON head and a binary payload. After the header every record is one step: `S` when a mission's inner loop is reached, `T` after a logic tick, `P` after a pass, with the totals of missions, ticks, passes, VBlanks and entropy reads, the word `tick_input`, a SHA-256 of the state and the state itself as byte ranges that changed since the previous step. The state is the executable's DATA and BSS range `0x023000`–`0x028004` and every live allocation outside display memory; a reader rebuilds it and can check it against the hash. The tick that `main` runs itself at a mission's start comes before that mission's `S`.

A flight of 1260 ticks is 3778 steps and 1.8 MB.

### Directories

`ExNext` walks a directory in the file system's own order, not the alphabet: chain 0 upward and
inside a chain from its head. The harness reads that order out of `original/wof.adf`
(`headless_os.adf_order`) and puts what a run has saved at the head of its own chain, where a real
file system would put it. The name hash that decides the chain is in `re/notes/frontend.md`, and a
test checks it against every entry of five directory blocks of the image. Entries the image has but
the extracted directory has not are left out, so that what a run lists is what it can also open.

### Observers

`Headless(run, observe=[...])` takes routine names or addresses and records every entry of them:
the routine, the VBlank, pass and tick, all sixteen registers, and the longs and words above the
return address, which are a C routine's arguments. An observer only reads, so a run with observers
gives the same step hashes and the same schedule as one without, which
`tests/test_frontend.py::test_an_observer_does_not_change_a_run` holds it to. This is how
`re/notes/frontend.md` knows what the front-end screens draw and where.

With `observe_returns=True` a record also gets, under `return`, the registers and the
condition codes at the routine's `rts`. `watch={name: (address, length)}` adds the bytes of
those ranges at the entry and at the return, under `memory`; a range written as
`('*', pointer, length)` is followed through the long at `pointer`, and `watch_for` limits
the capture to the named routines. A twin of the test above holds a run with both to the
same steps. This is how `re/notes/ffp.md` knows what the two floating point routines of the
tick take and leave (`tools/ffp_observe.py`).

### Write summary, read hook

Two instruments answer the questions the change report is too large for.  Both only read,
which `tests/test_headless.py::test_an_instrument_does_not_change_a_run` holds them to.

**The phase.** Every write and every read is tagged with where the program was:

| Phase | Where |
|---|---|
| `V` | inside a VBlank: the key handlers and the interrupt servers |
| `T` | inside `logic_tick`'s tree, the one the key handler runs included |
| `F` | inside `frame_update`'s tree, that is, a pass proper |
| `M` | the main program outside all three: initialisation, the front end, the mission setup |

A VBlank delivered inside a pass, which happens at the pass's own start and in the restart
loop, is `V` and not `F`, so `F` is exactly what the pass itself does.

**`summary=True`** (`--summary FILE`) accumulates, per address, every write with its phase
and its routine, and every change with the kind of step it showed up in.
`headless_writes.Summary.ranges()` joins neighbouring addresses that were written and
changed in the same way and gives one entry per range; `format_summary` prints them.  This
is the whole run in a few hundred lines instead of tens of megabytes, and `keep_report=False`
switches the text of the change report off while keeping the comparison it rests on.

**Tables.** `headless_writes.strides` takes the ranges one routine wrote inside one region
and reports the record size they fall into: the smallest candidate under which every range
lies inside one record, the records form a nearly unbroken run, and the record is not filled
so densely that it is really a plain array.  `tables()` does that for every routine and
region of a run and is how a pool's record size and count are read off a run rather than
guessed.

**`read_owners` and `read_ranges`** (`--reads OWNER` or `--reads ADDR:LEN`) put a read hook
over chosen memory in the way `_plane_read` covers display memory: per read the routine, the
phase and the offset, counted in `machine.reads`, and with `read_detail=True` also the step.
An allocation is named by its owner, the routine `alloc` attributes it to, so a run can watch
"the map" or "the pools" without knowing an address; a range given by address gets a hook of
its own and costs nothing outside it.

```text
.venv/bin/python tools/headless.py run RUN.json --summary A.sum --reads sub_012d5a
.venv/bin/python tools/headless.py run RUN.json --reads 0253c8:2 --reads-out A.reads
```

### Change report, entropy log, schedule

`--changes FILE` hooks every write to the dumped memory and lists per step the ranges whose content changed, with the old and new bytes, a name and the routines that wrote them. A window runs from the previous step to this one, so a `P` step includes the VBlank servers that ran at its start. `--entropy-log FILE` and `--schedule FILE` write the two logs described above.

Names: an address with an entry in `re/names.txt` gets it; any other gets the listing's automatic `g_` name and, in brackets, the nearest name below it. That neighbour is for orientation only, because names carry no sizes. Addresses in allocations are given as offset into `alloc N (owner file)`, where the owner is the first routine on the stack that is not an allocator wrapper.

## Using it

```text
.venv/bin/python tools/headless.py run RUN.json --out A.dump --changes A.txt --entropy-log A.ent
.venv/bin/python tools/headless.py show A.dump              one line per step
.venv/bin/python tools/headless.py show A.dump --step 120   the ranges that step changed, with names
.venv/bin/python tools/headless.py diff A.dump B.dump       the first step that differs, with names
.venv/bin/python tools/headless.py diff A.dump B.dump --step 357
```

From Python: `headless.Headless(description, track_writes=False)`, then `run(until=...)` with `'inner'`, `'pass'`, `'tick'`, `'step'` or nothing for the description's stop; `o` is the oracle for reading memory, `regions()` the state, `schedule`, `entropy_log`, `step_hashes`, `player_calls`, `files_log`, `plane_reads`, `os_calls` the records.

The scripts the tests use: five presses of fire, three VBlanks each and thirty apart, carry the front end along and the mission begins at VBlank 132. On the deck a press of fire brings the aircraft up on the lift, stick right rolls it along the deck, and stick right and forward (`RU`) after 460 VBlanks of rolling lifts it off; without the push forward, or pulled back instead, the aircraft rolls over the bow and the player is reset.

For the open points of `SPEC.md` section 10:

- **Point 2**, per-tick against per-pass state: run with `--changes` and compare the `T` windows with the `P` windows. Every field a pass writes appears with its writer; the object-table fields written through pointers, which static reading could not enumerate, appear as offsets into the pool allocations of `alloc_pools`.
- **Point 3**, the object system: the pools are the allocations owned by `alloc_pools`. Their record size and the active records show in the change report as regular strides; `diff` between a run that fires and one that does not isolates one pool.
- **Point 5**, map semantics: the map is the allocation owned by the map loader `0x012D5A`. What the tick reads of it can be seen by adding a read hook over that allocation in the way `_plane_read` does for display memory.

Stick right against stick left on the deck, 85 ticks after the scripts part, differs in: `view_x`; the aircraft's x at `0x02507A` and its drawing copy at `0x026E5C`; a direction word, 1 against −1, at `0x02508C` and `0x026F7A`; and the pixel data and facing markers of `hellcat.shp` and `Torpedo.shp`, which is `shape_mirror_x` at work (`re/notes/shapes.md`).

## Read-back

`re/notes/drawing.md` left one gap: a CPU read of a bitplane through a pointer that static reading did not connect to one. Display memory has a region of its own here and every CPU read from it is counted by routine and block. Over the front end without input, a take-off, 1260 ticks of flight and a crash off the deck, **no bitplane and no ticker plane was read at all**. Every read was one of these:

| Block | Readers |
|---|---|
| the three copper lists and `cop_blank` | `cop_move`, `cop_move_ptr`, `cop_wait`, `cop_install`, `cop_colours`, `cop_set_split_line`, `view_build_copper`, `view_poke_colours1`, `view_poke_colours2`: the copper builder reading its own list |
| `MaskBuffer` | `text_render`, which ORs glyphs into the template it builds |

`vblank_server`'s ticker scroll reads the ticker plane while a message runs; none ran in these scripts. The test `test_no_logic_reads_what_was_drawn` fails if any other routine ever reads display memory.

## Unicorn, as it behaves here

- A register written inside a hook is lost: the translated block carries on with its own copy. Memory written inside a hook is kept. Every stub therefore parks the program with `emu_stop`, works, and resumes; stopped inside a code hook, the program counter is the hooked instruction and that instruction has not run.
- A hook added after a block was translated does not fire for it. All hooks are installed before the first instruction runs.
- The program counter read inside a memory hook is exact, which is what the entropy log, the change report and the read-back log rely on.
- The condition codes cannot be read out of the emulator. Unicorn keeps them lazily, and `reg_read(UC_M68K_REG_SR)` hands back whatever was last materialised, both after `emu_start` stops and inside a code hook: `addq.w #1` on `0x7FFF` reports N without V, and `tst.w` on `0x00010000` reports nothing at all. `Oracle.call(ccr=True)` and the return observers read them by running a move from SR inside the emulation, which costs no register and no flag. Anything that wants flags out of a run has to go the same way.
- The watchdog is wall-clock time and only ever ends a run with an error; it does not influence one.

## Speed

On the development machine: the front end with fire presses 0.4 s, without any input 4 s; 1000 ticks of flight (2000 passes, 4000 VBlanks) 6.4 s, 7.3 s with the dump, about twice that with the change report.

## Not covered

- **Sound.** The audio interrupt never comes, so the effects engine never sees a channel end, and the player is not run. No dumped state outside the sound engine's own variables was seen to depend on it, but that was not examined. The event log of `SPEC.md` section 8, row Sound, needs a channel-end model and belongs to M8.
- **The case of a saved file's name.** The overlay keys its files in lower case, so a game saved
  under a name typed with capitals is listed by the dialog in lower case, where the real file
  system keeps the case the file was created with. Nothing the harness is used for depends on it,
  but a test that types capitals would see the difference. `re/notes/frontend.md` says what the
  port must do.
- **`Text` metrics** beyond the pen advance of 8 per character. `graphics.Text` draws nothing here, so what a dialog's text looks like is not observable; its pen positions are.
- **Demo playback and recording.** A `wofdemo` file can be supplied through `files`; recording needs `argc` above 1, which the run description does not offer yet.
- **Long campaigns.** The bump allocator has 8 MB and never reuses memory; start-up and the first mission take about 370 KB of it.
- What `0x01CAC8` and `0x014D50` do with their random values belongs to the notes of the subsystems that own them.
