"""Accuracy methods on the merged lifter, tested on a KERAAL participant the run never trained on.
One run: ASPset train + --train-parts, evaluated on --eval-parts. Nested selection uses the 6 ordered single-participant
pairs, so the config for outer test participant P1 is chosen only from P2->P3 and P3->P2 (see report.py).
Usage: python tune.py <run dir> --train-parts P2 --eval-parts P3 [--seed 0] [method options]
       python tune.py --check
KERAAL is CC BY-NC-SA: run dirs stay on E:, outside the repo."""
import argparse
import functools
import glob
import json
import os
import sys

import numpy as np
import torch

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import aspset
import keraal_eval
import merge_train
import train_lift
from merge_train import eval_keraal, keraal_seqs
from train_lift import TCN, evaluate, load_split

ASP, ASP_DET = "E:/ASPset510_data/extracted/ASPset-510", "E:/ASPset510_data/det2d/yolo11x"
G3, G3_DET, CALIB = "E:/KERAAL_data/extracted/group3", "E:/KERAAL_mocap3d/det2d", "E:/KERAAL_mocap3d/calib"
BONES = [(0, 1), (1, 2), (2, 16), (3, 4), (4, 5), (5, 14), (6, 7), (7, 8), (8, 16), (9, 10), (10, 11), (11, 14),
         (12, 13), (13, 14), (14, 15), (15, 16)]


def augment(X, Y, a, gen):
    """X (B, T, 17, 3) x, y, conf in root-normalised units; Y (B, T', 17, 3) metres. Returns new tensors."""
    X, Y = X.clone(), Y.clone()
    B, dev = X.shape[0], X.device
    if a.roll:  # camera roll: the only rotation valid on detected 2D without knowing depth
        t = torch.empty(B, device=dev).uniform_(-np.radians(a.roll), np.radians(a.roll), generator=gen)
        c, s = t.cos()[:, None, None], t.sin()[:, None, None]
        for Z in (X, Y):
            x, y = Z[..., 0].clone(), Z[..., 1].clone()
            Z[..., 0], Z[..., 1] = c * x - s * y, s * x + c * y
    if a.noise:
        X[..., :2] += a.noise * torch.randn(X[..., :2].shape, device=dev, generator=gen)
    if a.jdrop:  # whole joint lost for the whole chunk: same failure as an occluded limb in the detector
        m = torch.rand(B, 17, device=dev, generator=gen) < a.jdrop
        X[m[:, None].expand(-1, X.shape[1], -1)] = 0
    return X, Y


def losses(P, Y, a):
    m = ~torch.isnan(Y[..., 0])
    loss = torch.linalg.norm(P[m] - Y[m], dim=-1).mean()
    if a.bone:
        i, j = zip(*BONES)
        lp, ly = torch.linalg.norm(P[:, :, i] - P[:, :, j], dim=-1), torch.linalg.norm(Y[:, :, i] - Y[:, :, j], dim=-1)
        b = ~torch.isnan(ly)
        loss = loss + a.bone * (lp[b] - ly[b]).abs().mean()
    if a.vel:
        vp, vy = P[:, 1:] - P[:, :-1], Y[:, 1:] - Y[:, :-1]
        v = ~torch.isnan(vy[..., 0])
        loss = loss + a.vel * torch.linalg.norm(vp[v] - vy[v], dim=-1).mean()
    return loss, m


def angle_summary(rows):
    med = lambda v, k: float(np.nanmedian([r[k] for r in v])) if v else None
    rtk = [r for r in rows if r["exercise"] == "RTK"]
    return {"n_pairs": len(rows), "r0": med(rows, "ours_3d_r0"), "rmse": med(rows, "ours_3d_rmse"),
            "rtk_r0": med(rtk, "ours_3d_r0"), "kin_r0": med(rows, "kinect_r0"), "kin_rmse": med(rows, "kinect_rmse")}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("run")
    ap.add_argument("--train-parts", required=True)
    ap.add_argument("--eval-parts", required=True)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--epochs", type=int, default=120)
    ap.add_argument("--lr", type=float, default=1e-3)
    ap.add_argument("--keraal-share", type=float, default=0, help="repeat KERAAL recordings to this share of training frames")
    ap.add_argument("--roll", type=float, default=0, help="max camera roll augmentation, degrees")
    ap.add_argument("--noise", type=float, default=0, help="2D noise std, fraction of body extent")
    ap.add_argument("--jdrop", type=float, default=0, help="probability of hiding a joint for a whole chunk")
    ap.add_argument("--bone", type=float, default=0, help="bone-length loss weight")
    ap.add_argument("--vel", type=float, default=0, help="velocity loss weight")
    ap.add_argument("--layers", type=int, default=4, help="TCN layers: receptive field 3^layers")
    ap.add_argument("--drop", type=float, default=0.25)
    a = ap.parse_args()
    os.makedirs(a.run, exist_ok=True)
    json.dump({**vars(a), "input": "det", "norm": "root"}, open(os.path.join(a.run, "args.json"), "w"), indent=1)
    torch.manual_seed(a.seed)
    rng = np.random.default_rng(a.seed)
    dev = "cuda" if torch.cuda.is_available() else "cpu"
    gen = torch.Generator(dev).manual_seed(a.seed)
    make = functools.partial(TCN, widths=(3,) * a.layers, drop=a.drop)
    model = make(17, 3).to(dev)

    keys = sorted(os.path.basename(f)[:-4] for f in glob.glob(os.path.join(CALIB, "gt3d", "*.npz")))
    part = lambda k: k.split("-")[1][:2]
    tr_parts, ev_parts = a.train_parts.split(","), [p for p in a.eval_parts.split(",") if p]  # "" = final model, no G3 test
    assert not set(tr_parts) & set(ev_parts), "evaluation participant must never be trained on"
    tr_keys = [k for k in keys if part(k) in tr_parts]
    ktr = keraal_seqs(G3_DET, CALIB, [k for i, k in enumerate(tr_keys) if i % 5], "vicon")
    kval = keraal_seqs(G3_DET, CALIB, tr_keys[0::5], "vicon")
    atr = load_split(ASP, "train", "det", ASP_DET)
    aval = load_split(ASP, "val", "det", ASP_DET)
    nk, na = sum(len(q["y3d"]) for q in ktr), sum(len(q["y3d"]) for q in atr)
    rep = max(1, round(a.keraal_share * na / ((1 - a.keraal_share) * nk))) if a.keraal_share else 1
    tr = ktr * rep + atr
    print(f"KERAAL frames {nk} x{rep}, ASPset frames {na}", flush=True)

    opt = torch.optim.AdamW(model.parameters(), lr=a.lr, weight_decay=1e-4)
    sched = torch.optim.lr_scheduler.ExponentialLR(opt, 0.95 ** (60 / a.epochs))
    best, log = (1e9, -1), []
    for ep in range(a.epochs):
        model.train()
        for X, Y in train_lift.batches(tr, model.rf, 128, 64, "det", rng):
            X, Y = augment(X.to(dev), Y.to(dev), a, gen)
            loss, _ = losses(model(X), Y, a)
            opt.zero_grad(); loss.backward(); opt.step()
        sched.step()
        kv = eval_keraal(model, kval, dev)["mpjpe"]
        av = evaluate(model, aval, dev, "det", tta=False)[0]["mpjpe"]
        log.append({"epoch": ep + 1, "val_keraal": kv, "val_aspset": av})
        if (ep + 1) % 20 == 0:
            print(json.dumps(log[-1]), flush=True)
        if (kv + av) / 2 < best[0]:
            best = ((kv + av) / 2, ep + 1)
            torch.save(model.state_dict(), os.path.join(a.run, "best.pt"))
    json.dump(log, open(os.path.join(a.run, "log.json"), "w"))
    model.load_state_dict(torch.load(os.path.join(a.run, "best.pt"), map_location=dev))
    model.eval()
    if not ev_parts:
        return

    asp ={k: v for k, v in evaluate(model, load_split(ASP, "test", "det", ASP_DET), dev, "det")[0].items()
           if k in ("mpjpe", "pa_mpjpe")}
    train_lift.TCN = make  # keraal_eval builds the model itself
    tmp = os.path.join(a.run, "angles_all.json")
    keraal_eval.evaluate(G3, G3_DET, a.run, tmp)
    rows = json.load(open(tmp))["rows"]
    os.remove(tmp)
    for ev in ev_parts:  # one training serves every evaluation participant; one results.json per (train, eval)
        out = {"args": vars(a), "best_epoch": best[1], "val_keraal_same_people": log[best[1] - 1]["val_keraal"],
               "unseen": eval_keraal(model, keraal_seqs(G3_DET, CALIB, [k for k in keys if part(k) == ev], "vicon"), dev),
               "aspset_test": asp, "angles": angle_summary([r for r in rows if r["participant"] == ev])}
        res = os.path.join(os.path.dirname(a.run), f"{''.join(tr_parts)}_{ev}_s{a.seed}")
        os.makedirs(res, exist_ok=True)
        json.dump(out, open(os.path.join(res, "results.json"), "w"), indent=1)
        print("RESULT", ev, json.dumps({"mpjpe": out["unseen"]["mpjpe"], **out["angles"]}), flush=True)


def _check():
    a = argparse.Namespace(roll=30, noise=0, jdrop=0, bone=0, vel=0)
    gen = torch.Generator().manual_seed(0)
    X = torch.rand(4, 10, 17, 3); Y = torch.rand(4, 5, 17, 3)
    Y[0, 0, 12] = float("nan")
    Xa, Ya = augment(X, Y, a, gen)
    assert torch.allclose(Xa[..., 2], X[..., 2])  # confidence untouched
    n = lambda Z: torch.linalg.norm(Z[..., :2], dim=-1)
    assert torch.allclose(n(Xa), n(X), atol=1e-5)  # rotation keeps length
    assert torch.isnan(Ya[0, 0, 12]).all() and torch.isnan(Ya).sum() == 3  # masked targets stay masked, nothing new
    a = argparse.Namespace(roll=0, noise=0, jdrop=1.0, bone=0, vel=0)
    assert (augment(X, Y, a, gen)[0] == 0).all()
    a = argparse.Namespace(roll=0, noise=0, jdrop=0, bone=0, vel=0)
    assert torch.equal(augment(X, Y, a, gen)[0], X)
    # perfect prediction: every loss term is zero, including with masked joints
    a = argparse.Namespace(bone=1.0, vel=1.0)
    P = torch.nan_to_num(Y)
    assert losses(P, Y, a)[0].item() < 1e-5
    # wrong bone length is penalised beyond the position term
    Q = P.clone(); Q[:, :, 0] += 0.1
    assert losses(Q, Y, a)[0] > losses(Q, Y, argparse.Namespace(bone=0, vel=0))[0]
    print("tune --check OK")


if __name__ == "__main__":
    if sys.argv[1] == "--check":
        _check()
    else:
        main()
