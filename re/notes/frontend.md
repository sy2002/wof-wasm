# The front end

Everything M3 needs about the screens before a mission and after one: what each loads, what it
draws, how long it waits, what ends the wait, which song plays, and how the outer loop joins them
up. Geometry is in `re/notes/display.md`; the keys are in `re/notes/keys.md`; the high-score file
is in `re/notes/highscore.md`. Addresses use the standard load layout.

**How this was observed.** `tools/headless.py` runs the original's own front end. The timings
below are VBlank numbers from `tests/runs/front-end-idle.json`, a run with no input at all, and
the drawing calls are from the same run with observers on the drawing routines
(`tests/test_frontend.py`). An observer only reads: the same run with and without observers gives
the same step hashes, which `test_an_observer_does_not_change_a_run` holds it to. Where a
statement could not be observed it says so.

**Texts are not reproduced here.** A text is named by its address and its length; the port reads
it from the executable at build time (`SPEC.md` section 5).

## The timetable, left alone

One run, PAL, two VBlanks per pass, no input, from the first instruction to the first mission.

| VBlank | What happens |
|---|---|
| 1 | `title_sequence` (`0x018022`) starts. `music_start("wofsongs", 2)`, then `story_screen` |
| 1 | `screen_story`: 640 x 200 x 1, 230 rows shown from line 5 |
| 3 | the first story line is drawn; the scroller runs |
| 3 … 2915 | 53 story lines, one every **56 VBlanks** |
| 3791 | the scroller ends. `music_start("wofsongs", 1)`; `screen_picture`: 320 x 200 x 5 |
| 3793 | `load_picture_black("shapes/broderbund")`, then `view_show_wait` |
| 3794 | `fade_to(logo_fade_palette 0x02594C)` — the publisher logo comes up in a fixed palette |
| 3854 | after 60 rounds: `fade_to(the picture's own colours)`; `load_picture_black("shapes/wingstitle")` into the other buffer |
| 3974 | after 120 rounds: `fade_out`, `view_show_wait`, `fade_to(the title's colours)`; `load_picture_black("shapes/creditscreen")` |
| 4275 | after 300 rounds: `fade_out`, `view_show_wait`, `fade_to(the credits' colours)` |
| 4876 | after 600 rounds: `fade_out`. `rank_select` (`0x018262`) starts: `music_start("wofsongs", 4)`, `screen_picture` |
| 4878 | `load_picture_black("shapes/selectrank")`, the rank shapes from `shapes/selectrank.shp` |
| 4879 | `fade_to(the picture's colours)`, then `menu_input(1)` |
| 6680 | after 1800 rounds `menu_input` gives up: `fade_out`, and the game asks for demo playback. `mission_briefing` (`0x018590`) starts: `screen_hires3`, 640 x 147 x 3 |
| 6683 | `fade_to(briefing_palette 0x02592C)` |
| 6923 | after 240 rounds: `fade_out`; `mission_display_setup`, and the mission begins |

With the five taps of fire the tests use, the mission begins at **VBlank 132**
(`test_fire_skips_the_front_end`).

The rounds above are rounds of `wait_frames_or_fire` (`0x016EEE`) or of `menu_input`, each one
`graphics.WaitTOF`, so one round is one VBlank. **The fades take no time in the harness and their
real duration is not established** (`re/notes/display.md`): each of their 16 steps is arithmetic
plus a copper rebuild, with no wait. The three extra VBlanks between the briefing's 240 rounds and
`mission_display_setup` are the screen set-up and the two `view_show_wait`s, not the fades.

## Screen by screen

### The story scroller — `story_screen` `0x017E80`

- **Screen** `screen_story` (`0x016A60`): one view, 640 x 200 x 1, 230 rows displayed from line 5,
  the bitmap used as a ring (`re/notes/display.md`).
- **Loads** nothing. The lines are a block of NUL-terminated strings in the executable, the first
  at the address in `story_text` (`0x02598C`), which is `0x017494`; the block runs to about
  `0x017D00`.
- **Per step** (4 VBlanks: two `wait_frames_or_fire(2)` with `story_copper_build` and `view_show`
  between them) the front bitmap's `Planes[0]` advances by 80 bytes, one row, and the wrap row
  counts down from `0xD2`; at 0 it restarts and the plane pointer goes back to `view_a_planes`.
- **Every 14th step**, that is every 56 VBlanks: `SetAPen(0)`, `RectFill(0, y, 0x27F, y + 11)`
  clears a 12-row band, `SetAPen(1)`, `Move(0, y)` and `text_draw_justified(line, strlen, width)`
  in the **game font** through `MaskBuffer` and `BltTemplate` (`re/notes/drawing.md`). `y` is
  `0xC4` for the first line and `0xC4 - 0xD2 = -14` for every later one, that is 14 rows before
  the current plane start, which is the bottom of the visible window. The width is **`0x267`
  (615)** when the byte after the line's terminator is not 0, and 0 when it is: the last line of a
  paragraph is not stretched.
- **53 lines** are drawn (`line_count < 0x35`); after that the band is only cleared.
- **Ends** when fire is pressed, or 210 steps after the last line was drawn. Then a wind-down of
  16 rounds of `story_copper_build(ramp, wrap)` with the ramp counting 16 down to 1, two VBlanks
  each, which takes the two grey ramps out.
- **Reads no key** (`test_the_story_scroller_reads_no_key`).
- **Music:** song 2, started before the scroller.

### Publisher logo, title, credits — `title_sequence` `0x018022`

- **Screen** `screen_picture` (`0x016AD8`): two views, 320 x 200 x 5.
- **Loads** `shapes/broderbund`, `shapes/wingstitle`, `shapes/creditscreen`, each with
  `load_picture_black` (`0x017422`), which decodes into the **back** view, hands the caller the
  picture's colours and blacks the table. The next picture is decoded while the previous one is
  still shown, so nothing is ever seen coming up.
- Each picture is 256 rows high and shows its first 200 (`re/notes/display.md`).
- **Sequence:** show, `fade_to`, wait, `fade_out`, show the next. The logo is the exception: it
  fades first to `logo_fade_palette` (`0x02594C`, 32 words of which the first nine are used),
  waits 60, then fades to its own colours and waits 120.
- **Waits:** 60 and 120 for the logo, 300 for the title, 600 for the credits, all
  `wait_frames_or_fire`, which ends early on **fire** and on nothing else. Fire at any of them
  skips the rest of the sequence at once.
- **Music:** song 1, started before the first picture.
- `fade_to` and `fade_out` take a second argument that **nothing reads**.

### Rank selection — `rank_select` `0x018262`

- **Screen** `screen_picture`, 320 x 200 x 5.
- **Loads** `shapes/selectrank` as the picture and `shapes/selectrank.shp` as a shape container.
- **Draws** the highlight with `shape_draw_xor(shape, shape->+8, shape->+10)`, that is the shape
  of index `rank_cursor` drawn in XOR at its own stored source position, so that drawing it again
  erases it. After every move: XOR the old one away, XOR the new one in, `view_show_wait`,
  `view_copy(front, back)` so both buffers agree, then `wait_input_release`.
- **Eight entries**, `rank_cursor` (`0x026C64`) 0 to 7 with wrap. 0 to 6 are the seven ranks whose
  names are the pointers of `rank_names` (`0x025910`); 7 opens the load dialog.
- **Keys:** `re/notes/keys.md`. Cursor up and down, Return, keypad Enter, the stick and the
  button.
- **Timeout:** 1800 rounds of `menu_input` set `demo_mode` to 1, which asks for `wofdemo`; that
  file is not on this disk, so `demo_mode` falls back to 0 and a mission starts.
- **After a choice:** if the cursor is 7 the load dialog runs; a loaded game sets `0x026D40` and
  leaves `rank_select`, a cancel rebuilds the picture and goes back to the menu. Otherwise the
  shapes are freed, the screen fades out and, when `0x026F86` is set, a `0x1388`-byte demo
  recording buffer is allocated and `demo_mode` becomes 2. The chosen rank is stored in
  `0x025558` and `0x0253BE`. The return value, `0x023650[rank]`, has no caller that uses it.
- **Music:** song 4.

### Briefing — `mission_briefing` `0x018590`

- **Screen** `screen_hires3` (`0x016B04`): two views, 640 x 147 x 3.
- **Loads** nothing: the background is the shape named `rank` out of `world.shp`, found with
  `shape_find(world_container, 'rank')`.
- **Draws**, all on `back_rastport`, clipping full:
  - `shape_draw(rank shape, 320 - 4 * width_bytes, 101 - height / 2)`, which is (192, 54) for this
    shape: centred on (320, 101).
  - `Move(296, 61)`, `text_draw(rank_names[rank])` — the rank's name, in the **game font**.
  - `Move(340, 73)`, `text_draw(sprintf("%d", 0x0253C0))` — the mission number.
  - `Move(340, 119)`, `text_draw(sprintf("%d", byte at 0x025382))`.
  - `Move(340, 131)`, `text_draw(sprintf("%d", byte at 0x025370))`.
  What the last two count belongs to M7; they are one digit each at the start of a campaign.
- **Colours:** `bcopy(briefing_palette 0x02592C, local, 0x20)` — 16 words — then
  `view_show_wait`, `fade_to(local)`.
- **Waits** 240 rounds of `WaitTOF`, ending early on fire.
- **Keys:** Control and `r` fade out and **return 1**, on which `main` jumps back to the top of the
  outer loop, so the rank selection comes again. Any other key is dropped.
- **Music:** none of its own.

### Load and save dialog — `load_save_dialog` `0x018B96`

`load_save_dialog(mode)`, mode 0 load, 1 save; returns 0 when a game was loaded or saved.

- **Screen** `screen_dialog` (`0x0169A4`): the **back view only**, 320 x 200 x 4.
- **Loads** no picture. It draws itself, entirely with `graphics.library` in the **system font**
  (`re/notes/system-font.md`), `SetAPen(0x28F)`, which is pen 15 on four planes, and `SetDrMd(0)`,
  JAM1.
- **Static labels** come from a linked list walked at `0x018BE2`: each item holds the next
  pointer, x, y and the string. Observed for both modes:

  | Position | Text |
  |---|---|
  | (85, 19) | `Load` (`0x019254`, 4) or `Save` (`0x019259`, 4), by the mode |
  | (127, 19) | `Game` (`0x018B80`, 4) |
  | (63, 193) | `Exit Game` (`0x018B85`, 9) |
  | (222, 194) | `Cancel` (`0x018B8F`, 6) |

- **Six file slots**, each an outlined box `Move(43, 59 + 16i)` then `Draw` to (282, 59 + 16i),
  (282, 69 + 16i), (43, 69 + 16i) and back, for i = 0 to 5. The name is drawn at
  (45, 61 + 16i), padded to 28 characters with the 28-space string at `0x017CFC`.
- **Two buttons**, outlined boxes (43, 183)–(147, 199) and (205, 183)–(285, 199).
- **The selection** is one `RectFill(44, 60 + 16i, 281, 68 + 16i)` in `SetDrMd(2)`, COMPLEMENT,
  which is undone by drawing it again.
- **Timing:** `view_show_wait`, `fade_to`, then the loop; `fade_out` on the way out.

**The file list** (`dialog_file_list` `0x018A06`), observed in
`test_the_dialog_lists_the_saved_games_of_the_disk`:

1. clears the six 29-byte name slots at `0x027C7E`;
2. `mem_alloc(0x104)` for a `FileInfoBlock`;
3. `Lock(0, ACCESS_READ)` — a **NULL name**, which is the current directory, the game's own;
4. `Examine`, then `ExNext` until it fails, at most six kept;
5. an entry is kept when `tolower` of `fib_FileName[0..2]` is `w`, `o`, `f`, `fib_FileName[3]` is
   `.`, and `fib_FileName[4]` is not 0. `fib_DirEntryType` is **not** checked, so a directory
   whose name begins `wof.` would be listed;
6. the part **after** `wof.` is `strncpy`'d, 27 bytes, into slot i at `0x027C7E + 29i` and copied
   again into `0x027D2C + 29i`;
7. `UnLock`, `mem_free`, and the count is returned.

There is **no sorting and no filtering beyond the prefix**: the list is `ExNext` order. On this
disk that gives one entry, `mission 3`, from `wof.mission 3`. What the port must do to show the
same list is in **The order of the file list** below.

**The loop.** A cursor, 0 to 7: 0 to 5 are the slots, 6 and 7 the two buttons. In **load** mode
`menu_input` moves it and Return picks. In **save** mode a cursor on a slot goes straight into
`text_input` (`0x016086`) on that slot's name, so a name can be typed over the one that is there;
leaving the editor upward or downward moves to the next slot. On accept, the name is run through
`path_sanitise` (`0x016592`), which turns `:` and `/` into spaces, `wof.` is put in front, and
`Loading game...` (`0x019263`, 15) or `Saving game...` (`0x019273`, 14) is drawn.

Observed: saving over a slot that already held a name **writes the new file and deletes the old
one** (`test_a_save_writes_a_wof_file_and_replaces_the_one_it_was_edited_from`), so editing a name
renames the save. A save on this disk is **4258 bytes**; its layout belongs to M7.

**The return from the in-game dialog.** `ingame_keys` calls the dialog, then
`screen_game_restore` (`0x016D32`), which rebuilds the play screen in the back view and copies
bitmaps and colours over from the front view with `view_copy`, and then `input_queue_clear`. After
a **successful load** it does more: `load_dash_assets`, `mission_briefing`, `0x01EDAA`,
`mission_display_setup`, `load_ship_shapes`, `build_master_lists`, `sounds_load`, one `logic_tick`
and `input_queue_clear`.

### High-score display — `high_score_screen` `0x019856`

- The 360-byte table is a **local of this routine**, at `-0x21A(a5)`; `high_score_table`
  (`0x027DDA`) points at it and is valid only while the screen runs.
- `music_start("wofsongs", 0)` — **song 0**.
- `high_score_entry` (`0x019472`) runs **first**, before the screen is built, and may put up its
  own dialog screen (below).
- `screen_hiscore` (`0x016D7A`): one view, 320 x 75 x 5 at line 0 and 640 x 145 x 4 at line 76.
- `load_picture_black("shapes/hiscoreslab")` into the **second** viewport, then the ten lines are
  drawn on it, then `load_picture_black("shapes/hiscore.iff")` into the **first**.
  `hiscoreslab` is 256 rows high and shows its first 145.
- `view_show_wait`, `fade_to_pair(first viewport's colours, second viewport's colours)`.
- **Waits 1800 rounds**, ending early on fire, then `fade_out_pair`.

**The ten lines** (`high_score_draw` `0x01967E`), in the system font on the second viewport: three
passes over the same ten entries, with `hiscore_offsets` (`0x025A56`) = −1, 1, 0 and
`hiscore_pens` (`0x025A50`) = 0, 0, 15. Pass p draws every entry at
x = offset[p] + 13 + column and y = offset[p] + 12 * i + 6, so the text gets a black outline one
pixel up-left and one down-right before the white text goes on top. The four columns are the
position `"%d"` at +0, the score `"%-6ld"` at +0x28, the rank name `"%-12s"` from
`rank_names[entry.rank]` at +0x96, and the name at +0x12C. An entry whose score is 0 is skipped.

### High-score name entry — `high_score_entry` `0x019472`

- Reads the file (`high_score_load`), sorts it, and **returns at once** unless the player's score
  at `0x02534C` is greater than entry 9's score. Only then does a screen appear.
- **Screen** `screen_dialog`, the back view only, 320 x 200 x 4, system font.
- `SetAPen(8)`, `SetDrMd(0)`; `Move(52, 83)`, `Text(0x01964E, 26)`; `Move(91, 92)`,
  `Text(0x019669, 20)` — the two lines that say whose name is wanted.
- `SetAPen(2)`, then a rectangle outline (80, 100) – (225, 113) drawn with four `Draw` calls.
- `bcopy(dialog_palette 0x025A5C, local, 0x20)`, `view_show_wait`, `fade_to(local)`.
- `text_input(buffer, 16, 82, 102, 10000)` — the editor of `re/notes/keys.md`, so at most **16
  characters**.
- The score goes into **entry 9**, the name with `strncpy(..., 17)` and the rank word from
  `0x0253BE`; then `fade_out`, sort, write. `re/notes/highscore.md` has the layout and the test
  that an inserted score lands where it belongs.

## The outer loop, as a state diagram

`main` (`0x010006`), outer loop at `0x010066`. Conditions are the words and flags the code tests.

```text
  init, crack_text_screen
        │
        ▼
  title_sequence            story scroller, logo, title, credits; fire skips
        │
        ▼
  ┌─► outer loop 0x010066
  │     free_mission_assets; opt_music_off = 0; end_of_mission = 0; demo_mode = 0;
  │     quit_flag = 0; 0x013562 (reset)
  │         │
  │         ▼
  │     rank_select ──── cursor 7 ──► load_save_dialog(load)
  │         │                            │ loaded: 0x026D40 = 1 ──┐
  │         │                            └ cancelled ─► back to the menu
  │         ▼                                                      │
  │     load_dash_assets;  0x026D40 == 0 ? 0x012ADC  ◄─────────────┘
  │         │
  │         ▼
  │     mission_briefing ── returns 1 (Control-R) ──────────────────► outer loop
  │         │ returns 0
  │         ▼
  │     mission_display_setup, load_ship_shapes, build_master_lists, sounds_load,
  │     0x026D40 == 0 ? player reset 0x0135A8 + 0x013684;  logic_tick; input_queue_clear
  │         │
  │         ▼
  │  ┌─► inner loop 0x01010E
  │  │     ingame_keys                 the Control commands, Escape, the cheats
  │  │     quit_flag      ───────────────────────────────► end of the mission
  │  │     pause_flag     ── wait_next_vblank ──┐
  │  │     0x025364 and 0x0253BC set  ──► next mission:
  │  │         ticker_clear, fade_out_pair, free_mission_assets, choose_night,
  │  │         mission_briefing ── returns non-zero ──────► outer loop
  │  │         else reload the assets and go on
  │  │     frame_update (one pass)                        │
  │  │     run_queued_ticks                               │
  │  │     end_of_mission 0x0255C0 ──────────────────────────► outer loop
  │  └─────────────────────────────────────────────────────┘
  │         │ quit_flag
  │         ▼
  │     0x011F4E, ticker_clear, fade_out_pair
  │     0x026F8C = (demo_mode == 1)
  │     0x01852A                       demo recording writes wofdemo
  │     0x026F80 set ─────────────────────────────────► fatal_exit, the program ends
  │         │
  │         ▼
  │     0x026F8C set (a demo was played back) ─── yes ──┐
  │         │ no                                        │
  │         ▼                                           │
  │     free_mission_assets; high_score_screen          │
  │         │ high_score_entry asks for a name only     │
  │         │ when 0x02534C beats entry 9               │
  │         ▼                                           │
  └─────────┴───────────────────────────────────────────┘
```

**The demo request** is not a state of its own: `rank_select` sets `demo_mode` to 1 when
`menu_input` times out, loads `wofdemo` and falls back to 0 when the file is not there, which on
this disk it never is. Recording, `demo_mode` 2, is entered when `0x026F86` holds a file name.

**What decides whether the high-score entry appears**: two things in sequence. The screen itself
is skipped when the run was a demo playback (`0x026F8C`); the name entry inside it is skipped
unless `0x02534C`, the player's score, is greater than the tenth entry's score. The first is
observed above; the second is read from `0x0194A0`–`0x0194A8` and its consequence — the sort and
the write — is observed in `re/notes/highscore.md`.

**The manual's Control-D**, which shows the high scores, is not in this executable: the screen is
reached only from the end of the outer loop (`re/notes/keys.md`).

## The order of the file list

`ExNext` walks a directory in the file system's own order: hash chain 0 upward and inside a chain
from its head. The chain is `hash(name) % 72`, where

```text
hash = length of the name
for each letter: hash = (hash * 13 + upper(letter)) & 0x7FF
```

and `upper` is plain ASCII, because an old file system disk is not international. Every entry of
five directory blocks of `original/wof.adf` has the chain that hash gives
(`test_the_disk_image_gives_the_order_the_file_system_hands_out`), and the game's own directory
comes out as

```text
Wings  wingt  .info  shapes  wofsongs  wings.info  maps  sounds  UFXintro
highscore  songplay  newarmyfont  rank.iff.info  wof.mission 3
```

which is not the alphabet. The harness serves exactly that order
(`headless_os.adf_order`), and puts a file a run has saved at the head of its own chain, which is
where a real file system puts a new entry.

**For the port.** The virtual file system has to keep a per-directory order, not sort by name, or
the list of saved games comes out in a different order than on the Amiga. Two things follow: the
order of the files that come from the disk should be baked in at build time from `wof.adf`, and a
game saved in the browser should be inserted at the head of its chain, as the harness does. That a
real Kickstart 1.3 `ExNext` visits the chains in exactly this order is documented file-system
behaviour; it was **not** checked against a real machine here.

## Sky flash

`flip_buffers` pokes `COLOR01` of the back copper list while `flash_count` (`0x025416`) is not 0
(`re/notes/display.md`). Written by:

| Address | In | What it writes |
|---|---|---|
| `0x013698` | the player reset `0x013684` | `flash_count = 0` |
| `0x01CAB4` | `flash_set(count, colour)`, called from `0x01AFBA` | both, from its arguments |
| `0x01470E`, `0x0149A6`, `0x0149DC` | the weapon and explosion code | `count = 5`, `colour = 0xFFF` |
| `0x014744`, `0x014812`, `0x01485C`, `0x0149BC`, `0x014A42` | the same region | `colour = 0xF00` |

Read only by `flip_buffers` (`0x01031A`, `0x010322`, `0x01032C`). **Not observed:** a flight of
600 ticks that takes off, climbs and fires never wrote either word, so the flash comes from
something the script did not reach — a bomb or a shell hitting the ground. The observation belongs
to M5, where those routines are ported.

## What M3 has to build

- `wait_frames_or_fire`, `menu_input` and `wait_input_release` as coroutines: each of their rounds
  is one `CO_WAIT` on the next VBlank (`SPEC.md` section 6.3).
- The fades as they are (`colour_lerp`, `re/notes/display.md`), with a chosen number of VBlanks per
  step, because the original's is CPU time and is not established.
- `load_picture_black` into the back view and the show-then-fade order, which is what keeps a
  picture from ever being seen while it is decoded.
- `graphics.library` `Move`, `Text`, `RectFill`, `Draw`, `SetAPen`, `SetBPen`, `SetDrMd` on the
  indexed framebuffer, with JAM1, JAM2 and COMPLEMENT, and the system font of
  `re/notes/system-font.md`. The dialogs and the high-score list use nothing else.
- A per-directory file order in the virtual file system, and `localStorage` behind it
  (`SPEC.md` section 6.2).
