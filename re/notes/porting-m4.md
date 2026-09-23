# M4: the world, the player and the tick

Milestone M4 of `SPEC.md` section 9: everything the original runs between the end of the
briefing and the end of a mission. Part 1 is the world as a pass: the setup after the
briefing, `frame_update`'s tree and the mission half of the VBlank server. Part 2 is the
player and the tick: `logic_tick` and everything it calls, `run_queued_ticks`,
`ingame_keys`, the restart after a lost aircraft with its waits, and what follows a
mission's end. Addresses use the standard load layout.

Every statement is either **observed**, with the tool or test that shows it, or **read**,
which means it comes from the listing alone.

```text
src/mission.c            the outer loop's reset, the map loader, the setup after the briefing
src/world.c              frame_update and the playfield half of a pass
src/dash.c               the dashboard: the 3-D view and the instruments
src/front.c              main's mission part: the setup's order, the inner loop, the stand-ins
src/input.c              vblank_server's mission half: the counter and the ticker
src/tick.c               logic_tick and its hand-written routines, the map's helpers, the pools' claims
src/player.c             the player update and every C routine below it
src/draw.c               line_draw (the cable), beside the blits of M1
src/records.def          the record layouts, with the original's offsets
src/mission.def          the tables: fixed ones in DATA and the allocations, at fixed places
tools/reach_observe.py   what the scripts enter, where, how often; block coverage; cold regions
tools/m4_scripts.py      part 2's scripts, and the player tick by tick while one runs
tools/m4_autopilot.py    the autopilot the landing, the turns and the fuel flight were flown with
tests/m4state.py         the original's state as the port's structs, field by field
tests/m4compare.py       the headless original recorded; the port replayed in two loops, per pass and per tick
tests/m4complete.py      the completeness list: every address a mission writes, accounted for
tests/test_world.py      T1, T2, T3, the pass rates, the key runs, the island, the flip
tests/test_mission.py    the setup on every map and rank, the capacities, the arena
tests/test_oracle_m4.py  the blits against the blitter model, the pure routines under the oracle
tests/test_state_m4.py   states saved in a mission, native and wasm; the release core's hooks
tests/test_page.py       the page in Chrome, a mission flown from the keyboard
tests/test_firefox.py    the same in Firefox, headless and in a visible window
tests/m4_renders.py      pictures of the mission scene, for looking at (dist/m4-part1/, m4-part2/)
```

## What decides what is ported: the reach map

The mission scripts of M4 are `deck`, `flight`, `climb`, `lost` and `gameover` of
`tools/pass_observe.py` (guns and bomb are M5's), and `select`, `turns`, `landing`,
`island` and `fuel` of `tools/m4_scripts.py` ("The scripts of part 2" below); with them the
night mission (the flight script with a poke) and the key runs of `tests/runs/` that start a
mission and press a key in it. `tools/reach_observe.py` runs each under the headless
original with a hook on the first instruction of every routine of `re/functions.csv` and
counts every entry by the part of the run it happened in and by the harness's phase
(observed):

```text
.venv/bin/python tools/reach_observe.py                                 the tables below
.venv/bin/python tools/reach_observe.py --markdown TABLE.md             the same, as Markdown
.venv/bin/python tools/reach_observe.py --blocks --json REACH.json       with block coverage
.venv/bin/python tools/reach_observe.py --part2 --blocks --setups --json REACH.json
                                                     every script, run and setup of M4
.venv/bin/python tools/reach_observe.py --cold REACH.json                the cold regions
```

The windows are marked by the instruction `main` has reached: `outer` from the outer loop's
head at `0x010066` to the call of `rank_select`, `rank` the rank selection, `pre-briefing`
from its end to the briefing (`load_dash_assets`, `map_load`), `briefing`, `setup` from the
briefing's end at `0x0100B2` to step S at `0x01010A`, `mission` from step S to the end of the
inner loop, `between` from a mission's end to the next one's briefing, and `after` once the
mission is over. The phases are the harness's: V inside a VBlank, T inside `logic_tick`'s
tree, F inside `frame_update`'s tree, M the main program outside all three.

With `--blocks` the tool also records every basic block executed, so that for any routine
it can say which of its instructions the five scripts ran (`cold_ranges`); with `--setups`
it adds the setups of all fifteen maps, each loaded under its own number and run to step S,
which are the runs the setup comparison uses. `--cold` then lists, for every routine M4
ports, each region no run executed, with the stand-in marker that covers it or what it is
otherwise; a region that is neither fails the tool. That list is "Appendix: the regions no
run executed" at the end of this note, and it is what decides which routine is `ported`,
`partial` or `verified` in `re/functions.csv`.

### The answers the reach map gives (observed)

- **`line_draw`** is entered only in the landing script, 26 times, from `0x0103A6` while
  `player_on_deck` is 7: the arresting cable, from where the hook caught it to the hook. It
  is ported from the documented line mode and is provisional ("What is provisional").
- **The ticker.** Probes inside `vblank_server` at the scroll (`0x011856`), the message
  pointer (`0x0118DE`) and the glyph copy (`0x0118F8`) never fire in the five scripts: no
  ticker message runs.
- **Day and night.** `night_flag` (`0x025390`) is 0 at step S in all five. Its only writer
  is `choose_night` (`0x0111FC`), and its only caller is `main` at `0x010160`, on the path
  from one mission of a campaign to the next: the first mission of every campaign is day,
  whatever the map (read, and observed as the only writer in the write summary). The maps
  that can be night are those above 6, so of the first missions of the seven ranks, maps
  8, 10, 11 and 12 could be night only when reached as a later mission (read, from
  `mission_map_table`). The night mission is therefore reached by a poke; see "Night".
- **The eighth-scale view** is switched by `view_step` (`0x024F36`), which only
  `snapshot_for_draw` writes, every pass, from `0x0253B0`; `flight` and `climb` show it at
  1 in 711 and 538 of their passes, the other three never (observed). `0x0253B0` is
  written by the player update: 1 while the aircraft is above y `0xBA`, else 8.
- **`ingame_keys`** is entered from `main`'s inner loop at `0x01010E`, in phase M, once per
  head of the loop (passes plus one), never from inside `frame_update`.
- **Entropy.** Before the rank selection `0x01CAC8` draws once (the reset of the outer
  loop's head), in the setup twice (the player's reset, twice). In a mission `0x014D50`
  draws twice per pass in the eighth-scale view with the aircraft in the air (F),
  `0x01CAC8` once per restart inside the tick (T), and `draw_dashboard` once per pass while
  the tank is empty in the air (the fuel script). The island flight's draws in the tick are
  M5's (`target_fire`, `smoke_claim` from the target's fire).

The tables of every routine per window and phase, with entry counts per script, are in
"Appendix: the reach map" at the end of this note.

## The mission setup

`main` reaches a mission in two steps (read, and observed as the order of the harness's
file log and of the port's trace, which the comparison holds equal):

1. **After the rank selection** (`0x01009E`): `load_dash_assets` loads `dash.shp` or
   `nightdash.shp` and the dashboard picture by `night_flag`, and `map_load` opens the map
   that `mission_map_table[rank * 4 + mission]` names, allocates its record list and runs
   `map_scan`. Then the briefing.
2. **After the briefing** (`0x0100B2`, and `0x010170` for a later mission of a campaign):
   `dashboard_invalidate`, `mission_display_setup` (the game screen, the colour tables, the
   dashboard picture into both views), `load_ship_shapes`, `build_master_lists`,
   `sounds_load`; unless the game was loaded, `mission_reset_tables` and
   `player_restart_state`; `outside_mission` cleared; **one logic tick run by `main`
   itself** (`0x0100F2`), `input_queue_clear`, and the inner loop at `0x01010E`, which is
   step S of the headless original.

The port runs the same tick there, and at step S every registered global and table agrees
with the original's, nothing left out (`test_the_setup_agrees_at_step_s`).

### The map loader

- `map_scan`'s first walk reads **one record past the end of the list** (the loop ends on
  `dbmi`); the record list's pool is one record longer than the longest map for that.
- Each enemy ship's block of deck planes (`ship_block`, `0x01252C`) comes from two bytes of a
  count table by map number and a list of words. The four lists lie back to back from
  `0x0235A8`, and a count can be larger than its own list: map j's battleship has six
  planes and five entries, and the loader reads on into the cruise ship's list. The port
  keeps the counts from `0x023530` and the lists from `0x0235A8` as one table each and
  addresses them by the original's offsets.
- A count of 0 for a ship the map carries makes `dbra` run 65,536 times. No map is loaded
  under a number that does that, but laying map m or o over map a's file does: the
  original then writes far past the block and faults. The overlay comparison leaves those
  two out; every map is also compared under its own number, where this cannot happen.
- The ship records at `ship_records` (`0x025460`, `0x1E` bytes each) are, in this order:
  the destroyer, the battleship at `0x02547E`, the cruise ship at `0x02549C`, the Japanese
  carrier at `0x0254BA`, and the player's carrier at `0x0254D8`. `ship_order` (`0x02555A`)
  lists them as destroyer, carrier, battleship, cruise ship, Japanese carrier.

### Night

`night_flag` is written only by `choose_night`, between two missions of a campaign, so the
first mission of a campaign is always day (see the reach map's answers). The night mission
is compared by a **poke**: `night_flag` set to 1 on both sides at the rank selection's end
(`0x01009E`), before `load_dash_assets` reads it. The port then loads `nightdash.shp`, the
night dashboard picture, `night.p` and `nightocean.p` in the original's order, and the whole
flight script agrees in both loops (`test_the_night_mission_agrees_in_both_loops`).

## The pass

`frame_update` (`0x010228`) in the original's order: `wait_vblank`; the counter
`0x0253A6`; the playfield's clip and the back buffer as the target; `snapshot_for_draw`,
which copies the logic's positions (the player, the ships' rows, the ship blocks
`0x025096` into `0x024F38`) and steps two counters; the view: `view_shift` 3 in the
eighth-scale view, else 0, `view_x` is `0xFF60 << view_shift` plus the drawing's x,
`view_y` is `0x4B8` in the eighth-scale view and otherwise `0x97` plus how far the height
exceeds `0x83`; `split_row` is that row at full scale and `0x97` in the eighth-scale view,
and the copper's split line lies there, at most at `0xA2`; the guarded call of
`player_lost_restart`; `draw_world` with the sky, the map strip and its
layers; the Smoke, Soldiers and Splashes pools; the object records; `weapon_marker`;
the balloons; `draw_game_over`; the dashboard's clip and the back buffer's dashboard;
`map_window`; `draw_dashboard`; `frame_drawn` set; `flip_buffers`. The guarded call of
`player_lost_restart` runs the same coroutine as the tick's restart; no instruction of the
executable sets its guard `0x024F24`.

- **When a pass may start.** One `wof_pass` runs per VBlank. `frame_update` starts only
  when `wof_vblanks_per_pass` VBlanks (2 by default, `wof_set_vblanks_per_pass`) have
  happened since the previous pass began and `vblank_flag` is set, which is the headless
  original's rule (`re/notes/headless.md`, "Scheduling").
- **Signed branches after a subtraction** decide on the exact difference, not on the
  wrapped 16-bit or 8-bit result: `subq.b #1` and `bgt` in `draw_game_over` set
  `quit_flag` for a count of `0x80`, and the range test of `0x014DB8` gives no frame for a
  target more than `0x200` pixels ahead as well as behind.
- **The dashboard's instruments** are those of the manual's pages 8 and 9: the weapon
  counter (the weapon's icon and two drums), the Hellcat counter (a drum), the oil pressure
  and fuel gauges (needles, each with a red light that blinks when low), the 3-D view in the
  middle (`map_window`, `0x01417E`: sky and sea, the strip of map records ahead of the
  aircraft, and the cursor that serves as an artificial horizon, whose row follows the
  height), the score counter, and the enemy plane counter at `0x02537F` (two digits and a
  kill icon per plane, M5's).
- **The dashboard** keeps one cache of every instrument per buffer (`view_caches`,
  `0x027F30`); an instrument is drawn only when its value differs from what that buffer
  shows. The digits are slices of dashboard frame 7 blitted without a mask at the row
  `digit_rows` gives, added to the low byte of y and sign-extended; the drums are frame 6
  drawn with its mask under the drums' clip rows.
- **`flip_buffers`** pokes COLOR01 of the back list's copper with the sky colour, or with
  `flash_colour` on odd counts while `flash_count` runs, then shows the back view. The poke
  lands in the first viewport of the view only, above the split line.
- **The VBlank's mission half** (`0x011842` to `0x01195C`): nothing outside a mission; in
  one, `0x025410` counts VBlanks and the ticker scrolls its plane one pixel left on every
  VBlank while a message runs, taking the next character into the hidden column at byte 80
  whenever the last one has scrolled its width. **The messages are formatted at run time**
  by the tick with `sprintf` into `ticker_text` (`0x02716A`, 300 bytes) or
  `ticker_text_2` (`0x027E00`, 102 bytes); the port keeps both buffers in its registered
  state and reads the message pointer's bytes from there. No script shows a message; the
  ticker is held to the original under the oracle, VBlank by VBlank.

## Where mission memory lives

Every table a mission uses has a fixed place and a fixed capacity in the core's state
(`src/mission.def`), with the record layouts of `src/records.def`, whose fields keep the
original's offsets:

- **Fixed tables** in DATA and BSS keep their original addresses: the object records, the
  player's record, the four enemy-aircraft records, the airfields, the five ship records,
  the dashboard's caches, the two copies of the ship blocks, the frame tables and the
  record list's end.
- **Allocations** (`WOF_POOL`) are found in the original through their pointer global and
  kept at a capacity the largest map fits: the record list 3,576 words (map m has 3,570
  with the one read past the end), the slot-4 and slot-3 targets 16 each (14 and 13 on map
  m), the slot-`0x0F` targets 32 (30 on map o), the soldiers 160, the four gun lists 16
  each, the pools of `alloc_pools` at their own sizes, and `MasterList` and `AthList` at
  278. `test_the_pools_hold_every_map` holds every capacity against all fifteen maps.
- **No pointers.** A shape pointer becomes a handle (`((slot + 1) << 11) | index`, 0 for
  none), a pointer into the map a byte offset, a pointer to an allocation the port keeps at
  a fixed place a flag. `tests/m4state.py` converts the original's state field by field
  in the same way, which is what the comparison compares.
- **The arena** hands out zeroed memory, as `MEMF_CLEAR` gives the original, also when an
  address is handed out again after `wof_arena_reset` or `wof_arena_release`; nothing is
  taken from it after the assets are loaded, which thirty-one mission setups in a row show
  with `wof_arena_used` unchanged.

## How the port is held to the original

`tests/m4compare.py` records a script under the headless original with a dump of the
state after every step, the drawing calls, every entropy read and the writes of every
tick, and replays its schedule through the port with the fades at 0: the keys, the raw
controller state of every VBlank, one `wof_pass` after each. Two loops:

- **Open** (T1): at the end of every step the port's registered state, its views, its
  entropy position and the mirror markers are set to the original's state after that step,
  so that every pass and every tick starts from the original's state before it and is
  compared alone.
- **Closed** (T2): the port runs on its own from the program's start, the front end
  included, and nothing is handed over.

After every pass, in both loops: every registered global and table, the drawing calls with
their arguments, the entropy draws with their callers, which view is in front, the palette
of every output row, and the map's records drawn against `tools/map_decode.py`. After every
tick: every registered global and table, the drawing calls the tick made (the restart
clears the playfield and flips the buffers), the entropy it drew, the VBlanks it waited,
which view is in front, and the mirror markers of `hellcat.shp` and `Torpedo.shp`. The
setup's own tick is compared by its state; its drawing and entropy are the setup's, which
step S compares. The headless original runs no blits, so the pixels themselves are not
compared; the blits are held to the blitter model instead.

A tick that waits waits in the port because the port's tick waits: the restart spins on
`WaitTOF` inside the player update, each `WaitTOF` is one `CO_WAIT`, and the schedule's
VBlanks fall where they fall. The VBlanks a tick waited count toward the next pass, as the
original's do.

| Check | Test | What it covers |
|---|---|---|
| T1, T2 | `test_every_pass_and_tick_agrees_in_both_loops[deck, flight, climb, lost, gameover, select, turns, landing]` | every pass and every tick of eight scripts, both loops |
| T1, T2 | `test_the_long_scripts_agree_in_both_loops[fuel]` (slow) | 5,778 ticks of the fuel flight |
| T1, T2 | `test_the_night_mission_agrees_in_both_loops` | the flight script as a night mission |
| T2 | `test_the_key_runs_agree_in_both_loops[...]` | 20 key runs of M3: pause and continue, the restart, the flip, the save refused in the air, the load dialog, the music, the high scores cleared while paused, the cheat sequence |
| T1 by attribution | `test_the_island_flight_differs_only_where_a_stand_in_was_reached` | the flight over the island without the button: every differing pass or tick reached a marked stand-in in that same step |
| T2 at 1 and 3 | `test_the_closed_loop_holds_at_other_pass_rates[1, 3][lost, turns]` (slow) | the lost and the turns scripts at one and three VBlanks per pass, against the original run at the same rate |
| flip | `test_the_flip_with_the_stick_turned_round_flies_the_same_flight` | the port with the flip on and the turns script's forward and back exchanged: every pass and tick agrees apart from the flip's byte |
| setup | `test_the_setup_agrees_at_step_s` | everything the setup writes, its tick included, at S |
| T3 | `test_every_address_a_mission_writes_is_compared_or_excluded` | see "The completeness list" |
| V4 | `tests/test_mission.py` | the setup on thirteen maps laid over map a, on all fifteen under their own numbers, and for the first mission of every rank, with the map file the loader opens |
| V5 | `tests/test_oracle_m4.py` | `rect_fill` on 5 and 4 planes under the pass's clips; `shape_blit` without a mask for every dashboard shape and every fifth world shape; the digit and drum slices; `line_draw` for 400 random lines against the line mode of the model |
| V6, T4 | `tests/test_oracle_m4.py` | the ticker, the game-over countdown, the gauge resets, `deck_span`, `ship_at_offset`, `clip_to_waterline`, the 3-D view's cursor; `player_motion` against the original and `tests/ffp_model.py`; thirteen routines of the player, a turn's step, the crash and the ground over random states; `ground_height`, `map_slot_at`, `record_at`, `on_water` and `record_on_ship` on five maps; whole state |
| T5 | `tests/test_state_m4.py` | states saved flying left with the shapes mirrored, inside the restart's waits, and paused, loaded into the same core and a fresh one with another seed: state, picture and the next 400 VBlanks identical, native and wasm |
| T7 | `tests/test_page.py`, `tests/test_firefox.py` | a mission flown on the page with the keys held in real time ("The page") |

`shape_mirror_x` is held to the original over every shape of both containers, twice, by
M1's `test_shape_mirror_x_matches_on_every_shape`.

The tests marked slow - the fuel script and the pass rates - run only when asked for:

```text
.venv/bin/python -m pytest tests/            the suite without them, about 25 minutes
.venv/bin/python -m pytest tests/ --slow     everything, about 35 minutes (or WOF_SLOW=1)
```

The controls, each run by changing the port and reverting it:

- the drawing's player x plus 8 in `snapshot_for_draw`: the calls, the map draws and the
  state differ from pass 1;
- `0xFF60` in the view's formula changed to `0xFF68`: the calls and `view_x` differ from
  pass 1 (the map strip is placed by the drawing's x, not by `view_x`, on both sides);
- the first `rand_beam` of `0x014D50` skipped: pass 424 of the climb script draws one
  value fewer than the original, named with its caller, and `rand_state` differs;
- `player_motion`'s + 50 before the division by 100 made + 25: the oracle test's case 7
  leaves the player's x and horizontal speed one lower than the original's;
- forward and back swapped where the tick takes its byte: tick 151 of the turns script,
  the first with the stick forward, reads 6 where the original reads 5, and the frame,
  `0x025A9C` and the markers differ from there;
- the restart's last `WaitTOF` removed: tick 324 of the lost script waits 20 VBlanks where
  the original waits 21, and the VBlank counters differ from there;
- the mirror markers left out of a loaded state: the save state flying left, loaded into a
  fresh core, gives another picture and another state 400 VBlanks on;
- `player_reset`'s draw of `rand_mod` skipped: tick 324 of the lost script draws nothing
  where the original draws, and `rand_state` and the player's `+0x10` differ;
- one row of the completeness list removed: the test names the range and its writer;
- `line_draw`'s accumulator started one higher: two pixels of a line differ from the
  original's programme replayed by the model;
- the arena's clearing removed: `wof_alloc` after a reset hands out old bytes;
- positively, the closed loop holds at one and three VBlanks per pass as it does at two,
  and the flip with the stick turned round flies the same flight.

### The completeness list

`tests/m4complete.py` sorts every address the original writes during a mission - in the
setup, in a tick, in a pass, in a VBlank server, in the main program between them - into
three kinds: a registered field; state the port keeps in another form and compares by
another check (the double buffer as the index of the view in front, the colour tables as
the palette of every row); or state the port does not keep, with the reason and the
milestone. Each row names the routines that write its range, and a write by any other one
makes the address uncovered again. The runs are the eight scripts of T2, the night mission,
the island flight, and the `guns` and `bomb` scripts of `re/notes/passes.md`, which reach
the soldiers and the targets (the Ricochet pool is dead, `re/notes/porting-m5.md`).

What is not kept, by reason: the graphics library's structures (the views, the
viewports, their RastPorts and BitMaps, the drawing target, the plane pointers), which the
port's screen model replaces (`SPEC.md` section 6.6); the copper lists and their
bookkeeping, whose effect is the palette of every row; the blitter's parameter block and
`MaskBuffer`, which the port's blits do not need; the loader's result registers; two
pointers that always point at the same global (`player_record`, `0x027DF4`), and one the
walks over the enemy aircraft set before every read (`0x027DF0`); the allocator's headers;
the files as they are read; `MathBase`, which the first floating-point call opens; the copy
of the plane mask `line_draw` shifts a plane at a time; the sound engine's state, its eight
slots of `0x18` bytes that the tick's sounds write (the engine, the lift, a touch-down, an
object left behind) and the sample pointers, M8's; two bytes the weapon drop writes, M5's;
and the planes of the dashboard picture, which the port unpacks with M3's decoder.
`hellcat.shp` and `Torpedo.shp`, which the tick mirrors in place, are compared as their
markers after every tick; the port mirrors its converted pixels the same way.

The couplings of `re/notes/passes.md` that no run reached:

- **The score from a soldier's death** (`0x013EEE`): not carried; `soldiers_draw` is M5's
  stand-in beyond an empty walk.
- **The player's record `+0x12`** (the oil): not written by any pass of the port, and in the
  runs no pass of the original wrote it either; `0x014F5C`'s path that could is M5's
  stand-in.
- **`frame_update`'s call of `player_lost_restart`**: carried, as a call of the same
  coroutine, but never taken: no instruction of the executable sets its guard `0x024F24`.

## What stands in, and where

A stand-in is marked `M5 STAND-IN`, `M6 STAND-IN` and so on, with the first address or the
range of what it stands for. Reaching one counts `wof_standin_hits` in the state, which the
diagnostics overlay shows; in test builds it is also logged, and every comparison fails on
any stand-in reached. In the release build a reached stand-in does the least harmful thing
it can: it skips what it stands for. The release core has no test hook
(`test_the_release_core_has_no_test_hooks` reads the name section of `dist/core.wasm`).

- **The next mission of a campaign** (`0x010132` to `0x01018D`) is M7's and ends the
  campaign instead. Its condition, `0x0253BC`, is set only by `0x015694`, which only the
  last target destroyed (`0x0146DC`, `soldiers_draw`, M5) or a ship sunk (`0x011CD8`, M6)
  reaches.
- **A saved game loaded** is M7's (`0x019152` in the dialog, `0x01CDD4` in `ingame_keys`):
  the load dialog comes back as a cancel. The key run `flight-flip-then-load` loads one in
  the original, which is why it is left out of T2.
- **The sound engine** keeps nothing the port keeps except the two values `0x012132` eases
  (`0x02542C`, the engine's volume, and `0x02542E`, its pitch), which are registered and
  compared; the sounds themselves are M8's.
- Every other region is listed with its marker in "Appendix: the regions no run executed".

## What is provisional

- **The pass rate**, 2 VBlanks per pass, until the user's slow-motion film of the real
  machine settles it; the closed loop holding at 1 and 3 says the logic does not depend on
  it.
- **`line_draw`'s pixels** (`SPEC.md` section 10, point 7): the clipping is the original's
  arithmetic, and the line itself is the blitter's line mode as documented, the Bresenham
  walk of `dmax + 1` pixels from the first end with the accumulator `2*dmin - dmax`. The
  headless original draws no lines, so in the scripts only the call and its arguments are
  compared (the landing script's 26 calls agree). `tests/blitter.py` models the line mode
  from the same documentation, and `test_line_draw_matches_the_blitter` replays the
  original's own register programme for 400 random lines in every octant and against every
  edge: that holds the port's clipping, octant, accumulator, start and length to the
  original's, but not the line mode's pattern itself, which wants a comparison with a
  cycle-exact emulator.
- **The ticker's message bytes** are read from `ticker_text` and `ticker_text_2` and from
  the constant DATA hunk; a message anywhere else is M7's stand-in.
- **The ship-block reader** gives 0 for a word past the four lists; no map reaches that, and
  a count of 0 for a carried ship, which would, faults the original.
- **No pixel of the mission scene is compared with the original**, because the headless
  original runs no blits. The drawing calls, the palette of every row and the blitter model
  together stand for it; a blitter in the headless original would allow a direct check.

## The scripts of part 2

Each is a raw schedule of `[VBlanks, letters]` for the headless original
(`re/notes/headless.md`), in `tools/m4_scripts.py`; `trace NAME` prints the player tick by
tick while one runs.

| Script | What it flies | Ticks |
|---|---|---|
| `select` | the weapon menu in the hold: the stick back three times, forward four times, back once, each a step of the menu with its pause; the torpedo chosen; the lift, the roll and the climb | 410 |
| `turns` | turns both ways low and high, level, climbing and diving; one in the eighth-scale view, one at the ceiling; a glide with the stick left alone, in which the airspeed falls to its floor of 1000 and the aircraft sinks; the stick forward alone while flying left, which sets `0x025AAA` | 887 |
| `landing` | out to the right, back from the right low over the bow, a touch-down with the stick forward alone, the fourth cable, the taxi to the lift, the lift down, the next weapon in the hold, the lift up and a second take-off | 767 |
| `fuel` | back and forth over the sea east of the carrier at y 400 until the tank is empty, the fall into the sea and the next aircraft | 5,778 |
| `island` | the flight to the island of map a and across it at y 412 without the button | 960 |

The turns, the landing and the fuel flight were flown by `tools/m4_autopilot.py`: a policy
looks at the player's state every VBlank of the headless original, chooses the stick and the
button, and the choices, compressed into runs, are the script, which the original then
flies the same way without it (it is deterministic for a given schedule).

- **The landing** was found by observation in a few rounds of the policy. What makes it
  work: the approach from the right with the aircraft facing left (the manual, page 6),
  a glide path to the bow at 0.08 pixels of height per pixel of distance, the stick
  forward alone at the bow, and the stick forward held after the touch-down. The last is
  what the hook needs: on the deck `0x01C4E8` sets `0x025A9C` whenever the airspeed is
  above 600 and the stick is not forward, and the hook (`0x01B92E`) catches only while
  `0x025A9C` is clear.
- **The fuel flight** holds the button only inside its turns, from attitude 4 to 20.
  Left alone for 1,349 ticks the enemy's countdown (`0x01BC02`) brings the enemy aircraft,
  which are M6's, and only the button raises it again, to 750; held in level flight the
  button fires the guns and tapped it drops a weapon, both M5's, and in a turn at those
  attitudes it does neither.
- **The island flight** reaches M5's stand-ins in the pass (the targets' guns fire at the
  aircraft, their smoke, the soldiers) and in the tick, so it is judged by attribution.

## The tick

`logic_tick` (`0x011386`) and its routines are `src/tick.c`, in the original's order
(`re/notes/objects.md`, "The order of a tick"): nothing while paused; in the air the oil and
fuel timers; `0x027346` in turn 0 and 1; the swell's cycle (`0x0253AC` counts down from
`0x0253E8` and `0x0253AE` takes the next of `0x024C44`); the input byte; the weapon menu
(`0x0112B0`) and the lift (`0x011460`) once `0x026D3E` has run down; the player
(`0x01C660`); the enemy aircraft (`0x01E7D6`); the engine's sound (`0x012132`); the guns
(`0x01B682`); the sound slots (`0x012066`, M8); the shot's origin (`0x011274`); the engine's
smoke (`0x011BFC`); the object records (`0x010A72`); the guns' splashes (`0x0119BC`);
`0x027348` counted down; the airfields (`0x011622`); the ships' launches (`0x011510`); the
ships sinking (`0x011CAE`); the targets' timers (`0x011DE4`); the balloons (`0x011C5E`).
`run_queued_ticks` runs one per queued byte and none while `pause_flag` is negative.

The player is `src/player.c`: every C routine from `0x01AA6E` to `0x01CB74` that the update
reaches, `player_motion` on the value forms of `src/ffp.h`.

**The tick waits.** A lost aircraft's next one (`0x01AF7C` into `0x0135CE` and
`player_lost_restart`) clears the playfield, flips the buffers and spins on `WaitTOF` from
inside the player update: twenty times counting `0x027452` down, and once more that finds
it zero. So the path from `run_queued_ticks` down to the restart is a chain of coroutines,
and the twenty-one VBlanks fall inside the tick, as they do in the original; the input
queue fills meanwhile, and the ticks after the restart run in the same pass. The VBlanks
the tick waited count toward the next pass. A `CO_CALL` cannot sit inside a switch of the
coroutine's own (`src/coro.h`), so the player update's switch on the state is a chain of
`if`s.

**Tables read past their end.** The player's code indexes constant tables by attitude,
frame and pitch, and an index can run past a table into the globals behind it: the wheel
table `0x025E3E` at attitude 9 is `0x025E50`, which `0x01BCCE` writes. The port reads a
table by its original address, from the registered global where one covers the byte and
from the executable's constant image elsewhere (`wof_image16`); the oracle test of the deck
state found that case.

### The player's states

`player_on_deck` (`+0x0C` of the player's record) selects the case of the update:

| State | What it is | Observed in |
|---|---|---|
| 0 | in the air: the controls, `player_motion`, the ground | every flight |
| 1 | on the deck or in the hold: the deck's controls, the roll, its ends, the hook | every script |
| 4 | coming down: out of fuel or oil, or the ground touched away from the deck | fuel, lost, gameover, the page |
| 6 | in the sea, sinking a pixel every third tick | lost, gameover, fuel, the page |
| 7 | held by a cable: the airspeed falls by `0x6E` a tick, then 1 | landing |
| 8 | burning, a wreck at rest on land or on a ship above y `0x14` | read, and the oracle test of the crash |
| 11 | the lift moving; the height follows the lift until `0x025394` is 0 | every script |
| 2, 3, 5, 10 | the lift's case as well; never set | read |
| 9 | nothing; never set | read |

### Landing, refuelling, rearming

- **The touch-down** is `0x01BA80`: over the deck (`0x0253FC` to `0x0253FE`), level, the
  wheels at the deck's height and the carrier afloat, touching makes state 1 if the
  aircraft faces left with the stick forward alone (`0x025AAA`); anything else there
  bounces, with the vertical speed and the pitch turned round. Away from the deck touching
  is a crash (state 4).
- **The cable** is `0x01B92E`, on the deck: at 600 or more of airspeed and with
  `0x025A9C` clear, the hook `0x18` behind the aircraft within 8 of one of four cables,
  `0x38` apart from `player_start_x + 0x46`, makes state 7. The landing script's hook
  caught the fourth.
- **Refuelling and rearming** happen in the hold. The button on the lift, stopped, with the
  carrier afloat (`0x01B5B0`) takes the aircraft down (state 11, `0x025394` 3); the lift
  (`0x011460`) sinks a step a pass and at `0x20` calls `player_restart_state`, which fills
  the tank (`0xC0`), the oil (`0x80`) and the weapons by type, and raises the weapon menu.
  The stick or the cursor keys step the menu, the button or Return closes it and sends the
  lift up (`0x0112B0`).

### Every way an aircraft is lost

- **Into the sea**: touching the ground away from the deck, or leaving an end of the deck too
  slowly to climb (`0x01C5F4` makes it state 0 at the deck's height, and it comes down).
  The crash (`0x01AFBA`) finds the sea under it, floats the aircraft to rest with a splash,
  and state 6 follows. Observed in lost, gameover, fuel and on the page.
- **Out of fuel or oil**: in the air with the fuel below 0 or the oil below `0x60` the
  update makes state 4 and the crash follows (the fuel script, into the sea). Only enemy
  fire lowers the oil (M6).
- **On land**: the crash burns the wreck at rest (state 8, with smoke); what it does to the
  island's targets is M5's stand-in (`0x01BBF4`). Read, and held to the original by the
  oracle test of the crash and the ground; no script crashes on land.
- **On a ship**: on its deck the wreck comes to rest (6 below y `0x14`, else 8); against its
  side it slides back with the sky's flash (`0x01B0E2`). Read and held by the same test.
- **Shot down, or the carrier sunk**: M6's. With the carrier sunk (`+0x0C` of its record
  at 0 or below) the next aircraft is the game's end.

After a loss the wait (`0x01AF7C`) sets `game_over` when the last life is going, and after
150 ticks, or 30 with the button, `0x0135CE` takes a life and restarts: the aircraft back on
the lift in the hold, facing left, with the weapon menu up. With no life left
`player_lost_restart` sets `game_over` and `quit_flag` instead.

### What ends a mission

In M4's reach: **the game over** above, after which `main` (`0x0101C6`) clears the ticker,
fades out, ends a demo and, unless one was played, shows the high scores with the name
entry; **the restart** (Control-R, the port's R while paused), which sets `end_of_mission`
and `quit_flag` and goes straight back to the rank selection; and the cheat's `q`, which in
the original ends the program and in the port goes on as a game over does. A mission won
goes on to the next mission, which is M7's.

## `ingame_keys` and the pause

`ingame_keys` (`0x01CCF6`) is ported whole, as a coroutine because two of its commands wait
(re/notes/keys.md, "In flight and paused"): the restart fades out, the save and the load
open M3's dialog. The save opens only on the carrier (`player_on_deck` 1), then the play
screen comes back (`screen_game_restore`, `0x016D32`); the load comes back as a cancel
(M7). Control-C deletes the high scores; the flip calls `wof_invert_vertical_follow`; the
cheat sequence and the debug keys are there as they are, and on the page they cannot be
typed (re/notes/porting-m3.md). The space bar's memory figures show the arena's free bytes.

The inner loop's pause waits with `wait_next_vblank` (`0x01AA32`), which clears the flag
and waits for it without clearing it again, so a `frame_update` right after the pause finds
its VBlank already there; with `wait_vblank` instead the first pass after the pause comes a
VBlank late (the key run `flight-escape-twice` shows it).

`wof_request_pause` asks for the pause from outside: the next `ingame_keys` of a mission
sets `pause_flag` as Escape does, and outside a mission the request is dropped;
`wof_paused` says whether a mission is paused. The shell asks when the page is hidden, so a
mission comes back paused.

## Save states and the mirror markers

The markers at `+8` of the records of `hellcat.shp` (116 records) and `Torpedo.shp` (100)
are game state (`SPEC.md` section 7.2): `aircraft_frame` mirrors a frame in place when the
facing it wants differs from its marker. The port keeps them in the state, compares them
after every tick, and on a load mirrors every converted shape whose loaded marker differs
from its own (`wof_assets_follow_state`). A state saved flying left, inside the restart's
waits, or paused continues identically in the same core and in a fresh one with another
seed, on both targets (T5).

## The page

On the page a mission is started, flown and ended from the keyboard. The page checks in
Chrome and Firefox hold the keys in real time and read the player off the diagnostics
overlay's `player` line (`wof_dev_player`, a read-only export, and `wof_paused`): the
weapon menu, the lift, the roll with the stick forward late in it (forward from the start
keeps the tail down and the aircraft leaves the bow too slow to climb), the climb, the
pause stopping the tick count and the second press letting it run, the flip, and the flip
still on after a reload; in Chrome also a dive into the sea, the button for the next
aircraft, two aircraft rolled off the bow, the game over and the high-score entry. The page
switches the keyboard assist on at start (below), the overlay's player line shows the weapon
type, and both browsers tap the up key in the hold as soon as the mission scene is there,
inside the menu's first fifteen ticks, for one step; then three times, a tenth of a second
each and a tenth apart, for three steps, and once more with the flip on, where up still
steps up.

## The keyboard assist

`src/assist.c` is the port's own policy, decided with the owner on 2026-09-22, like the key
layer of `src/portkeys.c` (`re/notes/porting-m3.md`, "The port's own layer"). One switch,
`wof_set_keyboard_assist`, turns on both halves below. The core starts with it off, which is
the original, and every comparison with the original runs that way: the open and the closed
loop, the key runs, the oracle tests and the front end. The page switches it on at start.

### What the original does

The weapon menu in the hold (`weapon_menu`, `0x0112B0`) steps on the tick's input byte, which
`vblank_server` samples every fourth VBlank through `read_joy_bits` and its flip; when the byte
is 0 it takes `last_key` instead, so the cursor keys `0x4C` and `0x4D` reach it as well. After a
step it sets `weapon_menu_wait` (`0x02536E`) to 2 and counts that down only on ticks that carry
input, sideways bits included, so one step costs three sampled inputs; the menu opens with 1
there, so the first step falls on the second sample. The tick does not run the menu for the
first 15 ticks after it opens: `player_restart_state` (`0x013684`), the only writer of
`0x026D3E`, sets it to 15 at each of its three callers, the mission's setup (`0x0100D6`), the
lift reaching the hold (`0x0114D2`) and the next aircraft after a loss (`0x01362C`), and
`logic_tick` runs the menu only once it has counted down (`0x011402`). A press in that window,
about a second, is lost. Observed under the headless original, twelve taps of the stick
forward, 20 VBlanks apart:

| Tap | Steps |
|---|---|
| 1 VBlank | 1 |
| 2 VBlanks | 2 |
| 4 VBlanks | 4 |
| 8 VBlanks | 8 |
| 12 VBlanks | 12 |
| held for 240 VBlanks | 20 |

A key is tapped for two to six VBlanks, so on a keyboard a step takes two or three presses,
and with the flip on, up on the key goes down in the menu. In flight a tap shorter than four
VBlanks falls between two samples at some phases of the divider and is lost. The port matches
the original in all of this with the assist off (`tests/test_assist.py` repeats the table). The
rank menu (`menu_input`) polls every VBlank, reads the hardware without the flip and waits for
the release, so it already behaves as a keyboard player expects and is left alone.

### What the assist does

**The weapon menu's push.** The menu has the stick while `weapon_menu_up` (`0x025364`) is set
and `0x0253BC` clear, which is what `weapon_menu` tests, the mission coroutine is running and
`ingame_keys` is not inside a dialog or a fade of its own. The byte outlives a mission left
from the hold by a restart, and it is set by the campaign reset before the first mission; the
two further conditions keep the rank menu and the load dialog opened from the hold in
possession of their cursor keys. While the menu has the stick:

1. A press of forward or back starts a push of that direction for exactly twelve VBlanks,
   which is three samples at any phase of the divider: one step and the two pause counts. The
   physical vertical bits do not reach the sample meanwhile.
2. A press made while a push runs is remembered with its direction, at most two, and each
   starts one more push when the current one ends, so quick taps are one step each at the
   menu's own rate. With none remembered and the key still down when a push ends, the next
   push starts at once, which is the original's repeat of one step every three ticks.
3. A press in the menu is never lost. The menu is live when the tick that takes the next
   sample runs it, which is when `0x026D3E` less the bytes already waiting in the queue is at
   most 1. In the first 15 ticks after every opening it is not, and a press made then is
   remembered in the same queue, at most two; its push starts on the VBlank the menu becomes
   live. A key held through the window therefore steps once when the menu becomes live and
   then repeats. No push runs while the menu is not live.
4. A key already held when the menu opens does nothing until it is pressed again.
5. The push is not flipped: up on the key is up in the menu, `weapon_type` decreasing. The
   sample carries `WOF_RAW_UNFLIPPED` beside it, and `read_joy_bits` skips the flip for it.
6. The push ends the moment the menu loses the stick, and on a sample that carries the button
   (a tap or hold latch set) to a live menu, which gets the stick as it is: `weapon_menu`
   tests the button before it steps, so the push could not step on that tick, and that tick's
   player update already rides the lift. No synthetic bit reaches the lift or the deck. In
   the window the tick does not run the menu, so the button ends nothing there and the
   remembered presses stay.
7. `wof_port_key` swallows `0x4C` and `0x4D`, because they reach the menu a second time
   through `last_key`.

**The never-lost tap.** Everywhere else, a direction that goes down arms itself; the next
sample carries it whether it is still down or not, and disarms it. A press therefore gives one
tick of stick for every sample it covers and one where it covers none: a tap shorter than four
VBlanks is exactly one tick, never zero and never more than the original gives a push of that
length. A plain OR of every VBlank since the last sample would give a two- or three-VBlank tap
that straddles a sample two ticks. A new press clears an armed tap of the opposite end, and a
sample never carries both ends of an axis: the end held now wins. In the weapon menu the
sideways bits are armed the same way.

### Where it hooks, and what it leaves alone

`wof_vblank` calls `wof_assist_vblank` on every VBlank that is not paused, after
`vblank_every_frame` and before the divider, and around `read_joystick` it hands the sample
`wof_assist_sample` of the controller, restoring `wof_s.raw` right after. So only the sample
sees the assist: the front end's pollers (`wof_poll_joy_dir8`, `wof_poll_fire`) and the button's
latches see the controller as it is. The other two places are the flip in `read_joy_bits` and
the swallow in `wof_port_key`; each is one marked condition. The assist's state lives in the
core's state beside the flip preference (`WOF_STATE_VERSION` 6), so save states stay exact;
nothing of it is a registered global, and it never writes one.

Nothing in the tick changes. Run with the same raw schedule with the assist off and on and
compared after every tick, the deck script is identical in every registered field; on the
select script the sample itself differs on eight ticks, all while the menu is up (the input
byte, `tick_input` and the queue slot), and otherwise only what the chosen weapon writes:
`weapon_type`, `weapon_count`, `weapon_menu_wait`, the gauge's two drums, the weapon and the
count in both views' dashboard caches, and the clip rectangle a redraw of the gauge leaves
behind. The lift, the roll and the climb that follow are the same to the byte.

### What is fragile

- The push is twelve VBlanks because the original samples every fourth VBlank and a step
  costs three input ticks. Any three input ticks in a row contain exactly one step, whatever
  `weapon_menu_wait` stands at, which is why a push is one step also right after the menu
  opens with 1 there. A queue that dropped a sample of a push (more than six waiting, which
  only a long stall of the passes can cause) would break that.
- The window's end is predicted at every VBlank from `0x026D3E` and the queue's count. A
  queue that dropped a byte in a long stall of the passes would put it one tick early for
  the push that starts there.
- The swallow cannot be told from the push in steady play: the push covers every tick on which
  a cursor code's `last_key` is read, so a tap with its code steps once with or without the
  swallow. What the swallow stops is a key held when the menu opens, whose repeated codes would
  step the menu upward through `last_key` (the test's negative control).

## What M5 must know

- The object records' walk (`0x010A72`) leaves a record of kind 8 alone and stands in for
  every other kind (`0x010AB6`): the weapons in flight start there, and `object_spawn`'s
  second entry at `0x01088E` launches them.
- The button in the air (`0x01B5B0`) drops the other weapon on a tap (`0x01B5E2`, the
  stand-in) and sets `0x02536A` while held in level flight with rounds, which the guns'
  splashes (`0x0119C4`) and the muzzle flash in `draw_player` (`0x010642`) stand in for.
- A crash on land leaves the target damage to `0x0146C6` (the stand-in at `0x01BBF4`), and
  a splash on a record of low bits 2 stands in (`0x0152D8`).
- `ground_height` is held to the original for every record of five maps, enemy ships
  included; the ship heights read `+0x0E` and `+0x14` of the ship records and the swell.

## Facts the other notes share

- The player's record is `0x1E` bytes, and the 160 words behind it from `0x025096` are the
  ships' blocks of deck planes (`re/notes/objects.md`, "The player's record").
- The order of the ship records: destroyer, battleship, cruise ship, Japanese carrier, the
  player's carrier (`re/notes/map.md`, the first walk).
- `choose_night` runs only between two missions of a campaign, and the ticker's messages are
  formatted by the tick into two BSS buffers (`re/notes/display.md`).

## Appendix: the reach map

Entries per routine, window and phase, for the scripts of both parts, the night mission,
and the 21 key runs of `tests/runs/` summed as `keys`, as
`.venv/bin/python tools/reach_observe.py --part2 --blocks --setups --json REACH.json`
records them (observed).

### The head of the outer loop, before the rank selection

| Routine | Address | `deck` | `flight` | `climb` | `lost` | `gameover` | `night` | `select` | `turns` | `landing` | `island` | `fuel` | `keys` |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| `free_mission_assets` | `011234` | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 23 |
| `mem_free_var` | `0124e0` | 16 | 16 | 16 | 16 | 16 | 16 | 16 | 16 | 16 | 16 | 16 | 368 |
| `shapes_free` | `012502` | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 23 |
| `free_map` | `012bbe` | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 23 |
| `sub_01346c` | `01346c` | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 23 |
| `sub_0134a4` | `0134a4` | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 23 |
| `sub_0134ae` | `0134ae` | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 23 |
| `campaign_reset` | `013562` | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 23 |
| `mission_reset_tables` | `0135a8` | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 23 |
| `player_lost_restart` | `0135d8` | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 23 |
| `player_restart_state` | `013684` | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 23 |
| `sub_013756` | `013756` | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 23 |
| `shape_mirror_x` | `015b58` | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 42 |
| `aircraft_frame` | `01abde` | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 23 |
| `deck_span` | `01b7bc` | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 23 |
| `player_reset` | `01b7ec` | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 23 |
| `sub_01b9bc` | `01b9bc` | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 23 |
| `rand_mod` | `01cac8` | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 23 |
| `sub_01cb30` | `01cb30` | 4 | 4 | 4 | 4 | 4 | 4 | 4 | 4 | 4 | 4 | 4 | 92 |
| `aircraft_clear` | `01e608` | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 23 |
| `weapon_gauge_reset` | `01edbc` | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 23 |
| `lives_gauge_reset` | `01edea` | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 23 |
| `rand_beam` | `0203be` | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 23 |
| `shape_find_c` | `0204f4` | 4 | 4 | 4 | 4 | 4 | 4 | 4 | 4 | 4 | 4 | 4 | 92 |
| `shape_find` | `020560` | 4 | 4 | 4 | 4 | 4 | 4 | 4 | 4 | 4 | 4 | 4 | 92 |

### After the rank selection, before the briefing

| Routine | Address | `deck` | `flight` | `climb` | `lost` | `gameover` | `night` | `select` | `turns` | `landing` | `island` | `fuel` | `keys` |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| `sub_0129c8` | `0129c8` | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 22 |
| `map_load` | `012adc` | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 22 |
| `airfields_scan` | `012c84` | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 22 |
| `map_scan` | `012d5a` | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 22 |
| `sub_0131c8` | `0131c8` | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 44 |
| `sub_013216` | `013216` | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 44 |
| `airfields_clear` | `013554` | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 22 |
| `mem_alloc_asm` | `0158ec` | 5 | 5 | 5 | 5 | 5 | 5 | 5 | 5 | 5 | 5 | 5 | 110 |
| `shapes_load` | `015bc6` | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 22 |
| `shapes_resolve` | `015c5c` | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 22 |
| `load_file_public_asm` | `015d3e` | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 22 |
| `load_file_chip_asm` | `015d50` | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 22 |
| `load_dash_assets` | `01653c` | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 22 |
| `sub_0165c4` | `0165c4` | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 22 |
| `load_file_public` | `01feb4` | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 22 |
| `load_file_chip` | `01feca` | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 22 |
| `load_file` | `01ff16` | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 44 |
| `shape_find` | `020560` | 117 | 117 | 117 | 117 | 117 | 117 | 117 | 117 | 117 | 117 | 117 | 2574 |
| `mem_alloc` | `020848` | 7 | 7 | 7 | 7 | 7 | 7 | 7 | 7 | 7 | 7 | 7 | 154 |
| `sub_020874` | `020874` | 9 | 9 | 9 | 9 | 9 | 9 | 9 | 9 | 9 | 9 | 9 | 198 |
| `mem_free` | `02090a` | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 44 |
| `os_dos_close` | `022aae` | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 44 |
| `sub_022ab2` | `022ab2` | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 44 |
| `os_dos_examine` | `022ada` | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 44 |
| `os_dos_lock` | `022b1a` | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 44 |
| `os_dos_open` | `022b2c` | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 44 |
| `sub_022b30` | `022b30` | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 44 |
| `os_dos_read` | `022b3e` | 4 | 4 | 4 | 4 | 4 | 4 | 4 | 4 | 4 | 4 | 4 | 88 |
| `os_dos_unlock` | `022b50` | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 44 |
| `sub_022d36` | `022d36` | 9 | 9 | 9 | 9 | 9 | 9 | 9 | 9 | 9 | 9 | 9 | 198 |
| `sub_022d3a` | `022d3a` | 9 | 9 | 9 | 9 | 9 | 9 | 9 | 9 | 9 | 9 | 9 | 198 |
| `sub_022d86` | `022d86` | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 44 |
| `sub_022d8a` | `022d8a` | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 44 |

### Mission setup, main program: the briefing's end to step S

| Routine | Address | `deck` | `flight` | `climb` | `lost` | `gameover` | `night` | `select` | `turns` | `landing` | `island` | `fuel` | `keys` |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| `input_queue_clear` | `01174a` | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 22 |
| `sub_011f76` | `011f76` | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 22 |
| `load_ship_shapes` | `013252` | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 22 |
| `sounds_load` | `013368` | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 22 |
| `mission_reset_tables` | `0135a8` | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 22 |
| `player_lost_restart` | `0135d8` | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 22 |
| `player_restart_state` | `013684` | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 44 |
| `sub_013756` | `013756` | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 44 |
| `build_master_lists` | `01535a` | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 22 |
| `file_length` | `015b1a` | 8 | 8 | 8 | 8 | 8 | 8 | 8 | 8 | 8 | 8 | 8 | 176 |
| `load_file_public_asm` | `015d3e` | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 44 |
| `load_file_chip_asm` | `015d50` | 8 | 8 | 8 | 8 | 8 | 8 | 8 | 8 | 8 | 8 | 8 | 176 |
| `vport_init_bitmap` | `0167f2` | 4 | 4 | 4 | 4 | 4 | 4 | 4 | 4 | 4 | 4 | 4 | 88 |
| `view_layout` | `01692c` | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 44 |
| `ticker_vport_init` | `016bd8` | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 22 |
| `view_set_game` | `016c38` | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 44 |
| `screen_game` | `016cc6` | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 22 |
| `cmap_file_to_table` | `016dd6` | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 44 |
| `cop_add_ticker_ramp` | `0187ba` | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 44 |
| `mission_display_setup` | `018806` | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 22 |
| `cop_reset` | `019958` | 6 | 6 | 6 | 6 | 6 | 6 | 6 | 6 | 6 | 6 | 6 | 132 |
| `cop_move` | `0199bc` | 290 | 290 | 290 | 290 | 290 | 296 | 290 | 290 | 290 | 290 | 290 | 6380 |
| `cop_move_ptr` | `019a08` | 96 | 96 | 96 | 96 | 96 | 96 | 96 | 96 | 96 | 96 | 96 | 2112 |
| `cop_wait` | `019a9c` | 78 | 78 | 78 | 78 | 78 | 78 | 78 | 78 | 78 | 78 | 78 | 1716 |
| `cop_colours` | `019b5a` | 14 | 14 | 14 | 14 | 14 | 14 | 14 | 14 | 14 | 14 | 14 | 308 |
| `cop_vport_colours` | `019c0a` | 14 | 14 | 14 | 14 | 14 | 14 | 14 | 14 | 14 | 14 | 14 | 308 |
| `cop_vport_split` | `019c80` | 4 | 4 | 4 | 4 | 4 | 4 | 4 | 4 | 4 | 4 | 4 | 88 |
| `cop_vport_planes` | `019d18` | 14 | 14 | 14 | 14 | 14 | 14 | 14 | 14 | 14 | 14 | 14 | 308 |
| `cop_sprites_off` | `01a06c` | 6 | 6 | 6 | 6 | 6 | 6 | 6 | 6 | 6 | 6 | 6 | 132 |
| `view_build_copper` | `01a0d4` | 6 | 6 | 6 | 6 | 6 | 6 | 6 | 6 | 6 | 6 | 6 | 132 |
| `iff_cmap_to_table` | `01a1f6` | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 22 |
| `iff_next_chunk` | `01a336` | 8 | 8 | 8 | 8 | 8 | 8 | 8 | 8 | 8 | 8 | 8 | 176 |
| `iff_body_to_vport` | `01a362` | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 22 |
| `iff_parse_ilbm` | `01a452` | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 22 |
| `iff_to_vport` | `01a548` | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 22 |
| `view_poke_colours1` | `01a60e` | 3 | 3 | 3 | 3 | 3 | 3 | 3 | 3 | 3 | 3 | 3 | 66 |
| `view_poke_colours2` | `01a6ac` | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 22 |
| `vport_clear_planes` | `01a74c` | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 22 |
| `view_copy_bitmaps` | `01a834` | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 22 |
| `view_copy_colours` | `01a8c4` | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 22 |
| `view_copy` | `01a9ca` | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 22 |
| `cop_show_wait` | `01a9fc` | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 44 |
| `cop_install` | `01aa0e` | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 44 |
| `wait_vblank` | `01aa3e` | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 44 |
| `aircraft_frame` | `01abde` | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 44 |
| `deck_span` | `01b7bc` | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 44 |
| `player_reset` | `01b7ec` | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 44 |
| `sub_01b9bc` | `01b9bc` | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 44 |
| `rand_mod` | `01cac8` | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 44 |
| `sub_01cb30` | `01cb30` | 288 | 288 | 288 | 288 | 288 | 288 | 288 | 288 | 288 | 288 | 288 | 6336 |
| `enemy_frames` | `01d1ea` | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 22 |
| `dash_cache_invalidate` | `01ed7a` | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 44 |
| `dashboard_invalidate` | `01edaa` | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 22 |
| `weapon_gauge_reset` | `01edbc` | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 44 |
| `load_file_public` | `01feb4` | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 44 |
| `load_file_chip` | `01feca` | 8 | 8 | 8 | 8 | 8 | 8 | 8 | 8 | 8 | 8 | 8 | 176 |
| `rpck_unpack` | `01fee0` | 1 | 1 | 1 | 1 | 1 | 0 | 1 | 1 | 1 | 1 | 1 | 22 |
| `load_file` | `01ff16` | 10 | 10 | 10 | 10 | 10 | 10 | 10 | 10 | 10 | 10 | 10 | 220 |
| `rand_beam` | `0203be` | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 44 |
| `byterun1_row` | `0203e8` | 148 | 148 | 148 | 148 | 148 | 148 | 148 | 148 | 148 | 148 | 148 | 3256 |
| `shape_find_c` | `0204f4` | 288 | 288 | 288 | 288 | 288 | 288 | 288 | 288 | 288 | 288 | 288 | 6336 |
| `shape_find` | `020560` | 288 | 288 | 288 | 288 | 288 | 288 | 288 | 288 | 288 | 288 | 288 | 6336 |
| `mem_alloc` | `020848` | 11 | 11 | 11 | 11 | 11 | 10 | 11 | 11 | 11 | 11 | 11 | 242 |
| `sub_020874` | `020874` | 21 | 21 | 21 | 21 | 21 | 20 | 21 | 21 | 21 | 21 | 21 | 462 |
| `mem_free` | `02090a` | 14 | 14 | 14 | 14 | 14 | 13 | 14 | 14 | 14 | 14 | 14 | 308 |
| `sub_0223cc` | `0223cc` | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 22 |
| `sub_022424` | `022424` | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 22 |
| `os_dos_close` | `022aae` | 10 | 10 | 10 | 10 | 10 | 10 | 10 | 10 | 10 | 10 | 10 | 220 |
| `sub_022ab2` | `022ab2` | 10 | 10 | 10 | 10 | 10 | 10 | 10 | 10 | 10 | 10 | 10 | 220 |
| `os_dos_examine` | `022ada` | 10 | 10 | 10 | 10 | 10 | 10 | 10 | 10 | 10 | 10 | 10 | 220 |
| `os_dos_lock` | `022b1a` | 10 | 10 | 10 | 10 | 10 | 10 | 10 | 10 | 10 | 10 | 10 | 220 |
| `os_dos_open` | `022b2c` | 10 | 10 | 10 | 10 | 10 | 10 | 10 | 10 | 10 | 10 | 10 | 220 |
| `sub_022b30` | `022b30` | 10 | 10 | 10 | 10 | 10 | 10 | 10 | 10 | 10 | 10 | 10 | 220 |
| `os_dos_read` | `022b3e` | 20 | 20 | 20 | 20 | 20 | 20 | 20 | 20 | 20 | 20 | 20 | 440 |
| `os_dos_unlock` | `022b50` | 10 | 10 | 10 | 10 | 10 | 10 | 10 | 10 | 10 | 10 | 10 | 220 |
| `sub_022d36` | `022d36` | 21 | 21 | 21 | 21 | 21 | 20 | 21 | 21 | 21 | 21 | 21 | 462 |
| `sub_022d3a` | `022d3a` | 21 | 21 | 21 | 21 | 21 | 20 | 21 | 21 | 21 | 21 | 21 | 462 |
| `sub_022d86` | `022d86` | 14 | 14 | 14 | 14 | 14 | 13 | 14 | 14 | 14 | 14 | 14 | 308 |
| `sub_022d8a` | `022d8a` | 14 | 14 | 14 | 14 | 14 | 13 | 14 | 14 | 14 | 14 | 14 | 308 |
| `gfx_BltBitMap` | `022e0c` | 3 | 3 | 3 | 3 | 3 | 3 | 3 | 3 | 3 | 3 | 3 | 66 |
| `gfx_BltClear` | `022e2e` | 7 | 7 | 7 | 7 | 7 | 7 | 7 | 7 | 7 | 7 | 7 | 154 |
| `gfx_InitBitMap` | `022e5a` | 5 | 5 | 5 | 5 | 5 | 5 | 5 | 5 | 5 | 5 | 5 | 110 |
| `gfx_InitRastPort` | `022e6c` | 5 | 5 | 5 | 5 | 5 | 5 | 5 | 5 | 5 | 5 | 5 | 110 |

### Mission setup, the tick main runs itself

| Routine | Address | `deck` | `flight` | `climb` | `lost` | `gameover` | `night` | `select` | `turns` | `landing` | `island` | `fuel` | `keys` |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| `objects_step` | `010a72` | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 22 |
| `shot_origin` | `011274` | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 22 |
| `logic_tick` | `011386` | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 22 |
| `ship_launches` | `011510` | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 22 |
| `airfields_step` | `011622` | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 22 |
| `input_queue_pop` | `011714` | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 22 |
| `gun_splashes` | `0119bc` | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 22 |
| `engine_smoke` | `011bfc` | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 22 |
| `balloons_step` | `011c5e` | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 22 |
| `ships_sinking` | `011cae` | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 22 |
| `target_timers` | `011de4` | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 22 |
| `sound_channels` | `012066` | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 22 |
| `engine_sound` | `012132` | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 22 |
| `sub_0122ce` | `0122ce` | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 22 |
| `button` | `01b5b0` | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 22 |
| `guns` | `01b682` | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 22 |
| `enemy_countdown_step` | `01bc02` | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 22 |
| `player_update` | `01c660` | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 22 |
| `enemy_aircraft_step` | `01e7d6` | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 22 |
| `sub_01ea28` | `01ea28` | 3 | 3 | 3 | 3 | 3 | 3 | 3 | 3 | 3 | 3 | 3 | 66 |
| `sub_01eac0` | `01eac0` | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 44 |
| `sub_01eb2e` | `01eb2e` | 3 | 3 | 3 | 3 | 3 | 3 | 3 | 3 | 3 | 3 | 3 | 66 |
| `os_disable` | `022d48` | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 22 |
| `os_enable` | `022d66` | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 22 |

### Mission setup, VBlank servers

| Routine | Address | `deck` | `flight` | `climb` | `lost` | `gameover` | `night` | `select` | `turns` | `landing` | `island` | `fuel` | `keys` |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| `vblank_server` | `011754` | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 44 |
| `vblank_every_frame` | `01c9ca` | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 44 |
| `soundfx_vblank` | `01ec64` | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 44 |
| `poll_fire` | `02044c` | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 44 |
| `read_fire_button` | `02046a` | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 44 |

### A pass during a mission: `frame_update`'s tree (phase F)

| Routine | Address | `deck` | `flight` | `climb` | `lost` | `gameover` | `night` | `select` | `turns` | `landing` | `island` | `fuel` | `keys` |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| `frame_update` | `010228` | 934 | 1134 | 1324 | 1224 | 2682 | 1134 | 818 | 1772 | 1532 | 1918 | 11545 | 1979 |
| `flip_buffers` | `01030c` | 934 | 1134 | 1324 | 1224 | 2682 | 1134 | 818 | 1772 | 1532 | 1918 | 11545 | 1979 |
| `weapon_marker` | `010344` | 934 | 1134 | 1324 | 1224 | 2682 | 1134 | 818 | 1772 | 1532 | 1918 | 11545 | 1979 |
| `draw_player` | `0103a6` | 934 | 1134 | 1324 | 1224 | 2682 | 1134 | 818 | 1772 | 1532 | 1918 | 11545 | 1979 |
| `draw_objects` | `0106be` | 934 | 1134 | 1324 | 1224 | 2682 | 1134 | 818 | 1772 | 1532 | 1918 | 11545 | 1979 |
| `object_draw` | `010702` | 0 | 0 | 105 | 112 | 266 | 0 | 0 | 0 | 0 | 0 | 112 | 0 |
| `draw_enemy_aircraft` | `010da6` | 934 | 1134 | 1324 | 1224 | 2682 | 1134 | 818 | 1772 | 1532 | 1918 | 11545 | 1979 |
| `smoke_draw` | `010ee0` | 934 | 1134 | 1324 | 1224 | 2682 | 1134 | 818 | 1772 | 1532 | 1918 | 11545 | 1979 |
| `snapshot_for_draw` | `010f88` | 934 | 1134 | 1324 | 1224 | 2682 | 1134 | 818 | 1772 | 1532 | 1918 | 11545 | 1979 |
| `draw_game_over` | `0110c2` | 934 | 1134 | 1324 | 1224 | 2682 | 1134 | 818 | 1772 | 1532 | 1918 | 11545 | 1979 |
| `draw_world` | `013772` | 934 | 1134 | 1324 | 1224 | 2682 | 1134 | 818 | 1772 | 1532 | 1918 | 11545 | 1979 |
| `ship_planes` | `01391e` | 934 | 1134 | 1324 | 1224 | 2682 | 1134 | 818 | 1772 | 1532 | 1918 | 11545 | 1979 |
| `airfields_draw` | `013a18` | 934 | 1134 | 1324 | 1224 | 2682 | 1134 | 818 | 1772 | 1532 | 1918 | 11545 | 1979 |
| `deck_aircraft` | `013abc` | 934 | 1134 | 1324 | 1224 | 2682 | 1134 | 818 | 1772 | 1532 | 1918 | 11545 | 1979 |
| `record_extras` | `013b1c` | 68182 | 71197 | 75576 | 84982 | 185308 | 71197 | 79925 | 394242 | 86883 | 726837 | 1222209 | 144860 |
| `targets_3_draw` | `013d78` | 934 | 1134 | 1324 | 1224 | 2682 | 1134 | 818 | 1772 | 1532 | 1918 | 11545 | 1979 |
| `targets_f_draw` | `013de8` | 934 | 1134 | 1324 | 1224 | 2682 | 1134 | 818 | 1772 | 1532 | 1918 | 11545 | 1979 |
| `ocean` | `013e6c` | 934 | 1134 | 1324 | 1224 | 2682 | 1134 | 818 | 1772 | 1532 | 1918 | 11545 | 1979 |
| `soldiers_draw` | `013eee` | 934 | 1134 | 1324 | 1224 | 2682 | 1134 | 818 | 1772 | 1532 | 1918 | 11545 | 1979 |
| `lift_aircraft` | `01409c` | 934 | 1134 | 1324 | 1224 | 2682 | 1134 | 818 | 1772 | 1532 | 1918 | 11545 | 1979 |
| `islands_draw` | `0140e8` | 934 | 1134 | 1324 | 1224 | 2682 | 1134 | 818 | 1772 | 1532 | 1918 | 11545 | 1979 |
| `map_window` | `01417e` | 934 | 1134 | 1324 | 1224 | 2682 | 1134 | 818 | 1772 | 1532 | 1918 | 11545 | 1979 |
| `window_height` | `0141b4` | 934 | 423 | 786 | 1224 | 2682 | 423 | 583 | 643 | 1532 | 423 | 799 | 1979 |
| `window_strip` | `014206` | 934 | 423 | 786 | 1224 | 2682 | 423 | 583 | 643 | 1532 | 423 | 799 | 1979 |
| `window_ship` | `014430` | 934 | 423 | 786 | 1224 | 2682 | 423 | 583 | 643 | 1532 | 423 | 799 | 1979 |
| `window_background` | `014564` | 934 | 1134 | 1324 | 1224 | 2682 | 1134 | 818 | 1772 | 1532 | 1918 | 11545 | 1979 |
| `window_shape` | `0145a6` | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 162 | 902 | 0 | 0 | 0 |
| `ship_at_offset` | `014a4e` | 8406 | 5141 | 5446 | 9194 | 19612 | 5141 | 6480 | 14099 | 8989 | 11343 | 58081 | 17811 |
| `ship_at_span` | `014a52` | 9340 | 5454 | 5764 | 10086 | 21486 | 5454 | 6953 | 14534 | 10660 | 11656 | 58404 | 19790 |
| `ship_guns_draw` | `014c3e` | 934 | 1134 | 1324 | 1224 | 2682 | 1134 | 818 | 1772 | 1532 | 1918 | 11545 | 1979 |
| `target_frame` | `014d50` | 1868 | 2268 | 2648 | 2448 | 5364 | 2268 | 1636 | 3544 | 3064 | 3836 | 23090 | 4744 |
| `target_range_frame` | `014db8` | 0 | 228 | 304 | 40 | 120 | 228 | 228 | 668 | 1070 | 228 | 228 | 0 |
| `ride_on_ship` | `014eac` | 8406 | 5141 | 5446 | 9194 | 19612 | 5141 | 6480 | 14099 | 8989 | 11343 | 58081 | 17811 |
| `target_fire` | `014f5c` | 0 | 698 | 524 | 0 | 0 | 698 | 220 | 1121 | 0 | 1483 | 10708 | 0 |
| `target_refill` | `014fee` | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 6 |
| `nearest_barracks` | `015034` | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 6 |
| `format_to` | `015078` | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 46 |
| `format_putch` | `015090` | 16 | 16 | 16 | 16 | 16 | 16 | 16 | 16 | 16 | 16 | 16 | 368 |
| `flip_view` | `0150b0` | 934 | 1134 | 1324 | 1224 | 2682 | 1134 | 818 | 1772 | 1532 | 1918 | 11545 | 1979 |
| `draw_world_shape` | `015174` | 3736 | 5618 | 6779 | 5115 | 9647 | 5618 | 3876 | 8813 | 7537 | 9623 | 57916 | 25771 |
| `sub_01520c` | `01520c` | 934 | 1134 | 1324 | 1224 | 2682 | 1134 | 818 | 1772 | 1532 | 1918 | 11545 | 1979 |
| `clip_playfield` | `01524a` | 2802 | 2691 | 3434 | 3672 | 8344 | 2691 | 2219 | 4187 | 4596 | 4259 | 23889 | 5937 |
| `clip_dash_window` | `01525c` | 934 | 1134 | 1324 | 1224 | 2682 | 1134 | 818 | 1772 | 1532 | 1918 | 11545 | 1979 |
| `clip_to_waterline` | `01526e` | 934 | 1518 | 2066 | 1830 | 4312 | 1518 | 1202 | 2376 | 2941 | 2302 | 12295 | 2643 |
| `splashes_draw` | `0152f8` | 934 | 1134 | 1324 | 1224 | 2682 | 1134 | 818 | 1772 | 1532 | 1918 | 11545 | 1979 |
| `smoke_claim` | `015460` | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 2 | 0 | 20 |
| `smoke_at_player` | `0154e0` | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 2 | 0 | 0 |
| `balloons_draw` | `01557c` | 934 | 1134 | 1324 | 1224 | 2682 | 1134 | 818 | 1772 | 1532 | 1918 | 11545 | 1979 |
| `view_show` | `016f20` | 934 | 1134 | 1324 | 1224 | 2682 | 1134 | 818 | 1772 | 1532 | 1918 | 11545 | 1979 |
| `cop_set_split_line` | `01876e` | 934 | 1134 | 1324 | 1224 | 2682 | 1134 | 818 | 1772 | 1532 | 1918 | 11545 | 1979 |
| `cop_wait` | `019a9c` | 934 | 1134 | 1324 | 1224 | 2682 | 1134 | 818 | 1772 | 1532 | 1918 | 11545 | 1979 |
| `cop_install` | `01aa0e` | 934 | 1134 | 1324 | 1224 | 2682 | 1134 | 818 | 1772 | 1532 | 1918 | 11545 | 1979 |
| `wait_vblank` | `01aa3e` | 934 | 1134 | 1324 | 1224 | 2682 | 1134 | 818 | 1772 | 1532 | 1918 | 11545 | 1979 |
| `record_on_ship` | `01cb34` | 0 | 4 | 4 | 4 | 12 | 4 | 4 | 4 | 14 | 4 | 4 | 0 |
| `ship_of_record` | `01cbf2` | 0 | 4 | 4 | 4 | 12 | 4 | 4 | 4 | 14 | 4 | 4 | 0 |
| `draw_dashboard` | `01ee16` | 934 | 1134 | 1324 | 1224 | 2682 | 1134 | 818 | 1772 | 1532 | 1918 | 11545 | 1979 |
| `kill_icons` | `01f200` | 4 | 4 | 4 | 4 | 4 | 4 | 4 | 4 | 4 | 4 | 4 | 92 |
| `enemy_arrows` | `01f21a` | 934 | 1134 | 1324 | 1224 | 2682 | 1134 | 818 | 1772 | 1532 | 1918 | 11545 | 1979 |
| `draw_score` | `01f26a` | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 46 |
| `dash_digit` | `01f2b0` | 18 | 18 | 18 | 18 | 18 | 18 | 18 | 18 | 18 | 18 | 18 | 414 |
| `clip_dashboard` | `01f2dc` | 1868 | 2268 | 2648 | 2448 | 5364 | 2268 | 1636 | 3544 | 3064 | 3836 | 23090 | 3958 |
| `rand_beam` | `0203be` | 0 | 1422 | 1076 | 0 | 0 | 1422 | 470 | 2258 | 0 | 3178 | 21836 | 40 |
| `shape_find` | `020560` | 0 | 0 | 0 | 0 | 298 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| `blit_clip_setup` | `0209bc` | 24322 | 12372 | 15396 | 27217 | 57970 | 12372 | 16082 | 27649 | 31199 | 62454 | 93216 | 51279 |
| `shape_blit` | `020b0c` | 24322 | 12372 | 15396 | 27217 | 57970 | 12372 | 16082 | 27649 | 31199 | 62454 | 93216 | 51279 |
| `shape_draw` | `020ce2` | 22434 | 12274 | 15288 | 25961 | 55846 | 12274 | 15654 | 27551 | 30931 | 62356 | 93098 | 48189 |
| `rect_fill` | `021010` | 3736 | 5247 | 5834 | 4896 | 10728 | 5247 | 3507 | 8217 | 6128 | 9167 | 56926 | 8702 |
| `draw_set_target` | `02124a` | 2802 | 3402 | 3972 | 3672 | 8344 | 3402 | 2454 | 5316 | 4596 | 5754 | 34635 | 5937 |
| `clip_set` | `02129c` | 6538 | 7611 | 9472 | 9174 | 20702 | 7611 | 5875 | 11879 | 12133 | 12315 | 70819 | 14517 |
| `blit_begin` | `0212ce` | 7472 | 7977 | 9312 | 9186 | 20124 | 7977 | 5925 | 12443 | 10847 | 13465 | 80864 | 15168 |
| `blit_end` | `0212d4` | 7472 | 7977 | 9312 | 9186 | 20124 | 7977 | 5925 | 12443 | 10847 | 13465 | 80864 | 15168 |
| `line_draw` | `021318` | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 26 | 0 | 0 | 0 |
| `sub_022e40` | `022e40` | 7472 | 7977 | 9312 | 9186 | 20124 | 7977 | 5925 | 12443 | 10847 | 13465 | 80864 | 15168 |
| `sub_022e8a` | `022e8a` | 7472 | 7977 | 9312 | 9186 | 20124 | 7977 | 5925 | 12443 | 10847 | 13465 | 80864 | 15168 |

### A VBlank during a mission (phase V)

| Routine | Address | `deck` | `flight` | `climb` | `lost` | `gameover` | `night` | `select` | `turns` | `landing` | `island` | `fuel` | `keys` |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| `input_queue_pop` | `011714` | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 230 |
| `vblank_server` | `011754` | 1869 | 2269 | 2647 | 2447 | 5359 | 2269 | 1637 | 3545 | 3065 | 3837 | 23089 | 5975 |
| `read_joy_bits` | `01520e` | 468 | 568 | 662 | 612 | 1341 | 568 | 410 | 887 | 767 | 960 | 5773 | 1248 |
| `vblank_every_frame` | `01c9ca` | 1869 | 2269 | 2647 | 2447 | 5359 | 2269 | 1637 | 3545 | 3065 | 3837 | 23089 | 4950 |
| `read_joystick` | `01ca32` | 468 | 568 | 662 | 612 | 1341 | 568 | 410 | 887 | 767 | 960 | 5773 | 1248 |
| `read_joy_dispatch` | `01cb20` | 468 | 568 | 662 | 612 | 1341 | 568 | 410 | 887 | 767 | 960 | 5773 | 1248 |
| `soundfx_vblank` | `01ec64` | 1869 | 2269 | 2647 | 2447 | 5359 | 2269 | 1637 | 3545 | 3065 | 3837 | 23089 | 5975 |
| `poll_fire` | `02044c` | 1869 | 2269 | 2647 | 2447 | 5359 | 2269 | 1637 | 3545 | 3065 | 3837 | 23089 | 4950 |
| `read_fire_button` | `02046a` | 1869 | 2269 | 2647 | 2447 | 5359 | 2269 | 1637 | 3545 | 3065 | 3837 | 23089 | 4950 |
| `input_handler` | `02075a` | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 34 |
| `os_disable` | `022d48` | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 230 |
| `os_enable` | `022d66` | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 230 |

### The inner loop beside `frame_update` during a mission (phase M)

| Routine | Address | `deck` | `flight` | `climb` | `lost` | `gameover` | `night` | `select` | `turns` | `landing` | `island` | `fuel` | `keys` |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| `sub_011256` | `011256` | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 2 |
| `run_queued_ticks` | `0114d8` | 934 | 1134 | 1324 | 1224 | 2682 | 1134 | 818 | 1772 | 1532 | 1918 | 11545 | 1979 |
| `input_queue_clear` | `01174a` | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 |
| `sound_slots_clear` | `011f4e` | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 11 |
| `sub_011f76` | `011f76` | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 |
| `sound_channels` | `012066` | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 11 |
| `sub_012470` | `012470` | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 |
| `mem_free_var` | `0124e0` | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 50 |
| `shapes_free` | `012502` | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 4 |
| `free_map` | `012bbe` | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 |
| `load_ship_shapes` | `013252` | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 |
| `sounds_load` | `013368` | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 |
| `sub_01344e` | `01344e` | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 |
| `sub_01346c` | `01346c` | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 4 |
| `sub_0134a4` | `0134a4` | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 7 |
| `sub_0134ae` | `0134ae` | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 4 |
| `build_master_lists` | `01535a` | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 |
| `mem_alloc_asm` | `0158ec` | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 |
| `text_draw` | `015910` | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 4 |
| `text_width` | `01591e` | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 4 |
| `text_render` | `015956` | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 4 |
| `file_length` | `015b1a` | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 8 |
| `shapes_load` | `015bc6` | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 |
| `shapes_resolve` | `015c5c` | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 |
| `load_file_public_asm` | `015d3e` | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 3 |
| `load_file_chip_asm` | `015d50` | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 9 |
| `sub_015d62` | `015d62` | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 |
| `sub_015d7c` | `015d7c` | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 7 |
| `save_game_read` | `015e1a` | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 |
| `sub_015ec2` | `015ec2` | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 |
| `text_caret` | `016032` | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 |
| `text_input` | `016086` | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 |
| `load_dash_assets` | `01653c` | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 |
| `path_sanitise` | `016592` | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 |
| `vport_init_bitmap` | `0167f2` | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 9 |
| `view_layout` | `01692c` | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 7 |
| `screen_dialog` | `0169a4` | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 3 |
| `screen_hires3` | `016b04` | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 |
| `ticker_clear` | `016bbc` | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 3 |
| `ticker_vport_init` | `016bd8` | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 |
| `view_set_game` | `016c38` | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 2 |
| `screen_game` | `016cc6` | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 |
| `cmap_file_to_table` | `016dd6` | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 2 |
| `view_show` | `016f20` | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 133 |
| `view_show_wait` | `016fc4` | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 5 |
| `colour_lerp` | `016ff6` | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 6656 |
| `fade_to` | `017084` | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 5 |
| `fade_to_pair` | `0171f2` | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 3 |
| `fade_out` | `0173b0` | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 |
| `fade_out_pair` | `0173e6` | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 3 |
| `menu_input` | `018194` | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 2 |
| `wait_input_release` | `018228` | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 |
| `text_draw_c` | `018570` | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 4 |
| `mission_briefing` | `018590` | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 |
| `cop_add_ticker_ramp` | `0187ba` | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 2 |
| `mission_display_setup` | `018806` | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 |
| `dialog_draw_names` | `018958` | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 6 |
| `dialog_file_list` | `018a06` | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 3 |
| `load_save_dialog` | `018b96` | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 3 |
| `cop_reset` | `019958` | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 139 |
| `cop_move` | `0199bc` | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 5374 |
| `cop_move_ptr` | `019a08` | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1946 |
| `cop_wait` | `019a9c` | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 909 |
| `cop_colours` | `019b5a` | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 243 |
| `cop_vport_colours` | `019c0a` | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 243 |
| `cop_vport_split` | `019c80` | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 52 |
| `cop_vport_planes` | `019d18` | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 243 |
| `cop_sprites_off` | `01a06c` | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 139 |
| `view_build_copper` | `01a0d4` | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 139 |
| `iff_cmap_to_table` | `01a1f6` | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 |
| `iff_next_chunk` | `01a336` | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 8 |
| `iff_body_to_vport` | `01a362` | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 |
| `iff_parse_ilbm` | `01a452` | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 |
| `iff_to_vport` | `01a548` | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 |
| `view_poke_colours1` | `01a60e` | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 3 |
| `view_poke_colours2` | `01a6ac` | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 |
| `vport_clear_planes` | `01a74c` | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 |
| `view_copy_bitmaps` | `01a834` | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 |
| `view_copy_colours` | `01a8c4` | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 |
| `view_copy` | `01a9ca` | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 |
| `cop_show_wait` | `01a9fc` | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 6 |
| `cop_install` | `01aa0e` | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 139 |
| `wait_next_vblank` | `01aa32` | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1025 |
| `wait_vblank` | `01aa3e` | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 11 |
| `sub_01cb30` | `01cb30` | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 280 |
| `ingame_keys` | `01ccf6` | 935 | 1135 | 1325 | 1225 | 2682 | 1135 | 819 | 1773 | 1533 | 1919 | 11546 | 3021 |
| `enemy_frames` | `01d1ea` | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 |
| `sub_01eac0` | `01eac0` | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 33 |
| `dash_cache_invalidate` | `01ed7a` | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 2 |
| `dashboard_invalidate` | `01edaa` | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 |
| `load_file_public` | `01feb4` | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 3 |
| `load_file_chip` | `01feca` | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 9 |
| `rpck_unpack` | `01fee0` | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 |
| `load_file` | `01ff16` | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 12 |
| `byterun1_row` | `0203e8` | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 148 |
| `poll_fire` | `02044c` | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 980 |
| `poll_joy_dir8` | `020454` | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 741 |
| `read_fire_button` | `02046a` | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 980 |
| `read_joy_dir8` | `020488` | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 741 |
| `shape_find_c` | `0204f4` | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 281 |
| `shape_find` | `020560` | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 398 |
| `key_to_char` | `020700` | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 33 |
| `key_available` | `0207d8` | 935 | 1135 | 1325 | 1225 | 2682 | 1135 | 819 | 1773 | 1533 | 1919 | 11546 | 4068 |
| `key_get` | `0207e4` | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 34 |
| `mem_alloc` | `020848` | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 22 |
| `sub_020874` | `020874` | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 34 |
| `mem_free` | `02090a` | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 44 |
| `blit_clip_setup` | `0209bc` | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 |
| `shape_blit` | `020b0c` | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 |
| `shape_draw_c` | `020cc4` | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 |
| `shape_draw` | `020ce2` | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 |
| `draw_set_target_c` | `021246` | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 7 |
| `draw_set_target` | `02124a` | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 7 |
| `clip_set_full` | `021280` | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 7 |
| `clip_set` | `02129c` | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 7 |
| `blit_begin` | `0212ce` | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 |
| `blit_end` | `0212d4` | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 |
| `sprintf` | `0215d8` | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 3 |
| `sub_021608` | `021608` | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 3 |
| `sub_021624` | `021624` | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 3 |
| `sub_0216b2` | `0216b2` | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 3 |
| `strcpy` | `021e02` | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 3 |
| `strlen` | `021e12` | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 55 |
| `tolower` | `021e82` | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 63 |
| `bcopy` | `021eca` | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 4 |
| `strcat` | `0222a8` | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 2 |
| `strncpy` | `0222d2` | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 3 |
| `sub_0223cc` | `0223cc` | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 6241 |
| `sub_02240e` | `02240e` | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 3 |
| `sub_02241a` | `02241a` | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 3 |
| `sub_022424` | `022424` | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 6247 |
| `os_dos_close` | `022aae` | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 13 |
| `sub_022ab2` | `022ab2` | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 13 |
| `os_dos_examine` | `022ada` | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 15 |
| `os_dos_ex_next` | `022aec` | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 45 |
| `os_dos_lock` | `022b1a` | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 15 |
| `os_dos_open` | `022b2c` | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 13 |
| `sub_022b30` | `022b30` | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 13 |
| `os_dos_read` | `022b3e` | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 31 |
| `os_dos_unlock` | `022b50` | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 15 |
| `sub_022d36` | `022d36` | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 34 |
| `sub_022d3a` | `022d3a` | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 34 |
| `os_disable` | `022d48` | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 34 |
| `os_enable` | `022d66` | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 34 |
| `sub_022d86` | `022d86` | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 44 |
| `sub_022d8a` | `022d8a` | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 44 |
| `gfx_BltBitMap` | `022e0c` | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 3 |
| `gfx_BltClear` | `022e2e` | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 15 |
| `sub_022e40` | `022e40` | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 |
| `os_gfx_draw` | `022e48` | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 96 |
| `gfx_InitBitMap` | `022e5a` | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 10 |
| `gfx_InitRastPort` | `022e6c` | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 10 |
| `os_gfx_move` | `022e78` | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 79 |
| `sub_022e8a` | `022e8a` | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 |
| `os_gfx_rect_fill` | `022e92` | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 3 |
| `os_gfx_set_apen` | `022ea4` | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 6 |
| `os_gfx_set_bpen` | `022eb4` | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 |
| `os_gfx_set_drmd` | `022ec4` | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 47 |
| `os_gfx_text` | `022ed4` | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 87 |
| `gfx_WaitTOF` | `022eee` | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 982 |
| `os_console_raw_key_convert` | `022f30` | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 33 |

### The tick during a mission (phase T)

| Routine | Address | `deck` | `flight` | `climb` | `lost` | `gameover` | `night` | `select` | `turns` | `landing` | `island` | `fuel` | `keys` |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| `flip_buffers` | `01030c` | 0 | 0 | 1 | 1 | 2 | 0 | 0 | 0 | 0 | 0 | 1 | 0 |
| `object_spawn` | `010820` | 0 | 0 | 15 | 16 | 38 | 0 | 0 | 0 | 0 | 0 | 16 | 0 |
| `objects_step` | `010a72` | 467 | 567 | 667 | 617 | 1351 | 567 | 409 | 886 | 766 | 959 | 5777 | 989 |
| `object_step` | `010aa6` | 0 | 0 | 60 | 64 | 152 | 0 | 0 | 0 | 0 | 0 | 64 | 0 |
| `shot_origin` | `011274` | 467 | 567 | 667 | 617 | 1351 | 567 | 409 | 886 | 766 | 959 | 5777 | 989 |
| `weapon_menu` | `0112b0` | 454 | 554 | 647 | 590 | 1310 | 554 | 396 | 873 | 739 | 946 | 5755 | 703 |
| `logic_tick` | `011386` | 467 | 567 | 667 | 617 | 1351 | 567 | 409 | 886 | 766 | 959 | 5777 | 989 |
| `lift_step` | `011460` | 454 | 554 | 647 | 590 | 1310 | 554 | 396 | 873 | 739 | 946 | 5755 | 703 |
| `ship_launches` | `011510` | 467 | 567 | 667 | 617 | 1351 | 567 | 409 | 886 | 766 | 959 | 5777 | 989 |
| `airfields_step` | `011622` | 467 | 567 | 667 | 617 | 1351 | 567 | 409 | 886 | 766 | 959 | 5777 | 989 |
| `input_queue_pop` | `011714` | 467 | 567 | 667 | 617 | 1351 | 567 | 409 | 886 | 766 | 959 | 5777 | 989 |
| `vblank_server` | `011754` | 0 | 0 | 21 | 21 | 42 | 0 | 0 | 0 | 0 | 0 | 21 | 0 |
| `gun_splashes` | `0119bc` | 467 | 567 | 667 | 617 | 1351 | 567 | 409 | 886 | 766 | 959 | 5777 | 989 |
| `engine_smoke` | `011bfc` | 467 | 567 | 667 | 617 | 1351 | 567 | 409 | 886 | 766 | 959 | 5777 | 989 |
| `balloons_step` | `011c5e` | 467 | 567 | 667 | 617 | 1351 | 567 | 409 | 886 | 766 | 959 | 5777 | 989 |
| `ships_sinking` | `011cae` | 467 | 567 | 667 | 617 | 1351 | 567 | 409 | 886 | 766 | 959 | 5777 | 989 |
| `target_timers` | `011de4` | 467 | 567 | 667 | 617 | 1351 | 567 | 409 | 886 | 766 | 959 | 5777 | 989 |
| `sound_slots_clear` | `011f4e` | 0 | 1 | 1 | 1 | 3 | 1 | 1 | 1 | 3 | 1 | 1 | 1 |
| `sound_channels` | `012066` | 467 | 568 | 668 | 618 | 1354 | 568 | 410 | 887 | 769 | 960 | 5778 | 990 |
| `engine_sound` | `012132` | 467 | 567 | 667 | 617 | 1351 | 567 | 409 | 886 | 766 | 959 | 5777 | 989 |
| `sub_0122ce` | `0122ce` | 467 | 567 | 667 | 617 | 1351 | 567 | 409 | 886 | 766 | 959 | 5777 | 966 |
| `sub_0122f6` | `0122f6` | 0 | 0 | 0 | 1 | 3 | 0 | 0 | 0 | 0 | 0 | 1 | 0 |
| `sub_012306` | `012306` | 0 | 0 | 0 | 1 | 3 | 0 | 0 | 0 | 0 | 0 | 1 | 0 |
| `sub_012324` | `012324` | 0 | 0 | 0 | 1 | 3 | 0 | 0 | 0 | 0 | 0 | 1 | 0 |
| `sub_012354` | `012354` | 0 | 1 | 1 | 1 | 3 | 1 | 1 | 1 | 3 | 1 | 1 | 1 |
| `sub_012380` | `012380` | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 0 | 0 | 0 |
| `next_aircraft` | `0135ce` | 0 | 0 | 1 | 1 | 3 | 0 | 0 | 0 | 0 | 0 | 1 | 0 |
| `player_lost_restart` | `0135d8` | 0 | 0 | 1 | 1 | 3 | 0 | 0 | 0 | 0 | 0 | 1 | 0 |
| `player_restart_state` | `013684` | 0 | 0 | 1 | 1 | 2 | 0 | 0 | 0 | 1 | 0 | 1 | 0 |
| `sub_013756` | `013756` | 0 | 0 | 1 | 1 | 2 | 0 | 0 | 0 | 1 | 0 | 1 | 0 |
| `flip_view` | `0150b0` | 0 | 0 | 1 | 1 | 2 | 0 | 0 | 0 | 0 | 0 | 1 | 0 |
| `map_slot_at` | `0150c8` | 0 | 0 | 22 | 16 | 48 | 0 | 0 | 0 | 0 | 0 | 32 | 0 |
| `sub_01520c` | `01520c` | 0 | 0 | 1 | 1 | 2 | 0 | 0 | 0 | 0 | 0 | 1 | 0 |
| `read_joy_bits` | `01520e` | 0 | 0 | 5 | 5 | 10 | 0 | 0 | 0 | 0 | 0 | 5 | 0 |
| `clip_playfield` | `01524a` | 0 | 0 | 1 | 1 | 2 | 0 | 0 | 0 | 0 | 0 | 1 | 0 |
| `sub_0152ac` | `0152ac` | 0 | 0 | 22 | 16 | 48 | 0 | 0 | 0 | 0 | 0 | 32 | 0 |
| `splash_spawn` | `0152b0` | 0 | 0 | 22 | 16 | 48 | 0 | 0 | 0 | 0 | 0 | 32 | 0 |
| `sub_015710` | `015710` | 0 | 547 | 480 | 145 | 435 | 547 | 309 | 931 | 708 | 1011 | 5538 | 333 |
| `ground_height` | `015714` | 0 | 547 | 480 | 145 | 435 | 547 | 309 | 931 | 708 | 1011 | 5538 | 333 |
| `shape_mirror_x` | `015b58` | 0 | 24 | 26 | 28 | 82 | 24 | 24 | 32 | 60 | 28 | 84 | 0 |
| `view_show` | `016f20` | 0 | 0 | 1 | 1 | 2 | 0 | 0 | 0 | 0 | 0 | 1 | 0 |
| `cop_install` | `01aa0e` | 0 | 0 | 1 | 1 | 2 | 0 | 0 | 0 | 0 | 0 | 1 | 0 |
| `turn_allowed` | `01aa6e` | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 272 | 52 | 40 | 936 | 0 |
| `wheel_height` | `01aaea` | 0 | 959 | 1008 | 333 | 905 | 959 | 483 | 1662 | 975 | 1815 | 11272 | 333 |
| `turn_step` | `01ab80` | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 272 | 52 | 40 | 936 | 0 |
| `aircraft_frame` | `01abde` | 0 | 548 | 642 | 305 | 820 | 548 | 310 | 1141 | 756 | 984 | 6650 | 333 |
| `wreck_smoke` | `01aed8` | 0 | 0 | 150 | 150 | 356 | 0 | 0 | 0 | 0 | 0 | 150 | 0 |
| `lost_wait` | `01af7c` | 0 | 0 | 150 | 150 | 356 | 0 | 0 | 0 | 0 | 0 | 150 | 0 |
| `crash` | `01afba` | 0 | 0 | 11 | 9 | 27 | 0 | 0 | 0 | 0 | 0 | 60 | 0 |
| `hook_state` | `01b45a` | 0 | 548 | 641 | 304 | 818 | 548 | 310 | 867 | 705 | 940 | 5749 | 333 |
| `on_the_lift` | `01b4de` | 0 | 413 | 346 | 11 | 33 | 413 | 175 | 732 | 391 | 805 | 5404 | 0 |
| `button` | `01b5b0` | 467 | 567 | 667 | 617 | 1351 | 567 | 409 | 886 | 766 | 959 | 5777 | 989 |
| `guns` | `01b682` | 467 | 567 | 667 | 617 | 1351 | 567 | 409 | 886 | 766 | 959 | 5777 | 989 |
| `deck_span` | `01b7bc` | 0 | 0 | 1 | 1 | 2 | 0 | 0 | 0 | 1 | 0 | 1 | 0 |
| `player_reset` | `01b7ec` | 0 | 0 | 1 | 1 | 2 | 0 | 0 | 0 | 1 | 0 | 1 | 0 |
| `touches_ground` | `01b8c4` | 0 | 412 | 345 | 10 | 30 | 412 | 174 | 731 | 267 | 804 | 5403 | 0 |
| `cable_hook` | `01b92e` | 0 | 104 | 104 | 104 | 312 | 104 | 104 | 104 | 329 | 104 | 104 | 301 |
| `sub_01b9bc` | `01b9bc` | 0 | 0 | 1 | 1 | 2 | 0 | 0 | 0 | 1 | 0 | 1 | 0 |
| `engine_idle` | `01b9cc` | 0 | 1 | 1 | 1 | 3 | 1 | 1 | 1 | 2 | 1 | 1 | 1 |
| `sub_01b9f0` | `01b9f0` | 0 | 412 | 345 | 10 | 30 | 412 | 174 | 731 | 267 | 804 | 5403 | 0 |
| `ground_contact` | `01ba80` | 0 | 412 | 345 | 10 | 30 | 412 | 174 | 731 | 267 | 804 | 5403 | 0 |
| `enemy_countdown_step` | `01bc02` | 467 | 567 | 667 | 617 | 1351 | 567 | 409 | 886 | 766 | 959 | 5777 | 989 |
| `deck_state` | `01bcce` | 0 | 516 | 449 | 114 | 342 | 516 | 278 | 835 | 596 | 908 | 5507 | 301 |
| `deck_roll` | `01bdba` | 0 | 104 | 104 | 104 | 312 | 104 | 104 | 104 | 342 | 104 | 104 | 301 |
| `player_motion` | `01bdfa` | 0 | 412 | 345 | 10 | 30 | 412 | 174 | 731 | 267 | 804 | 5403 | 0 |
| `flight_controls` | `01bff4` | 0 | 412 | 345 | 10 | 30 | 412 | 174 | 731 | 267 | 804 | 5403 | 0 |
| `frame_select` | `01c378` | 0 | 548 | 641 | 304 | 818 | 548 | 310 | 867 | 705 | 940 | 5749 | 333 |
| `deck_controls` | `01c4e8` | 0 | 104 | 104 | 104 | 312 | 104 | 104 | 104 | 329 | 104 | 104 | 301 |
| `deck_edge` | `01c5f4` | 0 | 104 | 104 | 104 | 312 | 104 | 104 | 104 | 329 | 104 | 104 | 301 |
| `player_update` | `01c660` | 467 | 567 | 667 | 617 | 1351 | 567 | 409 | 886 | 766 | 959 | 5777 | 989 |
| `record_at` | `01c982` | 0 | 959 | 1011 | 337 | 907 | 959 | 483 | 1597 | 971 | 1743 | 11225 | 333 |
| `vblank_every_frame` | `01c9ca` | 0 | 0 | 21 | 21 | 42 | 0 | 0 | 0 | 0 | 0 | 21 | 0 |
| `read_joystick` | `01ca32` | 0 | 0 | 5 | 5 | 10 | 0 | 0 | 0 | 0 | 0 | 5 | 0 |
| `rand_mod` | `01cac8` | 0 | 0 | 1 | 1 | 2 | 0 | 0 | 0 | 1 | 0 | 1 | 0 |
| `read_joy_dispatch` | `01cb20` | 0 | 0 | 5 | 5 | 10 | 0 | 0 | 0 | 0 | 0 | 5 | 0 |
| `sub_01cb30` | `01cb30` | 0 | 2613 | 2931 | 1401 | 3730 | 2613 | 1423 | 3386 | 2970 | 4441 | 25771 | 1332 |
| `on_water` | `01cb74` | 0 | 0 | 13 | 11 | 33 | 0 | 0 | 0 | 0 | 0 | 61 | 0 |
| `enemy_aircraft_step` | `01e7d6` | 467 | 567 | 667 | 617 | 1351 | 567 | 409 | 886 | 766 | 959 | 5777 | 989 |
| `sub_01ea28` | `01ea28` | 0 | 9 | 12 | 12 | 36 | 9 | 9 | 9 | 30 | 141 | 12 | 15 |
| `sub_01eac0` | `01eac0` | 0 | 12 | 17 | 17 | 53 | 12 | 12 | 12 | 41 | 230 | 17 | 16 |
| `sub_01eb2e` | `01eb2e` | 0 | 9 | 12 | 12 | 36 | 9 | 9 | 9 | 30 | 141 | 12 | 15 |
| `sub_01eb4c` | `01eb4c` | 0 | 96 | 248 | 89 | 267 | 96 | 101 | 376 | 342 | 163 | 1235 | 0 |
| `soundfx_vblank` | `01ec64` | 0 | 0 | 21 | 21 | 42 | 0 | 0 | 0 | 0 | 0 | 21 | 0 |
| `weapon_gauge_reset` | `01edbc` | 0 | 0 | 1 | 1 | 2 | 0 | 5 | 0 | 2 | 0 | 1 | 0 |
| `rand_beam` | `0203be` | 0 | 0 | 1 | 1 | 2 | 0 | 0 | 0 | 1 | 0 | 1 | 0 |
| `poll_fire` | `02044c` | 0 | 0 | 21 | 21 | 42 | 0 | 0 | 0 | 0 | 0 | 21 | 0 |
| `read_fire_button` | `02046a` | 0 | 0 | 21 | 21 | 42 | 0 | 0 | 0 | 0 | 0 | 21 | 0 |
| `sub_0204e4` | `0204e4` | 0 | 548 | 641 | 304 | 818 | 548 | 310 | 867 | 705 | 940 | 5749 | 333 |
| `sub_0204ec` | `0204ec` | 0 | 548 | 641 | 304 | 818 | 548 | 310 | 867 | 705 | 940 | 5749 | 333 |
| `shape_find_c` | `0204f4` | 0 | 2613 | 2931 | 1401 | 3730 | 2613 | 1423 | 3386 | 2970 | 4441 | 25771 | 1332 |
| `shape_find` | `020560` | 0 | 2613 | 2931 | 1401 | 3730 | 2613 | 1423 | 3386 | 2970 | 4441 | 25771 | 1332 |
| `rect_fill` | `021010` | 0 | 0 | 1 | 1 | 2 | 0 | 0 | 0 | 0 | 0 | 1 | 0 |
| `draw_set_target` | `02124a` | 0 | 0 | 1 | 1 | 2 | 0 | 0 | 0 | 0 | 0 | 1 | 0 |
| `clip_set` | `02129c` | 0 | 0 | 1 | 1 | 2 | 0 | 0 | 0 | 0 | 0 | 1 | 0 |
| `blit_begin` | `0212ce` | 0 | 0 | 1 | 1 | 2 | 0 | 0 | 0 | 0 | 0 | 1 | 0 |
| `blit_end` | `0212d4` | 0 | 0 | 1 | 1 | 2 | 0 | 0 | 0 | 0 | 0 | 1 | 0 |
| `ffp_add` | `021c9c` | 0 | 412 | 345 | 10 | 30 | 412 | 174 | 731 | 267 | 804 | 5403 | 0 |
| `ffp_neg` | `021cb0` | 0 | 0 | 129 | 9 | 27 | 0 | 0 | 329 | 97 | 693 | 4622 | 0 |
| `ffp_fix` | `021cc4` | 0 | 1236 | 1035 | 30 | 90 | 1236 | 522 | 2193 | 801 | 2412 | 16209 | 0 |
| `ffp_div` | `021cd8` | 0 | 824 | 690 | 20 | 60 | 824 | 348 | 1462 | 534 | 1608 | 10806 | 0 |
| `ffp_flt` | `021ce2` | 0 | 824 | 690 | 20 | 60 | 824 | 348 | 1462 | 534 | 1608 | 10806 | 0 |
| `ffp_mul` | `021cec` | 0 | 1236 | 1035 | 30 | 90 | 1236 | 522 | 2193 | 801 | 2412 | 16209 | 0 |
| `sub_021d7c` | `021d7c` | 0 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 0 |
| `sub_021e24` | `021e24` | 0 | 0 | 30 | 30 | 70 | 0 | 0 | 0 | 0 | 0 | 30 | 0 |
| `sub_0222f4` | `0222f4` | 0 | 0 | 30 | 30 | 70 | 0 | 0 | 0 | 0 | 0 | 30 | 0 |
| `os_disable` | `022d48` | 467 | 567 | 667 | 617 | 1351 | 567 | 409 | 886 | 766 | 959 | 5777 | 989 |
| `os_enable` | `022d66` | 467 | 567 | 667 | 617 | 1351 | 567 | 409 | 886 | 766 | 959 | 5777 | 989 |
| `sub_022e40` | `022e40` | 0 | 0 | 1 | 1 | 2 | 0 | 0 | 0 | 0 | 0 | 1 | 0 |
| `sub_022e8a` | `022e8a` | 0 | 0 | 1 | 1 | 2 | 0 | 0 | 0 | 0 | 0 | 1 | 0 |
| `gfx_WaitTOF` | `022eee` | 0 | 0 | 21 | 21 | 42 | 0 | 0 | 0 | 0 | 0 | 21 | 0 |

### Entropy reads, by the routine that called `rand_beam`

| Window | Phase | Caller | `deck` | `flight` | `climb` | `lost` | `gameover` | `night` | `select` | `turns` | `landing` | `island` | `fuel` | `keys` |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| outer | M | `rand_mod` | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 23 |
| setup | M | `rand_mod` | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 44 |
| mission | F | `draw_dashboard` | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 448 | 0 |
| mission | F | `smoke_claim` | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 4 | 0 | 40 |
| mission | F | `target_fire` | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 184 | 0 | 0 |
| mission | F | `target_frame` | 0 | 1422 | 1076 | 0 | 0 | 1422 | 470 | 2258 | 0 | 2990 | 21388 | 0 |
| mission | T | `rand_mod` | 0 | 0 | 1 | 1 | 2 | 0 | 0 | 0 | 1 | 0 | 1 | 0 |


## Appendix: the regions no run executed

Every region of an M4 routine that none of the scripts, the night mission, the key runs
and the setups of the fifteen maps executed, with the stand-in marker that covers it or
what it is otherwise; below them, the markers whose region the original did run (in the
island flight, which is judged by attribution, or in the key run that loads a saved game)
and the markers that stand for a value rather than a region. "Ported from reading" with a
test named means the region is held to the original by that test rather than by a script.
Written by

```text
.venv/bin/python tools/reach_observe.py --part2 --blocks --setups --json REACH.json
.venv/bin/python tools/reach_observe.py --cold REACH.json
```

| Routine | Region no run executed | Stand-in marker, or what it is | Owed to |
|---|---|---|---|
| `main` `0x010006` | `0x010036`-`0x010041` | M3's: the command line's demo file, which the port has no command line for | |
| `main` `0x010006` | `0x010104`-`0x010109` | ported from reading: `demo_mode` sets `0x026D44` before step S | |
| `main` `0x010006` | `0x010132`-`0x01018D` | `0x010132`-`0x01018D`, the next mission of a campaign | M7 |
| `main` `0x010006` | `0x0101B4`-`0x0101BD` | ported from reading: a demo ends on the fire button | |
| `frame_update` `0x010228` | `0x0102BC`-`0x0102CD` | ported from reading: `player_lost_restart` from `frame_update`, when `0x024F24` is set, which no instruction of the executable does | |
| `flip_buffers` `0x01030C` | `0x010322`-`0x010331` | ported from reading: the flash of `flip_buffers` | |
| `draw_player` `0x0103A6` | `0x01043E`-`0x01045B` | unreachable: no branch leads there | |
| `draw_player` `0x0103A6` | `0x0104D4`-`0x0104D5` | ported from reading: the climb clamped at -2 in the eighth-scale view | |
| `draw_player` `0x0103A6` | `0x01058C`-`0x01058D` | ported from reading | |
| `draw_player` `0x0103A6` | `0x0105F0`-`0x0105F1` | ported from reading: the cable's end when the aircraft faces right | |
| `draw_player` `0x0103A6` | `0x010642`-`0x0106B3` | `0x010642`, the guns' muzzle flash | M5 |
| `draw_objects` `0x0106BE` | `0x0106CC`-`0x0106CF` | ported from reading: `0x02536C` cleared | |
| `draw_objects` `0x0106BE` | `0x0106F6`-`0x0106F9` | ported from reading: the extra object record drawn | |
| `object_draw` `0x010702` | `0x010726`-`0x010779` | `0x010726`, an object of another type | M5 |
| `object_draw` `0x010702` | `0x0107C2`-`0x0107C5` | `0x0107C2`, an object in the eighth-scale view | M5 |
| `object_spawn` `0x010820` | `0x010840`-`0x010841` | ported from reading: all fifteen object records in use, nothing is left | |
| `object_spawn` `0x010820` | `0x01088E`-`0x010999` | another entry, the weapon's launch from `0x01107C`: M5's, behind the stand-in at `0x01B5E2` | |
| `objects_step` `0x010A72` | `0x010A9E`-`0x010AA1` | ported from reading: the extra object record walked as the others are | |
| `object_step` `0x010AA6` | `0x010AB6`-`0x010CF9` | `0x010AB6`-`0x010DA5`, a weapon or a shot in flight | M5 |
| `object_step` `0x010AA6` | `0x010D00`-`0x010DA5` | `0x010AB6`-`0x010DA5`, a weapon or a shot in flight | M5 |
| `draw_enemy_aircraft` `0x010DA6` | `0x010DBA`-`0x010E15` | `0x010DBA`, the formation words of `0x0251D8` | M6 |
| `draw_enemy_aircraft` `0x010DA6` | `0x010E26`-`0x010ED1` | `0x010E26`, an enemy aircraft | M6 |
| `draw_game_over` `0x0110C2` | `0x011118`-`0x011123` | ported from reading; tests/`test_oracle_m4.py`, every count | |
| `choose_night` `0x0111FC` | `0x0111FC`-`0x011233` | ported from reading; reached only between two missions, part 2 | |
| `weapon_menu` `0x0112B0` | `0x0112D4`-`0x0112D5` | ported from reading: the cursor keys and Return in the weapon menu | |
| `weapon_menu` `0x0112B0` | `0x0112DE`-`0x0112DF` | ported from reading: the cursor keys and Return in the weapon menu | |
| `weapon_menu` `0x0112B0` | `0x0112E8`-`0x0112E9` | ported from reading: the cursor keys and Return in the weapon menu | |
| `weapon_menu` `0x0112B0` | `0x0112F2`-`0x0112F5` | ported from reading: the cursor keys and Return in the weapon menu | |
| `logic_tick` `0x011386` | `0x0113A2`-`0x0113B3` | `0x0113A2`, the oil leaking from a damaged engine | M6 |
| `run_queued_ticks` `0x0114D8` | `0x0114E0`-`0x0114E5` | `0x0114E0`, `run_queued_ticks`, demo playback and recording | M7 |
| `run_queued_ticks` `0x0114D8` | `0x0114EE`-`0x0114EF` | ported from reading: nothing runs while paused | |
| `run_queued_ticks` `0x0114D8` | `0x011508`-`0x01150D` | ported from reading: `demo_mode` sets `0x026D44` | |
| `ship_launches` `0x011510` | `0x01152A`-`0x011569` | `0x01152A`, the Japanese carrier's aircraft | M6 |
| `ship_launches` `0x011510` | `0x011572`-`0x011573` | ported from reading: nothing is launched while `0x027348` counts down | |
| `ship_launches` `0x011510` | `0x0115AC`-`0x0115E9` | `0x0115C4`-`0x0115E9`, a ship launching an aircraft | M6 |
| `ship_launches` `0x011510` | `0x0115F4`-`0x011621` | `0x0115F4`-`0x011621`, the last ship's aircraft readied | M6 |
| `airfields_step` `0x011622` | `0x011630`-`0x011689` | `0x011630`, an enemy aircraft taking off | M6 |
| `airfields_step` `0x011622` | `0x0116BE`-`0x011709` | `0x0116BE`, the player near an enemy airfield | M6 |
| `vblank_server` `0x011754` | `0x011790`-`0x0117D3` | M3's input half: demo playback (M7) | |
| `vblank_server` `0x011754` | `0x01180A`-`0x011841` | M3's input half: demo recording (M7) | |
| `vblank_server` `0x011754` | `0x011856`-`0x0118D3` | ported from reading; tests/`test_oracle_m4.py`, the ticker | |
| `vblank_server` `0x011754` | `0x0118DE`-`0x01195D` | ported from reading; tests/`test_oracle_m4.py`, the ticker | |
| `gun_splashes` `0x0119BC` | `0x0119C4`-`0x011A11` | `0x0119C4`, the guns' bullets in the water | M5 |
| `engine_smoke` `0x011BFC` | `0x011C24`-`0x011C5B` | `0x011C24`, smoke from a damaged engine | M6 |
| `balloons_step` `0x011C5E` | `0x011C66`-`0x011CAB` | `0x011C66`, the balloons | M5 |
| `ships_sinking` `0x011CAE` | `0x011CCA`-`0x011CCD` | `0x011CCA`, a ship sinking (`0x011CD8`) | M6 |
| `target_timers` `0x011DE4` | `0x011DFE`-`0x011E29` | `0x011DFE`, a slot-3 target's timer | M5 |
| `target_timers` `0x011DE4` | `0x011E48`-`0x011E73` | `0x011E48`, a slot-4 target's timer | M5 |
| `engine_sound` `0x012132` | `0x0121D8`-`0x012207` | the sound slots (M8): an enemy aircraft's distance for its engine | |
| `engine_sound` `0x012132` | `0x01221E`-`0x012225` | the sound slots (M8): an enemy aircraft's distance for its engine | |
| `map_load` `0x012ADC` | `0x012B80`-`0x012B83` | an allocation failed, fatal; the port's tables are fixed (src/mission.def) | |
| `free_map` `0x012BBE` | `0x012BF6`-`0x012C0D` | ported from reading: a ship released at the end of a mission | |
| `free_map` `0x012BBE` | `0x012C1A`-`0x012C31` | ported from reading: a ship released at the end of a mission | |
| `free_map` `0x012BBE` | `0x012C3E`-`0x012C55` | ported from reading: a ship released at the end of a mission | |
| `free_map` `0x012BBE` | `0x012C62`-`0x012C79` | ported from reading: a ship released at the end of a mission | |
| `map_scan` `0x012D5A` | `0x0130AE`-`0x0130B1` | an allocation failed, fatal; the port's tables are fixed (src/mission.def) | |
| `load_ship_shapes` `0x013252` | `0x01327C`-`0x013283` | battleship.shp missing from the disk; the port loads every container at start-up | |
| `load_ship_shapes` `0x013252` | `0x0132C4`-`0x0132C7` | destroyer.shp missing, fatal; the port loads every container at start-up | |
| `load_ship_shapes` `0x013252` | `0x0132FE`-`0x013301` | cruiseship.shp missing, fatal; the port loads every container at start-up | |
| `load_ship_shapes` `0x013252` | `0x013346`-`0x013349` | japcarrier.shp missing, fatal; the port loads every container at start-up | |
| `ship_guns_setup` `0x01350E` | `0x013516`-`0x013517` | ported from reading: nothing for a loaded game | |
| `draw_world` `0x013772` | `0x01383A`-`0x01383D` | ported from reading: records before the map's start stepped over | |
| `draw_world` `0x013772` | `0x013900`-`0x013901` | ported from reading: the distance handed to the sound engine | |
| `ship_planes` `0x01391E` | `0x01395A`-`0x01396B` | `0x01395A`, the last ship's clip at full scale | M6 |
| `ship_planes` `0x01391E` | `0x013976`-`0x0139B7` | `0x013976`, aircraft on a ship's deck | M6 |
| `ship_planes` `0x01391E` | `0x0139CE`-`0x013A0D` | `0x0139D6`, the japanese carrier's crane | M6 |
| `airfields_draw` `0x013A18` | `0x013A36`-`0x013AB1` | `0x013A36`, an airfield in view | M6 |
| `deck_aircraft` `0x013ABC` | `0x013ADA`-`0x013ADB` | ported from reading: more than nine lives count as nine | |
| `record_extras` `0x013B1C` | `0x013B52`-`0x013BCD` | `0x013B52`, an island's flag | M5 |
| `targets_3_draw` `0x013D78` | `0x013DB2`-`0x013DB9` | `0x013DB2`, a slot-3 target's count | M5 |
| `targets_f_draw` `0x013DE8` | `0x013E3E`-`0x013E5D` | `0x013DFA`-`0x013E5D`, the slot-`0x0F` targets | M5 |
| `soldiers_draw` `0x013EEE` | `0x013F14`-`0x013FEF` | `0x013F0A`-`0x01408B`, a soldier | M5 |
| `soldiers_draw` `0x013EEE` | `0x014000`-`0x01400F` | `0x013F0A`-`0x01408B`, a soldier | M5 |
| `soldiers_draw` `0x013EEE` | `0x01403C`-`0x014041` | `0x013F0A`-`0x01408B`, a soldier | M5 |
| `soldiers_draw` `0x013EEE` | `0x014050`-`0x01408B` | `0x013F0A`-`0x01408B`, a soldier | M5 |
| `window_strip` `0x014206` | `0x014244`-`0x01424D` | ported from reading: the 3-D view over an enemy ship whose +`0x12` is 6000 | |
| `window_strip` `0x014206` | `0x0142AC`-`0x01430B` | `0x0142BC`, an enemy aircraft in the 3-D view | M6 |
| `window_strip` `0x014206` | `0x01435C`-`0x014363` | ported from reading: a record of class 6 to 8 in the 3-D view | |
| `window_strip` `0x014206` | `0x014382`-`0x014383` | ported from reading: land in the 3-D view, which draws the shore line | |
| `window_strip` `0x014206` | `0x014390`-`0x0143A3` | ported from reading: the shore line of the 3-D view | |
| `window_strip` `0x014206` | `0x0143AE`-`0x0143DD` | ported from reading: a record of class 6 to 8 in the 3-D view | |
| `window_shape` `0x0145A6` | `0x0145EE`-`0x014601` | ported from reading: the shape of a record in the 3-D view | |
| `window_shape` `0x0145A6` | `0x01460A`-`0x01460F` | ported from reading: the shape of a record in the 3-D view | |
| `window_shape` `0x0145A6` | `0x01461A`-`0x01461B` | ported from reading: the shape of a ship in the 3-D view facing right | |
| `window_shape` `0x0145A6` | `0x01464C`-`0x014655` | ported from reading: an enemy ship's own shapes in the 3-D view | |
| `window_shape` `0x0145A6` | `0x014662`-`0x014665` | ported from reading: an enemy ship's own shapes in the 3-D view | |
| `window_shape` `0x0145A6` | `0x01467E`-`0x0146C5` | ported from reading: the shape of a record in the 3-D view | |
| `ship_at_span` `0x014A52` | `0x014A5A`-`0x014A6F` | ported from reading; tests/`test_oracle_m4.py`, `ship_at_offset` | |
| `ship_at_span` `0x014A52` | `0x014A78`-`0x014A8D` | ported from reading; tests/`test_oracle_m4.py`, `ship_at_offset` | |
| `ship_at_span` `0x014A52` | `0x014A96`-`0x014AAB` | ported from reading; tests/`test_oracle_m4.py`, `ship_at_offset` | |
| `ship_at_span` `0x014A52` | `0x014AB4`-`0x014AC9` | ported from reading; tests/`test_oracle_m4.py`, `ship_at_offset` | |
| `ship_at_span` `0x014A52` | `0x014AE0`-`0x014AE1` | ported from reading; tests/`test_oracle_m4.py`, `ship_at_offset` | |
| `ship_guns_draw` `0x014C3E` | `0x014C66`-`0x014D49` | `0x014C66`, an enemy ship's guns | M6 |
| `target_frame` `0x014D50` | `0x014D92`-`0x014DAF` | reached only when `0x014DB8` gives a frame, after its stand-ins (M5) | |
| `target_range_frame` `0x014DB8` | `0x014DCA`-`0x014DCF` | `0x014DCA`, the range test in the eighth-scale view | M5 |
| `target_range_frame` `0x014DB8` | `0x014DD6`-`0x014DE1` | ported from reading: no frame for a target far ahead | |
| `target_range_frame` `0x014DB8` | `0x014DE8`-`0x014E0F` | `0x014DE8`, a target within range at full scale | M5 |
| `target_range_frame` `0x014DB8` | `0x014E18`-`0x014EAB` | `0x014E18`, a slot-5 target in view | M5 |
| `target_fire` `0x014F5C` | `0x014FCA`-`0x014FE7` | `0x014F72`-`0x014FE7`, a target near the aircraft | M5 |
| `splash_spawn` `0x0152B0` | `0x0152D8`-`0x0152E1` | `0x0152D8`, a splash on a record of low bits 2 | M5 |
| `splashes_draw` `0x0152F8` | `0x015334`-`0x01533B` | `0x015334`, a splash of kind 2 | M5 |
| `smoke_claim` `0x015460` | `0x01547A`-`0x01547D` | ported from reading: all forty smoke records in use, nothing is left | |
| `smoke_claim` `0x015460` | `0x01548A`-`0x01548F` | `0x01548A`, smoke below the ground's line | M5 |
| `balloons_draw` `0x01557C` | `0x015584`-`0x015621` | `0x015584`, the balloons | M5 |
| `ground_height` `0x015714` | `0x015866`-`0x015877` | ported from reading; tests/`test_oracle_m4.py`, every record of five maps | |
| `load_dash_assets` `0x01653C` | `0x016568`-`0x01656B` | dash.shp missing, fatal; the port loads every container at start-up | |
| `screen_game_restore` `0x016D32` | `0x016D32`-`0x016D79` | ported from reading: the play screen back after the save or the load dialog | |
| `demo_end` `0x01852A` | `0x018536`-`0x01855D` | `0x018536`, saving a recorded demo | M7 |
| `turn_allowed` `0x01AA6E` | `0x01AA9A`-`0x01AACD` | ported from reading; tests/`test_oracle_m4.py`, an enemy aircraft that stops a turn | |
| `wreck_smoke` `0x01AED8` | `0x01AF16`-`0x01AF19` | ported from reading: the burning wreck's smoke | |
| `crash` `0x01AFBA` | `0x01AFFC`-`0x01B00F` | ported from reading; tests/`test_oracle_m4.py`, the aircraft down on land or a ship | |
| `crash` `0x01AFBA` | `0x01B070`-`0x01B1A7` | ported from reading; tests/`test_oracle_m4.py`, the aircraft down on land | |
| `crash` `0x01AFBA` | `0x01B1B4`-`0x01B1BB` | ported from reading; tests/`test_oracle_m4.py`, the aircraft down on a ship | |
| `crash` `0x01AFBA` | `0x01B1D4`-`0x01B1F7` | ported from reading; tests/`test_oracle_m4.py`, the attitude levelling out | |
| `crash` `0x01AFBA` | `0x01B200`-`0x01B2A1` | ported from reading; tests/`test_oracle_m4.py`, a wreck sliding along a ship | |
| `crash` `0x01AFBA` | `0x01B304`-`0x01B33D` | `0x01B304`, a wreck at rest on land or a deck | M5 |
| `crash` `0x01AFBA` | `0x01B40C`-`0x01B423` | ported from reading; tests/`test_oracle_m4.py`, a wreck at rest on land or a ship | |
| `crash` `0x01AFBA` | `0x01B430`-`0x01B439` | ported from reading; tests/`test_oracle_m4.py`, a wreck at rest on land or a ship | |
| `hook_state` `0x01B45A` | `0x01B4A8`-`0x01B4AB` | ported from reading; tests/`test_oracle_m4.py`, the hook with the carrier sunk | |
| `on_the_lift` `0x01B4DE` | `0x01B538`-`0x01B56F` | ported from reading; tests/`test_oracle_m4.py`, on the lift facing right | |
| `on_the_lift` `0x01B4DE` | `0x01B582`-`0x01B589` | ported from reading; tests/`test_oracle_m4.py`, short of the lift | |
| `button` `0x01B5B0` | `0x01B5D2`-`0x01B5E7` | `0x01B5E2`, the other weapon dropped | M5 |
| `button` `0x01B5B0` | `0x01B5EE`-`0x01B5FB` | ported from reading; tests/`test_oracle_m4.py`, the guns firing (their bullets are M5's, the stand-in at `0x0119C4`) | |
| `guns` `0x01B682` | `0x01B692`-`0x01B7B3` | `0x01B6B0`, the guns at an enemy aircraft | M6 |
| `ground_contact` `0x01BA80` | `0x01BB68`-`0x01BB81` | ported from reading; tests/`test_oracle_m4.py`, a bounce off the deck | |
| `ground_contact` `0x01BA80` | `0x01BBAC`-`0x01BBF9` | `0x01BBF4`, what a crash on land does to the island's targets | M5 |
| `enemy_countdown_step` `0x01BC02` | `0x01BC1A`-`0x01BC1D` | ported from reading; tests/`test_oracle_m4.py`, the enemy's countdown far east | |
| `enemy_countdown_step` `0x01BC02` | `0x01BC5E`-`0x01BCC9` | `0x01BC66`, the enemy aircraft come | M6 |
| `deck_state` `0x01BCCE` | `0x01BCEA`-`0x01BCF9` | ported from reading; tests/`test_oracle_m4.py`, the deck state | |
| `deck_state` `0x01BCCE` | `0x01BD7A`-`0x01BD91` | ported from reading; tests/`test_oracle_m4.py`, the deck state | |
| `player_motion` `0x01BDFA` | `0x01BF84`-`0x01BF89` | ported from reading; tests/`test_oracle_m4.py`, `player_motion` | |
| `player_motion` `0x01BDFA` | `0x01BFE8`-`0x01BFEF` | ported from reading; tests/`test_oracle_m4.py`, `player_motion` | |
| `flight_controls` `0x01BFF4` | `0x01C074`-`0x01C085` | ported from reading; tests/`test_oracle_m4.py`, the stick in the air | |
| `flight_controls` `0x01BFF4` | `0x01C09C`-`0x01C09F` | ported from reading; tests/`test_oracle_m4.py`, the stick in the air | |
| `flight_controls` `0x01BFF4` | `0x01C12E`-`0x01C131` | ported from reading; tests/`test_oracle_m4.py`, the stick in the air | |
| `flight_controls` `0x01BFF4` | `0x01C200`-`0x01C20D` | ported from reading; tests/`test_oracle_m4.py`, the stick in the air | |
| `flight_controls` `0x01BFF4` | `0x01C2A0`-`0x01C2CD` | ported from reading; tests/`test_oracle_m4.py`, the stick in the air | |
| `flight_controls` `0x01BFF4` | `0x01C326`-`0x01C34F` | ported from reading; tests/`test_oracle_m4.py`, the stick in the air | |
| `deck_controls` `0x01C4E8` | `0x01C5E6`-`0x01C5EB` | ported from reading; tests/`test_oracle_m4.py`, the stick on the deck | |
| `player_update` `0x01C660` | `0x01C6E8`-`0x01C705` | ported from reading: the aircraft below the sea without a crash | |
| `player_update` `0x01C660` | `0x01C7C6`-`0x01C881` | ported from reading: the burning wreck (state 8), which a crash on land leaves | |
| `player_update` `0x01C660` | `0x01C8EE`-`0x01C8EF` | ported from reading: state 9 does nothing | |
| `player_update` `0x01C660` | `0x01C934`-`0x01C94B` | the player update's jump table: data | |
| `record_at` `0x01C982` | `0x01C98C`-`0x01C98F` | ported from reading; tests/`test_oracle_m4.py`, `record_at` left of the map | |
| `flash_set` `0x01CAB4` | `0x01CAB4`-`0x01CAC7` | ported from reading: the sky's flash, which a crash on a ship sets | |
| `burn_smoke` `0x01CAE0` | `0x01CAE0`-`0x01CB1B` | ported from reading: smoke from the burning wreck | |
| `record_on_ship` `0x01CB34` | `0x01CB50`-`0x01CB51` | ported from reading: a record at the list's end is on no ship | |
| `record_on_ship` `0x01CB34` | `0x01CB70`-`0x01CB71` | ported from reading: a record of other low bits is on no ship | |
| `on_water` `0x01CB74` | `0x01CBAE`-`0x01CBAF` | ported from reading; tests/`test_oracle_m4.py`, `on_water` | |
| `ship_of_record` `0x01CBF2` | `0x01CC04`-`0x01CC0F` | ported from reading: a debugging line to the console, and 1 | |
| `ship_of_record` `0x01CBF2` | `0x01CC68`-`0x01CCB5` | ported from reading: a debugging line to the console, and 1 | |
| `ingame_keys` `0x01CCF6` | `0x01CD92`-`0x01CD9F` | ported from reading: the save dialog on the carrier | |
| `ingame_keys` `0x01CCF6` | `0x01CE0A`-`0x01CE1D` | ported from reading: the load dialog cancelled | |
| `ingame_keys` `0x01CCF6` | `0x01CE26`-`0x01CE27` | the crash reporter of Control-B, which the port does not have (re/notes/keys.md) | |
| `enemy_aircraft_step` `0x01E7D6` | `0x01E7FC`-`0x01E8A7` | `0x01E7FC`, an enemy aircraft | M6 |
| `lives_gauge_reset` `0x01EDEA` | `0x01EDF4`-`0x01EDF5` | ported from reading; tests/`test_oracle_m4.py`, the gauge resets | |
| `lives_gauge_reset` `0x01EDEA` | `0x01EDFE`-`0x01EDFF` | ported from reading; tests/`test_oracle_m4.py`, the gauge resets | |
| `draw_dashboard` `0x01EE16` | `0x01EEB8`-`0x01EED1` | ported from reading: the oil warning's blink | |
| `draw_dashboard` `0x01EE16` | `0x01F062`-`0x01F065` | `0x01F062`, unlimited weapons | M5 |
| `draw_dashboard` `0x01EE16` | `0x01F07A`-`0x01F0AD` | `0x01F07A`, the weapon counter's drums turning | M5 |
| `draw_dashboard` `0x01EE16` | `0x01F102`-`0x01F103` | ported from reading: negative lives count as none | |
| `draw_dashboard` `0x01EE16` | `0x01F10C`-`0x01F10D` | ported from reading: more than nine lives count as nine | |
| `draw_dashboard` `0x01EE16` | `0x01F12E`-`0x01F133` | ported from reading: the lives drum turning down, a life more | |
| `draw_dashboard` `0x01EE16` | `0x01F186`-`0x01F187` | `0x01F186`, the enemy plane counter above 99 | M5 |
| `draw_dashboard` `0x01EE16` | `0x01F1DA`-`0x01F1DB` | ported from reading: the first row of bars clamped at seven | |
| `draw_dashboard` `0x01EE16` | `0x01F1EE`-`0x01F1EF` | ported from reading: the second row of bars clamped at seven | |
| `kill_icons` `0x01F200` | `0x01F206`-`0x01F217` | `0x01F206`, the enemy plane counter's kill icons | M5 |
| `enemy_arrows` `0x01F21A` | `0x01F226`-`0x01F235` | `0x01F226`-`0x01F269`, an arrow to an enemy aircraft | M6 |
| `enemy_arrows` `0x01F21A` | `0x01F240`-`0x01F269` | `0x01F226`-`0x01F269`, an arrow to an enemy aircraft | M6 |
| `line_draw` `0x021318` | `0x021342`-`0x021343` | ported from reading, PROVISIONAL: the clipping of `line_draw` | |
| `line_draw` `0x021318` | `0x021354`-`0x021357` | ported from reading, PROVISIONAL: the clipping of `line_draw` | |
| `line_draw` `0x021318` | `0x02136A`-`0x02136B` | ported from reading, PROVISIONAL: the clipping of `line_draw` | |
| `line_draw` `0x021318` | `0x02137C`-`0x02137F` | ported from reading, PROVISIONAL: the clipping of `line_draw` | |
| `line_draw` `0x021318` | `0x02138E`-`0x0214EB` | ported from reading, PROVISIONAL: the clipping of `line_draw` | |
| `line_draw` `0x021318` | `0x021556`-`0x021561` | the blitter's busy wait, which the port's line has none of | |
| `line_draw` `0x021318` | `0x0215D0`-`0x0215D7` | ported from reading, PROVISIONAL: a line wholly outside the clip | |
| | run by the original | `0x010F2A`, a smoke record | M5 |
| | run by the original | `0x013D92`, a destroyed slot-3 target | M5 |
| | run by the original | `0x019152`, `save_game_read`: a saved game loaded | M7 |
| | run by the original | `0x01CDD4`, a loaded game: the briefing and the mission again | M7 |
| | no region: a value | more than four islands, in `0x0140E8` | M6 |
| | no region: a value | a negative score, in `0x01F26A` | M7 |
| | no region: a value | a ticker message outside the registered state | M7 |
