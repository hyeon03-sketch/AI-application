"""Person-trait confound check → results/person_confound.csv

Question: can features that say nothing about how the movement was performed — body size, where the
person stood relative to the camera, how long the recording is — predict the error label of an unseen
participant? If they do about as well as raw coordinates (R0), R0's lead in round 7 is a confound
(the model recognises "people who make this error"), not movement quality.

Static feature sets (medians over all frames of the untouched camera-space skeleton):
  anthropometry  torso length, shoulder width, left/right arm length, SpineBase-Head distance
  camera         SpineBase x, y, z (lateral offset, height, distance) and heading of the hip line
  duration       number of frames
  static_all     all of the above
Compared on the same protocol, folds, model and seeds as rf_baseline.py (Random Forest, 5 seeds), next to
R0, Rerr_d (motion relative to the starting posture) and the majority baseline from results/rf_<P>_summary.csv.

Usage:  python src/person_confound.py [--protocol P4] [--check]
"""
from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path

import numpy as np
from sklearn.ensemble import RandomForestClassifier

sys.path.insert(0, str(Path(__file__).resolve().parent))
from evaluate import evaluate  # noqa: E402
from preprocess import J, heading_rotation  # noqa: E402
from rf_baseline import N_TREES, folds_of  # noqa: E402

SEEDS = [0, 1, 2, 3, 4]


def static_features(pos: np.ndarray) -> dict[str, float]:
    d = lambda a, b: float(np.median(np.linalg.norm(pos[:, J[a]] - pos[:, J[b]], axis=1)))  # noqa: E731
    sb = np.median(pos[:, J["SpineBase"]], axis=0)
    _, heading = heading_rotation(pos - pos[:, J["SpineBase"]:J["SpineBase"] + 1])
    return {
        "torso_len": d("SpineBase", "SpineShoulder"), "shoulder_width": d("ShoulderLeft", "ShoulderRight"),
        "arm_len_L": d("ShoulderLeft", "ElbowLeft") + d("ElbowLeft", "WristLeft"),
        "arm_len_R": d("ShoulderRight", "ElbowRight") + d("ElbowRight", "WristRight"),
        "spine_head": d("SpineBase", "Head"),
        "cam_x": float(sb[0]), "cam_y": float(sb[1]), "cam_z": float(sb[2]), "heading": heading,
        "n_frames": float(len(pos)),
    }


SETS = {
    "anthropometry": ["torso_len", "shoulder_width", "arm_len_L", "arm_len_R", "spine_head"],
    "camera": ["cam_x", "cam_y", "cam_z", "heading"],
    "duration": ["n_frames"],
}
SETS["static_all"] = SETS["anthropometry"] + SETS["camera"] + SETS["duration"]


def run(root: Path, protocol: str, seeds=SEEDS) -> list[dict]:
    raw = np.load(root / "data" / "skeleton_raw.npz")
    with (root / "data" / "labels.csv").open(encoding="utf-8") as f:
        lab = {r["rec_key"]: r for r in csv.DictReader(f)}
    folds = folds_of(json.loads((root / "data" / "splits.json").read_text(encoding="utf-8")), protocol)
    needed = {k for _, tr, te in folds for k in tr + te}
    missing = needed - set(raw.files)
    if missing:
        raise SystemExit(f"{len(missing)} recordings in {protocol} have no skeleton yet; on hold.")
    S = {k: static_features(raw[k].astype(np.float64)) for k in sorted(needed)}
    rows = []
    for ann in ("A", "B"):
        col = f"label_{ann}"
        for ex in ("RTK", "ELK", "CTK"):
            for set_name, cols in SETS.items():
                f1s, bas, ci = [], [], None
                for seed in seeds:
                    yt, yp, gs = [], [], []
                    for _, tr, te in folds:
                        tr = [k for k in tr if lab[k]["exercise"] == ex and lab[k][col] != "EXCL"]
                        te = [k for k in te if lab[k]["exercise"] == ex and lab[k][col] != "EXCL"]
                        if not tr or not te:
                            continue
                        X = lambda ks: np.array([[S[k][c] for c in cols] for k in ks])  # noqa: E731
                        clf = RandomForestClassifier(n_estimators=N_TREES, class_weight="balanced",
                                                     min_samples_leaf=2, random_state=seed, n_jobs=-1)
                        clf.fit(X(tr), [lab[k][col] for k in tr])
                        yp += list(clf.predict(X(te))); yt += [lab[k][col] for k in te]
                        gs += [lab[k]["participant_key"] for k in te]
                    res = evaluate(yt, yp, gs if seed == seeds[0] else None, n_boot=1000)
                    f1s.append(res["macro_f1"]); bas.append(res["balanced_accuracy"])
                    ci = ci or res.get("macro_f1_ci")
                rows.append({"protocol": protocol, "annotator": ann, "exercise": ex, "features": set_name,
                             "n_features": len(cols), "macro_f1_mean": float(np.mean(f1s)),
                             "macro_f1_sd": float(np.std(f1s)), "macro_f1_ci_lo": ci[0], "macro_f1_ci_hi": ci[1],
                             "bal_acc_mean": float(np.mean(bas))})
    return rows


def reference(root: Path, protocol: str) -> dict:
    p = root / "results" / f"rf_{protocol}_summary.csv"
    if not p.exists():
        return {}
    with p.open(encoding="utf-8") as f:
        return {(r["annotator"], r["exercise"], r["rep"]): float(r["macro_f1_mean"]) for r in csv.DictReader(f)}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    ap.add_argument("--protocol", default="P4")
    ap.add_argument("--check", action="store_true")
    args = ap.parse_args()
    root = args.root

    if args.check:
        fails = []
        raw = np.load(root / "data" / "skeleton_raw.npz")
        k = raw.files[0]
        s = static_features(raw[k].astype(np.float64))
        if not all(np.isfinite(v) for v in s.values()):
            fails.append("non-finite static feature")
        if not 0.25 < s["torso_len"] < 0.8 or not 0.2 < s["shoulder_width"] < 0.6:
            fails.append(f"implausible body size for {k}: {s}")
        # rigid motion of the whole skeleton must leave anthropometry unchanged and move the camera features
        pos = raw[k].astype(np.float64)
        c, si = np.cos(0.4), np.sin(0.4)
        R = np.array([[c, 0, si], [0, 1, 0], [-si, 0, c]])
        s2 = static_features(pos @ R.T + np.array([0.5, 0.1, -0.3]))
        if any(abs(s[a] - s2[a]) > 1e-6 for a in SETS["anthropometry"]):
            fails.append("anthropometry changed under a rigid motion")
        if abs(s2["cam_x"] - s["cam_x"]) < 0.1:
            fails.append("camera features did not respond to moving the skeleton")
        rows = run(root, args.protocol, seeds=[0])
        if len(rows) != 2 * 3 * len(SETS) or not all(np.isfinite(r["macro_f1_mean"]) for r in rows):
            fails.append("end-to-end run did not produce one finite row per annotator x exercise x feature set")
        for x in fails:
            print("CHECK FAILED:", x)
        print("CHECK", "PASSED" if not fails else f"FAILED ({len(fails)})")
        return 1 if fails else 0

    rows = run(root, args.protocol)
    ref = reference(root, args.protocol)
    out = root / "results" / f"person_confound_{args.protocol}.csv"
    with out.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]) + ["ref_R0", "ref_Rerr_d", "ref_majority"])
        w.writeheader()
        for r in rows:
            k = (r["annotator"], r["exercise"])
            w.writerow({**{a: (f"{v:.4f}" if isinstance(v, float) else v) for a, v in r.items()},
                        "ref_R0": ref.get(k + ("R0",), ""), "ref_Rerr_d": ref.get(k + ("Rerr_d",), ""),
                        "ref_majority": ref.get(k + ("majority",), "")})
    print(f"wrote {out.relative_to(root).as_posix()}")
    print(f"{args.protocol} Macro-F1 (5 seeds): static feature sets vs references from rf_{args.protocol}_summary.csv")
    for ann in ("A", "B"):
        for ex in ("RTK", "ELK", "CTK"):
            rs = {r["features"]: r for r in rows if (r["annotator"], r["exercise"]) == (ann, ex)}
            k = (ann, ex)
            print(f"  {ann} {ex}: " + "  ".join(f"{n} {rs[n]['macro_f1_mean']:.3f}" for n in SETS) +
                  f"  | R0 {ref.get(k + ('R0',), float('nan')):.3f}  Rerr_d {ref.get(k + ('Rerr_d',), float('nan')):.3f}"
                  f"  majority {ref.get(k + ('majority',), float('nan')):.3f}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
