"""RQ3: does the ASPset-trained lifter track rehab joint angles on KERAAL G3, against Vicon?
Mapping-free metric: per-recording Pearson r (and mean-centred RMSE) of joint-angle time series.
Sources: lifted 3D (ours), raw 2D keypoint angles (control), Kinect 3D (depth-sensor baseline).
Usage: python keraal_eval.py detect <KERAAL group3 dir> <cache dir>
       python keraal_eval.py eval <KERAAL group3 dir> <cache dir> <lifter run dir (det input)> <out json>
       python keraal_eval.py --check   (synthetic tests of the angle code)
KERAAL is CC BY-NC-SA: outputs here are aggregates only; keep caches outside the repo."""
import glob
import json
import os
import sys

import cv2
import numpy as np

STD_MIN = 5.0     # deg; skip (recording, angle) pairs where the Vicon angle barely moves
MAX_LAG = 30      # video frames (1 s) searched for sync, same search for every source
SOURCES = ("kinect", "ours_3d", "raw_2d")

# (name, vicon (proximal, distal) segment ids, kinect (a, b, c), coco (a, b, c), aspset (a, b, c))
# angle at b between a-b and c-b; "shoulder" uses the trunk instead of a (see trunk_angle)
ANGLES = [
    ("R_elbow", (2, 0), (8, 9, 10), (6, 8, 10), (5, 4, 3)),
    ("L_elbow", (3, 1), (4, 5, 6), (5, 7, 9), (11, 10, 9)),
    ("R_knee", (5, 15), (16, 17, 18), (12, 14, 16), (2, 1, 0)),
    ("L_knee", (6, 16), (12, 13, 14), (11, 13, 15), (8, 7, 6)),
    ("R_shoulder", (4, 2), (8, 9, None), (6, 8, None), (5, 4, None)),
    ("L_shoulder", (4, 3), (4, 5, None), (5, 7, None), (11, 10, None)),
]


def joint_angle(a, b, c):
    u, v = a - b, c - b
    cos = (u * v).sum(-1) / (np.linalg.norm(u, axis=-1) * np.linalg.norm(v, axis=-1) + 1e-9)
    return 180 - np.degrees(np.arccos(np.clip(cos, -1, 1)))  # 0 = straight limb


def trunk_angle(sh, el, top, bottom):
    """Angle between the upper arm and the downward trunk axis (0 = arm hanging)."""
    u, v = el - sh, bottom - top
    cos = (u * v).sum(-1) / (np.linalg.norm(u, axis=-1) * np.linalg.norm(v, axis=-1) + 1e-9)
    return np.degrees(np.arccos(np.clip(cos, -1, 1)))


def quat_rel_angle(q1, q2):
    """Rotation angle between two orientations (quaternions x y z w), degrees."""
    d = np.abs((q1 * q2).sum(-1) / (np.linalg.norm(q1, axis=-1) * np.linalg.norm(q2, axis=-1) + 1e-12))
    return np.degrees(2 * np.arccos(np.clip(d, 0, 1)))


def angles_from_points(P, kind):
    """P (F, J, 2|3). kind in kinect/coco/aspset."""
    col = {"kinect": 2, "coco": 3, "aspset": 4}[kind]
    out = {}
    for row in ANGLES:
        a, b, c = row[col]
        if c is not None:
            out[row[0]] = joint_angle(P[:, a], P[:, b], P[:, c])
        else:
            if kind == "kinect":
                top, bottom = P[:, 20], P[:, 0]
            elif kind == "coco":
                top, bottom = (P[:, 5] + P[:, 6]) / 2, (P[:, 11] + P[:, 12]) / 2
            else:
                top, bottom = P[:, 14], P[:, 16]
            out[row[0]] = trunk_angle(P[:, a], P[:, b], top, bottom)
    return out


def vicon_angles(V):
    """V (F, 17, 7) x y z qx qy qz qw; frames with a zero target are NaN."""
    bad = (np.abs(V[..., :3]).sum(-1) == 0).any(1)
    out = {}
    for name, (p, d), *_ in ANGLES:
        a = quat_rel_angle(V[:, p, 3:], V[:, d, 3:])
        a[bad] = np.nan
        out[name] = a
    return out


def detect(g3, cache):
    from ultralytics import YOLO
    os.makedirs(cache, exist_ok=True)
    model = YOLO("yolo11x-pose.pt")
    vids = sorted(glob.glob(os.path.join(g3, "videos", "*.avi")))
    for k, vid in enumerate(vids):
        out = os.path.join(cache, os.path.basename(vid)[:-4] + ".npz")
        if os.path.exists(out):
            continue
        cap = cv2.VideoCapture(vid)
        frames = []
        while True:
            ok, img = cap.read()
            if not ok:
                break
            frames.append(img)
        h, w = frames[0].shape[:2]
        kp, conf, found = np.zeros((len(frames), 17, 2)), np.zeros((len(frames), 17)), np.zeros(len(frames), bool)
        for s in range(0, len(frames), 32):
            for i, r in enumerate(model(frames[s:s + 32], imgsz=960, verbose=False)):
                if r.keypoints is None or len(r.boxes) == 0:
                    continue
                b = r.boxes.xyxy.cpu().numpy()
                j = int(np.argmax((b[:, 2] - b[:, 0]) * (b[:, 3] - b[:, 1])))  # largest person
                kp[s + i], conf[s + i], found[s + i] = r.keypoints.xy[j].cpu().numpy(), r.keypoints.conf[j].cpu().numpy(), True
        np.savez_compressed(out, kp=kp, conf=conf, found=found, wh=np.array([w, h]))
        print(f"{k + 1}/{len(vids)} {os.path.basename(vid)} frames {len(frames)} found {found.mean():.3f}", flush=True)


def lift(model, d, dev, norm):
    import torch
    import aspset
    kp, ok = d["kp"].copy(), d["found"]
    idx = np.arange(len(kp))
    for j in range(17):
        for c in range(2):
            kp[:, j, c] = np.interp(idx, idx[ok], kp[ok, j, c])
    w, h = d["wh"]
    x2d = kp / w * 2 - np.array([1, h / w]) if norm == "screen" else aspset.normalize_root(kp, (11, 12))
    x = np.concatenate([x2d, (d["conf"] * ok[:, None])[..., None]], -1).astype(np.float32)
    half = model.rf // 2
    xi = x[np.clip(np.arange(-half, len(x) + half), 0, len(x) - 1)]
    from train_lift import COCO_FLIP
    xf = xi[:, COCO_FLIP].copy()  # flip test-time augmentation, same as the ASPset evaluation
    xf[..., 0] *= -1
    with torch.no_grad():
        p = model(torch.from_numpy(xi)[None].to(dev))[0].cpu().numpy()
        pf = model(torch.from_numpy(xf)[None].to(dev))[0].cpu().numpy()
    pf[..., 0] *= -1
    p = (p + pf[:, aspset.FLIP]) / 2
    return p - p[:, aspset.PELVIS:aspset.PELVIS + 1], kp


def corr(a, b):
    m = np.isfinite(a) & np.isfinite(b)
    if m.sum() < 30 or a[m].std() < 1e-6 or b[m].std() < 1e-6:
        return np.nan, np.nan
    r = np.corrcoef(a[m], b[m])[0, 1]
    rmse = np.sqrt(np.mean(((a[m] - a[m].mean()) - (b[m] - b[m].mean())) ** 2))
    return r, rmse


def shift(x, lag):
    """Shift a series by `lag` frames (positive = later), NaN-padded."""
    y = np.full_like(x, np.nan)
    if lag >= 0:
        y[lag:] = x[:len(x) - lag]
    else:
        y[:lag] = x[-lag:]
    return y


def evaluate(g3, cache, run, out_json):
    import torch
    from train_lift import TCN
    dev = "cuda" if torch.cuda.is_available() else "cpu"
    model = TCN(17, 3).to(dev)
    model.load_state_dict(torch.load(os.path.join(run, "best.pt"), map_location=dev))
    model.eval()
    norm = json.load(open(os.path.join(run, "args.json"))).get("norm", "screen")
    rows = []
    for vfile in sorted(glob.glob(os.path.join(g3, "vicon", "*.txt"))):
        key = os.path.basename(vfile).replace("G3-Vicon-", "")[:-4]
        det = os.path.join(cache, "G3-Anon-" + key + ".npz")
        kin = os.path.join(g3, "kinect", "G3-Kinect-" + key + ".txt")
        if not (os.path.exists(det) and os.path.exists(kin)):
            continue
        d = np.load(det)
        if d["found"].mean() < 0.5:
            continue
        V = np.loadtxt(vfile).reshape(-1, 17, 7)[::2]          # 60 fps -> 30 fps
        K = np.loadtxt(kin).reshape(-1, 25, 7)[..., :3]
        K[(np.abs(K).sum(-1) == 0).any(1)] = np.nan  # Kinect frames with a lost joint
        p3d, kp2d = lift(model, d, dev, norm)
        n = min(len(V), len(K), len(p3d))
        src = {"vicon": vicon_angles(V[:n]), "kinect": angles_from_points(K[:n], "kinect"),
               "ours_3d": angles_from_points(p3d[:n], "aspset"), "raw_2d": angles_from_points(kp2d[:n], "coco")}
        moving = [a for a in src["vicon"] if np.nanstd(src["vicon"][a]) >= STD_MIN]
        if not moving:
            continue
        # the same sync search for every source: one lag per (recording, source), maximising its mean r
        lags = {}
        for s in SOURCES:
            score = {l: np.nanmean([corr(shift(src[s][a], l), src["vicon"][a])[0] for a in moving])
                     for l in range(-MAX_LAG, MAX_LAG + 1)}
            lags[s] = max(score, key=lambda l: -2 if np.isnan(score[l]) else score[l])
        ex, part, label = key.split("-")[0], key.split("-")[1][:2], key.split("-")[3]
        for a in moving:
            g = src["vicon"][a]
            row = {"rec": key, "exercise": ex, "participant": part, "label": label, "angle": a,
                   "vicon_std": float(np.nanstd(g))}
            for s in SOURCES:
                row[s + "_r"], row[s + "_rmse"] = (float(v) for v in corr(shift(src[s][a], lags[s]), g))
                row[s + "_r0"] = float(corr(src[s][a], g)[0])
                row[s + "_lag"] = lags[s]
            rows.append(row)
    summary = summarise(rows)
    json.dump({"summary": summary, "rows": rows}, open(out_json, "w"), indent=1)
    print(json.dumps(summary, indent=1))


def summarise(rows):
    out = {"n_pairs": len(rows), "n_recordings": len({r["rec"] for r in rows})}
    for grp, keyf in (("all", lambda r: "all"), ("angle", lambda r: r["angle"]), ("exercise", lambda r: r["exercise"]),
                      ("participant", lambda r: r["participant"]), ("label", lambda r: r["label"][0])):
        g = {}
        for r in rows:
            g.setdefault(keyf(r), []).append(r)
        out[grp] = {k: {"n": len(v), **{f"{s}_{m}": round(float(np.nanmedian([x[f"{s}_{m}"] for x in v])), 3)
                                           for s in SOURCES for m in ("r", "r0", "rmse")}}
                    for k, v in sorted(g.items())}
    # paired comparison ours_3d vs raw_2d / kinect (fraction of pairs where ours has higher r)
    for other in ("raw_2d", "kinect"):
        diff = np.array([r["ours_3d_r"] - r[other + "_r"] for r in rows])
        diff = diff[np.isfinite(diff)]
        out[f"ours_minus_{other}_r"] = {"median": round(float(np.median(diff)), 3),
                                        "frac_ours_better": round(float((diff > 0).mean()), 3), "n": int(len(diff))}
    return out


def _check():
    rng = np.random.default_rng(0)
    # a bent elbow at 90 deg -> flexion 90
    assert np.isclose(joint_angle(np.array([[0, 1, 0.]]), np.zeros((1, 3)), np.array([[1, 0, 0.]])), 90)
    assert np.isclose(joint_angle(np.array([[0, 1, 0.]]), np.zeros((1, 3)), np.array([[0, -1, 0.]])), 0, atol=0.01)
    # quaternion: rotation by t about z
    t = np.radians(np.linspace(0, 120, 50))
    q1 = np.tile([0, 0, 0, 1.], (50, 1))
    q2 = np.stack([np.zeros(50), np.zeros(50), np.sin(t / 2), np.cos(t / 2)], 1)
    assert np.allclose(quat_rel_angle(q1, q2), np.degrees(t), atol=0.01)
    x = rng.normal(size=200).cumsum()
    assert np.isclose(corr(x, 2 * x + 5)[0], 1) and np.isnan(shift(x, 3)[:3]).all() and shift(x, 3)[3] == x[0]
    print("keraal_eval --check OK")


if __name__ == "__main__":
    if sys.argv[1] == "--check":
        _check()
    elif sys.argv[1] == "detect":
        detect(*sys.argv[2:4])
    elif sys.argv[1] == "eval":
        evaluate(*sys.argv[2:6])
