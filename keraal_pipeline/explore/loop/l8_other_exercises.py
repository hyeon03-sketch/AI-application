"""L8 (exploratory): is the acted -> real threshold shift specific to CTK? L1 repeated on ELK and RTK.

Tasks (same error definitions as Roshini's Kinect model, members/roshini/Kinect_model/config.py):
  ELK  C vs E2          (G3 train: C 45, E2 45)
  RTK  C vs E1 + E2     (G3 train: C 45, E1 + E2 90; real data has few errors, so the two are merged)
P1 split (train Group 3 -> test 1A + 2A), reps R0 / R1 / Rerr, RF (5-seed averaged probability) and logistic
regression (C = 0.1), annotators A and B. Same columns as L1 (explore/loop/l1_acted_to_real_auc.py):
AUC pooled / within-participant, within-participant shuffle null (1,000), share predicted error at 0.5, true error
rate, Macro-F1 at 0.5, Macro-F1 at the test-chosen best threshold (ORACLE upper bound), majority-baseline Macro-F1.
CTK rows from L1 are appended for comparison. Aggregates only.
Outputs: explore/loop/l8_other_exercises.{csv,md}
Usage: python explore/loop/l8_other_exercises.py [--perms 1000] [--check]
"""
from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path

import numpy as np
from sklearn.metrics import f1_score, roc_auc_score

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(HERE))
from l1_acted_to_real_auc import best_f1, shuffle_within, within_auc  # noqa: E402
from rf_baseline import folds_of, summarize  # noqa: E402
from run_experiment import make_model, model_name  # noqa: E402

TASKS = [("ELK", "C vs E2", {"C": 0, "E2": 1}), ("RTK", "C vs E1+E2", {"C": 0, "E1": 1, "E2": 1})]
REPS = ["R0", "R1", "Rerr"]
MODELS = [{"type": "rf"}, {"type": "logreg", "C": 0.1}]
SEEDS = [0, 1, 2, 3, 4]


def run(root: Path, perms: int):
    feats = np.load(root / "data" / "features_T100.npz")
    pos = {k: i for i, k in enumerate(feats["keys"])}
    with (root / "data" / "labels.csv").open(encoding="utf-8") as f:
        lab = {r["rec_key"]: r for r in csv.DictReader(f)}
    sp = json.loads((root / "data" / "splits.json").read_text(encoding="utf-8"))
    folds = folds_of(sp, "P1")
    train, test = folds[0][1], [k for _, _, te in folds for k in te]
    Z = {r: summarize(feats[r].astype(np.float64)) for r in REPS}
    rng = np.random.default_rng(0)
    rows = []
    for ex, task, cmap in TASKS:
        for ann in ("A", "B"):
            col = f"label_{ann}"
            ok = lambda k: lab[k]["exercise"] == ex and lab[k][col] in cmap  # noqa: E731
            tr, te = [k for k in train if ok(k)], [k for k in test if ok(k)]
            ytr = [cmap[lab[k][col]] for k in tr]
            y = np.array([cmap[lab[k][col]] for k in te])
            g = np.array([lab[k]["participant_key"] for k in te])
            maj = f1_score(y, np.full_like(y, np.bincount(y).argmax()), average="macro")
            for model in MODELS:
                for rep in REPS:
                    ss = []
                    for seed in SEEDS:
                        clf = make_model(model, seed).fit(Z[rep][[pos[k] for k in tr]], ytr)
                        ss.append(clf.predict_proba(Z[rep][[pos[k] for k in te]])[:, list(clf.classes_).index(1)])
                        if model["type"] == "logreg":
                            break
                    s = np.mean(ss, axis=0)
                    auc = roc_auc_score(y, s)
                    null = np.array([roc_auc_score(shuffle_within(y, g, rng), s) for _ in range(perms)])
                    wa, nw = within_auc(y, s, g)
                    rows.append({"exercise": ex, "task": task, "annotator": ann, "model": model_name(model), "rep": rep,
                                 "n": len(te), "n_error": int(y.sum()), "participants": len(set(g)), "n_within": nw,
                                 "auc_pooled": auc, "null_p95": float(np.percentile(null, 95)),
                                 "p": float((1 + (null >= auc).sum()) / (perms + 1)), "auc_within_mean": wa,
                                 "pred_err_rate": float((s >= 0.5).mean()), "true_err_rate": float(y.mean()),
                                 "f1_at_0.5": f1_score(y, (s >= 0.5).astype(int), average="macro"),
                                 "majority_f1": maj, "f1_best_oracle": best_f1(y, s)})
    return rows


def add_ctk(rows):
    with (HERE / "l1_acted_to_real_auc.csv").open(encoding="utf-8") as f:
        for r in csv.DictReader(f):
            rows.append({"exercise": "CTK", "task": "C vs E1+E3 (L1)", "annotator": r["annotator"], "model": r["model"],
                         "rep": r["rep"], "n": int(r["n"]), "n_error": round(float(r["true_err_rate"]) * int(r["n"])),
                         "participants": int(r["participants"]), "n_within": int(r["n_within"]),
                         **{k: float(r[k]) for k in ("auc_pooled", "null_p95", "p", "auc_within_mean", "pred_err_rate",
                                                     "true_err_rate", "f1_at_0.5", "f1_best_oracle")},
                         "majority_f1": float("nan")})
    return rows


def write(rows, out: Path):
    fmt = lambda v: ("–" if v != v else f"{v:.3f}") if isinstance(v, float) else v  # noqa: E731
    with out.with_suffix(".csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        for r in rows:
            w.writerow({k: fmt(v) for k, v in r.items()})
    cols = ["exercise", "annotator", "model", "rep", "n", "n_error", "participants", "auc_pooled", "null_p95", "p",
            "auc_within_mean", "pred_err_rate", "true_err_rate", "f1_at_0.5", "majority_f1", "f1_best_oracle"]
    lines = ["# L8 · 연기 → 실제 AUC를 ELK·RTK로 확장 (탐색) / L1 on ELK and RTK (exploratory)", "",
             "P1 (G3 학습 → 1A·2A 시험). ELK = C vs E2, RTK = C vs E1+E2. AUC 기준선 0.5, null = 참가자 안 라벨 섞기. "
             "`f1_best_oracle`은 시험셋에서 고른 기준점의 상한일 뿐이다. CTK 행은 L1 결과(다수 클래스 F1은 L1에 없음).", "",
             "| " + " | ".join(cols) + " |", "|" + "---|" * len(cols)]
    lines += ["| " + " | ".join(str(fmt(r[c])) for c in cols) + " |" for r in rows]
    out.with_suffix(".md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--perms", type=int, default=1000)
    ap.add_argument("--check", action="store_true")
    a = ap.parse_args()
    if a.check:
        ok = all(set(m.values()) == {0, 1} for _, _, m in TASKS) and TASKS[1][2]["E1"] == TASKS[1][2]["E2"] == 1
        print("CHECK", "PASSED" if ok else "FAILED")
        return 0 if ok else 1
    rows = add_ctk(run(ROOT, a.perms))
    out = HERE / "l8_other_exercises"
    write(rows, out)
    print(out.with_suffix(".md").read_text(encoding="utf-8"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
