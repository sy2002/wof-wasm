# The keys

Every key of the port, with when it acts and the original's key. The letters are where a US or a German keyboard has them; the port reads a key's place, so where a layout moves a letter, the key at that place acts ([chapter 1](part-1/faithful.md#the-keys)).

## The stick and fire

| Key | What it does |
|---|---|
| the arrow keys, or W, A, S and D | the stick: up is forward, which climbs; towards the aircraft's facing the throttle, against it a turn |
| Space | fire; in a menu, choose |
| Enter, the keypad's too | choose in a menu, the original's Return |

Fire also skips the [story](glossary.md#story-scroller), the title pictures and the [briefing](glossary.md#briefing). A gamepad steers with its d-pad or left stick and fires with its four face buttons and two lower triggers; the commands need the keyboard. The [vertical flip](glossary.md#vertical-flip) swaps forward and back and is remembered ([chapter 1](part-1/faithful.md#the-remembered-flip)); the [keyboard assist](glossary.md#keyboard-assist), which the page turns on, makes a press one step in the weapon menu of the [hold](glossary.md#hold), and a short tap is never lost ([chapter 19](part-2/front-end.md#the-keyboard-assist)).

## The game's commands

| Key | What it does | When it acts | The original's |
|---|---|---|---|
| P, or Escape | pause, and continue | in a mission | Escape |
| V | the vertical flip | in a mission or paused | Control-F |
| G | save the game | on the carrier, in a mission or paused | Control-G |
| L | load a saved game | in a mission or paused, not while the [demo](glossary.md#attract-demo) plays; or the [rank selection](glossary.md#rank-selection)'s last item | Control-L |
| M | all sound off and on, the music and the effects | in a mission or paused | Control-S |
| R | restart, back to the rank selection | while paused, or in the briefing | Control-R |
| C | clear the high scores, without asking | while paused | Control-C |

R and C wait for the pause, since without Control a stray press could throw a [campaign](glossary.md#campaign) away. The game switches the sound back on before every rank selection.

## The shell's keys

| Key | What it does | When it acts |
|---|---|---|
| H | the help screen | outside the [line editor](glossary.md#line-editor) |
| any key but a lone modifier or one held with Control, Alt or Command | closes it; the very first only starts the sound, the screen going once the sound runs | while the help screen is up |
| F | fullscreen on and off | outside the line editor |
| Escape | leaves fullscreen and pauses, never continues | in the fullscreen F gives, not the browser's own |

The help screen, the [shell](glossary.md#shell)'s list of the player's keys, pauses a running mission until it closes. Leaving fullscreen in any way, or the page hidden for a second or more, pauses a mission; P continues.

## The line editor

It takes the name for the high scores in the [name entry](glossary.md#name-entry), up to 16 characters, and a saved game's name, up to 28:

| Key | What it does |
|---|---|
| a letter, a digit, a sign | goes in at the caret, if there is room; Shift and Caps Lock give capitals |
| Enter, the keypad's too, or fire | accepts the line |
| cursor left, right | moves the caret; with Shift, to the start or the end |
| cursor up, down, or the stick | leaves the line; in the save dialog, to the slot above or below |
| Backspace, Delete | deletes before the caret, or under it |

The original's clear-line, right Amiga with X, has no key in the port.

## The original's commands

These Amiga keys are not for the browser, which keeps Control with R, L and F: Control with R reloads the page, losing a game not saved ([chapter 1](part-1/faithful.md#the-keys)). The game's manual lists them on its page 12, save and load also on page 11. Escape, and Control with R, F, G and L, work as it says; the manual and the program part on three ([chapter 20](part-2/quirks.md#what-the-manual-promises)):

| Key | The manual | The program |
|---|---|---|
| Control-D | shows the high scores | absent: nothing reads it; the port leaves it out |
| Control-C | clears them, only after Control-D | clears them at once, in a mission or paused |
| Control-S | not listed | switches all sound off and on |

/// dev
The key left of 1 opens and closes the shell's [diagnostics overlay](glossary.md#diagnostics-overlay), and so does the key right of the left Shift, since Chrome and Safari on a Mac with an ISO keyboard swap the two keys' codes, `Backquote` and `IntlBackslash`; neither reaches the game, and the same key closes it. Behind the overlay the digits are development keys, which change the game's score and open its dialogs. 1 sets the score to 5,000, enough for the name entry. 2 and 3 open the save and the load dialog at the next rank chosen; 4 records the following games as the demo, or stops. 5 and 6 choose [PAL](glossary.md#pal) and NTSC, and 7 steps the stereo width and remembers it.

Inside the [core](glossary.md#core) the [key layer](glossary.md#key-layer) turns each command letter into the original's key ([chapter 19](part-2/front-end.md#the-key-layer)). In the line editor every key but the diagnostics key is a character or an editing key, and a saved game's name gets `wof.` in front, `:` and `/` becoming spaces. The function keys and Help stay with the browser, for reload and the developer tools; no modifier is ever mapped, since with Control as fire and W as up, firing while climbing would close the tab. The places: [`src/portkeys.c`](repo:src/portkeys.c), the key layer; [`web/input.js`](repo:web/input.js), the key map; [`web/main.js`](repo:web/main.js), the shell's keys; [`re/notes/keys.md`](repo:re/notes/keys.md#the-commands), the original's commands.
///
