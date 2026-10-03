Chapter 17
{ .chapter-kicker }

# The campaign

Chapters 13 to 16 took one mission apart. This chapter is about what holds the missions together and what outlives a mission, a game and a page reload. By its end you will know in which order the maps come and why the game never ends; what a won mission and a promotion change; how the high scores are kept; what a saved game holds and how the port reads one written on a real Amiga; and how the game records and replays its own demo. The port and its instruments are gathered at the end.

## Seven ranks, fifteen maps

The manual offers seven naval ranks, each harder than the last (page 4). A [**campaign**](../glossary.md#campaign) is the run of missions from the rank chosen to the game's end, through the fifteen maps in the order of their letters. The [**rank**](../glossary.md#rank) is the campaign's stage, 0 to 6: the player chooses the first, and a promotion moves it on. The [**mission number**](../glossary.md#mission-number) counts the missions within a rank from 1.

| Rank | Missions | Maps |
|---|---|---|
| 0 | 3 | a, b, c |
| 1 | 3 | d, e, f |
| 2 | 2 | g, h |
| 3 | 2 | i, j |
| 4 | 1 | k |
| 5 | 1 | l |
| 6 | 3 | m, n, o |

The rank selection lists the seven ranks and, below them, an item that loads a saved game; choosing a rank sets the mission number to 1. `map_load`, chapter 13's loader, needs the map's file name: it adds up the missions of the ranks below and the mission number less one, an index into the fifteen names. The other readers, the night's choice and the island's bonus among them, take the map from a second table by rank and mission, without a sum.

![Boxes and arrows from the rank selection through a mission, its win, the next mission and a promotion to the game over and the high scores.](../figures/campaign-course.svg)

/// caption
A won mission leads to the next mission, or first to a promotion; the last Hellcat or the carrier lost, to the game over and the high scores. A saved game enters at a mission; the attract demo returns without the high scores.
///

## A mission won

The pass calls `mission_won` when the last island is [neutralised](../glossary.md#neutralised-island) (chapter 15), the tick when the last enemy ship has sunk with no island left (chapter 16). It counts the mission number on and compares it with the rank's count of missions, read by address, as the port reads it, so a rank past 6 would read beyond the table. Within the count, the ticker gets the next mission's message. Beyond it comes the [**promotion**](../glossary.md#promotion), the step from a rank's last mission to the next rank's first: the mission number back to 1, the rank one up but never past 6, the flag `balloons_on` set, and a message of its own.

The message is appended to what the [ticker](../glossary.md#ticker), chapter 11's message line, holds, which is always the island's bonus or the sunk ship's name. On the left, `tst.b (a2)+` walks to the end of that text and leaves the pointer one past its NUL, the zero byte that ends a text; `subq.w #2` steps back over the NUL and the character before it, so the new message begins on the old one's last character. Both branches then point the ticker at the text and set the [**won flag**](../glossary.md#won-flag), a word only this routine sets, which says that the mission is won.

//// html | div.listing-pair

/// html | div
```wingslst
--8<-- "generated/listings/asm/mission_won.lst"
```
///

/// html | div
```c
--8<-- "generated/listings/c/wof_mission_won.c"
```
///

////

Nothing here touches the score: the manual's bonus for a whole mission (page 10) is the last island's bonus, paid just before the call.

## The next mission

The won flag waits for the next aircraft. `main` tests it at the head of its inner loop together with the weapon menu, which is up only in the [hold](../glossary.md#hold): so the next mission begins when the next aircraft stands in the hold, whether the one that won landed or was lost on the way back.

The steps come in a fixed order: the flags cleared, the sound slots emptied, the ticker stopped, both views faded out, the mission's assets freed. If `balloons_on` is set, the lives get one more, the `addq.b` on the left. Then the night is chosen, the new map loaded and its briefing shown, where Control-R goes back to the rank selection. Only now are the dashboard's pictures loaded, because only now is it decided whether they are the day's or the night's. The display's setup, the ships' shapes, the lists and the sounds follow, and `bra.w` jumps into the first mission's reset, which ends at step S, chapter 8's moment where a mission's loop begins. On the right, the port's coroutine with its `goto`.

//// html | div.listing-pair

/// html | div
```wingslst
--8<-- "generated/listings/asm/main_next_mission.lst"
```
///

/// html | div
```c
--8<-- "generated/listings/c/main_next_mission_c.c"
```
///

////

There is no rank selection and no campaign reset: the score, the kills, the [enemy plane counter](../glossary.md#enemy-plane-counter) and the lives carry over. [Chapter 11](display.md) told how `choose_night` makes the night here and that nothing clears the flag between campaigns: the script `night_again` loses a game at night, and the next campaign begins at night in both loops.

The briefing shows the rank's name, the mission number and the manual's objectives (page 10), two counts from the map's first walk (chapter 13): the islands that hold a target, so only two of map l's three, and the enemy ships, a count that goes down as they sink.

| Map | a | b | c | d | e | f | g | h | i | j | k | l | m | n | o |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| islands | 1 | 2 | 3 | 2 | 3 | 2 | 3 | 3 | 3 | 0 | 3 | 2 | 4 | 3 | 3 |
| ships | 0 | 0 | 0 | 0 | 0 | 1 | 1 | 1 | 2 | 2 | 1 | 2 | 2 | 2 | 3 |

Three Hellcats begin a campaign (page 10); each aircraft lost costs one (chapter 14), each promotion adds one, and the dashboard's drum shows at most nine.

## The promotion, and no end

From the next pass the promotion's flag lets the free records of the Balloons [pool](../glossary.md#pool) rise over the carrier (chapter 15), all twenty within two ticks of the win in the script `promote_a`. And it is still set at the next mission, which gives the Hellcat the manual promises (pages 8 and 10) before the reset clears it. The balloons themselves are never cleared: with the flag off, the records in use are neither drawn nor moved, so nineteen of the twenty stand unseen through the whole next mission and fly on at the next promotion.

After map o, the last rank's last mission, the promotion runs once more: the rank stays 6 and the mission number becomes 1, so the next map is m. The campaign goes round m, n and o for ever, each round with a promotion's message, balloons and a Hellcat more. The executable has no end sequence: a game ends only when the last Hellcat is lost or the player quits.

The [**game over**](../glossary.md#game-over) comes when the last Hellcat is lost, after chapter 14's wait, or after the carrier has sunk, chapter 16's count. `main` fades out and, unless a demo was played, shows the high scores; then the rank selection begins a new campaign.

## The high scores

The [**high-score file**](../glossary.md#high-score-file), `highscore`, chapter 3's, is 360 bytes: ten rows of 36, best first. A row holds a score, the rank reached and a name of 30 bytes, of which at most 16 are ever typed. The high-score screen reads the file and sorts it, a bubble sort that swaps whole rows until a pass swaps nothing. Only a score greater than the tenth's gets the name entry; the new row replaces the tenth, the lowest after the sort, and the table is sorted again and written. Nothing else writes the file, so it is written at most once a game.

A missing file reads as ten empty rows: score 0, rank 0 and a name of twelve spaces. The disk's own file holds exactly that in its last three rows, so it had been played into seven times before it shipped. Control-C in flight deletes the file without a question. The manual lets it work only after Control-D has shown the list (page 12), but this executable has no Control-D. A developer's reset that writes ten rows of 5,000 points is there too, and nothing calls it. The port keeps the file in the browser's storage (chapter 23).

## The saved game

Control-G saves only while the aircraft is on the carrier (page 11); the dialog puts `wof.` in front of the name typed. Chapter 3 described the result.

Writing and reading share one [**walker**](../glossary.md#walker), a routine that hands a callback the file's pieces in a fixed order, each as the file, an address, a length and a mode: mode 0 means the memory at the address, mode 1 the block whose address is stored there. Since the write and the read run the same walk, the read finds every piece where the write put it.

| # | Piece | Mode | Length |
|---|---|---|---|
| 1 | the raw part, memory from `0x024CAE` | 0 | `0x84A` bytes |
| 2 | the map's length | 0 | 2 bytes |
| 3 | the map's records | 1 | the map's length |
| 4 | a gun list for each enemy ship | 1 | 14 bytes a gun |
| 5 | the pillboxes | 1 | 14 bytes a record |
| 6 | the soldiers | 1 | 8 bytes a record |
| 7 | the dug-outs | 1 | 16 bytes a record |
| 8 | the barracks | 1 | 16 bytes a record |

The lengths come as the compiled C computes them: a target count is a byte, which `ext.w` widens with its sign and `mulu.w` multiplies as an unsigned word, and only the product's low word is kept. On the left, a call of a routine that does nothing, then the pillboxes and the soldiers; on the right, the port's walker.

//// html | div.listing-pair

/// html | div
```wingslst
--8<-- "generated/listings/asm/save_walk_tables.lst"
```
///

/// html | div
```c
--8<-- "generated/listings/c/save_walk.c"
```
///

////

A gun list goes in for each ship whose record holds a score; the player's carrier scores 0 (chapter 16), so it is never in the file. The [**raw part**](../glossary.md#raw-part), the first piece, 2,122 bytes of memory as they stand from the object records on, holds every count the later pieces need: a file describes its own layout, and [`tools/savegame.py`](repo:tools/savegame.py) decodes one by that alone. The walker also writes: after the map it sets the map's end pointer two bytes past where the loader left it, so every save moves that pointer of the running game.

/// figures
| The figures | |
|---|---|
| The raw part and the map's length | 2,124 bytes |
| The smallest save, map a | 4,258 bytes |
| The disk's saved game, map c | 6,866 bytes |
| The largest save, map m | 11,516 bytes |
///

A save's size follows from its map alone. The disk's `wof.mission 3` was saved on a real Amiga in map c, the first rank's third mission, with 14,225 points, two Hellcats and two of the three islands left.

![Two columns of bars: the saved game's pieces to scale, and its first piece enlarged with labelled regions and gold marks.](../generated/figures/savegame-disk.png)

/// caption
The disk's saved game to scale, its pieces in the walker's order, and the raw part enlarged: its regions named by the port's registered fields, the bytes of no field dark, and in gold the fields that hold addresses.
///

The raw part holds the object records, the player's record, the ships, the enemy aircraft and airfields, the score, the lives, the flags, the rank and mission number, the islands, the ship records and the two options. 75 of its bytes belong to no variable the port keeps; nothing writes them, and in the disk's file all are 0. Outside it, and so in no file, lie the sixteenth [object record](../glossary.md#object-record), where an enemy torpedo runs, the pools, the sound slots and the ticker's text.

Four kinds of field in the raw part hold addresses in the machine that saved: the player's shape, a shape the tick keeps for level flight, the torpedo's shape, and each ship's gun list. These are the [**pointer fields**](../glossary.md#pointer-field); in the disk's file the player's shape reads `0x0005FB4A`. On another machine such an address means nothing.

## Loading a game

The reader walks the file with a callback of its own: a mode-0 piece goes back where it lies; for a mode-1 piece it allocates a new block, reads into it and stores the block's address, only when the read delivered the whole length. The lengths come from the counts the raw part has just brought. A file that cannot be opened ends the game.

Two paths lead there. From the rank selection, the load item opens the dialog; the map is freed, the file read, the briefing shown, and `main` runs the mission's setup without its reset, so the file's state becomes the mission's. In flight, Control-L does the same unless a demo runs: it frees the dashboard's shapes, the sounds and the demo's buffer, loads, shows the briefing and runs one tick, and the inner loop goes on in the mission it was in.

The pointer fields come back as the saving machine left them. The player's and the torpedo's shapes do no harm, since the next tick sets both from the frame's name, which the file holds, before anything reads them; the gun lists are replaced by the new blocks. The one that matters is the shape the tick keeps at `0x02541A` for level flight: the player's drawing reads it in the hold before any level tick sets it again.

The port derives all four. In its own files that field holds a shape handle of at most four hex digits, from a real Amiga an address far larger. For an address the port uses the player's pointer beside it, whose shape the frame name gives. A record lies 6 plus 8 times the shape count plus its offset bytes after its container's start (chapter 12), so the player's pointer places the container in that machine's memory, and the other pointer's distance from there names its record: for the disk's file, the very shape the original's own saves hold there. A pointer that names no record draws nothing until a level tick sets the field. In the C, the last loop compares each record's place with the pointer:

```c
--8<-- "generated/listings/c/saved_hellcat_shape.c"
```

The file also brings back the [vertical flip](../glossary.md#vertical-flip), and the player's remembered preference wins (chapter 1). The port refuses a file it cannot hold before the load begins: one missing, shorter than its own counts ask, or with counts beyond the port's tables. The original exits on the first and reads the others into blocks of any size; the port keeps each block at a fixed place of a fixed size, so its dialog leaves as a cancel and the game goes on.

## The demo

The manual promises a self-running demo after loading (pages 2 and 3), chapter 3's [attract demo](../glossary.md#attract-demo), which this disk does not carry. `main` looks at its argument count once: started with an argument, the program records every game from the rank chosen on. The rank selection then allocates a buffer of `0x1388` bytes, 5,000, seeds the random generator from the [beam](../glossary.md#beam), the only place the program seeds it, and stores the rank in entry 0, the buffer's first byte.

From step S the [VBlank server](../glossary.md#vblank-server) stores each [input byte](../glossary.md#input-byte) it samples at the next entry while the pass still owes it one. `run_queued_ticks`, whose first lines chapter 7 left to this chapter, waits VBlank by VBlank until two bytes are in. So a demo's pass always has two ticks, whatever the pass costs, and a recording and its playback run the same ticks. The entries go in pairs, 1 and 2, then 3 and 4, so entry `0x1386` is always the second of its pass. The byte stored at entry `0x1385` brings the index to `0x1386`, which ends the game; the pass's second sample still takes that entry. At the game's end `demo_end` writes `0xFF` after the last entry and saves the whole buffer as `wofdemo`.

![A hexadecimal dump: the rank in gold, input bytes, an orange FF, then zeros, with a key to the values.](../generated/figures/demo-file.png)

/// caption
The port's recording kept for its replay test: the rank, input bytes such as `04`, right, and `05`, right and forward, one `24` for a tap, the end after 260 of them, and zeros.
///

Left alone for 1,800 rounds of its menu, a round being one VBlank, the rank selection asks for the demo. It loads `wofdemo`, and would read a shorter file past its end; without the file it starts a mission. It seeds the generator from the beam, takes the rank from entry 0, and from step S the server takes the demo's bytes in place of the stick, two a pass and no others. The `0xFF` ends the playback, and so does the count, as in a recording; on the left, the byte taken only while the pass owes one, and beside it the port's.

//// html | div.listing-pair

/// html | div
```wingslst
--8<-- "generated/listings/asm/vblank_server_playback.lst"
```
///

/// html | div
```c
--8<-- "generated/listings/c/wof_vblank_playback.c"
```
///

////

Fire ends a playback too; after a playback a flag skips the high scores, and a pause takes no byte.

On the machine a playback replays its recording only as far as nothing random differs: the seed is the beam's at the playback's own start, and two values the game reads run on from mission to mission and are not in the file, the swell's phase, which moves the carrier and its lift, and the night flag.

The port asks more: a recorded demo must replay identically after a page reload. So beside the demo it writes a [**seed file**](../glossary.md#seed-file), `wofdemo.seed`, 12 bytes: the [entropy stream](../glossary.md#entropy-stream)'s state where the recording began, a hash of the demo's bytes, the swell's phase and the night flag. A playback whose demo matches the hash starts from all three and replays the recording exactly; the hash keeps a seed off any other demo. A `wofdemo` without it, one from a real Amiga, plays with everything as it stands. Neither name begins with `wof.`, so the dialog never lists them; the port records with a development key (chapter 23).

/// figures
| The times, on PAL, derived | |
|---|---|
| The rank selection left alone, 1,800 VBlanks | 36 seconds |
| The longest demo, 4,998 input bytes, one a tick | about 400 seconds |
///

## What the port made of it

The next mission runs in the mission's coroutine, in the original's order, with a `goto` into the reset (chapter 22). `choose_night` reads its table by address with the original's signed index, where the port once took it modulo the table's length.

The write callback takes every byte of the original's memory from the port's registered state by its address, from the block behind a pointer for a mode-1 piece, and from the executable's image where nothing writes, as the original's memory holds it. A pointer field gets a shape handle, or 1 for a block. The file goes to the file system in one piece, of at most 12,412 bytes, the largest save the port's tables allow.

A cancelled load goes back into the rank selection's menu, as in the original. Two [stand-ins](../glossary.md#stand-in) for values fell. The score is formatted as the system's formatter, RawDoFmt, does with `%07ld`, the sign inside the zeros, so a negative score, which only a loaded game can bring, reads `000-123`. The ticker's message stays in the registered state, at most 220 of its 300 bytes. The demo's buffer is a registered pool, so every byte recorded or played is compared. And the chain of missions found a fault: after a save the port's model of the play screen stayed switched off, and 997 passes drew the rows below the split and the ticker without their colours.

## How it is held

Six [mission scripts](../glossary.md#mission-script) of the campaign run in the [closed loop](../glossary.md#closed-loop) from the program's start, every tick and pass compared through the win and the next mission's first ticks, and through a save; three run only in the suite's long run. A [poke](../glossary.md#poke) of the mission number and the rank reaches the promotion and the cap.

One script makes the chain with pokes: with each enemy ship's hits and the islands left set to 0 at every mission's reset, the ships sink while the aircraft waits in the hold, eight missions and seven wins. No map of a rank with one mission can be won by the [autopilot](../glossary.md#autopilot), and two wins in a row by play were not reached: two attempts at map b lost their last Hellcat to the [dug-outs](../glossary.md#dug-out)' fire in the low hunts and to the soldiers the bombs let out. No weapon can be in flight at a save: the landing takes longer than any weapon flies. The chain and the save also hold at one and three VBlanks a pass, the [open loop](../glossary.md#open-loop) finds no step that differs, and the [completeness list](../glossary.md#completeness-list) accounts for every address the scripts write. The save script at one VBlank a pass found another of chapter 9's [upper words](../glossary.md#upper-word).

The saved file is compared byte for byte with the one the headless original wrote; every differing byte is named by its field, and only the pointer fields may differ:

```python
--8<-- "generated/listings/py/test_the_saved_file_is_the_originals_but_for_its_pointers.py"
```

Under the [oracle](../glossary.md#oracle), `mission_won` and `choose_night` are held over 2,000 random states each, the walker's writes and reads over 600 each, and the score's formatting over 616 scores against the ROM's own RawDoFmt. Eight more scripts load the disk's file and a save by both paths, record a demo and play it back. After a load the port's state is the original's, the derived fields what the original's first tick makes of them; the port's recording is the original's file, and the original plays it as the port does. A recorded demo is replayed in the native core and in WebAssembly against the state's fingerprint after each of its 2,021 input samples, and page tests save, reload and load, and record, reload and play twice (chapter 24).

[Controls](../glossary.md#control), chapter 8's breaks of the port on purpose, were each caught:

| What was changed in the port | Script | Where it first showed |
|---|---|---|
| the promotion one mission early | the chain | pass 243, map n won |
| the extra Hellcat not given | the chain | the first tick of map k |
| the next mission's map one further | the chain | the second mission's first pass |
| a byte of the raw part one off | the save | byte 1,809 of the file |
| the soldiers' piece a record short | the save | the file's size |

/// dev
Other routines: `campaign_reset` `0x013562`, `rank_select` `0x018262`, `demo_end` `0x01852A`, `high_score_entry` `0x019472`. The scripts are [`tools/m7_scripts.py`](repo:tools/m7%5Fscripts.py), whose `trace NAME` prints the campaign tick by tick; the controls [`tools/m7_controls.py`](repo:tools/m7%5Fcontrols.py); [`tools/savegame.py`](repo:tools/savegame.py) with `--fields` names every byte of a raw part.
///

## What comes next

The chapter in one sentence: one table of maps by rank and mission number holds the campaign together, and a promotion that stops at rank 6 makes it endless; a reload keeps the high-score file, a saved game's memory and a demo's input bytes, the port's seed file beside them. Chapter 18 takes up the sound: the slots the next mission empties, the music a load stops, and Paula's channels.

## Further reading

- [`re/notes/campaign.md`](repo:re/notes/campaign.md): ["A mission won"](repo:re/notes/campaign.md#a-mission-won), ["The next mission"](repo:re/notes/campaign.md#the-next-mission), ["The saved game"](repo:re/notes/campaign.md#the-saved-game) and ["The loader"](repo:re/notes/campaign.md#the-loader).
- [`re/notes/demo.md`](repo:re/notes/demo.md): ["Recording"](repo:re/notes/demo.md#recording), ["Playback and the attract mode"](repo:re/notes/demo.md#playback-and-the-attract-mode) and ["The port"](repo:re/notes/demo.md#the-port); [`re/notes/highscore.md`](repo:re/notes/highscore.md).
- [`re/notes/porting-m7.md`](repo:re/notes/porting-m7.md): ["The scripts"](repo:re/notes/porting-m7.md#the-scripts), ["The port"](repo:re/notes/porting-m7.md#the-port), ["Part 2: the port"](repo:re/notes/porting-m7.md#part-2-the-port) and ["Part 2: how it is held"](repo:re/notes/porting-m7.md#part-2-how-it-is-held).
- [`src/front.c`](repo:src/front.c), [`src/dialog.c`](repo:src/dialog.c), [`src/hiscore.c`](repo:src/hiscore.c), [`tools/savegame.py`](repo:tools/savegame.py), [`tests/test_campaign.py`](repo:tests/test%5Fcampaign.py), [`tests/test_loader.py`](repo:tests/test%5Floader.py), [`tests/test_demo.py`](repo:tests/test%5Fdemo.py) and [`tests/test_replays.py`](repo:tests/test%5Freplays.py).
- [`original/manual.txt`](repo:original/manual.txt), the game's manual: pages 2 and 3 for the demo, 4 for the ranks, 8 and 10 for the Hellcats and the objectives, 11 for the high scores and the save, 12 for the commands.
