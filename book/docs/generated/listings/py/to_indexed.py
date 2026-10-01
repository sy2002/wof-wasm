# tools/ppkc.py, lines 50-63
def to_indexed(s):
    wb, h = s['wbytes'], s['h']
    w = wb * 8
    pix = [[0] * w for _ in range(h)]
    d = s['data']
    for pi, mask in enumerate(s['masks']):
        plane = d[pi*wb*h:(pi+1)*wb*h]
        if len(plane) < wb * h: break
        for y in range(h):
            row = plane[y*wb:(y+1)*wb]
            for x in range(w):
                if row[x >> 3] & (0x80 >> (x & 7)):
                    pix[y][x] |= mask
    return pix
