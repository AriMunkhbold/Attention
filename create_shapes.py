# incremental_shapes_mapper_fixed.py
import matplotlib.pyplot as plt
import numpy as np
import os, cv2, pandas as pd

# ────────── helpers (unchanged) ────────────────────────────────────────────
def generate_complex_polygon(num_sides, distortion, concavity, jaggedness, scale=0.75):
    angles = np.sort(np.random.rand(num_sides) * 2 * np.pi)
    radii  = 0.5 + np.random.rand(num_sides) * distortion
    pts    = [(0.5 + r*np.cos(a), 0.5 + r*np.sin(a)) for r, a in zip(radii, angles)]

    # concave vertices
    n_conc = int(num_sides * concavity)
    conc_i = np.random.choice(num_sides, n_conc, replace=False)
    for i in conc_i:
        pts[i] = ((pts[i][0]+0.5)/2, (pts[i][1]+0.5)/2)

    # jagged vertices
    n_jag  = int(num_sides * jaggedness)
    jag_i  = np.random.choice(num_sides, n_jag, replace=False)
    for i in jag_i:
        pts[i] = (pts[i][0] + np.random.uniform(-0.05, 0.05),
                  pts[i][1] + np.random.uniform(-0.05, 0.05))

    # global scaling
    return [(0.5+(x-0.5)*scale, 0.5+(y-0.5)*scale) for x, y in pts]

def compute_rms_contrast(png_path):
    img  = cv2.imread(png_path, cv2.IMREAD_GRAYSCALE)
    mu   = np.mean(img)
    return np.sqrt(np.mean((img-mu)**2))

# ────────── main generator ─────────────────────────────────────────────────
def generate_shapes(
        output_dir     = "generated_shapes",
        sides_list     = (8, 10, 12, 14, 16, 18, 20, 22, 24, 26, 28, 30), 
        jagged_list    = (0.15, 0.22, 0.29, 0.36, 0.43, 0.50, 0.57, 0.64, 0.71, 0.78, 0.85, 0.92),   
        scale          = 0.75,
        distortion     = 0.40,           # constant
        concavity      = 0.30,           # constant
        target_rms     = 120,
        random_seed    = 42 ):           # default fixed seed

    if random_seed is not None:
        np.random.seed(random_seed)
        import random
        random.seed(random_seed)

    os.makedirs(output_dir, exist_ok=True)
    meta = []

    # Select exactly 10 evenly spaced shapes
    indices = np.linspace(0, len(sides_list) - 1, 10, dtype=int)
    sides_list = [sides_list[i] for i in indices]
    jagged_list = [jagged_list[i] for i in indices]

    # parameter vectors with matching length
    n_shapes   = len(sides_list)
    jag_vals   = jagged_list

    for idx, (n_sides, jag) in enumerate(zip(sides_list, jag_vals), 1):

        # --- draw polygon ---------------------------------------------------
        fig, ax = plt.subplots(figsize=(5, 5), dpi=300)
        pts     = generate_complex_polygon(n_sides, distortion, concavity,
                                           jaggedness=jag, scale=scale)
        ax.add_patch(plt.Polygon(pts, color='black'))
        ax.set(xlim=(0,1), ylim=(0,1), aspect='equal'); ax.axis('off')

        fname = os.path.join(output_dir, f"shape_{idx:02d}.png")
        plt.savefig(fname, bbox_inches='tight', pad_inches=0.2); plt.close(fig)

        # --- RMS‐contrast balancing (identical to before) -------------------
        rms, it = compute_rms_contrast(fname), 0
        while not (115 <= rms <= 125) and it < 20:
            g  = cv2.imread(fname, cv2.IMREAD_GRAYSCALE); mu = np.mean(g)
            g  = np.clip((g-mu)*(target_rms/rms)+mu, 0, 255).astype(np.uint8)
            cv2.imwrite(fname, g); rms = compute_rms_contrast(fname); it += 1

        meta.append(dict(File=fname, Sides=n_sides, Jaggedness=round(jag,3),
                         Distortion=distortion, Concavity=concavity,
                         RMS_Contrast=round(rms,2)))
        print(f"✓ {fname} | sides={n_sides:<2d}  jag={jag:.2f}")

    # --- Excel log ----------------------------------------------------------
    df = pd.DataFrame(meta)
    df.to_excel(os.path.join(output_dir, "shape_metadata.xlsx"), index=False)
    print("\nMetadata saved →", os.path.join(output_dir, "shape_metadata.xlsx"))

# ────────── run as script ──────────────────────────────────────────────────
if __name__ == "__main__":
    generate_shapes()
