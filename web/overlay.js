/* The diagnostics overlay.  It exists so that the M0 acceptance criteria - a steady
   emulated 60 Hz, the tick rate, the input bits, sound actually flowing - can be read off
   the page instead of guessed at.  The backtick key toggles it. */

const BIT_NAMES = ['down', 'up', 'right', 'left', 'fire'];

export function createOverlay(element, core, clock, audio, input) {
    let visible = false;
    let lastPaint = 0;

    function bits() {
        const raw = input.raw();
        let text = '';
        for (let b = 0; b < 5; b++) {
            text += ((raw >> b) & 1 ? BIT_NAMES[b].toUpperCase() : BIT_NAMES[b]) + ' ';
        }
        return raw.toString(2).padStart(5, '0') + '  ' + text.trim();
    }

    function paint(now) {
        if (!visible || now - lastPaint < 200) {
            return;
        }
        lastPaint = now;

        const c = core.counters();
        const s = clock.stats();
        const a = audio.stats();
        const expectedTick = s.hz / 4;

        element.innerHTML =
            '<b>Wings of Fury - M1 diagnostics</b>\n' +
            'clock        ' + s.hz + ' Hz emulated, ' + (s.backlog).toFixed(2) + ' vbl backlog\n' +
            'vblanks/s    ' + s.rate.vblank.toFixed(2) + '   (want ' + s.hz + ')\n' +
            'ticks/s      ' + s.rate.tick.toFixed(2) + '   (want ' + expectedTick + ')\n' +
            'vbl per tick ' + s.rate.perTick.toFixed(2) + '   (exactly 4: ' +
                (s.rate.tickExact ? 'yes' : 'NO') + ')\n' +
            'passes/s     ' + s.rate.pass.toFixed(2) + '   (want ' + s.hz + ')\n' +
            'animation/s  ' + s.rate.animation.toFixed(1) + '   stalls ' + s.stalls + '\n' +
            'counters     ' + c.vblanks + ' vbl  ' + c.ticks + ' tick  ' + c.passes + ' pass\n' +
            'input        ' + bits() + '\n' +
            'audio        ' + a.backend + ', ' + a.state + ', ' + Math.round(a.rate) + ' Hz\n' +
            'buffer       ' + a.queuedMs.toFixed(0) + ' ms queued, ' + a.underruns + ' underruns\n' +
            (a.note ? 'note         ' + a.note.slice(0, 48) + '\n' : '') +
            'core         ' + core.width + 'x' + core.height + ', ' + core.paletteCount +
                ' palettes, ' + c.files + ' files\n' +
            'assets       ' + (c.assetsReady ? 'loaded' : 'INCOMPLETE') + '\n' +
            'arena        ' + (c.arenaUsed / 1024).toFixed(0) + ' of ' +
                (c.arenaSize / 1024).toFixed(0) + ' KiB';
    }

    function toggle() {
        visible = !visible;
        element.classList.toggle('off', !visible);
        lastPaint = 0;
    }

    element.classList.add('off');
    return {
        paint,
        toggle,
        attach(value) { clock = value; },
        visible: () => visible,
    };
}
