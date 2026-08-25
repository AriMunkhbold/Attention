# Assessing Audiovisual Learning Plasticity with Novel Stimuli

This experiment investigates **audiovisual learning plasticity** using novel, unfamiliar stimuli. Participants are exposed to **arbitrary pairings** of abstract shapes and distinct tones, and their ability to learn and recall these pairings is tested.

---

## 🧠 Significance

This study examines **developmental differences** in how participants bind auditory and visual features.

By evaluating **audiovisual binding thresholds** and **cross-modal learning**, this work contributes to a **predictive framework** for when and how new audiovisual associations are learned and generalised across developmental stages.

---

## Stimuli

This experiment uses two distinct sets of **novel audiovisual stimuli**—one for the learning blocks and one for the test block. Each set consists of **6 pairings** used in the experiment.

### 👁 Visual Stimuli: Irregular Polygons

Shapes are generated procedurally using a parametric method that introduces:

- **Concavity** — by pulling selected vertices toward the center.
- **Jaggedness** — by applying random shifts to vertex positions.
- **Consistent luminance** — by normalising RMS contrast across images.

Each shape is:

- Created from 18 randomly placed vertices around a circle.
- Adjusted for distortion, concavity, jaggedness, and global scale.
- Saved as `.png` files (black-filled, centered shapes on white background).
- Logged with metadata in `shape_metadata.xlsx`.

There are **two shape sets**:

- `generated_shapes/`: Used during the learning phase (training set).
- `generated_shapes_testset/`: Used exclusively during the test phase, with **distinct geometry parameters** to encourage generalisation.

### 👂 Auditory Stimuli: Harmonic Tones

Tones are synthesised with a harmonic stack approach using:

- Varying **number of harmonic layers** (from 6 to 24).
- Evenly spaced **fundamental frequencies (F0)**.
- A fixed **spectral tilt** value (β = 3.5).
- An **ADSR envelope** with attack, decay, sustain, and release.

Each sound:

- Lasts **1.2 seconds**.
- Is saved as a `.wav` file at **44.1kHz** sampling rate.
- Has metadata including F0, harmonic count, spectral centroid, and tilt.
- Is stored in `tone_feature_log.csv` and `tone_feature_log.json`.

There are **two tone sets**:

- `generated_sounds/`: Used in learning blocks.
- `generated_sounds_testset/`: Used in the final test block, with new F0s and slightly fewer harmonics to alter timbre.

---

### 🔄 Pairing Logic

- **6 shape–tone pairs** are selected per dataset.
- Pairings are **fixed within each set** but differ between the training and test sets.
- This setup allows us to test **cross-modal learning and generalisation**.


---

## 🧪 Experimental Design

The experiment consists of **4 blocks**, presented in a fixed order:

### 🔢 Block 1: Free Pairing (Training Stimuli)
Participants are shown the full set of training stimuli:
- **6 sounds and 6 shapes** are displayed.
- Participants **click a sound**, hear it, then **click a shape** to assign a pairing.
- All sounds must be paired before proceeding.

### 🧠 Block 2: Learning Phase (Passive or Active)
Participants choose:
- **Passive Block**:
  - Shapes and tones are shown one at a time.
  - Participants observe 240 random pairings (each shown 40 times).
- **Active Block**:
  - Shapes or tones are presented alongside distractors.
  - Participants make forced-choice decisions about correct pairings.
  - Feedback is provided on each trial.
  - Responses and reaction times are recorded.

### 🔁 Block 3: Free Pairing (Test Stimuli)
Participants repeat the free pairing task with a **new set** of 6 novel shapes and tones from the testset:
- Pairings are again self-determined.

### 🎯 Block 4: Forced-Choice Testing
Participants complete a **matching task** using the testset:
- Each shape is followed by two tones (or vice versa).
- They must choose which tone or image matches.
  - **Press `1`** if the **first** matches.
  - **Press `2`** if the **second** matches.
- Trials are split into subblocks with breaks.
- Performance and reaction times are logged.

---

## 💾 Data Storage

- Each block is saved in a **separate Excel file** in the participant's folder.
- A **consolidated Excel file** combines all blocks into one `.xlsx` file with multiple sheets.
- Logs include stimulus IDs, responses, reaction times, and accuracy.

---

## 🚀 Installation & Setup

### 1️⃣ Clone the Repository

```bash
git clone https://github.com/annamachado1/AV-learning.git
cd AV-learning
