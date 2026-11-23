"""VideoPose3D before / after fine-tuning on the shared bundles (same interface as Roshini's MotionBERT scripts).

  python vp3d_ft.py train --data <bundle dir> [<bundle dir> ...] --out runs/seed0 \
        --train aspset:train rehab24:train --val aspset:val rehab24:val
  python vp3d_ft.py infer --data <bundle dir> --in aspset_kp2d_coco.npz --ids aspset:test --out pred.npz [--ckpt best.pt]

Conditions (Euijin's vp3d_finetune.py + team sheet): public checkpoint pretrained_h36m_detectron_coco.bin
(COCO-17 x, y in -> H36M-17 out, 243 frames), crop scaling (one square box per recording), AdamW lr 1e-4,
x0.95 per epoch, 20 epochs, 128-frame chunks, batch 64, flip augmentation, masked MPJPE loss, best epoch = lowest
validation MPJPE, seed 0. Prediction uses flip test-time augmentation, as in Euijin's script.
Targets: <dataset>_gt3d.npz, H36M order, mm -> metres, pelvis at 0, NaN joints masked.
dataset:split items: "aspset:train", "keraal_kinect:train", "keraal_g3:folds/test_P1/train" (nested with /)."""
import argparse
import json
import os
import sys
import time

import numpy as np
import torch

HERE = os.path.dirname(os.path.abspath(__file__))
VP3D = os.path.join(HERE, "..", "VideoPose3D")
CKPT = os.path.join(VP3D, "checkpoint", "pretrained_h36m_detectron_coco.bin")
COCO_FLIP = [0, 2, 1, 4, 3, 6, 5, 8, 7, 10, 9, 12, 11, 14, 13, 16, 15]
H36M_FLIP = [0, 4, 5, 6, 1, 2, 3, 7, 8, 9, 10, 14, 15, 16, 11, 12, 13]
RF = 243


def build_model(ckpt=None):
    sys.path.insert(0, VP3D)
    from common.model import TemporalModel
    tm = TemporalModel(17, 2, 17, filter_widths=[3, 3, 3, 3, 3], causal=False, dropout=0.25, channels=1024)
    sd = torch.load(CKPT, map_location="cpu", weights_only=False)["model_pos"]
    tm.load_state_dict({k.replace("module.", "", 1): v for k, v in sd.items()}, strict=True)
    if ckpt:
        tm.load_state_dict(torch.load(ckpt, map_location="cpu", weights_only=True), strict=True)
    return tm


def crop_scale(xy):
    lo, hi = xy.reshape(-1, 2).min(0), xy.reshape(-1, 2).max(0)
    s = max(float((hi - lo).max()), 1e-6)
    return ((xy - (lo + hi - s) / 2) / s - 0.5) * 2


def find(dirs, name):
    for d in dirs:
        if os.path.exists(os.path.join(d, name)):
            return os.path.join(d, name)
    raise FileNotFoundError(name)


def ids_of(dirs, item):
    d, split = item.split(":")
    for dd in dirs:
        sp = json.load(open(os.path.join(dd, "splits.json")))
        if d in sp:
            node = sp[d]
            for part in split.split("/"):
                node = node[part]
            return d, list(node)
    raise KeyError(item)


def load(dirs, items, weights=None):
    """-> list of {id, x2d (T,17,2) crop-scaled, y3d (T,17,3) metres with NaN, w (17,) per-joint loss weight}."""
    seqs = []
    for item in items:
        d, ids = ids_of(dirs, item)
        K, G = np.load(find(dirs, f"{d}_kp2d_coco.npz")), np.load(find(dirs, f"{d}_gt3d.npz"))
        w = np.ones(17, np.float32) if (weights is None or d != "keraal_kinect") else np.asarray(weights, np.float32)
        for rid in ids:
            y = G[rid].astype(np.float32) / 1000
            seqs.append({"id": rid, "x2d": crop_scale(K[rid][..., :2].astype(np.float64)).astype(np.float32),
                         "y3d": y - y[:, :1], "w": w})
    return seqs


def batches(seqs, chunk, bs, rng):
    items = [(i, s) for i, q in enumerate(seqs) for s in range(0, len(q["y3d"]), chunk)]
    rng.shuffle(items)
    half = RF // 2
    for b in range(0, len(items), bs):
        X, Y, W = [], [], []
        for i, s in items[b:b + bs]:
            q = seqs[i]
            n = len(q["y3d"])
            e = min(s + chunk, n)
            x, y = q["x2d"][np.clip(np.arange(s - half, e + half), 0, n - 1)], q["y3d"][s:e]
            if rng.random() < 0.5:
                x, y = x[:, COCO_FLIP] * np.array([-1, 1], np.float32), y[:, H36M_FLIP] * np.array([-1, 1, 1], np.float32)
            if e - s < chunk:
                p = chunk - (e - s)
                x = np.concatenate([x, np.repeat(x[-1:], p, 0)])
                y = np.concatenate([y, np.full((p, 17, 3), np.nan, np.float32)])
            X.append(x), Y.append(y), W.append(q["w"])
        yield torch.from_numpy(np.stack(X)), torch.from_numpy(np.stack(Y)), torch.from_numpy(np.stack(W))


def masked_mpjpe(P, Y, W):
    m = ~torch.isnan(Y).any(-1)
    d = torch.linalg.norm(P - torch.nan_to_num(Y), dim=-1) * W[:, None, :] * m
    return d.sum() / (W[:, None, :] * m).sum().clamp(min=1)


@torch.no_grad()
def predict(model, x2d, dev, tta=True):
    """(T,17,2) scaled -> (T,17,3) metres, pelvis at 0. Long recordings are processed in pieces of 2000 frames."""
    model.eval()
    half, T, out = RF // 2, len(x2d), []
    for s in range(0, T, 2000):
        e = min(s + 2000, T)
        xi = np.ascontiguousarray(x2d[np.clip(np.arange(s - half, e + half), 0, T - 1)])
        p = model(torch.from_numpy(xi)[None].to(dev))[0].cpu().numpy()
        if tta:
            xf = np.ascontiguousarray(xi[:, COCO_FLIP] * np.array([-1, 1], np.float32))
            pf = model(torch.from_numpy(xf)[None].to(dev))[0].cpu().numpy()
            p = (p + pf[:, H36M_FLIP] * np.array([-1, 1, 1], np.float32)) / 2
        out.append(p)
    p = np.concatenate(out)
    return p - p[:, :1]


def val_mpjpe(model, seqs, dev):
    tot = n = 0.0
    for q in seqs:
        p = predict(model, q["x2d"], dev, tta=False)
        m = ~np.isnan(q["y3d"]).any(-1)
        m[:, 10] = False                                    # head top left out, as compute_metrics.py
        tot += np.linalg.norm(p - np.nan_to_num(q["y3d"]), axis=-1)[m].sum(); n += m.sum()
    return tot / n * 1000


def train(a):
    dev = "mps" if torch.backends.mps.is_available() else ("cuda" if torch.cuda.is_available() else "cpu")
    os.makedirs(a.out, exist_ok=True)
    kw = None
    if a.kinect_weights:
        d, ids = a.kinect_weights.split(":")[0], a.kinect_weights.split(":")[1]
        kw = ids_of(a.data, f"{d}:{ids}")[1]
    tr, va = load(a.data, a.train, kw), load(a.data, a.val)
    print(f"train {len(tr)} recordings ({sum(len(q['y3d']) for q in tr)} frames), val {len(va)}, device {dev}", flush=True)
    torch.manual_seed(a.seed)
    rng = np.random.default_rng(a.seed)
    model = build_model().to(dev)
    print("parameters (M):", round(sum(p.numel() for p in model.parameters()) / 1e6, 1), flush=True)
    opt = torch.optim.AdamW(model.parameters(), lr=a.lr, weight_decay=1e-4)
    sched = torch.optim.lr_scheduler.ExponentialLR(opt, a.lr_decay)
    last = os.path.join(a.out, "last.pt")
    if os.path.exists(last):
        ck = torch.load(last, map_location=dev, weights_only=False)
        model.load_state_dict(ck["model"]); opt.load_state_dict(ck["opt"]); sched.load_state_dict(ck["sched"])
        start, best, hist = ck["epoch"] + 1, ck["best"], ck["hist"]
        rng = np.random.default_rng(a.seed + start)
        print(f"continuing from epoch {start}, best {best:.1f} mm", flush=True)
    else:
        start, best = 0, float("inf")
        b = val_mpjpe(model, va, dev)
        hist = [{"epoch": "before", "val_mpjpe_mm": round(float(b), 2)}]
        print(f"before fine-tuning: val MPJPE {b:.1f} mm", flush=True)
    for ep in range(start, a.epochs):
        t0, tot, cnt = time.time(), 0.0, 0
        model.train()
        for X, Y, W in batches(tr, a.chunk, a.bs, rng):
            X, Y, W = X.to(dev), Y.to(dev), W.to(dev)
            loss = masked_mpjpe(model(X), Y, W)
            opt.zero_grad(); loss.backward(); opt.step()
            tot, cnt = tot + loss.item(), cnt + 1
            if a.max_batches and cnt >= a.max_batches:
                break
        sched.step()
        v = float(val_mpjpe(model, va, dev))
        mins = (time.time() - t0) / 60
        hist.append({"epoch": ep, "train_mpjpe_mm": round(tot / cnt * 1000, 2), "val_mpjpe_mm": round(v, 2), "minutes": round(mins, 1)})
        if v < best:
            best = v
            torch.save(model.state_dict(), os.path.join(a.out, "best.pt"))
        torch.save({"model": model.state_dict(), "opt": opt.state_dict(), "sched": sched.state_dict(), "epoch": ep,
                    "best": best, "hist": hist}, last)
        json.dump(hist, open(os.path.join(a.out, "history.json"), "w"), indent=1)
        print(f"epoch {ep:2d} | train {tot / cnt * 1000:6.1f} mm | val {v:6.1f} mm | best {best:6.1f} | {mins:.1f} min", flush=True)
    print("done. best val MPJPE:", round(best, 1), "mm", flush=True)


def infer(a):
    dev = "mps" if torch.backends.mps.is_available() else ("cuda" if torch.cuda.is_available() else "cpu")
    model = build_model(a.ckpt).to(dev)
    K = np.load(find(a.data, a.inp))
    ids = ids_of(a.data, a.ids)[1] if a.ids else K.files
    pred = {rid: (predict(model, crop_scale(K[rid][..., :2].astype(np.float64)).astype(np.float32), dev) * 1000).astype(np.float32)
            for rid in ids}
    np.savez_compressed(a.out, **pred)
    print(f"{len(pred)} recordings -> {a.out}", flush=True)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=("train", "infer"))
    ap.add_argument("--data", nargs="+", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--train", nargs="+", default=["aspset:train", "rehab24:train"])
    ap.add_argument("--val", nargs="+", default=["aspset:val", "rehab24:val"])
    ap.add_argument("--kinect-weights", default=None, help="e.g. keraal_g3:folds/test_P1/kinect_joint_loss_weight_h36m")
    ap.add_argument("--epochs", type=int, default=20)
    ap.add_argument("--lr", type=float, default=1e-4)
    ap.add_argument("--lr-decay", type=float, default=0.95)
    ap.add_argument("--chunk", type=int, default=128)
    ap.add_argument("--bs", type=int, default=64)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--max-batches", type=int, default=0, help="speed test only")
    ap.add_argument("--in", dest="inp")
    ap.add_argument("--ids", default=None)
    ap.add_argument("--ckpt", default=None)
    a = ap.parse_args()
    train(a) if a.cmd == "train" else infer(a)
