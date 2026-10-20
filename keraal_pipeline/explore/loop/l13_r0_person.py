"""L13 (exploratory): why does raw R0 win the binary real -> real (P4) tasks? Between-person vs within-person signal.

L12 found R0 RF above the annotator ceiling for RTK C vs E1+E2 (0.77) and high for ELK B (0.71). Backlog 17
(src/person_confound.py) showed static features (camera position, body size, length) explain the multiclass ELK
lead but not RTK. Here, for the binary tasks, R0's summary features are split into two parts:
  R0_within   R0 minus each participant's mean over his/her recordings (only within-person differences remain)
  R0_between  each recording replaced by its participant's mean (only between-person differences remain)
next to R0, R1, Rerr and the static sets camera / static_all. If R0_between scores like R0 and R0_within falls,
R0 wins by recognising people; if R0_within keeps the score, the signal is movement inside a person.
The participant mean uses no labels, but it does use the test participant's own recordings (transductive).
Also: pooled AUC vs mean within-participant AUC of the R0 / R0_within RF probabilities (positive = error).

P4 folds (leave-one-participant-out inside Group 1A). RF (300 trees, 5 seeds) and logreg C = 0.1; null = 100
participant permutations (permutation_null.loo_score, RF 100 trees 1 seed; p against the same setting).
Not R2 (Roshini, P1 raw advantage): this is P4 only. Aggregates only. Outputs: explore/loop/l13_r0_person.{csv,md}
Usage: python explore/loop/l13_r0_person.py [--perms 100] [--check]
"""
from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path

import numpy as np
from joblib import Parallel, delayed
from sklearn.metrics import roc_auc_score

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT / "src"))
from evaluate import macro_f1  # noqa: E402
from permutation_null import feature_matrix, loo_score, permute_by_participant  # noqa: E402
from rf_baseline import folds_of  # noqa: E402
from run_experiment import make_model, model_name  # noqa: E402

TASKS = {"RTK": {"C": "C", "E1": "E12", "E2": "E12"}, "ELK": {"C": "C", "E2": "E2"}}
SETS = ["R0", "R0_within", "R0_between", "R1", "Rerr", "camera", "static_all"]
MODELS = [{"type": "rf"}, {"type": "logreg", "C": 0.1}]
SEEDS = [0, 1, 2, 3, 4]


def split_person(X: np.ndarray, g: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Return (within, between): X minus the participant mean, and the participant mean itself."""
    mean = np.zeros_like(X)
    for p in np.unique(g):
        mean[g == p] = X[g == p].mean(0)
    return X - mean, mean


def lopo_proba(X, y, fold_ids, pos_label) -> np.ndarray:
    """RF probability of the error class, averaged over seeds."""
    out = np.zeros(len(y))
    for seed in SEEDS:
        for te in fold_ids:
            tr = np.setdiff1d(np.arange(len(y)), te)
            m = make_model({"type": "rf"}, seed).fit(X[tr], y[tr])
            out[te] += m.predict_proba(X[te])[:, list(m.classes_).index(pos_label)] / len(SEEDS)
    return out


def within_auc(y01, s, g) -> tuple[float, int]:
    vals = [roc_auc_score(y01[g == p], s[g == p]) for p in np.unique(g) if len(set(y01[g == p])) == 2]
    return (float(np.mean(vals)) if vals else float("nan")), len(vals)


def observed(X, y, fold_ids, model) -> float:
    out = []
    for seed in SEEDS if model["type"] == "rf" else SEEDS[:1]:
        pred = np.empty_like(y)
        for te in fold_ids:
            tr = np.setdiff1d(np.arange(len(y)), te)
            pred[te] = make_model(model, seed).fit(X[tr], y[tr]).predict(X[te])
        out.append(macro_f1(list(y), list(pred)))
    return float(np.mean(out))


def run(root: Path, n_perm: int):
    with (root / "data" / "labels.csv").open(encoding="utf-8") as f:
        lab = {r["rec_key"]: r for r in csv.DictReader(f)}
    folds = folds_of(json.loads((root / "data" / "splits.json").read_text(encoding="utf-8")), "P4")
    rows, aucs = [], []
    for ex, cmap in TASKS.items():
        err = [v for v in set(cmap.values()) if v != "C"][0]
        for ann in ("A", "B"):
            col = "label_" + ann
            keys = sorted({k for _, _, te in folds for k in te if lab[k]["exercise"] == ex and lab[k][col] in cmap})
            y = np.array([cmap[lab[k][col]] for k in keys])
            g = np.array([lab[k]["participant_key"] for k in keys])
            pos = {k: i for i, k in enumerate(keys)}
            fold_ids = [f for f in (np.array([pos[k] for k in te if k in pos]) for _, _, te in folds) if len(f)]
            rng = np.random.default_rng(0)
            perms = [permute_by_participant(y, g, rng) for _ in range(n_perm)]
            per_person = {p: f"{int((y[g == p] != 'C').sum())}/{int((g == p).sum())}" for p in np.unique(g)}
            base = {"task": f"{ex}_C_vs_{err}", "annotator": ann, "n": len(y), "participants": len(set(g)),
                    "n_error": int((y != "C").sum())}
            maj = np.empty_like(y)
            for te in fold_ids:
                tr = np.setdiff1d(np.arange(len(y)), te)
                v, c = np.unique(y[tr], return_counts=True)
                maj[te] = v[c.argmax()]
            rows.append({**base, "set": "-", "model": "majority", "macro_f1": macro_f1(list(y), list(maj)),
                         "null_p95": float("nan"), "p": float("nan")})
            R0 = feature_matrix(root, "R0", keys)
            r0w, r0b = split_person(R0, g)
            mats = {"R0": R0, "R0_within": r0w, "R0_between": r0b}
            for name in SETS:
                X = mats[name] if name in mats else feature_matrix(root, name, keys)
                for m in MODELS:
                    obs = observed(X, y, fold_ids, m)
                    null_obs = loo_score(X, y, g, fold_ids, 0, m)
                    null = np.array(Parallel(n_jobs=-1)(delayed(loo_score)(X, yp, g, fold_ids, 0, m) for yp in perms))
                    rows.append({**base, "set": name, "model": model_name(m), "macro_f1": obs,
                                 "null_p95": float(np.percentile(null, 95)),
                                 "p": float((1 + np.sum(null >= null_obs)) / (1 + n_perm))})
            y01 = (y != "C").astype(int)
            for name in ("R0", "R0_within"):
                s = lopo_proba(mats[name], y, fold_ids, err)
                wa, nw = within_auc(y01, s, g)
                aucs.append({**base, "set": name, "pooled_auc": float(roc_auc_score(y01, s)),
                             "within_auc_mean": wa, "within_participants": nw,
                             "errors_per_participant": json.dumps(per_person)})
    return rows, aucs


def write(rows, aucs, out: Path):
    for suffix, rs in (("", rows), ("_auc", aucs)):
        with out.with_name(out.name + suffix + ".csv").open("w", newline="", encoding="utf-8") as fh:
            w = csv.DictWriter(fh, fieldnames=list(rs[0]))
            w.writeheader(); w.writerows(rs)
    f = lambda x: "—" if x != x else f"{x:.2f}"  # noqa: E731
    L = ["# L13 · R0가 이기는 이유: 사람 사이 차이 vs 사람 안 차이 (탐색) / why R0 wins: between- vs within-person (exploratory)", "",
         "P4(1A 6명, 참가자 하나씩 빼기) 이진 과제. R0_within = R0 − 참가자 평균(사람 안 차이만), R0_between = 참가자 평균만"
         "(사람 사이 차이만). 참가자 평균은 라벨을 쓰지 않지만 테스트 참가자 자신의 녹화를 쓴다(전이적). "
         "RF 300 trees·5 seed 평균, logreg C=0.1. null p95 = 참가자 순열 100회(RF 100 trees·1 seed), p는 같은 설정 기준.", ""]
    for task in sorted({r["task"] for r in rows}):
        for ann in ("A", "B"):
            rs = [r for r in rows if r["task"] == task and r["annotator"] == ann]
            maj = next(r for r in rs if r["model"] == "majority")
            L += [f"## {task} · 주석자 {ann} (n {maj['n']}, 오류 {maj['n_error']}, 사람 {maj['participants']}, "
                  f"다수 클래스 {f(maj['macro_f1'])})", "",
                  "| 표현 | RF | null p95 | p | logreg | null p95 | p |", "|---|---|---|---|---|---|---|"]
            for s in SETS:
                rf = next(r for r in rs if r["set"] == s and r["model"] == "rf")
                lg = next(r for r in rs if r["set"] == s and r["model"] != "rf" and r["model"] != "majority")
                L.append(f"| {s} | **{f(rf['macro_f1'])}** | {f(rf['null_p95'])} | {f(rf['p'])} | "
                         f"**{f(lg['macro_f1'])}** | {f(lg['null_p95'])} | {f(lg['p'])} |")
            L.append("")
    L += ["## AUC: 전체 vs 사람 안 (RF 확률, 양성 = 오류)", "",
          "| 과제 | 주석자 | 표현 | 전체 AUC | 사람 안 AUC 평균 | 두 클래스 다 있는 사람 | 사람별 오류/녹화 |",
          "|---|---|---|---|---|---|---|"]
    for a in aucs:
        L.append(f"| {a['task']} | {a['annotator']} | {a['set']} | {f(a['pooled_auc'])} | {f(a['within_auc_mean'])} | "
                 f"{a['within_participants']} | {', '.join(f'{k}: {v}' for k, v in json.loads(a['errors_per_participant']).items())} |")
    L += ["", "*탐색 결과. 확증 설정·결과는 바꾸지 않았다. 집계값만 저장.* / *Exploratory; aggregates only.*", ""]
    out.with_suffix(".md").write_text("\n".join(L), encoding="utf-8")


def check() -> list[str]:
    errs = []
    X = np.array([[1.0, 2.0], [3.0, 4.0], [10.0, 0.0], [12.0, 2.0]])
    g = np.array(["a", "a", "b", "b"])
    w, b = split_person(X, g)
    if not np.allclose(w + b, X):
        errs.append("within + between should equal X")
    if not np.allclose(w[g == "a"].mean(0), 0) or not np.allclose(b[0], [2.0, 3.0]):
        errs.append("participant mean wrong")
    wa, n = within_auc(np.array([0, 1, 0, 1]), np.array([0.1, 0.9, 0.8, 0.2]), g)
    if n != 2 or abs(wa - 0.5) > 1e-9:
        errs.append("within_auc should average 1.0 and 0.0")
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
    rows, aucs = run(ROOT, args.perms)
    write(rows, aucs, HERE / "l13_r0_person")
    sys.stdout.reconfigure(encoding="utf-8")
    print((HERE / "l13_r0_person.md").read_text(encoding="utf-8"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
