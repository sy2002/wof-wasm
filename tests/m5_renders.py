"""Pictures of the M5 scenes the port draws, for looking at (M5 part 1, deliverable 6).

    .venv/bin/python tests/m5_renders.py          writes dist/m5-part1/

Part 1 ports the pass, and the tick that drops and moves the weapons is part 2's, so these
pictures come from the open loop of tests/m4compare.py: every pass starts from the headless
original's state before it, and the picture is what the port draws of that state - the
bombs and rockets in the air, their explosions, the soldiers, the flags, the smoke, the
muzzle flash, the weapon counter, the balloons.  A picture is the port's framebuffer with
each row's palette, rows doubled as in tests/m4_renders.py; the dashboard is also written
alone, four times enlarged.  dist/ is not versioned, and neither are these.
"""
import os
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, 'tools'))
sys.path.insert(0, HERE)

import conftest                            # noqa: E402
import m4compare                           # noqa: E402
import m5_scripts                          # noqa: E402
from m4_renders import picture, save, s16   # noqa: E402

OUT = os.path.join(ROOT, 'dist', 'm5-part1')
PLAYER = 0x025078
OBJECTS = 0x024CAE


def capture(ported, script, want, count=1):
    """Replay `script` in the open loop and return the pictures of the first `count` passes
    for which want(memory, pass) holds."""
    work = tempfile.mkdtemp()
    dump_path = os.path.join(work, script + '.dump')
    pokes = m5_scripts.POKES.get(script)
    machine = m4compare.record(script, dump_path, pokes=pokes)
    replay = m4compare.Replay(ported, machine, dump_path, mode='open', pokes=pokes)
    found = []

    def on_pass(r, memory, head, k):
        if len(found) < count and want(memory, k):
            found.append((k, picture(ported)))

    replay.run(on_pass=on_pass)
    assert found, 'no pass of %s met the condition' % script
    print('%s: passes %s' % (script, [k for k, _ in found]))
    return [image for _, image in found]


def objects(memory, kind=None, types=None):
    out = []
    for i in range(15):
        a = OBJECTS + 0x2A * i
        k = memory.u(a + 0x20, 1)
        if k and (kind is None or k == kind) and (types is None or s16(memory.u(a + 0x22, 2)) in types):
            out.append(i)
    return out


def soldiers(memory, state):
    base, count = memory.u(0x025500, 4), memory.u(0x0253C4, 2)
    return sum(1 for i in range(count) if memory.u(base + 8 * i + 6, 2) == state)


def main():
    page = conftest.PAGE.read_text(encoding='utf-8')
    ported = conftest.Ported(conftest.payload(page, 'wof-fs'))

    def bomb_falling(m, k):
        return len(objects(m, 0xFF, {1})) >= 1 and s16(m.u(0x024F36, 2)) == 8
    save(capture(ported, 'bomb_a', bomb_falling)[0], 'bomb-falling.png', out=OUT)

    burst = []

    def bursting(m, k):
        if objects(m, 8):
            burst.append(k)
        return len(burst) == 3
    image = capture(ported, 'bomb_a', bursting)[0]
    save(image, 'bomb-bursting.png', out=OUT)
    save(image.crop((0, 163, 640, 200)), 'weapon-counter.png', scale=(4, 8), out=OUT)

    def running(m, k):
        return soldiers(m, 1) >= 4 and s16(m.u(0x024F36, 2)) == 8
    save(capture(ported, 'bomb_b', running)[0], 'soldiers-running.png', out=OUT)

    def dying(m, k):
        return soldiers(m, 2) >= 1 and s16(m.u(0x024F36, 2)) == 8
    save(capture(ported, 'bomb_b', dying)[0], 'soldier-dying.png', out=OUT)

    def flag(m, k):
        x = s16(m.u(0x026E5C, 2))
        return 2300 <= x <= 2600 and s16(m.u(0x024F36, 2)) == 8 and m.u(PLAYER + 0x0C, 2) == 0
    save(capture(ported, 'bomb_a', flag)[0], 'island-flag.png', out=OUT)

    def muzzle(m, k):
        return s16(m.u(0x02536A, 2)) != 0 and m.u(0x025388, 1) in (1, 3)
    save(capture(ported, 'guns_sea', muzzle)[0], 'muzzle-flash.png', out=OUT)

    def rocket(m, k):
        return len(objects(m, 0xFF, {0})) >= 1
    save(capture(ported, 'rockets_a', rocket)[0], 'rocket.png', out=OUT)

    def flash(m, k):
        return m.u(0x025416, 2) == 4                   # the pass that found 5 poked the colour
    save(capture(ported, 'rockets_a', flash)[0], 'sky-flash.png', out=OUT)

    smoke = []

    def pillbox_smoke(m, k):
        base = m.u(0x026F58, 4)
        if any(m.u(base + 0x14 * i + 0x10, 2) == 5 for i in range(40)):
            smoke.append(k)
        return len(smoke) == 60
    save(capture(ported, 'rockets_c', pillbox_smoke)[0], 'pillbox-smoke.png', out=OUT)

    def high(m, k):
        return s16(m.u(0x024F36, 2)) == 1 and objects(m, None, {1})
    save(capture(ported, 'high_a', high)[0], 'eighth-scale-bombs.png', out=OUT)

    def balloons(m, k):
        base = m.u(0x026F66, 4)
        up = sum(1 for i in range(20) if m.u(base + 0x12 * i + 0x11, 1))
        return k > 300 and up >= 15 and 5750 <= s16(m.u(0x026E5C, 2)) <= 5950
    save(capture(ported, 'balloons_c', balloons)[0], 'balloons.png', out=OUT)


if __name__ == '__main__':
    main()
