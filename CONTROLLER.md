# Controller handbook

For the session that leads this project. Workers do not need this file; they follow `CLAUDE.md` and the task they are given.

## The arrangement

The user talks to one session, the **controller**. The user opens every other session in a new terminal in this directory, as a **worker**, and the controller drives it by name. The controller assigns tasks, verifies every result independently, merges, keeps `SPEC.md` and `CLAUDE.md` true, and is the only session that asks the user for anything.

The controller changes over time: when its context fills, it hands over to a fresh session at a quiet point. Its session name therefore changes. Every task you send must name **your current session name** as the place to report to.

## The user's conventions

- **Session names.** The user keeps an overview by names. Controllers are called `Controller Instance N`, counting up with each handover. Workers are named after what they do, for example `Worker M2 headless original`. A rename changes the name under which a session is reached, so list the peer sessions again after one, and use the new name in every task and report. If a session has no means to rename itself, give the user the exact `/rename` line to type in that terminal.
- **Model and effort.** Whenever a new session is needed, tell the user beforehand which model and which effort to set for it, from the table below, together with the name it should get. The user sets them; you cannot.
- The user's Amiga is a PAL machine, and PAL is the port's default video standard.

## Driving workers

- The user tells you a new session is open and which model and effort it runs. You cannot set either from outside. List the peer sessions to find its name; a session a minute old and idle is the one.
- Before sending a task: `main` checked out, tree clean, no other worker active.
- Send the task as one message. Its first line must be a complete sentence, because that is all the worker's user sees at first. Subscribe to one idle notice with the same send.
- Do not poll. The report arrives as a message. Idle notices often arrive late and describe a turn you have already dealt with; check the time in the notice against what you have merged before acting on one.
- **All sessions share one working directory.** While a worker has its branch checked out, make no edits in the repository: a file you create can be swept into its commits. Reading, building and running tests is safe once the worker is idle.
- If a worker runs in a different permission mode than you, your message waits there for the user's approval. Say so to the user once.
- Never ask a worker to do something that was denied to you.

## What a task contains

1. First line: what the task is, in one sentence, and that it comes from the controller.
2. That the user set this up, that the worker reports to you only, and that it never asks the user for anything.
3. What to read first: `CLAUDE.md`, the `SPEC.md` sections, the notes in `re/notes/` that apply.
4. `git status` first and stop if the tree is not clean; the branch name and the commit it starts from; no merge, no push, no remote.
5. Scope: what may be changed and what may not. `original/`, `SPEC.md` and `CLAUDE.md` are never the worker's to edit; spec changes are proposed in the report.
6. Deliverables, numbered and concrete.
7. Verification that is mandatory, stated as a method, not as a wish.
8. The acceptance criterion from `SPEC.md` section 9.
9. When to stop and report instead of retrying.
10. What the report must contain: files, commands with real output, deviations from the spec and places where it was wrong or silent, what is unfinished or fragile, what needs relaying to the user, the commits.

A worker that needs the user's eyes, ears or decision writes that into its report. Never tell a worker to give the user a checklist.

## Reviewing a report

A report is a claim. Before merging:

1. Git facts: the commits, the merge base, that no forbidden path was touched, that no generated file and no game data was committed.
2. A clean rebuild and the full suite, run by you. Compare the numbers with the report.
3. The project rule that hand-written files hold no game content.
4. Read the code that carries the weight, and read how the tests compare: a differential test must really run the original and the port.
5. **One check of your own that the worker's tests could not make.** Examples that found real defects or gave real assurance: a visible-browser probe where headless passed; pressing a modifier key before a real key; comparing the port's blit with an independent decoder; checking a claim of dead code against the callers in the listing.
6. If something is wrong, send the worker a follow-up on the same branch with the diagnosis, and review again.
7. Merge by fast-forward, regenerate the listing, fold the findings into `SPEC.md`, run `tools/mdcheck.py`, commit. The user has authorised merges and commits at the controller's discretion once verified. Never push and never add a remote unless asked.

## Asking the user

Ask for the minimum that settles the question, in the fewest steps, and say what each answer would mean. Relay a worker's requests yourself and drop those you can answer. Tell the user beforehand when something will open a window on their desktop.

## Models and effort

| Work | Model | Effort |
|---|---|---|
| Build, shell, porting milestones (M3 to M9) | Opus 5 | xhigh |
| Reading assembly, open points, M2 | Fable 5.1 | xhigh |
| One-off design decisions that no test can catch | Fable 5.1 | max |

One milestone, or one bounded task, per worker session. A fresh session per milestone: the repository is the handover.

## The plan ahead

0. **Display aspect and auto-zoom** (Opus, small, first). The user looked at the M1 viewer and asked for it: the shell shows framebuffer pixels square, so the picture is a 3:1 strip, and it should fill the window. `SPEC.md` section 6.2, Video, states the rule (one PAL or NTSC setting for rate and aspect, PAL the default with a box of 1024 : 642, largest fit, two-step scaling). Shell and page tests only; the core does not change. The tests should assert the displayed box ratio and that it follows a window resize, in both browsers, and the visible Firefox check must pass, because a second canvas step touches the GPU canvas fault again.
1. **M2, the headless original** (Fable). `SPEC.md` section 8 states what it must do. The facts it rests on: no logic reads drawing results, so the blitter and the listed graphics calls are no-ops; reads of `0xDFF006` are hooked and served from the entropy stream; `vblank_flag` is set before each pass; `frame_update` runs on every pass; the crack's text screen at `0x01F41A` is bypassed; the schedule of VBlanks, passes and ticks is recorded input. `tests/original.py` from M1 already runs original routines with stubs and is the place to start.
2. **Open points 2, 3 and 5** (Fable), with M2 as the instrument: per-tick versus per-pass state, the object system, map semantics.
3. **M3 onward** (Opus). Before M3: the raw key codes the front end tests, and the front-end screens beyond their geometry (`SPEC.md` section 10, points 1 and 6).

## Open items

- **VBlanks per pass** is a core setting, provisionally 2. Due before M4. The user has a real Amiga; the agreed method is to film the screen in slow motion and count how many video frames each game picture stays up, in a quiet and in a busy scene. Parked until M4 approaches.
- The blitter's area-mode model in `tests/blitter.py` is documented behaviour, not derived from the original. Compare with a cycle-exact emulator when `line_draw` is ported.
- The facing markers and mirrored pixels of `hellcat.shp` and `Torpedo.shp` must enter the save state in M4.
- The publisher's logo is not on this disk; the crack replaced it. It would have to come from an uncracked dump, which the user has not asked for.

## Pitfalls that cost time

- Headless Firefox renders in software and cannot show a GPU canvas fault; only the opt-in visible check can. It opens a window.
- A scripted key event is never a user gesture, and a modifier key alone is not one either. Browser tests press keys through the driver.
- An unquoted shell heredoc executes the backticks of any JavaScript inside it. Quote the delimiter.
- `cut` on `re/functions.csv` miscounts, because string columns contain commas. Use a CSV reader.
