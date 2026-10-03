Chapter 8
{ .chapter-kicker }

# Porting a mission

Chapters 5 to 7 built the instruments; this chapter puts them to work on the game's missions. By its end you will know how we decided what to port, and what stands where the port lacks the original's code; how the mission scripts grew to a whole campaign, and why an autopilot flew some of them; the two ways the port is compared with the original, and why it takes both; how a list keeps anything the original writes from escaping the comparison; and why we broke the port on purpose.

## More than the game runs

A faithful port translates what the original's code does, which raises a question the listing cannot answer: which code does the game run? The executable holds more than the game: the C library, the code that talks to the operating system, the crack's text screen, debugging aids, routines nothing calls. Nor can the game's logic be held routine by routine alone: the [oracle](../glossary.md#oracle) holds one routine on inputs it is handed, but most routines read a world the others built, so only a run of the whole game can hold them (chapter 5), and a run reaches only what its scripts reach. Code no run executes could be ported, but no run would compare it, and a mistake in it would never show. So the port carries what the runs reach, and the first instrument here finds out what that is.

The port was built in numbered [**milestones**](../glossary.md#milestone), stages each ending with a working page and green tests: first the loaders, the headless original and the [front end](../glossary.md#front-end), the screens before and between missions, M1 to M3; then the missions, M4 to M7; the sound, M8, done before M7; and the page's drawing, M9.

The [**reach map**](../glossary.md#reach-map) is the record of which routines the [mission scripts](../glossary.md#mission-script), the recorded hands of chapter 6, execute in the [headless original](../glossary.md#headless-original), and where. A tool runs each script with a [hook](../glossary.md#hook) on the first instruction of each of the 616 routines of the [routine inventory](../glossary.md#routine-inventory) and counts every entry by two coordinates. The phase is chapter 7's: inside a [VBlank](../glossary.md#vblank)'s server, the tick's routines, the [pass](../glossary.md#pass)'s routines, or the main program. The window says how far `main`, the program's main routine, has got. The outer loop runs around a mission, from the title to the high scores; [**step S**](../glossary.md#step-s) is the moment the setup is done and the mission's loop begins, where chapter 6's dump keeps a record.

| Window | Where `main` is |
|---|---|
| `front` | the program's start |
| `outer` | the head of the outer loop |
| `rank` | the rank selection |
| `pre-briefing` | the dashboard and the map loaded |
| `briefing` | the briefing |
| `setup` | the setup, up to step S |
| `mission` | from step S to the mission's end |
| `between` | on to the next mission |
| `after` | the fade, the high scores, back round |

So the map answers when, not only whether: the window says which milestone's scripts need a routine, and the phase which part of that milestone ports it. Among the first mission milestone's scripts, the routine that draws a line runs in the landing alone, while the aircraft hangs on the arresting cable: it draws the cable. The flag that makes a mission a night mission is written by one routine, which runs only between two missions of a campaign, so the program's first campaign begins by day, unless a saved game is loaded.

That a routine runs is not enough, because it can run in every tick and still have a branch no flight takes. So the tool also records every stretch of instructions the processor executes between two branches. A [**cold region**](../glossary.md#cold-region) is a part of a ported routine that no run executed. Every cold region must be accounted for, by a stand-in's marker or by a note saying what it is: ported from reading, with the oracle test that holds it where one can; unreachable; data between instructions; or one of a few named cases. A region that is neither makes the tool fail.

The rule, as it stood at the end, has two halves. A routine no run enters is not carried: the C library and the system's glue, the crack's screen, the debugging aids, code nothing calls; chapter 4's statuses `replace` and `drop` say which the port does its own way and which it leaves out. A cold region of an entered routine is ported from the listing and held by an oracle test whose cases run it, where such a test can hold it, or was marked as a stand-in, owed to the milestone whose scripts would reach it. Hence the statuses: `partial` for a routine ported only as far as the scripts execute it, `ported` when the comparisons below hold it, [verified](../glossary.md#verified) when a test of its own holds it too. Over all the runs, the fifteen maps' setups and the key runs included, 440 of the 616 routines are entered.

## Stand-ins that fail loudly

Where the port lacks a region, it has a [**stand-in**](../glossary.md#stand-in): a marked place in the port's C where the original has code the port does not carry. It is one call of a macro, `WOF_STANDIN`, whose marker names the milestone that owes the code and what it stands for, an address of the executable or a place in the music player. In M4 every region its scripts did not run became one, each replaced in its turn. A stand-in is not a [stub](../glossary.md#stub): a stub answers, inside an instrument, for something a routine calls; a stand-in marks, inside the port, code the port lacks.

Reaching a stand-in counts in the game's state, which the port's diagnostics overlay, a panel of figures over the picture (chapter 23), shows. In a test build it is also logged by name, and every comparison fails on a stand-in reached, but for the open loop of a half-done milestone, which accepts a later milestone's stand-in in a step that differs. In the release build, which carries no test instrumentation, as a test makes sure, it does the least harmful thing: it skips what it stands for.

The loudness has a reason: a port that met code it lacks and carried on would differ from then on, and the difference would surface later and elsewhere, as a puzzle. A stand-in turns it into a failure where the script left the ported ground, with the place named.

Here is one left in the finished port, in the routine that starts a [sound sample](../glossary.md#sound-sample). It takes a channel number, and one value beyond [Paula](../glossary.md#paula)'s four channels, 6, would first hand Paula's channel 2 between the music and the sound effects. Look at the marker on line 19: the milestone that owed it, M8, the address it stands for, and above it the reason, read from the listing: no caller ever asks for channel 6. Past it, the routine skips the hand-over and plays on channel 2.

```c linenums="1"
--8<-- "generated/listings/c/channel_play.c"
```

Why keep a marker for what the game never does, rather than port it from reading or delete it? No run could check such a port, and a deletion would hide the gap; the marker keeps it visible, and loud if the game ever got there.

## From one mission to a campaign

The mission milestones:

| Milestone | Accepted when | Scripts | Cold regions its list left marked |
|---|---|---|---|
| M4, the world and the player | a mission flown and ended by a landing or a crash | 11, and 21 runs of the keys, 20 of them replayed in the loops | 55, for M5 to M7 |
| M5, the weapons and the ground targets | the same on the first three maps | 18 | 24, for M6 and M7 |
| M6, the enemy aircraft and the ships | the same on all fifteen maps | 25 | 3, for M7 |
| M7, the campaign | a full campaign playable | 6, and 8 runs of loaded games and demos | 3, M8's |

Each cold list named what the later milestones owed, so the next milestone's plan was not a guess but the list of stand-ins its scripts had to reach. The first three were done in two parts each, cut by chapter 7's phases: what the scripts run in a pass and a VBlank, then what they run in the tick, the first part held by the open loop below while the tick still had stand-ins. M7's parts were the campaign and the saved game, then the loader and the demo.

What stays marked at the end is not code owed but what the game never does: M8's seventeen markers and M5's one. Seven of the eighteen stand for values the game never produces, a full table of soldiers and six values the songs never hold; the rest for paths no caller takes, among them commands the game never gives its music player, and channel 6.

The scripts kept off the ground later milestones owned. The enemy aircraft were M6's, and the enemy's countdown, a timer that sends one up when the fire button has been left alone long enough, would have brought them. So every M5 script, like M4's flight until the fuel ran out, holds the button inside its turns, where it neither fires nor drops but resets the countdown.

Some states no flight of a script's length reaches: maps b and c follow only after winning a and b, which was M7's work. A script reaches them with a [**poke**](../glossary.md#poke): a value written into one address of the game's state at a fixed point of the run, on both sides, the original and the port, so that the comparison stays fair. A poke sets what the game itself would set: the mission number a won mission writes, poked at the end of the rank selection for maps b and c, or the night's flag. No state is made that play could not reach.

## Scripts flown by an autopilot

A script is a list of segments, each a number of VBlanks with the letters of the stick and the button held during them: `U` forward, `D` back, `L`, `R`, and `F` for fire. A take-off is a handful of segments written by hand. A landing is not: the aircraft must come in low over the bow at the right moment and the right speed, and that moment depends on everything before it.

So we flew the headless original with an [**autopilot**](../glossary.md#autopilot): a program that looks at the game's state every VBlank and chooses the stick and the button by a policy, a set of rules for one task. Compressed into segments, its choices are the script. The original is deterministic for a given [schedule](../glossary.md#schedule) (chapter 6), so the script flies the same flight again without the autopilot, in the original and in the port.

The landing came out of a few rounds of observation. The approach comes from the right with the aircraft facing left, as the manual teaches (page 6), on a glide path that loses 0.08 pixels of height for every pixel flown towards the bow. At the bow the stick goes forward alone, which lifts the nose, as the manual's landing stalls the aircraft onto the deck, and it stays forward after the touch-down, for a rule of the original: on the deck a flag is set whenever the aircraft is fast and the stick is not forward, and while it is set the tailhook never catches a cable.

Here is the script the autopilot left, from [`tools/m4_scripts.py`](repo:tools/m4%5Fscripts.py). `PILOT` is the start: the front end, bombs chosen in the hold, the lift and the roll to the right. Look at the short segments of four to twenty-four VBlanks in the middle: the approach, the policy correcting the glide path a little at a time; `U` alone after it is the stick forward at the bow and on the deck.

```python linenums="1"
--8<-- "generated/listings/py/LANDING.py"
```

The later autopilots added what their milestones needed. M5's drops a bomb where the game's own arithmetic, run ahead, says it will hit a target. M6's flies a dogfight, holding the button through the close chase, because the guns fire only after ten VBlanks held and a shorter press drops the other weapon. M7's flies on from a won mission into the next and presses the keys that save the game. Where even the autopilot could not get after real attempts, as with winning the third map or shooting an enemy down over land, a poke set the state instead.

## Two loops

The recorder runs a script in the headless original and keeps a [dump](../glossary.md#dump) of the game's state after every pass and every tick, the drawing calls, every value read from the [entropy stream](../glossary.md#entropy-stream) with the routine that asked, and the addresses each tick wrote. The port replays the recording VBlank by VBlank, the keys and the stick of each, calling its pass entry after each. The port begins a pass by its own rule, when the setting's VBlanks have gone by since the last, so it follows the VBlanks and the hands, and its passes fall where the original's do (chapter 7). The fades take no time on either side. Both loops are given, at the start, the seed of the entropy stream and the map list's addresses, where the original's allocator put the map's records at every map load: a defect of the original makes a wreck's explosion on land take its position from that address (chapter 20).

In the [**open loop**](../glossary.md#open-loop) the port is set to the original's state before every pass and every tick, so that each step is compared alone. From step S on, the original's state after each step is handed to the port: the game's variables and tables, which of the two screens is in front, how far the entropy stream has got, which way the shapes that the tick mirrors in place are facing, and the sound model's state. A difference then names its step: this pass or this tick, with nothing before it to blame.

In the [**closed loop**](../glossary.md#closed-loop) the port runs on its own from the program's start, the front end included, and is given nothing else; it is compared after every pass and every tick, so that every error it carries over shows. The names say where the port's own output goes: in the open loop it never reaches the next step, in the closed loop it always does.

![Three rows of steps: the original's records S, P, T, P, P, T, P; the open loop, the original's state handed down to each of the port's steps; the closed loop on its own from the program's start; every pass and tick compared; the seed and the map list's addresses given to both loops.](../figures/two-loops.svg)

/// caption
The two loops. S is the setup's end, P a pass and T a tick, in the order of a quiet scene at two VBlanks a pass. Both loops get the entropy seed and the map list's addresses; the open loop is handed the original's state after every step as well, the closed loop nothing else.
///

Each loop does what the other cannot. The open loop is the sharp one: it says where a difference arises, and it holds a half-done milestone, since every step starts afresh and a differing step can be judged alone: it must have reached a stand-in in that same step, or the fault is the port's. The closed loop is the honest one. The open loop replaces all of the port's registered state after every step; the closed loop replaces nothing, so all of it must come out right on its own, as in your browser. It caught the play screen left switched off after a dialog, the error chapter 4 told, where nearly a thousand passes differed. Over the four mission milestones, some 160 tests run the scripts through the loops.

## What is compared

After every pass both loops compare:

- every variable and table the port keeps, registered under its original address and read from the original's memory field by field (chapter 22);
- the drawing calls: which shape, where, with which arguments;
- the values read from the entropy stream, each with the routine that read it;
- which of the two screens is in front;
- the [palette](../glossary.md#palette) of every row of the picture;
- the objects of the map the pass draws, held against what a decoder of the map file, written apart from the port, says should be there;
- the sound samples started;
- the state of the sound model, Paula's registers and its timer.

After every tick they compare the same state, the tick's drawing calls and random reads, which way the mirrored shapes face, and the VBlanks the tick waited inside the restart. Here is the check after a pass, from [`tests/test_world.py`](repo:tests/test%5Fworld.py), which drives the replay of [`tests/m4compare.py`](repo:tests/m4compare.py). Look at the eight names under which a difference is filed, from `'state'` on line 7 to `'paula'` on line 30. For the drawing calls it files three from the first that differs, for the random reads the pass's first four.

```python linenums="1"
--8<-- "generated/listings/py/compare_passes.on_pass.py"
```

The setup is compared on its own, at step S: everything it wrote, the one tick `main` runs itself at the setup's end included, on every one of the fifteen maps and for the first mission of every rank.

Two things are not compared directly. The pixels: the headless original draws nothing. The drawing calls and the palette of every row stand for them, with a model of the [blitter](../glossary.md#blitter) through which the original's own drawing routine draws every shape, pixel for pixel against the port's. And the sound as you hear it: compared are the log of every sound sample started, with its channel, pitch and volume, and the sound model's state, not the waves the browser plays (chapter 18).

## The completeness list

A comparison compares what it is given: a variable the porter forgot to register would be compared nowhere, and its difference would never show. The [**completeness list**](../glossary.md#completeness-list) closes that gap: it sorts every address the original writes during a mission, in any phase, into a registered field, state compared in another form, or state not kept, with its reason and the milestone that owes it. An address that is none of the three fails the test.

Each row names the routines that write its range, and a write by any other routine makes the address uncovered again, because a new writer can mean a new meaning. The first milestone's test also fails on a row no run needs any more, so that its list cannot go stale. Here are the two rows of the second kind, from [`tests/m4complete.py`](repo:tests/m4complete.py). Look at the writers in braces and at each row's last field, how the port carries the state: the double buffer as the index of the screen in front, the colour tables as the palette of every row.

```python linenums="1"
--8<-- "generated/listings/py/COMPARED.py"
```

The rows of the third kind give their reasons. The graphics library's descriptions of screens and pens are not kept, because the port's screen model replaces them; nor the [copper](../glossary.md#copper)'s lists, whose effect is the palette of every row; nor the allocator's bookkeeping, nor the files as they are read. Each milestone has a completeness test of its own.

/// figures
| The completeness list | How many |
|---|---|
| Variables the port registers under their original addresses | 252 |
| Tables kept at fixed places | 30 |
| Allocated blocks of memory kept at fixed places | 21 |
| Rows of state compared in another form | 2 |
| Address ranges not kept, each with its reason and milestone | 35 |
| Kinds of memory block not kept, each with its reason and milestone | 10 |
///

## Breaking the port on purpose

A comparison that has never failed may be unable to fail: it may compare the wrong thing, or too little, and a test that has only ever passed looks no different from one that guards a correct port. So the milestones were closed with [**controls**](../glossary.md#control): deliberate changes of the port in one place, each run through the test that must catch it. A control passes when its test fails, and the place where the change showed is named, a step of a script or a case of a test: the test fails for the change itself. About sixty were run and reverted; M7's were built into a library of their own from a copy of the sources, so that the library the tests load was never touched and every control can be run again. A few:

| What was changed in the port | Script, or test | Where it first showed |
|---|---|---|
| a random read skipped in the pass's routine for a ground target's fire | `climb` | pass 424: one value fewer, named with its caller |
| forward and back swapped where the tick takes its byte | `turns` | the first tick with the stick forward |
| the restart's last wait for the next picture removed | `lost` | the restart's tick, one VBlank short |
| a row of the completeness list removed | the completeness test | the range and its writer named |
| a pointer of a loaded game kept as the file gave it | `load_disk` | the player's shape after the load |
| the demo's byte stored before the input sample, not after | `demo_record` | the first pass |
| a demo's playback ended one entry late | `demo_play_ff` | the tick where it should have ended |

Two controls run the other way: changes that must leave the comparison's result alone. Chapter 7 showed that the tick does not depend on how many VBlanks a pass takes, as long as the [couplings](../glossary.md#coupling) are reproduced, so the closed loop must hold at one and three VBlanks a pass as at two, against the original run at the same rate, and it does for scripts of every milestone. And the port with the [vertical flip](../glossary.md#vertical-flip) on, flying the turns script with forward and back exchanged, must fly the original's flight: every pass and tick agrees, but for the flip's own byte.

The controls also show what an instrument cannot see. A bomb's killing span made one pixel wider went through the scripts' comparisons unchanged, because no script puts a running soldier at the very edge of a span. The oracle caught it on random states, as chapter 5 told, and an oracle test of the tick places running soldiers at the edges of the guns' span on purpose.

## A check by another hand

One rule of the project completes the method: a claim, such as a porter's that a milestone's comparisons hold, is reviewed with one check of the reviewer's own that the porter's tests could not make. For a milestone of missions, one such check was the comparison run on scripts, maps and an entropy seed the porter never used, and, where stand-ins were left, every differing pass of the open loop attributed to a stand-in reached in that same pass. The porter chose the scripts, the maps and the seed; the check uses others.

/// dev
The reach map is [`tools/reach_observe.py`](repo:tools/reach%5Fobserve.py), with `--blocks --setups --json REACH.json` for block coverage and the fifteen setups, and `--cold` with such files for the cold regions. A stand-in is the macro `WOF_STANDIN` of [`src/wof.h`](repo:src/wof.h), counted in [`src/core.c`](repo:src/core.c) and logged in [`src/trace.c`](repo:src/trace.c). The recorder and the replay are `Recorder` and `Replay` in [`tests/m4compare.py`](repo:tests/m4compare.py); the loops of M5 to M7 are [`tests/test_weapons.py`](repo:tests/test%5Fweapons.py), [`tests/test_enemy.py`](repo:tests/test%5Fenemy.py), [`tests/test_campaign.py`](repo:tests/test%5Fcampaign.py), [`tests/test_loader.py`](repo:tests/test%5Floader.py) and [`tests/test_demo.py`](repo:tests/test%5Fdemo.py). [`tools/m4_autopilot.py`](repo:tools/m4%5Fautopilot.py) is run with a policy's name, the later autopilots up to [`tools/m7_autopilot.py`](repo:tools/m7%5Fautopilot.py) with a plan's; [`tools/m7_controls.py`](repo:tools/m7%5Fcontrols.py) points the tests at a control's library through `WOF_CORE_LIBRARY`.
///

## What comes next

The chapter in one sentence: the port carries what the scripts run, and two loops, a list and deliberate breakages hold it to the original, step by step. These instruments caught mistakes, the port's and their own. Chapter 9 tells them, each with what caught it: the stick's bits, the memory-form shift, the timeout, the shared core, the register carried as a long, and the last ticks nobody compared.

## Further reading

The files named here are in the repository, [`github.com/sy2002/wof-wasm`](repo:).

- [`re/notes/porting-m4.md`](repo:re/notes/porting-m4.md): ["What decides what is ported: the reach map"](repo:re/notes/porting-m4.md#what-decides-what-is-ported-the-reach-map), ["How the port is held to the original"](repo:re/notes/porting-m4.md#how-the-port-is-held-to-the-original), ["The completeness list"](repo:re/notes/porting-m4.md#the-completeness-list), ["What stands in, and where"](repo:re/notes/porting-m4.md#what-stands-in-and-where) and ["The scripts of part 2"](repo:re/notes/porting-m4.md#the-scripts-of-part-2).
- [`re/notes/porting-m7.md`](repo:re/notes/porting-m7.md#part-2-the-controls), "Part 2: the controls".
- [`SPEC.md`](repo:SPEC.md), sections 7.3, ["Determinism"](repo:SPEC.md#73-determinism); 7.4, ["Working method"](repo:SPEC.md#74-working-method); 8, ["Verification"](repo:SPEC.md#8-verification); 9, ["Milestones"](repo:SPEC.md#9-milestones).

Outside the repository: Wikipedia's ["Code coverage"](https://en.wikipedia.org/wiki/Code%5Fcoverage), the kind of measure the reach map is, and ["Mutation testing"](https://en.wikipedia.org/wiki/Mutation%5Ftesting), the method the controls follow by hand.
