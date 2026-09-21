"""Pictures of the port's mission scene, for looking at (M4 part 1, deliverable 5).

    .venv/bin/python tests/m4_renders.py          writes dist/m4-part1/*.png

The tick is still a stand-in, so the port cannot fly on its own yet: each picture comes from
the closed loop of tests/m4compare.py, in which the port runs every pass itself and is handed
only what the original's tick wrote.  A picture is the port's framebuffer with each row's
palette, rows doubled so that the proportions are roughly the display's; the dashboard is
also written alone, four times enlarged.  dist/ is not versioned, and neither are these.
"""
import os
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, 'tools'))
sys.path.insert(0, HERE)

from PIL import Image                      # noqa: E402

import conftest                            # noqa: E402
import m4compare                           # noqa: E402

OUT = os.path.join(ROOT, 'dist', 'm4-part1')
NIGHT = {0x025390: (2, 1)}


def picture(ported):
    """The port's picture after the last pass as an RGB image, 640 x 214."""
    import ctypes
    lib = ported.lib
    lib.wt_present()
    lib.wof_framebuffer.restype = ctypes.c_void_p
    lib.wof_palette_rows.restype = ctypes.c_void_p
    lib.wof_palettes.restype = ctypes.c_void_p
    width, height = lib.wof_framebuffer_width(), lib.wof_framebuffer_height()
    fb = ctypes.string_at(lib.wof_framebuffer(), width * height)
    rows = ctypes.string_at(lib.wof_palette_rows(), height * 2)
    count = lib.wof_palette_colours()
    pal = ctypes.string_at(lib.wof_palettes(), lib.wof_palette_count() * count * 4)
    image = Image.new('RGB', (width, height))
    px = image.load()
    for y in range(height):
        p = int.from_bytes(rows[2 * y:2 * y + 2], 'little')
        for x in range(width):
            at = (p * count + fb[y * width + x]) * 4
            px[x, y] = (pal[at], pal[at + 1], pal[at + 2])
    return image


def save(image, name, scale=(1, 2)):
    os.makedirs(OUT, exist_ok=True)
    w, h = image.size
    image.resize((w * scale[0], h * scale[1]), Image.NEAREST).save(os.path.join(OUT, name))
    print('wrote', os.path.join('dist', 'm4-part1', name))


def capture(ported, script, want, pokes=None, more=None):
    """Replay `script` in the closed loop and return the picture of the first pass for
    which want(memory, pass) holds, with that pass's original state."""
    work = tempfile.mkdtemp()
    dump_path = os.path.join(work, script + '.dump')
    machine = m4compare.record(script, dump_path, pokes=pokes, more=more)
    replay = m4compare.Replay(ported, machine, dump_path, mode='closed', pokes=pokes)
    found = {}

    def on_pass(r, memory, head, k):
        if 'image' not in found and want(memory, k):
            found['image'] = picture(ported)
            found['pass'] = k

    replay.run(on_pass=on_pass)
    assert 'image' in found, 'no pass of %s met the condition' % script
    print('%s: pass %d' % (script, found['pass']))
    return found['image']


def s16(v):
    return v - 0x10000 if v & 0x8000 else v


def flying(memory, k):
    """In the air at full scale: the sky above the horizon row, the sea below it."""
    on_deck = memory.u(0x025078 + 0x0C, 2)
    return on_deck == 0 and s16(memory.u(0x024F36, 2)) == 8 and k > 380


def main():
    page = conftest.PAGE.read_text(encoding='utf-8')
    ported = conftest.Ported(conftest.payload(page, 'wof-fs'))

    save(capture(ported, 'deck', lambda m, k: k == 300), 'deck-day.png')
    level = capture(ported, 'flight', flying)
    save(level, 'level-flight.png')
    save(level.crop((0, 163, 640, 200)), 'dashboard.png', scale=(4, 8))
    save(capture(ported, 'flight', flying, pokes=NIGHT), 'night.png')
    save(capture(ported, 'flight', lambda m, k: s16(m.u(0x024F36, 2)) == 1 and k > 700),
         'eighth-scale.png')
    over = []

    def game_over(memory, k):
        if memory.u(0x025362, 1):
            over.append(k)
        return len(over) > 40
    save(capture(ported, 'gameover', game_over), 'game-over.png')


if __name__ == '__main__':
    main()
