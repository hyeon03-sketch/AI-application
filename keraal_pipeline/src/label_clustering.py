"""How strongly are labels clustered within participants? → results/label_clustering.{csv,md}

For each test group (1A, 2A, 1A+2A), exercise and annotator (A, B, consensus):
  - per-participant class counts
  - ICC(1) of the binary "error" indicator (any E vs C), one-way ANOVA estimator with unequal cluster sizes:
        ICC = (MSB - MSW) / (MSB + (k0 - 1) MSW),  k0 = (N - sum n_i^2 / N) / (g - 1)
  - design effect DEFF = 1 + (k0 - 1) ICC and effective sample size N / DEFF
  - purity: share of participants whose recordings are >= 90% one class (participants with >= 3 recordings)
EXCL labels are dropped. ICC is truncated at 0 for reporting (negative estimates mean no clustering).

Why it matters: when labels are a property of the person, a test set of N recordings carries the
information of roughly N / DEFF independent samples, and leave-one-participant-out scores mostly measure
whether the model can tell "people who make this error" apart (see PROGRESS.md, round 7).

Usage:  python src/label_clustering.py [--check]
"""
from __future__ import annotations

import argparse
import csv
import sys
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np

PURITY = 0.9


def icc1(y: np.ndarray, groups: np.ndarray) -> tuple[float, float]:
    """ICC(1) and k0 for a numeric outcome y clustered by groups."""
    ids = np.unique(groups)
    g, N = len(ids), len(y)
    if g < 2 or N <= g:
        return float("nan"), float("nan")
    n = np.array([np.sum(groups == i) for i in ids])
    means = np.array([y[groups == i].mean() for i in ids])
    grand = y.mean()
    ssb = np.sum(n * (means - grand) ** 2)
    ssw = sum(np.sum((y[groups == i] - m) ** 2) for i, m in zip(ids, means))
    msb, msw = ssb / (g - 1), ssw / (N - g)
    k0 = (N - np.sum(n ** 2) / N) / (g - 1)
    denom = msb + (k0 - 1) * msw
    if denom == 0:
        return float("nan"), float(k0)  # no variation at all
    return float((msb - msw) / denom), float(k0)


def analyse(lab: list[dict]) -> list[dict]:
    rows = []
    for test, groups in (("1A", {"1A"}), ("2A", {"2A"}), ("1A+2A", {"1A", "2A"})):
        for ann in ("A", "B", "consensus"):
            col = f"label_{ann}"
            for ex in ("RTK", "ELK", "CTK"):
                rs = [r for r in lab if r["group"] in groups and r["exercise"] == ex and r[col] != "EXCL"]
                if not rs:
                    continue
                y = np.array([0.0 if r[col] == "C" else 1.0 for r in rs])
                gr = np.array([r["participant_key"] for r in rs])
                icc, k0 = icc1(y, gr)
                icc_r = max(icc, 0.0) if np.isfinite(icc) else float("nan")
                deff = 1 + (k0 - 1) * icc_r if np.isfinite(icc_r) else float("nan")
                per = defaultdict(Counter)
                for r in rs:
                    per[r["participant_key"]][r[col]] += 1
                big = [c for c in per.values() if sum(c.values()) >= 3]
                pure = sum(max(c.values()) / sum(c.values()) >= PURITY for c in big)
                rows.append({
                    "test": test, "annotator": ann, "exercise": ex, "n": len(rs), "participants": len(per),
                    "error_rate": float(y.mean()), "icc_error": icc, "k0": k0, "deff": deff,
                    "n_effective": len(rs) / deff if deff and np.isfinite(deff) else float("nan"),
                    "pure_participants": f"{pure}/{len(big)}",
                    "per_participant": "; ".join(f"{p.split('-', 1)[1]}: " + ",".join(f"{k}{v}" for k, v in sorted(c.items()))
                                                 for p, c in sorted(per.items())),
                })
    return rows


def write(root: Path, rows: list[dict]) -> None:
    out = root / "results" / "label_clustering.csv"
    with out.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        for r in rows:
            w.writerow({k: (f"{v:.4f}" if isinstance(v, float) else v) for k, v in r.items()})
    md = ["# Label clustering within participants (test groups)", "",
          "Binary outcome: any error vs correct. ICC(1), design effect and effective N; EXCL dropped.", "",
          "| test | annotator | exercise | N | participants | error rate | ICC | DEFF | effective N | ≥90% one class |",
          "|---|---|---|---|---|---|---|---|---|---|"]
    for r in rows:
        md.append(f"| {r['test']} | {r['annotator']} | {r['exercise']} | {r['n']} | {r['participants']} | "
                  f"{r['error_rate']:.2f} | {r['icc_error']:.2f} | {r['deff']:.1f} | {r['n_effective']:.1f} | "
                  f"{r['pure_participants']} |")
    md += ["", "## Per-participant counts (1A+2A)", ""]
    for r in rows:
        if r["test"] == "1A+2A":
            md.append(f"- **{r['annotator']} {r['exercise']}**: {r['per_participant']}")
    (root / "results" / "label_clustering.md").write_text("\n".join(md) + "\n", encoding="utf-8")


def check(lab: list[dict], rows: list[dict]) -> list[str]:
    fails = []
    rng = np.random.default_rng(0)
    g = np.repeat(np.arange(8), 15)
    icc_none = np.mean([icc1(rng.integers(0, 2, len(g)).astype(float), g)[0] for _ in range(200)])
    if abs(icc_none) > 0.03:
        fails.append(f"ICC of unclustered data should be ~0, got {icc_none:.3f}")
    perfect = (g % 2).astype(float)
    if abs(icc1(perfect, g)[0] - 1.0) > 1e-9:
        fails.append("ICC of perfectly clustered data should be 1")
    # classic textbook check: equal cluster sizes -> k0 equals the cluster size
    if abs(icc1(perfect + rng.normal(0, 0.1, len(g)), g)[1] - 15) > 1e-9:
        fails.append("k0 should equal the common cluster size")
    for r in rows:
        col = "label_" + r["annotator"]
        groups = {"1A": {"1A"}, "2A": {"2A"}, "1A+2A": {"1A", "2A"}}[r["test"]]
        n = sum(1 for x in lab if x["group"] in groups and x["exercise"] == r["exercise"] and x[col] != "EXCL")
        if n != r["n"]:
            fails.append(f"{r['test']} {r['annotator']} {r['exercise']}: n {r['n']} != {n}")
    return fails


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    ap.add_argument("--check", action="store_true")
    args = ap.parse_args()
    with (args.root / "data" / "labels.csv").open(encoding="utf-8") as f:
        lab = list(csv.DictReader(f))
    rows = analyse(lab)
    write(args.root, rows)
    print("wrote results/label_clustering.csv and results/label_clustering.md")
    for r in rows:
        if r["test"] in ("1A", "1A+2A") and r["annotator"] != "consensus":
            print(f"  {r['test']:6s} {r['annotator']} {r['exercise']}: N {r['n']:3d}, {r['participants']:2d} people, "
                  f"error rate {r['error_rate']:.2f}, ICC {r['icc_error']:+.2f}, DEFF {r['deff']:.1f}, "
                  f"effective N {r['n_effective']:.1f}, pure {r['pure_participants']}")
    if args.check:
        fails = check(lab, rows)
        for x in fails:
            print("CHECK FAILED:", x)
        print("CHECK", "PASSED" if not fails else f"FAILED ({len(fails)})")
        return 1 if fails else 0
    return 0


if __name__ == "__main__":
    sys.exit(main())
