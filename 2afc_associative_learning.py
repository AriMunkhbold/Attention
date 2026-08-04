"""
2AFC Shape-Sound Associative Learning Task (all-in-one)
----------------------------------------------------------------


  PART A - STIMULUS GENERATION (runs automatically if stimuli don't exist yet)
    Generates N random "sharp" (angular/spiky) shape images and N random
    pure-tone sounds within the audible range, randomly pairs them 1:1,
    and saves everything under stimuli/.

  PART B - THE TASK
    Ground truth: each shape has ONE correct sound (from Part A).
    On each trial, the participant sees two shapes on screen (left/right).
    Each shape's sound is played (left shape's sound, then right shape's
    sound). ONE of the two shape-sound PAIRINGS shown is correct (matches
    the true association); the other is a foil (a shape paired with a
    sound that is not its true match). The participant chooses which SIDE
    shows the correct pairing, and gets feedback after every response.

"""

import os
import random
import csv
import json
from datetime import datetime

import numpy as np


# =====================================================================
# PART A - STIMULUS GENERATION CONFIG
# =====================================================================

N_STIMULI = 12              # number of shape-sound pairs to generate
GEN_SEED = 42                # set to None for a fresh random stimulus set each time

IMG_DIR = os.path.join("stimuli", "images")
SND_DIR = os.path.join("stimuli", "sounds")
ASSOCIATIONS_PATH = os.path.join("stimuli", "associations.json")

# --- Shape params ---
N_VERTICES_RANGE = (7, 12)     # more vertices = more "spikes"
RADIUS_RANGE = (0.3, 1.0)      # min/max radius (relative units); bigger swing = sharper look
IMG_SIZE_PX = 400
SHAPE_COLOR = "black"
BG_COLOR = "white"

# --- Sound params (pure tones) ---
FREQ_RANGE_HZ = (250, 4000)    # comfortable, clearly audible sub-range of 20-20000 Hz
MIN_FREQ_SEPARATION_HZ = 200   # keep tones easily discriminable from each other
DURATION_SEC = 0.5
SAMPLE_RATE = 44100
FADE_MS = 15                   # fade in/out to avoid audio clicks
VOLUME = 0.5                   # 0-1, avoid clipping/loudness


# ---------------------------------------------------------------
# Shape generation
# ---------------------------------------------------------------

def generate_sharp_shape(n_vertices, rng):
    """
    Create a random angular/spiky polygon by picking a random radius at
    each of n_vertices evenly-spaced angles around a circle, then
    connecting the points with straight lines (no smoothing -> sharp
    corners).
    """
    angles = np.linspace(0, 2 * np.pi, n_vertices, endpoint=False)
    angles = angles + rng.uniform(-0.15, 0.15, size=n_vertices)
    radii = rng.uniform(RADIUS_RANGE[0], RADIUS_RANGE[1], size=n_vertices)

    x = radii * np.cos(angles)
    y = radii * np.sin(angles)
    return x, y


def save_shape_image(x, y, filepath):
    import matplotlib.pyplot as plt
    fig, ax = plt.subplots(figsize=(IMG_SIZE_PX / 100, IMG_SIZE_PX / 100), dpi=100)
    ax.fill(x, y, color=SHAPE_COLOR)
    ax.set_xlim(-1.2, 1.2)
    ax.set_ylim(-1.2, 1.2)
    ax.set_aspect("equal")
    ax.axis("off")
    fig.patch.set_facecolor(BG_COLOR)
    ax.set_facecolor(BG_COLOR)
    fig.savefig(filepath, facecolor=BG_COLOR, bbox_inches="tight", pad_inches=0.1)
    plt.close(fig)


# ---------------------------------------------------------------
# Sound generation
# ---------------------------------------------------------------

def generate_tone_frequencies(n, rng):
    """
    Pick n frequencies within FREQ_RANGE_HZ that are each at least
    MIN_FREQ_SEPARATION_HZ apart, so tones remain discriminable.

    Uses stratified sampling: evenly spaces n slots across the range,
    then jitters each point within its slot by an amount small enough
    to guarantee the minimum separation is preserved.
    """
    low, high = FREQ_RANGE_HZ
    span = high - low
    spacing = span / (n - 1) if n > 1 else 0

    if spacing < MIN_FREQ_SEPARATION_HZ:
        raise RuntimeError(
            f"FREQ_RANGE_HZ span ({span} Hz) is too narrow to fit {n} tones "
            f"with {MIN_FREQ_SEPARATION_HZ} Hz separation. Widen FREQ_RANGE_HZ "
            f"or lower MIN_FREQ_SEPARATION_HZ."
        )

    max_jitter = (spacing - MIN_FREQ_SEPARATION_HZ) / 2
    base_points = low + spacing * np.arange(n)
    jitter = rng.uniform(-max_jitter, max_jitter, size=n) if max_jitter > 0 else 0
    freqs = list(base_points + jitter)
    rng.shuffle(freqs)
    return freqs


def save_tone_wav(freq_hz, filepath):
    from scipy.io import wavfile
    t = np.linspace(0, DURATION_SEC, int(SAMPLE_RATE * DURATION_SEC), endpoint=False)
    tone = np.sin(2 * np.pi * freq_hz * t)

    fade_samples = int(SAMPLE_RATE * FADE_MS / 1000)
    fade_in = np.linspace(0, 1, fade_samples)
    fade_out = np.linspace(1, 0, fade_samples)
    tone[:fade_samples] *= fade_in
    tone[-fade_samples:] *= fade_out

    tone = tone * VOLUME
    tone_int16 = np.int16(tone * 32767)
    wavfile.write(filepath, SAMPLE_RATE, tone_int16)


def generate_stimuli():
    """Generate shapes, sounds, and their random pairing; save to stimuli/."""
    rng = np.random.default_rng(GEN_SEED)
    py_rng = random.Random(GEN_SEED)

    os.makedirs(IMG_DIR, exist_ok=True)
    os.makedirs(SND_DIR, exist_ok=True)

    shape_files = []
    for i in range(N_STIMULI):
        n_vertices = rng.integers(N_VERTICES_RANGE[0], N_VERTICES_RANGE[1] + 1)
        x, y = generate_sharp_shape(n_vertices, rng)
        fname = f"shape{chr(65 + i)}.png"
        save_shape_image(x, y, os.path.join(IMG_DIR, fname))
        shape_files.append(fname)

    freqs = generate_tone_frequencies(N_STIMULI, rng)
    sound_files = []
    for i, freq in enumerate(freqs):
        fname = f"sound{chr(65 + i)}.wav"
        save_tone_wav(freq, os.path.join(SND_DIR, fname))
        sound_files.append(fname)

    shuffled_sounds = sound_files.copy()
    py_rng.shuffle(shuffled_sounds)
    associations = dict(zip(shape_files, shuffled_sounds))

    with open(ASSOCIATIONS_PATH, "w") as f:
        json.dump(associations, f, indent=2)

    print(f"Generated {len(associations)} shape-sound pairs -> {ASSOCIATIONS_PATH}")
    return associations


def load_or_generate_associations():
    """Use existing stimuli/associations.json if present, else generate fresh stimuli."""
    if os.path.exists(ASSOCIATIONS_PATH):
        with open(ASSOCIATIONS_PATH, "r") as f:
            return json.load(f)
    return generate_stimuli()


# =====================================================================
# PART B - TASK CONFIG
# =====================================================================

DATA_DIR = "data"

IMAGE_SIZE = (0.4, 0.4)
IMAGE_OFFSET_X = 0.35
FIXATION_DURATION = 0.5
SOUND_GAP = 0.3          # pause between left-sound and right-sound playback
POST_SOUND_PAUSE = 0.3   # pause after both sounds before response window opens
MAX_RESPONSE_TIME = 6.0
FEEDBACK_DURATION = 1.0
ITI = 0.6
RESPONSE_KEYS = ["left", "right", "escape"]
TOTAL_TRIALS = 120       # total number of trials in the whole task


# ---------------------------------------------------------------
# Build trial list
# ---------------------------------------------------------------

def build_trials(associations, total_trials=TOTAL_TRIALS):
    """
    Build exactly `total_trials` trials in total, with each shape appearing
    as the 'correct' side as evenly as possible. Each trial pairs the
    chosen shape's TRUE pairing against a foil: a different shape combined
    with a sound that is NOT its true match.
    """
    shapes = list(associations.keys())
    if len(shapes) < 2:
        raise ValueError("Need at least 2 shape-sound associations to build foils.")

    n_shapes = len(shapes)
    base_count = total_trials // n_shapes
    remainder = total_trials % n_shapes

    counts = {shape: base_count for shape in shapes}
    for shape in random.sample(shapes, remainder):
        counts[shape] += 1

    trials = []
    for shape, count in counts.items():
        true_sound = associations[shape]
        for _ in range(count):
            foil_shape = random.choice([s for s in shapes if s != shape])
            possible_foil_sounds = [
                s for s in associations.values() if s != associations[foil_shape]
            ]
            foil_sound = random.choice(possible_foil_sounds)

            trials.append({
                "correct_shape": shape,
                "correct_sound": true_sound,
                "foil_shape": foil_shape,
                "foil_sound": foil_sound,
            })

    random.shuffle(trials)
    assert len(trials) == total_trials
    return trials


def assign_sides(trial):
    """Randomly assign correct pairing to left or right side."""
    t = dict(trial)
    if random.random() < 0.5:
        t["left_shape"], t["left_sound"] = t["correct_shape"], t["correct_sound"]
        t["right_shape"], t["right_sound"] = t["foil_shape"], t["foil_sound"]
        t["correct_side"] = "left"
    else:
        t["left_shape"], t["left_sound"] = t["foil_shape"], t["foil_sound"]
        t["right_shape"], t["right_sound"] = t["correct_shape"], t["correct_sound"]
        t["correct_side"] = "right"
    return t


# ---------------------------------------------------------------
# Participant info
# ---------------------------------------------------------------

def get_participant_info():
    """Plain terminal prompt for participant info (avoids Qt/cocoa dependency)."""
    participant_id = input("Participant ID: ").strip() or "test"
    session = input("Session (default 001): ").strip() or "001"
    return {"participant_id": participant_id, "session": session}


# ---------------------------------------------------------------
# Main experiment
# ---------------------------------------------------------------

def run_experiment(associations):
    from psychopy import visual, core, event, sound

    raw_trials = build_trials(associations)
    if not raw_trials:
        raise RuntimeError("No trials could be built. Check associations.")

    trials = [assign_sides(t) for t in raw_trials]

    info = get_participant_info()
    os.makedirs(DATA_DIR, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_path = os.path.join(
        DATA_DIR, f"{info['participant_id']}_sess{info['session']}_{timestamp}.csv"
    )

    win = visual.Window(size=(1024, 768), color="gray", units="norm", fullscr=False)

    fixation = visual.TextStim(win, text="+", color="white", height=0.1)
    instructions = visual.TextStim(
        win,
        text=(
            "On each trial you will see two shapes.\n\n"
            "Each shape's sound will play, one at a time (left, then right).\n"
            "Only ONE side shows the shape correctly matched with its sound.\n\n"
            "Press LEFT if the left shape+sound pairing is correct.\n"
            "Press RIGHT if the right shape+sound pairing is correct.\n\n"
            "You will get feedback after each choice — use it to learn "
            "the correct pairings.\n\n"
            "Press SPACE to begin."
        ),
        color="white",
        wrapWidth=1.6,
        height=0.06,
    )
    instructions.draw()
    win.flip()
    event.waitKeys(keyList=["space"])

    left_shape_stim = visual.ImageStim(win, pos=(-IMAGE_OFFSET_X, 0), size=IMAGE_SIZE)
    right_shape_stim = visual.ImageStim(win, pos=(IMAGE_OFFSET_X, 0), size=IMAGE_SIZE)
    left_box = visual.Rect(win, pos=(-IMAGE_OFFSET_X, 0), width=IMAGE_SIZE[0] + 0.05,
                            height=IMAGE_SIZE[1] + 0.05, lineColor="yellow", lineWidth=4,
                            fillColor=None)
    right_box = visual.Rect(win, pos=(IMAGE_OFFSET_X, 0), width=IMAGE_SIZE[0] + 0.05,
                             height=IMAGE_SIZE[1] + 0.05, lineColor="yellow", lineWidth=4,
                             fillColor=None)
    prompt_text = visual.TextStim(win, text="Which pairing is correct?\n\u2190 Left     Right \u2192",
                                   pos=(0, -0.7), color="white", height=0.06)
    feedback_correct = visual.TextStim(win, text="Correct!", color="green", height=0.1)
    feedback_incorrect = visual.TextStim(win, text="Incorrect", color="red", height=0.1)

    results = []

    for i, trial in enumerate(trials):
        # Fixation
        fixation.draw()
        win.flip()
        core.wait(FIXATION_DURATION)

        left_shape_stim.image = os.path.join(IMG_DIR, trial["left_shape"])
        right_shape_stim.image = os.path.join(IMG_DIR, trial["right_shape"])
        left_snd = sound.Sound(os.path.join(SND_DIR, trial["left_sound"]))
        right_snd = sound.Sound(os.path.join(SND_DIR, trial["right_sound"]))

        # Show both shapes; play left sound while highlighting left shape
        left_shape_stim.draw()
        right_shape_stim.draw()
        left_box.draw()
        win.flip()
        left_snd.play()
        core.wait(left_snd.getDuration() + SOUND_GAP)

        # Highlight right shape while its sound plays
        left_shape_stim.draw()
        right_shape_stim.draw()
        right_box.draw()
        win.flip()
        right_snd.play()
        core.wait(right_snd.getDuration() + SOUND_GAP)

        # Response window
        left_shape_stim.draw()
        right_shape_stim.draw()
        prompt_text.draw()
        win.flip()
        core.wait(POST_SOUND_PAUSE)

        event.clearEvents()
        clock = core.Clock()
        keys = event.waitKeys(
            keyList=RESPONSE_KEYS, maxWait=MAX_RESPONSE_TIME, timeStamped=clock
        )

        if keys is None:
            response, rt, correct = "no_response", None, False
        else:
            key, rt = keys[0]
            if key == "escape":
                win.close()
                core.quit()
            response = "left" if key == "left" else "right"
            correct = (response == trial["correct_side"])

        # Feedback
        fb = feedback_correct if correct else feedback_incorrect
        fb.draw()
        win.flip()
        core.wait(FEEDBACK_DURATION)

        results.append({
            "trial_num": i + 1,
            "left_shape": trial["left_shape"],
            "left_sound": trial["left_sound"],
            "right_shape": trial["right_shape"],
            "right_sound": trial["right_sound"],
            "correct_side": trial["correct_side"],
            "response_side": response,
            "correct": correct,
            "rt_sec": rt,
        })

        # ITI
        win.flip()
        core.wait(ITI)

    # Save data
    with open(out_path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=results[0].keys())
        writer.writeheader()
        writer.writerows(results)

    n_correct = sum(r["correct"] for r in results)
    end_text = visual.TextStim(
        win,
        text=f"Task complete!\n\nAccuracy: {n_correct}/{len(results)} "
             f"({100*n_correct/len(results):.1f}%)",
        color="white",
        height=0.08,
    )
    end_text.draw()
    win.flip()
    core.wait(3.0)

    win.close()
    print(f"Data saved to: {out_path}")


# =====================================================================
# ENTRY POINT
# =====================================================================

if __name__ == "__main__":
    associations = load_or_generate_associations()
    run_experiment(associations)
