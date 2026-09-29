# The campaign and the saved game

What happens from a mission won to the next mission's first ticks, the promotion after a
rank's last mission, and what a saved game holds and how it is laid out. Addresses use the
standard load layout. Every statement is **observed**, with the run or test that shows it,
or **read** from the listing alone. The scripts named here are those of
`tools/m7_scripts.py` (`re/notes/porting-m7.md`, "The scripts"); the manual is cited by
page.

## The order of the maps

The fifteen maps are played in their letters' order: a campaign is seven ranks of 3, 3, 2,
2, 1, 1 and 3 missions (`missions_per_rank`, `0x025548`). `map_load` (`0x012ADC`) adds up
`missions_per_rank` below `rank_played` (`0x0253BE`), adds `mission_number` (`0x0253C0`) less
one, and opens the file whose name pointer stands at that index of the table at `0x02550C`
(read). `mission_map_table` (`0x02345F`, a byte by `rank_played` x 4 + `mission_number`)
holds the same numbers, 0 to 14, for every rank and mission; `choose_night` (`0x0111FC`),
`island_bonus` (`0x015AE8`) and the airfields' scan (`0x012C84`) read that one (observed:
at step S of every map loaded under its own rank and mission number the table's entry is
the map's index, and the map's length is the file's).

| Rank | Missions | Maps |
|---|---|---|
| 0 | 3 | a, b, c |
| 1 | 3 | d, e, f |
| 2 | 2 | g, h |
| 3 | 2 | i, j |
| 4 | 1 | k |
| 5 | 1 | l |
| 6 | 3 | m, n, o |

## A mission won

`mission_won` (`0x015694`) is called by the pass when a map's last island is neutralised
(`soldiers_draw` `0x013EEE`, a soldier's death, and `weapon_hit` `0x0146DC`, the last
pillbox) and by the tick when the last enemy ship is gone with no island left
(`ship_sinking` `0x011CD8`) (read; the pass's call observed in every M7 script built on
`island_a`). It counts `mission_number` on and compares it with
`missions_per_rank[rank_played]`, a word read by address (a rank past 6 reads what follows
the table):

- **the next mission** while the new number is within the rank: `msg_next_mission`
  (`0x02399E`) goes into `ticker_text`;
- **the promotion** beyond it: `mission_number` 1, `rank_played` one up and **capped at 6**,
  `balloons_on` (`0x02535D`) set, and `msg_promotion` (`0x023A5A`).

The message is appended to what `ticker_text` (`0x02716A`) holds, over its last character:
the scan stops behind the NUL and `subq.w #2` steps back over it and the character before.
Both branches point the ticker at `ticker_text` and set `0x0253BC` to -1. Observed:
`chain_a`'s win of map a at tick 4374 makes rank 0, mission 2; `promote_a` (map a poked to
the first rank's last mission) rank 1, mission 1; `cap_a` (the last rank's last mission)
rank 6, mission 1. The manual's bonus for a whole mission (page 10) is no score of its own:
nothing in `mission_won` touches the score; what the win adds is the last island's bonus,
which `island_bonus` gives before the call (read).

## The next mission

`main` goes on to the next mission from the head of its inner loop (`0x010122`): only while
the weapon menu is up (`weapon_menu_up`, `0x025364`) with `0x0253BC` set, that is when the
next aircraft is in the hold after the win, whether the one that won landed or was lost.
Then, in this order (read, and observed as the port's closed loop holds it step for step,
`tests/test_campaign.py`):

1. `0x0253BC` and the weapon menu cleared, the sound slots cleared (`0x011F4E`), the ticker
   stopped and cleared, both views faded out (`fade_out_pair` with 1), the mission's assets
   freed (`free_mission_assets` `0x011234`: the dashboard's shapes, the sounds, the map and
   its tables, the ships' gun lists and containers);
2. **a Hellcat more if `balloons_on` is set** (`0x01015C`, `addq.b` on `lives`), which only
   the promotion sets (below);
3. `choose_night`, `dashboard_invalidate`, `map_load` of the new map, and its briefing
   (`mission_briefing` `0x018590`); Control-R there returns 1 and `main` goes back to the
   outer loop's head (`0x010172`: `tst.b d0`), as it does from the first briefing;
4. `load_dash_assets` (after the briefing here, because `choose_night` has only now decided
   the dashboard), `mission_display_setup`, `load_ship_shapes`, `build_master_lists`,
   `sounds_load`, and the jump to `0x0100D2`, which is the first mission's reset:
   `mission_reset_tables` (which clears `balloons_on`), `player_restart_state`, the flags,
   the tick `main` runs itself, `input_queue_clear`, the demo's counter, and step S.

What the next mission does not do: the rank selection, `campaign_reset` (`0x013562`), the
score, the kill counter and the enemy plane counter stay, and so do the lives beside the
extra one (read; observed: `chain_a` comes to map b with score 2,850 and one Hellcat).

Observed in the scripts (the headless original's schedule):

| Script | Won at tick | Next aircraft in the hold | Briefing (VBlanks) | Next mission | Rank, mission | Night |
|---|---|---|---|---|---|---|
| `chain_a` | 4,374 | 4,556 | 243 | map b | 0, 2 | no draw (map 1) |
| `promote_a` | 4,374 | 4,556 | 243 | map d | 1, 1 | no draw (map 3) |
| `cap_a` | 4,374 | 4,556 | 243 | map m | 6, 1 | night (map 12, four draws) |

## The promotion, the extra Hellcat and the balloons

After a rank's last mission `mission_won` sets `balloons_on`; from the next pass on,
`balloons_draw` (`0x01557C`) releases every free record of the Balloons pool over the
carrier and draws them, and `balloons_step` (`0x011C5E`) moves them, both only while
`balloons_on` is set (read; observed in `promote_a`: all twenty records in use within two
ticks of the win at tick 4374). At the next mission, `main` gives the extra Hellcat the
manual promises for every promotion (pages 8 and 10) because `balloons_on` is still set
(observed in `promote_a`: one Hellcat left when the next aircraft is in the hold, two at the
next mission's step S), and `mission_reset_tables` then clears it.

**The balloons do not go away.** The Balloons pool is allocated once at start-up and nothing
clears it between missions, and with `balloons_on` clear the records in use are neither
drawn nor moved: nineteen of `promote_a`'s twenty are still in use, standing where they
were, through the whole of map d's flight (observed, `tools/m7_scripts.py trace promote_a`).
They fly on from there at the next promotion, where only the free records are released
anew (read).

## The rank's cap, and no end

The rank is capped at 6 (`0x0156BC`): after the last rank's last mission (map o) the
promotion runs again with the rank staying 6 and `mission_number` 1, so the next map is m,
and a campaign goes on through m, n and o for ever (observed in `cap_a`: map a won as rank
6's third mission, then map m as rank 6's first, a night mission; the promotion's message,
the balloons and the extra Hellcat as at any promotion). No routine reads the rank or the
mission number for anything else: the readers are `choose_night`, `map_load`, the
airfields' scan, `mission_won`, `island_bonus`, `rank_select`, the briefing and the
high-score entry, which records `rank_played` (`0x019632`), and one routine the gap sweep
found (`0x01251E`), which nothing calls (read). The executable has **no end sequence**: the
game ends only when the last Hellcat is lost or the player quits.

## Day and night

`choose_night` runs only between two missions of a campaign, after `mission_won` has counted
on: the new map's number from `mission_map_table`; at 6 or below `night_flag` (`0x025390`)
is 0, above it (maps h to o) `rand_beam` is drawn four times and bit 15 of the fourth
decides (read; observed in `cap_a`: map m, four draws by `0x0111FC`, night). It is the only
writer of `night_flag` (read), which nothing clears between campaigns: the first mission of
the program's first campaign is day because the DATA hunk starts with 0 there, and **a new
campaign after a game lost at night begins at night** (observed in `night_again`: M4's game
over flown as a night mission, the flag poked once at the first rank selection's end;
after the high scores and the rank selection the next campaign's first mission, map a, has
`night_flag` 1 at its step S, the night dashboard and the night palettes, on both sides and
in every pass of the closed loop).

## The briefing's numbers

The briefing draws the rank's name, `mission_number`, and two bytes that `map_scan` counts
in its first walk (read, `0x012E82` to `0x012FD4`; `map_load` clears both first):

- `briefing_islands` (`0x025382`): the islands that have a target, counted at each island's
  marker when a target came before it; nothing counts it down (`islands_left`, `0x025383`,
  starts equal and counts the islands neutralised);
- `briefing_ships` (`0x025370`): the enemy ships; `ship_sinking` counts it down when a ship
  is gone at `0x78` rows (`0x011DB8`).

So the briefing names what the manual says a mission's objectives are (page 10): the
islands to neutralise and the ships to sink. At step S of every map (observed):

| Map | a | b | c | d | e | f | g | h | i | j | k | l | m | n | o |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| islands | 1 | 2 | 3 | 2 | 3 | 2 | 3 | 3 | 3 | 0 | 3 | 2 | 4 | 3 | 3 |
| ships | 0 | 0 | 0 | 0 | 0 | 1 | 1 | 1 | 2 | 2 | 1 | 2 | 2 | 2 | 3 |

Map l has three islands but two with targets (`island_count` 3).

## The lives

Three Hellcats at a campaign's start (`campaign_reset`, the manual's page 10), one fewer
for every aircraft lost, one more at the next mission after every promotion (above); the
dashboard's drum shows at most nine and `deck_aircraft` counts more than nine as nine
(read).

## The saved game

Control-G saves the game while the aircraft is on the carrier (`player_on_deck` 1, on the
deck or in the hold; the manual's page 11): the load and save dialog opens in save mode,
the name typed goes after `wof.`, and `save_game_write` (`0x015E8A`) opens the file new,
writes it through the walker `save_walk` (`0x015EC2`) with the write callback
`save_write_part` (`0x015DDE`), and closes it (read; observed in `save_a`). `save_game_read`
(`0x015E1A`) reads it through the same walker with `save_read_part` (`0x015D7C`), M7 part
2's.

### The layout

The walker hands its callback (file, address, length, flag), and the file is those pieces
in this order, nothing between them (read; observed: `save_a`'s file is the concatenation,
and `tests/test_oracle_m7.py` holds the port's walker to the original's writes over 600
states):

| # | Piece | From | Length | Flag |
|---|---|---|---|---|
| 1 | the raw part | `object_records` (`0x024CAE`) up to `target_records_4` (`0x0254F8`) | `0x84A` (2,122) | 0 |
| 2 | `map_length` | `0x0253C6` | 2 | 0 |
| 3 | the map's record list | the block `map_records` (`0x024628`) points to | `map_length` (`ext.l`) | 1 |
| 4 | a gun list per ship | for each of the five `ship_records` (`0x025460`, `0x1E` each) whose words at `+4` and `+0x12` are set, the block its `+6` points to | 14 x `+0x0A` | 1 |
| - | `save_nothing` (`0x015D62`) | an empty routine the walker calls here | - | - |
| 5 | the pillboxes | `target_records_f` (`0x025504`) | 14 x `target_count_f` | 1 |
| 6 | the soldiers | `soldier_records` (`0x025500`) | 8 x `soldier_count` | 1 |
| 7 | the dug-outs | `target_records_3` (`0x0254FC`) | 16 x `target_count_3` | 1 |
| 8 | the barracks | `target_records_4` (`0x0254F8`) | 16 x `target_count_4` | 1 |

Flag 0 writes the memory at the address; flag 1 the block the long at the address points
to. The counts are bytes sign-extended before an unsigned multiply of the low word, and a
length is the product's low word (read). Only enemy ships have a score at `+0x12`; the
carrier's is 0, and it has no gun list, so the carrier is never written (observed on all
fifteen maps at step S). The raw part holds the counts the pieces after it need, so a file
describes its own layout: `tools/savegame.py` decodes one by it.

**The walker also writes.** After the map it sets `map_extent` (`0x024630`) to `map_length`
x 4 and `map_records_end` (`0x02462C`) to `map_records` + `map_length`, where `map_load`
leaves it a word before the list's end: every save moves the running game's
`map_records_end` two bytes on (read; observed as the closed loop of `save_a` holds the
port's `map_records_end` to the original's after the save, and by the oracle's walker test).

### The sizes

A save is 2,124 bytes of raw part and length, the map's record list, the ships' gun lists
and the four tables, so its size follows from the map and nothing else (observed at step S
of all fifteen maps):

| Map | a | b | c | d | e | f | g | h | i | j | k | l | m | n | o |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| bytes | 4,258 | 6,186 | 6,866 | 6,442 | 7,486 | 6,424 | 7,990 | 8,906 | 9,206 | 4,426 | 8,852 | 8,402 | 11,516 | 9,752 | 11,118 |

Map a's 4,258 are 2,124 + 1,910 of records + 20 soldiers x 8 + 2 x 16 + 2 x 16 (observed,
`re/notes/frontend.md`'s save on this disk). The disk's `wof.mission 3`, 6,866 bytes, is a
game saved on a real Amiga on map c: 2,124 + 3,902 of records + 4 x 14 + 70 x 8 + 7 x 16 +
7 x 16, no gun list. It holds rank 0, mission 3 (the first rank's third, map c by the
table), 14,225 points, two Hellcats, the aircraft on the carrier, two of the three islands
left, and the player's shape pointer `0x0005FB4A`, an address of that machine's memory
(observed, `tools/savegame.py --disk`, and `tests/test_oracle_m7.py`).

### The raw part

The raw part is memory as it stands, and so it is the port's registered state at those
addresses (`src/globals.def`, `src/mission.def`): the fifteen object records (`+0x000`), the
view (`+0x282`), the drawing's copy of the ship blocks (`+0x28A`), the player's record
(`+0x3CA`), the ship blocks (`+0x3E8`), the enemy aircraft with their wrecks and the
fighters up (`+0x528`), the airfields (`+0x64C`), the score, the lives and `balloons_on`
(`+0x69E` on), the counts of `map_scan`, the ships' flags and the briefing's numbers,
`night_flag`, `player_start_x`, `rank_played` (`+0x710`), `mission_number` (`+0x712`),
`map_length` again (`+0x718`), the pass counter, `vblank_total`, the player's controls and
the engine, the islands' lists (`+0x782`), the ship records (`+0x7B2`), and the two options,
`opt_invert_vertical` (`+0x848`) and `opt_music_off` (`+0x849`). 75 of its bytes are no
registered field; nothing in a mission writes them (`tests/m4complete.py`), and they are the
executable's (observed: all 75 are 0 in the disk's file and in `save_a`'s).

Not in the file (read): the extra object record (`0x025594`), where an enemy torpedo runs,
lies beyond the raw part; the pools (the smoke, the splashes, the balloons), `MasterList`,
the frame tables, the sound engine's slots and the ticker's text are not written.

### What the port writes in the raw part

The port writes every byte the original writes, from its registered state, except where the
original's memory holds a pointer, whose value is an address of the machine that saved:

| Field | Offset | The original writes | The port writes |
|---|---|---|---|
| the player's shape, `player` `+0x04` | `+0x3CE` | the address of a shape record in `hellcat.shp` | its shape handle, as a long |
| `0x02541A` | `+0x76C` | the address of a shape record | its shape handle |
| `torpedo_shape`, `0x02541E` | `+0x770` | the address of a shape record in `Torpedo.shp` | its shape handle |
| a ship's gun list, `ship_records` `+0x06` | `+0x7B8` + `0x1E` x the ship | the list's address | 1 where the list is set, 0 where not |

A shape handle is at most `0xFFFF`, while a pointer to a shape on the machine is an address
of its memory far above that (`0x0005FB4A` in the disk's file), so the two are told apart by
value. Nothing else differs: `tests/test_campaign.py` holds `save_a`'s file to the
original's byte for byte, and the list of differing bytes is exactly these four fields
(observed).

### What the reader of part 2 will meet (read)

- `save_read_part` reads a flag-0 piece into memory where it lies, and for a flag-1 piece
  allocates a new block of the length, reads into it and stores its address at the
  address the walker gave; the blocks the running game held are not freed. A short read
  leaves the pointer as it was.
- The raw part comes back whole, the three shape pointers and the carrier's gun-list
  pointer among it, as the saving machine held them; the enemy ships' gun-list pointers are
  replaced by the new blocks.
- **The loader must derive the four pointer fields and never trust them**: a file from a
  real Amiga holds that machine's addresses (`wof.mission 3`: the player's shape pointer
  `0x0005FB4A`), and the port's own files hold its handles and flags. Each follows from
  something the file holds as plain data (read, `frame_select` `0x01C378`, which the tick
  runs): the player's shape (`+0x04`) is the shape of `hellcat.shp` named by the frame
  name at `+0x08`, and `torpedo_shape` (`0x02541E`) the shape of `Torpedo.shp` of the same
  name, both set again by every tick's `frame_select`; `0x02541A` is the shape of
  `hellcat.shp` named by `0x025422`, which `frame_select` sets again only on some of its
  paths (the aircraft level on the deck or in the air), so it must be derived at the load;
  an enemy ship's gun list (`+0x06`) is the block the walker reads for it (set where the
  ship's `+4` and `+0x12` are set) and none where no block was read, as for the carrier.
- `opt_invert_vertical` comes back with the game (`SPEC.md` section 6.1: the port restores
  the owner's preference over it).
- The loaded game's path is `0x019152` from the rank selection and `0x01CDD4` in flight;
  both are M7 part 2's stand-ins (`re/notes/porting-m7.md`).
