Chapter 8
{ .chapter-kicker }

# Porting a mission

Chapters 5 to 7 built the instruments; this chapter puts them to work on the game's missions. By its end you will know how we decided which routines to port at all, and what the port does where it lacks the original's code; how the mission scripts grew from one mission to a campaign, and why an autopilot flew some of them; the two ways the port is compared with the original, and why it takes both; how a list makes sure that nothing the original writes escapes the comparison; and why we broke the port on purpose.

## More than the game runs

A faithful port translates what the original's code does (chapter 1), which raises a question the listing cannot answer: which code does the game run? The executable holds more than the game: the C library the compiler linked in, the code that talks to the operating system, the crack's text screen, debugging aids, routines nothing calls. Code that never runs cannot be compared with the original, so a port of it could be wrong and nothing would ever say so. The port therefore carries what the game runs, and the first instrument of this chapter finds out what that is.

The [**reach map**](../glossary.md#reach-map) is the record of which routines the [mission scripts](../glossary.md#mission-script), the recorded hands of chapter 6, execute in the [headless original](../glossary.md#headless-original), and where. A tool runs each script with a [hook](../glossary.md#hook) on the first instruction of each of the 616 routines of the [routine inventory](../glossary.md#routine-inventory) and counts every entry by two coordinates. The phase is chapter 7's: inside a [VBlank](../glossary.md#vblank)'s server, inside the tick's routines, inside the pass's routines, or in the main program outside them. The window says how far the program's main routine, `main`, has got, which the tool reads off the instruction `main` has just reached:

| Window | Where `main` is |
|---|---|
| `front` | from the program's start to the outer loop |
| `outer` | the head of the outer loop, up to the rank selection |
| `rank` | the rank selection |
| `pre-briefing` | loading the dashboard's pictures and the mission's map |
| `briefing` | the mission's briefing |
| `setup` | from the briefing's end to the moment the setup is done, which the tools call step S |
| `mission` | from step S to the mission's end |
| `between` | from a mission's end to the next mission's briefing, when the campaign goes on |
| `after` | the mission over: the fade, the high scores, back to the outer loop |

So the map answers when, not only whether. Among the first milestone's scripts, the routine that draws a line runs in the landing alone, while the aircraft hangs on the arresting cable: it draws the cable. The flag that makes a mission a night mission is written by one routine, which runs only between two missions of a campaign, so the first mission after the program starts is always flown by day.

That a routine runs is not enough, because it can run in every tick and still have a branch no flight takes. So the tool can also record every stretch of instructions the processor executes between two branches, and say, for each routine the port carries, which of its instructions no run executed. Such a stretch is a [**cold region**](../glossary.md#cold-region): a part of a ported routine that no run executed. Every cold region must be accounted for, by the marker of a stand-in, the next section's subject, or by a note saying what it is: ported from reading and held by an oracle test whose random cases run it, unreachable, or data between instructions. A region that is neither makes the tool fail.

Those lists decided each routine's status in the inventory of chapter 4: `partial` while a stand-in was left in it, `ported` when the scripts ran it and the comparisons below held it, [verified](../glossary.md#verified) when a test of its own held it as well, as the [oracle](../glossary.md#oracle) holds the regions the scripts leave cold. Chapter 4's code map shows the result along the code's addresses. Over all the scripts, 440 of the 616 routines are entered at least once.

## Stand-ins that fail loudly

What the scripts never execute, the port does not carry. In its place is a [**stand-in**](../glossary.md#stand-in): a marked place in the port's C where the original has code the port does not carry. It is one call of a macro, `WOF_STANDIN`, whose marker names the milestone that owes the code and the first address of what it stands for, so that the tool can match the marker to its cold region. A stand-in is not a [stub](../glossary.md#stub): a stub answers for the operating system inside the instrument, a stand-in marks a gap in the port.

Reaching a stand-in counts in the game's state, which the port's diagnostics overlay shows. In a test build it is also logged by name, and every comparison fails when that log is not empty. In the release build, which has no test hooks at all, it does the least harmful thing it can: it skips what it stands for. A test reads the function names in the release's WebAssembly and fails if a test hook is among them.

The loudness has a reason: a port that met code it lacks and carried on would differ from then on, and the difference would surface later and elsewhere, as a puzzle. A stand-in turns it into a failure where the script left the ported ground, with the place named.

Here is a stand-in left in the finished port, in the routine that starts a [sound sample](../glossary.md#sound-sample) on one of [Paula](../glossary.md#paula)'s channels. Look at the marker on line 19: the milestone that owed it, M8, the address it stands for, `0x01EA3A`, and above it the reason, read from the listing: no caller ever asks for channel 6. Past the marker, the routine skips the hand-over that channel 6 would start and plays on channel 2.

```c linenums="1"
--8<-- "generated/listings/c/channel_play.c"
```

Eighteen markers are left in the finished port. Seventeen stand for what the game never does, among them commands it never gives its music player, values its songs never hold and a channel no caller asks for. One stands for a value, a table of soldiers with every record in use, which the game's own bookkeeping never lets happen and a test watches for.

## From one mission to a campaign

The port was built in milestones, each with its scripts, its reach map and its stand-ins:

| Milestone | Accepted when | Scripts | Cold regions left marked for later milestones |
|---|---|---|---|
| M4, the world and the player | a mission started, flown and ended by a landing or a crash | 11, and 20 runs of the keys in a mission | 55 |
| M5, the weapons and the ground targets | the same on the first three maps | 18 | 24 |
| M6, the enemy aircraft and the ships | the same on all fifteen maps | 25 | 3 |
| M7, the campaign | a full campaign playable | 6, and 8 runs of loaded games and demos | none |

Each milestone's cold list named what the later ones owed, region by region, and every marker carried the milestone that would replace it. So the next milestone's plan was not a guess but the list of stand-ins its scripts had to reach. Each milestone was itself done in two parts, cut by chapter 7's phases: first what its scripts run in a pass and a VBlank, then what they run in the tick.

The scripts kept to the ground the port had. Holding the fire button in level flight fires the guns, and a flight left alone too long brings the enemy's aircraft up, both later milestones' work. So the fuel flight and the weapon scripts hold the button only inside their turns, where it fires and drops nothing yet still resets the countdown that would send the enemy.

Some states no flight of a script's length reaches. The first rank's campaign begins with map a, and maps b and c follow only after winning a and b, which was M7's work. A script reaches them with a [**poke**](../glossary.md#poke): a value written into one address of the game's state at a fixed point of the run, on both sides, the original and the port, so that the comparison stays fair. The scripts for maps b and c poke the mission number at the end of the rank selection; the night mission pokes the flag for the night there.

## Scripts flown by an autopilot

A script is a list of runs, each a number of VBlanks with the letters of the stick and the button held during them: `U` forward, `D` back, `L`, `R`, and `F` for fire (chapter 6). A take-off is easy to write so. A landing is not: the aircraft must come in low over the bow at the right moment and the right speed, and that moment depends on everything before it.

So we flew the headless original with an [**autopilot**](../glossary.md#autopilot): a program that looks at the game's state every VBlank and chooses the stick and the button by a policy, a set of rules written for one task, recording its choices. Compressed into runs, the choices are the script. The original is deterministic for a given schedule (chapter 6), so the script then flies the same flight again without the autopilot, in the original and in the port.

The landing came out of a few rounds of observation. The approach comes from the right with the aircraft facing left, as the manual teaches (page 6), on a glide path that loses 0.08 pixels of height for every pixel flown towards the bow. At the bow the stick goes forward alone, and it stays forward after the touch-down. The last rule is the original's: on the deck a flag is set whenever the aircraft is fast and the stick is not forward, and while it is set the hook never catches a cable.

Here is the script the autopilot left, from [`tools/m4_scripts.py`](repo:tools/m4%5Fscripts.py). `PILOT` is the start: the front end, bombs chosen in the hold, the lift and the roll to the right. Forward climbs by default (chapter 1), so `RU` is a climb to the right. Look at the short runs of four to twenty-four VBlanks in the middle: the approach, the policy correcting the glide path a little at a time. `U` alone after it is the stick forward at the bow and on the deck; then come the taxi to the lift, the next weapon in the hold and a second take-off.

```python linenums="1"
--8<-- "generated/listings/py/LANDING.py"
```

The later autopilots added what their milestones needed. M5's drops a bomb where the game's own arithmetic, run ahead, says it will come down on a target. M6's flies a dogfight, holding the button through the close chase, because the guns fire only after ten VBlanks held and a shorter press drops the other weapon. M7's replays a script that wins its mission and flies on into the next. Where even the autopilot could not get after real attempts, as with winning the third map, which earns a promotion, or shooting an enemy down over land, a poke set the state instead.

## Two loops

The recorder runs a script in the headless original and keeps a [dump](../glossary.md#dump) of the game's state after every pass and every tick, the drawing calls, every value read from the [entropy stream](../glossary.md#entropy-stream) with the routine that asked, and the addresses each tick wrote. The port then replays the same [schedule](../glossary.md#schedule): the keys and the stick of every VBlank, and a [pass](../glossary.md#pass) wherever the original began one, which chapter 7 showed to be part of the input. The fades take no time in the port, as they take none in the headless original (chapter 7). The port can then be run against the recording in two ways.

In the [**open loop**](../glossary.md#open-loop) the port is set to the original's state before every pass and every tick, so that each step is compared alone. From step S on, the original's state after each step is handed to the port: the game's variables and tables, which of the two screens is in front, how far the entropy stream has got, and which way the shapes that the tick mirrors in place are facing. A difference then names its step: this pass or this tick, with nothing before it to blame.

In the [**closed loop**](../glossary.md#closed-loop) the port runs on its own from the program's start, the [front end](../glossary.md#front-end), the screens before the mission, included, and is compared after every pass and every tick, so that every error it carries over shows. It is handed only the seed of the entropy stream and one address, where the original's allocator put the map's records, because a defect of the original takes that address for a position (chapter 20).

![Three rows over the same steps: at the top the original's records after the front end, S, P, T, P, P, T, P; in the middle the open loop, the port's steps with the original's state handed down from each record to the port's next step and every pass and tick compared; at the bottom the closed loop, the port on its own from the program's start, given only the entropy seed and the map list's address, every pass and tick compared.](../figures/two-loops.svg)

/// caption
The two loops. S is the setup's end, P a pass and T a tick, in the order of a quiet scene at two VBlanks a pass (chapter 7). The open loop is handed the original's state after every step; the closed loop is handed nothing after its start.
///

Each loop does what the other cannot. The open loop is the sharp one: it says where a difference arises. It also lets a milestone be held while half done. The pass's part was ported first, and its scripts then reached stand-ins in the tick; since every step starts afresh, each differing step can be judged alone: it must have reached a stand-in in that same step, or the fault is the port's. The closed loop is the honest one. In the open loop, whatever the port carries from one step to the next is replaced by the original's before it can matter; the closed loop replaces nothing, so all of it must come out right on its own, as in your browser. Every script of the later milestones runs in both, the closed loop with no stand-in reached and the open loop with no step differing: some 160 tests.

## What is compared

After every pass both loops compare:

- every variable and table of the game the port keeps, each registered under its original address, so that the original's memory can be read into the port's form field by field (chapter 22);
- the drawing calls: which shape, where, with which arguments;
- the values read from the entropy stream, each with the routine that read it;
- which of the two screens is in front;
- the [palette](../glossary.md#palette) of every row of the picture;
- the map's records as drawn, against a decoder's prediction from the original's map;
- the sound samples started, and the state of Paula.

After every tick they compare the same state, the tick's own drawing calls and random reads, which way the mirrored shapes face, and the VBlanks the tick waited, since a tick can wait inside the restart (chapter 7). Here is the check after a pass, from [`tests/test_world.py`](repo:tests/test%5Fworld.py), which drives the replay of [`tests/m4compare.py`](repo:tests/m4compare.py). Look at the eight names under which a difference is filed, from `'state'` on line 7 to `'paula'` on line 30; for the drawing calls and the random reads it files the first that differ, the original's beside the port's.

```python linenums="1"
--8<-- "generated/listings/py/compare_passes.on_pass.py"
```

The setup is compared on its own, at step S: everything it wrote, its own tick included, on every one of the fifteen maps and for the first mission of every rank.

Two things are not compared directly, as chapter 1 said. The pixels: the headless original draws nothing, so no picture of its mission exists. The drawing calls and the palette of every row stand for them, with a model of the [blitter](../glossary.md#blitter) through which the original's own drawing routine draws every shape, pixel for pixel against the port's. And the sound as you hear it: what is compared is the log of every sound sample started, with its channel, pitch and volume, and Paula's state, not the waves the browser plays (chapter 18).

## The completeness list

A comparison compares what it is given: a variable the porter forgot to register would be compared nowhere, and its difference would never show. The [**completeness list**](../glossary.md#completeness-list) closes that gap: it sorts every address the original writes during a mission, in any phase, into a registered field, state compared in another form, or state not kept, with its reason and the milestone that owes it. An address that is none of the three fails the test.

Each row names the routines that write its range, and a write by any other routine makes the address uncovered again, because a new writer can mean a new meaning. The first milestone's test also fails on a row no run needs any more, so that its list cannot go stale. Here are the two rows of the second kind, from [`tests/m4complete.py`](repo:tests/m4complete.py). Look at the writers in braces, and at each row's last field, which says how the port carries the state: the double buffer as the index of the screen in front, the colour tables as the palette of every row.

```python linenums="1"
--8<-- "generated/listings/py/COMPARED.py"
```

The rows of the third kind give their reasons. The graphics library's descriptions of screens and pens are not kept, because the port's screen model replaces them; nor the [copper](../glossary.md#copper)'s lists, whose effect is the palette of every row; nor the allocator's bookkeeping, nor the files as they are read. Each milestone has a completeness test of its own.

/// figures
| The completeness list | How many |
|---|---|
| Globals the port registers under their original addresses | 252 |
| Tables, and blocks of memory, kept at fixed places | 30 and 21 |
| Rows of state compared in another form | 2 |
| Rows of state not kept: address ranges, and kinds of block | 35 and 10 |
///

## Breaking the port on purpose

A comparison that has never failed may be unable to fail: it may compare the wrong thing, or too little, and a test that has only ever passed looks no different from one that guards a correct port. So the milestones were closed with [**controls**](../glossary.md#control): deliberate changes of the port in one place, each run through the test that must catch it. A control passes when its test fails, and the first step where the change showed is named, so that the test is seen to fail for the change itself. About fifty were run and reverted, M7's in a library built from a copy of the sources, so that the port itself was never touched. A few:

| What was changed in the port | Script, or test | Where it first showed |
|---|---|---|
| a random read of a drawing routine skipped | `climb` | pass 424: one value fewer, named with its caller |
| forward and back swapped where the tick takes its byte | `turns` | the first tick with the stick forward |
| the restart's last wait for the next picture removed | `lost` | the restart's tick, one VBlank short |
| a row of the completeness list removed | the completeness test | the range and its writer named |
| a pointer of a loaded game kept as the file gave it | `load_disk` | the player's shape after the load |
| the demo's byte stored before the input sample, not after | `demo_record` | the first pass |
| a demo's playback ended one entry late | `demo_play_ff` | the tick where it should have ended |

Two controls run the other way: changes that must leave the result alone. Chapter 7 showed that the tick does not depend on how many VBlanks a pass takes, as long as the [couplings](../glossary.md#coupling) are reproduced, so the closed loop must hold at one and three VBlanks a pass as at two, against the original run at the same rate; it does, for scripts of every milestone. And the port with the [vertical flip](../glossary.md#vertical-flip) on, flying the turns script with forward and back exchanged, must fly the original's flight: every pass and tick agrees, but for the flip's own byte.

The controls also show what an instrument cannot see. A bomb's killing span made one pixel wider went through the scripts' comparisons unchanged, because no script puts a running soldier at the very edge of a span. The oracle caught it on random states, as chapter 5 told, and an oracle test of the tick places running soldiers at the edges of the guns' span on purpose.

## A check by another hand

One rule of the project completes the method: whoever reviews a report that the comparisons hold makes one check of their own that the porter's tests could not make. For a milestone of missions, that is the comparison run again on scripts, maps and an entropy seed the porter never used, and, where stand-ins are left, every differing pass of the open loop attributed to a stand-in reached in that same pass. The porter chose the scripts, the maps and the seed; the check runs on ones the porter did not choose.

/// dev
The reach map is [`tools/reach_observe.py`](repo:tools/reach%5Fobserve.py): block coverage and the fifteen setups with `--blocks --setups --json REACH.json`, and with `--cold` and such files the cold regions of every ported routine, failing on one without a marker or a note. A stand-in is the macro `WOF_STANDIN` of [`src/wof.h`](repo:src/wof.h), counted in [`src/core.c`](repo:src/core.c) and logged in [`src/trace.c`](repo:src/trace.c). The recorder and the replay are `Recorder` and `Replay` in [`tests/m4compare.py`](repo:tests/m4compare.py), and the completeness list is [`tests/m4complete.py`](repo:tests/m4complete.py); the loops of M5 to M7 are [`tests/test_weapons.py`](repo:tests/test%5Fweapons.py), [`tests/test_enemy.py`](repo:tests/test%5Fenemy.py) and [`tests/test_campaign.py`](repo:tests/test%5Fcampaign.py). A script is recorded once in a process and shared by the tests that replay it. The autopilots are [`tools/m4_autopilot.py`](repo:tools/m4%5Fautopilot.py) to [`tools/m7_autopilot.py`](repo:tools/m7%5Fautopilot.py), run with a plan's name. [`tools/m7_controls.py`](repo:tools/m7%5Fcontrols.py) builds each of M7's controls into a library of its own and points the tests at it through `WOF_CORE_LIBRARY`.
///

## What comes next

The chapter in one sentence: the port carries what the scripts run and marks the rest, and two loops, a list and deliberate breakages hold it to the original, step by step. These instruments caught mistakes, the port's and their own. Chapter 9 tells them, each with what caught it: the stick's bits, the memory-form shift, the timeout, the shared core, the register carried as a long, and the last ticks nobody compared.

## Further reading

The files named here are in the repository, [`github.com/sy2002/wof-wasm`](repo:).

- [`re/notes/porting-m4.md`](repo:re/notes/porting-m4.md): ["What decides what is ported: the reach map"](repo:re/notes/porting-m4.md#what-decides-what-is-ported-the-reach-map), ["How the port is held to the original"](repo:re/notes/porting-m4.md#how-the-port-is-held-to-the-original), ["The completeness list"](repo:re/notes/porting-m4.md#the-completeness-list), ["What stands in, and where"](repo:re/notes/porting-m4.md#what-stands-in-and-where) and ["The scripts of part 2"](repo:re/notes/porting-m4.md#the-scripts-of-part-2).
- [`re/notes/porting-m6.md`](repo:re/notes/porting-m6.md#the-dogfight), "The dogfight"; [`re/notes/porting-m7.md`](repo:re/notes/porting-m7.md#part-2-the-controls), "Part 2: the controls".
- [`SPEC.md`](repo:SPEC.md), sections 7.3, ["Determinism"](repo:SPEC.md#73-determinism); 7.4, ["Working method"](repo:SPEC.md#74-working-method); 8, ["Verification"](repo:SPEC.md#8-verification).

Outside the repository: Wikipedia's ["Code coverage"](https://en.wikipedia.org/wiki/Code%5Fcoverage), the kind of measure the reach map is, and ["Mutation testing"](https://en.wikipedia.org/wiki/Mutation%5Ftesting), the method the controls follow by hand.
