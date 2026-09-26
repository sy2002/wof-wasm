# The sound effects engine

How the game plays its eight sound effects: the slots the tick fills, the channel layer
under them, the audio interrupt and the VBlank server, and what each effect is played with.
The music player, `songplay` with the song data `wofsongs`, is a separate executable and not
part of this note (M8 part 2). Addresses use the standard load layout; how the port takes the
engine is in `re/notes/porting-m8.md`.

Every finding is marked **observed**, with the instrument that shows it, or **read**, from
the listing alone. The instruments:

```text
tools/headless_paula.py   the headless original's Paula: the audio registers, DMA, INTENA and
                          INTREQ as the game writes them, the interrupts raised through the
                          level-4 autovector, the sound event log (re/notes/headless.md)
tools/sound_observe.py    every M4 to M6 script with the model: starts and restarts by sound
                          and channel, handler calls, late requests
tools/reach_observe.py    which routines and blocks the scripts execute (--blocks, --cold)
tests/test_oracle_m8.py   every routine of the engine against the port over random states
tests/test_sound.py       the model's own properties
```

## Two layers

The engine has two layers, both in the executable (**read**):

- **The slots** (`0x011F4E`-`0x0123DA`, beside the tick's other routines): eight slots of
  `0x18` bytes at `0x027368`, two per audio channel. The tick switches a slot on or off, and
  moves its volume and period; `sound_channels` (`0x012066`) gives each channel the first of
  its two slots that is on.
- **The channels** (`0x01E8B8`-`0x01ED78`): four records of `0x1E` bytes at `0x027E6E`, the
  hardware registers, the level-4 handler `audio_irq` (`0x01EBAA`) and the VBlank server
  `soundfx_vblank` (`0x01EC64`, installed under the name `SoundFX_IntHandler`).

`songplay` has sound-effect entries of its own (`_PlaySfx`, `_StopSfx`, `_SfxStat`,
`_AdjustSfx`); the game never calls them. Over all M4 to M6 scripts the calls into the
player are the commands 0 (open the timer), 1, 2, 4, 5 and 6 of `music_start`, never 7 to 9
or 12 (**observed**, the harness's `player_calls`).

## A slot, `0x18` bytes at `0x027368` + `0x18` x i

| Offset | Size | Meaning |
|---|---|---|
| `+0x00` | word | on when not zero; the tick sets it with `st.b`, which makes `0xFF00`, or copies a flag word |
| `+0x02` | long | the sample: a pointer into one of the eight effects |
| `+0x06` | long | its length in bytes; three setters write only the low word, `+0x08` |
| `+0x0A` | word | the period |
| `+0x0C` | word | the volume, 0 to 64 |
| `+0x0E` | word | the repeat count: the cycles to play, -1 for ever |
| `+0x10` | long | in the first slot of a pair: the sample the channel was last given, 0 for none |
| `+0x14` | long | in the first slot of a pair: the period and volume it was given, as one long |

`+0x10` and `+0x14` of the second slot of a pair are never used (**read**).

## The slots and what they play

`sub_011f76` (`0x011F76`), at the end of `sounds_load`, builds slots 0 to 6 from the sound
pointers and lengths; slot 7 is filled by whoever switches it on. The periods, volumes and
repeat counts are the immediates of the instructions (`re/tables.toml`, the `slot_*`
tables); a period is in colour clocks, so a byte lasts period / 3,546,895 s on PAL.

| Slot | Channel | Sample | Period | Volume | Repeat | Switched on by |
|---|---|---|---|---|---|---|
| 0 | 0 | `machinegun` | `0xC8` | 64 | -1 | `engine_sound`: the player's guns fire (`guns_firing`, `0x02536A`) |
| 1 | 0 | `Engine` | eased | eased | -1 | `engine_sound`: the engine, while its eased volume is not 0 |
| 2 | 1 | `machinegun` | `0xA0` | 57 | -1 | `engine_sound`: any enemy aircraft fires (`+0x12`, flying or attacking) |
| 3 | 1 | `Engine` | `0x14A` | by distance | -1 | `engine_sound`: the nearest enemy aircraft in states 1 and 2 |
| 4 | 2 | `boom` | `0x1F4` | by distance | 1 | `0x012324`: a bomb's or a rocket's burst, a wreck at rest (`object_spawn`) |
| 5 | 2 | `splash` | `0x15E` | by distance | 1 | `0x01233E`: something in the sea; aboard the carrier `engine_sound` makes it the sea itself, period `0x320`, volume 34, for ever |
| 6 | 3 | `machinegun` | `0x140` | by distance | -1 | `engine_sound`: the guns of the ground, from `draw_world`'s nearest distance (`0x027164`, `0x027166`) |
| 7 | 3 | set when used | | | | the lift moving (`Grind.1`, `0x1C2`, 64, for ever); its clang when it stops (`metal.clang.1`, length `0x1646`, `0x1C2`, 64, once); the wheels touching the deck (`screech`, `0x1A5A`, `0x15E`, 64, once); a soldier hit (`scream`, `0x19AC`, `0x17C`, half the distance's loudness, once) |

The first slot of a pair has priority (**read**, `sound_channels`): the guns drown the
engine, an enemy's guns its engine, a burst a splash, the ground's guns the lift. The
setters of slot 7 switch slot 6 off, and slot 6 on switches slot 7 off, so on channel 3
the last one set wins. A one-shot setter clears the first slot's `+0x10`, which makes
`sound_channels` start the sample again even where the same one plays. The burst's setter
does nothing before `boom` is loaded (`0x026E3E` zero).

Loudness by distance, with the aircraft at `player_x`, `player_y` (**read**, and held to
the original over every input by `tests/test_oracle_m8.py`):

- An enemy aircraft (`0x0122CE`): d = `|x - player_x| + |y - player_y|`, the smallest of
  the four records in states 1 and 2; with n = d >> 4, 0 for n above `0x2C`, else
  64 - 4n up to n = 5 and 64 - (n + 20) above.
- A burst, a splash, a scream (`0x012306` and `0x0122F6`): d is
  `|x - player_x| + |0x14 - player_y|`; n = d >> 5, 0 above 64, else 64 - n. The scream
  takes half of it.
  `0x012306` leaves `|0x14 - player_y|` in D1, and `soldiers_hit` (`0x011A8C`) and
  `0x010D8E` go on with the registers it leaves (`re/notes/porting-m5.md`).

The engine (slot 1, `engine_sound` `0x012132`): the volume `0x02542C` moves towards
`0x025428` by 1 up and 2 down each tick, the period `0x02542E` towards
`(pitch_target >> 7) + 0x02542A + (player_y >> 4)` by 20 up and 10 down; the comparisons
are unsigned. The controls set the two targets (`re/tables.toml`, `engine_targets`): at
rest volume 40 and period `0x328`, climbing or full speed 64 and `0x14F`, level 49 and
`0x181`, crashed 25 and `0x3C0`. So the engine rises in pitch as the aircraft climbs and
speeds up; nothing moves while paused or with the music off (**read**).

## A channel record, `0x1E` bytes at `0x027E6E` + `0x1E` x c

| Offset | Size | Meaning |
|---|---|---|
| `+0x00` | long | the sample; 0 when the channel is free |
| `+0x04` | long | the engine's VBlank count (`0x027E6A`) when the channel last stopped |
| `+0x08` | word | 1 while a start waits for `soundfx_vblank` |
| `+0x0A` | word | the length in words: the slot's byte length shifted right once |
| `+0x0C` | word | the period |
| `+0x0E` | long | the volume as 16.16; the upper word goes to `AUDxVOL` |
| `+0x12` | word | the repeat count as asked for |
| `+0x14` | word | the count `audio_irq` takes down; -1 plays for ever |
| `+0x16` | long | the volume to ease to, negative for none |
| `+0x1A` | long | the easing's step |

## The channel layer

- **`sound_channels`** (`0x012066`, from `logic_tick` and `sound_slots_clear`): for a slot
  whose sample is the one the channel was given, only the period and the volume are
  adjusted, and only when they changed (`0x01EB4C`, which also gives up any easing); for
  another sample it calls `0x01EA28` three times with the same arguments; with no slot on,
  paused or with the music off, a channel that was given a sample is stopped three times
  (`0x01EAC0`). **Read.**
- **`0x01EA28`**, a sample for a channel: a busy channel is stopped first, its request
  cleared and its interrupt enabled, and the record takes the sample and waits. The second
  and third calls therefore stop the start the first one set up and set it up again; each
  stop stamps the record with the current VBlank count.
- **`0x01EAC0`**, a channel stopped: its interrupt off, its DMA off, the record free, count
  -1, no easing, volume 0, the VBlank count stamped, and `AUDxPER` left at `0x7C`.
- **`soundfx_vblank`** (`0x01EC64`, VBlank server at priority 30, before `vblank_server`):
  counts `0x027E6A`; with the audio interrupts off, every record that waits and stopped at
  least two VBlanks ago gets `AUDxLC`, `AUDxLEN`, `AUDxPER` and `AUDxVOL` and its count, and
  the channels are switched on together with one `DMACON` write at the end; then the
  interrupts that were on, and all four. So a sample the tick asks for starts at the second
  VBlank after it, because the stops of the triple call stamp the current count (**read**).
- **`audio_irq`** (`0x01EBAA`, the level-4 autovector at `0x70`): the CPU's interrupts off,
  the long `0x027F1A` stored into the table at `0x026218` at the index `0x027F18` (neither is
  ever written, so it stores 0 at `0x026218`, **read**); then for every channel whose request
  is on and enabled: a free record, or a count that goes below zero, stops the channel; a
  count below zero plays on. The requests it saw are cleared. When it stops a channel it
  writes `INTENA` with the bits of every channel handled so far in this call, so a channel
  handled before it and kept loses its interrupt until the next `soundfx_vblank` turns all
  four on again (**read**; no script has two channels in one call).

A start raises the channel's request at once and each cycle's end raises it again (Paula's
behaviour, `re/notes/headless.md`), so a repeat count of N plays N cycles: the count goes
N - 1 at the start and below zero at the end of the N-th cycle. The lift's clang, a
one-shot, sees two handler calls, at its start and at its cycle's end, and is stopped by the
second (**observed**, `tests/test_sound.py`). A count of -1 never reaches the stop: the
engine, the sea aboard, the guns and the lift's grinding loop until `sound_channels` stops
their channel.

Never executed in any script, and not reachable from anything the game calls (**observed**,
the reach map; **read**, no caller): `0x011F64` (the slots off without the channels
following); `0x01E94C` (the engine shut down, from `close_libraries` at exit); `0x01E992`
(a sample given by a record with a rate in Hz, turned into a period with the NTSC clock
3,579,545); `0x01E9DE` (a wait on the music's flag or the fire button); `0x01E9F4` and
`0x01EA18` (channel 2 handed to the music and back, with a `Delay`); `0x01EAB4` (all four
stopped); `0x01EB94` (a volume easing started). `0x01EA28` hands channel 2 to the music
when asked for channel 6, which nothing does. The easing in `soundfx_vblank` and the music's
flags `0x027F14`-`0x027F16` therefore never act; the port has both, held to the original by
`tests/test_oracle_m8.py`.

## The samples

The eight files of `sounds/` are signed 8-bit PCM without a header. `sounds_load`
(`0x013368`) loads each into chip memory only while its pointer is 0 and keeps the length in
`sound_length` (`0x025572`); the pointers are at `0x026E3E` (`boom`), `0x026E42`
(`metal.clang.1`), `0x026E58` (`Engine`), `0x026E7A` (`Grind.1`), `0x026E96`
(`machinegun`), `0x026EA8` (`screech`), `0x026EAC` (`scream`) and `0x026EB4` (`splash`).
`0x01346C` frees all but the engine's between missions; the load and save dialog frees the
engine's too (`0x0134A4`) and loads it again when it closes (`0x01344E`), after which slot 1
still holds the old pointer until the next `sounds_load` (**read**; the key run
`run:flight-flip-then-load` reaches the reload, **observed**, the reach map).

## What the scripts play

`tools/sound_observe.py` over every M4 to M6 script gives the table in
`re/notes/porting-m8.md` ("The event log"). In every mission the sea aboard the carrier starts
on channel 2 two VBlanks after the mission's first tick, the lift grinds and clangs on
channel 3, and the engine starts on channel 0 when the lift is up (**observed**).
