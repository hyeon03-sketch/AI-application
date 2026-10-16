"""Representation ladder R0–R4 and error-specific features → data/features_T100.npz.

Input: data/skeleton_T100.npz (raw and normalized positions, (N, T, 25, 3)).
Normalized frame: origin at SpineBase, x along the hip line (HipLeft -> HipRight), y up, z depth;
units = torso lengths.

Representations, each a sequence (N, T, F):
  R0     raw camera-space positions (resampled only)                    75
  R1     normalized positions                                           75
  R2     joint angles                                                   10
  R3     R2 + their time derivatives                                    20
  R4     R3 + left-right differences                                    24
  Rerr   error-specific features (one or two per KERAAL error)           9
  Rerr_d Rerr minus its own mean over the first 10% of the recording    9
         (starting-posture baseline; cancels static offsets such as camera pitch)

Every feature carries a plane tag (data/feature_names.json):
  invariant  - unchanged by any rotation of the skeleton (angles between body segments)
  frontal    - measured in the x-y plane (left-right tilt); robust to camera pitch
  horizontal - measured in the x-z plane (rotation about the vertical)
  sagittal   - measured in the y-z plane; directly shifted by camera pitch
  vertical   - uses the y axis (heights); partly shifted by camera pitch
  camera     - raw camera coordinates

Velocity is per step of normalized time (frame rate is unknown; see PROGRESS.md), scaled by T so that
it is "change per recording duration".

Usage:  python src/features.py [--T 100] [--check]
"""
from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from preprocess import J  # noqa: E402

BASELINE_FRAC = 0.10


def _angle(u: np.ndarray, v: np.ndarray) -> np.ndarray:
    """Angle in degrees between vectors along the last axis."""
    cos = (u * v).sum(-1) / (np.linalg.norm(u, axis=-1) * np.linalg.norm(v, axis=-1) + 1e-9)
    return np.degrees(np.arccos(np.clip(cos, -1.0, 1.0)))


def _wrap(deg: np.ndarray) -> np.ndarray:
    return (deg + 180.0) % 360.0 - 180.0


def joint_angles(P: np.ndarray) -> dict[str, tuple[np.ndarray, str]]:
    """P: (..., 25, 3) positions. Returns name -> (values (...), plane tag)."""
    g = lambda name: P[..., J[name], :]  # noqa: E731
    out = {}
    trunk_down = g("SpineBase") - g("SpineShoulder")
    shoulder_line = g("ShoulderRight") - g("ShoulderLeft")
    for side, s in (("L", "Left"), ("R", "Right")):
        upper = g(f"Elbow{s}") - g(f"Shoulder{s}")
        fore = g(f"Wrist{s}") - g(f"Elbow{s}")
        out[f"elbow_flex_{side}"] = (_angle(upper, fore), "invariant")             # 0 = straight arm
        out[f"shoulder_elev_{side}"] = (_angle(upper, trunk_down), "invariant")    # 0 = arm down, 90 = horizontal
        lateral = -shoulder_line if side == "L" else shoulder_line                 # points outward on that side
        out[f"arm_spread_{side}"] = (_angle(upper, lateral), "invariant")          # 0 = arm straight out sideways
    hip_line = g("HipRight") - g("HipLeft")
    out["trunk_rotation"] = (_wrap(np.degrees(np.arctan2(shoulder_line[..., 2], shoulder_line[..., 0])
                                              - np.arctan2(hip_line[..., 2], hip_line[..., 0]))), "horizontal")
    spine = g("SpineShoulder") - g("SpineBase")
    out["spine_tilt_frontal"] = (np.degrees(np.arctan2(spine[..., 0], spine[..., 1])), "frontal")
    out["spine_tilt_sagittal"] = (np.degrees(np.arctan2(spine[..., 2], spine[..., 1])), "sagittal")
    out["neck_angle"] = (_angle(g("Neck") - g("SpineShoulder"), g("Head") - g("Neck")), "invariant")
    return out


def error_features(P: np.ndarray, ang: dict) -> dict[str, tuple[np.ndarray, str]]:
    """One or two features per KERAAL error definition (defined from the labeling guide, frozen before use)."""
    g = lambda name: P[..., J[name], :]  # noqa: E731
    sw = np.linalg.norm(g("ShoulderRight") - g("ShoulderLeft"), axis=-1) + 1e-9
    return {
        # RTK-E1, CTK-E1/E3 "arms not raised enough"
        "shoulder_elev_L": ang["shoulder_elev_L"], "shoulder_elev_R": ang["shoulder_elev_R"],
        "wrist_height_L": (g("WristLeft")[..., 1] - g("ShoulderLeft")[..., 1], "vertical"),
        "wrist_height_R": (g("WristRight")[..., 1] - g("ShoulderRight")[..., 1], "vertical"),
        # RTK-E2 "torso rotation not sufficient"
        "trunk_rotation": ang["trunk_rotation"],
        # RTK-E3 "body leaned to the side", ELK-E2 "body not tilted"
        "spine_tilt_frontal": ang["spine_tilt_frontal"],
        # ELK-E3 "upper arm not bent" (and ELK-E1 "opposite arm not along the body" via shoulder_elev)
        "elbow_flex_L": ang["elbow_flex_L"], "elbow_flex_R": ang["elbow_flex_R"],
        # CTK-E2 "arms not outspread enough"
        "wrist_dist_over_shoulder_width": (np.linalg.norm(g("WristRight") - g("WristLeft"), axis=-1) / sw, "invariant"),
    }


def _stack(d: dict) -> tuple[np.ndarray, list[str], list[str]]:
    names = list(d)
    return np.stack([d[n][0] for n in names], axis=-1), names, [d[n][1] for n in names]


def build(raw: np.ndarray, norm: np.ndarray) -> dict:
    N, T = norm.shape[:2]
    reps = {}
    pos_names = [f"{j}_{c}" for j in J for c in "xyz"]
    reps["R0"] = (raw.reshape(N, T, -1), pos_names, ["camera"] * 75)
    reps["R1"] = (norm.reshape(N, T, -1), pos_names, ["normalized"] * 75)

    ang = joint_angles(norm)
    A, an, ap = _stack(ang)
    reps["R2"] = (A, an, ap)
    dA = np.gradient(A, axis=1) * T
    reps["R3"] = (np.concatenate([A, dA], -1), an + [f"d_{n}" for n in an], ap + ap)
    sym = {}
    for base in ("elbow_flex", "shoulder_elev", "arm_spread"):
        sym[f"sym_{base}"] = (ang[f"{base}_L"][0] - ang[f"{base}_R"][0], "invariant")
    sym["sym_wrist_height"] = (norm[..., J["WristLeft"], 1] - norm[..., J["WristRight"], 1], "vertical")
    S, sn, sp = _stack(sym)
    R3, n3, p3 = reps["R3"]
    reps["R4"] = (np.concatenate([R3, S], -1), n3 + sn, p3 + sp)

    E, en, ep = _stack(error_features(norm, ang))
    reps["Rerr"] = (E, en, ep)
    nb = max(1, int(round(BASELINE_FRAC * T)))
    reps["Rerr_d"] = (E - E[:, :nb].mean(axis=1, keepdims=True), [f"{n}_delta" for n in en], ep)
    return reps


def _random_rotation(rng) -> np.ndarray:
    q = rng.normal(size=4); q /= np.linalg.norm(q)
    a, b, c, d = q
    return np.array([[a*a+b*b-c*c-d*d, 2*(b*c-a*d), 2*(b*d+a*c)],
                     [2*(b*c+a*d), a*a-b*b+c*c-d*d, 2*(c*d-a*b)],
                     [2*(b*d-a*c), 2*(c*d+a*b), a*a-b*b-c*c+d*d]])


def check(reps: dict, norm: np.ndarray, N: int, T: int) -> list[str]:
    fails = []
    expected_dims = {"R0": 75, "R1": 75, "R2": 10, "R3": 20, "R4": 24, "Rerr": 9, "Rerr_d": 9}
    for k, dim in expected_dims.items():
        X, names, planes = reps[k]
        if X.shape != (N, T, dim) or len(names) != dim or len(planes) != dim:
            fails.append(f"{k}: shape {X.shape}, {len(names)} names, expected (N, T, {dim})")
        if not np.isfinite(X).all():
            fails.append(f"{k}: non-finite values")
    A, an, _ = reps["R2"]
    for i, n in enumerate(an):
        if n.startswith(("elbow_flex", "shoulder_elev", "arm_spread", "neck")):
            if A[..., i].min() < 0 or A[..., i].max() > 180:
                fails.append(f"{n} outside [0, 180]")
    # Invariance: features tagged 'invariant' must not change under an arbitrary 3D rotation + translation + scale.
    rng = np.random.default_rng(0)
    P = norm[:5]
    R = _random_rotation(rng)
    P2 = 1.7 * (P @ R.T) + np.array([0.3, -1.2, 2.5])
    a1, a2 = joint_angles(P), joint_angles(P2)
    for n, (v, plane) in a1.items():
        if plane == "invariant":
            d = np.abs(v - a2[n][0]).max()
            if d > 1e-3:
                fails.append(f"{n} tagged invariant but changed by {d:.4f} deg under rotation")
    return fails


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    ap.add_argument("--T", type=int, default=100)
    ap.add_argument("--check", action="store_true")
    args = ap.parse_args()
    root = args.root

    sk = np.load(root / "data" / f"skeleton_T{args.T}.npz")
    keys, raw, norm = sk["keys"], sk["raw"].astype(np.float64), sk["norm"].astype(np.float64)
    N, T = norm.shape[:2]
    reps = build(raw, norm)

    np.savez_compressed(root / "data" / f"features_T{args.T}.npz", keys=keys,
                        **{k: v[0].astype(np.float32) for k, v in reps.items()})
    meta = {k: [{"name": n, "plane": p} for n, p in zip(v[1], v[2])] for k, v in reps.items()}
    (root / "data" / "feature_names.json").write_text(json.dumps(meta, indent=1), encoding="utf-8")
    print(f"wrote data/features_T{args.T}.npz:", {k: v[0].shape[-1] for k, v in reps.items()})
    print("plane tags in R4:", {str(p): int(v) for p, v in zip(*np.unique(reps["R4"][2], return_counts=True))})

    # Descriptive sanity check on annotator-A labels. Feature definitions above were fixed from the
    # error wording before this was run; do NOT tune features on these numbers (they are test data).
    with (root / "data" / "labels.csv").open(encoding="utf-8") as f:
        lab = {r["rec_key"]: r for r in csv.DictReader(f)}
    E, en, _ = reps["Rerr"]
    probes = [("RTK", "trunk_rotation", "range", "E2"), ("ELK", "spine_tilt_frontal", "range", "E2"),
              ("CTK", "shoulder_elev_L", "max", "E1"), ("CTK", "shoulder_elev_L", "max", "E3"),
              ("CTK", "wrist_dist_over_shoulder_width", "max", "E2")]
    print("sanity (annotator A, median per class; summary over the recording):")
    for ex, feat, how, err in probes:
        i = en.index(feat)
        v = E[..., i]
        s = v.max(1) - v.min(1) if how == "range" else v.max(1)
        cls = np.array([lab[k]["label_A"] if lab[k]["exercise"] == ex else "" for k in keys])
        c, e = s[cls == "C"], s[cls == err]
        if len(e):
            print(f"  {ex} {feat} {how}: C {np.median(c):.2f} (n={len(c)})  vs  {err} {np.median(e):.2f} (n={len(e)})")

    if args.check:
        fails = check(reps, norm, N, T)
        for x in fails:
            print("CHECK FAILED:", x)
        print("CHECK", "PASSED" if not fails else f"FAILED ({len(fails)})")
        return 1 if fails else 0
    return 0


if __name__ == "__main__":
    sys.exit(main())
