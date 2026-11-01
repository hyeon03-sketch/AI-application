"""YOLO11-pose 2D keypoints for every ASPset-510 video, on crops around the dataset's person boxes.
Usage: python detect2d.py <ASPset-510 root> <out dir> [--workers 3] [--weights yolo11x-pose.pt]
       python detect2d.py --check <ASPset-510 root> <out dir>   (one short clip, then sanity checks)
Output per view: <subj>-<clip>-<cam>.npz with kp (F,17,2) px in full frame (COCO order), conf (F,17), found (F,)."""
import argparse
import glob
import multiprocessing as mp
import os
import time

import cv2
import numpy as np

import aspset

CROP = 384  # px fed to the model per crop
PAD = 1.3   # crop side = PAD * longer box side


def crop_square(img, box):
    cx, cy = (box[0] + box[2]) / 2, (box[1] + box[3]) / 2
    side = PAD * max(box[2] - box[0], box[3] - box[1])
    x0, y0 = cx - side / 2, cy - side / 2
    s = CROP / side
    M = np.array([[s, 0, -x0 * s], [0, s, -y0 * s]])
    return cv2.warpAffine(img, M, (CROP, CROP), borderValue=(114, 114, 114)), x0, y0, s


def detect_view(model, video, boxes, batch=32):
    cap = cv2.VideoCapture(video)
    n = len(boxes)
    kp, conf, found = np.zeros((n, 17, 2)), np.zeros((n, 17)), np.zeros(n, bool)
    buf, meta = [], []

    def flush():
        res = model(buf, imgsz=CROP, verbose=False, half=True)
        for r, (fi, x0, y0, s) in zip(res, meta):
            if r.keypoints is None or len(r.boxes) == 0:
                continue
            b = r.boxes.xyxy.cpu().numpy()
            # the person nearest the crop centre (the dataset box is centred on the subject)
            d = np.hypot((b[:, 0] + b[:, 2]) / 2 - CROP / 2, (b[:, 1] + b[:, 3]) / 2 - CROP / 2)
            j = int(np.argmin(d - 1e-3 * r.boxes.conf.cpu().numpy()))
            kp[fi] = r.keypoints.xy[j].cpu().numpy() / s + [x0, y0]
            conf[fi] = r.keypoints.conf[j].cpu().numpy()
            found[fi] = True
        buf.clear(), meta.clear()

    for fi in range(n):
        ok, img = cap.read()
        if not ok:
            break
        c, x0, y0, s = crop_square(img, boxes[fi])
        buf.append(c), meta.append((fi, x0, y0, s))
        if len(buf) == batch:
            flush()
    if buf:
        flush()
    cap.release()
    return kp, conf, found


def worker(args):
    jobs, out_dir, weights, wid = args
    from ultralytics import YOLO
    model = YOLO(weights)
    t0 = time.time()
    for k, (root, split, subj, clip, cam) in enumerate(jobs):
        out = os.path.join(out_dir, f"{subj}-{clip}-{cam}.npz")
        if os.path.exists(out):
            continue
        boxes = aspset.read_boxes(os.path.join(root, aspset.part(split), "boxes", subj, f"{subj}-{clip}-{cam}.csv"))
        video = os.path.join(root, aspset.part(split), "videos", subj, f"{subj}-{clip}-{cam}.mkv")
        kp, conf, found = detect_view(model, video, boxes)
        np.savez_compressed(out + ".tmp.npz", kp=kp, conf=conf, found=found)
        os.replace(out + ".tmp.npz", out)
        print(f"[w{wid}] {k + 1}/{len(jobs)} {subj}-{clip}-{cam} frames {len(boxes)} found {found.mean():.3f} "
              f"elapsed {(time.time() - t0) / 60:.1f} min", flush=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("root"), ap.add_argument("out")
    ap.add_argument("--workers", type=int, default=3)
    ap.add_argument("--weights", default="yolo11x-pose.pt")
    ap.add_argument("--check", action="store_true")
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)
    jobs = [(a.root, sp, *v) for sp in ("test", "val", "train") for v in aspset.clip_views(a.root, sp)]
    if a.check:
        root, split, subj, clip, cam = min(jobs, key=lambda j: len(aspset.read_boxes(os.path.join(
            j[0], aspset.part(j[1]), "boxes", j[2], f"{j[2]}-{j[3]}-{j[4]}.csv"))))
        worker(([(root, split, subj, clip, cam)], a.out, a.weights, 0))
        d = np.load(os.path.join(a.out, f"{subj}-{clip}-{cam}.npz"))
        gt = aspset.load_view(root, split, subj, clip, cam)["uv"]
        # COCO -> aspset joints that exist in both (ankles, knees, hips, wrists, elbows, shoulders)
        coco = [16, 14, 12, 10, 8, 6, 15, 13, 11, 9, 7, 5]
        err = np.linalg.norm(d["kp"][:, coco] - gt[:, :12], axis=-1)[d["found"]]
        h = np.median(np.ptp(gt[:, :, 1], axis=1))
        print(f"detect2d --check: found {d['found'].mean():.3f}, median 2D error {np.median(err):.1f} px "
              f"= {np.median(err) / h:.3f} of body height")
        assert d["found"].mean() > 0.9 and np.median(err) / h < 0.05
        print("detect2d --check OK")
        return
    print(f"{len(jobs)} views, {a.workers} workers", flush=True)
    chunks = [jobs[i::a.workers] for i in range(a.workers)]
    with mp.get_context("spawn").Pool(a.workers) as pool:
        pool.map(worker, [(c, a.out, a.weights, i) for i, c in enumerate(chunks)])
    print("ALL DONE", flush=True)


if __name__ == "__main__":
    main()
