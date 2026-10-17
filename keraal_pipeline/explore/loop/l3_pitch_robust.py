"""L3 (exploratory, backlog 13): do pitch-robust features shrink the sim-to-real gap?

Group 3 was filmed with a different camera pose (sagittal spine tilt -4 deg vs -18 deg in 1A/2A, PROGRESS 10-08).
Features tagged sagittal (y-z plane) or vertical (heights) move with camera pitch; invariant, frontal and
horizontal ones should not (src/features.py). For R4 and Rerr we compare three column subsets:
  full        all features of the representation
  robust      invariant + frontal + horizontal   (backlog 13 definition)
  invariant   invariant only
on CTK C vs E13 under
  P1  train Group 3 -> test 1A + 2A   (sim-to-real)
  P4  leave-one-participant-out inside 1A + 2A (real -> real reference)
gap = P4 - P1. Per annotator, model (RF 5-seed averaged probability, logreg C=0.1):
  Macro-F1 at 0.5, AUC, share predicted E13; P1 AUC null = within-participant label shuffles (1,000).
Majority baseline Macro-F1 is listed per annotator. Aggregates only.
Outputs: explore/loop/l3_pitch_robust.{csv,md}
Usage: python explore/loop/l3_pitch_robust.py [--perms 1000] [--check]
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
from l1_acted_to_real_auc import shuffle_within  # noqa: E402
from rf_baseline import folds_of, summarize  # noqa: E402
from run_experiment import make_model, model_name  # noqa: E402

POS = "E13"
SUBSETS = {"full": None, "robust": {"invariant", "frontal", "horizontal"}, "invariant": {"invariant"}}
MODELS = [{"type": "rf"}, {"type": "logreg", "C": 0.1}]
SEEDS = [0, 1, 2, 3, 4]


def column_mask(planes: list[str], keep: set[str] | None) -> np.ndarray:
    """summarize() stacks 7 statistics of every feature, feature-fastest: tile the per-feature mask 7 times."""
    m = np.ones(len(planes), bool) if keep is None else np.array([p in keep for p in planes])
    return np.tile(m, 7)


def oof_scores(Zs, folds, ok, lab, col, pos, model):
    s_all, y_all, g_all, grp = [], [], [], []
    for _, tr, te in folds:
        tr, te = [k for k in tr if ok(k)], [k for k in te if ok(k)]
        ytr = [lab[k][col] for k in tr]
        if not te:
            continue
        if len(set(ytr)) < 2:
            s = np.full(len(te), float(ytr[0] == POS))
        else:
            ss = []
            for seed in SEEDS:
                clf = make_model(model, seed).fit(Zs[[pos[k] for k in tr]], ytr)
                ss.append(clf.predict_proba(Zs[[pos[k] for k in te]])[:, list(clf.classes_).index(POS)])
                if model["type"] == "logreg":
                    break
            s = np.mean(ss, axis=0)
        s_all += list(s); y_all += [lab[k][col] == POS for k in te]
        g_all += [lab[k]["participant_key"] for k in te]; grp += [lab[k]["group"] for k in te]
    return np.array(s_all), np.array(y_all, int), np.array(g_all), np.array(grp)


def run(root: Path, perms: int):
    names = json.loads((root / "data" / "feature_names.json").read_text(encoding="utf-8"))
    feats = np.load(root / "data" / "features_T100.npz")
    pos = {k: i for i, k in enumerate(feats["keys"])}
    with (root / "data" / "labels.csv").open(encoding="utf-8") as f:
        lab = {r["rec_key"]: r for r in csv.DictReader(f)}
    sp = json.loads((root / "data" / "splits.json").read_text(encoding="utf-8"))
    rng = np.random.default_rng(0)
    rows = []
    for rep in ("R4", "Rerr"):
        Z = summarize(feats[rep].astype(np.float64))
        planes = [d["plane"] for d in names[rep]]
        for col in ("label_A_ctk13", "label_B_ctk13"):
            ok = lambda k: lab[k]["exercise"] == "CTK" and lab[k][col] in ("C", POS)  # noqa: E731
            for sub, keep in SUBSETS.items():
                mask = column_mask(planes, keep)
                Zs = Z[:, mask]
                for model in MODELS:
                    res = {}
                    for proto in ("P1", "P4"):
                        s, y, g, grp = oof_scores(Zs, folds_of(sp, proto), ok, lab, col, pos, model)
                        res[proto] = dict(f1=f1_score(y, (s >= 0.5).astype(int), average="macro"),
                                          auc=roc_auc_score(y, s), pred=float((s >= 0.5).mean()),
                                          n=len(y), parts=len(set(g)), y=y, s=s, g=g)
                    p1 = res["P1"]
                    null = np.array([roc_auc_score(shuffle_within(p1["y"], p1["g"], rng), p1["s"])
                                     for _ in range(perms)])
                    maj = f1_score(p1["y"], np.full_like(p1["y"], np.bincount(p1["y"]).argmax()), average="macro")
                    rows.append({"rep": rep, "annotator": col.split("_")[1], "subset": sub,
                                 "n_features": int(mask.sum() // 7), "model": model_name(model),
                                 "P1_n": p1["n"], "P1_participants": p1["parts"],
                                 "P1_f1": p1["f1"], "P1_majority_f1": maj, "P1_auc": p1["auc"],
                                 "P1_auc_null_p95": float(np.percentile(null, 95)),
                                 "P1_auc_p": float((1 + (null >= p1["auc"]).sum()) / (perms + 1)),
                                 "P1_pred_err": p1["pred"], "true_err": float(p1["y"].mean()),
                                 "P4_f1": res["P4"]["f1"], "P4_auc": res["P4"]["auc"],
                                 "P4_participants": res["P4"]["parts"],
                                 "gap_f1": res["P4"]["f1"] - p1["f1"], "gap_auc": res["P4"]["auc"] - p1["auc"]})
    return rows


def write(rows, out: Path):
    fmt = lambda v: f"{v:.3f}" if isinstance(v, float) else v  # noqa: E731
    with out.with_suffix(".csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        for r in rows:
            w.writerow({k: fmt(v) for k, v in r.items()})
    cols = ["rep", "annotator", "subset", "n_features", "model", "P1_f1", "P1_majority_f1", "P1_auc",
            "P1_auc_null_p95", "P1_auc_p", "P1_pred_err", "true_err", "P4_f1", "P4_auc", "gap_f1", "gap_auc"]
    r0 = rows[0]
    lines = ["# L3 · pitch에 강한 feature만 쓰면 sim-to-real 격차가 줄어드는가 (탐색) / pitch-robust features (exploratory)",
             "", f"CTK C vs E13. P1 = G3 학습 → 1A·2A 시험 (n = {r0['P1_n']}, 참가자 {r0['P1_participants']}명), "
             f"P4 = 1A·2A 안 참가자 하나씩 빼기 (참가자 {r0['P4_participants']}명). gap = P4 − P1. "
             "robust = invariant + frontal + horizontal (sagittal·vertical 제외).", "",
             "| " + " | ".join(cols) + " |", "|" + "---|" * len(cols)]
    lines += ["| " + " | ".join(str(fmt(r[c])) for c in cols) + " |" for r in rows]
    out.with_suffix(".md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--perms", type=int, default=1000)
    ap.add_argument("--check", action="store_true")
    a = ap.parse_args()
    if a.check:
        m = column_mask(["invariant", "sagittal", "frontal"], SUBSETS["robust"])
        ok = m.tolist() == [True, False, True] * 7 and column_mask(["x", "y"], None).all()
        print("CHECK", "PASSED" if ok else "FAILED")
        return 0 if ok else 1
    rows = run(ROOT, a.perms)
    out = HERE / "l3_pitch_robust"
    write(rows, out)
    print(out.with_suffix(".md").read_text(encoding="utf-8"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
