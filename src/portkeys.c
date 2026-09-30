/* The port's own layer in front of the key buffer (SPEC 6.1 and 6.2).
 *
 * This file is not a port of anything: it is policy, decided with the owner on 2026-09-20,
 * and it is kept apart from src/keys.c for that reason.  Two things live here.
 *
 * The command keys.  The original's commands are Escape and Control with R, C, F, G, L and
 * S (re/notes/keys.md).  A browser keeps Control with those letters for itself - reload,
 * find, the address bar - and a page cannot prevent all of them, so the port gives the
 * commands plain keys and rewrites them here into the code and qualifier the original's
 * readers expect.  The readers themselves are untouched.  Two restrictions narrow the
 * original and add nothing to it: without Control in front of it a stray key would throw a
 * campaign away, so the restart and the high-score clear are rewritten only where the
 * player has already stopped playing - while the game is paused, and the restart in the
 * briefing as well.  Where a restriction does not hold the key passes on as it came, which
 * is exactly what the original does with a plain letter, so nothing that used to work stops
 * working there.  Inside the line editor no command applies at all and every key passes.
 *
 * The vertical flip.  In the original opt_invert_vertical is game state: it starts at 0,
 * only the flip command writes it, and a loaded game overwrites it, so the setting can be
 * taken away under the player (re/notes/keys.md).  The owner flies with the flip on, so the
 * port treats it as a preference: the shell stores it and hands it over at start, the flip
 * command changes the preference with the byte, and after a loaded game the preference
 * wins.  A core that was never given a preference behaves exactly as the original, which is
 * what the differential tests run.
 */
#include "wof.h"

/* Raw Amiga key codes, by position (re/notes/input.md: raw codes are positional, which is
 * why the shell maps KeyboardEvent.code, which is positional too). */
#define RAW_R      0x13
#define RAW_S      0x21
#define RAW_F      0x23
#define RAW_G      0x24
#define RAW_L      0x28
#define RAW_C      0x33
#define RAW_M      0x37
#define RAW_P      0x19
#define RAW_ESCAPE 0x45

/* The one qualifier bit the game reads (re/notes/keys.md). */
#define IEQUALIFIER_CONTROL 0x0008u

/* The shell's entry.  The state that decides what happens here - the line editor, the
 * pause, the briefing - lives in the core, which is why this layer does (SPEC 6.1). */
void wof_port_key(uint8_t code, uint16_t qualifier)
{
    uint16_t with_control = (uint16_t)(qualifier | IEQUALIFIER_CONTROL);

    /* The keyboard assist steps the weapon menu with the stick alone; the cursor keys would
     * reach it a second time through last_key (src/assist.c). */
    if (wof_assist_swallows(code))
        return;
    if (!wof_f.editing) {
        switch (code) {
        case RAW_P:                             /* KeyP pauses and continues */
            wof_key(RAW_ESCAPE, qualifier);
            return;
        case RAW_F:                             /* KeyF flips the vertical control */
            wof_key(RAW_F, with_control);
            return;
        case RAW_G:                             /* KeyG saves, on the carrier only */
            wof_key(RAW_G, with_control);
            return;
        case RAW_L:                             /* KeyL loads */
            wof_key(RAW_L, with_control);
            return;
        case RAW_M:                             /* KeyM switches the music: KeyS is the stick */
            wof_key(RAW_S, with_control);
            return;
        case RAW_R:                             /* KeyR restarts, paused or in the briefing */
            if (wof_g.pause_flag || wof_f.briefing) {
                wof_key(RAW_R, with_control);
                return;
            }
            break;
        case RAW_C:                             /* KeyC clears the high scores, paused only */
            if (wof_g.pause_flag) {
                wof_key(RAW_C, with_control);
                return;
            }
            break;
        default:
            break;
        }
    }
    wof_key(code, qualifier);
}

/* ------------------------------------------------------------------ the help screen */

/* The shell's help screen pauses a running mission with wof_request_pause and, when it
 * closes, continues it with this (SPEC 6.2).  A pause asked for and not yet taken is simply
 * withdrawn; a mission the request did pause gets the Escape that KeyP gives, so the next
 * ingame_keys continues it exactly as P would.  Outside a mission, or with nothing paused,
 * there is nothing to continue.  The shell only calls it for a pause the help asked for
 * itself: a pause the player made stays. */
void wof_request_continue(void)
{
    if (wof_g.outside_mission)
        return;
    wof_f.pause_request = 0;
    if (wof_g.pause_flag)
        wof_key(RAW_ESCAPE, 0);
}

/* The line editor has the keys (text_input, src/dialog.c): the high-score name and the
 * dialog's file names.  Read-only. */
int wof_line_editor_active(void)
{
    return wof_f.editing ? 1 : 0;
}

/* ------------------------------------------------------------------ the vertical flip */

void wof_set_invert_vertical(int on)
{
    wof_s.invert_given         = 1;
    wof_s.invert_pref          = on ? 1u : 0u;
    wof_g.opt_invert_vertical  = on ? 0xFFu : 0x00u;
}

int wof_invert_vertical(void)
{
    return wof_g.opt_invert_vertical ? 1 : 0;
}

/* The flip command changes both (M4, ingame_keys 0x01CD6E writes the byte with not.b). */
void wof_invert_vertical_follow(void)
{
    if (wof_s.invert_given)
        wof_s.invert_pref = wof_g.opt_invert_vertical ? 1u : 0u;
}

/* opt_invert_vertical (0x0254F6) lies inside the raw part a saved game covers, so loading
 * one overwrites it.  The loader (wof_save_game_read, src/dialog.c) calls this afterwards
 * and the preference wins. */
void wof_invert_vertical_restore(void)
{
    if (wof_s.invert_given)
        wof_g.opt_invert_vertical = wof_s.invert_pref ? 0xFFu : 0x00u;
}
