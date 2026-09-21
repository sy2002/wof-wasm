"""Drawing one shape the way the original does it, for comparison with the port.

The original's shape_draw runs under the oracle with the custom-chip space mapped as
plain memory; the blits it starts are captured at BLTSIZE and replayed by the model in
tests/blitter.py against a copy of the emulated bitplanes.  What comes back is indexed
pixels, which is what the port produces directly.

One Reference holds one container, one target bitmap and one emulated machine, because
building those costs far more than a draw does.
"""
import struct

import blitter
from original import Original

RASTPORT_MASK = 0x18


class Reference:
    def __init__(self, path, bytes_per_row, rows, depth):
        self.bytes_per_row = bytes_per_row
        self.rows = rows
        self.depth = depth
        self.width = bytes_per_row * 8
        self.plane_bytes = bytes_per_row * rows

        self.original = Original()
        blitter.map_custom(self.original.o)
        self.blits = blitter.capture(self.original.o)

        self.container = self.original.container(path)

        o = self.original.o
        self.planes = [o.alloc(self.plane_bytes, fill=0) for _ in range(depth)]
        bitmap = o.alloc(48, fill=0)
        o.w16(bitmap + 0, bytes_per_row)
        o.w16(bitmap + 2, rows)
        o.write(bitmap + 5, bytes([depth]))
        for i, plane in enumerate(self.planes):
            o.w32(bitmap + 8 + 4 * i, plane)

        rastport = o.alloc(100, fill=0)
        o.write(rastport + RASTPORT_MASK, bytes([(1 << depth) - 1]))

        self.original.set_target(bitmap, rastport)
        self.mask_buffer = self.original.mask_buffer()

        # One window over the whole heap; the container never moves and the two regions
        # that do change - MaskBuffer and the planes - are refreshed before each replay.
        top = (o.heap + 0xFFF) & ~0xFFF
        self.mem = blitter.Window(0x100000, o.read(0x100000, top - 0x100000))

    @property
    def count(self):
        return self.container['count']

    def name(self, index):
        return self.container['names'][index]

    def shape_size(self, index):
        record = self.container['records'][index]
        width, height = struct.unpack('>HH', self.original.o.read(record, 4))
        return width * 8, height

    def draw(self, index, x, y, clip, background):
        """The original's shape_draw, as indexed pixels over `background`."""
        return self.replay(clip, background,
                           lambda: self.original.shape_draw(self.container['records'][index], x, y))

    def replay(self, clip, background, call):
        """Any drawing call of the original, as indexed pixels over `background`: `call`
        runs it under the oracle, and the blits it started are replayed by the model."""
        self.blits.clear()
        self.original.clip_set(*clip)
        call()

        # MaskBuffer is what the CPU part of shape_draw produced this time round.
        off = self.mask_buffer - self.mem.base
        self.mem.data[off:off + 0x410] = self.original.o.read(self.mask_buffer, 0x410)

        planes = blitter.indexed_to_planes(background, self.bytes_per_row, self.rows,
                                           self.depth)
        for base, plane in zip(self.planes, planes):
            off = base - self.mem.base
            self.mem.data[off:off + self.plane_bytes] = plane

        for blit in self.blits:
            blitter.execute(self.mem, blit)
        return blitter.planes_to_indexed(self.mem, self.planes, self.bytes_per_row,
                                         self.rows)
