# M8: the sound effects engine and the music

Milestone M8 of `SPEC.md` section 9, in two parts: part 1 the instrument and the sound effects
engine, part 2 the music player `songplay` with the song format of `wofsongs` (from "Part 2:
the music player" below). What the engine is and does, observed, is `re/notes/sound.md`, and
the music's `re/notes/music.md`; the instrument, the headless original's model of Paula and
of CIA-A's timer A, is in `re/notes/headless.md` ("The audio channels", "The music's timer",
"The fade's wait"). Addresses use the standard load layout; the player's are the offsets of
`re/songplay.lst`.

Every statement is either **observed**, with the tool or test that shows it, or **read**,
which means it comes from the listing alone.

```text
tools/headless_paula.py  the headless original's Paula: the audio registers, DMA, INTENA and INTREQ,
                         the channels in a time of their own, the level-4 interrupt, the event log
tools/headless.py        the model installed, the channel events at every VBlank and the requests
                         after every server, audio_irq's rte executed by the driver
tools/sound_observe.py   every M4 to M6 script with the model: events by sound and channel
tools/reach_observe.py   --sound-markdown: the reach map of the engine's routines; src/sound.c
                         among the ported files of --cold
tools/extract_tables.py  `words` with `stride`, or with a list of `addrs`: instruction immediates
src/sound.c              the engine in the original's order: the slots 0x011F4E-0x0123DA and the
                         channels 0x01E8B8-0x01ED78
src/audio.c              the port's Paula: the same model, the mixer, the event log in test builds
src/input.c              wof_vblank: the channel events, then soundfx_vblank and its requests
src/mission.c            sounds_load with the sample pointers; the dialog's engine sample
src/tick.c, objects.c, player.c, front.c, dialog.c
                         the engine's callers, where M4 to M6 left a comment
src/records.def          the slot and the channel record; WOF_K_SOUND
src/mission.def          the slots, the channel records and the eight sample pointers
src/globals.def          the engine's counters and flags, the registered sound globals renamed
re/tables.toml           the slots' periods, volumes, repeats and lengths; the engine's targets
tests/m4compare.py       the event log and the model after every pass and tick, both loops
tests/m4state.py         a sample pointer to the port's handle
tests/test_sound.py      the model's own properties, and the port's PCM
tests/test_oracle_m8.py  every routine of the engine against the original, Paula compared too
tests/m8_renders.py      the port's PCM of five scripts in the closed loop, dist/m8-sound/*.wav
web/audio.js, core.js, main.js, overlay.js
                         the page takes the core's PCM by emulated time; the stereo width
```

## What decides what is ported: the reach map

`tools/reach_observe.py --m6 --blocks --setups` over the 75 scripts of M4 to M6 and the
setups of the fifteen maps, now with the model of Paula in the headless original, enters
every routine of the engine the game calls except those that nothing reaches
(**observed**; the tables are in the appendix below):

- **Every VBlank** from the program's start: `soundfx_vblank` (328,516 entries over all
  runs, in every window).
- **Every tick**: `engine_sound`, its `enemy_loudness` (`0x0122CE`), and `sound_channels`
  with `channel_play`, `channel_busy`, `channel_stop` and `channel_adjust` under it.
- **The one-shots**, in the tick: `sound_boom` (35 scripts), `sound_splash` (8),
  `sound_clang` (54), `sound_screech` (3), `sound_scream` (3), with `loudness_at` and
  `near_loudness`.
- **`audio_irq`**: 11,279 entries over 75 scripts, at the VBlank boundaries and after
  `soundfx_vblank` (phase V), and in four VBlanks a tick waited in (phase T).
- **Once**: `sound_init` at the program's start; `sounds_load` with `sound_slots_init` at
  every mission's setup; `sounds_free` and `sound_engine_free` in the outer loop; in a
  mission, `sound_engine_free` at the start of the load and save dialog
  (`run:flight-control-g`, `run:flight-control-l`, `run:flight-flip-then-load`) and
  `sound_engine_load` at its end (`run:flight-flip-then-load`).
- **Never**: `sound_slots_off`, `sound_shutdown` (the program's exit), `sound_play_rate`,
  `sound_wait_music`, `channel2_to_music`, `channel2_from_music`, `channels_stop` and
  `channel_ease`. None has a caller the game reaches (**read**; `re/notes/sound.md`).

The blocks no run executes in the ported routines are three (`--cold`, **observed**): the
request for channel 6 in `channel_play` (`0x01EA3A`), a marked stand-in, dead (part 2), and in
`soundfx_vblank` the music's flags for channel 2 (`0x01ECBE`) and the volume easing
(`0x01ECF8`), which only the uncalled `channel2_to_music` and `channel_ease` would set up.
Both are ported from reading and executed by the cases of `tests/test_oracle_m8.py`.

## The port

**The engine** (`src/sound.c`) is ported routine by routine in the original's order, with the
original's arithmetic: the triple calls of `sound_channels`, the high byte `st.b` sets in a
slot's word, the length word written into the low half of slot 7's long, the D0 the burst
leaves for the splash at `0x010D8E`, the D0 and D1 the scream leaves for `soldiers_hit`,
and `audio_irq`'s `INTENA` write with the bits of every channel handled so far. The custom
registers the original writes go to the port's Paula through `wof_paula_write` in the same
order; a sample pointer is a sound handle, `WOF_SOUND(file, offset)`: the file's index in
`sound_files` plus one in the top byte, the offset below. The samples are played from the
file system blob, where they lie as the disk has them, so the port loads nothing: its
`sounds_load` opens the files and keeps the lengths in the original's order, as it did in
M4, and now sets the handles and builds the slots. The engine's periods, volumes, lengths and
repeat counts are read out of the instructions' immediates at build time
(`re/tables.toml`, the `slot_*` and `engine_*` tables), and so are the engine's targets the
controls set, which M4 had written as numbers into `src/player.c`.

**The state.** The slots (`sound_slots`, eight records at `0x027368`), the channel records
(`sound_channels`, four at `0x027E6E`) and the eight sample pointers (one table of one
record each, `0x026E3E` and on) are tables of `src/mission.def`; the counters and flags
(`sound_vblanks`, `sound_installed`, `sound_intena`, `sound_dmacon`, `sound_flags`,
`g_027f18`, `g_027f1a`, `irq_store`) are registered globals; the slot's and the record's
sample pointers travel with the new kind `WOF_K_SOUND`, which `tests/m4state.py` converts
through the original's own eight pointers. The four globals M4 kept for the engine are
renamed to their listing names: `engine_volume`, `engine_volume_target`, `engine_period`,
`engine_period_base`. Paula's state (`wof_s.paula`: the registers, the DMA bits, where each
channel is in its cycle, `INTENA`, `INTREQ`) is part of the save state. The state version
is 10.

**The timing.** `wof_vblank` is the port of the VBlank as the headless original delivers it:
first the channel events of the VBlank that has passed (`wof_paula_boundary`), then
`soundfx_vblank` once `sound_init` has run, the requests it made deliverable, and then
`vblank_server`, the rest of the function. The model is the headless original's, so the
definitions of `re/notes/headless.md` ("The audio channels") are the port's.

**The mixer** runs inside the boundary's walk: the output frames of the VBlank that has
passed are mixed at its end, each from the byte every channel plays at the frame's instant,
so a channel `audio_irq` stops at a cycle's end falls silent at that instant and not a
VBlank later. Channels 0 and 3 go left and 1 and 2 right, each sample times the volume. The
frames wait in a queue outside the state until `wof_audio_render` takes them; that entry now
returns how many frames of emulated time it gave (the rest of the buffer is silence), and a
new rate drops what was mixed at the old one. The shell's calls therefore never touch what
the game computes, and a replay renders the same PCM however the shell asks for it.

**The page** (`web/audio.js`): every animation frame, after the VBlanks the clock ran, the
shell takes what the core mixed and queues it behind what is playing, in the worklet or as
scheduled buffers. The emulation's clock and the audio hardware's drift apart a little, so
the queue is kept between 40 and 300 ms: below, silence tops it up to 100 ms; above, the
core's PCM is dropped. What was mixed before the sound started is dropped when it starts.
The overlay shows the frames taken, how many were not silent, the loudest sample, and what
was padded and dropped. The stereo width is a setting of the shell, 100, 75, 50 or 25
percent, stepped with key 7 while the overlay is up and stored under `wof:stereoWidth`.

## How the port is held to the original

| Check | Test | What it covers |
|---|---|---|
| T2 | `tests/test_world.py`, `test_weapons.py`, `test_enemy.py`: every closed loop | every M4, M5 and M6 script, from the program's start: after every pass and every tick the sample starts and restarts since the previous step (kind, VBlank, pass, channel, file, offset, length, period, volume, instant) and the model's state (registers, DMA, the byte each running channel is at, the bytes left, the next instant, `INTENA`, `INTREQ`) are the original's, beside everything M4 to M6 compare; the slots and channel records as registered state |
| T1 | the attributed open loops of the same files | the same comparisons with the model set to the original's after every step |
| T3 | the completeness tests of M4 to M6 | the slots, the channel records, the pointers and the engine's globals are registered; the three rows that excluded them are gone |
| model | `tests/test_sound.py` | a silent run's steps unchanged by the model; a one-shot stopped by its second interrupt; a loop restarting at the instant its length and period give; no late request; the port's PCM silent up to the first start and not after it, 960 frames a VBlank at 48 kHz |
| V6 | `tests/test_oracle_m8.py` | every routine of the engine against the original over random slots, records, pointers and Paula states: the loudness helpers over every distance, `engine_sound` over 3,000 states, each slot setter over 1,000, `sound_channels` and the channel routines over 3,000, `audio_irq` and `soundfx_vblank` (the easing and the music's flags included) over 3,000, `sound_init`; registered state and Paula register by register |
| cold | `tools/reach_observe.py --cold` | the three regions above, each a marker or a note |
| page | `tests/test_page.py`, `tests/test_firefox.py` | the front end's PCM is silence; the flight's PCM through the worklet and the enemy flight's through the scheduled buffers (`?audio=buffers`) is not; in Chrome, Firefox and a visible Firefox window |
| core | `tests/test_core_native.py`, `test_core_wasm.py` | the frames `wof_audio_render` returns are the VBlanks' at the rate asked for, natively and in WebAssembly; the release core carries no test hook |

The negative controls, each run by changing the port in one place, building it into a
library of its own and running the closed loop of one script, then reverting; the first
step where each shows:

| Control | Script | The first |
|---|---|---|
| a period one too high (`soundfx_vblank`'s `AUDxPER`, `src/sound.c`) | `kills_a` | pass 2: the sea's start at VBlank 134 on channel 2 with period 801 for 800, and the channel's next instant |
| a volume one too high (`AUDxVOL` at a start) | `kills_a` | pass 2: the same start with volume 35 for 34 |
| the two slots of a pair exchanged (`sound_channels` takes the second first) | `guns_a` | pass 1120: the guns' start on channel 0 at VBlank 2371 missing, the engine playing on; `sound_dmacon` 0x8000 for 0x8001 |
| a channel's end delivered a VBlank late (`src/audio.c`, `cycle_end`) | `kills_a` | pass 40: the sea's restart at VBlank 212 for 211, and channel 2's position |
| the repeat length wrong: a restart takes `LEN` + 1 words (`src/audio.c`, `restart`) | `kills_a` | pass 40: channel 2's bytes left 6,678 for 6,676; in the event log from pass 81, the grinding's restart at instant 1,034,837,745 for 1,034,792,745 |

In `kills_a` the guns never fire over the engine, so the exchanged pair shows nowhere there;
`guns_a` fires at pass 1120.

### The page and the fullscreen finding

The user's finding of 2026-09-26, Firefox put into fullscreen during a mission: the picture
stood still and the sound was gone from then on. Measured with `tests/pagefullscreen.mjs`
(**observed**): a page hidden and shown again within 1 to 5 ms, as a window's change of
state does, got the pause the shell asked for on the way out, and its audio context,
suspended on the way out with the resume made only once the state read suspended, stayed
suspended for good when the suspend landed after the page was back: 9 of 12 tries in
Firefox, idle and beside a headless-original run alike, 5 of 6 in the M6 build, 7 of 8
headless; a hidden phase of 6 ms or longer never. The fix (`web/audio.js`, `web/main.js`):
the suspend and the resume go by the shell's own record, the pause is asked for on the way
back after an absence of a second or more, and leaving fullscreen asks for the pause as
`SPEC.md` 6.2 says, the browser's own fullscreen followed through the `display-mode` media
query. The page is driven through a moment hidden, a real absence and the browser's
fullscreen in both browsers, each span held to the clock, the picture, the pause and the
sound (`tests/test_page.py`, `tests/test_firefox.py`, `assert_the_page_goes_on`); the visible
fullscreen check needs an unlocked screen. Not a stall: at a Retina fullscreen size the
two-step scaling costs 32 ms a frame, half the frame rate, with the clock and the sound
holding (M9's scaling options).

### The pause sign

The owner's wish of 2026-09-27: whenever the game is paused, "PAUSED" over the picture and below it, a little smaller, "Press P to continue". It shows the core's own pause, `wof_paused`, which the shell reads once every animation frame after the VBlanks (`web/main.js`), so it comes up whatever asked for the pause - P, Escape, fullscreen left, the page back from a real absence - and goes with it; outside a mission the core is never paused and the sign never shows. It is a DOM element over the displayed canvas, `#paused` in `web/index.html`, in the key hint's font and colours; `web/video.js` puts its centre on the picture's and sets its size from the picture's height on every change of the box (PAUSED 6 percent of it, the second line 0.6 of that, at least 16 and 11 px), so it keeps to about a twentieth of the picture at any size. The diagnostics overlay, the key hint and the sound prompt lie above it and are untouched. No picture test is affected: every comparison of a screenshot or of the displayed canvas with the source canvas is made in the front end, where nothing is paused, and the mission's pictures are read off the source canvas, which no element covers. Tested in both browsers from the hold of a mission (`tests/pagefullscreen.mjs`, `assert_the_pause_sign_stands`): P and Escape each bring the sign up with the picture standing still and take it away with the mission going on; the absence of 1.5 s and the fullscreen left show it; paused in fullscreen and in a window of 420 x 320 it stays centred, a tenth of the picture at most, its letters at their minimum or more; at the title and in the rank menu, P or not, it never shows.

## The event log

`tools/sound_observe.py` over the 75 scripts, with the music (**observed**): per script its
VBlanks, the sample starts and restarts of the event log, the songs' (`wofsongs`) and the
effects' apart, the calls of the level-4 handlers (the player's and `audio_irq`), the
requests the main program made deliverable, timer A's ticks, the VBlanks of the fades' waits,
the level-4 vector and the timer's vector at step S, and the effects' starts by sound and
channel (`sound channel:count`). The closed loops hold the port to every one of these
events.

| Script | VBlanks | Music S/R | Effects S/R | Handler calls | Late | Timer ticks | Fades | At S | Effects' starts by sound and channel |
|---|---|---|---|---|---|---|---|---|---|
| `deck` | 2313 | 49/29 | 1/24 | 79 | 0 | 393 | 312 | `audio_irq`, no timer vector | splash 2:1 |
| `flight` | 2713 | 49/29 | 4/33 | 90 | 0 | 393 | 312 | `audio_irq`, no timer vector | engine 0:1, grind.1 3:1, metal.clang.1 3:1, splash 2:1 |
| `climb` | 3112 | 49/29 | 5/30 | 88 | 0 | 393 | 312 | `audio_irq`, no timer vector | engine 0:1, grind.1 3:1, metal.clang.1 3:1, splash 2:2 |
| `lost` | 2912 | 49/29 | 5/12 | 70 | 0 | 393 | 312 | `audio_irq`, no timer vector | boom 2:1, engine 0:1, grind.1 3:1, metal.clang.1 3:1, splash 2:1 |
| `gameover` | 7312 | 287/115 | 13/37 | 298 | 0 | 1726 | 312 | `audio_irq`, no timer vector | boom 2:3, engine 0:3, grind.1 3:3, metal.clang.1 3:3, splash 2:1 |
| `night` | 2713 | 49/29 | 4/33 | 90 | 0 | 393 | 312 | `audio_irq`, no timer vector | engine 0:1, grind.1 3:1, metal.clang.1 3:1, splash 2:1 |
| `select` | 2081 | 49/29 | 4/24 | 81 | 0 | 393 | 312 | `audio_irq`, no timer vector | engine 0:1, grind.1 3:1, metal.clang.1 3:1, splash 2:1 |
| `turns` | 3989 | 49/29 | 4/49 | 106 | 0 | 393 | 312 | `audio_irq`, no timer vector | engine 0:1, grind.1 3:1, metal.clang.1 3:1, splash 2:1 |
| `landing` | 3509 | 49/29 | 11/47 | 109 | 0 | 393 | 312 | `audio_irq`, no timer vector | engine 0:2, grind.1 3:3, metal.clang.1 3:3, screech 3:1, splash 2:2 |
| `island` | 4281 | 49/29 | 48/60 | 161 | 0 | 393 | 312 | `audio_irq`, no timer vector | engine 0:1, grind.1 3:1, machinegun 3:44, metal.clang.1 3:1, splash 2:1 |
| `fuel` | 23554 | 49/29 | 5/323 | 381 | 0 | 393 | 312 | `audio_irq`, no timer vector | boom 2:1, engine 0:1, grind.1 3:1, metal.clang.1 3:1, splash 2:1 |
| `run:flight-cheat` | 613 | 49/29 | 1/2 | 57 | 0 | 393 | 312 | `audio_irq`, no timer vector | splash 2:1 |
| `run:flight-control-c` | 613 | 49/29 | 1/2 | 57 | 0 | 393 | 312 | `audio_irq`, no timer vector | splash 2:1 |
| `run:flight-control-d` | 613 | 49/29 | 1/2 | 57 | 0 | 393 | 312 | `audio_irq`, no timer vector | splash 2:1 |
| `run:flight-control-f-twice` | 613 | 49/29 | 1/2 | 57 | 0 | 393 | 312 | `audio_irq`, no timer vector | splash 2:1 |
| `run:flight-control-f` | 613 | 49/29 | 1/2 | 57 | 0 | 393 | 312 | `audio_irq`, no timer vector | splash 2:1 |
| `run:flight-control-g` | 832 | 49/29 | 1/0 | 55 | 0 | 393 | 312 | `audio_irq`, no timer vector | splash 2:1 |
| `run:flight-control-key-first` | 613 | 49/29 | 1/2 | 57 | 0 | 393 | 312 | `audio_irq`, no timer vector | splash 2:1 |
| `run:flight-control-l` | 832 | 49/29 | 1/0 | 55 | 0 | 393 | 312 | `audio_irq`, no timer vector | splash 2:1 |
| `run:flight-control-r` | 612 | 65/34 | 1/0 | 67 | 0 | 477 | 312 | `audio_irq`, no timer vector | splash 2:1 |
| `run:flight-control-s` | 613 | 49/29 | 1/0 | 55 | 0 | 393 | 312 | `audio_irq`, no timer vector | splash 2:1 |
| `run:flight-escape-twice` | 613 | 49/29 | 2/0 | 56 | 0 | 393 | 312 | `audio_irq`, no timer vector | splash 2:2 |
| `run:flight-escape` | 612 | 49/29 | 1/0 | 55 | 0 | 393 | 312 | `audio_irq`, no timer vector | splash 2:1 |
| `run:flight-flip-then-load` | 1713 | 49/29 | 2/5 | 61 | 0 | 393 | 312 | `audio_irq`, no timer vector | engine 0:1, splash 2:1 |
| `run:flight-flip-then-restart` | 2524 | 378/138 | 1/1 | 316 | 0 | 2181 | 424 | `audio_irq`, no timer vector | splash 2:1 |
| `run:flight-no-key` | 613 | 49/29 | 1/2 | 57 | 0 | 393 | 312 | `audio_irq`, no timer vector | splash 2:1 |
| `run:flight-plain-f` | 613 | 49/29 | 1/2 | 57 | 0 | 393 | 312 | `audio_irq`, no timer vector | splash 2:1 |
| `run:paused-control-c` | 732 | 49/29 | 1/0 | 55 | 0 | 393 | 312 | `audio_irq`, no timer vector | splash 2:1 |
| `run:paused-control-d` | 732 | 49/29 | 1/0 | 55 | 0 | 393 | 312 | `audio_irq`, no timer vector | splash 2:1 |
| `run:paused-control-f` | 732 | 49/29 | 1/0 | 55 | 0 | 393 | 312 | `audio_irq`, no timer vector | splash 2:1 |
| `run:paused-no-key` | 732 | 49/29 | 1/0 | 55 | 0 | 393 | 312 | `audio_irq`, no timer vector | splash 2:1 |
| `run:paused-restart` | 1529 | 99/53 | 5/7 | 117 | 0 | 692 | 528 | `audio_irq`, no timer vector | engine 0:1, grind.1 3:1, metal.clang.1 3:1, splash 2:2 |
| `guns_sea` | 2317 | 49/29 | 10/83 | 146 | 0 | 393 | 312 | `audio_irq`, no timer vector | engine 0:4, grind.1 3:1, machinegun 0:3, metal.clang.1 3:1, splash 2:1 |
| `guns_a` | 3501 | 49/29 | 12/154 | 219 | 0 | 393 | 312 | `audio_irq`, no timer vector | engine 0:4, grind.1 3:1, machinegun 0:3, machinegun 3:2, metal.clang.1 3:1, splash 2:1 |
| `bomb_a` | 4081 | 49/29 | 10/97 | 160 | 0 | 393 | 312 | `audio_irq`, no timer vector | boom 2:4, engine 0:1, grind.1 3:1, machinegun 3:2, metal.clang.1 3:1, splash 2:1 |
| `high_a` | 4833 | 49/29 | 30/78 | 161 | 0 | 393 | 312 | `audio_irq`, no timer vector | boom 2:4, engine 0:1, grind.1 3:1, machinegun 3:22, metal.clang.1 3:1, splash 2:1 |
| `rockets_a` | 5101 | 49/29 | 8/116 | 177 | 0 | 393 | 312 | `audio_irq`, no timer vector | boom 2:2, engine 0:1, grind.1 3:1, machinegun 3:2, metal.clang.1 3:1, splash 2:1 |
| `torpedo_a` | 2797 | 49/29 | 5/37 | 95 | 0 | 393 | 312 | `audio_irq`, no timer vector | engine 0:1, grind.1 3:1, metal.clang.1 3:1, splash 2:2 |
| `hit_a` | 9174 | 49/29 | 47/444 | 544 | 0 | 393 | 312 | `audio_irq`, no timer vector | boom 2:32, engine 0:1, grind.1 3:1, machinegun 3:11, metal.clang.1 3:1, splash 2:1 |
| `crash_a` | 4430 | 49/29 | 33/72 | 158 | 0 | 393 | 312 | `audio_irq`, no timer vector | boom 2:28, engine 0:1, grind.1 3:1, machinegun 3:1, metal.clang.1 3:1, splash 2:1 |
| `island_a` | 19793 | 49/29 | 124/600 | 772 | 0 | 393 | 312 | `audio_irq`, no timer vector | boom 2:68, engine 0:11, grind.1 3:2, machinegun 0:9, machinegun 3:10, metal.clang.1 3:2, scream 3:20, splash 2:2 |
| `bomb_b` | 4521 | 49/29 | 22/158 | 233 | 0 | 393 | 312 | `audio_irq`, no timer vector | boom 2:6, engine 0:3, grind.1 3:1, machinegun 0:2, machinegun 3:3, metal.clang.1 3:1, scream 3:5, splash 2:1 |
| `bomb_c` | 4173 | 49/29 | 21/188 | 262 | 0 | 393 | 312 | `audio_irq`, no timer vector | boom 2:6, engine 0:2, grind.1 3:1, machinegun 0:1, machinegun 3:4, metal.clang.1 3:1, scream 3:5, splash 2:1 |
| `rockets_c` | 4449 | 49/29 | 10/225 | 288 | 0 | 393 | 312 | `audio_irq`, no timer vector | boom 2:3, engine 0:1, grind.1 3:1, machinegun 3:3, metal.clang.1 3:1, splash 2:1 |
| `balloons_c` | 2713 | 49/29 | 4/35 | 92 | 0 | 393 | 312 | `audio_irq`, no timer vector | engine 0:1, grind.1 3:1, metal.clang.1 3:1, splash 2:1 |
| `torpedo_run` | 3437 | 49/29 | 5/46 | 104 | 0 | 393 | 312 | `audio_irq`, no timer vector | engine 0:1, grind.1 3:1, metal.clang.1 3:1, splash 2:2 |
| `bomb_pause` | 4082 | 49/29 | 12/104 | 168 | 0 | 393 | 312 | `audio_irq`, no timer vector | boom 2:4, engine 0:2, grind.1 3:1, machinegun 3:3, metal.clang.1 3:1, splash 2:1 |
| `bomb_flip` | 4081 | 49/29 | 10/97 | 160 | 0 | 393 | 312 | `audio_irq`, no timer vector | boom 2:4, engine 0:1, grind.1 3:1, machinegun 3:2, metal.clang.1 3:1, splash 2:1 |
| `bomb_restart` | 3305 | 107/46 | 6/44 | 150 | 0 | 707 | 528 | `audio_irq`, no timer vector | engine 0:1, grind.1 3:1, machinegun 3:1, metal.clang.1 3:1, splash 2:2 |
| `bomb_cheat` | 4081 | 49/29 | 10/97 | 160 | 0 | 393 | 312 | `audio_irq`, no timer vector | boom 2:4, engine 0:1, grind.1 3:1, machinegun 3:2, metal.clang.1 3:1, splash 2:1 |
| `kills_a` | 1829 | 49/29 | 4/21 | 78 | 0 | 393 | 312 | `audio_irq`, no timer vector | engine 0:1, grind.1 3:1, metal.clang.1 3:1, splash 2:1 |
| `wrecks_a` | 4977 | 49/29 | 4/67 | 124 | 0 | 393 | 312 | `audio_irq`, no timer vector | engine 0:1, grind.1 3:1, metal.clang.1 3:1, splash 2:1 |
| `burning_a` | 4385 | 49/29 | 7/168 | 228 | 0 | 393 | 312 | `audio_irq`, no timer vector | engine 0:1, grind.1 3:1, machinegun 3:3, metal.clang.1 3:1, splash 2:1 |
| `oil_d` | 4230 | 48/26 | 40/204 | 293 | 0 | 379 | 312 | `audio_irq`, no timer vector | boom 2:31, engine 0:1, engine 1:2, grind.1 3:1, machinegun 1:1, machinegun 3:2, metal.clang.1 3:1, splash 2:1 |
| `night_d` | 4230 | 48/26 | 40/204 | 293 | 0 | 379 | 312 | `audio_irq`, no timer vector | boom 2:31, engine 0:1, engine 1:2, grind.1 3:1, machinegun 1:1, machinegun 3:2, metal.clang.1 3:1, splash 2:1 |
| `airfield_e` | 6093 | 48/26 | 46/370 | 465 | 0 | 379 | 312 | `audio_irq`, no timer vector | engine 0:1, engine 1:2, grind.1 3:1, machinegun 3:40, metal.clang.1 3:1, splash 2:1 |
| `cruise_f` | 4485 | 48/26 | 9/200 | 258 | 0 | 379 | 312 | `audio_irq`, no timer vector | engine 0:1, engine 1:1, grind.1 3:1, machinegun 3:4, metal.clang.1 3:1, splash 2:1 |
| `torpedo_f` | 4822 | 48/26 | 12/165 | 226 | 0 | 379 | 312 | `audio_irq`, no timer vector | boom 2:1, engine 0:1, engine 1:3, grind.1 3:1, machinegun 1:1, machinegun 3:1, metal.clang.1 3:1, splash 2:3 |
| `crash_f` | 4042 | 48/26 | 32/57 | 138 | 0 | 379 | 312 | `audio_irq`, no timer vector | boom 2:26, engine 0:1, engine 1:1, grind.1 3:1, machinegun 3:1, metal.clang.1 3:1, splash 2:1 |
| `crash_side_f` | 4114 | 48/26 | 8/51 | 108 | 0 | 379 | 312 | `audio_irq`, no timer vector | boom 2:2, engine 0:1, engine 1:1, grind.1 3:1, machinegun 3:1, metal.clang.1 3:1, splash 2:1 |
| `rockets_f` | 4041 | 48/26 | 9/138 | 196 | 0 | 379 | 312 | `audio_irq`, no timer vector | boom 2:1, engine 0:1, engine 1:2, grind.1 3:1, machinegun 3:2, metal.clang.1 3:1, splash 2:1 |
| `cruise_g` | 5398 | 49/28 | 12/300 | 364 | 0 | 391 | 312 | `audio_irq`, no timer vector | boom 2:1, engine 0:1, engine 1:1, grind.1 3:1, machinegun 3:6, metal.clang.1 3:1, splash 2:1 |
| `destroyer_h` | 5190 | 49/28 | 19/266 | 337 | 0 | 391 | 312 | `audio_irq`, no timer vector | boom 2:8, engine 0:1, engine 1:2, grind.1 3:1, machinegun 1:1, machinegun 3:4, metal.clang.1 3:1, splash 2:1 |
| `ships_i` | 4814 | 51/29 | 41/212 | 308 | 0 | 402 | 312 | `audio_irq`, no timer vector | boom 2:31, engine 0:1, engine 1:2, grind.1 3:1, machinegun 1:1, machinegun 3:3, metal.clang.1 3:1, splash 2:1 |
| `battleship_j` | 3734 | 51/29 | 16/128 | 199 | 0 | 402 | 312 | `audio_irq`, no timer vector | boom 2:9, engine 0:1, engine 1:1, grind.1 3:1, machinegun 3:2, metal.clang.1 3:1, splash 2:1 |
| `battleship_k` | 4970 | 53/31 | 9/230 | 298 | 0 | 414 | 312 | `audio_irq`, no timer vector | boom 2:1, engine 0:1, engine 1:1, grind.1 3:1, machinegun 3:3, metal.clang.1 3:1, splash 2:1 |
| `destroyer_l` | 4102 | 55/33 | 10/169 | 242 | 0 | 426 | 312 | `audio_irq`, no timer vector | boom 2:1, engine 0:1, engine 1:2, grind.1 3:1, machinegun 1:1, machinegun 3:2, metal.clang.1 3:1, splash 2:1 |
| `japcarrier_m` | 4438 | 56/33 | 8/194 | 266 | 0 | 437 | 312 | `audio_irq`, no timer vector | boom 2:1, engine 0:1, engine 1:1, grind.1 3:1, machinegun 3:2, metal.clang.1 3:1, splash 2:1 |
| `destroyer_n` | 5450 | 56/33 | 39/293 | 396 | 0 | 437 | 312 | `audio_irq`, no timer vector | boom 2:31, engine 0:1, engine 1:1, grind.1 3:1, machinegun 3:3, metal.clang.1 3:1, splash 2:1 |
| `japcarrier_o` | 6050 | 56/33 | 86/237 | 386 | 0 | 437 | 312 | `audio_irq`, no timer vector | boom 2:4, engine 0:1, engine 1:4, grind.1 3:1, machinegun 1:1, machinegun 3:73, metal.clang.1 3:1, splash 2:1 |
| `countdown_b` | 9181 | 49/29 | 7/148 | 208 | 0 | 393 | 312 | `audio_irq`, no timer vector | engine 0:1, engine 1:1, grind.1 3:1, metal.clang.1 3:1, splash 2:3 |
| `countdown_c` | 8710 | 49/29 | 54/422 | 528 | 0 | 393 | 312 | `audio_irq`, no timer vector | boom 2:31, engine 0:2, engine 1:2, grind.1 3:2, machinegun 3:12, metal.clang.1 3:2, splash 2:3 |
| `enemy_a` | 10881 | 49/29 | 12/172 | 236 | 0 | 393 | 312 | `audio_irq`, no timer vector | engine 0:1, engine 1:2, grind.1 3:2, metal.clang.1 3:2, screech 3:1, splash 2:4 |
| `fight_a` | 36442 | 49/29 | 79/2059 | 2189 | 0 | 393 | 312 | `audio_irq`, no timer vector | boom 2:32, engine 0:13, engine 1:12, grind.1 3:2, machinegun 0:11, machinegun 3:4, metal.clang.1 3:2, splash 2:3 |
| `sunk_a` | 26712 | 148/63 | 16/368 | 516 | 0 | 934 | 312 | `audio_irq`, no timer vector | engine 0:1, engine 1:3, grind.1 3:1, metal.clang.1 3:1, screech 3:1, splash 2:9 |
| all 75 | | 4492/2442 | 1129/10219 | 15995 | 0 | | | | |

The commands the scripts give the music player: 0, 1, 2, 4, 5, 6. Handler calls that saw the requests of two channels or more: 1171; that stopped a channel after keeping one: 0.

The effects are part 1's in every script. Three of them take a poke for it: `high_a`,
`island_a` and `bomb_b`, where soldiers come out of targets. `target_timers` (`0x011E18`,
`0x011E62`) times that by `vblank_total` (`0x0253CA`), `(vblank_total >> 4) & 31`, and the
fades' waits before the mission add their 312 VBlanks to that count, so a soldier comes out at
another tick and what follows differs: without the poke the first soldier of `bomb_b` comes
out at tick 625 and `island_a` no longer takes the island, nor wins the mission
(**observed**). The three scripts were made before the music played; they set `vblank_total`
back at the rank selection's end to what it is there without the fades, 97
(`tools/m5_scripts.py`, `WITHOUT_THE_FADES`), and their missions are again the ones they were
made for. The count with the fades is the original's own timing; a real machine leaves each
fade's wait up to three VBlanks earlier than the harness's rounds of four, which moves the
count by as much.

## The completeness list

The rows M4 wrote for M8 are gone: `0x026E3E`-`0x026EB7` (the sample pointers, now the eight
tables), `0x027368`-`0x027427` (the slots) and `0x027E6A`-`0x027F21` (the channel state);
every address the scripts write there during a mission is registered (**observed**, the
completeness tests of M4 to M6). `sound_init`'s saved vector (`0x027EE6`) and its interrupt
node (`0x027EEA`-`0x027EFF`) are written only at the program's start, outside a mission,
and are not registered: the port calls `audio_irq` and `soundfx_vblank` itself.

## What stands in, and where

- `M8 STAND-IN: 0x01EA3A`, a sample asked for on channel 6: `channel_play` would first hand
  channel 2 over from the music (`channel2_to_music`, with a `Delay` of ten VBlanks). The
  path is dead (**read**): the one caller the game reaches, `sound_channels`, asks for its
  pair index, 0 to 3 (`0x0120F8`, D6), and the other, `sound_play_rate`, has no caller.

The engine's routines the M4 to M6 ports left out with a comment are all called now; no
comment naming one is left (`src/tick.c`, `objects.c`, `player.c`, `front.c`).

## What the model leaves out

- **The wrap request's time.** Paula raises it when a cycle's last word is fetched, a word
  before it is played; the model raises it when the word has played. The difference is four
  samples; it moves a restart to the next VBlank only when a VBlank boundary falls inside
  them. When `audio_irq` stops a one-shot there, Paula cuts off the last word, which the
  model plays.
- **The length of a VBlank.** The model takes a VBlank as exactly 1/hz s; a real PAL frame is
  313 lines of 227 colour clocks, 71,051 of them, about 0.16 percent longer than 1/50 s. The
  shell's clock runs VBlanks at exactly 50 or 60 per second of emulated time too.
- **Paula's filters and the channels' analogue mixing.** The mixer takes each byte as it is,
  held for its period, and adds the two channels of a side; there is no low-pass filter.

## Part 2: the music player

The music is a player of its own, `songplay`, and its song data, `wofsongs`, both loaded with
`LoadSeg` by `music_start` (`0x0123DC`) and let go by `music_stop` (`0x012470`); what they are
and do, observed, is `re/notes/music.md`.

```text
tools/disasm_player.py    re/songplay.lst: the player's hunks with its symbols and relocations,
                          names from re/songplay_names.txt; not versioned, run after a checkout
tools/song_decode.py      wofsongs as the player reads it: songs, tracks, patterns, voices, samples
tools/hunk.py             stops at an overlay table, where LoadSeg stops
tools/headless_os.py      LoadSeg and UnLoadSeg as dos does them; ciaa.resource
tools/headless_paula.py   CIA-A's timer A in the channels' time; the read-back registers
tools/headless.py         the fade's wait; the player's rte; the vector and the timer at step S;
                          the segments' own memory area
tools/reach_observe.py    the player's routines and blocks from its load on, and its cold list
tools/sound_observe.py    the songs' and the effects' events apart, the ticks, the fades' waits
tools/extract_tables.py   entries read from songplay (`file = "songplay"`); bytes by `addrs`
src/music.c               music_start, music_stop, and the player
src/audio.c               timer A and its underflows in the boundary's walk; the level-4 vector;
                          the song data found in the file system blob
src/core.c                the player's DATA and the voices loaded as LoadSeg leaves them
src/records.def, mission.def, globals.def
                          the player's memory, the game's pointers to it, song_number,
                          music_playing; the kinds WOF_K_SONG and WOF_K_VECTOR
re/tables.toml            note_clocks, the durations, the volumes, periods and notes the
                          player's instructions carry, its DATA image, the song file's name,
                          the fade speed
tests/test_music.py       the instrument's claims, the port's timer and read-back registers,
                          the music VBlank by VBlank in the front end and the outer loop
tests/music_steps.py      the music's state before every VBlank, and the comparison
tests/test_oracle_m8.py   the player's routines against songplay's own code
tests/test_front_port.py  the front end's whole sound event log
tests/m4compare.py, m4state.py
                          the timer and the level-4 vector after every step; the music's tables
tests/pagecheck.mjs, pagecheck_firefox.mjs, pagemeasure.mjs, pagefullscreen.mjs, pagescale.mjs
                          the front end's waits with the fades; KeyM in flight
```

### What decides what is ported

The game gives the player commands 0, 1, 2, 4, 5 and 6 and no other (**observed**,
`tools/sound_observe.py` over every script; `tests/test_music.py` over the outer loop). So
`music_start` and `music_stop` are ported for real, with every routine of the player that
those commands and its two interrupts reach; the six commands the game never gives - 3
`_StopSong`, 7 to 9 and 12 the player's sound effects, 10 and 11 the pause - are marked
stand-ins, and with them `_StopSong` behind a fade while paused and `sfx_start` in the tick,
which only command 10 and command 7 could lead to. The routines the scripts enter, with their
entries, are in the appendix "The reach map of the player"; the regions of the ported
routines no run executes are listed below, each a marker or reached by an oracle test.

### The port

**The game's side** (`src/music.c`). `music_start` and `music_stop` are coroutines, because
each waits for a fade: a round of command 5 that answers other than 0 is followed by four
VBlanks, the rule the headless original follows (`re/notes/headless.md`, "The fade's wait").
They are called where the original calls them: `title_sequence` twice, `rank_select` at its
start and, with `music_stop`, at its end (`0x0184D6`), `high_score_screen`, and
`load_save_dialog` before its loader (`0x019146`, before the M7 stand-in). `fatal_exit`, the
third caller of `music_stop`, ends the program, which the page has no use for. M3's recording
of the calls is gone.

**LoadSeg, as far as the port keeps it.** The player's DATA hunk is the player's state: the
parts that change are four tables of `src/mission.def` (`player_head`, `player_vars`,
`player_tracks`, `player_song`), and the seven voices of the song data, the only part of it
the player writes, a fifth (`song_voices`). `music_start` loads them as `LoadSeg` would, the
player's from the hunk's image (`re/tables.toml`, `player_data`) and the voices from the file,
and `music_stop` lets them go; the game's four pointers to the segments are flags
(`songs_seglist`, `song_data`, `player_seglist`, `player_entry`). The rest of the song data is
read where the file system blob holds it: its pointers are relocated to its own DATA hunk, so
read as they stand they are offsets into it, and an offset is what the port keeps wherever the
original keeps a pointer into the song data (the kind `WOF_K_SONG`). A sample the player plays
is the sound handle `WOF_SOUND(8, offset)`, file 8 being the song data. `tests/m4state.py`
finds the player's tables through the segment list and the voices through `song_data`, as the
game does.

**The player** is ported routine by routine at the offsets of `re/songplay.lst`, with the
68000's arithmetic where it matters: `divu` that leaves its dividend when the quotient does
not fit, shifts by a register counted modulo 64, the release tick subtracted as a byte, the
track's bit set in `TrackState`'s top byte. It writes the channel's registers through the
addresses its track records hold, as the original does. Vibrato, arpeggio, the effect's
channel paths, the octaves of a sample of more than one and the commands no song gives are
ported from reading and held by the oracle tests; no song of the disk reaches them.

**The timer and the level-4 vector** (`src/audio.c`, `wof_s.cia`). Timer A is the model of
`re/notes/headless.md`: `wof_cia_write` takes `TALO`, `TAHI` and `CRA`, and the boundary's walk
delivers an underflow in time order with the channels' events, after them at an equal
instant, calling `SongInt` at the underflow's instant. The handler at `0x70` is a value of the
state, `WOF_L4_SYSTEM`, `WOF_L4_AUDIO_IRQ` or `WOF_L4_SONGINT`: `sound_init` puts `audio_irq`
there, `_OpenTimerInt` the player's handler and `_CloseTimerInt` back what it found, and
`wof_paula_deliver` calls whichever holds it. A change of the video standard carries the
timer's next underflow over into the new units. The four read-back registers ignore a write,
so the player's writes to `INTREQR` do nothing, as on the machine. The state version is 11.

**The page** plays the music through the same queue as the effects; nothing in the shell
changed. The drivers of the page tests leave the fades' waits room, about two seconds a
change of song.

### How the port is held

| Check | Test | What it covers |
|---|---|---|
| front end | `tests/test_front_port.py` | the idle front end and the one with five taps of fire: the whole sound event log, songs and effects, and timer A where the run ends |
| VBlank by VBlank | `tests/test_music.py`, `test_the_music_is_the_originals_after_every_vblank` | the idle front end, the one with fire, the outer loop after a game over - the high-score screen's song 0, the rank selection's song 4 faded in from it, `music_stop`, the second mission - and the same with the music switched off by Control-S in flight: after every VBlank's pass the game's pointers, `song_number`, `0x027430`, the player's DATA and the voices, converted as every table is; the whole event log; the timer |
| missions | every closed and open loop of `tests/test_world.py`, `test_weapons.py`, `test_enemy.py` | the event log up to each step, the front end's songs at the first; after every pass and tick the channels, timer A (latch, counter, running, one-shot, next underflow, vector, calls) and the level-4 vector; the music's tables, empty by step S |
| instrument | `tests/test_music.py` | from step S on the missions of `kills_a`, `guns_a` and `deck` with the player run and answered as idle are the same step for step, the VBlank counts less the fades'; at S the vector is `audio_irq` and the timer has none; a song's first notes start at the first tick after its command 2; the ticks come at the songs' tempo; a write to a read-back register changes nothing |
| port's model | `tests/test_music.py` | the port's read-back registers and its timer against the definition |
| V6 | `tests/test_oracle_m8.py` | `track_step` (4 x 1,500 states), `track_read` and `note_start` (2,000), `note_period` for every note the tables reach (792), `_ReadInstruments` for the five songs (100), `SongInt` in every state with commands 2, 5 and 6 (3,000), `SongIntHandler` (3,000), and a variant of the song data with what no song has (2,000): registered state, Paula and timer A compared; each test asserts that its cases reached the regions no run executes |
| page | `tests/test_page.py`, `tests/test_firefox.py` | the front end's music through the worklet and through the scheduled buffers; KeyM in flight silences the effects and a second press brings them back; in Chrome, Firefox and a visible Firefox window |

The negative controls, each a change of the port in one place built into a library of its own,
run through the idle front end's comparison and the closed loop of `kills_a`, then reverted:

| Control | Front end without input | Script, step |
|---|---|---|
| the tempo: timer A's latch high byte one too high (`event_tempo_hi`, `src/music.c`) | event 186, VBlank 1981: channel 3's start of song 2's sample at offset 8,450 missing, the notes after it later | `kills_a`, closed loop, pass 1: timer A's latch `0x39FF` for `0x38FF` |
| an instrument's period one too high (`note_period`) | event 0, VBlank 6: song 2's first note with period 428 for 427 | `kills_a`, closed loop, pass 1: channels 0 and 1 with periods 428 and 856 |
| a track's step wrong: the pattern read on two bytes too far after a command (`track_read`) | event 8, VBlank 105: a start on channel 3 where the original restarts channel 0 at 118 | `kills_a`, closed loop, pass 1: channel 2's sample and length |
| the fade speed one too high (`music_start`'s command 6) | event 410, VBlank 3896: song 1's first start missing, the port still fading | `kills_a`, open loop, pass 1: the front end's song events; the closed loop cannot follow the run, whose input then comes too early |
| a timer tick delivered a VBlank late (`timer_due`, `src/audio.c`) | event 0: song 2's first starts at VBlank 7 for 6 | `kills_a`, open loop, pass 1: the timer's next underflow and the song events; the closed loop cannot follow |

### The event log

The table of "The event log" above carries the songs' events beside the effects' (**observed**):
over the 75 scripts 4,492 starts and 2,442 restarts of the songs, 15,995 calls of the level-4
handlers, no request made deliverable outside a delivery point; at every step S the vector at
`0x70` is `audio_irq` and the timer has no vector. The fades' waits take 312 VBlanks in a
front end that goes straight to its mission, more where the outer loop comes round again
(`gameover`, the restarts and the reloads).

### The cold list

`tools/reach_observe.py --cold` over every script and setup of M4 to M6 (**observed**): the regions of
the player's ported routines that no run executed, each a stand-in marker or ported from
reading and reached by the cases of an oracle test, which asserts it; no region is
unclassified. The regions of the game's own routines are those of part 1, the channel-6
path now marked dead.

| Routine | Region no run executed | Stand-in marker, or what it is | Owed to |
|---|---|---|---|
| `segentry` `0000` | `0034`-`0063` | songplay+`0x0034`, command 7, `_PlaySfx` (+`0x00AA`) | M8 |
| `segentry` `0000` | `0034`-`0063` | songplay+`0x003A`, command 8, `_StopSfx` (+`0x01A8`) | M8 |
| `segentry` `0000` | `0034`-`0063` | songplay+`0x0042`, command 9, `_SfxStat` (+`0x01EA`) | M8 |
| `segentry` `0000` | `0034`-`0063` | songplay+`0x004A`, command 10, `_PauseMusic` (+`0x01FA`) | M8 |
| `segentry` `0000` | `0034`-`0063` | songplay+`0x0052`, command 11, `_RestartMusic` (+`0x0240`) | M8 |
| `segentry` `0000` | `0034`-`0063` | songplay+`0x005A`, command 12, `_AdjustSfx` (+`0x0252`) | M8 |
| `SongInt` `02a6` | `02b8`-`02bb` | songplay+`0x02B8`, `sfx_start` (+`0x0104`), an effect of command 7 | M8 |
| `song_step` `041e` | `04cc`-`04d9` | ported from reading; tests/`test_oracle_m8.py`, the tick: a song no track has started a note of, which ends it | |
| `track_step` `04f4` | `050e`-`051f` | ported from reading; tests/`test_oracle_m8.py`, `track_step`: the arpeggio's next offset, which no voice of wofsongs has on | |
| `track_step` `04f4` | `0538`-`0545` | ported from reading; tests/`test_oracle_m8.py`, `track_step`: the arpeggio's note | |
| `track_step` `04f4` | `054e`-`0597` | ported from reading; tests/`test_oracle_m8.py`, `track_step`: the vibrato between its limits, which no voice of wofsongs has on | |
| `track_read` `05d2` | `0646`-`064d` | ported from reading; tests/`test_oracle_m8.py`, the variant song data: a hold and a command byte passed over, which no song gives | |
| `event_end` `0682` | `0682`-`0687` | ported from reading; tests/`test_oracle_m8.py`, the variant song data: a track's end | |
| `event_tempo_lo` `06c2` | `06c2`-`06db` | ported from reading; tests/`test_oracle_m8.py`, the variant song data: the latch's low byte | |
| `event_hold` `06fc` | `06fc`-`0703` | ported from reading; tests/`test_oracle_m8.py`, the variant song data: a hold | |
| `note_start` `0704` | `0748`-`0757` | ported from reading; tests/`test_oracle_m8.py`, the variant song data: a sample of three octaves, a note in a lower one's part | |
| `note_start` `0704` | `07b0`-`07bf` | ported from reading; tests/`test_oracle_m8.py`, `note_start`: the volume scaled while an effect of command 7 plays | |
| `note_period` `07ea` | `0808`-`0809` | ported from reading; tests/`test_oracle_m8.py`, the note lookup: a note above the sample's octaves | |
| `CheckChannelInt` `08ae` | `0916`-`0929` | ported from reading; tests/`test_oracle_m8.py`, the level-4 handler: a channel an effect of command 7 has | |
| | a routine not ported, never entered | songplay+`0x0064` `_StopSong`, a fade while paused | M8 |
| | a routine not ported, never entered | songplay+`0x0064` `_StopSong`, command 3 | M8 |
| | no region: a value | songplay, a voice of wofsongs read as bytes | M8 |
| | no region: a value | songplay, a voice pointer that names no voice of wofsongs | M8 |
| | no region: a value | songplay, a division by zero, which traps | M8 |
| | no region: a value | songplay, a note outside `note_clocks` (+`0x0816`) | M8 |
| | no region: a value | songplay, a length past the durations (+`0x0712`) | M8 |
| | no region: a value | songplay, a sample without its chunk (+`0x099C`) | M8 |

### What stands in, and where

- `M8 STAND-IN: songplay+0x0034` to `+0x005A`: commands 7 to 12, which the game never gives.
- `M8 STAND-IN: songplay+0x0064`: `_StopSong`, command 3, and the same reached by a fade while
  paused, which only command 10 could set up.
- `M8 STAND-IN: songplay+0x02B8`: `sfx_start` in the tick, which only command 7 sets up.
- Guards that name no region, each for a value no song or state of the game produces: a voice
  pointer that names no voice, a division by zero, a note outside `note_clocks`, a length
  past the durations, a sample without its chunks, a voice read as bytes.

### What the model leaves out

- **The fade's wait.** A round of it is four VBlanks, the script waiting; a real machine
  leaves the spin within one VBlank of the fade's end, so the port's front end, like the
  headless original's, stands still up to three VBlanks longer per change of song.
- **The latch's low byte at power-up**, `0xFF`, the 8520's reset state: nothing writes it.
  With `0x00` every song would be 1.8 percent faster.

## Appendix: the reach map of the engine

Entries of the engine's routines per part of the run, summed over the 32 runs of M4 (its
scripts and its key runs), the 18 scripts of M5 and the 25 of M6, and the number of runs
that entered each, written by
`tools/reach_observe.py --m6 --load REACH.json --sound-markdown TABLE.md`:

### The head of the outer loop, before the rank selection

| Routine | Address | M4 (32) | M5 (18) | M6 (25) | Runs |
|---|---|---|---|---|---|
| `sounds_free` | `01346c` | 34 | 19 | 25 | 75 |
| `sound_engine_free` | `0134a4` | 34 | 19 | 25 | 75 |

### Mission setup, main program: the briefing's end to step S

| Routine | Address | M4 (32) | M5 (18) | M6 (25) | Runs |
|---|---|---|---|---|---|
| `sound_slots_init` | `011f76` | 33 | 20 | 25 | 75 |
| `sounds_load` | `013368` | 33 | 20 | 25 | 75 |

### Mission setup, the tick main runs itself

| Routine | Address | M4 (32) | M5 (18) | M6 (25) | Runs |
|---|---|---|---|---|---|
| `sound_channels` | `012066` | 33 | 20 | 25 | 75 |
| `engine_sound` | `012132` | 33 | 20 | 25 | 75 |
| `enemy_loudness` | `0122ce` | 33 | 20 | 25 | 75 |
| `channel_play` | `01ea28` | 99 | 63 | 75 | 75 |
| `channel_stop` | `01eac0` | 66 | 42 | 50 | 75 |
| `channel_busy` | `01eb2e` | 99 | 63 | 75 | 75 |

### Mission setup, VBlank servers

| Routine | Address | M4 (32) | M5 (18) | M6 (25) | Runs |
|---|---|---|---|---|---|
| `soundfx_vblank` | `01ec64` | 66 | 40 | 50 | 75 |

### A VBlank during a mission (phase V)

| Routine | Address | M4 (32) | M5 (18) | M6 (25) | Runs |
|---|---|---|---|---|---|
| `audio_irq` | `01ebaa` | 817 | 3030 | 7428 | 75 |
| `soundfx_vblank` | `01ec64` | 58008 | 82119 | 171191 | 75 |

### The inner loop beside `frame_update` during a mission (phase M)

| Routine | Address | M4 (32) | M5 (18) | M6 (25) | Runs |
|---|---|---|---|---|---|
| `sound_slots_clear` | `011f4e` | 11 | 1 | 0 | 12 |
| `sound_slots_init` | `011f76` | 1 | 0 | 0 | 1 |
| `sound_channels` | `012066` | 11 | 1 | 0 | 12 |
| `sounds_load` | `013368` | 1 | 0 | 0 | 1 |
| `sound_engine_load` | `01344e` | 1 | 0 | 0 | 1 |
| `sounds_free` | `01346c` | 4 | 0 | 0 | 2 |
| `sound_engine_free` | `0134a4` | 7 | 0 | 0 | 3 |
| `channel_stop` | `01eac0` | 33 | 6 | 0 | 12 |

### The tick during a mission (phase T)

| Routine | Address | M4 (32) | M5 (18) | M6 (25) | Runs |
|---|---|---|---|---|---|
| `sound_slots_clear` | `011f4e` | 15 | 19 | 28 | 54 |
| `sound_channels` | `012066` | 14037 | 20556 | 42892 | 75 |
| `engine_sound` | `012132` | 14022 | 20537 | 42864 | 75 |
| `enemy_loudness` | `0122ce` | 13999 | 20537 | 42864 | 75 |
| `near_loudness` | `0122f6` | 5 | 256 | 331 | 37 |
| `loudness_at` | `012306` | 5 | 256 | 331 | 37 |
| `sound_boom` | `012324` | 5 | 224 | 313 | 35 |
| `sound_splash` | `01233e` | 0 | 2 | 18 | 8 |
| `sound_clang` | `012354` | 15 | 19 | 28 | 54 |
| `sound_screech` | `012380` | 1 | 0 | 2 | 3 |
| `sound_scream` | `0123ac` | 0 | 30 | 0 | 3 |
| `engine_idle` | `01b9cc` | 14 | 19 | 27 | 54 |
| `channel_play` | `01ea28` | 294 | 1077 | 1782 | 56 |
| `channel_stop` | `01eac0` | 433 | 1202 | 2283 | 56 |
| `channel_busy` | `01eb2e` | 294 | 1077 | 1782 | 56 |
| `channel_adjust` | `01eb4c` | 3013 | 7884 | 20538 | 53 |
| `audio_irq` | `01ebaa` | 0 | 0 | 4 | 3 |
| `soundfx_vblank` | `01ec64` | 105 | 84 | 336 | 23 |

## Appendix: the reach map of the player

Entries of the player's routines per part of the run, summed over the 75 scripts of M4 to M6,
and the number of scripts that entered each, written by
`tools/reach_observe.py --m6 --load REACH.json --player-markdown TABLE.md`. `front` is the
title sequence, `rank` the rank selection with the fade at its end, `after` what follows a
mission: the high-score screen and the outer loop's next rank selection.

| Routine | Offset | `front` | `rank` | `after` | Runs |
|---|---|---|---|---|---|
| `segentry` | `0000` | 2475 | 4579 | 18 | 75 |
| `_FadeSong` | `0084` | 75 | 155 | 0 | 75 |
| `PlaySong` | `027c` | 150 | 78 | 6 | 75 |
| `_GetSongStat` | `029e` | 2175 | 4269 | 6 | 75 |
| `SongInt` | `02a6` | 11925 | 18229 | 3768 | 75 |
| `song_stop` | `02fe` | 75 | 155 | 0 | 75 |
| `song_fade` | `030a` | 7425 | 15345 | 0 | 75 |
| `track_fade` | `0348` | 9900 | 20460 | 0 | 75 |
| `song_begin` | `035a` | 150 | 78 | 6 | 75 |
| `song_step` | `041e` | 11700 | 17762 | 3768 | 75 |
| `audio_off` | `04da` | 75 | 155 | 0 | 75 |
| `track_step` | `04f4` | 46800 | 71048 | 15072 | 75 |
| `note_release` | `0598` | 300 | 3209 | 702 | 75 |
| `track_read` | `05d2` | 900 | 3521 | 726 | 75 |
| `event_next` | `0656` | 300 | 620 | 144 | 75 |
| `event_repeat` | `066a` | 0 | 0 | 4 | 1 |
| `event_voice` | `0688` | 900 | 704 | 203 | 75 |
| `event_tempo_hi` | `06aa` | 225 | 157 | 14 | 75 |
| `event_volume` | `06dc` | 75 | 76 | 12 | 75 |
| `note_start` | `0704` | 900 | 3521 | 726 | 75 |
| `note_period` | `07ea` | 525 | 3286 | 712 | 75 |
| `SongIntHandler` | `0848` | 975 | 3191 | 550 | 75 |
| `CheckChannelInt` | `08ae` | 3900 | 12764 | 2200 | 75 |
| `_PlaySong` | `092a` | 150 | 78 | 6 | 75 |
| `_ReadInstruments` | `0946` | 150 | 78 | 6 | 75 |
| `find_vhdr` | `099c` | 5775 | 3276 | 210 | 75 |
| `find_body` | `09ac` | 32175 | 18252 | 1170 | 75 |
| `_OpenTimerInt` | `09bc` | 75 | 0 | 6 | 75 |
| `_CloseTimerInt` | `0a50` | 0 | 77 | 0 | 75 |

Never entered: `_StopSong`, `_PlaySfx`, `sfx_start`, `_StopSfx`, `_SfxStat`, `_PauseMusic`, `track_rewind`, `_RestartMusic`, `_AdjustSfx`, `event_end`, `event_tempo_lo`, `event_hold`.
