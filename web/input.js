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
 * The shell's one addition is the sticky latch.  The original samples a level once a VBlank,
 * 50 or 60 times a second; a browser can deliver a key press and its release between two of
 * our VBlanks, so a bit that went down since the last sample stays set for exactly one
 * sample.
 *
 * Keys are read from KeyboardEvent.code, which is positional, like the raw Amiga key codes
 * that the menus, the briefing, the line editor and the in-flight commands read (the second
 * path, below). */

/* No Control key is a fire key: with KeyW mapped to up, firing while climbing would be
   Ctrl+W, which closes the tab in every mainstream browser and which a page cannot prevent.
   Do not add them back.  Space is the one fire key: whichever hand steers, arrows or W A S D,
   the other one has it (the owner's decision of 2026-09-30). */
const KEYS = {
    ArrowUp: 0x01, KeyW: 0x01,
    ArrowDown: 0x02, KeyS: 0x02,
    ArrowRight: 0x04, KeyD: 0x04,
    ArrowLeft: 0x08, KeyA: 0x08,
    Space: 0x10,
};

/* The diagnostics key, the key left of 1, by the two codes it can arrive with.  On a Mac with
   an ISO keyboard, the German one among them, Chrome and Safari report that key as
   IntlBackslash and the key right of the left Shift as Backquote; Firefox undoes the swap.
   So both codes toggle the overlay in every browser, which also makes the key right of the
   left Shift a second diagnostics key, and neither reaches the game (web/main.js). */
export const DIAGNOSTIC_CODES = new Set(['Backquote', 'IntlBackslash']);

const PAD_BUTTONS = { 12: 0x01, 13: 0x02, 14: 0x08, 15: 0x04 };  /* d-pad up down left right */
const PAD_FIRE = [0, 1, 2, 3, 6, 7];
const PAD_DEADZONE = 0.4;

/* ------------------------------------------------------- the second path: raw key codes
 *
 * The menus, the briefing, the line editor and the in-flight commands read raw Amiga key
 * codes, which are positional, so the shell maps KeyboardEvent.code, which is positional
 * too: a German keyboard gives the same codes as an American one and the same characters
 * come out of the core's conversion table (re/notes/keys.md, SPEC 6.2).
 *
 * The function keys and Help are deliberately absent.  A page that swallowed F5 or F12
 * would take reload and the developer tools away from the player, and their only readers in
 * the whole executable are two of the debug keys the cheat sequence unlocks (raw 0x59 and
 * 0x5F), which are ported with ingame_keys and out of reach on the page, because the
 * sequence cannot be typed: its l is the load command (re/notes/keys.md).
 */
const RAW_CODES = {
    Digit1: 0x01, Digit2: 0x02, Digit3: 0x03, Digit4: 0x04, Digit5: 0x05,
    Digit6: 0x06, Digit7: 0x07, Digit8: 0x08, Digit9: 0x09, Digit0: 0x0a,
    Minus: 0x0b, Equal: 0x0c, IntlYen: 0x0d, Backspace: 0x41,

    Tab: 0x42,
    KeyQ: 0x10, KeyW: 0x11, KeyE: 0x12, KeyR: 0x13, KeyT: 0x14, KeyY: 0x15,
    KeyU: 0x16, KeyI: 0x17, KeyO: 0x18, KeyP: 0x19,
    BracketLeft: 0x1a, BracketRight: 0x1b,

    CapsLock: 0x62,
    KeyA: 0x20, KeyS: 0x21, KeyD: 0x22, KeyF: 0x23, KeyG: 0x24, KeyH: 0x25,
    KeyJ: 0x26, KeyK: 0x27, KeyL: 0x28,
    Semicolon: 0x29, Quote: 0x2a, Backslash: 0x2b, Enter: 0x44,

    ShiftLeft: 0x60,
    KeyZ: 0x31, KeyX: 0x32, KeyC: 0x33, KeyV: 0x34, KeyB: 0x35, KeyN: 0x36, KeyM: 0x37,
    Comma: 0x38, Period: 0x39, Slash: 0x3a, IntlRo: 0x3b, ShiftRight: 0x61,

    Space: 0x40, Escape: 0x45, Delete: 0x46,
    ArrowUp: 0x4c, ArrowDown: 0x4d, ArrowRight: 0x4e, ArrowLeft: 0x4f,

    Numpad0: 0x0f, Numpad1: 0x1d, Numpad2: 0x1e, Numpad3: 0x1f,
    Numpad4: 0x2d, Numpad5: 0x2e, Numpad6: 0x2f,
    Numpad7: 0x3d, Numpad8: 0x3e, Numpad9: 0x3f,
    NumpadDecimal: 0x3c, NumpadEnter: 0x43, NumpadSubtract: 0x4a,
    NumpadLeftParen: 0x5a, NumpadRightParen: 0x5b,
    NumpadDivide: 0x5c, NumpadMultiply: 0x5d, NumpadAdd: 0x5e,
};

/* The qualifier bits the shell sends.  Never Control: the game reads that bit and the
   port's own key layer is what puts it there (SPEC 6.2). */
const IEQUALIFIER_LSHIFT = 0x0001;
const IEQUALIFIER_RSHIFT = 0x0002;
const IEQUALIFIER_CAPSLOCK = 0x0004;

export function createInput(target, core) {
    let held = 0;
    let sticky = 0;
    let shiftLeft = false;
    let shiftRight = false;

    /* The qualifier word of a key press.  Which Shift key is down is tracked rather than
       taken from event.shiftKey, which does not say; without either of them seen the left
       one is assumed, because the two convert alike. */
    function qualifier(e) {
        let bits = 0;
        if (shiftLeft || (e.shiftKey && !shiftRight)) {
            bits |= IEQUALIFIER_LSHIFT;
        }
        if (shiftRight) {
            bits |= IEQUALIFIER_RSHIFT;
        }
        if (e.getModifierState && e.getModifierState('CapsLock')) {
            bits |= IEQUALIFIER_CAPSLOCK;
        }
        return bits;
    }

    target.addEventListener('keydown', (e) => {
        if (e.code === 'ShiftLeft') {
            shiftLeft = true;
        } else if (e.code === 'ShiftRight') {
            shiftRight = true;
        }

        /* A key pressed with Control, Alt or Command belongs to the browser, not to the
           game, and a page cannot take all of those away from it (SPEC 6.2). */
        /* The diagnostics key's two codes (DIAGNOSTIC_CODES) are not in the table: the game
           never sees them, and web/index.html names the key by its position. */
        const raw = RAW_CODES[e.code];
        if (raw !== undefined && !e.ctrlKey && !e.altKey && !e.metaKey && core) {
            core.portKey(raw, qualifier(e));
            e.preventDefault();
        }

        const bit = KEYS[e.code];
        if (bit === undefined) {
            return;
        }
        held |= bit;
        sticky |= bit;
        e.preventDefault();
    });

    target.addEventListener('keyup', (e) => {
        if (e.code === 'ShiftLeft') {
            shiftLeft = false;
        } else if (e.code === 'ShiftRight') {
            shiftRight = false;
        }
        const bit = KEYS[e.code];
        if (bit === undefined) {
            return;
        }
        held &= ~bit;
        e.preventDefault();
    });

    /* A key can be released while the page is not listening; forget everything held. */
    window.addEventListener('blur', () => { held = 0; shiftLeft = false; shiftRight = false; });

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
    return { consume, raw: () => (held | sticky | gamepad()) & 0x1f, rawCodes: RAW_CODES };
}
