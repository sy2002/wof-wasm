# The music player and the songs

How the game plays its music: the player `songplay`, a small executable of its own, the song
data `wofsongs`, the game's calls into them, the timer that drives the songs, and the song
format. The sound effects are `re/notes/sound.md`; the port is `re/notes/porting-m8.md`.

Every finding is marked **observed**, with the instrument that shows it, or **read**, from the
listing alone. The instruments:

```text
re/songplay.lst            the player's listing (tools/disasm_player.py, names in re/songplay_names.txt)
tools/song_decode.py       wofsongs as the player reads it: songs, tracks, patterns, voices, samples
tools/headless.py          the headless original with "music": the real LoadSeg of both files,
                           ciaa.resource's timer A, the player's own level-4 handler
tools/headless_paula.py    the channels and CIA-A timer A in one time (re/notes/headless.md)
tools/sound_observe.py     per mission script: the songs' and the effects' events, the timer's
                           ticks, the fades' waits, the level-4 vector at step S
tests/test_music.py        the instrument held to its claims; the oracle tests of the player's
                           routines are in tests/test_oracle_m8.py
```

## The two files

`songplay` (5,148 bytes) is a hunk executable: CODE 2,696 bytes with 138 relocations and twenty
symbols, DATA 988 bytes with four relocations and its variables by symbol, BSS 4 bytes.
Addresses below are those of `re/songplay.lst`, which lays the hunks out at CODE `0x0000`,
DATA `0x1000` and BSS `0x2000`, so a CODE address is the offset into the hunk.

`wofsongs` (41,328 bytes) is a hunk file too: a CODE hunk of 276 bytes whose entry is a branch
to `lea DATA,a0; rts`, so that a call of it returns the song data, and whose other code, an
overlay loader of the linker's, nothing calls; a DATA hunk of 39,020 bytes in chip memory with
349 relocations, which holds the songs, the voices and the samples; a BSS hunk of 4 bytes; and
after the last hunk an empty overlay table, where `LoadSeg` stops (**read**; the harness's
`LoadSeg` loads exactly these, **observed**).

## The game's calls

The player is one entry, `segentry`, which takes a command in D0 (**read**,
`re/names.txt` "music"): 0 `_OpenTimerInt`, 1 `_ReadInstruments`, 2 `_PlaySong`,
3 `_StopSong`, 4 `_CloseTimerInt`, 5 `_GetSongStat`, 6 `_FadeSong`, 7 `_PlaySfx`,
8 `_StopSfx`, 9 `_SfxStat`, 10 `_PauseMusic`, 11 `_RestartMusic`, 12 `_AdjustSfx`. The game
gives only 0, 1, 2, 4, 5 and 6 (**observed**, `tools/sound_observe.py` over every script).

- **`music_start`** (`0x0123DC`, song file, song number; from `title_sequence`, `rank_select`
  and `high_score_screen`): with the files not loaded, it
  loads `wofsongs` and `songplay` with `LoadSeg`, calls the song data's entry for its address,
  and gives command 0; with them loaded, it gives command 6 with D1 2, a fade at speed 2, and
  then gives command 5 again and again until it answers 0, or, with `opt_music_off` set,
  takes the path of files not loaded (the branch at `0x0123FE`, below). Then command 1 with
  the song number and the song data, and, unless `opt_music_off` is set, command 2 and
  `0x027430` set. The game passes the song number and the song data in D1 and D2 to command 2
  as well; `_PlaySong` (`songplay+0x092A`) ignores them and plays the song command 1 set up
  (**read**).
- **`music_stop`** (`0x012470`, from `rank_select`, `load_save_dialog` and `fatal_exit`): with
  the files loaded, command 6 with 2, `0x027430` cleared, the same wait unless
  `opt_music_off` is set, command 4, and both files unloaded (`0x01249E`).

Where the songs fall in the front end (**observed**, the headless original with the music,
no input): song 2 from the program's start behind the story scroller (commands 0, 1 and 2
at VBlank 1); song 1 when the scroller ends, behind the title pictures (the fade at VBlank
3791, the song at 3895); song 4 in the rank selection (4980, 5084); `music_stop` when the
rank selection ends (6888, command 4 at 6992); song 0 on the high-score screen. Each change
fades the playing song first, and the wait for the fade is 104 VBlanks, 26 rounds of the
harness's rule (re/notes/headless.md, "The fade's wait"), in which 101 ticks come: the fade
takes 33 steps of three ticks, 32 from volume 32 to 0 and one that finds nothing left and
stops the song, 99 ticks or 2.04 s on PAL, and the wait notices the end at its next round.
On the real machine the screen stands still for about two seconds there. The fade lowers
the tracks' stored volumes only: a note that started before it keeps the volume it started
with until the fade's end switches the channels off, so a long held note (the drones of
songs 2 and 4) sounds at full volume through the fade and stops at its end (**read**).

`opt_music_off` (Control-S, the port's KeyM) is read only in flight (`ingame_keys`,
re/notes/keys.md), where no song plays; it silences the sound effects, and a song started
while it is set is not played: `music_start` reads the song's voices but gives no command 2,
and skips the fade's wait. The outer loop clears the flag before the rank selection, so it
can silence only the high-score screen of the game it was set in (**read**). A way to mute
the title's music would be the shell's, not the game's.

The branch at `0x0123FE` (**read**, `re/Wings.lst`, `re/songplay.lst`): with the files loaded
and `opt_music_off` set, `music_start` gives the fade and then takes the path of files not
loaded, `0x01240E`. It loads `wofsongs` and `songplay` a second time, the first copies
leaking, and gives the new player command 0 and command 1, no command 2. The new player's
`_OpenTimerInt` (`songplay+0x09BC`) ignores what `AddICRVector` answers: timer A keeps the
first player's `timer_node`, so every underflow runs the first player's `SongInt` on its own
DATA hunk, fading under command 6, while `0x70` gets the new player's handler and the first
player's goes into the new one's `saved_level4_vector`. Two players' DATA hunks are live then,
one under the timer and one under the level-4 handler. A later `music_stop` gives command 4 to
the new player: `RemICRVector` takes the first player's node off timer A, and `0x70` gets
back the first player's handler, inside a segment that leaked but still holds its code, so
`audio_irq` never comes back to `0x70`. Nothing reaches it. `opt_music_off` has two writers,
`not.b` at `0x01CD5A` in `ingame_keys`, in flight, where the music is not loaded (`rank_select`
unloads it at `0x0184D6` before every mission), and `clr.b` at `0x01006A` in `main`, which
every return to the rank selection passes: the outer loop goes back to `0x010066`, and the
game over reaches it through `high_score_screen` and `bra 0x010066`. `music_start` has four
callers, `title_sequence` at `0x01802E` and `0x018040`, `rank_select` at `0x018272` and
`high_score_screen` at `0x019868`; the last, the only one that can find the flag set, finds
the music unloaded and takes the path of files not loaded by the first test. The port holds
one player and marks the branch as a stand-in (`src/music.c`), going on as with the music
off: command 1 and no command 2 (`tests/test_music.py`).

## The timer

`_OpenTimerInt` (`0x09BC`, command 0) clears `PlayState` and `TrackState`, opens
`ciaa.resource` and gives `AddICRVector` bit 0, CIA-A's timer A, with an Interrupt node whose
code is `SongInt` (`0x02A6`); it starts timer A in continuous mode (CRA 1) without loading
it, and it puts its own level-4 handler, `SongIntHandler` (`0x0848`), at `0x70`, keeping the
vector it found, which is `audio_irq`, `sound_init`'s. `_CloseTimerInt` (`0x0A50`) removes the
ICR vector, switches the audio interrupts and DMA off and puts the kept vector back; the
timer itself runs on (**read**). So while the music is loaded the effects engine's
`audio_irq` does not run, and it is back for every mission, because the rank selection ends
with `music_stop` (**observed**, `tools/sound_observe.py` and `tests/test_music.py`: at every
mission's step S the vector at `0x70` is `audio_irq` and the timer has no vector). Both
routines write `0x0780` to `INTREQR` (`0xDFF01E`), a register that can only be read, as does
the stop path `audio_off` (`0x04DA`): evidently meant to clear the audio requests, the writes
do nothing on the machine and the requests stay pending (re/notes/headless.md).

Timer A counts at the E clock, 709,379 Hz on PAL. The songs set only the latch's high byte,
56 for songs 1 to 4 and 60 for song 0, with command `0xDD`, which also force-loads and starts
the timer; nothing writes the low byte, which keeps its power-up value `0xFF`. That value is
an assumption, the 8520's reset state: with `0x00` instead every tick would be 255 E cycles
shorter and every song 1.8 percent faster. So a tick comes every `0x38FF` + 1 = 14,592 E
cycles, 20.57 ms, 1.0285 VBlanks on PAL (**observed**, the harness's timer calls: 6,792 at
latch `0x38FF` over the no-input front end, 3,648,000 units apart); song 0's every
`0x3CFF` + 1 = 15,616 cycles, 22.01 ms. The first tick after `_OpenTimerInt` comes 65,536 E
cycles after the start, at the power-up latch (**observed**: VBlank 6 of the program).

## The tick: SongInt

`SongInt` runs per tick, after starting a waiting sound effect of `_PlaySfx`'s (which the
game never asks for), unless the music is paused; by `PlayState`:

| `PlayState` | Meaning | The tick |
|---|---|---|
| 0 | idle | nothing |
| 1 | a song asked for (`PlaySong`) | `song_begin` (`0x035A`): each track from its sequence's first entry, volume 32; the channels' DMA off; `PlayState` 2; then as 2 |
| 2 | playing | `song_step` (`0x041E`): the four tracks' `track_step`, each with its channel's bits; while `TrackState`, the tracks that have started a note since `_OpenTimerInt`, is still 0, `PlayState` goes to 0 and the channels off |
| 3 | stop asked for (`_StopSong`) | `PlayState` 0, the channels off |
| 4 | fading (`_FadeSong`) | `FadeCount` down; at below zero it reloads from `FadeSpeed` and every track's volume goes one lower; with none left above 0 the song stops (as 3); otherwise the tracks play on |

`track_step` (`0x04F4`), for one track (a record of `0x4A` bytes, `Track0Info` to
`Track3Info`): a note that sounds counts down its length; at its release tick the channel
is switched off unless the note is tied or held; arpeggio and vibrato would move the period,
but no voice of `wofsongs` has either on. With the length run out, the pattern's next
events are read (`track_read`, `0x05D2`) up to the next note, which `note_start` (`0x0704`)
plays: its length and release from the player's durations, the sample of the note's octave
from the voice's 8SVX body, `AUDxLC` at the sample and `AUDxLEN` over its one-shot and repeat
parts, the period from `note_period` (`0x07EA`), the track's volume, and DMA and the channel's
interrupt on. `CheckChannelInt` (`0x08AE`), from the player's level-4 handler, then sets
`AUDxLC` and `AUDxLEN` to the repeat part at the channel's first interrupt, so that a
sample plays its one-shot part once and loops its repeat part, or, for a sample without a
repeat part, marks the channel to go off at its next interrupt (**read**; **observed**: the
event log shows a start and then restarts at the repeat part's offset).

The period: `note_clocks` (DATA `0x1044`, 132 longs) gives per note the colour clocks of one
cycle of the waveform, a semitone apart; the note indexes it at `0x1134 + 4 x (note - 0x1B)`,
so notes from 0x1B less 60 on reach it. The period is that divided by the voice's
`samplesPerHiCycle` shifted by the octave (**read**; **observed**: the period 427, the first
of song 2, is `0x3572` / 32). The table holds NTSC colour clocks: read with 3,579,545 Hz its
notes are equal temperament at A 440 Hz within 0.3 cents on average, with PAL's 3,546,895 Hz
every one is 0.91 percent, 15.9 cents, flat (**observed**, the table against both clocks). So
on a PAL machine the music plays that much flat, as on a PAL Amiga; the port plays the table as
it stands.

## The song format (wofsongs's DATA hunk)

Every pointer is relocated; read at 0, it is an offset into the DATA hunk. `tools/song_decode.py`
decodes all of it (**read**, every field as the player uses it; the decoded songs are what the
harness plays, **observed**).

| Part | Layout |
|---|---|
| songs | 5 longs, song 0 to 4; song 3 is song 1 again |
| song | 4 longs, the sequences of tracks 0 to 3; at +0x10 the voice table, voice n at +0x10 + 4n, ended by 0. Voice 0 is in every song the rest voice, the record at `0x000CC` without a sample, whose note takes its length from the durations and starts nothing (`note_start` skips to `0x07DC` when the track has no VHDR); two patterns select it with `0xDC 0`, `0x003AC` in song 0's track 0 (sequence entries 0, 2, 8 and 10) and `0x00A02` in song 2's track 3 (all 20 entries) (**observed**, `tools/song_decode.py`) |
| sequence | entries of 6 bytes: the pattern (long) and a transpose (word) |
| pattern | events of 2 bytes. A byte below `0xD9` is a note, bit 7 tying it to the one before; the second byte is its length's index into the player's durations. `0xD9` next sequence entry, `0xDA` the track ends, `0xDB` the sequence from its start, `0xDC` voice n, `0xDD` timer A's latch high byte, `0xDE` its low byte, `0xDF` volume, `0xE0` hold (1 keeps a note past its release); from `0xE1` on the pair is skipped |
| voice | `0x2E` bytes: +0 VHDR and +4 BODY of its sample, +8 notes per octave (the player writes `0x53 / ctOctave` there), +0xA the sample's 8SVX FORM, +0x12 to +0x2C vibrato and arpeggio, both off in every voice |
| sample | an IFF 8SVX FORM: VHDR and BODY |

The durations (DATA `0x1254`, 20 pairs of a note's length in ticks and the tick of its
release, counted from the note's start):
(96, 86), (48, 43), (32, 28), (64, 58), (24, 21), (72, 64), (12, 10), (84, 75), (60, 54),
(36, 32), (6, 5), (90, 81), (78, 70), (66, 59), (54, 48), (42, 38), (30, 27), (18, 16),
(8, 7), (16, 14).

The songs, each on four tracks that loop (`0xDB`):

| Song | Symbol | Where | Sequence entries | Voices |
|---|---|---|---|---|
| 0 | `song1` | the high-score screen | 17 | SyntheBass, omlead, RoomBrass2, BassDrum3, sdrum1 |
| 1 | `song2` | the title pictures | 13 | the same five |
| 2 | `song3` | the story scroller | 29 | the five and Mechanic1 |
| 3 | `song2` | never asked for | 13 | as song 1 |
| 4 | `song4` | the rank selection | 15 | the five and Mechanic1 |

The tempo, from the note lengths the songs use (**read**, `tools/song_decode.py`): 96 ticks
is a whole note, 24 a quarter, 8 a triplet eighth, 6 a sixteenth. Songs 1 to 4 tick every
20.57 ms, a quarter note 494 ms, 121.5 beats a minute; song 0 every 22.01 ms, a quarter note
528 ms, 113.6 beats a minute. Song 2, the scroller's, is almost all whole notes; song 4, the
rank selection's, runs in sixteenths and eighths over held notes.

The samples, one octave each (`ctOctave` 1), the one-shot part played once and the repeat
part looped:

| Sample | One-shot | Repeat | Samples a cycle | Rate |
|---|---|---|---|---|
| BassDrum3 | 3,400 | 0 | 32 | 8,363 Hz |
| sdrum1 | 1,642 | 0 | 32 | 8,363 Hz |
| RoomBrass2 | 1,768 | 6,548 | 8 | 8,363 Hz |
| SyntheBass | 7,644 | 384 | 8 | 8,363 Hz |
| omlead | 3,434 | 3,042 | 16 | 4,181 Hz |
| Mechanic1 | 7,374 | 64 | 32 | 8,363 Hz |

## What the front end plays

Over the no-input front end (**observed**, the headless original with the music, up to the
mission's first ticks): 1,154 sample starts and restarts, 1,013 calls of the level-4
handlers, 6,793 ticks, no request made deliverable outside a delivery point; the mission
begins after 7,237 VBlanks, 312 of them the three fades' waits.

## The port

`src/music.c` ports the game's two calls and every routine of the player the game's calls
reach; `re/notes/porting-m8.md`, part 2, says how it is held.
