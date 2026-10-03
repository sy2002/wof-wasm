Chapter 24
{ .chapter-kicker }

# The tests

Since chapter 1 this book has backed its claims with tests, many of them by name. This chapter shows the suite they belong to, whole. By its end you will know its seven layers, from one routine of the game to the finished page in two browsers, each with what it compares and against what; the machinery that lets a run of the suite give the same answers however its tests are spread over a machine; why the suite runs in two phases, and how one run of it is held to another; and what a green run proves, and what it leaves to the eye and the ear.

## Seven layers

The suite is about 930 tests under [`tests/`](repo:tests/), run by pytest, Python's framework for tests. Each [**layer**](../glossary.md#layer-of-the-suite) of it is a group of tests that holds the port at one scale against one reference, from a single routine to the page a browser shows. We arranged them so because a fault is best caught at the smallest scale that can see it, where its failure says the most: a routine and an input under the [oracle](../glossary.md#oracle), a pass in the [open loop](../glossary.md#open-loop), a picture's fault only in a browser. The instruments were told earlier; here they stand side by side.

| Layer | What it compares | Against | Told in |
|---|---|---|---|
| one routine | results, flags and touched memory, on random inputs | the original under the emulator; the ROM's floating point; the blitter model | 5, 12 |
| the original observed | the instrument's claims; the notes' findings; a key's effect | the headless original itself | 6, 19 |
| the front end | files, music and drawing calls, VBlank by VBlank | the headless original's run | 19 |
| the missions | state, drawing, chance, palettes and sound, every pass and tick | a recording of the original | 8, 18 |
| the whole game replayed | the state's hash after every input sample | hashes stored with a demo | 17 |
| the core itself | its two builds, save states, the page file, the generated files | itself and the repository | 22 |
| the page | requests, pixels, box, clock, sound, saves, pause, fullscreen | what the core gave it | 23 |

They follow the levels of the specification's section on verification, the drawing folded into the routine's layer and the sound into the missions'.

![Seven rows, one a layer, from one routine to the page, each with what it compares, against what and its chapter; a dashed frame round the first six for phase 1, another round the page for phase 2.](../figures/suite-layers.svg)

/// caption
The seven layers and the two phases they run in. A phase is a way of running the suite, not a layer: the first six layers run together over the processor cores, the page alone after them.
///

## One routine

Eight modules hold the routines one at a time: one for each milestone that ported [pure routines](../glossary.md#pure-routine), and one for the floating point. Each test is a [differential test](../glossary.md#differential-test) under chapter 5's oracle: the original's 68000 code under the emulator and the port's C in the [native library](../glossary.md#native-library) run on the same random inputs, and the results, the flags and every byte of memory either side touched are compared. The later modules also assert that their cases ran the parts of their routines no mission script reaches. The floating point is held to the ROM's own library, the port's built three ways; the blit through its [register programme](../glossary.md#register-programme), replayed by chapter 12's model of the [blitter](../glossary.md#blitter).

## The original observed

Seven modules hold the [headless original](../glossary.md#headless-original) to what it claims, and use it to observe what the notes say. Two runs of one [run description](../glossary.md#run-description) give the same [dump](../glossary.md#dump); an [observer](../glossary.md#observer) changes no step; the model of [Paula](../glossary.md#paula) only observes where nothing sounds. Beside them stand findings later chapters rest on: what a pass writes, how a map is drawn, what each key command does. A run description of [`tests/runs/`](repo:tests/runs/) that presses a key is compared with one that does not, the pair's baseline, so that whatever differs belongs to the key.

## The front end and the missions

One module replays the [front end](../glossary.md#front-end): the headless original's [schedule](../glossary.md#schedule) of the title sequence and the menus goes through the port VBlank by VBlank, the fades taking no time on either side, since the harness's fades contain no wait and the port's are a setting (chapter 7). Every file opened, every call of the music and every drawing call with its place and text must come at the same VBlank.

Seven modules fly the missions. Each [mission script](../glossary.md#mission-script) is first made into a [**recording**](../glossary.md#recording-of-a-script): the script run once under the headless original with a dump after every pass and tick, observers on the drawing routines, the reads of the [entropy stream](../glossary.md#entropy-stream) and the addresses each tick wrote. The port replays it in chapter 8's two loops, the open and the [closed](../glossary.md#closed-loop), and compares after every pass and tick what chapter 8 listed, the sound events among it. Beside the loops run the [completeness lists](../glossary.md#completeness-list), the setup of each of the fifteen maps and the capacities of the port's tables against all fifteen. A recording is the costliest thing the suite makes, and every test of its script shares it, as told below.

## The whole game, replayed

One module plays back chapter 17's demo, which [`tests/replays/`](repo:tests/replays/) keeps with its seed file, its schedule and a hash of the whole [save state](../glossary.md#save-state) after every [input sample](../glossary.md#input-sample), from the program's start to the end of the [attract demo](../glossary.md#attract-demo). It plays it in the native library and in Node's [WebAssembly](../glossary.md#webassembly), and both must give the stored hashes. So the whole game is played in one stored replay, a guard against any later change, and the page's own build is held to the hashes, where every other comparison runs natively. The state holds the display memory (chapter 22), so a change in what is drawn changes the hashes; but they are the port's own record, never compared with the original.

## The core itself

Eight modules test the port as a program. The same C sources build both forms of the [core](../glossary.md#core), and two modules hold them to each other: four VBlanks a tick, as many audio frames as the emulated time lasts, a state moved between cores, a foreign one refused, a WebAssembly that imports nothing, the same picture from both. A third saves states in the middle of a mission and goes on identically in a new core on another seed (chapter 22). The rest hold the page as one file that asks the network for nothing, the [generated files](../glossary.md#generated-file) against their regeneration, the ROM check's messages, the [keyboard assist](../glossary.md#keyboard-assist)'s rules, and the tests' own isolation, told below.

## The page

Two modules open the finished page in Chrome and Firefox, headless, from a `file://` address, because a double click is how the page is meant to run. A program in Node drives each browser through its own remote control, Chrome's DevTools protocol and Firefox's WebDriver BiDi, a standard of the W3C, both over the WebSocket that Node has built in, so that nothing need be installed. Keys are pressed through the driver, never dispatched from a script in the page: a scripted event activates nothing, and a page not activated may not start its sound (chapter 23). The browsers are muted from outside, which leaves the page's sound running.

A driver runs one session and prints what it measured as plain data; the tests in Python judge it. The geometry is read off the page's layout, never taken from the [shell](../glossary.md#shell)'s word, so that the shell cannot vouch for its own mistakes. What the sessions hold:

| Area | What is held |
|---|---|
| the file | it loads only itself; the console shows no error |
| the picture | the box in the machine's proportions, in both standards and after resizes; the canvas and a screenshot against the exact picture, on both [renderers](../glossary.md#renderer) |
| the clock | 50 VBlanks a second within 2 on PAL, 60 on NTSC |
| the sound | nothing built before an activating key; music and effects arriving as [audio frames](../glossary.md#audio-frame) that are not silent |
| the game | the stick's keys; a mission flown from the keyboard; the enemy's fighter found in the sky |
| the storage | a game saved and loaded after a reload; the demo recorded, reloaded and played as recorded |
| the shell's own | the help screen, the pause sign, a moment hidden, an [absence](../glossary.md#absence-of-the-page), fullscreen |

### Under a true scale factor

Only a screenshot shows what the browser did after the shell was finished. Chrome can pretend a screen's density through its protocol, but then it places the canvas on whole CSS pixels, and where the box's edge falls on half a CSS pixel the picture is shifted by a [device pixel](../glossary.md#device-pixel) or resampled once more, an artefact that would hide a real fault. So the picture is judged under a true scale factor, two device pixels to a CSS pixel as on a Retina screen, given on Chrome's command line, where Chrome behaves as on a real display; and the window is chosen so that the box's edge lands on half a CSS pixel, the case worth measuring.

Three questions are asked of a screenshot, none of which a few sample points could answer. Every pixel: at the centre of the block each framebuffer pixel is shown as, the screenshot must carry that pixel's colour. Where the picture lies: its position, fitted from its own colour edges to a fraction of a device pixel, must be the box the page reports. Whether the edges are hard: between the centres of two neighbouring blocks of different colour, at most one device pixel may be neither colour, where one smooth step would smear the edge over most of a block. Here is the first question; look at lines 6 and 7, which find the screenshot's pixel at the centre of every block across and down, and at the last line, which keeps the worst of the three colour channels:

```python linenums="1"
--8<-- "generated/listings/py/whole_picture_differences.py"
```

The three hold only where a framebuffer pixel is shown as at least three device pixels each way, and refuse below that rather than pass, for there a block's centre carries its neighbours and the fitted position wanders. A Retina window gives three; a window of ordinary density must be made large, as the headless Firefox runs do. Every session states which renderer drew it, and a test meant for one fails on the other.

### The frame time and the visible window

The frame-time test walks the page into a mission at a screen's size, the picture scrolling, and times every [animation frame](../glossary.md#animation-frame) for five seconds: the mean interval held to the display's refresh, a handful of late frames allowed, `present()` well under a millisecond, the WebGL renderer demanded. It measures the refresh first, on a blank page, because a page that misses every other refresh would otherwise judge itself by twice the refresh. It asks of the page only what every build of the shell offered, so that it can be pointed at the previous build, which lacks the WebGL renderer and must fail, for a test that has never failed may be unable to (chapter 8). In a visible Firefox the previous build fails it by every figure.

That visible window is the one check that can see a canvas fault of the graphics processor: headless Firefox composites in software, and the fault that once gave Firefox a black picture happens only there. It must stay in front and uncovered, because a covered window stops the page's clock and the tests then fail as if the page stood still, so it runs while the owner is away; and on a locked screen macOS moves no window into fullscreen, so its two fullscreen checks skip, saying why.

## What makes a run hold

What every module shares is in [`tests/conftest.py`](repo:tests/conftest.py): the options and the markers, the build, the core reached through ctypes, Python's way of calling C, with every function's types spelt out, and the [fixtures](../glossary.md#fixture) that keep each test apart from the others.

### Built once

pytest-xdist, a plugin for pytest, spreads the tests over [**test processes**](../glossary.md#test-process): processes of their own, each running a share of the tests with its own copy of the core. Each would build the port at its first test, and the build writes the native library in place, where a process that has it loaded while another rewrites it can crash or read a torn file. So the first test process to take a lock in the directory they all share builds and leaves a file to say so, and the others find the file and build nothing. The code calls a test process a worker, pytest-xdist's word; look at the lock on line 14 and at `needed()`, asked while it is held:

```python linenums="1"
--8<-- "generated/listings/py/once_per_run.py"
```

A [control](../glossary.md#control) of chapter 8, built from a changed copy of the sources into a library of its own, points the suite at that library, and nothing is built at all.

### A fresh core for every test

A process holds one copy of the core, and chapter 9 told how a test that left it changed broke the next one. So every test that takes the core starts from a [**fresh core**](../glossary.md#fresh-core): the core reset to its start and the state beside it put back. About two thirds of the suite takes the core, at under five thousandths of a second each. The core's initialisation resets its state, but not what a test sets from outside:

| Beside the core's state | Put back by |
|---|---|
| the VBlanks of a fade step and of a pass | the values read at the test process's first test |
| the [callbacks](../glossary.md#callback) into the test at a tick, a pass and the setup's end | clearing them |
| the [pokes](../glossary.md#poke), the map list's addresses | clearing them, and every replay as it ends |
| the [stand-ins](../glossary.md#stand-in) reached, the trace, the snapshots | clearing them |
| the sound event log, the files written | the core's own initialisation |
| the audio output rate | nothing: every test that renders names its rate |

Look at line 29, which reads the two settings once, at a test process's first test, and at lines 30 to 38, which run before every test that takes the core:

```python linenums="1"
--8<-- "generated/listings/py/fresh_settings.py"
```

So the start is rebuilt before every test, and a replay also clears what it set when it ends, normally or by an exception. [`tests/test_isolation.py`](repo:tests/test%5Fisolation.py) sets every item of the instrumentation, resets, and looks for each; the message of each assertion names what would have outlived its test:

```python linenums="1"
--8<-- "generated/listings/py/isolation_after_reset.py"
```

The rest of the shared state was audited the same way. A file a test writes goes into its test process's own directory; the files they all read are written by the build alone, before any test reads them; a module's caches live in one process; and a browser runs only in the page phase, one test at a time.

### Recordings made once

A recording is kept in the test process that made it, under its script, the VBlanks of a pass and its pokes, and every later test that needs it takes it from there. Spread over test processes, every process that ran one of a script's tests would record it again. So the collection hook gives the loop tests of one script one group, and pytest-xdist sends a group whole to one test process. The group is a [**marker**](../glossary.md#marker-of-a-test): a label pytest attaches to a test, by which a run selects, skips or groups it. Look at lines 4 to 7, which give each loop test its script's group; the rest of the hook comes back in the next section:

```python linenums="1"
--8<-- "generated/listings/py/pytest_collection_modifyitems.py"
```

Measured over the emulator tests with eight test processes:

| Tests sent | Recordings made in more than one process | Processor time beyond one each |
|---|---|---|
| any test to any free process | 60 | 4,225 s |
| a script's tests as one group | 35 | 1,165 s |

What is still made twice belongs to the completeness tests and a few others outside the loops. A recording on a busy machine also takes longer: the headless original's limits on the wall clock, which only ever end a run (chapter 6), were set from times measured with the suite in parallel.

![The collection on the left, whose hook gives a script's loop tests one group, sent whole to one test process; two test processes, each building once under the lock or finding the build done, a fresh core before each test, and a loop test's recording kept in the process.](../figures/test-process.svg)

/// caption
A test process's life: the build once for all, a fresh core before every test that takes one, and a recording made once and kept for its group.
///

## Two phases

The page tests measure time and pictures: the clock against the standard's rate, the start of the sound, the pictures a browser really shows. Load from outside the browser disturbs all three: seven page tests once failed while another program used more than a processor core, and passed on a quiet machine. The emulator tests keep every processor core busy. So the suite runs in two [**phases**](../glossary.md#phase-of-the-suite), parts run one after the other and never side by side: the emulator tests over the processor cores, then the page tests alone.

The suite registers three markers of its own. `page` marks the two browser modules, and `-m 'not page'` and `-m page` split the suite between the phases. `slow` marks about fifty of the longest differential runs, run only with `--slow`. `without_rom` marks the four tests that need no ROM: without the ROM the hook above marks every other test skipped with the ROM check's one message, nothing is built, and the message is printed again at the end, since pytest's own summary shows such skips only as a count by file.

The emulator phase runs eight test processes, one for each of the machine's processor cores, with `--dist loadgroup` to keep the groups. The times below were measured when the suite was smaller, 738 tests in the emulator phase and 827 serially; the next section's run is the present suite, so the two tables' counts are not to be compared.

| Run | Test processes | Wall time | Processor time | Result |
|---|---|---|---|---|
| serial, with `--slow` | 1 | 3:00:14 | about 10,800 s | 812 passed, 15 skipped |
| emulator phase, machine idle | 8 | 51:13 | 20,510 s | 736 passed, 2 skipped |
| emulator phase, the owner at work | 12 | 1:10:46 | 38,467 s | 734 passed, 2 failed |
| emulator phase, the owner at work | 6 | 1:35:57 | 27,219 s | 736 passed, 2 skipped |

Eight take about twice the serial processor time: a processor core runs slower when all are busy, and the recordings made twice add the rest. Twelve share processor cores, and their two failures were a recording past the old limit of a whole run; six leave cores idle. Both ran with the owner at work, so their times are upper bounds.

The serial run, every test in one process, was the first [**reference run**](../glossary.md#reference-run): the run another is held to. A run is held to it by its [**outcome set**](../glossary.md#outcome-set): every test by its id, its module, name and parameters, with its outcome, passed, failed, an error, or skipped with its reason. pytest writes it into a junit file, an XML report, and [`tools/junit_compare.py`](repo:tools/junit%5Fcompare.py) reads the first file as one set and all the others as the other, so that two phases are held to one serial run; it prints every test only one side has and every outcome that differs, and fails on any. Look at line 8, which drops what pytest-xdist appends to a grouped test's id, its group, which says where the test ran, not what it is:

```python linenums="1"
--8<-- "generated/listings/py/outcomes.py"
```

## One run, counted

The release's run of both phases, and a fresh clone of the repository with the ROM copied in and the setup run, its emulator phase on four test processes and without `--slow`:

| Run | Emulator phase | Page phase |
|---|---|---|
| the release | 804 passed, 3 skipped, in 1:00:54 | 103 passed, 20 skipped, in 22:33 |
| a fresh clone | 752 passed, 55 skipped, in 55:57 | 103 passed, 20 skipped, in 22:24 |

The release's three skips are two long runs of the headless original and the stored replay's recorder, each run only when asked for; the twenty are the visible window's nineteen tests and a lost WebGL context tried on the 2D renderer, which has none to lose. The visible window, run alone, skipped only its two fullscreen checks. The clone built the page byte for byte the same. Held to the older serial reference, no test's outcome differed; the tests on one side only were those added since, and a few renumbered or split, so the two-phase run became the reference.

The modules by layer, counted at this book's build from pytest's collection of the suite, which runs no test:

--8<-- "generated/tables/suite-layers.md"

## What a green run proves

A green run says this. After every logic tick and every pass of every mission script, in both loops, on every map the scripts reach, through the campaign's chain of missions, the saved games and the demo, the port's state, drawing calls, draws of chance, palettes and sound events are the original's, and every address the original writes in a mission is compared or listed with its reason. The front end agrees VBlank by VBlank. Every pure routine agrees with the original's over random inputs, the floating point with the ROM's. Both builds of the core are one program. The page shows the framebuffer exactly, keeps the clock and the sound, and keeps the saved games and the demo through a reload, in two browsers. That is chapter 1's definition, logic, picture and sound, wherever an instrument reaches.

What it does not say belongs to the proof. No pixel of a mission scene is compared with the original: the headless original draws nothing, and the drawing calls, the rows' palettes and the blitter model stand for the picture. That model is the chip's documented behaviour, not derived from the original, and no emulator exact to the cycle has checked it; the original's line routine is held to the port's through its line mode over random lines. Code no script runs is held by the oracle's cases where a test can hold it, or stands as a stand-in that would fail loudly. A fade's step and a pass's VBlanks are settings, one set by eye, the other filmed in a quiet scene (chapter 7). Fullscreen on a real screen and the smoothness of scrolling as a person sees it were the owner's eyes, and the sound as a person hears it the owner's ears (chapter 10).

Every test is named for what it holds, and the suite holds what each claim of a run rests on: that is why this book could cite a test by name for every such claim.

/// dev
The suite's switches are environment variables: `WOF_SLOW_HEADLESS=1` the two long determinism runs; `WOF_REPLAY_WRITE=1` records the stored replay anew; `WOF_CORE_LIBRARY` names a control's library; `WOF_FRAMES_PAGE` points the frame-time test at another build; `WOF_FIREFOX_VISIBLE=1` adds the visible window. The drivers are [`tests/pagecheck.mjs`](repo:tests/pagecheck.mjs), [`tests/pagescale.mjs`](repo:tests/pagescale.mjs), [`tests/pageframes.mjs`](repo:tests/pageframes.mjs) and [`tests/pagecheck_firefox.mjs`](repo:tests/pagecheck%5Ffirefox.mjs); the table of modules comes from [`book/tools/suite.py`](repo:book/tools/suite.py) and [`book/suite.toml`](repo:book/suite.toml).
///

## What comes next

The chapter in one sentence: the suite holds the port at seven layers, from one routine to the page in two browsers, keeps every test free of what ran before it, runs the page alone, and a green run proves chapter 1's definition wherever an instrument reaches, leaving a mission's pixels to the blitter model and the eye and the ear to the owner. Chapter 25 hands it to you: the setup, the ROM, the build and both phases on your own machine, the tools, and how to change the port without breaking the proof.

## Further reading

The files named here are in the repository, [`github.com/sy2002/wof-wasm`](repo:).

- [`SPEC.md`](repo:SPEC.md#8-verification), section 8, "Verification".
- [`re/notes/testing.md`](repo:re/notes/testing.md): ["A fresh core for every test"](repo:re/notes/testing.md#a-fresh-core-for-every-test), ["Duplicate recordings"](repo:re/notes/testing.md#duplicate-recordings), ["Times, and how many workers"](repo:re/notes/testing.md#times-and-how-many-workers) and ["Comparing runs"](repo:re/notes/testing.md#comparing-runs); [`re/notes/page-video.md`](repo:re/notes/page-video.md#what-the-page-tests-see), "What the page tests see".
- [`tests/conftest.py`](repo:tests/conftest.py), [`tests/m4compare.py`](repo:tests/m4compare.py), [`tests/picture.py`](repo:tests/picture.py), [`tests/runs/`](repo:tests/runs/) and [`tools/junit_compare.py`](repo:tools/junit%5Fcompare.py).

Outside the repository: [pytest](https://docs.pytest.org/en/stable/) and [pytest-xdist](https://pytest-xdist.readthedocs.io/en/stable/distribution.html); the [Chrome DevTools Protocol](https://chromedevtools.github.io/devtools-protocol/) and [WebDriver BiDi](https://w3c.github.io/webdriver-bidi/); Martin Fowler's ["Eradicating Non-Determinism in Tests"](https://martinfowler.com/articles/nonDeterminism.html), on tests that leave state behind.
