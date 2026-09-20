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

Seven scripts, together 8,000 ticks and 16,000 passes (observed):

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
from world x 4,200 on. One of them hits a barracks at tick 850: the score rises by 200 and six
soldiers appear in the soldier table (observed, `pass_observe.py` script `bomb`).

## The answer

Over the seven runs a pass wrote **367 ranges**, merged to 171 neighbouring blocks, and a tick
read **62 of those blocks**. The full table is one command:

```text
.venv/bin/python tools/pass_observe.py --out TABLE.txt
```

What crosses from the pass into the tick is this, and nothing else (observed):

| Written in a pass | By | Read in a tick by | What it is |
|---|---|---|---|
| `object_records` `+0x0C` of each of the 16 records | `snapshot_for_draw` | `0x011AE2` | the drawing copy the logic reads back |
| `object_records` `+0x20` of each record | `0x010702`, in `draw_world`'s tree | `0x0107F2`, `0x010820`, `0x010A72`, `0x010AA6` | the record's kind: **the pass frees and changes object records** |
| `pass_counter` `0x0253C8` | `draw_world` | `0x010AA6`, `0x011460`, `0x013684` | the pass counter, 0 to 99 |
| `frame_drawn` `0x026E3C` | `frame_update` | `0x010AA6` | a frame was drawn since the last tick |
| `0x026E60` | `snapshot_for_draw`, `0x0103A6` | `0x010820` | the drawing's copy of the player height |
| `0x027164`–`0x027167` | `draw_world` | `0x012132` | a distance-derived value the sound engine uses |
| the four pools of `alloc_pools` | `0x0152F8`, `0x010EE0`, `0x015460` | `0x0152B0` | ricochets, splashes, smoke, balloons: **the pass spawns them** |
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

The rest of what a pass writes is drawing state that no tick reads: `snapshot_for_draw`'s
copies (47 blocks), the map window of the dashboard, the blitter's parameter block, the copper
lists and the sky flash.

### What a pass reads of the tick

The other direction is the one `re/notes/drawing.md` already described and this run confirms:
`snapshot_for_draw` copies the logic's positions and frames into the fields the drawing reads,
between `Forbid` and `Permit`, and `draw_world` takes `view_x`, `view_y`, `view_shift` and
`view_step` from what `frame_update` computed out of the player's position.

## The control: one, two and three VBlanks per pass

The same script at three pass rates, over an **entropy stream of one constant value**
(`{"entropy": {"constant": 10304}}`), so that the three runs see the same stream although a
pass consumes entropy. Compared is the state at the same tick number, byte by byte
(`tools/pass_observe.py --control`, observed):

```text
  1 VBlanks per pass: 873 passes, 1005 VBlanks at tick 220
  2 VBlanks per pass: 437 passes, 1005 VBlanks at tick 220
  3 VBlanks per pass: 292 passes, 1006 VBlanks at tick 220
51 bytes differ; 43 of them were written by a pass, 3 only by a VBlank server, 5 by neither
```

Of 20,996 bytes of state, **51 differ after 220 ticks** although the pass rate is three times
apart, and every one of them is explained:

- **43 bytes were written in phase `F`**: the pass counter, the sky split row, the
  `snapshot_for_draw` copies, the plane and view pointers of the double buffer, the copper
  list pointers and two bytes of the sound engine's queue. Every one is a row of the table
  above or a drawing range beside it.
- **4 bytes were written by a VBlank server** (`vblank_total`, `vblank_counter`,
  `vblank_divider`, one sound slot): the three runs stand at 1005, 1005 and 1006 VBlanks at
  tick 220, because a pass waits for a VBlank of its own, so they are one VBlank apart.
- **4 bytes were written inside a tick** and differ because that tick read a coupled range:
  `0x027352` by `0x011460`, which reads `pass_counter`, and three bytes of the sound engine by
  `0x01EAC0`, which `0x012132` drives from `0x027164`.

**Everything else is identical at equal tick numbers**, including the player's record, the
enemy aircraft, the map, the score and the input queue. The tick is therefore a function of
the input bytes and the entropy stream alone, as long as the coupled ranges above are
reproduced; the pass rate changes only them.

## What this does not answer

**How many VBlanks a pass takes on a real A500** is not answerable here and is not attempted:
the harness has no cycle model. It sets the speed of the soldiers, of the game over countdown,
of the object animation and of everything else in the table, so the port needs a measurement
from the owner's machine or from a cycle-exact emulator. Until then the harness and the port
use two VBlanks per pass, which is a setting, not a finding.

## Open

- Which object each of the pass's spawn sites makes, and what the four pools hold, is point 3
  (`re/notes/objects.md`).
- `0x01AF7C`, the routine the player update runs while the aircraft is in the water, was read
  only as far as the restart it ends in.
- The sky flash, which `re/notes/frontend.md` names writers for, was not provoked by any of
  the seven scripts.
