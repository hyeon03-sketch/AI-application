"""Summary-statistics + Random Forest baseline, run on any protocol in data/splits.json.

Each recording's feature sequence (T, F) is summarized per feature by mean, sd, min, max, range,
10th and 90th percentile → 7F numbers. One Random Forest per exercise (Paper 2 also trains one model per
exercise). Labels are filtered per fold: EXCL rows are dropped from both train and test.

Default run: protocol P4 (leave-one-patient-out inside 1A), every representation, annotators A and B,
5 seeds. P4 is real-to-real and within one population, so it is a smoke test of the whole pipeline and a
preliminary look at the representations — not the main (sim-to-real, P1) result.

Outputs:
  results/rf_<protocol>_runs.csv     one row per representation x exercise x annotator x seed
  results/rf_<protocol>_summary.csv  mean / sd over seeds, plus participant-bootstrap CI (seed 0)

Usage:  python src/rf_baseline.py [--protocol P4] [--reps R0,R1,...] [--seeds 0,1,2,3,4] [--check]
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
from evaluate import evaluate, majority_baseline  # noqa: E402

REPS = ["R0", "R1", "R2", "R3", "R4", "Rerr", "Rerr_d"]
N_TREES = 300


def summarize(X: np.ndarray) -> np.ndarray:
    """(N, T, F) -> (N, 7F)."""
    p10, p90 = np.percentile(X, [10, 90], axis=1)
    mn, mx = X.min(1), X.max(1)
    return np.concatenate([X.mean(1), X.std(1), mn, mx, mx - mn, p10, p90], axis=1)


def folds_of(sp: dict, protocol: str) -> list[tuple[str, list[str], list[str]]]:
    p = sp[protocol]
    if isinstance(p, list):                       # leave-one-out style: P2, P4
        return [(f["held_out"], f["train"], f["test"]) for f in p]
    if "test_1A" in p:                            # P1
        return [("1A", p["train"], p["test_1A"]), ("2A", p["train"], p["test_2A"])]
    return [(s, d["train"], d["test"]) for s, d in p.items()]  # P3_*: one "fold" per split seed


def run(root: Path, protocol: str, reps: list[str], seeds: list[int], annotators=("A", "B")):
    feats = np.load(root / "data" / "features_T100.npz")
    keys = list(feats["keys"])
    pos = {k: i for i, k in enumerate(keys)}
    with (root / "data" / "labels.csv").open(encoding="utf-8") as f:
        lab = {r["rec_key"]: r for r in csv.DictReader(f)}
    sp = json.loads((root / "data" / "splits.json").read_text(encoding="utf-8"))
    folds = folds_of(sp, protocol)
    missing = {k for _, tr, te in folds for k in tr + te if k not in pos}
    if missing:
        raise SystemExit(f"{len(missing)} recordings in {protocol} have no skeleton yet "
                         f"(e.g. {sorted(missing)[0]}); this protocol has to wait for that data.")
    Z = {r: summarize(feats[r].astype(np.float64)) for r in reps}

    runs, preds = [], {}
    for ann in annotators:
        col = f"label_{ann}"
        for ex in ("RTK", "ELK", "CTK"):
            for rep in reps + ["majority"]:
                for seed in (seeds if rep != "majority" else [0]):
                    yt_all, yp_all, g_all, k_all = [], [], [], []
                    for _, tr, te in folds:
                        tr = [k for k in tr if lab[k]["exercise"] == ex and lab[k][col] != "EXCL"]
                        te = [k for k in te if lab[k]["exercise"] == ex and lab[k][col] != "EXCL"]
                        if not tr or not te:
                            continue
                        ytr = [lab[k][col] for k in tr]
                        if rep == "majority":
                            yp = majority_baseline(ytr, te)
                        else:
                            clf = RandomForestClassifier(n_estimators=N_TREES, class_weight="balanced",
                                                         min_samples_leaf=2, random_state=seed, n_jobs=-1)
                            clf.fit(Z[rep][[pos[k] for k in tr]], ytr)
                            yp = list(clf.predict(Z[rep][[pos[k] for k in te]]))
                        yt_all += [lab[k][col] for k in te]; yp_all += yp
                        g_all += [lab[k]["participant_key"] for k in te]; k_all += te
                    res = evaluate(yt_all, yp_all, g_all, n_boot=1000 if seed == 0 else 0) if seed == 0 \
                        else evaluate(yt_all, yp_all)
                    runs.append({"protocol": protocol, "annotator": ann, "exercise": ex, "rep": rep, "seed": seed,
                                 "n": res["n"], "accuracy": res["accuracy"], "macro_f1": res["macro_f1"],
                                 "balanced_accuracy": res["balanced_accuracy"],
                                 "macro_f1_ci": res.get("macro_f1_ci"), "support": res["support"]})
                    preds[(ann, ex, rep, seed)] = (k_all, yt_all, yp_all)
    return runs, preds


def write(root: Path, protocol: str, runs: list[dict]) -> list[dict]:
    out_runs = root / "results" / f"rf_{protocol}_runs.csv"
    with out_runs.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["protocol", "annotator", "exercise", "rep", "seed", "n", "accuracy", "macro_f1", "balanced_accuracy"])
        for r in runs:
            w.writerow([r[k] for k in ("protocol", "annotator", "exercise", "rep", "seed", "n")] +
                       [f"{r[k]:.4f}" for k in ("accuracy", "macro_f1", "balanced_accuracy")])
    summary = []
    for ann in ("A", "B"):
        for ex in ("RTK", "ELK", "CTK"):
            for rep in REPS + ["majority"]:
                rs = [r for r in runs if (r["annotator"], r["exercise"], r["rep"]) == (ann, ex, rep)]
                if not rs:
                    continue
                f1 = np.array([r["macro_f1"] for r in rs]); ba = np.array([r["balanced_accuracy"] for r in rs])
                ci = next(r["macro_f1_ci"] for r in rs if r["seed"] == 0)
                summary.append({"annotator": ann, "exercise": ex, "rep": rep, "n": rs[0]["n"],
                                "support": json.dumps(rs[0]["support"]), "n_seeds": len(rs),
                                "macro_f1_mean": f1.mean(), "macro_f1_sd": f1.std(),
                                "macro_f1_ci_lo": ci[0], "macro_f1_ci_hi": ci[1],
                                "bal_acc_mean": ba.mean(), "accuracy_mean": np.mean([r["accuracy"] for r in rs])})
    out_sum = root / "results" / f"rf_{protocol}_summary.csv"
    with out_sum.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(summary[0]))
        w.writeheader()
        for s in summary:
            w.writerow({k: (f"{v:.4f}" if isinstance(v, float) else v) for k, v in s.items()})
    return summary


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    ap.add_argument("--protocol", default="P4")
    ap.add_argument("--reps", default=",".join(REPS))
    ap.add_argument("--seeds", default="0,1,2,3,4")
    ap.add_argument("--check", action="store_true", help="quick end-to-end run (2 reps, 2 seeds) with checks")
    args = ap.parse_args()
    root = args.root

    if args.check:
        reps, seeds = ["R1", "Rerr"], [0, 1]
    else:
        reps, seeds = args.reps.split(","), [int(s) for s in args.seeds.split(",")]
    runs, preds = run(root, args.protocol, reps, seeds)

    if args.check:
        fails = []
        sp = json.loads((root / "data" / "splits.json").read_text(encoding="utf-8"))
        with (root / "data" / "labels.csv").open(encoding="utf-8") as f:
            lab = {r["rec_key"]: r for r in csv.DictReader(f)}
        for ann in ("A", "B"):
            for ex in ("RTK", "ELK", "CTK"):
                n_expected = sum(1 for f_ in folds_of(sp, args.protocol) for k in f_[2]
                                 if lab[k]["exercise"] == ex and lab[k][f"label_{ann}"] != "EXCL")
                k_all = preds[(ann, ex, "R1", 0)][0]
                if len(k_all) != n_expected or len(set(k_all)) != n_expected:
                    fails.append(f"{ann} {ex}: {len(k_all)} out-of-fold predictions, expected {n_expected} unique")
        if any(not np.isfinite(r["macro_f1"]) for r in runs):
            fails.append("non-finite macro-F1")
        again, _ = run(root, args.protocol, ["Rerr"], [0], annotators=("A",))
        first = [r["macro_f1"] for r in runs if r["rep"] == "Rerr" and r["seed"] == 0 and r["annotator"] == "A"]
        if [r["macro_f1"] for r in again if r["rep"] == "Rerr"] != first:
            fails.append("same seed gave different results (not reproducible)")
        for x in fails:
            print("CHECK FAILED:", x)
        print(f"end-to-end run on {args.protocol}: {len(runs)} runs")
        print("CHECK", "PASSED" if not fails else f"FAILED ({len(fails)})")
        return 1 if fails else 0

    summary = write(root, args.protocol, runs)
    # out-of-fold predictions, for paired comparisons between representations (compare_reps.py)
    with (root / "results" / f"rf_{args.protocol}_preds.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["annotator", "exercise", "rep", "seed", "rec_key", "y_true", "y_pred"])
        for (ann, ex, rep, seed), (ks, yt, yp) in sorted(preds.items()):
            for k, t, p in zip(ks, yt, yp):
                w.writerow([ann, ex, rep, seed, k, t, p])
    print(f"wrote results/rf_{args.protocol}_runs.csv and results/rf_{args.protocol}_summary.csv")
    print(f"{args.protocol}: Macro-F1 mean ± sd over seeds [participant bootstrap 95% CI, seed 0]")
    for s in summary:
        print(f"  {s['annotator']} {s['exercise']} {s['rep']:8s} {s['macro_f1_mean']:.3f} ± {s['macro_f1_sd']:.3f} "
              f"[{s['macro_f1_ci_lo']:.3f}, {s['macro_f1_ci_hi']:.3f}]  bal-acc {s['bal_acc_mean']:.3f}  n={s['n']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
