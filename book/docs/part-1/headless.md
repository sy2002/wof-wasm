Chapter 6
{ .chapter-kicker }

# The headless original

The oracle of chapter 5 holds one routine at a time to its port. To hold the whole game, the project runs the original program whole, on the same emulated processor and without a screen. By the end of this chapter you will know what stands in for the Amiga in such a run and why none of it changes what the game does; how time, the player's hands and chance reach the program; what a run leaves for the comparisons with the port; and why two runs always come out the same. And you will meet the chapter's lesson: the wall clock must never shape a run.

## One routine is not a game

A routine under the oracle runs on a state the test builds, which lets a test choose states no mission produces. In a mission the game builds the state itself, routine after routine, and most of its routines read the world it has built: the positions, the pools of objects, the timers. What a mission does depends on the order in which the routines run, on what one leaves for the next and on the interrupts between them, all of which a test of one routine leaves out.

So the original program itself runs, from its `main` routine on, on the oracle's own machine: the same Unicorn set to be a [68000](../glossary.md#68000), the program at the [fixed load layout](../glossary.md#fixed-load-layout), the memory-form shift corrected. Everything from the initialisation and the title sequence to the inner loop that plays a mission, the VBlank's routines and the key handler is the original's own code; nothing of the game's logic is written again for the instrument. `main` is entered as the C library's start-up code would enter it, with A4 set and an argument count of one on the stack.

This is the [headless original](../glossary.md#headless-original) of chapter 1, the original program run under emulation without a screen: the reference the port is compared with, tick by tick, in chapter 8, and the way the notes observe the running game, as chapter 4 put it. Around it is the [**harness**](../glossary.md#harness): the instrument's own code around the original program, written in Python, with the stubs, the hooks, the script, the stream and the dump of the sections below.

## What stands in for the machine

Besides its memory, a program on the Amiga deals with the operating system, the custom chips and the ROM, and the harness answers each in its own way.

![Under Unicorn, the program from main on and the ROM's routines, beneath the custom chips as plain memory, where the script and the entropy stream come in; stubs on the left, VBlanks on the right, the dump below.](../figures/headless.svg)

/// caption
The headless original: the original's code and the ROM's run for real; the harness stands in for the system, the chips and time, and brings in the player's hands and chance.
///

### The operating system

The game calls the operating system through its [libraries](../glossary.md#library), tables of jumps at fixed offsets from a library's address (chapter 2). The harness gives each library a made-up address whose every slot holds a return instruction, with a [hook](../glossary.md#hook) over the whole area, a routine of the instrument's own that the emulator calls at a chosen instruction. When the game calls a library, the hook stops the emulation, the harness runs a Python method of the same name, puts its answer into D0 and lets the program return. Each such method is a [stub](../glossary.md#stub), a stand-in for something the game calls. The emulation is stopped first because Unicorn forgets a register written inside a hook, while it keeps memory written there.

The stubs answer sixty of the libraries' functions. Files come from the game's disk, and what the game saves goes into a layer over them. Memory comes from an allocator that hands out each address once, so every address is the same in every run and fresh memory is zero. `AddIntServer` keeps the list of routines the game wants called at every VBlank: the sound effects' and, after it, the game's own. `Text`, the system's routine for a line of text, draws nothing and moves the pen on as the system's font would. A call without a stub ends the run, naming the library, the function and the chain of callers, so that nothing the game asks for is answered by accident. Stubs are enough because the game asks the system for little, files, memory, the records of its display and a place for its key handler; otherwise it does its own work.

### The ROM, run for real

Two services of the [Kickstart](../glossary.md#kickstart) ROM are not stood in for but run: the [fast floating point](../glossary.md#fast-floating-point), in which the game's tick computes the flight, and `RawKeyConvert`, which turns a raw key code into a character through the system's keymap. Both compute from their registers and read nothing of the machine, so the ROM's own instructions can run as they are. A stand-in would be a second implementation that no test could show exact, and the port's floating point is held to the ROM's (chapter 5), so the reference has to be the ROM itself; the keymap is not even on the game's disk. The harness maps the ROM image, which whoever builds the port supplies, at the ROM's own addresses and finds both services in it by name and content. Without the ROM no run starts.

### The custom chips

The addresses of the [custom chips](../glossary.md#custom-chips) are plain memory, so nothing is drawn; where the game waits for the blitter, the busy bit reads as zero and the wait falls through. Chapter 2 said that the game's logic never reads back what was drawn, and the headless original holds that as a test. Every read of display memory by the processor is counted by routine, and over the front end, a take-off, a long flight and a crash, not one bitplane was read: the only reads were of the copper's lists, by the routines that build them, and of the template the text routine builds. Any other reader fails the test.

Some registers are more than memory: the beam's position and the controller's, of the sections below, and Paula's. [Paula](../glossary.md#paula) is the one chip plain memory could not stand in for, because the sound effects engine learns that a [sound sample](../glossary.md#sound-sample) has played from Paula's interrupt, which plain memory never raises. So the harness runs a model of the four channels in a time of its own and calls the game's handler when a channel asks; the port's Paula is the same model, so that the two logs of sound samples can be compared (chapter 18). The model only watches: a flight without sound runs to the same states with it and without it.

The music player is a small program of its own, which the game loads with [LoadSeg](../glossary.md#loadseg) together with its songs. By default it runs for real, its timer counting in the model's time, and every call the game makes into it is recorded. A run can instead answer every call with "idle", and from a mission's start on both kinds of run hold the same state at every tick. One piece of the original is skipped: the text screen of the [crack](../glossary.md#crack), which draws random numbers the port never draws.

## Time: only where the program waits

On the Amiga the VBlank's [interrupt](../glossary.md#interrupt) comes when the picture is done, wherever the program happens to be. Unicorn imitates only the processor, so nothing in it finishes a picture. The harness could deliver the interrupt after some number of instructions, but then every result would depend on how the emulator counts. The harness follows one rule instead: the program runs until it waits, and VBlanks happen only where it waits.

A [**wait point**](../glossary.md#wait-point) is a place where the program waits for the next VBlank. Most of its waiting is a spin on one byte, `vblank_flag`, which the VBlank's routine sets in its third instruction; `st.b` sets every bit of the byte:

```wingslst
--8<-- "generated/listings/asm/vblank_server_flag.lst"
```

Here is the spin, `wait_vblank`, which a pass calls first. Look at the two instructions after the label `loc_01aa44`: `tst.b` tests the flag and `beq.b` jumps back to the test while it is zero; then `clr.b` clears it for the next time.

```wingslst
--8<-- "generated/listings/asm/wait_vblank.lst"
```

The harness hooks the test at `0x01AA44`. Reached with the flag clear, the hook delivers one VBlank, whose routine sets the flag, and the spin falls through. The other wait points are the system's `WaitTOF`, which waits for the next picture and gets one VBlank; `Delay`, which gets the VBlanks its time holds; the start of a pass, which gets those the run still owes it; and a spin in which the front end waits for a song's fade to end. On the machine the player's timer ends the fade while the program spins; the harness gives each round of that spin four VBlanks, because the game takes an [input sample](../glossary.md#input-sample) every fourth VBlank and four keeps its rhythm.

A VBlank in the harness does what the machine's would: it sets the controller's registers from the script, delivers the script's keys, and calls the routines the game installed for the VBlank, highest priority first; the game's own counters of VBlanks count exactly as many as the harness delivers. So nothing depends on how many instructions the program runs, or on how fast the emulator runs them. Work that only burns processor time between two waits takes no time at all, such as the step of a fade, whose length on the machine the listing cannot tell either (chapter 7).

The start of a pass is the one wait point whose VBlanks the run decides. A [pass](../glossary.md#pass) draws a picture, and how many VBlanks it takes on the real machine, which no listing tells, depends on the scene. So the VBlanks a pass takes are a setting of the run, two by default, and the run records its [**schedule**](../glossary.md#schedule): the order of its VBlanks, passes and [logic ticks](../glossary.md#logic-tick) as they happened. In flight it reads two VBlanks and a pass, then two VBlanks, a pass and a tick, and so on. Tests hold it: each pass of a mission begins two VBlanks after the last, three when the setting says three, and a tick comes for every four VBlanks. The port's tests replay exactly that schedule, because how passes and ticks interleave decides what the game does: the schedule is an input of the simulation, and chapter 7 tells why two VBlanks a pass is right.

## The player's hands

The input is a script: segments of so many VBlanks with the state of the stick and the button during them, written as letters, `U` for the stick pushed forward, `D` for pulled back, `L` and `R`, `F` for fire, and raw key codes, if wanted, delivered at a segment's first VBlank.

The harness does not turn the letters into the [input byte](../glossary.md#input-byte). It turns them into the hardware's state at each VBlank: the joystick's register, `JOY1DAT`, and the button's bit in the CIA's port. The game's own VBlank routines then read them, latch a tap or a hold of fire and queue the input sample, so the input byte, its latches, the queue and the message ticker are the original's own work. Even the table from directions to register values is the original's: at the start the harness calls the game's own decoder of the stick on all sixteen combinations of the register's bits, rather than trusting a reading of those bits, which was once wrong (chapter 9). Tests hold the result: a tap of fire gives the tap bit for exactly one tick, fire held becomes the hold bit after ten VBlanks, and the stick pushed forward is bit 0. Keys go in as the system delivers them, each as a raw key event with its qualifier, the state of keys such as Control, through the handler the game put into the system's input chain.

All of it is set down in a [**run description**](../glossary.md#run-description): a small JSON file that says what one run of the headless original is, its script, its random stream, the VBlanks a pass and where it stops. This one, from [`tests/runs/`](repo:tests/runs/), flies with the vertical flip; the book lays it out one entry a line. Look at the presses of fire on lines 6 to 15, the key on line 17 and the stop on line 20:

```json linenums="1"
--8<-- "generated/listings/json/flight-control-f.json"
```

There are five presses, three VBlanks each and thirty apart. The first four carry the front end from the story to the mission, which begins at the run's VBlank 444; the fifth already falls on the carrier's deck. While the music fades, three times in the front end, the script stands still, so the mission begins at the script's VBlank 132. The key on line 17, 35 with Control, is Control-F, the flip, in decimal because JSON has no hexadecimal. The stop counts the script's VBlanks too, so the run ends after 300 of them, long before the 600 of line 18 are used up.

## Chance from a stream

The game's one source of chance, the routine `rand_beam`, combines a constant with the [beam](../glossary.md#beam)'s position at the moment of the call, so on the machine every random number comes from the processor's timing. The headless original has no beam. A hook on the beam's register, `0xDFF006`, writes into it before each read the next value of the [**entropy stream**](../glossary.md#entropy-stream): the reproducible stream of values that stands in for the beam's position, one value for every read.

The stream is the port's own generator, which multiplies and adds in 32 bits and gives values shaped like the beam's register; a test holds the harness's copy to the port's, value for value. So a run can be repeated exactly, and the port, given the same stream, draws the same numbers, as long as it calls `rand_beam` in exactly the original's order. A call out of order shows at once as a difference, which makes the stream a check of its own. The log of every read names the value, the routine that asked, and the VBlank, pass and tick. A run with another stream differs from its first record on, while its schedule stays the same.

## What a run leaves

A run leaves a [**dump**](../glossary.md#dump): the file of the game's whole state after every logic tick, after every pass, and once when a mission's inner loop is first reached. The state is the program's own variables, the DATA and [BSS](../glossary.md#bss) of chapter 3, and every block of memory the game has asked for, display memory left out. Each record carries the counts of ticks, passes, VBlanks and random reads, the tick's input byte, the bytes changed since the record before, and a SHA-256 hash of the whole state, a short fingerprint computed from every byte of it. A reader rebuilds the state from the changes and checks it against the fingerprint, so it can trust its reconstruction; a test does so for every record. Chapter 8 compares such a dump with the port's state.

Beside the dump a run keeps logs of the schedule, the random reads, the files opened, the music player's calls and the sound samples started. It can also watch more closely, in four ways that chapters 4 and 5 already leaned on.

- [**The change report.**](../glossary.md#change-report) For every record, each range of memory that changed, with its old and new bytes, a name and the routines that wrote it.
- **The write summary.** The change report of a few thousand ticks runs to tens of megabytes; the summary keeps the run in a few hundred lines. Every write is tagged with its routine and its phase, inside a VBlank, a tick, a pass or the main program, and neighbouring addresses written alike are joined into one range, from which the harness reads off a table's record size, as chapter 4 read a pool's off its stride.
- **The read hook.** It watches chosen memory, given by address or by the routine that asked for it, "the map" or "the pools", and says for every read which routine read which offset in which phase.
- [**Observers.**](../glossary.md#observer) An observer records every entry of a routine named to it: the VBlank, pass and tick, all sixteen registers, and the longs and words above the return address, which are a C routine's arguments; on request also the return, with the [condition codes](../glossary.md#condition-codes) read inside the emulation as in chapter 5. That is how the notes know what each screen of the front end draws and what the floating point is handed.

All of them only read, and tests hold it: a run with an observer, or with the write summary and the read hook switched on, gives the same records and the same schedule as a plain run. Watching the game does not change it.

## The same run, twice

Two runs of one description give the same dump, byte for byte, the same schedule and the same random reads; tests hold it on a flight, a longer flight and the front end left alone. Change the input instead, and the dumps agree record for record until the scripts part, and never after. The reasons are the ones above: the program's time is the VBlanks of its waits, its chance the stream, its input the script, and its memory the same addresses in every run. Nothing the program can see depends on a clock.

/// figures
| The headless original | How much |
|---|---|
| Library functions answered by stubs | 60, of six libraries |
| Kinds of wait point | 5 |
| A flight of 1,260 ticks | 3,778 records, 1.8 MB of dump |
| The front end, five presses of fire | under a second |
| A thousand ticks of flight | 6.4 s, 7.3 s with the dump |
| Tests of the instrument | nearly forty |
///

## Wall time never shapes a run

The harness itself does read the clock. A program caught in a loop that never waits would hang the test that ran it, so the harness must notice. It runs the emulation in [**slices**](../glossary.md#slice): stretches of a fixed number of instructions, a million by default, after each of which the harness looks at the clock and goes on. Where a slice ends is no wait point and nothing the program can notice, or so it must be.

Unicorn can end a stretch of emulation after a count of instructions or after a time. Time is the tempting choice, since the harness is asking about time, and it is wrong. A timeout stops the emulation from another thread, whenever the clock runs out. It can land while a memory hook of the harness runs, on a read of the beam, say. Unicorn calls such a hook before the access completes, with the [program counter](../glossary.md#program-counter) set back to the instruction making it, so the stop reports that instruction as not yet run, its access made, and the next slice runs it again: a decrement counts twice, a read of the beam takes a second value. Landing between the two flags with which Unicorn stops, a timeout leaves every code hook silent in the next slice, and the program spins in `wait_vblank` for ever, with no hook to deliver its VBlank.

With slices of three thousandths of a second, ten recordings of one mission all differed from the unhurried one, each first by a counter one apart; one crashed and three hung. Slices of two seconds make the fault rare, since the machine must stall that long, and yet the full suite once met it: the timer of the oil that leaks from a damaged engine came out one apart from one tick on. Chapter 9 tells how that was caught.

The cure is the counter, and a rule. Unicorn counts instructions in a hook of its own that runs ahead of every other, so a slice ends before an instruction whose hooks have not run yet, at a place the program alone decides, and the next slice starts exactly there. Wall time only ever ends a run, and then as "Stuck", a failure that names where the program was: no wait point for a minute, or a whole run longer than half an hour. The limits are sized for a loaded machine, well above the longest stretches measured while the suite ran in parallel, because tighter ones once failed tests on a busy machine though nothing was wrong:

| | Longest measured, the suite running in parallel | Limit |
|---|---|---|
| Between two wait points | about 10 s | 60 s |
| A whole run | about 12 minutes | 30 minutes |

The test that holds the rule runs one flight three times, with every kind of hook in use, in slices of three lengths, and demands that everything comes out the same. Look at the three lengths on line 14 and the four comparisons at the end:

```python linenums="1"
--8<-- "generated/listings/py/test_where_a_slice_ends_changes_nothing.py"
```

`run` makes a headless original of the flight and runs it. The shortest slices, an odd length, end everywhere, more than ten thousand times (line 15); the longest never end between two wait points (line 16). Lines 18 to 22 demand the same records, random reads, schedule and observed calls, here of `shape_draw`, the routine that draws a shape. A second test sets the limit to nothing and expects the first slice without a wait point to end the run as Stuck. The counter costs nothing measurable: a mission recorded in 38 seconds with it took 40 with the timeout.

## What it does not cover

The instrument draws nothing, so no pixel of a mission's scene is compared: the drawing calls and the palette of every row stand for the picture (chapter 1). `Text` only moves the pen, so a dialog's text is seen only by where it goes. A saved game's name comes back in lower case, where the real file system keeps its case. The allocator never reuses memory, which suits a mission but not an endless campaign: of its eight megabytes the start and the first mission take less than half a megabyte. And how many VBlanks a pass takes on the machine is not measured by the instrument but given to a run.

/// dev
The harness is [`tools/headless.py`](repo:tools/headless.py), with the stubs in [`tools/headless_os.py`](repo:tools/headless%5Fos.py), the dump in [`tools/headless_dump.py`](repo:tools/headless%5Fdump.py), the write summary and the read hook in [`tools/headless_writes.py`](repo:tools/headless%5Fwrites.py), and Paula and the CIA's timer in [`tools/headless_paula.py`](repo:tools/headless%5Fpaula.py). Its command line takes `run RUN.json --out A.dump`, then `show A.dump --step 120` or `diff A.dump B.dump`. In Python: `Headless(description, observe=['shape_draw'])`, then `run(until='tick')`. Every hook is installed before the first instruction runs, because Unicorn does not translate a block again for a later hook. The tests are [`tests/test_headless.py`](repo:tests/test%5Fheadless.py).
///

## What comes next

The headless original runs the game in VBlanks, passes and ticks, and leaves it to the run how many VBlanks a pass takes. Chapter 7 is about that time: why the schedule is an input of the simulation, and how a film of a real Amiga at 240 frames a second settled two VBlanks a pass. Chapter 8 then holds the port to the headless original, mission by mission, and uses it to decide what to port at all: the reach map, what the scripts execute under it.

## Further reading

The files named here are in the repository, [`github.com/sy2002/wof-wasm`](repo:).

- [`re/notes/headless.md`](repo:re/notes/headless.md), above all ["Scheduling"](repo:re/notes/headless.md#scheduling), ["The stubs"](repo:re/notes/headless.md#the-stubs), ["Read-back"](repo:re/notes/headless.md#read-back) and ["Unicorn, as it behaves here"](repo:re/notes/headless.md#unicorn-as-it-behaves-here).
- [`re/notes/random.md`](repo:re/notes/random.md), ["Consequences"](repo:re/notes/random.md#consequences); [`re/notes/testing.md`](repo:re/notes/testing.md), ["The wall-clock limits of the headless original"](repo:re/notes/testing.md#the-wall-clock-limits-of-the-headless-original); [`SPEC.md`](repo:SPEC.md#8-verification), section 8.

Outside the repository: [Unicorn Engine](https://www.unicorn-engine.org/); the [*Amiga Hardware Reference Manual*](https://archive.org/details/commodore-amiga-tech-ref-series-amiga-hardware-reference-manual-3rd-edition), for the beam's register, the controller's registers and the interrupts.
