# M3: the front end as coroutines, and what the tests prove

Milestone M3 of `SPEC.md` section 9: the key path, the waits and fades as coroutines, the
screens of `re/notes/frontend.md`, the graphics.library primitives the dialogs use, the high
scores and the load and save dialog. Addresses use the standard load layout. Everything
stated here is either read from the disassembly or measured by a test, and where it is
measured the test is named.

`re/notes/frontend.md`, `re/notes/keys.md` and `re/notes/highscore.md` say what the original
does; this note says what the port does about it and where the two are not the same.

## The key path

### What the port keeps

| Original | Port | Status |
|---|---|---|
| `input_handler` `0x02075A`, the `IECLASS_RAWKEY` half | `wof_key`, `src/keys.c` | verified |
| `key_available` `0x0207D8` | `wof_key_available` | verified |
| `key_get` `0x0207E4` | `wof_key_get` | verified |
| `key_to_char` `0x020700` | `wof_key_to_char` over a generated table | verified |
| `keyboard_open` `0x0205CC` | `wof_keys_init`: the three words it sets | replace |
| `read_joy_bits` `0x01520E`, `read_joy_dir8` `0x020488` | `src/input.c` | ported |
| `vblank_every_frame` `0x01C9CA`, `read_joystick` `0x01CA32` | `src/input.c` | ported |
| `vblank_server` `0x011754`, input half | `wof_vblank`, `src/input.c` | ported |

Dropped, with the reason: the `IECLASS_RAWMOUSE` half of `input_handler`, which writes
`rmb_down` (`0x027F6E`) — a grep over the listing finds the two writes and no read, and no
run of the original ever read the address; the InputEvent chain and the `ie_Class` the
handler clears, because there is no input.device to swallow an event from; `key_get`'s
`WaitTOF` spin on an empty buffer, which only `key_wait_char` (`0x0206EE`) can reach and
which has no caller; and `keyboard_open`'s ports and devices.

`key_qualifier_mask` is kept although it is dead. `task_setup` (`0x0125C6`) sets it to
`0x10` only when the task's trap handler is not the one dos gives a process, which a game
started from the CLI never is, so it is 0 in play; it costs three lines and
`test_the_qualifier_mask_filters_and_is_taken_out_of_what_key_get_returns` runs the other
path against the original.

### The off-by-one that is state

`key_get`'s shift loop runs from index 0 up to and including the *new* `key_count`, so with
a full buffer its last round copies one entry past the end of each array. On the machine
those two reads land on the next globals: `key_buffer + 10` is the first byte of
`key_qualifier_buffer`, and `key_qualifier_buffer + 20` is `key_count` itself. The port
keeps the values rather than the adjacency, so the quirk survives a struct whose member
order is its own (`src/keys.c`, `key_code_at` and `key_qualifier_at`). Because the shift
runs upward, the byte that lands in the last code slot is the high byte of the *shifted*
first qualifier word, not of the one that was popped
(`test_popping_a_full_buffer_reproduces_the_original_off_by_one`).

### The key conversion table

`key_to_char` calls console.device's `RawKeyConvert` with the system's default keymap and
takes the key only when exactly one character comes back. `re/notes/keys.md` offered two
ways and recommended the second; the second is what the build does. `tools/extract_tables.py`
locates `RawKeyConvert` and the ROM's own default keymap in `original/kick.rom` by their
contents — the same two lookups the headless original uses, now module-level functions of
`tools/headless.py` — and runs the routine for every raw code from `0x00` to `0x7F` under
every qualifier combination of the four bits the shell and the port's key layer can produce:
the two Shift keys, Caps Lock and Control. The result is 2,048 bytes, 1,050 of which carry a
character.

Alt and Amiga are not in the table, because the shell ignores a key pressed with Alt or
Command and never sends those bits. `text_input` tests raw `0x32` with right Amiga for
"clear the line" **before** it converts, so that command needs no table entry either; the
shell has no key for it (below). If a later milestone needs Alt, the table grows a
dimension.

`test_the_generated_table_is_what_the_roms_own_routine_returns` runs the ROM's routine again
over all 2,048 combinations and compares every one; it skips when `original/kick.rom` is
absent. Without the ROM the build says so and writes what the positions of the raw codes
give: letters, digits and the space bar. Return, Escape, Backspace, Delete and the cursor
keys are tested by their raw code before `key_to_char` is reached, so the menus and the line
editor still work without the ROM; what is lost is typing anything but a letter or a digit.

### The port's own layer

`wof_port_key` (`src/portkeys.c`) is not a port of anything: it is the policy of `SPEC.md`
sections 6.1 and 6.2, decided with the owner, and it is kept in a file of its own for that
reason. Inside the line editor every key passes as it came. Outside it, seven keys are
rewritten into the code and qualifier the original's readers expect:

| Port key, by `KeyboardEvent.code` | Raw code in | Becomes | When |
|---|---|---|---|
| `KeyP` | `0x19` | `0x45`, Escape | always |
| `KeyF` | `0x23` | `0x23` with Control | always |
| `KeyG` | `0x24` | `0x24` with Control | always |
| `KeyL` | `0x28` | `0x28` with Control | always |
| `KeyM` | `0x37` | `0x21` with Control, the original's Control-S | always |
| `KeyR` | `0x13` | `0x13` with Control | while paused, and in the briefing |
| `KeyC` | `0x33` | `0x33` with Control | while paused |
| `Escape` | `0x45` | unchanged | always |

Where a restriction does not hold the key passes on **as it came**, which is exactly what
the original does with a plain letter, so the restriction narrows the original and adds
nothing to it. The qualifier the shell sent survives the rewrite; the readers strip it
before they convert and test only the Control bit.

**What the decision costs.** Five keys — P, F, G, L and M — carry a command in every state
outside the line editor, so a plain press of them never reaches a reader as a plain letter
(`test_the_letters_the_layer_always_takes_are_exactly_four`). Nothing the manual describes
is affected, because a plain letter does nothing in the original either. Two things that are
not in the manual are: the cheat sequence `c o l i n` (`re/notes/keys.md`) cannot be typed,
because its `l` is the load command; and of the debug keys the cheat unlocks, `f` and `m`
would be taken as well. Both belong to `ingame_keys`, which M4 ports.

### The vertical flip

In the original `opt_invert_vertical` (`0x0254F6`) is game state: it starts at 0, only the
flip command writes it, and a loaded game overwrites it. The port treats it as a preference
(`SPEC.md` section 6.1, a deliberate divergence confirmed by the owner): the shell stores it
under `wof:invertVertical`, hands it over with `wof_set_invert_vertical` before the first
VBlank, and reads `wof_invert_vertical` back on every animation frame so that a flip made in
the game is remembered. A core that was never given a preference behaves exactly as the
original, which is what the differential tests run.

Two hooks are in `src/portkeys.c` for the milestones that will need them:
`wof_invert_vertical_follow`, which M4's `ingame_keys` calls after it toggles the byte, and
`wof_invert_vertical_restore`, **an M7 stand-in**, which the saved-game loader calls so that
the preference wins over what the saved game carried.

### The shell's key map

`web/input.js` maps `KeyboardEvent.code`, which is positional, to raw Amiga key codes, which
are positional too, so a German keyboard gives the same codes as an American one and the
same characters come out. The qualifier word carries the two Shift keys and Caps Lock and
never Control. A key pressed with Control, Alt or Command is ignored and left to the browser,
because a page cannot take all of those away from it.

Left out of the map on purpose:

- **The function keys and Help.** A page that swallowed F5 or F12 would take reload and the
  developer tools away from the player. Their only readers in the whole executable are two
  of the debug keys the cheat unlocks (raw `0x59` and `0x5F`), which belong to M4.
- **The key left of 1** (`Backquote`), which is the diagnostics toggle. It is the one
  printable key the game never sees; a name typed in the high-score entry cannot contain it.
- **Right Amiga**, so `text_input`'s "clear the whole line" (raw `0x32` with right Amiga)
  has no key. Backspace and Delete are there and clear a line one character at a time.

Text that names a key to the user names its **position**, because the character on it
differs by keyboard. The seven command letters P, F, G, L, M, R and C sit in the same place
on a German and an American keyboard and may be named by their letter.
