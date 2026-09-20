# The key commands

What the keyboard does in each state of the game. Closes the open items of `re/notes/input.md`
and answers the rest of point 1 of `SPEC.md` section 10. Addresses use the standard load layout.

Every row of the table below is backed by a run of the headless original, named in the last
column; the runs live in `tests/runs/` and `tests/test_frontend.py` drives them. Each key run has
a negative control: the same script without the key, which does not show the effect.

## The chain from a key press to an effect

```text
IECLASS_RAWKEY event
   │  input_handler 0x02075A, on input.device at priority 127
   │    ignores key-up (bit 7 of the code), filters on key_qualifier_mask when that is not 0,
   │    appends the raw code to key_buffer and the qualifier word to key_qualifier_buffer,
   │    clears ie_Class so the event never reaches the rest of the system
   ▼
key_buffer 0x026C98, 10 codes   key_qualifier_buffer 0x026CA2, 10 words   key_count 0x026CB6
   │  key_available 0x0207D8 -> 0xFF when something is waiting
   │  key_get       0x0207E4 -> (qualifier << 16) | raw code, then shifts the buffer down
   ▼
one of the five readers below
```

`key_get` waits: while the buffer is empty it calls `graphics.WaitTOF`, so a reader that calls it
without asking `key_available` first blocks until a key arrives. Only `key_wait_char` (`0x0206EE`)
does that, and it has no caller. After popping, `key_get` clears the bits of `key_qualifier_mask`
from the qualifier it returns.

**Raw codes are positional**, so the port's key map has to be positional too
(`KeyboardEvent.code`, `re/notes/input.md`).

## Control, and the two masks

The game reads exactly one qualifier bit: **`IEQUALIFIER_CONTROL`, `0x0008`**, tested as
`and.w #8` on the qualifier word by `ingame_keys` (`0x01CD24`) and as `btst #3` by
`mission_briefing` (`0x018712`). The Control key's own raw code, `0x63`, is appended to the buffer
like any other key, but `key_to_char` gives it no character, so it matches no command and is
skipped. Delivering a command key with the Control qualifier and no separate `0x63` event works,
and so does delivering `0x63` first; both were run.

`key_qualifier_mask` (`0x026D30`) is set once, by `keyboard_open` (`0x0205CC`) from
`key_mask_default` (`0x027162`). `key_mask_default` is 0 unless `task_setup` (`0x0125C6`) finds a
trap handler that is not the one dos gives a process, in which case it becomes `0x10`, left Alt,
and from then on **every** key has to be pressed with left Alt (`re/notes/headless.md`). A game
started from the CLI under Kickstart 1.3 takes the first branch, so the mask is 0 in play and no
key needs a qualifier it does not ask for. `key_set_qualifier_mask` (`0x0205B4`) exists but has no
caller. **For the port both masks are dead**: the shell can hand the core raw codes with a
qualifier word of 0 except for the Control bit.

## Raw code to character: console.device

`key_to_char` (`0x020700`) builds an `InputEvent` on the stack (class `IECLASS_RAWKEY`, the code
in `ie_Code`, the qualifier in `ie_Qualifier`) and calls **`console.device` `RawKeyConvert`**
(LVO −48, through `os_console_raw_key_convert` `0x022F30`) with a buffer of **one** byte and
`keyMap` 0, which means the system's default keymap. It returns the character only when exactly
one came back; a key that yields two or three, such as a cursor or function key, returns 0. The
device is opened by `keyboard_open` (`0x0205F0`), which is why `re/notes/system-font.md` already
had to care about it.

The conversion therefore **depends on the system keymap**, which is not on the game disk. The
harness runs the ROM's own `RawKeyConvert` and the ROM's own default keymap, both found in
`original/kick.rom` by their contents (`headless._find_rom_console`), exactly as the mathffp
routines are run and as `system-font.md` finds topaz 8:

| What | Where in a 256 KB Kickstart 1.3 image | Found by |
|---|---|---|
| `console.device` resident | `0xFE4C6C` | the name in its `RT_NAME` |
| `RawKeyConvert` | `0xFE6D18` | the eighth entry of the function table the init code's first `lea d16(pc),a0` points at |
| default `KeyMap` record | `0xFE7F8A` | a long that points at the `LoKeyMap`, which is found by the QWERTY row |

Observed under the harness (`test_the_rom_converts_raw_codes_as_the_game_expects`):

| Raw code | Qualifier | Characters |
|---|---|---|
| `0x13` | none | `r` |
| `0x13` | left shift | `R` |
| `0x13` | Control | `0x12` |
| `0x45` | none | `0x1B` |
| `0x44` | none | `0x0D` |
| `0x41` | none | `0x08` |
| `0x46` | none | `0x7F` |
| `0x40` | none | a space |
| `0x4C` | none | two: no character for the game |
| `0x50` | none | three: no character for the game |

**For the port.** The port needs the same table, and M3 generates it: the build runs the ROM's
own `RawKeyConvert` with the ROM's own default keymap, both located by their contents, over
every raw code and every qualifier combination the shell can send, and embeds the single
characters as a plain `code x qualifier -> character` table beside the font extraction
(`SPEC.md` section 5 step 1, `re/notes/porting-m3.md`). Reimplementing the routine instead —
the type byte selects which of the four bytes of a key's longword applies, Control ands the
result with `0x9F`, `KCF_STRING` and `KCF_DEAD` entries point at descriptor tables — buys
nothing here, because the game never converts with a keymap of its own and never asks for more
than one character. The port's key map is positional either way, so a German keyboard gives the
same raw codes as an American one and the same characters come out.

## The five readers

| Reader | Where | Runs in | Asks | Does |
|---|---|---|---|---|
| `menu_input` `0x018194` | rank selection, load and save dialog | rank selection, the dialog's list | `key_available`, then `key_get` | `0x4C` → −1, `0x4D` → +1, `0x44` or `0x43` → 0; any other key falls through to the stick and the button. One `WaitTOF` per round; with its argument non-zero it gives up after 1800 rounds and returns 1000 |
| `wait_input_release` `0x018228` | between menu moves | rank selection, dialog | `key_available` only | returns at once when a key is waiting, otherwise waits up to 9 `WaitTOF` for fire and the stick to be centred |
| `text_input` `0x016086` | high-score name, save-game file names | name entry, dialog in save mode | `key_available`, `key_get`, `key_to_char` twice | the line editor, below |
| `mission_briefing` `0x018590` | the briefing | briefing | `key_available`, `key_get`, `key_to_char` | Control and `r` → return 1, which sends `main` back to the rank selection |
| `ingame_keys` `0x01CCF6` | once per pass, from the head of the inner loop | in flight, paused | `key_available`, `key_get`, `key_to_char` | all the commands of the manual's last page, and a cheat sequence |

`ingame_keys` converts the code **with the qualifier stripped** (`and.l #0xFFFF`), so `Control-R`
converts as a plain `r` and the Control bit is tested separately on the saved qualifier word. The
same holds in `mission_briefing`. Only `text_input` converts with the qualifier, which is how it
gets capitals.

## The commands

`M` names the page of `original/manual.txt` that lists the command. Every row was run; the run
description and the test are named in the last column.

### Story scroller (`story_screen` `0x017E80`)

| Key | Effect | M | Shown by |
|---|---|---|---|
| — | no key is read at all | | `test_the_story_scroller_reads_no_key` |
| fire | ends the scroller and goes on to the pictures | 2 | `test_fire_skips_the_front_end` |

### Publisher logo, title, credits (`title_sequence` `0x018022`)

| Key | Effect | M | Shown by |
|---|---|---|---|
| — | no key is read | | `test_the_story_scroller_reads_no_key` |
| fire | skips the rest of the sequence, one picture at a time | 2 | `test_fire_skips_the_front_end` |

### Rank selection (`rank_select` `0x018262`)

| Raw code | Qualifier | Effect | M | Shown by |
|---|---|---|---|---|
| `0x4C` | none | cursor up, wrapping 0 → 7 | 4 | `test_the_rank_menu_moves_with_the_cursor_keys` |
| `0x4D` | none | cursor down, wrapping 7 → 0 | 4 | `test_the_rank_menu_moves_with_the_cursor_keys` |
| `0x44`, `0x43` | none | choose the entry under the cursor | 4 | `test_return_chooses_the_rank` |
| any other | | ignored; the stick and the button are polled instead | | |
| — | | after 1800 rounds `menu_input` returns 1000 and the game asks for demo playback | | `test_headless.py::test_left_alone_the_program_starts_a_mission_by_itself` |

Eight entries: seven ranks (`rank_names` `0x025910`) and, at index 7, the load dialog.

### Briefing (`mission_briefing` `0x018590`)

| Raw code | Qualifier | Effect | M | Shown by |
|---|---|---|---|---|
| `0x13` | Control | fade out and return 1: `main` goes back to the top of the outer loop, so the rank selection comes again | 12 | `test_control_r_in_the_briefing_restarts` |
| any other | | ignored | | |
| fire, or 240 rounds | | go on to the mission | | `test_the_briefing_waits_240_vblanks` |

### In flight and paused (`ingame_keys` `0x01CCF6`)

Read once per pass, from the head of the inner loop, which the pause loop comes back to, so
every command below works **in flight and while paused alike**
(`test_the_commands_work_while_the_game_is_paused`, which runs the clear and the flip with the
game paused and finds the pause still on afterwards, and
`test_a_restart_from_the_pause_starts_the_next_mission_unpaused`). The handler drains the whole
buffer each time.

| Raw code | Qualifier | Effect | M | Shown by |
|---|---|---|---|---|
| `0x45` | any | toggles `pause_flag` (`0x025556`); when it becomes set, the sound-effect slots are cleared | 12 | `test_escape_pauses_and_unpauses` |
| `0x13` | Control | restart: clears `0x0257B6`, `ticker_clear`, `fade_out_pair`, sets `0x0255C0` and `quit_flag`, which ends the mission and the outer loop starts again at the rank selection | 12 | `test_control_r_in_flight_restarts` |
| `0x21` | Control | toggles `opt_music_off` (`0x0254F7`); when it becomes set, `sub_011F4E` clears the sound slots. `music_start` then skips its second player call and `music_stop` skips the fade wait | — | `test_control_s_toggles_the_music_flag` |
| `0x23` | Control | toggles `opt_invert_vertical` (`0x0254F6`), the vertical flip | 12 | `test_control_f_flips_the_vertical_control` |
| `0x24` | Control | save game, **only while `player_on_deck` (`0x025084`) is 1**, that is on the carrier: opens the dialog in save mode, then `screen_game_restore` and `input_queue_clear` | 11, 12 | `test_the_save_dialog_only_opens_on_the_carrier` |
| `0x28` | Control | load game, only while `demo_mode` is 0: opens the dialog in load mode; on success reloads the assets, shows the briefing and runs one tick; on cancel restores the play screen | 11, 12 | `test_the_dialog_lists_the_saved_games_of_the_disk` |
| `0x33` | Control | `dos.DeleteFile("highscore")`, with no further check | 12 | `test_control_c_deletes_the_high_score_file` |
| `0x35` | Control | executes an `illegal` instruction, which is the way into the game's own crash reporter. Not to be ported | — | not run |
| `0x34` | Control | formats two words from `0x027DE2` and `0x027DE4` into a ticker message | — | not run |
| `0x33`,`0x18`,`0x28`,`0x17`,`0x36` in order, no qualifier | | drives `cheat_state` (`0x025F18`) 0→5; at 5 a set of debug keys is live (below) | — | `test_the_cheat_sequence_unlocks_the_debug_keys` |

The manual's Control-D, which shows the high scores, **is not in the code**: no reader tests `d`
with Control, and `high_score_screen` is reached only from the end of the outer loop. Run in each
of the four states where a key is read at all — in flight, while paused, in the rank selection and
in the briefing — Control-D leaves the final state, the files log and the schedule exactly as a run
without it (`test_control_d_does_nothing_anywhere`). The step hashes in between do differ, because
the key sits in the buffer for a step; that is why the comparison is of the final state.
Control-C, which the manual says works only after Control-D, deletes the file unconditionally.
Those two are the places where the manual and this executable disagree.

With `cheat_state` at 5 (no qualifier): `i` and `k` add and subtract 50 at `0x025F16`; `f` sets
`0x025086` to `0x80`; `p` increments `0x02535C`; `q` sets `0x026F80` and `quit_flag`, which leaves
the program; `m` toggles `0x02536D`; `r` calls `0x013756`; `c` cycles `0x0253A4` through 0, 1, 2;
`8`, `2`, `6`, `4` add and subtract `0x1000` and `0x100` at `0x025350`; `d` sets `0x02508A` to
`0x80`, clears `player_on_deck` and toggles `0x026F72`; the space bar writes four `AvailMem`
figures into a ticker message; raw `0x59` (F10) clears `0x0257B6`; raw `0x5F` (Help) writes a
message chosen by `0x026E5C`. What these mean belongs to M4 and later; they are listed so that a
port does not lose them.

### End of a mission, game over, high-score display

No key is read. `high_score_screen` (`0x019856`) waits 1800 rounds of `wait_frames_or_fire`, which
ends early on **fire** only.

### High-score name entry and the dialog's file names (`text_input` `0x016086`)

Arguments: buffer, maximum length, x, y, and a fifth word both callers pass and **nothing
reads**, like the second argument of `fade_to`. The high-score entry calls it with 16 and
(82, 102); the save dialog with 28 and the slot's own position. The y it is given is the top
of the text: the routine adds the RastPort's `TxBaseline` (+`0x3E`) before it moves the pen.

| Raw code | Qualifier | Effect |
|---|---|---|
| `0x44`, `0x43` | any | accept and leave |
| `0x4F` | any | cursor left; **with either Shift** it jumps to the start of the line |
| `0x4E` | any | cursor right; **with either Shift** it jumps to the end |
| `0x4C` | any | leave with −1 (the dialog moves to the slot above) |
| `0x4D` | any | leave with +1 |
| `0x41` | any | delete the character before the cursor |
| `0x46` | any | delete the character under the cursor |
| `0x32` | right Amiga | clear the whole line. The code is converted **without** the qualifier and compared with `x`, so it is right-Amiga-X, the system's own clear-line |
| any other | any | `key_to_char` **with the qualifier**; a non-zero character is inserted at the cursor if the line is shorter than the maximum |

Fire also accepts and leaves; the stick forward and back leave with −1 and +1. There is **no
character filter**: whatever `RawKeyConvert` returns as a single byte goes in, control characters
included. The caret is one 8 x 8 `COMPLEMENT` `RectFill` (`text_caret` `0x016032`); the text is
drawn with `graphics.Text` in the system font (`re/notes/system-font.md`).

The save dialog runs the name through `path_sanitise` (`0x016592`), which replaces `:` and `/`
with a space, and prefixes `wof.` before opening the file.

## The vertical flip, and how long it lasts

The owner flies with the flip on, so M3 has to know exactly when the original turns it off.
`opt_invert_vertical` is the **byte** at `0x0254F6`; the byte after it, `0x0254F7`, is the music
flag, which is why a word read of the address shows `0xFF00`.

| | |
|---|---|
| Written by | `ingame_keys` at `0x01CD6E`, `not.b`, and nothing else |
| Read by | `read_joy_bits` at `0x015238`, `tst.b`, and nothing else |
| At program start | 0: it lies in the initialised part of the DATA hunk and the executable has a 0 there |
| A restart, Control-R | **unchanged**. The outer loop clears `opt_music_off` beside it but not the flip |
| A loaded game | **set to whatever the saved game holds**: loading a game that was saved with the flip off turns the flip off |
| A new mission, a lost aircraft, game over | unchanged |

Both the restart and the load were run
(`test_a_restart_keeps_the_flip_and_a_loaded_game_undoes_it`); the two `grep` results are held by
`test_the_flip_is_read_by_the_joystick_decoder_and_by_nothing_else`. The original therefore never
remembers the flip past the end of the program, and a loaded game can take it away under the
player. **For the port** that is worth diverging from: the flip is a preference, not game state,
so it belongs in the shell's stored settings and survives both a reload and a load, with the
core's word set from the setting after every load. The owner decided for it; what M3 built is in
`re/notes/porting-m3.md`.

## The right mouse button

`rmb_down` (`0x027F6E`) is written by `input_handler` from raw codes `0x69` and `0xE9` and is
**read nowhere**: `grep` over the listing finds the two writes and no read. The port can drop it.
Observed indirectly only, in that no run of the front end or of a mission ever reads the address;
the change report never names a reader.

## What the port has to keep

- The buffer is 10 deep and drops what does not fit; `key_get` removes the mask bits.
- A pass reads **all** waiting keys, so two commands in one pass both take effect.
- `ingame_keys` runs before the pause test in the inner loop, which is why Escape can unpause.
- The tap and hold latches of the button are untouched by any of this (`re/notes/input.md`).

## The run description's keys

A raw segment's third element is the list of keys delivered at the segment's first VBlank. An
entry is a raw code on its own, which means qualifier 0, or `[code, qualifier]`, where the
qualifier is a number or names of `IEQUALIFIER` bits joined with `+`. A run description is JSON,
which has **no hexadecimal**, so the codes are written in decimal; the names are there so that a
qualifier at least reads as itself:

```json
"raw": [[40, ""], [1, "", [[35, "ctrl"], 68]], [600, ""]]
```

That is the F key with Control, then Return. `headless.QUALIFIERS` lists the names. The old form
stays valid and is still used by `test_headless.py`.
