/* M7 part 2 on the page, in Chrome and in Firefox alike (tests/pagecheck.mjs,
 * tests/pagecheck_firefox.mjs): a game saved on the carrier with G and loaded after a
 * reload from the rank selection's seventh entry, the same save loaded with L in flight,
 * and a demo recorded from the overlay's key 4, played by the attract mode after a reload
 * and played again.
 *
 * The drivers hand in `d`: tap(name, ms), hold(name), release(name), sleep(ms),
 * evaluate(expression) and reload(); key names are the ones both drivers know (backquote,
 * space, enter, up, down, right, keyG, keyL, keyP, keyR, keyA, keyB, keyC, four).  What the
 * game holds is read off the overlay's player and game lines, the place a person reads it,
 * and the demo's ticks through STATE_WATCH, which the driver installs before the page's
 * own scripts run. */
import { PLAYER, STORED_FILES, startTheSound } from './pagemeasure.mjs';
import { walkToTheHold } from './pagefullscreen.mjs';

/* The campaign as the overlay's game line shows it (M7 part 2). */
export const GAME = `(() => {
    const text = document.getElementById('overlay').textContent;
    const m = text.match(/game\\s+rank (-?\\d+)\\s+mission (-?\\d+)\\s+lives (-?\\d+)\\s+score (-?\\d+)(, outside a mission)?(, a demo playing)?(, a demo recording)?/);
    const demo = (text.match(/^demo\\s+(.*)$/m) || [null, null])[1];
    return m ? { rank: +m[1], mission: +m[2], lives: +m[3], score: +m[4], inMission: !m[5],
                 playing: !!m[6], recording: !!m[7], demo } : null;
})()`;

/* The core's exports, kept when the shell instantiates them, and after every pass that ran
 * a tick the player's and the campaign's numbers, while window.__wofTicking is set: what a
 * demo does, tick by tick, without reading anything the shell does not read itself.  The
 * shell runs as it is. */
export const STATE_WATCH = `() => {
    window.__wofTicks = [];
    window.__wofTicking = false;
    const native = WebAssembly.instantiate;
    WebAssembly.instantiate = async function (...args) {
        const result = await native.apply(this, args);
        const real = result.instance && result.instance.exports;
        if (!real || typeof real.wof_pass !== 'function') {
            return result;
        }
        const exports = {};
        for (const name of Object.keys(real)) {
            exports[name] = real[name];
        }
        let last = -1;
        let wasIn = false;
        exports.wof_pass = () => {
            const out = real.wof_pass();
            const tick = real.wof_tick_count();
            const g = new Int32Array(real.memory.buffer, real.wof_dev_game(), 6);
            const nowIn = g[4] !== 0;
            if (window.__wofTicking && tick !== last) {
                const p = new Int16Array(real.memory.buffer, real.wof_dev_player(), 4);
                /* A sample taken while a mission ran: one taken in the VBlank whose pass ends
                   the setup is a recording's alone, and that pass's input_queue_clear drops
                   it again. */
                if (wasIn && nowIn) {
                    window.__wofTicks.push([p[0], p[1], p[2], p[3], g[0], g[1], g[2], g[3], g[5],
                                            real.wof_pass_count(), tick, real.wof_vblank_count()]);
                }
            }
            last = tick;
            wasIn = nowIn;
            return out;
        };
        return { module: result.module, instance: { exports } };
    };
}`;

async function until(d, test, limitMs, stepMs = 100) {
    let p = null;
    for (let waited = 0; waited < limitMs; waited += stepMs) {
        p = await d.evaluate(PLAYER);
        if (p && test(p)) {
            return p;
        }
        await d.sleep(stepMs);
    }
    return p;
}

async function game(d, test, limitMs, stepMs = 250) {
    let g = null;
    for (let waited = 0; waited < limitMs; waited += stepMs) {
        g = await d.evaluate(GAME);
        if (g && test(g)) {
            return g;
        }
        await d.sleep(stepMs);
    }
    return g;
}

/* A fresh page's first key starts the sound, which is all the help screen lets it do; the
   second opens the overlay, which the readings here come from. */
async function soundAndOverlay(d) {
    await startTheSound(() => d.tap('backquote', 50), d.evaluate, d.sleep);
    await d.tap('backquote', 50);
}

/* The title left with fire twice: the rank selection is up, its song playing. */
async function toTheRanks(d) {
    await soundAndOverlay(d);
    await d.sleep(800);
    await d.tap('space', 250);                      /* the scroller */
    await d.sleep(6600);
    await d.tap('space', 250);                      /* the title sequence */
    await d.sleep(4600);                            /* and the fade of its song */
}

/* In the hold: G, the cursor down to the dialog's empty second slot, a name, Return. */
async function saveInTheHold(d, name) {
    await d.tap('keyG', 80);
    await d.sleep(2500);
    await d.tap('down', 80);
    await d.sleep(600);
    for (const letter of name) {
        await d.tap('key' + letter.toUpperCase(), 80);
        await d.sleep(300);
    }
    await d.tap('enter', 80);
    await d.sleep(3000);
}

/* The load dialog open: Return on its first entry; the load, the fades and the briefing,
   which runs out by itself (240 rounds): a press of fire there would reach the hold's menu
   once the briefing is gone and send the lift up. */
async function loadTheFirst(d) {
    await d.tap('enter', 80);
    await game(d, (g) => !g.inMission, 10000);      /* the dialog and the briefing */
    await game(d, (g) => g.inMission, 30000);       /* the mission from the file */
    await d.sleep(2000);
}

/* The hold's menu live, the lift up, the roll along the deck and the stick forward late in
   it, as tests/pagecheck.mjs flies it; the aircraft climbing, the keys still held. */
async function takeOff(d) {
    await d.sleep(1500);
    await d.tap('space', 250);
    await until(d, (p) => p.deck === 1 && p.y > 30, 5000);
    await d.hold('right');
    const rolling = await until(d, (p) => p.deck === 1 && p.x >= 7295, 20000, 60);
    await d.hold('up');
    const air = await until(d, (p) => p.deck === 0, 10000);
    await d.sleep(1500);
    return { rolling, air };
}

async function letGo(d) {
    await d.release('up');
    await d.release('right');
}

/* A game saved on the carrier, the page reloaded, the game loaded from the rank selection's
   seventh entry.  The name `abc` lies in the directory's hash chain 7, before the disk's
   `wof.mission 3` in chain 64, so it is the dialog's first entry. */
export async function saveLoadRun(d) {
    const out = {};
    await d.evaluate("(localStorage.removeItem('wof:files'), true)");
    await d.reload();
    const walked = await walkToTheHold({ tap: d.tap, evaluate: d.evaluate }, () => d.evaluate(PLAYER), d.sleep,
                                       async () => null);
    out.hold = walked.hold;
    out.before = await d.evaluate(GAME);
    await saveInTheHold(d, 'abc');
    out.saved = await d.evaluate(GAME);
    out.savedPlayer = await d.evaluate(PLAYER);
    out.stored = (await d.evaluate(STORED_FILES)).map((f) => [f.name, f.bytes]);

    await d.reload();
    await toTheRanks(d);
    await d.tap('up', 80);                          /* the cursor from the first rank to 7 */
    await d.sleep(800);
    await d.tap('enter', 80);                       /* the load dialog */
    await d.sleep(3000);
    await loadTheFirst(d);
    out.loaded = await d.evaluate(GAME);
    out.loadedPlayer = await d.evaluate(PLAYER);
    await d.sleep(2000);
    out.later = await d.evaluate(PLAYER);
    return out;
}

/* The save of saveLoadRun loaded with L in flight, on a fresh page. */
export async function flightLoadRun(d) {
    const out = {};
    await d.reload();
    const walked = await walkToTheHold({ tap: d.tap, evaluate: d.evaluate }, () => d.evaluate(PLAYER), d.sleep,
                                       async () => null);
    out.hold = walked.hold;
    out.flight = await takeOff(d);
    await letGo(d);                                 /* in the air still: L at once */
    await d.tap('keyL', 80);
    out.beforePlayer = await d.evaluate(PLAYER);
    out.before = await d.evaluate(GAME);
    await d.sleep(3000);
    await loadTheFirst(d);
    out.loaded = await d.evaluate(GAME);
    out.loadedPlayer = await d.evaluate(PLAYER);
    return out;
}

/* A demo: key 4 arms main's argument, the first rank chosen records a take-off and a
   flight, P and R end the game, and demo_end writes wofdemo and wofdemo.seed; the ticks of
   the recording are kept.  The page reloaded, the rank selection left alone: after its
   1,800 idle rounds the attract mode plays the demo, and after the next 1,800 plays it
   again; the ticks of both playbacks are kept. */
export async function demoRun(d) {
    const out = {};
    const ticks = async (on) => {
        const got = await d.evaluate('window.__wofTicks');
        await d.evaluate('(window.__wofTicks = [], window.__wofTicking = ' + on + ', true)');
        return got;
    };
    await d.evaluate("(localStorage.removeItem('wof:files'), true)");
    await d.reload();
    await soundAndOverlay(d);
    await d.sleep(800);
    await d.tap('four', 80);                        /* main's argument on */
    await d.sleep(400);
    out.armed = await d.evaluate(GAME);
    await d.tap('space', 250);                      /* the scroller */
    await d.sleep(6600);
    await d.tap('space', 250);                      /* the title sequence */
    await d.sleep(4600);
    await ticks(true);
    await d.tap('enter', 80);                       /* the first rank: the recording begins */
    await d.sleep(5100);
    await d.tap('space', 250);                      /* the briefing */
    await until(d, (p) => p.x !== 0, 20000);
    out.recording = await d.evaluate(GAME);
    out.flight = await takeOff(d);
    await d.sleep(1500);
    await letGo(d);
    await d.sleep(1500);
    await d.tap('keyP', 80);
    await d.sleep(500);
    await d.tap('keyR', 80);                        /* the game ends: demo_end writes */
    await d.sleep(3000);
    out.recorded = await ticks(false);
    await d.tap('four', 80);                        /* main's argument off again */
    await d.sleep(400);
    out.stored = (await d.evaluate(STORED_FILES)).map((f) => [f.name, f.bytes]);

    await d.reload();
    await soundAndOverlay(d);
    await d.sleep(800);
    await d.tap('space', 250);
    await d.sleep(6600);
    await d.tap('space', 250);
    await d.sleep(4600);
    await ticks(true);
    out.firstStart = await game(d, (g) => g.playing, 90000);
    out.firstEnd = await game(d, (g) => !g.playing, 300000);  /* back at the rank selection */
    out.first = await ticks(true);
    out.secondStart = await game(d, (g) => g.playing, 90000);
    out.secondEnd = await game(d, (g) => !g.playing, 300000);
    out.second = await ticks(false);
    return out;
}
