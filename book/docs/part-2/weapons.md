Chapter 15
{ .chapter-kicker }

# Weapons, targets and soldiers

Chapter 14 flew the aircraft; this chapter is about what it fights with and against. By its end you will know where the game keeps a weapon while it flies, and why a shot can vanish; how a bomb, a rocket and the torpedo move and where they come down; what a hit does to an island's targets; how the soldiers come out, run and die, and why their deaths decide when an island is beaten; how the guns and the targets' fire work; and the small pools of smoke, splashes and balloons. The port and its instruments are gathered at the end.

## What the player fights with

Besides its guns, the Hellcat carries one kind of weapon at a time, chosen in the [hold](../glossary.md#hold)'s weapon menu before take-off: rockets, bombs or the torpedo (manual, pages 4 and 7). The game numbers them in the menu's order, 0, 1 and 2, the weapon's type; a reset in the hold sets bombs. A load comes from three bytes of the executable, 15 rockets, 30 bombs or one torpedo, as the manual counts them. The guns fire while the button is held, and a tap drops the other weapon (pages 6 and 7): chapter 7's two fire bits of the [input byte](../glossary.md#input-byte). The [dashboard](../glossary.md#dashboard)'s weapon counter shows the load on two drums.

## Fifteen records and a byte

A weapon in flight needs a place for its position and speeds; the game keeps it in an [**object record**](../glossary.md#object-record): one of fifteen records of 42 bytes in a fixed table, with a sixteenth after them for an enemy torpedo bomber's torpedo (chapter 16). There is no allocator and no list of free records. An object record's byte at `+0x20`, its kind, says whether it is in use: `0xFF` while it flies, 8 while it goes out, 0 when free. Its word at `+0x22`, its type, says which weapon it is.

Outside a turn, with the [attitude](../glossary.md#attitude) below 6 or above 16, a tap drops the weapon, and the drop looks for a free object record the only way the table allows: from the first, one by one. On the left, `tst.b` of `weapon_count` gives up when no weapon is left; `moveq #$e,d0` and `dbra` count fifteen rounds, `tst.b $20(a0)` tests a kind byte, and `beq.w` leaves for the launch at the first that is zero. The port's C on the right does the same with a `for`.

//// html | div.listing-pair

/// html | div
```wingslst
--8<-- "generated/listings/asm/object_draw_first.lst"
```
///

/// html | div
```c
--8<-- "generated/listings/c/object_draw_first.c"
```
///

////

With all fifteen in use the walk runs out and returns: the game silently drops the shot, and the listing shows the weapon taken off the count only in the launch, so the lost shot costs nothing either. The launch fills the object record from the aircraft: the type, its two speeds, its x and the height at which it is drawn. The same walk in `object_spawn` leaves the explosions of a crash (chapter 14). The tick moves the object records and the [pass](../glossary.md#pass) draws them; the pass frees one that has gone out by clearing its kind byte, which the tick reads: one of chapter 7's [couplings](../glossary.md#coupling).

## A weapon in flight

Once a tick, `objects_step` hands every object record whose kind byte is set to `object_step`, and what the record does is decided by a chain of tests, not by a table of routines or a switch: a kind byte of 8, going out, has nothing left to do; a type of 0 is a rocket; a type of 2 with a frame byte of `0x0A` is a torpedo running in the sea; everything else falls like a bomb.

A bomb loses a tenth of the whole part of its horizontal speed each tick, a division of whole numbers, so below ten pixels a tick it loses nothing more; gravity takes `0x6000`, three-eighths of a pixel, off its vertical speed each tick. The height moves by that speed's whole part, rounded down, and keeps no fraction, so the speed's fraction never carries. As it falls, a bomb tumbles: its frame steps on every other pass, round twelve frames.

![On the left, a bomb's curve from the aircraft to the ground, a dot a tick, and the aircraft flying on beyond it; on the right, a rocket fired level that drops a few pixels and races on level, and a rocket fired in a dive that follows the dive down.](../figures/weapons-flight.svg)

/// caption
A bomb dropped in level flight at 14 pixels a tick from a height of 150, and two rockets with a fall of 8 ticks, fired level and in a dive of 20 degrees: computed from the arithmetic of `object_step`, a dot a tick.
///

A rocket takes more at the launch: the [**bearing**](../glossary.md#bearing), the aircraft's pitch as an angle of the game's sine tables; a thrust of twice the bearing's sine and cosine; and a fall of 4, 8 or 12 ticks, two bits of a draw of the [beam](../glossary.md#beam). While the fall counts, the rocket keeps the aircraft's speeds and moves a pixel back and a pixel down each tick besides. When the count runs out it is aimed, and from then on the thrust is added to its speeds every tick. Fired level, it drops a few pixels and races on level, never coming down; only from a dive does it reach the ground, as the autopilot found. More than `0x500` pixels from the aircraft, its object record is freed. The aim turns a rocket pointing down towards the first enemy ship's gun or standing pillbox along its bearing; no script's rocket ever found one, so the [oracle](../glossary.md#oracle) alone holds the aim.

Here is the head of the chain and a rocket's own part. Look at `cmpi.b #$8,$20(a2)`, the kind, and `cmpi.w #$0,$22(a2)`, the type; then `subq.w #$1,$24(a2)`, the fall's count, with `sub.w d0,(a2)` and `subq.w #$1,$4(a2)`, a pixel back and down; `bsr.w $1099a`, the aim, when the count reaches zero; and the two `add.l`, the thrust.

```wingslst
--8<-- "generated/listings/asm/object_step_head.lst"
```

The torpedo falls like a bomb. If it meets the sea no faster than 5 pixels a tick, it runs in it: 4.3 pixels a tick the way it flew, for 200 ticks, not drawn but leaving a splash every tick, and it hits the first [map record](../glossary.md#map-record) under it that is not sea. Faster, it goes out where it fell. The manual asks for a low drop with the ship in sight (page 7).

![Tiny shapes with their names in three rows: twelve bomb frames; ten rocket frames from nose up to nose down and two of a torpedo; the ten rocket frames with a flame.](../generated/figures/weapons-torpedo.png)

/// caption
The weapons' frames of `Torpedo.shp`: a bomb's twelve; a rocket's ten by its bearing while it falls, and the torpedo's two; the rocket's ten once it fires.
///

## Where a weapon comes down

Over an airfield a rocket goes out and anything else bounces on the runway, the bounce of chapter 5; the first three maps have none. Elsewhere the ground is `0x0C`, 12 pixels above the [water line](../glossary.md#water-line), over the sea, the land and the targets alike, and a ship's deck over a ship. The listing does compare the map record's low bits with the slots of the dug-out and the barracks, 3 and 4, but on land the low bits are 2, the test never holds, and the targets' heights of chapter 13 play no part.

At the ground the object record keeps the low bits, which choose an explosion over land or a deck and a splash over the sea; makes the impact's sound (chapter 18); calls `weapon_hit`, two sections on; and goes out, eight frames, one a pass, before the pass frees it. The running soldiers within 16 pixels start dying.

## The targets

An island carries three kinds of target, shapes standing in the map's records. A [**dug-out**](../glossary.md#dug-out) holds soldiers and fires at the aircraft while it holds any; a [**barracks**](../glossary.md#barracks) holds soldiers and burns when hit; a [**pillbox**](../glossary.md#pillbox), the notes' name for the large gun the manual gives the rockets for (pages 7 and 10), fires, and only a rocket destroys it.

| Slot | Shape | The target | Hit |
|---|---|---|---|
| 3 | `dugo` | a dug-out, five soldiers inside | 200 points while it holds soldiers, who are let out |
| 4 | `huta` | a barracks, five soldiers inside | 150 points; it burns, slot 5, `hutb`, and its soldiers are let out |
| `0x0F` to `0x1E` | `pila` to `pilp` | a pillbox | by a rocket only: 200 points, destroyed |

A target is four map records wide, the third carrying the [draw flag](../glossary.md#draw-flag), and has an entry in a table the loader built (chapter 13): its place, its island, the soldiers inside and its counters.

![A dug-out, a barracks and a burnt barracks; below, sixteen pictures of a grey pillbox, from whole to marked in every quarter.](../generated/figures/targets-world.png)

/// caption
The targets of `world.shp`: the dug-out, the barracks and the burnt barracks a hit leaves; the pillbox's sixteen pictures, `pila` whole to `pilp`, by the quarters a rocket has hit.
///

Each island keeps two counts: its soldiers alive, five for every dug-out and barracks, and its pillboxes standing. An island whose two counts have both fallen to zero is a [**neutralised island**](../glossary.md#neutralised-island). The dug-outs and barracks themselves are counted nowhere, yet the two counts make the manual's rule hold, that an island falls only when every barracks, soldier and gun on it is gone (page 10). They do it through the soldiers, because a soldier inside counts until he is dead, a dug-out's soldiers come out only when it is hit, and a barracks gives a soldier to an empty dug-out only while it holds two or more, so that its last comes out only when it is hit too.

Neutralised, the island pays a bonus from a table by map and island and puts its message on the [ticker](../glossary.md#ticker); the map's last island, with no enemy ship left, ends the mission, chapter 17's subject. Map a's one island has two dug-outs and two barracks: twenty soldiers.

## What a hit does

`weapon_hit` is what an impact does to the map record under the object. On the left, `jsr map_slot_at` and the two `beq.w $14986` send low bits 0 and 1, the sea and a ship, to a branch of their own. On land a rocket, an object record of type 0, sets `flash_count` and `flash_colour`; slot `0x113`, the island's flag, is left alone; for slot 3 `target_of` finds the dug-out's entry, and `tst.b $8(a0)`, the soldiers inside, decides the rest: `#$c8`, 200, for the refill's timer and the score, and `target_release`. The C on the right begins after the branch to the sea.

//// html | div.listing-pair

/// html | div
```wingslst
--8<-- "generated/listings/asm/weapon_hit_land.lst"
```
///

/// html | div
```c
--8<-- "generated/listings/c/wof_weapon_hit_land.c"
```
///

////

A dug-out hit is not destroyed: its soldiers join those still to come out, and a timer starts. A barracks burns whatever it holds: its four map records become slot 5, each keeping its draw flag, as chapter 13 told, and the burnt barracks smokes. A rocket at a pillbox sets in the slot of all four records the bit of the record it hit, bit 3 for the first and bit 0 for the fourth: the slot becomes the pillbox's first slot plus a bit for each quarter hit, the figure's sixteen pictures. The first rocket destroys it, one pillbox fewer on its island; later rockets mark more quarters, and a bomb does nothing.

On land a rocket flashes the sky, chapter 11's [sky flash](../glossary.md#sky-flash), for five passes, white, or red when it hits a target. A bomb never does. Here are two rockets of a dive, down on a dug-out in the same tick:

![The play screen with a red sky: the aircraft low, flying west, just past two explosions beside a dug-out, palms to the right, dark smoke drifting up behind it; the dashboard shows 13 rockets and 200 points.](../generated/figures/rocket-flash.png)

/// caption
The rockets run, a replay of the script `rockets_a`, about 47 seconds into the mission: both rockets have hit the dug-out at world x 3,224, the sky is red, and the aircraft, 41 pixels up, has flown just past them; 13 rockets left and 200 points, which the run checks.
///

In the sea nothing happens. On a ship, chapter 16's subject, a bomb does nothing, a running torpedo takes one of the ship's hits, and a rocket destroys its first gun within 16 pixels, for 200 points. A crash on land hits as a rocket would, as chapter 14 told, and the running soldiers within 8 pixels of the wreck start dying. A bomb on each of map a's four targets scores 700.

## The soldiers

A [**soldier**](../glossary.md#soldier) is a record of eight bytes: his x, a direction, a frame, a timer, his island and his state, 0 free, 1 running, 2 dying, 3 dead. The loader sizes the soldiers' table at five for every dug-out and barracks.

A hit lets a target's soldiers out one at a time, by a timer the tick runs: the first after 60 ticks, each next one after up to 31, a number taken from the count of [VBlanks](../glossary.md#vblank) since the program's start. So the moment depends on everything before it, and three scripts set the count back at a fixed point.

He comes out at one end of his target and runs, in the pass, three pixels a pass, turning round at the water. Running into a dug-out he goes in, and a dug-out that was empty shows its gun again only 360 passes later. An empty dug-out sends every 200 passes for a soldier from the nearest barracks of its island that holds two or more, and he runs across: this refill is where chapter 9's [upper word](../glossary.md#upper-word) came from. Since the soldiers live in the pass, how long a pass takes sets how fast they run (chapter 7).

In the listing, `sub.w d1,d0` and `add.w d1,d1` turn the x and the half width into a span's start and width, so that one unsigned compare, `cmp.w` with `bhi.w`, tests both ends; `cmpi.w #$1,$6(a0)` takes only a running soldier, and a hit one gets state 2, frame 5 and a timer of 2, and screams.

//// html | div.listing-pair

/// html | div
```wingslst
--8<-- "generated/listings/asm/soldiers_hit.lst"
```
///

/// html | div
```c
--8<-- "generated/listings/c/wof_soldiers_hit.c"
```
///

////

The scream's sound routine returns with its own values in D0 and D1, which held the span, and the walk goes on with them: the listing shows that after the first soldier it hits, the span lies near the map's west end. So one impact sets one running soldier dying, unless others stand near world x 0. The port's sound routine hands the two values back.

Dying, a soldier's frame steps every third pass, and after the seventh he is dead: 25 points, scored in the pass, and one soldier fewer on his island. A dead soldier stays where he fell, drawn at full scale.

![A soldier's nine frames, running, falling, lying; below, a gun at seven angles, and the seven firing.](../generated/figures/soldier-guns.png)

/// caption
A soldier facing east, `guy0` to `guy8`: running, dying, dead; nine more face west. Below, a target's gun by the aircraft's distance and height, `gun0` to `gun6`, and firing, `gnf0` to `gnf6`.
///

The search for a free soldier's record has no end: it passes a soldier's record in use without counting, and would run past the table if all were in use. That cannot happen, because the soldiers inside, those still to come out and the soldiers' records in use, running, dying or dead, always add up to the table's size. The port marks the case as a [stand-in](../glossary.md#stand-in), and a test holds the balance in the original's state at more than 20,000 steps of the scripts.

## The guns, and the targets' fire

The guns are no object at all. While the button is held and the aircraft flies straight, the tick works out where the bullets reach the ground: the aircraft's height over the tangent of the bearing, ahead of it. They reach it only while the aircraft sinks below a height of `0xA0`, 160, which is why the autopilot fires them in a shallow descent. Each tick a splash or a puff of dust is made there, and the running soldiers within 16 pixels start dying. The rounds are a word set to `0x600` in the hold that nothing counts down: the guns never run out. The muzzle flash is drawn by chapter 12's exclusive-or blit.

The targets fire back. In each pass a dug-out with soldiers and a standing pillbox show one of seven frames of their gun, chosen from a table by the aircraft's height and distance, or the firing frame when a draw of the beam allows. The index can leave the table's 48 bytes, so the port reads it by its address, as chapter 14 told of the wheel table. Then the gun may hit the aircraft, on two draws of the beam: the first is held against the distance and the height, so that the nearer and lower the aircraft, the likelier the hit; the second lets about one value in five through. A hit on the aircraft puts smoke at the engine, and at the end of a hit count, a word of the [player's record](../glossary.md#players-record), the oil falls by one and the fuel by up to three: chapter 14's oil.

/// figures
| The targets' fire | |
|---|---|
| A gun shown | within 512 pixels, `0x200` |
| A gun that may hit | within 448 pixels, `0x1C0` |
| The first draw | below 512, at least the larger of distance and height and a quarter of the smaller |
| The second draw | below 2,048, at most 409, `0x199` |
| The hit count | 6 to 9 at a reset, then 6 to 13 |
///

## The pools

Beside the object records the game keeps four [**pools**](../glossary.md#pool), tables of small records allocated once at the start. Each of a pool's records has a byte or word that says it is in use, a claim walks the table for the first free one, and with all in use nothing happens. With no list of the records in use, the only way to find them is to look at each, so every walker steps through its whole table, every pass or every tick.

| Pool | Records | Each | Free again |
|---|---|---|---|
| Smoke | 40 | a puff from the engine, a burnt barracks, a destroyed pillbox or a wreck, drifting one to two pixels a pass east and up | when it has shrunk through six frames, one every seventh pass |
| Splashes | 20 | a splash of a bullet or a running torpedo in the sea, or a bullet's dust on land | after 6 passes, 4 on land |
| Balloons | 20 | a balloon rising from the carrier after a promotion | at a height of 170 |
| Ricochet | 20 | never filled | |

The counts are the allocations' sizes over the records' sizes. The balloons rise only while a flag is set that only the promotion after a rank's last mission sets, for the flight back to the carrier; every free balloon record goes up again over the carrier in a colour and with a drift from the beam. The Ricochet pool is dead: its one writer is a routine nothing calls, and the port keeps the allocation only for the layout.

## What the port made of it

The port keeps the same records, bytes and chains of tests, in [`src/objects.c`](repo:src/objects.c), [`src/targets.c`](repo:src/targets.c), [`src/pools.c`](repo:src/pools.c) and [`src/tick.c`](repo:src/tick.c), each routine with its `orig` comment and the original's widths. Where a register of these hand-written routines crosses a call, the C passes it as an argument and names it. So chapter 9's upper word goes from one walk of the targets to the next, and the scream's two registers come back from the sound routine. The address of the map's records, which a wreck's explosion takes for an x, is given to the port at every map load (chapter 20).

What the scripts reached was ported. What they did not reach was ported from reading the listing and is held by the oracle, region by region; what belonged to the enemy was a stand-in until its milestone. One marker is left, the full table of soldiers the balance rules out.

The eighteen [mission scripts](../glossary.md#mission-script) of the weapons fly every weapon on the first three maps, the targets' fire until the engine seizes, a crash, the island cleared of its soldiers, the balloons, and the keys while a bomb falls; maps b and c and the balloons are reached by a [poke](../glossary.md#poke). The [autopilot](../glossary.md#autopilot) of chapter 8 flew them by plans: a rocket from a dive, the guns in a shallow descent, and a bomb where its own copy of `object_step`'s arithmetic, run ahead, says the bomb comes down on a target. The prediction falls 14 pixels short, the tick or so between the tap and the drop, which the plans add.

```python
--8<-- "generated/listings/py/fall.py"
```

Every script runs in both loops of chapter 8, the [closed loop](../glossary.md#closed-loop) and the [open loop](../glossary.md#open-loop), every tick and pass compared, two also at one and three VBlanks a pass, and the [completeness list](../glossary.md#completeness-list) accounts for every address they write. Under the oracle, fifteen tests hold the routines over random settings of the registered state, the objects' step over 2,500 settings of sixteen random object records each; a later test draws the targets' upper word at random. The drop's test fills all fifteen object records in every fifth case:

```python
--8<-- "generated/listings/py/test_the_drop_matches_the_original.py"
```

No script of the weapons reached the promotion: an autopilot's eight sorties against map c killed 35 of its 70 soldiers. The campaign's scripts reach it with a poke (chapter 17).

/// dev
The routines: `weapon_drop` `0x01107C`, `object_step` `0x010AA6`, `weapon_hit` `0x0146DC`, `target_fire` `0x014F5C`, `soldier_out` `0x011E82`, `soldiers_draw` `0x013EEE`, `gun_splashes` `0x0119BC`. A torpedo that runs into something goes out undrawn, and its object record is freed only when the hold clears them all. The scripts: [`tools/m5_scripts.py`](repo:tools/m5%5Fscripts.py); the upper word's test: [`tests/test_oracle_m7.py`](repo:tests/test%5Foracle%5Fm7.py).
///

## What comes next

The chapter in one sentence: the weapons fly in fifteen records with a byte that says in use, moved by a chain of tests and brought down where the map's low bits say; a hit rewrites the map and lets soldiers out, and their deaths, with the pillboxes, neutralise an island. Chapter 16 takes up the enemy: the aircraft that come when the countdown runs out, the ships and their guns, the torpedo run, the airfields.

## Further reading

- [`re/notes/porting-m5.md`](repo:re/notes/porting-m5.md): ["The targets and the soldiers"](repo:re/notes/porting-m5.md#the-targets-and-the-soldiers), ["The pools"](repo:re/notes/porting-m5.md#the-pools), ["The tick: the drop"](repo:re/notes/porting-m5.md#the-tick-the-drop), ["The tick: a weapon in flight"](repo:re/notes/porting-m5.md#the-tick-a-weapon-in-flight), ["The tick: the hits"](repo:re/notes/porting-m5.md#the-tick-the-hits), ["The scripts"](repo:re/notes/porting-m5.md#the-scripts) and ["How the port is held to the original"](repo:re/notes/porting-m5.md#how-the-port-is-held-to-the-original).
- [`re/notes/objects.md`](repo:re/notes/objects.md): ["The inventory"](repo:re/notes/objects.md#the-inventory), ["Claiming and freeing a record"](repo:re/notes/objects.md#claiming-and-freeing-a-record) and ["What decides a record's behaviour"](repo:re/notes/objects.md#what-decides-a-records-behaviour).
- [`src/targets.c`](repo:src/targets.c), [`src/objects.c`](repo:src/objects.c) and [`src/pools.c`](repo:src/pools.c); [`tests/test_oracle_m5.py`](repo:tests/test%5Foracle%5Fm5.py), [`tests/test_weapons.py`](repo:tests/test%5Fweapons.py) and [`tools/m5_autopilot.py`](repo:tools/m5%5Fautopilot.py).
- [`original/manual.txt`](repo:original/manual.txt), the game's manual: page 4 for the weapon menu, pages 6 and 7 for the guns and the other weapons, page 10 for the islands' targets.

Outside the repository: Wikipedia's ["Object pool pattern"](https://en.wikipedia.org/wiki/Object%5Fpool%5Fpattern), the general form of the game's tables.
