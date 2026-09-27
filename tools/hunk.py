"""Minimal AmigaDOS hunk loader: loads segments at fixed bases, applies reloc32."""
import struct

HUNK_NAMES = {0x3E9: 'CODE', 0x3EA: 'DATA', 0x3EB: 'BSS'}

def load(path, bases=None):
    """The hunks of a hunk file, given by its path or as its bytes, relocated for `bases`."""
    raw = bytes(path) if isinstance(path, (bytes, bytearray)) else open(path, 'rb').read()
    pos = 0
    def u32():
        nonlocal pos
        v = struct.unpack('>I', raw[pos:pos+4])[0]; pos += 4
        return v
    assert u32() == 0x3F3
    while True:                       # resident library names
        n = u32()
        if n == 0: break
        pos += n * 4
    table, first, last = u32(), u32(), u32()
    sizes = [u32() for _ in range(last - first + 1)]
    segs = []
    cur = None
    while pos < len(raw):
        h = u32() & 0x3FFFFFFF
        if h in (0x3E9, 0x3EA):
            n = u32() * 4
            cur = {'type': HUNK_NAMES[h], 'data': bytearray(raw[pos:pos+n]), 'relocs': [], 'file_off': pos}
            pos += n
            segs.append(cur)
        elif h == 0x3EB:
            n = u32() * 4
            cur = {'type': 'BSS', 'data': bytearray(n), 'relocs': [], 'file_off': None}
            segs.append(cur)
        elif h == 0x3EC:              # reloc32
            while True:
                n = u32()
                if n == 0: break
                target = u32()
                offs = [u32() for _ in range(n)]
                cur['relocs'].append((target, offs))
        elif h == 0x3F0:              # symbols
            while True:
                n = u32()
                if n == 0: break
                name = raw[pos:pos + (n & 0xFFFFFF) * 4].rstrip(b'\0').decode('latin1'); pos += (n & 0xFFFFFF) * 4
                val = u32()
                cur.setdefault('symbols', []).append((name, val))
        elif h == 0x3F1:              # debug
            n = u32() * 4; pos += n
        elif h == 0x3F2:
            pass
        elif h == 0x3F5:              # overlay table: LoadSeg of a plain file stops here
            break
        else:
            raise ValueError('unknown hunk %x at %x' % (h, pos - 4))
    # alloc sizes from header (BSS tail of data hunk)
    for s, words in zip(segs, sizes):
        want = (words & 0x3FFFFFFF) * 4
        if len(s['data']) < want:
            s['data'] += bytes(want - len(s['data']))
    if bases is None:
        bases, a = [], 0x10000
        for s in segs:
            bases.append(a)
            a = (a + len(s['data']) + 0xFFF) & ~0xFFF
    for s, b in zip(segs, bases):
        s['base'] = b
    for s in segs:
        for target, offs in s['relocs']:
            for o in offs:
                v = struct.unpack('>I', s['data'][o:o+4])[0]
                struct.pack_into('>I', s['data'], o, (v + segs[target]['base']) & 0xFFFFFFFF)
    return segs

if __name__ == '__main__':
    import sys
    for i, s in enumerate(load(sys.argv[1])):
        print(i, s['type'], 'base=%06x' % s['base'], 'len=%x' % len(s['data']), 'relocs=', [(t, len(o)) for t, o in s['relocs']], 'syms=', len(s.get('symbols', [])))
