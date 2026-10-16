"""Confirmatory analysis exactly as pre-registered (PREREGISTRATION.md) → results/confirmatory_<exp>_<P>.{csv,md}

Reads the out-of-fold predictions of a run_experiment run (default: p1_confirmatory, protocol P1) and computes

  H1  Rerr (primary model) Macro-F1 vs a participant-level permutation null with FIXED predictions:
      the model was trained once on Group 3; test labels are permuted between test participants
      (permutation_null.permute_by_participant), 1000 permutations; Macro-F1 averaged over seeds; one-sided p.
  H2  Macro-F1(R1) - Macro-F1(R0), paired participant bootstrap (2000), seeds averaged per resample; one-sided p
      = share of resamples with difference <= 0.
  H3  Macro-F1(Rerr) - Macro-F1(R1), same.
  Holm correction over H1-H3 (family-wise alpha 0.05).

Primary = annotator A, Random Forest. Also reported, as pre-specified: the same three tests with logistic
regression (robustness: same direction?) and with annotator B (sensitivity). Only the primary family is
confirmatory.

Without Group 3 the P1 predictions do not exist; the script says so. `--check` runs a DRY RUN on the
exploratory main_binary / P4 predictions (protocol differs: leave-one-patient-out, so this is not the
pre-registered test) to exercise the code end to end, plus unit checks of the Holm procedure.

Usage:  python src/confirmatory.py [--experiment p1_confirmatory] [--protocol P1] [--check]
"""
from __future__ import annotations

import argparse
import csv
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from evaluate import macro_f1  # noqa: E402
from permutation_null import permute_by_participant  # noqa: E402

N_PERM, N_BOOT, ALPHA = 1000, 2000, 0.05
PRIMARY_MODEL, ROBUST_MODEL = "rf", "logreg(C=0.1)"


def holm(pvals: list[float]) -> list[float]:
    """Holm step-down adjusted p-values (same order as input)."""
    m = len(pvals)
    order = np.argsort(pvals)
    adj = np.empty(m)
    running = 0.0
    for rank, i in enumerate(order):
        running = max(running, min(1.0, (m - rank) * pvals[i]))
        adj[i] = running
    return adj.tolist()


def fixed_prediction_null(y, preds: list, groups, n_perm: int = N_PERM, seed: int = 0) -> dict:
    y, groups = np.asarray(y), np.asarray(groups)
    P = [np.asarray(p) for p in preds]
    score = lambda yy: float(np.mean([macro_f1(list(yy), list(p)) for p in P]))  # noqa: E731
    obs = score(y)
    rng = np.random.default_rng(seed)
    null = np.array([score(permute_by_participant(y, groups, rng)) for _ in range(n_perm)])
    return {"observed": obs, "null_mean": float(null.mean()), "null_p95": float(np.percentile(null, 95)),
            "p": float((1 + np.sum(null >= obs)) / (1 + n_perm))}


def paired_one_sided(y, preds_a: list, preds_b: list, groups, n_boot: int = N_BOOT, seed: int = 0) -> dict:
    y, groups = np.asarray(y), np.asarray(groups)
    A = [np.asarray(p) for p in preds_a]; B = [np.asarray(p) for p in preds_b]
    d = lambda idx: (np.mean([macro_f1(list(y[idx]), list(a[idx])) for a in A])  # noqa: E731
                     - np.mean([macro_f1(list(y[idx]), list(b[idx])) for b in B]))
    obs = float(d(np.arange(len(y))))
    ids = np.unique(groups)
    members = [np.flatnonzero(groups == g) for g in ids]
    rng = np.random.default_rng(seed)
    vals = np.array([d(np.concatenate([members[i] for i in rng.integers(0, len(ids), len(ids))]))
                     for _ in range(n_boot)])
    lo, hi = np.percentile(vals, [2.5, 97.5])
    return {"observed": obs, "lo": float(lo), "hi": float(hi), "p": float(max(np.mean(vals <= 0), 1 / n_boot))}


def load(root: Path, experiment: str, protocol: str):
    path = root / "results" / "experiments" / experiment / "preds.csv"
    if not path.exists():
        return None
    with (root / "data" / "labels.csv").open(encoding="utf-8") as f:
        groups_of = {r["rec_key"]: r["participant_key"] for r in csv.DictReader(f)}
    cells = defaultdict(dict)  # (task, model, rep) -> {seed: {rec_key: (y, pred)}}
    with path.open(encoding="utf-8") as f:
        for r in csv.DictReader(f):
            if r["protocol"] == protocol:
                cells[(r["task"], r["model"], r["rep"])].setdefault(int(r["seed"]), {})[r["rec_key"]] = (r["y_true"], r["y_pred"])
    return cells, groups_of


def family(cells, groups_of, task: str, model: str, n_perm: int, n_boot: int) -> list[dict]:
    def get(rep):
        seeds = cells[(task, model, rep)]
        keys = sorted(next(iter(seeds.values())))
        y = [seeds[next(iter(seeds))][k][0] for k in keys]
        return keys, y, [[s[k][1] for k in keys] for s in seeds.values()]
    kR0, y, pR0 = get("R0"); kR1, _, pR1 = get("R1"); kE, _, pE = get("Rerr")
    if not (kR0 == kR1 == kE):
        raise ValueError(f"{task} {model}: representations evaluated on different recordings")
    g = [groups_of[k] for k in kR0]
    h1 = fixed_prediction_null(y, pE, g, n_perm)
    h2 = paired_one_sided(y, pR1, pR0, g, n_boot)
    h3 = paired_one_sided(y, pE, pR1, g, n_boot)
    adj = holm([h1["p"], h2["p"], h3["p"]])
    rows = []
    for name, desc, h, a in (("H1", "Rerr > permutation null", h1, adj[0]), ("H2", "R1 > R0", h2, adj[1]),
                             ("H3", "Rerr > R1", h3, adj[2])):
        rows.append({"task": task, "model": model, "hypothesis": name, "description": desc, "n": len(y),
                     "participants": len(set(g)), **h, "p_holm": a, "supported": a < ALPHA})
    return rows


def report(rows: list[dict], experiment: str, protocol: str, dry: bool) -> str:
    lines = [f"# Confirmatory analysis — {experiment} / {protocol}", ""]
    if dry:
        lines += ["**DRY RUN on exploratory predictions (not the pre-registered protocol). Do not cite as a result.**", ""]
    lines += ["| task | model | role | H | test | n | observed | reference | p | p (Holm) | supported |",
              "|---|---|---|---|---|---|---|---|---|---|---|"]
    for r in rows:
        ref = (f"null mean {r['null_mean']:.3f}, p95 {r['null_p95']:.3f}" if "null_mean" in r
               else f"95% CI [{r['lo']:+.3f}, {r['hi']:+.3f}]")
        lines.append(f"| {r['task']} | {r['model']} | {r['role']} | {r['hypothesis']} | {r['description']} | {r['n']} | "
                     f"{r['observed']:+.3f} | {ref} | {r['p']:.4f} | {r['p_holm']:.4f} | {'yes' if r['supported'] else 'no'} |")
    return "\n".join(lines) + "\n"


def run(root: Path, experiment: str, protocol: str, tasks: tuple[str, str], n_perm=N_PERM, n_boot=N_BOOT):
    data = load(root, experiment, protocol)
    if data is None:
        return None
    cells, groups_of = data
    rows = []
    primary, sensitivity = tasks
    for task, model, role in ((primary, PRIMARY_MODEL, "confirmatory"), (primary, ROBUST_MODEL, "robustness"),
                              (sensitivity, PRIMARY_MODEL, "sensitivity"), (sensitivity, ROBUST_MODEL, "sensitivity+robustness")):
        for r in family(cells, groups_of, task, model, n_perm, n_boot):
            rows.append({**r, "role": role})
    return rows


def write(root: Path, rows, experiment, protocol, dry):
    stem = f"confirmatory_{'dryrun_' if dry else ''}{experiment}_{protocol}"
    with (root / "results" / f"{stem}.csv").open("w", newline="", encoding="utf-8") as f:
        cols = ["task", "model", "role", "hypothesis", "description", "n", "participants", "observed", "null_mean",
                "null_p95", "lo", "hi", "p", "p_holm", "supported"]
        w = csv.DictWriter(f, fieldnames=cols, extrasaction="ignore")
        w.writeheader()
        for r in rows:
            w.writerow({k: (f"{r[k]:.4f}" if isinstance(r.get(k), float) else r.get(k, "")) for k in cols})
    (root / "results" / f"{stem}.md").write_text(report(rows, experiment, protocol, dry), encoding="utf-8")
    return stem


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    ap.add_argument("--experiment", default="p1_confirmatory")
    ap.add_argument("--protocol", default="P1")
    ap.add_argument("--check", action="store_true")
    args = ap.parse_args()
    root = args.root
    tasks = ("CTK_C_vs_E13_A", "CTK_C_vs_E13_B")

    if args.check:
        fails = []
        if not np.allclose(holm([0.01, 0.04, 0.03]), [0.03, 0.06, 0.06]):
            fails.append(f"Holm example wrong: {holm([0.01, 0.04, 0.03])}")
        if not np.allclose(holm([0.5, 0.001]), [0.5, 0.002]):
            fails.append("Holm two-test example wrong")
        g = np.repeat(np.arange(8), 6); yy = np.where(g % 2 == 0, "C", "E13")
        if fixed_prediction_null(yy, [yy], g, 200)["p"] > 0.05:
            fails.append("perfect fixed predictions not significant against the participant null")
        rng = np.random.default_rng(0)
        if fixed_prediction_null(yy, [rng.choice(["C", "E13"], len(yy))], g, 200)["p"] < 0.05:
            fails.append("random fixed predictions came out significant")
        rows = run(root, "main_binary", "P4", tasks, n_perm=100, n_boot=200)
        if rows is None or len(rows) != 12:
            fails.append("dry run on main_binary/P4 did not produce 12 rows (4 families x 3 hypotheses)")
        else:
            write(root, rows, "main_binary", "P4", dry=True)
            for r in rows:
                if r["role"] == "confirmatory":
                    print(f"dry run {r['hypothesis']} ({r['description']}): observed {r['observed']:+.3f}, "
                          f"p {r['p']:.3f}, Holm {r['p_holm']:.3f}")
        if load(root, args.experiment, args.protocol) is None:
            print(f"{args.experiment}/{args.protocol}: ON HOLD (no predictions until Group 3 skeletons exist)")
        for x in fails:
            print("CHECK FAILED:", x)
        print("CHECK", "PASSED" if not fails else f"FAILED ({len(fails)})")
        return 1 if fails else 0

    rows = run(root, args.experiment, args.protocol, tasks)
    if rows is None:
        print(f"ON HOLD: results/experiments/{args.experiment}/preds.csv not found. Run "
              f"`python src/run_experiment.py --config configs/{args.experiment}.json` once Group 3 is in place.")
        return 0
    stem = write(root, rows, args.experiment, args.protocol, dry=False)
    print(f"wrote results/{stem}.csv and .md")
    print(report(rows, args.experiment, args.protocol, dry=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
