"""Pictures of the M6 scenes the port draws, for looking at.

    .venv/bin/python tests/m6_renders.py          writes dist/m6-part1/ and dist/m6-part2/
    .venv/bin/python tests/m6_renders.py 2        only dist/m6-part2/

Part 2's pictures come from the closed loop: the port runs on its own from the program's
start, and the picture is its own state (a fighter on the tail firing, a torpedo plane at
its drop, the carrier sinking, the carrier hit, an aircraft shot down and falling, the Japanese
carrier's aircraft rolling, a wreck burning on land).  The conditions read the original's
memory at the same pass, which the closed loop holds equal to the port's.

Part 1 ports the pass, and the tick that flies the enemy aircraft and sinks the ships is part
2's, so these pictures come from the open loop of tests/m4compare.py: every pass starts
from the headless original's state before it, and the picture is what the port draws of
that state - the enemy aircraft and their guns' flash, the wrecks on the water, the ships'
guns and the aircraft on their decks, the Japanese carrier, the airfields, the
arrow to a torpedo plane, the enemy plane counter with its kill icons and the 3-D view with
an enemy in it.  A picture is the port's framebuffer with each row's palette, rows doubled
as in tests/m4_renders.py; the dashboard is also written alone, four times enlarged.  dist/
is not versioned, and neither are these.
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
import m6_scripts                          # noqa: E402
from m4_renders import picture, save, s16   # noqa: E402

OUT = os.path.join(ROOT, 'dist', 'm6-part1')
OUT2 = os.path.join(ROOT, 'dist', 'm6-part2')
PLAYER = 0x025078
AIRCRAFT = 0x02522A


class Enough(Exception):
    pass


def capture(ported, script, want, count=1, mode='open'):
    """Replay `script` in the open or the closed loop until `count` passes met
    want(memory, pass), and return their pictures."""
    work = tempfile.mkdtemp()
    dump_path = os.path.join(work, script + '.dump')
    pokes = m6_scripts.pokes(script)
    machine = m4compare.record(script, dump_path, pokes=pokes)
    replay = m4compare.Replay(ported, machine, dump_path, mode=mode, pokes=pokes)
    found = []

    def on_pass(r, memory, head, k):
        if want(memory, k):
            found.append((k, picture(ported)))
            if len(found) >= count:
                raise Enough()

    try:
        replay.run(on_pass=on_pass)
    except Enough:
        pass
    assert found, 'no pass of %s met the condition' % script
    print('%s: passes %s' % (script, [k for k, _ in found]))
    return [image for _, image in found]


def enemies(memory):
    """(state, mode, x, y, firing, flash) of the enemy aircraft in use."""
    out = []
    for i in range(4):
        a = AIRCRAFT + 0x34 * i
        if memory.u(a, 2):
            out.append((memory.u(a, 2), memory.u(a + 2, 2), s16(memory.u(a + 0x20, 2)),
                        s16(memory.u(a + 0x26, 2)), memory.u(a + 0x12, 2),
                        memory.u(a + 0x2C, 2)))
    return out


def full(memory):
    return s16(memory.u(0x024F36, 2)) == 8


def near(memory, lo, hi):
    return lo <= s16(memory.u(0x026E5C, 2)) <= hi


def dashboard(image, name):
    save(image.crop((0, 163, 640, 200)), name, scale=(2, 4), out=OUT)


def part2(ported):
    """The tick's scenes from the closed loop into dist/m6-part2/."""
    def closed(script, want):
        return capture(ported, script, want, mode='closed')[0]

    def around(m, states=None, modes=None, width=150):
        px = s16(m.u(0x026E5C, 2))
        return [e for e in enemies(m) if abs(e[2] - px) < width and
                (states is None or e[0] in states) and (modes is None or e[1] in modes)]

    def tail_firing(m, k):
        return full(m) and any(f and fl & 1 for _, mode, _, _, f, fl in around(m, {2}, {2}))
    save(closed('oil_d', tail_firing), 'fighter-on-the-tail-firing.png', out=OUT2)

    def drop(m, k):
        return full(m) and around(m, {2}, {0x10}, 200) and m.u(0x025594 + 0x20, 1) == 0xFF
    save(closed('countdown_b', drop), 'torpedo-plane-dropped.png', out=OUT2)

    def sinking(m, k):                        # the carrier, low over it: the cruise ship
        rows = s16(m.u(0x0254D8 + 0x14, 2))  # sinks while torpedo_f flies high over it
        return full(m) and 4 <= rows <= 0x40 and near(m, 6300, 7600) and \
            s16(m.u(PLAYER, 2)) < 100
    save(closed('sunk_a', sinking), 'carrier-sinking.png', out=OUT2)

    def carrier_hit(m, k):
        return full(m) and s16(m.u(0x0254D8 + 0x0C, 2)) == 3 and m.u(0x025416, 2) > 0
    save(closed('enemy_a', carrier_hit), 'carrier-hit.png', out=OUT2)

    def falling(m, k):
        return full(m) and around(m, {4}, None, 160)
    save(closed('fight_a', falling), 'shot-down-falling.png', out=OUT2)

    def rolling(m, k):
        count = m.u(0x025196, 2)
        flag = s16(m.u(0x025196 + 8 + 8 * (count - 1), 2)) if count else 0
        return full(m) and flag > 0 and m.u(0x02734A, 2) > 0x20 and near(m, 21700, 22800)
    save(closed('japcarrier_m', rolling), 'japanese-carrier-rolling.png', out=OUT2)

    def burning(m, k):
        return full(m) and around(m, {0x10}, None, 160)
    save(closed('burning_a', burning), 'wreck-burning-on-land.png', out=OUT2)


def main():
    page = conftest.PAGE.read_text(encoding='utf-8')
    ported = conftest.Ported(conftest.payload(page, 'wof-fs'))
    if sys.argv[1:] == ['2']:
        part2(ported)
        return

    def fighter_near(m, k):
        px = s16(m.u(0x026E5C, 2))
        return full(m) and any(s == 2 and abs(x - px) < 120 for s, _, x, _, _, _ in enemies(m))
    image = capture(ported, 'oil_d', fighter_near)[0]
    save(image, 'fighter.png', out=OUT)
    dashboard(image, 'fighter-3d-view.png')

    def firing(m, k):
        return full(m) and any(f and fl & 1 for _, _, _, _, f, fl in enemies(m))
    save(capture(ported, 'oil_d', firing)[0], 'fighter-firing.png', out=OUT)

    def airfield(m, k):
        return full(m) and near(m, 3100, 3500) and m.u(PLAYER + 0x0C, 2) == 0
    save(capture(ported, 'oil_d', airfield)[0], 'airfield.png', out=OUT)

    def night(m, k):
        px = s16(m.u(0x026E5C, 2))
        return full(m) and any(abs(x - px) < 140 for _, _, x, _, _, _ in enemies(m))
    save(capture(ported, 'night_d', night)[0], 'night-fighter.png', out=OUT)

    def cruise(m, k):
        return full(m) and near(m, 5250, 5450) and m.u(PLAYER + 0x0C, 2) == 0
    save(capture(ported, 'cruise_f', cruise)[0], 'cruise-ship-guns.png', out=OUT)

    def torpedo_sight(m, k):
        return full(m) and near(m, 5750, 6000) and s16(m.u(PLAYER, 2)) < 40
    image = capture(ported, 'torpedo_f', torpedo_sight)[0]
    save(image, 'torpedo-run.png', out=OUT)
    dashboard(image, 'torpedo-run-3d-view.png')

    def battleship(m, k):
        return full(m) and near(m, 7300, 7800) and m.u(PLAYER + 0x0C, 2) == 0
    save(capture(ported, 'battleship_j', battleship)[0], 'battleship.png', out=OUT)

    def japcarrier(m, k):
        return full(m) and near(m, 22150, 22500) and m.u(PLAYER + 0x0C, 2) == 0
    save(capture(ported, 'japcarrier_m', japcarrier)[0], 'japanese-carrier.png', out=OUT)

    def wrecks(m, k):
        return full(m) and near(m, 6950, 7250) and m.u(PLAYER + 0x0C, 2) == 0
    save(capture(ported, 'wrecks_a', wrecks)[0], 'wrecks.png', out=OUT)

    def high(m, k):
        return s16(m.u(0x024F36, 2)) == 1 and near(m, 6900, 7600)
    save(capture(ported, 'wrecks_a', high)[0], 'wrecks-eighth-scale.png', out=OUT)

    def kills(m, k):
        return k > 20 and m.u(PLAYER + 0x0C, 2) == 0
    dashboard(capture(ported, 'kills_a', kills)[0], 'kill-icons.png')

    def arrow(m, k):
        return any(mode & 7 == 4 for _, mode, _, _, _, _ in enemies(m)) and \
            m.u(PLAYER + 0x0C, 2) == 0
    dashboard(capture(ported, 'countdown_b', arrow)[0], 'torpedo-plane-arrow.png')
    part2(ported)


if __name__ == '__main__':
    main()
