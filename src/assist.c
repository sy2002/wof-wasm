/* The keyboard assist: the port's own layer in front of the tick's sample (SPEC 6.1, 6.2).
 *
 * This file is not a port of anything: it is policy, decided with the owner on 2026-09-22,
 * and it sits beside src/portkeys.c for the same reason that file exists.  One switch,
 * wof_set_keyboard_assist, turns on both halves below.  The core starts with it off, which
 * is the original, and every comparison with the original runs that way; the page switches
 * it on at start.
 *
 * Why.  The original samples the stick every fourth VBlank (vblank_server, re/notes/input.md)
 * and the weapon menu in the hold (0x0112B0) steps on the sampled byte: after a step it sets
 * 0x02536E to 2 and counts that down only on ticks that carry input, so one step costs three
 * samples.  A joystick is held; a key is tapped, for two to six VBlanks, so on a keyboard a
 * step takes two or three presses, and with the vertical flip on, up on the key goes down in
 * the menu.  In flight a tap shorter than four VBlanks can fall between two samples and be
 * lost altogether.  The rank menu (menu_input) polls every VBlank without the flip and waits
 * for the release, so it already behaves as a keyboard player expects and is left alone.
 *
 * The weapon menu's push.  While the menu has the stick (menu_has_stick below), a press of
 * forward or back starts a push of that direction for exactly twelve VBlanks, which is three
 * samples whatever the divider's phase: one step and the two pause counts.  The physical
 * vertical bits do not reach the sample meanwhile.  A press made while a push runs is
 * remembered, at most two, and each starts one more push when the current one ends; with
 * none remembered and the key still down, the next push starts at once, which is the
 * original's own repeat of one step every three ticks.  For its first 15 ticks the menu is
 * up but the tick does not run it (0x026D3E); a press made then is remembered the same way
 * and its push starts on the VBlank the menu becomes live, so no press is ever lost.  A key
 * already held when the menu opens does nothing until it is pressed again.  The push is not flipped: up on the key is up
 * in the menu, weapon_type decreasing.  It ends the moment the menu loses the stick, and on
 * a sample that carries the button to a live menu, which gets the stick as it is:
 * weapon_menu tests the button before it steps, so the push could not step on that tick,
 * and that tick's player update already rides the lift.  The cursor keys reach the menu a second way, through
 * last_key, so while the menu has the stick wof_port_key swallows them; otherwise a tap could
 * step twice.
 *
 * The never-lost tap.  Everywhere else, a direction that goes down arms itself, and the next
 * sample carries it whether it is still down or not, and disarms it.  So a press gives one
 * tick of stick for every sample it covers and one where it covers none: a tap shorter than
 * four VBlanks is exactly one tick, never zero, and never more than the original gives a
 * push of that length.  A press clears an armed tap of the opposite end.  The button keeps
 * the original's own latches untouched.
 *
 * What it does not touch.  The front end's pollers (wof_poll_joy_dir8, wof_poll_fire) see the
 * controller as it is; only the sample of wof_vblank sees what this file makes of it.  The
 * ported routines consult it in three marked places: wof_vblank (the watch on every VBlank,
 * and the sample), read_joy_bits (the flip, suspended for a push) and wof_port_key (the
 * cursor keys).
 */
#include "wof.h"

#define DIR_FORWARD 0x01u
#define DIR_BACK    0x02u
#define DIR_RIGHT   0x04u
#define DIR_LEFT    0x08u
#define VERTICAL    (DIR_FORWARD | DIR_BACK)
#define HORIZONTAL  (DIR_RIGHT | DIR_LEFT)

/* Three samples at one every fourth VBlank, whatever the phase: one step, two pause counts. */
#define PUSH_VBLANKS 12u
#define QUEUE_MAX    2u

#define RAW_CURSOR_UP   0x4C
#define RAW_CURSOR_DOWN 0x4D

/* The weapon menu has the stick and the cursor keys: 0x025364 set and the mission not won
 * (0x0253BC), which is what weapon_menu tests; a mission running, because the byte outlives
 * a mission left from the hold and the rank menu needs its cursor keys; and ingame_keys not
 * inside a dialog or a fade of its own, which read the keys themselves. */
static int menu_has_stick(void)
{
    return wof_g.g_025364 && !wof_g.g_0253bc
        && wof_f.co_mission.line != 0 && wof_f.co_keys.line == 0;
}

/* The tick runs the menu only once 0x026D3E has run down (logic_tick, 0x011402), which
 * player_restart_state sets to 15 every time the menu opens: at a mission's start, when the
 * lift reaches the hold and when the next aircraft comes.  The tick that takes the next
 * sample runs the menu when what is left of the count after the bytes already waiting is at
 * most 1. */
static int menu_live(void)
{
    return (int16_t)(wof_g.g_026d3e - (int16_t)wof_g.input_queue_count) <= 1;
}

static void push_start(uint16_t dir)
{
    wof_s.assist_push = dir;
    wof_s.assist_left = PUSH_VBLANKS;
}

static void push_end(void)
{
    wof_s.assist_push   = 0;
    wof_s.assist_left   = 0;
    wof_s.assist_queued = 0;
}

/* The armed taps with every axis a press went down on reduced to that press. */
static uint16_t arm(uint16_t armed, uint16_t down)
{
    if (down & VERTICAL)
        armed &= (uint16_t)~VERTICAL;
    if (down & HORIZONTAL)
        armed &= (uint16_t)~HORIZONTAL;
    return (uint16_t)(armed | down);
}

void wof_set_keyboard_assist(int on)
{
    wof_s.assist       = on ? 1u : 0u;
    wof_s.assist_armed = 0;
    push_end();
}

int wof_keyboard_assist(void)
{
    return wof_s.assist ? 1 : 0;
}

/* Every VBlank that is not paused, before the sample: the edges, the armed taps and the push.
 * wof_s.raw is the controller of this VBlank with opposing directions cancelled. */
void wof_assist_vblank(void)
{
    uint16_t now  = (uint16_t)(wof_s.raw & (VERTICAL | HORIZONTAL));
    uint16_t down = (uint16_t)(now & ~wof_s.assist_prev);
    uint16_t press;

    wof_s.assist_prev = now;
    if (!wof_s.assist)
        return;
    if (!menu_has_stick()) {
        push_end();
        wof_s.assist_armed = arm(wof_s.assist_armed, down);
        return;
    }

    /* The weapon menu: a sideways tap is armed as anywhere, forward and back are pushes. */
    wof_s.assist_armed = (uint16_t)(arm(wof_s.assist_armed, down & HORIZONTAL) & HORIZONTAL);
    press = (uint16_t)(down & VERTICAL);
    if (!menu_live()) {
        /* Up, but not run by the tick yet: a press waits for it in the queue. */
        wof_s.assist_push = 0;
        wof_s.assist_left = 0;
        if (press && wof_s.assist_queued < QUEUE_MAX)
            wof_s.assist_queue[wof_s.assist_queued++] = press;
        return;
    }
    if (wof_s.assist_push && --wof_s.assist_left == 0) {
        wof_s.assist_push = 0;
        if (!wof_s.assist_queued && (now & VERTICAL) && !press)
            push_start((uint16_t)(now & VERTICAL));         /* still down: the repeat */
    }
    if (!wof_s.assist_push && wof_s.assist_queued) {
        push_start(wof_s.assist_queue[0]);
        wof_s.assist_queue[0] = wof_s.assist_queue[1];
        wof_s.assist_queued--;
    }
    if (press) {
        if (!wof_s.assist_push)
            push_start(press);
        else if (wof_s.assist_queued < QUEUE_MAX)
            wof_s.assist_queue[wof_s.assist_queued++] = press;
    }
}

/* What the sample of this VBlank sees instead of the controller: the armed taps added, and in
 * the weapon menu the push in place of forward and back, marked so that read_joy_bits does
 * not flip it.  The armed taps are spent.  The identity while the assist is off. */
uint16_t wof_assist_sample(uint16_t physical)
{
    uint16_t out;

    if (!wof_s.assist)
        return physical;
    out = (uint16_t)(physical | wof_s.assist_armed);
    wof_s.assist_armed = 0;
    /* A stick cannot report both ends of an axis; the end held now wins over an armed one. */
    if ((out & VERTICAL) == VERTICAL)
        out = (uint16_t)((out & ~VERTICAL) | (physical & VERTICAL));
    if ((out & HORIZONTAL) == HORIZONTAL)
        out = (uint16_t)((out & ~HORIZONTAL) | (physical & HORIZONTAL));
    if (!menu_has_stick())
        return out;
    if ((wof_g.fire_tap_latch || wof_g.fire_hold_latch) && menu_live()) {
        push_end();                    /* this byte carries the button and closes the menu */
        return out;
    }
    out &= (uint16_t)~VERTICAL;
    if (wof_s.assist_push)
        out |= (uint16_t)(wof_s.assist_push | WOF_RAW_UNFLIPPED);
    return out;
}

/* The cursor keys, while the weapon menu has the stick. */
int wof_assist_swallows(uint8_t code)
{
    return wof_s.assist && (code == RAW_CURSOR_UP || code == RAW_CURSOR_DOWN) && menu_has_stick();
}
