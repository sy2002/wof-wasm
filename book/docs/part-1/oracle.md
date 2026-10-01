Chapter 5
{ .chapter-kicker }

# The oracle

A port that calls itself faithful has to be held to the original one routine at a time. By the end of this chapter you will know how a single routine is taken out of the original program, run on an emulated 68000 beside its port and compared with it on thousands of inputs, and why the project needed that before it had a running game to compare with. You will know what the tests compare and how widely, and what the word "verified" in the inventory of routines promises and what it does not. And you will see the instrument itself put to the test, which is how a fault in the emulator came to light.

## One routine at a time

The port was written from the [listing](../glossary.md#listing), routine by routine, and every ported [routine](../glossary.md#routine) names the address of its original (chapter 4). The obvious test of such a port is to run the whole game twice, the original and the port, and compare them. The project does that too, tick by tick, and chapter 8 tells how; it is the last word on whether the game behaves the same. But a comparison of whole runs can only say that the two part company, and from which tick on. Which routine went wrong, and on what input, still has to be searched for among hundreds.

Run one routine alone, on inputs the test chooses, and a failure names both. The test can also choose inputs that the recorded missions never produce. When the port was broken on purpose, a bomb's killing span made one pixel wider, the recorded [mission scripts](../glossary.md#mission-script) run against it went through unchanged, because none of them puts a running soldier at the edge of a span. The test of the routine alone, over random states of the game, failed. Chapter 8 tells of these deliberate breakages.

There was a third reason, at the very start. The first things the port needed were the loaders and decoders: the unpacker of the packed files, the reader of the pictures, the shapes, the font. They could be held to the original's own routines before anything could run the original whole. That is where the port began; the whole original running without a screen came after, and it is chapter 6's subject.

## The arrangement

The instrument that runs a routine on both sides is the [oracle](../glossary.md#oracle), as chapter 1 called it, and the tests it serves are [**differential tests**](../glossary.md#differential-test): tests that hand two implementations of the same thing the same input and demand the same output.

On the original's side runs Unicorn, a library that imitates processors. It is built on the processor emulation of QEMU, a well-known [emulator](../glossary.md#emulator), and lets the program that uses it watch and step in at any instruction or access to memory. Left to itself, Unicorn's emulation of Motorola's 68000 family starts as a ColdFire, a related chip that lacks instructions the game uses, so the oracle tells it to be a [68000](../glossary.md#68000). It gives it two megabytes of plain memory, room for the program, a stack and the test's buffers, and loads the game's program into it at the [fixed load layout](../glossary.md#fixed-load-layout) of chapter 3, with every [relocation](../glossary.md#relocation) applied. So each address in the listing is the routine's own: a test calls `0x016FF6`, and `colour_lerp` runs.

On the port's side runs the port's C, compiled by the test machine's own compiler into a [**native library**](../glossary.md#native-library): the port built for the computer the tests run on, as a library a program can load, rather than as the WebAssembly of the page. The sources are the same, and the native library is what a test written in Python can call one routine of, directly. A handful of entry points for the tests alone, compiled into this library and nowhere else, reach the port's internals.

![Above, the same inputs from a fixed seed go to two sides. Left, the original: Unicorn as a 68000, the program Wings at the fixed layout, the routine called at its address with its arguments on the stack and A4 set, stubs for what is not under test, a trap address to return to. Right, the port: the same routine in C in the native library. Below, both outputs are compared: D0, the memory touched, the condition codes; equal, or the test fails.](../figures/oracle.svg)

/// caption
The oracle: one routine of the original under emulation, its port in the native library, the same inputs into both and the outputs compared.
///

## Calling a routine without its program

A routine expects to be called from inside the running game, with its arguments in their places, the game's variables in theirs and somewhere to return to. The oracle provides each of these.

A compiled routine is called as its callers call it, by the compiler's [calling convention](../glossary.md#calling-convention) of chapter 3: the test pushes the arguments onto the stack, two bytes for an [int](../glossary.md#int-the-c-type) and four for a long or a pointer, and reads the result from D0. Where the routine reaches the game's variables, the oracle sets A4 to `0x02AFFE`, the [small-data base](../glossary.md#small-data-base) the game's own code keeps there. A hand-written routine follows no convention but its own, so its test sets the [registers](../glossary.md#register) the routine was read to take: `text_width` of chapter 4 gets the text's address in A0 and its length less one in D0.

As the return address, the oracle pushes a trap address at which the emulation stops. A routine that has not arrived there after 50 million instructions fails the test, and so does one that touches memory outside the two megabytes, with the address and the instruction that touched it. A routine that goes astray is a failure with a place, not a test that hangs.

Most routines of the game read and write its variables. For them the test writes one state of the game into both sides. Every variable the port keeps is registered with its original address, so the test can copy a state between the emulated memory and the port, turning the byte order round, because the 68000 is [big-endian](../glossary.md#big-endian) and the test machine [little-endian](../glossary.md#little-endian). Afterwards it compares every registered variable and table that either side touched.

Some routines call things that mean nothing without the operating system. For those the test uses a [**stub**](../glossary.md#stub): a stand-in that answers for something the routine calls but that is not under test. The first tests need three. The game's wrapper around the system's memory allocator hands back a fixed buffer. The system's routine that clears a picture's memory returns at once, and the test clears the same bytes itself, so that both sides start from the same empty picture. Inside the routine that loads the game's font, the call that reads the file becomes "the font is here", because the font already lies in the emulated memory and the system's disk library does not. Nothing else is changed, and never the routine under test; later tests add a few stubs by the same rule, each with its reason written beside it in [`tests/original.py`](repo:tests/original.py).

## A test, read

Here is the test of `colour_lerp`, the step of a fade that chapter 4 showed beside its port, from [`tests/test_oracle_m1.py`](repo:tests/test%5Foracle%5Fm1.py). Look first at `compare`, which runs the original and the port on one step and two colours and, if they differ, fails with the input and both answers; then at the two kinds of input below it.

```python linenums="1"
--8<-- "generated/listings/py/test_colour_lerp_matches_over_its_range.py"
```

`Original()` on line 9 is one emulated machine with the program loaded; `ported` is the native library. The loops on lines 24 to 28 fade every colour to black and to white, and black to every colour, at each of the 16 steps: every fade the game runs. Lines 30 to 32 add 20,000 random triples of a step and two colours. The random numbers come from a fixed seed, the 11 on line 30, so every run draws the same inputs and a failure can be repeated exactly. Set `WOF_SLOW_ORACLE=1` and lines 17 to 22 run the whole cross product instead, every step from every colour to every colour, which takes about an hour and a half.

## Every input, or many

The tests follow one rule: where a routine's inputs are few, all of them; where they are many, random ones from a fixed seed, with the edges added by hand. The first tests, of the loaders and decoders, show the first half. The unpacker runs on every packed file of the disk and on random streams besides, including a control byte that means 128 literal bytes. The routine that finds a shape by its name is asked every name the game's lists hold and every name a container carries, in each of the twelve containers. Every shape is converted to the port's pixels and compared. Every shape of the player's aircraft, which the game mirrors in place whenever the aircraft turns round, is mirrored by both sides and compared, then mirrored again and required to come back as it was.

/// figures
| The first tests | What they cover |
|---|---|
| Packed files, through the unpacker | all 10, and 40 random streams |
| Files, through the loader | all 55 the port carries |
| Shapes, converted to pixels | all 1,049 |
| The player's aircraft, mirrored and back | all 216 shapes |
| The fade's arithmetic | every step of every fade, and 20,000 random colours |
| Pictures and palettes | all 12 and all 6 |
| Oracle tests in the suite today | over 300 |
///

The later routines work on the game's state, and their inputs are random states: the player's flight is compared over 3,000 of them, the movement of the bombs, rockets and torpedoes over 2,500, the writer of a saved game over 600.

Drawing is the exception. The original draws its shapes with the [blitter](../glossary.md#blitter), so the result never passes through the processor, and the emulator has no blitter. The oracle maps the chips' addresses as plain memory instead, and every time the original's drawing routine writes the register that starts a blit, the test captures all the blitter's registers as they stand. A small model of the blitter, [`tests/blitter.py`](repo:tests/blitter.py), replays that programme on a copy of the picture, and the pixels are compared with the port's. The clipping arithmetic, the addresses, the sizes and the masks in that comparison are the original's own. The blitter's way of combining them is documented hardware behaviour that the project modelled, not something derived from the original, so a mistake in the model would pass unseen. One test leaves the port out altogether: drawn over a picture all of zeros and one all of ones, a blit may change no pixel outside the shape's own box within the clip, which is what lets the port clip pixel by pixel. Chapter 12 returns to the model.

## What verified means

Chapter 4 listed the statuses the inventory gives a routine. A routine is [verified](../glossary.md#verified) when it is ported and held to the original by a test of its own, and for a [pure routine](../glossary.md#pure-routine), one that computes from its inputs alone, that test is the oracle's and is due before the status is set. About a quarter of the 616 routines of the [routine inventory](../glossary.md#routine-inventory) are verified. The status is written by hand and no tool checks it; what stands behind it is the test.

What it does not promise matters as much. The oracle holds a routine on the inputs its test hands it. It does not hold that the port calls the routine at the right moment, with the state the game would have at that moment; that is the work of the comparisons of whole runs, which also hold the routines that read or draw the world as a whole (chapter 8).

A test is also only as good as its inputs. A register's upper half was once assumed to be zero at a routine's start, because every recorded run had found it so, until a run found it otherwise; chapter 9 tells the story. Since then the rule is never to assume it, and the oracle tests of the later routines draw it at random.

And the oracle holds the port to the original as the emulator runs it. If the emulator were wrong, a test would fail a right port, or hold a port to a wrong answer. So the instrument has to be checked too.

## The instrument is checked too

[`tools/oracle.py`](repo:tools/oracle.py), run on its own, tests itself: it runs the original's unpacker on all ten packed files and compares what comes out with the project's decoder in Python, [`tools/rpck.py`](repo:tools/rpck.py), and prints PASSED or FAILED. That decoder is in turn what the test of the port's loader holds all 55 files to. Each link of the chain is a comparison that leads back to the original's own code.

A harder lesson came from a test that failed where the port was right. Two words are needed to tell it. A shift moves the bits of a number along; one place to the right halves it. An [**arithmetic shift**](../glossary.md#arithmetic-shift) right copies the sign bit into the top, so a negative number stays negative and is halved, rounded down. A [**logical shift**](../glossary.md#logical-shift) right fills the top with a zero, which suits a number without a sign and turns a negative one into a large positive one. The 68000 has both, for a register and for a word in memory; a [**memory-form shift**](../glossary.md#memory-form-shift) is one that shifts a word in memory by one bit, without a register.

The oracle test of `object_step`, the routine that moves the bombs, rockets and torpedoes, failed over its random states. When a bomb comes down on an airfield's runway, the routine bounces it: it turns the vertical speed round, halves it and caps it at 9, then halves the horizontal speed too, and once either has come to zero the bomb is done. These are the lines:

```wingslst
--8<-- "generated/listings/asm/object_step_bounce.lst"
```

A speed is a long here, its upper word the whole pixels a tick and its lower word the fraction. `neg.l` turns the vertical speed round, and `asr.w`, an arithmetic shift right of a word in memory, halves its upper word; `cmpi.w`, `blt.w` and `move.w` cap it at 9. The second `asr.w` halves the horizontal speed the same way, and the `bne.w` after it branches on whether the result was zero. On one of its random states the port turned a vertical speed into −2 and the original, under the emulator, into +9. The word to be halved was `0xFFFD`, which is −3. A 68000 shifts it to `0xFFFE`, which is −2. The emulator shifted it to `0x7FFE`, as if it had no sign, a large positive number that the routine capped at 9.

The reason lies in the instruction's first word, its [opcode](../glossary.md#opcode). A shift of a register keeps its type, arithmetic or logical, in two low bits of that word. A shift of a word in memory needs those bits to say where the word lies, and keeps its type higher up. The emulator reads the same bit, bit 3, in both forms.

![Two 16-bit words. Above, an arithmetic shift of register D4 right by one, 0xE244: bits 4 and 3 hold the type, 00 for arithmetic, and bit 3 is marked. Below, an arithmetic shift of the word 0x12 bytes past A2, 0xE0EA: bits 11 to 9 hold the type, 000 for arithmetic, bits 5 to 3 the mode 101, an address register with an offset, and bit 3, a 1, is marked.](../figures/shift-bits.svg)

/// caption
One bit, two meanings. In a shift of a register, bit 3 is the low bit of the type; in a shift of a memory word it belongs to the mode, which says where the word lies. The emulator takes it for the type in both, so an arithmetic shift of a word reached through an address register with an offset, as the game's are, runs as a logical one.
///

One failing case says little about the rest, so we went through every shift and rotate with a memory operand in the whole program, 48 in all. Three are arithmetic shifts of that kind, which the emulator gets wrong: the two of the bounce, and one in a compiled routine that builds a copper list, where it halves one of the routine's arguments when a flag of its own is set:

```wingslst
--8<-- "generated/listings/asm/cop_vport_planes_shift.lst"
```

The port builds its copper lists its own way, so that one matters only to the whole original running under the emulator. The one logical shift of a memory word comes out right, by the same fault. Two left shifts give the right word and a wrong overflow flag, which the next instructions overwrite before anything reads it. The other 42 are rotates in the routine that scrolls the ticker's text, and the emulator executes them right.

The correction is a [**hook**](../glossary.md#hook): a routine of the test's own that the emulator calls whenever the program reaches a chosen instruction or touches chosen memory. [`tools/m68k_fix.py`](repo:tools/m68k%5Ffix.py) puts one on each of the three instructions. It works out the word's address from the instruction, shifts the word as a 68000 does, sets the five flags as a 68000 would, and moves the program counter past the instruction, so the emulator never executes it. The flags are not a nicety: the `bne.w` after the second shift reads them. Here is the shift, and then the hook:

```python
--8<-- "generated/listings/py/asr_word.py"
```

```python
--8<-- "generated/listings/py/_shift.py"
```

The oracle installs the hook whenever it loads the game's program, and the whole original that chapter 6 runs is built on the oracle, so both instruments carry the correction. A test holds all of it: it first demands that the emulator still shifts wrongly, so that a corrected emulator will announce that the hook can go; then that the hook gives the 68000's word and flags, that the next branch sees them, and that its list holds every arithmetic shift of a memory word in the listing.

No recorded mission reaches the bounce, and the comparisons of whole runs passed with the correction as they had passed without it. Only a test that drew its inputs at random could meet the fault, and only a port that computes as a 68000 does could show it up.

## Flags that go stale

The second check concerns the [**condition codes**](../glossary.md#condition-codes): five bits the 68000 sets after most instructions, saying whether the result was negative (N), zero (Z) or too large for its width (V), whether a carry came out (C), and a copy of the carry for longer arithmetic (X). They are kept in the low byte of the status register, and a conditional branch reads them. So the flags a routine leaves are part of what it does, as the `bne.w` after the bounce's shift shows. The program also branches on what its floating-point routines leave in them, at five places. All five lie in a number formatter that the game, as it turns out, never runs; the port keeps the flags all the same.

To compare flags, the oracle must read them, and Unicorn does not hand them out reliably. It works the flags out lazily, only when an instruction needs them, and reading the status register from outside gives whatever was last worked out. After `addq.w #1` on `0x7FFF` it reports a negative result without the overflow, where a 68000 sets both. After `tst.w` on `0x00010000` it reports nothing at all, where a 68000 sets Z.

The oracle's answer is to let the routine return through two instructions of its own: a move of the status register into a memory slot, then a jump to the trap address. Neither changes a flag, and the move runs inside the emulation, which forces the flags to be worked out first. The instrument is tested before it measures anything: nine short hand-made sequences of instructions, whose flags Motorola's manual fixes, run through the oracle, and all but one of them would come out wrong if it still read the lazy register.

## The ROM's own floating point

The game's flight model computes in [fast floating point](../glossary.md#fast-floating-point), whose routines lie in the [Kickstart](../glossary.md#kickstart) ROM, not on the disk. The tests run them under the oracle: the ROM image is mapped into the emulated memory, the floating-point library is found in it by its name, and it is called through the game's own entry points. The port's nine operations are the ROM's instructions transliterated one by one into C, because a browser's own floating point rounds differently and the flight would drift; they are held to the ROM's in the result, the second register and the condition codes. The tests use over 27,000 cases: the known edges, random numbers shaped to make the hard cases frequent, and every pair of numbers the game was seen to hand the library in a run. They run on the native library, in WebAssembly and under a checker that stops at any undefined behaviour of C. Beside the suite, a longer run, [`tools/ffp_soak.py`](repo:tools/ffp%5Fsoak.py), takes a million random operands for each operation; at its last run not one result differed. Chapter 14 tells what the game computes with them.

/// dev
The oracle is [`tools/oracle.py`](repo:tools/oracle.py): `Oracle(a4=0x02AFFE)`, then `o.call(address, o.W(word), o.L(long), regs={'a0': ...}, ccr=True)`, which returns D0 and leaves the flags in `o.ccr`. [`tests/original.py`](repo:tests/original.py) wraps the original's routines with their stubs, and `Ported` in [`tests/conftest.py`](repo:tests/conftest.py) reaches the port through [`tests/shim.c`](repo:tests/shim.c). The three shifts the hook corrects lie at `0x010BB8` and `0x010BE0` in `object_step` and `0x019D5E` in `cop_vport_planes`; [`tests/test_headless.py`](repo:tests/test%5Fheadless.py) holds the fault and the list. `WOF_SLOW_ORACLE=1` runs the full ranges of [`tests/test_oracle_m1.py`](repo:tests/test%5Foracle%5Fm1.py), and [`tools/ffp_soak.py`](repo:tools/ffp%5Fsoak.py), given a count and a seed, a shorter or another soak.
///

## What comes next

The oracle runs one routine at a time. Chapter 6 runs the whole program under the same emulator, from its `main` routine on, with stubs for the operating system and hooks to watch it: the headless original, the reference that the comparisons of whole runs are made against.

## Further reading

The files named here are in the repository, [`github.com/sy2002/wof-wasm`](repo:).

- [`SPEC.md`](repo:SPEC.md), section 4, ["Tools"](repo:SPEC.md#4-tools), with its paragraph on the oracle; 7.1, ["Arithmetic"](repo:SPEC.md#71-arithmetic); 7.4, ["Working method"](repo:SPEC.md#74-working-method); 8, ["Verification"](repo:SPEC.md#8-verification).
- [`re/notes/porting-m1.md`](repo:re/notes/porting-m1.md), ["How the tests establish it"](repo:re/notes/porting-m1.md#how-the-tests-establish-it); [`re/notes/porting-m5.md`](repo:re/notes/porting-m5.md), ["The emulator's memory-form shift (observed)"](repo:re/notes/porting-m5.md#the-emulators-memory-form-shift-observed); [`re/notes/headless.md`](repo:re/notes/headless.md), ["Unicorn, as it behaves here"](repo:re/notes/headless.md#unicorn-as-it-behaves-here); [`re/notes/ffp.md`](repo:re/notes/ffp.md), ["The port"](repo:re/notes/ffp.md#the-port).
- [`tools/oracle.py`](repo:tools/oracle.py), [`tools/m68k_fix.py`](repo:tools/m68k%5Ffix.py), [`tests/original.py`](repo:tests/original.py), [`tests/test_oracle_m1.py`](repo:tests/test%5Foracle%5Fm1.py) and its successors, [`tests/blitter.py`](repo:tests/blitter.py).

Outside the repository: Motorola's [*M68000 Family Programmer's Reference Manual*](https://archive.org/details/m68000familyprog0000unse), for the shifts, their encoding and the condition codes; [Unicorn Engine](https://www.unicorn-engine.org/), the emulator.
