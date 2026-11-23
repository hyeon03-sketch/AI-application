"""KERAAL G3 metrics from the shared bundle, the same way for every model.

  python keraal_metrics.py --name VP3D_after --pred runs/keraal_test_P1_s0/pred_test.npz runs/.../P2 runs/.../P3
  python keraal_metrics.py --name Kinect --kinect                # Kinect skeleton as the "prediction"
  python keraal_metrics.py --name VP3D_before --pred runs/keraal_before_pred3d.npz

Position: as merge_train.eval_keraal (frame mean over the valid joints, head top left out, pooled over frames; PA on
frames with all 16 joints). Angles: keraal_eval's angle definitions, moving-angle rule (std >= 5 deg), lag search
(+-30 frames) and mean-removed RMSE, but the REFERENCE is the angle computed from the Vicon JOINT POINTS in the bundle.
The original 13.5 / 18.7 deg used Vicon segment quaternions from the raw files, which are not in the bundle, so these
angle numbers are a different definition and must not be mixed with the original ones."""
import argparse
import json
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "code_1118"))
from keraal_eval import MAX_LAG, STD_MIN, angles_from_points, corr, shift   # noqa: E402
from train_lift import pa_mpjpe                                              # noqa: E402

KER = os.path.join(HERE, "..", "data", "Mocap3D_preprocessed_KERAAL_1118")
A2H = [16, 2, 1, 0, 8, 7, 6, 15, 14, 13, 12, 11, 10, 9, 5, 4, 3]
H2A = list(np.argsort(A2H))
VALID = [j for j in range(17) if j != 12]                                    # ASPset order, head top left out


def evaluate(pred, name):
    G = np.load(os.path.join(KER, "keraal_g3_gt3d.npz"))
    sp = json.load(open(os.path.join(KER, "splits.json")))["keraal_g3"]
    mp, pa, rows = [], [], []
    for rid in pred:
        P, Y = pred[rid][:, H2A].astype(np.float64), G[rid][:, H2A].astype(np.float64)
        n = min(len(P), len(Y)); P, Y = P[:n], Y[:n]
        P, Y = P - P[:, 16:17], Y - Y[:, 16:17]
        e = np.linalg.norm(P[:, VALID] - Y[:, VALID], axis=-1)
        if np.isfinite(e).any():
            mp.append(np.nanmean(e[np.isfinite(e).any(1)], 1))
        full = np.isfinite(Y[:, VALID]).all((1, 2)) & np.isfinite(P[:, VALID]).all((1, 2))
        if full.any():
            pa.append(pa_mpjpe(P[full][:, VALID].copy(), Y[full][:, VALID]))
        ap, ag = angles_from_points(P, "aspset"), angles_from_points(Y, "aspset")
        moving = [a for a in ag if np.isfinite(ag[a]).sum() >= 30 and np.nanstd(ag[a]) >= STD_MIN]
        if not moving:
            continue
        score = {l: np.nanmean([corr(shift(ap[a], l), ag[a])[0] for a in moving]) for l in range(-MAX_LAG, MAX_LAG + 1)}
        lag = max(score, key=lambda l: -2 if np.isnan(score[l]) else score[l])
        for a in moving:
            r, rm = corr(shift(ap[a], lag), ag[a])
            rows.append({"rec": rid, "participant": sp["participant"][rid] if isinstance(sp["participant"], dict) else None,
                         "angle": a, "r0": float(corr(ap[a], ag[a])[0]), "r": float(r), "rmse": float(rm)})
    out = {"name": name, "recordings": len(pred), "mpjpe_mm": float(np.mean(np.concatenate(mp))),
           "pa_mpjpe_mm": float(np.mean(np.concatenate(pa))), "angle_pairs": len(rows),
           "angle_r0_median": float(np.nanmedian([r["r0"] for r in rows])),
           "angle_rmse_median_deg": float(np.nanmedian([r["rmse"] for r in rows]))}
    parts = sorted({r["participant"] for r in rows if r["participant"]})
    out["by_participant"] = {p: round(float(np.nanmedian([r["rmse"] for r in rows if r["participant"] == p])), 2) for p in parts}
    return out, rows


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--name", required=True)
    ap.add_argument("--pred", nargs="*", default=[])
    ap.add_argument("--kinect", action="store_true")
    ap.add_argument("--out", default=None)
    a = ap.parse_args()
    pred = {}
    for f in ([os.path.join(KER, "keraal_g3_kinect3d.npz")] if a.kinect else a.pred):
        z = np.load(f)
        pred.update({k: z[k] for k in z.files})
    res, rows = evaluate(pred, a.name)
    print(json.dumps(res, indent=1))
    if a.out:
        json.dump({"summary": res, "rows": rows}, open(a.out, "w"))
