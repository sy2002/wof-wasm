# Display geometry and colours

Answers point 6 of `SPEC.md` section 10. Everything here is read from the disassembly; addresses use the standard load layout.

## Summary

The game does **not** build an AmigaOS View. It keeps its own view and viewport records, writes its own copper lists with a small C library (`0x019958`–`0x01A1F4`) and points the hardware at them by writing `COP1LC` (`0xDFF080`) directly. The OS routines around `0x01F7BE` (`InitVPort`, `GetColorMap`, `MakeVPort`, `MrgCop`) are linked in but **nothing references them**; they are dead code, as is the IFF library next to them that reports errors under the name `ReadIFF`.

- **Play screen:** a 320 x 162 low-resolution playfield with 5 planes at line 0, a 640 x 37 high-resolution dashboard with 4 planes at line 163, and a 640 x 13 high-resolution message ticker with 1 plane at line 201. Lines 162 and 200 are blank. The picture is **214 lines** high, 320 low-resolution pixels wide, at the standard window position.
- **Double buffering:** two complete views, A and B, each with its own bitplanes (playfield and dashboard) and its own copper list. Every pass draws into the back view and then installs the back view's copper list; the swap is one `COP1LC` write. The ticker is single-buffered and shared by both views.
- **Colours** are 12-bit words in per-viewport tables of 32 entries. The copper builder turns a table into `COLORxx` moves. There is no `ColorMap` and no `LoadRGB4`. Colours change either by changing a table and rebuilding the list (picture loads, fades) or by poking a built list in place (sky flash, horizon split line).
- **Palette change part-way down the screen:** yes, two. During play the playfield switches from the sky palette to the ocean palette at a split line that is rewritten every pass, and the ticker text has a fixed ten-line brightness ramp. The story scroller of the front end has its own ramps.
- **Colour cycling:** none. No code reads `CRNG` chunks, and nothing rotates a colour table.
- **Day and night** are two sets of files chosen once per mission by `night_flag`. There is no transition during a mission.

## Records

### View, 14 bytes

Two exist: `view_a` (`0x0279F8`) and `view_b` (`0x027A06`).

| Offset | Size | Meaning |
|---|---|---|
| +0 | word | offset of this view's entry in `view_caches` (`0x027F30`): 0 for A, `0x14` for B. Drawing code keeps per-buffer state there |
| +2 | long | copper list buffer |
| +6 | long | first viewport of the chain |
| +10 | long | bitplane memory of this view |

### Viewport, `0xAC` bytes

Five exist in the BSS part of DATA: `vport_a1` (`0x027748`), `vport_b1` (`0x0277F4`), `vport_a2` (`0x0278A0`), `vport_b2` (`0x02794C`) and `vport_ticker` (`0x027296`).

| Offset | Size | Meaning |
|---|---|---|
| +0x00 | long | next viewport, 0 ends the chain |
| +0x04 | 40 bytes | a graphics.library `BitMap`: BytesPerRow +0x04, Rows +0x06, Depth +0x09, Planes +0x0C |
| +0x2C | 100 bytes | a graphics.library `RastPort`; its BitMap pointer (+0x30) points at +0x04 |
| +0x90 | word | split x, always 0 |
| +0x92 | word | split line, in display lines |
| +0x94 | word | split enabled |
| +0x96 | word | copied between views, never read otherwise |
| +0x98 | long | colour table 1, 32 words |
| +0x9C | long | colour table 2, 32 words, 0 when the viewport has none |
| +0xA0 | word | displayed bytes per row. Above `0x3C` the viewport is high resolution |
| +0xA2 | word | displayed rows |
| +0xA4 | word | x position, always 0 |
| +0xA6 | word | y position in display lines; line 0 is beam line `0x2C` |
| +0xA8 | word | width in pixels |
| +0xAA | word | height in rows |

Colour tables are fixed: `coltab_a1` `0x027A18`, `coltab_b1` `0x027A58`, `coltab_a2` `0x027A98`, `coltab_b2` `0x027AD8`, `coltab_ticker` `0x027B18`, and as table 2 of the two first viewports `coltab_a1_split` `0x027B58` and `coltab_b1_split` `0x027B98`. Only the first viewport of each view has a table 2.

### Copper list buffer

| Offset | Size | Meaning |
|---|---|---|
| +0 | word | capacity in entries |
| +2 | word | entries used |
| +4 | 4 bytes each | copper instructions |

`cop_install` writes the end marker `0xFFFFFFFE` behind the last used entry and loads `COP1LC` with buffer + 4.

## Memory

`display_init` (`0x016670`), called once from `main`, allocates everything from chip memory and never resizes it:

| Global | Size | Use |
|---|---|---|
| `cop_blank` `0x026D46` | `0x90` | copper list with `BPLCON0 = 0x0200`, `COLOR00 = 0`, sprites off: a black screen, shown between screens |
| `null_sprite` `0x027A14` | 16 | zeroes; all eight sprite pointers point here. The game uses no sprites |
| `view_a_planes` `0x027C58` | `0x159A0` | bitplanes of both views; `view_b_planes` (`0x027C5C`) is this + `0xACD0` |
| copper buffers at `0x0279FA`, `0x027A08`, `cop_spare` `0x027C64` | 1000 each | view A, view B, and a spare that fades swap in |
| `ticker_plane` `0x027C60` | `0x444` | 84 x 13 bytes |

`0xACD0` is 44,240 bytes, exactly the play screen: 40 x 162 x 5 for the playfield plus 80 x 37 x 4 for the dashboard. `view_layout` (`0x01692C`) clears that many bytes with `BltClear`, then `vport_init_bitmap` (`0x0167F2`) hands each viewport of the chain its planes one after another from the view's memory and calls `InitBitMap` and `InitRastPort`. Plane size is displayed bytes per row times height, with the width rounded up to 16 pixels.

The high-score screen needs 61,400 bytes and runs over into view B's half. It uses view A alone, so nothing is lost.

## Screens

Each screen is set up by one routine that fills in sizes and depths and calls `view_layout`. All viewports are at x 0. Low resolution is `BPLCON0 = 0x5200` for 5 planes; high resolution sets bit 15, giving `0xC200` for 4 planes and `0x9200` for 1. No dual playfield, no HAM, no extra-halfbrite, no interlace.

| Routine | Views | Viewports (width x height x planes, y) | Used by |
|---|---|---|---|
| `screen_game` `0x016CC6` with `view_set_game` `0x016C38` | A and B | 320 x 162 x 5 at 0; 640 x 37 x 4 at 163; ticker 640 x 13 x 1 at 201 | play, `mission_display_setup` `0x018806` |
| `screen_picture` `0x016AD8` | A and B | 320 x 200 x 5 at 0 | publisher logo, title, credits (`0x018022`), rank selection (`0x018262`) |
| `screen_story` `0x016A60` | A and B | 640 x 200 x 1 at 5, 230 rows shown | story scroller `story_screen` `0x017E80` |
| `screen_hires3` `0x016B04` | A and B | 640 x 147 x 3 at 0 | `0x018590` |
| `screen_hires2` `0x016B60` | A and B | 640 x 200 x 2 at 0 | the crack's text screen `0x01F41A` |
| `screen_dialog` `0x0169A4` | back view only | 320 x 200 x 4 at 0 | load and save dialog `0x018B96`, high-score entry `0x019472` |
| `screen_hiscore` `0x016D7A` | A only | 320 x 75 x 5 at 0; 640 x 145 x 4 at 76 | high-score display `0x019856` |
| `screen_game_restore` `0x016D32` | back view | as `screen_game` | return from the in-game dialog; copies bitmaps and colours from the front view with `view_copy` `0x01A9CA` |

### The play screen line by line

| Display lines | Content |
|---|---|
| 0–161 | playfield, low resolution, 32 colours, sky palette above the split line and ocean palette below |
| 162 | blank, colour 0 |
| 163–199 | dashboard, high resolution, 16 colours |
| 200 | blank |
| 201–213 | ticker, high resolution, 1 plane, 640 of 672 pixels shown |

Display line 0 is beam line `0x2C`, so the picture ends at beam line 257, inside an NTSC frame. The horizontal window is the standard one: `DIWSTRT` x `0x81`, `DIWSTOP` x `0xC1`, `DDFSTRT` `0x38` and `DDFSTOP` `0xD0` in low resolution, `0x3C` and `0xD4` in high resolution.

The ticker bitmap is 84 bytes wide with 80 shown (`BPL1MOD` = 4). `vblank_server` draws each new glyph into the hidden 32 pixels at byte 80 and shifts the whole plane left by one pixel per VBlank with a `roxl` chain over 42 words x 13 rows (`0x011856`–`0x0118C0`). This is CPU work inside the interrupt, not a blit. The message the pointer `ticker_message` (`0x0257B6`) walks is not a text of the executable: the tick formats it with `sprintf` into `ticker_text` (`0x02716A`, 300 bytes) or `ticker_text_2` (`0x027E00`, 102 bytes) and hands it over through `0x01555A`, which takes it only while no message runs.

### The story scroller

The bitmap is 640 x 200 but 230 rows are displayed from line 5. `story_copper_build` (`0x017D4E`) reloads `BPL1PT` with the start of the plane at the wrap row, so the 200-row bitmap acts as a ring, and adds two 16-line grey ramps on `COLOR01`: `i x 0x111` at lines 5 + i and at lines 201 − i. Text is therefore visible between lines 6 and 200 only. The routine swaps the front view's copper buffer with `cop_spare` before rebuilding, so that the displayed list is never written to. `story_screen` advances `Planes[0]` of the front bitmap by 80 bytes per step.

## The copper builder

`view_build_copper` (`0x01A0D4`) regenerates a view's list from its viewport chain:

1. `BPLCON0 = 0x0200`, then `cop_sprites_off` (`0x01A06C`): 32 moves.
2. For every viewport except the first: `WAIT (0, y − 1)`, `BPLCON0 = 0x0200`. This is what makes the line above each lower viewport blank.
3. A viewport whose y is not at least 2 below the next one's y is skipped.
4. `cop_vport_colours` (`0x019C0A`): `WAIT (0, y − 1)`, then 2^depth moves to `COLOR00` upward from colour table 1.
5. `cop_vport_planes` (`0x019D18`): `WAIT (0, y − 1)`, `BPLCON0 = 0x0200`, `BPLCON1`, `DIWSTRT`, `DIWSTOP`, `DDFSTRT`, `DDFSTOP`, `BPL1MOD`, `BPL2MOD`, the plane pointers, `WAIT (0, y)`, `BPLCON0` with depth and resolution. If the window's stop line is below `0x80`, a further wait and `BPLCON0 = 0x0200` end the viewport. The routine contains clipping and fine-scroll arithmetic for x and y positions outside the screen; with every viewport at x 0 and inside the frame none of it takes effect.
6. If split enabled is set and table 2 exists: the entry index is stored in `cop_split_index` (`0x027C6C`), then `cop_vport_split` (`0x019C80`) emits `WAIT (split x, split line)` and one move for **each colour whose table 2 value differs from table 1**.

`cop_wait` (`0x019A9C`) converts (x, y) to a copper wait: x / 4 x 2 clamped to `0xE2`, y + `0x2C` clamped to `0x106`; beyond beam line 255 it first emits the customary wait for the end of line 255.

In the play screen the list begins: entry 0 `BPLCON0`, entries 1–32 sprites, entry 33 the wait, entry 34 `COLOR00`, entry 35 `COLOR01`.

## Double buffering and the swap

`view_show` (`0x016F20`) installs a view's copper list with `cop_install` (`0x01AA0E`) and sets the working pointers: `front_view` `0x026E30`, `back_view` `0x026E2C`, and for the first viewport of each `front_vport` `0x026E28`, `front_rastport` `0x026E24`, `front_bitmap` `0x026E38`, `back_vport` `0x026E20`, `back_rastport` `0x026E1C`, `back_bitmap` `0x026E34`. It does not wait. `view_show_wait` (`0x016FC4`) adds `wait_vblank`.

One pass of play:

1. `frame_update` (`0x010228`) starts with `wait_vblank` (`0x01AA3E`), which returns as soon as `vblank_flag` (`0x0255BE`) is set and clears it. `vblank_server` sets the flag on every VBlank, and `cop_install` clears it. The wait is therefore for the first VBlank **after the previous pass installed its list**: if one already went by while the logic ticks ran, there is no wait.
2. It selects `back_rastport` as the draw target, draws the playfield, then selects the RastPort of the back view's second viewport and draws the dashboard.
3. It calls `cop_set_split_line` (`0x01876E`) on the back list.
4. It falls into `flip_buffers` (`0x01030C`): the flash poke described below, then `flip_view` (`0x0150B0`), which is `view_show(back_view)`.

The hardware reloads the copper position from `COP1LC` at the next vertical blank, so the new buffer appears then. `vblank_server` takes no part in the swap: it touches neither `COP1LC` nor the view pointers, and it does not read `g_026E3C`, the flag `frame_update` sets just before the swap.

Consequences for the port: a pass is never faster than one per VBlank, and the picture a pass draws becomes visible at the VBlank after the pass ends. The dashboard is double-buffered like the playfield, which is why drawing code keeps per-view state in `view_caches`: each buffer has to be brought up to date separately.

Every global that holds a BitMap, a plane pointer or a RastPort is listed in the two tables above (`view_a_planes`, `view_b_planes`, `ticker_plane`, the five viewport records with their embedded BitMap and RastPort, and the six front and back pointers). `story_screen` is the only code that alters a plane pointer after layout.

## How colours change

| Mechanism | Routine | What it does |
|---|---|---|
| Picture colours | `iff_cmap_to_table` `0x01A1F6` | `CMAP` chunk into colour table 1, at most 32 entries, each component masked to its high nibble |
| Palette files | `cmap_file_to_table` `0x016DD6` | searches the first 4000 bytes for `CMAP`, skips the length, converts 32 triplets as `(r << 4) or g or (b >> 4)` **without masking**. All four files in use have zero low nibbles, so the result equals the masked conversion |
| Day and night | `mission_display_setup` `0x018806` | see below |
| Horizon split | `cop_set_split_line` `0x01876E` | rewrites the split `WAIT` of the back list in place, using `cop_split_index` |
| Sky flash | `flip_buffers` `0x01030C` | pokes `COLOR01` of the back list at buffer + `0x92`: normally table 1 colour 1, but while `flash_count` (`0x025416`) is non-zero it is decremented and odd counts show `flash_colour` (`0x025418`) |
| Ticker ramp | `cop_add_ticker_ramp` `0x0187BA` | ten `WAIT (0, 201 + i)`, `COLOR01` pairs from `ticker_ramp` (`0x025994`): 777 999 BBB DDD FFF DDD BBB 999 777 555 |
| Fades | `fade_to` `0x017084`, `fade_to_pair` `0x0171F2`, `fade_out` `0x0173B0`, `fade_out_pair` `0x0173E6` | see below |
| View copy | `view_poke_colours1` `0x01A60E`, `view_poke_colours2` `0x01A6AC` | patch the first or second `COLORxx` move of each index in a built list and copy into the table. Every caller rebuilds the list right afterwards |
| Private `CMP2` chunk | `iff_cmp2_to_table` `0x01A284` | split line from the chunk, colour table 2, split enabled. No file on the disk contains the chunk |

### Day and night

`choose_night` (`0x0111FC`), called from `main` only on the way from one mission of a campaign to the next (`0x010160`), so that the first mission of a campaign is always day, looks the map number up in `mission_map_table` (`0x02345F`, index rank x 4 + mission). For map numbers up to 6 `night_flag` is 0. Above 6 it calls `rand_beam` four times and takes the top bit of the last result, so night is an even chance. `night_flag` then selects one file from each of four pairs: `wingspalette` or `night.p` into playfield table 1, `ocean.palette` or `nightocean.p` into playfield table 2, `iff-dash` or `nightdash` as the dashboard picture with its own 16 colours, and `dash.shp` or `nightdash.shp`. `mission_display_setup` loads them into the back view, sets ticker colour 1 to `0x777`, copies everything to the other view with `view_copy`, rebuilds both lists and appends the ticker ramp to both.

Sky and ocean palettes differ in colours 2–15 and 24 by day (15 moves after the split wait) and in 2–15, 20 and 22–24 by night (18 moves). The files `palette` and `ocean.p` are never opened; the executable does not contain their names.

### The split line

`view_set_game` presets the split line to 150. During play `frame_update` computes it every pass: `0x97` plus the amount by which the word at `0x026E60` exceeds `0x83`; when the word at `0x024F36` is 1 it is `0x97` flat. The value is stored in `split_row` (`0x0253A0`) and passed on clamped to 162. At 162 the split falls on the blank line and the ocean palette is never seen. Established: the arithmetic. Inferred: `0x026E60` is the vertical scroll position, so the split follows the horizon.

### Fades

`fade_to(table)` runs 16 steps, step 0 to 15. In each step every colour of the front view's first viewport, in table 1 and in table 2 if present, becomes `colour_lerp(step, start, target)`; then the front view's copper buffer is swapped with `cop_spare`, the list is rebuilt and installed. `fade_to_pair` does the same for two viewports with two targets. **There is no wait inside the loop**: a step lasts as long as the arithmetic and the rebuild take, so the fade's duration is CPU time. A guess from instruction counts is two to four VBlanks per step.

`colour_lerp` (`0x016FF6`) returns the target at step 15. Otherwise it starts from the whole start word and, for blue, green and red in that order, adds a masked quotient into the **whole word**:

```c
r = from;
r += ((((to & 0x00f) - (from & 0x00f)) * step) / 15) & 0x00f;   /* division truncates toward zero */
r += ((((to & 0x0f0) - (from & 0x0f0)) * step) / 15) & 0x0f0;
r += ((((to & 0xf00) - (from & 0xf00)) * step) / 15) & 0xf00;
```

A falling component therefore adds its negative quotient as a masked two's complement value and **carries into the next higher component**: `0x005` towards 0 at step 8 gives `0x013`, and `0xFFF` towards 0 at step 8 gives `0x1887`. The hardware ignores bits 12 to 15. This model agrees with the original under the oracle on 400 random inputs; the port has to keep the arithmetic as it is, because the intermediate colours of every fade-out depend on it.

Pictures appear like this: `load_picture_black` (`0x017422`) decodes the file into the back view, hands the picture's colours to the caller and blacks the table; the caller shows the view and calls `fade_to` with the saved colours. The publisher logo fades first to the fixed `logo_fade_palette` (`0x02594C`), waits 60 frames with `wait_frames_or_fire` (`0x016EEE`, a `WaitTOF` loop), then fades to the picture's own colours.

## How pictures reach a viewport

The ILBM reader in use is `iff_to_vport` (`0x01A548`) with `iff_parse_ilbm` (`0x01A452`); it knows `BMHD`, `CMAP`, `CMP2` and `BODY` and ignores everything else. `iff_body_to_vport` (`0x01A362`) clears the viewport's planes, then decodes min(picture rows, viewport height) rows of min(picture planes, viewport depth) planes with `byterun1_row` (`0x0203E8`), (width + 7) / 8 bytes per row, written back to back. It assumes ByteRun1 without looking at the compression byte and does not skip a mask plane or surplus planes; no file that is loaded needs either. Pictures taller than their viewport are cut off at the bottom: `broderbund`, `wingstitle` and `selectrank` are 256 rows high and show their first 200, and `hiscoreslab` shows its first 145. `shapes/Rank.iff` is on the disk and its name is in DATA at `0x0238C3`, but no code and no table points at that string and no run ever opens the file: the briefing screen draws the shape named `rank` out of `world.shp` instead (`re/notes/frontend.md`).

## Answered elsewhere

`story_screen`, the briefing at `0x018590`, the two dialogs and the high-score screen were read
here only as far as their geometry. What they draw, in what order and with what timing is in
`re/notes/frontend.md`, observed under the headless original. They draw text with
graphics.library `Text` on these RastPorts and never open or set a font, so they use the system
default font, which is not on the game disk (`re/notes/system-font.md`).

## Open

- **Duration of the fades.** Reading cannot settle it. Experiment: count the instructions one step of `fade_to` executes under the oracle for an estimate, or count VBlanks across a fade in a cycle-exact Amiga emulator for the real figure, and give the port a fixed number of VBlanks per step.
- `cop_vport_planes` was read for the case x 0 only. Its clipping branches are unreachable with the positions the game uses and need not be ported.
- The meaning of the words at `0x026E60` and `0x024F36` that drive the split line belongs to the scrolling code of M4.
- The layout of a `view_caches` entry (20 bytes per view), which belongs to the dashboard drawing.
- What sets `flash_count` and `flash_colour`: the writers are named in `re/notes/frontend.md`. They are all in the weapon and explosion code, and no short mission script reached one, so the observation belongs to M5.
