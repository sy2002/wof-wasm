# M8: the sound effects engine

Milestone M8 of `SPEC.md` section 9, part 1 of two: the instrument and the sound effects
engine. Part 2 is the music player `songplay` with the song format of `wofsongs`. What the
engine is and does, observed, is `re/notes/sound.md`; the instrument, the headless
original's model of Paula, is in `re/notes/headless.md` ("The audio channels"). Addresses
use the standard load layout.

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
request for channel 6 in `channel_play` (`0x01EA3A`), a marked stand-in of part 2, and in
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

## The event log

`tools/sound_observe.py` over the 75 scripts (**observed**): per script its VBlanks, the
sample starts and restarts of the event log, the calls of `audio_irq`, the requests the
main program made deliverable, and the starts by sound and channel (`sound channel:count`).
The closed loops hold the port to every one of these events.

| Script | VBlanks | Starts | Restarts | Handler calls | Late | Starts by sound and channel |
|---|---|---|---|---|---|---|
| `deck` | 2001 | 1 | 24 | 25 | 0 | splash 2:1 |
| `flight` | 2401 | 4 | 33 | 36 | 0 | engine 0:1, grind.1 3:1, metal.clang.1 3:1, splash 2:1 |
| `climb` | 2800 | 5 | 30 | 34 | 0 | engine 0:1, grind.1 3:1, metal.clang.1 3:1, splash 2:2 |
| `lost` | 2600 | 5 | 12 | 16 | 0 | boom 2:1, engine 0:1, grind.1 3:1, metal.clang.1 3:1, splash 2:1 |
| `gameover` | 7000 | 13 | 37 | 47 | 0 | boom 2:3, engine 0:3, grind.1 3:3, metal.clang.1 3:3, splash 2:1 |
| `night` | 2401 | 4 | 33 | 36 | 0 | engine 0:1, grind.1 3:1, metal.clang.1 3:1, splash 2:1 |
| `select` | 1769 | 4 | 24 | 27 | 0 | engine 0:1, grind.1 3:1, metal.clang.1 3:1, splash 2:1 |
| `turns` | 3677 | 4 | 49 | 52 | 0 | engine 0:1, grind.1 3:1, metal.clang.1 3:1, splash 2:1 |
| `landing` | 3197 | 11 | 47 | 55 | 0 | engine 0:2, grind.1 3:3, metal.clang.1 3:3, screech 3:1, splash 2:2 |
| `island` | 3969 | 48 | 60 | 107 | 0 | engine 0:1, grind.1 3:1, machinegun 3:44, metal.clang.1 3:1, splash 2:1 |
| `fuel` | 23242 | 5 | 323 | 327 | 0 | boom 2:1, engine 0:1, grind.1 3:1, metal.clang.1 3:1, splash 2:1 |
| `run:flight-cheat` | 301 | 1 | 2 | 3 | 0 | splash 2:1 |
| `run:flight-control-c` | 301 | 1 | 2 | 3 | 0 | splash 2:1 |
| `run:flight-control-d` | 301 | 1 | 2 | 3 | 0 | splash 2:1 |
| `run:flight-control-f-twice` | 301 | 1 | 2 | 3 | 0 | splash 2:1 |
| `run:flight-control-f` | 301 | 1 | 2 | 3 | 0 | splash 2:1 |
| `run:flight-control-g` | 520 | 1 | 0 | 1 | 0 | splash 2:1 |
| `run:flight-control-key-first` | 301 | 1 | 2 | 3 | 0 | splash 2:1 |
| `run:flight-control-l` | 520 | 1 | 0 | 1 | 0 | splash 2:1 |
| `run:flight-control-r` | 300 | 1 | 0 | 1 | 0 | splash 2:1 |
| `run:flight-control-s` | 301 | 1 | 0 | 1 | 0 | splash 2:1 |
| `run:flight-escape-twice` | 301 | 2 | 0 | 2 | 0 | splash 2:2 |
| `run:flight-escape` | 300 | 1 | 0 | 1 | 0 | splash 2:1 |
| `run:flight-flip-then-load` | 1401 | 2 | 5 | 7 | 0 | engine 0:1, splash 2:1 |
| `run:flight-flip-then-restart` | 2100 | 1 | 1 | 2 | 0 | splash 2:1 |
| `run:flight-no-key` | 301 | 1 | 2 | 3 | 0 | splash 2:1 |
| `run:flight-plain-f` | 301 | 1 | 2 | 3 | 0 | splash 2:1 |
| `run:paused-control-c` | 420 | 1 | 0 | 1 | 0 | splash 2:1 |
| `run:paused-control-d` | 420 | 1 | 0 | 1 | 0 | splash 2:1 |
| `run:paused-control-f` | 420 | 1 | 0 | 1 | 0 | splash 2:1 |
| `run:paused-no-key` | 420 | 1 | 0 | 1 | 0 | splash 2:1 |
| `run:paused-restart` | 1001 | 5 | 7 | 11 | 0 | engine 0:1, grind.1 3:1, metal.clang.1 3:1, splash 2:2 |
| `guns_sea` | 2005 | 10 | 83 | 92 | 0 | engine 0:4, grind.1 3:1, machinegun 0:3, metal.clang.1 3:1, splash 2:1 |
| `guns_a` | 3189 | 12 | 154 | 165 | 0 | engine 0:4, grind.1 3:1, machinegun 0:3, machinegun 3:2, metal.clang.1 3:1, splash 2:1 |
| `bomb_a` | 3769 | 10 | 97 | 106 | 0 | boom 2:4, engine 0:1, grind.1 3:1, machinegun 3:2, metal.clang.1 3:1, splash 2:1 |
| `high_a` | 4521 | 30 | 78 | 107 | 0 | boom 2:4, engine 0:1, grind.1 3:1, machinegun 3:22, metal.clang.1 3:1, splash 2:1 |
| `rockets_a` | 4789 | 8 | 116 | 123 | 0 | boom 2:2, engine 0:1, grind.1 3:1, machinegun 3:2, metal.clang.1 3:1, splash 2:1 |
| `torpedo_a` | 2485 | 5 | 37 | 41 | 0 | engine 0:1, grind.1 3:1, metal.clang.1 3:1, splash 2:2 |
| `hit_a` | 8862 | 47 | 444 | 490 | 0 | boom 2:32, engine 0:1, grind.1 3:1, machinegun 3:11, metal.clang.1 3:1, splash 2:1 |
| `crash_a` | 4118 | 33 | 72 | 104 | 0 | boom 2:28, engine 0:1, grind.1 3:1, machinegun 3:1, metal.clang.1 3:1, splash 2:1 |
| `island_a` | 19481 | 124 | 600 | 718 | 0 | boom 2:68, engine 0:11, grind.1 3:2, machinegun 0:9, machinegun 3:10, metal.clang.1 3:2, scream 3:20, splash 2:2 |
| `bomb_b` | 4209 | 22 | 158 | 179 | 0 | boom 2:6, engine 0:3, grind.1 3:1, machinegun 0:2, machinegun 3:3, metal.clang.1 3:1, scream 3:5, splash 2:1 |
| `bomb_c` | 3861 | 21 | 188 | 208 | 0 | boom 2:6, engine 0:2, grind.1 3:1, machinegun 0:1, machinegun 3:4, metal.clang.1 3:1, scream 3:5, splash 2:1 |
| `rockets_c` | 4137 | 10 | 225 | 234 | 0 | boom 2:3, engine 0:1, grind.1 3:1, machinegun 3:3, metal.clang.1 3:1, splash 2:1 |
| `balloons_c` | 2401 | 4 | 35 | 38 | 0 | engine 0:1, grind.1 3:1, metal.clang.1 3:1, splash 2:1 |
| `torpedo_run` | 3125 | 5 | 46 | 50 | 0 | engine 0:1, grind.1 3:1, metal.clang.1 3:1, splash 2:2 |
| `bomb_pause` | 3770 | 12 | 104 | 114 | 0 | boom 2:4, engine 0:2, grind.1 3:1, machinegun 3:3, metal.clang.1 3:1, splash 2:1 |
| `bomb_flip` | 3769 | 10 | 97 | 106 | 0 | boom 2:4, engine 0:1, grind.1 3:1, machinegun 3:2, metal.clang.1 3:1, splash 2:1 |
| `bomb_restart` | 2777 | 6 | 44 | 49 | 0 | engine 0:1, grind.1 3:1, machinegun 3:1, metal.clang.1 3:1, splash 2:2 |
| `bomb_cheat` | 3769 | 10 | 97 | 106 | 0 | boom 2:4, engine 0:1, grind.1 3:1, machinegun 3:2, metal.clang.1 3:1, splash 2:1 |
| `kills_a` | 1517 | 4 | 21 | 24 | 0 | engine 0:1, grind.1 3:1, metal.clang.1 3:1, splash 2:1 |
| `wrecks_a` | 4665 | 4 | 67 | 70 | 0 | engine 0:1, grind.1 3:1, metal.clang.1 3:1, splash 2:1 |
| `burning_a` | 4073 | 7 | 168 | 174 | 0 | engine 0:1, grind.1 3:1, machinegun 3:3, metal.clang.1 3:1, splash 2:1 |
| `oil_d` | 3918 | 40 | 204 | 243 | 0 | boom 2:31, engine 0:1, engine 1:2, grind.1 3:1, machinegun 1:1, machinegun 3:2, metal.clang.1 3:1, splash 2:1 |
| `night_d` | 3918 | 40 | 204 | 243 | 0 | boom 2:31, engine 0:1, engine 1:2, grind.1 3:1, machinegun 1:1, machinegun 3:2, metal.clang.1 3:1, splash 2:1 |
| `airfield_e` | 5781 | 46 | 370 | 415 | 0 | engine 0:1, engine 1:2, grind.1 3:1, machinegun 3:40, metal.clang.1 3:1, splash 2:1 |
| `cruise_f` | 4173 | 9 | 200 | 208 | 0 | engine 0:1, engine 1:1, grind.1 3:1, machinegun 3:4, metal.clang.1 3:1, splash 2:1 |
| `torpedo_f` | 4510 | 12 | 165 | 176 | 0 | boom 2:1, engine 0:1, engine 1:3, grind.1 3:1, machinegun 1:1, machinegun 3:1, metal.clang.1 3:1, splash 2:3 |
| `crash_f` | 3730 | 32 | 57 | 88 | 0 | boom 2:26, engine 0:1, engine 1:1, grind.1 3:1, machinegun 3:1, metal.clang.1 3:1, splash 2:1 |
| `crash_side_f` | 3802 | 8 | 51 | 58 | 0 | boom 2:2, engine 0:1, engine 1:1, grind.1 3:1, machinegun 3:1, metal.clang.1 3:1, splash 2:1 |
| `rockets_f` | 3729 | 9 | 138 | 146 | 0 | boom 2:1, engine 0:1, engine 1:2, grind.1 3:1, machinegun 3:2, metal.clang.1 3:1, splash 2:1 |
| `cruise_g` | 5086 | 12 | 300 | 311 | 0 | boom 2:1, engine 0:1, engine 1:1, grind.1 3:1, machinegun 3:6, metal.clang.1 3:1, splash 2:1 |
| `destroyer_h` | 4878 | 19 | 266 | 284 | 0 | boom 2:8, engine 0:1, engine 1:2, grind.1 3:1, machinegun 1:1, machinegun 3:4, metal.clang.1 3:1, splash 2:1 |
| `ships_i` | 4502 | 41 | 212 | 252 | 0 | boom 2:31, engine 0:1, engine 1:2, grind.1 3:1, machinegun 1:1, machinegun 3:3, metal.clang.1 3:1, splash 2:1 |
| `battleship_j` | 3422 | 16 | 128 | 143 | 0 | boom 2:9, engine 0:1, engine 1:1, grind.1 3:1, machinegun 3:2, metal.clang.1 3:1, splash 2:1 |
| `battleship_k` | 4658 | 9 | 230 | 238 | 0 | boom 2:1, engine 0:1, engine 1:1, grind.1 3:1, machinegun 3:3, metal.clang.1 3:1, splash 2:1 |
| `destroyer_l` | 3790 | 10 | 169 | 178 | 0 | boom 2:1, engine 0:1, engine 1:2, grind.1 3:1, machinegun 1:1, machinegun 3:2, metal.clang.1 3:1, splash 2:1 |
| `japcarrier_m` | 4126 | 8 | 194 | 201 | 0 | boom 2:1, engine 0:1, engine 1:1, grind.1 3:1, machinegun 3:2, metal.clang.1 3:1, splash 2:1 |
| `destroyer_n` | 5138 | 39 | 293 | 331 | 0 | boom 2:31, engine 0:1, engine 1:1, grind.1 3:1, machinegun 3:3, metal.clang.1 3:1, splash 2:1 |
| `japcarrier_o` | 5738 | 86 | 237 | 321 | 0 | boom 2:4, engine 0:1, engine 1:4, grind.1 3:1, machinegun 1:1, machinegun 3:73, metal.clang.1 3:1, splash 2:1 |
| `countdown_b` | 8869 | 7 | 148 | 154 | 0 | engine 0:1, engine 1:1, grind.1 3:1, metal.clang.1 3:1, splash 2:3 |
| `countdown_c` | 8398 | 54 | 422 | 474 | 0 | boom 2:31, engine 0:2, engine 1:2, grind.1 3:2, machinegun 3:12, metal.clang.1 3:2, splash 2:3 |
| `enemy_a` | 10569 | 12 | 172 | 182 | 0 | engine 0:1, engine 1:2, grind.1 3:2, metal.clang.1 3:2, screech 3:1, splash 2:4 |
| `fight_a` | 36130 | 79 | 2059 | 2135 | 0 | boom 2:32, engine 0:13, engine 1:12, grind.1 3:2, machinegun 0:11, machinegun 3:4, metal.clang.1 3:2, splash 2:3 |
| `sunk_a` | 26400 | 16 | 368 | 383 | 0 | engine 0:1, engine 1:3, grind.1 3:1, metal.clang.1 3:1, screech 3:1, splash 2:9 |
| all 75 | | 1129 | 10219 | 11279 | 0 | |

The commands the scripts give the music player: 0, 1, 2, 4, 5, 6. Handler calls that saw
the requests of two channels or more: 69; that stopped a channel after keeping one: 0.

## The completeness list

The rows M4 wrote for M8 are gone: `0x026E3E`-`0x026EB7` (the sample pointers, now the eight
tables), `0x027368`-`0x027427` (the slots) and `0x027E6A`-`0x027F21` (the channel state);
every address the scripts write there during a mission is registered (**observed**, the
completeness tests of M4 to M6). `sound_init`'s saved vector (`0x027EE6`) and its interrupt
node (`0x027EEA`-`0x027EFF`) are written only at the program's start, outside a mission,
and are not registered: the port calls `audio_irq` and `soundfx_vblank` itself.

## What stands in, and where

- `M8 PART 2 STAND-IN: 0x01EA3A`, a sample asked for on channel 6: `channel_play` would
  first hand channel 2 over from the music (`channel2_to_music`, with a `Delay` of ten
  VBlanks). Nothing asks for channel 6.
- The music player: `music_start` still records its calls (M3's), part 2 ports it.

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
