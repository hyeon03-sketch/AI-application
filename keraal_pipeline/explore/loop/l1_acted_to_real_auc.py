"""L1 (exploratory): AUC of the acted -> real direction (P1: train Group 3, test 1A / 2A).

The confirmatory run (PREREGISTRATION.md) scored hard labels with Macro-F1 and failed: the Group 3 models called
92-97 % of test recordings errors. This asks the threshold question directly: do the same models still RANK the
test recordings correctly? High AUC with low Macro-F1 = the models can tell errors apart but their decision
threshold sits in the wrong place.

Same task, representations, models and seeds as configs/p1_confirmatory.json (read only, never written), but the
models output probabilities. Reported per annotator, model and representation:
  auc_pooled        AUC over all test recordings (1A + 2A)
  auc_1A / auc_2A   per test group
  auc_within_mean   mean AUC inside each test participant that has both classes (removes between-person level)
  null_p95, p       within-participant label shuffles (1,000): pooled AUC under "no within-person ranking"
  pred_err_rate     share predicted E13 at threshold 0.5 (the confirmatory failure mode); true_err_rate for reference
  f1_at_0.5         Macro-F1 at the default threshold
  f1_best_oracle    Macro-F1 at the best threshold chosen ON THE TEST SET: an upper bound, not a result

Output: explore/loop/l1_acted_to_real_auc.csv (+ .md). Aggregates only, no per-recording values.
Usage: python explore/loop/l1_acted_to_real_auc.py [--perms 1000] [--check]
"""
from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path

import numpy as np
from sklearn.metrics import f1_score, roc_auc_score

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))
from rf_baseline import folds_of, summarize  # noqa: E402
from run_experiment import make_model, model_name  # noqa: E402

POS = "E13"


def within_auc(y, s, g):
    vals = []
    for p in np.unique(g):
        m = g == p
        if len(np.unique(y[m])) == 2:
            vals.append(roc_auc_score(y[m], s[m]))
    return (float(np.mean(vals)) if vals else float("nan")), len(vals)


def shuffle_within(y, g, rng):
    out = y.copy()
    for p in np.unique(g):
        idx = np.flatnonzero(g == p)
        out[idx] = rng.permutation(y[idx])
    return out


def best_f1(y, s):
    best = 0.0
    for t in np.unique(s):
        best = max(best, f1_score(y, (s >= t).astype(int), average="macro"))
    return best


def run(root: Path, perms: int):
    cfg = json.loads((root / "configs" / "p1_confirmatory.json").read_text(encoding="utf-8"))
    feats = np.load(root / "data" / "features_T100.npz")
    pos = {k: i for i, k in enumerate(feats["keys"])}
    with (root / "data" / "labels.csv").open(encoding="utf-8") as f:
        lab = {r["rec_key"]: r for r in csv.DictReader(f)}
    sp = json.loads((root / "data" / "splits.json").read_text(encoding="utf-8"))
    folds = folds_of(sp, "P1")
    train = folds[0][1]
    test = [k for _, _, te in folds for k in te]
    Z = {r: summarize(feats[r].astype(np.float64)) for r in cfg["reps"]}
    rng = np.random.default_rng(0)
    rows = []
    for task in cfg["tasks"]:
        col, ex, keep = task["label_col"], task["exercise"], task["classes"]
        ok = lambda k: lab[k]["exercise"] == ex and lab[k][col] in keep  # noqa: E731
        tr = [k for k in train if ok(k)]
        te = [k for k in test if ok(k)]
        ytr = [lab[k][col] for k in tr]
        y = np.array([lab[k][col] == POS for k in te], dtype=int)
        g = np.array([lab[k]["participant_key"] for k in te])
        grp = np.array([lab[k]["group"] for k in te])
        for model in [m for m in cfg["models"] if m["type"] != "majority"]:
            for rep in cfg["reps"]:
                per_seed = []
                for seed in cfg["seeds"]:
                    clf = make_model(model, seed).fit(Z[rep][[pos[k] for k in tr]], ytr)
                    s = clf.predict_proba(Z[rep][[pos[k] for k in te]])[:, list(clf.classes_).index(POS)]
                    per_seed.append(s)
                    if model["type"] == "logreg":
                        break  # deterministic
                s = np.mean(per_seed, axis=0)  # seed-averaged probability
                auc = roc_auc_score(y, s)
                null = np.array([roc_auc_score(shuffle_within(y, g, rng), s) for _ in range(perms)])
                wa, n_within = within_auc(y, s, g)
                rows.append({
                    "annotator": col.split("_")[1], "model": model_name(model), "rep": rep,
                    "n": len(te), "participants": len(set(g)), "n_within": n_within,
                    "true_err_rate": y.mean(), "pred_err_rate": float((s >= 0.5).mean()),
                    "auc_pooled": auc,
                    "auc_1A": roc_auc_score(y[grp == "1A"], s[grp == "1A"]) if len(set(y[grp == "1A"])) == 2 else float("nan"),
                    "auc_2A": roc_auc_score(y[grp == "2A"], s[grp == "2A"]) if len(set(y[grp == "2A"])) == 2 else float("nan"),
                    "auc_within_mean": wa,
                    "null_p95": float(np.percentile(null, 95)), "p": float((1 + (null >= auc).sum()) / (perms + 1)),
                    "f1_at_0.5": f1_score(y, (s >= 0.5).astype(int), average="macro"),
                    "f1_best_oracle": best_f1(y, s),
                })
    return rows


def write(rows, out: Path):
    fmt = lambda v: f"{v:.3f}" if isinstance(v, float) else v  # noqa: E731
    with out.with_suffix(".csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        for r in rows:
            w.writerow({k: fmt(v) for k, v in r.items()})
    cols = ["annotator", "model", "rep", "auc_pooled", "null_p95", "p", "auc_1A", "auc_2A", "auc_within_mean",
            "pred_err_rate", "true_err_rate", "f1_at_0.5", "f1_best_oracle"]
    lines = ["# L1 · 연기 → 실제 방향 AUC (탐색) / acted -> real AUC (exploratory)", "",
             f"P1 (G3 학습 → 1A·2A 시험), CTK C vs E13, n = {rows[0]['n']}, 참가자 {rows[0]['participants']}명. "
             "AUC 기준선(우연) = 0.5. `f1_best_oracle`은 시험셋에서 고른 기준점이라 상한일 뿐이다.", "",
             "| " + " | ".join(cols) + " |", "|" + "---|" * len(cols)]
    lines += ["| " + " | ".join(str(fmt(r[c])) for c in cols) + " |" for r in rows]
    out.with_suffix(".md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--perms", type=int, default=1000)
    ap.add_argument("--check", action="store_true")
    a = ap.parse_args()
    if a.check:  # helpers on synthetic data
        rng = np.random.default_rng(1)
        y = np.array([0, 1] * 20); g = np.repeat(np.arange(4), 10); s = y + rng.normal(0, 0.1, 40)
        ok = (within_auc(y, s, g)[0] == 1.0 and best_f1(y, s) == 1.0
              and all((shuffle_within(y, g, rng)[g == p].sum() == y[g == p].sum()) for p in range(4)))
        print("CHECK", "PASSED" if ok else "FAILED")
        return 0 if ok else 1
    rows = run(ROOT, a.perms)
    out = Path(__file__).resolve().parent / "l1_acted_to_real_auc"
    write(rows, out)
    print(out.with_suffix(".md").read_text(encoding="utf-8"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
