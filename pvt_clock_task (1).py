"""
PVT CLOCK TASK - starter script
================================

WHAT THIS SCRIPT DOES (plain English):
This runs a "psychomotor vigilance task" (PVT) using a clock instead of the
usual digital counter. Here's the flow for ONE trial:

    1. A "+" fixation cross shows (currently 2 seconds - flagged by the team
       as possibly too long; see the FIXATION_DURATION note below).
    2. A clock face appears with the hand pointing straight up (12 o'clock).
       Nothing moves for a random amount of time - this is what makes the
       task unpredictable. The team agreed the original 2-10s range should
       be shortened; see the MIN_DELAY/MAX_DELAY note below for where that
       stands.
    3. The clock hand starts sweeping clockwise. The participant must click
       the LEFT mouse button as fast as possible once they see it move.
       If they click before the hand moves, that's logged as a false start
       (see the false_start_count field in the saved data).
    4. The clock freezes on screen for 1 second (this is "feedback" - it
       lets them see where they stopped it).
    5. A blank grey screen shows for 0.5 seconds.
    6. Either the next trial starts, OR a "thought probe" question appears
       asking the participant what they were just thinking about.

Per the team's latest review, this repeats for ~34 trials per block (about
20 minutes of real task time total), across 4 blocks (2 with background
music/distraction playing, 2 in silence). A mandatory timed break runs
between each block, and the counterbalancing order (which condition comes
first) is chosen by the experimenter at the start via the "Session" field
in the participant dialog - see get_block_order() below for exactly how.

HOW TO USE THIS FILE:
- This is a plain Python script (not a PsychoPy Builder .psyexp file), so you
  run it directly: `python pvt_clock_task.py`
- All the "knobs" you might want to change (number of trials, timings, etc.)
  are collected at the top under SETTINGS, so you shouldn't need to touch
  the actual trial code below that to tweak the task.
- Data gets saved to a .csv file in a "data" folder, one row per trial.

NUMBERS STILL PENDING FINAL CONFIRMATION FROM THE TEAM:
- Thought probes per block: earlier notes gave conflicting numbers (3 vs. 6).
  The latest team review settled on "~2-4, distributed randomly," so this is
  set to 3 as a middle-ground default (THOUGHT_PROBES_PER_BLOCK below) -
  change this one number once the exact count is finalized. Random placement
  within the block is already handled for you.
- Wait time before the clock moves, and fixation cross length: the team
  agreed both should be shortened from the original paper's values (2-10s
  wait, 2s fixation) but hasn't landed on exact new numbers yet. Both are
  left at the original values below (MIN_DELAY, MAX_DELAY, FIXATION_DURATION)
  with a comment marking them as pending - update them once the team decides.
- Break length between blocks: set to 30 seconds below (BREAK_DURATION_SECONDS)
  as a starting default since the team asked for timed breaks to be
  implemented but hadn't specified a length - change this one number once
  the team settles on how long the break should be.
"""

from psychopy import visual, core, event, gui, data
import random
import os
import csv


# ============================================================
# SETTINGS  (change things here, not in the code below)
# ============================================================

N_PRACTICE_TRIALS = 5          # practice trials before the real task starts
N_BLOCKS = 4                   # total blocks (2 distraction + 2 no-distraction)
N_TRIALS_PER_BLOCK = 34        # ~34 trials/block -> ~20 min total task time (per team review)
THOUGHT_PROBES_PER_BLOCK = 3   # middle of the agreed ~2-4 range; finalize and update

# PENDING: team agreed this should be shorter than the original paper's 2s,
# exact value not yet decided. Left at the original value until confirmed.
FIXATION_DURATION = 2.0        # seconds the "+" cross shows for

# PENDING: team agreed the original 2-10s wait range should be shortened,
# exact new range not yet decided. Left at the original values until confirmed.
MIN_DELAY = 2.0                # shortest possible wait before the clock moves
MAX_DELAY = 10.0               # longest possible wait before the clock moves
DELAY_STEP = 0.5               # delays are in these increments (2.0, 2.5, 3.0 ... 10.0)

FEEDBACK_DURATION = 1.0        # seconds the stopped clock stays on screen
BLANK_DURATION = 0.5           # seconds of blank grey screen between trials

# PENDING: team asked for timed breaks between blocks but didn't specify a
# length yet. 30 seconds is a placeholder default - change this one number
# once the team decides on the real break length.
BREAK_DURATION_SECONDS = 30

CLOCK_ROTATION_SPEED = 360.0   # degrees per second the hand sweeps (tune to taste)

# NOTE: block order (which blocks have music vs. silence) is no longer a
# fixed constant here - it's chosen per participant via the "Session"
# field in the startup dialog, so the team can alternate 1/2/1/2 across
# participants and actually get counterbalancing. See get_block_order().

# The three thought-probe response options participants choose between.
# Key '1', '2', '3' on the keyboard selects the matching option.
THOUGHT_PROBE_OPTIONS = [
    "1 - My mind was disengaged (blank, tired, elsewhere)",
    "2 - I was focused on the task",
    "3 - I was distracted by something external (sights/sounds/sensations)",
]

DATA_FOLDER = "data"


# ============================================================
# SET UP THE WINDOW AND STIMULI
# ============================================================

def get_participant_info():
    """
    Pops up a small dialog box asking for the participant ID and which
    counterbalancing "Session" this run should use. The Session value
    controls which condition (music or silence) this participant does
    first - see get_block_order() below for exactly how. Returns a
    dictionary of what the experimenter typed.
    """
    info = {"Participant ID": "", "Session (1 or 2)": "1"}
    dlg = gui.DlgFromDict(info, title="PVT Clock Task")
    if not dlg.OK:
        core.quit()  # if they hit Cancel, stop the script entirely
    return info


def get_block_order(session_value):
    """
    Turns the "Session" value the experimenter typed into an actual block
    order, so counterbalancing is a real per-participant choice instead of
    a constant buried in the settings.

    Session 1 -> distraction, silence, distraction, silence
    Session 2 -> silence, distraction, silence, distraction
    Anything else typed by mistake falls back to Session 1's order, rather
    than crashing the script.

    Run consecutive participants as 1, 2, 1, 2, ... and the two orders end
    up used equally often, which is what counterbalancing means in practice.
    """
    if session_value.strip() == "2":
        return [False, True, False, True]
    return [True, False, True, False]


def make_window():
    """Creates the PsychoPy window everything gets drawn into."""
    win = visual.Window(
        size=(1920, 1080),
        fullscr=True,
        color="grey",
        units="norm",
    )
    win.mouseVisible = True
    return win


def make_stimuli(win):
    """
    Builds all the visual objects we'll reuse across trials, so we don't
    recreate them every single trial (that would be slower and messier).
    Returns them as a dictionary so we can grab whichever one we need by name.
    """
    fixation = visual.TextStim(win, text="+", height=0.15, color="white")

    # The clock face: a circle outline.
    clock_face = visual.Circle(
        win, radius=0.3, edges=64, fillColor=None, lineColor="white", lineWidth=4
    )

    # The clock hand: a line from the centre pointing up (12 o'clock) at rotation 0.
    # PsychoPy rotates shapes clockwise as `ori` increases, which is exactly
    # what we want for a clock hand.
    clock_hand = visual.Line(
        win, start=(0, 0), end=(0, 0.28), lineColor="white", lineWidth=6
    )

    instructions = visual.TextStim(
        win,
        text=(
            "Watch the clock.\n\n"
            "As soon as the hand starts moving, click the LEFT mouse button "
            "as fast as you can.\n\n"
            "Click the mouse button now to begin practice."
        ),
        height=0.06,
        wrapWidth=1.6,
        color="white",
    )

    probe_text = visual.TextStim(
        win,
        text="",
        height=0.06,
        wrapWidth=1.6,
        color="white",
        pos=(0, 0.3),
    )

    break_text = visual.TextStim(
        win,
        text="",
        height=0.06,
        wrapWidth=1.6,
        color="white",
    )

    return {
        "fixation": fixation,
        "clock_face": clock_face,
        "clock_hand": clock_hand,
        "instructions": instructions,
        "probe_text": probe_text,
        "break_text": break_text,
    }


# ============================================================
# WAITING FOR A MOUSE CLICK (without freezing the window)
# ============================================================

def wait_for_mouse_click(win, mouse, draw_each_frame=None):
    """
    Waits for a left mouse click, redrawing the screen every frame while
    it waits.

    Why this function exists (this is a real fix, not just style): a loop
    like `while not mouse.getPressed()[0]: pass` never calls win.flip(),
    and PsychoPy processes window/input events during flip() calls. Without
    that, the window can appear to freeze or stop responding to clicks -
    this is exactly what was happening on the old "click to continue"
    screens. Calling win.flip() every frame here keeps the window
    responsive the whole time it's waiting.

    draw_each_frame: an optional stimulus, or list of stimuli, to redraw
    every frame while waiting (e.g. instructions text) so it stays on
    screen instead of disappearing after the first flip.
    """
    mouse.clickReset()
    stims_to_draw = []
    if draw_each_frame is not None:
        stims_to_draw = draw_each_frame if isinstance(draw_each_frame, list) else [draw_each_frame]

    clicked = False
    while not clicked:
        for stim_item in stims_to_draw:
            stim_item.draw()
        win.flip()
        if mouse.getPressed()[0]:
            clicked = True


# ============================================================
# ONE TRIAL
# ============================================================

def run_one_trial(win, stim, mouse):
    """
    Runs a single PVT trial from fixation cross through to the feedback
    screen. Returns a dictionary with the trial's data (delay used, reaction
    time, etc.) so the main loop can save it.
    """

    # --- Step 1: fixation cross ---
    stim["fixation"].draw()
    win.flip()
    core.wait(FIXATION_DURATION)

    # --- Step 2: still clock, random wait before it starts moving ---
    # random.choice picks one of the allowed 0.5s-step delay values,
    # e.g. 2.0, 2.5, 3.0, ... 10.0 seconds.
    possible_delays = [
        MIN_DELAY + i * DELAY_STEP
        for i in range(int((MAX_DELAY - MIN_DELAY) / DELAY_STEP) + 1)
    ]
    wait_time = random.choice(possible_delays)

    stim["clock_hand"].ori = 0  # hand back to 12 o'clock
    mouse.clickReset()          # clear any earlier clicks so they don't carry over

    # A "false start" is a click that happens before the hand starts moving.
    # We count how many happen during the wait, but we don't end the trial
    # early for one - the participant just keeps waiting for the real onset.
    false_start_count = 0

    still_clock_timer = core.Clock()
    while still_clock_timer.getTime() < wait_time:
        stim["clock_face"].draw()
        stim["clock_hand"].draw()
        win.flip()
        if mouse.getPressed()[0]:
            false_start_count += 1
            mouse.clickReset()  # clear it so the same click isn't counted repeatedly

    # --- Step 3: clock hand starts moving, timing starts NOW ---
    mouse.clickReset()
    rt_clock = core.Clock()
    clicked = False
    rt = None

    while not clicked:
        elapsed = rt_clock.getTime()
        stim["clock_hand"].ori = (elapsed * CLOCK_ROTATION_SPEED) % 360
        stim["clock_face"].draw()
        stim["clock_hand"].draw()
        win.flip()

        if mouse.getPressed()[0]:
            rt = rt_clock.getTime()
            clicked = True

        # Safety cap: don't let a trial hang forever if they never click.
        if elapsed > 5.0:
            rt = None
            clicked = True

    # --- Step 4: feedback - clock stays frozen where it stopped ---
    stim["clock_face"].draw()
    stim["clock_hand"].draw()
    win.flip()
    core.wait(FEEDBACK_DURATION)

    # --- Step 5: blank screen between trials ---
    win.flip()  # window background color (grey) with nothing drawn on it
    core.wait(BLANK_DURATION)

    return {
        "wait_time": wait_time,
        "rt_seconds": rt,
        "false_start_count": false_start_count,
    }


def run_thought_probe(win, stim):
    """
    Shows the three thought-probe options and waits for the participant to
    press 1, 2, or 3 on the keyboard. Returns which one they picked.
    """
    probe_lines = "Please characterise your immediately preceding thoughts:\n\n"
    probe_lines += "\n".join(THOUGHT_PROBE_OPTIONS)
    stim["probe_text"].text = probe_lines
    stim["probe_text"].pos = (0, 0)

    stim["probe_text"].draw()
    win.flip()

    response = event.waitKeys(keyList=["1", "2", "3"])
    return response[0]


def run_timed_break(win, stim, mouse, block_number, is_distraction_block):
    """
    Runs the mandatory break before a block starts: first a fixed-length
    countdown the participant can't skip (BREAK_DURATION_SECONDS), then a
    "click when ready" screen so the experimenter can start or stop the
    music before the block actually begins.

    Splitting it into two parts like this guarantees everyone gets the same
    minimum rest, while still letting the experimenter control exactly when
    the block's audio starts.
    """
    break_clock = core.Clock()
    while break_clock.getTime() < BREAK_DURATION_SECONDS:
        remaining = max(0, int(BREAK_DURATION_SECONDS - break_clock.getTime()))
        stim["break_text"].text = (
            f"Take a short break.\n\n"
            f"Block {block_number} of {N_BLOCKS} starts in {remaining} seconds..."
        )
        stim["break_text"].draw()
        win.flip()

    stim["break_text"].text = (
        f"Block {block_number} of {N_BLOCKS}\n\n"
        + ("(Background music will play)\n\n" if is_distraction_block
           else "(Silence - no music)\n\n")
        + "Click the mouse button when you are ready to continue."
    )
    wait_for_mouse_click(win, mouse, draw_each_frame=stim["break_text"])


# ============================================================
# SAVING DATA
# ============================================================

def make_data_writer(participant_id):
    """
    Opens a .csv file for this participant and writes the header row.
    Returns the file handle and a csv.writer so the main loop can add rows.
    """
    if not os.path.exists(DATA_FOLDER):
        os.makedirs(DATA_FOLDER)

    filename = os.path.join(DATA_FOLDER, f"{participant_id}_pvt_clock.csv")
    csv_file = open(filename, mode="w", newline="")
    writer = csv.writer(csv_file)
    writer.writerow([
        "block_number",
        "distraction_condition",
        "trial_number",
        "wait_time_seconds",
        "rt_seconds",
        "false_start_count",
        "trial_type",       # "trial" or "thought_probe"
        "thought_probe_response",
    ])
    csv_file.flush()
    return csv_file, writer


def write_data_row(csv_file, writer, row):
    """
    Writes one row and immediately flushes it to disk. Flushing after every
    row (instead of only when the file is closed) means that if the script
    crashes or PsychoPy is force-quit mid-session, whatever's been collected
    so far is still safely on disk rather than lost with the unclosed file.
    """
    writer.writerow(row)
    csv_file.flush()


# ============================================================
# MAIN EXPERIMENT LOOP
# ============================================================

def main():
    participant_info = get_participant_info()
    participant_id = participant_info["Participant ID"] or "test"
    block_order = get_block_order(participant_info["Session (1 or 2)"])

    win = make_window()
    stim = make_stimuli(win)
    mouse = event.Mouse(win=win)

    csv_file, writer = make_data_writer(participant_id)

    # Wrapped in try/finally so the data file always gets closed properly -
    # including if something goes wrong partway through a session - rather
    # than risking a corrupted or incomplete file.
    try:
        # --- Practice trials (not saved to the real data file) ---
        # Uses wait_for_mouse_click so this actually waits for a mouse
        # click, matching what the on-screen instructions say. (The
        # previous version of this screen said "click the mouse" but the
        # code was actually waiting for a keyboard press instead - fixed.)
        wait_for_mouse_click(win, mouse, draw_each_frame=stim["instructions"])

        for _ in range(N_PRACTICE_TRIALS):
            run_one_trial(win, stim, mouse)

        # --- Real blocks ---
        for block_index in range(N_BLOCKS):
            is_distraction_block = block_order[block_index]

            # Mandatory timed break, then click-to-continue so the
            # experimenter can start/stop the music before the block begins.
            run_timed_break(win, stim, mouse, block_index + 1, is_distraction_block)

            # Decide in advance which trial numbers within this block will
            # be followed by a thought probe, so they land on random (not
            # fixed) trials, matching the paper's design.
            probe_after_trials = set(
                random.sample(range(N_TRIALS_PER_BLOCK), THOUGHT_PROBES_PER_BLOCK)
            )

            for trial_index in range(N_TRIALS_PER_BLOCK):
                trial_data = run_one_trial(win, stim, mouse)

                write_data_row(csv_file, writer, [
                    block_index + 1,
                    is_distraction_block,
                    trial_index + 1,
                    trial_data["wait_time"],
                    trial_data["rt_seconds"],
                    trial_data["false_start_count"],
                    "trial",
                    "",
                ])

                if trial_index in probe_after_trials:
                    probe_response = run_thought_probe(win, stim)
                    write_data_row(csv_file, writer, [
                        block_index + 1,
                        is_distraction_block,
                        trial_index + 1,
                        "",
                        "",
                        "",
                        "thought_probe",
                        probe_response,
                    ])

        # --- Goodbye screen ---
        goodbye = visual.TextStim(
            win, text="Thank you - this part of the study is complete.",
            height=0.07, color="white",
        )
        goodbye.draw()
        win.flip()
        core.wait(2.0)

    finally:
        csv_file.close()
        win.close()

    core.quit()


if __name__ == "__main__":
    main()
