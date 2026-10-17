"""L2 (exploratory): where do the P1 models put real recordings on the probability scale?

L1 showed the Group 3 models rank real recordings above chance but call most of them errors at threshold 0.5.
This describes the shift itself, without refitting anything on the test data (that is R1's job):
  - Group 3 out-of-fold probabilities (leave-one-G3-participant-out, 3 folds) show where the training classes sit;
  - the P1 model (trained on all of Group 3) gives the 1A and 2A probabilities;
  - per group x true class: median P(E13), IQR, share above 0.5;
  - two descriptive thresholds: Youden-optimal on G3 out-of-fold (what the acted data would pick) and Youden-optimal
    on the real test set (ORACLE: chosen on the test labels, shown only to measure the gap, not a usable threshold).

Same task / reps / models / seeds as configs/p1_confirmatory.json (read only). Aggregates only.
Outputs: explore/loop/l2_probability_shift.{csv,md,png}
Usage: python explore/loop/l2_probability_shift.py [--check]
"""
from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path

import numpy as np
from sklearn.metrics import roc_curve

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT / "src"))
from rf_baseline import folds_of, summarize  # noqa: E402
from run_experiment import make_model, model_name  # noqa: E402

POS = "E13"


def youden(y, s):
    if len(np.unique(y)) < 2:
        return float("nan")
    fpr, tpr, thr = roc_curve(y, s)
    return float(thr[np.argmax(tpr - fpr)])


def proba(model, rep_Z, tr_idx, ytr, te_idx, seeds):
    out = []
    for seed in seeds:
        clf = make_model(model, seed).fit(rep_Z[tr_idx], ytr)
        out.append(clf.predict_proba(rep_Z[te_idx])[:, list(clf.classes_).index(POS)])
        if model["type"] == "logreg":
            break
    return np.mean(out, axis=0)


def run(root: Path):
    cfg = json.loads((root / "configs" / "p1_confirmatory.json").read_text(encoding="utf-8"))
    feats = np.load(root / "data" / "features_T100.npz")
    pos = {k: i for i, k in enumerate(feats["keys"])}
    with (root / "data" / "labels.csv").open(encoding="utf-8") as f:
        lab = {r["rec_key"]: r for r in csv.DictReader(f)}
    sp = json.loads((root / "data" / "splits.json").read_text(encoding="utf-8"))
    folds = folds_of(sp, "P1")
    train, test = folds[0][1], [k for _, _, te in folds for k in te]
    Z = {r: summarize(feats[r].astype(np.float64)) for r in cfg["reps"]}
    rows, curves = [], {}
    for task in cfg["tasks"]:
        col, ex, keep = task["label_col"], task["exercise"], task["classes"]
        ann = col.split("_")[1]
        ok = lambda k: lab[k]["exercise"] == ex and lab[k][col] in keep  # noqa: E731
        tr = [k for k in train if ok(k)]
        te = [k for k in test if ok(k)]
        ytr = np.array([lab[k][col] for k in tr])
        gtr = np.array([lab[k]["participant_key"] for k in tr])
        for model in [m for m in cfg["models"] if m["type"] != "majority"]:
            for rep in cfg["reps"]:
                # G3 out-of-fold
                s_g3 = np.zeros(len(tr))
                for p in np.unique(gtr):
                    m = gtr == p
                    s_g3[m] = proba(model, Z[rep], [pos[k] for k in np.array(tr)[~m]], ytr[~m],
                                    [pos[k] for k in np.array(tr)[m]], cfg["seeds"])
                # P1 model on the real test set
                s_te = proba(model, Z[rep], [pos[k] for k in tr], list(ytr), [pos[k] for k in te], cfg["seeds"])
                y_g3 = (ytr == POS).astype(int)
                y_te = np.array([lab[k][col] == POS for k in te], dtype=int)
                grp = np.array([lab[k]["group"] for k in te])
                thr_g3, thr_real = youden(y_g3, s_g3), youden(y_te, s_te)
                sets = [("G3 (OOF)", y_g3, s_g3, len(set(gtr)))] + [
                    (g, y_te[grp == g], s_te[grp == g], len({lab[k]["participant_key"] for k in np.array(te)[grp == g]}))
                    for g in ("1A", "2A")]
                for name, y, s, n_p in sets:
                    for c, cname in ((0, "C"), (1, POS)):
                        v = s[y == c]
                        rows.append({"annotator": ann, "model": model_name(model), "rep": rep, "set": name,
                                     "class": cname, "n": int(len(v)), "participants": n_p,
                                     "median_p": float(np.median(v)), "q25": float(np.percentile(v, 25)),
                                     "q75": float(np.percentile(v, 75)), "share_above_0.5": float((v >= 0.5).mean()),
                                     "thr_youden_G3": thr_g3, "thr_youden_real_oracle": thr_real})
                curves[(ann, model_name(model), rep)] = sets, thr_g3, thr_real
    return rows, curves


def plot(curves, out: Path):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    keys = [k for k in curves if k[2] in ("R1", "Rerr")]
    fig, axes = plt.subplots(len(keys) // 2, 2, figsize=(10, 2.6 * (len(keys) // 2)), sharex=True)
    col = {"C": "#3b6ea5", "E13": "#c0392b"}
    for ax, key in zip(axes.ravel(), sorted(keys)):
        sets, tg, tr = curves[key]
        data, labels, colors = [], [], []
        for name, y, s, _ in sets:
            for c, cname in ((0, "C"), (1, "E13")):
                data.append(s[y == c]); labels.append(f"{name} {cname} (n={int((y == c).sum())})"); colors.append(col[cname])
        bp = ax.boxplot(data, orientation="horizontal", patch_artist=True, widths=0.6, showfliers=False)
        for patch, c in zip(bp["boxes"], colors):
            patch.set_facecolor(c); patch.set_alpha(0.45)
        ax.set_yticks(range(1, len(labels) + 1), labels, fontsize=7)
        ax.axvline(0.5, color="k", lw=1, ls="--", label="0.5")
        ax.axvline(tg, color="#2e7d32", lw=1.2, label=f"Youden G3 {tg:.2f}")
        ax.axvline(tr, color="#8e44ad", lw=1.2, ls=":", label=f"Youden real (oracle) {tr:.2f}")
        ax.set_title(f"annotator {key[0]} · {key[1]} · {key[2]}", fontsize=8)
        ax.legend(fontsize=6, loc="lower right")
        ax.set_xlim(0, 1)
    for ax in axes[-1]:
        ax.set_xlabel("P(E13)")
    fig.suptitle("L2 (exploratory): P(E13) by set and true class — CTK C vs E13, P1 models", fontsize=9)
    fig.tight_layout()
    fig.savefig(out, dpi=130)


def write(rows, out: Path):
    fmt = lambda v: f"{v:.3f}" if isinstance(v, float) else v  # noqa: E731
    with out.with_suffix(".csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        for r in rows:
            w.writerow({k: fmt(v) for k, v in r.items()})
    cols = ["annotator", "model", "rep", "set", "class", "n", "participants", "median_p", "q25", "q75",
            "share_above_0.5", "thr_youden_G3", "thr_youden_real_oracle"]
    lines = ["# L2 · 확률 분포와 기준점 위치 (탐색) / probability shift (exploratory)", "",
             "P(E13) 분포. G3는 참가자 하나씩 뺀 out-of-fold, 1A·2A는 G3 전체로 학습한 P1 모델. "
             "`thr_youden_real_oracle`은 시험 라벨로 고른 값이라 격차 측정용일 뿐 사용할 수 있는 기준점이 아니다.", "",
             "| " + " | ".join(cols) + " |", "|" + "---|" * len(cols)]
    lines += ["| " + " | ".join(str(fmt(r[c])) for c in cols) + " |" for r in rows]
    out.with_suffix(".md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true")
    a = ap.parse_args()
    if a.check:
        y = np.array([0, 0, 1, 1]); s = np.array([0.1, 0.2, 0.7, 0.9])
        ok = 0.2 < youden(y, s) <= 0.7 and np.isnan(youden(np.zeros(3), np.ones(3)))
        print("CHECK", "PASSED" if ok else "FAILED")
        return 0 if ok else 1
    rows, curves = run(ROOT)
    out = HERE / "l2_probability_shift"
    write(rows, out)
    plot(curves, out.with_suffix(".png"))
    print(out.with_suffix(".md").read_text(encoding="utf-8"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
