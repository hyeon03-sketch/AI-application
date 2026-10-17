"""L4 (exploratory, backlog 24): do RF and logistic regression agree on which representation is better?

A representation comparison (e.g. "R1 beats R0") is only worth reporting if it does not flip with the model.
For every protocol x task and every pair of representations (a, b) we take the seed-mean Macro-F1 difference
a - b under RF and under logistic regression (C = 0.1) and label the pair
  agree      both differences have the same sign and both |diff| >= TIE
  tie        both |diff| < TIE
  one-sided  one model shows a difference, the other is within TIE
  flip       opposite signs, both |diff| >= TIE
Inputs are existing outputs only (no model is refit):
  results/experiments/main_binary/summary.csv       P4 (inside 1A + 2A), ELK C vs E2 and CTK C vs E13, A and B
  results/experiments/p1_confirmatory/summary.csv   P1 (Group 3 -> 1A + 2A), CTK C vs E13, A and B
  explore/loop/l1_acted_to_real_auc.csv             P1 AUC per rep and model (threshold-free view)
Per task the Spearman correlation of the representation ranking under the two models is also given.
Outputs: explore/loop/l4_model_agreement.{csv,md}
Usage: python explore/loop/l4_model_agreement.py [--check]
"""
from __future__ import annotations

import argparse
import csv
import itertools
import sys
from pathlib import Path

import numpy as np
from scipy.stats import spearmanr

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
TIE = 0.02
LR = "logreg(C=0.1)"


def label(d_rf: float, d_lr: float, tie: float = TIE) -> str:
    big_rf, big_lr = abs(d_rf) >= tie, abs(d_lr) >= tie
    if not big_rf and not big_lr:
        return "tie"
    if big_rf != big_lr:
        return "one-sided"
    return "agree" if np.sign(d_rf) == np.sign(d_lr) else "flip"


def load_summary(path: Path, metric: str = "macro_f1_mean"):
    out = {}
    with path.open(encoding="utf-8") as f:
        for r in csv.DictReader(f):
            if r["model"] in ("rf", LR):
                out.setdefault((r["protocol"], r["task"]), {}).setdefault(r["rep"], {})[r["model"]] = float(r[metric])
    return out


def load_l1_auc(path: Path):
    out = {}
    with path.open(encoding="utf-8") as f:
        for r in csv.DictReader(f):
            out.setdefault(("P1 (AUC)", f"CTK_C_vs_E13_{r['annotator']}"), {}).setdefault(r["rep"], {})[r["model"]] = \
                float(r["auc_pooled"])
    return out


def compare(table):
    pairs, ranks = [], []
    for (proto, task), reps in table.items():
        names = sorted(r for r in reps if "rf" in reps[r] and LR in reps[r])
        for a, b in itertools.combinations(names, 2):
            d_rf = reps[a]["rf"] - reps[b]["rf"]
            d_lr = reps[a][LR] - reps[b][LR]
            pairs.append({"protocol": proto, "task": task, "a": a, "b": b, "diff_rf": d_rf, "diff_logreg": d_lr,
                          "verdict": label(d_rf, d_lr)})
        if len(names) >= 3:
            rho = spearmanr([reps[r]["rf"] for r in names], [reps[r][LR] for r in names]).statistic
            ranks.append({"protocol": proto, "task": task, "n_reps": len(names), "spearman_rf_vs_logreg": float(rho),
                          "best_rf": max(names, key=lambda r: reps[r]["rf"]),
                          "best_logreg": max(names, key=lambda r: reps[r][LR])})
    return pairs, ranks


def write(pairs, ranks, out: Path):
    fmt = lambda v: f"{v:+.3f}" if isinstance(v, float) else v  # noqa: E731
    with out.with_suffix(".csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(pairs[0]))
        w.writeheader()
        for r in pairs:
            w.writerow({k: fmt(v) for k, v in r.items()})
    lines = ["# L4 · RF와 logreg가 표현 비교에서 같은 결론을 내는가 (탐색) / model agreement (exploratory)", "",
             f"Macro-F1(P1 AUC는 L1) 차이 a − b의 부호를 두 모델에서 비교. |차이| < {TIE}는 무승부. "
             "새로 학습한 모델은 없다(기존 결과 표만 사용).", "",
             "## 판정 개수 / verdict counts", "", "| protocol | agree | tie | one-sided | flip | 합 |", "|---|---|---|---|---|---|"]
    for proto in sorted({p["protocol"] for p in pairs}):
        sub = [p["verdict"] for p in pairs if p["protocol"] == proto]
        lines.append(f"| {proto} | " + " | ".join(str(sub.count(v)) for v in ("agree", "tie", "one-sided", "flip"))
                     + f" | {len(sub)} |")
    lines += ["", "## 표현 순위의 일치 / ranking agreement", "",
              "| protocol | task | reps | Spearman ρ | best RF | best logreg |", "|---|---|---|---|---|---|"]
    lines += [f"| {r['protocol']} | {r['task']} | {r['n_reps']} | {r['spearman_rf_vs_logreg']:+.2f} | {r['best_rf']} | "
              f"{r['best_logreg']} |" for r in ranks]
    key = {("R1", "R0"), ("R0", "R1"), ("R1", "Rerr"), ("Rerr", "R1"), ("R0", "Rerr"), ("Rerr", "R0"),
           ("R0", "R4"), ("R4", "R0")}
    lines += ["", "## 주요 쌍 / key pairs (R0, R1, R4, Rerr)", "",
              "| protocol | task | a | b | a−b RF | a−b logreg | verdict |", "|---|---|---|---|---|---|---|"]
    lines += [f"| {p['protocol']} | {p['task']} | {p['a']} | {p['b']} | {p['diff_rf']:+.3f} | {p['diff_logreg']:+.3f} | "
              f"{p['verdict']} |" for p in pairs if (p["a"], p["b"]) in key]
    out.with_suffix(".md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true")
    a = ap.parse_args()
    if a.check:
        ok = (label(0.05, 0.03) == "agree" and label(0.05, -0.03) == "flip" and label(0.01, -0.01) == "tie"
              and label(0.05, 0.01) == "one-sided")
        print("CHECK", "PASSED" if ok else "FAILED")
        return 0 if ok else 1
    table = load_summary(ROOT / "results" / "experiments" / "main_binary" / "summary.csv")
    table.update(load_summary(ROOT / "results" / "experiments" / "p1_confirmatory" / "summary.csv"))
    table.update(load_l1_auc(HERE / "l1_acted_to_real_auc.csv"))
    pairs, ranks = compare(table)
    out = HERE / "l4_model_agreement"
    write(pairs, ranks, out)
    print(out.with_suffix(".md").read_text(encoding="utf-8"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
