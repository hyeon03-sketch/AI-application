"""L6 (exploratory, backlog 20): how does recording length relate to errors?

Round 10 found recording length alone reaching Macro-F1 0.339 on CTK (A), above R0. Every representation is
resampled to T = 100, so the models never see length directly; if errors really are longer or shorter, that is
motion information the representations throw away. Here, per main task (ELK C vs E2, CTK C vs E13; annotators
A and B):
  1. length (frames, n_frames in data/master_index.csv) by group (1A, 2A, G3) and class: median, IQR;
  2. within-participant AUC of length for "error" (mean over participants with both classes) and its sign;
  3. a length-only logistic regression (log frames) under P4 (leave-one-participant-out inside 1A + 2A) and P1
     (train Group 3 -> test 1A + 2A): Macro-F1, AUC, within-participant label-shuffle null (1,000) for AUC,
     majority-baseline Macro-F1.
Aggregates only. Outputs: explore/loop/l6_length.{csv,md}
Usage: python explore/loop/l6_length.py [--perms 1000] [--check]
"""
from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path

import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import f1_score, roc_auc_score

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(HERE))
from l1_acted_to_real_auc import shuffle_within, within_auc  # noqa: E402
from rf_baseline import folds_of  # noqa: E402

TASKS = [("ELK", "label_A", "A", ("C", "E2")), ("ELK", "label_B", "B", ("C", "E2")),
         ("CTK", "label_A_ctk13", "A", ("C", "E13")), ("CTK", "label_B_ctk13", "B", ("C", "E13"))]


def length_model_scores(folds, ok, lab, col, err, length):
    s, y, g = [], [], []
    for _, tr, te in folds:
        tr, te = [k for k in tr if ok(k)], [k for k in te if ok(k)]
        if not te:
            continue
        ytr = np.array([lab[k][col] == err for k in tr], int)
        if len(set(ytr)) < 2:
            p = np.full(len(te), float(ytr[0]))
        else:
            X = np.log([[length[k]] for k in tr])
            clf = LogisticRegression(class_weight="balanced").fit(X, ytr)
            p = clf.predict_proba(np.log([[length[k]] for k in te]))[:, 1]
        s += list(p); y += [lab[k][col] == err for k in te]; g += [lab[k]["participant_key"] for k in te]
    return np.array(s), np.array(y, int), np.array(g)


def run(root: Path, perms: int):
    with (root / "data" / "labels.csv").open(encoding="utf-8") as f:
        lab = {r["rec_key"]: r for r in csv.DictReader(f)}
    with (root / "data" / "master_index.csv").open(encoding="utf-8") as f:
        length = {r["rec_key"]: int(r["n_frames"]) for r in csv.DictReader(f) if r["n_frames"]}
    sp = json.loads((root / "data" / "splits.json").read_text(encoding="utf-8"))
    rng = np.random.default_rng(0)
    dist, models = [], []
    for ex, col, ann, classes in TASKS:
        err = classes[1]
        ok = lambda k: k in length and lab[k]["exercise"] == ex and lab[k][col] in classes  # noqa: E731
        for grp in ("1A", "2A", "3"):
            for c in classes:
                v = np.array([length[k] for k in lab if ok(k) and lab[k]["group"] == grp and lab[k][col] == c])
                if len(v):
                    dist.append({"exercise": ex, "annotator": ann, "group": grp if grp != "3" else "G3", "class": c,
                                 "n": len(v), "median_frames": float(np.median(v)),
                                 "q25": float(np.percentile(v, 25)), "q75": float(np.percentile(v, 75))})
        real = [k for k in lab if ok(k) and lab[k]["group"] in ("1A", "2A")]
        y = np.array([lab[k][col] == err for k in real], int)
        g = np.array([lab[k]["participant_key"] for k in real])
        L = np.array([length[k] for k in real], float)
        wa, n_w = within_auc(y, L, g)
        for proto in ("P4", "P1"):
            s, yy, gg = length_model_scores(folds_of(sp, proto), ok, lab, col, err, length)
            auc = roc_auc_score(yy, s)
            null = np.array([roc_auc_score(shuffle_within(yy, gg, rng), s) for _ in range(perms)])
            maj = f1_score(yy, np.full_like(yy, np.bincount(yy).argmax()), average="macro")
            models.append({"exercise": ex, "annotator": ann, "protocol": proto, "n": len(yy),
                           "participants": len(set(gg)), "length_only_f1": f1_score(yy, (s >= 0.5).astype(int),
                                                                                     average="macro"),
                           "majority_f1": maj, "length_only_auc": auc, "auc_null_p95": float(np.percentile(null, 95)),
                           "auc_p": float((1 + (null >= auc).sum()) / (perms + 1)),
                           "within_participant_auc_real": wa, "n_within": n_w})
    return dist, models


def write(dist, models, out: Path):
    fmt = lambda v: f"{v:.3f}" if isinstance(v, float) else v  # noqa: E731
    with out.with_suffix(".csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(models[0]))
        w.writeheader()
        for r in models:
            w.writerow({k: fmt(v) for k, v in r.items()})
    lines = ["# L6 · 녹화 길이와 오류 (탐색) / recording length vs error (exploratory)", "",
             "프레임 수 기준(15 fps 주석 시간축). 모든 표현은 T = 100으로 리샘플링되어 모델은 길이를 직접 보지 않는다.", "",
             "## 길이 분포 / length distribution (frames)", "",
             "| exercise | annotator | group | class | n | median | q25 | q75 |", "|---|---|---|---|---|---|---|---|"]
    lines += [f"| {d['exercise']} | {d['annotator']} | {d['group']} | {d['class']} | {d['n']} | {d['median_frames']:.0f} | "
              f"{d['q25']:.0f} | {d['q75']:.0f} |" for d in dist]
    cols = list(models[0])
    lines += ["", "## 길이만 쓴 모델 / length-only model", "",
              "`within_participant_auc_real`: 1A·2A 참가자 안에서 길이가 길수록 오류인 정도(0.5 = 무관, < 0.5 = 오류가 더 짧음).", "",
              "| " + " | ".join(cols) + " |", "|" + "---|" * len(cols)]
    lines += ["| " + " | ".join(str(fmt(r[c])) for c in cols) + " |" for r in models]
    out.with_suffix(".md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--perms", type=int, default=1000)
    ap.add_argument("--check", action="store_true")
    a = ap.parse_args()
    if a.check:
        lab = {f"k{i}": {"participant_key": f"p{i % 2}", "x": "E" if i % 2 else "C"} for i in range(8)}
        length = {f"k{i}": 100 + 50 * (i % 2) for i in range(8)}
        folds = [("f", [f"k{i}" for i in range(6)], ["k6", "k7"])]
        s, y, _ = length_model_scores(folds, lambda k: True, lab, "x", "E", length)
        ok = s[1] > s[0] and list(y) == [0, 1]
        print("CHECK", "PASSED" if ok else "FAILED")
        return 0 if ok else 1
    dist, models = run(ROOT, a.perms)
    out = HERE / "l6_length"
    write(dist, models, out)
    print(out.with_suffix(".md").read_text(encoding="utf-8"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
