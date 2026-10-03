Chapter 18
{ .chapter-kicker }

# Sound and music

This chapter takes apart chapter 2's two sound engines. By its end you will know how the effects reach Paula through two layers of code, why a sound starts two VBlanks late and how its end is learnt; how the music's waits move a mission; how the music player keeps its own time and stores its songs; and the one value the tempo rests on. The port and its instruments come at the end.

## Paula, as far as this chapter needs it

[Paula](../glossary.md#paula) plays four channels, each given a [sound sample](../glossary.md#sound-sample)'s address, its length in words, a [period](../glossary.md#period) and a volume from 0 to 64 (chapter 2). The register `DMACON` switches them, its bits 0 to 3 naming the four: written with bit 15 set, the named channels go on, without it they go off; the interrupt registers follow the same rule.

A channel plays its bytes, each held for its period, and at their end, a cycle's end, takes the address and length again and plays on. At the start and the end of every cycle it raises an [**interrupt request**](../glossary.md#interrupt-request), a bit by which a chip asks for an [interrupt](../glossary.md#interrupt): bits 7 to 10 of `INTREQ`, together `0x0780`. A request reaches the processor only while its bit and the master bit, bit 14 or `0x4000`, are set in `INTENA`; the processor then runs the routine whose address lies at `0x70`, the [**level-4 vector**](../glossary.md#level-4-vector). So a program learns that a sample has played.

## Two layers

The game's [**sound effects engine**](../glossary.md#sound-effects-engine), the code that plays its eight effects, has two layers. The [logic tick](../glossary.md#logic-tick) knows what ought to sound, but a channel is given a new sample by a [VBlank server](../glossary.md#vblank-server), and its end shows only in a request, which only the interrupt's handler sees. So the tick writes what it wants into records of its own, and a second layer starts and stops the channels when the hardware lets it.

The upper layer is eight [**sound slots**](../glossary.md#sound-slot), records of `0x18` bytes, two to a channel, holding a sample, its length, period, volume and repeat count, the cycles to play. The lower layer is four [**channel records**](../glossary.md#channel-record) of `0x1E` bytes, one a channel, holding what the channel was last asked to play and when it last stopped. The numbers are operands of the instructions (chapter 3):

| Sound slot, channel | Sample | Period, volume | Cycles | Sounds for |
|---|---|---|---|---|
| 0, 0 | `machinegun` | 200, 64 | for ever | the player's guns |
| 1, 0 | `engine` | eased | for ever | the engine |
| 2, 1 | `machinegun` | 160, 57 | for ever | an enemy aircraft's guns |
| 3, 1 | `engine` | 330, by distance | for ever | the nearest enemy aircraft |
| 4, 2 | `boom` | 500, by distance | 1 | a burst |
| 5, 2 | `splash` | 350, by distance | 1 | a splash; aboard, the sea at 800, 34, for ever |
| 6, 3 | `machinegun` | 320, by distance | for ever | a ground gun |
| 7, 3 | as set | | | the lift, the wheels' screech, a scream |

The first sound slot of a pair that is on gets the channel: the guns drown the engine, a burst a splash. Setting sound slot 7 switches 6 off and the reverse, so on channel 3 the last one set wins. A one-shot's setter clears the pair's memory of the sample last handed over, so a second burst starts afresh instead of passing for the one playing. Loudness falls with distance:

/// figures
| Loudness by distance | |
|---|---|
| An enemy aircraft, n its distance in steps of 16 pixels | 64 − 4n up to n = 5, then 44 − n |
| A burst, a splash, a scream, n in steps of 32 pixels | 64 − n; a scream half of it |
| Silent from, derived | 704 and 2,048 pixels |
///

The engine is eased: each tick its volume moves towards a target by 1 up or 2 down, and its period by 20 up or 10 down towards a base plus the pitch's target and the height, scaled down, so it sounds higher with the nose down and lower with height. Ten places of the controls set the targets, in [chapter 14](player.md)'s terms:

| The aircraft | Volume | Period's base |
|---|---|---|
| full throttle, diving, rolling to the bow | 64 | `0x14F` |
| flying on otherwise | 49 | `0x181` |
| on the deck, on the cable, at rest | 40 | `0x328` |
| crashing | 25 | `0x3C0` |

Paused, or with the music off, nothing moves and the channels stop.

## Two VBlanks late

Once a tick, `sound_channels` gives each channel the winner of its pair: a sample already playing gets only a changed period or volume, a new one goes to `channel_play`, three times with the same arguments. Look at the three calls at the end, and above them three of `channel_stop`:

//// html | div.listing-pair

/// html | div
```wingslst
--8<-- "generated/listings/asm/sound_channels_play.lst"
```
///

/// html | div
```c
--8<-- "generated/listings/c/sound_channels_play_c.c"
```
///

////

`channel_play` stops a busy channel before setting the new sample up, and every stop writes the engine's count of VBlanks into the channel record. So the second call undoes the first and sets it up again, as does the third, and the record waits, stamped with the current count.

The engine's VBlank server, `soundfx_vblank`, runs before the game's own (chapter 7) and starts a waiting channel only two VBlanks or more after its stamp: `cmp.l #$2, d0` and `blt.w`. Then come the four registers, and `or.w d1` collects the channel's bit for the one write of `DMACON` after the loop, which switches the channels on together.

//// html | div.listing-pair

/// html | div
```wingslst
--8<-- "generated/listings/asm/soundfx_vblank_start.lst"
```
///

/// html | div
```c
--8<-- "generated/listings/c/soundfx_vblank_start_c.c"
```
///

////

So a sample the tick asks for starts at the second VBlank after the tick, which keeps a channel silent for at least a whole VBlank between two samples.

![A ruler of VBlanks k to k + 3 and the cycle's end; four rows: the tick, the VBlank server, Paula's channel 3 and the handler, with what each does when.](../figures/sound-layers.svg)

/// caption
The lift's clang through the two layers: the tick fills sound slot 7 and stamps the channel record; the VBlank server waits a VBlank and starts the channel at the second; Paula plays the one cycle, a request at its start and its end; the handler stops it at the second.
///

The handler at the level-4 vector, `audio_irq`, counts a channel's cycles down at each request and stops the channel when the count goes below zero. A request comes at the start and at every cycle's end, so a repeat count of N plays N cycles: the clang, with 1, is stopped by its second request. A count of −1 is never counted, and the engine, the sea and the guns loop until the tick stops them.

Look at the two `bset.b d1, d4`: every channel handled adds its bit to D4, and a stop writes D4 to `INTENA` without bit 15, switching off the interrupt of each channel in it. So a channel kept before a stopped one loses its interrupt until the next VBlank's server switches all four on again. No script ever met that; the port copies it all the same.

//// html | div.listing-pair

/// html | div
```wingslst
--8<-- "generated/listings/asm/audio_irq_count.lst"
```
///

/// html | div
```c
--8<-- "generated/listings/c/audio_irq_count_c.c"
```
///

////

Eight routines of the engine, a shutdown, a volume easing and a hand-over of channel 2 to the music among them, have no caller the game reaches in play, and two hold chapter 7's two short waits; the port leaves them out. The hand-over's path in `channel_play`, for a channel 6 no caller asks for, is the [stand-in](../glossary.md#stand-in) chapter 8 showed; the flags it would set, and the easing, never act.

## The samples

The eight effects are files of [signed bytes](../glossary.md#signed-byte) (chapter 3), loaded into [chip memory](../glossary.md#chip-memory) at a mission's setup while their pointers are 0; between missions all but the engine's are freed, and the dialog for saving and loading frees that one too and loads it again (chapter 17). The manual warns that a 512K machine may lose some effects at the higher levels (page 3); the port plays them all from its page.

## What the scripts play

The [headless original](../glossary.md#headless-original) and the port keep the same [**event log**](../glossary.md#event-log), chapter 1's sound event log: every start of a sample and every restart at a cycle's end, with its channel, period, volume and instant. Over the 75 [mission scripts](../glossary.md#mission-script) of the first three mission milestones the effects start 1,129 times and restart 10,219 times, and no request became deliverable, ready for the processor, anywhere but where chapter 6's model [delivers](../part-1/headless.md#the-custom-chips): at a VBlank, before its servers, and after each server. The sea starts in all 75, while the aircraft waits in the [hold](../glossary.md#hold); the engine in 55, a ground gun in 35, a burst in 32, a scream in 3.

The sound moves even missions that never hear it. A target lets its [soldiers](../glossary.md#soldier) out by a timer set from the count of VBlanks since the program's start (chapter 15), which includes the 312 VBlanks the front end waits for the music's fades. Three scripts made before the music played went another way with it: one let its first soldier out at tick 625, another no longer won its mission. Each takes a [poke](../glossary.md#poke) that sets the count back to its value without the fades.

## The music player

The [**music player**](../glossary.md#music-player), `songplay`, is a [hunk file](../glossary.md#hunk-file) of 5,148 bytes; the songs, voices and samples are in `wofsongs`, 41,328 bytes, whose code only returns the address of its data. `music_start` loads both with [LoadSeg](../glossary.md#loadseg) and opens the player's timer; `music_stop` closes it and lets both go. The player has one entry with a command in D0, thirteen commands, of which the game gives six: open the timer, read a song's instruments, play, close the timer, report the song's state, and fade.

With the music loaded, `music_start` first fades the song playing, the [**song's fade**](../glossary.md#songs-fade), which lowers every track's volume a step every few ticks of the timer until none is left, not the display's fade. Then it asks for the song's state until the answer is 0: at `0x012402`, a call, a test, a branch back, nothing that waits. On a real machine the timer's interrupts end the song's fade while it spins, and the screen stands still for about two seconds. The port's [coroutine](../part-3/core.md) gives each round, one call, four VBlanks, as the headless original does (chapter 6).

//// html | div.listing-pair

/// html | div
```wingslst
--8<-- "generated/listings/asm/music_start_fade.lst"
```
///

/// html | div
```c
--8<-- "generated/listings/c/music_start_fade_c.c"
```
///

////

At speed 2 the song's fade takes 33 steps of three ticks: 32 from volume 32 to 0, and one that finds nothing left and stops the song. A note takes the track's volume when it starts, so the long held notes of songs 2 and 4 sound at full volume through the song's fade and stop at its end.

Which song plays where is in the table below, and chapter 19 tells the screens; each change of song waits 104 VBlanks for the song's fade.

Control-S, which the manual's keys leave out (page 12) and the port puts on M (chapter 1), toggles a flag that switches the music off. The game reads the key only in flight, where no song plays; the flag silences the effects, and a song started while it is set is never played. The outer loop clears it before every rank selection, so it silences at most the high-score screen of the game it was set in, or of a game loaded from a file saved with it set, being the last byte of the [raw part](../glossary.md#raw-part).

With the music loaded and the flag set, the branch at `0x0123FE` takes the path for music not loaded: both files are loaded again, the first copies never freed, and the second player, ignoring what the system answers, leaves the timer calling the first while it takes the level-4 vector: two players live at once. Nothing reaches the branch: the flag is set only in flight or by a load, with the music unloaded, and cleared before the music is next found loaded; the port, holding one player, marks it as a stand-in.

## The timer

The player's beat is CIA-A's timer A (chapter 2), taken through the system's `ciaa.resource`. Command 0, `_OpenTimerInt`, gives the timer an interrupt node whose code is the player's tick, `SongInt`, and starts it without loading it. Then it keeps the level-4 vector, the `move.l` from `$70.w`, and puts its own handler there; in the port the vector is a value of the state.

//// html | div.listing-pair

/// html | div
```wingslst
--8<-- "generated/listings/player/_OpenTimerInt.lst"
```
///

/// html | div
```c
--8<-- "generated/listings/c/open_timer_int.c"
```
///

////

While the music is loaded `audio_irq` never runs; command 4 puts it back, and since the rank selection ends with `music_stop`, every mission begins with it in place. The `move.w` to `$dff01e` writes `INTREQR`, a register that can only be read; the player's three such writes do nothing on the machine, whatever they were for.

The timer counts down at the [**E clock**](../glossary.md#e-clock), the colour clock divided by five, 709,379 counts a second on PAL. Run out, it reloads from the [**timer's latch**](../glossary.md#timers-latch), a 16-bit value written a byte at a time, and raises its interrupt: a [**timer's tick**](../glossary.md#timers-tick), at which the player runs `SongInt`. A latch of L gives a tick every L + 1 counts.

A song's command sets the latch's high byte and restarts the timer: 56 for songs 1 to 4, 60 for song 0. Nothing writes the low byte, which keeps its value from when the machine was switched on, `0xFF` by the CIA's documentation: the one assumption chapter 1 said the tempo rests on. With it a tick comes every 14,592 E cycles, as [chapter 2](../part-1/amiga.md#paula) gave; with `0x00` every song would be 1.8 percent faster. The first tick comes when the whole counter, as it stood at power-up, has run down: 65,536 counts.

/// figures
| The times, on PAL, derived | |
|---|---|
| A byte at period 500, the burst's | 7,094 a second |
| A timer's tick, songs 1 to 4 | 1.0285 VBlanks |
| The first timer's tick | 92 ms after the timer opens |
| The song's fade, 99 ticks | 2.04 seconds |
///

## A tick of a song

At each tick `SongInt` looks at the play state: idle, a song asked for, playing, a stop asked for, or fading. A song asked for starts its four [**tracks**](../glossary.md#track), each a line of music on its own channel. Playing, a note counts its length down and at its release tick switches its channel off; when the length has run out, the track reads on to the next note.

A note takes its length and release from a table of durations, the sample of its [**voice**](../glossary.md#voice), the instrument the track has chosen, and its period, and switches its channel and interrupt on, the length covering the sample's one-shot part and its repeat part. At the channel's first request, at the start, the player's own handler sets the address and length to the repeat part, which Paula takes at the cycle's end: the one-shot part plays once, the repeat part loops while the note sounds. A sample without a repeat part goes off at its next request.

![A waveform in two inks, the one-shot part gold and the repeat part blue, a line at the boundary; below, a hundred bytes around the boundary as steps.](../generated/figures/sample-omlead.png)

/// caption
The voice omlead at the period of song 2's first note: its one-shot part, played once, and its repeat part, looped; below, the bytes around the boundary.
///

The period comes from a table of 132 numbers, a semitone apart, each the colour clocks of one cycle of a waveform at that note, divided by the samples in a cycle of the voice and shifted by its octave; the rate a sample's header names is never read. The table holds an NTSC machine's clocks: on an NTSC Amiga its notes are tuned to A at 440 hertz within a third of a cent, on a PAL Amiga, whose clock is slightly slower, every note is 15.9 cents flat, a sixth of a semitone. The port plays the table as it stands, as a PAL Amiga does.

## The songs

Every pointer in the song data is an offset into it; [`tools/song_decode.py`](repo:tools/song%5Fdecode.py) reads it as the player does:

| Part | What it holds |
|---|---|
| a song | a sequence for each track and a table of voices |
| a sequence | a pattern and a transpose for each entry, played in turn |
| a [**pattern**](../glossary.md#pattern) | events of 2 bytes: a note and its length's index, or a command |
| a command | the next entry, the sequence again, a voice, the timer's latch, a volume |
| a voice | `0x2E` bytes: its sample, an IFF 8SVX form, and a vibrato and arpeggio, off |

A note with its top bit set is tied: a run of tied notes sounds as one. Voice 0 is the rest voice, without a sample, whose notes take their time and start nothing.

/// figures
| The durations, in timer's ticks | |
|---|---|
| Lengths, index 0 to 19 | 96, 48, 32, 64, 24, 72, 12, 84, 60, 36, 6, 90, 78, 66, 54, 42, 30, 18, 8, 16 |
| Releases, after the start | 86, 43, 28, 58, 21, 64, 10, 75, 54, 32, 5, 81, 70, 59, 48, 38, 27, 16, 7, 14 |
///

| Song | Played | Sequence entries | Voices |
|---|---|---|---|
| 0 | on the high-score screen | 17 | SyntheBass, omlead, RoomBrass2, BassDrum3, sdrum1 |
| 1 | behind the title pictures | 13 | the same five |
| 2 | behind the story scroller | 29 | the five and Mechanic1 |
| 3 | never | 13 | as song 1 |
| 4 | in the rank selection | 15 | the five and Mechanic1 |

A whole note is 96 ticks, so songs 1 to 4 play at 121.5 beats a minute and song 0 at 113.6.

![Four lanes of coloured bars over four bars of music: a brass melody with gaps, a brass line of long notes, a bass in short notes, and drums.](../generated/figures/song-highscore.png)

/// caption
Song 0's first four bars, walked as the player plays them. Songs 2 and 4 open with tied notes of one voice; song 0 shows more: the rest voice's half bars, tied notes held to the next start, a bass, two drums in turn.
///

| Sample | One-shot part | Repeat part | Samples a cycle | Rate in its header |
|---|---|---|---|---|
| BassDrum3 | 3,400 | 0 | 32 | 8,363 Hz |
| sdrum1 | 1,642 | 0 | 32 | 8,363 Hz |
| RoomBrass2 | 1,768 | 6,548 | 8 | 8,363 Hz |
| SyntheBass | 7,644 | 384 | 8 | 8,363 Hz |
| omlead | 3,434 | 3,042 | 16 | 4,181 Hz |
| Mechanic1 | 7,374 | 64 | 32 | 8,363 Hz |

Left alone, the front end up to the first mission makes 1,154 starts and restarts and runs 6,793 timer's ticks.

## What the port made of it

[`src/sound.c`](repo:src/sound.c) is the engine routine by routine in the original's order and arithmetic: the triple calls, the high byte `st.b` sets in a sound slot's word, the length written as a word into the low half of sound slot 7's long, the D0 and D1 the burst and the scream leave for their callers ([chapter 9](../part-1/wrong.md#the-register-carried-as-a-long)'s family), the `INTENA` write. A sample pointer becomes a sound handle, a file's number and an offset, since the samples play where the files lie in the page. The sound slots, channel records and pointers are [registered state](../part-1/oracle.md#calling-a-routine-without-its-program); Paula, the timer and the level-4 vector are in the core's saved state (chapter 22).

The model is the headless original's, so that the two event logs can be held to each other: time in units of one over the colour clock times the frame rate, in which a VBlank and a byte at any period are whole numbers; every write at its VBlank's instant; what happens between two VBlanks delivered at the second, in time order. So the port's VBlank runs the events of the one that passed, `soundfx_vblank`, its requests, then the game's server. In the same walk the core mixes each output frame from the byte each channel plays at its instant, 0 and 3 left, 1 and 2 right, into a queue outside the state, so a replay renders the same sound whatever the [shell](../glossary.md#shell) asks; the shell takes it by emulated time (chapter 23).

`music_start` and `music_stop` are coroutines, since each waits for a song's fade, four VBlanks a round, which keeps the phase of the [input samples](../glossary.md#input-sample). Of what LoadSeg would load, the port keeps the player's changing data and the seven voices, which the player writes, and reads the rest where the file lies. The player follows [`re/songplay.lst`](repo:re/songplay.lst) with the 68000's arithmetic: a `divu` that leaves its dividend when the quotient does not fit, shifts counted modulo 64, the release tick subtracted as a byte. Seventeen stand-ins of the sound remain, chapter 8's count: channel 6, and sixteen of the music, among them the commands the game never gives, the second player and six guards for values no song holds.

## How it is held

Every [closed](../glossary.md#closed-loop) and [open loop](../glossary.md#open-loop) of the mission milestones compares the event log and the model's state, timer and level-4 vector included, after every pass and tick (chapter 8). The model's tests hold a one-shot stopped by its second interrupt, a loop's restarts, and the port's output, 960 frames a VBlank at 48 kHz. The [oracle](../glossary.md#oracle) holds every routine of the engine and the player on thousands of random states, Paula and the timer register by register; the front end's event log, the music after every VBlank through the outer loop, Control-S included, and the page's sound in the browsers are compared too (chapter 24). The tempo's test wants the first tick at the power-up latch and every steady one `0x3900` counts after the last:

```python
--8<-- "generated/listings/py/test_the_timer_ticks_at_the_songs_tempo.py"
```

That the songs sound right rests on the owner's ear, on the files of the port's sound [`tests/m8_renders.py`](repo:tests/m8%5Frenders.py) writes (chapter 10). [Controls](../glossary.md#control), chapter 8's breaks of the port on purpose, were each caught:

| What was changed in the port | Where it first showed |
|---|---|
| a period one too high | `kills_a`, pass 2: the sea's start |
| the two sound slots of a pair exchanged | `guns_a`, pass 1120: the guns' start missing |
| a cycle's end delivered a VBlank late | `kills_a`, pass 40: the sea's restart |
| the timer's latch's high byte one too high | the idle front end, event 186: a start of song 2 |
| a timer's tick delivered a VBlank late | the idle front end, event 0: song 2's first starts |

Left out of the model: Paula raises a cycle's end request four bytes earlier than the model, which moves a restart only when a VBlank falls inside them; a real PAL frame is about 0.16 percent longer than a fiftieth of a second; there is no filter and no analogue mixing; the fade's wait ends up to three VBlanks late; and the latch's low byte is an assumption.


## What comes next

The chapter in one sentence: the tick asks, a VBlank server starts the sound two VBlanks later and an interrupt stops it, and the music is a player of its own on a CIA timer, whose one unwritten byte sets the tempo. Chapter 19 takes up the screens the songs play behind and the keys, Control-S among them.

## Further reading

- [`re/notes/sound.md`](repo:re/notes/sound.md): ["Two layers"](repo:re/notes/sound.md#two-layers), ["The slots and what they play"](repo:re/notes/sound.md#the-slots-and-what-they-play), ["The channel layer"](repo:re/notes/sound.md#the-channel-layer) and ["What the scripts play"](repo:re/notes/sound.md#what-the-scripts-play).
- [`re/notes/music.md`](repo:re/notes/music.md): ["The game's calls"](repo:re/notes/music.md#the-games-calls), ["The timer"](repo:re/notes/music.md#the-timer), ["The tick: SongInt"](repo:re/notes/music.md#the-tick-songint) and ["The song format"](repo:re/notes/music.md#the-song-format-wofsongss-data-hunk).
- [`re/notes/porting-m8.md`](repo:re/notes/porting-m8.md): ["The port"](repo:re/notes/porting-m8.md#the-port), ["How the port is held to the original"](repo:re/notes/porting-m8.md#how-the-port-is-held-to-the-original) and ["Part 2: the music player"](repo:re/notes/porting-m8.md#part-2-the-music-player).
- [`re/notes/headless.md`](repo:re/notes/headless.md): ["The audio channels"](repo:re/notes/headless.md#the-audio-channels), ["The music's timer"](repo:re/notes/headless.md#the-musics-timer) and ["The fade's wait"](repo:re/notes/headless.md#the-fades-wait).
- [`src/sound.c`](repo:src/sound.c), [`src/music.c`](repo:src/music.c), [`src/audio.c`](repo:src/audio.c), [`re/songplay.lst`](repo:re/songplay.lst), [`tools/song_decode.py`](repo:tools/song%5Fdecode.py), [`tests/test_oracle_m8.py`](repo:tests/test%5Foracle%5Fm8.py) and [`tests/test_music.py`](repo:tests/test%5Fmusic.py).
- [`original/manual.txt`](repo:original/manual.txt), the game's manual: page 3 for the sound on a 512K machine, page 12 for the key commands.
