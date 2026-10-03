# Input

Answers point 1 of `SPEC.md` section 10. Everything here is read from the disassembly; addresses use the standard load layout.

## Summary

Game logic never touches the hardware. It reads **one input byte per logic tick**, from `tick_input` (`0x026D42`). Everything below is the machinery that produces that byte. For the port, only the byte and its timing have to be faithful; how it is produced is free.

## The chain

```text
JOY1DAT (0xDFF00C)  ──► read_joy_bits 0x01520E ──┐
CIA-A PRA bits 6,7  ──► read_fire_button 0x02046A│
                             │                   │
                             ▼                   ▼
                    vblank_every_frame     read_joystick 0x01CA32
                       0x01C9CA                  │  (every 4th VBlank)
                    (every VBlank)               │
                    tap / hold latches ─────────►│
                                                 ▼
                                            input_byte 0x027366
                                                 │
                                   vblank_server 0x011754 appends
                                                 ▼
                                    input_queue 0x027356  (max 6)
                                                 │
                                run_queued_ticks 0x0114D8, one tick each
                                                 ▼
                                     logic_tick 0x011386 pops it into
                                          tick_input 0x026D42
```

`tick_input` is then read by about ten subsystem routines (`0x01AFA8`, `0x01B5B4`, `0x01BA08`, `0x01BC1E`, `0x01C026`, `0x01C0F6`, `0x01C176`, `0x01C4F6`, `0x0112C0`).

## Input byte layout

Only the low byte of the word at `0x027366` is used.

| Bit | Meaning |
|---|---|
| 0 | stick forward: up in the menus, climb in flight |
| 1 | stick back: down in the menus, descend in flight |
| 2 | stick right |
| 3 | stick left |
| 4 | fire **held** — down for 10 or more VBlanks |
| 5 | fire **tapped** — pressed and released inside 10 VBlanks |
| 6, 7 | unused |

Note that `read_joystick` swaps the left and right bits on the way in: the bitmask from `read_joy_bits` uses b2 for left and b3 for right, the input byte uses b2 for right and b3 for left.

## Direction decoding

`read_joy_bits` (`0x01520E`) reads JOY1DAT, which is joystick port 2, builds a 4-bit index from bits 9, 8, 1, 0 and looks up `joy_bits_table` (`0x0256A6`, 16 bytes):

```text
00 02 0a 08 01 00 00 09 05 00 00 00 04 06 00 00
```

The index is bit 9, bit 8, bit 1, bit 0 of the register, in that order. That is the standard Amiga gray-code decode (`right = b1`, `left = b9`, `back = b1 xor b0`, `forward = b9 xor b8`) baked into a table, producing `b0 = forward, b1 = back, b2 = left, b3 = right`. Forward is the stick pushed away from the player. Run under the oracle, the routine returns 1 for `JOY1DAT` = `0x0100` and 2 for `0x0001`; in the menus forward moves the cursor up like the cursor-up key `0x4C`, and in flight it climbs (`re/notes/headless.md`). **Every contradictory combination maps to 0**, that is, to centre: up with down, left with right, and anything containing them. Nine of the sixteen entries are live, seven are 0.

If `opt_invert_vertical` (`0x0254F6`) is set and at least one of the vertical bits is set, the routine applies `eori #3`, which swaps up and down. This is the reversed-vertical-control option. The guard matters: without it, `eori #3` on a neutral stick would produce up **and** down at once.

`read_joy_dir8` (`0x020488`) decodes the same register into a single direction code (0 centre, then clockwise from 1 up, which is the stick forward: 2 up-right, 3 right, 4 down-right, 5 down, 6 down-left, 7 left, 8 up-left) through `joy_dir8_table` (`0x0204B0`). It feeds `joy_dir8` (`0x027742`) and is used outside the tick path by the menus' pollers, which `menu_input`, `wait_input_release` and `text_input` call (chapter 19 of the book).

## Fire button and the tap/hold discrimination

`read_fire_button` (`0x02046A`) returns 1 if the button is down on **either** port: CIA-A PRA bit 6 is port 1, bit 7 is port 2, both active low.

`vblank_every_frame` (`0x01C9CA`) runs on **every** VBlank and does the timing:

```c
vblank_counter++;
fire = read_fire_button();
if (fire && !fire_prev_state)
    fire_press_frame = vblank_counter;              /* press edge */
if (vblank_counter < fire_press_frame + 10) {
    if (!fire && fire_prev_state) fire_tap_latch = 1;   /* released early  -> bit 5 */
} else {
    if (fire) fire_hold_latch = 1;                      /* still down      -> bit 4 */
}
if (!fire) fire_press_frame = 0;
fire_prev_state = fire;
```

`read_joystick` consumes the latches and clears them. A tap wins: when `fire_tap_latch` is set it emits bit 5 and clears **both** latches, so one sample never reports tap and hold together.

Two consequences the port has to keep:

- The threshold is 10 **VBlanks**, not 10 ticks. The timing runs at 60 Hz while sampling runs at 15 Hz, so tap and hold must be evaluated per VBlank inside the core.
- The latches persist between samples, so a tap that starts and ends between two samples is still delivered. A per-tick poll of the button would lose it.

## Keyboard and mouse

Entirely separate from the input byte, so it does not reach game logic through the tick.

`input_handler` (`0x02075A`) is installed on input.device at priority 127 by the routine at `0x0205F0`, which also opens console.device. It walks the InputEvent list and:

- on `IECLASS_RAWMOUSE`, tracks the right mouse button in `rmb_down` (`0x027F6E`) from codes `0x69` down and `0xE9` up;
- on `IECLASS_RAWKEY`, ignores key-up events (code bit 7 set), optionally filters by `key_qualifier_mask` (`0x026D30`), then appends the **raw Amiga key code** to `key_buffer` (`0x026C98`) and the qualifier to `key_qualifier_buffer` (`0x026CA2`), and clears `ie_Class` so the event is swallowed and never reaches the rest of the system.

The buffer is drained by the routines at `0x0207DA`–`0x020828`. Because the codes are raw and positional, the port's key mapping has to be positional too.

## Answered elsewhere

- **Which raw key codes the game tests, and in which states**: `re/notes/keys.md`, with the five
  readers of the buffer, the table of commands and a run of the headless original behind each row.
  Control is the qualifier bit `0x0008`; raw codes become characters through console.device
  `RawKeyConvert` and the system keymap.
- **Whether `rmb_down` is read anywhere that matters**: it is not. `input_handler` writes it from
  raw codes `0x69` and `0xE9` and nothing in the executable reads it (`re/notes/keys.md`).

## Open

- `read_joy_dispatch` (`0x01CB20`) takes an alternative path to `sub_021DCE` when `g_026EB0` is set. Establish what that is; a second controller type is a plausible guess but it is only a guess.
- What the meaning of tap versus hold is in each game state, which is a question for the consumers of `tick_input`, not for this note.
