"""Shared parts of the MotionBERT fine-tuning: model loading, input scaling, clips, loss, whole-recording prediction."""
import json
import os
import sys
from functools import partial

import numpy as np
import torch

L, STRIDE = 243, 81          # clip length (MotionBERT's maxlen) and step between clips
SCALING = "crop"             # "crop" (team decision) or "screen" (x/w*2-1, y/w*2-h/w)


def load_motionbert(mb_dir, ckpt=None):
    """MotionBERT (DSTformer, 42.5M parameters) with the official H36M fine-tuned weights,
    or with our fine-tuned weights if `ckpt` (a best.pt state dict) is given."""
    sys.path.insert(0, mb_dir)
    from lib.model.DSTformer import DSTformer
    m = DSTformer(dim_in=3, dim_out=3, dim_feat=512, dim_rep=512, depth=5, num_heads=8, mlp_ratio=2,
                  norm_layer=partial(torch.nn.LayerNorm, eps=1e-6), maxlen=L, num_joints=17)
    if ckpt:
        m.load_state_dict(torch.load(ckpt, map_location="cpu", weights_only=True), strict=True)
    else:
        sd = torch.load(os.path.join(mb_dir, "checkpoint/pose3d/FT_MB_release_MB_ft_h36m/best_epoch.bin"),
                        map_location="cpu", weights_only=True)["model_pos"]
        m.load_state_dict({k.replace("module.", "", 1): v for k, v in sd.items()}, strict=True)
    return m


def screen_scale(x, w, h):
    out = x.copy(); out[..., 0] = x[..., 0] / w * 2 - 1; out[..., 1] = x[..., 1] / w * 2 - h / w; return out


def crop_scale(x):
    """One square box around all 2D joints of the whole recording, stretched to [-1, 1]. Confidence is kept."""
    lo, hi = x[..., :2].reshape(-1, 2).min(0), x[..., :2].reshape(-1, 2).max(0)
    s = (hi - lo).max()
    out = x.copy(); out[..., :2] = ((x[..., :2] - (lo + hi - s) / 2) / s - 0.5) * 2
    return out


def scale_input(x, image_wh=None):
    """(T, 17, 3) pixels + confidence -> MotionBERT input. image_wh is only needed for screen scaling."""
    return crop_scale(x) if SCALING == "crop" else screen_scale(x, *image_wh)


def image_size(sp, dataset, rid):
    if dataset == "rehab24":
        return (1920, 1080) if rid.endswith("c17") else (1080, 1920)
    return sp[dataset]["image_size_wh"]


def make_clips(x, y):
    """243-frame clips every 81 frames (last clip ends at the last frame). Short recordings repeat their last frame.
    Returns (x, y, frame_mask) per clip; frame_mask is False on the repeated frames."""
    T = len(x)
    starts = list(range(0, T - L + 1, STRIDE)) if T >= L else [0]
    if T >= L and starts[-1] != T - L:
        starts.append(T - L)
    out = []
    for s in starts:
        idx = np.arange(s, s + L); mask = idx < T; idx = np.minimum(idx, T - 1)
        out.append((x[idx], y[idx], mask))
    return out


def build(data_dir, sets):
    """sets: list of "dataset:split", e.g. ["aspset:train", "rehab24:train"].
    Reads <dataset>_kp2d_h36m.npz (2D) and <dataset>_gt3d.npz (3D, mm), ids from splits.json[dataset][split].
    Returns X (N,243,17,3), Y (N,243,17,3) in metres with NaN set to 0, M (N,243) frame mask, J (N,243,17) joint mask."""
    sp = json.load(open(os.path.join(data_dir, "splits.json")))
    X, Y, M = [], [], []
    for item in sets:
        d, split = item.split(":")
        K = np.load(os.path.join(data_dir, f"{d}_kp2d_h36m.npz")); G = np.load(os.path.join(data_dir, f"{d}_gt3d.npz"))
        ids = sp[d][split]
        for rid in ids:
            xx = scale_input(K[rid], None if SCALING == "crop" else image_size(sp, d, rid))
            for cx, cy, cm in make_clips(xx, G[rid] / 1000.0):
                X.append(cx); Y.append(cy); M.append(cm)
    X, Y, M = np.stack(X).astype(np.float32), np.stack(Y).astype(np.float32), np.stack(M)
    J = ~np.isnan(Y).any(-1)            # joints with a valid 3D target (KERAAL Vicon has NaN for hidden joints)
    Y = np.nan_to_num(Y)
    return X, Y, M, J


def masked_losses(pred, gt, fmask, jmask):
    """MotionBERT's loss (MB_ft_h36m.yaml): MPJPE + 0.5 * scale-aligned MPJPE + 20 * velocity error.
    Padded frames (fmask) and joints without a target (jmask) are left out. Returns (loss, mpjpe in metres)."""
    w = fmask.float()[..., None] * jmask.float()                       # (B, T, 17)
    n = w.sum().clamp(min=1)
    pos = (torch.norm(pred - gt, dim=-1) * w).sum() / n
    s = (gt * pred * w[..., None]).sum((-1, -2), keepdim=True) / \
        (pred ** 2 * w[..., None]).sum((-1, -2), keepdim=True).clamp(min=1e-8)
    scale = (torch.norm(s * pred - gt, dim=-1) * w).sum() / n
    vw = w[:, 1:] * w[:, :-1]
    dv = (pred[:, 1:] - pred[:, :-1]) - (gt[:, 1:] - gt[:, :-1])
    vel = (torch.norm(dv, dim=-1) * vw).sum() / vw.sum().clamp(min=1)
    return pos + 0.5 * scale + 20 * vel, pos


@torch.no_grad()
def predict(net, kp, dev):
    """One whole recording: (T,17,3) scaled 2D -> (T,17,3) 3D in mm, pelvis at 0, H36M order.
    243-frame windows every 81 frames; overlapping predictions are averaged."""
    T = len(kp)
    starts = list(range(0, max(T - L, 0) + 1, STRIDE))
    if T > L and starts[-1] != T - L:
        starts.append(T - L)
    out, cnt = np.zeros((T, 17, 3)), np.zeros(T)
    for b in range(0, len(starts), 8):
        idx = [np.arange(s, s + L) for s in starts[b:b + 8]]
        x = np.stack([kp[np.minimum(i, T - 1)] for i in idx])
        p = net(torch.from_numpy(x.astype(np.float32)).to(dev)).float()
        p = (p - p[:, :, :1]).cpu().numpy()
        for i, pi in zip(idx, p):
            real = i < T
            out[i[real]] += pi[real]; cnt[i[real]] += 1
    return out / cnt[:, None, None] * 1000
