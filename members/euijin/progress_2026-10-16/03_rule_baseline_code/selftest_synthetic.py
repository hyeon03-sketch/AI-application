"""Self-test with synthetic Kinect data (no KERAAL needed).
Creates a fake model_input CSV with three exercises, correct and 'insufficient amplitude' reps,
then you can run the whole pipeline on it:

    python selftest_synthetic.py           -> writes selftest/model_input_synthetic.csv
    set the path in config or pass --csv to the scripts
"""
import numpy as np
import pandas as pd
from pathlib import Path

rng = np.random.default_rng(0)
FPS = 15
BASE = {  # standing pose, metres (x lateral, y up, z depth)
    "SpineBase": (0, 0.0, 2.5), "SpineMid": (0, 0.28, 2.5), "Neck": (0, 0.58, 2.5), "Head": (0, 0.72, 2.5),
    "ShoulderLeft": (-0.18, 0.52, 2.5), "ElbowLeft": (-0.2, 0.25, 2.5), "WristLeft": (-0.2, 0.02, 2.5), "HandLeft": (-0.2, -0.05, 2.5),
    "ShoulderRight": (0.18, 0.52, 2.5), "ElbowRight": (0.2, 0.25, 2.5), "WristRight": (0.2, 0.02, 2.5), "HandRight": (0.2, -0.05, 2.5),
    "HipLeft": (-0.09, -0.02, 2.5), "KneeLeft": (-0.1, -0.45, 2.5), "AnkleLeft": (-0.1, -0.85, 2.5), "FootLeft": (-0.1, -0.9, 2.4),
    "HipRight": (0.09, -0.02, 2.5), "KneeRight": (0.1, -0.45, 2.5), "AnkleRight": (0.1, -0.85, 2.5), "FootRight": (0.1, -0.9, 2.4),
    "SpineShoulder": (0, 0.52, 2.5), "HandTipLeft": (-0.2, -0.1, 2.5), "ThumbLeft": (-0.17, -0.05, 2.5),
    "HandTipRight": (0.2, -0.1, 2.5), "ThumbRight": (0.17, -0.05, 2.5),
}
ORDER = list(BASE)


def rot(v, axis, deg, origin):
    th = np.radians(deg); c, s = np.cos(th), np.sin(th)
    p = np.array(v) - origin
    if axis == "z":   R = np.array([[c, -s, 0], [s, c, 0], [0, 0, 1]])
    elif axis == "y": R = np.array([[c, 0, s], [0, 1, 0], [-s, 0, c]])
    else:             R = np.array([[1, 0, 0], [0, c, -s], [0, s, c]])
    return R @ p + origin


def pose(ex, a):
    P = {k: np.array(v, float) for k, v in BASE.items()}
    upper = ["SpineMid", "Neck", "Head", "SpineShoulder"] + [k for k in P if any(s in k for s in ("Shoulder", "Elbow", "Wrist", "Hand", "Thumb"))]
    if ex == "CTK":   # raise both arms forward (flexion about x axis at the shoulder)
        for side in ("Left", "Right"):
            o = P["Shoulder" + side].copy()
            for k in ("Elbow", "Wrist", "Hand", "HandTip", "Thumb"):
                P[k + side] = rot(P[k + side], "x", -a, o)
    elif ex == "ELK":  # lateral bend of the upper body about z at SpineBase
        o = P["SpineBase"].copy()
        for k in upper:
            P[k] = rot(P[k], "z", a, o)
    elif ex == "RTK":  # axial rotation of the upper body about y
        o = P["SpineBase"].copy()
        for k in upper:
            P[k] = rot(P[k], "y", a, o)
    return P


rows = []
plan = {"1A": [f"R{i}" for i in range(1, 7)], "2A": [f"S{i}" for i in range(1, 7)], "3": ["P1", "P2"]}
amp = {"CTK": 100, "ELK": 30, "RTK": 45}
etype = {"CTK": ("Error1", "BothArms"), "ELK": ("Error2", "Spine"), "RTK": ("Error2", "Spine")}
for grp, parts in plan.items():
    for pid in parts:
        bias = rng.normal(0, 0.08)
        for ex in ("CTK", "ELK", "RTK"):
            for k in range(2):
                rec = f"G{grp}_{pid}_{ex}_{k}"
                n_rep = 4
                frames = [np.zeros(20)]
                errs = [np.zeros(20, bool)]
                for r in range(n_rep):
                    bad = rng.random() < 0.35
                    A = amp[ex] * (1 + bias) * (rng.uniform(0.35, 0.6) if bad else rng.uniform(0.85, 1.1))
                    if ex != "CTK" and rng.random() < 0.5: A = -A
                    L = int(rng.uniform(2.5, 4.0) * FPS)
                    prof = np.sin(np.linspace(0, np.pi, L)) ** 2 * A
                    frames += [prof, np.zeros(int(FPS * 0.8))]
                    errs += [np.full(L, bad) & (np.abs(prof) > 0.2 * abs(A)), np.zeros(int(FPS * 0.8), bool)]
                a = np.concatenate(frames); e = np.concatenate(errs)
                last_err = np.flatnonzero(e)
                span_end = (last_err[-1] if len(last_err) and grp == "1A" else len(a) - 1)
                for t, (ang, er) in enumerate(zip(a, e)):
                    P = pose(ex, ang)
                    row = dict(recording_id=rec, participant_key=f"{grp}_{pid}", group=grp, frame=t,
                               error_type=etype[ex][0] if er else "", body_part=etype[ex][1] if er else "",
                               in_annotated_span="yes" if t <= span_end else "no", skeleton_truncated="no")
                    for j, name in enumerate(ORDER):
                        x, y, z = P[name] + rng.normal(0, 0.004, 3)
                        row[f"j{j}_x"], row[f"j{j}_y"], row[f"j{j}_z"] = x, y, z
                    rows.append(row)

out = Path("selftest"); out.mkdir(exist_ok=True)
df = pd.DataFrame(rows)
df.to_csv(out / "model_input_synthetic.csv", index=False)
print(f"wrote {out / 'model_input_synthetic.csv'}  rows={len(df):,} recordings={df.recording_id.nunique()}")
