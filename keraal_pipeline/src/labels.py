"""Derive classification labels from data/master_index.csv → data/labels.csv.

Classes per exercise: C (correct), E1, E2, E3. Anything else is excluded, with the reason kept:
  Incomplete / Motionless evaluations, "Other" errors, and Incorrect without an error type.

Columns written (one row per recording):
  label_A, label_B          per-annotator label, or EXCL
  excl_reason_A, excl_reason_B
  label_consensus           label when A and B agree (and neither is excluded), else EXCL
  label_{A,B,consensus}_ctk13   same, but CTK E1 and E3 merged into "E13"
                                (both papers describe them identically: "Arms are not raised enough")
  severity_A, severity_B    SmallError / LargeError for error labels

Group 3 has a single label source (the file name), copied into all three label columns.

Usage:  python src/labels.py [--root .] [--check]
"""
from __future__ import annotations

import argparse
import csv
import sys
from collections import Counter
from pathlib import Path

CLASSES = ("C", "E1", "E2", "E3")
EXCL = "EXCL"

# Test-set counts (1A+2A) from KERAAL_Pipeline_KR.pdf section 1: (C, E1, E2, E3, excluded).
EXPECTED = {
    ("A", "RTK"): (73, 4, 6, 0, 18),
    ("B", "RTK"): (58, 5, 27, 0, 11),
    ("A", "ELK"): (36, 0, 43, 0, 13),
    ("B", "ELK"): (17, 0, 60, 0, 15),
    ("A", "CTK"): (61, 26, 1, 17, 3),
    ("B", "CTK"): (63, 32, 4, 6, 3),
}
G3_PER_CLASS = 45

FIELDS = ["rec_key", "group", "exercise", "participant_key",
          "label_A", "excl_reason_A", "severity_A", "label_B", "excl_reason_B", "severity_B",
          "label_consensus", "label_A_ctk13", "label_B_ctk13", "label_consensus_ctk13"]


def annotator_label(evaluation: str, error: str) -> tuple[str, str]:
    if evaluation == "Correct":
        return "C", ""
    if evaluation == "Incorrect":
        if error in ("Error1", "Error2", "Error3"):
            return "E" + error[-1], ""
        return EXCL, "other_error" if error == "Other" else "incorrect_without_type"
    if evaluation in ("Incomplete", "Motionless"):
        return EXCL, evaluation.lower()
    return EXCL, f"evaluation={evaluation or 'missing'}"


def merge13(label: str, exercise: str) -> str:
    return "E13" if exercise == "CTK" and label in ("E1", "E3") else label


def build(rows: list[dict]) -> list[dict]:
    out = []
    for r in rows:
        o = {k: r[k] for k in ("rec_key", "group", "exercise", "participant_key")}
        if r["group"] == "3":
            lab = "C" if r["g3_error"] == "C" else r["g3_error"]
            for a in ("A", "B"):
                o[f"label_{a}"], o[f"excl_reason_{a}"], o[f"severity_{a}"] = lab, "", ""
        else:
            for a in ("A", "B"):
                lab, why = annotator_label(r[f"evaluation_{a}"], r[f"error_{a}"])
                o[f"label_{a}"], o[f"excl_reason_{a}"] = lab, why
                o[f"severity_{a}"] = r[f"severity_{a}"] if lab.startswith("E") else ""
        a, b = o["label_A"], o["label_B"]
        o["label_consensus"] = a if (a == b and a != EXCL) else EXCL
        for k in ("A", "B", "consensus"):
            o[f"label_{k}_ctk13"] = merge13(o[f"label_{k}"], r["exercise"])
        out.append(o)
    return out


def table(labels: list[dict], col: str, groups=("1A", "2A")) -> dict:
    c = Counter((r["exercise"], r[col]) for r in labels if r["group"] in groups)
    return {ex: tuple(c[(ex, k)] for k in CLASSES) + (c[(ex, EXCL)],) for ex in ("RTK", "ELK", "CTK")}


def check(labels: list[dict]) -> list[str]:
    fails = []
    for a in ("A", "B"):
        got = table(labels, f"label_{a}")
        for ex in ("RTK", "ELK", "CTK"):
            if got[ex] != EXPECTED[(a, ex)]:
                fails.append(f"annotator {a} {ex}: expected {EXPECTED[(a, ex)]}, got {got[ex]}")
    g3 = Counter((r["exercise"], r["label_A"]) for r in labels if r["group"] == "3")
    if g3:
        bad = {k: v for k, v in g3.items() if v != G3_PER_CLASS}
        if bad or len(g3) != 12:
            fails.append(f"group 3 not 45 per exercise x class: {dict(g3)}")
    for r in labels:
        if r["label_consensus"] != EXCL and not (r["label_A"] == r["label_B"] == r["label_consensus"]):
            fails.append(f"{r['rec_key']}: consensus inconsistent")
    return fails


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    ap.add_argument("--check", action="store_true")
    args = ap.parse_args()

    with (args.root / "data" / "master_index.csv").open(encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    labels = build(rows)
    out = args.root / "data" / "labels.csv"
    with out.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        w.writeheader()
        w.writerows(labels)
    print(f"wrote {out} ({len(labels)} rows)")

    print("test set (1A+2A) counts as (C, E1, E2, E3, excluded):")
    for col in ("label_A", "label_B", "label_consensus", "label_A_ctk13"):
        print(f"  {col}: {table(labels, col)}")
    c = Counter(r["label_A_ctk13"] for r in labels if r["group"] in ("1A", "2A") and r["exercise"] == "CTK")
    print(f"  CTK with E1+E3 merged (annotator A): {dict(c)}")
    reasons = Counter((r["excl_reason_A"], r["excl_reason_B"]) for r in labels
                      if r["group"] in ("1A", "2A") and (r["excl_reason_A"] or r["excl_reason_B"]))
    print("exclusion reasons (A, B):", dict(reasons))

    if args.check:
        fails = check(labels)
        for x in fails:
            print("CHECK FAILED:", x)
        print("CHECK", "PASSED" if not fails else f"FAILED ({len(fails)})")
        return 1 if fails else 0
    return 0


if __name__ == "__main__":
    sys.exit(main())
