"""Build the bundled pilot sample from ASPset-510 (CC0): a few test views with YOLO 2D detections and GT 3D.
Also writes the fp16 copy of the ASPset-only lifter weights.
Usage: python make_sample.py <ASPset-510 root> <ASPset det2d dir> <lifter run dir>"""
import os
import sys

import numpy as np
import torch

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
import aspset  # noqa: E402

N_VIEWS, MAX_FRAMES = 4, 300


def main(root, det_dir, run):
    views = list(aspset.clip_views(root, "test"))[::15][:N_VIEWS]
    out = {}
    for subj, clip, cam in views:
        d = np.load(os.path.join(det_dir, f"{subj}-{clip}-{cam}.npz"))
        v = aspset.load_view(root, "test", subj, clip, cam)
        n = min(MAX_FRAMES, len(v["x3d"]))
        key = f"{subj}-{clip}-{cam}"
        out[f"{key}/kp"] = d["kp"][:n].astype(np.float32)
        out[f"{key}/conf"] = d["conf"][:n].astype(np.float32)
        out[f"{key}/found"] = d["found"][:n]
        out[f"{key}/gt3d_mm"] = v["x3d"][:n].astype(np.float32)
        print(key, n, "frames")
    os.makedirs(os.path.join(HERE, "sample"), exist_ok=True)
    np.savez_compressed(os.path.join(HERE, "sample", "aspset_test_sample.npz"), **out)
    sd = torch.load(os.path.join(run, "best.pt"), map_location="cpu")
    os.makedirs(os.path.join(HERE, "weights"), exist_ok=True)
    torch.save({k: v.half() if v.is_floating_point() else v for k, v in sd.items()},
               os.path.join(HERE, "weights", "lifter_aspset_fp16.pt"))


if __name__ == "__main__":
    main(*sys.argv[1:4])
