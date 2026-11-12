"""Rehab mini model: one ordinary camera video -> 2D keypoints -> 3D skeleton -> joint angles -> exercise readout.
  python demo_rehab.py <video> <out dir> --weights <best.pt> [--clean] [--squeeze] [--flag] [--fps 15]
    --clean    remove a burned-in orange Kinect skeleton (KERAAL 1A/1B/2A/2B videos)
    --squeeze  the frame is a 16:9 image squeezed to 4:3 (KERAAL 480x360 videos): stretch x by 4/3
    --flag     the weights are a km_train.py --flag model (output in the KERAAL/Kinect skeleton definition)
  python demo_rehab.py --check
Outputs: pose3d.npz (F, 17, 3) mm pelvis-relative camera axes, angles.csv, summary.json (range of motion and repetitions
per angle), demo.mp4 (video + 2D | 3D skeleton | angle trace). Videos below 20 fps are lifted at 2x (the model saw 30 fps)."""
import argparse
import csv
import json
import os
import sys

import cv2
import numpy as np
import torch

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, ".."))
sys.path.insert(0, os.path.join(HERE, "..", "patients_1a"))
import aspset
from keraal_eval import angles_from_points
from train_lift import COCO_FLIP, COCO_HIPS, TCN

BONES = [(0, 1), (1, 2), (3, 4), (4, 5), (6, 7), (7, 8), (9, 10), (10, 11), (2, 16), (8, 16), (16, 15), (15, 14),
         (14, 13), (14, 5), (14, 11)]
COCO_BONES = [(5, 7), (7, 9), (6, 8), (8, 10), (5, 6), (11, 12), (5, 11), (6, 12), (11, 13), (13, 15), (12, 14), (14, 16)]
SHOWN = ("R_elbow", "L_elbow", "R_knee", "L_knee", "R_shoulder", "L_shoulder")


def detect(path, clean):
    import g1a
    from ultralytics import YOLO
    yolo = YOLO(g1a.YOLO if os.path.exists(g1a.YOLO) else "yolo11x-pose.pt")
    cap = cv2.VideoCapture(path)
    fps = cap.get(cv2.CAP_PROP_FPS) or 30
    frames = []
    while True:
        ok, img = cap.read()
        if not ok:
            break
        frames.append(img)
    if not frames:
        sys.exit(f"could not read frames from {path}")
    inp = [g1a.clean(f) for f in frames] if clean else frames
    boxes, kps, confs = [], [], []
    for s in range(0, len(inp), 16):
        for r in yolo(inp[s:s + 16], imgsz=640, verbose=False):
            if r.keypoints is None or len(r.boxes) == 0:
                boxes.append(np.zeros((0, 4))), kps.append(np.zeros((0, 17, 2))), confs.append(np.zeros((0, 17)))
                continue
            boxes.append(r.boxes.xyxy.cpu().numpy()), kps.append(r.keypoints.xy.cpu().numpy()), confs.append(r.keypoints.conf.cpu().numpy())
    pick = g1a.pick_person(boxes, g1a.overlay_centre(frames) if clean else None)
    kp, conf, found = np.zeros((len(inp), 17, 2)), np.zeros((len(inp), 17)), pick >= 0
    for i in np.flatnonzero(found):
        kp[i], conf[i] = kps[i][pick[i]], confs[i][pick[i]]
    return frames, fps, kp, conf, found


def resample(x, k):
    idx = np.arange(len(x)); t = np.arange(k * (len(x) - 1) + 1) / k
    flat = x.reshape(len(x), -1)
    return np.stack([np.interp(t, idx, flat[:, c]) for c in range(flat.shape[1])], 1).reshape(len(t), *x.shape[1:])


def lift(model, kp, conf, found, fps, squeeze, dev):
    kp, idx = kp.copy(), np.arange(len(kp))
    for j in range(17):
        for c in range(2):
            kp[:, j, c] = np.interp(idx, idx[found], kp[found, j, c])
    conf = conf * found[:, None]
    k = 2 if fps < 20 else 1
    k2 = kp * np.array([4 / 3 if squeeze else 1, 1])
    k2, c2 = resample(k2, k), resample(conf, k)
    x = np.concatenate([aspset.normalize_root(k2, COCO_HIPS), c2[..., None]], -1).astype(np.float32)
    half = model.rf // 2
    xi = x[np.clip(np.arange(-half, len(x) + half), 0, len(x) - 1)]
    xf = xi[:, COCO_FLIP].copy()
    xf[..., 0] *= -1
    with torch.no_grad():
        p = model(torch.from_numpy(xi)[None].to(dev))[0].cpu().numpy()
        pf = model(torch.from_numpy(xf)[None].to(dev))[0].cpu().numpy()
    pf[..., 0] *= -1
    p = (p + pf[:, aspset.FLIP]) / 2
    return ((p - p[:, aspset.PELVIS:aspset.PELVIS + 1]) * 1000)[::k], kp


def repetitions(a, fps, prom=15.0):
    """Peaks of a 1 s-smoothed angle curve, 1 s apart, standing out by max(`prom`, 30% of the range of motion) degrees
    (so jitter on a held pose is not counted)."""
    from scipy.signal import find_peaks, savgol_filter
    a = np.nan_to_num(a, nan=float(np.nanmedian(a)))
    w = max(5, int(fps) | 1)
    s = savgol_filter(a, w, 2) if len(a) > w else a
    prom = max(prom, 0.3 * float(np.percentile(a, 95) - np.percentile(a, 5)))
    peaks, _ = find_peaks(s, prominence=prom, distance=max(1, int(fps)))
    return peaks


def summarise(ang, fps):
    out = {}
    for n in SHOWN:
        a = ang[n]
        pk = repetitions(a, fps)
        out[n] = {"min_deg": round(float(np.nanpercentile(a, 5)), 1), "max_deg": round(float(np.nanpercentile(a, 95)), 1),
                  "range_of_motion_deg": round(float(np.nanpercentile(a, 95) - np.nanpercentile(a, 5)), 1),
                  "repetitions": int(len(pk)), "peak_frames": pk.tolist()}
    main = max(out, key=lambda n: out[n]["range_of_motion_deg"])
    return {"main_angle": main, "frames": len(ang[main]), "fps": fps, "angles": out}


def render(frames, kp, conf, P, ang, summ, path, fps):
    h, w = frames[0].shape[:2]
    S = h                                                    # 3D panel and plot panel are h x h
    main = summ["main_angle"]
    a = ang[main]
    lo, hi = np.nanmin(a) - 5, np.nanmax(a) + 5
    vw = cv2.VideoWriter(path, cv2.VideoWriter_fourcc(*"mp4v"), fps, (w + 2 * S, h))
    scale = 0.38 * S / max(1.0, np.nanpercentile(np.abs(P[..., :2]), 99))
    for i, img in enumerate(frames):
        left = img.copy()
        for a_, b_ in COCO_BONES:
            if conf[i, a_] > 0.3 and conf[i, b_] > 0.3:
                cv2.line(left, tuple(int(v) for v in kp[i, a_]), tuple(int(v) for v in kp[i, b_]), (80, 220, 80), 2)
        mid = np.full((S, S, 3), 255, np.uint8)
        th = np.radians(60 + 25 * np.sin(i / 40))                # swinging near side-on so depth (seated knees) is visible
        R = np.array([[np.cos(th), 0, np.sin(th)], [0, 1, 0], [-np.sin(th), 0, np.cos(th)]])
        q = P[i] @ R.T
        uv = (q[:, :2] * scale + [S / 2, S / 2]).astype(int)
        for a_, b_ in BONES:
            cv2.line(mid, tuple(uv[a_]), tuple(uv[b_]), (200, 90, 30), 3)
        cv2.putText(mid, "3D (rotating view)", (10, 25), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 0), 1)
        right = np.full((S, S, 3), 255, np.uint8)
        xs = np.linspace(10, S - 10, len(a)).astype(int)
        ys = (S - 40 - (np.nan_to_num(a, nan=lo) - lo) / (hi - lo) * (S - 80)).astype(int)
        cv2.polylines(right, [np.stack([xs, ys], 1)], False, (60, 60, 60), 1)
        for p_ in summ["angles"][main]["peak_frames"]:
            cv2.circle(right, (xs[p_], ys[p_]), 4, (0, 0, 220), -1)
        cv2.line(right, (xs[i], 30), (xs[i], S - 30), (0, 150, 255), 1)
        done = sum(1 for p_ in summ["angles"][main]["peak_frames"] if p_ <= i)
        cv2.putText(right, f"{main}: {a[i]:.0f} deg", (10, 25), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 0), 1)
        cv2.putText(right, f"reps {done}/{summ['angles'][main]['repetitions']}  ROM {summ['angles'][main]['range_of_motion_deg']:.0f} deg",
                    (10, S - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 0, 0), 1)
        vw.write(np.hstack([left, mid, right]))
    vw.release()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("video"), ap.add_argument("out")
    ap.add_argument("--weights", required=True)
    ap.add_argument("--clean", action="store_true"), ap.add_argument("--squeeze", action="store_true")
    ap.add_argument("--flag", action="store_true")
    ap.add_argument("--fps", type=float, help="true frame rate when the file header is wrong (KERAAL 1A/1B/2A/2B: 15)")
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)
    dev = "cuda" if torch.cuda.is_available() else "cpu"
    if a.flag:
        from km_train import FlagTCN
        model = FlagTCN(17, 3)
    else:
        model = TCN(17, 3)
    model.load_state_dict({k: v.float() for k, v in torch.load(a.weights, map_location=dev).items()})
    model = model.to(dev).eval()
    frames, fps, kp, conf, found = detect(a.video, a.clean)
    fps = a.fps or fps
    if found.mean() < 0.5:
        sys.exit(f"a person was found in only {found.mean():.0%} of frames")
    P, kpf = lift(model, kp, conf, found, fps, a.squeeze, dev)
    ang = angles_from_points(P, "aspset")
    summ = summarise(ang, fps)
    np.savez_compressed(os.path.join(a.out, "pose3d.npz"), joints_mm=P.astype(np.float32), names=np.array(aspset.JOINTS), fps=fps)
    with open(os.path.join(a.out, "angles.csv"), "w", newline="") as f:
        wr = csv.writer(f)
        wr.writerow(["frame", "time_s"] + list(ang))
        for i in range(len(P)):
            wr.writerow([i, round(i / fps, 3)] + [round(float(ang[n][i]), 2) for n in ang])
    json.dump(summ, open(os.path.join(a.out, "summary.json"), "w"), indent=1)
    render(frames, kpf, conf, P, ang, summ, os.path.join(a.out, "demo.mp4"), fps)
    m = summ["angles"][summ["main_angle"]]
    print(f"{len(P)} frames at {fps:.0f} fps; main angle {summ['main_angle']}: {m['repetitions']} repetitions, "
          f"range of motion {m['range_of_motion_deg']} deg. Wrote {a.out}")


def _check():
    fps = 15
    t = np.arange(150) / fps
    a = 60 + 40 * np.sin(2 * np.pi * t / 2.0)                   # 5 cycles of 2 s
    assert len(repetitions(a, fps)) == 5, repetitions(a, fps)
    assert len(repetitions(np.full(150, 60.0), fps)) == 0
    assert resample(np.arange(3.0)[:, None], 2).ravel().tolist() == [0, .5, 1, 1.5, 2]
    s = summarise({n: a for n in SHOWN}, fps)
    assert abs(s["angles"]["R_knee"]["range_of_motion_deg"] - 79) < 2
    print("demo_rehab --check OK")


if __name__ == "__main__":
    _check() if sys.argv[1:] == ["--check"] else main()
