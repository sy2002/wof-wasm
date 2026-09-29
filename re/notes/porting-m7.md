# M7: the campaign and the saved game

Milestone M7 of `SPEC.md` section 9, in two parts. Part 1, this note: everything from a
mission won to the next mission's first ticks, the promotion after a rank's last mission,
and the saved game's layout and its writer. Part 2, later: the loader on both of its paths,
the demo, the two markers that stand for values, and the page. What the campaign and the
saved game are, observed, is `re/notes/campaign.md`. Addresses use the standard load layout.

Every statement is either **observed**, with the tool or test that shows it, or **read**,
which means it comes from the listing alone.

```text
src/front.c              main's next mission (0x010132-0x01018D) as the mission coroutine's
                         continuation into its reset (0x0100D2); the poke point 0x0100AE
src/dialog.c             save_nothing, save_write_part, save_game_write and save_walk
                         (0x015D62-0x016030), beside M3's dialog; the save in the dialog
src/core.c               the byte of the original's memory at an address, of a registered
                         global, a fixed table or a pool (wof_original_load8, wof_pool_load8)
src/mission.c            choose_night reads mission_map_table by address
src/screen.c             screen_game_restore makes the play screen the one drawn again
src/fs.c                 a written file up to WOF_SAVE_MAX, the largest saved game
src/globals.def          briefing_islands and briefing_ships, named by what they count
src/trace.c, tests/shim.c
                         a third poke point, where main has run map_load (0x0100AE)
tools/m7_autopilot.py    the autopilot: a script that wins its mission replayed to the next
                         mission's hold, then an M6 plan; the save in the hold; the chain
tools/m7_scripts.py      the M7 scripts, and the campaign tick by tick while one runs
tools/m7_runs.py         the flown tails (tools/m7_autopilot.py --all writes it)
tools/savegame.py        the saved game's layout: a file's pieces, what it holds, its fields
tools/m7_controls.py     the controls, each built into a library of its own
tools/reach_observe.py   the reach map, with --m7 and --m7-only
tests/test_campaign.py   every M7 script in the closed and the attributed open loop, one at
                         three pass rates; the saved file byte for byte; the completeness list
tests/test_oracle_m7.py  mission_won, choose_night and the walker against the original; the
                         disk's saved game decoded
tests/m4compare.py       the recorder follows a mission won into the next one; the third poke
tests/m4complete.py      the rows the save dialog and the next mission add (M7_EXCLUDED)
```

## What decides what is ported: the reach map

The M7 scripts are the six of `tools/m7_scripts.py` ("The scripts" below). The reach map
runs them beside every run of M4 to M6 and joins the two for the cold regions (observed):

```text
.venv/bin/python tools/reach_observe.py --m6 --blocks --setups --jobs 5 --json REACH456.json
.venv/bin/python tools/reach_observe.py --m7-only --blocks --jobs 5 --json REACH7.json
.venv/bin/python tools/reach_observe.py --m7-only --load REACH7.json --markdown TABLE.md
.venv/bin/python tools/reach_observe.py --cold REACH456.json REACH7.json
```

### The cut between the parts (observed)

What the six M7 scripts executed that no run of M4 to M6 did, by phase, over the joined
runs (the blocks of `REACH7.json` that no block of `REACH456.json` covers):

- **Phase F:** `mission_won`'s promotion (`0x0156B2` to `0x0156E7`), called by the pass
  when the last island is neutralised (`promote_a`, `cap_a`); `draw_dashboard`'s drum
  turning down for a life more (`0x01F12E`); two blocks of `line_draw`, the cable of
  `save_a`'s landing.
- **Phase T:** `mission_won` called by `ship_sinking` (`0x011D28`), the last enemy ship
  gone with no island left, with its promotion (`ships_j`), and the blocks of
  `ship_sunk_message` and `ticker_offer` around it.
- **Phase M, between two missions:** `main`'s extra Hellcat (`0x01015C`), `choose_night`'s
  night branch (`0x011218`), and `free_map`'s release of three of the four enemy ships
  (`0x012BF6`, `0x012C1A`, `0x012C62`; the cruise ship's, `0x012C3E`, no script runs).
- **Phase M, in a mission:** the save: `ingame_keys`' Control-G on the carrier
  (`0x01CD92`), the dialog's save with the typing and the rename's test
  (`load_save_dialog`, `text_input`, `strcmp`), `save_game_write`, `save_walk`'s piece
  for a ship (`0x015F5A`), `save_write_part`, `os_dos_write` with the `dos.Write` glue,
  and `screen_game_restore`, which no script had run before.
- **Phase M, the rank selection:** `night_again`'s second rank selection runs out after
  1,800 rounds and asks for the demo (`rank_select` `0x018456` on, `menu_input`'s 1000,
  `load_file` of `wofdemo`, which is not on the disk, and `IoErr`), so the mission starts
  with `demo_mode` back at 0. M3 ported that fall-back and its front-end tests hold it; the
  demo itself is part 2's.
- **Phase V:** nothing new.

All of it but the demo is part 1's. Every routine among them was ported before M7 except
the saved game's writer, which part 1 adds; the next mission's path in `main` was M4's
stand-in. Part 2's regions are the loader's and the demo's, which no script of part 1 runs
(the cold list below). Over all the runs, M4 to M7 and the fifteen setups, 438 of the 616
routines are entered; the six M7 scripts enter 408, 13,059,113 times, and `--cold` finds
no region without a marker or a note.

## The scripts

Each is a raw schedule for the headless original, flown by a plan of
`tools/m7_autopilot.py` and kept in `tools/m7_runs.py` as its base, the VBlanks of the base
replayed and the tail the autopilot chose after them; `tools/m7_scripts.py trace NAME`
prints the mission, the rank and the mission number, the player, the lives, the score,
`balloons_on`, `night_flag`, the won flag (`0x0253BC`), the weapon menu and the balloons in
use tick by tick. A plan either starts from a script of M4 or M5 whose run goes on to
another mission, `island_a`'s win or `gameover`'s game over, replayed to 40 VBlanks into
the next mission's hold, or flies from the front end as an M6 plan does. The promotion and the rank's cap are reached with the mission
number and the rank poked where `main` has run `map_load` for a campaign's first mission
(`0x0100AE`, a third poke point beside the rank selection's end and the mission's reset, on
both sides), as `balloons_c` pokes `balloons_on`: map a won as a rank's last mission; no
rank with one mission (ranks 4 and 5, maps k and l) has a map the autopilot can win, each
having three islands and enemy ships (`re/notes/enemy.md`, "The fifteen maps").

| Script | What it flies | Ticks | Missions |
|---|---|---|---|
| `save_a` | map f (the second rank chosen, the mission number 3 poked at the rank selection's end): out east to the island at 11536-12712, a bomb on its first barracks and one on its first dug-out (+350), back to the carrier from the east, the landing on a cable, the taxi and the lift down; in the hold Control-G, the cursor down to the dialog's empty second slot, `save` typed and Return: `wof.save`, 6,424 bytes; then the lift, the take-off and out east | 1,547 | 1 |
| `ships_j` | the fourth rank chosen, the mission number 2 poked (map j), and after every mission's reset (`0x0100D6`) every enemy ship's hits and the islands left poked to 0: the aircraft waits in the hold while the ships sink, and the last one at ten rows wins the mission (`ship_sinking` `0x011D28`); j, k and l are each their rank's last mission, so three promotions follow one another, m and n go on to the next mission, o's promotion keeps the rank at 6 and goes back to m | 190 | 8 |
| `night_again` | M4's `gameover` (every aircraft lost) as a night mission, `night_flag` poked to 1 once, at the first rank selection's end only; then nothing: the high-score screen and the rank selection run out by themselves (1,800 rounds each, and `wofdemo` is not on the disk), and the next campaign's first mission, map a, begins at night; 400 VBlanks into its hold | 1,459 | 2 |
| `chain_a` | `island_a`'s win of map a, the aircraft into the ground and the next one in the hold: the fade, map b's briefing and setup (the first rank's second mission), then the lift, the take-off, east over the sea and back | 5,174 | 2 |
| `promote_a` | the same with the mission number poked to 3 after `map_load`: map a won as the first rank's last mission, the promotion, the balloons over the carrier, the extra Hellcat, and the second rank's first mission, map d | 5,134 | 2 |
| `cap_a` | the same with the rank poked to 6 and the mission number to 3: the promotion keeps the rank at 6, and the next mission is its first, map m, at night (`choose_night` draws for maps above 6) | 5,155 | 2 |

The enemy's countdown (`0x01BC02`) is left alone: `island_a`'s own flight keeps it up with
the button in its turns as every M5 script does, and no M7 flight after the switch lasts
long enough for it to run out (observed: no aircraft record is set in any of the six).
The three scripts built on `island_a` run with `--slow`.

What the scripts do not reach, after a real attempt:

- **Two wins in a row by play.** The plan `win_b` flies `island_a`'s win of map a on into
  map b and clears both of its islands sortie after sortie, bombing every target that
  holds soldiers and hunting the soldiers with the guns, with a landing between the
  sorties (`tools/m7_autopilot.py`, the M5 attack with its landings), the lives poked to 5
  and then 9 after `map_load`. Neither won: the first lost its last Hellcat at tick
  12,125, 7,569 ticks into map b, with 10,900 points (its process ran 32 minutes, some ten
  of them in the front end after the game over, where the autopilot then did not stop);
  the second, with nine Hellcats and the hunt at 30 pixels, lost its last with 20,725
  points (its process ran about an hour, the front end's wait after the game over again
  among it; the autopilot now ends a flight at a game over). The dug-outs' fire takes the
  oil during the low hunts and the soldiers the bombs let out keep coming, as `win_c`
  found on map c (`re/notes/porting-m5.md`); the harness's run limit of 1,800 s never
  stopped a run. `chain_a` and `ships_j` stand for the chain instead: `ships_j` makes it
  with pokes, eight missions and seven wins, and is the script the pass rates run.
- **A weapon in flight at the save.** Control-G saves only on the carrier (`player_on_deck`
  1, `ingame_keys` `0x01CD86`): a bomb comes down within some twenty ticks of its drop, and
  a torpedo runs 200 ticks, while from a drop east of the carrier the landing policy needs
  the turn, the approach from the east and the cable, well over 200 ticks. An enemy
  torpedo lives in the extra object record (`0x025594`), which lies beyond the raw part and
  is never saved (`re/notes/campaign.md`).

## The port

- **The next mission** (`main` `0x010132` to `0x01018D`, `src/front.c`): the inner loop's
  test of the weapon menu and `0x0253BC` now goes on to the next mission in the mission
  coroutine itself, in the original's order (`re/notes/campaign.md`, "The next mission"):
  the flags cleared, the sound slots, the ticker, `fade_out_pair`,
  `free_mission_assets`, a Hellcat more if `balloons_on` is set, `choose_night`,
  `dashboard_invalidate`, `map_load`, the briefing (a Control-R there goes back to the
  outer loop's head, `mission_end` 2), `load_dash_assets`, `mission_display_setup`,
  `load_ship_shapes`, `build_master_lists`, `sounds_load`, and a `goto` into the reset of
  the mission's own setup, as `0x01018A` branches to `0x0100D2`. The coroutine keeps no local
  across the waits. The port's trace marks the next mission's setup as it marks the
  first one's, and step S counts the missions on, which is how the comparison finds each
  mission's S.
- **`choose_night`** reads `mission_map_table` by address with the original's signed word
  index (`SPEC.md` section 7.1), where the port had a modulo of the table's length; the
  oracle's cases read past the table.
- **The saved game's writer** (`src/dialog.c`, in the original's order beside M3's dialog):
  `save_nothing` (`0x015D62`), `save_write_part` (`0x015DDE`), `save_game_write`
  (`0x015E8A`) and `save_walk` (`0x015EC2`), which the load will share. The write callback
  takes each byte of the original's memory from the port's registered state by its
  address (`wof_original_load8`, `src/core.c`: a global, a table at a fixed address) or,
  for a flag-1 piece, from the pool behind the pointer's address (`wof_pool_load8`), and
  the executable's image where the port keeps nothing, which is what the original holds
  where nothing writes. A pointer's four bytes are the long of what the port keeps in its
  place: the shape handle, or 1 for an allocation (`re/notes/campaign.md`, "What the port
  writes in the raw part"). The walker's side effect on `map_extent` and `map_records_end`
  is ported. The file is assembled in scratch memory at the arena's top and handed to the
  file system in one piece, under the dialog's name; as the original walks nothing when
  Open fails, the port walks nothing when its file system could not keep the file (its
  overlay full, `wof_fs_can_write`). The file system's largest file is now
  `WOF_SAVE_MAX`, 12,412 bytes, the largest save the port's tables allow (the largest map,
  m, saves 11,516), where it was 8,192 and a save on maps h, i and k to o would not have
  been kept.
- **`screen_game_restore`** (`0x016D32`, `src/screen.c`), ported from reading in M4 and
  first run with passes after it by `save_a`: the dialog's own screen had switched the
  port's play-screen model off, and nothing switched it on again, so after a save the
  port drew the playfield without its split's colours and the ticker without its ramp
  (observed: 997 passes of `save_a`'s closed loop differed in the rows below the split
  and the ticker's, and in nothing else). It now marks both views as play screens again
  and, as `view_build_copper` rebuilds the back view's list, drops a COLOR01 poke of the
  back view's.
- **The briefing's two numbers** are named by what they count, `briefing_islands`
  (`0x025382`) and `briefing_ships` (`0x025370`).

## How the port is held to the original

| Check | Test | What it covers |
|---|---|---|
| T2 | `tests/test_campaign.py::test_every_tick_and_pass_agrees_in_the_closed_loop[...]` | every M7 script in the closed loop, from the program's start with nothing handed over but the entropy and the map list's addresses: after every tick and every pass the registered state, the drawing calls, the entropy with its callers, the view, the palette of every row, the markers, the map draws, the sound events and Paula agree, and no stand-in is reached, through the win, the fade, the briefing, the next mission's setup and its first ticks to the script's end, and through the save in the hold and the flight after it (the three built on `island_a` with `--slow`) |
| T2 at 1 and 3 | `test_the_closed_loop_holds_at_other_pass_rates[ships_j-1, ships_j-3]` (slow) | the chain of eight missions at one and three VBlanks per pass against the original run at the same rate; `island_a`'s flight wins only at two (observed: at three it does not win) |
| T1, attributed | `test_every_pass_agrees_and_every_other_difference_is_owed[...]` | the open loop over every M7 script: a step that differs must have reached a stand-in of M7 part 2 or of M8 in that same step (none differs, none is reached) |
| file | `test_the_saved_file_is_the_originals_but_for_its_pointers[save_a]` | `save_a`'s `wof.save` against the file the headless original wrote in the same run, byte for byte, with the differing bytes listed by field and reason: the four pointer fields of `re/notes/campaign.md` and nothing else |
| T3 | `test_every_address_the_m7_scripts_write_is_compared_or_excluded` | the completeness list over the M7 scripts, below |
| V6 | `tests/test_oracle_m7.py` | `mission_won` over 2,000 states (every rank with the ranks past the table, the next mission, the promotion, the cap, the message over what `ticker_text` holds); `choose_night` over 2,000 (day, the four draws, the index past the table, the entropy consumed); the walker with the write callback over 600 states of random counts, lengths and ships against the original's own writes captured at `dos.Write` under the oracle, with its side effects; `save_game_write` when the file cannot be opened (`0x015EBE`); touched memory compared, and the cases reach every region the scripts do not |
| decode | `test_the_disks_saved_game_is_map_c_as_the_first_ranks_last_mission` | the disk's `wof.mission 3` decoded by the walker's layout: map c, rank 0, mission 3, every table's count, 6,866 bytes exactly |
| T2, M5 | `tests/test_weapons.py::...[island_a]` (slow) | `island_a` in the closed loop now runs through its win into map b to the recording's end |

The controls, each a change of the port in one place, built into a library of its own from
a copy of the sources (`tools/m7_controls.py`, which points the tests at it through
`WOF_CORE_LIBRARY`), run through the test that must catch it, then thrown away; every one
is caught, and the first step where it shows is named:

| Control | Where | Script, test | The first |
|---|---|---|---|
| the extra life of a promotion not given | `src/front.c`, `0x01015C` | `ships_j`, closed loop | tick 30, the setup's own tick of map k after j's promotion: `lives` 3 for 4; from pass 57 the lives drum and its drawing |
| the promotion one mission early (`bgt` for `bge` at `0x0156AE`) | `src/targets.c`, `mission_won` | `ships_j`, closed loop | pass 243, map n won as the last rank's second mission: the port promotes and loads m where the original goes on to o (`mission_number` 1 for 3, `map_length`, the map's draws) |
| the next mission's map one further | `src/front.c`, `0x010168` | `ships_j`, closed loop | pass 57, the first pass of the second mission: the port draws map l's records where the original draws map k's |
| a byte of the saved file's raw part one off (`rank_played`'s low byte) | `src/dialog.c`, `save_write_part` | `save_a`, the saved file | byte 1,809 (`0x0253BF`) 02 for 01, in `rank_played`, which is no pointer |
| the soldiers' block of the saved file a record short | `src/dialog.c`, `save_walk` | `save_a`, the saved file | the file 6,416 bytes for 6,424 |
| `choose_night`'s night branch taken by day (the map number at or above 0 for above 6) | `src/mission.c`, `0x011214` | `chain_a`, closed loop | tick 4,557, the setup's own tick of map b: `rand_state` `0x101A` for `0x66E1`, the four draws the original does not make |

The oracle tests catch the changes to `mission_won`, `choose_night` and the walker as well
(`tests/test_oracle_m7.py`).

## The completeness list

`test_every_address_the_m7_scripts_write_is_compared_or_excluded` takes the rows of M4 to M6
and adds these (`tests/m4complete.py`, `M7_EXCLUDED` and `M7_HEAP`) for what the window
between two missions and the save write; the M5 list takes them too, and M6's rows
beside them, because `island_a` now runs on into its next mission, whose setup loads the
ships' containers again, and the recorder follows it (`tests/m4compare.py`). None is owed
to part 1:

| Address | Writers | What it is | How the port carries it | Owed to |
|---|---|---|---|---|
| `0x02463A` | `load_dash_assets`, `mem_free_var` | `dash_container`, freed with the mission's assets and loaded again by the next setup | every container is loaded at start-up (`src/assets.c`); the dashboard shown is compared as the drawing calls and the rows | M1, M4 |
| `0x0254F8`-`0x025507` | `map_scan`, `mem_free_var` | the pointers to `map_scan`'s four tables, freed with the old map and allocated for the next | the tables live at fixed places (`src/mission.def`) and their records are compared | M4 |
| `0x026C60` | `save_game_write` | `save_handle`, the file's handle | the file system writes the file in one piece; the file is held byte for byte | M7 |
| `0x026D32` | `sprintf`, `0x021608` | the C library's `sprintf`, for the briefing's numbers | `wof_number`; the briefing's text is held by the front end's tests | M3 |
| `0x026D4E` | `mem_free_var` | `demo_buffer_ptr`, freed between the missions | the demo is part 2's | M7 part 2 |
| `0x026E52` | `load_dash_assets`, `mem_free_var` | `dash_shapes`, the dashboard's table of shape pointers | as `dash_container` | M1, M4 |
| `0x026F34`-`0x026F53` | `load_ship_shapes`, `mem_free_var` | the ships' containers, freed between the missions | as M6's row: `ship_loaded` and `MasterList`'s slots | M4 |
| `0x02772E`-`0x027741` | `text_render` | the game font's renderer at work on the briefing | the port draws a text from the font directly (`src/font.c`) | M1, M3 |
| `0x027744`, `0x027C68` | `load_dash_assets` | the dashboard picture's file and its length | a buffer of the port's own (`src/mission.c`) | M4 |
| `0x027748`-`0x027A13` | the screens and the fades | the views and viewports the briefing between two missions and the save dialog lay out, and the play screen after them | as M4's row; the picture after them is compared as the rows | M3, M4 |
| `0x027A18`-`0x027BD7` | as M4's row with `fade_to` and `fade_to_pair` | the colour tables as the fade after a win, the briefing's fades and the dialog's leave them | compared as the rows; the fades are held by M3's test | M3, M4 |
| `0x027C64` | `fade_to`, `fade_to_pair` | `cop_spare` | no copper lists (M5's row) | M3 |
| `0x027C7E`-`0x027DD9` | the dialog's routines | the dialog's six names and their copies | the front end's state, held by `tests/test_front_port.py` | M3 |
| display memory | `shape_draw`, `text_render` | the back view's planes and `MaskBuffer`, where the briefing between two missions draws | no blits in the headless original; the briefing's calls are held by the front end's tests | M1, M3 |

The saved game adds nothing the port does not keep: the raw part's bytes are registered
fields or never written (above).

## What stands in, and where

No stand-in of M7 part 1 is left. The markers of M7 left in the sources are part 2's, and
say so (`M7 PART 2 STAND-IN`): the loaded game from the rank selection (`0x019152`,
`src/dialog.c`) and in flight (`0x01CDD4`, `src/front.c`), the demo's spin in
`run_queued_ticks` (`0x0114E0`) and its saving (`0x018536`), a negative score in
`draw_score` (`0x01F26A`) and a ticker message outside the registered state. The regions
of the routines part 1 ports that no script runs are ported from reading and named in the
cold list below.

## What part 2 must know

- **The loader.** `save_read_part` (`0x015D7C`) reads a flag-0 piece where it lies and for
  a flag-1 piece allocates a new block, reads into it and stores its address; the old
  blocks are not freed, and a short read leaves the pointer. So after a load the raw part
  holds the saving machine's pointers: the three shape pointers and the carrier's gun
  list, which the port's files carry as a handle and a flag, and the disk's file as
  addresses of that Amiga's memory (a handle is at most `0xFFFF`, an address far above);
  the walker's `map_records_end` is the list's end, not a word before it. The loaded
  game's paths: from the rank selection `rank_select` sets `loaded_game` (`0x0183DE`),
  `main` skips `map_load` (`0x0100A2`) and the setup skips the reset
  (`0x0100CA`); in flight `ingame_keys` (`0x01CDD4`) runs `load_dash_assets`, the
  briefing, `0x01EDAA`, `mission_display_setup`, `load_ship_shapes`,
  `build_master_lists`, `sounds_load`, a tick and `input_queue_clear` (read).
  `opt_invert_vertical` comes back with the game, which the port overrides with the
  owner's preference (`SPEC.md` section 6.1).
- **The demo's counter.** `g_026d44`'s setting at step S for a demo (`0x010100`) is on the
  path the next mission shares and is ported with it; `run_queued_ticks`' spin while it is
  set is part 2's stand-in (`0x0114E0`). `free_mission_assets` frees the demo buffer
  (`demo_buffer_ptr`) between missions as well, which the port has none of.
- **The seed.** The generator is seeded only for a demo, from the beam, and the demo file
  keeps no seed (`re/notes/random.md`).
- **What carries over between missions and campaigns**: the balloons in use, frozen, and
  `night_flag`, which only `choose_night` writes (`re/notes/campaign.md`).

## SPEC corrections this part proposes

- Section 9, M7's row: the executable has no end sequence. Proposed deliverable: "Missions,
  ranks, scoring, messages, save and load, demo record and playback; after the last rank's
  last mission the promotion keeps the rank at 6 and the campaign goes on through maps m, n
  and o, each round with a promotion's message, balloons and a Hellcat more, until the last
  Hellcat is lost: the game has no end sequence" (`re/notes/campaign.md`, "The rank's cap,
  and no end"; observed in `cap_a` and `ships_j`).
- Section 6.4: "chosen once per mission by `choose_night` (`0x0111FC`), which `main` calls
  only between two missions of a campaign, so a campaign's first mission is always by day"
  becomes "chosen by `choose_night` (`0x0111FC`), which `main` calls only between two
  missions of a campaign and which alone writes `night_flag`: the program's first campaign
  begins by day, and a campaign begun after a game lost at night begins at night" (observed
  in `night_again`).
- Section 10, point 12: the save-game layout is answered (`re/notes/campaign.md`).
- Section 3.1: `wof.mission 3` is a game saved on map c, the first rank's third mission.
- Section 9's paragraph: M3's front end no longer stands in for the content of a saved
  game, only for its loading.

## Appendix: the reach map

Entries per routine and phase for the six M7 scripts, written from the run above (observed)
with

```text
.venv/bin/python tools/reach_observe.py --m7-only --load REACH7.json --markdown TABLE.md
```

The windows are M4's (`re/notes/porting-m4.md`, "What decides what is ported"); a
mission's setup after a mission won is the window `setup` like the first one's, and
`between` is `main` from `0x010132` to the next briefing.

### The head of the outer loop, before the rank selection

| Routine | Address | `save_a` | `ships_j` | `night_again` | `chain_a` | `promote_a` | `cap_a` |
|---|---|---|---|---|---|---|---|
| `free_mission_assets` | `011234` | 1 | 1 | 2 | 1 | 1 | 1 |
| `mem_free_var` | `0124e0` | 16 | 16 | 32 | 16 | 16 | 16 |
| `shapes_free` | `012502` | 1 | 1 | 2 | 1 | 1 | 1 |
| `free_map` | `012bbe` | 1 | 1 | 2 | 1 | 1 | 1 |
| `sounds_free` | `01346c` | 1 | 1 | 2 | 1 | 1 | 1 |
| `sound_engine_free` | `0134a4` | 1 | 1 | 2 | 1 | 1 | 1 |
| `sub_0134ae` | `0134ae` | 1 | 1 | 2 | 1 | 1 | 1 |
| `campaign_reset` | `013562` | 1 | 1 | 2 | 1 | 1 | 1 |
| `mission_reset_tables` | `0135a8` | 1 | 1 | 2 | 1 | 1 | 1 |
| `player_lost_restart` | `0135d8` | 1 | 1 | 2 | 1 | 1 | 1 |
| `player_restart_state` | `013684` | 1 | 1 | 2 | 1 | 1 | 1 |
| `sub_013756` | `013756` | 1 | 1 | 2 | 1 | 1 | 1 |
| `shape_mirror_x` | `015b58` | 2 | 2 | 4 | 2 | 2 | 2 |
| `aircraft_frame` | `01abde` | 1 | 1 | 2 | 1 | 1 | 1 |
| `deck_span` | `01b7bc` | 1 | 1 | 2 | 1 | 1 | 1 |
| `player_reset` | `01b7ec` | 1 | 1 | 2 | 1 | 1 | 1 |
| `sub_01b9bc` | `01b9bc` | 1 | 1 | 2 | 1 | 1 | 1 |
| `rand_mod` | `01cac8` | 1 | 1 | 2 | 1 | 1 | 1 |
| `sub_01cb30` | `01cb30` | 4 | 4 | 8 | 4 | 4 | 4 |
| `aircraft_clear` | `01e608` | 1 | 1 | 2 | 1 | 1 | 1 |
| `weapon_gauge_reset` | `01edbc` | 1 | 1 | 2 | 1 | 1 | 1 |
| `lives_gauge_reset` | `01edea` | 1 | 1 | 2 | 1 | 1 | 1 |
| `rand_beam` | `0203be` | 1 | 1 | 2 | 1 | 1 | 1 |
| `shape_find_c` | `0204f4` | 4 | 4 | 8 | 4 | 4 | 4 |
| `shape_find` | `020560` | 4 | 4 | 8 | 4 | 4 | 4 |

### After the rank selection, before the briefing

| Routine | Address | `save_a` | `ships_j` | `night_again` | `chain_a` | `promote_a` | `cap_a` |
|---|---|---|---|---|---|---|---|
| `ship_block` | `01252c` | 1 | 2 | 0 | 0 | 0 | 0 |
| `sub_0129c8` | `0129c8` | 1 | 1 | 2 | 1 | 1 | 1 |
| `map_load` | `012adc` | 1 | 1 | 2 | 1 | 1 | 1 |
| `airfields_scan` | `012c84` | 1 | 1 | 2 | 1 | 1 | 1 |
| `map_scan` | `012d5a` | 1 | 1 | 2 | 1 | 1 | 1 |
| `sub_0131c8` | `0131c8` | 6 | 0 | 4 | 2 | 2 | 2 |
| `sub_013216` | `013216` | 6 | 0 | 4 | 2 | 2 | 2 |
| `sub_013236` | `013236` | 6 | 0 | 0 | 0 | 0 | 0 |
| `airfields_clear` | `013554` | 1 | 1 | 2 | 1 | 1 | 1 |
| `mem_alloc_asm` | `0158ec` | 6 | 2 | 10 | 5 | 5 | 5 |
| `shapes_load` | `015bc6` | 1 | 1 | 2 | 1 | 1 | 1 |
| `shapes_resolve` | `015c5c` | 1 | 1 | 2 | 1 | 1 | 1 |
| `load_file_public_asm` | `015d3e` | 1 | 1 | 2 | 1 | 1 | 1 |
| `load_file_chip_asm` | `015d50` | 1 | 1 | 2 | 1 | 1 | 1 |
| `load_dash_assets` | `01653c` | 1 | 1 | 2 | 1 | 1 | 1 |
| `sub_0165c4` | `0165c4` | 1 | 1 | 2 | 1 | 1 | 1 |
| `load_file_public` | `01feb4` | 1 | 1 | 2 | 1 | 1 | 1 |
| `load_file_chip` | `01feca` | 1 | 1 | 2 | 1 | 1 | 1 |
| `load_file` | `01ff16` | 2 | 2 | 4 | 2 | 2 | 2 |
| `shape_find` | `020560` | 117 | 117 | 234 | 117 | 117 | 117 |
| `mem_alloc` | `020848` | 8 | 4 | 14 | 7 | 7 | 7 |
| `sub_020874` | `020874` | 10 | 6 | 18 | 9 | 9 | 9 |
| `mem_free` | `02090a` | 2 | 2 | 4 | 2 | 2 | 2 |
| `os_dos_close` | `022aae` | 2 | 2 | 4 | 2 | 2 | 2 |
| `sub_022ab2` | `022ab2` | 2 | 2 | 4 | 2 | 2 | 2 |
| `os_dos_examine` | `022ada` | 2 | 2 | 4 | 2 | 2 | 2 |
| `os_dos_lock` | `022b1a` | 2 | 2 | 4 | 2 | 2 | 2 |
| `os_dos_open` | `022b2c` | 2 | 2 | 4 | 2 | 2 | 2 |
| `sub_022b30` | `022b30` | 2 | 2 | 4 | 2 | 2 | 2 |
| `os_dos_read` | `022b3e` | 4 | 4 | 8 | 4 | 4 | 4 |
| `os_dos_unlock` | `022b50` | 2 | 2 | 4 | 2 | 2 | 2 |
| `sub_022d36` | `022d36` | 10 | 6 | 18 | 9 | 9 | 9 |
| `sub_022d3a` | `022d3a` | 10 | 6 | 18 | 9 | 9 | 9 |
| `sub_022d86` | `022d86` | 2 | 2 | 4 | 2 | 2 | 2 |
| `sub_022d8a` | `022d8a` | 2 | 2 | 4 | 2 | 2 | 2 |

### Mission setup, main program: the briefing's end to step S

| Routine | Address | `save_a` | `ships_j` | `night_again` | `chain_a` | `promote_a` | `cap_a` |
|---|---|---|---|---|---|---|---|
| `input_queue_clear` | `01174a` | 1 | 8 | 2 | 2 | 2 | 2 |
| `sound_slots_init` | `011f76` | 1 | 8 | 2 | 2 | 2 | 2 |
| `load_ship_shapes` | `013252` | 1 | 8 | 2 | 2 | 2 | 2 |
| `sounds_load` | `013368` | 1 | 8 | 2 | 2 | 2 | 2 |
| `ship_guns_setup` | `01350e` | 1 | 16 | 0 | 0 | 0 | 2 |
| `mission_reset_tables` | `0135a8` | 1 | 8 | 2 | 2 | 2 | 2 |
| `player_lost_restart` | `0135d8` | 1 | 8 | 2 | 2 | 2 | 2 |
| `player_restart_state` | `013684` | 2 | 16 | 4 | 4 | 4 | 4 |
| `sub_013756` | `013756` | 2 | 16 | 4 | 4 | 4 | 4 |
| `build_master_lists` | `01535a` | 1 | 8 | 2 | 2 | 2 | 2 |
| `mem_alloc_asm` | `0158ec` | 2 | 39 | 0 | 1 | 1 | 5 |
| `file_length` | `015b1a` | 8 | 64 | 16 | 16 | 16 | 16 |
| `shape_mirror_x` | `015b58` | 0 | 0 | 2 | 0 | 0 | 0 |
| `shapes_load` | `015bc6` | 1 | 23 | 0 | 1 | 1 | 3 |
| `shapes_resolve` | `015c5c` | 1 | 23 | 0 | 1 | 1 | 3 |
| `load_file_public_asm` | `015d3e` | 2 | 23 | 4 | 5 | 5 | 5 |
| `load_file_chip_asm` | `015d50` | 9 | 87 | 16 | 17 | 17 | 19 |
| `load_dash_assets` | `01653c` | 0 | 7 | 0 | 1 | 1 | 1 |
| `vport_init_bitmap` | `0167f2` | 4 | 32 | 8 | 8 | 8 | 8 |
| `view_layout` | `01692c` | 2 | 16 | 4 | 4 | 4 | 4 |
| `ticker_vport_init` | `016bd8` | 1 | 8 | 2 | 2 | 2 | 2 |
| `view_set_game` | `016c38` | 2 | 16 | 4 | 4 | 4 | 4 |
| `screen_game` | `016cc6` | 1 | 8 | 2 | 2 | 2 | 2 |
| `cmap_file_to_table` | `016dd6` | 2 | 16 | 4 | 4 | 4 | 4 |
| `cop_add_ticker_ramp` | `0187ba` | 2 | 16 | 4 | 4 | 4 | 4 |
| `mission_display_setup` | `018806` | 1 | 8 | 2 | 2 | 2 | 2 |
| `cop_reset` | `019958` | 6 | 48 | 12 | 12 | 12 | 12 |
| `cop_move` | `0199bc` | 290 | 2338 | 592 | 580 | 580 | 586 |
| `cop_move_ptr` | `019a08` | 96 | 768 | 192 | 192 | 192 | 192 |
| `cop_wait` | `019a9c` | 78 | 624 | 156 | 156 | 156 | 156 |
| `cop_colours` | `019b5a` | 14 | 112 | 28 | 28 | 28 | 28 |
| `cop_vport_colours` | `019c0a` | 14 | 112 | 28 | 28 | 28 | 28 |
| `cop_vport_split` | `019c80` | 4 | 32 | 8 | 8 | 8 | 8 |
| `cop_vport_planes` | `019d18` | 14 | 112 | 28 | 28 | 28 | 28 |
| `cop_sprites_off` | `01a06c` | 6 | 48 | 12 | 12 | 12 | 12 |
| `view_build_copper` | `01a0d4` | 6 | 48 | 12 | 12 | 12 | 12 |
| `iff_cmap_to_table` | `01a1f6` | 1 | 8 | 2 | 2 | 2 | 2 |
| `iff_next_chunk` | `01a336` | 8 | 64 | 16 | 16 | 16 | 16 |
| `iff_body_to_vport` | `01a362` | 1 | 8 | 2 | 2 | 2 | 2 |
| `iff_parse_ilbm` | `01a452` | 1 | 8 | 2 | 2 | 2 | 2 |
| `iff_to_vport` | `01a548` | 1 | 8 | 2 | 2 | 2 | 2 |
| `view_poke_colours1` | `01a60e` | 3 | 24 | 6 | 6 | 6 | 6 |
| `view_poke_colours2` | `01a6ac` | 1 | 8 | 2 | 2 | 2 | 2 |
| `vport_clear_planes` | `01a74c` | 1 | 8 | 2 | 2 | 2 | 2 |
| `view_copy_bitmaps` | `01a834` | 1 | 8 | 2 | 2 | 2 | 2 |
| `view_copy_colours` | `01a8c4` | 1 | 8 | 2 | 2 | 2 | 2 |
| `view_copy` | `01a9ca` | 1 | 8 | 2 | 2 | 2 | 2 |
| `cop_show_wait` | `01a9fc` | 2 | 16 | 4 | 4 | 4 | 4 |
| `cop_install` | `01aa0e` | 2 | 16 | 4 | 4 | 4 | 4 |
| `wait_vblank` | `01aa3e` | 2 | 16 | 4 | 4 | 4 | 4 |
| `aircraft_frame` | `01abde` | 2 | 16 | 4 | 4 | 4 | 4 |
| `deck_span` | `01b7bc` | 2 | 16 | 4 | 4 | 4 | 4 |
| `player_reset` | `01b7ec` | 2 | 16 | 4 | 4 | 4 | 4 |
| `sub_01b9bc` | `01b9bc` | 2 | 16 | 4 | 4 | 4 | 4 |
| `rand_mod` | `01cac8` | 2 | 16 | 4 | 4 | 4 | 4 |
| `sub_01cb30` | `01cb30` | 288 | 2304 | 576 | 576 | 576 | 576 |
| `enemy_frames` | `01d1ea` | 1 | 8 | 2 | 2 | 2 | 2 |
| `dash_cache_invalidate` | `01ed7a` | 2 | 2 | 4 | 2 | 2 | 2 |
| `dashboard_invalidate` | `01edaa` | 1 | 1 | 2 | 1 | 1 | 1 |
| `weapon_gauge_reset` | `01edbc` | 2 | 16 | 4 | 4 | 4 | 4 |
| `load_file_public` | `01feb4` | 2 | 23 | 4 | 5 | 5 | 5 |
| `load_file_chip` | `01feca` | 9 | 87 | 16 | 17 | 17 | 19 |
| `rpck_unpack` | `01fee0` | 2 | 8 | 0 | 2 | 2 | 2 |
| `load_file` | `01ff16` | 11 | 110 | 20 | 22 | 22 | 24 |
| `rand_beam` | `0203be` | 2 | 16 | 4 | 4 | 4 | 4 |
| `byterun1_row` | `0203e8` | 148 | 1184 | 296 | 296 | 296 | 296 |
| `shape_find_c` | `0204f4` | 288 | 2304 | 576 | 576 | 576 | 576 |
| `shape_find` | `020560` | 336 | 3871 | 576 | 693 | 693 | 769 |
| `mem_alloc` | `020848` | 15 | 157 | 20 | 25 | 25 | 31 |
| `sub_020874` | `020874` | 26 | 267 | 40 | 47 | 47 | 55 |
| `mem_free` | `02090a` | 16 | 142 | 26 | 30 | 30 | 32 |
| `sub_0223cc` | `0223cc` | 1 | 8 | 2 | 2 | 2 | 2 |
| `sub_022424` | `022424` | 1 | 8 | 2 | 2 | 2 | 2 |
| `os_dos_close` | `022aae` | 11 | 110 | 20 | 22 | 22 | 24 |
| `sub_022ab2` | `022ab2` | 11 | 110 | 20 | 22 | 22 | 24 |
| `os_dos_examine` | `022ada` | 11 | 110 | 20 | 22 | 22 | 24 |
| `os_dos_lock` | `022b1a` | 11 | 110 | 20 | 22 | 22 | 24 |
| `os_dos_open` | `022b2c` | 11 | 110 | 20 | 22 | 22 | 24 |
| `sub_022b30` | `022b30` | 11 | 110 | 20 | 22 | 22 | 24 |
| `os_dos_read` | `022b3e` | 22 | 220 | 40 | 44 | 44 | 48 |
| `os_dos_unlock` | `022b50` | 11 | 110 | 20 | 22 | 22 | 24 |
| `sub_022d36` | `022d36` | 26 | 267 | 40 | 47 | 47 | 55 |
| `sub_022d3a` | `022d3a` | 26 | 267 | 40 | 47 | 47 | 55 |
| `sub_022d86` | `022d86` | 16 | 142 | 26 | 30 | 30 | 32 |
| `sub_022d8a` | `022d8a` | 16 | 142 | 26 | 30 | 30 | 32 |
| `gfx_BltBitMap` | `022e0c` | 3 | 24 | 6 | 6 | 6 | 6 |
| `gfx_BltClear` | `022e2e` | 7 | 56 | 14 | 14 | 14 | 14 |
| `gfx_InitBitMap` | `022e5a` | 5 | 40 | 10 | 10 | 10 | 10 |
| `gfx_InitRastPort` | `022e6c` | 5 | 40 | 10 | 10 | 10 | 10 |

### Mission setup, the tick main runs itself

| Routine | Address | `save_a` | `ships_j` | `night_again` | `chain_a` | `promote_a` | `cap_a` |
|---|---|---|---|---|---|---|---|
| `objects_step` | `010a72` | 1 | 8 | 2 | 2 | 2 | 2 |
| `shot_origin` | `011274` | 1 | 8 | 2 | 2 | 2 | 2 |
| `logic_tick` | `011386` | 1 | 8 | 2 | 2 | 2 | 2 |
| `ship_launches` | `011510` | 1 | 8 | 2 | 2 | 2 | 2 |
| `airfields_step` | `011622` | 1 | 8 | 2 | 2 | 2 | 2 |
| `input_queue_pop` | `011714` | 1 | 8 | 2 | 2 | 2 | 2 |
| `gun_splashes` | `0119bc` | 1 | 8 | 2 | 2 | 2 | 2 |
| `engine_smoke` | `011bfc` | 1 | 8 | 2 | 2 | 2 | 2 |
| `balloons_step` | `011c5e` | 1 | 8 | 2 | 2 | 2 | 2 |
| `ships_sinking` | `011cae` | 1 | 8 | 2 | 2 | 2 | 2 |
| `ship_sinking` | `011cd8` | 0 | 16 | 0 | 0 | 0 | 0 |
| `target_timers` | `011de4` | 1 | 8 | 2 | 2 | 2 | 2 |
| `sound_channels` | `012066` | 1 | 8 | 2 | 2 | 2 | 2 |
| `engine_sound` | `012132` | 1 | 8 | 2 | 2 | 2 | 2 |
| `enemy_loudness` | `0122ce` | 1 | 8 | 2 | 2 | 2 | 2 |
| `button` | `01b5b0` | 1 | 8 | 2 | 2 | 2 | 2 |
| `guns` | `01b682` | 1 | 8 | 2 | 2 | 2 | 2 |
| `enemy_countdown_step` | `01bc02` | 1 | 8 | 2 | 2 | 2 | 2 |
| `player_update` | `01c660` | 1 | 8 | 2 | 2 | 2 | 2 |
| `enemy_aircraft_step` | `01e7d6` | 1 | 8 | 2 | 2 | 2 | 2 |
| `channel_play` | `01ea28` | 3 | 24 | 6 | 6 | 6 | 6 |
| `channel_stop` | `01eac0` | 2 | 16 | 4 | 4 | 4 | 4 |
| `channel_busy` | `01eb2e` | 3 | 24 | 6 | 6 | 6 | 6 |
| `os_disable` | `022d48` | 1 | 8 | 2 | 2 | 2 | 2 |
| `os_enable` | `022d66` | 1 | 8 | 2 | 2 | 2 | 2 |

### Mission setup, VBlank servers

| Routine | Address | `save_a` | `ships_j` | `night_again` | `chain_a` | `promote_a` | `cap_a` |
|---|---|---|---|---|---|---|---|
| `input_queue_pop` | `011714` | 1 | 8 | 0 | 0 | 0 | 0 |
| `vblank_server` | `011754` | 2 | 16 | 4 | 4 | 4 | 4 |
| `vblank_server:ticker_scroll` | `011754` | 0 | 6 | 0 | 1 | 1 | 1 |
| `read_joy_bits` | `01520e` | 1 | 8 | 0 | 0 | 0 | 0 |
| `vblank_every_frame` | `01c9ca` | 2 | 16 | 4 | 4 | 4 | 4 |
| `read_joystick` | `01ca32` | 1 | 8 | 0 | 0 | 0 | 0 |
| `read_joy_dispatch` | `01cb20` | 1 | 8 | 0 | 0 | 0 | 0 |
| `soundfx_vblank` | `01ec64` | 2 | 16 | 4 | 4 | 4 | 4 |
| `poll_fire` | `02044c` | 2 | 16 | 4 | 4 | 4 | 4 |
| `read_fire_button` | `02046a` | 2 | 16 | 4 | 4 | 4 | 4 |
| `os_disable` | `022d48` | 1 | 8 | 0 | 0 | 0 | 0 |
| `os_enable` | `022d66` | 1 | 8 | 0 | 0 | 0 | 0 |

### A pass during a mission: `frame_update`'s tree (phase F)

| Routine | Address | `save_a` | `ships_j` | `night_again` | `chain_a` | `promote_a` | `cap_a` |
|---|---|---|---|---|---|---|---|
| `frame_update` | `010228` | 3102 | 364 | 2892 | 10332 | 10252 | 10294 |
| `flip_buffers` | `01030c` | 3102 | 364 | 2892 | 10332 | 10252 | 10294 |
| `weapon_marker` | `010344` | 3102 | 364 | 2892 | 10332 | 10252 | 10294 |
| `draw_player` | `0103a6` | 3102 | 364 | 2892 | 10332 | 10252 | 10294 |
| `draw_objects` | `0106be` | 3102 | 364 | 2892 | 10332 | 10252 | 10294 |
| `object_draw` | `010702` | 114 | 0 | 266 | 1292 | 1292 | 1292 |
| `draw_enemy_aircraft` | `010da6` | 3102 | 364 | 2892 | 10332 | 10252 | 10294 |
| `smoke_draw` | `010ee0` | 3102 | 364 | 2892 | 10332 | 10252 | 10294 |
| `snapshot_for_draw` | `010f88` | 3102 | 364 | 2892 | 10332 | 10252 | 10294 |
| `draw_game_over` | `0110c2` | 3102 | 364 | 2892 | 10332 | 10252 | 10294 |
| `draw_world` | `013772` | 3102 | 364 | 2892 | 10332 | 10252 | 10294 |
| `ship_planes` | `01391e` | 3102 | 364 | 2892 | 10332 | 10252 | 10294 |
| `airfields_draw` | `013a18` | 3102 | 364 | 2892 | 10332 | 10252 | 10294 |
| `deck_aircraft` | `013abc` | 3102 | 364 | 2892 | 10332 | 10252 | 10294 |
| `record_extras` | `013b1c` | 247590 | 26572 | 200638 | 744445 | 738527 | 741627 |
| `targets_3_draw` | `013d78` | 3102 | 364 | 2892 | 10332 | 10252 | 10294 |
| `targets_f_draw` | `013de8` | 3102 | 364 | 2892 | 10332 | 10252 | 10294 |
| `ocean` | `013e6c` | 3102 | 364 | 2892 | 10332 | 10252 | 10294 |
| `soldiers_draw` | `013eee` | 3102 | 364 | 2892 | 10332 | 10252 | 10294 |
| `lift_aircraft` | `01409c` | 3102 | 364 | 2892 | 10332 | 10252 | 10294 |
| `islands_draw` | `0140e8` | 3102 | 364 | 2892 | 10332 | 10252 | 10294 |
| `map_window` | `01417e` | 3102 | 364 | 2892 | 10332 | 10252 | 10294 |
| `window_height` | `0141b4` | 3066 | 364 | 2892 | 10332 | 10252 | 10294 |
| `window_strip` | `014206` | 3066 | 364 | 2892 | 10332 | 10252 | 10294 |
| `window_ship` | `014430` | 3066 | 364 | 2892 | 10332 | 10252 | 10294 |
| `window_background` | `014564` | 3102 | 364 | 2892 | 10332 | 10252 | 10294 |
| `window_shape` | `0145a6` | 16528 | 0 | 0 | 71392 | 72946 | 73386 |
| `ship_at_offset` | `014a4e` | 8969 | 3276 | 21502 | 10575 | 10744 | 10634 |
| `ship_at_span` | `014a52` | 11383 | 3640 | 23586 | 13549 | 13738 | 13614 |
| `target_records` | `014ae4` | 10 | 0 | 0 | 16 | 16 | 16 |
| `target_of` | `014b54` | 10 | 0 | 0 | 16 | 16 | 16 |
| `ship_guns_draw` | `014c3e` | 3102 | 364 | 2892 | 10332 | 10252 | 10294 |
| `target_frame` | `014d50` | 36703 | 10058 | 5784 | 11990 | 17400 | 50328 |
| `target_range_frame` | `014db8` | 33911 | 0 | 120 | 9847 | 13752 | 64740 |
| `ride_on_ship` | `014eac` | 8969 | 3276 | 21502 | 10575 | 10744 | 10634 |
| `ship_gun_shell` | `014efc` | 8716 | 0 | 0 | 0 | 0 | 26187 |
| `target_fire` | `014f5c` | 2624 | 0 | 0 | 1072 | 1302 | 1758 |
| `target_refill` | `014fee` | 0 | 0 | 0 | 48 | 48 | 48 |
| `nearest_barracks` | `015034` | 0 | 0 | 0 | 48 | 48 | 48 |
| `format_to` | `015078` | 6 | 28 | 4 | 66 | 66 | 66 |
| `format_putch` | `015090` | 48 | 224 | 32 | 680 | 715 | 715 |
| `flip_view` | `0150b0` | 3102 | 364 | 2892 | 10332 | 10252 | 10294 |
| `map_slot_at` | `0150c8` | 2772 | 0 | 0 | 19388 | 19388 | 19388 |
| `draw_world_shape` | `015174` | 50710 | 7462 | 10487 | 237516 | 246755 | 269044 |
| `sub_01520c` | `01520c` | 3102 | 364 | 2892 | 10332 | 10252 | 10294 |
| `clip_playfield` | `01524a` | 9270 | 1092 | 8974 | 30996 | 30756 | 30882 |
| `clip_dash_window` | `01525c` | 3102 | 364 | 2892 | 10332 | 10252 | 10294 |
| `clip_to_waterline` | `01526e` | 6079 | 364 | 4522 | 20547 | 20387 | 20471 |
| `splashes_draw` | `0152f8` | 3102 | 364 | 2892 | 10332 | 10252 | 10294 |
| `smoke_claim` | `015460` | 208 | 0 | 0 | 186 | 199 | 252 |
| `smoke_at_player` | `0154e0` | 191 | 0 | 0 | 88 | 101 | 154 |
| `balloons_draw` | `01557c` | 3102 | 364 | 2892 | 10332 | 10252 | 10294 |
| `mission_won` | `015694` | 0 | 0 | 0 | 1 | 1 | 1 |
| `island_bonus` | `015ae8` | 0 | 0 | 0 | 1 | 1 | 1 |
| `view_show` | `016f20` | 3102 | 364 | 2892 | 10332 | 10252 | 10294 |
| `cop_set_split_line` | `01876e` | 3102 | 364 | 2892 | 10332 | 10252 | 10294 |
| `cop_wait` | `019a9c` | 3102 | 364 | 2892 | 10332 | 10252 | 10294 |
| `cop_install` | `01aa0e` | 3102 | 364 | 2892 | 10332 | 10252 | 10294 |
| `wait_vblank` | `01aa3e` | 3102 | 364 | 2892 | 10332 | 10252 | 10294 |
| `record_on_ship` | `01cb34` | 47 | 0 | 12 | 277 | 297 | 283 |
| `ship_of_record` | `01cbf2` | 47 | 0 | 12 | 277 | 297 | 283 |
| `draw_dashboard` | `01ee16` | 3102 | 364 | 2892 | 10332 | 10252 | 10294 |
| `kill_icons` | `01f200` | 4 | 32 | 8 | 8 | 8 | 8 |
| `enemy_arrows` | `01f21a` | 3102 | 364 | 2892 | 10332 | 10252 | 10294 |
| `draw_score` | `01f26a` | 6 | 28 | 4 | 64 | 64 | 64 |
| `dash_digit` | `01f2b0` | 46 | 228 | 36 | 456 | 456 | 456 |
| `clip_dashboard` | `01f2dc` | 6204 | 728 | 5784 | 20664 | 20504 | 20588 |
| `rand_beam` | `0203be` | 15068 | 0 | 0 | 2879 | 3607 | 30962 |
| `shape_find` | `020560` | 0 | 0 | 298 | 0 | 0 | 0 |
| `blit_clip_setup` | `0209bc` | 87264 | 11742 | 63468 | 279520 | 284214 | 294652 |
| `shape_blit` | `020b0c` | 87264 | 11742 | 63468 | 279377 | 284071 | 294509 |
| `shape_draw` | `020ce2` | 87038 | 10770 | 60904 | 278683 | 283377 | 293815 |
| `shape_draw_xor` | `020e24` | 0 | 0 | 0 | 143 | 143 | 143 |
| `rect_fill` | `021010` | 27310 | 2128 | 11568 | 114266 | 114858 | 118120 |
| `draw_set_target` | `02124a` | 9306 | 1092 | 8974 | 30996 | 30756 | 30882 |
| `clip_set` | `02129c` | 24655 | 2548 | 22172 | 82539 | 81899 | 82235 |
| `blit_begin` | `0212ce` | 21803 | 2912 | 21804 | 72441 | 72235 | 72529 |
| `blit_end` | `0212d4` | 21803 | 2912 | 21804 | 72441 | 72235 | 72529 |
| `line_draw` | `021318` | 26 | 0 | 0 | 0 | 0 | 0 |
| `sub_022e40` | `022e40` | 21803 | 2912 | 21804 | 72441 | 72235 | 72529 |
| `sub_022e8a` | `022e8a` | 21803 | 2912 | 21804 | 72441 | 72235 | 72529 |

### A VBlank during a mission (phase V)

| Routine | Address | `save_a` | `ships_j` | `night_again` | `chain_a` | `promote_a` | `cap_a` |
|---|---|---|---|---|---|---|---|
| `input_queue_pop` | `011714` | 27 | 0 | 0 | 0 | 0 | 0 |
| `vblank_server` | `011754` | 6335 | 722 | 5780 | 20662 | 20502 | 20586 |
| `vblank_server:ticker_glyph` | `011754` | 0 | 54 | 0 | 60 | 60 | 60 |
| `vblank_server:ticker_message` | `011754` | 0 | 54 | 0 | 60 | 60 | 60 |
| `vblank_server:ticker_scroll` | `011754` | 0 | 450 | 0 | 705 | 705 | 705 |
| `read_joy_bits` | `01520e` | 1584 | 182 | 1447 | 5167 | 5127 | 5148 |
| `vblank_every_frame` | `01c9ca` | 6335 | 722 | 5780 | 20662 | 20502 | 20586 |
| `read_joystick` | `01ca32` | 1584 | 182 | 1447 | 5167 | 5127 | 5148 |
| `read_joy_dispatch` | `01cb20` | 1584 | 182 | 1447 | 5167 | 5127 | 5148 |
| `audio_irq` | `01ebaa` | 375 | 14 | 53 | 746 | 768 | 793 |
| `soundfx_vblank` | `01ec64` | 6335 | 722 | 5780 | 20662 | 20502 | 20586 |
| `poll_fire` | `02044c` | 6335 | 722 | 5780 | 20662 | 20502 | 20586 |
| `read_fire_button` | `02046a` | 6335 | 722 | 5780 | 20662 | 20502 | 20586 |
| `input_handler` | `02075a` | 7 | 0 | 0 | 0 | 0 | 0 |
| `os_disable` | `022d48` | 27 | 0 | 0 | 0 | 0 | 0 |
| `os_enable` | `022d66` | 27 | 0 | 0 | 0 | 0 | 0 |

### The inner loop beside `frame_update` during a mission (phase M)

| Routine | Address | `save_a` | `ships_j` | `night_again` | `chain_a` | `promote_a` | `cap_a` |
|---|---|---|---|---|---|---|---|
| `run_queued_ticks` | `0114d8` | 3102 | 364 | 2892 | 10332 | 10252 | 10294 |
| `input_queue_clear` | `01174a` | 1 | 0 | 0 | 0 | 0 | 0 |
| `sound_slots_clear` | `011f4e` | 1 | 0 | 0 | 0 | 0 | 0 |
| `sound_channels` | `012066` | 1 | 0 | 0 | 0 | 0 | 0 |
| `mem_free_var` | `0124e0` | 1 | 0 | 0 | 0 | 0 | 0 |
| `sound_engine_load` | `01344e` | 1 | 0 | 0 | 0 | 0 | 0 |
| `sound_engine_free` | `0134a4` | 1 | 0 | 0 | 0 | 0 | 0 |
| `file_length` | `015b1a` | 1 | 0 | 0 | 0 | 0 | 0 |
| `load_file_chip_asm` | `015d50` | 1 | 0 | 0 | 0 | 0 | 0 |
| `save_nothing` | `015d62` | 1 | 0 | 0 | 0 | 0 | 0 |
| `save_write_part` | `015dde` | 8 | 0 | 0 | 0 | 0 | 0 |
| `save_game_write` | `015e8a` | 1 | 0 | 0 | 0 | 0 | 0 |
| `save_walk` | `015ec2` | 1 | 0 | 0 | 0 | 0 | 0 |
| `text_caret` | `016032` | 8 | 0 | 0 | 0 | 0 | 0 |
| `text_input` | `016086` | 2 | 0 | 0 | 0 | 0 | 0 |
| `path_sanitise` | `016592` | 1 | 0 | 0 | 0 | 0 | 0 |
| `vport_init_bitmap` | `0167f2` | 3 | 0 | 0 | 0 | 0 | 0 |
| `view_layout` | `01692c` | 2 | 0 | 0 | 0 | 0 | 0 |
| `screen_dialog` | `0169a4` | 1 | 0 | 0 | 0 | 0 | 0 |
| `view_set_game` | `016c38` | 1 | 0 | 0 | 0 | 0 | 0 |
| `screen_game_restore` | `016d32` | 1 | 0 | 0 | 0 | 0 | 0 |
| `view_show` | `016f20` | 34 | 0 | 0 | 0 | 0 | 0 |
| `view_show_wait` | `016fc4` | 2 | 0 | 0 | 0 | 0 | 0 |
| `colour_lerp` | `016ff6` | 1024 | 0 | 0 | 0 | 0 | 0 |
| `fade_to` | `017084` | 2 | 0 | 0 | 0 | 0 | 0 |
| `fade_out` | `0173b0` | 1 | 0 | 0 | 0 | 0 | 0 |
| `cop_add_ticker_ramp` | `0187ba` | 1 | 0 | 0 | 0 | 0 | 0 |
| `dialog_draw_names` | `018958` | 2 | 0 | 0 | 0 | 0 | 0 |
| `dialog_file_list` | `018a06` | 1 | 0 | 0 | 0 | 0 | 0 |
| `load_save_dialog` | `018b96` | 1 | 0 | 0 | 0 | 0 | 0 |
| `cop_reset` | `019958` | 35 | 0 | 0 | 0 | 0 | 0 |
| `cop_move` | `0199bc` | 957 | 0 | 0 | 0 | 0 | 0 |
| `cop_move_ptr` | `019a08` | 426 | 0 | 0 | 0 | 0 | 0 |
| `cop_wait` | `019a9c` | 126 | 0 | 0 | 0 | 0 | 0 |
| `cop_colours` | `019b5a` | 37 | 0 | 0 | 0 | 0 | 0 |
| `cop_vport_colours` | `019c0a` | 37 | 0 | 0 | 0 | 0 | 0 |
| `cop_vport_split` | `019c80` | 1 | 0 | 0 | 0 | 0 | 0 |
| `cop_vport_planes` | `019d18` | 37 | 0 | 0 | 0 | 0 | 0 |
| `cop_sprites_off` | `01a06c` | 35 | 0 | 0 | 0 | 0 | 0 |
| `view_build_copper` | `01a0d4` | 35 | 0 | 0 | 0 | 0 | 0 |
| `view_poke_colours1` | `01a60e` | 3 | 0 | 0 | 0 | 0 | 0 |
| `view_poke_colours2` | `01a6ac` | 1 | 0 | 0 | 0 | 0 | 0 |
| `view_copy_bitmaps` | `01a834` | 1 | 0 | 0 | 0 | 0 | 0 |
| `view_copy_colours` | `01a8c4` | 1 | 0 | 0 | 0 | 0 | 0 |
| `view_copy` | `01a9ca` | 1 | 0 | 0 | 0 | 0 | 0 |
| `cop_show_wait` | `01a9fc` | 1 | 0 | 0 | 0 | 0 | 0 |
| `cop_install` | `01aa0e` | 35 | 0 | 0 | 0 | 0 | 0 |
| `wait_vblank` | `01aa3e` | 3 | 0 | 0 | 0 | 0 | 0 |
| `ingame_keys` | `01ccf6` | 3103 | 372 | 2893 | 10334 | 10254 | 10296 |
| `channel_stop` | `01eac0` | 6 | 0 | 0 | 0 | 0 | 0 |
| `load_file_chip` | `01feca` | 1 | 0 | 0 | 0 | 0 | 0 |
| `load_file` | `01ff16` | 1 | 0 | 0 | 0 | 0 | 0 |
| `poll_fire` | `02044c` | 128 | 0 | 0 | 0 | 0 | 0 |
| `poll_joy_dir8` | `020454` | 128 | 0 | 0 | 0 | 0 | 0 |
| `read_fire_button` | `02046a` | 128 | 0 | 0 | 0 | 0 | 0 |
| `read_joy_dir8` | `020488` | 128 | 0 | 0 | 0 | 0 | 0 |
| `key_to_char` | `020700` | 11 | 0 | 0 | 0 | 0 | 0 |
| `key_available` | `0207d8` | 3245 | 372 | 2893 | 10334 | 10254 | 10296 |
| `key_get` | `0207e4` | 7 | 0 | 0 | 0 | 0 | 0 |
| `mem_alloc` | `020848` | 2 | 0 | 0 | 0 | 0 | 0 |
| `sub_020874` | `020874` | 3 | 0 | 0 | 0 | 0 | 0 |
| `mem_free` | `02090a` | 3 | 0 | 0 | 0 | 0 | 0 |
| `draw_set_target_c` | `021246` | 2 | 0 | 0 | 0 | 0 | 0 |
| `draw_set_target` | `02124a` | 2 | 0 | 0 | 0 | 0 | 0 |
| `clip_set_full` | `021280` | 2 | 0 | 0 | 0 | 0 | 0 |
| `clip_set` | `02129c` | 2 | 0 | 0 | 0 | 0 | 0 |
| `sub_021d6e` | `021d6e` | 8 | 0 | 0 | 0 | 0 | 0 |
| `strcpy` | `021e02` | 1 | 0 | 0 | 0 | 0 | 0 |
| `strlen` | `021e12` | 45 | 0 | 0 | 0 | 0 | 0 |
| `tolower` | `021e82` | 21 | 0 | 0 | 0 | 0 | 0 |
| `strcmp` | `021e9a` | 1 | 0 | 0 | 0 | 0 | 0 |
| `bcopy` | `021eca` | 1 | 0 | 0 | 0 | 0 | 0 |
| `strcat` | `0222a8` | 2 | 0 | 0 | 0 | 0 | 0 |
| `strncpy` | `0222d2` | 1 | 0 | 0 | 0 | 0 | 0 |
| `sub_0223cc` | `0223cc` | 960 | 0 | 0 | 0 | 0 | 0 |
| `sub_022424` | `022424` | 960 | 0 | 0 | 0 | 0 | 0 |
| `os_dos_close` | `022aae` | 2 | 0 | 0 | 0 | 0 | 0 |
| `sub_022ab2` | `022ab2` | 2 | 0 | 0 | 0 | 0 | 0 |
| `os_dos_examine` | `022ada` | 2 | 0 | 0 | 0 | 0 | 0 |
| `os_dos_ex_next` | `022aec` | 15 | 0 | 0 | 0 | 0 | 0 |
| `os_dos_lock` | `022b1a` | 2 | 0 | 0 | 0 | 0 | 0 |
| `os_dos_open` | `022b2c` | 2 | 0 | 0 | 0 | 0 | 0 |
| `sub_022b30` | `022b30` | 2 | 0 | 0 | 0 | 0 | 0 |
| `os_dos_read` | `022b3e` | 2 | 0 | 0 | 0 | 0 | 0 |
| `os_dos_unlock` | `022b50` | 2 | 0 | 0 | 0 | 0 | 0 |
| `os_dos_write` | `022b60` | 8 | 0 | 0 | 0 | 0 | 0 |
| `sub_022d36` | `022d36` | 3 | 0 | 0 | 0 | 0 | 0 |
| `sub_022d3a` | `022d3a` | 3 | 0 | 0 | 0 | 0 | 0 |
| `os_disable` | `022d48` | 7 | 0 | 0 | 0 | 0 | 0 |
| `os_enable` | `022d66` | 7 | 0 | 0 | 0 | 0 | 0 |
| `sub_022d86` | `022d86` | 3 | 0 | 0 | 0 | 0 | 0 |
| `sub_022d8a` | `022d8a` | 3 | 0 | 0 | 0 | 0 | 0 |
| `gfx_BltBitMap` | `022e0c` | 3 | 0 | 0 | 0 | 0 | 0 |
| `gfx_BltClear` | `022e2e` | 2 | 0 | 0 | 0 | 0 | 0 |
| `os_gfx_draw` | `022e48` | 32 | 0 | 0 | 0 | 0 | 0 |
| `gfx_InitBitMap` | `022e5a` | 3 | 0 | 0 | 0 | 0 | 0 |
| `gfx_InitRastPort` | `022e6c` | 3 | 0 | 0 | 0 | 0 | 0 |
| `os_gfx_move` | `022e78` | 35 | 0 | 0 | 0 | 0 | 0 |
| `os_gfx_rect_fill` | `022e92` | 8 | 0 | 0 | 0 | 0 | 0 |
| `os_gfx_set_apen` | `022ea4` | 6 | 0 | 0 | 0 | 0 | 0 |
| `os_gfx_set_bpen` | `022eb4` | 2 | 0 | 0 | 0 | 0 | 0 |
| `os_gfx_set_drmd` | `022ec4` | 35 | 0 | 0 | 0 | 0 | 0 |
| `os_gfx_text` | `022ed4` | 39 | 0 | 0 | 0 | 0 | 0 |
| `gfx_WaitTOF` | `022eee` | 128 | 0 | 0 | 0 | 0 | 0 |
| `os_console_raw_key_convert` | `022f30` | 11 | 0 | 0 | 0 | 0 | 0 |

### The tick during a mission (phase T)

| Routine | Address | `save_a` | `ships_j` | `night_again` | `chain_a` | `promote_a` | `cap_a` |
|---|---|---|---|---|---|---|---|
| `flip_buffers` | `01030c` | 0 | 0 | 2 | 2 | 2 | 2 |
| `object_draw_first` | `0107f2` | 2 | 0 | 0 | 13 | 13 | 13 |
| `object_spawn` | `010820` | 0 | 0 | 38 | 83 | 83 | 83 |
| `objects_step` | `010a72` | 1550 | 182 | 1456 | 5176 | 5136 | 5157 |
| `object_step` | `010aa6` | 58 | 0 | 152 | 694 | 694 | 694 |
| `weapon_drop` | `01107c` | 2 | 0 | 0 | 13 | 13 | 13 |
| `airfield_at` | `011126` | 52 | 0 | 0 | 323 | 323 | 323 |
| `shot_origin` | `011274` | 1550 | 182 | 1456 | 5176 | 5136 | 5157 |
| `weapon_menu` | `0112b0` | 1523 | 90 | 1402 | 5131 | 5091 | 5112 |
| `logic_tick` | `011386` | 1550 | 182 | 1456 | 5176 | 5136 | 5157 |
| `lift_step` | `011460` | 1523 | 90 | 1402 | 5131 | 5091 | 5112 |
| `ship_launches` | `011510` | 1550 | 182 | 1456 | 5176 | 5136 | 5157 |
| `airfields_step` | `011622` | 1550 | 182 | 1456 | 5176 | 5136 | 5157 |
| `input_queue_pop` | `011714` | 1550 | 182 | 1456 | 5176 | 5136 | 5157 |
| `vblank_server` | `011754` | 0 | 0 | 42 | 42 | 42 | 42 |
| `vblank_server:ticker_glyph` | `011754` | 0 | 0 | 0 | 1 | 2 | 1 |
| `vblank_server:ticker_message` | `011754` | 0 | 0 | 0 | 1 | 2 | 1 |
| `vblank_server:ticker_scroll` | `011754` | 0 | 0 | 0 | 21 | 21 | 21 |
| `gun_splashes` | `0119bc` | 1550 | 182 | 1456 | 5176 | 5136 | 5157 |
| `guns_ground_x` | `011a46` | 0 | 0 | 0 | 125 | 125 | 125 |
| `soldiers_hit_c` | `011a84` | 0 | 0 | 0 | 27 | 27 | 27 |
| `soldiers_hit` | `011a8c` | 2 | 0 | 0 | 165 | 165 | 165 |
| `torpedoes_hit` | `011ae2` | 2 | 0 | 0 | 165 | 165 | 165 |
| `engine_smoke` | `011bfc` | 1550 | 182 | 1456 | 5176 | 5136 | 5157 |
| `balloons_step` | `011c5e` | 1550 | 182 | 1456 | 5176 | 5136 | 5157 |
| `ships_sinking` | `011cae` | 1550 | 182 | 1456 | 5176 | 5136 | 5157 |
| `ship_sinking` | `011cd8` | 0 | 383 | 0 | 0 | 0 | 0 |
| `target_timers` | `011de4` | 1550 | 182 | 1456 | 5176 | 5136 | 5157 |
| `soldier_out` | `011e82` | 10 | 0 | 0 | 36 | 36 | 36 |
| `sound_slots_clear` | `011f4e` | 3 | 0 | 3 | 3 | 3 | 3 |
| `sound_channels` | `012066` | 1553 | 182 | 1459 | 5179 | 5139 | 5160 |
| `engine_sound` | `012132` | 1550 | 182 | 1456 | 5176 | 5136 | 5157 |
| `enemy_loudness` | `0122ce` | 1550 | 182 | 1456 | 5176 | 5136 | 5157 |
| `near_loudness` | `0122f6` | 2 | 0 | 3 | 116 | 116 | 116 |
| `loudness_at` | `012306` | 2 | 0 | 3 | 116 | 116 | 116 |
| `sound_boom` | `012324` | 2 | 0 | 3 | 96 | 96 | 96 |
| `sound_clang` | `012354` | 3 | 0 | 3 | 3 | 3 | 3 |
| `sound_screech` | `012380` | 1 | 0 | 0 | 0 | 0 | 0 |
| `sound_scream` | `0123ac` | 0 | 0 | 0 | 20 | 20 | 20 |
| `next_aircraft` | `0135ce` | 0 | 0 | 3 | 2 | 2 | 2 |
| `player_lost_restart` | `0135d8` | 0 | 0 | 3 | 2 | 2 | 2 |
| `player_restart_state` | `013684` | 1 | 0 | 2 | 2 | 2 | 2 |
| `sub_013756` | `013756` | 1 | 0 | 2 | 2 | 2 | 2 |
| `crash_hit` | `0146c6` | 0 | 0 | 0 | 28 | 28 | 28 |
| `weapon_hit` | `0146dc` | 2 | 0 | 0 | 41 | 41 | 41 |
| `target_records` | `014ae4` | 3 | 0 | 0 | 16 | 16 | 16 |
| `target_release` | `014b40` | 2 | 0 | 0 | 10 | 10 | 10 |
| `target_of` | `014b54` | 2 | 0 | 0 | 14 | 14 | 14 |
| `format_to` | `015078` | 0 | 21 | 0 | 0 | 0 | 0 |
| `format_putch` | `015090` | 0 | 1495 | 0 | 0 | 0 | 0 |
| `flip_view` | `0150b0` | 0 | 0 | 2 | 2 | 2 | 2 |
| `map_slot_at` | `0150c8` | 56 | 0 | 48 | 628 | 628 | 628 |
| `tangent` | `01514c` | 0 | 0 | 0 | 125 | 125 | 125 |
| `sub_01520c` | `01520c` | 0 | 0 | 2 | 2 | 2 | 2 |
| `read_joy_bits` | `01520e` | 0 | 0 | 10 | 10 | 10 | 10 |
| `clip_playfield` | `01524a` | 0 | 0 | 2 | 2 | 2 | 2 |
| `splash_spawn_c` | `0152ac` | 0 | 0 | 48 | 0 | 0 | 0 |
| `splash_spawn` | `0152b0` | 0 | 0 | 48 | 125 | 125 | 125 |
| `smoke_claim` | `015460` | 294 | 0 | 0 | 1079 | 1098 | 1137 |
| `sub_0154cc` | `0154cc` | 0 | 0 | 0 | 75 | 75 | 75 |
| `smoke_at_player` | `0154e0` | 294 | 0 | 0 | 1004 | 1023 | 1062 |
| `ticker_offer` | `01555a` | 0 | 7 | 0 | 0 | 0 | 0 |
| `ship_sunk_message` | `015640` | 0 | 14 | 0 | 0 | 0 | 0 |
| `mission_won` | `015694` | 0 | 7 | 0 | 0 | 0 | 0 |
| `sub_015710` | `015710` | 1526 | 0 | 435 | 4892 | 4862 | 4876 |
| `ground_height` | `015714` | 1526 | 0 | 435 | 4892 | 4862 | 4876 |
| `shape_mirror_x` | `015b58` | 70 | 0 | 82 | 140 | 140 | 140 |
| `view_show` | `016f20` | 0 | 0 | 2 | 2 | 2 | 2 |
| `cop_install` | `01aa0e` | 0 | 0 | 2 | 2 | 2 | 2 |
| `turn_allowed` | `01aa6e` | 208 | 0 | 0 | 832 | 832 | 832 |
| `wheel_height` | `01aaea` | 2615 | 0 | 905 | 9984 | 9914 | 9949 |
| `turn_step` | `01ab80` | 208 | 0 | 0 | 832 | 832 | 832 |
| `aircraft_frame` | `01abde` | 1708 | 0 | 820 | 5639 | 5599 | 5620 |
| `wreck_smoke` | `01aed8` | 0 | 0 | 356 | 300 | 300 | 300 |
| `lost_wait` | `01af7c` | 0 | 0 | 356 | 300 | 300 | 300 |
| `crash` | `01afba` | 0 | 0 | 27 | 44 | 44 | 44 |
| `hook_state` | `01b45a` | 1507 | 0 | 818 | 5110 | 5070 | 5091 |
| `on_the_lift` | `01b4de` | 1193 | 0 | 33 | 4362 | 4322 | 4343 |
| `button` | `01b5b0` | 1550 | 182 | 1456 | 5176 | 5136 | 5157 |
| `guns` | `01b682` | 1550 | 182 | 1456 | 5176 | 5136 | 5157 |
| `deck_span` | `01b7bc` | 1 | 0 | 2 | 2 | 2 | 2 |
| `player_reset` | `01b7ec` | 1 | 0 | 2 | 2 | 2 | 2 |
| `touches_ground` | `01b8c4` | 1089 | 0 | 30 | 4359 | 4319 | 4340 |
| `cable_hook` | `01b92e` | 309 | 0 | 312 | 312 | 312 | 312 |
| `sub_01b9bc` | `01b9bc` | 1 | 0 | 2 | 2 | 2 | 2 |
| `engine_idle` | `01b9cc` | 2 | 0 | 3 | 3 | 3 | 3 |
| `sub_01b9f0` | `01b9f0` | 1089 | 0 | 30 | 4359 | 4319 | 4340 |
| `ground_contact` | `01ba80` | 1089 | 0 | 30 | 4359 | 4319 | 4340 |
| `enemy_countdown_step` | `01bc02` | 1550 | 182 | 1456 | 5176 | 5136 | 5157 |
| `deck_state` | `01bcce` | 1398 | 0 | 342 | 4671 | 4631 | 4652 |
| `deck_roll` | `01bdba` | 322 | 0 | 312 | 312 | 312 | 312 |
| `player_motion` | `01bdfa` | 1089 | 0 | 30 | 4359 | 4319 | 4340 |
| `flight_controls` | `01bff4` | 1089 | 0 | 30 | 4359 | 4319 | 4340 |
| `frame_select` | `01c378` | 1507 | 0 | 818 | 5110 | 5070 | 5091 |
| `deck_controls` | `01c4e8` | 309 | 0 | 312 | 312 | 312 | 312 |
| `deck_edge` | `01c5f4` | 309 | 0 | 312 | 312 | 312 | 312 |
| `player_update` | `01c660` | 1550 | 182 | 1456 | 5176 | 5136 | 5157 |
| `record_at` | `01c982` | 2595 | 0 | 907 | 9837 | 9757 | 9799 |
| `vblank_every_frame` | `01c9ca` | 0 | 0 | 42 | 42 | 42 | 42 |
| `read_joystick` | `01ca32` | 0 | 0 | 10 | 10 | 10 | 10 |
| `rand_mod` | `01cac8` | 1 | 0 | 2 | 2 | 2 | 2 |
| `burn_smoke` | `01cae0` | 0 | 0 | 0 | 75 | 75 | 75 |
| `read_joy_dispatch` | `01cb20` | 0 | 0 | 10 | 10 | 10 | 10 |
| `sub_01cb30` | `01cb30` | 6562 | 0 | 3730 | 22244 | 22044 | 22149 |
| `record_on_ship` | `01cb34` | 0 | 0 | 0 | 347 | 347 | 347 |
| `on_water` | `01cb74` | 0 | 0 | 33 | 47 | 47 | 47 |
| `enemy_aircraft_step` | `01e7d6` | 1550 | 182 | 1456 | 5176 | 5136 | 5157 |
| `channel_play` | `01ea28` | 78 | 0 | 36 | 375 | 378 | 378 |
| `channel_stop` | `01eac0` | 113 | 0 | 51 | 381 | 386 | 386 |
| `channel_busy` | `01eb2e` | 78 | 0 | 36 | 375 | 378 | 378 |
| `channel_adjust` | `01eb4c` | 1071 | 0 | 267 | 2006 | 2046 | 2094 |
| `soundfx_vblank` | `01ec64` | 0 | 0 | 42 | 42 | 42 | 42 |
| `weapon_gauge_reset` | `01edbc` | 1 | 0 | 2 | 2 | 2 | 2 |
| `rand_beam` | `0203be` | 951 | 0 | 2 | 3395 | 3538 | 3639 |
| `poll_fire` | `02044c` | 0 | 0 | 42 | 42 | 42 | 42 |
| `read_fire_button` | `02046a` | 0 | 0 | 42 | 42 | 42 | 42 |
| `sub_0204e4` | `0204e4` | 1507 | 0 | 818 | 5110 | 5070 | 5091 |
| `sub_0204ec` | `0204ec` | 1507 | 0 | 818 | 5110 | 5070 | 5091 |
| `shape_find_c` | `0204f4` | 6562 | 0 | 3730 | 22244 | 22044 | 22149 |
| `shape_find` | `020560` | 6562 | 0 | 3730 | 22244 | 22044 | 22149 |
| `rect_fill` | `021010` | 0 | 0 | 2 | 2 | 2 | 2 |
| `draw_set_target` | `02124a` | 0 | 0 | 2 | 2 | 2 | 2 |
| `clip_set` | `02129c` | 0 | 0 | 2 | 2 | 2 | 2 |
| `blit_begin` | `0212ce` | 0 | 0 | 2 | 2 | 2 | 2 |
| `blit_end` | `0212d4` | 0 | 0 | 2 | 2 | 2 | 2 |
| `ffp_add` | `021c9c` | 1089 | 0 | 30 | 4359 | 4319 | 4340 |
| `ffp_neg` | `021cb0` | 563 | 0 | 27 | 3219 | 3204 | 3211 |
| `ffp_fix` | `021cc4` | 3267 | 0 | 90 | 13077 | 12957 | 13020 |
| `ffp_div` | `021cd8` | 2178 | 0 | 60 | 8718 | 8638 | 8680 |
| `ffp_flt` | `021ce2` | 2178 | 0 | 60 | 8718 | 8638 | 8680 |
| `ffp_mul` | `021cec` | 3267 | 0 | 90 | 13077 | 12957 | 13020 |
| `sub_021d7c` | `021d7c` | 1 | 0 | 1 | 1 | 1 | 1 |
| `sub_021e24` | `021e24` | 0 | 0 | 70 | 54 | 54 | 54 |
| `sub_0222f4` | `0222f4` | 0 | 0 | 70 | 54 | 54 | 54 |
| `os_disable` | `022d48` | 1550 | 182 | 1456 | 5176 | 5136 | 5157 |
| `os_enable` | `022d66` | 1550 | 182 | 1456 | 5176 | 5136 | 5157 |
| `sub_022e40` | `022e40` | 0 | 0 | 2 | 2 | 2 | 2 |
| `sub_022e8a` | `022e8a` | 0 | 0 | 2 | 2 | 2 | 2 |
| `gfx_WaitTOF` | `022eee` | 0 | 0 | 42 | 42 | 42 | 42 |

### Between two missions: the fade, the next map and its briefing's start, main program (phase M)

| Routine | Address | `save_a` | `ships_j` | `night_again` | `chain_a` | `promote_a` | `cap_a` |
|---|---|---|---|---|---|---|---|
| `choose_night` | `0111fc` | 0 | 7 | 0 | 1 | 1 | 1 |
| `free_mission_assets` | `011234` | 0 | 7 | 0 | 1 | 1 | 1 |
| `sound_slots_clear` | `011f4e` | 0 | 7 | 0 | 1 | 1 | 1 |
| `sound_channels` | `012066` | 0 | 7 | 0 | 1 | 1 | 1 |
| `mem_free_var` | `0124e0` | 0 | 154 | 0 | 16 | 16 | 16 |
| `shapes_free` | `012502` | 0 | 21 | 0 | 1 | 1 | 1 |
| `ship_block` | `01252c` | 0 | 14 | 0 | 0 | 0 | 2 |
| `sub_0129c8` | `0129c8` | 0 | 7 | 0 | 1 | 1 | 1 |
| `map_load` | `012adc` | 0 | 7 | 0 | 1 | 1 | 1 |
| `free_map` | `012bbe` | 0 | 7 | 0 | 1 | 1 | 1 |
| `airfields_scan` | `012c84` | 0 | 7 | 0 | 1 | 1 | 1 |
| `map_scan` | `012d5a` | 0 | 7 | 0 | 1 | 1 | 1 |
| `sub_0131c8` | `0131c8` | 0 | 67 | 0 | 5 | 6 | 13 |
| `sub_013216` | `013216` | 0 | 78 | 0 | 5 | 6 | 14 |
| `sub_013236` | `013236` | 0 | 156 | 0 | 0 | 4 | 24 |
| `sounds_free` | `01346c` | 0 | 7 | 0 | 1 | 1 | 1 |
| `sound_engine_free` | `0134a4` | 0 | 7 | 0 | 1 | 1 | 1 |
| `sub_0134ae` | `0134ae` | 0 | 7 | 0 | 1 | 1 | 1 |
| `airfields_clear` | `013554` | 0 | 7 | 0 | 1 | 1 | 1 |
| `mem_alloc_asm` | `0158ec` | 0 | 35 | 0 | 4 | 5 | 5 |
| `sub_0165c4` | `0165c4` | 0 | 7 | 0 | 1 | 1 | 1 |
| `ticker_clear` | `016bbc` | 0 | 7 | 0 | 1 | 1 | 1 |
| `view_show` | `016f20` | 0 | 112 | 0 | 16 | 16 | 16 |
| `colour_lerp` | `016ff6` | 0 | 10752 | 0 | 1536 | 1536 | 1536 |
| `fade_to_pair` | `0171f2` | 0 | 7 | 0 | 1 | 1 | 1 |
| `fade_out_pair` | `0173e6` | 0 | 7 | 0 | 1 | 1 | 1 |
| `cop_reset` | `019958` | 0 | 112 | 0 | 16 | 16 | 16 |
| `cop_move` | `0199bc` | 0 | 6786 | 0 | 958 | 958 | 958 |
| `cop_move_ptr` | `019a08` | 0 | 2016 | 0 | 288 | 288 | 288 |
| `cop_wait` | `019a9c` | 0 | 1344 | 0 | 192 | 192 | 192 |
| `cop_colours` | `019b5a` | 0 | 336 | 0 | 48 | 48 | 48 |
| `cop_vport_colours` | `019c0a` | 0 | 336 | 0 | 48 | 48 | 48 |
| `cop_vport_split` | `019c80` | 0 | 112 | 0 | 16 | 16 | 16 |
| `cop_vport_planes` | `019d18` | 0 | 336 | 0 | 48 | 48 | 48 |
| `cop_sprites_off` | `01a06c` | 0 | 112 | 0 | 16 | 16 | 16 |
| `view_build_copper` | `01a0d4` | 0 | 112 | 0 | 16 | 16 | 16 |
| `cop_install` | `01aa0e` | 0 | 112 | 0 | 16 | 16 | 16 |
| `channel_stop` | `01eac0` | 0 | 21 | 0 | 6 | 6 | 6 |
| `dash_cache_invalidate` | `01ed7a` | 0 | 14 | 0 | 2 | 2 | 2 |
| `dashboard_invalidate` | `01edaa` | 0 | 7 | 0 | 1 | 1 | 1 |
| `rand_beam` | `0203be` | 0 | 28 | 0 | 0 | 0 | 4 |
| `mem_alloc` | `020848` | 0 | 35 | 0 | 4 | 5 | 5 |
| `sub_020874` | `020874` | 0 | 35 | 0 | 4 | 5 | 5 |
| `mem_free` | `02090a` | 0 | 143 | 0 | 14 | 14 | 14 |
| `sub_0223cc` | `0223cc` | 0 | 10080 | 0 | 1440 | 1440 | 1440 |
| `sub_022424` | `022424` | 0 | 10080 | 0 | 1440 | 1440 | 1440 |
| `sub_022d36` | `022d36` | 0 | 35 | 0 | 4 | 5 | 5 |
| `sub_022d3a` | `022d3a` | 0 | 35 | 0 | 4 | 5 | 5 |
| `sub_022d86` | `022d86` | 0 | 143 | 0 | 14 | 14 | 14 |
| `sub_022d8a` | `022d8a` | 0 | 143 | 0 | 14 | 14 | 14 |
| `gfx_BltClear` | `022e2e` | 0 | 7 | 0 | 1 | 1 | 1 |

### Entropy reads, by the routine that called `rand_beam`

| Window | Phase | Caller | `save_a` | `ships_j` | `night_again` | `chain_a` | `promote_a` | `cap_a` |
|---|---|---|---|---|---|---|---|---|
| outer | M | `rand_mod` | 1 | 1 | 2 | 1 | 1 | 1 |
| setup | M | `rand_mod` | 2 | 16 | 4 | 4 | 4 | 4 |
| mission | F | `balloons_draw` | 0 | 0 | 0 | 0 | 207 | 207 |
| mission | F | `ship_gun_shell` | 8716 | 0 | 0 | 0 | 0 | 26187 |
| mission | F | `ship_guns_draw` | 288 | 0 | 0 | 0 | 0 | 0 |
| mission | F | `smoke_claim` | 416 | 0 | 0 | 372 | 398 | 504 |
| mission | F | `target_fire` | 2950 | 0 | 0 | 1435 | 1700 | 2306 |
| mission | F | `target_frame` | 2698 | 0 | 0 | 1072 | 1302 | 1758 |
| mission | T | `burn_smoke` | 0 | 0 | 0 | 75 | 75 | 75 |
| mission | T | `engine_smoke` | 342 | 0 | 0 | 1056 | 1161 | 1184 |
| mission | T | `rand_mod` | 1 | 0 | 2 | 2 | 2 | 2 |
| mission | T | `smoke_claim` | 588 | 0 | 0 | 2158 | 2196 | 2274 |
| mission | T | `soldier_out` | 20 | 0 | 0 | 104 | 104 | 104 |
| between | M | `choose_night` | 0 | 28 | 0 | 0 | 0 | 4 |


## Appendix: the regions no run executed

Every region of a ported routine that no run of M4 to M7 executed - M4's scripts, the night
mission, the key runs, the fifteen setups, the scripts of M5, M6 and M7 - with the stand-in
marker that covers it or what it is otherwise; below them, the markers whose region the
original did run, all of them M7 part 2's, and the markers that stand for a value.
Written by

```text
.venv/bin/python tools/reach_observe.py --cold REACH456.json REACH7.json
```

| Routine | Region no run executed | Stand-in marker, or what it is | Owed to |
|---|---|---|---|
| `main` `0x010006` | `0x010036`-`0x010041` | M3's: the command line's demo file, which the port has no command line for | |
| `main` `0x010006` | `0x010104`-`0x010109` | ported from reading: `demo_mode` sets `0x026D44` before step S | |
| `main` `0x010006` | `0x0101B4`-`0x0101BD` | ported from reading: a demo ends on the fire button | |
| `frame_update` `0x010228` | `0x0102BC`-`0x0102CD` | ported from reading: `player_lost_restart` from `frame_update`, when `0x024F24` is set, which no instruction of the executable does | |
| `draw_player` `0x0103A6` | `0x01043E`-`0x01045B` | unreachable: no branch leads there | |
| `draw_player` `0x0103A6` | `0x0104D4`-`0x0104D5` | ported from reading: the climb clamped at -2 in the eighth-scale view | |
| `draw_player` `0x0103A6` | `0x0105F0`-`0x0105F1` | ported from reading: the cable's end when the aircraft faces right | |
| `object_draw_first` `0x0107F2` | `0x01081A`-`0x01081F` | ported from reading: no weapon left or every object record in use, nothing is dropped; tests/`test_oracle_m5.py`, the drop | |
| `object_spawn` `0x010820` | `0x010840`-`0x010841` | ported from reading: all fifteen object records in use, nothing is left | |
| `object_spawn` `0x010820` | `0x010970`-`0x010971` | ported from reading: a rocket's frame from the bearing, clamped at 0; tests/`test_oracle_m5.py`, the drop | |
| `rocket_homing` `0x01099A` | `0x010A16`-`0x010A67` | ported from reading: a rocket aimed at a pillbox or a ship's gun under its bearing, which no script's rocket found; tests/`test_oracle_m5.py`, the objects' step | |
| `object_step` `0x010AA6` | `0x010B1E`-`0x010B21` | ported from reading: a rocket's reach in the eighth-scale view; tests/`test_oracle_m5.py`, the objects' step | |
| `object_step` `0x010AA6` | `0x010B3C`-`0x010B43` | ported from reading: a rocket out of reach is freed; tests/`test_oracle_m5.py`, the objects' step | |
| `object_step` `0x010AA6` | `0x010B94`-`0x010BEF` | ported from reading: a weapon over an airfield, which no script's weapon came down on; tests/`test_oracle_m5.py`, the objects' step | |
| `object_step` `0x010AA6` | `0x010C1A`-`0x010C1F` | ported from reading: a weapon over a record of low bits 3; tests/`test_oracle_m5.py`, the objects' step | |
| `object_step` `0x010AA6` | `0x010C36`-`0x010C53` | ported from reading: a weapon over a ship's deck (low bits 1); `0x010C36` to `0x010C53`, the test of low bits 2 for 3 and 4, is unreachable; tests/`test_oracle_m5.py`, the objects' step | |
| `object_step` `0x010AA6` | `0x010D46`-`0x010D4F` | unreachable: +`0x1A` was set from `pass_counter` a few instructions before, so the splash at the start of a run is never made | |
| `draw_game_over` `0x0110C2` | `0x011118`-`0x011123` | ported from reading; tests/`test_oracle_m4.py`, every count | |
| `airfield_at` `0x011126` | `0x011138`-`0x011153` | ported from reading: an airfield record with a span, which maps a to c have none of; tests/`test_oracle_m5.py`, the objects' step | |
| `pillbox_between` `0x01115C` | `0x01119E`-`0x01119F` | ported from reading: a standing pillbox found under a rocket's bearing; tests/`test_oracle_m5.py`, the objects' step | |
| `weapon_menu` `0x0112B0` | `0x0112D4`-`0x0112D5` | ported from reading: the cursor keys and Return in the weapon menu | |
| `weapon_menu` `0x0112B0` | `0x0112DE`-`0x0112DF` | ported from reading: the cursor keys and Return in the weapon menu | |
| `weapon_menu` `0x0112B0` | `0x0112E8`-`0x0112E9` | ported from reading: the cursor keys and Return in the weapon menu | |
| `weapon_menu` `0x0112B0` | `0x0112F2`-`0x0112F5` | ported from reading: the cursor keys and Return in the weapon menu | |
| `run_queued_ticks` `0x0114D8` | `0x0114E0`-`0x0114E5` | `0x0114E0`, `run_queued_ticks`, demo playback and recording | M7 PART 2 |
| `run_queued_ticks` `0x0114D8` | `0x0114EE`-`0x0114EF` | ported from reading: nothing runs while paused | |
| `run_queued_ticks` `0x0114D8` | `0x011508`-`0x01150D` | ported from reading: `demo_mode` sets `0x026D44` | |
| `vblank_server` `0x011754` | `0x011790`-`0x0117D3` | M3's input half: demo playback (M7) | |
| `vblank_server` `0x011754` | `0x01180A`-`0x011841` | M3's input half: demo recording (M7) | |
| `guns_ground_x` `0x011A46` | `0x011A58`-`0x011A59` | ported from reading: a bearing of `0xFF01`, taken as `0xFF02`; tests/`test_oracle_m5.py`, the guns' reach | |
| `torpedoes_hit` `0x011AE2` | `0x011B08`-`0x011B09` | ported from reading: a torpedo west of the span; tests/`test_oracle_m5.py`, the soldiers' and torpedoes' hits | |
| `torpedoes_hit` `0x011AE2` | `0x011B30`-`0x011B4B` | ported from reading: the extra object record hit; tests/`test_oracle_m5.py`, the soldiers' and torpedoes' hits | |
| `ship_sinking` `0x011CD8` | `0x011D3A`-`0x011D51` | ported from reading; tests/`test_oracle_m6.py`, the ships sinking: the carrier a row deeper with the player aboard, back on the lift | |
| `ship_sinking` `0x011CD8` | `0x011D7E`-`0x011D97` | ported from reading; tests/`test_oracle_m6.py`, the ships sinking: the carrier `0x21` rows down with the aircraft on its deck, into the sea | |
| `target_timers` `0x011DE4` | `0x011E6E`-`0x011E6F` | ported from reading: a barracks' next soldier's timer from `vblank_total`, 0 counting as 3; tests/`test_oracle_m5.py`, the tick's routines | |
| `soldier_out` `0x011E82` | `0x011EF2`-`0x011EF5` | ported from reading: every soldier record in use, nobody comes out | |
| `soldier_out` `0x011E82` | `0x011F42`-`0x011F47` | ported from reading: a dug-out's soldier turned round by `rand_beam` | |
| `map_load` `0x012ADC` | `0x012B80`-`0x012B83` | an allocation failed, fatal; the port's tables are fixed (src/mission.def) | |
| `free_map` `0x012BBE` | `0x012C3E`-`0x012C55` | ported from reading: a ship released at the end of a mission | |
| `map_scan` `0x012D5A` | `0x0130AE`-`0x0130B1` | an allocation failed, fatal; the port's tables are fixed (src/mission.def) | |
| `load_ship_shapes` `0x013252` | `0x01327C`-`0x013283` | battleship.shp missing from the disk; the port loads every container at start-up | |
| `load_ship_shapes` `0x013252` | `0x0132C4`-`0x0132C7` | destroyer.shp missing, fatal; the port loads every container at start-up | |
| `load_ship_shapes` `0x013252` | `0x0132FE`-`0x013301` | cruiseship.shp missing, fatal; the port loads every container at start-up | |
| `load_ship_shapes` `0x013252` | `0x013346`-`0x013349` | japcarrier.shp missing, fatal; the port loads every container at start-up | |
| `ship_guns_setup` `0x01350E` | `0x013516`-`0x013517` | ported from reading: nothing for a loaded game | |
| `draw_world` `0x013772` | `0x013900`-`0x013901` | ported from reading: the distance handed to the sound engine | |
| `deck_aircraft` `0x013ABC` | `0x013ADA`-`0x013ADB` | ported from reading: more than nine lives count as nine | |
| `soldiers_draw` `0x013EEE` | `0x013FA8`-`0x013FB5` | ported from reading: an island neutralised that is not the map's last | |
| `soldiers_draw` `0x013EEE` | `0x013FE8`-`0x013FED` | ported from reading: a soldier turning round at the water | |
| `window_shape` `0x0145A6` | `0x014694`-`0x0146AD` | ported from reading: the shape of a record in the 3-D view | |
| `weapon_hit` `0x0146DC` | `0x014722`-`0x014725` | ported from reading: a hit on slot `0x113`, which it leaves alone; tests/`test_oracle_m5.py`, the hits | |
| `weapon_hit` `0x0146DC` | `0x014788`-`0x01478F` | ported from reading: the draw bit on another of the barracks' records than the third (D1, which nothing reads); tests/`test_oracle_m5.py`, the hits | |
| `weapon_hit` `0x0146DC` | `0x0147A8`-`0x0147AF` | ported from reading: the draw bit on another of the barracks' records than the third (D1, which nothing reads); tests/`test_oracle_m5.py`, the hits | |
| `weapon_hit` `0x0146DC` | `0x0147E8`-`0x0147EF` | ported from reading: the draw bit on another of the barracks' records than the third (D1, which nothing reads); tests/`test_oracle_m5.py`, the hits | |
| `weapon_hit` `0x0146DC` | `0x01493A`-`0x014981` | ported from reading: an island's last pillbox destroyed with no soldier left; tests/`test_oracle_m5.py`, the hits | |
| `target_of` `0x014B54` | `0x014B88`-`0x014B97` | ported from reading: no draw record among the four, no target | |
| `target_of` `0x014B54` | `0x014BC6`-`0x014BCB` | ported from reading: a burnt barracks not in the table, no target | |
| `target_of` `0x014B54` | `0x014BF4`-`0x014BF9` | ported from reading: a dug-out not in the table, no target | |
| `target_of` `0x014B54` | `0x014C2C`-`0x014C31` | ported from reading: a pillbox not in the table, no target | |
| `target_of` `0x014B54` | `0x014C3A`-`0x014C3D` | ported from reading: another slot, no target | |
| `target_refill` `0x014FEE` | `0x01501E`-`0x01501F` | ported from reading: the barracks east of the dug-out, its soldier runs west | |
| `nearest_barracks` `0x015034` | `0x015060`-`0x015061` | ported from reading: the barracks west of the dug-out, the distance negated | |
| `sine` `0x015108` | `0x015122`-`0x015127` | ported from reading: an angle in the second quarter; tests/`test_oracle_m5.py`, the angles | |
| `tangent` `0x01514C` | `0x015156`-`0x015157` | ported from reading: a negative angle; tests/`test_oracle_m5.py`, the angles | |
| `tangent` `0x01514C` | `0x01516C`-`0x01516D` | ported from reading: a negative angle; tests/`test_oracle_m5.py`, the angles | |
| `ticker_say` `0x015624` | `0x015624`-`0x01563F` | ported from reading: an island neutralised that is not the map's last, its message (`0x015624`) | |
| `bearing_of` `0x015CA6` | `0x015CA6`-`0x015D0B` | ported from reading: the angle of a vector, which only an aimed rocket asks for; tests/`test_oracle_m5.py`, the angles | |
| `save_game_write` `0x015E8A` | `0x015EBE`-`0x015EC1` | ported from reading; tests/`test_oracle_m7.py`, a save that cannot be opened: nothing is walked or written and 0 comes back, which the dialog ignores; the port's file system refuses a file only when its overlay is full | |
| `load_dash_assets` `0x01653C` | `0x016568`-`0x01656B` | dash.shp missing, fatal; the port loads every container at start-up | |
| `demo_end` `0x01852A` | `0x018536`-`0x01855D` | `0x018536`, saving a recorded demo | M7 PART 2 |
| `turn_allowed` `0x01AA6E` | `0x01AABE`-`0x01AACD` | ported from reading; tests/`test_oracle_m4.py`, an enemy aircraft that stops a turn | |
| `crash` `0x01AFBA` | `0x01B1A6`-`0x01B1A7` | ported from reading (M4): a wreck sliding along a ship; tests/`test_oracle_m4.py`, the crash and the ground | |
| `crash` `0x01AFBA` | `0x01B1BA`-`0x01B1BB` | ported from reading; tests/`test_oracle_m4.py`, the aircraft down on a ship | |
| `crash` `0x01AFBA` | `0x01B1DC`-`0x01B1E7` | ported from reading; tests/`test_oracle_m4.py`, the attitude levelling out | |
| `crash` `0x01AFBA` | `0x01B200`-`0x01B2A1` | ported from reading; tests/`test_oracle_m4.py`, a wreck sliding along a ship | |
| `hook_state` `0x01B45A` | `0x01B4A8`-`0x01B4AB` | ported from reading; tests/`test_oracle_m4.py`, the hook with the carrier sunk | |
| `on_the_lift` `0x01B4DE` | `0x01B538`-`0x01B56F` | ported from reading; tests/`test_oracle_m4.py`, on the lift facing right | |
| `button` `0x01B5B0` | `0x01B5DA`-`0x01B5E1` | ported from reading: the click inside a turn (attitude 6 to 16) drops nothing | |
| `guns` `0x01B682` | `0x01B6C8`-`0x01B6CB` | ported from reading; tests/`test_oracle_m6.py`, the guns at an enemy aircraft east of the player | |
| `ground_contact` `0x01BA80` | `0x01BB68`-`0x01BB81` | ported from reading; tests/`test_oracle_m4.py`, a bounce off the deck | |
| `deck_state` `0x01BCCE` | `0x01BCEA`-`0x01BCF9` | ported from reading; tests/`test_oracle_m4.py`, the deck state | |
| `deck_state` `0x01BCCE` | `0x01BD86`-`0x01BD91` | ported from reading; tests/`test_oracle_m4.py`, the deck state | |
| `player_motion` `0x01BDFA` | `0x01BF84`-`0x01BF89` | ported from reading; tests/`test_oracle_m4.py`, `player_motion` | |
| `player_motion` `0x01BDFA` | `0x01BFE8`-`0x01BFEF` | ported from reading; tests/`test_oracle_m4.py`, `player_motion` | |
| `flight_controls` `0x01BFF4` | `0x01C074`-`0x01C085` | ported from reading; tests/`test_oracle_m4.py`, the stick in the air | |
| `flight_controls` `0x01BFF4` | `0x01C09C`-`0x01C09F` | ported from reading; tests/`test_oracle_m4.py`, the stick in the air | |
| `flight_controls` `0x01BFF4` | `0x01C12E`-`0x01C131` | ported from reading; tests/`test_oracle_m4.py`, the stick in the air | |
| `flight_controls` `0x01BFF4` | `0x01C200`-`0x01C20D` | ported from reading; tests/`test_oracle_m4.py`, the stick in the air | |
| `flight_controls` `0x01BFF4` | `0x01C2A0`-`0x01C2CD` | ported from reading; tests/`test_oracle_m4.py`, the stick in the air | |
| `flight_controls` `0x01BFF4` | `0x01C326`-`0x01C34F` | ported from reading; tests/`test_oracle_m4.py`, the stick in the air | |
| `deck_controls` `0x01C4E8` | `0x01C5E6`-`0x01C5EB` | ported from reading; tests/`test_oracle_m4.py`, the stick on the deck | |
| `player_update` `0x01C660` | `0x01C8EE`-`0x01C8EF` | ported from reading: state 9 does nothing | |
| `player_update` `0x01C660` | `0x01C934`-`0x01C94B` | the player update's jump table: data | |
| `record_on_ship` `0x01CB34` | `0x01CB50`-`0x01CB51` | ported from reading: a record at the list's end is on no ship | |
| `record_is_land` `0x01CBB2` | `0x01CBEE`-`0x01CBEF` | ported from reading; tests/`test_oracle_m6.py`, an aircraft at rest on a record that is not land | |
| `ship_of_record` `0x01CBF2` | `0x01CC04`-`0x01CC0F` | ported from reading: a debugging line to the console, and 1 | |
| `ship_of_record` `0x01CBF2` | `0x01CC68`-`0x01CCB5` | ported from reading: a debugging line to the console, and 1 | |
| `ingame_keys` `0x01CCF6` | `0x01CE0A`-`0x01CE1D` | ported from reading: the load dialog cancelled | |
| `ingame_keys` `0x01CCF6` | `0x01CE26`-`0x01CE27` | the crash reporter of Control-B, which the port does not have (re/notes/keys.md) | |
| `aircraft_turn` `0x01D562` | `0x01D6BE`-`0x01D6E5` | ported from reading; tests/`test_oracle_m6.py`, a fighter's turn reversed behind the player while he turns | |
| `aircraft_turn` `0x01D562` | `0x01D6EE`-`0x01D703` | ported from reading; tests/`test_oracle_m6.py`, a fighter's turn reversed east of the player while he turns | |
| `aircraft_turn` `0x01D562` | `0x01D742`-`0x01D74B` | the jump table of `aircraft_turn`'s switch: data, not code | |
| `fighter_cruise` `0x01D9C6` | `0x01DB86`-`0x01DBBD` | ported from reading; tests/`test_oracle_m6.py`, a fighter ahead of the player hit by the guns: its evasion | |
| `fighter_cruise` `0x01D9C6` | `0x01DCAC`-`0x01DCB5` | the jump table of `fighter_cruise`'s switch: data, not code | |
| `torpedo_plane` `0x01DEA4` | `0x01DF8C`-`0x01DF97` | ported from reading; tests/`test_oracle_m6.py`, a torpedo plane flying west turning 500 past the deck | |
| `aircraft_falling` `0x01E244` | `0x01E3D2`-`0x01E3D5` | ported from reading; tests/`test_oracle_m6.py`, a fighter shot down and freed off land: one fewer up | |
| `aircraft_burning` `0x01E3E8` | `0x01E404`-`0x01E40D` | ported from reading; tests/`test_oracle_m6.py`, a wreck burning facing east | |
| `aircraft_idle` `0x01E4C8` | `0x01E4C8`-`0x01E4CF` | ported from reading; tests/`test_oracle_m6.py`, state 1, which nothing sets | |
| `aircraft_launch` `0x01E4D0` | `0x01E504`-`0x01E515` | ported from reading; tests/`test_oracle_m6.py`, a torpedo plane already up when another is launched | |
| `aircraft_speed` `0x01E64E` | `0x01E71A`-`0x01E723` | unreachable: slowing towards a want speed of at least 900 lands half the gap and 5 above it | |
| `aircraft_fly` `0x01E728` | `0x01E7BA`-`0x01E7BB` | ported from reading; tests/`test_oracle_m6.py`, a mode that is none of the four | |
| `aircraft_fly` `0x01E728` | `0x01E7D0`-`0x01E7D1` | ported from reading; tests/`test_oracle_m6.py`, a mode that is none of the four | |
| `enemy_aircraft_step` `0x01E7D6` | `0x01E84E`-`0x01E859` | ported from reading; tests/`test_oracle_m6.py`, state 1, which nothing sets | |
| `enemy_aircraft_step` `0x01E7D6` | `0x01E866`-`0x01E869` | ported from reading; tests/`test_oracle_m6.py`, state 8, which nothing sets | |
| `enemy_aircraft_step` `0x01E7D6` | `0x01E87E`-`0x01E87F` | ported from reading; tests/`test_oracle_m6.py`, a state that is none of the five | |
| `channel_play` `0x01EA28` | `0x01EA3A`-`0x01EA41` | `0x01EA3A`, a sample asked for on channel 6, which no caller does | M8 |
| `soundfx_vblank` `0x01EC64` | `0x01ECBE`-`0x01ECCD` | ported from reading; tests/`test_oracle_m8.py`, `soundfx_vblank`: the music's flags for channel 2, which only the uncalled `0x01E9F4` sets | |
| `soundfx_vblank` `0x01EC64` | `0x01ECF8`-`0x01ED3F` | ported from reading; tests/`test_oracle_m8.py`, `soundfx_vblank`: a volume eased to its target, which only the uncalled `0x01EB94` starts | |
| `lives_gauge_reset` `0x01EDEA` | `0x01EDF4`-`0x01EDF5` | ported from reading; tests/`test_oracle_m4.py`, the gauge resets | |
| `lives_gauge_reset` `0x01EDEA` | `0x01EDFE`-`0x01EDFF` | ported from reading; tests/`test_oracle_m4.py`, the gauge resets | |
| `draw_dashboard` `0x01EE16` | `0x01F102`-`0x01F103` | ported from reading: negative lives count as none | |
| `draw_dashboard` `0x01EE16` | `0x01F10C`-`0x01F10D` | ported from reading: more than nine lives count as nine | |
| `line_draw` `0x021318` | `0x021342`-`0x021343` | ported from reading, PROVISIONAL: the clipping of `line_draw` | |
| `line_draw` `0x021318` | `0x021354`-`0x021357` | ported from reading, PROVISIONAL: the clipping of `line_draw` | |
| `line_draw` `0x021318` | `0x02136A`-`0x02136B` | ported from reading, PROVISIONAL: the clipping of `line_draw` | |
| `line_draw` `0x021318` | `0x02137C`-`0x02137F` | ported from reading, PROVISIONAL: the clipping of `line_draw` | |
| `line_draw` `0x021318` | `0x02138E`-`0x0214EB` | ported from reading, PROVISIONAL: the clipping of `line_draw` | |
| `line_draw` `0x021318` | `0x021556`-`0x021561` | the blitter's busy wait, which the port's line has none of | |
| `line_draw` `0x021318` | `0x0215D0`-`0x0215D7` | ported from reading, PROVISIONAL: a line wholly outside the clip | |
| | run by the original | `0x019152`, `save_game_read`: a saved game loaded | M7 PART 2 |
| | run by the original | `0x01CDD4`, a loaded game: the briefing and the mission again | M7 PART 2 |
| | no region: a value | a negative score, in `0x01F26A` | M7 PART 2 |
| | no region: a value | every soldier record in use, `0x011E82` walks past the table | M5 |
| | no region: a value | a ticker message outside the registered state | M7 PART 2 |

The music player (src/music.c):

| Routine | Region no run executed | Stand-in marker, or what it is | Owed to |
|---|---|---|---|
| `segentry` `0000` | `0034`-`0063` | songplay+`0x0034`, command 7, `_PlaySfx` (+`0x00AA`) | M8 |
| `segentry` `0000` | `0034`-`0063` | songplay+`0x003A`, command 8, `_StopSfx` (+`0x01A8`) | M8 |
| `segentry` `0000` | `0034`-`0063` | songplay+`0x0042`, command 9, `_SfxStat` (+`0x01EA`) | M8 |
| `segentry` `0000` | `0034`-`0063` | songplay+`0x004A`, command 10, `_PauseMusic` (+`0x01FA`) | M8 |
| `segentry` `0000` | `0034`-`0063` | songplay+`0x0052`, command 11, `_RestartMusic` (+`0x0240`) | M8 |
| `segentry` `0000` | `0034`-`0063` | songplay+`0x005A`, command 12, `_AdjustSfx` (+`0x0252`) | M8 |
| `SongInt` `02a6` | `02b8`-`02bb` | songplay+`0x02B8`, `sfx_start` (+`0x0104`), an effect of command 7 | M8 |
| `song_step` `041e` | `04cc`-`04d9` | ported from reading; tests/`test_oracle_m8.py`, the tick: a song no track has started a note of, which ends it | |
| `track_step` `04f4` | `050e`-`051f` | ported from reading; tests/`test_oracle_m8.py`, `track_step`: the arpeggio's next offset, which no voice of wofsongs has on | |
| `track_step` `04f4` | `0538`-`0545` | ported from reading; tests/`test_oracle_m8.py`, `track_step`: the arpeggio's note | |
| `track_step` `04f4` | `054e`-`0597` | ported from reading; tests/`test_oracle_m8.py`, `track_step`: the vibrato between its limits, which no voice of wofsongs has on | |
| `track_read` `05d2` | `0646`-`064d` | ported from reading; tests/`test_oracle_m8.py`, the variant song data: a hold and a command byte passed over, which no song gives | |
| `event_end` `0682` | `0682`-`0687` | ported from reading; tests/`test_oracle_m8.py`, the variant song data: a track's end | |
| `event_tempo_lo` `06c2` | `06c2`-`06db` | ported from reading; tests/`test_oracle_m8.py`, the variant song data: the latch's low byte | |
| `event_hold` `06fc` | `06fc`-`0703` | ported from reading; tests/`test_oracle_m8.py`, the variant song data: a hold | |
| `note_start` `0704` | `0748`-`0757` | ported from reading; tests/`test_oracle_m8.py`, the variant song data: a sample of three octaves, a note in a lower one's part | |
| `note_start` `0704` | `07b0`-`07bf` | ported from reading; tests/`test_oracle_m8.py`, `note_start`: the volume scaled while an effect of command 7 plays | |
| `note_period` `07ea` | `0808`-`0809` | ported from reading; tests/`test_oracle_m8.py`, the note lookup: a note above the sample's octaves | |
| `CheckChannelInt` `08ae` | `0916`-`0929` | ported from reading; tests/`test_oracle_m8.py`, the level-4 handler: a channel an effect of command 7 has | |
| | a routine not ported, never entered | songplay+`0x0064` `_StopSong`, a fade while paused | M8 |
| | a routine not ported, never entered | songplay+`0x0064` `_StopSong`, command 3 | M8 |
| | no region: a value | songplay, a voice of wofsongs read as bytes | M8 |
| | no region: a value | songplay, a voice pointer that names no voice of wofsongs | M8 |
| | no region: a value | songplay, a division by zero, which traps | M8 |
| | no region: a value | songplay, a note outside `note_clocks` (+`0x0816`) | M8 |
| | no region: a value | songplay, a length past the durations (+`0x0712`) | M8 |
| | no region: a value | songplay, a sample without its chunk (+`0x099C`) | M8 |
