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

With the keyboard assist on, which the page always switches on, the layer also swallows the
cursor keys `0x4C` and `0x4D` while the weapon menu in the hold has the stick, because the
assist steps that menu with the stick alone (`re/notes/porting-m4.md`, "The keyboard assist").

**What the decision costs.** Five keys — P, F, G, L and M — carry a command in every state
outside the line editor, so a plain press of them never reaches a reader as a plain letter
(`test_the_letters_the_layer_always_takes_are_exactly_four`). Nothing the manual describes
is affected, because a plain letter does nothing in the original either. Two things that are
not in the manual are: the cheat sequence `c o l i n` (`re/notes/keys.md`) cannot be typed,
because its `l` is the load command; and of the debug keys the cheat unlocks, `f` and `m`
would be taken as well. Both belong to `ingame_keys`, which M4 ports as it is
(`re/notes/porting-m4.md`, "`ingame_keys` and the pause").

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
  of the debug keys the cheat unlocks (raw `0x59` and `0x5F`), which M4 ports.
- **The key left of 1** (`Backquote`), which is the diagnostics toggle. It is the one
  printable key the game never sees; a name typed in the high-score entry cannot contain it.
- **Right Amiga**, so `text_input`'s "clear the whole line" (raw `0x32` with right Amiga)
  has no key. Backspace and Delete are there and clear a line one character at a time.

Text that names a key to the user names its **position**, because the character on it
differs by keyboard. The seven command letters P, F, G, L, M, R and C sit in the same place
on a German and an American keyboard and may be named by their letter.

## The front end as coroutines

### The rule that makes the two agree

`SPEC.md` section 6.3 asks for stackless coroutines; what makes them line up with the
original is the unit of time. The headless original delivers a VBlank **exactly where the
program waits** (`re/notes/headless.md`), and the shell issues one `wof_pass` per VBlank
(`SPEC.md` section 6.2). So one `CO_WAIT` is one VBlank, and pass `N` runs what the
original runs after VBlank `N`.

That holds only if the port starts where the original starts: `wof_init` runs the
coroutine up to its first wait, which is the one inside `display_init`. The music call of
the title sequence then falls on VBlank 1, as it does in the original, and everything after
it follows (`test_the_music_plays_the_same_notes_at_the_same_instants`, since M8 part 2).

`src/coro.h` has the macros and the two rules the switch trick imposes: a local that must
survive a wait belongs in the context struct, and no `CO_` macro may sit inside a switch of
the routine's own. The first rule is not a style point — a local read after a `CO_CALL` is
read uninitialised, because the resume jumps past its initialisation.

### The waits

| Original | Port | Rounds |
|---|---|---|
| `wait_frames_or_fire` `0x016EEE` | `src/fade.c` | one `WaitTOF`, then up to `n - 1` more |
| `menu_input` `0x018194` | `src/fade.c` | one per round; 1800 and it returns 1000 |
| `wait_input_release` `0x018228` | `src/fade.c` | up to nine |
| `wait_vblank` `0x01AA3E` | `src/screen.c` | none when the flag is already set |

`wait_vblank` needs the flag `vblank_server` sets and `cop_install` clears. The port keeps
that much of `cop_install` and nothing else: the copper list has no meaning here, but the
fact that installing one makes the next wait really wait does.

### The fades, and the one provisional setting

A fade is sixteen steps of `colour_lerp` and a copper rebuild with **no wait in it at all**,
so on the machine its duration is CPU time and nothing in the executable says how much
(`re/notes/display.md`, `SPEC.md` section 10, point 6). The port gives a step a fixed
number of VBlanks, `WOF_FADE_VBLANKS`, **provisionally 2** (`src/fade.c`, `wof_set_fade_vblanks`).
The differential tests set it to 0, where the harness's fades take no time either, and the
two then agree VBlank for VBlank.

The four routines are one routine with two shapes. Two things about them are easy to get
wrong and are compared against the original over random tables
(`test_the_fades_agree_with_the_original`):

- the number of colours is `1 << depth` of the **first** viewport, in the pair as well, even
  where the second viewport has a depth of its own;
- `fade_to_pair` moves the first viewport's table 1 towards the first target, the second
  viewport's table 1 towards the second, and the first viewport's table 2 towards the
  **first** target again.

`colour_lerp`'s arithmetic is M1's and unchanged: a falling component adds its negative
quotient as a masked two's complement value and carries into the next higher one.

### Views, viewports and what reaches the output

The original keeps two views, each a chain of ViewPort records with its own bitplanes and
its own copper list, and swaps them by writing `COP1LC`. The port keeps the same two views
and the same chain. A viewport is one indexed surface and two 32-word colour tables;
"installing a copper list" is nothing more than saying which view the picture is composed
from. What the copper builder does that is **visible** comes out of the bands `src/screen.c`
hands to `src/video.c`, one per run of output rows that share a source row and a set of
colours. Everything else about it - the list buffers, the sprite parking, the window and
data-fetch registers, the plane pointers - is `replace` in `re/functions.csv`.

Two consequences worth writing down.

- **The display memory moved into the core's state.** A viewport names its surface by an
  offset into one block and its neighbour by an index, so nothing in the state is a host
  pointer and a loaded state brings the picture back with the logic. That is what
  `SPEC.md` section 7.3 asks of `wof_state_load`, and it could not have been had with
  pointers.
- **A view's block is 640 x 260, not the machine's `0xACD0` bytes.** The story scroller
  needs it: its bitmap is 640 x 200, but `story_screen` advances the plane by one row per
  step, 210 times, and the copper shows 230 rows from wherever the plane then starts, so the
  display reads up to row 258 of the view's memory and the text is drawn down to row 209 of
  it. On the machine those rows are the cleared rest of the view's block, and they are
  black here for the same reason. The high-score screen, which needs 61,400 bytes and runs
  over into view B's half on the machine, simply fits.

### The story scroller's ring and its ramps

`story_copper_build` (`0x017D4E`) does two things the port has to keep, and it does them in
three places that look different and mean one thing:

- **The plane-pointer reload.** It is emitted at viewport row `wrap` and only when `wrap` is
  196 or less; the three places that can emit it cover 0 to 15, 16 to 180 and 181 to 196
  between them. Above 196 the wrap point is below the text anyway. In the port that is one
  field, `ring_at`, and the band builder splits the run there.
- **The two grey ramps.** `COLOR01` takes `i x 0x111` at viewport row `i` below the ramp
  count and again at row `196 - i`, keeps the brightest value between them and black below,
  which is why the text is visible between display lines 6 and 200 only. The port gives
  each distinct value a palette of its own; the scroller needs seventeen, which is what
  `WOF_PAL_COUNT` was raised to 24 for.

The wind-down counts the ramp from 16 down to 1, which takes both ramps out and leaves the
screen black.

### graphics.library on indexed pixels

`src/gfx.c` has the seven calls the dialogs, the name entry, the high-score list and the
story scroller make, in JAM1, JAM2 and COMPLEMENT, with `Text` on topaz 8 from the ROM.
Three things about this layer are not the blitter library's:

- **It does not clip.** There is no Layer on these RastPorts, so on the machine a `RectFill`
  with a negative `yMin` writes before the plane, and the story scroller relies on exactly
  that: every line after the first is drawn fourteen rows before the current plane start,
  which is the bottom of the visible window. What bounds a write in the port is the view's
  own memory block, which is what bounds the original's too.
- **`Draw` is parallel to an axis.** Every `Draw` the front end makes is a side of one of the
  dialog's boxes or of the name entry's frame, which
  `test_every_draw_the_front_end_makes_is_parallel_to_an_axis` holds it to. A sloped line
  would need the blitter's line mode, whose pixel pattern is an open point of `SPEC.md`
  section 10; `wof_gfx_draw` refuses one rather than guessing.
- **The pens are what `InitRastPort` left.** This closes the open point M1 left. The
  briefing sets no pen at all, so its text comes out in the foreground pen `InitRastPort`
  leaves, `0xFF`, ANDed with the depth mask by `draw_set_target`: colour 7 on three planes,
  in JAM2. The dialog sets `SetAPen(0x28F)`, which is pen 15 on four planes, and JAM1. The
  line editor sets pen 6, background 0 and JAM2. The high-score list sets pen 0 twice and
  15 once, for the outline.

`shape_draw_xor` (`0x020E24`) is the one drawing routine M1 left out that M3 needs, for the
rank selection's highlight. It uses no mask and ignores the clear byte: inside the clipped
box it exclusive-ors `(set ^ pixel) & M` into the destination, which is the same statement
as the original's two blitter phases because no container on the disk has overlapping plane
masks.

## The file system's write side

Everything the game writes - the high-score file and the saved games - goes into an overlay
in front of the read-only disk (`src/fs.c`). A written file shadows the disk's own of the
same name and a deleted one hides it, which is what AmigaDOS does to the game. The shell
copies the overlay into `localStorage` under one key, `wof:files`, and puts it back at
start **in the order it stored it**, because that order is part of what the dialog's list is
made of.

The overlay is deliberately **not** part of the core's state: a save state is a snapshot of
the running game, and loading one must not un-write a saved game.

### The order of the list

`re/notes/frontend.md` works the rule out and says the order follows from the names alone.
The port implements exactly that: an entry's chain is the AmigaDOS name hash modulo 72,
chains are walked upward, and inside a chain a file the run has written comes before a file
of the disk, because it is newer.
`test_the_directory_comes_out_in_the_file_systems_own_order` checks the port's chains
against the harness's own hash, which was in turn checked against every entry of five
directory blocks of `original/wof.adf`.

## What is a stand-in, and where

| Marker | Where | What it stands in for |
|---|---|---|
| `M4 STAND-IN: the mission` | `src/front.c`, the outer loop | `mission_display_setup`, the ship shapes, the master lists, the sounds and the inner loop.  The mission ends at once, so the high-score sequence follows and the loop comes back to the rank selection |
| `M7 STAND-IN: the loader` | `src/dialog.c` | `save_game_read` (`0x015E1A`).  A load takes the path the original takes when the load fails, which `re/notes/frontend.md` observed: the dialog comes back as a cancel and the rank selection rebuilds its picture |
| `M7 STAND-IN: what a saved game holds` | `src/dialog.c` | `save_game_write` (`0x015E8A`).  The file is written, so the dialog, the list and the rename are the real thing; its contents are not |
| `M7 STAND-IN` | `wof_invert_vertical_restore`, `src/portkeys.c` | the loader calling it so that the remembered flip wins over the saved game |
| `PROVISIONAL` | `src/fade.c` | how many VBlanks one of the sixteen steps of a fade takes |

Demo playback and recording are left out of `rank_select` and of `vblank_server` with a
comment in each: playback asks for `wofdemo`, which is not on this disk, and recording needs
a file name on the command line, which a page has no way of giving. Both are M7.

`"Exit Game"` in the dialog calls `fatal_exit` on the machine, which ends the program. A
page has nothing to end into, so the port treats it as a cancel and says so where it does.

## The development keys

In a mission the save dialog opens on the carrier with G, and the high-score entry follows
a game over with a score that beats the tenth entry. So that both can be looked at without
flying for them, the shell offers three keys **while the diagnostics overlay is up**, and
they are outside the port's key layer on purpose (`wof_dev_set_score`,
`wof_dev_open_dialog`):

| Key | What it does |
|---|---|
| `1` | sets the player's score to 5000, which beats the tenth entry, so the high-score name entry appears at the end of the next mission |
| `2` | opens the **save** dialog after the next rank is chosen |
| `3` | opens the **load** dialog the same way |

`5` and `6`, which were always there, select PAL and NTSC and are now behind the overlay
too, so that a digit typed into a name never goes to the shell instead.
