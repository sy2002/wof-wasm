# Per-tick and per-pass state

Answers point 2 of `SPEC.md` section 10, except the one part of it that reading cannot give:
how many VBlanks a pass takes on a real A500. Addresses use the standard load layout.

Every finding is marked **observed**, with the run that shows it, or **read**, which means it
comes from the listing alone.

```text
tools/pass_observe.py     the seven scripts, the table, the pass-rate control
tools/headless_writes.py  the phase-aware write summary and the read hook behind them
tests/test_passes.py      the claims of this note over a short script, in the suite
```

## What the question is

`frame_update` (`0x010228`) is not a renderer. It runs game logic once per pass: the soldiers
move and die there, score is added, ticker messages are queued, objects are spawned, and the
restart after a lost aircraft and the game over countdown advance. The logic tick runs at a
quarter of the VBlank rate; a pass runs as often as the machine manages. **So how passes and
ticks interleave is an input of the simulation**, and the port has to know exactly which state
crosses from one to the other.

## The instrument

Every write and every read of a run is tagged with the phase it was made in: `V` inside a
VBlank's key handlers and servers, `T` inside `logic_tick`'s tree, `F` inside `frame_update`'s
tree, `M` in the main program outside all three (`re/notes/headless.md`, "Write summary, read
hook"). `tools/pass_observe.py` runs a script twice: the first run says which ranges phase `F`
wrote, the second watches reads of exactly those ranges and says who reads them in a tick.

Seven scripts, together 5,310 ticks and about 10,600 passes (observed; the table's ticks sum to 5,310, and a re-run of the seven at 5302294 counted 10,572 passes):

| Script | What it covers | Ticks |
|---|---|---|
| `deck` | a mission left alone on the carrier | 468 |
| `flight` | the take-off and level flight | 568 |
| `climb` | climbing, diving and turning both ways | 668 |
| `guns` | the same with the guns firing | 568 |
| `bomb` | a bomb on an island, which brings its soldiers out | 1068 |
| `lost` | the aircraft over the bow, the sinking and the restart | 618 |
| `gameover` | every life used up, to the end of the mission | 1352 |

Reaching an island took some care: the other weapon is dropped with a short click of the
button (the manual, page 7), the island of map `a` lies about 3,000 pixels left of the
carrier, and a turn after the take-off dives the aircraft, so the script turns, levels out
with a short push forward, flies left at ten pixels a tick and drops a bomb every four ticks
from world x 4,200 on. One of them hits a dug-out (slot 3) at tick 850: the score rises by 200
and six soldiers appear in the soldier table (observed, `pass_observe.py` script `bomb`; a hit
on a dug-out with soldiers inside scores 200, one on a barracks 150, as the bombs of
`tools/m5_scripts.py`'s `bomb_a` show, re/notes/porting-m5.md).

## The answer

Over the seven runs a pass wrote **367 ranges**, merged to 171 neighbouring blocks, and a tick
read **62 of those blocks**. The full table is one command:

```text
.venv/bin/python tools/pass_observe.py --out TABLE.txt
```

What the seven runs saw cross from the pass into the tick is this (observed). It is a
**lower bound**, not the whole: a coupling only shows up here if a script reached it, and the
table below this one lists the ones that are read but that no script reached.

| Written in a pass | By | Read in a tick by | What it is |
|---|---|---|---|
| `object_records` `+0x0C` of each of the fifteen records | `snapshot_for_draw` | `0x011AE2` | the drawing copy the logic reads back |
| `object_records` `+0x20` of each record | `0x010702`, in `draw_world`'s tree | `0x0107F2`, `0x010820`, `0x010A72`, `0x010AA6` | the record's kind: **the pass frees and changes object records** |
| `pass_counter` `0x0253C8` | `draw_world` | `0x010AA6`, `0x011460`, `0x013684` | the pass counter, 0 to 99 |
| `frame_drawn` `0x026E3C` | `frame_update` | `0x010AA6` | a frame was drawn since the last tick |
| `0x026E60` | `snapshot_for_draw`, `0x0103A6` | `0x010820` | the drawing's copy of the player height |
| `0x027164`–`0x027167` | `draw_world` | `0x012132` | a distance-derived value the sound engine uses |
| the four pools of `alloc_pools` | `0x0152F8`, `0x010EE0`, `0x015460` | `0x0152B0` | splashes, smoke and balloons: the pass draws them, counts their records down and frees them, and claims smoke's (`smoke_claim`); the tick's `splash_spawn` takes a free splash record (from `gun_splashes`, `object_step`, the player's crash and the enemy's splash), `engine_smoke` claims smoke through `smoke_at_player`, and `balloons_step` steps the balloons the pass's `balloons_draw` drew, in `balloons_c` alone. Nothing writes the Ricochet pool in any script (`re/notes/porting-m5.md`, the pools) |
| `soldier_records` | `0x013EEE` | `0x011E82`, `0x011A8C` | the soldiers, which live entirely in the pass |
| `clip_top` … `clip_right_incl` | `clip_set` and the scene routines | `clip_set`, `rect_fill` | the blitter library's clip rectangle |
| `draw_rastport`, `draw_bitmap`, `back_rastport`, `back_vport`, `front_vport`, `back_view`, `front_view` | `draw_set_target`, `view_show` | `rect_fill_aligned`, `flip_buffers`, `view_show`, `player_lost_restart` | the drawing target and the double buffer |

The last two rows are the surprise: **the tick draws too.** In the `lost` run the restart
`player_lost_restart` (`0x0135D8`) ran inside `logic_tick`'s tree and called `draw_set_target`,
`clip_playfield` and `rect_fill` there (observed). It was reached from `0x01AF7C`, which the
player update `0x01C660` calls on every tick while the aircraft is in the water, and which
calls the restart at the tick where the wait is over. `re/notes/drawing.md` has the restart in
`frame_update`'s list only; in these seven runs `frame_update`'s own call, guarded by
`0x024F24`, was never taken, and every entry came from the tick or from the mission setup.
Both callers exist; the port has to keep the drawing globals shared between the two trees.

The rest of what a pass writes is drawing state that no tick read in these runs:
`snapshot_for_draw`'s copies (47 blocks), the map window of the dashboard, the blitter's
parameter block, the copper lists and the sky flash.

### The couplings the seven scripts did not reach

These are in the listing and in `re/notes/drawing.md` but absent from the table above,
because no script of this note met the condition that exercises them. The scripts of M5
(`tools/m5_scripts.py`) reach the first two, and `tools/m5_observe.py couplings` hooks the
writes over `island_a`, `guns_a` and `hit_a` (observed):

| Written in a pass | By | Read in a tick by | What the M5 scripts show |
|---|---|---|---|
| `player_score` `0x02534C` and `island_score` `0x025450` | `0x013EEE`, which adds `0x19` per soldier and takes one off the island's count | `0x011CD8`, `0x0146DC` | **a soldier dies in a pass.** `soldiers_draw` writes `player_score` 21 times in `island_a`, twenty soldiers and the island's bonus, and `island_score` 20 times, every one in phase F. The guns bring the soldiers down in the tick (`0x011A8C` puts them in state 2); the pass counts their dying frames and scores |
| `0x02508A`, the player's record `+0x12` | `0x014F5C`, `target_fire`, under `draw_world` | `logic_tick`, `0x011BFC` (both observed as readers) | **the oil falls in a pass**: `target_fire` writes it 2 times in `guns_a`, 15 in `hit_a`, 11 in `island_a`. A target's hit counts `+0x10` down every time; the oil falls only when that count runs out, which is why the seven runs saw `+0x10` written and never `+0x12` |
| whatever `player_lost_restart` writes when `frame_update` calls it | `frame_update`, guarded by `0x024F24` | the readers of the restart's own state | **still unreachable**: nothing writes `0x024F24` in the three scripts, and no instruction of the executable writes it (read) |

The scripts of M6 (`tools/m6_scripts.py`) add one more: **a ship's shell ends a torpedo in a
pass.** `ship_guns_draw` (`0x014C3E`) runs in `draw_world`'s tree and calls `ship_gun_shell`
(`0x014EFC`) for every standing gun of an enemy ship; when a gun shells, it spawns a splash
(the pools' row above) and calls `torpedoes_hit` (`0x011AE2`), which sets `+0x20` to 8 and
`+0x21` to 1 in every torpedo record in the water within ten pixels of the splash, the
object records' and `object_record_extra`'s (`0x025594`) alike, and the tick's object walkers
read `+0x20` (read). Observed: 4,465 entries of `splash_spawn` and as many of
`torpedoes_hit` in phase F over the fourteen ship scripts, with
`tools/reach_observe.py --m6-only`; a torpedo ended that way is read, not observed. The same routine sets
`ship_shell` (`0x026D4A`), which nothing reads, and the ships' guns fire through
`target_fire`, so over a ship the oil falls in a pass as it does over a target.

### What a pass reads of the tick

The other direction is the one `re/notes/drawing.md` already described and this run confirms:
`snapshot_for_draw` copies the logic's positions and frames into the fields the drawing reads,
between `Forbid` and `Permit`, and `draw_world` takes `view_x`, `view_y`, `view_shift` and
`view_step` from what `frame_update` computed out of the player's position.

## The control: one, two and three VBlanks per pass

The same script at three pass rates, over an **entropy stream of one constant value**
(`{"entropy": {"constant": 10304}}`), so that the three runs see the same stream although a
pass consumes entropy. `tools/pass_observe.py --control --runs NAME --ticks N` then compares
their state at the same tick number, byte by byte, and:

- **checks that the three runs fed the tick the same input bytes.** They are the schedule's
  own `T` entries; if they differed the comparison would say nothing at all. They are equal in
  every run below.
- takes the writer of every byte **from the three compared runs themselves**, so a byte that
  only these runs write is still attributed;
- asks one more run of the same script, with a read hook over exactly the ranges a pass wrote,
  which routines read them inside a tick;
- and puts every differing byte into one of four classes, the last of which is a finding:
  written by a pass; written only by a VBlank server or something it calls; written in a tick
  by a routine that reads a pass-written range; written in a tick by a routine such a reader
  calls. A VBlank can happen inside a tick — the restart spins on `WaitTOF` there — so a
  server is recognised by its routine and not by the phase the write was tagged with.

Three scripts, the third of them run twice as far as the other two and through the restart
(observed):

| Script | Ticks | Passes at 1, 2, 3 VBlanks | VBlanks there | Bytes that differ | Left over |
|---|---|---|---|---|---|
| `flight` | 220 | 873, 437, 292 | 1005, 1005, 1006 | 51: 43 by a pass, 1 by a reader, 3 below one, 4 by a VBlank server | none |
| `lost` | 600 | 2373, 1188, 793 | 2525, 2526, 2527 | 82: 49 by a pass, 27 by a reader, 2 below one, 4 by a VBlank server | none |
| `bomb` | 1050 | 4193, 2097, 1399 | 4325, 4325, 4327 | 121: 61 by a pass, 54 by a reader, 2 below one, 4 by a VBlank server | none |

The first script is level flight with nothing in the air; the second flies the aircraft into
the sea and through the restart, which is where the tick itself draws; the third drops twenty
bombs, brings soldiers out of a barracks and keeps fifteen object records turning over. Of
about 21,000 bytes of state, the hardest of the three differs in 121 after 1,050 ticks
although the pass rate is three times apart, and **every one of them is explained**:

- a pass wrote it, which means it is a row of the table above or a drawing range beside it;
- or a VBlank server wrote it (`vblank_total`, `vblank_counter`, `vblank_divider` and one
  sound slot), and the runs stand one or two VBlanks apart at the same tick, because a pass
  waits for a VBlank of its own;
- or a tick wrote it, and the routine that did is one that reads a coupled range —
  `object_spawn`, `0x010AA6`, `0x0152B0`, `0x011E82`, `0x011460`, `0x013684` — or one such a
  reader calls, which is how the sound engine's `0x01EAC0` comes in behind `0x012132`.

**Everything else is identical at equal tick numbers**, including the map, the input queue and
the tick's own input bytes. The tick is therefore a function of the input bytes and the
entropy stream alone, as long as the coupled ranges above are reproduced; the pass rate
changes only them.

## What this does not answer

**How many VBlanks a pass takes on a real machine** is not answerable here: the harness has
no cycle model. It sets the speed of the soldiers, of the game over countdown, of the object
animation and of everything else in the table. The owner's machine answered it, below.

## What the film of the real machine shows

The owner filmed their PAL Amiga's monitor (HDMI out) with a phone at 240 fps on 2026-09-22:
the story scroller, and the hold with the lift, the flag and the aircraft accelerating on the
deck. The export plays the slowed section at 30 fps, so inside it one video frame is 1/240 s
and a 50 Hz refresh is 4.8 frames. `tools/film_rate.py` decodes the film to 480 x 270 grey,
takes the mean absolute difference of consecutive frames in a crop of the game's picture,
finds the frames where the picture changed as peaks above a moving average, and prints the
histogram of the intervals between them; camera shake does not matter, because consecutive
frames are 4 ms apart.

- **Calibration.** The port's story scroller changes its picture every 2 VBlanks (571 of 585
  intervals over VBlanks 200 to 1400), and its drawing is held to the original VBlank by
  VBlank, so the real machine does the same. The scroller film shows intervals of 9 and 10
  frames, two refreshes: the capture chain resolves every change (observed).
- **The result.** In the sea band below the ship the picture changes every 9 or 10 frames (85
  of 120 intervals are two refreshes), the rest at multiples of it, ten at one refresh and
  four at three: **a pass takes 2 VBlanks on the real machine in this scene** (observed). The
  harness's and the port's setting of 2 is therefore a measurement for a quiet scene.
- **Not measured:** a busy scene, with many objects, soldiers and explosions, where the
  original may need 3 VBlanks for a pass. The port's setting is fixed; if a film shows 3
  there, the port would have to model the load.

## Open

- Which object each of the pass's spawn sites makes, and what the four pools hold, is point 3
  (`re/notes/objects.md`).
- `0x01AF7C`, the routine the player update runs while the aircraft is in the water, was read
  only as far as the restart it ends in.
- The sky flash is provoked by a rocket's hit on land and by a crash on land, in the tick
  (`0x0146DC`), and drawn by the pass (`flip_buffers`); re/notes/porting-m5.md, "The sky's
  flash", has the observation.
