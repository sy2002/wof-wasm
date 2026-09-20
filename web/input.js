/* Input: keyboard and Gamepad API merged into the raw controller state of SPEC 6.1.
 *
 *   bit 0 stick forward (up), bit 1 stick back (down), bit 2 right, bit 3 left,
 *   bit 4 fire button currently down
 *
 * Forward is the stick pushed away from the player: up in the menus, and climbing in flight.
 *
 * The core, not the shell, decides what that becomes: cancelling opposing directions, the
 * reversed-vertical option and the ten-VBlank tap/hold discrimination are all part of the
 * port of vblank_every_frame (re/notes/input.md), because they are evaluated per VBlank
 * while the logic samples them only every fourth one.
 *
 * The shell's one addition is the sticky latch.  The original samples a level 60 times a
 * second; a browser can deliver a key press and its release between two of our VBlanks, so
 * a bit that went down since the last sample stays set for exactly one sample.
 *
 * Keys are read from KeyboardEvent.code, which is positional, like the raw Amiga key codes
 * the menus will need in M3. */

/* No Control key is a fire key: with KeyW mapped to up, firing while climbing would be
   Ctrl+W, which closes the tab in every mainstream browser and which a page cannot prevent.
   Do not add them back. */
const KEYS = {
    ArrowUp: 0x01, KeyW: 0x01,
    ArrowDown: 0x02, KeyS: 0x02,
    ArrowRight: 0x04, KeyD: 0x04,
    ArrowLeft: 0x08, KeyA: 0x08,
    Space: 0x10, KeyZ: 0x10,
};

const PAD_BUTTONS = { 12: 0x01, 13: 0x02, 14: 0x08, 15: 0x04 };  /* d-pad up down left right */
const PAD_FIRE = [0, 1, 2, 3, 6, 7];
const PAD_DEADZONE = 0.4;

export function createInput(target) {
    let held = 0;
    let sticky = 0;

    target.addEventListener('keydown', (e) => {
        const bit = KEYS[e.code];
        if (bit === undefined) {
            return;
        }
        held |= bit;
        sticky |= bit;
        e.preventDefault();
    });

    target.addEventListener('keyup', (e) => {
        const bit = KEYS[e.code];
        if (bit === undefined) {
            return;
        }
        held &= ~bit;
        e.preventDefault();
    });

    /* A key can be released while the page is not listening; forget everything held. */
    window.addEventListener('blur', () => { held = 0; });

    function gamepad() {
        if (!navigator.getGamepads) {
            return 0;
        }
        let bits = 0;
        for (const pad of navigator.getGamepads()) {
            if (!pad) {
                continue;
            }
            for (const index of Object.keys(PAD_BUTTONS)) {
                if (pad.buttons[index] && pad.buttons[index].pressed) {
                    bits |= PAD_BUTTONS[index];
                }
            }
            for (const index of PAD_FIRE) {
                if (pad.buttons[index] && pad.buttons[index].pressed) {
                    bits |= 0x10;
                }
            }
            if (pad.axes.length >= 2) {
                if (pad.axes[0] < -PAD_DEADZONE) bits |= 0x08;
                if (pad.axes[0] > PAD_DEADZONE) bits |= 0x04;
                if (pad.axes[1] < -PAD_DEADZONE) bits |= 0x01;     /* pushed forward */
                if (pad.axes[1] > PAD_DEADZONE) bits |= 0x02;      /* pulled back */
            }
        }
        return bits;
    }

    /* One call per emulated VBlank. */
    function consume() {
        const bits = (held | sticky | gamepad()) & 0x1f;
        sticky = 0;
        return bits;
    }

    /* What the next consume() would return, without consuming the latch: the overlay has to
       show gamepad input too, and must not eat a press on its way past. */
    return { consume, raw: () => (held | sticky | gamepad()) & 0x1f };
}
