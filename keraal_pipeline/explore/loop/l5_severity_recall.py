"""L5 (exploratory, backlog 6): are small errors missed more often than large ones?

Annotators A and B grade every error recording SmallError or LargeError (1A / 2A only; Group 3 has no grade).
Using the saved out-of-fold predictions (no model is refit):
  results/experiments/main_binary/preds.csv     P4 (inside 1A + 2A): ELK C vs E2, CTK C vs E13
  results/experiments/p1_confirmatory/preds.csv P1 (Group 3 -> 1A + 2A): CTK C vs E13
For each protocol x task x rep x model, a recording counts as detected if the majority of its seeds predicted the
error class. Recall is reported separately for Small and Large error recordings (severity from the same annotator
as the label), with counts, participants, and Fisher's exact test (two-sided) of Small vs Large recall.
Chance reference: a classifier that flags errors at its overall flag rate has the same expected recall for both
grades, so "no difference" is the null here.
Outputs: explore/loop/l5_severity_recall.{csv,md}
Usage: python explore/loop/l5_severity_recall.py [--check]
"""
from __future__ import annotations

import argparse
import csv
import sys
from collections import defaultdict
from pathlib import Path

from scipy.stats import fisher_exact

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
SOURCES = [("main_binary", "P4"), ("p1_confirmatory", "P1")]


def majority_detect(rows, err):
    """rows: [(seed, y_pred)] for one recording -> True if most seeds predict the error class."""
    hits = sum(p == err for _, p in rows)
    return hits * 2 > len(rows)


def run(root: Path):
    with (root / "data" / "labels.csv").open(encoding="utf-8") as f:
        lab = {r["rec_key"]: r for r in csv.DictReader(f)}
    out = []
    for exp, proto in SOURCES:
        preds = defaultdict(list)
        with (root / "results" / "experiments" / exp / "preds.csv").open(encoding="utf-8") as f:
            for r in csv.DictReader(f):
                if r["protocol"] != proto or r["model"] == "majority" or r["y_true"] == "C":
                    continue
                preds[(r["task"], r["rep"], r["model"], r["rec_key"], r["y_true"])].append((r["seed"], r["y_pred"]))
        cells = defaultdict(lambda: {"SmallError": [], "LargeError": []})
        for (task, rep, model, key, y), rows in preds.items():
            ann = task.rsplit("_", 1)[1]
            sev = lab[key][f"severity_{ann}"]
            if sev in ("SmallError", "LargeError"):
                cells[(task, rep, model)][sev].append((majority_detect(rows, y), lab[key]["participant_key"]))
        for (task, rep, model), d in sorted(cells.items()):
            s, l = d["SmallError"], d["LargeError"]
            if not s or not l:
                continue
            hs, hl = sum(h for h, _ in s), sum(h for h, _ in l)
            _, p = fisher_exact([[hs, len(s) - hs], [hl, len(l) - hl]])
            out.append({"protocol": proto, "task": task, "rep": rep, "model": model,
                        "n_small": len(s), "participants_small": len({g for _, g in s}),
                        "recall_small": hs / len(s),
                        "n_large": len(l), "participants_large": len({g for _, g in l}),
                        "recall_large": hl / len(l), "diff_large_minus_small": hl / len(l) - hs / len(s),
                        "fisher_p": p})
    return out


def write(rows, out: Path):
    fmt = lambda v: f"{v:.3f}" if isinstance(v, float) else v  # noqa: E731
    with out.with_suffix(".csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        for r in rows:
            w.writerow({k: fmt(v) for k, v in r.items()})
    cols = list(rows[0])
    big = [r for r in rows if r["fisher_p"] < 0.05]
    pos = sum(r["diff_large_minus_small"] > 0 for r in rows)
    lines = ["# L5 · 심각도별 recall: 작은 오류를 더 놓치는가 (탐색) / recall by severity (exploratory)", "",
             "오류 녹화만 대상. 녹화는 seed 다수결로 '탐지'. 심각도는 라벨과 같은 주석자 것. "
             "Fisher 정확 검정(양측), 다중 비교 보정 없음.", "",
             f"요약: {len(rows)}개 조합 중 Large recall > Small recall {pos}개, p < 0.05 {len(big)}개.", "",
             "| " + " | ".join(cols) + " |", "|" + "---|" * len(cols)]
    lines += ["| " + " | ".join(str(fmt(r[c])) for c in cols) + " |" for r in rows]
    out.with_suffix(".md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true")
    a = ap.parse_args()
    if a.check:
        ok = (majority_detect([(0, "E2"), (1, "E2"), (2, "C")], "E2")
              and not majority_detect([(0, "E2"), (1, "C")], "E2"))
        print("CHECK", "PASSED" if ok else "FAILED")
        return 0 if ok else 1
    rows = run(ROOT)
    out = HERE / "l5_severity_recall"
    write(rows, out)
    print(out.with_suffix(".md").read_text(encoding="utf-8"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
