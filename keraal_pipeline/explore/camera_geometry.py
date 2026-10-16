"""Pre-registered data-quality step 3: camera geometry per group (no labels, no model results).

Re-measures on ALL Group 3 recordings what round 3 measured on 6 sample files: where the person stands in camera
space (SpineBase x, y, z), the heading of the hip line, torso length, and the apparent sagittal spine tilt
(camera pitch + posture). Compares Groups 1A, 2A and 3.

Usage:  python explore/camera_geometry.py   → results/camera_geometry.csv
"""
import csv
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from preprocess import J, heading_rotation  # noqa: E402

raw = np.load(ROOT / "data" / "skeleton_raw.npz")
with (ROOT / "data" / "master_index.csv").open(encoding="utf-8") as f:
    group = {r["rec_key"]: r["group"] for r in csv.DictReader(f)}

rows = []
for k in raw.files:
    p = raw[k].astype(np.float64)
    sb = np.median(p[:, J["SpineBase"]], axis=0)
    spine = np.median(p[:, J["SpineShoulder"]] - p[:, J["SpineBase"]], axis=0)
    _, heading = heading_rotation(p - p[:, J["SpineBase"]:J["SpineBase"] + 1])
    rows.append({"rec_key": k, "group": group[k], "x": sb[0], "y": sb[1], "z": sb[2], "heading_deg": heading,
                 "torso_m": float(np.median(np.linalg.norm(p[:, J["SpineShoulder"]] - p[:, J["SpineBase"]], axis=1))),
                 "sagittal_tilt_deg": float(np.degrees(np.arctan2(spine[2], spine[1])))})

with (ROOT / "results" / "camera_geometry.csv").open("w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, fieldnames=list(rows[0]))
    w.writeheader()
    for r in rows:
        w.writerow({k: (f"{v:.4f}" if isinstance(v, float) else v) for k, v in r.items()})

print("group  n    SpineBase x / y / z (m)        heading     torso      sagittal tilt")
for g in ("1A", "2A", "3"):
    rs = [r for r in rows if r["group"] == g]
    a = lambda c: np.array([r[c] for r in rs])  # noqa: E731
    print(f"{g:5s} {len(rs):4d}  {a('x').mean():+.2f} / {a('y').mean():+.2f} / {a('z').mean():.2f}"
          f"   {a('heading_deg').mean():+5.1f}° (sd {a('heading_deg').std():.1f})"
          f"   {a('torso_m').mean():.3f} m   {a('sagittal_tilt_deg').mean():+5.1f}° (sd {a('sagittal_tilt_deg').std():.1f})")
