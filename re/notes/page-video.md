# The page's picture on the GPU (M9)

M9, as the owner redefined it on 2026-09-29: the page's drawing path made fast enough that the picture reaches the screen at the browser's full frame rate at any size, a Retina fullscreen included. The core's interface for the picture is unchanged (`SPEC.md` 6.1 and 6.4): one 640 x 214 indexed framebuffer, one palette per output row, palette 0 black. Everything here is in `web/video.js`, `web/main.js` (the frame's timing) and `web/overlay.js` (its line), with the tests in `tests/`.

## Summary

- **The cause.** The 2D path scaled the picture in two canvas steps, a whole-number nearest enlargement and a smooth reduction to the box. In Firefox the 2D canvas is software (Skia; about:support: `AzureCanvasBackend skia`, compositing WebRender on the GPU). At the owner's screen the reduction's `drawImage` took 28.7 ms on the main thread, the whole `present()` 32.8 ms, and the page showed a frame every other refresh. Chrome draws its 2D canvases on the GPU and was at full rate at every size.
- **The fix.** A WebGL renderer does both steps in one fragment shader pass, from three small textures. At the owner's screen `present()` takes 0.3 ms in Firefox and 0.05 ms in Chrome, and no frame is late in either.
- **The fallback.** Canvas 2D, as before, where WebGL is refused, runs only in software, fails to set up, or is lost and not given back. `?video=2d` asks for it.
- **The tests.** Every page session says which renderer drew it, and the tests fail if it is not the one they are about. The picture tests run on both renderers. A new frame-time test holds the frame interval and `present()` at a screen-sized window, and fails on the previous build in Firefox.

## The machine and the display's refresh

The owner's MacBook Pro 16" (Intel UHD Graphics 630 beside an AMD Radeon Pro 5600M) has a Retina panel of 3072 x 1920 that macOS runs at "looks like" 1792 x 1120: the screen is 1792 x 1120 CSS pixels at `devicePixelRatio` 2, so a fullscreen picture is 3573 x 2240 device pixels, the PAL box's 1024 : 642 at the screen's full height. The panel runs at 60 Hz, and `requestAnimationFrame` delivers 60 Hz in both browsers: 16.66 to 16.70 ms per frame on a blank page, the median of 90 frames. It did so on the locked screen with the display asleep, in a visible window and headless, which is how every number below was taken.

A display faster than 60 Hz changes nothing in the method: every figure is in refreshes, measured on the machine. PAL runs 50 passes a second, so at 60 Hz one frame in six presents nothing and the picture changes 50 times a second; at 120 Hz seven frames in twelve present nothing. A frame there is 8.3 ms, so the same `present()` is a larger share of it, and a frame is late from 12.5 ms on.

## How it was measured

The page is walked as a player walks it (help screen, story scroller, title, the first rank, the briefing) into the hold; the lift goes up and the aircraft rolls east along the deck, which scrolls the picture, and the window is made the size to be measured. Then every animation frame's timestamp is taken over ten seconds by a `requestAnimationFrame` loop of the measurement's own, beside the shell's, so it measures any build. A frame longer than 1.5 refreshes (25 ms at 60 Hz) is a frame the picture missed. `present()` was timed inside, with `performance.now()` round each step, in a copy of the previous build in the scratch area (the shipped page itself unchanged); the WebGL build keeps its own count (below).

Sizes: the page tests' usual window (Chrome 1280 x 900, Firefox 1400 x 800), the owner's screen 1792 x 1120, 420 x 320, and in Firefox a real window of 1536 x 960. A visible window cannot be made 1120 tall on this screen, whose menu bar and the browser's toolbar take some of it, and a locked screen refuses the fullscreen space (`SPEC.md` 8, row Page), so the screen size is given as the page's viewport (Firefox `browsingContext.setViewport`, Chrome `Emulation.setDeviceMetricsOverride` with the real density): the page lays itself out and draws at that size, which is what costs. Chrome ran under `--force-device-scale-factor=2`. Firefox's timer is coarse (`performance.now()` in steps of up to a millisecond), so its `present()` figures are means over hundreds of calls.

## Before: the two-step 2D path

Times in ms; "long" is frames longer than 1.5 refreshes over ten seconds; `present()` is the mean of every present in the span, and its parts are the conversion loop, `putImageData`, the enlargement's `drawImage` and the reduction's `drawImage`.

| Browser | Size (CSS) | Device | Mean frame | p95 | Long | `present()` | convert | put | enlarge | reduce |
|---|---|---|---|---|---|---|---|---|---|---|
| Firefox, visible | 1400 x 800 | 2552 x 1600 | 16.69 | 16.76 | 1 of 599 | 17.60 | 0.42 | 0.12 | 2.09 | 14.97 |
| Firefox, visible | 1536 x 960 window | 3062 x 1920 | 21.68 | 33.34 | 139 of 462 | 24.08 | 0.43 | 0.06 | 2.65 | 20.93 |
| Firefox, visible | 1792 x 1120 | 3573 x 2240 | 31.95 | 50.00 | 224 of 313 | 32.80 | 0.40 | 0.05 | 3.69 | 28.65 |
| Firefox, visible | 420 x 320 | 840 x 527 | 16.67 | 16.98 | 0 of 600 | 3.58 | 0.82 | 0.10 | 0.57 | 2.09 |
| Chrome, visible, GPU | 1280 x 900 | 2560 x 1605 | 16.67 | 18.20 | 0 of 600 | 0.70 | 0.45 | 0.08 | 0.02 | 0.14 |
| Chrome, visible, GPU | 1536 x 960 window | 3062 x 1920 | 16.67 | 18.20 | 0 of 601 | 0.73 | 0.48 | 0.07 | 0.03 | 0.15 |
| Chrome, visible, GPU | 1792 x 1120 | 3573 x 2240 | 16.67 | 18.20 | 0 of 600 | 0.63 | 0.39 | 0.08 | 0.02 | 0.14 |
| Chrome, visible, GPU | 420 x 320 | 840 x 527 | 16.66 | 18.10 | 0 of 601 | 0.64 | 0.42 | 0.07 | 0.02 | 0.13 |
| Chrome, headless, GPU | 1792 x 1120 | 3573 x 2240 | 16.67 | 16.70 | 0 of 601 | 0.66 | 0.42 | 0.08 | 0.03 | 0.14 |
| Chrome, headless, no GPU | 1280 x 900 | 2560 x 1605 | 17.24 | 16.80 | 20 of 581 | 2.61 | 0.23 | 0.10 | 0.02 | 2.26 |
| Chrome, headless, no GPU | 1792 x 1120 | 3573 x 2240 | 36.82 | 50.00 | 272 of 272 | 4.91 | 0.24 | 0.09 | 0.02 | 4.56 |
| Chrome, headless, no GPU | 420 x 320 | 840 x 527 | 16.67 | 16.80 | 0 of 601 | 1.08 | 0.41 | 0.07 | 0.02 | 0.58 |

The cause, as measured: in Firefox the reduction's `drawImage` onto the displayed canvas blocks the main thread in proportion to the pixels it writes, about 3.6 ns a pixel from a 9-megapixel enlargement. Firefox's about:support in that window lists `ACCELERATED_CANVAS2D` as available but the canvas backend as `skia`; whatever the reason in the browser, the time is spent synchronously and the picture misses every other refresh from about 3000 x 1900 device pixels up. The user's figure of 32 ms at a fullscreen size (`re/notes/porting-m8.md`, "The page and the fullscreen finding") is the 31.95 here. Chrome on its GPU records the 2D draws and runs them in its GPU process: 0.14 ms of the main thread, no frame late at any size. Chrome without a GPU (the page tests' old `--disable-gpu`) rasterises in software off the main thread and misses every frame at the screen's size.

## The WebGL path

WebGL 1, which the browsers here give wherever they give WebGL at all, with no extension: nothing in the renderer needs WebGL 2 (`texelFetch` or integer textures would be conveniences, not needs), and its GLSL ES 1.00 would run in a WebGL 2 context unchanged.

**Three textures, from the core's memory.** The framebuffer is a 640 x 214 `LUMINANCE` texture, filled every present by one `texSubImage2D` straight from the core's memory, a `Uint8Array` view with no copy and no `ImageData` in between (137 KB a frame). The palettes are one `RGBA` texture of 32 x 24, the core's words in the byte order an `ImageData` has; the row table is a 214 x 1 `LUMINANCE` texture of the palette index of each row. Both are compared with what was last sent and uploaded only when they differ, which the core makes them do at a fade step, the split line's move, the sky flash and the like. All three are sampled `NEAREST` with `CLAMP_TO_EDGE` at texel centres, which reads them exactly.

**One pass for both steps.** The fragment shader runs once per output pixel on one quad over the canvas, whose backing store is the box's device size as `fit()` lays it out. It computes where the output pixel's centre falls in the whole-number enlargement of 640 kx by 214 ky texels, `kx` and `ky` the same smallest whole numbers `fit()` has always chosen, as a smooth reduction samples it: position times enlargement over box, minus a half. It then filters bilinearly from the four texels round that point, as the reduction does. A texel of the enlargement is the framebuffer pixel whose block it lies in, so the shader never makes the enlargement: the texel's framebuffer pixel is the texel's index divided by the factor, rounded down. So the output is what the nearest enlargement followed by the smooth reduction gave, texel for texel and weight for weight, without the enlargement's up to nine megapixels being written and read every frame. Where all four texels lie in one block, which is every output pixel but the one where the reduction falls between two blocks, there is nothing to blend and one lookup is made; at a block edge two or four. The picture tests' tolerances therefore hold unchanged (below).

**Colours are blended, never indices.** Each of the four texels is looked up through the palette of its own framebuffer row before anything is mixed. Across a row boundary the two rows keep their own palettes, as they did when the 2D path's source canvas held RGBA; an interpolated index, or one palette for both, would put a colour between them that neither row has. The palette entry is the row's palette times 32 plus the pixel's index, as `pal[rows[y] * 32 + fb[i]]` was, so an index beyond 31 would reach the next palette exactly as before.

The second approach the task offered, sampling `NEAREST` and blending only by the share of the output pixel an edge covers, gives the same picture at the large sizes but needs a loop wherever a framebuffer pixel is smaller than an output pixel (any box narrower than 640 device pixels), where the two-step path samples bilinearly from the unenlarged source; the one-pass version of the two steps covers every size with one formula and keeps the look the tests were measured on.

**Precision.** Positions up to 3840 texels have to be exact, so the renderer asks for `highp` float in the fragment shader and takes the 2D path if the browser has none. Every coordinate is a whole number held in a float, and each division that must land on a whole number is given half a unit to spare before `floor()`, against a GPU whose division comes out a hair low.

**The context.** `alpha: false`, no antialiasing, depth or stencil, `preserveDrawingBuffer: false`: the drawing buffer is drawn once per present and once on a resize, and the compositor keeps showing the last one on frames with no present. `failIfMajorPerformanceCaveat: true`: a WebGL that the browser runs in software is refused. SwiftShader, which Chrome gives with `--enable-unsafe-swiftshader` where it has no GPU, took 133 ms a frame at the owner's screen and 68 ms at 1280 x 900 at a scale factor of 2, four times the 2D path's own software time; where WebGL is only software the 2D path is the faster one. No `powerPreference`: the browser's default keeps the integrated GPU on a machine with two.

**What present() costs now.** One `texSubImage2D` of 137 KB, two comparisons of 214 and 768 entries, and one draw call; the shader's work is the GPU's.

## The fallback, and the query

The 2D renderer is the previous path unchanged: the 640 x 214 source canvas that `putImageData` writes, still asked for with `willReadFrequently: true` so that it is software-backed (in GPU-composited Firefox the accelerated one can drop `putImageData` and show black, `SPEC.md` 6.2), the enlargement, and the displayed canvas. It is taken:

- when `getContext('webgl')` gives nothing: WebGL switched off or blocked, or only in software (above);
- when the shader does not compile or link, or `highp` is missing;
- when the context is lost and not given back within 2 s (`RESTORE_WAIT_MS`). On `webglcontextlost` the shell calls `preventDefault()`, which tells the browser it wants the context back; on `webglcontextrestored` it makes the program and the textures again and draws the last frame. If the restored context cannot be set up, it falls back at once.
- when the page is opened with `?video=2d`, which exists so that the tests and the owner can run the fallback on purpose, as `?audio=buffers` does for the audio.

A canvas that has once given a WebGL context never gives a 2D one, so the fallback puts a new canvas element in the old one's place, with the same id, class and inline style, and sizes it from the box; `fit()` goes on working on the new one. The diagnostics overlay's line `video` names the path in use, and a second line `video note` the reason for a fallback, or that a lost context came back.

## What the page tests see

After scaling, the exact framebuffer pixels exist nowhere on the page, so `window.__wofVideo` gives them to the tests:

| Member | What it is |
|---|---|
| `path` | `webgl` or `2d`, the renderer drawing now |
| `picture()` | the exact 640 x 214 RGBA picture on a 2D canvas: on the 2D path the source canvas itself, on the WebGL path one filled from the framebuffer and the palettes by the same conversion loop, on demand, never per frame |
| `readDisplay()` | what the displayed canvas holds, as width, height and RGBA rows from the top; on the WebGL path drawn again and read with `readPixels` in the same task, because the drawing buffer is not kept after compositing |
| `display` | the displayed canvas (a getter: the fallback replaces it) |
| `geometry()`, `present()` | as before |
| `stats()` | the path and the fallback's reason, the frame interval and `present()` time over the last second, and counts since the start |

The drivers (`tests/pagemeasure.mjs`, `tests/pagefullscreen.mjs`) read `picture()` where they read the source canvas and `readDisplay()` where they read the displayed canvas's 2D context. `PICTURE`, `GEOMETRY`, `DISPLAY` and `FULLSCREEN_LOOK` carry `path`, and `VIDEO` is `stats()`.

**Headless Chrome on its GPU.** The page tests started Chrome with `--disable-gpu`, which leaves headless Chrome no WebGL at all (and with `--enable-unsafe-swiftshader` only the software one the shell refuses). `tests/chrome.mjs` no longer passes it: headless Chrome then draws with ANGLE on Metal, the WebGL the owner's Chrome has, and composites on the GPU. The picture checks under a true scale factor pass there as they did in software (below).

**Which session runs which path.** Every session says it, and the tests fail on the wrong one:

| Session | Path | Held by |
|---|---|---|
| Chrome, `tests/pagecheck.mjs`, all eight pages | WebGL | `test_every_page_of_the_run_draws_with_webgl`, and the box and picture tests per look |
| Chrome, `tests/pagescale.mjs`, scale factor 2 | WebGL, and 2D under `?video=2d` | the `scaled` fixture runs twice; `test_the_scale_factor_run_draws_with_the_renderer_it_asked_for` and every picture test per look |
| Chrome, `tests/pageframes.mjs` | WebGL | `test_the_picture_keeps_the_frame_rate_at_a_screen_size` |
| Firefox headless and visible, `tests/pagecheck_firefox.mjs`, every tab | WebGL | `test_every_page_of_the_run_draws_with_webgl` and its visible twin |
| Firefox headless and visible, the tab with `?video=2d` | 2D | `test_the_2d_path_shows_the_picture` and its visible twin |
| Firefox visible, `tests/pageframes.mjs` | WebGL | `test_the_picture_keeps_the_frame_rate_in_a_visible_window` |

Headless Firefox gives WebGL on this machine; if a browser ever stops giving it, those tests fail instead of passing on the fallback.

**The picture tests on both paths.** Under a true scale factor of 2 in Chrome, both renderers: every framebuffer pixel against the screenshot at the centre of its block, the position fitted from the colour edges, the hardness of the block edges, and the sample points of the displayed canvas and of the screenshot. In Firefox, headless and visible: the same on the WebGL tabs, and on the 2D tab the sample points at the window's size and at the large viewport, and every framebuffer pixel wherever the blocks are large enough.

## The frame-time test

`tests/pageframes.mjs` drives either browser the same way and asks nothing of the page but what every build of the shell has had (the overlay's player line, `__wofVideo.display` and `present()`), so it measures older builds too. It measures the refresh on the blank page first, walks into the mission, rolls along the deck with the picture scrolling, makes the window the screen's size (Chrome headless at a scale factor of 2 at 1792 x 1120; the visible Firefox at its screen's own size, as its viewport) and times every frame over five seconds, with `present()` from the shell's own count (or, on a build without one, by calling it). `assert_the_picture_keeps_the_frame_rate` (`tests/conftest.py`) holds:

| Figure | Limit | The WebGL path | The previous build, visible Firefox |
|---|---|---|---|
| mean frame interval | at most 1.05 refreshes | 1.00 in both | 1.92 and 1.97 |
| frames longer than 1.5 refreshes | at most 5 in the span | 0 in both | 117 of 157, and 123 of 152 |
| `present()` mean | at most 1 ms | 0.06 (Chrome), 0.35 (Firefox) | 24.75 and 23.95 |
| the path | `webgl` | `webgl` | none (the previous build has no WebGL) |
| the window | the screen's size, the page not hidden, the aircraft moved | yes | yes |

The negative control is `WOF_FRAMES_PAGE`, which points both tests at another build: run on the previous build (main at `59e4ba9`), the visible Firefox fails every figure, twice over (mean 31.96 and 32.89 ms, 117 of 157 and 123 of 152 frames long, `present()` 24.75 and 23.95 ms by calls, the path absent). Chrome on its GPU fails it only for the path (mean 16.67 ms, none long, `present()` 0.62 ms by calls): the previous build was never slow in Chrome with a GPU, and without one both builds take the same 2D path. The test that tells the two builds apart by their frames is therefore Firefox's, which needs the visible window.

## After

The same walk, sizes and span as the table before, on the build with the WebGL renderer, on both paths: WebGL by default, Canvas 2D asked for with `?video=2d`. `present()` is the shell's own count: the mean of every present in the ten seconds, the whole call.

| Browser | Path | Size (CSS) | Device | Mean frame | p95 | Long | `present()` |
|---|---|---|---|---|---|---|---|
| Firefox, visible | WebGL | 1400 x 800 | 2552 x 1600 | 16.67 | 16.94 | 0 of 600 | 0.36 |
| Firefox, visible | WebGL | 1536 x 960 window | 3062 x 1920 | 16.67 | 16.80 | 0 of 600 | 0.36 |
| Firefox, visible | WebGL | 1792 x 1120 | 3573 x 2240 | 16.67 | 16.68 | 0 of 601 | 0.32 |
| Firefox, visible | WebGL | 420 x 320 | 840 x 527 | 16.67 | 16.86 | 0 of 600 | 0.33 |
| Firefox, visible | 2D | 1400 x 800 | 2552 x 1600 | 16.92 | 16.96 | 9 of 592 | 17.62 |
| Firefox, visible | 2D | 1536 x 960 window | 3062 x 1920 | 23.04 | 33.34 | 166 of 434 | 24.41 |
| Firefox, visible | 2D | 1792 x 1120 | 3573 x 2240 | 33.39 | 50.00 | 235 of 300 | 32.96 |
| Firefox, visible | 2D | 420 x 320 | 840 x 527 | 16.67 | 16.68 | 0 of 600 | 3.70 |
| Chrome, visible, GPU | WebGL | 1280 x 900 | 2560 x 1605 | 16.67 | 18.50 | 0 of 601 | 0.06 |
| Chrome, visible, GPU | WebGL | 1536 x 960 window | 3062 x 1920 | 16.67 | 18.40 | 0 of 601 | 0.05 |
| Chrome, visible, GPU | WebGL | 1792 x 1120 | 3573 x 2240 | 16.66 | 18.40 | 0 of 601 | 0.05 |
| Chrome, visible, GPU | WebGL | 420 x 320 | 840 x 527 | 16.67 | 18.20 | 0 of 601 | 0.05 |
| Chrome, visible, GPU | 2D | 1280 x 900 | 2560 x 1605 | 16.67 | 18.30 | 0 of 601 | 0.54 |
| Chrome, visible, GPU | 2D | 1536 x 960 window | 3062 x 1920 | 16.66 | 18.50 | 0 of 601 | 0.67 |
| Chrome, visible, GPU | 2D | 1792 x 1120 | 3573 x 2240 | 16.67 | 18.30 | 0 of 600 | 0.59 |
| Chrome, visible, GPU | 2D | 420 x 320 | 840 x 527 | 16.67 | 18.40 | 0 of 600 | 0.53 |
| Chrome, headless, GPU | WebGL | 1280 x 900 | 2560 x 1605 | 16.67 | 16.70 | 0 of 601 | 0.05 |
| Chrome, headless, GPU | WebGL | 1792 x 1120 | 3573 x 2240 | 16.67 | 16.70 | 0 of 601 | 0.06 |
| Chrome, headless, GPU | WebGL | 420 x 320 | 840 x 527 | 16.67 | 16.80 | 0 of 601 | 0.05 |
| Chrome, headless, GPU | 2D | 1280 x 900 | 2560 x 1605 | 16.67 | 16.80 | 0 of 601 | 0.60 |
| Chrome, headless, GPU | 2D | 1792 x 1120 | 3573 x 2240 | 16.67 | 16.70 | 0 of 601 | 0.62 |
| Chrome, headless, GPU | 2D | 420 x 320 | 840 x 527 | 16.67 | 16.70 | 0 of 601 | 0.62 |

On WebGL no frame is late in either browser at any size, and `present()` is 0.05 ms in Chrome and a third of a millisecond in Firefox, whose coarse timer makes that the upper side of the true figure. The 2D path is the previous one and measures as it did. Visible Chrome's p95 of about 18 ms with no frame late is the spread of its frame timestamps, which headless Chrome does not have; the mean is the refresh.

Chrome without a GPU takes the 2D path with the build, because it refuses the software WebGL: "WebGL refused, or only in software". It is then as slow as the previous build was there, measured side by side on a busier machine than the table before (the locked screen's moving wallpaper took a fifth of a core): at 1280 x 900 a mean of 24.5 and 25.9 ms against the previous build's 24.6 and 23.8, at 1792 x 1120 every frame late in both. No player's Chrome runs without a GPU, and the page tests no longer do.

## What the tests hold, and what only the owner's eyes can

The tests hold the picture to the pixel against a screenshot under a real scale factor of 2 in Chrome and at the real density in a visible Firefox window, on both paths, and the frame interval at the screen's size in both browsers. What they cannot hold is the real fullscreen on the unlocked screen, where macOS moves the window into a space of its own and the compositor may take another route; the smoothness of scrolling as a person sees it; and a display other than this one. The owner's look in real fullscreen in both browsers, with the overlay's `video` line read there, is M9's confirmation.
