# M4, part 1: the world as a pass

Milestone M4 of `SPEC.md` section 9, its first half: everything the original runs between
the end of the briefing and the first pass of a mission, and everything a pass does, which
is `frame_update`'s tree and the mission half of the VBlank server. The logic tick is
part 2's and is a marked stand-in here. Addresses use the standard load layout.

Every statement is either **observed**, with the tool or test that shows it, or **read**,
which means it comes from the listing alone.

```text
tools/reach_observe.py   what the five mission scripts enter, where, how often; block coverage
tests/m4state.py         the original's state as the port's structs, field by field
src/mission.c            the outer loop's reset, the map loader, the setup after the briefing
src/world.c              frame_update and the playfield half of a pass
src/dash.c               the dashboard's map window and instruments
src/records.def          the record layouts, with the original's offsets
src/mission.def          the tables: fixed ones in DATA and the allocations, at fixed places
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
it can say which of its instructions the five scripts ran (`cold_ranges`). That is what the
cut below rests on.

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
