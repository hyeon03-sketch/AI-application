"""Trial (session) confound check for Group 3 → results/trial_confound.csv, results/trial_confound_features.csv.

In Group 3 each trial pairs the correct movement with ONE error type:
  T1 = C + E1,  T2 = C + E2,  T3 = C + E3   (per participant and exercise, 5 repetitions each)
so a model can separate E1/E2/E3 by recognising the recording session (where the person stood, sensor
placement) instead of the movement. The check uses only the CORRECT recordings: they are the same task
in every trial, so any trial information in them is session information that leaks into the error labels.

Two complementary tests per exercise and representation (summary statistics of each feature):
  1. classifier  shrinkage LDA on standardized features; accuracy at telling T1/T2/T3 apart
                 - within: per participant, 5-fold CV over that person's 15 correct recordings
                 - across: leave-one-participant-out (is the cue shared between people?)
                 chance = 1/3; a permutation null (labels shuffled within participant) gives the 95th pct.
                 Sensitive to cues spread over many features (e.g. the whole skeleton shifted).
  2. per feature one-way ANOVA across trials after removing each participant's mean, Benjamini-Hochberg
                 FDR 5%. Sensitive to a cue concentrated in a few features, and says WHICH features.
Why not a Random Forest: with ~12 training recordings per fold it missed even a strong injected cue in
the self-test. Known limit: a cue confined to 1 feature among hundreds is invisible to test 1 (test 2
covers it).

Group 3 skeletons are not available yet: without them this script reports that it is on hold and exits 0.

Usage:  python src/trial_confound.py [--reps R0,R1,R2,Rerr] [--perms 200] [--check]
"""
from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path

import numpy as np
from scipy.stats import f_oneway
from sklearn.discriminant_analysis import LinearDiscriminantAnalysis
from sklearn.model_selection import StratifiedKFold
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

sys.path.insert(0, str(Path(__file__).resolve().parent))
from rf_baseline import summarize  # noqa: E402

REPS = ["R0", "R1", "R2", "Rerr"]
STATS = ["mean", "sd", "min", "max", "range", "p10", "p90"]  # order used by rf_baseline.summarize


def _clf():
    return make_pipeline(StandardScaler(), LinearDiscriminantAnalysis(solver="lsqr", shrinkage="auto"))


def within_acc(Z, trial, person, seed: int = 0) -> float:
    correct = 0
    for p in np.unique(person):
        m = np.flatnonzero(person == p)
        k = min(5, min(np.unique(trial[m], return_counts=True)[1]))
        cv = StratifiedKFold(n_splits=k, shuffle=True, random_state=seed)
        for tr, te in cv.split(Z[m], trial[m]):
            correct += np.sum(_clf().fit(Z[m][tr], trial[m][tr]).predict(Z[m][te]) == trial[m][te])
    return correct / len(trial)


def across_acc(Z, trial, person, seed: int = 0) -> float:
    correct = 0
    for p in np.unique(person):
        te, tr = person == p, person != p
        correct += np.sum(_clf().fit(Z[tr], trial[tr]).predict(Z[te]) == trial[te])
    return correct / len(trial)


def permutation_p95(fn, Z, trial, person, n_perm: int, seed: int = 0) -> float:
    rng = np.random.default_rng(seed)
    vals = []
    for i in range(n_perm):
        t = trial.copy()
        for p in np.unique(person):
            m = np.flatnonzero(person == p)
            t[m] = rng.permutation(t[m])
        vals.append(fn(Z, t, person, seed=i))
    return float(np.percentile(vals, 95))


def feature_anova(Z, trial, person, alpha: float = 0.05) -> tuple[np.ndarray, np.ndarray]:
    """p-values per feature (participant means removed) and the BH-FDR rejection mask."""
    R = Z.copy()
    for p in np.unique(person):
        m = person == p
        R[m] -= R[m].mean(0)
    groups = [R[trial == t] for t in np.unique(trial)]
    with np.errstate(all="ignore"):
        pv = np.nan_to_num(f_oneway(*groups).pvalue, nan=1.0)
    order = np.argsort(pv)
    thresh = alpha * np.arange(1, len(pv) + 1) / len(pv)
    passed = pv[order] <= thresh
    k = np.max(np.flatnonzero(passed)) + 1 if passed.any() else 0
    reject = np.zeros(len(pv), bool)
    reject[order[:k]] = True
    return pv, reject


def run(Zs, names, trial, person, exercise, n_perm: int):
    rows, feat_rows = [], []
    for ex in sorted(set(exercise)):
        m = exercise == ex
        for rep, Z in Zs.items():
            pv, rej = feature_anova(Z[m], trial[m], person[m])
            top = [names[rep][i] for i in np.argsort(pv)[:5] if rej[i]]
            for i in np.flatnonzero(rej):
                feat_rows.append({"exercise": ex, "rep": rep, "feature": names[rep][i], "p": float(pv[i])})
            for name, fn in (("within", within_acc), ("across", across_acc)):
                acc = fn(Z[m], trial[m], person[m])
                p95 = permutation_p95(fn, Z[m], trial[m], person[m], n_perm) if n_perm else float("nan")
                rows.append({"exercise": ex, "rep": rep, "eval": name, "n": int(m.sum()), "accuracy": acc,
                             "chance": 1 / 3, "perm_p95": p95, "lda_flag": bool(n_perm and acc > p95),
                             "n_features": Z.shape[1], "n_features_fdr": int(rej.sum()),
                             "top_features": json.dumps(top)})
    return rows, feat_rows


def summary_names(root: Path, rep: str) -> list[str]:
    meta = json.loads((root / "data" / "feature_names.json").read_text(encoding="utf-8"))[rep]
    return [f"{s}({f['name']})" for s in STATS for f in meta]


def load_g3(root: Path, reps: list[str]):
    f = np.load(root / "data" / "features_T100.npz")
    keys = list(f["keys"])
    with (root / "data" / "master_index.csv").open(encoding="utf-8") as fh:
        idx = {r["rec_key"]: r for r in csv.DictReader(fh)}
    sel = [i for i, k in enumerate(keys) if idx[k]["group"] == "3" and idx[k]["g3_error"] == "C"]
    if not sel:
        return None
    meta = [idx[keys[i]] for i in sel]
    Zs = {r: summarize(f[r][sel].astype(np.float64)) for r in reps}
    names = {r: summary_names(root, r) for r in reps}
    return (Zs, names, np.array([m["trial"] for m in meta]), np.array([m["participant_key"] for m in meta]),
            np.array([m["exercise"] for m in meta]))


def check(root: Path) -> list[str]:
    fails = []
    rng = np.random.default_rng(0)
    person = np.repeat(["P1", "P2", "P3"], 15)
    trial = np.tile(np.repeat(["T1", "T2", "T3"], 5), 3)
    step = np.array([{"T1": 0.0, "T2": 1.0, "T3": 2.0}[t] for t in trial])
    noise = rng.normal(size=(45, 100))
    dense = noise.copy()
    dense[:, :30] += 1.0 * step[:, None]        # whole-skeleton style shift: 30 of 100 features move
    sparse = rng.normal(size=(45, 100))
    sparse[:, 7] += 3.0 * step                  # one feature carries the cue
    a_dense, a_noise = within_acc(dense, trial, person), within_acc(noise, trial, person)
    if a_dense < 0.8:
        fails.append(f"dense session cue not detected by the classifier (within acc {a_dense:.2f})")
    if a_noise > 0.55:
        fails.append(f"pure noise looks like a session cue (within acc {a_noise:.2f})")
    _, rej_s = feature_anova(sparse, trial, person)
    if not rej_s[7]:
        fails.append("sparse single-feature cue not found by the per-feature ANOVA")
    _, rej_n = feature_anova(noise, trial, person)
    if rej_n.sum() > 2:
        fails.append(f"per-feature ANOVA flags {rej_n.sum()} noise features at FDR 5%")
    p95 = permutation_p95(within_acc, noise, trial, person, n_perm=20)
    if not 0.2 < p95 < 0.7:
        fails.append(f"permutation 95th percentile implausible on noise: {p95:.2f}")
    # Group 3 file names: Tk must hold only C and Ek (real sample files and the full listing)
    from index import RE_G3
    for n in sorted(p.stem for p in (root / "raw" / "sample" / "group3" / "kinect").glob("*.txt")):
        m = RE_G3.match(n)
        if not m:
            fails.append(f"sample Group 3 name not parsed: {n}")
        elif m["label"] != "C" and m["label"][1] != m["trial"][1]:
            fails.append(f"{n}: error E{m['label'][1]} recorded in trial {m['trial']}")
    with (root / "data" / "master_index.csv").open(encoding="utf-8") as fh:
        g3 = [r for r in csv.DictReader(fh) if r["group"] == "3"]
    bad = [r["rec_key"] for r in g3 if r["g3_error"] != "C" and r["g3_error"][1] != r["trial"][1]]
    if bad:
        fails.append(f"{len(bad)} Group 3 recordings break the trial-error pairing, e.g. {bad[0]}")
    if len(g3) != 540:
        fails.append(f"Group 3 index has {len(g3)} rows, expected 540")
    # Dry run of the real-data path on 1A (no Group 3 yet): pseudo-trials = thirds of each patient's
    # recordings in recording-ID order. Exercises run(), summary_names() and the CSV columns end to end.
    f = np.load(root / "data" / "features_T100.npz")
    keys = list(f["keys"])
    with (root / "data" / "master_index.csv").open(encoding="utf-8") as fh:
        idx = {r["rec_key"]: r for r in csv.DictReader(fh)}
    sel = sorted((i for i, k in enumerate(keys) if idx[k]["group"] == "1A" and idx[k]["exercise"] == "CTK"),
                 key=lambda i: (idx[keys[i]]["participant_key"], int(idx[keys[i]]["rec_id"])))
    pers = np.array([idx[keys[i]]["participant_key"] for i in sel])
    pseudo = np.empty(len(sel), dtype=object)
    for p in np.unique(pers):
        m = np.flatnonzero(pers == p)
        pseudo[m] = [f"T{1 + 3 * j // len(m)}" for j in range(len(m))]
    rows, _ = run({"R2": summarize(f["R2"][sel].astype(np.float64))}, {"R2": summary_names(root, "R2")},
                  pseudo.astype(str), pers, np.array(["CTK"] * len(sel)), n_perm=5)
    if len(rows) != 2 or not all(np.isfinite(r["accuracy"]) for r in rows):
        fails.append("dry run on 1A pseudo-trials did not produce two finite rows")
    else:
        print("dry run on 1A CTK (pseudo-trials = recording order thirds, R2): "
              + ", ".join(f"{r['eval']} acc {r['accuracy']:.2f} / FDR features {r['n_features_fdr']}" for r in rows))
    print(f"self-test: dense cue acc {a_dense:.2f}, noise acc {a_noise:.2f}, sparse cue found {bool(rej_s[7])}, "
          f"noise features flagged {int(rej_n.sum())}, perm p95 on noise {p95:.2f}")
    return fails


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    ap.add_argument("--reps", default=",".join(REPS))
    ap.add_argument("--perms", type=int, default=200)
    ap.add_argument("--check", action="store_true")
    args = ap.parse_args()

    data = load_g3(args.root, args.reps.split(","))
    if data is None:
        print("ON HOLD: no Group 3 skeletons in data/features_T100.npz yet. "
              "Put the Kinect files in raw/group3/kinect/ and rerun index, preprocess and features.")
    else:
        rows, feat_rows = run(*data, n_perm=args.perms)
        for name, rs in (("trial_confound.csv", rows), ("trial_confound_features.csv", feat_rows)):
            out = args.root / "results" / name
            with out.open("w", newline="", encoding="utf-8") as f:
                if rs:
                    w = csv.DictWriter(f, fieldnames=list(rs[0]))
                    w.writeheader()
                    w.writerows(rs)
        print("wrote results/trial_confound.csv, results/trial_confound_features.csv")
        for r in rows:
            print(f"  {r['exercise']} {r['rep']:5s} {r['eval']:6s} LDA acc {r['accuracy']:.2f} (perm p95 "
                  f"{r['perm_p95']:.2f}){' CUE' if r['lda_flag'] else ''} | FDR features "
                  f"{r['n_features_fdr']}/{r['n_features']} {r['top_features']}")

    if args.check:
        fails = check(args.root)
        for x in fails:
            print("CHECK FAILED:", x)
        print("CHECK", "PASSED" if not fails else f"FAILED ({len(fails)})")
        return 1 if fails else 0
    return 0


if __name__ == "__main__":
    sys.exit(main())
