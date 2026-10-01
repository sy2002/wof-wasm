# Running the test suite

The suite, 930 tests at `698d0f8` (807 emulator tests and 123 page tests; 827 when the runs below were measured), runs in two ways. Serially it takes about three hours with `--slow`, almost all of it single-threaded runs of the headless original under Unicorn and the port's replays of them, each independent and deterministic. In parallel, the emulator tests go over the machine's cores with pytest-xdist and the page tests run alone afterwards.

```text
.venv/bin/python -m pytest tests/ --slow                                          the serial run: the reference and the fallback
.venv/bin/python -m pytest tests/ --slow -m 'not page' -n 8 --dist loadgroup      phase 1: the emulator tests over the cores
.venv/bin/python -m pytest tests/ --slow -m page                                  phase 2: the page tests alone, both browsers headless
WOF_FIREFOX_VISIBLE=1 .venv/bin/python -m pytest tests/test_firefox.py -k visible the visible window, in the user's absence
.venv/bin/python tools/junit_compare.py REF.xml PHASE1.xml PHASE2.xml             two runs' outcome sets compared (--junitxml)
```

The two phases together are the serial run's tests, each exactly once: `-m 'not page'` and `-m page` split the collection, 807 and 123 tests with `--slow` at `698d0f8` (738 and 89 when the runs below were measured). `--dist loadgroup` is part of phase 1, not an option: without it the loop tests of one script go to different workers, which each record the script (below). pytest-xdist is 3.8.0, with execnet 2.1.2 under pytest 9.1.1, installed with `.venv/bin/python -m pip install pytest-xdist`; a serial run does not need it.

## Why the page tests run alone

The page tests measure the page's clock against the video standard's rate (50 VBlanks a second, within 2), the start of the sound and the pictures a browser really shows. Load from outside the browser disturbs all three: on 2026-09-26 seven page tests failed once while a browser of the user's own used more than a core, and passed on a quiet machine (`CONTROLLER.md`, "Pitfalls that cost time"). Phase 1 keeps every core busy, so the page tests never run beside it. `tests/test_page.py` and `tests/test_firefox.py` carry the marker `page` (a module-level `pytestmark`, registered in `tests/conftest.py`); no other module starts a browser. The visible Firefox window has a condition of its own: it must stay in front and uncovered, so it runs when the user is away.

Since M9 headless Chrome runs on the machine's GPU (`tests/chrome.mjs` no longer passes `--disable-gpu`): the page draws with WebGL, which headless Chrome gives only with its GPU, and the tests fail if a page falls back to Canvas 2D (`re/notes/page-video.md`). The frame-time tests (`tests/pageframes.mjs`) measure the page's frame rate at a screen-sized window, which load from outside disturbs even more than the clock; they run in the page phase with the rest.

## What happens once per run

Under pytest-xdist every worker is a process with a session of its own, and a session fixture runs once in each. The build writes files that the other processes read, so it runs once per run under a lock in the directory the workers share, `tmp_path_factory.getbasetemp().parent` (`once_per_run` in `tests/conftest.py`; `fcntl.flock`, nothing beyond xdist). The first worker to take the lock does the work; the others find it done.

- `built`: `tools/build.py --native` writes `tests/libwofcore.dylib` in place, and a process that has the library loaded while another rewrites it can crash or read a torn file. The first worker builds and leaves a marker, `wof-build.done`. Every parallel run measured built exactly once (with 8, 12 and 6 workers), logged by a plugin that recorded each `tools/build.py` a process started.

A serial run builds as it always did. The listings and the contact sheets are versioned and made by no test in place: `tests/test_generated.py` makes them into a directory of its own and compares them with the committed files byte for byte (`tools/disasm.py --out`, `tools/disasm_player.py --out`, `tools/ppkc.py --sheets`).

## Without the Kickstart ROM

`tools/rom.py` knows the image the project uses and gives one message when `original/kick.rom` is missing or another image: what is missing, the image's version, size and both checksums, and where to get it. The build stops with it before it writes anything, and the headless original and the oracle's reference (`tests/ffp.py`) raise it where they open the ROM. In the suite, `pytest_collection_modifyitems` in `tests/conftest.py` asks the check once per process and, when it fails, marks every test skipped with that message as its reason, except the few marked `without_rom` (`tests/test_generated.py`, the two message tests of `tests/test_rom.py`). Nothing is built and nothing runs that would crash or wait. The short summary folds a skip made by a marker by test file, and without `-rs` shows no reason at all, so `pytest_terminal_summary` prints the message once more at the end of the run, whatever the options.

## A fresh core for every test

A process holds one copy of the core's statics, shared by the `ported` fixture and by `NativeCore`. A test that leaves them changed hands the change to the next test its process runs, and under xdist that is another test in every run. Before the fix, a worker ran `tests/test_mission.py::test_the_setup_agrees_on_every_map`, which leaves the core in a mission, and then the shape oracles of `hellcat.shp` and `torpedo.shp`, the story scroller's ramps and the file loader, which failed on the core it left (the file loader found no `highscore`). Serially this is hidden: `tests/test_music.py` runs between them and leaves a fresh core behind.

`fresh_core` (autouse, `tests/conftest.py`) closes the class: a test that takes `ported`, itself or through a fixture built on it (`request.fixturenames`), gets `reset_core` before it runs, and a test that takes `native_core_factory` gets the settings back; tests without the core pay nothing and never build one. The settings are what `wof_init` leaves alone: the VBlanks of a fade step and of a pass, and the test hooks of `tests/shim.c`, which are ctypes callbacks a finished test may have left behind. They are read off the core at the first test of a process and put back before every such test. The audio output rate survives `wof_init` too and is left alone: every test that renders names its rate before the VBlanks it takes, and a new rate empties the queue. One fresh core costs 4.7 ms, and 557 tests take the core: about 2.6 s over the suite. `tests/test_music.py` keeps its own reset after its tests; it is redundant now and harmless.

The test instrumentation `tests/shim.c` sets lives in `src/trace.c`, beside the core's state, and survives `wof_init` as the settings do; the shim itself keeps no state but constant tables. A replay's pokes once outlived it: `bomb_c`'s closed loop poked `mission_number` 3 at the rank selection's end, and a worker that ran the front end's hand-over after it met the poke there (`mission_number: port 3, original 1`); serially `tests/test_front_port.py` runs first. A replay now clears what it set when it ends, normally or by an exception (`tests/m4compare.py`, `Replay.run`), and `fresh_settings` clears all of it before every test that takes the core. `tests/test_isolation.py` sets every item, resets, and finds none left; its slow test runs the finding's pair in one process. Item by item:

| State beside the core's | Set by | Put back |
|---|---|---|
| the VBlanks of a fade step and of a pass (`src/fade.c`, `src/core.c`) | `wof_set_fade_vblanks`, `wt_set_vblanks_per_pass` | `fresh_settings`, to the process's own values |
| the tick, pass and step-S hooks | `wt_set_tick_hook`, `wt_set_pass_hook`, `wt_set_step_s_hook` | `fresh_settings`, and a replay's end |
| the pokes | `wt_poke`, `wt_poke_reset`, `wt_poke_map`, `wt_poke_at`, `wt_poke_address` | `fresh_settings` (`wt_pokes_clear`), and a replay's end |
| the map list's addresses | `wt_map_addresses` | `fresh_settings` (`wt_map_addresses` with none), and a replay's end |
| the stand-ins reached | the core, `WOF_STANDIN` | `fresh_settings` (`wt_standins_reset`) |
| the trace records and the globals' snapshot of the front end's end | the core, `WOF_TRACE` | `fresh_settings` and `reset_core` (`wt_trace_reset`); `g_at_mission` fails without the snapshot instead of answering 0 |
| the sound event log | the core | `wof_init` (`wof_audio_init`) |
| the files written | the core | `wof_init` (`wof_fs_writes_reset`) |
| the audio output rate (`src/audio.c`) | `wof_audio_render` | left: every test that renders names its rate first |
| the step-S snapshot and the end-of-pass snapshot (`src/trace.c`) | the core, at step S and at a pass's end | `fresh_settings` (`wt_snapshots_reset`) only, never a reset inside a test, because the step-S snapshot must outlive a replay's trace resets until the setup comparison; a test that reads one it has not taken finds none and fails there (`port_mission`, `port_globals`, `g_at_mission`) |

## Shared state, audited

- **Files a test writes**: all under `tmp_path` or a per-process `tempfile.mkdtemp` - the recordings of `tests/test_world.py` (`RECORDING_DIR`), the `oil_d` dump of the enemy templates in `tests/conftest.py`, the dumps of `test_mission`, `test_headless` and `test_state_m4`, the programs `test_oracle_ffp` compiles. The `tests/m*_renders.py` scripts write `dist/m*-part*/` and `dist/m8-sound/`, but no test imports them.
- **Files read by all**: `dist/`, `tests/libwofcore.dylib`, `re/`, `original/`, `tests/runs/`; written only by the build above, once, before any test reads them; `re/` and `ref/` are read from the checkout as it is.
- **Module caches**: `RECORDINGS` and `RECORDED` (`tests/test_world.py`), `SEEN_SONGS` and `SEEN_SAMPLES` (`tests/m4state.py`), `_ENEMY_TEMPLATES` (`tests/conftest.py`), the two `lru_cache`s of `tests/test_music.py`: in-process, one per worker. `SEEN_SONGS` and `SEEN_SAMPLES` name the songs and samples a run's pointers point into, and are this run's alone: every `Replay` (`tests/m4compare.py`) and the music oracle empty both, because another recording laid its songs and samples out elsewhere and one of its starts below a freed block of this run would be taken for it (held by `tests/test_isolation.py::test_a_replay_attributes_samples_by_its_own_run_alone`; the finding in `re/notes/porting-m7.md`, "Paula's channel 0 after the save").
- **The core's statics**: one per process, made fresh for every test that takes them (above).
- **Browsers**: only in phase 2, one test at a time.
- **pytest's own cache and compiled test modules**: written atomically, as xdist expects.

## Duplicate recordings

A recording is cached per process (`tests/test_world.py`, `recorded`), keyed by script, pass rate and pokes. Serially a script is recorded once for all the tests that use it; in parallel every worker that runs one of those tests records it. Measured by a plugin that logged every run of a headless original with its key and CPU time, phase 1 with 8 workers:

| Distribution | keys recorded in more than one worker | CPU beyond one recording each |
|---|---|---|
| `--dist load` | 60 | 4,225 s |
| `--dist loadgroup`, loop tests grouped | 35 | 1,165 s |

The grouping: the tests of `test_world`, `test_weapons`, `test_enemy`, `test_campaign`, `test_loader` and `test_demo` whose parameters name a script carry `xdist_group('recording:<script>:<rate>')`, set in the collection hook of `tests/conftest.py`; `--dist loadgroup` sends a group to one worker. What remains is the three completeness tests, which serially reuse the recordings the loop tests made (`RECORDED`) and in parallel record on their worker whatever they do not find there, and a few tests that record a script outside the parametrised loops (`island` and `turns` in `test_world`, `kills_a` in `test_sound`, the soldiers' test in `test_weapons`, the pass rates of `test_loader`, and `demo_record` and a playback of the port's own recording in `test_demo`). The M6 completeness test is then the longest single test, 1,433 s; the M5 one takes 562 s. Neither sets the phase's wall time, which is bound by CPU (below).

## Times, and how many workers

| Run | wall time | CPU (user) | result |
|---|---|---|---|
| serial reference, `--slow`, on `2abd0f8` | 3:00:14 | about 10,800 s of test time | 812 passed, 15 skipped |
| phase 1, `-n 8 --dist loadgroup`, machine idle | 51:13 | 20,510 s | 736 passed, 2 skipped |
| phase 1, `-n 12 --dist loadgroup`, the user at the machine from noon | 1:10:46 | 38,467 s | 734 passed, 2 failed (the 600 s run limit, below) |
| phase 1, `-n 6 --dist loadgroup`, the user at the machine | 1:35:57 | 27,219 s | 736 passed, 2 skipped |
| phase 1, `-n 8 --dist loadgroup`, machine idle, M7 part 2's tests added | 59:51 | 25,746 s | 798 passed, 3 skipped |
| phase 2, `-m page` | 10:25 and 10:38 | | 76 passed, 13 skipped |
| phase 2, `-m page`, M9 (WebGL, the 2D runs and the frame-time test added) | 12:36 | | 97 passed, 20 skipped |
| phase 2, `-m page`, M7 part 2's page scenarios added (a save and its loads, the demo and two playbacks, in both browsers) | 22:47 | | 103 passed, 20 skipped |

The machine has 8 cores and 16 hardware threads. With 8 workers, phase 1 uses about twice the CPU time the same tests take serially: a core runs slower when all of them are busy, and the recordings made twice add the rest. 12 workers share cores and were slower still, and 6 leave cores idle; both were measured while the user worked at the machine, which the idle 8-worker run was not, so their times are upper bounds. **Use `-n 8`**: the two phases then take about an hour in all, against three.

## The wall-clock limits of the headless original

A run of the headless original is `Stuck` when the harness hears nothing from it, no wait point and no library call (the clock restarts at every stop), for `STUCK_SECONDS` of wall time, or when the whole run takes longer than `WALL_LIMIT` (`tools/headless.py`). Neither changes a run; both only end one. Under phase 1 a run takes longer than alone, so both were measured there, the first as the time spent inside the emulation between two wait points, which is what the limit counts:

| Limit | 8 workers, machine idle | 12 workers | 6 workers, the user at the machine | set to |
|---|---|---|---|---|
| between two wait points | 8.03 s | 7.95 s | 10.07 s | 60 s (was 10) |
| a whole run | 327 s | 600 s, reached twice | 701 s | 1,800 s (was 600) |

With 12 workers the recording of `island_a` reached the old limit of 600 s, and both of its loop tests failed as `Stuck: wall clock limit reached`; four runs took between 595 and 600 s. With 6 workers and the user working at the machine, both old limits would have been passed.

## Comparing runs

The two phases on this setup, phase 1 with 6 workers and phase 2 alone, gave the serial reference's outcome set exactly: 827 tests, 812 passed, 15 skipped, the 13 visible-window tests and the two `WOF_SLOW_HEADLESS` runs among the skips.

`tools/junit_compare.py` reads junit files (`--junitxml`): the first is one outcome set, every file after it together the other, so a two-phase run is held to a serial one. A test is its id, `module::name[parameters]`, with its outcome, a skip with its reason; `--dist loadgroup` appends `@<group>` to the id of a grouped test, and the script drops it. It prints the tests only one side has and every outcome that differs, and exits 1 on any difference.
