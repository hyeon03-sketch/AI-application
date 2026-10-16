"""Config-driven experiment runner → results/experiments/<name>/

One JSON config describes a grid: protocols x tasks x representations x models x seeds.
(JSON rather than YAML to avoid an extra dependency.)

Config keys
  name        output folder name
  protocols   e.g. ["P1", "P4"]; a protocol whose recordings have no skeleton yet is reported ON HOLD and skipped
  tasks       list of {"name", "exercise", "label_col", "classes"}:
                label_col  any column of data/labels.csv (label_A, label_B, label_consensus, label_A_ctk13, ...)
                classes    optional list; recordings with other labels are dropped (e.g. ["C", "E13"] for a
                           binary CTK task). EXCL is always dropped.
  reps        representation names from data/features_T100.npz (R0 ... Rerr_d)
  models      list of {"type": "rf" | "logreg" | "majority", optional params}
  seeds       list of ints (majority uses only the first)

Outputs: config.json (copy), runs.csv (one row per protocol x task x rep x model x seed),
summary.csv (mean / sd over seeds + participant bootstrap CI of the first seed), preds.csv (out-of-fold).

Usage:  python src/run_experiment.py --config configs/main_binary.json
        python src/run_experiment.py --check      (runs configs/p4_smoke.json and cross-checks rf_baseline)
"""
from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path

import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

sys.path.insert(0, str(Path(__file__).resolve().parent))
from evaluate import evaluate, majority_baseline  # noqa: E402
from rf_baseline import N_TREES, folds_of, summarize  # noqa: E402


def make_model(spec: dict, seed: int):
    t = spec["type"]
    if t == "rf":
        return RandomForestClassifier(n_estimators=spec.get("n_estimators", N_TREES), class_weight="balanced",
                                      min_samples_leaf=spec.get("min_samples_leaf", 2), random_state=seed, n_jobs=-1)
    if t == "logreg":
        return make_pipeline(StandardScaler(), LogisticRegression(C=spec.get("C", 0.1), class_weight="balanced",
                                                                  max_iter=5000, random_state=seed))
    raise ValueError(f"unknown model type {t}")


def model_name(spec: dict) -> str:
    extra = ",".join(f"{k}={v}" for k, v in sorted(spec.items()) if k != "type")
    return spec["type"] + (f"({extra})" if extra else "")


def run(root: Path, cfg: dict) -> tuple[list[dict], list[list], list[str]]:
    feats = np.load(root / "data" / "features_T100.npz")
    pos = {k: i for i, k in enumerate(feats["keys"])}
    with (root / "data" / "labels.csv").open(encoding="utf-8") as f:
        lab = {r["rec_key"]: r for r in csv.DictReader(f)}
    sp = json.loads((root / "data" / "splits.json").read_text(encoding="utf-8"))
    Z = {r: summarize(feats[r].astype(np.float64)) for r in cfg["reps"]}
    # Optional, pre-registered secondary analysis: drop the summary features that the Group 3 trial-confound
    # check flagged (per exercise and representation, results/trial_confound_features.csv).
    keep_cols = {}
    if cfg.get("drop_trial_cue_features"):
        from trial_confound import summary_names
        flagged = {}
        with (root / "results" / "trial_confound_features.csv").open(encoding="utf-8") as fh:
            for r in csv.DictReader(fh):
                flagged.setdefault((r["exercise"], r["rep"]), set()).add(r["feature"])
        for rep in cfg["reps"]:
            names = summary_names(root, rep)
            for ex in {t["exercise"] for t in cfg["tasks"]}:
                keep_cols[(ex, rep)] = np.array([n not in flagged.get((ex, rep), set()) for n in names])
    runs, preds, held = [], [], []
    for protocol in cfg["protocols"]:
        folds = folds_of(sp, protocol)
        missing = {k for _, tr, te in folds for k in tr + te if k not in pos}
        if missing:
            held.append(f"{protocol}: ON HOLD ({len(missing)} recordings without skeletons)")
            continue
        for task in cfg["tasks"]:
            col, ex, keep = task["label_col"], task["exercise"], task.get("classes")
            ok = lambda k: (lab[k]["exercise"] == ex and lab[k][col] != "EXCL"  # noqa: E731
                            and (keep is None or lab[k][col] in keep))
            for model in cfg["models"]:
                for rep in (cfg["reps"] if model["type"] != "majority" else ["-"]):
                    for seed in (cfg["seeds"] if model["type"] != "majority" else cfg["seeds"][:1]):
                        yt, yp, gs, ks = [], [], [], []
                        for fold, tr, te in folds:
                            tr, te = [k for k in tr if ok(k)], [k for k in te if ok(k)]
                            if not tr or not te:
                                continue
                            ytr = [lab[k][col] for k in tr]
                            if model["type"] == "majority":
                                p = majority_baseline(ytr, te)
                            elif len(set(ytr)) < 2:
                                p = ytr[:1] * len(te)  # a fold whose training side holds one class only
                            else:
                                cols = keep_cols.get((ex, rep), slice(None))
                                clf = make_model(model, seed).fit(Z[rep][[pos[k] for k in tr]][:, cols], ytr)
                                p = list(clf.predict(Z[rep][[pos[k] for k in te]][:, cols]))
                            yt += [lab[k][col] for k in te]; yp += p; ks += te
                            gs += [lab[k]["participant_key"] for k in te]
                        first = seed == cfg["seeds"][0]
                        res = evaluate(yt, yp, gs if first else None, n_boot=1000)
                        runs.append({"protocol": protocol, "task": task["name"], "rep": rep, "model": model_name(model),
                                     "seed": seed, "n": res["n"], "participants": len(set(gs)),
                                     "support": json.dumps(res["support"]), "accuracy": res["accuracy"],
                                     "macro_f1": res["macro_f1"], "balanced_accuracy": res["balanced_accuracy"],
                                     "ci": res.get("macro_f1_ci")})
                        preds += [[protocol, task["name"], rep, model_name(model), seed, k, t, q]
                                  for k, t, q in zip(ks, yt, yp)]
    return runs, preds, held


def summarize_runs(runs: list[dict]) -> list[dict]:
    out, seen = [], {}
    for r in runs:
        seen.setdefault((r["protocol"], r["task"], r["rep"], r["model"]), []).append(r)
    for (protocol, task, rep, model), rs in seen.items():
        f1 = np.array([r["macro_f1"] for r in rs]); ba = np.array([r["balanced_accuracy"] for r in rs])
        ci = next(r["ci"] for r in rs if r["ci"] is not None)
        out.append({"protocol": protocol, "task": task, "rep": rep, "model": model, "n": rs[0]["n"],
                    "participants": rs[0]["participants"], "support": rs[0]["support"], "n_seeds": len(rs),
                    "macro_f1_mean": float(f1.mean()), "macro_f1_sd": float(f1.std()),
                    "macro_f1_ci_lo": ci[0], "macro_f1_ci_hi": ci[1], "bal_acc_mean": float(ba.mean())})
    return out


def write(outdir: Path, cfg: dict, runs, preds, summary) -> None:
    outdir.mkdir(parents=True, exist_ok=True)
    (outdir / "config.json").write_text(json.dumps(cfg, indent=1), encoding="utf-8")
    fmt = lambda v: f"{v:.4f}" if isinstance(v, float) else v  # noqa: E731
    with (outdir / "runs.csv").open("w", newline="", encoding="utf-8") as f:
        cols = [c for c in runs[0] if c != "ci"]
        w = csv.DictWriter(f, fieldnames=cols, extrasaction="ignore")
        w.writeheader()
        for r in runs:
            w.writerow({k: fmt(r[k]) for k in cols})
    with (outdir / "summary.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(summary[0]))
        w.writeheader()
        for s in summary:
            w.writerow({k: fmt(v) for k, v in s.items()})
    with (outdir / "preds.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["protocol", "task", "rep", "model", "seed", "rec_key", "y_true", "y_pred"])
        w.writerows(preds)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    ap.add_argument("--config", type=Path)
    ap.add_argument("--check", action="store_true")
    args = ap.parse_args()
    root = args.root
    cfg_path = args.config or root / "configs" / "p4_smoke.json"
    cfg = json.loads(cfg_path.read_text(encoding="utf-8"))
    runs, preds, held = run(root, cfg)
    for h in held:
        print(h)

    if args.check:
        fails = []
        # the runner must reproduce rf_baseline exactly for the same settings
        with (root / "results" / "rf_P4_runs.csv").open(encoding="utf-8") as f:
            ref = {(r["annotator"], r["exercise"], r["rep"], int(r["seed"])): float(r["macro_f1"])
                   for r in csv.DictReader(f)}
        for r in runs:
            if r["model"] == "rf" and r["task"].startswith("ref_"):
                _, ann, ex = r["task"].split("_")
                want = ref[(ann, ex, r["rep"], r["seed"])]
                if abs(r["macro_f1"] - round(want, 4)) > 6e-5:
                    fails.append(f"{r['task']} {r['rep']} seed {r['seed']}: {r['macro_f1']:.4f} vs rf_baseline {want:.4f}")
        # The smoke config must never touch P1: once Group 3 is present that would compute sim-to-real test
        # results before the pre-registered confirmatory run (PREREGISTRATION.md).
        if "P1" in cfg["protocols"] or any(r["protocol"] == "P1" for r in runs):
            fails.append("smoke config must not run P1 (pre-registration: confirmatory run comes first)")
        binary = [r for r in runs if r["task"] == "CTK_C_vs_E13_A"]
        if not binary or any(set(json.loads(r["support"])) != {"C", "E13"} for r in binary):
            fails.append("class filter did not produce a C vs E13 task")
        for x in fails:
            print("CHECK FAILED:", x)
        print(f"smoke config: {len(runs)} runs; reproduces rf_baseline on matching settings")
        print("CHECK", "PASSED" if not fails else f"FAILED ({len(fails)})")
        return 1 if fails else 0

    if not runs:
        print("nothing to run: every protocol in this config is on hold; no outputs written")
        return 0
    summary = summarize_runs(runs)
    outdir = root / "results" / "experiments" / cfg["name"]
    write(outdir, cfg, runs, preds, summary)
    print(f"wrote {outdir.relative_to(root).as_posix()}/ (runs {len(runs)}, summary {len(summary)})")
    for s in summary:
        print(f"  {s['protocol']} {s['task']:18s} {s['rep']:7s} {s['model']:10s} Macro-F1 {s['macro_f1_mean']:.3f} "
              f"± {s['macro_f1_sd']:.3f} [{s['macro_f1_ci_lo']:.3f}, {s['macro_f1_ci_hi']:.3f}] n={s['n']} {s['support']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
