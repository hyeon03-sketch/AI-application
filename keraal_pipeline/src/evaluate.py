"""Metrics for small, imbalanced, participant-clustered test sets (numpy only).

  macro_f1           mean F1 over the classes PRESENT in y_true. Predictions of absent classes still count
                     as errors (they lower recall of the true class) but absent classes are not averaged in.
  balanced_accuracy  mean recall over the classes present in y_true
  per_class_recall   recall per present class
  bootstrap_ci       95% percentile interval, resampling whole participants with replacement
  majority_baseline  predict one class everywhere (the training majority; the test majority is reported
                     separately because it peeks at the test labels)

evaluate(y_true, y_pred, groups) returns all of the above in one dict.

Usage:  python src/evaluate.py [--check]
  Without models yet, the CLI reports the majority baselines for the P1 test sets (1A, 2A, 1A+2A),
  for annotator A and B labels, with participant bootstrap intervals.
"""
from __future__ import annotations

import argparse
import csv
import json
import sys
from collections import Counter
from pathlib import Path

import numpy as np

N_BOOT = 2000


def confusion(y_true, y_pred, classes) -> np.ndarray:
    idx = {c: i for i, c in enumerate(classes)}
    m = np.zeros((len(classes), len(classes)), dtype=int)
    for t, p in zip(y_true, y_pred):
        if t in idx and p in idx:
            m[idx[t], idx[p]] += 1
    return m


def per_class(y_true, y_pred) -> dict[str, dict[str, float]]:
    y_true, y_pred = np.asarray(y_true), np.asarray(y_pred)
    out = {}
    for c in sorted(set(y_true.tolist())):
        tp = np.sum((y_true == c) & (y_pred == c))
        fn = np.sum((y_true == c) & (y_pred != c))
        fp = np.sum((y_true != c) & (y_pred == c))
        rec = tp / (tp + fn) if tp + fn else 0.0
        prec = tp / (tp + fp) if tp + fp else 0.0
        f1 = 2 * prec * rec / (prec + rec) if prec + rec else 0.0
        out[c] = {"recall": float(rec), "precision": float(prec), "f1": float(f1), "support": int(tp + fn)}
    return out


def macro_f1(y_true, y_pred) -> float:
    pc = per_class(y_true, y_pred)
    return float(np.mean([v["f1"] for v in pc.values()])) if pc else float("nan")


def balanced_accuracy(y_true, y_pred) -> float:
    pc = per_class(y_true, y_pred)
    return float(np.mean([v["recall"] for v in pc.values()])) if pc else float("nan")


def accuracy(y_true, y_pred) -> float:
    return float(np.mean(np.asarray(y_true) == np.asarray(y_pred))) if len(y_true) else float("nan")


def bootstrap_ci(y_true, y_pred, groups, metric, n_boot: int = N_BOOT, seed: int = 0) -> tuple[float, float]:
    """Percentile 95% CI resampling whole participants (clusters) with replacement."""
    y_true, y_pred, groups = map(np.asarray, (y_true, y_pred, groups))
    ids = np.unique(groups)
    if len(ids) < 2:
        return (float("nan"), float("nan"))
    members = [np.flatnonzero(groups == g) for g in ids]
    rng = np.random.default_rng(seed)
    vals = []
    for _ in range(n_boot):
        pick = np.concatenate([members[i] for i in rng.integers(0, len(ids), len(ids))])
        vals.append(metric(y_true[pick], y_pred[pick]))
    lo, hi = np.nanpercentile(vals, [2.5, 97.5])
    return float(lo), float(hi)


def paired_bootstrap_diff(y_true, preds_a, preds_b, groups, metric, n_boot: int = N_BOOT, seed: int = 0) -> dict:
    """Difference metric(A) - metric(B) on the SAME participant resamples.

    preds_a / preds_b: one prediction list per training seed (lists of equal length to y_true). Within each
    resample the metric is averaged over seeds, so the interval covers participant sampling and seed noise.
    Returns the observed difference, its percentile 95% CI and a two-sided bootstrap p-value
    (twice the share of resamples on the other side of zero, capped at 1).
    """
    y = np.asarray(y_true)
    A = [np.asarray(p) for p in preds_a]
    Bp = [np.asarray(p) for p in preds_b]
    groups = np.asarray(groups)

    def diff(idx):
        return (np.mean([metric(y[idx], a[idx]) for a in A]) - np.mean([metric(y[idx], b[idx]) for b in Bp]))

    obs = float(diff(np.arange(len(y))))
    ids = np.unique(groups)
    members = [np.flatnonzero(groups == g) for g in ids]
    rng = np.random.default_rng(seed)
    vals = np.array([diff(np.concatenate([members[i] for i in rng.integers(0, len(ids), len(ids))]))
                     for _ in range(n_boot)])
    lo, hi = np.nanpercentile(vals, [2.5, 97.5])
    side = np.mean(vals <= 0) if obs > 0 else np.mean(vals >= 0)
    return {"diff": obs, "lo": float(lo), "hi": float(hi), "p": float(min(1.0, 2 * side))}


def majority_baseline(y_train, y_test) -> list[str]:
    counts = Counter(y_train)
    top = max(counts.values())
    winner = sorted(c for c, n in counts.items() if n == top)[0]  # deterministic tie-break
    return [winner] * len(y_test)


def evaluate(y_true, y_pred, groups=None, n_boot: int = N_BOOT, seed: int = 0) -> dict:
    res = {
        "n": len(y_true),
        "support": dict(sorted(Counter(y_true).items())),
        "accuracy": accuracy(y_true, y_pred),
        "macro_f1": macro_f1(y_true, y_pred),
        "balanced_accuracy": balanced_accuracy(y_true, y_pred),
        "per_class": per_class(y_true, y_pred),
    }
    if groups is not None:
        res["n_participants"] = len(set(groups))
        res["macro_f1_ci"] = bootstrap_ci(y_true, y_pred, groups, macro_f1, n_boot, seed)
        res["balanced_accuracy_ci"] = bootstrap_ci(y_true, y_pred, groups, balanced_accuracy, n_boot, seed)
    return res


# ----------------------------------------------------------------------------- checks

def check() -> list[str]:
    fails = []
    # hand-computed example: classes present C, E1; one prediction of an absent class (E2)
    yt = ["C", "C", "C", "E1", "E1"]
    yp = ["C", "C", "E1", "E1", "E2"]
    # C: tp2 fp0 fn1 -> P1 R.667 F.8 ; E1: tp1 fp1 fn1 -> P.5 R.5 F.5 ; macro .65 ; bal (.667+.5)/2
    if abs(macro_f1(yt, yp) - 0.65) > 1e-9:
        fails.append(f"macro_f1 hand example: {macro_f1(yt, yp)} != 0.65")
    if abs(balanced_accuracy(yt, yp) - (2 / 3 + 0.5) / 2) > 1e-9:
        fails.append("balanced_accuracy hand example")
    # majority predictor: macro-F1 = F1(majority)/K, balanced accuracy = 1/K
    yt2 = ["C"] * 72 + ["E1"] * 4 + ["E2"] * 6
    yp2 = majority_baseline(yt2, yt2)
    p = 72 / 82
    if abs(macro_f1(yt2, yp2) - (2 * p / (p + 1)) / 3) > 1e-9 or abs(balanced_accuracy(yt2, yp2) - 1 / 3) > 1e-9:
        fails.append("majority closed form")
    if abs(accuracy(yt2, yp2) - 72 / 82) > 1e-9:
        fails.append("accuracy of majority on Paper 2's RTK test counts should be 87.8%")
    # agreement with scikit-learn on random data (labels restricted to classes present in y_true)
    try:
        from sklearn.metrics import balanced_accuracy_score, f1_score
        rng = np.random.default_rng(1)
        for _ in range(50):
            classes = np.array(["C", "E1", "E2", "E3"])
            t = classes[rng.integers(0, 3, 40)]          # E3 absent from truth
            q = classes[rng.integers(0, 4, 40)]          # but may be predicted
            present = sorted(set(t))
            sk_f1 = f1_score(t, q, labels=present, average="macro", zero_division=0)
            if abs(sk_f1 - macro_f1(t, q)) > 1e-9:
                fails.append(f"macro_f1 differs from sklearn: {macro_f1(t, q)} vs {sk_f1}")
                break
            sk_bal = np.mean([np.mean(q[t == c] == c) for c in present])
            if abs(sk_bal - balanced_accuracy(t, q)) > 1e-9:
                fails.append("balanced_accuracy differs from per-class recall mean")
                break
            if set(q) <= set(t) and abs(balanced_accuracy_score(t, q) - balanced_accuracy(t, q)) > 1e-9:
                fails.append("balanced_accuracy differs from sklearn")
                break
    except ImportError:
        fails.append("scikit-learn not installed; cannot cross-check")
    # bootstrap: identical perfect predictions give a degenerate interval at 1.0
    g = ["a"] * 3 + ["b"] * 3 + ["c"] * 3
    t3 = ["C", "E1", "C", "C", "E1", "E1", "C", "E1", "C"]
    lo, hi = bootstrap_ci(t3, t3, g, macro_f1, n_boot=200)
    if not (lo == hi == 1.0):
        fails.append(f"bootstrap of perfect predictions should be [1, 1], got [{lo}, {hi}]")
    # bootstrap is deterministic for a fixed seed
    yp3 = ["C"] * 9
    if bootstrap_ci(t3, yp3, g, macro_f1, 200, 7) != bootstrap_ci(t3, yp3, g, macro_f1, 200, 7):
        fails.append("bootstrap not reproducible for a fixed seed")
    return fails


# ----------------------------------------------------------------------------- CLI report

def baseline_report(root: Path) -> list[dict]:
    with (root / "data" / "labels.csv").open(encoding="utf-8") as f:
        lab = {r["rec_key"]: r for r in csv.DictReader(f)}
    sp = json.loads((root / "data" / "splits.json").read_text(encoding="utf-8"))
    sets = {"1A": sp["P1"]["test_1A"], "2A": sp["P1"]["test_2A"], "1A+2A": sp["P1"]["test_1A"] + sp["P1"]["test_2A"]}
    rows = []
    for ann in ("A", "B"):
        col = f"label_{ann}"
        for ex in ("RTK", "ELK", "CTK"):
            for name, keys in sets.items():
                ks = [k for k in keys if lab[k]["exercise"] == ex and lab[k][col] != "EXCL"]
                yt = [lab[k][col] for k in ks]
                if not yt:
                    continue
                g = [lab[k]["participant_key"] for k in ks]
                # G3 (P1 train) is balanced at 45 per class, so its majority is a tie; the test majority is
                # the stronger (and optimistic) reference, as in KERAAL_Pipeline_KR.pdf section 1.
                res = evaluate(yt, majority_baseline(yt, yt), g)
                rows.append({"annotator": ann, "exercise": ex, "test": name, **res})
    return rows


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    ap.add_argument("--check", action="store_true")
    args = ap.parse_args()

    rows = baseline_report(args.root)
    out = args.root / "results" / "baseline_majority_P1.csv"
    out.parent.mkdir(exist_ok=True)
    with out.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["annotator", "exercise", "test", "n", "n_participants", "support", "accuracy",
                    "macro_f1", "macro_f1_lo", "macro_f1_hi", "balanced_accuracy"])
        for r in rows:
            w.writerow([r["annotator"], r["exercise"], r["test"], r["n"], r["n_participants"],
                        json.dumps(r["support"]), f"{r['accuracy']:.4f}", f"{r['macro_f1']:.4f}",
                        f"{r['macro_f1_ci'][0]:.4f}", f"{r['macro_f1_ci'][1]:.4f}", f"{r['balanced_accuracy']:.4f}"])
    print(f"wrote {out.relative_to(args.root).as_posix()}")
    print("majority baseline on P1 test sets (test-majority class predicted everywhere):")
    for r in rows:
        if r["test"] == "1A+2A":
            lo, hi = r["macro_f1_ci"]
            print(f"  {r['annotator']} {r['exercise']}: n={r['n']:3d} acc {r['accuracy']:.1%}  "
                  f"macro-F1 {r['macro_f1']:.3f} [{lo:.3f}, {hi:.3f}]  bal-acc {r['balanced_accuracy']:.3f}  "
                  f"support {r['support']}")

    if args.check:
        fails = check()
        expect = {("A", "RTK"): 0.880, ("B", "RTK"): 0.644, ("A", "ELK"): 0.544,
                  ("B", "ELK"): 0.779, ("A", "CTK"): 0.581, ("B", "CTK"): 0.600}
        for r in rows:
            k = (r["annotator"], r["exercise"])
            if r["test"] == "1A+2A" and abs(r["accuracy"] - expect[k]) > 0.0006:
                fails.append(f"majority accuracy {k}: {r['accuracy']:.4f}, expected {expect[k]} (PDF section 1)")
        for x in fails:
            print("CHECK FAILED:", x)
        print("CHECK", "PASSED" if not fails else f"FAILED ({len(fails)})")
        return 1 if fails else 0
    return 0


if __name__ == "__main__":
    sys.exit(main())
