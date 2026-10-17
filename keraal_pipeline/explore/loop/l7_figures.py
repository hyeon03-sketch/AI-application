"""L7 (exploratory, backlog 26): presentation figures for the confirmatory task (CTK C vs E13).

  l7_confusion_P1.png  P1 (Group 3 -> 1A + 2A) confusion matrices, Rerr (the pre-registered H1 representation),
                       RF and logistic regression x annotators A and B. One vote per recording: the majority over
                       the 5 seeds (logistic regression is deterministic). Rows = true class, columns = predicted.
  l7_ladder.png        Macro-F1 per representation (R0, R1, Rerr), real -> real (P4, leave-one-participant-out
                       inside 1A + 2A) next to acted -> real (P1), per model and annotator, with each protocol's
                       majority baseline and, for P1, the pre-registered permutation-null 95th percentile of Rerr.
  l7_figures.md        every number shown in the two figures (table twin).
Inputs only (no model is refit): results/experiments/{main_binary,p1_confirmatory}/{preds,summary}.csv and
results/confirmatory_p1_confirmatory_P1.csv. Confirmatory files are read, never written.
Usage: python explore/loop/l7_figures.py [--check]
"""
from __future__ import annotations

import argparse
import csv
import sys
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
LR = "logreg(C=0.1)"
REPS = ["R0", "R1", "Rerr"]
CLASSES = ["C", "E13"]


def vote(preds: list[str]) -> str:
    c = Counter(preds).most_common()
    return c[0][0] if len(c) == 1 or c[0][1] > c[1][1] else "E13"  # ties (none with 5 seeds) count as error


def confusion(root: Path, rep: str = "Rerr"):
    per = defaultdict(list)
    with (root / "results" / "experiments" / "p1_confirmatory" / "preds.csv").open(encoding="utf-8") as f:
        for r in csv.DictReader(f):
            if r["rep"] == rep and r["model"] in ("rf", LR):
                per[(r["task"][-1], r["model"], r["rec_key"], r["y_true"])].append(r["y_pred"])
    cm = defaultdict(lambda: np.zeros((2, 2), int))
    for (ann, model, _, y), ps in per.items():
        cm[(ann, model)][CLASSES.index(y), CLASSES.index(vote(ps))] += 1
    return dict(cm)


def ladder(root: Path):
    f1 = {}
    for exp in ("main_binary", "p1_confirmatory"):
        with (root / "results" / "experiments" / exp / "summary.csv").open(encoding="utf-8") as f:
            for r in csv.DictReader(f):
                if r["task"].startswith("CTK_C_vs_E13"):
                    f1[(r["protocol"], r["task"][-1], r["model"], r["rep"])] = float(r["macro_f1_mean"])
    null = {}
    with (root / "results" / "confirmatory_p1_confirmatory_P1.csv").open(encoding="utf-8") as f:
        for r in csv.DictReader(f):
            if r["hypothesis"] == "H1":
                null[(r["task"][-1], r["model"])] = float(r["null_p95"])
    return f1, null


def plot(cm, f1, null, out_dir: Path):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fig, axes = plt.subplots(2, 2, figsize=(7, 6.2))
    for ax, (ann, model) in zip(axes.ravel(), [("A", "rf"), ("A", LR), ("B", "rf"), ("B", LR)]):
        m = cm[(ann, model)]
        ax.imshow(m / m.sum(1, keepdims=True), cmap="Blues", vmin=0, vmax=1)
        for i in range(2):
            for j in range(2):
                share = m[i, j] / m[i].sum()
                ax.text(j, i, f"{m[i, j]}\n({share:.0%})", ha="center", va="center", fontsize=10,
                        color="white" if share > 0.6 else "black")
        ax.set_xticks([0, 1], ["pred C", "pred E13"]); ax.set_yticks([0, 1], ["true C", "true E13"])
        pred_err = m[:, 1].sum() / m.sum()
        ax.set_title(f"annotator {ann} · {model.split('(')[0]} · Rerr\nflagged as error: {pred_err:.0%} "
                     f"(true {m[1].sum() / m.sum():.0%})", fontsize=9)
    fig.suptitle("Acted → real (P1): Group 3 models on 1A + 2A, CTK C vs E13 (exploratory figure)", fontsize=10)
    fig.tight_layout()
    fig.savefig(out_dir / "l7_confusion_P1.png", dpi=150)

    fig, axes = plt.subplots(1, 4, figsize=(13, 3.6), sharey=True)
    x = np.arange(len(REPS))
    for ax, (ann, model) in zip(axes, [("A", "rf"), ("A", LR), ("B", "rf"), ("B", LR)]):
        for proto, style, lbl in (("P4", "-o", "real → real (P4)"), ("P1", "-s", "acted → real (P1)")):
            ax.plot(x, [f1[(proto, ann, model, r)] for r in REPS], style, label=lbl)
        for proto, c in (("P4", "C0"), ("P1", "C1")):
            ax.axhline(f1[(proto, ann, "majority", "-")], color=c, ls=":", lw=1)
        ax.axhline(null[(ann, model)], color="C1", ls="--", lw=1, label="P1 null 95% (Rerr)")
        ax.set_xticks(x, REPS); ax.set_ylim(0.2, 0.85)
        ax.set_title(f"annotator {ann} · {model.split('(')[0]}", fontsize=9)
    axes[0].set_ylabel("Macro-F1"); axes[0].legend(fontsize=7, loc="lower left")
    fig.suptitle("Macro-F1 by representation: real → real vs acted → real (dotted = majority baseline; exploratory "
                 "figure, confirmatory numbers unchanged)", fontsize=9)
    fig.tight_layout()
    fig.savefig(out_dir / "l7_ladder.png", dpi=150)


def write_md(cm, f1, null, out: Path):
    lines = ["# L7 · 발표용 그림의 표 쌍 / table twin of the L7 figures (탐색 그림, 확증 수치는 그대로)", "",
             "## P1 confusion matrix (Rerr, 녹화별 seed 다수결) / rows = true, columns = predicted", "",
             "| annotator | model | true C → C | true C → E13 | true E13 → C | true E13 → E13 | 오류 판정 비율 |",
             "|---|---|---|---|---|---|---|"]
    for (ann, model), m in sorted(cm.items()):
        lines.append(f"| {ann} | {model} | {m[0, 0]} | {m[0, 1]} | {m[1, 0]} | {m[1, 1]} | {m[:, 1].sum() / m.sum():.2f} |")
    lines += ["", "## Macro-F1 사다리 / ladder (seed 평균)", "",
              "| annotator | model | protocol | R0 | R1 | Rerr | majority | P1 null 95% (Rerr) |",
              "|---|---|---|---|---|---|---|---|"]
    for ann in ("A", "B"):
        for model in ("rf", LR):
            for proto in ("P4", "P1"):
                nv = f"{null[(ann, model)]:.3f}" if proto == "P1" else "–"
                lines.append(f"| {ann} | {model} | {proto} | " + " | ".join(f"{f1[(proto, ann, model, r)]:.3f}" for r in REPS)
                             + f" | {f1[(proto, ann, 'majority', '-')]:.3f} | {nv} |")
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true")
    a = ap.parse_args()
    cm = confusion(ROOT)
    f1, null = ladder(ROOT)
    if a.check:
        fails = []
        if vote(["C", "C", "E13"]) != "C" or vote(["E13", "C"]) != "E13":
            fails.append("vote")
        # the RF Rerr confusion matrix must give back roughly the confirmatory error-flag rate (92-97 %)
        m = cm[("A", "rf")]
        if not 0.85 <= m[:, 1].sum() / m.sum() <= 0.99:
            fails.append(f"RF Rerr flag rate {m[:, 1].sum() / m.sum():.2f}")
        if abs(f1[("P1", "A", "rf", "Rerr")] - 0.4066) > 1e-3:
            fails.append("P1 Rerr RF F1 differs from the confirmatory 0.4066")
        print("CHECK", "PASSED" if not fails else f"FAILED {fails}")
        return 1 if fails else 0
    plot(cm, f1, null, HERE)
    write_md(cm, f1, null, HERE / "l7_figures.md")
    print((HERE / "l7_figures.md").read_text(encoding="utf-8"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
