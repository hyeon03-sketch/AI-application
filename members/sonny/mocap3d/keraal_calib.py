"""Post-hoc camera calibration for KERAAL G3, so Vicon can be expressed like ASPset (camera coords, mm, aspset_17j).
Bridge: the G3 video is the Kinect v2 colour stream, so Kinect camera-space joints link Vicon to pixels.
  1. Intrinsics: one pinhole K (+ small Kinect depth->colour offset t0) fitted on all recordings,
     Kinect joints <-> YOLO 2D keypoints, robust least squares. Camera axes: OpenCV (x right, y down, z forward).
  2. Vicon -> camera, one rigid R, t per session = participant x exercise (scale fixed, mm), jointly with a constant offset of each
     virtual joint in its Vicon target's local frame (targets sit on segments, not on joint centres).
     Alternating least squares: Kabsch for R, t | per-joint offsets in closed form. Per-recording time lag.
     Fitted on even-numbered recordings, validated on odd ones (3D vs Kinect, 2D reprojection vs YOLO).
Outputs (outside the repo; KERAAL is CC BY-NC-SA): <out>/calib.json, <out>/gt3d/<key>.npz with
  vicon (F, 17, 3) and kinect (F, 17, 3) in camera mm, aspset_17j order, NaN where missing (head_top always NaN).
Usage: python keraal_calib.py <KERAAL group3 dir> <det2d cache> <out dir>
       python keraal_calib.py --check"""
import glob
import json
import os
import sys

import numpy as np
from scipy.optimize import least_squares
from scipy.spatial.transform import Rotation

import aspset

# aspset_17j joint -> (Kinect v2 joint, Vicon target). head_top has no Kinect counterpart -> NaN.
# Vicon targets: 0 R forearm, 1 L forearm, 2 R arm, 3 L arm, 4 chest, 5 R thigh, 6 L thigh, 7 R shoulder,
# 8 L shoulder, 9 R hand, 10 L hand, 11 R foot, 12 L foot, 13 hips, 14 head, 15 R tibia, 16 L tibia
MAP = {"right_ankle": (18, 15), "right_knee": (17, 5), "right_hip": (16, 13), "right_wrist": (10, 0),
       "right_elbow": (9, 2), "right_shoulder": (8, 7), "left_ankle": (14, 16), "left_knee": (13, 6),
       "left_hip": (12, 13), "left_wrist": (6, 1), "left_elbow": (5, 3), "left_shoulder": (4, 8),
       "head": (3, 14), "neck": (20, 4), "spine": (1, 4), "pelvis": (0, 13)}
JIDX = [aspset.JOINTS.index(j) for j in MAP]
KIN = [MAP[j][0] for j in MAP]
VIC = [MAP[j][1] for j in MAP]
FLIPK = np.array([-1.0, -1.0, 1.0])  # Kinect camera space (x left, y up) -> OpenCV axes
# COCO keypoint -> aspset_17j index, for 2D reprojection checks (shoulders, elbows, wrists, hips, knees, ankles)
COCO2ASP = {5: 11, 6: 5, 7: 10, 8: 4, 9: 9, 10: 3, 11: 8, 12: 2, 13: 7, 14: 1, 15: 6, 16: 0}
MAX_LAG = 15


def kinect_cam(K, t0):
    """(F, 25, 3) Kinect metres -> (F, 25, 3) camera mm (OpenCV axes), lost joints NaN."""
    X = (K + t0) * FLIPK * 1000.0
    X[(np.abs(K).sum(-1) == 0)] = np.nan
    return X


def project(X, k):
    fx, fy, cx, cy = k
    return np.stack([fx * X[..., 0] / X[..., 2] + cx, fy * X[..., 1] / X[..., 2] + cy], -1)


def fit_intrinsics(pairs):
    """pairs: list of (Kinect (N, 3) metres, uv (N, 2)) -> fx, fy, cx, cy, t0 (m)."""
    Xk = np.concatenate([p[0] for p in pairs]); uv = np.concatenate([p[1] for p in pairs])

    def res(v):
        return (project((Xk + v[4:]) * FLIPK, v[:4]) - uv).ravel()
    v = least_squares(res, [530, 530, 480, 270, 0, 0, 0], loss="soft_l1", f_scale=10.0).x
    return v[:4], v[4:]


def kabsch(A, B):
    """R, t minimising |R A + t - B| (no scale)."""
    ma, mb = A.mean(0), B.mean(0)
    U, _, Vt = np.linalg.svd((B - mb).T @ (A - ma))
    D = np.diag([1, 1, np.sign(np.linalg.det(U @ Vt))])
    R = U @ D @ Vt
    return R, mb - R @ ma


def fit_session(recs, conj, iters=30):
    """recs: list of (P (F, J, 3) Vicon target pos mm, Q (F, J, 3, 3) target rotations, C (F, J, 3) Kinect camera mm).
    Model C ≈ R (P + Q o_j) + t. Returns R, t, offsets (J, 3), per-pair residual mm."""
    P = np.concatenate([r[0] for r in recs]); Q = np.concatenate([r[1] for r in recs]); C = np.concatenate([r[2] for r in recs])
    if conj:
        Q = np.swapaxes(Q, -1, -2)
    ok = np.isfinite(P).all(-1) & np.isfinite(C).all(-1)
    o = np.zeros((P.shape[1], 3))
    keep = ok.copy()
    for it in range(iters):
        J = P + np.einsum("fjab,jb->fja", Q, o)
        R, t = kabsch(J[keep], C[keep])
        r = (C - t) @ R - P                                  # = R^T (C - t) - P, Vicon frame
        loc = np.einsum("fjba,fjb->fja", Q, r)               # Q^T r: offset estimate in target frame
        o = np.array([np.nanmedian(np.where(keep[:, j, None], loc[:, j], np.nan), 0) for j in range(P.shape[1])])
        if it == iters // 2:                                 # one robust pass: drop gross Kinect failures
            e = np.linalg.norm(R @ (P + np.einsum("fjab,jb->fja", Q, o))[..., None] + t[:, None] - C[..., None], axis=-2)[..., 0]
            keep = ok & (e < 3 * np.nanmedian(e[ok]))
    J = P + np.einsum("fjab,jb->fja", Q, o)
    e = np.linalg.norm(J @ R.T + t - C, axis=-1)
    return R, t, o, e[ok]


def load_rec(g3, key, k, t0):
    V = np.loadtxt(os.path.join(g3, "vicon", f"G3-Vicon-{key}.txt")).reshape(-1, 17, 7)[::2]
    Kr = np.loadtxt(os.path.join(g3, "kinect", f"G3-Kinect-{key}.txt")).reshape(-1, 25, 7)[..., :3]
    C = kinect_cam(Kr, t0)[:, KIN]
    P = V[:, VIC, :3].copy()
    P[np.abs(V[:, VIC, :3]).sum(-1) == 0] = np.nan
    q = V[:, VIC, 3:]
    qn = np.linalg.norm(q, axis=-1)
    Q = np.full(q.shape[:2] + (3, 3), np.nan)
    good = qn > 0.5
    Q[good] = Rotation.from_quat(q[good] / qn[good][:, None]).as_matrix()
    P[~good] = np.nan
    return P, Q, C


def lagged(P, Q, C, lag):
    """Shift Vicon by `lag` frames relative to Kinect and crop to the common length."""
    if lag >= 0:
        P, Q = P[lag:], Q[lag:]
    else:
        C = C[-lag:]
    n = min(len(P), len(C))
    return P[:n], Q[:n], C[:n]


def best_lag(P, Q, C, R, t, o):
    def err(l):
        p, q, c = lagged(P, Q, C, l)
        J = p + np.einsum("fjab,jb->fja", q, o)
        e = np.linalg.norm(J @ R.T + t - c, axis=-1)
        return np.nanmedian(e) if np.isfinite(e).sum() > 100 else np.inf
    return min(range(-MAX_LAG, MAX_LAG + 1), key=err)


def main(g3, cache, out):
    os.makedirs(os.path.join(out, "gt3d"), exist_ok=True)
    keys = sorted(os.path.basename(f)[9:-4] for f in glob.glob(os.path.join(g3, "vicon", "G3-Vicon-*.txt")))
    keys = [k for k in keys if os.path.exists(os.path.join(cache, f"G3-Anon-{k}.npz"))]
    # session = participant x exercise: P2's camera/Vicon geometry changes between exercises (one R, t per
    # participant leaves ~110 mm residual for P2, per exercise ~25-34 mm)
    part = {k: k.split("-")[1][:2] + "-" + k.split("-")[0] for k in keys}
    calib_set = set(keys[0::2])                              # even recordings fit, odd ones validate

    # 1. intrinsics from the calibration half (every 5th frame)
    pairs = []
    for k in sorted(calib_set):
        d = np.load(os.path.join(cache, f"G3-Anon-{k}.npz"))
        Kr = np.loadtxt(os.path.join(g3, "kinect", f"G3-Kinect-{k}.txt")).reshape(-1, 25, 7)[..., :3]
        n = min(len(Kr), len(d["kp"]))
        for c, a in COCO2ASP.items():
            kj = KIN[JIDX.index(a)]
            X, uv, cf = Kr[:n:5, kj], d["kp"][:n:5, c], d["conf"][:n:5, c]
            m = (cf > 0.5) & (X[:, 2] > 0.5)
            pairs.append((X[m], uv[m]))
    kin_k, t0 = fit_intrinsics(pairs)
    print(f"intrinsics fx {kin_k[0]:.1f} fy {kin_k[1]:.1f} cx {kin_k[2]:.1f} cy {kin_k[3]:.1f} t0 (m) {np.round(t0, 3)}", flush=True)

    # 2. Vicon -> camera per participant; quaternion convention chosen by residual
    data = {k: load_rec(g3, k, kin_k, t0) for k in keys}
    sessions, lags = {}, {}
    for p in sorted(set(part.values())):
        ks = [k for k in sorted(calib_set) if part[k] == p]
        best = None
        for conj in (False, True):
            R, t, o, e = fit_session([lagged(*data[k], 0) for k in ks], conj)
            if best is None or np.median(e) < best[0]:
                best = (np.median(e), conj, R, t, o)
        _, conj, R, t, o = best
        for rnd in range(2):                                 # refine per-recording lags, refit
            for k in ks:
                P, Q, C = data[k]
                lags[k] = best_lag(P, np.swapaxes(Q, -1, -2) if conj else Q, C, R, t, o)
            R, t, o, e = fit_session([lagged(*data[k], lags[k]) for k in ks], conj)
        sessions[p] = {"R": R, "t": t, "o": o, "conj": conj, "fit_median_mm": float(np.median(e))}
        print(f"{p}: quaternion {'conjugated' if conj else 'as given'}, fit residual median {np.median(e):.1f} mm, "
              f"offset norms (mm) {np.round(np.linalg.norm(o, axis=1)).astype(int).tolist()}", flush=True)

    # 3. apply to every recording, validate on the held-out half
    val = {"res3d": [], "naive3d": [], "rep_vicon": [], "rep_vicon_unb": [], "rep_kinect": [], "rep_kinect_unb": []}
    per_rec = {}
    for k in keys:
        s = sessions[part[k]]
        P, Q, C = data[k]
        Qc = np.swapaxes(Q, -1, -2) if s["conj"] else Q
        if k not in lags:
            lags[k] = best_lag(P, Qc, C, s["R"], s["t"], s["o"])
        p, q, c = lagged(P, Qc, C, lags[k])
        Jv = (p + np.einsum("fjab,jb->fja", q, s["o"])) @ s["R"].T + s["t"]
        e3 = np.linalg.norm(Jv - c, axis=-1)
        vic = np.full((len(Jv), 17, 3), np.nan); vic[:, JIDX] = Jv
        kin = np.full((len(c), 17, 3), np.nan); kin[:, JIDX] = c
        np.savez_compressed(os.path.join(out, "gt3d", f"{k}.npz"), vicon=vic.astype(np.float32),
                            kinect=kin.astype(np.float32), lag=lags[k])
        per_rec[k] = {"lag": int(lags[k]), "res3d_median_mm": float(np.nanmedian(e3)),
                      "vicon_missing": float(np.isnan(Jv).any((1, 2)).mean())}
        if k in calib_set:
            continue
        val["res3d"].append(np.nanmedian(e3))
        d = np.load(os.path.join(cache, f"G3-Anon-{k}.npz"))
        n = min(len(vic), len(d["kp"]))
        cocos = list(COCO2ASP); asp = [COCO2ASP[c] for c in cocos]
        uv, cf = d["kp"][:n, cocos], d["conf"][:n, cocos]
        for name, X in (("vicon", vic[:n, asp]), ("kinect", kin[:n, asp])):
            err = project(X, kin_k) - uv
            err[cf < 0.5] = np.nan
            val[f"rep_{name}"].append(np.nanmedian(np.linalg.norm(err, axis=-1)))
            unb = err - np.nanmean(err, axis=1, keepdims=True)   # ASPset-style: tolerate a per-frame constant offset
            val[f"rep_{name}_unb"].append(np.nanmedian(np.linalg.norm(unb, axis=-1)))
    summary = {k: float(np.nanmedian(v)) for k, v in val.items() if v}
    summary["n_validation_recordings"] = len(val["res3d"])
    print("validation (held-out recordings, medians):", json.dumps({k: round(v, 1) for k, v in summary.items()}), flush=True)
    json.dump({"intrinsics": {"fx": kin_k[0], "fy": kin_k[1], "cx": kin_k[2], "cy": kin_k[3], "t0_m": t0.tolist(),
                              "axes": "OpenCV camera: x right, y down, z forward; Kinect x,y negated"},
               "joint_map": {j: {"kinect": MAP[j][0], "vicon_target": MAP[j][1]} for j in MAP},
               "sessions": {p: {"R": s["R"].tolist(), "t_mm": s["t"].tolist(), "offsets_mm": s["o"].tolist(),
                                "quat_conjugated": bool(s["conj"]), "fit_median_mm": s["fit_median_mm"]}
                            for p, s in sessions.items()},
               "validation": summary, "recordings": per_rec, "calibration_set": sorted(calib_set)},
              open(os.path.join(out, "calib.json"), "w"), indent=1, default=float)


def _check():
    rng = np.random.default_rng(0)
    # session fit recovers R, t, offsets from synthetic targets
    F, J = 400, 5
    R0 = Rotation.from_rotvec(rng.normal(size=3)).as_matrix(); t0 = rng.normal(size=3) * 1000
    o0 = rng.normal(size=(J, 3)) * 80
    P = rng.normal(size=(F, J, 3)) * 300
    Q = Rotation.from_rotvec(rng.normal(size=(F * J, 3))).as_matrix().reshape(F, J, 3, 3)
    C = (P + np.einsum("fjab,jb->fja", Q, o0)) @ R0.T + t0 + rng.normal(size=(F, J, 3))
    R, t, o, e = fit_session([(P, Q, C)], False)
    assert np.allclose(R, R0, atol=1e-2) and np.allclose(o, o0, atol=2) and np.median(e) < 3, np.median(e)
    # intrinsics fit recovers a known camera
    X = rng.uniform([-0.5, -0.8, 2.5], [0.5, 0.8, 3.5], size=(500, 3))
    uv = project((X + [0.05, 0, 0]) * FLIPK, [536, 558, 468, 274])
    k, tt = fit_intrinsics([(X, uv)])
    assert np.allclose(k, [536, 558, 468, 274], atol=1) and np.allclose(tt, [0.05, 0, 0], atol=0.01), (k, tt)
    print("keraal_calib --check OK")


if __name__ == "__main__":
    if sys.argv[1] == "--check":
        _check()
    else:
        main(*sys.argv[1:4])
