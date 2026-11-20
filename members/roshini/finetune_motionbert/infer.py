"""2D keypoints -> 3D with MotionBERT (task sheet interface).

  python infer.py --in aspset_kp2d_h36m.npz --out aspset_pred3d.npz --mb MotionBERT --ckpt runs/seed0/best.pt
      --in : one array per recording, (T, 17, 3) = x px, y px, confidence, H36M 17-joint order
      --out: one array per recording, (T, 17, 3), mm, pelvis at 0, H36M order, same T
      --ids: optional splits.json "dataset:split" to keep only those recordings (e.g. aspset:test)
  Without --ckpt the original pretrained MotionBERT is used ("before")."""
import argparse
import json
import os

import numpy as np
import torch

import mb_common
from mb_common import load_motionbert, predict, scale_input

ap = argparse.ArgumentParser()
ap.add_argument("--in", dest="inp", required=True)
ap.add_argument("--out", required=True)
ap.add_argument("--mb", required=True, help="MotionBERT repository folder")
ap.add_argument("--ckpt", default=None, help="fine-tuned best.pt; leave out for the pretrained model")
ap.add_argument("--ids", default=None, help="dataset:split from splits.json next to --in, e.g. aspset:test")
ap.add_argument("--image-wh", nargs=2, type=int, default=None, help="only for --scaling screen")
ap.add_argument("--scaling", default="crop", choices=["crop", "screen"])
a = ap.parse_args()

mb_common.SCALING = a.scaling
dev = "cuda" if torch.cuda.is_available() else "cpu"
net = load_motionbert(a.mb, a.ckpt).to(dev).eval()
K = np.load(a.inp)
ids = K.files
if a.ids:
    d, split = a.ids.split(":")
    ids = json.load(open(os.path.join(os.path.dirname(os.path.abspath(a.inp)), "splits.json")))[d][split]
pred = {rid: predict(net, scale_input(K[rid], a.image_wh), dev).astype(np.float32) for rid in ids}
np.savez_compressed(a.out, **pred)
print(f"{len(pred)} recordings -> {a.out}")
