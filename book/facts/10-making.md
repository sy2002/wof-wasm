# Fact sheet: chapter 10, How the port was made

Every claim the chapter makes, one line each, with its source, in the order of the chapter. A claim without a source in the repository goes to the list at the end and stays out of the draft. The chapter is the one place of the book that tells how the work was arranged (`book/BOOK.md` 4, point 10); it tells it as an overview of the arrangement, its rules and its results, never as a diary: no dates, no times of day, no quotes, no session by its name or number. Durations in days are given where they are the point.

The project's chronicle, kept outside the repository (`CONTROLLER.md`, "The user's conventions", Times; `book/BOOK.md` 6), was read for the order of events and the decisions, as the writers' private source; no claim below rests on it. Where the chronicle holds something the repository does not, it is on the unsourced list.

Counts are of the branch's base, `f8b5fd9`, measured with the commands in the counts table at the end. Nothing was run but the book's build and one collection of the tests: no headless original, no comparison, no test, no browser. By the owner's rule on numbers the prose keeps about three numbers a sentence; the counts go to the figures box and the milestones' table; derived numbers stay out of the prose; this sheet keeps every figure exact.

The works outside the repository, each fetched once:

- Wikipedia, "Code review", `https://en.wikipedia.org/wiki/Code_review`: code review is "a software quality assurance activity in which one or more people examine the source code of a computer program", the checking persons, "excluding the author", called reviewers; it covers change-based review before code is integrated. For the Elsewhere line of the Review entry.

## Opening

1. By the chapter's end the reader knows who made the port (the owner and the sessions of an AI coding assistant), how the sessions were arranged (one controller, workers, handovers), the rules of the arrangement and the need each answers, what a task and a review contained, the method per routine and the points settled before a milestone, the milestones in order with what held each, which models did what and why, what it took, what the arrangement learned the hard way, an honest assessment of the collaboration, and how this book is made by the same method. Source: `book/BOOK.md` 3, chapter 10; the controller's task.
2. The chapter's thesis, drawn from chapter 9: the work was arranged so that the instruments, not the readers of the listing, decided. Source: `book/docs/part-1/wrong.md`, "What comes next"; `CONTROLLER.md`, "Models and effort" ("What makes Opus reliable at reading is the task, not the model").

## 1. Who we were

3. The owner set the goal: a faithful port of the game to one HTML file, its logic ported from the executable. Source: `SPEC.md` 1 ("Port the Amiga game ... as one self-contained HTML file"; "ported from the original 68000 executable, routine by routine"); `book/docs/part-1/faithful.md`.
4. The owner made every decision of the project: the keys, the order of the milestones, the redefinition of M9, the dropping of M10, the cheat sequence, the measurements on the real machine, the publication. Source: `CONTROLLER.md`, "The plan ahead" (the keys decision "made with the user"; "The user chose the order"; "The order after M6, decided by the user"; "M9 redefined by the user"; "The user decided the same evening that the game is done for now and M10 is dropped"); "Open items" (the cheat sequence "decided by the user"; "Decided by the user ...: no Amiga measurements"); `SPEC.md` 1 (the owner's decision to publish).
5. The owner tested by eye and ear: the fades by eye, every effect and every song by ear. Source: `CONTROLLER.md`, "Open items" ("The user's impression of the logo, title and credits decides it, and it is right for them"; "The listening check of M8 is complete: every effect, the soldiers' screams last, and every song confirmed by the user"); `SPEC.md` 9 ("the owner heard every effect and every song ..., found them right").
6. The owner's real Amiga, a PAL machine, confirmed the stick's sense, and the owner filmed its screen at 240 frames a second to measure the VBlanks a pass. Source: `CONTROLLER.md`, "The user's conventions" ("The user's Amiga is a PAL machine"); "Open items" ("confirmed by the user on the real Amiga"; "measured ... on the user's PAL Amiga by 240 fps film"); `re/notes/passes.md`, "What the film of the real machine shows"; `tools/film_rate.py`.
7. The owner is the port's player: the committed page is the owner's copy, and the owner's findings from playing became tasks. Source: `CONTROLLER.md`, "Driving workers" ("`dist/wof.html` ... is the user's copy"); "The arrangement" ("Worker test findings" for the user's own findings from playing; "Findings from the user's play go to the findings worker as bounded fix tasks between milestones").
8. The owner's own Kickstart ROM gave the system font and the floating point the port is held to, and the work ran on the owner's machine. Source: `SPEC.md` 10, last paragraph ("come from the owner's Kickstart ROM"); `CONTROLLER.md`, "Pitfalls that cost time" ("The user works on this machine while tests run").
9. The rest of the work was done by sessions of an AI coding assistant, Claude Code (named once in the chapter, as the handbook's opening names it). Source: `CONTROLLER.md`, opening paragraph ("the port was made by Claude Code sessions under the owner's direction").
10. A session is one conversation with the assistant in a terminal in the repository: it reads files, runs commands and commits; its context, what it has read and written in its conversation, fills, and a session whose context is full is replaced by a fresh one. Source: `CONTROLLER.md`, "The arrangement" ("The user opens every other session in a new terminal in this directory"; "when its context fills, it hands over to a fresh session"); "The plan ahead" ("Part 2 goes to a fresh session ... because the part 1 worker's context was at 86 percent"). The definition is the chapter's, from these.
11. One session leads, the controller: the owner talks to it alone; it assigns tasks, verifies every result independently, merges, keeps `SPEC.md` and `CLAUDE.md` true, and is the only session that asks the owner for anything. Source: `CONTROLLER.md`, "The arrangement".
12. The other sessions are workers, each opened by the owner in a terminal of its own and driven by the controller by message; one milestone, or one bounded task, per worker session. Source: `CONTROLLER.md`, "The arrangement"; "Models and effort" ("One milestone, or one bounded task, per worker session. A fresh session per milestone").
13. Sessions are named, controllers counting up with each handover and workers after what they do; the owner keeps an overview by the names. The chapter names none. Source: `CONTROLLER.md`, "The user's conventions", Session names.
14. The owner sets each session's model and effort; a session cannot. Source: `CONTROLLER.md`, "The user's conventions" ("The user sets them; you cannot"); "Driving workers".
15. The controller changes over as its context fills: it hands over to a fresh session at a quiet point, by message, and says so in its last brief; the owner opened the next controllers in advance and left them idle. Source: `CONTROLLER.md`, "The arrangement" ("when its context fills, it hands over to a fresh session at a quiet point"; "a retiring controller hands over to the next idle controller by message"; "the next controllers ... Controller Instance N+1").
16. Why early: the controller's context costs budget on every turn, so it hands over at a quiet point rather than late. Source: `CONTROLLER.md`, "Models and effort" ("The controller's own context costs budget on every turn, so hand over early, at a quiet point, rather than late").
17. The repository, not a conversation, is the handover: nothing may live only in a conversation; a worker starts from `SPEC.md` and the notes and ends by writing names, findings, statuses and spec corrections back. Source: `CLAUDE.md`, "Session protocol" ("The repository is the handover: nothing may live only in a conversation"; Start; End); `CONTROLLER.md`, "Models and effort" ("A fresh session per milestone: the repository is the handover").
18. The handbook of the sessions, `CONTROLLER.md`, is published as it was used; workers follow `CLAUDE.md` and their task. Source: `CONTROLLER.md`, opening paragraphs.
19. The figure `arrangement.svg` (claims 11 to 17, 23 to 25).

## 2. The rules, and what each answers

20. A worker never asks the owner anything; everything goes to the controller, which relays what needs the owner, because the owner watches the controller's chat and would miss a request made anywhere else. Source: `CLAUDE.md`, "Session protocol" ("Worker sessions do not ask the user for anything ... The user watches the controller chat and will miss a request made anywhere else"); `CONTROLLER.md`, "What a task contains" (last paragraph); "Asking the user" ("Relay a worker's requests yourself and drop those you can answer").
21. Every ask of the owner is self-contained, step by step, with a recommendation, and repeated in every brief until answered, because the terminal has scrolled far by the time the owner reads. Source: `CONTROLLER.md`, "The user's conventions" ("Every ask is self-contained ... because the terminal has scrolled far by the time they read. Every open ask is repeated in full in every brief").
22. An ask asks for the minimum that settles the question and gives a recommendation with every decision, so that "all as recommended" is a complete answer. Source: `CONTROLLER.md`, "Asking the user". (The phrase is the handbook's; the chapter paraphrases: an answer of one line, all as recommended, settles it. Not a quote of the owner.)
23. All sessions share one working directory; while a worker has its branch checked out the controller makes no edit in the repository, because a file it creates can be swept into the worker's commits; reading, building and testing are safe once the worker is idle. Source: `CONTROLLER.md`, "Driving workers".
24. Before a task is sent: the main branch checked out, the tree clean, no other worker active; the owner decided against separate working copies: one worker with a branch checked out at a time. Source: `CONTROLLER.md`, "Driving workers"; "The plan ahead" ("The user decided the same day: no worktrees, one worker with a branch checked out at a time").
25. A worker never commits the page; the controller rebuilds it and commits it at every merge, so that the committed page is always the build of the committed sources. Source: `CLAUDE.md`, "Rules"; `CONTROLLER.md`, "Driving workers".
26. The owner works on the same machine while the sessions run: the browsers in tests are muted, a visible window is announced, the visible browser checks run in the owner's absence, and while the owner works at the machine the suite uses at most four cores. Source: `CONTROLLER.md`, "Pitfalls that cost time" ("The user works on this machine while tests run. Browsers in tests stay silent ... and a visible window is announced beforehand"; the first point: "Ask the user for an away window and run the visible module alone in it"); "The plan ahead" ("The user's rule ... while they work at the machine: at most four cores"); "Asking the user" ("Browsers stay muted").
27. The asynchronous mode: the owner is away for hours and does not want the work to wait for their testing; the controller goes on through the milestones, decides routine questions itself, states each decision with its recommendation in the next brief, and stops only for a question nothing sensible can be done without; the owner opens sessions in advance. Source: `CONTROLLER.md`, "The arrangement", the asynchronous mode.
28. When the owner returns, the controller leads with where things stand in a few lines, then what is needed. Source: `CONTROLLER.md`, "The user's conventions".
29. Times are taken from git's commit times, not from a session's sense of the clock, which drifted by up to half an hour. Source: `CONTROLLER.md`, "The user's conventions", Times. (The chapter: "a session's sense of the clock drifts"; the half hour stays here.)
30. A task is one message, its first line a complete sentence, because that is all the worker's terminal shows at first; the controller does not poll, the report arrives as a message. Source: `CONTROLLER.md`, "Driving workers".
31. A worker stops and reports instead of retrying when an oracle test still fails after two fixes, when a hand-written routine is not understood after reading it in full, or when a change would alter a struct's layout, the core's interface or a porting rule. Source: `CLAUDE.md`, "Session protocol" (Stop and report). Why (the chapter's reasoning): those are the decisions the controller, and through it the owner, must see.
32. The owner authorised merges and commits at the controller's discretion once verified; nothing is pushed to a remote unless the owner asks. Source: `CONTROLLER.md`, "Reviewing a report", step 7; `CLAUDE.md`, "Rules".
33. A follow-up confined to the port's policy layer or the page, which no ported routine and no differential test depends on, gets a targeted run instead of the full suite, by the owner's rule; anything that touches ported code, and every milestone, gets the full suite. Source: `CONTROLLER.md`, "Reviewing a report", step 2.

## 3. A task and a review

34. A task has ten parts: what it is, from the controller; that the owner set this up and the worker reports to the controller only; what to read first; `git status` first and the branch and its start; the scope; numbered deliverables; mandatory verification stated as a method; the acceptance criterion from `SPEC.md` 9; when to stop and report; what the report must contain (files, commands with real output, where the spec was wrong or silent, what is fragile, what needs relaying, the commits). Source: `CONTROLLER.md`, "What a task contains" (ten numbered items, counted).
35. A report is a claim. Source: `CONTROLLER.md`, "Reviewing a report" (its first line).
36. The review has seven steps: the git facts; a clean rebuild and the full suite run by the reviewer; the rule that hand-written files hold no game content; reading the code that carries the weight and how the tests compare (a differential test must really run the original and the port); one check of the reviewer's own that the worker's tests could not make; a follow-up on the same branch if something is wrong; the merge, the listings regenerated, the findings folded into `SPEC.md`, the page rebuilt and committed. Source: `CONTROLLER.md`, "Reviewing a report" (seven numbered steps, counted).
37. Why a check of one's own: the worker's tests were chosen by the worker; a check on inputs the worker never chose meets what the worker did not think of. Source: `book/docs/part-1/mission.md`, "A check by another hand" ("The porter chose the scripts, the maps and the seed; the check uses others"). The chapter's reasoning from it.
38. Checks of the reviewer's own that found real defects: the full suite at a review failed one script once, which led to the harness's timeout (chapter 9); a closed loop at pass rates and on a seed the worker never used found a cache of the comparison's and a register's upper word (chapter 9); a reading of the routine the game calls, rather than the stub that answered for it, corrected a claim that a map's last four records are uninitialised (chapter 9); the reviewer's own reading of the music player against the listing found a branch the port had to mark as a stand-in. Source: `CONTROLLER.md`, "The plan ahead" (the M8 part 2 review: "At the review the controller's full suite failed the two M6 loops of `japcarrier_m` once"; the M7 part 1 review: "the closed loop on entropy seed 7 at pass rates the worker never used, which found a difference ...; the follow-up ... found beside it a real port bug"; points 2, 5 and 3: "The review found one wrong claim, which the worker corrected: the last four records of a map are not uninitialised"); "Open items", the M8 left-overs ("Found by the controller's independent reading"); `book/docs/part-1/wrong.md`.
39. A check can also give assurance, and send facts early: the reviewer of the music sent two facts of the hardware to the worker before either side of the comparison could build a wrong model in. Source: `CONTROLLER.md`, "The plan ahead", M8 part 2 ("two hardware facts sent early, before either side could bake a wrong model in"). The handbook's list of examples (claim 36's step 5) "found real defects or gave real assurance".
40. The original program, run and compared, was judged a stronger adversary than any reviewing session. Source: `CONTROLLER.md`, "Models and effort", Multi-agent workers ("The original executable is a stronger adversary than a reviewing agent"). Paraphrased, not quoted.
41. The rule that completes chapter 8's method is this review: a claim is reviewed with one check of the reviewer's own. Source: `book/docs/part-1/mission.md`, "A check by another hand".

## 4. The method, routine by routine

42. The method for each routine has six steps: its control-flow skeleton with `tools/skel.py`, then the routine read in the listing; it and the globals it touches named in `re/names.txt` and the listing regenerated; the C written with the comment that names the original's address; an oracle test for a pure routine, mandatory; the status set in `re/functions.csv`; and, when a subsystem is understood, a note in `re/notes/`. Source: `SPEC.md` 7.4 (six numbered steps, counted); `CLAUDE.md`, "Rules" ("Every ported routine carries an `orig 0x......` comment. Pure routines get an oracle test before they count as `verified`").
43. Why the notes: later sessions start from them instead of deriving it again. Source: `SPEC.md` 7.4, step 6 ("Later sessions start from these notes instead of re-deriving them"); `CLAUDE.md`, "Rules" ("When a subsystem is understood, write it down in `re/notes/` so that later sessions do not re-derive it").
44. Every statement of a porting note is marked observed, with the tool or test that shows it, or read, from the listing alone. Source: `re/notes/porting-m4.md` and `re/notes/porting-m7.md`, opening paragraphs; `SPEC.md` 10, last paragraph ("the notes mark every finding as observed, with the run that shows it, or as read").
45. A session never loads the listing whole, which is about 1.6 MB; it reads a skeleton, a search or an address range. Why: a session's context fills (claim 10). Source: `CLAUDE.md`, "Session protocol" ("Never load `re/Wings.lst` whole. It is about 1.6 MB").
46. The listing and the inventory are never edited by hand; names go into `re/names.txt`, the disassembler makes the listing again, and a test holds the committed files to what the tools make, byte for byte, so that a stale file fails the suite rather than misleading a reader. Source: `CLAUDE.md`, "Rules"; `tests/test_generated.py`, its docstring ("A committed file that went stale would mislead that reader") and `test_the_listings_are_their_regeneration`.
47. The listing shown: `test_the_listings_are_their_regeneration` from `tests/test_generated.py`, 8 lines (claim 101); the sentence before it points at the two generators run into a directory of their own and the comparison of the three files byte for byte, and the message that says what to do.
48. Points to establish: thirteen questions the listing can answer, each due before the milestone that consumes its answer, so that no milestone is built on a guess; the answer goes into a note. Source: `SPEC.md` 10 (its opening: "Each point is answerable from the listing ... A point is due before the milestone that consumes its answer starts"; the table: 13 rows, counted). The "why" is the chapter's, from the rule.
49. Three of them, what a pass writes and a tick reads, the object system and the map's records, were answered by observing the headless original rather than by reading alone. Source: `SPEC.md` 10, last paragraph ("Points 2, 3 and 5 were answered by observing the headless original rather than by reading alone").
50. Hand-written sources contain code only; tables, texts and tuning values come from the executable at build time. Source: `CLAUDE.md`, "Rules"; `CONTROLLER.md`, "Reviewing a report", step 3. Told in chapters 1 and 3; named here as one of the review's steps.

## 5. The milestones

51. The port was built in milestones, M0 to M9, each ending with a working page and green tests; chapter 8 defined the term. Source: `SPEC.md` 9 ("Each milestone ends with a working `dist/wof.html` and green tests"); the glossary's Milestone entry.
52. The table of the milestones in the order they were done, with what each delivered and what held it (claim 100). Rows and sources:
    - M0: the build, an empty core, the shell's screen, clock, keys and sound; held: the page opens from a file, a test pattern at a steady rate, a tone after a key, no request to the network. `SPEC.md` 9, the table's row M0.
    - M1: the file system, the memory, the loaders and decoders, the font and the tables; held: the first pictures in their colours, text in the game's font, the decoders under the oracle. `SPEC.md` 9, row M1.
    - M2: the headless original, to a mission's first pass; held: a dump after every tick, two runs the same. `SPEC.md` 9, row M2.
    - M3: the front end and the port's keys; held: the original's choices for the same keys, compared VBlank by VBlank. `SPEC.md` 9, row M3; `SPEC.md` 8, row Front end.
    - Points 2, 3, 5 and 13 before M4: what a pass writes and a tick reads, the map, the objects, the floating point; held: observation under the headless original, the floating point against the ROM. `CONTROLLER.md`, "The plan ahead", item 4 ("the open points due before M4 (2, 3, 5 and 13)"); `SPEC.md` 10, rows 2, 3, 5, 13.
    - M4: the world and the player, in two parts; held: a mission flown and ended, compared tick by tick in both loops. `SPEC.md` 9, row M4; `CONTROLLER.md`, "The plan ahead", item 5.
    - M5: the weapons and the ground targets, two parts; held: the same on the first three maps. `SPEC.md` 9, row M5, and its paragraph ("M5 is done in two parts as M4 was").
    - M6: the enemy aircraft and the ships, two parts; held: the same on all fifteen maps. `SPEC.md` 9, row M6, and its paragraph.
    - M8, done before M7: the sound effects and the music player, two parts; held: the sound event logs equal in every loop, the music compared VBlank by VBlank, the owner's ears. `SPEC.md` 9, row M8 and its paragraph; claim 5.
    - M7: the campaign, the saved game and the demo, two parts; held: a whole campaign, the saved file and the demo byte for byte, a replay after a reload. `SPEC.md` 9, row M7 and its paragraph ("by the port's `wofdemo` against the original's byte for byte"; "the saved file against the original's byte for byte but for its four pointer fields").
    - M9: the picture drawn on the graphics card; held: a frame-time test at the screen's size in both browsers, the picture tests on both renderers, the owner's look in full screen. `SPEC.md` 9, row M9.
    - The release groundwork: the page and the game data versioned, the ROM checked in one place, the generated files held to their regeneration, a setup script; held: a fresh clone with and without the ROM, one run of the suite. `SPEC.md` 9, its paragraph ("verified from a fresh clone with and without the ROM and by one two-phase run of the suite").
53. M4 to M8 were each done in two parts, with a review and a merge between them. Source: `CONTROLLER.md`, "The plan ahead" (M4 "as two tasks with a review and a merge between them"; M5 "as two parts with a review and a merge between them, as M4 was"; M6 "part 1 ... part 2"; M8 "as two parts"; M7 "as two parts with a review and a merge between them").
54. The front end came before the missions because it shows progress in the browser early and depends little on the object system, and the owner's look at the running shell found what tests could not. Source: `CONTROLLER.md`, "The plan ahead" ("the front end first, because it shows progress in the browser early, depends little on the object system, and the user's own look at the running shell has found what tests could not").
55. The sound was done before the campaign, so that it was in the page sooner for the owner's test flights; the numbering stayed. Source: `SPEC.md` 9 ("M8 before M7, so that the sound is in the page for the owner's test flights sooner; the numbering stays").
56. M9 was redefined by the owner as the page's drawing on the graphics card, because the frame rate halved at a large full-screen size; what it held before became M10. Source: `CONTROLLER.md`, "The plan ahead" ("M9 redefined by the user ...: M9 is the page's drawing path made fast on the GPU (the frame rate halves at a Retina fullscreen size ...)"); `SPEC.md` 9.
57. Each milestone's cold list named what the later milestones owed, so that the next one's plan was the list of stand-ins its scripts had to reach. Source: `book/docs/part-1/mission.md`, "From one mission to a campaign". Referred to, told in chapter 8.
58. Dropped: M10, the shell's options (key configuration, gamepad, scaling options, the video standard as an option, a title mute, the assist's halves, an export and import of saved games and high scores), when the owner decided that the game was done for now and only bug fixes may come. Source: `SPEC.md` 9 (the table's row M10; "What the plan listed for M9 before is M10, which the owner dropped ...: the game is done for now, and only bug fixes may come").
59. Dropped: the cheat sequence, which the owner decided the port does not need (its letters are commands now, chapter 1). Source: `CONTROLLER.md`, "Open items" ("The cheat sequence: decided by the user ..., the port does not need it"); `book/docs/part-1/faithful.md`, "The keys".
60. Not made: the measurements of the real machine beyond the one film (a busy scene, the fades' speed, the directory's order), because the owner found the port right as it was; the port keeps its settings. Source: `CONTROLLER.md`, "Open items", VBlanks per pass ("Decided by the user ...: no Amiga measurements, everything feels realistic as it is; the busy scene stays unfilmed, the fade speed unmeasured and the directory order unchecked"). Paraphrased; chapter 1 lists the four things that rest on documented behaviour or the owner's eye and ear.
61. Five small changes of the page the owner asked for after playing were tested by the owner in place of the suite, by the owner's rule for them. Source: `SPEC.md` 9 ("five small shell changes the owner asked for after playing were merged, coded and built by a worker and tested by the owner in place of the suite, by the owner's rule for them").

## 6. Two models, and no swarm

62. The controller ran on the stronger and scarcer model, the workers on the cheaper one; the handbook's table names Fable 5.1 for the controller and Opus for the workers (said once). Source: `CONTROLLER.md`, "Models and effort", the table and "The user's Fable budget is limited and the controller needs it"; the commit trailers (`git log main --format=%b | grep -i co-authored-by | sort | uniq -c`: 89 Fable 5.1, 52 Opus 5, 11 Opus 5 with a 1M context, 138 Opus 5.5). The chapter says "Opus" without a version: the table says Opus 5 and later workers' commits carry Opus 5.5 (see "Where a source was wrong or silent").
63. The stronger model is kept for reading no observation can check and for one-off design decisions no test can catch. Source: `CONTROLLER.md`, "Models and effort", the table's last row.
64. The reason: what makes a worker reliable at reading is the task, not the model: a task demands that every finding be backed by the oracle, the headless original or a test, and says which instrument answers which question; the one reading mistake of the early days, the stick's bits, was found by an observation, not by a better reader. Source: `CONTROLLER.md`, "Models and effort" ("What makes Opus reliable at reading is the task, not the model: require that every finding is backed by the oracle, the headless original or a test, and say in the task which instrument answers which question. A reading mistake made earlier in this project (the stick's up and down bits) was found by observation, not by a better reader"); `book/docs/part-1/wrong.md`, "The stick's bits".
65. The owner asked whether workers should fan out into many agents; the assessment was no: the original program, run and compared, is a stronger adversary than a reviewing agent; the clock was not what was scarce; every sub-agent pays again for reading the rules and the notes; and the work is a chain through shared files. Source: `CONTROLLER.md`, "Models and effort", Multi-agent workers.
66. The estimate that settled it: the object system is narrow, not wide: fourteen tables, the code that runs them about 11 KB in eight groups, a record's behaviour a chain of tests inside one routine (`0x010AA6`) rather than a handler per kind, the groups sharing their helpers; nothing to fan out over, so one worker per milestone stayed. Source: `CONTROLLER.md`, "Models and effort" ("The estimate, from the width table of `re/notes/objects.md`"); `re/notes/objects.md` (fourteen tables; `SPEC.md` 10, row 3: "fourteen tables ...; behaviour by a chain of tests on the kind byte and the type word, not a jump table"). The prose gives the fourteen tables and the one routine; the 11 KB and the eight groups may stand in a clause.
67. A fan-out of several reviewers was left for reading that no observation can check, untried. Source: `CONTROLLER.md`, "Models and effort", Multi-agent workers ("Untried; test it on one routine first"). Sheet only, or a clause.

## 7. What it took

68. About twelve days of calendar time from the first commit to the decision that the game was done. Source: `git log --reverse --format='%h %ad' --date=short main | head -1` (`c191167`, the first day) and `43e8f54` ("M10 dropped", the twelfth day, counted inclusive); `re/notes/amiga-to-web.md`, "What is the work of each game" ("Of the twelve days of this project"). Commits fell on ten of the twelve days (`git log --format=%ad --date=short 43e8f54 | sort -u | wc -l`). The prose gives "about twelve days"; no date.
69. Of those days about two fifths went into the instruments, the runtime, the shell and the method, three fifths into the game itself. Source: `re/notes/amiga-to-web.md`, "What is the work of each game"; `README.md`, "Amiga to Web" ("Two fifths of this project built those, three fifths ported the game").
70. Commits on the main branch at the base: 290, of which 197 up to the release groundwork's merge and 73 that touch the book. Source: `git log --oneline main | wc -l`; `git rev-list --count 43e8f54`; `git log --oneline main -- book | wc -l`. The box gives about 290.
71. Every commit carries the owner as its author and the session's model as co-author. Source: `git log main --format='%an' | sort | uniq -c` (290 sy2002); the trailers (claim 62). The chapter: "Every commit is the owner's, with the session's model named beside it". Sheet only unless the draft needs it.
72. Controller sessions to the game's end: eleven; the handbook names the eleventh as leading on the day M10 was dropped, and the controllers count up with each handover. Source: `CONTROLLER.md`, "The plan ahead" ("Controller Instance 11 leads since 09:20 on 2026-09-30"; the same day "The user decided the same evening that the game is done for now and M10 is dropped"); "The user's conventions" ("Controllers are called `Controller Instance N`, counting up with each handover"). Later controllers, for the book, are not counted in the repository (unsourced U2).
73. Worker sessions the handbook names: ten for the game (M2 to M6 one each, M7 two, M8 one, M9 one, and one for the owner's findings between milestones) and nine for the book (one for the site and chapter 1, one for each of chapters 2 to 9). Source: `grep -o 'Worker [A-Za-z0-9 ]*' CONTROLLER.md | sort -u`, nineteen names: Worker M2 headless original, M3 front end, M4 world and player, M5 weapons and targets, M6 enemy aircraft and ships, M7 campaign and saved games, M7 part 2 loader and demo, M8 sound and music, M9 shell polish, test findings; book site, book chapter 2 to book chapter 9. The M2 and M3 names appear in the handbook's examples of the naming ("for example `Worker M2 headless original`"; the start line for "Worker M3 front end"), the other seventeen as sessions that did the work ("The plan ahead"). The workers before M2 are not named in the repository (U3); the box says "the handbook names".
74. The core: 19,436 lines of C in 41 files (35 `.c`, 3 `.h`, 3 `.def`), the generated tables left out. Source: `git ls-files src | xargs wc -l | tail -1`; `git ls-files src | sed 's/.*\.//' | sort | uniq -c`. The box: about 19,400.
75. The shell: 2,404 lines of JavaScript, HTML and CSS. Source: `git ls-files web | xargs wc -l | tail -1`. The box: about 2,400.
76. The tools: 12,373 lines of Python and shell (and 810 lines of library descriptions and lists). Source: `git ls-files 'tools/*.py' 'tools/*.sh' | xargs wc -l | tail -1`; `git ls-files 'tools/*.fd' 'tools/*.txt' | xargs wc -l | tail -1`. The box: about 12,400.
77. The tests: 22,951 lines of Python, JavaScript and C (and 2,188 lines of JSON: run descriptions and replays). Source: `git ls-files 'tests/*.py' 'tests/*.mjs' 'tests/*.c' | xargs wc -l | tail -1`; `git ls-files 'tests/*.json' | xargs wc -l | tail -1`. The box: about 23,000.
78. The notes: 29 files, 196,186 words. Source: `git ls-files 're/notes/*.md' | xargs wc -w | tail -1`; `git ls-files 're/notes/*.md' | wc -l`. The box: 29, about 196,000 words.
79. The specification: 19,676 words; the handbook 12,030; `CLAUDE.md` 926. Source: `wc -w SPEC.md CONTROLLER.md CLAUDE.md`. The box: the specification about 19,700 words.
80. The routines by status: 616 in all; verified 167, ported 155, partial 1, replace 47, drop 31, no status (`todo`) 215; of the 215, 117 lie at the end of the code in the C library and the system's glue, 67 have no caller, 170 are one or both. Source: `re/functions.csv` with a CSV reader (`csv.DictReader`, counted by `status`; `addr` from `0x0215D8`; `callers` 0); `book/docs/part-1/reading.md` (the statuses; "117 ... 67"). The table (claim 102); the prose: "most of those with no status are the C library, the system's glue and code nothing calls (chapter 4)".
81. 445 of the 616 routines carry a name rather than an address. Source: `re/functions.csv`, `name` not beginning with `sub_`, with a CSV reader.
82. Tests collected: 930, with `--slow`, at the base; 807 emulator tests and 123 page tests by the testing note's split at `698d0f8`, the same total. Source: `.venv/bin/python -m pytest --collect-only -q --slow tests/` ("930 tests collected"); `re/notes/testing.md`, opening. The box: about 930.
83. A full run of the suite: about an hour over the cores, then about twenty minutes of page tests alone; serially about three hours. Source: `CLAUDE.md`, "Commands" ("phase 1 ... (about an hour)"; "phase 2 ... (about twenty minutes)"); `re/notes/testing.md`, "Times, and how many workers" (the serial reference 3:00:14). The box: about an hour and twenty minutes, in two phases.
84. What the work cost in money and in tokens is not in the repository; the chapter says nothing of it (U1).

## 8. What the arrangement learned the hard way

85. An expired login stops every session without a report: before an unattended night the controller looks at the login banner and asks the owner to renew it. Source: `CONTROLLER.md`, "Pitfalls that cost time".
86. The machine sleeps when left alone, and a sleep stops every session; once it cost an hour in the middle of a milestone; a command that keeps it awake runs before an unattended run, and a test that ran across a sleep is void. Source: `CONTROLLER.md`, "Pitfalls that cost time" ("on 2026-09-20 it cost an hour in the middle of M3"; `caffeinate`). The prose: "an hour in the middle of a milestone".
87. A usage limit stops every session in the middle of a turn and only the controller resumes; one-shot checks about every fifty minutes, a resume message to a worker found idle ("git status first, an interrupted test run is void, carry on"), the same clause in every task with the demand to commit whatever is green. Source: `CONTROLLER.md`, "Pitfalls that cost time". The prose paraphrases the resume message, no quote.
88. An idle notice fires at every pause between a worker's turns: subscribe once with the task; the report arrives as a message. Source: `CONTROLLER.md`, "Pitfalls that cost time"; "Driving workers".
89. The shared directory: a file the controller creates beside a worker's branch can be swept into its commits (claim 23). Source: `CONTROLLER.md`, "Driving workers".
90. A controller's test run that overlapped a worker's rebuild compared an old native library with a new core, four failures none reproducible: a run is stopped before a follow-up that will build is sent. Source: `CONTROLLER.md`, "Pitfalls that cost time" ("A controller's own test run must not overlap a worker's rebuild ... (four failures on one xdist worker ..., none reproducible)").
91. The parallel suite's verification took five full runs where one would have done and cost an afternoon: an infrastructure change gets one verification run, the owner's rule. Source: `CONTROLLER.md`, "The plan ahead" ("Its verification, five full runs where one would have done, cost the afternoon ...: an infrastructure change gets one verification run, the user's rule of that day").
92. A session's name on the command line without quotes takes only the first word. Source: `CONTROLLER.md`, "Pitfalls that cost time". Sheet only.

## 9. An honest account

93. What the sessions did in the time: every routine the game runs read and rewritten (chapter 1), 445 routines named, 29 notes of about 196,000 words, about 23,000 lines of tests, in about twelve days; more reading and writing than one person does in that time (the chapter's own assessment, from the counts). Source: claims 68, 74 to 82; `book/docs/part-1/faithful.md` ("Every routine the game runs was read, named and rewritten in C").
94. What they got wrong is chapter 9: readings, an instrument, the tests; in all but one an instrument, or a reading of what the code really calls, decided against the belief; some mistakes were the owner's eyes, ears and keyboard to find. Source: `book/docs/part-1/wrong.md`, "The rest of the record" and "What comes next".
95. Mistakes of the arrangement itself are in the handbook's pitfalls, kept as warnings for the next session. Source: `CONTROLLER.md`, "Pitfalls that cost time"; `book/docs/part-1/wrong.md`, further reading ("the record of the mistakes, kept as warnings").
96. What the owner did that no session could: the decisions, the eye and the ear, the real Amiga and its film, the play that found what tests could not. Source: claims 4 to 8, 54; `re/notes/amiga-to-web.md`, "What "start" can mean" ("The controller needs the owner at three points that no session replaces: the decisions ..., the look and the listen ..., and the budget").
97. What that makes the port: a record that can be checked rather than trusted: the source, the notes, the tests and the history are in the repository, proven against the original in a way one can read and repeat. Source: `README.md`, "Amiga to Web" ("proving the result against the original in a way one can read and repeat"; "leaves the game readable, as source, notes and proof, to whoever comes after"). The phrase "checked rather than trusted" is the chapter's.
98. What may follow: the owner's idea, written down and not started, of a template repository, "Amiga to Web", to do the same for other Amiga games built as this one is; proven only when a second game goes through it. Source: `README.md`, "Amiga to Web" ("Hence the idea, not started yet, of a template repository"); `re/notes/amiga-to-web.md` (opening: "a plan for a possible future project, not a description of anything that exists"; "The shape it could take": "A template is proven only when a second game goes through it"). Named, not promised.

## 10. The same method for this book

99. The book is made the same way: per chapter a fact sheet with every claim and its source, a draft from it with its figures and listings generated and the site's build green, a fact-check by a second worker that had no part in the draft, a readability read by a fresh session given only the chapter and the glossary, the controller's read, the owner's read as the final gate; the fact-checks and the readability reads are fresh sessions that edit nothing; the controller is the editor and alone the owner's contact; the chronicle, outside the repository, is the writers' private source for the order of events, and every claim is sourced in the repository. Source: `book/BOOK.md` 6; `book/BOOK.md` 4, point 2 (every number has its source). At every chapter's merge so far, something in the notes or the specification was corrected. Source: `CONTROLLER.md`, "The plan ahead" (chapters 1 to 9: each merge's "Fixed at the merge" or "Found on the way and fixed at the merge"). Said in one paragraph, not as a diary.

## What comes next and further reading

100. What it hands to Part II: the game inside, now that the reader knows how the knowledge was made and held. Source: `book/BOOK.md` 3 (Part II).
101. Further reading: `CONTROLLER.md` ("The arrangement", "What a task contains", "Reviewing a report", "Models and effort", "The plan ahead", "Pitfalls that cost time"); `CLAUDE.md` ("Session protocol", "Rules"); `SPEC.md` 7.4, 9 and 10; `book/BOOK.md` 6; `README.md`, "Amiga to Web"; `re/notes/amiga-to-web.md`; `re/notes/testing.md`, "Times, and how many workers". Outside: Wikipedia, "Code review".

## Left to the preface and to Part III

- The preface: who we were, in a few lines (`book/BOOK.md` 3, front matter: "who did what: the owner and the AI sessions, in the open"); this chapter tells the arrangement in full and the preface may point here.
- Part III: the tools and the build (chapters 21, 24, 25): the repository's tour, the suite's layers and phases, building it; this chapter names the suite's time and size only.

## The chapter references the prose makes, each checked against `book/BOOK.md` 3

| Reference | What the chapter says is there | `book/BOOK.md` 3 |
|---|---|---|
| chapter 1 | what faithful means; what was changed on purpose; the cheat sequence | 1, What faithful means |
| chapter 4 | the statuses; the listing | 4, Reading the executable |
| chapter 5 | the oracle | 5, The oracle |
| chapter 6 | the headless original | 6, The headless original |
| chapter 7 | the film, the VBlanks a pass | 7, Time |
| chapter 8 | the milestones, the reach map, the stand-ins, the check by another hand | 8, Porting a mission |
| chapter 9 | the mistakes and what caught them | 9, What went wrong |
| chapter 24 | the suite | 24, The tests |
| Part II | the game inside | 11 to 20 |

## Counts and where they were counted

| Count | Value | Command, at `f8b5fd9` |
|---|---|---|
| commits on main | 290 | `git log --oneline main \| wc -l` |
| commits to the game's end | 197 | `git rev-list --count 43e8f54` |
| commits touching the book | 73 | `git log --oneline main -- book \| wc -l` |
| days with commits | 12, from the first commit to the base; 10 to `43e8f54` | `git log --format=%ad --date=short main \| sort -u` |
| calendar days, first commit to the game done | 12, inclusive | `c191167` and `43e8f54` by `git log --date=short` |
| commit authors | 290 sy2002 | `git log main --format='%an' \| sort \| uniq -c` |
| co-author trailers | 89 Fable 5.1, 52 Opus 5, 11 Opus 5 (1M context), 138 Opus 5.5 | `git log main --format=%b \| grep -i co-authored-by \| sort \| uniq -c` |
| `src/` | 19,436 lines, 41 files | `git ls-files src \| xargs wc -l \| tail -1` |
| `web/` | 2,404 lines | `git ls-files web \| xargs wc -l \| tail -1` |
| `tools/` | 12,373 lines of `.py` and `.sh`; 810 of `.fd` and `.txt` | `git ls-files 'tools/*.py' 'tools/*.sh' \| xargs wc -l` |
| `tests/` | 22,951 lines of `.py`, `.mjs`, `.c`; 2,188 of `.json` | `git ls-files 'tests/*.py' 'tests/*.mjs' 'tests/*.c' \| xargs wc -l` |
| `re/notes/` | 29 notes, 196,186 words | `git ls-files 're/notes/*.md' \| xargs wc -w \| tail -1` |
| `SPEC.md`, `CONTROLLER.md`, `CLAUDE.md` | 19,676, 12,030, 926 words | `wc -w` |
| routines by status | verified 167, ported 155, partial 1, replace 47, drop 31, todo 215; 616 | `re/functions.csv`, `csv.DictReader`, by `status` |
| `todo` in detail | 117 from `0x0215D8` on; 67 without a caller; 170 either | the same, by `addr` and `callers` |
| named routines | 445 of 616 | the same, `name` not `sub_` |
| tests collected | 930 | `.venv/bin/python -m pytest --collect-only -q --slow tests/` |
| the suite's phases | about an hour, about twenty minutes; serially about three hours | `CLAUDE.md`, "Commands"; `re/notes/testing.md`, "Times, and how many workers" |
| controller instances to the game's end | 11 | `grep -o "Controller Instance [0-9]*" CONTROLLER.md \| sort -u` (6 to 11 named; 11 leads on the day M10 was dropped; counted up with each handover) |
| workers the handbook names | 10 for the game, 9 for the book | `grep -o 'Worker [A-Za-z0-9 ]*' CONTROLLER.md \| sort -u` (claim 73) |
| a task's parts | 10 | `CONTROLLER.md`, "What a task contains", counted |
| a review's steps | 7 | `CONTROLLER.md`, "Reviewing a report", counted |
| the method's steps | 6 | `SPEC.md` 7.4, counted |
| the points to establish | 13 | `SPEC.md` 10, the table's rows, counted |

## Figures

- `arrangement.svg` (new, drawn by hand under `book/docs/figures/`, its colours commented with their palette entries and held by the build's colour check): the owner at one chat, two-way with the controller (asks with a recommendation; decisions, findings, eyes and ears); the controller sending a task to one worker that has its branch checked out and receiving its report; two workers beside it, idle, opened in advance; below, the repository in one working directory, the main branch and the one task branch out, the worker committing on its branch and the controller merging after its review and rebuilding the page; on the left, an earlier controller handing over to the controller at a quiet point, through the repository and a message. No count: the idle workers are an example, the caption says so. Colours: the owner `#FFBB00` (wingstitle 25), the controller `#77AACC` (wingspalette 22), the working worker `#44AA44` (iff-dash 6), the idle sessions' frames `#888899` (wingspalette 28), the repository `#CCCCDD` (wingspalette 30), the ink `#111122` (wingspalette 6), the labels `#EEEEEE` (wingstitle 31), the muted labels `#AAAABB` (wingspalette 29), the wires `#CCCCDD` and `#FFBB00`. Claims 11 to 17, 20, 23 to 25, 27.
- No figure rendered from the game's data: the chapter is about the work, not the game.

## Tables

- 100. The milestones in the order they were done, with what each delivered and what held it: claim 52.
- 102. The routines by status: claim 80.

## Listings

- 101. `test_the_listings_are_their_regeneration` of `tests/test_generated.py` (kind `py`, `file`): claims 46, 47. A rule of `CLAUDE.md` written as a test.

## Terms and glossary entries

Introduced in chapter 10, in bold with an entry, each "First met and defined in chapter 10":

- Session (claim 10): one conversation with an AI coding assistant, in a terminal in the repository, which reads files, runs commands and commits; its context fills, and it is then replaced by a fresh one. The detail: `CLAUDE.md`, "Session protocol"; `CONTROLLER.md`, "The arrangement".
- Controller (claim 11): the session that leads: the owner talks to it alone; it assigns the tasks, reviews and merges, keeps the specification and the rules true and is the only session that asks the owner anything. The detail: `CONTROLLER.md`, "The arrangement".
- Worker (claim 12): a session that does one task the controller sends it, a milestone or a bounded part of one, on its own branch, and reports to the controller only. The detail: `CLAUDE.md`, "Session protocol"; `CONTROLLER.md`, "What a task contains".
- Handover (claim 15): the lead passed from a controller whose context is filling to a fresh session, at a quiet point, through the repository and a message. The detail: `CONTROLLER.md`, "The arrangement"; `CLAUDE.md`, "Session protocol".
- Review (claim 36): the controller's check of a worker's report before a merge, ending in one check of the reviewer's own that the worker's tests could not make. The detail: `CONTROLLER.md`, "Reviewing a report". Elsewhere: Wikipedia, "Code review".

Milestone (chapter 8) is linked, not redefined. Linked at their first use, not redefined: faithful port, listing, routine, oracle, headless original, closed loop, stand-in, verified, control-flow skeleton, pure routine, routine inventory, milestone, front end, mission script, sound sample. Glossed in words without an entry: a brief (the controller's short account to the owner), the asynchronous mode, a task, a report, the cold list (chapter 8), the fact sheet (the book's method, `book/BOOK.md` 6).

## Figures box

"The figures", in section 7: the days to the game's end, the commits, the controller sessions to the game's end, the workers the handbook names, the lines of the core, the shell, the tools and the tests, the tests collected, a full run of the suite, the notes and their words, the specification's words. Counts that grow are rounded (claims 68 to 83).

## Sidebars

- For the developer: where the arrangement lives: `CONTROLLER.md` (the handbook, its task and review lists), `CLAUDE.md` (what every session reads first), `SPEC.md` 7.4 and 9, `book/BOOK.md` 6; the generated files' test, `tests/test_generated.py`; the commit trailers name each session's model (`git log`). Source: the files.

No "How we know" box and no "What went wrong" box.

## Left to later chapters

The suite's layers, phases and isolation (24); the tools and the build (21, 25); the porting rules as a whole (22).

## Where a source was wrong or silent

- `CONTROLLER.md`, "Models and effort", names the workers' model as Opus 5; the commits of the later workers carry Opus 5.5 as co-author (138 trailers), and 11 an Opus 5 with a larger context. The chapter says "Opus" without a version.
- `CONTROLLER.md` names the M2 and M3 workers only in its examples of the naming, not in the plan; the chapter counts them, as the names the handbook gives.
- The repository does not count the controller sessions after the eleventh (the book's controllers) nor name the workers before M2 (M0, M1, the early points, the display's aspect); the chapter counts only what the handbook names.
- `re/notes/testing.md` gives the two phases as "about an hour in all", measured at 827 tests; `CLAUDE.md`'s commands give about an hour and about twenty minutes for the larger suite since. The chapter follows `CLAUDE.md`.
- `book/BOOK.md` 3, chapter 21, lists "the chronicle" in the tour of the repository; the chronicle left the tree (`CONTROLLER.md`, "The user's conventions", Times). Proposed for `book/BOOK.md` in the report.

## Unsourced

- U1. What the port cost in money and in tokens: not in the repository; out of the chapter.
- U2. The number of controller sessions over the whole project, the book's included: the repository names none after the eleventh.
- U3. The sessions before M2 (the build's, the loaders', the early readings') and their number: the chronicle names them, the repository does not.
- U4. How the arrangement began (that the owner proposed it in the first session): the chronicle only. The chapter says the owner set the arrangement up, as the handbook's task list says (`CONTROLLER.md`, "What a task contains", item 2: "That the user set this up") and as "The arrangement" describes (the owner opens every session).
- U5. The stories behind the rules (a worker that asked the owner in its own chat; a controller that forbade visible windows): the chronicle only. The chapter gives each rule's need from the handbook's own reasons, not the story.
