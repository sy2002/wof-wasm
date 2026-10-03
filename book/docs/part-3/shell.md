Chapter 23
{ .chapter-kicker }

# The shell

This chapter is the program on the other side of chapter 22's interface. By its end you will know what the [shell](../glossary.md#shell) is and why it is small; how its clock turns a display's refreshes into VBlanks; how the picture reaches the screen in the machine's proportions, and why through the graphics processor; how the sound keeps flowing; which keys the shell keeps and what it stores; and how [the help screen, the pause sign and fullscreen](../part-1/faithful.md#what-the-shell-adds) and a hidden page behave, each with its reason.

## A small program that knows no game

Chapter 1 called the shell a thin layer around the [core](../glossary.md#core): a clock, a screen, a loudspeaker, a keyboard and a place for saved games. It is plain JavaScript with no framework, in [`web/`](repo:web/): eight modules, the page's template [`web/index.html`](repo:web/index.html) and a stylesheet, about 2,400 lines, joined by the entry point [`web/main.js`](repo:web/main.js).

The page must open with a double click on the file and ask the network for nothing. A page opened from a file cannot load modules one by one, so the build is the bundler: it joins seven modules into one scope, strips their `import` lines and `export` words, and stops if any module syntax is left. Into the template go the stylesheet, the script and two payloads in base64, bytes written as text, the core's [WebAssembly](../glossary.md#webassembly) and the game's files, in `script` elements of a type no browser runs. The core is made from those bytes with an empty list of imports: it reads no clock and calls no JavaScript, and gets everything through chapter 22's interface. Nor can a page wait, or nothing is drawn and no key arrives; that is why the core's waits are [coroutines](../glossary.md#coroutine) that return.

Nearly nothing in the shell knows the game: its clock, picture, sound, key codes, storage and screens would serve another game ported the same way; only the help screen's list of keys is this game's.

## The clock

The game counts its time in [VBlanks](../glossary.md#vblank); a browser offers [**animation frames**](../glossary.md#animation-frame): calls of a page's drawing routine just before the browser repaints, at the display's refresh rate, and none while the page is hidden. Chapter 7 gave the rule, 50 VBlanks a second on PAL whatever the display; here is the mechanism.

The clock keeps an [**accumulator**](../glossary.md#accumulator): a store of real time not yet turned into VBlanks. Every animation frame adds the time since the last. For every fiftieth of a second in the store the clock calls the core's VBlank entry, `wof_vblank`, with the joystick's state, then its pass entry, `wof_pass`, and takes the fiftieth off; the rest waits. What the game sees is [**emulated time**](../glossary.md#emulated-time), its own time counted in VBlanks, never the display's: a monitor of 144 Hz gives a VBlank in about every third animation frame, one of 30 Hz one or two in each.

![Above, six animation frames of a 60 Hz display over five VBlanks of emulated time, each VBlank joined to the animation frame that issues it, and what each animation frame does; below, after a stall, one animation frame issuing at most 24 VBlanks.](../figures/clock-frames.svg)

/// caption
Six animation frames of a 60 Hz display on PAL: five VBlanks fall in them, so one animation frame in six presents nothing. After a stall, one animation frame makes up at most 24 VBlanks.
///

Here is one animation frame. Look at the cap before the loop, `MAX_CATCHUP` VBlanks' worth, and at `video.present()`, called only if a VBlank was issued, while the sound's `pump` runs every time:

```js
--8<-- "generated/listings/js/frame.js"
```

The cap is for a stall, an animation frame that comes very late while the page is on view. The clock then makes up at most 24 VBlanks, the original's own limit: the [input queue](../glossary.md#input-queue) holds six input bytes of four VBlanks each, and anything older the machine would have dropped too. The rest is lost, and counted.

After the VBlanks come, in a fixed order, the pause sign, the diagnostics overlay, the sound's start, the flip and the files to store, and the request to end the program. The clock also measures its rates for the diagnostics overlay; a change of the video standard empties the accumulator and starts the measurement again, because a second that straddled the change would show a rate that is neither.

/// figures
| The clock's figures, derived | |
|---|---|
| A refresh at 60 Hz | 16.7 ms |
| A VBlank on PAL | 20 ms |
| An animation frame counted as late, at 60 Hz | from 1.5 refreshes, 25 ms |
///

## The picture

### The box

The video standard is one setting, PAL or NTSC, which sets the VBlank rate and the [**pixel aspect**](../glossary.md#pixel-aspect), how wide a pixel is shown against its height, together, as a machine has one or the other; PAL is the default, for chapter 1's reasons. On PAL a [low-resolution](../glossary.md#low-resolution) pixel is 16/15 as wide as it is tall. The framebuffer's pixels are [high-resolution](../glossary.md#high-resolution) ones, half as wide, so its 640 by 214 are shown in a box of 1024 : 642; on NTSC, where 320 by 200 fills a screen of 4 : 3, in one of 800 : 642. Square pixels would give a strip three times as wide as high.

The box is the largest of its ratio that fits the window, centred on black, worked out again whenever the window or its screen changes. It is laid out in [**device pixels**](../glossary.md#device-pixel), the screen's own, rather than in CSS pixels, the page's unit, which a Retina screen draws two device pixels wide. In whole device pixels the canvas holds exactly as many pixels as it covers, and the browser resamples the picture no third time. Look at the canvas's size in device pixels against its style in CSS pixels, and at `kx` and `ky`:

```js
--8<-- "generated/listings/js/fit.js"
```

### Two steps

No pair of whole-number factors keeps the aspect at the size of any window, so the shell uses [**two-step scaling**](../glossary.md#two-step-scaling): an enlargement by whole numbers with nearest neighbour, which makes every framebuffer pixel a block of exactly equal size, then a smooth reduction to the box, the one step that falls between pixels, and it falls between blocks already large. One smooth step would blur every pixel; one nearest step would make some columns a device pixel wider than others.

The first shell did both in 2D canvases. Firefox draws a 2D canvas with the processor, through the Skia library, and the reduction writes every pixel of the box on the main thread, which also runs the clock: at the owner's Retina fullscreen, 1792 by 1120 CSS pixels, the picture missed every other refresh. Chrome draws its 2D canvases on the graphics processor and was never slow.

### The WebGL renderer

So the main [**renderer**](../glossary.md#renderer), the shell's code that puts the picture on the canvas, is WebGL 1, the browsers' way to the graphics processor, with the 2D renderer as its fallback. It hands the graphics processor three textures, images it reads from: the framebuffer, a byte a pixel, at every present, straight from the core's memory; the palettes; and the row table, which says which [palette](../glossary.md#palette) each row uses (chapter 11). The last two go only when they change.

A [**fragment shader**](../glossary.md#fragment-shader), the small program the graphics processor runs for every pixel it draws, then does both steps at once. For each device pixel it works out where the reduction would sample the enlargement and which four texels, pixels of the enlargement, lie round that point. A texel belongs to the framebuffer pixel whose block it lies in, so the enlargement, up to nine megapixels at a Retina fullscreen, is never made. Where the four lie in one block, nearly everywhere, it reads one; at a block's edge it mixes two or four by the reduction's weights, so the picture is the two-step one, texel for texel.

![Left, six framebuffer pixels in two rows; middle, their enlargement into blocks of equal size under the dashed grid of device pixels, one sample point where four blocks meet; right, its four texels, each through its own row's palette, then mixed.](../figures/two-step.svg)

/// caption
The two steps, and what the shader does with them: the same colour number gives another colour in another row, so each texel takes its own row's palette before anything is mixed.
///

Colours are mixed, never colour numbers: each texel goes through its own row's palette first, so where two rows meet each keeps its palette; mixing the numbers would put a colour between them that neither row has. Look at `colour`, which turns a position into its row's palette entry, and at the `mix` calls, made only where the texels belong to different pixels:

```c
--8<-- "generated/listings/js/fragment-shader.js"
```

The positions must be exact to the texel, so the shader demands high precision, and a browser without it gets the 2D renderer; each division meant to land on a whole number has half a unit to spare against hardware that divides a hair low. A WebGL the browser runs in software is refused, because there it was four times slower than the 2D renderer. A present now costs one upload of 137 KB, two comparisons and one draw. The note's measurements, ten seconds each in visible windows at 60 Hz on the shipped build, the 2D rows its fallback; the previous build, which had only the 2D renderer, measured the same:

| Browser | Renderer | CSS size | Device size | Mean (ms) | Late | `present()` (ms) |
|---|---|---|---|---|---|---|
| Firefox | 2D | 1400 x 800 | 2552 x 1600 | 16.92 | 9 of 592 | 17.62 |
| Firefox | 2D | 1792 x 1120 | 3573 x 2240 | 33.39 | 235 of 300 | 32.96 |
| Firefox | WebGL | 1792 x 1120 | 3573 x 2240 | 16.67 | 0 of 601 | 0.32 |
| Firefox | WebGL | 420 x 320 | 840 x 527 | 16.67 | 0 of 600 | 0.33 |
| Chrome | 2D | 1792 x 1120 | 3573 x 2240 | 16.67 | 0 of 600 | 0.59 |
| Chrome | WebGL | 1792 x 1120 | 3573 x 2240 | 16.66 | 0 of 601 | 0.05 |

### When WebGL is not there

The 2D renderer takes over where WebGL is refused, where the shader fails or high precision is missing, where the context is lost and not given back within two seconds, and on `?video=2d`, which lets the tests and the owner run the fallback on purpose. A canvas that has once given a WebGL context never gives a 2D one, so the shell puts a new canvas in its place. The page and the notes call the renderer in use the path; the diagnostics overlay names it, and the shell gives it to the tests with the exact picture, which after scaling exists nowhere on the page (chapter 24).

## The sound

The core mixes [Paula](../glossary.md#paula)'s channels by emulated time (chapter 18). Every animation frame the shell takes what its VBlanks mixed, as [**audio frames**](../glossary.md#audio-frame), instants of a value for the left and one for the right, and queues them behind what is playing. The emulation's clock and the audio hardware's drift apart a little, so the queue is kept between two bounds, both corrections counted on the diagnostics overlay:

/// figures
| The sound's queue | |
|---|---|
| Below this much queued, silence tops it up to 100 ms | 40 ms |
| Above this much queued, the core's audio frames are dropped | 300 ms |
///

The sound plays through an [**audio worklet**](../glossary.md#audio-worklet), a small program the browser runs on its audio thread. It plays the blocks the page posts and reports how much it has played, by which the page paces itself. Its source must reach the browser as an address: from a page opened from a file a `data:` address holding it, because Chrome refuses a Blob URL there, elsewhere a Blob URL. Where neither works, buffers scheduled one after another carry the sound, and `?audio=buffers` asks for them, for the tests. Look at the two bounds, `HIGH_SECONDS` and `LOW_SECONDS`:

```js
--8<-- "generated/listings/js/pumpWorklet.js"
```

A browser lets a page start sound only from a person's gesture, and not every event is one: a modifier alone activates nothing, and a context built there is born suspended. So the shell asks the browser whether the page is activated, where it can, and otherwise ignores modifiers, dead keys and keys held with a modifier. It builds and resumes the context in the event's own task, before the activation lapses, and keeps trying until the sound runs. Safari keeps the keyboard in its address bar for a page opened from a file; there one click starts the sound.

The stereo width, a setting of the shell, blends each side into the other: 100 percent is the Amiga's, channels 0 and 3 hard left and 1 and 2 hard right; 75, 50 and 25 percent bring them closer.

## The keys

Chapter 19 told how the shell turns `KeyboardEvent.code`, the name of a key's place, into the Amiga's [raw key codes](../glossary.md#raw-key-code), and what it leaves out. The joystick is a second path: four directions and the button, from the arrow keys or W, A, S and D, and Space, by place too. Space is the one fire key, a decision of the owner: whichever hand steers, the other has Space, and the second fire key, the key left of X, `KeyZ`, was the one whose letter changed with the layout, Z on an American keyboard and Y on a German one. A gamepad is merged into the same bits.

A button pressed and released between two VBlanks is held until the next VBlank, the shell's own latch, because the original samples a level and a browser times its events more coarsely. It is not the game's [latch](../glossary.md#latch), which keeps a tap of the fire button until the next input sample, nor the [keyboard assist](../glossary.md#keyboard-assist), which in the core lets a tap shorter than an input sample reach the tick exactly once (chapter 19).

A few keys the shell takes first: a listener in the capture phase, which sees a key before any other, takes H, F, the Escape that leaves fullscreen and any key while the help screen is up, and the game never sees them. H and F are letters inside the [line editor](../glossary.md#line-editor), which the shell asks the core about. A key held with Control, Alt or Command is the browser's.

The key left of 1 opens the [**diagnostics overlay**](../glossary.md#diagnostics-overlay), the shell's panel of figures over the picture. Chrome and Safari on a Mac with an ISO keyboard report that key as `IntlBackslash` and the key right of the left Shift as `Backquote`, the other way round from Firefox; so both codes open it in every browser, and neither reaches the game. Behind it lie the development keys, offered only while it is up, so that a digit typed into a name never goes to the shell; none is the game's. The commands are chapter 1's table; these are the shell's:

| Key | What it does | Why so |
|---|---|---|
| arrows, or W, A, S, D; Space | the stick; fire, and choose | one hand each, by place |
| H, F | the help screen, fullscreen | the shell's; letters in the line editor |
| Escape | the game's pause; leaves fullscreen | the browser keeps the second role |
| left of 1, or right of the left Shift | the diagnostics overlay | one key, two codes |
| 1; 2, 3; 4 | a score of 5,000; the save or the load dialog; a demo's recording | development, behind the panel |
| 5, 6, 7 | PAL, NTSC, the stereo width | development, behind the panel |

## What the shell stores

What the game writes, the [high-score file](../glossary.md#high-score-file) and the saved games, goes into the core's [overlay](../glossary.md#overlay-of-the-file-system) of written files, and the shell keeps them in the browser's `localStorage`, text kept under storage keys from one visit to the next. They go under one storage key as one list, because the order in which they were written is part of the order in which the [load and save dialog](../glossary.md#load-and-save-dialog) lists them (chapters 19 and 20). The shell stores the list whenever the core's count of writes moves; at the next start it puts the files back one by one, in that order, before the first VBlank, leaving out a file larger than its buffer, 8,192 bytes. The demo and its [seed file](../glossary.md#seed-file) are written files too.

| Storage key | What it holds |
|---|---|
| `wof:files` | the written files, each a name and its bytes in base64 |
| `wof:invertVertical` | the [vertical flip](../glossary.md#vertical-flip), handed to the core before the first VBlank |
| `wof:stereoWidth` | the stereo width |

The video standard is not stored: the page always starts on PAL.

The dialog's Exit Game ends the program on the machine; here it reloads the page, a decision of the owner, so the game starts again at the [story scroller](../glossary.md#story-scroller) as a program started anew. The shell checks for it after storing the files, so the saved games and the high scores survive; a game not saved is lost, as on the Amiga.

## Over the picture

Nothing covers the picture for good. Four layers can lie over it, bottom to top:

| Layer | When it shows | The keys it takes |
|---|---|---|
| the picture | always | the game's |
| the pause sign | while a mission is paused, the help screen down | none; P continues through the game |
| the help screen | at the start, and on H | every key while it is up |
| the diagnostics overlay | on the key left of 1 | the development keys |
| the key hint, a line at the foot | with the diagnostics overlay | none |

The help screen opens the page in place of a prompt for sound, which a browser starts only on a key or a click; its last line says that any key starts the sound and the game. That key does nothing else, a decision of the owner after F, as the first key, had started the sound and entered fullscreen at once. The screen goes only when the sound really runs, since its last line is a promise about the sound; after that, H brings it back and any key takes it away. Here is its list as the page carries it; look at the conditions in italics and at the two last lines, of which the page shows one:

```text
--8<-- "generated/listings/text/help-keys.txt"
```

Its text is 3.6 percent of the picture's height, at least 13 px; the sheet is then measured and made smaller until it fits 92 percent of the picture each way, so a window of 420 by 320 shows it whole. Over a running mission it asks for the pause and continues the mission when it goes, a decision of the owner; a pause it did not ask for stays. Outside a mission the game runs on beneath it.

The pause sign says PAUSED and, smaller, Press P to continue, centred on the picture, its big line 6 percent of the picture's height, so that it covers the same small part at any size. It shows the core's own pause, read once an animation frame after the VBlanks, so it comes up whatever asked for the pause: P, Escape, fullscreen left or an absence. Outside a mission it never shows, and while the help screen is up it hides, so that the sheet does not stand on it.

The diagnostics overlay exists so that the page's workings can be read off it rather than guessed at:

| Lines | What they show |
|---|---|
| clock to counters | the rates a second, whether the ticks are a quarter of the VBlanks, the stalls |
| standard to video | the box in CSS and device pixels, the two factors, the renderer, the time a present takes |
| input, audio | the joystick's five bits; the sound's state, its queue, the audio frames padded and dropped, the width |
| page | windowed or fullscreen, how often hidden, for how long the last time |
| core to demo | the arena, the files, the [stand-ins](../glossary.md#stand-in) reached; the aircraft, the pause, the flip, the game's rank and score |

## Fullscreen and the hidden page

F asks for the page's own fullscreen, on the whole page so that every layer stays in it, and F in it leaves. The request is made while the key is handled, because a browser grants fullscreen only to a gesture. In it no mouse cursor shows, a wish of the owner, since there is nothing to click.

Escape is both the game's pause and the browser's way out of fullscreen, which no page can take from it. So the shell keeps a [**leave rule**](../glossary.md#leave-rule): whenever fullscreen is left, it asks the core for the pause, a request and not a toggle, so that Escape always pauses. The browser's own fullscreen, from the window's button, shows only in a media query, `display-mode: fullscreen`, which the shell follows too. And the Escape that leaves fullscreen must not also reach the game, which would continue what the rule paused; so the shell drops an Escape pressed in its fullscreen and one arriving within half a second after, for a browser that hands the key over late.

A hidden page gets no animation frames, so its clock stops outright; the shell suspends the sound too. An [**absence**](../glossary.md#absence-of-the-page), the page hidden for a second or more, brings a mission back paused. A page hidden for a few milliseconds, as a window's change of state hides it, is no absence. The owner found why that matters: in Firefox put into fullscreen during a mission, the picture stood still and the sound was gone for good. The pause asked for on the way out had stopped the mission, and a resume made only once the audio context read suspended was skipped, in most tries, when the suspend landed after the page was back. So the pause is asked for on the way back, after a second, which reaches the same pass, as no VBlank runs meanwhile; and the shell records its own suspend and resumes on that record, never on the context's state, which then always ends running. Look at the way out and the way back:

```js
--8<-- "generated/listings/js/visibility.js"
```

## What the tests hold, and what only eyes can

The page tests open the page in Chrome and Firefox and hold its picture to the pixel against a screenshot, under a true scale factor and in a visible window, on both renderers; its frame rate at a screen's size; its clock, pause and sound through a moment hidden, an absence and fullscreen; the pause sign and the help screen. They run apart from the rest of the suite, whose load would disturb the clock and sound they measure. They cannot hold the real fullscreen on an unlocked screen, the smoothness of scrolling as a person sees it, or another display; the owner's look in real fullscreen in both browsers confirms those.

/// dev
[`web/video.js`](repo:web/video.js) puts on `window.__wofVideo` the path, the exact picture (`picture()`) and the canvas read back (`readDisplay()`), which on WebGL draws again first, since the drawing buffer is not kept after compositing. The 2D renderer's source canvas asks for `willReadFrequently: true`, a canvas drawn by the processor: in Firefox the accelerated one can drop what `putImageData` wrote and show black. At the owner's fullscreen the factors are 6 and 11, so the shader's positions reach 3,840 texels.
///

## What comes next

The chapter in one sentence: the shell is a small program that knows nothing of the game, keeps the game's time in VBlanks whatever the display does, puts its picture on the graphics processor in the machine's proportions, keeps its sound between two bounds, and takes for itself only the keys and the moments a browser imposes. Chapter 24 tells the tests: their layers, the two phases in which they run, and the page under a true scale factor.

## Further reading

The files named here are in the repository, [`github.com/sy2002/wof-wasm`](repo:).

- [`SPEC.md`](repo:SPEC.md#62-shell), section 6.2, "Shell"; [6.5, "Audio model"](repo:SPEC.md#65-audio-model), its last paragraph; [5, "Build"](repo:SPEC.md#5-build), step 4.
- [`re/notes/page-video.md`](repo:re/notes/page-video.md): ["Before: the two-step 2D path"](repo:re/notes/page-video.md#before-the-two-step-2d-path), ["The WebGL path"](repo:re/notes/page-video.md#the-webgl-path), ["The fallback, and the query"](repo:re/notes/page-video.md#the-fallback-and-the-query) and ["After"](repo:re/notes/page-video.md#after).
- [`re/notes/porting-m8.md`](repo:re/notes/porting-m8.md): ["The page and the fullscreen finding"](repo:re/notes/porting-m8.md#the-page-and-the-fullscreen-finding), ["The pause sign"](repo:re/notes/porting-m8.md#the-pause-sign) and ["The help screen"](repo:re/notes/porting-m8.md#the-help-screen); [`re/notes/porting-m3.md`](repo:re/notes/porting-m3.md), ["The shell's key map"](repo:re/notes/porting-m3.md#the-shells-key-map) and ["The development keys"](repo:re/notes/porting-m3.md#the-development-keys).
- [`web/clock.js`](repo:web/clock.js), [`web/video.js`](repo:web/video.js), [`web/audio.js`](repo:web/audio.js), [`web/input.js`](repo:web/input.js), [`web/main.js`](repo:web/main.js) and [`web/index.html`](repo:web/index.html).

Outside the repository: MDN's ["Window: requestAnimationFrame() method"](https://developer.mozilla.org/en-US/docs/Web/API/Window/requestAnimationFrame), ["AudioWorklet"](https://developer.mozilla.org/en-US/docs/Web/API/AudioWorklet), ["Fullscreen API"](https://developer.mozilla.org/en-US/docs/Web/API/Fullscreen%5FAPI) and ["Page Visibility API"](https://developer.mozilla.org/en-US/docs/Web/API/Page%5FVisibility%5FAPI); Glenn Fiedler's ["Fix Your Timestep!"](https://gafferongames.com/post/fix%5Fyour%5Ftimestep/), the accumulator's technique.
