# harmonic_layers_and_f0_ONLY.py
import numpy as np
from scipy.io.wavfile import write
from scipy.signal import welch
import pandas as pd, os, json

# ---------------- GLOBAL CONSTANTS -----------------------------------------
SR   = 44_100
DUR  = 1.2
# F0_VALUES = [130, 138, 146, 155, 164, 174, 185, 196, 207, 220, 233, 246]  # C3 to B3 chromatic (12 tones)
# F0_START = 130
# F0_STEP = 10.545454545454545  # (246 - 130) / (12 - 1)
# HARM_START = 24
# HARM_STEP = -2  # decrement by 2 each time
F0_VALUES = np.linspace(130, 246, 10)  # Generate 10 evenly spaced F0 values
N_HARM_LAYERS = np.linspace(24, 2, 10, dtype=int)  # Generate 10 evenly spaced harmonic layers
TILT_VALUE = 3.5  # fixed tilt value
assert len(F0_VALUES) == len(N_HARM_LAYERS), "F0 and harmonic lists must be same length"

OUT_DIR = "generated_sounds"
ENV_ATTACK, ENV_DECAY, ENV_SUS, ENV_REL = 0.015, 0.04, 0.85, 0.10
VOLUME = 0.9

# ---------------- helper functions -----------------------------------------
def adsr(t, a, d, s, r):
    a_len, d_len, r_len = int(a*SR), int(d*SR), int(r*SR)
    env = np.ones_like(t) * s
    env[:a_len] = np.linspace(0, 1, a_len, endpoint=False)
    env[a_len:a_len+d_len] = np.linspace(1, s, d_len, endpoint=False)
    env[-r_len:] *= np.linspace(1, 0, r_len)
    return env

def synth_signal(n_harm, beta, f0, t):  # Fix parameter name
    sig = np.zeros_like(t)
    for h in range(1, n_harm+1):  # Use n_harm instead of n_h
        sig += (1 / (h**beta)) * np.sin(2*np.pi*f0*h*t)
    return sig

def spectral_centroid(x, sr):
    f, Pxx = welch(x, sr, nperseg=4096)
    return np.sum(f * Pxx) / np.sum(Pxx)

# ---------------- synthesis -------------------------------------------------
os.makedirs(OUT_DIR, exist_ok=True)
t = np.linspace(0, DUR, int(SR*DUR), endpoint=False)

np.random.seed(42)  # Set a random seed for reproducibility

log = []
sound_idx = 1
for i in range(len(F0_VALUES)):  # Loop through all 10 F0 values
    f0 = F0_VALUES[i]
    n_h = N_HARM_LAYERS[i]
    sig = synth_signal(n_h, TILT_VALUE, f0, t)
    sig *= adsr(t, ENV_ATTACK, ENV_DECAY, ENV_SUS, ENV_REL)
    sig /= np.max(np.abs(sig)) / VOLUME
    wav = np.int16(sig * 32767)

    fname = f"sound_{sound_idx:02d}.wav"
    write(os.path.join(OUT_DIR, fname), SR, wav)
    print("Saved", fname)

    log.append({
        "file": fname,
        "F0_Hz": float(f0),  # Ensure float type
        "harmonics": int(n_h),  # Ensure int type
        "beta_tilt": TILT_VALUE,
        "spectral_centroid_Hz": float(spectral_centroid(sig, SR))  # Ensure float type
    })
    sound_idx += 1

# ---------------- feature log ----------------------------------------------
pd.DataFrame(log).to_csv(os.path.join(OUT_DIR, "sound_feature_log.csv"), index=False)
with open(os.path.join(OUT_DIR, "sound_feature_log.json"), "w") as f:
    json.dump(log, f, indent=2)

print("\nFinished – 10 sounds with varying F0 and harmonics saved in", OUT_DIR)  # Update to reflect 10 sounds
