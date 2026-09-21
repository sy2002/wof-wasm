# M4, part 1: the world as a pass

Milestone M4 of `SPEC.md` section 9, its first half: everything the original runs between
the end of the briefing and the first pass of a mission, and everything a pass does, which
is `frame_update`'s tree and the mission half of the VBlank server. The logic tick is
part 2's and is a marked stand-in here. Addresses use the standard load layout.

Every statement is either **observed**, with the tool or test that shows it, or **read**,
which means it comes from the listing alone.

```text
src/mission.c            the outer loop's reset, the map loader, the setup after the briefing
src/world.c              frame_update and the playfield half of a pass
src/dash.c               the dashboard: the 3-D view and the instruments
src/front.c              main's mission part: the setup's order, the inner loop, the stand-ins
src/input.c              vblank_server's mission half: the counter and the ticker
src/records.def          the record layouts, with the original's offsets
src/mission.def          the tables: fixed ones in DATA and the allocations, at fixed places
tools/reach_observe.py   what the scripts enter, where, how often; block coverage; cold regions
tests/m4state.py         the original's state as the port's structs, field by field
tests/m4compare.py       the headless original recorded; the port replayed in two loops
tests/m4complete.py      the completeness list: every address a mission writes, accounted for
tests/test_world.py      V1, V2, V3 and the pass rates
tests/test_mission.py    the setup on every map and rank, the capacities, the arena
tests/test_oracle_m4.py  the blits against the blitter model, the pure routines under the oracle
tests/test_state_m4.py   a state saved in a mission, native and wasm; the release core's hooks
tests/m4_renders.py      pictures of the mission scene, for looking at (dist/m4-part1/)
```

## What decides what is ported: the reach map

The five mission scripts of `tools/pass_observe.py` that belong to M4 are `deck`, `flight`,
`climb`, `lost` and `gameover` (guns and bomb are M5's). `tools/reach_observe.py` runs each
under the headless original with a hook on the first instruction of every routine of
`re/functions.csv` and counts every entry by the part of the run it happened in and by the
harness's phase (observed):

```text
.venv/bin/python tools/reach_observe.py                                 the tables below
.venv/bin/python tools/reach_observe.py --markdown TABLE.md             the same, as Markdown
.venv/bin/python tools/reach_observe.py --blocks --json REACH.json       with block coverage
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

- **`line_draw`** is never entered in any of the five scripts, from any caller. Its only
  caller is `0x0103A6`, on the path for `player_on_deck` 7, which none of the five took
  inside a pass. It is not ported (`SPEC.md` section 10, point 7 stays open).
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
  written by the tick, part 2's.
- **`ingame_keys`** is entered from `main`'s inner loop at `0x01010E`, in phase M, once per
  head of the loop (passes plus one), never from inside `frame_update`.
- **Entropy.** Before the rank selection `0x01CAC8` draws once (the reset of the outer
  loop's head), in the setup twice (the player's reset, twice). In a mission `0x014D50`
  draws twice per pass in the eighth-scale view with the aircraft in the air (F), and
  `0x01CAC8` once per restart inside the tick (T).

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

The tick at `0x0100F2` is part 2's. It writes twenty fields of the registered state
before step S; `tests/test_world.py` keeps them as `SETUP_TICK_WRITES`, derived again on
every run from the harness's own record of that tick's writes, and they are the only fields
in which the port may differ from the original at S.

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
`player_lost_restart` (a stand-in); `draw_world` with the sky, the map strip and its
layers; the Smoke, Soldiers and Splashes pools; the object records; `weapon_marker`;
the balloons; `draw_game_over`; the dashboard's clip and the back buffer's dashboard;
`map_window`; `draw_dashboard`; `frame_drawn` set; `flip_buffers`.

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
tick, and replays its schedule through the port with the fades at 0. Two loops:

- **Open** (V1): before every pass the port's registered state, its views, its entropy
  position and the mirror markers are set to the original's state before that pass.
- **Closed** (V2): the port runs on its own; after each of its ticks, which are the
  stand-in, it is handed exactly the bytes the original's tick wrote, taken by address from
  the harness's record. In test builds the tick stand-in waits as many VBlanks as the
  original's tick did, counted from the schedule.

After every pass, in both loops: every registered global and table, the drawing calls with
their arguments, the entropy draws with their callers, which view is in front, the palette
of every output row, and the map's records drawn against `tools/map_decode.py`. The headless
original runs no blits, so the pixels themselves are not compared; the blits are held to
the blitter model instead (V5).

| Check | Test | What it covers |
|---|---|---|
| V1, V2 | `test_every_pass_agrees_in_both_loops[deck, flight, climb, lost, gameover]` | every pass of the five scripts, both loops |
| V1, V2 | `test_the_night_mission_agrees_in_both_loops` | the flight script as a night mission |
| V2 at 1 and 3 | `test_the_closed_loop_holds_at_other_pass_rates[1, 3]` | the lost script's 600 ticks with its restart, one and three VBlanks per pass |
| setup | `test_the_setup_agrees_at_step_s` | everything but the setup tick's writes, at S |
| V3 | `test_every_address_a_mission_writes_is_compared_or_excluded` | see "The completeness list" |
| V4 | `tests/test_mission.py` | the setup on thirteen maps laid over map a, on all fifteen under their own numbers, and for the first mission of every rank, with the map file the loader opens |
| V5 | `tests/test_oracle_m4.py` | `rect_fill` on 5 and 4 planes under the pass's clips; `shape_blit` without a mask for every dashboard shape and every fifth world shape; the digit and drum slices |
| V6 | `tests/test_oracle_m4.py` | the ticker, the game-over countdown for every count, the gauge resets for every count, `deck_span`, `ship_at_offset`, `clip_to_waterline`, the 3-D view's cursor, whole state |
| V7 | `tests/test_state_m4.py` | a state saved 160 VBlanks into a mission continues identically, loaded into the same and into a fresh core, native and wasm; both targets save the same bytes |

The controls, each run by changing the port and reverting it:

- the drawing's player x plus 8 in `snapshot_for_draw`: the calls, the map draws and the
  state differ from pass 1;
- `0xFF60` in the view's formula changed to `0xFF68`: the calls and `view_x` differ from
  pass 1 (the map strip is placed by the drawing's x, not by `view_x`, on both sides);
- the first `rand_beam` of `0x014D50` skipped: pass 424 of the climb script draws one
  value fewer than the original, named with its caller, and `rand_state` differs;
- one row of the completeness list removed: the test names the range and its writer;
- the arena's clearing removed: `wof_alloc` after a reset hands out old bytes;
- positively, the closed loop holds at one and three VBlanks per pass as it does at two.

### The completeness list

`tests/m4complete.py` sorts every address the original writes during a mission outside
its tick - in the setup, in a pass, in a VBlank server, in the main program between them -
into three kinds: a registered field; state the port keeps in another form and compares by
another check (the double buffer as the index of the view in front, the colour tables as
the palette of every row); or state the port does not keep, with the reason and the
milestone. Each row names the routines that write its range, and a write by any other one
makes the address uncovered again. The runs are the five scripts, the night mission, and
the `guns` and `bomb` scripts of `re/notes/passes.md`, which reach the ricochets, the
soldiers and the targets.

What is not kept, by reason: the graphics library's structures (the views, the
viewports, their RastPorts and BitMaps, the drawing target, the plane pointers), which the
port's screen model replaces (`SPEC.md` section 6.6); the copper lists and their
bookkeeping, whose effect is the palette of every row; the blitter's parameter block and
`MaskBuffer`, which the port's blits do not need; the loader's result registers; two
pointers that always point at the same global (`player_record`, `0x027DF4`); the
allocator's headers; the files as they are read; the sound engine's state and the sample
pointers, M8's; and the planes of the dashboard picture, which the port unpacks with M3's
decoder.

The couplings of `re/notes/passes.md` that no run reached:

- **The score from a soldier's death** (`0x013EEE`): not carried; `soldiers_draw` is M5's
  stand-in beyond an empty walk.
- **The player's record `+0x12`** (the oil): not written by any pass of the port, and in the
  runs no pass of the original wrote it either; `0x014F5C`'s path that could is M5's
  stand-in.
- **`frame_update`'s call of `player_lost_restart`**: not carried; it is a stand-in, since
  the guard `0x024F24` is set by the tick.

## What stands in, and where

A stand-in is marked `M4 PART 2 STAND-IN`, `M5 STAND-IN` and so on, with the first address
or the range of what it stands for. Reaching one counts `wof_standin_hits` in the state,
which the diagnostics overlay shows; in test builds it is also logged, and every comparison
fails on any stand-in reached. In the release build a reached stand-in does the least
harmful thing it can: it skips what it stands for.

- **The tick** is the largest: it pops its input byte unless the game is paused, so that the
  queue's arithmetic is the original's, and does nothing else. In test builds it waits the
  VBlanks the comparison tells it to; the release core has neither the waits nor any other
  test hook (`test_the_release_core_has_no_test_hooks` reads the name section of
  `dist/core.wasm`).
- **`ingame_keys`** takes every waiting key out of the buffer and remembers the last in
  `last_key`, as its path without a command does. Its commands are part 2's. While the
  tick is a stand-in, the key E (raw `0x12`), without Control, sets `quit_flag` so that a
  mission can be left for the high scores and the rank selection; the hint bar and the
  overlay say so. Every other key during a mission counts as a stand-in reached.
- **The next mission of a campaign** (`0x010132` to `0x01018D`) ends the campaign instead.
- **`sounds_load`** opens the files in the original's order and keeps their lengths; the
  sound slots it builds and `soundfx_vblank` are M8's.
- Every other region is listed with its marker in "Appendix: the regions no run executed".

## What is provisional

- **The pass rate**, 2 VBlanks per pass, until the user's slow-motion film of the real
  machine settles it; the closed loop holding at 1 and 3 says the logic does not depend on
  it.
- **The tick's waits** exist only to line a replayed schedule up; part 2 replaces them with
  the tick's own `WaitTOF` loops.
- **The ticker's message bytes** are read from `ticker_text` and `ticker_text_2` and from
  the constant DATA hunk; a message anywhere else is a stand-in until part 2 shows where
  the tick points it.
- **The ship-block reader** gives 0 for a word past the four lists; no map reaches that, and
  a count of 0 for a carried ship, which would, faults the original.
- **No pixel of the mission scene is compared with the original**, because the headless
  original runs no blits. The drawing calls, the palette of every row and the blitter model
  together stand for it; a blitter in the headless original would allow a direct check.

## Facts the other notes share

- The player's record is `0x1E` bytes, and the 160 words behind it from `0x025096` are the
  ships' blocks of deck planes (`re/notes/objects.md`, "The player's record").
- The order of the ship records: destroyer, battleship, cruise ship, Japanese carrier, the
  player's carrier (`re/notes/map.md`, the first walk).
- `choose_night` runs only between two missions of a campaign, and the ticker's messages are
  formatted by the tick into two BSS buffers (`re/notes/display.md`).

## Appendix: the reach map

Entries per routine, window and phase, for the five scripts, as
`.venv/bin/python tools/reach_observe.py --markdown TABLE.md` writes them (observed).

### The head of the outer loop, before the rank selection

| Routine | Address | `deck` | `flight` | `climb` | `lost` | `gameover` |
|---|---|---|---|---|---|---|
| `free_mission_assets` | `011234` | 1 | 1 | 1 | 1 | 1 |
| `mem_free_var` | `0124e0` | 16 | 16 | 16 | 16 | 16 |
| `shapes_free` | `012502` | 1 | 1 | 1 | 1 | 1 |
| `free_map` | `012bbe` | 1 | 1 | 1 | 1 | 1 |
| `sub_01346c` | `01346c` | 1 | 1 | 1 | 1 | 1 |
| `sub_0134a4` | `0134a4` | 1 | 1 | 1 | 1 | 1 |
| `sub_0134ae` | `0134ae` | 1 | 1 | 1 | 1 | 1 |
| `campaign_reset` | `013562` | 1 | 1 | 1 | 1 | 1 |
| `mission_reset_tables` | `0135a8` | 1 | 1 | 1 | 1 | 1 |
| `player_lost_restart` | `0135d8` | 1 | 1 | 1 | 1 | 1 |
| `player_restart_state` | `013684` | 1 | 1 | 1 | 1 | 1 |
| `sub_013756` | `013756` | 1 | 1 | 1 | 1 | 1 |
| `shape_mirror_x` | `015b58` | 2 | 2 | 2 | 2 | 2 |
| `aircraft_frame` | `01abde` | 1 | 1 | 1 | 1 | 1 |
| `deck_span` | `01b7bc` | 1 | 1 | 1 | 1 | 1 |
| `player_reset` | `01b7ec` | 1 | 1 | 1 | 1 | 1 |
| `sub_01b9bc` | `01b9bc` | 1 | 1 | 1 | 1 | 1 |
| `rand_mod` | `01cac8` | 1 | 1 | 1 | 1 | 1 |
| `sub_01cb30` | `01cb30` | 4 | 4 | 4 | 4 | 4 |
| `aircraft_clear` | `01e608` | 1 | 1 | 1 | 1 | 1 |
| `weapon_gauge_reset` | `01edbc` | 1 | 1 | 1 | 1 | 1 |
| `lives_gauge_reset` | `01edea` | 1 | 1 | 1 | 1 | 1 |
| `rand_beam` | `0203be` | 1 | 1 | 1 | 1 | 1 |
| `shape_find_c` | `0204f4` | 4 | 4 | 4 | 4 | 4 |
| `shape_find` | `020560` | 4 | 4 | 4 | 4 | 4 |

### After the rank selection, before the briefing

| Routine | Address | `deck` | `flight` | `climb` | `lost` | `gameover` |
|---|---|---|---|---|---|---|
| `sub_0129c8` | `0129c8` | 1 | 1 | 1 | 1 | 1 |
| `map_load` | `012adc` | 1 | 1 | 1 | 1 | 1 |
| `airfields_scan` | `012c84` | 1 | 1 | 1 | 1 | 1 |
| `map_scan` | `012d5a` | 1 | 1 | 1 | 1 | 1 |
| `sub_0131c8` | `0131c8` | 2 | 2 | 2 | 2 | 2 |
| `sub_013216` | `013216` | 2 | 2 | 2 | 2 | 2 |
| `airfields_clear` | `013554` | 1 | 1 | 1 | 1 | 1 |
| `mem_alloc_asm` | `0158ec` | 5 | 5 | 5 | 5 | 5 |
| `shapes_load` | `015bc6` | 1 | 1 | 1 | 1 | 1 |
| `shapes_resolve` | `015c5c` | 1 | 1 | 1 | 1 | 1 |
| `load_file_public_asm` | `015d3e` | 1 | 1 | 1 | 1 | 1 |
| `load_file_chip_asm` | `015d50` | 1 | 1 | 1 | 1 | 1 |
| `load_dash_assets` | `01653c` | 1 | 1 | 1 | 1 | 1 |
| `sub_0165c4` | `0165c4` | 1 | 1 | 1 | 1 | 1 |
| `load_file_public` | `01feb4` | 1 | 1 | 1 | 1 | 1 |
| `load_file_chip` | `01feca` | 1 | 1 | 1 | 1 | 1 |
| `load_file` | `01ff16` | 2 | 2 | 2 | 2 | 2 |
| `shape_find` | `020560` | 117 | 117 | 117 | 117 | 117 |
| `mem_alloc` | `020848` | 7 | 7 | 7 | 7 | 7 |
| `sub_020874` | `020874` | 9 | 9 | 9 | 9 | 9 |
| `mem_free` | `02090a` | 2 | 2 | 2 | 2 | 2 |
| `os_dos_close` | `022aae` | 2 | 2 | 2 | 2 | 2 |
| `sub_022ab2` | `022ab2` | 2 | 2 | 2 | 2 | 2 |
| `os_dos_examine` | `022ada` | 2 | 2 | 2 | 2 | 2 |
| `os_dos_lock` | `022b1a` | 2 | 2 | 2 | 2 | 2 |
| `os_dos_open` | `022b2c` | 2 | 2 | 2 | 2 | 2 |
| `sub_022b30` | `022b30` | 2 | 2 | 2 | 2 | 2 |
| `os_dos_read` | `022b3e` | 4 | 4 | 4 | 4 | 4 |
| `os_dos_unlock` | `022b50` | 2 | 2 | 2 | 2 | 2 |
| `sub_022d36` | `022d36` | 9 | 9 | 9 | 9 | 9 |
| `sub_022d3a` | `022d3a` | 9 | 9 | 9 | 9 | 9 |
| `sub_022d86` | `022d86` | 2 | 2 | 2 | 2 | 2 |
| `sub_022d8a` | `022d8a` | 2 | 2 | 2 | 2 | 2 |

### Mission setup, main program: the briefing's end to step S

| Routine | Address | `deck` | `flight` | `climb` | `lost` | `gameover` |
|---|---|---|---|---|---|---|
| `input_queue_clear` | `01174a` | 1 | 1 | 1 | 1 | 1 |
| `sub_011f76` | `011f76` | 1 | 1 | 1 | 1 | 1 |
| `load_ship_shapes` | `013252` | 1 | 1 | 1 | 1 | 1 |
| `sounds_load` | `013368` | 1 | 1 | 1 | 1 | 1 |
| `mission_reset_tables` | `0135a8` | 1 | 1 | 1 | 1 | 1 |
| `player_lost_restart` | `0135d8` | 1 | 1 | 1 | 1 | 1 |
| `player_restart_state` | `013684` | 2 | 2 | 2 | 2 | 2 |
| `sub_013756` | `013756` | 2 | 2 | 2 | 2 | 2 |
| `build_master_lists` | `01535a` | 1 | 1 | 1 | 1 | 1 |
| `file_length` | `015b1a` | 8 | 8 | 8 | 8 | 8 |
| `load_file_public_asm` | `015d3e` | 2 | 2 | 2 | 2 | 2 |
| `load_file_chip_asm` | `015d50` | 8 | 8 | 8 | 8 | 8 |
| `vport_init_bitmap` | `0167f2` | 4 | 4 | 4 | 4 | 4 |
| `view_layout` | `01692c` | 2 | 2 | 2 | 2 | 2 |
| `ticker_vport_init` | `016bd8` | 1 | 1 | 1 | 1 | 1 |
| `view_set_game` | `016c38` | 2 | 2 | 2 | 2 | 2 |
| `screen_game` | `016cc6` | 1 | 1 | 1 | 1 | 1 |
| `cmap_file_to_table` | `016dd6` | 2 | 2 | 2 | 2 | 2 |
| `cop_add_ticker_ramp` | `0187ba` | 2 | 2 | 2 | 2 | 2 |
| `mission_display_setup` | `018806` | 1 | 1 | 1 | 1 | 1 |
| `cop_reset` | `019958` | 6 | 6 | 6 | 6 | 6 |
| `cop_move` | `0199bc` | 290 | 290 | 290 | 290 | 290 |
| `cop_move_ptr` | `019a08` | 96 | 96 | 96 | 96 | 96 |
| `cop_wait` | `019a9c` | 78 | 78 | 78 | 78 | 78 |
| `cop_colours` | `019b5a` | 14 | 14 | 14 | 14 | 14 |
| `cop_vport_colours` | `019c0a` | 14 | 14 | 14 | 14 | 14 |
| `cop_vport_split` | `019c80` | 4 | 4 | 4 | 4 | 4 |
| `cop_vport_planes` | `019d18` | 14 | 14 | 14 | 14 | 14 |
| `cop_sprites_off` | `01a06c` | 6 | 6 | 6 | 6 | 6 |
| `view_build_copper` | `01a0d4` | 6 | 6 | 6 | 6 | 6 |
| `iff_cmap_to_table` | `01a1f6` | 1 | 1 | 1 | 1 | 1 |
| `iff_next_chunk` | `01a336` | 8 | 8 | 8 | 8 | 8 |
| `iff_body_to_vport` | `01a362` | 1 | 1 | 1 | 1 | 1 |
| `iff_parse_ilbm` | `01a452` | 1 | 1 | 1 | 1 | 1 |
| `iff_to_vport` | `01a548` | 1 | 1 | 1 | 1 | 1 |
| `view_poke_colours1` | `01a60e` | 3 | 3 | 3 | 3 | 3 |
| `view_poke_colours2` | `01a6ac` | 1 | 1 | 1 | 1 | 1 |
| `vport_clear_planes` | `01a74c` | 1 | 1 | 1 | 1 | 1 |
| `view_copy_bitmaps` | `01a834` | 1 | 1 | 1 | 1 | 1 |
| `view_copy_colours` | `01a8c4` | 1 | 1 | 1 | 1 | 1 |
| `view_copy` | `01a9ca` | 1 | 1 | 1 | 1 | 1 |
| `cop_show_wait` | `01a9fc` | 2 | 2 | 2 | 2 | 2 |
| `cop_install` | `01aa0e` | 2 | 2 | 2 | 2 | 2 |
| `wait_vblank` | `01aa3e` | 2 | 2 | 2 | 2 | 2 |
| `aircraft_frame` | `01abde` | 2 | 2 | 2 | 2 | 2 |
| `deck_span` | `01b7bc` | 2 | 2 | 2 | 2 | 2 |
| `player_reset` | `01b7ec` | 2 | 2 | 2 | 2 | 2 |
| `sub_01b9bc` | `01b9bc` | 2 | 2 | 2 | 2 | 2 |
| `rand_mod` | `01cac8` | 2 | 2 | 2 | 2 | 2 |
| `sub_01cb30` | `01cb30` | 288 | 288 | 288 | 288 | 288 |
| `enemy_frames` | `01d1ea` | 1 | 1 | 1 | 1 | 1 |
| `dash_cache_invalidate` | `01ed7a` | 2 | 2 | 2 | 2 | 2 |
| `dashboard_invalidate` | `01edaa` | 1 | 1 | 1 | 1 | 1 |
| `weapon_gauge_reset` | `01edbc` | 2 | 2 | 2 | 2 | 2 |
| `load_file_public` | `01feb4` | 2 | 2 | 2 | 2 | 2 |
| `load_file_chip` | `01feca` | 8 | 8 | 8 | 8 | 8 |
| `rpck_unpack` | `01fee0` | 1 | 1 | 1 | 1 | 1 |
| `load_file` | `01ff16` | 10 | 10 | 10 | 10 | 10 |
| `rand_beam` | `0203be` | 2 | 2 | 2 | 2 | 2 |
| `byterun1_row` | `0203e8` | 148 | 148 | 148 | 148 | 148 |
| `shape_find_c` | `0204f4` | 288 | 288 | 288 | 288 | 288 |
| `shape_find` | `020560` | 288 | 288 | 288 | 288 | 288 |
| `mem_alloc` | `020848` | 11 | 11 | 11 | 11 | 11 |
| `sub_020874` | `020874` | 21 | 21 | 21 | 21 | 21 |
| `mem_free` | `02090a` | 14 | 14 | 14 | 14 | 14 |
| `sub_0223cc` | `0223cc` | 1 | 1 | 1 | 1 | 1 |
| `sub_022424` | `022424` | 1 | 1 | 1 | 1 | 1 |
| `os_dos_close` | `022aae` | 10 | 10 | 10 | 10 | 10 |
| `sub_022ab2` | `022ab2` | 10 | 10 | 10 | 10 | 10 |
| `os_dos_examine` | `022ada` | 10 | 10 | 10 | 10 | 10 |
| `os_dos_lock` | `022b1a` | 10 | 10 | 10 | 10 | 10 |
| `os_dos_open` | `022b2c` | 10 | 10 | 10 | 10 | 10 |
| `sub_022b30` | `022b30` | 10 | 10 | 10 | 10 | 10 |
| `os_dos_read` | `022b3e` | 20 | 20 | 20 | 20 | 20 |
| `os_dos_unlock` | `022b50` | 10 | 10 | 10 | 10 | 10 |
| `sub_022d36` | `022d36` | 21 | 21 | 21 | 21 | 21 |
| `sub_022d3a` | `022d3a` | 21 | 21 | 21 | 21 | 21 |
| `sub_022d86` | `022d86` | 14 | 14 | 14 | 14 | 14 |
| `sub_022d8a` | `022d8a` | 14 | 14 | 14 | 14 | 14 |
| `gfx_BltBitMap` | `022e0c` | 3 | 3 | 3 | 3 | 3 |
| `gfx_BltClear` | `022e2e` | 7 | 7 | 7 | 7 | 7 |
| `gfx_InitBitMap` | `022e5a` | 5 | 5 | 5 | 5 | 5 |
| `gfx_InitRastPort` | `022e6c` | 5 | 5 | 5 | 5 | 5 |

### Mission setup, the tick main runs itself (part 2)

| Routine | Address | `deck` | `flight` | `climb` | `lost` | `gameover` |
|---|---|---|---|---|---|---|
| `sub_010a72` | `010a72` | 1 | 1 | 1 | 1 | 1 |
| `sub_011274` | `011274` | 1 | 1 | 1 | 1 | 1 |
| `logic_tick` | `011386` | 1 | 1 | 1 | 1 | 1 |
| `sub_011510` | `011510` | 1 | 1 | 1 | 1 | 1 |
| `sub_011622` | `011622` | 1 | 1 | 1 | 1 | 1 |
| `input_queue_pop` | `011714` | 1 | 1 | 1 | 1 | 1 |
| `sub_0119bc` | `0119bc` | 1 | 1 | 1 | 1 | 1 |
| `sub_011bfc` | `011bfc` | 1 | 1 | 1 | 1 | 1 |
| `sub_011c5e` | `011c5e` | 1 | 1 | 1 | 1 | 1 |
| `sub_011cae` | `011cae` | 1 | 1 | 1 | 1 | 1 |
| `sub_011de4` | `011de4` | 1 | 1 | 1 | 1 | 1 |
| `sub_012066` | `012066` | 1 | 1 | 1 | 1 | 1 |
| `sub_012132` | `012132` | 1 | 1 | 1 | 1 | 1 |
| `sub_0122ce` | `0122ce` | 1 | 1 | 1 | 1 | 1 |
| `sub_01b5b0` | `01b5b0` | 1 | 1 | 1 | 1 | 1 |
| `sub_01b682` | `01b682` | 1 | 1 | 1 | 1 | 1 |
| `sub_01bc02` | `01bc02` | 1 | 1 | 1 | 1 | 1 |
| `sub_01c660` | `01c660` | 1 | 1 | 1 | 1 | 1 |
| `sub_01e7d6` | `01e7d6` | 1 | 1 | 1 | 1 | 1 |
| `sub_01ea28` | `01ea28` | 3 | 3 | 3 | 3 | 3 |
| `sub_01eac0` | `01eac0` | 2 | 2 | 2 | 2 | 2 |
| `sub_01eb2e` | `01eb2e` | 3 | 3 | 3 | 3 | 3 |
| `os_disable` | `022d48` | 1 | 1 | 1 | 1 | 1 |
| `os_enable` | `022d66` | 1 | 1 | 1 | 1 | 1 |

### Mission setup, VBlank servers

| Routine | Address | `deck` | `flight` | `climb` | `lost` | `gameover` |
|---|---|---|---|---|---|---|
| `vblank_server` | `011754` | 2 | 2 | 2 | 2 | 2 |
| `vblank_every_frame` | `01c9ca` | 2 | 2 | 2 | 2 | 2 |
| `soundfx_vblank` | `01ec64` | 2 | 2 | 2 | 2 | 2 |
| `poll_fire` | `02044c` | 2 | 2 | 2 | 2 | 2 |
| `read_fire_button` | `02046a` | 2 | 2 | 2 | 2 | 2 |

### A pass during a mission: `frame_update`'s tree (phase F)

| Routine | Address | `deck` | `flight` | `climb` | `lost` | `gameover` |
|---|---|---|---|---|---|---|
| `frame_update` | `010228` | 934 | 1134 | 1324 | 1224 | 2682 |
| `flip_buffers` | `01030c` | 934 | 1134 | 1324 | 1224 | 2682 |
| `weapon_marker` | `010344` | 934 | 1134 | 1324 | 1224 | 2682 |
| `draw_player` | `0103a6` | 934 | 1134 | 1324 | 1224 | 2682 |
| `draw_objects` | `0106be` | 934 | 1134 | 1324 | 1224 | 2682 |
| `sub_010702` | `010702` | 0 | 0 | 105 | 112 | 266 |
| `draw_enemy_aircraft` | `010da6` | 934 | 1134 | 1324 | 1224 | 2682 |
| `smoke_draw` | `010ee0` | 934 | 1134 | 1324 | 1224 | 2682 |
| `snapshot_for_draw` | `010f88` | 934 | 1134 | 1324 | 1224 | 2682 |
| `draw_game_over` | `0110c2` | 934 | 1134 | 1324 | 1224 | 2682 |
| `draw_world` | `013772` | 934 | 1134 | 1324 | 1224 | 2682 |
| `ship_planes` | `01391e` | 934 | 1134 | 1324 | 1224 | 2682 |
| `airfields_draw` | `013a18` | 934 | 1134 | 1324 | 1224 | 2682 |
| `deck_aircraft` | `013abc` | 934 | 1134 | 1324 | 1224 | 2682 |
| `record_extras` | `013b1c` | 68182 | 71197 | 75576 | 84982 | 185308 |
| `targets_3_draw` | `013d78` | 934 | 1134 | 1324 | 1224 | 2682 |
| `targets_f_draw` | `013de8` | 934 | 1134 | 1324 | 1224 | 2682 |
| `ocean` | `013e6c` | 934 | 1134 | 1324 | 1224 | 2682 |
| `soldiers_draw` | `013eee` | 934 | 1134 | 1324 | 1224 | 2682 |
| `lift_aircraft` | `01409c` | 934 | 1134 | 1324 | 1224 | 2682 |
| `islands_draw` | `0140e8` | 934 | 1134 | 1324 | 1224 | 2682 |
| `map_window` | `01417e` | 934 | 1134 | 1324 | 1224 | 2682 |
| `window_height` | `0141b4` | 934 | 423 | 786 | 1224 | 2682 |
| `window_strip` | `014206` | 934 | 423 | 786 | 1224 | 2682 |
| `window_ship` | `014430` | 934 | 423 | 786 | 1224 | 2682 |
| `window_background` | `014564` | 934 | 1134 | 1324 | 1224 | 2682 |
| `ship_at_offset` | `014a4e` | 8406 | 5141 | 5446 | 9194 | 19612 |
| `ship_at_span` | `014a52` | 9340 | 5454 | 5764 | 10086 | 21486 |
| `ship_guns_draw` | `014c3e` | 934 | 1134 | 1324 | 1224 | 2682 |
| `target_frame` | `014d50` | 1868 | 2268 | 2648 | 2448 | 5364 |
| `target_range_frame` | `014db8` | 0 | 228 | 304 | 40 | 120 |
| `ride_on_ship` | `014eac` | 8406 | 5141 | 5446 | 9194 | 19612 |
| `target_fire` | `014f5c` | 0 | 698 | 524 | 0 | 0 |
| `sub_015078` | `015078` | 2 | 2 | 2 | 2 | 2 |
| `sub_015090` | `015090` | 16 | 16 | 16 | 16 | 16 |
| `flip_view` | `0150b0` | 934 | 1134 | 1324 | 1224 | 2682 |
| `draw_world_shape` | `015174` | 3736 | 5618 | 6779 | 5115 | 9647 |
| `sub_01520c` | `01520c` | 934 | 1134 | 1324 | 1224 | 2682 |
| `clip_playfield` | `01524a` | 2802 | 2691 | 3434 | 3672 | 8344 |
| `clip_dash_window` | `01525c` | 934 | 1134 | 1324 | 1224 | 2682 |
| `clip_to_waterline` | `01526e` | 934 | 1518 | 2066 | 1830 | 4312 |
| `splashes_draw` | `0152f8` | 934 | 1134 | 1324 | 1224 | 2682 |
| `balloons_draw` | `01557c` | 934 | 1134 | 1324 | 1224 | 2682 |
| `view_show` | `016f20` | 934 | 1134 | 1324 | 1224 | 2682 |
| `cop_set_split_line` | `01876e` | 934 | 1134 | 1324 | 1224 | 2682 |
| `cop_wait` | `019a9c` | 934 | 1134 | 1324 | 1224 | 2682 |
| `cop_install` | `01aa0e` | 934 | 1134 | 1324 | 1224 | 2682 |
| `wait_vblank` | `01aa3e` | 934 | 1134 | 1324 | 1224 | 2682 |
| `record_on_ship` | `01cb34` | 0 | 4 | 4 | 4 | 12 |
| `ship_of_record` | `01cbf2` | 0 | 4 | 4 | 4 | 12 |
| `draw_dashboard` | `01ee16` | 934 | 1134 | 1324 | 1224 | 2682 |
| `kill_icons` | `01f200` | 4 | 4 | 4 | 4 | 4 |
| `enemy_arrows` | `01f21a` | 934 | 1134 | 1324 | 1224 | 2682 |
| `draw_score` | `01f26a` | 2 | 2 | 2 | 2 | 2 |
| `dash_digit` | `01f2b0` | 18 | 18 | 18 | 18 | 18 |
| `clip_dashboard` | `01f2dc` | 1868 | 2268 | 2648 | 2448 | 5364 |
| `rand_beam` | `0203be` | 0 | 1422 | 1076 | 0 | 0 |
| `shape_find` | `020560` | 0 | 0 | 0 | 0 | 298 |
| `blit_clip_setup` | `0209bc` | 24322 | 12372 | 15396 | 27217 | 57970 |
| `shape_blit` | `020b0c` | 24322 | 12372 | 15396 | 27217 | 57970 |
| `shape_draw` | `020ce2` | 22434 | 12274 | 15288 | 25961 | 55846 |
| `rect_fill` | `021010` | 3736 | 5247 | 5834 | 4896 | 10728 |
| `draw_set_target` | `02124a` | 2802 | 3402 | 3972 | 3672 | 8344 |
| `clip_set` | `02129c` | 6538 | 7611 | 9472 | 9174 | 20702 |
| `blit_begin` | `0212ce` | 7472 | 7977 | 9312 | 9186 | 20124 |
| `blit_end` | `0212d4` | 7472 | 7977 | 9312 | 9186 | 20124 |
| `sub_022e40` | `022e40` | 7472 | 7977 | 9312 | 9186 | 20124 |
| `sub_022e8a` | `022e8a` | 7472 | 7977 | 9312 | 9186 | 20124 |

### A VBlank during a mission (phase V)

| Routine | Address | `deck` | `flight` | `climb` | `lost` | `gameover` |
|---|---|---|---|---|---|---|
| `vblank_server` | `011754` | 1869 | 2269 | 2647 | 2447 | 5359 |
| `read_joy_bits` | `01520e` | 468 | 568 | 662 | 612 | 1341 |
| `vblank_every_frame` | `01c9ca` | 1869 | 2269 | 2647 | 2447 | 5359 |
| `read_joystick` | `01ca32` | 468 | 568 | 662 | 612 | 1341 |
| `read_joy_dispatch` | `01cb20` | 468 | 568 | 662 | 612 | 1341 |
| `soundfx_vblank` | `01ec64` | 1869 | 2269 | 2647 | 2447 | 5359 |
| `poll_fire` | `02044c` | 1869 | 2269 | 2647 | 2447 | 5359 |
| `read_fire_button` | `02046a` | 1869 | 2269 | 2647 | 2447 | 5359 |

### The inner loop beside `frame_update` during a mission (phase M)

| Routine | Address | `deck` | `flight` | `climb` | `lost` | `gameover` |
|---|---|---|---|---|---|---|
| `run_queued_ticks` | `0114d8` | 934 | 1134 | 1324 | 1224 | 2682 |
| `ingame_keys` | `01ccf6` | 935 | 1135 | 1325 | 1225 | 2682 |
| `key_available` | `0207d8` | 935 | 1135 | 1325 | 1225 | 2682 |

### The tick during a mission (phase T, part 2)

| Routine | Address | `deck` | `flight` | `climb` | `lost` | `gameover` |
|---|---|---|---|---|---|---|
| `flip_buffers` | `01030c` | 0 | 0 | 1 | 1 | 2 |
| `object_spawn` | `010820` | 0 | 0 | 15 | 16 | 38 |
| `sub_010a72` | `010a72` | 467 | 567 | 667 | 617 | 1351 |
| `sub_010aa6` | `010aa6` | 0 | 0 | 60 | 64 | 152 |
| `sub_011274` | `011274` | 467 | 567 | 667 | 617 | 1351 |
| `sub_0112b0` | `0112b0` | 454 | 554 | 647 | 590 | 1310 |
| `logic_tick` | `011386` | 467 | 567 | 667 | 617 | 1351 |
| `sub_011460` | `011460` | 454 | 554 | 647 | 590 | 1310 |
| `sub_011510` | `011510` | 467 | 567 | 667 | 617 | 1351 |
| `sub_011622` | `011622` | 467 | 567 | 667 | 617 | 1351 |
| `input_queue_pop` | `011714` | 467 | 567 | 667 | 617 | 1351 |
| `vblank_server` | `011754` | 0 | 0 | 21 | 21 | 42 |
| `sub_0119bc` | `0119bc` | 467 | 567 | 667 | 617 | 1351 |
| `sub_011bfc` | `011bfc` | 467 | 567 | 667 | 617 | 1351 |
| `sub_011c5e` | `011c5e` | 467 | 567 | 667 | 617 | 1351 |
| `sub_011cae` | `011cae` | 467 | 567 | 667 | 617 | 1351 |
| `sub_011de4` | `011de4` | 467 | 567 | 667 | 617 | 1351 |
| `sub_011f4e` | `011f4e` | 0 | 1 | 1 | 1 | 3 |
| `sub_012066` | `012066` | 467 | 568 | 668 | 618 | 1354 |
| `sub_012132` | `012132` | 467 | 567 | 667 | 617 | 1351 |
| `sub_0122ce` | `0122ce` | 467 | 567 | 667 | 617 | 1351 |
| `sub_0122f6` | `0122f6` | 0 | 0 | 0 | 1 | 3 |
| `sub_012306` | `012306` | 0 | 0 | 0 | 1 | 3 |
| `sub_012324` | `012324` | 0 | 0 | 0 | 1 | 3 |
| `sub_012354` | `012354` | 0 | 1 | 1 | 1 | 3 |
| `sub_0135ce` | `0135ce` | 0 | 0 | 1 | 1 | 3 |
| `player_lost_restart` | `0135d8` | 0 | 0 | 1 | 1 | 3 |
| `player_restart_state` | `013684` | 0 | 0 | 1 | 1 | 2 |
| `sub_013756` | `013756` | 0 | 0 | 1 | 1 | 2 |
| `flip_view` | `0150b0` | 0 | 0 | 1 | 1 | 2 |
| `map_slot_at` | `0150c8` | 0 | 0 | 22 | 16 | 48 |
| `sub_01520c` | `01520c` | 0 | 0 | 1 | 1 | 2 |
| `read_joy_bits` | `01520e` | 0 | 0 | 5 | 5 | 10 |
| `clip_playfield` | `01524a` | 0 | 0 | 1 | 1 | 2 |
| `sub_0152ac` | `0152ac` | 0 | 0 | 22 | 16 | 48 |
| `sub_0152b0` | `0152b0` | 0 | 0 | 22 | 16 | 48 |
| `sub_015710` | `015710` | 0 | 547 | 480 | 145 | 435 |
| `ground_height` | `015714` | 0 | 547 | 480 | 145 | 435 |
| `shape_mirror_x` | `015b58` | 0 | 24 | 26 | 28 | 82 |
| `view_show` | `016f20` | 0 | 0 | 1 | 1 | 2 |
| `cop_install` | `01aa0e` | 0 | 0 | 1 | 1 | 2 |
| `sub_01aa6e` | `01aa6e` | 0 | 0 | 1 | 0 | 0 |
| `sub_01aaea` | `01aaea` | 0 | 959 | 1008 | 333 | 905 |
| `sub_01ab80` | `01ab80` | 0 | 0 | 1 | 0 | 0 |
| `aircraft_frame` | `01abde` | 0 | 548 | 642 | 305 | 820 |
| `sub_01aed8` | `01aed8` | 0 | 0 | 150 | 150 | 356 |
| `sub_01af7c` | `01af7c` | 0 | 0 | 150 | 150 | 356 |
| `sub_01afba` | `01afba` | 0 | 0 | 11 | 9 | 27 |
| `sub_01b45a` | `01b45a` | 0 | 548 | 641 | 304 | 818 |
| `sub_01b4de` | `01b4de` | 0 | 413 | 346 | 11 | 33 |
| `sub_01b5b0` | `01b5b0` | 467 | 567 | 667 | 617 | 1351 |
| `sub_01b682` | `01b682` | 467 | 567 | 667 | 617 | 1351 |
| `deck_span` | `01b7bc` | 0 | 0 | 1 | 1 | 2 |
| `player_reset` | `01b7ec` | 0 | 0 | 1 | 1 | 2 |
| `sub_01b8c4` | `01b8c4` | 0 | 412 | 345 | 10 | 30 |
| `sub_01b92e` | `01b92e` | 0 | 104 | 104 | 104 | 312 |
| `sub_01b9bc` | `01b9bc` | 0 | 0 | 1 | 1 | 2 |
| `sub_01b9cc` | `01b9cc` | 0 | 1 | 1 | 1 | 3 |
| `sub_01b9f0` | `01b9f0` | 0 | 412 | 345 | 10 | 30 |
| `sub_01ba80` | `01ba80` | 0 | 412 | 345 | 10 | 30 |
| `sub_01bc02` | `01bc02` | 467 | 567 | 667 | 617 | 1351 |
| `sub_01bcce` | `01bcce` | 0 | 516 | 449 | 114 | 342 |
| `sub_01bdba` | `01bdba` | 0 | 104 | 104 | 104 | 312 |
| `player_motion` | `01bdfa` | 0 | 412 | 345 | 10 | 30 |
| `sub_01bff4` | `01bff4` | 0 | 412 | 345 | 10 | 30 |
| `sub_01c378` | `01c378` | 0 | 548 | 641 | 304 | 818 |
| `sub_01c4e8` | `01c4e8` | 0 | 104 | 104 | 104 | 312 |
| `sub_01c5f4` | `01c5f4` | 0 | 104 | 104 | 104 | 312 |
| `sub_01c660` | `01c660` | 467 | 567 | 667 | 617 | 1351 |
| `sub_01c982` | `01c982` | 0 | 959 | 1011 | 337 | 907 |
| `vblank_every_frame` | `01c9ca` | 0 | 0 | 21 | 21 | 42 |
| `read_joystick` | `01ca32` | 0 | 0 | 5 | 5 | 10 |
| `rand_mod` | `01cac8` | 0 | 0 | 1 | 1 | 2 |
| `read_joy_dispatch` | `01cb20` | 0 | 0 | 5 | 5 | 10 |
| `sub_01cb30` | `01cb30` | 0 | 2613 | 2931 | 1401 | 3730 |
| `sub_01cb74` | `01cb74` | 0 | 0 | 13 | 11 | 33 |
| `sub_01e7d6` | `01e7d6` | 467 | 567 | 667 | 617 | 1351 |
| `sub_01ea28` | `01ea28` | 0 | 9 | 12 | 12 | 36 |
| `sub_01eac0` | `01eac0` | 0 | 12 | 17 | 17 | 53 |
| `sub_01eb2e` | `01eb2e` | 0 | 9 | 12 | 12 | 36 |
| `sub_01eb4c` | `01eb4c` | 0 | 96 | 248 | 89 | 267 |
| `soundfx_vblank` | `01ec64` | 0 | 0 | 21 | 21 | 42 |
| `weapon_gauge_reset` | `01edbc` | 0 | 0 | 1 | 1 | 2 |
| `rand_beam` | `0203be` | 0 | 0 | 1 | 1 | 2 |
| `poll_fire` | `02044c` | 0 | 0 | 21 | 21 | 42 |
| `read_fire_button` | `02046a` | 0 | 0 | 21 | 21 | 42 |
| `sub_0204e4` | `0204e4` | 0 | 548 | 641 | 304 | 818 |
| `sub_0204ec` | `0204ec` | 0 | 548 | 641 | 304 | 818 |
| `shape_find_c` | `0204f4` | 0 | 2613 | 2931 | 1401 | 3730 |
| `shape_find` | `020560` | 0 | 2613 | 2931 | 1401 | 3730 |
| `rect_fill` | `021010` | 0 | 0 | 1 | 1 | 2 |
| `draw_set_target` | `02124a` | 0 | 0 | 1 | 1 | 2 |
| `clip_set` | `02129c` | 0 | 0 | 1 | 1 | 2 |
| `blit_begin` | `0212ce` | 0 | 0 | 1 | 1 | 2 |
| `blit_end` | `0212d4` | 0 | 0 | 1 | 1 | 2 |
| `ffp_add` | `021c9c` | 0 | 412 | 345 | 10 | 30 |
| `ffp_neg` | `021cb0` | 0 | 0 | 129 | 9 | 27 |
| `ffp_fix` | `021cc4` | 0 | 1236 | 1035 | 30 | 90 |
| `ffp_div` | `021cd8` | 0 | 824 | 690 | 20 | 60 |
| `ffp_flt` | `021ce2` | 0 | 824 | 690 | 20 | 60 |
| `ffp_mul` | `021cec` | 0 | 1236 | 1035 | 30 | 90 |
| `sub_021d7c` | `021d7c` | 0 | 1 | 1 | 1 | 1 |
| `sub_021e24` | `021e24` | 0 | 0 | 30 | 30 | 70 |
| `sub_0222f4` | `0222f4` | 0 | 0 | 30 | 30 | 70 |
| `os_disable` | `022d48` | 467 | 567 | 667 | 617 | 1351 |
| `os_enable` | `022d66` | 467 | 567 | 667 | 617 | 1351 |
| `sub_022e40` | `022e40` | 0 | 0 | 1 | 1 | 2 |
| `sub_022e8a` | `022e8a` | 0 | 0 | 1 | 1 | 2 |
| `gfx_WaitTOF` | `022eee` | 0 | 0 | 21 | 21 | 42 |

### Entropy reads, by the routine that called `rand_beam`

| Window | Phase | Caller | `deck` | `flight` | `climb` | `lost` | `gameover` |
|---|---|---|---|---|---|---|---|
| outer | M | `rand_mod` | 1 | 1 | 1 | 1 | 1 |
| setup | M | `rand_mod` | 2 | 2 | 2 | 2 | 2 |
| mission | F | `target_frame` | 0 | 1422 | 1076 | 0 | 0 |
| mission | T | `rand_mod` | 0 | 0 | 1 | 1 | 2 |


## Appendix: the regions no run executed

Every region of an M4 routine that neither the five scripts nor the setups of the fifteen
maps executed, with the stand-in marker that covers it or what it is otherwise; below them,
the markers whose region the original did run (in its tick, which is part 2's, or on a value
no script produced) and the markers that stand for a value rather than a region. Written by

```text
.venv/bin/python tools/reach_observe.py --blocks --setups --json REACH.json
.venv/bin/python tools/reach_observe.py --cold REACH.json
```

| Routine | Region no run executed | Stand-in marker, or what it is | Owed to |
|---|---|---|---|
| `main` `0x010006` | `0x010036`-`0x010041` | M3's: the command line's demo file, which the port has no command line for | |
| `main` `0x010006` | `0x010104`-`0x010109` | ported from reading: `demo_mode` sets `0x026D44` before step S | |
| `main` `0x010006` | `0x010132`-`0x01018D` | `0x010132`-`0x01018D`, the next mission of a campaign | M4 PART 2 |
| `main` `0x010006` | `0x010196`-`0x01019D` | ported from reading: a paused mission waits for the next VBlank | |
| `main` `0x010006` | `0x0101B4`-`0x0101BD` | ported from reading: a demo ends on the fire button | |
| `main` `0x010006` | `0x01020A`-`0x01020D` | ported from reading: back to the outer loop after the high scores | |
| `frame_update` `0x010228` | `0x0102BC`-`0x0102CD` | `0x0102BC`, `frame_update`'s call of `player_lost_restart` | M4 PART 2 |
| `flip_buffers` `0x01030C` | `0x010322`-`0x010331` | ported from reading: the flash of `flip_buffers` | |
| `draw_player` `0x0103A6` | `0x01043E`-`0x01045B` | unreachable: no branch leads there | |
| `draw_player` `0x0103A6` | `0x01047E`-`0x0104C3` | `0x01047E`, the aircraft at an attitude, eighth scale | M4 PART 2 |
| `draw_player` `0x0103A6` | `0x0104D4`-`0x0104D5` | ported from reading: the climb clamped at -2 in the eighth-scale view | |
| `draw_player` `0x0103A6` | `0x01052A`-`0x01054F` | `0x01052A`, the torpedo under a level aircraft | M5 |
| `draw_player` `0x0103A6` | `0x01058C`-`0x01058D` | ported from reading | |
| `draw_player` `0x0103A6` | `0x0105CA`-`0x0105FD` | `0x0105CA`, the hook's line on the lift | M4 PART 2 |
| `draw_player` `0x0103A6` | `0x010610`-`0x010635` | `0x010610`, the torpedo under a banked aircraft | M5 |
| `draw_player` `0x0103A6` | `0x010642`-`0x0106B3` | `0x010642`, the exclusive-or frame of `0x02536A` | M4 PART 2 |
| `draw_objects` `0x0106BE` | `0x0106CC`-`0x0106CF` | ported from reading: `0x02536C` cleared | |
| `draw_objects` `0x0106BE` | `0x0106F6`-`0x0106F9` | ported from reading: the extra object record drawn | |
| `sub_010702` `0x010702` | `0x010726`-`0x010779` | `0x010726`, an object of another type | M5 |
| `sub_010702` `0x010702` | `0x0107C2`-`0x0107C5` | `0x0107C2`, an object in the eighth-scale view | M5 |
| `draw_enemy_aircraft` `0x010DA6` | `0x010DBA`-`0x010E15` | `0x010DBA`, the formation words of `0x0251D8` | M6 |
| `draw_enemy_aircraft` `0x010DA6` | `0x010E26`-`0x010ED1` | `0x010E26`, an enemy aircraft | M6 |
| `smoke_draw` `0x010EE0` | `0x010F2A`-`0x010F6F` | `0x010F2A`, a smoke record | M5 |
| `draw_game_over` `0x0110C2` | `0x011118`-`0x011123` | ported from reading; tests/`test_oracle_m4.py`, every count | |
| `choose_night` `0x0111FC` | `0x0111FC`-`0x011233` | ported from reading; reached only between two missions, part 2 | |
| `run_queued_ticks` `0x0114D8` | `0x0114E0`-`0x0114E5` | `0x0114E0`, `run_queued_ticks`, demo playback and recording | M7 |
| `run_queued_ticks` `0x0114D8` | `0x0114EE`-`0x0114EF` | ported from reading: nothing runs while paused | |
| `run_queued_ticks` `0x0114D8` | `0x011508`-`0x01150D` | ported from reading: `demo_mode` sets `0x026D44` | |
| `vblank_server` `0x011754` | `0x011790`-`0x0117D3` | M3's input half: demo playback (M7) | |
| `vblank_server` `0x011754` | `0x01180A`-`0x011841` | M3's input half: demo recording (M7) | |
| `vblank_server` `0x011754` | `0x011856`-`0x0118D3` | ported from reading; tests/`test_oracle_m4.py`, the ticker | |
| `vblank_server` `0x011754` | `0x0118DE`-`0x01195D` | ported from reading; tests/`test_oracle_m4.py`, the ticker | |
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
| `draw_world` `0x013772` | `0x01382E`-`0x01383D` | ported from reading: records before the map's start stepped over | |
| `draw_world` `0x013772` | `0x0138F2`-`0x013913` | ported from reading: the distance handed to the sound engine | |
| `ship_planes` `0x01391E` | `0x01395A`-`0x01396B` | `0x01395A`, the last ship's clip at full scale | M6 |
| `ship_planes` `0x01391E` | `0x013976`-`0x0139B7` | `0x013976`, aircraft on a ship's deck | M6 |
| `ship_planes` `0x01391E` | `0x0139CE`-`0x013A0D` | `0x0139D6`, the japanese carrier's crane | M6 |
| `airfields_draw` `0x013A18` | `0x013A36`-`0x013AB1` | `0x013A36`, an airfield in view | M6 |
| `deck_aircraft` `0x013ABC` | `0x013ADA`-`0x013ADB` | ported from reading: more than nine lives count as nine | |
| `record_extras` `0x013B1C` | `0x013B52`-`0x013BCD` | `0x013B52`, an island's flag | M5 |
| `targets_3_draw` `0x013D78` | `0x013D92`-`0x013DA9` | `0x013D92`, a destroyed slot-3 target | M5 |
| `targets_3_draw` `0x013D78` | `0x013DB2`-`0x013DB9` | `0x013DB2`, a slot-3 target's count | M5 |
| `targets_f_draw` `0x013DE8` | `0x013DFA`-`0x013E61` | `0x013DFA`, the slot-`0x0F` targets | M5 |
| `soldiers_draw` `0x013EEE` | `0x013F0A`-`0x01408B` | `0x013F0A`, a soldier | M5 |
| `window_strip` `0x014206` | `0x014244`-`0x01424D` | `0x014244`, the 3-D view over an enemy ship | M6 |
| `window_strip` `0x014206` | `0x0142AC`-`0x01430B` | `0x0142BC`, an enemy aircraft in the 3-D view | M6 |
| `window_strip` `0x014206` | `0x01434C`-`0x01437B` | `0x01434C`, a map record in the 3-D view | M4 PART 2 |
| `window_strip` `0x014206` | `0x014382`-`0x014383` | `0x014382`, land in the 3-D view | M4 PART 2 |
| `window_strip` `0x014206` | `0x014390`-`0x0143A3` | reached only after the stand-in at `0x014382` set D7 (M4 PART 2) | |
| `window_strip` `0x014206` | `0x0143AE`-`0x0143DD` | reached only after the stand-in at `0x01434C` set `0x0253DA` (M4 PART 2) | |
| `window_strip` `0x014206` | `0x0143E6`-`0x014411` | reached only after the stand-in at `0x01434C` set `0x0253D8` (M4 PART 2) | |
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
| `target_fire` `0x014F5C` | `0x014F72`-`0x014FE7` | `0x014F72`, a target near the aircraft | M5 |
| `splashes_draw` `0x0152F8` | `0x015334`-`0x01533B` | `0x015334`, a splash of kind 2 | M5 |
| `balloons_draw` `0x01557C` | `0x015584`-`0x015621` | `0x015584`, the balloons | M5 |
| `load_dash_assets` `0x01653C` | `0x016568`-`0x01656B` | dash.shp missing, fatal; the port loads every container at start-up | |
| `demo_end` `0x01852A` | `0x018536`-`0x01855D` | `0x018536`, saving a recorded demo | M7 |
| `aircraft_frame` `0x01ABDE` | `0x01AC42`-`0x01AC59` | `0x01ABEC`-`0x01ACE3`, states 0 and 4 | M4 PART 2 |
| `aircraft_frame` `0x01ABDE` | `0x01AC6C`-`0x01AC83` | `0x01ABEC`-`0x01ACE3`, states 0 and 4 | M4 PART 2 |
| `aircraft_frame` `0x01ABDE` | `0x01ACAA`-`0x01ACDF` | `0x01ABEC`-`0x01ACE3`, states 0 and 4 | M4 PART 2 |
| `record_on_ship` `0x01CB34` | `0x01CB50`-`0x01CB51` | ported from reading: a record at the list's end is on no ship | |
| `record_on_ship` `0x01CB34` | `0x01CB70`-`0x01CB71` | ported from reading: a record of other low bits is on no ship | |
| `ship_of_record` `0x01CBF2` | `0x01CC04`-`0x01CC0F` | `0x01CC04`, a record on no ship | M4 PART 2 |
| `ship_of_record` `0x01CBF2` | `0x01CC68`-`0x01CCB5` | `0x01CC68`, a ship record not found | M4 PART 2 |
| `ingame_keys` `0x01CCF6` | `0x01CD04`-`0x01CE27` | `0x01CD04`-`0x01CE27`, `ingame_keys`, a key during a mission | M4 PART 2 |
| `lives_gauge_reset` `0x01EDEA` | `0x01EDF4`-`0x01EDF5` | ported from reading; tests/`test_oracle_m4.py`, the gauge resets | |
| `lives_gauge_reset` `0x01EDEA` | `0x01EDFE`-`0x01EDFF` | ported from reading; tests/`test_oracle_m4.py`, the gauge resets | |
| `draw_dashboard` `0x01EE16` | `0x01EEB8`-`0x01EED1` | `0x01EEB8`, the oil warning | M4 PART 2 |
| `draw_dashboard` `0x01EE16` | `0x01EF32`-`0x01EF33` | `0x01EF32`, fuel below zero | M4 PART 2 |
| `draw_dashboard` `0x01EE16` | `0x01EF48`-`0x01EF5B` | `0x01EF48`, the empty tank's needle | M4 PART 2 |
| `draw_dashboard` `0x01EE16` | `0x01EF68`-`0x01EF6F` | ported from reading: the fuel needle moving down | |
| `draw_dashboard` `0x01EE16` | `0x01EF8C`-`0x01EFA5` | `0x01EF8C`, the fuel warning | M4 PART 2 |
| `draw_dashboard` `0x01EE16` | `0x01F062`-`0x01F065` | `0x01F062`, unlimited weapons | M5 |
| `draw_dashboard` `0x01EE16` | `0x01F07A`-`0x01F0AD` | `0x01F07A`, the weapon counter's drums turning | M5 |
| `draw_dashboard` `0x01EE16` | `0x01F102`-`0x01F103` | `0x01F102`, negative lives | M4 PART 2 |
| `draw_dashboard` `0x01EE16` | `0x01F10C`-`0x01F10D` | `0x01F10C`, more than nine lives | M4 PART 2 |
| `draw_dashboard` `0x01EE16` | `0x01F12E`-`0x01F133` | `0x01F12E`, the lives drum turning down | M4 PART 2 |
| `draw_dashboard` `0x01EE16` | `0x01F186`-`0x01F187` | `0x01F186`, the enemy plane counter above 99 | M5 |
| `draw_dashboard` `0x01EE16` | `0x01F1DA`-`0x01F1DB` | ported from reading: the first row of bars clamped at seven | |
| `draw_dashboard` `0x01EE16` | `0x01F1EE`-`0x01F1EF` | ported from reading: the second row of bars clamped at seven | |
| `kill_icons` `0x01F200` | `0x01F206`-`0x01F217` | `0x01F206`, the enemy plane counter's kill icons | M5 |
| `enemy_arrows` `0x01F21A` | `0x01F226`-`0x01F235` | `0x01F226`-`0x01F269`, an arrow to an enemy aircraft | M6 |
| `enemy_arrows` `0x01F21A` | `0x01F240`-`0x01F269` | `0x01F226`-`0x01F269`, an arrow to an enemy aircraft | M6 |
| | run by the original | `0x013638`, `player_lost_restart`'s clear, flip and wait | M4 PART 2 |
| | run by the original | `0x01ACEA`, state 1 or 11 with `0x025A9C` set | M4 PART 2 |
| | run by the original | `0x01ADFE`-`0x01AEB3`, the other states | M4 PART 2 |
| | no region: a value | more than four islands, in `0x0140E8` | M6 |
| | no region: a value | a negative score, in `0x01F26A` | M7 |
| | no region: a value | a ticker message outside the registered state | M4 PART 2 |
