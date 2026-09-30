"""PPkc shape container parser + contact sheet renderer.

    ppkc.py SHP PALETTE OUT.png     one sheet of one shape container
    ppkc.py --sheets [DIR]          the contact sheets of ref/sheets/, into DIR (default ref/sheets)

The sheets of ref/sheets/ are versioned and held to this regeneration byte for byte by
tests/test_generated.py.  The names are drawn in Pillow's own bitmap font, not its default
FreeType one, so that a sheet does not depend on the FreeType a Pillow build carries, and a PNG
of Pillow carries no time and no text: the same Pillow writes the same bytes.
"""
import struct, sys, os
from PIL import Image, ImageDraw, ImageFont
import rpck

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SHAPES = os.path.join(ROOT, 'original', 'disk', 'Wings_of_Fury', 'shapes')
FONT = ImageFont.load_default_imagefont()

# ref/sheets/: the shape container, the sheet and its layout, all in the colours of wingspalette.
SHEETS = [
    ('8thscale.shp', '8thscale.png', 'grid'),
    ('battleship.shp', 'battleship.png', 'grid'),
    ('battleship.shp', 'battleship_packed.png', 'packed'),
    ('hellcat.shp', 'hellcat.png', 'grid'),
    ('japplane.shp', 'japplane.png', 'grid'),
    ('world.shp', 'world.png', 'grid'),
    ('world.shp', 'world_packed.png', 'packed'),
]
SHEET_PALETTE = 'wingspalette'

def parse(path):
    out, _ = rpck.load(path)
    assert out[:4] == b'PPkc', out[:4]
    n = struct.unpack('>H', out[4:6])[0]
    names = [out[6+4*i:10+4*i].decode('latin1') for i in range(n)]
    p = 6 + 4*n
    offs = [struct.unpack('>I', out[p+4*i:p+4+4*i])[0] for i in range(n)]
    base = p + 4*n
    shapes = []
    for i in range(n):
        a = base + offs[i]
        b = base + offs[i+1] if i + 1 < n else len(out)
        rec = out[a:b]
        wb, h, ox, oy, u1, u2, u3 = struct.unpack('>HHhhHHH', rec[:14])
        masks = [m for m in rec[14:20] if m]
        shapes.append(dict(name=names[i], wbytes=wb, h=h, ox=ox, oy=oy, u=(u1, u2, u3),
                           masks=masks, data=rec[20:], reclen=len(rec)))
    return shapes

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

def load_cmap(path):
    raw, _ = rpck.load(path)
    i = raw.find(b'CMAP')
    body = raw[i+8:i+8+96]
    return [(body[j] >> 4) * 17 for j in range(len(body))]

def draw_shape(im, dr, s, pal, cx, cy):
    """One shape with its name above it, its top left corner at (cx, cy)."""
    for y, row in enumerate(to_indexed(s)):
        for x, c in enumerate(row):
            if c:
                im.putpixel((cx + x, cy + y), tuple(pal[c*3:c*3+3]))
    dr.text((cx, cy - 10), s['name'], fill=(200, 200, 200), font=FONT)

def sheet(shapes, pal, out_path, scale=2, cols=None, bg=(255, 0, 255)):
    cell_w = max(s['wbytes'] * 8 for s in shapes) + 4
    cell_h = max(s['h'] for s in shapes) + 12
    cols = cols or max(1, 1400 // (cell_w * scale))
    rows = (len(shapes) + cols - 1) // cols
    im = Image.new('RGB', (cols * cell_w, rows * cell_h), (40, 40, 48))
    dr = ImageDraw.Draw(im)
    for idx, s in enumerate(shapes):
        draw_shape(im, dr, s, pal, (idx % cols) * cell_w + 2, (idx // cols) * cell_h + 10)
    im = im.resize((im.width * scale, im.height * scale), Image.NEAREST)
    im.save(out_path)
    return im.size

def packed_sheet(shapes, pal, out_path, scale=2, width=760, gap=6):
    """The same shapes packed densely: the tallest first, left to right in rows of `width`
    pixels, each row as tall as its tallest shape and its names."""
    rows, row, x = [], [], 0
    for s in sorted(shapes, key=lambda s: -s['h']):
        w = s['wbytes'] * 8
        if row and x + w + 4 > width:
            rows.append(row)
            row, x = [], 0
        row.append((x, s))
        x += w + 4 + gap
    if row:
        rows.append(row)
    heights = [max(s['h'] for _, s in r) + 12 for r in rows]
    im = Image.new('RGB', (width, sum(heights)), (40, 40, 48))
    dr = ImageDraw.Draw(im)
    y = 0
    for r, height in zip(rows, heights):
        for x0, s in r:
            draw_shape(im, dr, s, pal, x0 + 2, y + 10)
        y += height
    im = im.resize((im.width * scale, im.height * scale), Image.NEAREST)
    im.save(out_path)
    return im.size

def make_sheets(out_dir):
    """Every sheet of ref/sheets/ into out_dir."""
    os.makedirs(out_dir, exist_ok=True)
    pal = load_cmap(os.path.join(SHAPES, SHEET_PALETTE))
    for shp, name, layout in SHEETS:
        shapes = parse(os.path.join(SHAPES, shp))
        (packed_sheet if layout == 'packed' else sheet)(shapes, pal, os.path.join(out_dir, name))

if __name__ == '__main__' and sys.argv[1:2] == ['--sheets']:
    make_sheets(sys.argv[2] if len(sys.argv) > 2 else os.path.join(ROOT, 'ref', 'sheets'))
elif __name__ == '__main__':
    shp, palfile, outp = sys.argv[1:4]
    shapes = parse(shp)
    pal = load_cmap(palfile)
    ws = sorted(set(s['wbytes']*8 for s in shapes)); hs = sorted(set(s['h'] for s in shapes))
    print(os.path.basename(shp), len(shapes), 'shapes; widths', ws[:3], '..', ws[-3:], 'heights', hs[:3], '..', hs[-3:],
          'masksets', sorted(set(tuple(s['masks']) for s in shapes)))
    print(' size check:', all(s['reclen'] == 20 + s['wbytes'] * s['h'] * len(s['masks']) for s in shapes))
    print(' sheet', sheet(shapes, pal, outp))
