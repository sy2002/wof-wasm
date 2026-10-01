Chapter 9
{ .chapter-kicker }

# What went wrong, and what caught it

The instruments of chapters 5 to 8, and the suite of chapter 24, were built to catch the port's mistakes, and they caught ours as well: in our readings, in the instruments themselves and in the tests. This chapter tells six of them, each in the same order: what we believed and why that was reasonable, what an instrument showed, what was wrong, what changed, and last, which instrument caught it. By its end you will know why no reading of the listing is taken over what the running original answers, and why a test that fails a right port is a finding. You will know why a failure that goes away when a test runs alone is not noise, why an order of tests that never changes can hide a fault, why a value a routine leaves in a register is handed on and never assumed away, and why a check that has never failed must be made to. In a port that means to be faithful the instruments are the method, and a mistake teaches less by itself than by what caught it. A table at the end adds the shorter cases from the project's record of its mistakes, the handbook's [list of pitfalls](repo:CONTROLLER.md#pitfalls-that-cost-time).

## The stick's bits

The [input byte](../glossary.md#input-byte) is the only way the stick and the button reach the game's logic (chapter 7): four of its bits for the stick, two for the button. The routine that decodes the stick, `read_joy_bits`, reads the joystick's register, `JOY1DAT`, takes four of the register's sixteen bits, 9 and 8, 1 and 0, as an index, and looks the index up in a table of sixteen bytes; the byte it finds becomes the stick's part of the input byte. Look at the five instructions after the read, which build the index; at `move.b (a0, d0.w), d0`, the lookup; and at the end, where the vertical flip exchanges the byte's bits 0 and 1.

```wingslst
--8<-- "generated/listings/asm/read_joy_bits.lst"
```

The first reading named the byte's bit 0 the stick pulled back and bit 1 the stick pushed forward. The specification and the notes followed it, and so did the first version of the page, whose up key gave bit 1, the stick pulled back. The slip was easy to make. In the hardware each vertical switch is the exclusive-or of a pair of the register's bits, and the reading wrote that rule down with the two pairs exchanged. The table could not catch it: it turns one pair into the byte's bit 0 and the other into bit 1, and which pair the forward switch drives is the hardware's doing, not the program's.

![Above, the sixteen bits of JOY1DAT, bits 9 and 8 marked as the forward switch and bits 1 and 0 as the back switch; arrows through the decoder and its table of sixteen bytes to the input byte below, the forward pair to bit 0 and the back pair to bit 1. Beside bit 0, the first reading, the stick pulled back, struck through, and the original's answer: the forward switch alone gives bit 0.](../figures/stick-bits.svg)

/// caption
The stick's decode. Each vertical switch is the exclusive-or of a pair of the register's bits; the original's decoder turns the forward pair into the byte's bit 0. The first reading had the pairs the other way round.
///

The [headless original](../glossary.md#headless-original) did not take the reading on trust. From its first version its [harness](../glossary.md#harness) found the register's values by running the original's own decoder on all sixteen combinations of the four bits, keeping for each answer the value that gave it; asked with the forward switch alone, the decoder answers with the byte's bit 0. And the original lifted off the carrier only with the byte's bit 0, the bit the reading called pulled back; without it, or with bit 1, the aircraft rolled over the bow. The manual's take-off wants the stick pushed forward (page 5), so bit 0 is forward. The game's menus agree, answering the forward switch as they answer the cursor-up key, and so does the owner's Amiga: pushed forward, the stick climbs.

The game had been right all along; the names were wrong. The specification, the notes, the page's keys and the harness's letters were turned round, and tests hold the facts now: two run the original, and a page test in both browsers holds the up and down keys and watches what the core is handed. No reading of the stick's bits is taken over what the running original answers. The slip was made in reading the listing, chapter 4's subject; what caught it was the headless original of chapter 6, which asked the original instead of the reader of the listing.

## The shift that lost its sign

We trusted the [oracle](../glossary.md#oracle) of chapter 5 to run the game's code as a [68000](../glossary.md#68000) does: it is built on the processor emulation of QEMU, a well-known emulator, and its self-test agreed with the project's own decoder on every packed file. Then its test of the routine that moves the bombs, rockets and torpedoes failed over random states while the port was right: a bomb bouncing on a runway came out of the original with a vertical speed of +9 where a 68000 gives −2. The emulator made a [memory-form shift](../glossary.md#memory-form-shift) logical where the instruction asks for arithmetic, as chapter 5 tells with its figure; a [hook](../glossary.md#hook) corrects the three shifts that give a wrong result, a survey of every such shift found no other, and a test holds all of it. No mission script reached the bounce. A test that fails a right port is a finding about the instrument, and what caught this one was the oracle itself, over random states (chapter 5).

## Two runs that differed

The headless original was accepted when two runs of one description gave the same [dump](../glossary.md#dump), byte for byte, and a test holds that. Every check passed, and the clock looked harmless: the harness used it only to end a [slice](../glossary.md#slice) of emulation, after two seconds, or a whole run, so that a program caught in a loop could not hang a test. A slice normally reaches the next wait within milliseconds; it lasts two seconds only when the process gets no processor time for that long.

Then a run of the full suite on a busy machine failed one script, a flight to the enemy's carrier, in both of chapter 8's loops, once. Both loops compare with one recording of the original, made once in the run, and run alone, on a fresh recording, the same tests passed. Two recordings of that script, made with the same inputs and the same [entropy stream](../glossary.md#entropy-stream), parted from one tick on: the timer by which a damaged aircraft loses its oil stood at 43 in one and 44 in the other. With the inputs and the chance the same, the game cannot differ from itself (chapter 6), so the difference had to come from the instrument.

A fault that shows once in a full suite cannot be studied as it comes. So the slices were shortened to three thousandths of a second, which made the rare event frequent, and every recording differed; chapter 6 gives the figures. A timeout stops the emulation from a timer beside it, wherever the program is: it can make the next slice run an instruction a second time, or leave every code hook silent. Since then a slice ends after a count of instructions, at a place the program alone decides, and the wall clock only ever ends a run, as a failure the harness names Stuck; a test runs one flight in slices of three lengths and demands the same records. A failure that goes away when a test runs alone is not noise. With the inputs fixed it is a fault in the instrument, and the way to study a rare fault is to make it frequent. What caught this one was the full suite (chapter 24), and the comparison of two recordings that chapter 6's determinism allows.

## The core the tests shared

The tests drive the port through its [native library](../glossary.md#native-library), and a process that loads the library holds one copy of the core's state, shared by every test the process runs. Each test was believed to find the core as it needed it, since each sets up what it uses; every test passed alone, and the whole suite passed in its usual order. A test that passes alone and in the full run looks independent.

A leak, state one test leaves behind that a later test meets, was first met in the music tests: they ended their runs in a mission, with the shapes the game mirrors in place for a turn left mirrored, which breaks any test that reads the shapes as they lie in memory. They were made to leave a fresh core behind. That mend hid the next one. In the serial order the music tests' reset ran between the test of every map's setup and the shape tests, and so hid that the setup test leaked too. The suite takes about three hours in one process; to bring it to about one, it was run in several processes at once, each taking a share of the tests in an order that changes from run to run, with the outcomes compared test by test against the serial run's. The first such run failed tests of the shapes, the story scroller and the file loader that pass serially: in their process the setup test, which leaves the core in a mission, had run just before them.

The answer is a [**fixture**](../glossary.md#fixture): a function the test framework runs before a test, to set up what the test needs. This one runs before every test. Look at lines 12 to 16, which read the names the test asks for: a test that uses the port's core, the shared copy or one of its own, gets back the settings that the core's initialisation leaves alone, such as the VBlanks a pass and a fade step, because the tests set them from outside; a test that uses the shared copy gets it reset as well.

```python linenums="1"
--8<-- "generated/listings/py/fresh_core.py"
```

A fresh core costs under five thousandths of a second, little enough to give one to every test. It was then believed to isolate every test, and a later parallel run failed the [front end](../glossary.md#front-end)'s hand-over to the mission: the port's mission number was 3 where the original's was 1. The process had first run a [closed loop](../glossary.md#closed-loop) of a script on the third map, whose replay sets that number with a [poke](../glossary.md#poke), and the poke had outlived its test, because the core's initialisation does not touch the test instrumentation beside it. In the serial run, which takes the test files in alphabetical order, the front end's test came before the script's. Now everything beside the core's state but one setting, which every test that uses it sets itself, is put back before every test that takes the core, and [`re/notes/testing.md`](repo:re/notes/testing.md#a-fresh-core-for-every-test) lists that state item by item.

One more case was of the same kind. Where the original's state holds an address, the port keeps an offset (chapter 3), so the comparison names each pointer by what it points into, and a pointer into freed memory by the nearest start of a [sound sample](../glossary.md#sound-sample) below it that the run has seen. That record belonged to the process, not the run: a closed loop of the save script at another pass rate, run after other recordings, found [Paula](../glossary.md#paula)'s first channel named by a sound sample another recording had left. Every replay empties the record since, and the same run found one more thing, the next section's.

A test's result must not depend on what ran before it, and an order that never changes can hide such a dependence for ever: the last three leaks showed only when the order changed. What caught them was the suite run in parallel (chapter 24) and a closed loop run after others (chapter 8).

## The register carried as a long

A 68000 data register holds 32 bits, and an instruction on a word works on its lower half. The other half is the [**upper word**](../glossary.md#upper-word): the upper 16 bits of a 32-bit value, which in a data register an instruction on a word leaves as they were. In memory a long's upper word comes first, so a word instruction at a long's address works on the upper word, as in chapter 5's bounce, and an address register takes a word sign-extended, all 32 bits. So a value one routine leaves in a data register as a long reaches the next routine's upper word, unless something clears it. Chapter 3 gave an example from the game's hand-written routines, and chapter 4 said the port had to learn it. This is how it was learnt.

It came out of the check by another hand that chapter 8 describes: a closed loop of the save script on another seed and at pass rates the porter had never used. The check found the misnamed channel of the last section, and the search for its cause found a real difference beside it. At one [VBlank](../glossary.md#vblank) a [pass](../glossary.md#pass) there are twice as many passes, in which the ground targets are drawn and fire (chapter 7), and well into the run a dug-out's refill fell between two targets' fire. The port then placed the smoke the aircraft's engine gives off when a target's fire hits it almost exactly a pixel from where the original did. No script had exposed it at the pass rate the tests used.

The port treated the routines that walk the table of ground targets as working on words throughout. That had been observed: with [observers](../glossary.md#observer) on their entries over two scripts, the upper words of the two registers they take were 0 every time. Here is the routine that sends a soldier from the nearest barracks to refill an empty dug-out. Look at its first instruction, which saves D0, D2, D7 and address registers but not D1, and at the last but one, which puts back only what the first saved: a register the first does not save leaves the routine with whatever the routine left in it. Then look at `moveq #$1, d1`, which sets the whole of D1, all 32 bits, to the value 1, and at `neg.l d1`, which makes that −1, every bit set, when the soldier walks west.

```wingslst
--8<-- "generated/listings/asm/target_refill.lst"
```

So the refill leaves the soldier's direction in D1 as a long, and nothing between it and the next target's fire clears the upper word. That fire takes D1's upper word and, when the aircraft is at least as high as it is far, hands it on to the engine's smoke as the fraction of its position. The original's smoke took that word as part of its move; the port, assuming 0, left it out.

The port hands the upper word on from walk to walk now, as the original's D1 does. The specification gained a rule: never assume a register's upper word is 0 at a routine's entry because the scripts so far found it so. What caught the mistake was a closed loop at another pass rate, run by another hand (chapter 8); what guards against a repeat is the oracle tests of the targets and the ships' guns, which draw the upper words at random since (chapter 5).

## The last ticks nobody compared

A pass draws first and then runs its ticks: the inner loop calls `frame_update`, which draws, and then `run_queued_ticks`, which runs a [logic tick](../glossary.md#logic-tick) for each byte waiting. The dump records a pass where its drawing returns, so a pass's ticks come after the pass's record.

Every comparison of a [mission script](../glossary.md#mission-script) was believed to run to the script's end. The replay followed the original's schedule to the original's last pass, and every pass and tick up to there agreed; the last pass looked like the end.

A [control](../glossary.md#control), a deliberate break of the port (chapter 8), was made for the demo, a recorded game played back (chapter 17): its playback was made to end one input byte of the recording late. Such a late end shows only in the ticks after the last pass's drawing, and the replay stopped before them. With the old end in place the comparison passed; only once the replay ran on through the last ticks did the control fail, at tick 100 of its script. Until then the last ticks of every mission script had never been compared.

![One row of the original's last records, P T P P T, the last pass P and its tick T after it; a bracket under the last two: the dump records the pass where its drawing returns, its tick run after it. Below, a dashed span to the end of the last pass, compared before, and a gold span to the end of the last tick, compared since.](../figures/replay-end.svg)

/// caption
The replay's end. The dump records the last pass where its drawing ends, and the pass's tick follows; the comparison used to stop at the last pass and runs to the last tick since. The one tick after the last pass is an example: a pass may have none, one or more.
///

The fix is a few lines. Look at `last_tick` on line 7, worked out beside `last_pass` from the original's records, and at the condition on line 19 that ends the loop, which now asks for both.

```python linenums="1"
--8<-- "generated/listings/py/replay_end.py"
```

The tails of every script are compared since. A control that does not fail is a finding, about the comparison as much as about the port, and a control that only the tail of a script can catch belongs in every milestone's set, so that the comparison is tested where it ends. What caught this mistake was a control (chapter 8).

## The rest of the record

The six are not all: the record holds more, all but one caught by an instrument or by the owner's own eyes, ears and keyboard, and a few were told in earlier chapters. The table lists the six and the ones that touched the port or an instrument; the handbook's list holds more about the test setup.

| What we believed | What showed otherwise | What changed |
|---|---|---|
| Bit 0 of the input byte is the stick pulled back | the headless original, asking the original's decoder (chapter 6) | bit 0 is forward everywhere; tests run the original to pin it |
| The emulator runs every instruction as a 68000 does | an oracle test over random states (chapter 5) | three shifts corrected by a hook, every such shift surveyed |
| Two runs always give the same dump | the full suite on a busy machine, then two recordings compared (chapter 6) | slices end after a count of instructions; the clock only ends a run |
| Each test finds the core as it needs it | the suite run in parallel (chapter 24) | a fresh core, and what lives beside it put back, before every test that takes the core |
| The upper words of the targets' registers are 0 | a closed loop at another pass rate, by another hand (chapter 8) | the word handed on, never assumed, drawn at random by the oracle |
| Every comparison runs to its script's end | a control only the last ticks could catch (chapter 8) | the replay runs to the original's last tick |
| The machine leaves the last four records of a map uninitialised, as the harness's memory suggested | a reading of the allocator the game calls, which asks for cleared memory (chapter 4) | the port hands out cleared memory as a rule, with a test |
| A flag read out of the emulator is the flag | flags read out came back stale, as the emulator works them out lazily; nine sequences whose flags the manual fixes (chapter 5) | flags are read inside the emulation |
| A saved game fits the 8,192 bytes the port's file system gives a file, a buffer of fixed size, sized from one save on the first map | the saves measured on all fifteen maps: seven are larger, and would not have been kept (chapter 17) | the buffer holds the largest save the port's tables allow, 12,412 bytes |
| The routine that restores the play screen after a dialog, ported from reading, is right | the closed loop of the save script, nearly a thousand passes differing (chapters 4 and 8) | the play screen is switched on again after a dialog |
| A loaded game's ships keep the guns the file gives them | the [completeness list](../glossary.md#completeness-list) over a loaded game: the original sets two of a cruise ship's guns itself after loading (chapter 8) | the port sets them as the original does |
| The page's canvases behave in Firefox as in Chrome | a black picture, where a canvas dropped the pixels written into it; later a measurement, half the frame rate at full screen (chapter 23) | the picture is drawn by the graphics card, with a plain canvas as the fallback |
| The page pauses and resumes cleanly around a moment in which it is hidden | the owner's Firefox in full screen, still and silent; a measurement of a window's change of state (chapter 23) | the shell keeps its own record; leaving full screen pauses |
| The key left of 1 has one code in every browser | the owner's keyboard: the diagnostics overlay would not open in Chrome and Safari (chapter 23) | both codes open it |
| The page names nothing of the machine that built it | the core's debug information, read before the release, held every source's full path (chapter 25) | the paths made relative; the release carries no debug information |

/// dev
The stories in the code: the harness asks the stick's decoder in `_joy_words` of [`tools/headless.py`](repo:tools/headless.py), whose `_drive` ends a slice after `slice_insns` instructions; the shifts' hook is [`tools/m68k_fix.py`](repo:tools/m68k%5Ffix.py), held by [`tests/test_headless.py`](repo:tests/test%5Fheadless.py); `fresh_core` and `fresh_settings` are in [`tests/conftest.py`](repo:tests/conftest.py), and [`tests/test_isolation.py`](repo:tests/test%5Fisolation.py) holds the reset, the pokes and the record of samples, `SEEN_SAMPLES` of [`tests/m4state.py`](repo:tests/m4state.py); the walks hand the upper word on in `wof_targets_3_draw` and `wof_targets_f_draw` of [`src/targets.c`](repo:src/targets.c); the replay's end is `Replay._run` of [`tests/m4compare.py`](repo:tests/m4compare.py).
///

## What comes next

Each of these beliefs was reasonable when it was held, and in all but one an instrument, or a reading of what the code really calls, decided against it. Chapter 10 tells how the work was arranged so that the instruments, not the readers of the listing, would decide: the way of working as a whole, its rules and its reviews, what it cost and what it took.

## Further reading

The files named here are in the repository, [`github.com/sy2002/wof-wasm`](repo:).

- [`CONTROLLER.md`](repo:CONTROLLER.md#pitfalls-that-cost-time), "Pitfalls that cost time": the record of the mistakes, kept as warnings.
- [`re/notes/headless.md`](repo:re/notes/headless.md): ["Input"](repo:re/notes/headless.md#input) and ["Unicorn, as it behaves here"](repo:re/notes/headless.md#unicorn-as-it-behaves-here).
- [`re/notes/porting-m5.md`](repo:re/notes/porting-m5.md): ["Registers that cross a call"](repo:re/notes/porting-m5.md#registers-that-cross-a-call) and ["The emulator's memory-form shift (observed)"](repo:re/notes/porting-m5.md#the-emulators-memory-form-shift-observed).
- [`re/notes/porting-m7.md`](repo:re/notes/porting-m7.md): ["The port"](repo:re/notes/porting-m7.md#the-port), ["Paula's channel 0 after the save"](repo:re/notes/porting-m7.md#paulas-channel-0-after-the-save) and ["Part 2: the controls"](repo:re/notes/porting-m7.md#part-2-the-controls).
- [`re/notes/testing.md`](repo:re/notes/testing.md#a-fresh-core-for-every-test), "A fresh core for every test".
- [`SPEC.md`](repo:SPEC.md), sections 3.3, ["Runtime model"](repo:SPEC.md#33-runtime-model), and 7.1, ["Arithmetic"](repo:SPEC.md#71-arithmetic).

Outside the repository: the [*Amiga Hardware Reference Manual*](https://archive.org/details/commodore-amiga-tech-ref-series-amiga-hardware-reference-manual-3rd-edition), on the joystick's register; Martin Fowler's ["Eradicating Non-Determinism in Tests"](https://martinfowler.com/articles/nonDeterminism.html), on tests that leave state behind for the next.
