# Controller handbook

For the session that leads this project. Workers do not need this file; they follow `CLAUDE.md` and the task they are given.

## The arrangement

The user talks to one session, the **controller**. The user opens every other session in a new terminal in this directory, as a **worker**, and the controller drives it by name. The controller assigns tasks, verifies every result independently, merges, keeps `SPEC.md` and `CLAUDE.md` true, and is the only session that asks the user for anything.

The controller changes over time: when its context fills, it hands over to a fresh session at a quiet point. Its session name therefore changes. Every task you send must name **your current session name** as the place to report to.

## The user's conventions

- **Session names.** The user keeps an overview by names. Controllers are called `Controller Instance N`, counting up with each handover. Workers are named after what they do, for example `Worker M2 headless original`. A rename changes the name under which a session is reached, so list the peer sessions again after one, and use the new name in every task and report. If a session has no means to rename itself, give the user the exact `/rename` line to type in that terminal.
- **Model and effort.** Whenever a new session is needed, tell the user beforehand which model and which effort to set for it, from the table below, together with the name it should get. The user sets them; you cannot.
- The user's Amiga is a PAL machine, and PAL is the port's default video standard.
- The user is often away for hours and cannot read a long chat afterwards. When they return, lead with where things stand in a few lines, then what is needed from them.
- The game's manual is `original/manual.txt`; the user put it there as a reference.

## Driving workers

- The user tells you a new session is open and which model and effort it runs. You cannot set either from outside. List the peer sessions to find its name; a session a minute old and idle is the one.
- Before sending a task: `main` checked out, tree clean, no other worker active.
- Send the task as one message. Its first line must be a complete sentence, because that is all the worker's user sees at first. Subscribe to one idle notice with the same send.
- Do not poll. The report arrives as a message. Idle notices often arrive late and describe a turn you have already dealt with; check the time in the notice against what you have merged before acting on one.
- **All sessions share one working directory.** While a worker has its branch checked out, make no edits in the repository: a file you create can be swept into its commits. Reading, building and running tests is safe once the worker is idle.
- If a worker runs in a different permission mode than you, your message waits there for the user's approval. Say so to the user once.
- `dist/wof-look.html` is the user's copy of the last verified build. Refresh it from `dist/wof.html` after each merge that changes the page, point the user at it and never at `dist/wof.html`, which a worker's rebuilds and negative controls overwrite, and tell workers not to write to it.
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
5. **One check of your own that the worker's tests could not make.** Examples that found real defects or gave real assurance: a visible-browser probe where headless passed; pressing a modifier key before a real key; comparing the port's blit with an independent decoder; checking a claim of dead code against the callers in the listing; comparing every framebuffer pixel with a driver screenshot, and fitting the picture's real position from its colour edges, where the tests sampled flat areas.
6. If something is wrong, send the worker a follow-up on the same branch with the diagnosis, and review again.
7. Merge by fast-forward, regenerate the listing, fold the findings into `SPEC.md`, run `tools/mdcheck.py`, commit. The user has authorised merges and commits at the controller's discretion once verified. Never push and never add a remote unless asked.

## Asking the user

Ask for the minimum that settles the question, in the fewest steps, and say what each answer would mean. Relay a worker's requests yourself and drop those you can answer. Tell the user beforehand when something will open a window on their desktop.

## Models and effort

| Work | Model | Effort |
|---|---|---|
| The controller | Fable 5.1 | xhigh |
| Build, shell, porting milestones (M3 to M9) | Opus 5 | xhigh |
| Reading assembly and open points, where every finding can be backed by an observation | Opus 5 | xhigh |
| Reading that no observation can check, and one-off design decisions that no test can catch | Fable 5.1 | xhigh, max for a one-off decision |

**The user's Fable budget is limited and the controller needs it.** Workers therefore run on Opus 5 unless a task truly cannot be checked by observation. What makes Opus reliable at reading is the task, not the model: require that every finding is backed by the oracle, the headless original or a test, and say in the task which instrument answers which question. A reading mistake made earlier in this project (the stick's up and down bits) was found by observation, not by a better reader. The controller's own context costs budget on every turn, so hand over early, at a quiet point, rather than late.

One milestone, or one bounded task, per worker session. A fresh session per milestone: the repository is the handover. Give the user the start line with the name in quotes, for example `claude --model opus --effort xhigh --name "Worker M3 front end"`.

## The plan ahead

M0, M1 and M2 are done and merged, and so are the display aspect and auto-zoom the user asked for after M1. The headless original (`tools/headless.py`, `re/notes/headless.md`) runs the original from `main` through the front end into a mission, reproducibly, and is the instrument for what follows.

The user chose the order on 2026-09-20: the front end first, because it shows progress in the browser early, depends little on the object system, and the user's own look at the running shell has found what tests could not. The reading for the flight milestone follows. `SPEC.md` needs no change for this; its milestones were in this order already.

1. **M3 prerequisites** (Opus, reading backed by observation): `SPEC.md` section 10, points 1, 6 and 12 as far as M3 needs them.
   - The key commands. The manual's last page lists them. Establish from the code which routine reads which raw key code and qualifier in which state (the key-buffer readers from `0x0207DA` upward, `key_qualifier_mask`, `menu_input`), and check each under the headless original by delivering the key and watching the state.
   - The front-end screens beyond their geometry: which files each screen loads, pens and draw modes, the texts drawn, transitions and timings in VBlanks, observed through the harness's file log and schedule. The real duration of the fades is CPU-bound in the original and stays open.
   - The high-score file layout, by running the original's own reader and writer under the oracle on the disk's `highscore` file.
   - The harness gains `ExNext` and a directory `Lock` for the load and save dialog.
   - Deliverables: notes, names, the harness extensions with tests, and a proposal for the browser's keys.
2. **The keys decision** (controller with the user, before M3 starts): which keys replace the Control commands, which a browser keeps for itself. The user flies with the vertical flip on, so that option comes early and is remembered.
3. **M3, the front end** (Opus).
4. **Open points 2, 3 and 5, and point 13** (Opus where the change report, the oracle or the ROM decide; Fable only for a part that turns out to be pure reading). Before M4.
5. **M4 onward** (Opus).

## Open items

- **VBlanks per pass** is a core setting, provisionally 2. Due before M4. The user has a real Amiga; the agreed method is to film the screen in slow motion and count how many video frames each game picture stays up, in a quiet and in a busy scene. Parked until M4 approaches.
- The blitter's area-mode model in `tests/blitter.py` is documented behaviour, not derived from the original. Compare with a cycle-exact emulator when `line_draw` is ported.
- The facing markers and mirrored pixels of `hellcat.shp` and `Torpedo.shp` must enter the save state in M4.
- The publisher's logo is not on this disk; the crack replaced it. It would have to come from an uncracked dump, which the user has not asked for.
- Under the headless original the audio interrupt never comes and the music player is not run, so the sound engine never sees a channel end. The sound event log of `SPEC.md` section 8 needs a channel-end model, in M8.
- The headless original's bump allocator has 8 MB and never reuses memory; a mission takes about 370 KB. A whole campaign in one run would exhaust it.
- By default the stick pushed forward climbs: established from the hardware decode and the harness, stated in the manual's take-off instructions, and confirmed by the user on the real Amiga. The user prefers the flipped, pilot's sense (Control-F in the original) and will play with it.

## Pitfalls that cost time

- Headless Firefox renders in software and cannot show a GPU canvas fault; only the opt-in visible check can. It opens a window.
- A `devicePixelRatio` emulated through the DevTools protocol is not a Retina display: Chrome then places a canvas on whole CSS pixels, so a box edge on half a CSS pixel shows the picture shifted by a device pixel or resampled. `--force-device-scale-factor=2` on Chrome's command line behaves like the real thing. A test that samples only flat areas of the picture sees neither.
- The user works on this machine while tests run. Browsers in tests stay silent (`--mute-audio`, the Firefox preference `media.volume_scale`), and a visible window is announced beforehand.
- The page tests are sensitive to load from outside: clock rates, audio start and screenshots failed seven tests once while a browser of the user's own was using more than a core. Run the suite again on a quieter machine before believing such a failure, and do not run an emulator beside the page tests.
- A Claude Code login that expires stops every session without a report. Before an unattended night, look at the login banner in a terminal and ask the user to renew it if it expires within the day.
- An unquoted `--name` on the `claude` command line takes only the first word; the rest becomes the opening prompt. Give the user the line with quotes, or the `/rename` line.
- A scripted key event is never a user gesture, and a modifier key alone is not one either. Browser tests press keys through the driver.
- An unquoted shell heredoc executes the backticks of any JavaScript inside it. Quote the delimiter.
- `cut` on `re/functions.csv` miscounts, because string columns contain commas. Use a CSV reader.
- A comment-only edit in `src/core.c` that added a line made `core.wasm` one byte larger; the cause is not established. When a review relies on the binary being the same size as before, rebuild and look, even after touching only comments.
