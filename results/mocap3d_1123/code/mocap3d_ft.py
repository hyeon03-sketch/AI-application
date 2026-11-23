"""Mocap3D (FlagTCN, 12.9M) retrained from the shared bundles: the km_train.py recipe (--flag --kweight, Kinect groups,
REHAB24-6) without the workstation's raw files.

  python mocap3d_ft.py train --data <public bundle> <KERAAL bundle> --out runs/m3d_test_P1 --fold P1 [--all] [--epochs 30]
  python mocap3d_ft.py infer --data <bundle> --in aspset_kp2d_coco.npz --ids aspset:test --flag 0 --ckpt best.pt --out pred.npz

Same as km_train.py: body-size (root) normalisation + confidence channel, definition flag (0 ASPset, 1 others),
Kinect targets weighted per joint, G3 repeated to match the ASPset frame count, AdamW lr 1e-3, decay 0.95^(60/epochs)
per epoch, 128-frame chunks, batch 64, flip augmentation, best epoch = lowest mean of the validation MPJPEs
(ASPset, KERAAL G3, REHAB24-6). Different from km_train.py: --epochs defaults to 30 instead of 120 (time on a laptop).
best.pt is a FlagTCN state dict in ASPset joint order: usable with demo_rehab.py --flag.
--all: deployment model, trains on the fold's train + test (all three participants), validates on the fold's val."""
import argparse
import json
import os
import sys
import time

import numpy as np
import torch

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "code_1118"))
import aspset                                                   # noqa: E402
import train_lift                                               # noqa: E402
from train_lift import COCO_FLIP, COCO_HIPS, TCN                # noqa: E402
from vp3d_ft import find, ids_of                                # noqa: E402

A2H = [16, 2, 1, 0, 8, 7, 6, 15, 14, 13, 12, 11, 10, 9, 5, 4, 3]   # H36M index <- ASPset index (build_share.py)
H2A = list(np.argsort(A2H))                                          # ASPset index <- H36M index
DEV = "mps" if torch.backends.mps.is_available() else ("cuda" if torch.cuda.is_available() else "cpu")


class FlagTCN(TCN):
    def __init__(self, in_joints, in_ch, flag=1.0, **kw):
        super().__init__(in_joints, in_ch + 1, **kw)
        self.in_ch, self.flag = in_ch + 1, flag

    def forward(self, x):
        if x.shape[-1] == self.in_ch - 1:
            x = torch.cat([x, torch.full_like(x[..., :1], self.flag)], -1)
        return super().forward(x)


def x_of(k):
    k = k.astype(np.float64)
    return np.concatenate([aspset.normalize_root(k[..., :2], COCO_HIPS), k[..., 2:3]], -1).astype(np.float32)


def load(dirs, item, definition, noisy):
    """-> [{id, x2d (T,17,5): x, y, conf, definition flag, noisy flag; y3d (T,17,3) metres, ASPset order, NaN kept}]"""
    d, ids = ids_of(dirs, item)
    K, G = np.load(find(dirs, f"{d}_kp2d_coco.npz")), np.load(find(dirs, f"{d}_gt3d.npz"))
    out = []
    for rid in ids:
        x = x_of(K[rid])
        y = (G[rid].astype(np.float32) / 1000)[:, H2A]
        y = y - y[:, aspset.PELVIS:aspset.PELVIS + 1]
        extra = np.stack([np.full(x.shape[:2], definition, np.float32), np.full(x.shape[:2], noisy, np.float32)], -1)
        out.append({"id": rid, "x2d": np.concatenate([x, extra], -1), "y3d": y})
    return out


@torch.no_grad()
def predict(model, x, flag):
    """x (T,17,3) normalised + conf -> (T,17,3) metres, ASPset order, pelvis at 0; flip test-time augmentation."""
    model.eval()
    x = np.concatenate([x, np.full(x.shape[:2] + (1,), flag, np.float32)], -1)
    half, T, out = model.rf // 2, len(x), []
    for s in range(0, T, 4000):
        e = min(s + 4000, T)
        xi = x[np.clip(np.arange(s - half, e + half), 0, T - 1)]
        xf = xi[:, COCO_FLIP].copy(); xf[..., 0] *= -1
        p = model(torch.from_numpy(xi)[None].to(DEV))[0].cpu().numpy()
        pf = model(torch.from_numpy(xf)[None].to(DEV))[0].cpu().numpy()
        pf[..., 0] *= -1
        out.append((p + pf[:, aspset.FLIP]) / 2)
    p = np.concatenate(out)
    return p - p[:, aspset.PELVIS:aspset.PELVIS + 1]


@torch.no_grad()
def val_mpjpe(model, seqs):
    """Mean joint error in mm without flip augmentation, NaN targets left out."""
    model.eval()
    half, tot, n = model.rf // 2, 0.0, 0
    for q in seqs:
        x = q["x2d"][..., :4]
        T = len(x)
        p = model(torch.from_numpy(x[np.clip(np.arange(-half, T + half), 0, T - 1)])[None].to(DEV))[0].cpu().numpy()
        p = p - p[:, aspset.PELVIS:aspset.PELVIS + 1]
        m = ~np.isnan(q["y3d"]).any(-1)
        tot += np.linalg.norm(p - np.nan_to_num(q["y3d"]), axis=-1)[m].sum(); n += m.sum()
    return float(tot / n * 1000)


def loss_fn(P, Y, noisy, w):
    m = (~torch.isnan(Y[..., 0])).float()
    W = torch.where(noisy[:, None, None] > 0.5, w[None, None], torch.ones_like(w)[None, None]) * m
    e = torch.linalg.norm(P - torch.nan_to_num(Y), dim=-1)
    return (e * W).sum() / W.sum().clamp(min=1)


def train(a):
    os.makedirs(a.out, exist_ok=True)
    f = f"keraal_g3:folds/test_{a.fold}"
    ktr = load(a.data, f + "/train", 1, 0) + (load(a.data, f + "/test", 1, 0) if a.all else [])
    kval = load(a.data, f + "/val", 1, 0)
    atr, aval = load(a.data, "aspset:train", 0, 0), load(a.data, "aspset:val", 0, 0)
    kin = load(a.data, "keraal_kinect:train", 1, 1)
    rtr, rval = load(a.data, "rehab24:train", 1, 0), load(a.data, "rehab24:val", 1, 0)
    nk, na = sum(len(q["y3d"]) for q in ktr), sum(len(q["y3d"]) for q in atr)
    rep = max(1, round(na / nk))                                  # keraal_share 0.5, as km_train.py
    tr = ktr * rep + atr + kin + rtr
    w = torch.tensor(np.asarray(ids_of(a.data, f + "/kinect_joint_loss_weight_h36m")[1], np.float32)[H2A]).to(DEV)
    print(f"G3 {nk} frames x{rep}, ASPset {na}, Kinect-target {sum(len(q['y3d']) for q in kin)}, REHAB24 "
          f"{sum(len(q['y3d']) for q in rtr)}; device {DEV}; weights {np.round(w.cpu().numpy(), 2).tolist()}", flush=True)
    json.dump(vars(a), open(os.path.join(a.out, "args.json"), "w"), indent=1)
    torch.manual_seed(a.seed)
    rng = np.random.default_rng(a.seed)
    model = FlagTCN(17, 3).to(DEV)
    print("parameters (M):", round(sum(p.numel() for p in model.parameters()) / 1e6, 1), "rf", model.rf, flush=True)
    opt = torch.optim.AdamW(model.parameters(), lr=a.lr, weight_decay=1e-4)
    sched = torch.optim.lr_scheduler.ExponentialLR(opt, 0.95 ** (60 / a.epochs))
    last, start, best, hist = os.path.join(a.out, "last.pt"), 0, float("inf"), []
    if os.path.exists(last):
        ck = torch.load(last, map_location=DEV, weights_only=False)
        model.load_state_dict(ck["model"]); opt.load_state_dict(ck["opt"]); sched.load_state_dict(ck["sched"])
        start, best, hist = ck["epoch"] + 1, ck["best"], ck["hist"]
        rng = np.random.default_rng(a.seed + start)
        print(f"continuing from epoch {start}", flush=True)
    for ep in range(start, a.epochs):
        t0, tot, cnt = time.time(), 0.0, 0
        model.train()
        for X, Y in train_lift.batches(tr, model.rf, 128, 64, "det", rng):
            X, Y = X.to(DEV), Y.to(DEV)
            loss = loss_fn(model(X[..., :4]), Y, X[:, 0, 0, 4], w)
            opt.zero_grad(); loss.backward(); opt.step()
            tot, cnt = tot + loss.item(), cnt + 1
            if a.max_batches and cnt >= a.max_batches:
                break
        sched.step()
        v = {"val_aspset": val_mpjpe(model, aval), "val_keraal": val_mpjpe(model, kval), "val_rehab24": val_mpjpe(model, rval)}
        score = float(np.mean(list(v.values())))
        mins = (time.time() - t0) / 60
        hist.append({"epoch": ep, "train_mm": round(tot / cnt * 1000, 2), **{k: round(x, 2) for k, x in v.items()},
                     "score": round(score, 2), "minutes": round(mins, 1)})
        if score < best:
            best = score
            torch.save(model.state_dict(), os.path.join(a.out, "best.pt"))
        torch.save({"model": model.state_dict(), "opt": opt.state_dict(), "sched": sched.state_dict(), "epoch": ep,
                    "best": best, "hist": hist}, last)
        json.dump(hist, open(os.path.join(a.out, "history.json"), "w"), indent=1)
        print(json.dumps(hist[-1]), flush=True)
    print("done. best score:", round(best, 1), flush=True)


def infer(a):
    model = FlagTCN(17, 3).to(DEV)
    model.load_state_dict({k: v.float() for k, v in torch.load(a.ckpt, map_location=DEV, weights_only=True).items()})
    K = np.load(find(a.data, a.inp))
    ids = ids_of(a.data, a.ids)[1] if a.ids else K.files
    pred = {rid: (predict(model, x_of(K[rid]), a.flag) * 1000)[:, A2H].astype(np.float32) for rid in ids}   # H36M order, mm
    np.savez_compressed(a.out, **pred)
    print(f"{len(pred)} recordings -> {a.out}", flush=True)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=("train", "infer"))
    ap.add_argument("--data", nargs="+", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--fold", default="P1")
    ap.add_argument("--all", action="store_true")
    ap.add_argument("--epochs", type=int, default=30)
    ap.add_argument("--lr", type=float, default=1e-3)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--max-batches", type=int, default=0)
    ap.add_argument("--in", dest="inp")
    ap.add_argument("--ids", default=None)
    ap.add_argument("--flag", type=float, default=1.0)
    ap.add_argument("--ckpt", default=None)
    a = ap.parse_args()
    train(a) if a.cmd == "train" else infer(a)
