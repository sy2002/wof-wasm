"""Pictures of the port's mission scene, for looking at (M4, deliverable 5 of both parts).

    .venv/bin/python tests/m4_renders.py          writes dist/m4-part1/ and dist/m4-part2/

Each picture comes from the closed loop of tests/m4compare.py, in which the port runs from
the program's start on its own with the script's keys and controller state, and nothing is
handed over; the original's recorded run only says which pass to take.  A picture is the
port's framebuffer with each row's palette, rows doubled so that the proportions are
roughly the display's; the dashboard is also written alone, four times enlarged.  dist/ is
not versioned, and neither are these.
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
OUT2 = os.path.join(ROOT, 'dist', 'm4-part2')
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


def save(image, name, scale=(1, 2), out=OUT):
    os.makedirs(out, exist_ok=True)
    w, h = image.size
    image.resize((w * scale[0], h * scale[1]), Image.NEAREST).save(os.path.join(out, name))
    print('wrote', os.path.join(os.path.relpath(out, ROOT), name))


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


PLAYER = 0x025078


def player(memory, offset):
    return s16(memory.u(PLAYER + offset, 2))


def part2(ported):
    """The flights of part 2: flying left with hellcat.shp mirrored, a dive, the eighth-scale
    view at the ceiling and in a turn, the splash of a crash into the sea, the next aircraft
    on the lift, and a landing held by a cable."""
    def put(image, name):
        save(image, name, out=OUT2)

    def level_left(m, k):
        return (player(m, 0x0C) == 0 and player(m, 0x14) == -1 and m.u(0x02540E, 2) == 0 and
                s16(m.u(0x024F36, 2)) == 8 and player(m, 0x00) > 60)
    put(capture(ported, 'landing', level_left), 'flying-left.png')

    def dive(m, k):
        return (player(m, 0x0C) == 0 and player(m, 0x18) <= -4 and player(m, 0x14) == 1 and
                m.u(0x02540E, 2) == 0 and s16(m.u(0x024F36, 2)) == 8)
    put(capture(ported, 'turns', dive), 'dive.png')

    def ceiling(m, k):
        return s16(m.u(0x024F36, 2)) == 1 and player(m, 0x00) >= 1080
    put(capture(ported, 'turns', ceiling), 'ceiling-eighth-scale.png')

    def eighth_turn(m, k):
        return s16(m.u(0x024F36, 2)) == 1 and 8 <= m.u(0x02540E, 2) <= 18
    put(capture(ported, 'turns', eighth_turn), 'eighth-scale-turn.png')

    seen = []

    def splash(m, k):
        if player(m, 0x0C) == 6:
            seen.append(k)
        return len(seen) == 3
    put(capture(ported, 'lost', splash), 'crash-splash.png')

    def restart(m, k):
        return m.u(0x02535C, 1) == 2 and player(m, 0x0C) == 1 and player(m, 0x00) == 0
    put(capture(ported, 'lost', restart), 'restart.png')

    held = []

    def cable(m, k):
        if player(m, 0x0C) == 7:
            held.append(k)
        return len(held) == 4
    put(capture(ported, 'landing', cable), 'landing-cable.png')


if __name__ == '__main__':
    if '--part2' not in sys.argv:
        main()
    page = conftest.PAGE.read_text(encoding='utf-8')
    part2(conftest.Ported(conftest.payload(page, 'wof-fs')))
