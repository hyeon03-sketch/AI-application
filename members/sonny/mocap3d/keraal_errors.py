"""RQ4: can KERAAL G3 exercise errors be detected from video-estimated 3D as well as from Vicon / Kinect?
Every source goes through the same feature extractor (joint-angle summaries) and the same classifier
(random forest, leave-one-participant-out within each exercise). Only the angle source changes.
Usage: python keraal_errors.py angles <KERAAL group3 dir> <det cache> <runs dir> <out npz>
       python keraal_errors.py classify <angles npz> <out json> [max Vicon lost-frame fraction, default 1]
       python keraal_errors.py --check
KERAAL is CC BY-NC-SA: the angles npz stays outside the repo; the json holds aggregates only."""
import glob
import json
import os
import sys
from collections import defaultdict

import numpy as np

from keraal_eval import angles_from_points, quat_rel_angle, vicon_angles

N_RESAMPLE = 10   # points of the time-normalised curve kept per angle
N_TREES = 500
EXERCISES = ("CTK", "ELK", "RTK")


def trunk_points(P, kind):
    """Trunk twist (shoulder line vs hip line) and lateral bend (spine vs hip line), degrees."""
    idx = {"kinect": (8, 4, 16, 12, 20, 0), "coco": (6, 5, 12, 11, None, None),
           "aspset": (5, 11, 2, 8, 14, 16)}[kind]
    rs, ls, rh, lh, top, bot = idx
    sh, hip = P[:, ls] - P[:, rs], P[:, lh] - P[:, rh]
    if top is None:
        top, bot = (P[:, 5] + P[:, 6]) / 2, (P[:, 11] + P[:, 12]) / 2
    else:
        top, bot = P[:, top], P[:, bot]
    ang = lambda u, v: np.degrees(np.arccos(np.clip((u * v).sum(-1) / (np.linalg.norm(u, axis=-1)
                                                                       * np.linalg.norm(v, axis=-1) + 1e-9), -1, 1)))
    return {"trunk_twist": ang(sh, hip), "trunk_bend": ang(top - bot, hip)}


def source_angles(P, kind):
    return {**angles_from_points(P, kind), **trunk_points(P, kind)}


def vicon_all(V):
    out = vicon_angles(V)
    t = quat_rel_angle(V[:, 4, 3:], V[:, 13, 3:])  # chest vs hips: twist + bend together
    t[np.isnan(out["R_elbow"])] = np.nan
    out["trunk"] = t
    return out


# Vicon targets -> pseudo ASPset joints (targets sit on segments, so joints are approximations;
# the elbow is the midpoint of the arm and forearm targets)
VICON_AS_ASPSET = [11, 15, 5, 9, (2, 0), 7, 12, 16, 6, 10, (3, 1), 8, 14, 14, 4, 4, 13]


def vicon_points(V):
    P = np.stack([V[:, j, :3] if isinstance(j, int) else V[:, list(j), :3].mean(1) for j in VICON_AS_ASPSET], 1)
    P[(np.abs(V[..., :3]).sum(-1) == 0).any(1)] = np.nan
    return P


def features(series, delta=False):
    """series: dict name -> (F,) angle in degrees (NaN allowed) -> fixed-length vector.
    delta=True subtracts each angle's mean over the first 10% of the recording (starting posture), which
    removes per-participant static offsets (e.g. where a Vicon target sits on the segment)."""
    f = []
    for name in sorted(series):
        a = series[name]
        ok = np.isfinite(a)
        if ok.sum() < 2:
            f += [np.nan] * (6 + N_RESAMPLE)
            continue
        x = np.interp(np.arange(len(a)), np.flatnonzero(ok), a[ok])
        if delta:
            x = x - x[:max(1, len(x) // 10)].mean()
        p5, p95 = np.percentile(x, [5, 95])
        f += [x.mean(), x.std(), p5, p95, p95 - p5, np.abs(np.diff(x)).mean()]
        f += list(np.interp(np.linspace(0, len(x) - 1, N_RESAMPLE), np.arange(len(x)), x))
    return np.array(f, np.float32)


def compute_angles(g3, cache, runs, out_npz):
    import torch
    from keraal_eval import lift
    from train_lift import TCN
    dev = "cuda" if torch.cuda.is_available() else "cpu"
    models = {}
    for run in sorted(glob.glob(os.path.join(runs, "det_*_s*"))):
        if not os.path.exists(os.path.join(run, "best.pt")):
            continue
        m = TCN(17, 3).to(dev)
        m.load_state_dict(torch.load(os.path.join(run, "best.pt"), map_location=dev))
        m.eval()
        models["ours_" + os.path.basename(run)[4:]] = (m, json.load(open(os.path.join(run, "args.json")))["norm"])
    print("models:", list(models))
    X, meta, vicon_bad = defaultdict(list), [], []
    for vfile in sorted(glob.glob(os.path.join(g3, "vicon", "*.txt"))):
        key = os.path.basename(vfile).replace("G3-Vicon-", "")[:-4]
        det = os.path.join(cache, "G3-Anon-" + key + ".npz")
        kin = os.path.join(g3, "kinect", "G3-Kinect-" + key + ".txt")
        if not (os.path.exists(det) and os.path.exists(kin)):
            print("missing", key)
            continue
        d = np.load(det)
        V = np.loadtxt(vfile).reshape(-1, 17, 7)
        K = np.loadtxt(kin).reshape(-1, 25, 7)[..., :3]
        K[(np.abs(K).sum(-1) == 0).any(1)] = np.nan
        series = {"vicon": vicon_all(V), "vicon_pts": source_angles(vicon_points(V), "aspset"),
                  "kinect": source_angles(K, "kinect")}
        for name, (m, norm) in models.items():
            p3d, kp2d = lift(m, d, dev, norm)
            series[name] = source_angles(p3d, "aspset")
        series["raw_2d"] = source_angles(kp2d, "coco")
        for name, sr in series.items():
            X[name].append(features(sr))
            X[name + "_d"].append(features(sr, delta=True))
        vicon_bad.append((np.abs(V[..., :3]).sum(-1) == 0).any(1).mean())
        ex, rest = key.split("-")[0], key.split("-")
        meta.append((key, ex, rest[1][:2], rest[3][:2] if rest[3] != "C" else "C"))
        print(len(meta), key, flush=True)
    np.savez_compressed(out_npz, meta=np.array(meta), vicon_bad=np.array(vicon_bad), **{k: np.stack(v) for k, v in X.items()})


def auc(y, s):
    from sklearn.metrics import roc_auc_score
    return float(roc_auc_score(y, s)) if 0 < y.sum() < len(y) else np.nan


def classify_cells(X, meta, seed=0):
    """Leave-one-participant-out within each exercise. Returns {(participant, exercise): metrics}."""
    from sklearn.ensemble import RandomForestClassifier
    from sklearn.metrics import f1_score
    out = {}
    for ex in EXERCISES:
        m = meta[:, 1] == ex
        Xe, ye, pe = X[m], meta[m, 3], meta[m, 2]
        Xe = np.where(np.isfinite(Xe), Xe, np.nanmedian(Xe, 0))
        for p in np.unique(pe):
            tr, te = pe != p, pe == p
            clf = RandomForestClassifier(N_TREES, class_weight="balanced", random_state=seed, n_jobs=-1)
            clf.fit(Xe[tr], ye[tr])
            prob = clf.predict_proba(Xe[te])
            p_err = 1 - prob[:, list(clf.classes_).index("C")]
            out[(p, ex)] = {"auc": auc((ye[te] != "C").astype(int), p_err),
                            "f1": float(f1_score(ye[te], clf.classes_[prob.argmax(1)], average="macro")),
                            "n": int(te.sum())}
    return out


def classify(npz, out_json, max_vicon_bad=1.0, seeds=(0, 1, 2)):
    """max_vicon_bad < 1 drops recordings whose Vicon has more than that fraction of frames with a lost target."""
    from scipy.stats import wilcoxon
    z = np.load(npz)
    keep = z["vicon_bad"] <= max_vicon_bad
    meta = z["meta"][keep]
    srcs = [k for k in z.files if k not in ("meta", "vicon_bad")]
    cells = {}
    for s in srcs:
        runs = [classify_cells(z[s][keep], meta, seed) for seed in seeds]
        cells[s] = {k: {m: float(np.mean([r[k][m] for r in runs])) for m in ("auc", "f1")} for k in runs[0]}
    # pool lifter seeds: one "ours_<norm>" entry = mean over the 3 trained models
    for norm in ("root", "screen"):
        for suf in ("", "_d"):
            ss = [s for s in srcs if s.startswith(f"ours_{norm}_s") and s.endswith(suf) and (suf or not s.endswith("_d"))]
            if ss:
                cells[f"ours_{norm}{suf}"] = {k: {m: float(np.mean([cells[s][k][m] for s in ss])) for m in ("auc", "f1")}
                                              for k in cells[ss[0]]}
    keys = sorted(cells["vicon"])
    summary = {s: {m: float(np.mean([cells[s][k][m] for k in keys])) for m in ("auc", "f1")} for s in cells}
    per_ex = {s: {ex: {m: float(np.mean([cells[s][k][m] for k in keys if k[1] == ex])) for m in ("auc", "f1")}
                  for ex in EXERCISES} for s in cells}
    tests = []
    for suf in ("", "_d"):
        for a, b in (("ours_root", "vicon_pts"), ("ours_root", "vicon"), ("ours_root", "kinect"), ("ours_root", "raw_2d"),
                     ("kinect", "vicon_pts"), ("ours_root", "ours_screen")):
            a, b = a + suf, b + suf
            if a not in cells or b not in cells:
                continue
            for m in ("auc", "f1"):
                d = np.array([cells[a][k][m] - cells[b][k][m] for k in keys])
                tests.append({"a": a, "b": b, "metric": m, "mean_diff": float(d.mean()), "a_better": int((d > 0).sum()),
                              "cells": len(d), "p": float(wilcoxon(d).pvalue) if np.any(d != 0) else 1.0})
    res = {"n_recordings": int(len(meta)), "max_vicon_bad": max_vicon_bad,
           "cells": {s: {f"{p}-{e}": v for (p, e), v in c.items()} for s, c in cells.items()},
           "summary": summary, "per_exercise": per_ex, "tests": tests}
    json.dump(res, open(out_json, "w"), indent=1)
    report(res)


def report(res):
    sys.stdout.reconfigure(encoding="utf-8")
    print(f"## RQ4: KERAAL G3 error detection by angle source ({res['n_recordings']} recordings, "
          f"Vicon lost-frame fraction <= {res['max_vicon_bad']})\n")
    print("Random forest on joint-angle features, leave-one-participant-out within each exercise; "
          "mean over 9 participant × exercise cells and 3 classifier seeds. AUC = correct vs any error; "
          "F1 = macro-F1 over C/E1/E2/E3 (chance 0.25). `_d` = each angle minus its starting-posture mean.\n")
    base = ("vicon", "vicon_pts", "kinect", "ours_root", "ours_screen", "raw_2d")
    order = [s + suf for suf in ("", "_d") for s in base if s + suf in res["summary"]]
    print("| source | AUC | macro-F1 | " + " | ".join(f"{e} AUC | {e} F1" for e in EXERCISES) + " |")
    print("|---|---|---|" + "---|---|" * len(EXERCISES))
    for s in order:
        v, pe = res["summary"][s], res["per_exercise"][s]
        print(f"| {s} | {v['auc']:.3f} | {v['f1']:.3f} | " +
              " | ".join(f"{pe[e]['auc']:.3f} | {pe[e]['f1']:.3f}" for e in EXERCISES) + " |")
    print("\n| comparison | metric | mean Δ | cells a better | Wilcoxon p (9 cells) |\n|---|---|---|---|---|")
    for t in res["tests"]:
        print(f"| {t['a']} − {t['b']} | {t['metric']} | {t['mean_diff']:+.3f} | {t['a_better']}/{t['cells']} | {t['p']:.3f} |")


def _check():
    rng = np.random.default_rng(0)
    # trunk: shoulders and hips parallel and spine perpendicular -> twist 0, bend 90
    P = np.zeros((5, 17, 3))
    P[:, 5], P[:, 11], P[:, 2], P[:, 8], P[:, 14], P[:, 16] = [1, 1, 0], [-1, 1, 0], [1, 0, 0], [-1, 0, 0], [0, 1, 0], 0
    t = trunk_points(P, "aspset")
    assert np.allclose(t["trunk_twist"], 0, atol=0.01) and np.allclose(t["trunk_bend"], 90)
    # features: fixed length, NaN-tolerant, a constant series has zero spread
    f = features({"a": np.r_[np.full(50, 10.0), np.nan, np.full(49, 10.0)], "b": rng.normal(size=100)})
    assert f.shape == (2 * (6 + N_RESAMPLE),) and np.isfinite(f).all() and f[1] == 0 and f[0] == 10
    assert features({"a": np.full(100, 10.0)}, delta=True)[0] == 0  # starting-posture offset removed
    V = rng.normal(size=(4, 17, 7))
    V[2, 3, :3] = 0
    Pv = vicon_points(V)
    assert Pv.shape == (4, 17, 3) and np.isnan(Pv[2]).all() and np.allclose(Pv[0, 4], V[0, [2, 0], :3].mean(0))
    # classifier: separable synthetic data -> AUC 1; random labels -> near chance
    meta = np.array([(f"r{i}", EXERCISES[i % 3], f"P{i // 3 % 3 + 1}", ["C", "E1", "E2", "E3"][i // 9 % 4])
                     for i in range(360)])
    y = (meta[:, 3] != "C").astype(float)
    Xs = np.c_[y + rng.normal(0, 0.1, 360), rng.normal(size=(360, 5))]
    assert all(v["auc"] == 1 for v in classify_cells(Xs, meta).values())
    Xr = rng.normal(size=(360, 6))
    assert abs(np.mean([v["auc"] for v in classify_cells(Xr, meta).values()]) - 0.5) < 0.15
    print("keraal_errors --check OK")


if __name__ == "__main__":
    if sys.argv[1] == "--check":
        _check()
    elif sys.argv[1] == "angles":
        compute_angles(*sys.argv[2:6])
    elif sys.argv[1] == "classify":
        classify(*sys.argv[2:4], *map(float, sys.argv[4:5]))
