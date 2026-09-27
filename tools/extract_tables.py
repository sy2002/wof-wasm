#!/usr/bin/env python3
"""Extract the port's constant tables from the original files (SPEC.md section 5, step 1).

    .venv/bin/python tools/extract_tables.py [--quiet]

Reads the manifest re/tables.toml and writes src/gen/tables.c and src/gen/tables.h from
the bytes of original/disk/Wings_of_Fury/Wings and original/kick.rom.  Hand-written
sources hold code only: every name list, file name and font the core needs comes through
here.  Byte order is converted during extraction, so the generated sources are ordinary
little-endian C.

src/gen/ is ignored by version control and rebuilt on every build.
"""
import argparse
import os
import struct
import sys

try:
    import tomllib
except ModuleNotFoundError:                     # pragma: no cover - Python below 3.11
    import tomli as tomllib

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)

import hunk  # noqa: E402

EXE = os.path.join(ROOT, 'original', 'disk', 'Wings_of_Fury', 'Wings')
PLAYER = os.path.join(ROOT, 'original', 'disk', 'Wings_of_Fury', 'songplay')
ROM = os.path.join(ROOT, 'original', 'kick.rom')
MANIFEST = os.path.join(ROOT, 're', 'tables.toml')
GEN = os.path.join(ROOT, 'src', 'gen')

ROM_BASE = 0xFC0000
PREFIX = 'wof_tbl_'


class Image:
    """The executable at the fixed load addresses of SPEC 3.2, byte-addressable.  With
    `bases`, another hunk file at the addresses of its own listing: the music player
    songplay at CODE 0x0000, DATA 0x1000 (re/songplay.lst)."""

    def __init__(self, path, bases=None):
        self.segs = hunk.load(path, bases=bases)

    def bytes(self, addr, n):
        for s in self.segs:
            if s['base'] <= addr and addr + n <= s['base'] + len(s['data']):
                off = addr - s['base']
                return bytes(s['data'][off:off + n])
        raise SystemExit('address 0x%06X (%d bytes) is outside the executable' % (addr, n))

    def u32(self, addr):
        return struct.unpack('>I', self.bytes(addr, 4))[0]

    def cstr(self, addr, limit=256):
        out = bytearray()
        for i in range(limit):
            b = self.bytes(addr + i, 1)[0]
            if b == 0:
                return bytes(out)
            out.append(b)
        raise SystemExit('unterminated string at 0x%06X' % addr)


def c_string(raw):
    out = ['"']
    for b in raw:
        c = chr(b)
        if c == '"':
            out.append('\\"')
        elif c == '\\':
            out.append('\\\\')
        elif 0x20 <= b < 0x7F:
            out.append(c)
        else:
            out.append('\\%03o' % b)
    out.append('"')
    return ''.join(out)


def name_text(value):
    """A 4-character shape name, for the comment next to its long."""
    raw = struct.pack('>I', value)
    return ''.join(chr(b) if 0x20 <= b < 0x7F else '.' for b in raw)


# ------------------------------------------------------------------------ the kinds

def emit_names4(image, entry, header, source):
    name, addr, count = entry['name'], entry['addr'], entry['count']
    values = [image.u32(addr + 4 * i) for i in range(count)]

    if image.u32(addr + 4 * count) != 0:
        raise SystemExit('%s: no terminating zero after %d names at 0x%06X'
                         % (name, count, addr))
    # The lists need not be ascending - only the containers do, which is what
    # shape_find's early exit relies on (re/notes/shapes.md).
    header.append('extern const uint32_t %s%s[%d];   /* orig 0x%06X, %d names and a 0 */'
                  % (PREFIX, name, count + 1, addr, count))
    header.append('#define %s%s_COUNT %d' % (PREFIX.upper(), name.upper(), count))
    source.append("/* orig 0x%06X - %d names, zero-terminated */" % (addr, count))
    source.append('const uint32_t %s%s[%d] = {' % (PREFIX, name, count + 1))
    for i in range(0, count, 6):
        row = values[i:i + 6]
        source.append('    ' + ' '.join('0x%08Xu,' % v for v in row)
                      + '   /* ' + ' '.join(name_text(v) for v in row) + ' */')
    source.append('    0u,')
    source.append('};')
    source.append('')


def emit_cstr(image, entry, header, source):
    name, addr = entry['name'], entry['addr']
    raw = image.cstr(addr)

    header.append('extern const char %s%s[%d];   /* orig 0x%06X */'
                  % (PREFIX, name, len(raw) + 1, addr))
    source.append('const char %s%s[%d] = %s;' % (PREFIX, name, len(raw) + 1, c_string(raw)))
    source.append('')


def emit_string_array(name, addr, raws, addrs, header, source):
    header.append('extern const char *const %s%s[%d];   /* orig 0x%06X */'
                  % (PREFIX, name, len(raws), addr))
    header.append('#define %s%s_COUNT %d' % (PREFIX.upper(), name.upper(), len(raws)))
    for i, raw in enumerate(raws):
        source.append('static const char %s%s_%d[%d] = %s;   /* orig 0x%06X */'
                      % (PREFIX, name, i, len(raw) + 1, c_string(raw), addrs[i]))
    source.append('const char *const %s%s[%d] = {' % (PREFIX, name, len(raws)))
    for i in range(len(raws)):
        source.append('    %s%s_%d,' % (PREFIX, name, i))
    source.append('};')
    source.append('')


def emit_cstrs(image, entry, header, source):
    name, addr, count = entry['name'], entry['addr'], entry['count']
    raws, addrs, at = [], [], addr

    for _ in range(count):
        raw = image.cstr(at)
        raws.append(raw)
        addrs.append(at)
        at += len(raw) + 1
    emit_string_array(name, addr, raws, addrs, header, source)


def emit_strptrs(image, entry, header, source):
    name, addr, count = entry['name'], entry['addr'], entry['count']
    addrs = [image.u32(addr + 4 * i) for i in range(count)]
    raws = [image.cstr(a) for a in addrs]

    emit_string_array(name, addr, raws, addrs, header, source)


def emit_words(image, entry, header, source):
    """`count` big-endian 16-bit values, as they stand in the executable.  With `stride` they
    are that many bytes apart, which is how the immediate operands of a run of equal
    instructions are read: the sound engine's periods, volumes and repeat counts are words
    inside its `move.w #imm,d16(a4)` (re/notes/sound.md).  With `addrs` instead of `addr`
    and `count`, one word from each of the addresses listed."""
    name = entry['name']
    if 'addrs' in entry:                   # words scattered over the code, one per address
        addrs = entry['addrs']
        addr, count = addrs[0], len(addrs)
    else:
        addr, count = entry['addr'], entry['count']
        addrs = [addr + entry.get('stride', 2) * i for i in range(count)]
    values = [struct.unpack('>H', image.bytes(a, 2))[0] for a in addrs]

    header.append('extern const uint16_t %s%s[%d];   /* orig 0x%06X */'
                  % (PREFIX, name, count, addr))
    header.append('#define %s%s_COUNT %d' % (PREFIX.upper(), name.upper(), count))
    source.append('const uint16_t %s%s[%d] = {' % (PREFIX, name, count))
    for i in range(0, count, 8):
        source.append('    ' + ' '.join('0x%04X,' % v for v in values[i:i + 8]))
    source.append('};')
    source.append('')


def emit_longs(image, entry, header, source):
    """`count` big-endian 32-bit values.  The tables of floating-point constants the game
    computes with are of this kind (re/notes/ffp.md)."""
    name, addr, count = entry['name'], entry['addr'], entry['count']
    values = [struct.unpack('>L', image.bytes(addr + 4 * i, 4))[0] for i in range(count)]

    header.append('extern const uint32_t %s%s[%d];   /* orig 0x%06X */'
                  % (PREFIX, name, count, addr))
    header.append('#define %s%s_COUNT %d' % (PREFIX.upper(), name.upper(), count))
    source.append('const uint32_t %s%s[%d] = {' % (PREFIX, name, count))
    for i in range(0, count, 6):
        source.append('    ' + ' '.join('0x%08Xu,' % v for v in values[i:i + 6]))
    source.append('};')
    source.append('')


def emit_blob(image, entry, header, source):
    """`count` raw bytes.  This is how a block of text reaches the port: the long printable
    blocks of the executable are summarised in the listing on purpose, so they are read from
    the binary by address and never written down anywhere (CLAUDE.md)."""
    name = entry['name']
    if 'addrs' in entry:                   # bytes scattered over the code, one per address
        addr, count = entry['addrs'][0], len(entry['addrs'])
        raw = b''.join(image.bytes(a, 1) for a in entry['addrs'])
    else:
        addr, count = entry['addr'], entry['count']
        raw = image.bytes(addr, count)

    header.append('extern const uint8_t %s%s[%d];   /* orig 0x%06X */'
                  % (PREFIX, name, count, addr))
    header.append('#define %s%s_COUNT %d' % (PREFIX.upper(), name.upper(), count))
    source.append('const uint8_t %s%s[%d] = {' % (PREFIX, name, count))
    for i in range(0, count, 16):
        source.append('    ' + ' '.join('0x%02X,' % b for b in raw[i:i + 16]))
    source.append('};')
    source.append('')


# ------------------------------------------------------------- the key conversion table

# The qualifier bits the table covers.  The shell sends the two Shift keys and Caps Lock and
# ignores a key pressed with Control, Alt or Command; the port's own key layer adds Control
# in front of the game's command keys (SPEC 6.2).  Nothing else ever reaches key_to_char, so
# four bits is the whole space the game can ask for.
KEYMAP_CODES = 128                  # input_handler drops a code with bit 7 set: that is key-up
KEYMAP_QUALIFIERS = 16              # lshift 1, rshift 2, capslock 4, ctrl 8

# Without the ROM the table holds only what the positions of the raw codes give
# (re/notes/keys.md): letters, digits and the space bar.  Everything else - Return, Escape,
# the editing keys - is tested by its raw code before key_to_char is reached, so the line
# editor and the menus still work; what is lost is typing anything but a letter or a digit.
POSITIONAL = {}
for _row, _text in ((0x01, '1234567890'), (0x10, 'qwertyuiop'),
                    (0x20, 'asdfghjkl'), (0x31, 'zxcvbnm')):
    for _i, _c in enumerate(_text):
        POSITIONAL[_row + _i] = _c
POSITIONAL[0x40] = ' '


def keymap_positional():
    """The fallback table: raw code and qualifier -> character, from the positions alone."""
    table = bytearray(KEYMAP_CODES * KEYMAP_QUALIFIERS)
    for code, letter in POSITIONAL.items():
        for qualifier in range(KEYMAP_QUALIFIERS):
            shifted = bool(qualifier & 0x03) or (bool(qualifier & 0x04) and letter.isalpha())
            character = letter.upper() if shifted and letter.isalpha() else letter
            value = ord(character)
            if qualifier & 0x08:                # RawKeyConvert ands a Control result with 0x9F
                value &= 0x9F
            table[code * KEYMAP_QUALIFIERS + qualifier] = value
    return bytes(table)


def keymap_from_rom(rom, log):
    """The real table: console.device's RawKeyConvert with the ROM's own default keymap, both
    located by their contents, run over every raw code and every qualifier combination
    (SPEC 5 step 1, re/notes/keys.md).  The game asks for one character and takes the key only
    when exactly one comes back, so that is what a table entry holds; a key that yields two or
    three - a cursor or function key - holds 0, which is what key_to_char returns for it."""
    from unicorn import Uc, UC_ARCH_M68K, UC_MODE_BIG_ENDIAN
    from unicorn.m68k_const import (UC_CPU_M68K_M68000, UC_M68K_REG_A0, UC_M68K_REG_A1,
                                    UC_M68K_REG_A2, UC_M68K_REG_A6, UC_M68K_REG_A7,
                                    UC_M68K_REG_D0, UC_M68K_REG_D1, UC_M68K_REG_PC,
                                    UC_M68K_REG_SR)
    sys.path.insert(0, HERE)
    import headless                                            # the same two lookups a run uses

    base = 0x1000000 - len(rom)
    convert, keymap = headless.find_rom_console(rom, base)
    if convert is None or keymap is None:
        log('tables    keymap: console.device or its keymap is not in original/kick.rom; '
            'the table falls back to the positions of the raw codes')
        return None, None, None

    ram, event, buffer, stack, trap = 0x100000, 0x010000, 0x010100, 0x0F0000, 0x0FFF00
    uc = Uc(UC_ARCH_M68K, UC_MODE_BIG_ENDIAN)
    uc.ctl_set_cpu_model(UC_CPU_M68K_M68000)
    uc.mem_map(0, ram)
    uc.mem_map(base, len(rom))
    uc.mem_write(base, rom)

    table = bytearray(KEYMAP_CODES * KEYMAP_QUALIFIERS)
    for code in range(KEYMAP_CODES):
        for qualifier in range(KEYMAP_QUALIFIERS):
            uc.mem_write(event, bytes(22))
            uc.mem_write(event + 4, b'\x01')                    # ie_Class: IECLASS_RAWKEY
            uc.mem_write(event + 6, struct.pack('>HH', code, qualifier))
            uc.mem_write(buffer, bytes(8))
            uc.mem_write(stack, struct.pack('>L', trap))
            uc.reg_write(UC_M68K_REG_SR, 0x2000)
            uc.reg_write(UC_M68K_REG_A7, stack)
            uc.reg_write(UC_M68K_REG_A0, event)
            uc.reg_write(UC_M68K_REG_A1, buffer)
            uc.reg_write(UC_M68K_REG_A2, keymap)
            uc.reg_write(UC_M68K_REG_A6, 0)
            uc.reg_write(UC_M68K_REG_D1, 1)                     # the buffer is one byte long
            uc.emu_start(convert, trap, count=200000)
            if uc.reg_read(UC_M68K_REG_PC) != trap:
                raise SystemExit('RawKeyConvert did not return for code 0x%02X' % code)
            if uc.reg_read(UC_M68K_REG_D0) & 0xFFFF == 1:
                table[code * KEYMAP_QUALIFIERS + qualifier] = uc.mem_read(buffer, 1)[0]
    return bytes(table), convert, keymap


def emit_keymap(entry, header, source, log):
    name = entry['name']
    table = None

    if os.path.exists(ROM):
        with open(ROM, 'rb') as handle:
            rom = handle.read()
        table, convert, keymap = keymap_from_rom(rom, log)
        if table is not None:
            log('tables    keymap from RawKeyConvert 0x%06X with the keymap at 0x%06X: '
                '%d codes x %d qualifiers, %d entries carry a character'
                % (convert, keymap, KEYMAP_CODES, KEYMAP_QUALIFIERS, sum(1 for b in table if b)))
    else:
        log('tables    keymap: original/kick.rom is absent; the table falls back to the '
            'positions of the raw codes (re/notes/keys.md)')

    present = 1 if table is not None else 0
    if table is None:
        table = keymap_positional()

    header.append('/* key_to_char: raw code x qualifier -> character, from the ROM\'s own')
    header.append(' * RawKeyConvert and default keymap, or from the raw codes\' positions. */')
    header.append('#define %sKEYMAP_CODES      %d' % (PREFIX.upper(), KEYMAP_CODES))
    header.append('#define %sKEYMAP_QUALIFIERS %d' % (PREFIX.upper(), KEYMAP_QUALIFIERS))
    header.append('extern const int     %s%s_present;' % (PREFIX, name))
    header.append('extern const uint8_t %s%s[%d];' % (PREFIX, name, len(table)))
    source.append('const int     %s%s_present = %d;' % (PREFIX, name, present))
    source.append('const uint8_t %s%s[%d] = {' % (PREFIX, name, len(table)))
    for i in range(0, len(table), KEYMAP_QUALIFIERS):
        source.append('    ' + ' '.join('0x%02X,' % b for b in table[i:i + KEYMAP_QUALIFIERS])
                      + '   /* 0x%02X */' % (i // KEYMAP_QUALIFIERS))
    source.append('};')
    source.append('')


# ---------------------------------------------------------------------- the system font

def find_topaz8(rom):
    """The ROM's font headers are placeholders the system completes at start-up, so a
    search by node type or name finds nothing.  The body is found by its contents: height
    8, cell width 8, first character 0x20, and both pointers inside the ROM
    (re/notes/system-font.md).  Looking for the contents rather than a fixed offset is
    what makes another Kickstart version work."""
    for off in range(0, len(rom) - 32, 2):
        ysize, style, flags, xsize, baseline = struct.unpack('>HBBHH', rom[off:off + 8])
        if ysize != 8 or xsize != 8:
            continue
        lo, hi = rom[off + 12], rom[off + 13]
        if lo != 0x20 or hi < 0x7E:
            continue
        chardata, modulo, charloc = struct.unpack('>IHI', rom[off + 14:off + 24])
        charspace, charkern = struct.unpack('>II', rom[off + 24:off + 32])
        if charspace or charkern:
            continue                            # topaz is fixed width
        if not (ROM_BASE <= chardata < ROM_BASE + len(rom)):
            continue
        if not (ROM_BASE <= charloc < ROM_BASE + len(rom)):
            continue
        if modulo == 0 or modulo * ysize > len(rom):
            continue
        return dict(ysize=ysize, xsize=xsize, baseline=baseline, lo=lo, hi=hi,
                    modulo=modulo, data=chardata - ROM_BASE, loc=charloc - ROM_BASE,
                    style=style, flags=flags, off=off)
    return None


def emit_sysfont(entry, header, source, log):
    name = entry['name']
    font = None

    if os.path.exists(ROM):
        with open(ROM, 'rb') as handle:
            rom = handle.read()
        font = find_topaz8(rom)
        if font is None:
            log('tables    %s: no topaz 8 in original/kick.rom; the dialogs fall back to '
                'the game font' % name)
    else:
        log('tables    %s: original/kick.rom is absent; the dialogs fall back to the game '
            'font (re/notes/system-font.md)' % name)

    header.append('/* topaz 8 from the owner\'s Kickstart ROM, or absent (see the note). */')
    header.append('extern const int      %s%s_present;' % (PREFIX, name))
    header.append('extern const uint16_t %s%s_ysize;' % (PREFIX, name))
    header.append('extern const uint16_t %s%s_xsize;' % (PREFIX, name))
    header.append('extern const uint16_t %s%s_baseline;' % (PREFIX, name))
    header.append('extern const uint16_t %s%s_modulo;' % (PREFIX, name))
    header.append('extern const uint8_t  %s%s_lo;' % (PREFIX, name))
    header.append('extern const uint8_t  %s%s_hi;' % (PREFIX, name))
    header.append('extern const uint8_t  %s%s_data[];' % (PREFIX, name))
    header.append('extern const uint16_t %s%s_loc[];   /* 2 words per glyph: bit offset, width */')
    header[-1] = header[-1] % (PREFIX, name)

    if font is None:
        source.append('const int      %s%s_present  = 0;' % (PREFIX, name))
        for field in ('ysize', 'xsize', 'baseline', 'modulo'):
            source.append('const uint16_t %s%s_%s = 0;' % (PREFIX, name, field))
        source.append('const uint8_t  %s%s_lo = 0;' % (PREFIX, name))
        source.append('const uint8_t  %s%s_hi = 0;' % (PREFIX, name))
        source.append('const uint8_t  %s%s_data[1] = { 0 };' % (PREFIX, name))
        source.append('const uint16_t %s%s_loc[2] = { 0, 0 };' % (PREFIX, name))
        source.append('')
        return

    glyphs = font['hi'] - font['lo'] + 2        # one more for the undefined character
    bitmap = rom[font['data']:font['data'] + font['modulo'] * font['ysize']]
    loc = rom[font['loc']:font['loc'] + 4 * glyphs]
    words = struct.unpack('>%dH' % (2 * glyphs), loc)

    log('tables    topaz 8 at ROM offset 0x%05X: %d x %d, %d glyphs, modulo %d'
        % (font['off'], font['xsize'], font['ysize'], glyphs, font['modulo']))

    source.append('/* topaz 8, located by contents at ROM offset 0x%05X */' % font['off'])
    source.append('const int      %s%s_present  = 1;' % (PREFIX, name))
    source.append('const uint16_t %s%s_ysize    = %d;' % (PREFIX, name, font['ysize']))
    source.append('const uint16_t %s%s_xsize    = %d;' % (PREFIX, name, font['xsize']))
    source.append('const uint16_t %s%s_baseline = %d;' % (PREFIX, name, font['baseline']))
    source.append('const uint16_t %s%s_modulo   = %d;' % (PREFIX, name, font['modulo']))
    source.append('const uint8_t  %s%s_lo       = 0x%02X;' % (PREFIX, name, font['lo']))
    source.append('const uint8_t  %s%s_hi       = 0x%02X;' % (PREFIX, name, font['hi']))
    source.append('const uint8_t  %s%s_data[%d] = {' % (PREFIX, name, len(bitmap)))
    for i in range(0, len(bitmap), 16):
        source.append('    ' + ' '.join('0x%02X,' % b for b in bitmap[i:i + 16]))
    source.append('};')
    source.append('const uint16_t %s%s_loc[%d] = {' % (PREFIX, name, len(words)))
    for i in range(0, len(words), 8):
        source.append('    ' + ' '.join('%d,' % w for w in words[i:i + 8]))
    source.append('};')
    source.append('')


KINDS = {
    'names4': emit_names4,
    'cstr': emit_cstr,
    'cstrs': emit_cstrs,
    'strptrs': emit_strptrs,
    'words': emit_words,
    'longs': emit_longs,
    'blob': emit_blob,
}


def main():
    parser = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    parser.add_argument('--quiet', action='store_true')
    args = parser.parse_args()
    log = (lambda message: None) if args.quiet else print

    with open(MANIFEST, 'rb') as handle:
        manifest = tomllib.load(handle)

    image = Image(EXE)
    others = {'songplay': Image(PLAYER, bases=[0x0000, 0x1000, 0x2000])}
    header = ['/* Generated by tools/extract_tables.py from re/tables.toml.  Do not edit. */',
              '#ifndef WOF_GEN_TABLES_H',
              '#define WOF_GEN_TABLES_H',
              '',
              '#include <stdint.h>',
              '']
    source = ['/* Generated by tools/extract_tables.py from re/tables.toml.  Do not edit.',
              ' *',
              ' * Every value here comes out of original/disk/Wings_of_Fury/Wings or',
              ' * original/kick.rom at build time (SPEC.md section 5, step 1). */',
              '#include "tables.h"',
              '']

    for entry in manifest.get('table', []):
        kind = entry['kind']
        if kind == 'sysfont':
            emit_sysfont(entry, header, source, log)
        elif kind == 'keymap':
            emit_keymap(entry, header, source, log)
        elif kind in KINDS:
            KINDS[kind](others[entry['file']] if 'file' in entry else image, entry, header, source)
        else:
            raise SystemExit('unknown kind %r for table %r' % (kind, entry['name']))

    header.append('#endif /* WOF_GEN_TABLES_H */')

    os.makedirs(GEN, exist_ok=True)
    with open(os.path.join(GEN, 'tables.h'), 'w', encoding='ascii') as handle:
        handle.write('\n'.join(header) + '\n')
    with open(os.path.join(GEN, 'tables.c'), 'w', encoding='ascii') as handle:
        handle.write('\n'.join(source) + '\n')

    log('tables    %d entries -> src/gen/tables.c, src/gen/tables.h'
        % len(manifest.get('table', [])))


if __name__ == '__main__':
    main()
