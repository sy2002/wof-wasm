/* The waits and the fades of the front end, as coroutines (SPEC 6.3, re/notes/frontend.md).
 *
 * Four routines of the original block, and every one of them blocks by counting rounds of
 * graphics.WaitTOF: wait_frames_or_fire, menu_input, wait_input_release and the fades.  One
 * round is one VBlank, and one CO_WAIT is one pass, which the shell issues once per VBlank,
 * so the port counts the same rounds against the same clock.
 *
 * The fades are the exception, the one setting of the port that rests on no measurement.  A
 * fade is sixteen steps of arithmetic and a copper rebuild with no wait in it at all, so on
 * the machine its duration is CPU time and nothing in the executable says how much
 * (re/notes/display.md).  The port gives a step a fixed number of VBlanks, fade_vblanks
 * (wof_set_fade_vblanks), 2 by the owner's eye and kept so; the differential tests set it to
 * 0, where the harness' fades take no time either, and the two then agree VBlank for VBlank.
 */
#include "wof.h"
#include "coro.h"

/* PROVISIONAL (SPEC 10, point 6): how long one of the sixteen steps of a fade takes.  Read
 * the listing as one may, it cannot be settled there; a cycle-exact emulator can. */
static uint16_t fade_vblanks = 2;

void wof_set_fade_vblanks(int n)
{
    fade_vblanks = (uint16_t)(n < 0 ? 0 : n > 64 ? 64 : n);
}

int wof_fade_vblanks(void)
{
    return fade_vblanks;
}

/* orig 0x016EEE wait_frames_or_fire - one WaitTOF, then up to n - 1 more, ending early as
 * soon as the button is down.  It returns the button's state, which is how the callers
 * know whether the player skipped ahead. */
wof_co_t wof_wait_frames_or_fire(uint16_t n)
{
    wof_ctx_t *c = &wof_f.co_frames;

    CO_BEGIN(c);
    wof_f.frames_n = n;
    CO_WAIT(c);
    wof_f.frames_i = 1;
    while ((int16_t)wof_f.frames_i < (int16_t)wof_f.frames_n) {
        if (wof_poll_fire())
            break;
        CO_WAIT(c);
        wof_f.frames_i++;
    }
    wof_f.frames_fire = (uint16_t)wof_poll_fire();
    CO_END(c);
}

int wof_frames_fire(void)
{
    return wof_f.frames_fire;
}

/* orig 0x018194 menu_input - the reader of the rank selection and of the dialog's list.
 * The cursor keys and Return come out of the key buffer, the stick and the button are
 * polled, and with its argument non-zero it gives up after 1800 rounds and returns 1000,
 * which is what asks for demo playback.  The qualifier is ignored: the raw code is taken
 * from the low word of what key_get returns. */
wof_co_t wof_menu_input(uint16_t timeout)
{
    wof_ctx_t *c = &wof_f.co_menu;

    CO_BEGIN(c);
    wof_f.menu_timeout = timeout;
    wof_f.menu_rounds  = 0;
    for (;;) {
        if (wof_key_available()) {
            uint16_t key = (uint16_t)(wof_key_get() & 0xFFFFu);

            if (key == 0x4C) { wof_f.menu_result = -1; CO_RETURN(c); }
            if (key == 0x4D) { wof_f.menu_result =  1; CO_RETURN(c); }
            if (key == 0x44 || key == 0x43) { wof_f.menu_result = 0; CO_RETURN(c); }
        }
        {
            int dir = wof_poll_joy_dir8();

            if (dir == 1) { wof_f.menu_result = -1; CO_RETURN(c); }
            if (dir == 5) { wof_f.menu_result =  1; CO_RETURN(c); }
        }
        if (wof_poll_fire()) { wof_f.menu_result = 0; CO_RETURN(c); }
        CO_WAIT(c);
        wof_f.menu_rounds++;
        if (wof_f.menu_timeout && (int16_t)wof_f.menu_rounds > 0x708) {
            wof_f.menu_result = 1000;
            CO_RETURN(c);
        }
    }
    CO_END(c);
}

int wof_menu_result(void)
{
    return wof_f.menu_result;
}

/* orig 0x018228 wait_input_release - up to nine rounds of waiting for the button and the
 * stick to come back to rest.  A key already waiting ends it at once, and so does an input
 * that is already at rest; only a held button or a pushed stick keeps it going. */
wof_co_t wof_wait_input_release(void)
{
    wof_ctx_t *c = &wof_f.co_release;

    CO_BEGIN(c);
    wof_f.release_i = 0;
    do {
        CO_WAIT(c);
        if (wof_key_available() || !(wof_poll_fire() || wof_poll_joy_dir8()))
            wof_f.release_i = 1000;
        wof_f.release_i++;
    } while ((int16_t)wof_f.release_i < 9);
    CO_END(c);
}

/* ------------------------------------------------------------------------- the fades */

/* orig 0x017084 fade_to, 0x0171F2 fade_to_pair, 0x0173B0 fade_out and 0x0173E6
 * fade_out_pair, which are one routine with two shapes.
 *
 * fade_to moves both colour tables of the front view's first viewport towards one target
 * table.  fade_to_pair moves the first viewport's table 1 towards the first target, the
 * second viewport's table 1 towards the second, and the first viewport's table 2 towards
 * the first target again.  The two fade_out routines are the same with an all-black target.
 * The number of colours is 1 << depth of the **first** viewport in both, even in the pair,
 * where the second viewport may have a depth of its own.
 *
 * colour_lerp's arithmetic is kept exactly as it is (src/iff.c, verified in M1): a falling
 * component adds its negative quotient as a masked two's complement value and carries into
 * the next higher one, which is what every fade-out's intermediate colours depend on. */
static void fade_begin(const uint16_t *target1, const uint16_t *target2, int pair)
{
    wof_vport_t *v = wof_front_vport();
    wof_vport_t *w = 0;

    if (!v)
        return;
    if (pair && v->next != WOF_VP_NONE)
        w = &wof_f.vport[v->next];

    wof_f.fade_pair  = (uint16_t)(pair != 0);
    wof_f.fade_count = (uint16_t)(1u << v->depth);
    if (wof_f.fade_count > WOF_PAL_COLOURS)
        wof_f.fade_count = WOF_PAL_COLOURS;

    for (uint16_t i = 0; i < wof_f.fade_count; i++) {
        wof_f.fade_start1[i]  = v->colours[i];
        wof_f.fade_start2[i]  = (pair && w) ? w->colours[i] : 0;
        wof_f.fade_start3[i]  = v->colours2[i];
        wof_f.fade_target1[i] = target1 ? target1[i] : 0;
        wof_f.fade_target2[i] = target2 ? target2[i] : 0;
    }
}

static void fade_apply(uint16_t step)
{
    wof_vport_t *v = wof_front_vport();
    wof_vport_t *w = 0;

    if (!v)
        return;
    if (wof_f.fade_pair && v->next != WOF_VP_NONE)
        w = &wof_f.vport[v->next];

    for (uint16_t i = 0; i < wof_f.fade_count; i++) {
        v->colours[i] = wof_colour_lerp((int16_t)step, wof_f.fade_start1[i],
                                        wof_f.fade_target1[i]);
        if (wof_f.fade_pair) {
            if (w)
                w->colours[i] = wof_colour_lerp((int16_t)step, wof_f.fade_start2[i],
                                                wof_f.fade_target2[i]);
            if (v->has_colours2)
                v->colours2[i] = wof_colour_lerp((int16_t)step, wof_f.fade_start3[i],
                                                 wof_f.fade_target1[i]);
        } else if (v->has_colours2) {
            v->colours2[i] = wof_colour_lerp((int16_t)step, wof_f.fade_start3[i],
                                             wof_f.fade_target1[i]);
        }
    }
}

/* The body of all four.  `target1` of 0 is the all-black table the fade_out routines
 * build on their stack; `pair` says whether the second viewport comes along. */
wof_co_t wof_fade(const uint16_t *target1, const uint16_t *target2, int pair)
{
    wof_ctx_t *c = &wof_f.co_fade;

    CO_BEGIN(c);
    fade_begin(target1, target2, pair);
    for (wof_f.fade_step = 0; wof_f.fade_step < 16; wof_f.fade_step++) {
        fade_apply(wof_f.fade_step);
        /* Each step rebuilds and installs the front view's copper list.  What survives of
         * that here is that vblank_flag is cleared, so a wait_vblank after a fade waits. */
        wof_view_show(wof_f.front_view);
        for (wof_f.fade_wait = 0; wof_f.fade_wait < fade_vblanks; wof_f.fade_wait++)
            CO_WAIT(c);
    }
    CO_END(c);
}

wof_co_t wof_fade_to(const uint16_t *target)      { return wof_fade(target, 0, 0); }
wof_co_t wof_fade_out(void)                       { return wof_fade(0, 0, 0); }
wof_co_t wof_fade_to_pair(const uint16_t *a, const uint16_t *b) { return wof_fade(a, b, 1); }
wof_co_t wof_fade_out_pair(void)                  { return wof_fade(0, 0, 1); }
