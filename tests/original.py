"""Running the original's routines for the M1 differential tests (SPEC 7.4, 8).

Everything here sets up the emulated machine for one routine of the original and hands
back what it produced.  The only liberties taken are the three stubs below, each of which
replaces something that is not the routine under test:

  * mem_alloc_asm (0x0158EC) returns a fixed buffer.  It is a wrapper round exec AllocMem,
    which has no meaning without the operating system; shapes_resolve is the routine being
    tested, not the allocator.
  * vport_clear_planes (0x01A74C) becomes an immediate return, and the harness zeroes the
    same bytes itself.  It is graphics BltClear, which SPEC section 8 stubs for exactly
    this reason, and both sides then start from cleared planes.
  * the call to load_file_public inside font_load (0x012798-0x0127A1) becomes "d0 is the
    font image", because the file is already in emulated memory and dos.library is not.

Nothing else is patched, and no routine under test is touched.
"""
import os
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, 'tools'))

import rpck                      # noqa: E402
from oracle import Oracle        # noqa: E402

A4 = 0x02AFFE
GAME = os.path.join(ROOT, 'original', 'disk', 'Wings_of_Fury')

# Routines
RPCK_UNPACK     = 0x01FEE0
SHAPE_FIND      = 0x020560
SHAPE_BY_INDEX  = 0x02050E
SHAPES_RESOLVE  = 0x015C5C
SHAPE_MIRROR_X  = 0x015B58
COLOUR_LERP     = 0x016FF6
FONT_LOAD       = 0x012794
TEXT_WIDTH      = 0x01591E
TEXT_RENDER     = 0x015956
IFF_TO_VPORT    = 0x01A548
CMAP_FILE_TABLE = 0x016DD6
SHAPE_DRAW      = 0x020CE2
CLIP_SET        = 0x02129C

# Patched
MEM_ALLOC_ASM     = 0x0158EC
VPORT_CLEAR       = 0x01A74C
FONT_LOAD_LOADCALL = 0x012798      # pea name / jsr load_file_public / addq.w #4,a7

# Globals (A4-relative addresses resolved to the load layout of SPEC 3.2)
DRAW_RASTPORT   = 0x026F1A
DRAW_BITMAP     = 0x02714E
MASKBUFFER      = 0x027436
MASKBUFFER_SIZE = 0x02743A

VPORT_SIZE = 0xAC


def game_file(name):
    """One file off the disk, Rpck-unwrapped the way the original's loader leaves it."""
    return rpck.load(os.path.join(GAME, name))[0]


class Original:
    """One emulated machine with the executable mapped at the listing's addresses."""

    def __init__(self, a4=A4):
        self.o = Oracle(a4=a4)

    # ------------------------------------------------------------------ patching

    def patch(self, addr, code):
        self.o.write(addr, code)

    def stub_allocator(self, size=0x4000):
        """mem_alloc_asm returns one fixed buffer; it is called once per resolve."""
        buffer = self.o.alloc(size)
        self.patch(MEM_ALLOC_ASM, struct.pack('>HI', 0x203C, buffer) + b'\x4e\x75')
        return buffer

    def stub_clear_planes(self):
        self.patch(VPORT_CLEAR, b'\x4e\x75')            # rts

    def stub_font_loader(self, image):
        """The ten bytes that load newarmyfont become move.l #image,d0 and two nops."""
        self.patch(FONT_LOAD_LOADCALL,
                   struct.pack('>HI', 0x203C, image) + b'\x4e\x71\x4e\x71')

    # -------------------------------------------------------------------- data

    def put(self, data):
        return self.o.alloc_bytes(data)

    def get(self, addr, n):
        return self.o.read(addr, n)

    # ---------------------------------------------------------------- routines

    def rpck_unpack(self, packed, out_len):
        src = self.put(packed)
        dst = self.o.alloc(out_len + 16, fill=0xEE)
        self.o.call(RPCK_UNPACK, self.o.L(src), self.o.L(len(packed)),
                    self.o.L(dst), self.o.L(out_len))
        return self.get(dst, out_len)

    def container(self, path):
        """A PPkc container in emulated memory, with the index arithmetic to go with it."""
        image = game_file(path)
        base = self.put(image)
        count = struct.unpack('>H', image[4:6])[0]
        offsets = [struct.unpack('>I', image[6 + 4 * count + 4 * i:10 + 4 * count + 4 * i])[0]
                   for i in range(count)]
        records = [base + 6 + 8 * count + off for off in offsets]
        names = [struct.unpack('>I', image[6 + 4 * i:10 + 4 * i])[0] for i in range(count)]
        return dict(base=base, count=count, records=records, names=names, image=image)

    def shape_find(self, container, name):
        """The record pointer the original returns, as an index into the container."""
        result = self.o.call(SHAPE_FIND, regs={'a0': container['base'], 'd0': name})
        if result == 0:
            return -1
        return container['records'].index(result)

    def shape_by_index(self, container, index):
        result = self.o.call(SHAPE_BY_INDEX, self.o.L(container['base']), self.o.W(index))
        return result

    def shapes_resolve(self, container, names):
        """The pointer table the original builds, as indices."""
        table = self.put(struct.pack('>%dI' % (len(names) + 1), *(list(names) + [0])))
        self.stub_allocator(4 * (len(names) + 1))
        result = self.o.call(SHAPES_RESOLVE,
                             regs={'a0': container['base'], 'a1': table, 'd0': len(names)})
        assert result, 'shapes_resolve returned no table'
        out = []
        for i in range(len(names)):
            pointer = struct.unpack('>I', self.get(result + 4 * i, 4))[0]
            out.append(-1 if pointer == 0 else container['records'].index(pointer))
        return out

    def shape_mirror_x(self, container, index):
        """Mirrors the record in place; the caller reads the record back afterwards."""
        self.o.call(SHAPE_MIRROR_X, self.o.L(container['records'][index]))

    def record(self, container, index):
        """One record's bytes, as they stand in emulated memory now."""
        start = container['records'][index]
        width, height = struct.unpack('>HH', self.get(start, 4))
        masks = [b for b in self.get(start + 14, 6) if b]
        return self.get(start, 20 + len(masks) * width * height)

    def colour_lerp(self, step, source, target):
        return self.o.call(COLOUR_LERP, self.o.W(step), self.o.W(source),
                           self.o.W(target)) & 0xFFFF

    # -------------------------------------------------------------------- font

    def font_load(self):
        image = self.put(game_file('newarmyfont'))
        self.stub_font_loader(image)
        self.o.call(FONT_LOAD)
        return image

    def text_width(self, text):
        string = self.put(text.encode('latin1'))
        return self.o.call(TEXT_WIDTH,
                           regs={'a0': string, 'd0': len(text) - 1}) & 0xFFFF

    def text_render(self, text, x, row, justify, buf_w, buf_h):
        """The 1-bit template the CPU builds, and the pixel width it reports."""
        bpr = ((buf_w + 15) // 16) * 2
        size = bpr * buf_h
        string = self.put(text.encode('latin1'))
        buffer = self.o.alloc(size + 64, fill=0)
        width = self.o.call(TEXT_RENDER, regs={
            'a0': string, 'd0': len(text), 'a1': buffer, 'd1': x, 'd2': row,
            'd3': justify, 'd4': buf_w, 'd5': buf_h,
        }) & 0xFFFF
        return width, self.get(buffer, size)

    # ------------------------------------------------------------------ pictures

    def viewport(self, bytes_per_row, rows, depth):
        """A ViewPort record of the shape the picture reader expects, with its planes."""
        record = self.o.alloc(VPORT_SIZE, fill=0)
        colours = self.o.alloc(64, fill=0)
        planes = [self.o.alloc(bytes_per_row * rows, fill=0) for _ in range(depth)]

        self.o.w16(record + 4, bytes_per_row)            # BitMap.BytesPerRow
        self.o.w16(record + 6, rows)                     # BitMap.Rows
        self.o.write(record + 9, bytes([depth]))         # BitMap.Depth
        for i, plane in enumerate(planes):
            self.o.w32(record + 0x0C + 4 * i, plane)     # BitMap.Planes[i]
        self.o.w32(record + 0x98, colours)               # colour table 1
        self.o.w16(record + 0xA0, bytes_per_row)
        self.o.w16(record + 0xA2, rows)
        self.o.w16(record + 0xA8, bytes_per_row * 8)
        self.o.w16(record + 0xAA, rows)
        return dict(record=record, colours=colours, planes=planes,
                    bytes_per_row=bytes_per_row, rows=rows, depth=depth)

    def iff_to_vport(self, path, vport):
        self.stub_clear_planes()
        image = self.put(game_file(path))
        self.o.call(IFF_TO_VPORT, self.o.L(image), self.o.L(vport['record']))

    def vport_indexed(self, vport):
        """The viewport's planes as indexed pixels."""
        width = vport['bytes_per_row'] * 8
        out = bytearray(width * vport['rows'])
        for index, plane in enumerate(vport['planes']):
            bit = 1 << index
            data = self.get(plane, vport['bytes_per_row'] * vport['rows'])
            for y in range(vport['rows']):
                row = data[y * vport['bytes_per_row']:(y + 1) * vport['bytes_per_row']]
                for b, byte in enumerate(row):
                    if not byte:
                        continue
                    for k in range(8):
                        if byte & (0x80 >> k):
                            out[y * width + b * 8 + k] |= bit
        return bytes(out)

    def vport_colours(self, vport):
        return list(struct.unpack('>32H', self.get(vport['colours'], 64)))

    def cmap_file_to_table(self, path):
        """orig 0x016DD6, the reader for the bare-CMAP palette files."""
        image = self.put(game_file(path))
        table = self.o.alloc(64, fill=0)
        self.o.call(CMAP_FILE_TABLE, self.o.L(image), self.o.L(table))
        return list(struct.unpack('>32H', self.get(table, 64)))

    # -------------------------------------------------------------------- drawing

    def set_target(self, bitmap, rastport):
        self.o.w32(DRAW_BITMAP, bitmap)
        self.o.w32(DRAW_RASTPORT, rastport)

    def clip_set(self, top, bottom, left, right):
        self.o.call(CLIP_SET, regs={'d0': top & 0xFFFF, 'd1': bottom & 0xFFFF,
                                    'd2': left & 0xFFFF, 'd3': right & 0xFFFF})

    def mask_buffer(self, size=0x410):
        buffer = self.o.alloc(size, fill=0)
        self.o.w32(MASKBUFFER, buffer)
        self.o.w32(MASKBUFFER_SIZE, size)
        return buffer

    def shape_draw(self, record, x, y, custom=0xDFF000):
        self.o.call(SHAPE_DRAW, regs={'a0': record, 'a1': 0, 'd0': x & 0xFFFF,
                                      'd1': y & 0xFFFF, 'a6': custom})
