#!/usr/bin/env python
# coding: utf-8

# In[1]:


# --- Setup & imports ---
from psychopy import prefs  # set audio backend before importing sound
prefs.hardware['audioLib'] = ['pygame', 'sounddevice']
prefs.general['audioDevice'] = ['default']

import os
os.environ["QT_QPA_PLATFORM"] = "cocoa"  # macOS GUI fix (safe elsewhere too)

import random
import pandas as pd
import numpy as np
import traceback

from itertools import combinations
from psychopy import visual, core, event, sound

from psychopy import logging
logging.console.setLevel(logging.ERROR)  # suppresses certain warnings
import warnings
warnings.filterwarnings("ignore", message="elementwise comparison failed")

print("Current working directory:", os.getcwd())

# === Collect participant ID and set up directories before anything else ===
def get_participant_id():
    participant_id = input("Enter Participant ID: ").strip()

    # Create participant data folder if it doesn't exist
    participant_folder = os.path.join("./participant_data", participant_id)
    if not os.path.exists(participant_folder):
        os.makedirs(participant_folder)
    else:
        # Always overwrite existing data
        for file in [f for f in os.listdir(participant_folder) if os.path.isfile(os.path.join(participant_folder, f))]:
            os.remove(os.path.join(participant_folder, file))

    return participant_id

# === Instruction helper ===
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

# === Non-negative values for ISI and ITI helper function ===

# Make Gaussian Distrubution of Fixation Durations
mean_ITI = 0.5
sd_ITI = 0.2
n_ITI = 150

mean_ISI = 0.5
sd_ISI = 0.2
n_ISI = 150

def sample_non_negative_normal(mean, std, size):
    samples = np.random.normal(mean, std, size)
    while np.any(samples < 0):  # Re-sample until no negative values
        samples[samples < 0] = np.random.normal(mean, std, np.sum(samples < 0))
    return samples

interTrialPause = sample_non_negative_normal(mean_ITI, sd_ITI, n_ITI)
interStimulusPause = sample_non_negative_normal(mean_ISI, sd_ISI, n_ISI)

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

# === Save helpers ===

def save_crossmodal_with_feedback_to_excel():
    participant_folder = os.path.join("./participant_data", participant_data["participant_id"])
    os.makedirs(participant_folder, exist_ok=True)
    excel_filename = os.path.join(participant_folder, "crossmodal_wf_log.xlsx")
    
    df = pd.DataFrame(participant_data.get("crossmodal_wf_log", []))
    pause_df = pd.DataFrame(participant_data.get("crossmodal_pause_durations", []))

    confidence_df = pd.DataFrame(participant_data.get("confidence_responses", []))

    with pd.ExcelWriter(excel_filename, engine="openpyxl") as writer:
        df.to_excel(writer, sheet_name="trial_log", index=False)
        pause_df.to_excel(writer, sheet_name="pause_summary", index=False)
        confidence_df.to_excel(writer, sheet_name="confidence_responses", index=False)

    print(f"Crossmodal with feedback data saved to {excel_filename}")

def save_unimodal_to_excel(matrix, trial_log, stimuli, duration, label, order):
    try:
        # --- paths ---
        participant_folder = os.path.join("./participant_data", participant_data["participant_id"])
        os.makedirs(participant_folder, exist_ok=True)
        filename = os.path.join(participant_folder, f"Unimodal_{label}s_({order}).xlsx")

        # --- matrix → DataFrame (square, labels from stimuli) ---
        n = len(stimuli)
        matrix_df = pd.DataFrame(matrix, index=stimuli, columns=stimuli)

        # --- trial log mapping (indices → names OR pass-through if already names) ---
        def name_of(x):
            return stimuli[x] if isinstance(x, int) else x

        trial_rows = [[name_of(t[0]), name_of(t[1]), name_of(t[2]), name_of(res)]
                      for t, res in trial_log]

        trial_cols = [f"{label} 1", f"{label} 2", f"{label} 3", f"Chosen {label}"]
        trial_log_df = pd.DataFrame(trial_rows, columns=trial_cols)
        trial_log_df.index = range(1, len(trial_rows) + 1)
        trial_log_df.index.name = "Trial Number"

        # --- meta info at top of Trials sheet ---
        meta_df = pd.DataFrame({
            "Duration (s)": [duration],
            "Order": [order],
            "N stimuli": [n],
        })

        with pd.ExcelWriter(filename, engine="openpyxl") as writer:
            # Trials sheet: meta first, blank row, then table
            meta_df.to_excel(writer, sheet_name="Trials", index=False, startrow=0)
            trial_log_df.to_excel(writer, sheet_name="Trials", index=True, startrow=len(meta_df) + 2)

            # Matrix sheet
            matrix_df.to_excel(writer, sheet_name="Difference_Scores", index=True)

            # Stimuli sheet (for traceability)
            pd.DataFrame({"Stimulus": stimuli}).to_excel(writer, sheet_name="Stimuli", index=True)

        print(f"Data successfully saved to {filename}")
    except Exception as e:
        print(f"Could not save matrix to Excel ({e}).")

import random
import numpy as np
from itertools import combinations

import random
import numpy as np
from itertools import combinations
    

# === End-of-experiment survey ===
def run_end_survey():
    """Prompt participant for survey responses on the PsychoPy window and save to Excel."""
    survey_questions = [
        "Which features of the shapes did you focus on to help with learning?",
        "Which features of the sounds did you focus on to help with learning?",
        "Were certain shape–sound pairings easier to remember than others? Why?",
        "Did you use any specific strategies to remember the pairings?",
        "Did you notice any patterns in the stimuli that helped you?",
        "How confident were you in your answers during the test section? Why?",
        "Did your strategy change across the sections? If so, how and why?",
        "What did you find most challenging about the task?",
        "Did you rely more on intuition or logic when making your choices?",
        "Did you imagine any associations (e.g., stories, categories) to help remember the pairs?",
        "Any additional comments about how you approached the task?",
    ]
    responses = []
    instr = visual.TextStim(
        win,
        text="End Survey\n\nType your answer and press ENTER to continue.\n(Use BACKSPACE to edit)",
        color="lightgrey",
        height=0.06,
        wrapWidth=1.6,
        pos=(0, 0.7)
    )
    question_stim = visual.TextStim(win, text="", color="white", height=0.055, wrapWidth=1.6, pos=(0, 0.3))
    answer_stim = visual.TextStim(win, text="", color="yellow", height=0.055, wrapWidth=1.6, pos=(0, -0.2))

    for q in survey_questions:
        answer = ""
        question_stim.text = q
        while True:
            instr.draw()
            question_stim.draw()
            answer_stim.text = answer + "|"
            answer_stim.draw()
            win.flip()
            keys = event.waitKeys()
            commit = False
            for key in keys:
                if key == "return":
                    responses.append(answer)
                    commit = True
                    break
                elif key == "backspace":
                    answer = answer[:-1]
                elif key == "space":
                    answer += " "
                elif key == "escape":
                    win.close()
                    core.quit()
                elif len(key) == 1:
                    answer += key
            if commit:
                break

    # Save responses to Excel
    try:
        df = pd.DataFrame({"question": survey_questions, "response": responses})
        participant_folder = os.path.join("./participant_data", participant_data["participant_id"])
        os.makedirs(participant_folder, exist_ok=True)
        excel_path = os.path.join(participant_folder, "end_survey.xlsx")
        df.to_excel(excel_path, index=False)
        print(f"Survey responses saved to {excel_path}")
    except Exception as e:
        print(f"Could not save survey to Excel: {e}")

def ask_confidence_question(checkpoint_label):
    """Show a single typed-response question and store it under participant_data['confidence_responses']."""
    question_text = "How confident are you in your answers so far?\n\nType your response and press ENTER."
    instr = visual.TextStim(win, text=question_text, color="white", height=0.06, wrapWidth=1.6, pos=(0, 0.3))
    answer_stim = visual.TextStim(win, text="", color="yellow", height=0.055, wrapWidth=1.6, pos=(0, -0.2))

    answer = ""
    while True:
        instr.draw()
        answer_stim.text = answer + "|"
        answer_stim.draw()
        win.flip()
        keys = event.waitKeys()
        commit = False
        for key in keys:
            if key == "return":
                commit = True
                break
            elif key == "backspace":
                answer = answer[:-1]
            elif key == "space":
                answer += " "
            elif key == "escape":
                win.close()
                core.quit()
            elif len(key) == 1:
                answer += key
        if commit:
            break

    participant_data.setdefault("confidence_responses", []).append({
        "checkpoint": checkpoint_label,
        "response": answer
    })
    print(f"Confidence response recorded at {checkpoint_label}: {answer}")

# === Advanced end of survey experiment ===
def run_end_survey_adv():    
    survey_questions = [
        "Which features of the shapes did you focus on to help with learning?",
        "Which features of the sounds did you focus on to help with learning?",
        "Were certain shape–sound pairings easier to remember than others? Why?",
        "Did you use any specific strategies to remember the pairings?",
        "Did you notice any patterns in the stimuli that helped you?",
        "How confident were you in your answers during the testing section? Why?",
        "Did your strategy change across the sections? If so, how and why?",
        "What did you find most challenging about the task?",
        "Did you rely more on intuition or logic when making your choices?",
        "Did you imagine any associations (e.g., stories, categories) to help remember the pairs?",
    ]
    
    title = visual.TextStim(win, text="End of Experiment Survey", pos=(0, 0.65), height=0.1, bold=True)
    qnum = visual.TextStim(win, text="", pos=(0, 0.52), height=0.06, color="#000000")
    qtext = visual.TextStim(win, text="", pos=(0, 0.40), height=0.08, wrapWidth=1.6)
    
    # TextBox2 may not be available in older PsychoPy versions; fall back to the simple text survey
    try:
        textbox = visual.TextBox2(
            win,
            text="",
            pos=(0, -0.2),
            units="norm",
            size=(1.6, 0.65),
            letterHeight=0.07,
            editable=True,
            color='black',
            )
    except Exception as e:
        print(f"TextBox2 failed to initialize ({e}); falling back to basic end-survey.")
        return run_end_survey()
    
    tb_border = visual.Rect(
        win, units="norm",
        width=1.6, height=0.65, pos=(0, -0.2),
        lineColor='white', lineWidth=2, fillColor="#C2C2C2"
        )

    # Buttons
    def button(label, center_pos):
        padding = (0.08, 0.035)
        w, h = padding[0] * 2.4, padding[1] * 2.4
        rect = visual.Rect(win, width=w, height=h, pos=center_pos, fillColor="#4C7BF1", lineColor=None, opacity=1)
        text = visual.TextStim(win, text=label, pos=center_pos, height=0.06, color="white")
        return rect, text
    
    # Makes the buttons
    back_rect, back_text = button("Back", (-0.15, -0.65))
    next_rect, next_text = button("Next", (0.15, -0.65))
    finish_rect, finish_text = button("Finish", (0.15, -0.65))
    esc_text = visual.TextStim(win, text="Press Esc to cancel", pos=(0, -0.82), height=0.06, color="white")

    mouse = event.Mouse(win=win)
    responses = ["" for _ in survey_questions]
    idx = 0
    nQ = len(survey_questions)

    # Restore text when moving between questions
    def load_q(i):
        qnum.text = f"Question {i+1} of {nQ}"
        qtext.text = survey_questions[i]
        textbox.editable = False
        textbox.setText(responses[i] or "")
        textbox.editable = True

    load_q(idx)

    while True:
        # --- Draw frame ---
        title.draw()
        qnum.draw()
        qtext.draw()
        tb_border.draw()
        textbox.draw()
        esc_text.draw()

        # draw correct buttons depending on position
        if idx > 0:
            back_rect.draw(); back_text.draw()
        if idx < nQ - 1:
            next_rect.draw(); next_text.draw()
        else:
            finish_rect.draw(); finish_text.draw()

        win.flip()
        
        if len(textbox.text) > 480:
            textbox.setText(textbox.text[:480])

        # Handle mouse clicks
        if mouse.getPressed()[0]:
            mpos = mouse.getPos()
            clicked = False

            # Back
            if idx > 0:
                if (abs(mpos[0] - back_rect.pos[0]) <= back_rect.width/2) and (abs(mpos[1] - back_rect.pos[1]) <= back_rect.height/2):
                    responses[idx] = textbox.text
                    idx -= 1
                    load_q(idx)
                    clicked = True

            # Next / Finish
            target_rect = next_rect if idx < nQ - 1 else finish_rect
            if (abs(mpos[0] - target_rect.pos[0]) <= target_rect.width/2) and (abs(mpos[1] - target_rect.pos[1]) <= target_rect.height/2):
                responses[idx] = textbox.text
                if idx < nQ - 1:
                    idx += 1
                    load_q(idx)
                else:
                    break
                clicked = True

            # Anti-sticky click: wait for release
            if clicked:
                while mouse.getPressed()[0]:
                    win.flip()

        # Handle keys
        keys = event.getKeys(modifiers=True, timeStamped=False)
        
        for k in keys:
            if isinstance(k, tuple):
                key, mods = k
            else:
                key, mods = k, []

            # Quit
            if key == "escape":
                if key == "escape":
                    textbox.editable = False
                    core.quit()
    # Finished
    textbox.editable = False
    try:
        df = pd.DataFrame({"question": survey_questions, "response": responses})
        participant_folder = os.path.join("./participant_data", participant_data["participant_id"])
        os.makedirs(participant_folder, exist_ok=True)
        excel_path = os.path.join(participant_folder, "end_survey.xlsx")
        df.to_excel(excel_path, index=False)
        print(f"Survey responses saved to {excel_path}")
    except Exception as e:
        print(f"Could not save survey to Excel: {e}")

# === Presentation timing constants ===
STIMULUS_DURATION = 1.0  # seconds, all shapes and sounds
FIXATION_DURATION = 0.5  # seconds, all fixations

# === Stimulus pair definitions ===
stimuli_pairs = [
    ("shape_01.png", "sound_01.wav"),
    ("shape_02.png", "sound_02.wav"),
    ("shape_03.png", "sound_03.wav"),
    ("shape_04.png", "sound_04.wav"),
    ("shape_05.png", "sound_05.wav"),
    ("shape_06.png", "sound_06.wav"),
    ("shape_07.png", "sound_07.wav"),
    ("shape_08.png", "sound_08.wav"),
    ("shape_09.png", "sound_09.wav"),
    ("shape_10.png", "sound_10.wav"),
]

# === Preload all sound objects ===
def preload_sounds(audio_dir):
    sound_dict = {}
    for fname in sorted([f for f in os.listdir(audio_dir) if f.startswith("sound_") and f.endswith(".wav")]):
        sound_dict[fname] = sound.Sound(os.path.join(audio_dir, fname))
    return sound_dict



# === Helper function for caluclating difficylty of a crossmodal trial ===
def crossWF_calc_trial_diff(sound1,sound2):
    idx1 = int(sound1.split('_')[1].split('.')[0])
    idx2 = int(sound2.split('_')[1].split('.')[0])
    difficulty = 9 - abs(idx1 - idx2)
    return difficulty

# === Helper function for making crossmodal with feedback trials ===
def crossWF_pick_incorrect_tone(correct_tone, available_tones, current_diff, trial_num):
    attempts = 0
    while attempts < 30: # avoid infinite loops
        attempts += 1
        candidate = random.choice(available_tones)
        trial_diff = crossWF_calc_trial_diff(correct_tone, candidate)
        if ((current_diff + trial_diff) / trial_num) < 5 and ((current_diff + trial_diff) / trial_num) > 3:
            return candidate, trial_diff
    return candidate, trial_diff

# === Crossmodal with feedback ===
def crossmodal_with_feedback():
    global participant_data
    participant_data["task order"] = "active"
    participant_data["crossmodal_wf_log"] = []
    participant_data["crossmodal_pause_durations"] = []
    event.clearEvents()

    print("Starting Crossmodal with feedback...")

    instruction_result = show_instructions(
        "INSTRUCTIONS – Learning Task\n\n"
        "In this section, you’ll see a SHAPE and hear a SOUND together.\n\n"
        "The same shape will be presented twice, each time with a different sound.\n"
        "Press ‘1’ with your LEFT index finger if the FIRST pair is correct.\n"
        "Press ‘0’ with your RIGHT index finger if the SECOND pair is correct.\n\n"
        "You’ll get FEEDBACK after each response.\n\n"
        "The correct pairings have been pre-assigned and are NOT based on the pairings you made previously.\n\n"
        "Please focus on learning the correct pairings.\n\n"
        "Try to respond as accurately and quickly as possible.\n\n"
        "Press SPACEBAR to begin.",
        ["space"]
    )
    if instruction_result == "s":
        print("Crossmodal with feedback skipped.")
        return "skip"

    try:
        print("Entering trial loop for Crossmodal with feedback...")
        local_stimuli = list(stimuli_pairs)
        crossmodal_trials = []

        # For each pair, create (approximately) balanced congruent-first vs congruent-second
        TRIALS_PER_PAIR = 15
        all_tones = [pair[1] for pair in stimuli_pairs]

        for img_file, audio_file in local_stimuli:
            available_tones = [snd for snd in all_tones if snd != audio_file]
            total_diff = 0
            # 7 of each order, and 1 extra randomly to total 15
            for i in range(TRIALS_PER_PAIR // 2):
                # Congruent first
                incorrect_tone, trial_diff = crossWF_pick_incorrect_tone(audio_file, available_tones, total_diff, ((i+1)*2)-1)
                total_diff += trial_diff
                crossmodal_trials.append((img_file, audio_file, [audio_file, incorrect_tone]))
                # Congruent second
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
            win,
            text="Press 1 (LEFT index) if FIRST pair is correct;\nPress 0 (RIGHT index) if SECOND pair is correct.",
            color="white", height=0.05, pos=(0, 0)
        )

        img_stim_left = visual.ImageStim(win, image=None, size=(0.3, 0.4), pos=(-0.5, 0))
        img_stim_right = visual.ImageStim(win, image=None, size=(0.3, 0.4), pos=(0.5, 0))

        # Make the progress bar
        cx, cy = 0, -0.6
        finalwidth = 1.4
        left = cx - (finalwidth / 2)
        progress_bar = visual.Rect(
            win,
            width=0, height=0.05,  # start at 0%
            pos=(cx, cy),
            lineColor="white", fillColor="white",
            autoDraw=False, name="progressbar"
        )

        # Stimulus parameters
        STIMULUS_DURATION = 1.0  # Keep it as 1.0s for crossmodal block

        # Generate non-negative Gaussian jitters centered at 500 ms
        interTrialPause = sample_non_negative_normal(mean_ITI, sd_ITI, len(crossmodal_trials))
        interStimulusPause = sample_non_negative_normal(mean_ISI, sd_ISI, len(crossmodal_trials))

        # Record distribute information
        participant_data["crossmodal_pause_durations"].append({
            "interStimulusPause_mean": float(np.mean(interStimulusPause)),
            "interStimulusPause_std": float(np.std(interStimulusPause, ddof=0)),
            "interStimulusPause_min": float(np.min(interStimulusPause)),
            "interStimulusPause_max": float(np.max(interStimulusPause)),

            "interTrialPause_mean": float(np.mean(interTrialPause)),
            "interTrialPause_std": float(np.std(interTrialPause, ddof=0)),
            "interTrialPause_min": float(np.min(interTrialPause)),
            "interTrialPause_max": float(np.max(interTrialPause)),
        })

        for trial_index, (img_file, audio_file, tones) in enumerate(crossmodal_trials):
            event.clearEvents()
            if "escape" in event.getKeys(keyList=["escape"]):
                win.close()
                core.quit()
            if "s" in event.getKeys(keyList=["s"]):
                return "skip"

            trial_clock = core.Clock()
            image_path = os.path.join(image_dir, img_file)
            trial_difficulty = crossWF_calc_trial_diff(tones[0], tones[1])
            response_state = {"response": None, "reaction_time": None, "skip": False}

            # Update progress bar
            progress = trial_index / float((TRIALS_PER_PAIR * 10) - 1)  # progress fraction (0–1)
            width = finalwidth * progress
            progress_bar.width = width
            progress_bar.pos = (left + width/2,cy)
            progress_bar.autoDraw = True
            win.flip()

            # 1) Inter-Trial jitter (0.5s mean)
            win.flip()
            core.wait(interTrialPause[trial_index])

            # 2) shape + sound 1 (left) (0.5s)
            img_stim_left.image = image_path
            img_stim_left.draw()
            win.flip()
            trial_clock.reset() 
            main_sounds[tones[0]].stop()
            main_sounds[tones[0]].play()
            wait_and_listen(STIMULUS_DURATION, response_state, trial_clock)
            if response_state["skip"]:
                return "skip"

            # 3) fixation (0.5s)
            fixation.pos = (0, 0)
            fixation.draw()
            win.flip()
            wait_and_listen(FIXATION_DURATION, response_state, trial_clock)
            if response_state["skip"]:
                return "skip"

            # 4) Inter-Stimulus jitter (0.5s mean)
            win.flip()
            wait_and_listen(interStimulusPause[trial_index], response_state, trial_clock)
            if response_state["skip"]:
                return "skip"

            # 5) shape + sound 2 (right) (0.5s)
            img_stim_right.image = image_path
            img_stim_right.draw()
            win.flip()
            main_sounds[tones[1]].stop()
            main_sounds[tones[1]].play()
            wait_and_listen(STIMULUS_DURATION, response_state, trial_clock)
            if response_state["skip"]:
                return "skip"

            # Response
            prompt_sound2.draw()
            win.flip()

            if response_state["response"] is None:
                wait_and_listen(4, response_state, trial_clock)
                if response_state["skip"]:
                    return "skip"

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
            
            core.wait(0.5) # FEEDBACK DURATION (0.5s)

            # Record trial data
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
                "interStimulusPause": float(interStimulusPause[trial_index]),
                "interTrialPause": float(interTrialPause[trial_index])
            })

            # Mid-experiment confidence check (after 75 trials)
            if trial_index == 74:
                ask_confidence_question("midpoint")

        progress_bar.autoDraw = False
        ask_confidence_question("end")
        end_msg = visual.TextStim(
            win,
            text="You have completed this section.\n\nPress SPACEBAR to continue.",
            color="lightgrey", height=0.06, pos=(0, 0)
        )
        end_msg.draw()
        win.flip()
        event.waitKeys(keyList=["space"])

        print("Crossmodal with feedback completed successfully.")
        return "done"

    except Exception as e:
        print("Error during crossmodal with feedback:")
        traceback.print_exc()
        core.quit()


 

# === Helper function to highlight a note stimulus ===
def highlight_note(note_stim, on=True, color='red', scale=1.15):
    w, h = note_stim.size
    return visual.Rect(
        win,
        width=w * scale,
        height=h * scale,
        lineColor=color if on else None,
        lineWidth=3 if on else 0,
        fillColor=None,
        pos=note_stim.pos,
    )

# === Always collect participant ID and set up paths before anything else ===
participant_id = get_participant_id()
participant_data = {
    "participant_id": participant_id,
    "task order": "",
    "crossmodal with feedback correct": 0,
    "crossmodal with feedback incorrect": 0,
    "reaction time": [],
    "crossmodal_wf_log": [],
    "free_pairings": [],
    "confidence_responses": [],
}

# Set image/audio directories (adjust as needed for your experiment)
script_dir = os.path.dirname(os.path.abspath(__file__))
image_dir = os.path.join(script_dir, "generated_shapes")
audio_dir = os.path.join(script_dir, "generated_sounds")

# === Create PsychoPy window early so it's available for all functions ===
try:
    win = visual.Window(fullscr=True, color="gray", units="norm", allowGUI=True)
except Exception as e:
    print(f"Error creating window: {str(e)}")
    core.quit()


# === Preload audio ===
main_sounds = preload_sounds(audio_dir)

# === Experiment flow ===

# Crossmodal with Feedback (keys: 1 = FIRST, 0 = SECOND; use left/right index fingers)
result = crossmodal_with_feedback()
if result == "skip":
    print("Crossmodal with feedback skipped.")
save_crossmodal_with_feedback_to_excel()

# End Survey
run_end_survey_adv()

# Save again (redundant but safe)
save_crossmodal_with_feedback_to_excel()

# Cleanup
win.close()
core.quit()


# In[ ]:




