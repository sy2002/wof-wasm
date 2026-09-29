/* Video: indexed pixels from the core through the per-row palettes to RGBA (SPEC 6.4), and
 * the scaling that puts them on the page in the machine's proportions (SPEC 6.2).
 *
 * The palette is applied here, at presentation, and it is looked up per row, because the
 * original changes colours part-way down the screen and cycles them.  Nothing about the
 * picture is cached between frames for that reason: both the palettes and the row table
 * may have changed since the last pass.
 *
 * A framebuffer pixel is not square on either machine, so no single whole-number factor can
 * fill the window.  The picture is enlarged by the whole numbers kx and ky with nearest
 * neighbour, so that every framebuffer pixel is a block of exactly equal size, and that
 * enlargement is reduced smoothly to the box, which is the one step that may fall between
 * pixels, and it falls between blocks that are already large.  Two renderers do this:
 *
 *   webgl    one pass on the GPU (below, FRAGMENT): the framebuffer, the palettes and the row
 *            table go up as textures, and every output pixel is worked out from the
 *            enlargement's texels without the enlargement ever being made.  A Retina
 *            fullscreen is over eight million pixels a frame, which the 2D path draws on the
 *            main thread wherever the browser's 2D canvas is software (Firefox's is: 32 ms a
 *            frame there, half the frame rate; re/notes/page-video.md).
 *   2d       three canvases: the 640 x 214 source that putImageData writes, the enlargement,
 *            and the displayed canvas it is reduced onto.  The fallback where WebGL is
 *            refused or lost, and what ?video=2d asks for.
 */

/* The display box for one 640 x 214 framebuffer, and the VBlank rate, per video standard
 * (SPEC 6.2).  The two belong together: a machine has one of them, not either.
 *
 * On PAL a low-resolution pixel is 16/15 as wide as it is tall, so a framebuffer pixel,
 * which is a high-resolution one, is 8/15 and 640 x 214 is shown as 1024 : 642.  On NTSC,
 * where 320 x 200 fills a 4:3 screen, a low-resolution pixel is 5/6 and the box is 800 : 642.
 * PAL is the default: this disk comes from a PAL region and the machine the port is compared
 * against is a PAL machine. */
export const STANDARDS = {
    pal: { name: 'PAL', hz: 50, boxWidth: 1024, boxHeight: 642 },
    ntsc: { name: 'NTSC', hz: 60, boxWidth: 800, boxHeight: 642 },
};

/* The pause sign's big line as a share of the picture's height, and its smallest size. */
const SIGN_SHARE = 0.06;
const SIGN_MIN_PX = 16;

/* The help screen's text as a share of the picture's height, its smallest size before it is
   fitted, and how much of the picture's width and height its sheet may take: a narrow or
   small picture - NTSC's, or a small window's - takes the size down until the widest line
   and the last one fit, so a small window gets the largest text that fits it. */
const HELP_SHARE = 0.036;
const HELP_MIN_PX = 13;
const HELP_FILL = 0.92;

/* How long a lost WebGL context is given to come back before the page draws with the 2D
   renderer instead.  A browser restores a context within a frame or two when it can. */
const RESTORE_WAIT_MS = 2000;

/* The frame and present times the diagnostics overlay shows are averaged over this long. */
const STATS_WINDOW_MS = 1000;

/* The whole picture is one quad over the canvas. */
const VERTEX = `
attribute vec2 corner;
void main() {
    gl_Position = vec4(corner, 0.0, 1.0);
}`;

/* One output pixel.  Its centre is taken into the enlargement, 640 kx by 214 ky texels, as
   a smooth reduction samples it, and filtered bilinearly from the four texels round it, as
   that reduction does; a texel is the framebuffer pixel whose block it lies in, read through
   the palette of that pixel's own row.  So the colours are blended, never the indices, and
   across a row boundary each side keeps its own row's palette.  Where the four texels lie in
   one block, which is nearly everywhere, there is nothing to blend and one lookup is made.
   Every coordinate is a whole number held in a float, so floor() is given a half to spare
   against a division that comes out a hair below the integer. */
const FRAGMENT = `
precision highp float;
uniform sampler2D pixels;
uniform sampler2D rows;
uniform sampler2D palettes;
uniform vec2 box;
uniform vec2 enlarged;
uniform vec2 factor;
uniform vec2 source;
uniform vec2 palette;

vec4 colour(vec2 p) {
    float index = floor(texture2D(pixels, (p + 0.5) / source).r * 255.0 + 0.5);
    float row = floor(texture2D(rows, vec2((p.y + 0.5) / source.y, 0.5)).r * 255.0 + 0.5);
    float entry = row * palette.x + index;
    float line = floor((entry + 0.5) / palette.x);
    return texture2D(palettes, (vec2(entry - line * palette.x, line) + 0.5) / palette);
}

void main() {
    vec2 at = vec2(gl_FragCoord.x, box.y - gl_FragCoord.y);
    vec2 texel = at * enlarged / box - 0.5;
    vec2 first = clamp(floor(texel), vec2(0.0), enlarged - 1.0);
    vec2 second = min(first + 1.0, enlarged - 1.0);
    vec2 blend = clamp(texel - first, 0.0, 1.0);
    vec2 p0 = floor((first + 0.5) / factor);
    vec2 p1 = floor((second + 0.5) / factor);

    vec4 c = colour(p0);
    if (p1.x != p0.x) {
        c = mix(c, colour(vec2(p1.x, p0.y)), blend.x);
    }
    if (p1.y != p0.y) {
        vec4 below = colour(vec2(p0.x, p1.y));
        if (p1.x != p0.x) {
            below = mix(below, colour(p1), blend.x);
        }
        c = mix(c, below, blend.y);
    }
    gl_FragColor = vec4(c.rgb, 1.0);
}`;

/* The framebuffer through the palette of each row, as RGBA words in the byte order of an
   ImageData, which is the order the core keeps its palette words in. */
function convert(core, out) {
    const fb = core.framebuffer();
    const rows = core.paletteRows();
    const pal = core.palettes();
    const colours = core.paletteColours;
    for (let y = 0, i = 0; y < core.height; y++) {
        const base = rows[y] * colours;
        for (let x = 0; x < core.width; x++, i++) {
            out[i] = pal[base + fb[i]];
        }
    }
}

/* The WebGL renderer, or null where the browser refuses a context or the shader, in which
   case the canvas is left for the caller to replace: a canvas that has handed out a WebGL
   context never gives a 2D one. */
function createGlRenderer(canvas, core, onLost, onRestored) {
    /* failIfMajorPerformanceCaveat: a WebGL that the browser runs in software (SwiftShader,
       where the GPU is blocked) takes four times as long a frame as the 2D path does there,
       so it is refused and the 2D path taken instead (re/notes/page-video.md). */
    const options = { alpha: false, antialias: false, depth: false, stencil: false,
                      premultipliedAlpha: false, preserveDrawingBuffer: false,
                      failIfMajorPerformanceCaveat: true };
    const gl = canvas.getContext('webgl', options);
    if (!gl) {
        return { renderer: null, why: 'WebGL refused, or only in software', taken: false };
    }
    /* Positions up to 3840 texels have to be exact in the shader; a mediump float is not. */
    const high = gl.getShaderPrecisionFormat(gl.FRAGMENT_SHADER, gl.HIGH_FLOAT);
    if (!high || high.precision < 23) {
        return { renderer: null, why: 'no highp float in the fragment shader', taken: true };
    }

    const w = core.width;
    const h = core.height;
    const count = core.paletteCount;
    const colours = core.paletteColours;
    const rowBytes = new Uint8Array(h);
    const rowsSeen = new Uint8Array(h);
    const paletteSeen = new Uint32Array(count * colours);
    let everything = true;
    let program = null;
    let uniforms = null;
    let lost = false;
    let size = { width: 1, height: 1, kx: 1, ky: 1 };

    function compile(type, text) {
        const shader = gl.createShader(type);
        gl.shaderSource(shader, text);
        gl.compileShader(shader);
        if (!gl.getShaderParameter(shader, gl.COMPILE_STATUS) && !gl.isContextLost()) {
            throw new Error('shader: ' + gl.getShaderInfoLog(shader));
        }
        return shader;
    }

    function texture(unit, format, width, height) {
        const t = gl.createTexture();
        gl.activeTexture(gl.TEXTURE0 + unit);
        gl.bindTexture(gl.TEXTURE_2D, t);
        gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MIN_FILTER, gl.NEAREST);
        gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MAG_FILTER, gl.NEAREST);
        gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_S, gl.CLAMP_TO_EDGE);
        gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_T, gl.CLAMP_TO_EDGE);
        gl.texImage2D(gl.TEXTURE_2D, 0, format, width, height, 0, format, gl.UNSIGNED_BYTE, null);
        return t;
    }

    /* Everything a context holds, made again after a restore.  The three textures stay
       bound to units 0, 1 and 2 for the context's life. */
    function setUp() {
        program = gl.createProgram();
        gl.attachShader(program, compile(gl.VERTEX_SHADER, VERTEX));
        gl.attachShader(program, compile(gl.FRAGMENT_SHADER, FRAGMENT));
        gl.linkProgram(program);
        if (!gl.getProgramParameter(program, gl.LINK_STATUS) && !gl.isContextLost()) {
            throw new Error('program: ' + gl.getProgramInfoLog(program));
        }
        gl.useProgram(program);

        gl.bindBuffer(gl.ARRAY_BUFFER, gl.createBuffer());
        gl.bufferData(gl.ARRAY_BUFFER, new Float32Array([-1, -1, 1, -1, -1, 1, 1, 1]),
                      gl.STATIC_DRAW);
        const corner = gl.getAttribLocation(program, 'corner');
        gl.enableVertexAttribArray(corner);
        gl.vertexAttribPointer(corner, 2, gl.FLOAT, false, 0, 0);

        gl.pixelStorei(gl.UNPACK_ALIGNMENT, 1);
        gl.pixelStorei(gl.UNPACK_FLIP_Y_WEBGL, false);
        gl.pixelStorei(gl.UNPACK_PREMULTIPLY_ALPHA_WEBGL, false);
        texture(0, gl.LUMINANCE, w, h);
        texture(1, gl.LUMINANCE, h, 1);
        texture(2, gl.RGBA, colours, count);

        uniforms = {};
        for (const name of ['pixels', 'rows', 'palettes', 'box', 'enlarged', 'factor', 'source',
                            'palette']) {
            uniforms[name] = gl.getUniformLocation(program, name);
        }
        gl.uniform1i(uniforms.pixels, 0);
        gl.uniform1i(uniforms.rows, 1);
        gl.uniform1i(uniforms.palettes, 2);
        gl.uniform2f(uniforms.source, w, h);
        gl.uniform2f(uniforms.palette, colours, count);

        /* Nothing is on the GPU yet: this upload sends all of it. */
        everything = true;
        upload();
        resize(size);
    }

    /* The framebuffer every time; the row table and the palettes when they have changed,
       which the core does at a fade step, the split line's move and the like. */
    function upload() {
        gl.activeTexture(gl.TEXTURE0);
        gl.texSubImage2D(gl.TEXTURE_2D, 0, 0, 0, w, h, gl.LUMINANCE, gl.UNSIGNED_BYTE,
                         core.framebuffer());

        const rows = core.paletteRows();
        let rowsChanged = everything;
        for (let y = 0; y < h; y++) {
            rowBytes[y] = rows[y];
            if (rowBytes[y] !== rowsSeen[y]) {
                rowsChanged = true;
            }
        }
        if (rowsChanged) {
            rowsSeen.set(rowBytes);
            gl.activeTexture(gl.TEXTURE1);
            gl.texSubImage2D(gl.TEXTURE_2D, 0, 0, 0, h, 1, gl.LUMINANCE, gl.UNSIGNED_BYTE,
                             rowBytes);
        }

        const pal = core.palettes();
        let paletteChanged = everything;
        for (let i = 0; i < pal.length && !paletteChanged; i++) {
            paletteChanged = pal[i] !== paletteSeen[i];
        }
        if (paletteChanged) {
            paletteSeen.set(pal);
            gl.activeTexture(gl.TEXTURE2);
            gl.texSubImage2D(gl.TEXTURE_2D, 0, 0, 0, colours, count, gl.RGBA, gl.UNSIGNED_BYTE,
                             new Uint8Array(pal.buffer, pal.byteOffset, pal.byteLength));
        }
        everything = false;
    }

    function resize(next) {
        size = next;
        if (lost || !program) {
            return;
        }
        /* The drawing buffer is the canvas's backing store unless the browser had to make it
           smaller; the arithmetic is done in the pixels the shader really runs on. */
        const width = gl.drawingBufferWidth;
        const height = gl.drawingBufferHeight;
        gl.viewport(0, 0, width, height);
        gl.uniform2f(uniforms.box, width, height);
        gl.uniform2f(uniforms.enlarged, w * size.kx, h * size.ky);
        gl.uniform2f(uniforms.factor, size.kx, size.ky);
    }

    function draw() {
        if (!lost) {
            gl.drawArrays(gl.TRIANGLE_STRIP, 0, 4);
        }
    }

    function present() {
        if (!lost) {
            upload();
            draw();
        }
    }

    /* What the canvas shows, for the page tests: drawn and read back in one task, because
       the drawing buffer is not kept once the browser has composited it. */
    function readDisplay() {
        draw();
        const width = gl.drawingBufferWidth;
        const height = gl.drawingBufferHeight;
        const upside = new Uint8Array(width * height * 4);
        gl.readPixels(0, 0, width, height, gl.RGBA, gl.UNSIGNED_BYTE, upside);
        const data = new Uint8ClampedArray(upside.length);
        const stride = width * 4;
        for (let y = 0; y < height; y++) {
            data.set(upside.subarray((height - 1 - y) * stride, (height - y) * stride), y * stride);
        }
        return { width, height, data };
    }

    /* A lost context is given back by the browser only if the page says it wants it back,
       which is what preventDefault here does. */
    canvas.addEventListener('webglcontextlost', (event) => {
        event.preventDefault();
        lost = true;
        program = null;
        onLost();
    });
    canvas.addEventListener('webglcontextrestored', () => {
        lost = false;
        try {
            setUp();
            draw();
            onRestored(true);
        } catch (err) {
            onRestored(false);
        }
    });

    try {
        setUp();
    } catch (err) {
        return { renderer: null, taken: true,
                 why: 'WebGL set-up failed: ' + (err && err.message ? err.message : err) };
    }
    return { renderer: { name: 'webgl', resize, draw, present, readDisplay }, why: '',
             taken: true };
}

/* The Canvas 2D renderer: the source canvas, the enlargement, the displayed canvas. */
function create2dRenderer(canvas, core) {
    const w = core.width;
    const h = core.height;

    const source = document.createElement('canvas');
    source.width = w;
    source.height = h;

    /* willReadFrequently is not the hint it looks like here: it picks a software-backed 2D
       canvas, and in GPU-composited Firefox the accelerated one never shows what
       putImageData wrote - the canvas reads back as a single colour and the player sees a
       black picture.  Headless Firefox composites in software and cannot reproduce it, so
       only the visible check in tests/test_firefox.py catches a regression here.  In Chrome
       the flag is harmless.  Do not remove it as a no-op. */
    const sctx = source.getContext('2d', { alpha: false, willReadFrequently: true });
    const image = sctx.createImageData(w, h);
    const out = new Uint32Array(image.data.buffer);

    /* The other two are only ever drawn into, never read back by the shell, and drawImage is
       not the call the Firefox fault is about.  Where the browser's 2D canvas is software,
       the reduction is the cost at a large size that the WebGL renderer exists for. */
    const scaled = document.createElement('canvas');
    const mctx = scaled.getContext('2d', { alpha: false });
    const dctx = canvas.getContext('2d', { alpha: false });
    let size = { width: 1, height: 1, kx: 1, ky: 1 };

    function resize(next) {
        size = next;
        /* Resizing a canvas resets its context, so the smoothing settings are made again. */
        dctx.imageSmoothingEnabled = true;
        if (size.kx > 1 || size.ky > 1) {
            scaled.width = w * size.kx;
            scaled.height = h * size.ky;
            mctx.imageSmoothingEnabled = false;
        }
    }

    function draw() {
        if (size.kx === 1 && size.ky === 1) {
            /* The enlargement is the identity at this size: the source is the enlargement. */
            dctx.drawImage(source, 0, 0, size.width, size.height);
            return;
        }
        mctx.drawImage(source, 0, 0, scaled.width, scaled.height);
        dctx.drawImage(scaled, 0, 0, size.width, size.height);
    }

    function present() {
        convert(core, out);
        sctx.putImageData(image, 0, 0);
        draw();
    }

    function readDisplay() {
        const read = dctx.getImageData(0, 0, canvas.width, canvas.height);
        return { width: read.width, height: read.height, data: read.data };
    }

    return { name: '2d', resize, draw, present, readDisplay, source };
}

export function createVideo(canvas, core, sign = null, help = null) {
    const w = core.width;
    const h = core.height;

    let standard = STANDARDS.pal;
    let box = { deviceWidth: 0, deviceHeight: 0, left: 0, top: 0 };
    let dpr = 0;
    let kx = 1;
    let ky = 1;

    /* ?video=2d forces the Canvas 2D renderer, so that the fallback can be exercised on
       purpose instead of only when something else has failed, as ?audio=buffers does for
       the audio. */
    const forced = new URLSearchParams(location.search).get('video');
    let renderer = null;
    let note = '';
    let restoreTimer = 0;

    /* A new canvas in the old one's place, for the 2D renderer after WebGL has had it. */
    function replaceCanvas() {
        const fresh = canvas.cloneNode(false);
        canvas.replaceWith(fresh);
        canvas = fresh;
        canvas.width = Math.max(1, box.deviceWidth);
        canvas.height = Math.max(1, box.deviceHeight);
    }

    function fallBack(why) {
        clearTimeout(restoreTimer);
        note = why;
        replaceCanvas();
        renderer = create2dRenderer(canvas, core);
        renderer.resize({ width: box.deviceWidth, height: box.deviceHeight, kx, ky });
        present();
    }

    if (forced === '2d') {
        note = 'asked for by ?video=2d';
    } else {
        const made = createGlRenderer(canvas, core,
            () => {
                note = 'WebGL context lost, waiting for it';
                restoreTimer = setTimeout(
                    () => fallBack('WebGL context lost and not given back'), RESTORE_WAIT_MS);
            },
            (ok) => {
                clearTimeout(restoreTimer);
                if (ok) {
                    note = 'WebGL context lost and given back';
                } else {
                    fallBack('WebGL context given back but not usable');
                }
            });
        renderer = made.renderer;
        note = made.why;
        if (!renderer && made.taken) {
            replaceCanvas();
        }
    }
    if (!renderer) {
        renderer = create2dRenderer(canvas, core);
    }

    /* The frame interval and the time present() takes, over the last STATS_WINDOW_MS, for
       the diagnostics overlay (web/overlay.js), and in total for the page tests. */
    const stats = { frames: 0, frameMs: 0, frameMaxMs: 0, presents: 0, presentMs: 0,
                    presentMaxMs: 0 };
    let span = { start: -1, last: -1, frames: 0, frameMs: 0, frameMaxMs: 0, presents: 0,
                 presentMs: 0, presentMaxMs: 0 };
    let lastSecond = null;

    function noteFrame(now) {
        if (span.last >= 0) {
            const interval = now - span.last;
            span.frames++;
            span.frameMs += interval;
            span.frameMaxMs = Math.max(span.frameMaxMs, interval);
            stats.frames++;
            stats.frameMs += interval;
            stats.frameMaxMs = Math.max(stats.frameMaxMs, interval);
        } else {
            span.start = now;
        }
        span.last = now;
        if (now - span.start >= STATS_WINDOW_MS && span.frames) {
            lastSecond = {
                frameMs: span.frameMs / span.frames,
                frameMaxMs: span.frameMaxMs,
                presentMs: span.presents ? span.presentMs / span.presents : 0,
                presentMaxMs: span.presentMaxMs,
                presents: span.presents,
            };
            span = { start: now, last: now, frames: 0, frameMs: 0, frameMaxMs: 0,
                     presents: 0, presentMs: 0, presentMaxMs: 0 };
        }
    }

    /* A stopped clock is no slow frame: the interval across a pause of the animation frames
       (the page hidden, say) is not counted. */
    function restartFrames() {
        span = { start: -1, last: -1, frames: 0, frameMs: 0, frameMaxMs: 0, presents: 0,
                 presentMs: 0, presentMaxMs: 0 };
    }

    /* The box is laid out in whole device pixels and only then converted back to CSS pixels,
       so that the browser has nothing left to resample: the backing store is exactly the CSS
       size times devicePixelRatio, and the picture lands on the physical pixel grid. */
    function fit() {
        const ratio = window.devicePixelRatio || 1;
        const availableWidth = Math.max(1, Math.floor(window.innerWidth * ratio));
        const availableHeight = Math.max(1, Math.floor(window.innerHeight * ratio));
        const aspect = standard.boxWidth / standard.boxHeight;

        let deviceWidth = availableWidth;
        let deviceHeight = Math.round(availableWidth / aspect);
        if (deviceHeight > availableHeight) {
            deviceHeight = availableHeight;
            deviceWidth = Math.round(availableHeight * aspect);
        }
        deviceWidth = Math.max(1, Math.min(deviceWidth, availableWidth));
        deviceHeight = Math.max(1, Math.min(deviceHeight, availableHeight));

        const left = Math.round((availableWidth - deviceWidth) / 2);
        const top = Math.round((availableHeight - deviceHeight) / 2);

        if (ratio === dpr && deviceWidth === box.deviceWidth && deviceHeight === box.deviceHeight
            && left === box.left && top === box.top) {
            return;
        }
        dpr = ratio;
        box = { deviceWidth, deviceHeight, left, top };

        canvas.width = deviceWidth;
        canvas.height = deviceHeight;
        canvas.style.width = (deviceWidth / dpr) + 'px';
        canvas.style.height = (deviceHeight / dpr) + 'px';
        canvas.style.left = (left / dpr) + 'px';
        canvas.style.top = (top / dpr) + 'px';

        placeSign();
        placeHelp();

        /* The smallest whole numbers whose enlargement is at least as large as the box. */
        kx = Math.max(1, Math.ceil(deviceWidth / w));
        ky = Math.max(1, Math.ceil(deviceHeight / h));
        renderer.resize({ width: deviceWidth, height: deviceHeight, kx, ky });

        /* A resized canvas is cleared: the last picture is drawn again at once. */
        renderer.draw();
    }

    /* The pause sign (web/index.html) sits over the middle of the picture, its size a share of
       the picture's height, so that it covers the same small central part at any size. */
    function placeSign() {
        if (!sign) {
            return;
        }
        sign.style.left = ((box.left + box.deviceWidth / 2) / dpr) + 'px';
        sign.style.top = ((box.top + box.deviceHeight / 2) / dpr) + 'px';
        sign.style.fontSize = Math.max(SIGN_MIN_PX, box.deviceHeight / dpr * SIGN_SHARE) + 'px';
    }

    /* The help screen (web/index.html) covers the picture.  Its size is measured rather than
       worked out from the text, so that the font and the wording are free to change: the
       sheet is laid out at the picture's share and then scaled down if it does not fit.
       Monospace text scales with the font size, so one step is enough.  A hidden sheet has
       no size, which is why showing it places it again. */
    function placeHelp() {
        if (!help || help.classList.contains('off')) {
            return;
        }
        const width = box.deviceWidth / dpr;
        const height = box.deviceHeight / dpr;
        help.style.left = (box.left / dpr) + 'px';
        help.style.top = (box.top / dpr) + 'px';
        help.style.width = width + 'px';
        help.style.height = height + 'px';
        const size = Math.max(HELP_MIN_PX, height * HELP_SHARE);
        help.style.fontSize = size + 'px';
        const sheet = help.firstElementChild;
        const scale = Math.min(1, width * HELP_FILL / sheet.offsetWidth,
                               height * HELP_FILL / sheet.offsetHeight);
        help.style.fontSize = (size * scale) + 'px';
    }

    function showHelp(shown) {
        if (help) {
            help.classList.toggle('off', !shown);
            placeHelp();
        }
    }

    /* Shown while the game is paused, whatever asked for the pause; the shell asks every
       animation frame (web/main.js). */
    let signShown = false;
    function showPaused(paused) {
        if (sign && paused !== signShown) {
            signShown = paused;
            sign.classList.toggle('off', !paused);
        }
    }

    function present() {
        const start = performance.now();
        renderer.present();
        const took = performance.now() - start;
        span.presents++;
        span.presentMs += took;
        span.presentMaxMs = Math.max(span.presentMaxMs, took);
        stats.presents++;
        stats.presentMs += took;
        stats.presentMaxMs = Math.max(stats.presentMaxMs, took);
    }

    function setStandard(name) {
        standard = STANDARDS[name] || STANDARDS.pal;
        box = { deviceWidth: 0, deviceHeight: 0, left: 0, top: 0 };
        fit();
        return standard;
    }

    function geometry() {
        return {
            standard: standard.name,
            hz: standard.hz,
            ratio: standard.boxWidth + ':' + standard.boxHeight,
            dpr,
            kx,
            ky,
            deviceWidth: box.deviceWidth,
            deviceHeight: box.deviceHeight,
            cssWidth: box.deviceWidth / dpr,
            cssHeight: box.deviceHeight / dpr,
        };
    }

    function timing() {
        return { path: renderer.name, note, lastSecond, ...stats };
    }

    /* The exact picture, 640 x 214 RGBA, on a 2D canvas.  On the 2D path that is the source
       canvas the display was drawn from; on the WebGL path there is none, and it is made
       here from the same memory, on demand and never per frame. */
    let pictureCanvas = null;
    function picture() {
        if (renderer.source) {
            return renderer.source;
        }
        if (!pictureCanvas) {
            pictureCanvas = document.createElement('canvas');
            pictureCanvas.width = w;
            pictureCanvas.height = h;
        }
        const ctx = pictureCanvas.getContext('2d', { alpha: false, willReadFrequently: true });
        const image = ctx.createImageData(w, h);
        convert(core, new Uint32Array(image.data.buffer));
        ctx.putImageData(image, 0, 0);
        return pictureCanvas;
    }

    /* devicePixelRatio changes without a resize event when the window moves to a screen of
       another density or the page is zoomed.  A media query on the ratio the page currently
       has is the only notice a page gets, and it has to be made again for the new one. */
    let density = null;
    function onDensityChange() {
        fit();
        watchDensity();
    }
    function watchDensity() {
        if (density) {
            density.removeEventListener('change', onDensityChange);
        }
        density = window.matchMedia('(resolution: ' + (window.devicePixelRatio || 1) + 'dppx)');
        density.addEventListener('change', onDensityChange);
    }

    window.addEventListener('resize', fit);
    document.addEventListener('fullscreenchange', fit);
    watchDensity();
    fit();

    /* After scaling, the exact framebuffer pixels exist nowhere on the page, and the page
       tests of SPEC section 8 need both them and the canvas the browser really shows. */
    window.__wofVideo = {
        get display() { return canvas; },
        get path() { return renderer.name; },
        picture,
        readDisplay: () => renderer.readDisplay(),
        geometry,
        present,
        stats: timing,
    };

    return { present, fit, setStandard, geometry, showPaused, showHelp, noteFrame, restartFrames,
             timing, standard: () => standard };
}
