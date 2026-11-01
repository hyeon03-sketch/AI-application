"""Pilot: single-camera 2D video -> 3D joints with the ASPset-trained lifter.
  python run_pilot.py sample                      # no download: bundled ASPset test sample -> MPJPE / PA-MPJPE
  python run_pilot.py video <my_video.mp4> [out]  # your own video -> 3D joints (npz), joint angles (csv), plot (png)
  python run_pilot.py aspset <ASPset root> <det2d dir>   # full ASPset-510 test split (after download + detect2d.py)
  python run_pilot.py --check                     # self-test of the sample path
3D output: 17 joints (aspset_17j order), mm, pelvis-relative, camera axes (x right, y down, z forward)."""
import csv
import json
import os
import sys

import numpy as np
import torch

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
import aspset  # noqa: E402
from keraal_eval import angles_from_points, lift  # noqa: E402
from train_lift import TCN, mpjpe, pa_mpjpe  # noqa: E402

WEIGHTS = os.path.join(HERE, "weights", "lifter_aspset_fp16.pt")
SAMPLE = os.path.join(HERE, "sample", "aspset_test_sample.npz")
DEV = "cuda" if torch.cuda.is_available() else "cpu"
BONES = [(0, 1), (1, 2), (3, 4), (4, 5), (6, 7), (7, 8), (9, 10), (10, 11), (2, 16), (8, 16), (16, 15), (15, 14),
         (14, 13), (13, 12), (14, 5), (14, 11)]


def load_model():
    model = TCN(17, 3).to(DEV)
    model.load_state_dict({k: v.float() for k, v in torch.load(WEIGHTS, map_location=DEV).items()})
    return model.eval()


def run_sample():
    model, s = load_model(), np.load(SAMPLE)
    keys = sorted({k.split("/")[0] for k in s.files})
    allp, allg = [], []
    for k in keys:
        kp, conf, found = s[f"{k}/kp"], s[f"{k}/conf"], s[f"{k}/found"]
        p, _ = lift(model, {"kp": kp, "conf": conf, "found": found, "wh": np.array([aspset.W, aspset.H])}, DEV, "root")
        p, g = p * 1000, s[f"{k}/gt3d_mm"]
        allp.append(p), allg.append(g)
        print(f"{k}: {len(g)} frames  MPJPE {mpjpe(p, g).mean():6.1f} mm  PA-MPJPE {pa_mpjpe(p.copy(), g).mean():6.1f} mm")
    p, g = np.concatenate(allp), np.concatenate(allg)
    res = {"mpjpe": float(mpjpe(p, g).mean()), "pa_mpjpe": float(pa_mpjpe(p.copy(), g).mean()), "frames": len(g)}
    print(f"ALL: {res['frames']} frames  MPJPE {res['mpjpe']:.1f} mm  PA-MPJPE {res['pa_mpjpe']:.1f} mm")
    return res


def detect_video(path):
    import cv2
    from ultralytics import YOLO
    yolo = YOLO("yolo11x-pose.pt")  # downloaded automatically on first use
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
    h, w = frames[0].shape[:2]
    n = len(frames)
    kp, conf, found = np.zeros((n, 17, 2)), np.zeros((n, 17)), np.zeros(n, bool)
    for s in range(0, n, 16):
        for i, r in enumerate(yolo(frames[s:s + 16], verbose=False)):
            if r.keypoints is None or len(r.boxes) == 0:
                continue
            b = r.boxes.xyxy.cpu().numpy()
            j = int(np.argmax((b[:, 2] - b[:, 0]) * (b[:, 3] - b[:, 1])))  # largest person
            kp[s + i], conf[s + i], found[s + i] = r.keypoints.xy[j].cpu().numpy(), r.keypoints.conf[j].cpu().numpy(), True
    return {"kp": kp, "conf": conf, "found": found, "wh": np.array([w, h])}, fps, frames[n // 2]


def run_video(path, out):
    os.makedirs(out, exist_ok=True)
    d, fps, mid = detect_video(path)
    if d["found"].mean() < 0.5:
        sys.exit(f"a person was found in only {d['found'].mean():.0%} of frames; use a video with one clearly visible person")
    p3d, kp = lift(load_model(), d, DEV, "root")
    p3d = p3d * 1000
    np.savez_compressed(os.path.join(out, "pose3d.npz"), joints_mm=p3d.astype(np.float32), names=np.array(aspset.JOINTS),
                        kp2d=kp.astype(np.float32), found=d["found"], fps=fps)
    ang = angles_from_points(p3d, "aspset")
    with open(os.path.join(out, "angles.csv"), "w", newline="") as f:
        wr = csv.writer(f)
        wr.writerow(["frame", "time_s"] + list(ang))
        for i in range(len(p3d)):
            wr.writerow([i, round(i / fps, 3)] + [round(float(ang[a][i]), 2) for a in ang])
    try:
        plot(p3d, mid, kp, os.path.join(out, "preview.png"))
    except ImportError:
        print("matplotlib not installed: skipped preview.png")
    print(f"{len(p3d)} frames, person found in {d['found'].mean():.1%}. Wrote {out}/pose3d.npz, angles.csv, preview.png")


def plot(p3d, img, kp, path):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    f = len(p3d) // 2
    fig = plt.figure(figsize=(10, 5))
    ax = fig.add_subplot(1, 2, 1)
    ax.imshow(img[..., ::-1]), ax.axis("off"), ax.set_title("input + 2D keypoints")
    ax.scatter(kp[f, :, 0], kp[f, :, 1], s=12, c="lime")
    ax = fig.add_subplot(1, 2, 2, projection="3d")
    P = p3d[f]
    for a, b in BONES:  # plot with y down -> z up
        ax.plot([P[a, 0], P[b, 0]], [P[a, 2], P[b, 2]], [-P[a, 1], -P[b, 1]], c="tab:blue")
    ax.set_title("3D (mm, pelvis = 0)"), ax.set_xlabel("x"), ax.set_ylabel("depth"), ax.set_zlabel("up")
    lim = np.abs(P).max()
    ax.set_xlim(-lim, lim), ax.set_ylim(-lim, lim), ax.set_zlim(-lim, lim)
    fig.savefig(path, dpi=100, bbox_inches="tight")


def run_aspset(root, det_dir):
    from train_lift import evaluate, load_split
    res, _ = evaluate(load_model(), load_split(root, "test", "det", det_dir), DEV, "det")
    print(json.dumps({k: round(res[k], 1) for k in ("mpjpe", "pa_mpjpe", "accel")}))


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "sample"
    if cmd == "sample":
        run_sample()
    elif cmd == "video":
        run_video(sys.argv[2], sys.argv[3] if len(sys.argv) > 3 else "pilot_out")
    elif cmd == "aspset":
        run_aspset(sys.argv[2], sys.argv[3])
    elif cmd == "--check":
        r = run_sample()
        assert r["frames"] > 500 and r["pa_mpjpe"] < 80, r  # full test split gives ~50 mm PA-MPJPE
        print("run_pilot --check OK")
    else:
        sys.exit(__doc__)
