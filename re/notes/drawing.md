# Drawing routines and read-back

Answers point 7 of `SPEC.md` section 10. Everything here is read from the disassembly; addresses use the standard load layout. The mask handling and the register values of `shape_draw` were confirmed by running it in the oracle with A6 pointing at plain memory.

## Summary

**No game logic depends on a drawing result.** Nothing reads a pixel, a mask, the blitter's zero flag or a collision register. The blitter status is read for one purpose only, waiting until it is idle. A headless run of the original without a blitter model is therefore valid. The evidence is in the section "Read-back" below.

Two things qualify that answer, and both matter for M2 and for the port:

- **The drawing pass is not a pure renderer.** `frame_update` (`0x010228`) also runs game logic once per pass: the soldiers move and die there, score is added, ticker messages are queued, the restart after losing an aircraft happens there, and nine routines in its call tree call `rand_beam`. The headless run must execute `frame_update`, not skip it.
- **Logic reads state that the pass leaves behind**: a flag that a frame was drawn since the last tick, and a pass counter. Logic therefore depends on *how passes and ticks interleave*, which in the original is a matter of CPU speed. Harness and port have to use the same, explicitly chosen schedule.

All shape, rectangle and line drawing goes through one small library of hand-written assembly at `0x0209BC`–`0x0215D8`, outside the region `SPEC.md` names. **Every one of its routines drives the blitter through the custom-chip base**; the CPU only prepares parameters and, in `shape_draw`, builds the transparency mask. The scene routines in `0x010000`–`0x015D62` decide what to draw and call the library. Text is rendered by the CPU into a 1-bit template and put on screen with `BltTemplate`.

`MaskBuffer` is a 1040-byte scratch buffer in chip memory with two users: `shape_draw` writes the union of a shape's planes into it and hands it to the blitter as the cookie-cut mask, and `text_render` writes the text template into it. Nothing else touches it and nothing reads it back.

## The blitter library

`custom_base` (`0x026938`) holds `0xDFF000`. Callers load it into A6, call `blit_begin`, draw, call `blit_end`. Each routine has a twin that takes its arguments from the stack for C callers and does the begin and end itself.

| Address | Name | Arguments | What it does |
|---|---|---|---|
| `0x0212CE` | `blit_begin` | | `OwnBlitter` |
| `0x0212D4` | `blit_end` | | waits until the blitter is idle, `DisownBlitter` |
| `0x02124A` | `draw_set_target` (C: `0x021246`) | A0 = RastPort | stores it in `draw_rastport` (`0x026F1A`) and its BitMap in `draw_bitmap` (`0x02714E`); sets the RastPort's `Mask` byte (`+0x18`) to the depth mask, 5 planes give `0x1F` |
| `0x02129C` | `clip_set` | D0 top, D1 bottom, D2 left, D3 right | bottom and right exclusive; **left and right are rounded down to a multiple of 16** |
| `0x021280` | `clip_set_full` | | the whole target BitMap |
| `0x01524A` | `clip_playfield` | | top 0, bottom 162, left 0, right 320: the whole playfield |
| `0x01525C` | `clip_dash_window` | | top 7, bottom 32, left 256, right 400, a window of the dashboard |
| `0x01F2DC` | `clip_dashboard` | | top 0, bottom 37, left 0, right 640: the whole dashboard |
| `0x01526E` | | | keeps top, left and right and sets the bottom to a row computed from the record at `0x0254D8`, or to 161 when `0x025394` is 0 |
| `0x0209BC` | `blit_clip_setup` | as `shape_blit` | clips against the rectangle, leaves the blit parameters in `0x027F86`–`0x027FA2`, carry set when nothing is visible or the record is null |
| `0x020B0C` | `shape_blit` (C: `0x020AEE`) | A0 = record, A1 = mask or 0, D0 = x, D1 = y | the cookie-cut blit, see below |
| `0x020CE2` | `shape_draw` (C: `0x020CC4`) | the same | chooses the mask when A1 is 0, then `shape_blit`. 16 callers |
| `0x020E24` | `shape_draw_xor` (C: `0x020E0A`) | A0 = record, D0 = x, D1 = y | exclusive-or blit, see below |
| `0x021010` | `rect_fill` (C: `0x020FF2`) | D0 = x0, D1 = y0, D2 = x1, D3 = y1 inclusive, D4 = colour | clamps to the clip rectangle, one blit per plane that sets or clears the rectangle; first and last word masks from `left_mask_table` (`0x026968`) and `right_mask_table` (`0x02698A`) |
| `0x02113E` | `rect_fill_aligned` (C: `0x021120`) | the same | destination-only variant for edges on 16-pixel boundaries; `rect_fill` jumps into it when both edges are aligned |
| `0x021318` | `line_draw` (C: `0x0212FA`) | D0,D1 to D2,D3, D4 = colour | Cohen–Sutherland clipping with `muls`/`divs`, then the blitter's line mode, one line per plane |
| `0x020DEA` | `shape_clear_box` | A0 = record, D0 = x, D1 = y | `rect_fill` of the bounding box with colour 0. Reached only from an entry at `0x020DD0` that nothing calls |
| `0x020F7C` | `blit_raw_unused` (C: `0x020F54`) | three pointers, width, height | no caller |

All callers pass A1 = 0 to `shape_draw` and `shape_blit`. No caller ever supplies a mask of its own.

### What `shape_draw` does, exactly

Let `M` be the depth mask of the target, `clear` and `set` the bytes at `+12` and `+13` of the record, `m[i]` the destination plane mask of stored plane `i` (`re/notes/shapes.md`).

1. **Mask.** Let `size` be width in bytes times height and `n` the number of stored planes.
   - `size` above 1040 (`MaskBuffer_size`): **no mask**, whatever `n` is.
   - otherwise `n` of 2 or more: the CPU writes the OR of all stored planes into `MaskBuffer`; that is the mask.
   - `n` of 1: the stored plane itself is the mask; `MaskBuffer` is not touched.
   - `n` of 0: no mask.
   - `shape_blit` called directly (the dashboard digits at `0x01F2B0`, the two shapes at `0x010344`): no mask.
2. **Blit.** For every pixel of the shape's box that lies inside the clip rectangle and, if there is a mask, has its mask bit set, the destination value `v` becomes:

```c
v &= ~(clear & M);
v |=  (set & M);
for (i = 0; i < n; i++)                 /* in stored order */
    v = (v & ~(m[i] & M)) | (plane_bit(i) ? (m[i] & M) : 0);
```

Planes named by none of `clear`, `set` and `m[i]` keep the destination's bits. Without a mask the whole box is written, so **such a shape is opaque: its colour-0 pixels overwrite the background**.

3. **Clipping is exact to the pixel** on all four sides, and so is the shape's own box. Because left and right clip edges are multiples of 16, the routine gets there with whole-word skips plus first-word and last-word masks; a blit may start one word left of the clip edge, and end one word right of the shape, with those words masked out of the A channel, which leaves the destination unchanged there. The derivation, word by word through the barrel shifter, and the values of `left_mask_table` and `right_mask_table` that make it come out, are in `re/notes/porting-m1.md`; the port therefore clips per pixel and was compared against the original's own register programme for every shape of every container.

In hardware terms: minterm `0xCA` (D = A·B + ¬A·C) with A the mask, shifted by x and 15; phase one with `BLTBDAT` 0 on the clear planes, phase two with `BLTBDAT` `0xFFFF` on the set planes, phase three with B the stored plane on every plane of `m[i]`. Without a mask A is the constant `0xFFFF`. The oracle run showed `BLTCON0` `0x4FCA` for a masked 5-plane shape at x 100 and `0x37CA` for an unmasked one at x 35, with `BLTAPT` pointing at `MaskBuffer`, at plane 0 of a one-plane shape, and unused otherwise.

Eleven shapes exceed 1040 bytes per plane and are therefore always opaque: `fcar`, `mcar`, `rcar` and `rank` in `world.shp`, `batb`, `batf`, `batm`, `crus`, `dstb`, `dstm`, `jrmt` in the ship files. The ten ship and carrier pieces **contain no colour-0 pixel at all**; they carry sky colour 1 around the hull, which shows that the artwork was made for this behaviour. `rank` is two-thirds colour 0 and is drawn on an empty screen.

`shape_draw_xor` uses no mask and ignores `+12`: inside the clipped box it inverts the planes of `set & M` and exclusive-ors each stored plane into the planes of `m[i] & M` (minterm `0x6A`). Drawing twice restores the background. Callers: the rank selection highlight (`0x018262`), and one call each in `0x0103A6` and `0x010DA6`.

A null record draws nothing: `blit_clip_setup` rejects it. Before that, `shape_draw` and the hotspot subtraction of the callers read a few words at addresses 0 to 19, harmless on the Amiga; the port needs the null test up front.

The destination offset is a 16-bit value (`y` times bytes per row plus the word offset of `x`), added with sign extension. Every bitmap of the game is smaller than 32 KB per plane, so this never wraps.

### `line_draw`

After clipping to the inclusive rectangle `clip_left`, `clip_top`, `clip_right − 1`, `clip_bottom − 1` the routine programs a standard blitter line for each plane whose bit is set in the target's `Mask`: `BLTCON0` = (x0 and 15) shifted to the top nibble, or `0x0BCA`; `BLTCON1` from `line_octant_table` (`0x0269AC`: 01 11 09 15 05 19 0D 1D), with bit 6 when 2·dmin − dmax is negative; `BLTADAT` `0x8000`; `BLTBDAT` `0xFFFF` to set the plane or 0 to clear it, by the colour bit; `BLTAPTL` 2·dmin − dmax; `BLTBMOD` 2·dmin; `BLTAMOD` 2·(dmin − dmax); `BLTCMOD` and `BLTDMOD` bytes per row; `BLTSIZE` (dmax + 1) rows by 2. The intersection arithmetic is 16-bit `muls` then `divs`, truncating toward zero. The only caller is `0x0103A6`.

## Text

| Address | Name | What it does |
|---|---|---|
| `0x012794` | `font_load` | loads `newarmyfont`; header: `+0` u16 height (12), `+2` u8 first character (`0x20`), `+3` u8 last (`0x7E`), `+4` one width byte per character. Glyph data starts at `+4` plus the character count rounded up to even (`+100`). Builds `font_glyph_offsets` (`0x026D56`, 96 words): glyph `i` occupies height rows of ((width + 15) / 16) words |
| `0x01591E` | `text_width` | sum over the characters in range of width + 1, where a width of 0 counts as 10; characters outside first to last are skipped |
| `0x015956` | `text_render` | A0 string, D0 length, A1 buffer, D1 x, D2 row, D3 justify width, D4 buffer width, D5 buffer height. Clears the buffer, ORs each glyph in at the pen position by CPU (`lsr.l` into a long), advances by width + 1. A width-0 character draws nothing and advances 11. With D3 above the text width the surplus is spread over the gaps: quotient to every gap, one more pixel to the first *remainder* gaps. Returns the pixel width, or 0 when the text does not fit |
| `0x015A8C` | `text_draw_justified` | (string, length, width): `text_render` into `MaskBuffer` as a 640 x 12 template with 80 bytes per row, then `graphics.BltTemplate` into `draw_rastport` at its pen position, template width by font height. Pens and draw mode are the RastPort's. Caller: `story_screen` `0x017E80` |
| `0x015910` | `text_draw` | (string, length): the same without justification. Caller: `0x018570` |

The size of `MaskBuffer`, `0x410`, is exactly 80 bytes x 13 rows. The justification divides by length − 1 without a test; a one-character string narrower than the requested width would trap. The ticker does not use these routines: `vblank_server` copies glyph words into the ticker plane itself (`re/notes/display.md`).

The front-end dialogs draw text with `graphics.Text` instead (4 callers: `0x016086`, `0x018958`, `0x018B96`, `0x019472`), together with `Move`, `SetAPen`, `SetBPen`, `SetDrMd`, `RectFill` (`0x016032`, `0x017E80`, `0x018B96`) and `Draw` (`0x018B96`, `0x019472`, `0x01F374`). No font is ever set, so that text appears in the system's default font.

## Other drawing

| What | Where | How |
|---|---|---|
| Whole-screen copy between the two buffers | `view_copy_bitmaps` `0x01A834` | `graphics.BltBitMap`, minterm `0xCC`, one call per viewport. The only live `BltBitMap` site; the one at `0x01FE2C` has no caller |
| Clearing planes | `view_layout` `0x01692C`, `ticker_clear` `0x016BBC`, `screen_game` `0x016CC6`, `vport_clear_planes` `0x01A74C` | `graphics.BltClear` |
| Picture decoding | `iff_body_to_vport` `0x01A362`, `byterun1_row` `0x0203E8` | CPU, writes plane rows |
| Ticker | `vblank_server` `0x011856`–`0x01195A` | CPU, in the interrupt: shifts the plane one pixel per VBlank with a `roxl` chain, copies glyph words in. Its decisions use counters and the message pointer, never the plane's content |
| Story scroller | `story_screen` `0x017E80` | moves a plane pointer; text through `text_draw_justified` |
| Mirroring a shape in place | `shape_mirror_x` `0x015B58` | CPU, on shape data, called from logic (`re/notes/shapes.md`) |

There is no scrolling by copying: the playfield is redrawn from the map on every pass.

## The scene routines

`frame_update` calls these in order. Coordinates reach `draw_world_shape` (`0x015174`; A0 = pointer table, D2 = slot, D0 = world x, D1 = world y) as world values; it converts with `view_x` (`0x024F30`), `view_y` (`0x024F32`) and `view_shift` (`0x024F34`, 3 in the eighth-scale view), rejects x outside −128 to 448, subtracts the hotspot and calls `shape_draw`.

| Address | Draws | Through |
|---|---|---|
| `0x01AA3E` `wait_vblank` | nothing; waits for `vblank_flag` | |
| `0x010F88` `snapshot_for_draw` | nothing; copies the logic's positions and frames into the fields the drawing reads, between `Forbid` and `Permit` | |
| `0x01876E` `cop_set_split_line` | the horizon split of the copper list | |
| `0x0135D8` `player_lost_restart`, only when `0x024F24` is set | clears the playfield; **game logic**: game over or next life | `rect_fill`, `WaitTOF` loops |
| `0x013772` `draw_world` | sky (`rect_fill` colour 1 down to `view_y`), then the map: for each record in view the slot of bits 2–10 from `MasterList` or `AthList`, null slots skipped; then its sub-routines `0x013B1C`, `0x013ABC`, `0x01409C`, `0x0103A6` (the player's aircraft from `hellcat_shapes` or `eighth_shapes`, and the only lines), `0x010DA6` and `0x013A18` and `0x01391E` (from `japplane_shapes`), `0x013D78`, `0x013DE8`, `0x014C3E`, `0x013E6C`, `0x0140E8` | `shape_draw`, `rect_fill`, `line_draw`, `shape_draw_xor` |
| `0x010EE0` | objects from `MasterList` or `AthList` | `draw_world_shape` |
| `0x013EEE` | the soldiers, slots `0x6F` upward; **game logic**: moves and animates them, adds score, counts them down, queues ticker messages | `draw_world_shape` |
| `0x0152F8`, `0x0106BE` with `0x010702`, `0x01557C` | further object pools from `world_shapes`, `eighth_shapes`, `torpedo_shapes`, `MasterList`; `0x01557C` calls `rand_beam` | `draw_world_shape` |
| `0x010344` | two `world_shapes` entries at a fixed place, when `0x025364` is set and `0x0253BC` is 0 | `shape_blit`, unmasked |
| `0x0110C2` `draw_game_over` | `gmov` centred; **game logic**: counts `0x0255C2` down per pass and then sets `quit_flag` | `shape_draw` |
| `0x01417E` with `0x0141B4`, `0x014206`, `0x014430`, `0x014564`, `0x0145A6` | the map window of the dashboard, into the second viewport | `shape_draw`, `rect_fill` |
| `0x01EE16` `draw_dashboard` with `0x01F200`–`0x01F2B0` | instruments from `dash_shapes`, only what differs from the per-buffer cache in `view_caches`; the score digits are slices of one shape, clipped to rows 11 to 17 | `shape_draw`, `shape_blit` |
| `0x01030C` `flip_buffers` | the sky flash, then the buffer swap | |

What each pool holds is for the subsystem notes of M4 to M6.

## Read-back

The question: does any logic depend on what was drawn?

| Possible dependency | Finding |
|---|---|
| Blitter zero flag (`DMACONR` bit 13) | never tested. Every read of a custom register through A6 in the whole executable is `btst #6,2(a6)`, the busy bit, inside a wait loop. A scan of all instructions that read through A6 found nothing else in drawing code |
| Collision register `CLXDAT` | never read. The only absolute custom-chip reads are `JOY1DAT` (`0x015212`, `0x02048C`) and `VHPOSR` (`0x015D5A`, `0x0203CC`); the sound code reads `INTENAR` and `INTREQR` |
| `ReadPixel` or any other OS read | not among the graphics.library calls. Those are: `BltBitMap`, `BltClear`, `BltTemplate`, `Text`, `Move`, `Draw`, `RectFill`, `SetAPen`, `SetBPen`, `SetDrMd`, `InitBitMap`, `InitRastPort`, `WaitTOF`, `OwnBlitter`, `DisownBlitter`, plus the View calls in dead code |
| CPU reads of bitplanes | plane pointers reach code only through `draw_bitmap` (used by the blitter library alone, and only to load blitter pointer registers), the display code, the ticker and `story_screen`. Grouping every use of the buffer globals of `re/notes/display.md` by routine gives drawing, display and front-end routines only; nothing in the call tree of `logic_tick` is among them. `back_bitmap` is never read, `front_bitmap` only by `story_screen`. `draw_planes` (`0x02693C`), the library's copy of the plane pointers, is written and never read |
| `MaskBuffer` | written by `shape_draw` and `text_render`, given to the blitter or to `BltTemplate`, never read otherwise |
| Collision by shape data | none. Ground height comes from the map record type (`0x015714`). Logic looks shapes up by name only to store the pointer for the drawing and to mirror them |

So the answer is **no**, with this evidence. What remains possible in principle is a read through a pointer that static reading did not connect to a bitmap. The M2 harness can close that gap cheaply: serve chip-memory allocations made for planes (`display_alloc_chip`) from a region of their own and log any CPU read from it that does not come from `vblank_server`, the picture decoder or the OS stubs.

### What logic does take from the drawing pass

Found by intersecting the globals written in the call tree of `frame_update` with those read in the call tree of `logic_tick` (A4-relative accesses only; accesses through pointers into the object tables are not covered by this method).

| Global | Written by | Read by | Meaning |
|---|---|---|---|
| `0x026E3C` | `frame_update`, set at the end of every pass; cleared by `0x010A72` in the tick | `0x010AA6` at `0x010CD4` | a frame was drawn since the previous tick. Only then, and only when the pass counter is odd, does an object whose word at `+0x22` is 1 advance its frame byte at `+0x1E` |
| `0x0253C8` | `draw_world`, pass counter 0 to 99 | `0x010AA6` (also copied into object field `+0x1A`), `0x011460` | |
| `0x02534C`, `0x025383` | `0x013EEE` | `0x011CD8`, `0x0146DC` | the score (25 is added per soldier) and a countdown of what is left on the island; both meanings inferred from the ticker texts the routine queues |
| `0x02508A` | `0x014F5C`, reached from `draw_world` | `logic_tick`, `0x011BFC` | |
| `0x02507A`, `0x02508C`, `0x02535C`, `0x02540E` | `player_lost_restart` | many | the restart of the player |
| `0x027164`, `0x027166` | `draw_world` | `0x012132` | a distance-derived value, inferred to be a sound volume |
| `0x026E5C`, `0x026E60`, `view_shift` | `snapshot_for_draw`, `frame_update` | `0x010AA6`, `0x010820`, `0x011A46` | the drawing's copy of the player position and the scale |

The two trees share 31 routines, among them the spawn helpers `0x015460` and `0x0154E0` and the player reset `0x013684`. Inside the pass `rand_beam` is called from `0x014C3E`, `0x014D50`, `0x014EFC`, `0x014F5C`, `0x01557C` and `draw_dashboard`, and from three routines that the tick uses too: `0x011E82`, `0x015460`, `0x01CAC8`.

## Consequences

For the headless original (M2):

- Map the custom-chip area as plain memory. Every busy wait then falls through, and the register writes are harmless. Stub `OwnBlitter`, `DisownBlitter`, `BltClear`, `BltBitMap`, `BltTemplate` and `WaitTOF` as empty calls. No blitter model is needed for correct logic.
- **Call `frame_update` for every pass.** Skipping it changes the game state. `wait_vblank` and `wait_next_vblank` spin on `vblank_flag` (`0x0255BE`); the harness has to set it, or run `vblank_server`, before each pass.
- The schedule of VBlanks, passes and ticks is an input of the run, just like the input bytes and the entropy stream, because the pass consumes entropy and leaves the flag and the counter above. A fixed schedule, for example one pass every second VBlank, gives reproducible dumps; the port must run the same schedule to match them.
- With the blits intercepted at `shape_blit`, `shape_draw_xor`, `rect_fill` and `line_draw`, and the three OS calls modelled, the same harness yields reference frames.

For the port:

- The blit needs, per shape, the data listed in `re/notes/shapes.md`, and must apply clear planes, set planes and plane masks to the **existing** framebuffer value as above. "Colour 0 is transparent" is true only for shapes that get a mask.
- `rect_fill` and `shape_draw` respect the target depth: on the 4-plane dashboard bit 4 of every mask and colour is dropped.
- `line_draw` has to reproduce the blitter's line algorithm pixel for pixel; the parameters are above.
- `re/tables.toml` needs `left_mask_table` and `right_mask_table` only if the port keeps word masks; with per-pixel clipping it does not.

## Open

- **How long a pass takes in the original**, in VBlanks, under typical load. Reading cannot give it; a cycle-exact emulator can. It sets the speed of everything that runs per pass (the soldiers, the game-over delay, the kind-1 animation). This is the substance of point 2.
- The object-table fields that the pass writes through pointers were not enumerated. The headless original can: run one pass with an empty input queue and compare memory, as point 2 proposes.
- Which object each scene routine draws, and the draw order inside `draw_world`, are recorded here only as call order.
- The pixel pattern of the blitter's line mode is documented hardware behaviour, not re-derived here. A test against a cycle-exact emulator is advisable when `line_draw` is ported. The same applies to the area mode: `tests/blitter.py` models it, which is enough to check the port against the original's register programme but not to check the model itself (`re/notes/porting-m1.md`, "What that proves and what it does not").
- `0x01526E` computes its bottom clip row from fields of the record at `0x0254D8`; what they mean was not established.
- Text drawn with `graphics.Text` needs the system font's glyphs, which are not on the game disk (`re/notes/display.md`).
