# System font

The load and save dialog, the name entry and the file list draw text with graphics.library `Text` and never set a font, so the original shows the system default font, topaz 8 from the Kickstart ROM. The font is not on the game disk. The port reads it at build time from the owner's ROM image, `original/kick.rom`.

## The ROM

`original/kick.rom` is a plain 262,144-byte Kickstart 1.3 image (`exec 34.2`), neither encrypted nor byte-swapped. It maps at `0xFC0000`, so a ROM pointer minus `0xFC0000` is a file offset.

## Where the fonts are

The ROM holds two fonts. Their `TextFont` node headers are placeholders that the system completes at start-up, so a search by node type or name finds nothing. The font bodies are found by their contents:

| Font | File offset of `tf_YSize` | Height | Cell width | Baseline | Characters | Bytes per row (`tf_Modulo`) |
|---|---|---|---|---|---|---|
| topaz 9 | `0x084EE` | 9 | 10 | 6 | `0x20`–`0xFF` | 240 |
| topaz 8 | `0x09110` | 8 | 8 | 6 | `0x20`–`0xFF` | 192 |

Layout from `tf_YSize`, big-endian:

```text
+0   u16  tf_YSize          +12  u8   tf_LoChar
+2   u8   tf_Style          +13  u8   tf_HiChar
+3   u8   tf_Flags          +14  u32  tf_CharData   ROM pointer to the glyph bitmap
+4   u16  tf_XSize          +18  u16  tf_Modulo     bytes per bitmap row
+6   u16  tf_Baseline       +20  u32  tf_CharLoc    ROM pointer to the location table
+8   u16  tf_BoldSmear      +24  u32  tf_CharSpace  0 for a fixed-width font
+10  u16  tf_Accessors      +28  u32  tf_CharKern   0 for a fixed-width font
```

The glyph bitmap is `tf_YSize` rows of `tf_Modulo` bytes, all glyphs side by side. The location table has one entry per character from `tf_LoChar` to `tf_HiChar`, plus one more for the glyph shown for undefined characters: a u16 bit offset into each row and a u16 width in bits. Bits are most significant first.

## For the build

The build locates the body by contents rather than by a fixed offset (height 8, cell width 8, first character `0x20`, both pointers inside the ROM), so that another Kickstart version also works, and writes glyph bitmap, location table and metrics into the generated tables. When `original/kick.rom` is absent the build falls back to the game's own font and says so.
