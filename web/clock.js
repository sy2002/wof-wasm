/* The clock (SPEC 6.2): a fixed-rate accumulator on requestAnimationFrame.
 *
 * Emulated time, not display time, is what counts.  The accumulator issues one wof_vblank
 * per 1/50 second of emulated time on PAL, 1/60 on NTSC, and one wof_pass after each of
 * them, because the original's inner loop runs one pass per displayed frame and the display
 * is the VBlank.  A 144 Hz monitor therefore still gets 50 passes a second on PAL, and a
 * 30 Hz one still gets 50, two per animation frame.
 *
 * The rate is one half of the video standard, which the shell sets as a whole; the other
 * half is the pixel aspect in web/video.js.
 *
 * After a stall at most 24 VBlanks are replayed.  That is the original's own limit seen
 * from the outside: the input queue holds 6 entries, each worth four VBlanks, and anything
 * older than that would have been dropped on the machine as well. */

const MAX_CATCHUP = 24;

export function createClock(core, input, video, audio, onFrame) {
    /* PAL, like the shell's default video standard.  The core starts at 60 (SPEC 6.1) and
       is told otherwise on the setHz call the shell makes before the clock ever runs. */
    let hz = 50;
    let period = 1000 / hz;
    let accumulator = 0;
    let last = -1;
    let handle = 0;
    let animationFrames = 0;
    let stalls = 0;

    let windowStart = 0;
    let windowMark = null;
    const rate = { vblank: 0, tick: 0, pass: 0, animation: 0, perTick: 0, tickExact: false };

    function measure(now) {
        const counters = core.counters();
        if (windowMark === null) {
            windowStart = now;
            windowMark = counters;
            animationFrames = 0;
            return;
        }
        const seconds = (now - windowStart) / 1000;
        if (seconds < 1) {
            return;
        }
        rate.vblank = (counters.vblanks - windowMark.vblanks) / seconds;
        rate.tick = (counters.ticks - windowMark.ticks) / seconds;
        rate.pass = (counters.passes - windowMark.passes) / seconds;
        rate.animation = animationFrames / seconds;
        /* Counted rates of something that happens 15 times a second are a whole number
           either way; the cumulative ratio is the exact statement and must stay at 4. */
        rate.perTick = counters.ticks ? counters.vblanks / counters.ticks : 0;
        rate.tickExact = counters.ticks === Math.floor(counters.vblanks / 4);
        windowStart = now;
        windowMark = counters;
        animationFrames = 0;
    }

    function frame(now) {
        handle = requestAnimationFrame(frame);
        animationFrames++;

        if (last < 0) {
            last = now;
            measure(now);
            return;
        }

        let elapsed = now - last;
        last = now;
        if (elapsed < 0) {
            elapsed = 0;
        }

        accumulator += elapsed;
        if (accumulator > MAX_CATCHUP * period) {
            accumulator = MAX_CATCHUP * period;
            stalls++;
        }

        let issued = 0;
        while (accumulator >= period) {
            core.vblank(input.consume());
            core.pass();
            accumulator -= period;
            issued++;
        }

        if (issued) {
            video.present();
        }
        audio.pump();
        measure(now);
        if (onFrame) {
            onFrame(now);
        }
    }

    return {
        start() {
            if (handle) {
                return;
            }
            last = -1;
            accumulator = 0;
            windowMark = null;
            handle = requestAnimationFrame(frame);
        },
        stop() {
            if (handle) {
                cancelAnimationFrame(handle);
                handle = 0;
            }
        },
        running: () => handle !== 0,
        hz: () => hz,
        setHz(value) {
            hz = value === 50 ? 50 : 60;
            period = 1000 / hz;
            accumulator = 0;
            core.setVideoHz(hz);
        },
        stats: () => ({ rate, hz, stalls, backlog: accumulator / period }),
    };
}
