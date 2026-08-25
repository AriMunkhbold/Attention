#!/usr/bin/env python
# coding: utf-8

# In[ ]:


# =====================================================================
# COMBINED EXPERIMENT: 2AFC Association Task + Psychomotor Vigilance Task
# Section order (which task runs first) is randomized per participant.
# =====================================================================

# --- Setup & imports ---
from psychopy import prefs  # set audio backend before importing sound
prefs.hardware['audioLib'] = ['pygame', 'sounddevice']
prefs.general['audioDevice'] = ['default']

import os
os.environ["QT_QPA_PLATFORM"] = "cocoa"  # macOS GUI fix (safe elsewhere too)

import random
import csv
import traceback
from itertools import combinations

import pandas as pd
import numpy as np

from psychopy import visual, core, event, sound, gui, data
from psychopy import logging
logging.console.setLevel(logging.ERROR)  # suppresses certain warnings
import warnings
warnings.filterwarnings("ignore", message="elementwise comparison failed")

print("Current working directory:", os.getcwd())


# =====================================================================
# SHARED PARTICIPANT ID / FOLDER SETUP
# =====================================================================

def get_participant_id():
    """Prompt once for a participant ID; used by both sections."""
    participant_id = input("Enter Participant ID: ").strip()
    participant_folder = os.path.join("./participant_data", participant_id)
    if not os.path.exists(participant_folder):
        os.makedirs(participant_folder)
    else:
        # Always overwrite existing data
        for file in [f for f in os.listdir(participant_folder) if os.path.isfile(os.path.join(participant_folder, f))]:
            os.remove(os.path.join(participant_folder, file))
    return participant_id


def get_participant_folder():
    return os.path.join("./participant_data", participant_data["participant_id"])


# =====================================================================
# SHARED INSTRUCTION HELPER
# =====================================================================

def show_instructions(text, key_list):
    """Display instructions and wait for a key in key_list. Returns the key pressed (or 's' if pressed)."""
    instr = visual.TextStim(win, text=text, color="lightgrey", height=0.06, wrapWidth=1.6)
    while True:
        instr.draw()
        win.flip()
        keys = event.waitKeys(keyList=key_list + ["escape", "s"])
        if "escape" in keys:
            win.close()
            core.quit()
        if "s" in keys:
            return "s"
        if keys:
            return keys[0]

def show_overall_welcome():
    text = (
        "Welcome!\n\n"
        "This experiment has two sections.\n\n"
        "Press SPACEBAR to begin."
    )
    stim = visual.TextStim(win, text=text, color="lightgrey", height=0.06, wrapWidth=1.6)
    stim.draw()
    win.flip()
    keys = event.waitKeys(keyList=["space", "escape"])
    if "escape" in keys:
        win.close()
        core.quit()

def wait_for_mouse_click(win, mouse, draw_each_frame=None):
    """Waits for a left mouse click, redrawing the screen every frame while it waits."""
    mouse.clickReset()
    stims_to_draw = []
    if draw_each_frame is not None:
        stims_to_draw = draw_each_frame if isinstance(draw_each_frame, list) else [draw_each_frame]

    clicked = False
    while not clicked:
        for stim_item in stims_to_draw:
            stim_item.draw()
        win.flip()
        keys = event.getKeys(keyList=["space", "escape"])
        if "escape" in keys:
            win.close()
            core.quit()
        if mouse.getPressed()[0]:
            clicked = True


# =====================================================================
# ############################  2AFC TASK  ############################
# =====================================================================

# --- ISI / ITI jitter settings ---
mean_ITI = 0.5
sd_ITI = 0.2
n_ITI = 150

mean_ISI = 0.5
sd_ISI = 0.2
n_ISI = 150

def sample_non_negative_normal(mean, std, size):
    samples = np.random.normal(mean, std, size)
    while np.any(samples < 0):
        samples[samples < 0] = np.random.normal(mean, std, np.sum(samples < 0))
    return samples


def wait_and_listen(duration, response_state, trial_clock, valid_keys=("1", "0")):
    """Wait out `duration` seconds while polling for a keypress.
    If a valid key is pressed and no response has been recorded yet,
    record it (response + RT) but keep waiting until duration elapses."""
    clock = core.Clock()
    while clock.getTime() < duration:
        keys = event.getKeys(keyList=list(valid_keys) + ["escape", "s"])
        if "escape" in keys:
            win.close()
            core.quit()
        if "s" in keys:
            response_state["skip"] = True
            return
        for k in keys:
            if k in valid_keys and response_state["response"] is None:
                response_state["response"] = k
                response_state["reaction_time"] = round(trial_clock.getTime(), 3)
        core.wait(0.005)


# --- Save helpers ---

def save_crossmodal_with_feedback_to_excel():
    participant_folder = get_participant_folder()
    os.makedirs(participant_folder, exist_ok=True)
    excel_filename = os.path.join(participant_folder, "crossmodal_wf_log.xlsx")

    df = pd.DataFrame(participant_data.get("crossmodal_wf_log", []))
    pause_df = pd.DataFrame(participant_data.get("crossmodal_pause_durations", []))
    confidence_df = pd.DataFrame(participant_data.get("confidence_responses", []))

    # Record which section ran first/second, if that's been determined yet
    section_order = participant_data.get("section_order", [])
    order_rows = [{"position": i + 1, "section": name} for i, name in enumerate(section_order)]
    order_df = pd.DataFrame(order_rows if order_rows else [{"position": None, "section": None}])

    with pd.ExcelWriter(excel_filename, engine="openpyxl") as writer:
        df.to_excel(writer, sheet_name="trial_log", index=False)
        pause_df.to_excel(writer, sheet_name="pause_summary", index=False)
        confidence_df.to_excel(writer, sheet_name="confidence_responses", index=False)
        order_df.to_excel(writer, sheet_name="section_order", index=False)

    print(f"Crossmodal with feedback data saved to {excel_filename}")


def save_unimodal_to_excel(matrix, trial_log, stimuli, duration, label, order):
    try:
        participant_folder = get_participant_folder()
        os.makedirs(participant_folder, exist_ok=True)
        filename = os.path.join(participant_folder, f"Unimodal_{label}s_({order}).xlsx")

        n = len(stimuli)
        matrix_df = pd.DataFrame(matrix, index=stimuli, columns=stimuli)

        def name_of(x):
            return stimuli[x] if isinstance(x, int) else x

        trial_rows = [[name_of(t[0]), name_of(t[1]), name_of(t[2]), name_of(res)]
                      for t, res in trial_log]

        trial_cols = [f"{label} 1", f"{label} 2", f"{label} 3", f"Chosen {label}"]
        trial_log_df = pd.DataFrame(trial_rows, columns=trial_cols)
        trial_log_df.index = range(1, len(trial_rows) + 1)
        trial_log_df.index.name = "Trial Number"

        meta_df = pd.DataFrame({
            "Duration (s)": [duration],
            "Order": [order],
            "N stimuli": [n],
        })

        with pd.ExcelWriter(filename, engine="openpyxl") as writer:
            meta_df.to_excel(writer, sheet_name="Trials", index=False, startrow=0)
            trial_log_df.to_excel(writer, sheet_name="Trials", index=True, startrow=len(meta_df) + 2)
            matrix_df.to_excel(writer, sheet_name="Difference_Scores", index=True)
            pd.DataFrame({"Stimulus": stimuli}).to_excel(writer, sheet_name="Stimuli", index=True)

        print(f"Data successfully saved to {filename}")
    except Exception as e:
        print(f"Could not save matrix to Excel ({e}).")

def ask_confidence_question(checkpoint_label):
    """Show a single typed-response confidence question."""
    question_text = "Rate your confidence level in your answers so far, from 1 to 5.\n\n1 = Not at all confident\n5 = Extremely confident\n\nType a number and press ENTER."
    instr = visual.TextStim(win, text=question_text, color="white", height=0.06, wrapWidth=1.6, pos=(0, 0.3))
    selection_stim = visual.TextStim(win, text="", color="yellow", height=0.09, wrapWidth=1.6, pos=(0, -0.25))

    selected = None
    while True:
        instr.draw()
        selection_stim.text = f"Selected: {selected}" if selected is not None else "Selected: (none yet)"
        selection_stim.draw()
        win.flip()

        keys = event.waitKeys(keyList=["1", "2", "3", "4", "5", "return", "escape"])
        if "escape" in keys:
            win.close()
            core.quit()
        key = keys[0]
        if key in ["1", "2", "3", "4", "5"]:
            selected = key
        elif key == "return" and selected is not None:
            break

    participant_data.setdefault("confidence_responses", []).append({
        "checkpoint": checkpoint_label,
        "response": selected
    })
    print(f"Confidence response recorded at {checkpoint_label}: {selected}")

    # --- Transition screen ---
    if checkpoint_label == "midpoint":
        transition_text = "Thanks!\n\nYou're halfway through this section.\n\nPress SPACEBAR when you're ready to continue."
    else:
        transition_text = "Thanks!\n\nPress SPACEBAR to continue."

    transition_stim = visual.TextStim(win, text=transition_text, color="lightgrey", height=0.06, wrapWidth=1.6)
    transition_stim.draw()
    win.flip()
    keys = event.waitKeys(keyList=["space", "escape"])
    if "escape" in keys:
        win.close()
        core.quit()

    # --- Buffer before resuming trials ---
    fixation_buffer = visual.TextStim(win, text="+", color="lightgrey", height=0.1, pos=(0, 0))
    fixation_buffer.draw()
    win.flip()
    core.wait(1.0)


# --- 2AFC timing constants & stimuli ---
STIMULUS_DURATION = 1.0
FIXATION_DURATION = 0.5

stimuli_pairs = [
    ("shape_01.png", "sound_01.wav"), ("shape_02.png", "sound_02.wav"),
    ("shape_03.png", "sound_03.wav"), ("shape_04.png", "sound_04.wav"),
    ("shape_05.png", "sound_05.wav"), ("shape_06.png", "sound_06.wav"),
    ("shape_07.png", "sound_07.wav"), ("shape_08.png", "sound_08.wav"),
    ("shape_09.png", "sound_09.wav"), ("shape_10.png", "sound_10.wav"),
]


def preload_sounds(audio_dir):
    sound_dict = {}
    for fname in sorted([f for f in os.listdir(audio_dir) if f.startswith("sound_") and f.endswith(".wav")]):
        sound_dict[fname] = sound.Sound(os.path.join(audio_dir, fname))
    return sound_dict


def crossWF_calc_trial_diff(sound1, sound2):
    idx1 = int(sound1.split('_')[1].split('.')[0])
    idx2 = int(sound2.split('_')[1].split('.')[0])
    return 9 - abs(idx1 - idx2)


def crossWF_pick_incorrect_tone(correct_tone, available_tones, current_diff, trial_num):
    attempts = 0
    while attempts < 30:
        attempts += 1
        candidate = random.choice(available_tones)
        trial_diff = crossWF_calc_trial_diff(correct_tone, candidate)
        if ((current_diff + trial_diff) / trial_num) < 5 and ((current_diff + trial_diff) / trial_num) > 3:
            return candidate, trial_diff
    return candidate, trial_diff


def crossmodal_with_feedback():
    """The 2AFC section. Returns 'done' or 'skip'."""
    global participant_data
    participant_data["task order"] = "active"
    participant_data["crossmodal_wf_log"] = []
    participant_data["crossmodal_pause_durations"] = []
    event.clearEvents()

    print("Starting Crossmodal with feedback (2AFC)...")

    section_label = f"SECTION {section_number} of {total_sections}\n\n" if section_number else ""

    instruction_result = show_instructions(
        "INSTRUCTIONS – Learning Task\n\n"
        "In this section, you'll see a SHAPE and hear a SOUND together.\n\n"
        "The same shape will be presented twice, each time with a different sound.\n"
        "Press '1' with your LEFT index finger if the FIRST pair is correct.\n"
        "Press '0' with your RIGHT index finger if the SECOND pair is correct.\n\n"
        "You'll get FEEDBACK after each response.\n\n"
        "Please focus on learning the correct pairings.\n\n"
        "Try to respond as accurately and quickly as possible.\n\n"
        "Press SPACEBAR to begin.",
        ["space"]
    )
    if instruction_result == "s":
        print("Crossmodal with feedback skipped.")
        return "skip"

    try:
        local_stimuli = list(stimuli_pairs)
        crossmodal_trials = []
        TRIALS_PER_PAIR = 15
        all_tones = [pair[1] for pair in stimuli_pairs]

        for img_file, audio_file in local_stimuli:
            available_tones = [snd for snd in all_tones if snd != audio_file]
            total_diff = 0
            for i in range(TRIALS_PER_PAIR // 2):
                incorrect_tone, trial_diff = crossWF_pick_incorrect_tone(audio_file, available_tones, total_diff, ((i+1)*2)-1)
                total_diff += trial_diff
                crossmodal_trials.append((img_file, audio_file, [audio_file, incorrect_tone]))
                incorrect_tone, trial_diff = crossWF_pick_incorrect_tone(audio_file, available_tones, total_diff, (i+1)*2)
                total_diff += trial_diff
                crossmodal_trials.append((img_file, audio_file, [incorrect_tone, audio_file]))
            if TRIALS_PER_PAIR % 2 != 0:
                if random.random() < 0.5:
                    incorrect_tone, trial_diff = crossWF_pick_incorrect_tone(audio_file, available_tones, total_diff, TRIALS_PER_PAIR)
                    total_diff += trial_diff
                    crossmodal_trials.append((img_file, audio_file, [audio_file, incorrect_tone]))
                else:
                    incorrect_tone, trial_diff = crossWF_pick_incorrect_tone(audio_file, available_tones, total_diff, TRIALS_PER_PAIR)
                    total_diff += trial_diff
                    crossmodal_trials.append((img_file, audio_file, [incorrect_tone, audio_file]))

        random.shuffle(crossmodal_trials)

        correct_feedback = visual.ImageStim(win, image="green_tick.png", size=(0.2, 0.2), pos=(0, 0))
        incorrect_feedback = visual.ImageStim(win, image="red_cross.png", size=(0.2, 0.2), pos=(0, 0))
        fixation = visual.TextStim(win, text="+", color="lightgrey", height=0.1, pos=(0, 0))
        prompt_sound2 = visual.TextStim(
            win, text="Press 1 (LEFT index) if FIRST pair is correct;\nPress 0 (RIGHT index) if SECOND pair is correct.",
            color="white", height=0.05, pos=(0, 0)
        )
        img_stim_left = visual.ImageStim(win, image=None, size=(0.3, 0.4), pos=(-0.5, 0))
        img_stim_right = visual.ImageStim(win, image=None, size=(0.3, 0.4), pos=(0.5, 0))

        cx, cy = 0, -0.6
        finalwidth = 1.4
        left = cx - (finalwidth / 2)
        progress_bar = visual.Rect(win, width=0, height=0.05, pos=(cx, cy), lineColor="white", fillColor="white", autoDraw=False, name="progressbar")

        interTrialPause_local = sample_non_negative_normal(mean_ITI, sd_ITI, len(crossmodal_trials))
        interStimulusPause_local = sample_non_negative_normal(mean_ISI, sd_ISI, len(crossmodal_trials))

        participant_data["crossmodal_pause_durations"].append({
            "interStimulusPause_mean": float(np.mean(interStimulusPause_local)),
            "interStimulusPause_std": float(np.std(interStimulusPause_local, ddof=0)),
            "interStimulusPause_min": float(np.min(interStimulusPause_local)),
            "interStimulusPause_max": float(np.max(interStimulusPause_local)),
            "interTrialPause_mean": float(np.mean(interTrialPause_local)),
            "interTrialPause_std": float(np.std(interTrialPause_local, ddof=0)),
            "interTrialPause_min": float(np.min(interTrialPause_local)),
            "interTrialPause_max": float(np.max(interTrialPause_local)),
        })

        trial_index = 0
        n_crossmodal_trials = len(crossmodal_trials)
        midpoint_index = 75  # halfway through 150 trials

        while trial_index < n_crossmodal_trials:
            img_file, audio_file, tones = crossmodal_trials[trial_index]
            event.clearEvents()
            if "escape" in event.getKeys(keyList=["escape"]):
                win.close()
                core.quit()
            if "s" in event.getKeys(keyList=["s"]):
                if trial_index < midpoint_index:
                    ask_confidence_question("midpoint")
                    trial_index = midpoint_index
                continue
            else:
                break

            trial_clock = core.Clock()
            image_path = os.path.join(image_dir, img_file)
            trial_difficulty = crossWF_calc_trial_diff(tones[0], tones[1])
            response_state = {"response": None, "reaction_time": None, "skip": False}

            progress = trial_index / float((TRIALS_PER_PAIR * 10) - 1)
            width = finalwidth * progress
            progress_bar.width = width
            progress_bar.pos = (left + width/2, cy)
            progress_bar.autoDraw = True
            win.flip()

            win.flip()
            core.wait(interTrialPause_local[trial_index])

            img_stim_left.image = image_path
            img_stim_left.draw()
            win.flip()
            trial_clock.reset()
            main_sounds[tones[0]].stop()
            main_sounds[tones[0]].play()
            wait_and_listen(STIMULUS_DURATION, response_state, trial_clock)
            if response_state["skip"]:
                if trial_index < midpoint_index:
                    ask_confidence_question("midpoint")
                    trial_index = midpoint_index
                    continue
                else:
                    break

            fixation.pos = (0, 0)
            fixation.draw()
            win.flip()
            wait_and_listen(FIXATION_DURATION, response_state, trial_clock)
            if response_state["skip"]:
                if trial_index < midpoint_index:
                    ask_confidence_question("midpoint")
                    trial_index = midpoint_index
                    continue
                else:
                    break

            win.flip()
            wait_and_listen(interStimulusPause_local[trial_index], response_state, trial_clock)
            if response_state["skip"]:
                if trial_index < midpoint_index:
                    ask_confidence_question("midpoint")
                    trial_index = midpoint_index
                    continue
                else:
                    break

            img_stim_right.image = image_path
            img_stim_right.draw()
            win.flip()
            main_sounds[tones[1]].stop()
            main_sounds[tones[1]].play()
            wait_and_listen(STIMULUS_DURATION, response_state, trial_clock)
            if response_state["skip"]:
                if trial_index < midpoint_index:
                    ask_confidence_question("midpoint")
                    trial_index = midpoint_index
                    continue
                else:
                    break

            prompt_sound2.draw()
            win.flip()

            if response_state["response"] is None:
                wait_and_listen(4, response_state, trial_clock)
                if response_state["skip"]:
                    if trial_index < midpoint_index:
                        ask_confidence_question("midpoint")
                        trial_index = midpoint_index
                        continue
                    else:
                        break

            response = response_state["response"] if response_state["response"] is not None else "NA"
            reaction_time = response_state["reaction_time"] if response_state["reaction_time"] is not None else round(trial_clock.getTime(), 3)

            correct_sound = dict(stimuli_pairs).get(img_file)
            correct_answer = "1" if tones[0] == correct_sound else "0"

            participant_data["reaction time"].append(reaction_time)
            if response == correct_answer:
                participant_data["crossmodal with feedback correct"] += 1
                correct_feedback.draw()
            else:
                participant_data["crossmodal with feedback incorrect"] += 1
                incorrect_feedback.draw()
            win.flip()
            core.wait(0.5)

            participant_data["crossmodal_wf_log"].append({
                "trial_index": trial_index,
                "trial_type": "shape+2sounds",
                "stimulus": img_file,
                "audio": audio_file,
                "tones_order": tones,
                "correct_answer": correct_answer,
                "response": response,
                "reaction_time": reaction_time,
                "trial_difficulty": trial_difficulty,
                "interStimulusPause": float(interStimulusPause_local[trial_index]),
                "interTrialPause": float(interTrialPause_local[trial_index])
            })

            if trial_index == 74:
                ask_confidence_question("midpoint")
            trial_index += 1

        progress_bar.autoDraw = False
        ask_confidence_question("end")
        end_msg = visual.TextStim(win, text="You have completed this section.\n\nPress SPACEBAR to continue.", color="lightgrey", height=0.06, pos=(0, 0))
        end_msg.draw()
        win.flip()
        event.waitKeys(keyList=["space"])

        print("Crossmodal with feedback completed successfully.")
        return "done"

    except Exception as e:
        print("Error during crossmodal with feedback:")
        traceback.print_exc()
        core.quit()

# =====================================================================
# #####################  PSYCHOMOTOR VIGILANCE TASK  ###################
# =====================================================================

PVT_N_PRACTICE_TRIALS = 3
PVT_N_BLOCKS = 4
PVT_N_TRIALS_PER_BLOCK = 34
PVT_THOUGHT_PROBES_PER_BLOCK = 3

PVT_FIXATION_DURATION = 2.0
PVT_MIN_DELAY = 2.0
PVT_MAX_DELAY = 10.0
PVT_DELAY_STEP = 0.5

PVT_FEEDBACK_DURATION = 1.0
PVT_BLANK_DURATION = 0.5
PVT_BREAK_DURATION_SECONDS = 30
PVT_CLOCK_ROTATION_SPEED = 360.0


PVT_THOUGHT_PROBE_OPTIONS = [
    "My mind was disengaged (blank, tired, elsewhere)",
    "I was focused on the task",
    "I was distracted by something external (sights/sounds/sensations)",
]


def get_pvt_block_order(session_value):
    if session_value.strip() == "2":
        return [False, True, False, True]
    return [True, False, True, False]


def make_pvt_stimuli(win):
    fixation = visual.TextStim(win, text="+", height=0.15, color="white")
    clock_face = visual.Circle(win, radius=0.3, edges=64, fillColor=None, lineColor="white", lineWidth=4)
    clock_hand = visual.Line(win, start=(0, 0), end=(0, 0.28), lineColor="white", lineWidth=6)
    instructions = visual.TextStim(
        win,
        text=(
            "Watch the clock.\n\n"
            "As soon as the hand starts moving, click the LEFT mouse button "
            "as fast as you can.\n\n"
            "Click the mouse button now to begin practice."
        ),
        height=0.06, wrapWidth=1.6, color="white",
    )
    probe_text = visual.TextStim(win, text="", height=0.06, wrapWidth=1.6, color="white", pos=(0, 0.3))
    break_text = visual.TextStim(win, text="", height=0.06, wrapWidth=1.6, color="white")
    progress_bar = visual.Rect(
        win, width=0, height=0.05, pos=(0, -0.85),
        lineColor="white", fillColor="white", autoDraw=False, name="pvt_progressbar"
    )
    return {
        "fixation": fixation, "clock_face": clock_face, "clock_hand": clock_hand,
        "instructions": instructions, "probe_text": probe_text, "break_text": break_text,
        "progress_bar": progress_bar,    
    }


def run_one_pvt_trial(win, stim, mouse):
    stim["fixation"].draw()
    win.flip()
    core.wait(PVT_FIXATION_DURATION)

    possible_delays = [
        PVT_MIN_DELAY + i * PVT_DELAY_STEP
        for i in range(int((PVT_MAX_DELAY - PVT_MIN_DELAY) / PVT_DELAY_STEP) + 1)
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
        keys = event.getKeys(keyList=["s", "escape"])
        if "escape" in keys:
            win.close()
            core.quit()
        if "s" in keys:
            return {"wait_time": wait_time, "rt_seconds": None, "false_start_count": false_start_count, "skip": True}

    mouse.clickReset()
    rt_clock = core.Clock()
    clicked = False
    rt = None

    while not clicked:
        elapsed = rt_clock.getTime()
        stim["clock_hand"].ori = (elapsed * PVT_CLOCK_ROTATION_SPEED) % 360
        stim["clock_face"].draw()
        stim["clock_hand"].draw()
        win.flip()

        if mouse.getPressed()[0]:
            rt = rt_clock.getTime()
            clicked = True

        if elapsed > 5.0:
            rt = None
            clicked = True
        
        keys = event.getKeys(keyList=["space", "escape"])
        if "escape" in keys:
            win.close()
            core.quit()
        if "s" in keys:
            return {"wait_time": wait_time, "rt_seconds": None, "false_start_count": false_start_count, "skip": True}

    stim["clock_face"].draw()
    stim["clock_hand"].draw()
    win.flip()
    core.wait(PVT_FEEDBACK_DURATION)

    win.flip()
    core.wait(PVT_BLANK_DURATION)

    return {
        "wait_time": wait_time,
        "rt_seconds": rt,
        "false_start_count": false_start_count,
        "skip": False,
    }


def run_pvt_thought_probe(win, stim):
    ratings = {}
    for statement in PVT_THOUGHT_PROBE_OPTIONS:
        prompt = (
            "Rate the following on a scale from 1 to 5:\n"
            "1 = Not at all    5 = Very much\n\n"
            f"\"{statement}\"\n\n"
            "Press a number key (1-5)."
        )
        stim["probe_text"].text = prompt
        stim["probe_text"].pos = (0, 0)
        stim["probe_text"].draw()
        win.flip()

        response = event.waitKeys(keyList=["1", "2", "3", "4", "5", "escape"])
        if "escape" in response:
            win.close()
            core.quit()
        ratings[statement] = response[0]

    return ratings
    


def run_pvt_break(win, stim, mouse,block_number, is_distraction_block):
    break_clock = core.Clock()
    while break_clock.getTime() < PVT_BREAK_DURATION_SECONDS:
        remaining = max(0, int(PVT_BREAK_DURATION_SECONDS - break_clock.getTime()))
        stim["break_text"].text = (
            f"Take a short break.\n\n"
            f"Block {block_number} of {PVT_N_BLOCKS} starts in {remaining} seconds..."
        )
        stim["break_text"].draw()
        win.flip()
        keys = event.getKeys(keyList=["space", "escape"])
        if "escape" in keys:
            win.close()
            core.quit()

    stim["break_text"].text = (
        f"Block {block_number} of {PVT_N_BLOCKS}\n\n"
        + "Click the mouse button when you are ready to continue."
    )
    wait_for_mouse_click(win, mouse, draw_each_frame=stim["break_text"])

PVT_FINAL_QUESTIONNAIRE_ITEMS = [
    "I was fantasizing or daydreaming",
    "My thoughts drifted into situations unrelated to the task",
    "I was distracted by environmental stimuli while in task",
    "I found my attention drawn away by something I saw, heard, noticed around me",
    "I was worried about my score on this test",
    "I was wondering about the result for my test",
    "I make my thoughts wonder so the task passes faster",
    "I make my thoughts wonder so the task is less boring",
    "I actively use the time in routine tasks to think about other things",
    "I was surprised that, for a few seconds, your mind was thinking about something else",
    "I had other thoughts randomly popping into my head during the task",
    "I realized my mind wandered for a long time without intending them to",
]

def run_pvt_final_questionnaire(win, stim):
    """Shown once at the end of the PVT task. Returns a list of
    {"item": ..., "response": ...} dicts, one per statement."""
    responses = []

    intro = visual.TextStim(
        win,
        text=(
            "Before you finish, please answer a few questions about your\n"
            "thoughts during the task you just completed.\n\n"
            "For each statement, rate how much it applied to you,\n"
            "from 1 (Not at all) to 5 (Very much).\n\n"
            "Press SPACEBAR to begin."
        ),
        height=0.06, wrapWidth=1.6, color="white",
    )
    intro.draw()
    win.flip()
    keys = event.waitKeys(keyList=["space", "escape"])
    if "escape" in keys:
        win.close()
        core.quit()

    for i, item_text in enumerate(PVT_FINAL_QUESTIONNAIRE_ITEMS):
        prompt = (
            f"({i + 1} of {len(PVT_FINAL_QUESTIONNAIRE_ITEMS)})\n\n"
            f"\"{item_text}\"\n\n"
            "1 = Not at all        5 = Very much\n\n"
            "Press a number key (1-5)."
        )
        stim["probe_text"].text = prompt
        stim["probe_text"].pos = (0, 0)
        stim["probe_text"].draw()
        win.flip()

        response = event.waitKeys(keyList=["1", "2", "3", "4", "5", "escape"])
        if "escape" in response:
            win.close()
            core.quit()

        responses.append({"item": item_text, "response": response[0]})

    return responses

def save_pvt_final_questionnaire_to_excel(participant_id, responses):
    participant_folder = get_participant_folder()
    os.makedirs(participant_folder, exist_ok=True)
    filename = os.path.join(participant_folder, f"{participant_id}_pvt_final_questionnaire.xlsx")

    df = pd.DataFrame(responses)
    df.index = range(1, len(df) + 1)
    df.index.name = "Item Number"

    with pd.ExcelWriter(filename, engine="openpyxl") as writer:
        df.to_excel(writer, sheet_name="final_questionnaire", index=True)

    print(f"PVT final questionnaire saved to {filename}")

def make_pvt_data_writer(participant_id):
    participant_folder = get_participant_folder()
    os.makedirs(participant_folder, exist_ok=True)
    filename = os.path.join(participant_folder, f"{participant_id}_pvt_clock.csv")
    csv_file = open(filename, mode="w", newline="")
    writer = csv.writer(csv_file)
    writer.writerow([
        "block_number", "distraction_condition", "trial_number", "wait_time_seconds",
        "rt_seconds", "false_start_count", "trial_type",
        "probe_disengaged_rating", "probe_focused_rating", "probe_distracted_rating",
    ])
    csv_file.flush()
    return csv_file, writer


def write_pvt_data_row(csv_file, writer, row):
    writer.writerow(row)
    csv_file.flush()


def run_pvt_task():
    """The PVT section. Uses the shared `win` / `mouse`. Returns 'done'."""
    global participant_data

    block_order = get_pvt_block_order(session_value)

    stim = make_pvt_stimuli(win)
    csv_file, writer = make_pvt_data_writer(participant_data["participant_id"])

    print("Starting PVT task...")
    section_label = f"SECTION {section_number} of {total_sections}\n\n" if section_number else ""

    # --- progress bar geometry (matches 2AFC style) ---
    pb_cx, pb_cy = 0, -0.85
    pb_finalwidth = 1.4
    pb_left = pb_cx - (pb_finalwidth / 2)
    total_main_trials = PVT_N_BLOCKS * PVT_N_TRIALS_PER_BLOCK
    overall_trial_counter = 0

    try:
        wait_for_mouse_click(win, mouse, draw_each_frame=stim["instructions"])

        for _ in range(PVT_N_PRACTICE_TRIALS):
            run_one_pvt_trial(win, stim, mouse)

        for block_index in range(PVT_N_BLOCKS):
            is_distraction_block = block_order[block_index]
            run_pvt_break(win, stim, mouse, block_index + 1, is_distraction_block)

            probe_after_trials = set(
                random.sample(range(PVT_N_TRIALS_PER_BLOCK), PVT_THOUGHT_PROBES_PER_BLOCK)
            )

            for trial_index in range(PVT_N_TRIALS_PER_BLOCK):
                trial_data = run_one_pvt_trial(win, stim, mouse)

                write_pvt_data_row(csv_file, writer, [
                    block_index + 1, is_distraction_block, trial_index + 1,
                    trial_data["wait_time"], trial_data["rt_seconds"],
                    trial_data["false_start_count"],
                    "trial_skipped" if trial_data.get("skip") else "trial", "", "", "",
                ])

            # --- advance progress bar on any button press: a genuine click OR a skip ---
            button_was_pressed = (trial_data["rt_seconds"] is not None) or trial_data.get("skip", False)
            if button_was_pressed:
                overall_trial_counter += 1
                progress = overall_trial_counter / float(total_main_trials) if total_main_trials > 0 else 1.0
                progress = min(progress, 1.0)
                pb_width = pb_finalwidth * progress
                stim["progress_bar"].width = pb_width
                stim["progress_bar"].pos = (pb_left + pb_width / 2, pb_cy)
            
                if trial_data.get("skip"):
                    print(f"Block {block_index + 1} skipped by user at trial {trial_index + 1}; moving to next block.")
                    break

                if trial_index in probe_after_trials:
                    probe_ratings = run_pvt_thought_probe(win, stim)
                    write_pvt_data_row(csv_file, writer, [
                        block_index + 1, is_distraction_block, trial_index + 1,
                        "", "", "", "thought_probe",
                        probe_ratings[PVT_THOUGHT_PROBE_OPTIONS[0]],
                        probe_ratings[PVT_THOUGHT_PROBE_OPTIONS[1]],
                        probe_ratings[PVT_THOUGHT_PROBE_OPTIONS[2]],
                    ])


        stim["progress_bar"].autoDraw = False
        questionnaire_responses = run_pvt_final_questionnaire(win, stim)
        save_pvt_final_questionnaire_to_excel(participant_data["participant_id"], questionnaire_responses)
        participant_data["pvt_final_questionnaire"] = questionnaire_responses
        goodbye = visual.TextStim(win, text="Thank you - this part of the study is complete.", height=0.07, color="white")
        goodbye.draw()
        win.flip()
        core.wait(2.0)

        print("PVT task completed successfully.")
        return "done"

    finally:
        csv_file.close()


# =====================================================================
# SECTION Parity 
# =====================================================================

def get_section_order_for_participant(participant_id):
    """Even-numbered participant IDs do 2AFC first; odd-numbered IDs do PVT first.
    Pulls the numeric portion out of the ID (e.g. 'P014' -> 14) so IDs with
    letters/prefixes still work. Falls back to a random order if no digits
    are found in the ID at all."""
    digits = "".join(ch for ch in participant_id if ch.isdigit())
    if digits == "":
        print(f"Warning: no digits found in participant ID '{participant_id}'; using random section order.")
        sections = [
            ("2AFC", crossmodal_with_feedback),
            ("PVT", run_pvt_task),
        ]
        random.shuffle(sections)
        return sections

    id_number = int(digits)
    if id_number % 2 == 0:
        return [("2AFC", crossmodal_with_feedback), ("PVT", run_pvt_task)]
    else:
        return [("PVT", run_pvt_task), ("2AFC", crossmodal_with_feedback)]

def run_experiment_sections():
    """Randomly orders the 2AFC and PVT sections, runs them in that order,
    and records which order was used."""
    global participant_data

    sections = get_section_order_for_participant(participant_data["participant_id"])

    section_order = [name for name, _ in sections]
    participant_data["section_order"] = section_order
    print(f"Section order for this participant: {section_order}")
    total_sections = len(sections)

    show_overall_welcome()

    for i, (name, func) in enumerate(sections):
        section_number = i + 1
        print(f"--- Starting section: {name} (Section {section_number} of {total_sections}) ---")
        result = func(section_number=section_number, total_sections=total_sections)
        if result == "skip":
            print(f"{name} section skipped.")
        else:
            print(f"{name} section completed.")
        if name == "2AFC":
            save_crossmodal_with_feedback_to_excel()
    return section_order



# =====================================================================
# MAIN EXPERIMENT FLOW
# =====================================================================

participant_id = get_participant_id()
session_value = input("PVT Session (1 or 2, for block-order counterbalancing): ").strip() or "1"
participant_data = {
    "participant_id": participant_id,
    "task order": "",
    "crossmodal with feedback correct": 0,
    "crossmodal with feedback incorrect": 0,
    "reaction time": [],
    "crossmodal_wf_log": [],
    "free_pairings": [],
    "confidence_responses": [],
    "section_order": [],
}

script_dir = os.path.dirname(os.path.abspath(__file__))
image_dir = os.path.join(script_dir, "generated_shapes")
audio_dir = os.path.join(script_dir, "generated_sounds")

try:
    win = visual.Window(fullscr=True, color="gray", units="norm", allowGUI=True)
    win.mouseVisible = True
except Exception as e:
    print(f"Error creating window: {str(e)}")
    core.quit()

mouse = event.Mouse(win=win)
main_sounds = preload_sounds(audio_dir)

# Run both sections in parity
run_experiment_sections()

# Final save (redundant but safe)
save_crossmodal_with_feedback_to_excel()

# Save section order alongside other run metadata
try:
    participant_folder = get_participant_folder()
    order_df = pd.DataFrame({"section_order": participant_data["section_order"]})
    order_df.to_csv(os.path.join(participant_folder, "section_order.csv"), index=False)
except Exception as e:
    print(f"Could not save section order: {e}")

# Cleanup
win.close()
core.quit()

