# The keys

Every key of the port, with when it acts and the original's key, named by position where keyboard layouts differ.

## The stick and fire

| Key | What it does |
|---|---|
| the arrow keys, or W, A, S and D | the stick: up is forward, which climbs |
| Space | fire; in a menu, choose |
| Enter | choose in a menu, the original's Return |

Fire also skips the story, the title pictures and the briefing. A gamepad works too, in a fixed mapping: its left cluster or left stick is the stick, its right cluster's four buttons and its two lower front buttons fire. The [vertical flip](glossary.md#vertical-flip) swaps forward and back and is remembered ([chapter 1](part-1/faithful.md#the-remembered-flip)); the [keyboard assist](glossary.md#keyboard-assist) makes a press one step in the weapon menu and lets a short tap reach the game once ([chapter 19](part-2/front-end.md#the-keyboard-assist)).

## The game's commands

| Key | What it does | When it acts | The original's |
|---|---|---|---|
| P, or Escape | pause, and continue | in flight | Escape |
| V | the vertical flip | in flight or paused | Control-F |
| G | save the game | on the carrier, in flight or paused | Control-G |
| L | load a saved game | in flight or paused, not while the demo plays | Control-L |
| M | the music off and on, the effects too | in flight or paused | Control-S |
| R | restart, back to the rank selection | while paused, or in the briefing | Control-R |
| C | clear the high scores, without asking | while paused | Control-C |

In flight is the whole of a mission, the deck included, and the game reads these keys while paused too. R and C wait for the pause, since without Control a stray press could throw a campaign away. The music's switch is cleared before every rank selection, and the rank selection's last item loads too. Inside the core each letter becomes the original's key ([chapter 19](part-2/front-end.md#the-key-layer)); inside the [line editor](glossary.md#line-editor) every key is a letter.

## The shell's keys

| Key | What it does | When it acts |
|---|---|---|
| H | the help screen | outside the line editor |
| any key | closes the help screen; the first of all only starts the sound | while the help screen is up |
| F | fullscreen on and off | outside the line editor |
| Escape | leaves fullscreen and pauses, never continues | in the page's own fullscreen |

The help screen, which lists the player's keys, is up when the page opens; over a running mission it pauses it until it closes. Leaving fullscreen in any way, or the page hidden for a second or more, pauses a mission; P continues. A key held with Control, Alt or Command belongs to the browser.

## The line editor

It takes the name for the high scores, up to 16 characters, and a saved game's name, up to 28:

| Key | What it does |
|---|---|
| a letter, a digit, a sign | goes in at the caret, if there is room; Shift and Caps Lock give capitals |
| Return or Enter, or fire | accepts the line |
| cursor left, right | moves the caret; with Shift, to the start or the end |
| cursor up, down, or the stick | leaves the line; in the save dialog, to the slot above or below |
| Backspace, Delete | deletes before the caret, or under it |

The original's clear-line, right Amiga with X, has no key in the port. A saved game's name gets `wof.` in front, a `:` or a `/` becoming a space.

## The original's commands

The game's manual lists the original's keys on its page 12, save and load also on page 11:

| Key | The manual | The program |
|---|---|---|
| Escape | pause; again, continue | the same |
| Control-R | restart, back to the rank selection | the same, in the briefing too |
| Control-F | flip the vertical control | the same |
| Control-G | save, on the carrier (page 11) | the same |
| Control-L | load | the same, but not while the demo plays |
| Control-D | show the high scores | absent: nothing reads it, and the port leaves it out |
| Control-C | clear the list, only after Control-D | clears them at once, in flight or paused |
| Control-S | nothing | switches the music off and on |

The program has two more Control keys the manual leaves out, into its crash reporter and for a version line, which the port never sends ([chapter 20](part-2/quirks.md#what-the-manual-promises)).

/// dev
The key left of 1 opens the shell's [diagnostics overlay](glossary.md#diagnostics-overlay), and so does the key right of the left Shift, since Chrome and Safari on a Mac with an ISO keyboard swap the two keys' codes, `Backquote` and `IntlBackslash`; neither reaches the game. Behind the overlay the digits are development keys, none of them the game's: 1 sets the score to 5,000, enough for the name entry; 2 and 3 open the save and the load dialog at the next rank chosen; 4 records the following games as the demo, or stops; 5 and 6 choose PAL and NTSC; 7 steps the stereo width and remembers it.

The function keys and Help stay with the browser, for reload and the developer tools, and no modifier is ever mapped: with Control as fire and W as up, firing while climbing would be Control with W, which closes the tab. The places: [`src/portkeys.c`](repo:src/portkeys.c), the key layer; [`web/input.js`](repo:web/input.js), the map from a key's position to the Amiga's key code; [`web/main.js`](repo:web/main.js), the shell's keys; [`re/notes/keys.md`](repo:re/notes/keys.md#the-commands), the original's commands state by state.
///
