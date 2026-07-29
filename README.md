## 1. How to run it
 
**One-time setup:**
 
1. Install [PsychoPy](https://www.psychopy.org/download.html) (the Standalone
   version is easiest — no need to separately install Python packages).
2. Download or clone this repo, and make sure `pvt_clock_task.py` is on your
   computer somewhere you can find it.
**Running a session:**
 
1. Open PsychoPy, and use its "Coder" view (not "Builder") — this script is
   a plain Python file, not a `.psyexp` file.
2. Open `pvt_clock_task.py` in the Coder view and press the green "Run"
   arrow (or run `python pvt_clock_task.py` from a terminal if you have
   PsychoPy's Python on your PATH).
3. A small dialog box will pop up asking for a Participant ID and session
   number — fill these in and click OK.
4. A full-screen instructions window appears. Click the mouse to begin the
   5 practice trials.
5. After practice, the real task begins: 4 blocks of 20 trials each. Between
   blocks, a pause screen tells you (the experimenter) whether that block
   should have music playing or not — start/stop the track manually, then
   click the mouse to continue.
6. When all 4 blocks finish, a thank-you screen appears briefly and the
   window closes automatically.
**Where the data goes:**
 
A `data` folder is created automatically next to the script (if it doesn't
already exist), and a file named `<ParticipantID>_pvt_clock.csv` is saved
there with one row per trial and one row per thought probe, including block
number, whether that block had distraction, trial number, wait time,
reaction time, and (for thought probes) which option was chosen.
 
**If something looks wrong:** press `Esc` at any point — PsychoPy windows
close if you Alt-Tab or hit Esc during most stages, so if the task looks
frozen, that's usually the first thing to try (note this will end the
session, so only do it if genuinely stuck).

## 2. Where the design came from, and what I checked first
 
Before writing anything, I looked for existing code rather than starting
from a blank page, per the plan to reuse work where possible:
 
- **The source paper itself** (Kiss & Linnell, 2021, *Psychological
  Research*) — this is where the exact task parameters come from: 2s
  fixation, 2–10s random wait in 500ms steps, 1s feedback, 500ms blank
  screen, and the three-category thought-probe wording. The paper's
  Acknowledgements mention that Nash Unsworth shared his own PVT code with
  the authors — but that was a private exchange, not something posted
  publicly, so there's no repo of his to draw from.
- **[marsja/psychomotor_vigilance_task](https://github.com/marsja/psychomotor_vigilance_task)**
  — a public PsychoPy PVT built from a tutorial. Closest existing match in
  terms of platform (PsychoPy) and task family, but it uses the standard
  digital-counter version, not a clock, and has no thought-probe system —
  so it was useful as a sanity check on PsychoPy conventions, not as
  something to adapt directly.
- **[a-hurst/PVT](https://github.com/a-hurst/PVT)** — a Dinges & Powell
  (1985) PVT implementation, but built in KLibs (a different framework
  entirely), so only useful for cross-checking trial-timing logic, not
  usable as a base.
Given the clock hand and thought-probe pieces are specific to our design and
weren't in either existing script, I built the trial logic from Claude
against the paper's methods section, rather than trying to bolt those
features onto someone else's codebase.

## 3. Decisions made while building it
 
- **Config values are all at the top of the file.** Trial counts, timings,
  the thought-probe count, etc. are collected as named settings near the top
  of `pvt_clock_task.py`, so you can tune the task without touching the
  trial logic underneath.
- **One open question left as a setting, not a hardcoded choice:** the
  planning notes give two different numbers for thought probes per block —
  3 in one place, 6 in another (6 matches the original paper). Rather than
  guessing, this is left as a single `THOUGHT_PROBES_PER_BLOCK` variable —
  whoever finalizes this can just change that one number.
- **Comments are written in plain English throughout**, explaining *why* a
  step happens, not just *what* the line of code does — so it can be handed
  to a supervisor or a collaborator without deep Python experience and still
  make sense.
- **Block order (distraction vs. silence) is a plain list you can reorder**,
  so counterbalancing across participants is a one-line change rather than
  a code rewrite.
- **Data is saved incrementally to CSV**, one row per trial or per thought
  probe, so a crash partway through a session doesn't lose everything
  before it.

## 4. What's *not* yet handled (worth deciding as a team before real data collection)
 
- False starts (clicking before the clock hand moves) are detected but not
  currently logged — there's a placeholder comment where that would go.
- The script doesn't control the music itself — during the pause screen
  between blocks, it waits for a mouse click, giving the experimenter a
  moment to manually start or stop the track.
- Trials where the participant never clicks within 5 seconds are capped and
  recorded as a blank reaction time — whether these should be flagged
  differently in analysis is an open question.
 
