"""Regenerate the paper figures and tables from results/*.csv → results/figures/, results/tables.md

Figures (PNG at 200 dpi + PDF), light print style:
  fig1_label_clustering   recordings vs effective sample size per test task (dumbbell)
  fig2_main_binary_<P>    Macro-F1 per representation, RF vs logistic regression, with the participant
                          permutation-null 95th percentile and the majority baseline (2 x 2 small multiples)
  fig3_person_confound    camera-position-only features vs raw coordinates vs majority, per task
Tables (Markdown): test-set class counts, label clustering, main binary results with null, person confound.

Palette: reference categorical slots 1-2 (blue #2a78d6, orange #eb6834), validated with the dataviz
validator (light surface #fcfcfb: all checks pass); reference lines and nulls in muted gray ink.
Every value shown in a figure is also in results/tables.md (table twin).

When P1 results exist (results/experiments/main_binary/summary.csv with protocol P1, and
results/permutation_null_main_binary_P1.csv), fig2 is also produced for P1.

Usage:  python src/figures.py [--check]
"""
from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
SURFACE, INK, INK2, MUTED, GRID, AXIS = "#fcfcfb", "#0b0b0b", "#52514e", "#898781", "#e1e0d9", "#c3c2b7"
S1, S2 = "#2a78d6", "#eb6834"
REPS = ["R0", "R1", "R2", "R3", "R4", "Rerr", "Rerr_d"]
REP_LABEL = {"R0": "raw", "R1": "normal-\nized", "R2": "angles", "R3": "+veloc-\nity", "R4": "+sym-\nmetry",
             "Rerr": "error-\nspecific", "Rerr_d": "error-spec.\nΔ start"}


def style():
    plt.rcParams.update({
        "font.family": ["Segoe UI", "DejaVu Sans"], "font.size": 9, "text.color": INK,
        "axes.facecolor": SURFACE, "figure.facecolor": SURFACE, "axes.edgecolor": AXIS, "axes.linewidth": 0.8,
        "axes.labelcolor": INK2, "xtick.color": MUTED, "ytick.color": MUTED, "axes.grid": True,
        "grid.color": GRID, "grid.linewidth": 0.6, "grid.linestyle": "-", "axes.spines.top": False,
        "axes.spines.right": False, "legend.frameon": False, "axes.titlesize": 10, "axes.titleweight": "bold",
        "axes.titlecolor": INK, "axes.axisbelow": True})


def read(name: str) -> list[dict]:
    with (ROOT / "results" / name).open(encoding="utf-8") as f:
        return list(csv.DictReader(f))


def save(fig, stem: str) -> list[Path]:
    out = ROOT / "results" / "figures"
    out.mkdir(parents=True, exist_ok=True)
    paths = [out / f"{stem}.png", out / f"{stem}.pdf"]
    fig.savefig(paths[0], dpi=200, bbox_inches="tight", metadata={"Software": None})
    fig.savefig(paths[1], bbox_inches="tight", metadata={"Creator": None, "Producer": None, "CreationDate": None})
    plt.close(fig)
    return paths


# ----------------------------------------------------------------------------- figure 1
def fig_clustering():
    rows = [r for r in read("label_clustering.csv") if r["test"] == "1A+2A" and r["annotator"] in ("A", "B")]
    rows.sort(key=lambda r: (r["exercise"], r["annotator"]), reverse=True)
    fig, ax = plt.subplots(figsize=(6.2, 3.0))
    y = np.arange(len(rows))
    n = np.array([float(r["n"]) for r in rows]); ne = np.array([float(r["n_effective"]) for r in rows])
    ax.hlines(y, ne, n, color=AXIS, linewidth=2, zorder=1)
    ax.scatter(n, y, s=36, color=MUTED, zorder=2, label="recordings (N)", edgecolor=SURFACE, linewidth=1.5)
    ax.scatter(ne, y, s=40, color=S1, zorder=3, label="effective N = N / design effect", edgecolor=SURFACE, linewidth=1.5)
    for yi, r, a, b in zip(y, rows, ne, n):
        ax.text(a - 2, yi, f"{a:.0f}", ha="right", va="center", color=INK2, fontsize=8)
        ax.text(b + 2, yi, f"{b:.0f}  ICC {float(r['icc_error']):.2f}", ha="left", va="center", color=INK2, fontsize=8)
    ax.set_yticks(y, [f"{r['exercise']}  annotator {r['annotator']}" for r in rows])
    ax.set_xlim(0, 135); ax.set_xlabel("recordings in the test set (Groups 1A + 2A)")
    ax.grid(axis="y", visible=False)
    ax.set_title("Labels cluster within participants: test sets hold far fewer independent samples", loc="left")
    ax.legend(loc="upper left", bbox_to_anchor=(0, -0.2), ncol=2, fontsize=8)
    return save(fig, "fig1_label_clustering")


# ----------------------------------------------------------------------------- figure 2
def fig_main_binary(protocol: str):
    summ = [r for r in read("experiments/main_binary/summary.csv") if r["protocol"] == protocol]
    if not summ:
        return []
    null_path = ROOT / "results" / f"permutation_null_main_binary_{protocol}.csv"
    nulls = {}
    if null_path.exists():
        for r in read(null_path.name):
            nulls[(r["task"], r["rep"], r["model"].split("[")[0])] = float(r["null_p95"])
    tasks = ["ELK_C_vs_E2_A", "ELK_C_vs_E2_B", "CTK_C_vs_E13_A", "CTK_C_vs_E13_B"]
    titles = {"ELK_C_vs_E2_A": "ELK  correct vs E2  (annotator A)", "ELK_C_vs_E2_B": "ELK  correct vs E2  (annotator B)",
              "CTK_C_vs_E13_A": "CTK  correct vs E1+E3  (annotator A)", "CTK_C_vs_E13_B": "CTK  correct vs E1+E3  (annotator B)"}
    fig, axes = plt.subplots(2, 2, figsize=(9.2, 6.0), sharey=True)
    x = np.arange(len(REPS))
    for ax, task in zip(axes.flat, tasks):
        rs = {(r["rep"], r["model"]): r for r in summ if r["task"] == task}
        maj = next(float(r["macro_f1_mean"]) for r in summ if r["task"] == task and r["model"] == "majority")
        ax.axhline(maj, color=MUTED, linewidth=1, zorder=1)
        ax.text(len(REPS) - 0.62, maj + 0.012, f"majority\n{maj:.2f}", ha="left", va="bottom", color=MUTED, fontsize=7.5)
        for model, color, dx, label in (("rf", S1, -0.14, "Random Forest"), ("logreg(C=0.1)", S2, 0.14, "logistic regression")):
            m = np.array([float(rs[(rep, model)]["macro_f1_mean"]) for rep in REPS])
            lo = np.array([float(rs[(rep, model)]["macro_f1_ci_lo"]) for rep in REPS])
            hi = np.array([float(rs[(rep, model)]["macro_f1_ci_hi"]) for rep in REPS])
            ax.vlines(x + dx, lo, hi, color=color, linewidth=1.2, alpha=0.55, zorder=2)
            ax.scatter(x + dx, m, s=34, color=color, edgecolor=SURFACE, linewidth=1.5, zorder=4, label=label)
            for i, rep in enumerate(REPS):
                p95 = nulls.get((task, rep, model))
                if p95 is not None:
                    ax.hlines(p95, x[i] + dx - 0.11, x[i] + dx + 0.11, color=INK, linewidth=1.4, zorder=3,
                              label="permutation null, 95th percentile" if (i == 0 and model == "rf") else None)
        ax.set_title(titles[task], loc="left", fontsize=9)
        ax.set_xticks(x, [REP_LABEL[r] for r in REPS], fontsize=7.5)
        ax.set_ylim(0, 1); ax.set_xlim(-0.5, len(REPS) + 0.15); ax.grid(axis="x", visible=False)
    for ax in axes[:, 0]:
        ax.set_ylabel("Macro-F1")
    handles, labels = axes[0, 0].get_legend_handles_labels()
    fig.legend(handles, labels, loc="upper center", ncol=3, bbox_to_anchor=(0.5, 1.0), fontsize=8)
    proto = {"P4": "leave-one-patient-out within Group 1A", "P1": "train Group 3 → test Groups 1A + 2A"}.get(protocol, protocol)
    fig.suptitle(f"Binary main tasks, {proto}: dot = mean of 5 seeds, whisker = participant bootstrap 95% CI (seed 0)",
                 x=0.01, y=1.05, ha="left", fontsize=10, fontweight="bold")
    fig.tight_layout()
    return save(fig, f"fig2_main_binary_{protocol}")


# ----------------------------------------------------------------------------- figure 3
def fig_person_confound():
    rows = read("person_confound_P4.csv")
    order = [(a, e) for e in ("CTK", "ELK", "RTK") for a in ("B", "A")]
    get = {(r["annotator"], r["exercise"], r["features"]): r for r in rows}
    fig, ax = plt.subplots(figsize=(6.2, 3.0))
    y = np.arange(len(order))
    cam = np.array([float(get[(a, e, "camera")]["macro_f1_mean"]) for a, e in order])
    r0 = np.array([float(get[(a, e, "camera")]["ref_R0"]) for a, e in order])
    maj = np.array([float(get[(a, e, "camera")]["ref_majority"]) for a, e in order])
    ax.scatter(maj, y, marker="|", s=120, color=MUTED, linewidth=1.5, zorder=2, label="majority baseline")
    ax.scatter(r0, y, s=40, color=S1, edgecolor=SURFACE, linewidth=1.5, zorder=3, label="raw coordinates (R0)")
    ax.scatter(cam, y, s=40, color=S2, edgecolor=SURFACE, linewidth=1.5, zorder=4,
               label="camera position only (4 numbers, no movement)")
    ax.set_yticks(y, [f"{e}  annotator {a}" for a, e in order])
    ax.set_xlim(0, 0.85); ax.set_xlabel("Macro-F1, leave-one-patient-out within Group 1A (5 seeds)")
    ax.grid(axis="y", visible=False)
    ax.set_title("Camera position alone (no movement information) matches the raw skeleton on ELK", loc="left")
    ax.legend(loc="upper left", bbox_to_anchor=(0, -0.2), ncol=2, fontsize=7.5)
    return save(fig, "fig3_person_confound")


# ----------------------------------------------------------------------------- tables
def tables() -> str:
    lab = read("../data/labels.csv")
    out = ["# Paper tables (generated by src/figures.py — do not edit by hand)", ""]
    out += ["## T1. Test-set class counts (Groups 1A + 2A)", "",
            "| exercise | annotator | C | E1 | E2 | E3 | excluded |", "|---|---|---|---|---|---|---|"]
    for ex in ("RTK", "ELK", "CTK"):
        for a in ("A", "B"):
            c = {}
            for r in lab:
                if r["group"] in ("1A", "2A") and r["exercise"] == ex:
                    c[r[f"label_{a}"]] = c.get(r[f"label_{a}"], 0) + 1
            out.append(f"| {ex} | {a} | " + " | ".join(str(c.get(k, 0)) for k in ("C", "E1", "E2", "E3", "EXCL")) + " |")
    out += ["", "## T2. Label clustering within participants (1A + 2A)", "",
            "| exercise | annotator | N | participants | ICC | design effect | effective N |", "|---|---|---|---|---|---|---|"]
    for r in read("label_clustering.csv"):
        if r["test"] == "1A+2A" and r["annotator"] in ("A", "B"):
            out.append(f"| {r['exercise']} | {r['annotator']} | {r['n']} | {r['participants']} | {float(r['icc_error']):.2f} | "
                       f"{float(r['deff']):.1f} | {float(r['n_effective']):.1f} |")
    nulls = {(r["task"], r["rep"], r["model"].split("[")[0]): r for r in read("permutation_null_main_binary_P4.csv")}
    out += ["", "## T3. Binary main tasks, P4 (leave-one-patient-out within 1A)", "",
            "Macro-F1 mean of 5 seeds [participant bootstrap 95% CI, seed 0]; permutation null with 100 permutations "
            "(Random Forest null uses 100 trees).", "",
            "| task | representation | model | Macro-F1 | 95% CI | null 95th pct | p |", "|---|---|---|---|---|---|---|"]
    for r in read("experiments/main_binary/summary.csv"):
        if r["protocol"] != "P4":
            continue
        n = nulls.get((r["task"], r["rep"], r["model"]))
        out.append(f"| {r['task']} | {r['rep']} | {r['model']} | {float(r['macro_f1_mean']):.3f} | "
                   f"[{float(r['macro_f1_ci_lo']):.2f}, {float(r['macro_f1_ci_hi']):.2f}] | "
                   f"{float(n['null_p95']):.3f} | {float(n['p']):.3f} |" if n else
                   f"| {r['task']} | {r['rep']} | {r['model']} | {float(r['macro_f1_mean']):.3f} | "
                   f"[{float(r['macro_f1_ci_lo']):.2f}, {float(r['macro_f1_ci_hi']):.2f}] | – | – |")
    out += ["", "## T4. Person-trait confound, P4 (Macro-F1, 5 seeds)", "",
            "| annotator | exercise | anthropometry | camera | duration | static all | R0 | Rerr_d | majority |",
            "|---|---|---|---|---|---|---|---|---|"]
    pc = {(r["annotator"], r["exercise"], r["features"]): r for r in read("person_confound_P4.csv")}
    for a in ("A", "B"):
        for ex in ("RTK", "ELK", "CTK"):
            g = lambda f: float(pc[(a, ex, f)]["macro_f1_mean"])  # noqa: E731
            ref = pc[(a, ex, "camera")]
            out.append(f"| {a} | {ex} | {g('anthropometry'):.3f} | {g('camera'):.3f} | {g('duration'):.3f} | "
                       f"{g('static_all'):.3f} | {float(ref['ref_R0']):.3f} | {float(ref['ref_Rerr_d']):.3f} | "
                       f"{float(ref['ref_majority']):.3f} |")
    return "\n".join(out) + "\n"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true")
    args = ap.parse_args()
    style()
    made = fig_clustering() + fig_main_binary("P4") + fig_main_binary("P1") + fig_person_confound()
    (ROOT / "results" / "tables.md").write_text(tables(), encoding="utf-8")
    print("wrote", ", ".join(p.relative_to(ROOT).as_posix() for p in made), "and results/tables.md")
    if args.check:
        fails = [f"missing or empty: {p}" for p in made if not p.exists() or p.stat().st_size < 5000]
        t = (ROOT / "results" / "tables.md").read_text(encoding="utf-8")
        for head in ("## T1", "## T2", "## T3", "## T4"):
            if head not in t:
                fails.append(f"tables.md lacks {head}")
        if "| CTK | A | 61 | 26 | 1 | 17 | 3 |" not in t:
            fails.append("T1 does not match the design-document counts for CTK annotator A")
        for x in fails:
            print("CHECK FAILED:", x)
        print("CHECK", "PASSED" if not fails else f"FAILED ({len(fails)})")
        return 1 if fails else 0
    return 0


if __name__ == "__main__":
    sys.exit(main())
