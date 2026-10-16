"""Participant-level permutation null for leave-one-participant-out scores → results/permutation_null_<P>.csv

How high can Macro-F1 go by chance when labels are clustered within people? Each permutation hands every
participant the label set of another participant (a random derangement-free shuffle of participants),
keeping the within-person clustering (ICC) intact but breaking any link between that person's movements
and the labels. The same model is then evaluated exactly as for the real labels.

  observed  Macro-F1 with the real labels
  null_p95  95th percentile of the permutation distribution
  p         (1 + #{null >= observed}) / (1 + n_perm)

Model: Random Forest on summary statistics (as rf_baseline.py) but 100 trees and one seed so that a few
hundred refits per cell stay affordable; the observed score is recomputed with the same settings.

Usage:  python src/permutation_null.py [--protocol P4] [--sets R0,R1,Rerr,camera] [--perms 100] [--check]
        python src/permutation_null.py --config configs/main_binary.json --sets R0,R1,R2,Rerr,Rerr_d
            (tasks and models from a run_experiment config; logreg is refit exactly, rf uses 100 trees)
"""
from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path

import numpy as np
from joblib import Parallel, delayed
from sklearn.ensemble import RandomForestClassifier

sys.path.insert(0, str(Path(__file__).resolve().parent))
from evaluate import macro_f1  # noqa: E402
from person_confound import SETS, static_features  # noqa: E402
from rf_baseline import folds_of, summarize  # noqa: E402
from run_experiment import make_model, model_name  # noqa: E402

N_TREES_NULL = 100


def permute_by_participant(y: np.ndarray, groups: np.ndarray, rng, return_mapping: bool = False):
    """Give each participant the (shuffled) labels of another participant, resized to its own count."""
    ids = np.unique(groups)
    perm = rng.permutation(ids)
    out = np.empty_like(y)
    for src, dst in zip(perm, ids):
        donor = rng.permutation(y[groups == src])
        n = int(np.sum(groups == dst))
        out[groups == dst] = np.resize(donor, n)  # repeat or truncate to the receiver's size
    return (out, dict(zip(ids, perm))) if return_mapping else out


def _model(spec: dict | None, seed: int):
    if spec is None or spec["type"] == "rf":
        return RandomForestClassifier(n_estimators=N_TREES_NULL, class_weight="balanced", min_samples_leaf=2,
                                      random_state=seed, n_jobs=1)
    return make_model(spec, seed)  # logreg is cheap enough to use exactly as in run_experiment.py


def loo_score(X: np.ndarray, y: np.ndarray, groups: np.ndarray, fold_ids: list[np.ndarray], seed: int = 0,
              model: dict | None = None) -> float:
    pred = np.empty_like(y)
    for te in fold_ids:
        tr = np.setdiff1d(np.arange(len(y)), te)
        if len(set(y[tr])) < 2:  # a permutation can leave one class on the training side
            pred[te] = y[tr][0]
            continue
        pred[te] = _model(model, seed).fit(X[tr], y[tr]).predict(X[te])
    return macro_f1(list(y), list(pred))


def feature_matrix(root: Path, name: str, keys: list[str]) -> np.ndarray:
    if name in SETS:
        raw = np.load(root / "data" / "skeleton_raw.npz")
        return np.array([[static_features(raw[k].astype(np.float64))[c] for c in SETS[name]] for k in keys])
    f = np.load(root / "data" / "features_T100.npz")
    pos = {k: i for i, k in enumerate(f["keys"])}
    return summarize(f[name][[pos[k] for k in keys]].astype(np.float64))


def cell(root: Path, protocol: str, ann: str, ex: str, sets: list[str], n_perm: int, seed: int = 0) -> list[dict]:
    with (root / "data" / "labels.csv").open(encoding="utf-8") as f:
        lab = {r["rec_key"]: r for r in csv.DictReader(f)}
    folds = folds_of(json.loads((root / "data" / "splits.json").read_text(encoding="utf-8")), protocol)
    col = f"label_{ann}"
    keys = sorted({k for _, _, te in folds for k in te if lab[k]["exercise"] == ex and lab[k][col] != "EXCL"})
    y = np.array([lab[k][col] for k in keys])
    g = np.array([lab[k]["participant_key"] for k in keys])
    pos = {k: i for i, k in enumerate(keys)}
    fold_ids = [np.array([pos[k] for k in te if k in pos]) for _, _, te in folds]
    fold_ids = [f for f in fold_ids if len(f)]
    rng = np.random.default_rng(seed)
    perms = [permute_by_participant(y, g, rng) for _ in range(n_perm)]
    rows = []
    for name in sets:
        X = feature_matrix(root, name, keys)
        obs = loo_score(X, y, g, fold_ids, seed)
        null = np.array(Parallel(n_jobs=-1)(delayed(loo_score)(X, yp, g, fold_ids, seed) for yp in perms))
        rows.append({"protocol": protocol, "annotator": ann, "exercise": ex, "features": name, "n": len(y),
                     "participants": len(set(g)), "observed": obs, "null_mean": float(null.mean()),
                     "null_p95": float(np.percentile(null, 95)),
                     "p": float((1 + np.sum(null >= obs)) / (1 + n_perm)), "n_perm": n_perm})
    return rows


def cell_task(root: Path, protocol: str, task: dict, reps: list[str], models: list[dict], n_perm: int,
              seed: int = 0) -> list[dict]:
    """Same null for a run_experiment task definition (label_col + optional classes) and model specs."""
    with (root / "data" / "labels.csv").open(encoding="utf-8") as f:
        lab = {r["rec_key"]: r for r in csv.DictReader(f)}
    folds = folds_of(json.loads((root / "data" / "splits.json").read_text(encoding="utf-8")), protocol)
    col, keep = task["label_col"], task.get("classes")
    keys = sorted({k for _, _, te in folds for k in te if lab[k]["exercise"] == task["exercise"]
                   and lab[k][col] != "EXCL" and (keep is None or lab[k][col] in keep)})
    y = np.array([lab[k][col] for k in keys])
    g = np.array([lab[k]["participant_key"] for k in keys])
    pos = {k: i for i, k in enumerate(keys)}
    fold_ids = [f for f in ([np.array([pos[k] for k in te if k in pos]) for _, _, te in folds]) if len(f)]
    rng = np.random.default_rng(seed)
    perms = [permute_by_participant(y, g, rng) for _ in range(n_perm)]
    rows = []
    for rep in reps:
        X = feature_matrix(root, rep, keys)
        for m in models:
            obs = loo_score(X, y, g, fold_ids, seed, m)
            null = np.array(Parallel(n_jobs=-1)(delayed(loo_score)(X, yp, g, fold_ids, seed, m) for yp in perms))
            rows.append({"protocol": protocol, "task": task["name"], "rep": rep,
                         "model": model_name(m) + (f"[{N_TREES_NULL} trees]" if m["type"] == "rf" else ""),
                         "n": len(y), "participants": len(set(g)), "observed": obs, "null_mean": float(null.mean()),
                         "null_p95": float(np.percentile(null, 95)),
                         "p": float((1 + np.sum(null >= obs)) / (1 + n_perm)), "n_perm": n_perm})
    return rows


def check() -> list[str]:
    fails = []
    rng = np.random.default_rng(0)
    g = np.repeat(["a", "b", "c", "d"], [5, 3, 4, 2])
    y = np.array(["C"] * 5 + ["E2"] * 3 + ["C", "C", "E2", "C"] + ["E2", "E2"])
    for _ in range(50):
        yp, mapping = permute_by_participant(y, g, rng, return_mapping=True)
        if len(yp) != len(y) or sorted(mapping.values()) != sorted(mapping):
            fails.append("permutation is not a one-to-one reassignment of participants"); break
        if any(not set(yp[g == dst]) <= set(y[g == src]) for dst, src in mapping.items()):
            fails.append("a participant received labels its donor does not have"); break
    # a pure-noise feature set must give p well above 0.05 on clustered labels; a label-encoding feature must not
    groups = np.repeat(np.arange(6), 12)
    yy = np.where(np.isin(groups, [0, 2, 4]), "E2", "C")
    folds = [np.flatnonzero(groups == i) for i in range(6)]
    Xn = rng.normal(size=(72, 5))
    Xs = Xn.copy(); Xs[:, 0] += (yy == "E2") * 3.0
    perms = [permute_by_participant(yy, groups, rng) for _ in range(30)]
    obs_n, obs_s = loo_score(Xn, yy, groups, folds), loo_score(Xs, yy, groups, folds)
    null_n = [loo_score(Xn, p, groups, folds) for p in perms]
    if obs_s < 0.9:
        fails.append(f"a feature that encodes the label scored only {obs_s:.2f}")
    if (1 + sum(v >= obs_n for v in null_n)) / 31 < 0.05:
        fails.append("pure noise came out significant against the participant null")
    print(f"self-test: label-encoding feature {obs_s:.2f}, noise {obs_n:.2f} vs null p95 {np.percentile(null_n, 95):.2f}")
    return fails


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    ap.add_argument("--protocol", default="P4")
    ap.add_argument("--sets", default="R0,R1,Rerr,camera")
    ap.add_argument("--perms", type=int, default=100)
    ap.add_argument("--config", type=Path, help="run the null for the tasks/models of a run_experiment config")
    ap.add_argument("--check", action="store_true")
    args = ap.parse_args()

    if args.config and not args.check:
        cfg = json.loads(args.config.read_text(encoding="utf-8"))
        models = [m for m in cfg["models"] if m["type"] != "majority"]
        reps = args.sets.split(",")
        rows = []
        for task in cfg["tasks"]:
            rows += cell_task(args.root, args.protocol, task, reps, models, args.perms)
            for r in rows[-len(reps) * len(models):]:
                print(f"  {r['task']:16s} {r['rep']:6s} {r['model']:22s} observed {r['observed']:.3f} | null mean "
                      f"{r['null_mean']:.3f} p95 {r['null_p95']:.3f} | p = {r['p']:.3f}", flush=True)
        out = args.root / "results" / f"permutation_null_{cfg['name']}_{args.protocol}.csv"
        with out.open("w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=list(rows[0]))
            w.writeheader()
            for r in rows:
                w.writerow({k: (f"{v:.4f}" if isinstance(v, float) else v) for k, v in r.items()})
        print(f"wrote {out.relative_to(args.root).as_posix()}")
        return 0

    if args.check:
        fails = check()
        t = {"name": "CTK_C_vs_E13_A", "exercise": "CTK", "label_col": "label_A_ctk13", "classes": ["C", "E13"]}
        tr = cell_task(args.root, args.protocol, t, ["Rerr"], [{"type": "rf"}, {"type": "logreg", "C": 0.1}], n_perm=8)
        if len(tr) != 2 or not all(np.isfinite(r["observed"]) for r in tr):
            fails.append("task-based null (binary CTK, rf + logreg) failed")
        else:
            print("end-to-end task null: " + ", ".join(f"{r['model']} {r['observed']:.3f}" for r in tr))
        rows = cell(args.root, args.protocol, "A", "ELK", ["camera"], n_perm=8)
        if not (rows and np.isfinite(rows[0]["observed"]) and 0 < rows[0]["p"] <= 1):
            fails.append("end-to-end cell on real data failed")
        else:
            print(f"end-to-end: A ELK camera observed {rows[0]['observed']:.3f}, null p95 {rows[0]['null_p95']:.3f} (8 perms)")
        for x in fails:
            print("CHECK FAILED:", x)
        print("CHECK", "PASSED" if not fails else f"FAILED ({len(fails)})")
        return 1 if fails else 0

    sets = args.sets.split(",")
    rows = []
    for ann in ("A", "B"):
        for ex in ("RTK", "ELK", "CTK"):
            rows += cell(args.root, args.protocol, ann, ex, sets, args.perms)
            for r in rows[-len(sets):]:
                print(f"  {ann} {ex} {r['features']:7s} observed {r['observed']:.3f} | null mean {r['null_mean']:.3f} "
                      f"p95 {r['null_p95']:.3f} | p = {r['p']:.3f}", flush=True)
    out = args.root / "results" / f"permutation_null_{args.protocol}.csv"
    with out.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        for r in rows:
            w.writerow({k: (f"{v:.4f}" if isinstance(v, float) else v) for k, v in r.items()})
    print(f"wrote {out.relative_to(args.root).as_posix()}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
