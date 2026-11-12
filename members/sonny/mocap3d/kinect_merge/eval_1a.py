"""1A patients (never trained on; no Vicon): 3D agreement with the Kinect, the only 3D reference there.
Kinect legs and hips are within 11-38 mm of Vicon on G3, arms are not (wrist 122 mm), so the leg numbers carry the weight.
Usage: python eval_1a.py <out json> <name>=<best.pt>[@flag][@nosqueeze] ...
       python eval_1a.py --check"""
import glob
import json
import os
import sys

import numpy as np
import torch

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, ".."))
import aspset
from audit import hip_angle, kinect17
from demo_rehab import lift
from keraal_eval import angles_from_points
from km_train import FlagTCN
from train_lift import TCN

ROOT, DET = "E:/KERAAL_data/extracted/group1A", "E:/KERAAL_mocap3d/g1a/det_clean"
LEGS = [aspset.JOINTS.index(j) for j in ("right_ankle", "right_knee", "right_hip", "left_ankle", "left_knee", "left_hip")]
VALID = [j for j in range(17) if aspset.JOINTS[j] != "head_top"]


def compare(P, K):
    """P, K (F, 17, 3) mm pelvis-relative. MPJPE all/legs, hip-angle and knee-angle median absolute difference (deg)."""
    e = np.linalg.norm(P - K, axis=-1)
    ap, ak = angles_from_points(P, "aspset"), angles_from_points(K, "aspset")
    knee = np.nanmedian(np.abs(np.r_[ap["R_knee"] - ak["R_knee"], ap["L_knee"] - ak["L_knee"]]))
    return {"mpjpe": float(np.nanmean(e[:, VALID])), "legs": float(np.nanmean(e[:, LEGS])),
            "hip_angle": float(np.nanmedian(np.abs(hip_angle(P) - hip_angle(K)))), "knee_angle": float(knee),
            "hip_angle_pred": float(np.nanmedian(hip_angle(P))), "hip_angle_kinect": float(np.nanmedian(hip_angle(K)))}


def main(out, specs):
    dev = "cuda" if torch.cuda.is_available() else "cpu"
    res = {}
    for spec in specs:
        name, rest = spec.split("=", 1)
        path, *opts = rest.split("@")
        model = FlagTCN(17, 3) if "flag" in opts else TCN(17, 3)
        model.load_state_dict(torch.load(path, map_location=dev))
        model = model.to(dev).eval()
        rows = []
        for det in sorted(glob.glob(f"{DET}/*.npz")):
            key = os.path.basename(det)[:-4]
            d = np.load(det)
            if d["found"].mean() < 0.5:
                continue
            K = kinect17(f"{ROOT}/kinect/G1A-Kinect-{key}.txt")
            P, _ = lift(model, d["kp"], d["conf"], d["found"], 15, "nosqueeze" not in opts, dev)
            n = min(len(P), len(K))
            K = K[:n] - K[:n, aspset.PELVIS:aspset.PELVIS + 1]
            rows.append({"key": key, "patient": key.split("-")[1], **compare(P[:n], K)})
        pats = sorted({r["patient"] for r in rows})
        res[name] = {m: float(np.median([r[m] for r in rows])) for m in rows[0] if m not in ("key", "patient")}
        res[name]["per_patient_legs"] = {p: round(float(np.median([r["legs"] for r in rows if r["patient"] == p])), 1) for p in pats}
        print(name, json.dumps({k: round(v, 1) if isinstance(v, float) else v for k, v in res[name].items()}), flush=True)
    json.dump(res, open(out, "w"), indent=1)


def _check():
    rng = np.random.default_rng(0)
    K = rng.normal(size=(30, 17, 3)) * 200
    r = compare(K.copy(), K)
    assert r["mpjpe"] < 1e-9 and r["hip_angle"] < 1e-6 and r["knee_angle"] < 1e-6
    r = compare(K + [10, 0, 0], K)
    assert abs(r["mpjpe"] - 10) < 1e-9 and r["hip_angle"] < 1e-6
    print("eval_1a --check OK")


if __name__ == "__main__":
    _check() if sys.argv[1:] == ["--check"] else main(sys.argv[1], sys.argv[2:])
