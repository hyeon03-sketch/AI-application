"""L9 (exploratory): is the acted -> real shift a "patient" effect or a "session / setting" effect?

L1, L2 and L8 showed that Group 3 models push real recordings towards "error" on CTK and RTK. Two explanations:
  patient effect   patients move differently even when they are judged correct, so their "correct" looks like
                   an acted error;
  session effect   the robot-coached sessions (camera, room, instructions, standing vs sitting) differ from the
                   Group 3 lab, for everyone.
The healthy adults of 2A were recorded in the same robot-coached sessions as the patients of 1A, at the same two
sites. So for recordings that the annotator judged CORRECT, we compare the probability of error the same Group 3
model gives to 1A (patients) and 2A (healthy):
  2A correct ~ G3 correct (low)  and 1A correct high  -> patient effect
  2A correct ~ 1A correct (both high)                  -> session effect
Per exercise (CTK C vs E1+E3, RTK C vs E1+E2, ELK C vs E2), rep (R1, Rerr), model (RF 5-seed mean, logreg C = 0.1),
annotator (A, B):
  median P(error) of correct recordings for G3 (leave-one-G3-participant-out), 1A and 2A, and the share >= 0.5;
  1A - 2A difference of participant means, with an exact participant-level permutation test (all relabelings of
  participants into 1A / 2A, two-sided) - the unit of inference is the person, not the recording;
  the same contrast between sites (Brest vs Roscoff) inside 1A + 2A, as a check on site.
Aggregates only. Outputs: explore/loop/l9_patient_vs_session.{csv,md}
Usage: python explore/loop/l9_patient_vs_session.py [--check]
"""
from __future__ import annotations

import argparse
import csv
import itertools
import json
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT / "src"))
from rf_baseline import folds_of, summarize  # noqa: E402
from run_experiment import make_model, model_name  # noqa: E402

TASKS = [("CTK", "label_{a}_ctk13", {"C": 0, "E13": 1}), ("RTK", "label_{a}", {"C": 0, "E1": 1, "E2": 1}),
         ("ELK", "label_{a}", {"C": 0, "E2": 1})]
REPS = ["R1", "Rerr"]
MODELS = [{"type": "rf"}, {"type": "logreg", "C": 0.1}]
SEEDS = [0, 1, 2, 3, 4]


def perm_test(values: dict[str, float], group: dict[str, str], a: str, b: str):
    """Exact permutation of participant labels. values: participant -> mean score. Returns (diff a-b, p, n_a, n_b)."""
    ps = [p for p in values if group[p] in (a, b)]
    na = sum(group[p] == a for p in ps)
    if na == 0 or na == len(ps):
        return float("nan"), float("nan"), na, len(ps) - na
    v = np.array([values[p] for p in ps])
    obs = v[[group[p] == a for p in ps]].mean() - v[[group[p] == b for p in ps]].mean()
    diffs = []
    for idx in itertools.combinations(range(len(ps)), na):
        m = np.zeros(len(ps), bool); m[list(idx)] = True
        diffs.append(v[m].mean() - v[~m].mean())
    diffs = np.array(diffs)
    return float(obs), float((np.abs(diffs) >= abs(obs) - 1e-12).mean()), na, len(ps) - na


def proba(model, Z, tr, ytr, te):
    out = []
    for seed in SEEDS:
        clf = make_model(model, seed).fit(Z[tr], ytr)
        out.append(clf.predict_proba(Z[te])[:, list(clf.classes_).index(1)])
        if model["type"] == "logreg":
            break
    return np.mean(out, axis=0)


def run(root: Path):
    feats = np.load(root / "data" / "features_T100.npz")
    pos = {k: i for i, k in enumerate(feats["keys"])}
    with (root / "data" / "labels.csv").open(encoding="utf-8") as f:
        lab = {r["rec_key"]: r for r in csv.DictReader(f)}
    with (root / "data" / "master_index.csv").open(encoding="utf-8") as f:
        site = {r["rec_key"]: r["site"] for r in csv.DictReader(f)}
    sp = json.loads((root / "data" / "splits.json").read_text(encoding="utf-8"))
    folds = folds_of(sp, "P1")
    train, test = folds[0][1], [k for _, _, te in folds for k in te]
    Z = {r: summarize(feats[r].astype(np.float64)) for r in REPS}
    rows = []
    for ex, colt, cmap in TASKS:
        for ann in ("A", "B"):
            col = colt.format(a=ann)
            ok = lambda k: lab[k]["exercise"] == ex and lab[k][col] in cmap  # noqa: E731
            tr, te = [k for k in train if ok(k)], [k for k in test if ok(k)]
            ytr = np.array([cmap[lab[k][col]] for k in tr])
            gtr = np.array([lab[k]["participant_key"] for k in tr])
            te_c = [k for k in te if cmap[lab[k][col]] == 0]
            for model in MODELS:
                for rep in REPS:
                    # G3 correct, out-of-fold
                    g3 = []
                    for p in np.unique(gtr):
                        m = gtr == p
                        s = proba(model, Z[rep], [pos[k] for k in np.array(tr)[~m]], ytr[~m],
                                  [pos[k] for k in np.array(tr)[m]])
                        g3 += list(s[ytr[m] == 0])
                    s = proba(model, Z[rep], [pos[k] for k in tr], ytr, [pos[k] for k in te_c])
                    sc = dict(zip(te_c, s))
                    by_p = {}
                    for k in te_c:
                        by_p.setdefault(lab[k]["participant_key"], []).append(sc[k])
                    pmean = {p: float(np.mean(v)) for p, v in by_p.items()}
                    grp = {lab[k]["participant_key"]: lab[k]["group"] for k in te_c}
                    sit = {lab[k]["participant_key"]: site[k] for k in te_c}
                    d_g, p_g, n1, n2 = perm_test(pmean, grp, "1A", "2A")
                    d_s, p_s, nb, nr = perm_test(pmean, sit, "Brest", "Roscoff")
                    s1 = np.array([sc[k] for k in te_c if lab[k]["group"] == "1A"])
                    s2 = np.array([sc[k] for k in te_c if lab[k]["group"] == "2A"])
                    rows.append({"exercise": ex, "annotator": ann, "model": model_name(model), "rep": rep,
                                 "G3_correct_n": len(g3), "G3_correct_median": float(np.median(g3)),
                                 "1A_correct_n": len(s1), "1A_participants": n1,
                                 "1A_correct_median": float(np.median(s1)) if len(s1) else float("nan"),
                                 "1A_share_flagged": float((s1 >= 0.5).mean()) if len(s1) else float("nan"),
                                 "2A_correct_n": len(s2), "2A_participants": n2,
                                 "2A_correct_median": float(np.median(s2)) if len(s2) else float("nan"),
                                 "2A_share_flagged": float((s2 >= 0.5).mean()) if len(s2) else float("nan"),
                                 "diff_1A_minus_2A": d_g, "perm_p_group": p_g,
                                 "diff_Brest_minus_Roscoff": d_s, "perm_p_site": p_s,
                                 "site_participants": f"{nb}/{nr}"})
    return rows


def write(rows, out: Path):
    fmt = lambda v: ("–" if v != v else f"{v:.3f}") if isinstance(v, float) else v  # noqa: E731
    with out.with_suffix(".csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        for r in rows:
            w.writerow({k: fmt(v) for k, v in r.items()})
    cols = list(rows[0])
    lines = ["# L9 · 이동은 '환자라서'인가 '세션이라서'인가 (탐색) / patient vs session effect (exploratory)", "",
             "주석자가 **정상**으로 판정한 녹화만. 같은 G3 모델이 주는 P(오류). 1A = 환자, 2A = 건강인(같은 로봇 코칭 세션, "
             "같은 두 장소). 검정 단위는 사람(참가자 평균), 모든 재배치를 다 따지는 정확 순열 검정(양측).", "",
             "| " + " | ".join(cols) + " |", "|" + "---|" * len(cols)]
    lines += ["| " + " | ".join(str(fmt(r[c])) for c in cols) + " |" for r in rows]
    out.with_suffix(".md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true")
    a = ap.parse_args()
    if a.check:
        vals = {"a1": 1.0, "a2": 1.0, "b1": 0.0, "b2": 0.0}
        grp = {"a1": "X", "a2": "X", "b1": "Y", "b2": "Y"}
        d, p, na, nb = perm_test(vals, grp, "X", "Y")
        ok = d == 1.0 and abs(p - 2 / 6) < 1e-9 and (na, nb) == (2, 2)
        print("CHECK", "PASSED" if ok else f"FAILED {d} {p}")
        return 0 if ok else 1
    rows = run(ROOT)
    out = HERE / "l9_patient_vs_session"
    write(rows, out)
    print(out.with_suffix(".md").read_text(encoding="utf-8"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
