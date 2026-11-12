"""Measure the problems of merging ASPset-510 (Vicon-like optical mocap, standing, 50 fps) with KERAAL Kinect skeletons.
Every number is computed from the data; AUDIT.md is written here (aggregates only, KERAAL is CC BY-NC-SA).
Usage: python audit.py        (needs E:/ASPset510_data, E:/KERAAL_data, E:/KERAAL_mocap3d/calib, g1a detections)
       python audit.py --check"""
import glob
import json
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, ".."))
import aspset
import keraal_calib as kc

ROOT = "E:/KERAAL_data/extracted"
CALIB = "E:/KERAAL_mocap3d/calib"
DET = "E:/KERAAL_mocap3d/g1a"
ASP = "E:/ASPset510_data/extracted/ASPset-510"
J = {n: i for i, n in enumerate(aspset.JOINTS)}
BONES = {"thigh": ("right_hip", "right_knee"), "shin": ("right_knee", "right_ankle"),
         "upper_arm": ("right_shoulder", "right_elbow"), "forearm": ("right_elbow", "right_wrist"),
         "hip_width": ("right_hip", "left_hip"), "shoulder_width": ("right_shoulder", "left_shoulder"),
         "pelvis_spine": ("pelvis", "spine"), "spine_neck": ("spine", "neck"), "neck_head": ("neck", "head")}


def kinect17(path):
    """Kinect v2 text file -> (F, 17, 3) camera mm, aspset_17j order, OpenCV axes; lost joints NaN, head_top NaN.
    Root-relative quantities do not depend on the depth->colour offset t0, so it is left out."""
    K = np.loadtxt(path).reshape(-1, 25, 7)[..., :3]
    X = np.full((len(K), 17, 3), np.nan)
    X[:, kc.JIDX] = kc.kinect_cam(K, np.zeros(3))[:, kc.KIN]
    return X


def bone_lengths(P):
    return {b: np.linalg.norm(P[:, J[a]] - P[:, J[c]], axis=-1) for b, (a, c) in BONES.items()}


def hip_angle(P):
    """Trunk-thigh angle (deg), mean of both sides: about 180 standing, about 90 seated."""
    out = []
    for h, k in (("right_hip", "right_knee"), ("left_hip", "left_knee")):
        u, v = P[:, J["neck"]] - P[:, J["pelvis"]], P[:, J[k]] - P[:, J[h]]
        c = (u * v).sum(-1) / (np.linalg.norm(u, axis=-1) * np.linalg.norm(v, axis=-1) + 1e-9)
        out.append(np.degrees(np.arccos(np.clip(c, -1, 1))))
    return np.nanmean(out, 0)


def quality(P):
    """Per recording: lost-frame share, bone-length CV, jitter (median |acceleration|, mm/frame^2), share of frames with a
    joint jumping > 100 mm in one frame."""
    lost = np.isnan(P[:, kc.JIDX]).any((1, 2))
    R = P - P[:, J["pelvis"]:J["pelvis"] + 1]
    bl = bone_lengths(P)
    cv = np.nanmedian([np.nanstd(v) / np.nanmean(v) for v in bl.values()])
    acc = np.linalg.norm(R[2:] - 2 * R[1:-1] + R[:-2], axis=-1)
    jump = (np.linalg.norm(R[1:] - R[:-1], axis=-1) > 100).any(1)
    return {"lost": lost.mean(), "bone_cv": cv, "jitter": np.nanmedian(acc), "jump": jump.mean()}


def kinect_files(group, limit=None):
    f = sorted(glob.glob(f"{ROOT}/{group}/kinect/*.txt"))
    return f if not limit or len(f) <= limit else list(np.random.default_rng(0).choice(f, limit, replace=False))


def fit_k(group, det_dir, n=60):
    """Pinhole fit Kinect joints <-> YOLO 2D on 480x360 video, as keraal_calib does for G3. Median reprojection px."""
    pairs, recs = [], []
    for det in sorted(glob.glob(f"{det_dir}/*.npz"))[:n]:
        key = os.path.basename(det)[:-4]
        kf = glob.glob(f"{ROOT}/{group}/kinect/*-Kinect-{key}.txt")
        if not kf:
            continue
        Kr = np.loadtxt(kf[0]).reshape(-1, 25, 7)[..., :3]
        d = np.load(det)
        m = min(len(Kr), len(d["kp"]))
        for c, a in kc.COCO2ASP.items():
            kj = kc.KIN[kc.JIDX.index(a)]
            X, uv, cf = Kr[:m:3, kj], d["kp"][:m:3, c], d["conf"][:m:3, c]
            ok = (cf > 0.5) & (X[:, 2] > 0.5)
            pairs.append((X[ok], uv[ok]))
    k, t0 = kc.fit_intrinsics(pairs)
    X = np.concatenate([p[0] for p in pairs]); uv = np.concatenate([p[1] for p in pairs])
    e = np.linalg.norm(kc.project((X + t0) * kc.FLIPK, k) - uv, axis=-1)
    return k, t0, float(np.median(e)), len(uv)


def main():
    rows, res = [], {}
    # ASPset: optical mocap ground truth, the definition the lifter learns first
    asp = []
    for subj, clip, cam in list(aspset.clip_views(ASP, "val"))[::3]:
        asp.append(aspset.load_view(ASP, "val", subj, clip, cam)["x3d"])
    A = np.concatenate(asp)
    src = {"ASPset (val)": [A]}
    # G3: Vicon (calibrated to camera, joint offsets fitted to the Kinect definition) and Kinect, same frames
    g3v, g3k = [], []
    for f in sorted(glob.glob(f"{CALIB}/gt3d/*.npz")):
        d = np.load(f)
        g3v.append(d["vicon"]), g3k.append(d["kinect"])
    src["G3 Vicon"] = g3v
    src["G3 Kinect"] = g3k
    for g, lim in (("group1A", None), ("group2A", None), ("group1B", 300), ("group2B", None)):
        src[f"{g[5:]} Kinect"] = [kinect17(f) for f in kinect_files(g, lim)]

    # 1. skeleton definition: median bone lengths (mm)
    res["bones"] = {}
    for name, recs in src.items():
        P = np.concatenate(recs)
        res["bones"][name] = {b: float(np.nanmedian(v)) for b, v in bone_lengths(P).items()}
    # 2. pose domain: trunk-thigh angle
    res["posture"] = {}
    for name, recs in src.items():
        a = hip_angle(np.concatenate(recs))
        res["posture"][name] = {"median": float(np.nanmedian(a)), "seated_share": float(np.nanmean(a[np.isfinite(a)] < 135))}
    # 3. Kinect quality per group
    res["quality"] = {}
    for name, recs in src.items():
        if name.startswith("ASPset"):
            continue
        q = [quality(P) for P in recs]
        res["quality"][name] = {k: float(np.nanmedian([x[k] for x in q])) for k in q[0]} | {"recordings": len(recs)}
    # 4. Kinect vs Vicon on G3: what Kinect-as-ground-truth costs (root-relative, mm)
    E = []
    for v, k in zip(g3v, g3k):
        rv, rk = v - v[:, J["pelvis"]:J["pelvis"] + 1], k - k[:, J["pelvis"]:J["pelvis"] + 1]
        E.append(np.linalg.norm(rv - rk, axis=-1))
    E = np.concatenate(E)
    res["kinect_vs_vicon_mm"] = {"mpjpe": float(np.nanmean(E[:, kc.JIDX])),
                                 "per_joint": {aspset.JOINTS[j]: round(float(np.nanmean(E[:, j])), 1) for j in kc.JIDX}}
    # 5. camera: 1A/2A video is 480x360, G3 960x540; fit a pinhole per group
    res["camera"] = {}
    for g, det in (("group1A", f"{DET}/det_clean"), ("group2A", f"{DET}/det_clean_group2A")):
        if glob.glob(f"{det}/*.npz"):
            k, t0, e, n = fit_k(g, det)
            res["camera"][g] = {"fx": float(k[0]), "fy": float(k[1]), "cx": float(k[2]), "cy": float(k[3]),
                                "t0_m": np.round(t0, 3).tolist(), "reproj_median_px": e, "points": n}
    g3 = json.load(open(f"{CALIB}/calib.json"))["intrinsics"]
    res["camera"]["group3 (960x540)"] = {k: g3[k] for k in ("fx", "fy", "cx", "cy")}
    json.dump(res, open(f"{DET}/audit.json", "w"), indent=1)
    write_md(res)


def write_md(res):
    L = ["# 합친 데이터셋 점검 (자동 생성) / Merge audit", "",
         "ASPset-510과 KERAAL Kinect 골격을 합칠 때의 문제를 데이터에서 직접 잰 값. `audit.py`가 만든다.", "",
         "## 1. 골격 정의: 뼈 길이 중앙값 (mm)", ""]
    names = list(res["bones"])
    L += ["| 뼈 | " + " | ".join(names) + " |", "|---|" + "---|" * len(names)]
    for b in BONES:
        L.append(f"| {b} | " + " | ".join(f"{res['bones'][n][b]:.0f}" for n in names) + " |")
    L += ["", "## 2. 자세: 몸통–넓적다리 각도", "", "| 출처 | 중앙값 (°) | 앉은 자세 비율 (<135°) |", "|---|---|---|"]
    L += [f"| {n} | {v['median']:.0f} | {v['seated_share']:.2f} |" for n, v in res["posture"].items()]
    L += ["", "## 3. Kinect 품질 (녹화별 중앙값)", "",
          "| 출처 | 녹화 | 관절 잃은 프레임 | 뼈 길이 변동 | 떨림 (mm/프레임²) | 100 mm 이상 튐 |", "|---|---|---|---|---|---|"]
    L += [f"| {n} | {v['recordings']} | {v['lost']:.3f} | {v['bone_cv']:.3f} | {v['jitter']:.1f} | {v['jump']:.3f} |"
          for n, v in res["quality"].items()]
    kv = res["kinect_vs_vicon_mm"]
    L += ["", f"## 4. G3에서 Kinect vs Vicon (골반 기준, mm): 평균 {kv['mpjpe']:.1f}", "",
          "| " + " | ".join(kv["per_joint"]) + " |", "|" + "---|" * len(kv["per_joint"]),
          "| " + " | ".join(f"{v:.0f}" for v in kv["per_joint"].values()) + " |"]
    L += ["", "## 5. 카메라", "", "| 그룹 | fx | fy | cx | cy | 재투영 중앙값 (px) |", "|---|---|---|---|---|---|"]
    for g, c in res["camera"].items():
        L.append(f"| {g} | {c['fx']:.0f} | {c['fy']:.0f} | {c['cx']:.0f} | {c['cy']:.0f} | {c.get('reproj_median_px', float('nan')):.1f} |")
    open(os.path.join(HERE, "AUDIT.md"), "w", encoding="utf-8").write("\n".join(L) + "\n")


def _check():
    P = np.zeros((5, 17, 3))
    P[:, J["neck"]] = [0, -500, 0]; P[:, J["right_knee"]] = [0, 450, 0]; P[:, J["left_knee"]] = [0, 450, 0]
    assert np.allclose(hip_angle(P), 180)
    P[:, J["right_knee"]] = [0, 0, 450]; P[:, J["left_knee"]] = [0, 0, 450]
    assert np.allclose(hip_angle(P), 90)
    q = quality(np.random.default_rng(0).normal(size=(50, 17, 3)) + np.arange(17)[None, :, None] * 1000)
    assert q["lost"] == 0 and q["jump"] == 0
    print("audit --check OK")


if __name__ == "__main__":
    _check() if sys.argv[1:] == ["--check"] else main()
