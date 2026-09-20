/* The key buffer and its readers (re/notes/keys.md, re/notes/input.md).
 *
 * The keyboard is a path of its own: it never reaches game logic through the input byte.
 * On the machine an input.device handler at priority 127 appends raw Amiga key codes and
 * their qualifier words to a ten-deep buffer, and five routines read them - the menus, the
 * release wait, the line editor, the briefing and the in-flight commands.  The port keeps
 * the buffer and the readers exactly; what it drops is the plumbing around them:
 *
 *   - the InputEvent chain and the ie_Class the handler clears, because there is no
 *     input.device to swallow an event from;
 *   - the IECLASS_RAWMOUSE half, which tracks the right mouse button in rmb_down
 *     (0x027F6E); a grep over the whole listing finds the two writes and no read, and no
 *     run of the original ever read the address (re/notes/keys.md);
 *   - key_get's WaitTOF spin on an empty buffer.  Only key_wait_char (0x0206EE) reaches
 *     key_get without asking key_available first, and it has no caller; every live reader
 *     asks first.  wof_key_get on an empty buffer returns 0 instead of blocking.
 *   - keyboard_open's ports and devices (0x0205CC), of which only the three words it sets
 *     are kept.
 *
 * key_qualifier_mask is kept although it is dead: task_setup (0x0125C6) sets
 * key_mask_default to 0x10 only when it finds a trap handler that is not the one dos gives
 * a process, which a game started from the CLI under Kickstart 1.3 never is, so the mask is
 * 0 in play.  It costs three lines and it is what the readers would see on the other path.
 */
#include "wof.h"
#include "gen/tables.h"

/* orig 0x0205CC keyboard_open - the three words it sets before it opens anything.  The
 * mask comes from key_mask_default (0x027162), which is 0 on the path a game started from
 * the CLI takes (re/notes/headless.md). */
void wof_keys_init(void)
{
    wof_g.key_qualifier_mask = 0;
    wof_g.key_buffer_max     = 10;
    wof_g.key_count          = 0;
    for (uint16_t i = 0; i < 10; i++) {
        wof_g.key_buffer[i]           = 0;
        wof_g.key_qualifier_buffer[i] = 0;
    }
}

/* orig 0x02075A input_handler, the IECLASS_RAWKEY half.  A key-up event has bit 7 of the
 * code set and is ignored; when the qualifier mask is not 0 a key that carries none of its
 * bits is dropped; a full buffer drops the key and keeps the event. */
void wof_key(uint8_t code, uint16_t qualifier)
{
    if (code & 0x80u)
        return;
    if (wof_g.key_qualifier_mask && !(qualifier & wof_g.key_qualifier_mask))
        return;
    if ((int16_t)wof_g.key_count >= (int16_t)wof_g.key_buffer_max)
        return;
    wof_g.key_buffer[wof_g.key_count]           = code;
    wof_g.key_qualifier_buffer[wof_g.key_count] = qualifier;
    wof_g.key_count++;
}

/* orig 0x0207D8 - 0xFF when something is waiting, 0 when not. */
int wof_key_available(void)
{
    return wof_g.key_count ? 0xFF : 0;
}

/* The original's shift loop runs from index 0 up to and including the new key_count, so
 * with a full buffer its last round copies one entry past the end of each array.  On the
 * machine those two reads land on the next globals: key_buffer + 10 is the first byte of
 * key_qualifier_buffer, which big-endian is the high byte of its first word, and
 * key_qualifier_buffer + 20 is key_count itself.  The port keeps the values rather than the
 * adjacency, so that the quirk survives a struct whose order is its own. */
static uint8_t key_code_at(uint16_t i)
{
    if (i < 10)
        return wof_g.key_buffer[i];
    return (uint8_t)(wof_g.key_qualifier_buffer[0] >> 8);
}

static uint16_t key_qualifier_at(uint16_t i)
{
    if (i < 10)
        return wof_g.key_qualifier_buffer[i];
    return wof_g.key_count;
}

/* orig 0x0207E4 - pops the oldest key as (qualifier << 16) | raw code and shifts the
 * buffer down.  The bits of key_qualifier_mask are taken out of the qualifier on the way. */
uint32_t wof_key_get(void)
{
    if (!wof_g.key_count)
        return 0;                     /* the original would spin on WaitTOF here */

    uint32_t key = ((uint32_t)wof_g.key_qualifier_buffer[0] << 16) | wof_g.key_buffer[0];

    wof_g.key_count--;
    for (uint16_t i = 0; i <= wof_g.key_count; i++) {
        wof_g.key_buffer[i]           = key_code_at((uint16_t)(i + 1));
        wof_g.key_qualifier_buffer[i] = key_qualifier_at((uint16_t)(i + 1));
    }

    if (wof_g.key_qualifier_mask) {
        uint16_t keep = (uint16_t)~wof_g.key_qualifier_mask;
        key = ((uint32_t)(((uint16_t)(key >> 16)) & keep) << 16) | (key & 0xFFFFu);
    }
    return key;
}

/* orig 0x020700 key_to_char - the raw code and its qualifier through console.device's
 * RawKeyConvert with the system's default keymap, accepted only when exactly one character
 * comes back.  The port does not run the routine: the build ran it once, over every raw
 * code and every qualifier combination the shell can send, and wrote the characters as a
 * table (SPEC 5 step 1, re/notes/keys.md, recommendation 2).
 *
 * The table covers the four qualifier bits the shell and the port's key layer produce -
 * both Shift keys, Caps Lock and Control - because a key pressed with Alt or Command is
 * ignored by the shell (SPEC 6.2) and the game itself only ever tests Control.  Other bits
 * are ignored here; if a later milestone needs Alt, the table grows a dimension. */
uint16_t wof_key_to_char(uint32_t key)
{
    uint16_t code      = (uint16_t)(key & 0xFFFFu);
    uint16_t qualifier = (uint16_t)(key >> 16);

    if (code >= WOF_TBL_KEYMAP_CODES)
        return 0;                     /* input_handler never buffers a code above 0x7F */
    return wof_tbl_keymap[code * WOF_TBL_KEYMAP_QUALIFIERS
                          + (qualifier & (WOF_TBL_KEYMAP_QUALIFIERS - 1))];
}
