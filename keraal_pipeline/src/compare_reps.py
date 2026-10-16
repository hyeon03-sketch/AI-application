"""Paired comparisons between representations → results/compare_reps_<P>.csv

For each annotator x exercise and each pair (A, B) below, the Macro-F1 difference A - B is computed on the
same participant bootstrap resamples (2000), averaging over the 5 training seeds inside each resample
(evaluate.paired_bootstrap_diff). This is the statistic a claim like "kinematic features improve over raw
coordinates" needs; separate confidence intervals per model overlap far more than the paired difference does.

Pairs (the representation ladder and the questions from PROGRESS.md):
  R1 - R0      does normalization help?
  R2 - R1      angles instead of normalized positions
  R3 - R2      adding velocities
  R4 - R3      adding left-right differences
  Rerr - R1    error-specific features vs normalized positions
  Rerr_d - Rerr  baseline-relative vs absolute error features
  R0 - majority, Rerr - majority  sanity anchors

Input: results/rf_<P>_preds.csv from rf_baseline.py (full run).

Usage:  python src/compare_reps.py [--protocol P4] [--check]
"""
from __future__ import annotations

import argparse
import csv
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from evaluate import macro_f1, paired_bootstrap_diff  # noqa: E402

PAIRS = [("R1", "R0"), ("R2", "R1"), ("R3", "R2"), ("R4", "R3"), ("Rerr", "R1"), ("Rerr_d", "Rerr"),
         ("R0", "majority"), ("Rerr", "majority")]


def load_preds(path: Path) -> dict:
    """(annotator, exercise, rep) -> (rec_keys, y_true, {seed: y_pred})"""
    acc = defaultdict(lambda: {"keys": None, "y": None, "seeds": {}})
    rows = defaultdict(list)
    with path.open(encoding="utf-8") as f:
        for r in csv.DictReader(f):
            rows[(r["annotator"], r["exercise"], r["rep"], int(r["seed"]))].append(r)
    for (ann, ex, rep, seed), rs in rows.items():
        rs.sort(key=lambda r: r["rec_key"])
        d = acc[(ann, ex, rep)]
        keys = [r["rec_key"] for r in rs]
        if d["keys"] is None:
            d["keys"], d["y"] = keys, [r["y_true"] for r in rs]
        elif d["keys"] != keys:
            raise ValueError(f"recordings differ between seeds for {(ann, ex, rep)}")
        d["seeds"][seed] = [r["y_pred"] for r in rs]
    return dict(acc)


def compare(preds: dict, groups_of: dict, n_boot: int = 2000) -> list[dict]:
    out = []
    for ann in ("A", "B"):
        for ex in ("RTK", "ELK", "CTK"):
            for a, b in PAIRS:
                da, db = preds.get((ann, ex, a)), preds.get((ann, ex, b))
                if not da or not db:
                    continue
                if da["keys"] != db["keys"] or da["y"] != db["y"]:
                    raise ValueError(f"{ann} {ex}: {a} and {b} were evaluated on different recordings")
                g = [groups_of[k] for k in da["keys"]]
                res = paired_bootstrap_diff(da["y"], list(da["seeds"].values()), list(db["seeds"].values()),
                                            g, macro_f1, n_boot=n_boot)
                out.append({"annotator": ann, "exercise": ex, "a": a, "b": b, "n": len(g),
                            "participants": len(set(g)), **res,
                            "verdict": "A>B" if res["lo"] > 0 else ("A<B" if res["hi"] < 0 else "no difference shown")})
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    ap.add_argument("--protocol", default="P4")
    ap.add_argument("--check", action="store_true")
    args = ap.parse_args()
    root = args.root
    with (root / "data" / "labels.csv").open(encoding="utf-8") as f:
        groups_of = {r["rec_key"]: r["participant_key"] for r in csv.DictReader(f)}
    path = root / "results" / f"rf_{args.protocol}_preds.csv"
    if not path.exists():
        print(f"ON HOLD: {path.name} missing; run `python src/rf_baseline.py --protocol {args.protocol}` first")
        return 1 if args.check else 0
    preds = load_preds(path)

    if args.check:
        fails = []
        # the saved predictions must reproduce the Macro-F1 values in the runs file
        with (root / "results" / f"rf_{args.protocol}_runs.csv").open(encoding="utf-8") as f:
            runs = {(r["annotator"], r["exercise"], r["rep"], int(r["seed"])): float(r["macro_f1"]) for r in csv.DictReader(f)}
        for (ann, ex, rep), d in preds.items():
            for seed, yp in d["seeds"].items():
                if abs(macro_f1(d["y"], yp) - runs[(ann, ex, rep, seed)]) > 1e-4:
                    fails.append(f"{ann} {ex} {rep} seed {seed}: saved predictions do not reproduce macro-F1")
        res = compare({k: v for k, v in preds.items() if k[:2] == ("A", "CTK")}, groups_of, n_boot=200)
        if not res or not all(r["lo"] <= r["diff"] <= r["hi"] for r in res):
            fails.append("paired comparison failed or observed difference outside its own interval")
        for x in fails:
            print("CHECK FAILED:", x)
        print(f"{sum(len(d['seeds']) for d in preds.values())} saved prediction sets re-scored; "
              f"{len(res)} paired comparisons on A CTK (200 resamples)")
        print("CHECK", "PASSED" if not fails else f"FAILED ({len(fails)})")
        return 1 if fails else 0

    rows = compare(preds, groups_of)
    out = root / "results" / f"compare_reps_{args.protocol}.csv"
    with out.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        for r in rows:
            w.writerow({k: (f"{v:.4f}" if isinstance(v, float) else v) for k, v in r.items()})
    print(f"wrote {out.relative_to(root).as_posix()}")
    print(f"{args.protocol}: Macro-F1 difference A - B, paired participant bootstrap 95% CI (5 seeds averaged)")
    for r in rows:
        print(f"  {r['annotator']} {r['exercise']} {r['a']:>6s} - {r['b']:<8s} {r['diff']:+.3f} "
              f"[{r['lo']:+.3f}, {r['hi']:+.3f}] p={r['p']:.3f}  {r['verdict']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
