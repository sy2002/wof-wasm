Chapter 20
{ .chapter-kicker }

# The original's quirks

The chapters before this one met the original's oddities one at a time; this chapter gathers them, together with what a real Amiga does that the port does not model and what the port changes on purpose. By its end you will tell a quirk of the original from a change made on purpose and from a mistake of the port, and know why a wreck's explosions land where they do, why the port carries a memory address of an Amiga it never runs on, how the game's directory is ordered and what of it is unconfirmed, where the manual and the code part, and why all of it is known rather than suspected.

## Keeping the accidents

A faithful port translates what the original's code does, its defects included (chapter 1). The rule reaches far, because the comparisons hold the port to the original's state after every [tick](../glossary.md#logic-tick) and every [pass](../glossary.md#pass) (chapter 8). An accident that leaves a value behind must leave the same value in the port, or the two part; a well-meant correction would show as a difference. So the port keeps the original's accidents as carefully as its intentions.

This chapter gathers four kinds of thing: the original's accidents, its unused code and values, the machine's behaviour the model does not reproduce, and the port's own changes. The first two are the original's [**quirks**](../glossary.md#quirk): places where its code does something odd, reading past a table, handing a routine the wrong thing, keeping code nothing runs, or disagreeing with its manual. A quirk is what the code does; where the [listing](../glossary.md#listing) shows how it came about, this chapter says so, and it claims no intention. A quirk is not a mistake of the port. The original's refill of a dug-out leaves a soldier's direction in a register's [upper word](../glossary.md#upper-word), which the next target's fire hands on: that is the original's, and kept. The port at first assumed that word was 0: a mistake, caught and put right (chapter 9).

Two get a section each, an accident and a piece of the machine's behaviour; the rest go into a table per kind, with the chapter that told each.

## An address for an x

This is an accident of the first kind, and it rests on the machine's memory addresses. When the player's aircraft crashes on land or on a deck, it slides to a stop before its wreck burns. The crash's explosions are made by `object_spawn`, which puts one into a free [object record](../glossary.md#object-record) (chapter 15). The crash calls it from four places, and three push its arguments as ten bytes: the address of the [map record](../glossary.md#map-record) under the wreck, the height above which to explode, and a flag. `object_spawn` takes the record's distance in bytes from the start of the list of map records and multiplies it by four: the record's world x, since a record of two bytes covers eight pixels (chapter 13). An enemy's wreck never comes through this routine (chapter 16).

One call a tick during the slide is different. On the left, look at the three pushes before the `jsr`: a long of zero, then the aircraft's height, `(a0)`, then its x, `$2(a0)`, eight bytes. The routine reads its first argument as a long, so it takes the x and the height side by side as the address, and finds zero for the height. On the right, the port makes the same call:

//// html | div.listing-pair

/// html | div
```wingslst
--8<-- "generated/listings/asm/crash_explosion.lst"
```
///

/// html | div
```c
--8<-- "generated/listings/c/wof_crash_explosion.c"
```
///

////

`object_spawn` subtracts the address where the system put the list of map records, the map list's address, multiplies by four and keeps the lower 16 bits, because it shifts and stores a word, the explosion's x. Those bits depend only on the lower halves of the two numbers, so the aircraft's x drops out: the explosion's x is four times the difference between the height and the lower half of the map list's address, wrapped modulo `0x10000`. On the ground the sliding wreck has a height of 2, and in the [headless original](../glossary.md#headless-original)'s first mission the list lies at `0x24F404`: 2 less `0xF404` wraps to 3,070, and four times that is 12,280.

![Two lanes of boxes: a map record's address less the map list's gives 3,232 beside the wreck; the aircraft's x and height less the same address give 12,280, past the end of map a.](../figures/explosion-x.svg)

/// caption
The record under the wreck gives 3,232, beside it; the call during the slide gives 12,280. Both are less the map list's address, the second with its upper half dropped.
///

Map a ends at x 7,640, so there those explosions fall past its east end. A run of the port that dives onto map a's island shows what the player sees during the slide: the explosions made at the record under the wreck. The stray ones take object records while they burn out, and nothing on map a shows them.

![The play screen: a wreck on map a's island beside a dug-out, an explosion and black smoke over it, palms to the right.](../generated/figures/wreck-explosions.png)

/// caption
A wreck sliding on map a's island, [VBlank](../glossary.md#vblank) 3,574 of the run. The explosions shown are those at the record under it; the run checks three more records at x 12,280, past the map's end.
///

The number 12,280 is the headless original's, not the machine's. Its allocator hands out each address once, so its addresses are the same from run to run (chapter 6), but the list lies elsewhere after a restart and at the next mission. On an Amiga the address is whatever the system's memory allocator returns, which depends on the machine's memory and on what was loaded before. So where a wreck's explosions land on a real Amiga depends on the machine; near the wreck only by chance.

The port's positions in the map are offsets and need no address (chapter 13). But the original keeps the list's address in a variable of its own, and this call makes the variable's value part of the game's arithmetic. So the port keeps the variable in its [registered state](../part-1/oracle.md#calling-a-routine-without-its-program), the original's variables under their original addresses, and fills it from outside at every map load, as it takes the [entropy stream](../glossary.md#entropy-stream). It is compared from the map's load on, so a [control](../glossary.md#control) that left it unfilled differed at the first step, long before any wreck. The tests fill it with the headless original's address at every load.

The page has no machine's allocator to follow. We chose for it the address of a game's first mission in the headless original, at every load: our choice, recorded in the specification, not one of the owner's decisions below, and open to the owner. So a page's first mission behaves as that run, and a wreck sliding at height 2 sends those explosions to 12,280 on every map and in every mission: past the end of map a and the short map j, somewhere on the others. The headless original's addresses after a restart and in a next mission would put them at 48,376 and 44,312, off every map.

## The order of the directory

This is the machine's behaviour, documented and partly unconfirmed. The [load and save dialog](../glossary.md#load-and-save-dialog) lists the saved games in the order dos.library's `ExNext` hands out the entries of the game's directory, the one the dialog lists, without sorting (chapter 19). A directory spreads its entries over 72 chains, lists chosen by a number worked out from each name, so that finding a file means reading one chain rather than every entry (chapter 3). `ExNext` walks the chains from 0 upward, and each chain from its head. Here is the port's hash; look at the start from the name's length, each letter in upper case added after a multiplication by 13, the 11 bits kept, and the modulo 72:

```c
--8<-- "generated/listings/c/name_hash.c"
```

So the order follows from the names alone, and it is not the alphabet. The game's directory shows it: fourteen entries, each of its three subdirectories counted as one, in thirteen chains, `songplay` and `newarmyfont` sharing chain 53. A test reads the disk image's directory blocks and holds the order and the hash against them:

```python
--8<-- "generated/listings/py/test_the_disk_image_gives_the_order_the_file_system_hands_out.py"
```

Every entry of all five directories on the disk lies in the chain the same hash gives. The dialog lists only names that begin `wof.`, and the disk brings one, the saved game `wof.mission 3`, in chain 64.

![A grid of 72 numbered cells, six to a row: fourteen entries in their chains, numbered in the walk's order, and in chain 64 a saved game above wof.mission 3.](../figures/directory-chains.svg)

/// caption
The game's directory in its chains, read row by row. `wof.flight 4` is an example name that hashes to chain 64, drawn at the head of its chain, where the documentation puts a new entry.
///

The disk image confirms the chain of every name. How a real [Kickstart](../glossary.md#kickstart) 1.3 walks the chains, and whether it puts a new entry at the head of its chain or at the tail, are documented, not confirmed (chapter 3): nobody checked them on a machine, the owner having decided that the port feels right as it is and needs no more measuring on the Amiga. The disk cannot settle head or tail. Across its five directories, thirteen chains hold two or three entries; in twelve the head carries the earlier date, which reads as new entries added at the tail, and in one the later, which reads as an addition at the head. But the date 0 is the earliest an Amiga file can carry, and most of the game's files carry it, as a copying program writes when it keeps no dates, so the entries that look oldest may have been written last.

Head or tail matters only when two saved games share a chain. A game saved as `wof.flight 4` falls in chain 64 beside `wof.mission 3`: at the head it is listed first, at the tail second. A reader with a Kickstart 1.3 machine could save one and see. The two games of the test `test_a_saved_game_can_be_loaded_again` lie in chains 34 and 64, so they come in chain order either way. The port computes the order from the names, a written file ahead of the disk's in its chain, as in the headless original, and the [shell](../glossary.md#shell) keeps the written files in the order they were written (chapter 19).

## Accidents that reach the game

The port keeps each of these, held by the [oracle](../glossary.md#oracle) or a run. The manual's disagreements with the code are accidents too; they have the next section.

| The quirk | What follows | Told in |
|---|---|---|
| The balloons of a [promotion](../glossary.md#promotion) are never cleared | those in use stand unseen through the next mission and fly on at the next promotion | 17 |
| The Japanese carrier draws a shape its container does not hold | the call draws nothing; the port makes it | 16 |
| The [wreck's word](../glossary.md#wrecks-word) is written past a list of forty | a forty-first lands on the first [enemy aircraft record](../glossary.md#enemy-aircraft-record)'s state | 16 |
| The guns test a record's [relation](../glossary.md#relation-to-the-player) to the player, not whether it is in use | a freed record left ahead of the player would be shot down; no run has shown it | 16 |
| The count of ships left is decremented as a byte, then tested with its overflow | with no island left, from a count of 128 the mission is won with 127 ships afloat | 16 |
| The carrier and an enemy ship are told apart by the flags a score's move leaves | a score of 0 takes the carrier's path | 16 |
| Tables are read past their end, and a text written past it: the wheels' table, the islands' lists, a gun's frame, a [rank](../glossary.md#rank) past 6, a score of more than seven digits | each by its original address | 14 to 17, and here |
| The map's second walk reads one record past the list | the port's table is longer than any map | 13 |
| Saving moves the map's end pointer two bytes | a mission's first save changes the running game | 17 |
| The [key buffer](../glossary.md#key-buffer)'s shift runs one place too far | a full buffer copies a value from behind each array | 19 |
| A shot finds all fifteen object records in use | it is lost, and costs no weapon | 15 |
| A [soldier](../glossary.md#soldier)'s scream leaves its numbers in two registers | one impact kills one soldier, unless others stand at the map's west end | 15 |
| A running torpedo goes out undrawn | its record stays in use until the [hold](../glossary.md#hold) clears them all | 15 |
| One unpacker writes a byte past the end of its buffer | the port stops at the declared size; nothing reads the byte | 12 |
| A sound is started three times over, each time stamped with the VBlank | it plays from the second VBlank after the tick | 18 |
| The music's table of periods is an NTSC machine's | on [PAL](../glossary.md#pal) every note comes out about a sixth of a semitone flat | 18 |
| The soldiers' waits count every VBlank since the start | the [front end](../glossary.md#front-end)'s 312 VBlanks of waiting on [songs' fades](../glossary.md#songs-fade) move them | 15, 18 |
| The program never asks which video standard it runs on | on a 60 Hz machine all but the music's timer and two short waits of the sound run a fifth faster; the port takes the standard as a setting | 7 |

The port's test of the ship count looks at the byte before the decrement, which decides what the `bgt` decides, so the quirk is kept (chapter 16). For a table read past its end the rule is to read by the original address. A byte that a registered variable covers comes from the variable, since the original finds there whatever the game last wrote; any other byte of the executable's data comes from the data, and a byte beyond it reads as 0. Writes go by address too, which is how the forty-first wreck's word reaches the aircraft records. Here is the reading side:

```c
--8<-- "generated/listings/c/data_byte.c"
```

## What the manual promises

Where the manual and this executable part, the port follows the code:

| The manual | The executable | Told in |
|---|---|---|
| Control-D shows the high scores (page 12) | no reader takes it; a test finds the final state, the files and the schedule as without it | 1, 17 |
| Control-C works only after Control-D (page 12) | it deletes the high-score file at once | 17 |
| its list of keys (page 12) | has three more: Control-S, the music; Control-B, into the crash reporter; Control-V, a version line | 1, 18, 19, and here |
| the torpedo run is for a ship whose guns are out of action (page 7) | a torpedo's hit counts with every gun still standing | 16 |
| a bonus for a whole mission (page 10) | is the last island's bonus or the last ship's score | 17 |

## Code nothing calls, values nothing reads

The [reach map](../glossary.md#reach-map) and the oracle found code no path of the game reaches and values nothing reads (chapter 8). A whole routine nothing calls is left out; code inside a routine the game runs is kept, in the original's order and arithmetic, as part of what a test runs and compares; a table or a [pool](../glossary.md#pool) is kept where it belongs to the layout the registered state mirrors. The exceptions are named: a path no caller takes is a marked [stand-in](../glossary.md#stand-in), a test that can never hold is left out with a comment, and the key handler's mouse half and a wait on an empty key buffer are dropped (chapter 19).

| What nothing reaches | The port | Told in |
|---|---|---|
| A developer's reset of the high scores, a wait for a key, a setter of the key mask | left out | 17, 19 |
| The C library's formats for floating-point numbers, a second random generator, a block copy by the [blitter](../glossary.md#blitter), a second copy of a whole picture | left out | here |
| Eight routines of the [sound effects engine](../glossary.md#sound-effects-engine) | left out; the one path to them is a stand-in | 8, 18 |
| The Ricochet pool, whose one writer nothing calls | kept, twenty records, for the layout | 15 |
| Values handed over and never read: a second word to the [fades](../glossary.md#fade), a fifth to the [line editor](../glossary.md#line-editor), the [rank selection](../glossary.md#rank-selection)'s answer, the [briefing](../glossary.md#briefing)'s answer after a game loaded in flight | ignored, as by the original | here |
| The right mouse button's byte, written and never read | dropped with the mouse half of the key handler | 19 |
| A line of the flight model that always takes 0 | kept | 14 |
| A floor of the enemy's speed, above which it always stays | kept | 16 |
| A test of the targets' slots that never holds | left out, a comment naming it | 15 |
| Two states of the enemy aircraft that nothing sets | kept | 16 |
| A second [music player](../glossary.md#music-player), loaded with the music switched off | a stand-in, forced by a test of the port | 18 |
| Three writes to a register of [Paula](../glossary.md#paula)'s that can only be read | kept, changing nothing, whatever they were for | 18 |
| A key mask a game started from the command line never sets | kept, its other path tested | 19 |

## What a real Amiga does differently

A few things a real Amiga does are not in the model the headless original and the port share; where they matter, something else is used in their place:

| On a real Amiga | The model and the port | Told in |
|---|---|---|
| A pass takes processor time the listing cannot give | two VBlanks a pass, filmed on the owner's PAL Amiga in a quiet scene; a busy scene not filmed | 7 |
| A fade's steps take processor time nobody measured | none in the headless original; two VBlanks a step in the port, by the owner's eye | 7 |
| The wait for a song's fade ends within a VBlank of its end | rounds of four VBlanks, up to three VBlanks late, which also moves the soldiers' count | 6, 18 |
| A PAL frame is about 0.16 percent longer than a fiftieth of a second | exactly a fiftieth | 18 |
| Paula raises a cycle's end request when it fetches the last word | raised once the word has played, four bytes later | 18 |
| Paula's filter and the analogue mixing | none | 18 |
| The [timer's latch](../glossary.md#timers-latch) holds at start whatever the chip's reset left | assumed to hold the documented reset value, on which the music's tempo rests; no film checked it | 1, 18 |
| The data holds the machine's addresses | the map list's, filled from outside; a saved game's [pointer fields](../glossary.md#pointer-field), derived; a demo's buffer, which the original frees between two missions of a demo and then reads at address 0, read as 0 | 17, and here |
| The blitter draws the cable, the game's one line | drawn from the blitter's documentation, its pixels not compared with a machine | here |

The specification listed thirteen points to establish, each due before the [milestone](../glossary.md#milestone) that needed it, and all are answered (chapter 10). Three rest on an estimate or on documentation rather than a measurement: the busy scene, the fade's step and the line mode. The other rows are the model's own limits.

## Changes made on purpose

A [**deliberate divergence**](../glossary.md#deliberate-divergence) is a change of the original's behaviour that the port makes on purpose, by a decision of the project's owner written in the specification. A quirk is the original's and kept, a divergence decided and written down, and a mistake of the port put right when an instrument catches it. There are seven:

| The change | Why | Told in |
|---|---|---|
| The [crack](../glossary.md#crack)'s screens and the copy protection left out; its pictures shown as the disk holds them | the screens are the crack's; the protection was disabled on this disk | 1 |
| A plain letter for each Control command, R and C only while paused, R in the briefing as well; the cheat sequence cannot be typed | a browser keeps Control with R, F and L | 1, 19 |
| The [keyboard assist](../glossary.md#keyboard-assist) | a key is tapped where a stick is held | 1, 19 |
| The [vertical flip](../glossary.md#vertical-flip) remembered, winning over a loaded game | the owner flies with it | 1 |
| A fade's step of two VBlanks, in the table above as well: an estimate that is also a decision | the original leaves it to the processor | 7 |
| A saved game's pointers derived; a file the port cannot hold refused | another machine's addresses mean nothing here | 17 |
| A [seed file](../glossary.md#seed-file) beside a recorded demo | so that it replays after a reload | 17 |

Three smaller departures, which the notes and the specification record, are no decisions of the owner: the freed demo buffer read as 0 and its write dropped, the unpacker's byte left unwritten, and the page's fixed map list address. Around the game the shell adds its own: the help screen, the pause sign, fullscreen, the stereo width, a reload where the dialog's Exit Game would end the program (chapter 23). Every comparison runs the [core](../glossary.md#core) as the original, the assist off and no preference given. One thing that looked like a quirk was none: the [memory-form shift](../glossary.md#memory-form-shift) that the emulator under the oracle once ran wrong was the instrument's fault, corrected there (chapter 5).

## What the catalogue says about the method

The original's quirks are known from the listing and the runs, not suspected; where the machine's behaviour is estimated, the table above says so. Every routine the scripts enter is ported, and every part of one that no run executes is accounted for: ported and run by the oracle's cases, marked as a stand-in, or explained in a note (chapter 8). The oracle's cases run the full key buffer, the music player's regions no run executes and the sinking's random states; the music's forced branch is a test of the port alone, which counts the stand-in. The [completeness list](../glossary.md#completeness-list) accounts for every address the original writes during a mission. And the port's departures in the game are seven decisions of the owner and three smaller ones, each written down.

/// dev
The addresses: `crash` `0x01AFBA` and its call at `0x01B304`; `object_spawn` `0x010820`; `map_list_address` `0x024628`; the wrecks' list `0x0251DA`, the aircraft records `0x02522A`; the wheels' table `0x025E3E`, read past its end at `0x025E50`. The port reads and writes the original's memory by address with `wof_original_load8`, `wof_original_store8` and `wof_original_store16` in [`src/core.c`](repo:src/core.c), the player's tables through `data_byte` in [`src/player.c`](repo:src/player.c). The page's address is `WOF_MAP_LIST_ADDRESS` in [`src/wof.h`](repo:src/wof.h). The tests: [`tests/test_front_port.py`](repo:tests/test%5Ffront%5Fport.py), [`tests/test_oracle_m3.py`](repo:tests/test%5Foracle%5Fm3.py), [`tests/test_oracle_m6.py`](repo:tests/test%5Foracle%5Fm6.py) and [`tests/test_music.py`](repo:tests/test%5Fmusic.py).
///

## What comes next

The chapter in one sentence: the port keeps what the original's code does, its accidents, its unused code and its quarrels with the manual included, models the machine where the game depends on it, and departs from the original in seven decisions, each written down. With it Part II, the game inside, is complete. Part III turns to the code itself: chapter 21 is a tour of the repository, chapter 22 tells the core and the registered state that lets the port keep the values this chapter has shown, and chapter 23 the shell and its additions.

## Further reading

- [`re/notes/porting-m5.md`](repo:re/notes/porting-m5.md#the-wrecks-explosion-and-the-map-lists-address-observed), "The wreck's explosion and the map list's address".
- [`re/notes/frontend.md`](repo:re/notes/frontend.md#the-order-of-the-file-list), "The order of the file list"; [`re/notes/porting-m3.md`](repo:re/notes/porting-m3.md): ["The order of the list"](repo:re/notes/porting-m3.md#the-order-of-the-list) and ["The off-by-one that is state"](repo:re/notes/porting-m3.md#the-off-by-one-that-is-state).
- [`re/notes/porting-m6.md`](repo:re/notes/porting-m6.md#flags-that-decide-in-the-tick), "Flags that decide in the tick"; [`re/notes/enemy.md`](repo:re/notes/enemy.md): ["Shot down, and what it scores"](repo:re/notes/enemy.md#shot-down-and-what-it-scores) and ["Open"](repo:re/notes/enemy.md#open).
- [`re/notes/music.md`](repo:re/notes/music.md): ["The game's calls"](repo:re/notes/music.md#the-games-calls) and ["The timer"](repo:re/notes/music.md#the-timer); [`re/notes/porting-m8.md`](repo:re/notes/porting-m8.md#what-the-model-leaves-out), "What the model leaves out"; [`re/notes/headless.md`](repo:re/notes/headless.md#the-fades-wait), "The fade's wait".
- [`re/notes/campaign.md`](repo:re/notes/campaign.md): ["A mission won"](repo:re/notes/campaign.md#a-mission-won), ["What the port writes in the raw part"](repo:re/notes/campaign.md#what-the-port-writes-in-the-raw-part) and ["The loader"](repo:re/notes/campaign.md#the-loader); [`re/notes/demo.md`](repo:re/notes/demo.md#the-port), "The port".
- [`SPEC.md`](repo:SPEC.md): ["Out of scope"](repo:SPEC.md#out-of-scope-for-this-specification), [7.3, "Determinism"](repo:SPEC.md#73-determinism) and [10, "Points to establish"](repo:SPEC.md#10-points-to-establish).
- [`src/core.c`](repo:src/core.c), [`src/fs.c`](repo:src/fs.c) and [`src/player.c`](repo:src/player.c).
- [`original/manual.txt`](repo:original/manual.txt), the game's manual: page 7 for the torpedo run, page 10 for the mission's bonus, page 12 for the keys.
