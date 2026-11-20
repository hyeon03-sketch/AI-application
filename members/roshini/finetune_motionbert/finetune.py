"""Fine-tune MotionBERT (all layers) and keep the epoch with the lowest validation MPJPE.

  python finetune.py --mb MotionBERT --data Mocap3D_preprocessed_1118 --out runs/seed0
  (stage 2: add KERAAL with --train ... keraal_kinect:all keraal_g3:<fold split> and --val ...)

Writes to --out after every epoch: best.pt (weights of the best epoch), last.pt (everything needed to continue),
history.json (train/val MPJPE per epoch). Rerunning the same command continues from last.pt."""
import argparse
import json
import os
import time

import numpy as np
import torch

from mb_common import build, load_motionbert, masked_losses

ap = argparse.ArgumentParser()
ap.add_argument("--mb", required=True, help="MotionBERT repository folder (with the checkpoint downloaded)")
ap.add_argument("--data", required=True, help="data bundle folder (splits.json, *_kp2d_h36m.npz, *_gt3d.npz)")
ap.add_argument("--out", required=True, help="folder for best.pt, last.pt, history.json")
ap.add_argument("--train", nargs="+", default=["aspset:train", "rehab24:train"], help="dataset:split list")
ap.add_argument("--val", nargs="+", default=["aspset:val", "rehab24:val"], help="dataset:split list")
ap.add_argument("--epochs", type=int, default=20)
ap.add_argument("--lr", type=float, default=5e-5)
ap.add_argument("--batch", type=int, default=4)
ap.add_argument("--accum", type=int, default=8, help="small steps per weight update (batch x accum = 32 clips)")
ap.add_argument("--seed", type=int, default=0)
a = ap.parse_args()

dev = "cuda" if torch.cuda.is_available() else "cpu"
os.makedirs(a.out, exist_ok=True)
Xtr, Ytr, Mtr, Jtr = build(a.data, a.train)
Xva, Yva, Mva, Jva = build(a.data, a.val)
print(f"{len(Xtr)} train clips, {len(Xva)} val clips, device {dev}")

torch.manual_seed(a.seed); np.random.seed(a.seed)
model = load_motionbert(a.mb).to(dev)
opt = torch.optim.AdamW(model.parameters(), lr=a.lr, weight_decay=0.01)
sched = torch.optim.lr_scheduler.ExponentialLR(opt, gamma=0.99)        # MotionBERT's own decay
use_amp = dev == "cuda"
scaler = torch.amp.GradScaler("cuda", enabled=use_amp)                  # half precision on the GPU


def to_dev(arrs, i):
    return (torch.from_numpy(x[i]).to(dev) for x in arrs)


@torch.no_grad()
def val_mpjpe():
    model.eval(); tot, n = 0.0, 0.0
    for s in range(0, len(Xva), 16):
        xb, yb, mb, jb = to_dev((Xva, Yva, Mva, Jva), slice(s, s + 16))
        with torch.autocast("cuda", dtype=torch.float16, enabled=use_amp):
            pred = model(xb)
        pred = pred.float(); pred = pred - pred[:, :, :1]
        w = mb.float()[..., None] * jb.float()
        tot += (torch.norm(pred - yb, dim=-1) * w).sum().item(); n += w.sum().item()
    model.train()
    return tot / n * 1000


last_path = os.path.join(a.out, "last.pt")
if os.path.exists(last_path):
    ck = torch.load(last_path, map_location=dev, weights_only=False)
    model.load_state_dict(ck["model"]); opt.load_state_dict(ck["opt"])
    sched.load_state_dict(ck["sched"]); scaler.load_state_dict(ck["scaler"])
    start, best, hist = ck["epoch"] + 1, ck["best"], ck["hist"]
    print(f"continuing from epoch {start}, best val so far {best:.1f} mm")
else:
    start, best = 0, float("inf")
    before = val_mpjpe()
    hist = [{"epoch": "before", "val_mpjpe_mm": round(before, 2)}]
    print(f"before fine-tuning: val MPJPE {before:.1f} mm")

model.train()
for ep in range(start, a.epochs):
    t0 = time.time()
    order = np.random.default_rng(ep).permutation(len(Xtr))          # same shuffle when continuing
    nsteps, run = len(order) // a.batch, 0.0
    opt.zero_grad()
    for k in range(nsteps):
        xb, yb, mb, jb = to_dev((Xtr, Ytr, Mtr, Jtr), order[k * a.batch:(k + 1) * a.batch])
        with torch.autocast("cuda", dtype=torch.float16, enabled=use_amp):
            pred = model(xb)
        pred = pred.float(); pred = pred - pred[:, :, :1]               # pelvis at 0, like the targets
        loss, pos = masked_losses(pred, yb, mb, jb)
        scaler.scale(loss / a.accum).backward()
        run += pos.item()
        if (k + 1) % a.accum == 0 or k + 1 == nsteps:
            scaler.step(opt); scaler.update(); opt.zero_grad()
    sched.step()
    v = val_mpjpe()
    mins = (time.time() - t0) / 60
    hist.append({"epoch": ep, "train_mpjpe_mm": round(run / nsteps * 1000, 2), "val_mpjpe_mm": round(v, 2),
                 "minutes": round(mins, 1)})
    if v < best:
        best = v
        torch.save(model.state_dict(), os.path.join(a.out, "best.pt"))
    torch.save({"model": model.state_dict(), "opt": opt.state_dict(), "sched": sched.state_dict(),
                "scaler": scaler.state_dict(), "epoch": ep, "best": best, "hist": hist}, last_path)
    json.dump(hist, open(os.path.join(a.out, "history.json"), "w"), indent=1)
    print(f"epoch {ep:2d} | train {run / nsteps * 1000:6.1f} mm | val {v:6.1f} mm | best {best:6.1f} | {mins:.1f} min")

print("done. best val MPJPE:", round(best, 1), "mm")
