/* Input sampling: the raw controller state of one VBlank becomes the input byte of one
 * logic tick (re/notes/input.md, SPEC 6.1).
 *
 * On the machine the chain is JOY1DAT and CIA-A PRA -> read_joy_bits and read_fire_button
 * -> vblank_every_frame's tap and hold latches -> read_joystick's input byte ->
 * vblank_server's six-entry queue -> one logic tick per entry.  The port is handed the five
 * bits directly, so JOY1DAT and the gray-code table it is decoded with fall away; everything
 * after that is the original's own arithmetic, because it is evaluated at VBlank rate while
 * sampling happens every fourth VBlank and the latches live between samples.
 *
 * wof_s.raw is the port's stand-in for the two hardware registers: the five bits of the
 * current VBlank with opposing directions already cancelled, which is what a real stick can
 * produce and what the headless original's script is turned into before it writes JOY1DAT.
 */
#include "wof.h"
#include "gen/tables.h"

#define RAW_FORWARD 0x01u
#define RAW_BACK    0x02u
#define RAW_RIGHT   0x04u
#define RAW_LEFT    0x08u
#define RAW_FIRE    0x10u

/* Every 4th VBlank makes one input sample, which is one logic tick: 15 Hz on a 60 Hz
 * machine, 12.5 Hz on a 50 Hz one.  The program never asks which it is running on
 * (re/notes/random.md). */
#define VBLANKS_PER_TICK 4

void wof_input_init(void)
{
    wof_g.vblank_counter    = 0;
    wof_g.vblank_total      = 0;
    wof_g.fire_press_frame  = 0;
    wof_g.fire_prev_state   = 0;
    wof_g.fire_tap_latch    = 0;
    wof_g.fire_hold_latch   = 0;
    wof_g.fire_state        = 0;
    wof_g.joy_dir8          = 0;
    wof_g.input_byte        = 0;
    wof_g.input_queue_count = 0;
    wof_g.tick_input        = 0;
    wof_g.demo_mode         = 0;
    wof_g.vblank_divider    = 0;    /* zero-filled DATA: the very first VBlank samples */
    wof_g.vblank_flag       = 0;
    wof_g.pause_flag        = 0;
    for (int i = 0; i < 6; i++)
        wof_g.input_queue[i] = 0;
}

/* orig 0x02046A read_fire_button - the button of either port, active low on CIA-A PRA.
 * The port has one button. */
static int read_fire_button(void)
{
    return (wof_s.raw & RAW_FIRE) ? 1 : 0;
}

/* orig 0x01520E read_joy_bits - b0 forward, b1 back, b2 left, b3 right, and the vertical
 * flip applied only when one of the two vertical bits is set, because eori #3 on a centred
 * stick would produce up and down at once.  Port policy, not the original: a push of the
 * keyboard assist in the weapon menu is not flipped (WOF_RAW_UNFLIPPED, src/assist.c). */
uint16_t wof_read_joy_bits(void)
{
    uint16_t bits = 0;

    if (wof_s.raw & RAW_FORWARD) bits |= 0x1u;
    if (wof_s.raw & RAW_BACK)    bits |= 0x2u;
    if (wof_s.raw & RAW_LEFT)    bits |= 0x4u;
    if (wof_s.raw & RAW_RIGHT)   bits |= 0x8u;

    if ((bits & 0x3u) && wof_g.opt_invert_vertical && !(wof_s.raw & WOF_RAW_UNFLIPPED))
        bits ^= 0x3u;
    return bits;
}

/* orig 0x020488 read_joy_dir8 - 0 centre, then clockwise from 1, which is the stick pushed
 * forward: 2 up-right, 3 right, 4 down-right, 5 down, 6 down-left, 7 left, 8 up-left.  The
 * routine reads the hardware, so it does not see the vertical flip. */
static int read_joy_dir8(void)
{
    int up    = (wof_s.raw & RAW_FORWARD) != 0;
    int down  = (wof_s.raw & RAW_BACK) != 0;
    int right = (wof_s.raw & RAW_RIGHT) != 0;
    int left  = (wof_s.raw & RAW_LEFT) != 0;

    if (up)    return right ? 2 : left ? 8 : 1;
    if (down)  return right ? 4 : left ? 6 : 5;
    if (right) return 3;
    if (left)  return 7;
    return 0;
}

/* orig 0x02044C and 0x020454 - the two pollers the front end uses. */
int wof_poll_fire(void)
{
    wof_g.fire_state = (uint16_t)read_fire_button();
    return wof_g.fire_state;
}

int wof_poll_joy_dir8(void)
{
    wof_g.joy_dir8 = (uint16_t)read_joy_dir8();
    return wof_g.joy_dir8;
}

/* orig 0x01C9CA vblank_every_frame - the fire button's edge timing.  The threshold is ten
 * VBlanks, not ten ticks, and the latches persist between samples, so a tap that begins and
 * ends between two samples is still delivered. */
static void vblank_every_frame(void)
{
    wof_g.vblank_counter++;

    int fire = wof_poll_fire();

    if (fire && !wof_g.fire_prev_state)
        wof_g.fire_press_frame = wof_g.vblank_counter;

    if ((int32_t)wof_g.vblank_counter < (int32_t)(wof_g.fire_press_frame + 10)) {
        if (!fire && wof_g.fire_prev_state)
            wof_g.fire_tap_latch = 1;
    } else if (fire) {
        wof_g.fire_hold_latch = 1;
    }

    if (!fire)
        wof_g.fire_press_frame = 0;
    wof_g.fire_prev_state = (uint16_t)fire;
}

/* orig 0x01CA32 read_joystick - the input byte of one tick.  A tap wins: it sets bit 5 and
 * clears both latches, so one sample never reports tap and hold together.  The left and
 * right bits swap on the way in: read_joy_bits uses b2 for left, the input byte b3.  D0 is
 * left as read_joy_bits returned it, which vblank_server's recording half stores. */
static uint16_t read_joystick(void)
{
    uint16_t bits = wof_read_joy_bits();
    uint8_t  byte = 0;

    if (wof_g.fire_tap_latch) {
        byte |= 0x20u;
        wof_g.fire_tap_latch  = 0;
        wof_g.fire_hold_latch = 0;
    }
    if (wof_g.fire_hold_latch) {
        byte |= 0x10u;
        wof_g.fire_hold_latch = 0;
    }
    if (bits & 0x1u) byte |= 0x01u;
    if (bits & 0x2u) byte |= 0x02u;
    if (bits & 0x4u) byte |= 0x08u;
    if (bits & 0x8u) byte |= 0x04u;

    wof_g.input_byte = byte;
    return bits;
}

/* The demo buffer's byte at `index`: demo_buffer_ptr + index.  A buffer freed between two
 * missions (free_mission_assets, 0x01124C) leaves the pointer 0 and the original reading and
 * writing the machine's memory from address 0; the port reads 0 there and drops the write
 * (re/notes/demo.md). */
static uint8_t demo_byte(uint16_t index)
{
    return wof_f.demo_buffer_set && index < WOF_DEMO_BYTES ? wof_m.demo_buffer[index].v : 0;
}

static void demo_store(uint16_t index, uint8_t value)
{
    if (wof_f.demo_buffer_set && index < WOF_DEMO_BYTES)
        wof_m.demo_buffer[index].v = value;
}

/* orig 0x011714 input_queue_pop - queue[0], then the queue shifts down.  The dbra runs as
 * many rounds as the new count, so the last live entry is copied and the slot it came from
 * is left stale, which is what the count makes invisible. */
uint16_t wof_input_queue_pop(void)
{
    uint16_t value = wof_g.input_queue[0];
    int16_t  count = (int16_t)(wof_g.input_queue_count - 1);

    if (count < 0)
        count = 0;
    wof_g.input_queue_count = (uint16_t)count;
    for (int16_t i = 0; i < count; i++)
        wof_g.input_queue[i] = wof_g.input_queue[i + 1];
    return value;
}

/* orig 0x01174A input_queue_clear. */
void wof_input_queue_clear(void)
{
    wof_g.input_queue_count = 0;
    wof_g.input_queue[0]    = 0;
}

/* orig 0x011842 to 0x01195C - vblank_server's mission half: nothing outside a mission; in
 * one, 0x025410 counts VBlanks, and the ticker scrolls its plane one pixel left on every
 * VBlank while 0x0255C8 says a message is running, taking the next character of the
 * message into the hidden column at byte 80 whenever the last one has scrolled its width
 * (re/notes/display.md).  No script of M4 runs a message; the scroll and the glyph copy are
 * ported from reading and held to the original under the oracle (tests/test_oracle_m4.py). */
void wof_vblank_ticker(void)
{
    uint8_t *plane = wof_f.vram + wof_f.ticker_base;

    if (wof_g.outside_mission)
        return;
    wof_g.g_025410++;
    if (wof_g.g_0255c8) {
        for (uint32_t r = 0; r < WOF_TICKER_H; r++) {
            uint8_t *row = plane + r * 672u;

            for (uint32_t x = 0; x + 1 < 672u; x++)
                row[x] = row[x + 1];
            row[671] = 0;
        }
        wof_g.g_0255c8--;
        if (wof_g.g_0255e0) {
            if (--wof_g.g_0255e0)
                return;
        }
    }
    if (!wof_g.ticker_message)
        return;
    {
        uint8_t ch = wof_ticker_char(wof_g.ticker_message);
        uint8_t index, width;

        wof_g.ticker_message++;
        if (ch == 0) {
            wof_g.ticker_message = 0;
            wof_g.g_0255e0 = 0;
            return;
        }
        wof_g.g_0255c8 = 0x2A0;
        index = (uint8_t)(ch - wof_font_first());
        width = wof_font_width_byte(index);
        if (width == 0) {
            wof_g.g_0255e0 = 10;
            return;
        }
        wof_g.g_0255e0 = (uint16_t)(width + 1);
        {
            uint16_t words = (uint16_t)((width + 15u) >> 4);
            uint32_t at    = 0;

            for (uint32_t r = 0; r < wof_font_height(); r++) {
                uint8_t *dst = plane + r * 672u + 640u;

                for (uint16_t w = 0; w < words; w++, at += 2) {
                    uint16_t bits = wof_font_glyph_word(index, at);

                    for (int b = 0; b < 16 && 640u + w * 16u + (uint32_t)b < 672u; b++)
                        dst[w * 16 + b] = (uint8_t)((bits >> (15 - b)) & 1u);
                }
            }
        }
    }
}

/* orig 0x011754 vblank_server, together with 0x01C9CA vblank_every_frame (SPEC 6.1).
 *
 * What is here is the input half: the flag the waits spin on, the pause gate, the divider,
 * the sample and the six-entry queue.  The ticker scroll of the second half is per-pass
 * drawing on the play screen and arrives with M4; the flag that gates it, the byte at
 * 0x02464E, is non-zero outside a mission, which is the whole of M3.  The word at 0x027364,
 * which would skip the sampling altogether, is tested here and written nowhere in the
 * executable, so it is left out.  Demo playback and recording are the two branches around
 * the sample (M7 part 2, re/notes/demo.md).
 */
void wof_vblank(uint8_t raw)
{
    uint8_t state = (uint8_t)(raw & 0x1Fu);

    /* A real stick cannot report both ends of an axis; the core cancels them (SPEC 6.1). */
    if ((state & (RAW_FORWARD | RAW_BACK)) == (RAW_FORWARD | RAW_BACK))
        state &= (uint8_t)~(RAW_FORWARD | RAW_BACK);
    if ((state & (RAW_LEFT | RAW_RIGHT)) == (RAW_LEFT | RAW_RIGHT))
        state &= (uint8_t)~(RAW_LEFT | RAW_RIGHT);

    /* The audio channels' events of the VBlank that has passed, then the servers in the order
     * of their priorities: soundfx_vblank (30) once sound_init has added it, with the start
     * interrupts it raises delivered when it returns, then vblank_server (-10), which is the
     * rest of this function (src/audio.c, re/notes/sound.md). */
    wof_paula_boundary();
    if (wof_g.sound_installed) {
        wof_paula_server(1);
        wof_soundfx_vblank();
        wof_paula_server(0);
        wof_paula_deliver();
    }

    wof_s.raw = state;
    wof_s.vblanks++;
    wof_s.since_pass++;
    wof_g.vblank_flag = 0xFF;

    if (wof_g.pause_flag)
        return;

    wof_g.vblank_total++;
    vblank_every_frame();
    wof_assist_vblank();                /* port policy: the keyboard assist watches (src/assist.c) */

    if ((int16_t)--wof_g.vblank_divider > 0) {
        wof_vblank_ticker();
        return;
    }
    wof_g.vblank_divider = VBLANKS_PER_TICK;

    uint16_t d0;                        /* what the original's D0 holds on the way */

    if (wof_g.demo_mode == 1) {
        /* 0x011790: a playback takes the byte from the demo, and only while step S has set
         * 0x026D54 and run_queued_ticks' count 0x026D44 still wants one: nothing is queued
         * otherwise.  A 0xFF byte ends the playback and is queued itself; so is the entry
         * that brings the index to 0x1386. */
        uint16_t d1;

        if (!wof_g.demo_step_s || !wof_g.demo_bytes_owed) {
            wof_vblank_ticker();
            return;
        }
        wof_g.demo_bytes_owed--;
        d1 = wof_g.demo_index;
        d0 = demo_byte(d1);
        if (d0 == 0xFFu) {
            wof_g.quit_flag = 0xFF;
        } else {
            d1++;
            wof_g.demo_index = d1;
            if (d1 >= WOF_DEMO_ENTRIES)
                wof_g.quit_flag = 0xFF;
        }
        wof_g.input_byte = d0;
    } else {
        /* Port policy, not the original: the sample sees what the keyboard assist makes of
         * the VBlanks since the previous one, and everything else keeps seeing the
         * controller as it is (src/assist.c).  While the assist is off it is the identity. */
        uint16_t physical = wof_s.raw;

        wof_s.raw = wof_assist_sample(physical);
        d0 = read_joystick();
        wof_s.raw = physical;
    }

    uint16_t count = wof_g.input_queue_count;

    if (count < 6)
        count++;
    else
        d0 = wof_input_queue_pop();     /* the oldest entry goes, into D0 */
    wof_g.input_queue_count  = count;
    wof_g.input_queue[count - 1] = wof_g.input_byte;

    if (wof_g.demo_mode == 2 && wof_g.demo_step_s && wof_g.demo_bytes_owed) {
        /* 0x011800: a recording keeps the sample's low byte while run_queued_ticks' count
         * wants one, and ends at entry 0x1386; then input_byte takes what D0 holds, which is
         * read_joy_bits' result or, when the queue was full, the entry it dropped. */
        wof_g.demo_bytes_owed--;
        demo_store(wof_g.demo_index, (uint8_t)wof_g.input_byte);
        wof_g.demo_index++;
        if (wof_g.demo_index >= WOF_DEMO_ENTRIES)
            wof_g.quit_flag = 0xFF;
        wof_g.input_byte = d0;
    }

    /* The count of samples taken, which is the rate one logic tick per queued byte runs
     * at: wof_tick_count.  The ticks the inner loop runs are counted in wof_f.ticks_run. */
    wof_s.ticks++;
    wof_vblank_ticker();
}

/* A byte of a ticker message.  The original keeps the message pointer at 0x0257B6; the
 * port keeps the same address and reads the byte from the registered global that holds it,
 * or from the executable's initialised DATA hunk for a constant text (re/tables.toml,
 * data_image).  Its writers point it at ticker_text (0x02716A: mission_won 0x0156FC, and
 * ticker_offer 0x015562 from ticker_say, ship_sinking and the cheat's memory line) or at
 * ticker_text_2 (0x027E00: the version and Help lines), both registered, and the server
 * steps it to the text's NUL (0x0118E2).  No text reaches past them: ticker_text holds a
 * message formatted from its start, at most 95 characters (the cheat's memory line; an
 * island's bonus 83, a ship sunk 59), and mission_won appends at most 125 to an island's or
 * a ship's, 220 bytes with the NUL in its 300; ticker_text_2's lines are at most 50 of 102
 * (re/notes/porting-m7.md, "Part 2: the port").  So the last answer, 0, is never given. */
uint8_t wof_ticker_char(uint32_t addr)
{
    uint8_t b;

    if (wof_global_byte(addr, &b))
        return b;
    if (addr >= 0x023000u && addr - 0x023000u < sizeof wof_tbl_data_image)
        return wof_tbl_data_image[addr - 0x023000u];
    return 0;
}
