Chapter 9
{ .chapter-kicker }

# What went wrong, and what caught it

The instruments of chapters 5 to 8 were built to catch the port's mistakes, and they caught ours as well: in our readings, in the instruments themselves and in the tests. This chapter tells six of them, each in the same order: what we believed and why that was reasonable, what an instrument showed, what was wrong, what changed, and which instrument it was. By its end you will know why a test that fails a right port is a finding, why a failure that goes away when a test runs alone is not noise, why an order of tests that never changes can hide a fault, and why a check that has never failed must be made to. In a port that means to be faithful the instruments are the method, and a mistake teaches less by itself than by what caught it. A table at the end lists the shorter cases the record holds.

## The stick's bits

The [input byte](../glossary.md#input-byte) is the only way the player's hands reach the game's logic (chapter 7): four bits for the stick, two for the button. Which bit is which, the [listing](../glossary.md#listing) seems to say plainly. The routine that decodes the stick, `read_joy_bits`, reads the joystick's register, `JOY1DAT`, and looks four of its bits up in a table of sixteen bytes. Look at the five instructions after the read, which gather the register's bits 9 and 8 and bits 1 and 0 into an index; at `move.b (a0, d0.w), d0`, the lookup; and at the end, where the vertical flip exchanges bits 0 and 1.

```wingslst
--8<-- "generated/listings/asm/read_joy_bits.lst"
```

The first reading named bit 0 "stick down" and bit 1 "stick up", and the specification, the notes and the first shell's keys followed it. It was a reasonable reading. The table is the standard decode of the Amiga's joystick, in which each vertical switch is the exclusive-or of two bits of the register, and the reading wrote that rule down with the two vertical pairs exchanged. Nothing in the program could catch the slip: the sixteen bytes work for either naming, because which pair is the forward switch is a fact of the hardware, not of the code.

The [headless original](../glossary.md#headless-original) did not take the reading on trust. From its first version its [harness](../glossary.md#harness) found the register's values by running the original's own decoder on all sixteen combinations of the four bits, keeping for each answer the value that gave it. So when a script asked for bit 0, the harness set the register as the original reads bit 0, and the original's take-off lifted off only with the bit the reading called "down"; without it, or with bit 1, the aircraft rolled over the bow. Asked with the forward switch alone, the decoder answers 1, which is bit 0. The game's menus agree: their own decoder turns the forward switch into the code they answer exactly as they answer the cursor-up key. The manual's take-off instructions say the same (page 5), and the owner's Amiga agrees: pushed forward, the stick climbs.

The game had been right all along; the names were wrong. Bit 0 is the stick pushed forward, which moves a menu's cursor up and climbs in flight. The specification and the note were turned round, the shell's up key gives bit 0, the letters of a [run description](../glossary.md#run-description) mean what they say, two tests run the original to pin the facts, and a page test in both browsers presses each key and watches what the core is handed. The rule that came of it: no reading of the stick's bits is assumed; they are what the running original answers. Reading the listing is chapter 4's subject; what caught the slip was the headless original of chapter 6, which asked the original instead of the reader.

## The shift that lost its sign

The [oracle](../glossary.md#oracle) of chapter 5 runs one routine of the original on an emulated [68000](../glossary.md#68000) and holds its port to it. We trusted the emulator to run the game's code as the chip does, and with reason: it is built on the processor emulation of QEMU, a well-known emulator, and the oracle's self-test, the original's unpacker on all ten packed files, agreed with the project's own decoder.

Then the oracle test of the routine that moves the bombs, rockets and torpedoes failed over its random states, and the port was right. A bomb bouncing on an airfield's runway came out of the original, under the emulator, with a vertical speed of +9 where a 68000 gives −2. Chapter 5 tells the cause, a [memory-form shift](../glossary.md#memory-form-shift) that the emulator makes logical where the instruction asks for arithmetic, because it reads the shift's type from a bit that in this form belongs to the address; the figure of the two encodings and the correcting [hook](../glossary.md#hook) are there.

What changed went beyond the one instruction. Every shift and rotate of a word in memory in the program was surveyed; three give a wrong result, and a hook corrects each of them in the oracle, and so in the headless original, which is built on it. A test holds the fault, the correction with its flags, and the list against the listing, so that a corrected emulator will say when the hooks can go, and any new instrument built on the same emulator must install them. No mission script reached the bounce; a test over random states did. And a test that fails a right port is a finding about the instrument: the instrument is checked too.

## Two runs that differed

The headless original was accepted when two runs of one description gave the same [dump](../glossary.md#dump), byte for byte, and a test holds that. We believed it, and with reason. Every check passed, and the harness's one use of the clock looked harmless: a timeout ended each [slice](../glossary.md#slice) of emulation after two seconds, so that a program caught in a loop could not hang a test, while a slice normally reaches the next wait within milliseconds.

Then a run of the full suite on a busy machine failed one script, a flight to the enemy's carrier, in both of chapter 8's loops, once. Run alone, the same tests passed. The original's two recordings of that script, made with the same inputs and the same [entropy stream](../glossary.md#entropy-stream), parted from one tick on: the timer by which a damaged aircraft loses its oil stood at 43 in one and 44 in the other. With the inputs and the chance the same, the game cannot differ from itself (chapter 6), so the difference had to come from the instrument.

A fault that shows once in a full suite cannot be studied as it comes. So the slices were shortened to three thousandths of a second, which turned the rare event into some twenty thousand a recording. Every one of ten such recordings differed from the unhurried one, each beginning with a counter one apart; one crashed and three hung. Chapter 6 tells the mechanism: a timeout stops the emulation from a timer beside it, wherever the program is, and can make the next slice run an instruction a second time or leave every hook silent. Counted over one recording, nearly every timeout that stopped on an access to memory had that access made twice.

Since then a slice ends after a count of instructions, at a place the program alone decides, and the wall clock only ever ends a run, as a failure named Stuck. A test runs one flight in slices of three lengths and demands the same records. The rule: the wall clock never shapes a run. The lesson reaches beyond the emulator. A failure that goes away when a test runs alone is not noise to be run again until it passes; with the inputs fixed, it is a fault in the instrument, and the way to study a rare fault is to make it frequent.

## The core the tests shared

The tests drive the port through its [native library](../glossary.md#native-library), and a process that loads the library holds one copy of the core's state, shared by every test the process runs. Each test was believed to find the core as it needed it, since each sets up what it uses; every test passed alone, and the whole suite passed in its usual order. A test that passes alone and in the full run looks independent.

The first leak was met and mended where it showed: the music tests ended their runs in a mission with the shapes mirrored, and were made to leave a fresh core behind. That mend hid the next one. The suite takes about three hours in one process; to bring it to about one, it was run in several processes at once, each taking a share of the tests in an order that changes from run to run, with the outcomes compared test by test against the serial run's. The first such run failed tests of the shapes, the story scroller and the file loader that passed serially. In the same process the test of every map's setup, which leaves the core in a mission, had run before them; in the serial order the music tests ran in between and reset it.

The answer is a [**fixture**](../glossary.md#fixture): a function the test framework runs before a test, to set up what the test needs. This one runs before every test. Look at lines 12 to 16: a test that takes the core, or makes one of its own, gets back the settings that the core's own initialisation leaves alone, and a test that takes the shared core gets it reset.

```python linenums="1"
--8<-- "generated/listings/py/fresh_core.py"
```

A fresh core costs under five thousandths of a second, little enough to give one to every test. It was then believed to isolate every test, and a later parallel run failed the [front end](../glossary.md#front-end)'s hand-over to the mission: the port's mission number was 3 where the original's was 1. The process had first run a [closed loop](../glossary.md#closed-loop) of a script on the third map, whose replay sets that number with a [poke](../glossary.md#poke), and the poke had outlived its test, because the core's initialisation does not touch the test instrumentation that lives beside it. Serially the alphabet ran the front end's test first. Now everything beside the core's state is put back before every test, a replay clears what it set however it ends, and the testing note keeps an audit table of that state, each item with what sets it and what puts it back; a test sets every item, resets, and finds none left.

One more case was of the same kind. To name a pointer into freed memory, the comparison looks for the nearest start of a [sound sample](../glossary.md#sound-sample) below it that the run has seen, and that record, a cache of the test helpers, belonged to the process, not the run. A closed loop of the script that saves a game, run at another pass rate after other recordings, found [Paula](../glossary.md#paula)'s first channel named by a sample another recording had left; whether it did depended on which recordings had run before it in the process. Every replay empties the cache since.

The lesson is about order. A test's result must not depend on what ran before it, and an order that never changes can hide such a dependence for ever: the last three leaks showed only when the order changed. Chapter 24 takes the suite up.

## The register carried as a long

A 68000 register holds 32 bits, and an instruction on a word works on its lower half. The other half is the [**upper word**](../glossary.md#upper-word): the upper 16 bits of a register or a long, which an instruction on a word leaves as they were. So a value one routine leaves in a register as a long reaches the next routine's upper word, unless something clears it. Chapter 3 gave an example from the game's hand-written routines, and chapter 4 said the port had to learn it. This is how it was learnt.

The port treated the targets' walks, the routines that draw the ground targets and let them fire, as working on words throughout. That had been observed: with [observers](../glossary.md#observer) on their entries over two scripts, the upper words of the registers they take were 0 every time. Here is the routine that sends a soldier from the nearest barracks to refill an empty dug-out. Look at its first instruction, which saves D0, D2, D7 and address registers but not D1; at `moveq #$1, d1`, which sets the whole of D1, all 32 bits, to the value 1; and at `neg.l d1`, which makes that −1, every bit set, when the soldier walks west.

```wingslst
--8<-- "generated/listings/asm/target_refill.lst"
```

So the refill leaves the soldier's direction in D1 as a long, and nothing between it and the next target's fire clears the upper word. That fire takes D1's upper word and, when the aircraft is at least as high as it is far, hands it on to the smoke at the engine as the fraction of its position.

No mission script exposed it. A closed loop of the script that saves a game did, at one [VBlank](../glossary.md#vblank) a [pass](../glossary.md#pass), a pass rate its tests had not used (chapter 7): well into the run a dug-out was refilled, and the port placed the smoke at the engine elsewhere than the original did, by exactly the word the refill had left: the original had taken it for a fraction of the smoke's position, the port had assumed 0. It came out of a check by another hand (chapter 8), a closed loop on another seed and at pass rates the porter had never used: the check found the misnamed channel of the last section, and the search for its cause found the upper word beside it.

The port hands the upper word on from walk to walk now, as the original's D1 does. The specification gained a rule: never assume a register's upper word is 0 at a routine's entry because the scripts so far found it so. And the oracle tests of the targets, the ships' guns and the music player draw the upper words at random. Two rules caught this mistake together: the oracle draws what the scripts never produced, and a reviewer checks on inputs the porter never chose.

## The last ticks nobody compared

A pass draws first and then runs its ticks: the inner loop calls `frame_update`, which draws, and then `run_queued_ticks`, which runs a [logic tick](../glossary.md#logic-tick) for each byte waiting. The headless original records a pass where `frame_update` returns, so a pass's ticks come after the pass's record.

Every comparison of a [mission script](../glossary.md#mission-script) was believed to run to the script's end. The replay followed the original's schedule to the original's last pass, and every pass and tick up to there agreed; the last pass looked like the end.

A [control](../glossary.md#control), a deliberate break of the port (chapter 8), showed otherwise. The demo is a recorded game played back (chapter 17), and the control made its playback end one entry late. Such a late end shows only in the ticks after the last pass's drawing, and the replay had stopped before them; the control was caught only once the replay ran on through those ticks, at tick 100 of its script. Until then the last ticks of every mission script had never been compared.

![One row of the original's last records, P T P P T, the last pass P and its tick T after it; a bracket under the last two: the pass recorded where its drawing returns, its tick run after it. Below, a dashed span to the end of the last pass, compared before, and a gold span to the end of the last tick, compared since.](../figures/replay-end.svg)

/// caption
The replay's end. The original records its last pass where the drawing ends, and the pass's tick follows; the comparison used to stop at the last pass and runs to the last tick since. The one tick after the last pass is an example: a pass may have none, one or more.
///

The fix is a few lines. Look at `last_tick` on line 7, worked out beside `last_pass` from the original's records, and at the condition on line 19 that ends the loop, which now asks for both.

```python linenums="1"
--8<-- "generated/listings/py/replay_end.py"
```

The tails agreed once compared, as the full suite showed; no fault of the port had been hiding there. The lessons are two. A control that does not fail is a finding, about the comparison as much as about the port. And a control that only the tail of a script can catch belongs in every milestone's set, so that the comparison is tested where it ends.

## The rest of the record

The six are not all. The record holds more, each caught by an instrument or by the owner's own eyes, ears and keyboard, and a few were told in earlier chapters. The table lists them all, the six first.

| What we believed | What showed otherwise | What changed |
|---|---|---|
| Bit 0 of the input byte is the stick pulled back | the headless original, asking the original's decoder (chapter 6) | bit 0 is forward everywhere; tests run the original to pin it |
| The emulator runs every instruction as a 68000 does | an oracle test over random states (chapter 5) | three shifts corrected by a hook, every such shift surveyed |
| Two runs always give the same dump | the full suite on a busy machine, then two recordings compared (chapter 6) | slices end after a count of instructions; the clock only ends a run |
| Each test finds the core as it needs it | the suite run in parallel (chapter 24) | a fresh core, and everything beside it put back, before every test |
| The upper words of the targets' registers are 0 | a closed loop at another pass rate, by another hand (chapter 8) | the word handed on, never assumed, drawn at random by the oracle |
| Every comparison runs to its script's end | a control only the last ticks could catch (chapter 8) | the replay runs to the original's last tick |
| The machine leaves the last four records of a map uninitialised, as the harness's memory suggested | a reading of the allocator the game calls, which asks for cleared memory (chapter 4) | the port hands out cleared memory as a rule, with a test |
| A flag read out of the emulator is the flag | flags read out came back stale, as the emulator works them out lazily; nine sequences whose flags the manual fixes (chapter 5) | flags are read inside the emulation |
| A saved game fits a file of 8,192 bytes, sized from one save on the first map | the saves measured on all fifteen maps: seven are larger | the limit is the largest save the port's tables allow, 12,412 bytes |
| The routine that restores the play screen after a dialog, ported from reading, is right | the closed loop of the save script, nearly a thousand passes differing (chapters 4 and 8) | the play screen is switched on again after a dialog |
| A loaded game's gun list is the file's | the completeness list over a loaded game (chapter 8) | the cruise ship's two guns set as the original sets them |
| The page's canvases behave in Firefox as in Chrome | a black picture, where a canvas dropped the pixels written into it; later a measurement, half the frame rate at full screen | a software canvas takes the pixels; WebGL draws the picture |
| The page pauses and resumes cleanly around a moment hidden | the owner's Firefox in full screen, still and silent; a measurement of a window's change of state | the shell keeps its own record; leaving full screen pauses |
| The key left of 1 has one code in every browser | the owner's keyboard: the diagnostics overlay would not open in Chrome and Safari | both codes open it |
| The page names nothing of the machine that built it | the core's debug information, which held every source's full path | the paths made relative; the release carries no debug information |

/// dev
The stories in the code: the harness asks the stick's decoder in `_joy_words` of [`tools/headless.py`](repo:tools/headless.py), whose `_drive` ends a slice after `slice_insns` instructions; the shifts' hook is [`tools/m68k_fix.py`](repo:tools/m68k%5Ffix.py), held by [`tests/test_headless.py`](repo:tests/test%5Fheadless.py); `fresh_core` and `fresh_settings` are in [`tests/conftest.py`](repo:tests/conftest.py), and [`tests/test_isolation.py`](repo:tests/test%5Fisolation.py) holds the reset, the pokes and the cache, `SEEN_SAMPLES` of [`tests/m4state.py`](repo:tests/m4state.py); the walks hand the upper word on in `wof_targets_3_draw` and `wof_targets_f_draw` of [`src/targets.c`](repo:src/targets.c); the replay's end is `Replay._run` of [`tests/m4compare.py`](repo:tests/m4compare.py).
///

## What comes next

Each of these beliefs was reasonable when it was held, and in each an instrument, or a reading of what the code really calls, decided against it. Chapter 10 tells how the work was arranged so that the instruments, not the readers, would decide: the way of working as a whole, its rules and its reviews, what it cost and what it took.

## Further reading

The files named here are in the repository, [`github.com/sy2002/wof-wasm`](repo:).

- [`CONTROLLER.md`](repo:CONTROLLER.md#pitfalls-that-cost-time), "Pitfalls that cost time": the record of the mistakes, kept as warnings.
- [`re/notes/headless.md`](repo:re/notes/headless.md): ["Input"](repo:re/notes/headless.md#input) and ["Unicorn, as it behaves here"](repo:re/notes/headless.md#unicorn-as-it-behaves-here).
- [`re/notes/porting-m5.md`](repo:re/notes/porting-m5.md): ["Registers that cross a call"](repo:re/notes/porting-m5.md#registers-that-cross-a-call) and ["The emulator's memory-form shift (observed)"](repo:re/notes/porting-m5.md#the-emulators-memory-form-shift-observed).
- [`re/notes/porting-m7.md`](repo:re/notes/porting-m7.md): ["The port"](repo:re/notes/porting-m7.md#the-port), ["Paula's channel 0 after the save"](repo:re/notes/porting-m7.md#paulas-channel-0-after-the-save) and ["Part 2: the controls"](repo:re/notes/porting-m7.md#part-2-the-controls).
- [`re/notes/testing.md`](repo:re/notes/testing.md#a-fresh-core-for-every-test), "A fresh core for every test".
- [`SPEC.md`](repo:SPEC.md), sections 3.3, ["Runtime model"](repo:SPEC.md#33-runtime-model), and 7.1, ["Arithmetic"](repo:SPEC.md#71-arithmetic).
