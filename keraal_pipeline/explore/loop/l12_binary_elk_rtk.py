"""L12 (exploratory): binary real -> real (P4) scores for ELK and RTK, to fill the model column of the L10 ceiling table.

L10 compared models with the annotator A-B ceiling, but binary P4 model scores existed only for CTK (C vs E1+E3).
  ELK C vs E2       already run by configs/main_binary.json; read from results/experiments/main_binary/summary.csv
                    and results/permutation_null_main_binary_P4.csv (no retraining).
  RTK C vs E1+E2    not run before (labels.csv has no merged RTK column). Run here in memory: P4 folds
                    (leave-one-participant-out inside Group 1A), reps R0 R1 R2 Rerr Rerr_d, RF (5 seeds) and
                    logreg C = 0.1, plus the training-fold majority class; participant permutation null
                    (permutation_null.loo_score, RF with 100 trees as in that module, 100 permutations).
Both annotators. Aggregates only. Outputs: explore/loop/l12_binary_elk_rtk.{csv,md}
Usage: python explore/loop/l12_binary_elk_rtk.py [--perms 100] [--check]
"""
from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path

import numpy as np
from joblib import Parallel, delayed

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT / "src"))
from evaluate import macro_f1  # noqa: E402
from permutation_null import feature_matrix, loo_score, permute_by_participant  # noqa: E402
from rf_baseline import folds_of  # noqa: E402
from run_experiment import make_model, model_name  # noqa: E402

REPS = ["R0", "R1", "R2", "Rerr", "Rerr_d"]
MODELS = [{"type": "rf"}, {"type": "logreg", "C": 0.1}]
SEEDS = [0, 1, 2, 3, 4]
RTK_MAP = {"C": "C", "E1": "E12", "E2": "E12"}


def majority_loo(y, fold_ids) -> float:
    pred = np.empty_like(y)
    for te in fold_ids:
        tr = np.setdiff1d(np.arange(len(y)), te)
        vals, cnt = np.unique(y[tr], return_counts=True)
        pred[te] = vals[cnt.argmax()]
    return macro_f1(list(y), list(pred))


def observed(X, y, fold_ids, model) -> float:
    """Macro-F1 averaged over seeds, the full model of run_experiment (logreg: one seed)."""
    out = []
    for seed in SEEDS if model["type"] == "rf" else SEEDS[:1]:
        pred = np.empty_like(y)
        for te in fold_ids:
            tr = np.setdiff1d(np.arange(len(y)), te)
            pred[te] = make_model(model, seed).fit(X[tr], y[tr]).predict(X[te])
        out.append(macro_f1(list(y), list(pred)))
    return float(np.mean(out))


def rtk_rows(root: Path, n_perm: int):
    with (root / "data" / "labels.csv").open(encoding="utf-8") as f:
        lab = {r["rec_key"]: r for r in csv.DictReader(f)}
    folds = folds_of(json.loads((root / "data" / "splits.json").read_text(encoding="utf-8")), "P4")
    rows = []
    for ann in ("A", "B"):
        col = "label_" + ann
        keys = sorted({k for _, _, te in folds for k in te if lab[k]["exercise"] == "RTK" and lab[k][col] in RTK_MAP})
        y = np.array([RTK_MAP[lab[k][col]] for k in keys])
        g = np.array([lab[k]["participant_key"] for k in keys])
        pos = {k: i for i, k in enumerate(keys)}
        fold_ids = [f for f in (np.array([pos[k] for k in te if k in pos]) for _, _, te in folds) if len(f)]
        rng = np.random.default_rng(0)
        perms = [permute_by_participant(y, g, rng) for _ in range(n_perm)]
        base = {"task": f"RTK_C_vs_E12_{ann}", "exercise": "RTK", "annotator": ann, "n": len(y),
                "participants": len(set(g)), "n_error": int((y != "C").sum()), "source": "L12 (new run)"}
        rows.append({**base, "rep": "-", "model": "majority", "macro_f1": majority_loo(y, fold_ids),
                     "null_p95": float("nan"), "p": float("nan")})
        for rep in REPS:
            X = feature_matrix(root, rep, keys)
            for m in MODELS:
                obs = observed(X, y, fold_ids, m)
                null_obs = loo_score(X, y, g, fold_ids, 0, m)
                null = np.array(Parallel(n_jobs=-1)(delayed(loo_score)(X, yp, g, fold_ids, 0, m) for yp in perms))
                rows.append({**base, "rep": rep, "model": model_name(m), "macro_f1": obs,
                             "null_p95": float(np.percentile(null, 95)),
                             "p": float((1 + np.sum(null >= null_obs)) / (1 + n_perm))})
    return rows


def elk_rows(root: Path):
    null = {}
    with (root / "results" / "permutation_null_main_binary_P4.csv").open(encoding="utf-8") as f:
        for r in csv.DictReader(f):
            null[(r["task"], r["rep"], r["model"].replace("[100 trees]", ""))] = (float(r["null_p95"]), float(r["p"]))
    rows = []
    with (root / "results" / "experiments" / "main_binary" / "summary.csv").open(encoding="utf-8") as f:
        for r in csv.DictReader(f):
            if r["protocol"] != "P4" or not r["task"].startswith("ELK"):
                continue
            if r["model"] != "majority" and r["rep"] not in REPS:
                continue
            sup = json.loads(r["support"])
            npv, p = null.get((r["task"], r["rep"], r["model"]), (float("nan"), float("nan")))
            rows.append({"task": r["task"], "exercise": "ELK", "annotator": r["task"][-1], "n": int(r["n"]),
                         "participants": int(r["participants"]), "n_error": sup.get("E2", 0),
                         "source": "main_binary (existing)", "rep": r["rep"], "model": r["model"],
                         "macro_f1": float(r["macro_f1_mean"]), "null_p95": npv, "p": p})
    return rows


def write(rows, out: Path):
    with out.with_suffix(".csv").open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0]))
        w.writeheader(); w.writerows(rows)
    f = lambda x: "—" if x != x else f"{x:.2f}"  # noqa: E731
    L = ["# L12 · ELK·RTK 이진 과제의 실제 → 실제(P4) 점수 (탐색) / binary P4 scores for ELK and RTK (exploratory)", "",
         "L10 상한 표의 빈칸을 채운다. ELK C vs E2는 기존 main_binary 결과를 읽었고, RTK C vs E1+E2는 새로 돌렸다"
         " (P4 = 1A 안 참가자 하나씩 빼기). null p95 = 참가자 순열 100회(RF는 100 trees, 1 seed로 다시 맞춤). p는 같은 설정의 관측값 기준.",
         "", "| 과제 | 주석자 | 표현 | 모델 | Macro-F1 | null p95 | p | 다수 클래스 | n (오류) | 사람 수 |",
         "|---|---|---|---|---|---|---|---|---|---|"]
    for task in sorted({r["task"] for r in rows}):
        rs = [r for r in rows if r["task"] == task]
        maj = next(r for r in rs if r["model"] == "majority")
        for r in rs:
            if r["model"] == "majority":
                continue
            L.append(f"| {task[:-2]} | {r['annotator']} | {r['rep']} | {r['model']} | **{f(r['macro_f1'])}** | "
                     f"{f(r['null_p95'])} | {f(r['p'])} | {f(maj['macro_f1'])} | {r['n']} ({r['n_error']}) | {r['participants']} |")
    L += ["", "*탐색 결과. 확증 설정·결과는 바꾸지 않았다. 집계값만 저장.* / *Exploratory; aggregates only.*", ""]
    out.with_suffix(".md").write_text("\n".join(L), encoding="utf-8")


def check() -> list[str]:
    errs = []
    y = np.array(["C"] * 6 + ["E"] * 2)
    folds = [np.array([0, 6]), np.array([1, 7]), np.array([2, 3, 4, 5])]
    if abs(majority_loo(y, folds) - macro_f1(list(y), ["C"] * 8)) > 1e-9:
        errs.append("majority_loo should predict C everywhere")
    if set(RTK_MAP.values()) != {"C", "E12"}:
        errs.append("RTK merge map wrong")
    return errs


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--perms", type=int, default=100)
    ap.add_argument("--check", action="store_true")
    args = ap.parse_args()
    if args.check:
        e = check()
        print("CHECK FAILED: " + "; ".join(e) if e else "CHECK PASSED")
        return 1 if e else 0
    rows = elk_rows(ROOT) + rtk_rows(ROOT, args.perms)
    write(rows, HERE / "l12_binary_elk_rtk")
    sys.stdout.reconfigure(encoding="utf-8")
    print((HERE / "l12_binary_elk_rtk.md").read_text(encoding="utf-8"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
