"""2D->3D lifting on ASPset-510 with a VideoPose3D-style temporal conv net.
Usage: python train_lift.py <ASPset-510 root> <run dir> --input {gt,det} [--det-dir DIR] [--epochs 60]
       python train_lift.py --check <ASPset-510 root> <run dir>   (tiny run on a few clips)
Model selection uses val only; test is evaluated once with the best-val checkpoint."""
import argparse
import json
import os
import time

import numpy as np
import torch
import torch.nn as nn

import aspset

COCO_FLIP = [0, 2, 1, 4, 3, 6, 5, 8, 7, 10, 9, 12, 11, 14, 13, 16, 15]


class TCN(nn.Module):
    """Temporal conv net; receptive field = prod(widths). Input (B, T, J, C) -> output (B, T - rf + 1, 17, 3)."""

    def __init__(self, in_joints, in_ch, widths=(3, 3, 3, 3), ch=1024, drop=0.25):
        super().__init__()
        self.rf = int(np.prod(widths))
        self.expand = nn.Sequential(nn.Conv1d(in_joints * in_ch, ch, widths[0], bias=False), nn.BatchNorm1d(ch),
                                    nn.ReLU(), nn.Dropout(drop))
        self.blocks, self.pads = nn.ModuleList(), []
        d = widths[0]
        for w in widths[1:]:
            self.pads.append((w - 1) * d // 2)
            self.blocks.append(nn.Sequential(
                nn.Conv1d(ch, ch, w, dilation=d, bias=False), nn.BatchNorm1d(ch), nn.ReLU(), nn.Dropout(drop),
                nn.Conv1d(ch, ch, 1, bias=False), nn.BatchNorm1d(ch), nn.ReLU(), nn.Dropout(drop)))
            d *= w
        self.head = nn.Conv1d(ch, 17 * 3, 1)

    def forward(self, x):
        B, T = x.shape[:2]
        x = self.expand(x.reshape(B, T, -1).transpose(1, 2))
        for pad, blk in zip(self.pads, self.blocks):
            x = x[..., pad:x.shape[-1] - pad] + blk(x)
        return self.head(x).transpose(1, 2).reshape(B, -1, 17, 3)


COCO_HIPS, ASPSET_HIPS = (11, 12), (2, 8)


def norm_2d(uv, norm, hips):
    return aspset.normalize_2d(uv) if norm == "screen" else aspset.normalize_root(uv, hips)


def load_split(root, split, inp, det_dir, limit=None, norm="root"):
    seqs = []
    for k, (subj, clip, cam) in enumerate(aspset.clip_views(root, split)):
        if limit and k >= limit:
            break
        v = aspset.load_view(root, split, subj, clip, cam)
        if inp == "gt":
            x2d = norm_2d(v["uv"], norm, ASPSET_HIPS)
        else:
            d = np.load(os.path.join(det_dir, f"{subj}-{clip}-{cam}.npz"))
            kp, ok = d["kp"].copy(), d["found"]
            if not ok.any():
                continue
            idx = np.arange(len(kp))  # fill frames with no detection by linear interpolation
            for j in range(17):
                for c in range(2):
                    kp[:, j, c] = np.interp(idx, idx[ok], kp[ok, j, c])
            x2d = np.concatenate([norm_2d(kp, norm, COCO_HIPS), (d["conf"] * ok[:, None])[..., None]], -1)
        seqs.append({"id": f"{subj}-{clip}-{cam}", "x2d": x2d.astype(np.float32),
                     "y3d": (v["x3d"] / 1000).astype(np.float32)})
    return seqs


def flip(x2d, y3d, inp):
    x2d, y3d = x2d.copy(), y3d.copy()
    x2d[..., 0] *= -1
    y3d[..., 0] *= -1
    return x2d[:, COCO_FLIP if inp == "det" else aspset.FLIP], y3d[:, aspset.FLIP]


def batches(seqs, rf, chunk, bs, inp, rng):
    """Random chunks of `chunk` output frames, padded by edge replication for the receptive field."""
    items = [(i, s) for i, q in enumerate(seqs) for s in range(0, len(q["y3d"]), chunk)]
    rng.shuffle(items)
    half = rf // 2
    for b in range(0, len(items), bs):
        X, Y = [], []
        for i, s in items[b:b + bs]:
            q = seqs[i]
            n = len(q["y3d"])
            e = min(s + chunk, n)
            idx = np.clip(np.arange(s - half, e + half), 0, n - 1)
            x, y = q["x2d"][idx], q["y3d"][s:e]
            if rng.random() < 0.5:
                x, y = flip(x, y, inp)
            if e - s < chunk:  # pad short chunks; padded targets are masked out
                p = chunk - (e - s)
                x = np.concatenate([x, np.repeat(x[-1:], p, 0)])
                y = np.concatenate([y, np.full((p, 17, 3), np.nan, np.float32)])
            X.append(x), Y.append(y)
        yield torch.from_numpy(np.stack(X)), torch.from_numpy(np.stack(Y))


def mpjpe(p, g):
    return np.linalg.norm(p - g, axis=-1).mean(-1)


def pa_mpjpe(p, g):
    """Per-frame Procrustes alignment (rotation, scale, translation) before MPJPE."""
    mp_, mg = p.mean(1, keepdims=True), g.mean(1, keepdims=True)
    p0, g0 = p - mp_, g - mg
    U, S, Vt = np.linalg.svd(np.einsum("fji,fjk->fik", p0, g0))
    sign = np.sign(np.linalg.det(np.einsum("fij,fjk->fik", U, Vt)))
    S[:, -1] *= sign
    U[:, :, -1] *= sign[:, None]
    R = np.einsum("fij,fjk->fik", U, Vt)
    s = S.sum(1) / (p0 ** 2).sum((1, 2))
    return mpjpe(s[:, None, None] * np.einsum("fji,fik->fjk", p0, R) + mg, g)


@torch.no_grad()
def evaluate(model, seqs, dev, inp, tta=True):
    model.eval()
    half = model.rf // 2
    per = {"mpjpe": [], "pa_mpjpe": [], "accel": [], "joint": []}
    preds = {}
    for q in seqs:
        n = len(q["y3d"])
        idx = np.clip(np.arange(-half, n + half), 0, n - 1)
        x = torch.from_numpy(q["x2d"][idx])[None].to(dev)
        p = model(x)[0].cpu().numpy()
        if tta:
            xf, _ = flip(q["x2d"][idx], q["y3d"], inp)
            pf = model(torch.from_numpy(xf)[None].to(dev))[0].cpu().numpy()
            pf[..., 0] *= -1
            p = (p + pf[:, aspset.FLIP]) / 2
        p -= p[:, aspset.PELVIS:aspset.PELVIS + 1]
        g = q["y3d"]
        p, g = p * 1000, g * 1000
        preds[q["id"]] = p.astype(np.float32)
        per["mpjpe"].append(mpjpe(p, g))
        per["pa_mpjpe"].append(pa_mpjpe(p, g))
        per["accel"].append(np.linalg.norm(np.diff(p, 2, 0) - np.diff(g, 2, 0), axis=-1).mean(-1))
        per["joint"].append(np.linalg.norm(p - g, axis=-1))
    out = {k: float(np.concatenate(v).mean()) for k, v in per.items() if k != "joint"}
    out["per_joint"] = dict(zip(aspset.JOINTS, np.concatenate(per["joint"]).mean(0).round(1).tolist()))
    out["per_clip_mpjpe"] = {q["id"]: float(m.mean()) for q, m in zip(seqs, per["mpjpe"])}
    return out, preds


def mean_pose_baseline(train, test):
    mu = np.concatenate([q["y3d"] for q in train]).mean(0) * 1000
    g = np.concatenate([q["y3d"] for q in test]) * 1000
    p = np.broadcast_to(mu, g.shape)
    return {"mpjpe": float(mpjpe(p, g).mean()), "pa_mpjpe": float(pa_mpjpe(p.copy(), g).mean())}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("root"), ap.add_argument("run")
    ap.add_argument("--input", choices=["gt", "det"], default="gt")
    ap.add_argument("--det-dir")
    ap.add_argument("--epochs", type=int, default=60)
    ap.add_argument("--lr", type=float, default=1e-3)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--norm", choices=["root", "screen"], default="root")
    ap.add_argument("--train-subjects", type=int, help="learning curve: keep N random train subjects (seeded)")
    ap.add_argument("--check", action="store_true")
    a = ap.parse_args()
    os.makedirs(a.run, exist_ok=True)
    json.dump(vars(a), open(os.path.join(a.run, "args.json"), "w"), indent=1)
    torch.manual_seed(a.seed)
    rng = np.random.default_rng(a.seed)
    dev = "cuda" if torch.cuda.is_available() else "cpu"
    lim = 6 if a.check else None
    if a.check:
        a.epochs = 400  # 6 views = 1 batch per epoch
    train = load_split(a.root, "train", a.input, a.det_dir, lim, a.norm)
    if a.train_subjects:
        subs = sorted({q["id"].split("-")[0] for q in train})
        keep = set(rng.choice(subs, a.train_subjects, replace=False))
        train = [q for q in train if q["id"].split("-")[0] in keep]
        print(f"train subjects kept: {sorted(keep)}", flush=True)
    val = load_split(a.root, "val", a.input, a.det_dir, lim, a.norm)
    print(f"train views {len(train)} frames {sum(len(q['y3d']) for q in train)} | val views {len(val)}", flush=True)
    in_ch = train[0]["x2d"].shape[-1]
    model = TCN(17, in_ch).to(dev)
    opt = torch.optim.AdamW(model.parameters(), lr=a.lr, weight_decay=1e-4)
    sched = torch.optim.lr_scheduler.ExponentialLR(opt, 0.95 ** (60 / a.epochs))  # same total decay as 60 epochs at 0.95
    log, best = [], (1e9, -1)
    t0 = time.time()
    for ep in range(a.epochs):
        model.train()
        tot, cnt = 0.0, 0
        for X, Y in batches(train, model.rf, 128, 64, a.input, rng):
            X, Y = X.to(dev), Y.to(dev)
            P = model(X)
            m = ~torch.isnan(Y[..., 0, 0])
            loss = torch.linalg.norm(P[m] - Y[m], dim=-1).mean()
            opt.zero_grad()
            loss.backward()
            opt.step()
            tot, cnt = tot + loss.item() * m.sum().item(), cnt + m.sum().item()
        sched.step()
        v, _ = evaluate(model, val, dev, a.input)
        log.append({"epoch": ep + 1, "train_mpjpe": tot / cnt * 1000, "val_mpjpe": v["mpjpe"],
                    "val_pa_mpjpe": v["pa_mpjpe"], "min": (time.time() - t0) / 60})
        print(json.dumps(log[-1]), flush=True)
        if v["mpjpe"] < best[0] or a.check:  # --check keeps the last epoch for the overfit test
            best = (v["mpjpe"], ep + 1)
            torch.save(model.state_dict(), os.path.join(a.run, "best.pt"))
    json.dump(log, open(os.path.join(a.run, "log.json"), "w"), indent=1)
    model.load_state_dict(torch.load(os.path.join(a.run, "best.pt")))
    test = load_split(a.root, "test", a.input, a.det_dir, lim, a.norm)
    res, preds = evaluate(model, test, dev, a.input)
    vres, _ = evaluate(model, val, dev, a.input)
    out = {"input": a.input, "best_epoch": best[1], "val": {k: vres[k] for k in ("mpjpe", "pa_mpjpe", "accel")},
           "test": res, "mean_pose_test": mean_pose_baseline(train, test), "n_test_views": len(test),
           "n_test_frames": int(sum(len(q["y3d"]) for q in test)), "seed": a.seed, "norm": a.norm}
    json.dump(out, open(os.path.join(a.run, "results.json"), "w"), indent=1)
    np.savez_compressed(os.path.join(a.run, "test_preds.npz"), **preds)
    print("RESULT", json.dumps({k: out[k] for k in ("input", "best_epoch", "val", "mean_pose_test")}),
          json.dumps({k: res[k] for k in ("mpjpe", "pa_mpjpe", "accel")}), flush=True)
    if a.check:  # overfit test: the net must fit 6 training views far better than the mean pose
        fit, _ = evaluate(model, train, dev, a.input)
        base = mean_pose_baseline(train, train)["mpjpe"]
        print(f"check: train-fit MPJPE {fit['mpjpe']:.1f} vs mean pose {base:.1f}")
        assert np.isfinite(res["mpjpe"]) and fit["mpjpe"] < 0.5 * base
        g = np.random.default_rng(1).normal(size=(5, 17, 3))
        assert np.allclose(pa_mpjpe(g * 2 + 1, g), 0, atol=1e-6) and np.allclose(mpjpe(g, g), 0)
        print("train_lift --check OK")


if __name__ == "__main__":
    main()
