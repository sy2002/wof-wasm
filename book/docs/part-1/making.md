Chapter 10
{ .chapter-kicker }

# How the port was made

This chapter tells who made the port and how the work was arranged, the other half of the case study: the port was made by its owner and by the sessions of an AI coding assistant, arranged so that the instruments, not the readers of the listing, would decide. By the end of this chapter you will know who "we" were, the rules the sessions worked by and the need each answers, what a task and a review contained, the method for each routine, the milestones in order, which model did which work, what it all took and what was learned the hard way. It is an overview, not a diary.

## Who we were

Two kinds of hand made the port. The first is its owner's. The owner set the goal, a faithful port in one HTML file with the logic taken from the executable, and made the decisions that shaped it: the keys, the order of the milestones, what was dropped, whether to publish. The owner tested what no instrument could, the fades by eye and every sound effect and every song by ear. The owner's own Amiga, a PAL machine, confirmed which way the stick climbs, and a film of its screen measured how long a pass takes (chapter 7). The work ran on the owner's computer, and the owner plays the port: findings from playing became tasks between the milestones.

The rest was done by sessions of an AI coding assistant, Claude Code. A [**session**](../glossary.md#session) is one conversation with the assistant in a terminal opened in the repository: it reads files, runs commands, writes code and commits. What it has read and written is its context, and the context has a limit; when it fills, the session makes way for a fresh one, which knows nothing of the conversation before it.

One session led. The [**controller**](../glossary.md#controller) is the session the owner talks to: it assigns the tasks, checks every result itself, merges, keeps the specification and the rules true, and is the only session that asks the owner for anything. The others were [**workers**](../glossary.md#worker): sessions the owner opened in terminals of their own, each doing one task the controller sent it, a [milestone](../glossary.md#milestone) or a bounded part of one, on a branch of its own, and reporting to the controller alone. Every milestone got a fresh worker. The owner chose each session's model and effort; a session cannot set its own.

The controller changed too. Its context costs budget on every turn and fills as the work goes on, so before it was full, at a quiet point, it handed the lead to a fresh session the owner had opened in advance. That is a [**handover**](../glossary.md#handover): the lead passed on through the repository and a message saying where things stand. It works only if the repository holds everything, so the rule every session reads first is that nothing may live only in a conversation. A worker starts from the specification and the notes, and ends by writing back its names, its findings, each routine's status and every correction to the specification.

![The owner above the controller, two-way; a worker to its left, getting a task and returning a report, two idle workers above it; the controller before, to the right, handing over; below, the repository's main branch and one task branch, the worker committing on it, the controller merging it.](../figures/arrangement.svg)

/// caption
The arrangement. The owner talks to the controller, which sends one worker its task and reviews its report; the idle workers stand for sessions opened in advance, however many. All share one working directory, one task branch out at a time, and a controller hands the lead on through the repository.
///

The sessions' handbook, [`CONTROLLER.md`](repo:CONTROLLER.md), is published as it was used; [`CLAUDE.md`](repo:CLAUDE.md) holds the rules every session reads first.

## The rules, and what each answers

A worker never asks the owner anything. Its questions, and whatever needs the owner's eyes, ears or decision, go into its report, and the controller relays what it cannot answer itself. The owner watches one chat, the controller's, and would miss a request made anywhere else.

Every ask of the owner carries its whole context and a recommendation, and is repeated in every brief, the controller's short account of where things stand, until it is answered: by the time the owner reads, the terminal has scrolled far past any earlier message. An ask asks for the least that settles the question and recommends an answer to each decision, so that a reply of one line, all as recommended, settles it.

All sessions share one working directory. While a worker has its branch out, the controller edits nothing, because a file it made could be swept into the worker's commits. So a task goes out only with the main branch checked out, the tree clean and no other worker busy, and one branch is out at a time; the owner decided against separate working copies for workers in parallel. The page is the owner's copy of the game: a worker never commits it, and the controller rebuilds and commits it at every merge, so that the committed page is always the build of the committed sources.

The owner works on the same computer while the sessions run. So the browsers in the tests are muted, a test that needs a visible browser window runs while the owner is away, since a covered window stops the page's clock, and while the owner works the suite takes at most four cores.

The owner is often away for hours and did not want the work to wait for their testing. In the asynchronous mode the controller goes on through the milestones, decides routine questions itself and states each decision with its recommendation in the next brief, stopping only for a question nothing sensible can be done without. When the owner returns, the brief opens with where things stand, then what is needed. Times are taken from git's commit times, never from a session's own sense of the clock, which drifts.

A worker stops and reports instead of trying again when an oracle test still fails after two fixes, when a hand-written routine is not understood after reading it whole, or when a change would alter a structure's layout, the core's interface or a porting rule: those are the controller's decisions, and through it the owner's. The owner let the controller merge once a result was verified; nothing is pushed to any server without the owner's word.

## A task and a review

A task is one message, and its first line is a complete sentence, since that is all a worker's terminal shows at first. The handbook gives a task ten parts:

1. what the task is, from the controller;
2. that the owner set this up and the worker reports to the controller only;
3. what to read first;
4. a clean tree, the branch and its starting commit;
5. what may be changed and what not;
6. the deliverables, numbered;
7. the verification, as a method rather than a wish;
8. the milestone's acceptance criterion;
9. when to stop and report;
10. what the report holds: the files, the commands with their real output, where the specification was wrong or silent, what is fragile, what needs the owner, the commits.

Then the controller waits for the report.

A report is a claim. Before anything is merged, a [**review**](../glossary.md#review) checks it in seven steps:

1. the git facts: the commits, no forbidden path touched, no generated file or game data committed;
2. a clean rebuild and the full suite, run by the reviewer;
3. no game content in the hand-written files;
4. a reading of the code that carries the weight and of how the tests compare, for a differential test must really run the original and the port;
5. one check of the reviewer's own that the worker's tests could not make;
6. a follow-up on the same branch if anything is wrong, and the review again;
7. the merge, the findings folded into the specification, the page rebuilt.

The fifth step is the one chapter 8 ended with. The worker chose its scripts, maps and seed, and its tests pass on what it thought of; a check on inputs it never chose meets what it did not. The reviews' own runs and checks found real defects. The full suite, run again at a review on a busy machine, failed one script once, and led to the harness's timeout. A [closed loop](../glossary.md#closed-loop) on another seed and at other pass rates found a cache of the comparison's own and a register's upper word handed on. Reading the routine the game calls, rather than the stub that answered for the call, corrected a claim about a map's last records. All three are chapter 9's. A reviewer's own reading of the music player against the listing found a branch the port had to mark as a [stand-in](../glossary.md#stand-in).

A full run of the suite takes over an hour, so by the owner's rule a follow-up confined to the port's own key policy, such as the keyboard assist, or to the page, on which no ported routine and no differential test depends, gets a targeted run of the tests that hold that layer. Anything that touches ported code, and every milestone, gets the whole suite.

## The method, routine by routine

Inside a task, each routine went through the same six steps, written into the specification. Print its [control-flow skeleton](../glossary.md#control-flow-skeleton), then read it in the [listing](../glossary.md#listing). Name it, and the variables it touches, in the names file, and make the listing again. Write the C, with a comment that names the original's address. Give a [pure routine](../glossary.md#pure-routine) an [oracle](../glossary.md#oracle) test, which is mandatory. Set its status in the [routine inventory](../glossary.md#routine-inventory). When a part of the game is understood, write a note, so that later sessions start from it instead of working it out again. Every statement in the notes of the milestones M4 to M8 says whether it was observed, with the tool or the test that shows it, or read, from the listing alone. No session loads the listing whole, about 1.6 megabytes: it reads a skeleton, a search or a range of addresses, and keeps its context for the work.

Where a rule could be a test, it was made one. The listing and the inventory are never edited by hand: a name goes into the names file, and the disassembler makes both again. Both are committed, so that a reader can browse them without running anything, and a committed file gone stale would mislead that reader. Here is the test that prevents it. Look at lines 3 and 4, which run the two disassemblers into a directory of the test's own, never over the committed files, and at lines 6 to 8, which compare each file byte for byte and say what to do when one differs.

```python linenums="1"
--8<-- "generated/listings/py/test_the_listings_are_their_regeneration.py"
```

Before a milestone began, the questions it needed answered were settled: the specification lists thirteen points to establish, each answerable from the listing and due before the milestone that consumes its answer, so that no milestone was built on a guess. Three of them, what a [pass](../glossary.md#pass) writes and a tick reads, the game's objects and the map's records, were answered by watching the [headless original](../glossary.md#headless-original) rather than by reading alone.

## The milestones

The port was built in milestones, each ending with a working page and green tests. Here they are in the order they were done.

| Milestone | What it delivered | What held it |
|---|---|---|
| M0 | the build, an empty core, the shell's screen, clock, keys and sound | the page from a file, a steady test pattern, a tone after a key, nothing from the network |
| M1 | the file system, the memory, the loaders and decoders, the font, the tables | the first pictures in their colours, text in the game's font, the decoders under the oracle |
| M2 | the headless original, as far as a mission's first pass | a dump after every tick, and two runs the same |
| M3 | the [front end](../glossary.md#front-end) and the port's keys | the original's choices for the same keys, compared VBlank by VBlank |
| four points | what a pass writes and a tick reads, the map, the objects, the floating point | the headless original watched; the floating point against the ROM |
| M4 | the world and the player | a mission flown and ended, compared tick by tick in both loops |
| M5 | the weapons and the ground targets | the same, on the first three maps |
| M6 | the enemy aircraft and the ships | the same, on all fifteen maps |
| M8 | the sound effects and the music | the sound events equal in every loop, the music VBlank by VBlank, the owner's ears |
| M7 | the campaign, the saved game and the demo | a whole campaign; the demo byte for byte, the saved file but for four pointers; a replay after a reload |
| M9 | the picture drawn by the graphics card | the frame time at the screen's size in both browsers, the owner's look in full screen |
| the release groundwork | the page and the game data in the repository, one check of the ROM, the generated files held | a fresh clone, with and without the ROM; one run of the suite |

M4 to M8 were each done in two parts, with a review and a merge between them, and the stand-ins each milestone left named what the next had to reach (chapter 8). The order was the owner's. The front end came first because it showed progress in the browser early, depended little on the game's objects, and the owner's look at the running page found what tests could not. The sound came before the campaign, to be in the page sooner for the owner's test flights. M9 was to be the shell's polish until the frame rate halved at a large full-screen size; the owner made it the page's drawing on the graphics card instead.

Three things were left undone, each by the owner's decision. M10, the shell's options (keys of the player's choosing, a gamepad, the scaling, the video standard, a mute for the title's music, an export of saved games), was dropped when the owner judged the game done for now; only bug fixes may come. The game's hidden cheat sequence was not needed, and chapter 1 told why it can no longer be typed. And beyond the one film, the real machine was not measured again: a busy scene's rhythm, the speed of the fades and the order of a directory stay as the port has them, because the port felt right to the owner as it was.

## Two models, and no swarm

The controller ran on the stronger and scarcer of two models, Fable, the workers on the cheaper one, Opus. The owner's budget for the stronger model was limited and the controller needed it on every turn; beyond that it is kept for reading no observation can check and for design decisions no test can catch.

The handbook gives the reason the cheaper model was enough: what makes a worker reliable at reading is its task, not its model. A task demands that every finding be backed by an observation, from the oracle, the headless original or a test, and says which instrument answers which question. A reading mistake of the early days, the stick's bits of chapter 9, was found by an observation, not by a better reader.

The owner asked whether a worker should fan out into many agents at once. The answer was no. The original program, run and compared, is a stronger adversary than a reviewing agent; time on the clock was not scarce; every agent pays again to read the rules and the notes; and the work is a chain through shared files. One estimate settled it, from the width of the game's object system: fourteen tables, the code that runs them about 11 kilobytes in eight groups that share their helpers, and a record's behaviour a chain of tests inside one routine rather than a handler for each kind of object. There was nothing wide to fan out over, and one worker per milestone stayed.

## What it took

The game took about twelve days of calendar time, from the first commit to the owner's decision that it was done. By the owner's reckoning, about two fifths of that went into what does not depend on this game, the instruments, the runtime, the shell and the method, and three fifths into porting the game itself. Every commit carries the owner as its author and the assistant as co-author.

/// figures
| What it took | How much |
|---|---|
| Calendar days, the first commit to the game done | about 12 |
| Commits, the game and the book so far | about 290 |
| Controller sessions, to the game's end | 11 |
| Worker sessions the handbook names | 10 for the game, 9 for this book |
| The core, in C | about 19,400 lines |
| The shell, in JavaScript, HTML and CSS | about 2,400 lines |
| The tools | about 12,400 lines |
| The tests | about 23,000 lines, about 930 tests |
| A full run of the suite | about an hour and twenty minutes, in two phases |
| The notes | 29, about 196,000 words |
| The specification | about 19,700 words |
///

The routines of the game's program stand as follows; chapter 4 tells what each status means. Most of those with no status are the C library, the system's glue and code nothing calls, which the port does its own way or never runs.

| Status | Routines |
|---|---|
| verified | 167 |
| ported | 155 |
| partial | 1 |
| replace | 47 |
| drop | 31 |
| no status | 215 |

## What the arrangement learned the hard way

Some lessons cost time before they became rules; the handbook keeps them as warnings. These are the arrangement's own.

- An expired login stops every session without a word, so before a long run without the owner the controller checks when the login expires and asks for it to be renewed.
- A computer left alone goes to sleep, and a sleep stops every session; once it cost an hour in the middle of a milestone. A long run without the owner starts with a command that keeps the machine awake, and a test that ran across a sleep counts for nothing.
- A usage limit stops every session in mid-turn, and only the controller resumes by itself. So the controller checks about every fifty minutes and tells a worker found idle without a report to look at the repository's state first and to treat an interrupted test run as void; every task carries the same clause and asks for whatever is green to be committed.
- A notice that a worker is idle comes at every pause between its turns, so the controller asks for one notice with the task and waits for the report.
- A file made in the shared directory while a worker has its branch out can land in the worker's commits, hence no edits beside a worker.
- A controller's test run that overlapped a worker's rebuild compared an old native library with a new core, and four tests failed that never failed again; a run is stopped before a follow-up that builds goes out.
- The suite's move to running in parallel was verified with five full runs where one would have done, which cost an afternoon. By the owner's rule, a change to the infrastructure gets one verification run.

## An honest account

The sessions did more reading and writing than one person could have done in those twelve days. Every routine the game runs was read and rewritten, 445 of the program's 616 routines now carry a name, and what was learned went into the notes beside the suite; the figures above give their size.

The sessions also got things wrong. Chapter 9 told the mistakes, in reading, in the instruments and in the tests. In all but one, an instrument, or a reading of what the code really calls, decided against the belief, and a few were for the owner's eyes, ears and keyboard to find. The arrangement's own mistakes are the warnings above.

The owner did what no session could. The decisions were the owner's, and so were the eye on the fades, the ear on every sound, the real Amiga and its film, and the playing that found what no test had: the page in Firefox standing still and silent after it went to full screen, and a key that would not open the page's diagnostics in two browsers. No session can decide what the port is for, or hear whether a song sounds right.

What this makes the port is a record that can be checked rather than trusted. The source, the notes with what was observed and what was only read, the tests, the handbook with its rules and its warnings, and the history of every change are in the repository, and anyone with the ROM can run the original beside the port and compare.

The owner has also written down an idea of what may follow, not started: a template, "Amiga to Web", that would carry the instruments, the runtime, the shell and this method to other Amiga games built as this one is. It would be proven only when a second game went through it.

## The same method for this book

This book is made the same way. Each chapter starts as a fact sheet: every claim it will make, with its source in the repository. A worker writes the draft from it. A second worker that had no part in the draft checks every claim against the notes and the listing, and a fresh session given only the chapter and the glossary reads it as you do and reports where it lost the thread; neither edits anything. The controller reads and edits; the owner's read is the last gate. The order of events comes from a dated record kept outside the repository; the claims are sourced inside it. At every chapter's merge so far, the checks also found something to correct in the notes or the specification: the method checks the record as well as the book.

## What comes next

Part I has told how the port was made and how it is known to be faithful. Part II opens the game itself, now that you know how the knowledge of it was made and kept, beginning in chapter 11 with the display: its areas, its bitplanes, the copper lists the game builds and the palettes that change down the picture.

## Further reading

The files named here are in the repository, [`github.com/sy2002/wof-wasm`](repo:).

- [`CONTROLLER.md`](repo:CONTROLLER.md), the handbook: ["The arrangement"](repo:CONTROLLER.md#the-arrangement), ["The user's conventions"](repo:CONTROLLER.md#the-users-conventions), ["Driving workers"](repo:CONTROLLER.md#driving-workers), ["What a task contains"](repo:CONTROLLER.md#what-a-task-contains), ["Reviewing a report"](repo:CONTROLLER.md#reviewing-a-report), ["Models and effort"](repo:CONTROLLER.md#models-and-effort), ["The plan ahead"](repo:CONTROLLER.md#the-plan-ahead) and ["Pitfalls that cost time"](repo:CONTROLLER.md#pitfalls-that-cost-time).
- [`CLAUDE.md`](repo:CLAUDE.md): ["Session protocol"](repo:CLAUDE.md#session-protocol) and ["Rules"](repo:CLAUDE.md#rules).
- [`SPEC.md`](repo:SPEC.md), sections 7.4, ["Working method"](repo:SPEC.md#74-working-method); 9, ["Milestones"](repo:SPEC.md#9-milestones); 10, ["Points to establish"](repo:SPEC.md#10-points-to-establish).
- [`book/BOOK.md`](repo:book/BOOK.md#6-the-way-of-working), section 6, "The way of working".
- [`README.md`](repo:README.md#amiga-to-web), "Amiga to Web", and [`re/notes/amiga-to-web.md`](repo:re/notes/amiga-to-web.md).
- [`re/notes/testing.md`](repo:re/notes/testing.md#times-and-how-many-workers), "Times, and how many workers".

Outside the repository: Wikipedia's ["Code review"](https://en.wikipedia.org/wiki/Code%5Freview), the practice the review follows.
