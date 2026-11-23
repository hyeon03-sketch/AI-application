"""Model comparison per statistical unit (participant x exercise, 9 units) on KERAAL group 3.

  python unit_compare.py                  # reads runs/ next to this file, writes runs/unit_compare.json

Seeds are averaged inside each unit first, so the test is over people x exercises, not over training runs.
MPJPE: mean over the unit's recordings. Angle RMSE: median over the unit's (recording, angle) pairs, as keraal_metrics.py.
Wilcoxon signed-rank on the 9 paired differences (two-sided, no correction for multiple comparisons)."""
import json
import os
import sys

import numpy as np
from scipy.stats import wilcoxon

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import keraal_metrics as km   # noqa: E402

RUNS = os.path.join(HERE, "runs")
SP = json.load(open(os.path.join(km.KER, "splits.json")))["keraal_g3"]
G = np.load(os.path.join(km.KER, "keraal_g3_gt3d.npz"))


def load(files):
    d = {}
    for f in files:
        z = np.load(f)
        d.update({k: z[k] for k in z.files})
    return d


def unit(rid):
    return SP["participant"][rid], SP["exercise"][rid]


def per_unit(pred):
    mp, ang = {}, {}
    for rid in pred:
        P, Y = pred[rid][:, km.H2A].astype(float), G[rid][:, km.H2A].astype(float)
        n = min(len(P), len(Y))
        P, Y = P[:n] - P[:n, 16:17], Y[:n] - Y[:n, 16:17]
        e = np.linalg.norm(P[:, km.VALID] - Y[:, km.VALID], axis=-1)
        ok = np.isfinite(e).any(1)
        if ok.any():
            mp.setdefault(unit(rid), []).append(np.nanmean(e[ok], 1).mean())
    for r in km.evaluate(pred, "x")[1]:
        ang.setdefault(unit(r["rec"]), []).append(r["rmse"])
    units = sorted(mp)
    return units, np.array([np.mean(mp[u]) for u in units]), np.array([np.nanmedian(ang.get(u, [np.nan])) for u in units])


if __name__ == "__main__":
    models = {"Kinect": [load([os.path.join(km.KER, "keraal_g3_kinect3d.npz")])]}
    for label, pat in (("VideoPose3D", "keraal_test_{}_s{}"), ("Mocap3D", "m3d_test_{}_s{}")):
        models[label] = [load([os.path.join(RUNS, pat.format(p, s), "pred_test.npz") for p in ("P1", "P2", "P3")]) for s in (0, 1, 2)]
    res = {}
    for k, preds in models.items():
        outs = [per_unit(p) for p in preds]
        res[k] = {"units": ["-".join(u) for u in outs[0][0]], "mpjpe_mm": np.mean([o[1] for o in outs], 0),
                  "angle_rmse_deg": np.mean([o[2] for o in outs], 0)}
    out = {"units": res["Mocap3D"]["units"], "per_unit": {}, "tests": {}}
    for metric in ("mpjpe_mm", "angle_rmse_deg"):
        out["per_unit"][metric] = {k: [round(float(x), 2) for x in v[metric]] for k, v in res.items()}
        print(f"\n{metric}:", "  ".join(out["units"]))
        for k in res:
            print(f"  {k:12s}", np.round(res[k][metric], 1))
        for other in ("VideoPose3D", "Kinect"):
            d = res["Mocap3D"][metric] - res[other][metric]
            t = {"mocap3d_lower_units": int((d < 0).sum()), "n_units": len(d), "mean_diff": round(float(d.mean()), 2),
                 "wilcoxon_p": round(float(wilcoxon(d).pvalue), 4)}
            out["tests"][f"{metric}: Mocap3D vs {other}"] = t
            print(f"  Mocap3D lower than {other} in {t['mocap3d_lower_units']}/9 units, mean diff {t['mean_diff']:+.2f}, p={t['wilcoxon_p']}")
    json.dump(out, open(os.path.join(RUNS, "unit_compare.json"), "w"), indent=1)
    print("\nwritten:", os.path.join(RUNS, "unit_compare.json"))
