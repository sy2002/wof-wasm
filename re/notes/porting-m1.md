# M1: what was ported, how the pixels were pinned down, and what the tests prove

Milestone M1 of `SPEC.md` section 9. Addresses use the standard load layout. Everything
stated here is either read from the disassembly or measured by the tests in
`tests/test_oracle_m1.py`; where it is measured, the test is named.

## Summary

The loaders, the decoders, the fonts and the shape blit are ported and compared with the
original routine by routine. The port keeps **indexed pixels** rather than bitplanes
(`SPEC.md` section 6.4), which changes the representation of three things and nothing
else:

- A **shape** is converted once, at load, to `8 * width` pixels by `height` plus the
  header fields the blit still needs. The blit's transparency mask, which the original
  builds as the OR of the stored planes, is then exactly "the pixel is not 0", because no
  container on the disk has overlapping plane masks (checked over all 1,049 shapes).
- A **pointer table** becomes an array of shape indices with `-1` where the original
  stores a null pointer.
- A **viewport** becomes one indexed surface plus its 32-word colour table. The picture
  decoder still needs the planar stride, because it writes rows back to back at the
  picture's own stride and not the viewport's, so it decodes into planes and composes
  afterwards; a picture of the wrong width therefore shears in the port exactly as it
  does on the machine.

## The routines

| Original | Port | Status |
|---|---|---|
| `rpck_unpack` `0x01FEE0` | `src/load.c` | verified |
| `load_file` `0x01FF16` with `load_file_public` and `load_file_chip` | `src/load.c`, over the dos glue in `src/fs.c` | verified |
| `shapes_load` `0x015BC6`, `shapes_resolve` `0x015C5C` | `src/shapes.c` | verified |
| `shape_find` `0x020560`, `shape_by_index` `0x02050E` | `src/shapes.c` | verified |
| `shape_mirror_x` `0x015B58` and the `+8` marker rule of `0x01ABDE` | `src/shapes.c` | verified |
| `load_permanent_shapes` `0x0129DC`, `load_dash_assets` `0x01653C`, `load_ship_shapes` `0x013252` | `src/assets.c` | ported |
| `byterun1_row` `0x0203E8`, `iff_body_to_vport` `0x01A362`, `iff_parse_ilbm` `0x01A452`, `iff_to_vport` `0x01A548`, `iff_cmap_to_table` `0x01A1F6` | `src/iff.c` | verified |
| `cmap_file_to_table` `0x016DD6` | `src/iff.c` | verified |
| `colour_lerp` `0x016FF6` | `src/iff.c` | verified |
| `font_load` `0x012794`, `text_width` `0x01591E`, `text_render` `0x015956` | `src/font.c` | verified |
| `draw_set_target` `0x02124A`, `clip_set` `0x02129C`, `clip_set_full` `0x021280` | `src/draw.c` | verified, ported |
| `blit_clip_setup` `0x0209BC`, `shape_blit` `0x020B0C`, `shape_draw` `0x020CE2` | `src/draw.c` | verified |
| `vport_clear_planes` `0x01A74C` | `src/video.c` | ported |
| the allocators `0x0158EC`, `0x020848`, `0x02085E`, `0x020874`, `0x02090A`, `0x0124E0` | the arena in `src/mem.c` | replace |

Not ported by M1, although they are in the same call trees: `text_draw` `0x015910` and
`text_draw_justified` `0x015A8C` put the template on screen with `BltTemplate` using the
RastPort's pens and draw mode, which the front end sets per screen; the port draws the
template in JAM1 for now and the real pens arrive with M3. `rect_fill`, `line_draw` and
`shape_draw_xor` are not part of M1. `build_master_lists` `0x01535A` is pure and
understood but belongs to the map, so it waits for M4.

## The blit is per-pixel, and why

This is the one place where the port cannot follow the original instruction by
instruction: the original programmes the blitter, and the port has to produce the same
pixels. The claim `re/notes/drawing.md` makes, that clipping is exact to the pixel
although the clip edges are multiples of 16, is now established in full and is what
`src/draw.c` implements:

> For every pixel of the shape's box that lies inside
> `[clip_left, clip_right)` by `[clip_top, clip_bottom)`, and only for those, the
> destination changes; nothing outside the box is touched, however the blit is shifted.

The argument, reading `blit_clip_setup` (`0x0209BC`) and `shape_blit` (`0x020B0C`):

- The destination span starts at `x` rounded down to a multiple of 16 and is one word
  wider than the shape when `x` is not word-aligned, so it can overhang the shape's box
  by `shift` pixels on the left and `16 - shift` on the right.
- Minterm `0xCA` is `D = A*B + not A*C`, so wherever the A channel is 0 the destination
  keeps its value. Both edges of A are masked: `BLTAFWM` from `left_mask_table`
  (`0x026968`, entry `n` is `0xFFFF >> n`) and `BLTALWM` from `right_mask_table`
  (`0x02698A`, entry `n` is `0xFFFF << (16 - n)`), indexed with `(clip_left - x) and 15`
  and `16 - shift`.
- Work the shifted A stream out word by word: the first destination word receives
  `A[0] >> shift` with 0 shifted in, and the last receives `A[last-1] << (16 - shift)`
  with `BLTALWM` of 0. Both overhangs come out as A equal to 0. On the left the mask
  also removes the `(clip_left - x) and 15` source columns that the whole-word skip,
  `(clip_left - x) >> 4` words, did not remove; the two together skip exactly
  `clip_left - x` columns.
- The shifter carries across rows, and the last A word of every row is masked to 0 (or,
  when the right edge is clipped, to `0xFFFF << shift`, whose low bits are 0), so each
  row starts with a clean shifter.
- When there is no mask, A is the constant `0xFFFF` from `BLTADAT`, and the same two
  masks apply to it. That is what makes the unshifted case safe enough for the original
  to run it with the C channel constant as well (`BLTCON0` `0x01CA`), and what keeps the
  shifted case from smearing the next row's first word, which the B channel really does
  read, into the right-hand overhang.

Per written pixel, with `M` the target's depth mask, `clear` and `set` the bytes at `+12`
and `+13`, `U` the union of the stored planes' destination masks and `p` the converted
pixel, the three blitter phases in order come to:

```text
v = (((v and not (clear and M)) or (set and M)) and not (U and M)) or (p and M)
```

Planes named by none of `clear`, `set` and `U` keep the background's bits. Whether a
pixel is written at all is the mask rule of `shape_draw`: a shape gets a mask when its
plane is at most `MaskBuffer_size` (1,040) bytes **and** it stores at least one plane.
Eleven shapes exceed that and are opaque; one, `bchm` in `8thscale.shp`, stores no plane
at all and paints its `clear` and `set` bytes, `0x0E` and `0x11`, over a 16 by 1 box.

## How the tests establish it

`tests/test_oracle_m1.py`, 70 tests, about 30 seconds.

Every pure routine runs twice on the same input, once as 68000 code under the oracle and
once as the C the port compiled, and the results are compared byte for byte. What the
original's routines need in order to run without an operating system is in
`tests/original.py`, which also documents the only three stubs: the allocator wrapper
`mem_alloc_asm`, `vport_clear_planes` (which is `BltClear`, stubbed the way `SPEC.md`
section 8 stubs it, with the harness zeroing the same bytes), and the call to
`load_file_public` inside `font_load`, because the font is already in emulated memory.

Coverage: all ten packed files and 40 random streams for the unpacker; all 55 files of
the disk through `load_file`; every name of every list and every name every container
carries, looked up in each of the twelve containers, for `shape_find`; every list against
its container for `shapes_resolve`; all 1,049 shapes for the conversion to indexed
pixels; all 216 hellcat and Torpedo shapes for the mirror, both ways, checked to be an
involution; all sixteen steps against black and white in both directions plus 20,000
random triples for `colour_lerp` (`WOF_SLOW_ORACLE=1` runs the whole 16 by 4,096 by 4,096
cross product, which takes about an hour and a half); ten strings including the whole
printable range for the text; all twelve ILBM files on the disk, pixels and colour table,
for the picture reader; all six palette files for `cmap_file_to_table`.

The blit is compared through its **register programme**. The original's `shape_draw` runs
with the custom-chip space mapped as plain memory, every write to `BLTSIZE` (`0xDFF058`)
is captured together with the registers as they stood at that moment, and
`tests/blitter.py` replays the programme against a copy of the emulated bitplanes. Every
shape of every container is drawn at six positions - word-aligned and shifted, inside the
target and hanging off each of the four edges - against two clip rectangles and over an
empty and a noisy background on the 5-plane playfield, and four containers are drawn
again on the 4-plane dashboard, where bit 4 of every mask is dropped.

**What that proves and what it does not.** The clipping arithmetic, the pointers, the
modulos, the sizes, the word masks and the order of the three phases in the comparison
are the original's own, computed by its own code; a mistake in the port's clipping or in
its plane arithmetic shows up at once. The blitter's area mode itself - the minterm, the
barrel shifters, the first and last word masks applying to `BLTADAT` - is documented
hardware behaviour that this project has modelled rather than re-derived, so the
comparison cannot catch a mistake in that model. One test leaves the port out, though it replays through the model too:
`test_the_blit_writes_exactly_the_shape_box` draws over an all-zero and an all-ones
background and checks that the set of pixels that differ lies inside the shape's box
intersected with the clip rectangle, which is a statement about the register programme,
not about the port. A run against a cycle-exact emulator would close the rest, and is
worth doing when `line_draw` is ported, which needs the blitter's line mode anyway.

## Decisions the port made

- **The arena has two ends.** Everything that outlives a load grows up from the bottom;
  the buffer a file is read and unpacked into comes from the top and is given back with a
  mark. That is what the original's `Free` of a just-loaded file amounts to here, and it
  is why `load_file` can hand out a pointer that the caller uses and drops.
- **The file system ignores case**, because AmigaDOS does: the game asks for
  `shapes/Torpedo.shp` and `shapes/rank.iff` and the disk has `torpedo.shp` and
  `Rank.iff`. A lock and a file handle are both a directory index, so neither allocates.
- **A screen is a stack of bands.** Each band names a viewport, where it starts on the
  640 by 214 output and which palette its rows go through, which is how the per-row
  palette interface of `SPEC.md` section 6.4 is fed. Rows no band covers go through the
  blank palette at index 0, which is what the copper's `BPLCON0 = 0x0200` gives on the
  machine for the line above each lower viewport. The sky-to-ocean split, the ticker ramp
  and the fades are further bands and further palettes, and need no new mechanism.
- **Low-resolution viewports are doubled at presentation**, not in the surface, so the
  blit works in the original's own pixel coordinates.

## Findings

- **`shapes/broderbund` is not the publisher's logo on this disk.** It decodes to a
  "MicroTech presents" screen, and `shapes/wingstitle` carries "CopyRight 1992, MicroTech
  Software Inc" along its bottom edge. The crack replaced the artwork as well as the
  protection check. `SPEC.md` section 3.1 and section 9 call the first picture the
  publisher logo; what the port shows is what the file holds.
- **Two files decode to one byte more than they declare** (`cruiseship.shp` and
  `japplane.shp`, already in `SPEC.md` section 3.5). The original writes that byte past
  the end of a buffer it allocated at the declared size; the port stops at the declared
  size. Nothing reads it either way.
- **`selectrank.shp` has no name list** and is addressed by index, as
  `re/notes/shapes.md` says; the port loads it the same way and the browser shows its
  eight records.
- The nine name lists are **not** in ascending order, although the containers are. Only
  the containers have to be, which is what `shape_find`'s early exit relies on.

## Open

- The exact pens and draw mode of the text on screen. `text_render` is verified, but what
  `BltTemplate` and `graphics.Text` do with it depends on the RastPort the front end sets
  up, which is M3.
- `load_ship_shapes` chooses its containers from flags the map loader sets, and
  `load_dash_assets` from `night_flag`. M1 has no map and no mission, so it loads all of
  them; the choice arrives with M4.
- The system font is drawn in JAM1 with one pen. `graphics.Text` in JAM2 also paints the
  background pen, and which mode each dialog uses is due before M3.
- Whether any state ever draws the eleven frame names that are absent from `hellcat.shp`
  or `Torpedo.shp` (`re/notes/shapes.md`) is still open; the port's `shape_find` returns
  no shape and the draw does nothing, which is the same visible result as the original's
  null-pointer read.
