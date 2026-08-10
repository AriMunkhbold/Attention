"""
PVT CLOCK TASK

A psychomotor vigilance task using a clock hand instead of a digital
counter. Run directly: `python pvt_clock_task.py`. All the settings you'd
want to tweak are below under SETTINGS. Data saves to a .csv in "data/".

Pending team decisions, still using placeholder values below:
- THOUGHT_PROBES_PER_BLOCK: agreed ~2-4, set to 3 for now
- MIN_DELAY / MAX_DELAY / FIXATION_DURATION: team agreed to shorten these
  from the paper's original values, exact numbers not decided yet
- BREAK_DURATION_SECONDS: 30s placeholder, no official length set yet
- MUSIC_FILE_PATH: points at a placeholder filename, needs a real audio file
"""

from psychopy import visual, core, event, gui, data, sound
import random
import os
import csv


# ============================================================
# SETTINGS
# ============================================================

N_PRACTICE_TRIALS = 5
N_BLOCKS = 4                   # 2 distraction + 2 no-distraction
N_TRIALS_PER_BLOCK = 34        # ~20 min total task time
THOUGHT_PROBES_PER_BLOCK = 3

FIXATION_DURATION = 2.0        # seconds the "+" cross shows for
MIN_DELAY = 2.0                # shortest wait before the clock moves
MAX_DELAY = 10.0               # longest wait before the clock moves
DELAY_STEP = 0.5               # delay increments (2.0, 2.5, 3.0 ... 10.0)

FEEDBACK_DURATION = 1.0        # seconds the stopped clock stays on screen
BLANK_DURATION = 0.5           # seconds of blank screen between trials
BREAK_DURATION_SECONDS = 30    # mandatory break length between blocks

CLOCK_ROTATION_SPEED = 360.0   # degrees per second the hand sweeps

MUSIC_FILE_PATH = "eternal.mp3"  # plays during distraction blocks only

# Block order (music vs. silence) comes from the "Session" field the
# experimenter types in - see get_block_order().

THOUGHT_PROBE_OPTIONS = [
    "1 - My mind was disengaged (blank, tired, elsewhere)",
    "2 - I was focused on the task",
    "3 - I was distracted by something external (sights/sounds/sensations)",
]

DATA_FOLDER = "data"


# ============================================================
# SETUP
# ============================================================

def get_participant_info():
    """Dialog box for participant ID + counterbalancing session (1 or 2)."""
    info = {"Participant ID": "", "Session (1 or 2)": "1"}
    dlg = gui.DlgFromDict(info, title="PVT Clock Task")
    if not dlg.OK:
        core.quit()
    return info


def get_block_order(session_value):
    """
    Session 1 -> distraction, silence, distraction, silence
    Session 2 -> silence, distraction, silence, distraction
    Run participants alternating 1, 2, 1, 2... for real counterbalancing.
    """
    if session_value.strip() == "2":
        return [False, True, False, True]
    return [True, False, True, False]


def make_window():
    win = visual.Window(size=(1920, 1080), fullscr=True, color="grey", units="norm")
    win.mouseVisible = True
    return win


def make_stimuli(win):
    """Builds every visual element once, reused across trials."""
    fixation = visual.TextStim(win, text="+", height=0.15, color="white")

    clock_face = visual.Circle(
        win, radius=0.3, edges=64, fillColor=None, lineColor="white", lineWidth=4
    )

    # ori=0 points the hand at 12 o'clock; PsychoPy rotates clockwise as ori increases
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
        win, text="", height=0.06, wrapWidth=1.6, color="white", pos=(0, 0.3)
    )

    break_text = visual.TextStim(win, text="", height=0.06, wrapWidth=1.6, color="white")

    return {
        "fixation": fixation,
        "clock_face": clock_face,
        "clock_hand": clock_hand,
        "instructions": instructions,
        "probe_text": probe_text,
        "break_text": break_text,
    }


def load_music():
    """Loads the distraction track once. Returns None (silent) if the file's missing."""
    try:
        return sound.Sound(MUSIC_FILE_PATH, loops=-1)
    except Exception as error:
        print(f"WARNING: couldn't load music file '{MUSIC_FILE_PATH}' ({error}). "
              f"Distraction blocks will run in silence.")
        return None


# ============================================================
# WAITING FOR A MOUSE CLICK
# ============================================================

def wait_for_mouse_click(win, mouse, draw_each_frame=None):
    """
    Waits for a left click while flipping every frame, so the window stays
    responsive (a plain `while not pressed: pass` loop can freeze it, since
    PsychoPy processes input during flip() calls).
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
    """Runs one trial, fixation through feedback. Returns the trial's data."""

    stim["fixation"].draw()
    win.flip()
    core.wait(FIXATION_DURATION)

    possible_delays = [
        MIN_DELAY + i * DELAY_STEP
        for i in range(int((MAX_DELAY - MIN_DELAY) / DELAY_STEP) + 1)
    ]
    wait_time = random.choice(possible_delays)

    stim["clock_hand"].ori = 0
    mouse.clickReset()
    false_start_count = 0

    still_clock_timer = core.Clock()
    while still_clock_timer.getTime() < wait_time:
        stim["clock_face"].draw()
        stim["clock_hand"].draw()
        win.flip()
        if mouse.getPressed()[0]:
            false_start_count += 1
            mouse.clickReset()

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
        if elapsed > 5.0:  # safety cap so a trial can't hang forever
            rt = None
            clicked = True

    stim["clock_face"].draw()
    stim["clock_hand"].draw()
    win.flip()
    core.wait(FEEDBACK_DURATION)

    win.flip()
    core.wait(BLANK_DURATION)

    return {
        "wait_time": wait_time,
        "rt_seconds": rt,
        "false_start_count": false_start_count,
    }


def run_thought_probe(win, stim):
    """Shows the 3 options, waits for a 1/2/3 keypress, returns the choice."""
    probe_lines = "Please characterise your immediately preceding thoughts:\n\n"
    probe_lines += "\n".join(THOUGHT_PROBE_OPTIONS)
    stim["probe_text"].text = probe_lines
    stim["probe_text"].pos = (0, 0)

    stim["probe_text"].draw()
    win.flip()

    response = event.waitKeys(keyList=["1", "2", "3"])
    return response[0]


def run_timed_break(win, stim, mouse, music, block_number, is_distraction_block):
    """
    Countdown break, then click-to-continue. Music is always stopped here
    first - breaks are silent even going into a distraction block.
    """
    if music is not None:
        music.stop()

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
        "trial_type",
        "thought_probe_response",
    ])
    csv_file.flush()
    return csv_file, writer


def write_data_row(csv_file, writer, row):
    """Writes + flushes immediately, so a crash doesn't lose unsaved rows."""
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
    music = load_music()

    csv_file, writer = make_data_writer(participant_id)

    try:
        wait_for_mouse_click(win, mouse, draw_each_frame=stim["instructions"])

        for _ in range(N_PRACTICE_TRIALS):
            run_one_trial(win, stim, mouse)

        for block_index in range(N_BLOCKS):
            is_distraction_block = block_order[block_index]

            run_timed_break(win, stim, mouse, music, block_index + 1, is_distraction_block)

            if is_distraction_block and music is not None:
                music.play()

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

            if music is not None:
                music.stop()

        goodbye = visual.TextStim(
            win, text="Thank you - this part of the study is complete.",
            height=0.07, color="white",
        )
        goodbye.draw()
        win.flip()
        core.wait(2.0)

    finally:
        if music is not None:
            music.stop()
        csv_file.close()
        win.close()

    core.quit()


if __name__ == "__main__":
    main()
