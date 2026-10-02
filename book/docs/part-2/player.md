Chapter 14
{ .chapter-kicker }

# The player

Chapter 13 laid out the strip of records the aircraft flies over; this chapter is about the aircraft. By its end you will know what the game keeps of the player; how one tick turns the stick into a motion, on the floating point of the Amiga's ROM; how the aircraft takes off from the carrier and lands on it, and why the landing needs the stick held forward; what the lift and the hold do; how the fuel and the oil run down; every way an aircraft is lost and how the next one comes; and what the fire button does besides firing. Each mechanism ends with what the port made of it and the instrument that holds it.

## What the game keeps of the player

Everything the tick does to the aircraft goes through one place, the [**player's record**](../glossary.md#players-record): thirty bytes at a fixed address that say where the aircraft is, how fast it moves and what it is doing. With a few variables beside it, the record is the whole of the player's state, and the loops of chapter 8 compare it after every tick.

| Field | What it holds |
|---|---|
| height | pixels above the [water line](../glossary.md#water-line), the sea's surface |
| x | the [world x](../glossary.md#world-coordinates), pixels from the map's west end |
| frame | the shape the aircraft is drawn with: a pointer to it and its name |
| state | what the tick does with the aircraft, the table below |
| fuel | `0xC0` when full |
| oil | `0x80` when full |
| facing | +1 flying east, −1 west |
| two speeds | horizontal and vertical, pixels a tick |
| the enemy's countdown | ticks, a later section's |

Two more words have no use that the notes name. In the air the x moves by the horizontal speed times the facing every tick, and the height by the vertical speed; on the deck the deck's own code moves the aircraft.

The state word picks what the tick does: one routine, the player's update, runs once a tick and branches on it.

| State | The aircraft |
|---|---|
| 0 | in the air |
| 1 | on the deck, or standing in the hold |
| 4 | coming down |
| 6 | in the sea |
| 7 | held by an arresting cable |
| 8 | burning, a wreck at rest |
| 11 | on the lift while it moves |

The other values never occur. Beside the record lie the variables of the flight. The [**airspeed**](../glossary.md#airspeed) is a number from 0 to 1,400 that scales both speeds. No control sets it directly: the stick pushed the way the aircraft faces raises it, and the manual names the stick's sideways positions as throttle settings (page 5). The [**pitch**](../glossary.md#pitch) is the aircraft's angle in hundredths of a degree, positive with the nose up, which moves towards a target the stick sets. The [**attitude**](../glossary.md#attitude) is the stage of a turn, 0 when the aircraft flies straight and 1 to 25 while it turns.

## The flight model

Once a tick, while the aircraft is in the air, the routine `player_motion` turns the pitch and the airspeed into a step. It moves the pitch a quarter of the way to its target, so that the nose swings over a few ticks when the stick moves the target; the division rounds towards zero, so the pitch stops a few hundredths short.

The sine and the cosine of the angle come from a table of 91 sines, one for each whole degree from 0 to 90; the cosine is the sine of 90 degrees less the angle. From them the routine splits the airspeed into a speed along the ground and a speed across it, each divided by 100. The horizontal speed is also multiplied by a factor for the attitude, which falls from 1 in straight flight to 0 at the middle of a turn, the stage where the facing changes; the result has 50 added before the division, so that it is rounded to the nearest whole pixel. In level flight at 1,400 the aircraft moves 14 pixels a tick: the airspeed counts hundredths of a pixel a tick.

![The aircraft pitched up by an angle; the airspeed along its nose split into a horizontal and a vertical speed; a height axis from the water line to the ceiling at 1,100 with a climb that bounces off it; an airspeed bar from 0 to 1,400 with the region below 1,000 marked.](../figures/flight-model.svg)

/// caption
One tick of the flight model: the two speeds from the pitch and the airspeed, the ceiling the aircraft bounces off, and the airspeed below which it sinks.
///

On the left, the horizontal speed: the attitude's factor times the airspeed made floating point (`ffp_flt`), times the cosine, plus 50 (`0xC8000046`, 50 in the format), divided by 100, and cut to a whole number (`ffp_fix`); then `muls.w` multiplies it by the facing and adds it to the x. The vertical speed follows the same way with the sine and without the factor. On the right, the port's C makes the same calls on the same 32-bit values.

//// html | div.listing-pair

/// html | div
```wingslst
--8<-- "generated/listings/asm/player_motion_speeds.lst"
```
///

/// html | div
```c
--8<-- "generated/listings/c/wof_player_motion_speeds.c"
```
///

////

Before the speeds, the routine takes the vertical part, cut to a whole number, out of the airspeed's step, the amount the airspeed moves in a tick. Every sine in the table short of 90 degrees is below 1, and the pitches observed in play run from about −45 to +30 degrees, so the whole number is 0 and the line changes nothing at any angle the game reaches.

Below an airspeed of 1,000 the aircraft sinks: the vertical speed loses another pixel a tick for every hundred the airspeed lacks, and the pitch's target drops by half a step a tick unless the stick is held forward. A player sees it after a slow take-off, the aircraft sagging towards the sea before it climbs. Here is that part in the model of the motion, which the tests drive with the ROM's floating point or the port's; `g_025414` is the airspeed, `g_026d43` the [input byte](../glossary.md#input-byte), whose bit 0 is the stick forward, and `ffp` the floating point handed in:

```python
--8<-- "generated/listings/py/model_01bdfa_slow.py"
```

Last, the height moves by the vertical speed. Above 1,100 it is held at 1,100, the vertical speed is halved and turned round and so is the pitch's target, so the aircraft bounces off a ceiling; below −4 it is held at −4.

All of it runs on the [fast floating point](../glossary.md#fast-floating-point) of the Kickstart ROM, up to twelve calls a tick on six of the library's nine operations. The port does the same arithmetic in integer code, the ROM's routines transliterated, because a browser's floating point rounds differently and the state would drift: the loops of chapter 8 compare the position and the speeds after every tick, and a last bit that differed would show at once. Chapter 5 told how the nine operations are held to the ROM. The motion itself is held under the [oracle](../glossary.md#oracle) over 3,000 random states, every attitude, both facings, the ceiling and the airspeed's floor among them, against the original running the ROM's own routines, and against the model driven by the port's floating point.

## The stick

The stick reaches the logic only through the input byte of chapter 7: four bits for the directions and two for the button, held and tapped. In the air, its routine reads them so:

| The stick | What it does in the air |
|---|---|
| left alone | a climb levels out, the airspeed falls to 1,000, a turn under way goes on or unwinds |
| towards the facing | the airspeed rises by its step, to 1,400 |
| against the facing | a turn |
| a direction with forward or back | the pitch's target up or down, at most 6 degrees a tick, between +30 and −45 |
| back alone | the target down two steps a tick, a steep dive |
| forward alone, flying west | the stall |

The airspeed's step itself grows by one a tick, up to 8, while the stick points the way the aircraft faces, and shrinks to 4 when it is left alone. While it turns with neither forward nor back, the pitch's target sinks by a quarter step a tick, which is why a turn loses height unless the stick pulls, as the manual warns (page 5). The manual's diagram of the stick puts the stall at its top (page 5).

A turn runs the attitude from 0 to 25, one stage every second tick. At 14 the facing changes, and after 25 the attitude is 0 again, the aircraft flying the other way. For each attitude a table gives the frame, one table for each facing, and the turn's frames are drawn as the container stores them; only the frames of straight flight, chosen by the pitch's target, and those on the deck are mirrored in place through the [mirror marker](../glossary.md#mirror-marker) of chapter 12. A turn begun facing west shows these frames:

![Twenty-one frames of the Hellcat in two rows, from hc28 to hc32 facing west, then hc33 to hc36 and hc27 to hc22 coming round to face east.](../generated/figures/turn-hellcat.png)

/// caption
The frames of a turn from facing west to facing east, in the order the attitude shows them, each drawn as `hellcat.shp` stores it.
///

The stick left alone lets a turn finish once it is past its sixth stage; earlier, the aircraft rolls back.

Since straight flight takes its frame from the pitch's target, not from the pitch, the frame shows where the nose is going. The [**landing stall**](../glossary.md#landing-stall) uses that. The stick forward alone, flying west, sets a flag and moves the target to 6 degrees up, so the aircraft is drawn nose up; but while the flag is set the motion eases the pitch towards 8 degrees down instead, and the aircraft drops. A player knows it as the stall the manual teaches for the landing (page 6): the nose raised, the stick forward alone, the aircraft sinking onto the deck. Flying east, the same stick lowers the target instead.

## On the deck and off it

On the deck another routine reads the stick. Pushed towards the facing it raises the airspeed by its step, as in the air; against the facing it takes 8 off the airspeed a tick and, once the aircraft stands, turns it round on the spot; left alone the airspeed falls by 8 a tick to 0. Each tick the aircraft rolls a hundredth of its airspeed along the deck, rounded.

The deck runs between two ends, the carrier's span sixteen pixels in from both sides, which in map a are world x 6,608 and 7,344. Past either end the aircraft is in the air, state 0, with the airspeed the roll gave it. Below 1,000 that is slow flight: in the landing run below, the aircraft left the deck at 708, sank from a height of 37 to 18 and only then climbed, the stick pushed east and forward, much as the manual tells the player to take off (page 5). Too slow to climb, it comes down in the sea.

## The landing

The approach comes from the east, the aircraft facing west, as the manual teaches (page 6). When the aircraft touches what lies under it, its wheels at or below the [ground height](../glossary.md#ground-height) of chapter 13, the routine of the ground decides. It counts the aircraft over the deck when its x lies between the deck's ends, its attitude is 0, its wheels are no more than 4 pixels below the deck and the carrier is afloat. Then it lands only facing west with the landing stall set; anything else over the deck bounces.

After the test of the deck, the listing tests the facing, `cmpi.w #$ffff,$14(a0)`, and the flag, `tst.w landing_stall`; a landing writes 1, the deck's state, into the record (`move.w #$1,$c(a0)`). The bounce turns the vertical speed and the pitch's target round with two `neg.w` and lifts the aircraft 6 pixels (`addq.w #$6,(a0)`). Both sound the screech.

//// html | div.listing-pair

/// html | div
```wingslst
--8<-- "generated/listings/asm/ground_contact_landing.lst"
```
///

/// html | div
```c
--8<-- "generated/listings/c/ground_landing.c"
```
///

////

Anywhere else, touching is a crash, state 4, which a later section follows.

On the deck the tailhook does the rest. An [**arresting cable**](../glossary.md#arresting-cable) is one of four wires across the deck; the hook catches one when it passes over it fast enough:

/// figures
| The cables | |
|---|---|
| The hook | 24 pixels behind the aircraft |
| The first cable | 70 pixels east of where the aircraft stands on the lift |
| The others | 56 pixels apart, four in all |
| Caught | within 8 pixels of a cable |
| At an airspeed of | 600 or more, with the deck's flag clear |
///

The deck's flag is the catch. While the aircraft rolls along the deck faster than 600, its routine sets a flag whenever the stick is not held forward; the aircraft is then drawn in its frame of straight flight instead of its deck frame, and the hook does not catch. So the stick must stay forward after the touch-down: that is what the [autopilot](../glossary.md#autopilot) of chapter 8 found, and here is why. In the listing, look at `tst.w g_025a9c` and the loop of four: the hook's x, the cable's x minus and plus 8 compared with it, then `addi.w #$38` to the next cable. A catch writes 7 into the record's state and keeps the cable's x for the drawing.

//// html | div.listing-pair

/// html | div
```wingslst
--8<-- "generated/listings/asm/cable_hook.lst"
```
///

/// html | div
```c
--8<-- "generated/listings/c/hook.c"
```
///

////

Held by the cable, the aircraft loses 110 of its airspeed a tick until it stands, and the state is 1 again. Meanwhile the pass draws the cable as a line, the only line the game draws.

![The aircraft on the carrier's deck, a red cable drawn from its hook to the deck behind it, the dashboard below.](../generated/figures/landing-cable.png)

/// caption
VBlank 1900 of the landing run: the cable at world x 7,270 holds the aircraft, its airspeed down to 1,148.
///

The figures of this section come from the landing that chapter 8's autopilot found: the [headless original](../glossary.md#headless-original) flew the script, its [schedule](../glossary.md#schedule) is kept with the book, and the book's build replays it through the port's [native library](../glossary.md#native-library), which meets the original's states at the same VBlanks. The aircraft touched down at an airspeed of 1,400, and four ticks later the hook caught the fourth cable, the first one an aircraft flying west meets.

![The landing run plotted: the height over the world x, the take-off from the deck and a dip, a climb to 145, a turn at the east end, a descending approach back to the deck, the cable, the stop and the column of the lift.](../generated/figures/landing-path.png)

/// caption
The landing run tick by tick, from the deck to the hold: the height over the world x, coloured by the record's state; the deck, the lift and the four cables marked, the caught one in gold. The height is drawn four times as tall as the x.
///

Then the aircraft taxis back to the lift.

## The lift and the hold

The [**lift**](../glossary.md#lift) carries the aircraft between the carrier's deck and the hold below it. The fire button on the lift, with the aircraft standing and the carrier afloat, takes it down, state 11; the lift sinks one step a pass, 32 steps, and the aircraft's height follows, since the ground under it is the deck less the lift (chapter 13). At the bottom the aircraft is reset: the tank filled, the oil restored, the weapons loaded and the weapon menu raised, which chapter 15 tells. While the menu is up the aircraft cannot move; the stick forward and back steps through the weapons, and the button closes the menu and sends the lift up, a step a pass. The manual's repairs, fuel and weapons are this one reset (page 6).

## Fuel and oil

The fuel starts at `0xC0` and falls by one every 28 ticks, only in the air; it never rises but in the hold. The oil starts at `0x80`, the engine's oil pressure of the manual (page 8), and stays there while nothing hits the aircraft. The fire of the islands' guns takes oil, and fuel, when it hits (chapter 15), and once the oil is below full it leaks one more every 80 ticks in the air; the enemy's fighters take it too (chapter 16).

In the air with the fuel below 0, or the oil below `0x60`, the update sets state 4 and the aircraft comes down. The [dashboard](../glossary.md#dashboard)'s two gauges show both (chapter 11). The oil's needle measures only what lies above `0x60`, so it reads empty when the engine stops; each gauge has a light that blinks in flight, the oil's below `0x74` and the fuel's at `0x40` or below: the red warning lights of the manual (pages 8 and 9). The script `fuel` flies until the tank is empty and the aircraft falls into the sea.

## Losing an aircraft

The crash's routine looks at what lies under the aircraft, and the attitude levels out two stages a tick while it comes down.

| Where, or why | What follows |
|---|---|
| the sea, after a crash or a take-off too slow | at rest in the water, state 6, sinking a pixel every third tick |
| out of fuel, or the oil too low | state 4, then the sea or the land below |
| land | the wreck burns at rest, state 8; the record under it is hit as by a rocket, and the soldiers within 8 pixels die (chapter 15) |
| a ship's deck | the wreck rests there; against the ship's side it slides back with the [sky flash](../glossary.md#sky-flash) |
| shot down | chapter 16 |

At rest, a wait counts the ticks: after 150, or after 30 with the fire button, the next aircraft comes. It costs a life; it stands on the lift in the hold, facing west, with the weapon menu up. With no life left, or the carrier sunk, the game is over, chapter 17's subject. Before the next aircraft appears, the tick itself clears the playfield, shows it and waits for the VBlank twenty-one times, so twenty-one VBlanks pass inside one tick, as chapter 7 told. On the left the clearing, `flip_buffers` and the two loops on `gfx_WaitTOF`, the first counting `g_027452` down from 20 and the second finding it 0; on the right each wait is a `CO_WAIT`, a point where the port's tick stops and goes on at the next VBlank, which chapter 22 tells.

//// html | div.listing-pair

/// html | div
```wingslst
--8<-- "generated/listings/asm/player_lost_restart_waits.lst"
```
///

/// html | div
```c
--8<-- "generated/listings/c/wof_player_lost_restart_waits.c"
```
///

////

The scripts `lost` and `gameover` roll the aircraft off the deck into the sea, once and until the lives are gone, and both loops compare every pass and tick of them, the VBlanks each tick waited included. Two keys stop a flight otherwise: Escape pauses it, and Control-R abandons the mission for the rank selection (chapter 19).

## What the button does besides firing

Tapped in the air, the fire button drops the chosen weapon; held, it fires the guns while the aircraft flies straight (chapter 15). It has one more use. The record's last field counts down to the enemy: set to 1,350 for each new aircraft, it loses one in every tick whose input byte has neither fire bit, and at 0 an enemy aircraft comes (chapter 16). A tick with a fire bit puts it back to 750 if it has fallen below. That is why the scripts of the first milestones held the button inside their turns, where a hold neither fires nor drops: the enemy aircraft were a later milestone's.

## What the port made of it

The port keeps the player's code as the original has it: [`src/player.c`](repo:src/player.c) holds the original's routines from `0x01AA6E` to `0x01CB74` in address order, each with its `orig` comment, every width of the listing kept, the [int](../glossary.md#int-the-c-type) of 16 bits included. The code indexes small constant tables by attitude, frame and pitch, and an index can run past a table's end into the variables behind it: the wheel table at attitude 9 reads a variable the deck's routine writes. The port reads such a table by its original address, from the registered variable where one covers the byte and from the executable's own bytes elsewhere; the oracle test of the deck found the case. The restart's waits are coroutines, and the floating point is the ROM's in integer code.

The oracle holds fifteen of the update's routines over 1,500 random states each, the whole registered state compared after every call, and a turn's step through every attitude over as many. This is their table in the test; the last field says whether the routine wants the aircraft in the air (0), on the deck (1), coming down (4) or anywhere:

```python
--8<-- "generated/listings/py/PLAYER_ROUTINES.py"
```

The [mission scripts](../glossary.md#mission-script) of the first mission milestone fly all of it in both loops of chapter 8, [open](../glossary.md#open-loop) and [closed](../glossary.md#closed-loop), every pass and tick compared: the aircraft left on the deck, a flight, a climb, a lost aircraft, the game over, the weapon menu, the turns, the landing and, in the long run of the suite, the fuel flight.

/// dev
The routines: `player_update` `0x01C660`, `player_motion` `0x01BDFA`, `flight_controls` `0x01BFF4`, `deck_controls` `0x01C4E8`, `deck_roll` `0x01BDBA`, `deck_edge` `0x01C5F4`, the turn's step `0x01AB80`, `frame_select` `0x01C378`, `aircraft_frame` `0x01ABDE`, `ground_contact` `0x01BA80`, `cable_hook` `0x01B92E`, `crash` `0x01AFBA`, `lost_wait` `0x01AF7C`, `next_aircraft` `0x0135CE`, `player_lost_restart` `0x0135D8`, `player_restart_state` `0x013684`; in the tick, the lift `0x011460` and the weapon menu `0x0112B0`.

The port's switch on the state is a chain of `if`s, because a coroutine's wait cannot sit inside a switch of its own ([`src/coro.h`](repo:src/coro.h)). The mirror markers belong to a saved state, so a state saved flying west comes back with its frames facing west. In the port: [`src/player.c`](repo:src/player.c), [`src/tick.c`](repo:src/tick.c), [`src/mission.c`](repo:src/mission.c), [`src/ffp.h`](repo:src/ffp.h); the tests in [`tests/test_oracle_m4.py`](repo:tests/test%5Foracle%5Fm4.py) and [`tests/test_world.py`](repo:tests/test%5Fworld.py).
///

## What comes next

The chapter in one sentence: the player is one record and a few variables, moved once a tick by the stick through a flight model on the ROM's floating point, landed by a rule and a cable, refuelled in the hold and brought back after every loss. Chapter 15 takes up what the button drops and fires, and the targets it hits.

## Further reading

- [`re/notes/objects.md`](repo:re/notes/objects.md#the-players-record), "The player's record".
- [`re/notes/ffp.md`](repo:re/notes/ffp.md): ["The format"](repo:re/notes/ffp.md#the-format), ["`player_motion` `0x01BDFA`, once per tick from `0x01C70E`"](repo:re/notes/ffp.md#player%5Fmotion-0x01bdfa-once-per-tick-from-0x01c70e), ["The call sites"](repo:re/notes/ffp.md#the-call-sites) and ["The two tables of constants"](repo:re/notes/ffp.md#the-two-tables-of-constants).
- [`re/notes/porting-m4.md`](repo:re/notes/porting-m4.md): ["The tick"](repo:re/notes/porting-m4.md#the-tick), ["The player's states"](repo:re/notes/porting-m4.md#the-players-states), ["Landing, refuelling, rearming"](repo:re/notes/porting-m4.md#landing-refuelling-rearming), ["Every way an aircraft is lost"](repo:re/notes/porting-m4.md#every-way-an-aircraft-is-lost) and ["The scripts of part 2"](repo:re/notes/porting-m4.md#the-scripts-of-part-2).
- [`SPEC.md`](repo:SPEC.md), sections 3.4, ["Operating system and hardware use"](repo:SPEC.md#34-operating-system-and-hardware-use), the row of mathffp; 6.3, ["Blocking code becomes coroutines"](repo:SPEC.md#63-blocking-code-becomes-coroutines).
- [`src/player.c`](repo:src/player.c), its comments; [`tests/ffp_model.py`](repo:tests/ffp%5Fmodel.py), [`tests/test_oracle_m4.py`](repo:tests/test%5Foracle%5Fm4.py) and [`tools/m4_scripts.py`](repo:tools/m4%5Fscripts.py).

Outside the repository: Wikipedia's ["Arresting gear"](https://en.wikipedia.org/wiki/Arresting%5Fgear), the real thing the cables imitate.
