# The demo

The game's self-running demo (the manual, pages 2 and 3): how the original records one, how
the rank selection's attract mode plays one back, the file, the seed, and what the port
keeps beside it. Addresses use the standard load layout. Every statement is **observed**,
with the script or test that shows it, or **read** from the listing alone. The scripts are
those of `tools/m7_scripts.py` (`re/notes/porting-m7.md`, "Part 2: the scripts").

## The globals

| Address | Name | What it is |
|---|---|---|
| `0x026D4C` | `demo_mode` | 0 play, 1 playback, 2 recording |
| `0x026D4E` | `demo_buffer_ptr` | the demo's block: `rank_select`'s allocation of `0x1388` bytes for a recording, `load_file`'s for a playback |
| `0x026D52` | `demo_index` | the buffer's next entry |
| `0x026D44` | `demo_bytes_owed` | how many bytes `vblank_server` may still take or keep before `run_queued_ticks` goes on: 2 after every pass of a demo |
| `0x026D54` | `demo_step_s` | set (`st.b`) at a mission's step S (`0x01010A`), cleared at its end (`0x0101D8`); the server's demo halves do nothing while it is clear |
| `0x026F86` | `demo_file_name` | main's argument: the address of the name `wofdemo` (`0x023458`) when the program was started with one |
| `0x026F8C` | `demo_was_played` | set at a mission's end when it was a playback; the high scores are skipped |

## Recording

`main` looks at its argument count once (`0x01002C`): above one, `demo_file_name` points at
`wofdemo` and stays so for the whole run; the argument's text is never read (read). From
then on every rank chosen at the rank selection records (read, `0x018436`; observed,
`demo_record` with the harness's `argc` of 2):

1. `rank_select`, after its fade, allocates `0x1388` bytes (cleared, as every allocation is)
   for `demo_buffer_ptr` and sets `demo_mode` 2, unless a playback was asked for;
2. `rand_set_seed(read_vhposr())` seeds the generator from the beam (`0x018480`), the one
   place the program seeds it (`re/notes/random.md`);
3. the rank's low byte (`0x0253BF`) goes into entry 0 and `demo_index` is 1;
4. at step S `0x026D44` is 2 and `0x026D54` set; from then on `vblank_server` samples as in
   play and queues the byte, and while `0x026D44` is above 0 it also counts it down, stores
   the byte's low half at the next entry, and sets `quit_flag` when the index reaches
   `0x1386`; then `input_byte` takes what D0 holds there, which is `read_joy_bits`' result,
   or the entry the full queue dropped (read, `0x011800` to `0x01183E`);
5. `run_queued_ticks` first waits VBlank by VBlank until `0x026D44` is 0 (`0x0114E0`), runs
   the queue's ticks, and sets it to 2 again: every pass of a demo has two ticks and its
   pass waits for their two samples (observed: `demo_record`, 253 passes, 512 ticks with
   main's own);
6. the game's end (a game over, Control-R, the count) runs `demo_end` (`0x01852A`): a
   `0xFF` at the next entry, the whole buffer, `0x1388` bytes, written as `wofdemo`
   (`save_file` `0x01FE50`), the buffer freed and `demo_mode` cleared (observed:
   `demo_record`'s `wofdemo`, 5,000 bytes, the rank at 0, 507 input bytes, the `0xFF` at
   entry 507).

Samples the server takes while `0x026D44` is 0 are queued but not recorded: that is inside
the tick, while the restart after a lost aircraft waits for VBlanks (read).

## Playback and the attract mode

`menu_input` gives up after 1800 rounds without input and returns 1000 (`re/notes/frontend.md`);
`rank_select` sets `demo_mode` 1 and leaves its loop (`0x018320`). With the cursor on the
seventh entry that still opens the load dialog, and a cancel there goes back to the menu with
`demo_mode` left at 1 (read). Otherwise, after the fade:

1. `load_file("wofdemo")` into `demo_buffer_ptr`; without the file `demo_mode` falls back to
   0 and a mission starts (observed on this disk, which has no `wofdemo`: `night_again`);
2. the generator seeded from the beam, as for a recording;
3. `rank_played` from entry 0, sign-extended; `rank_chosen` stays the cursor's;
4. at step S the same two flags; the server takes a byte from the buffer only while
   `0x026D44` is above 0 and queues nothing otherwise, so a pass has the demo's two bytes
   and no others; a `0xFF` sets `quit_flag` and is queued as the byte, and so is the entry
   that brings the index to `0x1386`; `read_joystick` is not called, and the button's
   latches run on unread (read; observed: `demo_play_ff`, the `0xFF` poked at entry 100,
   ends with `demo_index` 100 after 101 ticks; `demo_play_long`, every entry after the
   recording neutral, ends at the count with `demo_index` `0x1387`: the pass's second sample
   takes one entry more after the first set `quit_flag`, so entry `0x1386` is read and
   nothing beyond it);
5. the inner loop polls the button after every pass (`0x0101AA`): fire ends the playback
   (observed: `demo_play`, fire 1,500 VBlanks in, at `demo_index` 485 of 507);
6. at the end `demo_was_played` is set and the high scores are skipped: the outer loop goes
   straight back to the rank selection (observed in all three playbacks).

A playback runs with the generator seeded from the beam at its own start, so on the machine
it replays its recording only as far as nothing random differs (read). Two more values the
tick reads run on from one mission to the next and are not in the file: the swell's phase
(`0x02476A`), which moves the carrier and the lift with it and which nothing resets
(`player_restart_state` resets only its countdown, `0x013716`), and `night_flag`. A playback
that starts in another phase than its recording parts from it; observed on the page with the
seed file carrying only the stream: the recording and the first playback after a reload
agreed at every sample, the second playback of the same session was two rows behind on the
lift from its 41st sample on.

**The entries go in pairs.** At step S the index is 1 and the count 2, and every pass takes
two entries, so a pass takes entries 1 and 2, 3 and 4, and so on; entry `0x1386` is always
the second of its pass. The end at the count therefore sets `quit_flag` at entry `0x1385`,
the first of the last pass, and the second sample of that pass still takes entry `0x1386`
and leaves the index at `0x1387`, in the recording as in the playback (observed:
`demo_record_long` and `demo_play_long`, 4,999 ticks each, `demo_index` `0x1387`). A byte
of the demo is never read past entry `0x1386`, well inside the `0x1388` bytes.

**Pausing a demo.** Escape, or the port's P or its help screen's H, pauses a demo as it
pauses a mission: while `pause_flag` is set `vblank_server` returns before the sample, so
no byte is taken or stored and the divider keeps its phase, and the inner loop runs no
pass; the pause's end lets the demo go on where it stood. A key is no fire, so it never
ends a playback (read; `src/portkeys.c`, `wof_request_continue`).

## The file

`wofdemo`, `0x1388` bytes: the rank, the input bytes, a `0xFF`, zeros to the end. It is the
recording's buffer as it stood, so its size never varies. `load_file` would unpack an
`Rpck` file too (`SPEC.md` section 3.5). A shorter file leaves the playback reading
whatever memory follows its block (read).

## The port

- `src/front.c` `rank_select`: the attract mode's request, the load of `wofdemo`, the seed,
  the rank; the recording's buffer; `run_queued_ticks`' wait; `src/input.c` the two halves
  of `vblank_server`; `src/mission.c` `demo_end` and the buffer's release in
  `free_mission_assets` and `0x011256`.
- The buffer is a registered pool, `demo_buffer` (`src/mission.def`, `0x1388` records of one
  byte, found through `0x026D4E`), so the comparisons hold every byte recorded or played;
  the port keeps whether the pointer is set (`demo_buffer_set`).
- A buffer freed between two missions of a demo (a mission won while a demo runs:
  `free_mission_assets` at `0x010150` frees it) leaves the original reading and writing from
  address 0 on; the port reads 0 there and drops the write. No script reaches it.
- **The seed** (port policy): a recording notes, before the beam is read, where the
  entropy stream stands, the swell's phase and `night_flag`, and its end writes, beside
  `wofdemo`, the file `wofdemo.seed`, 12 bytes big-endian: the stream's state (a long), an
  FNV-1a hash of the 5,000 demo bytes (a long), the swell's phase and `night_flag` (a word
  each). A playback whose `wofdemo` has that hash starts from all three, so it replays the
  recording exactly, after a page reload and after any number of games (`SPEC.md` section
  9, M7; observed on the page in Chrome and Firefox: the recording and two playbacks in one
  session agree at every input sample, `tests/pageload.mjs`). A `wofdemo` without it, one
  from a real Amiga, plays with everything as it stands, as on another machine; so does
  every differential test, whose files have none. Neither name begins with `wof.`, so the
  load and save dialog never lists them.
- **The development key** `4` with the diagnostics overlay up switches main's argument on
  and off (`wof_dev_demo_record`); the overlay's `demo` line says off, armed or recording,
  and its `game` line shows the rank, the mission, the lives and the score and whether a
  demo plays or records (`wof_dev_game`). Both files are stored like a saved game, through
  the written files the shell keeps under `wof:files` (`SPEC.md` section 6.2, Storage).
- **The replay** of `SPEC.md` section 8: `tests/replays/demo_a.json` is a demo the port
  recorded, its seed file and its playback's schedule, with the SHA-256 of the saved state
  after every input sample; `tests/test_replays.py` replays it in the native core and in
  Node's WebAssembly (`tests/replay_wasm.mjs`) and demands the stored hashes.
